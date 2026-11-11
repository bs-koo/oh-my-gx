# gx-pull-request verify 확인·Audit Summary 규칙

gx-pull-request SKILL.md의 Step 2 verify 경고 게이트와 PR 본문의 Audit Summary 작성에서 읽는다. 어떤 상태가 verify 미통과인지의 판정은 SKILL.md가 정본이다.

## verify 미통과 PR — Claude Code 확인은 한 번

- 훅(`pre-tool-guard.sh`)은 `git push`·`gh pr create`에 verify 확인을 하지 않는다(강제 push 차단만 한다). PR 쪽 확인은 SKILL.md 게이트의 질문 한 번이다.
- Claude Code에서 세션이 bypassPermissions 모드로 표시되어 있으면 묻지 않는다. 경고만 하고 Checklist에 "verify 미통과 PR" 또는 "verify 통과 후 변경 PR"을 적고 진행한다.
- 같은 코드에 대해 gx-commit이 실제 응답으로 위험 수용을 받아 `.dev/{branch-slug}/verify-risk-accepted`의 `tree:` 값이 현재 트리 지문(SKILL.md 지문 규약의 트리 성분)과 같으면 다시 묻지 않는다. "커밋하고 PR"에서 확인이 두 번 나오지 않게 하는 규칙이다. 경고와 Checklist 표기는 같다. 토큰 형식·기록 조건은 `../../gx-commit/references/verify-and-branch.md`를 따른다.
- Codex는 이 절을 쓰지 않는다. SKILL.md대로 gx-verify를 안내하고 PR 실행 전에 중단한다.

## 취소된 TDD 작업의 PR — 양 하네스

- SKILL.md verify 경고 게이트는 `status: in_progress`만 본다. 현재 브랜치 state가 `pipeline: gx-tdd`·`status: cancelled`(사용자가 작업 취소를 고름)이고 `verify-status`가 `passed`가 아니면 파이프라인을 그만둔 상태이므로 PR을 막지 않는다.
- Claude Code·Codex 모두 진행 여부를 묻지 않고 "취소된 TDD 작업 — verify를 통과하지 않은 코드입니다"를 경고한 뒤, PR 본문 Checklist에 `- [ ] verify 미통과(취소된 TDD 작업)`을 넣는다. 리뷰어가 검증되지 않은 변경임을 알게 하는 표기라 빼지 않는다.
- 취소를 verify 미통과 PR의 우회 수단으로 안내하지 않는다.

## Audit Summary의 기존 실패

- `--background`·`--extra-section` 파일의 `## Audit Summary` 절은 PR 본문 Checklist 앞에 `## Audit Summary`로 싣는다.
- 그 안의 `기존 실패 N건(이번 변경과 무관): {테스트 ID 목록}` 줄은 요약하거나 빼지 않고 건수와 ID 목록까지 그대로 옮긴다. 리뷰어가 이번 변경과 무관한 실패를 구분하는 근거다.
- 입력 파일에 그 줄이 없어도 현재 브랜치 state(`.dev/{branch-slug}/state.md`)의 `known-failures`가 1건 이상이면 `## Audit Summary`에 `- 기존 실패 N건(이번 변경과 무관): {테스트 ID, 최대 5개}` 한 줄을 넣는다. Audit Summary 절이 없으면 이 줄만으로 만든다. `known-failures`가 없거나 `[]`면 넣지 않는다.
