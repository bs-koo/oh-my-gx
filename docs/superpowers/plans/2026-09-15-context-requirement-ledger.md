# gx-context 요구사항 원장 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `gx-context --from`이 추출한 요구사항을 `status.md`에 영속화하고, 누락 없는 증분 sync 범위를 유지한다.

**Architecture:** `status.md`의 5열 표를 요구사항 원장 정본으로 확정한다. 문서 분석 결과는 context 생성·갱신 직후 원장에 ID 안정성을 유지하며 병합되고, 작업계획은 병합 결과의 ID만 참조한다. sync는 status.md의 숨김 cursor를 기준으로 변경 범위를 계산한다.

**Tech Stack:** Markdown skill instructions, Python 3.10 `unittest`, Git/SVN/gh command contracts

**Spec:** `docs/superpowers/specs/2026-09-15-core-skills-hardening-design.md` — D1

## Global Constraints

- 기준 브랜치: `docs/codex-skill-maintenance`의 `5893c6c`; 작업 브랜치: `feat/context-requirement-ledger`.
- 이 브랜치에서는 `gx-dev`와 `gx-tdd` 파일을 수정하지 않는다.
- `status.md` 열 순서는 `ID | 요구사항 | AC | 상태 | PR`로 고정한다.
- 기존 `✅` 행의 ID·AC·상태·PR은 문서 재분석만으로 바꾸지 않는다.
- 기능 브랜치에서는 manifest·marketplace·CHANGELOG 버전을 바꾸지 않는다.
- 테스트 파일명은 `tests/test_codex_skill_context.py`로 하여 기존 CI가 Windows와 Linux에서 자동 실행하게 한다.

---

### Task 1: status.md 원장 형식을 정본으로 만든다

**Files:**
- Create: `tests/test_codex_skill_context.py`
- Modify: `.claude/rules/context-docs.md`
- Modify: `.claude/skills/gx-context/SKILL.md` — B-9-1

**Interfaces:**
- Consumes: 없음
- Produces: `STATUS_HEADER = "| ID | 요구사항 | AC | 상태 | PR |"`, 상태 집합 `⬜|✅|🚫`

- [ ] **Step 1: 원장 형식 회귀 테스트를 작성한다**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_SKILL = ROOT / ".claude/skills/gx-context/SKILL.md"
CONTEXT_RULE = ROOT / ".claude/rules/context-docs.md"
STATUS_HEADER = "| ID | 요구사항 | AC | 상태 | PR |"


class ContextRequirementLedgerTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_status_template_has_canonical_ledger(self):
        text = self.read(CONTEXT_SKILL)
        self.assertIn(STATUS_HEADER, text)
        self.assertIn("|---|---|---|---|---|", text)
        self.assertIn("🚫 폐기", text)

    def test_context_rule_declares_same_schema(self):
        text = self.read(CONTEXT_RULE)
        self.assertIn(STATUS_HEADER, text)
        self.assertIn("FR-N", text)
        self.assertIn("NFR-N", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 기존 빈 템플릿 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_context.ContextRequirementLedgerTests.test_status_template_has_canonical_ledger tests.test_codex_skill_context.ContextRequirementLedgerTests.test_context_rule_declares_same_schema -v`

Expected: 두 테스트 모두 `AssertionError`로 FAIL하고, 누락 문자열에 `| ID | 요구사항 | AC | 상태 | PR |`가 표시된다.

- [ ] **Step 3: gx-context B-9-1 템플릿을 완성한다**

기존 범례 아래에 다음 내용을 넣는다.

```markdown
- 🚫 폐기 — 승인된 문서 갱신에서 제거됨

## 요구사항 원장

| ID | 요구사항 | AC | 상태 | PR |
|---|---|---|---|---|

작성 규칙:
- ID는 기능 요구사항 `FR-N`, 비기능 요구사항 `NFR-N` 형식이다.
- 입력 문서의 ID가 유효하고 중복되지 않으면 유지한다.
- ID가 없거나 중복이면 유형별 기존 최댓값 다음 번호를 부여하며 삭제된 번호를 재사용하지 않는다.
- AC가 연결되기 전과 구현 근거가 없을 때는 각각 `-`를 쓴다.
```

- [ ] **Step 4: context-docs.md에 정본을 기록한다**

`코드 반영 상태` 규칙 바로 아래에 다음 블록을 추가한다.

```markdown
### status.md 요구사항 원장

| ID | 요구사항 | AC | 상태 | PR |
|---|---|---|---|---|
| FR-1 | 사용자는 이메일로 로그인할 수 있다 | AC-1,AC-2 | ⬜ | - |

- ID는 `FR-N` 또는 `NFR-N`이며 삭제된 번호를 재사용하지 않는다.
- 상태는 `⬜`(미반영), `✅`(반영), `🚫`(폐기) 중 하나다.
- `plan.md`의 요구사항 열은 이 ID를 참조할 뿐 status 상태를 직접 변경하지 않는다.
```

- [ ] **Step 5: 테스트와 기존 린트를 실행한다**

Run: `python -m unittest tests.test_codex_skill_context -v && bash scripts/lint-consistency.sh`

Expected: 2 tests OK, lint 36/36 통과.

- [ ] **Step 6: 커밋한다**

```bash
git add tests/test_codex_skill_context.py .claude/rules/context-docs.md .claude/skills/gx-context/SKILL.md
git commit -m "feat: status.md 요구사항 원장 형식을 확정한다"
```

---

### Task 2: `--from` 분석 결과를 원장에 안정적으로 병합한다

**Files:**
- Modify: `tests/test_codex_skill_context.py`
- Modify: `.claude/skills/gx-context/SKILL.md` — C-4와 C-5 사이
- Modify: `tests/golden-scenarios.md`

**Interfaces:**
- Consumes: Task 1의 `STATUS_HEADER`, C-2의 추출 요구사항 배열
- Produces: `LEDGER_REQUIREMENTS` 배열 `{id, type, text, ac, status, pr}`; C-5는 이 배열의 ID만 사용

- [ ] **Step 1: producer·병합 순서 테스트를 추가한다**

`ContextRequirementLedgerTests`에 다음 메서드를 추가한다.

```python
    def test_from_mode_persists_requirements_before_plan(self):
        text = self.read(CONTEXT_SKILL)
        producer = text.index("### C-4-1. 요구사항 원장 반영")
        planner = text.index("### C-5. 작업 계획")
        self.assertLess(producer, planner)
        section = text[producer:planner]
        for phrase in (
            "LEDGER_REQUIREMENTS",
            "기존 ID·AC·상태·PR을 유지",
            "삭제된 번호를 재사용하지 않는다",
            "승인한 경우에만 `🚫`",
            "C-5는 `LEDGER_REQUIREMENTS`의 ID",
        ):
            self.assertIn(phrase, section)

    def test_new_context_does_not_drop_extracted_requirements(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4. context 생성"):text.index("### C-5. 작업 계획")]
        self.assertIn("B-5~B-11", section)
        self.assertIn("C-4-1을 반드시 실행", section)
```

- [ ] **Step 2: 새 테스트가 producer 부재로 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_context.ContextRequirementLedgerTests.test_from_mode_persists_requirements_before_plan tests.test_codex_skill_context.ContextRequirementLedgerTests.test_new_context_does_not_drop_extracted_requirements -v`

Expected: `ValueError: substring not found` 또는 `AssertionError`로 FAIL.

- [ ] **Step 3: C-4 위임 뒤에도 원장 단계가 실행되도록 명시한다**

C-4 마지막 문장을 다음 문장으로 교체한다.

```markdown
**두 경우 모두 context 문서 작업이 끝나면 C-4-1을 반드시 실행한 뒤 C-5로 이어서 진행한다.** 모드 B·D로 위임해도 `--from` 경로는 요구사항 원장과 작업계획을 만들기 전에는 끝나지 않는다.
```

- [ ] **Step 4: C-4-1 원장 병합 절을 추가한다**

C-4와 C-5 사이에 다음 블록을 추가한다.

```markdown
### C-4-1. 요구사항 원장 반영

C-2에서 추출한 각 요구사항을 `{ id, type, text, ac, status, pr }`로 정규화하여 `LEDGER_REQUIREMENTS`를 만든다. type은 기능이면 `FR`, 비기능이면 `NFR`; 새 항목의 ac·pr은 `-`, status는 `⬜`다.

`context/{도메인}/status.md`의 `## 요구사항 원장` 표를 Read하고 다음 순서로 병합한다.

1. 입력 ID가 유효하고 기존 행과 같으면 같은 항목으로 본다.
2. ID가 없으면 공백·문장부호를 제거한 핵심 문장을 비교한다. 같은 항목이면 기존 ID·AC·상태·PR을 유지하고 승인된 요구사항 문장만 갱신한다.
3. 새 항목은 유형별 기존 최댓값 다음 번호를 받는다. 삭제된 번호를 재사용하지 않는다.
4. 기존 입력에서 사라진 `⬜` 행은 변경 제안에 포함하고 사용자가 제거를 승인한 경우에만 `🚫`로 바꾼다. `✅` 행은 자동 폐기하지 않는다.
5. Edit으로 기존 행을 수정하고 새 행을 표 끝에 추가한다. 기존 파일 전체를 Write로 덮어쓰지 않는다.
6. 저장한 표를 다시 읽어 ID 중복, 빈 요구사항, 허용되지 않은 상태, 기존 `✅` 행의 ID·AC·상태·PR 변경이 없는지 확인한다. 실패하면 C-5로 진행하지 않는다.

C-5는 `LEDGER_REQUIREMENTS`의 ID만 `plan.md` 요구사항 열에 기록한다. C-2의 임시 번호나 원문에 없는 새 ID를 계획에 쓰지 않는다.
```

- [ ] **Step 5: 골든 시나리오 S44를 추가한다**

`tests/golden-scenarios.md`의 S43 다음에 다음 행을 추가하고 기록 절의 총 시나리오 수를 44로 갱신한다.

```markdown
| S44 ★ | context가 없는 저장소, 입력 문서에 ID 없는 기능 요구사항 3건과 `NFR-2` 1건 | `/gx-context 주문 --from requirements/order.md` | `context/주문/status.md` 원장에 `FR-1~3`과 `NFR-2`의 요구사항 문장이 남고 `.dev/plan.md`는 그 ID만 참조한다. 같은 문서를 다시 실행해도 ID가 늘지 않으며 기존 ✅ 행의 AC·PR은 유지된다 | gx-context C-4-1 요구사항 원장 병합 |
```

- [ ] **Step 6: 테스트를 통과시킨다**

Run: `python -m unittest tests.test_codex_skill_context -v && bash scripts/lint-consistency.sh`

Expected: 4 tests OK, lint 36/36 통과.

- [ ] **Step 7: 커밋한다**

```bash
git add tests/test_codex_skill_context.py .claude/skills/gx-context/SKILL.md tests/golden-scenarios.md
git commit -m "feat: 문서 요구사항을 status 원장에 병합한다"
```

---

### Task 3: sync cursor로 검색 범위를 연속화한다

**Files:**
- Modify: `tests/test_codex_skill_context.py`
- Modify: `.claude/skills/gx-context/SKILL.md` — B-9-1, E-1~E-4

**Interfaces:**
- Consumes: Task 1의 status.md
- Produces: `SYNC_GIT_HEAD`, `SYNC_SVN_REVISION`, `SYNC_PR_MERGED_AT`

- [ ] **Step 1: cursor·실패 보존 테스트를 추가한다**

```python
    def test_sync_uses_persisted_cursor(self):
        text = self.read(CONTEXT_SKILL)
        for phrase in (
            "<!-- gx-sync",
            "git-head:",
            "svn-revision:",
            "pr-merged-at:",
            "${SYNC_GIT_HEAD}..HEAD",
            "분석·명령 실패 시 cursor를 갱신하지 않는다",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("git log --oneline -20", text)

    def test_initial_sync_searches_ids_across_history(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        self.assertIn("각 pending FR/NFR/AC ID를 전체 이력", section)
        self.assertIn("설명 키워드는 최근 100건", section)
```

- [ ] **Step 2: 기존 고정 20건 검색 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_context.ContextRequirementLedgerTests.test_sync_uses_persisted_cursor tests.test_codex_skill_context.ContextRequirementLedgerTests.test_initial_sync_searches_ids_across_history -v`

Expected: `<!-- gx-sync` 누락과 `git log --oneline -20` 잔존으로 FAIL.

- [ ] **Step 3: status 템플릿에 cursor 블록을 추가한다**

B-9-1 표 작성 규칙 뒤에 다음 블록을 추가한다.

```markdown
<!-- gx-sync
git-head: -
svn-revision: -
pr-merged-at: -
-->
```

- [ ] **Step 4: E-1에서 cursor를 파싱한다**

E-1 목록에 다음 항목을 추가한다.

```markdown
4. `<!-- gx-sync ... -->`에서 `SYNC_GIT_HEAD`, `SYNC_SVN_REVISION`, `SYNC_PR_MERGED_AT`을 읽는다. 블록이나 값이 없으면 `-`로 둔다.
5. git이면 현재 `HEAD`, svn이면 현재 revision, gh가 있으면 현재 UTC 시각을 갱신 후보로 저장한다. 아직 status.md에는 쓰지 않는다.
```

- [ ] **Step 5: E-2의 고정 조회를 cursor 조회로 교체한다**

```markdown
1. **git cursor 있음**: `git merge-base --is-ancestor ${SYNC_GIT_HEAD} HEAD`가 성공하면 `git log --oneline ${SYNC_GIT_HEAD}..HEAD`를 조회한다. ancestor가 아니면 cursor 손상으로 보고 초기 조회로 전환한다.
2. **git 초기 조회**: 각 pending FR/NFR/AC ID를 전체 이력에서 `git log --all --oneline --regexp-ignore-case --grep=<ID>`로 정확히 검색한다. 설명 키워드는 최근 100건 `git log --oneline -100`에서 보조 검색한다.
3. **svn cursor 있음**: `svn log -r ${SYNC_SVN_REVISION}:HEAD`를 조회한다. 초기 조회는 각 pending ID로 `svn log --search <ID>`를 수행하고 설명 키워드는 `svn log -l 100`에서 보조 검색한다.
4. **PR**: gh가 있고 `SYNC_PR_MERGED_AT`이 있으면 `gh pr list --state merged --search "merged:>=${SYNC_PR_MERGED_AT}" --limit 100`을 사용한다. 초기 조회는 각 pending ID로 `gh pr list --state merged --search "<ID> in:title,body" --limit 100`을 수행한다.
5. 커밋 메시지와 PR 제목·본문에서 pending ID를 우선 매칭하고, ID가 없을 때만 설명 키워드 일치를 후보로 제시한다.
6. 명령 실패는 해당 소스의 `분석 실패`로 표시한다. 분석·명령 실패 시 cursor를 갱신하지 않는다.
```

- [ ] **Step 6: E-4에서 사용자 결정 뒤 cursor를 전진시킨다**

E-4 끝에 다음 규칙을 추가한다.

```markdown
- 사용자가 `전체 반영`, `조정 후 반영`, `건너뛰기` 중 하나를 확정하고 모든 분석 명령이 성공한 경우에만 gx-sync 블록을 현재 HEAD/revision/UTC 시각으로 Edit한다.
- 질문 중단, 파일 Edit 실패, 분석·명령 실패 시 기존 cursor를 유지한다.
```

- [ ] **Step 7: 전체 검증 후 커밋한다**

Run: `python -m unittest tests.test_codex_skill_context -v && python scripts/sync-codex-resources.py --check && bash scripts/lint-consistency.sh`

Expected: 6 tests OK, sync check 성공, lint 36/36 통과.

```bash
git add tests/test_codex_skill_context.py .claude/skills/gx-context/SKILL.md
git commit -m "feat: context 동기화 범위를 cursor로 추적한다"
```

---

### Task 4: gx-context의 SVN 저장소 ID를 공통 규칙으로 바꾼다

**Files:**
- Modify: `tests/test_codex_skill_context.py`
- Modify: `.claude/skills/gx-context/SKILL.md` — PROJECTS.md 자동 등록

**Interfaces:**
- Consumes: SVN working-copy URL
- Produces: pipeline 분기와 같은 `REPOSITORY_ID`

- [ ] **Step 1: gx-context SVN 식별 테스트를 추가한다**

```python
    def test_context_uses_shared_svn_repository_identity(self):
        text = self.read(CONTEXT_SKILL)
        for phrase in (
            "svn info --show-item url",
            "trunk",
            "branches/<name>",
            "tags/<name>",
            "REPOSITORY_ID",
            "basename(PROJECT_ROOT)",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("svn info --show-item repos-root-url", text)
```

- [ ] **Step 2: 기존 repos-root-url 규칙 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_context.ContextRequirementLedgerTests.test_context_uses_shared_svn_repository_identity -v`

Expected: `svn info --show-item url` 누락으로 FAIL.

- [ ] **Step 3: PROJECTS.md 자동 등록의 SVN 설명을 교체한다**

```markdown
- **PROJECTS.md**: 현재 레포를 자동 등록한다. git은 `git remote get-url origin`의 레포명을 사용한다. svn은 `svn info --show-item url` 끝의 `trunk`, `branches/<name>`, `tags/<name>`을 제거하고 남은 마지막 세그먼트를 `REPOSITORY_ID`로 사용하며, 결과가 비거나 모호하면 `basename(PROJECT_ROOT)`를 사용한다.
```

- [ ] **Step 4: 테스트와 린트를 실행한다**

Run: `python -m unittest tests.test_codex_skill_context -v && bash scripts/lint-consistency.sh`

Expected: context 테스트 모두 OK, lint 36/36 통과.

- [ ] **Step 5: 커밋한다**

```bash
git add tests/test_codex_skill_context.py .claude/skills/gx-context/SKILL.md
git commit -m "fix: gx-context의 SVN 저장소 식별 규칙을 통일한다"
```

---

### Task 5: 브랜치 수용 증거를 정리한다

**Files:**
- Create: `docs/reports/2026-09-15-context-requirement-ledger-validation.md`

**Interfaces:**
- Consumes: Task 1~3 결과
- Produces: 통합 브랜치가 확인할 A 완료 커밋 SHA와 검증 결과

- [ ] **Step 1: 전체 자동 검증을 실행한다**

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`

Expected: 모든 Codex 계약 테스트 OK.

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh && bash scripts/test-behavior-tests.sh`

Expected: lint 36/36, 훅 테스트 성공, 행동 테스트 mock 성공.

- [ ] **Step 2: 변경 범위를 확인한다**

Run: `git diff --check docs/codex-skill-maintenance...HEAD && git diff --name-only docs/codex-skill-maintenance...HEAD`

Expected: whitespace 오류 없음. 변경 파일은 gx-context, context-docs, golden scenarios, context 계약 테스트, 설계 명세뿐이다.

- [ ] **Step 3: 분기 검증 보고서를 작성한다**

```markdown
# gx-context 요구사항 원장 검증

- 기준 커밋: `5893c6c`
- 분기: `feat/context-requirement-ledger`
- 결과: PASS

| 검사 | 결과 |
|---|---|
| `test_codex_skill_context.py` | PASS |
| lint 36/36 | PASS |
| hook-tests | PASS |
| behavior mock | PASS |
```

- [ ] **Step 4: 문서 증거를 커밋한다**

```bash
git add docs/reports/2026-09-15-context-requirement-ledger-validation.md
git commit -m "docs: 요구사항 원장 분기 검증 결과를 기록한다"
```
