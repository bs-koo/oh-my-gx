# gx-tdd 테스트 실행 횟수 축소 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-tdd가 W 하나에서 돌리는 전체 테스트 스위트를 기준선 1회(사전 실행) + verify 1회로 줄인다.

**Architecture:** 스킬은 문서(phase 지시문)이므로 "구현"은 phase·에이전트·참조 문서의 계약 문구를 바꾸는 것이다. 각 계약을 `tests/test_codex_skill_pipeline.py`의 문서 계약 assert와 실행 가능한 판정 probe로 먼저 고정(RED)한 뒤 문서를 고쳐 통과(GREEN)시킨다.

**Tech Stack:** Markdown 스킬 문서, Python unittest, Bash(린트·probe), `scripts/sync-codex-resources.py`

**Spec:** `docs/superpowers/specs/2026-10-14-gx-tdd-test-run-reduction-design.md`

## Global Constraints

- 작업 위치: 워크트리 `D:\SQ\oh-my-gx\.claude\worktrees\gx-tdd-test-runs`, 브랜치 `perf/gx-tdd-test-runs`. 이 경로 밖 파일을 고치지 않는다.
- 린트 존재 검사 문자열 유지: `'SSOT는 config'`, `'복수 타입'`(phase-review·phase-implement·gx-verify), `'테스트 하네스 부재'`, `'레이어별 하네스'`, `'프론트 AC 제외'`, `'focused 집합 직접 실행'`, `## Step 0.7: gx-ralph 전환 (--ralph 전용)`, `'라운드 5'`.
- `phase-setup.md`는 고치지 않는다 (바이트 예산 22000B, 금지 문자열 `'Step 3.5'`).
- phase-implement에서 Step 2-I보다 앞에 행 시작 `Task(subagent_type="oh-my-gx:implementer")` 블록을 넣지 않는다.
- `agents/implementer.md`를 고치면 `python scripts/sync-codex-resources.py`로 codex-roles를 재생성한다. 생성물을 직접 고치지 않는다.
- implementer 프롬프트 플레이스홀더 원문을 바꾸면 `tests/fixtures/behavior/b2/subs.json` 키도 같이 바꾼다.
- 린트 항목을 추가하지 않는다 (`[N/36]` 분모 유지).
- 이력 문서(`docs/specs/2026-09-01-*`, `docs/superpowers/plans/2026-09-01-*`, 발표 자료)는 고치지 않는다.
- 커밋: 이 저장소는 커밋을 `oh-my-gx:gx-commit` 스킬로만 한다 (전체 스테이징). 계획 전체를 마치고 Codex 리뷰 반영 후 사용자 확인을 받아 한 번에 커밋한다.
- 린트 실행은 약 4분 — Bash `timeout: 600000`.

## Review Focus

1. **사전 실행 결과가 불완전한데 수용됨** — `DONE`은 있지만 한 타입의 build 줄이 없거나 로그가 없거나 종료 지문이 다른 경우는 반드시 동기 실행으로 가야 한다. → Task 3의 probe 테스트가 고정한다.
2. **rc≠0인 사전 실행을 "재실행 대상"으로 오판** — 실패한 기준선도 완료된 측정이므로 수용 후 판정 1(기준 GREEN 실패 보고)로 가야 한다. 버리고 다시 돌리면 실패가 20분 뒤 똑같이 재현될 뿐이다. → Task 3 probe의 rc=1 케이스.
3. **HEAD만 바뀌고 트리는 같은 경우** — 설계 중 `.dev/` 커밋(착수 기록 등)으로 HEAD가 움직여도 코드 트리가 같으면 수용해야 한다. → Task 3 probe의 HEAD 상이 케이스.
4. **`--phase review` 단독·ralph 이후 리뷰의 누적 focused** — `test-file` 기록이 없으므로 조용히 0건 실행이 되면 안 되고 전체 폴백이어야 한다. → Task 1 assert.
5. **verify 차단 "수정" 후 이전 통과 기록 잔존** — 수리 중 `verify-status: passed`가 남으면 커밋 게이트가 열린다. → Task 4 assert.

---

### Task 1: 리뷰 Step 0을 "Step 0 테스트 집합"으로 바꾼다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` (Step 0 서두 :26, Step 0-1 :32-42, Step 0-2 :54-66, Gate 통과 기준 :70, Step 4.4 :295-318, state 예시 :343, 금지 사항 :375)
- Test: `tests/test_codex_skill_pipeline.py` (새 클래스 `TestRunBudgetContractTests`)

**Interfaces:**
- Produces: 용어 "Step 0 테스트 집합"(phase-review Step 0-2 정의 — Task 2·5가 참조), 헬퍼 `section(text, start, end)`와 상수 `TDD_PHASES`, `IMPLEMENTER` (Task 2~4가 같은 클래스에 테스트를 추가)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_codex_skill_pipeline.py`의 `if __name__ == "__main__":` 바로 위에 추가

```python
TDD_PHASES = ROOT / ".claude/skills/gx-tdd/phases"
IMPLEMENTER = ROOT / "agents/implementer.md"


def section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    stop = text.index(end, begin + len(start))
    return text[begin:stop]


class TestRunBudgetContractTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (TDD_PHASES / name).read_text(encoding="utf-8")

    def test_review_gate_runs_pipeline_tests_not_full_suite(self):
        text = self.read("phase-review.md")
        gate = section(text, "## Step 0: Mechanical Gate", "## Step 1:")
        for needle in (
            "Step 0 테스트 집합",
            "무결성 선확인",
            "누적 focused",
            "전체 폴백",
            "`test-file` 기록이 하나도 없음",
            "`focusedTest` 없음",
            "명령 자체 오류",
            "-x test",
            "기존 스위트 전체 회귀는 phase-complete의 verify 게이트가 1회 맡는다",
            "SSOT는 config",
            "복수 타입",
        ):
            self.assertIn(needle, gate)
        handling = section(text, "### Step 4.4", "## state.md 추적")
        self.assertNotIn("전체 테스트 1회 직접 실행", handling)
        self.assertGreaterEqual(handling.count("Step 0 테스트 집합"), 3)
        self.assertNotIn("정리 후 전체 테스트 GREEN", text)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v`
Expected: FAIL — `'Step 0 테스트 집합' not found`

- [ ] **Step 3: phase-review.md 수정**

(a) :26 문단 교체

```
리뷰 에이전트 호출 전에 기계적 검증을 통과시킨다. 실패하는 코드를 리뷰하는 것은 토큰 낭비이다. 이 Gate는 **이번 파이프라인이 만든 테스트와 빌드의 GREEN**을 보장한다 — 태스크마다 그 태스크 테스트만 돌렸으므로 여기서 태스크 간 회귀를 한 번에 확인한다. **기존 스위트 전체 회귀는 phase-complete의 verify 게이트가 1회 맡는다** (이 Gate는 Step 0-2의 전체 폴백 경우가 아니면 전체 스위트를 돌리지 않는다).
```

(b) Step 0-1의 "빌드 명령 결정" 3항 뒤(`**실행 흐름**` 앞)에 문단 추가

```
**테스트 제외**: 이 Gate의 빌드는 테스트를 돌리지 않는다. 1·2에서 정한 명령이 테스트를 포함하면(gradle `build`·`clean build` 등) 테스트 제외 변형(gradle `-x test`)으로 바꿔 실행하고 `clean`은 붙이지 않는다. 테스트는 Step 0-2가 맡는다.
```

(c) Step 0-2의 `**테스트 명령 결정**` 문단을 아래로 교체하고, 실행 흐름 1·4항을 고친다

```
**Step 0 테스트 집합** (이 Gate의 첫 실행·재시도와 Step 4.4의 4b·4c 재확인이 모두 이 정의를 쓴다):

1. **무결성 선확인**: state.md `steps.implement`의 모든 태스크 `test-file-hash`를 현재 파일의 해시(`git hash-object`)와 대조한다. 불일치나 파일 부재가 있으면 테스트를 실행하지 않고 phase-implement verify_implement 3의 무단 수정 처리(RED 산출물로 원복 후 재수행, 재차 위반 시 사용자 보고)를 따른다. 정당한 테스트 변경은 red-writer 재호출 때 verify_red가 해시를 다시 기록하므로 이 대조에 걸리지 않는다.
2. **누적 focused**: 모든 태스크의 `test-file`(경로 하나 또는 경로 목록)을 모아 중복을 제거하고, 파일마다 태스크 focused와 같은 방식으로 프로젝트 타입을 정해 타입별로 config `focusedTest` 템플릿에 대입한다 (조립 규칙은 phase-implement "focused 테스트 명령 조립").
3. **전체 폴백**: 아래 중 하나면 그 타입은 config `test` 명령(전체)을 실행하고 사유를 execution-log에 남긴다 — `test-file` 기록이 하나도 없음(`--phase review` 단독·gx-ralph 루프 이후 리뷰·구 세션) / `test-file` 값을 경로로 해석할 수 없음 / 해당 타입에 `focusedTest` 없음 / focused 명령이 명령 자체 오류로 끝남(phase-implement 명령 오류 가드와 같은 판정).

타입에 `test` 필드도 없으면 → AskUserQuestion: "테스트 검증 명령을 감지하지 못했습니다." 선택지: 사용자가 직접 입력 / 건너뛰기. **조용히 건너뛰지 않는다** — 건너뛰기 선택 시 위험 수용으로 간주하고 trust-ledger에 "테스트 미검증 리뷰" 항목을 기록한다.
```

실행 흐름 1항: `1. Step 0 테스트 집합을 \`PROJECT_ROOT\`에서 실행한다.` / 4항: `4. 수정 후 같은 테스트 집합으로 **1회 재시도**한다.`

(d) Gate 통과 기준(:70)의 `각 타입의 build·test를 모두 돌리고` → `각 타입의 build와 Step 0 테스트 집합을 모두 돌리고`

(e) Step 4.4 의사코드
- `#  전제: Step0 mechanical gate(build+test 통과)로 이미 GREEN 상태가 보장됨` → `#  전제: Step0 mechanical gate(build + Step 0 테스트 집합 통과)로 이미 GREEN 상태가 보장됨`
- `GREEN 기준선은 Step 0에서 통과한 전체 테스트다` → `GREEN 기준선은 Step 0에서 통과한 Step 0 테스트 집합이다`
- `→ 어느 경로든 정리 후 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인` → `→ 어느 경로든 정리 후 오케스트레이터가 Step 0 테스트 집합 ∪ 정리 대상 파일 관련 테스트(중복 제거)를 1회 직접 실행해 GREEN 재확인 (전체 회귀는 phase-complete verify)`
- `4a RGR 수정이 기존 스위트를 깨뜨렸는지 전체 테스트로 먼저 확인한 뒤` → `4a RGR 수정이 이번 파이프라인 테스트를 깨뜨렸는지 Step 0 테스트 집합으로 먼저 확인한 뒤`
- `→ 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인 → 단발성 확인 리뷰 (반복 카운트 미포함)` → `→ 오케스트레이터가 Step 0 테스트 집합 ∪ 정리 대상 파일 관련 테스트(중복 제거)를 1회 직접 실행해 GREEN 재확인 → 단발성 확인 리뷰 (Step 0 재실행 없음, 반복 카운트 미포함)`

(f) state 예시 `result: "build ✓, test ✓"` → `result: "build ✓, test ✓ (Step 0 테스트 집합 — 전체 회귀는 verify)"`

(g) 금지 사항 절 끝 `단, 정리 후 전체 테스트 GREEN을 반드시 재확인한다.` → `단, 정리 후 Step 0 테스트 집합으로 GREEN을 반드시 재확인한다 (전체 회귀는 phase-complete verify).`

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v`
Expected: PASS (1 test)

---

### Task 2: 태스크 focused 범위·Step 3.5·implementer 계약

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (핵심 모드 분기 :21-30, 세션 절대 규칙 4 :315, 격리 프롬프트 규칙 4 :345·플레이스홀더 :362, focused 조립 :375, verify_implement 4 :386, Step 3.5 :513-515, 완료 보고 :530)
- Modify: `agents/implementer.md` (:37, :51, :114)
- Modify: `tests/fixtures/behavior/b2/subs.json` (키 1개)
- Regenerate: `.claude/skills/gx-dev/references/codex-roles/implementer.md`
- Test: `tests/test_codex_skill_pipeline.py`

**Interfaces:**
- Consumes: `section`, `TDD_PHASES`, `IMPLEMENTER` (Task 1)
- Produces: Step 3.5 제목 `## Step 3.5: 경계 회귀 (--phase implement 단독 전용)`, 수리 모드 호출처 문구 "verify 회귀 수리"(Task 4가 phase-complete에서 같은 이름을 쓴다)

