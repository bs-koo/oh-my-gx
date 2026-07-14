# phase-complete: 완료 (verify 게이트 강제)

## Iron Law: verify 게이트 통과 필수

```
NO COMMIT/PR WITHOUT VERIFY GATE PASS
```

complete Phase 진입 시 **반드시 `Skill("oh-my-gx:gx-verify")` 호출**한다. 통과 못 하면 commit/PR 진입 차단.

이유:
- phase-review가 통과해도 시간이 지나며 외부 환경 변화(의존성 업데이트, 다른 브랜치 머지 등)로 회귀 가능
- "phase-review에서 통과했으니 OK"는 신선한 증거 아님 (Iron Law 3)
- commit 직전 신선한 검증 실행이 유일한 안전망

위반 시 즉시 중단하고 verify 게이트부터 재시작.

각 단계가 실패하면 사용자에게 보고하고 진행 여부를 확인한다.

---

## Step -2: TDD 이행 게이트 (모든 진입 경로 공통)

commit/PR로 이어지는 이 Phase의 **모든 진입**(전체 모드, `--phase complete` 단독, 수동 수정 후 재호출)에서 수행한다:

0. **ralph 무인 루프 예외 (선판정)**: state.md가 `pipeline: gx-ralph`이고 `origin: gx-tdd`이면, 반복 세션이 red-writer→green-coder→refactor-coder 트리오로 AC를 구현한 산출물이다 (구현 상태는 phases가 아니라 ac-status.json 원장에 있다). **이 게이트를 통과 처리하고 Step -1로 진행한다** — 아래 phases 기반 조건(implement/review 미완)을 적용하지 않는다. gx-tdd 출발 루프의 복귀 경로(`/gx-tdd --phase complete`)에서 phases.implement가 completed가 아니라는 이유로 오탐이 뜨는 것을 막는다.
1. 그 외에는 state.md를 확인한다. 다음 중 하나면 **TDD 미이행 가능성**으로 판정한다:
   - `pipeline: gx-tdd` 필드가 없다 (gx-dev 이력이거나 알 수 없는 state — phases 기록을 신뢰할 수 없다)
   - `phases.implement`가 `completed`가 아니다
   - 핵심 모드(`mode: core` — 구 명칭 `light`, 레거시 `mode: hotfix`, 또는 `flags`의 `--core`/`--light`/`--hotfix` 포함)가 **아닌데** `phases.review`가 `completed`가 아니다 (core는 review를 설계상 스킵하므로 review 부재가 정상이다)
2. TDD 미이행 가능성이면 AskUserQuestion으로 위험 수용을 확인한다. 수용 시 `${DEV_DIR}/trust-ledger.md`에 "TDD 미이행 완료 실행" 항목을 기록한 후 진행하고, 거부 시 중단하며 `/gx-tdd`(전체 모드)를 안내한다.
3. 전체 모드의 정상 순서 진입(직전 review 완료)에서는 조건이 모두 충족되므로 이 게이트는 확인만 하고 지나간다.

## Step -1: verify 게이트 (commit/PR 진입 전 필수)

`Skill("oh-my-gx:gx-verify")`를 호출한다.

verify 게이트는 테스트 0 failures·빌드 성공에 더해, phase-implement Step 0.5(기준선 게이트)가 기록한 `warnings-baseline` 대비 **신규 경고**도 차단한다 (기존 경고는 허용 — 기준선이 RGR 시작 전이므로 이번 구현이 유입한 경고부터 잡힌다). verify가 "위험 수용"으로 통과를 보고하면(신규 경고·검증 명령 미감지 등) **오케스트레이터가 그 내용을 `${DEV_DIR}/trust-ledger.md`에 기록**한다 (gx-verify는 Write 권한이 없다).

**verify 결과 처리**:

- **✅ verify 통과** → state.md 최상위 `verify-status: passed` 갱신(커밋/PR 게이트 해제 키) 후 Step 0 (인수 검증)으로 진행. 이후 코드 변경이 발생해 재진입하면 `pending`으로 리셋하고 Step -1부터 재실행한다
- **❌ verify 차단**:
  1. verify가 실패 테스트/빌드 항목을 보고함
  2. 사용자에게 표시 후 AskUserQuestion:
     - "RGR 사이클로 수정" → phase-implement로 복귀 (실패 항목을 새 AC로 정의)
     - "수동 수정" → 사용자 수정 후 phase-complete 재호출 (execution-log에 "수동 수정 재주입" 기록. 재호출 시 Step -1 verify부터 재실행)
     - "중단" → state.md에 `status: cancelled` 기록
  3. 자동 수정은 시도하지 않음 (RGR 사이클로만 수정. coder 직접 호출 금지)

**Iron Law 위반 감지**: verify 통과 없이 Step 0 이후를 진입하려는 시도가 감지되면 즉시 중단.

`current-step`을 `"verify 게이트"`로 갱신.

---

## Step 0: 인수 검증 (ProductOwner / LIGHT는 AC 자가 검증)

**diff 갱신** (모드 무관 공통): phase-review 이후 코드 수정이 있었을 수 있으므로 diff를 갱신한다.
- **git**: `git add -A`로 스테이징한 후 **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트.
- **svn**: `svn diff > ${DIFF_FILE}`로 갱신.

**핵심 모드이면** product-owner를 디스패치하지 않고 오케스트레이터가 **AC 자가 검증**을 직접 수행한다 (verify 게이트가 테스트 실행 증거를 이미 강제하므로 여기서는 AC 충족 대조만 한다):
1. `${DEV_DIR}/ac.md`(레거시 재개로 ac.md가 없으면 prd.md)의 G-W-T AC와 RGR 사이클 결과(각 AC의 테스트 통과)·DIFF_FILE을 대조한다.
2. AC별 충족 체크리스트를 사용자에게 표시한다 (예: `AC-1 ✅ (shouldReject401 통과) / AC-2 ⚠️ — 사유`).
3. 모두 충족 → Step 1 진행. 미충족이 있으면 AskUserQuestion으로 확인한다:
   ```
   AskUserQuestion(
     questions: [{
       header: "AC 자가 검증",
       question: "AC 자가 검증에서 미충족 항목이 있습니다. 어떻게 진행할까요?",
       multiSelect: false,
       options: [
         { label: "RGR 수정", description: "미충족 AC를 새 태스크로 phase-implement RGR 사이클을 재실행합니다" },
         { label: "건너뛰기", description: "위험 수용으로 진행합니다 (trust-ledger에 기록)" }
       ]
     }]
   )
   ```
   - "RGR 수정" → phase-implement 복귀 (coder 직접 호출 금지 — Iron Law 1).
   - "건너뛰기" → 위험 수용을 trust-ledger에 기록 후 Step 1 진행.

**전체 모드**는 아래를 따른다. PRD가 없으면 이 단계를 건너뛴다.

PRD가 있으면 (`${DEV_DIR}/prd.md`), product-owner에게 인수 검증을 요청한다.

`Task(subagent_type="oh-my-gx:product-owner")` — prompt에 다음을 포함:
- PRD의 "요구사항" + "수용 기준" (Context Slicing 규칙 참조)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- "인수 검증"으로 동작할 것

**결과를 사용자에게 요약만 보고한다** (Agent 전문 출력 금지):
- **ACCEPT**: "인수 검증 통과. 모든 [Must] 수용 기준 충족." 다음 단계 진행.
- **REJECT**: "인수 검증 미통과. [Must] 미충족 N건:" + 미충족 항목 목록만 표시. 수정 여부를 확인한다.
  - **RGR 수정 선택** → phase-implement로 복귀하여 미충족 AC를 새 태스크로 RGR 사이클 실행. (coder 직접 호출 금지 — Iron Law 1)
  - 수동 수정 선택 → 사용자가 직접 수정 후 phase-complete 재호출 (execution-log에 "수동 수정 재주입" 기록)
  - 건너뛰기 선택 → 다음 단계 진행 (위험 수용. trust-ledger에 기록)

