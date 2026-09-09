# phase-implement: RED-GREEN-REFACTOR 사이클 (TDD 강제)

## Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

이 Phase는 **RED 격리 디스패치 → IMPLEMENT 세션 직접 수행**으로 동작한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님). 태스크의 AC 시나리오 전부를 테스트 집합으로 한 번에 쓴다
- **IMPLEMENT** → 통과 최소 코드(GREEN) + 안전한 정리(REFACTOR — 동작 변경 금지). 기본 경로에서는 **오케스트레이터가 직접 수행**한다 (Step 2-I "세션 IMPLEMENT 절차"). `--isolated`면 implementer를 디스패치한다 — 입력은 RED report+시그니처로 한정하되 기존 코드 Read는 허용, 테스트 실행은 focused 집합만. 어느 경로든 verify_implement의 해시·focused 직접 실행 검증은 같다

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.

> green-coder·refactor-coder는 이 파이프라인에서 호출하지 않는다 — 단독 스킬(gx-green·gx-refactor) 전용. gx-ralph 루프는 항상 red-writer→implementer 2석(격리 경로)을 쓴다.

---

## 핵심 모드 분기 (core)

오케스트레이터가 핵심 모드이면:
- Step 0에서 설계서(`design.md`)와 PRD(`prd.md`) 로드를 건너뛰고, `${DEV_DIR}/ac.md`를 Read하여 **G-W-T 형식 AC**를 추출한다 (phase-requirements core 분기가 저장).
- **Step 0.5(기준선 게이트)는 실행한다** (RGR이 강제되므로 기준 GREEN 확인과 warnings-baseline 기록이 필요하다).
- Step 1(태스크 분해)과 Step 1.2(승인 게이트)도 건너뛴다.
- **RGR 사이클은 유지**한다 (핵심 모드여도 TDD는 강제. Iron Law 1).
  - red-writer 입력: ac.md의 AC (G-W-T) + 기존 테스트 스타일 (설계서 testability 섹션 없음).
  - IMPLEMENT 입력(세션 또는 implementer): RED report 경로 + 기존 코드 인터페이스 (설계서 없음) + focused 테스트 명령.
- Step H1~H4 (긴급 보안 감사)는 사이클 완료 후 동일하게 실행한다.

핵심 모드가 아닌 경우 아래 전체 모드 플로우를 따른다.

---

## Step 0: 문서 로드

- `${PROJECT_ROOT}/${DEV_DIR}/design.md`를 Read하여 설계서를 로드한다. **testability 섹션**(phase-design에서 test-architect가 추가)을 확인한다.
- `${PROJECT_ROOT}/${DEV_DIR}/prd.md`를 Read하여 PRD를 로드한다. **수용 기준(AC) Given-When-Then 시나리오**를 추출한다.
- testability 섹션이 누락된 설계서면 사용자에게 경고: "testability 평가가 누락된 설계서입니다. phase-design을 재실행해야 RGR 격리 컨텍스트를 구성할 수 있습니다."
- `ANTI_PATTERNS_PATH`를 확정한다: 이 phase 파일이 위치한 gx-tdd 스킬 디렉토리 기준 `references/testing-anti-patterns.md`의 절대 경로 (플러그인 설치 환경에서는 플러그인 베이스 경로 하위 — 소비 프로젝트 루트가 아니다). red-writer(phase-implement)·reviewer(phase-review) 프롬프트에 이 경로를 전달한다.
- `FRONTEND_TESTING_PATH`를 같은 규칙으로 확정한다 (`references/frontend-testing.md`). **UI 컴포넌트를 다루는 태스크에서만** red-writer(phase-implement)·reviewer(phase-review) 프롬프트에 추가로 전달한다 — 백엔드 전용 태스크에 넣으면 프롬프트만 불어난다.
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

**전환 절차**: `Skill(skill: "oh-my-gx:gx-ralph")`를 호출한다. 이 시점의 state.md에 `pipeline: gx-tdd` 이력이 있으므로 gx-ralph가 `origin: gx-tdd`로 기록하고, 반복 세션이 red-writer→implementer 2석으로 구현한다. **이 파이프라인은 여기서 종료한다** — Step 1 이후를 실행하지 않고, state.md execution-log에 `implement: ralph 전환` 1줄을 기록한다. 루프 종료 후 복귀 경로는 gx-ralph가 안내한다. `MODEL_PROFILE`이 `eco`이면 전환 시 1줄 안내한다: "ralph 루프는 모델 프로파일(eco)을 아직 지원하지 않습니다 — 반복은 GX_RALPH_MODEL 미지정 시 에이전트 기본 모델(표준)로 실행됩니다." Skill 호출이 실패하면 직접 우회하지 않고 사용자에게 보고한 뒤 대화형 RGR로 진행할지 확인한다.

## Step 1: 태스크 분해 (오케스트레이터 직접 수행)

설계서의 "구현 순서"와 PRD의 AC를 결합하여 **RGR 사이클 단위 태스크**로 분해한다. 각 태스크는 다음을 만족한다:

1. **태스크 = AC 1건**이 기본이다. AC 하나의 G-W-T 시나리오 전부가 그 태스크의 테스트 집합이 된다. **같은 컴포넌트를 건드리는 AC들**과 **같은 패턴의 소형 변경으로 환산되는 AC들**(동일 검증 로직의 필드별 반복, 동일 형태의 매핑 추가 등)은 하나의 태스크로 **묶는 것이 기본**이다. 한 AC가 컴포넌트 둘 이상에 걸칠 때만 컴포넌트 단위로 나눈다 — 이때만 AC보다 작은 태스크가 생긴다.
2. **2~15분**은 태스크의 크기가 아니라 태스크 안에서 **테스트 하나를 통과시키는 한 걸음**의 크기다 (Step 2-I 내부 루프). 태스크는 리뷰어가 이웃 태스크를 승인하면서 이 태스크만 거절할 수 있을 만큼 독립적이면 충분하다.
3. 다른 태스크와 **파일이 겹치지 않는다** (사이클 간 간섭 방지 — 태스크는 순차 실행된다). 겹치면 앞 태스크의 `test-file-hash`·porcelain 스냅샷 기준선이 뒤 태스크의 변경으로 오염되어 무결성 검증이 오탐한다.

### 1.1 태스크 표 생성

사용자에게 다음 형식으로 제시한다:

```
## RGR 태스크 분해

| # | AC 매핑 | 컴포넌트 | RED (테스트 작성) | IMPLEMENT (구현+정리) |
|---|---------|---------|-------------------|------------------------|
| 1 | AC-1 | PaymentLimit | PaymentLimitTest (케이스 3건: 초과 거부·경계값·기본 한도) | PaymentLimit.kt: data class + validate() → 매직 넘버 상수화 |
| 2 | AC-2, AC-3 (묶음) | PaymentService | PaymentServiceTest (케이스 4건) | PaymentService.processPayment() 한도 검증 추가 → 중복 검증 로직 추출 |
| 3 | AC-4 | PaymentController | PaymentControllerE2ETest (케이스 2건) | PaymentController.updateLimit() 엔드포인트 |

### 의존성 (실행 순서)
- T1 (PaymentLimit) → T2 (PaymentService가 PaymentLimit 참조) → T3 (Controller가 Service 참조)
- T1, T2, T3은 **순차 실행** (의존성 체인).
```

### 1.15 태스크 수 가드

태스크가 **8개를 넘으면** 승인 게이트 전에 아래를 먼저 묻는다. 태스크마다 red-writer 콜드 스타트와 verify 6단계가 붙으므로 30개짜리 분해는 한 세션에서 끝나지 않는다 — 분해가 잘못됐거나 실행 단위가 잘못된 것이다.

```
AskUserQuestion(
  questions: [{
    question: "태스크가 {N}개로 분해됐습니다. 8개를 넘으면 한 세션에서 완주하기 어렵습니다. 어떻게 할까요?",
    header: "태스크 수",
    options: [
      { label: "AC 묶어서 재분해 (추천)", description: "같은 컴포넌트·같은 패턴의 AC를 한 태스크로 묶어 8개 이하로 줄입니다. 태스크당 테스트 케이스가 늘어날 뿐 RGR 강도는 같습니다" },
      { label: "작업 계획으로 분할", description: "이번 실행은 앞 8개까지만 진행하고 나머지 AC는 `.dev/plan.md`의 후속 작업(W행)으로 등록합니다. 다음 실행에서 `W0N 시작해줘`로 이어집니다" },
      { label: "무인 루프로 전환", description: "이 파이프라인을 중단하고 `--ralph`로 재실행해 외부 러너가 AC를 1건씩 반복합니다 (svn 미지원)" },
      { label: "그대로 진행", description: "{N}개 전부 이 세션에서 진행합니다. 컨텍스트 압축이 일어날 수 있으며 `--resume`으로 이어갈 수 있습니다" }
    ],
    multiSelect: false
  }]
)
```

- **AC 묶어서 재분해** → 조건 1의 묶기 규칙을 적용해 재분해하고 1.1 표를 다시 제시한다. 여전히 8개를 넘으면 이 가드를 한 번 더 거친다 (최대 2회).
- **작업 계획으로 분할** → `.dev/plan.md`가 없으면 이 선택지를 **제외**하고 제시한다. 있으면 앞 8개 태스크에 대응하는 AC로 범위를 줄이고, 나머지 AC를 `.dev/plan.md`에 `대기` 상태의 새 W행으로 추가한다 (도메인·브랜치명은 현재 실행과 같은 규칙, 선행은 현재 `work-id`). `.dev/plan.md`만 스테이징해 `docs: [plan] 후속 작업 등록` 메시지로 커밋한다. trust-ledger `### 위험 수용`에 `- [범위 분할] AC-N…: 후속 W행으로 이관 (implement/Step 1.15)`를 기록한다.
- **무인 루프로 전환** → `status: cancelled`로 종료하고 `/gx-tdd --ralph {원 요청}` 재실행을 안내한다. svn이면 이 선택지를 제외한다.
- **그대로 진행** → 1.2로 진행한다. execution-log에 `"태스크 수 가드 통과(사용자 선택): {N}개"`를 남긴다.

핵심 모드는 Step 1을 건너뛰므로 이 가드도 타지 않는다 (AC 3~5개 = 태스크 3~5개).

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
    if "--isolated" in state.flags:
        impl_result = dispatch_implementer(task, red_report_path)   # 격리 경로. report: reports/t{N}-impl.md
    else:
        impl_result = session_implement(task, red_report_path)      # 기본 경로. 세션이 직접 구현하고 같은 report를 Write
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증 (경로 무관 동일)

    # 2-V: 태스크 리뷰 (조건부 — 프로덕션 파일 2개 이상 또는 fix 라운드 있음)
    if task_review_required(task):
        review_task(task)                    # reviewer 태스크 범위 모드 (sonnet). report: reports/t{N}-review.md
    record_to_state(task, results)
```

### Step 2-R: RED (red-writer 디스패치)

```
Task(subagent_type="oh-my-gx:red-writer"):
  description: "RED: Write failing tests for {AC-N}"
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
    1. 이 태스크에 매핑된 AC의 시나리오마다 테스트 케이스 1건씩 작성 ([작성 범위] 참조). 각 케이스는 테스트 품질 3기준 준수:
       - 하나의 동작만 검증 (이름에 '그리고'가 필요하면 분리)
       - 이름이 검증하는 동작을 설명
       - 실제 코드 우선, 모의는 불가피할 때만
    2. 테스트 명령 실행으로 실패 확인 (에러 메시지 캡처)
    3. 실패 사유 분류 (NoSuchMethod / assertion / etc)

    [작성 범위 — 테스트 집합]
    이 태스크에 매핑된 AC의 G-W-T 시나리오 **전부**를 각각 테스트 케이스로 작성합니다 (시나리오 1건 = 케이스 1건). 컴포넌트당 테스트 파일 하나에 모읍니다. 케이스마다 실패 확인 명령을 실행해 전부 실패하는지 확인하고, 통과하는 케이스가 있으면 기존 동작을 검증하는 잘못된 케이스이므로 다시 씁니다.

    [report 파일]
    {reports/t{N}-red.md} — 테스트 코드 전문·케이스 목록(케이스 수 명시)·실패 확인 명령·케이스별 실패 메시지·참조한 파일 전체 목록을 이 파일에 Write하십시오

    [반환 형식 — 15줄 이내. 전문은 report 파일에]
    - Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
    - 테스트 파일: {경로}
    - 실패 확인: {1줄 — 명령 + 케이스 수 + 실패 유형 (NoSuchMethod / assertion / etc)}
    - 우려사항: {1~2줄, 없으면 "없음"}
    - report: {reports/t{N}-red.md}
