"""skip 휴리스틱 회귀 — locate_test로 판정한다."""
import re
import tempfile
import unittest
from pathlib import Path

from de13_support import load_de13

de13 = load_de13()


class SkipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 check 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def status(self, test_id):
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

    def test_finds_display_name_and_underscore_forms(self):
        self.write("src/test/java/a/SourceTest.java",
                   '@Test\n@DisplayName("REB-UT-002 용량 초과 차단")\nvoid a() {}\n'
                   '@Test\nvoid REB_UT_003_정확히_상한() {}\n')
        self.write("tests/test_memo.py", "def test_REB_UT_005_빈_메모():\n    pass\n")
        self.write("web/src/memo.spec.ts", "it('REB-UT-006 2001자 차단', () => {})\n")
        res = {i: self.status(i) for i in ("REB-UT-002", "REB-UT-003", "REB-UT-005", "REB-UT-006")}
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

    def test_disabled_below_display_name_is_skipped(self):
        self.write("src/test/ATest.java",
                   'class ATest {\n  @Test\n  @DisplayName("REB-UT-101 차단")\n  @Disabled("미구현")\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-101")["status"], "skipped")

    def test_display_name_then_disabled_then_test_is_skipped(self):
        self.write("src/test/ATest.java",
                   'class ATest {\n  @Test\n  void z() {}\n\n  @DisplayName("REB-UT-102 차단")\n  @Disabled\n  @Test\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-102")["status"], "skipped")

    def test_parameterized_with_multiline_source_then_disabled_is_skipped(self):
        self.write("src/test/ATest.java",
                   'class ATest {\n  @ParameterizedTest(name = "REB-UT-103 {0}")\n  @CsvSource({\n'
                   '      "1001, false",\n      "1000, true"\n  })\n  @Disabled\n  void a(int n, boolean ok) {\n  }\n}\n')
        self.assertEqual(self.status("REB-UT-103")["status"], "skipped")

    def test_class_disabled_after_javadoc_mentioning_class_is_skipped(self):
        self.write("src/test/ATest.java",
                   '/**\n * Test class for memo\n */\n@Disabled\nclass ATest {\n  @Test\n  @DisplayName("REB-UT-104")\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-104")["status"], "skipped")

    def test_previous_test_disabled_does_not_skip_target(self):
        self.write("src/test/ATest.java",
                   'class ATest {\n  @Disabled\n  @Test\n  void z() {}\n\n  @DisplayName("REB-UT-105 차단")\n  @Test\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-105")["status"], "found")

    def test_second_describe_skip_block_is_skipped(self):
        self.write("a.test.ts",
                   "describe('ok', () => { it('x', () => {}) })\ndescribe.skip('memo', () => {\n  it('REB-UT-106 차단', () => {})\n})\n")
        self.assertEqual(self.status("REB-UT-106")["status"], "skipped")

    def test_kotlin_nested_disabled_inner_class_is_skipped(self):
        self.write("src/test/ATest.kt",
                   'class ATest {\n  @Nested\n  @Disabled\n  inner class In {\n    @Test\n    fun `REB-UT-107 차단`() {}\n  }\n}\n')
        self.assertEqual(self.status("REB-UT-107")["status"], "skipped")

    def test_sibling_disabled_class_does_not_skip_next_class(self):
        self.write("src/test/ATest.java",
                   '@Disabled\nclass A {\n  @Test void z() {}\n}\nclass B {\n  @Test\n  @DisplayName("REB-UT-108")\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-108")["status"], "found")

    def test_pytest_skip_below_other_decorator_and_xfail_are_skipped(self):
        self.write("tests/test_a.py",
                   '@pytest.mark.parametrize("x", [1])\n@pytest.mark.skip\ndef test_REB_UT_109(x):\n    pass\n\n'
                   '@pytest.mark.xfail\ndef test_REB_UT_110():\n    pass\n')
        self.assertEqual(self.status("REB-UT-109")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-110")["status"], "skipped")

    def test_todo_and_csharp_skip_are_skipped(self):
        self.write("a.test.js", "it.todo('REB-UT-111 차단')\n")
        self.write("tests/ATests.cs", '[Fact(Skip = "x", DisplayName = "REB-UT-112")]\npublic void A() {}\n'
                                      '[Ignore("x")]\n[Test]\npublic void REB_UT_113() {}\n')
        self.assertEqual(self.status("REB-UT-111")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-112")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-113")["status"], "skipped")

    def test_id_only_in_comment_is_missing(self):
        self.write("src/test/ATest.java",
                   'class ATest {\n  @Test\n  void a() {}\n  // TODO REB-UT-114 나중에\n  /* REB-UT-114 */\n}\n')
        self.assertEqual(self.status("REB-UT-114")["status"], "missing")

    def test_js_skip_each_chain_is_skipped(self):
        self.write("a.test.js", "test.skip.each([[1], [2]])('REB-UT-201 %s', (v) => {\n  expect(v).toBe(9);\n});\n")
        self.assertEqual(self.status("REB-UT-201")["status"], "skipped")

    def test_pytest_module_marker_skips_file(self):
        self.write("tests/test_m.py", 'pytestmark = pytest.mark.skip(reason="disabled")\n\n'
                                      "def test_REB_UT_202():\n    assert False\n")
        self.assertEqual(self.status("REB-UT-202")["status"], "skipped")

    def test_pytest_unconditional_skip_in_body_is_skipped_but_conditional_is_not(self):
        self.write("tests/test_b.py", 'def test_REB_UT_203():\n    pytest.skip("disabled")\n    assert False\n\n'
                                      'def test_REB_UT_210():\n    if os.name == "nt":\n        pytest.skip("win")\n'
                                      '    assert True\n')
        self.assertEqual(self.status("REB-UT-203")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-210")["status"], "found")

    def test_one_line_test_followed_by_disabled_next_test_is_found(self):
        self.write("src/test/ATest.java", 'class ATest {\n  @Test @DisplayName("REB-UT-204") void a() {}\n'
                                          '  @Disabled\n  @Test\n  void b() {}\n}\n')
        self.assertEqual(self.status("REB-UT-204")["status"], "found")

    def test_blank_line_and_long_source_before_disabled_are_skipped(self):
        rows = "".join(f'      "{n}, true",\n' for n in range(20))
        self.write("src/test/ATest.java", 'class ATest {\n  @DisplayName("REB-UT-205")\n\n  @Disabled\n  @Test\n  void a() {}\n\n'
                                          f'  @ParameterizedTest(name = "REB-UT-211 {{0}}")\n  @CsvSource({{\n{rows}  }})\n'
                                          '  @Disabled\n  void b(int n, boolean ok) {\n  }\n}\n')
        self.assertEqual(self.status("REB-UT-205")["status"], "skipped")
        self.assertEqual(self.status("REB-UT-211")["status"], "skipped")

    def test_closed_describe_skip_does_not_skip_following_multiline_it(self):
        self.write("a.test.js", "describe.skip('old', () => {\n  it('old', () => {});\n});\nit(\n  'REB-UT-212',\n  () => {},\n);\n")
        self.assertEqual(self.status("REB-UT-212")["status"], "found")

    def test_trailing_and_block_comment_ids_are_ignored_but_strings_kept(self):
        self.write("b.test.js", "it('다른 테스트', () => {}); // REB-UT-206\n/*\nREB-UT-207\n*/\n"
                                "it('REB-UT-208 http://example.com', () => {});\n")
        self.assertEqual(self.status("REB-UT-206")["status"], "missing")
        self.assertEqual(self.status("REB-UT-207")["status"], "missing")
        self.assertEqual(self.status("REB-UT-208")["status"], "found")

    def test_commented_out_disabled_does_not_skip(self):
        self.write("src/test/ATest.java", 'class ATest {\n  // @Disabled\n  @Test\n  @DisplayName("REB-UT-209")\n  void a() {}\n}\n')
        self.assertEqual(self.status("REB-UT-209")["status"], "found")

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


if __name__ == "__main__":
    unittest.main()
