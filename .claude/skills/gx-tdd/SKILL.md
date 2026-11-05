---
name: gx-tdd
version: 1.0.0
description: 기능 개발·버그 수정의 TDD 실행과 기존 TDD 작업 재개 요청에 사용한다. 요구사항·설계·구현계획을 구체화하고 RED-GREEN-REFACTOR와 완료 검증을 수행한다.
argument-hint: "<자연어 요청>"
allowed-tools: ["Bash(python *)", "Bash(python3 *)", "Bash(git *)", "Bash(svn *)", "Bash(test *)", "Bash(mkdir *)", "Bash(cp *)", "Bash(mv *)", "Bash(ls *)", "Bash(find *)", "Bash(pwd *)", "Bash(basename *)", "Bash(dirname *)", "Bash(which *)", "Bash(grep *)", "Bash(wc *)", "Bash(echo *)", "Bash(mktemp *)", "Bash(sort *)", "Bash(rm -f *)", "Bash(./gradlew *)", "Bash(npm *)", "Bash(bun *)", "Bash(npx *)", "Bash(pnpm *)", "Bash(yarn *)", "Bash(pytest *)", "Bash(go *)", "Bash(make *)", "Bash(cmake *)", "Bash(ctest *)", "Bash(ceedling *)", "Bash(cargo *)", "Bash(mvn *)", "Bash(dotnet *)", "Bash(gh *)", "Bash(GH_HOST= *)", "Read", "Edit", "Write", "Glob", "Grep", "Task", "AskUserQuestion", "Skill"]
---

# GX TDD — 테스트 주도 개발

> **이 스킬**: gx-tdd — TDD 사이클 강제 개발 파이프라인
> 공통 진입은 oh-my-gx:gx-work, 개발 실행은 이 스킬이 담당한다. RED-GREEN-REFACTOR와 완료 전 verify 게이트는 항상 유지한다.
> **호출 시 주의**: 이 스킬 내에서 다른 스킬을 호출할 때 반드시 `oh-my-gx:` 접두사를 사용한다.

요구사항·설계·구현·리뷰·검증을 진행하고 요청된 완료점까지 개발 작업을 관리한다. **TDD 사이클이 강제된다.**

항상 한국어로 응답한다.

## 스킬 참조 경로

**번들 파일 경로 규약**: 이 스킬의 phase·참조 파일은 이 SKILL.md와 같은 디렉토리 아래에 있다. **그 지시가 적힌 파일의 위치를 기준으로 한 상대경로**로 Read한다 — 하네스가 플러그인을 어디에 설치하든(Claude Code의 플러그인 캐시, Codex의 스킬 루트) 파일 사이의 상대 위치는 같으므로 경로가 어긋나지 않는다.
- 예: `Read("phases/phase-setup.md")`
- 상대경로 Read가 실패하면, 하네스가 알려준 이 SKILL.md의 절대경로에서 디렉토리 부분을 떼어 앞에 붙인 뒤 다시 시도한다.

**하네스 적응**: 이 문서는 Claude Code 도구명(`Task`·`AskUserQuestion`·`Skill`)으로 서술한다. Codex 등 다른 하네스에서 실행 중이면 먼저 `Read("references/harness-adaptation.md")`로 도구 대응표를 읽고 그대로 옮겨 수행한다. 도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다.
Codex: `../gx-work/references/codex-runtime.md`를 읽는다. 질문은 한 번에 1~3개, 질문마다 선택지는 2~3개. Other를 option으로 직접 추가하지 않는다. 실제 도구 스키마를 우선한다.

Codex Windows: read files as UTF-8 (`Get-Content -Encoding UTF8`).


다른 스킬의 프로세스를 실행할 때 **반드시 `Skill` 도구로 호출**한다:
- 테스트(완료 게이트): `Skill("oh-my-gx:gx-verify")`
- 커밋: `Skill("oh-my-gx:gx-commit")`
- PR 생성: `Skill("oh-my-gx:gx-pull-request")`

`Skill` 도구가 있는 하네스에서는 `Read()`로 스킬 파일을 읽어 인라인 실행하지 않는다 — 그 도구를 거쳐야 `allowed-tools` 제한이 시스템 레벨에서 강제된다. 없는 하네스는 하네스 적응표를 따르되 그 스킬의 게이트를 빼지 않는다.

