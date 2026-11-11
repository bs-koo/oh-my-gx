> gx-tdd/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태/질문/페이즈 결정을 추정하지 않는다. 상대경로는 이 파일의 위치를 기준으로 해석한다.

## 코드 맵

오케스트레이터가 관리하는 누적 문서. 관련 파일의 경로와 역할을 기록한다. 구조(핵심 파일·참조 파일·설정)는 아래 "조건부 운영 규칙"의 코드 맵 구조를 따른다.

**생성**: phase-setup의 Step 4에서 초기 맵을 생성한다.
**누적**: 각 agent 출력에 "탐색 추가 항목" 섹션이 있으면 해당 항목을 맵에 append한다. 누적 맵은 **최대 25개**로 제한한다. 초과 시 참조 파일부터 제거한다.
**저장**: 코드 맵이 갱신될 때마다 `${DEV_DIR}/codemap.md`에 Write한다.
**전달**: 모든 agent 호출 시 현재 코드 맵을 프롬프트에 포함한다.

## Trust Ledger (신뢰 원장)

감사 결과와 위험 수용 이력을 누적하는 문서. security-auditor 감사, reviewer의 Critical/Important 요약(Part 2), 각 게이트의 위험 수용 항목을 기록한다. 오케스트레이터가 관리한다.

**위험 수용 기록 규약**: 파이프라인의 모든 위험 수용(테스트 미검증 리뷰, 미해결 Critical 수용, TDD 미이행 완료 실행, 신규 경고 수용, G-W-T 제외, core 긴급 감사 수용, 기존 실패 알고 진행(`known-failures`) 등)은 `### 위험 수용` 섹션에 `- [{항목명}] {사유} ({phase/step})` 형식으로 기록한다. Write 권한이 없는 스킬(gx-verify)은 보고만 하고 **오케스트레이터가 기록**한다. 문서 구조(`### 통합 감사 (review)`·`### 위험 수용`)는 아래 "조건부 운영 규칙"의 Trust Ledger 구조를 따른다.

**생성**:
- 전체 모드: phase-review Step 2 Task B의 security-auditor 통합 감사 완료 시 생성.
- 핵심 모드: phase-implement Step H1~H4의 긴급 보안 감사 완료 시 생성 (`### 핵심 모드 긴급 감사` 섹션).
- 후속 review 반복마다 갱신/append.

**저장**: `${DEV_DIR}/trust-ledger.md`에 저장한다.
**전달**: PR 본문(`pr-context.md` 조립 시)에 감사 결과 요약으로 포함한다.

---

## 공유 규칙

### 작업 경로 기준
phase-setup 결정, 모든 Phase 사용.

| 변수 | 값 | 결정 |
|---|---|---|
| `VCS_TYPE` | `.claude/config.json`의 `"vcs"` 값 (`"git"`/`"svn"`) | Step 1 |
| `GIT_PREFIX` | `VCS_TYPE`과 동일 | Step 1 |
| `DEV_DIR` | `.dev/{branch-slug}/`. **SVN은 브랜치가 없으므로 git 브랜치명과 동일 규칙으로 작업 slug를 만들어 `.dev/{slug}/`를 쓰고(기능별 격리), 활성 slug를 `.dev/.active`에 기록한다 — 훅·라우팅·verify가 이 포인터로 활성 작업의 state.md를 찾는다(`.active` 부재·공백 시 `.dev/trunk/` 폴백).** | Step 6.5 |
| `BASE_BRANCH` | SVN 미사용 | Step 2 |
| `DIFF_FILE` | `${DEV_DIR}/diff.txt` | — |
| `DOMAIN_CONTEXT` | `context/*/PROJECTS.md` 매칭. 없으면 빈 상태 | Step 3.1 |
| `REFERENCES` | `references/` 문서 목록. 없으면 빈 상태·미포함 | Step 3.1 |
| `MODEL_PROFILE` | `standard`/`eco` | Step 1.5 |

