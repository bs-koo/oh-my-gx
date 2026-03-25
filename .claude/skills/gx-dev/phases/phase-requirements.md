# phase-requirements: PRD Q&A 사이클

**사용자가 "승인"할 때까지 반복한다.** 반복 횟수 제한 없음.

## Hotfix 모드 분기

`--hotfix` 모드이면 경량 PRD를 작성한다:
- product-owner에게 "경량 PRD 작성"으로 동작할 것을 지시한다.
- 포함 섹션: 배경 + 요구사항 + 수용 기준만 (3관점 품질 검증, Q&A 생략).
- 작성 완료 후 사용자에게 전문 표시 + 승인 확인.
- 승인 → `${PROJECT_ROOT}/.dev/prd.md`에 저장 후 phase-implement로 진행.
- 수정 요청 → 1회 수정 후 저장.

hotfix가 아닌 경우 아래 정상 플로우를 따른다.

---

**Step 1**: product-owner agent를 호출한다 (PRD 작성).
`Task(subagent_type="product-owner")` — prompt에 다음을 포함:
- 기능/버그 설명: ARGS[0]
- 코드 맵 (phase-setup에서 생성한 초기 맵)
- 프로젝트 타입, 디렉토리 구조
- 프로젝트 루트 경로
- "PRD 작성"으로 동작할 것
- 이전 Q&A 히스토리 (사용자 수정 요청이 있었으면: 이전 PRD 초안 + 사용자 답변)
- PRD 품질 자가 검증 3관점:
  1. **유저 경험 검증**: 이 정책대로 만들면 사용자가 자연스럽게 이해하고 행동할 수 있는가. 혼란을 겪을 수 있는 상태 전환, 빈 화면, 오류 상황이 정의되어 있는가.
  2. **해석 여지 제거**: 개발자·디자이너·PO가 같은 문서를 보고 다르게 해석할 여지가 없는가. "크게", "적절히" 같은 상대적 표현 대신 구체적 수치가 있는가.
  3. **엣지케이스 커버리지**: 빈 상태, 로딩, 에러, 수량/길이의 최솟값·최댓값이 정의되어 있는가. 암묵적으로 처리되는 케이스가 없는가.

**Step 2**: Agent 출력(PRD + 질문)을 사용자에게 **전문 표시**한다. Q&A 여부와 무관하게 항상 전문을 표시한다 (사용자가 PRD를 검토할 수 있도록).

**Step 3**: Agent 출력에서 "탐색 추가 항목"을 파싱하여 코드 맵에 누적한다.

**Step 4**: 질문 여부를 확인한다.

**질문이 있으면** ("추가 확인 사항 없음"이 포함되지 않은 경우):
- PRD를 사용자에게 출력한다.
- Agent 출력의 "확인이 필요한 사항"을 **에이전트 질문 → AskUserQuestion 변환 규칙** (SKILL.md 공유 규칙)에 따라 변환하여 사용자에게 순서대로 제시한다.
- 사용자 답변을 반영하여 product-owner를 다시 호출 → Step 2로 돌아가 반복한다.

**질문이 없으면** ("추가 확인 사항 없음. PRD가 확정되었습니다."):
- **승인/수정 공통 패턴** (SKILL.md 공유 규칙)에 따라 AskUserQuestion을 사용한다:
  ```
  AskUserQuestion(
    question: "PRD를 확인해주세요.",
    options: [
      { value: "approve", label: "승인 — 설계 단계로 진행" },
      { value: "input", label: "직접 입력 — 수정사항을 직접 입력합니다" }
    ]
  )
  ```
- 승인 → phase-design으로 진행.
- 직접 입력 → 후속 AskUserQuestion(자유입력)으로 수정 내용을 받아 product-owner를 다시 호출 → Step 2로 돌아가 반복한다.

**Phase 완료 후 저장**:
1. `${PROJECT_ROOT}/.dev/` 디렉토리가 없으면 생성한다.
2. 확정된 PRD를 `${PROJECT_ROOT}/.dev/prd.md`에 Write한다.

**Phase 완료 보고 (요약 모드)**:
PRD 저장 후 사용자에게 **요약만** 출력한다 (Step 2에서 이미 전문을 표시했으므로 반복하지 않음):
```
PRD 확정: <제목>
- 핵심 요구사항: [Must] N건, [Should] N건, [Could] N건
- 수용 기준: N건
- 저장: .dev/prd.md
```
이후 Phase에서 PRD가 필요하면 파일을 Read하여 Agent prompt에 포함한다.
