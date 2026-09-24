#!/usr/bin/env python3
"""[P 모드: Cowork 제작] 오늘 호를 발행함(허브 아티팩트)에 올릴 파일로 준비한다. 루틴(A 모드)이 발행함에서 받아 GitHub로 넘긴다.

  python3 pipeline/hub_stage.py 2026-09-25 --index <발행함에서 받은 issues.json>
출력
  hub_stage/issues/<날짜>/   JPG·캡션·post.json·근거 CSV·원문 발췌·후보 목록·실행 로그·미리보기
  hub_stage/issues/<날짜>/handoff.json   루틴이 받을 파일 목록(sha256). 이 파일이 있어야 루틴이 가져간다
  hub_stage/issues.json      발행함 목록(최신이 앞). 지난 호의 인스타 링크는 저장소 published/ 에서 채운다
  hub_stage/files.json       Artifact publish 의 files 인자로 그대로 쓰는 매핑 (null = 7일 지난 파일 삭제)
검증: 저장소 게시 기록(중복)·원문 발췌(근거)로 render.validate 를 다시 돌려 오류가 있으면 올리지 않는다.
"""
import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from render import load_history, load_json, repo_root, slide_refs, validate  # noqa: E402
sys.path.insert(0, str(ROOT / "pipeline"))
import dedup  # noqa: E402

KEEP_DAYS = 7   # 발행함(아티팩트)에는 최근 7일치 파일만 둔다 (파일 255개 한도). 전체 기록은 GitHub 저장소
KST = dt.timezone(dt.timedelta(hours=9))
HANDOFF_FILES = ("caption.txt", "data_sources.csv", "evidence.csv", "post.json", "candidates.md", "run_log.md")


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--index", default="", help="발행함에서 받은 현재 issues.json (없으면 새로 만든다)")
    ap.add_argument("--stage", default=str(ROOT / "hub_stage"))
    ap.add_argument("--status", default="staged", help="발행함 페이지에 보일 전달 상태")
    a = ap.parse_args()

    post_path = ROOT / "posts" / f"{a.date}_brief.json"
    post = load_json(post_path)
    brand = load_json(ROOT / "brand.json")
    run = ROOT / "runs" / a.date
    errors, warns = validate(post, brand, run if run.exists() else None, load_history())
    if errors:
        print("✗ 검증 오류가 있어 발행함에 올리지 않음:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    out = ROOT / "out" / post["id"]
    jpgs = sorted(out.glob("[0-9][0-9].jpg"))
    if not jpgs:
        print(f"✗ {out} 에 JPG 없음 — render.py 먼저")
        sys.exit(1)
    stage = Path(a.stage)
    if stage.exists():
        shutil.rmtree(stage)
    dest = stage / "issues" / a.date
    (dest / "articles").mkdir(parents=True)

    files, manifest = {}, []

    def put(src: Path, name: str, handoff=True):
        if src.exists():
            d = dest / name
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, d)
            files[f"issues/{a.date}/{name}"] = str(d)
            if handoff:
                manifest.append({"path": name, "bytes": d.stat().st_size, "sha256": sha(d)})

    for p in jpgs:
        put(p, p.name)
    for n in ("caption.txt", "data_sources.csv", "evidence.csv"):
        put(out / n, n)
    put(out / "preview.png", "preview.png", handoff=False)   # 발행함 페이지용
    put(post_path, "post.json")
    for n in ("candidates.md", "run_log.md"):
        put(run / n, n)
    for p in sorted((run / "articles").glob("*.md")):
        put(p, f"articles/{p.name}")
    handoff = {"date": a.date, "issue": post.get("issue"), "post_id": post["id"], "slides": [p.name for p in jpgs],
               "created_at": dt.datetime.now(KST).isoformat(timespec="seconds"), "created_by": "cowork",
               "validated": True, "warnings": warns, "files": manifest}
    (dest / "handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=1), encoding="utf-8")
    files[f"issues/{a.date}/handoff.json"] = str(dest / "handoff.json")

    # ---- 발행함 목록(issues.json)
    idx = {"issues": []}
    if a.index and Path(a.index).exists():
        try:
            idx = json.loads(Path(a.index).read_text(encoding="utf-8"))
        except Exception:
            pass
    idx.setdefault("issues", [])
    idx.setdefault("series", brand.get("series"))
    cats = brand["categories"]
    S = {x["id"]: x for x in post.get("sources", [])}
    toc = []
    for s in post["slides"]:
        if s.get("type") != "news":
            continue
        src = S.get(slide_refs(s)[0], {}) if slide_refs(s) else {}
        toc.append({"category": s.get("category"), "category_ko": cats.get(s.get("category"), {}).get("ko", ""),
                    "headline": (s.get("toc") or s.get("headline", "")).replace("**", "").replace("\n", " "),
                    "publisher": src.get("publisher", ""), "via": src.get("via", "")})
    entry = {"date": a.date, "id": post["id"], "issue": post.get("issue"),
             "title": post["slides"][0].get("title", "").replace("**", "").replace("\n", " "),
             "slides": [f"issues/{a.date}/{p.name}" for p in jpgs], "toc": toc,
             "sources": [{k: x.get(k, "") for k in ("id", "publisher", "via", "title", "date", "time", "url")} | {"evidence": x.get("evidence", [])}
                         for x in post.get("sources", [])],
             "validation": {"errors": 0, "warnings": warns},
             "stories": dedup.stories_for_index(post),
             "instagram": {"handoff": a.status, "repo": brand.get("github_repo", ""),
                           "publish_at_kst": brand.get("instagram", {}).get("publish_time_kst", "07:00"), "permalink": ""},
             "published_at": handoff["created_at"],
             "files": sorted(k for k in files if not k.endswith(".png") or "preview" in k)}
    old_files = {e["date"]: e.get("files", []) + e.get("slides", []) for e in idx["issues"]}
    idx["issues"] = [e for e in idx["issues"] if e.get("date") != a.date]
    idx["issues"].insert(0, entry)
    idx["issues"].sort(key=lambda e: e["date"], reverse=True)
    idx["updated"] = entry["published_at"]
    # 지난 호의 인스타 링크를 저장소 게시 기록에서 채운다
    rr = repo_root()
    for e in idx["issues"]:
        rec = rr / "published" / f"{e['date']}.json" if rr else None
        if rec and rec.exists():
            pub = load_json(rec)
            e.setdefault("instagram", {})
            e["instagram"].update({"permalink": pub.get("permalink", ""), "media_id": pub.get("media_id", ""),
                                   "published_at": pub.get("published_at", ""), "handoff": "published"})
    # 오래된 호의 파일은 발행함에서 내린다 (목록 기록과 GitHub 사본은 남음)
    cutoff = (dt.date.fromisoformat(a.date) - dt.timedelta(days=KEEP_DAYS)).isoformat()
    removed = []
    for e in idx["issues"]:
        if e["date"] < cutoff and not e.get("archived"):
            removed += old_files.get(e["date"], [])
            e["archived"] = True
    (stage / "issues.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    files["issues.json"] = str(stage / "issues.json")
    for f in removed:
        files.setdefault(f, None)  # Artifact publish 에서 null = 삭제
    (stage / "files.json").write_text(json.dumps(files, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ 발행함 준비: {len(files)}개 파일 → {stage}/files.json  (handoff.json {len(manifest)}개 파일)")
    for w in warns:
        print("   !", w)


if __name__ == "__main__":
    main()
