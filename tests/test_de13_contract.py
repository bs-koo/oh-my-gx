"""단위테스트계획서 연동 지시문 계약 — 최종 리뷰 I1~I5·M7 회귀."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TDD = ROOT / ".claude/skills/gx-tdd"


def read(rel: str) -> str:
    return (TDD / rel).read_text(encoding="utf-8")


def between(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


class TestPlanLinkContractTests(unittest.TestCase):
    def test_ralph_return_and_reentry_paths_run_floor_gate(self):
        complete = read("phases/phase-complete.md")
        tdd_gate = between(complete, "## Step -2:", "## Step -1.5:")
        self.assertIn("Step -1.5로", tdd_gate)
        self.assertNotIn("Step -1로 진행", tdd_gate)
        verify = between(complete, "## Step -1:", "## Step 0:")
        self.assertNotRegex(verify, r"Step -1(?: verify)?부터 재실행")
        self.assertEqual(verify.count("Step -1.5부터 재실행"), 2)

    def test_function_list_is_not_written_into_project_before_opt_in(self):
        plan = read("phases/setup-testplan.md")
        self.assertNotIn("export/functions.json", plan)
        self.assertIn("mktemp -d", plan)

    def test_declined_link_is_recorded_and_respected(self):
        state = read("references/pipeline-state.md")
        self.assertIn("`ut-scope: off`", state)
        self.assertIn("`ut-scope: off`", read("phases/setup-testplan.md"))
        env8 = next(l for l in read("SKILL.md").splitlines() if l.startswith("> 8."))
        self.assertIn("`off`", env8)
        stale = re.compile(r"ut-scope`?가 (?:있으면|없으면|있을 때만|있고)|`ut-scope` 있음")
        for rel in ("SKILL.md", "references/pipeline-state.md", "phases/setup-testplan.md",
                    "phases/setup-resume.md", "phases/phase-requirements.md", "phases/phase-design.md",
                    "phases/phase-implement.md", "phases/phase-review.md", "phases/phase-complete.md"):
            with self.subTest(file=rel):
                self.assertIsNone(stale.search(read(rel)))

    def test_setup_step7_records_ut_scope_and_ignore_runs_in_step6(self):
        setup = read("phases/phase-setup.md")
        self.assertIn("ut-scope", between(setup, "## Step 7:", "**작업 계획 되돌림**"))
        self.assertIn("Step 6에서", between(read("phases/setup-testplan.md"), "## 4.", "## 5."))
        self.assertLessEqual(len(setup.replace("\r", "").encode("utf-8")), 22000)

    def test_scope_marks_previous_passes_from_ledger(self):
        save = between(read("phases/setup-testplan.md"), "## 3.", "## 4.")
        self.assertIn("--ledger-dir", save)
        self.assertIn("제외(원장 Pass)", save)

    def test_python_command_is_resolved_once_and_reused(self):
        plan = read("phases/setup-testplan.md")
        self.assertIn("`PY`", plan)
        complete = read("phases/phase-complete.md")
        self.assertNotIn('python3 "<DE13>"', complete)
        self.assertEqual(complete.count('"<PY>" "<DE13>"'), 2)
        gate = between(complete, "## Step -1.5:", "## Step -1:")
        self.assertIn("Python", gate)
        self.assertIn("중단", gate)


if __name__ == "__main__":
    unittest.main()
