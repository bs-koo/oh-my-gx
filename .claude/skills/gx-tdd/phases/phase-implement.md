# phase-implement: RED-GREEN-REFACTOR 사이클 (TDD 강제)

## Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

이 Phase는 **격리된 3 에이전트가 순차 사이클로 동작**한다:
- **red-writer** → 실패 테스트 작성 (프로덕션 코드 안 봄)
- **green-coder** → 통과 최소 코드 (테스트와 스펙만 봄)
- **refactor-coder** → 안전한 정리 (동작 변경 금지)

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.

---

## Hotfix 모드 분기

오케스트레이터가 `--hotfix` 모드이면:
- Step 0에서 설계서(`design.md`) 로드를 건너뛴다. PRD(`prd.md`)는 로드한다.
- Step 1(구현 계획 승인), Step 1.5(태스크 분해)도 건너뛴다.
- **RGR 사이클은 유지**한다 (hotfix여도 TDD는 강제. Iron Law 1).
  - red-writer 입력: AC (G-W-T) + 기존 테스트 스타일 (설계서 testability 섹션 없음).
  - green-coder 입력: 실패 테스트 + 기존 코드 인터페이스 (설계서 없음).
  - refactor-coder 입력: 정리 대상.
- Step H1~H4 (긴급 보안 감사)는 사이클 완료 후 동일하게 실행한다.

hotfix가 아닌 경우 아래 정상 플로우를 따른다.

---

## Step 0: 문서 로드

- `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read하여 설계서를 로드한다. **testability 섹션**(phase-design에서 test-architect가 추가)을 확인한다.
- `${PROJECT_ROOT}/${DEV_DIR}/prd.md`를 Read하여 PRD를 로드한다. **수용 기준(AC) Given-When-Then 시나리오**를 추출한다.
- testability 섹션이 누락된 설계서면 사용자에게 경고: "testability 평가가 누락된 설계서입니다. phase-design을 재실행해야 RGR 격리 컨텍스트를 구성할 수 있습니다."

## Step 1: 태스크 분해 (오케스트레이터 직접 수행)

설계서의 "구현 순서"와 PRD의 AC를 결합하여 **RGR 사이클 단위 태스크**로 분해한다. 각 태스크는 다음을 만족한다:

1. **단일 AC 또는 단일 컴포넌트**에 매핑된다.
2. **2-15분 단위**로 RED→GREEN→REFACTOR 완료 가능한 크기.
3. 다른 태스크와 **파일 잠금 충돌이 없다** (배치 병렬 조건).

### 1.1 태스크 표 생성

사용자에게 다음 형식으로 제시한다:

```
## RGR 태스크 분해

| # | AC 매핑 | 컴포넌트 | RED (테스트 작성) | GREEN (구현) | REFACTOR (정리) |
|---|---------|---------|-------------------|--------------|-----------------|
| 1 | AC-1 | PaymentLimit | PaymentLimitTest.shouldRejectExceededLimit | PaymentLimit.kt: data class + validate() | 매직 넘버 상수화 |
| 2 | AC-2 | PaymentService | PaymentServiceTest.shouldThrowOnExcess | PaymentService.processPayment() 한도 검증 추가 | 중복 검증 로직 추출 |
| 3 | AC-3 | PaymentController | PaymentControllerE2ETest | PaymentController.updateLimit() 엔드포인트 | — |

### 의존성 (실행 순서)
- T1 (PaymentLimit) → T2 (PaymentService가 PaymentLimit 참조) → T3 (Controller가 Service 참조)
- T1, T2, T3은 **순차 실행** (의존성 체인).
```

### 1.2 사용자 승인 게이트

```
AskUserQuestion(
  question: "RGR 태스크 분해를 확인해주세요.",
  options: [
    { value: "approve", label: "승인 — RGR 사이클 시작" },
    { value: "modify", label: "수정 요청 — 변경할 항목을 알려주세요" }
  ]
)
```

- **승인** → Step 2 (RGR 사이클 시작)
- **수정 요청** → 후속 자유입력 → 분해 갱신 후 재제시 (1회까지)

`current-step`을 `"태스크 분해 승인"`으로 갱신.

### 1.3 건너뛰기 조건

- `--hotfix`: 건너뛴다. AC 1개를 단일 태스크로 간주하여 바로 Step 2 진입.
- 설계서에 "구현 순서" 없음: AC 단위로 자동 분해 후 진입.

---

## Step 2: RGR 사이클 (태스크별 순차)

각 태스크에 대해 **반드시 RED → GREEN → REFACTOR 순서로 실행**한다. 병렬 금지 (Iron Law).

```
for task in tasks:
    current_task = task

    # 2-R: RED
    red_result = dispatch_red(task)
    verify_red(red_result)  # 실패 확인 필수

    # 2-G: GREEN
    green_result = dispatch_green(task, red_result)
    verify_green(green_result)  # 통과 확인 + 전체 테스트 회귀 확인

    # 2-F: REFACTOR
    refactor_result = dispatch_refactor(task, green_result)
    verify_refactor(refactor_result)  # GREEN 유지 확인

    record_to_state(task, results)
