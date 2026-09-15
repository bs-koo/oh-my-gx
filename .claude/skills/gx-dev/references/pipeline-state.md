> gx-dev/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태·질문·phase 결정을 추정하지 않는다. 상대경로는 gx-dev/SKILL.md 위치를 기준으로 해석한다.

## 코드 맵

오케스트레이터가 관리하는 누적 문서. 관련 파일의 경로와 역할을 기록한다.

**구조:**
```
## 코드 맵: <기능 설명>

### 핵심 파일
- <파일경로:라인> → 역할 설명
- ...

### 참조 파일
- <파일경로:라인> → 역할 설명
- ...

### 설정
- <파일경로> → 역할 설명
- ...
```

**생성**: phase-setup의 Step 4에서 초기 맵을 생성한다.
**누적**: 각 agent 출력에 "탐색 추가 항목" 섹션이 있으면 해당 항목을 맵에 append한다. 누적 맵은 **최대 25개**로 제한한다. 초과 시 참조 파일부터 제거한다.
**저장**: 코드 맵이 갱신될 때마다 `${DEV_DIR}/codemap.md`에 Write한다.
**전달**: 모든 agent 호출 시 현재 코드 맵을 프롬프트에 포함한다.

## Trust Ledger (신뢰 원장)

security-auditor의 감사 결과를 누적하는 문서. 오케스트레이터가 관리한다.

**구조:**
```
## Trust Ledger

### 통합 감사 (review)
- [분류/심각도] 항목 설명
  - 근거: ...
  - 권고: ...
```

**생성**: phase-review에서 ZT 통합 감사 완료 시 생성.
**저장**: `${DEV_DIR}/trust-ledger.md`에 저장한다.
**전달**: PR 본문에 감사 결과 요약으로 포함한다.

---

## 공유 규칙

### 작업 경로 기준
phase-setup에서 결정된 변수를 이후 모든 Phase에서 사용한다:
- `VCS_TYPE`: `.claude/config.json`의 `"vcs"` 값. `"git"`, `"svn"`, 또는 `""` (미설정, `"git"`으로 취급). phase-setup에서 읽어 이후 모든 Phase에서 사용한다. VCS별 명령어 분기의 기준이 된다.
- `GIT_PREFIX`: `VCS_TYPE`이 `"git"`이면 `git`, `"svn"`이면 `svn`. 소비 프로젝트 루트에서 직접 실행한다.
- `PROJECT_ROOT`: phase-setup Step -1이 Git `--show-toplevel` > SVN `wc-root` > 현재 디렉토리 절대경로 순으로 결정한 값.
- `DEV_DIR`: 브랜치별 산출물 디렉토리. `.dev/{branch-slug}` 형식. branch-slug는 브랜치명에서 `/`를 `-`로 치환한 값 (예: `feat/login` → `.dev/feat-login`). phase-setup Step 5에서 브랜치 결정 후 설정한다. **SVN은 브랜치가 없어 git 브랜치명과 동일 규칙으로 작업 slug를 만들어 `.dev/{slug}`를 쓰고(기능별 격리), 활성 slug를 `.dev/.active`에 기록한다 — 훅·라우팅·verify가 이 포인터로 활성 작업의 state.md를 찾는다(`.active` 부재·공백 시 `.dev/trunk` 폴백).** 이후 모든 Phase에서 산출물 Read/Write 경로의 기준이 된다.
- `BASE_BRANCH`: phase-setup Step 2에서 결정된 베이스 브랜치 (예: `main`, `develop`). state.md의 `base` 필드에 기록된다. SVN인 경우 미사용. phase-setup Step 3-0(context 최신화), phase-complete Step 3(경로 B 커밋 로그 비교), Step 4(diff 기반 환류)에서 사용한다.
- `DIFF_FILE`: 변경사항 diff를 저장하는 파일 경로. `${DEV_DIR}/diff.txt`. Diff 수집 규칙에 따라 phase-implement(자기점검), phase-review, phase-complete에서 갱신된다.
- `DOMAIN_CONTEXT`: phase-setup Step 3(도메인 컨텍스트 탐색)에서 `context/*/PROJECTS.md` 매칭으로 로드된 4요소 — 용어(glossary)·README 핵심(배경·안 하면·사용자/규모·성공 기준)·status.md 미반영 항목·아키텍처. 매칭되지 않으면 빈 상태.
- `REFERENCES`: phase-setup Step 3(외부 규격 참조 탐색)에서 `references/` 디렉토리를 탐색하여 수집한 외부 규격 문서 목록(파일 경로 + 한줄 설명). `references/` 디렉토리가 없으면 빈 상태. 빈 상태이면 에이전트 프롬프트에 포함하지 않는다.
- `MODEL_PROFILE`: 모델 프로파일 (`standard`/`eco`). phase-setup Step 1.5에서 결정하며 state.md의 `model-profile`에 기록된다. 디스패치 적용 규칙은 아래 "모델 프로파일" 섹션 참조.
- Agent에게 `PROJECT_ROOT`를 전달해 파일 도구의 기준점으로 쓰고, Git·SVN·빌드·테스트 명령도 그 디렉토리에서 실행한다.

