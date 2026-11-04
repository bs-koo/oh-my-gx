"""Behavior checks for affected selection and same-run verification evidence."""
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/gx-test-plan.py'


class TaskFocusedCommandTests(unittest.TestCase):
    """Inner-loop selection uses file fixtures only, without Git or test execution."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gx focused ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = {'detect': ['package.json'], 'test': 'npm test'}
        self.config = self.root / '.claude/config.json'
        self.config.parent.mkdir()
        (self.root / 'web/tests').mkdir(parents=True)
        self.test = "tests/login's case.test.js"
        (self.root / 'web' / self.test).write_text('test fixture', encoding='utf-8')
        self.paths = self.root / 'tests.json'
        self.paths.write_text(json.dumps(['web/' + self.test]), encoding='utf-8')

    def invoke(self, script='vitest', project='node:web', config_path=None):
        (self.root / 'web/package.json').write_text(json.dumps({'scripts': {'test': script}}), encoding='utf-8')
        self.config.write_text(json.dumps({'projectTypes': {'node': self.settings}}), encoding='utf-8')
        command = [sys.executable, str(HELPER), 'focused', '--cwd', str(self.root),
                   '--project', project, '--tests-file', str(self.paths)]
        if config_path:
            command += ['--config', str(config_path)]
        return subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')

    def test_explicit_template_wins_and_preserves_shell_quoted_current_files(self):
        import shlex
        self.settings['focusedTest'] = 'custom-test {files}'
        result = self.invoke('arbitrary wrapper')
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(shlex.split(value['command']), ['custom-test', self.test])
        self.assertEqual((value['cwd'], value['scope']), ('web', [self.test]))

    def test_exact_known_node_scripts_choose_file_execution_without_all_suite_fallback(self):
        import shlex
        for script, flags in [('vitest', ['--run']), ('vitest run', []),
                              ('jest', ['--runInBand', '--runTestsByPath']), ('node --test', [])]:
            with self.subTest(script=script):
                result = self.invoke(script)
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertEqual(shlex.split(value['command']), ['npm', 'test', '--', *flags, self.test])
                self.assertTrue(value['supported'])
                self.assertEqual(value['scope'], [self.test])

    def test_custom_runner_reports_explicit_configuration_instead_of_running_everything(self):
        for script in ('vitest --watch', 'custom-test', 'jest && echo done'):
            with self.subTest(script=script):
                result = self.invoke(script)
                self.assertEqual(result.returncode, 2, result.stderr)
                value = json.loads(result.stdout)
                self.assertFalse(value['supported'])
                self.assertEqual(value['requires'], 'focusedTest')
                self.assertNotIn('command', value)

    def test_invalid_project_empty_missing_or_cross_project_paths_are_blocked(self):
        for paths in ([], ['web/tests/missing.test.js'], ['../outside.test.js'],
                      ['/outside.test.js'], ['C:/outside.test.js'], ['other/test.test.js']):
            with self.subTest(paths=paths):
                self.paths.write_text(json.dumps(paths), encoding='utf-8')
                result = self.invoke()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.paths.write_text(json.dumps(['web/' + self.test]), encoding='utf-8')
        self.assertEqual(self.invoke(project='node:missing').returncode, 1)

    def test_exact_pytest_command_and_config_override_need_no_git_repository(self):
        import shlex
        (self.root / 'web/pytest.ini').write_text('[pytest]', encoding='utf-8')
        python_test = self.root / 'web/tests/test_limit.py'
        python_test.write_text('def test_limit(): pass', encoding='utf-8')
        self.paths.write_text('["web/tests/test_limit.py"]', encoding='utf-8')
        override = self.root / 'override.json'
        for base in ('pytest', 'python -m pytest', 'python3 -m pytest'):
            with self.subTest(base=base):
                override.write_text(json.dumps({'projectTypes': {'python': {
                    'detect': ['pytest.ini'], 'test': base}}}), encoding='utf-8')
                result = self.invoke(project='python:web', config_path=override)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(shlex.split(json.loads(result.stdout)['command']),
                                 [*shlex.split(base), 'tests/test_limit.py'])
        self.assertFalse((self.root / '.git').exists())

    def test_explicit_gradle_template_keeps_kotlin_task_scope(self):
        import shlex
        self.settings['focusedTest'] = './gradlew test --tests {pattern}'
        (self.root / 'web/tests/LimitTest.kt').write_text('class LimitTest', encoding='utf-8')
        self.paths.write_text('["web/tests/LimitTest.kt"]', encoding='utf-8')
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(shlex.split(json.loads(result.stdout)['command']),
                         ['./gradlew', 'test', '--tests', 'LimitTest'])


class TestExecutionContractTests(unittest.TestCase):
    def test_review_and_verify_share_selection_and_exact_evidence_contract(self):
        verify = (ROOT / '.claude/skills/gx-verify/SKILL.md').read_text(encoding='utf-8')
        review = (ROOT / '.claude/skills/gx-tdd/phases/phase-review.md').read_text(encoding='utf-8')
        self.assertIn('test-execution.md', verify)
        self.assertIn('test-execution.md', review)
        self.assertNotIn('캐시된 결과 사용 금지. **반드시 새로 실행**.', verify)
        reference = ROOT / '.claude/skills/gx-tdd/references/test-execution.md'
        self.assertTrue(reference.is_file())
        text = reference.read_text(encoding='utf-8')
        for token in ('--ownership-file', '--run-id', 'configHash', '0건', 'buildOnly', '전체 폴백'):
            self.assertIn(token, text)


class SelectionEdgeTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('test_plan', HELPER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def select(self, settings, changed):
        project = {'cwd': '.', 'settings': settings}
        return self.module.select_tests(self.root, project, changed, [], None, [])

    def test_empty_mapping_cannot_silently_skip_changed_code(self):
        command, scope, _ = self.select({'test': 'run-all', 'testSelection': {
            'mappings': [{'sources': ['src/A.java'], 'tests': []}]}}, ['src/A.java'])
        self.assertEqual((command, scope), ('run-all', ['*']))

    def test_unknown_java_template_falls_back_instead_of_leaving_placeholder(self):
        (self.root / 'ATest.java').write_text('class ATest {}', encoding='utf-8')
        command, scope, _ = self.select({'test': 'run-all',
            'focusedTest': 'custom --include={pattern}'}, ['ATest.java'])
        self.assertEqual((command, scope), ('run-all', ['*']))

    def test_builtin_related_runner_keeps_explicit_test_coverage(self):
        (self.root / 'package.json').write_text('{"scripts":{"test":"vitest"}}', encoding='utf-8')
        (self.root / 'A.test.js').write_text('test("A", () => {});', encoding='utf-8')
        command, scope, _ = self.select({'test': 'npm test'}, ['src/A.js', 'A.test.js'])
        self.assertEqual((command, scope), ('npm test', ['*']))

    def test_kotlin_mapping_uses_gradle_focused_selection(self):
        (self.root / 'LimitTest.kt').write_text('class LimitTest', encoding='utf-8')
        command, scope, _ = self.select({'test': './gradlew test',
            'focusedTest': './gradlew test --tests {pattern}',
            'testSelection': {'mappings': [
                {'sources': ['src/Limit.kt'], 'tests': ['LimitTest.kt']}]}
            }, ['src/Limit.kt'])
        self.assertEqual(scope, ['LimitTest.kt'])
        self.assertIn('--tests LimitTest', command)

    def test_commit_with_identical_tree_preserves_execution_identity(self):
        config = self.root / 'config.json'
        config.write_text('{}', encoding='utf-8')
        entry = {'id': 'test-1', 'project': 'node:.', 'type': 'node', 'cwd': '.',
                 'kind': 'test', 'command': 'node --test a.test.js', 'scope': ['a.test.js']}
        value = {'root': str(self.root), 'fingerprint': '1234567:abcdef123456',
                 'configPath': str(config), 'configHash': self.module.digest({}),
                 'runId': 'run-1', 'entries': [entry]}
        with mock.patch.object(self.module, 'fingerprint', return_value='7654321:abcdef123456'):
            identity, _ = self.module.identity(self.root, value, 'test-1')
        self.assertEqual(identity['fingerprint'], 'abcdef123456')

    def test_changed_tree_invalidates_execution_identity(self):
        with mock.patch.object(self.module, 'fingerprint', return_value='1234567:000000000000'):
            with self.assertRaises(ValueError):
                self.module.identity(self.root, {'root': str(self.root),
                    'fingerprint': '1234567:abcdef123456'}, 'test-1')

    def test_explicit_independent_unaffected_project_is_not_executed(self):
        command, scope, reason = self.select({'test': 'run-all',
            'testSelection': {'independent': True}}, [])
        self.assertIsNone(command)
        self.assertEqual(scope, [])
        self.assertIn('independent', reason)

    def test_crosscutting_change_still_checks_independent_project(self):
        project = {'cwd': '.', 'settings': {'test': 'run-all',
                   'testSelection': {'independent': True}}}
        command, scope, _ = self.module.select_tests(self.root, project, [], [],
            'shared dependency changed', [])
        self.assertEqual((command, scope), ('run-all', ['*']))

    def test_typescript_configuration_forces_full_before_related_selection(self):
        command, scope, _ = self.select({'test': 'run-all',
            'affectedTest': 'related {files}'}, ['tsconfig.json', 'src/a.ts'])
        self.assertEqual((command, scope), ('run-all', ['*']))

    def test_changed_file_hint_cannot_hide_real_repository_changes(self):
        self.root.joinpath('package.json').write_text('{}', encoding='utf-8')
        self.root.joinpath('a.test.js').write_text('test a', encoding='utf-8')
        self.root.joinpath('b.test.js').write_text('test b', encoding='utf-8')
        config = self.root / 'settings.json'
        config.write_text(json.dumps({'projectTypes': {'node': {
            'detect': ['package.json'], 'test': 'run-all', 'focusedTest': 'run {files}',
            'testSelection': {'mappings': [
                {'sources': ['src/a.js'], 'tests': ['a.test.js']},
                {'sources': ['src/b.js'], 'tests': ['b.test.js']}]}}}}), encoding='utf-8')
        changes = self.root / 'changes.json'
        changes.write_text('["src/a.js"]', encoding='utf-8')
        args = type('Args', (), {'cwd': self.root, 'config': config, 'base': 'HEAD',
            'run_id': 'run-1', 'changed_file': changes, 'tests_file': None,
            'ownership_file': None, 'full': False, 'rerun_tests': False})()
        with mock.patch.object(self.module, 'changed_paths', return_value=['src/b.js']), \
             mock.patch.object(self.module, 'fingerprint', return_value='123:abcdef123456'):
            plan = self.module.plan(args)
        entry = next(item for item in plan['entries'] if item['kind'] == 'test')
        self.assertEqual(entry['scope'], ['a.test.js', 'b.test.js'])


class TestPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gx tests 한글 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.git('init', '-q', '-b', 'feat/test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.config = {'projectTypes': {'node': {
            'detect': ['package.json'], 'test': 'npm test', 'buildOnly': 'npm run build',
            'focusedTest': 'npm test -- {files}',
            'testSelection': {'mappings': [
                {'sources': ['src/login.js'], 'tests': ['tests/login.test.js']}]}}}}
        self.write('.claude/config.json', json.dumps(self.config))
        self.write('web/package.json', '{"scripts":{"test":"node --test"}}')
        self.write('web/src/login.js', 'export const login = true;')
        self.write('web/tests/login.test.js', 'test("login", () => {});')
        self.git('add', '-A')
        self.git('commit', '-qm', 'fixture')

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
        return path

    def git(self, *args):
        return subprocess.run(['git', '-c', f'safe.directory={self.root.as_posix()}', *args],
                              cwd=self.root, env=self.env, check=True, capture_output=True).stdout

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(HELPER), *args, '--cwd', str(self.root)],
                              env=self.env, capture_output=True, text=True, encoding='utf-8', errors='replace')

    def plan(self, changed, run='run-1'):
        paths = self.write('.dev/changed.json', json.dumps(changed))
        result = self.invoke('plan', '--base', 'HEAD', '--run-id', run, '--changed-file', str(paths))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def entries_for_tests(self, plan):
        return [entry for entry in plan['entries'] if entry['kind'] == 'test']

    def test_mapped_change_selects_related_tests(self):
        tests = self.entries_for_tests(self.plan(['web/src/login.js']))
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0]['scope'], ['tests/login.test.js'])
        self.assertEqual(tests[0]['cwd'], 'web')
        self.assertNotEqual(tests[0]['command'], 'npm test')

    def test_unmapped_change_falls_back_without_ignoring_another_project(self):
        self.write('api/package.json', '{}')
        tests = self.entries_for_tests(self.plan(['web/src/login.js', 'api/src/unknown.js']))
        self.assertEqual({entry['cwd'] for entry in tests}, {'web', 'api'})
        self.assertEqual(next(e for e in tests if e['cwd'] == 'api')['scope'], ['*'])

    def test_root_dependency_change_runs_every_project(self):
        self.write('api/package.json', '{}')
        tests = self.entries_for_tests(self.plan(['package-lock.json']))
        self.assertEqual(len(tests), 2)
        self.assertTrue(all(e['scope'] == ['*'] for e in tests))

    def test_explicit_full_request_overrides_mapped_selection(self):
        changed = self.write('.dev/changed.json', '["web/src/login.js"]')
        result = self.invoke('plan', '--base', 'HEAD', '--run-id', 'run-1',
                             '--changed-file', str(changed), '--full')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.entries_for_tests(json.loads(result.stdout))[0]['scope'], ['*'])

    def test_crosscutting_change_falls_back(self):
        self.config['projectTypes']['node']['testSelection']['crosscutting'] = ['src/shared/**']
        self.write('.claude/config.json', json.dumps(self.config))
        self.assertEqual(self.entries_for_tests(self.plan(['web/src/shared/auth.js']))[0]['scope'], ['*'])

    def test_approved_task_ownership_selects_focused_without_persistent_config_change(self):
        changed = self.write('.dev/changed.json', '["web/src/profile.js"]')
        owners = self.write('.dev/ownership.json', json.dumps([
            {'sources': ['web/src/profile.js'], 'tests': ['web/tests/login.test.js']}]))
        result = self.invoke('plan', '--base', 'HEAD', '--run-id', 'run-1',
                             '--changed-file', str(changed), '--ownership-file', str(owners))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.entries_for_tests(json.loads(result.stdout))[0]['scope'], ['tests/login.test.js'])

    def test_known_vitest_runner_uses_related_selection(self):
        self.write('web/package.json', '{"scripts":{"test":"vitest"}}')
        # The runner is part of the baseline; changing package.json itself requires full coverage.
        self.git('add', 'web/package.json')
        self.git('commit', '-qm', 'configure fixture runner')
        entry = self.entries_for_tests(self.plan(['web/src/unmapped.js']))[0]
        self.assertIn('related --run', entry['command'])
        self.assertEqual(entry['scope'], ['src/unmapped.js'])

    def test_deleted_mapped_test_forces_full_fallback(self):
        (self.root / 'web/tests/login.test.js').unlink()
        self.assertEqual(self.entries_for_tests(self.plan(['web/src/login.js']))[0]['scope'], ['*'])

    def test_gradle_build_is_explicitly_test_free(self):
        self.config['projectTypes']['java'] = {'detect': ['build.gradle'],
                                               'test': './gradlew test', 'build': './gradlew build'}
        self.write('.claude/config.json', json.dumps(self.config))
        self.write('api/build.gradle', '')
        builds = [e for e in self.plan(['api/src/A.java'])['entries'] if e['kind'] == 'build']
        self.assertIn('./gradlew build -x test testClasses', [e['command'] for e in builds])

    def test_gradle_cache_refresh_is_part_of_planned_test_command(self):
        self.config['projectTypes']['java'] = {'detect': ['build.gradle'],
                                               'test': './gradlew test', 'build': './gradlew build'}
        self.write('.claude/config.json', json.dumps(self.config))
        self.write('api/build.gradle', '')
        changed = self.write('.dev/changed.json', '["api/src/A.java"]')
        result = self.invoke('plan', '--base', 'HEAD', '--run-id', 'run-1',
                             '--changed-file', str(changed), '--rerun-tests')
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = self.entries_for_tests(json.loads(result.stdout))
        self.assertEqual(next(e for e in entries if e['cwd'] == 'api')['command'],
                         './gradlew test --rerun-tasks')
        self.assertEqual(next(e for e in entries if e['cwd'] == 'web')['command'], 'npm test')

    def proof(self, plan, exit_code=0, tests=3, failures=0):
        path = self.write('.dev/plan.json', json.dumps(plan))
        log = self.write('.dev/test.log', '3 passed\n')
        proof = self.root / '.dev/proof.json'
        entry = self.entries_for_tests(plan)[0]
        result = self.invoke('record', '--plan', str(path), '--entry', entry['id'],
                             '--proof', str(proof), '--log', str(log), '--exit-code', str(exit_code),
                             '--tests', str(tests), '--failures', str(failures))
        return path, proof, entry, result

    def reuse(self, path, proof, entry):
        return self.invoke('reuse', '--plan', str(path), '--entry', entry['id'], '--proof', str(proof))

    def test_successful_same_run_evidence_reuses_and_code_changes_invalidate(self):
        path, proof, entry, recorded = self.proof(self.plan(['web/src/login.js']))
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        self.assertEqual(self.reuse(path, proof, entry).returncode, 0)
        self.write('web/src/login.js', 'changed')
        self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)

    def test_run_command_scope_config_and_log_changes_invalidate(self):
        plan = self.plan(['web/src/login.js'])
        path, proof, entry, _ = self.proof(plan)
        for field, value in [('runId', 'other'), ('configHash', 'other')]:
            with self.subTest(field=field):
                changed = dict(plan, **{field: value})
                path.write_text(json.dumps(changed), encoding='utf-8')
                self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)
        path.write_text(json.dumps(plan), encoding='utf-8')
        for field, value in [('command', 'npm test -- other'), ('scope', ['other'])]:
            with self.subTest(field=field):
                changed = json.loads(json.dumps(plan))
                next(e for e in changed['entries'] if e['id'] == entry['id'])[field] = value
                path.write_text(json.dumps(changed), encoding='utf-8')
                self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)
        path.write_text(json.dumps(plan), encoding='utf-8')
        self.write('.dev/test.log', 'modified')
        self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)

    def test_failure_zero_tests_and_missing_count_cannot_produce_reusable_proof(self):
        for exit_code, tests, failures in [(1, 3, 0), (0, 0, 0), (0, 3, 1), (0, -1, 0)]:
            with self.subTest(exit_code=exit_code, tests=tests, failures=failures):
                path, proof, entry, result = self.proof(self.plan(['web/src/login.js']),
                                                      exit_code, tests, failures)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)

    def test_unowned_change_and_missing_project_detection_fail_closed(self):
        tests = self.entries_for_tests(self.plan(['shared/auth.js']))
        self.assertTrue(all(e['scope'] == ['*'] for e in tests))
        (self.root / 'web/package.json').unlink()
        changed = self.write('.dev/changed.json', '["shared/auth.js"]')
        result = self.invoke('plan', '--base', 'HEAD', '--run-id', 'run-1', '--changed-file', str(changed))
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
