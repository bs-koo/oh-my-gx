---
name: dev
version: 1.0.0
description: "PRD → 설계 → 구현 → 리뷰 → 커밋/PR까지 전체 개발 사이클을 에이전트 팀이 Q&A 루프로 수행"
argument-hint: "<자연어 요청>"
allowed-tools: ["Bash(git *)", "Bash(test *)", "Bash(mkdir *)", "Bash(cp *)", "Bash(mv *)", "Bash(ls *)", "Bash(find *)", "Bash(pwd *)", "Bash(basename *)", "Bash(dirname *)", "Bash(which *)", "Bash(./gradlew *)", "Bash(gh *)", "Bash(GH_HOST= *)", "Read", "Edit", "Write", "Glob", "Grep", "Task", "AskUserQuestion"]
---

오케스트레이터. 직무 기반 Agent 팀과 Q&A 피드백 루프로 전체 개발 사이클을 관리한다.

항상 한국어로 응답한다.

## 스킬 참조 경로

이 스킬의 파일들은 프로젝트 루트의 `.claude/skills/dev/` 하위에 위치한다.
Phase 파일이나 다른 스킬을 Read할 때, 현재 작업 디렉토리(프로젝트 루트)를 기준으로 절대 경로를 구성한다.

다른 스킬의 프로세스를 실행할 때 아래 경로에서 Read한다:
- `<프로젝트 루트>/.claude/skills/commit/SKILL.md`
- `<프로젝트 루트>/.claude/skills/pull-request/SKILL.md`

## 인자

`ARGS[0]`에 자연어 요청을 받는다. 레거시 플래그도 호환한다.

### 의도 파싱

ARGS[0]을 받으면 아래 순서로 의도를 파싱한다:

**Step 1: 레거시 플래그 호환** (기존 사용자 보호)
- `--hotfix`, `--phase`, `--base`, `--status`, `--resume`이 포함되면 기존 로직 그대로 실행.
- 플래그가 없으면 Step 2로 진행.

**Step 2: 자연어 → 모드 판정**

| 감지 패턴 | 모드 | 예시 |
|-----------|------|------|
| `상태`, `진행`, `어디까지`, `현황` | STATUS | "지금 어디까지 됐어?" |
| `이어서`, `계속`, `재개`, `아까 하던` | RESUME | "아까 하던 작업 이어서 해줘" |
| `긴급`, `핫픽스`, `급한`, `빨리 고쳐`, `버그 수정만` | HOTFIX | "로그인 버그 긴급 수정해줘" |
| `설계만`, `PRD만`, `구현만`, `리뷰만`, `커밋만` | PHASE(해당) | "설계만 해줘" |
| `{branch}에서`, `{branch} 기반`, `{branch} 브랜치` | BASE 추출 | "develop 브랜치 기반으로 작업해줘" |
| 위 어디에도 해당 안 됨 | NORMAL | "로그인 기능 추가해줘" |

PHASE 매핑: `PRD만`/`요구사항만` → `--phase requirements`, `설계만` → `--phase design`, `구현만` → `--phase implement`, `리뷰만` → `--phase review`, `커밋만`/`PR만` → `--phase complete`.

BASE 추출: `{branch}에서`, `{branch} 기반`, `{branch} 브랜치`에서 branch명을 추출하여 `--base`로 처리한다.

### 모드 판정 결과 기록

의도 파싱 결과를 state.md에 기록한다:
```yaml
mode: normal | hotfix
intent-source: flag | natural-language
```

### 레거시 플래그 참조 (호환용)

- `--phase requirements|design|implement|review|complete`: 특정 Phase만 실행
- `--hotfix`: 긴급 버그 수정용 경량 경로
- `--base <branch>`: 베이스 브랜치 지정
- `--status`: 현재 파이프라인 진행 상태 조회
- `--resume`: 이전 파이프라인 재개

ARGS[0]이 없고 모드도 판정되지 않으면 다음을 응답:
"구현할 기능이나 수정할 버그를 설명해주세요. 예: `/dev 로그인 기능 추가해줘`"

### --status 동작
`--status`가 지정되면 파이프라인을 실행하지 않고 현재 상태만 출력한다:

1. phase-setup의 0.0과 동일한 방식으로 `.dev/state.md`를 탐색한다.
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

## Agent 팀

