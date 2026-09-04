# phase-review: 통합 리뷰 (reviewer 1석 — spec verdict 선행) + Security 병렬

## Iron Law

```
NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED
```

이 Phase는 **reviewer 1석**이 Part 1(spec)과 Part 2(quality)를 한 패스로 수행한다 — Part 1 verdict가 먼저 확정된다 (에이전트 내부 순서 강제). Part 1이 FAIL이어도 Part 2는 수행되어 재구현 라운드에 품질 지적이 함께 전달된다.
security-auditor는 reviewer와 **병렬 가능** (서로 독립).

위반 시 즉시 중단하고 reviewer부터 재시작한다.

---

**최대 2회 반복.**

**문서 로드**: `${PROJECT_ROOT}/${DEV_DIR}/prd.md`와 `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read한다. 파일이 없으면 (`--phase review` 단독 실행 등) 건너뛴다. `ANTI_PATTERNS_PATH`(gx-tdd 스킬 디렉토리의 `references/testing-anti-patterns.md` 절대 경로 — 플러그인 설치 환경에서는 플러그인 베이스 경로 하위)와 `FRONTEND_TESTING_PATH`(같은 규칙의 `references/frontend-testing.md`)를 확정한다.

## Step 0: Mechanical Gate (build + test)

리뷰 에이전트 호출 전에 기계적 검증을 통과시킨다. 실패하는 코드를 리뷰하는 것은 토큰 낭비이다. 이 Gate는 사이클 중 focused만 실행한 implement 단계의 **경계 회귀**를 겸한다 — 기존 스위트 회귀가 여기서 처음 전체 실행으로 검증된다.

프로젝트 타입은 config.json의 `projectTypes`를, 타임아웃은 `timeouts`를 참조한다.

### Step 0-1: Build

**빌드 명령 결정**:

1. `${PROJECT_ROOT}/CLAUDE.md`를 Read하여 빌드/컴파일 명령을 탐색한다. `build`, `compile`, `빌드` 키워드가 포함된 명령을 찾는다. CLAUDE.md가 없으면 다음 단계로.
2. CLAUDE.md에 빌드 명령이 없으면 → config `projectTypes`의 `build` 필드를 사용한다. **SSOT는 config다** — 아래는 기본 템플릿 기준 예시(파생 사본):
   | 프로젝트 타입 | 빌드 명령 (예시) |
   |---------------|---------------|
   | java-spring (gradle) | `./gradlew build -x test` (`build` 필드의 테스트 제외 변형) |
   | node | `bun run build` 또는 `npm run build` (package.json의 scripts.build가 있을 때만. `which bun` → bun, 없으면 npm) |

   `build` 필드가 없거나 빈 값인 타입(인터프리터 언어 등)은 빌드 검증을 건너뛰고, 건너뛰었음을 보고에 명시한다.
3. 프로젝트 타입으로도 결정 불가 → AskUserQuestion: "빌드 검증 명령을 감지하지 못했습니다." 선택지: 사용자가 직접 입력 / 건너뛰기.

**실행 흐름**:
1. 감지된 빌드 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 0-2로 진행.
3. **실패** → 직전 RGR 사이클이 컴파일 미완성 상태일 가능성이 크다. `Task(subagent_type="oh-my-gx:implementer")`에 빌드 에러를 전달하여 컴파일을 통과시킨다. 이는 진행 중인 IMPLEMENT 단계의 연장이므로 **새 RED는 불필요**하다 (해당 사이클의 실패 테스트가 이미 가드 역할). **단, `coder`(deprecated)·`green-coder`(파이프라인 미호출) 직접 호출 금지.** 컴파일 에러가 **테스트 파일**에 있으면 implementer가 아니라 **red-writer를 재호출**한다 (테스트 수정은 red-writer 소관). implementer 수정 후에는 변경 파일에 테스트 파일이 없는지 확인하고, 테스트가 수정되었으면 원복 후 재호출한다 (state.md의 `test-file-hash` 대조). 이 수리는 fix loop 라운드에 계상하지 않는다.

   수리 디스패치는 **RED report 없이 시작하는 수리 모드**다 — 빌드 에러(또는 깨진 테스트 파일 경로 + 에러 전문)와, 오케스트레이터가 깨진 대상으로 조립한 focused 검증 명령(config `focusedTest` 템플릿에 깨진 테스트 파일을 대입. 미지원 타입은 전체 `test` 명령)을 전달한다. 수리 후 전체 확인은 이 Gate의 재시도 실행이 담당한다.
4. 수정 후 빌드를 **1회 재시도**한다.
5. **재시도 성공** → Step 0-2로 진행.
6. **재시도 실패** → 사용자에게 빌드 에러 표시 후 AskUserQuestion: "빌드 실패. 직접 수정 후 계속 / 중단".

### Step 0-2: Test

**테스트 명령 결정**: config.json `projectTypes`의 `test` 필드를 사용한다. 없으면 → AskUserQuestion: "테스트 검증 명령을 감지하지 못했습니다." 선택지: 사용자가 직접 입력 / 건너뛰기. **조용히 건너뛰지 않는다** — 건너뛰기 선택 시 위험 수용으로 간주하고 trust-ledger에 "테스트 미검증 리뷰" 항목을 기록한다.

**실행 흐름**:
1. 테스트 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 1로 진행.
3. **실패(회귀)** → 깨진 기존 테스트가 이미 RED 역할을 한다. `implementer`에 깨진 테스트 + 에러를 전달해 통과시킨다 (새 RED 불필요). 직전 정리가 동작을 바꾼 것이 원인이면 `implementer`에 롤백을 요청한다. `coder`(deprecated) 직접 호출 금지. implementer 수정 후에는 **테스트 파일 무변경**을 확인한다 (무단 수정 감지 시 원복 + "테스트 수정 금지" 재강조 재호출 — 프로덕션 코드로만 해결).

   수리 디스패치는 **RED report 없이 시작하는 수리 모드**다 — 빌드 에러(또는 깨진 테스트 파일 경로 + 에러 전문)와, 오케스트레이터가 깨진 대상으로 조립한 focused 검증 명령(config `focusedTest` 템플릿에 깨진 테스트 파일을 대입. 미지원 타입은 전체 `test` 명령)을 전달한다. 수리 후 전체 확인은 이 Gate의 재시도 실행이 담당한다.
4. 수정 후 테스트를 **1회 재시도**한다.
5. **재시도 성공** → Step 1로 진행.
6. **재시도 실패** → 사용자에게 표시 후 AskUserQuestion: "테스트 실패. 직접 수정 후 계속 / 중단".

### Gate 통과 기준

**복수 타입이 감지되면 전부 실행한다** — `detect` 매칭이 2개 이상이면 각 타입의 build·test를 모두 돌리고 하나라도 실패하면 차단한다 (gx-verify Step 1과 동일 규약). 한쪽만 실행하면 나머지 레이어가 리뷰 대상 코드인데도 기계 검증 없이 통과한다.

build, test 모두 통과해야 Step 1로 진행한다. 단일 Gate에서 오케스트레이터가 직접 판단한다 (에이전트 호출 불필요). 경고는 이 Gate에서 차단하지 않는다 — 경고 baseline은 phase-implement Step 0.5(기준선 게이트)가 기록하고, 차단은 verify 게이트(`oh-my-gx:gx-verify`)가 수행한다.

---

각 반복(1~2회)에서:

## Step 1: 변경사항 수집 및 파일 저장

**git인 경우** (작업 경로 기준에 따라 GIT_PREFIX를 붙여 실행):
- **전체 플로우** (phase-setup부터 진행): `git add -A`로 스테이징한 후, **Diff 수집 규칙**에 따라 `--cached` diff를 `DIFF_FILE`에 리다이렉트한다.
- **`--phase review` 단독 실행**: 베이스 브랜치 감지 규칙에 따라 베이스를 결정한다. `git diff $(git merge-base HEAD <base-branch>)...HEAD -- . ':(exclude).dev'`를 `DIFF_FILE`에 리다이렉트한다.

**svn인 경우**:
- `svn add --force . 2>/dev/null`로 신규 파일을 등록한 뒤 `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다.

