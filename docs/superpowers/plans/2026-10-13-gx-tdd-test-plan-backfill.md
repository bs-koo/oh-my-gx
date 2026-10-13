# gx-tdd 단위테스트계획서 역보강 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR #93의 "계획서 → 하한선" 흐름을 걷어내고, gx-tdd가 작성한 테스트로 gx-pm 단위테스트계획서를 역보강(기존 케이스 결과·기대결과 보강, 신규 케이스 추가)하고 개정이력을 남기는 "gx-tdd → 계획서" 흐름으로 바꾼다.

**Architecture:** gx-tdd는 도메인·요구사항 흐름 그대로 진행하고, phase-complete Step 0.5에서 오케스트레이터가 이번 변경의 테스트를 계획서 행과 짝지은 초안을 쓰면 `de13.py record`가 검증해 `.dev/ut-results/{slug}.md` 원장에 병합한다. `/gx-test-plan`이 `de13.py apply`로 원장을 모아 등록된 계획서 xlsx를 제자리에서 갱신(셀 패치·행 추가·범위 확장·개정이력)하고 원장에 반영 표시를 남긴다. 계획서 경로는 gx-setup이 `config.json` `testPlan.path`에 등록한다.

**Tech Stack:** Python 3.10 표준 라이브러리(zipfile, xml.etree, re), unittest, Markdown 지시문(스킬·phase), Bash 린트.

**Spec:** `docs/superpowers/specs/2026-10-13-gx-tdd-test-plan-backfill-design.md`

## Global Constraints

- 헬퍼는 Python 3.10 표준 라이브러리만 쓴다. 파일 입출력은 `encoding="utf-8"`.
- 메시지·문서는 한국어. 이모지는 기존 출력 관례(`완료 ✅`) 외에 쓰지 않는다.
- 커밋은 `oh-my-gx:gx-commit` 스킬로만 한다. 메시지 `feat: …`, `Co-Authored-By` 금지. `git push --force` 금지.
- 워크트리 가드: Bash 명령은 단순 명령으로, 복잡한 처리는 scratchpad의 Python 스크립트로 한다. 캐시(`__pycache__`)는 스테이징하지 않는다.
- `phase-setup.md` ≤ 22000B, gx-tdd `SKILL.md` ≤ 63000B (린트 [32]).
- 역할 정의를 바꾸면 `python scripts/sync-codex-resources.py`, `.claude/config.json`을 바꿔도 같은 명령으로 템플릿을 동기화한다.
- Codex 질문 규칙: 질문 1~3개, 선택지 2~3개, Other를 option으로 직접 넣지 않는다.
- 버전은 1.34.0 유지(미릴리스), CHANGELOG 날짜만 2026-10-13으로 바꾼다.
- 날짜 형식은 계획서 관례 `YYYY.MM.DD`.
- 검증 명령: `python -m unittest discover -s tests -p "test_de13_*.py" -v`, `python -m unittest discover -s tests -p "test_codex_*.py"`, `python scripts/sync-codex-resources.py --check`, `bash scripts/hook-tests.sh`, `bash scripts/lint-consistency.sh`(약 4분, timeout 600000).

## Review Focus

1. 엑셀에서 다시 저장된 계획서(공유 문자열, 셀이 빠진 행)에 신규 행을 추가해도 다시 읽히고 범위가 맞아야 한다 — Task 4 `test_shared_strings_plan_with_missing_cells_gets_new_row`.
2. 계획서가 엑셀에서 열려 교체가 실패하면 계획서도 원장도 바뀌지 않아야 한다 — Task 4 `test_excel_lock_leaves_plan_and_ledger_untouched`.
3. `/gx-test-plan` 반영 후 같은 브랜치에서 complete를 다시 돌리거나 apply를 다시 돌려도 중복 행이 생기지 않아야 한다 — Task 3 `test_merge_keeps_applied_rows_and_replaces_pending`, Task 4 `test_second_run_changes_nothing`.
4. AI가 쓴 초안의 테스트 위치가 없는 줄·skip 테스트를 가리키면 원장에 들어가지 않아야 한다 — Task 3 `test_location_must_point_to_live_test`.
5. 원장 기록과 반영 사이에 PM이 계획서 행을 고치면 덮어쓰지 않고 "재확인 필요"로 남아야 한다 — Task 4 `test_changed_or_unknown_rows_are_reported_and_left_pending`.

---

## 파일 구조

| 파일 | 역할 | 변경 |
|---|---|---|
| `.claude/skills/gx-test-plan/scripts/de13.py` | 계획서 읽기, 테스트 목록(`tests`), 기능 목록(`functions`), UT 행(`rows`), 원장 기록(`record`), 반영(`apply`) | 재작성 |
| `tests/de13_support.py` | xlsx 픽스처 생성(필터·정의 이름 추가) | 수정 |
| `tests/test_de13_read.py` | 계획서 읽기·지문·md 표·functions/rows | 신규(구 scope 대체) |
| `tests/test_de13_tests.py` | diff 파일 목록·테스트 선언 목록·위치 판정 | 신규 |
| `tests/test_de13_skip.py` | skip 휴리스틱 회귀(구 check 이관) | 신규(구 check 대체) |
| `tests/test_de13_record.py` | 초안 검증·원장 병합 | 재작성 |
| `tests/test_de13_apply.py` | 기존 행 패치·신규 행·범위·제자리 쓰기 | 재작성 |
| `tests/test_de13_revision.py` | 개정이력·버전·CLI | 신규 |
| `tests/test_de13_contract.py` | 지시문 계약 | 재작성 |
| `.claude/skills/gx-tdd/phases/phase-complete.md` | Step 0.5 원장 작성 | main 복원 후 추가 |
| `.claude/skills/gx-tdd/...`, `agents/*.md` | 하한선 흐름 | main 복원 |
| `.claude/skills/gx-setup/SKILL.md`, `.claude/config.json`, 템플릿 | 계획서 경로 등록 | 수정 |
| `.claude/skills/gx-test-plan/SKILL.md` | 제자리 갱신 절차 | 재작성 |
| `.claude/skills/gx-commit/SKILL.md`, `.claude/rules/skill-routing.md` | export 제거, 라우팅 문구 | 수정 |
| 문서류 | 새 흐름 설명 | 수정 |

---

### Task 1: 하한선 흐름 걷어내기 (gx-tdd·에이전트 main 복원)

**Files:**
- Restore from main: `.claude/skills/gx-tdd/phases/phase-setup.md`, `setup-resume.md`, `phase-requirements.md`, `phase-design.md`, `phase-implement.md`, `phase-review.md`, `phase-complete.md`, `.claude/skills/gx-tdd/references/pipeline-state.md`, `.claude/skills/gx-tdd/SKILL.md`, `agents/product-owner.md`, `agents/red-writer.md`, `agents/test-architect.md`, `agents/reviewer.md`, `scripts/lint-consistency.sh`
- Delete: `.claude/skills/gx-tdd/phases/setup-testplan.md`, `tests/test_de13_contract.py`
- Modify: `.claude/skills/gx-tdd/SKILL.md` (allowed-tools에 python 재추가)
- Regenerate: `.claude/skills/gx-dev/references/codex-roles/*`

**Interfaces:**
- Consumes: 없음
- Produces: gx-tdd 지시문이 main과 같음(SKILL.md allowed-tools의 `"Bash(python *)", "Bash(python3 *)"`만 차이). Task 6이 phase-complete에 Step 0.5를 추가한다.

- [ ] **Step 1: main 버전으로 복원**

```bash
git checkout main -- .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-tdd/phases/setup-resume.md .claude/skills/gx-tdd/phases/phase-requirements.md .claude/skills/gx-tdd/phases/phase-design.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-tdd/phases/phase-review.md .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-tdd/references/pipeline-state.md .claude/skills/gx-tdd/SKILL.md agents/product-owner.md agents/red-writer.md agents/test-architect.md agents/reviewer.md scripts/lint-consistency.sh
git rm -q .claude/skills/gx-tdd/phases/setup-testplan.md tests/test_de13_contract.py
```

- [ ] **Step 2: allowed-tools에 python 재추가**

`.claude/skills/gx-tdd/SKILL.md` frontmatter의 `"Bash(dotnet *)", "Bash(gh *)"`를 `"Bash(dotnet *)", "Bash(python *)", "Bash(python3 *)", "Bash(gh *)"`로 바꾼다 (Step 0.5가 헬퍼를 실행한다).

- [ ] **Step 3: codex-roles 재생성과 잔재 확인**

Run: `python scripts/sync-codex-resources.py`
Run: `python scripts/sync-codex-resources.py --check`
Expected: 드리프트 없음
Run: Grep `ut-scope|ut-floor|setup-testplan|Step -1\.5|\[UT: ` in `.claude/skills/gx-tdd`, `agents`, `.claude/skills/gx-dev/references/codex-roles`
Expected: 0건
Run: `git diff --stat main -- .claude/skills/gx-tdd agents .claude/skills/gx-dev/references/codex-roles scripts/lint-consistency.sh`
Expected: `.claude/skills/gx-tdd/SKILL.md` 1줄 변경만

- [ ] **Step 4: 헬퍼 테스트가 여전히 통과하는지 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py"`
Expected: OK (contract 제외 나머지 그대로)

- [ ] **Step 5: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `gx-tdd에서 계획서 하한선 흐름을 걷어낸다`. 스테이징 대상은 위 파일과 codex-roles만 (캐시 제외).

---

### Task 2: 테스트 목록·기능 목록·UT 행 명령 (scope·check 대체)

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py`
- Modify: `tests/de13_support.py`
- Create: `tests/test_de13_read.py`, `tests/test_de13_tests.py`, `tests/test_de13_skip.py`
- Delete: `tests/test_de13_scope.py`, `tests/test_de13_check.py`

**Interfaces:**
- Consumes: 기존 `load_plan`, `row_fingerprint`, `read_md_table`, `write_md_table`, `function_list`, `_strip_comments`, `_test_header`, `_is_skipped`, `DECL_RE`, `PY_MODULE_SKIP_RE`, `SKIP_DIRS`, `TEST_DIRS`, `SOURCE_EXT`, `TEST_FILE_RE`
- Produces:
  - `load_plan(path) -> dict` 반환에 `"index": int`(시트 순번, 0부터) 추가
  - `changed_files(diff_text: str) -> list[str]`
  - `_is_test_file(rel: str) -> bool`
  - `_load_source(path: Path) -> tuple[list[str], bool]` (주석 제거 줄, 모듈 skip 여부)
  - `list_tests(root: Path, files: list[str]) -> list[dict]` — `{"path","line","decl","skipped"}`
  - `locate_test(root: Path, location: str) -> dict | None` — `{"path","line","skipped"}`
  - `plan_rows(plan: dict, fn_ids: list[str]) -> list[dict]` — `ROWS_HEADER` 키
  - `ROWS_HEADER = ["테스트ID", "연계기능ID", "사전조건", "입력", "기대결과", "사후조건", "결과", "행 지문"]`
  - CLI `tests --diff --root --out`, `functions --plan [--spec] --out`, `rows --plan --fn --out` (종료 코드 0/2)
  - `make_xlsx(..., filters: dict[str, str] | None = None)` — 시트명 → 필터 시작 셀

- [ ] **Step 1: 픽스처에 필터·정의 이름 추가**

`tests/de13_support.py`의 `_sheet_xml`과 `make_xlsx`를 아래로 바꾼다 (validation·rich는 `단위테스트계획` 시트, 없으면 첫 시트에 적용).

```python
def _abs(rng: str) -> str:
    import re
    return re.sub(r"([A-Z]+)(\d+)", r"$\1$\2", rng)


def _sheet_xml(rows, shared_index, validation, style, rich, filter_from=None):
    body = []
    for r, values in enumerate(rows, start=1):
        cells = "".join(
            _cell(f"{_col(c)}{r}", v, shared_index, style, rich.get(f"{_col(c)}{r}"))
            for c, v in enumerate(values))
        body.append(f'<row r="{r}">{cells}</row>')
    last = f"{_col(max((len(r) for r in rows), default=1) - 1)}{len(rows)}"
    dim = f'<dimension ref="A1:{last}"/>' if filter_from else ""
    af = f'<autoFilter ref="{filter_from}:{last}"/>' if filter_from else ""
    dv = ""
    if validation:
        dv = (f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" '
              f'sqref="{validation}"><formula1>"Pass,Fail"</formula1></dataValidation></dataValidations>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{dim}<sheetData>{"".join(body)}</sheetData>{af}{dv}</worksheet>'), last