```

**verify_red**: 오케스트레이터가 직접 검증.
1. report 파일(`reports/t{N}-red.md`)에서 테스트 파일 경로·케이스 목록·실패 확인 명령을 읽는다.
2. **실패 확인 (집합 전체)**: report의 실패 확인 명령을 직접 실행해 신규 케이스가 **모두** 실패하는지 본다 (실패 건수 = report의 케이스 수). 통과하는 케이스가 있으면 그 케이스만 지목해 red-writer를 재호출한다 (전체 재작성 아님). 에러(컴파일 실패·러너 오류)로 끝난 것은 실패가 아니다 — 원인을 report와 대조해 red-writer 재호출.
3. 실패 사유가 "이미 구현이 있어서 통과"이면 → AC를 더 좁히도록 사용자에게 안내 후 중단.
4. **격리 오염 검증**: report 파일의 "참조한 파일" 목록에 프로덕션 소스가 포함되어 있으면 → 해당 테스트 폐기 후 red-writer 재호출 (구현에 적응한 오염된 RED일 수 있음).
5. **`NEEDS_CONTEXT` 처리**: red-writer가 `NEEDS_CONTEXT`(설계서 인터페이스 불충분 등)를 반환하면 — 전체 모드: phase-design 재실행(테스트 전략 보강) 여부를 사용자에게 확인. 핵심 모드: AskUserQuestion(자유입력)으로 대상 인터페이스 정보를 받아 red-writer에 보강 전달 후 재호출.
6. **테스트 파일 해시 기록**: `git hash-object "{테스트 파일}"` 결과를 state.md 해당 태스크의 `test-file-hash`로 기록한다 (GREEN의 테스트 무결성 기준선. untracked 파일에도 동작. 경로는 따옴표로 감싼다). 동시에 `git -c core.quotePath=false status --porcelain > ${DEV_DIR}/rgr-t{N}-porcelain.txt`로 스냅샷을 **파일로 저장**한다 (GREEN에서 **다른 테스트 파일** 변경을 잡기 위한 기준선. **svn 프로젝트는 `svn status`를 사용**. 파일이 DEV_DIR에 남으므로 --resume 재개 시에도 기준선이 유지된다). 테스트 파일 경로를 state.md 해당 태스크의 `test-file`로 기록한다 (focused 집합 조립에 사용).
7. **report 저장 확인**: `reports/t{N}-red.md`가 존재하고 테스트 코드·실패 메시지를 담고 있는지 확인한다. 다음 단계(2-I) 인계는 이 파일 경로로만 한다.
8. ✅ 실패 정상 → IMPLEMENT(2-I)로 진행.

`current-step`을 `"RGR T{N}: RED"`로 갱신.

---

### Step 2-I: IMPLEMENT (세션 직접 수행 — GREEN+REFACTOR 통합. `--isolated`면 implementer 디스패치)

기본 경로에서는 **오케스트레이터가 이 단계를 직접 수행**한다 — 태스크당 콜드 스타트를 red-writer 1회로 줄이기 위해서다. verify_implement의 검증은 파일 상태 대조(해시·porcelain·focused 직접 실행)라 수행 주체와 무관하게 같은 강도로 동작한다. state.md `flags`에 `--isolated`가 있으면 아래 "격리 경로"의 implementer 디스패치를 대신 쓴다. gx-ralph 루프는 항상 격리 경로다.

**세션 IMPLEMENT 절차** (`agents/implementer.md`의 절대 규칙·REFACTOR 범위·report 형식과 같은 계약이다 — 한쪽을 고치면 함께 갱신. `references/maintenance-notes.md` 참조):

[절대 규칙]
1. 테스트 파일을 수정하지 않는다. 테스트가 실패하면 코드를 고친다. 테스트 자체 결함이 의심되면 고치지 말고 report `## 우려사항`에 "테스트 결함 의심"으로 적고 verify_implement 2번을 따른다.
2. GREEN: 실패 테스트를 통과시키는 최소 코드만 작성한다 (YAGNI — 추가 기능/에러 핸들링/검증/로깅 금지).
3. REFACTOR: 동작 변경 금지. 매 정리 후 focused 테스트로 GREEN 유지 확인, 깨지면 즉시 롤백.
4. 테스트 실행은 focused 명령만 사용한다. 전체 스위트는 사이클 경계(Step 3.5 / phase-review Step 0)에서만 실행한다.
5. report 작성 전 self-review(완전성/품질/규율/테스트 4관점)를 수행하고 발견 즉시 수정한다. 이 절차를 다른 에이전트에 재위임하지 않는다 (fix 라운드 4~5의 격상 디스패치만 예외).

[수행 불가능한 정리]
- 동작 변경
- 새 기능 추가
- 에러 핸들링 추가
- 성능 최적화
- 인터페이스 시그니처 변경

[절차 — 내부 RGR 루프]
1. `reports/t{N}-red.md`를 Read해 이 태스크의 실패 테스트 집합(파일·케이스·실패 메시지)을 파악한다. 설계서 인터페이스(대상 시그니처)를 확인한다. 구현에 필요한 기존 코드는 Read한다 (세션은 red-writer와 달리 코드 차단 대상이 아니다).
2. focused 명령(조립 규칙은 아래 **focused 테스트 명령 조립** 참조)을 실행해 현재 실패 케이스 목록을 얻는다.
3. 실패 케이스 **하나**를 고른다 → 그 케이스만 통과시키는 최소 코드를 작성한다 → focused를 재실행해 그 케이스가 통과하고 이미 통과한 케이스가 유지되는지 본다. 실패 케이스가 남아 있으면 3을 반복한다. 한 걸음이 15분을 넘기면 케이스를 더 잘게 볼 수 있는지 먼저 의심한다.
4. 전부 GREEN이면 REFACTOR: 중복 제거·네이밍·구조 정리. 정리 한 단위마다 focused 재실행. 깨지면 그 단위를 롤백한다. 정리할 것이 없으면 "정리 없음"으로 기록한다.
5. self-review 후 `reports/t{N}-impl.md`를 Write한다. 형식은 `agents/implementer.md`의 report 형식과 같다 — `## 구현 내용` / `## GREEN 증거`(focused 명령 + "N pass / 0 fail" 출력 요약) / `## REFACTOR 내역` / `## self-review 결과` / `## 우려사항`.
6. verify_implement로 진행한다. 세션 경로에는 NEEDS_CONTEXT·BLOCKED 상태 반환이 없다 — 필요한 파일은 직접 읽고, 막히면 fix loop와 Step 3 정체 감지가 처리한다. 우려가 있으면 report `## 우려사항`에 적고 verify_implement 1번의 DONE_WITH_CONCERNS 처리를 따른다.

