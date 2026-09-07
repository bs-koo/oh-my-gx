# gx-tdd 지시문 밀도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-tdd 오케스트레이터가 사이클마다 읽는 지시문을 줄인다 — SKILL.md 74,904B → 58,000B 이하, phase-setup.md 35,622B → 22,000B 이하 — 그리고 그 예산을 정합성 린트로 고정한다. 실행 규칙·판별 키·지시 문구는 하나도 바꾸지 않는다.

**Architecture:** 세 가지 수단만 쓴다. (1) **추출** — 실행 중 읽히지 않는 유지보수 노트와 하네스 대응표를 `references/`로 옮기고 한 줄 포인터를 남긴다. (2) **압축** — 산문·YAML 예시로 서술된 스키마와 입력 규칙을 표로 바꾼다. (3) **조건부 로드** — phase-setup에서 `--resume`·`--work` 경로에만 필요한 절을 별도 phase 파일로 빼고 플래그가 있을 때만 Read한다. 이 저장소의 테스트는 `scripts/lint-consistency.sh`이므로 각 태스크는 린트 통과 상태로 끝나고, 마지막 태스크가 바이트 예산 검사를 추가한다(변이 시험으로 RED 확인).

**Tech Stack:** Markdown (스킬·phase·references), Bash (린트 스크립트)

**Spec:** `docs/specs/2026-09-07-tdd-density-rhythm-design.md` — D3 절과 4절 비용 모델

## Global Constraints

- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (PreToolUse 훅 G1이 차단). 작업 시작 전 `feat/tdd-instruction-density` 브랜치를 생성한다.
- **커밋**: 메시지는 `docs: …` 또는 `feat: …` 한 줄 제목 (`.claude/config.json` `conventions.commitFormat`). gx-commit 규칙에 따라 `Co-Authored-By` 등 트레일러를 **붙이지 않는다**. 서브에이전트는 gx-commit의 확인 게이트에 응답할 수 없으므로 직접 `git commit`을 허용한다 (이전 계획과 같은 ruling). 훅 G1 오탐을 피하려면 grep 패턴 인자에 `git commit` 문자열을 넣지 않는다.
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 **둘 다 통과**한 상태로 끝난다.
- **린트 번호 체계**: 현재 `[N/31]`. Task 5가 검사 1개를 추가하며 분모를 32로 올린다. 린트 `[31/31]`이 `.claude/`와 `README.md`의 `[N/M]` 인용을 실제 분모와 대조하므로 스크립트 밖 참조도 함께 치환한다. `docs/`·`CHANGELOG.md`는 과거 기록이라 치환하지 않는다.
- **`sed -i` 이식성**: GNU sed(Linux·Git Bash) 전제. 치환 후 반드시 `grep -c`로 결과를 확인한다.
- **외과적 변경**: 옮기는 텍스트는 **원문 그대로** 옮긴다(잘라내기·붙여넣기). 압축 태스크에서도 굵은 지시 문구·판별 키·경로 문자열은 글자 하나 바꾸지 않는다. 옮기거나 압축하는 대상이 아닌 줄은 건드리지 않는다.
- **gx-dev는 범위 밖**: gx-dev SKILL.md·phase-setup에 같은 구조의 쌍둥이 블록이 있지만 이번에는 손대지 않는다. 린트 [11]·[12]·[21]·[25]가 두 파이프라인을 각각 검사하므로 gx-dev를 안 건드리면 그쪽은 그대로 초록이다.
- **경로 규약**: 새 references·phase 파일은 `.claude/skills/gx-tdd/` 아래에 두고, 지시가 적힌 파일 기준 상대경로로 Read한다 (`Read("references/x.md")`, `Read("phases/setup-work.md")`). 린트 `[15/31]`이 Read 대상의 실존을 검사한다.

---

### Task 1: 하네스 적응 표와 드리프트 목록을 references/로 추출

**Files:**
- Create: `.claude/skills/gx-tdd/references/harness-adaptation.md`
- Create: `.claude/skills/gx-tdd/references/maintenance-notes.md`
- Modify: `.claude/skills/gx-tdd/SKILL.md` (현재 35~43행 하네스 적응 블록, 55~75행 드리프트 주의 블록)
- Modify: `.claude/rules/harness-codex.md:122`

**Interfaces:**
- Consumes: 없음
- Produces: 두 references 파일. Task 5의 예산 검사와 Task 6의 CHANGELOG가 이 파일명을 인용한다.

- [ ] **Step 1: 현재 크기와 이동 대상 경계를 기록한다**

Run: `wc -c .claude/skills/gx-tdd/SKILL.md && grep -nE '^\*\*하네스 적응\*\*|^도구 이름이 다르다는 이유로|^> \*\*드리프트 주의\*\*|^> - \*\*fix 라운드 상한\*\*|^## 인자' .claude/skills/gx-tdd/SKILL.md`
Expected: `74904`, 그리고 5개 앵커 행이 순서대로 출력된다 (하네스 적응 시작 → "도구 이름이 다르다는 이유로" 끝 → 드리프트 주의 시작 → fix 라운드 상한(마지막 항목) → `## 인자`).

- [ ] **Step 2: `references/harness-adaptation.md`를 만든다**

SKILL.md에서 `**하네스 적응**:`으로 시작하는 문단부터 `도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.` 행까지(표 포함)를 **그대로 잘라내어** 아래 머리말 뒤에 붙인다.

```markdown
# gx-tdd 하네스 적응표

이 스킬의 본문은 Claude Code 도구명(`Task`·`AskUserQuestion`·`Skill`)으로 서술한다. Codex 등 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다. SKILL.md가 실행 진입 시 이 파일을 가리킨다.

```

