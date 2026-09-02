# phase-implement: RED-GREEN-REFACTOR 사이클 (TDD 강제)

## Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

이 Phase는 **2 에이전트가 순차 사이클로 동작**한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님)
- **implementer** → 통과 최소 코드(GREEN) + 안전한 정리(REFACTOR — 동작 변경 금지). 입력은 RED report+시그니처로 한정하되, 구현을 위한 기존 코드 Read는 허용 — red-writer 수준의 차단 아님. 테스트 실행은 focused 집합만

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.

> green-coder·refactor-coder는 이 파이프라인에서 호출하지 않는다 — 단독 스킬(gx-green·gx-refactor)·gx-ralph 루프 전용 (부록 A 참조).

---

## 핵심 모드 분기 (core)

오케스트레이터가 핵심 모드이면:
- Step 0에서 설계서(`design.md`)와 PRD(`prd.md`) 로드를 건너뛰고, `${DEV_DIR}/ac.md`를 Read하여 **G-W-T 형식 AC**를 추출한다 (phase-requirements core 분기가 저장).
- **Step 0.5(기준선 게이트)는 실행한다** (RGR이 강제되므로 기준 GREEN 확인과 warnings-baseline 기록이 필요하다).
- Step 1(태스크 분해)과 Step 1.2(승인 게이트)도 건너뛴다.
- **RGR 사이클은 유지**한다 (핵심 모드여도 TDD는 강제. Iron Law 1).
  - red-writer 입력: ac.md의 AC (G-W-T) + 기존 테스트 스타일 (설계서 testability 섹션 없음).
  - implementer 입력: RED report 경로 + 기존 코드 인터페이스 (설계서 없음) + focused 테스트 명령.
- Step H1~H4 (긴급 보안 감사)는 사이클 완료 후 동일하게 실행한다.

핵심 모드가 아닌 경우 아래 전체 모드 플로우를 따른다.

---

## Step 0: 문서 로드

