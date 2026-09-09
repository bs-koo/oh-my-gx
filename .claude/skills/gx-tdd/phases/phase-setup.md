# phase-setup: 작업환경 준비

## Step 0: 진행 중 작업 감지

ARGS[0]이 있고 `--resume`이 없으면 새 작업이다 — 이 Step을 건너뛰고 Step 1로 진행한다.

그 외(`--resume` 지정, 또는 ARGS[0] 부재)에는 `Read("setup-resume.md")`를 수행한다. 그 파일이 state.md 탐색·재개 정합성 체크(0.1)·"이어서 진행" 복원·구 버전 세션 방어·`--work` 세션의 착수 기록 보정을 담당한다. 재개가 확정되면 phase-setup의 나머지 Step(1~7)을 건너뛴다.

## Step 1: VCS 확인

`.claude/config.json`의 `"vcs"` 필드를 읽어 `VCS_TYPE`을 결정한다. **config.json이 없거나 파싱 불가하면** `VCS_TYPE`을 잠정 `"git"`으로 두고 진행하며, 파일 존재·자동 생성·손상 검증은 Step 3.0 config 가드에서 정식 처리한 뒤 `vcs` 값으로 재확정한다 (config가 늦게 생성되어도 부트스트랩이 깨지지 않도록).

**git인 경우** (vcs가 `"git"` 또는 `""` 미설정):
- `git rev-parse --is-inside-work-tree` 확인.
- 성공 → `VCS_TYPE` = `"git"`, `GIT_PREFIX` = `git`.
- 실패 → AskUserQuestion: "Git 저장소가 아닙니다. `git init`으로 생성할까요?"
  - 예 → `git init` 실행 후 계속.
  - 아니오 → 중단.

**svn인 경우:**
- `svn info` 확인.
- 성공 → `VCS_TYPE` = `"svn"`, `GIT_PREFIX` = `svn`.
- 실패 → "SVN 작업 복사본이 아닙니다." 출력 후 중단.

## Step 1.5: 모델 프로파일 결정

`MODEL_PROFILE`을 결정한다 (우선순위 순 — 먼저 매칭된 것 사용):
1. 플래그: `--eco` → `eco`, `--standard` → `standard`
2. ARGS[0] 자연어: `에코 모드`/`에코로`/`절약 모드` 포함 → `eco` (단독 명사 `에코`는 오탐 방지를 위해 제외)
3. 의도 파싱 Step 3에서 프로파일 질문에 답한 경우 → 그 답변 (표준 → `standard`, 에코 → `eco`)
4. `.claude/config.json`의 `"modelProfile"` 값 (`"eco"` / `"standard"`) — config.json이 없거나 파싱 불가하면 건너뛴다 (Step 3.0에서 재확정)
5. 그 외 (미설정·빈 값·config 부재) → `standard`

config.json이 아직 없으면(부트스트랩) 플래그·자연어·질문 답변이 없을 때 잠정 `standard`로 두고, **Step 3.0 config 가드에서 config 로드 후 `modelProfile` 값으로 재확정한다** (Step 1의 vcs 재확정과 동일 패턴).

`eco`로 결정되면 안내한다: "에코 모드로 실행합니다 — 에이전트 디스패치가 sonnet 중심으로 하향됩니다 (절차·게이트·Iron Law는 동일). 더 큰 절감을 원하면 실행 전 세션 모델도 sonnet으로 바꾸세요 — 그래야 오케스트레이터와 인라인 단계(setup·complete 등)까지 sonnet으로 실행됩니다. (에코는 에이전트 디스패치만 낮추며, 오케스트레이터/메인 세션 모델은 플러그인이 제어하지 못합니다.)"
`standard`로 결정되면 안내한다: "표준 프로파일 — 에이전트를 frontmatter 모델대로 디스패치합니다 (architect·coder·design-critic·test-architect·reviewer 등 opus 에이전트는 세션 모델과 무관하게 opus로 실행). 세션 모델을 sonnet으로 낮춰 절감하려면 표준이 아니라 eco를 쓰세요 — 표준은 이 opus 에이전트들을 그대로 유지하므로 절감 효과가 제한적입니다."
결정 값은 Step 7에서 state.md `model-profile`에 기록한다. 디스패치 적용 규칙은 SKILL.md 공유 규칙 "모델 프로파일" 참조.

