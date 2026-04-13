# phase-review: 검토 + 통합 감사 (QA Manager + ZeroTrust 병렬)

**최대 2회 반복.**

**문서 로드**: `${DEV_DIR}/prd.md`와 `${DEV_DIR}/design.md`를 Read한다. 파일이 없으면 (`--phase review` 단독 실행 등) 건너뛴다.
`${DEV_DIR}/self-check.md`가 존재하면 Read하여 `SELF_CHECK_FINDINGS`와 `SELF_CHECK_QUESTIONS` 변수를 복원한다 (`--resume`으로 phase-review에서 재개하는 경우).

## Step 0: Mechanical Gate (build + test)

QA/ZT 에이전트 호출 전에 기계적 검증을 통과시킨다. 실패하는 코드를 리뷰하는 것은 토큰 낭비이다.

프로젝트 타입은 config.json의 `projectTypes`를, 타임아웃은 `timeouts`를 참조한다.

### Step 0-1: Build

**빌드 명령 결정**:

1. `${PROJECT_ROOT}/CLAUDE.md`를 Read하여 빌드/컴파일 명령을 탐색한다. `build`, `compile`, `빌드` 키워드가 포함된 명령을 찾는다. CLAUDE.md가 없으면 다음 단계로.
2. CLAUDE.md에 빌드 명령이 없으면 → 프로젝트 타입에서 기본값을 사용한다:
   | 프로젝트 타입 | 기본 빌드 명령 |
   |---------------|---------------|
   | kotlin-gradle, java-gradle | `./gradlew build -x test` |
   | node | `bun run build` 또는 `npm run build` (package.json의 scripts.build가 있을 때만. `which bun` → bun, 없으면 npm) |
   | python | 건너뛰기 (인터프리터 언어) |
3. 프로젝트 타입으로도 결정 불가:
   ```
   AskUserQuestion(
     questions: [{
       question: "빌드 검증 명령을 감지하지 못했습니다. 어떻게 진행할까요?",
       header: "빌드 검증",
       options: [
         { label: "건너뛰기", description: "빌드 검증 없이 진행합니다" },
         { label: "중단", description: "작업을 중단합니다" }
       ],
       multiSelect: false
     }]
   )
   ```
   - Other → 사용자가 입력한 명령을 사용.
   - 건너뛰기 → 빌드 검증 없이 진행.
   - 중단 → 작업을 중단합니다.

**실행 흐름**:
1. 감지된 빌드 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 0-2로 진행.
3. **실패** → 에러 출력을 `Task(subagent_type="coder")`에 전달하여 자동 수정 시도 (Context Slicing: coder 수정 모드 — 빌드 에러 메시지 + 코드 맵 + 프로젝트 루트 경로).
4. 수정 후 빌드를 **1회 재시도**한다.
5. **재시도 성공** → Step 0-2로 진행.
6. **재시도 실패** → 사용자에게 빌드 에러를 표시하고:
   ```
   AskUserQuestion(
     questions: [{
       question: "빌드가 실패했습니다. 어떻게 진행할까요?",
       header: "빌드 실패",
       options: [
         { label: "계속 진행", description: "직접 수정 후 이어서 진행합니다" },
         { label: "중단", description: "파이프라인을 중단합니다" }
       ],
       multiSelect: false
     }]
   )
   ```

### Step 0-2: Test

**테스트 명령 결정**: config.json `projectTypes`의 `test` 필드를 사용한다. 테스트 명령이 없으면 건너뛴다.

**실행 흐름**:
1. 테스트 명령을 `PROJECT_ROOT`에서 실행한다.
2. **성공** → Step 1로 진행.
3. **실패** → 에러 출력을 `Task(subagent_type="coder")`에 전달하여 자동 수정 시도.
4. 수정 후 테스트를 **1회 재시도**한다.
5. **재시도 성공** → Step 1로 진행.
6. **재시도 실패** → 사용자에게 테스트 실패를 표시하고:
   ```
   AskUserQuestion(
     questions: [{
       question: "테스트가 실패했습니다. 어떻게 진행할까요?",
       header: "테스트 실패",
       options: [
         { label: "계속 진행", description: "직접 수정 후 이어서 진행합니다" },
         { label: "중단", description: "파이프라인을 중단합니다" }
       ],
       multiSelect: false
     }]
   )
   ```

### Gate 통과 기준

build, test 모두 통과해야 Step 1로 진행한다. 단일 Gate에서 오케스트레이터가 직접 판단한다 (에이전트 호출 불필요).

---

각 반복(1~2회)에서:

**Step 1**: 변경사항 수집 및 파일 저장.

**git인 경우** (작업 경로 기준에 따라 GIT_PREFIX를 붙여 실행):
- **전체 플로우** (phase-setup부터 진행): `${GIT_PREFIX} add -A`로 스테이징한 후, **Diff 수집 규칙**에 따라 `--cached` diff를 `DIFF_FILE`에 리다이렉트한다.
- **`--phase review` 단독 실행**: 베이스 브랜치 감지 규칙에 따라 베이스를 결정한다. **Diff 수집 규칙**에 따라 `${GIT_PREFIX} diff $(${GIT_PREFIX} merge-base HEAD <base-branch>)...HEAD`를 `DIFF_FILE`에 리다이렉트한다. 미커밋 변경이 있으면 `${GIT_PREFIX} diff >> ${DIFF_FILE}`로 추가한다.

