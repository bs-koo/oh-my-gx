# 스킬 라우팅 규칙

사용자가 자연어로 아래 의도를 표현하면, git 명령어를 직접 실행하지 말고 **반드시 해당 스킬을 호출**한다.

## 단일 스킬

| 사용자 표현 | 호출 스킬 |
|------------|----------|
| `커밋`, `커밋해`, `커밋해줘`, `commit` | `/gx-commit` |
| `PR`, `PR 올려`, `PR 생성`, `풀리퀘`, `pull request` | `/gx-pull-request` |
| `교차 리뷰`, `교차 검증`, `cross review`, `크로스 리뷰` | `/gx-cross-review` |

**gx-tdd·gx-ralph 파이프라인 진행 중 커밋/PR 의도 (verify 우회 방지):**
- 이 분기는 **사용자의 자연어 발화에만** 적용한다. 파이프라인 내부(phase-complete Step 1/2)의 Skill 호출에는 적용하지 않는다.
- 판별: 저장소 루트 기준 `.dev/{branch-slug}/state.md`(branch-slug = 브랜치명의 `/`를 `-`로 치환. **svn은 `.dev/.active`가 가리키는 `.dev/{slug}/state.md` — 포인터 부재·공백 시 `.dev/trunk/state.md` 폴백**)가 존재하고 `pipeline: gx-tdd` 또는 `pipeline: gx-ralph`이며 `status: in_progress`이고 `verify-status`가 `passed`가 아니면 — 단일 스킬이든 체이닝(`커밋하고 PR`)이든 커밋/PR로 직행시키지 않는다.
- **svn 프로젝트**는 gx-commit이 미지원(VCS 가드 종료)이라 스킬 층의 재확인 게이트가 없다 — PreToolUse 훅이 Claude의 `svn commit` 시도를 차단(verify 미통과 시 경고 포함)하지만 사용자의 터미널 커밋에는 개입하지 못하므로, 이 라우팅 분기가 사용자 안내의 핵심 방어다. `svn commit` 직접 실행 안내 전에 반드시 이 판별을 수행한다.
- **git 프로젝트**는 라우팅·스킬 층을 우회하더라도 PreToolUse 훅(`pre-tool-guard.sh` G3)이 `git commit` 시점에 verify 미통과를 감지해 사용자 확인(ask)을 요구한다 — 컨텍스트 압축·라우팅 실패와 무관하게 동작하는 최종 방어선.
- 대신 안내한다: "verify 게이트 미통과 상태입니다. `oh-my-gx:gx-verify`로 검증을 통과시킨 뒤 커밋/PR을 진행하거나, 전체 완료 절차(인수 검증 포함)는 `/gx-tdd --phase complete`를 사용하세요." 판별된 파이프라인이 `gx-ralph`(lock 없음 = 루프 중단 잔여 상태)이면 대신 안내한다: "gx-ralph 루프의 잔여 상태입니다. 러너 재실행으로 루프를 재개하거나, `oh-my-gx:gx-verify` 통과 후 커밋/PR을 진행하세요." 사용자가 verify 없이 명시적으로 고집하면 위험 수용을 확인하고 진행한다 (gx-commit/gx-pull-request의 경고 게이트가 재확인).
- `pipeline` 필드가 gx-tdd/gx-ralph가 아닌 state.md(gx-dev 등)에는 적용하지 않는다.

**gx-ralph 루프 예외:**
- `oh-my-gx:gx-ralph-iterate`(헤드리스 반복 세션)의 직접 `git commit`은 gx-commit 라우팅 강제의 **명시적 예외**다 — 헤드리스에는 gx-commit의 확인 게이트(AskUserQuestion)에 응답할 사용자가 없다. 커밋 메시지 컨벤션(`{type}: 메시지`, 트레일러 금지)은 동일하게 준수하며, verify 게이트는 훅 G3(`pipeline: gx-ralph` 인식)가 유지한다.
- 사용자가 루프 실행 중(`.dev/{branch-slug}/ralph.lock` 존재) 커밋/PR을 요청하면: 러너가 실행 중임을 안내하고, 루프 종료(또는 lock 해제 확인) 후 진행하도록 권한다.

