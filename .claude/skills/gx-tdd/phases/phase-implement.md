# phase-implement: RED-GREEN-REFACTOR 사이클 (TDD 강제)

Codex에서는 이 phase 파일 기준 `../../gx-work/references/codex-runtime.md`를 먼저 읽는다. 역할 index와 파일은 **그 runtime.md 파일과 같은 디렉토리**의 `codex-roles/`에서 찾는다. `agents/red-writer.md`·`agents/implementer.md`·`agents/reviewer.md` 표기는 역할 계약의 원본을 뜻하며, 배포된 Codex에서는 공통 매핑이 주입한 해당 역할 본문·도구 제약을 사용한다. 각 역할의 기존 report와 spec/quality YAML 반환 계약은 유지한다.

## Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

이 Phase는 **계획 검토·실행방법 확정 → RED 격리 디스패치 → IMPLEMENT**로 동작한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님). 태스크의 AC 시나리오 전부를 테스트 집합으로 한 번에 쓴다
- **IMPLEMENT** → 통과 최소 코드(GREEN) + 안전한 정리(REFACTOR — 동작 변경 금지). Step 1.3에서 현재 세션을 선택하면 **오케스트레이터가 직접 수행**한다 (Step 2-I "세션 IMPLEMENT 절차"). 서브에이전트를 선택하면 `--isolated`로 implementer를 디스패치한다 — 입력은 RED report+시그니처로 한정하되 기존 코드 Read는 허용, 테스트 실행은 focused 집합만. 어느 경로든 verify_implement의 해시·focused 직접 실행 검증은 같다

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.

> green-coder·refactor-coder는 이 파이프라인에서 호출하지 않는다 — 단독 스킬(gx-green·gx-refactor) 전용.

---

## 핵심 모드 분기 (core)

모드 분기와 RED 실행보다 먼저 `Read("../references/document-lifecycle.md")`의 사전 대조를 수행한다. 확정된 G-W-T AC·FR/W 연결과 현재 관련 문서 해시를 검사한다. `--phase implement`·`--resume`에서도 생략하지 않는다. 기존 입력을 재사용하고 차이만 보완하며, RED에는 이 보고서나 구현 본문을 추가하지 않는다.

오케스트레이터가 핵심 모드이면:
- Step 0에서 설계서(`design.md`)와 PRD(`prd.md`) 로드를 건너뛰고, `${DEV_DIR}/ac.md`를 Read하여 **G-W-T 형식 AC**를 추출한다 (phase-requirements core 분기가 저장).
- **Step 0.5(기준선 게이트)는 실행한다** (RGR이 강제되므로 기준 GREEN 확인과 warnings-baseline 기록이 필요하다).
- Step 1의 전체 분해·태스크 수 가드는 생략하고 ac.md의 각 AC를 기본 태스크로 하는 최소 실행표(파일·테스트 의도·명령·순서)를 준비한다. **Step 1.2 계획 검토와 Step 1.3 실행방법 확정은 수행한다**.
- **RGR 사이클은 유지**한다 (핵심 모드여도 TDD는 강제. Iron Law 1).
  - red-writer 입력: ac.md의 AC (G-W-T) + 기존 테스트 스타일 (설계서 testability 섹션 없음).
  - IMPLEMENT 입력(세션 또는 implementer): RED report 경로 + 기존 코드 인터페이스 (설계서 없음) + focused 테스트 명령.
- **Step 3.5(경계 회귀)는 건너뛴다** — 핵심 모드는 implement 다음이 곧 complete(verify)라, 실행하면 전체 스위트가 연달아 두 번 돈다.
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

RGR 사이클 진입 전에 [공통 테스트 실행 계약](../references/test-execution.md)을 읽고 **이번 변경의 영향 범위**로 기준선을 측정한다. `scripts/gx-test-plan.py plan`에 현재 실행 run-id·base와 승인된 태스크의 소스/기존 테스트 ownership을 전달한다. 신규 RED 테스트는 아직 기준선에 넣지 않는다. 매핑되지 않은 변경·공통 설정/의존성 변경·명시적 `--full-tests`에서만 전체로 확장하고 이유를 기록한다.

동일 실행·동일 코드·설정·명령·범위·정상 로그의 성공 proof가 있으면 `reuse`로 검증한 뒤 재실행하지 않는다. 없으면 plan entry를 순차 실행하고 `record`로 증거를 기록한다. test와 `buildOnly`를 사용해 Gradle build의 테스트 중복을 피한다. 선택된 테스트의 0건·실패·검증 명령 오류는 성공으로 기록하지 않는다. SVN은 재사용 없이 등록된 테스트와 buildOnly를 보수적으로 실행한다. 출력 캡처와 경고 추출은 gx-verify Step 2 규약을 따른다. 아래 판정 1~5는 유지한다.