**격리 경로 (`--isolated`)** — 아래 implementer 디스패치를 그대로 쓴다. 상태 반환(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)은 이 경로에서만 발생한다.

```
Task(subagent_type="oh-my-gx:implementer"):
  description: "IMPLEMENT: Pass & clean {component}"
  prompt: |
    당신은 GREEN+REFACTOR 통합 구현 전담자입니다.

    [절대 규칙]
    1. 테스트 파일을 수정하지 않습니다. 테스트가 실패하면 코드를 고치고, 테스트를 고치지 않습니다. 테스트 자체 결함이 의심되면 수정하지 말고 "테스트 결함 의심"으로 보고합니다.
    2. GREEN: 실패 테스트를 통과시키는 최소 코드만 작성합니다 (YAGNI — 추가 기능/에러 핸들링/검증/로깅 금지).
    3. REFACTOR: 동작 변경 금지. 매 정리 후 focused 테스트로 GREEN 유지 확인, 깨지면 즉시 롤백.
    4. 테스트 실행은 아래 focused 명령만 사용합니다. 전체 스위트를 임의로 실행하지 않습니다 (전달된 명령이 focusedTest 미등록 폴백으로 전체 test 명령이면 그 명령이 곧 focused 집합입니다).
    5. 보고 전 self-review(완전성/품질/규율/테스트 4관점)를 수행하고 발견 즉시 수정합니다.

    [수행 불가능한 정리]
    - 동작 변경
    - 새 기능 추가
    - 에러 핸들링 추가
    - 성능 최적화
    - 인터페이스 시그니처 변경

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
- `{pattern}` 플레이스홀더: 각 테스트 파일명(확장자 제외)에서 유도한 클래스 글롭 `*.{파일명}`으로 치환하고, 복수 파일이면 플레이스홀더를 포함한 인자를 반복한다 (예: `./gradlew test --tests '*.PaymentLimitTest' --tests '*.PaymentServiceTest'`).
- `focusedTest` 필드가 없으면 해당 타입의 전체 `test` 명령을 사용하고 execution-log에 `"focused 미지원 — 전체 실행 폴백"`을 기록한다.

**명령 오류 가드**: focused 실행이 테스트 실패가 아니라 **명령 자체 오류**(러너 미설치·옵션 오류 등 — 출력에 테스트 결과 요약이 없음)로 끝나면 fix loop에 넣지 않는다. execution-log에 `"focusedTest 명령 오류 — 전체 실행 폴백"`을 기록하고 이 파이프라인 실행의 남은 구간은 전체 `test` 명령으로 전환하며, 사용자에게 config의 `focusedTest` 값 확인을 안내한다.

**verify_implement**: 오케스트레이터가 직접 검증. **저비용 검사(1~3번)를 테스트 실행보다 먼저 수행한다.**
1. **Status 분기** (격리 경로에서만 상태가 반환된다. 세션 경로는 report `## 우려사항`에 "없음" 외의 내용이 있으면 DONE_WITH_CONCERNS로 취급한다): `NEEDS_CONTEXT` → 요청된 정보를 보강해 재디스패치 (라운드 미소모, 태스크당 최대 2회 — 초과 시 BLOCKED로 승격해 처리한다). `BLOCKED` → 컨텍스트 보강 / 모델 격상 / 태스크 분할 / 설계 재확인 중 판정 후 처리. `DONE_WITH_CONCERNS` → report의 우려를 Read하고 정합성 문제면 fix 라운드로, 관찰이면 기록 후 진행.
2. **테스트 결함 의심 확인**: 보고됐으면 사유 확인 후 **red-writer 재호출**로 테스트를 재작성한다 (구현 주체가 테스트를 고치지 않는다).
3. **테스트 무결성 확인**: `git hash-object "{테스트 파일}"`을 재실행하여 verify_red의 `test-file-hash`와 비교하고, `git -c core.quotePath=false status --porcelain`(svn은 `svn status`)을 verify_red 스냅샷 파일(`${DEV_DIR}/rgr-t{N}-porcelain.txt`)과 대조한다 — **대조는 테스트 파일 라인만 필터**하여 수행한다(판별 글롭은 Step 0.5 4항의 테스트 파일 글롭 `**/*test*`·`**/*Test*`·`**/*spec*` 재사용. `.dev/` 경로 라인은 제외. svn은 `svn status` 출력의 경로 컬럼 기준으로 같은 필터를 적용). **이전 태스크들의 `test-file-hash`도 재검증**한다. 무단 수정 감지 → 해당 테스트를 RED 산출물로 원복하고 구현 주체가 1회 재수행한다 — 세션 경로는 세션이 원복 후 재구현, 격리 경로는 implementer 재호출 ("테스트 수정 금지" 재강조 — fix 라운드와 별도 카운트). 재차 위반 시 사이클 중단·사용자 보고.
4. **focused 집합 직접 실행**: 위 focused 명령을 오케스트레이터가 1회 직접 실행한다 — 통과 목격(증거 주체는 오케스트레이터, verify_red와 대칭) + 결과의 테스트 수를 state.md 해당 태스크의 `test-count`로 기록한다(직전 태스크의 같은 방식 값과 비교해 감소 시 사유 확인 — 무단 삭제면 롤백 요청). **전체 스위트는 실행하지 않는다** — 전체 회귀는 사이클 경계(전체 모드: phase-review Step 0 Mechanical Gate / 핵심 모드·`--phase implement` 단독: Step 3.5)가 담당한다.
5. **과잉 구현 판정**: 추가된 public 메서드/필드 중 focused 테스트 집합이 참조하지 않는 것을 찾는다. 있으면 **묻지 않고 판정한다** — "판정 기록 (Rulings)" 절의 기본값대로 설계서 인터페이스가 명시한 멤버는 "설계 예약"으로 유지하고, 그 외는 제거한 뒤 focused를 재실행한다 (제거로 깨지면 복원하고 `## 우려사항`에 기록). 제거·유지 목록을 `reports/t{N}-impl.md`에 `## 과잉 구현 정리` 절로 append하고, decisions.md에 `Ruling: T{N} 과잉 구현 정리` 블록을 append한다. 판정할 것이 없으면 아무것도 기록하지 않는다.
6. **public 인터페이스 시그니처 변경 없음 확인**: diff에서 공개 메서드·함수·타입 시그니처 라인의 변경을 대조한다 (REFACTOR 금지 목록 위반 — 발견 시 롤백한다. 격리 경로는 implementer에 롤백 요청).
7. ✅ 통과 + 무결성 유지 → **Step 2-V 태스크 리뷰 판정**으로 진행한다 (발동 조건 미충족이면 `review: skipped` 기록 후 태스크 완료).
8. ❌ 실패 → **fix loop 진입** (아래).

