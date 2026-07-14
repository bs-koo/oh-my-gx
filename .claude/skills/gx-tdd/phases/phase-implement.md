# phase-implement: RED-GREEN-REFACTOR 사이클 (TDD 강제)

## Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

이 Phase는 **3 에이전트가 순차 사이클로 동작**한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님)
- **green-coder** → 통과 최소 코드 (입력은 실패 테스트+시그니처로 한정하되, 구현을 위한 기존 코드 Read는 허용 — red-writer 수준의 차단 아님)
- **refactor-coder** → 안전한 정리 (동작 변경 금지)

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.

---

## 핵심 모드 분기 (core)

오케스트레이터가 핵심 모드이면:
- Step 0에서 설계서(`design.md`)와 PRD(`prd.md`) 로드를 건너뛰고, `${DEV_DIR}/ac.md`를 Read하여 **G-W-T 형식 AC**를 추출한다 (phase-requirements core 분기가 저장). ac.md가 없으면(레거시 hotfix→core 재개) `${DEV_DIR}/prd.md`를 대용으로 Read한다.
- **Step 0.5(기준선 게이트)는 실행한다** (RGR이 강제되므로 기준 GREEN 확인과 warnings-baseline 기록이 필요하다).
- Step 1(태스크 분해)과 Step 1.2(승인 게이트)도 건너뛴다.
- **RGR 사이클은 유지**한다 (light여도 TDD는 강제. Iron Law 1).
  - red-writer 입력: ac.md의 AC (G-W-T) + 기존 테스트 스타일 (설계서 testability 섹션 없음).
  - green-coder 입력: 실패 테스트 + 기존 코드 인터페이스 (설계서 없음).
  - refactor-coder 입력: 정리 대상.
- Step H1~H4 (긴급 보안 감사)는 사이클 완료 후 동일하게 실행한다.

핵심 모드가 아닌 경우 아래 전체 모드 플로우를 따른다.

---

## Step 0: 문서 로드

