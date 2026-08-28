# Codex 하네스 호환 설계

작성일: 2026-08-28
브랜치: `feat/codex-compat-smoke`
상태: Phase 0·1 완료, Phase 2 축소 실행, Phase 3 폐지

## 배경

oh-my-gx는 Claude Code 전용으로 작성되어 있다. 다른 하네스에서도 쓰려면 무엇을 바꿔야 하는지 확인하기 위해, 타깃을 Codex + Claude Code 둘로 좁혀 실측했다.

## 실측 결과 (Codex CLI 0.130.0)

Codex는 Claude Code의 플러그인 규격을 상당 부분 그대로 채택했다. 바이너리에 `CLAUDE_PLUGIN_ROOT` 문자열이 존재하는 것이 호환 레이어의 직접 증거다.

| 영역 | Claude Code | Codex | 판정 |
|------|-------------|-------|------|
| 스킬 파일 | `SKILL.md` + frontmatter | 동일 (`allowed-tools`·`argument-hint`·`user-invocable`·`disable-model-invocation`) | 동일 |
| 스킬 경로 | `.claude/skills/` | `.codex/skills/`·`~/.codex/skills/`, 매니페스트로 경로 지정 가능 | 지정으로 공유 |
| 매니페스트 | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | 파일만 분리 |
| 마켓플레이스 | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | 파일만 분리 |
| 훅 이벤트 | `PreToolUse` 외 | 동일 | 동일 |
| 훅 입출력 | `tool_input`·`permissionDecision`·`allow`/`ask`/`deny` | 동일 | 동일 |
| 셸 도구명 | `Bash` | `exec_command`·`local_shell` | **다름** |
| 서브에이전트 | `Task(subagent_type=)` | `spawn_agent`(`agent_type`·`fork_turns`) + `wait_agent`·`followup_task` | 대응 가능 |
| 사용자 질문 | `AskUserQuestion` | `request_user_input` (선택지 지원) | 대응 가능 |

## 검증 방법과 결과

`codex debug prompt-input`은 API 호출 없이 모델에게 전달되는 프롬프트를 렌더링한다. 스킬 인식 여부를 이것으로 측정했다.

1. **Baseline**: gx 스킬 인식 0건 (시스템 스킬 3개만 노출)
2. **스킬 배치 후**: `.claude/skills/*`를 무수정으로 배치 → **gx 스킬 17개 전부 인식**. 한국어 description과 frontmatter 모두 정상 파싱
3. **훅 회귀**: `scripts/hook-tests.sh` 통과. Codex 도구명(`exec_command`·`local_shell`) 페이로드 케이스 2건을 추가해 함께 통과
4. **정합성 린트**: `scripts/lint-consistency.sh` 24/24 통과 (기존 계약 무손상)

핵심 결론은 **스킬 본문을 고치지 않아도 Codex가 그대로 읽는다**는 것이다. 앞서 이식 비용의 대부분으로 추정했던 스킬 파일 변환이 불필요하다.

## 산출물

| 파일 | 역할 |
|------|------|
| `.codex-plugin/plugin.json` | Codex 매니페스트. `skills`가 `./.claude/skills/`를 가리켜 소스를 단일 유지 |
| `.agents/plugins/marketplace.json` | Codex 마켓플레이스. `source.url`이 `./`로 저장소 루트를 가리킴 |
| `hooks.json` | Codex 훅 설정. matcher만 다르고 같은 `pre-tool-guard.sh`를 호출 |
| `AGENTS.md` | 하네스 공통 진입 문서 |
| `.claude/rules/harness-codex.md` | 도구 매핑·제약·미검증 항목 |
| `scripts/hook-tests.sh` | Codex 도구명 회귀 케이스 2건 추가 |

## 제약

**`plugin_hooks`가 개발 중이다.** 플러그인이 훅을 번들로 배포하지 못한다. verify 게이트(G3)를 쓰려면 사용자가 훅 설정을 직접 배치해야 한다. 게이트 로직 자체는 동작한다.

**`codex plugin`에 설치 서브커맨드가 없다.** 마켓플레이스 등록까지만 CLI로 되고, 플러그인 활성화는 TUI에서 한다. 이번 검증에서 마켓플레이스 등록만으로는 스킬이 노출되지 않았고, 스킬 디렉토리 직접 배치로 노출을 확인했다.

**`request_user_input`이 EXPERIMENTAL이다.** `default_mode_request_user_input`이 개발 중이라 기본 모드에서 구조화된 선택지가 뜨지 않을 수 있다.

## 미검증 항목

`exec_command` 실행 시 훅 입력의 `tool_input`이 Claude Code와 같은 `command` 필드를 갖는지 런타임으로 확인하지 못했다. 측정 당시 Codex 계정이 `deactivated_workspace`(402)여서 세션이 도구 실행 단계에 도달하지 못했다. `pre-tool-guard.sh`는 추출 실패 시 입력 전체를 검사 대상으로 폴백하므로, 구조가 다르면 오탐이 발생할 수 있다. 계정이 활성화되면 프로브 훅으로 실제 입력을 캡처해 확인한다.

