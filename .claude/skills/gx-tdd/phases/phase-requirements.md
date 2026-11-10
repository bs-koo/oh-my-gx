# phase-requirements: PRD Q&A 사이클 (Given-When-Then 강제)

core 분기·기존 계획 재사용으로 종료하기 전에, 새 요구가 이전 팀 판단을 바꿀 수 있으면 [공유 결정 이력 대조](../../gx-work/references/decision-history.md)로 관련 원문·후속 설계·현재 적용 범위를 확인한다. product-owner에는 관련 절·포인터·확정 선택/미정만 전달하고, 미해결 의미 충돌은 실제 응답 전 PRD/AC 확정·재사용 완료로 넘기지 않는다.

`Read("../references/requirements-dialogue.md")`의 공통 문답을 **core 초안·전체 PRD·기존 계획 재사용 전** 적용한다. 중요한 미정이 해소될 때까지 실제 답변과 후속 질문을 반복한다. 핵심 inline 분기는 오케스트레이터가 직접 수행하고 추가 인터뷰 에이전트를 호출하지 않는다. `waiting`/`stopped`이면 현재 단계에서 종료하여 확정 저장·phase 완료·후속 진행을 막는다. 읽기 전용 인계와 문서 저장 금지는 helper 등록도 없이 대화로만 대기한다.

## Iron Law: AC = Given-When-Then 강제

```
NO ACCEPTANCE CRITERIA WITHOUT EXECUTABLE SCENARIO
```

모든 수용 기준(AC)은 **반드시 Given-When-Then 형식**으로 작성한다. 자연어 서술만 있는 AC는 미통과.

이유:
- red-writer가 AC를 보고 실패 테스트를 작성해야 함
- G-W-T 변환 불가능한 AC = red-writer가 무엇을 테스트할지 모름 = RGR 사이클 진입 불가

위반 시 해당 분기의 `gwt_rewriter`로 재작성한다. 핵심 inline은 오케스트레이터, 전체 PRD는 product-owner이며 아래 공통 게이트의 분기 선택을 따른다.

**G-W-T 형식 재작성은 최대 1회 반복.** 중요한 미정의 문답 횟수 제한이 아니다.

## 기준선 준비

요구사항을 이해하기 전에 전체 테스트·빌드를 시작하지 않는다. 관련 소스·기존 테스트의 경로만 식별해 계획으로 넘긴다. 기준선 실행은 phase-implement Step 0.5에서 영향 범위를 확정한 뒤 수행한다. 같은 실행 증거의 재사용 규약은 `references/test-execution.md`를 따른다.

## 핵심 모드 분기 (core)

먼저 `Read("../references/document-lifecycle.md")`의 사전 대조를 확인한다. 관련 문서·FR/W 연결을 기존 계획에서 재사용하고 누락/변경만 보완한다. 조회·계획만 요청했으면 읽기만 한다. 아래 G-W-T 확정 후 검사 입력에 해당 AC/FR 연결만 보강하고, 구현 직전에 같은 run-id로 다시 검사한다. 문서 관측이나 helper의 ready 표시는 요구사항/승인을 대신하지 않는다.

현재 명시 `--phase requirements/design`은 저장 mode가 core여도 PRD를 만드는 전체 문서 경로다. design의 선행 PRD 보완에서도 현재 요청 design을 유지하며 mode를 all로 바꾸거나 implement/complete로 체이닝하지 않는다. 산출물 선택은 다음 정책을 따른다:

```python
use_inline_core = mode == "core" and requested_phase not in ("requirements", "design")
```

`use_inline_core`가 거짓이면 아래 core 작성·결합 승인 블록을 건너뛰고 전체 PRD 경로를 수행한다. PRD의 확정 변경이 기존 core AC·계획에 영향을 주면 해당 문서를 실제 변경하기 전에 core-plan-status를 pending·지문 null로 무효화한다. 문서 단독 실행에서 새 core 구현 승인까지 받지는 않는다. HANDOFF_READ_ONLY는 state를 쓰지 않고 차이만 보고한다.

유효한 계획·handoff의 G-W-T AC는 배경·수치·결정을 재인터뷰하지 않고 재사용한다. G-W-T는 점검하고 누락·변경만 확인한다. AC의 과거 승인만으로 아직 없는 plan.md의 결합 승인을 추정하지 않는다.

