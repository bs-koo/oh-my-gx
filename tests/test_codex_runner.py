import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from codex_test_support import ROOT, load

runner = load('gx_runner', 'scripts/codex-run.py')
MOCK = [sys.executable, str(ROOT / 'tests/fixtures/codex/mock_codex.py')]


class RunnerTests(unittest.TestCase):
    def test_stdin_events_stderr_and_final_are_separate(self):
        with tempfile.TemporaryDirectory(prefix='gx runner 한글 ') as directory:
            cwd = Path(directory)
            prompt, final, events = (cwd / n for n in ('prompt.md', 'final.md', 'events.jsonl'))
            prompt.write_text('한글 $x `value` & 내용', encoding='utf-8')
            self.assertEqual(runner.run_codex(MOCK, cwd, prompt, final, events, 'review', None, 5), 0)
            event = json.loads(events.read_text(encoding='utf-8'))
            self.assertEqual(event['prompt'], '한글 $x `value` & 내용')
            self.assertNotIn(event['prompt'], event['args'])
            self.assertIn('read-only', event['args'])
            self.assertEqual(final.read_text(encoding='utf-8'), '검증 완료\n')
            self.assertIn('mock diagnostic', Path(str(events) + '.stderr').read_text())

    def test_nonzero_or_empty_final_fails_even_with_event_complete(self):
        for case in ('failure', 'empty'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                cwd = Path(directory)
                prompt, final, events = (cwd / n for n in ('p', 'f', 'e'))
                prompt.write_text('test', encoding='utf-8')
                old = os.environ.get('GX_CODEX_MOCK_CASE')
                os.environ['GX_CODEX_MOCK_CASE'] = case
                try:
                    self.assertEqual(runner.run_codex(MOCK, cwd, prompt, final, events, 'iterate', None, 5), 3)
                finally:
                    if old is None: os.environ.pop('GX_CODEX_MOCK_CASE', None)
                    else: os.environ['GX_CODEX_MOCK_CASE'] = old

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            prompt, final, events = (cwd / n for n in ('p', 'f', 'e'))
            prompt.write_text('test', encoding='utf-8')
            final.write_text('stale', encoding='utf-8')
            self.assertEqual(runner.run_codex(MOCK, cwd, prompt, final, events, 'review', None, 5), 2)
            self.assertEqual(final.read_text(), 'stale')
            self.assertFalse(events.exists())

    def test_timeout_kills_child_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            command = MOCK
            if os.name == 'nt':
                wrapper = cwd / 'mock.cmd'
                wrapper.write_bytes((f'@"{sys.executable}" "{MOCK[1]}" %*\r\n'
                                     '@exit /b %ERRORLEVEL%\r\n').encode())
                command = [str(wrapper)]
            prompt, final, events = (cwd / n for n in ('p', 'f', 'e'))
            prompt.write_text('test', encoding='utf-8')
            old = os.environ.get('GX_CODEX_MOCK_CASE')
            os.environ['GX_CODEX_MOCK_CASE'] = 'child'
            try:
                self.assertEqual(runner.run_codex(command, cwd, prompt, final, events, 'iterate', None, .3), 124)
            finally:
                if old is None: os.environ.pop('GX_CODEX_MOCK_CASE', None)
                else: os.environ['GX_CODEX_MOCK_CASE'] = old
            time.sleep(2.2)
            self.assertFalse((cwd / 'child-survived').exists())

    def test_mode_and_model_are_explicit(self):
        args = runner.build_argv(['codex'], Path('x'), Path('f'), 'iterate', 'gpt-test')
        self.assertIn('workspace-write', args)
        self.assertEqual(args[-1], '-')
        self.assertEqual(args[args.index('--model') + 1], 'gpt-test')

    @unittest.skipUnless(os.name == 'nt', 'Windows cmd shim')
    def test_cmd_shim_supports_spaces_and_korean_but_rejects_metacharacters(self):
        with tempfile.TemporaryDirectory(prefix='gx runner 한글 ') as directory:
            cwd = Path(directory)
            wrapper = cwd / 'mock codex.cmd'
            wrapper.write_bytes((f'@"{sys.executable}" "{MOCK[1]}" %*\r\n'
                                 '@exit /b %ERRORLEVEL%\r\n').encode())
            prompt, final, events = (cwd / n for n in ('prompt.md', 'final.md', 'events.jsonl'))
            prompt.write_text('안전한 내용 & %!', encoding='utf-8')
            self.assertEqual(runner.run_codex([str(wrapper)], cwd, prompt, final,
                                              events, 'review', None, 5), 0)
            self.assertEqual(json.loads(events.read_text(encoding='utf-8'))['prompt'],
                             '안전한 내용 & %!')
            other_final, other_events = cwd / 'other.md', cwd / 'other.jsonl'
            for bad_model in ('bad&model', 'bad(model)'):
                with self.subTest(bad_model=bad_model):
                    self.assertEqual(runner.run_codex([str(wrapper)], cwd, prompt, other_final,
                                                      other_events, 'iterate', bad_model, 5), 2)
                    self.assertFalse(other_events.exists())

    def test_cli_stdout_contains_only_final_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            prompt, final, events = (cwd / n for n in ('p', 'f', 'e'))
            prompt.write_text('hello', encoding='utf-8')
            if os.name == 'nt':
                wrapper = cwd / 'mock.cmd'
                wrapper.write_bytes((f'@"{sys.executable}" "{MOCK[1]}" %*\r\n'
                                     '@exit /b %ERRORLEVEL%\r\n').encode())
            else:
                wrapper = cwd / 'mock.sh'
                wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} '
                                   f'{shlex.quote(MOCK[1])} "$@"\n', encoding='utf-8')
                wrapper.chmod(0o755)
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/codex-run.py'),
                                     '--cwd', str(cwd), '--prompt', str(prompt),
                                     '--final', str(final), '--events', str(events),
                                     '--mode', 'review', '--codex-executable', str(wrapper)],
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, final.read_bytes())

    def test_cli_rejects_zero_and_negative_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            prompt = cwd / 'p'
            prompt.write_text('hello', encoding='utf-8')
            for timeout in ('0', '-1', 'NaN', 'Infinity', '-Infinity'):
                with self.subTest(timeout=timeout):
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts/codex-run.py'),
                                             '--cwd', str(cwd), '--prompt', str(prompt),
                                             '--final', str(cwd / 'f'), '--events', str(cwd / 'e'),
                                             '--mode', 'review', '--timeout', timeout,
                                             '--codex-executable', MOCK[0]],
                                            capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse((cwd / 'e').exists())

    def test_nonfinite_timeout_is_rejected_before_process_launch(self):
        for timeout in (math.nan, math.inf, -math.inf):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as directory:
                cwd = Path(directory)
                prompt, final, events = (cwd / n for n in ('p', 'f', 'e'))
                prompt.write_text('hello', encoding='utf-8')
                self.assertEqual(runner.run_codex(MOCK, cwd, prompt, final, events,
                                                  'review', None, timeout), 2)
                self.assertFalse(final.exists())
                self.assertFalse(events.exists())

    def test_unexpected_wait_error_still_kills_child_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            prompt, final, events = (cwd / n for n in ('p', 'f', 'e'))
            prompt.write_text('hello', encoding='utf-8')
            old_case = os.environ.get('GX_CODEX_MOCK_CASE')
            os.environ['GX_CODEX_MOCK_CASE'] = 'child'
            original = subprocess.Popen.communicate
            raised = False

            def fail_first_wait(proc, *args, **kwargs):
                nonlocal raised
                if not raised:
                    raised = True
                    time.sleep(.2)
                    raise ValueError('unexpected wait error')
                return original(proc, *args, **kwargs)

            try:
                with mock.patch.object(subprocess.Popen, 'communicate', fail_first_wait):
                    self.assertEqual(runner.run_codex(MOCK, cwd, prompt, final, events,
                                                      'iterate', None, 5), 3)
            finally:
                if old_case is None: os.environ.pop('GX_CODEX_MOCK_CASE', None)
                else: os.environ['GX_CODEX_MOCK_CASE'] = old_case
            time.sleep(2.2)
            self.assertFalse((cwd / 'child-survived').exists())
