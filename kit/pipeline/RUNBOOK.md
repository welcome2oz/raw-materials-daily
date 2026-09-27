# RAW MATERIALS DAILY — 매일 발행 절차 (RUNBOOK)

매일 새벽 이 문서대로 카드뉴스를 만들어 GitHub 저장소 `welcome2oz/raw-materials-daily` 로 넘기면, 저장소의 GitHub Actions(`publish.yml`)가 **07:00(KST)에 인스타그램 @raw_material_procurement 에 자동 게시**한다.
결과물은 **인스타그램 공식 API 규격: 4:5(1080×1350) JPEG, 캐러셀 최대 10장** + 캡션.

실행 모드는 둘이다. 둘 다 클라우드에서 돌아 **PC가 꺼져 있어도 된다.**

| 모드 | 언제 | 어디서 | 하는 일 |
|---|---|---|---|
| **P. Cowork 수집** | 매일 02:50 KST (04:40까지 발행함에 올림) | Cowork 예약 작업 | **코드를 실행하지 않는다.** WebFetch로 채널 목록과 기사 원문을 읽고, WebSearch로 보충 후보·전재본·함께 보도 매체를 찾아 파일로 쓰고 발행함에 올린다 (`feeds/<날짜>/`). 카드 소스를 최대한 많이 확보하는 것이 목표. 절차는 맨 아래 "P. Cowork 수집 절차" |
| **A. 클라우드 루틴** | 매일 05:00 KST | Claude Code 루틴 (저장소 연결) | 발행함 수집 자료를 받아 0~8단계: 후보 정리·선정·카드 제작·검증 → 작업 브랜치(`claude/…`) push. 발행함 자료가 없으면 기다리지 않고(1분씩 최대 3번 확인) 수집부터 직접 |


**게시 확인(감시)**: 매일 07:20 KST Cowork 예약 작업 '원재료 카드뉴스 게시 확인 (07:20)'이 `published/<날짜>.json` 을 확인하고, 게시가 안 됐을 때만 원인 단서(수집 자료·ready.json·두 작업 실행 시각)와 할 일을 휴대폰 알림으로 보낸다. 확인·알림만 하고 제작·실행은 하지 않는다 (2026-09-26 추가).

역할을 나눈 이유: 루틴 환경의 WebFetch는 mining.com(403)·icis.com(빈 응답)을 읽지 못하고(2026-09-24 점검), Cowork 예약 작업은 인터넷에서 받은 스크립트를 실행하려 하면 자동 승인 안전 검사가 '외부 코드 실행'으로 막는다(2026-09-25·26 실제로 중단). 그래서 Cowork는 읽기만, 코드는 루틴만 실행한다.

- 발행함: https://claude.ai/artifact/3SR1vSAzM6inN4WTHvjoBZ (Cowork 수집 자료 `feeds/<날짜>/`, 최근 7일)
- 기준 문서: `kit/FORMAT_GUIDE.md`(편집 원칙), `kit/brand.json`(허용 매체·규칙·인스타 규격), `kit/pipeline/channels.json`, `kit/pipeline/keywords.json`
- 발행 기록은 저장소가 전부다: `issues/<날짜>/`(카드 JPG·캡션·post.json·근거 CSV·ledger.xlsx·원문 발췌) + `published/<날짜>.json`(게시 링크). 중복 검열도 이 기록으로 한다.

## 절대 규칙

