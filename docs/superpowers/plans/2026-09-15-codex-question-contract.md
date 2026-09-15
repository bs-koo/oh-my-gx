# gx-context·gx-dev·gx-tdd Codex 질문 계약 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 세 스킬의 질문 예시와 Codex 변환 규칙을 현재 공통 스키마 범위로 맞춰 중복 Other와 잘못된 질문 배열을 제거한다.

**Architecture:** Claude용 AskUserQuestion 표현은 유지하되 질문·선택지 개수는 양쪽 하네스가 수용하는 1~3개로 제한한다. Codex runtime은 `multiSelect` 제거, stable `id` 추가, 실제 도구 스키마 우선 규칙을 담당한다. 정적 테스트가 세 스킬의 명시적 Other option과 상충하는 개수 규칙을 차단한다.

**Tech Stack:** Markdown skill instructions, Python 3.10 `unittest`, Codex smoke contract

**Spec:** `docs/superpowers/specs/2026-09-15-core-skills-hardening-design.md` — D3

## Global Constraints

- 선행 조건: A `feat/context-requirement-ledger`와 B `fix/pipeline-bootstrap-contract`가 병합된 브랜치에서 시작한다.
- 작업 브랜치: `fix/codex-question-contract`.
- 질문은 한 호출에 1~3개, 질문당 option 2~3개다.
- option label이 `Other`, `Other로 입력`, `직접 입력`, `답변 입력`, `주제 입력`인 예시를 두지 않는다.
- Claude AskUserQuestion 예시에 Codex 전용 `id`를 억지로 넣지 않는다. Codex 변환 단계가 stable snake_case id를 추가한다.
- 기존 결정 기록 hook과 승인 게이트는 유지한다.
- 기능 브랜치에서는 manifest·marketplace·CHANGELOG 버전을 바꾸지 않는다.

---

### Task 1: Codex 변환 규칙을 실행 가능한 형태로 고정한다

**Files:**
- Create: `tests/test_codex_skill_questions.py`
- Modify: `.claude/skills/gx-dev/references/codex-runtime.md`

**Interfaces:**
- Consumes: Claude `AskUserQuestion.questions[]`
- Produces: Codex `request_user_input({questions:[{id,header,question,options}]})`

- [ ] **Step 1: Codex adapter 계약 테스트를 작성한다**

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".claude/skills/gx-dev/references/codex-runtime.md"
TARGETS = (
    ROOT / ".claude/skills/gx-context/SKILL.md",
    ROOT / ".claude/skills/gx-dev/SKILL.md",
    ROOT / ".claude/skills/gx-tdd/SKILL.md",
)


class CodexQuestionContractTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_runtime_defines_codex_schema_translation(self):
        text = self.read(RUNTIME)
        for phrase in (
            "질문 1~3개",
            "선택지 2~3개",
            "stable snake_case `id`",
            "`multiSelect`를 제거",
            "실제 도구 스키마가 이 문서보다 우선",
            "Other를 직접 option으로 추가하지 않는다",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 현재 runtime의 변환 세부 부족으로 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_questions.CodexQuestionContractTests.test_runtime_defines_codex_schema_translation -v`

Expected: 질문·선택지 상한과 multiSelect 제거 문구 누락으로 FAIL.

- [ ] **Step 3: codex-runtime 질문 규칙을 교체한다**

기존 질문 규칙 항목을 다음 블록으로 바꾼다.

```markdown
5. 질문은 제공된 async 도구 또는 해당 모드에서 허용된 동기 도구를 사용한다. Claude `AskUserQuestion` 예시를 Codex `request_user_input`으로 옮길 때 한 호출은 질문 1~3개, 질문별 선택지 2~3개로 제한한다. 각 질문에 의미가 유지되는 stable snake_case `id`를 추가하고 Claude 전용 `multiSelect`를 제거한다. 추천 option은 첫 번째에 두고 label 끝에 `(Recommended)`를 붙인다. UI가 제공하는 Other를 직접 option으로 추가하지 않는다. 실제 도구 스키마가 이 문서보다 우선하며 허용 필드·개수가 다르면 실제 스키마에 맞춘다. 응답 전에는 독립 작업만 수행하고 자연어 fallback도 실제 답변을 기다린다. 확정된 자연어/async 결정은 아래 capture payload로 기록한다.
```

- [ ] **Step 4: 테스트와 sync 검사를 통과시킨다**

Run: `python -m unittest tests.test_codex_skill_questions -v && python scripts/sync-codex-resources.py --check`

Expected: 1 test OK, sync check 성공.

- [ ] **Step 5: 커밋한다**

```bash
git add tests/test_codex_skill_questions.py .claude/skills/gx-dev/references/codex-runtime.md
git commit -m "fix: Codex 질문 스키마 변환 규칙을 고정한다"
```

---

### Task 2: 세 스킬의 질문 개수와 Other 규칙을 통일한다

**Files:**
- Modify: `tests/test_codex_skill_questions.py`
- Modify: `.claude/skills/gx-context/SKILL.md`
- Modify: `.claude/skills/gx-dev/SKILL.md`
- Modify: `.claude/skills/gx-tdd/SKILL.md`

**Interfaces:**
- Consumes: Task 1 Codex adapter
- Produces: 하네스 공통 질문 범위 1~3, option 범위 2~3, 명시적 Other label 0건

- [ ] **Step 1: 금지 label과 상충 문구 테스트를 추가한다**

```python
    def test_skill_rules_use_common_question_limits(self):
        for path in TARGETS:
            text = self.read(path)
            self.assertIn("질문은 한 호출에 1~3개", text, path)
            self.assertIn("선택지는 2~3개", text, path)
            self.assertNotRegex(text, r"질문[^\n]*(?:1~5|최대 5)")
            self.assertNotRegex(text, r"선택지[^\n]*(?:2~4|최대 4)")

    def test_static_options_do_not_duplicate_other(self):
        forbidden = re.compile(
            r'label:\s*["\'](?:Other|Other로 입력|직접 입력|답변 입력|주제 입력)["\']'
        )
        for path in TARGETS:
            text = self.read(path)
            self.assertIsNone(forbidden.search(text), path)

    def test_every_skill_points_codex_to_runtime(self):
        for path in TARGETS:
            text = self.read(path)
            self.assertIn("codex-runtime.md", text, path)
            self.assertIn("실제 도구 스키마", text, path)
```

- [ ] **Step 2: gx-context의 명시적 Other와 gx-dev 상한 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_questions.CodexQuestionContractTests.test_skill_rules_use_common_question_limits tests.test_codex_skill_questions.CodexQuestionContractTests.test_static_options_do_not_duplicate_other tests.test_codex_skill_questions.CodexQuestionContractTests.test_every_skill_points_codex_to_runtime -v`

Expected: gx-context의 `label: "Other로 입력"`, gx-dev의 1~5·2~4 규칙, 일부 runtime 포인터 누락으로 FAIL.

- [ ] **Step 3: 각 스킬 하네스 적응 절에 공통 경계를 넣는다**

세 파일의 하네스 적응 절에 다음 문장을 넣는다.

```markdown
질문은 한 호출에 1~3개, 질문별 선택지는 2~3개로 제한한다. UI가 제공하는 Other를 option으로 직접 추가하지 않는다. Codex에서는 `gx-dev/references/codex-runtime.md`와 실제 도구 스키마를 우선한다.
```

gx-tdd에서 링크는 파일 위치 기준 `../gx-dev/references/codex-runtime.md`, gx-context도 같은 상대경로를 사용한다. gx-dev에서는 `references/codex-runtime.md`를 사용한다.

- [ ] **Step 4: gx-dev 질문 작성 규칙을 공통 범위로 교체한다**

질문 작성 규칙의 개수·자유입력 설명을 다음으로 바꾼다.

```markdown
- 질문은 한 호출에 1~3개이며, 질문별 선택지는 2~3개다.
- 선택지는 가능한 실제 답변 후보를 쓴다. 추천 후보는 첫 번째에 두고 `(Recommended)`를 붙인다.
- 개방형 질문은 실제 후보 2개 또는 후보 1개와 `모르겠음`을 제시한다. UI가 제공하는 Other로 사용자가 자연어를 입력하므로 `Other로 입력` option을 만들지 않는다.
```

기존의 `1~5`, `2~4`, `후보를 제시할 수 없는 개방형 질문이면 { label: "Other로 입력" ... }` 문장은 삭제한다.

- [ ] **Step 5: gx-context의 명시적 Other option을 제거한다**

다음 네 종류를 모두 수정한다.

- 권장 답변 / `Other로 입력` / `모르겠음` 배열은 권장 답변 / `모르겠음` 두 option으로 바꾼다.
- `수정 필요`는 실제 선택이므로 유지하되 description만 `선택 후 UI의 Other에 수정 내용을 입력합니다`로 쓴다.
- 산문 `권장 답변 + Other + 모르겠음`은 `권장 답변 + 모르겠음, 자유입력은 UI Other`로 바꾼다.
- 파고들기 규칙의 `예시 후보 + Other`는 `예시 후보, 자유입력은 UI Other`로 바꾼다.

변경 후 다음 명령의 출력이 없어야 한다.

Run: `rg -n 'label: "(Other|Other로 입력|직접 입력|답변 입력|주제 입력)"' .claude/skills/gx-context/SKILL.md`

Expected: 출력 없음.

- [ ] **Step 6: gx-tdd 규칙을 같은 표현으로 정리한다**

기존 `questions 배열 필수` 절 앞에 다음 두 불릿을 둔다.

```markdown
- 질문은 한 호출에 1~3개이며, 질문별 선택지는 2~3개다.
- 개방형 질문은 실제 후보를 제시하고 자유입력은 UI가 제공하는 Other를 사용한다. 명시적인 Other option을 만들지 않는다.
```

기존 `Other는 UI가 자동 제공` 문장은 중복되지 않게 위 두 번째 불릿에 합친다.

- [ ] **Step 7: 테스트와 기존 린트를 실행한다**

Run: `python -m unittest tests.test_codex_skill_questions -v && bash scripts/lint-consistency.sh`

Expected: 4 tests OK, lint 36/36 통과.

- [ ] **Step 8: 커밋한다**

```bash
git add tests/test_codex_skill_questions.py .claude/skills/gx-context/SKILL.md .claude/skills/gx-dev/SKILL.md .claude/skills/gx-tdd/SKILL.md
git commit -m "fix: 세 스킬의 질문 선택지 계약을 통일한다"
```

---

### Task 3: Codex 실제 질문 smoke 계약을 보강한다

**Files:**
- Modify: `tests/test_codex_skill_questions.py`
- Modify: `tests/codex-smoke.md`
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md`

**Interfaces:**
- Consumes: Task 1의 Codex 변환, Task 2의 질문 범위
- Produces: smoke Q2 증거 계약

- [ ] **Step 1: smoke Q2 존재 테스트를 추가한다**

```python
    def test_smoke_contract_checks_question_shape(self):
        text = self.read(ROOT / "tests/codex-smoke.md")
        self.assertIn("| Q2 |", text)
        self.assertIn("stable snake_case id", text)
        self.assertIn("명시적 Other option 0개", text)
        self.assertIn("질문 3개 이하", text)
        self.assertIn("선택지 3개 이하", text)
```

- [ ] **Step 2: Q2 부재로 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_questions.CodexQuestionContractTests.test_smoke_contract_checks_question_shape -v`

Expected: `| Q2 |` 누락으로 FAIL.

- [ ] **Step 3: codex-smoke 역할·질문 표에 Q2를 추가한다**

```markdown
| Q2 | gx-context 문서 기반 개방형 질문과 gx-dev 모드·프로파일 질문 | 각 질문에 stable snake_case id; 질문 3개 이하; 질문별 선택지 3개 이하; 명시적 Other option 0개; UI Other 자연어 답변이 decision capture에 같은 id로 기록 | 미실행 |
```

- [ ] **Step 4: maintenance notes에 정본·소비자를 기록한다**

```markdown
- **질문 공통 경계**: 호출당 질문 1~3개, 질문당 option 2~3개, 명시적 Other option 금지. Claude 예시는 각 SKILL.md, Codex 변환 정본은 `gx-dev/references/codex-runtime.md`. `tests/test_codex_skill_questions.py`가 gx-context·gx-dev·gx-tdd를 함께 검사한다.
```

- [ ] **Step 5: 전체 Codex 계약 테스트를 실행한다**

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v && python scripts/sync-codex-resources.py --check && bash scripts/lint-consistency.sh`

Expected: 모든 unittest OK, sync check 성공, lint 36/36 통과.

- [ ] **Step 6: 커밋한다**

```bash
git add tests/test_codex_skill_questions.py tests/codex-smoke.md .claude/skills/gx-tdd/references/maintenance-notes.md
git commit -m "test: Codex 질문 형태 smoke 계약을 추가한다"
```

---

### Task 4: 질문 계약 브랜치의 수용 증거를 기록한다

**Files:**
- Create: `docs/reports/2026-09-15-codex-question-contract-validation.md`

**Interfaces:**
- Consumes: Task 1~3 결과
- Produces: D 모듈화 분기가 이동해야 할 확정 문구

- [ ] **Step 1: 금지 패턴과 자동 검사를 실행한다**

Run: `rg -n 'label: "(Other|Other로 입력|직접 입력|답변 입력|주제 입력)"|질문.*1~5|선택지.*2~4' .claude/skills/gx-context .claude/skills/gx-dev .claude/skills/gx-tdd`

Expected: 출력 없음.

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v && bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh && bash scripts/test-behavior-tests.sh`

Expected: 모든 unittest OK, lint 36/36, hook tests와 behavior mock 성공.

- [ ] **Step 2: 분기 검증 보고서를 작성한다**

```markdown
# Codex 질문 계약 검증

- 분기: `fix/codex-question-contract`
- 결과: PASS

| 검사 | 결과 |
|---|---|
| `test_codex_skill_questions.py` | PASS |
| smoke Q2 계약 | PASS |
| lint 36/36 | PASS |
| hook-tests | PASS |
| behavior mock | PASS |
```

- [ ] **Step 3: 증거를 커밋한다**

```bash
git add docs/reports/2026-09-15-codex-question-contract-validation.md
git commit -m "docs: Codex 질문 계약 검증 결과를 기록한다"
```
