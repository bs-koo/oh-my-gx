# phase-implement: 구현 + 자기점검

## Hotfix 모드 분기

오케스트레이터가 `--hotfix` 모드이면:
- Step 0에서 설계서(`design.md`) 로드를 건너뛴다. PRD(`prd.md`)는 로드한다.
- 구현 Task에서 설계서 대신 PRD와 코드 맵을 전달한다.
  - prompt: "다음 PRD를 참고하여 최소한의 변경으로 구현하라: {PRD 내용}. 코드 맵을 참고하라."
- 자기점검은 동일하게 실행한다.

hotfix가 아닌 경우 아래 정상 플로우를 따른다.

## 구현

**Task A**: coder 구현.

**Step 0**: 문서 로드.
- `${PROJECT_ROOT}/.dev/design.md`를 Read하여 설계서를 로드한다.
- `${PROJECT_ROOT}/.dev/prd.md`를 Read하여 PRD를 로드한다 (자기점검에서 "요구사항"+"수용 기준" 섹션 사용).

**Step 0.5**: 구현 계획 승인.

설계서의 "구현 순서"와 코드 맵을 기반으로, coder가 실제로 수행할 구체적인 변경 계획을 사용자에게 제시한다.
오케스트레이터가 직접 구성한다 (agent 호출 불필요):

1. 설계서의 "구현 순서" 섹션과 "변경 범위" 섹션을 파싱한다.
2. 코드 맵의 핵심 파일과 매칭하여 구체적 변경 목록을 구성한다.
3. 사용자에게 다음 형식으로 제시한다:

   ```
   ## 구현 계획

   ### 변경 파일
   | # | 파일 | 변경 유형 | 예상 변경 상세 | 영향 범위 |
   |---|------|----------|--------------|----------|
   | 1 | src/domain/PaymentLimit.kt | 신규 | PaymentLimit 데이터 클래스 생성 (필드: userId, dailyLimit, monthlyLimit) | PaymentService에서 참조 |
   | 2 | src/service/PaymentService.kt | 수정 | processPayment()에 한도 검증 로직 추가. PaymentLimit 조회 후 초과 시 예외 발생 | PaymentController, PaymentServiceTest |
   | 3 | src/controller/PaymentController.kt | 수정 | PUT /api/payments/limit 엔드포인트 추가. RequestBody로 한도 변경 요청 수신 | API 클라이언트, 프론트엔드 |
   | ... | | | | |

   ### 구현 순서
   1. [1단계] PaymentLimit 도메인 모델 생성
   2. [2단계] PaymentService에 한도 검증 로직 추가
   3. [3단계] PaymentController에 API 엔드포인트 추가
   ```

4. AskUserQuestion으로 승인을 받는다:
   ```
   AskUserQuestion(
     question: "구현 계획을 확인해주세요.",
     options: [
       { value: "approve", label: "승인 — 구현 시작" },
       { value: "modify", label: "수정 요청 — 변경할 항목을 알려주세요" }
     ]
   )
   ```
   - **승인** → Task A (coder 구현)로 진행. 구현 계획을 coder 프롬프트에 추가 포함.
   - **수정 요청** → 후속 AskUserQuestion(자유입력)으로 수정 내용을 받아 계획을 갱신 후 재제시 (1회).
   - 2회 제시 후에도 수정이 있으면 최신 계획으로 진행.

5. `current-step`을 `"구현 계획 승인"`으로 설정한다.

**건너뛰기 조건**:
- `--hotfix` 모드: 건너뛴다 (긴급 수정이므로 승인 대기 없이 바로 구현).
- 설계서에 "구현 순서" 섹션이 없는 경우: 건너뛴다 (`--phase implement` 단독 실행 등).

`Task(subagent_type="coder")` — prompt에 다음을 포함:
- 확정된 설계서 (Step 0에서 로드한 설계 문서 전체)
- 코드 맵 (누적된 상태)
- 프로젝트 타입 및 구조
- 프로젝트 루트 경로 (작업 경로 기준 참조)
- Step 0.5에서 승인된 계획이 있다면 해당 계획을, 없다면 설계서의 "구현 순서"를 전달하여 순서대로 구현하도록 지시합니다.

