> gx-tdd/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태/질문/페이즈 결정을 추정하지 않는다. 상대경로는 이 파일의 위치를 기준으로 해석한다.

## 코드 맵

오케스트레이터가 관리하는 누적 문서. 관련 파일의 경로와 역할을 기록한다.

**구조:**
```
## 코드 맵: <기능 설명>

### 핵심 파일
- <파일경로:라인> → 역할 설명
- ...

### 참조 파일
- <파일경로:라인> → 역할 설명
- ...

### 설정
- <파일경로> → 역할 설명
- ...
```

**생성**: phase-setup의 Step 0.4에서 초기 맵을 생성한다.
**누적**: 각 agent 출력에 "탐색 추가 항목" 섹션이 있으면 해당 항목을 맵에 append한다. 누적 맵은 **최대 25개**로 제한한다. 초과 시 참조 파일부터 제거한다.
**저장**: 코드 맵이 갱신될 때마다 `${DEV_DIR}/codemap.md`에 Write한다.
**전달**: 모든 agent 호출 시 현재 코드 맵을 프롬프트에 포함한다.

## Trust Ledger (신뢰 원장)

감사 결과와 위험 수용 이력을 누적하는 문서. security-auditor 감사, reviewer의 Critical/Important 요약(Part 2), 각 게이트의 위험 수용 항목을 기록한다. 오케스트레이터가 관리한다.

**위험 수용 기록 규약**: 파이프라인의 모든 위험 수용(테스트 미검증 리뷰, 미해결 Critical 수용, TDD 미이행 완료 실행, 신규 경고 수용, G-W-T 제외, core 긴급 감사 수용 등)은 `### 위험 수용` 섹션에 `- [{항목명}] {사유} ({phase/step})` 형식으로 기록한다. Write 권한이 없는 스킬(gx-verify)은 보고만 하고 **오케스트레이터가 기록**한다.

**구조:**
```
## Trust Ledger

### 통합 감사 (review)
- [분류/심각도] 항목 설명
  - 근거: ...
  - 권고: ...

### 위험 수용
- [{항목명}] {사유} ({phase/step})
```

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

### 모델 프로파일 (MODEL_PROFILE)

에이전트 디스패치의 모델 수준. 절차 축(mode)과 **직교**하며 Phase 구성·게이트·Iron Law에 영향을 주지 않는다.

- 결정 우선순위: `--eco`/`--standard` 플래그 > ARGS[0] 자연어(`에코 모드`/`에코로`/`절약 모드` → eco) > **의도 파싱 Step 3 질문 답변**(모드 확인 질문에 프로파일 질문이 함께 제시된 경우) > config.json `modelProfile` > 기본 `standard`. phase-setup Step 1.5가 이 순서로 확정해 state.md에 기록한다.
- **standard (표준)**: Agent 팀 표의 모델 그대로 디스패치한다.
- **eco (에코 모드)**: **design-critic, test-architect, reviewer**를 Task 호출 시 `model: "sonnet"` 파라미터로 오버라이드하여 디스패치한다 — Task의 model 파라미터는 에이전트 정의(frontmatter)보다 우선한다. **architect는 eco에서도 opus를 유지한다** — 설계 오류는 게이트가 방어하지 못하고 하류 전체로 전파되는 유일한 상류 실패인 반면 호출은 1~2회로 가장 적다 (하향 대상은 실패 모드가 '놓침'인 검증자이며 security-auditor·verify가 별도 축에서 방어). 이미 sonnet인 에이전트(red-writer/implementer, green/refactor-coder 포함)는 그대로 유지한다 (haiku 강등 금지). 이 규칙은 **모든 Phase의 모든 Task 디스패치에 적용**된다 — phase 파일에 개별 표기가 없어도 적용한다. fix loop 라운드 4~5의 opus 격상은 "실패의 대응"으로 프로파일과 독립이다 — eco 세션에서도 격상한다 (하향 규칙은 초기 디스패치 모델에만 적용된다).
- 게이트(G-W-T·testability·기준선·Mechanical Gate·verify)는 모델 무관 기계 검증 또는 스킬(gx-verify) 실행이므로 eco에서도 동일하게 유지된다.
- 오케스트레이터가 직접 수행하는 단계(핵심 모드 ac.md 작성, AC 자가 검증 등)는 메인 세션 모델을 따른다 — 플러그인이 제어하지 않는다.
- `--resume` 시 state.md의 `model-profile`을 복원한다. 재개 중 프로파일 변경은 지원하지 않는다.

