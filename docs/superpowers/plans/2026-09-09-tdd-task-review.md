# gx-tdd 조건부 태스크 리뷰 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 세션 IMPLEMENT가 통과시킨 태스크 중 프로덕션 파일을 2개 이상 바꿨거나 fix 라운드를 거친 태스크에만 reviewer를 태스크 범위 모드로 한 번 붙여, 자기 검증 편향을 상쇄하고 phase-review의 재구현 라운드를 줄인다.

**Architecture:** phase-implement에 `### Step 2-V: 태스크 리뷰 (조건부)`를 신설한다. verify_implement 통과 직후 porcelain 스냅샷 차이로 변경 파일을 구해 발동 조건을 판정하고, 임시 인덱스로 태스크 diff를 `reports/t{N}-diff.txt`에 쓴 뒤 `oh-my-gx:reviewer`를 `model: "sonnet"`으로 디스패치한다. findings는 기존 fix loop(라운드 5 공유)로 흘리고 Minor는 phase-review Task A에 유예 목록으로 넘긴다. `agents/reviewer.md`에 태스크 범위 모드 절을 추가하고, 린트 `[34]`와 골든 S40·S41로 고정한다.

**Tech Stack:** Markdown (스킬·phase·에이전트 정의·문서), Bash (린트)

**Spec:** `docs/specs/2026-09-09-superpowers-gap-design.md` — D1, 2절 불변 목록, D5 순서

## Global Constraints

- **선행 조건**: main의 `.claude-plugin/plugin.json` version이 `1.27.0`이고 `grep -c '/33\]' scripts/lint-consistency.sh`가 0보다 커야 한다 (린트 분모 33, phase-implement에 "세션 IMPLEMENT 절차" 존재).
- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (훅 G1). 작업 시작 전 `feat/tdd-task-review` 브랜치를 생성한다.
- **커밋**: 메시지는 `feat: …`/`docs: …` 한 줄 제목 (`.claude/config.json` `conventions.commitFormat`). gx-commit 규칙에 따라 `Co-Authored-By` 등 트레일러를 **붙이지 않는다**. 서브에이전트는 gx-commit의 확인 게이트에 응답할 수 없으므로 직접 `git commit`을 허용한다 (이전 계획과 같은 ruling). grep 패턴 인자에 `git commit` 문자열을 넣지 않는다 (훅 G1 오탐).
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 둘 다 통과한 상태로 끝난다.
- **바이트 예산**: 린트 `[32]`가 SKILL.md ≤ 62,500B(LF 기준 `tr -d '\r' | wc -c`)를 검사한다. 현재 62,431B로 여유가 69B뿐이다. Task 4가 예산을 **63,000B로 올린다** (Step 2-V 참조 3곳 도입분 약 250B). Task 4 이전 태스크는 SKILL.md를 건드리지 않는다.
- **린트 번호 체계**: 현재 `[N/33]`. Task 6이 검사 1개를 추가하며 분모를 34로 올린다. `.claude/`·`README.md`의 인용도 함께 치환한다 (`[31]`이 검사). `docs/`·`CHANGELOG.md`는 치환하지 않는다.
- **린트가 고정하는 문구 (phase-implement.md)**: `[3]` 금지 5항목·`라운드 5`, `[26]` `reports/t{N}-impl.md`·`reports/t{N}-red.md`·4-status, `[33]` `세션 IMPLEMENT 절차`·`focused 집합 직접 실행`·`model: "opus"`·`태스크 수 가드`·`작성 범위 — 테스트 집합`. 이 문구를 지우거나 바꾸지 않는다.
- **gx-ralph-iterate·gx-dev는 손대지 않는다**: 루프는 리뷰 없이 verify로 닫는다 (설계 4절).
- **외과적 변경**: 지시된 블록만 고친다.

---

### Task 1: phase-implement에 Step 2-V 태스크 리뷰를 신설한다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` — `## Step 2` 도입 의사코드, verify_implement 7번, fix loop 첫 불릿, `## Step 3` 앞에 `### Step 2-V` 신설, `## Step 4` 보고 템플릿, `## state.md 추적`, `## --resume 호환`, `## 금지 사항`

**Interfaces:**
- Consumes: 없음
- Produces: 절 제목 `### Step 2-V: 태스크 리뷰 (조건부 — reviewer 태스크 범위 모드)`, 파일 `reports/t{N}-diff.txt`·`reports/t{N}-review.md`·`reports/t{N}-diff-r{r}.txt`, state.md 태스크 필드 `review`·`review-report`·`deferred-minors` (Task 2·3·6이 인용·검사)

- [ ] **Step 1: Step 2 의사코드에 2-V를 넣는다**

현재:

```
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증 (경로 무관 동일)

    record_to_state(task, results)
```

새 텍스트:

```
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증 (경로 무관 동일)

    # 2-V: 태스크 리뷰 (조건부 — 프로덕션 파일 2개 이상 또는 fix 라운드 있음)
    if task_review_required(task):
        review_task(task)                    # reviewer 태스크 범위 모드 (sonnet). report: reports/t{N}-review.md
    record_to_state(task, results)
```

