---
name: gx-tdd
version: 1.0.0
description: "PRD → 설계 → RED-GREEN-REFACTOR → 리뷰(spec→quality) → verify → 커밋/PR. TDD 사이클 강제 + verify 게이트. 일반 개발은 oh-my-gx:gx-dev 사용."
argument-hint: "<자연어 요청>"
allowed-tools: ["Bash(git *)", "Bash(svn *)", "Bash(test *)", "Bash(mkdir *)", "Bash(cp *)", "Bash(mv *)", "Bash(ls *)", "Bash(find *)", "Bash(pwd *)", "Bash(basename *)", "Bash(dirname *)", "Bash(which *)", "Bash(grep *)", "Bash(./gradlew *)", "Bash(npm *)", "Bash(bun *)", "Bash(npx *)", "Bash(pnpm *)", "Bash(yarn *)", "Bash(pytest *)", "Bash(go *)", "Bash(gh *)", "Bash(GH_HOST= *)", "Read", "Edit", "Write", "Glob", "Grep", "Task", "AskUserQuestion", "Skill"]
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
| implement | coder 단일 호출 | **RED → GREEN → REFACTOR (3에이전트 순차; red-writer만 코드 격리)** |
| review | qa+security 병렬 | **spec → quality 순차 강제** |
| complete | qa 통과 → commit | **verify 게이트 → commit** |

항상 한국어로 응답한다.

## 스킬 참조 경로

이 스킬의 파일들은 프로젝트 루트의 `.claude/skills/gx-tdd/` 하위에 위치한다.
Phase 파일이나 다른 스킬을 Read할 때, 현재 작업 디렉토리(프로젝트 루트)를 기준으로 절대 경로를 구성한다.

다른 스킬의 프로세스를 실행할 때 **반드시 `Skill` 도구로 호출**한다:
- 테스트(완료 게이트): `Skill("oh-my-gx:gx-verify")`
- 커밋: `Skill("oh-my-gx:gx-commit")`
- PR 생성: `Skill("oh-my-gx:gx-pull-request")`

`Read()`로 스킬 파일을 읽어 인라인 실행하지 않는다. `Skill` 도구를 사용해야 스킬의 `allowed-tools` 제한이 시스템 레벨에서 강제된다.

> **RGR 보조 스킬(gx-red/gx-green/gx-refactor)은 파이프라인에서 호출하지 않는다.** phase-implement는 이 스킬들을 거치지 않고 `red-writer`/`green-coder`/`refactor-coder` 에이전트를 **직접 `Task`로 디스패치**하며, 사이클 제어·검증은 오케스트레이터가 직접 수행한다. gx-red/gx-green/gx-refactor는 사용자가 단계를 단독 실행하거나 보조 스킬끼리 체이닝하는 경로 전용이다.
>
> **드리프트 주의**: 아래 정의들이 여러 파일에 **의도적으로 중복**되어 있다(에이전트 자기완결성·라우팅 강제력 목적 — 단일 출처화하면 에이전트/프롬프트가 정의를 못 받아 라우팅이 깨진다). 한쪽을 수정하면 나머지도 함께 갱신해 어긋나지 않게 한다.
> 이 중 기계 검증 가능한 불변식(refactor 금지 목록 3파일 일치, green 재호출 상한, 프로젝트 루트 전달, verify 판별식 키, 디스패치 이름↔agents/ 대조)은 `scripts/lint-consistency.sh`가 CI(`.github/workflows/lint.yml`)에서 자동 검사한다. 나머지는 여전히 수동 동기화 대상이다.
> - **디스패치 프롬프트**(red-writer/green-coder/refactor-coder): phase-implement.md(Step 2-R/G/F)와 각 보조 스킬(gx-red/gx-green/gx-refactor) SKILL.md에 정의. phase-review Step 4b의 refactor-coder 호출은 Step 2-F를 **포인터 참조**하므로 2-F만 고치면 따라온다.
> - **마커 분류**(`[동작결함]`/`[동작불변]`): `agents/quality-reviewer.md`가 SSOT이며, phase-review의 Task A 프롬프트·Step 4.4 의사코드에 라우팅 강제를 위해 재명시된다.
> - **spec 기계 판정 블록**(`spec_verdict` YAML): `agents/spec-reviewer.md`가 SSOT이며 phase-review Step 2 프롬프트에 재명시, Step 2.1이 소비(블록 우선 → 산문 폴백 → 상충 시 FAIL). 린트가 producer-consumer 쌍 존재를 검사.
> - **테스트 무결성 규칙**("테스트 파일 수정 금지" + "테스트 결함 의심" 보고 필드): `agents/green-coder.md` ↔ phase-implement.md(Step 2-G, verify_red/verify_green) ↔ gx-green SKILL.md(Step 1~3)에 중복.
> - **테스트 품질 가드**(anti-pattern 요약 + Good Tests 3기준): `agents/red-writer.md` ↔ phase-implement.md(Step 2-R) ↔ gx-red SKILL.md(Step 2)에 중복. 상세 기준의 SSOT는 `references/testing-anti-patterns.md`.
> - **참조 파일 자기신고 + 격리 오염 검증**: `agents/red-writer.md`(출력 형식) ↔ phase-implement.md(Step 2-R 출력·verify_red) ↔ gx-red SKILL.md(Step 2 출력·Step 3)에 중복.
> - **경고 측정 규약**: `gx-verify` SKILL.md Step 2가 SSOT. phase-implement Step 0.5(baseline 기록)는 포인터 참조만 하므로 gx-verify만 고치면 따라온다.
> - **verify 경고 게이트 조건**(`pipeline`/`verify-status` 판별): `.claude/rules/skill-routing.md` ↔ gx-commit SKILL.md ↔ gx-pull-request SKILL.md에 중복. 판별 키의 SSOT는 이 파일의 state.md 스키마.
> - **review 진입 '변경 없음' 판정**: 이 파일(실행 루프 2a) ↔ gx-dev SKILL.md에 쌍둥이 — 한쪽 보수 시 함께 갱신.
> - **프로젝트 타입 폴백 표**: SSOT는 `.claude/config.json`의 projectTypes. gx-verify Step 1과 gx-tdd/gx-dev phase-review의 표는 파생 사본.
> - **state.md 초기화 필드**: phase-setup Step 7이 정본이며, `--phase` 부트스트랩 골격(환경 감지 5항)은 그 부분집합 사본.
> - **무결성 기준선 규약**(`rgr-t{N}-porcelain.txt`·`test-file-hash`·`test-count`): phase-implement.md(verify_red/green/refactor) ↔ 이 파일(state.md 스키마·--resume 규칙)에 중복. 단독 gx-green SKILL.md는 해시 단독 비교의 **의도적 경량판**(스냅샷·카운트 없음).
> - **"수동 수정 재주입" 기록 문구**: phase-review(2곳)·phase-complete(Step -1)에 산재 — 문구 변경 시 함께 동기화.

