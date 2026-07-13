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

**문서 로드**: `${PROJECT_ROOT}/${DEV_DIR}/prd.md`와 `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read한다. 파일이 없으면 (`--phase review` 단독 실행 등) 건너뛴다. `ANTI_PATTERNS_PATH`(gx-tdd 스킬 디렉토리의 `references/testing-anti-patterns.md` 절대 경로 — 플러그인 설치 환경에서는 플러그인 베이스 경로 하위)를 확정한다.

## Step 0: Mechanical Gate (build + test)

리뷰 에이전트 호출 전에 기계적 검증을 통과시킨다. 실패하는 코드를 리뷰하는 것은 토큰 낭비이다.

프로젝트 타입은 config.json의 `projectTypes`를, 타임아웃은 `timeouts`를 참조한다.

### Step 0-1: Build

**빌드 명령 결정**:

1. `${PROJECT_ROOT}/CLAUDE.md`를 Read하여 빌드/컴파일 명령을 탐색한다. `build`, `compile`, `빌드` 키워드가 포함된 명령을 찾는다. CLAUDE.md가 없으면 다음 단계로.
2. CLAUDE.md에 빌드 명령이 없으면 → 프로젝트 타입에서 기본값을 사용한다:
   | 프로젝트 타입 | 기본 빌드 명령 |
   |---------------|---------------|
   | java-spring (gradle) | `./gradlew build -x test` |
   | node | `bun run build` 또는 `npm run build` (package.json의 scripts.build가 있을 때만. `which bun` → bun, 없으면 npm) |
   | python | 건너뛰기 (인터프리터 언어 — 기본 config 미정의 타입, `projectTypes` 확장 시에만 도달) |
3. 프로젝트 타입으로도 결정 불가 → AskUserQuestion: "빌드 검증 명령을 감지하지 못했습니다." 선택지: 사용자가 직접 입력 / 건너뛰기.

**실행 흐름**:
1. 감지된 빌드 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 0-2로 진행.
3. **실패** → 직전 RGR 사이클이 컴파일 미완성 상태일 가능성이 크다. `Task(subagent_type="oh-my-gx:green-coder")`에 빌드 에러를 전달하여 컴파일을 통과시킨다. 이는 진행 중인 GREEN 단계의 연장이므로 **새 RED는 불필요**하다 (해당 사이클의 실패 테스트가 이미 가드 역할). **단, `coder`(deprecated) 직접 호출 금지.** 컴파일 에러가 **테스트 파일**에 있으면 green-coder가 아니라 **red-writer를 재호출**한다 (테스트 수정은 red-writer 소관). green-coder 수정 후에는 변경 파일에 테스트 파일이 없는지 확인하고, 테스트가 수정되었으면 원복 후 재호출한다 (state.md의 `test-file-hash` 대조).
4. 수정 후 빌드를 **1회 재시도**한다.
5. **재시도 성공** → Step 0-2로 진행.
6. **재시도 실패** → 사용자에게 빌드 에러 표시 후 AskUserQuestion: "빌드 실패. 직접 수정 후 계속 / 중단".

### Step 0-2: Test

**테스트 명령 결정**: config.json `projectTypes`의 `test` 필드를 사용한다. 없으면 → AskUserQuestion: "테스트 검증 명령을 감지하지 못했습니다." 선택지: 사용자가 직접 입력 / 건너뛰기. **조용히 건너뛰지 않는다** — 건너뛰기 선택 시 위험 수용으로 간주하고 trust-ledger에 "테스트 미검증 리뷰" 항목을 기록한다.

**실행 흐름**:
1. 테스트 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 1로 진행.
3. **실패(회귀)** → 깨진 기존 테스트가 이미 RED 역할을 한다. `green-coder`에 깨진 테스트 + 에러를 전달해 통과시킨다 (새 RED 불필요). 직전 정리가 동작을 바꾼 것이 원인이면 `refactor-coder`에 롤백을 요청한다. `coder`(deprecated) 직접 호출 금지. green-coder 수정 후에는 **테스트 파일 무변경**을 확인한다 (무단 수정 감지 시 원복 + "테스트 수정 금지" 재강조 재호출 — 프로덕션 코드로만 해결).
4. 수정 후 테스트를 **1회 재시도**한다.
5. **재시도 성공** → Step 1로 진행.
6. **재시도 실패** → 사용자에게 표시 후 AskUserQuestion: "테스트 실패. 직접 수정 후 계속 / 중단".

### Gate 통과 기준

build, test 모두 통과해야 Step 1로 진행한다. 단일 Gate에서 오케스트레이터가 직접 판단한다 (에이전트 호출 불필요). 경고는 이 Gate에서 차단하지 않는다 — 경고 baseline은 phase-implement Step 0.5(기준선 게이트)가 기록하고, 차단은 verify 게이트(`oh-my-gx:gx-verify`)가 수행한다.

---

각 반복(1~2회)에서:

## Step 1: 변경사항 수집 및 파일 저장

**git인 경우** (작업 경로 기준에 따라 GIT_PREFIX를 붙여 실행):
- **전체 플로우** (phase-setup부터 진행): `git add -A`로 스테이징한 후, **Diff 수집 규칙**에 따라 `--cached` diff를 `DIFF_FILE`에 리다이렉트한다.
- **`--phase review` 단독 실행**: 베이스 브랜치 감지 규칙에 따라 베이스를 결정한다. `git diff $(git merge-base HEAD <base-branch>)...HEAD`를 `DIFF_FILE`에 리다이렉트한다.

**svn인 경우**:
- `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다. staging 없이 한 단계로 끝난다.

