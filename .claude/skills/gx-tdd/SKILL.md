---
name: gx-tdd
version: 1.0.0
description: "PRD → 설계 → RED-GREEN-REFACTOR → 리뷰(reviewer 통합) → verify → 커밋/PR. TDD 사이클 강제 + verify 게이트. 일반 개발은 oh-my-gx:gx-dev 사용."
argument-hint: "<자연어 요청>"
allowed-tools: ["Bash(git *)", "Bash(svn *)", "Bash(test *)", "Bash(mkdir *)", "Bash(cp *)", "Bash(mv *)", "Bash(ls *)", "Bash(find *)", "Bash(pwd *)", "Bash(basename *)", "Bash(dirname *)", "Bash(which *)", "Bash(grep *)", "Bash(wc *)", "Bash(echo *)", "Bash(mktemp *)", "Bash(sort *)", "Bash(rm -f *)", "Bash(./gradlew *)", "Bash(npm *)", "Bash(bun *)", "Bash(npx *)", "Bash(pnpm *)", "Bash(yarn *)", "Bash(pytest *)", "Bash(go *)", "Bash(make *)", "Bash(cmake *)", "Bash(ctest *)", "Bash(ceedling *)", "Bash(cargo *)", "Bash(mvn *)", "Bash(dotnet *)", "Bash(gh *)", "Bash(GH_HOST= *)", "Read", "Edit", "Write", "Glob", "Grep", "Task", "AskUserQuestion", "Skill"]
---

# gx-tdd

> **이 스킬**: gx-tdd — TDD 사이클 강제 개발 파이프라인
> **혼동 주의**: oh-my-gx:gx-dev와 다른 스킬. 구현 단계가 RED-GREEN-REFACTOR로 강제되고, 완료 전 verify 게이트가 강제됨.
> **호출 시 주의**: 이 스킬 내에서 다른 스킬을 호출할 때 반드시 `oh-my-gx:` 접두사를 사용한다.

오케스트레이터. 직무 기반 Agent 팀과 Q&A 피드백 루프로 전체 개발 사이클을 관리한다. **TDD 사이클이 강제된다.**

## gx-tdd vs gx-dev 차별점 (필수 인지)

| 단계 | gx-dev | gx-tdd (이 스킬) |
|------|--------|----------------|
| requirements | 자연어 AC | **Given-When-Then 강제** |
| design | 비판 검토 | **testability 평가 추가** |
| implement | coder 단일 호출 | **RED 격리 디스패치 → IMPLEMENT 세션 직접 (기본. `--isolated`면 implementer 디스패치). 태스크 = AC 1건** |
| review | qa+security 병렬 | **reviewer 통합 1석 (spec verdict 선행)** |
| complete | qa 통과 → commit | **verify 게이트 → commit** |

항상 한국어로 응답한다.

## 스킬 참조 경로

**번들 파일 경로 규약**: 이 스킬의 phase·참조 파일은 이 SKILL.md와 같은 디렉토리 아래에 있다. **그 지시가 적힌 파일의 위치를 기준으로 한 상대경로**로 Read한다 — 하네스가 플러그인을 어디에 설치하든(Claude Code의 플러그인 캐시, Codex의 스킬 루트) 파일 사이의 상대 위치는 같으므로 경로가 어긋나지 않는다.
- 예: `Read("phases/phase-setup.md")`
- 상대경로 Read가 실패하면, 하네스가 알려준 이 SKILL.md의 절대경로에서 디렉토리 부분을 떼어 앞에 붙인 뒤 다시 시도한다.

**하네스 적응**: 이 문서는 Claude Code 도구명(`Task`·`AskUserQuestion`·`Skill`)으로 서술한다. Codex 등 다른 하네스에서 실행 중이면 먼저 `Read("references/harness-adaptation.md")`로 도구 대응표를 읽고 그대로 옮겨 수행한다. 도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다.
Codex: `../gx-dev/references/codex-runtime.md`를 읽는다. 질문은 한 번에 1~3개, 질문마다 선택지는 2~3개. Other를 option으로 직접 추가하지 않는다. 실제 도구 스키마를 우선한다.

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

세 파일을 읽은 뒤 아래 TDD Phase 실행 루프를 수행한다. RED → IMPLEMENT → VERIFY와 Given-When-Then 게이트는 아래 본문과 phase 파일 지시를 유지한다.

## Agent 팀 (총 15종)

