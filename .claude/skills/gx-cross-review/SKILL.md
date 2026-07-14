---
name: gx-cross-review
description: dev 산출물(PRD/설계서/Trust Ledger)을 컨텍스트로 주입한 교차 검증 리뷰를 수행한다. "교차 리뷰", "교차 검증", "cross review", "크로스 리뷰" 시 사용. /gx-dev 또는 /gx-tdd 완료 후 단발 호출 전용.
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

# gx-cross-review

`/gx-dev` 파이프라인이 만들어낸 dev 산출물(PRD, 설계서, Trust Ledger, 자기점검, 코드 맵)을 컨텍스트로 주입한 교차 검증 리뷰를 수행한다. 일반 `/codex:review`와 달리 **"코드 품질"이 아닌 "산출물 약속 대비 충실도"**를 검증한다.

항상 한국어로 응답한다.

## 정체성

> **cross-review의 본질 = "산출물 대비 충실도 검증"**.
> 모델 다양성(codex 활용)은 부가 차별점이지 단독 정체성은 아니다.

| advisor | 차별점 |
|---------|--------|
| `codex` | 산출물 기반 검증 미션 + 다른 모델 관점 (이중 차별) |
| `claude` | 산출물 기반 검증 미션 + 별도 페르소나/contract (단일 차별) |

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

- `--advisor codex|claude`: advisor 자동 선택 (생략 시 사용자에게 묻는다).
- `--dev-dir <path>`: 산출물 디렉토리 직접 지정 (생략 시 현재 브랜치 기준 자동 추론).
- `--base <branch>`: 베이스 브랜치 직접 지정 (생략 시 자동 감지).
- `--scope diff|stat`: diff 수집 모드 (기본: diff. 변경이 큰 경우 stat).

## 사용 시점

- **권장**: `/gx-dev` 완료 후 단발 호출. PR 생성 직전 추가 검증으로 사용.
- **비권장**: `/gx-dev` 파이프라인 도중 호출. 자기점검·phase-review와 중복된다.

## 공유 변수

다른 스킬과 동일한 명명 규칙을 따른다 (gx-dev "공유 규칙" 참조):

- `BRANCH`: `git branch --show-current` 결과.
- `BRANCH_SLUG`: `${BRANCH}`에서 `/`를 `-`로 치환한 값.
- `DEV_DIR`: 기본값 `.dev/${BRANCH_SLUG}`. `--dev-dir`로 오버라이드 가능.
- `BASE_BRANCH`: 자동 감지 또는 `--base`로 지정.
- `ADVISOR`: `codex` 또는 `claude`. Step 1에서 결정.
- `CODEX_COMPANION`: codex companion 스크립트 절대 경로. Step 3a에서 동적 탐색.
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
| `--advisor` | `--advisor codex` 또는 `--advisor=codex` | `${ADVISOR}` | `codex`, `claude` |
| `--dev-dir` | `--dev-dir <path>` 또는 `--dev-dir=<path>` | `${DEV_DIR}` | 디렉토리 경로 |
| `--base` | `--base main` 또는 `--base=main` | `${BASE_BRANCH}` | 브랜치명 |
| `--scope` | `--scope diff` 또는 `--scope=stat` | `${SCOPE}` | `diff`(기본), `stat` |

알 수 없는 옵션이 있으면:
```
"인식하지 못한 옵션을 무시했습니다: <token>. 지원 옵션: --advisor, --dev-dir, --base, --scope"
```

### 0-1. 브랜치/디렉토리 결정

1. `git branch --show-current` → `${BRANCH}`. 빈 문자열(detached HEAD)이면 중단:
   ```
   "현재 detached HEAD 상태입니다. 브랜치 위에서 다시 호출해주세요."
   ```
2. `${BRANCH_SLUG}` = `${BRANCH}`에서 `/` → `-`.
3. `--dev-dir`이 지정되지 않았으면 `${DEV_DIR}` = `.dev/${BRANCH_SLUG}`.
4. `mkdir -p ${DEV_DIR}` 실행 (없으면 생성).

### 0-2. 베이스 브랜치 결정

