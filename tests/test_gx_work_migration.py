"""공통 리소스가 제거된 개발 스킬에 의존하지 않는지 확인한다."""

import importlib.util
import json
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
