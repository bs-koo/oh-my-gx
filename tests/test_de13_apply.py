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
        with zipfile.ZipFile(self.plan_path) as before:
            originals = {n: before.read(n) for n in before.namelist()}
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
