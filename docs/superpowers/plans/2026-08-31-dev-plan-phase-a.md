# .dev/plan.md Phase A 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `gx-dev`/`gx-tdd`가 `--work W01` 플래그로 `.dev/plan.md`의 작업 행을 읽어 도메인·요구사항·브랜치명을 자동 확정하고, 완료 시 그 행의 상태를 갱신·커밋한다.

**Architecture:** 신규 코드는 없다. 스킬 마크다운 문서(인자 파싱·phase-setup·phase-complete)에 절차를 추가하고, `scripts/lint-consistency.sh`의 검사 항목으로 문구 존재를 고정한다. 이 저장소의 검증 수단은 린트와 훅 회귀 테스트뿐이므로, 각 태스크는 "린트 검사 추가 → 실패 확인 → 문서 수정 → 통과 확인" 순서로 진행한다.

**Tech Stack:** Markdown (스킬 문서), Bash (`lint-consistency.sh`), Git

**Spec:** `docs/specs/2026-08-31-dev-plan-design.md`

## Global Constraints

- 한국어로 작성한다. 이모지를 쓰지 않는다. 사과 표현을 쓰지 않는다.
- `gx-dev`와 `gx-tdd`는 쌍둥이 문서다. 한쪽을 고치면 반드시 다른 쪽도 같은 층위로 고친다.
- 기존 동작을 바꾸지 않는다. `--work` 미사용 시 모든 경로가 이전과 동일해야 한다.
- 작업 ID는 `W` + 두 자리 숫자(`W01`)다. 하이픈을 넣지 않는다 — `config.json`의 `issueKey.pattern`(`^[A-Z]+-[0-9]+$`)에 매칭되면 브랜치명이 오염된다.
- 상태 값은 `대기` / `진행` / `완료` 세 가지 텍스트다. 이모지를 쓰지 않는다.
- 커밋 메시지 형식은 `docs: [plan] W01 완료`로 고정한다.
- 린트 항목 번호는 `[25/25]`가 된다. 기존 24개 echo 줄과 상단 주석 블록을 함께 수정한다.

---

### Task 1: 린트 번호 재부여와 신규 검사 골격

**Files:**
- Modify: `scripts/lint-consistency.sh` (상단 주석 블록 6~29행, 24개 `echo "[N/24]"` 줄)

**Interfaces:**
- Produces: `[25/25] 작업 계획(plan.md) 계약` 검사 블록. 이후 Task 2~5가 이 블록에 검사를 추가한다.

- [ ] **Step 1: 현재 번호 표기를 전수 확인**

```bash
grep -n '\[[0-9]*/24\]' scripts/lint-consistency.sh | wc -l
grep -n '^#  [0-9]*\.' scripts/lint-consistency.sh | wc -l
```

Expected: 앞은 24, 뒤는 24 (주석 목록)

- [ ] **Step 2: `/24` → `/25` 일괄 치환**

```bash
sed -i 's|/24\]|/25]|g' scripts/lint-consistency.sh
grep -c '/25\]' scripts/lint-consistency.sh
```

Expected: 24

- [ ] **Step 3: 상단 주석에 25번 항목 추가**

`scripts/lint-consistency.sh`의 주석 블록 마지막 항목(`# 24. 하네스·복수 타입 검증 계약`) 바로 아래에 추가한다.

```
# 25. 작업 계획(.dev/plan.md) 계약 — --work 인자·읽기·갱신·커밋 규칙의 3지점 문구 대조
```

- [ ] **Step 4: 25번 검사 블록 골격 추가**

`echo "[24/25] 하네스·복수 타입 검증 계약"` 블록의 마지막 `ok "..."` 줄 다음, 최종 판정부(`if [ "$FAIL" -ne 0 ]`) 앞에 추가한다.

```bash
echo "[25/25] 작업 계획(plan.md) 계약"
# --work 플래그·읽기 절차·갱신 Step·커밋 규칙이 dev/tdd 양쪽과 라우팅 규칙에 대칭으로 존재하는지 대조한다.
# plan.md 자체는 소비 프로젝트의 런타임 파일이라 이 저장소에 없다 — 문구 존재만 검사하고,
# 표 파싱·의존 그래프 검증은 Phase C의 scripts/plan-lint.py가 담당한다.
[ "$FAIL" -eq 0 ] && ok "작업 계획 계약 확인"
```

- [ ] **Step 5: 문법·실행 확인**

