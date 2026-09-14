#!/usr/bin/env python3
"""Compute the GX Git fingerprint without writing into the real Git database."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def git(root, env, *args):
    """Run Git with trust limited to this repository for this one command."""
    result = subprocess.run(
        ['git', '-c', f'safe.directory={root.as_posix()}', *args],
        cwd=root, env=env, capture_output=True, text=True,
        encoding='utf-8', errors='replace', check=True, timeout=30)
    return result.stdout.strip()


def fingerprint(cwd):
    root = Path(cwd).resolve()
    if not root.is_dir():
        raise ValueError('project root is not a directory')
    env = os.environ.copy()
    reported_root = Path(git(root, env, 'rev-parse', '--show-toplevel')).resolve()
    if reported_root != root:
        raise ValueError('--cwd must be the Git project root')
    object_path = Path(git(root, env, 'rev-parse', '--git-path', 'objects'))
    if not object_path.is_absolute():
        object_path = root / object_path
    object_path = object_path.resolve()
    if not object_path.is_dir():
        raise ValueError('Git object directory does not exist')

    with tempfile.TemporaryDirectory(prefix='gx-fingerprint-') as directory:
        temporary = Path(directory)
        object_store = temporary / 'objects'
        object_store.mkdir()
        isolated = env.copy()
        isolated['GIT_INDEX_FILE'] = str(temporary / 'index')
        isolated['GIT_OBJECT_DIRECTORY'] = str(object_store)
        existing = env.get('GIT_ALTERNATE_OBJECT_DIRECTORIES', '')
        isolated['GIT_ALTERNATE_OBJECT_DIRECTORIES'] = os.pathsep.join(
            [str(object_path), *([existing] if existing else [])])
        git(root, isolated, 'add', '-A')
        git(root, isolated, 'rm', '-r', '--cached', '-q', '--ignore-unmatch', '.dev')
        tree = git(root, isolated, 'write-tree')

    head = git(root, env, 'rev-parse', '--short', 'HEAD')
    if not re.fullmatch(r'[0-9a-f]+', head) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', tree):
        raise ValueError('Git returned an invalid fingerprint component')
    return f'{head}:{tree[:12]}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', required=True, type=Path)
    args = parser.parse_args()
    try:
        value = fingerprint(args.cwd)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or '').strip() or str(exc)
        sys.stderr.buffer.write(f'fingerprint failed: {detail}\n'.encode('utf-8'))
        return 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        sys.stderr.buffer.write(f'fingerprint failed: {exc}\n'.encode('utf-8'))
        return 1
    sys.stdout.buffer.write((value + '\n').encode('ascii'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
