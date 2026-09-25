#!/usr/bin/env python3
"""RAW MATERIALS DAILY — 카드뉴스 PNG 렌더러

사용법
  python render.py posts/2026-09-24_cu.json            # 검증 통과 시 PNG 생성
  python render.py posts/*.json                         # 여러 포스트 일괄
  python render.py posts/x.json --draft                 # 출처 누락 등 오류가 있어도 초안으로 렌더 (빨간 경고 표시)
  python render.py posts/x.json --ratio 3:4             # 1080x1440 (앱 수동 업로드용. 자동 게시 API는 3:4 불가 → 기본 4:5)

출력
  out/<post id>/01.png ...   슬라이드 PNG (1080px)
  out/<post id>/caption.txt  캡션 + 출처 + 해시태그 (인스타 본문에 그대로 붙여넣기)
  out/<post id>/preview.png  전체 슬라이드 미리보기 시트
  out/<post id>/data_sources.csv  카드의 모든 숫자·사실 ↔ 출처 대조표 (엑셀에서 바로 열림)
  out/<post id>/evidence.csv      출처별 근거 문장(원문 그대로) + 저장된 원문 발췌에서 확인 여부
  out/<post id>/ledger.xlsx       위 두 표를 시트 2개로 묶은 엑셀

근거(evidence) 검증
  sources[].evidence 에 기사 원문 문장을 그대로 넣는다. runs/<포스트 날짜>/articles/<출처 id>.md
  (WebFetch로 저장한 본문 발췌)가 있으면 문장이 그 안에 실제로 있는지 대조하고,
  카드의 숫자(stats·split·gauge·key)가 근거 문장에 나오는지 확인한다. 계산값은 calc: true 로 표시.
"""
import argparse
import csv
import datetime
import json
import re
import sys
from urllib.parse import urlparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template" / "card.html"


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ids(v):
    if v is None:
        return []
    return [x for x in (v if isinstance(v, list) else [v]) if x]


PRICE_RE = re.compile(
    r"(US\$|\$\s?\d|€\s?\d|£\s?\d|¥\s?\d|\d[\d,.]*\s?(달러|원|위안|엔|유로|센트)(\s|$|/|/톤|/t)|"
    r"(USD|CNY|RMB|EUR|JPY|KRW)\s?/\s?(t|mt|톤|kg|lb|bbl|배럴|gal)|/\s?(톤|t|mt|kg|lb|bbl|배럴)\b|"
    r"(달러|원|위안)\s?/\s?(톤|kg|배럴)|per\s+(tonne|ton|barrel|pound|gallon))",
    re.IGNORECASE)
PRICE_WORD_RE = re.compile(r"(가격|시세|단가|price)", re.IGNORECASE)


