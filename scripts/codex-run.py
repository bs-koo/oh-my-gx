#!/usr/bin/env python3
"""Run Codex headlessly, keeping its final answer separate from JSON events."""
import argparse
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys


def build_argv(command, cwd, final, mode, model):
    if mode not in ('review', 'iterate'):
        raise ValueError('mode must be review or iterate')
    argv = [*command, 'exec', '--cd', str(cwd), '--sandbox',
            'read-only' if mode == 'review' else 'workspace-write',
            '--json', '--color', 'never', '--output-last-message', str(final)]
    if model:
        argv.extend(['--model', model])
    return [*argv, '-']


def stop_tree(proc):
    if os.name == 'nt':
        # CREATE_NEW_PROCESS_GROUP alone does not terminate grandchildren.
        try:
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()


def run_codex(command, cwd, prompt, final, events, mode, model, timeout):
    try:
        cwd, prompt, final, events = (Path(p).resolve() for p in (cwd, prompt, final, events))
        stderr_path = Path(str(events) + '.stderr')
        if (not command or not cwd.is_dir() or not prompt.is_file()
                or not math.isfinite(timeout) or timeout <= 0
                or len({prompt, final, events, stderr_path}) != 4
                or any(p.exists() for p in (final, events, stderr_path))):
            return 2
        argv = build_argv(command, cwd, final, mode, model)
        if os.name == 'nt' and str(command[0]).lower().endswith(('.cmd', '.bat')):
            if any(any(c in str(arg) for c in '&|<>^%!()\r\n"') for arg in argv):
                return 2
        data = prompt.read_bytes()
        data.decode('utf-8')
        final.parent.mkdir(parents=True, exist_ok=True)
        events.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, UnicodeError, ValueError, TypeError):
        return 2

    proc = None
    try:
        with events.open('xb') as out, stderr_path.open('xb') as err:
            proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE,
                                    stdout=out, stderr=err,
                                    start_new_session=(os.name != 'nt'),
                                    creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP
                                                   if os.name == 'nt' else 0))
            try:
                proc.communicate(data, timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_tree(proc)
                return 124
        if proc.returncode != 0 or not final.is_file():
            return 3
        return 0 if final.read_text(encoding='utf-8').strip() else 3
    except (OSError, UnicodeError, ValueError, OverflowError, subprocess.SubprocessError):
        if proc is not None and proc.poll() is None:
            stop_tree(proc)
        return 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('--prompt', type=Path, required=True)
    parser.add_argument('--final', type=Path, required=True)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--mode', choices=('review', 'iterate'), required=True)
    parser.add_argument('--model')
    parser.add_argument('--timeout', type=float)
    parser.add_argument('--codex-executable')
    args = parser.parse_args()
    executable = args.codex_executable or shutil.which('codex.cmd' if os.name == 'nt' else 'codex')
    if not executable:
        print('codex executable not found', file=sys.stderr)
        return 2
    timeout = args.timeout if args.timeout is not None else (300 if args.mode == 'review' else 1800)
    rc = run_codex([executable], args.cwd, args.prompt, args.final, args.events,
                   args.mode, args.model, timeout)
    if rc == 0:
        sys.stdout.buffer.write(args.final.read_bytes())
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
