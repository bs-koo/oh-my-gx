# Codex 네이티브 실행 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude companion 없이 Codex 리뷰와 Ralph 반복을 실행하고 실제 소비 프로젝트에서 완료 계약을 검증한다.

**Architecture:** Codex 호출은 Python 프로세스 어댑터 하나로 모은다. 기존 Ralph 상태 머신은 유지하고 호출부·최종 응답 처리만 분기한다. 리뷰는 같은 어댑터의 read-only 모드를 쓴다.

**Tech Stack:** Python 3.10+ subprocess/unittest, Bash, Codex CLI 0.154.0, Node 테스트 fixture.

**Spec:** `docs/superpowers/specs/2026-09-14-codex-native-compat-design.md` C1~C3 및 종단 검증.

## Global Constraints

- 지원 검증 기준은 Codex CLI 0.154.0이다. 더 낮은 버전은 호환을 보증하지 않는다.
- Windows PowerShell + Git Bash, Linux Bash를 필수 검증 환경으로 둔다. macOS는 추가 검증 전 미측정으로 표시한다.
- Python 3.10 이상 표준 라이브러리와 기존 Bash/Git/Node를 사용한다. 새 런타임 패키지는 추가하지 않는다.
- 전역 설치·훅 신뢰·모델·권한을 진단 명령에서 변경하지 않는다. 신뢰 우회·샌드박스 해제 플래그를 러너에 추가하지 않는다.
- 구현 브랜치에서 작업하고 기존 미커밋 변경을 임의로 스테이징·되돌리기·삭제하지 않는다. 커밋은 gx-commit 절차를 따른다.
- 문서와 커밋 메시지는 한국어로 작성한다. 이모지는 새로 추가하지 않는다.

## Task 1: stdin·이벤트·최종 응답을 분리하는 Codex 실행기

**Files:**
- Create: `scripts/codex-run.py`, `tests/test_codex_runner.py`
- Create: `tests/fixtures/codex/mock_codex.py`

**Interfaces:**
- Consumes: UTF-8 prompt 파일, 소비 프로젝트 cwd, `review|iterate`, 선택적 모델, timeout 초.
- Produces: `build_argv(command: list[str], cwd: Path, final: Path, mode: str, model: str | None) -> list[str]`; `run_codex(command, cwd, prompt, final, events, mode, model, timeout) -> int`.
- CLI: `python scripts/codex-run.py --cwd DIR --prompt FILE --final FILE --events FILE --mode review|iterate [--model NAME] [--timeout SECONDS] [--codex-executable FILE]`.
- exit: 0 성공, 2 입력/출력 충돌, 3 자식 실패·빈 응답, 124 timeout. stdout에는 성공 시 최종 응답만 쓴다. 이벤트와 stderr는 events 파일에 저장하되 서로 식별 가능한 별도 `.stderr` 파일로 분리한다.

- [x] **Step 1: 테스트 fixture와 실패 테스트를 작성한다.** mock은 실제 모델을 호출하지 않는다.

```python
# tests/fixtures/codex/mock_codex.py
import json
from pathlib import Path
import sys
args = sys.argv[1:]
prompt = sys.stdin.read()
if prompt == 'FAIL':
    raise SystemExit(9)
final = Path(args[args.index('--output-last-message') + 1])
final.write_text('검토 완료\n', encoding='utf-8')
print(json.dumps({'type': 'probe', 'args': args, 'prompt': prompt}))
```

```python
# tests/test_codex_runner.py
import json
from pathlib import Path
import sys
import tempfile
import unittest
from codex_test_support import ROOT, load
runner = load('gx_runner', 'scripts/codex-run.py')
class RunnerTests(unittest.TestCase):
    def test_prompt_stays_on_stdin_and_events_are_separate(self):
        with tempfile.TemporaryDirectory(prefix='gx runner ') as directory:
            cwd = Path(directory)
            prompt, final, events = [cwd / n for n in ('prompt.md', 'final.md', 'events.jsonl')]
            prompt.write_text('한글 $x `value` & 내용', encoding='utf-8')
            command = [sys.executable, str(ROOT / 'tests/fixtures/codex/mock_codex.py')]
            rc = runner.run_codex(command, cwd, prompt, final, events, 'review', None, 5)
            self.assertEqual(rc, 0)
            event = json.loads(events.read_text(encoding='utf-8'))
            self.assertNotIn('한글 $x `value` & 내용', event['args'])
            self.assertEqual(event['prompt'], '한글 $x `value` & 내용')
            self.assertIn('read-only', event['args'])
            self.assertEqual(final.read_text(encoding='utf-8'), '검토 완료\n')
```