```bash
bash -n scripts/lint-consistency.sh && bash scripts/lint-consistency.sh 2>&1 | tail -3
```

Expected: `[25/25] 작업 계획(plan.md) 계약` 출력 후 `정합성 린트 통과`

- [ ] **Step 6: 커밋**

```bash
git add scripts/lint-consistency.sh
git commit -m "chore: 정합성 린트에 작업 계획 계약 항목을 신설한다"
```

---

### Task 2: `--work` 인자 파싱

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` (인자 파싱 절 — 앵커: `- \`--core\`, \`--phase\`, \`--base\`, \`--status\`, \`--resume\`이 포함되면`)
- Modify: `.claude/skills/gx-dev/SKILL.md` (같은 층위의 인자 파싱 절)
- Modify: `scripts/lint-consistency.sh` (`[25/25]` 블록)

**Interfaces:**
- Consumes: Task 1의 `[25/25]` 블록
- Produces: `--work {ID}` 플래그가 파싱되어 `WORK_ID` 변수로 이후 phase에 전달된다. Task 3의 phase-setup이 이 값을 소비한다.

- [ ] **Step 1: 린트에 검사 추가 (실패하는 상태를 만든다)**

`[25/25]` 블록의 `[ "$FAIL" -eq 0 ]` 줄 앞에 추가한다.

```bash
for f in .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md; do
  grep -q '\-\-work' "$f" || fail "--work 플래그 파싱 규칙 누락: $f"
done
```

- [ ] **Step 2: 실패 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | grep -E "FAIL|실패"
```

Expected: `FAIL: --work 플래그 파싱 규칙 누락` 2건

- [ ] **Step 3: gx-tdd SKILL.md에 파싱 규칙 추가**

인자 파싱 절의 `--eco`/`--standard` 설명 줄 다음에 추가한다.

```
- `--work {ID}`가 포함되면 **작업 계획 참조 플래그**로 기록한다 (`.dev/plan.md`의 해당 행에서 도메인·요구사항·브랜치명을 확정한다 — phase-setup "작업 계획 참조" 절 참조). ID는 `W` + 두 자리 숫자 형식이다. 작업 계획 플래그는 모드 판정과 독립이므로 나머지 플래그·자연어 파싱을 계속 진행한다.
- `--work`와 `--resume`은 **동시 사용 불가**다. `--resume`은 state.md의 `work-id`에서 문맥을 복원하므로 작업 ID를 다시 받을 이유가 없다. 동시 지정 시 "`--work`와 `--resume`은 동시에 사용할 수 없습니다." 안내 후 중단한다.
```

- [ ] **Step 4: gx-dev SKILL.md에 같은 규칙 추가**

위와 동일한 두 줄을 gx-dev SKILL.md의 같은 위치에 추가한다. 문구를 그대로 복제한다 (쌍둥이 대칭).

- [ ] **Step 5: 통과 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | tail -3
```

Expected: `정합성 린트 통과`

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md scripts/lint-consistency.sh
git commit -m "feat: 파이프라인에 작업 계획 참조 플래그를 추가한다"
```

---

### Task 3: phase-setup 읽기 처리

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` (도메인 컨텍스트 탐색 절 — 앵커: `context/*/PROJECTS.md를 Grep하여 해당 레포를 참조하는 도메인을 찾는다`)
- Modify: `.claude/skills/gx-dev/phases/phase-setup.md` (같은 절)
- Modify: `scripts/lint-consistency.sh`

**Interfaces:**
- Consumes: Task 2의 `--work {ID}` 파싱 결과
- Produces: `state.md`에 `work-id: W01` 필드. Task 4의 phase-complete가 이 값으로 행을 찾는다.

- [ ] **Step 1: 린트에 검사 추가**

`[25/25]` 블록에 추가한다.

```bash
for f in .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md; do
  grep -q '작업 계획 참조' "$f" || fail "작업 계획 참조 절 누락: $f"
  grep -q 'work-id' "$f" || fail "state.md work-id 기록 누락: $f"
done
```

- [ ] **Step 2: 실패 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | grep -E "FAIL"
```

Expected: 4건 (파일 2개 × 검사 2개)

- [ ] **Step 3: gx-tdd phase-setup.md에 절 추가**

"도메인 컨텍스트 탐색" 항목(4번) 바로 앞에 새 절을 삽입한다.

```
### 작업 계획 참조 (`--work` 사용 시)

`--work {ID}`가 지정된 경우에만 아래를 수행한다. 지정되지 않았으면 이 절을 통째로 건너뛰고 기존 절차(4번 도메인 컨텍스트 탐색)로 진행한다.