| Agent | 분류 | 역할 | 관점 | 모델 |
|-------|------|------|------|------|
| product-owner | PRODUCT | PRD 작성 + 인수 검증 | "뭘 만들지" / "비즈니스 의도대로 됐나" | sonnet |
| architect | PLANNING | 설계 | "어떻게 만들지" / "구조적 일관성" | opus |
| design-critic | REVIEW | 설계 비판 검토 | "이 가정이 맞나" / "더 단순하게 안 되나" | opus |
| coder | EXECUTION | 구현 + 수정 | "만든다" | opus |
| qa-manager | REVIEW | 코드 리뷰 + 스펙 충족 검증 | "스펙대로 됐나" | sonnet |
| security-auditor | REVIEW | 정책/보안/허점 감사 | "뭘 놓쳤나" | sonnet |
| researcher | ANALYSIS | 코드베이스 조사 + 기술 비교 | "이해한다" (독립 호출 전용) | sonnet |
| hacker | RECOVERY | 제약 우회 + 정체 탈출 | "다른 길이 있다" (정체 감지 시 호출) | sonnet |
| simplifier | RECOVERY | 복잡도 제거 + 범위 축소 | "더 작게 만들자" (정체 감지 시 호출) | sonnet |

### 모델 라우팅 원칙

- 비판적 분석 (가정 도전, 설계 비판): opus — 추론 깊이 우선
- 구조적 설계 (기술 설계, 아키텍처 결정): opus — 설계 품질 우선
- 코드 구현 (구현, 수정): opus — 복잡한 코드 생성 품질 우선
- 산출물 생성 (PRD, 리뷰): sonnet — 비용 효율 우선
- 정체 탈출 (제약 우회, 복잡도 제거): sonnet — 빠른 판단 우선
- 단순 검증 (Mechanical Gate 결과 판단): 오케스트레이터가 직접 수행 — 에이전트 불필요

## Phase 개요

| Phase | 파일 | 주 Agent | Q&A Loop |
|-------|------|----------|----------|
| setup | 작업환경 준비 | (inline) | No |
| requirements | PRD Q&A | product-owner | Yes (max 1) |
| design | 설계 Q&A | architect + design-critic (선택적) | Yes (max 2) |
| implement | 구현 + 자기점검 | coder + qa-manager | Self-check (1회) |
| review | 검토 + 감사 | qa-manager + security-auditor (병렬) | Yes (max 2) |
| complete | 완료 | product-owner (인수) + (스킬 참조) | 인수 재시도 (max 1) |

### Hotfix 경로 (`--hotfix`)

긴급 버그 수정용 경량 경로. 설계/리뷰를 건너뛰지만, **경량 PRD와 인수 검증은 실행**한다:
```
--hotfix: setup → requirements (경량) → implement → complete (인수검증 포함)
정상:     setup → requirements → design → implement → review → complete
```
- requirements: product-owner가 소형 PRD를 작성한다 (배경 + 요구사항 + 수용 기준만).
- design: 건너뛴다. coder가 PRD와 코드 맵을 기반으로 직접 구현한다.
- review: 건너뛴다.
- complete: 인수 검증(5.1)을 **실행**한다. PRD 수용 기준 대비 결과를 검증한다.

## Phase 라우팅

Phase에 진입할 때 **반드시** 해당 Phase 파일을 Read한 후 실행한다:
```
Read(`<프로젝트 루트>/.claude/skills/dev/phases/phase-{name}.md`)
```
예: `phase-setup.md`, `phase-requirements.md`, `phase-design.md`, `phase-implement.md`, `phase-review.md`, `phase-complete.md`

Phase 파일의 지시에 따라 실행하고, 완료 후 다음 Phase로 진행한다.

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
**저장**: 코드 맵이 갱신될 때마다 `.dev/codemap.md`에 Write한다.
**전달**: 모든 agent 호출 시 현재 코드 맵을 프롬프트에 포함한다.

## Trust Ledger (신뢰 원장)

security-auditor의 감사 결과를 누적하는 문서. 오케스트레이터가 관리한다.

**구조:**
```
## Trust Ledger

### 통합 감사 (review)
- [분류/심각도] 항목 설명
  - 근거: ...
  - 권고: ...
```

**생성**: phase-review에서 ZT 통합 감사 완료 시 생성.
**저장**: `.dev/trust-ledger.md`에 저장한다.
**전달**: PR 본문에 감사 결과 요약으로 포함한다.

---

## 공유 규칙

