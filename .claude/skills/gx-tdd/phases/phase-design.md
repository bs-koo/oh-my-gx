# phase-design: 설계 Q&A 사이클 (testability 평가 강제)

승인된 설계를 재사용하기 전에도 새 안이 이전 팀 판단을 바꿀 수 있으면 [공유 결정 이력 대조](../../gx-work/references/decision-history.md)로 관련 원문·후속 설계·현재 적용 범위를 확인한다. architect에는 관련 절·포인터·확정 선택/미정만 전달하고, 미해결 의미 충돌은 실제 응답 전 설계 확정·재사용 완료로 넘기지 않는다.

`Read("../references/requirements-dialogue.md")`로 **재사용·단독 진입 전** 현재 요청의 중요한 미정을 확인한다. 제품 미정이 남으면 필요한 requirements 문답으로 돌아가 `waiting`으로 대기하며 설계 확정·구현을 진행하지 않는다. 응답 후 요청 phase·원 커서·종료점을 보존하여 필요한 문서/승인만 보완한다. 읽기 전용이면 질문도 대화로만 처리한다.

## 승인된 설계 재사용

계획 검토와 인계는 [판단과 검증 전달](../../gx-work/references/reviewability.md)을 따른다. 동작·범위·데이터 보존에 영향을 주는 선택의 이유·핵심 가정·반증 조건·원문 근거만 기존 설계/decisions/Trust Ledger에 남기며, 내부 선택을 전부 재승인받거나 새 문서를 의무화하지 않는다.

검증된 `--from-plan`·`--handoff`에 연결된 기존 설계가 있고 이번 범위·공개 인터페이스·제약과 실제 승인 근거가 유효하면 먼저 재사용한다. [계획 인계 계약](../references/plan-handoff.md)에 따라 원문 위치와 변경점만 확인하고, 전체 설계를 다시 작성·출력·덮어쓰거나 같은 승인을 반복하지 않는다.

G-W-T·testability 검증은 유지한다. 기존 testability 섹션·점수가 현재 컴포넌트와 일치하고 기준을 충족하면 그 근거를 연결한다. 누락·변경된 컴포넌트만 test-architect로 보완한다. 새 기술 결정이나 동작 범위가 바뀌면 그 변경만 설계·확인한다. 모든 조건이 충족되면 이 Phase를 완료하고 다음으로 진행한다. 재사용 조건이 충족되지 않는 경우 아래 작성 절차를 수행한다.

## Iron Law: testability ≥ 7

```
NO IMPLEMENTATION WITHOUT TESTABILITY SCORE >= 7
```

architect의 설계는 **test-architect의 testability 평가**를 통과해야 phase-implement로 진입할 수 있다.

- testability score 1-10 산정
- < 7: 강결합/전역 상태/static 의존 등으로 RGR 사이클이 동작 불가 → architect 재설계
- ≥ 7: 통과 → phase-implement 진입

이유: RGR 사이클의 red-writer는 격리된 단위 테스트를 작성해야 한다. testability가 낮으면 red-writer가 의존성을 격리할 수 없어 사이클이 멈춘다.

**설계 검토·재설계는 최대 2회 반복.** 중요한 미정의 문답 종료 조건과 구분한다.

## 각 반복 (1~2회)

**승인 대기 초안 재개**: `${DEV_DIR}/design.draft.md`가 있고 `current-step`이 `설계 승인 대기`이면 architect·design-critic·test-architect를 다시 부르지 않는다. 그 초안(소형이면 함께 저장한 `implementation-plan.md` 요약 포함)을 다시 보여 Step 4의 확인 질문만 다시 한다. 초안의 `## 확인이 필요한 사항 (승인 전)` 절에서 답변 표시가 없는 항목만 다시 묻고, 답한 항목은 `${DEV_DIR}/decisions.md`의 답을 Step 4의 답으로 이어 쓴다. prd.md가 초안보다 나중에 바뀌었으면 초안을 버리고 Step 0부터 새로 한다.