- [ ] **Step 2: verify_implement 7번과 fix loop 불릿을 2-V로 연결한다**

`7. ✅ 통과 + 무결성 유지 → 태스크 완료, 다음 태스크로 진행.`을 아래로 바꾼다:

```
7. ✅ 통과 + 무결성 유지 → **Step 2-V 태스크 리뷰 판정**으로 진행한다 (발동 조건 미충족이면 `review: skipped` 기록 후 태스크 완료).
```

fix loop 표 아래 첫 불릿 `- 매 라운드: 구현 주체(세션 또는 implementer)가 수정 → focused 재실행 → fix report를 같은 report 파일에 append → 상태 반환(격리 경로만) → 오케스트레이터가 verify_implement 재수행.` 문장 끝(`재수행.` 뒤, 같은 불릿 안)에 이어 붙인다:

```
 Step 2-V 태스크 리뷰의 findings 수정도 **이 라운드 카운터와 상한 5를 공유**한다 — 리뷰가 연 라운드는 verify_implement 재수행 뒤 재리뷰(2-V)로 닫힌다.
```

- [ ] **Step 3: `## Step 3: 정체 감지 + 에스컬레이션 (RGR 사이클)` 제목 위의 `---` 앞에 Step 2-V 절을 삽입한다**

```markdown
### Step 2-V: 태스크 리뷰 (조건부 — reviewer 태스크 범위 모드)

verify_implement 7번 직후, 태스크를 완료 처리하기 **전에** 판정한다. 세션 IMPLEMENT는 검사자와 피검사자가 같으므로, 자기 검증 편향이 커지는 태스크에만 fresh eyes를 한 번 붙인다. phase-review는 **전체 브랜치 리뷰**로 그대로 남는다.

**발동 조건** (하나라도 해당하면 리뷰, 아니면 state.md 태스크에 `review: skipped` 기록 후 태스크 완료):
- (a) 이 태스크가 바꾼 **프로덕션 파일이 2개 이상**이다. 변경 파일 목록은 verify_red 스냅샷과 현재 porcelain의 차이로 구한다 (`.dev/` 제외. 스냅샷에 없거나 상태가 달라진 줄의 경로. `reports/t{N}-impl.md` `## 구현 내용`의 변경 파일과 합집합). 프로덕션 파일은 그중 테스트 파일 글롭(Step 0.5 4항의 `**/*test*`·`**/*Test*`·`**/*spec*`)에 해당하지 않는 파일이다.
  ```bash
  git status --porcelain -- . ':(exclude).dev' | sort > ${DEV_DIR}/rgr-t{N}-porcelain.now.txt
  comm -13 <(grep -v ' \.dev/' ${DEV_DIR}/rgr-t{N}-porcelain.txt | sort) ${DEV_DIR}/rgr-t{N}-porcelain.now.txt | cut -c4-
  ```
  (svn은 `svn status`로 같은 대조를 한다. 경로 열은 8열부터다.)
- (b) 이 태스크의 state.md에 `fix-round`가 기록되어 있다 (fix loop를 1회 이상 돌았다).

**태스크 diff 수집**: 실제 인덱스와 porcelain 스냅샷을 건드리지 않도록 **임시 인덱스**를 쓴다 (훅 `compute_fingerprint`와 같은 관용구 — mktemp가 만든 빈 파일은 git이 거부하므로 경로만 쓴다). 대상은 (a)의 변경 파일 전부 + 이 태스크의 `test-file`이다.
```bash
IDX="${TMPDIR:-/tmp}/.gxtr.$$"; rm -f "$IDX"
GIT_INDEX_FILE="$IDX" git add -A -- {변경 파일 목록} "{test-file}"
GIT_INDEX_FILE="$IDX" git diff --cached HEAD -- {변경 파일 목록} "{test-file}" > ${DEV_DIR}/reports/t{N}-diff.txt
rm -f "$IDX"
```
svn: 버전 관리 중인 파일은 `svn diff -- {파일들}`, 미등록 신규 파일은 `diff -u /dev/null {파일}`을 같은 파일에 이어 붙인다. 500줄 초과 시 Diff 수집 규칙의 `--stat` 강등을 그대로 적용한다.

**디스패치** (`model: "sonnet"` — 프로파일·격상과 무관하게 고정. 태스크 diff는 작고 재리뷰는 scoped다):

