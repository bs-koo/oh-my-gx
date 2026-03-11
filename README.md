<div align="center">

# oh-my-gx

**요청 한 줄이면 PRD부터 커밋/PR까지, AI 에이전트 팀이 전체 개발 사이클을 수행합니다.**

</div>

---

## 30초 시작

```bash
# 1. 설치
/plugin marketplace add bs-koo/oh-my-gx
/plugin install oh-my-gx@oh-my-gx

# 2. 초기 설정 (환경 구성)
/oh-my-gx:setup

# 3. 첫 작업 시작
/oh-my-gx:dev 상품 목록 정렬 기능 추가
```

---

## 핵심 워크플로우

3개 명령으로 전체 개발 플로우가 완성됩니다.

```
/context → 도메인 지식 등록
/lens    → 현행 분석 + 영향도 파악
/dev     → PRD → 설계 → 구현 → 리뷰 → 커밋/PR
```

| 하고 싶은 말 | 실행되는 기능 | 예시 |
|-------------|-------------|------|
| 기능 추가/수정 | `/dev` 전체 사이클 | "주문 취소 기능 추가" |
| 긴급 수정 | `/dev` hotfix 모드 | "결제 오류 긴급 수정해줘" |
| PRD만 작성 | `/dev` requirements | "PRD만 작성해줘" |
| 이어서/계속 | `/dev` 재개 | "아까 하던 작업 이어서 해줘" |
| 진행 상태 | `/dev` 상태 확인 | "지금 어디까지 됐어?" |
| 도메인 등록 | `/context` | "결제 도메인 등록해줘" |
| 정책 분석 | `/lens` | "구매 한도 정리해줘" |

---

## 이럴 때 이렇게 쓰세요

### 새 프로젝트에 투입되었을 때

```bash
# 1. 도메인 지식부터 등록 (코드베이스를 스캔해서 자동 생성)
/oh-my-gx:context

# 2. 기존 비즈니스 정책 파악
/oh-my-gx:lens 할인 정책 정리해줘

# 3. 기능 개발 시작
/oh-my-gx:dev 쿠폰 적용 기능 추가
```

### 기획서를 받아서 개발할 때

```bash
# 1. 기획서를 context에 등록
/oh-my-gx:context 주문 --from requirements/주문-기획서.md

# 2. 기획서 기반으로 개발 요청
/oh-my-gx:dev 주문 취소 기능 추가
# → AI가 context에 등록된 기획서를 참조하여 PRD 작성 → 설계 → 구현 → PR
```

### 운영 중 긴급 버그가 발생했을 때

```bash
/oh-my-gx:dev 결제 금액 소수점 절삭 오류 긴급 수정해줘
# → hotfix 모드: 설계/리뷰 생략, 바로 구현 → 커밋 → PR
```

### 정책 변경의 영향을 먼저 확인하고 싶을 때

```bash
/oh-my-gx:lens 구매 한도 --idea "한도를 100만원으로 올리면?"
# → 코드를 수정하지 않고 영향 범위만 분석하여 보고
```

### 코드는 직접 짰고, 커밋/PR만 자동화하고 싶을 때

```bash
/oh-my-gx:commit                # 변경사항 분석 → 한국어 커밋 메시지 생성 → 커밋
/oh-my-gx:pull-request          # 커밋 히스토리 분석 → PR 제목/본문 생성 → PR
```

---

## 어떻게 작동하나요?

```
자연어 입력 → 의도 파악 → Q&A 인터뷰 → 단계별 실행 → 결과 보고
```

| 단계 | 담당 | 하는 일 |
|------|------|---------|
| 의도 파악 | 오케스트레이터 | 자연어에서 모드/스킬 자동 판정 |
| 인터뷰 | PO(제품책임자) | 요구사항 구체화 질문 |
| 설계 | 설계자 | 기술 설계 + 사용자 승인 |
| 구현 | 개발자 | 코드 작성 + 자기점검 |
| 리뷰 | 리뷰어 | 코드 리뷰 + 보안 감사 |
| 완료 | 오케스트레이터 | 인수 검증 + 커밋/PR |

---

## `/context` — 도메인 지식 관리

도메인의 용어, 아키텍처, 프로젝트 매핑을 등록하면 `/dev` 시 자동 참조합니다.

```bash
/oh-my-gx:context                              # 코드베이스 스캔으로 자동 생성
/oh-my-gx:context 결제                          # Q&A 기반 새 도메인 추가
/oh-my-gx:context 정산 --from docs/정산-요구사항.md  # 문서 기반 생성 (검증 Q&A 포함)
/oh-my-gx:context 결제 --sync                   # git 히스토리 기반 진행도 동기화
```

## `/lens` — 비즈니스 정책 분석

코드에서 비즈니스 정책을 탐지하고 영향도를 분석합니다. 코드를 수정하지 않습니다.

```bash
/oh-my-gx:lens 구매 정책 정리해줘
/oh-my-gx:lens 구매 한도 --idea "한도를 50만원으로 올리면?"
```

## `/dev` — 전체 개발 사이클

요청 한 줄로 PRD → 설계 → 구현 → 리뷰 → 커밋/PR까지 자동 수행합니다.