위 Step 0 진입 조건에 의해 PRD 부재이면 이 단계 전체가 건너뛰어진다.

## Step 1: Commit

**svn인 경우** → `gx-commit` 스킬은 git 전용이므로 건너뛴다. "SVN 프로젝트입니다. verify 게이트 통과를 확인한 뒤 `svn commit`을 직접 실행해주세요." 출력 후 Step 3으로 진행한다.

**git인 경우:**
`Skill("oh-my-gx:gx-commit")`을 호출하여 커밋한다 (Step -1 verify 게이트 통과 후 → commit).

> 주의: `oh-my-gx:gx-commit`은 gx-dev와 공유하는 스킬로 verify 실행(테스트 실행 증거 수집)을 포함하지 않는다 (`verify-status` 기반 조건부 경고 게이트만 있다).
> verify 책임은 전적으로 Step -1(`oh-my-gx:gx-verify`)에 있다. Step -1 이후 코드 변경이 발생했다면 commit 전에 Step -1을 반드시 재실행한다.

**build/test 실패 시**: Step -1 verify 게이트의 차단 처리 분기를 그대로 따른다 (동일 절차의 이중 서술을 피하기 위해 **Step -1이 단일 기준**이다). `coder`(deprecated) 직접 호출 금지 — 수정은 RGR 사이클로만 한다.

## Step 2: PR 생성

**svn인 경우** → 건너뛴다 (Step 1에서 이미 건너뜀. SVN은 PR 개념이 없다).

**git인 경우:**
`Skill("oh-my-gx:gx-pull-request")`를 호출하여 PR을 생성한다. pull-request은 독립 스킬이므로 dev 컨텍스트를 알지 못하며, **dev 산출물을 자동 감지하지도 않는다**. 오케스트레이터가 **스킬 호출 전에** `${DEV_DIR}/pr-context.md`를 조립하고 `--background` 인자로 명시 전달한다.

### Step 2-1: `${DEV_DIR}/pr-context.md` 조립 (Skill 호출 전)

오케스트레이터가 아래 내용을 `${DEV_DIR}/pr-context.md`에 Write한다:

1. **비즈니스 맥락**: PRD의 "배경"과 "요구사항", 설계서의 "배경 및 목적". 핵심 모드이면 ac.md의 "배경"과 "요구사항 (AC)"를 사용 (레거시 재개로 ac.md가 없으면 prd.md, 그것도 없으면 ARGS[0]).
2. **Trust Ledger 요약**: `${DEV_DIR}/trust-ledger.md`가 존재하면 Read하여 아래 형식으로 포함한다:
   ```
   ## Audit Summary
   - 총 N건 (CRITICAL: n, HIGH: n, MEDIUM: n)
   - [주요 발견 항목 1줄 요약] (최대 5건)
   ```
   Trust Ledger가 없으면 이 섹션을 생략한다.

   **핵심 모드 긴급 감사 병기**: Trust Ledger에 `### 핵심 모드 긴급 감사` 섹션(레거시 산출물은 `### Light 긴급 감사` 또는 `### Hotfix 긴급 감사`)이 포함되어 있으면, `## Audit Summary` 블록 끝에 `- 핵심 모드 긴급 감사: CRITICAL n건, HIGH n건 (자세한 내용은 Trust Ledger 참조)` 한 줄을 추가한다. 전체·핵심 모드 모두 동일한 Audit Summary 포맷을 사용하여 PR 본문의 일관성을 유지한다.

### Step 2-2: `Skill("oh-my-gx:gx-pull-request")` 호출

