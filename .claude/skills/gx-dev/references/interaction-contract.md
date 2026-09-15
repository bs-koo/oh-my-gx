> gx-dev/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태·질문·phase 결정을 추정하지 않는다. 상대경로는 이 파일의 위치를 기준으로 해석한다.

### 에이전트 질문 → AskUserQuestion 변환 규칙

에이전트(product-owner, architect, qa-manager, security-auditor)가 "확인이 필요한 사항"에 구조화된 질문을 출력하면, 오케스트레이터가 AskUserQuestion으로 변환하여 사용자에게 제시한다.

#### 변환 프로세스

1. 에이전트 출력에서 "확인이 필요한 사항" 섹션을 파싱한다.
2. "추가 확인 사항 없음"이 포함되면 질문 변환을 건너뛴다.
3. 각 질문의 `유형` 필드에 따라 변환한다:

**유형: 선택** → AskUserQuestion 선택형:
```
AskUserQuestion(
  questions: [{
    question: "질문 텍스트 (맥락이 있으면 질문에 포함)",
    header: "카테고리",
    options: [
      { label: "레이블", description: "설명" },
      { label: "레이블", description: "설명" }
    ],
    multiSelect: false
  }]
)
```

**유형: 자유입력** → 사용자가 "Other"(직접 입력)를 통해 자유 입력할 수 있도록 선택형으로 구성한다. 예상되는 답변 후보 2개를 options에 배치하고, 사용자가 해당하지 않으면 Other로 직접 입력한다:
```
AskUserQuestion(
  questions: [{
    question: "질문 텍스트 (맥락이 있으면 질문에 포함)",
    header: "카테고리",
    options: [
      { label: "예상 답변 A", description: "설명" },
      { label: "예상 답변 B", description: "설명" }
    ],
    multiSelect: false
  }]
)
```

#### AskUserQuestion 스키마 규칙

- **questions 배열 필수**: 최상위에 반드시 `questions: [{ ... }]` 배열로 감싼다. 질문은 한 번에 1~3개다.
- **header 필수**: 각 질문에 `header` (최대 12자)를 지정한다. 칩/태그로 표시된다.
- **options 필수**: 질문마다 선택지는 2~3개다. 각 옵션은 `{ label, description }` 구조. `value` 필드는 없다.
- **multiSelect 필수**: 기본 `false`. 에이전트가 "복수 선택 가능"으로 표시하면 `true`.
- **"Other" 자동 제공**: UI가 항상 "Other" 선택지를 자동 추가하며, Other를 누르면 자유 입력 창이 열린다.
- **자유 입력**: 예상 답변 후보 2개를 실제 선택지로 제시한다. 후보가 없다면 자연어로 개방형 질문을 묻고 실제 답변을 기다린다. UI Other가 제공되는 질문에서는 사용자가 그 자유 입력란을 사용한다. `"Other로 입력"`, `"직접 입력"`, `"답변 입력"`, `"주제 입력"` 같은 입력용 메타 라벨을 옵션으로 만들지 않는다.
- **preview (선택)**: 옵션에 `preview` 필드를 추가하면 마크다운 미리보기가 표시된다. 산출물 비교 시 유용하다.

#### 변환 규칙

- **(권장)** 표시가 있는 선택지는 options 배열의 첫 번째에 배치하고, label 끝에 `(Recommended)`를 추가한다.
- 질문이 **2개 이상**이면 순서대로 하나씩 AskUserQuestion을 호출한다. 이전 답변이 다음 질문의 맥락에 영향을 주는 경우 반영한다. (이 규칙은 에이전트 질문 변환에 적용된다 — **의도 파싱 Step 3의 모드·프로파일 동시 질문은 명시적 예외**로, 한 호출의 questions 배열에 2개를 담는다.)
- 에이전트가 기술 용어를 사용한 경우, 사용자에게 표시할 때 **비기술적 표현으로 의역**한다. 예: "JWT vs 세션" → "로그인 유지 방식".

#### 승인/수정 공통 패턴

산출물(PRD, 설계서, 구현 계획) 확인 시 공통으로 사용하는 AskUserQuestion 패턴:
```
AskUserQuestion(
  questions: [{
    question: "{산출물}을 확인해주세요.",
    header: "산출물 확인",
    options: [
      { label: "승인", description: "다음 단계로 진행" },
      { label: "수정 요청", description: "선택하면 후속 질문에서 수정할 사항을 묻습니다" }
    ],
    multiSelect: false
  }]
)
```
"수정 요청" 선택 시 후속 질문으로 수정 내용을 받고 실제 답변을 기다린다. 원 질문 UI Other에 입력한 내용은 바로 처리한다.

---

## 에러 처리

- Phase가 심각하게 실패하면 에러를 표시하고 사용자에게 진행 방법을 확인한다.
- 에러를 조용히 무시하지 않는다.
- 도구나 명령이 사용 불가하면 대안을 제안한다.
- 사용자가 중단하면 진행 상황을 저장하고 완료된 내용을 보고한다.
- phase-review의 ZT 통합 감사가 실패해도 QA 리뷰 결과만으로 진행한다. 감사 실패를 사용자에게 알린다.
- 2분 이상 소요될 수 있는 Bash 명령(`./gradlew test`, `npm test`, `npm install` 등)에는 `timeout: 300000`(5분, config.json `timeouts.build` 값)을 설정한다.