## Step 2: 베이스 브랜치 결정

**svn인 경우** → 건너뛴다. SVN은 브랜치 없이 trunk에서 직접 작업하며, 자동 stash도 수행하지 않는다 (SVN은 stash 개념이 없음). 최신화는 Step 5의 `svn update`로 수행한다.

**git인 경우:**
공유 규칙의 "베이스 브랜치 감지"에 따라 결정한다.

결정 후 베이스 브랜치를 최신 상태로 동기화한다. **작업 중 변경사항은 자동 stash로 보호한다.**

### 2.1 자동 stash 보호

`git checkout`/`git pull` 전에 워킹 디렉토리의 미커밋 변경을 보존하고 워킹 디렉토리를 깨끗하게 비운다.

1. `git status --porcelain` 실행. 결과가 비어 있지 않으면 미커밋 변경이 존재한다.
2. 변경이 있으면:
   - `git stash push -u -m "gx-tdd-auto-$(date +%s)"` 실행. `-u` 옵션으로 untracked 파일까지 포함해 워킹 디렉토리를 비우고 변경을 보관한다.
   - (참고) `git stash create`/`store` 조합은 워킹 디렉토리를 비우지 않으므로 이후 `checkout` 충돌을 유발한다. 반드시 `push -u`만 사용한다.
   - `AUTO_STASHED=true`로 기록하고 `git stash list` 최상단 ref를 state.md `execution-log`의 `auto-stash: <ref>` 엔트리에 저장한다.
3. 변경이 없으면 `AUTO_STASHED=false`.

### 2.2 베이스 브랜치 동기화

1. `git remote get-url origin`으로 remote 존재를 확인한다. 없으면 pull 단계만 건너뛴다.
2. `git checkout <base-branch>`를 실행한다. 실패 시 경고를 표시하고 2.3으로 진행한다.
3. checkout 성공 시, `git pull origin <base-branch>`를 실행한다. pull 실패 시 (네트워크 오류 등) 경고를 표시하고 현재 로컬 상태로 계속 진행한다.

### 2.3 stash 복원

Step 5 (작업 브랜치 생성)가 완료된 후에만 stash를 복원한다. 그 전에 복원하면 베이스 브랜치로 변경이 섞일 수 있다.

1. `AUTO_STASHED=true`이면 **Step 5 종료 시점**에 `git stash pop` 실행.
2. pop 충돌 발생 시 사용자에게 보고하고 AskUserQuestion:
   - "stash를 유지하고 수동 해결" → **중단 전에 `${DEV_DIR}/state.md` 골격을 먼저 Write한다** (`pipeline: gx-tdd`, `status: in_progress`, `auto-stashed: true`, execution-log에 `auto-stash: <ref>` — `DEV_DIR`이 아직 미정이면(2.3은 Step 6.5보다 먼저 실행된다) Step 6.5의 규칙대로 `.dev/{branch-slug}`를 먼저 확정하고 `mkdir -p`한 뒤 Write한다 — 골격이 없으면 `--resume`이 재개할 작업을 찾지 못한다). 이후 conflict 상태를 유지한 채 파이프라인을 일시 중단하고, 사용자에게 stash ref와 수동 복원 명령(`git stash pop`)을 안내한다. 사용자가 해결 후 재개 지시.
   - "stash를 drop하고 계속" → `git stash drop`으로 버리고 다음 단계 진행. 위험 수용을 state.md에 기록.
3. 복원 성공 시 `AUTO_STASHED=false`로 초기화하고 execution-log에 `auto-stash-restored` 기록.

## Step 3: 프로젝트 정보 수집
`PROJECT_ROOT = ./` (현재 디렉토리).

### 3.0 config.json 가드 (필수 선행, 재시도 1회 제한)

`test -f .claude/config.json`로 존재 여부를 확인한다.

**Iron Law (무한 루프 방지)**: `CONFIG_SETUP_ATTEMPTS` 변수로 setup 시도 횟수를 추적한다. 초기값 0. setup 호출마다 +1. **2 이상이면 자동 재시도 금지** (사용자 직접 해결 요구).