def make_xlsx(path: Path, sheets, shared=False, validation=None, style=None, rich=None, filters=None):
    """sheets: [(시트명, [[셀값,...],...]), ...].
    shared=True면 공유 문자열(엑셀 재저장 형식). validation(결과 열 데이터 검증 범위)과
    rich={"D2": ["앞", "뒤"]}(서식 런)는 '단위테스트계획' 시트(없으면 첫 시트)에 적용한다.
    filters={"시트명": "A1"}이면 그 시트에 dimension·autoFilter·_FilterDatabase 정의 이름을 넣는다."""
    shared_index = {} if shared else None
    filters = filters or {}
    target = next((i for i, (name, _) in enumerate(sheets) if name == "단위테스트계획"), 0)
    sheet_parts, defined = [], []
    for n, (name, rows) in enumerate(sheets):
        xml, last = _sheet_xml(rows, shared_index, validation if n == target else None, style,
                               (rich or {}) if n == target else {}, filters.get(name))
        sheet_parts.append((name, f"xl/worksheets/sheet{n + 1}.xml", xml))
        if name in filters:
            defined.append(f'<definedName name="_xlnm._FilterDatabase" localSheetId="{n}" hidden="1">'
                           f"'{escape(name)}'!{_abs(filters[name] + ':' + last)}</definedName>")
    names = f"<definedNames>{''.join(defined)}</definedNames>" if defined else ""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        sheets_xml = "".join(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _, _) in enumerate(sheet_parts, start=1))
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f'<sheets>{sheets_xml}</sheets>{names}</workbook>')
        rels = "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(sheet_parts) + 1))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'{rels}</Relationships>')
        for _, part, xml in sheet_parts:
            z.writestr(part, xml)
        if shared_index is not None:
            items = "".join(f"<si><t>{escape(v)}</t></si>" for v, _ in sorted(shared_index.items(), key=lambda kv: kv[1]))
            z.writestr("xl/sharedStrings.xml",
                       '<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                       f'count="{len(shared_index)}" uniqueCount="{len(shared_index)}">{items}</sst>')
    return path
```

- [ ] **Step 2: 실패하는 테스트 작성 — `tests/test_de13_read.py`**

`tests/test_de13_scope.py`에서 `test_reads_inline_strings_and_resolves_ditto_within_same_function`, `test_ditto_across_function_boundary_is_not_resolved`, `test_reads_shared_strings_and_rich_runs`, `test_finds_header_by_name_with_title_row_renamed_sheet_and_12_columns`, `test_missing_required_column_is_input_error`, `test_fingerprint_ignores_whitespace_and_excludes_test_id`를 클래스 `ReadTests`(setUp·`plan()` 헬퍼 포함)로 그대로 옮기고 아래 테스트를 추가한다. 그 뒤 `tests/test_de13_scope.py`를 지운다.

```python
    def test_load_plan_reports_sheet_index(self):
        self.assertEqual(de13.load_plan(self.plan())["index"], 1)

    def test_pipe_and_newline_survive_md_round_trip(self):
        out = self.dir / "t.md"
        out.write_text(de13.write_md_table(["a", "b"], [{"a": "A | B\n둘째 줄", "b": ""}]), encoding="utf-8")
        self.assertEqual(de13.read_md_table(out)[0]["a"], "A | B\n둘째 줄")

    def test_rows_cli_writes_function_rows_with_fingerprint(self):
        path = self.plan()
        out = self.dir / "rows.md"
        self.assertEqual(de13.main(["rows", "--plan", str(path), "--fn", "FN-002", "--out", str(out)]), 0)
        rows = de13.read_md_table(out)
        self.assertEqual([r["테스트ID"] for r in rows], ["UT-004", "UT-005", "UT-007"])
        self.assertEqual(list(rows[0]), de13.ROWS_HEADER)
        self.assertEqual(rows[1]["사전조건"], "회차 5건")  # 〃 해소
        plan = de13.load_plan(path)
        self.assertEqual(rows[0]["행 지문"], de13.row_fingerprint(next(r for r in plan["rows"] if r["테스트ID"] == "UT-004")))

    def test_rows_cli_unknown_function_returns_2(self):
        out = self.dir / "rows.md"
        self.assertEqual(de13.main(["rows", "--plan", str(self.plan()), "--fn", "FN-999", "--out", str(out)]), 2)
        self.assertFalse(out.exists())

    def test_functions_cli_writes_list_with_names(self):
        spec = make_xlsx(self.dir / "REB-기능명세서.xlsx",
                         [("기능명세", [["기능ID", "대분류", "기능명"], ["FN-001", "전처리", "원천 데이터 등록"]])])
        out = self.dir / "functions.json"
        self.assertEqual(de13.main(["functions", "--plan", str(self.plan()), "--spec", str(spec), "--out", str(out)]), 0)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data[0], {"기능ID": "FN-001", "UT수": 4, "기능명": "원천 데이터 등록"})
        self.assertEqual(data[1], {"기능ID": "FN-002", "UT수": 3, "기능명": ""})
```

- [ ] **Step 3: 실패하는 테스트 작성 — `tests/test_de13_tests.py`**

```python
"""de13.py tests: 변경 파일에서 테스트 선언 목록과 위치 판정."""
import json
import tempfile
import unittest
from pathlib import Path

from de13_support import load_de13

de13 = load_de13()

GIT_DIFF = """diff --git a/src/test/java/a/MemoTest.java b/src/test/java/a/MemoTest.java
new file mode 100644
--- /dev/null
+++ b/src/test/java/a/MemoTest.java
@@ -0,0 +1,3 @@
+class MemoTest {}
diff --git a/src/main/java/a/Memo.java b/src/main/java/a/Memo.java
--- a/src/main/java/a/Memo.java
+++ b/src/main/java/a/Memo.java
@@ -1 +1 @@
diff --git a/old/GoneTest.java b/old/GoneTest.java
deleted file mode 100644
--- a/old/GoneTest.java
+++ /dev/null
"""

SVN_DIFF = """Index: web/src/memo.spec.ts
===================================================================
--- web/src/memo.spec.ts\t(nonexistent)
+++ web/src/memo.spec.ts\t(working copy)
@@ -0,0 +1 @@
"""

JAVA = """package a;
class MemoTest {
    @Test
    void 빈_내용이면_거부() {}
    @Disabled
    @Test
    void 보류() {}
    @ParameterizedTest
    @ValueSource(ints = {1, 2})
    void 길이_경계(int n) {
        assertThat(n).isPositive();
    }
}
"""


class TestsCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 tests 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return rel

    def test_changed_files_from_git_and_svn_diff(self):
        self.assertEqual(de13.changed_files(GIT_DIFF), ["src/test/java/a/MemoTest.java", "src/main/java/a/Memo.java"])
        self.assertEqual(de13.changed_files(SVN_DIFF), ["web/src/memo.spec.ts"])

    def test_lists_each_test_once_with_skip_flag(self):
        rel = self.write("src/test/java/a/MemoTest.java", JAVA)
        tests = de13.list_tests(self.root, [rel])
        self.assertEqual([(t["line"], t["skipped"]) for t in tests], [(3, False), (6, True), (8, False)])
        self.assertIn("빈_내용이면_거부", tests[0]["decl"])
        self.assertIn("ValueSource", tests[2]["decl"])

    def test_lists_js_and_python_tests(self):
        js = self.write("web/src/memo.spec.ts", "describe('메모', () => {\n  it('빈 메모 거부', () => {})\n  it.skip('보류', () => {})\n})\n")
        py = self.write("tests/test_memo.py", "@pytest.mark.parametrize('n', [1])\ndef test_길이(n):\n    pass\n")
        tests = de13.list_tests(self.root, [js, py])
        self.assertEqual([(t["path"], t["skipped"]) for t in tests],
                         [(js, False), (js, True), (py, False)])

    def test_ignores_non_test_build_and_missing_files(self):
        main = self.write("src/main/java/a/Memo.java", "class Memo { @Test void x() {} }\n")
        built = self.write("build/test/MemoTest.java", "@Test\nvoid x() {}\n")
        self.assertEqual(de13.list_tests(self.root, [main, built, "src/test/java/NoFile.java"]), [])

    def test_locate_test_accepts_header_or_body_line_and_rejects_others(self):
        rel = self.write("src/test/java/a/MemoTest.java", JAVA)
        self.assertEqual(de13.locate_test(self.root, f"{rel}:4"), {"path": rel, "line": 4, "skipped": False})
        self.assertFalse(de13.locate_test(self.root, f"{rel}:11")["skipped"])  # 본문 줄
        self.assertTrue(de13.locate_test(self.root, f"{rel}:7")["skipped"])
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:1"))   # package 줄
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:99"))
        self.assertIsNone(de13.locate_test(self.root, "src/main/java/a/Memo.java:1"))
        self.assertIsNone(de13.locate_test(self.root, "MemoTest.java"))

    def test_cli_writes_json_from_diff(self):
        self.write("src/test/java/a/MemoTest.java", JAVA)
        diff = self.root / "diff.txt"
        diff.write_text(GIT_DIFF, encoding="utf-8")
        out = self.root / ".dev" / "x" / "ut-tests.json"
        self.assertEqual(de13.main(["tests", "--diff", str(diff), "--root", str(self.root), "--out", str(out)]), 0)
        self.assertEqual(len(json.loads(out.read_text(encoding="utf-8"))), 3)

    def test_cli_missing_diff_returns_2(self):
        self.assertEqual(de13.main(["tests", "--diff", str(self.root / "none.txt"), "--root", str(self.root),
                                    "--out", str(self.root / "o.json")]), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: skip 회귀를 새 위치 판정으로 이관 — `tests/test_de13_skip.py`**

`tests/test_de13_check.py`를 `tests/test_de13_skip.py`로 옮기고(`git mv`) 다음을 바꾼다.
- 모듈 docstring: `"""skip 휴리스틱 회귀 — locate_test로 판정한다."""`
- `floor_rows` 함수와 `test_only_target_rows_are_checked`, `test_cli_exit_codes_and_json` 테스트를 지운다.
- `status` 메서드를 아래로 바꾼다.

```python
    def status(self, test_id, rows=None):
        """구 check_floor와 같은 판정: ID가 있는 모든 (주석 아닌) 줄을 테스트 위치로 보고 하나라도 살아 있으면 found."""
        raw, under = re.escape(test_id), re.escape(test_id.replace("-", "_"))
        pat = re.compile(rf"(?<![A-Za-z0-9-])(?:{raw}|{under})(?![0-9A-Za-z])")
        locs = []
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root).as_posix()
            if not path.is_file() or not de13._is_test_file(rel):
                continue
            lines, _ = de13._load_source(path)
            for i, line in enumerate(lines):
                if pat.search(line):
                    hit = de13.locate_test(self.root, f"{rel}:{i + 1}")
                    if hit is not None:
                        locs.append(hit)
        if not locs:
            return {"status": "missing", "locations": []}
        return {"status": "found" if any(not l["skipped"] for l in locs) else "skipped", "locations": locs}
```
- 파일 머리에 `import re`를 추가하고 쓰지 않게 된 `import json`은 지운다.
- `de13.check_floor(...)["results"]`를 직접 쓰는 테스트(`test_finds_display_name_and_underscore_forms`, `test_found_wins_when_one_location_is_not_skipped`, `test_ignores_non_test_files_build_dirs_and_dev` 등)는 `{i: self.status(i)["status"] for i in ids}` 형태로 바꾼다. 단언 값은 그대로 둔다.

- [ ] **Step 5: 테스트가 실패하는지 확인**

Run: `python -m unittest tests.test_de13_read tests.test_de13_tests tests.test_de13_skip` (cwd `tests`가 아니면 `python -m unittest discover -s tests -p "test_de13_*.py"`)
Expected: FAIL — `AttributeError: module 'de13' has no attribute 'list_tests'` 등

- [ ] **Step 6: de13.py 구현**

1) 모듈 docstring을 바꾼다.

```python
"""DE-13 단위테스트계획서(xlsx) 역보강 헬퍼 — Python 3.10 표준 라이브러리 전용.

tests     : diff의 변경 테스트 파일에서 테스트 선언 목록을 뽑는다
functions : 계획서 기능 목록(기능ID·기능명·UT 수)
rows      : 지정 기능의 UT 행과 행 지문
record    : gx-tdd가 쓴 짝짓기 초안을 검증해 원장에 병합한다
apply     : 원장을 계획서에 반영하고(결과·보강·신규 행) 개정이력을 남긴다
"""
```

2) `load_plan`에서 시트 순번을 함께 반환한다.

```python
def load_plan(path: Path) -> dict:
    wb = Workbook(Path(path))
    try:
        sheet, part, cols, body = _find_table(wb, REQUIRED)
        index = [name for name, _ in wb.sheets].index(sheet)
    finally:
        wb.close()  # Windows에서 핸들이 남으면 임시 폴더 정리·덮어쓰기가 실패한다
    ...  # 본문 동일
    return {"sheet": sheet, "part": part, "index": index, "cols": cols, "rows": rows, "sha": file_sha(Path(path))}
```

3) 지운다: `FLOOR_HEADER`, `_undecided`, `build_floor`, `write_floor`, `iter_test_files`, `_id_pattern`, `check_floor`, `cmd_check`, `cmd_scope`와 parser의 `scope`·`check`.

4) 추가한다 (테스트 소스 검사 절, `_is_skipped` 아래).

```python
def _is_test_file(rel: str) -> bool:
    p = Path(rel)
    if p.suffix.lower() not in SOURCE_EXT or any(part in SKIP_DIRS for part in p.parts[:-1]):
        return False
    return any(part in TEST_DIRS for part in p.parts[:-1]) or bool(TEST_FILE_RE.search(p.name))


def _load_source(path: Path) -> tuple[list[str], bool]:
    text = Path(path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    suffix = Path(path).suffix.lower()
    lines = _strip_comments(text, hash_comments=suffix in {".py", ".rb"})  # 주석 속 선언·표식은 테스트가 아니다
    return lines, suffix == ".py" and any(PY_MODULE_SKIP_RE.match(l) for l in lines)


def changed_files(diff_text: str) -> list[str]:
    """unified diff의 새 쪽 경로 (git `+++ b/x`, svn `+++ x\\t(working copy)`). 삭제 파일은 뺀다."""
    git = "diff --git " in diff_text
    out: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+++ "):
            continue
        path = line[4:].split("\t")[0].strip()
        if path == "/dev/null":
            continue
        if git and path.startswith("b/"):
            path = path[2:]
        if path not in out:
            out.append(path)
    return out


def list_tests(root: Path, files: list[str]) -> list[dict]:
    out = []
    for rel in files:
        path = Path(root) / rel
        if not _is_test_file(rel) or not path.is_file():
            continue
        lines, module_skip = _load_source(path)
        seen: set[tuple[int, int]] = set()
        for i, line in enumerate(lines):
            if not DECL_RE.search(line):
                continue
            start, anchor, end = _test_header(lines, i)
            if (start, end) in seen:
                continue
            seen.add((start, end))
            decl = " ".join(l.strip() for l in lines[start:end + 1] if l.strip())
            out.append({"path": rel, "line": anchor + 1, "decl": decl[:300],
                        "skipped": module_skip or _is_skipped(lines, i)})
    return out


def locate_test(root: Path, location: str) -> dict | None:
    """`경로:줄`이 테스트(머리 또는 본문)를 가리키면 skip 여부를, 아니면 None을 돌려준다."""
    rel, _, num = location.strip().rpartition(":")
    path = Path(root) / rel
    if not rel or not num.isdigit() or not _is_test_file(rel) or not path.is_file():
        return None
    lines, module_skip = _load_source(path)
    i = int(num) - 1
    if not 0 <= i < len(lines):
        return None
    start, _, end = _test_header(lines, i)
    if not any(DECL_RE.search(l) for l in lines[start:end + 1]):
        return None
    return {"path": rel, "line": i + 1, "skipped": module_skip or _is_skipped(lines, i)}
```