```bash
/oh-my-gx:dev 주문 취소 기능 추가                # 전체 사이클
/oh-my-gx:dev 결제 오류 긴급 수정해줘             # → hotfix 모드 자동 판정
```

| Phase | 하는 일 | 사용자 확인 |
|-------|---------|-----------|
| requirements | PRD 작성 | Q&A + 승인 |
| design | 기술 설계 | Q&A + 승인 |
| implement | 코드 구현 + 자기점검 | 결과 보고 |
| review | 코드 리뷰 + 보안 감사 | 이슈 답변 |
| complete | 인수 검증 + 커밋/PR | 최종 확인 |

**실전 대화 흐름 예시:**

```
사용자: /oh-my-gx:dev 상품 목록에 카테고리 필터 추가

AI(PO): 몇 가지 확인이 필요합니다.
    1. 카테고리는 단일 선택인가요, 복수 선택인가요?
    2. 필터 초기화 버튼이 필요한가요?

사용자: 복수 선택, 초기화 버튼 필요해

AI(PO): PRD를 작성했습니다. 확인해주세요.
    → [PRD 내용 표시]

사용자: 승인

AI(설계자): 기술 설계를 완료했습니다. API 엔드포인트와 DB 스키마를 확인해주세요.
    → [설계 내용 표시]

사용자: 승인

AI(개발자): 구현을 완료했습니다. 변경된 파일 5개, 테스트 통과.
AI(리뷰어): 코드 리뷰 완료. 이슈 없음.
AI: PR을 생성했습니다. → https://github.com/...
```

---

## 보조 스킬

핵심 워크플로우와 독립적으로 사용할 수 있는 스킬입니다.

| 스킬 | 설명 | 예시 |
|------|------|------|
| `/commit` | 브랜치명 기반 한국어 커밋 메시지 자동 생성 | `/oh-my-gx:commit` |
| `/pull-request` | 커밋 히스토리 기반 PR 자동 생성 | `/oh-my-gx:pull-request` |
| `/humanizer` | AI 글쓰기 교정 (감지/수정 모드) | `/oh-my-gx:humanizer docs/guide.md` |

---

## Google Chat 알림

`/setup` 실행 시 Google Chat 웹훅을 연동하면 PR 생성 시 Chat Space에 자동 알림이 전송됩니다.

한 명이 setup에서 URL을 설정하고 커밋하면, 다른 팀원은 pull 후 별도 설정 없이 동일한 알림을 받습니다.

---

## 안전장치

- PR 생성까지만 자동화합니다. **PR 머지는 사용자가 직접** 수행합니다.
- 보호 브랜치(main)에서 직접 커밋을 차단합니다.
- `git push --force`, `gh pr merge`를 차단합니다.
- 커밋 전 민감 파일(`.env` 등) 감지 시 경고합니다.

---

## FAQ

<details>
<summary><b>context/는 꼭 만들어야 하나요?</b></summary>

아니요. 없어도 동작합니다. 등록하면 에이전트가 도메인 용어와 아키텍처를 정확히 이해하여 더 정확한 코드를 생성합니다.
</details>

<details>
<summary><b>개발 지식 없이 사용할 수 있나요?</b></summary>

PRD 작성(`/dev PRD만 작성해줘`)과 정책 분석(`/lens`)은 코드를 직접 다루지 않아도 사용할 수 있습니다.
</details>

<details>
<summary><b>/dev를 실행하면 바로 코드를 짜나요?</b></summary>

아닙니다. 먼저 Q&A로 요구사항을 구체화하고(PRD), 기술 설계를 거친 뒤 사용자가 승인해야 구현에 들어갑니다. 각 단계마다 확인을 받기 때문에 의도와 다른 코드가 만들어질 걱정은 없습니다.
</details>

<details>
<summary><b>/dev 도중에 멈추면 처음부터 다시 해야 하나요?</b></summary>

아닙니다. "이어서 해줘" 또는 "아까 하던 작업 계속"이라고 말하면 중단된 단계부터 재개합니다.
</details>

<details>
<summary><b>context, lens, dev를 꼭 순서대로 실행해야 하나요?</b></summary>

아닙니다. `/dev`만 단독으로 실행해도 됩니다. 다만 `/context`로 도메인을 먼저 등록하면 AI가 도메인 용어를 정확히 이해하고, `/lens`로 현행 정책을 파악하면 더 정확한 결과를 얻을 수 있습니다.
</details>

<details>
<summary><b>PR이 자동으로 머지되나요?</b></summary>

아닙니다. PR 생성까지만 자동화합니다. 머지는 리뷰어가 직접 수행합니다.
</details>

<details>
<summary><b>/dev 없이 자연어로 코드를 수정했는데, context가 안 맞아요</b></summary>

`/commit` 실행 시 변경된 파일이 등록된 도메인과 관련 있으면 "context를 동기화할까요?"라고 물어봅니다. 동의하면 `/context 결제 동기화해줘`처럼 자연어로 동기화할 수 있습니다.
</details>

<details>
<summary><b>플러그인 업데이트는?</b></summary>

`/plugin marketplace update oh-my-gx`
</details>

---

## 업데이트

```bash
/plugin marketplace update oh-my-gx
```
