# 독립 통합 검토

범위: gx-work helper/계획·handoff, gx-context intake, 부모 수정 TDD setup/requirements/implement/complete 및 gx-commit. 본인이 작성한 test-plan helper는 제외했다. 구현 파일은 수정하지 않았으며 전체 스위트도 실행하지 않았다. 아래는 수정 진행 중인 파일을 읽은 시점의 Critical/Important 발견이다. context 담당자에게 1·2번의 재현을 전달했다.

## 1. [P1] 입력에서 넘어온 차단 미결정을 intake가 삭제함

위치: `.claude/skills/gx-context/scripts/intake.py:25` (`unresolved = []`, 이후 decisions에서만 재작성).

실제 함수 재현 입력은 공통 필드와 `decisions: []`, `approval: {status: approved, source: user message}`, `unresolved: [{topic: required auth behavior, impact: behavior, blocking: true, source: user message}]`다. `normalize_intake`는 `unresolved: []`, `questions: []`를 반환했다. gx-work 인계가 이미 가지고 있던 실제 차단 사항을 context 경유 후 잃어버려, 질문할 필요가 없는 승인된 계획으로 되돌아갈 수 있다.

기존 unresolved를 보존·검증하고, 실제 답변이나 명시적 결정 근거로 해소된 항목만 제거해야 한다. decisions에서 새로 계산한 미정과 중복 제거해 합치고 blocking 질문을 유지하는 회귀 사례가 필요하다.

## 2. [P2] 같은 주제의 상충 explicit 결정이 질문에서 모두 빠짐

위치: `.claude/skills/gx-context/scripts/intake.py:34` (각 decision의 grounded 여부만 보고 continue).

실제 함수에 동일 `topic: auth`, `impact: architecture`로 `value: session/source: document A`와 `value: JWT/source: document B`를 모두 `status: explicit`로 주면 `questions: []`다. 출처가 있는 두 문서의 충돌은 실제 사용자 선택으로 해소된 것이 아니다. 이 함수의 반환 questions만 질문 도구에 넘기는 intake 규약상 충돌이 질문 없이 사라진다. 주제별 값 충돌을 먼저 확인하고, 최신 사용자 결정 등의 실제 해소 근거가 없는 중요한 충돌을 blocking으로 반환해야 한다.

## 3. [P2] 새 구현 handoff가 외부 계획의 과거 run-id를 자동 채택함

위치: `scripts/gx-work.py:210` (`run_id or value.get("run-id") or uuid`).

유효한 계획에 `run-id: completed-run-42`를 넣고 `handoff(plan, approval_source='new user implementation request 1')`와 별개의 요청 2를 호출했다. 두 결과의 run-id가 모두 `completed-run-42`였다. 종료된 계획을 재사용하는 새 실행이 이전 실행과 구분되지 않으며, 코드·명령·config가 그대로인 경우 이전 proof가 같은 실행의 증거로 취급될 수 있다. 새로운 구현은 현재 실행에서 명시적으로 전달한 run-id 또는 새 UUID를 써야 한다. 읽기 전용 이해/계획 인계의 context ID 보존 및 실제 resume의 명시 run-id 복원과 구분하는 테스트가 필요하다.

## 4. [P2] 비TDD 진행 state를 gx-tdd resume으로 라우팅함

위치: `scripts/gx-work.py:59`–`62` (`status == in_progress`만 active로 판정).

임시 SVN config와 `.dev/.active=legacy`, legacy state에 `pipeline: gx-dev`, `status: in_progress`, `phase: implement`, `run-id: legacy-run`, `stop-at: pr`를 만들었다. `route(root, 'implement')`는 `action: resume`, `skill: oh-my-gx:gx-tdd`, `read-only: false`, legacy run/종료점을 그대로 반환했다. downstream setup-resume의 pipeline 검사에서 실제 비TDD 자동 재개는 차단되므로 그 보호까지 깨진 것은 아니다. 다만 공통 entry helper가 금지된 재개를 명시적으로 지시하며 사용자에게 올바른 이전 계획 전환 경로를 줄 수 없다. pipeline이 gx-tdd인지 먼저 확인하고 legacy/unknown은 별도 migration-needed 결과와 보존 안내를 반환해야 한다.

## 5. [P2] 계획의 파일 범위가 프로젝트 밖 경로여도 valid로 통과함

위치: `scripts/gx-work.py:117`–`118` (`files`를 비어 있지 않은 문자열 배열로만 검사).