`--base`가 지정되지 않았으면 다음 우선순위로 결정한다:

1. **state.md 우선**: `${DEV_DIR}/state.md`가 존재하면 Read하여 `base:` 필드를 추출하여 `${BASE_BRANCH}`로 사용한다. `/gx-dev`가 phase-setup에서 결정한 값과 동일하게 정렬된다 (재질문 없음).
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
| ac (LIGHT) | `${DEV_DIR}/ac.md` | "AC 모두 충족됐는가?" (LIGHT 모드의 AC 명세 — prd.md의 경량 대체물) |
| design | `${DEV_DIR}/design.md` | "변경 범위 외 파일 수정이 있는가?" |
| summary (LIGHT) | `${DEV_DIR}/summary.md` | "변경 요약·Gate 증거 대조" (LIGHT 모드) |
| trust-ledger | `${DEV_DIR}/trust-ledger.md` | "이미 보고된 항목 제외, 신규 위험만" |
| self-check | `${DEV_DIR}/self-check.md` | "자기점검 Warning/Info 중복 보고 금지" |
| codemap | `${DEV_DIR}/codemap.md` | "탐색 부담 절감용 핵심 파일 목록" |

**판정 규칙**:
- prd, ac, design 셋 다 없으면 → **fallback 모드** (Step 5의 산출물 부재 fallback 진입).
- 셋 중 하나라도 있으면 → cross-review 본 모드 진행. **AC 명세는 prd.md 우선, 없으면 ac.md(LIGHT)를 사용한다.**
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

산출물 둘 다 없으면:
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
      { label: "codex (Recommended)", description: "다른 모델(GPT-5.4) 관점으로 교차 검증" },
      { label: "claude", description: "oh-my-gx의 qa-manager + security-auditor를 cross-review 미션으로 호출 (omc 의존 없음)" }
    ],
    multiSelect: false
  }]
)
```

선택 결과를 `${ADVISOR}`에 저장한다.

### 1-1. codex 환경 사전 점검 (codex 선택 시)

다음 순서로 검증한다:

1. **CLI 존재 확인**:
   ```bash
   which codex
   ```
   실패 시 안내 후 종료:
   ```
   codex CLI가 설치되어 있지 않습니다.

   설치:
     npm install -g @openai/codex

   인증:
     codex login
     또는 /codex:setup

   설치/인증 완료 후 /gx-cross-review를 다시 호출해주세요.
   ```
   자동 설치/인증은 수행하지 않는다 — 사용자 환경 침해 방지.

2. **companion 스크립트 탐색**:
   ```bash
   ls -t ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs 2>/dev/null | head -1
   ```
   결과를 `${CODEX_COMPANION}`에 저장. 빈 결과면:
   ```
   codex CLI는 있지만 codex 플러그인이 설치되지 않았습니다.

   설치:
     /plugin marketplace add openai/codex-plugin-cc
     /plugin install codex@openai-codex
     /reload-plugins

   설치 후 다시 호출해주세요.
   ```

3. **인증 상태**: companion이 자체적으로 인증을 검증하므로, 이 단계에서는 추가 점검을 하지 않는다.

claude advisor를 선택했으면 1-1을 건너뛴다.

---

## Step 2: 산출물 컨텍스트 빌더

오케스트레이터가 직접 수행한다.

### 2-1. 우선순위 슬라이싱 규칙

advisor의 컨텍스트 한계를 고려하여 다음 우선순위로 산출물을 슬라이싱한다:

| 순위 | 항목 | 추출 방법 | 비고 |
|------|------|----------|------|
| 1 | PRD "수용 기준" | `prd.md`에서 `### 수용 기준` 섹션만 추출. **prd.md가 없고 ac.md(LIGHT)가 있으면 ac.md의 `## 요구사항 (AC)` 섹션을 대신 추출** | 약속 대조용 |
| 1 | 설계 "변경 범위" + "구현 순서" | `design.md`에서 해당 섹션 추출. **LIGHT는 design.md 대신 summary.md의 "변경 파일" 표를 사용** | 범위 이탈 검증용 |
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
> `git diff <merge-base-commit>`는 working tree와 merge-base의 차이를 한 번에 보여주므로 staged + unstaged + 커밋된 변경은 모두 포함되지만, **`git add` 전 untracked 파일은 누락**된다. `/gx-dev` 직후 `git add` 전에 cross-review를 호출하는 흐름을 지원하기 위해 `git ls-files --others --exclude-standard`로 untracked 목록을 별도 수집하여 `git diff --no-index`로 신규 파일 diff를 합산한다.

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

