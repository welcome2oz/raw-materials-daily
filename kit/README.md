# RAW MATERIALS DAILY — 원재료 카드뉴스 키트

@raw_material_procurement 인스타그램용 원재료 카드뉴스. 그날의 원재료 뉴스(주요 외신·전문지)를 **인스타 캐러셀 4:5(1080×1350) JPEG + 캡션**으로 만든다. 가격은 싣지 않는다.
매일 04:00(KST) Cowork 예약 작업이 `pipeline/RUNBOOK.md`(P 모드) 순서대로 만들어 발행함에 올리고, 05:00 Claude Code 루틴(A 모드)이 받아 재검증·push 하면, GitHub Actions가 **07:00에 인스타그램에 자동 게시**한다(저장소 루트 `README.md`). 결과와 기록은 저장소 `issues/<날짜>/`·`published/<날짜>.json` 에 쌓인다.

```
kit/
├─ brand.json              계정명·발행 표기·카테고리 컬러·허용 매체·검증 규칙·인스타 규격
├─ render.py               검증(출처·근거 문장·가격 금지·중복·인스타 규격) → JPEG/PNG → 캡션 → 근거표(엑셀)
├─ template/               card.html / card.css / card.js  (fonts/ 는 setup.sh가 채움)
├─ pipeline/
│  ├─ RUNBOOK.md           매일 발행 절차 (A 클라우드 루틴 / B Cowork 백업)
│  ├─ channels.json        수집 채널 (MINING.COM 피드·ICIS·Bing 뉴스 RSS)
│  ├─ keywords.json        카테고리·토픽 키워드, 가격 기사·종목 기사 제외 규칙, 본문 접근 가능 도메인
│  ├─ collect.py           채널 결과 → 후보 목록 (허용 매체·게재일·가격 기사·이미 쓴 기사 필터)
│  ├─ dedup.py             중복 기사 검열 (같은 사건·새 사실 판정)
│  ├─ hub_stage.py         [P] 발행함에 올릴 파일·handoff.json(sha256 목록) 준비
│  ├─ pickup.py            [A] 발행함에서 받은 호를 sha256 대조·재검증해 키트에 배치
│  ├─ gh_handoff.py        [A] issues/<날짜>/ 에 쓰고 push (--inplace) · Chrome 업로드 준비 (--prepare)
│  ├─ hub/index.html       발행함 페이지
│  ├─ mirror_repo.py       [백업] push 권한 없는 환경에서 저장소를 raw 로 받아 오기
│  ├─ pack.py              kit/manifest.json 갱신 (키트 파일을 고친 뒤 실행)
│  └─ setup.sh             폰트(npm)·Playwright·Chromium 준비
├─ posts/                  _template.json (매일 만드는 포스트 JSON은 커밋하지 않음 → issues/<날짜>/post.json 으로 보관)
├─ runs/<날짜>/            (작업용, 커밋 안 함) raw/ · articles/ · candidates.md · run_log.md
├─ out/<id>/               (작업용, 커밋 안 함) 01.jpg… · caption.txt · ledger.xlsx · data_sources.csv · evidence.csv
├─ manifest.json           키트 파일 목록·sha256 (pack.py)
├─ FORMAT_GUIDE.md         편집 원칙·레이아웃·출처 정책·인스타 규격(근거 링크)
└─ DATA_SOURCES.md         가격 카드를 폐지한 근거 기록
```

## 1. 준비 (1회)

```bash
bash pipeline/setup.sh     # 폰트 2종을 npm에서 받고(키트에 없을 때만) Playwright 확인
```
- 한글 Pretendard (npm `pretendard@1.3.9`), 영문·숫자 Inter (npm `@fontsource-variable/inter@5.3.0`). 둘 다 SIL OFL 1.1
- 개인 PC(WSL2)에서는 먼저 `python3 -m venv .venv && source .venv/bin/activate && pip install playwright openpyxl && playwright install --with-deps chromium`

## 2. 쓰는 법

```bash
python3 pipeline/collect.py 2026-09-25                 # runs/2026-09-25/raw/*.json → candidates.md
python3 render.py posts/2026-09-25_brief.json --check  # 검증만
python3 render.py posts/2026-09-25_brief.json          # 렌더 (기본 4:5 1080×1350 JPEG + PNG)
```

| 옵션 | 동작 |
|---|---|
| `--check` | 검증만 하고 렌더하지 않음 |
| `--draft` | 오류가 있어도 초안 렌더 (빨간 "출처 누락" 표시) |
| `--ratio 3:4` | 1080×1440으로 렌더 (앱 수동 업로드용, API 게시 불가) |
| `--history 경로` | 발행 이력: 저장소 루트 폴더 또는 issues.json (기본: 키트가 저장소 안이면 저장소의 게시 기록) |
| `--runs 폴더` | 원문 발췌 폴더 위치 (기본 `runs/`) |

## 3. 자동 검증

오류(렌더 중단)
- 출처 URL 도메인·발행처가 허용 매체가 아님 / 전재 기사인데 `via` 없음
- 게재일이 포스트 날짜 전날보다 오래됨, 또는 포스트 날짜보다 뒤
- 가격 표현(`$`, `달러`, `USD/t`, `per tonne` 등)
- 출처 필수 항목 누락·id 중복·미등록 id 참조, 해시태그 5개·슬라이드 20장 초과, `sample: true`
- **근거 문장**: 뉴스 출처에 `evidence` 없음 / 근거 문장이 저장된 원문 발췌에 없음 / 카드 숫자(stats·split·gauge·key)가 근거 문장에 없음
- **인스타 규격(API)**: 폭 1080px, 비율 4:5·1:1·1.91:1, 장마다 같은 크기, 10장 이하, JPEG 8MB 이하
- **중복**: 이미 발행한 URL, 이미 발행한 사건인데 새 사실 없음, 후속인데 `update_of` 없음

경고: 달력·타임라인 날짜나 보조 사실 숫자가 근거 문장에 없음, 가격 관련 단어, 캡션 2,200자 초과, 인용 안 된 출처, 레이아웃 넘침

## 4. 기록 (엑셀)

- `ledger.xlsx`: 시트 `data_sources`(카드의 모든 숫자·사실 ↔ 출처), 시트 `evidence`(출처별 근거 문장 원문, 원문 발췌에서 확인 여부)
- 같은 내용이 CSV(UTF-8 BOM)로도 저장되고, 저장소 `issues/<날짜>/` 에 날짜별로 쌓인다 (GitHub에서 파일을 열고 Download)

## 5. 바꾸고 싶을 때

- 계정명·발행 표기·면책 문구 → `brand.json` (`editor`, `disclaimer`)
- 허용 매체 → `brand.json > news_outlets`
- 수집 채널·키워드 → `pipeline/channels.json`, `pipeline/keywords.json`
- 디자인 → `template/card.css` 상단 `:root` 변수
- 키트를 고친 뒤에는 `python3 pipeline/pack.py` 로 manifest.json 을 갱신해 함께 커밋한다 (루틴은 저장소를 매번 새로 clone 하므로 main 에 반영되면 다음 날부터 적용)