- `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read하여 설계서를 로드한다. **testability 섹션**(phase-design에서 test-architect가 추가)을 확인한다.
- `${PROJECT_ROOT}/${DEV_DIR}/prd.md`를 Read하여 PRD를 로드한다. **수용 기준(AC) Given-When-Then 시나리오**를 추출한다.
- testability 섹션이 누락된 설계서면 사용자에게 경고: "testability 평가가 누락된 설계서입니다. phase-design을 재실행해야 RGR 격리 컨텍스트를 구성할 수 있습니다."
- `ANTI_PATTERNS_PATH`를 확정한다: 이 phase 파일이 위치한 gx-tdd 스킬 디렉토리 기준 `references/testing-anti-patterns.md`의 절대 경로 (플러그인 설치 환경에서는 플러그인 베이스 경로 하위 — 소비 프로젝트 루트가 아니다). red-writer·quality-reviewer 프롬프트에 이 경로를 전달한다.

## Step 0.5: 기준선 게이트 (RGR 시작 전)

RGR 사이클 진입 전에 전체 테스트+빌드를 1회 실행한다 (명령은 config.json `projectTypes`의 test·build. 출력 캡처·경고 수 추출은 **gx-verify Step 2의 경고 측정 규약(SSOT)** 을 따른다):

1. **기준 GREEN 확인**: 기존 테스트가 깨져 있으면 사용자에게 보고하고 진행 여부를 확인한다 (깨진 기준 위에서는 RGR의 회귀 판정이 성립하지 않는다).
2. **warnings-baseline 기록**: 테스트+빌드 출력의 경고 수를 세어 state.md **최상위 필드** `warnings-baseline: N`으로 기록한다. phase-complete의 verify 게이트가 이 값과 비교하여 **이번 구현이 유입한 경고부터** 차단한다 (기존 경고는 허용).
3. 테스트 명령 미감지·추출 불가 시 baseline을 기록하지 않고 execution-log에 "경고 비교 미수행"을 명시한다 (**조용한 0 기록 금지** — 0과 미측정은 다르다).

핵심 모드에서도 실행한다 (RGR이 강제되므로). `current-step`을 `"기준선 게이트"`로 갱신.

## Step 0.7: 구현 방식 확인 (ralph 무인 루프 전환)

기준선 게이트 통과 직후, RGR 사이클 진입 전에 구현 방식을 사용자에게 **1회** 확인한다. 기준선 게이트를 먼저 통과시키는 이유: 깨진 기준 위에서 무인 루프를 돌리면 verify가 매 반복 차단되어 루프가 즉시 BLOCKED로 낭비된다 (warnings-baseline도 이 시점에 기록되어 루프의 verify가 신규 경고를 비교할 수 있다).

**질문 생략 조건** (하나라도 해당하면 질문 없이 Step 1로 직행):
- 핵심 모드 (경량 경로 — PRD가 없어 gx-ralph 진입 조건을 충족하지 않음)
- `--phase implement` 단독 실행 또는 `--resume` 재진입 (진행 방식 의도가 이미 명시됨)
- `VCS_TYPE`이 `svn` (gx-ralph 미지원)

```
AskUserQuestion(
  questions: [{
    question: "기준선 게이트를 통과했습니다. RGR 구현을 어떻게 진행할까요?",
    header: "구현 방식",
    options: [
      { label: "대화형 RGR (Recommended)", description: "이 세션에서 RED→GREEN→REFACTOR 사이클을 바로 진행합니다 (기존 방식)" },
      { label: "ralph 무인 루프", description: "외부 러너가 AC 1건 단위로 무인 반복합니다. 루프 안에서도 RGR 트리오가 유지됩니다 (origin: gx-tdd)" }
    ],
    multiSelect: false
  }]
)
```

- **"대화형 RGR"** → Step 1로 진행한다.
- **"ralph 무인 루프"** → `Skill(skill: "oh-my-gx:gx-ralph")`를 호출한다. 이 시점의 state.md에 `pipeline: gx-tdd` 이력이 있으므로 gx-ralph가 `origin: gx-tdd`로 기록하고, 반복 세션이 red-writer→green-coder→refactor-coder 트리오로 구현한다. **이 파이프라인은 여기서 종료한다** — Step 1 이후를 실행하지 않고, state.md execution-log에 `implement: ralph 전환` 1줄을 기록한다. 루프 종료 후 복귀 경로는 gx-ralph가 안내한다. Skill 호출이 실패하면 직접 우회하지 않고 사용자에게 보고한 뒤 대화형 RGR로 진행할지 확인한다.

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
  questions: [{
    question: "RGR 태스크 분해를 확인해주세요.",
    header: "산출물 확인",
    options: [
      { label: "승인", description: "RGR 사이클 시작" },
      { label: "수정 요청", description: "Other로 이동해서 변경할 항목을 자연어로 입력해주세요" }
    ],
    multiSelect: false
  }]
)
```

- **승인** → Step 2 (RGR 사이클 시작)
- **수정 요청** → 후속 자유입력 → 분해 갱신 후 재제시 (1회까지)

`current-step`을 `"태스크 분해 승인"`으로 갱신.

### 1.3 건너뛰기 조건

