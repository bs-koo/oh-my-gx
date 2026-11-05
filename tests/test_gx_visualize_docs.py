import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
CODEX_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
INDEX = ROOT / "index.html"
SKILL_DIR = ROOT / ".claude" / "skills" / "gx-visualize"


class BalancedHtmlParser(HTMLParser):
    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
        self.image_labels = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("role") == "img":
            self.image_labels.append(attributes.get("aria-label", ""))
        if tag not in self.VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack:
            self.errors.append(f"unexpected closing tag: {tag}")
            return
        expected = self.stack.pop()
        if expected != tag:
            self.errors.append(f"expected closing tag {expected}, got {tag}")


class GxVisualizePublicDocsTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"required public file is missing: {path}")
        return path.read_text(encoding="utf-8")

    def load_json(self, path: Path) -> dict:
        return json.loads(self.read(path))

    def test_public_manifests_publish_matching_release_versions(self):
        version = self.load_json(CLAUDE_MANIFEST)["version"]
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertEqual(self.load_json(CODEX_MANIFEST)["version"], version)

        marketplace = self.load_json(MARKETPLACE)
        plugin = next(
            item for item in marketplace["plugins"] if item["name"] == "oh-my-gx"
        )
        self.assertEqual(plugin["version"], version)

    def test_readme_publishes_current_skill_contract(self):
        self.assertTrue(SKILL_DIR.is_dir(), "gx-visualize skill directory must ship")
        readme = self.read(README)

        self.assertIn("gx-visualize", readme)
        self.assertIn("docs/gx-visualize-guide.md", readme)
        self.assertIn("GX 스킬 16개", readme)
        guide = self.read(ROOT / "docs/gx-visualize-guide.md")

        for term in (
            "시각화 포함",
            "trace",
            "progress",
            "impact",
            ".dev/{branch-slug}/visual/",
            "Archify",
            "Mermaid",
            "정적 HTML",
        ):
            with self.subTest(term=term):
                self.assertIn(term, guide)

        self.assertIn("실행에 실패하면", guide)
        self.assertIn("운영 토폴로지", guide)

    def test_github_pages_publishes_accessible_visualization_feature(self):
        page = self.read(INDEX)

        for term in (
            "gx-visualize",
            "trace",
            "progress",
            "impact",
            ".dev/{branch-slug}/visual/",
            "docs/gx-visualize-guide.md",
        ):
            with self.subTest(term=term):
                self.assertTrue(term in page, f"public visualization reference missing: {term}")

        self.assertIn('id="skills"', page)
        self.assertEqual(len(list((ROOT / ".claude/skills").glob("gx-*/SKILL.md"))), 16)

        parser = BalancedHtmlParser()
        parser.feed(page)
        self.assertTrue(any("gx-visualize" in label for label in parser.image_labels))
        self.assertTrue(all(parser.image_labels), "terminal examples need accessible labels")

    def test_github_pages_html_is_balanced_without_script_runtime(self):
        page = self.read(INDEX)
        parser = BalancedHtmlParser()
        parser.feed(page)
        parser.close()

        self.assertEqual(parser.errors, [])
        self.assertEqual(parser.stack, [])
        self.assertNotRegex(page, r"(?i)<script\b")
        self.assertNotRegex(page, r"(?i)(?:cdn\.jsdelivr\.net|unpkg\.com)/.*mermaid")


if __name__ == "__main__":
    unittest.main()
