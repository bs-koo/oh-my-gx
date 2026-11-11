#!/usr/bin/env python3
"""단독 GREEN 전후의 테스트·실행 설정을 보존한다. 테스트는 실행하지 않는다."""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys


# 러너 캐시·빌드 산출물은 테스트 재실행만으로 바뀌므로 지문 대상이 아니다.
EXCLUDED = {'.git', '.svn', '.dev', '.humanize', 'node_modules', '.gradle',
            'build', 'dist', '.venv', 'venv', '__pycache__', 'target', '.pytest_cache',
            'test-results', 'out', 'coverage', '.tox', '.mypy_cache', '.nyc_output'}
# 부분 문자열 일치는 LoggingAspect.java 같은 운영 파일을 오분류하므로 경로 세그먼트·파일명 관례로만 판정한다.
TEST_DIRECTORIES = {'test', 'tests', '__tests__', '__test__', 'spec', 'specs'}
TEST_FILE = re.compile(
    r'(?:test_.+\.py|.+_test\.(?:py|go|rb)|.+_spec\.rb'
    r'|.+(?:Test|Tests|IT|ITCase|TestCase)\.(?:java|kt|groovy|scala|cs)'
    r'|.+\.(?:test|spec|cy)\.[^.]+)')
RUNNER_CONFIG = {'package.json', 'pyproject.toml', 'pytest.ini', 'tox.ini', 'setup.cfg',
                 'conftest.py', 'build.gradle', 'build.gradle.kts', 'settings.gradle',
                 'settings.gradle.kts', 'gradle.properties', 'browserslist', 'pom.xml'}
# 의존성만 담은 파일의 변경은 테스트 변조가 아니라 "사용자 확인 필요"로 따로 보고한다.
# package.json은 의존성 섹션만 따로 지문하고 scripts 등 나머지는 러너 설정으로 계속 보호한다.
DEPENDENCY_FILES = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lock', 'bun.lockb',
                    'requirements.txt', 'poetry.lock', 'uv.lock', 'go.mod', 'go.sum',
                    'Cargo.toml', 'Cargo.lock', 'package.json'}
DEPENDENCY_KEYS = ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies',
                   'bundledDependencies', 'overrides', 'resolutions')
# 앱·빌드 도구 설정은 테스트 러너 설정이 아니다. 공용 판정의 *.config.* 일치에서 뺀다.
APP_CONFIG = re.compile(r'(?:app|next|nuxt|tailwind|postcss|astro|svelte|gatsby|remix|vue|eslint|'
                        r'prettier|stylelint|commitlint|lint-staged)\.config\.[^/]+')
# 공용 판정이 놓치는 `.conf.` 이름의 테스트 러너 설정.
RUNNER_CONF = re.compile(r'(?:karma|protractor|wdio|jest|mocha)\.conf\.[^/]+|\.mocharc(?:\.[^/]+)?')
_SHARED_PLAN = None


def shared(name):
    """공통 테스트 계획(gx-test-plan.py)과 같은 판정 함수를 쓴다."""
    global _SHARED_PLAN
    if _SHARED_PLAN is None:
        _SHARED_PLAN = runpy.run_path(str(Path(__file__).with_name('gx-test-plan.py')))
    return _SHARED_PLAN[name]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_default_test(path):
    parts = path.split('/')
    return (any(part in TEST_DIRECTORIES for part in parts[:-1]) or
            TEST_FILE.fullmatch(parts[-1]) is not None)


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) or
               (pattern.startswith('**/') and fnmatch.fnmatchcase(path, pattern[3:]))
               for pattern in patterns)


def configuration_path(path):
    """공통 테스트 계획과 같은 설정 판정을 쓰되 앱 설정·의존성 전용 파일은 제외한다."""
    name = Path(path).name
    if name in RUNNER_CONFIG or RUNNER_CONF.fullmatch(name):
        return True
    if name in DEPENDENCY_FILES or APP_CONFIG.fullmatch(name):
        return False
    return bool(shared('configuration_path')(path))