`${DEV_DIR}/pr-context.md` 조립이 완료된 후 **args로 파일을 명시 전달**하여 호출한다:

`Skill(skill: "oh-my-gx:gx-pull-request", args: "--background ${DEV_DIR}/pr-context.md")`

pull-request 스킬은 `--background`로 받은 파일만 PR 본문(Background + Audit Summary)에 반영한다 — 자동 감지는 없다 (gx-dev phase-complete와 동일한 명시 전달 방식).

### Step 2-3: 후속 처리

- pull-request 스킬이 전제조건 미충족(gh 미설치, remote 미설정 등)으로 종료하면, 오케스트레이터는 후속 안내를 추가한다: "나중에 `/oh-my-gx:gx-pull-request`로 PR을 생성할 수 있습니다."
- **PR 생성 후 알림**: pull-request 스킬이 알림까지 처리한다. 스킬 종료 후 알림이 누락된 정황이 있으면 (PR URL은 있으나 알림 미전송) 오케스트레이터가 알림 전송을 직접 수행한다.

## Step 3: 도메인 status.md 갱신

**svn인 경우** → 건너뛴다 (PR 링크 기입 등 git 전제이며, Step 1에서 커밋도 건너뛰므로 동기화 대상이 없다. status.md를 갱신해야 하면 `svn commit`으로 직접 반영).

`DOMAIN_CONTEXT`가 있고 (phase-setup에서 도메인 매칭 성공), Step 0 인수 검증이 ACCEPT이면 실행한다. 그 외에는 건너뛴다.

1. Step 0 인수 검증 결과에서 **통과한 AC 목록**을 추출한다 (예: AC-1, AC-4, AC-7).
2. 매칭된 도메인의 `context/{domain}/status.md`를 Read한다.
3. 통과한 AC와 일치하는 행의 상태를 `⬜`→`✅`로, PR 열에 생성된 PR 링크를 기입한다.
4. AC가 `-`인 행은 변경하지 않는다 (PR 머지 시 수동 판정).
5. Edit으로 status.md를 갱신한다.
6. 갱신 결과를 사용자에게 보고한다:
   ```
   status.md 갱신: ✅ AC-1, AC-4, AC-7 (FR-1, FR-16, FR-19)
   ```

## Step 4: context 환류 제안

`DOMAIN_CONTEXT`가 있으면 실행한다. 없으면 건너뛴다.

PRD와 설계서에서 context 갱신 후보를 추출하여 사용자에게 제안한다:

1. **glossary 후보**: PRD/설계서에 등장하는 도메인 용어 중, 현재 `glossary.md`에 없는 것을 추출한다.
2. **주제 문서 후보**: PRD 제목과 배경을 기반으로, 주제 문서 생성을 제안한다.
3. **architecture.md 갱신 후보**: 설계서에 새로운 구조적 결정(레이어, 의존관계 등)이 있으면 인덱스 갱신을 제안한다.

사용자에게 AskUserQuestion으로 제안:
- "context 문서에 반영할까요?" + 후보 목록 표시
- 반영 선택 → 해당 파일 Edit/Write. 주제 문서 생성 시 architecture.md 인덱스에 링크 추가.
- 건너뛰기 선택 → 다음 단계 진행.

**임의 반영 금지**: 사용자 승인 없이 context 문서를 수정하지 않는다.

## Step 5: 진행 상태 완료
`${DEV_DIR}/state.md`의 `status`를 `completed`, `phases.complete`를 `completed`로 갱신한다.

## Step 6: 다음 단계

PR이 생성되었으면 완료이다. **PR 머지는 절대 실행하지 않는다** — 머지는 리뷰어가 직접 수행한다.

리뷰 수정 요청에 대비하여 작업환경 유지를 안내한다:
"리뷰 피드백 대응을 위해 현재 브랜치를 유지합니다. 리뷰 완료 후 베이스 브랜치로 전환하세요."
