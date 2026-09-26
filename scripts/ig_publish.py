#!/usr/bin/env python3
"""RAW MATERIALS DAILY — 인스타그램 자동 게시 (GitHub Actions에서 실행)

Instagram 공식 Content Publishing API (Instagram API with Instagram Login, graph.instagram.com)
  1) 이미지마다 캐러셀 항목 컨테이너 생성   POST /{IG_ID}/media  image_url, is_carousel_item=true
  2) 캐러셀 컨테이너 생성                    POST /{IG_ID}/media  media_type=CAROUSEL, children, caption
  3) 상태 확인                               GET  /{container}?fields=status_code  (FINISHED 대기)
  4) 게시                                    POST /{IG_ID}/media_publish  creation_id
  5) 기록                                    published/<날짜>.json (media id·permalink) → 같은 날 두 번 게시하지 않음
                                             (인스타에서 지운 게시물은 기록에 "withdrawn": true 를 넣으면 같은 날짜로 다시 게시)

필요한 저장소 Secrets: IG_ACCESS_TOKEN, IG_USER_ID
이미지 주소: https://raw.githubusercontent.com/<저장소>/<커밋>/issues/<날짜>/NN.jpg (공개 저장소라 Meta가 내려받을 수 있음)

  python scripts/ig_publish.py --date 2026-09-25            # 07:00(KST)까지 기다렸다 게시
  python scripts/ig_publish.py --date 2026-09-25 --now      # 바로 게시
  python scripts/ig_publish.py --date 2026-09-25 --dry-run  # 점검만 (API 호출 없음)
"""
import argparse
import datetime as dt
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = dt.timezone(dt.timedelta(hours=9))
API = os.environ.get("IG_API_BASE") or f"https://graph.instagram.com/{os.environ.get('IG_API_VERSION', 'v25.0')}"
SPEC = {"width": 1080, "height": 1350, "max_slides": 10, "max_mb": 8, "max_caption": 2200, "max_hashtags": 5}


def log(*a):
    print(dt.datetime.now(KST).strftime("%H:%M:%S"), *a, flush=True)


def jpeg_size(p: Path):
    """JPEG SOF 마커에서 (폭, 높이)."""
    b = p.read_bytes()
    if b[:3] != b"\xff\xd8\xff":
        raise ValueError(f"{p.name}: JPEG 아님")
    i = 2
    while i < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        seg = struct.unpack(">H", b[i + 2:i + 4])[0]
        i += 2 + seg
    raise ValueError(f"{p.name}: 크기를 읽을 수 없음")


def check(day: Path, ready: dict):
    probs = []
    slides = ready.get("slides") or []
    if not 1 <= len(slides) <= SPEC["max_slides"]:
        probs.append(f"슬라이드 {len(slides)}장 — 1~{SPEC['max_slides']}장이어야 함 (API 캐러셀 한도)")
    for s in slides:
        p = day / s
        if not p.exists():
            probs.append(f"{s} 없음")
            continue
        try:
            w, h = jpeg_size(p)
            if (w, h) != (SPEC["width"], SPEC["height"]):
                probs.append(f"{s}: {w}x{h} — {SPEC['width']}x{SPEC['height']}(4:5)이어야 함")
        except ValueError as e:
            probs.append(str(e))
        if p.stat().st_size > SPEC["max_mb"] * 1024 * 1024:
            probs.append(f"{s}: {SPEC['max_mb']}MB 초과")
    cap = (day / ready.get("caption_file", "caption.txt")).read_text(encoding="utf-8").strip()
    if len(cap) > SPEC["max_caption"]:
        probs.append(f"캡션 {len(cap)}자 — {SPEC['max_caption']}자 초과")
    tags = re.findall(r"#[^\s#]+", cap)
    if len(tags) > SPEC["max_hashtags"]:
        probs.append(f"해시태그 {len(tags)}개 — {SPEC['max_hashtags']}개 초과")
    if ready.get("errors", 1) != 0 or not ready.get("validated"):
        probs.append("검증을 통과하지 않은 포스트 (ready.json validated/errors)")
    return probs, cap


def call(method, path, params=None, token=None):
    url = f"{API}/{path}"
    data = None
    if method == "GET" and params:
        url += "?" + urllib.parse.urlencode(params)
    elif params:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} → HTTP {e.code}: {body[:500]}") from None


def wait_finished(cid, token, label, limit=300):
    t0 = time.time()
    while True:
        st = call("GET", cid, {"fields": "status_code"}, token).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"{label} 컨테이너 상태 {st}")
        if time.time() - t0 > limit:
            raise RuntimeError(f"{label} 컨테이너가 {limit}초 안에 준비되지 않음 (마지막 상태 {st})")
        time.sleep(5)