- `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read하여 설계서를 로드한다. **testability 섹션**(phase-design에서 test-architect가 추가)을 확인한다.
- `${PROJECT_ROOT}/${DEV_DIR}/prd.md`를 Read하여 PRD를 로드한다. **수용 기준(AC) Given-When-Then 시나리오**를 추출한다.
- testability 섹션이 누락된 설계서면 사용자에게 경고: "testability 평가가 누락된 설계서입니다. phase-design을 재실행해야 RGR 격리 컨텍스트를 구성할 수 있습니다."
- `ANTI_PATTERNS_PATH`를 확정한다: 이 phase 파일이 위치한 gx-tdd 스킬 디렉토리 기준 `references/testing-anti-patterns.md`의 절대 경로 (플러그인 설치 환경에서는 플러그인 베이스 경로 하위 — 소비 프로젝트 루트가 아니다). red-writer·quality-reviewer 프롬프트에 이 경로를 전달한다.
- `FRONTEND_TESTING_PATH`를 같은 규칙으로 확정한다 (`references/frontend-testing.md`). **UI 컴포넌트를 다루는 태스크에서만** red-writer·quality-reviewer 프롬프트에 추가로 전달한다 — 백엔드 전용 태스크에 넣으면 프롬프트만 불어난다.
- **UI 태스크 판별**: 설계서 testability 섹션의 `레이어` 필드가 `동작`이면서 대상이 화면 컴포넌트·컴포저블·훅·스토어·라우팅 가드인 경우, 또는 (핵심 모드처럼 설계서가 없으면) 대상 파일이 프로젝트의 프론트엔드 경로에 속하는 경우다.

## Step 0.5: 기준선 게이트 (RGR 시작 전)

RGR 사이클 진입 전에 전체 테스트+빌드를 1회 실행한다 (명령은 config.json `projectTypes`의 test·build. **복수 타입이 감지되면 전부 실행한다** — gx-verify Step 1과 동일 규약이며, 기준선은 verify가 나중에 대조할 대상이므로 같은 명령 집합으로 측정해야 유효하다. 출력 캡처·경고 수 추출은 **gx-verify Step 2의 경고 측정 규약(SSOT)** 을 따른다):

1. **기준 GREEN 확인**: 기존 테스트가 깨져 있으면 사용자에게 보고하고 진행 여부를 확인한다 (깨진 기준 위에서는 RGR의 회귀 판정이 성립하지 않는다).
2. **warnings-baseline 기록**: 테스트+빌드 출력의 경고 수를 세어 state.md **최상위 필드** `warnings-baseline: N`으로 기록한다. phase-complete의 verify 게이트가 이 값과 비교하여 **이번 구현이 유입한 경고부터** 차단한다 (기존 경고는 허용).
3. 테스트 명령 미감지·추출 불가 시 baseline을 기록하지 않고 execution-log에 "경고 비교 미수행"을 명시한다 (**조용한 0 기록 금지** — 0과 미측정은 다르다).
4. **테스트 하네스 부재 감지**: test 명령이 미등록이거나 실행 결과 테스트 수가 0건이면, 테스트 파일 글롭(`**/*test*`, `**/*Test*`, `**/*spec*` — 파일·디렉토리)을 확인한다. 글롭도 0건이면 하네스 부재로 판정하고 안내 후 중단한다:
   "테스트 하네스가 감지되지 않습니다. gx-tdd는 실행 가능한 테스트 없이 진행할 수 없습니다 (Iron Law 1). 테스트 프레임워크를 먼저 구축한 뒤 다시 실행해주세요 (oh-my-gx 저장소 `docs/test-harness-guide.md` 참고 — C: Unity/Ceedling/CppUTest). 하네스 구축 자체를 원하시면 별도 작업으로 요청해주세요."
   state.md를 `status: cancelled`로 갱신하고 파이프라인을 종료한다. 테스트 파일이 존재하는데 실행이 0건이면 하네스 부재가 아니라 명령/경로 문제다 — 1항(기준 GREEN 확인)의 절차를 따른다.
5. **레이어별 하네스 확인**: 4항은 저장소 전체에 테스트가 하나도 없는 경우만 잡는다. 풀스택 저장소에서는 **한쪽 레이어에만 하네스가 있는 상태**가 더 흔하고, 이때 4항은 통과해버린 뒤 해당 레이어의 RED에서 사이클이 정체된다. 진입 전에 미리 확인한다 — 아래 "레이어별 하네스 게이트" 참조.

핵심 모드에서도 실행한다 (RGR이 강제되므로). `current-step`을 `"기준선 게이트"`로 갱신.

### 레이어별 하네스 게이트

설계서 testability 섹션에서 `러너: 없음 — 하네스 필요`로 표시된 동작 컴포넌트를 수집한다 (설계서가 없는 핵심 모드에서는 AC가 가리키는 대상 경로로 판별한다). 해당 항목이 없으면 이 게이트를 건너뛴다.

러너가 없는 레이어가 1건 이상이면 **RGR 진입 전에 멈추고** 사용자에게 분기를 제시한다. 그대로 진행하면 그 레이어의 RED에서 "실패"가 아니라 "실행 불가"가 되어 red-writer 재호출만 소진된다.

```
AskUserQuestion(
  questions: [{
    question: "{레이어}에 테스트 러너가 감지되지 않습니다. 설계에 해당 컴포넌트 {N}건이 포함되어 있습니다. 어떻게 진행할까요?",
    header: "하네스 게이트",
    options: [
      { label: "하네스 구축 후 재실행", description: "테스트 러너를 먼저 설치합니다. 러너가 없으면 실패 테스트를 쓸 수 없어 gx-tdd로는 구축할 수 없습니다 — oh-my-gx:gx-dev로 별도 수행 후 이 파이프라인을 재개하세요" },
      { label: "해당 AC 제외 후 진행", description: "러너가 있는 레이어의 AC만 RGR로 구현합니다. 제외한 AC는 trust-ledger에 기록되며, 그 부분은 별도 작업이 필요합니다" },
      { label: "중단", description: "요구사항 범위를 다시 정의합니다" }
    ],
    multiSelect: false
  }]
)
```

- **"하네스 구축 후 재실행"** → 대상 레이어와 권장 러너를 안내하고 파이프라인을 중단한다 (`status: cancelled`). 프론트엔드면 `references/frontend-testing.md` §8의 안내를 함께 전달한다.
- **"해당 AC 제외 후 진행"** → **프론트 AC 제외**(또는 러너 없는 해당 레이어의 AC 제외)로 처리한다. 제외 항목을 `${DEV_DIR}/trust-ledger.md`의 `### 위험 수용`에 `- [하네스 부재 AC 제외] {AC-N}: {레이어} 러너 없음 (implement/Step 0.5)` 형식으로 기록하고, 태스크 분해에서 해당 AC를 빼고 진행한다. **제외 후 남은 AC가 0건이면** 구현 대상이 없으므로 중단하고 보고한다.
- **"중단"** → `status: cancelled`.

이 게이트는 모노레포 복합 명령(`references/frontend-testing.md` §7)이 등록되어 있어도 동작한다 — 명령이 등록되었는지가 아니라 **그 레이어에 실행 가능한 테스트가 있는지**를 본다.

## Step 0.7: gx-ralph 전환 (--ralph 전용)

state.md `flags`에 `--ralph`가 **없으면 이 Step을 건너뛰고 Step 1로 직행한다** — 기본 경로에서는 묻지 않는다 (v1.23.0에서 진입 질문을 제거했다. 무인 루프는 명시적 opt-in — `--ralph` 플래그 또는 "랄프로 …" 발화 — 으로만 진입하며, 의도 파싱이 phase-setup Step 7을 통해 `flags`에 정규화 기록한다). 있으면 기준선 게이트 통과 직후, RGR 사이클 진입 전에 아래 전환 절차를 실행한다. 기준선 게이트를 먼저 통과시키는 이유: 깨진 기준 위에서 무인 루프를 돌리면 verify가 매 반복 차단되어 루프가 즉시 BLOCKED로 낭비된다 (warnings-baseline도 이 시점에 기록되어 루프의 verify가 신규 경고를 비교할 수 있다).

**방어 조건** (`--ralph`가 있어도 하나라도 해당하면 무시하고 "gx-ralph 전환을 건너뜁니다 — {사유}" 1줄 안내 후 Step 1로 직행. 의도 파싱의 RALPH 우선순위 규칙이 정상 경로에서 이 조합을 막지만, state.md를 손으로 고친 경우 등을 방어한다):
- 핵심 모드 (경량 경로 — PRD가 없어 gx-ralph 진입 조건을 충족하지 않음)
- `--phase implement` 단독 실행 (구현 단독 실행 의도가 명시됨)
- `VCS_TYPE`이 `svn` (gx-ralph 미지원)

`--resume` 재진입은 방어 조건이 **아니다** — 재개된 state.md의 `flags`에 `--ralph`가 있으면 그대로 전환한다. PRD·설계 승인 도중 세션이 유실된 정당한 opt-in을 재개 시 조용히 대화형으로 바꾸지 않는다 (구 버전 state.md에는 `--ralph`가 존재하지 않으므로 별도 방어가 필요 없다).

**전환 절차**: `Skill(skill: "oh-my-gx:gx-ralph")`를 호출한다. 이 시점의 state.md에 `pipeline: gx-tdd` 이력이 있으므로 gx-ralph가 `origin: gx-tdd`로 기록하고, 반복 세션이 red-writer→green-coder→refactor-coder 트리오로 구현한다. **이 파이프라인은 여기서 종료한다** — Step 1 이후를 실행하지 않고, state.md execution-log에 `implement: ralph 전환` 1줄을 기록한다. 루프 종료 후 복귀 경로는 gx-ralph가 안내한다. `MODEL_PROFILE`이 `eco`이면 전환 시 1줄 안내한다: "ralph 루프는 모델 프로파일(eco)을 아직 지원하지 않습니다 — 반복은 GX_RALPH_MODEL 미지정 시 에이전트 기본 모델(표준)로 실행됩니다." Skill 호출이 실패하면 직접 우회하지 않고 사용자에게 보고한 뒤 대화형 RGR로 진행할지 확인한다.

## Step 1: 태스크 분해 (오케스트레이터 직접 수행)

설계서의 "구현 순서"와 PRD의 AC를 결합하여 **RGR 사이클 단위 태스크**로 분해한다. 각 태스크는 다음을 만족한다:

1. **단일 AC 또는 단일 컴포넌트**에 매핑된다. 단, **같은 패턴의 소형 변경으로 환산되는 AC들**(동일 검증 로직의 필드별 반복, 동일 형태의 매핑 추가 등)은 하나의 태스크로 배칭할 수 있다 — RED는 테이블 드리븐 또는 케이스별 테스트를 한 파일에 작성하고, 한 번의 R→I 사이클로 처리하며, 태스크 표의 AC 매핑에 `AC-2~AC-4 (배칭)` 형태로 표기해 승인 게이트에서 확인받는다. 분리 기준: 독자적 판단·독자적 테스트 전략·독자적 리뷰 표면이 필요한 작업만 태스크를 분리한다.
2. **2-15분 단위**로 RED→IMPLEMENT 완료 가능한 크기.
3. 다른 태스크와 **파일이 겹치지 않는다** (사이클 간 간섭 방지 — 태스크는 순차 실행된다). 겹치면 앞 태스크의 `test-file-hash`·porcelain 스냅샷 기준선이 뒤 태스크의 변경으로 오염되어 무결성 검증이 오탐한다.

### 1.1 태스크 표 생성

사용자에게 다음 형식으로 제시한다:

```
## RGR 태스크 분해

| # | AC 매핑 | 컴포넌트 | RED (테스트 작성) | IMPLEMENT (구현+정리) |
|---|---------|---------|-------------------|------------------------|
| 1 | AC-1 | PaymentLimit | PaymentLimitTest.shouldRejectExceededLimit | PaymentLimit.kt: data class + validate() → 매직 넘버 상수화 |
| 2 | AC-2, AC-3 (배칭) | PaymentService | PaymentServiceTest (케이스 2건) | PaymentService.processPayment() 한도 검증 추가 → 중복 검증 로직 추출 |
| 3 | AC-4 | PaymentController | PaymentControllerE2ETest | PaymentController.updateLimit() 엔드포인트 |

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

각 태스크에 대해 **반드시 RED → IMPLEMENT(GREEN+REFACTOR) 순서로 실행**한다. 병렬 금지 (Iron Law).

**진입 준비**: `mkdir -p ${DEV_DIR}/reports`를 실행한다 (핵심 모드처럼 Step 1을 건너뛴 경로 포함 — 모든 진입 경로 공통). 이후 에이전트 보고는 `reports/t{N}-red.md`·`reports/t{N}-impl.md`에 파일로 저장되고, 인계는 **파일 경로로만** 이루어진다 (전문 인라인 전달 금지 — 컨텍스트 경량화). `.dev/` 공유 정책에 따라 커밋에 포함된다.

```
for task in tasks:
    current_task = task

    # 2-R: RED
    red_result = dispatch_red(task)          # report: reports/t{N}-red.md
    verify_red(red_result)                   # 실패 확인 필수 (오케스트레이터 직접 실행)

    # 2-I: IMPLEMENT (GREEN + REFACTOR 통합)
    impl_result = dispatch_implementer(task, red_report_path)   # report: reports/t{N}-impl.md
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증

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
    - **깨짐 명명**: 테스트 본문 작성 전에 "이 테스트를 실패시키는 프로덕션 변경"을 명명한다. 명명할 수 없으면 관찰 가능한 동작으로 재설계한다.
    - 기댓값을 검증 대상 코드로 계산하지 않는다 (미러 assertion 금지 — 손으로 도출한 리터럴 사용).
    - 상수값·문구·내부 구조만 검증하는 change detector를 만들지 않는다 — 결정에 의존하는 동작을 검증한다.
    - 완성 전 변이 점검: 잘못된 상수/인자·잘못된 분기·부작용 누락·빈 반환·경계 입력 미검증 중 최소 하나가 이 테스트에 잡히는지 확인한다.

    [UI 가드 — UI 태스크에서만 포함. 상세: {FRONTEND_TESTING_PATH} §3~4]
    - 셀렉터는 role/접근성 이름 > 화면에 보이는 텍스트 > 라벨 > data-testid 순으로 고릅니다.
      CSS 클래스(.text-red-500)와 구조 셀렉터(div > div:nth-child(2))는 쓰지 않습니다 —
      스타일이나 마크업을 바꾸는 순간 동작이 그대로인데도 테스트가 깨지고, 그게 팀이 테스트를 지우게 되는 경로입니다.
    - **스타일 값**(색상·여백·폰트·정렬·애니메이션)에 assert를 걸지 않습니다. 검증 대상은
      무엇이 노출되는가 / 무엇이 잠기는가(disabled·aria-*) / 무엇이 emit·호출되는가 / 무엇이 발생하지 않는가 입니다.
    - 렌더 결과 전체 스냅샷(toMatchSnapshot)을 쓰지 않습니다. 무엇을 검증하는지 드러나지 않고,
      의도한 변경과 회귀를 구분하지 못합니다.
    - 컴포넌트 내부 상태(wrapper.vm, 인스턴스 필드)를 들여다보지 않습니다. 구현 세부사항입니다.
    - 프로젝트에 이미 테스트 컨벤션이 있으면 그것을 우선합니다 (일관성이 이 규약보다 중요합니다).

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

    [report 파일]
    {reports/t{N}-red.md} — 테스트 코드 전문·실패 확인 명령·실패 메시지를 이 파일에 Write하고, 최종 메시지에는 아래 출력 형식의 요약만 반환하십시오

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
6. **테스트 파일 해시 기록**: `git hash-object "{테스트 파일}"` 결과를 state.md 해당 태스크의 `test-file-hash`로 기록한다 (GREEN의 테스트 무결성 기준선. untracked 파일에도 동작. 경로는 따옴표로 감싼다). 동시에 `git status --porcelain > ${DEV_DIR}/rgr-t{N}-porcelain.txt`로 스냅샷을 **파일로 저장**한다 (GREEN에서 **다른 테스트 파일** 변경을 잡기 위한 기준선. **svn 프로젝트는 `svn status`를 사용**. 파일이 DEV_DIR에 남으므로 --resume 재개 시에도 기준선이 유지된다). 테스트 파일 경로를 state.md 해당 태스크의 `test-file`로 기록한다 (focused 집합 조립에 사용).
7. **report 저장 확인**: `reports/t{N}-red.md`가 존재하고 테스트 코드·실패 메시지를 담고 있는지 확인한다. 다음 단계(2-I) 인계는 이 파일 경로로만 한다.
8. ✅ 실패 정상 → IMPLEMENT(2-I)로 진행.

`current-step`을 `"RGR T{N}: RED"`로 갱신.

---

### Step 2-I: IMPLEMENT (implementer 디스패치 — GREEN+REFACTOR 통합)

```
Task(subagent_type="oh-my-gx:implementer"):
  description: "IMPLEMENT: Pass & clean {component}"
  prompt: |
    당신은 GREEN+REFACTOR 통합 구현 전담자입니다.

    [절대 규칙]
    1. 테스트 파일을 수정하지 않습니다. 테스트가 실패하면 코드를 고치고, 테스트를 고치지 않습니다. 테스트 자체 결함이 의심되면 수정하지 말고 "테스트 결함 의심"으로 보고합니다.
    2. GREEN: 실패 테스트를 통과시키는 최소 코드만 작성합니다 (YAGNI — 추가 기능/에러 핸들링/검증/로깅 금지).
    3. REFACTOR: 동작 변경 금지. 매 정리 후 focused 테스트로 GREEN 유지 확인, 깨지면 즉시 롤백.
    4. 테스트 실행은 아래 focused 명령만 사용합니다. 전체 스위트를 실행하지 않습니다.
    5. 보고 전 self-review(완전성/품질/규율/테스트 4관점)를 수행하고 발견 즉시 수정합니다.

    [RED report]
    - 경로: {reports/t{N}-red.md} — Read하여 실패 테스트(파일·코드·실패 메시지)를 파악하십시오

    [설계서 인터페이스]
    {대상 컴포넌트의 시그니처만}

    [focused 테스트 명령]
    {오케스트레이터가 조립한 명령 — 대상 테스트 + 이번 파이프라인 실행의 신규 테스트 전부}

    [report 파일]
    {reports/t{N}-impl.md} — 전문 보고를 이 파일에 Write하십시오 (agents/implementer.md의 report 형식)

    [프로젝트 루트]
    {PROJECT_ROOT}

    [반환 형식 — 15줄 이내]
    - Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
    - 변경 파일 / 테스트 1줄 요약 / 우려사항 / report 경로
```

**focused 테스트 명령 조립**: config.json `projectTypes.{타입}.focusedTest` 템플릿을 사용한다. 대상은 이 태스크의 테스트 파일 + 이번 파이프라인 실행에서 이전 태스크들이 만든 신규 테스트 파일 전부(state.md 각 태스크의 `test-file` 기록)다.
- `{files}` 플레이스홀더: 테스트 파일 경로들을 공백 구분으로 치환한다 (예: `npx vitest run src/a.spec.ts src/b.spec.ts`).
- `{pattern}` 플레이스홀더: 각 테스트 파일명(확장자 제외)에서 유도한 클래스 글롭 `*.{파일명}`으로 치환하고, 복수 파일이면 플레이스홀더를 포함한 인자를 반복한다 (예: `./gradlew test --tests *.PaymentLimitTest --tests *.PaymentServiceTest`).
- `focusedTest` 필드가 없으면 해당 타입의 전체 `test` 명령을 사용하고 execution-log에 `"focused 미지원 — 전체 실행 폴백"`을 기록한다.

**verify_implement**: 오케스트레이터가 직접 검증. **저비용 검사(1~3번)를 테스트 실행보다 먼저 수행한다.**
1. **Status 분기**: `NEEDS_CONTEXT` → 요청된 정보를 보강해 재디스패치 (라운드 미소모, 태스크당 최대 2회 — 초과 시 BLOCKED로 승격해 처리한다). `BLOCKED` → 컨텍스트 보강 / 모델 격상 / 태스크 분할 / 설계 재확인 중 판정 후 처리. `DONE_WITH_CONCERNS` → report의 우려를 Read하고 정합성 문제면 fix 라운드로, 관찰이면 기록 후 진행.
2. **테스트 결함 의심 확인**: 보고됐으면 사유 확인 후 **red-writer 재호출**로 테스트를 재작성한다 (implementer가 테스트를 고치지 않는다).
3. **테스트 무결성 확인**: `git hash-object "{테스트 파일}"`을 재실행하여 verify_red의 `test-file-hash`와 비교하고, `git status --porcelain`(svn은 `svn status`)을 verify_red 스냅샷 파일(`${DEV_DIR}/rgr-t{N}-porcelain.txt`)과 대조한다 — **대조는 테스트 파일 라인만 필터**하여 수행한다(판별 글롭은 Step 0.5 4항의 테스트 파일 글롭 `**/*test*`·`**/*Test*`·`**/*spec*` 재사용. `.dev/` 경로 라인은 제외). **이전 태스크들의 `test-file-hash`도 재검증**한다. 무단 수정 감지 → 해당 테스트를 RED 산출물로 원복하고 implementer 재호출 1회 ("테스트 수정 금지" 재강조 — fix 라운드와 별도 카운트). 재차 위반 시 사이클 중단·사용자 보고.
4. **focused 집합 직접 실행**: 위 focused 명령을 오케스트레이터가 1회 직접 실행한다 — 통과 목격(증거 주체는 오케스트레이터, verify_red와 대칭) + 결과의 테스트 수를 state.md 해당 태스크의 `test-count`로 기록한다(직전 태스크의 같은 방식 값과 비교해 감소 시 사유 확인 — 무단 삭제면 롤백 요청). **전체 스위트는 실행하지 않는다** — 전체 회귀는 사이클 경계(전체 모드: phase-review Step 0 Mechanical Gate / 핵심 모드·`--phase implement` 단독: Step 3.5)가 담당한다.
5. **과잉 구현 감지**: 추가된 메서드/필드 중 테스트에서 안 쓰는 것 → 사용자에게 보고: "과잉 구현 감지. YAGNI 권고로 다음 RED 단계로 미루는 것이 좋습니다. 정리할까요?"
6. ✅ 통과 + 무결성 유지 → 태스크 완료, 다음 태스크로 진행.
7. ❌ 실패 → **fix loop 진입** (아래).

**fix loop (실패 시 — 태스크당 최대 5라운드)**:

| 라운드 | 방식 | 모델 |
|--------|------|------|
| 1~3 | **같은 implementer를 재개** — 하네스가 서브에이전트 재개(후속 메시지)를 지원하면 그 방식으로 미해결 항목을 전달, 지원하지 않으면 report 파일 경로를 실은 fresh 디스패치 (report가 영속 기억) | sonnet |
| 4~5 | **fresh 디스패치 + 모델 격상** (`model: "opus"` 오버라이드) — 프롬프트에 "이전 구현자가 {r-1}회 시도했다. report 파일에서 시도 내역을 읽어라"를 포함 | opus |

- 매 라운드: implementer가 수정 → focused 재실행 → fix report를 같은 report 파일에 append → 상태 반환 → 오케스트레이터가 verify_implement 재수행. `current-step`을 `"RGR T{N}: FIX R{r}"`로, state.md 해당 태스크에 `fix-round: {r}/5`를 기록한다.
- 모델 격상은 "실패의 대응"으로 **모델 프로파일과 독립**이다 — eco 세션에서도 라운드 4~5는 opus로 격상한다.
- **라운드 5 소진 시**: 사이클 중단 + AskUserQuestion — "수동 수정 후 계속" / "태스크 스킵 (위험 수용 — trust-ledger 기록)" / "중단".

`current-step`을 `"RGR T{N}: IMPLEMENT"`로 갱신.

---

## Step 3: 정체 감지 + 에스컬레이션 (RGR 사이클)

SKILL.md 정체 감지 규칙을 RGR 사이클에 적용.

| 패턴 | RGR 적용 | 대응 |
|------|---------|------|
| SPINNING (동일 에러 2회) | implementer가 같은 컴파일 에러 반복 | 1차: hacker 호출 / 2차: researcher 호출 |
| OSCILLATION (A→B→A) | implementer가 구현 접근법 왕복 | 1차: architect 재검토 / 2차: 사용자 선택 |
| NO_DRIFT (변경 없음) | implementer의 REFACTOR 결과 diff 없음 | 정리 대상 없음으로 간주, 다음 태스크로 진행 |
| DIMINISHING_RETURNS | 재호출 상한 도달 **전**, 시도마다 수정 범위가 줄지 않고 진전 없음 | 1차: simplifier (태스크 분해 단순화) / 2차: 사용자 보고 |

**fix loop 소진 시 아키텍처 격상** (superpowers 패턴):
- fix loop **라운드 4 진입(모델 격상)이 DIMINISHING_RETURNS 에스컬레이션보다 우선한다.** 라운드 5까지 소진하면 사이클을 중단하고 소진 처리(Step 2-I)를 따르되, 실패 양상이 설계 결함을 가리키면 architect에 "이 태스크의 설계가 잘못된 것 같다. 재설계 필요"를 위임한다.
- architect 결과로 설계서 갱신 후 RGR 사이클 재시작.

---

## Step 3.5: 경계 회귀 (핵심 모드·--phase implement 단독 전용)

**핵심 모드** 또는 **`--phase implement` 단독 실행**이면 전체 테스트를 1회 실행한다 — 사이클 중 focused만 돌렸으므로 기존 스위트 회귀를 여기서 확인한다 (전체 모드는 phase-review Step 0 Mechanical Gate가 이 역할을 겸하므로 건너뛴다). 실패 시 깨진 테스트를 implementer에 전달해 수정한다 (fix loop 규칙 적용).

---

## Step 4: 사이클 완료 보고

모든 태스크 완료 후 사용자에게 **요약만** 보고한다 (Agent 전문 출력 금지).

```
RGR 사이클 완료: {N}개 태스크

