"""단위테스트계획서 역보강 지시문 계약."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def between(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


COMPLETE = ".claude/skills/gx-tdd/phases/phase-complete.md"


class BackfillContractTests(unittest.TestCase):
    def test_floor_flow_is_gone(self):
        stale = re.compile(r"ut-scope|ut-floor|setup-testplan|Step -1\.5|\[UT: ")
        files = [*(ROOT / ".claude/skills/gx-tdd").rglob("*.md"),
                 *(ROOT / ".claude/skills/gx-dev/references/codex-roles").glob("*.md"),
                 *(ROOT / "agents" / n for n in ("product-owner.md", "red-writer.md", "test-architect.md", "reviewer.md"))]
        for path in files:
            with self.subTest(file=path.name):
                self.assertIsNone(stale.search(path.read_text(encoding="utf-8")))

    def test_ledger_step_runs_between_acceptance_and_commit(self):
        complete = read(COMPLETE)
        self.assertLess(complete.index("## Step 0:"), complete.index("## Step 0.5:"))
        self.assertLess(complete.index("## Step 0.5:"), complete.index("## Step 1:"))
        core = between(complete, "**핵심 모드이면**", "**전체 모드**")
        self.assertNotIn("Step 1 진행", core)
        self.assertEqual(core.count("Step 0.5 진행"), 2)

    def test_ledger_step_uses_helper_without_questions(self):
        step = between(read(COMPLETE), "## Step 0.5:", "## Step 1:")
        for needle in ("testPlan.path", "tests --files-from", "merge-base", "ls-files --others", "core.quotePath=false",
                       "svn status", "functions --plan", "rows --plan", "record --draft",
                       "skipped", "미지정", "커밋을 막지 않는다", "/gx-test-plan"):
            with self.subTest(needle=needle):
                self.assertIn(needle, step)
        self.assertNotIn("AskUserQuestion", step)
        self.assertNotIn("DIFF_FILE", step)  # 500줄 이상이면 --stat 요약으로 바뀌어 파일 목록을 잃는다
        self.assertEqual(step.count('"<PY>" "<DE13>"'), 4)

    def test_setup_registers_test_plan_path(self):
        section = between(read(".claude/skills/gx-setup/SKILL.md"), "### 3.5단계", "### 4단계")
        for needle in ('{"testPlan":{"path":', "~$*.xlsx", "등록 안 함", "단위테스트계획서 : 완료"):
            with self.subTest(needle=needle):
                self.assertIn(needle, section)
        for rel in (".claude/config.json", ".claude/skills/gx-setup/references/config.template.json"):
            with self.subTest(file=rel):
                self.assertEqual(json.loads(read(rel))["testPlan"], {"path": ""})

    def test_test_plan_skill_updates_registered_plan_in_place(self):
        skill = read(".claude/skills/gx-test-plan/SKILL.md")
        for needle in ("testPlan.path", "--author", "git status --porcelain", "개정이력", "testers.md", "엑셀에서 닫고"):
            with self.subTest(needle=needle):
                self.assertIn(needle, skill)
        for stale in ("_결과반영_", "export", "사본"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, skill)
        commit = read(".claude/skills/gx-commit/SKILL.md")
        self.assertIn("`.dev/ut-results/`", commit)
        self.assertNotIn("ut-results/export", commit)
        self.assertIn("계획서 반영", read(".claude/rules/skill-routing.md"))


if __name__ == "__main__":
    unittest.main()
