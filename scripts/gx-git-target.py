#!/usr/bin/env python3
"""훅이 넘긴 Bash 명령에서 git commit 대상 저장소를 판정한다. 명령은 실행하지 않는다.

stdout에 대상 경로를 한 줄에 하나씩 쓴다. `?` 접두 경로는 커밋 흔적은 있으나 대상을 해석하지 못해
현재 위치로 대신 검사하라는 뜻이다(Git 저장소가 아니면 훅이 건너뛴다). 판정할 수 없으면 원인 한 줄을
stdout에 쓰고 1로 끝난다 — 훅이 그 줄을 deny 사유로 쓴다.
"""
import json
import os
from pathlib import Path
import re
import sys


UNCLOSED = '따옴표·괄호·명령 치환이 닫히지 않아 명령을 해석할 수 없습니다'
SHELLS = {'bash', 'sh', 'zsh', 'dash', 'ksh', 'ash'}
# 실행 파일 앞에 붙어도 실행 위치를 바꾸지 않는 접두어
PREFIXES = {'{', '!', 'command', 'builtin', 'exec', 'time', 'nohup', 'if', 'then', 'elif', 'else', 'while', 'until', 'do'}
SAFE_GIT_FLAGS = {'--no-pager', '-P', '-p', '--paginate', '--literal-pathspecs', '--glob-pathspecs',
                  '--noglob-pathspecs', '--icase-pathspecs', '--no-optional-locks', '--no-replace-objects'}
# 값을 다음 단어로 받는 전역 옵션
GIT_VALUE_OPTIONS = {'--git-dir', '--work-tree', '--namespace', '--super-prefix', '--config-env', '--attr-source'}
ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
GIT_ENV = 'GIT_* 환경변수'
# 해석하지 못한 문자열(python -c 등) 안의 커밋 흔적: git 단어 뒤 같은 줄의 commit 단어
TRACE = re.compile(r'(?<![\w-])git(?:\.exe)?\b[^\n]*?(?<![\w-])commit(?![\w-])')


def lex(text, i=0, nested=False):
    """셸 규칙으로 단어·연산자를 나눈다. nested면 짝이 맞는 ')'에서 멈추고 그 위치를 함께 돌려준다.

    항목: ('w', 값, 리터럴, 치환 명령들) · ('op', 연산자) · ('group', 서브셸 명령) · ('doc', heredoc 본문 줄)
    값은 치환을 원문대로 담고, 리터럴은 치환을 뺀 글자만 담는다(커밋 흔적 검사용).
    """
    items, heredocs, n = [], [], len(text)
    word = None

    def add(chars, literal=True):
        nonlocal word
        word = word or ([], [], [])
        word[0].append(chars)
        if literal:
            word[1].append(chars)

    def flush():
        nonlocal word
        if word is not None:
            items.append(('w', ''.join(word[0]), ''.join(word[1]), word[2]))
        word = None

    def substitute(i):
        # i의 $( 또는 `부터 치환 하나를 단어에 원문으로 붙이고 끝 다음 위치를 돌려준다.
        if text[i] == '`':
            j = i + 1
            while j < n and text[j] != '`':
                j += 2 if text[j] == '\\' else 1
            if j >= n:
                raise ValueError(UNCLOSED)
            inner = text[i + 1:j]
        else:
            j = lex(text, i + 2, True)[1]
            inner = text[i + 2:j]
        add(text[i:j + 1], literal=False)
        word[2].append(inner)
        return j + 1

    while i < n:
        c = text[i]
        if c in ' \t\r':
            flush()
            i += 1
        elif c == '\\':
            if text[i + 1:i + 2] != '\n':
                add(text[i + 1:i + 2])
            i += 2
        elif c == "'":
            j = text.find("'", i + 1)
            if j < 0:
                raise ValueError(UNCLOSED)
            add(text[i + 1:j])
            i = j + 1
        elif c == '"':
            add('')
            i += 1
            while True:
                if i >= n:
                    raise ValueError(UNCLOSED)
                c = text[i]
                if c == '"':
                    i += 1
                    break
                if c == '\\' and text[i + 1:i + 2] in ('$', '`', '"', '\\', '\n'):
                    if text[i + 1] != '\n':
                        add(text[i + 1])
                    i += 2
                elif c == '`' or text.startswith('$(', i):
                    i = substitute(i)
                else:
                    add(c)
                    i += 1
        elif c == '`' or text.startswith('$(', i):
            i = substitute(i)
        elif c == ')' and nested:
            flush()
            return items, i
        elif c == '(':
            flush()
            j = lex(text, i + 1, True)[1]
            items.append(('group', text[i + 1:j]))
            i = j + 1
        elif c == '\n':
            flush()
            items.append(('op', c))
            i = skip_heredocs(text, i + 1, heredocs)
        elif c in ';&|' and not text.startswith('&>', i):
            flush()
            op = text[i:i + 2] if text[i:i + 2] in ('&&', '||', ';;', '|&') else c
            items.append(('op', op))
            i += len(op)
        elif c in '<>&':
            # 리다이렉션. 바로 앞의 fd 숫자는 인자가 아니다. 대상 파일 이름은 인자로 남아도 판정에 영향이 없다.
            if word is not None and ''.join(word[0]).isdigit():
                word = None
            flush()
            if text.startswith('<<<', i):
                i += 3
            elif text.startswith('<<', i):
                strip = text.startswith('<<-', i)
                i, delimiter = read_delimiter(text, i + (3 if strip else 2))
                body = []
                items.append(('doc', body))
                heredocs.append((delimiter, strip, body))
            else:
                j = i + 1 if c == '&' else i
                while j < n and text[j] in '<>':
                    j += 1
                i = j + 1 if c != '&' and j < n and text[j] in '&|' else j
        else:
            add(c)
            i += 1
    if nested:
        raise ValueError(UNCLOSED)
    flush()
    return items, i