### Step 1.1: diff 공백 안전장치

**svn인 경우** → `svn diff`가 0줄이면 "변경사항이 없습니다" 보고 후 중단한다.

**git인 경우** (브랜치 커밋 비교):
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
Task(subagent_type="oh-my-gx:spec-reviewer"):
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

    ## 기계 판정 블록 (출력 맨 마지막, yaml 코드 펜스로 감싼다)
    spec_verdict:
      verdict: PASS | FAIL   # 산문 판정과 일치 (⚠️/❌ 1건 이상이면 FAIL)
      ac_total: {전체 AC 수}
      ac_met: {✅ 건수}
      ac_partial: {⚠️ 건수}
      ac_unmet: {❌ 건수}
      unmet_ids: [{⚠️/❌ AC ID 목록, 없으면 빈 배열}]
```

### Step 2.1: spec-reviewer 결과 판정

오케스트레이터가 결과를 분석한다. **판정 소스 우선순위**:
1. 출력 마지막의 `spec_verdict` YAML 블록을 파싱한다 (`verdict: PASS|FAIL`).
2. 블록이 없거나 파싱 불가하면 산문 판정(SPEC PASS/FAIL 문구 + AC 매트릭스)으로 폴백한다.
3. 블록과 산문 판정이 **상충하면 FAIL로 간주**하고 spec-reviewer를 1회 재호출한다. 재호출도 상충이면 사용자에게 보고한다.

- **SPEC PASS** (모두 ✅) → Step 3 (quality + security)으로 진행
- **SPEC FAIL** (⚠️ 또는 ❌ 1건 이상) → 다음 처리:
  1. 미충족/부분 AC를 사용자에게 표시
  2. AskUserQuestion: "spec 미충족 항목 발견. RGR 사이클로 재구현 시도할까요?"
     - "재구현" → 미충족 AC를 새 태스크로 정의 → `phase-implement`로 복귀 (해당 AC만 RGR)
     - "수동 수정" → 사용자가 코드 수정 후 phase-review 재호출 (execution-log에 "수동 수정 재주입" 기록)
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
Task(subagent_type="oh-my-gx:quality-reviewer"):
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

    [테스트 품질 기준 파일]
    {ANTI_PATTERNS_PATH} — 테스트 코드 품질 판정 시 Read하여 기준으로 사용 (부재 시 평가 영역의 항목 정의로 판정)

    [평가 영역]
    - Critical: 보안 취약점, 데이터 손실, race condition, null pointer, 무한 루프
    - Important: DRY 위반, 단일 책임 위반, 매직 넘버, 잘못된 추상화, 컨벤션 위반, 테스트 코드 품질(모의 동작 검증·테스트 전용 메서드·불완전 모킹 → [동작불변])
    - Minor: 가독성, 주석 개선, import 정리

    [출력 형식]
    ## 코드 품질 리뷰
    ### Critical (N건) — 전부 [동작결함]
    - {파일}:{라인} — {문제}
      - 권고: {수정 방안}
    ### Important (N건) — 항목마다 [동작결함|동작불변] 표기 필수 (오케스트레이터 라우팅 키)
    - {파일}:{라인} — {문제} → [동작결함|동작불변]
      - 권고: {수정 방안}
    ### Minor (N건) — 전부 [동작불변], 비차단
    - ...

    ## 판정
    - Critical 0 + Important 0 → QUALITY PASS
    - Critical N > 0 또는 Important N > 0 → QUALITY FAIL (수정 필요)
    - Minor만 → QUALITY PASS (Minor는 메모만)

    ## 기계 판정 블록 (출력 맨 마지막, yaml 코드 펜스로 감싼다. 각 건수는 위 목록의 항목 수를 다시 세어 일치시킨다)
    quality_verdict:
      verdict: PASS | FAIL   # 산문 판정과 일치 (Critical 또는 Important 1건 이상이면 FAIL)
      critical: {Critical 건수}
      important: {Important 건수}
      important_behavior: {Important 중 [동작결함] 표기 + 무표기 건수}
      minor: {Minor 건수}
```

