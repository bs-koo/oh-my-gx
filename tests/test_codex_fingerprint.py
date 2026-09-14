"""Process-level checks for the Codex fingerprint's Git side effects."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import ROOT


HELPER = ROOT / 'scripts/codex-fingerprint.py'


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gx fingerprint 한글 ')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.cwd = self.parent / 'project with spaces 한글'
        self.cwd.mkdir()
        self.env = os.environ.copy()
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.git(self.cwd, 'init', '-q', '-b', 'feat/t')
        self.git(self.cwd, 'config', 'user.email', 'gx@test.invalid')
        self.git(self.cwd, 'config', 'user.name', 'GX fixture')
        (self.cwd / 'tracked.txt').write_text('base\n', encoding='utf-8')
        (self.cwd / '.dev').mkdir()
        (self.cwd / '.dev/state.md').write_text('state: old\n', encoding='utf-8')
        self.git(self.cwd, 'add', '-A')
        self.git(self.cwd, 'commit', '-qm', 'chore: fixture')
        (self.cwd / '.claude').mkdir()
        (self.cwd / '.claude/config.json').write_text('{"vcs":"git"}\n', encoding='utf-8')
        (self.cwd / '새 파일.txt').write_text('새 내용\n', encoding='utf-8')
        (self.cwd / '.dev/state.md').write_text('state: new\n', encoding='utf-8')

    def git(self, cwd, *args):
        return subprocess.run(['git', '-c', f'safe.directory={cwd.as_posix()}', *args],
                              cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True, encoding='utf-8',
                              errors='replace').stdout.strip()

    def invoke(self, cwd=None, env=None):
        return subprocess.run([sys.executable, str(HELPER), '--cwd', str(cwd or self.cwd)],
                              cwd=self.parent, env=env or self.env,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')

    def object_inventory(self):
        objects = Path(self.git(self.cwd, 'rev-parse', '--git-path', 'objects'))
        if not objects.is_absolute():
            objects = self.cwd / objects
        return {p.relative_to(objects).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in objects.rglob('*') if p.is_file()}

    def reference_tree(self):
        reference = self.parent / 'reference'
        reference.mkdir()
        self.git(reference, 'init', '-q')
        shutil.copy2(self.cwd / 'tracked.txt', reference / 'tracked.txt')
        shutil.copy2(self.cwd / '새 파일.txt', reference / '새 파일.txt')
        (reference / '.claude').mkdir()
        shutil.copy2(self.cwd / '.claude/config.json', reference / '.claude/config.json')
        self.git(reference, 'add', '-A')
        return self.git(reference, 'write-tree')[:12]

    def test_matches_worktree_without_mutating_real_index_or_objects(self):
        expected_tree = self.reference_tree()
        expected_head = self.git(self.cwd, 'rev-parse', '--short', 'HEAD')
        index = self.cwd / '.git/index'
        index_before = hashlib.sha256(index.read_bytes()).hexdigest()
        objects_before = self.object_inventory()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f'{expected_head}:{expected_tree}\n')
        self.assertEqual(hashlib.sha256(index.read_bytes()).hexdigest(), index_before)
        self.assertEqual(self.object_inventory(), objects_before)

    def test_dev_and_staging_do_not_change_fingerprint_but_code_does(self):
        first = self.invoke()
        self.assertEqual(first.returncode, 0, first.stderr)
        (self.cwd / '.dev/state.md').write_text('state: third\n', encoding='utf-8')
        self.assertEqual(self.invoke().stdout, first.stdout)
        self.git(self.cwd, 'add', '.claude/config.json')
        self.assertEqual(self.invoke().stdout, first.stdout)
        (self.cwd / '.claude/config.json').write_text('{"vcs":"svn"}\n', encoding='utf-8')
        changed = self.invoke()
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertNotEqual(changed.stdout, first.stdout)

    def test_inherited_alternate_objects_are_preserved(self):
        alternate = self.parent / 'other objects 한글'
        alternate.mkdir()
        env = self.env.copy()
        env['GIT_ALTERNATE_OBJECT_DIRECTORIES'] = str(alternate)
        result = self.invoke(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r'^[0-9a-f]+:[0-9a-f]{12}\n$')

    def test_invalid_repository_never_emits_a_fingerprint(self):
        empty = self.parent / 'not a repository'
        empty.mkdir()
        result = self.invoke(cwd=empty)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(re.search(r'[0-9a-f]+:[0-9a-f]{12}', result.stdout))
        self.assertIn('not a git repository', result.stderr.lower())
