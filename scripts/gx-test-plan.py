#!/usr/bin/env python3
"""Plan affected tests and validate exact, same-run evidence; never execute commands."""
import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

EXCLUDED = {'.git', '.dev', 'node_modules', '.gradle', 'build', 'dist', '.venv', '__pycache__'}
DEPENDENCIES = {'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                'bun.lock', 'bun.lockb', 'build.gradle', 'build.gradle.kts',
                'settings.gradle', 'settings.gradle.kts', 'gradle.properties',
                'pom.xml', 'requirements.txt', 'pyproject.toml', 'poetry.lock',
                'uv.lock', 'go.mod', 'go.sum', 'Cargo.toml', 'Cargo.lock'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def git(root, *args):
    return subprocess.run(['git', '-c', f'safe.directory={root.as_posix()}', *args],
                          cwd=root, check=True, capture_output=True).stdout


def fingerprint(root):
    spec = importlib.util.spec_from_file_location('gx_fingerprint',
                                                Path(__file__).with_name('codex-fingerprint.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fingerprint(root)


def tree_fingerprint(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]+:[0-9a-f]{12}', value):
        raise ValueError('invalid code fingerprint')
    return value.split(':', 1)[1]


def relative(value):
    path = str(value).replace('\\', '/')
    if not path or path.startswith('/') or re.match(r'^[A-Za-z]:', path) or '..' in path.split('/'):
        raise ValueError(f'expected repository-relative path: {value!r}')
    return path.removeprefix('./').rstrip('/') or '.'


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) or
               (pattern.startswith('**/') and fnmatch.fnmatchcase(path, pattern[3:]))
               for pattern in patterns)


def discover(root, types):
    files = []
    for directory, folders, names in os.walk(root):
        folders[:] = sorted(f for f in folders if f not in EXCLUDED and not Path(directory, f).is_symlink())
        files.extend(Path(directory, name).relative_to(root).as_posix() for name in sorted(names))
    projects = []
    for name, settings in types.items():
        explicit = settings.get('roots')
        roots = {relative(path) for path in explicit} if explicit is not None else {
            str(Path(file).parent).replace('\\', '/') for file in files
            if matches(Path(file).name, settings.get('detect', []))}
        for directory in sorted(roots):
            folder = root / directory
            if not folder.is_dir() or not any(matches(file.relative_to(folder).as_posix(),
                                                      settings.get('detect', []))
                                              for file in folder.iterdir() if file.is_file()):
                if explicit is not None:
                    raise ValueError(f'configured project root not detected: {name}:{directory}')
                continue
            projects.append({'type': name, 'cwd': directory, 'settings': settings})
    if not projects:
        raise ValueError('no project types detected; verification is blocked')
    return projects


def under(path, directory):
    return directory == '.' or path == directory or path.startswith(directory + '/')


def local(path, directory):
    return path if directory == '.' else path[len(directory) + 1:]


def configuration_path(path):
    name = Path(path).name
    return (name in DEPENDENCIES or
            name in {'.npmrc', '.yarnrc', '.yarnrc.yml', '.babelrc', '.babelrc.json',
                     '.swcrc', '.browserslistrc', 'pytest.ini', 'setup.cfg', 'tox.ini'} or
            bool(re.fullmatch(r'(?:tsconfig|jsconfig)(?:\.[^/]+)?\.json', name)) or
            bool(re.search(r'(^|/)([^/]*[.]config[.][^/]+|conftest[.]py|gradlew(?:[.]bat)?)$', path)))


def changed_paths(root, base):
    # Includes committed branch work, index/worktree edits, deletions and untracked files.
    value = git(root, 'diff', '--name-only', '--no-renames', '-z', f'{base}...HEAD')
    value += git(root, 'diff', '--name-only', '--no-renames', '-z', 'HEAD')
    value += git(root, 'ls-files', '--others', '--exclude-standard', '-z')
    return sorted({relative(p.decode('utf-8')) for p in value.split(b'\0') if p})


def build_command(settings):
    if settings.get('buildOnly'):
        return settings['buildOnly']
    command = settings.get('build', '').strip()
    if not command:
        return None
    # Only this exact known command is safely converted. Custom builds must declare buildOnly.
    if command in ('./gradlew build', 'gradlew build', 'gradlew.bat build'):
        return command + ' -x test testClasses'
    raise ValueError('buildOnly required for custom build command (test-free execution must be explicit)')


def focused(args):
    """Return a current-task file command without Git, execution or a full fallback."""
    root = args.cwd.resolve()
    config = read_json(args.config or root / '.claude/config.json')
    types = config.get('projectTypes', {}) if isinstance(config, dict) else {}
    name, separator, raw_directory = args.project.partition(':')
    if not separator or not isinstance(types, dict) or name not in types:
        raise ValueError('focused project must identify a configured TYPE:RELROOT')
    directory = relative(raw_directory)
    folder = (root / directory).resolve()
    settings = types[name]
    if not isinstance(settings, dict) or not folder.is_dir() or not folder.is_relative_to(root):
        raise ValueError('focused project root is missing or outside the project')
    if settings.get('roots') is not None and directory not in {
            relative(path) for path in settings['roots']}:
        raise ValueError('focused project is outside configured roots')
    if not any(matches(path.name, settings.get('detect', []))
               for path in folder.iterdir() if path.is_file()):
        raise ValueError('focused project marker was not detected')
    tests = read_json(args.tests_file)
    if not isinstance(tests, list) or not tests or any(not isinstance(p, str) or not p for p in tests):
        raise ValueError('focused tests must be a nonempty repository-relative path array')
    files = []
    for value in tests:
        path = relative(value)
        target = (root / path).resolve()
        if (not under(path, directory) or not target.is_relative_to(folder) or
                not target.is_file()):
            raise ValueError(f'focused test is missing or outside selected project: {value}')
        files.append(local(path, directory))
    files = sorted(set(files))
    # A root-level filename beginning with '-' must remain an operand, not a runner flag.
    operands = shlex.join('./' + path if path.startswith('-') else path for path in files)
    result = {'supported': True, 'project': f'{name}:{directory}', 'cwd': directory, 'scope': files}

    def unsupported(reason):
        return {**result, 'supported': False, 'requires': 'focusedTest', 'reason': reason}

    template = settings.get('focusedTest')
    if template:
        if not isinstance(template, str):
            raise ValueError('focusedTest must be a command template string')
        if '{files}' in template and '{pattern}' not in template:
            command = template.replace('{files}', operands)
        elif ('--tests {pattern}' in template and '{files}' not in template and
              all(path.endswith(('.java', '.kt')) for path in files)):
            patterns = ' '.join('--tests ' + shlex.quote(Path(path).stem) for path in files)
            command = template.replace('--tests {pattern}', patterns)
        else:
            return unsupported('configured focusedTest needs {files} or Java/Kotlin --tests {pattern}')
        return {**result, 'command': command, 'runner': 'configured'}

    base = settings.get('test', '')
    if base in ('pytest', 'python -m pytest', 'python3 -m pytest'):
        return {**result, 'command': base + ' ' + operands, 'runner': 'pytest'}
    package_path = folder / 'package.json'
    if base == 'npm test' and package_path.is_file():
        package = read_json(package_path)
        scripts = package.get('scripts', {}) if isinstance(package, dict) else {}
        script = scripts.get('test', '') if isinstance(scripts, dict) else ''
        known = {'vitest': 'npm test -- --run', 'vitest run': 'npm test --',
                 'jest': 'npm test -- --runInBand --runTestsByPath', 'node --test': 'npm test --'}
        if isinstance(script, str) and script.strip() in known:
            script = script.strip()
            return {**result, 'command': known[script] + ' ' + operands, 'runner': script}
    return unsupported('runner has no known current-file invocation; configure focusedTest explicitly')


def select_tests(root, project, paths, task_tests, global_reason, ownership):
    settings, directory = project['settings'], project['cwd']
    policy = settings.get('testSelection', {})
    changed = sorted({local(path, directory) for path in paths if under(path, directory)})
    required = {local(path, directory) for path in task_tests if under(path, directory)}
    full_reason = global_reason
    selected, related = set(required), set()
    mappings = list(policy.get('mappings', []))
    for rule in ownership:
        sources = [local(p, directory) for p in rule['sources'] if under(p, directory)]
        owned_tests = [local(p, directory) for p in rule['tests'] if under(p, directory)]
        if sources and owned_tests and len(owned_tests) == len(rule['tests']):
            mappings.append({'sources': sources, 'tests': owned_tests})
    for path in changed:
        if configuration_path(path) or matches(path, policy.get('crosscutting', [])):
            full_reason = 'dependency/config/crosscutting change'
            continue
        if matches(path, policy.get('ignore', [])):
            continue
        mapped = [rule for rule in mappings if matches(path, rule['sources'])]
        if mapped and any(rule.get('tests') for rule in mapped):
            selected.update(test for rule in mapped for test in rule['tests'])
        elif matches(path, policy.get('tests', ['**/test_*.py', '**/*_test.py', '**/*.test.*',
                                               '**/*.spec.*', '**/*Test.java', '**/*Tests.java',
                                               '**/*Test.kt', '**/*Tests.kt'])):
            selected.add(path)
        else:
            related.add(path)
    if any(not (root / directory / path).is_file() for path in selected):
        full_reason = 'mapped/required test missing or deleted'
    if related and not full_reason:
        if settings.get('affectedTest'):
            template = settings['affectedTest']
        else:
            package = root / directory / 'package.json'
            script = read_json(package).get('scripts', {}).get('test', '') if package.is_file() else ''
            # Only a simple recognized script has known forwarding semantics.
            if selected:
                # A related-source invocation cannot certify separately required tests.
                template = None
            elif re.fullmatch(r'vitest(?:\s+run)?', script.strip()):
                template = 'npm test -- related --run {files}'
            elif re.fullmatch(r'jest', script.strip()):
                template = 'npm test -- --runInBand --findRelatedTests {files}'
            else:
                template = None
        if template and '{files}' in template:
            files = sorted(related | selected)
            return template.replace('{files}', shlex.join(files)), files, 'affected runner'
        full_reason = 'unmapped changed file or unsupported affected runner'
    if not full_reason and not changed and not required and policy.get('independent') is True:
        return None, [], 'unaffected independent project'
    if full_reason or not changed and not required:
        return settings.get('test'), ['*'], full_reason or 'unaffected detected project; conservative full coverage'
    if selected:
        template = settings.get('focusedTest', '')
        files = sorted(selected)
        if '{files}' in template:
            return template.replace('{files}', shlex.join(files)), files, 'mapped/changed tests'
        if '--tests {pattern}' in template and all(path.endswith(('.java', '.kt')) for path in files):
            patterns = ' '.join('--tests ' + shlex.quote(Path(path).stem) for path in files)
            return template.replace('--tests {pattern}', patterns), files, 'mapped/changed tests'
        return settings.get('test'), ['*'], 'focused template unsupported'
    # Explicit ignore is the only path to an empty selection, and is visible in the plan.
    return None, [], 'all changes explicitly ignored by project policy'


def plan(args):
    root = args.cwd.resolve()
    config_path = (args.config or root / '.claude/config.json').resolve()
    config = read_json(config_path)
    projects = discover(root, config.get('projectTypes', {}))
    paths = sorted({relative(p) for p in (changed_paths(root, args.base) +
                                         (read_json(args.changed_file) if args.changed_file else []))
                    if not relative(p).startswith('.dev/')})
    tests = sorted({relative(p) for p in read_json(args.tests_file)}) if args.tests_file else []
    ownership = read_json(args.ownership_file) if args.ownership_file else []
    for rule in ownership:
        rule['sources'] = [relative(p) for p in rule['sources']]
        rule['tests'] = [relative(p) for p in rule['tests']]
    unknown = [p for p in paths + tests if not any(under(p, x['cwd']) for x in projects)]
    global_reason = 'unowned changed/test path: ' + ', '.join(unknown) if unknown else None
    if '.claude/config.json' in paths or any(configuration_path(p) and
                                          not any(p == x['cwd'] + '/' + Path(p).name for x in projects)
                                          for p in paths):
        global_reason = 'shared dependency or validation configuration changed'
    if args.full:
        global_reason = 'explicit full regression requested'
    entries, skipped = [], []
    for project in projects:
        settings = project['settings']
        command, scope, reason = select_tests(root, project, paths, tests, global_reason, ownership)
        if command is None and scope:
            raise ValueError(f"test command missing: {project['type']}:{project['cwd']}")
        if command is None:
            skipped.append({'project': project['cwd'], 'reason': reason})
            continue
        for kind, cmd, selected, why in [('test', command, scope, reason),
                                         ('build', build_command(settings), ['build'], 'explicit test-free build')]:
            if not cmd:
                continue
            if kind == 'test' and args.rerun_tests:
                words = shlex.split(cmd)
                if (words and words[0] in ('./gradlew', 'gradlew', 'gradlew.bat') and
                        any(word.rsplit(':', 1)[-1] == 'test' for word in words[1:]) and
                        '--rerun-tasks' not in words):
                    cmd += ' --rerun-tasks'
            entry = {'project': f"{project['type']}:{project['cwd']}", 'type': project['type'],
                     'cwd': project['cwd'], 'kind': kind, 'command': cmd, 'scope': selected, 'reason': why}
            entry['id'] = digest({k: v for k, v in entry.items() if k != 'reason'})[:16]
            entries.append(entry)
    return {'version': 1, 'runId': args.run_id, 'root': str(root), 'fingerprint': fingerprint(root),
            'configPath': str(config_path), 'configHash': digest(config), 'base': args.base,
            'changed': paths, 'rerunTests': args.rerun_tests, 'entries': entries, 'skipped': skipped}


def identity(root, value, entry_id):
    if str(root) != value['root'] or tree_fingerprint(fingerprint(root)) != tree_fingerprint(value['fingerprint']):
        raise ValueError('code fingerprint changed or project root differs; regenerate plan')
    if digest(read_json(value['configPath'])) != value['configHash']:
        raise ValueError('validation configuration changed; regenerate plan')
    entry = next(e for e in value['entries'] if e['id'] == entry_id)
    return {'runId': value['runId'], 'root': value['root'], 'fingerprint': tree_fingerprint(value['fingerprint']),
            'configHash': value['configHash'], 'entry': {k: entry[k] for k in
             ('project', 'type', 'cwd', 'kind', 'command', 'scope')}}, entry


def proof_action(args):
    root, value = args.cwd.resolve(), read_json(args.plan)
    proof_path = args.proof.resolve()
    if args.action == 'record':
        # Overwrite a previous pass before validating, so failed/zero/stale attempts invalidate it.
        proof_path.parent.mkdir(parents=True, exist_ok=True)
        proof_path.write_text('{"passed": false}\n', encoding='utf-8')
    key, entry = identity(root, value, args.entry)
    if args.action == 'reuse':
        proof = read_json(proof_path)
        if not proof.get('passed') or proof.get('identity') != key:
            raise ValueError('no matching successful evidence in this run')
        log = Path(proof['log'])
        if hashlib.sha256(log.read_bytes()).hexdigest() != proof['logHash']:
            raise ValueError('evidence log changed')
        return {'reusable': True, 'entry': args.entry}
    if args.exit_code != 0 or args.failures != 0 or (entry['kind'] == 'test' and args.tests < 1):
        raise ValueError('failed/zero/unconfirmed test execution cannot be reused')
    log = args.log.resolve()
    proof = {'passed': True, 'identity': key, 'exitCode': args.exit_code,
             'tests': args.tests, 'failures': args.failures, 'log': str(log),
             'logHash': hashlib.sha256(log.read_bytes()).hexdigest(),
             'recordedAt': datetime.now(timezone.utc).isoformat()}
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'recorded': True, 'entry': args.entry}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    task_focused = subs.add_parser('focused')
    task_focused.add_argument('--project', required=True)
    task_focused.add_argument('--tests-file', required=True, type=Path)
    task_focused.add_argument('--config', type=Path)
    planning = subs.add_parser('plan')
    planning.add_argument('--base', required=True)
    planning.add_argument('--run-id', required=True)
    planning.add_argument('--config', type=Path)
    planning.add_argument('--changed-file', type=Path)
    planning.add_argument('--tests-file', type=Path)
    planning.add_argument('--ownership-file', type=Path)
    planning.add_argument('--full', action='store_true')
    planning.add_argument('--rerun-tests', action='store_true')
    for name in ('record', 'reuse'):
        sub = subs.add_parser(name)
        sub.add_argument('--plan', required=True, type=Path)
        sub.add_argument('--entry', required=True)
        sub.add_argument('--proof', required=True, type=Path)
        if name == 'record':
            sub.add_argument('--log', required=True, type=Path)
            sub.add_argument('--exit-code', required=True, type=int)
            sub.add_argument('--tests', type=int, default=-1)
            sub.add_argument('--failures', type=int, default=0)
    for sub in subs.choices.values():
        sub.add_argument('--cwd', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'focused':
            result = focused(args)
        else:
            result = plan(args) if args.action == 'plan' else proof_action(args)
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError) as exc:
        sys.stderr.buffer.write(f'test plan blocked: {exc}\n'.encode('utf-8'))
        return 1
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    return 2 if args.action == 'focused' and not result['supported'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