```

### Step 2-R: RED (red-writer 디스패치)

```
Task(subagent_type="red-writer"):
  description: "RED: Write failing test for {AC-N}"
  prompt: |
    당신은 RED 단계 테스트 작성 전담자입니다.

    [절대 규칙]
    1. 프로덕션 코드를 작성하지 않습니다. 테스트 파일만 작성합니다.
    2. 기존 프로덕션 코드를 보지 않습니다. AC와 설계서 인터페이스만 봅니다.
    3. 테스트가 반드시 실패해야 합니다.

    [AC (Given-When-Then)]
    {태스크가 매핑된 AC 시나리오}

    [설계서 testability 섹션]
    {대상 컴포넌트의 인터페이스 + 모의 전략}

    [기존 테스트 스타일]
    {프로젝트의 테스트 컨벤션 (네이밍, assertion 라이브러리)}

    [프로젝트 루트]
    {PROJECT_ROOT}

    [작업]
    1. AC를 검증하는 최소 테스트 1개 작성
    2. 테스트 명령 실행으로 실패 확인 (에러 메시지 캡처)
    3. 실패 사유 분류 (NoSuchMethod / assertion / etc)

    [출력 형식]
    - 테스트 파일: {경로}
    - 테스트 코드: {코드 블록}
    - 실패 확인 명령: {명령}
    - 실패 메시지: {메시지 마지막 10줄}
    - 실패 사유: {유형}
```

**verify_red**: 오케스트레이터가 직접 검증.
1. red-writer가 보고한 테스트 명령을 직접 실행.
2. **실패 확인** (통과 시 잘못된 테스트 → red-writer 재호출).
3. 실패 사유가 "이미 구현이 있어서 통과"이면 → AC를 더 좁히도록 사용자에게 안내 후 중단.
4. ✅ 실패 정상 → GREEN으로 진행.

`current-step`을 `"RGR T{N}: RED"`로 갱신.

---

### Step 2-G: GREEN (green-coder 디스패치)

```
Task(subagent_type="green-coder"):
  description: "GREEN: Pass test {test-name}"
  prompt: |
    당신은 GREEN 단계 최소 코드 작성 전담자입니다.

    [절대 규칙]
    1. 실패 테스트 1개만 통과시키는 최소 코드만 작성합니다.
    2. 추가 기능, 에러 핸들링, 검증, 로깅을 미리 넣지 않습니다 (YAGNI).
    3. 다른 테스트가 깨지지 않는지 확인합니다.

    [실패 테스트]
    - 파일: {red 결과의 테스트 파일}
    - 코드: {테스트 코드}
    - 실패 메시지: {메시지}

    [설계서 인터페이스]
    {대상 컴포넌트의 시그니처만}

    [프로젝트 루트]
    {PROJECT_ROOT}

    [작업]
    1. 테스트를 통과시키는 가장 단순한 구현 작성
    2. 테스트 명령 실행으로 통과 확인
    3. 전체 테스트 실행으로 회귀 없음 확인

    [출력 형식]
    - 구현 파일: {경로}
    - 구현 코드: {코드 블록 — 최소}
    - 통과 확인 명령: {명령}
    - 통과 메시지: {N pass}
    - 다른 테스트 영향: {0건 또는 영향 받은 테스트 목록}