1. **기준 GREEN 확인**: 기존 테스트가 깨져 있으면 사용자에게 보고하고 진행 여부를 확인한다 (깨진 기준 위에서는 RGR의 회귀 판정이 성립하지 않는다).
2. **warnings-baseline 기록**: 같은 선택 명령·범위의 테스트+buildOnly 출력의 경고 수를 세어 state.md **최상위 필드** `warnings-baseline: N`으로 기록한다. phase-complete의 verify 게이트가 이 값과 비교하여 **이번 구현이 유입한 경고부터** 차단한다 (기존 경고는 허용).
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
      { label: "하네스 구축 후 재실행", description: "테스트 러너를 먼저 설치합니다. 러너가 없으면 실패 테스트를 쓸 수 없어 gx-tdd로는 구축할 수 없습니다 — oh-my-gx:gx-work로 별도 수행 후 이 파이프라인을 재개하세요" },
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

### 기준선 사전 실행

요구사항을 이해하기 전에는 전체 테스트를 백그라운드에서 시작하지 않는다. 영향 범위가 확정된 뒤 공통 테스트 계획을 생성하고 필요한 명령만 실행한다. 기존 `baseline.done`·옛 proof는 현재 run-id·지문·설정·명령·범위가 일치하지 않으면 재사용하지 않는다. 서로 다른 테스트·빌드를 동시에 시작하지 않는다.

경고 baseline은 실제 명령과 scope를 함께 기록한다. 최종 선택 범위가 달라졌으면 경고 합계를 직접 비교하지 않고 `경고 비교 미수행: 선택 범위 변경`으로 보고한다. 범위를 바꾼 측정을 0건으로 가장하지 않는다.

## Step 1: 태스크 분해 (오케스트레이터 직접 수행)

`--from-plan`·`--handoff`에서 검증한 `units[]`가 있으면 [계획 인계 계약](../references/plan-handoff.md)에 따라 기존 태스크를 그대로 T태스크에 매핑한다. request 인계에는 units가 없을 수 있으므로 기존 PRD·설계에서 이 단계의 구체 계획을 만든다. AC·파일·의존 조건이 부족한 태스크만 보완하며 유효한 목록 전체를 다시 분해하지 않는다. 외부 계획·core·재개도 Step 1.2~1.3의 검토·방법 게이트를 통과한다. 같은 run·계획의 실제 승인 기록은 재사용한다.

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

태스크마다 정확한 변경/테스트 파일 경로, 공개 인터페이스·제약, G-W-T 시나리오·경계값, RED→GREEN→REFACTOR의 구체 순서, focused 명령·cwd·예상 실패/성공과 검증·리뷰 초점을 기재한다. 코드 전체를 미리 작성하지 않는다. 기존 유효한 구체 계획 파일이 있으면 해당 절을 재사용하고, 없으면 위 내용을 `${DEV_DIR}/implementation-plan.md`에 저장한다. `implementation-plan-file`에 절대 포인터, `implementation-plan-sha256`에 파일의 현재 SHA-256을 기록한다. 외부 request-file/plan-file을 이 내부 계획 포인터로 덮지 않는다.

### 1.15 태스크 수 가드

태스크가 **8개를 넘으면** 승인 게이트 전에 한 질문으로 재분해·작업 분할·그대로 진행을 선택받는다. 태스크마다 RED 작성과 검증 비용이 있으므로 같은 컴포넌트/패턴의 AC를 합칠 수 있는지 먼저 확인한다. 실행 가능한 선택지만 2~3개로 제시한다.

```
AskUserQuestion(
  questions: [{
    question: "태스크가 {N}개로 분해됐습니다. 어떻게 진행할까요?",
    header: "태스크 수",
    options: [
      { label: "AC 묶어서 재분해 (Recommended)", description: "같은 컴포넌트·같은 패턴의 AC를 묶어 태스크를 줄입니다. RGR 강도는 유지합니다" },
      { label: "작업 계획으로 분할", description: "이번 실행 범위를 줄이고 나머지 AC를 후속 W작업으로 등록합니다" },
      { label: "그대로 진행", description: "{N}개를 이 세션에서 진행하고, 중단하면 --resume으로 이어갑니다" }
    ],
    multiSelect: false
  }]
)
```

- **AC 묶어서 재분해** → 조건 1의 묶기 규칙을 적용해 1.1 표를 다시 제시한다. 여전히 8개를 넘으면 이 가드를 한 번 더 거친다 (최대 2회).
- **작업 계획으로 분할** → `.dev/plan.md`가 없거나 문서 수정 금지이면 이 선택지를 **제외**한다. 허용된 경우 앞 8개 태스크로 범위를 줄이고 나머지 AC를 `.dev/plan.md`에 `대기` W행으로 로컬 추가한다 (같은 도메인·브랜치 규칙, 선행은 현재 `work-id`). 여기서 stage/commit/push하지 않는다. [실행 종료점](../references/execution-boundaries.md)에 따라 최종 검증 후 요청된 commit/pr 완료 단계에 함께 반영한다. trust-ledger `### 위험 수용`에 `- [범위 분할] AC-N…: 후속 W행으로 이관 (implement/Step 1.15)`를 기록한다.
- **그대로 진행** → 1.2로 진행한다. execution-log에 `"태스크 수 가드 통과(사용자 선택): {N}개"`를 남긴다.

문서 분할이 불가능하면 재분해/그대로 진행의 두 선택지를 제시한다. 핵심 모드는 전체 분해를 생략하므로 이 수 가드는 타지 않는다 (AC 3~5개 = 태스크 3~5개). 최소 실행표를 파일에 보존한 뒤 1.2로 간다.

