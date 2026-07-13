---
name: gx-ralph-iterate
version: 1.0.0
description: "gx-ralph 루프의 반복 1회 실행 스킬 (헤드리스 전용) - 미완료 AC 1건을 구현·verify·커밋한다. 러너(scripts/gx-ralph.sh)가 호출하며 사용자가 직접 호출하지 않는다."
argument-hint: ""
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Task
  - Skill
  - Bash(git *)
  - Bash(./gradlew *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(pnpm *)
  - Bash(yarn *)
  - Bash(bun *)
  - Bash(pytest *)
  - Bash(go *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(mkdir *)
  - Bash(pwd *)
  - Bash(wc *)
  - Bash(grep *)
---

# gx-ralph-iterate

> **이 스킬**: gx-ralph-iterate — Ralph 루프의 반복 1회 (헤드리스 전용)
> **호출 시 주의**: 이 스킬 내에서 다른 스킬을 호출할 때 반드시 `oh-my-gx:` 접두사를 사용한다.

외부 러너(`scripts/gx-ralph.sh`)가 매 반복 새 세션에서 호출하는 스킬. **미완료 AC 정확히 1건**을 구현하고, verify를 통과시키고, 커밋하고, 원장을 갱신한 뒤 종료 계약을 출력하고 끝난다.

상태 계약(ac-status.json 스키마·state.md 필드·종료 계약·회귀 정책)의 정본은 `gx-ralph/SKILL.md`의 "상태 계약 (SSOT)" 섹션이다. 이 파일의 계약 표기는 그 사본이다 (드리프트 주의 — 함께 갱신).

## 철칙 (Iron Law)

1. **루프당 AC 1건만.** 여러 AC를 한 번에 처리하지 않는다. "간단하니까 두 개"도 금지.
2. **질문 금지.** 이 세션은 헤드리스다 — AskUserQuestion 도구가 존재하지 않으며, 사용자도 없다. 판단 불가 상황은 질문이 아니라 `<ralph>BLOCKED: 사유</ralph>`로 종료한다.
3. **브랜치 조작 금지.** `git checkout`, `git pull`, `git rebase`, `git merge`, setup 절차를 실행하지 않는다. 러너가 준비한 브랜치 그대로 작업한다. `.claude/rules/git-workflow.md`의 "매 요청 시작 전" 브랜치 복귀·pull 규칙은 이 세션에 적용하지 않는다.
4. **verify 없이 커밋 금지.** 커밋은 `verify-status: passed` 기록 후에만.
5. **종료 계약을 응답의 마지막 줄에 정확히 한 번** 출력한다. 지시 인용 등으로 계약 문자열을 본문 중간에 쓰지 않는다.

## 실행 절차

### Step 0: 가드 (하나라도 실패 시 즉시 BLOCKED 종료)

1. `DEV_DIR = .dev/{branch-slug}` 계산 (`git branch --show-current` → `/`를 `-`로 치환).
2. 브랜치 assert:
   - 현재 브랜치가 빈 값(detached HEAD) → `<ralph>BLOCKED: detached HEAD</ralph>`
   - 현재 브랜치가 `main`/`master`/`develop` → `<ralph>BLOCKED: 보호 브랜치에서 실행됨</ralph>`
3. `${DEV_DIR}/state.md` Read. 파싱 실패 또는 `pipeline: gx-ralph`가 아니거나 `status: in_progress`가 아니면 → `<ralph>BLOCKED: state.md 부재/불일치</ralph>`
4. state.md의 `branch` 필드와 현재 브랜치가 다르면 → `<ralph>BLOCKED: 브랜치 불일치 (state: {A}, 현재: {B})</ralph>`
5. `${DEV_DIR}/ac-status.json` Read. JSON 파싱 실패 → `<ralph>BLOCKED: ac-status.json 파싱 실패</ralph>`

### Step 1: AC 선택

1. `acs` 배열에서 `passes: false`이고 `attempts < 3`인 **첫 항목**을 선택한다.
2. 선택할 항목이 없으면:
   - 전 항목이 `passes: true` → `<ralph>COMPLETE</ralph>` 출력 후 종료.
   - `passes: false`인데 전부 `attempts >= 3` → `<ralph>BLOCKED: {해당 AC id 목록} 3회 연속 실패 — 사람 판단 필요</ralph>` 출력 후 종료.

### Step 2: 구현 (에이전트 디스패치)

컨텍스트 수집: `${DEV_DIR}/prd.md`의 해당 AC 관련 요구사항, `${DEV_DIR}/design.md`(있으면 해당 AC 관련 섹션), `${DEV_DIR}/codemap.md`(있으면), `${DEV_DIR}/progress.txt` 마지막 20줄(이전 반복의 학습 — 특히 같은 AC의 `last_error`가 있으면 반드시 포함).

state.md의 `origin`에 따라 디스패치한다 (`subagent_type`은 `oh-my-gx:` 접두사 필수):

- **origin: gx-dev** → `oh-my-gx:coder` 단일 디스패치:
  ```
  {id}: {title}을 구현하라.
  - PROJECT_ROOT: ./
  - 요구사항/설계 발췌: {수집한 컨텍스트}
  - 이전 시도 실패 사유 (있으면): {last_error + progress 발췌}
  - 이 AC 하나만 구현한다. 다른 AC 범위를 건드리지 않는다.
  - 완료 후 변경 파일 목록과 요약을 보고하라.
  ```
- **origin: gx-tdd** → RGR 순차 디스패치: `oh-my-gx:red-writer`(해당 AC의 실패 테스트 작성·실패 확인) → `oh-my-gx:green-coder`(최소 구현으로 통과) → `oh-my-gx:refactor-coder`(GREEN 유지 정리). 각 단계 프롬프트는 `gx-tdd/phases/phase-implement.md`의 Step 2-R/G/F 디스패치 프롬프트를 따르되, 대상을 이 AC 1건으로 한정한다. phase-implement.md를 Read할 수 없으면(플러그인 설치 환경의 경로 차이 등) BLOCKED로 중단하지 않는다 — 위 괄호의 각 에이전트 기본 역할 계약대로 이 AC 1건 한정 프롬프트를 직접 구성해 디스패치한다.

디스패치가 코드 변경을 보고하면 즉시 state.md에 `verify-status: pending`을 기록한다.

에이전트가 구현 불가/전제 결함을 보고하면 → Step 4-실패 경로로 간다 (attempts 증가 + CONTINUE).

### Step 3: verify (backpressure)

`Skill("oh-my-gx:gx-verify", args: "--non-interactive")`를 호출한다.

- **차단 시 (실패 경로)**:
  1. 커밋하지 않는다. `verify-status`는 `pending` 유지.
  2. ac-status.json: 해당 AC `attempts += 1`, `last_error`에 실패 사유 1줄(실패 테스트명 포함), `updated` 갱신.
  3. progress.txt에 1줄 append: `[iter] {id} 실패: {사유 1줄}` (id는 원장 표기 그대로 — 예: `AC-1`)
  4. `<ralph>CONTINUE</ralph>` 출력 후 종료 — 다음 반복이 신선한 컨텍스트로 재시도한다. 워킹트리의 미커밋 변경은 되돌리지 않고 남긴다 (다음 반복의 재료).

### Step 4: verify-status 선기록 → 커밋 (통과 시)

1. **커밋보다 먼저** state.md에 `verify-status: passed`를 기록한다 (훅 G3가 커밋 시점에 passed를 요구한다 — 순서 위반 시 헤드리스에서 자기 차단).
2. 스테이징: `git add -A` 후 `git status --porcelain`으로 스테이징 목록을 검사한다. 민감 파일 패턴(`.claude/config.json` → `sensitiveFilePatterns` 참조 — gx-commit과 동일한 SSOT)이 매치되면 해당 파일을 unstage하고 progress.txt에 경고 1줄을 append한다.
3. 커밋: `git commit -m "{type}: {AC title} ({id})"` — id는 원장 표기 그대로(예: `AC-1` → `(AC-1)`), type은 AC 성격으로 판단(기능 추가 feat, 버그 수정 fix, 그 외 chore). **Co-Authored-By 등 트레일러를 추가하지 않는다** (gx-commit 컨벤션과 동일). 이 커밋은 `oh-my-gx:gx-commit` 스킬을 경유하지 않는 gx-ralph 전용 non-interactive 경로다 (`.claude/rules/skill-routing.md`에 명문화된 예외).
4. 커밋이 훅에 의해 거부되면 → `<ralph>BLOCKED: 커밋 차단 — {훅 사유}</ralph>` 출력 후 종료.

### Step 5: 원장 갱신

1. ac-status.json: 해당 AC `passes: true`, `updated` 갱신.
2. progress.txt에 1줄 append: `[iter] {id} 완료: {커밋 sha 앞 7자} {학습/특이사항 1줄}`

### Step 6: 종료 계약 출력

- 남은 미완료 AC(`passes: false`)가 있으면 → `<ralph>CONTINUE</ralph>`
- 모두 `passes: true` → `<ralph>COMPLETE</ralph>`

응답의 **마지막 줄**에 위 문자열만 출력하고 종료한다.