- T1 (AC-1): RED ✅ → IMPLEMENT ✅
- T2 (AC-2, AC-3 배칭): RED ✅ → IMPLEMENT ✅ (fix 라운드 1회)
- T3 (AC-4): RED ✅ → IMPLEMENT ✅ (정리 대상 없음)

focused 누적: {N pass}, 0 fail (전체 회귀는 경계에서 — 전체 모드: review Step 0 / 핵심 모드·단독: Step 3.5)
변경 파일: {N}개

특이사항: (있으면)
- T2 IMPLEMENT 단계에서 과잉 구현 감지 → 사용자 승인으로 다음 RED로 미룸
```

---

## Step 5: 변경사항 수집 및 파일 저장

phase-review로 인계하기 위해 diff를 수집한다.

**git인 경우:**
1. `git add -A`로 스테이징한다.
2. **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트한다 (`git diff --cached`를 Bash 단독 실행하지 않는다).

이 스테이징은 phase-review의 diff 수집과 phase-complete의 commit까지 유지된다.

**svn인 경우:**
1. **신규 파일 등록**: `svn add --force . 2>/dev/null`로 unversioned 신규 파일을 일괄 등록한다 (`--force`는 versioned 디렉토리 하위 추가를 허용하며 svn:ignore 패턴은 존중된다. RGR이 만든 신규 테스트·구현 파일은 add 없이는 `svn diff`에 실리지 않아 리뷰가 오판한다).
2. `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다.

