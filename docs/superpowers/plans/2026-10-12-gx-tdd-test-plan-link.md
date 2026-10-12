# gx-tdd 단위테스트계획서(DE-13) 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-pm이 만든 DE-13 단위테스트계획서(xlsx)를 gx-tdd의 테스트 하한선으로 쓰고, 통과한 케이스를 기능별 원장에 남겨 계획서 사본에 결과를 반영할 수 있게 한다.

**Architecture:** 표준 라이브러리 전용 헬퍼 `de13.py`(scope·check·record·apply)가 xlsx 입출력과 판정을 맡는다. gx-tdd는 조건부 phase 파일 `setup-testplan.md`로 범위를 확정하고, requirements 게이트 1(UT 태그)과 complete 게이트 2(테스트 존재)로 하한선을 강제한 뒤, `.dev/ut-results/{기능ID}.md` 원장을 기능 커밋에 포함한다. 새 스킬 `gx-test-plan`이 원장을 계획서 사본에 반영한다.

**Tech Stack:** Python 3.10 표준 라이브러리(zipfile, xml.etree, hashlib, json, argparse, os, re), unittest, Markdown 스킬·phase·에이전트 정의, Bash 린트.

**Spec:** `docs/superpowers/specs/2026-10-12-gx-tdd-test-plan-link-design.md`

## Global Constraints

- 헬퍼는 Python **3.10** 표준 라이브러리만 사용한다 (CI `actions/setup-python` 3.10, Windows·Ubuntu 매트릭스). openpyxl 등 외부 패키지 금지.
- 파일 입출력은 모두 `encoding="utf-8"`. 큰 출력은 파일로 쓰고 stdout에는 한두 줄 요약만 쓴다. `main()` 시작에서 stdout·stderr 둘 다 `reconfigure(encoding="utf-8", errors="replace")` (Windows 콘솔 cp949에서 오류 메시지가 깨지는 것을 계획 검증 중 확인).
- 원본 계획서 xlsx는 읽기만 한다. 반영은 항상 사본(`--out`)에만 쓴다.
- 원장 위치는 `.dev/ut-results/{기능ID}.md`, 담당자 매핑은 `.dev/ut-results/testers.md`, 반영 사본은 `.dev/ut-results/export/`. `.dev` 밖에 쓰지 않는다 (verify 지문이 `.dev`만 제외).
- 수행일 형식 `YYYY.MM.DD`. `결과` 열에는 정확히 `Pass`만 쓴다 (계획서 데이터 검증 `Pass,Fail`).
- `ut-floor.md` 판정 값은 `대상`, `제외(사유)`, `이관(Wnn)` 세 가지뿐이다.
- gx-tdd `phases/phase-setup.md`는 CR 제거 후 **22,000바이트 이하** (린트 [32/36]). `SKILL.md`는 63,000바이트 이하.
- phase 파일의 정적 `AskUserQuestion` 예시는 질문 1~3개, 질문마다 선택지 2~3개. `label: "직접 입력"`류 입력 라벨과 `description: "Other로…"` 금지 (`tests/test_codex_skill_questions.py`).
- 번들 파일 참조는 그 지시가 적힌 파일 위치 기준 상대경로. `${CLAUDE_PLUGIN_ROOT}` 금지 (린트 [15/36]). 마크다운 링크는 실제 파일로 해석되어야 한다 (`tests/test_codex_skill_layout.py`).
- 커밋 메시지 `{type}: 한국어 메시지`, `Co-Authored-By` 트레일러 금지. 이 브랜치의 타입은 `feat`.
- `agents/*.md`를 바꾸면 같은 태스크에서 `python scripts/sync-codex-resources.py`를 실행해 `codex-roles/`를 갱신한다.
- 버전 4곳과 `CHANGELOG.md`는 마지막 태스크에서만 바꾼다.

## Review Focus

1. **엑셀에서 열어 저장한 계획서** (공유 문자열·서식 런으로 바뀜) — 사용자는 gx-pm 출력과 같은 결과를 기대한다 → Task 1 `test_reads_shared_strings_and_rich_runs`.
2. **같은 ID지만 PM 개정으로 내용이 바뀐 행** — Pass를 조용히 덮어쓰지 않고 `재확인 필요`로 보고되기를 기대한다 → Task 4 `test_fingerprint_mismatch_is_reported_not_written`.
3. **`@Disabled`가 붙은 테스트에만 UT ID가 있는 경우** — 하한선 통과로 보면 안 된다 → Task 2 `test_method_level_disabled_is_skipped`, `test_class_level_disabled_skips_file`.
4. **`REB-UT-0021`처럼 앞부분이 같은 ID** — `REB-UT-002`가 있다고 오판하면 안 된다 → Task 2 `test_id_boundary_does_not_match_longer_id`.
5. **반영 사본 경로를 원본과 같게 준 실수** — 원본이 덮어써지면 안 된다 → Task 4 `test_refuses_to_overwrite_plan`.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `.claude/skills/gx-test-plan/scripts/de13.py` (신규) | DE-13 xlsx 읽기, ut-floor.md 쓰기, 테스트 소스 검사, 원장 갱신, xlsx 사본 반영 |
| `tests/de13_support.py` (신규) | 테스트용 최소 xlsx 생성기와 헬퍼 로더 |
| `tests/test_de13_scope.py` · `test_de13_check.py` · `test_de13_record.py` · `test_de13_apply.py` (신규) | 명령별 단위 테스트 |
| `.github/workflows/lint.yml` | `test_de13_*.py`를 CI에서 실행 |
| `.claude/skills/gx-tdd/phases/setup-testplan.md` (신규) | 계획서 탐지·범위 확정·단독 진입 절 |
| `.claude/skills/gx-tdd/phases/phase-setup.md` | 3.1 포인터 한 줄 + 예산 맞춤 압축 |
| `.claude/skills/gx-tdd/SKILL.md` | 환경 감지 8, `allowed-tools`에 python |
| `.claude/skills/gx-tdd/references/pipeline-state.md` | `ut-scope` 필드 |
| `.claude/skills/gx-tdd/phases/setup-resume.md` | ut-floor 복원 |
| `.claude/skills/gx-tdd/phases/phase-requirements.md` | 태그 주입, core 상한 완화, 게이트 1 |
| `.claude/skills/gx-tdd/phases/phase-design.md` | test-architect에 UT 조건 전달 |
| `.claude/skills/gx-tdd/phases/phase-implement.md` | ut-floor 로드, 태스크 표, 이관, 2-R·2-V 프롬프트 |
| `.claude/skills/gx-tdd/phases/phase-review.md` | Task A UT 대조 |
| `.claude/skills/gx-tdd/phases/phase-complete.md` | Step -1.5 게이트 2, core 자가 검증, Step 0.5 원장 기록 |
| `agents/product-owner.md` · `red-writer.md` · `test-architect.md` · `reviewer.md` | UT 규칙 |
| `.claude/skills/gx-commit/SKILL.md` | `.dev/ut-results/` 예외, export 언스테이징 |
| `.claude/skills/gx-test-plan/SKILL.md` (신규) | 반영 스킬 |
| `.claude/rules/skill-routing.md` · `harness-codex.md`, `README.md`, `docs/onboarding-guide.md`, `docs/guide.md`, `docs/tdd-guide.md`, `index.html`, `tests/codex-smoke.md` | 라우팅·스킬 수·사용 안내 |
| `scripts/lint-consistency.sh` | [32/36]에 setup-testplan 포인터 검사 |
| `.claude-plugin/plugin.json` · `marketplace.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md` | 릴리스 |

---

### Task 1: 테스트 지원 모듈과 `scope` 명령

**Files:**
- Create: `.claude/skills/gx-test-plan/scripts/de13.py`
- Create: `tests/de13_support.py`
- Test: `tests/test_de13_scope.py`

**Interfaces:**
- Consumes: 없음
- Produces (이후 태스크가 그대로 사용):
  - `class InputError(Exception)`
  - `load_plan(path: Path) -> dict` — 키 `sheet: str`, `part: str`(zip 내부 시트 경로), `cols: dict[str, int]`(머리글 → 0기반 열 번호), `rows: list[dict]`(머리글 키 + `_row: int` 엑셀 행 번호 + `_flags: list[str]`), `sha: str`(파일 sha256 앞 12자)
  - `row_fingerprint(rec: dict) -> str` — 8자 16진수
  - `build_floor(plan: dict, fn_ids: list[str]) -> list[dict]` — 키 `테스트ID, 기능ID, 사전조건, 입력, 기대결과, 사후조건, 의존성, 표식, 판정, 행 지문`
  - `write_floor(path: Path, source: str, plan: dict, fn_ids: list[str], rows: list[dict], date: str) -> None`
  - `read_md_table(path: Path) -> list[dict[str, str]]` — 파일의 첫 번째 마크다운 표
  - `write_md_table(header: list[str], rows: list[dict]) -> str`
  - `function_list(plan: dict, spec: Path | None) -> list[dict]` — 키 `기능ID, UT수, 기능명`
  - `main(argv: list[str] | None = None) -> int`
  - `FLOOR_HEADER`, `LEDGER_HEADER` 상수 (아래 코드)
- 테스트 지원: `de13_support.make_xlsx(path, sheets, shared=False, validation=None)`, `de13_support.load_de13()`, `de13_support.PLAN_HEADER_11`, `de13_support.sample_rows()`

- [ ] **Step 1: 테스트 지원 모듈 작성**

`tests/de13_support.py`:

```python
"""DE-13 헬퍼 테스트용 최소 xlsx 생성기."""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from codex_test_support import load

HELPER = ".claude/skills/gx-test-plan/scripts/de13.py"

PLAN_HEADER_11 = ["테스트ID", "연계기능ID", "연계요구사항ID", "사전조건", "입력", "기대결과",
                  "사후조건", "의존성", "테스트담당자", "수행일", "결과"]


def load_de13():
    return load("de13", HELPER)


def sample_rows():
    """REB 계획서의 실제 패턴(〃, 비기능, [미확정], [가정], 떨어진 ID, 타기능 의존)을 담은 행."""
    return [
        ["UT-001", "FN-001", "RE-001", "신규 프로젝트", "파일 4종(각 500MB)", "회차 생성, 상태 '등록완료'", "TB_CYCL 1건", "없음", "", "", ""],
        ["UT-002", "FN-001", "RE-001", "〃", "파일 1,001MB", "\"파일 용량 초과\" 안내", "저장 없음", "없음", "", "", ""],
        ["UT-003", "FN-001", "RE-001", "〃", "파일 정확히 1,000MB", "정상 등록", "TB_SRC_FILE 1건", "UT-001", "", "", ""],
        ["UT-004", "FN-002", "RE-002", "회차 5건", "목록 조회", "등록일 역순 5건", "변화 없음", "UT-001", "", "", ""],
        ["UT-005", "FN-002", "RE-002", "〃", "메모 2,001자", "\"2,000자 이내\" 안내 [가정:2000]", "변화 없음", "없음", "", "", ""],
        ["UT-006", "", "RE-050", "300MB 파일", "응답시간 측정", "30초 이내", "측정 로그", "없음", "", "", ""],
        ["UT-007", "FN-002", "RE-002", "(규격 미정)", "파싱 검증", "[미확정] 규격 없음", "검증 보류", "없음", "", "", ""],
        ["UT-008", "FN-001", "RE-001", "상한 초과", "다운로드", "\"조건을 좁혀\" 안내", "변화 없음", "없음", "", "", ""],
    ]


def _cell(ref: str, value: str, shared_index: dict | None, style: str | None, runs: list | None) -> str:
    s = f' s="{style}"' if style else ""
    if runs is not None:
        rich = "".join(f"<r><t>{escape(t)}</t></r>" for t in runs)
        return f'<c r="{ref}"{s} t="inlineStr"><is>{rich}</is></c>'
    if value == "":
        return f'<c r="{ref}"{s}/>'
    if shared_index is not None:
        idx = shared_index.setdefault(value, len(shared_index))
        return f'<c r="{ref}"{s} t="s"><v>{idx}</v></c>'
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def _col(i: int) -> str:
    i += 1
    out = ""
    while i:
        i, r = divmod(i - 1, 26)
        out = chr(65 + r) + out
    return out


def _sheet_xml(rows, shared_index, validation, style, rich):
    body = []
    for r, values in enumerate(rows, start=1):
        cells = "".join(
            _cell(f"{_col(c)}{r}", v, shared_index, style, rich.get(f"{_col(c)}{r}"))
            for c, v in enumerate(values))
        body.append(f'<row r="{r}">{cells}</row>')
    dv = ""
    if validation:
        dv = (f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" '
              f'sqref="{validation}"><formula1>"Pass,Fail"</formula1></dataValidation></dataValidations>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(body)}</sheetData>{dv}</worksheet>')


def make_xlsx(path: Path, sheets, shared=False, validation=None, style=None, rich=None):
    """sheets: [(시트명, [[셀값,...],...]), ...].
    shared=True면 공유 문자열(엑셀 재저장 형식), validation은 첫 시트의 결과 열 데이터 검증 범위,
    style은 모든 셀의 s 속성, rich={"D2": ["앞", "뒤"]}는 첫 시트의 해당 셀을 서식 런으로 쓴다."""
    shared_index = {} if shared else None
    sheet_parts = []
    for n, (name, rows) in enumerate(sheets, start=1):
        xml = _sheet_xml(rows, shared_index, validation if n == 1 else None, style,
                         (rich or {}) if n == 1 else {})
        sheet_parts.append((name, f"xl/worksheets/sheet{n}.xml", xml))
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
                   f'<sheets>{sheets_xml}</sheets></workbook>')
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

- [ ] **Step 2: scope 실패 테스트 작성**

`tests/test_de13_scope.py`:

```python
"""de13.py scope: 계획서 읽기와 ut-floor 생성."""
import json
import tempfile
import unittest
from pathlib import Path

from de13_support import PLAN_HEADER_11, load_de13, make_xlsx, sample_rows

