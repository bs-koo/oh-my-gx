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

    def test_floor_marks_rows_already_passed_in_ledger_with_same_fingerprint(self):
        plan = de13.load_plan(self.plan())
        fp = {r["테스트ID"]: de13.row_fingerprint(r) for r in plan["rows"]}
        ledger = {"UT-001": {"테스트ID": "UT-001", "상태": "Pass", "행 지문": fp["UT-001"]},
                  "UT-002": {"테스트ID": "UT-002", "상태": "Pass", "행 지문": "deadbeef"},
                  "UT-003": {"테스트ID": "UT-003", "상태": "제외", "행 지문": fp["UT-003"]}}
        floor = {r["테스트ID"]: r for r in de13.build_floor(plan, ["FN-001"], ledger)}
        self.assertEqual(floor["UT-001"]["판정"], "제외(원장 Pass)")
        self.assertEqual(floor["UT-002"]["판정"], "대상")  # 계획서가 바뀐 행은 다시 검증
        self.assertEqual(floor["UT-003"]["판정"], "대상")

    def test_cli_scope_reads_ledger_dir(self):
        path = self.plan()
        plan = de13.load_plan(path)
        fp = next(de13.row_fingerprint(r) for r in plan["rows"] if r["테스트ID"] == "UT-001")
        ledger = self.dir / ".dev" / "ut-results"
        ledger.mkdir(parents=True)
        (ledger / "FN-001.md").write_text("# FN-001 단위테스트 결과 원장\n\n" + de13.write_md_table(de13.LEDGER_HEADER, [
            {"테스트ID": "UT-001", "상태": "Pass", "수행일": "2026.10.01", "담당자": "kim", "테스트 위치": "a:1",
             "행 지문": fp, "비고": ""}]), encoding="utf-8")
        out = self.dir / "floor.md"
        self.assertEqual(de13.main(["scope", "--plan", str(path), "--fn", "FN-001", "--out", str(out),
                                    "--ledger-dir", str(ledger), "--date", "2026-10-12"]), 0)
        rows = {r["테스트ID"]: r for r in de13.read_md_table(out)}
        self.assertEqual(rows["UT-001"]["판정"], "제외(원장 Pass)")

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
