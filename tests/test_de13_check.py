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