### 1.2 계획 검토·실행방법 확인

계획 링크와 핵심 태스크·범위·순서·명령을 제시하고 **한 질문에서 계획 검토와 실행방법을 함께 확인**한다. 현재 PRD/AC·설계와 달라진 태스크는 계획 파일에 반영해 해시를 갱신한다. gx-work의 진입 승인과 원래 구현 요청은 이 검토 응답을 대신하지 않는다. `plan-approved-run`·`plan-approved-sha256`이 현재 run·내부 계획 파일 해시와 일치하고 `plan-approved-source`에 실제 응답 근거가 있으면 계획은 재질문하지 않고 1.3에서 방법 기록을 검증한다. 외부 계획의 실제 검토 근거도 현재 파일/범위에 대응할 때만 이 필드로 보존해 재사용한다.

```
AskUserQuestion(
  questions: [{
    question: "이 계획을 어떤 방식으로 구현할까요?",
    header: "계획·실행방법",
    options: [
      { label: "현재 세션에서 구현 (Recommended)", description: "계획을 승인하고 이 세션이 GREEN·REFACTOR를 수행합니다. RED와 리뷰는 별도 에이전트가 담당합니다" },
      { label: "서브에이전트로 구현", description: "계획을 승인하고 implementer에 GREEN·REFACTOR를 위임합니다. RED와 리뷰의 격리는 유지합니다" },
      { label: "계획 문서로 종료", description: "계획을 전달하고 이번에는 구현하지 않습니다" }
    ],
    multiSelect: false
  }]
)
```

- **현재 세션/서브에이전트** → 한 실제 응답으로 `plan-approved-source`·`plan-approved-run`·`plan-approved-sha256`과 `execution-method`·`execution-method-run`·`execution-method-plan-sha256`·`execution-method-source`를 모두 기록하고 Step 1.3에서 검증·flags 반영한다. 승인 질문을 추가하지 않는다.
- **초기 명시 방법 있음** → 그 선택을 보존해 질문을 "이 계획을 {현재 세션/서브에이전트}으로 진행할까요?"로 바꾸고 "계획 승인"·"수정 요청"·"계획 문서로 종료"를 제시한다. 실제 계획 승인 응답과 원래 명시 선택 근거를 각각 기록해 두 승인 필드를 모두 확정한다. 방법을 다시 고르게 하지 않는다.
- **계획 승인만 응답, 방법 미정** → plan-approved 세 필드만 기록하고 Step 1.3에서 빠진 방법만 확인한다.
- **계획 문서로 종료** → Step 1.3의 미구현 종료 처리를 즉시 수행한다.
- **수정 요청** → 수정 선택 시 별도 후속 질문에서 변경할 항목을 묻고 실제 수정 답변을 기다린 뒤 수정 내용을 반영한다. 원 질문 UI Other에 수정 내용이 있으면 그 답변을 사용한다. 계획을 재제시하며 기존 계획·방법 승인 해시는 새 계획에 재사용하지 않는다.

질문 대기 중 `current-step`을 `"태스크 분해 승인"`으로 유지한다. Codex는 [질문 대기 계약](../../gx-work/references/codex-questions.md)의 pending 등록·표시·실제 answer 기록을 수행한다. 무응답·도구 ack·추천 값은 승인이 아니다. 헤드리스는 BLOCKED와 질문을 기록해 중단한다.

### 1.3 실행방법 검증·반영

Step 1.2 이후 첫 RED 전에 수행한다. 설계서에 구현 순서가 없으면 AC 단위 계획을 만들고, core·외부 계획·재개도 같은 게이트를 사용한다.

Step 1.2의 응답 또는 기존 기록에서 현재 `run-id`·내부 계획 해시와 `execution-method-run`·`execution-method-plan-sha256`이 같고 `execution-method-source`에 실제 선택 근거가 있으면 추가 질문 없이 flags를 반영한다. 초기 명시 방법도 실제 계획 검토 응답과 연결됐으면 같은 규칙으로 처리한다. **계획 승인만 받았고 방법이 미정일 때에만** Step 1.2의 세 방법 선택지를 사용해 "계획 검토는 완료됐습니다. 어떤 방식으로 진행할까요?"라고 질문한다. 계획 승인 질문을 반복하지 않는다.

- **현재 세션** → `execution-method: session`. 초기 방법 확정에서 `--isolated`를 제외한다.
- **서브에이전트** → `execution-method: subagents`. 초기 방법 확정에서 `--isolated`를 추가해 Step 2-I가 실제 implementer 경로를 쓰도록 한다. 나머지 플래그는 보존한다.
- **계획 문서로 종료** → `phase: implement`·`status: in_progress`·`current-step: 계획 문서로 종료`·`verify-status: pending`·빈 verify 지문을 유지한다. 계획 경로와 미구현 범위를 보고하고 **이 파이프라인을 여기서 종료**한다. 방법 승인·implement 완료·verify 통과로 기록하지 않으며 RED/코드 변경·review/complete/commit/PR로 체이닝하지 않는다. 원래 stop-at을 확대하거나 삭제하지 않는다.