- `PROJECT_ROOT`: phase-setup Step -1이 Git `--show-toplevel` > SVN `wc-root` > 현재 디렉토리 절대경로 순으로 결정한 값.
- Agent에게 `PROJECT_ROOT`를 전달해 파일 도구의 기준점으로 쓰고, Git·SVN·빌드·테스트 명령도 그 디렉토리에서 실행한다.

### gx-work 진입·계획·실행방법 상태

gx-work 인계의 진입 승인은 TDD로 연결할 **원래 요청 범위**에 대한 실제 응답이다. PRD·설계·구체 T태스크 계획과 그 검토는 gx-tdd 안에서 수행한다. 전체 인계 검증은 [계획 인계 계약](plan-handoff.md), 실행방법 질문은 [구현 phase Step 1.2~1.3](../phases/phase-implement.md)이 소유한다. 상태 초기화·stash 충돌 골격·`--phase` 부트스트랩·재개에 아래 필드를 보존한다.

| 필드 | 기록·검증 |
|---|---|
| `run-id`, `goal`, `stop-at` | 원래 실행 식별자·목표·종료점. 다른 실행과 섞거나 권한을 확장하지 않는다 |
| `handoff-file`, `request-file`, `plan-file` | 존재하는 원문/인계의 프로젝트 상대경로 포인터(예: `.dev/<run-id>/handoff.json`). 이전 세션이 남긴 절대경로 값도 읽는다(setup-resume 0.05). request 인계에 없는 plan-file은 생략하며 원문을 프롬프트로 복사하지 않는다 |
| `entry-approved-run`, `entry-approved-source`, `entry-approved-scope-sha256` | 검증된 gx-work `entry-approval`의 run·실제 응답 출처·scope-sha256. question-set-id는 결정 기록/작업 문맥에도 보존한다. 직접 gx-tdd 호출에는 만들어 넣지 않는다 |
| `implementation-plan-file`, `implementation-plan-sha256` | TDD 내부의 구체 T태스크·순서·테스트 의도가 담긴 파일과 현재 SHA-256. 기존 유효한 계획을 재사용하며 원래 request-file/plan-file 포인터를 덮지 않는다 |
| `plan-approved-run`, `plan-approved-source`, `plan-approved-sha256` | Step 1.2에서 실제 검토 응답을 확인한 run·출처·내부 계획 해시 |
| `execution-method` | 실제 선택한 `session` 또는 `subagents`. 미결정은 비운다. 처음 명시한 선택도 계획 검토 전에는 실행 허가가 아니다 |
| `execution-method-run`, `execution-method-plan-sha256`, `execution-method-source` | 확정된 방법의 run·승인된 내부 계획 해시·실제 응답 출처. 같은 조합일 때만 재질문 없이 재사용한다 |

Step 1.2에서 현재 세션/서브에이전트로 진행하는 한 실제 응답은 plan-approved와 execution-method 양쪽 필드를 함께 확정한다. 초기 명시 방법이 있으면 실제 계획 검토 응답과 기존 선택 근거를 각각 연결한다. Step 1.3은 이 기록을 검증·반영하고 계획 승인만 받아 방법이 빠진 경우에만 추가 선택 질문을 한다. 수정·미응답·문서 종료는 실행방법 승인을 만들어 넣지 않는다. `session`/`subagents`의 플래그 반영과 handoff 재검증 세부는 아래 "조건부 운영 규칙"에 있다.

### 핵심 모드 계획 승인·실행 범위 상태

정본은 [core-planning.md](core-planning.md)다. core·mode 부재 legacy flags·core→all 전이·재개/부분 phase의 범위 복원에만 조건부로 읽는다. HANDOFF_READ_ONLY는 state를 초기화하거나 갱신하지 않고 탐색·계획 내용까지만 수행한다.

