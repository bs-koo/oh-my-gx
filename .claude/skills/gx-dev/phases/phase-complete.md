# phase-complete: 완료

각 단계가 실패하면 사용자에게 보고하고 진행 여부를 확인한다.

## Step 0-pre: diff 갱신
phase-review 이후 coder 수정이 있었을 수 있으므로 diff를 갱신한다. 이 단계는 인수 검증 여부와 무관하게 항상 실행한다.
- **git**: `git add -A`로 스테이징한 후 **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트.
- **svn**: `svn diff > ${DIFF_FILE}`로 갱신.

## Step 0: 인수 검증 (ProductOwner)
PRD가 없으면 이 단계를 건너뛴다.

PRD가 있으면 (`${DEV_DIR}/prd.md`), product-owner에게 인수 검증을 요청한다.

`Task(subagent_type="product-owner")` — prompt에 다음을 포함:
- PRD의 "요구사항" + "수용 기준" (Context Slicing 규칙 참조)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- "인수 검증"으로 동작할 것

**결과를 사용자에게 요약만 보고한다** (Agent 전문 출력 금지):
- **ACCEPT**: "인수 검증 통과. 모든 [Must] 수용 기준 충족." 다음 단계 진행.
- **REJECT**: "인수 검증 미통과. [Must] 미충족 N건:" + 미충족 항목 목록만 표시. 수정 여부를 확인한다:
  ```
  AskUserQuestion(
    question: "인수 검증에서 미충족 항목이 있습니다. 자동 수정할까요?",
    options: [
      { value: "fix", label: "수정 — 미충족 항목을 자동 수정합니다" },
      { value: "skip", label: "건너뛰기 — 현재 상태로 다음 단계로 진행합니다" }
    ]
  )
  ```
  - 수정 선택 → coder로 수정 후 인수 검증 1회 재실행.
  - 건너뛰기 선택 → 다음 단계 진행.

> **참고**: PRD가 없는 경우(`implement` 경량 구현 모드 등) 이 단계가 건너뛰어진다. `--hotfix` 모드는 경량 PRD를 생성하므로 인수 검증이 **실행**된다. 단, Step 3 status.md 갱신에서 HOTFIX는 인수검증 결과와 무관하게 **경로 B (커밋 기반)**를 사용한다.

## Step 1: Commit

**svn인 경우** → 건너뛴다. "SVN 프로젝트입니다. 리뷰 완료 후 `svn commit`을 직접 실행해주세요." 출력 후 Step 3으로 진행.

**git인 경우:**

`Skill(skill: "oh-my-gx:gx-commit")`을 호출하여 커밋을 실행한다.

**test 실패 시 자동 수정 (1회):**
1. commit 스킬이 test 실패로 중단하면, 실패 로그와 코드 맵, PROJECT_ROOT를 `Task(subagent_type="coder")`에 전달하여 수정 요청.
2. 수정 완료 후 `Skill(skill: "oh-my-gx:gx-commit")`을 재호출한다.
3. 재호출도 실패하면 사용자에게 실패 목록을 보고하고 진행 여부를 확인한다.

## Step 2: PR 생성

**svn인 경우** → 건너뛴다 (Step 1에서 이미 건너뜀).

**git인 경우:**

`Skill(skill: "oh-my-gx:gx-pull-request")`을 호출하여 PR을 생성한다. args를 통해 dev 컨텍스트를 전달한다:

1. **args 구성**:
   - `--background ${DEV_DIR}/prd.md`: PRD의 "배경"과 "요구사항"을 Background 섹션에 반영. `implement` (경량 구현) 모드이면 PRD가 없으므로 `--background`를 생략한다.
   - `--extra-section ${DEV_DIR}/trust-ledger.md`: Trust Ledger가 존재하면 Audit Summary 섹션을 Checklist 앞에 삽입. 파일이 없으면 `--extra-section`을 생략한다.
   - 예: `Skill(skill: "oh-my-gx:gx-pull-request", args: "--background ${DEV_DIR}/prd.md --extra-section ${DEV_DIR}/trust-ledger.md")`
2. pull-request 스킬이 전제조건 미충족(gh 미설치, remote 미설정 등)으로 종료하면, 오케스트레이터는 후속 안내를 추가한다: "나중에 `/gx-pull-request`로 PR을 생성할 수 있습니다."
3. **PR 생성 후 알림**: `pull-request` 스킬이 PR 생성 후 내부적으로 알림 절차를 수행한다. 오케스트레이터가 별도로 알림을 처리할 필요 없다.

## Step 3: 도메인 status.md 갱신