(이하 원문 블록 그대로)

- [ ] **Step 3: `references/maintenance-notes.md`를 만든다**

SKILL.md에서 `> **드리프트 주의**:`로 시작하는 인용 블록부터 `> - **fix 라운드 상한**:` 행까지를 **그대로 잘라내어** 아래 머리말 뒤에 붙인다. 인용 접두 `> `는 유지해도 되고 벗겨도 된다 — 벗기면 항목마다 `- **…**` 불릿이 된다.

```markdown
# gx-tdd 유지보수 노트 — 의도적 중복 목록

이 스킬의 정의 여러 개가 에이전트 자기완결성·라우팅 강제력을 위해 여러 파일에 **의도적으로 중복**돼 있다. 아래는 무엇이 어디에 중복돼 있고 무엇이 SSOT인지의 목록이다. 스킬·phase·에이전트 정의를 **수정할 때** 읽는다. 파이프라인 실행 중에는 읽지 않는다.

```

(이하 원문 블록 그대로)

- [ ] **Step 4: SKILL.md에 포인터 두 줄을 남긴다**

잘라낸 하네스 적응 블록 자리에 아래 한 문단을 넣는다.

```markdown
**하네스 적응**: 이 문서는 Claude Code 도구명(`Task`·`AskUserQuestion`·`Skill`)으로 서술한다. Codex 등 다른 하네스에서 실행 중이면 먼저 `Read("references/harness-adaptation.md")`로 도구 대응표를 읽고 그대로 옮겨 수행한다. 도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다.
```

잘라낸 드리프트 주의 블록 자리에 아래 한 문단을 넣는다. 바로 위의 `> **RGR 보조 스킬(gx-red/gx-green/gx-refactor)은 파이프라인에서 호출하지 않는다.**` 문단은 실행 규칙이므로 **그대로 둔다**.

```markdown
> **의도적 중복 목록**: 이 스킬의 정의 여러 개가 에이전트 자기완결성·라우팅 강제력을 위해 여러 파일에 중복돼 있다. 어느 정의가 어디에 중복돼 있고 무엇이 SSOT인지는 `Read("references/maintenance-notes.md")`에 있다 — 이 스킬이나 에이전트 정의를 **수정할 때** 읽고, 실행 중에는 읽지 않는다.
```

- [ ] **Step 5: harness-codex.md의 근거 문장을 갱신한다**

`.claude/rules/harness-codex.md` 122행의 아래 문장을

```
따라서 하네스 매핑을 이 문서에만 두면 설치 사용자에게 닿지 않는다. `gx-dev`·`gx-tdd`의 SKILL.md에 "하네스 적응" 표를 직접 넣어둔 것은 그 때문이다. 스킬 파일은 어느 경로로 설치되든 항상 함께 배포된다.
```

다음으로 바꾼다.

```
따라서 하네스 매핑을 이 문서에만 두면 설치 사용자에게 닿지 않는다. `gx-dev`는 SKILL.md에 "하네스 적응" 표를 직접 두고, `gx-tdd`는 `references/harness-adaptation.md`에 두고 SKILL.md가 실행 진입 시 가리킨다. 스킬 디렉토리는 어느 경로로 설치되든 항상 함께 배포된다.
```

- [ ] **Step 6: 검증**

Run: `grep -c '드리프트 주의' .claude/skills/gx-tdd/SKILL.md; grep -c 'spawn_agent' .claude/skills/gx-tdd/SKILL.md; grep -c 'spawn_agent' .claude/skills/gx-tdd/references/harness-adaptation.md; grep -c '^\(> \)\?- \*\*' .claude/skills/gx-tdd/references/maintenance-notes.md; wc -c .claude/skills/gx-tdd/SKILL.md`
Expected: `0`, `0`, `1` 이상, `19`, 그리고 SKILL.md가 **64,000B 이하**.

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 31/31 통과 (`[15/31]`이 새 Read 대상 두 파일의 실존을 확인한다), 훅 테스트 통과.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-tdd/references/harness-adaptation.md .claude/skills/gx-tdd/references/maintenance-notes.md .claude/rules/harness-codex.md
git commit -F - <<'MSG'
docs: gx-tdd 하네스 적응표와 의도적 중복 목록을 references/로 추출한다
MSG
```

---

### Task 2: state.md 스키마 예시를 필드 표로 압축

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` — `### 진행 상태 추적 (state.md)` 절 안의 `**state.md 구조 (RGR 사이클 반영)**:` 문단과 그 아래 YAML 코드 블록(현재 약 60줄). `**갱신 규칙:**` 이하는 건드리지 않는다.

**Interfaces:**
- Consumes: 없음
- Produces: 없음. 판별 키 문자열(`pipeline: gx-tdd`, `verify-status`, `verify-fingerprint`, `model-profile`, `warnings-baseline`, `work-id`, `test-file-hash`, `test-count`, `fix-round`, `execution-log`, `current-step`, `last-known-head`, `config-setup-attempts`)은 표 안에 전부 남는다.

- [ ] **Step 1: 교체 범위를 확인한다**

Run: `grep -nE '^\*\*state\.md 구조 \(RGR 사이클 반영\)\*\*:|^\*\*갱신 규칙:\*\*' .claude/skills/gx-tdd/SKILL.md`
Expected: 두 행. 첫 행부터 둘째 행 직전까지가 교체 범위이며, 그 안에 ```` ```yaml ```` 블록 하나가 있다.

- [ ] **Step 2: 범위를 아래 내용으로 교체한다**

```markdown
**state.md 필드** (초기화의 정본은 phase-setup Step 7. 태스크 객체의 정본 예시는 phase-implement "state.md 추적" 절):