`use_inline_core`가 참이면 `Read("../references/core-planning.md")`를 수행하고 **오케스트레이터가 ac.md를 직접 작성한다** (product-owner 디스패치 없음):
- 재계획·구세션 재개이면 [core-replanning.md](../references/core-replanning.md)의 변경 전 검증·불변 이력 보관 후 기존 AC·ID·제외 기록을 복원한다. 승인 문서를 바꾸기 전에 승인을 무효화하며 기존 RED·테스트·보고·기준선과 baseline-fingerprint는 보존한다.
- ARGS[0] + 코드 맵 + DOMAIN_CONTEXT(있으면 — 미반영 항목과 겹치는 AC는 그 FR ID를 `FR-N (status.md 미반영)` 형식으로 인용한다)를 기반으로 `${PROJECT_ROOT}/${DEV_DIR}/ac.md`를 작성한다.
- 포함 섹션: `## 배경`(2~3줄) + `## 요구사항 (AC)` — **AC는 Given-When-Then 형식 강제** (core여도 RGR 사이클이 강제되므로. 위 Iron Law의 형식·예시를 그대로 따른다). 소형 작업의 AC는 보통 3~5개이며 필수 시나리오를 줄이는 상한이 아니다. 필요한 확정 정책·답변 근거·비차단 가정은 짧은 기존 문서 절에 포함한다.
- 긴급 버그 수정 요청이면 AC를 재현 조건 관점으로 구성한다 — AC-1은 재현 조건(Given 현재 상태 / When 트리거 / Then 잘못된 동작이 아닌 **기대 동작**), 필요 시 회귀 방지 AC 추가. 재현 조건 정보가 부족하면 추측하지 말고 사용자에게 확인한다.
- 저장 전에 **G-W-T 검증 게이트**(아래 섹션)를 정상 플로우와 동일하게 수행한다 (core에서도 RGR이 강제되므로 그 전제인 게이트도 유지).
- 게이트 통과 후 ac.md 초안을 저장하고 대상 코드·호출부·기존 테스트·설정을 실제 Read한다. 공통 템플릿으로 `${DEV_DIR}/plan.md`에 확인한 코드, 변경 파일·내용, 작업 순서·의존관계, AC별 검증 명령·기대결과, 영향 범위·가정과 자체 점검을 작성한다. 기본은 오케스트레이터이며 구현 위치/의존이 불명확할 때만 architect 1회다. design-critic·test-architect를 자동 추가하지 않는다.
- 계획에 AC·프로덕션 파일·테스트 파일과 focused 검증을 RGR 태스크로 연결한다. 같은 파일을 고치는 AC는 묶고 태스크 간 파일 중복을 없앤다. 새 구조·핵심 인터페이스·중요한 기술 선택이 필요하면 전체 모드 전환을 제안하고 실제 결정 전 구현하지 않는다. 실제 선택 후 공통 pending→applied 전이를 저장하고 `return "mode-transition"`으로 과거 core 루프를 끝낸다.
- 자체 점검 후 **ac.md와 plan.md 실물을 함께 전문 표시하고 결합 승인 1회**를 받는다. core-plan-status는 pending에서 시작하고 현재 raw bytes 결합지문과 실제 응답이 일치할 때만 approved·core-plan-approved-digest를 기록한다. 같은 문서 쌍의 유효한 승인은 재사용한다. AC 단독 승인·태스크 분해 승인을 추가하지 않는다.
- 공통 결합 질문에서 방법 미정이면 현재 세션/서브에이전트/계획 문서 종료를 함께 선택받는다. 초기 명시 방법은 보존하고 승인/수정 요청만 확인한다. 승인된 plan.md를 implementation-plan-file 및 단독 SHA-256·plan-approved-run/source/sha256에 연결하고 실제 방법 선택을 execution-method 기록과 연결한다. 원 gx-work 진입 승인·원문 포인터·run·종료점은 보존한다. implement 1.2~1.3은 같은 기록을 재사용하며 유효한 결합 승인 후 방법만 빠졌으면 방법만 보완한다.
- 수정 요청은 구체 내용을 후속 질문으로 묻고 실제 답변을 기다린다. Other에 직접 적은 수정 내용은 그 답변을 사용한다. AC 또는 계획 변경 전 승인 무효화 → G-W-T 재검증·계획 갱신·자체 점검 → 두 문서 재표시·결합 재승인 순서다. Codex는 core_plan_approval 질문 세트·표시 지문·실제 응답을 대조하고 answer 성공·pending 해제를 확인한다.
- 문서 종료·미응답·수정 요청은 실행 승인이 아니다. pending·미구현 상태를 유지하고 RED·complete로 체이닝하지 않는다. 계획 전용 인계는 요청된 내용만 제시하며 저장 요청 없이는 문서도 만들지 않는다.

