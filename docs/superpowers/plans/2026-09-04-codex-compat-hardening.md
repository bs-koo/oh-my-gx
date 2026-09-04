# Codex 호환 보강 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex에서 verify 게이트가 조용히 무력화되는 경로를 문서로 막고, 남은 비호환을 실행 가능한 실측 체크리스트로 정리한다.

**Architecture:** Codex 비호환 항목은 두 종류다. **우리가 고칠 수 있는 것**(문서·절차)과 **하네스가 미완이라 실측 없이는 손댈 수 없는 것**(`agent_type` 값, spawn 허용 모델 목록, `plugin_hooks` 지원 여부). 이 계획은 앞의 것만 다룬다. 뒤의 것은 "선행 조사" 절에 확인 방법과 함께 남기고, 결과가 나온 뒤 별도 계획으로 옮긴다. 추측으로 매핑 표를 채우면 사용자를 잘못된 설정으로 이끈다.

**Tech Stack:** Bash (린트 스크립트), Markdown (하네스 규칙 문서)

**Spec:** `https://claude.ai/code/artifact/0d15c9c7-8d25-4de5-9117-4f6428238f53` (Fable 도입 설계안 2판 — 설계 G "Codex 보강")

## Global Constraints

- **선행 조건:** `2026-09-04-prompt-guide-alignment.md`가 머지되어 린트 분모가 `29`인 상태를 전제한다. 그 계획을 건너뛰고 이 계획을 먼저 실행한다면 아래 `sed` 구문의 분모를 현재 값으로 바꾼다.
- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (훅 G1). `feat/codex-compat-hardening` 브랜치를 생성한다.
- **커밋**: `git commit`을 직접 실행하지 않는다. `Skill(skill: "oh-my-gx:gx-commit")`으로 커밋한다.
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 **둘 다 통과**한 상태로 끝난다.
- **측정 기준**: 이 문서의 Codex 관련 사실은 `codex-cli 0.130.0` 실측 기준이다. 실행 시점에 `codex --version`이 다르면 먼저 실제 도구 목록을 확인한다.
- **추측 금지**: 확인하지 못한 Codex 도구 파라미터 값, 모델 이름, 기능 플래그를 문서에 쓰지 않는다.
- **`sed -i` 이식성**: 아래 단계는 GNU sed(Linux·Git Bash)를 전제한다. macOS의 BSD sed에서는 `sed -i '' 's|...|...|g'`처럼 빈 확장자 인자가 필요하다. 치환 후 `grep -c`로 결과를 확인한다.

---

## File Structure

| 파일 | 책임 | 태스크 |
|------|------|--------|
| `.claude/rules/harness-codex.md` | 훅 수동 배치 절차 + 실측 체크리스트 | 1·2 |
| `scripts/lint-consistency.sh` | 두 절의 존재를 계약으로 고정 (`[30]`) | 1·2 |

---

### Task 1: 훅 수동 배치 절차를 문서화한다

**근거:** `hooks.json`의 command가 `bash ${CLAUDE_PLUGIN_ROOT:-.}/.claude/hooks/pre-tool-guard.sh`다. Codex에서 이 변수가 채워지지 않으면 `.`로 폴백해 **작업 디렉토리를 뒤지다 스크립트를 못 찾고 조용히 아무 일도 하지 않는다.** 게다가 `plugin_hooks` 기능 자체가 미완이라 Codex가 `hooks.json`을 자동으로 읽는다는 보장도 없다. 결과는 하나다 — **verify 게이트 G3가 발화하지 않는데 사용자가 그 사실을 모른다.**

`scripts/hook-tests.sh`는 이 층을 검증하지 못한다. 테스트는 `.claude/hooks/pre-tool-guard.sh`를 직접 호출하므로 `hooks.json`의 경로 해석을 거치지 않는다. 가드 로직은 이미 Codex 도구명(`exec_command`·`local_shell`)으로 검증돼 있으나, **가드가 호출되기까지의 경로**는 검증 대상 밖이다.

**Files:**
- Modify: `.claude/rules/harness-codex.md` (`## 훅` 섹션 끝)
- Modify: `scripts/lint-consistency.sh` (분모 29→30, 검사 `[30]` 추가)

