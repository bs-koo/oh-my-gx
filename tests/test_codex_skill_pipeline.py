from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / ".claude/skills/gx-dev/SKILL.md"
TDD = ROOT / ".claude/skills/gx-tdd/SKILL.md"


class PipelineBootstrapContractTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_partial_phase_lists_include_setup(self):
        for path in (DEV, TDD):
            text = self.read(path)
            loop = text[
                text.index("### Phase 실행 루프") : text.index("### Phase 파일 경로")
            ]
            self.assertIn('elif --phase == "requirements":', loop, path)
            self.assertIn("PHASES = [setup, requirements]", loop, path)
            self.assertIn('elif --phase == "design":', loop, path)
            self.assertIn("PHASES = [setup, design]", loop, path)
            remaining = "PHASES = [해당 phase만]"
            self.assertIn(remaining, loop, path)
            self.assertLess(loop.index("PHASES = [setup, design]"), loop.index(remaining))

    def test_phase_selection_matches_loop(self):
        for path in (DEV, TDD):
            text = self.read(path)
            selection = text[text.index("## Phase 선택") :]
            self.assertIn("requirements`: `[setup, requirements]`", selection, path)
            self.assertIn("design`: `[setup, design]`", selection, path)


if __name__ == "__main__":
    unittest.main()