## 인자

`ARGS[0]`에 자연어 요청을 받는다. 레거시 플래그도 호환한다.

### 의도 파싱

ARGS[0]을 받으면 아래 순서로 의도를 파싱한다:

**Step 1: 레거시 플래그 호환** (기존 사용자 보호)
- `--hotfix`, `--phase`, `--base`, `--status`, `--resume`이 포함되면 기존 로직 그대로 실행.
- 플래그가 없으면 Step 2로 진행.

**Step 2: 자연어 → 모드 판정**

먼저 아래 패턴으로 자동 판정을 시도한다:

| 감지 패턴 | 모드 | 예시 |
|-----------|------|------|
| `상태`, `진행`, `어디까지`, `현황` | STATUS | "지금 어디까지 됐어?" |
| `이어서`, `계속`, `재개`, `아까 하던` | RESUME | "아까 하던 작업 이어서 해줘" |
| `긴급`, `핫픽스`, `급한`, `빨리 고쳐`, `버그 수정만` | HOTFIX | "로그인 버그 긴급 수정해줘" |
| `설계만`, `PRD만`, `구현만`, `리뷰만`, `커밋만` | PHASE(해당) | "설계만 해줘" |
| `{branch}에서`, `{branch} 기반`, `{branch} 브랜치` | BASE 추출 | "develop 브랜치 기반으로 작업해줘" |

PHASE 매핑: `PRD만`/`요구사항만` → `--phase requirements`, `설계만` → `--phase design`, `구현만` → `--phase implement`, `리뷰만` → `--phase review`, `커밋만`/`PR만` → `--phase complete`.

BASE 추출: `{branch}에서`, `{branch} 기반`, `{branch} 브랜치`에서 branch명을 추출하여 `--base`로 처리한다. BASE 추출은 모드 판정과 독립적이다 — BASE가 추출되어도 모드가 결정되지 않으면 Step 3으로 진행한다.

**Step 3: 모드 확인 (위 패턴에 해당하지 않는 경우)**

위 자동 판정 패턴에서 모드(STATUS/RESUME/HOTFIX/PHASE)가 결정되지 않으면 — 즉, 일반적인 기능 요청이면 — **반드시** AskUserQuestion으로 모드를 확인한다. 오케스트레이터가 임의로 모드를 판정하지 않는다.

```
AskUserQuestion(
  questions: [{
    question: "어떤 방식으로 진행할까요? (요청: {ARGS[0]})",
    header: "진행 방식",
    options: [
      { label: "전체 파이프라인", description: "PRD → 설계 → RED-GREEN-REFACTOR → 리뷰 → verify → PR" },
      { label: "긴급 수정", description: "경량 PRD → RGR → verify → PR (design/정식 review 생략, RGR·verify는 유지)" }
    ],
    multiSelect: false
  }]
)
```

- "전체 파이프라인" 선택 → NORMAL 모드 (전체 Phase 실행)
- "긴급 수정" 선택 → HOTFIX 모드

> **gx-dev와 달리 "구현만"(설계·테스트 없이 바로 구현) 경량 모드는 제공하지 않는다.** TDD 파이프라인의 Iron Law 1(실패 테스트 우선)과 정면 충돌하기 때문이다. 설계를 건너뛰고 빠르게 진행하려면 "긴급 수정"(hotfix: 경량 PRD + RGR + verify)을 사용하고, 테스트 강제 없이 즉시 구현하려면 `oh-my-gx:gx-dev`를 사용한다.

### 모드 판정 결과 기록

의도 파싱 결과를 state.md에 기록한다:
```yaml
mode: normal | hotfix
intent-source: flag | natural-language | user-selection
```

### 레거시 플래그 참조 (호환용)

- `--phase requirements|design|implement|review|complete`: 특정 Phase만 실행
- `--hotfix`: 긴급 버그 수정용 경량 경로
- `--base <branch>`: 베이스 브랜치 지정
- `--status`: 현재 파이프라인 진행 상태 조회
- `--resume`: 이전 파이프라인 재개

ARGS[0]이 없고 모드도 판정되지 않으면 다음을 응답:
"구현할 기능이나 수정할 버그를 설명해주세요. 예: `/gx-tdd 로그인 기능 추가해줘`"

### --status 동작
`--status`가 지정되면 파이프라인을 실행하지 않고 현재 상태만 출력한다:

