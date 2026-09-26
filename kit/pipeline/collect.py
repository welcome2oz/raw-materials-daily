#!/usr/bin/env python3
"""RAW MATERIALS DAILY — 뉴스 후보 수집기

Claude 세션이 WebFetch로 읽어 저장한 채널 결과(runs/<날짜>/raw/*.json)를 합쳐
허용 매체·게재일·가격기사 제외·카테고리 분류를 적용하고 후보 목록을 만든다.
네트워크를 쓰지 않는다(클라우드 셸은 뉴스 사이트 접근이 막혀 있기 때문).

사용법
  python pipeline/collect.py 2026-09-25            # runs/2026-09-25/raw/*.json → candidates.json/.md
  python pipeline/collect.py 2026-09-25 --top 4     # 카테고리별 상위 4건까지 표시

raw 파일 형식 (채널 1개 = 파일 1개)
  {"channel": "bing-copper", "url": "...", "fetched_at": "2026-09-25T06:02:00+09:00",
   "items": [{"title": "...", "url": "...", "published": "...", "source": "...", "snippet": "..."}]}

출력
  runs/<날짜>/candidates.json   후보(included) + 제외(excluded, 사유 포함)
  runs/<날짜>/candidates.md     사람이 읽는 표
"""
import argparse
import datetime as dt
import email.utils
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dedup  # noqa: E402
KST = dt.timezone(dt.timedelta(hours=9))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ---------- URL ----------
TRACK = re.compile(r"^(utm_|guccounter|guce_|ncid|fbclid|gclid|mc_|cmpid|taid|yptr|soc_)", re.I)


def clean_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    p = urlparse(u)
    host = (p.hostname or "").lower()
    # Bing News 리다이렉트: apiclick.aspx?...&url=<원문>
    if host.endswith("bing.com") and "url" in parse_qs(p.query):
        return clean_url(unquote(parse_qs(p.query)["url"][0]))
    # Google News 등 기타 리다이렉트의 url= 파라미터
    q = parse_qs(p.query)
    if "url" in q and q["url"][0].startswith("http"):
        return clean_url(q["url"][0])
    keep = [(k, v) for k, vs in q.items() for v in vs if not TRACK.match(k)]
    return urlunparse((p.scheme or "https", p.netloc.lower(), p.path.rstrip("/") or "/", "", urlencode(keep), ""))


# ---------- 날짜 ----------
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


KR_HOSTS = (".kr", "hankyung.com", "snmnews.com")


def parse_date(s: str, url: str = ""):
    """다양한 날짜 문자열 → datetime(aware). 시간대가 없으면 한국 매체는 KST, 그 밖은 UTC. 실패 시 URL의 /YYYY/MM/DD/ 로 보조."""
    host = (urlparse(url or "").hostname or "").lower()
    tz0 = KST if host.endswith(KR_HOSTS) else dt.timezone.utc
    d = _parse_date(s, url)
    return d.replace(tzinfo=tz0) if d is not None and d.tzinfo is None else d


def _parse_date(s: str, url: str = ""):
    s = (s or "").strip()
    if s:
        try:  # RFC 822 (RSS pubDate)
            return email.utils.parsedate_to_datetime(s)
        except Exception:
            pass
        try:  # ISO 8601 · 2026-09-24 16:54:23
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            pass
        m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
        if m:
            return dt.datetime(int(m[1]), int(m[2]), int(m[3]))
        m = re.match(r"(\d{2})\.(\d{2})\.(\d{2})(?:\s+(\d{1,2}):(\d{2}))?", s)  # 이데일리 26.09.19 07:00
        if m:
            return dt.datetime(2000 + int(m[1]), int(m[2]), int(m[3]), int(m[4] or 0), int(m[5] or 0))
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?,?\s+(\d{4})", s)  # 23 Sep 2026
        if m and m[2].lower()[:3] in MONTHS:
            return dt.datetime(int(m[3]), MONTHS[m[2].lower()[:3]], int(m[1]))
        m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", s)  # Sep 23, 2026
        if m and m[1].lower()[:3] in MONTHS:
            return dt.datetime(int(m[3]), MONTHS[m[1].lower()[:3]], int(m[2]))
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", url or "")
    if m:
        return dt.datetime(int(m[1]), int(m[2]), int(m[3]))
    return None