## Task 완료 후

**Step 1**: coder 결과를 받은 후:
- 설계서 "구현 순서"의 항목 수와 coder의 보고 단계 수(`[N/M]`의 M)를 비교한다. 불일치 시 누락 항목을 명시하고 사용자에게 확인한다.
- **요약만** 사용자에게 보고한다 (Agent 전문 출력 금지. 코드는 파일에 이미 작성됨):
  ```
  구현 완료: M단계
  - [1/M] <파일> - <변경 요약>
  - [2/M] <파일> - <변경 요약>
  - ...
  특이사항: (설계 불일치 등, 있으면)
  ```
- Agent가 설계에서 벗어난 판단을 했다면 해당 내용을 특이사항에 포함하고 사용자 확인을 받는다.

## 자기점검 (1회 패스, 루프 없음)

사용자 리뷰(phase-review) 전에 명백한 실수를 자동으로 잡는다. **1회만 실행하고 루프하지 않는다.**

**조건**: `${GIT_PREFIX} diff --stat`으로 변경 규모와 대상 파일을 확인한다 (unstaged 변경 기준). 다음 **두 조건을 모두** 만족할 때만 자기점검을 건너뛰고 phase-review로 직행한다:
1. 총 변경이 **10줄 미만**
2. 변경된 파일이 **설정 파일만**으로 구성 (e.g., `.yml`, `.yaml`, `.json`, `.toml`, `.properties`, `.env`, `.md`). 코드 파일(`.kt`, `.java`, `.ts`, `.js`, `.py` 등)이 하나라도 포함되면 규모와 무관하게 자기점검을 실행한다.

**Step 1**: 변경사항 수집 및 파일 저장 (작업 경로 기준에 따라 GIT_PREFIX를 붙여 실행). 이 스테이징은 diff 추출 목적이며, 커밋은 phase-complete의 commit이 별도로 수행한다. 스테이징 상태는 이후 phase-review의 diff 수집과 phase-complete의 commit까지 유지된다 (각 단계에서 `git add -A`를 재실행하므로 중간에 coder가 수정한 파일도 포함됨).

1. `${GIT_PREFIX} add -A`로 스테이징한다.
2. **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트한다 (`git diff --cached`를 Bash 단독 실행하지 않는다).

**Step 2**: qa-manager agent로 자동 리뷰.
`Task(subagent_type="qa-manager")` — prompt에 다음을 포함:
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- PRD의 "요구사항" + "수용 기준" 섹션만 (Context Slicing 규칙 참조: 자기점검 모드). `--hotfix`이면 PRD만 전달 (설계서 없음).
- "자기점검 단계이므로 CERTAIN 문제만 자동 수정 대상으로 취급할 것. QUESTION은 보고하되 수정하지 않고 phase-review로 이월한다."

**Step 3**: 결과 판단.
- **Critical이 있으면**: `Task(subagent_type="coder")` — Critical 항목 목록, qa-manager가 제시한 수정 방안, 코드 맵, 프로젝트 루트 경로를 prompt에 포함하여 자동 수정 (Context Slicing: coder 수정 모드). 수정 실패 시(coder가 해결하지 못했거나 수정 후에도 문제가 남는 경우) 미해결 Critical을 `SELF_CHECK_FINDINGS`에 `[Critical/미해결]`로 추가하고 phase-review로 이월한다. 자기점검은 1회만 시도하므로 재시도하지 않는다.
- **Critical이 없으면**: 자기점검 완료.
- Warning/Info는 `SELF_CHECK_FINDINGS` 변수에 저장한다. 형식: `[Warning] 파일:라인 - 설명` (한 줄씩). phase-review에서 qa-manager 프롬프트에 포함하여 중복 보고를 방지한다.
- QUESTION은 `SELF_CHECK_QUESTIONS` 변수에 저장한다. phase-review에서 qa-manager 프롬프트에 포함하여 사용자 확인을 받는다.
- 자기점검 결과(SELF_CHECK_FINDINGS + SELF_CHECK_QUESTIONS)를 `${PROJECT_ROOT}/.dev/self-check.md`에 Write한다. `--resume`으로 phase-review에서 재개할 때 이 파일을 Read하여 복원한다.

