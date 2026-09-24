#!/usr/bin/env bash
# RAW MATERIALS DAILY — 실행 환경 준비 (새 클라우드 세션·새 PC에서 1회)
#   bash pipeline/setup.sh
# 1) 폰트: npm 레지스트리에서 받아 template/fonts/ 에 배치 (키트에 폰트가 없을 때만)
#    - Pretendard Variable  ← npm pretendard@1.3.9  (SIL OFL 1.1)
#    - Inter latin variable ← npm @fontsource-variable/inter@5.3.0  (SIL OFL 1.1)
#    2026-09-24 확인: 두 파일 모두 키트에 넣어 둔 폰트와 바이트 단위로 동일
# 2) Python Playwright·openpyxl·Pillow 확인 (없으면 설치). Chromium이 없으면 playwright install 로 받는다
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p template/fonts
TMP="$(mktemp -d)"
if [ ! -s template/fonts/PretendardVariable.woff2 ]; then
  (cd "$TMP" && npm pack pretendard@1.3.9 --silent >/dev/null)
  tar xzOf "$TMP"/pretendard-1.3.9.tgz package/dist/web/variable/woff2/PretendardVariable.woff2 > template/fonts/PretendardVariable.woff2
  echo "✓ Pretendard 폰트 받음"
fi
if [ ! -s template/fonts/Inter-latin-wght.woff2 ]; then
  (cd "$TMP" && npm pack @fontsource-variable/inter@5.3.0 --silent >/dev/null)
  tar xzOf "$TMP"/fontsource-variable-inter-5.3.0.tgz package/files/inter-latin-wght-normal.woff2 > template/fonts/Inter-latin-wght.woff2
  echo "✓ Inter 폰트 받음"
fi
rm -rf "$TMP"
python3 -c "import playwright" 2>/dev/null || pip install playwright --break-system-packages -q
python3 -c "import openpyxl" 2>/dev/null || pip install openpyxl --break-system-packages -q
python3 -c "import PIL" 2>/dev/null || pip install pillow --break-system-packages -q
launch_ok() {
python3 - <<'PY' 2>/dev/null
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); b.close()
PY
}
if ! launch_ok; then
  # 브라우저가 없는 환경(Claude Code 클라우드 루틴 등): Playwright 전용 Chromium 설치 (네트워크 '전체' 허용 필요)
  echo "… Chromium 설치"
  python3 -m playwright install --with-deps chromium >/dev/null 2>&1 || python3 -m playwright install chromium >/dev/null 2>&1 || true
fi
launch_ok && echo "✓ Playwright Chromium 실행 확인" || { echo "✗ Chromium 실행 실패 — 환경 네트워크 설정(전체 허용) 확인"; exit 1; }
mkdir -p runs posts out
echo "✓ 준비 완료"
