# gx-commit 보호 브랜치·verify 미통과 분기

gx-commit SKILL.md "사전 확인"의 레거시 선행 검사, 보호 브랜치 선행 중단과 verify 게이트(취소 상태 포함)에서 읽는다. 어떤 상태가 보호 브랜치·verify 미통과인지의 판정은 SKILL.md가 정본이고, 이 파일은 판정 뒤 묻고 진행하는 방법만 다룬다. Codex에서는 `AskUserQuestion`을 공통 codex-runtime의 질문 대기 계약으로 옮긴다 — 필수 질문은 pending 상태를 저장하고 실제 답변·결정 기록 전 다음 단계로 넘어가지 않는다.

## 보호 브랜치에서 작업 브랜치 만들기

현재 브랜치가 `main`/`master`/`develop`이면 빌드·스테이징·커밋 전에 한 번 묻는다. detached HEAD는 리베이스·bisect 중일 수 있으므로 묻지 않고 작업 브랜치가 필요하다고 안내하며 종료한다.

1. 제안 이름 `{type}/{설명}`을 만든다. `type`은 변경 내용에 맞는 `.claude/config.json` `conventions.branchTypes` 값, `설명`은 변경을 요약한 영문 소문자·숫자·`-` 2~4단어다.
2. 묻는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "작업 브랜치",
       question: "{현재 브랜치}에는 커밋할 수 없습니다. 작업 브랜치를 만들어 이 변경을 그대로 옮기고 커밋할까요?",
       multiSelect: false,
       options: [
         { label: "{제안 이름} 만들고 진행 (Recommended)", description: "미커밋 변경을 그대로 가지고 새 브랜치에서 커밋합니다" },
         { label: "다른 이름으로", description: "Other로 이동해서 {type}/{설명} 형식의 브랜치 이름을 입력해주세요" },
         { label: "중단", description: "브랜치를 만들지 않고 커밋을 끝냅니다" }
       ]
     }]
   )
   ```
3. 실제 답이 "만들고 진행"이거나 `{type}/{설명}` 형식(type은 `conventions.branchTypes`)의 이름일 때만 `git switch -c <이름>`을 실행한다. 미커밋 변경과 staged 상태는 새 브랜치로 그대로 따라간다. 형식이 맞지 않거나 `git switch -c`가 실패하면(잘못된 이름·이미 있는 브랜치) 원인을 보여주고 다시 묻는다. 만든 뒤에는 사전 확인을 처음부터 다시 수행한다(새 브랜치 기준 verify 게이트 포함).
4. "중단"이거나 답할 사용자가 없으면(헤드리스) 브랜치를 만들지 않고 "작업 브랜치가 필요합니다"로 종료한다. 답 없이 추측한 이름으로 브랜치를 만들지 않는다.

## verify 미통과 커밋 — Claude Code

SKILL.md verify 게이트가 미통과(또는 통과 뒤 코드 변경)로 판정한 뒤 **Claude Code에서만** 쓴다. Codex는 이 절을 쓰지 않고 SKILL.md대로 gx-verify를 안내하고 중단한다. 훅도 Codex 어댑터(`GX_HOOK_HARNESS=codex`)에서는 아래 완화를 모두 무시한다.

- **베이스 병합 커밋**: 병합이 진행 중이고(`git rev-parse -q --verify MERGE_HEAD` 성공) 미해결 경로(`git ls-files -u`)가 없으면 위험 수용을 묻지 않고 "베이스 병합 커밋 — 병합 후 verify를 다시 통과해야 커밋·PR 게이트가 닫힌다"를 알리고 진행한다. 훅 G3도 같은 조건에서만 문맥으로 허용한다. 미해결 경로가 남아 있으면 묻지 않고 빌드·스테이징 전에 중단하고 "충돌을 해결하고 `git add <경로>`로 해결 표시한 뒤 다시 커밋을 요청하세요"를 안내한다(인덱스 helper `stage`도 같은 상태를 거부한다).
- **이미 받은 위험 수용**: 같은 요청에서 사용자가 verify 미통과 상태 그대로의 커밋을 실제 응답으로 이미 골랐으면(gx-work `지금 상태 그대로 커밋` 등) 그 응답을 아래 "위험을 알고 커밋"으로 보고 다시 묻지 않는다. 추천값·추측·이전 요청의 답은 해당하지 않는다. 토큰 기록은 아래와 같다.
- **bypassPermissions 모드**: 세션이 bypassPermissions 모드로 표시되어 있으면(시스템 안내에 bypass permissions 모드가 활성으로 나온다) 묻지 않는다. "verify 미통과 커밋으로 진행합니다 — {사유}"를 경고하고 진행한다. 훅 G3도 이 모드에서는 묻지 않고 문맥 경고만 남긴다 — 서브에이전트가 직접 실행한 커밋도 문맥 경고만 남는다. 토큰은 쓰지 않는다.
- **그 밖의 모드**(default·acceptEdits·plan·auto·dontAsk): 한 번 묻는다.
   ```
   AskUserQuestion(
     questions: [{
       header: "verify 미통과",
       question: "검증(verify)을 통과하지 않은 코드입니다({사유}). 어떻게 할까요?",
       multiSelect: false,
       options: [
         { label: "검증 먼저 (Recommended)", description: "커밋하지 않고 oh-my-gx:gx-verify로 검증합니다" },
         { label: "위험을 알고 커밋", description: "'verify 미통과 커밋'으로 기록하고 지금 커밋합니다" }
       ]
     }]
   )
   ```
  - "검증 먼저" → 빌드·스테이징 전에 중단하고 `oh-my-gx:gx-verify`를 안내한다.
  - "위험을 알고 커밋"을 **실제 응답으로 받았을 때만** 토큰을 쓴다. 응답은 지금 받고, 기록은 커밋 실행 Step 5의 `assert-excluded`가 exit 0을 낸 뒤 `git commit` 직전에 인덱스 helper(`index-helper.md`)에 `{"action":"accept-risk","cwd":"<PROJECT_ROOT>"}`를 전달해 한다 — 그 전에 중단·실패하면 토큰이 남지 않는다. helper가 `.dev/{branch-slug}/verify-risk-accepted`에 `tree: <현재 트리 지문 12자>` 한 줄을 쓰고, 훅 G3는 이 트리가 지금 트리와 같으면 다시 묻지 않는다 — 확인은 이 질문 한 번이다. 응답 없이, 또는 helper가 아닌 방법으로 토큰을 쓰지 않는다. helper 실패는 커밋 중단 사유가 아니다(훅이 한 번 더 물을 뿐이다). 수용 뒤 코드가 바뀌면 트리가 달라 훅이 다시 묻는다. 토큰은 helper가 커밋에서 항상 뺀다.
  - auto·dontAsk 모드에서 토큰 없이 실행한 커밋은 훅 G3가 그대로 ask를 낸다(dontAsk는 확인이 필요한 호출을 거부하므로 사실상 막힌다).
- 진행한 커밋은 결과 보고에 "verify 미통과 커밋"(병합 커밋은 "베이스 병합 커밋")으로 적는다. gx-tdd 진행 중이면 오케스트레이터가 trust-ledger와 PR 본문에 그렇게 기록한다.

## 취소된 TDD 작업의 커밋 — 양 하네스

SKILL.md verify 게이트는 `status: in_progress`만 본다. 현재 브랜치 state가 `pipeline: gx-tdd`·`status: cancelled`(사용자가 작업 취소를 고름)이고 `verify-status`가 `passed`가 아니면 파이프라인을 그만둔 상태이므로 커밋을 막지 않는다. Claude Code·Codex 모두 위험 수용 질문·토큰 없이 "취소된 TDD 작업 — verify를 통과하지 않은 코드입니다"를 경고하고 진행하며, 결과 보고에 "verify 미통과(취소된 TDD 작업)"로 적는다. 이어서 PR을 만들면 gx-pull-request가 Checklist에 같은 표기를 남긴다. 취소를 verify 미통과 커밋의 우회 수단으로 안내하지 않는다.

## 제거된 Ralph 실행 기록 — 양 하네스

SKILL.md 레거시 선행 검사로 중단했을 때의 안내다. `pipeline: gx-ralph`는 제거된 레거시 실행이다. status가 in_progress이거나 ralph.lock이 남아 있으면 검증 표식과 무관하게 커밋 전에 중단한다. 기록을 보존하고 진행 중인 외부 프로세스 종료와 명시적 gx-tdd 전환을 안내하며 자동 재개·상태 변환을 하지 않는다.