```
Task(subagent_type="oh-my-gx:reviewer", model: "sonnet"):
  description: "Task review T{N} (scoped)"
  prompt: |
    당신은 통합 리뷰 전담자입니다. **태스크 범위 모드**로 동작합니다 — 전달된 AC와 태스크 diff만 봅니다. 전체 브랜치 리뷰는 phase-review가 별도로 수행하므로 범위를 넓히지 않습니다.

    [Iron Law]
    NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED — Part 1 verdict를 먼저 확정한 뒤 Part 2를 냅니다.

    [발견 단계 커버리지]
    발견 단계의 목표는 커버리지다. 확신이 서지 않거나 심각도가 낮다고 판단한 항목도 빠짐없이 보고합니다. 확신이 낮은 항목은 Minor로 분류하되 보고에서 빼지 않습니다.

    [구현자 보고 불신뢰]
    RED/IMPL report의 산문 정당화는 미검증 주장입니다 — diff로 검증하고, 테스트를 재실행하지 않습니다 (증거는 verify_implement가 확보).

    [태스크 AC (Given-When-Then)]
    {이 태스크에 매핑된 AC 시나리오 — Part 1은 이것만 평가}

    [설계서 인터페이스]
    {대상 컴포넌트의 시그니처 — 핵심 모드는 "없음 (핵심 모드)"}

    [태스크 diff]
    - {reports/t{N}-diff.txt} — Read하여 확인

    [구현 report]
    - {reports/t{N}-red.md}, {reports/t{N}-impl.md}

    [코드 맵]
    {코드 맵}

    [프로젝트 컨벤션]
    {CLAUDE.md 컨벤션 또는 기존 코드 스타일}

    [테스트 품질 기준 파일]
    {ANTI_PATTERNS_PATH} — 테스트 코드 품질 판정 시 Read
    {FRONTEND_TESTING_PATH} — UI 태스크에서만 전달

    [재리뷰 — fix 라운드 후에만 포함]
    이전 findings: {항목 목록}. 각 항목을 ADDRESSED / NOT ADDRESSED로 판정하고(파일:라인 근거. "시도함"은 NOT ADDRESSED), 수정 diff {reports/t{N}-diff-r{r}.txt}의 새 결함만 추가로 보고합니다. 범위 밖 관찰은 Minor로 둡니다.

    [출력 형식]
    agents/reviewer.md의 출력 형식 — Part 1 매트릭스(전달된 AC만)·판정, Part 2 분류·판정, 맨 마지막에 spec_verdict → quality_verdict 두 YAML 블록 순서 고정. 재리뷰면 Part 2 앞에 `## 재리뷰 판정` 표(항목 | ADDRESSED/NOT ADDRESSED | 근거)를 둡니다.
```

**결과 처리** (오케스트레이터 직접):
1. reviewer 출력 전문을 `${DEV_DIR}/reports/t{N}-review.md`에 Write한다 (reviewer는 Write 도구가 없다). 재리뷰는 `## 재리뷰 R{r}` 제목으로 같은 파일에 append한다. state.md 태스크에 `review: in_progress`·`review-report: reports/t{N}-review.md`를 기록한다.
2. `spec_verdict`·`quality_verdict` 블록을 phase-review Step 4.0과 같은 규칙으로 파싱한다 — 블록 우선, 산문 판정과 상충하면 FAIL로 간주하고 reviewer를 1회 재호출, 재호출도 상충이면 사용자에게 보고. `[검증 필요]` 항목은 해당 focused 테스트를 1회 직접 실행해 반영한다.
3. 라우팅 (사용자에게 묻지 않는다 — Step 2-I fix loop와 같은 자동 경로):
   - `spec_verdict: FAIL`, Critical, Important `[동작결함]`(무표기 포함) → **fix loop 진입**. 구현 주체(세션. `--isolated`면 같은 implementer 재개)가 findings를 수정 → focused 재실행 → fix report를 `reports/t{N}-impl.md`에 append → verify_implement 재수행 → 수정 diff를 위 임시 인덱스 관용구로 `reports/t{N}-diff-r{r}.txt`에 수집 → **재리뷰** 디스패치(위 프롬프트의 `[재리뷰]` 절 포함). NOT ADDRESSED 또는 새 Critical/Important가 남으면 다음 라운드. `current-step`은 `"RGR T{N}: REVIEW R{r}"`, 태스크에 `fix-round: {r}/5`.
   - Important `[동작불변]` → 세션 정리 (세션 IMPLEMENT 절차의 REFACTOR 규칙·금지 목록. `--isolated`면 implementer 정리 모드) → focused 재실행 → 같은 라운드의 재리뷰 대상에 포함.
   - Minor → **유예**. 수정하지 않고 태스크에 `deferred-minors: {건수}`를 기록한다. phase-review Task A가 유예 목록을 받아 머지 전 수정 필요 여부를 판정한다.
   - spec PASS·Critical 0·Important 0 → `review: completed` 기록, 태스크 완료.
   - 라운드 5 소진 → Step 2-I의 소진 처리(AskUserQuestion: 수동 수정 후 계속 / 태스크 스킵 / 중단)를 그대로 따른다. 태스크 스킵 시 미해결 findings를 trust-ledger `### 위험 수용`에 `- [태스크 리뷰 미해결] T{N}: {findings 요약} (implement/Step 2-V)`로 기록한다.
4. execution-log에 `agent: reviewer (T{N}, task-scoped)`와 결과 요약(SPEC 판정·Critical/Important/Minor 건수·처리)을 남긴다.

`current-step`을 `"RGR T{N}: REVIEW"`로 갱신.
```

- [ ] **Step 4: Step 4 보고 템플릿·state.md 추적·--resume·금지 사항을 맞춘다**

`## Step 4: 사이클 완료 보고` 템플릿의 세 태스크 행을 교체한다:

```
- T1 (AC-1): RED ✅ → IMPLEMENT ✅ → REVIEW skip (파일 1개)
- T2 (AC-2, AC-3 배칭): RED ✅ → IMPLEMENT ✅ (fix 라운드 1회) → REVIEW ✅ (Important 1건 정리, Minor 2건 유예)
- T3 (AC-4): RED ✅ → IMPLEMENT ✅ (정리 대상 없음) → REVIEW ✅
```

`## state.md 추적`의 `"RGR T1 (AC-1)"` 객체에서 `impl: completed` 줄 뒤에 세 줄을 추가한다 (들여쓰기는 이웃 줄과 같게):

```yaml
        review: completed             # Step 2-V 결과 — skipped | in_progress | completed
        review-report: reports/t1-review.md
        deferred-minors: 2            # phase-review Task A에 유예 목록으로 전달
```

`"RGR T2 (AC-2)"` 객체의 `fix-round: 2/5` 줄 뒤에 `        review: in_progress`를 추가한다. execution-log 예시 끝에 엔트리를 추가한다:

```yaml
- phase: implement
  agent: reviewer (T1, task-scoped)
  result: "SPEC PASS · Critical 0, Important 1[동작불변] 정리, Minor 2 유예"
```

`## --resume 호환`의 `"RGR T{N}: FIX R{r}"` 행 뒤에 두 행을 추가한다:

```markdown
- `"RGR T{N}: REVIEW"` → Step 2-V 판정부터 재실행 (변경 파일·태스크 diff 재수집 후 디스패치)
- `"RGR T{N}: REVIEW R{r}"` → 라운드 {r}의 수정 diff 재수집 후 재리뷰부터 재개 (`reports/t{N}-review.md`가 이전 findings의 영속 기억)
```

`## 금지 사항 (Iron Law 강제)`의 "절대 수행하지 않는 동작" 목록 끝에 추가한다:

```markdown
- ❌ 발동 조건(프로덕션 파일 2개 이상 또는 fix 라운드)을 충족한 태스크의 리뷰 생략 — "diff가 작아 보여서"는 사유가 아니다. 조건은 기계 판정이다
```

- [ ] **Step 5: 검증**

Run: `for s in '### Step 2-V: 태스크 리뷰 (조건부 — reviewer 태스크 범위 모드)' '프로덕션 파일이 2개 이상' 'reports/t{N}-diff.txt' 'reports/t{N}-review.md' 'reports/t{N}-diff-r{r}.txt' 'model: "sonnet"' 'subagent_type="oh-my-gx:reviewer"' 'deferred-minors' 'ADDRESSED' 'review: skipped' 'RGR T{N}: REVIEW' 'GIT_INDEX_FILE' '세션 IMPLEMENT 절차' 'focused 집합 직접 실행' 'model: "opus"' '태스크 수 가드' '작성 범위 — 테스트 집합' '라운드 5'; do grep -qF "$s" .claude/skills/gx-tdd/phases/phase-implement.md || echo "MISSING: $s"; done; grep -c 'review_task' .claude/skills/gx-tdd/phases/phase-implement.md`
Expected: `MISSING` 없음, 마지막 `1`.

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 33/33 통과 (`[3]`·`[26]`·`[33]` 문구 유지), 훅 테스트 통과.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md
git commit -F - <<'MSG'
feat: gx-tdd phase-implement에 조건부 태스크 리뷰(Step 2-V)를 신설한다
MSG
```

---

### Task 2: agents/reviewer.md에 태스크 범위 모드를 정의한다

**Files:**
- Modify: `agents/reviewer.md:4` (description), `## 입력` 절 뒤에 `## 태스크 범위 모드` 신설

**Interfaces:**
- Consumes: Task 1의 프롬프트 계약 (태스크 AC·태스크 diff·재리뷰 판정)
- Produces: 절 제목 `## 태스크 범위 모드` (Task 6 린트가 검사), `## 재리뷰 판정` 표 형식

- [ ] **Step 1: description을 고친다**

4행의 `oh-my-gx:gx-tdd phase-review 전용 — 구 spec-reviewer/quality-reviewer 2석을 대체한다.`를 `oh-my-gx:gx-tdd phase-review(전체 브랜치)와 phase-implement Step 2-V(태스크 범위 모드) 전용 — 구 spec-reviewer/quality-reviewer 2석을 대체한다.`로 바꾼다.

- [ ] **Step 2: `## 입력` 절과 `## Part 1: spec 충족 검증` 사이에 절을 넣는다**

```markdown
## 태스크 범위 모드 (phase-implement Step 2-V)

phase-implement가 태스크 하나의 diff에 대해 디스패치하는 모드다. 전체 브랜치 리뷰(phase-review)와 다음만 다르다:

- Part 1 대상은 **전달된 AC만**이다. 다른 AC는 매트릭스에 넣지 않는다.
- 설계 범위 이탈은 태스크의 대상 컴포넌트 기준으로 본다.
- diff는 태스크 diff(`reports/t{N}-diff.txt`)이고, 구현 report(`reports/t{N}-red.md`·`reports/t{N}-impl.md`)를 함께 받는다 — 미검증 주장이다.
- **재리뷰**(fix 라운드 후): 이전 findings 각각을 `ADDRESSED` / `NOT ADDRESSED`로 판정한다 (파일:라인 근거. "시도함"은 NOT ADDRESSED). 수정 diff(`reports/t{N}-diff-r{r}.txt`)의 새 결함만 추가한다. 범위 밖 관찰은 Minor로 보고한다. Part 2 앞에 아래 표를 둔다:

  ```
  ## 재리뷰 판정

  | 항목 | 판정 | 근거 |
  |------|------|------|
  | {이전 finding 요약} | ADDRESSED | {파일}:{라인} |
  | {이전 finding 요약} | NOT ADDRESSED | {파일}:{라인} — {남은 문제} |
  ```

- 출력 형식·기계 판정 블록·Iron Law·금지 사항은 전체 브랜치 리뷰와 같다.
```