- [ ] **Step 1: 실패 테스트 추가** (`TestRunBudgetContractTests` 안)

```python
    def test_task_focused_scope_is_task_only(self):
        text = self.read("phase-implement.md")
        implementer = IMPLEMENTER.read_text(encoding="utf-8")
        assembly = section(text, "**focused 테스트 명령 조립**", "**명령 오류 가드**")
        self.assertIn("이 태스크의 `test-file` 기록 파일만", assembly)
        self.assertNotIn("이전 태스크들이 만든 신규 테스트 파일 전부", text)
        self.assertGreaterEqual(text.count("와일드카드"), 3)
        for needle in ("와일드카드", "모듈 묶음", "verify 회귀 수리", "완료 verify"):
            self.assertIn(needle, implementer)
        self.assertNotIn("전체는 경계에서", implementer)
        self.assertIn("같은 태스크의 직전 `test-count`", text)
        self.assertNotIn("직전 태스크의 같은 방식 값", text)
        subs = ROOT / "tests/fixtures/behavior/b2/subs.json"
        import json
        for key in json.loads(subs.read_text(encoding="utf-8")):
            self.assertIn(key, text, key)

    def test_boundary_regression_only_without_following_verify(self):
        text = self.read("phase-implement.md")
        step = section(text, "## Step 3.5:", "## Step 4:")
        self.assertIn("## Step 3.5: 경계 회귀 (--phase implement 단독 전용)", step)
        self.assertIn("complete(verify)가 실행되지 않는 경로", step)
        core = section(text, "## 핵심 모드 분기 (core)", "## Step 0: 문서 로드")
        self.assertIn("Step 3.5(경계 회귀)는 건너뛴다", core)
        self.assertNotIn("핵심 모드·`--phase implement` 단독: Step 3.5", text)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v`
Expected: 2 FAIL (`이 태스크의 \`test-file\` 기록 파일만` not found, `Step 3.5: 경계 회귀 (--phase implement 단독 전용)` not found)

- [ ] **Step 3: phase-implement.md 수정**

(a) 핵심 모드 분기 목록의 `- Step H1~H4 (긴급 보안 감사)는 …` 앞에 항목 추가

```
- **Step 3.5(경계 회귀)는 건너뛴다** — 핵심 모드는 implement 다음이 곧 complete(verify)라, 실행하면 전체 스위트가 연달아 두 번 돈다.
```

(b) 세션 절대 규칙 4 교체

```
4. 테스트 실행은 focused 명령만 사용한다 — 대상은 이 태스크의 `test-file` 기록 파일뿐이며 와일드카드(`*DbTest` 등)·패키지/모듈 묶음·회귀 확인용 이웃 클래스를 덧붙이지 않는다. 전체 스위트는 완료 verify(`--phase implement` 단독은 Step 3.5)에서만 실행하고, 다른 테스트·빌드 명령이 실행 중이면 새 실행을 시작하지 않는다.
```

(c) 격리 프롬프트 규칙 4 교체 (4칸 들여쓰기 유지)

```
    4. 테스트 실행은 아래 focused 명령만 사용합니다. 명령에 테스트를 덧붙이거나 와일드카드·패키지/모듈 묶음으로 넓히지 않고, 전체 스위트를 임의로 실행하지 않습니다 (전달된 명령이 focusedTest 미등록 폴백으로 전체 test 명령이면 그 명령이 곧 focused 집합입니다).
```

(d) 플레이스홀더 `{오케스트레이터가 조립한 명령 — 대상 테스트 + 이번 파이프라인 실행의 신규 테스트 전부}` → `{오케스트레이터가 조립한 명령 — 이 태스크의 test-file 기록 파일만}`. `tests/fixtures/behavior/b2/subs.json`의 같은 키도 새 문자열로 바꾼다 (값은 유지).

(e) focused 조립 첫 문단 교체

```
**focused 테스트 명령 조립**: config.json `projectTypes.{타입}.focusedTest` 템플릿을 사용한다. 대상은 **이 태스크의 `test-file` 기록 파일만**이다 (`test-file`은 경로 하나 또는 경로 목록). 이전 태스크들의 테스트는 넣지 않는다 — 태스크 간 회귀는 phase-review Step 0의 누적 실행이, 기존 스위트 회귀는 완료 verify가 확인한다. 와일드카드(`*DbTest` 등)·패키지/모듈 묶음·회귀 확인용 이웃 클래스로 넓히지 않는다.
```

(f) verify_implement 4 교체

```
4. **focused 집합 직접 실행**: 위 focused 명령을 오케스트레이터가 1회 직접 실행한다 — 통과 목격(증거 주체는 오케스트레이터, verify_red와 대칭) + 결과의 테스트 수를 state.md 해당 태스크의 `test-count`로 기록한다. **같은 태스크의 직전 `test-count`와 비교**해 감소하면 사유를 확인한다(무단 삭제면 롤백 요청). 첫 기록이거나, 직전 기록 이후 red-writer 재호출로 verify_red가 `test-file-hash`를 다시 기록했으면(정당한 테스트 변경) 비교하지 않고 새 값을 기준으로 삼는다. 태스크마다 대상 집합이 다르므로 태스크 간 비교는 하지 않는다. **전체 스위트는 실행하지 않는다** — 태스크 간 회귀는 phase-review Step 0(누적 실행), 기존 스위트 회귀는 완료 verify(`--phase implement` 단독: Step 3.5)가 담당한다.
```

(g) Step 3.5 제목·첫 문장 교체 (나머지 수리 절차 문장은 유지)

```
## Step 3.5: 경계 회귀 (--phase implement 단독 전용)

**같은 실행 안에서 implement 뒤에 complete(verify)가 실행되지 않는 경로** — 현재는 `--phase implement` 단독 실행 — 이면 전체 테스트를 1회 실행한다. 사이클 중 태스크마다 그 태스크 테스트만 돌렸으므로 기존 스위트 회귀를 여기서 확인한다. 전체 모드(implement → review → complete)와 핵심 모드(implement → complete)는 같은 실행에서 verify가 전체 회귀를 맡으므로 건너뛴다. 실패 시 …(기존 문장 그대로)
```