| 필드 | 기록·검증 |
|---|---|
| `mode` | 명시 all/core 우선. 필드 부재만 restore_mode(None, saved_flags)로 독립 --core를 복원한다. 존재하는 null·빈 값·다른 값은 중단한다 |
| `requested-phase`, `execution-phases` | 이번 명시 phase와 실제 실행 목록. 현재 명시 요청은 저장 범위·목록·커서보다 우선한다. requirements/design은 [explore, 요청phase]이며 저장 core를 all로 바꾸지 않는다 |
| `core-plan-status`, `core-plan-approved-digest` | pending/approved 및 ac.md raw bytes + NUL byte + plan.md raw bytes의 SHA-256. 기본 pending·null. 실제 문서 쌍 승인과 현재 지문이 모두 같을 때만 유효하다 |
| `mode-transition`, `mode-transition-status` | core-to-all 및 pending/applied. 실제 선택을 decisions.md에 먼저 보존하고 pending을 멱등 적용한 뒤 applied를 기록한다 |
| `transition-requested-phase`, `mode-transition-source` | 실제 전체 전환으로 해제한 단독 범위(null)와 결정 기록 위치. 과거 범위·해제 이유·phase/step은 결정 로그에 보존한다 |

core의 내부 T계획 정본은 `${DEV_DIR}/plan.md`다. 결합 승인과 단독 해시의 연결, 승인 무효화, core→all 전이 적용 세부는 아래 "조건부 운영 규칙"에 있다.

### 모델 프로파일 (MODEL_PROFILE)

Codex는 [모델 정책](../../gx-work/references/codex-models.md)의 helper로 아래 역할·프로파일과 태스크 리뷰·fix 격상 예외를 함께 해석한다. opus/sonnet은 원본 티어이며 메인 세션 IMPLEMENT를 mid 디스패치로 기록하지 않는다. `model-dispatches.jsonl`에 계획과 실제 도구 인자·관측값을 구분한다.

에이전트 디스패치의 모델 수준. 절차 축(mode)과 **직교**하며 Phase 구성·게이트·Iron Law에 영향을 주지 않는다.

- 결정 우선순위: `--eco`/`--standard` 플래그 > gx-work 인계 `model-profile` > ARGS[0] 자연어(`에코 모드`/`에코로`/`절약 모드` → eco, `표준으로`/`표준 모드` → standard) > **의도 파싱 Step 3 질문 답변**(정해지지 않은 항목만 시작 전에 한 번 묻는다. 정본은 intent-routing Step 3. 핵심 모드면 묻지 않고 standard) > config.json `workflowDefaults.modelProfile` > config.json `modelProfile` > 기본 `standard`. phase-setup Step 1.5가 이 순서로 확정해 state.md에 기록한다.
- **standard (표준)**: Agent 팀 표의 모델 그대로 디스패치한다.
- **eco (에코 모드)**: **design-critic, test-architect, reviewer**를 Task 호출 시 `model: "sonnet"` 파라미터로 오버라이드하여 디스패치한다 — Task의 model 파라미터는 에이전트 정의(frontmatter)보다 우선한다. **architect는 eco에서도 opus를 유지한다** — 설계 오류는 게이트가 방어하지 못하고 하류 전체로 전파되는 유일한 상류 실패인 반면 호출은 1~2회로 가장 적다 (하향 대상은 실패 모드가 '놓침'인 검증자이며 security-auditor·verify가 별도 축에서 방어). 이미 sonnet인 에이전트(red-writer/implementer, green/refactor-coder 포함)는 그대로 유지한다 (haiku 강등 금지). 이 규칙은 **모든 Phase의 모든 Task 디스패치에 적용**된다 — phase 파일에 개별 표기가 없어도 적용한다. fix loop 라운드 4~5의 opus 격상은 "실패의 대응"으로 프로파일과 독립이다 — eco 세션에서도 격상한다 (하향 규칙은 초기 디스패치 모델에만 적용된다).
- 게이트(G-W-T·testability·기준선·Mechanical Gate·verify)는 모델 무관 기계 검증 또는 스킬(gx-verify) 실행이므로 eco에서도 동일하게 유지된다.
- 오케스트레이터가 직접 수행하는 단계(핵심 모드 ac.md 작성, AC 자가 검증 등)는 메인 세션 모델을 따른다 — 플러그인이 제어하지 않는다.
- `--resume` 시 state.md의 `model-profile`을 복원한다. 재개할 때 사용자가 프로파일을 바꾸면(`--eco`/`--standard`·자연어) **남은 디스패치부터** 적용한다: `model-profile`을 새 값으로 갱신하고 decisions.md와 execution-log에 이전 값·새 값·바꾼 시점(phase/step)을 남긴다. 이미 끝난 디스패치는 다시 실행하지 않는다.

