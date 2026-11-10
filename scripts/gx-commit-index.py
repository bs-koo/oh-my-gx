#!/usr/bin/env python3
"""커밋 스킬의 인덱스 보존·제외·복구. stdin JSON만 받고 커밋은 실행하지 않는다."""
from contextlib import contextmanager
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


RUNTIME = ['.dev/*/ralph.lock', '.dev/*/iter-*.log', '.dev/architecture', '.dev/*/visual/*']


def git(root, *args, check=True, index=None):
    env = os.environ.copy()
    env['GIT_OPTIONAL_LOCKS'] = '0'
    options = ['-c', f'safe.directory={root.as_posix()}']
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
        options += ['-c', 'core.splitIndex=false']
    proc = subprocess.run(['git', *options, *args],
                          cwd=root, capture_output=True, timeout=30, env=env)
    if check and proc.returncode:
        raise ValueError(proc.stderr.decode('utf-8', errors='replace').strip())
    return proc


def text(root, *args):
    return git(root, *args).stdout.decode('utf-8').strip()


def identity(root):
    head = git(root, 'rev-parse', '--verify', 'HEAD', check=False)
    branch = git(root, 'symbolic-ref', '-q', 'HEAD', check=False)
    return [head.stdout.decode('ascii').strip(), branch.stdout.decode('utf-8').strip()]


def index_bytes(index):
    if index.is_symlink():
        raise ValueError('index symlink은 지원하지 않습니다')
    return index.read_bytes() if index.exists() else None


def digest(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None


def semantic_index(root, index):
    """stat/감시 캐시를 제외하고 blob·mode·stage·영구 플래그를 비교한다."""
    if index_bytes(index) is None:
        return None
    data = git(root, 'ls-files', '--stage', '--debug', '-z', index=index).stdout
    signature = hashlib.sha256()
    cursor = 0
    while cursor < len(data):
        end = data.index(b'\x00', cursor)
        debug = re.match(rb'  ctime: [^\n]*\n  mtime: [^\n]*\n  dev: [^\n]*\n'
                         rb'  uid: [^\n]*\n  size: [^\n]*\tflags: ([0-9a-fA-F]+)\n', data[end + 1:])
        if debug is None:
            raise ValueError('index debug 형식을 확인할 수 없습니다')
        # assume-unchanged, intent-to-add, skip-worktree는 stat 갱신과 구분한다.
        flags = int(debug.group(1), 16) & (0x8000 | 0x20000000 | 0x40000000)
        signature.update(data[cursor:end] + b'\x00' + flags.to_bytes(4, 'big'))
        cursor = end + 1 + debug.end()
    return signature.hexdigest()


def same_index(root, index, meta):
    return (digest(index_bytes(index)) == meta['expectedHash'] or
            semantic_index(root, index) == meta['expectedEntries'])


@contextmanager
def exclusive(path):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        yield fd
    finally:
        os.close(fd)
        path.unlink()


def save(snapshot, meta):
    temporary = snapshot / 'metadata.tmp'
    temporary.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, snapshot / 'metadata.json')


def paths(value):
    if not isinstance(value, list) or any(not isinstance(p, str) or not p or '\x00' in p
                                          or Path(p).is_absolute() or '..' in Path(p).parts
                                          for p in value):
        raise ValueError('paths/excludes는 저장소 상대경로 배열이어야 합니다')
    return value


def preview(root, payload):
    excluded = paths(payload.get('excludes', []))
    config_path = root / '.claude/config.json'
    config = json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.is_file() else {}
    sensitive = config.get('sensitiveFilePatterns', [])
    if not isinstance(sensitive, list) or any(not isinstance(p, str) for p in sensitive):
        raise ValueError('sensitiveFilePatterns는 문자열 배열이어야 합니다')
    head, branch = identity(root)
    staged = set(git(root, 'diff', '--cached', '--name-only', '--no-renames', '-z').stdout.decode('utf-8').split('\x00'))
    changed = (git(root, 'diff', '--name-only', '--no-renames', '-z', head).stdout.decode('utf-8').split('\x00')
               if head else list(staged) + git(root, 'diff', '--name-only', '-z').stdout.decode('utf-8').split('\x00'))
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z').stdout.decode('utf-8').split('\x00')
    rows = []
    for path in sorted((set(changed + untracked) | staged) - {''}):
        reasons = []
        if path in excluded:
            reasons.append('명시 제외')
        if any(path == pattern or path.startswith(pattern.rstrip('/') + '/') or fnmatch.fnmatchcase(path, pattern)
               for pattern in RUNTIME):
            reasons.append('runtime/시각화 산출물')
        if any(fnmatch.fnmatchcase(path, pattern) or ('/' not in pattern and fnmatch.fnmatchcase(Path(path).name, pattern))
               for pattern in sensitive):
            reasons.append('민감 파일 후보 — 실제 커밋 시 기존 확인 절차 적용')
        if path not in changed and path not in untracked:
            reasons.append('작업 트리는 HEAD와 동일 — 전체 스테이징 시 해제 후보')
        rows.append({'path': path, 'included': not reasons, 'alreadyStaged': path in staged, 'reasons': reasons})
    return {'action': 'preview', 'root': str(root), 'branch': branch.removeprefix('refs/heads/'),
            'commitAllowed': False, 'notice': '파일 후보 조회이며 커밋 가능 판정이나 실행 승인이 아닙니다',
            'files': rows}