(h) 완료 보고 템플릿 줄 교체

```
focused: 태스크별 {N pass}, 0 fail (태스크 간 회귀는 review Step 0, 전체 회귀는 complete verify — `--phase implement` 단독: Step 3.5)
```

- [ ] **Step 4: agents/implementer.md 수정**

- 절대 규칙 4 교체:
```
4. **테스트 실행은 focused 집합만.** 오케스트레이터가 전달한 focused 테스트 명령만 실행합니다. 명령에 테스트를 덧붙이거나 와일드카드·패키지/모듈 묶음으로 넓히지 않고, 전체 스위트를 임의로 실행하지 않습니다 (태스크 간 회귀는 리뷰 Gate, 전체 회귀는 완료 verify가 1회 실행합니다. 전달된 명령이 focusedTest 미등록 폴백으로 전체 test 명령이면 그 명령이 곧 focused 집합입니다).
```
- 수리 모드 괄호 `(리뷰 Gate 수리, 경계 회귀 수리)` → `(리뷰 Gate 수리, 경계 회귀 수리, verify 회귀 수리)`
- Red Flags `→ focused 집합만. 전체는 경계에서` → `→ focused 집합만. 전체는 완료 verify에서`

- [ ] **Step 5: codex-roles 재생성**

Run: `python scripts/sync-codex-resources.py` 후 `python scripts/sync-codex-resources.py --check`
Expected: check 출력에 불일치 없음, exit 0

- [ ] **Step 6: 통과 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v` 그리고 `bash scripts/test-behavior-tests.sh`
Expected: 3 tests OK, test-behavior-tests 전부 PASS

---

### Task 3: 기준선 사전 실행

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-requirements.md` (`**최대 1회 반복.**` 뒤, `## 핵심 모드 분기 (core)` 앞에 절 추가)
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (Step 0.5 서두 :47, `### 레이어별 하네스 게이트` 절 끝과 `## Step 0.7` 사이에 새 절)
- Modify: `.claude/skills/gx-tdd/references/harness-adaptation.md` (표 행 추가)
- Modify: `.claude/skills/gx-tdd/references/pipeline-state.md` (스키마 예시·갱신 규칙)
- Test: `tests/test_codex_skill_pipeline.py`

**Interfaces:**
- Consumes: `section`, `TDD_PHASES` (Task 1)
- Produces: 절 제목 `### 기준선 사전 실행 (Claude Code·git 전용)`(phase-implement), `## 기준선 사전 실행 (진입 직후)`(phase-requirements), state 필드 `baseline-fingerprint`, 파일 `${DEV_DIR}/baseline.done`·`${DEV_DIR}/baseline-{타입}-{test|build}.log`

- [ ] **Step 1: 실패 테스트 추가** — 모듈 상단 probe 상수는 `TDD_PHASES` 정의 바로 위에, 테스트 메서드는 클래스 안에

```python
# Executable approximation of the acceptance rule in phase-implement Step 0.5
# "기준선 사전 실행". It checks the decision table, not a model run.
BASELINE_ACCEPT_PROBE = r'''
accept() {
  local done="$1" start="$2" current="$3" dir="$4"; shift 4
  test -f "$done" || { echo sync; return; }
  test "$(tail -n 1 "$done")" = DONE || { echo sync; return; }
  local end; end=$(sed -n 's/^fingerprint-end=//p' "$done")
  test -n "$end" || { echo sync; return; }
  test "${start#*:}" = "${end#*:}" && test "${start#*:}" = "${current#*:}" || { echo sync; return; }
  local t k
  for t in "$@"; do
    for k in test build; do
      test "$(grep -c "^$t $k rc=[0-9][0-9]*$" "$done")" = 1 || { echo sync; return; }
      test -f "$dir/baseline-$t-$k.log" || { echo sync; return; }
    done
  done
  echo accept
}
accept "$DONE_FILE" "$START" "$CURRENT" "$DIR" $TYPES
'''
```

```python
    def test_baseline_prelaunch_contract(self):
        req = self.read("phase-requirements.md")
        trigger = section(req, "## 기준선 사전 실행 (진입 직후)", "## 핵심 모드 분기 (core)")
        self.assertIn("phase-implement.md", trigger)
        self.assertIn("Codex와 svn은 시작하지 않고", trigger)
        impl = self.read("phase-implement.md")
        pre = section(impl, "### 기준선 사전 실행 (Claude Code·git 전용)", "## Step 0.7")
        for needle in (
            "run_in_background: true",
            "`baseline-fingerprint`",
            "${DEV_DIR}/baseline.done",
            "${DEV_DIR}/baseline-{타입}-{test|build}.log",
            "`{타입} {test|build} rc={N}`",
            "`fingerprint-end={값}`",
            "실행 완료 표식이지 성공이 아니다",
            "동기 실행",
            "판정 1(기준 GREEN 실패)",
        ):
            self.assertIn(needle, pre)
        self.assertIn("기준선 사전 실행", section(impl, "## Step 0.5", "### 레이어별 하네스 게이트"))
        refs = TDD_PHASES.parent / "references"
        self.assertIn("run_in_background", (refs / "harness-adaptation.md").read_text(encoding="utf-8"))
        self.assertIn("baseline-fingerprint:", (refs / "pipeline-state.md").read_text(encoding="utf-8"))

    def test_baseline_acceptance_probe(self):
        bash = shutil.which("bash") or "bash"
        start = "1111111:aaaaaaaaaaaa"
        good = ["java-spring test rc=0", "java-spring build rc=0",
                "node test rc=0", "node build rc=0",
                f"fingerprint-end={start}", "DONE"]
        cases = (
            ("complete", good, start, True, "accept"),
            ("failed baseline still accepted", [l.replace("node test rc=0", "node test rc=1") for l in good], start, True, "accept"),
            ("head moved, tree same", good, "2222222:aaaaaaaaaaaa", True, "accept"),
            ("no DONE", good[:-1], start, True, "sync"),
            ("missing type line", [l for l in good if l != "node build rc=0"], start, True, "sync"),
            ("end fingerprint differs", [l.replace(f"fingerprint-end={start}", "fingerprint-end=1111111:bbbbbbbbbbbb") for l in good], start, True, "sync"),
            ("current tree differs", good, "1111111:cccccccccccc", True, "sync"),
            ("log missing", good, start, False, "sync"),
        )
        for name, lines, current, logs, expected in cases:
            with self.subTest(name), tempfile.TemporaryDirectory(prefix="baseline probe ") as root:
                done = Path(root) / "baseline.done"
                done.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))  # LF 고정 — Windows 텍스트 모드 CRLF 방지
                if logs:
                    for t in ("java-spring", "node"):
                        for k in ("test", "build"):
                            (Path(root) / f"baseline-{t}-{k}.log").write_text("", encoding="utf-8")
                env = dict(os.environ, DONE_FILE=str(done), START=start, CURRENT=current,
                           DIR=root, TYPES="java-spring node")
                result = subprocess.run([bash, "-c", BASELINE_ACCEPT_PROBE], env=env,
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.stdout.strip(), expected, result.stderr)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v`
Expected: `test_baseline_prelaunch_contract` FAIL (`## 기준선 사전 실행 (진입 직후)` substring not found), `test_baseline_acceptance_probe` PASS (probe는 규칙 자체의 일관성 검사 — 문서 계약은 바로 위 테스트가 고정)

