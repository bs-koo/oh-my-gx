from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_SKILL = ROOT / ".claude/skills/gx-context/SKILL.md"
CONTEXT_RULE = ROOT / ".claude/rules/context-docs.md"
STATUS_HEADER = "| ID | 요구사항 | AC | 상태 | PR |"


class ContextRequirementLedgerTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_status_template_has_canonical_ledger(self):
        text = self.read(CONTEXT_SKILL)
        self.assertIn(STATUS_HEADER, text)
        self.assertIn("|---|---|---|---|---|", text)
        self.assertIn("🚫 폐기", text)

    def test_context_rule_declares_same_schema(self):
        text = self.read(CONTEXT_RULE)
        self.assertIn(STATUS_HEADER, text)
        self.assertIn("FR-N", text)
        self.assertIn("NFR-N", text)


if __name__ == "__main__":
    unittest.main()
