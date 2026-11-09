# 핵심 모드 계획·승인의 main 통합

사용자 요청: 핵심 모드 계획·승인과 4건의 수정, core→all 및 AC 추가·수정·삭제 검증 결과를 PR로 올리고 main에 머지한다.

## 기준과 범위

기준은 `origin/main`의 `030f198`이다. 기존 작업 브랜치는 시각화 기능과 구 gx-dev 구조를 포함하므로 그대로 머지하지 않는다. 격리된 `codex/fix-core-plan-approval` 브랜치에 현재 gx-work → gx-tdd 구조에 맞춰 기능을 이식한다. 원본 작업 디렉터리의 파일과 브랜치를 유지하고 시각화 커밋·산출물을 포함하지 않는다.

공통 계약은 현재 실행 주체인 `gx-tdd/references/core-planning.md`에 둔다. 역할·질문·모델 실행 규약은 gx-work 경로를 사용하며 red-writer 원본에서 배포 역할을 재생성한다. gx-work 인계 검증·원 요청·run·stop-at, 읽기 전용 계획과 explore, 실제 실행방법 선택을 보존한다. 기본 종료점 verify와 명시적인 commit/pr 권한을 유지한다.

## 승인된 동작

- AC 작성 → 실제 코드 확인 → 구현 파일·순서·의존관계·AC별 검증 계획 → AC와 계획 결합 승인 → 기존 RGR·verify.
- 오케스트레이터가 기본으로 계획하고 구현 위치가 불명확할 때 architect를 1회 사용한다. 중요한 설계 판단은 전체 모드 전환의 실제 선택으로 해소한다.
- 동일 실행·범위·문서 지문의 승인과 실제 실행방법 선택은 재사용한다. 변경·누락이면 구현 전에 재승인한다. 미응답·문서 종료는 구현 허가를 만들지 않는다.
- 명시 단계가 저장 모드·실행 목록보다 우선한다. legacy flags의 core를 복원하고 단독 구현·완료도 승인 게이트를 검사한다. requirements/design 단독은 explore 범위를 유지한다.
- 전체 모드 전환은 pending/applied로 기록하고 setup 반복 없이 requirements → design → implement → review → complete로 인계한다. 이전 루프는 종료하며 중단 커서·코드·증거를 보존한다.
- 재계획은 keep GREEN, add/replace RED, 승인된 retire로 분리한다. 변경 기대값에는 새 ID를 사용하며 불변 이력·활성 세대·태스크 소유권을 보존한다. 전부 은퇴하면 범위 종료 확인에서 멈춘다.
- 후속 complete가 없는 implement와 보안 수리 뒤에는 최신 코드로 경계 회귀를 판단한다. main의 영향 계획·유효 증거 재사용 계약을 보존한다.

## 분담과 검증

- 진입 담당: core-planning, SKILL, requirements, setup-resume/explore, complete, intent-routing, pipeline-state.
- 재계획 담당: core-replanning, implement, review, maintenance-notes, red-writer 원본.
- 테스트 담당: 신규 core 5개 테스트 파일과 기존 pipeline 소비 검사. main 구조로 RED를 먼저 확인하고 이식 후 재검증한다.
- 부모: 사용자 문서·시나리오, 역할 동기화, 전체 검사, 독립 리뷰, 커밋·PR·CI·main 머지.

실제 앱의 사용자 승인부터 전체 개발 완료까지의 종단 smoke는 미실행으로 유지한다. 로컬 정책·Node fixture·mock·CI와 실제 앱 실행을 구분해 보고한다.

## 실행 근거

- 원본 보존 스냅샷: `D:/Temp/gx-core-original-preservation-jd1n5kzy.json` (기존 변경 48개 파일의 SHA-256, 원 브랜치·HEAD).
- main 이식 RED: core edge 10개에서 실패 20개, 오류 0개. 새 정본·정책·소비 게이트가 없는 상태를 확인한 뒤 구현 담당에게 편집 시작을 전달했다.
- 신규 core 41개와 기존 pipeline 38개, 합계 79개 focused가 통과한 뒤 독립 리뷰를 수행했다.
- 진입 리뷰 P2: 저장 core에서 명시 requirements/design을 요청하면 PRD를 만들지만 G-W-T가 과거 ac.md를 고르는 연결 문제가 있었다. 현재 `use_inline_core`로 문서·재작성 주체·실패 안내를 통일했다. 새 회귀 RED 1개 확인 후 edge 13개 통과. 새 명시 요청의 커서도 PHASES 첫 단계(explore)로 맞춰 RED 2서브케이스 후 resume 3개 통과.
- 재계획 리뷰 P2: review에서 제외한 과거 태스크가 공통 verify의 hash·필수 테스트·소유권에 재유입될 수 있었다. core-replanning의 ACTIVE_TASKS 정본을 test-execution과 review 양쪽이 사용하도록 연결했다. 회귀 RED 11 assertion/subtest 실패 후 integration 7개 통과.
- 두 독립 재리뷰 모두 READY이며 미해결 P1/P2 없음. 리뷰는 정적 읽기 검토이며 실제 앱 실행을 의미하지 않는다.
- 배포 리소스 `sync-codex-resources.py --check` 통과. 정합성 린트 36항목, 훅 회귀 6구간, 행동 러너 mock 30건(0 fail) 통과.
- Codex 전체 검사와 main의 기존 gx-work/context/history/lens/test-plan 검사는 최종 코드에서 순차 실행 중이다. 최종 결과·PR은 완료 후 기록한다.