- [ ] **Step 3: phase-requirements.md에 절 추가** (`**최대 1회 반복.**` 다음 줄 뒤)

```
## 기준선 사전 실행 (진입 직후)

본문(핵심 모드의 ac.md 작성, 전체 모드의 PRD 사이클)보다 먼저 같은 디렉토리 `phase-implement.md` Step 0.5의 "기준선 사전 실행 (Claude Code·git 전용)" 절차로 기준선 측정을 백그라운드에서 시작한다. 판정은 RGR 진입 시 Step 0.5가 한다. **Claude Code·git에서만** 시작한다 — Codex와 svn은 시작하지 않고 Step 0.5가 동기 실행한다. 재진입 시 이미 진행 중이거나 완료된 실행이 있으면 다시 시작하지 않는다.
```

- [ ] **Step 4: phase-implement.md 수정**

(a) Step 0.5 서두 문장 끝 `…을 따른다):` 의 `):` 앞에 문장 추가 → `…을 따른다. phase-requirements가 시작한 **기준선 사전 실행**(아래 절)의 결과가 수용 조건을 충족하면 다시 실행하지 않고 그 결과로 판정한다 — 아래 판정 1~5는 측정값의 출처와 무관하게 같다):`

(b) `### 레이어별 하네스 게이트` 절의 마지막 문단(`이 게이트는 모노레포 복합 명령…`) 뒤, `## Step 0.7` 앞에 추가

```
### 기준선 사전 실행 (Claude Code·git 전용)

phase-requirements 진입 직후 이 절차로 기준선 측정을 백그라운드에서 미리 시작한다 — PRD·설계 단계와 겹쳐 RGR 진입 대기에서 빼려는 것이다. 여기서는 판정하지 않는다 (판정 1~5는 Step 0.5가 RGR 진입 시점에 수행한다).

**적용 조건** (하나라도 아니면 시작하지 않고 Step 0.5가 동기 실행한다): 하네스가 Claude Code(Bash `run_in_background` 사용 가능)다 / VCS가 git이다 / 아래 1의 지문 계산이 성공한다. Codex·svn·`--phase implement`·`--phase design` 단독 진입은 사전 실행이 없다.

1. gx-verify Step 5-A의 Claude Code 지문 규약(임시 인덱스·`.dev` 제외·`{HEAD 단축}:{트리해시 앞12자}`)으로 지문을 계산한다. 결과가 `^[0-9a-f]+:[0-9a-f]{12}$` 형식이 아니면 시작하지 않는다. 형식이 맞으면 state.md 최상위 `baseline-fingerprint`에 기록한다.
2. Bash `run_in_background: true` 호출 한 번으로 Step 0.5 본문과 같은 명령 집합(감지된 타입별 config `test` → `build`, config 등록 순서)을 순차 실행한다.
3. 각 명령의 출력은 `${DEV_DIR}/baseline-{타입}-{test|build}.log`에 리다이렉트로 캡처하고, 명령이 끝날 때마다 `{타입} {test|build} rc={N}` 줄을 `${DEV_DIR}/baseline.done`에 추가한다.
4. 모든 명령이 끝나면 1과 같은 규약으로 지문을 다시 계산해 `fingerprint-end={값}` 줄을 쓰고, 마지막 줄에 `DONE`을 쓴다. `DONE`은 실행 완료 표식이지 성공이 아니다.
5. 시작부터 Step 0.5까지 오케스트레이터는 프로젝트 코드 파일을 바꾸지 않는다 (requirements·design은 `.dev/` 산출물만 쓴다). 실행 중에는 다른 테스트·빌드 명령을 시작하지 않는다.

requirements 재진입 시 `baseline-fingerprint`가 이미 있고 사전 실행이 진행 중이거나 `baseline.done`이 있으면 다시 시작하지 않는다.

**결과 수용** (Step 0.5 진입 시): 아래를 **모두** 만족하면 사전 실행 결과로 판정 1~5를 수행한다 — `baseline.done`의 마지막 줄이 `DONE` / 감지된 모든 타입의 test·build 줄이 각 1개 / `baseline-fingerprint`·`fingerprint-end`·지금 다시 계산한 지문의 트리 성분이 모두 같음 (HEAD 성분은 비교하지 않는다) / 각 로그 파일 존재. rc≠0은 판정 1(기준 GREEN 실패), 실행 0건은 판정 4(하네스 부재 감지), 경고 추출 불가는 판정 3(미측정)으로 동기 실행과 똑같이 처리한다.

| 상태 | 처리 |
|---|---|
| 수용 조건 충족 | 사전 실행 로그로 판정 |
| 같은 세션에서 아직 실행 중 | 완료 알림 또는 `DONE` 줄을 기다린다 (그동안 다른 테스트·빌드 금지) |
| `baseline.done`·`DONE` 없음, 실행 중인 작업도 없음 (세션 재개 등) | 동기 실행 |
| 지문 불일치·타입 줄 누락·로그 부재 | 결과를 버리고 동기 실행 |
| `baseline-fingerprint` 없음 | 동기 실행 |

동기 실행으로 전환하면 사유를 execution-log에 남긴다 (`gate: baseline`, 예: `"사전 실행 지문 불일치 — 동기 실행"`).
```

- [ ] **Step 5: references 수정**

