---
name: gx-dev
description: PRD에서 PR까지 전체 개발 사이클을 에이전트 팀으로 수행한다. "개발해줘", "구현해줘", "만들어줘" 시 사용.
argument-hint: "<자연어 요청>"
allowed-tools:
  # VCS
  - Bash(git *)
  - Bash(svn *)
  - Bash(gh *)
  - Bash(GH_HOST= *)
  # 빌드/테스트
  - Bash(./gradlew *)
  - Bash(npm *)
  - Bash(bun *)
  - Bash(npx *)
  - Bash(pnpm *)
  - Bash(yarn *)
  - Bash(pytest *)
  - Bash(go *)
  - Bash(make *)
  - Bash(cmake *)
  - Bash(ctest *)
  - Bash(ceedling *)
  - Bash(cargo *)
  - Bash(mvn *)
  - Bash(dotnet *)
  # 파일 시스템
  - Bash(test *)
  - Bash(mkdir *)
  - Bash(cp *)
  - Bash(mv *)
  - Bash(ls *)
  - Bash(pwd *)
  - Bash(basename *)
  - Bash(dirname *)
  - Bash(which *)
  - Bash(wc *)
  - Bash(echo *)
  - Bash(mktemp *)
  - Bash(sort *)
  - Bash(rm -f *)
  # 도구
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Task
  - Skill
  - AskUserQuestion
---

오케스트레이터. 직무 기반 Agent 팀과 Q&A 피드백 루프로 전체 개발 사이클을 관리한다.

항상 한국어로 응답한다.

## 스킬 참조 경로