de13 = load_de13()


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 scope 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def plan(self, rows=None, **kw):
        rows = sample_rows() if rows is None else rows
        sheets = kw.pop("sheets", None) or [("개정이력", [["버전"], ["1.0"]]),
                                            ("단위테스트계획", [PLAN_HEADER_11, *rows])]
        return make_xlsx(self.dir / "REB-단위테스트계획서.xlsx", sheets, **kw)

    def test_reads_inline_strings_and_resolves_ditto_within_same_function(self):
        plan = de13.load_plan(self.plan())
        rows = {r["테스트ID"]: r for r in plan["rows"]}
        self.assertEqual(plan["sheet"], "단위테스트계획")
        self.assertEqual(rows["UT-002"]["사전조건"], "신규 프로젝트")
        self.assertEqual(rows["UT-003"]["사전조건"], "신규 프로젝트")
        self.assertEqual(rows["UT-005"]["사전조건"], "회차 5건")
        self.assertEqual(rows["UT-002"]["_row"], 3)

    def test_ditto_across_function_boundary_is_not_resolved(self):
        rows = sample_rows()
        rows[3][3] = "〃"  # UT-004(FN-002) 사전조건이 위 행(FN-001)을 가리킴
        plan = de13.load_plan(self.plan(rows))
        rec = next(r for r in plan["rows"] if r["테스트ID"] == "UT-004")
        self.assertEqual(rec["사전조건"], "〃")
        self.assertIn("〃미해결", rec["_flags"])

    def test_reads_shared_strings_and_rich_runs(self):
        plan = de13.load_plan(self.plan(shared=True))
        self.assertEqual(next(r for r in plan["rows"] if r["테스트ID"] == "UT-008")["기대결과"], "\"조건을 좁혀\" 안내")
        plan2 = de13.load_plan(self.plan(rich={"D2": ["신규 ", "프로젝트"]}))
        self.assertEqual(plan2["rows"][0]["사전조건"], "신규 프로젝트")

    def test_finds_header_by_name_with_title_row_renamed_sheet_and_12_columns(self):
        header12 = PLAN_HEADER_11[:3] + ["요구사항명"] + PLAN_HEADER_11[3:]
        rows12 = [r[:3] + ["원천 데이터 등록"] + r[3:] for r in sample_rows()]
        sheets = [("시험계획", [["단위테스트계획서"], [], header12, *rows12])]
        plan = de13.load_plan(self.plan(sheets=sheets))
        self.assertEqual(plan["sheet"], "시험계획")
        self.assertEqual(plan["cols"]["요구사항명"], 3)
        self.assertEqual(plan["rows"][0]["_row"], 4)

    def test_missing_required_column_is_input_error(self):
        header = [h for h in PLAN_HEADER_11 if h != "사후조건"]
        sheets = [("단위테스트계획", [header, ["UT-001", "FN-001"]])]
        with self.assertRaisesRegex(de13.InputError, "사후조건"):
            de13.load_plan(self.plan(sheets=sheets))

    def test_floor_selects_function_rows_by_id_not_range_and_marks_rows(self):
        plan = de13.load_plan(self.plan())
        floor = {r["테스트ID"]: r for r in de13.build_floor(plan, ["FN-001", "FN-002"])}
        self.assertEqual(sorted(floor), ["UT-001", "UT-002", "UT-003", "UT-004", "UT-005", "UT-007", "UT-008"])
        self.assertNotIn("UT-006", floor)  # 비기능(연계기능ID 공란)
        self.assertEqual(floor["UT-007"]["판정"], "제외(미확정 행)")
        self.assertEqual(floor["UT-001"]["판정"], "대상")
        self.assertIn("가정", floor["UT-005"]["표식"])
        self.assertIn("타기능 의존", floor["UT-004"]["표식"])  # FN-002가 FN-001의 UT-001에 의존
        self.assertNotIn("타기능 의존", floor["UT-003"]["표식"])

    def test_fingerprint_ignores_whitespace_and_excludes_test_id(self):
        a = {"테스트ID": "UT-1", "사전조건": "a  b", "입력": " x", "기대결과": "y", "사후조건": "z"}
        b = {"테스트ID": "UT-9", "사전조건": "a b", "입력": "x ", "기대결과": "y", "사후조건": "z"}
        c = dict(b, 기대결과="y2")
        self.assertEqual(de13.row_fingerprint(a), de13.row_fingerprint(b))
        self.assertNotEqual(de13.row_fingerprint(b), de13.row_fingerprint(c))
        self.assertRegex(de13.row_fingerprint(a), r"^[0-9a-f]{8}$")

    def test_cli_writes_floor_and_round_trips_through_md_parser(self):
        path = self.plan()
        out = self.dir / ".dev" / "feat-x" / "ut-floor.md"
        code = de13.main(["scope", "--plan", str(path), "--fn", "FN-001", "--out", str(out), "--date", "2026-10-12"])
        self.assertEqual(code, 0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("- 범위: FN-001", text)
        self.assertIn("- 생성: 2026-10-12", text)
        rows = de13.read_md_table(out)
        self.assertEqual([r["테스트ID"] for r in rows], ["UT-001", "UT-002", "UT-003", "UT-008"])
        self.assertEqual(rows[1]["기대결과"], "\"파일 용량 초과\" 안내")
        self.assertEqual(list(rows[0]), de13.FLOOR_HEADER)

    def test_pipe_and_newline_survive_md_round_trip(self):
        rows = sample_rows()
        rows[0][5] = "A | B\n둘째 줄"
        out = self.dir / "floor.md"
        de13.main(["scope", "--plan", str(self.plan(rows)), "--fn", "FN-001", "--out", str(out), "--date", "2026-10-12"])
        self.assertEqual(de13.read_md_table(out)[0]["기대결과"], "A | B\n둘째 줄")

    def test_cli_unknown_function_returns_2(self):
        code = de13.main(["scope", "--plan", str(self.plan()), "--fn", "FN-999", "--out", str(self.dir / "f.md")])
        self.assertEqual(code, 2)
        self.assertFalse((self.dir / "f.md").exists())

    def test_cli_without_fn_writes_function_list_json(self):
        spec = make_xlsx(self.dir / "REB-기능명세서.xlsx",
                         [("기능명세", [["기능ID", "대분류", "기능명"], ["FN-001", "전처리", "원천 데이터 등록"]])])
        out = self.dir / "functions.json"
        code = de13.main(["scope", "--plan", str(self.plan()), "--spec", str(spec), "--out", str(out)])
        self.assertEqual(code, 0)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data[0], {"기능ID": "FN-001", "UT수": 4, "기능명": "원천 데이터 등록"})
        self.assertEqual(data[1], {"기능ID": "FN-002", "UT수": 3, "기능명": ""})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_scope.py" -v`
Expected: 로드 단계에서 FAIL/ERROR (`FileNotFoundError` 또는 `No such file` — `de13.py` 없음)

- [ ] **Step 4: de13.py 작성 (공통부 + scope)**

`.claude/skills/gx-test-plan/scripts/de13.py`:

```python
#!/usr/bin/env python3
"""DE-13 단위테스트계획서(xlsx) 연동 헬퍼 — Python 3.10 표준 라이브러리 전용.

scope  : 계획서에서 기능별 UT 행을 뽑아 ut-floor.md를 쓴다 (--fn 생략 시 기능 목록 JSON)
check  : ut-floor의 '대상' UT ID가 테스트 소스에 skip 없이 존재하는지 확인한다
record : check 결과로 기능별 결과 원장을 갱신한다
apply  : 원장을 계획서 xlsx 사본의 결과·수행일·테스트담당자 열에 반영한다
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
M = "{%s}" % NS_MAIN

DATA_SHEET = "단위테스트계획"
REQUIRED = ("테스트ID", "연계기능ID", "사전조건", "입력", "기대결과", "사후조건",
            "의존성", "테스트담당자", "수행일", "결과")
FIELDS4 = ("사전조건", "입력", "기대결과", "사후조건")
DITTO = "〃"
FLOOR_HEADER = ["테스트ID", "기능ID", "사전조건", "입력", "기대결과", "사후조건",
                "의존성", "표식", "판정", "행 지문"]
LEDGER_HEADER = ["테스트ID", "상태", "수행일", "담당자", "테스트 위치", "행 지문", "비고"]


class InputError(Exception):
    """입력 파일·인자 오류 (종료 코드 2)."""


# ---------- xlsx 읽기 ----------

def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _col_letters(idx: int) -> str:
    idx += 1
    out = ""
    while idx:
        idx, r = divmod(idx - 1, 26)
        out = chr(65 + r) + out
    return out


def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(M + "t"))


class Workbook:
    def __init__(self, path: Path):
        try:
            self.zip = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise InputError(f"xlsx를 열 수 없습니다: {path} ({exc})") from exc
        names = set(self.zip.namelist())
        self.shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            sst = ET.fromstring(self.zip.read("xl/sharedStrings.xml"))
            self.shared = [_text(si) for si in sst.findall(M + "si")]
        wb = ET.fromstring(self.zip.read("xl/workbook.xml"))
        rels = ET.fromstring(self.zip.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        self.sheets: list[tuple[str, str]] = []
        for s in wb.find(M + "sheets"):
            target = targets[s.get("{%s}id" % NS_REL)]
            part = target.lstrip("/") if target.startswith("/") else "xl/" + target
            self.sheets.append((s.get("name"), part))

    def close(self) -> None:
        self.zip.close()

    def rows(self, part: str) -> list[tuple[int, dict[int, str]]]:
        root = ET.fromstring(self.zip.read(part))
        out = []
        for n, row in enumerate(root.iter(M + "row"), start=1):
            rnum = int(row.get("r") or n)
            cells: dict[int, str] = {}
            for pos, c in enumerate(row.findall(M + "c")):
                idx = _col_index(c.get("r")) if c.get("r") else pos
                t = c.get("t")
                if t == "inlineStr":
                    is_ = c.find(M + "is")
                    value = _text(is_) if is_ is not None else ""
                elif t == "s":
                    v = c.find(M + "v")
                    value = self.shared[int(v.text)] if v is not None and v.text else ""
                else:
                    v = c.find(M + "v")
                    value = v.text if v is not None and v.text else ""
                cells[idx] = value
            out.append((rnum, cells))
        return out


def _find_table(wb: Workbook, must: tuple[str, ...]):
    order = sorted(wb.sheets, key=lambda s: s[0] != DATA_SHEET)
    for name, part in order:
        rows = wb.rows(part)
        for i, (_, cells) in enumerate(rows):
            heads = {v.strip(): k for k, v in cells.items() if v and v.strip()}
            if all(h in heads for h in must[:2]):
                missing = [h for h in must if h not in heads]
                if missing:
                    raise InputError(f"필수 열 없음: {', '.join(missing)} (시트: {name})")
                return name, part, heads, rows[i + 1:]
    raise InputError(f"머리글({', '.join(must[:2])})을 찾을 수 없습니다")


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def load_plan(path: Path) -> dict:
    wb = Workbook(Path(path))
    try:
        sheet, part, cols, body = _find_table(wb, REQUIRED)
    finally:
        wb.close()  # Windows에서 핸들이 남으면 임시 폴더 정리·덮어쓰기가 실패한다
    rows: list[dict] = []
    prev: dict | None = None
    for rnum, cells in body:
        rec = {h: (cells.get(i, "") or "").strip() for h, i in cols.items()}
        if not rec.get("테스트ID"):
            continue
        rec["_row"] = rnum
        rec["_flags"] = []
        for h in cols:
            if rec[h] == DITTO and prev and rec["연계기능ID"] and prev["연계기능ID"] == rec["연계기능ID"]:
                rec[h] = prev[h]
            if rec[h] == DITTO and "〃미해결" not in rec["_flags"]:
                rec["_flags"].append("〃미해결")
        rows.append(rec)
        prev = rec
    return {"sheet": sheet, "part": part, "cols": cols, "rows": rows, "sha": file_sha(Path(path))}


def row_fingerprint(rec: dict) -> str:
    parts = [re.sub(r"\s+", " ", rec.get(f, "") or "").strip() for f in FIELDS4]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:8]


def _undecided(rec: dict) -> bool:
    return any("[미확정" in (rec.get(h) or "") for h in rec if not h.startswith("_"))


def build_floor(plan: dict, fn_ids: list[str]) -> list[dict]:
    known = {r["연계기능ID"] for r in plan["rows"] if r["연계기능ID"]}
    unknown = [f for f in fn_ids if f not in known]
    if unknown:
        raise InputError(f"계획서에 없는 기능ID: {', '.join(unknown)}")
    fn_of = {r["테스트ID"]: r["연계기능ID"] for r in plan["rows"]}
    floor = []
    for rec in plan["rows"]:
        if rec["연계기능ID"] not in fn_ids:
            continue
        marks = list(rec["_flags"])
        if "[가정" in " ".join(rec.get(f, "") for f in FIELDS4):
            marks.append("가정")
        deps = re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", rec.get("의존성", ""))
        if any(d in fn_of and fn_of[d] != rec["연계기능ID"] for d in deps):
            marks.append("타기능 의존")
        floor.append({
            "테스트ID": rec["테스트ID"], "기능ID": rec["연계기능ID"],
            **{f: rec.get(f, "") for f in FIELDS4}, "의존성": rec.get("의존성", ""),
            "표식": ", ".join(marks),
            "판정": "제외(미확정 행)" if _undecided(rec) else "대상",
            "행 지문": row_fingerprint(rec),
        })
    return floor


# ---------- 마크다운 표 ----------

def _md_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def write_md_table(header: list[str], rows: list[dict]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        lines.append("| " + " | ".join(_md_cell(r.get(h, "")) for h in header) + " |")
    return "\n".join(lines) + "\n"


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, i = [], [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if s[i] == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(s[i])
        i += 1
    cells.append("".join(cur).strip())
    return [c.replace("<br>", "\n") for c in cells]


def read_md_table(path: Path) -> list[dict[str, str]]:
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            if header is not None:
                break
            continue
        cells = _split_row(line)
        if header is None:
            header = cells
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def write_floor(path: Path, source: str, plan: dict, fn_ids: list[str], rows: list[dict], date: str) -> None:
    head = ("# UT 하한선\n\n"
            f"- 출처: {source} (시트: {plan['sheet']}, sha256: {plan['sha']})\n"
            f"- 범위: {', '.join(fn_ids)}\n"
            f"- 생성: {date}\n\n")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(head + write_md_table(FLOOR_HEADER, rows), encoding="utf-8")


def function_list(plan: dict, spec: Path | None) -> list[dict]:
    names: dict[str, str] = {}
    if spec:
        try:
            wb = Workbook(Path(spec))
            try:
                _, _, cols, body = _find_table(wb, ("기능ID", "기능명"))
            finally:
                wb.close()
            for _, cells in body:
                fid = (cells.get(cols["기능ID"], "") or "").strip()
                if fid:
                    names[fid] = (cells.get(cols["기능명"], "") or "").strip()
        except InputError:
            names = {}
    counts: dict[str, int] = {}
    for r in plan["rows"]:
        if r["연계기능ID"]:
            counts[r["연계기능ID"]] = counts.get(r["연계기능ID"], 0) + 1
    return [{"기능ID": f, "UT수": n, "기능명": names.get(f, "")} for f, n in counts.items()]


# ---------- 명령 ----------

def cmd_scope(args) -> int:
    plan = load_plan(Path(args.plan))
    out = Path(args.out)
    if not args.fn:
        functions = function_list(plan, Path(args.spec) if args.spec else None)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(functions, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"기능 {len(functions)}개 목록을 {out}에 썼습니다")
        return 0
    fn_ids = [f.strip() for f in args.fn.split(",") if f.strip()]
    rows = build_floor(plan, fn_ids)
    write_floor(out, Path(args.plan).as_posix(), plan, fn_ids, rows, args.date)
    target = sum(1 for r in rows if r["판정"] == "대상")
    print(f"하한선 {len(rows)}행(대상 {target})을 {out}에 썼습니다")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="de13", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scope")
    s.add_argument("--plan", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--fn")
    s.add_argument("--spec")
    s.add_argument("--date", default=_dt.date.today().isoformat())
    s.set_defaults(func=cmd_scope)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"de13: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_scope.py" -v`
