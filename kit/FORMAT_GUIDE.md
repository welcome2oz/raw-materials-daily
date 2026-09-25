# RAW MATERIALS DAILY — 카드뉴스 포맷 가이드

계정 @raw_material_procurement · 시리즈명 RAW MATERIALS DAILY(원재료 데일리)
대상 독자: 구매·조달·원가 담당자, 제조업 실무자
한 줄 정의: **"그날의 원재료 뉴스를, 주요 외신 출처와 구매 관점으로 한 번에."**

## 0. 운영 원칙 (2026-09-24 결정)

1. **가격은 싣지 않는다.** 시세·단가·가격 수치는 카드에 쓰지 않는다. 합법적으로 매일 받을 수 있는 가격 소스가 없다는 검토 결과에 따른 결정이다(근거: `DATA_SOURCES.md`). 렌더러가 가격 표현(예: `$9,800`, `톤당 80달러`, `USD/t`)을 발견하면 오류로 막는다.
2. **그날의 최신 뉴스만 쓴다.** 기사 게재일은 포스트 날짜 기준 전날부터 당일까지(`news_max_age_days: 1`)만 허용한다.
3. **출처는 글로벌 주요 외신과 이름 있는 전문지만 쓴다.** 허용 목록은 아래 4장. URL 도메인과 발행처가 모두 목록에 있어야 한다.
4. **요약은 새로 쓴다.** 기사 문장을 번역해 옮기지 않는다. 원문 제목은 짧은 인용으로 표기할 수 있다.
5. **의견은 구분한다.** 구매 관점에만 쓰고 "의견"으로 표시한다.

---

## 1. 비주얼 시스템

| 항목 | 규칙 |
|---|---|
| 캔버스 | **4:5 = 1080×1350 JPEG** (자동 게시 API 규격, 7장). 보관용 PNG도 함께 저장. 앱 수동 업로드용 `--ratio 3:4`(1080×1440)도 가능하지만 API로는 게시할 수 없다 |
| 안전 영역 | 좌우 여백 76px. 프로필 그리드는 3:4로 보여 4:5 카드의 좌우 약 34px가 잘리지만 여백 안이라 안전 |
| 톤 | 절제된 보도 그래픽. 가는 선(hairline)으로 구획, 카테고리색은 강조 1곳에만. 그리드·글로우·둥근 패널·배지·아이콘 없음 |
| 테마 (2026-09-25) | **호수마다 다크·라이트를 번갈아 쓴다**: No.1 다크 → No.2 라이트 → No.3 다크 … (`brand.json > theme_rotation`). 다크 = 배경 #121314·밝은 글자, 라이트 = 종이색 #F5F3EE·먹색 #17181B 글자. 레이아웃·문구 규칙은 같다. 한 호만 고정하려면 포스트 JSON에 `"theme": "dark"` 또는 `"light"` |
| 발행 표기 | 하단 `@raw_material_procurement 원재료 구매 담당자 발행`. 사람이 검수·대조했다는 문구는 쓰지 않는다 |
| 자동 맞춤 | 내용이 넘치면 `dense`→`denser`로 줄이고, 여백이 260px 넘게 남으면 `roomy`로 키운다 |
| 서체 | 한글 **Pretendard**, 영문·숫자 **Inter (Sans-Serif)**. 한 문장 안에서도 글자 종류에 따라 자동 적용 |
| 강조 | `**텍스트**` → 카테고리 컬러. 텍스트 블록당 1곳만 |

### 카테고리 컬러 (뉴스 슬라이드마다 자기 카테고리 색)

| key | 표시 | 다크 | 라이트 (`accent_light`, 바탕 대비) | 범위 |
|---|---|---|---|---|
| `steel` | STEEL 스틸 | #7FA3B8 스틸블루 | #3F6F8C (4.9:1) | 열연·냉연·도금·STS·철근, 철광석·스크랩 |
| `resin` | RESIN 레진 | #A3B26E 올리브 | #5E6B24 (5.3:1) | PP·PE·PVC·ABS·HIPS·PS, 에틸렌·프로필렌·나프타 크래커 |
| `nonferrous` | NON-FERROUS 비철 | #C98B5E 코퍼 | #955426 (5.3:1) | 구리·알루미늄 |
| `chemical` | CHEMICAL 화공 | #A391C2 라일락 | #6E5A99 (5.3:1) | 냉매(HFC·HFO), 원유·정제·베이스오일 |
| `brief` | DAILY BRIEF 브리핑 | #CDB16A 머스터드 | #7D6419 (5.1:1) | 커버·마무리 장 |

### 토픽 태그

`supply` 수급(S/D) · `maker` 메이커 · `regulation` 규제 · `tariff` 관세

---

## 2. 레이아웃