1. `.dev/plan.md`를 Read한다. 파일이 없으면 "작업 계획이 없습니다. `.dev/plan.md`를 만들거나 `--work` 없이 실행하세요." 출력 후 중단한다.
2. 표에서 ID가 일치하는 행을 찾는다. 표 파싱에 실패하거나 행이 없으면 "작업 계획에서 {ID} 행을 찾지 못했습니다." 출력 후 중단한다. 조용히 진행하지 않는다.
3. **이슈 키 추출을 건너뛴다.** 아래 "이슈 키 추출" 단계를 수행하지 않는다 — 작업 ID가 이슈 키로 오인되면 브랜치명이 오염되어 gx-commit의 타입 파싱이 깨진다.
4. **브랜치명을 `작업` 열에서 생성한다.** `{type}/{작업 열을 슬러그화한 값}` 형식이며 type은 AskUserQuestion으로 확인한다 (기본값 `feat`). svn이면 브랜치 대신 slug로 쓴다.
5. **코드 맵 키워드**를 `작업` + `요구사항` 열 텍스트에서 추출한다.
6. **도메인 컨텍스트**를 `도메인` 열의 도메인 하나만 로드한다 (`glossary.md`·`architecture.md`·`status.md`). 도메인이 예약어 `공통` 또는 `통합`이면 context를 읽지 않고 `DOMAIN_CONTEXT`를 빈 상태로 둔다. 이 경우 아래 4번 항목(레포 매칭 탐색)은 수행하지 않는다.
7. **의존 확인**: `의존` 열의 각 ID가 표에서 `완료` 상태인지 확인한다. 아닌 것이 있으면 AskUserQuestion으로 진행 여부를 확인한다.
8. **착수 기록**: `작업 위치` 열에 브랜치명(svn은 slug)을 기입하고 `상태` 열을 `진행`으로 바꾼다. 기입 전 값이 `-`가 아니면 다른 사람이 이미 착수한 것이므로 경고하고 확인받는다.
9. **ARGS[0] 보강**: `작업` 열 텍스트를 요청 문구로 사용한다.
```

- [ ] **Step 4: state.md 스키마에 필드 추가**

같은 파일의 state.md 스키마 절(`mode:`·`model-profile:` 등이 나열된 곳)에 추가한다.

```
work-id: W01        # --work로 진입한 경우의 작업 ID. 미사용 시 생략. phase-complete가 plan.md 행 매칭에 사용한다
```

- [ ] **Step 5: gx-dev phase-setup.md에 동일 적용**

Step 3·4의 내용을 gx-dev phase-setup.md의 같은 위치에 그대로 복제한다.

- [ ] **Step 6: 통과 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | tail -3
```

Expected: `정합성 린트 통과`

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md scripts/lint-consistency.sh
git commit -m "feat: phase-setup이 작업 계획 행을 읽어 도메인과 브랜치를 확정한다"
```

---

### Task 4: phase-complete 갱신 Step

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md` (Step 3 다음)
- Modify: `.claude/skills/gx-dev/phases/phase-complete.md` (Step 3 다음)
- Modify: `.claude/rules/skill-routing.md` (예외 목록 — 앵커: `**예외**: gx-dev phase-complete의 "context 변경사항 자동 커밋"`)
- Modify: `scripts/lint-consistency.sh`

**Interfaces:**
- Consumes: Task 3이 기록한 `state.md`의 `work-id`
- Produces: `.dev/plan.md`의 해당 행이 `완료`로 바뀌고 `docs: [plan] {ID} 완료` 메시지로 커밋된다.

- [ ] **Step 1: 린트에 검사 추가**

```bash
for f in .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-dev/phases/phase-complete.md; do
  grep -q 'docs: \[plan\]' "$f" || fail "plan.md 전용 커밋 규칙 누락: $f"
done
grep -q 'docs: \[plan\]' .claude/rules/skill-routing.md || fail "skill-routing 예외 목록에 plan 커밋 미등록"
```

- [ ] **Step 2: 실패 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | grep -E "FAIL"
```

Expected: 3건

- [ ] **Step 3: gx-tdd phase-complete.md에 Step 3.5 추가**

Step 3(도메인 status.md 갱신) 블록이 끝나는 지점, Step 4 시작 전에 삽입한다.

```
## Step 3.5: 작업 계획(plan.md) 갱신

