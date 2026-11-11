> gx-tdd의 조건부 운영 규칙이다. [상태 계약](pipeline-state.md)의 "조건부 운영 규칙" 표에 적힌 시점에만 읽는다. 상대경로는 이 파일의 위치를 기준으로 해석한다.

## 공유 규칙 (조건부)

### gx-work 진입·실행방법 상태 세부

`session`은 GREEN/REFACTOR를 현재 세션에서 수행하며 `--isolated`가 없어야 한다. `subagents`는 implementer 디스패치를 위해 `--isolated`를 기록한다. 최초 실제 방법 선택을 반영할 때만 해당 플래그를 맞추고 다른 플래그는 보존한다. 재개/명시 선택/기존 flags가 충돌하면 근거를 보고하고 해소 전 실행하지 않는다.

원 handoff의 `validate-handoff` 재검증은 같은 run·원문·scope·종료점·승인과 현재 프로젝트 루트를 검사한다. 내부 T계획 작성만으로 요청 진입 승인을 다시 묻지 않는다. 계획 변경은 plan/method 승인만 재검토하며, 요구범위·종료점까지 달라졌으면 그 변경의 진입 승인을 확인한다. 누락된 gx-work 승인이나 false·exit 2·pending을 일반 구현 요청 문구로 보완하지 않는다. 실패가 실제 사용자 결정에 따른 종료점 변경이나 경로 이동 때문일 때만 setup-resume 0.05의 재발급(`reissue`) 뒤 다시 검사한다.

### 핵심 모드 계획 승인 세부

core의 내부 T계획 정본은 `${DEV_DIR}/plan.md`다. 유효한 결합 승인 응답을 implementation-plan-file·plan.md **단독** SHA-256과 plan-approved-run/source/sha256에 연결한다. 결합지문과 단독 해시를 혼동하지 않는다. 같은 실제 응답에서 선택한 session/subagents 또는 초기 명시 선택을 execution-method 필드에 연결하면 implement 1.2~1.3이 재질문 없이 재사용한다. 결합 승인만 유효하고 방법이 없으면 방법만 보완한다. 문서 종료·수정·미응답은 승인/방법을 만들어 넣지 않는다. 원 handoff의 plan-file과 내부 구현계획 포인터는 별개다.

AC/계획 변경 직전 또는 외부 변경·누락을 발견하면 core-plan-status를 pending·승인 지문을 null로 무효화한다. RED/IMPLEMENT·Gate/verify 수리·complete 진입·재개 직전 현재 문서·지문·실제 승인·pending 해제를 확인한다. 필요한 계획·승인 Step만 보완하고 유효한 같은 승인·완료 RGR·setup은 반복하지 않는다. RED/테스트/report·baseline-fingerprint는 보존하며 변경은 core-replanning의 영향 태스크만 처리한다.

미적용 실제 전환 결정/pending은 mode·승인·과거 커서 복원보다 먼저 처리한다. 전체 전환은 setup 없이 execution-phases를 requirements/design/implement/review/complete로 저장하고 새 세대 phase를 pending, phase requirements·step null, verify pending·빈 지문으로 둔다. caller의 mode-transition 신호는 과거 core 루프를 끝내며 일반 완료 표시를 쓰지 않는다. applied의 이후 일반 재개는 새 전체 목록과 **현재 커서**를 유지하고 requirements로 재초기화하지 않는다. 새 명시 phase는 이 과거 목록보다 우선한다. 원 run·진입 승인·요청 포인터·stop-at와 기존 증거는 전이로 바꾸지 않는다.

### 코드 맵 구조

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

### Trust Ledger 구조

```
## Trust Ledger

### 통합 감사 (review)
- [분류/심각도] 항목 설명
  - 근거: ...
  - 권고: ...

### 위험 수용
- [{항목명}] {사유} ({phase/step})
```

### verify 지문 계산·대조

