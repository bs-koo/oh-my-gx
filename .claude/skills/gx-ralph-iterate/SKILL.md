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
  - Bash(make *)
  - Bash(cmake *)
  - Bash(ctest *)
  - Bash(ceedling *)
  - Bash(cargo *)
  - Bash(mvn *)
  - Bash(dotnet *)
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
4. **verify 없이 커밋 금지.** 커밋은 `verify-status: passed`와 `verify-fingerprint`(verify가 보고한 코드 지문) 기록 후에만. 지문 기록 후에는 커밋 전까지 코드를 더 고치지 않는다 — 고치면 지문이 어긋나 훅 G3가 커밋을 차단한다.
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
- **origin: gx-tdd** → 2석 순차 디스패치: `oh-my-gx:red-writer`(해당 AC의 실패 테스트 작성·실패 확인) → `oh-my-gx:implementer`(GREEN 최소 구현 + REFACTOR 정리 — 루프 모드). 각 단계 프롬프트는 `gx-tdd/phases/phase-implement.md`의 Step 2-R/2-I 디스패치 프롬프트를 따르되, 대상을 이 AC 1건으로 한정하고 **report 파일·15줄 반환 계약은 제외**한다 — 루프에는 reports/ 디렉토리와 태스크 번호가 없으므로 RED 산출물은 인라인으로 인계하고 implementer는 루프 모드(agents/implementer.md)로 동작한다. focused 검증 명령은 이 AC의 테스트 파일로 조립한다(config `focusedTest` 템플릿 — 미지원 시 해당 타입의 전체 `test` 명령으로 폴백하고 반복 로그에 기록). phase-implement.md를 Read할 수 없으면(플러그인 설치 환경의 경로 차이 등) BLOCKED로 중단하지 않는다 — 위 괄호의 각 에이전트 기본 역할 계약대로 이 AC 1건 한정 프롬프트를 직접 구성해 디스패치한다. 대상이 UI(화면 컴포넌트·컴포저블·스토어·라우팅 가드)이면 red-writer 프롬프트에 `gx-tdd/references/frontend-testing.md`의 UI 가드(셀렉터 우선순위·스타일 assert 금지)를 함께 전달한다. (v1.25.0 이전에 시작된 루프의 잔여 반복도 다음 반복부터 이 2석으로 디스패치한다 — 반복은 서로 독립이다)

  **하네스 사전 확인 (origin: gx-tdd 전용, 디스패치 전 1회)**: 이 AC가 요구하는 레이어에 실행 가능한 테스트 러너가 있는지 먼저 확인한다. 대화형 파이프라인은 phase-implement Step 0.5의 하네스 게이트에서 사용자에게 물어보지만, **헤드리스에는 답할 사람이 없다.** 러너가 없는 채로 RED를 디스패치하면 "실패"가 아니라 "실행 불가"가 나오고, 그 AC는 attempts만 3회 소진한 뒤 BLOCKED가 된다 — 러너 부재라는 진짜 원인은 로그에 묻힌다.

  판별: 이 AC의 대상 파일 경로가 속한 레이어의 test 명령(복합 명령이면 해당 조각)을 실행해 **테스트가 1건 이상 수집되는지** 확인한다. 0건이거나 명령 자체가 실행 불가이면 디스패치하지 않고 즉시 종료한다:

  ```
  <ralph>BLOCKED: {AC id} — {레이어} 테스트 러너 없음. 하네스 구축 후 재개 필요</ralph>
  ```

  `attempts`를 증가시키지 않는다 — 구현 실패가 아니라 전제 미충족이며, 시도 횟수를 소진시키면 하네스를 갖춘 뒤에도 그 AC가 3회 초과로 막힌다. `progress.txt`에 사유를 1줄 기록한다.

디스패치가 코드 변경을 보고하면 즉시 state.md에 `verify-status: pending`을 기록한다 (`verify-fingerprint`도 빈 값으로 리셋 — 직전 반복의 지문이 남아 있으면 판정이 흐려진다).

에이전트가 구현 불가/전제 결함을 보고하면 → Step 4-실패 경로로 간다 (attempts 증가 + CONTINUE).

### Step 3: verify (backpressure)

`Skill("oh-my-gx:gx-verify", args: "--non-interactive")`를 호출한다.