Expected: 11 tests OK

- [ ] **Step 6: 커밋**

`/gx-commit` 스킬로 커밋한다. 메시지: `feat: DE-13 계획서 읽기와 하한선(scope) 헬퍼를 추가한다`

---

### Task 2: `check` 명령 — 테스트 소스에서 UT ID 찾기

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py` (상수·함수·서브커맨드 추가)
- Test: `tests/test_de13_check.py`

**Interfaces:**
- Consumes: `read_md_table`, `FLOOR_HEADER`, `InputError`, `main` (Task 1)
- Produces: `check_floor(floor_rows: list[dict], root: Path) -> dict` — 반환 `{"results": {ID: {"status": "found"|"missing"|"skipped", "locations": [{"path": str, "line": int, "skipped": bool}]}}, "summary": {"found": int, "missing": int, "skipped": int}}`. `판정`이 `대상`인 행만 검사한다. CLI `check --floor F --root R --out O` 종료 코드 0/1/2.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_de13_check.py`:

```python
"""de13.py check: 테스트 소스의 UT ID 존재·skip 판정."""
import json
import tempfile
import unittest
from pathlib import Path

from de13_support import load_de13

de13 = load_de13()


def floor_rows(*ids, verdict="대상"):
    return [{"테스트ID": i, "기능ID": "FN-001", "판정": verdict} for i in ids]


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 check 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def status(self, test_id, rows=None):
        result = de13.check_floor(rows or floor_rows(test_id), self.root)
        return result["results"][test_id]

    def test_finds_display_name_and_underscore_forms(self):
        self.write("src/test/java/a/SourceTest.java",
                   '@Test\n@DisplayName("REB-UT-002 용량 초과 차단")\nvoid a() {}\n'
                   '@Test\nvoid REB_UT_003_정확히_상한() {}\n')
        self.write("tests/test_memo.py", "def test_REB_UT_005_빈_메모():\n    pass\n")
        self.write("web/src/memo.spec.ts", "it('REB-UT-006 2001자 차단', () => {})\n")
        rows = floor_rows("REB-UT-002", "REB-UT-003", "REB-UT-005", "REB-UT-006")
        res = de13.check_floor(rows, self.root)["results"]
        self.assertEqual({k: v["status"] for k, v in res.items()},
                         {"REB-UT-002": "found", "REB-UT-003": "found", "REB-UT-005": "found", "REB-UT-006": "found"})
        self.assertEqual(res["REB-UT-002"]["locations"][0],
                         {"path": "src/test/java/a/SourceTest.java", "line": 2, "skipped": False})

    def test_id_boundary_does_not_match_longer_id(self):
        self.write("src/test/XTest.java", '@Test @DisplayName("REB-UT-0021 다른 케이스") void a() {}\n')
        self.assertEqual(self.status("REB-UT-002")["status"], "missing")

    def test_method_level_disabled_is_skipped(self):
        self.write("src/test/XTest.java",
                   '@Disabled\n@Test\n@DisplayName("REB-UT-002 차단")\nvoid a() {}\n'
                   '@Test\n@DisplayName("REB-UT-003 통과")\nvoid b() {}\n')
        self.assertEqual(self.status("REB-UT-002")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-003")["status"], "found")

    def test_js_and_python_skip_markers(self):
        self.write("a.test.js", "it.skip('REB-UT-010 x', () => {})\nxit('REB-UT-011 y', () => {})\nit('REB-UT-012 z', () => {})\n")
        self.write("tests/test_b.py", "@pytest.mark.skip(reason='x')\ndef test_REB_UT_013():\n    pass\n")
        self.assertEqual(self.status("REB-UT-010")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-011")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-012")["status"], "found")
        self.assertEqual(self.status("REB-UT-013")["status"], "skipped")

    def test_class_level_disabled_skips_file(self):
        self.write("src/test/YTest.java",
                   'import x;\n@Disabled\nclass YTest {\n  @Test\n  @DisplayName("REB-UT-020 a")\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-020")["status"], "skipped")

    def test_found_wins_when_one_location_is_not_skipped(self):
        self.write("src/test/ATest.java", '@Disabled\n@Test\n@DisplayName("REB-UT-030")\nvoid a() {}\n')
        self.write("src/test/BTest.java", '@Test\n@DisplayName("REB-UT-030")\nvoid b() {}\n')
        res = self.status("REB-UT-030")
        self.assertEqual(res["status"], "found")
        self.assertEqual(len(res["locations"]), 2)

    def test_ignores_non_test_files_build_dirs_and_dev(self):
        self.write("src/main/java/Service.java", '// REB-UT-040\n')
        self.write("build/test/GenTest.java", '@Test @DisplayName("REB-UT-040") void a() {}\n')
        self.write("node_modules/x/test/a.test.js", "it('REB-UT-040', () => {})\n")
        self.write(".dev/feat-x/ut-floor.md", "| REB-UT-040 |\n")
        self.write("docs/test-notes.md", "REB-UT-040\n")
        self.assertEqual(self.status("REB-UT-040")["status"], "missing")

    def test_only_target_rows_are_checked(self):
        rows = floor_rows("REB-UT-050") + floor_rows("REB-UT-051", verdict="제외(대용량)")
        res = de13.check_floor(rows, self.root)
        self.assertEqual(list(res["results"]), ["REB-UT-050"])

    def test_cli_exit_codes_and_json(self):
        floor = self.root / ".dev/feat-x/ut-floor.md"
        floor.parent.mkdir(parents=True)
        floor.write_text(de13.write_md_table(de13.FLOOR_HEADER, [
            {"테스트ID": "REB-UT-060", "기능ID": "FN-001", "판정": "대상"}]), encoding="utf-8")
        out = self.root / ".dev/feat-x/ut-check.json"
        self.assertEqual(de13.main(["check", "--floor", str(floor), "--root", str(self.root), "--out", str(out)]), 1)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["summary"]["missing"], 1)
        self.write("src/test/ZTest.java", '@Test @DisplayName("REB-UT-060") void a() {}\n')
        self.assertEqual(de13.main(["check", "--floor", str(floor), "--root", str(self.root), "--out", str(out)]), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_check.py" -v`
Expected: ERROR `AttributeError: module 'de13' has no attribute 'check_floor'`

- [ ] **Step 3: check 구현**

`de13.py`의 `# ---------- 명령 ----------` 줄 **위**에 추가:

```python
# ---------- 테스트 소스 검사 ----------

SKIP_DIRS = {"node_modules", "build", "dist", "target", ".gradle", "out", ".git", ".dev",
             ".idea", ".venv", "venv", "__pycache__", ".next", ".nuxt"}
TEST_DIRS = {"test", "tests", "__tests__", "spec"}
SOURCE_EXT = {".java", ".kt", ".kts", ".groovy", ".scala", ".js", ".jsx", ".ts", ".tsx", ".mjs",
              ".cjs", ".py", ".go", ".cs", ".rb", ".php", ".rs", ".c", ".cc", ".cpp", ".swift"}
TEST_FILE_RE = re.compile(r"(Tests?\.[^.]+$)|(\.(test|spec)\.[^.]+$)|(^test_.*\.py$)|(_test\.[^.]+$)")
DECL_RE = re.compile(
    r"@Test\b|@ParameterizedTest\b|@RepeatedTest\b|@TestFactory\b"
    r"|\b[xf]?(?:it|test)\s*(?:\.\s*(?:skip|only|each)\s*)?\("
    r"|\bdef test_|\bfunc Test|\[(?:Fact|Theory|Test)\b")
SKIP_RE = re.compile(
    r"@Disabled\b|@Ignore\b|\.\s*skip\s*\(|\bxit\s*\(|\bxtest\s*\(|\bxdescribe\s*\("
    r"|@pytest\.mark\.skip|@unittest\.skip|\bt\.Skip\(|\bSkip\s*=")
CLASS_RE = re.compile(r"\bclass\s+\w+|\b[x]?describe\s*(?:\.\s*skip\s*)?\(")


def _annotation_block_start(lines: list[str], j: int) -> int:
    k = j
    while k - 1 >= 0 and lines[k - 1].strip().startswith(("@", "[")):
        k -= 1
    return k


def _file_skipped(lines: list[str]) -> bool:
    for k, line in enumerate(lines):
        if CLASS_RE.search(line):
            start = _annotation_block_start(lines, k)
            return any(SKIP_RE.search(l) for l in lines[start:k + 1])
    return False


def _is_skipped(lines: list[str], i: int) -> bool:
    j = i
    while j >= 0 and not DECL_RE.search(lines[j]):
        j -= 1
    if j < 0:
        return False
    start = _annotation_block_start(lines, j)
    return any(SKIP_RE.search(l) for l in lines[start:i + 1])


def iter_test_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        in_test_dir = any(part in TEST_DIRS for part in rel_dir.parts)
        for name in filenames:
            if Path(name).suffix.lower() not in SOURCE_EXT:
                continue
            if in_test_dir or TEST_FILE_RE.search(name):
                yield Path(dirpath) / name, (rel_dir / name).as_posix()


def _id_pattern(test_id: str) -> re.Pattern:
    raw, under = re.escape(test_id), re.escape(test_id.replace("-", "_"))
    return re.compile(rf"(?<![A-Za-z0-9-])(?:{raw}|{under})(?![0-9A-Za-z])")


def check_floor(floor_rows: list[dict], root: Path) -> dict:
    targets = [r["테스트ID"] for r in floor_rows if r.get("판정") == "대상"]
    patterns = {t: _id_pattern(t) for t in targets}
    found: dict[str, list[dict]] = {t: [] for t in targets}
    for path, rel in iter_test_files(Path(root)):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        whole = _file_skipped(lines)
        for i, line in enumerate(lines):
            for t, pat in patterns.items():
                if pat.search(line):
                    found[t].append({"path": rel, "line": i + 1,
                                     "skipped": whole or _is_skipped(lines, i)})
    results, summary = {}, {"found": 0, "missing": 0, "skipped": 0}
    for t in targets:
        locs = sorted(found[t], key=lambda l: (l["path"], l["line"]))
        status = "missing" if not locs else ("found" if any(not l["skipped"] for l in locs) else "skipped")
        summary[status] += 1
        results[t] = {"status": status, "locations": locs}
    return {"results": results, "summary": summary}


def cmd_check(args) -> int:
    floor = Path(args.floor)
    if not floor.is_file():
        raise InputError(f"ut-floor 파일이 없습니다: {floor}")
    result = check_floor(read_md_table(floor), Path(args.root))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    s = result["summary"]
    print(f"found {s['found']} · missing {s['missing']} · skipped {s['skipped']}")
    return 0 if s["missing"] == 0 and s["skipped"] == 0 else 1
```

`build_parser()`의 `return p` 위에 추가:

```python
    c = sub.add_parser("check")
    c.add_argument("--floor", required=True)
    c.add_argument("--root", required=True)
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_check)
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v`
Expected: scope 11 + check 9 = 20 tests OK

- [ ] **Step 5: 커밋**

`/gx-commit`. 메시지: `feat: 테스트 소스에서 UT ID와 skip 표식을 찾는 check 명령을 추가한다`

---

### Task 3: `record` 명령 — 기능별 결과 원장

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py`
- Test: `tests/test_de13_record.py`

**Interfaces:**
- Consumes: `read_md_table`, `write_md_table`, `FLOOR_HEADER`, `LEDGER_HEADER`, `InputError` (Task 1), check JSON 형식 (Task 2)
- Produces: `record(floor_rows: list[dict], check: dict, ledger_dir: Path, date: str, tester: str) -> list[Path]` (갱신한 원장 경로). 원장 파일 `{ledger_dir}/{기능ID}.md` — 제목 `# {기능ID} 단위테스트 결과 원장` + `LEDGER_HEADER` 표. CLI `record --floor --check --ledger-dir --date --tester` 종료 코드 0/2.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_de13_record.py`:

```python
"""de13.py record: 기능별 결과 원장 갱신."""
import json
import tempfile
import unittest
from pathlib import Path

from de13_support import load_de13

de13 = load_de13()


def floor_row(tid, fn="FN-001", verdict="대상", fp="aaaa0001"):
    return {"테스트ID": tid, "기능ID": fn, "판정": verdict, "행 지문": fp}


def check_of(**status):
    return {"results": {k.replace("_", "-"): {"status": v, "locations": [{"path": "src/test/A.java", "line": 3, "skipped": False}] if v == "found" else []}
                        for k, v in status.items()}}


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 record ")
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / ".dev" / "ut-results"

    def test_records_pass_exclusion_and_transfer_per_function(self):
        floor = [floor_row("UT-001"), floor_row("UT-002", verdict="제외(1,001MB 실파일 필요)"),
                 floor_row("UT-003", verdict="이관(W03)"), floor_row("UT-010", fn="FN-002")]
        paths = de13.record(floor, check_of(UT_001="found", UT_010="found"), self.ledger, "2026.10.12", "bs.koo")
        self.assertEqual(sorted(p.name for p in paths), ["FN-001.md", "FN-002.md"])
        text = (self.ledger / "FN-001.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# FN-001 단위테스트 결과 원장\n"))
        rows = {r["테스트ID"]: r for r in de13.read_md_table(self.ledger / "FN-001.md")}
        self.assertEqual(rows["UT-001"], {"테스트ID": "UT-001", "상태": "Pass", "수행일": "2026.10.12", "담당자": "bs.koo",
                                          "테스트 위치": "src/test/A.java:3", "행 지문": "aaaa0001", "비고": ""})
        self.assertEqual(rows["UT-002"]["상태"], "제외")
        self.assertEqual(rows["UT-002"]["비고"], "1,001MB 실파일 필요")
        self.assertEqual(rows["UT-003"]["상태"], "이관(W03)")
        self.assertEqual(rows["UT-003"]["수행일"], "")

    def test_preserves_rows_outside_scope_and_overwrites_same_id(self):
        de13.record([floor_row("UT-001"), floor_row("UT-005")], check_of(UT_001="found", UT_005="found"),
                    self.ledger, "2026.10.01", "kim")
        de13.record([floor_row("UT-001", fp="bbbb0002")], check_of(UT_001="found"), self.ledger, "2026.10.12", "bs.koo")
        rows = {r["테스트ID"]: r for r in de13.read_md_table(self.ledger / "FN-001.md")}
        self.assertEqual(rows["UT-005"]["수행일"], "2026.10.01")
        self.assertEqual(rows["UT-001"]["수행일"], "2026.10.12")
        self.assertEqual(rows["UT-001"]["행 지문"], "bbbb0002")
        self.assertEqual(list(rows), ["UT-001", "UT-005"])

    def test_refuses_when_target_is_missing_or_skipped(self):
        with self.assertRaisesRegex(de13.InputError, "UT-001"):
            de13.record([floor_row("UT-001")], check_of(UT_001="missing"), self.ledger, "2026.10.12", "x")
        with self.assertRaisesRegex(de13.InputError, "UT-002"):
            de13.record([floor_row("UT-002")], check_of(UT_002="skipped"), self.ledger, "2026.10.12", "x")
        self.assertFalse(self.ledger.exists())

    def test_rejects_unknown_verdict(self):
        with self.assertRaisesRegex(de13.InputError, "판정"):
            de13.record([floor_row("UT-001", verdict="보류")], check_of(), self.ledger, "2026.10.12", "x")

    def test_cli(self):
        base = Path(self.tmp.name)
        floor = base / "ut-floor.md"
        floor.write_text(de13.write_md_table(de13.FLOOR_HEADER, [floor_row("UT-001")]), encoding="utf-8")
        check = base / "ut-check.json"
        check.write_text(json.dumps(check_of(UT_001="found")), encoding="utf-8")
        code = de13.main(["record", "--floor", str(floor), "--check", str(check), "--ledger-dir", str(self.ledger),
                          "--date", "2026.10.12", "--tester", "bs.koo"])
        self.assertEqual(code, 0)
        self.assertTrue((self.ledger / "FN-001.md").is_file())
        bad = de13.main(["record", "--floor", str(floor), "--check", str(base / "none.json"),
                         "--ledger-dir", str(self.ledger), "--date", "2026.10.12", "--tester", "x"])
        self.assertEqual(bad, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_record.py" -v`
