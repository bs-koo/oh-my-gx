#!/usr/bin/env python3
"""리뷰 diff/stat과 전체 변경 파일 목록을 읽기 전용으로 수집한다. stdin JSON 입력, 지정 파일에 diff 저장, stdout JSON은 요약만 출력."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def git(root, *args, difference=False, index=None, stdin=None):
    """git을 실행해 stdout 바이트를 돌려준다. 소스 인코딩을 바꾸지 않도록 디코딩하지 않는다."""
    env = os.environ.copy()
    env['GIT_OPTIONAL_LOCKS'] = '0'
    # 사용자 환경의 pathspec 해석 변수가 :(exclude) 등 helper의 pathspec 의미를 바꾸지 않게 한다.
    for name in ('GIT_LITERAL_PATHSPECS', 'GIT_GLOB_PATHSPECS', 'GIT_NOGLOB_PATHSPECS', 'GIT_ICASE_PATHSPECS'):
        env.pop(name, None)
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
    proc = subprocess.run(['git', '-c', f'safe.directory={root.as_posix()}',
                           '-c', 'core.quotePath=false', *args], cwd=root, input=stdin,
                          capture_output=True, timeout=120, env=env)
    if proc.returncode not in ((0, 1) if difference else (0,)):
        raise ValueError(proc.stderr.decode('utf-8', errors='replace').strip())
    return proc.stdout


def text(root, *args):
    return git(root, *args).decode('utf-8', errors='replace')


def collect(payload):
    root = Path(payload['cwd']).resolve()
    if not Path(payload['cwd']).is_absolute() or Path(text(root, 'rev-parse', '--show-toplevel').strip()).resolve() != root:
        raise ValueError('cwd는 Git 루트 절대경로여야 합니다')
    base = payload['base']
    if not isinstance(base, str) or not base or base.startswith('-'):
        raise ValueError('base ref가 잘못됐습니다')
    scope = payload.get('scope', 'diff')
    if scope not in ('diff', 'stat'):
        raise ValueError('scope는 diff 또는 stat입니다')
    if not isinstance(payload['output'], str) or not Path(payload['output']).is_absolute():
        raise ValueError('output은 diff를 저장할 절대경로여야 합니다')
    output_path = Path(payload['output'])
    # 출력 파일이 저장소 안이면 직전 결과가 다음 diff에 섞이지 않도록 대상에서 뺀다.
    try:
        own = output_path.resolve().relative_to(root).as_posix()
    except ValueError:
        own = None
    revision = text(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').strip()
    ancestor = text(root, 'merge-base', 'HEAD', revision).strip()
    excluded = [':(exclude).dev'] + ([':(exclude,literal)' + own] if own else [])
    tracked = text(root, 'diff', '--name-only', '-z', ancestor, '--', '.', *excluded).split('\x00')
    untracked = [p for p in text(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\x00')
                 if p and p != '.dev' and not p.startswith('.dev/') and p != own]
    files = sorted(set(p for p in tracked + untracked if p))

    with tempfile.TemporaryDirectory(prefix='gx-review-') as directory:
        # untracked는 임시 index에 intent-to-add로 올려 한 번의 git diff로 처리한다. 실제 index는 변경하지 않는다.
        temporary = Path(directory) / 'index'
        real = Path(text(root, 'rev-parse', '--git-path', 'index').strip())
        real = real if real.is_absolute() else root / real
        if real.is_file():
            temporary.write_bytes(real.read_bytes())
        else:
            git(root, 'read-tree', 'HEAD', index=temporary)
        if untracked:
            git(root, '--literal-pathspecs', 'add', '-N', '--pathspec-from-file=-', '--pathspec-file-nul',
                index=temporary, stdin='\x00'.join(untracked).encode('utf-8'))

        def render(stat):
            flags = ['--stat'] if stat else ['--binary']
            return git(root, 'diff', *flags, ancestor, '--', '.', *excluded, index=temporary)

        output = render(scope == 'stat')
        reduced = False
        if scope == 'diff' and len(output.splitlines()) >= 500:
            scope, reduced = 'stat', True
            output = render(True)
    if files:
        output += ('\n변경 파일 목록 (tracked + untracked):\n' + '\n'.join(files) + '\n').encode('utf-8')
        if scope == 'stat':
            output += '위는 요약입니다. 목록의 모든 파일을 직접 Read하여 확인하세요.\n'.encode('utf-8')
    # 성공한 결과만 원자적으로 저장한다. 실패하면 기존 파일은 그대로 남는다.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_name(output_path.name + '.tmp')
    partial.write_bytes(output)
    os.replace(partial, output_path)
    return {'scope': scope, 'reduced': reduced, 'files': files, 'untracked': untracked,
            'output': str(output_path), 'bytes': len(output), 'lines': len(output.splitlines())}


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
