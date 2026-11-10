> gx-tdd/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태/질문/페이즈 결정을 추정하지 않는다. 상대경로는 이 파일의 위치를 기준으로 해석한다.

### 에이전트 질문 → AskUserQuestion 변환 규칙

Codex에서는 먼저 [질문 대기 계약](../../gx-work/references/codex-questions.md)을 적용한다. 질문의 필수 여부·도구 용도 제한·pending 등록·실제 답변 기록을 확인하고 아래 Claude 예시를 현재 스키마로 변환한다. 질문 UI의 등록 성공을 승인으로 취급하지 않는다.

에이전트(product-owner, architect, test-architect, reviewer, security-auditor)가 "확인이 필요한 사항"에 구조화된 질문을 출력하면, 오케스트레이터가 AskUserQuestion으로 변환하여 사용자에게 제시한다.

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

**유형: 자유입력** → 예상 답변 후보 2개를 options에 배치하고, 해당하지 않으면 "Other"로 직접 입력:
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

#### 변환 규칙

- **questions 배열 필수**: `questions: [{ ... }]`로 감싼다. `header`는 최대 12자, `multiSelect` 기본 false.
- **options 필수**: 2~3개. `{ label, description }` 구조, `value` 없음. UI Other는 별도 option이 아니다.
- **개방형 질문**: 후보 2개, 자유 입력은 UI Other. 후보가 없으면 자연어로 묻고 답변을 기다린다.
- **(권장)** option은 첫 번째에 놓고 label 끝에 `(Recommended)`를 붙인다.
- 에이전트 질문 **2개 이상**: 하나씩 순차 호출하며 앞선 답변을 반영한다. **의도 파싱 Step 3 모드·프로파일은 예외**로 동시 질문한다.
- 에이전트가 기술 용어를 사용한 경우 **비기술적 표현으로 의역**한다. 예: "JWT vs 세션" → "로그인 유지 방식".
- 복수 선택이 필요하면 `multiSelect: true`로 지정한다.

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
"수정 요청" 선택 시 후속 질문으로 수정 내용을 받고 답변을 기다린다. 원 질문 UI Other의 자유 입력은 바로 처리한다.

### 이전 질문 정리

새 작업이나 재개를 시작할 때 질문 helper `status`가 exit 2(미응답)이거나 `.dev/<slug>/pending-question.json`이 있으면, 그 질문의 목표·run·phase를 이번 요청과 대조한다.

- 같은 작업이면 원래 질문을 다시 보여 주고 실제 답을 원래 phase에 기록해 이어 간다.
- 다른 작업이면 새 질문으로 덮지 않고 `이전 질문에 답하기 (Recommended)` / `폐기하고 새 작업`을 묻는다. Claude Code는 AskUserQuestion을 쓴다. Codex는 pending이 있어 helper가 새 등록을 거부하므로 등록하지 않고 현재 도구나 자연어로 묻고, 질문을 담은 final 응답으로 턴을 끝내 실제 답을 기다린다.
  - **이전 질문에 답하기** → 원래 질문을 표시하고 그 답을 기록·해제한 뒤 원래 작업으로 돌아간다. 새 요청은 그다음에 다시 받는다.
  - **폐기하고 새 작업** → `python <플러그인 루트>/scripts/codex-question.py discard --cwd <PROJECT_ROOT> --dev-dir <질문의 .dev/slug> --reason "<실제 사용자 결정 근거>"`를 실행한다(POSIX는 `python3`, 플러그인 루트는 이 파일 기준 `../../../..`). exit 0이면 pending이 `discarded-question-<UTC 시각>.json`으로 보관되고 decisions.md에 기록된 것이므로 새 작업을 진행한다. exit 2(pending 없음·`.question-lock` 있음)면 멈추고 보고한다.
- 응답 없이 폐기하지 않는다. 시간 경과·새 요청 도착·추천 값은 폐기 결정이 아니며 pending 파일을 직접 지우거나 옮기지 않는다. 헤드리스는 BLOCKED와 질문을 기록하고 종료한다.

---

## 에러 처리

- Phase가 심각하게 실패하면 에러를 표시하고 사용자에게 진행 방법을 확인한다.
- 에러를 조용히 무시하지 않는다.
- 도구나 명령이 사용 불가하면 대안을 제안한다.
- 사용자가 중단하면 진행 상황을 저장하고 완료된 내용을 보고한다.
- phase-review의 ZT 통합 감사가 실패해도 QA 리뷰 결과만으로 진행한다. 감사 실패를 사용자에게 알린다.
- 2분 이상 소요될 수 있는 Bash 명령(`./gradlew test`, `npm test`, `npm install` 등)에는 `timeout: 300000`(5분, config.json `timeouts.build` 값)을 설정한다.