**git인 경우에만 실행한다.** svn인 경우 건너뛴다 (SVN은 브랜치 기반 커밋 로그 비교가 불가하며, Step 1에서 커밋도 건너뛰므로 동기화 대상이 없다).

`DOMAIN_CONTEXT`가 없으면 (phase-setup에서 도메인 매칭 실패) 건너뛴다.

`DOMAIN_CONTEXT`가 있으면, 모드에 따라 **경로 A** 또는 **경로 B**로 분기한다.

### 분기 규칙

```
if HOTFIX 모드이고 Step 0 인수 검증이 REJECT → 건너뛴다 (Must 미충족 상태에서 갱신하면 안 됨)
elif HOTFIX 또는 IMPLEMENT 모드 → 경로 B (커밋 기반 — 인수 검증 결과가 아닌 커밋 단위로 추적)
elif NORMAL 모드이고 Step 0 인수 검증이 ACCEPT → 경로 A
elif NORMAL 모드이고 Step 0 인수 검증이 REJECT → 건너뛴다 (미충족 상태에서 status.md를 ✅로 바꾸면 안 됨)
else → 건너뛴다
```

### 경로 A: 인수 검증 기반 (NORMAL 모드)

NORMAL 모드이고 Step 0 인수 검증이 ACCEPT이면 이 경로를 사용한다.

1. Step 0 인수 검증 결과에서 **통과한 AC 목록**을 추출한다 (예: AC-1, AC-4, AC-7).
2. 매칭된 도메인의 `context/{domain}/status.md`를 Read한다.
3. 통과한 AC와 일치하는 행의 상태를 `⬜`→`✅`로, PR 열에 생성된 PR 링크를 기입한다.
4. AC가 `-`인 행은 변경하지 않는다 (PR 머지 시 수동 판정).
5. Edit으로 status.md를 갱신한다.
6. 갱신 결과를 사용자에게 보고한다:
   ```
   status.md 갱신: ✅ AC-1, AC-4, AC-7 (FR-1, FR-16, FR-19)
   ```

### 경로 B: 커밋 기반 (HOTFIX / IMPLEMENT 모드)

Step 0 인수 검증이 실행되지 않았거나 (PRD 부재, `implement` 모드 등), HOTFIX 모드이면 이 경로를 사용한다.

1. `${GIT_PREFIX} log ${BASE_BRANCH}..HEAD --oneline`로 현재 브랜치의 커밋 목록을 수집한다.
2. 매칭된 도메인의 `context/{domain}/status.md`를 Read한다.
3. status.md에서 `⬜` 상태인 항목을 파싱한다.
4. 커밋 메시지와 `⬜` 항목을 대조하여 매칭 후보를 구성한다:
   - **ID 직접 매칭** (우선): 커밋 메시지에 FR/BR ID(예: `FR-2`, `BR-5`)가 직접 언급된 경우 확정 매칭.
   - **키워드 매칭** (보조): ID가 없으면 커밋 메시지의 핵심 명사와 항목 설명의 명사를 대조하여, 2개 이상 일치 시 후보로 제시.
5. **매칭 후보가 없으면** → 건너뛴다.
6. **매칭 후보가 있으면** → AskUserQuestion으로 사용자에게 확인한다:
   ```
   AskUserQuestion(
     question: "커밋 기반으로 다음 항목의 상태를 갱신할까요?",
     options: [
       { value: "apply", label: "갱신 — 아래 항목을 ✅로 변경합니다" },
       { value: "skip", label: "건너뛰기 — 갱신하지 않고 진행합니다" }
     ],
     description: "매칭된 항목:\n- FR-2: 결제 한도 변경 (⬜ → ✅)\n  근거: feat: 결제 한도 검증 로직 추가 (abc1234)"
   )
   ```
7. 승인 시 `⬜`→`✅` 갱신 + PR 열에 생성된 PR 링크 (있으면) 또는 커밋 해시를 기입한다.

### 공통: context 변경사항 자동 커밋

경로 A 또는 경로 B에서 status.md가 갱신되었으면, context 변경을 별도 커밋으로 기록한다:

1. `${GIT_PREFIX} add context/`로 context 변경사항을 스테이징한다.
2. `${GIT_PREFIX} diff --cached --quiet -- context/`로 실제 변경이 있는지 확인한다.
3. 변경이 있으면 커밋한다:
   ```
   ${GIT_PREFIX} commit -m "docs: [context] {domain} status.md 동기화 — {갱신된 AC 목록}"
   ```
4. 변경이 없으면 (이미 최신이면) 건너뛴다.

