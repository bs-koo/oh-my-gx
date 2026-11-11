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

    def read(self, relative):
        return (ROOT / '.claude/skills' / relative).read_text(encoding='utf-8')

    def section(self, text, start, end):
        return text[text.index(start):text.index(end, text.index(start))]

    def test_plan_failure_known_failures_and_long_runs_have_one_contract(self):
        text = self.read('gx-tdd/references/test-execution.md')
        failure = self.section(text, '## 계획 실패 처리', '## 기존 실패')
        for token in ('한 번', 'config 수정안', '`test-plan-override`', '`command`', '`scope`', '`reason`',
                      '즉흥', '금지', '다시 묻지 않고'):
            self.assertIn(token, failure)
        # M2: the override run leaves reusable proof; Codex receives the command in a second step.
        for token in ('gx-test-plan.py override', '`type: test-plan-override`', '`reuse`', '`record`',
                      'gx-commit', 'codex-questions.md', '후속 질문'):
            self.assertIn(token, failure)
        self.assertNotIn('helper 증거 재사용은 하지 않으며', failure)
        known = self.section(text, '## 기존 실패', '## 긴 실행과 시간 초과')
        for token in ('`known-failures`', '새 실패', '보고만', '기존 실패 해소', '실제 사용자 응답',
                      '`--continue`', '`-fae`'):
            self.assertIn(token, known)
        # H2: known failures are compared with the baseline count recorded at Step 0.5.
        for token in ('record --baseline', '`baseline-tests.json`', '실행 수를 대조할 기준이 없음', 'plan --full'):
            self.assertIn(token, self.section(text, '## 실행과 재사용', '## 계획 실패 처리'))
        self.assertRegex(text, r'`context/` 아래 Markdown 문서\(`\.md`')
        long_run = self.section(text, '## 긴 실행과 시간 초과', '## 빌드와 경고')
        for token in ('`timeouts.build`', '600000', '`durationSeconds`', 'run_in_background', 'write_stdin',
                      '사유', '지난 소요', '다음', '테스트 실패 아님', '백그라운드로 재실행', 'RED로 간다'):
            self.assertIn(token, long_run)
        self.assertIn('--known-failures-file', text)
        self.assertIn('--duration-seconds', text)
        self.assertRegex(text, r'`context/`[^\n]*테스트 선택 입력에서만[^\n]*지문에는 그대로 포함')
        self.assertRegex(text, r'선택 제외 경로[^\n]*같은 focused 범위로 다시 실행')
        adaptation = self.read('gx-tdd/references/harness-adaptation.md')
        row = next(line for line in adaptation.splitlines() if 'run_in_background' in line)
        self.assertIn('write_stdin', row)
        self.assertNotIn('미지원', row)

    def test_verify_blocks_only_new_failures_and_hides_internal_identifiers(self):
        verify = self.read('gx-verify/SKILL.md')
        self.assertNotIn('증거 없이 다음 단계 진입 불가', verify)
        self.assertNotIn('7c9e814:3ca970cc12ab', verify)
        self.assertNotIn('300000', verify)
        judgement = self.section(verify, '판정 (아래 순서로', '### Step 5-A')
        self.assertIn('`known-failures` 밖의 **새** 테스트 실패', judgement)
        self.assertIn('test-plan-override', self.section(verify, '### Step 1:', '### Step 2:'))
        self.assertIn('Read("references/output.md")', verify)
        output = self.read('gx-verify/references/output.md')
        user = self.section(output, '## 사용자 줄', '## 기록용 블록')
        self.assertNotIn('verify-fingerprint', user)
        self.assertIn('기존 실패', user)
        self.assertIn('verify-fingerprint', output.split('## 기록용 블록', 1)[1])

    def test_review_fixes_behavior_defects_by_default_and_repairs_in_session(self):
        review = self.read('gx-tdd/phases/phase-review.md')
        handling = self.section(review, '# 4a:', '# 4b:')
        self.assertNotIn('동작 결함을 RGR 사이클로 수정할까요', handling)
        self.assertIn('Ruling: review 동작 결함 RGR 수정', handling)
        self.assertRegex(handling, r'if [^\n]*범위[^\n]*AC[^\n]*:\n\s+AskUserQuestion')
        gate = self.section(review, '## Step 0: Mechanical Gate', '## Step 1:')
        self.assertRegex(gate, r'`execution-method: session`이면 implementer를 디스패치하지 않고 \*\*세션이 직접\*\*')
        self.assertIn('테스트 파일 무변경', gate)
        self.assertIn('`known-failures`', gate)
        self.assertIn('test-plan-override', gate)

    def test_composite_hint_example_runs_once_from_repository_root(self):
        hints = self.read('gx-setup/references/project-type-hints.md')
        block = hints.split('## 복합 타입', 1)[1].split('```json', 1)[1].split('```', 1)[0]
        types = json.loads('{' + block.strip() + '}')
        spec = importlib.util.spec_from_file_location('test_plan_hint', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ('build.gradle.kts', 'frontend/package.json'):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text('{}', encoding='utf-8')
            self.assertEqual([p['cwd'] for p in module.discover(root, types)], ['.'])


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

    def test_broad_source_mapping_preserves_changed_and_required_tests(self):
        (self.root / 'src').mkdir()
        for path in ('src/feature.test.js', 'src/smoke.test.js', 'required.test.js'):
            (self.root / path).write_text('test fixture', encoding='utf-8')
        settings = {'test': 'npm test', 'focusedTest': 'npm test -- {files}',
                    'testSelection': {'mappings': [
                        {'sources': ['src/**'], 'tests': ['src/smoke.test.js']}]}}
        command, scope, _ = self.module.select_tests(self.root,
            {'cwd': '.', 'settings': settings}, ['src/feature.test.js'],
            ['required.test.js'], None, [])
        self.assertEqual(scope, ['required.test.js', 'src/feature.test.js', 'src/smoke.test.js'])
        import shlex
        self.assertEqual(shlex.split(command), ['npm', 'test', '--',
            'required.test.js', 'src/feature.test.js', 'src/smoke.test.js'])

    def test_option_like_selected_test_remains_a_file_operand(self):
        import shlex
        filename = '--ignore=test_sensitive.py'
        (self.root / filename).write_text('def test_sensitive(): pass', encoding='utf-8')
        command, scope, _ = self.select({'test': 'pytest', 'focusedTest': 'pytest {files}',
            'testSelection': {'tests': ['-*']}}, [filename])
        self.assertEqual(scope, [filename])
        self.assertEqual(shlex.split(command), ['pytest', './--ignore=test_sensitive.py'])

    def test_external_test_symlinks_are_blocked_for_changed_required_and_mapped_tests(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'outside.test.js'
            target.write_text('external test fixture', encoding='utf-8')
            try:
                (self.root / 'linked.test.js').symlink_to(target)
            except OSError as exc:
                self.skipTest(f'symlinks unavailable: {exc}')
            settings = {'test': 'all', 'focusedTest': 'runner {files}'}
            cases = [(['linked.test.js'], [], settings),
                     ([], ['linked.test.js'], settings),
                     (['src/a.js'], [], {**settings, 'testSelection': {'mappings': [
                         {'sources': ['src/a.js'], 'tests': ['linked.test.js']}]}})]
            for changed, required, config in cases:
                with self.subTest(changed=changed, required=required):
                    with self.assertRaisesRegex(ValueError, 'outside selected project'):
                        self.module.select_tests(self.root, {'cwd': '.', 'settings': config},
                                                 changed, required, None, [])

    def test_explicit_project_root_symlink_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external)
            (target / 'package.json').write_text('{}', encoding='utf-8')
            try:
                (self.root / 'linked').symlink_to(target, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f'symlinks unavailable: {exc}')
            with self.assertRaisesRegex(ValueError, 'outside repository'):
                self.module.discover(self.root, {'node': {
                    'roots': ['linked'], 'detect': ['package.json'], 'test': 'npm test'}})

    def test_related_source_symlink_cannot_escape_selected_project(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'source.js'
            target.write_text('external source fixture', encoding='utf-8')
            try:
                (self.root / 'source.js').symlink_to(target)
            except OSError as exc:
                self.skipTest(f'symlinks unavailable: {exc}')
            with self.assertRaisesRegex(ValueError, 'outside selected project'):
                self.select({'test': 'all', 'affectedTest': 'related {files}'}, ['source.js'])

    def test_changed_symlinks_are_checked_before_config_crosscutting_or_ignore(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'external.js'
            target.write_text('external fixture', encoding='utf-8')
            try:
                for path in ('vite.config.js', 'source.js'):
                    (self.root / path).symlink_to(target)
            except OSError as exc:
                self.skipTest(f'symlinks unavailable: {exc}')
            for path, policy in [('vite.config.js', {}),
                                 ('source.js', {'crosscutting': ['source.js']}),
                                 ('source.js', {'ignore': ['source.js']})]:
                with self.subTest(path=path, policy=policy):
                    with self.assertRaisesRegex(ValueError, 'outside selected project'):
                        self.select({'test': 'all', 'testSelection': policy}, [path])

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

    def test_unowned_changed_symlink_cannot_hide_behind_global_fallback(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'workspace.yaml'
            target.write_text('packages: [web]', encoding='utf-8')
            try:
                (self.root / 'pnpm-workspace.yaml').symlink_to(target)
            except OSError as exc:
                self.skipTest(f'symlinks unavailable: {exc}')
            result = self.invoke('plan', '--base', 'HEAD', '--run-id', 'run-1')
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('outside repository', result.stderr)

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

    def test_context_documents_do_not_widen_selection_but_stay_in_fingerprint(self):
        before = self.plan(['web/src/login.js'])
        self.write('context/auth/status.md', '| FR-1 | done |')
        after = self.plan(['web/src/login.js', 'context/auth/status.md'])
        self.assertNotIn('context/auth/status.md', after['changed'])
        self.assertEqual([e['scope'] for e in self.entries_for_tests(after)], [['tests/login.test.js']])
        # Same entry (command and scope) but a new tree: the proof is rerun with the same focused scope.
        self.assertEqual([e['id'] for e in before['entries']], [e['id'] for e in after['entries']])
        self.assertNotEqual(before['fingerprint'].split(':')[1], after['fingerprint'].split(':')[1])

    def record(self, plan, *extra, exit_code=0, tests=3, failures=0):
        path = self.write('.dev/plan.json', json.dumps(plan))
        log = self.write('.dev/test.log', '3 passed\n')
        proof = self.root / '.dev/proof.json'
        entry = self.entries_for_tests(plan)[0]
        result = self.invoke('record', '--plan', str(path), '--entry', entry['id'], '--proof', str(proof),
                             '--log', str(log), '--exit-code', str(exit_code), '--tests', str(tests),
                             '--failures', str(failures), *extra)
        return path, proof, entry, result

    def test_only_baseline_known_failures_can_produce_reusable_proof(self):
        known = self.write('.dev/known.json', '["LoginTest.locked"]')
        listed = self.write('.dev/failed.json', '["LoginTest.locked"]')
        unlisted = self.write('.dev/new.json', '["LoginTest.reset"]')
        plan = self.plan(['web/src/login.js'])
        # The failing baseline is not evidence, but its executed count is kept for later comparison.
        *_, baseline = self.record(plan, '--baseline', exit_code=1, failures=1)
        self.assertNotEqual(baseline.returncode, 0)
        path, proof, entry, result = self.record(plan, '--failed-file', str(listed),
                                                 '--known-failures-file', str(known), exit_code=1, failures=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(proof.read_text(encoding='utf-8'))['knownFailures'], ['LoginTest.locked'])
        reuse = self.invoke('reuse', '--plan', str(path), '--entry', entry['id'], '--proof', str(proof),
                            '--known-failures-file', str(known))
        self.assertEqual(reuse.returncode, 0, reuse.stderr)
        self.assertEqual(json.loads(reuse.stdout)['knownFailures'], ['LoginTest.locked'])
        self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)
        for failed, failures in ((unlisted, 1), (listed, 2), (None, 1)):
            with self.subTest(failed=failed, failures=failures):
                extra = ('--failed-file', str(failed)) if failed else ()
                *_, result = self.record(plan, *extra, '--known-failures-file', str(known),
                                         exit_code=1, failures=failures)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(json.loads(proof.read_text(encoding='utf-8'))['passed'])

    def test_known_failures_need_a_baseline_count_that_this_run_reaches(self):
        """H2: a runner that stops at the first (known) failure must not pass with later tests skipped."""
        known = self.write('.dev/known.json', '["LoginTest.locked"]')
        listed = self.write('.dev/failed.json', '["LoginTest.locked"]')
        plan = self.plan(['web/src/login.js'])
        accept = ('--failed-file', str(listed), '--known-failures-file', str(known))
        _, proof, _, result = self.record(plan, *accept, exit_code=1, failures=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('실행 수를 대조할 기준이 없음', result.stderr)
        self.assertFalse(json.loads(proof.read_text(encoding='utf-8'))['passed'])
        *_, baseline = self.record(plan, '--baseline', exit_code=1, tests=5, failures=1)
        self.assertNotEqual(baseline.returncode, 0)
        counts = json.loads((proof.parent / 'baseline-tests.json').read_text(encoding='utf-8'))
        self.assertEqual(counts, [{'project': 'node:web', 'scope': ['tests/login.test.js'], 'tests': 5}])
        *_, fewer = self.record(plan, *accept, exit_code=1, tests=4, failures=1)
        self.assertNotEqual(fewer.returncode, 0)
        self.assertIn('fewer than the baseline 5', fewer.stderr)
        self.assertFalse(json.loads(proof.read_text(encoding='utf-8'))['passed'])
        *_, reached = self.record(plan, *accept, exit_code=1, tests=5, failures=1)
        self.assertEqual(reached.returncode, 0, reached.stderr)
        # Runs without known failures and build entries never depend on the baseline count.
        *_, clean = self.record(plan, exit_code=0, tests=1)
        self.assertEqual(clean.returncode, 0, clean.stderr)

    def test_full_run_is_compared_with_a_baseline_of_any_scope_in_the_same_project(self):
        entry = {'project': 'node:web', 'scope': ['*']}
        counts = self.write('.dev/evidence/baseline-tests.json', json.dumps([
            {'project': 'node:web', 'scope': ['tests/login.test.js'], 'tests': 3},
            {'project': 'node:api', 'scope': ['*'], 'tests': 90}]))
        spec = importlib.util.spec_from_file_location('test_plan_counts', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.baseline_tests(counts, entry), 3)
        self.assertEqual(module.baseline_tests(counts, {'project': 'node:web',
                         'scope': ['tests/login.test.js', 'tests/new.test.js']}), 3)
        self.assertIsNone(module.baseline_tests(counts, {'project': 'node:web', 'scope': ['tests/new.test.js']}))
        self.assertIsNone(module.baseline_tests(counts, {'project': 'node:other', 'scope': ['*']}))

    def override(self, command='./run-all-tests.sh', *scope):
        result = self.invoke('override', '--run-id', 'run-1', '--command', command,
                             *(('--scope', *scope) if scope else ()))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_override_command_records_reusable_proof_bound_to_run_tree_and_scope(self):
        """M2: a user-chosen test-plan-override leaves proof that commit can reuse, not a rerun or prose."""
        # Detection fails, which is why the user chose an override; the broken config is not its identity.
        self.write('.claude/config.json', '{"projectTypes": ')
        plan = self.override()
        [entry] = plan['entries']
        self.assertEqual((plan['source'], entry['type'], entry['cwd'], entry['scope']),
                         ('test-plan-override', 'test-plan-override', '.', ['*']))
        path, proof, _, recorded = self.record(plan)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        again = self.write('.dev/again.json', json.dumps(self.override()))
        self.assertEqual(self.reuse(again, proof, entry).returncode, 0)
        for changed in (self.override('./other-tests.sh'), self.override('./run-all-tests.sh', 'web/tests/login.test.js')):
            with self.subTest(entry=changed['entries'][0]['command'], scope=changed['entries'][0]['scope']):
                self.assertNotEqual(changed['entries'][0]['id'], entry['id'])
        other_run = dict(plan, runId='run-2')
        path.write_text(json.dumps(other_run), encoding='utf-8')
        self.assertNotEqual(self.reuse(path, proof, entry).returncode, 0)
        self.write('web/src/login.js', 'changed')
        self.assertNotEqual(self.reuse(again, proof, entry).returncode, 0)
        *_, zero = self.record(self.override(), tests=0)
        self.assertNotEqual(zero.returncode, 0)
        self.assertFalse(json.loads(proof.read_text(encoding='utf-8'))['passed'])

    def test_override_scope_is_star_or_repository_relative_tests(self):
        self.assertEqual(self.override('run', 'web/tests/b.test.js', 'web/tests/a.test.js')['entries'][0]['scope'],
                         ['web/tests/a.test.js', 'web/tests/b.test.js'])
        for scope in (('*', 'web/tests/a.test.js'), ('../outside.test.js',)):
            with self.subTest(scope=scope):
                result = self.invoke('override', '--run-id', 'run-1', '--command', 'run', '--scope', *scope)
                self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(self.invoke('override', '--run-id', 'run-1', '--command', ' ').returncode, 0)

    def test_context_code_files_still_select_tests(self):
        """L9: only gx-context Markdown is a selection-free document; code under context/ is a change."""
        plan = self.plan(['web/src/login.js', 'context/auth/status.md', 'context/tools/sync.js'])
        self.assertEqual(plan['changed'], ['context/tools/sync.js', 'web/src/login.js'])
        self.assertEqual([e['scope'] for e in self.entries_for_tests(plan)], [['*']])

    def test_duration_is_recorded_for_passed_and_failed_runs(self):
        plan = self.plan(['web/src/login.js'])
        _, proof, _, result = self.record(plan, '--duration-seconds', '252.5')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(proof.read_text(encoding='utf-8'))['durationSeconds'], 252.5)
        _, proof, _, result = self.record(plan, '--duration-seconds', '600', exit_code=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(proof.read_text(encoding='utf-8')),
                         {'passed': False, 'durationSeconds': 600.0})


class PathDetectTests(unittest.TestCase):
    """detect markers with '/' are repository-relative paths; the project runs in the marker directory."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location('test_plan', HELPER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def write(self, name, value=''):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')

    def projects(self, types):
        return sorted((p['type'], p['cwd']) for p in self.module.discover(self.root, types))

    def test_single_path_marker_uses_its_directory_as_project_cwd(self):
        self.write('backend/build.gradle.kts')
        self.assertEqual(self.projects({'java-spring': {
            'detect': ['backend/build.gradle.kts'], 'test': './gradlew test'}}),
            [('java-spring', 'backend')])

    def test_multiple_path_marker_projects_are_all_detected(self):
        self.write('backend/build.gradle.kts')
        self.write('frontend/package.json', '{}')
        self.write('tools/frontend/package.json', '{}')
        self.assertEqual(self.projects({
            'java-spring': {'detect': ['backend/build.gradle.kts'], 'test': './gradlew test'},
            'node': {'detect': ['frontend/package.json'], 'test': 'pnpm test'}}),
            [('java-spring', 'backend'), ('node', 'frontend')])

    def test_name_and_double_star_markers_keep_matching_any_directory(self):
        self.write('package.json', '{}')
        self.write('web/package.json', '{}')
        for detect in (['package.json'], ['**/package.json']):
            with self.subTest(detect=detect):
                self.assertEqual(self.projects({'node': {'detect': detect, 'test': 'npm test'}}),
                                 [('node', '.'), ('node', 'web')])

    def test_explicit_root_runs_composite_command_from_repository_root(self):
        self.write('frontend/package.json', '{}')
        types = {'fullstack': {'roots': ['.'], 'detect': ['build.gradle.kts', 'frontend/package.json'],
                               'test': './gradlew test && pnpm --dir frontend test'}}
        self.assertEqual(self.projects(types), [('fullstack', '.')])
        types['fullstack']['roots'] = ['backend']
        self.write('backend/build.txt')
        with self.assertRaisesRegex(ValueError, 'not detected'):
            self.projects(types)

    # The real consumer layout: path markers with commands that cd into the same directory.
    KREB = {'java-spring': {'detect': ['backend/build.gradle.kts'],
                            'build': 'cd backend && ./gradlew build', 'test': 'cd backend && ./gradlew test',
                            'focusedTest': 'cd backend && ./gradlew test --tests {pattern}'},
            'node': {'detect': ['frontend/package.json'], 'build': 'cd frontend && pnpm build',
                     'test': 'cd frontend && pnpm test && pnpm lint',
                     'focusedTest': 'cd frontend && pnpm vitest run {files}'}}

    def focused(self, project, tests, types):
        self.write('.claude/config.json', json.dumps({'projectTypes': types}))
        self.write('tests.json', json.dumps(tests))
        args = type('Args', (), {'cwd': self.root, 'config': None, 'project': project,
                                 'tests_file': self.root / 'tests.json'})()
        return self.module.focused(args)

    def kreb_fixture(self):
        self.write('backend/build.gradle.kts')
        self.write('backend/src/test/kotlin/LoginTest.kt', 'class LoginTest')
        self.write('frontend/package.json', '{"scripts":{"test":"vitest run"}}')
        self.write('frontend/src/cart.test.ts', 'test("cart", () => {})')

    def test_kreb_config_is_detected_and_focused_without_its_same_directory_cd(self):
        import shlex
        self.kreb_fixture()
        self.assertEqual(self.projects(self.KREB), [('java-spring', 'backend'), ('node', 'frontend')])
        web = self.focused('node:frontend', ['frontend/src/cart.test.ts'], self.KREB)
        self.assertEqual(web['cwd'], 'frontend')
        self.assertEqual(shlex.split(web['command']), ['pnpm', 'vitest', 'run', 'src/cart.test.ts'])
        api = self.focused('java-spring:backend', ['backend/src/test/kotlin/LoginTest.kt'], self.KREB)
        self.assertEqual((api['cwd'], api['command']), ('backend', './gradlew test --tests LoginTest'))

    def test_kreb_plan_runs_stripped_commands_in_each_project_directory(self):
        self.kreb_fixture()
        types = json.loads(json.dumps(self.KREB))
        self.write('.claude/config.json', json.dumps({'projectTypes': types}))
        args = type('Args', (), {'cwd': self.root, 'config': None, 'base': 'HEAD', 'run_id': 'run-1',
                                 'changed_file': None, 'tests_file': None, 'ownership_file': None,
                                 'full': False, 'rerun_tests': False})()
        changed = ['backend/src/main/kotlin/Login.kt', 'context/auth/status.md']
        with mock.patch.object(self.module, 'changed_paths', return_value=changed), \
             mock.patch.object(self.module, 'fingerprint', return_value='123:abcdef123456'):
            # The frontend build is custom; the existing explicit test-free build rule still applies.
            with self.assertRaisesRegex(ValueError, 'buildOnly required'):
                self.module.plan(args)
            types['node']['buildOnly'] = 'cd frontend && pnpm build'
            self.write('.claude/config.json', json.dumps({'projectTypes': types}))
            plan = self.module.plan(args)
        commands = {(e['cwd'], e['kind']): e['command'] for e in plan['entries']}
        self.assertEqual(commands, {('backend', 'test'): './gradlew test',
                                    ('backend', 'build'): './gradlew build -x test testClasses',
                                    ('frontend', 'test'): 'pnpm test && pnpm lint',
                                    ('frontend', 'build'): 'pnpm build'})

    def test_same_directory_cd_forms_are_dropped_and_other_targets_are_configuration_errors(self):
        self.write('backend/build.gradle.kts')
        for command in ('cd backend && ./gradlew test', 'cd ./backend && ./gradlew test',
                        'cd "backend" && ./gradlew test', "cd 'backend/' && ./gradlew test"):
            with self.subTest(command=command):
                self.assertEqual(self.module.project_commands('backend', {'test': command})['test'],
                                 './gradlew test')
        for command in ('cd ../shared && ./gradlew test', 'cd api && ./gradlew test', 'cd backend; ./gradlew test'):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, 'leaves project directory'):
                    self.module.project_commands('backend', {'test': command})
        root = {'test': 'cd backend && ./gradlew test'}
        self.assertEqual(self.module.project_commands('.', root), root)


if __name__ == '__main__':
    unittest.main()