```

**verify_green**: 오케스트레이터가 직접 검증.
1. 대상 테스트 통과 확인.
2. 전체 테스트 실행 → 다른 테스트 회귀 없음 확인.
3. **과잉 구현 감지**:
   - 추가된 메서드/필드 중 테스트에서 안 쓰는 것 → 사용자에게 보고: "과잉 구현 감지 ({N줄}). YAGNI 권고로 다음 RED 단계로 미루는 것이 좋습니다. 정리할까요?"
4. ✅ 통과 + 회귀 없음 → REFACTOR로 진행.
5. ❌ 실패 → green-coder 재호출 (에러 메시지 전달, 최대 2회).

`current-step`을 `"RGR T{N}: GREEN"`으로 갱신.

---

### Step 2-F: REFACTOR (refactor-coder 디스패치)

```
Task(subagent_type="refactor-coder"):
  description: "REFACTOR: Clean up {component}"
  prompt: |
    당신은 REFACTOR 단계 정리 전담자입니다.

    [절대 규칙]
    1. 동작을 변경하지 않습니다.
    2. 새 기능을 추가하지 않습니다.
    3. 매 정리 후 테스트를 실행하여 GREEN 상태를 유지합니다.
    4. 테스트가 깨지면 즉시 변경을 되돌립니다.

    [정리 대상]
    - 파일: {green 결과의 구현 파일}
    - 식별된 정리 항목: {중복/네이밍/구조 등}

    [프로젝트 루트]
    {PROJECT_ROOT}

    [수행 가능한 정리]
    - 중복 제거 (Extract Method)
    - 변수/함수 이름 개선 (Rename)
    - 구조 정리 (Extract Class, Move Method)
    - 매직 넘버 상수화

    [수행 불가능한 정리]
    - 동작 변경
    - 새 기능 추가
    - 에러 핸들링 추가
    - 인터페이스 시그니처 변경

    [출력 형식]
    - 정리 항목 (각 항목당 테스트 통과 확인):
      1. {항목 1} → ✅ 테스트 통과
      2. {항목 2} → ❌ 롤백
    - 변경된 파일: {경로 목록}
    - 최종 테스트 결과: {전체 통과}
    - 동작 변경: 없음
```

**verify_refactor**: 오케스트레이터가 직접 검증.
1. 전체 테스트 실행 → 모든 테스트 통과 확인.
2. public 인터페이스 시그니처 변경 없음 확인.
3. ❌ 테스트 실패 → refactor-coder에 즉시 롤백 요청. 롤백 실패 시 사용자에게 보고.
4. ✅ GREEN 유지 → 태스크 완료. 다음 태스크로 진행.

`current-step`을 `"RGR T{N}: REFACTOR"`로 갱신.

---

## Step 3: 정체 감지 + 에스컬레이션 (RGR 사이클)

SKILL.md 정체 감지 규칙을 RGR 사이클에 적용.

| 패턴 | RGR 적용 | 대응 |
|------|---------|------|
| SPINNING (동일 에러 2회) | green-coder가 같은 컴파일 에러 반복 | 1차: hacker 호출 / 2차: researcher 호출 |
| OSCILLATION (A→B→A) | green-coder가 구현 접근법 왕복 | 1차: architect 재검토 / 2차: 사용자 선택 |
| NO_DRIFT (변경 없음) | refactor-coder 결과 diff 없음 | 정리 대상 없음으로 간주, 다음 태스크로 진행 |
| DIMINISHING_RETURNS | green-coder 재호출 2회 후도 실패 | 1차: simplifier (태스크 분해 단순화) / 2차: 사용자 보고 |

**3회 실패 시 아키텍처 격상** (superpowers 패턴):
- 같은 태스크에서 green-coder가 3회 실패하면 → 사이클 중단.
- architect에 "이 태스크의 설계가 잘못된 것 같다. 재설계 필요" 위임.
- architect 결과로 설계서 갱신 후 RGR 사이클 재시작.

---

## Step 4: 사이클 완료 보고

모든 태스크 완료 후 사용자에게 **요약만** 보고한다 (Agent 전문 출력 금지).

```
RGR 사이클 완료: {N}개 태스크

- T1 (AC-1): RED ✅ → GREEN ✅ → REFACTOR ✅
- T2 (AC-2): RED ✅ → GREEN ✅ → REFACTOR ✅ (회귀 0건)
- T3 (AC-3): RED ✅ → GREEN ✅ → REFACTOR — (정리 대상 없음)