### 베이스 브랜치 감지

**svn인 경우** → 베이스 브랜치 개념이 없으므로 건너뛴다 (trunk에서 직접 작업).

**git인 경우:**
`--base`가 지정되었으면 해당 브랜치를 사용한다. 미지정이면 자동 감지:
1. `git branch --list main master develop`로 존재하는 브랜치를 확인한다.
2. 존재하는 브랜치가 **2개 이상**이면 → AskUserQuestion으로 사용자에게 선택지 제시 (예: main, develop).
3. 존재하는 브랜치가 **1개**이면 → 해당 브랜치를 베이스로 자동 선택.
4. 하나도 없으면 → AskUserQuestion(자유입력)으로 직접 입력을 요청한다.

확정된 베이스 브랜치를 이후 phase-review (diff 계산), phase-complete (PR 생성)에서 사용한다.

### Q&A 히스토리 관리
Agent prompt 크기를 관리하기 위해:
- Agent에게는 **최신 설계/리뷰 출력만** 전달한다. 이전 버전은 전달하지 않는다.
- 이전 라운드의 질문+답변은 **핵심 결정 사항만 요약**하여 전달한다 (원문 그대로 X).
- 예: "Q: 세션 기반 vs JWT? → A: JWT 선택. Q: 토큰 만료 시간? → A: 30분"

### Agent 결과 전달 규칙 (컨텍스트 경량화)

| 상황 | 사용자에게 보이는 것 |
|---|---|
| Q&A Phase (requirements, design) 첫 표시 | Agent 출력 **전문** — 산출물 검토용. Phase 파일의 구체적인 표시 규칙이 이 일반 규칙보다 우선한다 |
| Q&A Phase 완료 보고 | 파일에 저장하고 **요약만** ("PRD 확정. ${DEV_DIR}/prd.md에 저장됨") |
| Q&A 없는 Phase (implement, review, complete) | Agent 출력 **요약만**. 전문은 파일·변수 보관 |
| implement Phase의 인계 | **report 파일 경로로만 한다** — red-writer·implementer는 전문을 ${DEV_DIR}/reports/t{N}-*.md에 Write, 상태(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)와 15줄 이내 요약만 반환 (상태 반환은 격리 경로. 세션 경로는 report 파일이 인계 단위) |

이후 Phase에서 이전 산출물이 필요하면 **파일을 Read하여 Agent prompt에 포함**하되, 오케스트레이터 자신의 출력에는 포함하지 않는다. 각 Phase 파일에서 구체적인 요약 포맷을 정의한다.

### 문서 보관
- phase-requirements 완료 시 확정된 PRD를 `${DEV_DIR}/prd.md`에 저장한다. **핵심 모드는 prd.md 대신 `${DEV_DIR}/ac.md`**(G-W-T 형식 AC)에 저장한다 (phase-requirements core 분기).
- phase-design 완료 시 확정된 설계 문서를 `${DEV_DIR}/design.md`에 저장한다 (핵심 모드는 design 단계가 없어 미생성).
- Trust Ledger를 `${DEV_DIR}/trust-ledger.md`에 저장한다 (핵심 모드는 H1~H4 긴급 감사 결과가 여기에 기록된다).
- 코드 맵을 `${DEV_DIR}/codemap.md`에 저장한다 (갱신 시마다).
- phase-design, phase-implement, phase-review 진입 시 해당 파일들을 Read하여 에이전트 프롬프트에 사용한다.
- `.dev/` 산출물은 **협업 공유 대상**으로 커밋에 포함한다 (`.gitignore`에 추가하지 않음 — verify 지문은 `.dev`를 제외하므로 게이트와 무관). `.gitignore` 보강은 phase-setup Step 6에서 config `projectTypes.artifacts` 기준으로 빌드 아티팩트만 처리한다.