**fix loop (실패 시 — 태스크당 최대 5라운드)**:

| 라운드 | 방식 | 모델 |
|--------|------|------|
| 1~3 | **세션이 직접 수정** (기본 경로). 격리 경로는 **같은 implementer를 재개** — 하네스가 서브에이전트 재개(후속 메시지)를 지원하면 그 방식으로 미해결 항목을 전달, 지원하지 않으면 report 파일 경로를 실은 fresh 디스패치 (report가 영속 기억) | 세션 / sonnet |
| 4~5 | **두 경로 모두 fresh implementer 디스패치 + 모델 격상** (`model: "opus"` 오버라이드) — 세션이 3라운드 실패한 뒤에는 fresh eyes와 역량 격상이 함께 필요하다. 프롬프트에 "이전 구현자가 {r-1}회 시도했다. report 파일에서 시도 내역을 읽어라"를 포함 | opus |

- 매 라운드: 구현 주체(세션 또는 implementer)가 수정 → focused 재실행 → fix report를 같은 report 파일에 append → 상태 반환(격리 경로만) → 오케스트레이터가 verify_implement 재수행. Step 2-V 태스크 리뷰의 findings 수정도 **이 라운드 카운터와 상한 5를 공유**한다 — 리뷰가 연 라운드는 verify_implement 재수행 뒤 재리뷰(2-V)로 닫힌다. `current-step`을 `"RGR T{N}: FIX R{r}"`로, state.md 해당 태스크에 `fix-round: {r}/5`를 기록한다.
- 모델 격상은 "실패의 대응"으로 **모델 프로파일과 독립**이다 — eco 세션에서도 라운드 4~5는 opus로 격상한다.
- **라운드 5 소진 시**: 사이클 중단 + AskUserQuestion — "수동 수정 후 계속" / "태스크 스킵 (위험 수용 — trust-ledger 기록)" / "중단".

`current-step`을 `"RGR T{N}: IMPLEMENT"`로 갱신.

### Step 2-V: 태스크 리뷰 (조건부 — reviewer 태스크 범위 모드)

verify_implement 7번 직후, 태스크를 완료 처리하기 **전에** 판정한다. 세션 IMPLEMENT는 검사자와 피검사자가 같으므로, 자기 검증 편향이 커지는 태스크에만 fresh eyes를 한 번 붙인다. phase-review는 **전체 브랜치 리뷰**로 그대로 남는다.

**발동 조건** (하나라도 해당하면 리뷰, 아니면 state.md 태스크에 `review: skipped` 기록 후 태스크 완료):
- (a) 이 태스크가 바꾼 **프로덕션 파일이 2개 이상**이다. 변경 파일 목록은 verify_red 스냅샷과 현재 porcelain의 차이로 구한다 (`.dev/` 제외. 스냅샷에 없거나 상태가 달라진 줄의 경로. `reports/t{N}-impl.md` `## 구현 내용`의 변경 파일과 합집합). 프로덕션 파일은 그중 테스트 파일 글롭(Step 0.5 4항의 `**/*test*`·`**/*Test*`·`**/*spec*`)에 해당하지 않는 파일이다.
  ```bash
  git -c core.quotePath=false status --porcelain -- . ':(exclude).dev' | sort > ${DEV_DIR}/rgr-t{N}-porcelain.now.txt
  comm -13 <(grep -v ' \.dev/' ${DEV_DIR}/rgr-t{N}-porcelain.txt | sort) ${DEV_DIR}/rgr-t{N}-porcelain.now.txt | cut -c4-
  ```
  (svn은 `svn status`로 같은 대조를 한다. 경로 열은 8열부터다.) **verify_red 스냅샷 파일이 없으면**(구 세대 재개) (a)를 판정하지 않고 (b)만 본다 — 왼쪽이 비면 워킹트리 전체가 이 태스크의 변경으로 잡힌다.
- (b) 이 태스크의 state.md에 `fix-round`가 기록되어 있다 (fix loop를 1회 이상 돌았다).

**태스크 diff 수집**: 실제 인덱스와 porcelain 스냅샷을 건드리지 않도록 **임시 인덱스**를 쓴다 (훅 `compute_fingerprint`와 같은 관용구 — mktemp가 만든 빈 파일은 git이 거부하므로 경로만 쓴다). 대상은 (a)의 변경 파일 전부 + 이 태스크의 `test-file`이다.
```bash
# 한 번의 Bash 호출로 실행한다 — 호출이 갈리면 $$가 달라져 빈 인덱스로 diff가 나온다
IDX="${TMPDIR:-/tmp}/.gxtr.$$"; rm -f "$IDX"
GIT_INDEX_FILE="$IDX" git add -A -- {변경 파일 목록} "{test-file}" \
  && GIT_INDEX_FILE="$IDX" git diff --cached HEAD -- {변경 파일 목록} "{test-file}" > ${DEV_DIR}/reports/t{N}-diff.txt \
  || echo "TASK_DIFF_FAILED"
rm -f "$IDX"
```

`TASK_DIFF_FAILED`가 출력되거나 diff 파일이 비어 있거나 `deleted file mode`만 있고 추가 hunk가 없으면 **Step 2-V를 중단하고 사용자에게 보고**한다 — add가 실패해도 이어지는 diff는 종료 코드 0으로 HEAD 파일을 전부 삭제로 출력하므로, 오류 신호 없이 reviewer에게 가짜 삭제 diff가 간다. 실패 원인은 대개 경로 인용이다 (그래서 porcelain 수집에 `-c core.quotePath=false`를 쓴다).