harness-adaptation.md 표의 `Skill(...)` 행 다음에 추가:

```
| `Bash(run_in_background: true)` — 기준선 사전 실행 (phase-requirements, phase-implement Step 0.5) | 미지원 — 시작하지 않는다. Step 0.5가 동기 실행한다 |
```

pipeline-state.md:
- 스키마 예시 `warnings-baseline: 12` 다음 줄에 `baseline-fingerprint: "7c9e814:3ca970cc12ab"`
- `**state.md 필드**` 문단의 `` `fix-round`를 중첩한다 `` 뒤에 ` (`test-file`은 경로 하나 또는 경로 목록)` 삽입
- 갱신 규칙 `- **기준선 게이트 결과**: …` 항목 끝에 추가: ` requirements 진입 시 기준선 사전 실행을 시작했으면 최상위 \`baseline-fingerprint\`를 기록한다 (Claude Code·git 전용 — 절차·수용 조건은 phase-implement Step 0.5 "기준선 사전 실행" 절). 필드가 없으면 사전 실행을 하지 않은 것이다.`

- [ ] **Step 6: 통과 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v`
Expected: 5 tests OK

---

### Task 4: verify 차단 처리와 동시 실행 금지

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md` (서두 이유 :11-14, Step -1 :36-53)
- Modify: `.claude/skills/gx-verify/SKILL.md` (Step 2 :112)
- Modify: `.claude/skills/gx-tdd/references/pipeline-state.md` (verify-status 전이)
- Test: `tests/test_codex_skill_pipeline.py`

**Interfaces:**
- Consumes: "verify 회귀 수리" (Task 2에서 implementer.md에 추가한 호출처 이름)

- [ ] **Step 1: 실패 테스트 추가**

```python
    def test_verify_block_repair_contract(self):
        text = self.read("phase-complete.md")
        step = section(text, "## Step -1: verify 게이트", "## Step 0: 인수 검증")
        for needle in (
            '"수정"',
            "verify 회귀 수리",
            "`verify-status: pending`",
            '`verify-fingerprint: ""`',
            "수리 모드",
            "red-writer 재호출",
            "수리 라운드 상한 2회",
            "다시 리뷰하지 않는다",
            "다른 테스트·빌드 명령을 시작하지 않고",
        ):
            self.assertIn(needle, step)
        self.assertNotIn('"RGR 사이클로 수정"', step)
        self.assertIn("이 verify가 유일하다", text[: text.index("## Step -2")])
        verify = (ROOT / ".claude/skills/gx-verify/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("다른 테스트·빌드 명령을 병행하지 않는다", section(verify, "### Step 2", "### Step 3"))
        state = (TDD_PHASES.parent / "references/pipeline-state.md").read_text(encoding="utf-8")
        self.assertIn("verify 회귀 수리", state)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests.test_verify_block_repair_contract -v`
Expected: FAIL (`'"수정"' not found`)

- [ ] **Step 3: phase-complete.md 수정**

(a) 서두 `이유:` 목록 마지막에 추가

```
- gx-tdd에서 기존 스위트 회귀를 전체 실행으로 확인하는 곳은 이 verify가 유일하다 (태스크는 그 태스크 테스트만, phase-review Step 0은 이번 파이프라인 테스트만 실행한다)
```

(b) Step -1의 `` `Skill("oh-my-gx:gx-verify")`를 호출한다. `` 줄 뒤에 추가

```
verify 실행 중에는 다른 테스트·빌드 명령을 시작하지 않고 테스트를 실행하는 서브에이전트도 디스패치하지 않는다 — 같은 빌드 데몬·DB·CPU를 나눠 쓰면 시간 제한 테스트가 오탐하고 테스트 프로세스가 메모리 부족으로 죽는다.
```

(c) `- **❌ verify 차단**:` 블록(1~3항)을 아래로 교체하고, 블록 뒤(`**Iron Law 위반 감지**` 앞)에 수리 절차를 추가

```
- **❌ verify 차단**:
  1. verify가 실패 테스트·빌드·신규 경고 항목을 보고함
  2. 사용자에게 표시 후 AskUserQuestion:
     - "수정" → 아래 **verify 회귀 수리**를 수행한다
     - "수동 수정" → 사용자 수정 후 phase-complete 재호출 (execution-log에 "수동 수정 재주입" 기록. 재호출 시 Step -1 verify부터 재실행)
     - "중단" → state.md에 `status: cancelled` 기록
  3. 자동 수정은 시도하지 않음 (사용자가 "수정"을 고른 경우에만 수리한다. coder 직접 호출 금지)

**verify 회귀 수리** ("수정" 선택 시):

1. state.md를 `verify-status: pending`·`verify-fingerprint: ""`로 두고 `current-step`을 `"verify 회귀 수리"`로 갱신한다 (이전 통과 기록이 남아 커밋 게이트가 열리는 것을 막는다).
2. 차단 사유를 분류해 처리한다:

   | 차단 사유 | 처리 | 새 RED |
   |---|---|---|
   | 기존 테스트 실패 (프로덕션 코드가 기대를 깨뜨림) | implementer **수리 모드** — 깨진 테스트 + 에러 전문 + 깨진 대상으로 조립한 focused 검증 명령. 프로덕션 코드로만 해결하고 수리 뒤 테스트 파일 무변경을 확인한다 | 불필요 (깨진 테스트가 RED) |
   | 테스트의 기대 자체가 틀림 (테스트 결함 의심) | red-writer 재호출 | — |
   | 빌드 실패 — 프로덕션 소스 | implementer 수리 모드 | 불필요 |
   | 빌드 실패 — 테스트 소스 컴파일 | red-writer 재호출 | — |
   | 신규 경고 — 동작 불변으로 정리 가능 | 정리 모드 (phase-implement 세션 IMPLEMENT 절차의 REFACTOR 규칙·수행 불가능한 정리 목록) | 불필요 |
   | 신규 경고 — 고치려면 동작이 바뀜 | 실패 항목을 새 AC로 정의해 phase-implement로 복귀 (RGR) | 필요 |

3. 처리 뒤 Step -1(verify)을 다시 실행한다.
4. **수리 라운드 상한 2회**: 같은 Step -1 진입에서 "수정"을 2회 수행한 뒤에도 차단되면 "수정" 선택지를 빼고 "수동 수정"·"중단"만 묻는다.
5. 수리 diff는 다시 리뷰하지 않는다. execution-log에 `{ phase: complete, gate: "verify 회귀 수리 R{n}", result: "{분류} — {대상} — {결과}" }`를 남긴다.
6. `--resume`이 `"verify 회귀 수리"`에서 재개되면 Step -1부터 재실행한다 (state는 1에서 이미 pending이다).
```