확정된 방법에는 `execution-method-run`·`execution-method-plan-sha256`·`execution-method-source`로 현재 run·승인된 계획 해시·실제 선택 출처를 기록한 뒤 Step 2로 간다. 이미 기록된 방법/복원 flags/이번 명시 `--isolated`가 충돌하면 사유를 보고하고 실제 결정으로 해소하기 전 실행하지 않는다. 기존 방법을 기본값으로 바꾸거나 flags를 조용히 재작성하지 않는다. 명시 방법 없는 flags의 부재를 session 선택으로 간주하지 않는다.

질문 대기 중 `current-step: 실행방법 선택`을 유지한다. Codex는 위 질문 계약으로 등록·표시하고 실제 답을 기다린다. 무응답이면 선택 의존 작업을 멈추고 질문을 포함해 응답하며, 헤드리스는 BLOCKED를 기록한다.

---

## Step 2: RGR 사이클 (태스크별 순차)

Step 1.2~1.3의 현재 run·계획 검토·방법 기록과 실제 flags의 일치를 확인한 뒤 진입한다. 재개한 RGR 중간 Step도 이 검증을 먼저 수행한다.

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

명시된 focused 명령이 없으면 설치 플러그인의 `scripts/gx-test-plan.py` 절대경로와 해당 프로젝트 ID(`TYPE:RELROOT`)를 프롬프트에 포함한다. red-writer는 테스트 파일을 먼저 저장한 뒤 공통 계약의 `focused` CLI로 **현재 태스크 파일만** 선택해 실패를 확인한다. helper는 설정·package의 명령·테스트 경로를 확인할 뿐 기존 프로덕션 본문을 읽지 않는다. 실행 방식이 불명확하면 focusedTest를 보완하며 전체 npm test를 매번 자동 실행하지 않는다.

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
    2. 테스트를 저장한 뒤 focused helper가 반환한 `cwd`에서 `command`를 실행해 실패 확인 (실행 위치와 에러 메시지 캡처)
    3. 실패 사유 분류 (NoSuchMethod / assertion / etc)

    [작성 범위 — 테스트 집합]
    이 태스크에 매핑된 AC의 G-W-T 시나리오 **전부**를 각각 테스트 케이스로 작성합니다 (시나리오 1건 = 케이스 1건). 컴포넌트당 테스트 파일 하나에 모읍니다. 케이스마다 실패 확인 명령을 실행해 전부 실패하는지 확인하고, 통과하는 케이스가 있으면 기존 동작을 검증하는 잘못된 케이스이므로 다시 씁니다.

    [report 파일]
    {reports/t{N}-red.md} — 테스트 코드 전문·케이스 목록(케이스 수 명시)·실패 확인 명령과 실행 위치·케이스별 실패 메시지·참조한 파일 전체 목록을 이 파일에 Write하십시오

    [반환 형식 — 15줄 이내. 전문은 report 파일에]
    - Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
    - 테스트 파일: {경로}
    - 실패 확인: {1줄 — 명령 + 케이스 수 + 실패 유형 (NoSuchMethod / assertion / etc)}
    - 우려사항: {1~2줄, 없으면 "없음"}
    - report: {reports/t{N}-red.md}