**Step 0**: `${PROJECT_ROOT}/${DEV_DIR}/prd.md`를 Read하여 확정된 PRD를 로드한다.

**환경 준비 병행**: 기준선(phase-implement Step 0.5)에 필요한 환경이 빠져 있으면(예: config `artifacts`의 `node_modules/` 부재, 프로젝트 문서에 적힌 테스트 DB 미기동) architect 디스패치와 함께 그 준비만 백그라운드로 시작한다. lock 파일 기준 의존성 설치나 프로젝트에 문서화된 준비 스크립트만 쓰고 테스트·빌드는 시작하지 않는다. 시작한 명령과 로그 경로를 execution-log에 남긴다. 백그라운드 실행을 지원하지 않는 하네스는 시작하지 않고 Step 0.5에서 준비한다.

`FRONTEND_TESTING_PATH`를 확정한다: 이 phase 파일이 위치한 gx-tdd 스킬 디렉토리 기준 `references/frontend-testing.md`의 절대 경로 (플러그인 설치 환경에서는 플러그인 베이스 경로 하위 — 소비 프로젝트 루트가 아니다). PRD·설계서에 UI 컴포넌트가 포함될 때 test-architect 프롬프트에 이 경로를 전달한다.

**Task**: architect agent를 호출한다 (설계).
`Task(subagent_type="oh-my-gx:architect")` — prompt에 다음을 포함:
- 확정된 PRD (Step 0에서 로드)
- 코드 맵 (누적된 상태)
- 프로젝트 타입, 디렉토리 구조, 컨벤션 (phase-setup에서 수집한 정보)
- 프로젝트 루트 경로 (agent가 코드 탐색 시 사용)
- 도메인 컨텍스트 (DOMAIN_CONTEXT가 있으면 용어·아키텍처만): 기존 용어를 그대로 쓰고, `architecture.md`의 레이어·의존 규칙과 다른 설계는 "의존성 및 영향도" 절 안에 "기존 구조와의 차이" 소제목으로 명시할 것 (architect 출력 포맷에 새 절을 만들지 않는다)
- 코드 맵의 핵심 파일에서 기존 구현 패턴(레이어 구조, 네이밍, 에러 처리 방식 등)을 파악하고, 새 설계가 기존 패턴과 일관되도록 할 것
- "설계"로 동작할 것
- 이전 Q&A 히스토리 (이전 반복의 답변, 있으면)
- REFERENCES (있으면): "아래 외부 규격/표준을 설계에 반영하라. 관련 규격이 있으면 Read하여 준수 여부를 확인하고, 설계서에 '준수 규격' 섹션을 추가하라." + REFERENCES 테이블
- 반복 2회차면: 이전 설계 초안 + 사용자의 수정 요청 또는 답변

## Task 완료 후

**Step 1**: architect 출력(설계 초안 + 질문)을 사용자에게 **전문 표시**한다. Q&A 여부와 무관하게 항상 전문을 표시한다 (사용자가 설계를 검토할 수 있도록). 표시하는 즉시 설계 초안을 `${DEV_DIR}/design.draft.md`에 저장한다(반복마다 덮어쓴다). 승인을 기다리다 세션이 끊겨도 같은 초안으로 다시 묻기 위해서다.

**Step 2**: architect 출력에서 "탐색 추가 항목"을 파싱하여 코드 맵에 누적한다.

**Step 3**: 설계 비판 검토 + testability 평가 (조건부 병렬).

**호출 분기 규칙**:
- architect 출력의 "설계 규모" 필드를 확인한다 (소형/중형/대형).
- **소형**: test-architect 단독 호출 (design-critic은 작은 설계에 과잉).
- **중형/대형**: design-critic + test-architect **병렬** 호출 (하나의 메시지에서 동시 Task 발행).

두 에이전트 모두 architect 설계 초안만 참조하므로 병렬 격리 안전. test-architect는 모든 규모에서 항상 수행 (testability 게이트는 Iron Law).

**Step 3-A**: design-critic (조건부 — 중형/대형만).