### PRODUCT
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| product-owner | PRD 작성 + 인수 검증 | "뭘 만들지" / "비즈니스 의도대로 됐나" | sonnet |

### PLANNING
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| architect | 설계 | "어떻게 만들지" / "구조적 일관성" | opus |
| **test-architect** | **testability 평가 (신규)** | **"어떻게 테스트할 수 있나"** | **opus** |

### REVIEW
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| design-critic | 설계 비판 검토 | "이 가정이 맞나" / "더 단순하게 안 되나" | opus |
| **reviewer** | **spec Part 1 + quality Part 2 통합. phase-implement 2-V 태스크 범위 모드는 sonnet** | **"스펙대로인가 → 잘 짜였나" — Part 1 verdict 선행** | **opus** |
| security-auditor | 정책/보안/허점 감사 | "뭘 놓쳤나" | sonnet |
| ~~qa-manager~~ | (deprecated — spec-reviewer·quality-reviewer로 분해 후 reviewer로 통합) | — | — |

### EXECUTION (RED 디스패치 → IMPLEMENT 세션 직접; `--isolated`·fix 4~5·ralph는 implementer)
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| **red-writer** | **실패 테스트 작성 전담 (신규)** | **"테스트만 작성" — 프로덕션 코드 안 봄** | **sonnet** |
| **implementer** | **GREEN+REFACTOR 통합 — `--isolated`·fix 라운드 4~5 격상·gx-ralph 루프에서 디스패치. 기본 경로는 세션이 같은 계약으로 직접 수행** | **"최소 통과 후 안전한 정리" — 테스트 수정 금지, focused만 실행** | **sonnet** |
| green-coder / refactor-coder / ~~coder~~ | (파이프라인 미호출 — 단독 스킬 전용; coder deprecated → red-writer/implementer로 재편) | — | sonnet |

### VERIFICATION
완료 검증은 **에이전트가 아니라 `oh-my-gx:gx-verify` 스킬**이 담당한다. phase-complete의 Step -1에서 `Skill("oh-my-gx:gx-verify")`로 호출되어 테스트/빌드를 직접 실행하고 0 failures를 확인한다.

### ANALYSIS
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| researcher | 코드베이스 조사 + 기술 비교 | "이해한다" (독립 호출 전용) | sonnet |

### RECOVERY (정체 시)
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| hacker | 제약 우회 + 정체 탈출 | "다른 길이 있다" (정체 감지 시 호출) | sonnet |
| simplifier | 복잡도 제거 + 범위 축소 | "더 작게 만들자" (정체 감지 시 호출) | sonnet |

### 모델 라우팅 원칙

- 비판적 분석 / 구조적 설계 / 코드 품질 리뷰 / testability 평가: **opus** — 추론 깊이 우선
- PRD 작성 / spec 리뷰 / RED-GREEN-REFACTOR 구현 / 보안 감사 / 정체 탈출: **sonnet** — 비용 효율 우선
- verify 게이트: **`oh-my-gx:gx-verify` 스킬**이 담당 (별도 에이전트 아님). 테스트/빌드 직접 실행 + 0 failures 확인
- Mechanical Gate 결과 판단: 오케스트레이터가 직접 수행 — 에이전트 불필요
- 위 원칙과 Agent 팀 표의 모델은 **표준 프로파일(standard)** 기준이다. 에코 모드(eco)에서는 architect를 제외한 opus 에이전트가 sonnet으로 하향된다 — 공유 규칙 "모델 프로파일" 참조.
- **최소 강도 + 실패 시 격상**: 각 역할을 감당하는 가장 약한 모델을 쓰되(sonnet이 바닥 — haiku 강등 금지), 격상은 fix loop 라운드 4~5에서만 수행한다.

## Phase 개요 (TDD 강제)

| Phase | 파일 | 주 Agent | TDD 강제 사항 | Q&A Loop |
|-------|------|----------|--------------|----------|
| setup | phase-setup.md | (inline) | — | No |
| requirements | phase-requirements.md | product-owner (핵심 모드는 inline — 오케스트레이터 직접 ac.md) | **AC = Given-When-Then 강제** (G-W-T 게이트 — 오케스트레이터 직접 검증) | Yes (max 1) |
| design | phase-design.md | architect + design-critic + **test-architect** | **testability score ≥ 7 필수** (미충족 시 재설계) | Yes (max 2) |
| implement | phase-implement.md | **red-writer(디스패치) → 세션 IMPLEMENT (`--isolated`: implementer) → 조건부 태스크 리뷰(reviewer)** | **Iron Law 1**: 실패 테스트 없이 코드 작성 금지 | RGR 사이클 |
| review | phase-review.md | **reviewer (spec+quality 통합 1석)** + security-auditor (병렬) | **Iron Law**: Part 1(spec) verdict 확정 전 Part 2 판정 금지 | Yes (max 2) |
| complete | phase-complete.md | **gx-verify(스킬)** → product-owner (인수) → commit/PR | **Iron Law 3**: verify 게이트 통과 필수 (테스트 실행 증거) | 인수 재시도 (max 1) |