### Agent 결과 전달 규칙 (컨텍스트 경량화)

| 상황 | 사용자에게 보이는 것 |
|---|---|
| Q&A Phase (requirements, design) 첫 표시 | Agent 출력 **전문** — 산출물 검토용. Phase 파일의 구체적인 표시 규칙이 이 일반 규칙보다 우선한다 |
| Q&A Phase 완료 보고 | 파일에 저장하고 **요약만** ("PRD 확정. ${DEV_DIR}/prd.md에 저장됨") |
| Q&A 없는 Phase (implement, review, complete) | Agent 출력 **요약만**. 전문은 파일·변수 보관 |
| implement Phase의 인계 | **report 파일 경로로만 한다** — red-writer·implementer는 전문을 ${DEV_DIR}/reports/t{N}-*.md에 Write, 상태(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)와 15줄 이내 요약만 반환 (상태 반환은 격리 경로. 세션 경로는 report 파일이 인계 단위) |

이후 Phase에서 이전 산출물이 필요하면 **파일을 Read하여 Agent prompt에 포함**하되, 오케스트레이터 자신의 출력에는 포함하지 않는다. 각 Phase 파일에서 구체적인 요약 포맷을 정의한다.

### 문서 보관
- phase-requirements는 PRD를 `${DEV_DIR}/prd.md`에 저장한다. inline core는 대신 `${DEV_DIR}/ac.md`(G-W-T AC)와 코드 Read 기반 `${DEV_DIR}/plan.md`를 저장하고 두 문서를 함께 승인받는다. 명시 requirements/design은 저장 core여도 PRD 경로다. 계획 전용 인계는 요청한 저장 범위만 수행한다.
- phase-design 완료 시 확정된 설계 문서를 `${DEV_DIR}/design.md`에 저장한다 (핵심 모드는 design 단계가 없어 미생성).
- **승인 대기 초안**: PRD·설계 초안을 사용자에게 표시하는 즉시 같은 디렉토리에 `prd.draft.md`·`design.draft.md`로 저장하고 `current-step`을 `PRD 승인 대기`·`설계 승인 대기`로 둔다. 승인되면 정식 파일(`prd.md`·`design.md`)로 저장하고 초안을 지운다. 초안에는 `## 확인이 필요한 사항 (승인 전)` 절을 함께 저장하고 받은 답에는 `→ 답변: decisions.md` 표시를 붙인다. 재개 시 초안이 있으면 에이전트를 다시 디스패치하지 않고 같은 초안으로 표시 없는 질문만 다시 한다. HANDOFF_READ_ONLY·문서 저장 금지에서는 초안도 저장하지 않는다. 초안은 승인 근거가 아니다.
- Trust Ledger를 `${DEV_DIR}/trust-ledger.md`에 저장한다 (핵심 모드는 H1~H4 긴급 감사 결과가 여기에 기록된다).
- 코드 맵을 `${DEV_DIR}/codemap.md`에 저장한다 (갱신 시마다).
- phase-design, phase-implement, phase-review 진입 시 해당 파일들을 Read하여 에이전트 프롬프트에 사용한다.
- `.dev/` 산출물은 **협업 공유 대상**으로 커밋에 포함한다 (`.gitignore`에 추가하지 않음 — verify 지문은 `.dev`를 제외하므로 게이트와 무관). `.gitignore` 보강은 phase-setup Step 6에서 config `projectTypes.artifacts` 기준으로 빌드 아티팩트만 처리한다.

