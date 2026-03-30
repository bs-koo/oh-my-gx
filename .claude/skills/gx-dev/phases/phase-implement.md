# phase-implement: 구현 + 자기점검

## Hotfix 모드 분기

오케스트레이터가 `--hotfix` 모드이면:
- Step 0에서 설계서(`design.md`) 로드를 건너뛴다. PRD(`prd.md`)는 로드한다.
- Step 1(구현 계획 승인), Step 1.5(배치 구성)도 건너뛴다.
- 구현 Task에서 설계서 대신 PRD와 코드 맵을 전달한다.
  - prompt: "다음 PRD를 참고하여 최소한의 변경으로 구현하라: {PRD 내용}. 코드 맵을 참고하라." + REFERENCES (있으면): "아래 외부 규격/표준을 구현 시 준수하라. 필요 시 Read하여 상세 내용을 확인하라." + REFERENCES 테이블
- 자기점검은 동일하게 실행한다.

## 경량 구현 모드 분기

오케스트레이터가 `implement` (경량 구현) 모드이면:
- Step 0에서 설계서(`design.md`)와 PRD(`prd.md`) 로드를 모두 건너뛴다.
- Step 1(구현 계획 승인), Step 1.5(배치 구성)도 건너뛴다.
- 구현 Task에서 ARGS[0]과 코드 맵을 전달한다.
  - prompt: "다음 요청을 참고하여 구현하라: {ARGS[0]}. 코드 맵을 참고하라." + REFERENCES (있으면): "아래 외부 규격/표준을 구현 시 준수하라. 필요 시 Read하여 상세 내용을 확인하라." + REFERENCES 테이블
- 자기점검은 동일하게 실행한다. 단, PRD가 없으므로 자기점검(Step 5)에서 qa-manager에게 PRD 대신 ARGS[0]을 전달한다.

## 코드 미리보기 승인 분기

state.md에 `preview-written: true`가 기록되어 있으면 (phase-design에서 코드 미리보기 승인 후 파일이 이미 Write된 경우):
- Step 0~2(문서 로드, 구현 계획, 배치 구성, coder 디스패치)를 건너뛴다.
- Step 3(구현 결과 수집)부터 시작한다. 미리보기에서 Write된 파일 목록을 기반으로 결과를 수집한다.
- 자기점검은 동일하게 실행한다.
- state.md에서 `preview-written` 플래그를 제거한다.

hotfix도 경량 구현 모드도 코드 미리보기도 아닌 경우 아래 정상 플로우를 따른다.

## 구현

**Task A**: coder 구현.

**Step 0**: 문서 로드.
- `${DEV_DIR}/design.md`를 Read하여 설계서를 로드한다.
- `${DEV_DIR}/prd.md`를 Read하여 PRD를 로드한다 (자기점검에서 "요구사항"+"수용 기준" 섹션 사용).

**Step 1**: 구현 계획 승인.

설계서의 "구현 순서"와 코드 맵을 기반으로, coder가 실제로 수행할 구체적인 변경 계획을 사용자에게 제시한다.
오케스트레이터가 직접 구성한다 (agent 호출 불필요):

1. 설계서의 "구현 순서" 섹션에서 각 단계의 `(의존: N)` 또는 `(의존: N, M)` 표기를 파싱하고, "변경 범위" 섹션에서 대상 파일을 추출한다.
   - **폴백**: 구현 순서 섹션은 있으나 `(의존:)` 표기가 없는 단계는 이전 단계에 순차 의존하는 것으로 간주한다 (기존 설계서 호환).
2. 코드 맵의 핵심 파일과 매칭하여 구체적 변경 목록을 구성한다.
3. 의존성 힌트를 기반으로 **예비 배치**를 간이 위상 정렬로 구성한다:
   - `(의존: 없음)` 단계들 → B1 (병렬 후보)
   - 의존 대상이 모두 B(K)에 속하는 단계들 → B(K+1)
   - 같은 파일을 수정하는 단계가 같은 배치에 있으면 분리한다
   - 이 예비 배치는 사용자 확인용이며, Step 1.5에서 import/참조 검증 후 확정된다
