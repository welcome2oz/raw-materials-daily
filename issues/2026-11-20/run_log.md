# run_log 2026-11-20 (A. 클라우드 루틴, 호수 No.53)

- 05:03 0단계: published/2026-11-20.json·issues/2026-11-20/ready.json 없음 → 진행. 전날(11-19) 게시 확인됨.
- 05:05 setup.sh: 처음 Chromium 실행 실패(python3 에 playwright 모듈 없음, pip 이 다른 파이썬에 설치) → `python3 -m pip install playwright openpyxl pillow` 후 재실행 ✓
- 05:08 1A: 발행함 feeds/2026-11-20 feed.json 있음(03:12 Cowork). raw.json + 발췌 6건 받음 → pickup.py ✓ (채널 65개, 항목 82건). 단, Cowork 발췌는 리드 1문장뿐(body: excerpt).
- 05:09 2단계 collect.py: 2곳 이상 함께 보도 뉴스 없음. 후보 nonferrous 7·steel 25·resin 2·chemical 1.
- 05:12 4단계 직접 재확인: snmnews.com 은 루틴 WebFetch 에서 오류 페이지(se-cu.com/ndsoft/error.html)로 302 → Cowork 발췌(리드 원문 1문장) 사용. steeldaily 204507·204508 은 유료회원 전용(본문 없음). EIA 68485 는 exact-quotes 모드로 다시 읽어 발췌 교체.
- 05:15 범위 밖으로 뺀 후보: AngloGold Ashanti 콜롬비아 구리광산(Investing.com, Nov 17 03:20 PM → KST 11/18), 산은 대산공장 금융지원(이데일리, 2026-02-25), Steel Dynamics(Fastmarkets, 10/29), US copper smelting(Fastmarkets, 2025-10-31). 구리 전망(snm 577677)=가격 기사. Osiris(소형 탐사 옵션 계약, 게재일 11/12 LOI)·IAI 행사 기사 제외. WebSearch 보충(구리·알루미늄·석화·철강 관세, investing.com·Yahoo) → 범위 안 새 사실 기사 없음(가격 기사만).
- 05:18 3단계 선정 (2곳 이상 함께 보도 뉴스 없음 → 단독 보도로 채움):
  - 스틸: 철강금속신문 '英, 한국산 후판 반덤핑 최종 확정' — 단독 보도 — 관세·무역구제 결정(영국 Trade Remedies Notice 2026/32, 18일 발표). 같은 카테고리 다른 후보(KG스틸 PLTCM 합리화, 中 철강 선적량, 영국 용해·주조국 신고, 인도 2047 목표)는 카테고리당 1건 한도·우선순위(② 관세)로 제외.
  - 화공: 美 EIA 'Oil flows through Middle East chokepoints increased in the third quarter' — 단독(기관 발표) — 수급 통계(3분기 물동량 +19%, 10월 중동 원유 생산 2,310만 b/d). 본문의 Brent·디젤 가격 수치는 쓰지 않음.
  - 비철·레진: 범위 안에서 읽을 수 있는 새 사실 기사 없음 → 비움.
- 05:24 6단계: render.py --check 오류 0(단독 보도 경고 2건만), 렌더 4장(다크 테마, No.53), JPG 4장 열어 확인(잘림·겹침 없음). PIL 모듈 깨짐 → pillow 재설치 후 렌더.
- 05:25 7단계: gh_handoff.py 실행.
