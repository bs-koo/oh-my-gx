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

    def handle_starttag(self, tag, attrs):
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

    def test_public_manifests_release_version_1_33_0(self):
        self.assertEqual(self.load_json(CLAUDE_MANIFEST)["version"], "1.33.0")
        self.assertEqual(self.load_json(CODEX_MANIFEST)["version"], "1.33.0")

        marketplace = self.load_json(MARKETPLACE)
        plugin = next(
            item for item in marketplace["plugins"] if item["name"] == "oh-my-gx"
        )
        self.assertEqual(plugin["version"], "1.33.0")

    def test_readme_publishes_eighteenth_skill_contract(self):
        self.assertTrue(SKILL_DIR.is_dir(), "gx-visualize skill directory must ship")
        readme = self.read(README)

        for term in (
            "18번째 스킬",
            "gx-visualize",
            "시각화 포함",
            "trace",
            "progress",
            "impact",
            ".dev/{branch-slug}/visual/",
            "Archify → Mermaid → 정적 HTML",
            "docs/gx-visualize-guide.md",
        ):
            with self.subTest(term=term):
                self.assertIn(term, readme)

        self.assertIn("Archify가 없거나 실행에 실패", readme)
        self.assertIn("운영 인프라를 자동 탐색하지", readme)
        self.assertIn("GX 스킬 18개", readme)

    def test_github_pages_publishes_accessible_visualization_feature(self):
        page = self.read(INDEX)

        for term in (
            "18개 스킬이 사이클을 나눠 맡습니다",
            "gx-visualize",
            "요구사항 추적 맵을 시각화해줘",
            "trace · progress · impact",
            ".dev/{branch-slug}/visual/",
            "Archify → Mermaid → 정적 HTML",
            "docs/gx-visualize-guide.md",
        ):
            with self.subTest(term=term):
                self.assertIn(term, page)

        self.assertIn('aria-label="gx-visualize 한국어 출력 흐름 예시"', page)
        self.assertIn("Archify가 없거나 실행에 실패", page)
        self.assertIn("운영 인프라를 자동 탐색하지", page)
        self.assertNotIn("17개 스킬이 사이클을 나눠 맡습니다", page)

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
