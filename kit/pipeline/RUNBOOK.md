# RAW MATERIALS DAILY — 매일 발행 절차 (RUNBOOK)

매일 새벽 이 문서대로 카드뉴스를 만들어 GitHub 저장소 `welcome2oz/raw-materials-daily` 로 넘기면, 저장소의 GitHub Actions(`publish.yml`)가 **07:00(KST)에 인스타그램 @raw_material_procurement 에 자동 게시**한다.
결과물은 **인스타그램 공식 API 규격: 4:5(1080×1350) JPEG, 캐러셀 최대 10장** + 캡션.

실행 모드는 둘이다. 둘 다 클라우드에서 돌아 **PC가 꺼져 있어도 된다.** 단계마다 해당 모드만 따른다.

| 모드 | 언제 | 어디서 | 하는 일 |
|---|---|---|---|
| **P. Cowork 제작** | 매일 04:00 KST | Cowork 예약 작업 | 뉴스 수집·원문 발췌·검증·카드 제작(1~6단계) → **발행함**(허브 아티팩트)에 오늘 호와 `handoff.json` 을 올린다. GitHub에는 쓰지 않는다 |
| **A. 클라우드 루틴** | 매일 05:00 KST | Claude Code 루틴 (저장소 연결) | 발행함에서 오늘 호를 받아 **다시 검증** → 저장소에 커밋 → 작업 브랜치(`claude/…`) push. 05:50까지 발행함에 호가 없으면 직접 제작(1~6단계) |

역할을 나눈 이유 (2026-09-24 점검): 루틴 환경의 WebFetch는 mining.com(403)·icis.com(빈 응답)을 읽지 못하고, Cowork 환경은 GitHub에 push 하지 못한다. Cowork는 기사를 읽고, 루틴은 GitHub에 넘긴다.

- 발행함: https://claude.ai/artifact/3SR1vSAzM6inN4WTHvjoBZ (최근 7일 호, 목록 issues.json)
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

### P. Cowork 제작
```bash
DATE=$(TZ=Asia/Seoul date +%F)
RAW=https://raw.githubusercontent.com/welcome2oz/raw-materials-daily/main
curl -s -o /dev/null -w "%{http_code}\n" $RAW/issues/$DATE/ready.json    # 200 → 이미 넘어감 → 종료
curl -s -o /dev/null -w "%{http_code}\n" $RAW/published/$DATE.json       # 200 → 이미 게시됨 → 종료
```
200이 하나라도 나오면 한 줄 보고하고 끝낸다. 아니면 세션 시작 폴더(pwd) 아래로 저장소를 받아 온다 (Cowork는 git clone 불가, raw 읽기만 됨):
```bash
curl -fsSL $RAW/kit/pipeline/mirror_repo.py -o mirror_repo.py && python3 mirror_repo.py repo
cd repo/kit && bash pipeline/setup.sh
```
Artifact `read` — url: 발행함, path: `issues.json` → 저장된 파일을 `hub_index.json` 으로 복사 (없으면 빈 목록으로 진행).

### A. 클라우드 루틴
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

### 1A단계 (A 전용). 발행함에서 오늘 호 받기
1. Artifact `read` — url: 발행함, path: `issues/$DATE/handoff.json`
   - 없으면(파일 없음 오류): `sleep 300` 후 다시 읽는다. **05:50 KST까지** 반복. 그때까지 없으면 → P 제작이 실패한 것 → 1~6단계를 직접 한다 (아래 "A 직접 제작 시 제한" 참고) → 7A단계
2. 있으면: handoff.json 의 `files[].path` 앞에 `issues/$DATE/` 를 붙인 목록을 `paths` 로 한 번에 Artifact `read`. 결과에 나온 저장 위치에서 `issues/$DATE/` 폴더 경로를 FROM 으로 둔다 (handoff.json 도 같은 폴더에 있어야 한다)
3. 받아서 재검증:
```bash
python3 pipeline/pickup.py $DATE --from "$FROM"      # sha256 대조 → 배치 → 근거표 재생성 → 검증(근거·중복·인스타 규격)
```
   - `✓ 받음·재검증 통과` → 7A단계
   - sha256 불일치 → 2번을 한 번 더. 그래도 실패하면 직접 제작
   - 검증 오류(예: 중복) → 넘기지 않고 오류를 보고한다 (P 제작 이후 게시 기록이 바뀐 경우 등). 직접 제작으로 넘어가지 않는다