```

**verify_red**: 오케스트레이터가 직접 검증.
1. report 파일(`reports/t{N}-red.md`)에서 테스트 파일 경로·케이스 목록·실패 확인 명령과 실행 위치를 읽는다. helper의 `cwd`는 프로젝트 루트에 대한 상대경로이며 모든 직접 재실행도 `${PROJECT_ROOT}/${focused.cwd}`에서 같은 `command`를 사용한다.
2. **실패 확인 (집합 전체)**: report의 실패 확인 명령을 직접 실행해 신규 케이스가 **모두** 실패하는지 본다 (실패 건수 = report의 케이스 수). 통과하는 케이스가 있으면 그 케이스만 지목해 red-writer를 재호출한다 (전체 재작성 아님). 에러(컴파일 실패·러너 오류)로 끝난 것은 실패가 아니다 — 원인을 report와 대조해 red-writer 재호출. **재현 RED**(Step 2-V RED 재호출)에서는 통과하는 케이스가 finding의 오탐을 뜻하므로 재호출하지 않는다 — 3번의 재현 RED 예외를 따른다.
3. 실패 사유가 "이미 구현이 있어서 통과"이면 → AC를 더 좁히도록 사용자에게 안내 후 중단. **재현 RED 예외**: Step 2-V RED 재호출에서는 이 통과가 finding이 실제 결함이 아니라는 뜻이다 — 사용자에게 묻지 않고 그 finding을 '재현 불가' 근거(통과한 케이스와 실행 출력)와 함께 재리뷰에 넘기며 라운드를 1 소모한다. 이 재리뷰는 수정 diff 없이 진행한다 — `reports/t{N}-diff-r{r}.txt` 대신 '재현 불가' 근거만 `[재리뷰]` 절에 싣는다.
4. **격리 오염 검증**: report 파일의 "참조한 파일" 목록에 프로덕션 소스가 포함되어 있으면 → 해당 테스트 폐기 후 red-writer 재호출 (구현에 적응한 오염된 RED일 수 있음).
5. **`NEEDS_CONTEXT` 처리**: red-writer가 `NEEDS_CONTEXT`(설계서 인터페이스 불충분 등)를 반환하면 — 전체 모드: phase-design 재실행(테스트 전략 보강) 여부를 사용자에게 확인. 핵심 모드: AskUserQuestion(자유입력)으로 대상 인터페이스 정보를 받아 red-writer에 보강 전달 후 재호출.
6. **테스트 파일 해시 기록**: `git hash-object "{테스트 파일}"` 결과를 state.md 해당 태스크의 `test-file-hash`로 기록한다 (GREEN의 테스트 무결성 기준선. untracked 파일에도 동작. 경로는 따옴표로 감싼다). 동시에 `git -c core.quotePath=false status --porcelain > ${DEV_DIR}/rgr-t{N}-porcelain.txt`로 스냅샷을 **파일로 저장**한다 (GREEN에서 **다른 테스트 파일** 변경을 잡기 위한 기준선. **svn 프로젝트는 `svn status`를 사용**. 파일이 DEV_DIR에 남으므로 --resume 재개 시에도 기준선이 유지된다). 테스트 파일 경로를 state.md 해당 태스크의 `test-file`로 기록한다 (focused 집합 조립에 사용).
7. **report 저장 확인**: `reports/t{N}-red.md`가 존재하고 테스트 코드·실패 메시지를 담고 있는지 확인한다. 다음 단계(2-I) 인계는 이 파일 경로로만 한다.
8. ✅ 실패 정상 → IMPLEMENT(2-I)로 진행.

`current-step`을 `"RGR T{N}: RED"`로 갱신.

---

### Step 2-I: IMPLEMENT (세션 직접 수행 — GREEN+REFACTOR 통합. `--isolated`면 implementer 디스패치)

기본 경로에서는 **오케스트레이터가 이 단계를 직접 수행**한다 — 태스크당 콜드 스타트를 red-writer 1회로 줄이기 위해서다. verify_implement의 검증은 파일 상태 대조(해시·porcelain·focused 직접 실행)라 수행 주체와 무관하게 같은 강도로 동작한다. state.md `flags`에 `--isolated`가 있으면 아래 "격리 경로"의 implementer 디스패치를 대신 쓴다.

**세션 IMPLEMENT 절차** (`agents/implementer.md`의 절대 규칙·REFACTOR 범위·report 형식과 같은 계약이다 — 한쪽을 고치면 함께 갱신. `references/maintenance-notes.md` 참조):

[절대 규칙]
1. 테스트 파일을 수정하지 않는다. 테스트가 실패하면 코드를 고친다. 테스트 자체 결함이 의심되면 고치지 말고 report `## 우려사항`에 "테스트 결함 의심"으로 적고 verify_implement 2번을 따른다.
2. GREEN: 실패 테스트를 통과시키는 최소 코드만 작성한다 (YAGNI — 추가 기능/에러 핸들링/검증/로깅 금지).
3. REFACTOR: 동작 변경 금지. 매 정리 후 focused 테스트로 GREEN 유지 확인, 깨지면 즉시 롤백.
4. 테스트 실행은 focused 명령만 사용한다 — 대상은 이 태스크의 `test-file` 기록 파일뿐이며 와일드카드(`*DbTest` 등)·패키지/모듈 묶음·회귀 확인용 이웃 클래스를 덧붙이지 않는다. 회귀 범위는 완료 verify(`--phase implement` 단독은 Step 3.5)의 공통 영향 계획으로 결정하고, 다른 테스트·빌드 명령이 실행 중이면 새 실행을 시작하지 않는다.
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
5. self-review 후 `reports/t{N}-impl.md`를 Write한다. 형식은 `agents/implementer.md`의 report 형식과 같다 — `## 구현 내용` / `## GREEN 증거`(focused 명령 + "N pass / 0 fail" 출력 요약) / `## REFACTOR 내역` / `## self-review 결과` / `## 우려사항`. verify_implement 5가 append하는 `## 과잉 구현 정리`는 6번째 절이며, fix 라운드에서 report를 다시 쓸 때 보존한다.
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
    4. 테스트 실행은 아래 focused 명령만 사용합니다. 명령에 테스트를 덧붙이거나 와일드카드·패키지/모듈 묶음으로 넓히지 않고, 전체 스위트를 임의로 실행하지 않습니다.
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
    {오케스트레이터가 조립한 명령 — 이 태스크의 test-file 기록 파일만}

    [focused 테스트 실행 위치]
    {PROJECT_ROOT}/{FOCUSED_CWD}
    위 명령은 이 디렉터리에서 실행합니다. FOCUSED_CWD는 helper가 반환한 프로젝트 루트 상대 cwd입니다.

    [report 파일]
    {reports/t{N}-impl.md} — 전문 보고를 이 파일에 Write하십시오 (agents/implementer.md의 report 형식)

    [프로젝트 루트]
    {PROJECT_ROOT}

    [반환 형식 — 15줄 이내]
    - Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
    - 변경 파일 / 테스트 1줄 요약 / 우려사항 / report 경로