- [x] **Step 2: RED 확인.** `python -m unittest discover -s tests -p 'test_codex_runner.py' -v`; 실행기 부재로 실패.
- [x] **Step 3: 명령 생성과 실행을 구현한다.**

```python
from pathlib import Path
import os
import signal
import subprocess

def build_argv(command, cwd, final, mode, model):
    if mode not in ('review', 'iterate'):
        raise ValueError('mode는 review 또는 iterate여야 합니다.')
    argv = [*command, 'exec', '--cd', str(cwd), '--sandbox',
            'read-only' if mode == 'review' else 'workspace-write',
            '--json', '--color', 'never', '--output-last-message', str(final)]
    if model:
        argv += ['--model', model]
    return [*argv, '-']

def stop_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       capture_output=True, timeout=10)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait(timeout=10)

def run_codex(command, cwd, prompt, final, events, mode, model, timeout):
    paths = [Path(p).resolve() for p in (cwd, prompt, final, events)]
    cwd, prompt, final, events = paths
    stderr_path = events.with_suffix(events.suffix + '.stderr')
    if final.exists() or events.exists() or stderr_path.exists():
        return 2
    if not cwd.is_dir() or not prompt.is_file() or timeout <= 0:
        return 2
    argv = build_argv(command, cwd, final, mode, model)
    if os.name == 'nt' and str(command[0]).lower().endswith(('.cmd', '.bat')):
        if any(any(c in arg for c in '&|<>^%!\r\n"') for arg in argv):
            return 2
    data = prompt.read_bytes()
    proc = None
    try:
        final.parent.mkdir(parents=True, exist_ok=True)
        events.parent.mkdir(parents=True, exist_ok=True)
        with events.open('xb') as out, stderr_path.open('xb') as err:
            proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE,
                stdout=out, stderr=err, start_new_session=(os.name != 'nt'),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
            try:
                proc.communicate(data, timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_tree(proc)
                return 124
        if proc.returncode != 0 or not final.is_file():
            return 3
        return 0 if final.read_text(encoding='utf-8').strip() else 3
    except (OSError, UnicodeError, subprocess.SubprocessError):
        if proc is not None and proc.poll() is None:
            stop_tree(proc)
        return 3
```

CLI는 argparse로 위 인자를 받아 Path로 변환한다. 실행 파일은 명시된 `--codex-executable` 또는 `shutil.which('codex.cmd' if os.name == 'nt' else 'codex')`로 결정한다. 찾지 못하면 stderr 안내와 exit 2. 성공 시 final의 UTF-8 내용을 `sys.stdout.buffer`로 출력한다. 이벤트 파일 내용을 stdout에 재출력하지 않는다. timeout 기본값은 review 300초, iterate 1800초다.

- [x] **Step 4: 실패 경계를 검사한다.** mock에 빈 final, final을 쓴 후 exit 9, stderr에 가짜 COMPLETE, 자식 sleep 프로세스를 만든 뒤 정지하는 경우를 추가한다. 각각 3/3/최종 응답만 사용/124 및 자식 종료를 검사한다. 이전 final/events가 있으면 바이트와 mtime 불변·rc 2를 검사한다. Windows `.cmd` wrapper로 mock을 호출하는 통합 테스트도 추가하여 공백·한글 경로를 실행한다.
- [ ] **Step 5: gx-commit.** `feat: Codex 비대화형 실행과 최종 응답 계약을 분리한다`.

## Task 2: Ralph의 Claude/Codex 호출부 분기

**Files:**
- Modify: `scripts/gx-ralph.sh` 환경/호출/계약 파싱
- Modify: `scripts/test-gx-ralph.sh` COMPLETE 원장 및 두 하네스 실행
- Modify: `.claude/skills/gx-ralph/SKILL.md`, `gx-ralph-iterate/SKILL.md`
- Create: `tests/test_codex_ralph.py`

**Interfaces:**
- Consumes: Task 1 CLI, 계획 B의 설치된 gx-ralph-iterate 절대경로.
- Produces: `GX_RALPH_HARNESS=claude|codex`(기본 claude), `GX_RALPH_CODEX_CMD`(선택 실행 파일 경로), `GX_RALPH_ITERATE_SKILL`(Codex에서 필수), 기존 exit 0/2/3/4/5/6/7 유지.

