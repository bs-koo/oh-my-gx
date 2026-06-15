# phase-setup: 작업환경 준비

## Step 0: 진행 중 작업 감지

### `--resume` 플래그가 있는 경우
1. state.md 탐색을 위해 현재 브랜치명에서 **임시** 경로를 계산한다: `git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/state.md`.
2. 해당 경로의 state.md를 탐색한다.
3. 존재하고 `status: in_progress`이면 → DEV_DIR을 해당 파일의 부모 디렉토리(`.dev/{branch-slug}/`)로 확정하고 바로 재개 (아래 "이어서 진행" 절차).
4. state.md가 없거나 `status: completed`이면 → "재개할 작업이 없습니다." 출력 후 종료.

### `--resume` 플래그가 없는 경우 (자동 감지)
ARGS[0]이 있으면 → 새 작업이므로 자동 감지를 건너뛰고 Step 1로 진행.
ARGS[0]이 없으면 → 아래 자동 감지 로직 실행.

1. state.md 탐색을 위해 현재 브랜치명에서 **임시** 경로를 계산한다: `git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/state.md`.
2. 해당 경로의 state.md를 탐색한다.
3. state.md가 존재하고 `status: in_progress`이면:
   - 사용자에게 AskUserQuestion으로 질문: "이전에 진행하던 작업이 있습니다."
     - "이어서 진행" → 재개
     - "새로 시작" → Step 1로 진행 (Step 7에서 덮어씀)
3. state.md가 없거나 `status: completed`이면 → Step 1로 진행.

### 0.1 재개 정합성 체크 (이어서 진행 선택 시)

state.md를 재개하기 전에 외부 개입으로 인한 불일치를 감지한다.

1. **브랜치 정합성**: state.md의 `branch` 필드와 `git branch --show-current` 결과를 비교한다. 표기 규약은 다음과 같다:
   - `{state.md의 branch}` / `{현재 브랜치}`: 원본 브랜치명 (예: `feat/login`).
   - `{old-slug}` / `{new-slug}`: 각 브랜치명에서 `/`를 `-`로 치환한 **DEV_DIR 슬러그** (예: `feat-login`).

   불일치 시 AskUserQuestion을 띄운다:
   - "기존 DEV_DIR `.dev/{old-slug}/` (state.md의 branch=`{state.md의 branch}`)를 현재 브랜치 DEV_DIR `.dev/{new-slug}/` (`{현재 브랜치}`)로 이관" → 이관 실행.
     - 이관 전에 목적지 `.dev/{new-slug}/`가 이미 존재하는지 확인한다. **존재 시 `mv`를 사용하지 않는다** (목적지 내부로 중첩 이동되어 구조가 깨진다).
     - 존재하지 않으면: `mv ".dev/{old-slug}" ".dev/{new-slug}"`.
     - 존재하면: 추가 AskUserQuestion — ①"기존 `.dev/{new-slug}/`를 `.dev/{new-slug}.backup-$(date +%s)/`로 백업 후 이관" / ②"중단". 백업 선택 시 `mv ".dev/{new-slug}" ".dev/{new-slug}.backup-$(date +%s)"` → `mv ".dev/{old-slug}" ".dev/{new-slug}"` 순서로 실행.
     - 경로에 공백/특수문자가 포함될 수 있으므로 `mv` 인자는 반드시 따옴표로 감싼다.
   - "새로 시작" → 기존 `.dev/{old-slug}/`는 유지하고 Step 1로 진행.
   - "중단" → 사용자에게 수동 정리를 요청하고 종료.
2. **HEAD 정합성**: state.md에 `last-known-head` 필드가 있고 현재 `git rev-parse HEAD`와 다르면, `git log {last-known-head}..HEAD --oneline`으로 외부 커밋 개수를 센다. 1개 이상이면 사용자에게 보고: "외부 커밋 {N}건이 감지되었습니다: {sha1}..{sha2}. 계속하시려면 확인해주세요." 후 AskUserQuestion으로 진행/중단 선택.

**이어서 진행 시:**
- state.md에서 GIT_PREFIX, PROJECT_ROOT, 베이스 브랜치, 프로젝트 타입, ARGS[0], flags를 복원.
- `test -d`로 경로 검증. 실패 시 "작업 경로가 유효하지 않습니다." → 새로 시작.
- `${DEV_DIR}/` 하위의 prd.md, design.md, trust-ledger.md, codemap.md, self-check.md가 있으면 Read하여 맥락 복원.
- `references/` 디렉토리가 있으면 외부 규격 참조 탐색(Step 3.5)을 재실행하여 `REFERENCES`를 복원한다.
- phases 맵에서 마지막 in_progress Phase를 찾아 재개.
- phase-setup의 나머지 단계(Step 1~Step 7)를 건너뛴다.

## Step 1: Git 저장소 확인
`git rev-parse --is-inside-work-tree` 확인.
- 성공 → `GIT_PREFIX` = `git`.
- 실패 → AskUserQuestion: "Git 저장소가 아닙니다. `git init`으로 생성할까요?"
  - 예 → `git init` 실행 후 계속.
  - 아니오 → 중단.

