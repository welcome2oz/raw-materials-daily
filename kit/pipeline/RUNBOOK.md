# RAW MATERIALS DAILY — 매일 발행 절차 (RUNBOOK)

매일 새벽 이 문서대로 카드뉴스를 만들어 GitHub 저장소 `welcome2oz/raw-materials-daily` 로 넘기면, 저장소의 GitHub Actions(`publish.yml`)가 **07:00(KST)에 인스타그램 @raw_material_procurement 에 자동 게시**한다.
결과물은 **인스타그램 공식 API 규격: 4:5(1080×1350) JPEG, 캐러셀 최대 10장** + 캡션.

실행 모드는 둘이다. 둘 다 클라우드에서 돌아 **PC가 꺼져 있어도 된다.**

| 모드 | 언제 | 어디서 | 하는 일 |
|---|---|---|---|
| **P. Cowork 수집** | 매일 04:00 KST | Cowork 예약 작업 | **코드를 실행하지 않는다.** WebFetch로 채널 목록과 기사 원문을 읽어 파일로 쓰고 발행함에 올린다 (`feeds/<날짜>/`). 절차는 맨 아래 "P. Cowork 수집 절차" |
| **A. 클라우드 루틴** | 매일 05:00 KST | Claude Code 루틴 (저장소 연결) | 발행함 수집 자료를 받아 0~8단계: 후보 정리·선정·카드 제작·검증 → 작업 브랜치(`claude/…`) push. 05:50까지 자료가 없으면 수집부터 직접 |

역할을 나눈 이유: 루틴 환경의 WebFetch는 mining.com(403)·icis.com(빈 응답)을 읽지 못하고(2026-09-24 점검), Cowork 예약 작업은 인터넷에서 받은 스크립트를 실행하려 하면 자동 승인 안전 검사가 '외부 코드 실행'으로 막는다(2026-09-25·26 실제로 중단). 그래서 Cowork는 읽기만, 코드는 루틴만 실행한다.

- 발행함: https://claude.ai/artifact/3SR1vSAzM6inN4WTHvjoBZ (Cowork 수집 자료 `feeds/<날짜>/`, 최근 7일)
- 기준 문서: `kit/FORMAT_GUIDE.md`(편집 원칙), `kit/brand.json`(허용 매체·규칙·인스타 규격), `kit/pipeline/channels.json`, `kit/pipeline/keywords.json`
- 발행 기록은 저장소가 전부다: `issues/<날짜>/`(카드 JPG·캡션·post.json·근거 CSV·ledger.xlsx·원문 발췌) + `published/<날짜>.json`(게시 링크). 중복 검열도 이 기록으로 한다.

## 절대 규칙