**Interfaces:**
- Consumes: 린트 분모 `29` (계획 1이 남긴 값)
- Produces: 린트 분모 `30`. Task 2가 같은 `[30/30]` 블록에 검사 줄을 추가한다.

- [ ] **Step 1: 작업 브랜치 생성**

```bash
git checkout -b feat/codex-compat-hardening
git branch --show-current
```

기대: `feat/codex-compat-hardening` 출력.

- [ ] **Step 2: 린트 분모를 29에서 30으로 올리고 헤더에 항목을 추가한다**

```bash
sed -i 's|/29\]|/30]|g' scripts/lint-consistency.sh
```

헤더 주석의 마지막 항목(`# 29. 헤드리스 조기 종료 방지 철칙 ...`) 뒤에 추가한다:

```bash
# 30. Codex 훅 배치·실측 계약 (수동 배치 절차·미검증 항목 체크리스트)
```

- [ ] **Step 3: 실패하는 린트 검사를 추가한다**

린트 스크립트의 마지막 검사 블록 뒤, `if [ "$FAIL" -ne 0 ]; then` 앞에 추가한다:

```bash

echo "[30/30] Codex 훅 배치·실측 계약"
# hooks.json의 ${CLAUDE_PLUGIN_ROOT} 폴백은 Codex에서 조용히 실패할 수 있고,
# hook-tests.sh는 스크립트를 직접 호출하므로 이 층을 검증하지 못한다.
# 절차가 문서에 없으면 사용자는 G3가 안 도는 것을 알 방법이 없다.
CODEX_MD=.claude/rules/harness-codex.md
grep -qF '## 훅 수동 배치' "$CODEX_MD" \
  || fail "훅 수동 배치 절차 누락: $CODEX_MD"
grep -qF 'CLAUDE_PLUGIN_ROOT' "$CODEX_MD" \
  || fail "경로 변수 폴백 위험 설명 누락: $CODEX_MD"
grep -qF '게이트가 도는지 확인' "$CODEX_MD" \
  || fail "훅 동작 확인 절차 누락: $CODEX_MD"
[ "$FAIL" -eq 0 ] && ok "Codex 훅 배치·실측 계약 확인"
```

- [ ] **Step 4: 린트를 실행해 실패를 확인한다**

```bash
bash scripts/lint-consistency.sh
```

기대: `[30/30] Codex 훅 배치·실측 계약` 아래에 FAIL 3줄, 종료 코드 1.

- [ ] **Step 5: harness-codex.md에 배치 절차를 추가한다**

`.claude/rules/harness-codex.md`의 `## 훅` 섹션 마지막 문단을 찾는다:

```markdown
의사결정 기록 훅(`PostToolUse`)도 같은 구조다. matcher만 다르다 — Claude Code는 `AskUserQuestion`, Codex는 `AskUserQuestion|request_user_input`을 함께 받는다. `request_user_input`이 EXPERIMENTAL이라 기본 모드에서 발화하지 않으면 기록도 남지 않는다.
```

바로 뒤에 다음 절을 추가한다:

```markdown
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

```

- [ ] **Step 6: 린트와 훅 테스트를 실행해 통과를 확인한다**

```bash
bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh
```

기대: `ok: Codex 훅 배치·실측 계약 확인`과 `정합성 린트 통과`, 훅 테스트 통과.

- [ ] **Step 7: 커밋**

`Skill(skill: "oh-my-gx:gx-commit")`를 호출한다. 커밋 메시지 방향:

```
docs: Codex 훅 수동 배치 절차와 동작 확인 방법을 추가한다
```

---

### Task 2: 미검증 항목을 실행 가능한 체크리스트로 바꾼다

**근거:** `harness-codex.md`의 `## 미검증 항목` 절은 두 가지를 남겨 뒀는데, 그중 하나는 이미 해소됐다. `scripts/hook-tests.sh`에 Codex 도구명 케이스(`exec_command`·`local_shell`, `capture-decision`의 `request_user_input`)가 들어 있어 **가드 로직이 도구명에 의존하지 않는다는 것은 검증돼 있다.** 남은 것은 `tool_input.command`의 **필드 구조**가 실제 Codex 입력에서 같은지다.