- [x] **Step 1: mock 회귀를 추가하고 RED를 확인한다.** 아래 테스트는 임시 Git 프로젝트와 원장을 생성한다. mock Codex는 final에 BLOCKED를 쓰며 stdout에 가짜 COMPLETE를 출력한다. Claude 실행 파일도 무해한 `echo`로 대체하여 현재 코드의 실패 확인 중 실제 모델을 호출하지 않는다. 실행: `python -m unittest discover -s tests -p 'test_codex_ralph.py' -v`; 구현 전에는 기대 exit 2와 달라 실패한다.

```python
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from codex_test_support import ROOT

class RalphTests(unittest.TestCase):
    def test_contract_never_comes_from_event_log(self):
        bash = shutil.which('bash')
        self.assertIsNotNone(bash, '테스트에는 Git Bash 또는 Bash가 필요합니다.')
        with tempfile.TemporaryDirectory(prefix='gx-ralph-') as directory:
            cwd = Path(directory)
            env = os.environ.copy()
            env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
            def git(*args):
                return subprocess.run(['git', *args], cwd=cwd, env=env,
                                      check=True, capture_output=True)
            git('init', '-q', '-b', 'feat/t')
            git('config', 'user.email', 'gx@test.invalid')
            git('config', 'user.name', 'GX fixture')
            (cwd / 'empty-hooks').mkdir()
            git('config', 'core.hooksPath', str(cwd / 'empty-hooks'))
            (cwd / 'base.txt').write_text('base\n', encoding='utf-8')
            git('add', 'base.txt')
            git('commit', '-qm', 'chore: fixture')
            dev = cwd / '.dev/feat-t'
            dev.mkdir(parents=True)
            (dev / 'state.md').write_text(
                'pipeline: gx-ralph\nstatus: in_progress\nverify-status: pending\n'
                'branch: feat/t\nmax-iterations: 1\nlast-known-head: none\n',
                encoding='utf-8')
            (dev / 'ac-status.json').write_text(json.dumps({
                'version': 1, 'branch': 'feat/t', 'created': 't', 'updated': 't',
                'acs': [{'id': 'AC-1', 'title': 't', 'passes': False,
                         'attempts': 0, 'last_error': ''}]}), encoding='utf-8')
            (dev / 'progress.txt').write_text('# progress\n', encoding='utf-8')
            mock = cwd / 'mock_codex.py'
            mock.write_text(
                'import json, sys\nfrom pathlib import Path\n'
                'args = sys.argv[1:]\nsys.stdin.read()\n'
                "Path(args[args.index('--output-last-message') + 1]).write_text("
                "'<ralph>BLOCKED: fixture</ralph>\\n', encoding='utf-8')\n"
                "print(json.dumps({'text': '<ralph>COMPLETE</ralph>'}))\n",
                encoding='utf-8')
            wrapper = cwd / ('mock.cmd' if os.name == 'nt' else 'mock.sh')
            if os.name == 'nt':
                self.assertFalse(any(c in str(mock) + sys.executable for c in '%!&|<>^"'))
                wrapper.write_bytes(
                    f'@"{sys.executable}" "{mock}" %*\r\n@exit /b %ERRORLEVEL%\r\n'.encode())
            else:
                wrapper.write_text(
                    f'#!/bin/sh\nexec {shlex.quote(sys.executable)} '
                    f'{shlex.quote(str(mock))} "$@"\n', encoding='utf-8')
                wrapper.chmod(0o755)
            env.update(GX_RALPH_HARNESS='codex', GX_RALPH_CLAUDE_CMD='echo',
                       GX_RALPH_CODEX_CMD=str(wrapper),
                       GX_RALPH_ITERATE_SKILL=str(
                           ROOT / '.claude/skills/gx-ralph-iterate/SKILL.md'))
            env.pop('GX_RALPH_MODEL', None)
            result = subprocess.run([bash, str(ROOT / 'scripts/gx-ralph.sh'), '1'],
                cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
```

Windows `.cmd` mock의 공백·한글 경로 검증은 Task 1의 전용 통합 테스트에서 수행한다. 위 fixture는 계약 판정만 검사한다.