### 작업 경로 기준
phase-setup에서 결정된 변수를 이후 모든 Phase에서 사용한다:
- `GIT_PREFIX`: 항상 `git`. 소비 프로젝트 루트에서 직접 실행한다.
- `PROJECT_ROOT`: 항상 `./` (현재 디렉토리).
- `DIFF_FILE`: 변경사항 diff를 저장하는 파일 경로. `.dev/diff.txt`. Diff 수집 규칙에 따라 phase-implement(자기점검), phase-review, phase-complete에서 갱신된다.
- `DOMAIN_CONTEXT`: phase-setup 0.3에서 `context/*/PROJECTS.md` 매칭으로 로드된 도메인 용어(glossary)와 아키텍처 정보. 매칭되지 않으면 빈 상태.
- Agent에게 `PROJECT_ROOT` 경로를 항상 전달하여 파일 도구(Read/Write/Edit/Glob/Grep)의 기준점으로 사용하게 한다.
- 빌드/테스트 명령(`./gradlew`, `npm`, `pytest` 등)을 `PROJECT_ROOT`에서 실행할 때, Bash 작업 디렉토리가 변경되지 않도록 **서브셸**을 사용한다: `(cd ${PROJECT_ROOT} && ./gradlew build)`. 괄호 `()`로 감싸면 서브셸에서 `cd`가 실행되어 부모 셸의 작업 디렉토리가 유지된다.

### 베이스 브랜치 감지
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
- **Q&A Phase 완료 보고**: 확정된 산출물을 파일에 저장하고, 사용자에게는 **요약만** 보고한다 ("PRD 확정. .dev/prd.md에 저장됨" 등).
- **Q&A 없는 Phase** (implement, review, complete): Agent 출력의 **요약만** 사용자에게 표시한다. 전문은 파일에 저장하거나 변수에 보관한다.

이후 Phase에서 이전 산출물이 필요하면 **파일을 Read하여 Agent prompt에 포함**하되, 오케스트레이터 자신의 출력에는 포함하지 않는다. 각 Phase 파일에서 구체적인 요약 포맷을 정의한다.

### 문서 보관
- phase-requirements 완료 시 확정된 PRD를 `.dev/prd.md`에 저장한다.
- phase-design 완료 시 확정된 설계 문서를 `.dev/design.md`에 저장한다.
- Trust Ledger를 `.dev/trust-ledger.md`에 저장한다.
- 코드 맵을 `.dev/codemap.md`에 저장한다 (갱신 시마다).
- 자기점검 결과를 `.dev/self-check.md`에 저장한다 (phase-implement 자기점검 완료 시).
- phase-design, phase-implement, phase-review 진입 시 해당 파일들을 Read하여 에이전트 프롬프트에 사용한다.
- `.gitignore` 보강은 phase-setup의 Step 0.5a에서 프로젝트 타입별로 처리한다 (`.dev/` 포함).

### 진행 상태 추적 (state.md)
파이프라인 진행 상태를 `.dev/state.md`에 기록하여 세션 재개를 지원한다.

**state.md 구조:**
```yaml
phase: implement
status: in_progress
branch: JIRA-123
base: main
project-type: kotlin-gradle
project-root: ./
args: "[JIRA-123] 로그인 기능 추가"
flags: --hotfix
started: 2026-02-17T10:30:00
current-step: "자기점검"
phases:
  setup: completed
  requirements: completed
  design: completed
  implement: in_progress
steps:
  implement:
    - coder 구현: completed
    - 자기점검: in_progress
  review:
    - mechanical-gate: pending
    - qa-review-1: pending
execution-log:
  - phase: implement
    agent: coder
    result: completed
    steps-reported: 5/5
  - phase: implement
    agent: qa-manager (자기점검)
    result: "Critical 1건, Warning 2건"
  - phase: implement
    agent: coder (수정)
    result: "Critical 1건 해소"
  - phase: review
    step: mechanical-gate
    result: "build ✓, test ✓"
  - phase: review
    agent: qa-manager
    result: "CERTAIN 0건, QUESTION 1건"
  - phase: review
    agent: security-auditor
    result: "CRITICAL 0건"
```

