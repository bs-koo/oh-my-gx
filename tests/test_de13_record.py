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
