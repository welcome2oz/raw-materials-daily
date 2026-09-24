#!/usr/bin/env python3
"""오늘 포스트를 GitHub 저장소로 넘긴다. 저장소의 GitHub Actions(publish.yml)가 07:00(KST)에 인스타그램에 게시한다.

  python pipeline/gh_handoff.py 2026-09-25 --inplace       # [클라우드 루틴] 키트가 저장소 안(<저장소>/kit)일 때:
                                                            #   issues/<날짜>/ 에 쓰고 커밋 → 현재 작업 브랜치(claude/…)로 push
  python pipeline/gh_handoff.py 2026-09-25 --prepare       # [Cowork 백업] Chrome 업로드용 폴더만 준비 (handoff/<날짜>/), push 안 함
  python pipeline/gh_handoff.py 2026-09-25                 # (구) 저장소를 clone 해서 main 에 push — 권한이 있는 환경에서만

올리는 것: issues/<날짜>/ NN.jpg · caption.txt · post.json · evidence.csv · data_sources.csv · ledger.xlsx
           · candidates.md · articles/*.md · run_log.md · ready.json
ready.json 이 올라가는 순간 Actions가 시작된다. 이미 게시된 날짜(main 의 published/<날짜>.json)는 건드리지 않는다.
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from render import load_history, load_json, repo_root, validate  # noqa: E402

KST = dt.timezone(dt.timedelta(hours=9))
FILES = ("caption.txt", "evidence.csv", "data_sources.csv", "ledger.xlsx")


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}".strip())
    return r


def fill_day(day: Path, a, post, jpgs, out, run, warns, brand):
    if day.exists():
        shutil.rmtree(day)
    (day / "articles").mkdir(parents=True)
    for p in jpgs:
        shutil.copy2(p, day / p.name)
    for n in FILES:
        if (out / n).exists():
            shutil.copy2(out / n, day / n)
    shutil.copy2(ROOT / "posts" / f"{a.date}_brief.json", day / "post.json")
    for p in sorted((run / "articles").glob("*.md")):
        shutil.copy2(p, day / "articles" / p.name)
    for n in ("run_log.md", "candidates.md"):
        if (run / n).exists():
            shutil.copy2(run / n, day / n)
    ready = {"date": a.date, "issue": post.get("issue"), "slides": [p.name for p in jpgs], "caption_file": "caption.txt",
             "validated": True, "errors": 0, "warnings": warns,
             "handoff_at": dt.datetime.now(KST).isoformat(timespec="seconds"),
             "handoff": "routine" if a.inplace else ("chrome" if a.prepare else "git"),
             "publish_at_kst": brand.get("instagram", {}).get("publish_time_kst", "07:00")}
    (day / "ready.json").write_text(json.dumps(ready, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {day} 준비 ({len(jpgs)}장)")
    return ready


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--repo", default="")
    ap.add_argument("--work", default=str(ROOT / "gh_repo"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prepare", action="store_true", help="Chrome 업로드용: handoff/<날짜>/ 에 파일만 모은다")
    ap.add_argument("--inplace", action="store_true", help="클라우드 루틴용: 키트가 들어 있는 저장소에 바로 커밋하고 현재 브랜치로 push")
    a = ap.parse_args()
    if a.prepare:
        a.dry_run = True
        a.work = str(ROOT / "handoff_work")

    brand = load_json(ROOT / "brand.json")
    repo = a.repo or brand.get("github_repo", "")
    post = load_json(ROOT / "posts" / f"{a.date}_brief.json")
    run = ROOT / "runs" / a.date
    errors, warns = validate(post, brand, run if run.exists() else None, load_history())
    if errors:
        print("✗ 검증 오류가 있어 넘기지 않음:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    out = ROOT / "out" / post["id"]
    jpgs = sorted(out.glob("[0-9][0-9].jpg"))
    if not jpgs:
        print(f"✗ {out} 에 JPG 없음 — render.py 먼저")
        sys.exit(1)

    # ---- 클라우드 루틴: 이 저장소에 바로 커밋 → 현재 작업 브랜치로 push
    if a.inplace:
        rr = repo_root()
        if not rr:
            print(f"✗ 키트가 GitHub 저장소 안(<저장소>/kit)에 있지 않음: {ROOT}")
            sys.exit(2)
        sh(["git", "fetch", "origin", "main"], cwd=rr, check=False)
        if sh(["git", "cat-file", "-e", f"origin/main:published/{a.date}.json"], cwd=rr, check=False).returncode == 0:
            print(f"! {a.date} 는 이미 게시됨 (main 의 published/{a.date}.json) — 넘기지 않음")
            return
        branch = sh(["git", "branch", "--show-current"], cwd=rr).stdout.strip()
        if branch in ("", "main", "master"):
            branch = f"claude/issue-{a.date}"
            sh(["git", "checkout", "-B", branch], cwd=rr)
            print(f"  작업 브랜치 {branch} 생성 (main 으로는 push 하지 않음)")
        fill_day(rr / "issues" / a.date, a, post, jpgs, out, run, warns, brand)
        if a.dry_run:
            return
        sh(["git", "add", f"issues/{a.date}"], cwd=rr)
        if sh(["git", "diff", "--cached", "--quiet"], cwd=rr, check=False).returncode == 0:
            print("! 바뀐 파일 없음 — 이미 같은 내용이 커밋돼 있음")
        else:
            sh(["git", "-c", "commit.gpgsign=false", "commit", "-m", f"issue {a.date} (No.{post.get('issue')})"], cwd=rr)
        last = None
        for i in range(4):  # 네트워크 오류 시 2·4·8초 간격 재시도
            r = sh(["git", "push", "-u", "origin", f"HEAD:{branch}"], cwd=rr, check=False)
            if r.returncode == 0:
                break
            last = r
            import time
            time.sleep(2 ** (i + 1))
        else:
            raise RuntimeError(f"git push 실패\n{last.stdout}\n{last.stderr}")
        sha = sh(["git", "rev-parse", "HEAD"], cwd=rr).stdout.strip()
        print(f"✓ push 완료 → 브랜치 {branch} ({sha[:7]}). Actions가 main 에 반영하고 "
              f"{brand.get('instagram', {}).get('publish_time_kst', '07:00')} KST에 게시")
        print(f"  확인: https://github.com/{repo}/actions  ·  https://github.com/{repo}/tree/{branch}/issues/{a.date}")
        return

    if not repo and not a.dry_run:
        print("✗ brand.json > github_repo 가 비어 있음 (예: \"welcome2oz/raw-materials-daily\")")
        sys.exit(2)
    work = Path(a.work)
    if not a.dry_run:
        if work.exists():
            shutil.rmtree(work)
        sh(["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(work)])
        if (work / "published" / f"{a.date}.json").exists():
            print(f"! {a.date} 는 이미 게시됨 — 넘기지 않음")
            return
    day = work / "issues" / a.date
    fill_day(day, a, post, jpgs, out, run, warns, brand)
    if a.prepare:
        flat = ROOT / "handoff" / a.date
        if flat.exists():
            shutil.rmtree(flat)
        flat.mkdir(parents=True)
        order = [p.name for p in jpgs] + ["caption.txt", "post.json", "evidence.csv", "data_sources.csv", "ledger.xlsx",
                                          "candidates.md", "run_log.md", "ready.json"]
        paths = []
        for n in order:
            if (day / n).exists():
                shutil.copy2(day / n, flat / n)
                paths.append(str(flat / n))
        (flat / "upload_list.json").write_text(json.dumps({"repo": repo, "upload_url": f"https://github.com/{repo}/upload/main/issues/{a.date}",
                                                           "commit_message": f"issue {a.date} (No.{post.get('issue')})", "paths": paths},
                                                          ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ Chrome 업로드 목록 → {flat / 'upload_list.json'} ({len(paths)}개, ready.json 마지막)")
        return
    if a.dry_run:
        return
    sh(["git", "add", f"issues/{a.date}"], cwd=work)
    sh(["git", "-c", "commit.gpgsign=false", "commit", "-m", f"issue {a.date} (No.{post.get('issue')})"], cwd=work)
    sh(["git", "push", "origin", "HEAD:main"], cwd=work)
    print(f"✓ GitHub push 완료 → https://github.com/{repo}/tree/main/issues/{a.date}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print("✗ GitHub 전송 실패:\n", e)
        sys.exit(3)