핵심 모드가 아닌 경우 아래 전체 모드 플로우를 따른다.

---

**기존 계획 재사용 분기 (전체 모드)**: 검증된 `--from-plan`·`--handoff`가 있으면 [계획 인계 계약](../references/plan-handoff.md)으로 이번 범위의 G-W-T AC·제약·원문 포인터를 기존 PRD에 연결한다. 아래 G-W-T 게이트를 통과하고 실제 승인 근거가 있으면 이 Phase를 완료한다. 기존 PRD를 새로 작성하거나 전문 인터뷰·승인을 반복하지 않는다. 승인되지 않은 외부 계획이면 이번 범위만 최초 확인하고, 누락·변경이 있으면 그 항목만 product-owner에게 보완하도록 요청한다.

core→all 전환이면 기존 ac.md 전체·plan.md·승인된 AC 추가/삭제/수정 및 은퇴 내역을 PRD 입력으로 인계한다. 기존 AC ID별 매핑을 남기고 변경/삭제 요구가 빠지지 않게 한다. 전환 선택을 PRD 승인으로 쓰거나 기존 GREEN·테스트·RED 이력을 지우지 않는다. 전체 요구사항 게이트·실제 승인은 그대로 수행한다.

**Step 1**: 재사용할 유효 계획이 없으면 product-owner agent를 호출한다 (PRD 작성).
`Task(subagent_type="oh-my-gx:product-owner")` — prompt에 다음을 포함:
- 기능/버그 설명: ARGS[0]
- 코드 맵 (phase-setup에서 생성한 초기 맵)
- 프로젝트 타입, 디렉토리 구조
- 프로젝트 루트 경로
- 도메인 컨텍스트 (DOMAIN_CONTEXT가 있으면 4요소 전부 — 용어·README 핵심·미반영 항목·아키텍처). **미반영 항목과 겹치는 요구사항은 새 FR을 만들지 않고 그 FR ID를 인용**한다 (`FR-7 (status.md 미반영)` 형식으로 요구사항 제목 끝에 표기). README 성공 기준의 수치는 해당 AC의 Then에 검증값으로 반영한다
- "PRD 작성"으로 동작할 것
- 이전 Q&A 히스토리 (사용자 수정 요청이 있었으면: 이전 PRD 초안 + 사용자 답변)
- 공통 요구사항 문답 계약: 확정한 선택·근거, 현재 중요한 미정과 비차단 가정을 구분한다. 중요한 미정이 남으면 PRD 초안과 질문을 반환하고 임의 정책으로 확정하지 않는다. 후속 답변으로 새 미정이 생기면 이어 질문한다. 문답 종료 신호는 사용자 승인과 구분한다.
- **[Iron Law] 수용 기준(AC) 형식 강제**:
  ```
  모든 AC는 반드시 Given-When-Then 형식으로 작성하라:

  AC-N: <한 줄 요약>
    Given: <초기 상태/전제 조건>
    When: <발생하는 동작/이벤트>
    Then: <기대되는 결과/검증 가능한 산출물>

  예시 (올바름):
  AC-1: 잘못된 비밀번호로 로그인 시도 시 401 응답
    Given: 사용자가 등록되어 있고 비밀번호가 "correct"이다
    When: "wrong" 비밀번호로 POST /login을 호출한다
    Then: 401 응답이 반환되고 응답 body의 message가 "비밀번호 불일치"이다

  금지 (자연어 서술만):
  AC-1: 잘못된 비밀번호로 로그인하면 에러가 나와야 한다

  금지 (표현 속성 — 화면 요구사항일 때 특히 자주 나온다):
  AC-2: 에러가 빨간색으로 표시된다          ← 색·여백·폰트는 assert 대상이 아님
  AC-3: 모달이 부드럽게 나타난다             ← 비결정적
  AC-4: 폼이 보기 좋게 정렬된다              ← 검증 불가

  화면 요구사항은 "무엇이 보이고 무엇이 잠기는가"라는 동작으로 쓴다:
  AC-2: 한도 초과 입력 시 폼이 제출을 막는다
    Given: ChargeForm이 표시되어 있다
    When:  150,000원을 입력하고 제출한다
    Then:  "1회 충전 한도는 100,000원입니다"가 노출되고 제출 버튼이 비활성화되며
           제출 요청이 발생하지 않는다
  ```