> **RGR 보조 스킬(gx-red/gx-green/gx-refactor)은 파이프라인에서 호출하지 않는다.** phase-implement는 이 스킬들을 거치지 않고 `red-writer`를 **직접 `Task`로 디스패치**하고 IMPLEMENT는 오케스트레이터가 직접 수행하며(`--isolated`면 `implementer` 디스패치. green-coder/refactor-coder는 단독 스킬 전용), 사이클 제어·검증은 오케스트레이터가 직접 수행한다. gx-red/gx-green/gx-refactor는 사용자가 단계를 단독 실행하거나 보조 스킬끼리 체이닝하는 경로 전용이다.
>
> **의도적 중복 목록**: 이 스킬의 정의 여러 개가 에이전트 자기완결성·라우팅 강제력을 위해 여러 파일에 중복돼 있다. 어느 정의가 어디에 중복돼 있고 무엇이 SSOT인지는 `Read("references/maintenance-notes.md")`에 있다 — 이 스킬이나 에이전트 정의를 **수정할 때** 읽고, 실행 중에는 읽지 않는다.

## 필수 실행 계약 로드

Phase 목록을 계산하기 전에 다음 파일을 순서대로 Read한다.

1. `Read("references/intent-routing.md")`
2. `Read("references/pipeline-state.md")`
3. `Read("references/interaction-contract.md")`
4. `Read("references/roles-and-phases.md")`
5. `Read("references/document-lifecycle.md")` — 개발 전 관련 문서 사전 대조와 구현 후 최종 검증 순서.

