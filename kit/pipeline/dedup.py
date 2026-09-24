#!/usr/bin/env python3
"""중복 기사 검열 — 이미 발행한 사건과 같은 내용인지, 새 사실이 있는지 판정한다.

규칙 (사용자 결정 2026-09-24)
  - 같은 기사(URL)는 다시 쓰지 않는다.
  - 같은 사건이라도 새로 확인된 사실(업데이트)이 있으면 후속으로 쓸 수 있다.
  - 다른 매체가 같은 내용을 다음 날 다시 쓴 경우(예: 로이터 → 다음 날 NYT)는 매체와 관계없이 건너뛴다.

판정 방식
  1) 사건 동일성: 고유명사(회사·광산·설비·지명)와 사건 유형 단어(파업·가동중단·불가항력·관세…)가 겹치는 정도
  2) 새 사실: 새 근거 문장 가운데 이전 근거 문장에 없는 숫자·날짜·상태 단어가 들어 있는 문장
발행 이력: 키트가 저장소 안이면 저장소의 게시된 호(issues/<날짜>/post.json + published/<날짜>.json, render.history_from_repo),
아니면 issues.json (issues[].stories).

  python pipeline/dedup.py posts/2026-09-25_brief.json                  # 포스트 점검 (이력 자동)
  python pipeline/dedup.py posts/2026-09-25_brief.json --history ../     # 저장소 루트 지정
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WINDOW_DAYS = 14          # 이 기간 안의 발행분과 비교
SAME_STORY = 0.34         # 사건 동일성 점수 기준

STOP = set("""a an the and or of in on at to for from by with as is are was were be been has have had it its this that these those
said says say according after before over under into amid while when than then also more most new latest last first second third
monday tuesday wednesday thursday friday saturday sunday january february march april may june july august september october
november december jan feb mar apr jun jul aug sep sept oct nov dec reuters bloomberg icis mining com yahoo finance editing reporting
writing by company firm group corp inc ltd plc co the all following typically world operations operation east west north south
market markets sources source spokesperson statement officials official data database supply demand global international national
state government ministry president chief executive ceo cfo it's we our they their he she his her"""
.split())
EVENT = {
    "halt": ["halt", "halts", "halted", "suspend", "suspended", "suspension", "stoppage", "shut", "shutdown", "outage", "closure", "closed"],
    "restart": ["restart", "restarted", "resume", "resumed", "resumption", "reopen", "reopened", "back online"],
    "strike": ["strike", "strikes", "walkout", "union", "unions", "vote", "mediation", "collective contract", "wage talks"],
    "fm": ["force majeure"],
    "fm_lift": ["lifted the force majeure", "lifts force majeure", "lift force majeure", "force majeure was lifted"],
    "accident": ["accident", "killed", "death", "fatal", "fire", "explosion", "injured"],
    "tariff": ["tariff", "tariffs", "duty", "duties", "anti-dumping", "countervailing", "safeguard", "section 232", "quota", "cbam"],
    "regulation": ["ban", "regulation", "rule", "sanction", "sanctions", "waiver", "export control", "phase-down", "permit"],
    "deal": ["acquire", "acquisition", "merger", "takeover", "stake", "joint venture", "offtake"],
    "capacity": ["expansion", "capacity", "new plant", "startup", "start-up", "commission", "cut output", "production cut", "curtail"],
}
# 한국어 기사용 사건 단어 (국내 매체 추가, 2026-09-25)
EVENT_KO = {
    "halt": ["가동 중단", "가동중단", "조업 중단", "조업중단", "생산 중단", "생산중단", "셧다운", "폐쇄", "중단"],
    "restart": ["재개", "재가동", "정상화"],
    "strike": ["파업", "노조", "찬반 투표", "찬반투표", "임금 협상", "임금협상"],
    "fm": ["불가항력"],
    "fm_lift": ["불가항력 해제", "불가항력을 해제"],
    "accident": ["사고", "사망", "화재", "폭발", "부상"],
    "tariff": ["관세", "반덤핑", "상계관세", "세이프가드", "쿼터", "탄소국경"],
    "regulation": ["규제", "금지", "제재", "수출통제", "수출 통제", "허가", "단계적 감축"],
    "deal": ["인수", "합병", "지분", "합작"],
    "capacity": ["증설", "감산", "신규 공장", "생산능력", "생산 능력", "가동률", "구조조정"],
}
for _k, _ws in EVENT_KO.items():
    EVENT[_k] = EVENT[_k] + _ws
