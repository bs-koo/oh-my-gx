# gx-context·gx-dev·gx-tdd 지시문 모듈화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기능 계약을 바꾸지 않고 세 스킬의 긴 SKILL.md를 조건부 참조 파일로 나눠 수정 범위와 instruction load를 줄인다.

**Architecture:** gx-context는 선택한 mode 본문만 Read하고, gx-dev·gx-tdd는 의도 라우팅·상태 계약·질문 계약을 각각 전용 reference에서 읽는다. 각 SKILL.md는 실행 순서와 안전 게이트를 유지한다. 자동 테스트는 파일 존재, Read 순서, 헤딩의 단일 소유권, 본문 행 상한을 검사한다.

**Tech Stack:** Markdown skill instructions, Python 3.10 `unittest`, Bash consistency lint

**Spec:** `docs/superpowers/specs/2026-09-15-core-skills-hardening-design.md` — D4

## Global Constraints

- 선행 조건: A·B·C가 병합되고 context/pipeline/question 계약 테스트가 모두 통과한 상태.
- 작업 브랜치: `refactor/skill-instruction-layout`.
- 새 동작, 새 질문, 새 phase, 새 상태 필드를 추가하지 않는다.
- 파일 이동 전후의 문장 내용은 상대경로 포인터와 연결 문장을 제외하고 유지한다.
- gx-context SKILL.md 320행 이하, gx-dev 520행 이하, gx-tdd 520행 이하를 목표로 한다.
- 이동한 파일은 반드시 상위 SKILL.md에서 실행 전에 `Read("상대경로")`로 연결한다.
- 기존 lint 36개 계약을 참조 파일까지 따라가도록 수정하되 검사 의미를 약화하지 않는다.
- 기능 브랜치에서는 manifest·marketplace·CHANGELOG 버전을 바꾸지 않는다.

---

### Task 1: 모듈 배치와 필수 포인터를 테스트로 고정한다

**Files:**
- Create: `tests/test_codex_skill_layout.py`

**Interfaces:**
- Consumes: D1~D3에서 확정한 스킬 본문
- Produces: 파일 배치·행 상한·필수 Read 포인터 테스트

- [ ] **Step 1: 레이아웃 계약 테스트를 작성한다**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillInstructionLayoutTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_context_modes_are_conditionally_loaded(self):
        main = self.read(".claude/skills/gx-context/SKILL.md")
        expected = {
            "신규": "modes/create.md",
            "문서 기반": "modes/from-document.md",
            "갱신": "modes/update.md",
            "동기화": "modes/sync.md",
        }
        for mode, relative in expected.items():
            self.assertTrue((ROOT / ".claude/skills/gx-context" / relative).is_file())
            self.assertIn(f'`{mode}` → `Read("{relative}")`', main)
        self.assertLessEqual(len(main.splitlines()), 320)

    def test_dev_references_are_loaded_before_phase_loop(self):
        main = self.read(".claude/skills/gx-dev/SKILL.md")
        refs = (
            "references/intent-routing.md",
            "references/pipeline-state.md",
            "references/interaction-contract.md",
        )
        loop = main.index("### Phase 실행 루프")
        for relative in refs:
            self.assertTrue((ROOT / ".claude/skills/gx-dev" / relative).is_file())
            self.assertLess(main.index(f'Read("{relative}")'), loop)
        self.assertLessEqual(len(main.splitlines()), 520)

    def test_tdd_references_are_loaded_before_phase_loop(self):
        main = self.read(".claude/skills/gx-tdd/SKILL.md")
        refs = (
            "references/intent-routing.md",
            "references/pipeline-state.md",
            "references/interaction-contract.md",
        )
        loop = main.index("### Phase 실행 루프")
        for relative in refs:
            self.assertTrue((ROOT / ".claude/skills/gx-tdd" / relative).is_file())
            self.assertLess(main.index(f'Read("{relative}")'), loop)
        self.assertLessEqual(len(main.splitlines()), 520)

    def test_moved_headings_have_one_owner_per_skill(self):
        bundles = {}
        for name in ("gx-dev", "gx-tdd"):
            directory = ROOT / ".claude/skills" / name
            bundles[name] = [directory / "SKILL.md"] + [
                directory / "references/intent-routing.md",
                directory / "references/pipeline-state.md",
                directory / "references/interaction-contract.md",
            ]
        for name, paths in bundles.items():
            text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
            for heading in (
                "## 인자",
                "## 코드 맵",
                "## Trust Ledger (신뢰 원장)",
                "### 에이전트 질문 → AskUserQuestion 변환 규칙",
                "## 플래그 충돌 검증",
                "## 에러 처리",
            ):
                self.assertEqual(text.count(heading), 1, (name, heading))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 파일 부재와 행 상한으로 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_layout -v`

Expected: 새 reference/mode 파일 부재 또는 line limit으로 네 테스트가 FAIL.

- [ ] **Step 3: 테스트만 커밋한다**

```bash
git add tests/test_codex_skill_layout.py
git commit -m "test: 핵심 스킬 지시문 배치 계약을 추가한다"
```

---

### Task 2: gx-context mode 본문을 조건부 파일로 분리한다

**Files:**
- Create: `.claude/skills/gx-context/modes/create.md`
- Create: `.claude/skills/gx-context/modes/from-document.md`
- Create: `.claude/skills/gx-context/modes/update.md`
- Create: `.claude/skills/gx-context/modes/sync.md`
- Modify: `.claude/skills/gx-context/SKILL.md`
- Modify: `tests/test_codex_skill_layout.py`

**Interfaces:**
- Consumes: SKILL.md 모드 자동 판단 결과 `신규|문서 기반|갱신|동기화`
- Produces: mode 파일 하나를 Read한 뒤 해당 절차 실행

- [ ] **Step 1: 네 mode 파일로 정확한 절 범위를 이동한다**

| 대상 파일 | 원본 시작 | 원본 끝 |
|---|---|---|
| `modes/create.md` | `## 모드 B: 신규 (Q&A 기반)` | `## 모드 C` 직전 |
| `modes/from-document.md` | `## 모드 C: 문서 기반 (--from)` | `## 모드 D` 직전 |
| `modes/update.md` | `## 모드 D: 갱신` | `## 모드 E` 직전 |
| `modes/sync.md` | `## 모드 E: 동기화 (--sync)` | `## 주제 문서 헤더 템플릿` 직전 |