### Task B: security-auditor (통합 감사)

```
Task(subagent_type="oh-my-gx:security-auditor"):
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

    ## 기계 판정 블록 (출력 맨 마지막, yaml 코드 펜스로 감싼다. 각 건수는 위 목록의 항목 수를 다시 세어 일치시킨다)
    security_verdict:
      critical: {CRITICAL 건수}
      high: {HIGH 건수}
      medium: {MEDIUM 건수}
```

`current-step`을 `"quality-review + security (2단계 병렬)"`로 갱신.

---

## Step 4: 결과 합산 및 처리

두 Task 완료 후:

### Step 4.0: 기계 판정 블록 파싱

각 출력 마지막의 YAML 블록을 우선 파싱한다 (Step 2.1의 `spec_verdict`와 동일한 규칙):

- `quality_verdict`: verdict + 심각도 집계. 블록이 없거나 파싱 불가하면 산문(QUALITY PASS/FAIL 문구 + 섹션별 건수)으로 폴백한다. 블록과 산문 판정이 **상충하면 FAIL로 간주**하고 quality-reviewer를 1회 재호출한다.
- `security_verdict`: CRITICAL/HIGH/MEDIUM 집계. 블록 부재 시 산문 집계로 폴백한다 (verdict 필드 없음 — 집계는 Step 4.3 요약과 4c의 MEDIUM 처리에 사용).
- **집계 불일치 처리 (공통)**: 블록의 건수와 산문 목록의 항목 수가 다르면 **산문 열거를 기준**으로 집계한다 (항목 목록이 원본이고 블록은 요약 — LLM 집계 오류는 모의 검증에서 실측된 사례). 불일치 사실을 Step 4.3 요약에 표기한다.
- 개별 항목의 수정 경로 라우팅(`[동작결함]`/`[동작불변]` 마커, security 동작 변경 분류)은 **기존 산문 계약을 그대로 사용**한다 — 블록은 게이트 판정과 집계만 구조화한다.

### Step 4.1: Trust Ledger 저장

security-auditor 결과와 **quality-reviewer의 Critical/Important 요약**을 `${PROJECT_ROOT}/${DEV_DIR}/trust-ledger.md`에 **Write/Append**한다 (quality 결함도 영속화해야 PR의 Audit Summary와 사후 감사에서 추적된다). 기존 항목(Step 0-2의 "테스트 미검증 리뷰" 위험 수용, Step 2.1의 "미충족 AC" 기록 등)을 **덮어쓰지 않고 보존**한다.

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

> 결함을 **동작 결함**과 **동작 불변 품질 결함**으로 분류하여 수정 경로를 달리한다 (quality-reviewer의 `[동작결함]`/`[동작불변]` 표기 사용).
> - **동작 결함** → RGR 사이클(RED 선행). 결함을 재현하는 실패 테스트가 먼저 있어야 한다 (Iron Law 1).
> - **동작 불변 품질 결함**(DRY/네이밍/매직넘버/추상화 정리) → refactor-coder 단독. 기존 테스트 GREEN 유지하며 정리하므로 새 RED 불필요 (= RGR의 REFACTOR 단계).

