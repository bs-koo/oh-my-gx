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


def static_question_shapes(markdown: str):
    """Count questions and options in fenced AskUserQuestion examples."""
    fence_lines = []
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            if in_fence:
                block = "\n".join(fence_lines)
                if "AskUserQuestion(" in block and "questions:" in block:
                    questions = len(re.findall(r"(?m)^\s*question:\s*", block))
                    options = [
                        len(re.findall(r"(?m)^\s*\{\s*label:\s*", group))
                        for group in re.findall(r"options:\s*\[(.*?)\]", block, re.S)
                    ]
                    yield questions, options
                fence_lines = []
            in_fence = not in_fence
        elif in_fence:
            fence_lines.append(line)


def validate_question_shape(questions: int, options: list[int]):
    if not 1 <= questions <= 3:
        raise AssertionError(f"question count outside 1–3: {questions}")
    if len(options) != questions:
        raise AssertionError(f"option groups {len(options)} != questions {questions}")
    for count in options:
        if not 2 <= count <= 3:
            raise AssertionError(f"option count outside 2–3: {count}")


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

    def test_static_examples_have_valid_question_and_option_counts(self):
        for path in SKILLS:
            examples = list(static_question_shapes(path.read_text(encoding="utf-8")))
            with self.subTest(skill=path.parent.name):
                self.assertGreater(len(examples), 0)
                for questions, options in examples:
                    validate_question_shape(questions, options)

    def test_static_example_checker_rejects_one_and_four_options(self):
        for count in (1, 4):
            labels = "\n".join('{ label: "Choice", description: "Meaning" },' for _ in range(count))
            fixture = f"```\nAskUserQuestion(\n questions: [{{\n question: \"Choose?\",\n options: [\n{labels}\n ]\n }}]\n)\n```"
            questions, options = next(static_question_shapes(fixture))
            with self.assertRaisesRegex(AssertionError, "option count outside 2–3"):
                validate_question_shape(questions, options)

    def test_context_correction_choice_waits_for_follow_up_answer(self):
        text = SKILLS[0].read_text(encoding="utf-8")
        align = text.split("3. 모든 프레임이 해소되면", 1)[1].split("**모호함 판단 기준**", 1)[0]
        self.assertIn('"수정 필요" 선택 시', align)
        self.assertIn("후속 질문", align)
        self.assertIn("async", align)
        self.assertIn("자연어", align)
        self.assertIn("원 질문 UI Other", align)
        self.assertLess(align.index("답변을 기다린 뒤"), align.index("패턴을 파싱"))
        self.assertNotIn("선택 후 UI Other에", align)

    def test_real_choices_do_not_claim_same_question_other_input(self):
        for path in SKILLS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                match = re.search(r'(?m)^\s*\{\s*label:[^\n]*description:\s*"Other로', text)
                self.assertIsNone(match, f"{path}: {match.group(0) if match else ''}")


if __name__ == "__main__":
    unittest.main()