- **부재 시**:
  1. `CONFIG_SETUP_ATTEMPTS` 확인. **≥ 1이면 자동 재시도 금지** → 다음 안내 후 중단:
     ```
     "/oh-my-gx:gx-setup을 1회 실행했지만 config.json이 여전히 없습니다.
     원인:
     - 플러그인 번들 템플릿 누락 (gx-setup 기준 ../../config.json)

     수동 해결:
       cp <플러그인 경로>/.claude/config.json .claude/config.json

     해결 후 /oh-my-gx:gx-tdd를 다시 실행해주세요."
     ```
     파이프라인 중단.
  2. `CONFIG_SETUP_ATTEMPTS` == 0이면 AskUserQuestion — "`.claude/config.json`이 없습니다. `/oh-my-gx:gx-setup`으로 자동 생성할까요?"
     - "자동 생성" → `CONFIG_SETUP_ATTEMPTS = 1` 갱신 후 `Skill("oh-my-gx:gx-setup")` 호출. 생성 완료 후 다시 3.0 검증 (단, 위 재시도 가드가 작동하여 무한 루프 방지).
     - "직접 생성 후 재실행" → 파이프라인 중단.
- **존재 시**: Read하여 `vcs`, `modelProfile`, `projectTypes`, `sensitiveFilePatterns`, `buildArtifactPatterns`, `timeouts`, `contextLimits`를 변수에 로드. **Step 1에서 config 부재로 `VCS_TYPE`을 git으로 잠정했다면 여기서 `vcs` 값으로 재확정한다** (이후 Phase에 반영). Step 1.5에서 플래그·자연어·질문 답변 없이 잠정 `standard`였다면 `modelProfile` 값(비어있으면 `standard` 유지)으로 `MODEL_PROFILE`을 재확정한다.
- JSON 파싱 실패 시: "config.json이 손상되었습니다. 백업 후 재설정하세요." 출력 후 중단.

### 3.0.5 작업 계획 참조 (`--work` 사용 시)

의도 파싱이 `--work {ID}`(플래그 또는 WORK 추출)로 작업 ID를 확정했으면 `Read("setup-work.md")`의 "작업 계획 참조" 절을 수행한다 — 계획 행에서 도메인·요구사항·브랜치명을 확정하고 의존·중복 착수를 확인하며, Step 7에서 state.md에 `work-id`를 기록한다. 작업 ID가 없어도 `.dev/plan.md`가 존재하면 같은 파일의 "계획이 있으나 작업 ID가 지정되지 않은 경우" 소절만 수행한다 (요청을 계획의 대기 작업과 대조). 작업 ID도 계획 파일도 없으면 이 Step을 건너뛴다.

### 3.1 병렬 수집

아래 5개 작업은 서로 독립적이므로 **병렬로 실행**한다:
1. **프로젝트 타입 감지**: `.claude/config.json`의 `projectTypes`에서 detect 필드와 매칭한다 (예: `build.gradle.kts` → `java-spring`, `package.json` → `node`, `Makefile` → `c-make`). 여러 타입이 감지되면 모두 기록한다. **매칭 실패 시**: gx-setup의 "프로젝트 타입 등록" 절차(빌드 파일 스캔 → 힌트 카탈로그 `Read("../../gx-setup/references/project-type-hints.md")` 제안 → 사용자 확인 → config 기록 → 권한 등록 → 하네스 확인)를 인라인으로 1회 실행한다. 사용자가 등록을 건너뛰면 타입 미상으로 진행한다 (이후 게이트는 fail-closed 동작 — 조용한 통과 없음).
2. **디렉토리 구조 수집**: `PROJECT_ROOT`의 최상위 2레벨 디렉토리 구조를 수집한다.
3. **CLAUDE.md 확인**: `PROJECT_ROOT`에 CLAUDE.md가 있으면 읽어서 코딩 컨벤션을 확보한다.
4. **도메인 컨텍스트 탐색**: 현재 레포와 매칭되는 도메인 컨텍스트를 찾는다.
   - **git**: `git remote get-url origin`으로 레포명을 추출한다 (예: `xx/asset-factory-api`).
   - **svn**: `svn info --show-item url`로 작업 복사본 URL을 추출하고, `trunk`/`branches`/`tags`를 제외한 마지막 경로 세그먼트를 레포명으로 사용한다 (단일 저장소 다중 프로젝트 구조 대응). 추출이 모호하면 로컬 디렉토리명(`basename $(pwd)`)을 폴백으로 사용한다.
   - `context/*/PROJECTS.md`를 Grep하여 해당 레포를 참조하는 도메인을 찾는다.
   - 매칭되면 해당 도메인의 네 파일을 Read하여 `DOMAIN_CONTEXT`를 **4요소**로 구성한다 (우선순위 순 — `contextLimits` 초과 시 역할별 슬라이스 안에서 뒤 요소부터 요약하고, 요약으로도 넘치면 생략한다):
     1. **용어**: `glossary.md` 전체
     2. **README 핵심**: `README.md`의 `## 배경`·`## 안 하면 어떻게 되는가`·`## 사용자와 규모`·`## 성공 기준` 네 절 (없는 절은 건너뛴다)
     3. **미반영 항목**: `status.md`에서 상태 열이 `⬜`인 행 전체 (FR ID·설명·AC 열 포함. 0건이면 "미반영 없음")
     4. **아키텍처**: `architecture.md` 전체
   - `context/` 디렉토리가 없거나 매칭되지 않으면 `DOMAIN_CONTEXT`는 빈 상태로 진행한다.
     사용자에게 안내: "도메인 컨텍스트가 없습니다. `context/` 디렉토리를 생성하고 `/oh-my-gx:gx-context`로 도메인을 등록하면 이후 작업에서 용어/아키텍처를 참조할 수 있습니다."
   - `DOMAIN_CONTEXT`는 이후 agent 프롬프트에 "도메인 컨텍스트"로 포함한다 — product-owner는 4요소 전부, architect·design-critic·test-architect는 용어·아키텍처만 (SKILL.md Context Slicing 표).