KO_PARTICLES = sorted("은 는 이 가 을 를 의 에 에서 에게 로 으로 와 과 도 만 까지 부터 서 께 이다 였다 했다 한다 하고 하며 하는 된다 되는".split(), key=len, reverse=True)
KO_STOP = set("""기자 오늘 어제 올해 지난해 내년 이번 관련 대한 위해 통해 따라 따른 대해 등 및 또 또한 이날 현지 시간 당국 정부 업계 시장 국내 해외
글로벌 세계 최대 최고 최저 전년 전월 대비 이상 이하 가능성 전망 예상 우려 영향 발표 밝혔다 말했다 전했다 보도 보도했다 뉴스 소식 속보 단독
종합 사진 영상 제공 기업 회사 그룹 산업 경제 가운데 가격 시세 수요 공급 수급 수출 수입 생산 판매 계획 방침 결정 검토 추진 확대 축소 증가 감소
상승 하락 급등 급락 원재료 원자재 철강 구리 알루미늄 광산 제련소 제련 석유화학 화학 냉매 원유 정유 나프타 에틸렌 합성수지 비철 금속
전면 근로자 노동자 관계자 여파 계속 공장 설비 업체 제품 소재 사업 투자 조업 현장 인근 일대 지역 주요 일부 전체 모든 각국 당시 최근 향후""".split())
_KO_EVENT_WORDS = {w for ws in EVENT_KO.values() for w in ws}


# 한글 표기 ↔ 영문 고유명사 (국내·해외 기사를 같은 사건으로 묶기 위함). 필요하면 추가한다
KO_ALIAS = {"에스콘디다": "escondida", "센티넬라": "centinela", "코델코": "codelco", "안토파가스타": "antofagasta", "글렌코어": "glencore",
            "리오틴토": "rio", "앵글로아메리칸": "anglo", "프리포트": "freeport", "그라스베르그": "grasberg", "퍼스트퀀텀": "quantum",
            "알코아": "alcoa", "루살": "rusal", "노벨리스": "novelis", "고려아연": "korea zinc", "포스코": "posco", "현대제철": "hyundai",
            "아르셀로미탈": "arcelormittal", "일본제철": "nippon", "뉴코어": "nucor", "클리블랜드클리프스": "cliffs", "바오산": "baosteel",
            "바오우": "baowu", "아람코": "aramco", "사빅": "sabic", "라이온델바젤": "lyondellbasell", "다우": "dow", "시노펙": "sinopec",
            "엑손모빌": "exxonmobil", "케무어스": "chemours", "허니웰": "honeywell", "다이킨": "daikin", "아케마": "arkema", "오페크": "opec",
            "석유수출국기구": "opec", "런던금속거래소": "lme", "칠레": "chile", "페루": "peru", "인도네시아": "indonesia", "싱가포르": "singapore"}


def ko_tokens(text):
    """한국어 고유명사 후보: 2자 이상 한글 낱말에서 조사를 떼고 일반어·사건어·품목어를 뺀 것."""
    out = set()
    for w in re.findall(r"[가-힣]{2,}", _norm(text)):
        for pt in KO_PARTICLES:
            if w.endswith(pt) and len(w) - len(pt) >= 2:
                w = w[: -len(pt)]
                break
        if w in KO_STOP or len(w) < 2 or w[-1] in "져졌해했돼됐" or any(e in w for e in _KO_EVENT_WORDS if " " not in e):
            continue
        out.add(w)
        if w in KO_ALIAS:
            out.add(KO_ALIAS[w])
    return out
STATUS_TERMS = {t for k in ("halt", "restart", "fm", "fm_lift", "strike") for t in EVENT[k]} | {"agreement", "deal reached", "rejected", "approved", "accepted", "ended", "extended", "delayed",
                                                                                     "타결", "합의", "부결", "가결", "승인", "거부", "종료", "연장", "연기"}


def _norm(t):
    t = str(t)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), (" ", " "), ("**", "")):
        t = t.replace(a, b)
    t = re.sub("[​‌‍⁠﻿­]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def entities(text):
    """고유명사 후보: 대문자로 시작하는 단어·약어 (문장 첫 단어 포함), 불용어 제외."""
    out = set()
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9&\-]{1,}|[A-Z]{2,}[0-9]*)\b", _norm(text)):
        w = m.group(1).lower().strip("-")
        if w not in STOP and len(w) > 1 and not w.isdigit():
            out.add(w)
    return out | ko_tokens(text)