- [ ] **Step 3: 검증**

Run: `grep -n '## 태스크 범위 모드\|## 재리뷰 판정\|NOT ADDRESSED\|phase-implement Step 2-V' agents/reviewer.md | cut -c1-80; bash scripts/lint-consistency.sh`
Expected: 4개 앵커 존재, 33/33 통과 (`[28]` 커버리지 문단 유지).

- [ ] **Step 4: 커밋**

```bash
git add agents/reviewer.md
git commit -F - <<'MSG'
feat: reviewer 에이전트에 태스크 범위 모드와 재리뷰 판정 형식을 추가한다
MSG
```

---

### Task 3: phase-review가 유예 Minor를 받고 전체 브랜치 리뷰임을 명시한다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` — 도입부(`security-auditor는 reviewer와 **병렬 가능** (서로 독립).` 뒤), Task A 프롬프트의 `[테스트 품질 기준 파일]` 블록 뒤, `[작업]` 2번

**Interfaces:**
- Consumes: Task 1의 `deferred-minors`·`reports/t{N}-review.md`
- Produces: 프롬프트 절 제목 `[태스크 리뷰 유예 Minor — 있을 때만]` (Task 6 린트가 검사)

- [ ] **Step 1: 도입부에 한 문단을 넣는다**

`security-auditor는 reviewer와 **병렬 가능** (서로 독립).` 행 뒤에 빈 줄 하나를 두고 추가한다:

```markdown
이 Phase는 **전체 브랜치 리뷰**다. phase-implement Step 2-V가 태스크 범위 리뷰를 조건부로 먼저 수행했을 수 있으며, 거기서 유예된 Minor는 Task A가 받아 머지 전 수정 필요 여부만 판정한다 — 태스크 리뷰를 다시 하지 않는다.
```

- [ ] **Step 2: Task A 프롬프트에 유예 목록 절을 넣는다**

`    {FRONTEND_TESTING_PATH} — diff에 UI 테스트가 포함된 경우에만 Read. …` 행과 `    [작업]` 행 사이에 삽입한다 (들여쓰기 4칸):

```
    [태스크 리뷰 유예 Minor — 있을 때만]
    {state.md 태스크 객체의 deferred-minors > 0인 태스크의 reports/t{N}-review.md 경로 목록} — 각 파일의 Minor 항목을 Read하여, 머지 전 수정이 필요한 항목만 Part 2에 Important [동작불변]로 승격하고 나머지는 Minor로 유지합니다. 유예 목록 자체를 다시 리뷰하지 않습니다.
```

`[작업]` 2번 `    2. Part 2: Critical/Important/Minor 분류 + [동작결함|동작불변] 마커 → QUALITY 판정 + quality_verdict` 끝에 ` (유예 Minor가 전달됐으면 승격 판정 포함)`을 붙인다.

- [ ] **Step 3: 검증**

