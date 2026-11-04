---
name: gx-cross-review
description: gx-tdd 개발 완료 후 '교차 리뷰'·'교차 검증'·'cross review'·'크로스 리뷰' 요청에 사용한다. PRD·설계·위험 기록을 기준으로 구현의 충실도를 검토한다.
argument-hint: ""
allowed-tools:
  # VCS
  - Bash(git *)
  # codex 호출
  - Bash(node *)
  - Bash(which *)
  - Bash(codex *)
  # 파일 시스템 (읽기/조회)
  - Bash(test *)
  - Bash(mkdir *)
  - Bash(ls *)
  - Bash(cat *)
  - Bash(wc *)
  - Bash(head *)
  - Bash(tail *)
  - Bash(find *)
  - Bash(echo *)
  - Bash(basename *)
  - Bash(dirname *)
  # 도구
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# 구현 교차 검토

gx-tdd 실행이 남긴 개발 산출물(PRD, 설계서, Trust Ledger, 자기점검, 코드 맵)을 기준으로 구현의 충실도를 교차 검증한다. 일반 `/codex:review`와 달리 **"코드 품질"이 아닌 "산출물 약속 대비 충실도"**를 검증한다.

항상 한국어로 응답한다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("../gx-work/references/codex-runtime.md")`로 공통 실행 규약을 읽고, 이 스킬의 절차·게이트를 유지한다. 상대경로는 이 SKILL.md 위치 기준이다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → 공통 codex-runtime의 질문 대기 계약으로 옮긴다. 실제 모드·용도가 허용하는 `request_user_input`·`request_user_input_async` 또는 자연어를 사용한다. 필수 질문은 pending 상태를 저장하고 실제 답변·결정 기록 전 다음 단계로 넘어가지 않는다. async 반환은 답변이 아니며 본문·선택지를 표시한다.
- `Task(subagent_type="oh-my-gx:{name}")` → 공통 실행 규약의 `codex-roles/index.json`과 역할 본문·도구 제약을 읽어 `spawn_agent`의 message에 태스크 prompt 전문과 함께 전달한다. 격리 시 `fork_turns: "none"`을 쓴다.

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.

## 자동 수정 금지 원칙

1. advisor 응답에 Critical 항목이 있어도 즉시 coder를 호출하지 않는다.
2. 모든 수정은 Step 5의 AskUserQuestion을 거쳐 사용자가 명시적으로 승인한 항목만 수행.
3. coder는 "수정" 모드로만 호출하고, 신규 기능 추가나 리팩토링은 위임 범위 밖.
4. 승인된 범위만 수정하고 리뷰 결과를 자동으로 구현 작업으로 전환하지 않는다.

---

## 정체성

> **cross-review의 본질 = "산출물 대비 충실도 검증"**.
> 모델 다양성(codex 활용)은 부가 차별점이지 단독 정체성은 아니다.

| advisor | 차별점 |
|---------|--------|
| `codex` | 산출물 기반 검증 미션 + 다른 모델 관점 (이중 차별) |
| `native` | 현재 하네스의 내부 역할 에이전트로 산출물 기반 검증 |
| `claude` | Claude Code 호스트에서 기존 역할 리뷰 (Codex 호스트에서는 미지원) |

기본 `/codex:review`와의 비교:

| 기준 | `/codex:review` | `/gx-cross-review` |
|------|----------------|---------------------|
| 입력 | git diff | diff + PRD + 설계 + Trust Ledger + references |
| 검증 미션 | 일반 코드 품질 | AC 충족 + 설계 범위 이탈 + 신규 위험만 |
| 중복 제거 | 없음 | trust-ledger·self-check 기반 차단 |
| 출력 정규화 | codex 자체 포맷 | oh-my-gx Trust Ledger 호환 |
| 한국어 | 영어 기본 | 한국어 강제 |

## 인자

`ARGS[0]`은 비워두는 것이 기본이다. 옵션 플래그만 지원한다:

- `--advisor codex|native|claude`: advisor 선택 (생략 시 사용자에게 묻는다).
- `--dev-dir <path>`: 산출물 디렉토리 직접 지정 (생략 시 현재 브랜치 기준 자동 추론).
- `--base <branch>`: 베이스 브랜치 직접 지정 (생략 시 자동 감지).
- `--scope diff|stat`: diff 수집 모드 (기본: diff. 변경이 큰 경우 stat).

## 사용 시점

- **권장**: `/gx-work` 완료 후 단발 호출. PR 생성 직전 추가 검증으로 사용.
- **비권장**: `/gx-work` 파이프라인 도중 호출. 자기점검·phase-review와 중복된다.

## 공유 변수

다른 스킬과 동일한 명명 규칙을 따른다 (gx-dev "공유 규칙" 참조):

- `BRANCH`: `git branch --show-current` 결과.
- `PROJECT_ROOT`: `git rev-parse --show-toplevel`로 확인한 소비 프로젝트의 절대경로.
- `BRANCH_SLUG`: `${BRANCH}`에서 `/`를 `-`로 치환한 값.
- `DEV_DIR`: 기본값 `.dev/${BRANCH_SLUG}`. `--dev-dir`로 오버라이드 가능.
- `BASE_BRANCH`: 자동 감지 또는 `--base`로 지정.
- `ADVISOR`: `codex`, `native`, `claude`. Step 1에서 결정.
- `GX_PLUGIN_ROOT`: 설치된 GX 플러그인 루트의 확인된 절대경로. `scripts/codex-run.py` 확인에 사용.
- `DIFF_FILE`: `${DEV_DIR}/diff.txt`. Step 2-2에서 갱신.
- `ARTIFACTS`: 로드된 산출물 목록 (prd/design/trust-ledger/self-check/codemap/references).
- `RESULT_FILE`: `${DEV_DIR}/cross-review.md`. Step 4 산출물.
- `RAW_FILE`: `${DEV_DIR}/cross-review.raw.md`. advisor 원시 응답.
- `PROMPT_FILE`: `${DEV_DIR}/cross-review-prompt.md`. codex 호출용 prompt 본문 (3a-1).
- `BATCH_MODE`: `none | AUTO_FIX | AUTO_SKIP`. Step 5 일괄 처리 상태.

> **오케스트레이터 변수 추적**: 위 변수들은 셸 환경변수가 아니라 **오케스트레이터(LLM)가 컨텍스트로 들고 다니는 값**이다. Bash 결과(`git branch --show-current` 등)를 받아 후속 Bash/Task/Read 호출에 직접 치환해서 전달한다. 셸 변수처럼 export 되지 않으므로 매 호출에 명시적으로 값을 적어 넣는다.

---

## Step 0: 환경 감지

오케스트레이터가 직접 수행한다 (에이전트 호출 없음).

### 0-0. ARGS 파싱

`ARGS[0]`을 공백으로 토큰 분리하여 다음 옵션을 추출한다. 인식하지 못한 토큰은 무시하고 사용자에게 한 번 알린다.

| 옵션 | 형식 | 저장 변수 | 허용 값 |
|------|------|----------|---------|
| `--advisor` | `--advisor codex` 또는 `--advisor=codex` | `${ADVISOR}` | `codex`, `native`, `claude` |
| `--dev-dir` | `--dev-dir <path>` 또는 `--dev-dir=<path>` | `${DEV_DIR}` | 디렉토리 경로 |
| `--base` | `--base main` 또는 `--base=main` | `${BASE_BRANCH}` | 브랜치명 |
| `--scope` | `--scope diff` 또는 `--scope=stat` | `${SCOPE}` | `diff`(기본), `stat` |

알 수 없는 옵션이 있으면:
```
"인식하지 못한 옵션을 무시했습니다: <token>. 지원 옵션: --advisor, --dev-dir, --base, --scope"
```

### 0-1. 브랜치/디렉토리 결정

1. `git rev-parse --show-toplevel`로 소비 프로젝트의 `${PROJECT_ROOT}` 절대경로를 확인한다. 실패하면 Git 프로젝트가 아니므로 중단한다. 이후 Git·helper 명령은 이 경로를 작업 위치로 쓴다.
2. `git branch --show-current` → `${BRANCH}`. 빈 문자열(detached HEAD)이면 중단:
   ```
   "현재 detached HEAD 상태입니다. 브랜치 위에서 다시 호출해주세요."
   ```
3. `${BRANCH_SLUG}` = `${BRANCH}`에서 `/` → `-`.
4. `--dev-dir`이 지정되지 않았으면 `${DEV_DIR}` = `.dev/${BRANCH_SLUG}`.
5. 상대 `${DEV_DIR}`은 `${PROJECT_ROOT}` 기준 절대경로로 정규화한다 (`--dev-dir`로 이미 절대경로가 주어졌으면 유지). `mkdir -p ${DEV_DIR}` 실행 (없으면 생성). 이후 `${PROMPT_FILE}`·`${RAW_FILE}`·events도 이 절대 `${DEV_DIR}` 아래에서 계산해 helper에 전달한다.

### 0-2. 베이스 브랜치 결정

`--base`가 지정되지 않았으면 다음 우선순위로 결정한다:

1. **state.md 우선**: `${DEV_DIR}/state.md`가 존재하면 Read하여 `base:` 필드를 추출하여 `${BASE_BRANCH}`로 사용한다. `/gx-work`가 phase-setup에서 결정한 값과 동일하게 정렬된다 (재질문 없음).
2. **자동 감지** (state.md 없거나 base 필드 없을 때, gx-dev "베이스 브랜치 감지" 규칙과 동일):
   - `git branch --list main master develop`로 존재하는 브랜치 확인.
   - 2개 이상이면 AskUserQuestion으로 선택:
     ```
     AskUserQuestion(
       questions: [{
         question: "베이스 브랜치를 선택해주세요.",
         header: "베이스 브랜치",
         options: [
           { label: "main", description: "기본 브랜치" },
           { label: "develop", description: "개발 브랜치" }
         ],
         multiSelect: false
       }]
     )
     ```
   - 1개면 자동 선택.
   - 0개면 사용자 입력 요청.

### 0-3. 산출물 점검

다음 5종 산출물의 존재 여부를 확인한다:

| 산출물 | 경로 | 검증 미션 |
|--------|------|-----------|
| prd | `${DEV_DIR}/prd.md` | "[Must] AC 모두 충족됐는가?" |
| ac (core) | `${DEV_DIR}/ac.md` | "AC 모두 충족됐는가?" (핵심 모드의 AC 명세 — prd.md의 경량 대체물) |
| design | `${DEV_DIR}/design.md` | "변경 범위 외 파일 수정이 있는가?" |
| summary (core) | `${DEV_DIR}/summary.md` | "변경 요약·Gate 증거 대조" (핵심 모드) |
| trust-ledger | `${DEV_DIR}/trust-ledger.md` | "이미 보고된 항목 제외, 신규 위험만" |
| self-check | `${DEV_DIR}/self-check.md` | "자기점검 Warning/Info 중복 보고 금지" |
| codemap | `${DEV_DIR}/codemap.md` | "탐색 부담 절감용 핵심 파일 목록" |

**판정 규칙**:
- prd, ac, design 셋 다 없으면 → **fallback 모드** (아래 "산출물 부재 fallback" 섹션 진입).
- 셋 중 하나라도 있으면 → cross-review 본 모드 진행. **AC 명세는 prd.md 우선, 없으면 ac.md(core)를 사용한다.**
- summary/trust-ledger/self-check/codemap은 있으면 활용, 없어도 진행.

또한 프로젝트 루트의 `references/` 디렉토리를 점검한다. 존재하면 `ARTIFACTS.references`에 파일 목록을 채운다.

### 0-4. 환경 보고

사용자에게 감지 결과를 한 번 보여준다:
```
## gx-cross-review 환경
- 브랜치: feat/login (base: main)
- DEV_DIR: .dev/feat-login
- 산출물:
  - prd.md ✓
  - design.md ✓
  - trust-ledger.md ✓
  - self-check.md ✓ (Warning 3건, Info 1건)
  - codemap.md ✓ (15개 파일)
  - references/ (2개 파일)