| type | 용도 | 주요 필드 |
|---|---|---|
| `cover` | 1장. 대표 뉴스 제목 + 오늘의 뉴스 목차 | `title`, `sub`, `toc: true` (뉴스 장에서 목차 자동 생성) |
| `news` | 뉴스 1건 = 1장 | `src`(대표 출처), `headline`, `orig`(원문 제목), `facts`(사실 3개 내외, 항목별 `src` 가능), `why`(구매 관점) |
| `closing` | 출처 목록(게재일·확인일·URL) + 면책 + 팔로우 | 자동 |
| `bullets`·`table`·`bars`·`insight` | 필요할 때만. 관세율·쿼터·증설량 같은 **가격 아닌 수치** 정리용 | 기존 필드 |

`number`·`board`는 가격 차트·시세판용이라 쓰지 않는다.

### news 슬라이드 구성 — 글은 줄이고 시각화로 보여준다

1. 매체 배지: `REUTERS` + `via Yahoo Finance`(전재) + 게재 일시
2. 헤드라인: 2줄, 줄당 약 10자. 핵심 1곳만 강조
3. **시각화 블록 1~3개** (`viz`): 기사 속 사실·수치를 그림으로
4. 보조 사실(`facts`): 0~1줄. 시각화로 못 보여주는 것만
5. 구매 관점: 한 줄(약 20자), "의견" 표시
6. SOURCE: 자동 생성 (발행처·전재 호스트·게재일, 같은 매체는 묶어서 표시)

### 시각화 블록 (`viz[].type`)

| type | 용도 | 주요 필드 | 예시 |
|---|---|---|---|
| `status` | 상태판 타일 (조업·재가동·원인 등) | `items[{k, v, sub, tone: alert/warn/ok}]` | STATUS 전면 중단 / RESTART 미정 |
| `stats` | 핵심 수치 1~2개 | `items[{value, unit, label, hi, calc}]` | 1.28 Mt 올해 생산 전망 |
| `split` | 구성비 막대 (지분·점유율) | `parts[{label, value, calc}]`, `unit`, `half` | BHP 57.5* / Rio 30 / JECO 12.5 |
| `timeline` | 사건 흐름 | `start`, `end`, `span{from,to,label}`, `events[{d, t, hi}]` | 전쟁 → FM 선언 → 해제 |
| `calendar` | 일정표 (투표·마감·발효일) | `start`, `days`, `today`, `rows[{label, sub, src, bars[{from,to,kind: vote/est/opt,label}]}]`, `legend` | 파업 찬반 투표 일정 |
| `gauge` | 범위·비율 게이지 | `from`, `to`, `max`, `display`, `label` | 가동률 50–60% |

- `half: true`: 블록을 반폭으로 나란히 배치
- `calc: true` → "계산값", 달력의 `est`·`opt` 구간 → 추정으로 표시. 기사에 없는 수치를 계산·추정했다면 반드시 표시
- 시각화에도 가격 수치는 쓰지 않는다 (렌더러가 검사)
- 커버 목차의 오른쪽 숫자: 뉴스 장의 `key: {value, label}`

---

## 3. 포스트 구성 (매일 1회)

`cover(toc) → news × 2~5 → closing`

- 뉴스 선정: **여러 허용 매체가 함께 다룬 뉴스일수록 중요**(coverage). 스틸·레진·비철·화공에서 각각 최대 1건, 하루 최대 4건, coverage 2곳 이상 우선. 해당 카테고리에 그런 뉴스가 없으면 그날은 뺀다(억지로 채우지 않음, 사용자 결정 2026-09-25)
- 우선순위: ① 공급 차질·가동 중단·불가항력 ② 관세·무역구제·규제 ③ 메이커 증설·감산·M&A ④ 수요 변화
- 가격 등락이 주제인 기사(예: "구리 사상 최고가")는 선정하지 않는다
- 같은 사건을 다룬 기사 여러 건은 한 장에 묶고, 사실마다 출처를 따로 단다

---

## 4. 뉴스 출처 정책

### 허용 매체 (`brand.json > news_outlets`)

| 구분 | 매체 | 도메인 |
|---|---|---|
| 핵심 | Reuters · The Wall Street Journal · The New York Times · Yahoo Finance | reuters.com · wsj.com · nytimes.com · finance.yahoo.com |
| 글로벌 주요 외신 | Bloomberg · Financial Times · The Economist · AP · CNBC · Nikkei Asia · MarketWatch · Barron's | bloomberg.com · ft.com · economist.com · apnews.com · cnbc.com · asia.nikkei.com · marketwatch.com · barrons.com |
| 전문지·거래소·리서치 | S&P Global Commodity Insights · Argus · Fastmarkets · ICIS · MINING.COM · C&EN · London Metal Exchange · Wood Mackenzie · Trading Economics · DIGITIMES | spglobal.com · argusmedia.com · fastmarkets.com · icis.com · mining.com · cen.acs.org · lme.com · woodmac.com · tradingeconomics.com · digitimes.com |
| 국내 경제지·전문지 | 한국경제 · 매일경제 · 연합인포맥스 · 이데일리 · 철강금속신문 · 스틸데일리(스틸앤스틸) · 화학저널(ChemLOCUS) | hankyung.com · mk.co.kr · einfomax.co.kr · edaily.co.kr · snmnews.com · steeldaily.co.kr · chemlocus.co.kr |