def ignored_by_git(root):
    """Git 저장소면 ignore 대상(파일 또는 'dir/')을 돌려준다. 저장소가 아니면 빈 목록."""
    try:
        done = subprocess.run(['git', '-C', str(root), 'ls-files', '-o', '-i', '--exclude-standard',
                               '--directory', '-z'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode != 0:
        return []
    return [item.decode('utf-8', 'surrogateescape') for item in done.stdout.split(b'\0') if item]


def is_ignored(relative, ignored):
    return any(relative == item or (item.endswith('/') and relative.startswith(item))
               for item in ignored)


def split_hashes(path, relative):
    """(러너·테스트 지문, 의존성 지문). 해당 없는 쪽은 None."""
    raw = path.read_bytes()
    name = Path(relative).name
    if name != 'package.json':
        return (None, sha(raw)) if name in DEPENDENCY_FILES else (sha(raw), None)
    try:
        value = json.loads(raw.decode('utf-8-sig'))
    except ValueError:
        return sha(raw), None
    if not isinstance(value, dict):
        return sha(raw), None
    dependencies = {key: value.pop(key) for key in DEPENDENCY_KEYS if key in value}
    return tuple(sha(json.dumps(item, sort_keys=True, ensure_ascii=False).encode('utf-8'))
                 for item in (value, dependencies))


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
    ignored = ignored_by_git(root)
    for directory, folders, names in os.walk(root, onerror=scan_error):
        folders[:] = sorted(name for name in folders if name not in EXCLUDED and not is_ignored(
            Path(directory, name).relative_to(root).as_posix() + '/', ignored))
        for name in folders:
            if Path(directory, name).is_symlink():
                raise ValueError('테스트 목록에서 symlink 디렉터리를 조용히 생략할 수 없습니다')
        folders_seen.append(Path(directory))
        files.extend(Path(directory, name) for name in sorted(names) if not is_ignored(
            Path(directory, name).relative_to(root).as_posix(), ignored))
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
            # 이름 marker는 파일 이름, '/'가 든 marker는 저장소 상대 경로로 찾는다 (gx-test-plan.py와 같다).
            roots = [folder.relative_to(root).as_posix() for folder in folders_seen
                     if any(shared('detected')((folder / name).relative_to(root).as_posix(), markers)
                            for name in names_by_folder.get(folder, []))]
        if not isinstance(roots, list):
            raise ValueError('roots는 배열이어야 합니다')
        if patterns and not roots:
            raise ValueError('추가 테스트 glob의 프로젝트 root를 확인할 수 없습니다')
        for folder in roots:
            target = inside(root, folder)
            if not target.is_dir():
                raise ValueError('등록된 프로젝트 root가 없습니다')
            configured.append((target, patterns))
    result, dependencies = {}, {}
    for path in files:
        relative = path.relative_to(root).as_posix()
        selected = is_default_test(relative) or configuration_path(relative)
        selected = selected or any(path.is_relative_to(folder) and
                                   matches(path.relative_to(folder).as_posix(), patterns)
                                   for folder, patterns in configured)
        if selected:
            inside(root, path)
            if not path.is_file():
                raise ValueError('테스트 파일을 읽을 수 없습니다: ' + relative)
            runner, dependency = split_hashes(path, relative)
            result[relative] = runner
            if dependency is not None:
                dependencies[relative] = dependency
        elif Path(relative).name in DEPENDENCY_FILES:
            inside(root, path)
            if not path.is_file():
                raise ValueError('의존성 파일을 읽을 수 없습니다: ' + relative)
            dependencies[relative] = split_hashes(path, relative)[1]
    return result, dependencies


def capture(cwd, baseline, config=None):
    root = Path(cwd).resolve(strict=True)
    target = inside(root, baseline)
    if not target.is_relative_to(root / '.dev'):
        raise ValueError('기준선은 프로젝트 .dev/ 아래에 저장해야 합니다')
    config_path, config_sha, settings = config_state(root, config)
    files, dependencies = inventory(root, settings)
    if not any(not configuration_path(path) for path in files):
        raise ValueError('보존할 테스트 파일이 없습니다')
    value = {'schema': 1, 'root': str(root), 'config_path': config_path,
             'config_sha256': config_sha, 'files': files, 'dependencies': dependencies}
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
        return {'unchanged': False, 'configuration_changed': True, 'added': [], 'removed': [], 'changed': [],
                'dependency_changed': []}
    _, _, settings = config_state(root, path if path.is_file() else None)
    current, current_dependencies = inventory(root, settings)
    old = previous['files']
    added, removed = sorted(current.keys() - old.keys()), sorted(old.keys() - current.keys())
    changed = sorted(path for path in current.keys() & old.keys() if current[path] != old[path])
    old_dependencies = previous.get('dependencies', {})
    dependency_changed = sorted(path for path in current_dependencies.keys() | old_dependencies.keys()
                                if current_dependencies.get(path) != old_dependencies.get(path))
    return {'unchanged': not (added or removed or changed), 'configuration_changed': False,
            'added': added, 'removed': removed, 'changed': changed,
            'dependency_changed': dependency_changed}


def emit(value):
    # Windows 파이프의 기본 stdout은 cp949라 한글·이모지 경로가 깨지거나 오류가 난다. 항상 UTF-8로 쓴다.
    sys.stdout.buffer.write((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
    sys.stdout.flush()


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
        emit(result)
        if not result.get('unchanged', True):
            return 1
        # 테스트·러너 설정은 그대로지만 의존성이 바뀐 경우: 통과로 오해하지 않도록 별도 코드로 알린다.
        return 3 if result.get('dependency_changed') else 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        emit({'blocked': True, 'reason': str(error)})
        return 2


if __name__ == '__main__':
    sys.exit(main())