5) 추가한다 (계획서 읽기 절, `row_fingerprint` 아래).

```python
ROWS_HEADER = ["테스트ID", "연계기능ID", *FIELDS4, "결과", "행 지문"]


def plan_rows(plan: dict, fn_ids: list[str]) -> list[dict]:
    known = {r["연계기능ID"] for r in plan["rows"] if r["연계기능ID"]}
    unknown = [f for f in fn_ids if f not in known]
    if unknown:
        raise InputError(f"계획서에 없는 기능ID: {', '.join(unknown)}")
    return [{"테스트ID": r["테스트ID"], "연계기능ID": r["연계기능ID"], **{f: r.get(f, "") for f in FIELDS4},
             "결과": r.get("결과", ""), "행 지문": row_fingerprint(r)}
            for r in plan["rows"] if r["연계기능ID"] in fn_ids]
```

6) 명령과 parser (기존 `cmd_scope` 자리).

```python
def _write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_tests(args) -> int:
    diff = Path(args.diff)
    if not diff.is_file():
        raise InputError(f"diff 파일이 없습니다: {diff}")
    tests = list_tests(Path(args.root), changed_files(diff.read_text(encoding="utf-8", errors="replace")))
    _write_json(Path(args.out), tests)
    print(f"테스트 {len(tests)}개 (skip {sum(t['skipped'] for t in tests)})")
    return 0


def cmd_functions(args) -> int:
    functions = function_list(load_plan(Path(args.plan)), Path(args.spec) if args.spec else None)
    _write_json(Path(args.out), functions)
    print(f"기능 {len(functions)}개")
    return 0


def cmd_rows(args) -> int:
    fn_ids = [f.strip() for f in args.fn.split(",") if f.strip()]
    rows = plan_rows(load_plan(Path(args.plan)), fn_ids)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(write_md_table(ROWS_HEADER, rows), encoding="utf-8")
    print(f"UT {len(rows)}행")
    return 0
```

`build_parser`의 `scope`·`check` 대신:

```python
    t = sub.add_parser("tests")
    t.add_argument("--diff", required=True)
    t.add_argument("--root", required=True)
    t.add_argument("--out", required=True)
    t.set_defaults(func=cmd_tests)
    f = sub.add_parser("functions")
    f.add_argument("--plan", required=True)
    f.add_argument("--spec")
    f.add_argument("--out", required=True)
    f.set_defaults(func=cmd_functions)
    w = sub.add_parser("rows")
    w.add_argument("--plan", required=True)
    w.add_argument("--fn", required=True)
    w.add_argument("--out", required=True)
    w.set_defaults(func=cmd_rows)
```

`record`·`apply`(구)와 그 parser는 이 Task에서 그대로 둔다 (Task 3·4가 바꾼다). 구 `record`가 쓰는 `_ledger_path`·`_read_ledger`·`_write_ledger`·`VERDICT_RE`도 그대로 둔다.

- [ ] **Step 7: 테스트 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py"`
Expected: OK (read·tests·skip·구 record·구 apply 모두)

- [ ] **Step 8: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `계획서 역보강용 테스트 목록·기능 목록·UT 행 명령을 추가한다`.

---

### Task 3: 짝짓기 초안 검증과 원장 병합 (`record`)

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py`
- Rewrite: `tests/test_de13_record.py`

**Interfaces:**
- Consumes: `load_plan`, `row_fingerprint`, `locate_test`, `read_md_table`, `write_md_table`, `FIELDS4`
- Produces:
  - `LEDGER_HEADER = ["구분", "테스트ID", "연계기능ID", "사전조건", "입력", "기대결과", "사후조건", "결과", "수행일", "담당자", "테스트 위치", "행 지문", "근거", "반영"]`
  - `DRAFT_HEADER = ["구분", "테스트ID", "연계기능ID", "사전조건", "입력", "기대결과", "사후조건", "테스트 위치", "근거"]`
  - `UNASSIGNED = "미지정"`
  - `_write_ledger(path: Path, rows: list[dict]) -> None` (제목 `# {파일 stem} 단위테스트 원장`)
  - `record(draft_rows: list[dict], plan: dict, root: Path, ledger_path: Path, date: str, tester: str) -> dict` — `{"기존": int, "보강": int, "신규": int, "미지정": int}`
  - CLI `record --draft --plan --root --ledger --date --tester` (0/2), 출력 `원장 {파일명}: 기존 N(보강 M) · 신규 K[ · 기능 미지정 U]`

- [ ] **Step 1: 실패하는 테스트 작성 — `tests/test_de13_record.py` 전체 교체**

```python
"""de13.py record: 짝짓기 초안 검증과 원장 병합."""
import tempfile
import unittest
from pathlib import Path

from de13_support import PLAN_HEADER_11, load_de13, make_xlsx, sample_rows

de13 = load_de13()

JAVA = """package a;
class MemoTest {
    @Test
    void 파일_용량_초과면_차단() {}
    @Disabled
    @Test
    void 보류() {}
    @Test
    void 빈_메모면_거부() {}
}
"""
TEST = "src/test/java/a/MemoTest.java"


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 record 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / TEST).parent.mkdir(parents=True)
        (self.root / TEST).write_text(JAVA, encoding="utf-8")
        self.plan = de13.load_plan(make_xlsx(self.root / "REB-단위테스트계획서.xlsx",
                                             [("단위테스트계획", [PLAN_HEADER_11, *sample_rows()])]))
        self.fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in self.plan["rows"]}
        self.ledger = self.root / ".dev" / "ut-results" / "feat-memo.md"

    def existing(self, tid="UT-002", loc=f"{TEST}:4", expected=""):
        return {"구분": "기존", "테스트ID": tid, "연계기능ID": "", "사전조건": "", "입력": "",
                "기대결과": expected, "사후조건": "", "테스트 위치": loc, "근거": "용량 초과 차단을 단언"}

    def new(self, fn="FN-002", loc=f"{TEST}:9", inp="빈 메모 저장", exp="\"메모를 입력하세요\" 안내, 저장 차단"):
        return {"구분": "신규", "테스트ID": "", "연계기능ID": fn, "사전조건": "회차 1건", "입력": inp,
                "기대결과": exp, "사후조건": "변화 없음", "테스트 위치": loc, "근거": "계획서에 빈 메모 케이스 없음"}

    def run_record(self, rows):
        return de13.record(rows, self.plan, self.root, self.ledger, "2026.10.13", "bs.koo")

    def test_existing_and_new_rows_are_written_with_pass_and_fingerprint(self):
        summary = self.run_record([self.existing(expected="\"파일 용량 초과(최대 1,000MB)\" 안내"), self.new()])
        self.assertEqual(summary, {"기존": 1, "보강": 1, "신규": 1, "미지정": 0})
        rows = de13.read_md_table(self.ledger)
        self.assertEqual(list(rows[0]), de13.LEDGER_HEADER)
        old, new = rows
        self.assertEqual((old["구분"], old["테스트ID"], old["연계기능ID"], old["행 지문"]),
                         ("기존", "UT-002", "FN-001", self.fp["UT-002"]))
        self.assertEqual((old["결과"], old["수행일"], old["담당자"], old["반영"]), ("Pass", "2026.10.13", "bs.koo", ""))
        self.assertEqual((new["테스트ID"], new["연계기능ID"], new["입력"]), ("", "FN-002", "빈 메모 저장"))
        self.assertTrue(self.ledger.read_text(encoding="utf-8").startswith("# feat-memo 단위테스트 원장"))

    def test_location_must_point_to_live_test(self):
        bad = [self.existing(loc=f"{TEST}:7"), self.existing(tid="UT-003", loc=f"{TEST}:1"),
               self.new(loc="src/test/java/a/None.java:3"), self.new(loc="")]
        with self.assertRaises(de13.InputError) as ctx:
            self.run_record(bad)
        msg = str(ctx.exception)
        for part in (f"{TEST}:7(skip)", f"{TEST}:1(테스트 아님)", "None.java:3(테스트 아님)", "테스트 위치 없음"):
            self.assertIn(part, msg)
        self.assertFalse(self.ledger.exists())

    def test_existing_id_must_be_in_plan_and_unique(self):
        with self.assertRaisesRegex(de13.InputError, "계획서에 없는 테스트ID"):
            self.run_record([self.existing(tid="UT-999")])
        with self.assertRaisesRegex(de13.InputError, "중복"):
            self.run_record([self.existing(), self.existing(loc=f"{TEST}:9")])

    def test_new_row_needs_input_expected_and_known_function(self):
        with self.assertRaisesRegex(de13.InputError, "입력·기대결과"):
            self.run_record([self.new(exp="")])
        with self.assertRaisesRegex(de13.InputError, "계획서에 없는 연계기능ID FN-404"):
            self.run_record([self.new(fn="FN-404")])
        self.assertEqual(self.run_record([self.new(fn="")])["미지정"], 1)
        self.assertEqual(de13.read_md_table(self.ledger)[0]["연계기능ID"], de13.UNASSIGNED)

    def test_unknown_kind_is_rejected(self):
        with self.assertRaisesRegex(de13.InputError, "구분은 기존/신규"):
            self.run_record([dict(self.new(), 구분="추가")])

    def test_merge_keeps_applied_rows_and_replaces_pending(self):
        self.run_record([self.existing(), self.new()])
        rows = de13.read_md_table(self.ledger)
        rows[0]["반영"] = "v1.1"
        de13._write_ledger(self.ledger, rows)
        self.run_record([self.new(inp="공백 메모 저장")])
        after = de13.read_md_table(self.ledger)
        self.assertEqual([(r["구분"], r["입력"], r["반영"]) for r in after],
                         [("기존", "", "v1.1"), ("신규", "공백 메모 저장", "")])

    def test_cli_exit_codes_and_summary_line(self):
        draft = self.root / ".dev" / "feat-memo" / "ut-draft.md"
        draft.parent.mkdir(parents=True)
        draft.write_text(de13.write_md_table(de13.DRAFT_HEADER, [self.existing(), self.new()]), encoding="utf-8")
        args = ["record", "--draft", str(draft), "--plan", str(self.root / "REB-단위테스트계획서.xlsx"),
                "--root", str(self.root), "--ledger", str(self.ledger), "--date", "2026.10.13", "--tester", "bs.koo"]
        self.assertEqual(de13.main(args), 0)
        self.assertEqual(len(de13.read_md_table(self.ledger)), 2)
        draft.write_text(de13.write_md_table(de13.DRAFT_HEADER, [self.existing(tid="UT-999")]), encoding="utf-8")
        self.assertEqual(de13.main(args), 2)
        self.assertEqual(de13.main(args[:2] + [str(self.root / "none.md")] + args[3:]), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_record.py"`
Expected: FAIL — `DRAFT_HEADER`·`UNASSIGNED` 없음, `record` 인자 불일치

- [ ] **Step 3: 구현**

`# ---------- 결과 원장 ----------` 절 전체(`VERDICT_RE`부터 `cmd_record`까지)를 아래로 바꾸고, 파일 머리의 구 `LEDGER_HEADER` 정의를 지운다.

