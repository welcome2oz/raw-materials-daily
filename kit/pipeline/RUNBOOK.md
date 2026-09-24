# RAW MATERIALS DAILY — 매일 발행 절차 (RUNBOOK)

매일 아침 이 문서대로 카드뉴스를 만들어 GitHub 저장소 `welcome2oz/raw-materials-daily` 로 넘기면, 저장소의 GitHub Actions(`publish.yml`)가 **07:00(KST)에 인스타그램 @raw_material_procurement 에 자동 게시**한다.
결과물은 **인스타그램 공식 API 규격: 4:5(1080×1350) JPEG, 캐러셀 최대 10장** + 캡션.

실행 모드는 둘이다. 단계마다 해당 모드만 따른다.

| 모드 | 언제 | 어디서 | 넘기는 방법 |
|---|---|---|---|
| **A. 클라우드 루틴** (기본) | 매일 05:00 KST | Claude Code 루틴 (claude.ai/code/routines) — PC 꺼져도 동작 | 저장소에 커밋 → 현재 작업 브랜치(`claude/…`) push |
| **B. Cowork 백업** | 매일 06:15 KST | Cowork 예약 작업 | 루틴이 이미 넘겼으면 **바로 종료**. 아니면 사용자 PC Chrome으로 main 에 업로드 (PC·Chrome 켜져 있어야 함) |

- 기준 문서: `kit/FORMAT_GUIDE.md`(편집 원칙), `kit/brand.json`(허용 매체·규칙·인스타 규격), `kit/pipeline/channels.json`, `kit/pipeline/keywords.json`
- 발행 기록은 저장소가 전부다: `issues/<날짜>/`(카드 JPG·캡션·post.json·근거 CSV·ledger.xlsx·원문 발췌) + `published/<날짜>.json`(게시 링크). 중복 검열도 이 기록으로 한다.

## 절대 규칙

1. 기사 본문을 WebFetch로 직접 읽고 저장한 내용만 카드에 쓴다. 검색 스니펫·제목만으로 쓰지 않는다. 지어낸 숫자·인용·날짜는 한 글자도 넣지 않는다. 가상 데이터로는 카드를 만들지 않는다.
2. 가격(시세·단가) 수치는 쓰지 않는다. 가격 등락이 주제인 기사는 고르지 않는다.
3. 출처는 `brand.json > news_outlets` 허용 매체만. Yahoo Finance·MINING.COM 전재 기사는 원 발행처가 허용 매체일 때만, `via`로 표기.
4. 게재일은 포스트 날짜 전날~당일(`news_max_age_days: 1`)만.
5. 카드의 숫자는 모두 `sources[].evidence`(원문 문장 그대로)에 있어야 한다. 기사에 없는 계산값은 `calc: true`, 추정 구간은 `est`/`opt`.
6. **중복 금지**: 이미 게시한 기사(URL)는 다시 쓰지 않는다. 이미 게시한 사건은 **새로 확인된 사실이 있을 때만** 후속(`update_of`)으로 쓰고, 다른 매체가 같은 내용을 다시 쓴 것(예: 전날 로이터 → 오늘 NYT)은 건너뛴다. render.py가 저장소 기록과 대조해 막는다.
7. 검증 오류가 0이 될 때까지 고친다. 고칠 수 없는 뉴스는 뺀다. 게시할 뉴스가 0건이면 그날은 넘기지 않고 이유만 보고한다.
8. 카드와 캡션에 "원문과 대조했다", "검수했다" 같은 사람의 작업을 주장하는 문구를 쓰지 않는다. 편집 표기는 `brand.json > editor`("원재료 구매 담당자 발행")만.
9. 셸(curl·python)로 뉴스 사이트를 직접 받지 않는다. 뉴스 조회는 WebFetch·WebSearch만. WebFetch가 막힌 도메인은 우회하지 않고 그 후보를 버린다.
10. 인스타그램 로그인 정보·토큰은 어디에도 쓰거나 표시하지 않는다. 인스타 게시는 GitHub Actions가 저장소 Secrets로 한다. 비밀번호·토큰 입력 칸에는 아무것도 입력하지 않는다.
11. 사용자에게 질문하지 않는다(무인 실행). 판단이 필요하면 이 문서 기준으로 보수적으로 고르고(애매하면 뺀다) 보고에 적는다.
12. main 브랜치로 직접 push 하지 않는다(A 모드). 저장소의 `kit/`, `.github/`, `scripts/`, `published/` 는 고치지 않는다 — 매일 쓰는 곳은 `issues/<오늘>/` 뿐이다.

## 0단계. 준비