2026-09-25 사용자 지정 20개 매체를 기본 매체로 넣었다. 유료·차단 매체(블룸버그·FT·WSJ·플래츠·아거스·닛케이·디지타임스·매일경제·연합인포맥스, 화학저널 본문)는 본문을 읽을 수 없어 **'함께 보도한 매체 수' 신호**로만 쓰고, 카드 근거는 본문을 읽은 기사에서만 가져온다. 안티 스크래핑 우회(헤더 위장·브라우저 자동화)는 쓰지 않는다. `brand.json`에서 빼거나 추가할 수 있다.

### 전재(syndication) 규칙

- Yahoo Finance와 MINING.COM에는 다른 매체의 기사가 전재된다. **원 발행처가 허용 매체일 때만** 쓴다. 예: Reuters 기사 → `publisher: "Reuters", via: "Yahoo Finance"`
- Yahoo Finance에 실린 Zacks, Motley Fool, Insider Monkey, GuruFocus, Investing.com, 보도자료 배포 기사는 쓰지 않는다 → 렌더 오류
- 원 발행처와 전재 호스트가 다른데 `via`가 빠져 있으면 렌더 오류

### 읽을 수 있는 기사만 쓴다

- 기사 본문을 열어 확인한 사실만 카드에 쓴다. 검색 스니펫이나 헤드라인만으로는 쓰지 않는다
- 게재일은 기사 페이지에서 확인한다
- 2026-09-24 첫 제작 기준: Reuters·AP·Bloomberg·WSJ·NYT·CNBC 본사 페이지는 자동 조회가 막히거나 유료였다. 실제로 확인할 수 있었던 경로는 Yahoo Finance(Reuters·Bloomberg 전재), MINING.COM(Reuters 전재), ICIS 무료 기사였다
- 한쪽 주장만 있는 보도(예: "~ 검토 중" 보도에 당국이 부인)라면, 부인한 내용도 허용 매체에서 확인될 때만 함께 싣는다. 확인이 안 되면 그 뉴스는 뺀다

### 출처 등록 필드

`id`, `publisher`(원 발행처), `via`(전재 호스트, 해당 시), `title`(원문 제목 그대로), `date`(게재일 YYYY-MM-DD), `time`(게재 시각·시간대, 페이지에 있을 때), `accessed`(확인일), `url`

---

## 5. 카피 규칙

1. 커버 제목: 대표 뉴스 1건, 2줄, 줄당 약 10~12자
2. 뉴스 헤드라인: "누가/무엇이 + 어떻게 됐다" 한 문장. 과장 표현(폭등·쇼크 등) 금지
3. 사실 문장: 기사에 있는 내용만. 주체·시점·수치(가격 제외)를 정확히. 기사가 "시장 관계자에 따르면"이라고 했으면 그대로 밝힌다
4. 구매 관점: 가능성·점검 사항 중심. 단정적인 전망·투자 권유 금지
5. 기사 문장을 그대로 번역해 옮기지 않는다. 원문 제목만 짧게 인용한다
6. 확인 안 된 루머·단독 보도의 2차 인용은 쓰지 않는다

---

## 6. 매일 제작 절차

매일 04:00(KST) Cowork 예약 작업이 `pipeline/RUNBOOK.md`(P 모드) 순서대로 만들어 발행함에 올리고, 05:00 Claude Code 루틴(A 모드)이 받아 재검증 후 GitHub로 넘긴다. 둘 다 클라우드라 PC는 꺼져 있어도 된다.

`채널 수집(WebFetch) → collect.py 후보 정리 → 기사 선택 → 본문 발췌 저장 → 포스트 JSON(근거 문장 포함) → render.py 검증·렌더 → 저장소 issues/<날짜>/ push → 보고`

### 근거 문장(evidence) 규칙

- `sources[].evidence`에 카드의 사실·숫자가 들어 있는 원문 문장을 **그대로** 넣는다
- 렌더러가 확인하는 것: ① 근거 문장이 `runs/<날짜>/articles/<출처 id>.md`(저장한 원문 발췌)에 실제로 있는가 ② stats·split·gauge·key의 숫자가 근거 문장에 있는가(없으면 오류) ③ 달력·타임라인 날짜, 보조 사실 숫자(없으면 경고)
- 계산값은 `calc: true`, 추정 구간은 달력 `est`·`opt`로 표시하면 검사에서 빠지고 카드에 "계산값"·"추정"이 붙는다
- 원문 발췌는 WebFetch가 돌려준 본문이다. 요약 모델을 거치므로 드물게 원문과 표기가 다를 수 있다. 저장소 `issues/<날짜>/evidence.csv`(근거 문장)와 원문 링크로 언제든 사후 확인할 수 있다