svn: 버전 관리 중인 파일은 `svn diff -- {파일들}`, 미등록 신규 파일은 `diff -u /dev/null {파일}`을 같은 파일에 이어 붙인다. 500줄 초과 시 Diff 수집 규칙의 `--stat` 강등을 그대로 적용한다.

**디스패치** (`model: "sonnet"` — 프로파일·격상과 무관하게 고정. 태스크 diff는 작고 재리뷰는 scoped다):

```
Task(subagent_type="oh-my-gx:reviewer", model: "sonnet"):
  description: "Task review T{N} (scoped)"
  prompt: |
    당신은 통합 리뷰 전담자입니다. **태스크 범위 모드**로 동작합니다 — 전달된 AC와 태스크 diff만 봅니다. 전체 브랜치 리뷰는 phase-review가 별도로 수행하므로 범위를 넓히지 않습니다.

    [Iron Law]
    NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED — Part 1 verdict를 먼저 확정한 뒤 Part 2를 냅니다.

    [발견 단계 커버리지]
    발견 단계의 목표는 커버리지다. 확신이 서지 않거나 심각도가 낮다고 판단한 항목도 빠짐없이 보고합니다. 확신이 낮은 항목은 Minor로 분류하되 보고에서 빼지 않습니다.

    [구현자 보고 불신뢰]
    RED/IMPL report의 산문 정당화는 미검증 주장입니다 — diff로 검증하고, 테스트를 재실행하지 않습니다 (증거는 verify_implement가 확보).

    [태스크 AC (Given-When-Then)]
    {이 태스크에 매핑된 AC 시나리오 — Part 1은 이것만 평가}

    [설계서 인터페이스]
    {대상 컴포넌트의 시그니처 — 핵심 모드는 "없음 (핵심 모드)"}

    [태스크 diff]
    - {reports/t{N}-diff.txt} — Read하여 확인

    [구현 report]
    - {reports/t{N}-red.md}, {reports/t{N}-impl.md}

    [코드 맵]
    {코드 맵}

    [프로젝트 컨벤션]
    {CLAUDE.md 컨벤션 또는 기존 코드 스타일}

    [테스트 품질 기준 파일]
    {ANTI_PATTERNS_PATH} — 테스트 코드 품질 판정 시 Read
    {FRONTEND_TESTING_PATH} — UI 태스크에서만 전달

    [재리뷰 — fix 라운드 후에만 포함]
    이전 findings: {항목 목록}. 각 항목을 ADDRESSED / NOT ADDRESSED로 판정하고(파일:라인 근거. "시도함"은 NOT ADDRESSED), 수정 diff {reports/t{N}-diff-r{r}.txt}의 새 결함만 추가로 보고합니다. 범위 밖 관찰은 Minor로 둡니다.

    [출력 형식]
    agents/reviewer.md의 출력 형식 — Part 1 매트릭스(전달된 AC만)·판정, Part 2 분류·판정, 맨 마지막에 spec_verdict → quality_verdict 두 YAML 블록 순서 고정. 재리뷰면 Part 2 앞에 `## 재리뷰 판정` 표(항목 | ADDRESSED/NOT ADDRESSED | 근거)를 둡니다.
```

**결과 처리** (오케스트레이터 직접):
1. reviewer 출력 전문을 `${DEV_DIR}/reports/t{N}-review.md`에 Write한다 (reviewer는 Write 도구가 없다). 재리뷰는 `## 재리뷰 R{r}` 제목으로 같은 파일에 append한다. state.md 태스크에 `review: in_progress`·`review-report: reports/t{N}-review.md`를 기록한다.
2. `spec_verdict`·`quality_verdict` 블록을 phase-review Step 4.0과 같은 규칙으로 파싱한다 — 블록 우선, 산문 판정과 상충하면 FAIL로 간주하고 reviewer를 1회 재호출, 재호출도 상충이면 사용자에게 보고. `[검증 필요]` 항목은 해당 focused 테스트를 1회 직접 실행해 반영한다.
3. 라우팅 (사용자에게 묻지 않는다 — Step 2-I fix loop와 같은 자동 경로):
   - `spec_verdict: FAIL`, Critical, Important `[동작결함]`(무표기 포함) → **RED 재호출 후 fix loop 진입** (Iron Law 1 — 동작 결함은 그것을 재현하는 실패 테스트가 먼저 있어야 고친다. 기존 fix loop는 verify_red 기준선의 테스트를 통과시키는 루프라 그 안에서는 테스트를 추가할 수 없으므로 RED를 먼저 연다):
     1. **RED 재호출**: red-writer를 Step 2-R 프롬프트로 재디스패치한다. `[AC (Given-When-Then)]`에는 미충족 AC(spec FAIL) 또는 finding을 재현 조건으로 옮긴 시나리오(Critical·`[동작결함]`: Given 현재 상태 / When 트리거 / Then 기대 동작)를 넣고, `[작성 범위 — 테스트 집합]` 뒤에 "이 태스크의 기존 테스트 파일에 케이스를 **추가**합니다 (기존 케이스 수정·삭제 금지)"를 덧붙인다. verify_red 1~7을 그대로 재적용한다 (3번의 "이미 구현이 있어 통과"는 재현 RED에서는 finding이 실제 결함이 아니라는 뜻이다 — 사용자에게 묻지 않고 그 finding을 '재현 불가' 근거와 함께 재리뷰에 넘기며 라운드를 1 소모한다) — 새 케이스만 실패해야 하고 기존 케이스는 통과를 유지하며, `test-file-hash`·`rgr-t{N}-porcelain.txt`·`test-count` 기준선을 **갱신**한다. report는 `reports/t{N}-red.md`에 `## 재현 RED R{r}` 절로 append한다.
     2. **fix loop**: 구현 주체(세션. `--isolated`면 같은 implementer 재개. **라운드 4~5는 Step 2-I fix loop 표대로 두 경로 모두 fresh implementer + `model: "opus"` 격상**)가 새 실패 케이스를 통과시키며 findings를 수정 → focused 재실행 → fix report를 `reports/t{N}-impl.md`에 append → verify_implement 재수행(갱신된 기준선 기준) → 수정 diff를 위 임시 인덱스 관용구로 `reports/t{N}-diff-r{r}.txt`에 수집 → **재리뷰** 디스패치(위 프롬프트의 `[재리뷰]` 절 포함).
     3. NOT ADDRESSED 또는 새 Critical/Important가 남으면 다음 라운드 — 새 동작 결함이면 1번(RED)부터, `[동작불변]`만 남았으면 정리만. `current-step`은 `"RGR T{N}: REVIEW R{r}"`, 태스크에 `fix-round: {r}/5`.
   - Important `[동작불변]` → 세션 정리 (세션 IMPLEMENT 절차의 REFACTOR 규칙·금지 목록. `--isolated`면 implementer 정리 모드) → focused 재실행 → 재리뷰. `[동작불변]`만 있어도 **라운드를 1 올린다** (`fix-round: {r}/5` — 정리·재리뷰 왕복도 상한 5를 공유한다). 동작 결함과 함께 나왔으면 같은 라운드의 재리뷰에 포함한다.
   - Minor → **유예**. 수정하지 않고 태스크에 `deferred-minors: {건수}`를 기록한다. phase-review Task A가 유예 목록을 받아 머지 전 수정 필요 여부를 판정한다.
   - spec PASS·Critical 0·Important 0 → `review: completed` 기록, 태스크 완료.
   - 라운드 5 소진 → Step 2-I의 소진 처리(AskUserQuestion: 수동 수정 후 계속 / 태스크 스킵 / 중단)를 그대로 따른다. 태스크 스킵 시 미해결 findings를 trust-ledger `### 위험 수용`에 `- [태스크 리뷰 미해결] T{N}: {findings 요약} (implement/Step 2-V)`로 기록한다.