**svn인 경우**:
- `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다. staging 없이 한 단계로 끝난다.

**Step 2**: qa-manager와 security-auditor를 **병렬로** 호출한다.

**Task A**: qa-manager agent.
`Task(subagent_type="qa-manager")` — prompt에 다음을 포함:
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- PRD의 "요구사항" + "수용 기준" + 설계서의 "변경 범위" 섹션 (Context Slicing 규칙 참조). **`--phase review` 단독 실행으로 문서가 없으면**: 문서 없이 diff만으로 코드 품질 리뷰를 수행하도록 안내한다.
- 코드 맵 (누적된 상태, 있으면)
- 이전 Q&A 히스토리 (이전 반복의 답변, 있으면)
- `SELF_CHECK_FINDINGS` (phase-implement 자기점검에서 발견된 Warning/Info 항목, 있으면). "다음 항목은 자기점검에서 이미 발견·수정된 사항이다. 동일 항목을 다시 보고하지 말 것." 안내와 함께 전달.
- `SELF_CHECK_QUESTIONS` (phase-implement 자기점검에서 QA가 보고한 QUESTION 항목, 있으면). "다음 항목은 자기점검에서 확인이 필요하다고 보고된 사항이다. 사용자 확인이 필요하면 QUESTION에 포함할 것." 안내와 함께 전달.
- REFERENCES (있으면): "아래 외부 규격/표준의 준수 여부를 검토하라. 위반 발견 시 CERTAIN으로 보고하라." + REFERENCES 테이블
- 반복 2회차면: 이전 리뷰 이후 수정된 내용

**Task B**: security-auditor 통합 감사.
`Task(subagent_type="security-auditor")` — prompt에 다음을 포함:
- PRD 전체 (있으면)
- 설계서 전체 (있으면)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- REFERENCES (있으면): "아래 외부 규격/표준의 보안 관련 항목을 감사에 포함하라." + REFERENCES 테이블
- "통합 감사"로 동작할 것

**Step 3**: 두 Task 완료 후 결과를 합산한다.

1. ZT 감사 결과를 Trust Ledger로 구성하고 `${DEV_DIR}/trust-ledger.md`에 저장한다.
2. QA의 CERTAIN + ZT의 CRITICAL/HIGH/MEDIUM을 합산하여 **통합 findings**를 구성한다.
3. 중복 항목은 병합한다 (같은 파일:라인을 둘 다 지적한 경우).
4. 사용자에게 **요약만** 표시한다 (Agent 전문 출력 금지):
   ```
   리뷰 완료:
   - QA: Critical N건, Warning N건, Info N건, QUESTION N건
   - ZT: CRITICAL N건, HIGH N건, MEDIUM N건
   - 전문 확인: ${DEV_DIR}/trust-ledger.md
   ```

**Step 4**: 결과 처리 (의사코드)

```
findings = Step 3에서 합산한 통합 findings
did_fix = false

# 4a: Critical 자동 수정
if findings에 Critical(QA) 또는 CRITICAL(ZT)이 있으면:
    해당 항목만 사용자에게 표시
    coder로 자동 수정 (수정 모드: 항목 목록 + 수정 방안 + 코드 맵 + PROJECT_ROOT)
    did_fix = true

# 4b: QUESTION 사용자 확인 (AskUserQuestion 변환)
if findings에 QUESTION(QA)이 있으면:
    각 QUESTION을 **에이전트 질문 → AskUserQuestion 변환 규칙** (SKILL.md 공유 규칙)에 따라 변환한다.
    단, 첫 번째 AskUserQuestion에 "전부 넘어가기" 선택지를 추가한다:
    ```
    AskUserQuestion(
      questions: [{
        question: "QA 리뷰에서 확인이 필요한 사항이 N건 있습니다. 첫 번째 질문입니다: {질문}",
        header: "QA 확인",
        options: [
          { label: "선택지A", description: "설명" },
          { label: "선택지B", description: "설명" },
          { label: "전부 넘어가기", description: "모든 QUESTION을 기록만 하고 진행" }
        ],
        multiSelect: false
      }]
    )
    ```
    if 사용자가 "전부 넘어가기" 선택:
        미답변 QUESTION을 Trust Ledger에 기록:
        ### 미답변 QA QUESTION
        - [QUESTION] 항목 설명
          - 맥락: ...
    else:
        답변을 수렴하고 나머지 QUESTION도 순서대로 AskUserQuestion으로 제시
        did_fix = true

# 4c: 반복 판단
if did_fix:
    → 다음 반복 (재리뷰)
else:
    # Critical도 QUESTION도 없는 경우
    if Warning/Info(QA) 또는 HIGH/MEDIUM(ZT) 항목이 있으면:
        항목 목록을 표시하고:
        ```
        AskUserQuestion(
          questions: [{
            question: "위 항목들을 수정할까요?",
            header: "리뷰 항목",
            options: [
              { label: "수정", description: "위 항목들을 자동 수정합니다" },
              { label: "건너뛰기", description: "현재 상태로 진행합니다" }
            ],
            multiSelect: false
          }]
        )
        ```
        if 수정 선택:
            coder로 수정 → qa-manager 1회 확인 리뷰 → phase-complete
            # 이 확인 리뷰는 최대 2회 반복 카운트에 포함되지 않는 단발성 검증이다.
        else:
            → phase-complete
    else:
        → phase-complete (클린 통과)
```

**2회 반복 후 미해결 Critical**: 2회 반복 후에도 Critical이 남아있으면 미해결 항목을 사용자에게 명시하고:
```
AskUserQuestion(
  questions: [{
    question: "2회 리뷰 후에도 미해결 Critical이 있습니다. 어떻게 진행할까요?",
    header: "미해결 항목",
    options: [
      { label: "수동 수정 후 재리뷰", description: "직접 수정 후 다시 리뷰합니다" },
      { label: "현재 상태로 진행", description: "미해결 항목을 남기고 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