def read_delimiter(text, i):
    """heredoc 구분자 단어를 따옴표를 벗겨 읽는다."""
    n = len(text)
    while i < n and text[i] in ' \t':
        i += 1
    start, out = i, []
    while i < n and text[i] not in ' \t\r\n;&|()<>':
        c = text[i]
        if c in '\'"':
            j = text.find(c, i + 1)
            if j < 0:
                raise ValueError(UNCLOSED)
            out.append(text[i + 1:j])
            i = j + 1
        else:
            if c == '\\':
                i += 1
            out.append(text[i:i + 1])
            i += 1
    if i == start:
        raise ValueError('heredoc(<<) 구분자가 없어 명령을 해석할 수 없습니다')
    return i, ''.join(out)


def skip_heredocs(text, i, heredocs):
    """줄바꿈 다음 위치 i부터 대기 중인 heredoc 본문을 각 항목에 담고, 본문 뒤 위치를 돌려준다."""
    for delimiter, strip, body in heredocs:
        while i < len(text):
            end = text.find('\n', i)
            end = len(text) if end < 0 else end
            line, i = text[i:end], end + 1
            mark = line.rstrip('\r')
            if (mark.lstrip('\t') if strip else mark) == delimiter:
                break
            body.append(line)
    heredocs.clear()
    return min(i, len(text))


def name(word):
    """실행 파일 이름 — 경로·.exe·대소문자를 무시한다."""
    base = word.replace('\\', '/').rsplit('/', 1)[-1].lower()
    return base[:-4] if base.endswith('.exe') else base


def directory(value, current):
    """cd·git -C 값을 경로로 바꾼다. 확정할 수 없으면 그 이유(str)를 돌려준다(commit일 때만 차단)."""
    if any(c in value for c in ('$', '`', '\n', '\r', '\x00')):
        return f'동적 경로({value[:60]})는 확정할 수 없습니다'
    if os.name == 'nt' and re.match(r'^/[a-zA-Z]/', value):
        value = value[1] + ':' + value[2:]
    path = Path(value)
    if not path.is_absolute():
        if isinstance(current, str):
            return current
        path = current / path
    path = path.resolve()
    return path if path.is_dir() else f'디렉터리가 없습니다({value[:80]})'


def change_directory(command, args, cwd):
    """cd·pushd 뒤 위치를 돌려준다. 확정할 수 없으면 이유(str)."""
    operands = [a for a in args if a not in ('-L', '-P', '-e', '-@', '--')]
    if command == 'popd' or len(operands) != 1 or operands[0] == '-':
        return f'{command} 이동 위치를 확정할 수 없습니다'
    result = directory(operands[0], cwd)
    return result if isinstance(result, Path) else f'{command} 대상을 확정할 수 없습니다 — {result}'


def git_commit_target(values, start, cwd, override):
    """values[start]에서 실행되는 git이 commit이면 대상 경로를, 아니면 None을 돌려준다."""
    target, i = cwd, start + 1
    while i < len(values):
        value = values[i]
        if value == 'commit':
            if override:
                raise ValueError(f'Git 저장소 위치를 바꾸는 {override}와 결합한 commit은 대상을 확정할 수 없습니다')
            if isinstance(target, str):
                raise ValueError(target)
            return target
        if not value.startswith('-'):
            # log·diff 등 다른 하위 명령의 인자에 commit이라는 문자열이 있어도 커밋이 아니다.
            return None
        if value.startswith(('-C', '-c')):
            if len(value) == 2:
                i += 1
                if i >= len(values):
                    raise ValueError(f'git {value} 값이 없습니다')
            argument = values[i] if len(value) == 2 else value[2:]
            if value.startswith('-C'):
                result = directory(argument, target)
                target = result if isinstance(result, Path) else f'git -C 대상을 확정할 수 없습니다 — {result}'
            elif argument.lower().startswith(('core.worktree', 'include')):
                override = override or '-c ' + argument.split('=', 1)[0]
        elif value not in SAFE_GIT_FLAGS:
            override = override or value.split('=', 1)[0]
            if value in GIT_VALUE_OPTIONS:
                i += 1
        i += 1
    return None


