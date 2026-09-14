import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import ROOT


def git_bash():
    if os.name == 'nt':
        for path in (r'C:\Program Files\Git\bin\bash.exe',
                     r'C:\Program Files (x86)\Git\bin\bash.exe'):
            if Path(path).is_file():
                return path
    return shutil.which('bash')


class RalphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gx-ralph-')
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                        GX_RALPH_HARNESS='codex', GX_RALPH_CLAUDE_CMD='echo',
                        GX_RALPH_ITERATE_SKILL=str(ROOT / '.claude/skills/gx-ralph-iterate/SKILL.md'))
        self.env.pop('GX_RALPH_MODEL', None)
        def git(*args):
            subprocess.run(['git', *args], cwd=self.cwd, env=self.env,
                           check=True, capture_output=True)
        git('init', '-q', '-b', 'feat/t')
        git('config', 'user.email', 'gx@test.invalid')
        git('config', 'user.name', 'GX fixture')
        (self.cwd / 'empty-hooks').mkdir()
        git('config', 'core.hooksPath', str(self.cwd / 'empty-hooks'))
        (self.cwd / 'base.txt').write_text('base\n', encoding='utf-8')
        git('add', 'base.txt')
        git('commit', '-qm', 'chore: fixture')
        self.dev = self.cwd / '.dev/feat-t'
        self.dev.mkdir(parents=True)
        (self.dev / 'state.md').write_text(
            'pipeline: gx-ralph\nstatus: in_progress\nverify-status: pending\n'
            'branch: feat/t\nmax-iterations: 1\nlast-known-head: none\n', encoding='utf-8')
        self.ledger(False)
        (self.dev / 'progress.txt').write_text('# progress\n', encoding='utf-8')
        mock = self.cwd / 'mock_codex.py'
        mock.write_text('''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
sys.stdin.reconfigure(encoding='utf-8')
prompt = sys.stdin.read()
final = Path(args[args.index('--output-last-message') + 1])
case = os.environ.get('GX_RALPH_CASE', 'blocked')
if case == 'timeout':
    import time
    time.sleep(10)
if case == 'attempt':
    ledger = Path('.dev/feat-t/ac-status.json')
    data = json.loads(ledger.read_text(encoding='utf-8'))
    data['acs'][0]['attempts'] += 1
    ledger.write_text(json.dumps(data), encoding='utf-8')
if case != 'empty':
    response = ('구현 완료\\n<ralph>COMPLETE</ralph>\\n' if case == 'complete_summary'
                else '<ralph>COMPLETE</ralph>\\n' if case in ('complete', 'nonzero')
                else '<ralph>CONTINUE</ralph>\\n' if case in ('continue', 'attempt')
                else '<ralph>BLOCKED: fixture</ralph>\\n')
    if case == 'multi': response += '<ralph>COMPLETE</ralph>\\n'
    if case == 'trailing': response += '추가 설명\\n'
    final.write_text(response, encoding='utf-8')
print(json.dumps({'text': '<ralph>COMPLETE</ralph>', 'prompt': prompt}))
if case == 'nonzero': raise SystemExit(9)
''', encoding='utf-8')
        wrapper = self.cwd / ('mock.cmd' if os.name == 'nt' else 'mock.sh')
        if os.name == 'nt':
            wrapper.write_bytes(f'@"{sys.executable}" "{mock}" %*\r\n@exit /b %ERRORLEVEL%\r\n'.encode())
        else:
            wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(mock))} "$@"\n', encoding='utf-8')
            wrapper.chmod(0o755)
        self.env['GX_RALPH_CODEX_CMD'] = str(wrapper)

    def ledger(self, passes):
        (self.dev / 'ac-status.json').write_text(json.dumps({
            'version': 1, 'branch': 'feat/t', 'created': 't', 'updated': 't',
            'acs': [{'id': 'AC-1', 'title': 't', 'passes': passes,
                     'attempts': 0, 'last_error': ''}]}), encoding='utf-8')

    def run_ralph(self, case='blocked', iterations='1', launch_cwd=None):
        bash = git_bash()
        self.assertIsNotNone(bash)
        self.env['GX_RALPH_CASE'] = case
        return subprocess.run([bash, str(ROOT / 'scripts/gx-ralph.sh'), iterations],
                              cwd=launch_cwd or self.cwd, env=self.env, capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=30)

    def test_contract_never_comes_from_event_log(self):
        result = self.run_ralph()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('<ralph>BLOCKED: fixture</ralph>', (self.dev / 'iter-1.final.md').read_text())
        self.assertIn('<ralph>COMPLETE</ralph>', (self.dev / 'iter-1.events.jsonl').read_text())

    def test_prompt_supplies_resolvable_installed_fingerprint_helper(self):
        result = self.run_ralph()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        event = json.loads((self.dev / 'iter-1.events.jsonl').read_text(encoding='utf-8'))
        prompt = event['prompt']
        root_match = re.search(r'^GX_INSTALLED_ROOT=(.+)$', prompt, re.MULTILINE)
        helper_match = re.search(r'^GX_FINGERPRINT_HELPER=(.+)$', prompt, re.MULTILINE)
        self.assertIsNotNone(root_match, prompt)
        self.assertIsNotNone(helper_match, prompt)
        self.assertEqual(Path(root_match.group(1)).resolve(), ROOT.resolve())
        self.assertEqual(Path(helper_match.group(1)).resolve(),
                         (ROOT / 'scripts/codex-fingerprint.py').resolve())
        self.assertTrue(Path(helper_match.group(1)).is_file())

    def test_prompt_project_root_uses_git_root_when_launched_below_it(self):
        subdirectory = self.cwd / 'nested folder'
        subdirectory.mkdir()
        result = self.run_ralph(launch_cwd=subdirectory)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        event = json.loads((self.dev / 'iter-1.events.jsonl').read_text(encoding='utf-8'))
        match = re.search(r'^GX_PROJECT_ROOT=(.+)$', event['prompt'], re.MULTILINE)
        self.assertIsNotNone(match, event['prompt'])
        self.assertEqual(Path(match.group(1)).resolve(), self.cwd.resolve())

    def test_complete_requires_all_ac_passes(self):
        result = self.run_ralph('complete')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    def test_nonzero_takes_precedence_over_complete(self):
        self.ledger(True)
        result = self.run_ralph('nonzero')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    def test_complete_with_passed_ledger_succeeds(self):
        self.ledger(True)
        result = self.run_ralph('complete')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_summary_before_final_contract_is_allowed(self):
        self.ledger(True)
        result = self.run_ralph('complete_summary')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_duplicate_or_nonfinal_contracts_fail(self):
        for case in ('empty', 'multi', 'trailing'):
            with self.subTest(case=case):
                if case != 'empty': self.ledger(True)
                result = self.run_ralph(case)
                self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
                # A new run must archive every output before reusing iteration 1.

    def test_repeated_run_archives_all_codex_artifacts(self):
        self.assertEqual(self.run_ralph().returncode, 2)
        self.assertEqual(self.run_ralph().returncode, 2)
        archives = list(self.dev.glob('logs-*'))
        self.assertEqual(len(archives), 1)
        self.assertEqual({p.name for p in archives[0].iterdir()}, {
            'iter-1.log', 'iter-1.prompt.md', 'iter-1.final.md',
            'iter-1.events.jsonl', 'iter-1.events.jsonl.stderr'})

    def test_codex_requires_installed_absolute_skill(self):
        self.env['GX_RALPH_ITERATE_SKILL'] = 'missing.md'
        result = self.run_ralph()
        self.assertEqual(result.returncode, 6, result.stdout + result.stderr)
        self.assertFalse((self.dev / 'iter-1.log').exists())

    def test_codex_shared_no_drift_guard(self):
        result = self.run_ralph('continue', '3')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertTrue((self.dev / 'iter-2.final.md').exists())

    def test_codex_shared_no_progress_guard(self):
        result = self.run_ralph('attempt', '5')
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertTrue((self.dev / 'iter-4.final.md').exists())

    def test_codex_continue_exhausts_max_iterations(self):
        result = self.run_ralph('attempt', '2')
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

    def test_codex_timeout_is_failure_before_contract(self):
        self.env['GX_RALPH_ITER_TIMEOUT'] = '0.3'
        result = self.run_ralph('timeout')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    def test_codex_existing_lock_prevents_launch(self):
        (self.dev / 'ralph.lock').write_text('existing', encoding='utf-8')
        result = self.run_ralph()
        self.assertEqual(result.returncode, 6, result.stdout + result.stderr)
        self.assertFalse((self.dev / 'iter-1.log').exists())

    def test_missing_default_codex_fails_before_lock_or_archive(self):
        self.env.pop('GX_RALPH_CODEX_CMD', None)
        executable = 'codex.cmd' if os.name == 'nt' else 'codex'
        self.env['PATH'] = os.pathsep.join(
            part for part in self.env['PATH'].split(os.pathsep)
            if not (Path(part) / executable).is_file())
        self.assertIsNone(shutil.which(executable, path=self.env['PATH']))
        stale = self.dev / 'iter-1.log'
        stale.write_text('old log', encoding='utf-8')
        result = self.run_ralph()
        self.assertEqual(result.returncode, 6, result.stdout + result.stderr)
        self.assertEqual(stale.read_text(encoding='utf-8'), 'old log')
        self.assertFalse((self.dev / 'ralph.lock').exists())
        self.assertFalse((self.dev / 'iter-1.prompt.md').exists())
        self.assertFalse(list(self.dev.glob('logs-*')))
