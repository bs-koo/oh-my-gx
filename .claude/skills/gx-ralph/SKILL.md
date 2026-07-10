---
name: gx-ralph
version: 1.0.0
description: "루프 엔지니어링(Ralph 루프) 진입 스킬 - PRD 수용 기준을 AC 원장으로 변환하고 외부 러너의 무인 반복을 준비한다. PRD 확정 후 사용. '랄프', 'ralph', '루프 돌려' 시 사용."
argument-hint: "[--status]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
  - Bash(git *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(mkdir *)
  - Bash(pwd *)
---

# gx-ralph

> **이 스킬**: gx-ralph — 루프 엔지니어링(Ralph 루프) 진입/관제 스킬
> **호출 시 주의**: 이 스킬 내에서 다른 스킬을 호출할 때 반드시 `oh-my-gx:` 접두사를 사용한다.

Ralph Wiggum 루프 패턴의 진입 스킬. PRD의 수용 기준(AC)을 기계 판독 가능한 원장(`ac-status.json`)으로 변환하고, 외부 러너(`scripts/gx-ralph.sh`)가 AC 1건씩 무인 반복할 수 있도록 상태를 준비한다.

**이 스킬은 구현·검증·커밋을 하지 않는다** — 그것은 반복 세션(`oh-my-gx:gx-ralph-iterate`)의 몫이다. 이 스킬은 준비와 관제만 담당한다.

## 파이프라인 위치

```
[대화형 1회] /gx-dev 또는 /gx-tdd     → PRD(·설계) 사용자 승인까지 확정
[대화형 1회] /gx-ralph                → AC 원장 생성 + 러너 준비 (이 스킬)
[무인 반복]  scripts/gx-ralph.sh      → 반복마다 새 claude 세션이 gx-ralph-iterate 실행
                                        (AC 1건 구현 → verify → 커밋 → 원장 갱신)
[대화형 1회] 사용자 복귀              → /gx-dev --phase review → --phase complete
```

핵심 원리 (Ralph 루프): 진행 상태는 대화 이력이 아닌 **파일과 git 히스토리에 영속**하고, 매 반복은 **신선한 컨텍스트**로 시작하며, **verify가 backpressure**, **종료 계약**으로 루프를 탈출한다. 루프당 AC 1건만 처리한다.

## 상태 계약 (SSOT)

이 섹션이 gx-ralph 상태 계약의 **정본**이다. `gx-ralph-iterate/SKILL.md`와 `scripts/gx-ralph.sh`는 이 계약의 사본을 참조한다.

> **드리프트 주의**: 스키마 키·종료 계약 문자열은 3파일(이 파일·gx-ralph-iterate·러너)에 의도적으로 중복된다. 한쪽 수정 시 함께 갱신한다. `scripts/lint-consistency.sh`가 일치를 검사한다.

### ac-status.json — AC 원장

경로: `${DEV_DIR}/ac-status.json`

```json
{
  "version": 1,
  "branch": "{작업 브랜치명}",
  "created": "{ISO8601}",
  "updated": "{ISO8601}",
  "acs": [
    { "id": "AC-1", "title": "{수용 기준 요약 1줄}", "passes": false, "attempts": 0, "last_error": "" }
  ]
}
```

- `passes`: 해당 AC가 verify 통과 + 커밋 완료된 경우에만 `true`
- `attempts`: 시도 횟수. verify 차단 시 +1. **3 이상이면 반복 세션이 건너뛴다**
- `last_error`: 마지막 실패 사유 1줄

### state.md 확장 필드

기존 state.md(gx-dev/gx-tdd 산출)에 아래 필드를 추가/갱신한다. 기존 state.md가 없으면 골격을 생성한다:

```yaml
pipeline: gx-ralph        # 훅 G3·스킬 라우팅의 판별 키
status: in_progress
origin: gx-dev | gx-tdd   # 반복 세션의 구현 디스패치 방식 (gx-tdd면 RGR 트리오)
verify-status: pending    # pending|passed — 전이 규칙은 아래
last-known-head: {sha}    # 러너가 반복 전후 기록 (NO_DRIFT 감지용)
max-iterations: 10        # 러너 최대 반복 수 (Step 2에서 사용자 확정)
branch: {작업 브랜치명}
args: "{원 요청}"
```

**verify-status 전이 규칙 (주체: 반복 세션)**: 코드 변경 직후 `pending`으로 리셋 → gx-verify 통과 시 `passed`로 전이 → **커밋은 `passed` 상태에서만 실행** (훅 G3가 커밋 시점에 이를 검사하는 최종 방어선이므로 순서를 지켜야 헤드리스에서 자기 차단되지 않는다).

### 종료 계약 (반복 세션 → 러너)

반복 세션은 **응답의 마지막 줄에 정확히 한 번** 아래 중 하나를 출력한다. 러너는 반복 로그의 **마지막 매치**를 파싱하며, 미출력(크래시 등)은 BLOCKED로 취급한다:

- `<ralph>COMPLETE</ralph>` — 모든 AC `passes: true`. 러너가 루프를 종료한다
- `<ralph>CONTINUE</ralph>` — 미완료 AC 남음 (이번 반복의 성공/실패와 무관)
- `<ralph>BLOCKED: {사유 1줄}</ralph>` — 사람 개입 필요. 러너가 루프를 중단한다

### 회귀 정책 (fail-closed)

verify는 매 반복 **전체 테스트**를 실행한다. 새 AC 구현이 기존 AC의 테스트를 깨면 verify가 차단되어 커밋 자체가 일어나지 않으므로, 잘못된 상태는 원장에도 git에도 기록되지 않는다. 같은 AC가 3회 차단되면 반복 세션이 BLOCKED를 선언하고 사람이 복귀해 판단한다. `passes: true`의 소급 무효화는 하지 않는다 — 최종 리뷰(`--phase review`)가 base..HEAD 누적 diff와 전체 테스트로 재검증한다.

---

## 실행 절차

### Step 0: --status 분기

`--status`가 지정되면 준비를 실행하지 않고 현재 상태만 출력한다:

1. DEV_DIR을 계산한다 (`git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/`).
2. `${DEV_DIR}/ac-status.json`이 없으면: "gx-ralph 루프가 준비되지 않았습니다." 출력 후 종료.
3. 있으면 출력:
   ```
   ## gx-ralph 루프 상태
   - 브랜치: {branch}
   - AC: {passes=true 수}/{전체 수} 완료
   - AC별: AC-1 ✅ / AC-2 ⬜ (attempts: 1) / ...
   - 최근 진행 (progress.txt 마지막 5줄)
   - lock: {존재 여부 → 러너 실행 중 추정}
   ```
4. 출력 후 종료.

### Step 1: 사전 조건 게이트

순서대로 검사하고, 하나라도 실패하면 해당 안내와 함께 **중단**한다:

1. **VCS**: `.claude/config.json`의 `vcs`가 `"svn"`이면 차단 — "SVN 프로젝트에서는 gx-ralph를 사용할 수 없습니다. 무인 루프가 요구하는 자동 커밋을 훅(G2)이 차단하며, 사용자 터미널 커밋으로는 무인 반복이 성립하지 않습니다."
2. **git repo**: `git rev-parse --is-inside-work-tree` 실패 시 차단.
3. **브랜치**: `git branch --show-current`가 빈 값(detached HEAD)이면 차단. `main`/`master`/`develop`이면 차단 — "보호 브랜치에서는 루프를 돌릴 수 없습니다. 작업 브랜치를 먼저 생성하세요."
4. **PRD**: `DEV_DIR = .dev/{branch-slug}` 계산 후 `${DEV_DIR}/prd.md`가 없으면 차단 — "PRD가 없습니다. `oh-my-gx:gx-dev` 또는 `oh-my-gx:gx-tdd`로 PRD를 먼저 확정하세요. 루프는 승인된 PRD를 명세로 읽는 소비자입니다."
5. **lock**: `${DEV_DIR}/ralph.lock`이 존재하면 차단 — "러너가 이미 실행 중이거나 비정상 종료로 lock이 남아 있습니다. 실행 중인 러너가 없다면 `${DEV_DIR}/ralph.lock`을 삭제한 뒤 다시 시도하세요."
6. **기존 원장**: `${DEV_DIR}/ac-status.json`이 이미 있으면 AskUserQuestion으로 확인:
   ```
   questions: [{
     question: "기존 AC 원장이 있습니다 ({passes 수}/{전체 수} 완료). 어떻게 할까요?",
     header: "AC 원장",
     options: [
       { label: "이어서 사용 (Recommended)", description: "기존 진행 상태를 유지하고 러너 안내로 넘어갑니다" },
       { label: "재생성", description: "PRD에서 AC를 다시 추출하고 진행 상태를 초기화합니다" }
     ],
     multiSelect: false
   }]
   ```
   "이어서 사용"이면 Step 2를 건너뛰고 Step 3으로 진행한다.

### Step 2: AC 원장 생성

1. `${DEV_DIR}/prd.md`의 수용 기준 섹션에서 AC 항목을 추출한다 (번호/불릿 단위, Given-When-Then이면 시나리오 단위).
2. 각 AC가 **한 컨텍스트 윈도우에서 완료 가능한 크기**인지 평가한다. 여러 파일·여러 레이어에 걸친 큰 AC는 분할안을 준비한다.
3. AskUserQuestion (한 번에 두 질문):
   ```
   questions: [
     {
       question: "PRD에서 AC {N}건을 추출했습니다: {AC id·제목 목록}. 각 AC가 루프 1회(한 컨텍스트 윈도우)에 완료 가능한 크기여야 합니다.",
       header: "AC 확정",
       options: [
         { label: "이대로 확정 (Recommended)", description: "추출된 AC를 그대로 루프 단위로 사용합니다" },
         { label: "분할 제안 검토", description: "크기가 큰 AC의 분할안을 확인한 뒤 확정합니다" }
       ],
       multiSelect: false
     },
     {
       question: "러너의 최대 반복 수를 정해주세요. AC {N}건 기준 여유분을 포함한 값을 권장합니다.",
       header: "최대 반복",
       options: [
         { label: "{N+5}회 (Recommended)", description: "AC 수 + 재시도 여유 5회" },
         { label: "{N*2}회", description: "재시도 여유를 넉넉히" }
       ],
       multiSelect: false
     }
   ]
   ```
   "분할 제안 검토"를 선택하면 분할안을 제시하고 확정을 재확인한다.
4. 확정된 AC로 `${DEV_DIR}/ac-status.json`을 생성한다 (전 AC `passes: false`, `attempts: 0`).

### Step 3: state.md 기록 + 러너 안내

1. `${DEV_DIR}/state.md`를 갱신한다 (없으면 골격 생성):
   - `pipeline: gx-ralph`, `status: in_progress`, `verify-status: pending`
   - `origin`: 기존 state.md에 gx-tdd 이력이 있으면 `gx-tdd`, 그 외 `gx-dev`
   - `max-iterations`: Step 2에서 확정한 값
   - `last-known-head`: `git rev-parse HEAD` 결과
   - `branch`: 현재 브랜치명
2. `${DEV_DIR}/progress.txt`가 없으면 헤더 1줄로 생성한다: `# gx-ralph progress — {branch} — 반복마다 학습·결과를 append`
3. 러너 경로를 계산한다: 이 스킬 파일의 base directory에서 3단계 상위(저장소/플러그인 루트)의 `scripts/gx-ralph.sh`. 사용자에게 안내한다:
   ```
   준비 완료. 터미널에서 러너를 실행하세요:

     bash {러너 절대 경로}

   - 러너는 반복마다 새 claude 세션을 기동해 AC 1건씩 처리합니다 (최대 {max-iterations}회)
   - 진행 관찰: ${DEV_DIR}/progress.txt (요약), ${DEV_DIR}/iter-{N}.log (반복별 상세)
   - 중간 상태 확인: /oh-my-gx:gx-ralph --status
   - 루프 종료 후: /gx-dev --phase review 로 리뷰 → --phase complete 로 인수·PR
   ```
   이 스킬은 러너를 직접 실행하지 않는다 — 러너는 수 분~수십 분 실행되는 사용자 터미널 프로세스다.
