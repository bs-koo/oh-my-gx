"""커밋 인덱스·Git 대상·리뷰 입력의 실제 Git 경계 회귀."""
import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
INDEX = REPO / 'scripts/gx-commit-index.py'
DIFF = REPO / 'scripts/gx-review-diff.py'
GUARD = REPO / '.claude/hooks/pre-tool-guard.sh'
BASH = shutil.which('bash')
if os.name == 'nt' and Path('C:/Program Files/Git/bin/bash.exe').is_file():
    BASH = 'C:/Program Files/Git/bin/bash.exe'


@unittest.skipUnless(shutil.which('git'), 'Git 필요')
class DeliveryFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='gx 배송 경계 ')
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.env = os.environ.copy()
        self.env['GIT_CONFIG_GLOBAL'] = str(self.parent / 'global.config')
        (self.parent / 'global.config').write_text('', encoding='utf-8')
        self.root = self.repository('작업 저장소', 'feat/a')

    def git(self, root, *args, check=True):
        return subprocess.run(['git', '-c', f'safe.directory={root.as_posix()}',
                               '-c', 'commit.gpgsign=false', *args], cwd=root,
                              capture_output=True, check=check, encoding='utf-8', env=self.env)

    def repository(self, name, branch):
        root = self.parent / name
        root.mkdir()
        self.git(root, 'init', '-q', '-b', branch)
        hooks = root / '.git/empty-hooks'
        hooks.mkdir()
        self.git(root, 'config', 'core.hooksPath', str(hooks))
        self.git(root, 'config', 'user.name', 'GX fixture')
        self.git(root, 'config', 'user.email', 'gx@example.invalid')
        self.write(root, 'app.txt', 'first\nsecond\n')
        self.git(root, 'add', '-A')
        self.git(root, 'commit', '-qm', 'fixture')
        return root

    def write(self, root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def helper(self, script, payload, success=True):
        proc = subprocess.run([sys.executable, str(script)], input=json.dumps(payload),
                              cwd=self.root, capture_output=True, encoding='utf-8', env=self.env)
        if success:
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)
        self.assertNotEqual(proc.returncode, 0)
        return proc

    def index(self, action, **kw):
        return self.helper(INDEX, {'action': action, 'cwd': str(self.root), **kw})

    def snapshot(self):
        return self.index('snapshot')['snapshot']


