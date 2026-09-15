"""Contract checks for Codex question translation in the installed runtime."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".claude/skills/gx-dev/references/codex-runtime.md"
SKILLS = (
    ROOT / ".claude/skills/gx-context/SKILL.md",
    ROOT / ".claude/skills/gx-dev/SKILL.md",
    ROOT / ".claude/skills/gx-tdd/SKILL.md",
)
INPUT_LABEL = re.compile(
    r"label:\s*[\"'](?:Other(?:로 입력)?|직접 입력|답변 입력|주제 입력)[\"']"
)


class CodexQuestionContractTests(unittest.TestCase):
    def test_runtime_defines_codex_schema_translation(self):
        text = RUNTIME.read_text(encoding="utf-8")
        for phrase in (
            "질문 1~3개",
            "선택지 2~3개",
            "stable snake_case `id`",
            "`multiSelect`를 제거",
            "(Recommended)",
            "Other를 직접 option으로 추가하지 않는다",
            "실제 도구 스키마가 이 문서보다 우선",
            "현재 모드에서 제공된",
            "Plan 모드에서만 제공되면 기본 모드에서 호출하지 않는다",
            "자연어 fallback도 실제 답변을 기다린다",
            "capture payload",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_skills_use_common_question_bounds(self):
        for path in SKILLS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                self.assertIn("질문은 한 번에 1~3개", text)
                self.assertIn("질문마다 선택지는 2~3개", text)
                self.assertNotRegex(text, r"(?:질문|questions)[^\n]*(?:1~5|최대 5)")
                self.assertNotRegex(text, r"(?:선택지|options)[^\n]*(?:2~4|최대 4)")

    def test_skills_do_not_add_input_labels_as_options(self):
        for path in SKILLS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                self.assertIsNone(INPUT_LABEL.search(text))
                self.assertNotIn("권장 답변 + Other + 모르겠음", text)
                self.assertNotIn("예시 후보 + Other", text)

    def test_skills_use_runtime_schema_for_codex_questions(self):
        for path in SKILLS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                self.assertIn("codex-runtime.md", text)
                self.assertIn("실제 도구 스키마", text)
                self.assertIn("Other를 option으로 직접 추가하지 않는다", text)
                self.assertIn("(Recommended)", text)


if __name__ == "__main__":
    unittest.main()
