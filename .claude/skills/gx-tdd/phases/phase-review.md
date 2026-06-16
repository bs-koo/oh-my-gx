# phase-review: 2단계 순차 리뷰 (Spec → Quality) + Security 병렬

## Iron Law

```
NO QUALITY REVIEW UNTIL SPEC COMPLIANCE CONFIRMED
```

이 Phase는 **spec-reviewer → quality-reviewer 순차 강제**다. spec 통과 못 하면 quality 진입 금지.
security-auditor는 quality-reviewer와 **병렬 가능** (서로 독립).

위반 시 즉시 중단하고 spec-reviewer부터 재시작한다.

---

**최대 2회 반복.**

**문서 로드**: `${PROJECT_ROOT}/${DEV_DIR}/prd.md`와 `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read한다. 파일이 없으면 (`--phase review` 단독 실행 등) 건너뛴다.

## Step 0: Mechanical Gate (build + test)

리뷰 에이전트 호출 전에 기계적 검증을 통과시킨다. 실패하는 코드를 리뷰하는 것은 토큰 낭비이다.

프로젝트 타입은 config.json의 `projectTypes`를, 타임아웃은 `timeouts`를 참조한다.

### Step 0-1: Build

**빌드 명령 결정**:

1. `${PROJECT_ROOT}/CLAUDE.md`를 Read하여 빌드/컴파일 명령을 탐색한다. `build`, `compile`, `빌드` 키워드가 포함된 명령을 찾는다. CLAUDE.md가 없으면 다음 단계로.
2. CLAUDE.md에 빌드 명령이 없으면 → 프로젝트 타입에서 기본값을 사용한다:
   | 프로젝트 타입 | 기본 빌드 명령 |
   |---------------|---------------|
   | kotlin-gradle, java-gradle | `./gradlew build -x test` |
   | node | `bun run build` 또는 `npm run build` (package.json의 scripts.build가 있을 때만. `which bun` → bun, 없으면 npm) |
   | python | 건너뛰기 (인터프리터 언어) |
3. 프로젝트 타입으로도 결정 불가 → AskUserQuestion: "빌드 검증 명령을 감지하지 못했습니다." 선택지: 사용자가 직접 입력 / 건너뛰기.

**실행 흐름**:
1. 감지된 빌드 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 0-2로 진행.
3. **실패** → RGR 사이클 위반 신호. `Task(subagent_type="green-coder")`에 빌드 에러 + 관련 테스트 전달하여 새 RED-GREEN 사이클로 수정 시도. **단, 직접 수정(coder 호출) 금지**. RGR 사이클로만 수정.
4. 수정 후 빌드를 **1회 재시도**한다.
5. **재시도 성공** → Step 0-2로 진행.
6. **재시도 실패** → 사용자에게 빌드 에러 표시 후 AskUserQuestion: "빌드 실패. 직접 수정 후 계속 / 중단".

### Step 0-2: Test

**테스트 명령 결정**: config.json `projectTypes`의 `test` 필드를 사용한다. 없으면 건너뛴다.

**실행 흐름**:
1. 테스트 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 1로 진행.
3. **실패** → green-coder/refactor-coder에 회귀 수정 위임 (RGR 사이클 재진입). coder 직접 호출 금지.
4. 수정 후 테스트를 **1회 재시도**한다.
5. **재시도 성공** → Step 1로 진행.
6. **재시도 실패** → 사용자에게 표시 후 AskUserQuestion: "테스트 실패. 직접 수정 후 계속 / 중단".

### Gate 통과 기준

build, test 모두 통과해야 Step 1로 진행한다. 단일 Gate에서 오케스트레이터가 직접 판단한다 (에이전트 호출 불필요).

---

각 반복(1~2회)에서:

## Step 1: 변경사항 수집 및 파일 저장

작업 경로 기준에 따라 GIT_PREFIX를 붙여 실행한다.
- **전체 플로우** (phase-setup부터 진행): `${GIT_PREFIX} add -A`로 스테이징한 후, **Diff 수집 규칙**에 따라 `--cached` diff를 `DIFF_FILE`에 리다이렉트한다.
- **`--phase review` 단독 실행**: 베이스 브랜치 감지 규칙에 따라 베이스를 결정한다. `${GIT_PREFIX} diff $(${GIT_PREFIX} merge-base HEAD <base-branch>)...HEAD`를 `DIFF_FILE`에 리다이렉트한다.

### Step 1.1: diff 공백 안전장치

`wc -l < ${DIFF_FILE}`로 라인 수를 확인한다. **0줄**이면 사용자가 파이프라인 도중 수동 커밋을 끼워 넣었을 가능성이 있다.

1. 베이스 브랜치가 결정되어 있으면 `${GIT_PREFIX} log {base}..HEAD --oneline`으로 브랜치 커밋 존재 여부 확인.
2. 커밋이 1건 이상이면 "수동 커밋 감지" 경로:
   - AskUserQuestion: "브랜치 diff로 리뷰" / "현재 상태로 진행" / "중단"
   - **브랜치 diff 선택** → `${GIT_PREFIX} diff $(${GIT_PREFIX} merge-base HEAD {base})...HEAD`를 `DIFF_FILE`에 리다이렉트.
3. 커밋도 없고 diff도 없으면 "변경사항이 없습니다" 보고 후 중단.

---

## Step 2: spec-reviewer (1단계 — AC 충족 검증)

> **Iron Law**: spec-reviewer가 통과(✅)해야 Step 3 진입 가능. 미통과 시 quality-reviewer 호출 금지.

```
Task(subagent_type="spec-reviewer"):
  description: "Spec compliance review"
  prompt: |
    당신은 spec 준수 검증 전담자입니다.

    [절대 규칙]
    1. AC 충족 여부만 검증합니다.
    2. 코드 품질을 평가하지 않습니다.
    3. 결과는 ✅ 충족 / ⚠️ 부분 / ❌ 미충족 3단계로 분류합니다.

    [PRD]
    - 요구사항: {PRD "요구사항" 섹션}
    - 수용 기준 (G-W-T 시나리오): {PRD "수용 기준" 섹션}

    [설계서]
    - 변경 범위: {design "변경 범위" 섹션}

    [변경사항]
    - diff 파일 경로: {DIFF_FILE}
    - 이 파일을 Read하여 변경사항 확인

    [코드 맵]
    {코드 맵}

    [작업]
    1. 각 AC를 순회하며 충족도 평가
    2. 설계 범위 이탈 식별 (설계서에 없는 파일 수정 여부)
    3. 보고

    [출력 형식]
    ## AC 충족 매트릭스
    | AC | 충족도 | 근거 |
    |----|--------|------|
    | AC-1 | ✅ | LoginService:42 |
    | AC-2 | ⚠️ | 부분 — Then 검증 누락 |
    | AC-3 | ❌ | 코드 변경 없음 |

    [Must] N건 중 N건 충족, [Should] N건 중 N건 충족.

    ## 설계 범위 이탈
    (없으면 "이탈 없음")

    ## 판정
    - 모두 ✅ → SPEC PASS
    - ⚠️/❌ 있음 → SPEC FAIL (재구현 필요)