class CommitIndexTests(DeliveryFixture):
    def test_preview_accepts_bom_json_without_rewriting_config_or_index(self):
        config = self.root / '.claude/config.json'
        config.parent.mkdir()
        config.write_bytes(json.dumps({'sensitiveFilePatterns': ['.env']}).encode('utf-8-sig'))
        self.write(self.root, '.env', 'BOM_SECRET_NOT_FOR_OUTPUT\n')
        self.git(self.root, 'add', '.env')
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.index('preview')
        rows = {row['path']: row for row in result['files']}
        self.assertFalse(rows['.env']['included'])
        self.assertTrue(rows['.env']['alreadyStaged'])
        self.assertEqual({str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)

    def test_external_index_change_during_stage_is_preserved_and_not_adopted(self):
        spec = importlib.util.spec_from_file_location('gx_commit_index_concurrency', INDEX)
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, 'dont_write_bytecode', True):
            spec.loader.exec_module(module)
        snap = self.snapshot()
        actual = self.root / '.git/index'
        initial = actual.read_bytes()
        self.write(self.root, 'app.txt', 'implementation\n')
        self.write(self.root, 'external.txt', 'other writer\n')
        # 실패한 staging은 실제 index를 전혀 바꾸지 않고 임시 index를 정리한다.
        self.helper(INDEX, {'action': 'stage', 'cwd': str(self.root), 'snapshot': snap,
                            'paths': ['app.txt', 'does-not-exist.txt'], 'excludes': []}, False)
        self.assertEqual(actual.read_bytes(), initial)
        original_git = module.git
        injected = []

        def interleave(root, *args, **kwargs):
            result = original_git(root, *args, **kwargs)
            if not injected and 'add' in args:
                # helper의 add 직후 다른 작성자가 실제 index에 추가한다.
                self.git(self.root, 'add', 'external.txt')
                injected.append(actual.read_bytes())
            return result

        error = None
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(module, 'git', side_effect=interleave):
            try:
                module.run({'action': 'stage', 'cwd': str(self.root), 'snapshot': snap,
                            'paths': ['app.txt'], 'excludes': []})
            except ValueError as exc:
                error = exc
        self.assertTrue(injected, '실제 Git 동시 추가가 주입돼야 합니다')
        self.assertIsNotNone(error, '외부 index 변경을 helper의 성공 상태로 채택하면 안 됩니다')
        self.assertEqual(actual.read_bytes(), injected[0])
        self.assertEqual(self.git(self.root, 'diff', '--cached', '--name-only').stdout.strip(), 'external.txt')
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap}, False)
        self.assertEqual(actual.read_bytes(), injected[0])
        self.assertEqual(list(Path(snap).glob('stage-*')), [])

    def test_preview_uses_requested_repository_without_any_file_or_index_writes(self):
        target = self.repository('미리보기 대상', 'main')
        self.write(target, '.claude/config.json', json.dumps({'sensitiveFilePatterns': ['.env']}))
        self.write(target, '.env', 'NEVER_PRINT_THIS_SECRET\n')
        self.write(target, 'app.txt', 'preview change\n')
        self.git(target, 'add', '.env')
        before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        global_before = self.git(self.root, 'config', '--global', '--list', check=False)
        result = self.helper(INDEX, {'action': 'preview', 'cwd': str(target)})
        self.assertEqual(result['root'], str(target.resolve()))
        self.assertEqual(result['branch'], 'main')
        self.assertFalse(result['commitAllowed'])
        rows = {r['path']: r for r in result['files']}
        self.assertFalse(rows['.env']['included'])
        self.assertTrue(rows['.env']['alreadyStaged'])
        self.assertTrue(rows['.env']['reasons'])
        self.assertTrue(rows['app.txt']['included'])
        self.assertNotIn('NEVER_PRINT_THIS_SECRET', json.dumps(result))
        self.assertEqual({str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}, before)
        global_after = self.git(self.root, 'config', '--global', '--list', check=False)
        self.assertEqual((global_after.returncode, global_after.stdout, global_after.stderr),
                         (global_before.returncode, global_before.stdout, global_before.stderr))

    def test_explicit_exclusion_removes_already_staged_secret_and_asserts_before_commit(self):
        self.write(self.root, '.env', 'TOKEN=secret\n')
        self.git(self.root, 'add', '.env')
        snap = self.snapshot()
        self.write(self.root, 'app.txt', 'implementation\n')
        self.index('stage', snapshot=snap, paths=['app.txt'], excludes=['.env'])
        self.assertEqual(self.git(self.root, 'diff', '--cached', '--name-only').stdout.strip(), 'app.txt')
        self.assertTrue((self.root / '.env').is_file())
        self.index('assert-excluded', snapshot=snap)
        self.git(self.root, 'add', '.env')
        result = self.helper(INDEX, {'action': 'assert-excluded', 'cwd': str(self.root), 'snapshot': snap}, False)
        self.assertIn('index', result.stderr.lower())

    def test_failed_commit_restores_partial_staging_deleted_entry_and_worktree(self):
        self.write(self.root, 'app.txt', 'staged\nsecond\n')
        self.git(self.root, 'add', 'app.txt')
        self.write(self.root, 'app.txt', 'staged\nUNSTAGED\n')
        self.write(self.root, 'keep.txt', 'tracked\n')
        self.git(self.root, 'add', 'keep.txt')
        self.git(self.root, 'commit', '-qm', 'keep')
        self.write(self.root, 'app.txt', 'STAGED\nUNSTAGED\n')
        self.git(self.root, 'add', 'app.txt')
        self.write(self.root, 'app.txt', 'STAGED\nsecond-unstaged\n')
        self.git(self.root, 'rm', '--cached', 'keep.txt')
        self.write(self.root, 'loose.txt', 'untracked\n')
        original = self.git(self.root, 'diff', '--cached', '--binary').stdout
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        snap = self.snapshot()
        self.index('stage', snapshot=snap, paths=None, excludes=[])
        failed = self.git(self.root, 'commit', '-m', '', check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.index('restore', snapshot=snap)
        self.assertEqual(self.git(self.root, 'diff', '--cached', '--binary').stdout, original)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}, before)

    def test_unborn_missing_index_is_removed_on_restore(self):
        self.root = self.parent / '새 저장소'
        self.root.mkdir()
        self.git(self.root, 'init', '-q', '-b', 'feat/new')
        snap = self.snapshot()
        self.write(self.root, 'new.txt', 'new\n')
        self.index('stage', snapshot=snap, paths=None, excludes=[])
        self.index('restore', snapshot=snap)
        self.assertFalse((self.root / '.git/index').exists())
        self.assertTrue((self.root / 'new.txt').is_file())

    def test_changed_head_or_external_index_prevents_destructive_restore(self):
        snap = self.snapshot()
        self.write(self.root, 'app.txt', 'changed\n')
        self.index('stage', snapshot=snap, paths=None, excludes=[])
        self.git(self.root, 'commit', '-qm', 'advance')
        before = (self.root / '.git/index').read_bytes()
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap}, False)
        self.assertEqual((self.root / '.git/index').read_bytes(), before)
        self.assertTrue(Path(snap).exists())

    def test_external_staging_lock_and_damaged_backup_do_not_overwrite_index(self):
        snap = self.snapshot()
        self.write(self.root, 'external.txt', 'external\n')
        self.git(self.root, 'add', 'external.txt')
        before = (self.root / '.git/index').read_bytes()
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap}, False)
        self.assertEqual((self.root / '.git/index').read_bytes(), before)
        self.git(self.root, 'reset', '-q')
        # 새 snapshot은 변경된 상태를 보존하며 기존 snapshot을 덮지 않는다.
        snap2 = self.snapshot()
        self.assertNotEqual(snap, snap2)
        backup = Path(snap2) / 'original.index'
        backup.write_bytes(b'broken')
        before = (self.root / '.git/index').read_bytes()
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap2}, False)
        self.assertEqual((self.root / '.git/index').read_bytes(), before)
        (self.root / '.git/index.lock').write_bytes(b'other owner')
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap2}, False)
        self.assertEqual((self.root / '.git/index.lock').read_bytes(), b'other owner')

    def test_external_persistent_index_flags_are_not_treated_as_stat_refresh(self):
        snap = self.snapshot()
        self.git(self.root, 'update-index', '--assume-unchanged', 'app.txt')
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap}, False)
        self.git(self.root, 'update-index', '--no-assume-unchanged', 'app.txt')
        snap = self.snapshot()
        self.git(self.root, 'update-index', '--skip-worktree', 'app.txt')
        self.helper(INDEX, {'action': 'restore', 'cwd': str(self.root), 'snapshot': snap}, False)

    def test_lock_and_split_index_are_rejected_before_snapshot(self):
        (self.root / '.git/index.lock').write_bytes(b'owner')
        self.helper(INDEX, {'action': 'snapshot', 'cwd': str(self.root)}, False)
        (self.root / '.git/index.lock').unlink()
        self.git(self.root, 'update-index', '--split-index')
        before = (self.root / '.git/index').read_bytes()
        self.helper(INDEX, {'action': 'snapshot', 'cwd': str(self.root)}, False)
        self.assertEqual((self.root / '.git/index').read_bytes(), before)

    def test_worktree_snapshot_uses_its_actual_index(self):
        linked = self.parent / '연결 worktree'
        self.git(self.root, 'worktree', 'add', '-qb', 'feat/linked', str(linked))
        original_root = self.root
        self.root = linked
        result = self.index('snapshot')
        self.assertIn('worktrees', Path(result['index']).parts)
        self.assertNotEqual(Path(result['index']), original_root / '.git/index')
        self.index('restore', snapshot=result['snapshot'])