Run: `grep -n '전체 브랜치 리뷰\|\[태스크 리뷰 유예 Minor\|승격 판정 포함' .claude/skills/gx-tdd/phases/phase-review.md | cut -c1-80; bash scripts/lint-consistency.sh`
Expected: 3개 앵커 존재, 33/33 통과 (`[27]`·`[28]`·`[33]`의 phase-review 문구 유지).

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-review.md
git commit -F - <<'MSG'
feat: phase-review가 태스크 리뷰의 유예 Minor를 받아 승격 여부를 판정한다
MSG
```

---

### Task 4: SKILL.md·maintenance-notes를 맞추고 바이트 예산을 63,000B로 올린다

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` — Agent 팀 REVIEW 표 reviewer 행, Phase 개요 implement 행, Context Slicing 표 reviewer 행
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md` — `**마커 분류**` 항목 앞에 항목 추가
- Modify: `scripts/lint-consistency.sh` — `[32]` 예산 3곳 (헤더 주석 37행, `for spec in` 목록, ok 메시지)

**Interfaces:**
- Consumes: Task 1·2의 용어("태스크 범위 모드", `reports/t{N}-diff.txt`)
- Produces: SKILL.md의 `태스크 범위 모드` 문자열 (Task 6 린트가 검사)

- [ ] **Step 1: 린트 [32] 예산을 먼저 올린다 (SKILL.md 편집이 예산을 넘기지 않도록)**

```bash
sed -i 's|SKILL.md ≤ 62500B|SKILL.md ≤ 63000B|g; s|gx-tdd/SKILL.md:62500"|gx-tdd/SKILL.md:63000"|' scripts/lint-consistency.sh
grep -n '63000\|62500' scripts/lint-consistency.sh
```
Expected: `63000` 3곳(헤더 주석·for 목록·ok 메시지), `62500` 0곳.

- [ ] **Step 2: SKILL.md 세 곳을 고친다**

Agent 팀 REVIEW 표의 reviewer 행 역할 셀 `**spec Part 1 + quality Part 2 통합 (신설)**`을 `**spec Part 1 + quality Part 2 통합. phase-implement 2-V 태스크 범위 모드는 sonnet**`으로 바꾼다.

Phase 개요 표 implement 행의 주 Agent 셀 `**red-writer(디스패치) → 세션 IMPLEMENT (`--isolated`: implementer)**`를 `**red-writer(디스패치) → 세션 IMPLEMENT (`--isolated`: implementer) → 조건부 태스크 리뷰(reviewer)**`로 바꾼다.

Context Slicing 표의 reviewer 행 끝 `**"Part 1 verdict 선행. 테스트 재실행 금지"** |`를 `**"Part 1 verdict 선행. 테스트 재실행 금지"**. **태스크 범위 모드**(phase-implement 2-V): 태스크 AC+`reports/t{N}-diff.txt`+RED/IMPL report+인터페이스만, `model: "sonnet"` |`로 바꾼다.

- [ ] **Step 3: maintenance-notes에 항목을 추가한다**

`- **마커 분류**(`[동작결함]`/`[동작불변]`): …` 항목 **바로 앞**에 추가한다:

```markdown
- **태스크 리뷰 프롬프트·재리뷰 계약**: phase-implement.md Step 2-V의 reviewer 디스패치 프롬프트(Iron Law·커버리지·불신뢰 문단은 phase-review Task A와 같은 문구) ↔ `agents/reviewer.md` "태스크 범위 모드" 절(재리뷰 판정 표 형식이 SSOT) ↔ phase-review Task A의 `[태스크 리뷰 유예 Minor]` 절(소비)에 중복. 린트 [34/33]가 세 곳을 검사한다.
```

(인용을 `[34/33]`으로 적는 이유: 린트 `[31]`은 `.claude` 아래 `.md`의 `[N/M]` 인용에서 M이 현재 분모(33)와 같은지만 본다. Task 6 Step 2의 전역 치환이 `[34/34]`로 올린다.)

- [ ] **Step 4: 검증**

Run: `grep -c '태스크 범위 모드' .claude/skills/gx-tdd/SKILL.md; tr -d '\r' < .claude/skills/gx-tdd/SKILL.md | wc -c; grep -c '태스크 리뷰 프롬프트' .claude/skills/gx-tdd/references/maintenance-notes.md; bash scripts/lint-consistency.sh`
Expected: `2` 이상, 63,000 이하, `1`, 33/33 통과 (`[32]`가 새 예산으로, `[31]`이 `[34/33]` 인용으로 통과).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-tdd/references/maintenance-notes.md scripts/lint-consistency.sh
git commit -F - <<'MSG'
docs: gx-tdd SKILL.md에 태스크 범위 리뷰를 반영하고 바이트 예산을 63,000B로 올린다
MSG
```

---

### Task 5: 사용자 문서를 갱신한다

**Files:**
- Modify: `README.md` — tdd 절 `- **implement**:` 불릿
- Modify: `docs/tdd-guide.md` — 6.5 표의 `| 리뷰 |` 행, 6.6 `**verify_implement (IMPLEMENT 직후 — GREEN+REFACTOR 통합)**` 목록 끝

**Interfaces:**
- Consumes: Task 1의 발동 조건
- Produces: 없음

- [ ] **Step 1: README**

`- **implement**:` 불릿에서 `태스크는 AC 1건 단위이며 8개를 넘으면 분할을 먼저 묻는다.` 뒤(같은 불릿 안)에 이어 붙인다: ` 프로덕션 파일을 2개 이상 바꿨거나 fix 라운드를 거친 태스크는 완료 전에 `reviewer`가 태스크 범위로 한 번 더 본다(sonnet). 나머지는 기계 검증(해시·focused 직접 실행)으로 닫는다.`

- [ ] **Step 2: tdd-guide**

6.5 표의 `| 리뷰 | `reviewer` | PRD의 AC + diff + 컨벤션 (Part 1: AC 충족 → Part 2: 코드 품질) | Part 1 verdict 확정 전 품질 판정 |` 행의 "무엇을 보는가" 셀 끝에 `. 태스크 범위 모드(Step 2-V)는 태스크 AC + 태스크 diff만`을 붙인다.

6.6의 verify_implement 목록 `5. public 시그니처 변경 없음 확인` 뒤에 항목을 추가한다:

```markdown
6. 프로덕션 파일을 2개 이상 바꿨거나 fix 라운드가 있었으면 `reviewer`가 태스크 범위로 리뷰 → findings는 같은 fix loop로, Minor는 phase-review에 유예. 단일 파일·fix 없음이면 기계 검증만으로 닫는다
```

- [ ] **Step 3: 검증**

Run: `grep -c '태스크 범위' README.md docs/tdd-guide.md; bash scripts/lint-consistency.sh`
Expected: README 1, tdd-guide 2 이상, 33/33 통과.