1. 기사 본문을 WebFetch로 직접 읽고 저장한 내용만 카드에 쓴다. 검색 스니펫·제목만으로 쓰지 않는다. 지어낸 숫자·인용·날짜는 한 글자도 넣지 않는다. 가상 데이터로는 카드를 만들지 않는다.
2. 가격(시세·단가) 수치는 쓰지 않는다. 가격 등락이 주제인 기사는 고르지 않는다.
3. 출처는 `brand.json > news_outlets` 허용 매체만. Yahoo Finance·MINING.COM 전재 기사는 원 발행처가 허용 매체일 때만, `via`로 표기. **영어·한국어 원문 페이지만** 쓴다 — 번역판(es.finance.yahoo.com 등)은 쓰지 않는다 (중복 검열·근거 대조가 영어·한국어 기준. 2026-09-26 스페인어판 오판정 사례)
4. 게재일은 포스트 날짜 전날~당일(`news_max_age_days: 1`)만.
5. 카드의 숫자는 모두 `sources[].evidence`(원문 문장 그대로)에 있어야 한다. 기사에 없는 계산값은 `calc: true`, 추정 구간은 `est`/`opt`.
6. **중복 금지**: 이미 게시한 기사(URL)는 다시 쓰지 않는다. 이미 게시한 사건은 **새로 확인된 사실이 있을 때만** 후속(`update_of`)으로 쓰고, 다른 매체가 같은 내용을 다시 쓴 것(예: 전날 로이터 → 오늘 NYT)은 건너뛴다. render.py가 저장소 기록과 대조해 막는다.
7. 검증 오류가 0이 될 때까지 고친다. 고칠 수 없는 뉴스는 뺀다. 게시할 뉴스가 0건이면 그날은 넘기지 않고 이유만 보고한다.
8. 카드와 캡션에 "원문과 대조했다", "검수했다" 같은 사람의 작업을 주장하는 문구를 쓰지 않는다. 편집 표기는 `brand.json > editor`("원재료 구매 담당자 발행")만.
9. 셸(curl·python)로 뉴스 사이트를 직접 받지 않는다. 뉴스 조회는 WebFetch·WebSearch만. WebFetch가 막힌 도메인은 우회하지 않고 그 후보를 버린다.
10. 인스타그램 로그인 정보·토큰은 어디에도 쓰거나 표시하지 않는다. 인스타 게시는 GitHub Actions가 저장소 Secrets로 한다. 비밀번호·토큰 입력 칸에는 아무것도 입력하지 않는다.
11. 사용자에게 질문하지 않는다(무인 실행). 판단이 필요하면 이 문서 기준으로 보수적으로 고르고(애매하면 뺀다) 보고에 적는다.
12. main 브랜치로 직접 push 하지 않는다(A 모드). 저장소의 `kit/`, `.github/`, `scripts/`, `published/` 는 고치지 않는다 — 매일 쓰는 곳은 `issues/<오늘>/` 뿐이다.

## 0단계. 준비 (A. 클라우드 루틴)

작업 위치는 저장소 루트(세션이 clone 한 폴더)다.
```bash
DATE=$(TZ=Asia/Seoul date +%F)          # 포스트 날짜 (KST)
git branch --show-current                # 작업 브랜치 (claude/…). 바꾸지 않는다
git fetch -q origin main
git cat-file -e origin/main:published/$DATE.json 2>/dev/null && echo "이미 게시됨 → 종료"
git cat-file -e origin/main:issues/$DATE/ready.json 2>/dev/null && echo "이미 넘김 → 종료"
cd kit && bash pipeline/setup.sh         # 폰트(npm)·Playwright·Chromium 준비
```
"종료"가 나오면 8단계 보고만 하고 끝낸다. 아니면 **바로 1A단계**로 간다.

### 1A단계. 발행함에서 Cowork 수집 자료 받기
1. Artifact `read` — url: 발행함, path: `feeds/$DATE/feed.json`
   - 없으면(파일 없음 오류): `sleep 300` 후 다시 읽는다. **05:50 KST까지** 반복. 그때까지 없으면 → 1단계부터 직접 한다 (아래 "직접 수집 시 제한")
2. 있으면: feed.json 의 `raw_file`(보통 `raw.json`)과 `articles[].file` 앞에 `feeds/$DATE/` 를 붙인 목록을 `paths` 로 한 번에 Artifact `read`. 결과에 나온 저장 위치에서 `feeds/$DATE/` 폴더 경로를 FROM 으로 둔다 (feed.json 도 같은 폴더에 있어야 한다)
3. 받아서 배치:
```bash
python3 pipeline/pickup.py $DATE --feed "$FROM"    # → runs/$DATE/raw/<채널>.json, runs/$DATE/articles/<id>.md
```
   - `✓ 수집 자료 받음` → **1단계는 건너뛰고 2단계부터**. Cowork가 받아 둔 원문 발췌(articles)를 4단계 근거로 그대로 쓴다 (루틴에서 못 읽는 mining.com·ICIS 기사 포함)
   - `raw.json 읽기 실패` → 원문 발췌만 받은 것. 1단계 채널 수집은 직접 한 뒤 2단계로