### 모델 프로파일 (MODEL_PROFILE)

에이전트 디스패치의 모델 수준. 절차 축(mode)과 **직교**하며 Phase 구성·게이트에 영향을 주지 않는다.

- 결정 우선순위: `--eco`/`--standard` 플래그 > ARGS[0] 자연어(`에코 모드`/`에코로`/`절약 모드` → eco) > **의도 파싱 Step 3 질문 답변**(모드 확인 질문에 프로파일 질문이 함께 제시된 경우) > config.json `modelProfile` > 기본 `standard`. phase-setup Step 1.5가 이 순서로 확정해 state.md에 기록한다.
- **standard (표준)**: Agent 팀 표의 모델 그대로 디스패치한다.
- **eco (에코 모드)**: **design-critic과 coder**를 Task 호출 시 `model: "sonnet"` 파라미터로 오버라이드하여 디스패치한다 — Task의 model 파라미터는 에이전트 정의(frontmatter)보다 우선한다. **architect는 eco에서도 opus를 유지한다** — 설계 오류는 게이트(빌드·테스트)가 방어하지 못하고 하류 전체로 전파되는 유일한 실패인 반면 호출은 1~2회로 가장 적다 (게이트 4겹이 방어하는 생산자 coder와, 실패 모드가 '놓침'인 검증자 design-critic만 하향). 이미 sonnet인 에이전트는 그대로 유지한다 (haiku 강등 금지). 이 규칙은 **모든 Phase의 모든 Task 디스패치에 적용**된다 — phase 파일에 개별 표기가 없어도 적용한다.
- 게이트(빌드·테스트·Mechanical Gate)는 모델 무관 기계 검증이므로 eco에서도 동일하게 유지된다.
- 오케스트레이터가 직접 수행하는 단계(핵심 모드 직접 구현, AC 자가 검증 등)는 메인 세션 모델을 따른다 — 플러그인이 제어하지 않는다.
- `--resume` 시 state.md의 `model-profile`을 복원한다. 재개 중 프로파일 변경은 지원하지 않는다.

### 베이스 브랜치 감지
`--base`가 지정되었으면 해당 브랜치를 사용한다. 미지정이면 자동 감지:
1. `git branch --list main master develop`로 존재하는 브랜치를 확인한다.
2. 존재하는 브랜치가 **2개 이상**이면:
   ```
   AskUserQuestion(
     questions: [{
       question: "베이스 브랜치를 선택해주세요.",
       header: "베이스 브랜치",
       options: [
         { label: "<branch1>", description: "감지된 브랜치" },
         { label: "<branch2>", description: "감지된 브랜치" }
       ],
       multiSelect: false
     }]
   )
   ```
3. 존재하는 브랜치가 **1개**이면 → 해당 브랜치를 베이스로 자동 선택.
4. 하나도 없으면:
   ```
   AskUserQuestion(
     questions: [{
       question: "main, master, develop 중 해당 브랜치가 없습니다. 베이스 브랜치명을 직접 입력해주세요.",
       header: "베이스 브랜치",
       options: [
         { label: "main", description: "기본 브랜치" },
         { label: "master", description: "기본 브랜치 (레거시)" }
       ],
       multiSelect: false
     }]
   )
   ```

확정된 베이스 브랜치를 이후 phase-review (diff 계산), phase-complete (PR 생성)에서 사용한다.

### Q&A 히스토리 관리
Agent prompt 크기를 관리하기 위해:
- Agent에게는 **최신 설계/리뷰 출력만** 전달한다. 이전 버전은 전달하지 않는다.
- 이전 라운드의 질문+답변은 **핵심 결정 사항만 요약**하여 전달한다 (원문 그대로 X).
- 예: "Q: 세션 기반 vs JWT? → A: JWT 선택. Q: 토큰 만료 시간? → A: 30분"