5. **외부 규격 참조 탐색**: 프로젝트 루트에 `references/` 디렉토리가 있는지 확인한다.
   - `references/` 디렉토리가 존재하면:
     a. 디렉토리 내 파일 목록을 수집한다 (하위 디렉토리 포함).
     b. 각 파일에서 한줄 설명을 추출한다:
        - `.md` 파일: 첫 번째 `#` 헤딩 텍스트
        - `.txt` 파일: 첫 번째 비공백 줄
        - 그 외 (`.pdf` 등): 파일명 그대로 사용
     c. 파일 목록 + 한줄 설명을 `REFERENCES` 변수에 저장한다.
   - `references/` 디렉토리가 없으면 `REFERENCES`는 빈 상태로 진행한다. 안내 메시지를 출력하지 않는다.

## Step 4: 관련 코드 맵 생성
ARGS[0]에서 도메인 키워드를 추출하여 `PROJECT_ROOT` 내에서 관련 코드를 탐색하고 초기 코드 맵을 생성한다.

1. **키워드 추출**: ARGS[0]에서 핵심 도메인 키워드를 추출한다 (이슈 키 제외).
   - 예: "[JIRA-123] 결제 한도 변경" → `결제`, `한도` → `payment`, `limit`, `amount`
2. **관련 파일 탐색**: `PROJECT_ROOT`를 기준으로 키워드로 Grep하여 관련 파일을 수집한다.
   - 서비스, 도메인 모델, 컨트롤러/핸들러 등 핵심 파일을 식별한다.
3. **핵심 파일 스캔**: 발견된 파일의 상단(클래스 선언, 주요 상수/메서드 시그니처)을 Read하여 역할을 한 줄로 정리한다.
4. **코드 맵 작성**: 핵심 파일 / 참조 파일 / 설정으로 분류하여 맵을 작성한다.

탐색은 **가볍게** — 파일 전체를 읽지 않고, 역할 파악에 필요한 최소한만 읽는다. 코드 맵에 등록하는 파일은 **최대 15개**로 제한한다 (핵심 ≤ 5, 참조 ≤ 7, 설정 ≤ 3). 초과 시 관련도가 높은 파일을 우선한다. 상세한 코드 분석은 이후 agent들이 맵을 기반으로 타겟팅하여 수행한다.

## Step 5: 작업환경 생성