1. 현재 브랜치명에서 DEV_DIR을 계산하고 (`git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/`), `${DEV_DIR}/state.md`를 탐색한다.
2. state.md가 없으면: "진행 중인 파이프라인이 없습니다." 출력 후 종료.
3. state.md가 있으면 다음을 출력:
   ```
   ## 파이프라인 상태
   - 작업: {args}
   - 브랜치: {branch} (base: {base})
   - 프로젝트: {project-type} ({project-root})
   - 현재 Phase: {phase} ({status})
   - 플래그: {flags}
   - 시작: {started}

   ### Phase 진행
   - setup: {status}
   - requirements: {status}
   - ...
   ```
4. 출력 후 종료. 파이프라인을 시작하지 않는다.

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
| **spec-reviewer** | **AC 충족만 검증 (신규)** | **"스펙대로 됐나" — 코드 품질 무시** | **sonnet** |
| **quality-reviewer** | **코드 품질만 검증 (신규)** | **"잘 짜였나" — AC 무시** | **opus** |
| security-auditor | 정책/보안/허점 감사 | "뭘 놓쳤나" | sonnet |
| ~~qa-manager~~ | (deprecated — spec-reviewer + quality-reviewer로 분해) | — | — |

### EXECUTION (RED-GREEN-REFACTOR 순차; red-writer만 코드 격리)
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| **red-writer** | **실패 테스트 작성 전담 (신규)** | **"테스트만 작성" — 프로덕션 코드 안 봄** | **sonnet** |
| **green-coder** | **통과 최소 코드 (신규)** | **"YAGNI" — 테스트만 통과시킴** | **sonnet** |
| **refactor-coder** | **안전한 정리 (신규)** | **"동작 변경 금지" — GREEN 유지** | **sonnet** |
| ~~coder~~ | (deprecated — red-writer/green-coder/refactor-coder로 분해) | — | — |

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

### Deprecated 에이전트 처리

- `qa-manager`, `coder`는 기존(gx-dev) 호환을 위해 디렉토리에 남아있으나 oh-my-gx:gx-tdd에서는 **호출하지 않는다**.
- 자기점검은 spec-reviewer가 대체한다.
- 구현은 red-writer/green-coder/refactor-coder가 분담한다.

## Phase 개요 (TDD 강제)

| Phase | 파일 | 주 Agent | TDD 강제 사항 | Q&A Loop |
|-------|------|----------|--------------|----------|
| setup | phase-setup.md | (inline) | — | No |
| requirements | phase-requirements.md | product-owner | **AC = Given-When-Then 강제** (G-W-T 게이트 — 오케스트레이터 직접 검증) | Yes (max 1) |
| design | phase-design.md | architect + design-critic + **test-architect** | **testability score ≥ 7 필수** (미충족 시 재설계) | Yes (max 2) |
| implement | phase-implement.md | **red-writer → green-coder → refactor-coder (순차; red-writer만 코드 격리)** | **Iron Law 1**: 실패 테스트 없이 코드 작성 금지 | RGR 사이클 |
| review | phase-review.md | **spec-reviewer → quality-reviewer (순차 강제)** + security-auditor (quality와 병렬) | **Iron Law**: spec 통과 못 하면 quality 진입 금지 | Yes (max 2) |
| complete | phase-complete.md | **gx-verify(스킬)** → product-owner (인수) → commit/PR | **Iron Law 3**: verify 게이트 통과 필수 (테스트 실행 증거) | 인수 재시도 (max 1) |

**핵심 차별점 (gx-dev 대비)**:
- requirements/design에 **사전 게이트** (G-W-T, testability)
- implement는 단일 coder가 아니라 **3 에이전트 순차 사이클** (red-writer만 기존 코드 격리; green/refactor는 입력 범위만 제한)
- review는 병렬이 아니라 **spec → quality 순차** (spec 우선)
- complete는 **gx-verify 스킬 우선 호출** (verify 통과 없이 commit 진입 금지)

### Hotfix 경로 (`--hotfix`)

긴급 버그 수정용 경량 경로. 설계/리뷰를 건너뛰지만, **경량 PRD + RGR 사이클 + verify 게이트 + 긴급 보안 감사 + 인수 검증은 실행**한다:
```
--hotfix: setup → requirements (경량+G-W-T) → implement (RGR + H1~H4 긴급감사) → complete (verify + 인수)
정상:     setup → requirements → design → implement (RGR) → review (spec→quality+security) → complete (verify + 인수 + commit + PR)
```
- **requirements**: product-owner가 소형 PRD 작성 (배경 + 요구사항 + 수용 기준만). **AC는 G-W-T 형식 강제 유지** (RGR 사이클이 hotfix에서도 강제되므로).
- **design**: 건너뛴다. RGR 사이클이 PRD + 코드 맵을 기반으로 진행 (testability 평가 없이).
- **implement**: 정상 모드와 동일하게 RGR 사이클 수행. 단, design.md 부재로 red-writer/green-coder에 PRD만 전달. 사이클 종료 후 H1~H4 (긴급 보안 감사: CRITICAL/HIGH만) 실행.
- **review**: 건너뛴다 (긴급 보안 감사가 H1~H4에서 대체).
- **complete**: verify 게이트 → 인수 검증 → commit → PR. 정상 모드와 동일.

**Iron Law 유지 (hotfix여도)**:
- Iron Law 1 (실패 테스트 우선): RGR 사이클이 hotfix에서도 강제됨
- Iron Law 3 (verify 게이트): complete의 Step -1에서 강제됨
- 우회 가능한 것은 design Phase (testability 평가)뿐

## Phase 라우팅 — 필수 실행 프로토콜

> **CRITICAL: Phase 스킵 절대 금지.**
> "요구사항이 명확하다", "범위가 작다", "이미 확정되어 있다", "간단하다" 등 어떤 이유로도 Phase를 건너뛰지 않는다.
> Phase를 건너뛸 수 있는 유일한 조건은 `--hotfix` 모드와 `--phase` 플래그뿐이다.
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
if hotfix:
    PHASES = [setup, requirements, implement, complete]