## 개발 파이프라인 분기 (gx-dev vs gx-tdd)

| 사용자 표현 | 호출 스킬 |
|------------|----------|
| `개발해줘`, `구현해줘`, `만들어줘`, `기능 추가` | `/gx-dev` (일반 개발) |
| `TDD로`, `TDD로 개발`, `테스트 먼저`, `테스트 주도`, `RED-GREEN-REFACTOR`, `RGR` | `/gx-tdd` (TDD 강제) |

**분기 규칙:**
- 명시적 TDD 키워드(`TDD`, `테스트 먼저`, `테스트 주도`, `RED-GREEN-REFACTOR` 등)가 있으면 `/gx-tdd`를 호출한다.
- TDD 키워드가 없는 일반 개발 요청은 `/gx-dev`를 호출한다.
- 두 스킬은 commit/pull-request 공유 스킬을 동일하게 Skill 호출로 사용하고, setup phase 구조와 `context/` 참조 방식도 같다 (단, phase-setup은 각자 별도 파일이며 gx-context는 파이프라인이 호출하지 않는 독립 스킬이다). 차이는 구현(RGR 격리)·리뷰(spec→quality)·verify 게이트뿐이다.
- 애매하면 사용자에게 어느 방식으로 진행할지 확인한다.

### TDD 보조 스킬 (단독 호출)

아래 스킬은 명시적 키워드로 단독 호출할 수 있다. `gx-red`/`gx-green`/`gx-refactor`는 gx-tdd 파이프라인이 직접 호출하지 않고 `red-writer`/`green-coder`/`refactor-coder` 에이전트를 디스패치하므로 단독·체이닝 전용이며, `gx-verify`만 phase-complete가 Skill로 호출한다:

| 사용자 표현 | 호출 스킬 |
|------------|----------|
| `RED 단계`, `실패 테스트 먼저`, `실패 테스트 작성` | `/gx-red` |
| `GREEN 단계`, `테스트 통과시켜`, `최소 구현` | `/gx-green` |
| `리팩터 단계`, `REFACTOR 단계`, `중복 제거 정리` | `/gx-refactor` |
| `완료 검증`, `verify 게이트`, `테스트 실행 증거` | `/gx-verify` |

## 순차 스킬 체이닝

| 사용자 표현 | 실행 순서 |
|------------|----------|
| `커밋하고 PR`, `커밋 후 PR`, `커밋해주고 PR 올려`, `커밋하고 풀리퀘` | `/gx-commit` 완료 후 → `/gx-pull-request` 실행 |

**체이닝 규칙:**
- 첫 번째 스킬이 **성공적으로 완료**된 후에만 두 번째 스킬을 실행한다.
- 첫 번째 스킬이 실패하면 두 번째 스킬을 실행하지 않고 사용자에게 보고한다.
- 각 스킬은 독립적으로 호출한다 (Skill 도구 사용). git 명령어로 대체하지 않는다.

## 내부 파이프라인에서도 동일 적용

`/gx-dev`, `/gx-tdd` 등 파이프라인 스킬 내부에서 커밋/PR을 수행할 때도 위 규칙이 동일하게 적용된다.
파이프라인이 길어져 컨텍스트가 압축되더라도, 아래 명령어를 오케스트레이터가 직접 실행하지 않는다:

- **금지**: `git commit`, `gh pr create`, `git push` 직접 실행
- **필수**: `Skill(skill: "oh-my-gx:gx-commit")`, `Skill(skill: "oh-my-gx:gx-pull-request")` 호출
- **실패 시**: 직접 명령어로 우회하지 않고 사용자에게 보고한다.
- **예외**: gx-dev phase-complete의 "context 변경사항 자동 커밋"(Step 3~4)은 status.md 동기화를 전용 메시지 형식(`docs: [context] …`)으로 직접 `git add/commit/push`한다 — 기능 코드가 아닌 context 문서 동기화 전용이며 별도 push 정책을 따른다. gx-ralph-iterate의 헤드리스 직접 커밋과 함께 이 규칙의 명시적 예외다.