**A 직접 제작 시 제한** (루틴 환경 WebFetch 점검 2026-09-24): `mining.com`(403)·`icis.com`(빈 응답)은 읽을 수 없다. 1단계 채널 중 `miningcom-web`·`miningcom`·`icis` 는 건너뛰고 나머지 채널과 `fallback.websearch_queries`(WebSearch)로 후보를 찾는다. 국내·기타 매체 채널은 루틴 환경에서 확인되지 않았으니 실패하면 사유만 기록한다. 본문은 WebFetch로 읽히는 곳(예: finance.yahoo.com 전재)만 쓴다.

### 공통 (P 제작, A 직접 제작)
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

**중요도 = 같은 뉴스를 함께 다룬 허용 매체 수(coverage).** 여러 매체가 동시에 다룬 뉴스일수록 중요한 뉴스로 보고 그 순서로 고른다. 기사 수는 늘리지 않는다.
- 한도: 카테고리(비철·스틸·레진·화공)마다 **최대 1건**, 전체 **최대 4건**(`brand.json > rules.max_news`). 표지 + 뉴스 + 출처로 카드 최대 6장.
- `candidates.md` 의 "여러 매체가 함께 다룬 뉴스"에서 coverage 높은 묶음부터 본다. 자동 묶음은 틀릴 수 있으니 제목을 보고 확인하고, 해외·국내 기사가 같은 사건인데 따로 묶였으면 합쳐서 센다 (허용 매체만, 같은 매체는 1곳으로).
- 기준: coverage **2곳 이상**(`rules.min_coverage`)인 뉴스만 쓴다. 2곳 이상이 없는 카테고리는 비운다.
  예외: 그렇게 해서 전체가 1건 이하면, coverage 1곳이라도 우선순위 ①에 해당하는 뉴스로 최대 2건까지 채우고 run_log 에 "예외: 단독 보도"를 적는다.
- coverage가 같으면 우선순위: ① 공급 차질·가동 중단·불가항력·파업 ② 관세·무역구제·규제 ③ 메이커 증설·감산·M&A ④ 수요 변화
- 카드 근거로 쓸 기사는 묶음 안에서 **본문을 읽을 수 있는 기사**(접근 readable, 또는 전재본)를 고른다. 묶음 전체가 읽을 수 없으면 그 뉴스는 버린다 — 제목·스니펫만으로 쓰지 않는다.
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

## 7단계. 넘기기

### P. Cowork 제작 → 발행함
```bash
python3 pipeline/hub_stage.py $DATE --index ../../hub_index.json    # 재검증 → hub_stage/ + handoff.json + files.json
cat hub_stage/files.json
```
Artifact publish — `url`: 발행함, `file_path`: `pipeline/hub/index.html`, `files`: files.json 그대로 (값이 null인 항목은 7일 지난 파일 삭제). `capabilities`는 넘기지 않는다.
- 충돌(conflict)이면 발행함 `issues.json` 을 다시 read → `hub_index.json` 갱신 → hub_stage 부터 반복
- 올린 뒤 Artifact `read` path `issues/$DATE/handoff.json` 으로 올라갔는지 확인
- 결과: 성공 `staged (hub)`, 실패 `failed: <사유>`. GitHub push·Chrome 업로드는 하지 않는다 (루틴이 05:00에 가져간다)

### A. 클라우드 루틴 → GitHub
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

### P. Cowork 제작
1. SendUserFile: `out/${DATE}-brief/*.jpg`, `caption.txt` (status: proactive)
2. SendUserMessage (한국어, 짧게): 만든 뉴스·매체 / 후속으로 쓴 것과 새 사실 / 중복으로 뺀 후보와 이전 호 / 그 밖에 뺀 후보와 이유 / 채널 오류·검증 경고 / 발행함 올림 결과 ("05:00 루틴이 GitHub로 넘김 → 07:00 게시 예정") / 전날 게시 결과·링크
3. 뉴스가 0건이면 발행함은 건드리지 않고 이유와 채널 상태만 보고한다.

### A. 클라우드 루틴
마지막 메시지(한국어, 짧게): 받은 곳(발행함 / 직접 제작) / 넘긴 뉴스·매체 / 재검증 결과·경고 / push 결과(브랜치·커밋)와 07:00 게시 예정 / 직접 제작했다면 뺀 후보와 이유 / 전날 게시 실패가 있으면 그 사실.
직접 제작한 경우 같은 내용을 gh_handoff 전에 `runs/$DATE/run_log.md` 에 적는다.
