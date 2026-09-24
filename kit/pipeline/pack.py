#!/usr/bin/env python3
"""키트 파일 목록(kit/manifest.json)을 만든다. 키트 파일을 고친 뒤 커밋 전에 한 번 실행한다.

  python3 pipeline/pack.py            # → kit/manifest.json (경로·크기·sha256)

manifest.json 은 GitHub에 push 권한이 없는 환경(Cowork 백업 실행)이 raw.githubusercontent.com 에서
키트를 파일 단위로 받아 올 때 쓴다 (pipeline/mirror_repo.py). 폰트는 넣지 않는다 — setup.sh 가 npm 에서 받는다.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # <저장소>/kit
INCLUDE = ["render.py", "brand.json", "README.md", "FORMAT_GUIDE.md", "DATA_SOURCES.md",
           "template/card.html", "template/card.css", "template/card.js",
           "pipeline/*.py", "pipeline/*.sh", "pipeline/*.json", "pipeline/*.md", "posts/_template.json"]


def main():
    files = []
    for pat in INCLUDE:
        for p in sorted(ROOT.glob(pat)):
            if p.is_file():
                b = p.read_bytes()
                files.append({"path": f"kit/{p.relative_to(ROOT)}", "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "manifest.json"
    out.write_text(json.dumps({"name": "raw-materials-daily-kit", "sha": digest,
                               "packed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
                               "files": files}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {len(files)}개 파일 → {out} (sha {digest})")


if __name__ == "__main__":
    main()