4. execution-log에 `agent: reviewer (T{N}, task-scoped)`와 결과 요약(SPEC 판정·Critical/Important/Minor 건수·처리)을 남긴다.

`current-step`을 `"RGR T{N}: REVIEW"`로 갱신.

---

## Step 3: 정체 감지 + 에스컬레이션 (RGR 사이클)

SKILL.md 정체 감지 규칙을 RGR 사이클에 적용.

| 패턴 | RGR 적용 | 대응 |
|------|---------|------|
| SPINNING (동일 에러 2회) | 구현 주체(세션 또는 implementer)가 같은 컴파일 에러 반복 | 1차: hacker 호출 / 2차: researcher 호출 |
| OSCILLATION (A→B→A) | 구현 주체(세션 또는 implementer)가 구현 접근법 왕복 | 1차: architect 재검토 / 2차: 사용자 선택 |
| NO_DRIFT (변경 없음) | 구현 주체의 REFACTOR 결과 diff 없음 | 정리 대상 없음으로 간주, 다음 태스크로 진행 |
| DIMINISHING_RETURNS | 재호출 상한 도달 **전**, 시도마다 수정 범위가 줄지 않고 진전 없음 | 1차: simplifier (태스크 분해 단순화) / 2차: 사용자 보고 |

**fix loop 소진 시 아키텍처 격상** (superpowers 패턴):
- fix loop **라운드 4 진입(모델 격상)이 DIMINISHING_RETURNS 에스컬레이션보다 우선한다.** 라운드 5까지 소진하면 사이클을 중단하고 소진 처리(Step 2-I)를 따르되, 실패 양상이 설계 결함을 가리키면 architect에 "이 태스크의 설계가 잘못된 것 같다. 재설계 필요"를 위임한다.
- architect 결과로 설계서 갱신 후 RGR 사이클 재시작.

---

## Step 3.5: 경계 회귀 (핵심 모드·--phase implement 단독 전용)

**핵심 모드** 또는 **`--phase implement` 단독 실행**이면 전체 테스트를 1회 실행한다 — 사이클 중 focused만 돌렸으므로 기존 스위트 회귀를 여기서 확인한다 (전체 모드는 phase-review Step 0 Mechanical Gate가 이 역할을 겸하므로 건너뛴다). 실패 시 깨진 테스트 파일 경로 + 에러를 implementer에 **수리 모드**(RED report 없음 — agents/implementer.md 참조)로 전달해 수정한다. 검증 명령은 깨진 대상으로 조립한 focused 명령을 전달하고, 수리 후 전체 테스트를 오케스트레이터가 1회 재실행해 확인한다. 재시도는 1회로 제한하며(태스크 fix-round와 무관 — 태스크가 특정되지 않는 경계 수리다), 재차 실패하면 사용자에게 보고한다. `current-step`은 `"경계 회귀 수리"`로 갱신한다.

---

## Step 4: 사이클 완료 보고

모든 태스크 완료 후 사용자에게 **요약만** 보고한다 (Agent 전문 출력 금지).

```
RGR 사이클 완료: {N}개 태스크

- T1 (AC-1): RED ✅ → IMPLEMENT ✅ → REVIEW skip (파일 1개)
- T2 (AC-2, AC-3 배칭): RED ✅ → IMPLEMENT ✅ (fix 라운드 1회) → REVIEW ✅ (Important 1건 정리, Minor 2건 유예)
- T3 (AC-4): RED ✅ → IMPLEMENT ✅ (정리 대상 없음) → REVIEW ✅

focused 누적: {N pass}, 0 fail (전체 회귀는 경계에서 — 전체 모드: review Step 0 / 핵심 모드·단독: Step 3.5)
변경 파일: {N}개
판정: {N}건 (decisions.md — 제목 나열: T2 과잉 구현 정리, …)

특이사항: (있으면)
- T2 IMPLEMENT 단계에서 과잉 구현 감지 → 판정으로 제거 (decisions.md: T2 과잉 구현 정리)
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
  - "자동 수정 시도" → **RGR 사이클 재진입**: 보안 항목을 새 AC로 정의하여 red-writer(새 실패 테스트) → IMPLEMENT(세션 또는 implementer) 순서로 수정한다 (Step 2-R/2-I 재실행). implementer를 RED 없이 직접 호출하지 않는다.
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
        review: completed             # Step 2-V 결과 — skipped | in_progress | completed
        review-report: reports/t1-review.md
        deferred-minors: 2            # phase-review Task A에 유예 목록으로 전달
    - "RGR T2 (AC-2)":
        red: completed
        impl: in_progress
        fix-round: 2/5
        review: in_progress
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
  agent: session-implement (T1)     # 기본 경로. 격리 경로는 implementer (T1)
  result: "최소 구현 + focused 3/3 pass + 매직 넘버 상수화"
- phase: implement
  agent: reviewer (T1, task-scoped)
  result: "SPEC PASS · Critical 0, Important 1[동작불변] 정리, Minor 2 유예"
```