### Agent 결과 전달 규칙 (컨텍스트 경량화)
Agent 출력을 사용자에게 전달할 때, **Phase 상태에 따라** 전문 표시 여부를 결정한다:
- **Q&A Phase** (requirements, design): Agent 출력의 첫 표시는 항상 **전문 표시**한다 (사용자가 산출물을 검토할 수 있도록). Phase 파일의 구체적인 표시 규칙이 이 일반 규칙보다 우선한다.
- **Q&A Phase 완료 보고**: 확정된 산출물을 파일에 저장하고, 사용자에게는 **요약만** 보고한다 ("PRD 확정. ${DEV_DIR}/prd.md에 저장됨" 등).
- **Q&A 없는 Phase** (implement, review, complete): Agent 출력의 **요약만** 사용자에게 표시한다. 전문은 파일에 저장하거나 변수에 보관한다.

이후 Phase에서 이전 산출물이 필요하면 **파일을 Read하여 Agent prompt에 포함**하되, 오케스트레이터 자신의 출력에는 포함하지 않는다. 각 Phase 파일에서 구체적인 요약 포맷을 정의한다.

### 문서 보관
- phase-requirements 완료 시 확정된 PRD를 `${DEV_DIR}/prd.md`에 저장한다.
- phase-design 완료 시 확정된 설계 문서를 `${DEV_DIR}/design.md`에 저장한다.
- Trust Ledger를 `${DEV_DIR}/trust-ledger.md`에 저장한다.
- 코드 맵을 `${DEV_DIR}/codemap.md`에 저장한다 (갱신 시마다).
- 자기점검 결과를 `${DEV_DIR}/self-check.md`에 저장한다 (phase-implement 자기점검 완료 시).
- 핵심 모드: AC를 `${DEV_DIR}/ac.md`에, 변경 요약을 `${DEV_DIR}/summary.md`에 저장한다 (phase-core Step 0 / Step 3).
- phase-design, phase-implement, phase-review 진입 시 해당 파일들을 Read하여 에이전트 프롬프트에 사용한다.
- `.dev/` 산출물은 **협업 공유 대상**으로 커밋에 포함한다 (`.gitignore`에 추가하지 않음). `.gitignore` 보강은 phase-setup Step 6에서 config `projectTypes.artifacts` 기준으로 빌드 아티팩트만 처리한다.

### 진행 상태 추적 (state.md)
파이프라인 진행 상태를 `${DEV_DIR}/state.md`에 기록하여 세션 재개를 지원한다.

**state.md 구조:**
```yaml
phase: implement
status: in_progress
model-profile: standard
vcs-type: git
branch: JIRA-123
base: main
dev-dir: .dev/JIRA-123
project-type: java-spring
project-root: ./
args: "[JIRA-123] 로그인 기능 추가"
flags: --core              # 의도 파싱 플래그. 자연어 RALPH 추출도 --ralph로 정규화해 기록 (phase-setup Step 7) — phase-implement 전환 절의 판정 키
started: 2026-02-17T10:30:00
current-step: "자기점검"
phases:
  setup: completed
  requirements: completed
  design: completed
  implement: in_progress
steps:
  implement:
    - coder 구현: completed
    - 자기점검: in_progress
  review:
    - mechanical-gate: pending
    - qa-review-1: pending
execution-log:
  - phase: implement
    agent: coder
    result: completed
    steps-reported: 5/5
  - phase: implement
    agent: qa-manager (자기점검)
    result: "Critical 1건, Warning 2건"
  - phase: implement
    agent: coder (수정)
    result: "Critical 1건 해소"
  - phase: review
    step: mechanical-gate
    result: "build ✓, test ✓"
  - phase: review
    agent: qa-manager
    result: "CERTAIN 0건, QUESTION 1건"
  - phase: review
    agent: security-auditor
    result: "CRITICAL 0건"
```

**갱신 규칙:**
- Phase 진입 시: `phase: {name}`, `phases.{name}: in_progress`로 갱신.
- Phase 완료 시: `phases.{name}: completed`로 갱신.
- Phase 내 주요 Step 시작/완료 시: `current-step`과 `steps` 갱신.
- `--resume` 시 `current-step`에서 재개한다 (Phase 처음부터가 아닌 중단 Step부터).
- 에이전트 호출 완료 시: `execution-log`에 엔트리 추가 (agent명, result 요약).
- Gate 실행 결과도 `execution-log`에 기록한다.
- 정체 감지 시: 해당 `execution-log` 엔트리에 `stagnation: {패턴}` 필드를 추가한다.
- phase-complete 완료 시: `status: completed`로 갱신.
- 새 파이프라인 시작 시 기존 state.md를 덮어쓴다.

