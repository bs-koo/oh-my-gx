"""`.dev` 공유 확인 절차의 계약과, 그 절차가 기대는 git 동작을 실제 저장소로 검증한다."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
REFERENCE = SKILLS / "gx-dev/references/dev-ignore-check.md"
SHARING_BLOCK = REFERENCE.with_name("dev-sharing.gitignore")
PROBE = ".dev/gx-ignore-probe"
CONSUMERS = {
    SKILLS / "gx-setup/SKILL.md": SKILLS / "gx-setup",
    SKILLS / "gx-context/modes/plan.md": SKILLS / "gx-context",
    SKILLS / "gx-dev/phases/phase-setup.md": SKILLS / "gx-dev/phases",
    SKILLS / "gx-tdd/phases/phase-setup.md": SKILLS / "gx-tdd/phases",
}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DevIgnoreContractTests(unittest.TestCase):
    def test_reference_decides_with_quiet_flag_and_dotless_probe(self):
        ref = text(REFERENCE)
        self.assertIn(f"git check-ignore -q {PROBE}", ref)
        self.assertIn("판정에는 `-v`를 쓰지 않는다", ref)
        self.assertIn("점 없이 쓴다", ref)
        self.assertNotIn(".dev/.gx-ignore-probe", ref)

    def test_reference_fix_rules_cover_broad_patterns_and_global_settings(self):
        ref = text(REFERENCE)
        for phrase in (
            'Read("dev-sharing.gitignore")',
            "`.git/info/exclude`",
            "고치지 않는다. 다른 저장소에도 영향을 주므로",
            "헤드리스 세션",
            "같은 출처·줄이 다시 나오면",
        ):
            self.assertIn(phrase, ref)

    def test_every_consumer_reads_the_shared_reference(self):
        for path, base in CONSUMERS.items():
            with self.subTest(path=path.relative_to(SKILLS)):
                body = text(path)
                refs = [line for line in body.splitlines() if "dev-ignore-check.md" in line]
                self.assertTrue(refs, "공유 확인 참조 없음")
                rel = refs[0].split('Read("', 1)[1].split('")', 1)[0]
                self.assertEqual((base / rel).resolve(), REFERENCE.resolve())

    def test_commit_warns_without_editing_ignore_rules(self):
        commit = text(SKILLS / "gx-commit/SKILL.md")
        self.assertIn("Bash(git check-ignore:*)", commit)
        step = commit.split("4.5. **`.dev` 무시 경고**", 1)[1].split("\n5.", 1)[0]
        self.assertIn(f"git check-ignore -q {PROBE}", step)
        self.assertIn("커밋은 막지 않고 `.gitignore`도 여기서 고치지 않는다", step)


@unittest.skipUnless(shutil.which("git"), "git 필요")
class DevIgnoreGitBehaviourTests(unittest.TestCase):
    """참조 문서가 주장하는 git 동작이 실제와 같은지 확인한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def ignored(self, path=PROBE) -> int:
        return subprocess.run(["git", "check-ignore", "-q", path], cwd=self.repo).returncode

    def write(self, rules: str):
        (self.repo / ".gitignore").write_text(rules, encoding="utf-8")

    def test_quiet_check_detects_every_dev_pattern_form(self):
        for rules in (".dev\n", "/.dev/\n", ".dev/*\n", "**/.dev/\n", ".*\n", "*\n!*/\n"):
            with self.subTest(rules=rules):
                self.write(rules)
                self.assertEqual(self.ignored(), 0)
        self.write("build/\n")
        self.assertEqual(self.ignored(), 1)

    def test_info_exclude_is_detected(self):
        (self.repo / ".git/info/exclude").write_text(".dev/\n", encoding="utf-8")
        self.assertEqual(self.ignored(), 0)
        out = subprocess.run(["git", "check-ignore", "-v", PROBE], cwd=self.repo,
                             capture_output=True, text=True).stdout
        self.assertIn(".git/info/exclude:1:.dev/", out)

    def test_dotted_probe_would_be_misjudged_by_dotfile_pattern(self):
        self.write(".*\n!.dev/\n")
        self.assertEqual(self.ignored(PROBE), 1)
        self.assertEqual(self.ignored(".dev/.gx-ignore-probe"), 0)

    def test_two_negations_unignore_dev_but_keep_other_dotfiles(self):
        for broad in (".*\n", "*\n!*/\n", "*\n"):
            with self.subTest(broad=broad):
                self.write(broad + "!.gitignore\n!.dev/\n!.dev/**\n")
                self.assertEqual(self.ignored(), 1)
                self.assertEqual(self.ignored(".dev/plan.md"), 1)
                self.assertEqual(self.ignored(".envrc"), 0)

    def test_single_dir_negation_is_not_enough_for_star(self):
        self.write("*\n!.gitignore\n!.dev/\n")
        self.assertEqual(self.ignored(), 0)

    def test_verbose_exit_code_reports_negation_as_match(self):
        self.write("*\n!*/\n!.dev/**\n")
        self.assertEqual(self.ignored(), 1)
        verbose = subprocess.run(["git", "check-ignore", "-v", PROBE], cwd=self.repo,
                                 capture_output=True, text=True)
        self.assertEqual(verbose.returncode, 0)
        self.assertIn("!.dev/**", verbose.stdout)

    def stage_files(self, paths):
        for name in paths:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        return subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=self.repo,
                              capture_output=True, text=True, check=True).stdout.splitlines()

    def test_sharing_block_keeps_other_dev_names_ignored(self):
        self.write(".dev*\n" + text(SHARING_BLOCK))
        private = (".dev-private/local.json", ".development/settings.json", ".dev.env")
        for path in private:
            with self.subTest(path=path):
                self.assertEqual(self.ignored(path), 0)
        self.assertEqual(self.ignored(".dev/plan.md"), 1)
        staged = self.stage_files((".dev/plan.md", *private))
        self.assertIn(".dev/plan.md", staged)
        self.assertTrue(set(private).isdisjoint(staged))

    def test_sharing_block_keeps_question_state_out_of_index(self):
        runtime = ("pending-question.json", "answered-question.json", ".question-lock", "model-dispatches.jsonl")
        old_rules = "".join(f".dev/*/{name}\n" for name in runtime)
        for broad in (".*\n", "*\n", ".dev*\n"):
            with self.subTest(broad=broad):
                self.write(old_rules + broad + text(SHARING_BLOCK))
                for name in runtime:
                    self.assertEqual(self.ignored(f".dev/task/{name}"), 0)
                self.assertEqual(self.ignored(".dev/plan.md"), 1)
        staged = self.stage_files((".dev/plan.md", *(f".dev/task/{name}" for name in runtime)))
        self.assertIn(".dev/plan.md", staged)
        self.assertTrue(all(f".dev/task/{name}" not in staged for name in runtime))

    def test_sharing_block_preserves_narrow_rules_after_it(self):
        self.write("*.log\n.dev/private/**\n.*\n" + text(SHARING_BLOCK)
                   + "/.dev/**/*.log\n/.dev/private/**\n!/.dev/private/public.md\n")
        self.assertEqual(self.ignored(".dev/plan.md"), 1)
        for path in (".dev/task/verify.log", ".dev/private/local.json", "outside.log", ".env"):
            with self.subTest(path=path):
                self.assertEqual(self.ignored(path), 0)
        self.assertEqual(self.ignored(".dev/private/public.md"), 1)
        staged = self.stage_files((".dev/plan.md", ".dev/task/verify.log", ".dev/private/local.json",
                                   ".dev/private/public.md", "outside.log", ".env"))
        self.assertIn(".dev/private/public.md", staged)
        self.assertTrue({".dev/task/verify.log", ".dev/private/local.json", "outside.log", ".env"}.isdisjoint(staged))

    def test_sharing_block_works_in_local_exclude(self):
        (self.repo / ".git/info/exclude").write_text(".dev*\n" + text(SHARING_BLOCK), encoding="utf-8")
        self.assertEqual(self.ignored(".dev/plan.md"), 1)
        self.assertEqual(self.ignored(".dev/task/pending-question.json"), 0)
        self.assertEqual(self.ignored(".dev-private/local.json"), 0)


if __name__ == "__main__":
    unittest.main()