- [ ] **Step 4: gx-verify SKILL.md 수정** — Step 2의 `캐시된 결과 사용 금지. **반드시 새로 실행**.` 줄 뒤에 추가

```
검증 실행 중에는 다른 테스트·빌드 명령을 병행하지 않는다 (호출자 포함 — 같은 빌드 데몬·DB·CPU 경합은 시간 제한 테스트 오탐과 테스트 프로세스 메모리 부족을 부른다). 복수 타입도 config 등록 순서대로 하나씩 실행한다.
```

- [ ] **Step 5: pipeline-state.md 수정** — `- **verify-status 전이**:` 항목 끝에 추가

```
 phase-complete Step -1에서 "수정"(verify 회귀 수리)을 고른 때에도 즉시 `pending`·빈 지문으로 둔다.
```

- [ ] **Step 6: 통과 확인**

Run: `python -m unittest tests.test_codex_skill_pipeline.TestRunBudgetContractTests -v`
Expected: 6 tests OK

---

### Task 5: 유지보수 노트·사용자 문서·골든 시나리오

**Files:**
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md`
- Modify: `README.md` (:269-271)
- Modify: `docs/tdd-guide.md` (게이트 흐름도, 6.6 verify_implement 3, 7.x 예시 GREEN, 7.5 마지막 문단)
- Modify: `docs/guide.md` (4.9 표)
- Modify: `tests/golden-scenarios.md` (S47~S49)

- [ ] **Step 1: maintenance-notes.md** — `- **"수동 수정 재주입" 기록 문구**` 항목 바로 앞에 4항목 추가

```
- **테스트 실행 범위 규칙**(태스크 focused = 그 태스크 `test-file`만·범위 확장 금지·전체는 완료 verify): phase-implement.md 세션 IMPLEMENT 절대 규칙 4 ↔ 격리 경로 프롬프트 규칙 4·`[focused 테스트 명령]` 플레이스홀더 ↔ "focused 테스트 명령 조립" ↔ `agents/implementer.md` 절대 규칙 4·Red Flags에 중복. 플레이스홀더 원문을 바꾸면 `tests/fixtures/behavior/b2/subs.json` 키도 바꾼다. `tests/test_codex_skill_pipeline.py`의 `TestRunBudgetContractTests`가 문구를 검사한다.
- **수리 모드 호출처**(RED report 없는 수리 — 깨진 테스트 + 에러 + focused 검증 명령, 테스트 파일 무변경 확인): phase-review Step 0(리뷰 Gate 수리)·phase-implement Step 3.5(경계 회귀 수리)·phase-complete Step -1(verify 회귀 수리) ↔ `agents/implementer.md` 수리 모드 문단. 호출처를 늘리거나 계약을 바꾸면 네 곳을 함께 갱신한다.
- **Step 0 테스트 집합**: phase-review Step 0-2가 정본(무결성 선확인·누적 focused·전체 폴백 4조건). Step 4.4의 4b·4c 재확인과 금지 사항 절이 참조한다.
- **기준선 사전 실행**: 절차·수용 조건 정본은 phase-implement Step 0.5 "기준선 사전 실행 (Claude Code·git 전용)" 절. phase-requirements "기준선 사전 실행 (진입 직후)" 절은 트리거·적용 조건 요약만, `references/pipeline-state.md`는 `baseline-fingerprint` 필드만, `references/harness-adaptation.md`는 Codex 미지원 행만 가진다. 수용 판정의 실행 근사는 `tests/test_codex_skill_pipeline.py`의 `BASELINE_ACCEPT_PROBE`.
```

- [ ] **Step 2: README.md**

- implement 항목의 `기준선 게이트(기존 테스트 GREEN 확인) 통과 후 바로 사이클에 들어갑니다.` → `기준선 게이트(기존 테스트 GREEN 확인) 통과 후 바로 사이클에 들어갑니다 — Claude Code에서는 기준선 측정을 requirements 시작과 함께 백그라운드로 미리 돌려 PRD·설계 시간과 겹칩니다. 태스크마다 그 태스크 테스트만 실행합니다.`
- review 항목 → `- **review**: 빌드 + 이번 파이프라인 테스트 누적 게이트 후 \`reviewer\`(AC 충족 → 코드 품질 통합 1석, spec verdict 선행) + \`security-auditor\` 병렬`
- complete 항목 → `- **complete**: \`verify\` 게이트(신선한 테스트 실행 증거 — 기존 스위트 전체 회귀는 여기서 1회)를 통과해야만 commit/PR`

- [ ] **Step 3: docs/tdd-guide.md**

- `implement ──── [게이트 3] 기준선 게이트 — 기존 테스트 GREEN + 경고 수 기록` → `implement ──── [게이트 3] 기준선 게이트 — 기존 테스트 GREEN + 경고 수 기록 (측정은 requirements 시작과 함께 미리 실행)`
- `review ─────── [게이트 4] Mechanical Gate (build + test)` → `review ─────── [게이트 4] Mechanical Gate (build + 이번 파이프라인 테스트 누적)`
- `complete ───── [게이트 5] TDD 이행 게이트 → verify 게이트 (gx-verify)` → `complete ───── [게이트 5] TDD 이행 게이트 → verify 게이트 (gx-verify — 기존 스위트 전체 회귀 1회)`
- `(전체 회귀는 사이클 경계에서 별도 확인)` → `(대상은 그 태스크 테스트만. 태스크 간 회귀는 review 게이트, 전체 회귀는 complete verify에서 확인)`
- `→ 대상 테스트 통과, 전체 회귀 0건` → `→ 대상 테스트 통과 (전체 회귀는 complete의 verify에서)`
- `verify에서 실패가 나오면 자동 수정하지 않는다. 실패 항목을 새 AC로 정의해 **RGR 사이클로 되돌아간다.** 버그 수정도 RED가 먼저다.` → `verify에서 실패가 나오면 자동 수정하지 않는다. 사용자가 "수정"을 고르면 깨진 기존 테스트를 RED로 삼아 수리 모드로 고치고(테스트 파일은 손대지 않는다) verify를 다시 돈다. 고치려면 동작이 바뀌는 항목만 새 AC로 정의해 **RGR 사이클로 되돌아간다.** 수리는 2회까지이고, 그 뒤에는 수동 수정이나 중단을 고른다.`

