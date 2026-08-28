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

## 제약

아래 두 항목은 Codex가 개발 중인 기능에 걸려 있다. `codex features list`로 현재 상태를 확인한 뒤 판단한다.

**`plugin_hooks`가 미완이다.** 플러그인이 훅을 번들로 배포하지 못한다. `hooks.json`을 만들어 두어도 Codex가 자동으로 읽지 않을 수 있으므로, verify 게이트(G3)를 쓰려면 사용자가 훅 설정을 직접 배치해야 한다. 게이트 로직 자체는 동작하지만 설치 절차가 한 단계 늘어난다.

**`request_user_input`이 EXPERIMENTAL이다.** `default_mode_request_user_input`이 아직 개발 중이라 기본 모드에서는 구조화된 선택지 질문이 뜨지 않을 수 있다. 이 경우 스킬의 확인 게이트는 자연어 질문으로 낮춰 진행하되, 승인 없이 다음 단계로 넘어가지 않는다는 계약은 그대로 지킨다.

## 미검증 항목

`exec_command` 호출 시 훅 입력의 `tool_input`이 Claude Code와 동일하게 `command` 필드를 갖는지는 실행으로 확인하지 못했다(측정 당시 계정이 `deactivated_workspace` 상태였다). `pre-tool-guard.sh`는 `tool_input.command` 추출에 실패하면 입력 전체를 검사 대상으로 폴백하므로, 필드 구조가 다르면 오탐이 발생할 수 있다. Codex에서 처음 사용하기 전에 `scripts/hook-tests.sh`의 페이로드를 Codex 실제 입력으로 교체해 한 번 확인한다.