### 진행 상태 추적 (state.md)
파이프라인 진행 상태를 `${DEV_DIR}/state.md`에 기록하여 세션 재개를 지원한다.

**state.md 필드**: 초기화 필드의 정본은 phase-setup Step 7, 태스크 객체의 정본 예시는 phase-implement "state.md 추적" 절이다. 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)은 `pipeline: gx-tdd`·`status: in_progress`·`verify-status`·`verify-fingerprint`를 판별 키로 쓴다. `steps`의 RGR 태스크는 `"RGR T{N} (AC-N)"` 객체에 `red`·`impl`·`test-file`·`test-file-hash`·`test-count`·`report`·`fix-round`를 중첩한다 (`test-file`은 경로 하나 또는 경로 목록이며, 목록이면 `test-file-hash`도 같은 순서의 목록이다. 구 green/refactor 키는 3석 세대 전용 — 신규 기록 금지). `execution-log`는 `phase`·`agent`·`gate`·`result`·`stagnation` 엔트리 배열이다. 아래 예시가 최상위 필드 전체다.

```yaml
phase: implement
status: in_progress
pipeline: gx-tdd
verify-status: pending
verify-fingerprint: ""
model-profile: standard
mode: all
requested-phase: null
execution-phases: [setup, requirements, design, implement, review, complete]
core-plan-status: pending
core-plan-approved-digest: null
mode-transition: null
mode-transition-status: null
transition-requested-phase: null
mode-transition-source: null
intent-source: user-selection
run-id: "현재 실행 UUID"
goal: "로그인 기능 추가"
stop-at: verify
handoff-file: ".dev/20261109-153000-login/handoff.json"
request-file: ".dev/20261109-153000-login/intake.json"
entry-approved-run: "현재 실행 UUID"
entry-approved-source: "진입 질문의 실제 사용자 응답"
entry-approved-scope-sha256: "원래 요청 범위 SHA-256"
implementation-plan-file: ".dev/feat-login/implementation-plan.md"
implementation-plan-sha256: "구체 T계획 SHA-256"
plan-approved-run: "현재 실행 UUID"
plan-approved-source: "계획 검토의 실제 사용자 응답"
plan-approved-sha256: "구체 T계획 SHA-256"
execution-method: session
execution-method-run: "현재 실행 UUID"
execution-method-plan-sha256: "구체 T계획 SHA-256"
execution-method-source: "현재 세션 선택의 실제 사용자 응답"
work-id: W01
flags: ""
vcs-type: git
branch: feat/login
base: main
project-type: java-spring
project-root: ./
args: "로그인 기능 추가"
started: 2026-02-17T10:30:00
last-known-head: 7c9e814
auto-stashed: false
auto-stash: ""
warnings-baseline: 12
baseline-fingerprint: "7c9e814:3ca970cc12ab"
known-failures: []
test-plan-override: null
current-step: "RGR T2: FIX R2"
phases: { setup: completed, requirements: completed, design: completed, implement: in_progress }
steps:
  implement:
    - "RGR T1 (AC-1)": { red: completed, test-file: src/test/.../PasswordValidatorTest.java, test-file-hash: 3ca970cc..., test-count: 47, report: reports/t1-impl.md, impl: completed }
    - "RGR T2 (AC-2)": { red: completed, impl: in_progress, fix-round: 2/5 }
execution-log:
  - { phase: design, agent: test-architect, result: "testability score 8/10 PASS" }
  - { phase: implement, agent: session-implement (T2), result: "fix round 2/5 진행 중" }
```