다섯 파일을 읽고 [제거된 실행 경로의 중단 규약](references/intent-routing.md#제거된-무인-반복-경로--실행-전-중단)을 먼저 확인한 뒤 아래 TDD Phase 실행 루프를 수행한다. RED → IMPLEMENT → VERIFY와 Given-When-Then 게이트는 아래 본문과 phase 파일 지시를 유지한다.

## Phase 라우팅 — 필수 실행 프로토콜

### 공통 진입과 계획 인계

**계획 전용 인계**: 아래 진입 검증을 통과해도 `read-only: true`·`execution-authorized: false`이면 [탐색 setup](phases/setup-explore.md)과 필요한 requirements/design의 계획 내용만 수행하고 여기서 종료한다. 실행 setup·pipeline/state 초기화·브랜치·빌드·테스트·RED·구현·complete는 수행하지 않는다. 문서 저장 요청이 없으면 결과를 대화에만 제시한다. `ready-for-tdd`는 요청된 계획 단계에 들어갈 수 있다는 뜻이며 구현 허가를 뜻하지 않는다. 일반 구현 인계는 `execution-authorized: true`도 확인한다. `--handoff`의 origin 필드를 지워 직접 호출로 우회하지 않는다.

새로운 사용자는 `oh-my-gx:gx-work`에서 목적·종료점·기존 자료를 정리해 이 스킬로 들어온다. 직접 gx-tdd를 호출한 경우도 동일한 TDD 계약을 따른다. `--handoff <JSON>`·`--from-plan <JSON>`이 있으면 먼저 [계획 인계 계약](references/plan-handoff.md)을 읽는다. 기존 결정과 태스크는 검증해서 재사용하고 별도의 중복 계획을 만들지 않는다.

**gx-work 진입 게이트**: `origin: gx-work`인 인계는 실제 프로젝트 절대경로를 읽기 전용으로 확정하고 설치 플러그인의 `scripts/gx-work.py validate-handoff --handoff <절대경로> --project-root <실제 루트>`가 exit 0과 `ready-for-tdd: true`를 함께 반환한 뒤에만 소비한다. 원 요청/계획 포인터·해시·run·종료점·실제 진입 응답을 검증하며, 실패·exit 2·false·미응답이면 원래 질문/보완점으로 돌아간다. 일반 구현 요청 문구로 승인을 대체하지 않는다. 이 검사는 실행 setup·브랜치/stash·빌드·RED/코드 변경·state 초기화보다 먼저다. 재개도 원래 handoff를 재검증한다. gx-work 인계가 없는 직접 호출에는 이 진입 승인을 추가하지 않는다.

PRD·설계·구체 T태스크 계획은 이 파이프라인에서 기존 절차로 완성한다. `phase-implement` Step 1.2에서 계획 링크·범위를 보여주고 현재 세션/서브에이전트/문서로 종료의 한 응답으로 검토와 방법을 확인한다. 초기 명시 방법이 있으면 계획 검토만 확인하고, Step 1.3은 선택 검증·flags 반영을 수행한다. 세션은 GREEN/REFACTOR를 직접 수행하고, 서브에이전트는 `--isolated`로 implementer에 위임한다. RED/리뷰 격리는 유지한다. 같은 run·계획의 유효한 선택은 재사용하며 플래그 충돌을 조용히 덮지 않는다.

`--phase requirements`·`--phase design`처럼 논의·계획만 요청했다면 [탐색 setup](phases/setup-explore.md)을 사용한다. 브랜치·stash·pull은 실제 구현 시작 때만 준비한다. 실행 중인 상태를 가져온 경우 원래 `run-id`·`goal`·`stop-at`를 보존한다. 새 작업은 gx-work helper가 생성한 고유 `run-id`를 사용하며, 기존 산출물의 실행 식별자가 다르면 재개에 섞지 않는다.

완료점 기본값은 `verify`다. 사용자가 요청한 `commit`·`pr`만 추가 실행한다. 기존 세션에 종료점이 없으면 기존 요청과 실제 승인 근거에서 복원하고, 근거 없이 commit/PR 권한을 만들어 넣지 않는다.

> **CRITICAL: Phase 스킵 절대 금지.**
> "요구사항이 명확하다", "범위가 작다", "이미 확정되어 있다", "간단하다" 등 어떤 이유로도 Phase를 건너뛰지 않는다.
> Phase를 건너뛸 수 있는 조건은 검증된 계획 전용 인계의 조기 종료, 핵심 모드(사용자가 명시적으로 선택한 경량 경로 — RGR·verify·G-W-T 게이트는 유지), `--phase` 플래그뿐이다.
> 이 규칙을 위반하면 사용자가 기대하는 PRD, 설계서, 리뷰가 누락되어 품질 사고가 발생한다.
>
> **Phase 합치기 절대 금지.**
> 여러 Phase를 하나의 Agent 호출에 합쳐서 실행하지 않는다. 각 Phase는 반드시 **개별 Phase 파일을 Read한 후 순차적으로** 실행한다.
> "간단하니까 한꺼번에", "효율을 위해 합쳐서" 같은 이유로 Phase를 병합하지 않는다.
> Phase 파일을 Read하지 않고 오케스트레이터가 직접 Phase 내용을 수행하는 것도 금지한다.

### Phase 실행 루프

아래 의사코드를 기계적으로 실행한다. **판단하지 말고 순서대로 실행한다.**

```
# 1. 모드에 따라 Phase 목록 결정
# gx-work handoff는 위 진입 게이트 통과 후에만 Phase를 실행한다.
if HANDOFF_READ_ONLY:  # 검증된 read-only: true, execution-authorized: false
    Read(setup-explore); 요청한 requirements/design 계획 내용만 제시
    # 문서 저장은 요청한 범위만. setup·pipeline/state·코드·테스트 변경 없이 종료.
    return  # READ_ONLY_COMPLETE
if core (핵심 모드):
    PHASES = [setup, requirements, implement, complete]   # requirements는 core 분기 (오케스트레이터 직접 ac.md)
elif --phase == "requirements":
    PHASES = [explore, requirements]
elif --phase == "design":
    PHASES = [explore, design]
elif --phase 지정:
    PHASES = [해당 phase만]
else:  # ALL
    PHASES = [setup, requirements, design, implement, review, complete]

# 2. Phase별 순차 실행 (건너뛰기 금지)
for phase in PHASES:

    # Codex 필수 질문 게이트: pending status가 exit 2이면 질문을 표시하고 실제 답변을 기다린다.
    # answer 기록·해제 전 phase 실행·완료 표시는 하지 않는다. 자세한 절차는 codex-runtime 참조.

    # 문서 사전 대조 — setup/explore 이후 모든 진입(--phase/--resume/--core 포함)
    # references/document-lifecycle.md의 사전 대조를 수행한다. 이미 같은 범위를 확인했으면 차이만 확인한다.
    # requirements의 AC 확정 후 implement 직전에 다시 대조한다. 리뷰/조회/계획/문서 금지는 읽기만 한다.

    # 2a. 산출물 게이트 — 이전 Phase 산출물이 없으면 이전 Phase부터 실행 (순서 중요: 상위 의존성 먼저 체크)
    if phase == "design" and not exists("${DEV_DIR}/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and core and not exists("${DEV_DIR}/ac.md"):
        → phase-requirements(core 분기)부터 실행
    if phase == "implement" and not core and not exists("${DEV_DIR}/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and not core and not exists("${DEV_DIR}/design.md"):
        → phase-design부터 실행

    # 2a-1. testability 게이트 (Iron Law) — design.md에 testability 섹션 필수
    if phase == "implement" and not core:
        design_content = Read("${DEV_DIR}/design.md")
        if "## Testability 평가" not in design_content:
            → 사용자 경고: "design.md에 testability 평가가 누락됨. red-writer가 격리 전략을 모름."
            → phase-design 재실행 (test-architect 호출 강제)

    if phase == "review" and 변경사항 없음:
        # git: `git status --porcelain`(스테이징·미스테이징·untracked 포함)이 비어있고 **그리고** `git log {base}..HEAD` 커밋도 없을 때만 중단.
        #      워킹트리 변경 또는 브랜치 커밋 어느 한쪽이라도 있으면 진입한다 (커밋만 있는 경우의 diff 구성은 phase-review Step 1.1이 처리).
        # svn: `svn status` 출력이 비어있을 때
        → "변경사항이 없습니다" 보고 후 중단

    # 2b. Phase 파일 Read (필수)
    # explore는 Read("phases/setup-explore.md"), 그 외는 아래 경로를 사용한다.
    Read("phases/phase-{phase}.md")

    # 2c. Phase 파일의 지시에 따라 실행
    # implement Step 1.2~1.3에서 문서 종료/미응답이면 미구현을 보고하고 루프를 종료한다.
    # 이 경우 2d의 phase 완료 표시나 다음 phase를 수행하지 않는다.

    # 2d. state.md 갱신
    # Codex에서 질문 대기로 phase가 끝나지 않았다면 완료 표시를 하지 않고 현재 phase를 유지한다.
    # complete는 Step 5의 실제 완료 조건을 통과했을 때만 완료 표시한다.
    # 미충족 AC/미검증/문서 충돌/요청한 전달 실패이면 in_progress를 유지하고 중단한다.
    Update state.md → phases.{phase}: completed (해당 Phase의 모든 완료 조건 통과 시에만)

    # 2e. 다음 Phase로 진행
    # implement Step 1.2~1.3의 문서 종료 선택이면 미구현 상태를 보고하고 여기서 루프를 종료한다.
    # Codex에서는 미응답 pending 질문이 있으면 다음 Phase로 진행하지 않고 현재 Phase에서 대기한다.
```

### Phase 파일 경로

`phase-setup.md`, `phase-requirements.md`, `phase-design.md`, `phase-implement.md`, `phase-review.md`, `phase-complete.md`

### Agent 팀 강제

Phase 실행 시 반드시 이 스킬에 정의된 Agent 팀(product-owner, architect, test-architect, design-critic, red-writer, implementer, reviewer, security-auditor, researcher, hacker, simplifier)을 사용한다. (green-coder·refactor-coder는 파이프라인 미호출 — 단독 스킬 전용) (완료 검증은 별도 에이전트가 아니라 `oh-my-gx:gx-verify` 스킬이 담당한다.)

**디스패치 이름 규칙**: `Task` 호출 시 `subagent_type`은 `oh-my-gx:` 접두사를 포함한 정식 이름을 사용한다 (예: `oh-my-gx:red-writer`). 플러그인 설치 환경에서 에이전트는 접두사형으로 등록되므로 bare 이름은 해석되지 않을 수 있다.

**Iron Law**: 다음 에이전트는 oh-my-gx:gx-tdd에서 **절대 호출하지 않는다** (deprecated):
- `coder` — red-writer/implementer로 재편됨 (구 3석: green/refactor-coder)
- `qa-manager` — spec-reviewer·quality-reviewer 구 2석 분해를 거쳐 reviewer로 통합됨

외부 Agent(sisyphus-junior, sisyphus-junior-high 등)로 대체하지 않는다.

## Phase 선택 (--phase 플래그)

`--phase` 실행 목록:
- `--phase requirements`: `[explore, requirements]`를 실행하여 환경을 읽고 관련 도메인 컨텍스트로 PRD를 작성한다. 실행 setup은 하지 않는다.
- `--phase design`: `[explore, design]`을 실행한다. 탐색 후 `${DEV_DIR}/prd.md`가 없으면 게이트가 requirements를 먼저 실행한다.
- `--phase implement`: 환경 감지 + implement 실행. 대화 맥락에 설계서가 없고 `${DEV_DIR}/design.md`도 없으면: "설계서가 필요합니다. `/gx-tdd --phase design`을 먼저 실행하거나 설계 내용을 입력해주세요." 후 중단.
- `--phase review`: 환경·베이스 브랜치 감지 후 현재 변경사항을 리뷰한다. **결과 보고로 종료하고 phase-complete로 체이닝하지 않는다** (`--phase complete` 별도 실행). 리뷰만 요청한 부트스트랩 실행은 `status: completed`로 갱신한다. 원래 개발 실행의 문서/최종 검증이 남았으면 `phases.review`만 완료하고 실행은 진행 상태를 유지한다.
- `--phase complete`: 환경 감지 + 베이스 브랜치 감지 + complete 실행 (인수 검증, test, commit, PR, status 갱신). TDD 이행 여부는 phase-complete **진입부의 TDD 이행 게이트(Step -2)** 가 모든 진입 경로에서 공통 검사한다.

> **환경 감지**: 위 3개 모드는 phase-setup을 건너뛰므로, Phase 진입 전에 다음을 수행한다:
> 1. `PROJECT_ROOT` = phase-setup과 같은 우선순위의 절대경로. 이후 config, `.dev`, context, VCS·빌드·테스트 명령은 이 경로를 기준으로 수행한다.
> 2. `${PROJECT_ROOT}/.claude/config.json`의 `"vcs"`로 `VCS_TYPE`을 결정한다 (없거나 파싱 불가하면 `"git"`).
> 3. **git**: `git rev-parse --is-inside-work-tree`로 repo 확인. **svn**: `svn info`로 작업 복사본 확인.
> 4. **git**: `git branch --show-current` → `/`를 `-`로 치환 → `DEV_DIR = .dev/{branch-slug}/`. **svn**: `${PROJECT_ROOT}/.dev/.active`가 가리키는 `DEV_DIR = .dev/{slug}/` (`.active` 부재·공백 시 `.dev/trunk/` 폴백).
> 5. `MODEL_PROFILE`: `${DEV_DIR}/state.md`의 `model-profile` 값이 있으면 사용하고, 없으면 플래그(`--eco`/`--standard`) > config.json `modelProfile` > `standard` 순으로 결정한다 (phase-setup Step 1.5와 동일 규칙 — eco 디스패치 오버라이드가 이 값에 의존하므로 생략하지 않는다).
> 6. 현재 DEV_DIR의 제거된 실행 경로 검사를 먼저 수행하고 해당하면 쓰기 없이 중단한다. gx-work 인계는 진입 게이트를 먼저 통과해야 한다. 기존 state가 있으면 쓰기 전에 [재개 계약 0.05](phases/setup-resume.md)로 원 handoff·승인·방법을 복원/검증한다. `${DEV_DIR}/state.md`가 없으면 최소 골격을 생성한다 (`pipeline: gx-tdd`, `status: in_progress`, `verify-status: pending`, `model-profile: {5에서 결정한 값}`, `branch`, 원래 `flags`). [상태 계약](references/pipeline-state.md)의 run·진입 승인·원문 포인터·실행방법 필드도 보존한다. **이미 존재하고 `status: completed`이면 `status: in_progress`·`verify-status: pending`으로 되돌리고 `verify-fingerprint`를 비운다.** 재진입 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)이 `status: in_progress`를 요구한다. `--phase implement` 기준선 게이트(Step 0.5)가 warnings-baseline을 기록해야 `--phase complete`의 gx-verify가 로드한다. `pipeline`/`verify-status`는 커밋/PR 게이트(skill-routing·gx-commit·gx-pull-request)에 필요하다.
> 7. `--work {ID}`가 지정되었으면 **기존 work-id를 먼저 대조**한다. 다른 작업이면 기존 연결을 보존하고 명시적인 전환 결정을 받기 전 기록하지 않는다. `references/document-lifecycle.md`의 사전 대조로 행·원장·run/branch 연결을 검증한 뒤에만 `${DEV_DIR}/state.md`에 `work-id: {ID}`를 기록한다. 이 경로는 phase-setup을 건너뛰므로 없는 ID를 만들거나 조용히 무시하지 않는다. work 미지정도 관련 원장·W계획을 확인하며, 조회/계획/문서 금지 범위는 쓰지 않는다.

---