| 필드 | 값 | 기록·소비 |
|---|---|---|
| `phase` / `status` | phase명 / `in_progress`·`completed`·`cancelled` | 게이트 4곳(훅·라우팅·gx-commit·gx-pull-request)이 `status: in_progress`를 판별 조건으로 쓴다 |
| `pipeline` | `gx-tdd` | verify-status와 함께 커밋/PR 게이트의 판별 키 |
| `verify-status` | `pending`·`passed` | phase-complete Step -1 verify 통과 시 passed. 코드 변경 재진입 시 pending 리셋 |
| `verify-fingerprint` | `{HEAD단축}:{트리해시12자}` 또는 `""` | passed와 같은 시점에 기록. 게이트 4곳이 현재 지문과 대조해 스테일 passed를 감지 (아래 "verify 지문") |
| `model-profile` | `standard`·`eco` | phase-setup Step 1.5 결정. 에이전트 디스패치 모델 오버라이드 기준 |
| `mode` / `intent-source` / `work-id` / `flags` / `args` | 의도 파싱 결과 | phase-setup Step 7. `flags`는 자연어 RALPH도 `--ralph`로 정규화해 기록하며 phase-implement Step 0.7의 판정 키 |
| `vcs-type` / `branch` / `base` / `project-type` / `project-root` | 환경 감지 | svn은 branch/base 미사용 |
| `started` / `last-known-head` | 시작 시각 / Phase 완료 시점의 HEAD | 재개 시 외부 커밋 감지 (git 전용) |
| `auto-stashed` | true/false | phase-setup 2.1 stash 보호 상태 (git 전용) |
| `config-setup-attempts` | 정수 | phase-setup 3.0 가드의 재시도 카운터. 새 파이프라인 시 0 |
| `warnings-baseline` | 정수 | phase-implement Step 0.5 기준선 게이트가 기록. gx-verify가 신규 경고 판정 기준으로 사용 |
| `current-step` | 문자열 | 재개 지점 (예: `"RGR T2: FIX R2"`) |
| `phases` | setup~complete 각각의 상태 | Phase 진입·완료 시 갱신 |
| `steps` | phase별 Step 목록 | RGR 태스크는 `"RGR T{N} (AC-N)"` 객체에 `red`·`impl`·`test-file`·`test-file-hash`·`test-count`·`report`·`fix-round`를 중첩 (구 green/refactor 키는 3석 세대 전용 — 신규 기록 금지) |
| `execution-log` | `phase`·`agent`·`gate`·`result`·`stagnation` 엔트리 배열 | 에이전트 호출·게이트 결과·정체 감지 기록 |

```yaml
phase: implement
status: in_progress
pipeline: gx-tdd
verify-status: pending
verify-fingerprint: ""
model-profile: standard
warnings-baseline: 12
current-step: "RGR T2: FIX R2"
phases: { setup: completed, requirements: completed, design: completed, implement: in_progress }
steps:
  implement:
    - "RGR T1 (AC-1)": { red: completed, test-file: src/test/.../PasswordValidatorTest.java, test-file-hash: 3ca970cc..., test-count: 47, report: reports/t1-impl.md, impl: completed }
    - "RGR T2 (AC-2)": { red: completed, impl: in_progress, fix-round: 2/5 }
execution-log:
  - { phase: design, agent: test-architect, result: "testability score 8/10 PASS" }
  - { phase: implement, agent: implementer (T2), result: "fix round 2/5 진행 중" }
```

```

- [ ] **Step 3: 검증**

Run: `for k in 'pipeline: gx-tdd' verify-status verify-fingerprint model-profile warnings-baseline work-id test-file-hash test-count fix-round execution-log current-step last-known-head config-setup-attempts auto-stashed; do grep -q "$k" .claude/skills/gx-tdd/SKILL.md || echo "MISSING $k"; done; grep -c '^\*\*갱신 규칙:\*\*' .claude/skills/gx-tdd/SKILL.md; wc -c .claude/skills/gx-tdd/SKILL.md`
Expected: `MISSING` 출력 없음, `1`, SKILL.md가 **61,000B 이하**.

Run: `bash scripts/lint-consistency.sh`
Expected: 31/31 통과.

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md
git commit -F - <<'MSG'
docs: gx-tdd state.md 스키마 예시를 필드 표로 압축한다
MSG
```

---

### Task 3: phase-setup의 재개·작업 계획 절을 조건부 로드 파일로 분리

**Files:**
- Create: `.claude/skills/gx-tdd/phases/setup-resume.md`
- Create: `.claude/skills/gx-tdd/phases/setup-work.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` — `## Step 0` 전체(3~63행), `### 3.0.5 작업 계획 참조` 절(159~213행), `## Step 5.5` 절(265~274행), `## Step 7`의 `**작업 계획 되돌림**:` 문단
- Modify: `.claude/skills/gx-tdd/SKILL.md` — 갱신 규칙의 `--resume` 불릿(현재 584행 부근)에 있는 "phase-setup Step 0.1 정합성 체크"
- Modify: `scripts/lint-consistency.sh:293` — `구 버전 세션 방어` 검사 대상 파일

**Interfaces:**
- Consumes: 없음
- Produces: `phases/setup-resume.md` — "이어서 진행" 확정 시 phase-setup Step 1~7을 건너뛰는 계약을 그대로 유지. `phases/setup-work.md` — 절 제목 `## 작업 계획 참조`, `## 착수 기록`, `## 작업 계획 되돌림` 세 개(phase-setup의 포인터가 이 제목을 인용한다).