| 필드 | 기록·검증 |
|---|---|
| `status` | `in_progress` / `completed` / `cancelled`. 전이는 아래 갱신 규칙의 status·cancelled 수명주기 |
| `known-failures` | 기준선(phase-implement Step 0.5)에서 사용자가 "기존 실패를 알고 진행"을 고른 실패 테스트 ID 목록. 기본 `[]`. verify는 이 목록 밖의 **새 실패**만 차단한다. 베이스 동기화 뒤 사용자가 고른 베이스 실패도 추가한다(phase-complete Step -1). 기록할 때 trust-ledger `### 위험 수용`에 `[기존 실패 알고 진행]` 항목을 함께 남기고, PR 본문 Audit Summary에 "기존 실패 N건(이번 변경과 무관)"을 적는다 |
| `test-plan-override` | `{ command, scope, reason }` 또는 `null`. 테스트 계획 helper가 명령·범위를 정하지 못해 사용자가 실제로 정한 검증 명령·범위와 그 이유. 한 번 받은 답을 리뷰·verify가 다시 묻지 않고 재사용한다. 정본은 [테스트 실행 규약](test-execution.md) |
| `current-step` 초안 값 | `PRD 승인 대기`·`설계 승인 대기` — 초안을 표시하고 승인을 기다리는 중. 같은 디렉토리의 `prd.draft.md`·`design.draft.md`와 짝이다(문서 보관) |