```

산출물(prd·ac·design)이 셋 다 없으면:
```
## gx-cross-review 환경
- 브랜치: feat/login (base: main)
- DEV_DIR: .dev/feat-login
- 산출물: prd.md/design.md 모두 없음 → fallback 모드
```

---

## Step 1: advisor 선택

`--advisor` 플래그가 지정되지 않았으면 AskUserQuestion으로 묻는다:

```
AskUserQuestion(
  questions: [{
    question: "어떤 advisor로 교차 검증을 수행할까요?",
    header: "advisor 선택",
    options: [
      { label: "codex (Recommended)", description: "Codex CLI read-only 세션으로 교차 검증" },
      { label: "native", description: "현재 하네스의 qa-manager + security-auditor 역할로 검증" },
      { label: "claude", description: "Claude Code 호스트에서 기존 역할 리뷰 (Codex 호스트 미지원)" }
    ],
    multiSelect: false
  }]
)
```

선택 결과를 `${ADVISOR}`에 저장한다.

### 1-1. advisor 환경 사전 점검

ADVISOR가 codex인 경우만 `Read("references/codex-preflight.md")`로 CLI·helper·인증·실행 제약을 확인한다. 자동 설치·인증·권한 우회·advisor 자동 전환은 하지 않는다. native/claude는 codex 점검을 건너뛴다.

**Codex 호스트에서 claude를 선택하면 Claude 실행 경로 미지원으로 종료하고 native 또는 codex를 명시적으로 선택하도록 안내한다.** 이름만 자동으로 바꾸지 않는다.

---

## Step 2: 산출물 컨텍스트 빌더

오케스트레이터가 직접 수행한다.

### 2-1. 우선순위 슬라이싱 규칙

advisor의 컨텍스트 한계를 고려하여 다음 우선순위로 산출물을 슬라이싱한다:

| 순위 | 항목 | 추출 방법 | 비고 |
|------|------|----------|------|
| 1 | PRD "수용 기준" | `prd.md`에서 `### 수용 기준` 섹션만 추출. **prd.md가 없고 ac.md(core)가 있으면 ac.md의 `## 요구사항 (AC)` 섹션을 대신 추출** | 약속 대조용 |
| 1 | 설계 "변경 범위" + "구현 순서" | `design.md`에서 해당 섹션 추출. **핵심 모드는 design.md 대신 summary.md의 "변경 파일" 표를 사용** | 범위 이탈 검증용 |
| 1 | diff | Step 2-2에서 수집한 `${DIFF_FILE}` | 검증 대상 |
| 2 | trust-ledger 항목 목록 | `trust-ledger.md` 전체 (보통 짧음) | 중복 차단용 |
| 2 | self-check 발견 사항 | `self-check.md` 전체 | 중복 차단용 |
| 3 | codemap 핵심 파일 | `codemap.md`의 "핵심 파일" 섹션만 | 탐색 가이드용 |
| 4 | references 목록 | `references/` 파일명 + 첫 200자 요약 (`head -c 200 ${file}` 또는 Read의 `limit: 5`) | 표준 위반 검증용 |