1. 기사 본문을 WebFetch로 직접 읽고 저장한 내용만 카드에 쓴다. 검색 스니펫·제목만으로 쓰지 않는다. 지어낸 숫자·인용·날짜는 한 글자도 넣지 않는다. 가상 데이터로는 카드를 만들지 않는다.
2. 가격(시세·단가) 수치는 쓰지 않는다. 가격 등락이 주제인 기사는 고르지 않는다.
3. 출처는 `brand.json > news_outlets` 허용 매체만. Yahoo Finance·Investing.com·MINING.COM 전재 기사는 원 발행처가 허용 매체일 때만, `via`로 표기. **Investing.com 은 Reuters 전재본('By Reuters')만** 쓴다 — 자체 기사(Bloomberg 등 재인용 포함), URL에 `93CH-` 가 붙은 AI 작성 기사, kr.investing.com(AI 번역판)은 안 된다(render.py 오류, 사용자 요청 2026-09-27). **세계 주요 기관·정부 발표**(`news_outlets.institutions`: OECD·IEA·IAI·ICSG·worldsteel·WTO·WCO·UNEP·OPEC·미국 EIA·연방관보·USTR·상무부·EPA·EU 집행위·산업통상부·무역위원회·중국 상무부)도 1차 출처로 쓴다 — 기관 누리집의 발표문·통계·결정문을 직접 읽은 것만 인정하고, 기관을 인용한 비허용 매체 기사(예: Sputnik 의 IAI 통계 보도)는 쓰지 않는다 (사용자 결정 2026-09-27). **영어·한국어 원문 페이지만** 쓴다 — 번역판(es.finance.yahoo.com 등)은 쓰지 않는다 (중복 검열·근거 대조가 영어·한국어 기준. 2026-09-26 스페인어판 오판정 사례)
4. 게재일은 **한국시간(KST) 기준** 포스트 날짜 전날~당일(`news_max_age_days: 1`). 기사에 찍힌 현지 날짜만 보고 빼지 않는다 — 시각이 있으면 한국시간으로 바꿔 판단한다 (예: 미국 금요일 16:14 UTC 기사 = 한국 토요일 01:14 → 일요일 호 범위 안. 2026-09-27 페루 구리 기사를 현지 날짜로 빼서 0건이 된 사례). **일·월요일 호**는 해외 주말 공백 때문에 지난 7일(`rules.weekend_lookback_days`) 안의 아직 게시하지 않은 뉴스도 쓴다 (사용자 결정 2026-09-27). render.py·collect.py 가 같은 기준으로 검사한다 (`render.news_window_days`).
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
   - 없으면(파일 없음 오류): 긴 `sleep` 으로 기다리지 않는다 (셸의 긴 sleep 은 막히거나 시간 초과가 난다). `sleep 55` 로 1분씩 **최대 3번만** 다시 읽고, 그래도 없으면 → 곧바로 1단계부터 직접 한다 (아래 "직접 수집 시 제한"). Artifact 도구로 발행함을 읽지 못하면(도구 없음·오류) 그 오류 문구를 run_log·보고에 그대로 적고 1단계부터 직접 한다
   - **자료가 없다는 이유만으로 세션을 끝내지 않는다.** 세션은 7단계 push 성공, 또는 3단계 '게시할 뉴스 0건' 판정과 사유 보고 중 하나로만 끝낸다 (2026-09-25·26: 05:00 실행이 자료 없이 2분 만에 끝나 게시 누락)
2. 있으면: feed.json 의 `raw_file`(보통 `raw.json`)과 `articles[].file` 앞에 `feeds/$DATE/` 를 붙인 목록을 `paths` 로 한 번에 Artifact `read`. 결과에 나온 저장 위치에서 `feeds/$DATE/` 폴더 경로를 FROM 으로 둔다 (feed.json 도 같은 폴더에 있어야 한다)
3. 받아서 배치:
```bash
python3 pipeline/pickup.py $DATE --feed "$FROM"    # → runs/$DATE/raw/<채널>.json, runs/$DATE/articles/<id>.md
```
   - `✓ 수집 자료 받음` → **1단계는 건너뛰고 2단계부터**. Cowork가 받아 둔 원문 발췌(articles)를 4단계 근거로 그대로 쓴다 (루틴에서 못 읽는 mining.com·ICIS 기사 포함)
   - `raw.json 읽기 실패` → 원문 발췌만 받은 것. 1단계 채널 수집은 직접 한 뒤 2단계로

**직접 수집 시 제한** (루틴 환경 WebFetch 점검 2026-09-24): `mining.com`(403)·`icis.com`(빈 응답)은 읽을 수 없다. 1단계 채널 중 `miningcom-web`·`miningcom`·`icis` 는 건너뛰고 나머지 채널과 `fallback.websearch_queries`(WebSearch)로 후보를 찾는다. 본문은 WebFetch로 읽히는 곳(예: finance.yahoo.com·investing.com 의 Reuters 전재, 국내 매체)만 쓴다.