---

## 핵심 모드 전용 긴급 보안 감사 (core 모드만)

**조건**: 핵심 모드이고 RGR 사이클이 완료된 직후에만 실행한다.

`phase-review`를 핵심 모드에서 건너뛰면서 security-auditor가 호출되지 않던 공백을 보완한다. CRITICAL/HIGH만 보고하도록 범위를 제한하여 핵심 모드의 경량성을 유지한다.

**Step H1**: `Task(subagent_type="oh-my-gx:security-auditor")` — prompt에 다음을 포함:
- AC 문서 (`${DEV_DIR}/ac.md` Read — 핵심 모드의 요구사항 명세)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- REFERENCES (있으면)
- "**핵심 모드 긴급 감사** — CRITICAL/HIGH만 보고할 것. MEDIUM/LOW는 생략. 응답 형식은 `### 핵심 모드 긴급 감사` 섹션."

**Step H2**: 결과를 `${DEV_DIR}/trust-ledger.md`에 Write/Append.

**Step H3**: 결과 분기:
- CRITICAL/HIGH 0건 → "핵심 모드 긴급 감사 통과" 보고 후 phase-complete로 진행.
- CRITICAL/HIGH 1건 이상 → AskUserQuestion:
  - "자동 수정 시도" → **RGR 사이클 재진입**: 보안 항목을 새 AC로 정의하여 red-writer(새 실패 테스트) → implementer 순서로 수정한다 (Step 2-R/2-I 재실행). implementer를 RED 없이 직접 호출하지 않는다.
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
        test-file: src/test/.../PaymentLimitTest.java   # verify_red 기록 — focused 집합 조립에 사용
        test-file-hash: 3ca970cc...   # verify_red 기록 — verify_implement 무결성 비교 기준선
        test-count: 47                # verify_implement 기록 — focused 직접 실행 결과 (테스트 삭제 감지 기준선)
        report: reports/t1-impl.md
        impl: completed
    - "RGR T2 (AC-2)":
        red: completed
        impl: in_progress
        fix-round: 2/5
    - "RGR T3 (AC-3)":
        red: pending
        impl: pending
    - 변경사항 수집: pending
