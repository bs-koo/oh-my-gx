"""setup의 명시 요청/저장 재개 범위 정책 검사. 실제 앱 smoke와는 구분한다."""

from copy import deepcopy
from pathlib import Path
import re
import unittest

from test_codex_core_plan_edges import documented_policy


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
SETUPS = {
    "gx-tdd": "phases/setup-resume.md",
}


class CoreEntryResumeTests(unittest.TestCase):
    def setup_text(self, pipeline):
        return (SKILLS / pipeline / SETUPS[pipeline]).read_text(encoding="utf-8")

    def phase_scope(self, pipeline, requested_phase):
        self.assertEqual(pipeline, "gx-tdd")
        select = documented_policy(self, "gx-tdd/references/core-planning.md", "select_phases")
        return select("all", requested_phase)

    def apply_scope(self, pipeline, requested_phase, saved):
        blocks = re.findall(r"```python\n(.*?)\n```", self.setup_text(pipeline), re.S)
        source = next((block for block in blocks if "scope_updates" in block and "current_requested_phase" in block), None)
        self.assertIsNotNone(source, f"{pipeline}: setup의 실행 가능한 명시 요청/재개 분기 누락")
        select = documented_policy(self, "gx-tdd/references/core-planning.md", "select_phases")
        namespace = {
            "mode": saved["mode"], "select_phases": select,
            "current_requested_phase": requested_phase,
            "saved_requested_phase": saved["requested-phase"],
            "saved_state": saved,
            "PHASES": self.phase_scope(pipeline, requested_phase or saved["requested-phase"]),
        }
        exec(compile(source, f"{pipeline}:setup-scope", "exec"), namespace)
        return namespace["scope_updates"]

    def saved_applied_state(self):
        return {
            "mode": "all", "mode-transition-status": "applied",
            "requested-phase": None,
            "execution-phases": ["requirements", "design", "implement", "review", "complete"],
            "phase": "design", "current-step": "설계 Q&A",
            "phases": {"requirements": "completed", "design": "in_progress"},
            "reports": ["reports/g1/t1-red.md"], "baseline-generation": "g1",
        }

    def test_new_explicit_scope_survives_applied_transition_and_old_design_cursor(self):
        for pipeline in SETUPS:
            for requested_phase in ("requirements", "design", "implement", "review", "complete"):
                with self.subTest(pipeline=pipeline, phase=requested_phase):
                    saved = self.saved_applied_state()
                    original = deepcopy(saved)
                    updates = self.apply_scope(pipeline, requested_phase, saved)
                    self.assertEqual(updates, {
                        "requested-phase": requested_phase,
                        "execution-phases": self.phase_scope(pipeline, requested_phase),
                        "phase": self.phase_scope(pipeline, requested_phase)[0], "current-step": None,
                    })
                    self.assertEqual(saved, original, "범위 결정은 원래 증거/커서를 삭제하지 않는다")
                    saved.update(updates)
                    resumed = self.apply_scope(pipeline, None, saved)
                    self.assertEqual(resumed, updates, "다음 재개도 새 단독 범위/커서를 사용한다")

    def test_resume_without_new_phase_keeps_saved_full_scope_and_interrupted_step(self):
        for pipeline in SETUPS:
            with self.subTest(pipeline=pipeline):
                saved = self.saved_applied_state()
                updates = self.apply_scope(pipeline, None, saved)
                self.assertEqual(updates["execution-phases"], saved["execution-phases"])
                self.assertEqual(updates["phase"], "design")
                self.assertEqual(updates["current-step"], "설계 Q&A")
                self.assertIsNone(updates["requested-phase"])

    def test_resume_contract_keeps_the_required_question_gate(self):
        text = self.setup_text("gx-tdd")
        self.assertIn("미응답", text)
        self.assertIn("실제 응답", text)
        self.assertIn("core-planning.md", text)
        self.assertIn("scope_updates", text)


if __name__ == "__main__":
    unittest.main()