4. 사용자에게 예비 배치를 포함한 다음 형식으로 제시한다:

   ```
   ## 구현 계획

   ### 변경 파일
   | # | 파일 | 변경 유형 | 예상 변경 상세 | 영향 범위 |
   |---|------|----------|--------------|----------|
   | 1 | src/domain/PaymentLimit.kt | 신규 | PaymentLimit 데이터 클래스 생성 (필드: userId, dailyLimit, monthlyLimit) | PaymentService에서 참조 |
   | 2 | src/service/PaymentService.kt | 수정 | processPayment()에 한도 검증 로직 추가. PaymentLimit 조회 후 초과 시 예외 발생 | PaymentController, PaymentServiceTest |
   | 3 | src/controller/PaymentController.kt | 수정 | PUT /api/payments/limit 엔드포인트 추가. RequestBody로 한도 변경 요청 수신 | API 클라이언트, 프론트엔드 |
   | ... | | | | |

   ### 구현 순서 (병렬 배치)
   | 배치 | 단계/설명 | 대상 파일 |
   |------|----------|----------|
   | B1 | [1단계] PaymentLimit 도메인 모델 생성 | PaymentLimit.kt (신규) |
   | B1 | [2단계] PaymentLimitRepository 인터페이스 | PaymentLimitRepository.kt (신규) |
   | B2 | [3단계] PaymentService 한도 검증 | PaymentService.kt (수정) |
   | B3 | [4단계] Controller API 엔드포인트 | PaymentController.kt (수정) |

   - B1: 2개 단계 병렬 실행
   - B2: B1에 의존, 순차 실행
   - B3: B2에 의존, 순차 실행
   ```

5. AskUserQuestion으로 승인을 받는다:
   ```
   AskUserQuestion(
     question: "구현 계획을 확인해주세요. 수정할 사항이 있으면 직접 입력해주세요.",
     options: [
       { value: "approve", label: "승인 — 구현 시작" }
     ]
   )
   ```
   - **승인** → Step 1.5 (배치 구성)으로 진행.
   - **직접 입력(Other)** → 입력된 수정 내용으로 계획을 갱신 후 재제시. 사용자가 승인할 때까지 반복한다.

6. `current-step`을 `"구현 계획 승인"`으로 설정한다.

**건너뛰기 조건**:
- `--hotfix` 모드: 건너뛴다 (긴급 수정이므로 승인 대기 없이 바로 구현).
- 설계서에 "구현 순서" 섹션이 없는 경우: 건너뛴다 (`--phase implement` 단독 실행 등).

**Step 1.5**: 의존성 분석 및 배치 구성.

오케스트레이터가 직접 수행한다 (agent 호출 없음).

#### 1.5.1 파일 맵 구성
승인된 구현 계획의 각 단계에서 대상 파일(생성/수정)을 추출:
  단계별_파일맵 = { "1단계": ["PaymentLimit.kt"], "2단계": ["PaymentService.kt"], ... }

#### 1.5.2 의존성 분석

(a) **설계서 의존성 힌트** (1차 입력):
  설계서 "구현 순서"의 각 단계에 `(의존: N)` 또는 `(의존: N, M)` 표기가 있으면 이를 초기 의존성 그래프로 사용한다.
  `(의존: 없음)` 단계들은 잠재적 병렬 후보이다.
  표기가 없는 단계는 이전 단계에 순차 의존하는 것으로 간주한다 (폴백).

(b) **파일 배타적 잠금** (최우선, 기계적 판별):
  두 단계의 대상 파일 교집합이 비어있지 않으면 → 반드시 순차.
  설계서 힌트가 병렬이라고 해도 파일 충돌이 있으면 순차로 **오버라이드**한다.

(c) **import/참조 의존** (설계서 + 코드 맵):
  한 단계가 다른 단계에서 신규 생성하는 타입/인터페이스를 참조하면 → 의존.
  코드 맵의 import 관계도 교차 검증한다.
  설계서 힌트가 `의존: 없음`이라도 실제 참조가 발견되면 순차로 **오버라이드**한다.

#### 1.5.3 배치 배정 (위상 정렬)
의존성 그래프를 위상 정렬하여 배치 구성:
- 의존성 없는 단계들 → B1
- B1에 의존하는 단계들 → B2
- ...
단계가 2개 이상인 배치만 parallel=true.

`current-step`을 `"배치 구성"`으로 설정.

**건너뛰기 조건**: `--hotfix` 모드, 설계서에 "구현 순서" 없는 경우 → Step 1과 함께 건너뜀.

**Step 2**: 배치별 coder 디스패치.