**직접 수집 시 제한** (루틴 환경 WebFetch 점검 2026-09-24): `mining.com`(403)·`icis.com`(빈 응답)은 읽을 수 없다. 1단계 채널 중 `miningcom-web`·`miningcom`·`icis` 는 건너뛰고 나머지 채널과 `fallback.websearch_queries`(WebSearch)로 후보를 찾는다. 본문은 WebFetch로 읽히는 곳(예: finance.yahoo.com 전재, 국내 매체)만 쓴다.

### 공통
- 다음 호수: `python3 -c "from render import load_history; h=load_history(); print(max([i.get('issue') or 0 for i in h['issues']], default=0)+1)"`
- `runs/$DATE/run_log.md` 를 만들고 이후 단계마다 한 줄씩 기록한다 (시각, 한 일, 결과).
- 전날 호가 `issues/<전날>/ready.json` 은 있는데 `published/<전날>.json` 이 없으면 **게시 실패**로 보고에 넣는다.

이하 모든 명령은 `kit/` 폴더에서 실행한다.

## 1단계. 채널 수집 (WebFetch)

`pipeline/channels.json`의 채널마다 WebFetch(url, prompt = `fetch_prompt`) → 결과 JSON 배열을 **받은 그대로** 저장:
`runs/$DATE/raw/<id>.json` = `{"channel", "url", "fetched_at"(KST ISO), "error", "items": [{"title","url","published","source","snippet"}]}`
- 실패(404·차단·빈 결과)면 `items: []`, `error`에 사유. 재시도는 1번만. Bing이 `title: Bing` 빈 페이지를 주면 URL에서 `&qft=…` 를 빼고 한 번 더.
- 채널 절반 이상이 실패하면 `fallback.websearch_queries`로 WebSearch 보충 → `raw/websearch.json`
- 채널은 사용자 지정 20개 매체(국내외)를 포함한다 (`channels.json` 각 채널의 note에 확인일·접근성). Bing `site:` 채널은 제목·링크만 모으는 용도다 — 유료·차단 매체의 본문은 열지 않는다.

## 2단계. 후보 정리

```bash
python3 pipeline/collect.py $DATE          # 저장소 게시 기록과 대조해 이미 쓴 URL은 제외, 같은 사건은 표시
```
`runs/$DATE/candidates.md` 를 읽는다.

## 3단계. 기사 고르기

**중요도 = 같은 뉴스를 함께 다룬 허용 매체 수(coverage).** 여러 매체가 동시에 다룬 뉴스를 먼저 고르고, 남는 카테고리 자리는 **원재료 구매에 유용한 단독 보도**로 채운다 (사용자 결정 2026-09-26: "원재료와 관련된 유용한 내용이면 공유"). 한도는 늘리지 않는다.
- 한도: 카테고리(비철·스틸·레진·화공)마다 **최대 1건**, 전체 **최대 4건**(`brand.json > rules.max_news`). 표지 + 뉴스 + 출처로 카드 최대 6장.
- 고르는 순서 (카테고리마다):
  1. coverage **2곳 이상**(`rules.min_coverage`)인 뉴스. `candidates.md` 의 "여러 매체가 함께 다룬 뉴스"에서 coverage 높은 묶음부터 본다. 자동 묶음은 틀릴 수 있으니 제목을 보고 확인하고, 해외·국내 기사가 같은 사건인데 따로 묶였으면 합쳐서 센다 (허용 매체만, 같은 매체는 1곳으로).
  2. 그런 뉴스가 없는 카테고리는 **유용한 단독 보도**(coverage 1곳)로 채운다. 아래 세 가지를 모두 만족해야 한다. 하나라도 아니면 그 카테고리는 비운다 (억지로 채우지 않는다).
     - 구매 판단에 쓸 **새 사실**: 생산·설비·가동(증설·감산·재가동·중단·신규 프로젝트·투자 결정·인수), 수급 전망(생산·수입·수출·재고 물량), 정책·규제·인허가·관세·무역구제의 결정·시행, 주요 메이커·국가의 공급 계약·조달처 변화
     - **구체성**: 본문에 회사·국가·설비 이름과 함께 숫자·날짜·결정 내용 중 하나 이상이 있다
     - 제외 유형이 아니다 (아래 "제외")
     - 예: 페루 정부 인허가 27개 폐지 추진·구리 증산 100만 톤 목표·중국·미국 기업 투자 관심 (2026-09-26 Reuters) → 비철 단독 보도로 적합