각 파일 첫머리에 다음 전제 블록을 넣는다.

```markdown
> 호출 전제: gx-context/SKILL.md가 인자 파싱·모드 선택·하네스 적응을 완료했다. 이 파일의 상대경로는 gx-context/SKILL.md 위치를 기준으로 해석한다.
```

`## 주제 문서 헤더 템플릿`은 `modes/update.md` 끝으로 이동한다. 신규 mode가 같은 템플릿을 필요로 하지 않으므로 update가 단독 소유한다.

- [ ] **Step 2: SKILL.md에 조건부 디스패치 표를 넣는다**

모드 자동 판단 표 다음에 다음 절을 추가한다.

```markdown
## 모드 실행

모드 판정 직후 아래 파일 하나만 Read하고, 읽은 파일의 절차가 완료되면 종료한다.

- `신규` → `Read("modes/create.md")`
- `문서 기반` → `Read("modes/from-document.md")`
- `갱신` → `Read("modes/update.md")`
- `동기화` → `Read("modes/sync.md")`

`스캔`은 아래 모드 A를 현재 SKILL.md에서 계속 실행한다. 문서 기반 mode가 내부에서 신규·갱신 절차를 호출할 때는 필요한 mode 파일을 추가로 Read한다.
```

- [ ] **Step 3: mode 간 내부 참조를 파일 Read로 바꾼다**

`from-document.md` C-4의 위임을 다음처럼 명시한다.

```markdown
- context가 없으면 `Read("modes/create.md")`의 B-5~B-11을 실행한다.
- context가 있으면 `Read("modes/update.md")`의 변경 제안·반영 절차를 실행한다.
```

기존 B-2 참조는 `Read("modes/create.md")`의 B-2로 표기한다.

- [ ] **Step 4: context 레이아웃 테스트에 헤딩 단일 소유권과 bundle reader를 추가한다**

```python
    def test_context_mode_headings_have_one_owner(self):
        paths = list((ROOT / ".claude/skills/gx-context").rglob("*.md"))
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for heading in (
            "## 모드 B: 신규 (Q&A 기반)",
            "## 모드 C: 문서 기반 (--from)",
            "## 모드 D: 갱신",
            "## 모드 E: 동기화 (--sync)",
            "### C-4-1. 요구사항 원장 반영",
        ):
            self.assertEqual(text.count(heading), 1, heading)
```