**갱신 규칙:**
- Phase 진입 시: `phase: {name}`, `phases.{name}: in_progress`로 갱신.
- Phase 완료 시: `phases.{name}: completed`로 갱신.
- Phase 내 주요 Step 시작/완료 시: `current-step`과 `steps` 갱신.
- `--resume` 시 `current-step`에서 재개한다 (Phase 처음부터가 아닌 중단 Step부터).
- 에이전트 호출 완료 시: `execution-log`에 엔트리 추가 (agent명, result 요약).
- Gate 실행 결과도 `execution-log`에 기록한다.
- 정체 감지 시: 해당 `execution-log` 엔트리에 `stagnation: {패턴}` 필드를 추가한다.
- phase-complete 완료 시: `status: completed`로 갱신.
- 새 파이프라인 시작 시 기존 state.md를 덮어쓴다.

### Context Slicing 규칙
설계서와 PRD를 Agent에게 전달할 때, 역할에 따라 필요한 섹션만 전달하여 컨텍스트 효율을 높인다:
- **product-owner (PRD 작성)**: ARGS[0] + 코드 맵 + 프로젝트 타입/구조 + 프로젝트 루트 경로 + DOMAIN_CONTEXT (있으면)
- **product-owner (인수 검증)**: PRD의 "요구사항" + "수용 기준" + diff 파일 경로 (`DIFF_FILE`) + 코드 맵
- **architect (설계)**: PRD 전체 + 코드 맵 + 프로젝트 타입/구조/컨벤션 + 프로젝트 루트 경로 + DOMAIN_CONTEXT (있으면)
- **coder (구현)**: 설계서 전체 + 코드 맵 + 프로젝트 루트 경로. `--hotfix`이면 설계서 대신 PRD + 코드 맵.
- **coder (수정)**: 수정 항목 목록 + 수정 방안 + 코드 맵 + 프로젝트 루트 경로
- **qa-manager**: PRD의 "요구사항" + "수용 기준" + 설계서의 "변경 범위" 섹션 + 코드 맵
- **qa-manager (자기점검)**: PRD의 "요구사항" + "수용 기준" 섹션만 (스펙 충족 확인용)
- **security-auditor (통합 감사)**: PRD 전체 + 설계서 전체 + diff 파일 경로 (`DIFF_FILE`) + 코드 맵
- **design-critic (설계 비판)**: 설계서 초안 + PRD + 코드 맵 + 프로젝트 루트 경로
- **researcher (독립 조사)**: 조사 요청 + 코드 맵 (있으면) + 프로젝트 루트 경로
- **hacker (제약 우회)**: 정체 상황 설명 (에러 메시지, 시도한 접근) + 코드 맵 + 프로젝트 루트 경로
- **simplifier (복잡도 제거)**: 정체 상황 설명 + 설계서 + PRD + 코드 맵

각 에이전트에 전달하는 입력 크기가 `.claude/config.json`의 `contextLimits`를 초과하면, 우선순위가 낮은 섹션부터 요약 또는 생략한다.

### 병렬 실행 규칙
읽기 전용 Agent(product-owner, architect, design-critic, qa-manager, security-auditor, researcher, hacker, simplifier)는 서로 병렬 실행이 가능하다. 병렬 실행 시:
1. 하나의 메시지에서 여러 `Task()` 호출을 동시에 발행한다.
2. 모든 병렬 Task가 완료된 후 결과를 합산한다 (Gate 로직).
3. 쓰기 Agent(coder)는 다른 쓰기 Agent와 병렬 실행하지 않는다.
4. coder와 읽기 전용 Agent의 병렬은 **읽기 Agent가 이전 Phase의 산출물(설계서 등)만 참조하는 경우** 허용한다. 현재 구현 중인 코드를 참조하는 읽기 Agent와는 병렬하지 않는다.

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

1. `DIFF_FILE = .dev/diff.txt`. **매 수집 시** `mkdir -p .dev`를 실행하여 디렉토리 존재를 보장한다.
2. diff를 파일에 직접 리다이렉트한다 (Bash 결과에 diff가 나타나지 않음):
   ```bash
   git diff --cached > .dev/diff.txt
   ```
3. `wc -l < .dev/diff.txt`로 줄 수를 확인한다.
4. 총 변경이 **500줄 이상**이면: `--stat` 요약을 파일 앞에 추가하고, 파일 끝에 "변경된 파일을 Read 도구로 직접 확인하라"는 안내를 추가한다:
   ```bash
   git diff --cached --stat > .dev/diff.txt
   echo "---" >> .dev/diff.txt
   echo "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라." >> .dev/diff.txt
   ```
5. Agent 프롬프트에는 **파일 경로만 전달**한다:
   ```
   변경사항 diff: .dev/diff.txt
   이 파일을 Read하여 변경사항을 확인하라.
   ```