for batch in batches:

  **단일 배치 + 단일 단계 (batches==1, steps==1)**:
    기존 전체 모드 coder 호출 (설계서 전체 + 코드 맵 + PROJECT_ROOT).
    `Task(subagent_type="coder")` — prompt에 다음을 포함:
    - 확정된 설계서 (Step 0에서 로드한 설계 문서 전체)
    - 코드 맵 (누적된 상태)
    - 프로젝트 타입 및 구조
    - 프로젝트 루트 경로 (작업 경로 기준 참조)
    - REFERENCES (있으면): "아래 외부 규격/표준을 구현 시 준수하라. 필요 시 Read하여 상세 내용을 확인하라." + REFERENCES 테이블
    - Step 1에서 승인된 계획이 있다면 해당 계획을, 없다면 설계서의 "구현 순서"를 전달하여 순서대로 구현하도록 지시.

  **그 외**:
    if batch.parallel (단계 2개 이상):
      하나의 메시지에서 동시 Task(subagent_type="coder") 발행.
      각 coder에 배치 모드 prompt: 담당 단계 설계 + 담당 파일 목록 +
      이전 배치 결과 요약 + 병렬 안내 + 코드 맵 + PROJECT_ROOT + REFERENCES (있으면).
    else:
      단일 Task(subagent_type="coder") 배치 모드 호출.

  **배치 간 빌드 검증** (마지막 배치 제외):
    빌드 명령 실행 (phase-review Step 0-1과 동일한 빌드 명령 결정 로직).
    실패 시 → 에러 원인 특정 프로세스:
      1. 에러 출력에서 파일 경로 추출
      2. 단계별_파일맵과 대조 → 원인 coder 특정
      3. 특정 성공: 해당 단계 설계 + 에러 메시지로 coder 수정 모드 재호출
      4. 특정 실패 (통합 문제): 관련 단계들의 설계를 합쳐 단일 coder 수정 모드 호출
      5. 재빌드 실패: 사용자에게 보고 + AskUserQuestion

  batch_results에 결과 누적.
  `current-step`을 `"coder 구현 (B{N})"` 형식으로 갱신.

## Task 완료 후

**Step 3**: 구현 결과 수집.

**단일 배치 + 단일 단계** — 기존 포맷:
- 설계서 "구현 순서"의 항목 수와 coder의 보고 단계 수(`[N/M]`의 M)를 비교한다. 불일치 시 누락 항목을 명시하고 사용자에게 확인한다.
- **요약만** 사용자에게 보고한다 (Agent 전문 출력 금지. 코드는 파일에 이미 작성됨):
  ```
  구현 완료: M단계
  - [1/M] <파일> - <변경 요약>
  - [2/M] <파일> - <변경 요약>
  - ...
  특이사항: (설계 불일치 등, 있으면)
  ```

**다중 배치** — 배치별 그룹 포맷:
- **요약만** 사용자에게 보고한다:
  ```
  구현 완료: 총 M단계 (B개 배치)

  [B1] 병렬 2단계
  - [1/M] <파일> - <변경 요약>
  - [2/M] <파일> - <변경 요약>
  - 빌드 검증: Green

  [B2] 순차 1단계
  - [3/M] <파일> - <변경 요약>
  - 빌드 검증: Green
  ```

설계서 항목 수 vs coder 보고 단계 수 비교 → 불일치 시 누락 명시.
Agent가 설계에서 벗어난 판단을 했다면 해당 내용을 특이사항에 포함하고 사용자 확인을 받는다.

## 자기점검 (1회 패스, 루프 없음)

사용자 리뷰(phase-review) 전에 명백한 실수를 자동으로 잡는다. **1회만 실행하고 루프하지 않는다.**

**조건**: 변경 규모와 대상 파일을 확인하여 다음 **두 조건을 모두** 만족할 때만 자기점검을 건너뛰고 phase-review로 직행한다:
1. 총 변경이 **10줄 미만**
2. 변경된 파일이 **설정 파일만**으로 구성 (e.g., `.yml`, `.yaml`, `.json`, `.toml`, `.properties`, `.env`, `.md`). 코드 파일(`.kt`, `.java`, `.ts`, `.js`, `.py` 등)이 하나라도 포함되면 규모와 무관하게 자기점검을 실행한다.

변경 사항 확인 방법은 VCS에 따라 다르다:
- **git**: `${GIT_PREFIX} diff --stat` (unstaged 변경 기준).
- **svn**: `${GIT_PREFIX} status`로 변경된 파일 목록과 수를 확인한다.