### Context Slicing 규칙
설계서와 PRD를 Agent에게 전달할 때, 역할에 따라 필요한 섹션만 전달하여 컨텍스트 효율을 높인다:
- **product-owner (PRD 작성)**: ARGS[0] + 코드 맵 + 프로젝트 타입/구조 + 프로젝트 루트 경로 + DOMAIN_CONTEXT (있으면 — 4요소 전부. 미반영과 겹치면 FR ID 인용)
- **product-owner (인수 검증)**: PRD의 "요구사항" + "수용 기준" + diff 파일 경로 (`DIFF_FILE`) + 코드 맵
- **architect (설계)**: PRD 전체 + 코드 맵 + 프로젝트 타입/구조/컨벤션 + 프로젝트 루트 경로 + DOMAIN_CONTEXT (있으면 — 용어·아키텍처만) + REFERENCES (있으면)
- **coder (구현)**: 설계서 전체 + 코드 맵 + 프로젝트 루트 경로 + REFERENCES (있으면). 핵심 모드이면 설계서 대신 ac.md 전체 + 코드 맵 (phase-core Step 1의 규모 판정에서 coder 디스패치가 결정된 경우).
- **coder (배치 모드 구현)**: 담당 단계의 설계서 섹션 + 담당 파일 목록 + 이전 배치 결과 요약 (있으면) + 병렬 실행 안내 (병렬 배치인 경우) + 코드 맵 + 프로젝트 루트 경로 + REFERENCES (있으면). 설계서 전체 대신 담당 단계만 전달하므로 전체 모드보다 컨텍스트가 작다.
- **coder (수정)**: 수정 항목 목록 + 수정 방안 + 코드 맵 + 프로젝트 루트 경로
- **qa-manager**: PRD의 "요구사항" + "수용 기준" + 설계서의 "변경 범위" 섹션 + 코드 맵 + REFERENCES (있으면)
- **qa-manager (자기점검)**: PRD의 "요구사항" + "수용 기준" 섹션만 (스펙 충족 확인용). 전체 모드 전용 — 핵심 모드는 자기점검 대신 Mechanical Gate + AC 자가 검증을 사용한다
- **security-auditor (통합 감사)**: PRD 전체 + 설계서 전체 + diff 파일 경로 (`DIFF_FILE`) + 코드 맵 + REFERENCES (있으면)
- **design-critic (설계 비판)**: 설계서 초안 + PRD + 코드 맵 + 프로젝트 루트 경로
- **researcher (독립 조사)**: 조사 요청 + 코드 맵 (있으면) + 프로젝트 루트 경로
- **hacker (제약 우회)**: 정체 상황 설명 (에러 메시지, 시도한 접근) + 코드 맵 + 프로젝트 루트 경로
- **simplifier (복잡도 제거)**: 정체 상황 설명 + 설계서 + PRD + 코드 맵

각 에이전트에 전달하는 입력 크기가 `.claude/config.json`의 `contextLimits`를 초과하면, 우선순위가 낮은 섹션부터 요약 또는 생략한다.

### 병렬 실행 규칙
읽기 전용 Agent(product-owner, architect, design-critic, qa-manager, security-auditor, researcher, hacker, simplifier)는 서로 병렬 실행이 가능하다. 병렬 실행 시:
1. 하나의 메시지에서 여러 `Task()` 호출을 동시에 발행한다.
2. 모든 병렬 Task가 완료된 후 결과를 합산한다 (Gate 로직).
3. 쓰기 Agent(coder)는 다른 쓰기 Agent와 병렬 실행하지 않는다.
   **예외 — 배치 모드 병렬**:
   - 같은 배치 내 coder들은 병렬 실행이 허용된다.
   - 전제 조건: 파일 배타적 잠금이 보장될 것 (phase-implement Step 1.5에서 검증 완료).
     동일 파일을 수정하는 단계는 같은 배치에 배정되지 않는다.
   - 배치 순서 보장: B1 완료 → B2 시작. 배치 간 순서를 건너뛰지 않는다.