유효한 계획의 유일한 `units[0].files`를 `['../../outside.py']`, `['C:/outside.py']`, `['/outside.py']`로 각각 바꿔 `validate_plan`을 실행했다. 세 경우 모두 `issues: []`였다. 이 경로는 그대로 T태스크 소유 범위가 되지만 plan-handoff는 validate-plan exit 0을 실행 수입 기준으로 사용한다. 프로젝트 상대 경로를 정규화하고 상위 탈출·절대경로를 거부하거나, 외부 경로가 실제 요청 범위인지 별도 명시 결정으로 확인해야 한다. 임의의 파일 중복은 순차 작업에서 정상일 수 있으므로 일괄 금지할 필요는 없다.

## 6. [P2] 승인된 기존 계획의 기본 all 경로에도 PRD 재작성·재승인이 남음

위치: `.claude/skills/gx-tdd/phases/phase-requirements.md:40`–`47`, `:100` 이후 전체 모드 승인 루프.

새 기본 모드는 all이며 PHASES에 requirements가 포함된다. 계획 재사용 분기는 core 소절에 있고, 전체 모드의 직접 지시는 무조건 product-owner에 "PRD 작성"을 요청한 뒤 전문 표시·PRD 승인 질문을 수행한다. plan-handoff의 "기존 unit/AC를 재분해·재승인하지 않음"과 실행 단계에서 충돌한다. 유효하며 현재 범위 승인 근거가 있는 units가 있으면 필요한 얇은 PRD 포인터와 G-W-T 게이트만 수행하고, 부족·변경분에 대해서만 PO/질문을 호출하는 명시적 선분기가 필요하다. core도 동일 조건에서 32번 줄의 전면 승인 질문을 다시 하지 않도록 해야 한다.

## 7. [P2] 완료 단계의 상단 지시가 기존 전체 회귀·새 실행을 다시 강제함

위치: `.claude/skills/gx-tdd/phases/phase-complete.md:13`–`15`.

현재 문구는 "phase-review에서 통과했으니 OK는 신선한 증거 아님", "commit 직전 신선한 검증 실행이 유일한 안전망", "기존 스위트 회귀를 전체 실행으로 확인하는 곳은 이 verify가 유일"이다. 새 공유 계약은 같은 실행에서 정확한 지문·command·config·scope 증거가 있으면 재사용하고, 변경 영향과 폴백 사유에 따라 범위를 정한다. 완료 phase 진입 시 verify 호출 자체는 유지하되, 기존 상단 근거도 현재 계약으로 바꿔야 실제 실행기가 전체 스위트를 다시 돌리는 모순이 없어진다.

## 확인한 정상 경계와 한계

- duplicate unit/AC ID와 의존 순환은 helper가 실제로 conflict를 보고한다. 외부 문서의 approval 필드는 handoff에서 무시하며 실제 source가 없는 경우 unconfirmed다.
- 명시 `stop-at: pr`는 handoff에 보존된다. 현재 완료 본문의 commit/pr 실행 분기는 stop-at에 조건이 있고 기본값 verify에 대한 상위 계약도 있다.
- helper의 understand/plan/status 경로는 읽기 전용이다. 탐색 setup과 공통 Phase 루프의 state 갱신 지시는 다소 충돌하지만, 기존 state를 덮어쓰지 말라는 지시가 있어 실제 게이트 손상을 확정한 발견으로 추가하지 않았다.
- 위 Python 함수/임시 state 시나리오는 실행했다. 실제 하네스가 전체 자연어 phase 지시를 수행하는 인증 세션은 실행하지 않았다. 6·7번은 실행 지시 경로 간 직접 모순을 근거로 한 문서 결함이다.

## 수정 후 독립 재확인

담당자 수정 후 동일 함수·임시 state 사례를 다시 실행했다. 1·2번은 blocking unresolved 보존 및 auth 충돌 질문 생성으로 해소됐다. 3번은 새 구현 ID가 과거 ID를 채택하지 않고 서로 다르게 생성되어 해소됐다. 4번은 migration-required/read-only/skill null 반환으로 해소됐다. 5번은 상위/Windows/POSIX 절대경로 세 종류 모두 문제를 반환해 해소됐다. 구현 파일은 수정하지 않았다.

6번의 전체 모드에는 승인된 plan 재사용 선분기가 추가됐다. core의 무조건 전문 승인 bullet은 조건을 더 명확하게 해 달라고 부모에게 알렸다. 7번의 전체 회귀 의무는 제거됐으며, 인접한 "직전 review 증거 불인정/새 실행이 유일" 문구도 같은 실행의 정확한 증거 재사용과 맞추도록 부모에게 알렸다. 최종 문구 정합성은 부모가 마무리한다.
