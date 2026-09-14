"""Integration checks for Codex project config merges."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import ROOT


HELPER = ROOT / 'scripts/codex-project-config.py'


class ProjectConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gx config 한글 ')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.cwd = self.parent / 'project with spaces'
        self.cwd.mkdir()
        self.config = self.cwd / '.claude/config.json'
        self.settings = self.cwd / '.claude/settings.local.json'
        self.template = self.parent / 'config.template.json'
        self.template.write_text(json.dumps({
            'vcs': '', 'modelProfile': '',
            'projectTypes': {'node': {'detect': ['package.json'], 'test': 'old'}},
            'templateOnly': {'keep': True}}, ensure_ascii=False), encoding='utf-8')
        self.updates = self.parent / 'updates.json'

    def invoke(self, *, cwd=None, template=None):
        return subprocess.run([sys.executable, str(HELPER),
                               '--cwd', str(self.cwd if cwd is None else cwd),
                               '--template', str(self.template if template is None else template),
                               '--updates', str(self.updates)],
                              capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=15)

    def write_updates(self, data):
        self.updates.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def test_existing_config_preserves_unrelated_top_and_nested_keys(self):
        self.config.parent.mkdir()
        self.config.write_text(json.dumps({
            'vcs': '', 'modelProfile': '', 'fixtureKeep': {'nested': {'x': 1}},
            'projectTypes': {'node': {'test': 'old', 'detect': ['package.json'],
                                      'fixtureKeep': {'leaf': '보존'}}}},
            ensure_ascii=False), encoding='utf-8')
        self.settings.write_bytes(b'{"permissions":{"allow":["old"]}}\r\n')
        old_settings = self.settings.read_bytes()
        self.write_updates({'vcs': 'git', 'modelProfile': 'standard',
                            'projectTypes': {'node': {'test': 'npm test', 'new': 'yes'}}})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(self.config) + '\n')
        self.assertEqual(json.loads(self.config.read_text(encoding='utf-8')), {
            'vcs': 'git', 'modelProfile': 'standard', 'fixtureKeep': {'nested': {'x': 1}},
            'projectTypes': {'node': {'test': 'npm test', 'detect': ['package.json'],
                                      'fixtureKeep': {'leaf': '보존'}, 'new': 'yes'}}})
        self.assertEqual(self.settings.read_bytes(), old_settings)

    def test_semantic_noop_preserves_existing_bytes(self):
        self.config.parent.mkdir()
        old = b'{  "modelProfile" : "eco",\r\n "vcs":"git" }\r\n'
        self.config.write_bytes(old)
        self.write_updates({'vcs': 'git', 'modelProfile': 'eco'})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_bytes(), old)

    def test_missing_config_uses_template_and_merges_only_updates(self):
        self.write_updates({'vcs': 'git', 'projectTypes': {'node': {'test': 'npm test'}}})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(self.config) + '\n')
        self.assertEqual(json.loads(self.config.read_text(encoding='utf-8')), {
            'vcs': 'git', 'modelProfile': '',
            'projectTypes': {'node': {'detect': ['package.json'], 'test': 'npm test'}},
            'templateOnly': {'keep': True}})
        self.assertFalse(self.settings.exists())

    def test_existing_config_does_not_read_template(self):
        self.config.parent.mkdir()
        self.config.write_text('{"vcs":""}', encoding='utf-8')
        self.write_updates({'vcs': 'git'})
        result = self.invoke(template=self.parent / 'missing-template.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.config.read_text(encoding='utf-8')), {'vcs': 'git'})

    def test_malformed_updates_leave_existing_config_unchanged(self):
        self.config.parent.mkdir()
        old = b'{"fixtureKeep":"unchanged"}\n'
        self.config.write_bytes(old)
        for invalid in ('{broken', '[]', '{"vcs":NaN}'):
            with self.subTest(invalid=invalid):
                self.updates.write_text(invalid, encoding='utf-8')
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertEqual(self.config.read_bytes(), old)

    def test_malformed_existing_or_template_does_not_write(self):
        self.config.parent.mkdir()
        self.write_updates({'vcs': 'git'})
        old = b'{not json'
        self.config.write_bytes(old)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), old)
        self.assertEqual(result.stdout, '')
        self.config.unlink()
        self.template.write_text('{not json', encoding='utf-8')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.config.exists())
        self.assertEqual(result.stdout, '')

    def test_deep_unknown_values_are_not_truncated(self):
        self.config.parent.mkdir()
        nested = {'leaf': '보존'}
        for _ in range(30):
            nested = {'layer': nested}
        self.config.write_text(json.dumps({'vcs': '', 'deepKeep': nested},
                                          ensure_ascii=False), encoding='utf-8')
        self.write_updates({'vcs': 'git'})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.config.read_text(encoding='utf-8'))['deepKeep'], nested)

    def test_missing_cwd_fails_without_creating_config(self):
        self.write_updates({'vcs': 'git'})
        missing = self.parent / 'missing project'
        result = self.invoke(cwd=missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertFalse((missing / '.claude/config.json').exists())