- [ ] **Step 1: 이동 범위의 경계를 확인한다**

Run: `grep -nE '^## Step 0:|^## Step 1:|^### 3\.0\.5|^### 3\.1|^## Step 5\.5|^## Step 6:|^\*\*작업 계획 되돌림\*\*' .claude/skills/gx-tdd/phases/phase-setup.md; wc -c .claude/skills/gx-tdd/phases/phase-setup.md`
Expected: 7개 앵커가 순서대로, 크기 `35622`.

- [ ] **Step 2: `phases/setup-resume.md`를 만든다**

phase-setup의 `## Step 0: 진행 중 작업 감지` 행부터 `## Step 1: VCS 확인` **직전 행**까지(`### --resume 플래그가 있는 경우`, `### --resume 플래그가 없는 경우 (자동 감지)`, `### 0.1 재개 정합성 체크`, "이어서 진행 시" 불릿, `### 착수 기록 보정` 전부)를 **그대로 잘라내어** 아래 머리말 뒤에 붙인다. 원문의 `## Step 0: 진행 중 작업 감지` 제목은 유지한다.

```markdown
# phase-setup 보조 — 재개 감지

phase-setup Step 0이 `--resume` 지정 또는 ARGS[0] 부재일 때만 이 파일을 Read한다. 새 작업(ARGS[0] 있음, `--resume` 없음)에서는 읽히지 않는다. "이어서 진행"이 확정되면 phase-setup의 나머지 Step(1~7)을 건너뛴다는 계약은 원문 그대로다.

```

- [ ] **Step 3: `phases/setup-work.md`를 만든다**

아래 세 덩어리를 **그대로 잘라내어** 순서대로 붙인다. 각 덩어리 앞에 지정한 `##` 제목을 단다(원문의 `###`·`##` 제목은 그 아래에 그대로 남겨도 된다).

1. `## 작업 계획 참조` — phase-setup `### 3.0.5 작업 계획 참조 (`--work` 사용 시)` 행부터 `### 3.1 병렬 수집` 직전 행까지
2. `## 착수 기록` — `## Step 5.5: 작업 계획 착수 기록 (`--work` 사용 시)` 행부터 `## Step 6: VCS ignore 자동 보강` 직전 행까지
3. `## 작업 계획 되돌림` — `## Step 7`의 `**작업 계획 되돌림**:`으로 시작하는 문단 한 개

머리말:

```markdown
# phase-setup 보조 — 작업 계획 (`--work`)

의도 파싱이 `--work {ID}`(플래그 또는 WORK 추출)로 작업 ID를 확정한 실행에서만 Read한다. 세 절은 phase-setup의 3.0.5(작업 계획 참조) · 5.5(착수 기록) · 7(작업 계획 되돌림) 자리에서 각각 호출된다. 원문의 Step 번호 인용(3.0.5, 5.5, Step 7)은 phase-setup의 해당 포인터 위치를 가리킨다.

```

- [ ] **Step 4: phase-setup에 포인터 네 개를 남긴다**

잘라낸 Step 0 자리:

```markdown
## Step 0: 진행 중 작업 감지

ARGS[0]이 있고 `--resume`이 없으면 새 작업이다 — 이 Step을 건너뛰고 Step 1로 진행한다.

그 외(`--resume` 지정, 또는 ARGS[0] 부재)에는 `Read("phases/setup-resume.md")`를 수행한다. 그 파일이 state.md 탐색·재개 정합성 체크(0.1)·"이어서 진행" 복원·구 버전 세션 방어·`--work` 세션의 착수 기록 보정을 담당한다. 재개가 확정되면 phase-setup의 나머지 Step(1~7)을 건너뛴다.
```

잘라낸 3.0.5 자리:

```markdown
### 3.0.5 작업 계획 참조 (`--work` 사용 시)

의도 파싱이 `--work {ID}`(플래그 또는 WORK 추출)로 작업 ID를 확정했으면 `Read("phases/setup-work.md")`의 "작업 계획 참조" 절을 수행한다 — 계획 행에서 도메인·요구사항·브랜치명을 확정하고 의존·중복 착수를 확인하며, Step 7에서 state.md에 `work-id`를 기록한다. 작업 ID가 없으면 이 Step을 건너뛴다.
```

잘라낸 Step 5.5 자리:

```markdown
## Step 5.5: 작업 계획 착수 기록 (`--work` 사용 시)

`work-id`가 확정된 실행이면 `phases/setup-work.md`의 "착수 기록" 절을 수행한다 (3.0.5에서 이미 Read한 파일이다). 없으면 건너뛴다.
```

Step 7의 되돌림 문단 자리:

```markdown
**작업 계획 되돌림**: 덮어쓰기 전의 state.md가 `status: completed`이고 `work-id`가 있으면 `phases/setup-work.md`의 "작업 계획 되돌림" 절을 수행한다. 없으면 아무것도 하지 않는다.
```

- [ ] **Step 5: 바깥 포인터와 린트 대상을 갱신한다**

SKILL.md 갱신 규칙의 `--resume` 불릿에서 `재개 전에 phase-setup Step 0.1 정합성 체크(브랜치/HEAD)를 수행한다`를 `재개 전에 phases/setup-resume.md의 0.1 정합성 체크(브랜치/HEAD)를 수행한다`로 바꾼다.

`scripts/lint-consistency.sh` 293행의 검사 대상을 바꾼다.

