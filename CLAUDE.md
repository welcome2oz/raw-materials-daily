# RAW MATERIALS DAILY 저장소

인스타그램 @raw_material_procurement 원재료 카드뉴스를 매일 만들고, GitHub Actions가 07:00(KST)에 게시하는 저장소.

- **매일 발행 작업**은 `kit/pipeline/RUNBOOK.md` 를 처음부터 끝까지 읽고 그대로 따른다 (클라우드 루틴 = A 모드: 발행함에서 받은 호를 재검증해 push, 없으면 직접 제작).
- 매일 쓰는 곳은 `issues/<오늘 KST 날짜>/` 뿐이다. `kit/`·`.github/`·`scripts/`·`published/` 는 사용자가 요청할 때만 고친다.
- main 으로 직접 push 하지 않는다. 현재 작업 브랜치(`claude/…`)로 push 하면 `publish.yml` 이 main 에 반영하고 게시한다.
- 기사 원문(WebFetch)에 있는 내용만 쓴다. 근거 없는 숫자·인용·날짜, 가격, 가상 데이터는 넣지 않는다.
- 인스타그램 로그인 정보·토큰은 다루지 않는다 (GitHub Secrets에만 있음).
- 키트를 고치면 `cd kit && python3 pipeline/pack.py` 로 `kit/manifest.json` 을 갱신해 같이 커밋한다.
