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