### Step 1.1: diff 공백 안전장치

**svn인 경우** → `svn diff`가 0줄이면 "변경사항이 없습니다" 보고 후 중단한다.

**git인 경우** (브랜치 커밋 비교):
`wc -l < ${DIFF_FILE}`로 라인 수를 확인한다. **0줄**이면 사용자가 파이프라인 도중 수동 커밋을 끼워 넣었을 가능성이 있다.

1. 베이스 브랜치가 결정되어 있으면 `${GIT_PREFIX} log {base}..HEAD --oneline`으로 브랜치 커밋 존재 여부 확인.
2. 커밋이 1건 이상이면 "수동 커밋 감지" 경로:
   - AskUserQuestion: "브랜치 diff로 리뷰" / "현재 상태로 진행" / "중단"
   - **브랜치 diff 선택** → `${GIT_PREFIX} diff $(${GIT_PREFIX} merge-base HEAD {base})...HEAD -- . ':(exclude).dev'`를 `DIFF_FILE`에 리다이렉트.
3. 커밋도 없고 diff도 없으면 "변경사항이 없습니다" 보고 후 중단.

---

## Step 2: reviewer + security-auditor (병렬 디스패치)

두 에이전트를 **하나의 메시지에서 동시 Task 호출**한다.

### Task A: reviewer (spec Part 1 + quality Part 2 통합)