**컨텍스트 폭발 방지**:
- 각 산출물 추출 후 합산 토큰을 추정한다 (한국어 기준 1줄 ≈ 30자 ≈ 30~40토큰 가정. 영어 위주면 1줄 ≈ 8토큰).
- 합산이 60,000 토큰을 넘으면:
  - 4순위(references) → 파일명만 남기고 본문 제거.
  - 3순위(codemap) → 핵심 파일 5개만.
  - 2순위(trust-ledger/self-check) → CRITICAL/Critical만.
- 그래도 초과하면 사용자에게 안내:
  ```
  산출물이 너무 큽니다. --scope stat으로 재호출하시거나
  특정 산출물을 임시로 비워주세요.
  ```

### 2-2. diff 수집

`Diff 수집 규칙`에 따라 diff를 파일에 직접 리다이렉트한다 (메인 컨텍스트 절약).

```bash
mkdir -p "${DEV_DIR}"
git diff "$(git merge-base HEAD "${BASE_BRANCH}")" > "${DIFF_FILE}"
# untracked 파일은 git index에 없어 위 diff에 포함되지 않으므로 별도 합산
git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do
  git diff --no-index --binary /dev/null "$f" 2>/dev/null
done >> "${DIFF_FILE}"
```
> `git diff <merge-base-commit>`는 working tree와 merge-base의 차이를 한 번에 보여주므로 staged + unstaged + 커밋된 변경은 모두 포함되지만, **`git add` 전 untracked 파일은 누락**된다. `/gx-work` 직후 `git add` 전에 cross-review를 호출하는 흐름을 지원하기 위해 `git ls-files --others --exclude-standard`로 untracked 목록을 별도 수집하여 `git diff --no-index`로 신규 파일 diff를 합산한다.