```python
# ---------- 결과 원장 ----------

LEDGER_HEADER = ["구분", "테스트ID", "연계기능ID", *FIELDS4, "결과", "수행일", "담당자",
                 "테스트 위치", "행 지문", "근거", "반영"]
DRAFT_HEADER = ["구분", "테스트ID", "연계기능ID", *FIELDS4, "테스트 위치", "근거"]
UNASSIGNED = "미지정"


def _write_ledger(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {path.stem} 단위테스트 원장\n\n" + write_md_table(LEDGER_HEADER, rows), encoding="utf-8")


def _check_locations(root: Path, raw: str) -> tuple[list[str], list[str]]:
    locs = [s.strip() for s in (raw or "").split(",") if s.strip()]
    bad = []
    for loc in locs:
        hit = locate_test(root, loc)
        if hit is None:
            bad.append(f"{loc}(테스트 아님)")
        elif hit["skipped"]:
            bad.append(f"{loc}(skip)")
    return locs, bad


def record(draft_rows: list[dict], plan: dict, root: Path, ledger_path: Path, date: str, tester: str) -> dict:
    """초안을 검증해 원장에 병합한다. 반영(`반영` 값 있음)된 행은 보존하고 나머지는 이번 초안으로 바꾼다."""
    by_id = {r["테스트ID"]: r for r in plan["rows"]}
    functions = {r["연계기능ID"] for r in plan["rows"] if r["연계기능ID"]}
    errors, rows, seen = [], [], set()
    for n, d in enumerate(draft_rows, start=1):
        kind = d.get("구분", "")
        where = f"{n}행({d.get('테스트ID') or kind or '?'})"
        locs, bad = _check_locations(Path(root), d.get("테스트 위치", ""))
        if not locs:
            errors.append(f"{where}: 테스트 위치 없음")
            continue
        if bad:
            errors.append(f"{where}: " + ", ".join(bad))
            continue
        row = {h: "" for h in LEDGER_HEADER}
        row.update({"구분": kind, "결과": "Pass", "수행일": date, "담당자": tester,
                    "테스트 위치": ", ".join(locs), "근거": d.get("근거", "")})
        if kind == "기존":
            rec = by_id.get(d.get("테스트ID", ""))
            if rec is None:
                errors.append(f"{where}: 계획서에 없는 테스트ID")
                continue
            if rec["테스트ID"] in seen:
                errors.append(f"{where}: 같은 테스트ID 중복 — 한 행으로 묶으세요")
                continue
            seen.add(rec["테스트ID"])
            row.update({"테스트ID": rec["테스트ID"], "연계기능ID": rec["연계기능ID"],
                        "기대결과": d.get("기대결과", ""), "행 지문": row_fingerprint(rec)})
        elif kind == "신규":
            fn = d.get("연계기능ID", "") or UNASSIGNED
            if fn != UNASSIGNED and fn not in functions:
                errors.append(f"{where}: 계획서에 없는 연계기능ID {fn}")
                continue
            if not d.get("입력") or not d.get("기대결과"):
                errors.append(f"{where}: 신규 행은 입력·기대결과가 필요합니다")
                continue
            row.update({"연계기능ID": fn, **{f: d.get(f, "") for f in FIELDS4}})
        else:
            errors.append(f"{where}: 구분은 기존/신규")
            continue
        rows.append(row)
    if errors:
        raise InputError("초안 오류 — " + "; ".join(errors))
    ledger_path = Path(ledger_path)
    kept = [r for r in read_md_table(ledger_path) if r.get("반영")] if ledger_path.is_file() else []
    _write_ledger(ledger_path, kept + rows)
    old = [r for r in rows if r["구분"] == "기존"]
    new = [r for r in rows if r["구분"] == "신규"]
    return {"기존": len(old), "보강": sum(1 for r in old if r["기대결과"]), "신규": len(new),
            "미지정": sum(1 for r in new if r["연계기능ID"] == UNASSIGNED)}


def cmd_record(args) -> int:
    draft = Path(args.draft)
    if not draft.is_file():
        raise InputError(f"초안 파일이 없습니다: {draft}")
    s = record(read_md_table(draft), load_plan(Path(args.plan)), Path(args.root), Path(args.ledger),
               args.date, args.tester)
    tail = f" · 기능 미지정 {s['미지정']}" if s["미지정"] else ""
    print(f"원장 {Path(args.ledger).name}: 기존 {s['기존']}(보강 {s['보강']}) · 신규 {s['신규']}{tail}")
    return 0
```

parser의 `record`를 바꾼다.

```python
    r = sub.add_parser("record")
    r.add_argument("--draft", required=True)
    r.add_argument("--plan", required=True)
    r.add_argument("--root", required=True)
    r.add_argument("--ledger", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--tester", required=True)
    r.set_defaults(func=cmd_record)
```

구 `apply`가 쓰던 `_ledger_rows`·구 `LEDGER_HEADER` 의존은 Task 4가 바꾼다. 이 Task가 끝나면 구 `tests/test_de13_apply.py`는 새 원장 형식과 맞지 않아 실패한다 — Task 4 Step 1에서 바로 교체하므로 이 Task의 검증은 record 테스트로 한정한다.

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_record.py" -v`
Expected: 7 tests OK
Run: `python -m unittest discover -s tests -p "test_de13_*.py"`
Expected: `test_de13_apply` 실패만 남음 (Task 4에서 교체). 원장에 `Task 3: Ruling`으로 기록.

- [ ] **Step 5: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `짝짓기 초안을 검증해 단위테스트 원장에 병합하는 record를 바꾼다`.

---