@unittest.skipUnless(BASH, 'Bash 필요')
class CommitTargetTests(DeliveryFixture):
    def guard(self, command):
        payload = {'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
        proc = subprocess.run([BASH, str(GUARD)], input=json.dumps(payload), cwd=self.root,
                              capture_output=True, encoding='utf-8', env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)['hookSpecificOutput']['permissionDecision'] if proc.stdout.strip() else 'PASS'

    def test_other_repository_protected_branch_is_denied(self):
        target = self.repository('다른 main repo', 'main')
        self.assertEqual(self.guard(f'git -C "{target.as_posix()}" commit -m probe'), 'deny')

    def test_newline_commit_target_is_checked_but_quoted_message_newline_is_preserved(self):
        target = self.repository('다음 줄 main', 'main')
        self.assertEqual(self.guard(f'git commit -m a\ngit -C "{target.as_posix()}" commit -m b'), 'deny')
        self.assertEqual(self.guard('git commit -m "quoted\nmessage"'), 'PASS')

    def test_svn_deny_has_priority_over_deferred_git_verify_warning(self):
        self.write(self.root, '.dev/feat-a/state.md', 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n')
        self.assertEqual(self.guard('git commit -m a && svn ci'), 'deny')

    def test_current_main_does_not_block_other_feature_repository(self):
        target = self.repository('다른 feature repo', 'feat/b')
        self.git(self.root, 'switch', '-q', '-c', 'main')
        self.assertEqual(self.guard(f'git -C "{target.as_posix()}" commit -m probe'), 'PASS')

    def test_repeated_quoted_c_uses_target_verify_state(self):
        target = self.repository('검증 대상 repo', 'feat/b')
        self.write(target, '.dev/feat-b/state.md', 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n')
        command = f"git -C '{self.parent.as_posix()}' -C '{target.name}' commit -m probe"
        self.assertEqual(self.guard(command), 'ask')

    def test_ambiguous_target_is_denied_and_all_chained_targets_are_checked(self):
        self.assertEqual(self.guard('git -C "$UNKNOWN_TARGET" commit -m probe'), 'deny')
        target = self.repository('후속 main', 'main')
        self.assertEqual(self.guard(f'git commit -m a && git -C "{target.as_posix()}" commit -m b'), 'deny')

    def test_later_protected_target_has_priority_over_earlier_verify_warning(self):
        target = self.repository('후속 보호 repo', 'main')
        self.write(self.root, '.dev/feat-a/state.md', 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n')
        self.assertEqual(self.guard(f'git commit -m a && git -C "{target.as_posix()}" commit -m b'), 'deny')

    def test_unsupported_git_directory_override_is_denied(self):
        target = self.repository('별도 gitdir main', 'main')
        self.assertEqual(self.guard(f'git --git-dir="{(target / ".git").as_posix()}" commit -m probe'), 'deny')
        self.assertEqual(self.guard('git --no-pager log --grep commit'), 'PASS')


class ReviewDiffTests(DeliveryFixture):
    def collect(self, scope='diff'):
        return self.helper(DIFF, {'cwd': str(self.root), 'base': 'HEAD', 'scope': scope})

    def test_stat_preserves_untracked_names_and_counts_without_touching_index(self):
        self.write(self.root, '새 파일.txt', 'new\ncode\n')
        self.write(self.root, '.dev/feat-a/diff.txt', 'generated\n')
        before = (self.root / '.git/index').read_bytes()
        result = self.collect('stat')
        self.assertIn('새 파일.txt', result['files'])
        self.assertIn('새 파일.txt', result['text'])
        self.assertIn('2', result['text'])
        self.assertFalse(any(p.startswith('.dev/') for p in result['files']))
        self.assertEqual((self.root / '.git/index').read_bytes(), before)

    def test_large_untracked_diff_switches_to_stat_without_losing_file(self):
        self.write(self.root, 'large.txt', 'new\n' * 510)
        result = self.collect()
        self.assertEqual(result['scope'], 'stat')
        self.assertIn('large.txt', result['files'])
        self.assertIn('510', result['text'])

    def test_small_untracked_diff_and_staged_changes_are_both_present(self):
        self.write(self.root, 'app.txt', 'tracked change\n')
        self.git(self.root, 'add', 'app.txt')
        self.write(self.root, 'new.txt', 'untracked change\n')
        result = self.collect()
        self.assertEqual(result['scope'], 'diff')
        self.assertEqual(result['files'], ['app.txt', 'new.txt'])
        self.assertIn('+tracked change', result['text'])
        self.assertIn('+untracked change', result['text'])


if __name__ == '__main__':
    unittest.main()
