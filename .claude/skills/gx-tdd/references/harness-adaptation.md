# gx-tdd 하네스 적응표

SKILL.md가 실행 진입 시 이 파일을 가리킨다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("../../gx-dev/references/codex-runtime.md")`를 실행한다. 상대경로는 이 파일의 위치 기준이다.
역할 index의 실제 경로는 **읽은 runtime.md 파일과 같은 디렉토리**의 `codex-roles/index.json`이다. red-writer·security-auditor 등 역할 파일은 그 index의 `file`을 같은 `codex-roles/`에 붙여 읽는다. 소비 프로젝트 `.claude/codex-roles/`를 찾지 않는다.

| 이 문서의 표기 | Codex 대응 |
|----------------|-----------|
| `Task(subagent_type="oh-my-gx:{name}")` | 공통 실행 규약의 `codex-roles/index.json`과 역할 본문·도구 제약을 읽어 `spawn_agent`의 message에 태스크 prompt 전문과 함께 전달한다. 격리 시 `fork_turns: "none"`을 쓴다 |
| `AskUserQuestion` | 공통 질문 대기 계약으로 변환한다. 실제 모드·용도가 허용하는 `request_user_input`·`request_user_input_async` 또는 자연어를 사용한다. 필수 질문은 pending 기록·실제 답변 전 진행하지 않는다. async 반환은 답변이 아니며 본문·선택지를 표시한다 |
| `Skill(skill: "oh-my-gx:{name}")` | 해당 스킬의 `SKILL.md`를 읽어 그 절차를 수행한다 |

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.
