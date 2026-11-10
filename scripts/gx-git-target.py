#!/usr/bin/env python3
"""훅의 제한된 Git 명령 문법에서 commit 대상 cwd를 선택한다. 명령은 실행하지 않는다."""
import json
import os
from pathlib import Path
import re
import shlex
import sys


def directory(value, current):
    if any(c in value for c in ('$','`','\n','\r','\x00')):
        raise ValueError('동적 Git 대상 경로를 해석할 수 없습니다')
    if os.name == 'nt' and re.match(r'^/[a-zA-Z]/', value):
        value = value[1] + ':' + value[2:]
    path = Path(value)
    path = (path if path.is_absolute() else current / path).resolve()
    if not path.is_dir():
        raise ValueError('Git 대상 디렉터리가 없습니다')
    return path


def targets(payload):
    command = payload['tool_input']['command']
    if not isinstance(command, str):
        raise ValueError('command는 문자열이어야 합니다')
    cwd = Path(payload.get('cwd') or os.getcwd()).resolve()
    lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|()<>\n')
    # 따옴표 밖의 newline은 명령 경계다. 인용된 메시지 안 newline은 한 토큰으로 유지한다.
    lexer.whitespace = ' \t\r'
    lexer.whitespace_split = True
    lexer.commenters = ''
    parts, segment = [], []
    for token in lexer:
        if token and all(c in ';&|\n' for c in token):
            parts.append(segment)
            segment = []
        else:
            segment.append(token)
    parts.append(segment)
    found = []
    for tokens in parts:
        if 'commit' not in tokens:
            continue
        # cd/subshell/환경 경로 재지정은 현재 제한된 파서로 안전하게 복원하지 않는다.
        if any(p and p[0] in ('cd', 'pushd', 'popd') for p in parts):
            raise ValueError('디렉터리 변경과 결합한 commit 대상은 명시적인 git -C로 바꿔주세요')
        if not tokens or tokens[0] in ('echo', 'printf', 'cat'):
            continue
        start = 1 if tokens[0] in ('rtk', 'command') else 0
        while start < len(tokens) and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', tokens[start]):
            if tokens[start].startswith('GIT_'):
                raise ValueError('Git 환경 경로 재지정은 지원하지 않습니다')
            start += 1
        if start >= len(tokens) or Path(tokens[start]).name not in ('git', 'git.exe'):
            raise ValueError('commit 명령의 Git 실행 대상을 확정할 수 없습니다')
        target = cwd
        index = start + 1
        while index < len(tokens):
            token = tokens[index]
            if token == 'commit':
                found.append(target.as_posix())
                break
            if not token.startswith('-'):
                # log/diff 등의 인자에 commit이라는 문자열이 있어도 실제 commit이 아니다.
                break
            if token in ('-C', '-c'):
                index += 1
                if index >= len(tokens):
                    raise ValueError('Git 전역 옵션 값이 없습니다')
                if token == '-C':
                    target = directory(tokens[index], target)
                elif tokens[index].lower().startswith(('core.worktree=', 'include.')):
                    raise ValueError('Git 대상에 영향을 주는 config는 지원하지 않습니다')
            elif token.startswith('-C'):
                target = directory(token[2:], target)
            elif token.startswith('-c') and len(token) > 2:
                if token[2:].lower().startswith(('core.worktree=', 'include.')):
                    raise ValueError('Git 대상에 영향을 주는 config는 지원하지 않습니다')
            elif token not in ('--no-pager', '--literal-pathspecs', '--no-optional-locks', '--no-replace-objects'):
                raise ValueError('지원하지 않는 Git 전역 옵션/셸 조합입니다')
            index += 1
    return list(dict.fromkeys(found))


def main():
    try:
        result = targets(json.loads(sys.stdin.buffer.read().decode('utf-8')))
        sys.stdout.buffer.write((''.join(p + '\n' for p in result)).encode('utf-8'))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        sys.stderr.buffer.write((str(exc) + '\n').encode('utf-8'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
