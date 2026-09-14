# Codex 훅·커밋 보호 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex의 훅 매칭·판정·Windows 실행·의사결정 기록을 복구하고 훅과 독립적인 커밋 가드를 제공한다.

**Architecture:** Claude의 Bash 가드는 유지한다. Python 경계 어댑터가 Codex 판정으로 변환하고 Windows 프로세스 실행을 정규화한다. 설치 보조 도구는 JSON을 구조적으로 병합한다.

**Tech Stack:** Python 3.10+ unittest/subprocess/json, Bash, Windows cmd, Markdown.

**Spec:** `docs/superpowers/specs/2026-09-14-codex-native-compat-design.md` A1~A3.

## Global Constraints

- 지원 검증 기준은 Codex CLI 0.154.0이다. 더 낮은 버전은 호환을 보증하지 않는다.
- Windows PowerShell + Git Bash, Linux Bash를 필수 검증 환경으로 둔다. macOS는 추가 검증 전 미측정으로 표시한다.
- Python 3.10 이상 표준 라이브러리와 기존 Bash/Git/Node를 사용한다. 새 런타임 패키지는 추가하지 않는다.
- 전역 설치·훅 신뢰·모델·권한을 진단 명령에서 변경하지 않는다. 신뢰 우회·샌드박스 해제 플래그를 러너에 추가하지 않는다.
- 구현 브랜치에서 작업하고 기존 미커밋 변경을 임의로 스테이징·되돌리기·삭제하지 않는다. 커밋은 gx-commit 절차를 따른다.
- 문서와 커밋 메시지는 한국어로 작성한다. 이모지는 새로 추가하지 않는다.

## Task 1: Codex 판정 어댑터와 canonical matcher

**Files:**
- Create: `.claude/hooks/codex_hook.py`
- Create: `tests/codex_test_support.py`, `tests/test_codex_hooks.py`
- Modify: `hooks.json` PreToolUse/PostToolUse
- Test: `scripts/hook-tests.sh` 기존 Claude 회귀 유지

**Interfaces:**
- Consumes: 기존 Bash 가드 stdin JSON, stdout 빈 문자열 또는 `hookSpecificOutput`.
- Produces: `run_guard(payload: dict, *, bash: str | None = None) -> dict | None`; 반환 None은 통과, dict는 JSON 출력. `main`의 guard 모드는 항상 JSON 또는 빈 stdout과 exit 0을 사용한다.

- [x] **Step 1: 실패 테스트를 작성한다.** 테스트 모듈 로딩 헬퍼를 다음 내용으로 만든다.

```python
# tests/codex_test_support.py
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

`tests/test_codex_hooks.py`의 최초 테스트:

```python
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from codex_test_support import load
hook = load('gx_codex_hook', '.claude/hooks/codex_hook.py')

class GuardTests(unittest.TestCase):
    def test_ask_becomes_deny(self):
        answer = {'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'ask',
            'permissionDecisionReason': 'verify pending'}}
        with tempfile.TemporaryDirectory() as cwd:
            payload = {'cwd': cwd, 'tool_name': 'Bash',
                       'tool_input': {'command': 'git commit -m test'}}
            result = subprocess.CompletedProcess([], 0, json.dumps(answer), '')
            with patch.object(hook.subprocess, 'run', return_value=result) as run:
                out = hook.run_guard(payload, bash='bash')
            self.assertEqual(out['hookSpecificOutput']['permissionDecision'], 'deny')
            self.assertEqual(run.call_args.kwargs['cwd'], cwd)

    def test_guard_crash_denies(self):
        result = subprocess.CompletedProcess([], 127, '', 'missing script')
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook.subprocess, 'run', return_value=result):
                out = hook.run_guard({'cwd': cwd}, bash='bash')
            self.assertEqual(out['hookSpecificOutput']['permissionDecision'], 'deny')