## 추가 실측 — 동작하지 않는 것

스모크 테스트 이후 프롬프트 렌더링 결과를 더 분석해 아래 비호환을 확인했다. 스킬 인식과 별개로, 실제 실행을 막는 지점들이다.

| 항목 | 영향 | 원인 |
|------|------|------|
| 번들 파일 경로 | **해결됨** — 상대경로 전환 (27곳) | `${CLAUDE_PLUGIN_ROOT:-.}/.claude/skills/...` 조립. Codex 구조에 `.claude/skills/` 중간 경로가 없고 변수 설정도 미보장 |
| 서브에이전트 배포 | 17개 에이전트 수동 배치 | Codex `plugin.json`에 `agents` 필드가 없다 (`skills`·`hooks`·`mcpServers`·`apps`만) |
| 스킬 상호 호출 | `Skill()` 44곳 | Codex에 등가 도구 없음. 파일을 읽어 따르는 방식 |
| `allowed-tools` | 권한 사전 승인 효과 없음 | 모델 프롬프트에 전달되지 않음 (측정 0건) |

번들 파일 경로가 가장 시급하다. 파이프라인 4개가 첫 phase 로드에서 멈추기 때문이다. 반면 나머지 13개 스킬은 번들 파일에 의존하지 않아 그대로 동작한다.

해법은 이미 저장소 안에 있다. `gx-humanizer`가 `references/patterns-ko.md` 형태의 **스킬 기준 상대경로**를 쓰고 있고, superpowers도 `CLAUDE_PLUGIN_ROOT`를 한 번도 쓰지 않는다. 상대경로는 설치 위치와 무관하게 해석되므로 두 하네스 모두에서 동작한다.

## 남은 작업

**Phase 0 — 번들 경로 정규화 (완료).** `${CLAUDE_PLUGIN_ROOT:-.}/.claude/skills/{스킬}/` 조립 27곳을 스킬 기준 상대경로로 바꾼다. `lint-consistency.sh`의 `[15/24] 플러그인 번들 경로 규약`이 현재 이 조립을 **요구**하고 있으므로 검사도 함께 뒤집는다. 검사는 절대경로 조립 재발과 참조 대상 부재를 함께 본다. 전환 후 상대경로 13건이 모두 실제 파일을 가리키는 것을 확인했고, Codex 스킬 루트 구조에서도 해석됨을 검증했다. `gx-setup`의 config.json 템플릿만 스킬 밖에 있어 Codex에서는 수동 복사 안내로 대체한다.

**Phase 2 — 표기 중립화 (축소 실행).** 당초 계획은 `AskUserQuestion` 183건, `Task(`/`subagent_type` 각 48/47건, `Skill(` 44건을 하네스 중립 서술로 전면 치환하는 것이었다. 아래 두 실측이 이 계획을 바꿨다.

첫째, Codex는 `allowed-tools`를 모델 프롬프트에 넣지 않는다. `Task`·`AskUserQuestion` 같은 없는 도구명이 오류를 내지 않으므로, 표기를 그대로 두어도 실행이 막히지 않는다. 둘째, 계정이 `deactivated_workspace` 상태라 전면 치환의 효과를 측정할 수 없다. 측정 없이 240건을 건드리는 것은 위험 대비 이득이 낮다.

그래서 전면 치환 대신 **`gx-dev`·`gx-tdd`의 SKILL.md에 "하네스 적응" 매핑 표를 넣는 것으로 대체했다.** 이 둘이 전체 표기의 63%(82+69건)를 차지하고 서브에이전트·스킬 호출의 대부분을 담당한다. 나머지 스킬은 `AskUserQuestion` 위주여서, 도구가 없으면 모델이 자연어 질문으로 대체한다. 매핑 표에는 "도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다"를 명시해 확인·검증 계약이 하네스와 무관하게 유지되도록 했다.

전면 치환은 계정이 활성화되어 전후 비교가 가능해진 뒤에 재검토한다.

**Phase 3 — 에이전트 모델 추상화 (폐지).** `agents/`의 17개 정의를 하네스 중립 티어로 바꾸려 했으나, 전제가 성립하지 않는다. Codex는 `agents/*.md` 자체를 로드하지 않으므로(아래 실측) frontmatter의 `model` 필드에 매핑할 대상이 없다. 모델 지정은 `spawn_agent` 호출 파라미터의 문제이고, 그 지침은 Phase 2의 매핑 표에 흡수했다.

**개별 과제 — 서브에이전트 배포 (Codex 기능 대기).** `~/.codex/agents/`에 역할 파일을 넣어도 로드되지 않음을 실측했다(0.130, 노출 0건). `child_agents_md`가 개발 중이라 우리 쪽에서 취할 조치가 없다. 그동안은 디스패치 `prompt` 블록이 역할 정의를 대신한다.