- 핵심 모드: 건너뛴다. AC 1개를 단일 태스크로 간주하여 바로 Step 2 진입.
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
Task(subagent_type="oh-my-gx:red-writer"):
  description: "RED: Write failing test for {AC-N}"
  prompt: |
    당신은 RED 단계 테스트 작성 전담자입니다.

    [절대 규칙]
    1. 프로덕션 코드를 작성하지 않습니다. 테스트 파일만 작성합니다.
    2. 기존 프로덕션 코드를 보지 않습니다. AC와 설계서 인터페이스만 봅니다.
    3. 테스트가 반드시 실패해야 합니다.

    [테스트 품질 가드 — 상세: {ANTI_PATTERNS_PATH}. 파일 부재 시 아래 요약이 기준의 전부]
    - 모의(mock)의 동작이 아니라 실제 동작을 검증합니다.
    - 모의 구조는 설계서 testability 섹션의 인터페이스만 근거로 구성합니다 (설계서가 없는 핵심 모드 등에서는 AC와 기존 테스트 스타일만 근거). 없는 필드를 추측하지 않으며, 부족하면 "설계서 인터페이스 불충분"으로 보고합니다.
    - 프로덕션 클래스에 테스트 전용 메서드를 요구하지 않습니다.

    [AC (Given-When-Then)]
    {태스크가 매핑된 AC 시나리오}

    [설계서 testability 섹션]
    {대상 컴포넌트의 인터페이스 + 모의 전략}

    [기존 테스트 스타일]
    {프로젝트의 테스트 컨벤션 (네이밍, assertion 라이브러리)}

    [프로젝트 루트]
    {PROJECT_ROOT}

    [작업]
    1. AC를 검증하는 최소 테스트 1개 작성. 테스트 품질 3기준 준수:
       - 하나의 동작만 검증 (이름에 '그리고'가 필요하면 분리)
       - 이름이 검증하는 동작을 설명
       - 실제 코드 우선, 모의는 불가피할 때만
    2. 테스트 명령 실행으로 실패 확인 (에러 메시지 캡처)
    3. 실패 사유 분류 (NoSuchMethod / assertion / etc)

    [출력 형식]
    - 테스트 파일: {경로}
    - 테스트 코드: {코드 블록}
    - 실패 확인 명령: {명령}
    - 실패 메시지: {메시지 마지막 10줄}
    - 실패 사유: {유형}
    - 참조한 파일: {Read/Grep으로 참조한 파일 전체 목록}
```

**verify_red**: 오케스트레이터가 직접 검증.
1. red-writer가 보고한 테스트 명령을 직접 실행.
2. **실패 확인** (통과 시 잘못된 테스트 → red-writer 재호출).
3. 실패 사유가 "이미 구현이 있어서 통과"이면 → AC를 더 좁히도록 사용자에게 안내 후 중단.
4. **격리 오염 검증**: 보고된 "참조한 파일" 목록에 프로덕션 소스가 포함되어 있으면 → 해당 테스트 폐기 후 red-writer 재호출 (구현에 적응한 오염된 RED일 수 있음).
5. **"설계서 인터페이스 불충분" 보고 처리**: red-writer가 이 보고를 하면 — 전체 모드: phase-design 재실행(테스트 전략 보강) 여부를 사용자에게 확인. 핵심 모드: AskUserQuestion(자유입력)으로 대상 인터페이스 정보를 받아 red-writer에 보강 전달 후 재호출.
6. **테스트 파일 해시 기록**: `git hash-object "{테스트 파일}"` 결과를 state.md 해당 태스크의 `test-file-hash`로 기록한다 (GREEN의 테스트 무결성 기준선. untracked 파일에도 동작. 경로는 따옴표로 감싼다). 동시에 `git status --porcelain > ${DEV_DIR}/rgr-t{N}-porcelain.txt`로 스냅샷을 **파일로 저장**한다 (GREEN에서 **다른 테스트 파일** 변경을 잡기 위한 기준선. **svn 프로젝트는 `svn status`를 사용**. 파일이 DEV_DIR에 남으므로 --resume 재개 시에도 기준선이 유지된다).
7. ✅ 실패 정상 → GREEN으로 진행.

`current-step`을 `"RGR T{N}: RED"`로 갱신.

---

### Step 2-G: GREEN (green-coder 디스패치)

```
Task(subagent_type="oh-my-gx:green-coder"):
  description: "GREEN: Pass test {test-name}"
  prompt: |
    당신은 GREEN 단계 최소 코드 작성 전담자입니다.

    [절대 규칙]
    1. 실패 테스트 1개만 통과시키는 최소 코드만 작성합니다.
    2. 추가 기능, 에러 핸들링, 검증, 로깅을 미리 넣지 않습니다 (YAGNI).
    3. 다른 테스트가 깨지지 않는지 확인합니다.
    4. 테스트 파일을 수정하지 않습니다. 테스트가 실패하면 코드를 고치고, 테스트를 고치지 않습니다. 테스트 자체 결함이 의심되면 수정하지 말고 "테스트 결함 의심"으로 보고합니다.

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
    - 테스트 결함 의심: {없음 | 사유}
