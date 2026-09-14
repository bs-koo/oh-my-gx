# Codex 하네스 어댑터

이 저장소를 Codex CLI에서 작업할 때의 프로젝트 지침이다. 지원 검증 기준은 **Codex CLI 0.154.0**이다. 실제 세션의 도구 스키마·모델 allowlist가 이 문서와 다르면 노출된 스키마를 우선한다. 소비 프로젝트에 설치된 스킬은 이 문서를 받지 않을 수 있으므로, 실행 규약의 배포 정본은 [codex-runtime.md](../skills/gx-dev/references/codex-runtime.md)다.

## 설치와 발견

Windows PowerShell 예시:

```powershell
codex.cmd plugin marketplace add bs-koo/oh-my-gx
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

Codex 입력창의 `/skills`에서 17개 GX 스킬을 확인한다. `source:url,url:./`는 Git source이고, 개발 중 임시 marketplace에는 `source:local,path:./`를 사용한다. Git source의 실제 cache 경로와 사용자 홈은 `codex.cmd plugin list --json`으로 확인한다. subprocess의 홈 환경변수가 사용자 홈과 다를 수 있으므로 홈 디렉토리를 추측해 수동 복사하지 않는다. 개발용 `skill-creator` junction은 릴리스 스킬 목록에 포함하지 않는다.

## 역할·도구 매핑

Codex 스킬은 `../skills/gx-dev/references/codex-runtime.md`를 읽는다. 배포된 `codex-roles/index.json`에서 역할 이름별 `tier`, `file`, `tools`를 읽고 해당 역할 본문·도구 제약·소비 프로젝트 지침·태스크 prompt 전문을 `spawn_agent` message에 전달한다. reviewer처럼 `Read/Glob/Grep`만 가진 역할은 읽기/검색용 명령만 사용하고 보고서 파일은 부모가 저장한다. red-writer의 구현 코드 미열람 지침을 부모 대화 fork로 깨지 않도록 `fork_turns: "none"`을 쓴다.

현재 `spawn_agent`의 인자는 `task_name`, `message`, `fork_turns`, `model`, `reasoning_effort`다. 실제 스키마에 `agent_type`이 없으면 보내지 않는다. high 후보는 `gpt-6-astra`/`high`, mid 후보는 `gpt-5.6-sol`/`medium`이지만 세션 allowlist 확인 후에만 선택한다. 해당 모델이 없으면 허용 모델의 high/medium effort로 구분한다. 역할의 원래 `opus`/`sonnet` 매핑은 index 생성기가 보존한다. `allowed-tools`는 Codex 권한 설정이 아니므로 목록을 자식 지침에 전달해도 도구 강제가 이루어진다고 주장하지 않는다.

`AskUserQuestion`은 현재 모드에서 제공된 질문 도구로 옮긴다. 동기 `request_user_input`이 Plan 모드에만 제공되면 기본 모드에서 호출하지 않는다. async 또는 자연어 질문은 실제 사용자 응답을 기다리고, 확정된 결정은 `codex_hook.py capture`의 id→answers payload로 기록한다. `Skill()` 호출은 설치된 해당 `SKILL.md`를 읽고 verify/commit/pull-request의 모든 게이트를 수행한다.

## 훅과 신뢰

Codex `hooks.json`의 PreToolUse matcher는 **`^Bash$`**다. POSIX 명령은 `python3 "${PLUGIN_ROOT}/.claude/hooks/codex_hook.py" guard`, Windows 명령은 `python "${PLUGIN_ROOT}/.claude/hooks/codex_hook.py" guard`다. 어댑터가 기존 Bash 가드를 호출하고 Codex에서 지원되지 않는 `ask` 판정을 `deny`로 정규화한다. Claude Code는 기존 `Bash` 가드 호출과 ask 분기를 유지한다.

훅은 파일이 있다는 사실만으로 신뢰·실행되지 않는다. Codex 입력창의 `/hooks`에서 GX 정의를 확인하고 사용자 신뢰 상태를 확인한다. `/hooks`에 보이지 않거나 신뢰되지 않으면 보호 게이트가 실행된다고 보고하지 않는다. 이 프로젝트의 `scripts/codex-install-hooks.py`는 수동 설정이 필요한 경우 렌더링과 기존 비GX 훅 보존을 지원한다. `--write`만 파일을 변경한다. `plugin_hooks` 기능 플래그 활성화를 설치 해결책으로 권하지 않는다.

스킬 자체도 보호 분기를 갖는다. gx-commit은 main/master/develop과 detached HEAD에서 빌드·스테이징·커밋 전에 중단하고, Codex에서 verify 미통과·현재 코드 지문 불일치면 gx-verify를 안내하고 중단한다. 훅이 로드되지 않은 상태에서도 이 스킬 분기는 지킨다. 가드의 명령 파서 범위 밖 셸 조합이나 사용자 터미널 직접 실행까지 포괄하는 보안 경계로 주장하지 않는다.

## Windows·Git 실행

PowerShell 파일 읽기는 `Get-Content -Encoding UTF8`, Python 파일 입출력은 명시적 `encoding="utf-8"`을 사용한다. PowerShell에서 Python stdin으로 파이프를 보낼 때는 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $OutputEncoding = [System.Text.UTF8Encoding]::new($false)`를 먼저 설정한다. Bash 스크립트는 Git Bash/Bash로, PowerShell 코드는 PowerShell로 실행한다. `exec_command`에는 실제 지원되는 인자와 `workdir`만 전달하고, session id가 반환되면 `write_stdin`으로 기다린다.

샌드박스 계정의 Git 소유권 불일치가 확인되면 확인된 소비 프로젝트 절대경로 하나에만 명령별 `git -c safe.directory=<absolute-project-path> ...`를 사용한다. 전역 예외나 `safe.directory '*'`를 추가하지 않는다.

## 검증 범위

로컬 단위 검사는 `python scripts/sync-codex-resources.py --check`, `python -m unittest discover -s tests -p "test_codex_*.py" -v`, `bash scripts/hook-tests.sh`, `bash scripts/lint-consistency.sh`다. 이 검사는 실제 설치·모델·훅 신뢰를 입증하지 않는다. 소비 프로젝트 실제 세션의 S1~S3, R1~R3, Q1, H1~H4 시나리오는 [Codex smoke 계약](../../tests/codex-smoke.md)에 결과와 근거를 별도 기록한다. 인증된 모델 세션을 실행하지 않았다면 미실행으로 표시한다.
