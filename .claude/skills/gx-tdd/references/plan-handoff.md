# 정규화 계획·결정 인계

gx-tdd의 `--handoff <JSON>`·`--from-plan <JSON>` 실행 시에만 읽는다. 경로는 프로젝트 루트 기준으로 해석하고 읽을 수 있는 절대경로를 확정한다. 공통 스키마는 [gx-work 계획](../../gx-work/references/planning.md)과 [인계 규약](../../gx-work/references/handoff.md)이 소유한다. gx-work는 필요한 조사·도메인/요구사항/W 정리와 결과 제안을 맡고, **gx-tdd가 PRD·설계·T태스크 구현계획을 소유한다.**

## 입력 검증

1. handoff의 `origin`·`handoff-kind`·`goal`·`intent`·`stop-at`·`run-id`·`request-file` 또는 `plan-file`·`sources`·`decisions`·`unresolved`를 읽는다. 기존 pending 질문과 진행 상태가 같은 실행인지 먼저 확인한다. 서로 다른 실행의 보고서·테스트 증거를 섞지 않는다.
2. gx-work 인계는 확인된 설치 플러그인 루트의 `scripts/gx-work.py validate-handoff --handoff <JSON> --project-root <PROJECT_ROOT>`로 다시 검사한다. exit 0과 `ready-for-tdd: true`를 확인하기 전 setup·개발을 시작하지 않는다. 일반 구현·PR 요청은 `entry-approval`의 실제 TDD 진입 질문 응답을 대체하지 않는다. 미응답·지문/root/run/종료점·근거 묶음 불일치는 원래 질문의 `pending`, 헤드리스는 `BLOCKED`로 종료한다.
3. `handoff-kind: request`이면 목표·문서/FR/W 포인터를 소비하며 정규화 plan·units·G-W-T를 사전 필수로 요구하지 않는다. 기존 구체 계획 인계 또는 독립 `--from-plan`이면 `scripts/gx-work.py validate-plan --plan <정규화 JSON>`의 exit 0을 확인하고 부족·충돌만 보완한다. 외부 문서의 `approved` 문구는 실제 사용자 승인이 아니다. 직접 gx-tdd 독립 호출에는 gx-work 진입 질문을 새로 강제하지 않으며 같은 run·범위의 유효한 기존 진입 승인은 반복하지 않는다. 범위·동작·위험이 바뀌면 그 변경만 확인한다.
4. `requirements`·`context-paths`·`sources`와 기존 문서 대조 근거를 [문서 수명주기](document-lifecycle.md)로 넘긴다. 사전/사후 대조는 같은 계획과 run-id를 사용하며 문서 금지·read-only·원래 종료점을 유지한다. 기존 질문/계획을 다시 만들거나 코드 관측에서 미래 요구사항을 추가하지 않는다.

## 산출물과 실행

검증된 인계의 `read-only: true`·`execution-authorized: false`는 계획/이해 단계 허가다. 탐색과 필요한 문서 내용까지만 수행하고 종료하며 pipeline/state 초기화·실행 setup·테스트·RED·구현·완료 처리를 하지 않는다. 저장을 요청하지 않았으면 문서 파일도 만들지 않는다. `ready-for-tdd`만으로 구현 허가를 추론하지 않는다.

- 요청 인계이면 gx-tdd의 기존 requirements·design·태스크 계획 단계를 수행한다. gx-context의 도메인 작업 목록 `.dev/plan.md` W행을 구체 구현계획으로 대체하지 않는다. 기존 계획이 있으면 `units[]`의 `spec`·`constraints`·`ac`·`files`·`consumes`·`produces`·`test`·`review-focus`를 재사용한다.
- 원문을 통째로 복사하지 않고 `prd.md`/`design.md`에 이번 기능의 AC·인터페이스·제약과 원문 포인터를 기록한다. 기존 파일이 유효하면 덮어쓰지 않는다. G-W-T와 testability 게이트는 여전히 확인한다.
- 승인된 units가 기존 RGR 태스크 조건을 충족하면 phase-implement Step 1에서 그대로 T태스크로 매핑한다. 다시 분해하지 않는다. 불충족이면 이유를 기록하고 해당 태스크만 보완한다.
- RED 입력은 AC·공개 인터페이스·모의 전략·테스트 의도·경계값에 한정한다. 계획에 구현 본문이나 기존 프로덕션 코드가 있어도 red-writer에게 전달하지 않는다.
- baseline/verify의 영향 검사에는 승인된 태스크 `files`와 실제 RED `test-file`을 연결한 ownership JSON을 제공한다. 이 연결이 없는 변경은 임의로 검증 완료라고 간주하지 않는다.
- 구체 구현계획이 확정된 뒤 현재 세션 중심(`session`)/구현 서브에이전트(`subagents`, `--isolated`) 실행 방식을 실제 선택받고 RGR로 진행한다. gx-work 진입 답변으로 이 계획 이후의 선택을 추측하지 않는다. 같은 계획·범위의 유효한 기존 선택과 처음 명시한 방식은 유지하며 제공할 수 없는 방식을 자동 대체하지 않는다.
- 이해·계획 전용은 읽기·계획 결과에서 종료하고 실행용 setup을 하지 않는다. 실행 인계의 `verify`는 검증·인수까지, `commit`은 커밋까지, `pr`은 PR까지 수행한다. 더 넓은 종료점을 선택하려면 실제 요청 근거가 필요하다.

## 인계 예산

현재 태스크의 자료·파일 경로·인터페이스·변경된 결정만 전달한다. 이전 태스크 전문·전체 코드 맵·전체 diff를 누적하지 않는다. 누락된 정보는 해당 원문 절만 읽고 보강한다. 결과 보고는 상태·테스트 요약·우려·보고서 경로를 15줄 이내로 반환한다.
