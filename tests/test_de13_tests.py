"""de13.py tests: 변경 파일에서 테스트 선언 목록과 위치 판정."""
import json
import tempfile
import unittest
from pathlib import Path

from de13_support import load_de13

de13 = load_de13()

GIT_DIFF = """diff --git a/src/test/java/a/MemoTest.java b/src/test/java/a/MemoTest.java
new file mode 100644
--- /dev/null
+++ b/src/test/java/a/MemoTest.java
@@ -0,0 +1,3 @@
+class MemoTest {}
diff --git a/src/main/java/a/Memo.java b/src/main/java/a/Memo.java
--- a/src/main/java/a/Memo.java
+++ b/src/main/java/a/Memo.java
@@ -1 +1 @@
diff --git a/old/GoneTest.java b/old/GoneTest.java
deleted file mode 100644
--- a/old/GoneTest.java
+++ /dev/null
"""

SVN_DIFF = """Index: web/src/memo.spec.ts
===================================================================
--- web/src/memo.spec.ts\t(nonexistent)
+++ web/src/memo.spec.ts\t(working copy)
@@ -0,0 +1 @@
"""

JAVA = """package a;
class MemoTest {
    @Test
    void 빈_내용이면_거부() {}
    @Disabled
    @Test
    void 보류() {}
    @ParameterizedTest
    @ValueSource(ints = {1, 2})
    void 길이_경계(int n) {
        assertThat(n).isPositive();
    }
}
"""


class TestsCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="de13 tests 한글 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return rel

    def test_changed_files_from_git_and_svn_diff(self):
        self.assertEqual(de13.changed_files(GIT_DIFF), ["src/test/java/a/MemoTest.java", "src/main/java/a/Memo.java"])
        self.assertEqual(de13.changed_files(SVN_DIFF), ["web/src/memo.spec.ts"])

    def test_lists_each_test_once_with_skip_flag(self):
        rel = self.write("src/test/java/a/MemoTest.java", JAVA)
        tests = de13.list_tests(self.root, [rel])
        self.assertEqual([(t["line"], t["skipped"]) for t in tests], [(3, False), (6, True), (8, False)])
        self.assertIn("빈_내용이면_거부", tests[0]["decl"])
        self.assertIn("ValueSource", tests[2]["decl"])

    def test_lists_js_and_python_tests(self):
        js = self.write("web/src/memo.spec.ts", "describe('메모', () => {\n  it('빈 메모 거부', () => {})\n  it.skip('보류', () => {})\n})\n")
        py = self.write("tests/test_memo.py", "@pytest.mark.parametrize('n', [1])\ndef test_길이(n):\n    pass\n")
        tests = de13.list_tests(self.root, [js, py])
        self.assertEqual([(t["path"], t["skipped"]) for t in tests],
                         [(js, False), (js, True), (py, False)])

    def test_ignores_non_test_build_and_missing_files(self):
        main = self.write("src/main/java/a/Memo.java", "class Memo { @Test void x() {} }\n")
        built = self.write("build/test/MemoTest.java", "@Test\nvoid x() {}\n")
        self.assertEqual(de13.list_tests(self.root, [main, built, "src/test/java/NoFile.java"]), [])

    def test_locate_test_accepts_header_or_body_line_and_rejects_others(self):
        rel = self.write("src/test/java/a/MemoTest.java", JAVA)
        hit = de13.locate_test(self.root, f"{rel}:4")
        self.assertEqual((hit["path"], hit["line"], hit["skipped"]), (rel, 4, False))
        self.assertIn("빈_내용이면_거부", hit["decl"])
        self.assertFalse(de13.locate_test(self.root, f"{rel}:11")["skipped"])  # 본문 줄
        self.assertTrue(de13.locate_test(self.root, f"{rel}:7")["skipped"])
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:1"))   # package 줄
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:99"))
        self.assertIsNone(de13.locate_test(self.root, "src/main/java/a/Memo.java:1"))
        self.assertIsNone(de13.locate_test(self.root, "MemoTest.java"))

    def test_cli_writes_json_from_diff(self):
        self.write("src/test/java/a/MemoTest.java", JAVA)
        diff = self.root / "diff.txt"
        diff.write_text(GIT_DIFF, encoding="utf-8")
        out = self.root / ".dev" / "x" / "ut-tests.json"
        self.assertEqual(de13.main(["tests", "--diff", str(diff), "--root", str(self.root), "--out", str(out)]), 0)
        self.assertEqual(len(json.loads(out.read_text(encoding="utf-8"))), 3)

    def test_git_quoted_korean_path_is_decoded(self):
        quoted = 'diff --git "a/tests/test_\\353\\251\\224\\353\\252\\250.py" "b/tests/test_\\353\\251\\224\\353\\252\\250.py"\n' \
                 '--- /dev/null\n+++ "b/tests/test_\\353\\251\\224\\353\\252\\250.py"\n'
        self.assertEqual(de13.changed_files(quoted), ["tests/test_메모.py"])

    def test_cli_files_from_list(self):
        self.write("src/test/java/a/MemoTest.java", JAVA)
        self.write("tests/test_메모.py", "def test_a():\n    pass\n")
        listing = self.root / "files.txt"
        listing.write_text("src/test/java/a/MemoTest.java\ntests/test_메모.py\n\nsrc/main/X.java\n", encoding="utf-8")
        out = self.root / "ut-tests.json"
        self.assertEqual(de13.main(["tests", "--files-from", str(listing), "--root", str(self.root), "--out", str(out)]), 0)
        self.assertEqual(len(json.loads(out.read_text(encoding="utf-8"))), 4)

    def test_locate_test_rejects_lines_after_test_body(self):
        rel = self.write("src/test/java/a/HelperTest.java",
                         "class HelperTest {\n    @Test\n    void a() {\n        assertThat(1).isOne();\n    }\n"
                         "    private int helper() {\n        return 1;\n    }\n}\n")
        self.assertIsNotNone(de13.locate_test(self.root, f"{rel}:4"))
        self.assertIsNotNone(de13.locate_test(self.root, f"{rel}:5"))
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:7"))
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:9"))

    def test_python_body_line_shares_test_skip_and_module_code_is_rejected(self):
        rel = self.write("tests/test_b.py", 'def test_a():\n    marker = 1\n    pytest.skip("x")\n\nSETTING = 42\n')
        self.assertTrue(de13.locate_test(self.root, f"{rel}:2")["skipped"])
        self.assertIsNone(de13.locate_test(self.root, f"{rel}:5"))

    def test_cli_missing_diff_returns_2(self):
        self.assertEqual(de13.main(["tests", "--diff", str(self.root / "none.txt"), "--root", str(self.root),
                                    "--out", str(self.root / "o.json")]), 2)


if __name__ == "__main__":
    unittest.main()