## Step 2: 베이스 브랜치 결정
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
   - "stash를 유지하고 수동 해결" → conflict 상태를 유지한 채 파이프라인 일시 중단. 사용자가 해결 후 재개 지시.
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
     - 플러그인 번들 템플릿 누락 (${CLAUDE_PLUGIN_ROOT}/.claude/config.json)

     수동 해결:
       cp <플러그인 경로>/.claude/config.json .claude/config.json

     해결 후 /oh-my-gx:gx-tdd를 다시 실행해주세요."
     ```
     파이프라인 중단.
  2. `CONFIG_SETUP_ATTEMPTS` == 0이면 AskUserQuestion — "`.claude/config.json`이 없습니다. `/oh-my-gx:gx-setup`으로 자동 생성할까요?"
     - "자동 생성" → `CONFIG_SETUP_ATTEMPTS = 1` 갱신 후 `Skill("oh-my-gx:gx-setup")` 호출. 생성 완료 후 다시 3.0 검증 (단, 위 재시도 가드가 작동하여 무한 루프 방지).
     - "직접 생성 후 재실행" → 파이프라인 중단.
- **존재 시**: Read하여 `projectTypes`, `sensitiveFilePatterns`, `buildArtifactPatterns`, `timeouts`, `contextLimits`를 변수에 로드.
- JSON 파싱 실패 시: "config.json이 손상되었습니다. 백업 후 재설정하세요." 출력 후 중단.

### 3.1 병렬 수집

아래 5개 작업은 서로 독립적이므로 **병렬로 실행**한다:
1. **프로젝트 타입 감지**: `.claude/config.json`의 `projectTypes`에서 detect 필드와 매칭한다 (예: `build.gradle.kts` → `java-spring`, `package.json` → `node`). 여러 타입이 감지되면 모두 기록한다.
2. **디렉토리 구조 수집**: `PROJECT_ROOT`의 최상위 2레벨 디렉토리 구조를 수집한다.
3. **CLAUDE.md 확인**: `PROJECT_ROOT`에 CLAUDE.md가 있으면 읽어서 코딩 컨벤션을 확보한다.
4. **도메인 컨텍스트 탐색**: 현재 레포와 매칭되는 도메인 컨텍스트를 찾는다.
   - `git remote get-url origin`으로 레포명을 추출한다 (예: `xx/asset-factory-api`).
   - `context/*/PROJECTS.md`를 Grep하여 해당 레포를 참조하는 도메인을 찾는다.
   - 매칭되면 해당 도메인의 `glossary.md`, `architecture.md`를 Read하여 `DOMAIN_CONTEXT`에 저장한다.
   - `context/` 디렉토리가 없거나 매칭되지 않으면 `DOMAIN_CONTEXT`는 빈 상태로 진행한다.
     사용자에게 안내: "도메인 컨텍스트가 없습니다. `context/` 디렉토리를 생성하고 `/oh-my-gx:gx-context`로 도메인을 등록하면 이후 작업에서 용어/아키텍처를 참조할 수 있습니다."
   - `DOMAIN_CONTEXT`는 이후 agent 프롬프트에 "도메인 컨텍스트"로 포함한다.
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
격리된 작업환경을 생성한다.
- ARGS[0]에서 브랜치명을 생성한다:
  1. 이슈 키 추출 시도: 대문자 영문 + `-` + 숫자 패턴 (e.g., `JIRA-123`, `PAY-456`)
  2. **이슈 키가 있으면**: 이슈 키를 브랜치명으로 사용 (e.g., `[JIRA-123] 로그인 기능 추가` → 브랜치 `JIRA-123`)
  3. **이슈 키가 없으면**: 핵심 키워드 추출, 한국어→영어 번역, 최대 40자 (e.g., `로그인 기능 추가` → `login-feature`)
- `git checkout -b <branch-name>`으로 브랜치를 생성한다. 브랜치가 이미 존재하면 (`already exists` 에러) `git checkout <branch-name>`으로 전환한다.
- **작업 브랜치 전환 완료 직후 `Step 2.3 stash 복원` 절차를 수행한다** (`AUTO_STASHED=true`인 경우).
- 완료 후 프로젝트 타입, 브랜치명, 작업 경로를 사용자에게 보고.

## Step 6: .gitignore 자동 보강
프로젝트 타입에 따라 `.gitignore`에 빌드 아티팩트 패턴을 추가한다. 이미 존재하는 패턴은 건너뛴다.

| 프로젝트 타입 | 추가 패턴 |
|---------------|-----------|
| java-spring | `.gradle/`, `build/` |
| node | `node_modules/`, `dist/` |

`.dev/` 패턴도 이 단계에서 함께 추가한다 (dev 스킬의 문서 보관 규칙과 통합. 브랜치별 하위 폴더 전체가 무시됨).

## Step 6.5: DEV_DIR 결정

브랜치명에서 dev 산출물 디렉토리를 결정한다:
1. `git branch --show-current`로 현재 브랜치명을 가져온다.
2. 브랜치명의 `/`를 `-`로 치환하여 branch-slug를 생성한다 (예: `feat/login` → `feat-login`).
3. `DEV_DIR = .dev/{branch-slug}/` (예: `.dev/feat-login/`).
4. `mkdir -p ${DEV_DIR}`로 디렉토리를 생성한다.

이 `DEV_DIR`은 이후 모든 Phase에서 산출물 저장 경로로 사용된다.

## Step 7: 진행 상태 초기화
`${DEV_DIR}/state.md`에 초기 상태를 Write한다:
- phase: setup, status: in_progress
- branch, base, project-type, project-root, args, flags 기록
- mode, intent-source 기록 (의도 파싱 결과)
- **auto-stashed**: Step 2.1의 `AUTO_STASHED` 값(true/false). Step 2.3에서 stash pop이 완료되면 false로 갱신한다. 파이프라인이 stash 이후 중단되어도 `--resume`이 이 값을 보고 보류된 stash를 복원한다.
- **last-known-head**: `git rev-parse HEAD` 결과. 재개 시 외부 커밋 감지에 사용한다. 각 Phase 종료 시 갱신한다.
- phases: { setup: completed }

