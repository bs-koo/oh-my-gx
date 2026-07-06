# phase-requirements: PRD Q&A 사이클 (Given-When-Then 강제)

## Iron Law: AC = Given-When-Then 강제

```
NO ACCEPTANCE CRITERIA WITHOUT EXECUTABLE SCENARIO
```

모든 수용 기준(AC)은 **반드시 Given-When-Then 형식**으로 작성한다. 자연어 서술만 있는 AC는 미통과.

이유:
- red-writer가 AC를 보고 실패 테스트를 작성해야 함
- G-W-T 변환 불가능한 AC = red-writer가 무엇을 테스트할지 모름 = RGR 사이클 진입 불가

위반 시 즉시 product-owner 재호출.

**최대 1회 반복.**

## Hotfix 모드 분기

`--hotfix` 모드이면 경량 PRD를 작성한다:
- product-owner에게 "경량 PRD 작성"으로 동작할 것을 지시한다.
- 포함 섹션: 배경 + 요구사항 + 수용 기준만 (3관점 품질 검증, Q&A 생략).
- **단, AC는 Given-When-Then 형식 강제 유지** (hotfix여도 RGR 사이클이 강제되므로).
- 작성 완료 후 사용자에게 전문 표시 + 승인 확인.
- 저장 전에 **G-W-T 검증 게이트**(아래 섹션)를 정상 플로우와 동일하게 수행한다 (hotfix에서도 RGR이 강제되므로 그 전제인 게이트도 유지).
- 승인 + 게이트 통과 → `${PROJECT_ROOT}/${DEV_DIR}/prd.md`에 저장 후 phase-implement로 진행.
- 수정 요청 → 1회 수정 후 **G-W-T 게이트 재수행 + 재승인**을 거쳐 저장한다 (수정이 형식을 깨뜨릴 수 있으므로 게이트는 저장 전 불변식이다).

hotfix가 아닌 경우 아래 정상 플로우를 따른다.

---

**Step 1**: product-owner agent를 호출한다 (PRD 작성).
`Task(subagent_type="oh-my-gx:product-owner")` — prompt에 다음을 포함:
- 기능/버그 설명: ARGS[0]
- 코드 맵 (phase-setup에서 생성한 초기 맵)
- 프로젝트 타입, 디렉토리 구조
- 프로젝트 루트 경로
- "PRD 작성"으로 동작할 것
- 이전 Q&A 히스토리 (사용자 수정 요청이 있었으면: 이전 PRD 초안 + 사용자 답변)
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

**Step 4**: 질문 여부를 확인한다.

**질문이 있으면** ("추가 확인 사항 없음"이 포함되지 않은 경우):
- PRD를 사용자에게 출력한다.
- Agent 출력의 "확인이 필요한 사항"을 **에이전트 질문 → AskUserQuestion 변환 규칙** (SKILL.md 공유 규칙)에 따라 변환하여 사용자에게 순서대로 제시한다.
- 사용자 답변을 반영하여 product-owner를 1회 더 호출. 미해결 질문이 있으면 기록하고 phase-design으로 진행.

**질문이 없으면** ("추가 확인 사항 없음. PRD가 확정되었습니다."):
- **승인/수정 공통 패턴** (SKILL.md 공유 규칙)에 따라 AskUserQuestion을 사용한다:
  ```
  AskUserQuestion(
    questions: [{
      question: "PRD를 확인해주세요.",
      header: "산출물 확인",
      options: [
        { label: "승인", description: "설계 단계로 진행" },
        { label: "수정 요청", description: "Other로 이동해서 수정할 부분을 자연어로 입력해주세요" }
      ],
      multiSelect: false
    }]
  )
  ```
- 승인 → phase-design으로 진행.
- 수정 요청 → 후속 AskUserQuestion(자유입력)으로 수정 내용을 받아 product-owner를 1회 더 호출 후 phase-design으로 진행.

## G-W-T 검증 게이트 (Phase 완료 전 필수)

PRD 저장 전에 오케스트레이터가 **AC 형식 검증**을 수행한다.

### 검증 절차

1. PRD의 "수용 기준" 섹션을 파싱하여 각 AC를 추출한다.
2. 각 AC에 대해 다음을 확인:
   - `Given:`, `When:`, `Then:` 세 키워드가 모두 존재
   - Then 절에 구체적 검증값(코드, 필드, 숫자 등) 또는 자동 테스트 가능한 동작이 명시
   - 모호 표현(올바르게/적절히/정상적으로) 부재
3. 위반 AC가 1건이라도 있으면 **GATE FAIL** → product-owner 재호출:
   ```
   [G-W-T 게이트 실패]
   다음 AC가 Given-When-Then 형식 또는 검증 가능성 기준을 만족하지 않습니다:
   - AC-{N}: {위반 사유}

   재작성하라:
   - Given/When/Then 세 절을 모두 명시
   - Then 절에 자동 테스트로 검증 가능한 구체적 산출물 포함
   ```
4. 모든 AC 통과 시 **GATE PASS** → Phase 완료 저장으로 진행.

### 위반 시 사용자 안내

게이트 실패가 product-owner 재호출 1회로도 해결 안 되면:
```
AskUserQuestion(
  questions: [{
    question: "G-W-T 게이트 미통과 항목이 있습니다. 어떻게 진행할까요?",
    header: "게이트 처리",
    options: [
      { label: "직접 수정", description: "PRD를 직접 G-W-T 형식으로 고침" },
      { label: "위험 수용", description: "해당 AC를 구현 대상에서 제외하고 prd.md의 그 AC에 '(제외 — 위험 수용)' 표시 (테스트 없이 구현하는 것이 아님 — trust-ledger에 기록. 유일한 AC가 제외되면 구현 대상이 없으므로 파이프라인을 중단하고 보고)" },
      { label: "중단", description: "요구사항을 재정의" }
    ],
    multiSelect: false
  }]
)
```

`current-step`을 `"G-W-T 게이트"`로 갱신.

---

**Phase 완료 후 저장**:
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
