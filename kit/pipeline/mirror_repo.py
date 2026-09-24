#!/usr/bin/env python3
"""[Cowork 백업 실행용] GitHub 저장소를 raw.githubusercontent.com 에서 파일 단위로 받아 같은 구조의 폴더를 만든다.
(Cowork 클라우드 환경은 이 저장소에 git clone·push 권한이 없고, raw 파일 읽기만 된다)

  curl -fsSL https://raw.githubusercontent.com/welcome2oz/raw-materials-daily/main/kit/pipeline/mirror_repo.py -o mirror_repo.py
  python3 mirror_repo.py repo            # → repo/kit/… (manifest.json 목록) + repo/issues/<최근 30일>/ + repo/published/

받는 것: kit 전체(manifest.json 의 sha256 로 확인), 최근 30일 issues/<날짜>/post.json·ready.json, published/<날짜>.json
"""
import datetime as dt
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "welcome2oz/raw-materials-daily"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"
KST = dt.timezone(dt.timedelta(hours=9))


def get(path):
    try:
        with urllib.request.urlopen(RAW + path, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def main():
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "repo")
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    man = json.loads(get("kit/manifest.json"))
    bad = []
    for f in man["files"]:
        b = get(f["path"])
        if b is None or hashlib.sha256(b).hexdigest() != f["sha256"]:
            bad.append(f["path"])  # raw 캐시(약 5분)로 직전 커밋과 어긋날 수 있음 → 받은 내용은 그대로 쓰고 경고
        if b is not None:
            p = dest / f["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
    (dest / "published").mkdir(parents=True, exist_ok=True)
    (dest / "issues").mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(KST).date()
    n_iss = n_pub = 0
    for i in range(days + 1):
        d = (today - dt.timedelta(days=i)).isoformat()
        for name in ("post.json", "ready.json"):
            b = get(f"issues/{d}/{name}")
            if b is not None:
                p = dest / "issues" / d / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b)
                n_iss += name == "post.json"
        b = get(f"published/{d}.json")
        if b is not None:
            (dest / "published" / f"{d}.json").write_bytes(b)
            n_pub += 1
    print(f"✓ {dest}: 키트 {len(man['files'])}개 (sha {man['sha']}), 최근 {days}일 호 {n_iss}개, 게시 기록 {n_pub}개")
    if bad:
        print("! sha 불일치(raw 캐시 가능성):", ", ".join(bad))


if __name__ == "__main__":
    main()