```

`execution-log`에도 사이클 정보를 기록:
```yaml
- phase: implement
  agent: red-writer (T1)
  result: "실패 테스트 작성 + 실패 확인"
- phase: implement
  agent: implementer (T1)
  result: "최소 구현 + focused 3/3 pass + 매직 넘버 상수화"
```

---

## --resume 호환

- `"기준선 게이트"` → Step 0.5부터 재실행
- `"태스크 분해 승인"` → Step 1.1부터 재실행
- `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: IMPLEMENT"` → 해당 태스크의 implementer 재디스패치 (RED report는 reports/t{N}-red.md에서 복원)
- `"RGR T{N}: FIX R{r}"` → 해당 태스크의 fix loop 라운드 {r}부터 재개 (report 파일이 영속 기억)
- 구 세션 호환: `"RGR T{N}: GREEN"`/`"RGR T{N}: REFACTOR"`(3석 세대) → 해당 태스크를 implementer 재디스패치로 이어받는다. red 산출물(테스트 파일)은 유효하므로 RED 재실행 불필요. reports/가 없으므로 이 재개에 한해 테스트 코드·실패 메시지의 인라인 인계를 허용하고 execution-log에 "2석 전환 재개 — 인라인 인계"를 기록한다. 추가: 구 세션 state에는 `test-file` 기록이 없어 focused 집합을 복원할 수 없으므로, 이 태스크의 focused 실행은 전체 `test` 명령으로 폴백하고 execution-log에 기록한다.
- `"변경사항 수집"` → Step 5부터 재실행

