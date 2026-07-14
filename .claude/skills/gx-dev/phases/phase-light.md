# phase-light: AC 확인 + 구현 + Mechanical Gate + 기록 (LIGHT 모드 전용)

소형 변경용 경량 경로. 에이전트 팀 대신 오케스트레이터가 직접 수행하되, **기록(ac.md·summary.md)과 Mechanical Gate는 생략하지 않는다.** 이 둘이 "그냥 프롬프팅"과 이 파이프라인의 차이다.

- 이 phase는 LIGHT 모드(`mode: light`)에서만 진입한다. FULL 모드는 requirements → design → implement → review를 따른다.
- ralph 무인 루프 전환 질문은 두지 않는다 — LIGHT에는 PRD가 없어 gx-ralph 진입 조건(PRD 필수)을 충족하지 않는다.

## Step 0: AC 작성 (오케스트레이터 직접, 에이전트 디스패치 없음)

ARGS[0] + 코드 맵 + DOMAIN_CONTEXT(있으면)를 기반으로 `${DEV_DIR}/ac.md`를 직접 작성한다.

**형식** (초경량 PRD — gx-pull-request `--background`가 "배경"과 "요구사항"을 파싱하므로 섹션명을 유지한다):

```markdown
# {작업 제목}

## 배경
{왜 이 변경이 필요한가 — 2~3줄}

## 요구사항 (AC)
- AC-1: {검증 가능한 문장 — 무엇이 어떻게 동작해야 하는가}
- AC-2: ...
(3~5개 이내. 각 AC는 구현 완료 후 충족 여부를 판정할 수 있는 형태로 쓴다)
```

**긴급 버그 수정 요청**("긴급/핫픽스" 키워드 또는 레거시 `--hotfix`로 진입한 경우): AC를 버그 관점으로 구성한다 — AC-1은 재현 조건(현재 잘못된 동작), AC-2는 수정 후 기대 동작, 필요 시 AC-3에 회귀 방지 항목. 재현 조건을 파악할 정보가 부족하면 추측하지 말고 Step 0.5에서 사용자에게 확인한다.

작성 후 `current-step`을 `"AC 작성"`으로 설정한다.

## Step 0.5: AC 확인

ac.md 내용을 표시하고 AskUserQuestion으로 1회 확인한다 (긴급 요청도 예외 없다 — 긴급일수록 원인 오판 위험이 크고, 확인은 몇 초로 끝난다):

```
AskUserQuestion(
  questions: [{
    question: "AC를 확인해주세요. 이 기준으로 구현하고, 완료 시 충족 여부를 검증합니다.",
    header: "AC 확인",
    options: [
      { label: "승인", description: "구현 시작" },
      { label: "수정 요청", description: "Other로 이동해서 수정할 사항을 자연어로 입력해주세요" }
    ],
    multiSelect: false
  }]
)
```

- **승인** → Step 1로 진행.
- **수정 요청 또는 Other** → 입력 내용으로 ac.md를 갱신 후 재확인. 승인까지 반복한다.

## Step 1: 구현

**규모 판정** — 코드 맵과 AC를 대조하여 오케스트레이터가 직접 판단한다 (에이전트 불필요):

- **직접 구현** (다음 두 조건 모두 충족 시): 예상 변경 파일이 **2개 이하**이고, 변경 방향이 AC에서 명확히 도출됨.
  - 오케스트레이터가 대상 파일을 Read한 뒤 Edit/Write로 직접 구현한다. **수정 대상 코드를 읽지 않고 수정하지 않는다.**
  - **전환 안전장치**: 직접 구현 도중 변경 파일이 2개를 초과하거나 복잡도가 예상보다 높다고 판단되면, 무리하게 계속하지 말고 즉시 중단하고 **coder 1회 디스패치**로 전환한다 (이미 수행한 변경 내용을 프롬프트에 요약 포함).
- **coder 1회 디스패치** (그 외): `Task(subagent_type="oh-my-gx:coder")` — prompt에 다음을 포함:
  - ac.md 전체 (Context Slicing 규칙: coder 구현, LIGHT 모드. 레거시 세션 재개로 ac.md가 없으면 prd.md를 대용으로 사용)
  - 코드 맵 (누적된 상태)
  - 프로젝트 루트 경로
  - REFERENCES (있으면): "아래 외부 규격/표준을 구현 시 준수하라. 필요 시 Read하여 상세 내용을 확인하라." + REFERENCES 테이블
  - "AC를 벗어나는 변경을 하지 말 것. AC별로 어떤 파일을 어떻게 변경했는지 보고할 것."