```

**verify_green**: 오케스트레이터가 직접 검증. **저비용 검사(1~2번)를 테스트 실행보다 먼저 수행한다.**
1. **테스트 결함 의심 확인**: green-coder가 "테스트 결함 의심"을 보고했으면 (해시 일치 여부와 무관) → 사유 확인 후 **red-writer 재호출**로 테스트를 재작성한다 (green-coder가 테스트를 고치지 않는다).
2. **테스트 무결성 확인**: `git hash-object "{테스트 파일}"`을 재실행하여 verify_red의 `test-file-hash`와 비교하고, `git status --porcelain`(svn은 `svn status`)을 verify_red 스냅샷 파일(`${DEV_DIR}/rgr-t{N}-porcelain.txt`)과 대조하여 **다른 테스트 파일**의 변경 여부도 확인한다. **이전 태스크들의 `test-file-hash`도 재검증**한다 (이미 dirty/untracked 상태라 porcelain 델타에 잡히지 않는 이전 테스트 파일의 내용 수정 감지).
   - 무단 수정 감지 (해시 불일치 또는 타 테스트 파일 변경) → 해당 테스트를 RED 산출물(red 결과의 테스트 코드)로 원복하고 **green-coder 재호출** 1회 ("테스트 수정 금지" 재강조). **재차 위반 시** 사이클을 중단하고 사용자에게 보고한다.
3. 대상 테스트 통과 확인.
4. 전체 테스트 실행 → 다른 테스트 회귀 없음 확인. **전체 테스트 수를 state.md 해당 태스크의 `test-count: N` 필드로 기록**한다 (verify_refactor의 테스트 삭제 감지 기준선 — --resume 시에도 복원된다).
5. **과잉 구현 감지**:
   - 추가된 메서드/필드 중 테스트에서 안 쓰는 것 → 사용자에게 보고: "과잉 구현 감지 ({N줄}). YAGNI 권고로 다음 RED 단계로 미루는 것이 좋습니다. 정리할까요?"
6. ✅ 통과 + 회귀 없음 + 무결성 유지 → REFACTOR로 진행.
7. ❌ 실패 → green-coder 재호출 (에러 메시지 전달, 최대 2회).

`current-step`을 `"RGR T{N}: GREEN"`으로 갱신.

---

### Step 2-F: REFACTOR (refactor-coder 디스패치)

```
Task(subagent_type="oh-my-gx:refactor-coder"):
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
    - 식별된 정리 항목: {중복/네이밍/구조 등 — 오케스트레이터가 green-coder 결과의 구현 diff에서 식별하여 전달. 없으면 "없음"}

    [프로젝트 루트]
    {PROJECT_ROOT}

    [수행 가능한 정리]
    - 중복 제거 (Extract Method)
    - 변수/함수 이름 개선 (Rename)
    - 구조 정리 (Extract Class, Move Method)
    - 매직 넘버 상수화
    - 테스트 코드 정리 (모의 동작 검증을 실제 동작 검증으로 교체, 테스트 전용 프로덕션 메서드를 테스트 유틸리티로 이동 — 검증 강도를 낮추지 않는 범위. 프로덕션 호출자가 0인 테스트 전용 메서드 제거는 허용)

    [수행 불가능한 정리]
    - 동작 변경
    - 새 기능 추가
    - 에러 핸들링 추가
    - 성능 최적화
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
2. **테스트 수 확인**: 1번 실행 결과의 전체 테스트 수가 verify_green 시점(state.md의 `test-count`)보다 줄었으면 사유를 확인한다 (정당한 정리를 넘는 테스트 삭제는 금지 — 무단 삭제면 롤백 요청. 별도 재실행 없이 1번 출력에서 파싱한다).
3. public 인터페이스 시그니처 변경 없음 확인.
4. ❌ 테스트 실패 → refactor-coder에 즉시 롤백 요청. 롤백 실패 시 사용자에게 보고.
5. ✅ GREEN 유지 → 태스크 완료. 다음 태스크로 진행.

