> gx-cross-review의 advisor 결과를 받았을 때 읽는다. 역할에 출력 형식을 전달해야 하면 호출 전에 같은 파일을 읽는다. 변수·소비 프로젝트 경로는 SKILL.md를 따른다.

## Step 4: 결과 정규화 + 저장

advisor와 무관하게 동일한 포맷으로 정규화하여 `${RESULT_FILE}`에 저장한다.

### 4-1. 표준 포맷

```markdown
# Cross-Review 결과

- advisor: codex | native | claude
- 실행 하네스: Codex CLI | 현재 하네스 | Claude Code
- 실제 모델: 확인된 모델명 또는 미확인 (이벤트/도구 기록에 있을 때만 기재)
- 브랜치: ${BRANCH} (base: ${BASE_BRANCH})
- DEV_DIR: ${DEV_DIR}
- 실행 시각: 2026-05-04T10:30:00Z

## AC 충족 매트릭스

| AC | 충족 | 근거 |
|----|------|------|
| AC-1: 결제 한도 100→200만 변경 | O | PaymentService:42 |
| AC-2: 한도 초과 시 예외 발생 | X | 검증 로직 누락 |

[Must] 전체 N건 중 N건 충족, [Should] 전체 N건 중 N건 충족.

## 설계 범위 이탈

(없으면 "이탈 없음")

- 파일: PaymentController.kt
  - 변경 요약: ...
  - 이탈 사유: 설계서 변경 범위에 없음. 정당성 검토 필요.

## 신규 위험

(trust-ledger에 없는 항목만)

### Critical
- [RISK] PaymentService.kt:55 — 한도 초과 검증 누락
  - 근거: ...
  - 권고: ...

### Warning
- ...

### Info
- ...

## references 위반 (해당 시)

(섹션 자체를 생략 가능)

## 총평
- 강점: ...
- 합산: Critical N건, Warning N건, Info N건
- 권고: ...
```

### 4-2. 파일 저장

```bash
# RESULT_FILE에 정규화된 결과 작성
Write(${RESULT_FILE}, normalized_content)
```

`${RAW_FILE}`(advisor의 원시 응답)도 보존한다 — 사용자가 원본을 확인할 수 있도록.

### 4-3. 사용자 요약

전문은 표시하지 않는다. **요약만** 보고한다:

```
## Cross-Review 완료

- advisor: codex
- 실행 하네스/실제 모델: Codex CLI / 확인된 모델명 또는 미확인
- AC 충족: [Must] 4/5, [Should] 2/3
- 설계 범위 이탈: 1건
- 신규 위험: Critical 1, Warning 2, Info 3
- references 위반: 없음

전문: ${RESULT_FILE}     (= ${DEV_DIR}/cross-review.md)
원시 응답: ${RAW_FILE}    (= ${DEV_DIR}/cross-review.raw.md)
```

---