자기점검 결과를 사용자에게 **요약만** 보고한다 (Agent 전문 출력 금지):
```
자기점검 완료:
- Critical: N건 (자동 수정 완료/실패)
- Warning/Info: N건 (phase-review로 이월)
- QUESTION: N건 (phase-review로 이월)
```
이후 phase-review로 진행.

---

## 팀 모드 구현 (mode=team)

`mode: normal`이면 위 기존 로직을 실행한다. `mode: team`이면 아래를 실행한다.

### Step 0: 문서 로드 (동일)
기존과 동일하게 `design.md`, `prd.md`를 Read한다.

### Step 1: 팀장이 태스크 분할

팀장(architect)에게 SendMessage로 설계서를 전달하고 태스크 분할을 요청한다:
- 파일/모듈/레이어별로 분할 (예: Controller, Service, Repository, Test)
- 각 태스크에 담당 파일 목록 명시 (파일 소유권)
- TEAM_PLAN.md에 태스크 목록 기록

### Step 1.5: 태스크 분할 결과 승인

팀장의 태스크 분할 결과를 사용자에게 제시하고 승인을 받는다.

1. TEAM_PLAN.md에서 태스크 분할 결과를 읽어 사용자에게 다음 형식으로 제시한다:

   ```
   ## 팀 구현 계획

   ### 태스크 분할
   | # | 담당 | 태스크 | 파일 목록 |
   |---|------|--------|----------|
   | 1 | coder-backend | Service/Repository 구현 | PaymentService.kt, PaymentRepository.kt |
   | 2 | coder-frontend | Controller/API 구현 | PaymentController.kt |
   | 3 | coder-test | 테스트 작성 | PaymentServiceTest.kt |

   이 분할대로 진행할까요? 수정할 부분이 있으면 알려주세요.
   ```

2. 사용자 응답 처리:
   - **승인** → Step 2 (coder 스폰)로 진행.
   - **수정 요청** → 수정 사항을 반영하여 TEAM_PLAN.md 갱신 후 재제시 (1회).
   - 2회 제시 후에도 수정이 있으면 최신 계획으로 진행.

3. `current-step`을 `"태스크 분할 결과 승인"`으로 설정한다.

**건너뛰기 조건**: `--hotfix` 모드일 때 건너뛴다.

### Step 2: coder 팀원 스폰 (2~3명)

태스크 분할 결과에 따라 coder를 스폰한다:
```
Task({ team_name, name: "coder-backend", subagent_type: "coder", model: "inherit" })
Task({ team_name, name: "coder-frontend", subagent_type: "coder", model: "inherit" })
Task({ team_name, name: "coder-test", subagent_type: "coder", model: "sonnet" })
```

각 coder 프롬프트에 포함:
- 담당 파일/모듈 명시
- 다른 coder 담당 영역 명시 (충돌 방지)
- 공유 메모리 경로 + TEAM_PROGRESS.md 업데이트 규칙:
  - 태스크 시작 시: 상태를 `in_progress`로 기록
  - 태스크 완료 시: 상태를 `completed`로 기록
  - 차단 발생 시: 상태를 `blocked`로 기록 + TEAM_FINDINGS.md에 원인 기록
- 설계서에서 자신의 담당 부분
- 코드 맵, 프로젝트 루트 경로

### Step 3: 팀장 모니터링

팀장이 TEAM_PROGRESS.md를 모니터링한다:
- 모든 coder 완료 → Step 4(자기점검)로 진행
- 차단 발생 → SendMessage로 조율 (다른 coder에게 도움 요청 또는 담당 재배정)

### Step 4: 자기점검 (기존 로직과 동일)

기존 자기점검 로직(qa-manager 호출)을 그대로 실행한다.
- 변경사항 수집, qa-manager 리뷰, Critical 자동 수정 모두 동일.
- 팀 모드에서도 자기점검은 오케스트레이터가 단일 qa-manager로 수행한다 (팀 내 직접 소통은 phase-review에서).