```bash
sed -i 's|grep -q "구 버전 세션 방어" .claude/skills/gx-tdd/phases/phase-setup.md|grep -q "구 버전 세션 방어" .claude/skills/gx-tdd/phases/setup-resume.md|' scripts/lint-consistency.sh
sed -i 's|fail "구 버전 세션 방어 규칙 누락: gx-tdd phase-setup.md"|fail "구 버전 세션 방어 규칙 누락: gx-tdd setup-resume.md"|' scripts/lint-consistency.sh
grep -n '구 버전 세션 방어' scripts/lint-consistency.sh
```
Expected: 마지막 grep에서 gx-tdd 쪽 두 줄이 `setup-resume.md`를 가리킨다 (gx-dev 쪽 265~266행은 그대로).

- [ ] **Step 6: 검증**

Run: `grep -c '작업 계획 참조' .claude/skills/gx-tdd/phases/phase-setup.md; grep -c 'work-id' .claude/skills/gx-tdd/phases/phase-setup.md; grep -c '협업 공유 대상' .claude/skills/gx-tdd/phases/phase-setup.md; grep -cF "svn propset svn:ignore '.active'" .claude/skills/gx-tdd/phases/phase-setup.md; grep -c '구 버전 세션 방어' .claude/skills/gx-tdd/phases/setup-resume.md; grep -cE '^## (작업 계획 참조|착수 기록|작업 계획 되돌림)$' .claude/skills/gx-tdd/phases/setup-work.md; wc -c .claude/skills/gx-tdd/phases/phase-setup.md`
Expected: 첫 넷 모두 `1` 이상, `1`, `3`, phase-setup.md가 **22,000B 이하**.

Run: `grep -rnE 'Step 0\.1|3\.0\.5|Step 5\.5' .claude/skills/gx-tdd --include=*.md | grep -vE 'setup-(resume|work)\.md|phase-setup\.md'`
Expected: 두 행만 남는다 — SKILL.md의 `--phase` 부트스트랩 각주("phase-setup을 건너뛰어 3.0.5가 실행되지 않으므로")와 phase-complete.md:174("착수 기록(phase-setup Step 5.5)과 같은 층위"). 둘 다 phase-setup에 **같은 번호의 포인터 절이 남아 있으므로** 유효한 참조다. 그대로 둔다. `Step 0.1`은 SKILL.md `--resume` 불릿을 이미 `setup-resume.md`로 고쳤으므로 매칭되지 않는다.

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 31/31 통과 (`[15/31]`이 `phases/setup-resume.md`·`phases/setup-work.md` 실존 확인, `[21]`·`[22]`·`[25]`가 phase-setup에 남긴 문구로 통과), 훅 테스트 통과.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-tdd/phases/setup-resume.md .claude/skills/gx-tdd/phases/setup-work.md .claude/skills/gx-tdd/SKILL.md scripts/lint-consistency.sh
git commit -F - <<'MSG'
docs: gx-tdd phase-setup의 재개·작업 계획 절을 조건부 로드 파일로 분리한다
MSG
```

---

### Task 4: Context Slicing·작업 경로 기준·Agent 결과 전달 규칙을 표로 압축

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` — `### 작업 경로 기준` 절 전체, `### Context Slicing 규칙` 절 전체(`#### PRODUCT`~`#### ANALYSIS / RECOVERY`와 마지막 contextLimits 문장까지), `### Agent 결과 전달 규칙 (컨텍스트 경량화)` 절 전체. `### Diff 수집 규칙`·`### 문서 보관`·`### verify 지문`·`### 모델 프로파일 (MODEL_PROFILE)`은 **건드리지 않는다** (린트 [14]·[21]·[22]가 문구를 고정한다).

**Interfaces:**
- Consumes: 없음
- Produces: 없음. 굵은 지시 문구는 원문 그대로 표 셀로 옮긴다.

- [ ] **Step 1: `### 작업 경로 기준` 절을 교체한다**

절 제목부터 다음 `### ` 제목 직전까지를 아래로 바꾼다.