`tests/test_codex_skill_context.py`의 단일 파일 reader를 다음 bundle reader로 바꾸고, context 본문을 검사하는 테스트는 이 반환값을 사용한다.

```python
    def context_bundle(self) -> str:
        directory = ROOT / ".claude/skills/gx-context"
        ordered = [
            directory / "SKILL.md",
            directory / "modes/create.md",
            directory / "modes/from-document.md",
            directory / "modes/update.md",
            directory / "modes/sync.md",
        ]
        return "\n".join(path.read_text(encoding="utf-8") for path in ordered)
```

- [ ] **Step 5: context 계약과 레이아웃 테스트를 실행한다**

Run: `python -m unittest tests.test_codex_skill_context tests.test_codex_skill_layout -v`

Expected: context·layout 테스트 모두 OK. bundle 순서는 `SKILL.md`, `create.md`, `from-document.md`, `update.md`, `sync.md`로 고정된다.

- [ ] **Step 6: 커밋한다**

```bash
git add .claude/skills/gx-context/SKILL.md .claude/skills/gx-context/modes tests/test_codex_skill_context.py tests/test_codex_skill_layout.py
git commit -m "refactor: gx-context 모드를 조건부 파일로 분리한다"
```

---

### Task 3: gx-dev의 라우팅·상태·질문 계약을 분리한다

**Files:**
- Create: `.claude/skills/gx-dev/references/intent-routing.md`
- Create: `.claude/skills/gx-dev/references/pipeline-state.md`
- Create: `.claude/skills/gx-dev/references/interaction-contract.md`
- Modify: `.claude/skills/gx-dev/SKILL.md`
- Modify: `scripts/lint-consistency.sh`
- Modify: `tests/test_codex_skill_pipeline.py`
- Modify: `tests/test_codex_skill_questions.py`

**Interfaces:**
- Consumes: ARGS, flags, phase 결과, agent 결과
- Produces: intent 파일의 MODE/PHASES, state 파일의 PROJECT_ROOT/DEV_DIR/state 계약, interaction 파일의 질문·에러 처리

- [ ] **Step 1: 다음 헤딩 범위를 파일로 이동한다**

`references/intent-routing.md`:

- `## 인자`부터 `## Agent 팀` 직전까지
- `## 플래그 충돌 검증`부터 `## 에러 처리` 직전까지

`references/pipeline-state.md`:

- `## 코드 맵`부터 `### 에이전트 질문 → AskUserQuestion 변환 규칙` 직전까지

`references/interaction-contract.md`:

- `### 에이전트 질문 → AskUserQuestion 변환 규칙`부터 파일 끝의 `## 에러 처리`까지

각 파일 첫머리에 다음 전제를 넣는다.

```markdown
> gx-dev/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태·질문·phase 결정을 추정하지 않는다.
```

- [ ] **Step 2: SKILL.md의 스킬 참조 경로 절 뒤에 필수 Read 순서를 넣는다**

```markdown
## 필수 실행 계약 로드

Phase 목록을 계산하기 전에 다음 파일을 순서대로 Read한다.

1. `Read("references/intent-routing.md")`
2. `Read("references/pipeline-state.md")`
3. `Read("references/interaction-contract.md")`

세 파일을 읽은 뒤 의도 파싱 결과로 아래 Phase 실행 루프를 수행한다.
```

- [ ] **Step 3: 계약 테스트가 bundle을 읽도록 바꾼다**

`tests/test_codex_skill_pipeline.py`와 `tests/test_codex_skill_questions.py`에 다음 helper를 넣고 gx-dev 검사는 이를 사용한다.

```python
def skill_bundle(directory: Path) -> str:
    ordered = [
        directory / "SKILL.md",
        directory / "references/intent-routing.md",
        directory / "references/pipeline-state.md",
        directory / "references/interaction-contract.md",
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in ordered)
```

runtime, maintenance notes, harness adaptation, codex-roles는 bundle에 포함하지 않는다. 테스트가 그 파일 자체의 문구를 검사할 때만 개별 파일을 읽는다.

- [ ] **Step 4: lint의 gx-dev SKILL 직접 검색을 bundle 검색으로 바꾼다**