def run(payload):
    if any(os.environ.get(k) for k in ('GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE')):
        raise ValueError('별도 Git 경로 환경변수가 있으면 index 변경 전에 중단합니다')
    root = Path(payload['cwd']).resolve()
    if not Path(payload['cwd']).is_absolute() or Path(text(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise ValueError('cwd는 확인된 Git 루트 절대경로여야 합니다')
    if payload['action'] == 'preview':
        return preview(root, payload)
    index = Path(text(root, 'rev-parse', '--git-path', 'index'))
    index = index if index.is_absolute() else root / index
    index = index.parent.resolve() / index.name
    lock = index.with_name(index.name + '.lock')
    base = index.parent / 'gx-index-snapshots'
    action = payload['action']
    if action == 'snapshot':
        # split index의 공유 파일을 GC/동시 Git 작업에서 보존할 수 없으므로 변경 전 차단한다.
        if text(root, 'rev-parse', '--shared-index-path'):
            raise ValueError('split index는 지원하지 않습니다. 기존 index를 보존하고 중단합니다')
        with exclusive(lock):
            original = index_bytes(index)
            base.mkdir(exist_ok=True)
            snapshot = Path(tempfile.mkdtemp(prefix='commit-', dir=base))
            if original is not None:
                (snapshot / 'original.index').write_bytes(original)
            meta = {'root': str(root), 'index': str(index), 'head': identity(root),
                    'originalHash': digest(original), 'expectedHash': digest(original),
                    'expectedEntries': semantic_index(root, index), 'excludes': []}
            save(snapshot, meta)
        return {'snapshot': str(snapshot), 'index': str(index)}
    snapshot = Path(payload['snapshot']).resolve()
    if snapshot.parent != base or not snapshot.name.startswith('commit-'):
        raise ValueError('현재 worktree의 관리되는 index snapshot 경로가 아닙니다')
    with exclusive(snapshot / 'operation.lock'):
        meta = json.loads((snapshot / 'metadata.json').read_text(encoding='utf-8'))
        if meta['root'] != str(root) or meta['index'] != str(index):
            raise ValueError('snapshot의 저장소/index가 다릅니다')
        if lock.exists():
            raise ValueError('index.lock이 있어 중단합니다. snapshot은 보존합니다')
        if action == 'finish':
            # 성공한 커밋 뒤에만 호출한다. 새로운 HEAD를 과거 snapshot으로 되돌리지 않는다.
            current = identity(root)
            if current[1] != meta['head'][1] or current[0] == meta['head'][0]:
                raise ValueError('같은 브랜치의 성공한 새 HEAD가 확인되지 않았습니다')
            for name in ('original.index', 'metadata.json'):
                (snapshot / name).unlink(missing_ok=True)
            result = {'finished': True}
        else:
            if identity(root) != meta['head']:
                raise ValueError('HEAD/브랜치가 변경됐습니다. index와 snapshot을 보존합니다')
            if not same_index(root, index, meta):
                raise ValueError('index가 외부에서 변경됐습니다. snapshot을 보존하고 중단합니다')
            if action == 'stage':
                selected = payload.get('paths')
                if selected is not None:
                    selected = paths(selected)
                excluded = paths(payload.get('excludes', []))
                untrack = paths(payload.get('untrack', []))
                specs = [':(literal)' + p for p in excluded] + RUNTIME
                # add/reset/rm은 실제 index와 분리한다. 실패·중단 시 실제 선택은 그대로다.
                with tempfile.TemporaryDirectory(prefix='stage-', dir=snapshot) as directory:
                    temporary = Path(directory)
                    staged_index = temporary / 'index'
                    # 후보의 시작 bytes도 검증과 같은 lock 아래 읽는다. 외부 작성자의
                    # 일시적인 staged 상태를 후보에 섞어 복제하지 않는다.
                    with exclusive(lock):
                        if identity(root) != meta['head'] or not same_index(root, index, meta):
                            raise ValueError('staging 시작 전 HEAD/index가 변경됐습니다')
                        if text(root, 'rev-parse', '--shared-index-path'):
                            raise ValueError('split index는 staging 전에 중단합니다')
                        original = index_bytes(index)
                        if original is not None:
                            staged_index.write_bytes(original)
                    if selected is None:
                        git(root, 'add', '-A', index=staged_index)
                    elif selected:
                        git(root, '--literal-pathspecs', 'add', '-A', '--', *selected, index=staged_index)
                    if meta['head'][0]:
                        git(root, 'reset', '-q', meta['head'][0], '--', *specs, index=staged_index)
                    else:
                        git(root, 'rm', '-r', '-f', '--cached', '--ignore-unmatch', '--', *specs,
                            index=staged_index)
                    if untrack:
                        git(root, 'rm', '-r', '-f', '--cached', '--ignore-unmatch', '--',
                            *(':(literal)' + p for p in untrack), index=staged_index)
                    assert_excluded(root, specs, index=staged_index, base=meta['head'][0])
                    candidate = index_bytes(staged_index)
                    next_meta = {**meta, 'expectedHash': digest(candidate),
                                 'expectedEntries': semantic_index(root, staged_index), 'excludes': excluded}
                    # 실제 index.lock은 publish·metadata 확정 동안 유지한다. 중간의 외부
                    # staged 변경은 새 expected로 채택하지 않고 그대로 보존한다.
                    with exclusive(lock):
                        if identity(root) != meta['head'] or not same_index(root, index, meta):
                            raise ValueError('staging 도중 HEAD/index가 외부에서 변경됐습니다. 실제 index를 보존합니다')
                        before_publish = index_bytes(index)
                        rollback = temporary / 'before.index'
                        if before_publish is not None:
                            rollback.write_bytes(before_publish)
                        if candidate is None:
                            index.unlink(missing_ok=True)
                        else:
                            os.replace(staged_index, index)
                        try:
                            save(snapshot, next_meta)
                        except OSError:
                            # 다른 Git 작성자는 lock으로 막혀 있다. metadata 확정 실패도
                            # 이 publish 직전의 실제 index로 되돌린 뒤 실패를 보고한다.
                            if before_publish is None:
                                index.unlink(missing_ok=True)
                            else:
                                os.replace(rollback, index)
                            raise
                result = {'staged': True}
            elif action == 'assert-excluded':
                assert_excluded(root, [':(literal)' + p for p in meta['excludes']] + RUNTIME,
                                base=meta['head'][0])
                result = {'excluded': True}
            elif action == 'restore':
                original_path = snapshot / 'original.index'
                original = index_bytes(original_path)
                if digest(original) != meta['originalHash']:
                    raise ValueError('원 index snapshot이 손상됐습니다. 복구하지 않습니다')
                # Git의 index.lock을 배타 확보한 뒤 같은 디렉터리에서 원자적으로 교체한다.
                with exclusive(lock):
                    if identity(root) != meta['head'] or not same_index(root, index, meta):
                        raise ValueError('복구 직전 HEAD/index가 변경됐습니다')
                    if original is None:
                        index.unlink(missing_ok=True)
                    else:
                        replacement = snapshot / 'restored.index'
                        with replacement.open('wb') as stream:
                            stream.write(original)
                            stream.flush()
                            os.fsync(stream.fileno())
                        # Windows에서는 열린 파일의 rename이 불가능하므로 닫힌 사본을 교체한다.
                        os.replace(replacement, index)
                meta['expectedHash'] = meta['originalHash']
                meta['expectedEntries'] = semantic_index(root, index)
                save(snapshot, meta)
                result = {'restored': True, 'snapshot': str(snapshot)}
            else:
                raise ValueError('알 수 없는 action')
    return result


def assert_excluded(root, specs, index=None, base=None):
    if base == '':
        changed = git(root, 'ls-files', '--stage', '-z', '--', *specs, index=index).stdout
    else:
        revision = [base] if base is not None else []
        changed = git(root, 'diff', '--cached', '--name-only', '-z', *revision, '--', *specs, index=index).stdout
    if changed:
        raise ValueError('명시 제외/runtime 경로가 index에 남았습니다')


def main():
    try:
        result = run(json.loads(sys.stdin.buffer.read().decode('utf-8')))
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + '\n').encode('utf-8'))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        sys.stderr.buffer.write((str(exc) + '\n').encode('utf-8'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