**svn인 경우** → 격리 브랜치를 만들지 않는다. SVN은 trunk에서 직접 작업하며, `svn update`로 최신 상태만 동기화한다. **작업 slug를 git 브랜치명 생성과 동일 규칙으로 만든다** — `--work` 사용 시 3.0.5가 결정한 slug > `--slug <name>` > ARGS[0] 이슈 키(config `issueKey.pattern`) > 타입+키워드 `{type}-{description}`(최대 40자) 순. slug는 `/`→`-` 치환 후 `[a-zA-Z0-9._-]`로 정규화하고(대문자 이슈 키 보존) `/`·`..`를 제거한다. `DEV_DIR = .dev/{slug}/`(기능별 격리)로 설정하고 `mkdir -p ${DEV_DIR}`를 실행한 뒤, 결정한 slug를 `.dev/.active`에 기록한다(덮어쓰기 — 훅·라우팅·verify가 활성 작업을 찾는 포인터). 완료 후 프로젝트 타입, 작업 경로, slug를 사용자에게 보고하고 **Step 5.5(작업 계획 착수 기록)로 진행**한다 (Step 6.5는 git 전용이라 건너뜀).

**git인 경우:**
격리된 작업환경을 생성한다.
- **`--work` 사용 시**: 3.0.5에서 이미 결정한 브랜치명을 그대로 쓴다. 아래 유도 절차(이슈 키 추출 포함)를 수행하지 않는다 — 여기서 다시 유도하면 3.0.5가 `작업 위치` 열에 기록한 이름과 어긋나고, phase-complete의 작업 계획 갱신 단계에서 행 매칭(`작업 위치` = 현재 브랜치)이 실패한다.
- ARGS[0]에서 브랜치명을 생성한다 (`--work` 미사용 시):
  1. 이슈 키 추출 시도: 대문자 영문 + `-` + 숫자 패턴 (e.g., `JIRA-123`, `PAY-456`)
  2. **이슈 키가 있으면**: 이슈 키를 브랜치명으로 사용 (e.g., `[JIRA-123] 로그인 기능 추가` → 브랜치 `JIRA-123`)
  3. **이슈 키가 없으면**: 요청 성격에 맞는 타입(config.json `conventions.branchTypes` 중 선택)과 핵심 키워드로 `conventions.branchFormat`(`{type}/{description}`) 형식의 브랜치명을 생성한다. description은 한국어→영어 번역, 최대 40자 (e.g., `로그인 기능 추가` → `feat/login-feature`. 타입 접두사가 있어야 gx-commit의 타입 파싱이 동작한다)
- `git checkout -b <branch-name>`으로 브랜치를 생성한다. 브랜치가 이미 존재하면 (`already exists` 에러) `git checkout <branch-name>`으로 전환한다.
- **작업 브랜치 전환 완료 직후 `Step 2.3 stash 복원` 절차를 수행한다** (`AUTO_STASHED=true`인 경우).
- 완료 후 프로젝트 타입, 브랜치명, 작업 경로를 사용자에게 보고.

## Step 5.5: 작업 계획 착수 기록 (`--work` 사용 시)

`work-id`가 확정된 실행이면 `setup-work.md`의 "착수 기록" 절을 수행한다 (3.0.5에서 이미 Read한 파일이다). 없으면 건너뛴다.

## Step 6: VCS ignore 자동 보강

**svn인 경우** → `.dev` 산출물(PRD·설계서·Trust Ledger·state.md 등)은 **협업 공유 대상**이므로 `svn:ignore`에 추가하지 않는다. 이전 버전이 등록한 `.dev`가 남아 있으면 제거를 제안한다: `svn propget svn:ignore .`로 확인 후, 사용자 확인을 받아 `.dev` 줄만 제외한 목록으로 `svn propset svn:ignore`를 재적용한다.

단 **`.dev/.active`는 공유 예외**다 — 이 머신의 활성 작업을 가리키는 런타임 포인터라 공유되면 다른 사용자의 `--resume`·verify baseline이 타인 세션 기준으로 오염된다. `.dev`가 아직 unversioned면 `svn add --depth=empty .dev`로 디렉토리만 등록한 뒤 `svn propset svn:ignore '.active' .dev`를 적용해 `.active`를 공유에서 제외한다. 이미 `.active`가 versioned로 커밋되어 있으면 `svn rm --keep-local .dev/.active`로 버전 관리에서만 제거하도록 안내한다. 제거 후에는 위 `svn propset svn:ignore '.active' .dev`를 반드시 재적용한다 (ignore 속성이 없으면 다음 `svn add --force .`가 `.active`를 다시 등록한다).

처리 후 Step 7로 진행한다.

