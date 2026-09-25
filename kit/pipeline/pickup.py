#!/usr/bin/env python3
"""[A 모드: 클라우드 루틴] Cowork가 발행함에 올린 자료를 받아 키트 작업 폴더에 놓는다.

  (기본) --feed : Cowork 수집 자료(feeds/<날짜>/: feed.json · raw.json · articles/*.md)
                  → runs/<날짜>/raw/<채널>.json · runs/<날짜>/articles/*.md  (이후 RUNBOOK 2~6단계를 루틴이 진행)
  python3 pipeline/pickup.py 2026-09-27 --feed <FROM>/feeds/2026-09-27

  (예전) --from : Cowork가 카드까지 만든 호(issues/<날짜>/handoff.json) → 재검증 후 gh_handoff.py --inplace

  # 1) Artifact read 로 발행함의 issues/<날짜>/handoff.json 과 그 안의 files 전부를 받는다 (저장 폴더 = FROM)
  python3 pipeline/pickup.py 2026-09-25 --from <FROM>/issues/2026-09-25
  python3 pipeline/gh_handoff.py 2026-09-25 --inplace

하는 일
  - handoff.json 의 파일마다 크기·sha256 대조 (하나라도 다르면 중단)
  - 배치: post.json → posts/<날짜>_brief.json, articles/·run_log.md·candidates.md → runs/<날짜>/,
          NN.jpg·caption.txt → out/<id>/
  - 근거표(data_sources.csv·evidence.csv·ledger.xlsx)를 post.json·원문 발췌에서 다시 만든다
  - 검증: render.validate (근거 문장↔원문 발췌, 가격·매체·날짜, 저장소 게시 기록과 중복) + JPEG 1080×1350·장수·용량
  - 캡션이 post.json 으로 만든 캡션과 같은지 확인
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from render import (EVIDENCE_COLS, LEDGER_COLS, build_caption, build_evidence, build_ledger,  # noqa: E402
                    check_jpegs, load_history, load_json, validate, write_xlsx)

KST = dt.timezone(dt.timedelta(hours=9))


def jpeg_size(p: Path):
    b = p.read_bytes()
    i = 2
    while i < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


def pickup_feed(date: str, src: Path):
    """Cowork 수집 자료 → runs/<날짜>/raw·articles. 형식이 틀리면 중단(exit 2~3)."""
    fj = src / "feed.json"
    if not fj.exists():
        print(f"✗ {fj} 없음 — 발행함에 오늘 수집 자료가 아직 없음")
        sys.exit(2)
    feed = load_json(fj)
    if feed.get("date") != date:
        print(f"✗ feed.json 날짜 {feed.get('date')} ≠ {date}")
        sys.exit(2)
    raw_p = src / feed.get("raw_file", "raw.json")
    try:
        raw = load_json(raw_p)
    except Exception as e:  # 채널 목록이 깨졌어도 원문 발췌는 쓴다 — 채널 수집은 루틴이 직접
        print(f"! {raw_p.name} 읽기 실패({e}) → 채널 수집(1단계)은 루틴이 직접 하고, 원문 발췌만 받음")
        raw = {}
    chans = raw.get("channels", raw) if isinstance(raw, dict) else {}
    run = ROOT / "runs" / date
    (run / "raw").mkdir(parents=True, exist_ok=True)
    (run / "articles").mkdir(parents=True, exist_ok=True)
    n_items = 0
    for cid, c in chans.items():
        if not isinstance(c, dict):
            continue
        rec = {"channel": c.get("channel", cid), "url": c.get("url", ""), "fetched_at": c.get("fetched_at", ""),
               "error": c.get("error", ""), "items": c.get("items") or [], "collected_by": "cowork"}
        n_items += len(rec["items"])
        (run / "raw" / f"{cid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    missing, n_art = [], 0
    for art in feed.get("articles", []):
        f = src / art.get("file", f"articles/{art.get('id')}.md")
        if not f.exists() or not f.read_text(encoding="utf-8").strip():
            missing.append(art.get("id"))
            continue
        shutil.copy2(f, run / "articles" / f.name)
        n_art += 1
    with open(run / "run_log.md", "a", encoding="utf-8") as fh:
        fh.write(f"- {dt.datetime.now(KST).strftime('%H:%M')} [루틴] 발행함 수집 자료 받음 (Cowork {feed.get('created_at', '')}): "
                 f"채널 {len(chans)}개·항목 {n_items}건, 원문 발췌 {n_art}개" + (f", 누락 {missing}" if missing else "") + "\n")
    print(f"✓ 수집 자료 받음: 채널 {len(chans)}개(항목 {n_items}건), 원문 발췌 {n_art}개 → runs/{date}/"
          + (f"  ! 발췌 파일 누락: {missing}" if missing else ""))
    print("  다음: python3 pipeline/collect.py " + date + "  (RUNBOOK 2단계부터)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--from", dest="src", default="", help="발행함에서 받은 issues/<날짜>/ 폴더 (handoff.json 이 있는 곳)")
    ap.add_argument("--feed", default="", help="발행함에서 받은 feeds/<날짜>/ 폴더 (feed.json 이 있는 곳)")
    a = ap.parse_args()
    if a.feed:
        return pickup_feed(a.date, Path(a.feed))
    if not a.src:
        ap.error("--feed 또는 --from 중 하나가 필요함")
    src = Path(a.src)
    hf = src / "handoff.json"
    if not hf.exists():
        print(f"✗ {hf} 없음 — 발행함에 오늘 호가 아직 없음")
        sys.exit(2)
    h = load_json(hf)
    if h.get("date") != a.date:
        print(f"✗ handoff.json 날짜 {h.get('date')} ≠ {a.date}")
        sys.exit(2)
    bad = []
    for f in h["files"]:
        p = src / f["path"]
        if not p.exists():
            bad.append(f"{f['path']}: 없음")
        elif p.stat().st_size != f["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
            bad.append(f"{f['path']}: 크기·sha256 불일치")
    if bad:
        print("✗ 받은 파일이 발행함 목록과 다름 (다시 받기):")
        for b in bad:
            print("  -", b)
        sys.exit(3)

    brand = load_json(ROOT / "brand.json")
    post = load_json(src / "post.json")
    pid = post["id"]
    run = ROOT / "runs" / a.date
    out = ROOT / "out" / pid
    for d in (run / "articles", out):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    (ROOT / "posts").mkdir(exist_ok=True)
    shutil.copy2(src / "post.json", ROOT / "posts" / f"{a.date}_brief.json")
    for f in h["files"]:
        p = src / f["path"]
        if f["path"].startswith("articles/"):
            shutil.copy2(p, run / "articles" / p.name)
        elif f["path"] in ("run_log.md", "candidates.md"):
            shutil.copy2(p, run / f["path"])
        elif p.suffix == ".jpg" or f["path"] == "caption.txt":
            shutil.copy2(p, out / p.name)

    # 근거표 다시 만들기 (post.json·원문 발췌 기준)
    ledger = build_ledger(post)
    evid = build_evidence(post, run)
    for name, cols, rows in (("data_sources.csv", LEDGER_COLS, ledger), ("evidence.csv", EVIDENCE_COLS, evid)):
        with open(out / name, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            w.writerows(rows)
    write_xlsx(out / "ledger.xlsx", [("data_sources", LEDGER_COLS, ledger), ("evidence", EVIDENCE_COLS, evid)])

    # 검증
    errors, warns = validate(post, brand, run, load_history())
    jpgs = sorted(out.glob("[0-9][0-9].jpg"))
    ig = brand.get("instagram", {})
    if [p.name for p in jpgs] != h.get("slides"):
        errors.append(f"슬라이드 목록 불일치: {[p.name for p in jpgs]} ≠ {h.get('slides')}")
    if not 1 <= len(jpgs) <= ig.get("max_slides", 10):
        errors.append(f"슬라이드 {len(jpgs)}장 — 1~{ig.get('max_slides', 10)}장")
    for p in jpgs:
        if jpeg_size(p) != (ig.get("width", 1080), ig.get("height", 1350)):
            errors.append(f"{p.name}: {jpeg_size(p)} — {ig.get('width', 1080)}x{ig.get('height', 1350)} 아님")
    errors += check_jpegs(jpgs, brand)
    cap = (out / "caption.txt").read_text(encoding="utf-8") if (out / "caption.txt").exists() else ""
    if cap.strip() != build_caption(post).strip():
        errors.append("caption.txt 가 post.json 으로 만든 캡션과 다름")
    for w in warns:
        print("  !", w)
    if errors:
        print("✗ 검증 오류 — 넘기지 않음:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    with open(run / "run_log.md", "a", encoding="utf-8") as fh:
        fh.write(f"- {dt.datetime.now(KST).strftime('%H:%M')} [루틴] 발행함에서 받음 (Cowork 제작 {h.get('created_at', '')}), "
                 f"파일 {len(h['files'])}개 sha256 일치, 재검증 통과 (경고 {len(warns)}건)\n")
    print(f"✓ 받음·재검증 통과: {pid} {len(jpgs)}장, 원문 발췌 {len(list((run / 'articles').glob('*.md')))}개 → 다음: gh_handoff.py {a.date} --inplace")


if __name__ == "__main__":
    main()
