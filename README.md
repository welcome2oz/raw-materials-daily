# RAW MATERIALS DAILY

@raw_material_procurement 원재료 카드뉴스(스틸·레진·비철·화공)를 매일 **07:00(KST)** 인스타그램에 자동 게시하는 저장소.
PC를 켜 두지 않아도 된다. 제작은 Anthropic 클라우드의 Claude Code 루틴이, 게시는 GitHub Actions가 한다.

```
05:00  Claude Code 루틴 (claude.ai/code/routines, 이 저장소 연결)
       뉴스 수집(WebFetch) → 원문 발췌·근거 검증·중복 검열 → 카드(4:5 JPEG) 제작
       → issues/<날짜>/ 커밋 → 작업 브랜치(claude/…) push
       └ ready.json 이 올라오면 Actions 'Publish to Instagram' 시작 → 곧바로 main 의 issues/<날짜>/ 에 반영
06:15  (백업) Cowork 예약 작업: main 에 오늘 호가 있으면 바로 종료. 없으면 PC Chrome으로 업로드 (PC 켜져 있을 때만)
07:00  Actions: 규격 점검 → Instagram 공식 API로 캐러셀 게시 → main 에 published/<날짜>.json 기록
```

| 폴더 | 내용 |
|---|---|
| `kit/` | 제작 키트 — 절차서 `kit/pipeline/RUNBOOK.md`, 렌더러·검증 `kit/render.py`, 중복 검열 `kit/pipeline/dedup.py` |
| `issues/<날짜>/` | 그날 호: 카드 JPG, 캡션, post.json, **ledger.xlsx**(카드 숫자↔출처·근거 문장), evidence.csv, data_sources.csv, 원문 발췌, 작업 기록 |
| `published/<날짜>.json` | 게시 결과 (인스타 링크·media id) — 이 파일이 있는 날은 다시 게시하지 않는다 |
| `.github/workflows/` | `publish.yml`(게시), `token-check.yml`(매주 토큰 점검) |
| `scripts/ig_publish.py` | Instagram 공식 API 게시 스크립트 |

- 같은 날짜는 두 번 게시하지 않는다. 준비가 07:00보다 늦으면 준비되는 즉시 게시하고, 날짜가 지나면 게시하지 않는다.
- GitHub 예약 실행(cron)은 몇 시간씩 늦는 사례가 보고돼 게시 시각 맞추기에 쓰지 않는다 ([GitHub Community #207346](https://github.com/orgs/community/discussions/207346)).
- 이 저장소는 **공개**여야 한다. Instagram API가 이미지를 공개 주소에서 직접 내려받는다 ([Meta: Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)).

## Claude Code 루틴 설정 (1회)

루틴은 Anthropic 클라우드에서 실행돼 노트북을 닫아도 동작한다. Pro·Max·Team·Enterprise 플랜에서 쓸 수 있다 ([Claude Code 문서: Routines](https://code.claude.com/docs/en/routines)).

1. [claude.ai/code/routines](https://claude.ai/code/routines) → **New routine**
2. 이름: `RAW MATERIALS DAILY 발행`
3. 프롬프트 (그대로 붙여 넣기):
   ```
   오늘(KST 날짜) RAW MATERIALS DAILY 카드뉴스를 만들어 넘겨라.
   이 저장소의 kit/pipeline/RUNBOOK.md 를 처음부터 끝까지 읽고, 'A. 클라우드 루틴' 모드로 0단계부터 8단계까지 그대로 실행한다.
   절대 규칙을 모두 지킨다: 기사 원문(WebFetch)에 있는 내용만 쓰고, 근거 없는 숫자·인용은 넣지 않으며, 가격은 쓰지 않고, 이미 게시한 기사·같은 내용의 재보도는 뺀다.
   사용자에게 질문하지 말고 끝까지 진행한다. 게시할 뉴스가 0건이거나 오류로 멈추면 이유를 run_log 와 마지막 메시지에 남긴다.
   ```
   모델은 가장 성능이 좋은 모델을 고른다.
4. 저장소: `welcome2oz/raw-materials-daily`
   - 목록에 없거나 첫 실행에서 push 가 거부되면 [Claude GitHub App](https://github.com/apps/claude)을 이 저장소에 설치한다 (Only select repositories → raw-materials-daily)
5. 환경(Environment): 구름 아이콘 → **Add cloud environment** → 이름 `cardnews`, **Network access: Full** → 만들기 → 이 환경 선택
   - 뉴스 사이트(WebFetch)와 Chromium 설치가 기본 허용 목록(Trusted) 밖이라 필요하다 ([Cloud environments: Access levels](https://code.claude.com/docs/en/cloud-environments#access-levels))
   - Default 환경을 바꾸지 않고 따로 만들면 다른 작업에는 영향이 없다
   - 이 환경에는 비밀값을 넣지 않는다 (인스타 토큰은 GitHub Secrets에만 있다)
6. 트리거: **Schedule → Daily → 05:00** (시간은 내 지역 시간으로 입력하면 자동 변환)
7. 커넥터: 모두 제거 (이 작업에는 필요 없음)
8. **Create** → 상세 화면에서 **Run now** 로 한 번 시험

루틴은 작업을 `claude/` 로 시작하는 브랜치에 push 한다. 워크플로가 그 push 를 받아 main 에 반영하고 게시한다.

## Instagram·GitHub 설정 (완료됨, 참고용)

1. 인스타그램 프로페셔널 계정 (API 게시는 프로페셔널 계정만 가능)
2. Meta 앱 → Instagram → **API setup with Instagram login** → Generate Token (`instagram_business_basic`, `instagram_business_content_publish`) — 장기 토큰 60일
3. 저장소 Settings → Secrets and variables → Actions: `IG_ACCESS_TOKEN`, `IG_USER_ID` (토큰은 이 화면에만 넣는다)
4. Settings → Actions → General → Workflow permissions: **Read and write**
5. (선택) `GH_PAT`: 이 저장소 Secrets 쓰기 권한만 준 fine-grained 토큰 → 매주 인스타 토큰 자동 연장. 없으면 60일마다 토큰 교체

## 게시 규격 (Instagram 공식 API)

| 항목 | 값 | 근거 |
|---|---|---|
| 형식 | JPEG, sRGB, 8MB 이하 | [IG User Media 레퍼런스](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| 비율 | 4:5 (1080×1350). API 허용 범위 4:5~1.91:1 — 3:4는 불가 | 같은 문서 |
| 캐러셀 | 최대 10장 | [Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing) |
| 게시 한도 | 24시간에 API 게시 100건 | 같은 문서 |

## 수동 조작

- 게시 없이 점검: Actions → Publish to Instagram → Run workflow → `date` 입력, `dry_run` 체크
- 지금 바로 게시: 같은 화면에서 `now` 체크
- 토큰 점검: Actions → Instagram token check → Run workflow

## 실패하면

- 루틴 실행 기록: claude.ai/code/routines → 루틴 → 실행 목록 (초록 표시는 "세션이 오류 없이 끝남"일 뿐이니 마지막 메시지를 확인)
- Actions가 실패하면 GitHub가 메일을 보낸다. 로그의 `✗` 줄이 원인이다.
  - `토큰이 유효하지 않음` → 토큰 재발급 후 `IG_ACCESS_TOKEN` 교체
  - `이미지 주소 확인 실패` → 저장소가 비공개인지 확인
  - `HTTP 400 … aspect ratio` → 카드 규격 문제 (kit/brand.json 4:5 확인)