### Task 4: 계획서 제자리 반영 — 기존 행 패치·신규 행 추가·범위 확장 (`apply`)

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py`
- Rewrite: `tests/test_de13_apply.py`

**Interfaces:**
- Consumes: `load_plan`(`index` 포함), `row_fingerprint`, `read_md_table`, `_write_ledger`, `LEDGER_HEADER`, `UNASSIGNED`, `_patch_sheet`, `_cell_xml`, `_CELL_RE`, `_col_index`, `_col_letters`, `read_testers`
- Produces:
  - `apply(plan_path: Path, ledger_dir: Path, testers: dict[str, str], author: str, date: str, version: str | None = None) -> dict` — 키 `계획서, 버전, 결과 기입, 보강, 신규(list), 재확인 필요, 계획서에 없음, 기능 미지정, 개정이력, 매핑 없는 담당자`
  - `_append_rows(xml, rows: list[tuple[int, dict[int, str]]], style_rnum: int) -> str`
  - `_extend_sheet_ranges(xml, old: int, new: int) -> str`, `_extend_defined_names(workbook_xml, index: int, old: int, new: int) -> str`
  - `_replace_xlsx(path: Path, parts: dict[str, bytes]) -> None`
  - 이 Task의 `apply`는 개정이력을 쓰지 않는다(`개정이력: "개정이력 시트 없음"`, 반영 표시는 날짜). Task 5가 추가한다.

- [ ] **Step 1: 실패하는 테스트 작성 — `tests/test_de13_apply.py` 전체 교체**

```python
"""de13.py apply: 원장을 계획서에 제자리 반영."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from de13_support import PLAN_HEADER_11, load_de13, make_xlsx, sample_rows

de13 = load_de13()
TESTERS = {"bs.koo": "구본승", "lee": "이개발"}


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 apply 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.plan_path = make_xlsx(self.dir / "REB-단위테스트계획서.xlsx",
                                   [("단위테스트계획", [PLAN_HEADER_11, *sample_rows()]), ("보강 내역", [["기능ID"]])],
                                   validation="K2:K9", style="3", filters={"단위테스트계획": "A1"})
        self.fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in de13.load_plan(self.plan_path)["rows"]}
        self.ledger_dir = self.dir / ".dev" / "ut-results"

    def ledger(self, name, rows):
        de13._write_ledger(self.ledger_dir / f"{name}.md", rows)

    def existing(self, tid, expected="", tester="bs.koo", date="2026.10.13", fp=None):
        return {"구분": "기존", "테스트ID": tid, "연계기능ID": "FN-001", "기대결과": expected, "결과": "Pass",
                "수행일": date, "담당자": tester, "테스트 위치": "src/test/A.java:3",
                "행 지문": fp or self.fp[tid], "근거": "x", "반영": ""}

    def new(self, fn="FN-001", inp="빈 메모", tester="bs.koo"):
        return {"구분": "신규", "테스트ID": "", "연계기능ID": fn, "사전조건": "회차 1건", "입력": inp,
                "기대결과": "\"메모를 입력하세요\" 안내", "사후조건": "저장 없음", "결과": "Pass",
                "수행일": "2026.10.13", "담당자": tester, "테스트 위치": "src/test/A.java:9",
                "행 지문": "", "근거": "x", "반영": ""}

    def run_apply(self, testers=TESTERS):
        return de13.apply(self.plan_path, self.ledger_dir, testers, "구본승", "2026.10.13")

    def rows(self):
        return {r["테스트ID"]: r for r in de13.load_plan(self.plan_path)["rows"]}

    def part(self, name):
        with zipfile.ZipFile(self.plan_path) as z:
            return z.read(name).decode("utf-8")

    def test_existing_rows_get_result_and_refined_expected(self):
        before = zipfile.ZipFile(self.plan_path)
        originals = {n: before.read(n) for n in before.namelist()}
        before.close()
        self.ledger("feat-a", [self.existing("UT-001", expected="회차 1건 생성, 상태 '등록완료'"), self.existing("UT-002")])
        summary = self.run_apply()
        self.assertEqual((summary["결과 기입"], summary["보강"], summary["신규"]), (2, 1, []))
        rows = self.rows()
        self.assertEqual((rows["UT-001"]["결과"], rows["UT-001"]["수행일"], rows["UT-001"]["테스트담당자"]),
                         ("Pass", "2026.10.13", "구본승"))
        self.assertEqual(rows["UT-001"]["기대결과"], "회차 1건 생성, 상태 '등록완료'")
        self.assertEqual(rows["UT-002"]["기대결과"], "\"파일 용량 초과\" 안내")
        self.assertEqual(rows["UT-003"]["결과"], "")
        with zipfile.ZipFile(self.plan_path) as z:
            for name in z.namelist():
                if name not in ("xl/worksheets/sheet1.xml", "xl/workbook.xml"):
                    self.assertEqual(z.read(name), originals[name], name)
        self.assertIn('<c r="K2" s="3" t="inlineStr"><is><t>Pass</t></is></c>', self.part("xl/worksheets/sheet1.xml"))
        self.assertEqual([r["반영"] for r in de13.read_md_table(self.ledger_dir / "feat-a.md")],
                         ["2026.10.13", "2026.10.13"])

    def test_new_rows_are_numbered_copy_sibling_columns_and_extend_ranges(self):
        self.ledger("feat-a", [self.new(), self.new(fn="FN-002", inp="메모 2,001자")])
        summary = self.run_apply()
        self.assertEqual(summary["신규"], ["UT-009", "UT-010"])
        rows = self.rows()
        a, b = rows["UT-009"], rows["UT-010"]
        self.assertEqual((a["_row"], a["연계기능ID"], a["연계요구사항ID"], a["의존성"], a["결과"], a["테스트담당자"]),
                         (10, "FN-001", "RE-001", "없음", "Pass", "구본승"))
        self.assertEqual((b["_row"], b["연계요구사항ID"], b["입력"]), (11, "RE-002", "메모 2,001자"))
        sheet = self.part("xl/worksheets/sheet1.xml")
        self.assertIn('<c r="A10" s="3" t="inlineStr"><is><t>UT-009</t></is></c>', sheet)
        self.assertIn('<dimension ref="A1:K11"/>', sheet)
        self.assertIn('<autoFilter ref="A1:K11"/>', sheet)
        self.assertIn('sqref="K2:K11"', sheet)
        self.assertIn("!$A$1:$K$11</definedName>", self.part("xl/workbook.xml"))
        self.assertEqual([r["반영"] for r in de13.read_md_table(self.ledger_dir / "feat-a.md")],
                         ["2026.10.13 UT-009", "2026.10.13 UT-010"])

    def test_changed_or_unknown_rows_are_reported_and_left_pending(self):
        before = self.plan_path.read_bytes()
        self.ledger("feat-a", [self.existing("UT-001", fp="deadbeef"), dict(self.existing("UT-002"), 테스트ID="UT-999")])
        summary = self.run_apply()
        self.assertEqual((summary["재확인 필요"], summary["계획서에 없음"]), (["UT-001"], ["UT-999"]))
        self.assertEqual(self.plan_path.read_bytes(), before)
        self.assertEqual([r["반영"] for r in de13.read_md_table(self.ledger_dir / "feat-a.md")], ["", ""])

    def test_unassigned_or_unknown_function_is_not_added(self):
        before = self.plan_path.read_bytes()
        self.ledger("feat-a", [self.new(fn=de13.UNASSIGNED), self.new(fn="FN-404")])
        self.assertEqual(self.run_apply()["기능 미지정"], 2)
        self.assertEqual(self.plan_path.read_bytes(), before)

    def test_second_run_changes_nothing(self):
        self.ledger("feat-a", [self.existing("UT-001"), self.new()])
        self.run_apply()
        after_first = self.plan_path.read_bytes()
        summary = self.run_apply()
        self.assertEqual((summary["결과 기입"], summary["신규"]), (0, []))
        self.assertEqual(self.plan_path.read_bytes(), after_first)

    def test_latest_date_wins_and_refinement_kept_across_ledgers(self):
        self.ledger("feat-a", [self.existing("UT-001", expected="구체화 A", date="2026.10.12")])
        self.ledger("feat-b", [self.existing("UT-001", tester="lee", date="2026.10.13")])
        self.run_apply()
        row = self.rows()["UT-001"]
        self.assertEqual((row["수행일"], row["테스트담당자"], row["기대결과"]), ("2026.10.13", "이개발", "구체화 A"))
        self.assertEqual(de13.read_md_table(self.ledger_dir / "feat-a.md")[0]["반영"], "2026.10.13")

    def test_unknown_tester_writes_nothing(self):
        before = self.plan_path.read_bytes()
        self.ledger("feat-a", [self.existing("UT-001", tester="park")])
        self.assertEqual(self.run_apply()["매핑 없는 담당자"], ["park"])
        self.assertEqual(self.plan_path.read_bytes(), before)

    def test_excel_lock_leaves_plan_and_ledger_untouched(self):
        before = self.plan_path.read_bytes()
        self.ledger("feat-a", [self.existing("UT-001")])
        with mock.patch.object(de13.os, "replace", side_effect=PermissionError("locked")):
            with self.assertRaisesRegex(de13.InputError, "엑셀에서 닫고"):
                self.run_apply()
        self.assertEqual(self.plan_path.read_bytes(), before)
        self.assertEqual(list(self.dir.glob("*.gx-tmp")), [])
        self.assertEqual(de13.read_md_table(self.ledger_dir / "feat-a.md")[0]["반영"], "")

    def test_shared_strings_plan_with_missing_cells_gets_new_row(self):
        rows = [r[:8] for r in sample_rows()]  # 테스트담당자·수행일·결과 셀이 아예 없는 행
        self.plan_path = make_xlsx(self.dir / "shared.xlsx", [("단위테스트계획", [PLAN_HEADER_11, *rows])], shared=True)
        self.fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in de13.load_plan(self.plan_path)["rows"]}
        self.ledger("feat-a", [self.existing("UT-001"), self.new()])
        self.run_apply()
        rows = self.rows()
        self.assertEqual((rows["UT-001"]["결과"], rows["UT-009"]["입력"]), ("Pass", "빈 메모"))
        sheet = self.part("xl/worksheets/sheet1.xml")
        row2 = sheet[sheet.index('<row r="2"'):sheet.index("</row>", sheet.index('<row r="2"'))]
        self.assertLess(row2.index('r="H2"'), row2.index('r="I2"'))
        self.assertLess(row2.index('r="J2"'), row2.index('r="K2"'))

    def test_read_testers(self):
        self.ledger_dir.mkdir(parents=True)
        (self.ledger_dir / "testers.md").write_text("| git 이름 | 실명 |\n|---|---|\n| bs.koo | 구본승 |\n", encoding="utf-8")
        self.assertEqual(de13.read_testers(self.ledger_dir / "testers.md"), {"bs.koo": "구본승"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_apply.py"`
Expected: FAIL — `apply()` 인자 불일치 (`author`, `date`)

- [ ] **Step 3: 구현**

`# ---------- 사본 반영 ----------` 절의 `_ledger_rows`, 구 `apply`, `cmd_apply`를 지우고(`TESTERS_HEADER`, `read_testers`, `_cell_xml`, `_CELL_RE`, `_patch_row`, `_patch_sheet`는 유지) 절 제목을 `# ---------- 계획서 반영 ----------`으로 바꾼 뒤 아래를 추가한다. 파일 머리 import에 `os`가 이미 있다.

```python
ID_RE = re.compile(r"^(.*?)(\d+)$")
RANGE_RE = re.compile(r"(\$?[A-Z]+\$?)(\d+):(\$?[A-Z]+\$?)(\d+)")
_ROW_NUM_RE = re.compile(r'<row\b[^>]*\br="(\d+)"')


def _ledger_files(ledger_dir: Path) -> list[Path]:
    return [p for p in sorted(Path(ledger_dir).glob("*.md")) if p.name != "testers.md"]


def _id_scheme(rows: list[dict]) -> tuple[str, int, int]:
    found: dict[str, list[str]] = {}
    for r in rows:
        m = ID_RE.match(r["테스트ID"])
        if m:
            found.setdefault(m.group(1), []).append(m.group(2))
    if not found:
        raise InputError("테스트ID 번호 규칙을 찾을 수 없습니다")
    prefix = max(found, key=lambda k: len(found[k]))
    return prefix, max(len(n) for n in found[prefix]), max(int(n) for n in found[prefix])


def _sheet_max_row(xml: str) -> int:
    return max((int(n) for n in _ROW_NUM_RE.findall(xml)), default=0)


def _row_styles(xml: str, rnum: int) -> dict[int, str]:
    m = re.search(rf'<row\b[^>]*\br="{rnum}"[^>]*?(?:/>|>.*?</row>)', xml, re.S)
    styles: dict[int, str] = {}
    for c in _CELL_RE.finditer(m.group(0) if m else ""):
        ref = re.search(r'\br="([A-Z]+)\d+"', c.group("attrs"))
        style = re.search(r'\bs="(\d+)"', c.group("attrs"))
        if ref and style:
            styles[_col_index(ref.group(1))] = style.group(1)
    return styles


def _append_rows(xml: str, rows: list[tuple[int, dict[int, str]]], style_rnum: int) -> str:
    """시트 끝에 행을 붙인다. 셀 서식은 style_rnum 행의 같은 열을 따른다."""
    if "</sheetData>" not in xml:
        raise InputError("시트에 행을 추가할 수 없습니다 (sheetData 없음)")
    styles = _row_styles(xml, style_rnum)
    out = []
    for rnum, values in rows:
        cols = sorted(set(values) | set(styles))
        cells = "".join(_cell_xml(f"{_col_letters(c)}{rnum}", values.get(c, ""), styles.get(c)) for c in cols)
        out.append(f'<row r="{rnum}">{cells}</row>')
    return xml.replace("</sheetData>", "".join(out) + "</sheetData>", 1)


def _extend_range_text(text: str, old: int, new: int) -> str:
    return RANGE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}:{m.group(3)}{new}" if int(m.group(4)) == old
                        else m.group(0), text)


def _extend_sheet_ranges(xml: str, old: int, new: int) -> str:
    """마지막 행(old)에서 끝나는 dimension·autoFilter·데이터 검증·조건부 서식 범위를 new까지 늘린다."""
    return re.sub(r'(<(?:dimension|autoFilter|dataValidation|conditionalFormatting)\b[^>]*?\b(?:ref|sqref)=")([^"]*)(")',
                  lambda m: m.group(1) + _extend_range_text(m.group(2), old, new) + m.group(3), xml)


def _extend_defined_names(xml: str, index: int, old: int, new: int) -> str:
    return re.sub(rf'(<definedName\b[^>]*\blocalSheetId="{index}"[^>]*>)([^<]*)(</definedName>)',
                  lambda m: m.group(1) + _extend_range_text(m.group(2), old, new) + m.group(3), xml)


def _replace_xlsx(path: Path, parts: dict[str, bytes]) -> None:
    """같은 폴더 임시 파일에 쓰고 다시 읽어 확인한 뒤 원본과 바꾼다. 실패하면 원본은 그대로다."""
    path = Path(path)
    tmp = path.with_name(path.name + ".gx-tmp")
    try:
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w") as dst:
            for info in src.infolist():
                dst.writestr(info, parts[info.filename] if info.filename in parts else src.read(info))
        load_plan(tmp)
        os.replace(tmp, path)
    except PermissionError as exc:
        raise InputError(f"계획서를 바꿀 수 없습니다 — 엑셀에서 닫고 다시 실행하세요 ({exc})") from exc
    finally:
        if tmp.exists():
            tmp.unlink()


def apply(plan_path: Path, ledger_dir: Path, testers: dict[str, str], author: str, date: str,
          version: str | None = None) -> dict:
    plan_path = Path(plan_path)
    plan = load_plan(plan_path)
    by_id = {r["테스트ID"]: r for r in plan["rows"]}
    cols = plan["cols"]
    tables = {p: read_md_table(p) for p in _ledger_files(Path(ledger_dir))}
    pending = [(p, i, r) for p, rows in tables.items() for i, r in enumerate(rows)
               if not r.get("반영") and r.get("구분") in ("기존", "신규")]
    summary = {"계획서": plan_path.as_posix(), "버전": "", "결과 기입": 0, "보강": 0, "신규": [],
               "재확인 필요": [], "계획서에 없음": [], "기능 미지정": 0, "개정이력": "",
               "매핑 없는 담당자": sorted({r.get("담당자", "") for _, _, r in pending} - set(testers))}
    if summary["매핑 없는 담당자"]:
        return summary
    groups: dict[str, list[tuple[Path, int, dict]]] = {}
    for p, i, r in pending:
        if r["구분"] != "기존":
            continue
        rec = by_id.get(r.get("테스트ID", ""))
        if rec is None:
            summary["계획서에 없음"].append(r.get("테스트ID", ""))
        elif r.get("행 지문") != row_fingerprint(rec):
            summary["재확인 필요"].append(rec["테스트ID"])  # PM이 그 사이 행을 고쳤다
        else:
            groups.setdefault(rec["테스트ID"], []).append((p, i, r))
    updates: dict[int, dict[int, str]] = {}
    marks: dict[tuple[Path, int], str] = {}
    for tid, items in groups.items():
        items.sort(key=lambda it: it[2].get("수행일", ""))
        last = items[-1][2]
        values = {cols["결과"]: "Pass", cols["수행일"]: last.get("수행일", ""),
                  cols["테스트담당자"]: testers[last["담당자"]]}
        refined = next((it[2]["기대결과"] for it in reversed(items) if it[2].get("기대결과")), "")
        if refined:
            values[cols["기대결과"]] = refined
            summary["보강"] += 1
        updates[by_id[tid]["_row"]] = values
        summary["결과 기입"] += 1
        marks.update({(p, i): "" for p, i, _ in items})
    prefix, width, last_no = _id_scheme(plan["rows"])
    appended: list[dict[int, str]] = []
    for p, i, r in pending:
        if r["구분"] != "신규":
            continue
        siblings = [x for x in plan["rows"] if x["연계기능ID"] == r.get("연계기능ID")]
        if r.get("연계기능ID") == UNASSIGNED or not siblings:
            summary["기능 미지정"] += 1
            continue
        last_no += 1
        tid = f"{prefix}{last_no:0{width}d}"
        values = {c: siblings[-1].get(h, "") for h, c in cols.items()}  # 연계요구사항ID 등은 같은 기능 행을 따른다
        values.update({cols[f]: r.get(f, "") for f in FIELDS4})
        values.update({cols["테스트ID"]: tid, cols["연계기능ID"]: r["연계기능ID"], cols["의존성"]: "없음",
                       cols["결과"]: "Pass", cols["수행일"]: r.get("수행일", ""),
                       cols["테스트담당자"]: testers[r["담당자"]]})
        appended.append(values)
        summary["신규"].append(tid)
        marks[(p, i)] = tid
    if not updates and not appended:
        return summary
    with zipfile.ZipFile(plan_path) as z:
        sheet = z.read(plan["part"]).decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
    if appended and "<tablePart" in sheet:
        raise InputError("엑셀 표(Table) 서식이 있는 계획서에는 행을 추가할 수 없습니다")
    sheet = _patch_sheet(sheet, updates)
    if appended:
        old = _sheet_max_row(sheet)
        style_row = max(r["_row"] for r in plan["rows"])
        sheet = _append_rows(sheet, [(old + n, v) for n, v in enumerate(appended, start=1)], style_row)
        sheet = _extend_sheet_ranges(sheet, old, old + len(appended))
        workbook = _extend_defined_names(workbook, plan["index"], old, old + len(appended))
    parts = {plan["part"]: sheet.encode("utf-8")}
    summary["개정이력"] = "개정이력 시트 없음"
    parts["xl/workbook.xml"] = workbook.encode("utf-8")
    _replace_xlsx(plan_path, parts)
    tag = f"v{summary['버전']}" if summary["버전"] else date
    for (p, i), tid in marks.items():
        tables[p][i]["반영"] = f"{tag} {tid}".strip()
    for p in {p for p, _ in marks}:
        _write_ledger(p, tables[p])
    return summary


def cmd_apply(args) -> int:
    summary = apply(Path(args.plan), Path(args.ledger_dir), read_testers(Path(args.testers)),
                    args.author, args.date, args.version)
    _write_json(Path(args.report), summary)
    if summary["매핑 없는 담당자"]:
        print("매핑 없는 담당자: " + ", ".join(summary["매핑 없는 담당자"]))
        return 3
    if not summary["결과 기입"] and not summary["신규"]:
        print("반영할 원장 항목이 없습니다")
        return 0
    head = f"계획서 v{summary['버전']}" if summary["버전"] else "계획서"
    print(f"{head} 반영: 결과 {summary['결과 기입']} · 보강 {summary['보강']} · 신규 {len(summary['신규'])}")
    return 0
```

parser의 `apply`를 바꾼다.

```python
    a = sub.add_parser("apply")
    a.add_argument("--plan", required=True)
    a.add_argument("--ledger-dir", required=True)
    a.add_argument("--testers", required=True)
    a.add_argument("--author", required=True)
    a.add_argument("--date", default=_dt.date.today().strftime("%Y.%m.%d"))
    a.add_argument("--version")
    a.add_argument("--report", required=True)
    a.set_defaults(func=cmd_apply)
```

`version` 인자는 이 Task에서 쓰지 않는다(Task 5에서 연결). `_write_json`은 Task 2에서 만들었다.

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v`
Expected: 전부 OK (apply 10건 포함)

- [ ] **Step 5: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `원장을 계획서에 제자리 반영하고 신규 케이스를 이어 붙인다`.

---

### Task 5: 개정이력 기입과 버전

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py`
- Create: `tests/test_de13_revision.py`

**Interfaces:**
- Consumes: Task 4의 `apply`, `_append_rows`, `_extend_sheet_ranges`, `_extend_defined_names`, `_sheet_max_row`, `_find_table`, `Workbook`
- Produces:
  - `REVISION_HEAD = ("버전", "개정일", "개정 사유", "개정 내용", "작성자")`, `REVISION_REASON = "개발 반영(gx-tdd)"`
  - `next_version(last: str) -> str`
  - `load_revision(path: Path) -> dict | None` — `{"sheet","part","index","cols","last_rnum","last_version"}`
  - `revision_text(new_ids: list[str], refined: int, passed: int) -> str`
  - `apply`가 개정이력 행을 추가하고 `summary["버전"]`·`summary["개정이력"]`을 채우며, 원장 반영 표시를 `v{버전}`으로 남긴다.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
"""de13.py apply: 개정이력과 CLI."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from de13_support import PLAN_HEADER_11, load_de13, make_xlsx, sample_rows