### A. 클라우드 루틴
작업 위치는 저장소 루트(세션이 clone 한 폴더)다.
```bash
DATE=$(TZ=Asia/Seoul date +%F)          # 포스트 날짜 (KST)
git branch --show-current                # 작업 브랜치 (claude/…). 바꾸지 않는다
git fetch -q origin main
git cat-file -e origin/main:published/$DATE.json 2>/dev/null && echo "이미 게시됨 → 종료"
git cat-file -e origin/main:issues/$DATE/ready.json 2>/dev/null && echo "이미 넘김(백업) → 종료"
cd kit && bash pipeline/setup.sh         # 폰트(npm)·Playwright·Chromium 준비
```
둘 중 하나라도 "종료"가 나오면 9단계 보고만 하고 끝낸다.

### B. Cowork 백업
```bash
DATE=$(TZ=Asia/Seoul date +%F)
RAW=https://raw.githubusercontent.com/welcome2oz/raw-materials-daily/main
curl -s -o /dev/null -w "%{http_code}\n" $RAW/issues/$DATE/ready.json    # 200 → 루틴이 이미 넘김 → 종료
curl -s -o /dev/null -w "%{http_code}\n" $RAW/published/$DATE.json       # 200 → 이미 게시됨 → 종료
```
200이 하나라도 나오면 짧게 보고(“루틴이 이미 넘김/게시됨”)하고 끝낸다. 아니면 저장소를 받아 온다 (세션 시작 폴더 아래에서 — Chrome 업로드는 이 폴더 아래 파일만 허용됨):
```bash
curl -fsSL $RAW/kit/pipeline/mirror_repo.py -o mirror_repo.py && python3 mirror_repo.py repo
cd repo/kit && bash pipeline/setup.sh
```

### 공통
- 다음 호수: `python3 -c "from render import load_history; h=load_history(); print(max([i.get('issue') or 0 for i in h['issues']], default=0)+1)"`
- `runs/$DATE/run_log.md` 를 만들고 이후 단계마다 한 줄씩 기록한다 (시각, 한 일, 결과).
- 전날 호가 `issues/<전날>/ready.json` 은 있는데 `published/<전날>.json` 이 없으면 **게시 실패**로 보고에 넣는다.

이하 모든 명령은 `kit/` 폴더에서 실행한다.

## 1단계. 채널 수집 (WebFetch)

`pipeline/channels.json`의 채널마다 WebFetch(url, prompt = `fetch_prompt`) → 결과 JSON 배열을 **받은 그대로** 저장:
`runs/$DATE/raw/<id>.json` = `{"channel", "url", "fetched_at"(KST ISO), "error", "items": [{"title","url","published","source","snippet"}]}`
- 실패(404·차단·빈 결과)면 `items: []`, `error`에 사유. 재시도는 1번만.
- 채널 절반 이상이 실패하면 `fallback.websearch_queries`로 WebSearch 보충 → `raw/websearch.json`

## 2단계. 후보 정리

```bash
python3 pipeline/collect.py $DATE          # 저장소 게시 기록과 대조해 이미 쓴 URL은 제외, 같은 사건은 표시
```
`runs/$DATE/candidates.md` 를 읽는다.

## 3단계. 기사 고르기

카테고리(비철·스틸·레진·화공)마다 **최대 1건**, 전체 2~5건 (카드 최대 10장 = 표지 + 뉴스 + 출처).
- 우선순위: ① 공급 차질·가동 중단·불가항력·파업 ② 관세·무역구제·규제 ③ 메이커 증설·감산·M&A ④ 수요 변화
- 제외: 가격 기사, 종목·실적·주가 기사, 칼럼·팟캐스트, 이미 쓴 URL
- `같은 사건 추정` 표시가 붙은 후보: 본문을 읽고 이전 호에 없던 **새 사실**(상태 변화, 새 날짜, 사건과 관련된 새 숫자)이 있을 때만 후속으로 쓴다. 매체만 다르고 내용이 같으면 버린다.
- `access: blocked` 후보는 WebSearch `"<원문 제목>" Yahoo Finance` 또는 `"<제목>" mining.com` 으로 전재본을 찾는다. `finance.yahoo.com`·`mining.com/web/` 에서 제목이 같은 것만 인정. 없으면 버린다.
- 해당 카테고리에 쓸 기사가 없으면 비워 둔다.

## 4단계. 본문 읽기와 원문 발췌 저장

기사마다 출처 id를 정한다 (예: `reu-escondida`). WebFetch prompt:
```
Return, copying text EXACTLY as it appears (no summarizing, no paraphrasing, no translation):
HEADLINE: the exact headline
PUBLISHED: the exact publication date/time string shown on the page
ATTRIBUTION: the byline and original publisher/agency attribution exactly as shown (e.g. "Reuters")
BODY: the full article body text verbatim, paragraph by paragraph, in order. If the body is cut off or paywalled, write BODY NOT AVAILABLE after the last available paragraph.
```
받은 내용을 그대로 `runs/$DATE/articles/<id>.md` 에 저장 (머리말: `source_id`, `url`, `fetched_at`, `method: WebFetch`).
- ATTRIBUTION이 허용 매체인가 / PUBLISHED가 날짜 범위 안인가 / 본문이 있는가 — 하나라도 아니면 버리고 run_log에 사유.