4. coder와 읽기 전용 Agent의 병렬은 **읽기 Agent가 이전 Phase의 산출물(설계서 등)만 참조하는 경우** 허용한다. 현재 구현 중인 코드를 참조하는 읽기 Agent와는 병렬하지 않는다.

### 정체 감지 + 에스컬레이션

phase-implement(구현→자기점검 루프)와 phase-review(QA→수정→재리뷰 루프)에서 적용한다.
각 루프의 최대 반복은 기존과 동일하다. 정체 감지 시 반복을 소진하지 않고 에스컬레이션으로 전환한다.

#### 감지 패턴

| 패턴 | 감지 기준 | 유형 |
|------|----------|------|
| SPINNING | 동일 에러 메시지가 2회 연속 반복 | 기계적 (텍스트 비교) |
| OSCILLATION | 접근법 A→B→A 왕복이 감지됨 | 정성적 (LLM 판단) |
| NO_DRIFT | 이전 반복과 비교해 코드 변경이 실질적으로 없음 (diff 비교) | 반기계적 (diff stat) |
| DIMINISHING_RETURNS | 수정 범위가 줄어드는데 테스트/리뷰 결과가 개선되지 않음 | 정성적 (LLM 판단) |

#### 에스컬레이션 경로

| 감지 패턴 | 1차 대응 | 2차 대응 (1차 실패 시) |
|----------|---------|---------------------|
| SPINNING | hacker에 제약 우회 분석 위임 | researcher에 근본 원인 분석 위임 |
| OSCILLATION | architect에 설계 재검토 요청 | 사용자에게 두 접근법 제시, 선택 요청 |
| NO_DRIFT | hacker에 제약 식별 + 우회 경로 요청 | researcher에 코드베이스 탐색 위임 |
| DIMINISHING_RETURNS | simplifier에 복잡도 분석 + 범위 축소 요청 | 사용자에게 현재 상태 보고, 방향 전환 여부 확인 |

### Gate 로직
phase-review.md의 Step 3~4에 정의. QA + ZT 결과를 합산하고 심각도별로 처리한다.

### Diff 수집 규칙
Agent에게 변경사항 diff를 전달할 때, 메인 컨텍스트 절약을 위해 **파일 리다이렉트 + 경로 전달**을 사용한다.

**핵심 원칙**: diff 출력이 Bash 결과로 메인 컨텍스트에 진입하지 않도록, **셸 리다이렉트로 파일에 직접 쓴다**.

#### 수집 절차

1. `DIFF_FILE = ${DEV_DIR}/diff.txt`. **매 수집 시** `mkdir -p ${DEV_DIR}`를 실행하여 디렉토리 존재를 보장한다.
2. diff를 파일에 직접 리다이렉트한다 (Bash 결과에 diff가 나타나지 않음):
   ```bash
   git diff --cached -- . ':(exclude).dev' > ${DEV_DIR}/diff.txt
   ```
3. `wc -l < ${DEV_DIR}/diff.txt`로 줄 수를 확인한다.
4. 총 변경이 **500줄 이상**이면: `--stat` 요약을 파일 앞에 추가하고, 파일 끝에 "변경된 파일을 Read 도구로 직접 확인하라"는 안내를 추가한다:
   ```bash
   git diff --cached --stat -- . ':(exclude).dev' > ${DEV_DIR}/diff.txt
   echo "---" >> ${DEV_DIR}/diff.txt
   echo "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라." >> ${DEV_DIR}/diff.txt
   ```
5. Agent 프롬프트에는 **파일 경로만 전달**한다:
   ```
   변경사항 diff: ${DEV_DIR}/diff.txt
   이 파일을 Read하여 변경사항을 확인하라.
   ```

이 규칙은 모든 diff 패턴에 적용한다: `git diff --cached` (스테이징), `git diff <base>...HEAD` (브랜치 비교) 등 — **모든 git diff 명령에 `-- . ':(exclude).dev'` pathspec을 붙여 `.dev` 산출물을 리뷰 diff에서 제외한다** (산출물은 공유 대상이지만 코드 리뷰 대상이 아니며, PRD·AC 전문이 diff로 유입되면 qa-manager에게 전달되는 diff가 불필요하게 비대해지고 500줄 초과 강등이 빈발한다). svn은 pathspec 제외가 없으므로 diff 수집 후 리뷰 에이전트 프롬프트에 "`.dev` 경로의 변경은 리뷰 대상에서 제외하라"를 명시한다.