- 같은 단계 안에서는 우선순위: ① 공급 차질·가동 중단·불가항력·파업 ② 관세·무역구제·규제 ③ 메이커 증설·감산·투자·M&A ④ 수급 전망·수요 변화. 같으면 `candidates.md` 점수 순
- run_log 에 뉴스마다 "여러 매체 N곳" 또는 "단독 보도 — <위 새 사실 유형>"을 적는다
- 카드 근거로 쓸 기사는 묶음 안에서 **본문을 읽을 수 있는 기사**(접근 readable, 또는 전재본)를 고른다. 묶음 전체가 읽을 수 없으면 그 뉴스는 버린다 — 제목·스니펫만으로 쓰지 않는다.
- 제외: 가격 기사, 종목·실적·주가 기사, 칼럼·팟캐스트, 새 사실 없이 의견·전망 코멘트만 있는 기사, 행사·인사 기사, 이미 쓴 URL
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
- 1A에서 받은 Cowork 발췌가 있으면 그 파일을 그대로 쓴다 (다시 읽지 않는다). 출처 id 는 발췌 파일 이름(확장자 제외)과 같게 한다.
- ATTRIBUTION이 허용 매체인가 / PUBLISHED가 날짜 범위 안인가 / 본문이 있는가 — 하나라도 아니면 버리고 run_log에 사유.

## 5단계. 포스트 JSON 작성

`posts/_template.json` → `posts/${DATE}_brief.json`. `FORMAT_GUIDE.md` 2·3·5장을 따른다.
- `id`: `${DATE}-brief`, `date`: `$DATE`, `issue`: 다음 호수
- 뉴스 1건 = news 슬라이드 1장. 헤드라인 2줄(줄당 약 10자), 시각화 1~3개, 보조 사실 0~1줄, 구매 관점 1줄
- 후속 기사: `"update_of": "<이전 story_id>"` (render.py 오류 메시지에 id가 나온다). 헤드라인·시각화는 **새 사실 중심**으로. 카드에 "후속 보도"가 표시된다
- `sources[]`: publisher, via, title(원문 제목 그대로), date, time, accessed=$DATE, url, **evidence**(발췌 파일에서 그대로 복사한 문장)
- 뉴스 슬라이드마다 `"coverage"`: 같은 뉴스를 함께 다룬 허용 매체 목록 `[{"publisher", "title"(원문 제목 그대로), "url", "date"}]` — candidates.json 에서 그대로 옮긴다. **선정 근거 기록일 뿐 카드 근거가 아니다** (카드에 숫자·인용으로 쓰지 않는다). render.py 가 허용 매체·도메인을 확인한다
- 캡션: 첫 줄 `M월 D일(현지) 국내외 보도 기준 원재료 뉴스 N건.` (해외 매체만이면 `외신 보도 기준`), 번호 목록, 마지막 줄 `구매 관점은 의견이며, 정확한 내용은 각 원문을 확인하세요.` 해시태그 5개 이하

## 6단계. 검증·렌더

```bash
python3 render.py posts/${DATE}_brief.json --check     # 오류 0 될 때까지 수정 (근거·가격·매체·날짜·중복·인스타 규격)
python3 render.py posts/${DATE}_brief.json             # out/${DATE}-brief/ NN.jpg(게시용 4:5) + NN.png(보관) + ledger.xlsx
python3 pipeline/dedup.py posts/${DATE}_brief.json     # 중복 판정 내역 (보고에 요약)
```
- 카드 테마는 호수로 자동으로 정해진다: 홀수 호 다크, 짝수 호 라이트 (`brand.json > theme_rotation`, 사용자 결정 2026-09-25). 렌더 출력의 `테마:` 줄로 확인하고, 포스트 JSON에 `theme` 을 넣지 않는다
- `같은 사건 … 새 사실이 없음` 오류 → 그 뉴스를 뺀다 (매체가 달라도)
- JPG를 Read로 전부 열어 본다: 글자 잘림·겹침·빈 카드·깨진 한글이 없어야 한다