- [x] **Step 2: 호출 전 하네스·실행 조건을 검사한다.**

```bash
HARNESS="${GX_RALPH_HARNESS:-claude}"
case "$HARNESS" in claude|codex) ;; *) fail '지원하지 않는 하네스' ;; esac
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$HARNESS" = codex ]; then
  [ -f "${GX_RALPH_ITERATE_SKILL:-}" ] || fail 'Codex 반복 스킬 경로가 필요합니다'
fi
PYTHON_CMD=''
for candidate in python3 python; do
  if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3,10))' >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"; break
  fi
done
[ -n "$PYTHON_CMD" ] || fail 'Python 3.10 이상이 필요합니다'
```

`fail` 함수 정의 다음, lock 획득 전에 이 분기를 둔다. 실행 파일과 스킬을 찾지 못하면 반복을 시작하지 않는다. Codex 경로에 Claude `--allowedTools`를 전달하지 않는다.

- [x] **Step 3: 반복 호출부를 분기한다.**

```bash
FINAL="$DEV_DIR/iter-$i.final.md"
if [ "$HARNESS" = codex ]; then
  PROMPT="$DEV_DIR/iter-$i.prompt.md"
  printf '다음 SKILL.md를 읽고 반복 1회를 수행하라: %s\n' "$GX_RALPH_ITERATE_SKILL" > "$PROMPT"
  printf '종료 계약은 최종 응답에 한 줄로만 출력한다. 질문이 필요하면 BLOCKED로 종료한다.\n' >> "$PROMPT"
  CODEX_ARGS=()
  [ -n "${GX_RALPH_CODEX_CMD:-}" ] && CODEX_ARGS=(--codex-executable "$GX_RALPH_CODEX_CMD")
  "$PYTHON_CMD" "$SCRIPT_DIR/codex-run.py" --cwd "$PWD" --prompt "$PROMPT" \
    --final "$FINAL" --events "$DEV_DIR/iter-$i.events.jsonl" --mode iterate \
    --timeout "$ITER_TIMEOUT" ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
    ${CODEX_ARGS[@]+"${CODEX_ARGS[@]}"} > "$LOG" 2>&1
else
  MSYS_NO_PATHCONV=1 $TIMEOUT_CMD $CLAUDE_CMD -p "$SKILL_NAME" \
    ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} --allowedTools "$ALLOWED_TOOLS" > "$LOG" 2>&1
fi
EXIT_CODE=$?
[ "$EXIT_CODE" -eq 0 ] || { echo '[gx-ralph] 반복 실행 실패' >&2; exit 3; }
CONTRACT_SOURCE="$LOG"
[ "$HARNESS" = codex ] && CONTRACT_SOURCE="$FINAL"
CONTRACT=$(tr -d '\r' < "$CONTRACT_SOURCE" | grep -E '^<ralph>(COMPLETE|CONTINUE|BLOCKED: .+)</ralph>$')
```

정확한 계약 줄이 둘 이상이면 기존 case의 unknown 분기로 exit 3. COMPLETE 분기 전에 원장을 JSON으로 파싱해 `acs`가 비어 있지 않고 모든 항목의 `passes is True`인지 확인한다. 두 하네스 모두 Step 2에서 확보한 Python으로 아래 코드를 실행하고 실패하면 exit 3으로 종료한다.

```python
import json
import sys
with open(sys.argv[1], encoding='utf-8') as stream:
    items = json.load(stream)['acs']
raise SystemExit(0 if items and all(a.get('passes') is True for a in items) else 1)
```

원장 미완료 COMPLETE는 exit 3. 재실행 archive는 `iter-*.log`뿐 아니라 `.final.md`, `.prompt.md`, `.events.jsonl`, `.events.jsonl.stderr`도 동일 archive에 보존해 이전 final 충돌을 막는다. 파일명이 코드로 실행되지 않도록 경로 배열을 사용한다.

- [x] **Step 4: 회귀 실행.** 기존 COMPLETE mock은 원장 passes를 true로 변경한 뒤 계약을 출력하도록 수정한다. 두 하네스에 대해 COMPLETE/BLOCKED/NO_DRIFT/NO_PROGRESS/MAX_ITER/lock/nonzero/timeout을 검사한다. `bash scripts/test-gx-ralph.sh`와 `python -m unittest discover -s tests -p 'test_codex_*.py' -v`를 통과시킨다.
- [ ] **Step 5: gx-commit.** `feat: Ralph 반복을 Codex 하네스로 실행한다`.

