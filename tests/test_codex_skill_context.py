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

    def test_from_mode_persists_requirements_before_plan(self):
        text = self.read(CONTEXT_SKILL)
        producer = text.index("### C-4-1. 요구사항 원장 반영")
        planner = text.index("### C-5. 작업 계획")
        self.assertLess(producer, planner)
        section = text[producer:planner]
        for phrase in (
            "LEDGER_REQUIREMENTS",
            "기존 ID·AC·상태·PR을 유지",
            "삭제된 번호를 재사용하지 않는다",
            "승인한 경우에만 `🚫`",
            "C-5는 `LEDGER_REQUIREMENTS`의 ID",
        ):
            self.assertIn(phrase, section)

    def test_new_context_does_not_drop_extracted_requirements(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4. context 생성"):text.index("### C-5. 작업 계획")]
        self.assertIn("B-5~B-11", section)
        self.assertIn("C-4-1을 반드시 실행", section)


if __name__ == "__main__":
    unittest.main()