def iter_text(obj):
    """슬라이드 안의 모든 문자열(출처 id 제외)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_text(v)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in ("src", "type", "category", "topic", "impact", "coverage"):
                yield from iter_text(v)


def _norm(t):
    return re.sub(r"[^0-9a-z가-힣&]", "", str(t).lower())


def outlet_by_name(name, outlets):
    n = _norm(name)
    for o in outlets:
        if n and n in {_norm(a) for a in [o["name"]] + o.get("aliases", [])}:
            return o
    return None


def outlet_by_url(url, outlets):
    host = (urlparse(str(url)).hostname or "").lower()
    for o in outlets:
        for d in o.get("domains", []):
            if host == d or host.endswith("." + d):
                return o
    return None


def slide_refs(s: dict):
    """슬라이드에서 쓰인 출처 ID 전부(슬라이드 src + 항목별 src)."""
    out = list(_ids(s.get("src")))
    for x in [s.get("ticker") or {}] + (s.get("items") or []) + (s.get("rows") or []) + (s.get("bars") or []) + (s.get("facts") or []) + (s.get("viz") or []):
        if isinstance(x, dict):
            out += _ids(x.get("src"))
    for g in s.get("groups") or []:
        for r in g.get("rows") or []:
            out += _ids(r.get("src"))
    return list(dict.fromkeys(out))


def _qnorm(t):
    t = str(t)
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " "), ("**", ""), ("\\", "")):
        t = t.replace(a, b)
    t = re.sub("[\u200b\u200c\u200d\u2060\ufeff\u00ad]", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()


NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _nums(t):
    return {n.replace(",", "") for n in NUM_RE.findall(str(t))}


def _num_ok(n, pool):
    """카드 숫자 n이 근거 문장 숫자에 있는지. 1.10 ↔ 1.1 같은 표기 차이는 허용."""
    if n in pool:
        return True
    try:
        f = float(n)
        return any(abs(float(p) - f) < 1e-9 for p in pool if re.fullmatch(r"\d+(\.\d+)?", p))
    except ValueError:
        return False


def article_path(run_dir, sid):
    if not run_dir:
        return None
    for ext in (".md", ".txt"):
        p = Path(run_dir) / "articles" / f"{sid}{ext}"
        if p.exists():
            return p
    return None


def check_evidence(post, brand, run_dir, errors, warns):
    rules = brand.get("rules", {})
    S = {x.get("id"): x for x in post.get("sources") or []}
    news_refs = set()
    for s in post.get("slides", []):
        if s.get("type") == "news":
            news_refs.update(slide_refs(s))
    # 1) 출처마다 근거 문장, 저장된 원문 발췌와 대조
    for sid in sorted(news_refs):
        x = S.get(sid)
        if not x:
            continue
        ev = [e for e in (x.get("evidence") or []) if str(e).strip()]
        if not ev:
            (errors if rules.get("evidence_required") else warns).append(f"출처 '{sid}': evidence(원문 근거 문장) 없음")
            continue
        ap = article_path(run_dir, sid)
        if not ap:
            (errors if rules.get("evidence_extract_required") else warns).append(
                f"출처 '{sid}': 원문 발췌 파일 없음 (runs/{post.get('date')}/articles/{sid}.md) — 근거 문장 대조 불가")
            continue
        body = _qnorm(ap.read_text(encoding="utf-8"))
        for k, e in enumerate(ev, 1):
            if _qnorm(e) not in body:
                errors.append(f"출처 '{sid}': evidence[{k}]가 저장된 원문 발췌에 없음 — \"{str(e)[:70]}…\"")
    # 2) 카드 숫자 ↔ 근거 문장
    for i, s in enumerate(post.get("slides", []), 1):
        if s.get("type") != "news":
            continue
        pool = set()
        for sid in slide_refs(s):
            for e in (S.get(sid) or {}).get("evidence") or []:
                pool |= _nums(e)
        checks = []  # (라벨, 숫자문자열, 오류여부)
        for v in s.get("viz") or []:
            vt = v.get("type")
            if vt == "stats":
                checks += [(f"stats '{it.get('label', '')}'", str(it.get("value", "")), True) for it in v.get("items") or [] if not it.get("calc")]
            if vt == "split":
                checks += [(f"split '{p_.get('label', '')}'", str(p_.get("value", "")), True) for p_ in v.get("parts") or [] if not p_.get("calc")]
            if vt == "gauge" and not v.get("calc"):
                checks += [("gauge", str(v.get(k)), True) for k in ("from", "to") if v.get(k) is not None]
            if vt == "calendar":
                for r in v.get("rows") or []:
                    for b in r.get("bars") or []:
                        if b.get("kind", "vote") == "vote":
                            checks += [(f"calendar '{r.get('label', '')}' 날짜", str(int(str(b.get(k))[-2:])), False) for k in ("from", "to") if b.get(k)]
            if vt == "timeline":
                checks += [(f"timeline '{e.get('t', '')}' 날짜", str(int(str(e.get("d"))[-2:])), False) for e in v.get("events") or [] if e.get("d") and not e.get("calc")]
        kv = s.get("key") or {}
        if kv.get("value") and not kv.get("calc") and "계산" not in str(kv.get("label", "")) and not re.fullmatch(r"\d{1,2}[./]\d{1,2}", str(kv["value"])):
            checks += [("key", n, True) for n in _nums(kv["value"])]
        for f in s.get("facts") or []:
            checks += [(f"fact '{str(f.get('t', ''))[:20]}'", n, False) for n in _nums(f.get("t", ""))]
        for lab, val, hard in checks:
            for n in _nums(val):
                if not _num_ok(n, pool):
                    msg = f"slide {i}: {lab}의 숫자 {n} — 근거 문장(evidence)에서 찾을 수 없음 (계산값이면 calc: true)"
                    (errors if hard and rules.get("evidence_required") else warns).append(msg)


def repo_root():
    """키트가 GitHub 저장소 안(<저장소>/kit/)에 있으면 저장소 루트, 아니면 None."""
    r = ROOT.parent
    if ROOT.name == "kit" and (r / "issues").is_dir() and (r / "published").is_dir():
        return r
    return None


def history_from_repo(repo: Path):
    """저장소의 issues/<날짜>/post.json 중 실제로 게시된 날(published/<날짜>.json 있음)만 발행 이력으로 만든다.
    형식은 예전 발행함 issues.json 과 같다: {"issues": [{date, issue, sources, stories, instagram}]}"""
    sys.path.insert(0, str(ROOT / "pipeline"))
    import dedup
    out = []
    for pj in sorted(Path(repo, "issues").glob("*/post.json")):
        d = pj.parent.name
        rec = Path(repo, "published", f"{d}.json")
        if not rec.exists():
            continue
        try:
            post = load_json(pj)
            pub = load_json(rec)
        except Exception:
            continue
        out.append({"date": d, "id": post.get("id"), "issue": post.get("issue"),
                    "sources": [{k: s.get(k) for k in ("id", "publisher", "via", "title", "date", "url")} for s in post.get("sources", [])],
                    "stories": dedup.stories_for_index(post),
                    "instagram": {"permalink": pub.get("permalink"), "media_id": pub.get("media_id")}})
    return {"issues": out, "source": "repo"}


def load_history(path=None):
    """발행 이력. path 가 폴더면 GitHub 저장소 루트로 보고 history_from_repo, 파일이면 issues.json.
    path 가 없으면: 키트가 저장소 안에 있을 때 저장소 이력, 아니면 키트 폴더의 issues.json."""
    if path and Path(path).is_dir():
        return history_from_repo(Path(path))
    if not path and repo_root():
        return history_from_repo(repo_root())
    p = Path(path) if path else ROOT / "issues.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def validate(post: dict, brand: dict, run_dir=None, history=None):
    """오류(errors)는 게시 불가 사항, 경고(warns)는 확인 권장 사항."""
    errors, warns = [], []
    rules = brand.get("rules", {})
    for k in ("id", "date", "category", "slides"):
        if k not in post:
            errors.append(f"필수 키 누락: {k}")
    if errors:
        return errors, warns
    if post["category"] not in brand["categories"]:
        errors.append(f"알 수 없는 category: {post['category']} (허용: {', '.join(brand['categories'])})")
    if post.get("topic") and post["topic"] not in brand["topics"]:
        errors.append(f"알 수 없는 topic: {post['topic']} (허용: {', '.join(brand['topics'])})")

    # --- 출처 목록: id·발행처·자료명·기준일·URL 모두 필수
    srcs = post.get("sources") or []
    known = {}
    if not srcs:
        errors.append("sources(출처 목록)가 비어 있음")
    for j, x in enumerate(srcs, 1):
        tag = f"sources[{j}] {x.get('id', '?')}"
        for k, name in (("id", "id"), ("publisher", "발행처"), ("title", "자료명"), ("date", "기준일"), ("url", "URL")):
            if not str(x.get(k, "")).strip():
                errors.append(f"{tag}: {name}({k}) 누락")
        if x.get("date") and not DATE_RE.match(str(x["date"])):
            errors.append(f"{tag}: date는 YYYY-MM-DD 형식 (현재 {x['date']})")
        if x.get("url") and not str(x["url"]).startswith(("http://", "https://")):
            errors.append(f"{tag}: url은 http(s)://로 시작해야 함")
        if not x.get("accessed"):
            warns.append(f"{tag}: accessed(확인일) 없음 — 기록 권장")
        elif not DATE_RE.match(str(x["accessed"])):
            errors.append(f"{tag}: accessed는 YYYY-MM-DD 형식 (현재 {x['accessed']})")
        elif x.get("date") and DATE_RE.match(str(x["date"])) and x["accessed"] < x["date"]:
            errors.append(f"{tag}: 확인일({x['accessed']})이 기준일({x['date']})보다 앞섬")
        if x.get("id"):
            if x["id"] in known:
                errors.append(f"{tag}: id 중복")
            known[x["id"]] = x

    # --- 슬라이드별 출처 연결
    slides = post["slides"]
    if len(slides) > rules.get("max_slides", 20):
        errors.append(f"슬라이드 {len(slides)}장 — 최대 {rules.get('max_slides', 20)}장")
    need = set(rules.get("source_required_types", []))
    used = set()
    for i, s in enumerate(slides, 1):
        t = s.get("type")
        if "source" in s:
            errors.append(f"slide {i}: 'source' 자유 텍스트는 더 이상 쓰지 않음 → 'src': \"<출처 id>\"로 연결")
        refs = slide_refs(s)
        used.update(refs)
        for r in refs:
            if r not in known:
                errors.append(f"slide {i} ({t}): 등록되지 않은 출처 id '{r}'")
        if t in need and not refs:
            errors.append(f"slide {i} ({t}): src(출처) 누락")
        tk = s.get("ticker") or {}
        if tk.get("value") and not _ids(tk.get("src")):
            errors.append(f"slide {i}: 커버 지표(ticker)에 src 누락")
        for g in s.get("groups") or []:
            for r in g.get("rows") or []:
                if not _ids(r.get("src")):
                    errors.append(f"slide {i}: 시세판 행 '{r.get('name')}'에 src 누락 (행마다 출처 필수)")
        if t == "cover" and len(str(s.get("title", "")).replace("**", "").replace("\n", "")) > 34:
            warns.append(f"slide {i}: 커버 제목이 34자 초과 — 한눈에 안 읽힐 수 있음")
    # --- 번역판 금지: 영어·한국어 원문만 (중복 검열·근거 대조가 영어·한국어 기준. 2026-09-26 스페인어판 오판정 사례)
    for k, x in known.items():
        h = (urlparse(str(x.get("url", ""))).hostname or "").lower()
        if re.match(r"^(es|espanol|fr|de|it|br|mx|ar|co|cl|pe|jp|tw|hk|cn|vn|id|th|tr|ru)\.", h):
            errors.append(f"출처 '{k}': 번역판 페이지({h}) — 영어·한국어 원문 페이지만 쓴다")
    # --- 뉴스 출처: 허용 매체(도메인+발행처)만, 최신 기사만
    outlets = [o for grp in (brand.get("news_outlets") or {}).values() if isinstance(grp, list) for o in grp]
    if outlets:
        for k, x in known.items():
            host_o = outlet_by_url(x.get("url", ""), outlets)
            pub_o = outlet_by_name(x.get("publisher", ""), outlets)
            if not host_o:
                errors.append(f"출처 '{k}': URL 도메인이 허용 매체가 아님 ({urlparse(str(x.get('url', ''))).hostname})")
            if not pub_o:
                errors.append(f"출처 '{k}': 발행처 '{x.get('publisher')}'가 허용 매체 목록에 없음")
            if host_o and pub_o and host_o is not pub_o:
                if not host_o.get("syndication"):
                    errors.append(f"출처 '{k}': {host_o['name']} 도메인에 {pub_o['name']} 발행처 — 전재 허용 호스트가 아님")
                elif not x.get("via"):
                    errors.append(f"출처 '{k}': {host_o['name']}에 전재된 기사 → via: \"{host_o['name']}\" 표기 필요")
    max_age = rules.get("news_max_age_days")
    if max_age is not None and DATE_RE.match(str(post.get("date", ""))):
        oldest = (datetime.date.fromisoformat(post["date"]) - datetime.timedelta(days=max_age)).isoformat()
        for k, x in known.items():
            if DATE_RE.match(str(x.get("date", ""))) and x["date"] < oldest:
                errors.append(f"출처 '{k}': 게재일 {x['date']} — 최신 뉴스 기준({oldest} 이후) 밖")
            if DATE_RE.match(str(x.get("date", ""))) and x["date"] > post["date"]:
                errors.append(f"출처 '{k}': 게재일 {x['date']}이 포스트 날짜 {post['date']}보다 뒤")

    # --- 가격 금지: 카드 텍스트에 가격 표현이 있으면 오류
    if rules.get("price_allowed") is False:
        for i, s in enumerate(slides, 1):
            for txt in iter_text(s):
                m = PRICE_RE.search(txt)
                if m:
                    errors.append(f"slide {i}: 가격 표현 금지 — '{m.group(0)}' (…{txt[max(0, m.start() - 12):m.end() + 12]}…)")
                w = PRICE_WORD_RE.search(txt)
                if w and not m:
                    warns.append(f"slide {i}: 가격 관련 단어 '{w.group(0)}' — 수치 없이 맥락 설명인지 확인 (…{txt[max(0, w.start() - 12):w.end() + 12]}…)")

    for k in known:
        if k not in used:
            warns.append(f"출처 '{k}'가 목록에는 있지만 어느 슬라이드에서도 인용되지 않음")

    tags = post.get("hashtags") or []
    if len(tags) > rules.get("max_hashtags", 5):
        errors.append(f"해시태그 {len(tags)}개 — 최대 {rules.get('max_hashtags', 5)}개")
    cap = build_caption(post)
    if len(cap) > rules.get("max_caption_chars", 2200):
        warns.append(f"캡션 {len(cap)}자 — {rules.get('max_caption_chars', 2200)}자 초과")
    if post.get("sample"):
        errors.append("sample=true — 가상 데이터는 게시용으로 렌더하지 않음 (레이아웃 확인만 --draft)")
    check_evidence(post, brand, run_dir, errors, warns)
    check_coverage(post, brand, errors, warns)
    # 중복 기사 검열 (발행 이력 issues.json 과 비교)
    if history is not None:
        sys.path.insert(0, str(ROOT / "pipeline"))
        import dedup
        e2, w2, _ = dedup.check_post(post, history)
        errors += e2
        warns += w2
    elif rules.get("dedup_required"):
        errors.append("발행 이력이 없어 중복 검사를 못 함 — 키트를 저장소 안(<저장소>/kit)에서 실행하거나 --history 로 저장소 루트를 지정할 것")
    return errors, warns


def check_coverage(post: dict, brand: dict, errors: list, warns: list):
    """뉴스 슬라이드의 coverage(같은 뉴스를 함께 다룬 허용 매체 목록) 점검과 기사 수 한도.
    coverage 는 선정 근거 기록일 뿐 카드 근거가 아니다(카드 숫자·인용은 sources[].evidence 에서만)."""
    rules = brand.get("rules", {})
    outlets = [o for grp in (brand.get("news_outlets") or {}).values() if isinstance(grp, list) for o in grp]
    news = [(i, s) for i, s in enumerate(post.get("slides", []), 1) if s.get("type") == "news"]
    if rules.get("max_news") and len(news) > rules["max_news"]:
        errors.append(f"뉴스 {len(news)}건 — 하루 최대 {rules['max_news']}건 (여러 매체가 함께 다룬 중요 뉴스 위주로 줄일 것)")
    S = {x.get("id"): x for x in post.get("sources") or []}
    for i, s in news:
        cov = s.get("coverage")
        names = set()
        for x in (S.get(r, {}) for r in slide_refs(s)):
            o = outlet_by_name(x.get("publisher", ""), outlets) if x else None
            if o:
                names.add(o["name"])
        if cov is None:
            warns.append(f"slide {i}: coverage(함께 보도한 매체) 기록 없음 — 선정 근거를 남길 것")
        else:
            for c in cov:
                o = outlet_by_name(c.get("publisher", ""), outlets)
                if not o:
                    errors.append(f"slide {i}: coverage 발행처 '{c.get('publisher')}' 는 허용 매체가 아님")
                    continue
                u = c.get("url", "")
                if not str(u).startswith(("http://", "https://")) or not str(c.get("title", "")).strip():
                    errors.append(f"slide {i}: coverage 항목에 title·url 필요 ({c.get('publisher')})")
                    continue
                host_o = outlet_by_url(u, outlets)
                if not host_o or (host_o is not o and not host_o.get("syndication")):
                    errors.append(f"slide {i}: coverage URL 도메인이 발행처 '{o['name']}' 와 맞지 않음 ({u})")
                    continue
                names.add(o["name"])
        if rules.get("min_coverage") and len(names) < rules["min_coverage"]:
            warns.append(f"slide {i}: 함께 보도한 허용 매체 {len(names)}곳 — 기준 {rules['min_coverage']}곳 미만 (RUNBOOK 3단계 예외 사유를 run_log 에 남길 것)")


def build_caption(post: dict) -> str:
    parts = []
    if post.get("sample"):
        parts.append("※ 샘플 포스트 — 가상 데이터이며 실제 수치가 아닙니다.")
    if post.get("caption"):
        parts.append(post["caption"].strip())
    srcs = post.get("sources") or []
    if srcs:
        lines = ["출처"]
        for i, x in enumerate(srcs, 1):
            via = f" (via {x['via']})" if x.get("via") else ""
            line = f"[{i}] {x.get('publisher', '')}{via} — {x.get('title', '')} ({x.get('date', '')})"
            if x.get("url"):
                line += f" {x['url']}"
            lines.append(line)
        parts.append("\n".join(lines))
    tags = post.get("hashtags") or []
    if tags:
        parts.append(" ".join("#" + t.lstrip("#") for t in tags))
    return "\n\n".join(parts)


LEDGER_COLS = ["post_id", "slide", "type", "field", "label", "value", "unit", "change", "basis",
               "source_no", "source_id", "publisher", "source_title", "source_date", "accessed", "url"]


def build_ledger(post: dict):
    """카드에 찍힌 숫자·사실을 한 줄씩, 연결된 출처와 함께 원본 그대로 기록."""
    srcs = post.get("sources") or []
    S = {x.get("id"): (i, x) for i, x in enumerate(srcs, 1)}
    rows = []

    def add(slide, typ, field, label, value="", unit="", change="", basis="", src=None):
        for sid in _ids(src) or [""]:
            n, x = S.get(sid, ("", {}))
            rows.append([post.get("id"), slide, typ, field, label, value, unit, change, basis,
                         n, sid, x.get("publisher", ""), x.get("title", ""), x.get("date", ""),
                         x.get("accessed", ""), x.get("url", "")])

    for i, s in enumerate(post.get("slides", []), 1):
        t = s.get("type")
        sl = _ids(s.get("src"))
        tk = s.get("ticker")
        if tk and tk.get("value"):
            add(i, t, "ticker", tk.get("label", ""), tk.get("value"), tk.get("unit", ""), tk.get("chg", ""), tk.get("vs", ""), tk.get("src"))
            sl_labels = tk.get("spark_labels") or []
            for k, v in enumerate(tk.get("spark") or []):
                add(i, t, "ticker.spark", sl_labels[k] if k < len(sl_labels) else f"#{k + 1}", v, tk.get("unit", ""), src=tk.get("src"))
        if t == "number":
            add(i, t, "value", s.get("headline", "").replace("**", ""), s.get("value", ""), s.get("unit", ""), s.get("chg", ""), s.get("vs", ""), sl)
            ch = s.get("chart") or {}
            labels = ch.get("labels") or []
            for k, v in enumerate(ch.get("values") or []):
                add(i, t, "chart", labels[k] if k < len(labels) else f"#{k + 1}", v, s.get("unit", ""), src=sl)
        if t == "bullets":
            for it in s.get("items") or []:
                add(i, t, "fact", it.get("title", "").replace("**", ""), it.get("desc", "").replace("**", ""), src=_ids(it.get("src")) or sl)
        if t == "table":
            cols = [c.get("name", "") for c in s.get("columns") or []]
            for r in s.get("rows") or []:
                cells = r.get("cells", r) if isinstance(r, dict) else r
                lab = str(cells[0]).replace("|", " ") if cells else ""
                for j, v in enumerate(cells[1:], 1):
                    add(i, t, cols[j] if j < len(cols) else f"col{j}", lab, v, src=(_ids(r.get("src")) if isinstance(r, dict) else []) or sl)
        if t == "news":
            hl = s.get("headline", "").replace("**", "").replace("\n", " ")
            for v in s.get("viz") or []:
                vs = _ids(v.get("src")) or sl
                vt = v.get("type", "")
                for it in v.get("items") or []:
                    add(i, t, f"viz.{vt}", it.get("k") or it.get("label", ""), it.get("v") or f"{it.get('value', '')}{it.get('unit', '')}" + (" (계산값)" if it.get("calc") else ""), src=vs)
                for p_ in v.get("parts") or []:
                    add(i, t, f"viz.{vt}", p_.get("label", ""), f"{p_.get('value')}{v.get('unit', '')}" + (" (계산값)" if p_.get("calc") else ""), src=vs)
                for e in v.get("events") or []:
                    add(i, t, f"viz.{vt}", e.get("d", ""), e.get("t", ""), src=vs)
                for r in v.get("rows") or []:
                    for b in r.get("bars") or []:
                        add(i, t, f"viz.{vt}", f"{r.get('label', '')} {b.get('label', '')}", f"{b.get('from')}~{b.get('to')}" + (" (추정)" if b.get("kind") in ("est", "opt") else ""), src=_ids(r.get("src")) or vs)
                if vt == "gauge":
                    add(i, t, "viz.gauge", v.get("label", ""), v.get("display", ""), src=vs)
            for f in s.get("facts") or []:
                add(i, t, "fact", s.get("headline", "").replace("**", "").replace("\n", " "), f.get("t", "").replace("**", ""), src=_ids(f.get("src")) or sl)
        if t == "bars":
            for b in s.get("bars") or []:
                add(i, t, "bar", f"{b.get('label', '')} {b.get('sub', '')}".strip(), b.get("value", ""), s.get("unit", ""), src=_ids(b.get("src")) or sl)
        if t == "board":
            for g in s.get("groups") or []:
                for r in g.get("rows") or []:
                    add(i, t, g.get("category", ""), r.get("name", ""), r.get("value", ""), r.get("unit", ""), r.get("chg", ""), s.get("asof", ""), r.get("src"))
    return rows


IG_RATIOS = {"1:1": 1.0, "4:5": 0.8, "3:4": 0.75, "1.91:1": 1.91}


def png_size(p: Path):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def to_jpeg(pngs, brand):
    """인스타 API용 JPEG(sRGB, 4:4:4) 사본. PNG는 보관용."""
    from PIL import Image
    q = brand.get("instagram", {}).get("jpeg_quality", 95)
    out = []
    for p in pngs:
        j = p.with_suffix(".jpg")
        Image.open(p).convert("RGB").save(j, "JPEG", quality=q, subsampling=0, optimize=True)
        out.append(j)
    return out


def check_jpegs(jpgs, brand):
    ig = brand.get("instagram", {})
    probs = []
    for j in jpgs:
        with open(j, "rb") as f:
            if f.read(3) != b"\xff\xd8\xff":
                probs.append(f"{j.name}: JPEG 아님")
        mb = j.stat().st_size / 1024 / 1024
        if mb > ig.get("max_file_mb", 8):
            probs.append(f"{j.name}: {mb:.1f}MB — {ig.get('max_file_mb', 8)}MB 초과")
    return probs


def check_instagram(pngs, brand, post):
    """인스타그램 캐러셀 규격: 폭 1080, 허용 비율, 모든 장 같은 크기, 최대 장수, 캡션·해시태그."""
    ig = brand.get("instagram", {})
    probs = []
    if not pngs:
        return ["슬라이드 없음"]
    if len(pngs) > ig.get("max_slides", 20):
        probs.append(f"{len(pngs)}장 — 캐러셀 최대 {ig.get('max_slides', 20)}장")
    sizes = {p.name: png_size(p) for p in pngs}
    if len(set(sizes.values())) > 1:
        probs.append(f"슬라이드 크기가 서로 다름 {sizes} — 캐러셀은 첫 장 비율로 잘림")
    w, h = next(iter(sizes.values()))
    if w != ig.get("max_width", 1080):
        probs.append(f"폭 {w}px — 인스타 표시 폭 {ig.get('max_width', 1080)}px로 맞출 것")
    allowed = {k: v for k, v in IG_RATIOS.items() if k in ig.get("allowed_ratios", IG_RATIOS)}
    if not any(abs(w / h - r) < 0.002 for r in allowed.values()):
        probs.append(f"비율 {w}x{h} — 허용 비율({', '.join(allowed)}) 아님")
    want = (brand["size"]["width"], brand["size"]["height"])
    if (w, h) != want:
        probs.append(f"렌더 크기 {w}x{h}가 설정 {want[0]}x{want[1]}과 다름")
    return probs


EVIDENCE_COLS = ["post_id", "source_no", "source_id", "publisher", "via", "source_title", "source_date", "url",
                 "quote_no", "quote", "in_saved_extract", "extract_file"]


def build_evidence(post: dict, run_dir):
    rows = []
    for n, x in enumerate(post.get("sources") or [], 1):
        ap = article_path(run_dir, x.get("id"))
        body = _qnorm(ap.read_text(encoding="utf-8")) if ap else None
        for k, e in enumerate(x.get("evidence") or [], 1):
            found = "-" if body is None else ("Y" if _qnorm(e) in body else "N")
            rows.append([post.get("id"), n, x.get("id"), x.get("publisher", ""), x.get("via", ""), x.get("title", ""),
                         x.get("date", ""), x.get("url", ""), k, e, found, str(ap.relative_to(ROOT)) if ap else ""])
    return rows


def write_xlsx(path: Path, sheets):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        return False
    wb = Workbook()
    wb.remove(wb.active)
    for name, cols, rows in sheets:
        ws = wb.create_sheet(name)
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append(r)
        ws.freeze_panes = "A2"
        for col in ws.columns:
            w = max(len(str(c.value or "")) for c in col[:200])
            ws.column_dimensions[col[0].column_letter].width = min(max(10, w * 0.9), 80)
        if name == "evidence":
            for row in ws.iter_rows(min_row=2):
                row[9].alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)
    return True


def contact_sheet(page, pngs, out: Path, w: int, h: int):
    cols = 3
    tw = 340
    th = int(tw * h / w)
    imgs = "".join(
        f'<figure><img src="{p.as_uri()}" width="{tw}" height="{th}"><figcaption>{p.stem}</figcaption></figure>'
        for p in pngs
    )
    html = f"""<html><body style="margin:0;background:#05070A;font-family:monospace;color:#7D8898">
    <div style="display:grid;grid-template-columns:repeat({cols},{tw}px);gap:22px;padding:28px">{imgs}</div>
    <style>figure{{margin:0}}img{{display:block;border-radius:10px;border:1px solid #1F2733}}figcaption{{font-size:13px;margin-top:6px}}</style>
    </body></html>"""
    sheet = out / "_sheet.html"
    sheet.write_text(html, encoding="utf-8")
    page.set_viewport_size({"width": cols * tw + (cols - 1) * 22 + 56, "height": 400})
    page.goto(sheet.as_uri())
    page.wait_for_load_state("load")
    page.screenshot(path=str(out / "preview.png"), full_page=True)
    sheet.unlink()


def theme_for(post: dict, brand: dict) -> str:
    """카드 테마: 포스트에 theme 이 있으면 그것, 없으면 brand.theme_rotation 을 호수로 돌린다 (No.1 다크, No.2 라이트 …)."""
    if post.get("theme") in ("dark", "light"):
        return post["theme"]
    rot = brand.get("theme_rotation") or ["dark"]
    try:
        n = int(post.get("issue") or 1)
    except (TypeError, ValueError):
        n = 1
    return rot[(n - 1) % len(rot)]


def render(post_paths, out_dir: Path, draft: bool, ratio: str | None, runs: Path = ROOT / "runs", history=None):
    brand = load_json(ROOT / "brand.json")
    if ratio == "3:4":
        brand["size"] = {"width": 1080, "height": 1440}
    elif ratio == "4:5":
        brand["size"] = {"width": 1080, "height": 1350}
    W, H = brand["size"]["width"], brand["size"]["height"]
    ok = True
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W + 80, "height": H + 80}, device_scale_factor=1)
        for pp in post_paths:
            pp = Path(pp)
            post = load_json(pp)
            run_dir = Path(runs) / str(post.get("date", ""))
            errors, warns = validate(post, brand, run_dir if run_dir.exists() else None, load_history(history))
            print(f"\n■ {pp.name}")
            for w_ in warns:
                print(f"  ! {w_}")
            for e in errors:
                print(f"  ✗ {e}")
            if errors and not draft:
                print("  → 오류가 있어 렌더하지 않음 (초안 확인은 --draft)")
                ok = False
                continue
            page.goto(TEMPLATE.as_uri())
            page.evaluate(
                """async () => { await Promise.all([
                    document.fonts.load('800 40px Pretendard'), document.fonts.load('500 40px Pretendard'),
                    document.fonts.load('700 40px InterLatin'), document.fonts.load('500 40px InterLatin')]);
                  await document.fonts.ready; }"""
            )
            theme = theme_for(post, brand)
            print(f"  테마: {theme}")
            res = page.evaluate("([p, b]) => window.renderPost(p, b)", [post, {**brand, "theme": theme}])
            page.evaluate("document.fonts.ready")
            for w_ in res["warnings"]:
                print(f"  ! 레이아웃: {w_}")
            out = out_dir / post["id"]
            out.mkdir(parents=True, exist_ok=True)
            for old in out.glob("*.png"):
                old.unlink()
            pngs = []
            for old in out.glob("*.jpg"):
                old.unlink()
            for i, el in enumerate(page.query_selector_all(".card"), 1):
                p = out / f"{i:02d}.png"
                el.screenshot(path=str(p))
                pngs.append(p)
            jpgs = to_jpeg(pngs, brand)
            ig_problems = check_instagram(pngs, brand, post) + check_jpegs(jpgs, brand)
            for m in ig_problems:
                print(f"  ✗ 인스타 규격: {m}")
            if ig_problems:
                ok = False
            (out / "caption.txt").write_text(build_caption(post), encoding="utf-8")
            with open(out / "data_sources.csv", "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(LEDGER_COLS)
                ledger = build_ledger(post)
                w.writerows(ledger)
            evid = build_evidence(post, run_dir if run_dir.exists() else None)
            with open(out / "evidence.csv", "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(EVIDENCE_COLS)
                w.writerows(evid)
            write_xlsx(out / "ledger.xlsx", [("data_sources", LEDGER_COLS, ledger), ("evidence", EVIDENCE_COLS, evid)])
            contact_sheet(page, pngs, out, W, H)
            print(f"  ✓ {len(pngs)}장 → {out}")
        browser.close()
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="원재료 카드뉴스 렌더러")
    ap.add_argument("posts", nargs="+", help="포스트 JSON 경로")
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--draft", action="store_true", help="오류가 있어도 초안으로 렌더")
    ap.add_argument("--ratio", choices=["3:4", "4:5"], default=None, help="기본: brand.json size (인스타 3:4)")
    ap.add_argument("--runs", default=str(ROOT / "runs"), help="원문 발췌 폴더 루트 (runs/<날짜>/articles/<출처 id>.md)")
    ap.add_argument("--check", action="store_true", help="검증만 하고 렌더하지 않음")
    ap.add_argument("--history", default=None, help="발행 이력: 저장소 루트 폴더 또는 issues.json (기본: 키트가 저장소 안이면 저장소 게시 기록)")
    a = ap.parse_args()
    if a.check:
        brand = load_json(ROOT / "brand.json")
        bad = False
        for pp in a.posts:
            post = load_json(Path(pp))
            rd = Path(a.runs) / str(post.get("date", ""))
            errors, warns = validate(post, brand, rd if rd.exists() else None, load_history(a.history))
            print(f"\n■ {Path(pp).name}")
            for w_ in warns:
                print(f"  ! {w_}")
            for e in errors:
                print(f"  ✗ {e}")
            print("  ✓ 검증 통과" if not errors else f"  → 오류 {len(errors)}건")
            bad |= bool(errors)
        sys.exit(1 if bad else 0)
    sys.exit(0 if render(a.posts, Path(a.out), a.draft, a.ratio, Path(a.runs), a.history) else 1)