```


**focused 테스트 명령 조립**: 테스트 파일을 저장한 뒤 [공통 실행 계약](../references/test-execution.md)의 `focused` CLI로 현재 태스크의 `test-file` 경로 배열만 전달한다. 명시적 focusedTest를 우선하고, 없을 때 실제 등록된 알려진 runner만 해석한다. 이전 태스크·이웃 클래스·와일드카드로 범위를 넓히지 않는다. RED 작성자는 파일을 먼저 저장한 뒤 같은 절차로 실패를 확인하며, 조정자는 RED/IMPLEMENT 검증에서 반환된 명령을 직접 실행한다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-plan.py" focused --cwd "$PROJECT_ROOT" \
  --project "{TYPE}:{RELROOT}" --tests-file "{현재 태스크 테스트 경로 JSON}"
```

exit0이면 command·cwd·scope를 함께 기록하고 `${PROJECT_ROOT}/${focused.cwd}`에서 Git Bash로 command를 실행한다. 격리 프롬프트의 FOCUSED_CWD에 반환된 cwd를 전달하고 RED/IMPL report·직접 재실행에서도 이 쌍을 보존한다. exit2는 focusedTest 설정이 필요한 상태다. 먼저 프로젝트의 실제 runner/스크립트에서 지원하는 옵션을 확인해 그 설정만 보완한다. 확인할 수 없으면 사용자에게 필요한 명령 또는 명시적인 전체 실행 여부를 한 번 확인하고 이번 실행에 보존한다. 같은 질문과 전체 폴백을 태스크마다 반복하지 않는다. 헤드리스는 설정 부족을 BLOCKED로 보고한다. exit1이나 테스트 자체 실패를 runner 미지원으로 숨기지 않는다.

**명령 오류 가드**: 테스트 결과 요약 없이 끝난 옵션·러너 오류는 fix loop에서 제품 결함으로 다루지 않는다. 실제 설정을 보완한 뒤 현재 태스크만 재실행한다. 전체 검사는 공통 영향 계획과 명시적인 전체 실행 선택으로만 결정한다.
**verify_implement**: 오케스트레이터가 직접 검증. **저비용 검사(1~3번)를 테스트 실행보다 먼저 수행한다.**
1. **Status 분기** (격리 경로에서만 상태가 반환된다. 세션 경로는 report `## 우려사항`에 "없음" 외의 내용이 있으면 DONE_WITH_CONCERNS로 취급한다): `NEEDS_CONTEXT` → 요청된 정보를 보강해 재디스패치 (라운드 미소모, 태스크당 최대 2회 — 초과 시 BLOCKED로 승격해 처리한다). `BLOCKED` → 컨텍스트 보강 / 모델 격상 / 태스크 분할 / 설계 재확인 중 판정 후 처리. `DONE_WITH_CONCERNS` → report의 우려를 Read하고 정합성 문제면 fix 라운드로, 관찰이면 기록 후 진행.
2. **테스트 결함 의심 확인**: 보고됐으면 사유 확인 후 **red-writer 재호출**로 테스트를 재작성한다 (구현 주체가 테스트를 고치지 않는다).
3. **테스트 무결성 확인**: `git hash-object "{테스트 파일}"`을 재실행하여 verify_red의 `test-file-hash`와 비교하고, `git -c core.quotePath=false status --porcelain`(svn은 `svn status`)을 verify_red 스냅샷 파일(`${DEV_DIR}/rgr-t{N}-porcelain.txt`)과 대조한다 — **대조는 테스트 파일 라인만 필터**하여 수행한다(판별 글롭은 Step 0.5 4항의 테스트 파일 글롭 `**/*test*`·`**/*Test*`·`**/*spec*` 재사용. `.dev/` 경로 라인은 제외. svn은 `svn status` 출력의 경로 컬럼 기준으로 같은 필터를 적용). **이전 태스크들의 `test-file-hash`도 재검증**한다. 무단 수정 감지 → 해당 테스트를 RED 산출물로 원복하고 구현 주체가 1회 재수행한다 — 세션 경로는 세션이 원복 후 재구현, 격리 경로는 implementer 재호출 ("테스트 수정 금지" 재강조 — fix 라운드와 별도 카운트). 재차 위반 시 사이클 중단·사용자 보고.
4. **focused 집합 직접 실행**: 위 focused 명령을 오케스트레이터가 1회 직접 실행한다 — 통과 목격(증거 주체는 오케스트레이터, verify_red와 대칭) + 결과의 테스트 수를 state.md 해당 태스크의 `test-count`로 기록한다. **같은 태스크의 직전 `test-count`와 비교**해 감소하면 사유를 확인한다(무단 삭제면 롤백 요청). 첫 기록이거나, 직전 기록 이후 red-writer 재호출로 verify_red가 `test-file-hash`를 다시 기록했으면(정당한 테스트 변경) 비교하지 않고 새 값을 기준으로 삼는다. 태스크마다 대상 집합이 다르므로 태스크 간 비교는 하지 않는다. **전체 스위트는 실행하지 않는다** — 태스크 간 회귀는 phase-review Step 0(누적 실행), 기존 스위트 회귀는 완료 verify(`--phase implement` 단독: Step 3.5)가 담당한다.
5. **과잉 구현 판정**: 추가된 public 메서드/필드 중 focused 테스트 집합이 참조하지 않는 것을 찾는다. 있으면 **묻지 않고 판정한다** — "판정 기록 (Rulings)" 절의 기본값대로 설계서 인터페이스가 명시한 멤버는 "설계 예약"으로 유지하고, 그 외는 제거한 뒤 focused를 재실행한다 (제거는 기본 경로에서 세션이 직접, `--isolated`면 implementer에 요청한다 — 4b와 같은 경로 구분. 제거로 깨지면 복원하고 `## 우려사항`에 기록하되, 이것은 관찰이므로 1번의 DONE_WITH_CONCERNS 판정에는 넣지 않는다). 제거·유지 목록을 `reports/t{N}-impl.md`에 `## 과잉 구현 정리` 절로 append하고, decisions.md에 `Ruling: T{N} 과잉 구현 정리` 블록을 append한다. 판정할 것이 없으면 아무것도 기록하지 않는다.
6. **public 인터페이스 시그니처 변경 없음 확인**: diff에서 공개 메서드·함수·타입 시그니처 라인의 변경을 대조한다 (REFACTOR 금지 목록 위반 — 발견 시 롤백한다. 격리 경로는 implementer에 롤백 요청).
7. ✅ 통과 + 무결성 유지 → **Step 2-V 태스크 리뷰 판정**으로 진행한다 (발동 조건 미충족이면 `review: skipped` 기록 후 태스크 완료).
8. ❌ 실패 → **fix loop 진입** (아래).