`scripts/lint-consistency.sh`의 변수 초기화 구간에 다음 helper를 추가한다.

```bash
skill_bundle_text() {
  local skill_dir="$1"
  cat "$skill_dir/SKILL.md"
  [ ! -d "$skill_dir/references" ] || find "$skill_dir/references" -maxdepth 1 -type f -name '*.md' ! -path '*/codex-roles/*' -print0 | sort -z | xargs -0 -r cat
}
DEV_SKILL_TEXT=$(skill_bundle_text .claude/skills/gx-dev)
TDD_SKILL_TEXT=$(skill_bundle_text .claude/skills/gx-tdd)
```

Run: `rg -n '\.claude/skills/gx-dev/SKILL\.md' scripts/lint-consistency.sh`

각 결과에서 이동한 문구를 검사하는 `grep ... .claude/skills/gx-dev/SKILL.md`만 `printf '%s' "$DEV_SKILL_TEXT" | grep ...`로 바꾼다. frontmatter, SKILL 진입점, main에 남긴 Phase 실행 루프를 검사하는 항목은 직접 검색을 유지한다.

- [ ] **Step 5: dev 관련 검증을 실행한다**

Run: `python -m unittest tests.test_codex_skill_pipeline tests.test_codex_skill_questions tests.test_codex_skill_layout -v && bash scripts/lint-consistency.sh`

Expected: 모든 테스트 OK, lint 36/36 통과, gx-dev SKILL.md 520행 이하.

- [ ] **Step 6: 커밋한다**

```bash
git add .claude/skills/gx-dev/SKILL.md .claude/skills/gx-dev/references/intent-routing.md .claude/skills/gx-dev/references/pipeline-state.md .claude/skills/gx-dev/references/interaction-contract.md scripts/lint-consistency.sh tests/test_codex_skill_pipeline.py tests/test_codex_skill_questions.py
git commit -m "refactor: gx-dev 실행 계약을 참조 파일로 분리한다"
```

---

### Task 4: gx-tdd를 같은 파일 경계로 분리한다

**Files:**
- Create: `.claude/skills/gx-tdd/references/intent-routing.md`
- Create: `.claude/skills/gx-tdd/references/pipeline-state.md`
- Create: `.claude/skills/gx-tdd/references/interaction-contract.md`
- Modify: `.claude/skills/gx-tdd/SKILL.md`
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md`
- Modify: `scripts/lint-consistency.sh`
- Modify: `tests/test_codex_skill_pipeline.py`
- Modify: `tests/test_codex_skill_questions.py`

**Interfaces:**
- Consumes: gx-tdd ARGS, flags, RGR 상태, agent 결과
- Produces: gx-dev와 같은 파일 경계, TDD 전용 내용은 gx-tdd reference에만 유지

- [ ] **Step 1: gx-tdd에서 같은 책임의 헤딩 범위를 이동한다**

`references/intent-routing.md`:

- `## 인자`부터 `## Agent 팀` 직전까지
- `## 플래그 충돌 검증`부터 `## 에러 처리` 직전까지

`references/pipeline-state.md`:

- `## 코드 맵`부터 `### 에이전트 질문 → AskUserQuestion 변환 규칙` 직전까지

`references/interaction-contract.md`:

- `### 에이전트 질문 → AskUserQuestion 변환 규칙`과 `## 에러 처리`

TDD 전용 `verify 지문`, `test-file-hash`, RGR 재개 규칙은 `pipeline-state.md`에 그대로 유지한다. gx-dev reference에서 복사하지 않는다.

- [ ] **Step 2: gx-tdd SKILL.md에 필수 Read 순서를 넣는다**

```markdown
## 필수 실행 계약 로드

Phase 목록을 계산하기 전에 다음 파일을 순서대로 Read한다.

1. `Read("references/intent-routing.md")`
2. `Read("references/pipeline-state.md")`
3. `Read("references/interaction-contract.md")`

세 파일을 읽은 뒤 TDD Phase 실행 루프를 수행한다. RED → IMPLEMENT → VERIFY와 Given-When-Then 게이트는 아래 본문과 phase 파일의 지시를 유지한다.
```

- [ ] **Step 3: pipeline·question 테스트의 gx-tdd 검사도 bundle helper를 사용하게 한다**