`wc -l < "${DIFF_FILE}"`로 줄 수 확인. **500줄 이상**이거나 `${SCOPE}` == `stat`인 경우:
```bash
git diff "$(git merge-base HEAD "${BASE_BRANCH}")" --stat > "${DIFF_FILE}"
echo "---" >> "${DIFF_FILE}"
echo "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라." >> "${DIFF_FILE}"
```

### 2-3. 컨텍스트 통합

위 우선순위에 따라 산출물을 합산하여 advisor에 전달할 prompt를 구성한다.
codex는 prompt 파일에 저장한 후 인자로 전달, claude는 Task prompt에 인라인으로 포함한다.

---

## Step 3: advisor별 호출

### 3-A. codex 경로

ADVISOR가 codex인 경우만 `Read("references/advisor-codex.md")`의 prompt 빌드·read-only 호출·응답 검증을 수행한다. 다른 advisor 자료는 읽지 않는다. 종료 코드 실패·빈 응답은 결과 정규화/수정 없이 중단한다.

### 3-B. native/claude 역할 경로

ADVISOR가 native 또는 Claude Code 호스트의 claude인 경우만 `Read("references/advisor-native.md")`의 역할별 미션·호출·통합을 수행한다. Codex 호스트의 claude 미지원 중단은 Step 1을 따른다.