# ---------- 매체 ----------
def _norm(t):
    return re.sub(r"[^0-9a-z가-힣&]", "", str(t).lower())


def outlets_of(brand):
    return [o for grp in (brand.get("news_outlets") or {}).values() if isinstance(grp, list) for o in grp]


def outlet_by_url(url, outlets):
    host = (urlparse(url).hostname or "").lower()
    for o in outlets:
        for d in o.get("domains", []):
            if host == d or host.endswith("." + d):
                return o
    return None


def outlet_by_name(name, outlets):
    n = _norm(name)
    if not n:
        return None
    for o in outlets:
        names = {_norm(a) for a in [o["name"]] + o.get("aliases", [])}
        if n in names or any(len(a) > 3 and a in n for a in names):
            return o
    return None


def prefer_allowed_link(rec, outlets, readable_hosts):
    """같은 기사로 묶인 링크 중 허용 매체 도메인(본문 읽기 가능하면 더 우선)을 대표 링크로 삼는다.
    예: Bing이 준 aol.com 링크가 먼저 모였어도 mining.com/web/ 전재본을 대표로 (2026-09-26 페루 구리 기사 누락 사례)."""
    alts = rec.pop("_alts", [])
    if not alts:
        return

    def rank(a):
        host = (urlparse(a["url"]).hostname or "").lower()
        readable = any(host == h or host.endswith("." + h) for h in readable_hosts)
        return (1 if outlet_by_url(a["url"], outlets) else 0, 1 if readable else 0)
    cur = {k: rec[k] for k in ("url", "source", "published_raw", "snippet")}
    best = max([cur] + alts, key=rank)  # 동점이면 먼저 모인 링크 유지
    if best is cur:
        return
    rec.update({k: best[k] for k in ("url", "source", "published_raw")})
    rec["snippet"] = rec["snippet"] or best["snippet"]
    rec["alt_urls"] = [a["url"] for a in [cur] + alts if a["url"] != best["url"]]


# ---------- 키워드 ----------
def has(text, word):
    w = re.escape(word.lower())
    return re.search(rf"(?<![a-z0-9]){w}(?:s|es)?(?![a-z0-9])", text) is not None


def hits(text, words):
    return [w for w in words if has(text, w)]


def classify(item, kw):
    text = f"{item['title']} {item.get('snippet', '')}".lower()
    title = item["title"].lower()
    cats = {}
    off = hits(text, kw.get("off_commodity", []))
    for c, d in kw["categories"].items():
        strong = hits(text, d.get("strong", []))
        names = hits(text, d.get("names", []))
        # 회사 이름만 걸리고 다른 광종(석탄·금·리튬 등) 기사면 제외 — 예: Glencore 석탄 광산
        if strong or (names and not off):
            cats[c] = strong + names
    tops = {}
    for t, d in kw["topics"].items():
        h = hits(text, d["words"])
        if h:
            tops[t] = h
    ph = kw["price_headline"]
    price = hits(title, ph["words"])
    event = hits(title, ph["event_override"])
    ex = hits(title, kw["exclude"]["title_words"])
    return cats, tops, price, event, ex


# ---------- 같은 뉴스 묶기 (함께 보도한 허용 매체 수 = 중요도) ----------
def _feat(rec):
    t = rec["title"] + " " + rec.get("snippet", "")
    return set(dedup.entities(t)), set(dedup.events(t))


def cluster_candidates(inc, outlets):
    """오늘 후보끼리 같은 사건을 묶는다: 고유명사(한글 표기↔영문 포함) 겹침이 작은 쪽의 절반 이상이고,
    양쪽 모두 사건 단어가 있으면 하나 이상 같아야 한다. 묶음마다 서로 다른 허용 매체 수 = coverage."""
    n = len(inc)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    F = [_feat(r) for r in inc]
    for i in range(n):
        for j in range(i + 1, n):
            (ea, va), (eb, vb) = F[i], F[j]
            shared = ea & eb
            if not shared or len(shared) / max(1, min(len(ea), len(eb))) < 0.5:
                continue
            if va and vb and not (va & vb):
                continue
            parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    names = {o["name"] for o in outlets}
    clusters = []
    for k, (root, idx) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])), 1):
        members = [inc[i] for i in idx]
        outs = []
        for r in members:
            pub = r.get("publisher_hint", "")
            name = pub if pub in names else ("" if (outlet_by_url(r["url"], outlets) or {}).get("syndication") else r.get("outlet", ""))
            if name and name not in outs:
                outs.append(name)
        cid = f"c{k}"
        for r in members:
            r["cluster"] = cid
            r["coverage"] = len(outs)
            r["coverage_outlets"] = outs
            r["score"] += 3 * max(0, len(outs) - 1)
        clusters.append({"id": cid, "coverage": len(outs), "outlets": outs, "category": members[0].get("category", ""),
                         "items": [{"title": r["title"], "outlet": r.get("outlet", ""), "publisher": r.get("publisher_hint", ""),
                                    "url": r["url"], "published": r.get("published", ""), "access": r.get("access", "")} for r in members]})
    clusters.sort(key=lambda c: (-c["coverage"], -len(c["items"])))
    return clusters