### 공통
- 다음 호수: `python3 -c "from render import next_issue; print(next_issue('$DATE'))"` — `brand.json > issue_numbering` 기준(2026-09-27 호부터 No.1 로 다시 시작, 사용자 결정 2026-09-26). render.py 가 호수가 맞는지 검사한다
- `runs/$DATE/run_log.md` 를 만들고 이후 단계마다 한 줄씩 기록한다 (시각, 한 일, 결과).
- 전날 호가 `issues/<전날>/ready.json` 은 있는데 `published/<전날>.json` 이 없으면 **게시 실패**로 보고에 넣는다.

이하 모든 명령은 `kit/` 폴더에서 실행한다.

## 1단계. 채널 수집 (WebFetch)

`pipeline/channels.json`의 채널마다 WebFetch(url, prompt = `fetch_prompt`) → 결과 JSON 배열을 **받은 그대로** 저장:
`runs/$DATE/raw/<id>.json` = `{"channel", "url", "fetched_at"(KST ISO), "error", "items": [{"title","url","published","source","snippet"}]}`
- 실패(404·차단·빈 결과)면 `items: []`, `error`에 사유. 재시도는 1번만. Bing이 `title: Bing` 빈 페이지를 주면 URL에서 `&qft=…` 를 빼고 한 번 더.
- 채널 절반 이상이 실패하면 `fallback.websearch_queries`로 WebSearch 보충 → `raw/websearch.json`
- 채널은 사용자 지정 20개 매체(국내외)와 **세계 주요 기관 발표 채널**(worldsteel·IAI·IEA·미국 EIA·WCO·UNEP·연방관보·USTR·EU 집행위·산업통상부), **Investing.com RSS 3개**(원자재·증시·경제 — author 'Reuters' 항목이 Reuters 전재본)를 포함한다 (`channels.json` 각 채널의 note에 확인일·접근성). Bing `site:` 채널은 제목·링크만 모으는 용도다 — 유료·차단 매체의 본문은 열지 않는다.

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
     - 기관 발표도 같은 기준이다: 생산·수출입 통계(worldsteel 월간 조강 생산, IAI 월간 알루미늄 생산 등), 관세·반덤핑·세이프가드 결정(연방관보·EU 집행위·무역위원회), 규제 시행(냉매·몬트리올 의정서) → 새 사실. 기관의 전망·의견만 있는 발표는 제외
- 같은 단계 안에서는 우선순위: ① 공급 차질·가동 중단·불가항력·파업 ② 관세·무역구제·규제 ③ 메이커 증설·감산·투자·M&A ④ 수급 전망·수요 변화. 같으면 `candidates.md` 점수 순
- run_log 에 뉴스마다 "여러 매체 N곳" 또는 "단독 보도 — <위 새 사실 유형>"을 적는다
- 카드 근거로 쓸 기사는 묶음 안에서 **본문을 읽을 수 있는 기사**(접근 readable, 또는 전재본)를 고른다. 묶음 전체가 읽을 수 없으면 그 뉴스는 버린다 — 제목·스니펫만으로 쓰지 않는다.
- 제외: 가격 기사, 종목·실적·주가 기사, 칼럼·팟캐스트, 새 사실 없이 의견·전망 코멘트만 있는 기사, 행사·인사 기사, 이미 쓴 URL
- `같은 사건 추정` 표시가 붙은 후보: 본문을 읽고 이전 호에 없던 **새 사실**(상태 변화, 새 날짜, 사건과 관련된 새 숫자)이 있을 때만 후속으로 쓴다. 매체만 다르고 내용이 같으면 버린다.
- `access: blocked` 후보는 WebSearch `"<원문 제목>" Yahoo Finance`, `"<제목>" investing.com`(allowed_domains `["investing.com"]`) 또는 `"<제목>" mining.com` 으로 전재본을 찾는다. `finance.yahoo.com`·`www.investing.com`('By Reuters' 만)·`mining.com/web/` 에서 제목이 같은 것만 인정. 없으면 버린다.
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
- 캡션: 첫 줄 `M월 D일(현지) 국내외 보도 기준 원재료 뉴스 N건.` (해외 매체만이면 `외신 보도 기준`, 기관 발표가 들어가면 `국내외 보도·기관 발표 기준`), 번호 목록, 마지막 줄 `구매 관점은 의견이며, 정확한 내용은 각 원문을 확인하세요.` 해시태그 5개 이하
  - 일·월요일 호처럼 게재일이 여러 날이면 첫 줄을 `M월 D일~D일(현지) … 기준`으로 쓰고, 표지 `sub` 도 같은 기간으로 쓴다

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