```

### Step 2.1: spec-reviewer 결과 판정

오케스트레이터가 결과를 분석:

- **SPEC PASS** (모두 ✅) → Step 3 (quality + security)으로 진행
- **SPEC FAIL** (⚠️ 또는 ❌ 1건 이상) → 다음 처리:
  1. 미충족/부분 AC를 사용자에게 표시
  2. AskUserQuestion: "spec 미충족 항목 발견. RGR 사이클로 재구현 시도할까요?"
     - "재구현" → 미충족 AC를 새 태스크로 정의 → `phase-implement`로 복귀 (해당 AC만 RGR)
     - "수동 수정" → 사용자가 코드 수정 후 phase-review 재호출
     - "이대로 진행" → 미충족 AC를 trust-ledger에 "미충족 AC" 섹션으로 기록 후 Step 3 진행 (예외)
  3. 재구현 후 spec-reviewer 재호출 (반복 카운트에 포함)

**Iron Law 위반 감지**: spec-reviewer 미통과 상태에서 quality-reviewer를 호출하려는 시도가 발견되면 즉시 중단.

`current-step`을 `"spec-review (1단계)"`로 갱신.

---

## Step 3: quality-reviewer + security-auditor (병렬, spec 통과 후만)

> **순서 강제**: 이 Step은 Step 2가 SPEC PASS여야만 진입한다.

두 에이전트를 **하나의 메시지에서 동시 Task 호출**.

### Task A: quality-reviewer (코드 품질만)

```
Task(subagent_type="quality-reviewer"):
  description: "Code quality review (post-spec-pass)"
  prompt: |
    당신은 코드 품질 검증 전담자입니다.

    [절대 규칙]
    1. 코드 품질만 검증합니다.
    2. AC 충족 여부를 평가하지 않습니다 (spec-reviewer가 이미 통과시킴).
    3. 결과는 [Critical/Important/Minor]로 분류합니다.

    [변경사항]
    - diff 파일 경로: {DIFF_FILE}
    - 이 파일을 Read하여 변경사항 확인

    [코드 맵]
    {코드 맵}

    [프로젝트 컨벤션]
    {CLAUDE.md 컨벤션 또는 기존 코드 스타일}

    [평가 영역]
    - Critical: 보안 취약점, 데이터 손실, race condition, null pointer, 무한 루프
    - Important: DRY 위반, 단일 책임 위반, 매직 넘버, 잘못된 추상화, 컨벤션 위반
    - Minor: 가독성, 주석 개선, import 정리

    [출력 형식]
    ## 코드 품질 리뷰
    ### Critical (N건)
    - {파일}:{라인} — {문제}
      - 권고: {수정 방안}
    ### Important (N건)
    - ...
    ### Minor (N건)
    - ...

    ## 판정
    - Critical 0 + Important 0 → QUALITY PASS
    - Critical N > 0 또는 Important N > 0 → QUALITY FAIL (수정 필요)
    - Minor만 → QUALITY PASS (Minor는 메모만)