## 7단계. GitHub로 넘기기 → 07:00 자동 게시
```bash
python3 pipeline/gh_handoff.py $DATE --inplace
```
- `issues/$DATE/` 에 파일을 쓰고 커밋한 뒤 **현재 작업 브랜치**로 push 한다. Actions가 몇 분 안에 main 에 반영하고 07:00에 게시한다.
- push 가 거부되면 메시지를 그대로 보고에 넣는다. main 으로 push 를 시도하지 않는다.
- 결과: 성공 `pushed (routine)`, 실패 `failed: <사유>`

07:00 이후에 넘어오면 Actions가 받는 즉시 게시한다. 날짜가 지나면 게시하지 않는다.

### 수동 백업 (사용자가 요청할 때만): Chrome 업로드
루틴이 못 넘긴 날, 사용자가 PC를 켜 두고 요청하면 Cowork에서 `python3 pipeline/gh_handoff.py $DATE --prepare` → Claude in Chrome 으로 `upload_url` 에 `paths` 전부 업로드 → Commit changes (클릭 후 저장소 화면으로 바뀔 때까지 기다린다) → `$RAW/issues/$DATE/ready.json` 200 확인.

## 8단계. 보고

마지막 메시지(한국어, 짧게): 받은 곳(Cowork 수집 자료 / 직접 수집) / 넘긴 뉴스·매체 / 재검증 결과·경고 / push 결과(브랜치·커밋)와 07:00 게시 예정 / 직접 제작했다면 뺀 후보와 이유 / 전날 게시 실패가 있으면 그 사실.
같은 내용을 gh_handoff 전에 `runs/$DATE/run_log.md` 에 적는다.

---

## P. Cowork 수집 절차 (04:00 Cowork 예약 작업 — 코드 실행 없음)

**Python·셸 스크립트를 실행하지 않는다** (인터넷에서 받은 코드 실행은 자동 승인 안전 검사가 막는다). 쓰는 도구: Bash는 날짜·상태 확인(`date`, `curl -s -o /dev/null -w "%{http_code}"`)만, 나머지는 Projects(프로젝트 문서 읽기)·WebFetch·WebSearch·Write(파일 쓰기)·Artifact(발행함 읽기·올리기)·SendUserMessage.
위 **절대 규칙**은 모두 적용된다 (특히 1·2·3·4·9·10).

### P0. 확인·준비
1. `DATE=$(TZ=Asia/Seoul date +%F)`. `https://raw.githubusercontent.com/welcome2oz/raw-materials-daily/main/published/$DATE.json` 과 `.../issues/$DATE/ready.json` 의 HTTP 코드를 확인 — 하나라도 200이면 이미 처리됨 → 한 줄 보고하고 끝.
2. Projects `project_read` 로 읽는다: `cardnews-kit/pipeline/channels.json`(채널·fetch_prompt), `cardnews-kit/brand.json`(허용 매체 `news_outlets`, `rules`), `cardnews-kit/pipeline/keywords.json`(카테고리·가격 기사 판정 단어).
3. 작업 폴더: 세션 시작 폴더 아래 `feeds/$DATE/` (파일은 Write 도구로 쓴다).