## Task 3: cross-review의 Codex 직접 실행과 제공자 표시

**Files:**
- Modify: `.claude/skills/gx-cross-review/SKILL.md` 인자·Step 1-1·Step 3-A/B
- Modify: `README.md` cross-review 안내
- Modify: `tests/codex-smoke.md` 리뷰 시나리오

**Interfaces:**
- Consumes: 기존 `${PROMPT_FILE}`/`${RAW_FILE}`/산출물 slicing, Task 1 review 모드.
- Produces: `--advisor codex`는 직접 Codex CLI, `--advisor native`는 현재 하네스의 내부 역할 리뷰. `--advisor claude`는 Claude 호스트에서 기존 의미 유지; Codex 호스트에서는 명시적 미지원 안내.

- [x] **Step 1: companion 탐색을 실제 실행 파일 확인으로 대체한다.** Codex CLI가 없으면 설치/인증 안내 후 종료하는 기존 계약을 유지한다. `~/.claude/plugins/cache` 필수 의존과 Claude `/plugin install` 지시는 제거한다. 설치된 GX 루트의 `scripts/codex-run.py`가 있는지 확인하고 없다면 배포 불완전으로 중단한다.
- [x] **Step 2: Step 3-A를 다음 호출 규약으로 바꾼다.** 아래는 Bash 실행 예시이며 변수 값은 앞 단계에서 산정한 실제 경로다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/codex-run.py" --cwd "$PROJECT_ROOT" \
  --prompt "$PROMPT_FILE" --final "$RAW_FILE" \
  --events "$DEV_DIR/cross-review.events.jsonl" --mode review --timeout 300