```

### Task B: security-auditor (통합 감사)

```
Task(subagent_type="security-auditor"):
  description: "Security audit (parallel with quality)"
  prompt: |
    [PRD 전체]
    {PRD}

    [설계서 전체]
    {design}

    [변경사항]
    - diff 파일 경로: {DIFF_FILE}
    - Read 지시

    [코드 맵]
    {코드 맵}

    [REFERENCES (있으면)]
    "아래 외부 규격/표준의 보안 관련 항목을 감사에 포함하라."
    {REFERENCES 테이블}

    [지시]
    "통합 감사"로 동작. CRITICAL/HIGH/MEDIUM 분류.

    [출력 형식]
    Trust Ledger 포맷:
    ## 통합 감사 (review)
    - [분류/심각도] 항목 설명
      - 근거: ...
      - 권고: ...
```

`current-step`을 `"quality-review + security (2단계 병렬)"`로 갱신.

---

## Step 4: 결과 합산 및 처리

두 Task 완료 후:

### Step 4.1: Trust Ledger 저장

security-auditor 결과를 `${PROJECT_ROOT}/${DEV_DIR}/trust-ledger.md`에 저장.

### Step 4.2: 통합 findings 구성

```
findings = {
  spec: spec-reviewer 결과 (Step 2),
  quality: quality-reviewer 결과 (Step 3 Task A),
  security: security-auditor 결과 (Step 3 Task B)
}
```

중복 항목은 병합 (같은 파일:라인을 둘 다 지적).

### Step 4.3: 사용자 요약 보고

**요약만** 표시 (Agent 전문 출력 금지):

```
리뷰 완료:
- Spec: ✅ 모두 통과 (또는 ❌ N건 미충족 → 재구현 진행)
- Quality: Critical N건, Important N건, Minor N건
- Security: CRITICAL N건, HIGH N건, MEDIUM N건
- Trust Ledger: ${DEV_DIR}/trust-ledger.md
```

### Step 4.4: 결과 처리 (의사코드)

```
did_fix = false

# 4a: Critical/Important 자동 수정 (quality + security)
critical_items = quality.Critical + security.CRITICAL + quality.Important + security.HIGH
if critical_items:
    해당 항목 사용자에게 표시
    AskUserQuestion: "RGR 사이클로 수정할까요?"
      - "예 (RGR)" → 각 항목을 새 AC로 정의 → phase-implement RGR 사이클 진입
      - "수동 수정" → 사용자 수정 후 phase-review 재호출
      - "이대로 진행" → Trust Ledger에 "수용된 위험" 기록
    did_fix = true (RGR 선택 시)

# 4b: 반복 판단
if did_fix:
    → 다음 반복 (Step 2부터 재실행: spec → quality)
else:
    # Critical/Important 없는 경우
    if Minor 또는 MEDIUM 항목 있음:
        항목 목록 표시 + "수정할까요?" 확인
        if 수정 선택:
            RGR 사이클 진입 → 단발성 확인 리뷰 (반복 카운트 미포함)
        else:
            → phase-complete
    else:
        → phase-complete (클린 통과)
```

**2회 반복 후 미해결 Critical**: 2회 반복 후에도 Critical이 남으면 사용자에게 명시하고 AskUserQuestion: "수동 수정 후 재리뷰" / "현재 상태로 진행".

---

## state.md 추적

```yaml
steps:
  review:
    - mechanical-gate (build + test): completed
    - spec-review (1단계): completed
    - quality-review + security (2단계 병렬): in_progress
execution-log:
  - phase: review
    step: mechanical-gate
    result: "build ✓, test ✓"
  - phase: review
    agent: spec-reviewer
    result: "SPEC PASS — [Must] 5/5, [Should] 2/3"
  - phase: review
    agent: quality-reviewer
    result: "Critical 0, Important 2, Minor 5"
  - phase: review
    agent: security-auditor
    result: "CRITICAL 0, HIGH 1, MEDIUM 3"
```

---

## --resume 호환

- `"mechanical-gate"` → Step 0부터 재실행
- `"spec-review (1단계)"` → Step 2부터 재실행
- `"quality-review + security (2단계 병렬)"` → Step 3부터 재실행 (spec 결과는 trust-ledger/execution-log에서 복원)

---

## 금지 사항 (Iron Law 강제)

이 Phase에서 절대 호출하지 않는 에이전트:
- ❌ `qa-manager` (deprecated — spec-reviewer + quality-reviewer로 분해됨)
- ❌ `coder` (deprecated — 수정은 RGR 사이클로 phase-implement 재진입)

이 Phase에서 절대 수행하지 않는 동작:
- ❌ spec-reviewer 미통과 상태에서 quality-reviewer 호출 — Iron Law 위반
- ❌ spec-reviewer와 quality-reviewer 병렬 호출 — 순서 강제 위반
- ❌ coder 직접 호출로 수정 — RGR 사이클 우회 (Iron Law 1 위반)
- ❌ "Critical이지만 이번엔 그냥 진행" — 사용자 명시 승인 없이 우회 금지

위반 감지 시 즉시 중단하고 spec-reviewer부터 재시작한다.