`current-step`을 `"RGR T{N}: REFACTOR"`로 갱신.

---

## Step 3: 정체 감지 + 에스컬레이션 (RGR 사이클)

SKILL.md 정체 감지 규칙을 RGR 사이클에 적용.

| 패턴 | RGR 적용 | 대응 |
|------|---------|------|
| SPINNING (동일 에러 2회) | green-coder가 같은 컴파일 에러 반복 | 1차: hacker 호출 / 2차: researcher 호출 |
| OSCILLATION (A→B→A) | green-coder가 구현 접근법 왕복 | 1차: architect 재검토 / 2차: 사용자 선택 |
| NO_DRIFT (변경 없음) | refactor-coder 결과 diff 없음 | 정리 대상 없음으로 간주, 다음 태스크로 진행 |
| DIMINISHING_RETURNS | 재호출 상한 도달 **전**, 시도마다 수정 범위가 줄지 않고 진전 없음 | 1차: simplifier (태스크 분해 단순화) / 2차: 사용자 보고 |

**3회 실패 시 아키텍처 격상** (superpowers 패턴):
- 같은 태스크에서 green-coder가 3회 실패하면(최초 1회 + 재호출 2회 소진) → 사이클 중단. **재호출 상한 소진 시점에는 이 격상 경로가 DIMINISHING_RETURNS 에스컬레이션보다 우선한다.**
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

**git인 경우:**
1. `git add -A`로 스테이징한다.
2. **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트한다 (`git diff --cached`를 Bash 단독 실행하지 않는다).

이 스테이징은 phase-review의 diff 수집과 phase-complete의 commit까지 유지된다.

**svn인 경우:**
1. 스테이징 불필요 (SVN은 staging 개념 없음).
2. `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다.

---

## 핵심 모드 전용 긴급 보안 감사 (core 모드만)

**조건**: 핵심 모드이고 RGR 사이클이 완료된 직후에만 실행한다.

`phase-review`를 light에서 건너뛰면서 security-auditor가 호출되지 않던 공백을 보완한다. CRITICAL/HIGH만 보고하도록 범위를 제한하여 light의 경량성을 유지한다.

**Step H1**: `Task(subagent_type="oh-my-gx:security-auditor")` — prompt에 다음을 포함:
- AC 문서 (`${DEV_DIR}/ac.md` Read — 핵심 모드의 요구사항 명세. 레거시 hotfix→core 재개로 ac.md가 없으면 `${DEV_DIR}/prd.md`를 대용으로 Read)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- REFERENCES (있으면)
- "**핵심 모드 긴급 감사** — CRITICAL/HIGH만 보고할 것. MEDIUM/LOW는 생략. 응답 형식은 `### 핵심 모드 긴급 감사` 섹션."

**Step H2**: 결과를 `${DEV_DIR}/trust-ledger.md`에 Write/Append.

**Step H3**: 결과 분기:
- CRITICAL/HIGH 0건 → "핵심 모드 긴급 감사 통과" 보고 후 phase-complete로 진행.
- CRITICAL/HIGH 1건 이상 → AskUserQuestion:
  - "자동 수정 시도" → **RGR 사이클 재진입**: 보안 항목을 새 AC로 정의하여 red-writer(새 실패 테스트) → green-coder → refactor-coder 순서로 수정한다 (Step 2-R/G/F 재실행). green-coder를 RED 없이 직접 호출하지 않는다.
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

- `"기준선 게이트"` → Step 0.5부터 재실행
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