구현 결과(변경 파일 목록)는 **요약만** 사용자에게 보고한다. `current-step`을 `"구현"`으로 설정한다.

## Step 2: Mechanical Gate (필수 — 건너뛰기 금지)

빌드/테스트 명령 결정과 실행 흐름은 **phase-review.md Step 0(Mechanical Gate)과 동일한 로직**을 사용한다 (빌드 명령 결정 우선순위: CLAUDE.md → 프로젝트 타입 기본값 → AskUserQuestion. 테스트 명령: config.json `projectTypes`의 `test` 필드).

1. build 실행 → 실패 시 수정(직접 구현이었으면 오케스트레이터가 직접, coder 디스패치였으면 coder 수정 모드 1회) 후 **1회 재시도**.
2. test 실행 → 실패 시 동일하게 수정 후 **1회 재시도**.
3. 재시도에도 실패하면 실패 로그를 표시하고 AskUserQuestion으로 확인한다:
   ```
   AskUserQuestion(
     questions: [{
       question: "Gate(빌드/테스트)가 실패했습니다. 어떻게 진행할까요?",
       header: "Gate 실패",
       options: [
         { label: "수동 수정 후 재실행", description: "직접 수정 후 Gate를 다시 실행합니다" },
         { label: "중단", description: "파이프라인을 중단합니다" }
       ],
       multiSelect: false
     }]
   )
   ```
4. **감지된 build·test가 모두 통과해야 Step 3으로 진행한다.** 긴급 요청도 예외 없다. 단 위임한 phase-review Step 0 로직과 동일하게, 프로젝트에 테스트 명령이 감지되지 않으면(config.json projectTypes에 test 없음) 테스트는 건너뛴다 — 이 경우 build 통과만으로 진행하되 execution-log에 "테스트 명령 미감지"를 명시한다. **테스트 명령이 있는데 그 통과 증거 없이 complete에 진입하지는 않는다.**

Gate 결과(명령·통과 여부)를 `execution-log`에 기록한다.

## Step 3: 기록

1. **Diff 수집 규칙**(SKILL.md 공유 규칙)에 따라 변경사항을 수집한다: `${GIT_PREFIX} add -A` 후 diff를 `DIFF_FILE`에 리다이렉트 (svn은 `svn diff > ${DIFF_FILE}`).
2. `${DEV_DIR}/summary.md`를 작성한다:
   ```markdown
   # 변경 요약: {작업 제목}

   ## 변경 파일
   | 파일 | 변경 유형 | 내용 |
   |------|----------|------|
   | ... | 신규/수정 | ... |

   ## 무엇을 왜
   {AC별로 어떤 변경으로 충족했는지 2~5줄}

   ## Gate 증거
   - build: {명령} → 통과
   - test: {명령} → 통과 (0 failures)
   ```
3. 사용자에게 요약만 보고하고 phase-complete로 진행한다.

## state.md 추적

```yaml
steps:
  light:
    - AC 작성: completed
    - AC 확인: completed
    - 구현: completed           # (직접) 또는 (coder)
    - mechanical-gate: completed
    - 기록: in_progress
```

`execution-log`에 구현 주체(직접/coder)와 Gate 결과를 기록한다.

## --resume 호환

- `"AC 작성"`/`"AC 확인"` → ac.md가 있으면 Step 0.5부터, 없으면 Step 0부터 재실행.
- `"구현"` → ac.md를 Read하여 복원 후 Step 1부터 재실행. **레거시 세션 재개**(phase-setup의 hotfix/implement→light 마이그레이션)로 ac.md가 없으면 prd.md를 대용으로 Read한다 (재작성하지 않음). 둘 다 없으면(구 implement 세션) Step 0부터 재실행하여 ac.md를 먼저 생성한다.
- `"mechanical-gate"` 이후 → Step 2부터 재실행 (Gate는 재실행해도 안전하다).