- **계산 규약** (훅·gx-commit·gx-pull-request·라우팅이 동일하게 사용): 임시 인덱스에 워킹트리 전체를 `add -A`한 뒤 `.dev`를 인덱스에서 제거하고 `write-tree`한 **트리 해시**(앞 12자)를 `git rev-parse --short HEAD`와 `:`로 이은 값 (예: `7c9e814:59ca4aacfeab`). **`git diff HEAD`가 아니라 트리 해시**를 쓰는 이유는 신규 파일이 스테이징되면 diff 기반 값이 바뀌어, verify(스테이징 전) → `git add -A` → commit 순서에서 게이트가 오발동하기 때문이다 (RGR은 새 파일 생성이 기본).
- **`.dev/` 제외 이유**: state.md·diff.txt 등 파이프라인 산출물은 코드가 아니며, 포함하면 상태를 기록할 때마다 지문이 스스로 무효화된다 (ignore 누락 저장소에서도 안정).
- **대조는 트리 성분(콜론 뒤)만 수행한다** — HEAD 성분은 기록·추적용이며, 검증된 코드가 그대로 커밋되어 HEAD만 전진한 경우는 일치로 간주한다 (커밋 → PR 정상 경로의 상시 오경고 방지). 단 트리 성분이 `notree`(계산 실패)면 값이 같아도 일치로 보지 않는다 — 코드 동일성이 입증되지 않으므로 보수적으로 재검증을 권고한다.
- **적용 파이프라인**: `pipeline: gx-tdd`가 이 규약을 쓴다. 제거된 pipeline은 재개 전에 intent-routing의 이관 안내로 중단한다.
- **하위 호환**: 필드가 없는 구 세션은 기존 판정(`verify-status`만)으로 동작한다.
- **svn**: git 지문을 계산할 수 없어 대조가 성립하지 않는다. 훅은 이 경우 보수적으로 "재검증 권고"를 안내한다.

### 베이스 브랜치 감지

**svn인 경우** → 베이스 브랜치 개념이 없으므로 건너뛴다 (trunk에서 직접 작업).

**git인 경우:**
`--base`가 지정되었으면 해당 브랜치를 사용한다. 미지정이고 `.claude/config.json`의 `conventions.baseBranch`에 값이 있으면 `git rev-parse --verify --quiet <값>` 또는 `origin/<값>`으로 존재를 확인해, 있으면 묻지 않고 그 값을 쓴다(gx-setup이 저장한 기본 베이스). 없으면 그렇게 한 줄 알리고 아래 자동 감지로 간다. 그 밖에는 자동 감지:
1. `git branch --list main master develop`로 존재하는 브랜치를 확인한다.
2. 존재하는 브랜치가 **2개 이상**이면 → AskUserQuestion으로 사용자에게 선택지 제시 (예: main, develop).
3. 존재하는 브랜치가 **1개**이면 → 해당 브랜치를 베이스로 자동 선택.
4. 하나도 없으면 → AskUserQuestion(자유입력)으로 직접 입력을 요청한다.

확정된 베이스 브랜치를 이후 phase-review (diff 계산), phase-complete (PR 생성)에서 사용한다.

### Q&A 히스토리 관리
Agent prompt 크기를 관리하기 위해:
- Agent에게는 **최신 설계/리뷰 출력만** 전달한다. 이전 버전은 전달하지 않는다.
- 이전 라운드의 질문+답변은 **핵심 결정 사항만 요약**하여 전달한다 (원문 그대로 X).
- 예: "Q: 세션 기반 vs JWT? → A: JWT 선택. Q: 토큰 만료 시간? → A: 30분"

### Context Slicing 규칙
설계서·PRD는 역할별 필요 섹션만 전달한다. 모든 디스패치에 프로젝트 루트 경로를 포함한다. `contextLimits`(config.json) 초과 시 우선순위 낮은 섹션부터 요약·생략.

| 에이전트 | 전달 입력 |
|---|---|
| product-owner (PRD 작성) | ARGS[0]+코드 맵+프로젝트 타입/구조+DOMAIN_CONTEXT(있으면 — 용어·README 핵심·미반영·아키텍처 4요소. 미반영과 겹치면 FR ID 인용)+**"AC는 반드시 Given-When-Then 형식. 자동 테스트로 변환 가능해야 함"** |
| product-owner (인수 검증) | PRD요구사항+수용기준+`DIFF_FILE`+코드 맵 |
| architect | PRD 전체+코드 맵+프로젝트 타입/구조/컨벤션+DOMAIN_CONTEXT(있으면 — 용어·아키텍처만)+REFERENCES(있으면)+**"각 컴포넌트의 테스트 가능성(의존성 주입, 인터페이스 격리)을 고려"** |
| design-critic | 설계초안+PRD+코드맵 |
| test-architect | 설계서+PRD수용기준+코드 맵+**"각 컴포넌트별 단위/통합 테스트 전략 명시 + testability score 1-10 산정"** |
| red-writer | AC(G-W-T)+testability 섹션+테스트 스타일. **기존 프로덕션 코드는 절대 포함하지 않는다**. **UI 태스크에만** `FRONTEND_TESTING_PATH`(`frontend-testing.md`) |
| 세션 IMPLEMENT (기본 경로) | 디스패치 없음 — 오케스트레이터가 RED report·설계서 인터페이스·focused 명령을 직접 읽고 phase-implement "세션 IMPLEMENT 절차"를 수행 |
| implementer | RED report(reports/t{N}-red.md)+인터페이스+focused 테스트 명령+report 경로. **PRD 전체나 설계서 전체는 전달하지 않는다** |
| reviewer | PRD요구사항+수용기준+설계서변경범위+`DIFF_FILE`+코드 맵+컨벤션+품질기준. **"Part 1 verdict 선행. 테스트 재실행 금지"**. **태스크 범위 모드**(phase-implement 2-V): 태스크 AC+`reports/t{N}-diff.txt`+RED/IMPL report+인터페이스만, `model: "sonnet"` |
| security-auditor | PRD 전체+설계서 전체+`DIFF_FILE`+코드 맵+REFERENCES(있으면) |
| gx-verify (스킬, 완료 게이트) | phase-complete Step -1에서 `Skill("oh-my-gx:gx-verify")`로 호출. config.json의 projectTypes 기반으로 테스트/빌드 명령을 직접 실행. 캐시 결과 사용 금지, 0 failures 확인. 에이전트 Task가 아니므로 Context Slicing(입력 전달) 대상이 아니다. |
| researcher | 조사+코드맵(있으면) |
| hacker | 정체+코드맵 |
| simplifier | 정체+설계서+PRD+코드맵 |

