# Codex 실행 규약

이 파일과 아래 역할 경로는 현재 파일의 위치를 기준으로 해석한다. 실행 전 **실제 노출된 도구 스키마와 spawn 모델 allowlist**를 확인한다. 이 파일은 Codex 경로에만 적용하며 Claude Code의 기존 `Task`/`Skill` 호출은 유지한다.

**설치 경로 확인**: 소비 프로젝트의 cwd나 `.claude`를 플러그인 루트로 간주하지 않는다. 실제 설치된 이 `codex-runtime.md`의 절대경로를 `RUNTIME_PATH`로 잡으면 Python의 `Path(RUNTIME_PATH).resolve().parents[4]`가 GX 플러그인 루트다. 각 설치된 `SKILL.md`의 절대경로를 `SKILL_PATH`로 잡으면 `Path(SKILL_PATH).resolve().parents[3]`가 같은 루트다. PowerShell에서는 `$skillPath = (Resolve-Path -LiteralPath '<installed SKILL.md>').Path; $pluginRoot = (Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $skillPath) '..\..\..')).Path`로 확인한다. 이 루트의 `.codex-plugin/plugin.json` 존재를 확인한 뒤, 스킬에 적힌 `../../../scripts/...` helper를 이 루트에서 찾는다. 캐시를 검색해야 할 때는 **확인된 설치 루트 안에서만** `rg --files --hidden --no-ignore`를 사용한다. 검색에서 안 보인다는 이유로 소비 프로젝트나 개발 소스 경로의 helper로 대체하지 않는다.

1. 역할 위임: **현재 이 runtime.md 파일이 실제로 설치된 디렉토리**에서 `codex-roles/index.json`을 찾고, index의 `file`을 같은 디렉토리의 `codex-roles/`에 붙여 해당 `.md`를 읽는다. 예를 들어 red-writer는 `<설치된 gx-dev/references 디렉토리>/codex-roles/red-writer.md`다. 소비 프로젝트의 `.claude/codex-roles/`나 셸 cwd를 찾지 않는다. index의 `tier`·`file`·`tools`를 확인하고, 역할 본문 + 소비 프로젝트 지침 + 현재 태스크의 **전체 prompt**를 자식에게 전달한다. `agents/` 원본이 설치된다는 가정을 하지 않는다. 구현 파일을 볼 수 없는 RED 역할에는 구현 코드나 부모 대화 전체를 넘기지 않는다.
2. 현재 API는 `spawn_agent(task_name, message, fork_turns, model, reasoning_effort)`다. 격리는 `fork_turns: "none"`을 쓴다. `agent_type`은 실제 스키마에 있을 때만 사용한다. 전체 이력 fork와 모델 override를 함께 요구하지 않는다.
3. 역할 high/mid는 index에서 읽는다. 현재 후보는 high=`gpt-6-astra`/`high`, mid=`gpt-5.6-sol`/`medium`이다. **allowlist에 없는 모델은 호출하지 않는다.** 후보 부재 시 같은 허용 모델의 `high`/`medium`으로 구분한다. 허용 effort도 구분할 수 없으면 지원 제한을 보고한다. 태스크가 명시한 티어 예외와 eco의 architect high 유지 규칙을 우선한다.
4. 자식 결과는 `wait_agent`로 받고 수정 라운드는 `followup_task`로 재개한다. 도구 수 제한이나 `agent_type` 부재를 역할 전달 생략의 이유로 삼지 않는다. 원래 태스크의 JSON/YAML 반환 계약을 보존한다.
5. 질문은 현재 모드에서 제공된 async 도구 또는 허용된 동기 도구를 사용한다. 동기 `request_user_input`이 Plan 모드에서만 제공되면 기본 모드에서 호출하지 않는다. Claude `AskUserQuestion.questions[]`를 Codex `request_user_input` 형식으로 옮길 때는 한 번에 질문 1~3개, 질문마다 선택지 2~3개로 제한한다. 각 질문에 `header`·`question`·`options`를 채우고, 같은 결정을 다시 물을 때도 유지되는 stable snake_case `id`를 Codex 변환 단계에서 추가한다. Claude 전용 `multiSelect`를 제거하고, 각 option에는 짧은 `label`과 한 문장의 `description`을 넣는다. 추천 option을 첫 번째에 놓고 label 끝에 `(Recommended)`를 붙인다. UI가 자유 입력을 제공하므로 Other를 직접 option으로 추가하지 않는다. 실제 도구 스키마가 이 문서보다 우선하며, 필드나 개수 제한이 다르면 노출된 스키마에 맞춘다. 응답 전에는 독립 작업만 수행하고 자연어 fallback도 실제 답변을 기다린다. 확정된 자연어/async 결정은 아래 capture payload로 기록한다.
6. `Skill` 호출은 설치 목록의 해당 `SKILL.md`를 읽고 절차를 실행한다. verify/commit/pull-request의 검사와 중단 조건을 생략하지 않는다.
7. Bash 코드는 Git Bash 또는 Bash를 명시해서 실행한다. PowerShell 명령은 PowerShell로 실행하고 작업 위치는 `workdir`로 지정한다. timeout 인자를 추측하지 않는다. `session_id`가 나오면 `write_stdin`으로 완료를 기다린다.
8. `allowed-tools`와 index의 `tools`는 Codex의 권한 설정이 아니다. 역할 지침과 실제 도구 권한을 구분한다.