Expected: ERROR `AttributeError: module 'de13' has no attribute 'record'`

- [ ] **Step 3: record 구현**

`# ---------- 명령 ----------` 줄 위에 추가:

```python
# ---------- 결과 원장 ----------

VERDICT_RE = re.compile(r"^(대상|제외\((?P<reason>.+)\)|이관\((?P<work>W\d{2,})\))$")


def _ledger_path(ledger_dir: Path, fn: str) -> Path:
    return Path(ledger_dir) / f"{fn}.md"


def _read_ledger(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    return {r["테스트ID"]: r for r in read_md_table(path) if r.get("테스트ID")}


def _write_ledger(path: Path, fn: str, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [rows[k] for k in sorted(rows)]
    path.write_text(f"# {fn} 단위테스트 결과 원장\n\n" + write_md_table(LEDGER_HEADER, ordered), encoding="utf-8")


def record(floor_rows: list[dict], check: dict, ledger_dir: Path, date: str, tester: str) -> list[Path]:
    results = check.get("results", {})
    entries: dict[str, list[dict]] = {}
    problems = []
    for r in floor_rows:
        m = VERDICT_RE.match(r.get("판정", ""))
        if not m:
            raise InputError(f"알 수 없는 판정 '{r.get('판정', '')}' ({r.get('테스트ID')})")
        base = {"테스트ID": r["테스트ID"], "상태": "", "수행일": "", "담당자": "",
                "테스트 위치": "", "행 지문": r.get("행 지문", ""), "비고": ""}
        if m.group(1) == "대상":
            res = results.get(r["테스트ID"], {"status": "missing", "locations": []})
            if res["status"] != "found":
                problems.append(f"{r['테스트ID']}({res['status']})")
                continue
            loc = next(l for l in res["locations"] if not l["skipped"])
            base.update({"상태": "Pass", "수행일": date, "담당자": tester,
                         "테스트 위치": f"{loc['path']}:{loc['line']}"})
        elif m.group("reason"):
            base.update({"상태": "제외", "비고": m.group("reason")})
        else:
            base.update({"상태": f"이관({m.group('work')})"})
        entries.setdefault(r["기능ID"], []).append(base)
    if problems:
        raise InputError("하한선 미충족 상태에서는 기록하지 않습니다: " + ", ".join(problems))
    written = []
    for fn, rows in entries.items():
        path = _ledger_path(ledger_dir, fn)
        merged = _read_ledger(path)
        for row in rows:
            merged[row["테스트ID"]] = row
        _write_ledger(path, fn, merged)
        written.append(path)
    return written


def cmd_record(args) -> int:
    floor, check = Path(args.floor), Path(args.check)
    for p in (floor, check):
        if not p.is_file():
            raise InputError(f"파일이 없습니다: {p}")
    paths = record(read_md_table(floor), json.loads(check.read_text(encoding="utf-8")),
                   Path(args.ledger_dir), args.date, args.tester)
    print("원장 갱신: " + ", ".join(p.name for p in paths))
    return 0
```

`build_parser()`에 추가:

```python
    r = sub.add_parser("record")
    r.add_argument("--floor", required=True)
    r.add_argument("--check", required=True)
    r.add_argument("--ledger-dir", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--tester", required=True)
    r.set_defaults(func=cmd_record)
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v`
Expected: 25 tests OK

- [ ] **Step 5: 커밋**

`/gx-commit`. 메시지: `feat: 하한선 통과 결과를 기능별 원장에 기록하는 record 명령을 추가한다`

---

### Task 4: `apply` 명령 — 계획서 사본 반영과 CI 등록

**Files:**
- Modify: `.claude/skills/gx-test-plan/scripts/de13.py`
- Modify: `.github/workflows/lint.yml`
- Test: `tests/test_de13_apply.py`

