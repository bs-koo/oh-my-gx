"""de13.py: 계획서 읽기·행 지문·md 표·functions/rows 명령."""
import json
import tempfile
import unittest
from pathlib import Path

from de13_support import PLAN_HEADER_11, load_de13, make_xlsx, sample_rows

de13 = load_de13()


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 read 한글 ")
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

    def test_fingerprint_ignores_whitespace_and_excludes_test_id(self):
        a = {"테스트ID": "UT-1", "사전조건": "a  b", "입력": " x", "기대결과": "y", "사후조건": "z"}
        b = {"테스트ID": "UT-9", "사전조건": "a b", "입력": "x ", "기대결과": "y", "사후조건": "z"}
        c = dict(b, 기대결과="y2")
        self.assertEqual(de13.row_fingerprint(a), de13.row_fingerprint(b))
        self.assertNotEqual(de13.row_fingerprint(b), de13.row_fingerprint(c))
        self.assertRegex(de13.row_fingerprint(a), r"^[0-9a-f]{8}$")

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


if __name__ == "__main__":
    unittest.main()