---

## 금지 사항 (Iron Law 강제)

이 Phase에서 절대 호출하지 않는 에이전트:
- ❌ `coder` (deprecated) / `green-coder`·`refactor-coder` (파이프라인 미호출 — implementer로 통합. 단독 스킬·gx-ralph 전용)
- ❌ `qa-manager` (자기점검은 spec-reviewer가 phase-review에서 수행)

이 Phase에서 절대 수행하지 않는 동작:
- ❌ "구현 후 테스트 작성" — Iron Law 1 정면 위반
- ❌ RGR 사이클 병렬 실행 — 격리 깨짐
- ❌ "이번 한 번만" 코드 우선 작성 — 첫 예외가 규칙이 됨
- ❌ 검증 명령 생략 (verify_red/verify_implement) — Iron Law 3 위반

위반 감지 시 즉시 중단하고 RED 단계부터 재시작한다.

---

## 부록 A: gx-ralph 전용 트리오 프롬프트 (구 Step 2-G/2-F)

> 이 부록은 gx-tdd 파이프라인이 사용하지 않는다. `gx-ralph-iterate`(헤드리스 반복)가 origin: gx-tdd 루프에서 red-writer → green-coder → refactor-coder 트리오를 디스패치할 때의 프롬프트 소스로만 보존된다. 파이프라인 본문은 Step 2-I(implementer)를 사용한다.