de13 = load_de13()
REV_HEADER = ["버전", "개정일", "개정 사유", "개정 내용", "작성자", "승인자"]


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 revision 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.ledger_dir = self.dir / ".dev" / "ut-results"

    def plan(self, last_version="1.0"):
        self.plan_path = make_xlsx(
            self.dir / "REB-단위테스트계획서.xlsx",
            [("개정이력", [["개 정 이 력"], REV_HEADER, [last_version, "2026.09.09", "신규", "최초 작성", "구본승", ""]]),
             ("단위테스트계획", [PLAN_HEADER_11, *sample_rows()])],
            validation="K2:K9", style="3", filters={"개정이력": "A2", "단위테스트계획": "A1"})
        fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in de13.load_plan(self.plan_path)["rows"]}
        de13._write_ledger(self.ledger_dir / "feat-a.md", [
            {"구분": "기존", "테스트ID": "UT-001", "연계기능ID": "FN-001", "기대결과": "구체화", "결과": "Pass",
             "수행일": "2026.10.13", "담당자": "bs.koo", "테스트 위치": "a:1", "행 지문": fp["UT-001"], "근거": "", "반영": ""},
            {"구분": "신규", "테스트ID": "", "연계기능ID": "FN-001", "사전조건": "", "입력": "빈 메모", "기대결과": "거부",
             "사후조건": "", "결과": "Pass", "수행일": "2026.10.13", "담당자": "bs.koo", "테스트 위치": "a:2",
             "행 지문": "", "근거": "", "반영": ""}])
        return self.plan_path

    def revisions(self):
        wb = de13.Workbook(self.plan_path)
        try:
            _, _, cols, body = de13._find_table(wb, de13.REVISION_HEAD)
        finally:
            wb.close()
        return [(rnum, {h: cells.get(c, "") for h, c in cols.items()}) for rnum, cells in body]

    def test_next_version(self):
        self.assertEqual(de13.next_version("1.0"), "1.1")
        self.assertEqual(de13.next_version("1.9"), "1.10")
        with self.assertRaisesRegex(de13.InputError, "--version"):
            de13.next_version("초안")

    def test_revision_text(self):
        self.assertEqual(de13.revision_text(["UT-009"], 1, 2), "단위테스트 신규 1건 추가(UT-009)·기대결과 보강 1건·결과 기입 Pass 2건")
        self.assertEqual(de13.revision_text(["UT-009", "UT-010"], 0, 2), "단위테스트 신규 2건 추가(UT-009~UT-010)·결과 기입 Pass 2건")
        self.assertEqual(de13.revision_text([], 0, 3), "결과 기입 Pass 3건")

    def test_revision_row_is_appended_with_bumped_version(self):
        self.plan()
        summary = de13.apply(self.plan_path, self.ledger_dir, {"bs.koo": "구본승"}, "구본승", "2026.10.13")
        self.assertEqual(summary["버전"], "1.1")
        rnum, row = self.revisions()[-1]
        self.assertEqual(rnum, 4)
        self.assertEqual((row["버전"], row["개정일"], row["개정 사유"], row["작성자"], row["승인자"]),
                         ("1.1", "2026.10.13", "개발 반영(gx-tdd)", "구본승", ""))
        self.assertEqual(row["개정 내용"], "단위테스트 신규 1건 추가(UT-009)·기대결과 보강 1건·결과 기입 Pass 2건")
        with zipfile.ZipFile(self.plan_path) as z:
            rev = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
            wb = z.read("xl/workbook.xml").decode("utf-8")
        self.assertIn('<autoFilter ref="A2:F4"/>', rev)
        self.assertIn('<c r="F4" s="3" t="inlineStr"><is><t></t></is></c>', rev)
        self.assertIn("'개정이력'!$A$2:$F$4</definedName>", wb)
        self.assertIn("'단위테스트계획'!$A$1:$K$10</definedName>", wb)
        self.assertEqual([r["반영"] for r in de13.read_md_table(self.ledger_dir / "feat-a.md")], ["v1.1", "v1.1 UT-009"])

    def test_unparseable_version_needs_override(self):
        self.plan(last_version="초안")
        with self.assertRaisesRegex(de13.InputError, "--version"):
            de13.apply(self.plan_path, self.ledger_dir, {"bs.koo": "구본승"}, "구본승", "2026.10.13")
        summary = de13.apply(self.plan_path, self.ledger_dir, {"bs.koo": "구본승"}, "구본승", "2026.10.13", version="2.0")
        self.assertEqual((summary["버전"], self.revisions()[-1][1]["버전"]), ("2.0", "2.0"))

    def test_nothing_to_apply_adds_no_revision(self):
        self.plan()
        de13.apply(self.plan_path, self.ledger_dir, {"bs.koo": "구본승"}, "구본승", "2026.10.13")
        before = self.plan_path.read_bytes()
        summary = de13.apply(self.plan_path, self.ledger_dir, {"bs.koo": "구본승"}, "구본승", "2026.10.14")
        self.assertEqual(summary["버전"], "")
        self.assertEqual(self.plan_path.read_bytes(), before)

    def test_cli_exit_codes_and_report(self):
        self.plan()
        testers = self.ledger_dir / "testers.md"
        report = self.dir / "report.json"
        args = ["apply", "--plan", str(self.plan_path), "--ledger-dir", str(self.ledger_dir), "--testers", str(testers),
                "--author", "구본승", "--date", "2026.10.13", "--report", str(report)]
        self.assertEqual(de13.main(args), 3)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["매핑 없는 담당자"], ["bs.koo"])
        testers.write_text("| git 이름 | 실명 |\n|---|---|\n| bs.koo | 구본승 |\n", encoding="utf-8")
        self.assertEqual(de13.main(args), 0)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["버전"], "1.1")
        self.assertEqual(de13.main(args), 0)  # 두 번째는 반영할 것이 없다
        self.assertEqual(de13.main(args[:2] + [str(self.dir / "none.xlsx")] + args[3:]), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_revision.py"`
Expected: FAIL — `next_version`·`revision_text`·`REVISION_HEAD` 없음

- [ ] **Step 3: 구현**

`# ---------- 계획서 반영 ----------` 절 머리에 추가한다.

```python
REVISION_HEAD = ("버전", "개정일", "개정 사유", "개정 내용", "작성자")
REVISION_REASON = "개발 반영(gx-tdd)"


def next_version(last: str) -> str:
    m = re.fullmatch(r"\s*(\d+)\.(\d+)\s*", last or "")
    if not m:
        raise InputError(f"개정이력 마지막 버전 '{last}'을 해석할 수 없습니다 — --version으로 지정하세요")
    return f"{m.group(1)}.{int(m.group(2)) + 1}"


def revision_text(new_ids: list[str], refined: int, passed: int) -> str:
    parts = []
    if new_ids:
        span = new_ids[0] if len(new_ids) == 1 else f"{new_ids[0]}~{new_ids[-1]}"
        parts.append(f"단위테스트 신규 {len(new_ids)}건 추가({span})")
    if refined:
        parts.append(f"기대결과 보강 {refined}건")
    parts.append(f"결과 기입 Pass {passed}건")
    return "·".join(parts)


def load_revision(path: Path) -> dict | None:
    wb = Workbook(Path(path))
    try:
        try:
            name, part, cols, body = _find_table(wb, REVISION_HEAD)
        except InputError:
            return None
        names = [n for n, _ in wb.sheets]
    finally:
        wb.close()
    entries = [(rnum, cells) for rnum, cells in body if (cells.get(cols["버전"], "") or "").strip()]
    if not entries:
        return None
    rnum, cells = entries[-1]
    return {"sheet": name, "part": part, "index": names.index(name), "cols": cols,
            "last_rnum": rnum, "last_version": cells.get(cols["버전"], "").strip()}
```

`apply`에서 `if not updates and not appended: return summary` 바로 뒤에 버전을 정한다 (쓰기 전에 실패해야 원본이 안전하다).

```python
    revision = load_revision(plan_path)
    if revision:
        summary["버전"] = version or next_version(revision["last_version"])
    elif version:
        summary["버전"] = version
```

zip 읽기 블록에 개정이력 시트를 함께 읽는다.

```python
    with zipfile.ZipFile(plan_path) as z:
        sheet = z.read(plan["part"]).decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
        rev_xml = z.read(revision["part"]).decode("utf-8") if revision else ""
```

Task 4의 `summary["개정이력"] = "개정이력 시트 없음"` 한 줄을 아래로 바꾼다.

```python
    if revision:
        rc = revision["cols"]
        text = revision_text(summary["신규"], summary["보강"], summary["결과 기입"] + len(summary["신규"]))
        values = {rc["버전"]: summary["버전"], rc["개정일"]: date, rc["개정 사유"]: REVISION_REASON,
                  rc["개정 내용"]: text, rc["작성자"]: author}
        old = _sheet_max_row(rev_xml)
        rev_xml = _extend_sheet_ranges(_append_rows(rev_xml, [(old + 1, values)], revision["last_rnum"]), old, old + 1)
        workbook = _extend_defined_names(workbook, revision["index"], old, old + 1)
        parts[revision["part"]] = rev_xml.encode("utf-8")
        summary["개정이력"] = f"{summary['버전']} {text}"
    else:
        summary["개정이력"] = "개정이력 시트 없음"
```

이 블록은 `parts["xl/workbook.xml"] = workbook.encode("utf-8")`보다 앞에 둔다.

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v`
Expected: 전부 OK

- [ ] **Step 5: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `계획서 반영 시 개정이력에 버전 한 줄을 남긴다`.

---

### Task 6: gx-tdd 완료 단계에 원장 작성(Step 0.5) 추가

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md`
- Create: `tests/test_de13_contract.py`

**Interfaces:**
- Consumes: CLI `tests`, `functions`, `rows`, `record` (Task 2·3)
- Produces: phase-complete `## Step 0.5: 단위테스트 원장 작성 (계획서 등록 시)`. Task 7이 `config.json` `testPlan.path`를 만든다.

- [ ] **Step 1: 실패하는 계약 테스트 작성**

```python
"""단위테스트계획서 역보강 지시문 계약."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def between(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


COMPLETE = ".claude/skills/gx-tdd/phases/phase-complete.md"


class BackfillContractTests(unittest.TestCase):
    def test_floor_flow_is_gone(self):
        stale = re.compile(r"ut-scope|ut-floor|setup-testplan|Step -1\.5|\[UT: ")
        files = [*(ROOT / ".claude/skills/gx-tdd").rglob("*.md"),
                 *(ROOT / ".claude/skills/gx-dev/references/codex-roles").glob("*.md"),
                 *(ROOT / "agents" / n for n in ("product-owner.md", "red-writer.md", "test-architect.md", "reviewer.md"))]
        for path in files:
            with self.subTest(file=path.name):
                self.assertIsNone(stale.search(path.read_text(encoding="utf-8")))

    def test_ledger_step_runs_between_acceptance_and_commit(self):
        complete = read(COMPLETE)
        self.assertLess(complete.index("## Step 0:"), complete.index("## Step 0.5:"))
        self.assertLess(complete.index("## Step 0.5:"), complete.index("## Step 1:"))
        core = between(complete, "**핵심 모드이면**", "**전체 모드**")
        self.assertNotIn("Step 1 진행", core)
        self.assertEqual(core.count("Step 0.5 진행"), 2)

    def test_ledger_step_uses_helper_without_questions(self):
        step = between(read(COMPLETE), "## Step 0.5:", "## Step 1:")
        for needle in ("testPlan.path", "tests --diff", "functions --plan", "rows --plan", "record --draft",
                       "skipped", "미지정", "커밋을 막지 않는다", "/gx-test-plan"):
            with self.subTest(needle=needle):
                self.assertIn(needle, step)
        self.assertNotIn("AskUserQuestion", step)
        self.assertEqual(step.count('"<PY>" "<DE13>"'), 4)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_contract.py" -v`
Expected: `test_floor_flow_is_gone` PASS(Task 1), 나머지 2건 FAIL (`## Step 0.5:` 없음)

- [ ] **Step 3: phase-complete 수정**

1) 핵심 모드 3번의 `3. 모두 충족 → Step 1 진행.`을 `3. 모두 충족 → Step 0.5 진행.`으로, `- "건너뛰기" → 위험 수용을 trust-ledger에 기록 후 Step 1 진행.`을 `- "건너뛰기" → 위험 수용을 trust-ledger에 기록 후 Step 0.5 진행.`으로 바꾼다.

2) `위 Step 0 진입 조건에 의해 PRD 부재이면 이 단계 전체가 건너뛰어진다.` 다음, `## Step 1: Commit` 앞에 넣는다.