> **push 정책**: context 자동 커밋은 로컬에만 생성된다. Step 2(PR 생성)에서 `gx-pull-request` 스킬이 이미 `git push`를 실행했으므로, Step 3~4에서 추가된 context 커밋은 별도 push가 필요하다. GitHub/GitLab에서는 PR이 브랜치를 추적하므로, 추가 push된 커밋은 자동으로 PR diff에 반영된다.
>
> Step 3 또는 Step 4에서 context 커밋이 **1건 이상** 생긴 경우에만 `${GIT_PREFIX} push`를 Step 4 완료 후 1회 실행한다. context 커밋이 0건이면 push를 실행하지 않는다.
> - push 성공: "context 변경이 PR에 반영되었습니다."
> - push 실패: "context 커밋이 로컬에 남아있습니다. 수동으로 `git push`를 실행해주세요. PR 머지 전에 push하지 않으면 context 변경이 유실됩니다."

> **svn인 경우**: 자동 커밋하지 않는다. "status.md가 갱신되었습니다. `svn commit`으로 반영해주세요." 안내만 출력한다.

## Step 4: context 환류 제안

`DOMAIN_CONTEXT`가 없으면 건너뛴다.

`DOMAIN_CONTEXT`가 있으면, 모드에 따라 입력 소스를 결정한다:

| 모드 | 입력 소스 | 추출 가능 후보 |
|------|----------|---------------|
| NORMAL | PRD + 설계서 | glossary, 주제 문서, architecture |
| HOTFIX | diff + 경량 PRD | glossary, architecture |
| IMPLEMENT | diff only | glossary, architecture |

### 후보 추출

**NORMAL 모드** (PRD + 설계서):
1. **glossary 후보**: PRD/설계서에 등장하는 도메인 용어 중, 현재 `glossary.md`에 없는 것을 추출한다.
2. **주제 문서 후보**: PRD 제목과 배경을 기반으로, 주제 문서 생성을 제안한다.
3. **architecture.md 갱신 후보**: 설계서에 새로운 구조적 결정(레이어, 의존관계 등)이 있으면 인덱스 갱신을 제안한다.

**HOTFIX 모드** (경량 PRD + diff):
1. `${GIT_PREFIX} diff ${BASE_BRANCH}..HEAD`에서 변경 내용을 수집한다.
2. **glossary 후보**: 경량 PRD와 diff에서 도메인 용어를 추출하고, 현재 `glossary.md`에 없는 것을 필터링한다.
3. **architecture.md 갱신 후보**: diff에서 새 모듈, 새 레이어, 새 외부 연동이 발견되면 갱신을 제안한다.

**IMPLEMENT 모드** (diff only):
1. `${GIT_PREFIX} diff ${BASE_BRANCH}..HEAD`에서 변경 내용을 수집한다.
2. **glossary 후보**: 새로 등장한 클래스명, 패키지명, 상수명에서 도메인 용어를 추출하고, 현재 `glossary.md`에 없는 것을 필터링한다.
3. **architecture.md 갱신 후보**: 새 모듈, 새 레이어, 새 외부 연동이 diff에서 발견되면 갱신을 제안한다.

### 후보가 없으면 건너뛴다.

### 후보가 있으면

후보 목록을 표시한 후:
```
AskUserQuestion(
  question: "위 항목을 context 문서에 반영할까요?",
  options: [
    { value: "apply", label: "반영 — context 문서를 갱신합니다" },
    { value: "skip", label: "건너뛰기 — 다음 단계로 진행합니다" }
  ]
)
```
- 반영 선택 → 해당 파일 Edit/Write. 주제 문서 생성 시 architecture.md 인덱스에 링크 추가. 반영된 context 변경을 커밋한다:
  1. `${GIT_PREFIX} add context/`로 context 변경사항을 스테이징한다.
  2. `${GIT_PREFIX} diff --cached --quiet -- context/`로 실제 변경이 있는지 확인한다.
  3. 변경이 있으면 커밋: `${GIT_PREFIX} commit -m "docs: [context] {domain} 환류 반영 — {갱신된 항목 목록}"`
  4. 변경이 없으면 건너뛴다.
- 건너뛰기 선택 → 다음 단계 진행.

**임의 반영 금지**: 사용자 승인 없이 context 문서를 수정하지 않는다.

## Step 5: 진행 상태 완료
`${DEV_DIR}/state.md`의 `status`를 `completed`, `phases.complete`를 `completed`로 갱신한다.

## Step 6: 다음 단계

PR이 생성되었으면 완료이다. **PR 머지는 절대 실행하지 않는다** — 머지는 리뷰어가 직접 수행한다.

리뷰 수정 요청에 대비하여 작업환경 유지를 안내한다:
"리뷰 피드백 대응을 위해 현재 브랜치를 유지합니다. 리뷰 완료 후 베이스 브랜치로 전환하세요."
