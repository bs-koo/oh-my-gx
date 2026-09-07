# Codex 하네스 어댑터

이 문서는 oh-my-gx를 OpenAI Codex CLI에서 사용할 때의 도구 매핑과 제약을 정리한다. Claude Code에서는 이 문서를 읽을 필요가 없다.

측정 환경: Codex CLI 0.130.0 (2026-08-28 실측). 하네스가 갱신되면 아래 표보다 실제 도구 목록을 우선한다.

## 설치

Codex는 Claude Code의 플러그인 규격을 그대로 채택했다. 저장소 루트가 마켓플레이스 루트가 된다.

```bash
codex plugin marketplace add <저장소 경로>
```

- 매니페스트: `.codex-plugin/plugin.json` (Claude Code는 `.claude-plugin/plugin.json`)
- 마켓플레이스: `.agents/plugins/marketplace.json` (Claude Code는 `.claude-plugin/marketplace.json`)
- 스킬 경로는 양쪽 모두 `./.claude/skills/`를 가리킨다. 스킬 본문은 단일 소스이며 하네스별로 복제하지 않는다.

`codex plugin`에는 설치·활성화 서브커맨드가 없다. 마켓플레이스 등록까지만 CLI로 가능하고, 플러그인 활성화는 Codex TUI에서 수행한다.

## 도구 매핑

스킬 본문은 Claude Code 도구명으로 서술되어 있다. Codex에서는 아래로 옮겨 실행한다.

| 스킬 본문 표기 | Codex 실제 API | 비고 |
|----------------|----------------|------|
| `Task(subagent_type="oh-my-gx:red-writer")` | `spawn_agent`(`agent_type`, `fork_turns`, `model`, `reasoning_effort`) | 격리 컨텍스트는 `fork_turns: "none"` |
| 서브에이전트 결과 대기 | `wait_agent` | 이벤트 구독이다. 짧은 폴링을 쌓지 않는다 |
| 서브에이전트 재작업 지시 | `followup_task` | Claude Code의 Task에는 없는 기능. 새 에이전트를 띄우지 말고 재개한다 |
| `AskUserQuestion` | `request_user_input` | 선택지 지원. EXPERIMENTAL — 아래 제약 참조 |
| Bash 실행 | `exec_command` / `local_shell` | 훅 matcher가 달라지는 원인 |

`agents/`의 17개 에이전트 정의는 `model: opus` / `model: sonnet`을 쓴다. Codex에서는 해당 모델이 없으므로 `spawn_agent` 시 현재 spawn 허용 목록의 모델과 `reasoning_effort`를 함께 지정한다. `model`만 지정하면 effort가 그 모델의 기본값으로 조용히 되돌아간다.

## 훅

훅 규약은 Claude Code와 동일하다. 이벤트명(`PreToolUse`·`PostToolUse`·`SessionStart`·`Stop`·`UserPromptSubmit`), 입력 필드(`tool_name`·`tool_input`·`tool_response`), 출력 필드(`hookEventName`·`hookSpecificOutput`·`permissionDecision`·`permissionDecisionReason`), 판정값(`allow`·`ask`·`deny`)이 모두 같다.

다른 점은 matcher가 겨냥하는 도구명이다. Claude Code는 `Bash`, Codex는 `exec_command`·`local_shell`이다. 그래서 훅 설정 파일을 하네스별로 나눈다.

- Claude Code: `.claude-plugin/plugin.json`의 인라인 `hooks` (matcher `Bash`)
- Codex: `hooks.json` (matcher `exec_command|local_shell|shell`)

두 설정 모두 같은 스크립트 `.claude/hooks/pre-tool-guard.sh`를 호출한다. 가드 로직은 한 벌만 유지한다.

의사결정 기록 훅(`PostToolUse`)도 같은 구조다. matcher만 다르다 — Claude Code는 `AskUserQuestion`, Codex는 `AskUserQuestion|request_user_input`을 함께 받는다. `request_user_input`이 EXPERIMENTAL이라 기본 모드에서 발화하지 않으면 기록도 남지 않는다.

### 훅 수동 배치

`hooks.json`의 command는 `bash ${CLAUDE_PLUGIN_ROOT:-.}/.claude/hooks/pre-tool-guard.sh`다. Claude Code는 이 변수를 채우지만 **Codex가 채운다는 보장이 없다.** 비면 `.`로 폴백해 작업 중인 프로젝트 디렉토리를 뒤지고, 스크립트를 찾지 못한 채 조용히 끝난다. 훅이 실패했다는 신호가 없으므로 verify 게이트 G3가 안 도는 것을 알아챌 방법도 없다.