### 사람이 직접 만들 때 (Claude에게 맡기는 프롬프트)

```
pipeline/RUNBOOK.md 순서대로 오늘자 RAW MATERIALS DAILY를 만들어줘.
```

## 7. 인스타그램 게시 규격과 자동 게시 (확인일 2026-09-24)

매일 07:00(KST) 자동 게시: Claude Code 루틴(05:00 제작) → GitHub 저장소 push → GitHub Actions가 Instagram 공식 Content Publishing API로 게시. 설정 방법은 저장소 루트 `README.md`.

| 항목 | 이 키트의 설정 | 근거 |
|---|---|---|
| 비율·크기 | **4:5, 1080×1350** | API 이미지 비율은 4:5~1.91:1만 허용 ([IG User Media 레퍼런스](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media)). 앱에서는 3:4도 되지만([PetaPixel, 2025-05-29](https://petapixel.com/2025/05/29/instagram-finally-adds-support-for-34-aspect-ratio-photos/)) API로는 올릴 수 없다 |
| 형식 | JPEG(품질 95, sRGB), 8MB 이하 | API는 JPEG만, 8MB 이하, sRGB로 변환 (같은 레퍼런스) |
| 캐러셀 | **최대 10장**, 모든 장 같은 크기 | API 캐러셀은 10장까지, 첫 장 비율로 잘림 ([Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)). 앱에서는 20장까지 되지만 API 기준을 따른다 |
| 게시 한도 | 하루 1건 | API는 24시간에 100건까지 (같은 문서) |
| 이미지 주소 | 공개 GitHub 저장소 raw 주소 | API가 공개 서버에서 이미지를 직접 내려받음 (같은 문서) |
| 해시태그 | 5개 이하 | Instagram 2025-12-18 발표 ([Social Media Today](https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/)) |
| 캡션 | 2,200자 이하 | brand.json `max_caption_chars` |
| 프로필 그리드 | 3:4로 표시 → 4:5 카드 좌우 약 34px 잘림 | [Buffer, 2026-03-17](https://buffer.com/resources/instagram-image-size/), [Influencer Marketing Hub, 2026-09-17](https://influencermarketinghub.com/instagram-image-sizes/) |

- 게시 시각을 GitHub 예약 실행(cron)에 맡기지 않는다: 2026-08 말부터 cron 실행이 4~6시간 늦는 사례가 보고됨 ([GitHub Community #207346](https://github.com/orgs/community/discussions/207346)). 대신 Claude가 파일을 올리는 순간 Actions가 시작해 07:00까지 기다린다
- 캡션 속 URL은 인스타에서 클릭되지 않는다. 출처 추적용으로 남긴다

## 8. 중복 기사 검열 (사용자 결정 2026-09-24)

| 경우 | 처리 |
|---|---|
| 이미 발행한 기사(같은 URL) | 쓰지 않는다 (render.py 오류) |
| 이미 발행한 사건, 새 사실 없음 — 매체가 달라도 (예: 전날 로이터 → 오늘 NYT) | 건너뛴다 (render.py 오류) |
| 이미 발행한 사건, 새 사실 있음 (재가동·타결·해제·새 날짜·관련 새 수치) | 후속으로 쓴다. `update_of`에 이전 story_id, 카드에 "후속 보도" 표시 |

- 판정: 최근 14일 게시 기록(저장소 `issues/<날짜>/post.json` 중 `published/<날짜>.json` 이 있는 호)과 고유명사(회사·광산·설비·지명)·사건 유형(파업·중단·불가항력·관세…) 겹침으로 같은 사건인지 보고, 새 근거 문장에 이전 근거에 없던 상태 변화·날짜·사건 관련 숫자가 있는지로 새 사실을 가린다 (`pipeline/dedup.py`)
- 배경 숫자(작년 생산량 등)만 새로 나온 기사는 새 사실로 치지 않는다
- 국내 기사도 같은 기준으로 본다: 한글 고유명사(에스콘디다·포스코 등, 영문 표기와 연결)·한국어 사건 단어(중단·파업·불가항력·관세…)·한국어 날짜(9월 27일)를 인식한다. 예: 전날 로이터 기사로 낸 사건을 오늘 한국경제가 새 사실 없이 다시 쓰면 건너뛴다
- 자동 판정은 1차 거름망이다. 같은 사건인데 표현이 달라 못 잡는 경우를 대비해 3단계에서 후보의 이전 호 표시를 함께 본다
