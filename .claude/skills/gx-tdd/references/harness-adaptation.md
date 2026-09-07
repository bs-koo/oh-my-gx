# gx-tdd 하네스 적응표

이 스킬의 본문은 Claude Code 도구명(`Task`·`AskUserQuestion`·`Skill`)으로 서술한다. Codex 등 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다. SKILL.md가 실행 진입 시 이 파일을 가리킨다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

| 이 문서의 표기 | Codex 대응 |
|----------------|-----------|
| `Task(subagent_type="oh-my-gx:{name}")` | `spawn_agent` — 격리가 필요하면 `fork_turns: "none"`, `model`과 `reasoning_effort`를 함께 지정한다. Codex는 `agents/` 역할 파일을 로드하지 않으므로 호출에 딸린 `prompt` 블록만으로 역할이 전달된다. 그 블록을 줄이거나 생략하지 않는다 |
| `AskUserQuestion` | `request_user_input`. 그 도구를 쓸 수 없으면 자연어로 묻되, **승인 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다 |
| `Skill(skill: "oh-my-gx:{name}")` | 해당 스킬의 `SKILL.md`를 읽어 그 절차를 수행한다 |

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.