### 구 Step 2-G: GREEN (green-coder 디스패치 — gx-ralph 전용)

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
2. **테스트 무결성 확인**: `git hash-object "{테스트 파일}"`을 재실행하여 verify_red의 `test-file-hash`와 비교하고, `git status --porcelain`(svn은 `svn status`)을 verify_red 스냅샷 파일(`${DEV_DIR}/rgr-t{N}-porcelain.txt`)과 대조하여 **다른 테스트 파일**의 변경 여부도 확인한다. (`.dev/` 경로 라인은 대조에서 제외한다 — 산출물 공유 전환으로 델타에 나타날 수 있으나 테스트 무결성과 무관하다) **이전 태스크들의 `test-file-hash`도 재검증**한다 (이미 dirty/untracked 상태라 porcelain 델타에 잡히지 않는 이전 테스트 파일의 내용 수정 감지).
   - 무단 수정 감지 (해시 불일치 또는 타 테스트 파일 변경) → 해당 테스트를 RED 산출물(red 결과의 테스트 코드)로 원복하고 **green-coder 재호출** 1회 ("테스트 수정 금지" 재강조). **재차 위반 시** 사이클을 중단하고 사용자에게 보고한다.
3. 대상 테스트 통과 확인.
4. 전체 테스트 실행 → 다른 테스트 회귀 없음 확인. **전체 테스트 수를 state.md 해당 태스크의 `test-count: N` 필드로 기록**한다 (verify_refactor의 테스트 삭제 감지 기준선 — --resume 시에도 복원된다).
5. **과잉 구현 감지**:
   - 추가된 메서드/필드 중 테스트에서 안 쓰는 것 → 사용자에게 보고: "과잉 구현 감지 ({N줄}). YAGNI 권고로 다음 RED 단계로 미루는 것이 좋습니다. 정리할까요?"
6. ✅ 통과 + 회귀 없음 + 무결성 유지 → REFACTOR로 진행.
7. ❌ 실패 → green-coder 재호출 (에러 메시지 전달, 최대 2회).

`current-step`을 `"RGR T{N}: GREEN"`으로 갱신.

---

### 구 Step 2-F: REFACTOR (refactor-coder 디스패치 — gx-ralph 전용)

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