# ---------- 메인 ----------
def main():
    ap = argparse.ArgumentParser(description="뉴스 후보 수집기 (raw → candidates)")
    ap.add_argument("date", help="포스트 날짜 YYYY-MM-DD (KST 기준 발행일)")
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--history", default=None, help="발행 이력: issues.json 파일 또는 GitHub 저장소 루트 폴더 (기본: 키트가 저장소 안이면 저장소, 아니면 issues.json)")
    a = ap.parse_args()
    if not a.history:
        r = ROOT.parent
        in_repo = ROOT.name == "kit" and (r / "issues").is_dir() and (r / "published").is_dir()
        a.history = str(r if in_repo else ROOT / "issues.json")

    brand = load(ROOT / "brand.json")
    kw = load(ROOT / "pipeline" / "keywords.json")
    outlets = outlets_of(brand)
    max_age = brand.get("rules", {}).get("news_max_age_days", 1)
    post_day = dt.date.fromisoformat(a.date)
    oldest = post_day - dt.timedelta(days=max_age)

    run = Path(a.runs) / a.date
    raws = sorted((run / "raw").glob("*.json"))
    if not raws:
        print(f"✗ {run/'raw'}에 채널 결과가 없음 — RUNBOOK 2단계(WebFetch 저장) 먼저", file=sys.stderr)
        sys.exit(2)

    channel_stats, seen, inc, exc = [], {}, [], []
    if a.history and Path(a.history).is_dir():  # GitHub 저장소 루트 → 게시된 호만 이력으로
        sys.path.insert(0, str(ROOT))
        from render import history_from_repo
        hist = history_from_repo(Path(a.history))
    else:
        hist = json.loads(Path(a.history).read_text(encoding="utf-8")) if Path(a.history).exists() else {"issues": []}
    prior = dedup.prior_stories(hist, a.date)
    used = {clean_url(s.get("url", "")) for e in hist.get("issues", []) if e.get("date", "") < a.date for s in e.get("sources", [])}
    used |= {clean_url(u) for st in prior for u in st.get("urls", [])}
    bad_pubs = {_norm(p) for p in kw["exclude"]["publishers"]}
    access = kw.get("access", {})

    for rp in raws:
        try:
            raw = load(rp)
        except Exception as e:  # 저장 형식 오류
            channel_stats.append({"channel": rp.stem, "items": 0, "error": f"JSON 읽기 실패: {e}"})
            continue
        items = raw.get("items") or []
        channel_stats.append({"channel": raw.get("channel", rp.stem), "items": len(items), "fetched_at": raw.get("fetched_at", ""), "error": raw.get("error", "")})
        for it in items:
            title = re.sub(r"\s+", " ", str(it.get("title", ""))).strip()
            url = clean_url(it.get("url", ""))
            if not title or not url:
                continue
            rec = {"title": title, "url": url, "published_raw": it.get("published", ""), "source": (it.get("source") or "").strip(),
                   "snippet": (it.get("snippet") or "").strip()[:300], "channels": [raw.get("channel", rp.stem)]}
            key = url
            if key in seen:  # 같은 URL
                seen[key]["channels"] = sorted(set(seen[key]["channels"] + rec["channels"]))
                continue
            tnorm = set(re.findall(r"[a-z0-9]+", title.lower()))
            dup = next((s for s in seen.values() if len(tnorm & s["_tok"]) / max(1, len(tnorm | s["_tok"])) >= 0.7), None)
            rec["_tok"] = tnorm
            if dup:  # 같은 기사 다른 URL(전재본 등) → 대체 링크로 보관
                if url != dup["url"] and url not in dup.get("alt_urls", []):
                    dup.setdefault("alt_urls", []).append(url)
                    dup.setdefault("_alts", []).append({k: rec[k] for k in ("url", "source", "published_raw", "snippet")})
                dup["channels"] = sorted(set(dup["channels"] + rec["channels"]))
                continue
            seen[key] = rec

    for rec in seen.values():
        prefer_allowed_link(rec, outlets, access.get("readable", []))
        reasons = []
        host = (urlparse(rec["url"]).hostname or "").lower()
        host_o = outlet_by_url(rec["url"], outlets)
        src_o = outlet_by_name(rec["source"], outlets) if rec["source"] else None
        rec["host"] = host
        rec["outlet"] = host_o["name"] if host_o else ""
        if not host_o:
            reasons.append(f"허용 매체 도메인 아님({host})")
        if _norm(rec["source"]) in bad_pubs or any(b and b in _norm(rec["source"]) for b in bad_pubs):
            reasons.append(f"제외 발행처({rec['source']})")
        if host.endswith("mining.com") and not urlparse(rec["url"]).path.startswith("/web/"):
            rec["publisher_hint"] = "MINING.COM"  # 자체 기사
        elif host_o and host_o.get("syndication"):
            rec["publisher_hint"] = src_o["name"] if src_o and src_o is not host_o else "확인 필요(본문에서 원 발행처 확인)"
        elif host_o:
            rec["publisher_hint"] = host_o["name"]
        d = parse_date(rec["published_raw"], rec["url"])
        rec["published"] = d.isoformat() if d else ""
        if not d:
            reasons.append("게재일 불명(본문에서 확인 필요)")
            rec["date_unknown"] = True
        else:
            dk = d.astimezone(KST).date()  # 한국 발행 기준으로 창을 잡되
            du = d.astimezone(dt.timezone.utc).date()  # 현지(UTC) 날짜도 허용
            if max(dk, du) < oldest or min(dk, du) > post_day:
                reasons.append(f"게재일 범위 밖({du.isoformat()}, 허용 {oldest.isoformat()}~{post_day.isoformat()})")
        cats, tops, price, event, ex = classify(rec, kw)
        rec["categories"] = cats
        rec["topics"] = tops
        if not cats:
            reasons.append("4개 카테고리 키워드 없음")
        if price and not event:
            reasons.append(f"가격 기사 추정({', '.join(price)})")
        if ex:
            reasons.append(f"제외 유형({', '.join(ex)})")
        if re.search(r"\((?:NYSE|NASDAQ|NASDAQ:)?\s?[A-Z]{2,5}\)", rec["title"]):
            reasons.append("종목 기사 추정(제목에 티커)")
        rec["access"] = "readable" if any(host == h or host.endswith("." + h) for h in access.get("readable", [])) else (
            "blocked" if any(host == h or host.endswith("." + h) for h in access.get("blocked", [])) else "unknown")
        if rec["access"] == "blocked":
            rec["note"] = "본문 접근 불가 도메인 → 같은 기사의 Yahoo Finance·MINING.COM 전재본을 찾아서 사용"
        tw = sum(kw["topics"][t]["weight"] for t in tops)
        rec["score"] = sum(len(v) for v in cats.values()) + tw + (1 if rec["access"] == "readable" else 0) + (len(rec["channels"]) - 1)
        rec["category"] = max(cats, key=lambda c: len(cats[c])) if cats else ""
        rec["topic"] = max(tops, key=lambda t: kw["topics"][t]["weight"] * len(tops[t])) if tops else ""
        rec.pop("_tok", None)
        # 날짜 불명은 '확인 필요'로 후보에 남긴다(다른 사유가 없을 때)
        if rec["url"] in used or any(u in used for u in rec.get("alt_urls", [])):
            reasons.append("이미 발행한 기사(URL)")
        feat = {"entities": sorted(dedup.entities(rec["title"] + " " + rec["snippet"])), "events": sorted(dedup.events(rec["title"] + " " + rec["snippet"]))}
        best = max(((dedup.score(feat, st)[0], st) for st in prior), key=lambda x: x[0], default=(0, None))
        if best[1] is not None and best[0] >= dedup.SAME_STORY:
            st = best[1]
            rec["same_story_as"] = {"date": st["date"], "story_id": st.get("story_id"), "headline": st.get("headline"), "score": best[0]}
            rec["note"] = (rec.get("note", "") + f" / {st['date']} 발행 '{st.get('headline')}'과 같은 사건 추정 → 본문에서 새 사실이 있을 때만 후속(update_of)으로, 없으면 제외").strip(" /")
            rec["score"] -= 3
        hard = [r for r in reasons if not r.startswith("게재일 불명")]
        (exc if hard else inc).append({**rec, "reasons": reasons})

    clusters = cluster_candidates(inc, outlets)
    inc.sort(key=lambda r: (r["category"], -r["score"], r["published"] or ""), reverse=False)
    order = ["nonferrous", "steel", "resin", "chemical"]
    inc.sort(key=lambda r: (order.index(r["category"]) if r["category"] in order else 9, -r["score"]))
    out = {"date": a.date, "window": [oldest.isoformat(), post_day.isoformat()], "generated_at": dt.datetime.now(KST).isoformat(timespec="seconds"),
           "channels": channel_stats, "clusters": clusters, "included": inc, "excluded": exc}
    (run / "candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 사람이 읽는 표
    L = [f"# 후보 기사 — {a.date} (게재일 {oldest}~{post_day})", "", "## 채널", "", "| 채널 | 항목 수 | 오류 |", "|---|---:|---|"]
    L += [f"| {c['channel']} | {c['items']} | {c.get('error', '')} |" for c in channel_stats]
    L += ["", "## 여러 매체가 함께 다룬 뉴스 (중요도 순)", "",
          "같은 사건을 다룬 허용 매체 수(coverage)가 많을수록 중요. 자동 묶음은 고유명사·사건 단어 기준이라 틀릴 수 있다 — 3단계에서 제목을 보고 확인·합산한다.",
          "이런 뉴스가 없는 카테고리는 아래 카테고리별 후보에서 3단계 '유용한 단독 보도' 기준에 맞는 기사로 채운다.", ""]
    multi = [c for c in clusters if c["coverage"] >= 2]
    if not multi:
        L.append("- 2곳 이상이 함께 다룬 뉴스 없음")
    for c in multi[:15]:
        L.append(f"- **[{c['coverage']}곳] {c['items'][0]['title']}** ({c['category']}, {c['id']}) — {', '.join(c['outlets'])}")
        for it in c["items"]:
            L.append(f"  - {it['outlet'] or it['publisher']} · {it['published'][:16]} · 접근 {it['access']} · {it['title'][:80]} — {it['url']}")
    for c in order:
        rows = [r for r in inc if r["category"] == c][: a.top]
        L += ["", f"## {c} ({len([r for r in inc if r['category'] == c])}건 중 상위 {len(rows)})", ""]
        if not rows:
            L.append("- 후보 없음 → 이 카테고리는 오늘 생략")
        for r in rows:
            flag = " ⚠ 게재일 확인" if r.get("date_unknown") else ""
            L.append(f"- **{r['title']}** — {r['outlet']} / 발행처: {r.get('publisher_hint', '')} / {r['published'][:16]} / 토픽 {r['topic']} / 함께 보도 {max(1, r.get('coverage', 1))}곳({r.get('cluster', '')}){' — 단독' if r.get('coverage', 1) <= 1 else ''} / 점수 {r['score']} / 접근 {r['access']}{flag}")
            L.append(f"  - {r['url']}")
            if r.get("note"):
                L.append(f"  - {r['note']}")
    L += ["", f"## 제외 {len(exc)}건 (사유)", ""]
    L += [f"- {r['title'][:90]} — {'; '.join(r['reasons'])}" for r in exc[:80]]
    (run / "candidates.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"■ 후보 {len(inc)}건 / 제외 {len(exc)}건 / 2곳 이상 함께 보도 {len(multi)}묶음 → {run/'candidates.md'}")
    for c in order:
        n = len([r for r in inc if r["category"] == c])
        print(f"  {c:<11} {n}건")
    for c in channel_stats:
        if c.get("error") or not c["items"]:
            print(f"  ! 채널 {c['channel']}: {c.get('error') or '항목 0'}")


if __name__ == "__main__":
    main()
