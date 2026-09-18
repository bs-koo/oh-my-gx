import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHASES = [
    REPO / ".claude" / "skills" / "gx-dev" / "phases" / "phase-complete.md",
    REPO / ".claude" / "skills" / "gx-tdd" / "phases" / "phase-complete.md",
]


class CompletionGateTests(unittest.TestCase):
    def _text(self, path):
        return path.read_text(encoding="utf-8")

    def test_both_pipelines_have_a_visualization_step(self):
        for path in PHASES:
            self.assertIn("Step 5.5", self._text(path), path.name)

    def test_gate_offers_session_and_full_scope(self):
        for path in PHASES:
            text = self._text(path)
            self.assertIn("--scope session", text, path.name)
            self.assertIn("--scope all", text, path.name)

    def test_headless_sessions_skip_without_asking(self):
        for path in PHASES:
            text = self._text(path)
            self.assertIn("ralph.lock", text, path.name)
            self.assertIn("strict no-op", text, path.name)

    def test_gate_never_fails_commit_or_pr(self):
        for path in PHASES:
            self.assertIn("커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다", self._text(path), path.name)

    def test_first_full_scan_warns_before_running(self):
        for path in PHASES:
            self.assertIn(".scan-manifest.json", self._text(path), path.name)

    def test_step_order_places_gate_between_5_and_6(self):
        for path in PHASES:
            text = self._text(path)
            self.assertLess(text.index("## Step 5.5"), text.index("## Step 6"), path.name)
            self.assertLess(text.index("## Step 5:"), text.index("## Step 5.5"), path.name)


if __name__ == "__main__":
    unittest.main()
