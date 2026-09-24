#!/usr/bin/env python3
"""[A 모드: 클라우드 루틴] Cowork가 발행함에 올린 오늘 호를 받아 키트 작업 폴더에 놓고 다시 검증한다.
그다음 gh_handoff.py --inplace 로 GitHub에 넘긴다.

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--from", dest="src", required=True, help="발행함에서 받은 issues/<날짜>/ 폴더 (handoff.json 이 있는 곳)")
    a = ap.parse_args()
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