## 역할 프롬프트 전달

오케스트레이터는 읽은 역할 본문·소비 프로젝트의 `AGENTS.md`/`CLAUDE.md` 지침·태스크 전문을 합쳐 실제 `collaboration.spawn_agent` 도구의 `message`에 전달한다. index의 `tools`는 아래 대응표로 변환해 **역할 지침**으로 같은 message에 넣는다. 예를 들어 reviewer의 `Read, Glob, Grep`는 읽기/검색을 위한 `exec_command`만 허용하고 빌드·테스트·상태변경·임의 명령은 금지한다고 전달한다. 해당 역할에 `Write`가 없지만 report 파일이 필요한 경우 자식은 형식에 맞는 결과를 반환하고 부모가 파일로 저장한다. red-writer의 Bash는 허용되더라도 역할 본문의 구현 코드 열람·수정 금지가 우선한다. 도구 목록을 하네스 권한 집행으로 주장하지 않는다.

| 역할 tools 원문 | Codex에서 가능한 대응 | 전달할 제약 |
|---|---|---|
| `Read` | `exec_command`로 파일 읽기, 제공된 리소스 읽기 도구 | 읽기 명령만 |
| `Glob`·`Grep` | `rg --files`·`rg`를 `exec_command`로 실행 | 검색 명령만 |
| `Write`·`Edit` | `apply_patch` 또는 파일 편집 명령 | 역할 본문이 허용한 파일만 수정 |
| `Bash` | Bash를 명시한 `exec_command` | 역할 본문과 프로젝트 지침 범위의 명령만 |
| `AskUserQuestion` | 현재 모드에서 제공된 질문 도구 | 실제 사용자 응답을 기다림 |

다음은 **인자 조립 예시**다. 셸이나 `functions.exec`에서 collaboration을 호출하는 실행 라이브러리가 아니다. `model`과 `effort`는 위 allowlist 확인 후 선택한 값이다.

```javascript
function reviewArguments({roleBody, roleTools, projectInstructions, taskPrompt, model, effort}) {
  return {
    task_name: 'review_task_1',
    message: [roleBody, roleTools, projectInstructions, taskPrompt].join('\n\n'),
    fork_turns: 'none',
    model,
    reasoning_effort: effort
  };
}
```

## 질문 결정 기록

실제 사용자 응답이 확정된 뒤 자연어/async 선택 결과를 UTF-8 JSON 파일에 쓰고, 설치된 GX 루트의 `.claude/hooks/codex_hook.py capture`에 stdin으로 전달한다. 경로는 **이 runtime 파일 위치에서** `../../../../.claude/hooks/codex_hook.py`로 찾을 수 있다. 소비 프로젝트의 `.claude/hooks`를 찾지 않는다. 이미 PostToolUse 훅이 같은 결정을 기록했다면 명시적 기록은 생략한다. 기록에 실패하면 stderr를 확인하고 실패를 드러내되 응답 전에 추측한 답을 기록하지 않는다.

```json
{"tool_name":"request_user_input","cwd":"D:/consumer-project","tool_input":{"questions":[{"id":"verify_action","header":"검증 선택","question":"검증 후 진행할까요?","options":[{"label":"검증 실행 (Recommended)","description":"테스트를 실행하고 결과를 확인합니다."},{"label":"나중에 실행","description":"검증을 보류하고 이유를 기록합니다."}]}]},"tool_response":{"answers":{"verify_action":{"answers":["검증 실행 (Recommended)"]}}}}
```

## 경로·인코딩·Git

`Read("...")`의 상대경로는 셸 cwd가 아니라 **그 지시가 적힌 문서의 위치**를 기준으로 해석한다. Windows PowerShell에서는 `Get-Content -Encoding UTF8`을 사용한다. Python은 `encoding="utf-8"`을 명시한다. PowerShell에서 Python stdin으로 파이프를 보내기 전에는 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $OutputEncoding = [System.Text.UTF8Encoding]::new($false)`로 UTF-8을 설정한다. 파일 경로와 한글 payload를 기본 코드페이지에 맡기지 않는다.

격리된 sandbox 계정과 저장소 소유자가 달라 Git의 dubious ownership 검사가 실패하면 **그 소비 프로젝트의 확인된 절대경로 하나에만**, 해당 명령 프로세스의 `git -c safe.directory=<absolute-project-path> ...`를 사용한다. 전역 `git config --global --add safe.directory '*'` 또는 전역 예외를 만들지 않는다.

Windows PowerShell에서 Node CLI를 호출할 때 `npm`·`npx`·`pnpm`·`codex` 이름이 `.ps1`에 먼저 해석되어 실행 정책 오류가 날 수 있다. 실제 설치를 `Get-Command npm.cmd` 등으로 확인하고 `npm.cmd`, `npx.cmd`, `pnpm.cmd`, `codex.cmd`를 명시한다. Bash에서는 일반 실행 파일 이름을 쓴다.