Task 3에서 추가한 `skill_bundle()`에 `.claude/skills/gx-tdd`를 전달한다. `maintenance-notes.md`, `harness-adaptation.md`, `codex-roles/`는 동작 계약 bundle에서 제외하고 세 새 reference만 명시적으로 합친다.

- [ ] **Step 4: lint의 이동 문구 검사를 TDD_SKILL_TEXT로 바꾼다**

Run: `rg -n '\.claude/skills/gx-tdd/SKILL\.md' scripts/lint-consistency.sh`

이동한 intent/state/interaction 문구의 grep 입력만 `printf '%s' "$TDD_SKILL_TEXT"`로 바꾼다. frontmatter, TDD 차별점, Phase 실행 루프, RGR 강제 문구처럼 main에 남긴 계약은 직접 검색을 유지한다.

- [ ] **Step 5: maintenance notes에 파일 소유권을 기록한다**

```markdown
- **메인 지시문 모듈 경계**: gx-dev·gx-tdd는 `intent-routing.md`(인자·모드·phase 선택), `pipeline-state.md`(코드 맵·원장·경로·state·gate), `interaction-contract.md`(질문 변환·에러 처리)를 각 references에 둔다. SKILL.md는 Agent/Phase 실행 순서와 안전 게이트를 소유한다. 이동 시 양쪽 같은 책임 파일과 `scripts/lint-consistency.sh`의 bundle 검색을 함께 갱신한다.
```

- [ ] **Step 6: tdd 바이트·행 상한과 전체 검증을 실행한다**

Run: `python -m unittest tests.test_codex_skill_pipeline tests.test_codex_skill_questions tests.test_codex_skill_layout -v && bash scripts/lint-consistency.sh`

Expected: 모든 테스트 OK, lint 36/36, gx-tdd SKILL.md 520행 이하, 기존 63,000B 예산 이하.

- [ ] **Step 7: 커밋한다**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-tdd/references/intent-routing.md .claude/skills/gx-tdd/references/pipeline-state.md .claude/skills/gx-tdd/references/interaction-contract.md .claude/skills/gx-tdd/references/maintenance-notes.md scripts/lint-consistency.sh tests/test_codex_skill_pipeline.py tests/test_codex_skill_questions.py
git commit -m "refactor: gx-tdd 실행 계약을 참조 파일로 분리한다"
```

---

### Task 5: 모듈화가 동작을 바꾸지 않았는지 검증한다

**Files:**
- Create: `docs/reports/2026-09-15-skill-instruction-layout-validation.md`

**Interfaces:**
- Consumes: Task 1~4 결과
- Produces: E 통합 릴리스의 D 완료 증거

- [ ] **Step 1: 링크와 번들 경로를 검사한다**

Run: `python -m unittest tests.test_codex_skill_layout tests.test_codex_skill_context tests.test_codex_skill_pipeline tests.test_codex_skill_questions -v`

Expected: 모든 테스트 OK.

Run: `python scripts/sync-codex-resources.py --check && bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh && bash scripts/test-behavior-tests.sh`

Expected: sync check 성공, lint 36/36, hook tests와 behavior mock 성공.

- [ ] **Step 2: 전체 Codex 계약 테스트를 실행한다**

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`

Expected: 모든 테스트 OK.

- [ ] **Step 3: 이동 전후에 금지된 절 중복이 없는지 확인한다**

Run: `rg -n '^## (인자|코드 맵|Trust Ledger \(신뢰 원장\)|플래그 충돌 검증|에러 처리)$|^### 에이전트 질문 → AskUserQuestion 변환 규칙$' .claude/skills/gx-dev .claude/skills/gx-tdd`

Expected: 각 헤딩은 스킬별 한 번씩이며, 계획한 reference 파일에만 존재한다.

- [ ] **Step 4: 분기 검증 보고서를 작성한다**

```markdown
# 핵심 스킬 지시문 모듈화 검증

- 분기: `refactor/skill-instruction-layout`
- 결과: PASS

| 검사 | 결과 |
|---|---|
| `test_codex_skill_layout.py` | PASS |
| 전체 Codex unittest | PASS |
| lint 36/36 | PASS |
| hook-tests | PASS |
| behavior mock | PASS |
```

- [ ] **Step 5: 증거를 커밋한다**

```bash
git add docs/reports/2026-09-15-skill-instruction-layout-validation.md
git commit -m "docs: 핵심 스킬 모듈화 검증 결과를 기록한다"
```