**git인 경우:**
프로젝트 타입에 따라 `.gitignore`에 빌드 아티팩트 패턴을 추가한다. **패턴은 config `projectTypes.{타입}.artifacts` 필드에서 읽는다** (SSOT는 config — 예: java-spring `.gradle/`·`build/`, node `node_modules/`·`dist/`). `artifacts` 필드가 없는 타입은 이 보강을 건너뛴다. 이미 존재하는 패턴은 건너뛴다.

`.dev/`는 `.gitignore`에 추가하지 않는다 — 파이프라인 산출물(PRD·설계서·Trust Ledger·state.md 등)은 **협업 공유 대상**으로 커밋에 포함된다 (verify 지문은 `.dev`를 인덱스에서 제외하므로 게이트와 무관). 기존 `.gitignore`에 이전 버전이 추가한 `.dev/` 패턴이 남아 있으면 제거를 제안한다 (사용자 확인 후 해당 줄 삭제). 일시 파일(ralph.lock, verify-*.log 등)도 함께 커밋될 수 있음을 사용자에게 안내한다.

## Step 6.5: DEV_DIR 결정

**svn인 경우** → Step 5에서 이미 `.dev/{slug}/`로 설정하고 `.dev/.active`에 기록했으므로 건너뛴다.

**git인 경우:**
브랜치명에서 dev 산출물 디렉토리를 결정한다:
1. `git branch --show-current`로 현재 브랜치명을 가져온다.
2. 브랜치명의 `/`를 `-`로 치환하여 branch-slug를 생성한다 (예: `feat/login` → `feat-login`).
3. `DEV_DIR = .dev/{branch-slug}/` (예: `.dev/feat-login/`).
4. `mkdir -p ${DEV_DIR}`로 디렉토리를 생성한다.

이 `DEV_DIR`은 이후 모든 Phase에서 산출물 저장 경로로 사용된다.

## Step 7: 진행 상태 초기화
Write 전에 기존 `${DEV_DIR}/state.md`가 존재하고 `status: in_progress`이며 `pipeline: gx-tdd`가 아니면(gx-dev 등 다른 파이프라인 산출물), 덮어쓰면 해당 파이프라인 상태가 유실됨을 경고하고 AskUserQuestion으로 덮어쓰기/중단을 확인받는다.
`${DEV_DIR}/state.md`에 초기 상태를 Write한다:
- phase: setup, status: in_progress
- pipeline: gx-tdd, verify-status: pending (커밋/PR 게이트 판별 키 — SKILL.md 갱신 규칙 참조)
- vcs-type, branch, base, project-type, project-root, args, flags 기록 (svn은 branch/base 미사용). `flags`에는 의도 파싱의 RALPH 우선순위 규칙을 **통과해 살아남은** RALPH는(플래그·자연어 `랄프로` 등 출처 무관) `--ralph`로 **정규화하여** 포함한다 — phase-implement Step 0.7의 판정 키이며 별도 필드를 두지 않는다. 우선순위 규칙에서 **무시된 RALPH는 기록하지 않는다** (core 세션에 `--ralph`가 남아 `--status`·Step 0.7이 이중 안내를 내지 않도록). `VCS_TYPE`이 `svn`이면 포함하지 않고 "gx-ralph는 SVN 미지원 — 대화형으로 진행합니다" 1줄을 안내한다 (의도 파싱의 svn 우선 배제가 1차, 이것은 2차 방어). `--isolated`는 있는 그대로 기록한다 — phase-implement Step 2-I와 phase-review 4b의 경로 판정 키다.
- mode, intent-source 기록 (의도 파싱 결과)
- model-profile 기록 (Step 1.5/3.0 결정 값)
- **auto-stashed** (git 전용): Step 2.1의 `AUTO_STASHED` 값(true/false). Step 2.3에서 stash pop이 완료되면 false로 갱신한다. 파이프라인이 stash 이후 중단되어도 `--resume`이 이 값을 보고 보류된 stash를 복원한다. svn은 미사용.
- **last-known-head** (git 전용): `git rev-parse HEAD` 결과. 재개 시 외부 커밋 감지에 사용한다. 각 Phase 종료 시 갱신한다. svn은 미사용.
- phases: { setup: completed }

**작업 계획 되돌림**: 덮어쓰기 전의 state.md가 `status: completed`이고 `work-id`가 있으면 `setup-work.md`의 "작업 계획 되돌림" 절을 수행한다. 없으면 아무것도 하지 않는다.