def url_ok(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30) as r:
            return r.status == 200, r.headers.get("Content-Type", "")
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(KST).date().isoformat())
    ap.add_argument("--now", action="store_true", help="게시 시각을 기다리지 않음")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--at", default=os.environ.get("PUBLISH_AT_KST", "07:00"), help="게시 시각 (KST, HH:MM)")
    a = ap.parse_args()

    day = ROOT / "issues" / a.date
    rec = ROOT / "published" / f"{a.date}.json"
    prev = None
    if rec.exists():
        try:
            prev = json.loads(rec.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        if not prev.get("withdrawn"):  # 인스타에서 지운 게시물(withdrawn: true)만 같은 날짜 재게시 허용
            log(f"이미 게시됨 — {rec.read_text(encoding='utf-8').strip()[:200]}")
            return 0
        log(f"{a.date} 이전 게시물은 삭제 표시(withdrawn)됨 — 다시 게시")
    ready_p = day / "ready.json"
    if not ready_p.exists():
        log(f"{a.date} 게시할 포스트 없음 (issues/{a.date}/ready.json 없음)")
        return 0
    ready = json.loads(ready_p.read_text(encoding="utf-8"))
    probs, caption = check(day, ready)
    if probs:
        for p in probs:
            log("✗", p)
        return 1

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "main")
    urls = [f"https://raw.githubusercontent.com/{repo}/{sha}/issues/{a.date}/{s}" for s in ready["slides"]]
    log(f"{a.date} · {len(urls)}장 · 캡션 {len(caption)}자")

    if a.dry_run:
        bad = 0
        for u in urls:
            ok, info = url_ok(u)
            log("  ", "✓" if ok and "image/jpeg" in info else "✗", u, "" if ok else info)
            bad += 0 if ok and "image/jpeg" in info else 1
        log("dry-run: 인스타 API는 호출하지 않음" + (f" — 이미지 {bad}장을 공개 주소에서 받을 수 없음 (저장소가 공개인지 확인)" if bad else " — 규격·이미지 주소 모두 정상"))
        return 1 if bad else 0

    token, ig = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("IG_USER_ID")
    if not token or not ig:
        log("✗ 저장소 Secrets에 IG_ACCESS_TOKEN, IG_USER_ID 가 없음")
        return 1

    # 게시 시각까지 대기 (늦게 준비됐으면 바로 게시, 날짜가 지났으면 게시하지 않음)
    hh, mm = map(int, a.at.split(":"))
    target = dt.datetime.fromisoformat(a.date).replace(hour=hh, minute=mm, tzinfo=KST)
    now = dt.datetime.now(KST)
    if now.date() > target.date():
        log(f"✗ 게시일({a.date})이 지남 — 오래된 뉴스라 게시하지 않음")
        return 1
    if not a.now and now < target:
        wait = (target - now).total_seconds()
        log(f"{a.at} KST까지 {int(wait // 60)}분 대기")
        time.sleep(wait)

    for u in urls:  # Meta가 내려받을 수 있는지 먼저 확인
        ok, info = url_ok(u)
        if not ok or "image/jpeg" not in info:
            log(f"✗ 이미지 주소 확인 실패: {u} ({info})")
            return 1

    try:
        if len(urls) == 1:
            cid = call("POST", f"{ig}/media", {"image_url": urls[0], "caption": caption}, token)["id"]
        else:
            kids = []
            for i, u in enumerate(urls, 1):
                kids.append(call("POST", f"{ig}/media", {"image_url": u, "is_carousel_item": "true"}, token)["id"])
                log(f"  항목 {i}/{len(urls)} 컨테이너 {kids[-1]}")
            for i, k in enumerate(kids, 1):
                wait_finished(k, token, f"항목 {i}")
            cid = call("POST", f"{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption}, token)["id"]
        wait_finished(cid, token, "캐러셀")
        mid = call("POST", f"{ig}/media_publish", {"creation_id": cid}, token)["id"]
        info = call("GET", mid, {"fields": "permalink,timestamp"}, token)
    except RuntimeError as e:
        log("✗", e)
        return 1

    rec.parent.mkdir(exist_ok=True)
    out = {"date": a.date, "media_id": mid, "permalink": info.get("permalink"), "timestamp": info.get("timestamp"),
           "slides": ready["slides"], "commit": sha, "published_at": dt.datetime.now(KST).isoformat(timespec="seconds")}
    if prev and prev.get("withdrawn"):  # 지운 게시물 기록은 previous 에 남긴다
        out["previous"] = prev.get("previous", []) + [{k: v for k, v in prev.items() if k != "previous"}]
    rec.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"✓ 게시 완료 {info.get('permalink')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