```

재실행 전 기존 결과를 명시적인 timestamp archive로 옮긴 후 호출한다. 실행 실패면 결과를 정규화하거나 후속 단계로 넘어가지 않는다. prompt는 파일 stdin이므로 `$`·백틱·따옴표를 줄이라는 기존 제약은 삭제한다. 예제 Python 이름은 B setup에서 검증한 실행 파일로 치환하도록 안내한다.

- [x] **Step 3: 제공자 분기를 명시한다.**

```markdown
--advisor native: 현재 하네스의 역할 에이전트로 리뷰한다.
--advisor codex: Codex CLI의 read-only 세션에서 리뷰한다.
--advisor claude: Claude Code 호스트에서 기존 역할 리뷰를 수행한다.
Codex 호스트에서 claude를 선택하면 Claude 실행 경로 미지원으로 종료하고,
native 또는 codex를 명시적으로 선택하도록 안내한다. 자동으로 이름만 바꾸지 않는다.
결과에 실행 하네스와 확인 가능한 실제 모델을 기록한다.
```

- [ ] **Step 4: 회귀·실제 smoke.** Claude companion 없는 임시 소비 프로젝트에서 Codex 리뷰 수행, source/index/HEAD 불변, AC 매트릭스·신규 위험·총평 존재를 확인한다. `--advisor claude`가 Codex에서 native 성공으로 둔갑하지 않는지도 확인한다. 원래 native 역할 리뷰의 산출물 규약은 유지한다.
- [ ] **Step 5: gx-commit.** `feat: 교차 리뷰의 Codex 직접 실행과 제공자 구분을 지원한다`.

## Task 4: 실제 설치 후 행동 검증과 릴리스 판정

**Files:**
- Modify: `tests/codex-smoke.md`, `tests/golden-scenarios.md`, `README.md`
- Modify: `scripts/behavior-tests.sh` 문서에서 Claude 전용임을 명시
- Create: `tests/fixtures/codex/README.md` fixture와 실제 검증 구분
- Release only: `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`

**Interfaces:**
- Consumes: A H1~H4, B R1~R3/Q1/S1~S3, C runner의 event/final 분리.
- Produces: `tests/codex-smoke.md`에 실행 환경·명령·PASS/FAIL/NOT_RUN과 증거 경로를 기록한 릴리스 판정. 특정 개인 홈 경로는 fixture에 하드코딩하지 않는다.

- [ ] **Step 1: 깨끗한 설치 대상을 만든다.** 승인된 배포 커밋을 임시 export로 만들고 역할 생성 `--check`를 실행한다. 처음 개발 확인은 local source, 릴리스 합격은 커밋/태그의 Git source로 설치한다. 현재 미커밋 WIP를 HEAD와 같다고 가정하지 않는다.
- [x] **Step 2: 외부 최소 프로젝트에서 스모크를 실행한다.** `tests/fixtures/behavior/node-minimal`을 임시 경로에 복사하고 Node 테스트가 통과함을 먼저 확인한다. 플러그인 저장소의 AGENTS.md는 복사하지 않는다. 설치·활성화·hook trust를 각각 확인한 뒤 다음 요청을 실행한다.

```text
oh-my-gx gx-setup으로 이 프로젝트를 준비해줘.
oh-my-gx gx-tdd로 src/clamp-upper.js에 clampUpper(value, upper)를 테스트 먼저 구현해줘.
CommonJS module.exports = { clampUpper }로 내보내고, upper가 음수이면 RangeError,
그 외에는 Math.min(value, upper)를 반환하도록 해줘. 기존 테스트는 유지해줘.
구현한 변경을 oh-my-gx gx-cross-review --advisor codex로 검토해줘.
oh-my-gx gx-verify로 직접 테스트를 실행해 검증해줘.
커밋할 변경과 메시지만 정리해줘. push와 PR 게시 없이 검토 가능한 상태로 끝내줘.
```

스모크 수용 기준은 `clampUpper(5, 3) === 3`, `clampUpper(2, 3) === 2`, `clampUpper(2, -1)`이 `RangeError`를 던지는 것이다. 새 함수 테스트와 기존 테스트가 함께 통과해야 한다.

- [x] **Step 3: Ralph는 별도 임시 프로젝트에서 실행한다.** 사용자 프로젝트의 원장·커밋 이력을 재사용하지 않는다. 미완료 AC 1개부터 시작해 Codex 반복 1회와 COMPLETE 원장 검증을 확인한다. 네트워크 push를 수행하지 않는다. 승인 정책 때문에 로컬 commit이 불가능하면 BLOCKED가 올바른 결과이며 권한을 완화하지 않는다.
- [x] **Step 4: 3회 반복 결과를 기록한다.** 각 회차에 CLI 버전, OS, 실제 사용자 홈/설치 cache, 발견 스킬 수, hook trust, 호출한 child 역할·모델, RED/GREEN 실행 로그, review 파일, verify 지문, 사용자의 개입 횟수, 시간, 제공된 토큰 사용량을 적는다. 제공되지 않는 지표는 NOT_MEASURED로 기록한다. A/B/C의 실패가 하나라도 있으면 전체 지원 표기를 보류한다.
- [x] **Step 5: 기존 및 새 오프라인 검사를 실행한다.**

```bash
bash scripts/lint-consistency.sh
bash scripts/hook-tests.sh
bash scripts/test-gx-ralph.sh
bash scripts/test-behavior-tests.sh
python scripts/sync-codex-resources.py --check
python -m unittest discover -s tests -p 'test_codex_*.py' -v
```

- [ ] **Step 6: 지원표와 릴리스 문서를 갱신한다.** 실제 smoke 합격 범위만 README에 적는다. 배포가 요청된 시점에만 저장소 release 규칙대로 버전을 함께 올리고 gx-commit/gx-pull-request 절차를 따른다. 이 계획을 작성하거나 mock이 통과했다는 이유로 배포하지 않는다.

## 2026-09-14 실행 판정

구현·회귀·실제 설치 결과는 [실측 보고서](../../reports/2026-09-14-codex-validation.md)를 따른다. 기존 WIP 보존을 위해 태스크별 커밋 대신 파일 스냅샷과 독립 리뷰로 추적했으며 gx-commit 단계는 수행하지 않았다. 코드 예시는 최초 계획이며 최종 인터페이스는 구현 파일을 따른다.

C3 Step 4는 호스트 외부 Codex 리뷰와 내부 native 리뷰를 실측했으나 Codex의 `--advisor claude` 미지원 안내 자체는 실제 모델에서 별도로 실행하지 않아 부분 확인이다. C4 Step 1의 local export 설치는 완료했고 릴리스 Git source는 미실행이다. C4 Step 3의 실제 결과는 정상 BLOCKED이며 COMPLETE 원장 검증은 mock 회귀로 확인했다. 마지막 산출물 제외 변경은 실제 Git fixture로 검증했다. 릴리스·버전 갱신은 수행하지 않았다.