이 규칙은 모든 diff 패턴에 적용한다: `git diff --cached` (스테이징), `git diff <base>...HEAD` (브랜치 비교) 등. 브랜치 비교 시에는 해당 diff 명령으로 리다이렉트한다.

### 에이전트 질문 → AskUserQuestion 변환 규칙

에이전트(product-owner, architect, qa-manager, security-auditor)가 "확인이 필요한 사항"에 구조화된 질문을 출력하면, 오케스트레이터가 AskUserQuestion으로 변환하여 사용자에게 제시한다.

#### 변환 프로세스

1. 에이전트 출력에서 "확인이 필요한 사항" 섹션을 파싱한다.
2. "추가 확인 사항 없음"이 포함되면 질문 변환을 건너뛴다.
3. 각 질문의 `유형` 필드에 따라 변환한다:

**유형: 선택** → AskUserQuestion 선택형:
```
AskUserQuestion(
  question: "질문 텍스트",
  options: [
    { value: "a", label: "레이블 — 설명" },
    { value: "b", label: "레이블 — 설명" },
    { value: "c", label: "직접 입력 — 위 선택지 외 직접 입력합니다" }
  ],
  description: "맥락 텍스트"
)
```

**유형: 자유입력** → AskUserQuestion 자유입력형:
```
AskUserQuestion(
  question: "질문 텍스트",
  description: "맥락 텍스트"
)
```

#### 변환 규칙

- **(권장)** 표시가 있는 선택지는 options 배열의 첫 번째에 배치한다.
- **"직접 입력"** 선택지는 항상 마지막에 배치한다. 사용자가 이 옵션을 선택하면 후속 AskUserQuestion(자유입력)으로 직접 값을 받는다.
- 질문이 **2개 이상**이면 순서대로 하나씩 AskUserQuestion을 호출한다. 이전 답변이 다음 질문의 맥락에 영향을 주는 경우 반영한다.
- 에이전트가 기술 용어를 사용한 경우, 사용자에게 표시할 때 **비기술적 표현으로 의역**한다. 예: "JWT vs 세션" → "로그인 유지 방식".
- multiSelect가 필요한 경우(에이전트가 "복수 선택 가능"으로 표시): `multiSelect: true`를 추가한다.

#### 승인/수정 공통 패턴

산출물(PRD, 설계서, 구현 계획) 확인 시 공통으로 사용하는 AskUserQuestion 패턴:
```
AskUserQuestion(
  question: "{산출물}을 확인해주세요.",
  options: [
    { value: "approve", label: "승인 — 다음 단계로 진행" },
    { value: "modify", label: "수정 요청 — 수정할 부분을 알려주세요" }
  ]
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
- `--phase design`: setup (필요 시) + requirements + design만 실행. 대화 맥락에 요구사항이 없고 `.dev/prd.md`도 없으면 requirements부터 시작.
- `--phase implement`: 환경 감지 + implement 실행. 대화 맥락에 설계서가 없고 `.dev/design.md`도 없으면: "설계서가 필요합니다. `/dev --phase design`을 먼저 실행하거나 설계 내용을 입력해주세요." 후 중단.
- `--phase review`: 환경 감지 + 베이스 브랜치 감지 + review 실행 (현재 변경사항을 리뷰).
- `--phase complete`: 환경 감지 + 베이스 브랜치 감지 + complete 실행 (test, commit, PR).

> **환경 감지**: 위 3개 모드는 phase-setup을 건너뛰므로, Phase 진입 전에 다음을 수행한다:
> 1. `git rev-parse --is-inside-work-tree`로 git repo 확인.
> 2. `PROJECT_ROOT` = 현재 디렉토리. 완료.

---

## 에러 처리

- Phase가 심각하게 실패하면 에러를 표시하고 사용자에게 진행 방법을 확인한다.
- 에러를 조용히 무시하지 않는다.
- 도구나 명령이 사용 불가하면 대안을 제안한다.
- 사용자가 중단하면 진행 상황을 저장하고 완료된 내용을 보고한다.
- phase-review의 ZT 통합 감사가 실패해도 QA 리뷰 결과만으로 진행한다. 감사 실패를 사용자에게 알린다.
- 2분 이상 소요될 수 있는 Bash 명령(`./gradlew test`, `npm test`, `npm install` 등)에는 `timeout: 300000`(5분)을 설정한다.