**fix loop (실패 시 — 태스크당 최대 5라운드)**:

첫 수정 전에 [실패 조사](../references/failure-investigation.md)를 읽고 재현·가설·근거를 기록한다. 매 라운드 이 fix loop 절을 디스크에서 다시 읽어 5회 상한과 격상·중단 조건을 복원한다. 이전 대화의 기억만으로 상한을 연장하지 않는다.

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
   - `ac_unverified > 0` 또는 ❓ 항목이 있으면 [리뷰 근거 보강](../references/review-evidence.md)을 먼저 수행한다. 실제 결함으로 확정된 항목만 아래 RED 경로로 보낸다. 미해결 확인 불가가 있으면 태스크 완료 표시를 하지 않는다.
   - `spec_verdict: FAIL`, Critical, Important `[동작결함]`(무표기 포함) → **RED 재호출 후 fix loop 진입** (Iron Law 1 — 동작 결함은 그것을 재현하는 실패 테스트가 먼저 있어야 고친다. 기존 fix loop는 verify_red 기준선의 테스트를 통과시키는 루프라 그 안에서는 테스트를 추가할 수 없으므로 RED를 먼저 연다):
     1. **RED 재호출**: red-writer를 Step 2-R 프롬프트로 재디스패치한다. `[AC (Given-When-Then)]`에는 미충족 AC(spec FAIL) 또는 finding을 재현 조건으로 옮긴 시나리오(Critical·`[동작결함]`: Given 현재 상태 / When 트리거 / Then 기대 동작)를 넣고, `[작성 범위 — 테스트 집합]` 뒤에 "이 태스크의 기존 테스트 파일에 케이스를 **추가**합니다 (기존 케이스 수정·삭제 금지)"를 덧붙인다. verify_red 1~7을 그대로 재적용한다 (2·3번의 재현 RED 예외 — "이미 구현이 있어서 통과"는 finding의 오탐이므로 '재현 불가' 근거만으로 재리뷰에 넘긴다) — 새 케이스만 실패해야 하고 기존 케이스는 통과를 유지하며, `test-file-hash`·`rgr-t{N}-porcelain.txt`·`test-count` 기준선을 **갱신**한다. report는 `reports/t{N}-red.md`에 `## 재현 RED R{r}` 절로 append한다.
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

## Step 3.5: 경계 회귀 (--phase implement 단독 전용)

같은 실행에서 complete가 이어지면 중복 실행하지 않는다. `--phase implement` 단독이면 공통 영향 계획으로 누적된 태스크와 변경 범위를 검증한다. 매핑/설정/의존성 불확실성 또는 명시적 전체 검사에서만 전체 테스트를 실행한다. 변경되지 않은 코드의 동일 plan entry는 `reuse` 성공 증거로 확인하며, 코드가 바뀌면 이전 증거를 쓰지 않는다.

실패 시 대상 테스트·에러·focused 명령을 implementer **수리 모드**로 전달한다. RED report 없음, 테스트 파일 무변경 확인, 수리 1회 상한은 유지한다. 수리 후 변경된 범위의 plan/proof를 갱신하고 관련 테스트를 실행한다. 재차 실패하면 사용자에게 보고한다. `current-step: 경계 회귀 수리`로 기록한다.

## Step 4: 사이클 완료 보고

모든 태스크 완료 후 사용자에게 **요약만** 보고한다 (Agent 전문 출력 금지).