```
did_fix = false

# 분류 (무표기 Important는 안전하게 동작 결함으로 간주 → RED 선행)
# security 결함은 마커가 없으므로 동작 변경 여부로 분류한다:
#   동작 변경 동반(인증 우회·입력검증 누락 등) → behavior_defects
#   동작 불변(하드코딩 시크릿 제거·로그 마스킹·설정 변경) → refactor_only
#   모호하면 보수적으로 behavior_defects(RED 선행). 이 기준은 4c의 security MEDIUM에도 동일 적용.
behavior_defects = quality.Critical + (security 중 동작 변경 동반; CRITICAL/HIGH 기본)
                   + (quality.Important 중 [동작결함] 표기 또는 무표기 항목)
refactor_only    = (quality.Important 중 [동작불변] 표기 항목)        # DRY/네이밍/매직넘버/추상화
                   + (security 중 동작 불변이 명백한 항목)            # 시크릿 제거 등

# 4a: 동작 결함 → RGR 사이클 (실패 테스트 선행)
if behavior_defects:
    해당 항목 사용자에게 표시
    AskUserQuestion: "동작 결함을 RGR 사이클로 수정할까요?"
      - "예 (RGR)" → 각 항목을 새 AC로 정의 → phase-implement RGR 사이클 진입 (RED부터)
      - "수동 수정" → 사용자 수정 후 phase-review 재호출 (execution-log에 "수동 수정 재주입" 기록)
      - "이대로 진행" → Trust Ledger에 "수용된 위험" 기록
    did_fix = true (RGR 선택 시)

# 4b: 동작 불변 품질 결함 → refactor-coder 단독 (새 RED 없음)
#  전제: Step0 mechanical gate(build+test 통과)로 이미 GREEN 상태가 보장됨 → refactor-coder의 GREEN 선행 조건 충족
if refactor_only:
    해당 항목 사용자에게 표시
    AskUserQuestion: "동작 불변 정리를 수행할까요?"
      - "예" → Task(subagent_type="oh-my-gx:refactor-coder"):
               입력 = refactor_only 항목들의 {파일:라인 + 권고}를 "정리 대상"으로 전달 + PROJECT_ROOT.
               디스패치 형식(절대 규칙/수행 가능·불가 정리/출력 형식)은 phase-implement Step 2-F를 따르되,
               "정리 대상"은 green 산출물이 아니라 위 리뷰 findings이며 GREEN 기준선은 Step0에서 통과한 전체 테스트다.
               → 정리 후 전체 테스트 GREEN 재확인
      - "건너뛰기" → Trust Ledger/메모에 기록
    did_fix = true (수행 시)

# 4c: 반복 판단
if did_fix:
    → 다음 반복 (Step 2부터 재실행: spec → quality)
else:
    # 동작 결함도 동작 불변 결함도 없는 경우
    if Minor(quality) 또는 MEDIUM(security) 항목 있음:
        항목 목록 표시 + "수정할까요?" 확인
        if 수정 선택:
            # 4a/4b와 동일 분류 적용: Minor(quality)는 전부 동작 불변 → refactor-coder 단독,
            #   security MEDIUM은 위 분류 기준(동작 변경 동반이면 RGR, 아니면 refactor-coder 단독)
            → 단발성 확인 리뷰 (반복 카운트 미포함)
        else:
            → phase-complete
    else:
        → phase-complete (클린 통과)
```

**2회 반복 후 미해결 Critical**: 2회 반복 후에도 Critical이 남으면 사용자에게 명시하고 AskUserQuestion: "수동 수정 후 재리뷰" / "현재 상태로 진행". **"현재 상태로 진행" 선택 시 trust-ledger에 "미해결 Critical 수용" 항목을 기록**하고, "수동 수정 후 재리뷰" 선택 시에는 execution-log에 "수동 수정 재주입"을 기록한다.

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
- ❌ `coder`(deprecated) 직접 호출로 수정 — RGR 사이클 우회 (Iron Law 1 위반)
- ❌ 동작 결함을 실패 테스트 없이 green-coder로 바로 수정 — RED 선행 필수 (Iron Law 1 위반)
- ❌ "Critical이지만 이번엔 그냥 진행" — 사용자 명시 승인 없이 우회 금지

**허용 (오해 주의)**: 동작 불변 품질 결함(DRY/네이밍/매직넘버/추상화 정리)은 `refactor-coder` **단독 호출**로 기존 테스트 GREEN을 유지하며 정리한다. 이는 RGR의 REFACTOR 단계와 동일하므로 Iron Law 1 위반이 아니다 (동작이 바뀌지 않아 새 RED가 불필요). 단, 정리 후 전체 테스트 GREEN을 반드시 재확인한다.

위반 감지 시 즉시 중단하고 spec-reviewer부터 재시작한다.
