import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import ROOT, load


class ResourceTests(unittest.TestCase):
    def fixture(self, directory, model="opus", newline="\n"):
        root = Path(directory)
        (root / "agents").mkdir()
        (root / ".claude").mkdir()
        role = ("---\nname: reviewer\nmodel: " + model +
                "\ntools:\n  - Read\n  - Grep\n---\n# 역할\n코드를 수정하지 않는다.\n")
        (root / "agents/reviewer.md").write_bytes(role.replace("\n", newline).encode("utf-8"))
        config = b'{"vcs":"git"}\n'
        (root / ".claude/config.json").write_bytes(config)
        return root, config

    def test_role_body_tools_tier_and_template_survive_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root, config = self.fixture(directory)
            sync = load("gx_sync", "scripts/sync-codex-resources.py")
            files = sync.expected_files(root)
            base = root / ".claude/skills/gx-dev/references/codex-roles"
            self.assertEqual(files[base / "reviewer.md"],
                             "# 역할\n코드를 수정하지 않는다.\n".encode())
            self.assertEqual(json.loads(files[base / "index.json"]), {
                "reviewer": {"tier": "high", "file": "reviewer.md", "tools": ["Read", "Grep"]}
            })
            self.assertEqual(files[root / ".claude/skills/gx-setup/references/config.template.json"], config)

    def test_sonnet_and_crlf_normalize_to_utf8_lf(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.fixture(directory, model="sonnet", newline="\r\n")
            files = load("gx_sync", "scripts/sync-codex-resources.py").expected_files(root)
            base = root / ".claude/skills/gx-dev/references/codex-roles"
            self.assertEqual(files[base / "reviewer.md"], "# 역할\n코드를 수정하지 않는다.\n".encode())
            self.assertEqual(json.loads(files[base / "index.json"])["reviewer"]["tier"], "mid")

    def test_unsupported_model_fails_input_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.fixture(directory, model="haiku")
            with self.assertRaises(ValueError):
                load("gx_sync", "scripts/sync-codex-resources.py").expected_files(root)

    def test_check_detects_changed_role_template_and_stale_role(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.fixture(directory)
            sync = load("gx_sync", "scripts/sync-codex-resources.py")
            sync.write_files(root)
            self.assertEqual(sync.check_files(root), [])
            (root / "agents/reviewer.md").write_text(
                "---\nname: reviewer\nmodel: opus\ntools:\n  - Read\n---\n# changed\n", encoding="utf-8")
            self.assertTrue(sync.check_files(root))
            sync.write_files(root)
            (root / ".claude/config.json").write_bytes(b'{"vcs":"svn"}\n')
            self.assertTrue(sync.check_files(root))
            sync.write_files(root)
            (root / ".claude/skills/gx-dev/references/codex-roles/stale.md").write_text("stale")
            self.assertTrue(sync.check_files(root))

    def test_real_export_is_self_contained_for_skills_only_install(self):
        sync = load("gx_sync", "scripts/sync-codex-resources.py")
        expected = sync.expected_files(ROOT)
        self.assertEqual(len(list((ROOT / "agents").glob("*.md"))), 17)
        role_base = ROOT / ".claude/skills/gx-dev/references/codex-roles"
        self.assertEqual(len(json.loads(expected[role_base / "index.json"])), 17)
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            for source, content in expected.items():
                target = copy / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            self.assertFalse((copy / "agents").exists())
            self.assertFalse((copy / ".claude/config.json").exists())
            for source, content in expected.items():
                self.assertEqual((copy / source.relative_to(ROOT)).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
