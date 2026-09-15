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
            self.assertIn(
                "requirements`: `[setup, requirements]`를 실행하여 작업환경과 "
                "도메인 컨텍스트를 확정한 뒤 PRD를 작성한다.",
                selection,
                path,
            )
            self.assertIn("design`: `[setup, design]`", selection, path)

    def test_design_gate_precedes_phase_file_execution(self):
        for path in (DEV, TDD):
            text = self.read(path)
            loop_start = text.index("### Phase 실행 루프")
            loop_end = text.index("### Phase 파일 경로", loop_start)
            loop = text[loop_start:loop_end]
            design_list = "PHASES = [setup, design]"
            design_gate = (
                'if phase == "design" and not exists("${DEV_DIR}/prd.md"):\n'
                "        → phase-requirements부터 실행"
            )
            phase_execution = '# 2b. Phase 파일 Read (필수)\n    Read("phases/phase-{phase}.md")'

            self.assertIn(design_gate, loop, path)
            self.assertIn(phase_execution, loop, path)
            self.assertLess(loop.index(design_list), loop.index(design_gate), path)
            self.assertLess(loop.index(design_gate), loop.index(phase_execution), path)


if __name__ == "__main__":
    unittest.main()
