"""공통 리소스가 제거된 개발 스킬에 의존하지 않는지 확인한다."""

import importlib.util
import json
import re
import shutil
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UnifiedDistributionTests(unittest.TestCase):
    def test_skill_entries_fit_reload_budget(self):
        oversized = []
        for path in (ROOT / ".claude/skills").glob("*/SKILL.md"):
            normalized = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
            if len(normalized.encode("utf-8")) >= 20000:
                oversized.append(path.parent.name)
        self.assertEqual(oversized, [], "진입 지시문은 20KB 미만, 상세는 조건부 참조로 둡니다")

    def test_only_tdd_development_entry_is_distributed(self):
        skills = ROOT / ".claude/skills"
        self.assertFalse((skills / "gx-dev").exists())
        self.assertTrue((skills / "gx-work/SKILL.md").is_file())
        self.assertTrue((skills / "gx-tdd/SKILL.md").is_file())
        for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            data = json.loads((ROOT / manifest).read_text(encoding="utf-8"))
            self.assertEqual(data["skills"], "./.claude/skills/")

    def test_removed_unattended_runtime_is_not_distributed(self):
        skills = ROOT / ".claude/skills"
        self.assertEqual(len(list(skills.glob("gx-*/SKILL.md"))), 16)
        for relative in (".claude/skills/gx-ralph", ".claude/skills/gx-ralph-iterate",
                         "scripts/gx-ralph.sh", "scripts/test-gx-ralph.sh"):
            self.assertFalse((ROOT / relative).exists(), relative)
        workflow = (ROOT / ".github/workflows/lint.yml").read_text(encoding="utf-8")
        self.assertNotIn("test-gx-ralph.sh", workflow)

    def test_review_contract_survives_installation_without_source_repository(self):
        sources = ("gx-work/SKILL.md", "gx-context/SKILL.md", "gx-context/references/intake.md",
                   "gx-tdd/phases/phase-design.md", "gx-tdd/phases/phase-complete.md", "gx-verify/SKILL.md")
        with tempfile.TemporaryDirectory() as temporary:
            installed = Path(temporary) / "plugin/.claude/skills"
            shutil.copytree(ROOT / ".claude/skills", installed)
            target = (installed / "gx-work/references/reviewability.md").resolve()
            self.assertTrue(target.is_file())
            for relative in sources:
                consumer = installed / relative
                links = re.findall(r"\]\(([^)]+reviewability\.md)\)", consumer.read_text(encoding="utf-8"))
                self.assertEqual(len(links), 1, relative)
                self.assertEqual((consumer.parent / links[0]).resolve(), target, relative)

    def test_history_contract_and_helper_resolve_from_installed_plugin(self):
        sources = ("gx-work/references/tdd-entry.md", "gx-context/references/intake.md",
                   "gx-tdd/references/document-lifecycle.md", "gx-tdd/phases/phase-requirements.md",
                   "gx-tdd/phases/phase-design.md")
        with tempfile.TemporaryDirectory() as temporary:
            plugin = Path(temporary) / "installed plugin"
            installed = plugin / ".claude/skills"
            shutil.copytree(ROOT / ".claude/skills", installed)
            (plugin / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts/gx-history.py", plugin / "scripts/gx-history.py")
            target = (installed / "gx-work/references/decision-history.md").resolve()
            for relative in sources:
                consumer = installed / relative
                links = re.findall(r"\]\(([^)]*decision-history\.md)\)", consumer.read_text(encoding="utf-8"))
                self.assertEqual(len(links), 1, relative)
                self.assertEqual((consumer.parent / links[0]).resolve(), target, relative)
            links = re.findall(r"\]\(([^)]+gx-history\.py)\)", target.read_text(encoding="utf-8"))
            self.assertEqual(len(links), 1)
            self.assertEqual((target.parent / links[0]).resolve(), (plugin / "scripts/gx-history.py").resolve())
            self.assertTrue((target.parent / links[0]).is_file())

    def test_exported_roles_are_owned_by_the_common_entry(self):
        path = ROOT / "scripts/sync-codex-resources.py"
        spec = importlib.util.spec_from_file_location("gx_sync_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.ROLE_DIR, Path(".claude/skills/gx-work/references/codex-roles"))
        generated = module.expected_files(ROOT)
        index = ROOT / module.ROLE_DIR / "index.json"
        self.assertIn(index, generated)
        self.assertIn("red-writer", json.loads(generated[index]))

    def test_installed_skills_do_not_reference_removed_runtime(self):
        stale = []
        for path in (ROOT / ".claude/skills").rglob("*.md"):
            if "gx-dev" in path.parts:
                continue
            text = path.read_text(encoding="utf-8-sig")
            if "gx-dev/references/" in text:
                stale.append(str(path.relative_to(ROOT)))
        self.assertEqual(stale, [], "소비 프로젝트에서 사라진 경로를 참조합니다")


if __name__ == "__main__":
    unittest.main()