`Task(subagent_type="oh-my-gx:design-critic")` — prompt에 다음을 포함:
- architect의 설계 초안 (Step 1에서 받은 출력)
- PRD (Step 0에서 로드)
- 코드 맵 (누적된 상태)
- 프로젝트 루트 경로
- "설계 비판 검토"로 동작할 것

**Step 3-B**: test-architect (필수, 항상 호출).

```
Task(subagent_type="oh-my-gx:test-architect"):
  description: "Testability evaluation"
  prompt: |
    당신은 testability 평가 전담자입니다.

    [입력]
    - 설계서 초안: {Step 1 architect 출력}
    - PRD의 수용 기준: {Step 0 PRD의 "수용 기준" 섹션}
    - 코드 맵: {누적 코드 맵}
    - 프로젝트 루트: {PROJECT_ROOT}
    - 프론트 테스트 규약 (UI 컴포넌트가 있을 때만): {FRONTEND_TESTING_PATH} — Read하여 레이어 분류(§2)와 셀렉터 규약(§4)의 근거로 사용

    [절대 규칙]
    1. 각 컴포넌트별 테스트 전략 명시 (단위/통합 + 모의 전략)
    2. **레이어 분류**: 각 컴포넌트를 `동작`(검증 대상) 또는 `표현`(검증 대상 아님)으로 분류한다.
       - 동작: 로직·상태·분기·계약이 있는 것 (서비스, 컴포저블/훅, 스토어, 가드, 폼 검증, 조건부 렌더)
       - 표현: 스타일 래퍼·아이콘·배지처럼 assert할 동작이 없는 것
       - 표현 레이어는 **감점 사유가 아니라 범위 밖**이다. 억지로 테스트 전략을 배정하면 스타일에 결합된
         깨지기 쉬운 테스트가 나오고, 그게 팀이 테스트를 지우게 되는 경로다.
    3. **테스트 러너 확인**: 각 동작 컴포넌트에 대해 프로젝트에 실행 가능한 러너가 있는지 확인한다
       (백엔드: JUnit/pytest 등, 프론트: vitest/jest 등). 러너가 없는 레이어는 전략에
       `러너: 없음 — 하네스 필요`로 명시한다. phase-implement의 레이어별 하네스 게이트가 이 값을 읽는다.
    4. testability score 1-10 산정 — **동작 컴포넌트만 대상**으로 한다
    5. score < 7이면 재설계 권고 (사유와 권고 명시)

    [출력 형식]
    ## Testability 평가

    ### 컴포넌트별 테스트 전략
    #### {컴포넌트 X}
    - 레이어: 동작 | 표현
    - 러너: {테스트 명령 또는 "없음 — 하네스 필요"}
    - 단위 테스트: {방법}
    - 통합 테스트: {방법}
    - 모의 대상: {외부 의존성}
    - 격리 전략: {DI/Mock/Stub/InMemory 등}
    - AC 매핑: AC-N, AC-M

    (표현 레이어는 위 항목 대신 한 줄로: `- 레이어: 표현 — 검증 대상 아님 (사유: {스타일 래퍼 등})`)

    ### Testability Score: {N}/10  (동작 컴포넌트 기준)

    ### 판정
    - ≥ 7 → ✅ TESTABILITY PASS
    - < 7 → ❌ TESTABILITY FAIL
      - 사유: {강결합/전역 상태/static 의존 등}
      - 권고: {DI 도입/인터페이스 추출/책임 분리 등}
```

**Step 3-C**: 결과 처리.

design-critic 출력에서 "탐색 추가 항목"이 있으면 코드 맵에 누적한다. test-architect도 동일.

design-critic 결과 처리:
- **MUST-ADDRESS 항목이 있으면**: 사용자에게 design-critic 결과를 표시하고, MUST-ADDRESS 항목을 다음 architect 반복의 피드백으로 전달한다.
- **CONSIDER만 있으면**: 사용자에게 요약만 표시. 설계 반복에 피드백으로 전달하지 않는다.
- **근본 문제 없음**: 한 줄로 알린다.