`${ADVISOR}` == `codex`인 경우.

#### 3a-1. prompt 빌드

`${PROMPT_FILE}` (= `${DEV_DIR}/cross-review-prompt.md`)에 다음 형식으로 작성한다.

> **prompt 본문 작성 규칙**: companion이 `--prompt-file`로 파일을 직접 읽으므로 셸 인용/길이 제한은 무관하다. 다만 codex 측 prompt 파서 안정성을 위해 본문에 백틱(`` ` ``), 이스케이프되지 않은 큰따옴표(`"`), `$` 시작 토큰은 절제하고 코드 인용은 4칸 들여쓰기로 대체할 것을 권장한다.

```xml
<task>
oh-my-gx 파이프라인 산출물(PRD/설계/Trust Ledger)과 변경 코드를 교차 검증한다.
변경된 코드가 산출물의 약속을 충족하는지, 산출물에 정의되지 않은 신규 위험이 있는지 보고한다.

diff 파일: ${DIFF_FILE}
이 파일을 Read하여 변경사항을 확인한다.
</task>

<grounding_rules>
- 모든 지적은 PRD 또는 설계서의 정확한 인용으로 근거를 제시한다.
- trust-ledger.md에 이미 보고된 항목은 보고하지 않는다 (중복 금지).
- self-check.md의 Warning/Info는 중복 보고하지 않는다.
- 코드를 직접 확인하지 못한 추정은 ASSUMPTION으로 분리한다.
- PRD 자체가 코드와 일치하지 않을 가능성이 의심되면 ASSUMPTION으로 분류한다.
</grounding_rules>

<structured_output_contract>
다음 4개 섹션을 정확히 이 순서로 출력한다:

## AC 충족 매트릭스
| AC | 충족 | 근거 (파일:라인 또는 PRD 인용) |
|----|------|--------|
| AC-1 | O/X/부분 | ... |

## 설계 범위 이탈
설계서의 "변경 범위"에 명시되지 않은 파일 수정 목록.
항목별로: 파일 경로 / 변경 요약 / 이탈 사유 추정.
없으면 "이탈 없음".

## 신규 위험
trust-ledger.md에 없는 신규 risk/policy/gap/assumption만.
- [Critical/Warning/Info] [RISK/POLICY/GAP/ASSUMPTION] 항목 설명
  - 위치: 파일:라인
  - 근거: ...
  - 권고: ...

## references 위반 (해당 시)
references/ 디렉토리의 파일별로 위반 여부.
없으면 섹션 자체 생략.

## 총평
- 강점 1-2개
- Critical/Warning 합산
- 권고 사항 1줄
</structured_output_contract>

<language>
모든 출력은 한국어로 작성한다. 영어 단어는 고유명사·기술 용어에 한해 허용한다.
</language>

<artifacts>
다음 산출물을 참조한다.

### PRD 수용 기준
{prd.md의 "수용 기준" 섹션 내용}

### 설계서 변경 범위 + 구현 순서
{design.md의 해당 섹션 내용}

### 기존 Trust Ledger (이미 보고된 항목, 중복 금지)
{trust-ledger.md 전체}

### 자기점검 발견 사항 (중복 금지)
{self-check.md 전체}

### 코드 맵 (탐색 가이드)
{codemap.md의 "핵심 파일" 섹션}

### references (외부 표준)
{references 파일별 요약}
</artifacts>
```

#### 3a-2. codex 호출

```bash
node "${CODEX_COMPANION}" task --prompt-file "${PROMPT_FILE}" \
  > "${RAW_FILE}" 2>&1
```

- companion이 정식 지원하는 `--prompt-file` 플래그로 파일 경로만 전달한다. 위치 인자에 본문을 펼치지 않으므로 OS 명령줄 길이 제한(`ARG_MAX`, Windows ~32KB)을 회피한다.
- Bash 도구 호출 시 `timeout: 300000` 파라미터를 명시한다 (기본 2분으로는 부족).
- `--write` 플래그는 명시적으로 사용하지 않는다 (read-only 검증).

#### 3a-3. 응답 검증

1. 종료 코드 0 확인. 실패 시 stderr 마지막 20줄을 사용자에게 표시하고 중단.
2. `${RAW_FILE}` 줄 수 확인. 0줄이면 호출 실패로 간주.
3. 영어 응답 감지: 첫 50줄에서 한국어 문자(가-힣) 비율이 20% 미만이면 영어로 간주. 이 경우 한국어 정규화 단계를 추가:
   - 오케스트레이터가 직접 응답을 한국어로 재작성한다 (의미는 보존).

### 3-B. claude 경로

`${ADVISOR}` == `claude`인 경우.

#### 3b-1. cross-review contract

각 에이전트에 일반 phase-review와 다른 contract를 명시한다.

**Task A: qa-manager (cross-review 미션)**

`Task(subagent_type="oh-my-gx:qa-manager")` — prompt에 다음을 포함:

```
[중요] 이 호출은 일반 phase-review가 아닌 gx-cross-review이다.
일반적인 코드 품질 리뷰가 아니라, 다음 미션을 정확히 수행하라:

미션:
1. AC 충족 매트릭스 작성: PRD의 각 [Must] AC에 대해 충족 여부(O/X/부분)와 근거 파일:라인을 명시.
2. 설계 범위 이탈 점검: 설계서의 "변경 범위"에 없는 파일이 수정되었는지 확인. 이탈 시 정당성을 평가.
3. 중복 보고 금지:
   - trust-ledger.md에 이미 있는 항목은 다시 보고하지 않는다.
   - self-check.md의 Warning/Info는 중복 보고하지 않는다.
4. 신규 위험만 보고: trust-ledger에 없는 신규 발견 사항만 Critical/Warning/Info로 분류.

산출물:
- PRD: ${prd.md 내용}
- 설계서: ${design.md 내용}
- Trust Ledger: ${trust-ledger.md 내용}
- self-check: ${self-check.md 내용}
- 코드 맵: ${codemap.md 핵심 파일 섹션}
- diff 파일 경로: ${DIFF_FILE}
- references (있으면): ${references 요약}

출력 포맷은 cross-review 표준에 맞춘다 (Step 4의 정규화 형식 참조).
한국어로 출력한다.
```

**Task B: security-auditor (cross-review 미션)**

`Task(subagent_type="oh-my-gx:security-auditor")` — prompt에 다음을 포함:

```
[중요] 이 호출은 일반 review가 아닌 gx-cross-review이다.
다음 미션을 정확히 수행하라:

미션:
1. PRD 정책/제약 vs 코드 정합성: PRD에 명시된 정책/권한/제약이 코드에 반영되었는지 1:1 검증.
2. 설계 보안 약속 vs 코드: 설계서의 보안/장애대응(fallback/timeout/재시도)이 구현되었는지 검증.
3. trust-ledger 신선도: 기존 trust-ledger 항목 중 다시 발생한 것이 있는지 확인.
4. references 위반: references/ 디렉토리의 외부 표준 위반 여부 검증.
5. 중복 보고 금지: trust-ledger에 이미 있는 항목은 보고하지 않는다.

산출물 (qa-manager와 동일).

한국어로 출력한다.
```

#### 3b-2. 병렬 호출

`Task A`와 `Task B`를 **하나의 메시지에서** 동시에 발행한다 (병렬 실행).

#### 3b-3. 결과 통합

두 결과를 합산한다:
- AC 매트릭스 → qa-manager 결과를 우선 사용.
- 설계 범위 이탈 → qa-manager 결과 사용.
- 신규 위험 → 두 결과를 합치고 같은 위치(파일:라인)는 병합.
- references 위반 → security-auditor 결과 사용.

---

## Step 4: 결과 정규화 + 저장

advisor와 무관하게 동일한 포맷으로 정규화하여 `${RESULT_FILE}`에 저장한다.

### 4-1. 표준 포맷

```markdown
# Cross-Review 결과

- advisor: codex | claude
- 브랜치: ${BRANCH} (base: ${BASE_BRANCH})
- DEV_DIR: ${DEV_DIR}
- 실행 시각: 2026-05-04T10:30:00Z

## AC 충족 매트릭스

| AC | 충족 | 근거 |
|----|------|------|
| AC-1: 결제 한도 100→200만 변경 | O | PaymentService:42 |
| AC-2: 한도 초과 시 예외 발생 | X | 검증 로직 누락 |

[Must] 전체 N건 중 N건 충족, [Should] 전체 N건 중 N건 충족.

## 설계 범위 이탈

(없으면 "이탈 없음")

- 파일: PaymentController.kt
  - 변경 요약: ...
  - 이탈 사유: 설계서 변경 범위에 없음. 정당성 검토 필요.

## 신규 위험

(trust-ledger에 없는 항목만)

### Critical
- [RISK] PaymentService.kt:55 — 한도 초과 검증 누락
  - 근거: ...
  - 권고: ...

### Warning
- ...

### Info
- ...

## references 위반 (해당 시)

(섹션 자체를 생략 가능)

## 총평
- 강점: ...
- 합산: Critical N건, Warning N건, Info N건
- 권고: ...
```

### 4-2. 파일 저장

```bash
# RESULT_FILE에 정규화된 결과 작성
Write(${RESULT_FILE}, normalized_content)
```

`${RAW_FILE}`(advisor의 원시 응답)도 보존한다 — 사용자가 원본을 확인할 수 있도록.

### 4-3. 사용자 요약

전문은 표시하지 않는다. **요약만** 보고한다:

```
## Cross-Review 완료

- advisor: codex
- AC 충족: [Must] 4/5, [Should] 2/3
- 설계 범위 이탈: 1건
- 신규 위험: Critical 1, Warning 2, Info 3
- references 위반: 없음

전문: ${RESULT_FILE}     (= ${DEV_DIR}/cross-review.md)
원시 응답: ${RAW_FILE}    (= ${DEV_DIR}/cross-review.raw.md)
```

---

## Step 5: 발견 항목 처리 (수정 위임)

자동 수정은 절대 하지 않는다. 모든 항목에 대해 사용자에게 명시적 승인을 받는다.

### 5-1. 처리 대상 식별

다음 항목들이 처리 대상이다:
- AC 미충족 항목 (X 또는 부분).
- 설계 범위 이탈 (정당성 부족 시).
- 신규 위험 (Critical/Warning/Info).
- references 위반.

각 항목에 일련번호를 부여한다 (1, 2, 3, ...).

### 5-2. 일괄 처리 옵션 선택

```
AskUserQuestion(
  questions: [{
    question: "발견된 N개 항목을 어떻게 처리할까요?",
    header: "처리 방식",
    options: [
      { label: "전부 수정", description: "모든 항목을 coder에 위임하여 수정" },
      { label: "일부 수정", description: "항목별로 개별 선택" },
      { label: "직접 입력", description: "Other로 이동해서 수정할 항목 번호를 자연어로 입력 (예: 1, 3, 5번)" },
      { label: "전부 건너뛰기", description: "기록만 남기고 종료" }
    ],
    multiSelect: false
  }]
)
```

### 5-3. 분기 처리

#### 전부 수정

모든 항목을 한 번에 `Task(subagent_type="oh-my-gx:coder")` 수정 모드로 위임:

prompt:
- 수정 항목 목록 전체 (각 항목의 위치, 문제, 권고)
- 코드 맵
- PROJECT_ROOT
- "각 항목을 순서대로 수정하고 [N/M] 형식으로 보고하라."

수정 완료 후 `${RESULT_FILE}`에 처리 상태 섹션 추가:
```markdown
## 처리 결과
- 1번 항목 (Critical PaymentService:55): 수정됨
- 2번 항목 (Warning ...): 수정됨
- ...
```

#### 일부 수정

`${BATCH_MODE}` = `none`으로 시작. 항목별로 AskUserQuestion을 수행하되, 매 루프 시작 시 `${BATCH_MODE}`를 확인한다:
- `AUTO_FIX`이면 질문 생략 후 자동 "수정"으로 처리.
- `AUTO_SKIP`이면 질문 생략 후 자동 "건너뛰기"로 처리.
- `none`이면 질문 표시.

질문 결과 "이후 전부 수정"이면 `${BATCH_MODE}` = `AUTO_FIX`, "이후 전부 건너뛰기"면 `${BATCH_MODE}` = `AUTO_SKIP`로 전환하고 다음 항목부터 적용한다.
```
AskUserQuestion(
  questions: [{
    question: "1번 항목: [Critical] PaymentService:55 — 한도 초과 검증 누락. 수정할까요?",
    header: "1/N",
    options: [
      { label: "수정", description: "이 항목을 coder에 위임" },
      { label: "건너뛰기", description: "이 항목 건너뛰고 다음으로" },
      { label: "이후 전부 수정", description: "이 항목부터 끝까지 모두 수정" },
      { label: "이후 전부 건너뛰기", description: "이 항목부터 끝까지 모두 건너뛰기" }
    ],
    multiSelect: false
  }]
)
```

승인된 항목만 모아서 `Task(subagent_type="oh-my-gx:coder")` 수정 모드로 일괄 위임.

#### 직접 입력

사용자가 Other로 항목 번호 또는 자연어를 입력. 예:
- "1, 3, 5번"
- "Critical만"
- "AC 미충족 전부"

오케스트레이터가 입력을 파싱하여 매칭되는 항목들을 식별한다. 모호하면 재확인:
```
AskUserQuestion(
  questions: [{
    question: "다음 항목으로 이해했습니다: 1번, 3번, 5번. 맞나요?",
    header: "확인",
    options: [
      { label: "맞음", description: "이 항목들로 진행" },
      { label: "다시 입력", description: "Other로 다시 입력" }
    ],
    multiSelect: false
  }]
)
```

#### 전부 건너뛰기

수정 없이 종료. `${RESULT_FILE}`에 처리 상태 섹션 추가:
```markdown
## 처리 결과
- 모든 항목 건너뛰기 선택. 사용자가 별도로 처리 예정.
```

### 5-4. 수정 후 재확인 (선택적)

수정이 발생했으면 사용자에게 묻는다:
```
AskUserQuestion(
  questions: [{
    question: "수정이 완료되었습니다. cross-review를 다시 실행할까요?",
    header: "재실행",
    options: [
      { label: "재실행", description: "수정된 코드로 cross-review 재수행" },
      { label: "종료", description: "현재 상태로 종료" }
    ],
    multiSelect: false
  }]
)
```

재실행 선택 시 Step 0부터 다시 시작.

---

## 산출물 부재 fallback

Step 0-3에서 prd.md/design.md 둘 다 없으면 이 경로를 따른다.

### F-1. fallback 모드 안내

```
산출물(prd.md, design.md)이 없습니다.
gx-cross-review의 차별점인 "약속 대비 충실도 검증"을 수행할 수 없습니다.
일반 모드로 진행하면 기본 /codex:review 또는 qa-manager 일반 리뷰와 거의 동일합니다.
```

### F-2. 진행 여부 확인

```
AskUserQuestion(
  questions: [{
    question: "일반 모드로 진행할까요?",
    header: "fallback",
    options: [
      { label: "진행", description: "산출물 없이 diff만으로 일반 리뷰 수행" },
      { label: "중단", description: "/gx-dev로 산출물을 먼저 생성하세요" }
    ],
    multiSelect: false
  }]
)
```

### F-3. fallback 실행

**codex 선택 시**: companion의 `review` 서브명령을 그대로 호출 (산출물 주입 없음). companion이 자체적으로 diff를 수집하므로 `${DIFF_FILE}`은 전달하지 않는다.
```bash
node "${CODEX_COMPANION}" review --wait --base "${BASE_BRANCH}" --scope auto > "${RAW_FILE}"
```
- `--wait`: 동기 결과 수신.
- `--base`: 베이스 브랜치 명시 (Step 0-2 결과).
- `--scope`: companion은 `auto|working-tree|branch`만 허용하므로 항상 `auto`로 고정한다. Step 0-0의 `${SCOPE}`(`diff|stat`)는 자체 diff 수집(Step 2-2)에만 의미 있고, fallback은 companion이 알아서 결정한다.

**claude 선택 시**: `qa-manager`만 호출, 일반 contract 사용 (cross-review 미션 제거). security-auditor는 호출하지 않는다 (산출물 없으면 보안 정합성 검증이 불가능).

결과는 동일하게 `${RESULT_FILE}`에 저장. AC 매트릭스 / 설계 범위 이탈 섹션은 생략하고 신규 위험 섹션만 채운다.

---

## 한국어 강제 규칙

1. **prompt 강제**: codex prompt의 `<language>` 블록, claude prompt의 명시적 한국어 지시.
2. **응답 검증**: 응답의 첫 50줄에서 한국어 문자(가-힣) 비율이 20% 미만이면 한국어 정규화 단계를 추가.
3. **사용자 출력**: 사용자에게 표시하는 모든 메시지는 한국어로 작성. 고유명사·기술 용어는 영문 허용.

---

## 자동 수정 금지 원칙

1. advisor 응답에 Critical 항목이 있어도 즉시 coder를 호출하지 않는다.
2. 모든 수정은 Step 5의 AskUserQuestion을 거쳐 사용자가 명시적으로 승인한 항목만 수행.
3. coder는 "수정" 모드로만 호출하고, 신규 기능 추가나 리팩토링은 위임 범위 밖.
4. 이 원칙은 codex 플러그인의 `codex-result-handling` 스킬과 일치한다.

---

## 에러 처리

- **codex 호출 실패** (종료 코드 ≠ 0): stderr 마지막 20줄 표시 후 중단. 폴백 advisor 자동 전환은 하지 않는다.
- **claude Task 실패**: 어느 한 Task가 실패하면 성공한 결과만으로 정규화. 사용자에게 부분 결과임을 명시.
- **컨텍스트 초과**: Step 2-1의 슬라이싱으로 60,000 토큰 이하로 압축. 그래도 초과하면 사용자에게 `--scope stat` 사용 안내.
- **diff 빈 파일**: 변경사항이 없으면 "변경사항이 없습니다." 표시 후 즉시 종료.
- **pre-tool-guard 충돌**: oh-my-gx의 PreToolUse hook이 codex companion 호출을 차단하면 사용자에게 hook 우회 안내 (드물 것).

---

## 진행 상태 추적

`${DEV_DIR}/cross-review-state.md`에 다음을 기록한다 (간단한 형식):

```yaml
status: in_progress | completed | aborted
advisor: codex | claude
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

- `/gx-dev`: cross-review의 산출물(prd/design/trust-ledger)을 생성한다. 선행 의존.
- `/gx-tdd`: 산출물 파일 구조(prd/design/trust-ledger)가 동일하므로 gx-tdd 완료물에도 그대로 동작한다. 이때 claude advisor가 호출하는 qa-manager는 "gx-tdd 파이프라인 내부 호출 금지" 대상이 아니다 — cross-review는 파이프라인 완료 후의 독립 스킬이므로 허용된다 (gx-tdd 내부 리뷰는 spec-reviewer→quality-reviewer가 담당하며, cross-review는 그와 별개의 사후 검증 층이다).
- `/codex:review`: 일반 코드 리뷰. cross-review와 별개로 사용 가능.
- `/codex:adversarial-review`: cross-review의 codex 경로보다 더 공격적인 비판이 필요하면 별도 호출.
- `/gx-commit`, `/gx-pull-request`: cross-review 후 처리한 변경사항을 커밋/PR.