## 5단계. 포스트 JSON 작성

`posts/_template.json` → `posts/${DATE}_brief.json`. `FORMAT_GUIDE.md` 2·3·5장을 따른다.
- `id`: `${DATE}-brief`, `date`: `$DATE`, `issue`: 다음 호수
- 뉴스 1건 = news 슬라이드 1장. 헤드라인 2줄(줄당 약 10자), 시각화 1~3개, 보조 사실 0~1줄, 구매 관점 1줄
- 후속 기사: `"update_of": "<이전 story_id>"` (render.py 오류 메시지에 id가 나온다). 헤드라인·시각화는 **새 사실 중심**으로. 카드에 "후속 보도"가 표시된다
- `sources[]`: publisher, via, title(원문 제목 그대로), date, time, accessed=$DATE, url, **evidence**(발췌 파일에서 그대로 복사한 문장)
- 캡션: 첫 줄 `M월 D일(현지) 외신 보도 기준 원재료 뉴스 N건.`, 번호 목록, 마지막 줄 `구매 관점은 의견이며, 정확한 내용은 각 원문을 확인하세요.` 해시태그 5개 이하

## 6단계. 검증·렌더

```bash
python3 render.py posts/${DATE}_brief.json --check     # 오류 0 될 때까지 수정 (근거·가격·매체·날짜·중복·인스타 규격)
python3 render.py posts/${DATE}_brief.json             # out/${DATE}-brief/ NN.jpg(게시용 4:5) + NN.png(보관) + ledger.xlsx
python3 pipeline/dedup.py posts/${DATE}_brief.json     # 중복 판정 내역 (보고에 요약)
```
- `같은 사건 … 새 사실이 없음` 오류 → 그 뉴스를 뺀다 (매체가 달라도)
- JPG를 Read로 전부 열어 본다: 글자 잘림·겹침·빈 카드·깨진 한글이 없어야 한다

## 7단계. GitHub로 넘기기 → 07:00 자동 게시

### A. 클라우드 루틴
```bash
python3 pipeline/gh_handoff.py $DATE --inplace
```
- `issues/$DATE/` 에 파일을 쓰고 커밋한 뒤 **현재 작업 브랜치**로 push 한다. Actions가 몇 분 안에 main 에 반영하고 07:00에 게시한다.
- push 가 거부되면 메시지를 그대로 보고에 넣는다. main 으로 push 를 시도하지 않는다.
- 결과: 성공 `pushed (routine)`, 실패 `failed: <사유>`

### B. Cowork 백업 (Chrome 업로드)
1. 업로드 파일 준비
```bash
python3 pipeline/gh_handoff.py $DATE --prepare     # handoff/$DATE/ + upload_list.json (절대 경로, ready.json 마지막)
cat handoff/$DATE/upload_list.json
```
2. Chrome (Claude in Chrome 도구, ToolSearch로 로드)
   - `select_browser` — deviceId: `brand.json > handoff.chrome_device_id` (사용자 PC). 연결 안 되면 → 3번
   - `navigate` → `upload_url`
   - `find` "file input for uploading files" → 그 ref 로 `file_upload`(paths = upload_list.json 의 `paths` **전부 한 번에**)
   - `get_page_text` 로 파일 목록에 ready.json 까지 모두 올라왔는지 확인
   - `find` "commit summary input and Commit changes button" → `form_input` 으로 `commit_message` 입력 → Commit changes 클릭
   - 10초 뒤 `$RAW/issues/$DATE/ready.json` 을 셸 curl로 확인 (200이면 성공)
   - 결과: 성공 `pushed (Chrome)`, 실패 `failed: <사유>`
3. Chrome을 쓸 수 없으면(PC·Chrome 꺼짐, 확장 미연결, GitHub 로그아웃): 업로드하지 않고 `failed: Chrome 연결 안 됨` 으로 기록하고 보고한다.

07:00 이후에 넘어오면 Actions가 받는 즉시 게시한다. 날짜가 지나면 게시하지 않는다.

## 8단계. 보고

### A. 클라우드 루틴
마지막 메시지(한국어, 짧게): 넘긴 뉴스·매체 / 후속으로 쓴 것과 새 사실 / 중복으로 뺀 후보와 이전 호 / 그 밖에 뺀 후보와 이유 / 채널 오류·검증 경고 / push 결과(브랜치·커밋)와 07:00 게시 예정 / 전날 게시 실패가 있으면 그 사실.
같은 내용이 `issues/$DATE/run_log.md` 에도 남아 있어야 한다 (gh_handoff 전에 run_log 에 요약을 적는다).

### B. Cowork 백업
1. SendUserFile: `out/${DATE}-brief/*.jpg`, `caption.txt` (status: proactive)
2. SendUserMessage: A와 같은 항목
3. 뉴스가 0건이면 GitHub는 건드리지 않고 이유와 채널 상태만 보고한다.