**test-architect 결과 처리 (Iron Law 게이트)**:
- **✅ TESTABILITY PASS (score ≥ 7)**: testability 섹션을 설계서에 병합하여 phase-implement에서 red-writer가 참조할 수 있도록 한다.
- **❌ TESTABILITY FAIL (score < 7)**:
  1. test-architect의 사유와 권고를 사용자에게 표시
  2. 권고를 architect 다음 반복의 피드백으로 전달 (MUST-ADDRESS 처리와 동일)
  3. 반복 카운트에 포함됨 (최대 2회 반복 내에서)
  4. 2회 반복 후에도 score < 7이면 → 사용자에게 보고 + AskUserQuestion:
     - "권고를 반영해 설계 보완 (점수 재평가·승인 전 구현 보류)"
     - "중단 (요구사항 재정의)"

**Iron Law 위반 감지**: testability score < 7 상태에서 phase-implement로 진입하려는 시도가 감지되면 즉시 중단.

`current-step`을 `"design-critic + test-architect (병렬)"`로 갱신.

**Step 4**: 현재 실제 질문 목록과 중요한 미정을 대조한다. 종료 문구만으로 질문이 없다고 판단하지 않는다. 제품 미정은 공통 requirements 문답, 중요한 기술 미정은 기존 설계 질문으로 해소하며 비차단 가정은 근거와 구분한다. 설계 확인 질문 직전에 testability 평가를 초안 파일 끝에 `## Testability 평가 (test-architect)` 섹션으로 덧붙이고 `current-step`을 `"설계 승인 대기"`로 갱신한다. 이번에 물을 질문 목록(Agent 출력의 "확인이 필요한 사항"과 검토에서 나온 결정 질문)도 그 뒤에 `## 확인이 필요한 사항 (승인 전)` 절로 덧붙인다. 일부 답을 받으면 답은 `${DEV_DIR}/decisions.md`(질문 기록 훅의 기록, 자연어 답은 직접 기록)에 있으므로 해당 항목 끝에 `→ 답변: decisions.md`를 붙여 다시 저장한다. 질문 본문의 설계 요약은 몇 줄로 짧게 둔다(전문은 Step 1에서 보였다).

**실제 필수 질문이나 중요한 미정이 있으면**:
- 설계 초안 전문은 Step 1에서 보였으므로 다시 출력하지 않고 질문에 필요한 부분만 짧게 인용한다.
- Agent 출력의 "확인이 필요한 사항"을 **에이전트 질문 → AskUserQuestion 변환 규칙** (SKILL.md 공유 규칙)에 따라 변환하여 사용자에게 제시한다. 초안이 가정값을 밝힌 서로 독립인 결정 질문은 아래 설계 확인 질문과 **한 호출로 묶는다**(하네스 질문 수 한도 안에서. 넘치면 결정 질문을 먼저 묻는다). 각 결정 질문의 첫 선택지는 초안의 가정값이다. 모든 결정에서 가정값을 고르고 설계를 승인하면 그 응답으로 확정한다. 승인 게이트는 없애지 않는다.
- 가정과 다른 답이 있거나 묶지 못한 질문의 답은 수렴하여 다음 반복으로 전달하고, 승인은 갱신된 설계에서 다시 받는다.

**실제 필수 질문과 중요한 미정이 없으면** (`ready`; 종료 문구는 승인 아님):
- **승인/수정 공통 패턴** (SKILL.md 공유 규칙)에 따라 AskUserQuestion을 사용한다:
  ```
  AskUserQuestion(
    questions: [{
      question: "설계를 확인해주세요.",
      header: "산출물 확인",
      options: [
        { label: "승인", description: "설계를 확정하고 요청 범위의 다음 단계로 진행" },
        { label: "수정 요청", description: "별도 후속 질문에서 수정할 부분을 입력합니다" }
      ],
      multiSelect: false
    }]
  )
  ```