---

## Step 4: 결과 정규화 + 저장

advisor 결과를 받은 경우 `Read("references/result-format.md")`의 표준 포맷·파일 저장·사용자 요약을 수행한다. 역할 호출에 표준 포맷이 필요하면 같은 참조를 호출 전에 읽어 전달한다. 원시 응답도 보존하고 사용자에게 전문 대신 요약과 파일 경로를 보고한다.

---

## Step 5: 발견 항목 처리 (수정 위임)

자동 수정하지 않는다. 발견 항목이 있으면 `Read("references/finding-actions.md")`로 처리 대상 식별·사용자 승인·승인된 수정·선택적 재확인을 수행한다. 발견이 없으면 이 참조를 읽지 않는다.

---

## 산출물 부재 fallback

prd.md·ac.md·design.md가 셋 다 없을 때만 `Read("references/fallback.md")`를 읽어 제한을 설명하고 진행/중단을 확인한다. 승인 전 일반 리뷰로 전환하지 않는다.

---

## 한국어 강제 규칙

1. **prompt 강제**: codex prompt의 `<language>` 블록, claude prompt의 명시적 한국어 지시.
2. **응답 검증**: 응답의 첫 50줄에서 한국어 문자(가-힣) 비율이 20% 미만이면 한국어 정규화 단계를 추가.
3. **사용자 출력**: 사용자에게 표시하는 모든 메시지는 한국어로 작성. 고유명사·기술 용어는 영문 허용.

---

## 에러 처리

- **codex 호출 실패** (종료 코드 ≠ 0): stderr 마지막 20줄 표시 후 중단. 폴백 advisor 자동 전환은 하지 않는다.
- **claude Task 실패**: 어느 한 Task가 실패하면 성공한 결과만으로 정규화. 사용자에게 부분 결과임을 명시.
- **컨텍스트 초과**: Step 2-1의 슬라이싱으로 60,000 토큰 이하로 압축. 그래도 초과하면 사용자에게 `--scope stat` 사용 안내.
- **diff 빈 파일**: 변경사항이 없으면 "변경사항이 없습니다." 표시 후 즉시 종료.
- **hook 차단**: GX 훅이 실행을 차단하면 차단 이유를 보고하고 중단한다. 훅 신뢰·검증 우회로 재시도하지 않는다.

---

## 진행 상태 추적

`${DEV_DIR}/cross-review-state.md`에 다음을 기록한다 (간단한 형식):

```yaml
status: in_progress | completed | aborted
advisor: codex | native | claude
execution_harness: Codex CLI | current | Claude Code
actual_model: 확인된 모델명 또는 미확인
started: 2026-05-04T10:30:00Z
completed: 2026-05-04T10:35:00Z
findings:
  ac_total: 5
  ac_met: 4
  range_violation: 1
  critical: 1
  warning: 2
  info: 3
  references_violation: 0
processed:
  fixed: 3
  skipped: 4
```

`--resume`은 지원하지 않는다 (단발 호출 전용 스킬). 재실행하려면 처음부터 다시 호출.

---

## 다른 스킬과의 관계

- `/gx-work`: cross-review의 산출물(prd/design/trust-ledger)을 생성한다. 선행 의존.
- `/gx-tdd`: 산출물 파일 구조(prd/design/trust-ledger)가 동일하므로 gx-tdd 완료물에도 그대로 동작한다. 이때 claude advisor가 호출하는 qa-manager는 "gx-tdd 파이프라인 내부 호출 금지" 대상이 아니다 — cross-review는 파이프라인 완료 후의 독립 스킬이므로 허용된다 (gx-tdd 내부 리뷰는 reviewer(spec+quality 통합 1석)가 담당하며, cross-review는 그와 별개의 사후 검증 층이다).
- `/codex:review`: 일반 코드 리뷰. cross-review와 별개로 사용 가능.
- `/codex:adversarial-review`: cross-review의 codex 경로보다 더 공격적인 비판이 필요하면 별도 호출.
- `/gx-commit`, `/gx-pull-request`: cross-review 후 처리한 변경사항을 커밋/PR.