```
Task(subagent_type="oh-my-gx:reviewer"):
  description: "Unified review (spec + quality)"
  prompt: |
    당신은 통합 리뷰 전담자입니다. Part 1(spec) verdict를 먼저 확정한 후 Part 2(quality) verdict를 냅니다.

    [Iron Law]
    NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED — Part 1이 FAIL이어도 Part 2를 수행하되, 미충족 AC 관련 지적은 "(재구현 대상 — AC-N)"으로 표기합니다.

    [구현자 보고 불신뢰]
    전달 자료의 산문 정당화는 미검증 주장입니다 — diff로 검증하고, 테스트를 재실행하지 않습니다 (증거는 verify_implement가 확보).

    [PRD]
    - 요구사항: {PRD "요구사항" 섹션}
    - 수용 기준 (G-W-T 시나리오): {PRD "수용 기준" 섹션}

    [설계서]
    - 변경 범위: {design "변경 범위" 섹션}

    [변경사항]
    - diff 파일 경로: {DIFF_FILE} — Read하여 확인

    [코드 맵]
    {코드 맵}

    [프로젝트 컨벤션]
    {CLAUDE.md 컨벤션 또는 기존 코드 스타일}

    [테스트 품질 기준 파일]
    {ANTI_PATTERNS_PATH} — 테스트 코드 품질 판정 시 Read
    {FRONTEND_TESTING_PATH} — diff에 UI 테스트가 포함된 경우에만 Read. 스타일 결합 셀렉터·스타일 값 assert·전체 스냅샷·내부 상태 접근을 [동작불변] Important로 지적

    [작업]
    1. Part 1: 각 AC 충족도 평가(✅/⚠️/❌) + 설계 범위 이탈 → SPEC 판정 + spec_verdict
    2. Part 2: Critical/Important/Minor 분류 + [동작결함|동작불변] 마커 → QUALITY 판정 + quality_verdict

    [출력 형식]
    agents/reviewer.md의 출력 형식을 그대로 따릅니다 — Part 1 매트릭스·판정, Part 2 분류·판정, 맨 마지막에 spec_verdict → quality_verdict 두 YAML 블록 순서 고정.
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

`current-step`을 `"unified-review + security (병렬)"`로 갱신.

---

## (구 Step 3은 Step 2에 통합됨 — 번호는 --resume 호환을 위해 유지)

## Step 4: 결과 합산 및 처리

두 Task 완료 후:

### Step 4.0: 기계 판정 블록 파싱

reviewer의 한 출력에서 `spec_verdict`·`quality_verdict` 두 YAML 블록을, security-auditor 출력에서 `security_verdict` 블록을 각각 우선 파싱한다:

- `spec_verdict`: verdict + AC 집계. 블록이 없거나 파싱 불가하면 산문 판정(SPEC PASS/FAIL 문구 + AC 매트릭스)으로 폴백한다. 블록과 산문 판정이 **상충하면 FAIL로 간주**하고 reviewer를 1회 재호출한다. 재호출도 상충이면 사용자에게 보고한다.
- `quality_verdict`: verdict + 심각도 집계. 블록이 없거나 파싱 불가하면 산문(QUALITY PASS/FAIL 문구 + 섹션별 건수)으로 폴백한다. 블록과 산문 판정이 **상충하면 FAIL로 간주**하고 reviewer를 1회 재호출한다.
- `security_verdict`: CRITICAL/HIGH/MEDIUM 집계. 블록 부재 시 산문 집계로 폴백한다 (verdict 필드 없음 — 집계는 Step 4.3 요약과 4c의 MEDIUM 처리에 사용). 블록과 산문 집계가 모두 부재한 경우의 처리는 아래 **security 집계 미확보 시 처리** 문단을 따른다.
- **집계 불일치 처리 (공통)**: 블록의 건수와 산문 목록의 항목 수가 다르면 **산문 열거를 기준**으로 집계한다 (항목 목록이 원본이고 블록은 요약 — LLM 집계 오류는 모의 검증에서 실측된 사례). 불일치 사실을 Step 4.3 요약에 표기한다.
- 개별 항목의 수정 경로 라우팅(`[동작결함]`/`[동작불변]` 마커, security 동작 변경 분류)은 **기존 산문 계약을 그대로 사용**한다 — 블록은 게이트 판정과 집계만 구조화한다.

**verdict 블록 부재 시 우선순위**: (1) 산문 Part 1 판정(SPEC PASS/FAIL 문구)이 있으면 산문 폴백으로 진행한다. (2) 산문 Part 1 판정 자체가 없으면 reviewer를 1회 재호출한다. (3) 재호출 출력에도 Part 1 판정이 없으면 사용자에게 보고하고 중단한다. quality_verdict 부재도 같은 우선순위를 적용하며, 두 블록 모두 상충·부재인 경우에도 재호출은 합산 1회다.

**security 집계 미확보 시 처리**: (1) 블록과 산문 집계가 모두 부재하면 "집계 0건"이 아니라 "집계 미확보"로 판별한다. (2) security-auditor를 1회 재호출한다 (spec/quality의 재호출 합산 1회와 별도 카운트). (3) 재호출 출력에도 집계가 없으면: 대화형은 AskUserQuestion으로 "위험 수용(원장 기록 후 진행)" / "중단"을 확인하고, 헤드리스(gx-ralph-iterate)는 `<ralph>BLOCKED: security 감사 집계 확보 실패</ralph>`로 종료한다 (현재 gx-ralph 루프는 phase-review를 실행하지 않는다 — 루프는 red-writer/implementer만 디스패치하고 리뷰는 루프 종료 후 대화형 재진입이다. 이 분기는 향후 비대화 리뷰 경로를 위한 예약이다). (4) 위험 수용을 선택하면 Step 4.1에서 trust-ledger에 `security 감사 미확보 — 위험 수용` 항목을 기록한다 (SPEC FAIL의 "이대로 진행"과 같은 취급 — 감사 흔적 없이 통과하는 경로를 남기지 않는다).

reviewer가 `[검증 필요]`를 남기면 오케스트레이터가 해당 focused 테스트를 1회 실행해 결과를 findings에 반영한다.

### SPEC FAIL 처리

분기 선택 전에 Step 4.1(Trust Ledger 저장)을 먼저 수행한다 — 재구현·수동 수정으로 이 라운드가 끝나도 Part 2 quality findings와 병렬 실행된 security 결과가 원장에 남아야 한다.

- **SPEC PASS** (모두 ✅) → Step 4.1 이후 절차 계속
- **SPEC FAIL** (⚠️ 또는 ❌ 1건 이상) → 다음 처리:
  1. 미충족/부분 AC를 사용자에게 표시 (reviewer가 Part 2에서 "(재구현 대상 — AC-N)"으로 표기한 품질 지적도 함께 표시)
  2. AskUserQuestion: "spec 미충족 항목 발견. RGR 사이클로 재구현 시도할까요?"
     - "재구현" → 미충족 AC를 새 태스크로 정의 (reviewer가 표기한 "(재구현 대상)" 품질 지적을 태스크 정의에 함께 전달) → `phase-implement`로 복귀 (해당 AC만 RGR)
     - "수동 수정" → 사용자가 코드 수정 후 phase-review 재호출 (execution-log에 "수동 수정 재주입" 기록)
     - "이대로 진행" → 미충족 AC를 trust-ledger에 추가 기록 후 계속 진행 (위험 수용)
  3. 재구현 후 phase-review 재진입 (Step 0 Mechanical Gate부터 — 반복 카운트에 포함)
- reviewer가 `⚠️ 명세 부족`을 표기한 AC가 있으면 AskUserQuestion으로 "product-owner PRD 보강 후 재리뷰" / "현재 명세로 진행(위험 수용 — trust-ledger 기록)"을 확인한다.

**Iron Law 위반 감지**: reviewer 출력에 `spec_verdict` 없이 `quality_verdict`만 있는 등 Part 1 verdict 없이 Part 2 판정을 수용하려는 시도가 발견되면 Step 4.0의 "verdict 블록 부재 시 우선순위"를 따른다 (즉시 중단은 그 (3) 단계에서만 발생).

### Step 4.1: Trust Ledger 저장

security-auditor 결과와 **reviewer의 Critical/Important 요약(Part 2)**을 `${PROJECT_ROOT}/${DEV_DIR}/trust-ledger.md`에 **Write/Append**한다 (quality 결함도 영속화해야 PR의 Audit Summary와 사후 감사에서 추적된다). 기존 항목(Step 0-2의 "테스트 미검증 리뷰" 위험 수용, SPEC FAIL 처리의 "미충족 AC" 기록 등)을 **덮어쓰지 않고 보존**한다.

### Step 4.2: 통합 findings 구성

```
findings = {
  spec: reviewer 결과 Part 1 (Step 2 Task A),
  quality: reviewer 결과 Part 2 (Step 2 Task A),
  security: security-auditor 결과 (Step 2 Task B)
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

집계를 확보하지 못한 채 위험 수용으로 진행한 경우에는 건수 대신 `Security: 집계 미확보 (위험 수용 — trust-ledger 기록)`을 표시한다.

### Step 4.4: 결과 처리 (의사코드)

> 결함을 **동작 결함**과 **동작 불변 품질 결함**으로 분류하여 수정 경로를 달리한다 (reviewer의 `[동작결함]`/`[동작불변]` 표기 사용).
> - **동작 결함** → RGR 사이클(RED 선행). 결함을 재현하는 실패 테스트가 먼저 있어야 한다 (Iron Law 1).
> - **동작 불변 품질 결함**(DRY/네이밍/매직넘버/추상화 정리) → implementer 정리 모드. 기존 테스트 GREEN 유지하며 정리하므로 새 RED 불필요 (= RGR의 REFACTOR 단계).

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

# 4b: 동작 불변 품질 결함 → implementer 정리 모드 (새 RED 없음)
#  전제: Step0 mechanical gate(build+test 통과)로 이미 GREEN 상태가 보장됨 → implementer 정리 모드의 GREEN 선행 조건 충족
if refactor_only:
    해당 항목 사용자에게 표시
    AskUserQuestion: "동작 불변 정리를 수행할까요?"
      - "예" → Task(subagent_type="oh-my-gx:implementer"):
               정리 모드 — 입력 = refactor_only 항목들의 {파일:라인 + 권고}("정리 대상") + 대상 파일 관련 테스트로 조립한 focused 검증 명령 + PROJECT_ROOT + report 파일 경로(reports/review-cleanup.md — 반복 시 append).
               GREEN 유지·동작 변경 금지 계약은 agents/implementer.md의 REFACTOR 규칙을 따르며, GREEN 기준선은 Step 0에서 통과한 전체 테스트다.
               → 정리 후 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인
      - "건너뛰기" → Trust Ledger/메모에 기록
    did_fix = true (수행 시)

# 4c: 반복 판단
if did_fix:
    → 다음 반복 (Step 0 Mechanical Gate부터 재실행 — 4a RGR 수정이 기존 스위트를 깨뜨렸는지 전체 테스트로 먼저 확인한 뒤 Step 2 reviewer + security)
else:
    # 동작 결함도 동작 불변 결함도 없는 경우
    if Minor(quality) 또는 MEDIUM(security) 항목 있음:
        항목 목록 표시 + "수정할까요?" 확인
        if 수정 선택:
            # 4a/4b와 동일 분류 적용: Minor(quality)는 전부 동작 불변 → implementer 정리 모드,
            #   security MEDIUM은 위 분류 기준(동작 변경 동반이면 RGR, 아니면 implementer 정리 모드)
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
    - unified-review + security (병렬): in_progress
execution-log:
  - phase: review
    step: mechanical-gate
    result: "build ✓, test ✓"
  - phase: review
    agent: reviewer
    result: "SPEC PASS ([Must] 5/5) · Quality: Critical 0, Important 2, Minor 5"
  - phase: review
    agent: security-auditor
    result: "CRITICAL 0, HIGH 1, MEDIUM 3"
```

---

## --resume 호환

- `"mechanical-gate"` → Step 0부터 재실행
- `"unified-review + security (병렬)"` → Step 2부터 재실행
- 구 세션 호환: `"spec-review (1단계)"`/`"quality-review + security (2단계 병렬)"`(2석 세대) → Step 2(통합 디스패치)부터 재실행

---

## 금지 사항 (Iron Law 강제)

이 Phase에서 절대 호출하지 않는 에이전트:
- ❌ `qa-manager` (deprecated — spec-reviewer·quality-reviewer 구 2석 분해를 거쳐 reviewer 1석으로 통합됨)
- ❌ `coder` (deprecated — 수정은 RGR 사이클로 phase-implement 재진입)

이 Phase에서 절대 수행하지 않는 동작:
- ❌ Part 1 verdict 없이 quality 판정 수용 — Iron Law 위반 (처리는 Step 4.0의 "verdict 블록 부재 시 우선순위" 참조)
- ❌ spec-reviewer·quality-reviewer 개별 디스패치 — reviewer 1석으로 통합됨 (구 2석은 정의 삭제됨)
- ❌ `coder`(deprecated) 직접 호출로 수정 — RGR 사이클 우회 (Iron Law 1 위반)
- ❌ 동작 결함을 실패 테스트 없이 implementer(또는 green-coder)로 바로 수정 — RED 선행 필수 (Iron Law 1 위반)
- ❌ "Critical이지만 이번엔 그냥 진행" — 사용자 명시 승인 없이 우회 금지

**허용 (오해 주의)**: 동작 불변 품질 결함(DRY/네이밍/매직넘버/추상화 정리)은 `implementer` **정리 모드**로 기존 테스트 GREEN을 유지하며 정리한다. 이는 RGR의 REFACTOR 단계와 동일하므로 Iron Law 1 위반이 아니다 (동작이 바뀌지 않아 새 RED가 불필요). 단, 정리 후 전체 테스트 GREEN을 반드시 재확인한다.

위반 감지 시 즉시 중단하고 reviewer부터 재시작한다.
