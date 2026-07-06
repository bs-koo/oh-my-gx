# phase-design: 설계 Q&A 사이클 (testability 평가 강제)

## Iron Law: testability ≥ 7

```
NO IMPLEMENTATION WITHOUT TESTABILITY SCORE >= 7
```

architect의 설계는 **test-architect의 testability 평가**를 통과해야 phase-implement로 진입할 수 있다.

- testability score 1-10 산정
- < 7: 강결합/전역 상태/static 의존 등으로 RGR 사이클이 동작 불가 → architect 재설계
- ≥ 7: 통과 → phase-implement 진입

이유: RGR 사이클의 red-writer는 격리된 단위 테스트를 작성해야 한다. testability가 낮으면 red-writer가 의존성을 격리할 수 없어 사이클이 멈춘다.

**최대 2회 반복.**

## 각 반복 (1~2회)

**Step 0**: `${PROJECT_ROOT}/${DEV_DIR}/prd.md`를 Read하여 확정된 PRD를 로드한다.

**Task**: architect agent를 호출한다 (설계).
`Task(subagent_type="oh-my-gx:architect")` — prompt에 다음을 포함:
- 확정된 PRD (Step 0에서 로드)
- 코드 맵 (누적된 상태)
- 프로젝트 타입, 디렉토리 구조, 컨벤션 (phase-setup에서 수집한 정보)
- 프로젝트 루트 경로 (agent가 코드 탐색 시 사용)
- 코드 맵의 핵심 파일에서 기존 구현 패턴(레이어 구조, 네이밍, 에러 처리 방식 등)을 파악하고, 새 설계가 기존 패턴과 일관되도록 할 것
- "설계"로 동작할 것
- 이전 Q&A 히스토리 (이전 반복의 답변, 있으면)
- REFERENCES (있으면): "아래 외부 규격/표준을 설계에 반영하라. 관련 규격이 있으면 Read하여 준수 여부를 확인하고, 설계서에 '준수 규격' 섹션을 추가하라." + REFERENCES 테이블
- 반복 2회차면: 이전 설계 초안 + 사용자의 수정 요청 또는 답변

## Task 완료 후

**Step 1**: architect 출력(설계 초안 + 질문)을 사용자에게 **전문 표시**한다. Q&A 여부와 무관하게 항상 전문을 표시한다 (사용자가 설계를 검토할 수 있도록).

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

    [절대 규칙]
    1. 각 컴포넌트별 테스트 전략 명시 (단위/통합 + 모의 전략)
    2. testability score 1-10 산정
    3. score < 7이면 재설계 권고 (사유와 권고 명시)

    [출력 형식]
    ## Testability 평가

    ### 컴포넌트별 테스트 전략
    #### {컴포넌트 X}
    - 단위 테스트: {방법}
    - 통합 테스트: {방법}
    - 모의 대상: {외부 의존성}
    - 격리 전략: {DI/Mock/Stub/InMemory 등}
    - AC 매핑: AC-N, AC-M

    ### Testability Score: {N}/10

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
     - "권고대로 직접 수정 후 진행"
     - "위험 수용 (RGR 사이클이 일부 컴포넌트에서 실패할 수 있음)"
     - "중단 (요구사항 재정의)"

**Iron Law 위반 감지**: testability score < 7 상태에서 phase-implement로 진입하려는 시도가 감지되면 즉시 중단.

`current-step`을 `"design-critic + test-architect (병렬)"`로 갱신.

**Step 4**: 질문 여부를 확인한다.

**질문이 있으면** ("추가 확인 사항 없음"이 포함되지 않은 경우):
- 설계 초안을 사용자에게 출력한다.
- Agent 출력의 "확인이 필요한 사항"을 **에이전트 질문 → AskUserQuestion 변환 규칙** (SKILL.md 공유 규칙)에 따라 변환하여 사용자에게 순서대로 제시한다.
- 사용자 답변을 수렴하여 다음 반복으로 전달.

**질문이 없으면** ("추가 확인 사항 없음. 설계가 완료되었습니다."):
- **승인/수정 공통 패턴** (SKILL.md 공유 규칙)에 따라 AskUserQuestion을 사용한다:
  ```
  AskUserQuestion(
    questions: [{
      question: "설계를 확인해주세요.",
      header: "산출물 확인",
      options: [
        { label: "승인", description: "구현 단계로 진행" },
        { label: "수정 요청", description: "Other로 이동해서 수정할 부분을 자연어로 입력해주세요" }
      ],
      multiSelect: false
    }]
  )
  ```
- 승인 → phase-implement로 진행.
- 수정 요청 → 후속 AskUserQuestion(자유입력)으로 수정 내용을 받아 다음 반복 진행.

**2회 반복 후**: 최신 설계로 phase-implement를 진행한다. 미해결 질문이 있으면 기록한다.

**Phase 완료 후 저장**:
1. 확정된 설계 문서를 `${PROJECT_ROOT}/${DEV_DIR}/design.md`에 Write한다.
2. **test-architect 평가 결과를 설계서에 병합**: 설계서 끝에 `## Testability 평가 (test-architect)` 섹션을 추가한다. red-writer가 이 섹션을 참조하여 격리 전략을 결정한다.

**Phase 완료 보고 (요약 모드)**:
설계서 저장 후 사용자에게 **요약만** 출력한다 (Step 1에서 이미 전문을 표시했으므로 반복하지 않음):
```
설계 확정: <제목>
- 변경 범위: N개 파일 (신규 N, 수정 N)
- 구현 순서: N단계
- Testability score: N/10 ✅ (test-architect 평가)
- 저장: ${DEV_DIR}/design.md
```
이후 Phase에서 설계서가 필요하면 파일을 Read하여 Agent prompt에 포함한다.