**Step 4**: 변경사항 수집 및 파일 저장 (작업 경로 기준에 따라 GIT_PREFIX를 붙여 실행). 이 스테이징은 diff 추출 목적이며, 커밋은 phase-complete의 commit이 별도로 수행한다. 스테이징 상태는 이후 phase-review의 diff 수집과 phase-complete의 commit까지 유지된다 (각 단계에서 `git add -A`를 재실행하므로 중간에 coder가 수정한 파일도 포함됨).

**git인 경우:**
1. `${GIT_PREFIX} add -A`로 스테이징한다.
2. **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트한다 (`git diff --cached`를 Bash 단독 실행하지 않는다).

**svn인 경우:**
1. 스테이징 불필요 (SVN은 staging 개념 없음).
2. `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다.

**Step 5**: qa-manager agent로 자동 리뷰.
`Task(subagent_type="qa-manager")` — prompt에 다음을 포함:
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- PRD의 "요구사항" + "수용 기준" 섹션만 (Context Slicing 규칙 참조: 자기점검 모드). `--hotfix`이면 PRD만 전달 (설계서 없음). `implement` 모드이면 PRD 대신 ARGS[0]을 전달.
- "자기점검 단계이므로 CERTAIN 문제만 자동 수정 대상으로 취급할 것. QUESTION은 보고하되 수정하지 않고 phase-review로 이월한다."

**Step 6**: 결과 판단.
- **Critical이 있으면**: `Task(subagent_type="coder")` — Critical 항목 목록, qa-manager가 제시한 수정 방안, 코드 맵, 프로젝트 루트 경로를 prompt에 포함하여 자동 수정 (Context Slicing: coder 수정 모드). 수정 실패 시(coder가 해결하지 못했거나 수정 후에도 문제가 남는 경우) 미해결 Critical을 `SELF_CHECK_FINDINGS`에 `[Critical/미해결]`로 추가하고 phase-review로 이월한다. 자기점검은 1회만 시도하므로 재시도하지 않는다.
- **Critical이 없으면**: 자기점검 완료.
- Warning/Info는 `SELF_CHECK_FINDINGS` 변수에 저장한다. 형식: `[Warning] 파일:라인 - 설명` (한 줄씩). phase-review에서 qa-manager 프롬프트에 포함하여 중복 보고를 방지한다.
- QUESTION은 `SELF_CHECK_QUESTIONS` 변수에 저장한다. phase-review에서 qa-manager 프롬프트에 포함하여 사용자 확인을 받는다.
- 자기점검 결과(SELF_CHECK_FINDINGS + SELF_CHECK_QUESTIONS)를 `${DEV_DIR}/self-check.md`에 Write한다. `--resume`으로 phase-review에서 재개할 때 이 파일을 Read하여 복원한다.

자기점검 결과를 사용자에게 **요약만** 보고한다 (Agent 전문 출력 금지):
```
자기점검 완료:
- Critical: N건 (자동 수정 완료/실패)
- Warning/Info: N건 (phase-review로 이월)
- QUESTION: N건 (phase-review로 이월)
```
이후 다음 Phase로 진행.

## state.md 추적

`steps.implement`에 배치 정보를 반영한다:
```yaml
steps:
  implement:
    - 구현 계획 승인: completed
    - 배치 구성: completed
    - coder 구현 (B1, 2단계 병렬): completed
    - 빌드 검증 (B1): completed
    - coder 구현 (B2, 1단계): in_progress
```

`execution-log`에도 배치 정보를 기록한다:
```yaml
- phase: implement
  agent: coder (B1-step1)
  result: completed
  files: ["PaymentLimit.kt"]
```

## --resume 호환

- state.md의 `mode` 필드를 확인하여 `implement` (경량 구현) 모드이면 Step 1, Step 1.5를 건너뛰고 Step 2(coder 디스패치)부터 시작한다. `hotfix` 모드도 동일.
- state.md에 `preview-written: true`가 있으면 코드 미리보기 승인 분기를 따른다.
- `"배치 구성"` → Step 1.5부터 재실행
- `"coder 구현 (B2)"` → B1 결과는 파일에 반영됨. `execution-log`에서 이전 배치 결과 복원 후 B2부터 재개
- `"자기점검"` → Step 4(변경사항 수집)부터 재실행