**번들 파일 경로 규약**: 이 스킬의 phase·참조 파일은 이 SKILL.md와 같은 디렉토리 아래에 있다. **그 지시가 적힌 파일의 위치를 기준으로 한 상대경로**로 Read한다 — 하네스가 플러그인을 어디에 설치하든(Claude Code의 플러그인 캐시, Codex의 스킬 루트) 파일 사이의 상대 위치는 같으므로 경로가 어긋나지 않는다.
- 예: `Read("phases/phase-setup.md")`
- 상대경로 Read가 실패하면, 하네스가 알려준 이 SKILL.md의 절대경로에서 디렉토리 부분을 떼어 앞에 붙인 뒤 다시 시도한다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("references/codex-runtime.md")`로 공통 실행 규약을 읽고, 이 스킬의 절차·게이트를 유지한다. 상대경로는 이 SKILL.md 위치 기준이다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.
질문은 한 번에 1~3개, 질문마다 선택지는 2~3개로 제한한다. 추천 답변은 첫 번째에 놓고 label 끝에 `(Recommended)`를 붙인다. UI가 자유 입력을 제공하므로 Other를 option으로 직접 추가하지 않는다. Codex 변환에서는 `references/codex-runtime.md`와 실제 도구 스키마를 우선한다.

| 이 문서의 표기 | Codex 대응 |
|----------------|-----------|
| `Task(subagent_type="oh-my-gx:{name}")` | 공통 실행 규약의 `codex-roles/index.json`과 역할 본문·도구 제약을 읽어 `spawn_agent`의 message에 태스크 prompt 전문과 함께 전달한다. 격리 시 `fork_turns: "none"`을 쓴다 |
| `AskUserQuestion` | `request_user_input`. 그 도구를 쓸 수 없으면 자연어로 묻되, **승인 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다 |
| `Skill(skill: "oh-my-gx:{name}")` | 해당 스킬의 `SKILL.md`를 읽어 그 절차를 수행한다 |

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.


다른 스킬의 프로세스를 실행할 때 **반드시 `Skill` 도구로 호출**한다:
- 커밋: `Skill("oh-my-gx:gx-commit")`
- PR 생성: `Skill("oh-my-gx:gx-pull-request")`

`Skill` 도구가 있는 하네스에서는 `Read()`로 스킬 파일을 읽어 인라인 실행하지 않는다 — `Skill` 도구를 거쳐야 스킬의 `allowed-tools` 제한이 시스템 레벨에서 강제된다. `Skill` 도구가 없는 하네스에서는 위 하네스 적응표대로 해당 `SKILL.md`를 읽어 절차를 수행하고, 그 스킬의 게이트·확인 단계를 그대로 지킨다.

## 필수 실행 계약 로드

Phase 목록을 계산하기 전에 다음 파일을 순서대로 Read한다. 상대경로는 이 gx-dev/SKILL.md 위치를 기준으로 해석한다.

1. `Read("references/intent-routing.md")`
2. `Read("references/pipeline-state.md")`
3. `Read("references/interaction-contract.md")`

세 파일을 읽은 뒤 의도 파싱 결과에 따라 아래 Phase 실행 루프를 수행한다.

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
- 위 원칙과 Agent 팀 표의 모델은 **표준 프로파일(standard)** 기준이다. 에코 모드(eco)에서는 architect를 제외한 opus 에이전트가 sonnet으로 하향된다 — 공유 규칙 "모델 프로파일" 참조.

## Phase 개요

| Phase | 파일 | 주 Agent | Q&A Loop |
|-------|------|----------|----------|
| setup | 작업환경 준비 | (inline) | No |
| requirements | PRD Q&A | product-owner | Yes (사용자 승인까지) |
| design | 설계 Q&A | architect + design-critic (선택적) | Yes (사용자 승인까지) |
| implement | 구현 + 자기점검 | coder + qa-manager | Self-check (1회) |
| core | AC 확인 + 구현 + Gate + 기록 | (inline, 규모에 따라 coder) | AC 확인 (승인까지) |
| review | 검토 + 감사 | qa-manager + security-auditor (병렬) | Yes (max 2) |
| complete | 완료 | product-owner (인수) + (스킬 참조) | 인수 재시도 (max 1) |

### 핵심 모드 경로 (core)

소형 변경용 경량 경로. 에이전트 팀 대신 오케스트레이터가 직접 수행하되, **기록(ac.md·summary.md)과 Mechanical Gate는 유지**한다 — "그냥 프롬프팅"과의 차이가 바로 이 둘이다:
```
core: setup → core (AC 확인 → 구현 → Mechanical Gate → 기록) → complete (AC 자가 검증 + 커밋/PR)
all:  setup → requirements → design → implement → review → complete
```
- AC 작성·확인: 오케스트레이터가 `${DEV_DIR}/ac.md`(초경량 PRD: 배경 + 요구사항)를 직접 작성해 사용자 1회 확인. 긴급 버그 수정 요청이면 AC를 재현 조건 관점으로 작성한다.
- 구현: 예상 변경 파일 2개 이하 + 방향 명확이면 오케스트레이터 직접, 그 외 coder 1회 디스패치.
- Mechanical Gate: build + test **필수**. 통과 없이 complete에 진입하지 않는다.
- complete: product-owner 인수 대신 **AC 자가 검증**. PR에는 ac.md(배경/요구사항)와 summary.md(변경 요약)를 전달한다.
- 자연어 "긴급/핫픽스"도 이 경로로 실행된다.

## Phase 라우팅 — 필수 실행 프로토콜

> **CRITICAL: Phase 스킵 절대 금지.**
> "요구사항이 명확하다", "범위가 작다", "이미 확정되어 있다", "간단하다" 등 어떤 이유로도 Phase를 건너뛰지 않는다.
> Phase를 건너뛸 수 있는 조건은 핵심 모드(사용자가 명시적으로 선택한 경량 경로 — 기록·Gate는 유지), `--phase` 플래그, 그리고 `--ralph`(플래그 또는 자연어 `랄프로` 등)로 phase-implement에서 **gx-ralph로 전환**한 경우(gx-ralph 호출 후 종료 — 이후 Phase는 루프 종료 후 `--phase review`/`--phase complete`로 재개)뿐이다.
> 이 규칙을 위반하면 사용자가 기대하는 PRD, 설계서, 리뷰가 누락되어 품질 사고가 발생한다.

### Phase 실행 루프

아래 의사코드를 기계적으로 실행한다. **판단하지 말고 순서대로 실행한다.**

```
# 1. 모드에 따라 Phase 목록 결정
if core (핵심 모드):
    PHASES = [setup, core, complete]
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
    # 참고: core 모드는 PRD/설계서 대신 ac.md로 진행하므로 이 게이트를 적용하지 않는다
    if phase == "design" and not exists("${DEV_DIR}/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and not exists("${DEV_DIR}/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and not exists("${DEV_DIR}/design.md"):
        → phase-design부터 실행
    if phase == "review" and 변경사항이 없음:
        # VCS_TYPE == "git": `git status --porcelain`(스테이징·미스테이징·untracked 포함)이 비어있고 **그리고** `git log {base}..HEAD` 커밋도 없을 때만 중단.
        #      워킹트리 변경 또는 브랜치 커밋 어느 한쪽이라도 있으면 진입한다 (커밋만 있는 경우의 diff 구성은 phase-review가 처리).
        # VCS_TYPE == "svn": svn status가 비어있음
        → "변경사항이 없습니다" 보고 후 중단

    # 2b. Phase 파일 Read (필수)
    Read("phases/phase-{phase}.md")

    # 2c. Phase 파일의 지시에 따라 실행

    # 2d. state.md 갱신
    Update state.md → phases.{phase}: completed

    # 2e. 다음 Phase로 진행
```

### Phase 파일 경로

`phase-setup.md`, `phase-requirements.md`, `phase-design.md`, `phase-implement.md`, `phase-core.md`, `phase-review.md`, `phase-complete.md`

### Agent 팀 강제

Phase 실행 시 반드시 이 스킬에 정의된 Agent 팀(product-owner, architect, design-critic, coder, qa-manager, security-auditor)을 사용한다.
외부 Agent(sisyphus-junior, sisyphus-junior-high 등)로 대체하지 않는다.

**디스패치 이름 규칙**: Task의 `subagent_type`에는 `oh-my-gx:` 접두사가 붙은 정식 이름을 사용한다 (예: `oh-my-gx:coder`). 접두사 없는 bare 이름은 동명의 외부 에이전트와 충돌할 수 있다.

### 커밋/PR 스킬 강제

커밋과 PR 생성은 반드시 Skill 도구로 위임한다. 오케스트레이터가 `git commit`, `gh pr create` 등을 직접 실행하지 않는다.
- 커밋: `Skill(skill: "oh-my-gx:gx-commit")`
- PR: `Skill(skill: "oh-my-gx:gx-pull-request")`
- 스킬 호출 실패 시 직접 명령어로 우회하지 않고, 사용자에게 보고한다.