### 병렬 실행 규칙
읽기 전용 Agent(product-owner, architect, test-architect, design-critic, reviewer, security-auditor, researcher, hacker, simplifier)는 서로 병렬 실행이 가능하다. 병렬 실행 시:
1. 하나의 메시지에서 여러 `Task()` 호출을 동시에 발행한다.
2. 모든 병렬 Task가 완료된 후 결과를 합산한다 (Gate 로직).
3. 쓰기 주체(red-writer, 세션 IMPLEMENT, implementer)는 다른 쓰기 Agent와 병렬 실행하지 **않는다**. 예외는 phase-implement Step 2의 독립 갈래 병렬 진행(서로 겹치지 않는 프로젝트 루트) 하나이며, 그 절의 갈래별 격리 규칙을 따른다. 갈래 안의 RGR 순서는 아래 4를 그대로 지킨다.
4. **RGR 사이클 내 순차 강제 (Iron Law)**: red-writer → IMPLEMENT(세션 또는 implementer)는 **반드시 순차** 실행한다. 병렬 금지.
   - 이유: red-writer 산출물(실패 테스트 — RED report)이 IMPLEMENT의 입력.
   - 위반 시: 격리가 깨져 Iron Law 1 위반.
5. **review 통합 순서 강제 (Iron Law)**: reviewer 1석이 Part 1 → Part 2를 내부 순서로 수행한다 (개별 2석 디스패치 금지).
   - security-auditor는 reviewer와 **병렬 가능** (서로 독립).
6. RGR/review 사이클 외 읽기 Agent의 병렬은 **읽기 Agent가 이전 Phase의 산출물(설계서 등)만 참조하는 경우** 허용한다.

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

1. `DIFF_FILE = ${DEV_DIR}/diff.txt`. **매 수집 시** `mkdir -p "${DEV_DIR}"`를 실행하여 디렉토리 존재를 보장한다.
2. diff를 파일에 직접 리다이렉트한다 (Bash 결과에 diff가 나타나지 않음):
   ```bash
   git diff --cached -- . ':(exclude).dev' > "${DEV_DIR}/diff.txt"
   ```
3. `wc -l < "${DEV_DIR}/diff.txt"`로 줄 수를 확인한다.
4. 총 변경이 **500줄 이상**이면: `--stat` 요약을 파일 앞에 추가하고, 파일 끝에 "변경된 파일을 Read 도구로 직접 확인하라"는 안내를 추가한다:
   ```bash
   git diff --cached --stat -- . ':(exclude).dev' > "${DEV_DIR}/diff.txt"
   echo "---" >> "${DEV_DIR}/diff.txt"
   echo "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라." >> "${DEV_DIR}/diff.txt"
   ```
5. Agent 프롬프트에는 **파일 경로만 전달**한다:
   ```
   변경사항 diff: ${DEV_DIR}/diff.txt
   이 파일을 Read하여 변경사항을 확인하라.
   ```

이 규칙은 모든 diff 패턴에 적용한다: `git diff --cached` (스테이징), `git diff <base>...HEAD` (브랜치 비교) 등 — **모든 git diff 명령에 `-- . ':(exclude).dev'` pathspec을 붙여 `.dev` 산출물을 리뷰 diff에서 제외한다** (산출물은 공유 대상이지만 코드 리뷰 대상이 아니며, PRD·AC 전문이 diff로 유입되면 reviewer에게 전달되는 diff가 불필요하게 비대해지고 500줄 초과 강등이 빈발한다). svn은 pathspec 제외가 없으므로 diff 수집 후 리뷰 에이전트 프롬프트에 "`.dev` 경로의 변경은 리뷰 대상에서 제외하라"를 명시한다.