### P1. 채널 수집
channels.json 의 채널마다 WebFetch(url, prompt = `fetch_prompt`). 결과를 **받은 그대로** 모아 `feeds/$DATE/raw.json` 하나로 쓴다:
```json
{"<채널 id>": {"channel": "<id>", "url": "...", "fetched_at": "<KST ISO>", "error": "", "items": [{"title": "", "url": "", "published": "", "source": "", "snippet": ""}]}}
```
- 실패(404·차단·빈 결과)면 `items: []`, `error` 에 사유. 재시도 1번. Bing이 `title: Bing` 빈 페이지면 `&qft=…` 빼고 한 번 더.
- 올바른 JSON 이어야 한다 (제목 안의 큰따옴표는 `\"` 로). Bing 링크는 받은 그대로 둔다 (루틴의 collect.py 가 원문 주소로 푼다).

### P2. 원문 발췌 (루틴이 못 읽는 곳 위주)
P1 결과에서 아래를 모두 만족하는 기사를 고른다 — 허용 매체(또는 원 발행처가 허용 매체인 전재) / 게재일 전날~당일 / 가격 기사·종목·칼럼 아님 / 4개 카테고리 중 하나 / 영어·한국어 원문.
- 여러 매체가 함께 다룬 사건을 먼저, 그다음 **구매에 유용한 단독 보도**(3단계 고르는 순서 2의 기준: 생산·설비·투자·수급 전망·규제·관세·공급 계약의 새 사실 + 구체적인 이름·숫자·결정)를 읽는다. 카테고리마다 최대 3건, **전체 최대 12건**. 같은 사건은 가장 본문이 온전한 1건(전재본 포함)만.
- 같은 기사가 여러 링크로 보이면(예: Bing의 aol.com 링크와 mining.com/web/ 전재) **허용 매체 도메인 링크**를 연다.
- 특히 루틴이 못 읽는 `mining.com`·`icis.com` 기사는 여기서 꼭 읽어 둔다. Reuters·Bloomberg 원문(reuters.com 등)은 차단이니 Yahoo Finance·MINING.COM `/web/` 전재본을 연다.
- 기사마다 id 를 정하고(예 `reu-escondida-restart`) RUNBOOK 4단계의 WebFetch prompt 로 읽어, 받은 내용을 그대로 `feeds/$DATE/articles/<id>.md` 에 쓴다. 머리말 4줄: `source_id: <id>` / `url: <열어 본 URL>` / `fetched_at: <KST ISO>` / `method: WebFetch (Cowork)`.
- 본문이 없거나(BODY NOT AVAILABLE만) ATTRIBUTION 이 허용 매체가 아니면 파일을 만들지 않는다.

### P3. feed.json
`feeds/$DATE/feed.json`:
```json
{"date": "<DATE>", "created_at": "<KST ISO>", "created_by": "cowork", "raw_file": "raw.json",
 "channels": [{"id": "", "items": 0, "error": ""}],
 "articles": [{"id": "", "file": "articles/<id>.md", "url": "", "headline": "", "attribution": "", "published": "", "category": "", "also_covered_by": ["<다른 허용 매체>"]}],
 "notes": "고른 이유·뺀 후보 한두 줄"}
```

### P4. 발행함에 올리기
1. Artifact `read` — url: 발행함, path: `index.html` (페이지 파일을 받아 둔다). Artifact `list` scope `files` 로 올라가 있는 파일 목록도 본다.
2. Artifact publish — `url`: 발행함, `file_path`: 받아 둔 index.html, `files`: `{"feeds/$DATE/feed.json": ..., "feeds/$DATE/raw.json": ..., "feeds/$DATE/articles/<id>.md": ...}` + 목록에 있는 **7일 지난 `feeds/<날짜>/…` 파일은 `null`**(삭제). `capabilities` 는 넘기지 않는다.
3. Artifact `read` path `feeds/$DATE/feed.json` 으로 올라갔는지 확인.

### P5. 보고
SendUserMessage (한국어, 3~5줄): 채널 성공·실패 수 / 읽어 둔 원문 발췌 수와 카테고리 / 발행함 올림 결과 / "05:00 루틴이 카드를 만들어 07:00 게시". 발췌할 기사가 0건이어도 raw.json·feed.json 은 올린다 (루틴이 이어서 판단).