## P. Cowork 수집 절차 (02:50 Cowork 예약 작업 — 코드 실행 없음)

**목표: 카드로 만들 수 있는 원문 발췌를 최대한 많이 확보한다** (사용자 결정 2026-09-26). 루틴은 카테고리당 1건·전체 4건만 쓰지만, 읽어 둔 후보가 많을수록 빈 카테고리가 줄고 '여러 매체 함께 보도'(coverage) 판단도 정확해진다.

**Python·셸 스크립트를 실행하지 않는다** (인터넷에서 받은 코드 실행은 자동 승인 안전 검사가 막는다). 쓰는 도구: Bash는 날짜·상태 확인(`date`, `curl -s -o /dev/null -w "%{http_code}"`)만, 나머지는 Projects(프로젝트 문서 읽기)·WebFetch·WebSearch·Write(파일 쓰기)·Artifact(발행함 읽기·올리기)·SendUserMessage.
위 **절대 규칙**은 모두 적용된다 (특히 1·2·3·4·9·10). WebSearch 결과(제목·링크)는 **후보를 찾는 용도**일 뿐이고, 카드 근거는 WebFetch로 읽은 본문뿐이다.

**시간**: 02:50 KST에 시작해 **04:40 KST가 되면** 남은 검색·읽기를 멈추고 P3로 넘어간다 — 05:00 루틴이 시작할 때 발행함에 자료가 이미 있어야 한다 (루틴은 오래 기다리지 않는다).

### P0. 확인·준비
1. `DATE=$(TZ=Asia/Seoul date +%F)`. `https://raw.githubusercontent.com/welcome2oz/raw-materials-daily/main/published/$DATE.json` 과 `.../issues/$DATE/ready.json` 의 HTTP 코드를 확인 — 하나라도 200이면 이미 처리됨 → 한 줄 보고하고 끝.
2. Projects `project_read` 로 읽는다: `cardnews-kit/pipeline/channels.json`(채널·fetch_prompt·`websearch`), `cardnews-kit/brand.json`(허용 매체 `news_outlets`, `rules`), `cardnews-kit/pipeline/keywords.json`(카테고리·가격 기사 판정 단어).
3. 작업 폴더: 세션 시작 폴더 아래 `feeds/$DATE/` (파일은 Write 도구로 쓴다).

### P1. 채널 수집
channels.json 의 채널마다 WebFetch(url, prompt = `fetch_prompt`). 결과를 **받은 그대로** 모아 `feeds/$DATE/raw.json` 하나로 쓴다:
```json
{"<채널 id>": {"channel": "<id>", "url": "...", "fetched_at": "<KST ISO>", "error": "", "items": [{"title": "", "url": "", "published": "", "source": "", "snippet": ""}]}}
```
- 실패(404·차단·빈 결과)면 `items: []`, `error` 에 사유. 재시도 1번. Bing이 `title: Bing` 빈 페이지면 `&qft=…` 빼고 한 번 더.
- 올바른 JSON 이어야 한다 (제목 안의 큰따옴표는 `\"` 로). Bing 링크는 받은 그대로 둔다 (루틴의 collect.py 가 원문 주소로 푼다).

