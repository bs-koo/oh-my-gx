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

    def test_existing_pass_is_not_downgraded_by_later_exclusion_or_transfer(self):
        de13.record([floor_row("UT-001"), floor_row("UT-002")], check_of(UT_001="found", UT_002="found"),
                    self.ledger, "2026.10.01", "kim")
        de13.record([floor_row("UT-001", verdict="제외(원장 Pass)"), floor_row("UT-002", verdict="이관(W05)")],
                    check_of(), self.ledger, "2026.10.12", "bs.koo")
        rows = {r["테스트ID"]: r for r in de13.read_md_table(self.ledger / "FN-001.md")}
        self.assertEqual((rows["UT-001"]["상태"], rows["UT-001"]["수행일"]), ("Pass", "2026.10.01"))
        self.assertEqual((rows["UT-002"]["상태"], rows["UT-002"]["담당자"]), ("Pass", "kim"))

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
