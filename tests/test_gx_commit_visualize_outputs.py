import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMMIT_SKILL = REPO / ".claude" / "skills" / "gx-commit" / "SKILL.md"


def _reset_command(text):
    match = re.search(r"`(git reset -q -- [^`]+)`", text)
    return match.group(1) if match else None


class CommitExcludesVisualizeOutputsTests(unittest.TestCase):
    def setUp(self):
        self.text = COMMIT_SKILL.read_text(encoding="utf-8")

    def test_reset_command_names_both_output_locations(self):
        command = _reset_command(self.text)
        self.assertIsNotNone(command)
        self.assertIn("'.dev/architecture'", command)
        self.assertIn("'.dev/*/visual/*'", command)

    def test_other_slug_question_does_not_ask_about_visualize_outputs(self):
        self.assertIn("gx-visualize의 단발성 산출물", self.text)

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_documented_pathspecs_actually_unstage_the_outputs(self):
        """문서의 pathspec을 실제 저장소에서 실행한다 - 문자열 검사로는 매치 여부를 알 수 없다."""
        specs = re.findall(r"'([^']+)'", _reset_command(self.text))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                return subprocess.run(
                    ["git", "-c", "user.name=gx", "-c", "user.email=gx@example.com", "-c", "commit.gpgsign=false", *args],
                    cwd=root, check=True, capture_output=True, text=True,
                )

            git("init", "-q")
            git("commit", "-q", "--allow-empty", "-m", "init")
            for relative in (
                ".dev/architecture/domains/user.html",
                ".dev/architecture/assets/mermaid.min.js",
                ".dev/feat-x/visual/trace.html",
                ".dev/feat-x/visual/sub/trace.json",
                ".dev/feat-x/state.md",
                "src/App.java",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n", encoding="utf-8")
            git("add", "-A")
            subprocess.run(["git", "reset", "-q", "--", *specs], cwd=root, check=False, capture_output=True)
            staged = git("diff", "--cached", "--name-only").stdout.split()
        self.assertEqual(sorted(staged), [".dev/feat-x/state.md", "src/App.java"])


if __name__ == "__main__":
    unittest.main()