- [ ] **Step 4: 커밋**

```bash
git add README.md docs/tdd-guide.md
git commit -F - <<'MSG'
docs: 조건부 태스크 리뷰를 README와 TDD 가이드에 반영한다
MSG
```

---

### Task 6: 린트 [34]·골든 S40·S41·v1.28.0 릴리스

**Files:**
- Modify: `scripts/lint-consistency.sh` — 헤더 목록, `[33/33]` 블록 뒤에 새 블록, 분모 33→34 전역 치환
- Modify: `[N/33]`을 인용하는 `.claude/`·`README.md` 파일 전부
- Modify: `tests/golden-scenarios.md` — S40·S41 행, `N/39` → `N/41`
- Modify: `CHANGELOG.md` — v1.28.0 절
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` — `1.27.0` → `1.28.0`

**Interfaces:**
- Consumes: Task 1~4의 문자열 (`### Step 2-V`, `## 태스크 범위 모드`, `[태스크 리뷰 유예 Minor`, `태스크 범위 모드`)
- Produces: 린트 `[34/34] gx-tdd 태스크 리뷰 계약`

- [ ] **Step 1: 새 검사를 `[33/33]` 블록 뒤(`if [ "$FAIL" -ne 0 ]` 앞)에 추가한다 (분모는 아직 33)**

```bash
echo "[34/33] gx-tdd 태스크 리뷰 계약"
# 설계: docs/specs/2026-09-09-superpowers-gap-design.md D1
IMPL=.claude/skills/gx-tdd/phases/phase-implement.md
SEC=$(awk '/^### Step 2-V: 태스크 리뷰/{f=1} /^## Step 3: 정체 감지/{f=0} f' "$IMPL")
[ -n "$SEC" ] || fail "Step 2-V 태스크 리뷰 절 누락: phase-implement.md"
for s in '프로덕션 파일이 2개 이상' 'fix-round' 'reports/t{N}-diff.txt' 'reports/t{N}-review.md' 'reports/t{N}-diff-r{r}.txt' 'model: "sonnet"' 'subagent_type="oh-my-gx:reviewer"' 'deferred-minors' 'NOT ADDRESSED' 'GIT_INDEX_FILE'; do
  printf '%s' "$SEC" | grep -qF "$s" || fail "태스크 리뷰 계약 문구 누락($s): phase-implement.md Step 2-V"
done
grep -qF '## 태스크 범위 모드' agents/reviewer.md || fail "태스크 범위 모드 절 누락: agents/reviewer.md"
grep -qF '## 재리뷰 판정' agents/reviewer.md || fail "재리뷰 판정 표 형식 누락: agents/reviewer.md"
grep -qF '[태스크 리뷰 유예 Minor' .claude/skills/gx-tdd/phases/phase-review.md || fail "유예 Minor 전달 누락: phase-review.md Task A"
grep -qF '태스크 범위 모드' .claude/skills/gx-tdd/SKILL.md || fail "태스크 범위 모드 언급 누락: gx-tdd SKILL.md"
[ "$FAIL" -eq 0 ] && ok "Step 2-V 절·발동 조건·diff/report 경로·sonnet 디스패치·재리뷰·유예 Minor 전달 확인"
```

스크립트 헤더의 검사 항목 주석 목록 `# 33. …` 아래에 같은 형식으로 추가한다:

```
# 34. gx-tdd 태스크 리뷰 계약 (Step 2-V 절·발동 조건·diff/report 경로·sonnet 디스패치·재리뷰·유예 Minor 전달)
```

- [ ] **Step 2: 분모를 34로 올린다**

```bash
sed -i 's|/33\]|/34]|g' scripts/lint-consistency.sh
grep -rlE '\[[0-9]+/33\]' .claude README.md --include=*.md --exclude-dir=worktrees | xargs -r sed -i 's|/33\]|/34]|g'
grep -rnE '\[[0-9]+/33\]' .claude README.md scripts --include=*.md --include=*.sh | grep -v worktrees
```
Expected: 마지막 grep 출력 없음 (Task 4에서 `[34/33]`으로 적어 둔 maintenance-notes 인용도 `[34/34]`가 된다).

- [ ] **Step 3: 변이 시험 (RED)**