`plugin_hooks`가 미완인 동안은 훅 설정을 손으로 배치한다. 경로에 변수를 쓰지 말고 **절대경로를 직접 적는다.**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "exec_command|local_shell|shell",
        "hooks": [
          {
            "type": "command",
            "command": "bash /절대/경로/oh-my-gx/.claude/hooks/pre-tool-guard.sh",
            "shell": "bash"
          }
        ]
      }
    ]
  }
}
```

배치한 뒤 **게이트가 도는지 확인**한다. 저장소 루트에서 아래를 실행하면 가드가 `deny` 판정을 내야 한다.

```bash
printf '{"tool_name":"exec_command","tool_input":{"command":"git push --force origin main"}}' \
  | bash .claude/hooks/pre-tool-guard.sh
```

기대 출력에 `"permissionDecision": "deny"`가 포함된다. 이건 스크립트가 정상인지만 보는 검사다 — **Codex가 실제로 훅을 호출하는지**는 Codex 세션에서 force-push를 시도해 차단되는지로 확인한다. 차단되지 않으면 `hooks.json`이 로드되지 않은 것이므로 `codex features list`로 `plugin_hooks` 상태를 확인한다.

## 제약

아래 두 항목은 Codex가 개발 중인 기능에 걸려 있다. `codex features list`로 현재 상태를 확인한 뒤 판단한다.

**`plugin_hooks`가 미완이다.** 플러그인이 훅을 번들로 배포하지 못한다. `hooks.json`을 만들어 두어도 Codex가 자동으로 읽지 않을 수 있으므로, verify 게이트(G3)를 쓰려면 사용자가 훅 설정을 직접 배치해야 한다. 게이트 로직 자체는 동작하지만 설치 절차가 한 단계 늘어난다.

**`request_user_input`이 EXPERIMENTAL이다.** `default_mode_request_user_input`이 아직 개발 중이라 기본 모드에서는 구조화된 선택지 질문이 뜨지 않을 수 있다. 이 경우 스킬의 확인 게이트는 자연어 질문으로 낮춰 진행하되, 승인 없이 다음 단계로 넘어가지 않는다는 계약은 그대로 지킨다.

## 동작하지 않는 것

아래는 실측으로 확인한 비호환이다. 스킬 본문을 고쳐야 해결된다.

### 번들 파일 경로 (해결됨)

예전에는 네 스킬(`dev`·`tdd`·`lens`·`setup`)이 자기 `phases/`·`references/` 파일을 `${CLAUDE_PLUGIN_ROOT:-.}/.claude/skills/{스킬}/...` 형태로 조립해 읽었다(27곳). Codex 스킬 루트에는 `.claude/skills/` 중간 경로가 없고 이 변수가 설정된다는 보장도 없어, 변수가 비면 작업 중인 프로젝트 루트를 뒤지다 파일을 찾지 못했다.

지금은 **그 지시가 적힌 파일의 위치를 기준으로 한 상대경로**를 쓴다.

```
Read("phases/phase-setup.md")                          # 같은 스킬 안
Read("../references/report-guide.md")                  # 같은 스킬의 다른 폴더
Read("../../gx-setup/references/project-type-hints.md")  # 형제 스킬
```

파일 사이의 상대 위치는 설치 위치와 무관하게 같으므로 두 하네스 모두에서 해석된다. `lint-consistency.sh`의 `[15/31]`이 절대경로 조립의 재발과 참조 대상 부재를 함께 검사한다.

**예외 하나가 남았다.** `gx-setup`이 읽는 config.json 템플릿은 스킬 디렉토리 밖(플러그인 루트의 `.claude/`)에 있다. Claude Code에서는 `../../config.json`이 맞지만, 스킬 디렉토리만 배포되는 Codex에서는 그 위치에 파일이 없다. 스킬은 Read 실패 시 사용자에게 수동 복사를 안내하고 다음 단계로 넘어가도록 되어 있다.

### 서브에이전트 배포

Codex `plugin.json`이 지원하는 컴포넌트 필드는 `skills`·`hooks`·`mcpServers`·`apps`다. `agents`가 없어 17개 에이전트 정의를 플러그인으로 실을 수 없다.

수동 배치도 통하지 않는다. `~/.codex/agents/`를 만들어 `agents/*.md`를 넣고 프롬프트를 렌더링해봤지만 로드되지 않았다(0.130 실측, 노출 0건). 역할 파일에 대응하는 `child_agents_md`가 아직 개발 중이고, codex-tools.md도 이 기능에 0.145+를 요구한다.

그래서 Codex에서는 **디스패치 프롬프트가 역할 정의를 통째로 짊어진다.** 스킬 본문의 `Task(...)` 호출에는 이미 상세한 `prompt` 블록이 붙어 있으므로 그것을 그대로 `spawn_agent`에 전달하고, 줄이거나 생략하지 않는다. 다만 `agents/*.md`에만 적힌 제약(도구 제한, 금지 사항)은 전달되지 않으니 그만큼 통제가 느슨해진다는 점을 감안한다.

### AGENTS.md 로드 범위

Codex는 작업 디렉토리의 `AGENTS.md`를 세션 프롬프트에 자동으로 싣는다(실측 확인 — `AGENTS.md instructions for <경로>` 형태로 주입된다). 다만 기준이 **작업 디렉토리**라, 이 저장소에서 작업할 때는 우리 `AGENTS.md`가 실리지만 플러그인을 설치해 다른 프로젝트에서 쓸 때는 그 프로젝트의 `AGENTS.md`가 실린다.

따라서 하네스 매핑을 이 문서에만 두면 설치 사용자에게 닿지 않는다. `gx-dev`는 SKILL.md에 "하네스 적응" 표를 직접 두고, `gx-tdd`는 `references/harness-adaptation.md`에 두고 SKILL.md가 실행 진입 시 가리킨다. 스킬 디렉토리는 어느 경로로 설치되든 항상 함께 배포된다.

### 스킬 상호 호출

Codex에는 `Skill()`에 해당하는 도구가 없다. 스킬은 프롬프트가 알려준 경로의 파일을 읽어 지시를 따르는 방식으로 쓴다. `Skill(skill: "oh-my-gx:gx-commit")` 44곳은 "해당 SKILL.md를 읽고 절차를 따른다"로 옮겨야 한다.

### allowed-tools 미전달

Codex는 이 필드를 모델 프롬프트에 넣지 않는다(측정에서 `allowed-tools`·`argument-hint` 모두 0건). `Task`·`AskUserQuestion`·`Skill`처럼 Codex에 없는 도구명이 오류를 내지 않는 이유이기도 하지만, Claude Code에서 얻던 권한 사전 승인 효과가 사라져 승인 프롬프트가 잦아질 수 있다.

## 실측 체크리스트

아래는 Codex 세션에서만 확인할 수 있는 항목이다. 확인 전에는 추측으로 값을 채우지 않는다 — 잘못된 매핑은 조용히 잘못된 모델로 디스패치하거나 설치를 실패시킨다.

**1. 훅 입력의 필드 구조.** `exec_command` 호출 시 훅 입력의 `tool_input`이 Claude Code와 동일하게 `command` 필드를 갖는가. `pre-tool-guard.sh`는 `tool_input.command` 추출에 실패하면 입력 전체를 검사 대상으로 폴백하므로, 구조가 다르면 무관한 명령이 차단되는 오탐이 난다. 확인 방법: Codex에서 훅 입력을 파일로 덤프하는 임시 훅을 걸고 실제 페이로드를 캡처한 뒤, `scripts/hook-tests.sh`의 Codex 케이스 페이로드와 대조한다. (가드 로직이 도구명에 의존하지 않는다는 것은 `hook-tests.sh`의 `exec_command`·`local_shell` 케이스로 이미 검증돼 있다 — 미확인 부분은 필드 구조뿐이다.)

**2. `spawn_agent`의 `agent_type` 값.** 이 인자는 필수인데 `agents/*.md`가 배포되지 않아 `oh-my-gx:reviewer` 같은 값은 존재하지 않는다. Codex가 제공하는 내장 agent type 목록을 확인하고, 우리 17석을 그중 무엇에 태울지 정한다. 역할 정의는 디스패치 프롬프트가 통째로 전달하므로, `agent_type`은 도구 권한과 격리 수준을 고르는 용도로만 쓴다. 확인한 목록과 매핑을 이 문서의 도구 매핑 표에 추가한다.

**3. spawn 허용 모델 목록.** 위 표는 `model`과 `reasoning_effort`를 함께 지정하라고 지시하지만 지정할 값을 알려주지 않는다. 확인 전까지 이 지시는 실행 불가 상태이며, **Codex에서는 17석의 모델 구분(reviewer는 opus, red-writer는 sonnet)이 사라진 채 동작한다.** 목록을 확인한 뒤 `high`/`mid`/`low` 세 티어에 대응하는 모델과 effort를 정해 표로 남긴다.

**4. Windows에서의 훅 실행.** `hooks.json`이 지정하는 `bash ...` 실행이 Windows Codex에서 동작하는지 확인하지 않았다. superpowers는 Windows용으로 `hooks/run-hook.cmd` 래퍼를 따로 두므로, 문제가 생기면 같은 방식을 참고한다.