### P1b. WebSearch 보충 (매일 — 채널 결과와 상관없이)
Commodity news briefing(07:00 카톡 예약)과 같은 주제를 여기서 직접 검색한다. 브리핑 문장·검색 스니펫은 쓰지 않고 **기사 링크만 후보로** 받는다.
1. `channels.json > websearch.discovery_queries` 를 하나씩 WebSearch. `{d0}` 은 포스트 날짜 전날을 영어로(예 `September 25, 2026`). 일·월요일 호는 `{d0}` 을 직전 금요일로 한 번 더 검색한다. `allowed_domains` 는 넣지 않는다 (reuters.com·bloomberg.com·asia.nikkei.com 이 들어가면 검색이 거부된다).
2. 결과 중 **brand.json 허용 매체 도메인**(하위 도메인 포함)만 남긴다. 번역판 도메인(es.·fr.·de. 등으로 시작)과 기사가 아닌 페이지(위키·회사 소개·시세·종목 페이지)는 버린다. URL에 날짜가 있고 게재일 범위 밖이면 버린다.
3. raw.json 에 채널 `websearch` 로 넣는다: `{"channel": "websearch", "url": "WebSearch", "fetched_at": "<KST ISO>", "error": "", "queries": [실행한 검색어], "items": [{"title": 결과 제목 그대로, "url": 결과 링크 그대로, "published": URL에 날짜가 있으면 그 날짜(YYYY-MM-DD) 아니면 "", "source": "", "snippet": ""}]}`. 같은 URL은 한 번만.
   - `published` 를 추측으로 채우지 않는다. 모르면 비워 둔다 — P2에서 읽으면 채우고, 안 읽은 것은 루틴이 '게재일 확인 필요'로 다룬다.

### P2. 원문 발췌 — 최대한 많이
후보 = P1 + P1b 결과. 아래를 모두 만족하는 기사: 허용 매체·기관(또는 원 발행처가 허용 매체인 전재) / 게재일이 범위 안(절대 규칙 4: **한국시간 기준**, 일·월요일 호는 지난 7일 — 현지 날짜만 보고 빼지 않는다) / 가격 기사·종목·칼럼·행사·인사 아님 / 4개 카테고리 중 하나 / 영어·한국어 원문.

1. **읽을 목록**: 여러 매체가 함께 다룬 사건을 먼저, 그다음 **구매에 유용한 단독 보도**(3단계 고르는 순서 2의 기준: 생산·설비·투자·수급 전망·규제·관세·공급 계약의 새 사실 + 구체적인 이름·숫자·결정). **카테고리마다 최대 5건, 전체 최대 20건.** 같은 사건은 본문이 가장 온전한 1건만 읽고, 나머지 매체는 함께 보도로 기록한다.
   - 한 카테고리가 비면 그 카테고리의 discovery 검색어를 `{d1}`(포스트 날짜)로 바꿔 한 번 더 찾는다.
2. **본문을 못 읽는 매체 → 전재본 찾기**: 후보가 reuters.com·bloomberg.com·wsj.com·ft.com·asia.nikkei.com·argusmedia.com·spglobal.com·cnbc.com·apnews.com 등이면 WebSearch 로 전재본을 찾는다 — 검색어는 원문 제목의 핵심 단어, `allowed_domains: ["finance.yahoo.com"]`, 없으면 `["investing.com"]`, 그래도 없으면 `["mining.com"]`.
   - 제목이 같은 기사만 인정한다. finance.yahoo.com 영어 지역판(ca.·uk.·sg.·au.)은 되고, 번역판은 안 된다.
   - investing.com 은 기사 상단이 'By Reuters' 인 것만 (원 발행처 = Reuters). `www.`·영어 지역판(uk.·ca.·au.·in.·za.·ng.)만 되고, kr.investing.com 등 번역판과 URL에 `93CH-` 가 붙은 AI 작성 기사는 안 된다. 사례(2026-09-27 확인): Reuters 'Chinese, US firms line up for Peru copper projects…'(9/25)가 investing.com 에 본문 전체로 실려 있음.
   - 읽었을 때 ATTRIBUTION 이 원 발행처(예: Reuters)여야 한다. 같은 주제를 다른 발행처(Proactive·Motley Fool 등)가 쓴 기사는 전재본이 아니다.
   - 찾은 전재본 링크는 raw.json 채널 `websearch-syndication` 에 넣는다 (형식은 P1b와 같고 `source` 는 원 발행처 이름) → 루틴의 collect.py 가 같은 기사로 묶고 읽을 수 있는 링크를 대표로 쓴다.
   - 사례(2026-09-26): Escondida 노조 협상 중단 거부(Reuters)는 전재본을 못 찾아 버림. ArcelorMittal Kryvyi Rih 재가동 불가는 Yahoo Finance 에 있었지만 Proactive 기사라 불가.