**Step 3과 독립적으로 판정한다.** Step 3은 `DOMAIN_CONTEXT` 존재와 인수 검증 ACCEPT를 조건으로 하지만, 이 단계는 그와 무관하게 아래만 확인한다. `--phase complete` 경로는 phase-setup을 거치지 않아 `DOMAIN_CONTEXT`가 비어 있으므로, Step 3에 종속시키면 갱신이 영영 일어나지 않는다.

**진입 조건**: `.dev/plan.md`가 존재한다.

1. 행을 찾는다. state.md에 `work-id`가 있으면 그 ID의 행을, 없으면 `작업 위치` 열이 현재 브랜치(svn은 `.dev/.active`의 slug)와 일치하는 행을 쓴다.
2. **행이 없으면 아무것도 하지 않고 Step 4로 넘어간다.** `--work` 없이 시작한 작업은 계획에 없는 것이 정상이며, 이 시점은 커밋·PR이 이미 끝난 뒤라 중단할 수 없다.
3. `상태` 열을 `완료`로 바꾼다.
4. **전용 커밋**: `.dev/plan.md`만 스테이징하여 `docs: [plan] {ID} 완료` 메시지로 커밋하고 push한다. 기능 코드가 아닌 계획 문서 동기화 전용이며, gx-dev의 `docs: [context] …` 커밋과 같은 층위의 예외다 (skill-routing.md 명시). svn이면 커밋하지 않고 사용자에게 안내한다.

**status.md는 건드리지 않는다.** status.md 갱신은 Step 3이 AC 축으로 수행한다. plan.md의 `요구사항` 열은 참조 표기일 뿐이며, 여기서 전파하면 부분 통과한 AC까지 완료로 뒤집힌다.

**되돌림**: `status: completed`인 state.md에 재진입해 `status: in_progress`로 되돌릴 때, plan.md의 해당 행도 `완료 → 진행`으로 되돌린다. 되돌리지 않으면 다른 팀원이 미검증 산출물을 전제로 후속 작업에 착수한다.
```

- [ ] **Step 4: gx-dev phase-complete.md에 동일 적용**

Step 3(경로 A/B 분기)이 끝난 뒤, context 자동 커밋 절 앞에 같은 내용을 삽입한다. 문구를 그대로 복제한다.

- [ ] **Step 5: skill-routing.md 예외 목록에 추가**

`**예외**: gx-dev phase-complete의 "context 변경사항 자동 커밋"…` 문장 끝에 이어 붙인다.

```
 phase-complete Step 3.5의 작업 계획 갱신 커밋(`docs: [plan] …`)도 같은 예외다 — `.dev/plan.md` 한 파일만 스테이징하며 기능 코드를 포함하지 않는다.
```

- [ ] **Step 6: 통과 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | tail -3 && bash scripts/hook-tests.sh 2>&1 | tail -2
```

Expected: 린트 통과, 훅 회귀 통과

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-dev/phases/phase-complete.md .claude/rules/skill-routing.md scripts/lint-consistency.sh
git commit -m "feat: 완료 시 작업 계획 행을 갱신하고 전용 커밋으로 공유한다"
```

---

### Task 5: gx-ralph-iterate 갱신과 사용자 문서

**Files:**
- Modify: `.claude/skills/gx-ralph-iterate/SKILL.md`
- Modify: `README.md` (사용법 절)
- Modify: `scripts/lint-consistency.sh`

**Interfaces:**
- Consumes: Task 4의 Step 3.5 절차
- Produces: 없음 (Phase A 종료)

- [ ] **Step 1: 린트에 검사 추가**

```bash
grep -q 'plan.md' .claude/skills/gx-ralph-iterate/SKILL.md || fail "ralph 반복에 작업 계획 갱신 누락"
grep -q '\-\-work' README.md || fail "README에 --work 사용법 누락"
```

- [ ] **Step 2: 실패 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | grep -E "FAIL"
```

Expected: 2건

- [ ] **Step 3: gx-ralph-iterate에 갱신 지시 추가**

반복 종료(커밋 완료) 절 다음에 추가한다.

```
### 작업 계획 갱신

`.dev/plan.md`가 존재하고 state.md에 `work-id`가 있으면, 해당 행의 `상태`를 `완료`로 바꾸고 `docs: [plan] {ID} 완료` 메시지로 커밋한다. 이 루프는 phase-complete를 거치지 않으므로 여기서 직접 수행한다. 행이 없으면 건너뛴다.
```