```markdown
### 작업 경로 기준
phase-setup이 결정한 변수를 이후 모든 Phase가 사용한다.

| 변수 | 값 | 결정 지점 |
|---|---|---|
| `VCS_TYPE` | `.claude/config.json`의 `"vcs"` 값 — `"git"`·`"svn"`·`""`(미설정, `"git"`으로 취급). VCS별 명령어 분기의 기준 | phase-setup Step 1 |
| `GIT_PREFIX` | `VCS_TYPE`이 `"git"`이면 `git`, `"svn"`이면 `svn`. 소비 프로젝트 루트에서 직접 실행 | Step 1 |
| `PROJECT_ROOT` | 항상 `./` (현재 디렉토리) | — |
| `DEV_DIR` | `.dev/{branch-slug}/` — branch-slug는 브랜치명의 `/`를 `-`로 치환한 값 (예: `feat/login` → `.dev/feat-login/`). **SVN은 브랜치가 없으므로 git 브랜치명과 동일 규칙으로 작업 slug를 만들어 `.dev/{slug}/`를 쓰고(기능별 격리), 활성 slug를 `.dev/.active`에 기록한다 — 훅·라우팅·verify가 이 포인터로 활성 작업의 state.md를 찾는다(`.active` 부재·공백 시 `.dev/trunk/` 폴백).** | Step 6.5 |
| `BASE_BRANCH` | 베이스 브랜치 (예: `main`, `develop`). SVN은 미사용 | Step 2 |
| `DIFF_FILE` | `${DEV_DIR}/diff.txt`. Diff 수집 규칙에 따라 phase-implement(자기점검)·phase-review·phase-complete가 갱신 | — |
| `DOMAIN_CONTEXT` | `context/*/PROJECTS.md` 매칭으로 로드된 도메인 용어(glossary)와 아키텍처 정보. 매칭되지 않으면 빈 상태 | Step 3.1 |
| `REFERENCES` | `references/` 디렉토리를 탐색해 수집한 외부 규격 문서 목록(파일 경로 + 한줄 설명). 디렉토리가 없으면 빈 상태이며, 빈 상태이면 에이전트 프롬프트에 포함하지 않는다 | Step 3.1 |
| `MODEL_PROFILE` | `standard`/`eco`. state.md의 `model-profile`에 기록. 디스패치 적용 규칙은 아래 "모델 프로파일" 섹션 | Step 1.5 |

- Agent에게 `PROJECT_ROOT` 경로를 항상 전달하여 파일 도구(Read/Write/Edit/Glob/Grep)의 기준점으로 사용하게 한다.
- 빌드/테스트 명령(`./gradlew`, `npm`, `pytest` 등)을 `PROJECT_ROOT`에서 실행한다. `PROJECT_ROOT`가 기본값 `./`이면 **bare 명령**으로 실행한다 (예: `npm test`, `./gradlew build`) — `allowed-tools`의 prefix 패턴(`Bash(npm *)` 등)과 매칭되어 권한 프롬프트가 뜨지 않는다. `./`가 아닌 경우에만 서브셸 `(cd ${PROJECT_ROOT} && <cmd>)`로 감싼다 — 이 형태는 `(cd`로 시작하여 prefix 패턴과 매칭되지 않으므로 권한 프롬프트가 뜰 수 있다.
```

- [ ] **Step 2: `### Context Slicing 규칙` 절을 교체한다**

절 제목부터 `### 병렬 실행 규칙` 직전까지를 아래로 바꾼다. 굵은 인용 지시문은 원문과 글자까지 같아야 한다.

```markdown
### Context Slicing 규칙
설계서와 PRD를 Agent에게 전달할 때 역할에 필요한 섹션만 전달한다. 모든 디스패치에 프로젝트 루트 경로를 포함한다. 입력 크기가 `.claude/config.json`의 `contextLimits`를 초과하면 우선순위가 낮은 섹션부터 요약 또는 생략한다.

| 에이전트 (단계) | 전달 입력 |
|---|---|
| product-owner (PRD 작성) | ARGS[0] + 코드 맵 + 프로젝트 타입/구조 + DOMAIN_CONTEXT (있으면) + **"AC는 반드시 Given-When-Then 형식. 자동 테스트로 변환 가능해야 함"** 지시 |
| product-owner (인수 검증) | PRD의 "요구사항" + "수용 기준" + diff 파일 경로 (`DIFF_FILE`) + 코드 맵 |
| architect (설계) | PRD 전체 + 코드 맵 + 프로젝트 타입/구조/컨벤션 + DOMAIN_CONTEXT (있으면) + REFERENCES (있으면) + **"각 컴포넌트의 테스트 가능성(의존성 주입, 인터페이스 격리)을 고려"** 지시 |
| design-critic (설계 비판) | 설계서 초안 + PRD + 코드 맵 |
| test-architect (testability 평가) | 설계서 + PRD의 "수용 기준" + 코드 맵 + **"각 컴포넌트별 단위/통합 테스트 전략 명시 + testability score 1-10 산정"** 지시 |
| red-writer (RED — 코드 격리) | AC (Given-When-Then 시나리오 — 핵심 모드이면 ac.md의 AC) + 설계서의 testability 섹션 (핵심 모드는 없음 — 기존 테스트 스타일만 근거) + 기존 테스트 스타일. **기존 프로덕션 코드는 절대 포함하지 않는다** (격리 — 위반 여부는 verify_red가 "참조한 파일" 자기신고로 검증). "테스트만 작성. 프로덕션 코드 작성 금지" 지시. **UI 태스크에만** `FRONTEND_TESTING_PATH`(`references/frontend-testing.md`)를 추가 전달한다 — 백엔드 전용 태스크에 넣으면 프롬프트만 불어난다 |
| implementer (IMPLEMENT) | RED report 경로 (reports/t{N}-red.md) + 설계서 인터페이스(대상 시그니처만) + focused 테스트 명령 + report 파일 경로. **PRD 전체나 설계서 전체는 전달하지 않는다** (입력 범위 제한 — red-writer 수준의 코드 차단이 아니다. implementer는 구현을 위해 기존 코드를 Read할 수 있다). "최소 코드로 통과 후 GREEN 유지 정리. 테스트 수정 금지. focused만 실행" 지시 |
| reviewer (통합 리뷰 — Part 1→Part 2 내부 순서) | PRD의 "요구사항"+"수용 기준" + 설계서의 "변경 범위" + diff 파일 경로(DIFF_FILE) + 코드 맵 + 프로젝트 컨벤션 + 테스트 품질 기준 파일 경로. **"Part 1 verdict 선행. 테스트 재실행 금지"** 지시 |
| security-auditor (통합 감사, reviewer와 병렬) | PRD 전체 + 설계서 전체 + diff 파일 경로 (`DIFF_FILE`) + 코드 맵 + REFERENCES (있으면) |
| gx-verify (스킬, 완료 게이트) | phase-complete Step -1에서 `Skill("oh-my-gx:gx-verify")`로 호출. config.json의 projectTypes 기반으로 테스트/빌드 명령을 직접 실행 |
| researcher (독립 조사) | 조사 요청 + 코드 맵 (있으면) |
| hacker (제약 우회) | 정체 상황 설명 (에러 메시지, 시도한 접근) + 코드 맵 |
| simplifier (복잡도 제거) | 정체 상황 설명 + 설계서 + PRD + 코드 맵 |

Deprecated(~~coder~~ → red-writer/implementer로 재편, ~~qa-manager~~ → reviewer로 통합)는 gx-dev 호환을 위해 파일만 남아 있으며 gx-tdd 파이프라인에서는 참조하지 않는다.
```

원문의 `#### VERIFICATION`·`#### ANALYSIS / RECOVERY` 불릿에 위 표에 없는 문장이 있으면(예: gx-verify 행의 후반 설명) 해당 셀 끝에 그대로 이어 붙인다 — 문장을 버리지 않는다.

- [ ] **Step 3: `### Agent 결과 전달 규칙 (컨텍스트 경량화)` 절을 교체한다**

절 제목부터 다음 `### ` 제목 직전까지를 아래로 바꾼다. 원문 마지막 문단("이후 Phase에서 이전 산출물이 필요하면 …")은 그대로 유지한다.

```markdown
### Agent 결과 전달 규칙 (컨텍스트 경량화)

| 상황 | 사용자에게 보이는 것 |
|---|---|
| Q&A Phase (requirements, design) 첫 표시 | Agent 출력 **전문** — 사용자가 산출물을 검토할 수 있도록. Phase 파일의 구체적 표시 규칙이 우선 |
| Q&A Phase 완료 보고 | 확정 산출물은 파일에 저장하고 **요약만** ("PRD 확정. ${DEV_DIR}/prd.md에 저장됨") |
| Q&A 없는 Phase (implement, review, complete) | Agent 출력의 **요약만**. 전문은 파일 저장 또는 변수 보관 |
| implement Phase의 인계 | **report 파일 경로로만** 한다 — red-writer·implementer는 전문을 ${DEV_DIR}/reports/t{N}-*.md에 Write하고 상태(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)와 15줄 이내 요약만 반환한다 |
```

- [ ] **Step 4: 검증**

Run: `for s in 'AC는 반드시 Given-When-Then 형식. 자동 테스트로 변환 가능해야 함' '각 컴포넌트의 테스트 가능성(의존성 주입, 인터페이스 격리)을 고려' '각 컴포넌트별 단위/통합 테스트 전략 명시 + testability score 1-10 산정' 'Part 1 verdict 선행. 테스트 재실행 금지' '기존 프로덕션 코드는 절대 포함하지 않는다' '협업 공유 대상' ':(exclude).dev' 'model: "sonnet"' 'architect는 eco에서도 opus'; do grep -qF "$s" .claude/skills/gx-tdd/SKILL.md || echo "MISSING: $s"; done; wc -c .claude/skills/gx-tdd/SKILL.md`
Expected: `MISSING` 없음, SKILL.md가 **58,000B 이하**. 초과하면 Step 1~3의 표에서 설명 셀을 더 줄이되 굵은 지시문·판별 키·경로는 유지한다.

Run: `bash scripts/lint-consistency.sh`
Expected: 31/31 통과.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md
git commit -F - <<'MSG'
docs: gx-tdd Context Slicing·작업 경로·결과 전달 규칙을 표로 압축한다
MSG
```

---

### Task 5: 바이트 예산 린트 [32/32] 추가와 분모 갱신

**Files:**
- Modify: `scripts/lint-consistency.sh` — 헤더 검사 항목 주석 목록, `[31/31]` 블록 뒤에 새 블록, 분모 31→32 전역 치환
- Modify: `.claude/rules/release.md`, `.claude/rules/harness-codex.md`, `.claude/skills/gx-tdd/SKILL.md`, `.claude/skills/gx-dev/SKILL.md`, `README.md` 등 `[N/31]`을 인용하는 파일 전부 (린트 `[31]`이 목록을 알려준다)

**Interfaces:**
- Consumes: Task 1~4가 만든 크기 (SKILL.md ≤ 58,000B, phase-setup.md ≤ 22,000B)
- Produces: 린트 `[32/32] gx-tdd 지시문 바이트 예산`

- [ ] **Step 1: 새 검사를 스크립트 끝의 `[31/31]` 블록 **뒤**에 추가한다 (분모는 아직 31로 쓴다 — Step 3에서 한꺼번에 치환)**

```bash
echo "[32/31] gx-tdd 지시문 바이트 예산"
# 오케스트레이터가 사이클마다 읽는 파일의 상한. 설계: docs/specs/2026-09-07-tdd-density-rhythm-design.md D3
for spec in ".claude/skills/gx-tdd/SKILL.md:58000" ".claude/skills/gx-tdd/phases/phase-setup.md:22000"; do
  f=${spec%%:*}; max=${spec##*:}
  [ -f "$f" ] || { fail "예산 대상 파일 부재: $f"; continue; }
  sz=$(wc -c <"$f" | tr -d ' ')
  [ "$sz" -le "$max" ] || fail "지시문 예산 초과: $f ${sz}B > ${max}B (추출·압축·조건부 로드로 줄일 것)"
done
[ "$FAIL" -eq 0 ] && ok "SKILL.md ≤ 58000B · phase-setup.md ≤ 22000B"
```

스크립트 헤더의 검사 항목 주석 목록(`sed -n '1,60p' scripts/lint-consistency.sh`로 확인)에 `[31/31]` 항목 아래 같은 형식으로 `[32/31] gx-tdd 지시문 바이트 예산`을 한 줄 추가한다.

- [ ] **Step 2: 변이 시험으로 검출력을 확인한다 (RED)**

Run: `sed -i 's|SKILL.md:58000|SKILL.md:1000|' scripts/lint-consistency.sh && bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `지시문 예산 초과: .claude/skills/gx-tdd/SKILL.md …B > 1000B`로 FAIL, exit 1.

Run: `sed -i 's|SKILL.md:1000|SKILL.md:58000|' scripts/lint-consistency.sh && grep -c 'SKILL.md:58000' scripts/lint-consistency.sh`
Expected: `1`.

- [ ] **Step 3: 분모를 32로 올린다**

```bash
sed -i 's|/31\]|/32]|g' scripts/lint-consistency.sh
grep -rlE '\[[0-9]+/31\]' .claude README.md --include=*.md | xargs -r sed -i 's|/31\]|/32]|g'
grep -rnE '\[[0-9]+/31\]' .claude README.md scripts --include=*.md --include=*.sh | grep -v worktrees
```
Expected: 마지막 grep 출력 없음 (`docs/`·`CHANGELOG.md`는 대상이 아니다).

- [ ] **Step 4: 검증 (GREEN)**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 32/32 통과. `[31/32]`가 크로스레퍼런스 정합을, `[32/32]`가 예산을 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add scripts/lint-consistency.sh .claude README.md
git commit -F - <<'MSG'
feat: 린트 [32] gx-tdd 지시문 바이트 예산을 추가한다
MSG
```

---

### Task 6: 골든 시나리오 S37과 v1.26.2 릴리스 준비

**Files:**
- Modify: `tests/golden-scenarios.md` — 시나리오 표 마지막 행 뒤에 S37, 기록 절의 `N/36` → `N/37`
- Modify: `CHANGELOG.md` — 상단에 v1.26.2 절
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` — version `1.26.1` → `1.26.2`

**Interfaces:**
- Consumes: Task 1~5 결과
- Produces: 없음

- [ ] **Step 1: 골든 시나리오 행을 추가한다**

`tests/golden-scenarios.md`의 시나리오 표에서 S36 행 바로 아래에 추가한다 (열 구성은 S36과 같다).

```markdown
| S37 | 새 요청(ARGS 있음)이며 `--resume`·`--work`·W-토큰이 없는 gx-tdd 실행 | `/gx-tdd 알림 임계값 검증 TDD로 구현해줘` | phase-setup이 `phases/setup-resume.md`·`phases/setup-work.md`를 **Read하지 않고** Step 1로 진입한다 (도구 호출 기록에 두 파일이 없음). `--resume`으로 재실행하면 `setup-resume.md`만 Read한다 |
```

기록 절의 `골든 시나리오: N/36 통과`를 `골든 시나리오: N/37 통과`로 바꾼다.

- [ ] **Step 2: CHANGELOG 상단에 절을 추가한다**

```markdown
## v1.26.2 (2026-09-07)

gx-tdd 오케스트레이터가 사이클마다 읽는 지시문을 줄인다. 실행 규칙·판별 키·지시 문구는 그대로이며, 실행 중 읽히지 않던 텍스트를 옮기고 산문을 표로 바꿨을 뿐이다. 설계: `docs/specs/2026-09-07-tdd-density-rhythm-design.md`.

- **변경 — 유지보수 노트 추출**: SKILL.md의 하네스 적응 표는 `references/harness-adaptation.md`로, 의도적 중복 목록 19항목은 `references/maintenance-notes.md`로 옮겼다. 전자는 Codex 실행 시 포인터를 따라 읽고, 후자는 스킬을 수정할 때만 읽는다.
- **변경 — 조건부 로드**: phase-setup의 재개 감지(Step 0)와 작업 계획(3.0.5·5.5·되돌림) 절을 `phases/setup-resume.md`·`phases/setup-work.md`로 분리했다. `--resume`·`--work`가 없는 기본 경로에서는 읽히지 않는다.
- **변경 — 표로 압축**: state.md 스키마 예시, Context Slicing, 작업 경로 기준, Agent 결과 전달 규칙을 표로 바꿨다. 굵은 지시문·판별 키·경로는 원문 그대로다.
- **추가 — 린트 [32] 지시문 바이트 예산**: SKILL.md ≤ 58,000B, phase-setup.md ≤ 22,000B를 고정한다. 변이 시험으로 검출을 확인했다.
```

- [ ] **Step 3: 버전 세 곳을 올린다**

```bash
sed -i 's|"version": "1.26.1"|"version": "1.26.2"|' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
```
Expected: 세 파일 모두 `1.26.2`. marketplace.json은 `plugins[0].version` 자리다.

- [ ] **Step 4: 검증**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 32/32 통과 (`[1/32]`이 버전 4중 일치 확인), 훅 테스트 통과.

- [ ] **Step 5: 커밋**

```bash
git add tests/golden-scenarios.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json
git commit -F - <<'MSG'
docs: v1.26.2 릴리스 준비 — 골든 시나리오 S37과 CHANGELOG
MSG
```

---

## 완료 기준

- `wc -c` 기준 SKILL.md ≤ 58,000B, phase-setup.md ≤ 22,000B, 린트 32/32·훅 테스트 통과.
- `grep -c '드리프트 주의' .claude/skills/gx-tdd/SKILL.md` = 0, `grep -c spawn_agent .claude/skills/gx-tdd/SKILL.md` = 0.
- 새 파일 4개(`references/harness-adaptation.md`, `references/maintenance-notes.md`, `phases/setup-resume.md`, `phases/setup-work.md`)가 존재하고 린트 `[15/32]`가 Read 대상으로 확인한다.
- 후속 계획 `2026-09-07-tdd-session-implement.md`는 이 계획이 main에 머지된 뒤 착수한다 (분모 32를 전제).