3. **함께 보도 매체 찾기 (coverage)**: 읽기로 한 사건마다 WebSearch 1번 — 회사·설비·국가 이름 + 사건 단어(예 `JFE Steel Chiba output typhoon`), `allowed_domains` 없이.
   - 허용 매체 도메인이고, 제목이 분명히 같은 사건이며, 게재일이 범위 안인 것만 센다. 날짜는 URL 날짜로 확인하고, 없으면 읽을 수 있는 곳은 WebFetch 로 확인, 못 읽는 곳은 뺀다.
   - 허용 매체가 아닌 곳(Kallanish·MarketScreener·AOL 등)은 세지 않는다. investing.com 은 전재 호스트라 Reuters 전재본이면 **Reuters 로** 센다(원문과 같은 기사면 1곳), 자체 기사는 세지 않는다.
   - 센 기사는 raw.json 채널 `websearch-coverage` 에 넣고(형식은 P1b와 같음), feed.json `also_covered_by` 에 매체 이름을 적는다.
4. **읽기**: 기사마다 id 를 정하고(예 `reu-escondida-restart`) RUNBOOK 4단계의 WebFetch prompt 로 읽어, 받은 내용을 그대로 `feeds/$DATE/articles/<id>.md` 에 쓴다. 머리말 4줄: `source_id: <id>` / `url: <열어 본 URL>` / `fetched_at: <KST ISO>` / `method: WebFetch (Cowork)`.
   - 같은 기사가 여러 링크로 보이면(예: Bing의 aol.com 링크와 mining.com/web/ 전재) **허용 매체 도메인 링크**를 연다. 루틴이 못 읽는 `mining.com`·`icis.com` 기사는 여기서 꼭 읽어 둔다.
   - 본문이 없거나(BODY NOT AVAILABLE만), ATTRIBUTION 이 허용 매체가 아니거나, PUBLISHED 가 범위 밖이면 파일을 만들지 않는다 (raw.json 의 링크는 그대로 둔다).
   - `websearch`·`websearch-syndication` 항목을 읽었으면 raw.json 의 그 항목 `published` 를 읽은 PUBLISHED 문자열로, `source` 를 ATTRIBUTION 의 발행처로 채운다.

### P3. feed.json
`feeds/$DATE/feed.json`:
```json
{"date": "<DATE>", "created_at": "<KST ISO>", "created_by": "cowork", "raw_file": "raw.json",
 "channels": [{"id": "", "items": 0, "error": ""}],
 "websearch": {"discovery_queries": 0, "discovery_items": 0, "syndication_found": 0, "syndication_missed": ["<전재본을 못 찾은 제목>"], "coverage_items": 0},
 "articles": [{"id": "", "file": "articles/<id>.md", "url": "", "headline": "", "attribution": "", "published": "", "category": "", "also_covered_by": ["<다른 허용 매체>"]}],
 "notes": "고른 이유·뺀 후보 한두 줄"}
```

### P4. 발행함에 올리기
1. Artifact `read` — url: 발행함, path: `index.html` (페이지 파일을 받아 둔다). Artifact `list` scope `files` 로 올라가 있는 파일 목록도 본다.
2. Artifact publish — `url`: 발행함, `file_path`: 받아 둔 index.html, `files`: `{"feeds/$DATE/feed.json": ..., "feeds/$DATE/raw.json": ..., "feeds/$DATE/articles/<id>.md": ...}` + 목록에 있는 **7일 지난 `feeds/<날짜>/…` 파일은 `null`**(삭제). `capabilities` 는 넘기지 않는다.
   - "live version 을 보지 않았다"며 거부되면 그 응답이 최신본을 보여 준 것이다. 페이지 파일이 받아 둔 것과 같으면 같은 요청을 다시 보낸다(두 번째 거부 후 한 번 더 보내면 올라간다 — 2026-09-26 확인).
3. Artifact `read` path `feeds/$DATE/feed.json` 으로 올라갔는지 확인.

### P5. 보고
SendUserMessage (한국어, 3~6줄): 채널 성공·실패 수 / WebSearch 보충(검색어 수·남은 후보 수·찾은 전재본 수·함께 보도 매체 수) / 읽어 둔 원문 발췌 수와 카테고리 / 발행함 올림 결과 / "05:00 루틴이 카드를 만들어 07:00 게시". 발췌할 기사가 0건이어도 raw.json·feed.json 은 올린다 (루틴이 이어서 판단).