- **소형 설계의 계획·실행 방법 묶음**: "설계 규모"가 소형이고 요청 범위에 implement가 있으면, 확인 질문 전에 phase-implement Step 1~1.1의 분해 규칙으로 T계획을 만들어 `${DEV_DIR}/implementation-plan.md`에 저장하고 `implementation-plan-file`·`implementation-plan-sha256`을 기록한다. 질문 본문에 태스크 요약(태스크·수용 기준·순서 몇 줄)을 붙이고, 위 2선택 대신 [core-planning §3의 결합 승인](../references/core-planning.md) 방식으로 phase-implement 1.2의 세 선택지와 추천 기준을 쓴다. 질문은 "설계와 구현 계획을 함께 확인해주세요. 어떤 방식으로 구현할까요? 수정할 사항은 직접 입력해주세요."다. 응답 뒤 계획 해시가 표시 때와 같을 때만 현재 세션/서브에이전트 응답을 설계 승인이자 `plan-approved-*`·`execution-method-*`(출처: 이 설계 확인 응답) 기록으로 쓴다. 계획 문서로 종료는 설계를 확정 저장한 뒤 phase-implement Step 1.3의 같은 항목대로 끝낸다. 직접 입력한 수정은 아래 수정 요청과 같다. 태스크가 8개를 넘거나 중형·대형이면 묶지 않고 implement의 태스크 수 가드·1.2를 따로 거친다. Codex stable id는 `design_approval`을 그대로 쓴다.
- 승인 → 중요 미정·testability 게이트를 충족한 뒤 현재 요청 범위의 다음 단계로 진행한다. 명시 `--phase design`은 설계 결과로 종료한다.
- 수정 요청 → 수정 선택 시 별도 후속 질문으로 수정할 부분을 묻고 실제 수정 답변을 기다린 뒤 수정 내용을 반영해 다음 반복으로 진행한다. 원 질문 UI Other에 직접 입력한 수정 답변은 별도 경로에서 사용한다.

**2회 반복 후**: 검토 상한은 진행 허가가 아니다. 상한 뒤 사용자가 미정에 답하거나 "설계 보완"을 고르면 그 응답이 추가 반복 1회(architect 갱신 → design-critic·test-architect 재평가)를 승인한다. 그 뒤에도 남으면 같은 방식으로 다시 묻는다. 중요한 제품 미정은 공통 requirements 문답으로 해소하고, 중요한 기술 설계 미정은 실제 질문·응답으로 해소할 때까지 `waiting`으로 대기한다. testability·기존 설계 승인 조건도 충족해야 요청 범위의 다음 단계로 진행한다. 비차단 가정만 근거와 함께 남길 수 있으며 문서 전용 요청을 구현으로 넓히지 않는다.

**Phase 완료 후 저장**:
현재 중요한 미정·미응답이 없고 기존 설계 승인이 유효한지 먼저 확인한다. 대기 중에는 확정 저장/완료 보고를 하지 않으며 기존 실행·이력을 보존한다.
1. 승인된 초안(`design.draft.md`)을 `## 확인이 필요한 사항 (승인 전)` 절을 빼고 `${PROJECT_ROOT}/${DEV_DIR}/design.md`로 옮겨 Write하고 초안 파일은 지운다.
2. **test-architect 평가 결과를 설계서에 병합**: 설계서 끝에 `## Testability 평가 (test-architect)` 섹션이 있는지 확인하고 없으면 추가한다. red-writer가 이 섹션을 참조하여 격리 전략을 결정한다.

**Phase 완료 보고 (요약 모드)**:
설계서 저장 후 사용자에게 **요약만** 출력한다 (Step 1에서 이미 전문을 표시했으므로 반복하지 않음):
```
설계 확정: <제목>
- 변경 범위: N개 파일 (신규 N, 수정 N)
- 구현 순서: N단계
- 테스트 가능성 점수(testability): N/10 ✅
- 저장: ${DEV_DIR}/design.md
```
이후 Phase에서 설계서가 필요하면 파일을 Read하여 Agent prompt에 포함한다.