전체 테스트: {N pass}, 0 fail
변경 파일: {N}개

특이사항: (있으면)
- T2 GREEN 단계에서 과잉 구현 감지 → 사용자 승인으로 다음 RED로 미룸
```

---

## Step 5: 변경사항 수집 및 파일 저장

phase-review로 인계하기 위해 diff를 수집한다.

1. `${GIT_PREFIX} add -A`로 스테이징한다.
2. **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트한다 (`git diff --cached`를 Bash 단독 실행하지 않는다).

이 스테이징은 phase-review의 diff 수집과 phase-complete의 commit까지 유지된다.

---

## Hotfix 전용 긴급 보안 감사 (hotfix 모드만)

**조건**: `--hotfix` 모드이고 RGR 사이클이 완료된 직후에만 실행한다.

`phase-review`를 hotfix에서 건너뛰면서 security-auditor가 호출되지 않던 공백을 보완한다. CRITICAL/HIGH만 보고하도록 범위를 제한하여 hotfix의 경량성을 유지한다.

**Step H1**: `Task(subagent_type="security-auditor")` — prompt에 다음을 포함:
- 경량 PRD (`${DEV_DIR}/prd.md` Read)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- REFERENCES (있으면)
- "**hotfix 긴급 감사** — CRITICAL/HIGH만 보고할 것. MEDIUM/LOW는 생략. 응답 형식은 `### Hotfix 긴급 감사` 섹션."

**Step H2**: 결과를 `${DEV_DIR}/trust-ledger.md`에 Write/Append.

**Step H3**: 결과 분기:
- CRITICAL/HIGH 0건 → "hotfix 감사 통과" 보고 후 phase-complete로 진행.
- CRITICAL/HIGH 1건 이상 → AskUserQuestion:
  - "자동 수정 시도" → `Task(subagent_type="green-coder")` (RGR 재진입: 보안 항목을 새 AC로 간주하여 새 RED부터)
  - "이대로 진행" → 위험 수용 기록
  - "중단" → state.md에 `status: cancelled`

**Step H4**: `execution-log`에 기록.

---

## state.md 추적

```yaml
steps:
  implement:
    - 태스크 분해 승인: completed
    - "RGR T1 (AC-1)":
        red: completed
        green: completed
        refactor: completed
    - "RGR T2 (AC-2)":
        red: completed
        green: completed
        refactor: skipped (대상 없음)
    - "RGR T3 (AC-3)":
        red: completed
        green: in_progress
        refactor: pending
    - 변경사항 수집: pending
```

`execution-log`에도 사이클 정보를 기록:
```yaml
- phase: implement
  agent: red-writer (T1)
  result: "실패 테스트 작성 + 실패 확인"
- phase: implement
  agent: green-coder (T1)
  result: "최소 구현 + 통과 + 회귀 0건"
- phase: implement
  agent: refactor-coder (T1)
  result: "매직 넘버 상수화 + GREEN 유지"
```

---

## --resume 호환

- `"태스크 분해 승인"` → Step 1.1부터 재실행
- `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: GREEN"` → 해당 태스크의 GREEN부터 재시작 (RED는 file에서 복원)
- `"RGR T{N}: REFACTOR"` → 해당 태스크의 REFACTOR부터 재시작
- `"변경사항 수집"` → Step 5부터 재실행

---

## 금지 사항 (Iron Law 강제)

이 Phase에서 절대 호출하지 않는 에이전트:
- ❌ `coder` (deprecated — red-writer/green-coder/refactor-coder로 분해됨)
- ❌ `qa-manager` (자기점검은 spec-reviewer가 phase-review에서 수행)

이 Phase에서 절대 수행하지 않는 동작:
- ❌ "구현 후 테스트 작성" — Iron Law 1 정면 위반
- ❌ RGR 사이클 병렬 실행 — 격리 깨짐
- ❌ "이번 한 번만" 코드 우선 작성 — 첫 예외가 규칙이 됨
- ❌ 검증 명령 생략 (verify_red/green/refactor) — Iron Law 3 위반

위반 감지 시 즉시 중단하고 RED 단계부터 재시작한다.