- **차단 시 (실패 경로)**:
  1. 커밋하지 않는다. `verify-status`는 `pending` 유지(`verify-fingerprint`도 빈 값 유지).
  2. ac-status.json: 해당 AC `attempts += 1`, `last_error`에 실패 사유 1줄(실패 테스트명 포함), `updated` 갱신.
  3. progress.txt에 1줄 append: `[iter] {id} 실패: {사유 1줄}` (id는 원장 표기 그대로 — 예: `AC-1`)
  4. `<ralph>CONTINUE</ralph>` 출력 후 종료 — 다음 반복이 신선한 컨텍스트로 재시도한다. 워킹트리의 미커밋 변경은 되돌리지 않고 남긴다 (다음 반복의 재료).

### Step 4: verify-status + 지문 선기록 → 커밋 (통과 시)

1. **커밋보다 먼저** state.md에 `verify-status: passed`와 **verify가 보고한 `verify-fingerprint` 값**을 함께 기록한다 (훅 G3가 커밋 시점에 passed와 지문 일치를 함께 요구한다 — 순서 위반 시 헤드리스에서 자기 차단). verify가 지문을 보고하지 않았으면(svn 등) `passed`만 기록한다 — 훅은 지문 없는 세션을 구 세션과 동일하게 판정한다. 이후 커밋까지 코드를 수정하지 않는다 (state.md 갱신은 `.dev/` 제외 규약, `git add -A` 스테이징은 트리 해시 규약 덕분에 지문에 영향이 없다).
2. 스테이징: `git add -A` 후 런타임 파일을 unstage하고(`git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' 2>/dev/null` — 락·반복 로그는 커밋 금지) `git status --porcelain`으로 스테이징 목록을 검사한다. 민감 파일 패턴(`.claude/config.json` → `sensitiveFilePatterns` 참조 — gx-commit과 동일한 SSOT)이 매치되면 해당 파일을 unstage하고 progress.txt에 경고 1줄을 append한다.
3. 커밋: `git commit -m "{type}: {AC title} ({id})"` — id는 원장 표기 그대로(예: `AC-1` → `(AC-1)`), type은 AC 성격으로 판단(기능 추가 feat, 버그 수정 fix, 그 외 chore). **Co-Authored-By 등 트레일러를 추가하지 않는다** (gx-commit 컨벤션과 동일). 이 커밋은 `oh-my-gx:gx-commit` 스킬을 경유하지 않고 gx-ralph만 사용하는 non-interactive 경로다 (`.claude/rules/skill-routing.md`에 명문화된 예외).
4. 커밋이 훅에 의해 거부되면 → `<ralph>BLOCKED: 커밋 차단 — {훅 사유}</ralph>` 출력 후 종료.

### Step 5: 원장 갱신

1. ac-status.json: 해당 AC `passes: true`, `updated` 갱신.
2. progress.txt에 1줄 append: `[iter] {id} 완료: {커밋 sha 앞 7자} {학습/특이사항 1줄}`

### Step 5.5: 작업 계획(plan.md) 갱신 (**모든 AC 완료 시에만**)

**선행 조건**: ac-status.json의 모든 AC가 `passes: true`여야 한다. 하나라도 `passes: false`이면 이 단계를 건너뛴다.

루프는 AC를 1건씩 처리하므로, 이 조건 없이 갱신하면 첫 반복에서 작업 전체가 `완료`로 표시되고 push된다. 그러면 이 작업에 의존하는 다른 작업의 담당자가 phase-setup 3.0.5의 의존 확인을 통과해, 1/N만 끝난 산출물 위에서 착수하게 된다.

조건을 만족하면: `.dev/plan.md`가 존재하고 state.md에 `work-id`가 있을 때 해당 행의 `상태`를 `완료`로 바꾸고 `docs: [plan] {ID} 완료` 메시지로 커밋한 뒤 **현재 브랜치로 push한다** — phase-complete Step 3.5와 같은 층위이며, push하지 않으면 이 작업에 의존하는 담당자의 의존 확인이 계속 막힌다. 이 루프는 phase-complete를 거치지 않으므로 여기서 직접 수행한다. 파일이 없거나 행을 찾지 못하면 건너뛴다. 현재 값이 `폐기`이면 바꾸지 않는다.

### Step 6: 종료 계약 출력

- 남은 미완료 AC(`passes: false`)가 있으면 → `<ralph>CONTINUE</ralph>`
- 모두 `passes: true` → `<ralph>COMPLETE</ralph>`

응답의 **마지막 줄**에 위 문자열만 출력하고 종료한다.