elif --phase 지정:
    PHASES = [해당 phase만] (SKILL.md "Phase 선택" 섹션 참조)
else:  # NORMAL
    PHASES = [setup, requirements, design, implement, review, complete]

# 2. Phase별 순차 실행 (건너뛰기 금지)
for phase in PHASES:

    # 2a. 산출물 게이트 — 이전 Phase 산출물이 없으면 이전 Phase부터 실행 (순서 중요: 상위 의존성 먼저 체크)
    if phase == "design" and not exists("${DEV_DIR}/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and not exists("${DEV_DIR}/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and not hotfix and not exists("${DEV_DIR}/design.md"):
        → phase-design부터 실행

    # 2a-1. testability 게이트 (Iron Law) — design.md에 testability 섹션 필수
    if phase == "implement" and not hotfix:
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
    Read("<프로젝트 루트>/.claude/skills/gx-tdd/phases/phase-{phase}.md")

    # 2c. Phase 파일의 지시에 따라 실행

    # 2d. state.md 갱신
    Update state.md → phases.{phase}: completed

    # 2e. 다음 Phase로 진행
```

### Phase 파일 경로

`phase-setup.md`, `phase-requirements.md`, `phase-design.md`, `phase-implement.md`, `phase-review.md`, `phase-complete.md`

### Agent 팀 강제

Phase 실행 시 반드시 이 스킬에 정의된 Agent 팀(product-owner, architect, test-architect, design-critic, red-writer, green-coder, refactor-coder, spec-reviewer, quality-reviewer, security-auditor, researcher, hacker, simplifier)을 사용한다. (완료 검증은 별도 에이전트가 아니라 `oh-my-gx:gx-verify` 스킬이 담당한다.)

**디스패치 이름 규칙**: `Task` 호출 시 `subagent_type`은 `oh-my-gx:` 접두사를 포함한 정식 이름을 사용한다 (예: `oh-my-gx:red-writer`). 플러그인 설치 환경에서 에이전트는 접두사형으로 등록되므로 bare 이름은 해석되지 않을 수 있다.

**Iron Law**: 다음 에이전트는 oh-my-gx:gx-tdd에서 **절대 호출하지 않는다** (deprecated):
- `coder` — red-writer/green-coder/refactor-coder로 분해됨
- `qa-manager` — spec-reviewer/quality-reviewer로 분해됨

외부 Agent(sisyphus-junior, sisyphus-junior-high 등)로 대체하지 않는다.

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

감사 결과와 위험 수용 이력을 누적하는 문서. security-auditor 감사, quality-reviewer Critical/Important 요약, 각 게이트의 위험 수용 항목을 기록한다. 오케스트레이터가 관리한다.

**위험 수용 기록 규약**: 파이프라인의 모든 위험 수용(테스트 미검증 리뷰, 미해결 Critical 수용, TDD 미이행 완료 실행, 신규 경고 수용, G-W-T 제외, hotfix 감사 수용 등)은 `### 위험 수용` 섹션에 `- [{항목명}] {사유} ({phase/step})` 형식으로 기록한다. Write 권한이 없는 스킬(gx-verify)은 보고만 하고 **오케스트레이터가 기록**한다.

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
- 정상 모드: phase-review Step 3의 security-auditor 통합 감사 완료 시 생성.
- hotfix 모드: phase-implement Step H1~H4의 긴급 보안 감사 완료 시 생성 (`### Hotfix 긴급 감사` 섹션).
- 후속 review 반복마다 갱신/append.

**저장**: `${DEV_DIR}/trust-ledger.md`에 저장한다.
**전달**: PR 본문(`pr-context.md` 조립 시)에 감사 결과 요약으로 포함한다.

---

## 공유 규칙

### 작업 경로 기준
phase-setup에서 결정된 변수를 이후 모든 Phase에서 사용한다:
- `VCS_TYPE`: `.claude/config.json`의 `"vcs"` 값. `"git"`, `"svn"`, 또는 `""` (미설정, `"git"`으로 취급). phase-setup에서 읽어 이후 모든 Phase에서 사용한다. VCS별 명령어 분기의 기준이 된다.
- `GIT_PREFIX`: `VCS_TYPE`이 `"git"`이면 `git`, `"svn"`이면 `svn`. 소비 프로젝트 루트에서 직접 실행한다.
- `PROJECT_ROOT`: 항상 `./` (현재 디렉토리).
- `DEV_DIR`: 브랜치별 dev 산출물 디렉토리. `.dev/{branch-slug}/` 형식. branch-slug는 브랜치명의 `/`를 `-`로 치환한 값이다 (예: `feat/login` → `.dev/feat-login/`). phase-setup Step 6.5에서 브랜치 생성/전환 후 결정된다. **SVN은 브랜치가 없으므로 `.dev/trunk/`를 사용한다.**
- `BASE_BRANCH`: phase-setup Step 2에서 결정된 베이스 브랜치 (예: `main`, `develop`). SVN인 경우 미사용.
- `DIFF_FILE`: 변경사항 diff를 저장하는 파일 경로. `${DEV_DIR}/diff.txt`. Diff 수집 규칙에 따라 phase-implement(자기점검), phase-review, phase-complete에서 갱신된다.
- `DOMAIN_CONTEXT`: phase-setup 0.3에서 `context/*/PROJECTS.md` 매칭으로 로드된 도메인 용어(glossary)와 아키텍처 정보. 매칭되지 않으면 빈 상태.
- `REFERENCES`: phase-setup Step 3.1(병렬 수집)의 외부 규격 참조 항목에서 `references/` 디렉토리를 탐색하여 수집한 외부 규격 문서 목록(파일 경로 + 한줄 설명). `references/` 디렉토리가 없으면 빈 상태. 빈 상태이면 에이전트 프롬프트에 포함하지 않는다.
- Agent에게 `PROJECT_ROOT` 경로를 항상 전달하여 파일 도구(Read/Write/Edit/Glob/Grep)의 기준점으로 사용하게 한다.
- 빌드/테스트 명령(`./gradlew`, `npm`, `pytest` 등)을 `PROJECT_ROOT`에서 실행한다. `PROJECT_ROOT`가 기본값 `./`이면 **bare 명령**으로 실행한다 (예: `npm test`, `./gradlew build`) — `allowed-tools`의 prefix 패턴(`Bash(npm *)` 등)과 매칭되어 권한 프롬프트가 뜨지 않는다. `PROJECT_ROOT`가 `./`가 아닌 경우에만 작업 디렉토리 보존을 위해 서브셸 `(cd ${PROJECT_ROOT} && <cmd>)`로 감싼다 — 단 이 서브셸 형태는 `(cd`로 시작하여 prefix 패턴과 매칭되지 않으므로 권한 프롬프트가 뜰 수 있다 (gradle 포함 모든 명령에 적용되는 기존 한계).

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
Agent 출력을 사용자에게 전달할 때, **Phase 상태에 따라** 전문 표시 여부를 결정한다:
- **Q&A Phase** (requirements, design): Agent 출력의 첫 표시는 항상 **전문 표시**한다 (사용자가 산출물을 검토할 수 있도록). Phase 파일의 구체적인 표시 규칙이 이 일반 규칙보다 우선한다.
- **Q&A Phase 완료 보고**: 확정된 산출물을 파일에 저장하고, 사용자에게는 **요약만** 보고한다 ("PRD 확정. ${DEV_DIR}/prd.md에 저장됨" 등).
- **Q&A 없는 Phase** (implement, review, complete): Agent 출력의 **요약만** 사용자에게 표시한다. 전문은 파일에 저장하거나 변수에 보관한다.

이후 Phase에서 이전 산출물이 필요하면 **파일을 Read하여 Agent prompt에 포함**하되, 오케스트레이터 자신의 출력에는 포함하지 않는다. 각 Phase 파일에서 구체적인 요약 포맷을 정의한다.

### 문서 보관
- phase-requirements 완료 시 확정된 PRD를 `${DEV_DIR}/prd.md`에 저장한다.
- phase-design 완료 시 확정된 설계 문서를 `${DEV_DIR}/design.md`에 저장한다.
- Trust Ledger를 `${DEV_DIR}/trust-ledger.md`에 저장한다.
- 코드 맵을 `${DEV_DIR}/codemap.md`에 저장한다 (갱신 시마다).
- phase-design, phase-implement, phase-review 진입 시 해당 파일들을 Read하여 에이전트 프롬프트에 사용한다.
- `.gitignore` 보강은 phase-setup의 Step 0.5a에서 프로젝트 타입별로 처리한다 (`.dev/` 패턴 — 브랜치별 하위 폴더 전체 포함).

### 진행 상태 추적 (state.md)
파이프라인 진행 상태를 `${DEV_DIR}/state.md`에 기록하여 세션 재개를 지원한다.

**state.md 구조 (RGR 사이클 반영)**:
```yaml
phase: implement
status: in_progress
pipeline: gx-tdd           # 파이프라인 식별자 — verify-status와 함께 커밋/PR 게이트(skill-routing·gx-commit·gx-pull-request)의 판별 키
verify-status: pending     # pending | passed. phase-complete Step -1 verify 통과 시 passed 전이, 코드 변경 재진입 시 pending 리셋
vcs-type: git
branch: JIRA-123
base: main
project-type: java-spring
project-root: ./
args: "[JIRA-123] 로그인 기능 추가"
flags: --hotfix
started: 2026-02-17T10:30:00
last-known-head: 7c9e814abc...
config-setup-attempts: 1   # phase-setup 3.0 가드의 재시도 카운터
warnings-baseline: 12      # phase-implement Step 0.5 기준선 게이트가 기록. gx-verify가 신규 경고 판정 기준으로 사용
current-step: "RGR T1: GREEN"
phases:
  setup: completed
  requirements: completed       # G-W-T 게이트 통과
  design: completed             # testability score 8/10 통과
  implement: in_progress
steps:
  implement:
    - 태스크 분해 승인: completed
    - "RGR T1 (AC-1)":
        red: completed
        test-file-hash: 3ca970cc...   # verify_red 기록 — verify_green 무결성 비교 기준선
        test-count: 47                # verify_green 기록 — verify_refactor 테스트 삭제 감지 기준선
        green: in_progress
        refactor: pending
    - "RGR T2 (AC-2)": pending
    - 변경사항 수집: pending
  review:
    - mechanical-gate: pending
    - spec-review (1단계): pending
    - quality-review + security (2단계 병렬): pending
  complete:
    - verify-gate: pending
    - 인수검증: pending
execution-log:
  - phase: requirements
    gate: G-W-T
    result: "PASS — 모든 AC가 Given-When-Then 형식"
  - phase: design
    agent: test-architect
    result: "testability score 8/10 PASS"
  - phase: implement
    agent: red-writer (T1)
    result: "PasswordValidatorTest.shouldReject401 작성 + 실패 확인"
  - phase: implement
    agent: green-coder (T1)
    result: "in_progress"
```

**갱신 규칙:**
- Phase 진입 시: `phase: {name}`, `phases.{name}: in_progress`로 갱신.
- Phase 완료 시: `phases.{name}: completed`로 갱신한다. **git인 경우** `last-known-head`를 현재 `git rev-parse HEAD`로 갱신한다 (svn은 미사용).
- Phase 내 주요 Step 시작/완료 시: `current-step`과 `steps` 갱신.
- **RGR 사이클**: 각 태스크의 red/green/refactor 단계를 `"RGR T{N} (AC-N)"` 형식의 중첩 객체로 추적한다. (옛 "coder 구현/자기점검" 형식 사용 금지)
- **G-W-T / testability 게이트 결과**: `execution-log`에 `gate: G-W-T` 또는 `agent: test-architect` 엔트리로 기록.
- **verify 게이트 결과**: complete Step -1의 verify 게이트 결과를 `execution-log`에 기록 (gx-commit은 gx-dev와 공유하는 스킬이라 verify 실행을 포함하지 않는다 — 조건부 경고 게이트만 있음). verify가 "위험 수용"으로 통과를 보고하면 오케스트레이터가 trust-ledger에도 기록한다.
- **verify-status 전이**: phase-complete Step -1 verify 통과 시 최상위 `verify-status: passed`로 갱신한다. 이후 코드 변경으로 phase-complete를 재진입하면 `pending`으로 리셋 후 Step -1을 재실행한다. 새 파이프라인 시작·부트스트랩 시 초기값은 `pending`.
- **기준선 게이트 결과**: phase-implement Step 0.5에서 최상위 필드 `warnings-baseline: N`을 기록한다. 추출 불가 시 기록하지 않고 execution-log에 "경고 비교 미수행"을 명시한다.
- `--resume` 시 `current-step`에서 재개한다 (Phase 처음부터가 아닌 중단 Step부터). 재개 전에 phase-setup Step 0.1 정합성 체크(브랜치/HEAD)를 수행한다. RGR 사이클 재개 시 `red/green/refactor` 단계별로 매칭 (태스크의 `test-file-hash`·`test-count`와 `${DEV_DIR}/rgr-t{N}-porcelain.txt` 스냅샷 파일을 함께 사용하여 verify_green/verify_refactor 기준선을 유지).
- 에이전트 호출 완료 시: `execution-log`에 엔트리 추가 (agent명, result 요약). deprecated 에이전트(coder/qa-manager)는 절대 기록되지 않는다.
- Gate 실행 결과도 `execution-log`에 기록한다 (mechanical-gate, G-W-T, testability, verify, spec-review, quality-review).
- 정체 감지 시: 해당 `execution-log` 엔트리에 `stagnation: {패턴}` 필드를 추가한다.
- phase-complete 완료 시: `status: completed`로 갱신.
- 새 파이프라인 시작 시 기존 state.md를 덮어쓴다. `config-setup-attempts`도 0으로 초기화.

### Context Slicing 규칙
설계서와 PRD를 Agent에게 전달할 때, 역할에 따라 필요한 섹션만 전달하여 컨텍스트 효율을 높인다.

#### PRODUCT
- **product-owner (PRD 작성)**: ARGS[0] + 코드 맵 + 프로젝트 타입/구조 + 프로젝트 루트 경로 + DOMAIN_CONTEXT (있으면) + **"AC는 반드시 Given-When-Then 형식. 자동 테스트로 변환 가능해야 함"** 지시
- **product-owner (인수 검증)**: PRD의 "요구사항" + "수용 기준" + diff 파일 경로 (`DIFF_FILE`) + 코드 맵

#### PLANNING
- **architect (설계)**: PRD 전체 + 코드 맵 + 프로젝트 타입/구조/컨벤션 + 프로젝트 루트 경로 + DOMAIN_CONTEXT (있으면) + REFERENCES (있으면) + **"각 컴포넌트의 테스트 가능성(의존성 주입, 인터페이스 격리)을 고려"** 지시
- **design-critic (설계 비판)**: 설계서 초안 + PRD + 코드 맵 + 프로젝트 루트 경로
- **test-architect (testability 평가)** ← 신규: 설계서 + PRD의 "수용 기준" + 코드 맵 + 프로젝트 루트 경로 + **"각 컴포넌트별 단위/통합 테스트 전략 명시 + testability score 1-10 산정"** 지시

#### EXECUTION (RED-GREEN-REFACTOR 순차; red-writer만 코드 격리)
- **red-writer (RED)** ← 신규: AC (Given-When-Then 시나리오) + 설계서의 testability 섹션 + 기존 테스트 스타일 + 프로젝트 루트 경로. **기존 프로덕션 코드는 절대 포함하지 않는다** (격리 — 위반 여부는 verify_red가 "참조한 파일" 자기신고로 검증). "테스트만 작성. 프로덕션 코드 작성 금지" 지시.
- **green-coder (GREEN)** ← 신규: 실패 테스트 (파일/코드/에러 메시지) + 설계서 인터페이스 + 프로젝트 루트 경로. **PRD 전체나 설계서 전체는 전달하지 않는다** (입력 범위 제한 — red-writer 수준의 코드 차단이 아니다. green-coder는 구현을 위해 기존 코드를 Read할 수 있으며, 다만 전체 문서 대신 대상 시그니처만 전달받는다). "테스트만 통과시키는 최소 코드. 과잉 구현 금지" 지시.
- **refactor-coder (REFACTOR)** ← 신규: 정리 대상 파일 목록 + 정리 항목 (중복/네이밍/구조) + 프로젝트 루트 경로. "GREEN 유지하며 정리만. 동작 변경 금지" 지시.

#### Deprecated (oh-my-gx:gx-tdd에서 절대 호출 안 함)
- ~~coder (구현/배치/수정)~~ → red-writer/green-coder/refactor-coder로 분해됨
- ~~qa-manager (리뷰/자기점검)~~ → spec-reviewer/quality-reviewer로 분해됨
- 위 에이전트의 Context Slicing 정의는 기존(gx-dev) 호환을 위해 디렉토리에 파일은 남아있으나 gx-tdd 파이프라인에서는 참조하지 않는다.

#### REVIEW (2단계 순차)
- **spec-reviewer (1단계)** ← 신규: PRD의 "요구사항" + "수용 기준" + 설계서의 "변경 범위" + diff 파일 경로 (`DIFF_FILE`) + 코드 맵. **"AC 충족만 검증. 코드 품질은 평가 금지"** 지시.
- **quality-reviewer (2단계, spec 통과 후만)** ← 신규: diff 파일 경로 (`DIFF_FILE`) + 코드 맵 + 프로젝트 컨벤션. **PRD/AC는 전달하지 않는다** (격리). **"코드 품질만. AC 충족 여부 평가 금지"** 지시.
- **security-auditor (통합 감사, quality와 병렬)**: PRD 전체 + 설계서 전체 + diff 파일 경로 (`DIFF_FILE`) + 코드 맵 + REFERENCES (있으면)

#### VERIFICATION
- **gx-verify (스킬, 완료 게이트)**: phase-complete Step -1에서 `Skill("oh-my-gx:gx-verify")`로 호출. config.json의 projectTypes 기반으로 테스트/빌드 명령을 직접 실행. 캐시 결과 사용 금지, 0 failures 확인. 에이전트 Task가 아니므로 Context Slicing(입력 전달) 대상이 아니다.

#### ANALYSIS / RECOVERY
- **researcher (독립 조사)**: 조사 요청 + 코드 맵 (있으면) + 프로젝트 루트 경로
- **hacker (제약 우회)**: 정체 상황 설명 (에러 메시지, 시도한 접근) + 코드 맵 + 프로젝트 루트 경로
- **simplifier (복잡도 제거)**: 정체 상황 설명 + 설계서 + PRD + 코드 맵

각 에이전트에 전달하는 입력 크기가 `.claude/config.json`의 `contextLimits`를 초과하면, 우선순위가 낮은 섹션부터 요약 또는 생략한다.

### 병렬 실행 규칙
읽기 전용 Agent(product-owner, architect, test-architect, design-critic, spec-reviewer, quality-reviewer, security-auditor, researcher, hacker, simplifier)는 서로 병렬 실행이 가능하다. 병렬 실행 시:
1. 하나의 메시지에서 여러 `Task()` 호출을 동시에 발행한다.
2. 모든 병렬 Task가 완료된 후 결과를 합산한다 (Gate 로직).
3. 쓰기 Agent(red-writer, green-coder, refactor-coder)는 다른 쓰기 Agent와 병렬 실행하지 **않는다**.
4. **RGR 사이클 내 순차 강제 (Iron Law)**: red-writer → green-coder → refactor-coder는 **반드시 순차** 실행한다. 병렬 금지.
   - 이유: red-writer 산출물(실패 테스트)이 green-coder의 입력. green-coder 산출물(통과 코드)이 refactor-coder의 입력.
   - 위반 시: 격리가 깨져 Iron Law 1 위반.
5. **review 2단계 순차 강제 (Iron Law)**: spec-reviewer → quality-reviewer는 **반드시 순차**. spec 통과 후에만 quality 진입.
   - security-auditor는 quality-reviewer와 **병렬 가능** (서로 독립).
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

1. `DIFF_FILE = ${DEV_DIR}/diff.txt`. **매 수집 시** `mkdir -p ${DEV_DIR}`를 실행하여 디렉토리 존재를 보장한다.
2. diff를 파일에 직접 리다이렉트한다 (Bash 결과에 diff가 나타나지 않음):
   ```bash
   git diff --cached > ${DEV_DIR}/diff.txt
   ```
3. `wc -l < ${DEV_DIR}/diff.txt`로 줄 수를 확인한다.
4. 총 변경이 **500줄 이상**이면: `--stat` 요약을 파일 앞에 추가하고, 파일 끝에 "변경된 파일을 Read 도구로 직접 확인하라"는 안내를 추가한다:
   ```bash
   git diff --cached --stat > ${DEV_DIR}/diff.txt
   echo "---" >> ${DEV_DIR}/diff.txt
   echo "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라." >> ${DEV_DIR}/diff.txt
   ```
5. Agent 프롬프트에는 **파일 경로만 전달**한다:
   ```
   변경사항 diff: ${DEV_DIR}/diff.txt
   이 파일을 Read하여 변경사항을 확인하라.
   ```

이 규칙은 모든 diff 패턴에 적용한다: `git diff --cached` (스테이징), `git diff <base>...HEAD` (브랜치 비교) 등. 브랜치 비교 시에는 해당 diff 명령으로 리다이렉트한다.

### 에이전트 질문 → AskUserQuestion 변환 규칙

에이전트(product-owner, architect, test-architect, spec-reviewer, quality-reviewer, security-auditor)가 "확인이 필요한 사항"에 구조화된 질문을 출력하면, 오케스트레이터가 AskUserQuestion으로 변환하여 사용자에게 제시한다.

#### 변환 프로세스

1. 에이전트 출력에서 "확인이 필요한 사항" 섹션을 파싱한다.
2. "추가 확인 사항 없음"이 포함되면 질문 변환을 건너뛴다.
3. 각 질문의 `유형` 필드에 따라 변환한다:

**유형: 선택** → AskUserQuestion 선택형:
```
AskUserQuestion(
  questions: [{
    question: "질문 텍스트 (맥락이 있으면 질문에 포함)",
    header: "카테고리",
    options: [
      { label: "레이블", description: "설명" },
      { label: "레이블", description: "설명" }
    ],
    multiSelect: false
  }]
)
```

**유형: 자유입력** → 예상 답변 후보 2개를 options에 배치하고, 해당하지 않으면 "Other"로 직접 입력:
```
AskUserQuestion(
  questions: [{
    question: "질문 텍스트 (맥락이 있으면 질문에 포함)",
    header: "카테고리",
    options: [
      { label: "예상 답변 A", description: "설명" },
      { label: "예상 답변 B", description: "설명" }
    ],
    multiSelect: false
  }]
)
```

#### 변환 규칙

- **questions 배열 필수**: 최상위에 반드시 `questions: [{ ... }]` 배열로 감싸고, `header`(최대 12자)와 `multiSelect`(기본 false)를 지정한다.
- **options는 `{ label, description }` 구조**이며 구버전 `value` 필드는 없다. "Other"(직접 입력)는 UI가 자동 제공하므로 별도 옵션을 만들지 않는다.
- **(권장)** 표시가 있는 선택지는 options 첫 번째에 배치하고 label 끝에 `(Recommended)`를 추가한다.
- 질문이 **2개 이상**이면 순서대로 하나씩 AskUserQuestion을 호출한다. 이전 답변이 다음 질문의 맥락에 영향을 주면 반영한다.
- 에이전트가 기술 용어를 사용한 경우 **비기술적 표현으로 의역**한다. 예: "JWT vs 세션" → "로그인 유지 방식".
- 복수 선택이 필요하면 `multiSelect: true`로 지정한다.

#### 승인/수정 공통 패턴

산출물(PRD, 설계서, 구현 계획) 확인 시 공통으로 사용하는 AskUserQuestion 패턴:
```
AskUserQuestion(
  questions: [{
    question: "{산출물}을 확인해주세요.",
    header: "산출물 확인",
    options: [
      { label: "승인", description: "다음 단계로 진행" },
      { label: "수정 요청", description: "Other로 이동해서 수정할 사항을 자연어로 입력해주세요" }
    ],
    multiSelect: false
  }]
)
```
사용자가 "수정 요청"을 선택하면 후속 AskUserQuestion(자유입력)으로 수정 내용을 받는다.

---

## 플래그 충돌 검증

- `--hotfix`와 `--phase`는 **동시 사용 불가**. 둘 다 있으면: "`--hotfix`와 `--phase`는 동시에 사용할 수 없습니다." 에러 후 중단.
- `--resume`과 `--phase`, `--hotfix`, `--status`는 **동시 사용 불가**. 함께 있으면: "`--resume`은 다른 모드 플래그와 동시에 사용할 수 없습니다." 에러 후 중단.
- `--resume`은 ARGS[0] 없이 단독 사용한다. ARGS[0]이 함께 있으면: "`--resume`은 작업 설명 없이 단독으로 사용합니다." 에러 후 중단.

## Phase 선택 (--phase 플래그)

`--phase`가 지정되면 해당 Phase만 실행한다:
- `--phase requirements`: setup (필요 시) + requirements만 실행 (PRD 작성).
- `--phase design`: setup (필요 시) + requirements + design만 실행. 대화 맥락에 요구사항이 없고 `${DEV_DIR}/prd.md`도 없으면 requirements부터 시작.
- `--phase implement`: 환경 감지 + implement 실행. 대화 맥락에 설계서가 없고 `${DEV_DIR}/design.md`도 없으면: "설계서가 필요합니다. `/gx-tdd --phase design`을 먼저 실행하거나 설계 내용을 입력해주세요." 후 중단.
- `--phase review`: 환경 감지 + 베이스 브랜치 감지 + review 실행 (현재 변경사항을 리뷰). **단독 실행은 리뷰 결과 보고로 종료하며 phase-complete로 체이닝하지 않는다** (완료 절차는 `--phase complete`로 별도 실행). 종료 시 부트스트랩 골격 state.md라면 `status: completed`로 갱신한다 (영구 in_progress 잔존 방지).
- `--phase complete`: 환경 감지 + 베이스 브랜치 감지 + complete 실행 (인수 검증, test, commit, PR, status 갱신). TDD 이행 여부는 phase-complete **진입부의 TDD 이행 게이트(Step -2)** 가 모든 진입 경로에서 공통 검사한다.

> **환경 감지**: 위 3개 모드는 phase-setup을 건너뛰므로, Phase 진입 전에 다음을 수행한다:
> 1. `.claude/config.json`의 `"vcs"`로 `VCS_TYPE`을 결정한다 (없거나 파싱 불가하면 `"git"`).
> 2. **git**: `git rev-parse --is-inside-work-tree`로 repo 확인. **svn**: `svn info`로 작업 복사본 확인.
> 3. `PROJECT_ROOT` = 현재 디렉토리.
> 4. **git**: `git branch --show-current` → `/`를 `-`로 치환 → `DEV_DIR = .dev/{branch-slug}/`. **svn**: `DEV_DIR = .dev/trunk/`.
> 5. `${DEV_DIR}/state.md`가 없으면 최소 골격을 생성한다 (`pipeline: gx-tdd`, `status: in_progress`, `verify-status: pending`, `branch`, `flags: --phase {name}`). `--phase implement`의 기준선 게이트(Step 0.5)가 warnings-baseline을 이 파일에 기록해야 이후 `--phase complete`의 gx-verify가 로드할 수 있고, `pipeline`/`verify-status` 필드가 있어야 커밋/PR 게이트(skill-routing·gx-commit·gx-pull-request)가 동작한다.

---

## 에러 처리

- Phase가 심각하게 실패하면 에러를 표시하고 사용자에게 진행 방법을 확인한다.
- 에러를 조용히 무시하지 않는다.
- 도구나 명령이 사용 불가하면 대안을 제안한다.
- 사용자가 중단하면 진행 상황을 저장하고 완료된 내용을 보고한다.
- phase-review의 ZT 통합 감사가 실패해도 QA 리뷰 결과만으로 진행한다. 감사 실패를 사용자에게 알린다.
- 2분 이상 소요될 수 있는 Bash 명령(`./gradlew test`, `npm test`, `npm install` 등)에는 `timeout: 300000`(5분, config.json `timeouts.build` 값)을 설정한다.