### 진행 상태 추적 (state.md)
파이프라인 진행 상태를 `${DEV_DIR}/state.md`에 기록하여 세션 재개를 지원한다.

**state.md 필드**: 초기화 필드의 정본은 phase-setup Step 7, 태스크 객체의 정본 예시는 phase-implement "state.md 추적" 절이다. 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)은 `pipeline: gx-tdd`·`status: in_progress`·`verify-status`·`verify-fingerprint`를 판별 키로 쓴다. `steps`의 RGR 태스크는 `"RGR T{N} (AC-N)"` 객체에 `red`·`impl`·`test-file`·`test-file-hash`·`test-count`·`report`·`fix-round`를 중첩한다 (구 green/refactor 키는 3석 세대 전용 — 신규 기록 금지). `execution-log`는 `phase`·`agent`·`gate`·`result`·`stagnation` 엔트리 배열이다. 아래 예시가 최상위 필드 전체다.

```yaml
phase: implement
status: in_progress
pipeline: gx-tdd
verify-status: pending
verify-fingerprint: ""
model-profile: standard
mode: all
intent-source: user-selection
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
config-setup-attempts: 0
warnings-baseline: 12
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

**갱신 규칙:**
- Phase 진입 시: `phase: {name}`, `phases.{name}: in_progress`로 갱신.
- Phase 완료 시: `phases.{name}: completed`로 갱신한다. **git인 경우** `last-known-head`를 현재 `git rev-parse HEAD`로 갱신한다 (svn은 미사용).
- Phase 내 주요 Step 시작/완료 시: `current-step`과 `steps` 갱신.
- **RGR 사이클**: 각 태스크의 red/impl 단계를 `"RGR T{N} (AC-N)"` 형식의 중첩 객체로 추적한다 (구 green/refactor 키는 3석 세대 전용 — 신규 기록에 사용 금지). (옛 "coder 구현/자기점검" 형식 사용 금지)
- **G-W-T / testability 게이트 결과**: `execution-log`에 `gate: G-W-T` 또는 `agent: test-architect` 엔트리로 기록.
- **verify 게이트 결과**: complete Step -1의 verify 게이트 결과를 `execution-log`에 기록 (gx-commit은 gx-dev와 공유하는 스킬이라 verify 실행을 포함하지 않는다 — 조건부 경고 게이트만 있음). verify가 "위험 수용"으로 통과를 보고하면 오케스트레이터가 trust-ledger에도 기록한다.
- **verify-status 전이**: phase-complete Step -1 verify 통과 시 최상위 `verify-status: passed`로 갱신하고, **같은 시점의 코드 지문을 `verify-fingerprint`에 함께 기록한다**. 이후 코드 변경으로 phase-complete를 재진입하면 `pending`으로 리셋(지문은 빈 값으로) 후 Step -1을 재실행한다. 새 파이프라인 시작·부트스트랩 시 초기값은 `pending`.
- **status 수명주기**: `status: completed`인 state.md에 **어떤 Phase든 재진입하면 `status: in_progress`로 되돌리고 `verify-status: pending`·`verify-fingerprint: ""`로 리셋한다**. 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)이 `status: in_progress`를 판별 조건으로 쓰므로, 완료 표식이 남은 채 재작업하면 게이트가 전부 꺼진다.
- **execution-log 기록 규약**: `result:` 등 자유 텍스트에 판별 키 문자열(`verify-status: passed`, `pipeline: gx-tdd`)을 **그대로 쓰지 않는다** — 훅이 부분 문자열로 매칭하면 게이트가 조용히 꺼질 수 있다. 필요하면 "verify 통과 표식 미전이"처럼 키를 인용하지 않고 서술한다 (훅은 `verify-status`에 줄 시작 앵커를 쓰지만, 다른 키까지 앵커를 쓰지는 않는다).
- **기준선 게이트 결과**: phase-implement Step 0.5에서 최상위 필드 `warnings-baseline: N`을 기록한다. 추출 불가 시 기록하지 않고 execution-log에 "경고 비교 미수행"을 명시한다.
- `--resume` 시 `current-step`에서 재개한다 (Phase 처음부터가 아닌 중단 Step부터). 재개 전에 `../phases/setup-resume.md`의 0.1 정합성 체크(브랜치/HEAD)를 수행한다. RGR 사이클 재개 시 `red/impl` 단계별로 매칭 (태스크의 `test-file-hash`·`test-count`와 `${DEV_DIR}/rgr-t{N}-porcelain.txt` 스냅샷 파일을 함께 사용하여 verify_implement 기준선을 유지).
- 에이전트 호출 완료 시: `execution-log`에 엔트리 추가 (agent명, result 요약). deprecated 에이전트(coder/qa-manager)는 절대 기록되지 않는다.
- Gate 실행 결과도 `execution-log`에 기록한다 (mechanical-gate, G-W-T, testability, verify, spec-review, quality-review).
- 정체 감지 시: 해당 `execution-log` 엔트리에 `stagnation: {패턴}` 필드를 추가한다.
- phase-complete 완료 시: `status: completed`로 갱신.
- 새 파이프라인 시작 시 기존 state.md를 덮어쓴다. `config-setup-attempts`도 0으로 초기화.

### verify 지문 (verify-fingerprint)

verify 통과를 "상태 문자열"이 아니라 **"그 시점의 코드"** 로 고정하기 위한 값이다. `passed` 표식만으로는 통과 후 코드를 고치고 커밋해도 게이트가 열리지 않는다(스테일 passed).

- **계산 규약** (훅·gx-commit·gx-pull-request·라우팅이 동일하게 사용): 임시 인덱스에 워킹트리 전체를 `add -A`한 뒤 `.dev`를 인덱스에서 제거하고 `write-tree`한 **트리 해시**(앞 12자)를 `git rev-parse --short HEAD`와 `:`로 이은 값 (예: `7c9e814:59ca4aacfeab`). **`git diff HEAD`가 아니라 트리 해시**를 쓰는 이유는 신규 파일이 스테이징되면 diff 기반 값이 바뀌어, verify(스테이징 전) → `git add -A` → commit 순서에서 게이트가 오발동하기 때문이다 (RGR은 새 파일 생성이 기본).
- **`.dev/` 제외 이유**: state.md·diff.txt 등 파이프라인 산출물은 코드가 아니며, 포함하면 상태를 기록할 때마다 지문이 스스로 무효화된다 (ignore 누락 저장소에서도 안정).
- **대조는 트리 성분(콜론 뒤)만 수행한다** — HEAD 성분은 기록·추적용이며, 검증된 코드가 그대로 커밋되어 HEAD만 전진한 경우는 일치로 간주한다 (커밋 → PR 정상 경로의 상시 오경고 방지). 단 트리 성분이 `notree`(계산 실패)면 값이 같아도 일치로 보지 않는다 — 코드 동일성이 입증되지 않으므로 보수적으로 재검증을 권고한다.
- **기록 주체**: `oh-my-gx:gx-verify`는 Write 권한이 없으므로 **통과 보고에 지문 값을 실어 보내고, 오케스트레이터가 state.md에 기록한다**. gx-ralph 루프에서는 반복 세션(`oh-my-gx:gx-ralph-iterate`)이 기록 주체다.
- **적용 파이프라인**: `pipeline: gx-tdd`와 `pipeline: gx-ralph` 모두 동일한 규약을 쓴다.
- **하위 호환**: 필드가 없는 구 세션은 기존 판정(`verify-status`만)으로 동작한다.
- **svn**: git 지문을 계산할 수 없어 대조가 성립하지 않는다. 훅은 이 경우 보수적으로 "재검증 권고"를 안내한다.

### Context Slicing 규칙
설계서·PRD는 역할별 필요 섹션만 전달한다. 모든 디스패치에 프로젝트 루트 경로를 포함한다. `contextLimits`(config.json) 초과 시 우선순위 낮은 섹션부터 요약·생략.

| 에이전트 | 전달 입력 |
|---|---|
| product-owner (PRD 작성) | ARGS[0]+코드 맵+프로젝트 타입/구조+DOMAIN_CONTEXT(있으면 — 용어·README 핵심·미반영·아키텍처 4요소. 미반영과 겹치면 FR ID 인용)+**"AC는 반드시 Given-When-Then 형식. 자동 테스트로 변환 가능해야 함"** |
| product-owner (인수 검증) | PRD요구사항+수용기준+`DIFF_FILE`+코드 맵 |
| architect | PRD 전체+코드 맵+프로젝트 타입/구조/컨벤션+DOMAIN_CONTEXT(있으면 — 용어·아키텍처만)+REFERENCES(있으면)+**"각 컴포넌트의 테스트 가능성(의존성 주입, 인터페이스 격리)을 고려"** |
| design-critic | 설계초안+PRD+코드맵 |
| test-architect | 설계서+PRD수용기준+코드 맵+**"각 컴포넌트별 단위/통합 테스트 전략 명시 + testability score 1-10 산정"** |
| red-writer | AC(G-W-T)+testability 섹션+테스트 스타일. **기존 프로덕션 코드는 절대 포함하지 않는다**. **UI 태스크에만** `FRONTEND_TESTING_PATH`(`frontend-testing.md`) |
| 세션 IMPLEMENT (기본 경로) | 디스패치 없음 — 오케스트레이터가 RED report·설계서 인터페이스·focused 명령을 직접 읽고 phase-implement "세션 IMPLEMENT 절차"를 수행 |
| implementer | RED report(reports/t{N}-red.md)+인터페이스+focused 테스트 명령+report 경로. **PRD 전체나 설계서 전체는 전달하지 않는다** |
| reviewer | PRD요구사항+수용기준+설계서변경범위+`DIFF_FILE`+코드 맵+컨벤션+품질기준. **"Part 1 verdict 선행. 테스트 재실행 금지"**. **태스크 범위 모드**(phase-implement 2-V): 태스크 AC+`reports/t{N}-diff.txt`+RED/IMPL report+인터페이스만, `model: "sonnet"` |
| security-auditor | PRD 전체+설계서 전체+`DIFF_FILE`+코드 맵+REFERENCES(있으면) |
| gx-verify (스킬, 완료 게이트) | phase-complete Step -1에서 `Skill("oh-my-gx:gx-verify")`로 호출. config.json의 projectTypes 기반으로 테스트/빌드 명령을 직접 실행. 캐시 결과 사용 금지, 0 failures 확인. 에이전트 Task가 아니므로 Context Slicing(입력 전달) 대상이 아니다. |
| researcher | 조사+코드맵(있으면) |
| hacker | 정체+코드맵 |
| simplifier | 정체+설계서+PRD+코드맵 |

### 병렬 실행 규칙
읽기 전용 Agent(product-owner, architect, test-architect, design-critic, reviewer, security-auditor, researcher, hacker, simplifier)는 서로 병렬 실행이 가능하다. 병렬 실행 시:
1. 하나의 메시지에서 여러 `Task()` 호출을 동시에 발행한다.
2. 모든 병렬 Task가 완료된 후 결과를 합산한다 (Gate 로직).
3. 쓰기 주체(red-writer, 세션 IMPLEMENT, implementer)는 다른 쓰기 Agent와 병렬 실행하지 **않는다**.
4. **RGR 사이클 내 순차 강제 (Iron Law)**: red-writer → IMPLEMENT(세션 또는 implementer)는 **반드시 순차** 실행한다. 병렬 금지.
   - 이유: red-writer 산출물(실패 테스트 — RED report)이 IMPLEMENT의 입력.
   - 위반 시: 격리가 깨져 Iron Law 1 위반.
5. **review 통합 순서 강제 (Iron Law)**: reviewer 1석이 Part 1 → Part 2를 내부 순서로 수행한다 (개별 2석 디스패치 금지).
   - security-auditor는 reviewer와 **병렬 가능** (서로 독립).
6. RGR/review 사이클 외 읽기 Agent의 병렬은 **읽기 Agent가 이전 Phase의 산출물(설계서 등)만 참조하는 경우** 허용한다.

### 정체 감지 + 에스컬레이션

phase-implement(구현→자기점검 루프)와 phase-review(QA→수정→재리뷰 루프)에서 적용한다.
각 루프의 최대 반복은 기존과 동일하다. 정체 감지 시 반복을 소진하지 않고 에스컬레이션으로 전환한다.

#### 감지 패턴

| 패턴 | 감지 기준 | 유형 |
|------|----------|------|
| SPINNING | 동일 에러 메시지가 2회 연속 반복 | 기계적 (텍스트 비교) |
| OSCILLATION | 접근법 A→B→A 왕복이 감지됨 | 정성적 (LLM 판단) |
| NO_DRIFT | 이전 반복과 비교해 코드 변경이 실질적으로 없음 (diff 비교) | 반기계적 (diff stat) |
| DIMINISHING_RETURNS | 수정 범위가 줄어드는데 테스트/리뷰 결과가 개선되지 않음 | 정성적 (LLM 판단) |

#### 에스컬레이션 경로

| 감지 패턴 | 1차 대응 | 2차 대응 (1차 실패 시) |
|----------|---------|---------------------|
| SPINNING | hacker에 제약 우회 분석 위임 | researcher에 근본 원인 분석 위임 |
| OSCILLATION | architect에 설계 재검토 요청 | 사용자에게 두 접근법 제시, 선택 요청 |
| NO_DRIFT | hacker에 제약 식별 + 우회 경로 요청 | researcher에 코드베이스 탐색 위임 |
| DIMINISHING_RETURNS | simplifier에 복잡도 분석 + 범위 축소 요청 | 사용자에게 현재 상태 보고, 방향 전환 여부 확인 |

### Gate 로직
phase-review.md의 Step 3~4에 정의. QA + ZT 결과를 합산하고 심각도별로 처리한다.

### Diff 수집 규칙
Agent에게 변경사항 diff를 전달할 때, 메인 컨텍스트 절약을 위해 **파일 리다이렉트 + 경로 전달**을 사용한다.

**핵심 원칙**: diff 출력이 Bash 결과로 메인 컨텍스트에 진입하지 않도록, **셸 리다이렉트로 파일에 직접 쓴다**.

#### 수집 절차

1. `DIFF_FILE = ${DEV_DIR}/diff.txt`. **매 수집 시** `mkdir -p "${DEV_DIR}"`를 실행하여 디렉토리 존재를 보장한다.
2. diff를 파일에 직접 리다이렉트한다 (Bash 결과에 diff가 나타나지 않음):
   ```bash
   git diff --cached -- . ':(exclude).dev' > "${DEV_DIR}/diff.txt"
   ```
3. `wc -l < "${DEV_DIR}/diff.txt"`로 줄 수를 확인한다.
4. 총 변경이 **500줄 이상**이면: `--stat` 요약을 파일 앞에 추가하고, 파일 끝에 "변경된 파일을 Read 도구로 직접 확인하라"는 안내를 추가한다:
   ```bash
   git diff --cached --stat -- . ':(exclude).dev' > "${DEV_DIR}/diff.txt"
   echo "---" >> "${DEV_DIR}/diff.txt"
   echo "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라." >> "${DEV_DIR}/diff.txt"
   ```
5. Agent 프롬프트에는 **파일 경로만 전달**한다:
   ```
   변경사항 diff: ${DEV_DIR}/diff.txt
   이 파일을 Read하여 변경사항을 확인하라.
   ```

이 규칙은 모든 diff 패턴에 적용한다: `git diff --cached` (스테이징), `git diff <base>...HEAD` (브랜치 비교) 등 — **모든 git diff 명령에 `-- . ':(exclude).dev'` pathspec을 붙여 `.dev` 산출물을 리뷰 diff에서 제외한다** (산출물은 공유 대상이지만 코드 리뷰 대상이 아니며, PRD·AC 전문이 diff로 유입되면 reviewer에게 전달되는 diff가 불필요하게 비대해지고 500줄 초과 강등이 빈발한다). svn은 pathspec 제외가 없으므로 diff 수집 후 리뷰 에이전트 프롬프트에 "`.dev` 경로의 변경은 리뷰 대상에서 제외하라"를 명시한다.