---

## --resume 호환

- `"기준선 게이트"` → Step 0.5부터 재실행
- `"태스크 분해 승인"` → Step 1.1부터 재실행
- `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: IMPLEMENT"` → state.md `flags`에 `--isolated`가 있으면 implementer 재디스패치, 없으면 세션이 `reports/t{N}-red.md`를 읽고 "세션 IMPLEMENT 절차"를 처음부터 재개 (report 파일이 있으면 그 진행분을 반영)
- `"RGR T{N}: FIX R{r}"` → 해당 태스크의 fix loop 라운드 {r}부터 재개 (report 파일이 영속 기억)
- `"RGR T{N}: REVIEW"` → Step 2-V 판정부터 재실행 (변경 파일·태스크 diff 재수집 후 디스패치)
- `"RGR T{N}: REVIEW R{r}"` → 라운드 {r}의 수정 diff 재수집 후 재리뷰부터 재개 (`reports/t{N}-review.md`가 이전 findings의 영속 기억)
- 구 세션 호환: `"RGR T{N}: GREEN"`/`"RGR T{N}: REFACTOR"`(3석 세대) → 해당 태스크를 위 IMPLEMENT 규칙(`flags`에 따라 세션 또는 implementer)으로 이어받는다. red 산출물(테스트 파일)은 유효하므로 RED 재실행 불필요. reports/가 없으므로 이 재개에 한해 테스트 코드·실패 메시지의 인라인 인계를 허용하고 execution-log에 "구 세대 전환 재개 — 인라인 인계"를 기록한다. 구 세션 state에는 `test-file` 기록이 없어 focused 집합을 복원할 수 없으므로, 이 태스크의 focused 실행은 전체 `test` 명령으로 폴백하고 execution-log에 기록한다. `test-file-hash`·porcelain 스냅샷은 구 state에 기록이 있으면 그대로 대조하고 없을 때만 생략한다. `test-count`는 정의가 달라(전체 vs focused) 비교하지 않고 재측정한다
- `"경계 회귀 수리"` → Step 3.5부터 재실행 (전체 테스트 재확인 후 수리)
- `"변경사항 수집"` → Step 5부터 재실행

## 판정 기록 (Rulings)

구현 내부 게이트 3곳 — verify_implement 5번(과잉 구현), phase-review 4b(동작 불변 정리), 4c(Minor·MEDIUM) — 는 사용자에게 묻지 않고 **기본값으로 판정**하고 근거를 남긴다. 답이 거의 항상 기본값인 질문에 사람을 세우지 않기 위해서다. 산출물 승인(PRD·설계·태스크 분해), SPEC FAIL, Critical, 동작 결함의 RGR 여부, 위험 수용은 이 규약의 대상이 **아니며** 계속 AskUserQuestion으로 확인한다.

**기록 위치**: `${DEV_DIR}/decisions.md` — AskUserQuestion 훅(capture-decision)이 쓰는 파일에 오케스트레이터가 append한다. 파일이 없으면 훅과 같은 헤더로 만든다:

```
# 의사결정 기록

AskUserQuestion으로 오간 질문과 선택을 자동 기록한다. 고른 것뿐 아니라 버린 선택지도 남으므로 왜 그렇게 정했는지가 추적된다.
```

**블록 형식** (한 판정 = 한 블록. 시각은 `date "+%Y-%m-%d %H:%M"`):

```
## {YYYY-MM-DD HH:MM} · Ruling: {제목}

**판정.** {무엇을 어떻게 했는가 — 파일·항목을 명시}
**근거.** {왜 그 기본값인가}
**틀리면.** {되돌리는 방법과 비용 — 예: reports/t2-impl.md "## 과잉 구현 정리" 목록으로 복원}
```

**기본값 표**:

| 게이트 | 기본 판정 | 예외 |
|---|---|---|
| verify_implement 5 과잉 구현 | focused 테스트 집합이 참조하지 않는 신규 public 멤버를 **제거**하고 focused를 재실행한다. 제거로 focused가 깨지면(간접 사용) 복원하고 `## 우려사항`에 기록한다 | 설계서 인터페이스가 명시한 멤버는 제거하지 않고 "설계 예약"으로 판정만 기록한다 |
| phase-review 4b 동작 불변 정리 | **수행**한다 (정리 모드 — 기본은 세션 직접, `--isolated`면 implementer) | 없음 |
| phase-review 4c quality Minor | **유예** — 수정하지 않고 Deferred 목록에 올린다 | 없음 |
| phase-review 4c security MEDIUM | 동작 불변이 명백하면 **정리 모드로 수정**, 동작 변경을 동반하거나 모호하면 **유예** | 없음 |

**노출**: 판정은 사용자가 되돌릴 수 있어야 하므로 워크스페이스 안에만 두지 않는다. Step 4 사이클 완료 보고와 phase-complete Step 2-1의 `pr-rulings.md`(`## Rulings` 제목 나열 + `## Deferred` 유예 목록)에 옮긴다.

---

## 금지 사항 (Iron Law 강제)

이 Phase에서 절대 호출하지 않는 에이전트:
- ❌ `coder` (deprecated) / `green-coder`·`refactor-coder` (파이프라인 미호출 — implementer로 통합. 단독 스킬 전용)
- ❌ `qa-manager` (자기점검은 reviewer가 phase-review에서 수행)

이 Phase에서 절대 수행하지 않는 동작:
- ❌ "구현 후 테스트 작성" — Iron Law 1 정면 위반
- ❌ RGR 사이클 병렬 실행 — 격리 깨짐
- ❌ "이번 한 번만" 코드 우선 작성 — 첫 예외가 규칙이 됨
- ❌ 검증 명령 생략 (verify_red/verify_implement) — Iron Law 3 위반
- ❌ 발동 조건(프로덕션 파일 2개 이상 또는 fix 라운드)을 충족한 태스크의 리뷰 생략 — "diff가 작아 보여서"는 사유가 아니다. 조건은 기계 판정이다 (gx-ralph 반복 세션은 Step 2-R/2-I 프롬프트만 빌려 쓰므로 이 불릿의 대상이 아니다)
- ❌ 태스크 리뷰의 동작 결함·spec FAIL을 재현 테스트 없이 fix loop로 수정 — Iron Law 1 위반. RED 재호출이 먼저다

위반 감지 시 즉시 중단하고 RED 단계부터 재시작한다.