**갱신 규칙:**
- Phase 진입 시: `phase: {name}`, `phases.{name}: in_progress`로 갱신.
- Phase 완료 시: `phases.{name}: completed`로 갱신한다. **git인 경우** `last-known-head`를 현재 `git rev-parse HEAD`로 갱신한다 (svn은 미사용).
- Phase 내 주요 Step 시작/완료 시: `current-step`과 `steps` 갱신.
- **RGR 사이클**: 각 태스크의 red/impl 단계를 `"RGR T{N} (AC-N)"` 형식의 중첩 객체로 추적한다 (구 green/refactor 키는 3석 세대 전용 — 신규 기록에 사용 금지). (옛 "coder 구현/자기점검" 형식 사용 금지)
- **G-W-T / testability 게이트 결과**: `execution-log`에 `gate: G-W-T` 또는 `agent: test-architect` 엔트리로 기록.
- **verify 게이트 결과**: complete Step -1의 verify 결과를 execution-log에 기록한다(gx-commit은 verify를 실행하지 않고 별도 보호 게이트를 적용한다). 위험 수용 통과는 오케스트레이터가 trust-ledger에도 기록한다.
- **verify-status 전이**: [문서 수명주기](document-lifecycle.md)에 따라 현재 AC/인수 대조와 관련 context/원장 반영 후 phase-complete Step -1 최종 verify를 수행한다. 통과 시 최상위 `verify-status: passed`와 **같은 시점의 문서 포함 코드 지문을 `verify-fingerprint`에 함께 기록한다**. `verify-fingerprint` 키는 state.md에 한 줄만 두고 기존 줄을 덮어쓴다(새 줄을 덧붙이지 않는다). 이후 코드 또는 context/ 변경이 있으면 즉시 `pending`·빈 지문으로 리셋하고 AC/문서 대조부터 다시 수행한다. 차단/취소/수리 전 이번 실행이 투영한 새 ✅만 journal 해시를 확인해 조건부 원복한다. "수정"(verify 회귀 수리)을 고른 때에도 pending·빈 지문을 유지한다. 새 파이프라인 시작·부트스트랩 시 초기값은 `pending`.
- **status 수명주기**: `status: completed`인 state.md에 **어떤 Phase든 재진입하면 `status: in_progress`로 되돌리고 `verify-status: pending`·`verify-fingerprint: ""`로 리셋한다**. 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)이 `status: in_progress`를 판별 조건으로 쓰므로, 완료 표식이 남은 채 재작업하면 게이트가 전부 꺼진다.
- **cancelled 수명주기**: `status: cancelled`는 사용자가 작업 취소를 실제로 고른 응답(verify 차단의 "중단", 작업 취소 요청 등)으로만 기록한다. 미응답·시간 경과·오류로 바꾸지 않는다. state·decisions·reports·trust-ledger 기록은 지우지 않고 취소 근거를 decisions.md에 남긴다. 게이트 4곳은 `in_progress`만 보므로 취소 뒤에는 verify 게이트가 꺼진다. 단 gx-commit·gx-pull-request는 verify 미통과면 경고하고 커밋·PR에 "verify 미통과(취소된 TDD 작업)"를 표기한다(검증을 대신하지 않는다). 다시 열기도 사용자 응답으로만 하며(setup-resume `--resume`), 열면 completed 재진입과 같이 `status: in_progress`·`verify-status: pending`·`verify-fingerprint: ""`로 되돌린다.
- **execution-log 기록 규약**: `result:` 등 자유 텍스트에 판별 키 문자열(`verify-status: passed`, `pipeline: gx-tdd`)을 **그대로 쓰지 않는다** — 훅이 부분 문자열로 매칭하면 게이트가 조용히 꺼질 수 있다. 필요하면 "verify 통과 표식 미전이"처럼 키를 인용하지 않고 서술한다 (훅은 `verify-status`에 줄 시작 앵커를 쓰지만, 다른 키까지 앵커를 쓰지는 않는다).
- **기준선 게이트 결과**: phase-implement Step 0.5에서 최상위 필드 `warnings-baseline: N`을 기록한다. 추출 불가 시 기록하지 않고 execution-log에 "경고 비교 미수행"을 명시한다. requirements 진입 시 기준선 사전 실행을 시작했으면 최상위 `baseline-fingerprint`를 기록한다 (Claude Code·git 전용 — 절차·수용 조건은 phase-implement Step 0.5 "기준선 사전 실행" 절). 필드가 없으면 사전 실행을 하지 않은 것이다.
- `--resume`은 state 복원 → 저장 요청 범위 → PHASES 생성 → resume 커서 적용 순서로 current-step에서 재개한다. 현재 명시 phase는 과거 execution-phases/커서보다 우선한다. 완료 setup·phase는 반복하지 않고 모순은 보고한다. 먼저 setup-resume 0.05의 전이·모드·승인 복원, 다음 0.1 정합성 체크를 수행한다. RGR은 red/impl 단계·test-file-hash/test-count·rgr-t{N}-porcelain.txt로 verify_implement 기준선을 유지한다. implement 이후 complete가 실제 후속 목록에 없을 때만 needs_boundary_regression(PHASES)로 경계 전체 회귀를 수행한다.
- **진입/방법 재개 게이트**: pending 질문은 state 존재 판정보다 먼저 복원한다. `../phases/setup-resume.md` 0.05의 원 handoff·승인·실행방법 검증은 0.1의 이관·stash·기록·빌드/코드 변경 전에 통과한다. 문서로 종료를 선택했으면 `phase: implement`·`status: in_progress`·`current-step: 계획 문서로 종료`·`verify-status: pending`을 유지하고 미구현을 보고한다. 실행방법을 선택한 것으로 기록하거나 phase-complete로 넘어가지 않는다.
- 에이전트 호출 완료 시: `execution-log`에 엔트리 추가 (agent명, result 요약). deprecated 에이전트(coder/qa-manager)는 절대 기록되지 않는다.
- Gate 실행 결과도 `execution-log`에 기록한다 (mechanical-gate, G-W-T, testability, verify, spec-review, quality-review).
- 정체 감지 시: 해당 `execution-log` 엔트리에 `stagnation: {패턴}` 필드를 추가한다.
- phase-complete 완료 시: 현재 요청 범위의 AC/인수·문서 대조·최종 verify·요청한 종료점이 모두 성공한 경우만 `status: completed`로 갱신한다. 구현 완료, 검증 완료, PR 생성, 실제 merged는 구분한다. 미충족/미검증/위험 수용 AC가 남은 W행은 진행을 유지한다. pending 질문·충돌·요청한 commit/PR 실패도 완료로 덮지 않는다.
- **문서 대조 기록**: 같은 run-id의 document-pre/post 결과·snapshot·document-journal과 reports/document-lifecycle.md를 복원한다. 완료 투영의 원래 값·before/after 해시·현재 AC 실행 근거를 보존한다. 최종 verify 후 새 PR URL은 .dev 전달 기록에만 쓴다. context/ 원장 갱신은 후속 명시적 sync 또는 문서 대조/최종 verify 재실행에서 처리한다.
- 새 파이프라인 시작 시 같은 run이거나 끝난(completed·cancelled) state.md만 덮어쓴다. 다른 run-id의 `status: in_progress` state는 덮지 않는다(phase-setup Step 5 이름 충돌 확인·Step 7). `auto-stashed: true`면 `auto-stash`에 자동 stash SHA를 둔다(setup-branch.md).

