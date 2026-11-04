# 계획·요구사항 탐색 setup

이 절차는 `--phase requirements`·`--phase design` 및 gx-work의 계획 전용 인계에서 사용한다. 실행 준비를 생략한 별도 공개 경로이며, 구현 시에는 phase-setup의 실행 준비를 반드시 수행한다.

1. 프로젝트 절대경로, VCS 종류, 현재 브랜치, 설정·기존 산출물을 **읽기 전용**으로 확인한다. `checkout`·`pull`·`stash`·worktree 생성·의존성 설치·테스트 실행은 하지 않는다.
2. 관련 도메인 context의 필요한 절과 요청이 지목한 문서·코드를 읽는다. 문서에 답이 있는 사실을 다시 질문하지 않는다. 사용자 결정·문서 근거·조정자의 제안을 구분한다.
   `Read("../references/document-lifecycle.md")`의 사전 대조도 조회/계획 intent로 읽기만 한다. 이 탐색을 이유로 context/원장/W계획을 등록하거나 전체 인터뷰·스캔을 시작하지 않는다.
3. 산출물을 저장할 때만 `${DEV_DIR}`를 확정한다. gx-work handoff가 있으면 그 실행 경로를 사용하고, 없으면 `.dev/planning/{고유 run-id}/`를 사용한다. 기존 실행의 state.md를 덮어쓰지 않는다.
4. `run-id`·`goal`·`stop-at: plan`·`phase`·`status`와 원문 포인터를 기록한다. 변경 없는 조회라면 파일도 만들 필요가 없다.
5. 요구사항에는 G-W-T 게이트, 설계에는 testability 검토를 적용한다. 아직 부족한 명세를 승인된 것처럼 표시하지 않는다. 생성된 제품 코드는 없어야 한다.
6. 계획을 보여주고 요청한 종료점에서 끝낸다. 사용자가 실행을 요청하면 `--handoff`로 gx-tdd 실행 setup에 넘긴다. 같은 배경·모델·진행 방식은 재질문하지 않는다.