- PRD 품질 자가 검증 3관점:
  1. **유저 경험 검증**: 이 정책대로 만들면 사용자가 자연스럽게 이해하고 행동할 수 있는가. 혼란을 겪을 수 있는 상태 전환, 빈 화면, 오류 상황이 정의되어 있는가.
  2. **해석 여지 제거**: 개발자·디자이너·PO가 같은 문서를 보고 다르게 해석할 여지가 없는가. "크게", "적절히" 같은 상대적 표현 대신 구체적 수치가 있는가.
  3. **엣지케이스 커버리지**: 빈 상태, 로딩, 에러, 수량/길이의 최솟값·최댓값이 정의되어 있는가. 암묵적으로 처리되는 케이스가 없는가.
- **AC 자가 검증 (G-W-T 형식 강제)**: 각 AC가 다음을 만족하는지 확인:
  - [ ] Given/When/Then 세 절이 모두 명시되어 있는가
  - [ ] Then 절이 자동 테스트로 검증 가능한 구체적 산출물(응답 코드, 필드 값, 호출 횟수 등)을 포함하는가
  - [ ] "올바르게", "적절히", "정상적으로" 같은 모호한 표현이 Then 절에 없는가

**Step 2**: Agent 출력(PRD + 질문)을 사용자에게 **전문 표시**한다. Q&A 여부와 무관하게 항상 전문을 표시한다 (사용자가 PRD를 검토할 수 있도록).

**Step 3**: Agent 출력에서 "탐색 추가 항목"을 파싱하여 코드 맵에 누적한다.

**Step 4**: 공통 문답 계약으로 중요한 미정과 비차단 가정을 분류하고 근거를 확인한다. 질문 문구의 유무만으로 해소를 판단하지 않는다.

**중요한 미정이 있으면** (출력 문구가 없어도 실제 목록을 대조):
- PRD를 사용자에게 출력한다.
- Agent 출력의 "확인이 필요한 사항"을 **에이전트 질문 → AskUserQuestion 변환 규칙** (SKILL.md 공유 규칙)에 따라 변환하여 사용자에게 순서대로 제시한다.
- 실제 답변을 기다리고 해소된 항목·근거만 반영한다. 새 모호성이 생기거나 중요한 미정이 남으면 기존 PRD 초안·답변·잔여 미정을 product-owner에게 전달하고 **Step 2~4를 다시 수행**한다. 고정 Q&A 횟수로 설계 진입을 허용하지 않는다. 비차단 항목만 남으면 그 이유/가정을 기록한다.
- 미응답·중단은 `waiting`/`stopped`로 phase 미완료를 유지한다. 실제 답변 뒤 필요한 후속 질문만 이어가며 이전 응답을 다시 묻지 않는다.

**중요한 미정이 없으면** (`ready`; 종료 문구는 승인 아님):
- **승인/수정 공통 패턴** (SKILL.md 공유 규칙)에 따라 AskUserQuestion을 사용한다:
  ```
  AskUserQuestion(
    questions: [{
      question: "PRD를 확인해주세요.",
      header: "산출물 확인",
      options: [
        { label: "승인", description: "설계 단계로 진행" },
        { label: "수정 요청", description: "별도 후속 질문에서 수정할 부분을 입력합니다" }
      ],
      multiSelect: false
    }]
  )
  ```
- 승인 → G-W-T 검증·확정 저장을 통과한 뒤 요청 범위의 다음 단계로 진행한다.
- 수정 요청 → 수정 선택 시 별도 후속 질문으로 수정할 부분을 묻고 실제 수정 답변을 기다린 뒤 수정 내용을 반영해 product-owner를 호출한다. 원 질문 UI Other에 직접 입력한 수정 답변은 별도 경로에서 사용한다. Step 2~4에서 새로운 중요한 미정을 재평가하고 G-W-T 게이트 재수행·재승인을 거친다.

## G-W-T 검증 게이트 (Phase 완료 전 필수)

산출물 저장 전에 오케스트레이터가 **AC 형식 검증**을 수행한다. 전체·핵심 모드 공통 게이트다.

### 검증 절차

현재 requirements 분기의 `use_inline_core`로 게이트 입력과 재작성 주체를 선택한다. 저장된 mode가 core여도 명시 requirements/design은 새 PRD를 검증한다.

```python
gwt_document = "ac.md" if use_inline_core else "prd.md"
gwt_rewriter = "orchestrator" if use_inline_core else "product-owner"
```