```markdown
## Step 0.5: 단위테스트 원장 작성 (계획서 등록 시)

`.claude/config.json`의 `testPlan.path`가 비어 있거나 그 파일이 없으면 아무 안내 없이 Step 1로 진행한다. 등록돼 있으면 verify를 통과한 이번 변경의 테스트로 gx-pm 단위테스트계획서 역보강용 원장을 쓴다. **이 단계는 질문하지 않는다** — 짝짓기가 틀렸으면 사용자가 PR의 원장 diff에서 고친다.

`DE13`은 이 파일 위치 기준 `../../gx-test-plan/scripts/de13.py`의 절대경로, `PY`는 `python3 --version`이 3.x를 출력하면 `python3`, 아니면 `python`(Windows)이다. 둘 다 없으면 "Python이 없어 단위테스트 원장을 건너뜁니다" 1줄을 안내하고 Step 1로 진행한다. `TESTPLAN`은 `PROJECT_ROOT` 기준 `testPlan.path`, `SLUG`는 `DEV_DIR`의 마지막 경로 성분이다.

1. **테스트 목록**: `"<PY>" "<DE13>" tests --diff "${DIFF_FILE}" --root "${PROJECT_ROOT}" --out "${PROJECT_ROOT}/${DEV_DIR}/ut-tests.json"`. 테스트가 0개면 "이번 변경에 테스트가 없어 원장을 쓰지 않습니다" 1줄 후 Step 1로 진행한다.
2. **관련 기능**: `"<PY>" "<DE13>" functions --plan "<TESTPLAN>" --out "${PROJECT_ROOT}/${DEV_DIR}/ut-functions.json"` (계획서와 같은 폴더에 `*기능명세서*.xlsx`가 하나 있으면 `--spec "<그 파일>"`). AC·PRD 요구사항과 기능명·UT 수를 대조해 이번 작업에 해당하는 기능을 고르고, `"<PY>" "<DE13>" rows --plan "<TESTPLAN>" --fn "<기능ID,…>" --out "${PROJECT_ROOT}/${DEV_DIR}/ut-rows.md"`로 그 기능의 UT 행을 읽는다. 해당 기능을 고를 수 없으면 rows를 건너뛰고 모든 테스트를 신규(`미지정`)로 둔다.
3. **초안 작성**: `${DEV_DIR}/ut-draft.md`에 `| 구분 | 테스트ID | 연계기능ID | 사전조건 | 입력 | 기대결과 | 사후조건 | 테스트 위치 | 근거 |` 표를 쓴다.
   - `ut-tests.json`에서 `skipped: true`인 테스트는 넣지 않는다.
   - **기존**: 테스트가 UT 행의 사전조건·입력·기대결과와 같은 동작을 단언하면 `구분`=`기존`, 그 `테스트ID`. 계획서 기대결과가 모호하고("정상 처리", "안내" 등) 테스트 단언이 더 구체적이면 `기대결과`에 계획서 문체로 구체화한 한 문장을, 아니면 비운다. 사전조건·입력·사후조건은 비운다.
   - **신규**: 대응하는 행이 없는 동작은 `구분`=`신규`, `테스트ID` 비움, `연계기능ID`는 2에서 고른 기능(없으면 `미지정`), 사전조건·입력·기대결과·사후조건을 계획서 문체로 쓴다. 입력·기대결과는 필수다.
   - 확신이 낮으면 기존 행에 붙이지 않고 신규로 두고 `근거`에 "REB-UT-045와 유사"처럼 적는다.
   - 같은 동작의 여러 테스트(파라미터화·변형)는 한 행으로 묶고 `테스트 위치`에 `ut-tests.json`의 `path:line`을 `, `로 나열한다.
   - `근거`는 한 줄: 짝지은 이유(기존) 또는 계획서에 없다고 본 이유(신규).
4. **원장 기록**: `"<PY>" "<DE13>" record --draft "${PROJECT_ROOT}/${DEV_DIR}/ut-draft.md" --plan "<TESTPLAN>" --root "${PROJECT_ROOT}" --ledger "${PROJECT_ROOT}/.dev/ut-results/<SLUG>.md" --date "<오늘, YYYY.MM.DD>" --tester "<git config user.name>"`. svn이면 `--tester`에 OS 사용자명을 쓴다 (`/gx-test-plan`이 실명으로 매핑한다).
5. 종료 코드 2면 메시지대로 초안을 고쳐 4를 한 번 더 실행한다. 두 번째도 실패하면 "단위테스트 원장을 기록하지 못했습니다 — `/gx-tdd --phase complete`로 다시 시도할 수 있습니다"를 경고하고 execution-log에 남긴 뒤 Step 1로 진행한다. 원장 실패는 커밋을 막지 않는다.
6. 성공하면 헬퍼 출력 한 줄과 "계획서 반영은 `/gx-test-plan`"을 보고한다. 원장은 `.dev` 아래라 verify 지문이 바뀌지 않으며 Step 1 커밋에 함께 들어간다 (svn은 Step 1 안내의 `svn add --force .`로 등록된다).

`current-step`을 `"단위테스트 원장"`으로 갱신.
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_contract.py" -v`
Expected: 3 tests OK

- [ ] **Step 5: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `gx-tdd 완료 단계에서 작성된 테스트로 단위테스트 원장을 쓴다`.

---

### Task 7: gx-setup에 단위테스트계획서 경로 등록

**Files:**
- Modify: `.claude/skills/gx-setup/SKILL.md`, `.claude/config.json`
- Regenerate: `.claude/skills/gx-setup/references/config.template.json`
- Modify: `tests/test_de13_contract.py`

**Interfaces:**
- Consumes: 없음
- Produces: `config.json` `"testPlan": {"path": ""}`, gx-setup `### 3.5단계: 단위테스트계획서 (선택)`

- [ ] **Step 1: 실패하는 계약 테스트 추가** (`BackfillContractTests`에)

```python
    def test_setup_registers_test_plan_path(self):
        section = between(read(".claude/skills/gx-setup/SKILL.md"), "### 3.5단계", "### 4단계")
        for needle in ('{"testPlan":{"path":', "~$*.xlsx", "등록 안 함", "단위테스트계획서 : 완료"):
            with self.subTest(needle=needle):
                self.assertIn(needle, section)
        for rel in (".claude/config.json", ".claude/skills/gx-setup/references/config.template.json"):
            with self.subTest(file=rel):
                self.assertEqual(json.loads(read(rel))["testPlan"], {"path": ""})
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_contract.py"`
Expected: FAIL — `### 3.5단계` 없음

- [ ] **Step 3: config와 템플릿**

`.claude/config.json`의 `"notifications"` 객체 뒤에 `"testPlan": { "path": "" },`를 기존 들여쓰기에 맞춰 넣는다 (`contextLimits` 앞).
Run: `python scripts/sync-codex-resources.py`
Run: `python scripts/sync-codex-resources.py --check`
Expected: 드리프트 없음, 템플릿에 `testPlan` 반영

- [ ] **Step 4: gx-setup 단계 추가**

`### 4단계: Google Chat 알림 연동 (선택)` 앞에 넣는다.

```markdown
### 3.5단계: 단위테스트계획서 (선택)

gx-pm이 만든 단위테스트계획서가 있으면 경로를 등록한다. 등록하면 `/gx-tdd` 완료 단계가 작성된 테스트를 계획서 케이스와 짝지어 원장에 남기고, `/gx-test-plan`이 그 원장으로 계획서를 보강·결과 기입·개정이력 갱신한다.

1. `.claude/config.json`의 `testPlan.path`가 있고 그 파일이 있으면 `단위테스트계획서 : 완료 ✅ ({경로}, 기존 설정 유지)` 출력 후 건너뛴다.
2. 프로젝트 루트에서 `*단위테스트계획서*.xlsx`를 찾는다. `~$`로 시작하는 파일, `.dev/` 아래, 빌드 산출물 디렉터리(`projectTypes.*.artifacts`)는 뺀다. 최근 수정 순으로 정렬한다.
3. 1개 이상이면:
   ```
   AskUserQuestion(
     questions: [{
       header: "테스트계획서",
       question: "단위테스트계획서를 등록할까요? gx-tdd가 작성한 테스트로 계획서를 보강하고 결과를 기입합니다.",
       multiSelect: false,
       options: [
         { label: "{파일 1}", description: "최근 수정: {날짜}" },
         { label: "{파일 2}", description: "최근 수정: {날짜}" },
         { label: "등록 안 함", description: "계획서 없이 사용합니다" }
       ]
     }]
   )
   ```
   파일이 1개면 `{파일 2}` 선택지를 뺀다. 0개면 선택지를 "경로 입력"("다음 질문에서 경로를 받습니다")과 "등록 안 함"으로 묻는다. "경로 입력"이면 별도 후속 질문으로 경로를 받고 실제 답변을 기다린다. 파일이 없거나 `.xlsx`가 아니면 1회 다시 묻고, 그래도 아니면 건너뛴다.
4. 고른 파일의 `PROJECT_ROOT` 기준 상대경로(`/` 구분)를 기록한다. Codex는 위 helper에 `{"testPlan":{"path":"{상대경로}"}}` updates만 전달한다. Claude Code는 Edit를 사용한다.
5. 엑셀 잠금 파일이 커밋되지 않게 ignore를 보강한다. git은 `.gitignore`에 `~$*.xlsx`가 없으면 추가하고, svn은 `svn propget svn:ignore .`에 없으면 `svn propset`으로 추가한다.
6. `단위테스트계획서 : 완료 ✅ ({상대경로})` 출력. "등록 안 함"이면 `단위테스트계획서 : 건너뜀` 출력 (값은 빈 채로 두어 다음 setup에서 다시 묻는다).
```

- [ ] **Step 5: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_contract.py" -v`
Expected: 4 tests OK
Run: `python -m unittest discover -s tests -p "test_codex_*.py"`
Expected: OK (config 템플릿 계약 포함)

- [ ] **Step 6: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `gx-setup에서 단위테스트계획서 경로를 등록한다`.

---

### Task 8: `/gx-test-plan` 제자리 갱신 절차, gx-commit·라우팅 정리

**Files:**
- Rewrite: `.claude/skills/gx-test-plan/SKILL.md`
- Modify: `.claude/skills/gx-commit/SKILL.md`, `.claude/rules/skill-routing.md`
- Modify: `tests/test_de13_contract.py`

**Interfaces:**
- Consumes: CLI `apply --plan --ledger-dir --testers --author [--date] [--version] --report` (Task 4·5), `config.json` `testPlan.path` (Task 7)
- Produces: 사용자 진입점 절차

- [ ] **Step 1: 실패하는 계약 테스트 추가**

```python
    def test_test_plan_skill_updates_registered_plan_in_place(self):
        skill = read(".claude/skills/gx-test-plan/SKILL.md")
        for needle in ("testPlan.path", "--author", "git status --porcelain", "개정이력", "testers.md", "엑셀에서 닫고"):
            with self.subTest(needle=needle):
                self.assertIn(needle, skill)
        for stale in ("_결과반영_", "export", "사본"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, skill)
        commit = read(".claude/skills/gx-commit/SKILL.md")
        self.assertIn("`.dev/ut-results/`", commit)
        self.assertNotIn("ut-results/export", commit)
        self.assertIn("계획서 반영", read(".claude/rules/skill-routing.md"))
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_contract.py"`
Expected: FAIL

- [ ] **Step 3: gx-test-plan SKILL.md 교체**

```markdown
---
name: gx-test-plan
version: 1.1.0
description: "gx-tdd가 남긴 단위테스트 원장으로 gx-pm 단위테스트계획서(DE-13) xlsx를 갱신한다 — 결과·기대결과 보강, 신규 케이스 추가, 개정이력. '단위테스트 계획서 반영', '계획서 갱신', '단위테스트 결과 반영' 시 사용."
argument-hint: "[계획서 경로]"
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "AskUserQuestion", "Bash(python *)", "Bash(python3 *)", "Bash(git *)", "Bash(svn *)", "Bash(ls *)", "Bash(test *)", "Bash(mkdir *)"]
---

# gx-test-plan

> **이 스킬**: gx-test-plan — 단위테스트 원장을 계획서에 반영하고 개정이력을 남긴다
> **혼동 주의**: 원장은 gx-tdd 완료 단계가 만든다. 이 스킬은 테스트를 실행하지 않는다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. Codex에서는 먼저 `Read("../gx-dev/references/codex-runtime.md")`로 공통 실행 규약을 읽는다. 상대경로는 이 SKILL.md 위치 기준이다. `AskUserQuestion`은 현재 모드에서 제공된 질문 도구로 옮기고 실제 답변을 기다린다. 질문은 한 번에 1~3개, 질문마다 선택지는 2~3개이며 Other를 option으로 직접 추가하지 않는다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → `request_user_input`. 그 도구를 쓸 수 없으면 자연어로 묻되, **실제 답변 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다.

헬퍼는 [scripts/de13.py](scripts/de13.py)다. 이 SKILL.md 위치 기준 절대경로를 `DE13`으로 두고 `python3 "<DE13>" …`(Windows는 `python`)로 실행한다. 둘 다 없으면 "Python 3.10 이상이 필요합니다"를 안내하고 종료한다.

## 절차

1. **프로젝트 루트**: `git rev-parse --show-toplevel`(svn은 `svn info --show-item wc-root`), 둘 다 아니면 현재 디렉터리.
2. **계획서**: ARGS[0]에 경로가 있으면 그 파일, 없으면 `.claude/config.json`의 `testPlan.path`. 둘 다 없으면 "단위테스트계획서가 등록되지 않았습니다. `/gx-setup`에서 등록하거나 경로를 함께 적어 주세요"를 안내하고 종료한다.
3. **원장 확인**: `.dev/ut-results/`에 `testers.md`를 뺀 `*.md`가 없으면 "기록된 단위테스트 원장이 없습니다. 계획서를 등록한 뒤 gx-tdd를 완료하면 원장이 생깁니다"를 안내하고 종료한다.
4. **미커밋 수정 확인**: git은 `git status --porcelain -- "<계획서>"`, svn은 `svn status "<계획서>"` 출력이 비어 있지 않으면 "계획서에 커밋되지 않은 수정이 있습니다. 먼저 커밋하거나 되돌린 뒤 다시 실행하세요"를 안내하고 종료한다 (PM 수정분과 반영분이 한 변경에 섞이지 않게 한다).
5. **작성자**: `git config user.name`(svn은 OS 사용자명)이 `.dev/ut-results/testers.md`(`| git 이름 | 실명 |` 표)에 없으면 실명을 묻고 실제 답변을 기다린 뒤 행을 추가한다(파일이 없으면 만든다). 그 실명이 `AUTHOR`다.
6. **반영**: `python3 "<DE13>" apply --plan "<계획서>" --ledger-dir ".dev/ut-results" --testers ".dev/ut-results/testers.md" --author "<AUTHOR>" --report "<임시 디렉터리>/report.json"` (임시 디렉터리는 `mktemp -d`로 프로젝트 밖에 만든다).
7. **종료 코드 3** (매핑 없는 담당자): `report.json`의 `매핑 없는 담당자`마다 실명을 묻고(한 번에 3명까지) 실제 답변을 기다린 뒤 `testers.md`에 행을 추가하고 6을 다시 실행한다.
8. **종료 코드 2**: 메시지를 그대로 보고하고 종료한다. 버전을 해석할 수 없다는 메시지면 새 버전 번호를 묻고 `--version`을 붙여 6을 다시 실행한다. "엑셀에서 닫고" 메시지면 계획서를 닫은 뒤 다시 실행하도록 안내한다.
9. **보고**: `report.json`으로 표를 보여준다 — 버전, 결과 기입, 기대결과 보강, 신규 ID 범위, 개정이력 내용. `재확인 필요`가 있으면 "PM이 계획서에서 해당 케이스를 고쳤습니다. 원장 행을 확인하고 필요하면 그 기능을 gx-tdd로 다시 완료하세요"를, `계획서에 없음`·`기능 미지정`이 있으면 그 수와 원장의 해당 행을 고쳐 다시 실행하라는 안내를 한다. 마지막에 "계획서와 원장(`.dev/ut-results/`)이 바뀌었습니다. `/gx-commit`으로 함께 커밋하세요"를 안내한다.

## 하지 않는 것

- 커밋하지 않는다. 계획서와 원장 반영 표시는 사용자가 함께 커밋한다.
- `Fail`을 기록하지 않는다. 원장에는 verify를 통과한 `Pass`만 있다.
- 비기능 행(연계기능ID 공란)은 건드리지 않는다. 신규 행은 데이터 시트 끝에 추가한다.
```