**핵심 차별점 (gx-dev 대비)**:
- requirements/design에 **사전 게이트** (G-W-T, testability)
- implement는 **RED 격리 디스패치 + 세션 IMPLEMENT** (red-writer만 기존 코드 격리. `--isolated`로 implementer 디스패치 복원)
- review는 **reviewer 1석의 Part 1(spec) → Part 2(quality) 내부 순서 강제** (spec verdict 선행) + security 병렬
- complete는 **gx-verify 스킬 우선 호출** (verify 통과 없이 commit 진입 금지)

### 핵심 모드 경로 (core)

소형 변경용 경량 경로. 설계/정식 리뷰를 건너뛰고 AC 작성을 오케스트레이터가 직접 수행하지만, **RGR 사이클 + verify 게이트 + G-W-T 게이트 + 긴급 보안 감사 + AC 자가 검증은 실행**한다:
```
core: setup → requirements (core: 오케스트레이터 직접 ac.md + G-W-T 게이트) → implement (RGR + H1~H4 긴급감사) → complete (verify + AC 자가 검증)
all:  setup → requirements → design → implement (RGR) → review (spec+quality 통합 1석 + security 병렬) → complete (verify + 인수 + commit + PR)
```
- **requirements (core 분기)**: 오케스트레이터가 `${DEV_DIR}/ac.md`(배경 + 요구사항: G-W-T 형식 AC 3~5개)를 직접 작성한다 — product-owner 디스패치 없음. **G-W-T 검증 게이트는 동일하게 통과 필수** (RGR의 입력 계약이므로), 사용자 확인 1회.
- **design**: 건너뛴다. RGR 사이클이 ac.md + 코드 맵을 기반으로 진행 (testability 평가 없이).
- **implement**: 전체 모드와 동일하게 RGR 사이클 수행. 단, design.md 부재로 red-writer에 ac.md의 AC만 전달하고 세션이 그 AC로 구현. 사이클 종료 후 H1~H4 (긴급 보안 감사: CRITICAL/HIGH만) 실행.
- **review**: 건너뛴다 (긴급 보안 감사가 H1~H4에서 대체).
- **complete**: verify 게이트 → **AC 자가 검증**(오케스트레이터가 ac.md의 AC별 충족을 체크리스트로 판정 — product-owner 디스패치 없음. verify가 테스트 증거를 이미 강제한다) → commit → PR.
- 긴급 버그 수정 요청("긴급/핫픽스" 키워드)도 이 경로다 — AC를 재현 조건 관점의 G-W-T로 작성한다.

**Iron Law 유지 (core여도)**:
- Iron Law 1 (실패 테스트 우선): RGR 사이클이 core에서도 강제됨
- Iron Law 3 (verify 게이트): complete의 Step -1에서 강제됨
- 우회 가능한 것은 design Phase (testability 평가)와 정식 review뿐

## Phase 라우팅 — 필수 실행 프로토콜

> **CRITICAL: Phase 스킵 절대 금지.**
> "요구사항이 명확하다", "범위가 작다", "이미 확정되어 있다", "간단하다" 등 어떤 이유로도 Phase를 건너뛰지 않는다.
> Phase를 건너뛸 수 있는 조건은 핵심 모드(사용자가 명시적으로 선택한 경량 경로 — RGR·verify·G-W-T 게이트는 유지), `--phase` 플래그, 그리고 `--ralph`(플래그 또는 자연어 `랄프로` 등)로 phase-implement Step 0.7에서 **gx-ralph로 전환**한 경우(gx-ralph 호출 후 종료 — 이후 Phase는 루프 종료 후 사용자 복귀로 재개)뿐이다.
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
if core (핵심 모드):
    PHASES = [setup, requirements, implement, complete]   # requirements는 core 분기 (오케스트레이터 직접 ac.md)
elif --phase == "requirements":
    PHASES = [setup, requirements]