- [ ] **Step 4: README에 사용법 추가**

"사용법" 절의 개발 예시 표 아래에 추가한다.

```
**작업 계획으로 진행하기**

요구사항이 여러 건이면 `.dev/plan.md`에 작업 목록을 만들어두고 ID로 호출합니다. 도메인과 요구사항 범위를 매번 설명할 필요가 없습니다.

```
/gx-tdd --work W01
```

`.dev/plan.md`는 저장소에 공유되므로 팀원이 `git pull` 후 같은 계획을 봅니다. 의존이 걸린 작업은 선행 작업이 완료되지 않았음을 경고합니다.
```

- [ ] **Step 5: 통과 확인**

```bash
bash scripts/lint-consistency.sh 2>&1 | tail -3
```

Expected: `정합성 린트 통과`

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-ralph-iterate/SKILL.md README.md scripts/lint-consistency.sh
git commit -m "docs: 랄프 반복과 사용자 문서에 작업 계획을 반영한다"
```

---

### Task 6: 통합 검증

**Files:**
- Create: `tests/fixtures/plan-valid.md`

**Interfaces:**
- Consumes: Task 1~5 전체
- Produces: Phase C(그래프 린트)가 사용할 정상 픽스처

- [ ] **Step 1: 정상 픽스처 작성**

```markdown
# 작업 계획

| ID | 작업 | 도메인 | 요구사항 | 의존 | 작업 위치 | 상태 |
|----|------|--------|----------|------|-----------|------|
| W00 | 기초 스키마 | 공통 | FR-1~3 | - | feat/base-schema | 완료 |
| W01 | 이력 조회 | 재고관리 | FR-4~6 | W00 | feat/history | 진행 |
| W02 | 분류 규칙 | 재고관리 | FR-7~9 | W00 | - | 대기 |
| W03 | 통합 화면 | 통합 | FR-30 | W01,W02 | - | 대기 |
```

- [ ] **Step 2: 쌍둥이 대칭 수동 확인**

```bash
for k in '--work' 'work-id' '작업 계획 참조' 'docs: \[plan\]'; do
  printf "%-20s tdd=%s dev=%s\n" "$k" \
    "$(grep -rl "$k" .claude/skills/gx-tdd/ | wc -l)" \
    "$(grep -rl "$k" .claude/skills/gx-dev/ | wc -l)"
done
```

Expected: 각 키워드의 tdd/dev 파일 수가 동일

- [ ] **Step 3: 하위 호환 확인 — `--work` 없는 경로가 그대로인지**

```bash
git diff main --stat -- .claude/skills/gx-tdd/phases/phase-setup.md
grep -c '작업 계획 참조' .claude/skills/gx-tdd/phases/phase-setup.md
```

Expected: 추가만 있고 기존 절 삭제 없음. `작업 계획 참조` 절이 조건부(`--work` 사용 시)로 진입하는지 육안 확인.

- [ ] **Step 4: 전체 검증**

```bash
bash scripts/lint-consistency.sh 2>&1 | tail -3
bash scripts/hook-tests.sh 2>&1 | tail -2
bash scripts/test-gx-ralph.sh 2>&1 | tail -2
```

Expected: 3개 모두 통과

- [ ] **Step 5: 커밋**

```bash
git add tests/fixtures/plan-valid.md
git commit -m "test: 작업 계획 정상 픽스처를 추가한다"
```

---

## Phase A 완료 기준

- [ ] `--work W01`로 gx-tdd·gx-dev를 호출하면 `.dev/plan.md`의 행에서 도메인·요구사항·브랜치명이 확정된다
- [ ] `--work` 없이 호출하면 기존과 동일하게 동작한다 (plan.md를 읽지 않는다)
- [ ] 완료 시 해당 행이 `완료`로 바뀌고 `docs: [plan] W01 완료`로 커밋된다
- [ ] `--phase complete` 경로에서도 갱신이 동작한다
- [ ] 린트 25/25, 훅 회귀, ralph 테스트가 모두 통과한다

## Phase A에 포함하지 않은 것

| 항목 | 단계 |
|------|------|
| `gx-context --from`이 plan.md를 생성 | Phase B |
| 의존 그래프 순환·실존 검사 (`scripts/plan-lint.py`) | Phase C |
| 오류 픽스처 (`plan-cycle.md`·`plan-badref.md`) | Phase C |

Phase A만으로 기능이 성립한다. 계획을 손으로 쓰면 파이프라인이 읽고 갱신한다.
