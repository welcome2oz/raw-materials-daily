# 가격 데이터 소스 검토 (확인일 2026-09-24)

> **결정 (2026-09-24): 가격 카드는 운영하지 않는다.** 아래 검토에서 매일 합법적으로 공개 게시할 수 있는 가격 소스가 부족하다고 확인돼, 카드뉴스는 주요 외신 뉴스 중심으로 전환했다. 이 문서는 그 판단 근거 기록이며, 나중에 가격 카드를 다시 검토할 때 출발점으로 쓴다.

판정 기준은 두 가지이며, 둘 다 충족해야 "가능"이다.
(a) 스크립트로 정기적으로 받아올 수 있는가
(b) 인스타그램에 공개 게시해도 되는가 (이용약관·라이선스 근거)

※ 이용약관 해석은 법률 자문이 아니다. "조건부"는 권리자에게 서면으로 확인한 뒤에만 쓴다.

## 1. 결론 — 품목별 가격 카드 운영 여부

| 카테고리 | 일간 가격 | 월간 가격 | 판단 |
|---|---|---|---|
| 비철 (구리·알루미늄) | ✗ 무료·합법 소스 없음 | ✅ World Bank (CC BY 4.0) | 일간 가격 카드 제외. 월간 카드는 가능 |
| 스틸 (열연·GI·철근) | ✗ 없음 (SHFE는 서면 허가 필요) | △ 철광석만 World Bank 월간 | 일간 가격 카드 제외 |
| 레진 (PP·PE·ABS·HIPS) | ✗ 없음 (ABS·HIPS는 무료 소스 자체가 없음) | ✗ | 가격 카드 제외 |
| 화공 — 냉매 (R32·R134a) | ✗ 없음 | ✗ | 가격 카드 제외 |
| 화공 — 오일 (원유) | ✅ EIA (퍼블릭 도메인, 주 1회 발표) | – | 주간 원유 카드는 가능 |
| 화공 — 베이스오일 | ✗ 없음 | – | 가격 카드 제외 |
| 환율 (보조 지표) | ✅ 한국수출입은행 API | – | 가능 |

## 2. 합법적으로 쓸 수 있었던 소스 (현재 미사용)

| feed id | 소스 | 품목 | 빈도 | 접근 방식 | 게시 조건 | 근거 |
|---|---|---|---|---|---|---|
| `worldbank_cmo` | World Bank Commodity Price Data (Pink Sheet) | 구리·알루미늄 월평균, 철광석 62% Fe CFR China | 월간. 매월 2번째 영업일 갱신 (최근 2026-09-02, 다음 2026-10-02) | XLSX 직접 다운로드, 키 불필요 | CC BY 4.0, 출처 표기 필요. 단, 원자료 중 제3자(S&P Global 등) 데이터에 CC BY가 적용되는지는 라이선스 페이지에 명시되어 있지 않음 | [datacatalog](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections), [다운로드 페이지](https://www.worldbank.org/en/research/commodity-markets) |
| `eia_spot` | U.S. EIA 현물가격 | WTI Cushing, Brent | 값은 일별, 발표는 주 1회 | Open Data API, 무료 키 | 퍼블릭 도메인. "Source: U.S. Energy Information Administration (발표일)" 형식 표기 권장 | [EIA 저작권·재사용](https://www.eia.gov/about/copyrights_reuse.php), [Open Data](https://www.eia.gov/opendata/) |
| `koreaexim_fx` | 한국수출입은행 환율 정보 | USD/KRW, CNH 등 | 영업일 | JSON API, 무료 키 | 이용허락범위 제한 없음 | [공공데이터포털](https://www.data.go.kr/data/3068846/openapi.do) |

## 3. 조건부 — 권리자 허가·라이선스가 필요

| 소스 | 품목 | 막히는 지점 | 필요한 조치 | 근거 |
|---|---|---|---|---|
| LME | 구리·알루미늄 일간 | 공개 웹사이트·앱 배포에 라이선스 필요 | 다음날(next day) 배포 라이선스: 일회성 $4,000, 사용자당 요금 $0, 보고 의무 없음. 인스타그램이 적용 대상인지 LME에 확인 필요 | [LME Data Distribution](https://www.lme.com/en/market-data/market-data-licensing/data-distribution) |
| SHFE 상해선물거래소 | 열연·철근·스테인리스·구리·알루미늄 선물 정산가 (일간 파일 수집 가능) | 비상업 목적의 열람·다운로드만 허용. 영리 목적의 전재·전파·출판은 서면 허가 필요 | SHFE에 서면 허가 요청 | [SHFE 면책·저작권](https://www.shfe.com.cn/disclaimer/) |
| DCE·CZCE | PP·LLDPE·PVC·프로필렌 선물 | 거래소 허가 없이 상업 목적으로 전파 금지 (거래 규칙) | 거래소에 허가 요청 | [DCE 거래규칙 제103조 (2024년판, 증권사 게시본)](https://www.htfc.com/wz_upload/png_upload/20240207/1707285616186297353.pdf) — 2026년판은 미확인 |
| KOMIS 한국광해광업공단 | 비철·철광석 일간 | "무단 복제 및 배포를 원칙적으로 금합니다". 수익 목적이면 허락 필요 | 서면 허락 요청 | [KOMIS 저작권정책](https://www.komis.or.kr/Komis/Policy) |
| 오피넷 (한국석유공사) | 두바이유·나프타 일간 (HTML) | 수익 목적 이용 시 사전 협의·허락. 국제유가는 API 없음 | 사전 협의 | [오피넷 API 안내](https://www.opinet.co.kr/user/custapi/custApiInfo.do) |
| 조달청 비축물자 | LME 비철 일간 (HTML 차트) | 게시 권리 미확인. 원천 데이터가 LME | 조달청 문의 + LME 권리 확인 | [비축물자 차트](https://pps.go.kr/bichuk/internation/listChartView.do?key=00827) |

## 4. 불가 — 유료이고 재배포 금지

Platts, Argus, ICIS, Fastmarkets, Mysteel, SteelOrbis, 卓创(SCI99), 隆众(Oilchem), CME.
각 사 약관에서 사전 서면 동의 없는 공개 게시·배포 금지를 확인했다. 예: [Platts](https://www.spglobal.com/commodity-insights/en/overview/website-app-terms-of-use), [Argus](https://www.argusmedia.com/en/policies/copyright-policy), [Fastmarkets](https://www.fastmarkets.com/terms-of-use/), [Mysteel](https://www.mysteel.net/terms-conditions/), [CME](https://www.cmegroup.com/trading/market-data-disclaimer.html)

SunSirs(生意社·100ppi)는 보안 검사 페이지만 열려 약관을 확인하지 못했다 → 사용하지 않는다.

## 5. 참고 — 빈도가 낮은 공공 데이터 (배경 추세용)

- 산업통상부 철강원자재 가격동향: 반기, 이용허락범위 제한 없음 — [data.go.kr 3039951](https://www.data.go.kr/data/3039951/fileData.do)
- 산업통상부 석유화학 원자재가격동향: 연간, 이용허락범위 제한 없음 — [data.go.kr 3073978](https://www.data.go.kr/data/3073978/fileData.do)