class Scan:
    def __init__(self, origin):
        self.origin = origin
        self.found = {}  # 경로 → 확정 여부

    def add(self, path, exact):
        key = path.as_posix()
        self.found[key] = self.found.get(key, False) or exact

    def run(self, text, cwd, env, depth=0):
        """cwd는 Path 또는 확정하지 못한 이유(str), env는 대상을 바꾸는 GIT_* 환경 표식('' = 없음)."""
        if depth > 8:
            raise ValueError('중첩된 셸 명령이 너무 깊어 해석하지 않습니다')
        segment = []
        for item in lex(text)[0] + [('op', ';')]:
            if item[0] != 'op':
                segment.append(item)
                continue
            if segment:
                cwd, env = self.command(segment, cwd, env, depth)
            segment = []

    def command(self, items, cwd, env, depth):
        # 서브셸·명령 치환은 지금 위치에서 따로 실행된다. 그 안의 cd는 바깥에 남지 않는다.
        for item in items:
            if item[0] == 'group':
                self.run(item[1], cwd, env, depth + 1)
            elif item[0] == 'w':
                for inner in item[3]:
                    self.run(inner, cwd, env, depth + 1)
        words = [item for item in items if item[0] == 'w']
        values = [w[1] for w in words]
        k = 0
        while k < len(values):
            if values[k] in PREFIXES or ASSIGNMENT.match(values[k]):
                k += 1
            elif values[k] == 'rtk':
                k += 2 if values[k + 1:k + 2] == ['proxy'] else 1
            else:
                break
        local = env or (GIT_ENV if any(ASSIGNMENT.match(v) and v.startswith('GIT_') for v in values[:k]) else '')
        if k >= len(values):
            return cwd, local  # 대입만 있는 명령은 이후 명령의 환경에 남을 수 있다
        exe, args = name(values[k]), values[k + 1:]
        if exe in ('cd', 'pushd', 'popd'):
            return change_directory(exe, args, cwd), env
        if exe in ('export', 'declare', 'typeset', 'readonly', 'local'):
            return cwd, env or (GIT_ENV if any(a.startswith('GIT_') for a in args) else '')
        if exe in SHELLS:
            self.shell(args, items, cwd, local, depth)
            return cwd, env
        if exe == 'eval':
            self.run(' '.join(args), cwd, local, depth + 1)
            return cwd, env
        git = k if exe == 'git' else next((j for j in range(k + 1, len(values)) if name(values[j]) == 'git'), None)
        if git is not None:
            override = local or (GIT_ENV if any(ASSIGNMENT.match(v) and v.startswith('GIT_') for v in values[k:git]) else '')
            target = git_commit_target(values, git, cwd, override)
            if target is not None:
                self.add(target, True)
                return cwd, env
            if exe == 'git':
                return cwd, env  # 다른 하위 명령의 인자·heredoc은 데이터다
        # git을 직접 실행하지 않는 명령: 해석하지 못한 문자열·heredoc에 커밋 흔적이 있으면 현재 위치를 대신 검사한다.
        texts = [w[2] for w in words[k:]] + ['\n'.join(item[1]) for item in items if item[0] == 'doc']
        if any(TRACE.search(t) for t in texts):
            self.add(cwd if isinstance(cwd, Path) else self.origin, False)
        return cwd, env

    def shell(self, args, items, cwd, env, depth):
        """bash/sh -c 스크립트나 표준입력 heredoc을 같은 위치의 명령으로 다시 판정한다."""
        j, script, stdin = 0, False, False
        while j < len(args) and args[j][:1] in ('-', '+') and args[j] not in ('-', '--'):
            if args[j] in ('-o', '+o', '-O', '+O'):
                j += 1
            elif not args[j].startswith('--'):
                script = script or 'c' in args[j]
                stdin = stdin or 's' in args[j]
            j += 1
        if j < len(args) and args[j] in ('-', '--'):
            j += 1
        if script:
            if j < len(args):
                self.run(args[j], cwd, env, depth + 1)
        elif stdin or j >= len(args):
            for item in items:
                if item[0] == 'doc':
                    self.run('\n'.join(item[1]), cwd, env, depth + 1)


def targets(payload):
    command = payload['tool_input']['command']
    if not isinstance(command, str):
        raise ValueError('command는 문자열이어야 합니다')
    origin = Path(payload.get('cwd') or os.getcwd()).resolve()
    scan = Scan(origin)
    scan.run(command, origin, '')
    return [('' if exact else '?') + path for path, exact in scan.found.items()]


def main():
    try:
        result = targets(json.loads(sys.stdin.buffer.read().decode('utf-8')))
        sys.stdout.buffer.write(''.join(p + '\n' for p in result).encode('utf-8'))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        sys.stdout.buffer.write((str(exc).replace('\n', ' ') + '\n').encode('utf-8'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