def events(text):
    low = " " + _norm(text).lower() + " "
    return {k for k, words in EVENT.items() if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low) for w in words)}


MONTHS = "january february march april may june july august september october november december".split()


def facts_tokens(text):
    """숫자·날짜·상태 단어 — '새 사실' 판정용."""
    low = _norm(text).lower()
    nums = {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)*", low)}
    dates = set()
    for m in re.finditer(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")|(" + "|".join(MONTHS) + r")\s+(\d{1,2})", low):
        d, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        dates.add(f"{mo}-{int(d)}")
    for m in re.finditer(r"(\d{1,2})월\s*(\d{1,2})일", low):   # 9월 25일
        dates.add(f"{MONTHS[int(m.group(1)) - 1]}-{int(m.group(2))}")
    status = {t for t in STATUS_TERMS if re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", low)}
    return nums, dates, status


def story_features(slide, sources):
    """뉴스 슬라이드 1장 → 비교용 특징."""
    S = {x["id"]: x for x in sources}
    refs = []
    for v in [slide.get("src")] + [f.get("src") for f in slide.get("facts") or []] + [r.get("src") for vz in slide.get("viz") or [] for r in (vz.get("rows") or [])]:
        refs += v if isinstance(v, list) else ([v] if v else [])
    refs = list(dict.fromkeys(refs))
    ev = [q for r in refs for q in (S.get(r, {}).get("evidence") or [])]
    titles = [S.get(r, {}).get("title", "") for r in refs] + [slide.get("orig", ""), slide.get("toc") or slide.get("headline", "")]
    text = " ".join(titles + ev)
    return {"refs": refs, "urls": [S.get(r, {}).get("url", "") for r in refs], "titles": [t for t in titles if t],
            "evidence": ev, "entities": sorted(entities(text)), "events": sorted(events(text))}


def score(a, b):
    ea, eb = set(a["entities"]), set(b["entities"])
    ent = len(ea & eb) / max(1, min(len(ea), len(eb)))           # 작은 쪽 기준 겹침
    evt = len(set(a["events"]) & set(b["events"]))
    return round(ent * (1.0 if evt else 0.6), 3), sorted(ea & eb), sorted(set(a["events"]) & set(b["events"]))


STATUS_CANON = {"타결": "agreement", "합의": "agreement", "deal reached": "agreement", "부결": "rejected", "거부": "rejected",
                "가결": "approved", "승인": "approved", "accepted": "approved", "종료": "ended", "연장": "extended", "연기": "delayed"}


def _canon_status(terms):
    """상태 단어를 언어와 관계없이 같은 뜻끼리 묶는다 (예: '조업 중단' = 'halt', '재개' = 'resume')."""
    out = set()
    for t in terms:
        key = next((k for k, ws in EVENT.items() if t in ws), None)
        out.add(key or STATUS_CANON.get(t, t))
    return out


def novel_facts(new_ev, old_ev):
    """새 근거 문장 중 이전 근거에 없던 숫자·날짜·상태를 담은 문장."""
    old_n, old_d, old_s = set(), set(), set()
    old_norm = [_norm(q).lower() for q in old_ev]
    for q in old_ev:
        n, d, s = facts_tokens(q)
        old_n |= n; old_d |= d; old_s |= _canon_status(s)
    out = []
    for q in new_ev:
        nq = _norm(q).lower()
        if any(nq in o or o in nq for o in old_norm):
            continue
        n, d, s = facts_tokens(q)
        new_s, new_d, new_n = _canon_status(s) - old_s, d - old_d, n - old_n
        # 배경 숫자(작년 생산량 등)만 새로 나온 문장은 새 사실로 보지 않는다:
        # 상태 변화(재개·타결·해제…)나 새 날짜가 있거나, 새 숫자가 사건 단어와 함께 나올 때만 인정
        if new_s or new_d or (new_n and events(q)):
            out.append({"quote": q, "new": sorted(new_n | {f"date:{x}" for x in new_d} | {f"status:{x}" for x in new_s})})
    return out


def prior_stories(history, post_date):
    """history(issues.json) → 비교 대상 이전 스토리 목록 (포스트 날짜 이전, WINDOW_DAYS 이내)."""
    if not history:
        return []
    d0 = dt.date.fromisoformat(post_date)
    out = []
    for iss in history.get("issues", []):
        try:
            d = dt.date.fromisoformat(iss["date"])
        except Exception:
            continue
        if not (d0 - dt.timedelta(days=WINDOW_DAYS) <= d < d0):
            continue
        for st in iss.get("stories", []):
            out.append({**st, "date": iss["date"]})
    return out


def check_post(post, history):
    """포스트의 뉴스 슬라이드마다 중복 판정. errors, warns, report 반환."""
    errors, warns, report = [], [], []
    prior = prior_stories(history, post["date"])
    used_urls = {u.rstrip("/") for st in prior for u in st.get("urls", []) if u}
    # 같은 날짜 이전 발행 전부의 URL (창 밖 포함) — 같은 기사 재사용 금지
    for iss in (history or {}).get("issues", []):
        if iss.get("date", "") < post["date"]:
            for s in iss.get("sources", []):
                if s.get("url"):
                    used_urls.add(s["url"].rstrip("/"))
    srcs = post.get("sources", [])
    for i, s in enumerate(post.get("slides", []), 1):
        if s.get("type") != "news":
            continue
        f = story_features(s, srcs)
        for u in f["urls"]:
            if u and u.rstrip("/") in used_urls:
                errors.append(f"slide {i}: 이미 발행한 기사 URL을 다시 씀 — {u}")
        best = None
        for st in prior:
            sc, ents, evs = score(f, st)
            if sc >= SAME_STORY and (best is None or sc > best[0]):
                best = (sc, st, ents, evs)
        row = {"slide": i, "headline": _norm(s.get("headline", "")).replace("\n", " "), "match": None}
        if best:
            sc, st, ents, evs = best
            nov = novel_facts(f["evidence"], st.get("evidence", []))
            row["match"] = {"story_id": st.get("story_id"), "date": st["date"], "headline": st.get("headline"), "score": sc,
                            "shared_entities": ents, "shared_events": evs, "novel": nov}
            upd = s.get("update_of")
            if not nov:
                errors.append(f"slide {i}: {st['date']} 발행 '{st.get('headline')}'과 같은 사건(겹침 {', '.join(ents[:5])})인데 "
                              f"새 사실이 없음 — 매체가 달라도 건너뛸 것")
            elif upd != st.get("story_id"):
                errors.append(f"slide {i}: {st['date']} 발행 '{st.get('headline')}'의 후속 기사 — "
                              f"update_of: \"{st.get('story_id')}\" 를 적고 새 사실 위주로 쓸 것 "
                              f"(새 사실 예: {nov[0]['quote'][:60]}…)")
        elif s.get("update_of"):
            warns.append(f"slide {i}: update_of={s['update_of']} 이지만 최근 {WINDOW_DAYS}일 발행분에서 같은 사건을 찾지 못함")
        report.append(row)
    return errors, warns, report


def stories_for_index(post):
    """발행 이력에 들어갈 스토리 목록 (render.history_from_repo 가 호마다 계산)."""
    out = []
    n = 0
    for s in post.get("slides", []):
        if s.get("type") != "news":
            continue
        n += 1
        f = story_features(s, post.get("sources", []))
        out.append({"story_id": s.get("story_id") or f"{post['date']}-s{n}", "category": s.get("category"),
                    "headline": _norm(s.get("toc") or s.get("headline", "")).replace("\n", " "),
                    "update_of": s.get("update_of", ""), **f})
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("post")
    ap.add_argument("--history", default=None, help="저장소 루트 폴더 또는 issues.json (기본: 자동)")
    a = ap.parse_args()
    post = json.loads(Path(a.post).read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT))
    from render import load_history
    hist = load_history(a.history)
    e, w, r = check_post(post, hist)
    for row in r:
        m = row["match"]
        print(f"slide {row['slide']} {row['headline']}")
        if m:
            print(f"  ↳ {m['date']} '{m['headline']}' 과 같은 사건 (점수 {m['score']}, 공통 {m['shared_entities']}, 사건 {m['shared_events']})")
            for nf in m["novel"]:
                print(f"     새 사실 {nf['new']}: {nf['quote'][:90]}")
    for x in w:
        print("  !", x)
    for x in e:
        print("  ✗", x)
    sys.exit(1 if e else 0)
