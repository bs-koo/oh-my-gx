#!/usr/bin/env python3
"""리뷰 diff/stat과 전체 변경 파일 목록을 읽기 전용으로 수집한다. stdin/stdout JSON."""
import json
import os
from pathlib import Path
import subprocess
import sys


def git(root, *args, difference=False):
    env = os.environ.copy()
    env['GIT_OPTIONAL_LOCKS'] = '0'
    proc = subprocess.run(['git', '-c', f'safe.directory={root.as_posix()}',
                           '-c', 'core.quotePath=false', *args], cwd=root,
                          capture_output=True, timeout=30, env=env)
    if proc.returncode not in ((0, 1) if difference else (0,)):
        raise ValueError(proc.stderr.decode('utf-8', errors='replace').strip())
    return proc.stdout.decode('utf-8', errors='replace')


def collect(payload):
    root = Path(payload['cwd']).resolve()
    if not Path(payload['cwd']).is_absolute() or Path(git(root, 'rev-parse', '--show-toplevel').strip()).resolve() != root:
        raise ValueError('cwd는 Git 루트 절대경로여야 합니다')
    base = payload['base']
    if not isinstance(base, str) or not base or base.startswith('-'):
        raise ValueError('base ref가 잘못됐습니다')
    scope = payload.get('scope', 'diff')
    if scope not in ('diff', 'stat'):
        raise ValueError('scope는 diff 또는 stat입니다')
    revision = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').strip()
    ancestor = git(root, 'merge-base', 'HEAD', revision).strip()
    tracked = git(root, 'diff', '--name-only', '-z', ancestor, '--', '.', ':(exclude).dev').split('\x00')
    untracked = [p for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\x00')
                 if p and p != '.dev' and not p.startswith('.dev/')]
    files = sorted(set(p for p in tracked + untracked if p))

    def render(stat):
        flags = ['--stat'] if stat else ['--binary']
        output = git(root, 'diff', *flags, ancestor, '--', '.', ':(exclude).dev')
        for path in untracked:
            output += git(root, 'diff', '--no-index', *flags, '--', '/dev/null', path, difference=True)
        return output

    output = render(scope == 'stat')
    if scope == 'diff' and len(output.splitlines()) >= 500:
        scope = 'stat'
        output = render(True)
    if files:
        output += '\n변경 파일 목록 (tracked + untracked):\n' + '\n'.join(files) + '\n'
        if scope == 'stat':
            output += '위는 요약입니다. 목록의 모든 파일을 직접 Read하여 확인하세요.\n'
    return {'scope': scope, 'files': files, 'untracked': untracked, 'text': output}


def main():
    try:
        result = collect(json.loads(sys.stdin.buffer.read().decode('utf-8')))
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + '\n').encode('utf-8'))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        sys.stderr.buffer.write((str(exc) + '\n').encode('utf-8'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