- [ ] **Step 4: gx-commit·라우팅**

`.claude/skills/gx-commit/SKILL.md` 5번 "제외 파일 없음"의 `'.dev/ut-results/export'` 인자와 `` `.dev/ut-results/export`는 `/gx-test-plan`이 만드는 반영 사본이다`` 문장을 지워 main 문장으로 되돌린다 (1번의 `.dev/ut-results/` 예외 문장은 유지).
`.claude/rules/skill-routing.md`의 gx-test-plan 행을 바꾼다.

```markdown
| `계획서 반영`, `단위테스트 계획서 반영`, `계획서 갱신`, `단위테스트 결과 반영` | `/gx-test-plan` |
```

- [ ] **Step 5: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_contract.py" -v`
Expected: 5 tests OK
Run: `python scripts/sync-codex-resources.py --check`
Expected: 드리프트 없음

- [ ] **Step 6: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `gx-test-plan이 등록된 계획서를 제자리에서 갱신하도록 바꾼다`.

---

### Task 9: 문서·릴리스 노트·검증 기록, 전체 검증

**Files:**
- Modify: `README.md`, `docs/guide.md`, `docs/onboarding-guide.md`, `docs/tdd-guide.md`, `tests/codex-smoke.md`, `CHANGELOG.md`
- Delete: `docs/superpowers/specs/2026-10-12-gx-tdd-test-plan-link-design.md`, `docs/superpowers/plans/2026-10-12-gx-tdd-test-plan-link.md`, `docs/reports/2026-10-12-gx-tdd-test-plan-smoke.md`
- Create: `docs/reports/2026-10-13-gx-tdd-test-plan-backfill-smoke.md`

**Interfaces:**
- Consumes: Task 1~8 결과
- Produces: 사용자 문서

- [ ] **Step 1: README**

`**단위테스트계획서 연동** — …` 문단을 아래로 바꾼다.

```markdown
**단위테스트계획서 역보강** — `/gx-setup`에서 gx-pm 단위테스트계획서(xlsx) 경로를 등록해 두면, gx-tdd는 평소처럼 도메인·요구사항 단위로 개발하고 완료 단계에서 이번에 작성한 테스트를 계획서 케이스와 짝지어 `.dev/ut-results/{브랜치}.md` 원장에 남깁니다. 기존 케이스에는 결과와 구체화한 기대결과를, 계획서에 없던 케이스는 신규 후보로 적습니다. 원장은 기능 커밋에 함께 들어가 PR에서 확인할 수 있고, `/gx-test-plan`이 모아서 계획서를 새 버전으로 갱신합니다.
```

`### test-plan` 절 본문을 아래로 바꾼다.

```markdown
`/gx-test-plan` — 쌓인 단위테스트 원장을 등록된 단위테스트계획서 xlsx에 반영합니다. 기존 케이스의 결과·수행일·담당자를 채우고 기대결과를 보강하며, 신규 케이스는 이어지는 번호(예: REB-UT-170)로 추가하고, 개정이력 시트에 버전 한 줄을 남깁니다. PM이 그 사이 고친 케이스는 채우지 않고 "재확인 필요"로 알려 줍니다.
```

- [ ] **Step 2: guide·onboarding·tdd-guide**

`docs/guide.md`: `/gx-test-plan ────── 단위테스트 원장 → 계획서(xlsx) 보강·결과·개정이력`.
`docs/onboarding-guide.md`의 `#### /gx-test-plan` 절 본문:

```markdown
`/gx-setup`에서 단위테스트계획서(xlsx)를 등록하면 gx-tdd는 완료 단계에서 작성한 테스트를 계획서 케이스와 짝지어 `.dev/ut-results/`에 원장을 남깁니다. `/gx-test-plan`은 그 원장으로 계획서를 갱신합니다 — 결과·수행일·테스트담당자 기입, 기대결과 보강, 신규 케이스 추가, 개정이력 한 줄. 처음 보는 git 이름은 실명을 한 번 묻고 기억합니다.
```

`docs/tdd-guide.md`의 `#### 단위테스트계획서(DE-13) 연동` 소절 전체를 아래로 바꾼다.

```markdown
#### 단위테스트계획서(DE-13) 역보강

`/gx-setup`에서 단위테스트계획서를 등록한 프로젝트에서만 동작합니다. gx-tdd의 단계·게이트는 바뀌지 않습니다.

1. complete 단계 Step 0.5에서 이번 변경의 테스트(skip 제외)를 계획서 행과 짝지어 `.dev/ut-results/{브랜치}.md` 원장에 기록합니다. 질문하지 않으며, 짝짓기 근거가 원장에 남아 PR에서 고칠 수 있습니다.
2. 기존 케이스는 결과 `Pass`와 구체화한 기대결과를, 계획서에 없던 동작은 신규 행 후보를 적습니다. 확신이 낮으면 신규로 두고 유사한 케이스를 근거에 적습니다.
3. `/gx-test-plan`이 원장을 모아 계획서를 갱신하고 개정이력에 버전을 올립니다. 원장 행에는 `v1.1 REB-UT-170`처럼 반영 표시가 남아 두 번 반영되지 않습니다.
```

- [ ] **Step 3: codex-smoke T1·CHANGELOG**

`tests/codex-smoke.md` T1 행을 바꾼다.

```markdown
| T1 | 계획서가 등록된 소비 프로젝트에서 도메인 요청으로 gx-tdd 완료 후 `/gx-test-plan` (Codex) | complete 단계에 계획서 질문 없음; `.dev/ut-results/{slug}.md` 생성; `/gx-test-plan` 질문 3개 이하·선택지 3개 이하, 실명 질문이 실제 답변을 기다림; 계획서 개정이력 1행 추가 | 미실행 |
```

`CHANGELOG.md`의 `## v1.34.0 (2026-10-12)` 절 전체를 바꾼다.

```markdown
## v1.34.0 (2026-10-13)

### Added

- **단위테스트계획서(DE-13) 역보강**: `/gx-setup`에서 gx-pm 단위테스트계획서 경로를 등록하면 gx-tdd 완료 단계가 작성된 테스트를 계획서 케이스와 짝지어 `.dev/ut-results/{브랜치}.md` 원장에 남긴다 (질문 없음, 근거 기록, 기능 커밋에 포함). gx-tdd 진입·단계·게이트는 바뀌지 않는다.
- **`/gx-test-plan`**: 원장으로 계획서를 제자리 갱신한다 — 결과·수행일·담당자 기입, 기대결과 보강, 신규 케이스 채번·추가, 개정이력 버전 한 줄. PM이 고친 케이스는 "재확인 필요"로 남기고, 엑셀이 열려 있으면 원본과 원장을 바꾸지 않는다.
- `de13.py` 헬퍼(표준 라이브러리 전용: `tests`·`functions`·`rows`·`record`·`apply`)와 단위 테스트, CI 실행 단계.

Codex 실제 세션의 T1 시나리오와 실제 프로젝트 smoke는 별도 검증 항목이다.
```

- [ ] **Step 4: 실데이터 확인 (헬퍼 단독, 사본으로)**

scratchpad에 `realcheck/` 폴더를 만들고 실제 계획서를 복사한 뒤 아래 스크립트(`realcheck.py`, scratchpad의 별도 폴더)를 실행한다. 원본 경로는 읽기만 한다.

```python
import json, shutil, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0, r"D:\Temp\oh-my-gx-test-plan-link\.claude\skills\gx-test-plan\scripts")
import de13

work = Path(sys.argv[1])
src = Path(r"D:\SQ\pm-test\건물에너지 데이터 통합관리 시스템\xlsx\REB-단위테스트계획서.xlsx")
plan_path = work / src.name
shutil.copyfile(src, plan_path)
plan = de13.load_plan(plan_path)
rec = next(r for r in plan["rows"] if r["테스트ID"] == "REB-UT-001")
ledger = work / ".dev" / "ut-results"
de13._write_ledger(ledger / "feat-source.md", [
    {"구분": "기존", "테스트ID": "REB-UT-001", "연계기능ID": "REB-FN-001", "기대결과": "", "결과": "Pass",
     "수행일": "2026.10.13", "담당자": "bs.koo", "테스트 위치": "a:1", "행 지문": de13.row_fingerprint(rec), "근거": "", "반영": ""},
    {"구분": "신규", "테스트ID": "", "연계기능ID": "REB-FN-001", "사전조건": "회차 없음", "입력": "빈 파일(0바이트) 등록",
     "기대결과": "\"빈 파일은 등록할 수 없습니다\" 안내, 등록 차단", "사후조건": "저장 없음", "결과": "Pass",
     "수행일": "2026.10.13", "담당자": "bs.koo", "테스트 위치": "a:2", "행 지문": "", "근거": "", "반영": ""}])
summary = de13.apply(plan_path, ledger, {"bs.koo": "구본승"}, "구본승", "2026.10.13")
print(json.dumps(summary, ensure_ascii=False, indent=1))
after = de13.load_plan(plan_path)
print(len(after["rows"]), after["rows"][-1]["테스트ID"], after["rows"][-1]["연계요구사항ID"])
with zipfile.ZipFile(plan_path) as z, zipfile.ZipFile(src) as o:
    print(sorted(n for n in z.namelist() if z.read(n) != o.read(n)))
    print(z.read("xl/worksheets/sheet1.xml").decode()[-900:])
print(de13.read_md_table(ledger / "feat-source.md")[1]["반영"])
```

Run: `python -I <scratchpad>/realcheck-src/realcheck.py <scratchpad>/realcheck`
Expected: `버전` `1.1`, `신규` `["REB-UT-170"]`, 행 170개 → 171개(로드된 행 수 170), 마지막 `REB-UT-170 REB-RE-001`, 바뀐 zip 항목은 `sheet1.xml`·`sheet2.xml`·`workbook.xml`, 개정이력 시트 끝에 `1.1 · 2026.10.13 · 개발 반영(gx-tdd) · 단위테스트 신규 1건 추가(REB-UT-170)·결과 기입 Pass 2건 · 구본승`, 원장 표시 `v1.1 REB-UT-170`. 복사본 경로를 사용자 확인용으로 보고서에 적는다.

- [ ] **Step 5: 검증 기록 작성**

`docs/reports/2026-10-13-gx-tdd-test-plan-backfill-smoke.md`를 아래 구조로 쓰고 Step 4·6의 실제 출력 수치를 채운다. 구 보고서·구 spec·구 plan을 지운다.

```markdown
# gx-tdd 단위테스트계획서 역보강 검증 보고

작성일: 2026-10-13
대상 브랜치: `feat/gx-tdd-test-plan-link`
설계: `docs/superpowers/specs/2026-10-13-gx-tdd-test-plan-backfill-design.md`
계획: `docs/superpowers/plans/2026-10-13-gx-tdd-test-plan-backfill.md`

## 1. 자동 검사 (Windows, Python 3.10)

| 검사 | 명령 | 결과 |
|---|---|---|
| 헬퍼 단위·지시문 계약 테스트 | `python -m unittest discover -s tests -p "test_de13_*.py"` | {N} tests OK |
| Codex 계약 테스트 | `python -m unittest discover -s tests -p "test_codex_*.py"` | {N} tests OK |
| Codex 역할 동기화 | `python scripts/sync-codex-resources.py --check` | 드리프트 없음 |
| 훅 회귀 | `bash scripts/hook-tests.sh` | 통과 |
| 정합성 린트 | `bash scripts/lint-consistency.sh` | 36/36 |

## 2. 실데이터 확인 (헬퍼 단독, 사본)

| 항목 | 결과 |
|---|---|
| apply (기존 REB-UT-001 + 신규 1건) | {Step 4 출력} |
| 엑셀에서 갱신본 열기 | 미실행 — 사용자 확인 필요 (`{사본 경로}`: 신규 행 서식·드롭다운·필터 범위, 개정이력 행) |

## 3. 실제 파이프라인 smoke

| ID | 절차 | 확인 항목 | 상태 |
|---|---|---|---|
| P1 | 계획서를 등록한 샘플 Spring Boot 프로젝트에서 도메인 요청(`건물별 메모 관리 TDD로 개발해줘`) | 계획서 관련 질문 없음 / complete Step 0.5에서 `.dev/ut-results/{slug}.md` 생성, 기존·신규 행과 근거 / 기능 커밋에 원장 포함 | 미실행 |
| P2 | P1 이후 `/gx-test-plan` | 실명 질문 1회, 계획서 신규 행·결과·개정이력 1.1, 원장 반영 표시 | 미실행 |
| T1 | Codex 세션 (`tests/codex-smoke.md` T1) | 질문 규칙, 실제 답변 대기 | 미실행 |
```

- [ ] **Step 6: 전체 검증**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v` → OK
Run: `python -m unittest discover -s tests -p "test_codex_*.py"` → OK
Run: `python scripts/sync-codex-resources.py --check` → 드리프트 없음
Run: `bash scripts/hook-tests.sh` → 통과
Run: `bash scripts/lint-consistency.sh` (timeout 600000) → 36/36
Run: Grep `ut-floor|ut-scope|setup-testplan|_결과반영_|ut-results/export|하한선` in 저장소 전체(`docs/superpowers/plans/2026-10-13-*`·spec·CHANGELOG의 "하한선" 언급 제외)
Expected: 0건

- [ ] **Step 7: 커밋**

`Skill("oh-my-gx:gx-commit")`, 인자: `단위테스트계획서 역보강 흐름으로 문서와 검증 기록을 갱신한다`.