**Interfaces:**
- Consumes: `load_plan`, `row_fingerprint`, `read_md_table`, `_col_letters`, `InputError` (Task 1), 원장 형식 (Task 3)
- Produces: `apply(plan_path: Path, ledger_dir: Path, testers: dict[str, str], out: Path) -> dict` — 요약 dict (`기능별`, `재확인 필요`, `계획서에 없음`, `매핑 없는 담당자`, `output`). 매핑 없는 담당자가 있으면 파일을 쓰지 않고 요약만 반환한다. `read_testers(path: Path) -> dict[str, str]`. CLI `apply --plan --ledger-dir --testers --out --report` 종료 코드 0/2/3.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_de13_apply.py`:

```python
"""de13.py apply: 원장을 계획서 사본에 반영."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from de13_support import PLAN_HEADER_11, load_de13, make_xlsx, sample_rows

de13 = load_de13()


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 apply 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.plan_path = make_xlsx(self.dir / "REB-단위테스트계획서.xlsx",
                                   [("단위테스트계획", [PLAN_HEADER_11, *sample_rows()]), ("보강 내역", [["기능ID"]])],
                                   validation="K2:K9", style="3")
        self.plan = de13.load_plan(self.plan_path)
        self.fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in self.plan["rows"]}
        self.ledger = self.dir / ".dev" / "ut-results"
        self.ledger.mkdir(parents=True)
        self.out = self.dir / ".dev" / "ut-results" / "export" / "사본.xlsx"

    def ledger_file(self, fn, rows):
        text = f"# {fn} 단위테스트 결과 원장\n\n" + de13.write_md_table(de13.LEDGER_HEADER, rows)
        (self.ledger / f"{fn}.md").write_text(text, encoding="utf-8")

    def row(self, tid, state="Pass", tester="bs.koo", fp=None):
        return {"테스트ID": tid, "상태": state, "수행일": "2026.10.12" if state == "Pass" else "",
                "담당자": tester if state == "Pass" else "", "테스트 위치": "src/test/A.java:3",
                "행 지문": fp or self.fp[tid], "비고": ""}

    def test_writes_only_target_cells_and_keeps_other_parts(self):
        self.ledger_file("FN-001", [self.row("UT-001"), self.row("UT-002", state="제외")])
        summary = de13.apply(self.plan_path, self.ledger, {"bs.koo": "구본승"}, self.out)
        written = {r["테스트ID"]: r for r in de13.load_plan(self.out)["rows"]}
        self.assertEqual((written["UT-001"]["결과"], written["UT-001"]["수행일"], written["UT-001"]["테스트담당자"]),
                         ("Pass", "2026.10.12", "구본승"))
        self.assertEqual(written["UT-002"]["결과"], "")
        self.assertEqual(written["UT-003"]["기대결과"], "정상 등록")
        src, dst = zipfile.ZipFile(self.plan_path), zipfile.ZipFile(self.out)
        self.assertEqual(src.namelist(), dst.namelist())
        for name in src.namelist():
            if name != self.plan["part"]:
                self.assertEqual(src.read(name), dst.read(name), name)
        sheet = dst.read(self.plan["part"]).decode("utf-8")
        self.assertIn('<formula1>"Pass,Fail"</formula1>', sheet)
        self.assertIn('<c r="K2" s="3" t="inlineStr"><is><t>Pass</t></is></c>', sheet)
        self.assertEqual(summary["기능별"]["FN-001"], {"Pass": 1, "제외": 1, "이관": 0, "미착수": 2, "재확인 필요": 0})

    def test_fingerprint_mismatch_is_reported_not_written(self):
        self.ledger_file("FN-001", [self.row("UT-001", fp="deadbeef")])
        summary = de13.apply(self.plan_path, self.ledger, {"bs.koo": "구본승"}, self.out)
        self.assertEqual(summary["재확인 필요"], ["UT-001"])
        self.assertEqual(next(r for r in de13.load_plan(self.out)["rows"] if r["테스트ID"] == "UT-001")["결과"], "")

    def test_ids_missing_from_plan_are_reported(self):
        self.ledger_file("FN-001", [self.row("UT-001"), dict(self.row("UT-001"), 테스트ID="UT-999")])
        summary = de13.apply(self.plan_path, self.ledger, {"bs.koo": "구본승"}, self.out)
        self.assertEqual(summary["계획서에 없음"], ["UT-999"])

    def test_unknown_tester_writes_nothing(self):
        self.ledger_file("FN-001", [self.row("UT-001", tester="lee")])
        summary = de13.apply(self.plan_path, self.ledger, {}, self.out)
        self.assertEqual(summary["매핑 없는 담당자"], ["lee"])
        self.assertFalse(self.out.exists())

    def test_refuses_to_overwrite_plan(self):
        before = self.plan_path.read_bytes()
        with self.assertRaisesRegex(de13.InputError, "원본"):
            de13.apply(self.plan_path, self.ledger, {}, self.plan_path)
        self.assertEqual(self.plan_path.read_bytes(), before)

    def test_inserts_missing_cell_in_column_order_and_handles_shared_strings(self):
        rows = [r[:8] for r in sample_rows()]  # 테스트담당자·수행일·결과 셀이 아예 없는 행
        header = PLAN_HEADER_11
        plan_path = make_xlsx(self.dir / "shared.xlsx", [("단위테스트계획", [header, *rows])], shared=True)
        fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in de13.load_plan(plan_path)["rows"]}
        self.ledger_file("FN-001", [self.row("UT-001", fp=fp["UT-001"])])
        de13.apply(plan_path, self.ledger, {"bs.koo": "구본승"}, self.out)
        rec = next(r for r in de13.load_plan(self.out)["rows"] if r["테스트ID"] == "UT-001")
        self.assertEqual((rec["결과"], rec["테스트담당자"]), ("Pass", "구본승"))
        sheet = zipfile.ZipFile(self.out).read("xl/worksheets/sheet1.xml").decode("utf-8")
        row2 = sheet[sheet.index('<row r="2"'):sheet.index("</row>", sheet.index('<row r="2"'))]
        self.assertLess(row2.index('r="H2"'), row2.index('r="I2"'))
        self.assertLess(row2.index('r="J2"'), row2.index('r="K2"'))

    def test_read_testers_and_cli_exit_codes(self):
        (self.ledger / "testers.md").write_text("| git 이름 | 실명 |\n|---|---|\n| bs.koo | 구본승 |\n", encoding="utf-8")
        self.assertEqual(de13.read_testers(self.ledger / "testers.md"), {"bs.koo": "구본승"})
        self.ledger_file("FN-001", [self.row("UT-001"), self.row("UT-003", tester="lee")])
        report = self.dir / "report.json"
        args = ["apply", "--plan", str(self.plan_path), "--ledger-dir", str(self.ledger),
                "--testers", str(self.ledger / "testers.md"), "--out", str(self.out), "--report", str(report)]
        self.assertEqual(de13.main(args), 3)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["매핑 없는 담당자"], ["lee"])
        (self.ledger / "testers.md").write_text("| git 이름 | 실명 |\n|---|---|\n| bs.koo | 구본승 |\n| lee | 이개발 |\n",
                                                encoding="utf-8")
        self.assertEqual(de13.main(args), 0)
        self.assertTrue(self.out.is_file())


if __name__ == "__main__":
    unittest.main()
```

`test_writes_only_target_cells_and_keeps_other_parts`의 기대 요약 근거: FN-001 기능 행은 UT-001·002·003·008(4행). Pass 1(UT-001), 제외 1(UT-002), 원장에 없는 UT-003·008이 미착수 2.

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest discover -s tests -p "test_de13_apply.py" -v`
Expected: ERROR `AttributeError: module 'de13' has no attribute 'apply'`

- [ ] **Step 3: apply 구현**

`# ---------- 명령 ----------` 줄 위에 추가:

```python
# ---------- 사본 반영 ----------

TESTERS_HEADER = ["git 이름", "실명"]


def read_testers(path: Path) -> dict[str, str]:
    if not path or not Path(path).is_file():
        return {}
    return {r["git 이름"]: r["실명"] for r in read_md_table(Path(path)) if r.get("git 이름")}


def _ledger_rows(ledger_dir: Path) -> list[dict]:
    rows = []
    for p in sorted(Path(ledger_dir).glob("*.md")):
        if p.name == "testers.md":
            continue
        rows.extend(r for r in read_md_table(p) if r.get("테스트ID"))
    return rows


def _cell_xml(ref: str, value: str, style: str | None) -> str:
    s = f' s="{style}"' if style else ""
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


_CELL_RE = re.compile(r'<c\b(?P<attrs>[^>]*?)(?:/>|>.*?</c>)', re.S)


def _patch_row(row_xml: str, rnum: int, values: dict[int, str]) -> str:
    if row_xml.endswith("/>"):
        row_xml = row_xml[:-2].rstrip() + "></row>"
    open_end = row_xml.index(">") + 1
    head, inner, tail = row_xml[:open_end], row_xml[open_end:-len("</row>")], "</row>"
    cells = []
    for m in _CELL_RE.finditer(inner):
        ref = re.search(r'\br="([A-Z]+)\d+"', m.group("attrs"))
        cells.append([_col_index(ref.group(1)) if ref else -1, m.group(0)])
    for col, value in sorted(values.items()):
        ref = f"{_col_letters(col)}{rnum}"
        existing = next((c for c in cells if c[0] == col), None)
        if existing:
            style = re.search(r'\bs="(\d+)"', existing[1])
            existing[1] = _cell_xml(ref, value, style.group(1) if style else None)
        else:
            cells.append([col, _cell_xml(ref, value, None)])
    cells.sort(key=lambda c: c[0])
    return head + "".join(c[1] for c in cells) + tail


def _patch_sheet(xml: str, updates: dict[int, dict[int, str]]) -> str:
    if re.search(r"<\w+:worksheet\b", xml):
        raise InputError("지원하지 않는 시트 XML 형식입니다 (접두사 네임스페이스)")
    for rnum, values in updates.items():
        m = re.search(rf'<row\b[^>]*\br="{rnum}"[^>]*?(?:/>|>.*?</row>)', xml, re.S)
        if not m:
            raise InputError(f"계획서에서 {rnum}행을 찾을 수 없습니다")
        xml = xml[:m.start()] + _patch_row(m.group(0), rnum, values) + xml[m.end():]
    return xml


def apply(plan_path: Path, ledger_dir: Path, testers: dict[str, str], out: Path) -> dict:
    plan_path, out = Path(plan_path), Path(out)
    if out.resolve() == plan_path.resolve():
        raise InputError("반영 사본 경로가 원본 계획서와 같습니다 — 원본은 덮어쓰지 않습니다")
    plan = load_plan(plan_path)
    by_id = {r["테스트ID"]: r for r in plan["rows"]}
    cols = plan["cols"]
    ledger = _ledger_rows(Path(ledger_dir))
    in_ledger = {r["테스트ID"] for r in ledger}
    per_fn: dict[str, dict[str, int]] = {}
    for r in plan["rows"]:
        if r["연계기능ID"]:
            per_fn.setdefault(r["연계기능ID"], {"Pass": 0, "제외": 0, "이관": 0, "미착수": 0, "재확인 필요": 0})
            if r["테스트ID"] not in in_ledger:
                per_fn[r["연계기능ID"]]["미착수"] += 1

    def bump(fn: str, key: str) -> None:
        if fn in per_fn:
            per_fn[fn][key] += 1

    recheck, not_in_plan, unknown, updates = [], [], [], {}
    for row in ledger:
        tid, state = row["테스트ID"], row.get("상태", "")
        rec = by_id.get(tid)
        if rec is None:
            not_in_plan.append(tid)
            continue
        fn = rec["연계기능ID"]
        if state.startswith("이관"):
            bump(fn, "이관")
            continue
        if state == "제외":
            bump(fn, "제외")
            continue
        if state != "Pass":
            continue
        if row.get("행 지문") != row_fingerprint(rec):
            recheck.append(tid)
            bump(fn, "재확인 필요")
            continue
        git_name = row.get("담당자", "")
        name = testers.get(git_name)
        if name is None:
            if git_name not in unknown:
                unknown.append(git_name)
            continue
        updates[rec["_row"]] = {cols["결과"]: "Pass", cols["수행일"]: row.get("수행일", ""),
                                cols["테스트담당자"]: name}
        bump(fn, "Pass")
    summary = {"output": out.as_posix(), "기능별": per_fn, "재확인 필요": recheck,
               "계획서에 없음": not_in_plan, "매핑 없는 담당자": unknown}
    if unknown:
        return summary
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(plan_path) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == plan["part"] and updates:
                data = _patch_sheet(data.decode("utf-8"), updates).encode("utf-8")
            dst.writestr(info, data)
    return summary


def cmd_apply(args) -> int:
    summary = apply(Path(args.plan), Path(args.ledger_dir), read_testers(Path(args.testers)), Path(args.out))
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if summary["매핑 없는 담당자"]:
        print("매핑 없는 담당자: " + ", ".join(summary["매핑 없는 담당자"]))
        return 3
    print(f"반영 사본: {summary['output']}")
    return 0
```

`build_parser()`에 추가:

```python
    a = sub.add_parser("apply")
    a.add_argument("--plan", required=True)
    a.add_argument("--ledger-dir", required=True)
    a.add_argument("--testers", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--report", required=True)
    a.set_defaults(func=cmd_apply)
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v`
Expected: 32 tests OK

- [ ] **Step 5: CI 등록**

`.github/workflows/lint.yml`의 `codex-contract` 작업 마지막 단계 아래에 추가 (들여쓰기는 기존 `- name:`과 같게):

```yaml
      - name: DE-13 헬퍼 단위 테스트
        run: python -m unittest discover -s tests -p "test_de13_*.py" -v
```

- [ ] **Step 6: 실데이터 확인 (커밋하지 않음)**

Run (Git Bash, 한 줄씩):
```
python .claude/skills/gx-test-plan/scripts/de13.py scope --plan "D:/SQ/pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-단위테스트계획서.xlsx" --fn REB-FN-001,REB-FN-014 --out D:/Temp/claude/de13-real/ut-floor.md
python .claude/skills/gx-test-plan/scripts/de13.py scope --plan "D:/SQ/pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-단위테스트계획서.xlsx" --spec "D:/SQ/pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-기능명세서.xlsx" --out D:/Temp/claude/de13-real/functions.json
```
Expected: 첫 명령 "하한선 13행(대상 13)" (FN-001 7행 + FN-014 6행). `functions.json`에 기능 46개, `REB-FN-001`의 `기능명`이 `원천 데이터 등록`. ut-floor.md의 UT-002 사전조건이 `신규 프로젝트, 회차 없음`(〃 해소), UT-048 표식에 `가정`. 숫자가 다르면 원인을 확인해 보고서에 적는다 (헬퍼 버그면 수정 후 테스트 추가).

이어서 원장 하나를 손으로 만들어 apply를 확인한다:
```
python -c "import sys; sys.path.insert(0,'.claude/skills/gx-test-plan/scripts'); import de13; from pathlib import Path; p=de13.load_plan(Path(sys.argv[1])); r=next(x for x in p['rows'] if x['테스트ID']=='REB-UT-001'); d=Path('D:/Temp/claude/de13-real/ut-results'); d.mkdir(parents=True, exist_ok=True); (d/'REB-FN-001.md').write_text('# REB-FN-001 단위테스트 결과 원장\n\n'+de13.write_md_table(de13.LEDGER_HEADER,[{'테스트ID':'REB-UT-001','상태':'Pass','수행일':'2026.10.12','담당자':'bs.koo','테스트 위치':'x:1','행 지문':de13.row_fingerprint(r),'비고':''}]), encoding='utf-8'); (d/'testers.md').write_text('| git 이름 | 실명 |\n|---|---|\n| bs.koo | 구본승 |\n', encoding='utf-8')" "D:/SQ/pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-단위테스트계획서.xlsx"
python .claude/skills/gx-test-plan/scripts/de13.py apply --plan "D:/SQ/pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-단위테스트계획서.xlsx" --ledger-dir D:/Temp/claude/de13-real/ut-results --testers D:/Temp/claude/de13-real/ut-results/testers.md --out D:/Temp/claude/de13-real/REB-단위테스트계획서_결과반영_20261012.xlsx --report D:/Temp/claude/de13-real/report.json
```
Expected: 종료 코드 0, 사본 생성. 사용자에게 사본을 엑셀에서 열어 K2 셀 `Pass`·드롭다운·서식이 그대로인지 확인을 요청하고 결과를 작업 보고서에 기록한다 (자동 검증으로 표시하지 않는다). 원본 xlsx의 수정 시각이 바뀌지 않았는지 `ls -l`로 확인한다.

- [ ] **Step 7: 커밋**

`/gx-commit`. 메시지: `feat: 원장을 계획서 사본에 반영하는 apply 명령과 CI 테스트를 추가한다`

---

### Task 5: gx-tdd setup 연결 — setup-testplan.md, 포인터, 환경 감지, state 필드, 재개

**Files:**
- Create: `.claude/skills/gx-tdd/phases/setup-testplan.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` (2.1, 3.1, Step 5)
- Modify: `.claude/skills/gx-tdd/SKILL.md` (frontmatter `allowed-tools`, 환경 감지 7 다음)
- Modify: `.claude/skills/gx-tdd/references/pipeline-state.md` (state.md 예시와 갱신 규칙)
- Modify: `.claude/skills/gx-tdd/phases/setup-resume.md` (이어서 진행 시)
- Modify: `scripts/lint-consistency.sh` ([32/36])

**Interfaces:**
- Consumes: `de13.py scope` CLI (Task 1)
- Produces: state.md 필드 `ut-scope: <기능ID,…>`, 파일 `${DEV_DIR}/ut-floor.md`, 변수 `DE13`(헬퍼 절대경로)·`TESTPLAN`(계획서 경로). 이후 phase 파일은 "state.md에 `ut-scope`가 있으면 연동 중"으로 판정한다.

- [ ] **Step 1: 린트에 포인터 검사 추가 (실패하는 검사 먼저)**

`scripts/lint-consistency.sh`의 [32/36] 블록에서 `grep -qF '계획이 있으나 작업 ID가 지정되지 않은 경우' "$SETUP" || fail ...` 줄 바로 아래에 추가:

```bash
grep -qF 'Read("setup-testplan.md")' "$SETUP" || fail "setup-testplan.md 포인터 누락: phase-setup.md"
[ -f .claude/skills/gx-tdd/phases/setup-testplan.md ] || fail "setup-testplan.md 파일 없음"
```

같은 블록의 ok 메시지 `"SKILL.md ≤ 63000B · phase-setup.md ≤ 22000B · 조건부 로드 포인터 4건"`을 `"… 조건부 로드 포인터 5건"`으로 바꾼다.

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A3 "\[32/36\]"` (Bash timeout 600000)
Expected: `setup-testplan.md 포인터 누락` FAIL

- [ ] **Step 2: setup-testplan.md 작성**

`.claude/skills/gx-tdd/phases/setup-testplan.md`:

````markdown
# setup-testplan: 단위테스트계획서(DE-13) 연동

phase-setup 3.1의 6번 항목이 이 파일을 읽는다. 계획서가 없으면 아무것도 하지 않고 돌아간다. 헬퍼는 [de13.py](../../gx-test-plan/scripts/de13.py)이며, 이 파일 위치 기준 `../../gx-test-plan/scripts/de13.py`의 절대경로를 `DE13`으로 둔다 (소비 프로젝트 cwd 기준이 아니다). 실행은 `python3 "<DE13>" …`, Windows는 `python "<DE13>" …`. 둘 다 없으면 "Python이 없어 단위테스트계획서 연동을 건너뜁니다" 1줄을 안내하고 돌아간다.

## 1. 계획서 탐지

`PROJECT_ROOT` 아래에서 `*단위테스트계획서*.xlsx`를 찾는다. `~$`로 시작하는 파일, 이름에 `_결과반영_`이 든 파일, `.dev/` 아래, 빌드 산출물 디렉터리(`projectTypes.*.artifacts`)는 뺀다.

- 0개: 연동하지 않는다. 안내도 출력하지 않는다.
- 1개: 그 파일을 `TESTPLAN`으로 둔다.
- 2개 이상: 최근 수정 순 2개와 "연동 안 함"으로 묻는다. 다른 파일은 UI Other로 경로를 받는다.

```
AskUserQuestion(
  questions: [{
    question: "단위테스트계획서가 여러 개입니다. 어느 파일을 이번 작업의 하한선으로 쓸까요?",
    header: "계획서",
    options: [
      { label: "{파일 1}", description: "최근 수정: {날짜}" },
      { label: "{파일 2}", description: "최근 수정: {날짜}" },
      { label: "연동 안 함", description: "계획서 없이 gx-tdd를 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

## 2. 범위 확정

`python3 "<DE13>" scope --plan "<TESTPLAN>" --out "${PROJECT_ROOT}/.dev/ut-results/export/functions.json"`을 실행해 기능 목록을 얻는다 (`DEV_DIR`이 아직 정해지지 않은 시점이라 커밋되지 않는 반영 사본 폴더에 쓴다 — gx-commit이 이 폴더를 언스테이징한다). 같은 폴더에 `*기능명세서*.xlsx`가 하나 있으면 `--spec "<그 파일>"`을 붙인다. 종료 코드 2면 메시지를 보여주고 연동하지 않는다.

1. **`--work` 사용 시**: plan.md 해당 행의 `요구사항` 열에서 목록에 있는 기능ID를 찾는다.
2. **그 외**: ARGS[0]의 토큰 중 목록의 `기능ID`와 정확히 같은 것을 범위로 삼는다.
3. 찾은 기능ID는 **ARGS[0]에서 지운다** — Step 5가 `REB-FN-001`의 `FN-001`을 이슈 키(`대문자-숫자`)로 오인해 타입 없는 브랜치를 만들지 않게 하기 위해서다. 지운 자리에는 목록의 `기능명`을 넣어 Step 4 코드 맵 키워드로 쓴다.
4. 기능ID가 하나도 없으면 목록의 `기능명`(비어 있으면 그 기능 UT 행의 입력·기대결과)과 요청 문장이 가장 많이 겹치는 기능을 최대 2개 고른다.

```
AskUserQuestion(
  questions: [{
    question: "이번 작업이 단위테스트계획서의 어느 기능에 해당하나요? 해당 기능의 단위테스트 케이스가 최소 하한선이 됩니다.",
    header: "계획서 기능",
    options: [
      { label: "{기능ID 1} {기능명 1}", description: "단위테스트 {UT수}건" },
      { label: "{기능ID 2} {기능명 2}", description: "단위테스트 {UT수}건" },
      { label: "연동 안 함", description: "계획서 하한선 없이 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

겹치는 후보가 하나도 없으면 다음 질문을 쓴다.

```
AskUserQuestion(
  questions: [{
    question: "요청과 겹치는 계획서 기능을 찾지 못했습니다. 기능ID를 지정할까요?",
    header: "계획서 기능",
    options: [
      { label: "기능ID 지정", description: "다음 질문에서 기능ID를 받습니다" },
      { label: "연동 안 함", description: "계획서 하한선 없이 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

"기능ID 지정"을 고르면 별도 후속 질문으로 기능ID(여러 개면 쉼표)를 묻고 실제 답변을 기다린 뒤 진행한다. 답이 목록에 없으면 한 번 더 묻고, 두 번째도 없으면 연동하지 않는다.

## 3. 하한선 저장

범위가 정해지면 Step 6.5에서 `DEV_DIR`이 확정된 뒤 실행한다:

`python3 "<DE13>" scope --plan "<TESTPLAN>" --fn "<기능ID,…>" --out "${PROJECT_ROOT}/${DEV_DIR}/ut-floor.md"`

`--plan`은 `PROJECT_ROOT` 기준 상대경로로 넘긴다 (ut-floor의 `출처`에 그대로 남는다). 종료 코드 2면 메시지를 보여주고 연동하지 않는다. 성공하면 Step 7에서 state.md에 `ut-scope: <기능ID,…>`를 기록하고, 결과 한 줄(`하한선 N행(대상 M)`)과 `제외(미확정 행)` 행 수를 사용자에게 보고한다.

## 4. ignore 보강 (연동이 켜졌을 때만)

- **git**: `.gitignore`에 `~$*.xlsx`와 `.dev/ut-results/export/`가 없으면 추가한다.
- **svn**: `svn propget svn:ignore .`에 `~$*.xlsx`가 없으면 추가하고, `.dev/ut-results/export`는 `svn:ignore`를 `.dev/ut-results`에 설정한다 (디렉터리가 없으면 만든 뒤 `svn add --depth=empty`).

## 5. 단독 진입 (`--phase implement`·`--phase complete`)

SKILL.md 환경 감지 8이 이 절을 읽는다. state.md에 `ut-scope`가 있고 `${DEV_DIR}/ut-floor.md`가 있으면 그대로 쓴다. 둘 다 없으면 1(계획서 탐지)을 수행하고, 계획서가 있으면 2의 기능 질문을 한 번 한 뒤 3을 수행한다. "연동 안 함"이면 1줄 안내 후 진행한다.

## 6. 계획서 교체 감지

`ut-floor.md`의 `출처` 줄 sha256과 현재 계획서의 sha256 앞 12자(`python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:12])" "<TESTPLAN>"`)가 다르면 phase-complete 게이트 2가 경고한다. 범위를 다시 추출할지는 그 게이트가 묻는다.
````

- [ ] **Step 3: phase-setup.md 포인터와 압축**

(a) 3.1의 `아래 5개 작업은 서로 독립적이므로 **병렬로 실행**한다:`를 `아래 6개 작업은 서로 독립적이므로 **병렬로 실행**한다:`로 바꾼다.

(b) 5번 항목의 마지막 줄 `   - \`references/\` 디렉토리가 없으면 \`REFERENCES\`는 빈 상태로 진행한다. 안내 메시지를 출력하지 않는다.` 바로 아래에 **정확히 이 한 줄**을 추가한다 (예산 때문에 문구를 늘리지 않는다 — 건너뛰기 조건과 ARGS 정리 순서는 setup-testplan.md가 담는다):

```markdown
6. **계획서 연동**: `Read("setup-testplan.md")`.
```

(c) 예산 확보 — 2.1의 다음 줄을

```markdown
   - (참고) `git stash create`/`store` 조합은 워킹 디렉토리를 비우지 않으므로 이후 `checkout` 충돌을 유발한다. 반드시 `push -u`만 사용한다.
```

정확히 다음으로 바꾼다:

```markdown
   - `stash create`/`store`는 워킹 디렉토리를 비우지 않아 `checkout`이 충돌한다 — `push -u`만 쓴다.
```

다른 문장은 압축하지 않는다. Step 5의 `3.0.5에서 이미 결정한 브랜치명을 그대로 쓴다`는 린트 [25/36] S5가 검사하고, Step 4 코드 맵 문장은 gx-dev 쌍둥이 파일과 같아야 한다.

Run: `tr -d '\r' < .claude/skills/gx-tdd/phases/phase-setup.md | wc -c`
Expected: **21998** (계획 작성 시 실측: 현재 21,997 → 위 세 변경 후 21,998). 22000을 넘으면 붙여 넣은 문구가 위와 다른 것이니 대조해 고친다. 그래도 넘으면 다른 문장을 압축하지 말고 멈춰서 보고한다.

- [ ] **Step 4: SKILL.md — allowed-tools와 환경 감지 8**

(a) frontmatter `allowed-tools` 배열에서 `"Bash(dotnet *)",` 뒤에 `"Bash(python *)", "Bash(python3 *)",`를 넣는다.

(b) `> 7. \`--work {ID}\`가 지정되었으면 …` 줄 바로 아래에 추가:

```markdown
> 8. **단위테스트계획서 연동**: state.md에 `ut-scope`가 있으면 `${DEV_DIR}/ut-floor.md`를 하한선으로 쓴다. 없으면 `Read("phases/setup-testplan.md")`의 "5. 단독 진입" 절을 수행한다 (계획서가 없으면 아무 일도 없다).
```

- [ ] **Step 5: pipeline-state.md — ut-scope 필드**

(a) state.md 예시 YAML에서 `work-id: W01` 줄 아래에 `ut-scope: REB-FN-001`을 추가한다.

(b) 갱신 규칙 목록의 `- **기준선 게이트 결과**: …` 항목 바로 위에 추가:

```markdown
- **ut-scope**: 단위테스트계획서 연동이 켜진 세션에만 phase-setup Step 7(또는 SKILL.md 환경 감지 8)이 기록한다. 값은 쉼표로 이은 기능ID다. 이 필드가 있으면 `${DEV_DIR}/ut-floor.md`가 하한선이고, phase-requirements 게이트 1과 phase-complete Step -1.5·0.5가 동작한다. 필드가 없으면 연동이 꺼진 세션이다.
```

- [ ] **Step 6: setup-resume.md — 복원**

`- \`${DEV_DIR}/\` 하위의 prd.md, design.md, trust-ledger.md, codemap.md, ac.md가 있으면 Read하여 맥락 복원.`을 다음으로 바꾼다:

```markdown
- `${DEV_DIR}/` 하위의 prd.md, design.md, trust-ledger.md, codemap.md, ac.md가 있으면 Read하여 맥락 복원. state.md에 `ut-scope`가 있으면 `ut-floor.md`도 Read한다.
```

state.md 복원 목록 `state.md에서 VCS_TYPE, GIT_PREFIX, … model-profile을 복원하되`의 `model-profile` 뒤에 `, ut-scope`를 넣는다.

- [ ] **Step 7: 검증**

Run: `bash scripts/lint-consistency.sh` (Bash timeout 600000 — 약 4분)
Expected: `[32/36]` OK, 전체 FAIL 0

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`
Expected: 전부 OK (특히 `test_static_examples_have_valid_question_and_option_counts`, `test_relative_links...`)

- [ ] **Step 8: 커밋**

`/gx-commit`. 메시지: `feat: gx-tdd setup에서 단위테스트계획서 범위를 확정한다`

---

### Task 6: requirements — 태그 규칙과 게이트 1

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-requirements.md` (핵심 모드 분기, Step 1 프롬프트, G-W-T 게이트 뒤)
- Modify: `agents/product-owner.md` (`### 수용 기준` 템플릿과 AC 원칙)
- Regenerate: `codex-roles/` (`python scripts/sync-codex-resources.py`)

**Interfaces:**
- Consumes: `${DEV_DIR}/ut-floor.md` (Task 5), state.md `ut-scope`
- Produces: AC 요약 줄 끝 태그 문법 `[UT: <ID>(, <ID>)*]`. 이후 phase-implement·phase-review·phase-complete가 이 태그로 AC↔UT를 잇는다.

- [ ] **Step 1: 핵심 모드 분기 수정**

`- 포함 섹션: \`## 배경\`(2~3줄) + \`## 요구사항 (AC)\` — **AC는 Given-When-Then 형식 강제** (core여도 RGR 사이클이 강제되므로. 위 Iron Law의 형식·예시를 그대로 따른다). AC는 3~5개 이내.` 줄 바로 아래에 추가:

```markdown
- **단위테스트계획서 연동 중**(state.md `ut-scope` 있음)이면 `${DEV_DIR}/ut-floor.md`의 `판정=대상` 행을 입력으로 쓰고 아래 "UT 태그 규칙"을 따른다. 이때 AC 상한은 3~5개가 아니라 하한선을 다 담는 데 필요한 수까지다 — 입력값만 다른 경계 케이스는 한 AC로 묶어 수를 줄인다.
```

- [ ] **Step 2: Step 1 product-owner 프롬프트에 주입**

Step 1 목록의 `- 이전 Q&A 히스토리 (사용자 수정 요청이 있었으면: 이전 PRD 초안 + 사용자 답변)` 줄 바로 아래에 추가:

```markdown
- **단위테스트계획서 하한선** (state.md `ut-scope`가 있을 때만): `${DEV_DIR}/ut-floor.md`의 `판정=대상` 행 전체(테스트ID·사전조건·입력·기대결과·사후조건·의존성·표식)와 아래 "UT 태그 규칙". "계획서 케이스는 최소 하한선이다. AC 설계는 자유이며 계획서에 없는 AC도 추가할 수 있다"를 함께 전달한다
```

- [ ] **Step 3: UT 태그 규칙과 게이트 1 추가**

`### 위반 시 사용자 안내` 절의 AskUserQuestion 블록과 `` `current-step`을 `"G-W-T 게이트"`로 갱신. `` 줄 **다음**, `---` 앞에 추가:

````markdown
### UT 태그 규칙 (단위테스트계획서 연동 중에만)

- AC 요약 줄 끝에 대응하는 계획서 테스트ID를 `[UT: REB-UT-002]`로 붙인다. AC 하나에 G-W-T 하나라는 형식은 그대로다.
- 입력값만 다르고 나머지 시나리오가 같은 경계 케이스는 한 AC에 태그를 여러 개 붙인다 (`[UT: REB-UT-002, REB-UT-003]`). 이때 Then에 케이스별 기대값을 모두 적는다.
- Then은 계획서 문구를 복사하지 않고 위 모호어 규칙대로 구체화한다 ("정상 등록" → "회차 1건이 '등록완료' 상태로 저장된다").
- 사후조건의 테이블 건수(`TB_CYCL 1건 저장`)는 저장 대상과 건수로, `변화 없음`은 저장이 일어나지 않음으로 쓴다 (모의 검증 허용).
- 따옴표 화면 문구는 서버 응답·예외가 그 문구를 담는 경우 원문 그대로 Then에 둔다. 화면이 문구를 정하면 오류코드를 Then에 두고 AC 끝에 `(문구는 화면 책임)`을 적는다.
- 표식 `가정`인 행의 AC에는 `(가정 기반)`을 적는다.
- 태그 없는 AC는 gx-tdd 자체 설계분이다.

### UT 태그 게이트 (게이트 1 — 연동 중에만, G-W-T 게이트 통과 후)

1. AC 문서의 모든 `[UT: …]` 태그를 모은다.
2. `ut-floor.md`의 `판정=대상` 테스트ID가 모두 태그에 있는지, 태그에 하한선 밖 ID가 없는지 확인한다.
3. 위반이면 G-W-T 게이트와 같은 방식으로 1회 재작성한다 (전체 모드는 product-owner 재호출, 핵심 모드는 오케스트레이터 직접). 지시에 누락·초과 ID 목록을 넣는다.
4. 그래도 위반이면 묻는다:

```
AskUserQuestion(
  questions: [{
    question: "계획서 케이스 {N}건이 AC에 연결되지 않았습니다 ({ID 목록}). 어떻게 할까요?",
    header: "UT 하한선",
    options: [
      { label: "직접 수정", description: "AC 문서에 해당 케이스를 담은 AC나 태그를 직접 추가합니다" },
      { label: "UT 제외", description: "다음 질문에서 받은 사유로 ut-floor.md의 해당 행 판정을 제외(사유)로 바꿉니다" },
      { label: "중단", description: "요구사항을 재정의합니다" }
    ],
    multiSelect: false
  }]
)
```

"UT 제외"를 고르면 별도 후속 질문으로 제외 사유를 묻고 실제 답변을 기다린 뒤 `ut-floor.md`의 해당 행 `판정`을 `제외(사유)`로 고친다. 응답할 사용자가 없는 헤드리스 실행이면 제외하지 않고 중단한다. 결과를 execution-log에 `gate: UT-tag`로 기록한다.
````

- [ ] **Step 4: product-owner.md**

`### 수용 기준` 아래 `- AC-N: ... → [FR-N / BR-N]` 줄을 다음 두 줄로 바꾼다:

```markdown
- AC-N: ... → [FR-N / BR-N]
- (단위테스트계획서 연동 중) AC-N: ... → [FR-N] [UT: REB-UT-002, REB-UT-003]
```

`**수용 기준(AC):** 검증 가능(참/거짓 판단) + …` 문단 바로 아래에 추가:

```markdown
**단위테스트계획서 하한선**: 프롬프트에 하한선 행이 오면 각 행의 테스트ID가 적어도 한 AC의 `[UT: …]` 태그에 들어가야 한다. 계획서 문구는 Then으로 복사하지 않고 검증 가능한 값으로 구체화한다. 입력값만 다른 경계 케이스는 한 AC에 여러 태그로 묶는다. 계획서에 없는 AC를 추가하는 것은 자유다 — 하한선은 최소 조건이지 상한이 아니다.
```

- [ ] **Step 5: Codex 역할 동기화와 검증**

Run: `python scripts/sync-codex-resources.py`
Run: `python scripts/sync-codex-resources.py --check`
Expected: 드리프트 없음

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`
Expected: 전부 OK

- [ ] **Step 6: 커밋**

`/gx-commit`. 메시지: `feat: gx-tdd 요구사항 단계에 UT 태그 규칙과 하한선 게이트를 추가한다`

---

### Task 7: design·implement·review 연결

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-design.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (Step 0, 1.1, 1.15 분할 처리, 2-R 프롬프트, 2-V)
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` (Task A)
- Modify: `agents/test-architect.md`, `agents/red-writer.md`, `agents/reviewer.md`
- Regenerate: `codex-roles/`

**Interfaces:**
- Consumes: AC 태그 문법 (Task 6), `ut-floor.md` (Task 5)
- Produces: 테스트 명명 규칙 — 표시 이름 또는 이름에 UT ID 원문(`REB-UT-002`) 또는 밑줄형(`REB_UT_002`). Task 2 `check`가 이 두 형식을 인식한다.

- [ ] **Step 1: phase-design.md — test-architect 입력**

phase-design.md **Step 3-B**의 `Task(subagent_type="oh-my-gx:test-architect")` 프롬프트 `[입력]` 목록에서 다음 줄을 찾는다:

```
    - 프론트 테스트 규약 (UI 컴포넌트가 있을 때만): {FRONTEND_TESTING_PATH} — Read하여 레이어 분류(§2)와 셀렉터 규약(§4)의 근거로 사용
```

그 바로 아래에 같은 들여쓰기(공백 4칸)로 추가:

```
    - 단위테스트계획서 하한선 (state.md ut-scope가 있을 때만): {ut-floor.md의 판정=대상 행} — 대용량·시간 조건(파일 용량, 건수 상한, 경과 시간, 호출 한도)은 실제 값을 만들지 않는 대역(크기·건수 추상화, Clock 주입, 카운터 주입)으로, 사후조건의 테이블 건수는 저장소 모의로 저장 대상·건수를 단언하는 전략을 컴포넌트별 테스트 전략에 적는다. 대역으로도 검증할 수 없는 행은 "### 단위테스트 불가 후보"에 테스트ID와 사유로 나열한다
```

- [ ] **Step 2: test-architect.md**

`## 입력` 절 끝에 추가:

```markdown
- **단위테스트계획서 하한선** (있을 때만): 계획서 테스트 케이스 행. 대용량·시간 조건은 대역(크기·건수 추상화, Clock 주입)으로, 테이블 사후조건은 저장소 모의로 검증하는 전략을 컴포넌트별 테스트 전략에 포함한다. 대역으로도 검증할 수 없는 행은 출력의 `### 단위테스트 불가 후보`에 테스트ID와 사유로 나열한다 (score 산정과 무관).
```

- [ ] **Step 3: phase-implement.md — Step 0·1.1·1.15**

(a) Step 0 목록의 `- \`${PROJECT_ROOT}/${DEV_DIR}/prd.md\`를 Read하여 PRD를 로드한다. …` 줄 아래에 추가:

```markdown
- state.md에 `ut-scope`가 있으면 `${PROJECT_ROOT}/${DEV_DIR}/ut-floor.md`를 Read하고, AC의 `[UT: …]` 태그로 AC별 계획서 행을 묶어 둔다 (2-R·2-V 프롬프트에 쓴다).
```

(b) 1.1 표 예시 아래 `### 의존성 (실행 순서)` 코드 블록이 끝나는 ```` ``` ```` 다음 줄에 추가:

```markdown
단위테스트계획서 연동 중이면 `AC 매핑` 열에 태그를 함께 적는다 (예: `AC-2 [UT: REB-UT-002, REB-UT-003]`).
```

(c) 1.15의 `- **작업 계획으로 분할** → …` 항목 끝(`… (implement/Step 1.15)\`를 기록한다.` 뒤)에 이어서 같은 항목에 추가:

```markdown
 연동 중이면 이관한 AC의 `[UT: …]` 테스트ID를 `ut-floor.md`에서 `판정=이관(W0N)`(새 W행 ID)으로 고친다.
```

- [ ] **Step 4: phase-implement.md — 2-R 프롬프트**

2-R 프롬프트의

```
    [AC (Given-When-Then)]
    {태스크가 매핑된 AC 시나리오}
```

바로 아래에 추가:

```
    [단위테스트계획서 케이스 — 연동 중이고 태스크 AC에 UT 태그가 있을 때만]
    {태그된 테스트ID별 계획서 행: 사전조건 / 입력 / 기대결과 / 사후조건 / 의존성 / 표식}
    - 각 테스트ID마다 테스트 케이스 1건. 테스트 이름이나 표시 이름에 테스트ID 원문을 넣는다
      (@DisplayName("REB-UT-002 …"), it('REB-UT-002 …')). 하이픈을 못 쓰는 식별자만 쓸 수 있으면 REB_UT_002.
      파라미터화 테스트면 케이스별 표시 이름에 각 ID를 넣는다.
    - 의존성 열은 실행 순서가 아니다. 선행 상태를 Given 준비 데이터로 만들고, 선행 기능이 없으면 모의로 대신한다.
    - 사후조건의 테이블 건수는 저장소 모의로 저장 대상·건수를 단언하고, "변화 없음"은 저장 호출 0회를 단언한다.
    - 따옴표 화면 문구는 서버 응답·예외에 담기면 원문 그대로 단언하고, AC에 "(문구는 화면 책임)"이 있으면 오류코드를 단언한다.
```

같은 프롬프트 `[작업]` 1번의 `- 이름이 검증하는 동작을 설명` 줄을 `- 이름이 검증하는 동작을 설명 (계획서 케이스면 테스트ID를 앞에 둔다)`로 바꾼다.

- [ ] **Step 5: phase-implement.md — 2-V**

Step 2-V 디스패치 프롬프트(`Task(subagent_type="oh-my-gx:reviewer", model: "sonnet")`)의

```
    [태스크 AC (Given-When-Then)]
    {이 태스크에 매핑된 AC 시나리오 — Part 1은 이것만 평가}
```

바로 아래에 추가:

```
    [단위테스트계획서 케이스 — 연동 중이고 태스크 AC에 UT 태그가 있을 때만]
    {태그된 테스트ID별 계획서 행: 사전조건 / 입력 / 기대결과 / 사후조건}
    Part 1에 UT 대조표(테스트ID / 테스트 위치 / 기대결과·사후조건 단언 여부 ✅⚠️❌)를 추가한다. ❌는 Part 1 FAIL 사유다.
```

- [ ] **Step 6: phase-review.md — Task A**

Task A 프롬프트의

```
    [PRD]
    - 요구사항: {PRD "요구사항" 섹션}
    - 수용 기준 (G-W-T 시나리오): {PRD "수용 기준" 섹션}
```

바로 아래에 추가:

```
    [단위테스트계획서 하한선 — state.md ut-scope가 있을 때만]
    - ut-floor 경로: {PROJECT_ROOT}/{DEV_DIR}/ut-floor.md — Read하여 판정=대상 행 확인
    - Part 1에 "UT 대조표"(테스트ID / 테스트 위치 / 기대결과·사후조건 단언 여부 ✅⚠️❌)를 추가한다. ❌는 Part 1 FAIL 사유다.
    - Part 2에서 테스트 이름 정리를 권고할 때 테스트ID를 빼라고 권고하지 않는다.
```

- [ ] **Step 7: red-writer.md**

`## 작업 절차` 1번의 `   - **이름이 검증하는 동작을 설명**한다 (\`test1\` 금지, 예: \`잘못된_비밀번호는_401을_반환한다\`)` 줄 아래에 추가:

```markdown
   - **단위테스트계획서 케이스**가 프롬프트에 있으면 테스트ID마다 케이스 1건을 쓰고, 테스트 이름이나 표시 이름에 테스트ID 원문(`REB-UT-002`)을 넣는다. 하이픈을 못 쓰는 식별자만 가능하면 `REB_UT_002`. 의존성 열은 Given 준비 데이터로 풀고 실행 순서에 기대지 않는다.
```

- [ ] **Step 8: reviewer.md**

`## Part 1: spec 충족 검증` 절 끝에 추가:

```markdown
**단위테스트계획서 대조** (프롬프트에 하한선이나 계획서 케이스가 올 때만): 테스트ID마다 테스트가 존재하는지, 그 테스트가 계획서의 기대결과·사후조건을 실제로 단언하는지 `UT 대조표`(테스트ID / 위치 / ✅⚠️❌)로 보고한다. 이름에 ID만 있고 단언이 없으면 ❌이며 Part 1 FAIL 사유다. Part 2에서 테스트 이름 정리를 권고할 때 테스트ID를 빼라고 권고하지 않는다.
```

`## 출력 형식`의 `## Part 1: AC 충족 매트릭스` 템플릿 아래 `## 설계 범위 이탈` 앞에 추가:

```markdown
## UT 대조표 (단위테스트계획서 연동 시에만)
| 테스트ID | 테스트 위치 | 단언 | 비고 |
```

- [ ] **Step 9: 동기화와 검증**

Run: `python scripts/sync-codex-resources.py`
Run: `python scripts/sync-codex-resources.py --check`
Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`
Run: `bash scripts/lint-consistency.sh` (timeout 600000)
Expected: 모두 통과. [33/36]~[35/36]은 phase-implement 계약을 보므로 실패하면 바꾼 문장이 기존 계약 문구를 깨뜨렸는지 확인한다.

- [ ] **Step 10: 커밋**

`/gx-commit`. 메시지: `feat: 설계·구현·리뷰 단계에 계획서 케이스 명명과 대조를 연결한다`

---

### Task 8: complete — 게이트 2, 원장 기록, gx-commit 예외

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md`
- Modify: `.claude/skills/gx-commit/SKILL.md`

**Interfaces:**
- Consumes: `de13.py check`·`record` CLI (Task 2·3), `ut-floor.md`, setup-testplan "6. 계획서 교체 감지"
- Produces: `${DEV_DIR}/ut-check.json`, `.dev/ut-results/{기능ID}.md`

- [ ] **Step 1: Step -1.5 게이트 2 추가**

phase-complete.md의 `## Step -1: verify 게이트 (commit/PR 진입 전 필수)` 줄 **바로 앞**에 추가:

````markdown
## Step -1.5: 단위테스트계획서 하한선 게이트 (연동 중에만)

state.md에 `ut-scope`가 없으면 건너뛴다. `DE13`은 `setup-testplan.md`와 같은 규칙으로 정한다 (이 파일 위치 기준 `../../gx-test-plan/scripts/de13.py`의 절대경로).

1. **계획서 교체 감지**: `setup-testplan.md` "6. 계획서 교체 감지"대로 sha를 비교한다. 다르면 "브랜치 진행 중 계획서가 바뀌었습니다"를 알리고, 범위를 다시 추출할지(→ `scope` 재실행 후 phase-requirements 게이트 1부터) 그대로 진행할지 묻는다.
2. `python3 "<DE13>" check --floor "${PROJECT_ROOT}/${DEV_DIR}/ut-floor.md" --root "${PROJECT_ROOT}" --out "${PROJECT_ROOT}/${DEV_DIR}/ut-check.json"`
3. 종료 코드 0 → Step -1로 진행. 2 → 메시지를 보고하고 중단. 1 → `ut-check.json`의 `missing`·`skipped` 목록을 보여주고 묻는다:

```
AskUserQuestion(
  questions: [{
    question: "계획서 케이스 {N}건의 테스트가 없거나 skip 상태입니다 ({ID 목록}). 어떻게 할까요?",
    header: "UT 하한선",
    options: [
      { label: "RED 추가 (Recommended)", description: "phase-implement로 돌아가 해당 케이스를 새 태스크로 RGR 사이클을 수행합니다" },
      { label: "UT 제외", description: "다음 질문에서 받은 사유로 ut-floor.md의 해당 행 판정을 제외(사유)로 바꿉니다" },
      { label: "중단", description: "state.md에 status: cancelled를 기록합니다" }
    ],
    multiSelect: false
  }]
)
```

"UT 제외"를 고르면 별도 후속 질문으로 사유를 묻고 실제 답변을 기다린 뒤 `판정`을 고치고 2번부터 다시 실행한다. Codex에서는 현재 모드의 질문 도구로 묻고, 응답할 사용자가 없는 헤드리스 실행이면 제외하지 않고 중단한다. 결과를 execution-log에 `gate: UT-floor`로 기록한다.

`current-step`을 `"UT 하한선 게이트"`로 갱신.

---

````

- [ ] **Step 2: Step 0 핵심 모드 자가 검증에 UT 대조**

`2. AC별 충족 체크리스트를 사용자에게 표시한다 (예: \`AC-1 ✅ (shouldReject401 통과) / AC-2 ⚠️ — 사유\`).` 줄 아래에 추가:

```markdown
   단위테스트계획서 연동 중이면 `ut-check.json`의 위치를 열어 테스트ID마다 계획서의 기대결과·사후조건을 단언하는지 확인하고 `REB-UT-002 ✅ (SourceTest:12)`처럼 함께 표시한다. 단언이 없으면 ⚠️로 표시하고 아래 미충족 질문으로 처리한다.
```

- [ ] **Step 3: Step 0.5 원장 기록**

`## Step 1: Commit` 줄 **바로 앞**에 추가:

```markdown
## Step 0.5: 단위테스트 결과 원장 기록 (연동 중에만)

state.md에 `ut-scope`가 없으면 건너뛴다. Step -1.5와 Step -1이 통과한 뒤에만 실행한다.

`python3 "<DE13>" record --floor "${PROJECT_ROOT}/${DEV_DIR}/ut-floor.md" --check "${PROJECT_ROOT}/${DEV_DIR}/ut-check.json" --ledger-dir "${PROJECT_ROOT}/.dev/ut-results" --date "<오늘, YYYY.MM.DD>" --tester "<git config user.name>"`

- svn이면 `--tester`는 `git` 대신 사용자에게 한 번 확인한 이름을 쓰고 state.md `execution-log`에 남긴다.
- 원장은 `.dev` 아래라 verify 지문이 바뀌지 않는다. Step 1 커밋에 함께 들어간다 (svn은 Step 1 안내 문구의 `svn add --force .`로 등록된다).
- 실패(종료 코드 2)해도 커밋을 막지 않는다. 경고와 함께 "다음 `--phase complete`에서 원장 기록을 다시 시도합니다"를 안내하고 execution-log에 남긴다.
- 성공하면 "원장 갱신: REB-FN-001.md (Pass N · 제외 N · 이관 N). 계획서 사본 반영은 `/gx-test-plan`" 한 줄을 보고한다.
```

- [ ] **Step 4: gx-commit 예외**

`.claude/skills/gx-commit/SKILL.md` 커밋 실행 1번의 `목록에 **현재 브랜치 슬러그가 아닌 \`.dev/{다른-slug}/\`** 경로가 있으면 다른 작업의 잔재일 수 있으므로 포함 여부를 사용자에게 확인한다.` 문장 뒤에 이어서 추가:

```markdown
 단 `.dev/ut-results/`는 여러 작업이 함께 쓰는 단위테스트 결과 원장이므로 묻지 않는다.
```

5번 `- 제외 파일 없음: \`git add -A\` 후 런타임 파일을 unstage한다: \`git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' 2>/dev/null\`` 명령을 다음으로 바꾼다:

```markdown
   - 제외 파일 없음: `git add -A` 후 런타임 파일을 unstage한다: `git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' '.dev/ut-results/export' 2>/dev/null` (루프 락·반복 로그는 커밋 대상이 아니다 — 커밋되면 다른 사용자의 라우팅·게이트 판별이 오작동한다. `.dev/ut-results/export`는 `/gx-test-plan`이 만드는 반영 사본이다)
```

(괄호 안 기존 설명 문장은 유지하고 마지막 문장만 덧붙인다.)

- [ ] **Step 5: 검증**

Run: `bash scripts/lint-consistency.sh` (timeout 600000)
Run: `bash scripts/hook-tests.sh`
Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`
Expected: 모두 통과. [16/36] "phase-complete context 커밋 예외 대칭"이 실패하면 새 Step이 그 검사의 기준 문장을 끊었는지 확인한다.

- [ ] **Step 6: 커밋**

`/gx-commit`. 메시지: `feat: gx-tdd 완료 단계에 하한선 게이트와 결과 원장 기록을 추가한다`

---

### Task 9: gx-test-plan 스킬, 라우팅, 문서

**Files:**
- Create: `.claude/skills/gx-test-plan/SKILL.md`
- Modify: `.claude/rules/skill-routing.md`, `.claude/rules/harness-codex.md`
- Modify: `README.md`, `docs/onboarding-guide.md`, `docs/guide.md`, `docs/tdd-guide.md`, `index.html`, `tests/codex-smoke.md`

**Interfaces:**
- Consumes: `de13.py apply`·`read_testers` (Task 4), 원장 형식 (Task 3)
- Produces: 스킬 `oh-my-gx:gx-test-plan`

- [ ] **Step 1: SKILL.md 작성**

`.claude/skills/gx-test-plan/SKILL.md`:

````markdown
---
name: gx-test-plan
version: 1.0.0
description: "gx-tdd가 남긴 단위테스트 결과 원장을 단위테스트계획서(DE-13) xlsx 사본에 반영한다. '단위테스트 결과 반영', '결과반영 엑셀', '테스트 결과 엑셀로' 시 사용."
argument-hint: "[계획서 경로]"
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "AskUserQuestion", "Bash(python *)", "Bash(python3 *)", "Bash(git *)", "Bash(ls *)", "Bash(test *)", "Bash(mkdir *)"]
---

# gx-test-plan

> **이 스킬**: gx-test-plan — 단위테스트 결과 원장을 계획서 사본에 반영
> **혼동 주의**: 원장은 gx-tdd가 완료 단계에서 만든다. 이 스킬은 테스트를 실행하지 않고 원장을 엑셀에 옮기기만 한다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. Codex에서는 먼저 `Read("../gx-dev/references/codex-runtime.md")`로 공통 실행 규약을 읽는다. 상대경로는 이 SKILL.md 위치 기준이다. `AskUserQuestion`은 현재 모드에서 제공된 질문 도구로 옮기고 실제 답변을 기다린다. 질문은 한 번에 1~3개, 질문마다 선택지는 2~3개이며 Other를 option으로 직접 추가하지 않는다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

헬퍼는 [scripts/de13.py](scripts/de13.py)다. 이 SKILL.md 위치 기준 절대경로를 `DE13`으로 두고 `python3 "<DE13>" …`(Windows는 `python`)로 실행한다. 둘 다 없으면 "Python 3.10 이상이 필요합니다"를 안내하고 종료한다.

## 절차

1. **프로젝트 루트**: `git rev-parse --show-toplevel`(svn은 `svn info --show-item wc-root`), 둘 다 아니면 현재 디렉터리.
2. **원장 확인**: `.dev/ut-results/`에 `testers.md`를 뺀 `*.md`가 없으면 "기록된 단위테스트 결과가 없습니다. gx-tdd를 계획서 연동 상태로 완료하면 원장이 생깁니다"를 안내하고 종료한다.
3. **계획서 탐지**: ARGS[0]에 경로가 있으면 그 파일. 없으면 gx-tdd `setup-testplan.md` "1. 계획서 탐지"와 같은 규칙(`*단위테스트계획서*.xlsx`, `~$`·`_결과반영_`·`.dev/`·빌드 산출물 제외). 0개면 경로를 묻고, 2개 이상이면 최근 수정 순 2개와 "취소"로 묻는다.
4. **반영**: `python3 "<DE13>" apply --plan "<계획서>" --ledger-dir ".dev/ut-results" --testers ".dev/ut-results/testers.md" --out ".dev/ut-results/export/<원본 파일명에서 .xlsx 뺀 것>_결과반영_<YYYYMMDD>.xlsx" --report ".dev/ut-results/export/report.json"`
5. **종료 코드 3** (매핑 없는 담당자): `report.json`의 `매핑 없는 담당자`마다 별도 질문으로 실명을 묻고 실제 답변을 기다린다. `.dev/ut-results/testers.md`(`| git 이름 | 실명 |` 표, 없으면 새로 만듦)에 행을 추가한 뒤 4를 다시 실행한다.
6. **종료 코드 2**: 메시지를 그대로 보고하고 종료한다.
7. **보고**: 사본 경로와 `report.json`의 기능별 `Pass / 제외 / 이관 / 미착수 / 재확인 필요`를 표로 보여준다. `재확인 필요`가 있으면 "계획서가 개정되어 해당 케이스 내용이 바뀌었습니다. 그 기능을 gx-tdd로 다시 확인하세요"를, `계획서에 없음`이 있으면 그 ID 목록을 안내한다.

## 하지 않는 것

- 원본 계획서를 덮어쓰지 않는다 (헬퍼가 같은 경로를 거부한다).
- 반영 사본을 커밋하지 않는다 (`.dev/ut-results/export/`는 gx-commit이 언스테이징한다).
- `Fail`을 기록하지 않는다. 원장에는 verify를 통과한 `Pass`, 사유가 있는 `제외`, 후속 작업으로 넘긴 `이관`만 있다.
- 비기능 행(연계기능ID 공란)은 채우지 않는다.
````

- [ ] **Step 2: skill-routing.md**

`## 단일 스킬` 표의 `| \`교차 리뷰\`, …| \`/gx-cross-review\` |` 행 아래에 추가:

```markdown
| `단위테스트 결과 반영`, `결과반영 엑셀`, `테스트 결과 엑셀로`, `계획서에 결과 넣어줘` | `/gx-test-plan` |
```

- [ ] **Step 3: 스킬 수 갱신**

Run: `ls -d .claude/skills/gx-*/ | wc -l`
이 값을 `N`이라 한다 (이 브랜치 단독이면 18, PR #92가 먼저 머지됐으면 19).

- `.claude/rules/harness-codex.md`: `` `/skills`에서 17개 GX 스킬을 확인한다 `` → `` `/skills`에서 N개 GX 스킬을 확인한다 ``
- `README.md`: `` `/skills`로 GX 스킬 17개를 `` → `` `/skills`로 GX 스킬 N개를 ``
- `docs/onboarding-guide.md`: `[스킬 17종](#5-스킬-17종)` → `[스킬 N종](#5-스킬-N종)`, `**구성.** 스킬 17종 +` → `**구성.** 스킬 N종 +`, `## 5. 스킬 17종` → `## 5. 스킬 N종`
- `index.html`: `<h2 class="display-lg">17개 스킬이 사이클을 나눠 맡습니다</h2>` → `N개 스킬이 …`. (`17개 에이전트`, `17개 로드 확인`, `서브에이전트 17개`, FAQ의 "설치 스킬 17개" 검증 문장은 과거 검증 사실·에이전트 수라 바꾸지 않는다.)
- `docs/codex-guide.md`, `docs/reports/*`, `docs/specs/*`의 "17개"는 과거 기록이라 바꾸지 않는다.

- [ ] **Step 4: 사용 안내 문서**

(a) `README.md` `### tdd` 절 끝(다음 `### ralph` 앞)에 추가:

```markdown
**단위테스트계획서 연동** — 프로젝트에 gx-pm이 만든 `*단위테스트계획서*.xlsx`가 있으면 gx-tdd가 자동으로 연동합니다. `REB-FN-001 원천 데이터 등록 TDD로 개발해줘`처럼 기능ID를 적으면 그 기능의 계획서 케이스가 테스트의 최소 하한선이 되고, 테스트 이름에 테스트ID(`REB-UT-002`)가 남습니다. 기능ID가 없으면 후보를 묻습니다("연동 안 함" 선택 가능). 완료 시 `.dev/ut-results/{기능ID}.md`에 Pass가 기록되고, `/gx-test-plan`으로 계획서 사본에 결과·수행일·담당자를 채웁니다.
```

같은 파일 `### commit / pull-request` 앞에 추가:

```markdown
### test-plan

`/gx-test-plan` — gx-tdd가 남긴 단위테스트 결과 원장을 단위테스트계획서 xlsx **사본**(`.dev/ut-results/export/`)에 반영합니다. 원본은 바꾸지 않습니다. 계획서가 개정되어 케이스 내용이 바뀐 행은 채우지 않고 "재확인 필요"로 알려 줍니다.
```

(b) `docs/onboarding-guide.md` `### 5.6 검증과 문서` 절의 `#### \`/gx-humanizer\`` 앞에 추가:

```markdown
#### `/gx-test-plan` — 단위테스트 결과를 계획서에 반영

gx-pm 단위테스트계획서(xlsx)가 레포에 있으면 gx-tdd는 해당 기능의 계획서 케이스를 테스트 하한선으로 삼고, 완료 시 `.dev/ut-results/`에 결과 원장을 남깁니다. `/gx-test-plan`은 그 원장을 계획서 사본에 옮겨 `결과`·`수행일`·`테스트담당자` 열을 채웁니다. 처음 보는 git 이름은 실명을 한 번 묻고 기억합니다.
```

(c) `docs/guide.md`의 `/gx-tech-debt ────── 기술 부채 분석 + 우선순위 로드맵 (읽기 전용)` 줄 아래에 추가:

```
/gx-test-plan ────── 단위테스트 결과 원장 → 계획서(xlsx) 사본 반영
```

(d) `docs/tdd-guide.md`의 `complete ───── [게이트 5] TDD 이행 게이트 → verify 게이트 (gx-verify)` 줄이 있는 절 끝에 다음 절을 추가한다 (절 제목 수준은 주변과 같게):

```markdown
### 단위테스트계획서(DE-13) 연동

레포에 gx-pm 단위테스트계획서 xlsx가 있으면 다음이 추가됩니다. 계획서가 없으면 아무것도 바뀌지 않습니다.

| 단계 | 추가 동작 |
|---|---|
| setup | 요청의 기능ID(없으면 후보 질문)로 범위를 정해 `.dev/{브랜치}/ut-floor.md` 저장 |
| requirements | AC 끝에 `[UT: REB-UT-002]` 태그. 범위 케이스가 모두 태그되지 않으면 게이트 1이 막음 (사유를 남기고 개별 제외 가능) |
| design | 대용량·시간 조건과 테이블 사후조건을 대역·모의로 검증하는 전략 |
| implement | 테스트 이름에 테스트ID |
| review | reviewer가 케이스별 단언 여부를 대조 |
| complete | verify 전에 게이트 2(테스트 존재·skip 아님), 커밋 전에 `.dev/ut-results/{기능ID}.md` 원장 기록 |

계획서 사본 반영은 `/gx-test-plan`입니다. 사후조건의 테이블 건수는 모의 검증으로 충분하고, 따옴표 화면 문구는 서버가 내면 원문, 화면이 정하면 오류코드를 단언합니다.
```

(e) `tests/codex-smoke.md`의 `## 역할·질문` 표 마지막 행 아래에 추가:

```markdown
| T1 | 계획서 xlsx가 있는 소비 프로젝트에서 `REB-FN-014 … TDD로 개발해줘` (Codex) | 기능ID가 ARGS에서 빠지고 브랜치가 `feat/…`; 기능 후보 질문이 질문 3개 이하·선택지 3개 이하; 게이트 1·2 질문이 실제 답변을 기다림; `.dev/ut-results/REB-FN-014.md` 생성 | 미실행 |
```

- [ ] **Step 5: 검증**

Run: `bash scripts/lint-consistency.sh` (timeout 600000)
Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`
Run: `python scripts/sync-codex-resources.py --check`
Expected: 모두 통과. 실패 항목이 새 스킬에 공통 요구(하네스 적응 문구, 상대경로)를 요구하면 SKILL.md를 그 요구에 맞춘다.

- [ ] **Step 6: 커밋**

`/gx-commit`. 메시지: `feat: 결과 원장을 계획서 사본에 반영하는 gx-test-plan 스킬을 추가한다`

---

### Task 10: 실제 파이프라인 smoke, 전체 검증, 릴리스

**Files:**
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`
- Create: `docs/reports/2026-10-12-gx-tdd-test-plan-smoke.md`

**Interfaces:**
- Consumes: Task 1~9 전체

- [ ] **Step 1: 수동 smoke (사용자와 함께)**

이 단계는 실제 Claude Code 세션이 필요하므로 사용자에게 요청한다. 절차를 보고서 초안에 적어 전달한다.

1. 샘플 Spring Boot 프로젝트(빈 프로젝트 가능)에 `references/REB-단위테스트계획서.xlsx`와 `references/REB-기능명세서.xlsx`를 복사하고 이 브랜치의 플러그인을 로컬 설치한다.
2. `REB-FN-014 건물별 메모 관리 TDD로 개발해줘`를 실행한다.
3. 확인 항목: 브랜치가 `feat/…`(이슈 키 오인 없음) / `.dev/{브랜치}/ut-floor.md`에 REB-UT-045~050 6행 / AC에 `[UT: …]` 태그, REB-UT-048에 `(가정 기반)` / 테스트 이름에 `REB-UT-0xx` / complete에서 게이트 2 통과 후 `.dev/ut-results/REB-FN-014.md`에 Pass 6행(또는 사유 있는 제외) / 기능 커밋에 원장 포함 / `/gx-test-plan` 실행 시 실명 질문 1회, 사본 K열 Pass.
4. 결과를 `docs/reports/2026-10-12-gx-tdd-test-plan-smoke.md`에 항목별 PASS/FAIL과 근거(파일 경로·커밋 해시)로 기록한다. 실행하지 못한 항목은 "미실행"으로 적는다.

- [ ] **Step 2: 전체 검증**

Run: `python -m unittest discover -s tests -p "test_de13_*.py" -v`
Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`
Run: `python scripts/sync-codex-resources.py --check`
Run: `bash scripts/hook-tests.sh`
Run: `bash scripts/lint-consistency.sh` (timeout 600000)
Expected: 전부 0 failures. 출력의 요약 줄을 보고서에 붙인다.

- [ ] **Step 3: 버전과 CHANGELOG**

`git fetch origin main` 후 `git show origin/main:.claude-plugin/plugin.json | grep version`으로 main의 현재 버전을 확인한다. 그 다음 minor로 올린다 (main이 1.33.0이면 1.34.0, PR #92 머지로 1.34.0이면 1.35.0). 이 값을 `V`라 한다.

- `.claude-plugin/plugin.json` `version`, `.claude-plugin/marketplace.json` `plugins[0].version`, `.codex-plugin/plugin.json` `version`을 `V`로.
- `CHANGELOG.md` 맨 위 버전 섹션 위에 기존 형식을 따라 추가:

```markdown
## [V] - 2026-10-12

### Added
- **gx-tdd 단위테스트계획서(DE-13) 연동**: 레포에 gx-pm 단위테스트계획서 xlsx가 있으면 기능ID로 범위를 정해 계획서 케이스를 테스트 하한선으로 강제한다 (AC `[UT: …]` 태그 게이트, 완료 전 테스트 존재·skip 게이트). 완료 시 `.dev/ut-results/{기능ID}.md` 결과 원장을 기능 커밋에 포함한다.
- **`/gx-test-plan`**: 결과 원장을 계획서 xlsx 사본에 반영한다 (원본 불변, 개정된 케이스는 재확인 필요로 보고, 담당자 실명 매핑).
- `de13.py` 헬퍼(표준 라이브러리 전용)와 단위 테스트, CI 실행 단계.
```

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A2 "\[1/36\]"`
Expected: 버전 4중 일치 OK

- [ ] **Step 4: 커밋**

`/gx-commit`. 메시지: `feat: 단위테스트계획서 연동 릴리스 V를 준비한다` (V는 실제 값)

---

## Self-Review 결과

- **계획 코드 사전 검증 (2026-10-12)**: Task 1~4의 python 코드 블록을 스크래치에 그대로 조립해 `test_de13_*.py` **32 tests OK**를 확인했다 (Windows, Python 3). 같은 조립본으로 실제 REB 계획서에 `scope --fn REB-FN-001,REB-FN-014` → 하한선 13행(대상 13, `〃` 해소, UT-048 `가정`), `scope --spec` → 기능 46개·기능명 매핑, `apply` → 원본 바이트 불변·데이터 시트 1개만 변경·K2 서식(s=3) 유지·데이터 검증 유지를 확인했다. 이 결과는 구현 정답을 보장하지 않으므로 각 태스크의 RED 단계는 그대로 수행한다.

- **spec 커버리지**: 확정 결정 9개 → Task 1~9에 각각 대응 (모의 검증·문구 규칙은 Task 6 태그 규칙과 Task 7 2-R, 담당자 매핑은 Task 4·9, 활성 조건은 Task 5). 실측 근거의 각 항목은 Task 1 테스트 fixture(`sample_rows`)와 Task 4 Step 6 실데이터 확인이 덮는다. 엣지케이스 표 15행 중 자동 테스트가 없는 것(계획서 교체 감지, `--ralph` 복귀, 여러 브랜치)은 phase 지시문(Task 5 §6, Task 8 Step 1)과 Task 10 smoke로 덮는다.
- **범위 밖 유지**: gx-dev, ralph 루프 내부 기록, 비기능 행, Fail, XML 리포트 판정, gx-pm 가져오기는 어느 태스크에도 없다.
- **이름 일치**: `load_plan`·`row_fingerprint`·`build_floor`·`write_floor`·`read_md_table`·`write_md_table`·`check_floor`·`record`·`apply`·`read_testers`, 상수 `FLOOR_HEADER`·`LEDGER_HEADER`, state 필드 `ut-scope`, 파일 `ut-floor.md`·`ut-check.json`·`.dev/ut-results/` — 태스크 사이 표기가 같다.