Run: `sed -i 's|### Step 2-V: 태스크 리뷰|### Step 2-V: 태스크 검토|' .claude/skills/gx-tdd/phases/phase-implement.md && bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `Step 2-V 태스크 리뷰 절 누락`으로 FAIL, exit 1.

Run: `git checkout -- .claude/skills/gx-tdd/phases/phase-implement.md && sed -i 's|model: "sonnet"|model: "haiku"|' .claude/skills/gx-tdd/phases/phase-implement.md && bash scripts/lint-consistency.sh; echo "exit=$?"; git checkout -- .claude/skills/gx-tdd/phases/phase-implement.md`
Expected: `model: "sonnet"` 누락으로 FAIL, exit 1. 복원 후 다음 단계.

- [ ] **Step 4: 골든 시나리오 두 행을 추가한다**

S39 행 아래에 추가하고, 기록 절의 `N/39`를 `N/41`로 바꾼다.

```markdown
| S40 ★ | AC 1건이 프로덕션 파일 2개(서비스+리포지토리)에 걸치는 태스크, 전체 모드 | `/gx-tdd 포인트 충전 한도 검증 TDD로 구현해줘` | verify_implement 통과 직후 `reports/t{N}-diff.txt`가 만들어지고 reviewer가 `model: "sonnet"`으로 1회 디스패치된다. 출력이 `reports/t{N}-review.md`에 저장되고 state.md 태스크 객체에 `review: completed`가 남는다. Important [동작결함]이 나오면 fix 라운드가 오르고 재리뷰가 `## 재리뷰 판정` 표를 낸다. 실제 인덱스는 스테이징되지 않는다(`git diff --cached`가 비어 있다) | phase-implement Step 2-V + 린트 [34/34] |
| S41 | 프로덕션 파일 1개만 바꾸고 fix 라운드 없이 통과한 태스크 | 같은 요청 | reviewer 디스패치 없이 state.md에 `review: skipped`가 기록되고 다음 태스크로 진행한다. phase-review는 그대로 1회 수행된다 | phase-implement Step 2-V 발동 조건 |
```

- [ ] **Step 5: CHANGELOG와 버전**

CHANGELOG 상단에 추가한다:

```markdown
## v1.28.0 (2026-09-09)

세션 IMPLEMENT의 자기 검증 편향을 상쇄하는 조건부 태스크 리뷰를 넣는다. superpowers subagent-driven-development의 태스크 리뷰 층을 가져오되, 태스크마다 붙이지 않고 편향이 커지는 태스크에만 붙인다. 설계: `docs/specs/2026-09-09-superpowers-gap-design.md` D1.

- **추가 — phase-implement Step 2-V 태스크 리뷰**: verify_implement 통과 직후, 프로덕션 파일을 2개 이상 바꿨거나 fix 라운드를 거친 태스크에만 `reviewer`를 태스크 범위 모드(`model: "sonnet"`)로 디스패치한다. 변경 파일은 verify_red porcelain 스냅샷과의 차이로 기계 판정하고, 태스크 diff는 임시 인덱스로 `reports/t{N}-diff.txt`에 쓴다(실제 인덱스·스냅샷 대조 무영향). findings는 기존 fix loop(라운드 5 공유)로, Minor는 phase-review Task A에 유예 목록으로 넘긴다. 재리뷰는 findings + 수정 diff만 보는 scoped 재리뷰다
- **추가 — reviewer 태스크 범위 모드**: 전달된 AC만 Part 1 대상, `## 재리뷰 판정`(ADDRESSED/NOT ADDRESSED) 표. Iron Law·판정 블록·금지 사항은 동일
- **변경 — phase-review는 전체 브랜치 리뷰**: 유예 Minor를 받아 머지 전 수정 필요 여부만 판정한다
- **검증 — 린트 [34] 태스크 리뷰 계약**, 골든 S40·S41. `[32]` SKILL.md 예산 62,500 → 63,000B(2-V 참조 3곳 도입분)
```

```bash
sed -i 's|"version": "1.27.0"|"version": "1.28.0"|' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
```
Expected: 세 파일 모두 `1.28.0`.

- [ ] **Step 6: 검증 (GREEN)**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 34/34 통과, 훅 테스트 통과.

- [ ] **Step 7: 커밋**

```bash
git add scripts/lint-consistency.sh .claude README.md tests/golden-scenarios.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json
git commit -F - <<'MSG'
feat: 린트 [34] 태스크 리뷰 계약과 v1.28.0 릴리스 준비
MSG
```

---

## 완료 기준

- 린트 34/34·훅 테스트 통과. `[32]` 예산 63,000B 이내.
- phase-implement의 `Task(subagent_type="oh-my-gx:reviewer")`는 Step 2-V 블록에만 있고 `model: "sonnet"`이 붙어 있다.
- 골든 S40을 실제로 한 번 돌려 `reports/t{N}-diff.txt`·`reports/t{N}-review.md` 생성, `git diff --cached` 비어 있음, state.md `review: completed`를 눈으로 확인한다 (PR 체크박스).
- 후속: D2 판정 규약(`2026-09-09-tdd-rulings.md`)이 이 계획의 findings 라우팅 위에 올라간다.

## 최종 리뷰 반영 (실행 기록)

계획 Task 1의 결과 처리 3번 첫 불릿("… → **fix loop 진입**")은 실행 중 최종 리뷰 C1로 폐기됐다 — 기존 fix loop는 `test-file-hash`를 고정해 테스트를 추가할 수 없으므로 동작 결함을 RED 없이 고치는 경로였다. 반영본은 red-writer 재호출(재현 테스트 추가, verify_red 재적용·기준선 갱신)을 fix loop 앞에 둔다. 함께 반영: diff 수집 실패 감지·`core.quotePath=false`·한 Bash 호출, 스냅샷 부재 시 (b)만 판정, `[동작불변]` 라운드 소모, 라운드 4~5 격상 명시, 린트 [34] 핵심 문장·순서 검사, [31] `tests/` 포함. 스펙 D1도 같은 내용으로 정정했다.