### verify 지문 (verify-fingerprint)

verify 통과를 "상태 문자열"이 아니라 **"그 시점의 코드"** 로 고정하기 위한 값이다. `passed` 표식만으로는 통과 후 코드를 고치고 커밋해도 게이트가 열리지 않는다(스테일 passed).

- **context/는 제외하지 않는다**: README·원장·정책·아키텍처 문서의 실제 변경을 최종 verify 전에 끝낸다. proof/지문을 만든 뒤 문서 완료 표시를 추가하고 기존 지문을 그대로 쓰지 않는다. `.dev` 진행 기록만 검증 후에 갱신할 수 있다.
- **기록 주체**: `oh-my-gx:gx-verify`는 Write 권한이 없으므로 **통과 보고에 지문 값을 실어 보내고, 오케스트레이터가 state.md에 기록한다**.
- 계산 규약(`.dev` 제외 트리 해시)·트리 성분 대조·하위 호환·svn은 아래 "조건부 운영 규칙"에 있다.

### 조건부 운영 규칙

아래 규칙은 [조건부 운영 규칙](pipeline-operations.md)에 있다. 적힌 시점에만 읽는다. 같은 대화에서 이미 읽었으면 다시 읽지 않고, 압축 뒤에는 다시 읽는다.

| 규칙 | 읽는 시점 |
|---|---|
| 코드 맵 구조, Trust Ledger 구조 | codemap.md·trust-ledger.md를 처음 만들 때 |
| verify 지문 계산·대조 | 지문을 직접 대조하거나 게이트 경고를 해석할 때 |
| gx-work 진입·실행방법 상태 세부 (`session`/`subagents` 플래그, handoff 재검증) | gx-work 인계 재검증, 실행방법 반영, 재개 |
| 핵심 모드 계획 승인 세부 (단독 해시 연결, 승인 무효화, core→all 전이) | core 실행·전이·재개 |
| 베이스 브랜치 감지 | setup Step 2, `--phase review`·`complete`의 환경 감지 |
| Q&A 히스토리 관리 | product-owner·architect를 다시 디스패치할 때 |
| Context Slicing 규칙 | 에이전트 프롬프트를 조립할 때 (phase 파일 지시가 우선) |
| 병렬 실행 규칙 | 여러 에이전트를 함께 디스패치할 때 |
| 정체 감지 + 에스컬레이션 | fix loop·리뷰 반복이 같은 실패를 되풀이할 때 |
| Gate 로직 | phase-review Step 3~4 |
| Diff 수집 규칙 | diff를 모아 에이전트에 넘길 때 (implement 2-V·review·complete) |