```

- [x] **Step 2: RED를 확인한다.** `python -m unittest discover -s tests -p 'test_codex_hooks.py' -v`. 최초 기대 결과는 새 어댑터 부재로 인한 import 실패다. 구현 후에는 각각의 판정 assertion으로 동작을 검증한다.

- [x] **Step 3: 어댑터를 구현한다.** 아래 guard 분기와 CLI를 추가한다.

```python
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
def deny(reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny', 'permissionDecisionReason': reason}}

def find_bash():
    candidates = [shutil.which('bash')]
    if os.name == 'nt':
        candidates += [str(Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
                           / 'Git/bin/bash.exe')]
        candidates += [str(Path(os.environ.get('LOCALAPPDATA', '.'))
                           / 'Programs/Git/bin/bash.exe')]
    return next((p for p in candidates if p and Path(p).is_file()), None)

def run_guard(payload, *, bash=None):
    executable = bash or find_bash()
    if not executable:
        return deny('GX 가드를 실행할 Bash를 찾지 못했습니다.')
    cwd = payload.get('cwd')
    if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        return deny('GX 훅의 작업 경로가 유효하지 않습니다.')
    try:
        proc = subprocess.run([executable, str(HERE / 'pre-tool-guard.sh')],
            input=json.dumps(payload), text=True, encoding='utf-8',
            capture_output=True, cwd=cwd, timeout=30)
        if proc.returncode:
            return deny('GX 가드 실행 실패: ' + proc.stderr[-500:])
        if not proc.stdout.strip():
            return None
        result = json.loads(proc.stdout)
        output = result['hookSpecificOutput']
        if output['permissionDecision'] == 'ask':
            output['permissionDecision'] = 'deny'
        if output['permissionDecision'] not in ('allow', 'deny'):
            return deny('GX 가드가 지원하지 않는 판정을 반환했습니다.')
        return result
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        return deny('GX 가드 오류: ' + str(exc))

def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else ''
    if mode not in ('guard', 'capture'):
        print('사용: codex_hook.py guard|capture', file=sys.stderr)
        return 2
    if mode == 'capture':
        proc = subprocess.run([sys.executable, str(HERE / 'capture_decision.py')])
        return proc.returncode
    try:
        payload = json.loads(sys.stdin.buffer.read().decode('utf-8'))
        result = run_guard(payload)
    except (ValueError, AttributeError, UnicodeError) as exc:
        result = deny('GX 훅 입력 오류: ' + str(exc))
    if result is not None:
        print(json.dumps(result, ensure_ascii=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
```

`hooks.json`의 두 command를 아래 형태로 교체한다. PostToolUse는 matcher `AskUserQuestion|request_user_input`, 마지막 인자 `capture`를 사용한다. `shell: bash`는 제거한다.

```json
{
  "matcher": "^Bash$",
  "hooks": [{
    "type": "command",
    "command": "python3 \"${PLUGIN_ROOT}/.claude/hooks/codex_hook.py\" guard",
    "commandWindows": "python \"${PLUGIN_ROOT}/.claude/hooks/codex_hook.py\" guard",
    "timeout": 35
  }]
}
```

- [x] **Step 4: GREEN과 경계 케이스를 확인한다.** 같은 unittest에 empty stdout→None, deny 유지, invalid JSON/nonzero/timeout→deny, 프로세스 cwd를 각각 추가한다. 모든 오류는 `CompletedProcess` 또는 `TimeoutExpired`로 주입해 실제 판단을 검사한다. `bash scripts/hook-tests.sh`로 Claude의 기존 ask/deny 회귀도 통과시킨다.
- [ ] **Step 5: 이 태스크의 변경 파일만 gx-commit 절차로 커밋한다.** 메시지: `fix: Codex 훅 판정과 매칭을 실제 규약에 맞춘다`.

## Task 2: 공백 경로·설치 병합·Windows 종료코드

**Files:**
- Create: `scripts/codex-install-hooks.py`, `tests/test_codex_install.py`
- Modify: `scripts/codex-install-hooks.sh`, `.claude/hooks/run-hook.cmd`
- Modify: `scripts/hook-tests.sh` installer 섹션

**Interfaces:**
- Consumes: Task 1의 `codex_hook.py guard|capture`.
- Produces: `render(root: Path, python: str) -> dict`, `merge(existing: dict, generated: dict) -> dict`; CLI 기본 stdout, `--write PATH`는 기존 hooks 보존 후 기록, `--cmd`는 Windows override를 포함하는 호환 옵션으로 수용.

- [x] **Step 1: 실패 테스트를 만든다.** 아래를 `tests/test_codex_install.py`에 넣는다.

```python
import json
from pathlib import Path
import unittest
from codex_test_support import load
installer = load('gx_install', 'scripts/codex-install-hooks.py')
class InstallTests(unittest.TestCase):
    def test_space_path_is_quoted(self):
        value = installer.render(Path('D:/plugin with spaces'), 'C:/Python/python.exe')
        item = value['hooks']['PreToolUse'][0]
        self.assertEqual(item['matcher'], '^Bash$')
        self.assertIn('"D:/plugin with spaces/.claude/hooks/codex_hook.py"',
                      item['hooks'][0]['commandWindows'])
        json.loads(json.dumps(value))

    def test_other_hooks_survive(self):
        existing = {'description': 'keep', 'hooks': {'Stop': [
            {'hooks': [{'type': 'command', 'command': 'echo external'}]}]}}
        generated = installer.render(Path('/tmp/plugin'), '/usr/bin/python3')
        result = installer.merge(existing, generated)
        self.assertEqual(result['hooks']['Stop'], existing['hooks']['Stop'])
        self.assertEqual(installer.merge(result, generated), result)
```

- [x] **Step 2: RED를 확인한다.** `python -m unittest discover -s tests -p 'test_codex_install.py' -v`.
- [x] **Step 3: 렌더러와 병합을 구현한다.** 생성된 그룹과 완전히 같은 등록만 중복 제거한다. 다른 경로의 오래된 GX hook은 자동 삭제하지 않고 중복 실행 가능성을 경고한다.

```python
from copy import deepcopy
from pathlib import Path
import shlex
import subprocess

def render(root, python):
    script = (root / '.claude/hooks/codex_hook.py').as_posix()
    events = {}
    for event, matcher, mode in (
        ('PreToolUse', '^Bash$', 'guard'),
        ('PostToolUse', 'AskUserQuestion|request_user_input', 'capture')):
        posix = shlex.join([python, script, mode])
        windows = subprocess.list2cmdline([python, script, mode])
        events[event] = [{'matcher': matcher, 'hooks': [{'type': 'command',
            'command': posix, 'commandWindows': windows, 'timeout': 35}]}]
    return {'hooks': events}

def merge(existing, generated):
    result = deepcopy(existing)
    for event, groups in generated['hooks'].items():
        target = result.setdefault('hooks', {}).setdefault(event, [])
        for group in groups:
            if group not in target:
                target.append(group)
    return result
```

CLI는 `argparse`로 `--write`/`--cmd`를 읽고 `Path(__file__).resolve().parents[1]`과 `sys.executable`을 render에 전달한다. `--write` 때 기존 JSON 파싱이 실패하면 쓰지 않고 exit 2로 끝낸다. 백업명은 `PATH.bak-YYYYMMDDTHHMMSSffffff`이며 `open('xb')`로 충돌을 거부한다. 새 내용은 같은 디렉토리의 tempfile에 UTF-8로 쓰고 `os.replace`한다. 생성 전에 Task 1 어댑터에 cwd와 command를 포함한 fixture를 전달해 실제 프로세스와 JSON 판정을 확인한다.

```python
import json
import sys
script = Path(__file__).resolve().parents[1] / '.claude/hooks/codex_hook.py'
probe = subprocess.run([sys.executable, str(script), 'guard'],
    input=json.dumps({'cwd': str(Path.cwd()), 'tool_name': 'Bash',
                      'tool_input': {'command': 'git push --force origin main'}}),
    text=True, encoding='utf-8', capture_output=True, timeout=35)
assert probe.returncode == 0
assert json.loads(probe.stdout)['hookSpecificOutput']['permissionDecision'] == 'deny'
```

무해한 git status payload에도 같은 실행을 수행하여 빈 출력인지 확인한다. 여기서 command는 가드에 전달할 데이터이며 실제 Git 명령으로 실행하지 않는다.

`codex-install-hooks.sh`는 Python 실행을 확인하고 위 CLI에 위임한다.

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for candidate in python3 python; do
  if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3,10))' >/dev/null 2>&1; then
    exec "$candidate" "$SCRIPT_DIR/codex-install-hooks.py" "$@"
  fi
done
echo 'Python 3.10 이상이 필요합니다.' >&2
exit 2
```

`run-hook.cmd`는 Bash 탐색과 실행을 분리해 블록 밖에서 종료코드를 반환한다. 지연 확장은 사용하지 않아 `!`를 포함한 경로를 보존한다. 다음 내용으로 교체한다.

```bat
@echo off
setlocal DisableDelayedExpansion
set "HOOK=%~1"
if not defined HOOK exit /b 2
set "BASH_EXE="
for /f "delims=" %%B in ('where bash 2^>nul') do if not defined BASH_EXE set "BASH_EXE=%%B"
if defined BASH_EXE goto run
if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
if defined BASH_EXE goto run
if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if not defined BASH_EXE exit /b 1
:run
"%BASH_EXE%" "%HOOK%"
exit /b %ERRORLEVEL%
```

- [x] **Step 4: 생성된 명령의 실행 결과를 검사한다.** 임시 `plugin with spaces`에 필요한 hook 파일을 복사하고 render가 만든 Windows/POSIX 명령을 실제로 실행한다. rc 0과 deny JSON을 확인한다. Windows에서는 missing script의 nonzero, `!` 경로, 백업 충돌, 깨진 기존 JSON의 비변경도 검사한다. Windows skip은 Windows 합격이 아니다.
- [ ] **Step 5: gx-commit.** `fix: 훅 설치의 경로 인용과 실패 전파를 보장한다`.

## Task 3: 질문 id·복수 답변·수동 기록 정규화

**Files:**
- Modify: `.claude/hooks/capture_decision.py` render/실패 보고
- Create: `tests/test_codex_decisions.py`
- Modify: `.claude/rules/harness-codex.md` 의사결정 기록

**Interfaces:**
- Consumes: Claude `answers[question] = str`, Codex `answers[id] = {answers: list[str]}`.
- Produces: `answer_rows(payload: dict) -> list[tuple[str, dict, list[str], str | None]]`; 기존 `render(payload) -> str`와 저장 경로 유지.

- [x] **Step 1: 다음 테스트를 작성한다.**

```python
import unittest
from codex_test_support import load
capture = load('gx_capture', '.claude/hooks/capture_decision.py')
class DecisionTests(unittest.TestCase):
    def test_codex_question_is_not_replaced_by_id(self):
        payload = {'tool_input': {'questions': [{'id': 'q1', 'header': '방식',
            'question': '어떤 방식을 사용할까요?', 'options': [
                {'label': 'A', 'description': '첫 방법'},
                {'label': 'B', 'description': '둘째 방법'}]}]},
            'tool_response': {'answers': {'q1': {'answers': ['B']}}}}
        text = capture.render(payload)
        self.assertIn('어떤 방식을 사용할까요?', text)
        self.assertIn('둘째 방법', text)
        self.assertIn('**→** B', text)
        self.assertNotIn("{'answers':", text)
```

- [x] **Step 2: RED를 확인한다.** `python -m unittest discover -s tests -p 'test_codex_decisions.py' -v`; 질문 본문과 선택 표시 assertion 실패가 기대값이다.
- [x] **Step 3: 정규화 후 기존 렌더러를 연결한다.**

```python
def answer_rows(payload):
    questions = payload.get('tool_input', {}).get('questions') or []
    by_key = {}
    for q in questions:
        for key in (q.get('id'), q.get('question')):
            if key:
                by_key[key] = q
    response = payload.get('tool_response') or {}
    rows = []
    for key, answer in (response.get('answers') or {}).items():
        meta = by_key.get(key, {})
        values = answer.get('answers', []) if isinstance(answer, dict) else answer
        if not isinstance(values, list):
            values = [values]
        values = [str(v) for v in values if v is not None]
        if values:
            note = ((response.get('annotations') or {}).get(key) or {}).get('notes')
            rows.append((meta.get('question', key), meta, values, note))
    return rows
```

`render`의 answers 루프를 `for question, meta, values, note in answer_rows(payload):`로 교체한다. 선택 판정은 `opt.get('label') in values`, 출력 답변은 `', '.join(values)`를 쓴다. 선택지에 없는 값만 `(직접 입력)`으로 표시한다. 현재 시각·header·append 경로는 보존한다. 저장 실패 except에서 stderr 경고를 출력하되 exit 0을 유지한다.

async/자연어 응답을 기록할 때 오케스트레이터는 다음 payload를 임시 UTF-8 JSON 파일에 쓰고, 파일 내용을 `codex_hook.py capture`의 stdin으로 전달한다. 답변이 도착한 후만 실행한다. 실제 hook이 이미 같은 결정을 기록했다면 명시적 기록은 생략한다.

```json
{"tool_name":"request_user_input","cwd":"D:/project",
 "tool_input":{"questions":[{"id":"verify_action","question":"검증 후 진행할까요?","header":"검증"}]},
 "tool_response":{"answers":{"verify_action":{"answers":["검증 실행"]}}}}
```

- [x] **Step 4: GREEN 확인.** Codex id, Claude 문자열, 복수 선택, 자유 입력, 응답 없음, 한글 저장을 검사하고 기존 hook 회귀를 실행한다. `cwd`는 테스트 tempfile 절대경로로 주입하며 실제 소비 프로젝트에 파일을 만들지 않는다.
- [ ] **Step 5: gx-commit.** `fix: Codex 의사결정 질문과 답변 구조를 보존한다`.

## Task 4: 스킬 가드와 실제 hook smoke 계약

**Files:**
- Modify: `.claude/skills/gx-commit/SKILL.md` 사전 확인/타입 파싱
- Modify: `.claude/rules/harness-codex.md`, `.claude/rules/skill-routing.md`
- Modify: `scripts/lint-consistency.sh` [30/36]의 오래된 feature/agent_type 문자열 강제
- Create: `tests/codex-smoke.md` 보호 게이트 섹션

**Interfaces:**
- Consumes: Task 1의 Codex deny 정책.
- Produces: 훅 유무와 관계없는 스킬 보호 브랜치 중단 및 실제 smoke의 H1~H4 시나리오.

- [x] **Step 1: 보호 브랜치 사전 확인 본문을 추가한다.** 문서 변경을 구현 모양 그대로 검사하는 테스트 대신 아래 실제 행동 시나리오를 사용한다.

```markdown
- 현재 브랜치를 먼저 확인한다. main/master/develop 또는 detached HEAD이면
  빌드·스테이징·커밋을 하지 않고 작업 브랜치 필요를 안내한다.
- Codex에서 verify 미통과·지문 불일치이면 gx-verify를 수행하도록 안내하고
  커밋을 중단한다. 사용자 질문만으로 미통과 상태를 통과로 취급하지 않는다.
```

타입 선택 예시에서는 main/develop을 제거하고 `release-without-prefix`를 사용한다. Claude의 기존 위험 수용 분기는 보존하되 Codex 분기가 먼저 적용되도록 적는다.

- [x] **Step 2: H1~H4를 smoke 문서에 등록한다.**

| ID | 입력/환경 | 기대 증거 |
|---|---|---|
| H1 | 임시 프로젝트 main, hook 비활성, 커밋 스킬 요청 | HEAD/index 불변, 보호 브랜치 안내 |
| H2 | feat/t, pending verify, 신뢰된 GX hook, 빈 로컬 commit 시도 | deny event, HEAD 불변 |
| H3 | feat/t, 테스트 통과+현재 코드 지문, 로컬 commit | 정상 완료, HEAD 변경 |
| H4 | H3 검증 후 코드 변경, 재커밋 | stale fingerprint deny, HEAD 불변 |

실제 hook 로드를 확인하는 sentinel은 임시 테스트 hook이 `Write-Output GX_HOOK_SENTINEL`/`printf GX_HOOK_SENTINEL`을 deny하도록 구성한다. 배포 hook에는 sentinel 백도어를 넣지 않는다. `/hooks`로 테스트 정의를 확인·신뢰한 후 무해한 명령만 실행한다. 강제 push는 JSON fixture로만 테스트한다.

- [x] **Step 3: 린트 [30/36]을 새 계약으로 갱신한다.** 문서에 과거 주장 존재를 강제하는 검사를 제거하고 `hooks.json` JSON 파싱, `Bash` matcher, Python adapter 파일, 역할 매핑 문서 링크의 실재 여부를 검사한다. 이것을 H1~H4의 대체 증거로 쓰지 않는다.
- [x] **Step 4: 회귀 확인.** `python -m unittest discover -s tests -p 'test_codex_*.py' -v`, `bash scripts/hook-tests.sh`, `bash scripts/lint-consistency.sh`. 실제 모델 환경이 없으면 H1~H4를 미실행으로 표시한다.
- [ ] **Step 5: gx-commit.** `fix: Codex 커밋 스킬의 검증과 보호 브랜치 가드를 명시한다`.

## 2026-09-14 실행 판정

구현·회귀·실제 설치 결과는 [실측 보고서](../../reports/2026-09-14-codex-validation.md)를 따른다. 기존 WIP 보존을 위해 태스크별 커밋 대신 파일 스냅샷과 독립 리뷰로 추적했으며 gx-commit 단계는 수행하지 않았다. 코드 예시는 최초 계획이며 최종 인터페이스는 구현 파일을 따른다.