- [ ] **Step 4: docs/guide.md** — 4.9 표의 `| verify 게이트 | … |` 행 다음에 추가

```
| 테스트 실행 횟수 | 기존 스위트 전체 실행은 기준선(Claude Code에서는 requirements 시작과 함께 백그라운드 사전 실행)과 complete의 verify 1회뿐. 태스크는 그 태스크 테스트만, review 게이트는 이번 파이프라인 테스트 누적만 실행. 실행 중에는 다른 테스트를 겹쳐 돌리지 않는다 |
```

- [ ] **Step 5: tests/golden-scenarios.md** — S46 행 다음에 추가

```
| S47 | git 프로젝트, `projectTypes`에 java-spring·node 등록(각 `focusedTest` 포함), Claude Code | `/gx-tdd {기능}` 전체 모드로 끝까지 진행 | requirements 진입 직후 백그라운드 사전 실행 시작(`baseline-fingerprint` 기록, `baseline.done`에 타입별 rc 줄·`fingerprint-end`·`DONE`) → Step 0.5는 사전 실행 로그로 판정(미완료면 대기) → 태스크마다 그 태스크 테스트만 실행 → review Step 0은 빌드(`-x test`) + 누적 focused → 전체 스위트 실행은 사전 실행 1회 + verify 1회뿐. 사전 실행·verify 중 다른 테스트 명령 0건 | phase-requirements 사전 실행 절 → phase-implement Step 0.5 수용 조건 → phase-review Step 0-2 → phase-complete Step -1 |
| S48 | S47과 같고 사전 실행이 끝나기 전 사용자가 코드 파일 1개 수정 | 설계 승인 후 implement 진입 | 지문 불일치로 사전 실행 결과를 버리고 동기 실행, execution-log에 `gate: baseline` 전환 사유 기록. 수정된 코드 기준으로 warnings-baseline 기록 | phase-implement Step 0.5 결과 수용 표 |
| S49 | complete 단계에서 이번 변경이 기존 테스트 1건을 깨뜨린 상태 | verify 차단 후 "수정" 선택 | 선택 즉시 `verify-status: pending`·빈 지문·`current-step: "verify 회귀 수리"` → implementer 수리 모드(새 RED 없음, 테스트 파일 해시 불변) → verify 재실행 통과. 2회 수리 뒤에도 차단이면 "수정" 없이 수동 수정·중단만 제시 | phase-complete Step -1 verify 회귀 수리 |
```

- [ ] **Step 6: SKILL.md 확인** — `.claude/skills/gx-tdd/SKILL.md`에서 `전체 테스트|경계 회귀|Mechanical Gate` 검색. 사실과 달라지는 문구가 없으면 수정하지 않는다 (확인 결과를 실행 기록에 남긴다).

---

### Task 6: 릴리스 메타데이터

**Files:**
- Modify: `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`

- [ ] **Step 1: 버전 1.35.0** — 세 manifest의 `"version": "1.33.1"` → `"version": "1.35.0"` (PR #92가 1.34.0을 사용)

- [ ] **Step 2: CHANGELOG.md** — `# Changelog` 다음에 추가

```
## v1.35.0 (2026-10-14) — gx-tdd 테스트 실행 횟수 축소

### Changed

- gx-tdd가 기존 스위트 전체를 돌리는 곳을 기준선과 완료 verify 두 번으로 줄인다. 리뷰 전 게이트는 빌드(테스트 제외)와 이번 파이프라인 테스트 누적만 실행하고, 리뷰 정리 뒤 재확인도 같은 집합을 쓴다. 핵심 모드는 implement 직후의 경계 회귀를 건너뛴다(`--phase implement` 단독만 유지).
- 태스크 GREEN 확인은 그 태스크의 테스트 파일만 실행한다. 와일드카드·모듈 묶음·이웃 클래스로 범위를 넓히지 않고, 전체 스위트나 다른 테스트가 도는 동안 새 테스트·빌드를 시작하지 않는다.
- Claude Code·git에서는 기준선 측정을 requirements 진입과 함께 백그라운드로 미리 돌린다. 시작·종료·RGR 진입 시점의 코드 지문이 같고 모든 타입의 결과가 있을 때만 그 결과로 판정하며, 아니면 기존처럼 동기 실행한다. Codex·svn은 기존과 같다.
- verify가 차단되면 "수정"을 고를 수 있다. 깨진 기존 테스트를 RED로 삼아 수리 모드로 고치고 verify를 다시 돌리며, 수리는 2회까지다. 수정을 고르는 즉시 verify 통과 표식을 되돌린다.
```

- [ ] **Step 3: 버전 정합성 확인**

Run: `grep -n '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json && head -3 CHANGELOG.md`
Expected: 세 곳 모두 1.35.0, CHANGELOG 첫 섹션 v1.35.0

---

### Task 7: 전체 검증과 Codex 리뷰

- [ ] **Step 1:** `python scripts/sync-codex-resources.py --check` → exit 0
- [ ] **Step 2:** `python -m unittest discover -s tests -p "test_codex_*.py" -v` → 전부 OK
- [ ] **Step 3:** `bash scripts/test-behavior-tests.sh` → 전부 PASS
- [ ] **Step 4:** `bash scripts/lint-consistency.sh` (timeout 600000) → 36/36 통과
- [ ] **Step 5:** Codex 리뷰 — `codex exec -s read-only -C <워크트리> -o <scratchpad>/codex-impl-review.txt -` 에 "base main 대비 diff를 spec과 대조해 결함·누락·모순을 심각도와 파일:라인으로" 지시문을 stdin으로 전달 (`codex review --uncommitted`는 지시문과 함께 쓸 수 없다)
- [ ] **Step 6:** 지적을 기술적으로 검증해 반영하고 Step 1~4를 다시 실행
- [ ] **Step 7:** 결과를 사용자에게 보고하고 커밋·PR 진행 여부를 확인한다 (`oh-my-gx:gx-commit` → `oh-my-gx:gx-pull-request`)
