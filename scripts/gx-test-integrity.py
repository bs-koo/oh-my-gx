#!/usr/bin/env python3
"""단독 GREEN 전후의 테스트·실행 설정을 보존한다. 테스트는 실행하지 않는다."""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys


EXCLUDED = {'.git', '.svn', '.dev', '.humanize', 'node_modules', '.gradle',
            'build', 'dist', '.venv', '__pycache__'}
DEFAULT_TESTS = ['**/*test*', '**/*Test*', '**/*spec*', '**/tests/**', '**/__tests__/**']
RUNNER_CONFIG = {'package.json', 'pyproject.toml', 'pytest.ini', 'tox.ini', 'setup.cfg',
                 'conftest.py', 'build.gradle', 'build.gradle.kts', 'settings.gradle',
                 'settings.gradle.kts', 'pom.xml', 'gradle.properties', 'browserslist'}
_SHARED_CONFIGURATION = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) or
               (pattern.startswith('**/') and fnmatch.fnmatchcase(path, pattern[3:]))
               for pattern in patterns)


def configuration_path(path):
    """공통 테스트 계획과 같은 설정 판정을 사용한다. Python 캐시 파일은 만들지 않는다."""
    global _SHARED_CONFIGURATION
    if _SHARED_CONFIGURATION is None:
        _SHARED_CONFIGURATION = runpy.run_path(str(Path(__file__).with_name('gx-test-plan.py')))[
            'configuration_path']
    return Path(path).name in RUNNER_CONFIG or _SHARED_CONFIGURATION(path)


def scan_error(error):
    # os.walk의 기본 오류 무시는 불완전한 기준선을 정상으로 만들 수 있다.
    raise error


def inside(root, path):
    candidate = Path(path)
    candidate = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('프로젝트 밖 경로는 사용할 수 없습니다')
    return candidate


def config_state(root, config):
    path = inside(root, config or '.claude/config.json')
    if not path.is_file():
        if config is not None:
            raise ValueError('지정한 config 파일이 없습니다')
        return path.relative_to(root).as_posix(), None, {}
    raw = path.read_bytes()
    settings = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(settings, dict) or not isinstance(settings.get('projectTypes', {}), dict):
        raise ValueError('config의 projectTypes는 객체여야 합니다')
    return path.relative_to(root).as_posix(), sha(raw), settings


def inventory(root, settings):
    files, folders_seen = [], []
    for directory, folders, names in os.walk(root, onerror=scan_error):
        folders[:] = sorted(name for name in folders if name not in EXCLUDED)
        for name in folders:
            if Path(directory, name).is_symlink():
                raise ValueError('테스트 목록에서 symlink 디렉터리를 조용히 생략할 수 없습니다')
        folders_seen.append(Path(directory))
        files.extend(Path(directory, name) for name in sorted(names))
    names_by_folder = {}
    for path in files:
        names_by_folder.setdefault(path.parent, []).append(path.name)
    configured = []
    for project in settings.get('projectTypes', {}).values():
        if not isinstance(project, dict):
            raise ValueError('프로젝트 설정은 객체여야 합니다')
        selection = project.get('testSelection', {})
        if not isinstance(selection, dict):
            raise ValueError('testSelection은 객체여야 합니다')
        patterns = selection.get('tests', [])
        if not isinstance(patterns, list) or any(not isinstance(p, str) or not p for p in patterns):
            raise ValueError('testSelection.tests는 비어 있지 않은 glob 문자열 배열이어야 합니다')
        roots = project.get('roots')
        if roots is None:
            markers = project.get('detect', [])
            if not isinstance(markers, list):
                raise ValueError('detect는 배열이어야 합니다')
            roots = [folder.relative_to(root).as_posix() for folder in folders_seen
                     if any(matches(name, markers) for name in names_by_folder.get(folder, []))]
        if not isinstance(roots, list):
            raise ValueError('roots는 배열이어야 합니다')
        if patterns and not roots:
            raise ValueError('추가 테스트 glob의 프로젝트 root를 확인할 수 없습니다')
        for folder in roots:
            target = inside(root, folder)
            if not target.is_dir():
                raise ValueError('등록된 프로젝트 root가 없습니다')
            configured.append((target, patterns))
    result = {}
    for path in files:
        relative = path.relative_to(root).as_posix()
        selected = matches(relative, DEFAULT_TESTS) or configuration_path(relative)
        selected = selected or any(path.is_relative_to(folder) and
                                   matches(path.relative_to(folder).as_posix(), patterns)
                                   for folder, patterns in configured)
        if selected:
            inside(root, path)
            if not path.is_file():
                raise ValueError('테스트 파일을 읽을 수 없습니다: ' + relative)
            result[relative] = sha(path.read_bytes())
    return result


def capture(cwd, baseline, config=None):
    root = Path(cwd).resolve(strict=True)
    target = inside(root, baseline)
    if not target.is_relative_to(root / '.dev'):
        raise ValueError('기준선은 프로젝트 .dev/ 아래에 저장해야 합니다')
    config_path, config_sha, settings = config_state(root, config)
    files = inventory(root, settings)
    if not any(not configuration_path(path) for path in files):
        raise ValueError('보존할 테스트 파일이 없습니다')
    value = {'schema': 1, 'root': str(root), 'config_path': config_path,
             'config_sha256': config_sha, 'files': files}
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    return {'baseline': str(target), 'baseline_sha256': sha(raw), 'files': sorted(files)}


def verify(cwd, baseline, baseline_sha256):
    root = Path(cwd).resolve(strict=True)
    raw = inside(root, baseline).read_bytes()
    if not isinstance(baseline_sha256, str) or sha(raw) != baseline_sha256:
        raise ValueError('baseline 기준선 지문이 변경됐거나 없습니다')
    previous = json.loads(raw.decode('utf-8'))
    if previous.get('schema') != 1 or previous.get('root') != str(root):
        raise ValueError('기준선의 프로젝트가 현재 프로젝트와 다릅니다')
    path = inside(root, previous['config_path'])
    config_sha = sha(path.read_bytes()) if path.is_file() else None
    if config_sha != previous['config_sha256']:
        return {'unchanged': False, 'configuration_changed': True, 'added': [], 'removed': [], 'changed': []}
    _, _, settings = config_state(root, path if path.is_file() else None)
    current = inventory(root, settings)
    old = previous['files']
    added, removed = sorted(current.keys() - old.keys()), sorted(old.keys() - current.keys())
    changed = sorted(path for path in current.keys() & old.keys() if current[path] != old[path])
    return {'unchanged': not (added or removed or changed), 'configuration_changed': False,
            'added': added, 'removed': removed, 'changed': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['capture', 'verify'])
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--config')
    parser.add_argument('--baseline-sha256')
    args = parser.parse_args()
    try:
        if args.action == 'capture':
            result = capture(args.cwd, args.baseline, args.config)
        else:
            result = verify(args.cwd, args.baseline, args.baseline_sha256)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get('unchanged', True) else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'blocked': True, 'reason': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