여기에 이 대화에서 새로 드러난 두 갭을 더한다. `spawn_agent`의 `agent_type`에 무엇을 넣을지 정의가 없고, spawn 허용 모델 목록을 알 수 없어 `model`·`reasoning_effort`를 지정하라는 지시가 실행 불가 상태다. 둘 다 Codex 세션에서만 확인할 수 있으므로 **추측으로 매핑을 채우지 않고 확인 절차만 남긴다.**

**Files:**
- Modify: `.claude/rules/harness-codex.md` (`## 미검증 항목` 절 전체 교체)
- Modify: `scripts/lint-consistency.sh` (`[30/30]` 블록에 검사 2줄 추가)

**Interfaces:**
- Consumes: 린트 `[30/30]` 블록 (Task 1이 만든 것). 분모는 그대로 `30`이다.
- Produces: 없음 (이 계획의 마지막 태스크)

- [ ] **Step 1: 린트 검사 2줄을 추가한다**

`scripts/lint-consistency.sh`의 `[30/30] Codex 훅 배치·실측 계약` 블록에서 이 줄을 찾는다:

```bash
grep -qF '게이트가 도는지 확인' "$CODEX_MD" \
  || fail "훅 동작 확인 절차 누락: $CODEX_MD"
```

바로 뒤, `[ "$FAIL" -eq 0 ] && ok ...` 앞에 추가한다:

```bash
# agent_type·모델 목록은 Codex 세션에서만 확인 가능하다. 추측으로 채우면 잘못된 설정을 배포한다.
grep -qF '## 실측 체크리스트' "$CODEX_MD" \
  || fail "실측 체크리스트 절 누락: $CODEX_MD"
grep -qF 'agent_type' "$CODEX_MD" \
  || fail "agent_type 확인 항목 누락: $CODEX_MD"
```

- [ ] **Step 2: 린트를 실행해 실패를 확인한다**

```bash
bash scripts/lint-consistency.sh
```

기대: `[30/30]` 아래에 FAIL 1줄 (`실측 체크리스트 절 누락`). `agent_type`은 기존 문서에 이미 등장하므로 통과한다.

- [ ] **Step 3: 미검증 항목 절을 체크리스트로 교체한다**

`.claude/rules/harness-codex.md`의 `## 미검증 항목` 절 전체 — 다음 두 문단 — 를 찾는다:

```markdown
`exec_command` 호출 시 훅 입력의 `tool_input`이 Claude Code와 동일하게 `command` 필드를 갖는지는 실행으로 확인하지 못했다(측정 당시 계정이 `deactivated_workspace` 상태였다). `pre-tool-guard.sh`는 `tool_input.command` 추출에 실패하면 입력 전체를 검사 대상으로 폴백하므로, 필드 구조가 다르면 오탐이 발생할 수 있다. Codex에서 처음 사용하기 전에 `scripts/hook-tests.sh`의 페이로드를 Codex 실제 입력으로 교체해 한 번 확인한다.

`hooks.json`이 지정하는 `bash ...` 실행이 Windows Codex에서 동작하는지도 확인하지 않았다. superpowers는 Windows용으로 `hooks/run-hook.cmd` 래퍼를 따로 두고 있으므로, 문제가 생기면 같은 방식을 참고한다.
```

다음으로 교체한다:

```markdown
## 실측 체크리스트

아래는 Codex 세션에서만 확인할 수 있는 항목이다. 확인 전에는 추측으로 값을 채우지 않는다 — 잘못된 매핑은 조용히 잘못된 모델로 디스패치하거나 설치를 실패시킨다.

**1. 훅 입력의 필드 구조.** `exec_command` 호출 시 훅 입력의 `tool_input`이 Claude Code와 동일하게 `command` 필드를 갖는가. `pre-tool-guard.sh`는 `tool_input.command` 추출에 실패하면 입력 전체를 검사 대상으로 폴백하므로, 구조가 다르면 무관한 명령이 차단되는 오탐이 난다. 확인 방법: Codex에서 훅 입력을 파일로 덤프하는 임시 훅을 걸고 실제 페이로드를 캡처한 뒤, `scripts/hook-tests.sh`의 Codex 케이스 페이로드와 대조한다. (가드 로직이 도구명에 의존하지 않는다는 것은 `hook-tests.sh`의 `exec_command`·`local_shell` 케이스로 이미 검증돼 있다 — 미확인 부분은 필드 구조뿐이다.)

**2. `spawn_agent`의 `agent_type` 값.** 이 인자는 필수인데 `agents/*.md`가 배포되지 않아 `oh-my-gx:reviewer` 같은 값은 존재하지 않는다. Codex가 제공하는 내장 agent type 목록을 확인하고, 우리 17석을 그중 무엇에 태울지 정한다. 역할 정의는 디스패치 프롬프트가 통째로 전달하므로, `agent_type`은 도구 권한과 격리 수준을 고르는 용도로만 쓴다. 확인한 목록과 매핑을 이 문서의 도구 매핑 표에 추가한다.

**3. spawn 허용 모델 목록.** 위 표는 `model`과 `reasoning_effort`를 함께 지정하라고 지시하지만 지정할 값을 알려주지 않는다. 확인 전까지 이 지시는 실행 불가 상태이며, **Codex에서는 17석의 모델 구분(reviewer는 opus, red-writer는 sonnet)이 사라진 채 동작한다.** 목록을 확인한 뒤 `high`/`mid`/`low` 세 티어에 대응하는 모델과 effort를 정해 표로 남긴다.

**4. Windows에서의 훅 실행.** `hooks.json`이 지정하는 `bash ...` 실행이 Windows Codex에서 동작하는지 확인하지 않았다. superpowers는 Windows용으로 `hooks/run-hook.cmd` 래퍼를 따로 두므로, 문제가 생기면 같은 방식을 참고한다.
```

- [ ] **Step 4: 린트와 훅 테스트를 실행해 통과를 확인한다**

```bash
bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh
```

기대: `ok: Codex 훅 배치·실측 계약 확인`과 `정합성 린트 통과`, 훅 테스트 통과.

- [ ] **Step 5: 기존 Codex 린트가 깨지지 않았는지 확인한다**

```bash
bash scripts/lint-consistency.sh 2>&1 | grep -E '^\[(15|24)/30\]' -A2
```

기대: `[15/30] 번들 경로 규약`과 `[24/30] 하네스·복수 타입 검증 계약` 모두 FAIL 없음.

- [ ] **Step 6: 커밋**

`Skill(skill: "oh-my-gx:gx-commit")`를 호출한다. 커밋 메시지 방향:

```
docs: Codex 미검증 항목을 실측 체크리스트로 정리한다
```

---

## 마무리

- [ ] **CHANGELOG 갱신 및 PR**

`CHANGELOG.md`에 기록한 뒤 `Skill(skill: "oh-my-gx:gx-pull-request")`를 호출한다. 버전을 올린다면 `.claude/rules/release.md`에 따라 세 매니페스트의 `version`을 함께 갱신한다 (린트 `[1/30]`이 검사).

---

## 선행 조사 — 이 계획이 다루지 않는 것

아래 두 항목은 **위 체크리스트의 2·3번이 해소된 뒤에** 별도 계획으로 작성한다. 지금 계획에 넣으면 확인하지 못한 값을 문서에 쓰게 된다.

**`agentTiers` 축 신설.** `config.json`에 에이전트별 논리 티어(`high`/`mid`/`low`) 맵을 두고, 하네스별 매핑 표로 실제 모델·effort를 결정하는 설계다. Codex에는 frontmatter 층이 없어 이 맵이 모델 의도를 표현할 유일한 자리가 되지만, **Codex 쪽 매핑을 채우려면 체크리스트 3번의 결과가 필요하다.** Claude Code 절반만 먼저 넣는 것은 이득이 적다 — 그쪽은 frontmatter가 이미 같은 역할을 한다.

**`agent_type` 매핑 표 추가.** 체크리스트 2번의 결과를 도구 매핑 표에 반영하는 작업이다. 확인된 목록 없이는 한 줄도 쓸 수 없다.

두 항목의 설계 근거는 Spec 문서의 "설계 A"와 "설계 G"에 있다. 실측이 끝나면 그 절을 실제 값으로 채워 계획으로 옮긴다.