```
RGR 사이클 완료: {N}개 태스크

- T1 (AC-1): RED ✅ → IMPLEMENT ✅ → REVIEW skip (파일 1개)
- T2 (AC-2, AC-3 배칭): RED ✅ → IMPLEMENT ✅ (fix 라운드 1회) → REVIEW ✅ (Important 1건 정리, Minor 2건 유예)
- T3 (AC-4): RED ✅ → IMPLEMENT ✅ (정리 대상 없음) → REVIEW ✅

focused: 태스크별 {N pass}, 0 fail (태스크 간 회귀는 review Step 0, 전체 회귀는 complete verify — `--phase implement` 단독: Step 3.5)
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
implementation-plan-file: "/absolute/project/.dev/task/implementation-plan.md"
implementation-plan-sha256: "계획 파일 SHA-256"
plan-approved-run: "현재 run-id"
plan-approved-source: "계획 검토의 실제 응답 출처"
plan-approved-sha256: "계획 파일 SHA-256"
execution-method: session
execution-method-run: "현재 run-id"
execution-method-plan-sha256: "계획 파일 SHA-256"
execution-method-source: "실제 방법 선택 출처"
steps:
  implement:
    - 태스크 분해 승인: completed
    - 실행방법 선택: completed
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

모든 항목보다 먼저 setup-resume 0.05의 진입 승인·현재 계획 해시·방법/flags를 검증한다. 유효한 같은 run·계획의 선택은 재사용하고, 부족한 계획 검토/방법만 Step 1.2~1.3에서 확정한 후 아래 중단 지점으로 돌아온다. 완료된 RED·태스크/보고서·fix 카운터는 보존한다.

- `"기준선 게이트"` → Step 0.5부터 재실행
- `"태스크 분해 승인"` → 저장된 내부 계획·해시를 읽어 Step 1.2부터 재개. 유효한 계획 전체를 다시 분해하지 않는다.
- `"실행방법 선택"` → Step 1.3에서 원래 미응답 질문을 복원한다.
- `"계획 문서로 종료"` → 미구현 상태와 계획 경로를 보고하고 종료한다. 사용자의 새 실제 실행 응답이 있으면 같은 계획의 Step 1.3에서 이어간다.
- `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: IMPLEMENT"` → state.md `flags`에 `--isolated`가 있으면 implementer 재디스패치, 없으면 세션이 `reports/t{N}-red.md`를 읽고 "세션 IMPLEMENT 절차"를 처음부터 재개 (report 파일이 있으면 그 진행분을 반영)
- `"RGR T{N}: FIX R{r}"` → 해당 태스크의 fix loop 라운드 {r}부터 재개 (report 파일이 영속 기억)
- `"RGR T{N}: REVIEW"` → Step 2-V 판정부터 재실행 (변경 파일·태스크 diff 재수집 후 디스패치)
- `"RGR T{N}: REVIEW R{r}"` → 라운드 {r}의 수정 diff 재수집 후 재리뷰부터 재개 (`reports/t{N}-review.md`가 이전 findings의 영속 기억)
- 구 세션 호환: `"RGR T{N}: GREEN"`/`"RGR T{N}: REFACTOR"`(3석 세대) → 해당 태스크를 위 IMPLEMENT 규칙(`flags`에 따라 세션 또는 implementer)으로 이어받는다. red 산출물(테스트 파일)은 유효하므로 RED 재실행 불필요. reports/가 없으므로 이 재개에 한해 테스트 코드·실패 메시지의 인라인 인계를 허용하고 execution-log에 "구 세대 전환 재개 — 인라인 인계"를 기록한다. 구 세션 state에 `test-file` 기록이 없으면 RED 산출물과 실제 파일을 대조해 현재 태스크 경로를 복원한 뒤 공통 `focused` CLI를 사용한다. 복원이 불가능하면 필요한 경로를 확인할 때까지 중단하며 전체 `test`로 자동 폴백하지 않는다. `test-file-hash`·porcelain 스냅샷은 구 state에 기록이 있으면 그대로 대조하고 없을 때만 생략한다. `test-count`는 정의가 달라(전체 vs focused) 비교하지 않고 재측정한다
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
| verify_implement 5 과잉 구현 | focused 테스트 집합이 참조하지 않는 신규 public 멤버를 **제거**하고 focused를 재실행한다 (기본은 세션 직접, `--isolated`면 implementer). 제거로 focused가 깨지면(간접 사용) 복원하고 `## 우려사항`에 기록한다 | 설계서 인터페이스가 명시한 멤버는 제거하지 않고 "설계 예약"으로 판정만 기록한다 |
| phase-review 4b 동작 불변 정리 | **수행**한다 (정리 모드 — 기본은 세션 직접, `--isolated`면 implementer) | 없음 |
| phase-review 4c quality Minor | **유예** — 수정하지 않고 Deferred 목록에 올린다 | 없음 |
| phase-review 4c security MEDIUM | 동작 불변이 명백하면 **정리 모드로 수정**, 동작 변경을 동반하거나 모호하면 **유예** | 없음 |

**노출**: 판정은 사용자가 되돌릴 수 있어야 하므로 워크스페이스 안에만 두지 않는다. Step 4 사이클 완료 보고, phase-review 4c 말미의 통지, phase-complete Step 2-1의 `pr-rulings.md`(`## Rulings` 제목 나열 + `## Deferred` 유예 목록)에 옮긴다.

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
- ❌ 발동 조건(프로덕션 파일 2개 이상 또는 fix 라운드)을 충족한 태스크의 리뷰 생략 — "diff가 작아 보여서"는 사유가 아니다. 조건은 기계 판정이다
- ❌ 태스크 리뷰의 동작 결함·spec FAIL을 재현 테스트 없이 fix loop로 수정 — Iron Law 1 위반. RED 재호출이 먼저다

위반 감지 시 즉시 중단하고 RED 단계부터 재시작한다.
