# Codex 하네스 호환 설계

작성일: 2026-08-28
브랜치: `feat/codex-compat-smoke`
상태: Phase 1(스모크 테스트) 완료

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

## 남은 작업

**Phase 2 — 표기 중립화.** 스킬 본문의 Claude Code API 직접 호출을 하네스 중립 서술로 바꾸고, 실제 API는 `harness-codex.md`에 위임한다. 대상은 `AskUserQuestion` 183건, `Task(`/`subagent_type` 각 48/47건, `Skill(` 44건이다. `lint-consistency.sh`의 `[2/24] 서브에이전트 도구명 통일`이 현재 Claude Code 표기를 강제하고 있으므로, 이 검사를 중립 표기 강제로 뒤집는 것이 재발 방지 수단이 된다.

**Phase 3 — 에이전트 모델 추상화.** `agents/`의 17개 정의가 `model: opus`/`sonnet`을 하드코딩한다. 하네스 중립 티어(고성능/표준)로 바꾸고 하네스별로 실제 모델에 매핑한다.

Phase 2는 스킬 본문이 무수정으로 인식된다는 이번 결과 덕분에 "동작시키기 위한 필수 작업"이 아니라 "두 하네스에서 같은 품질을 내기 위한 개선"으로 성격이 바뀌었다. 우선순위를 그에 맞게 조정한다.
