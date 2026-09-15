"""Contract checks for Codex question translation in the installed runtime."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".claude/skills/gx-dev/references/codex-runtime.md"


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


if __name__ == "__main__":
    unittest.main()