1. `gwt_document`에서 각 AC를 추출한다. `use_inline_core=True`는 ac.md의 "요구사항 (AC)" 섹션, False는 prd.md의 "수용 기준" 섹션을 파싱한다. 다른 문서의 과거 AC로 대신 검증하지 않는다.
2. 각 AC에 대해 다음을 확인:
   - `Given:`, `When:`, `Then:` 세 키워드가 모두 존재
   - Then 절에 구체적 검증값(코드, 필드, 숫자 등) 또는 자동 테스트 가능한 동작이 명시
   - 모호 표현(올바르게/적절히/정상적으로) 부재
   - **표현 속성 부재**: Then 절이 색상·여백·폰트·정렬·애니메이션 등 **시각적 표현**을 검증 대상으로 삼지 않는다. 이런 AC는 red-writer가 assert할 수단이 없어 스타일에 결합된 깨지기 쉬운 테스트를 만든다 (상세: `references/frontend-testing.md` §6, `references/testing-anti-patterns.md` Anti-Pattern 6). 화면 요구사항은 "무엇이 보이고 무엇이 잠기고 무엇이 발생하지 않는가"라는 동작으로 재작성한다. 디자인 요구사항 자체가 불필요하다는 뜻이 아니라, **AC가 아니라 디자인 스펙으로 분리**한다는 뜻이다 — 사용자에게 이 구분을 안내한다.
3. 위반 AC가 1건이라도 있으면 **GATE FAIL** → `gwt_rewriter`에 재작성을 요청한다. product-owner이면 아래 지시로 현재 PRD의 AC를 재작성하고, orchestrator이면 ac.md의 해당 AC를 직접 재작성한다 (`use_inline_core=True` 분기는 product-owner를 디스패치하지 않는다):
   ```
   [G-W-T 게이트 실패]
   다음 AC가 Given-When-Then 형식 또는 검증 가능성 기준을 만족하지 않습니다:
   - AC-{N}: {위반 사유}

   재작성하라:
   - Given/When/Then 세 절을 모두 명시
   - Then 절에 자동 테스트로 검증 가능한 구체적 산출물 포함
   - 시각적 표현(색·여백·정렬·애니메이션)이 아니라 관찰 가능한 동작으로 Then을 구성
     (무엇이 노출되는가 / 무엇이 잠기는가 / 무엇이 발생하지 않는가 / 어디로 이동하는가)
   ```
4. 모든 AC 통과 시 **GATE PASS** → Phase 완료 저장으로 진행.

### 위반 시 사용자 안내

게이트 실패가 `gwt_rewriter`의 재작성 1회로도 해결 안 되면 아래 질문의 `{gwt_document}`를 현재 선택한 문서명으로 치환한다:
```
AskUserQuestion(
  questions: [{
    question: "G-W-T 게이트 미통과 항목이 있습니다. 어떻게 진행할까요?",
    header: "게이트 처리",
    options: [
      { label: "직접 수정", description: "현재 검증 중인 {gwt_document}의 AC를 직접 G-W-T 형식으로 고침" },
      { label: "위험 수용", description: "해당 AC를 구현 대상에서 제외하고 {gwt_document}의 그 AC에 '(제외 — 위험 수용)' 표시 (테스트 없이 구현하는 것이 아님 — trust-ledger에 기록. 유일한 AC가 제외되면 구현 대상이 없으므로 파이프라인을 중단하고 보고)" },
      { label: "중단", description: "요구사항을 재정의" }
    ],
    multiSelect: false
  }]
)
```

`current-step`을 `"G-W-T 게이트"`로 갱신.

---

**Phase 완료 후 저장**:
공통 문답의 `ready`와 현재 산출물의 실제 승인 조건을 먼저 확인한다. 미해결 중요한 미정이나 응답 대기가 있으면 아래 저장/확정 보고를 수행하지 않는다. HANDOFF_READ_ONLY·문서 금지이면 기존 파일과 state를 보존하고 대화로만 전달한다. core는 위 ac.md·plan.md 결합 승인 경로에서 종료하므로 아래 PRD 저장을 실행하지 않는다.
1. `${PROJECT_ROOT}/${DEV_DIR}/` 디렉토리가 없으면 생성한다.
2. 확정된 PRD를 `${PROJECT_ROOT}/${DEV_DIR}/prd.md`에 Write한다.

**Phase 완료 보고 (요약 모드)**:
PRD 저장 후 사용자에게 **요약만** 출력한다 (Step 2에서 이미 전문을 표시했으므로 반복하지 않음):
```
PRD 확정: <제목>
- 핵심 요구사항: [Must] N건, [Should] N건, [Could] N건
- 수용 기준: N건
- 저장: ${DEV_DIR}/prd.md
```
이후 Phase에서 PRD가 필요하면 파일을 Read하여 Agent prompt에 포함한다.
