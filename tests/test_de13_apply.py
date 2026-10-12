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