elif --phase == "design":
    PHASES = [setup, design]
elif --phase 지정:
    PHASES = [해당 phase만]
else:  # ALL
    PHASES = [setup, requirements, design, implement, review, complete]

# 2. Phase별 순차 실행 (건너뛰기 금지)
for phase in PHASES:

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
    Read("phases/phase-{phase}.md")

    # 2c. Phase 파일의 지시에 따라 실행

    # 2d. state.md 갱신
    Update state.md → phases.{phase}: completed

    # 2e. 다음 Phase로 진행
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
- `--phase requirements`: `[setup, requirements]`를 실행하여 작업환경과 도메인 컨텍스트를 확정한 뒤 PRD를 작성한다.
- `--phase design`: `[setup, design]`을 실행한다. setup 후 `${DEV_DIR}/prd.md`가 없으면 게이트가 requirements를 먼저 실행한다.
- `--phase implement`: 환경 감지 + implement 실행. 대화 맥락에 설계서가 없고 `${DEV_DIR}/design.md`도 없으면: "설계서가 필요합니다. `/gx-tdd --phase design`을 먼저 실행하거나 설계 내용을 입력해주세요." 후 중단.
- `--phase review`: 환경·베이스 브랜치 감지 후 현재 변경사항을 리뷰한다. **결과 보고로 종료하고 phase-complete로 체이닝하지 않는다** (`--phase complete` 별도 실행). 종료 시 부트스트랩 골격 state.md는 `status: completed`로 갱신한다.
- `--phase complete`: 환경 감지 + 베이스 브랜치 감지 + complete 실행 (인수 검증, test, commit, PR, status 갱신). TDD 이행 여부는 phase-complete **진입부의 TDD 이행 게이트(Step -2)** 가 모든 진입 경로에서 공통 검사한다.

> **환경 감지**: 위 3개 모드는 phase-setup을 건너뛰므로, Phase 진입 전에 다음을 수행한다:
> 1. `PROJECT_ROOT` = phase-setup과 같은 우선순위의 절대경로. 이후 config, `.dev`, context, VCS·빌드·테스트 명령은 이 경로를 기준으로 수행한다.
> 2. `${PROJECT_ROOT}/.claude/config.json`의 `"vcs"`로 `VCS_TYPE`을 결정한다 (없거나 파싱 불가하면 `"git"`).
> 3. **git**: `git rev-parse --is-inside-work-tree`로 repo 확인. **svn**: `svn info`로 작업 복사본 확인.
> 4. **git**: `git branch --show-current` → `/`를 `-`로 치환 → `DEV_DIR = .dev/{branch-slug}/`. **svn**: `${PROJECT_ROOT}/.dev/.active`가 가리키는 `DEV_DIR = .dev/{slug}/` (`.active` 부재·공백 시 `.dev/trunk/` 폴백).
> 5. `MODEL_PROFILE`: `${DEV_DIR}/state.md`의 `model-profile` 값이 있으면 사용하고, 없으면 플래그(`--eco`/`--standard`) > config.json `modelProfile` > `standard` 순으로 결정한다 (phase-setup Step 1.5와 동일 규칙 — eco 디스패치 오버라이드가 이 값에 의존하므로 생략하지 않는다).
> 6. `${DEV_DIR}/state.md`가 없으면 최소 골격을 생성한다 (`pipeline: gx-tdd`, `status: in_progress`, `verify-status: pending`, `model-profile: {5에서 결정한 값}`, `branch`, `flags: --phase {name}`). **이미 존재하고 `status: completed`이면 `status: in_progress`·`verify-status: pending`으로 되돌리고 `verify-fingerprint`를 비운다.** 재진입 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)이 `status: in_progress`를 요구한다. `--phase implement` 기준선 게이트(Step 0.5)가 warnings-baseline을 기록해야 `--phase complete`의 gx-verify가 로드한다. `pipeline`/`verify-status`는 커밋/PR 게이트(skill-routing·gx-commit·gx-pull-request)에 필요하다.
> 7. `--work {ID}`가 지정되었으면 `${DEV_DIR}/state.md`에 `work-id: {ID}`를 기록한다. 이 경로는 phase-setup을 건너뛰어 3.0.5가 실행되지 않으므로, 기록하지 않으면 **지정한 ID가 조용히 무시되고** phase-complete Step 3.5가 `작업 위치` 열로만 행을 찾는다 — 브랜치가 계획에 없으면 아무 일도 일어나지 않는다.

---
