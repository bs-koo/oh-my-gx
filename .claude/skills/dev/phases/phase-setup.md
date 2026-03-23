# phase-setup: 작업환경 준비

## Step 0: 진행 중 작업 감지

### `--resume` 플래그가 있는 경우
1. `.dev/state.md`를 탐색한다.
2. 존재하고 `status: in_progress`이면 → 질문 없이 바로 재개 (아래 "이어서 진행" 절차).
3. state.md가 없거나 `status: completed`이면 → "재개할 작업이 없습니다." 출력 후 종료.

### `--resume` 플래그가 없는 경우 (자동 감지)
ARGS[0]이 있으면 → 새 작업이므로 자동 감지를 건너뛰고 Step 1로 진행.
ARGS[0]이 없으면 → 아래 자동 감지 로직 실행.

1. `.dev/state.md`를 탐색한다.
2. state.md가 존재하고 `status: in_progress`이면:
   - 사용자에게 AskUserQuestion으로 질문: "이전에 진행하던 작업이 있습니다."
     - "이어서 진행" → 재개
     - "새로 시작" → Step 1로 진행 (Step 7에서 덮어씀)
3. state.md가 없거나 `status: completed`이면 → Step 1로 진행.

**이어서 진행 시:**
- state.md에서 VCS_TYPE, GIT_PREFIX, PROJECT_ROOT, 베이스 브랜치, 프로젝트 타입, ARGS[0], flags를 복원. VCS_TYPE이 없으면 `"git"`으로 fallback.
- `test -d`로 경로 검증. 실패 시 "작업 경로가 유효하지 않습니다." → 새로 시작.
- prd.md, design.md, trust-ledger.md, codemap.md, self-check.md가 있으면 Read하여 맥락 복원.
- `references/` 디렉토리가 있으면 외부 규격 참조 탐색(Step 3.5)을 재실행하여 `REFERENCES`를 복원한다.
- phases 맵에서 마지막 in_progress Phase를 찾아 재개.
- phase-setup의 나머지 단계(Step 1~Step 7)를 건너뛴다.

## Step 1: VCS 확인

`.claude/config.json`의 `"vcs"` 필드를 읽어 `VCS_TYPE`을 결정한다.

**git인 경우** (vcs가 `"git"` 또는 `""` 미설정):
- `git rev-parse --is-inside-work-tree` 확인.
- 성공 → `VCS_TYPE` = `"git"`, `GIT_PREFIX` = `git`.
- 실패 → AskUserQuestion: "Git 저장소가 아닙니다. `git init`으로 생성할까요?"
  - 예 → `git init` 실행 후 계속.
  - 아니오 → 중단.

**svn인 경우:**
- `svn info` 확인.
- 성공 → `GIT_PREFIX` = `svn`.
- 실패 → "SVN 작업 복사본이 아닙니다." 출력 후 중단.

## Step 2: 베이스 브랜치 결정

**svn인 경우** → 건너뛴다. SVN은 브랜치 없이 trunk에서 직접 작업한다.

**git인 경우:**

공유 규칙의 "베이스 브랜치 감지"에 따라 결정한다.

결정 후 베이스 브랜치를 최신 상태로 동기화한다:
1. `git remote get-url origin`으로 remote 존재를 확인한다. 없으면 건너뛴다.
2. `git checkout <base-branch>`를 실행한다. 실패 시 경고를 표시하고 현재 로컬 상태로 계속 진행한다.
3. checkout 성공 시, `git pull origin <base-branch>`를 실행한다. pull 실패 시 (네트워크 오류 등) 경고를 표시하고 현재 로컬 상태로 계속 진행한다.

## Step 3: 프로젝트 정보 수집
`PROJECT_ROOT = ./` (현재 디렉토리).

아래 5개 작업은 서로 독립적이므로 **병렬로 실행**한다:
1. **프로젝트 타입 감지**: `.claude/config.json`의 `projectTypes`에서 detect 필드와 매칭한다 (예: `build.gradle.kts` → `java-spring`, `package.json` → `node`). 여러 타입이 감지되면 모두 기록한다.
2. **디렉토리 구조 수집**: `PROJECT_ROOT`의 최상위 2레벨 디렉토리 구조를 수집한다.
3. **CLAUDE.md 확인**: `PROJECT_ROOT`에 CLAUDE.md가 있으면 읽어서 코딩 컨벤션을 확보한다.
4. **도메인 컨텍스트 탐색**: 현재 레포와 매칭되는 도메인 컨텍스트를 찾는다.
   - **git**: `git remote get-url origin`으로 레포명을 추출한다 (예: `xx/asset-factory-api`).
   - **svn**: `svn info --show-item repos-root-url`로 저장소 URL을 추출하고, URL의 마지막 세그먼트를 레포명으로 사용한다.
   - `context/*/PROJECTS.md`를 Grep하여 해당 레포를 참조하는 도메인을 찾는다.
   - 매칭되면 해당 도메인의 `glossary.md`, `architecture.md`를 Read하여 `DOMAIN_CONTEXT`에 저장한다.
   - `context/` 디렉토리가 없거나 매칭되지 않으면 `DOMAIN_CONTEXT`는 빈 상태로 진행한다.
     사용자에게 안내: "도메인 컨텍스트가 없습니다. `context/` 디렉토리를 생성하고 `/context`로 도메인을 등록하면 이후 작업에서 용어/아키텍처를 참조할 수 있습니다."
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

**svn인 경우** → 건너뛴다. SVN은 trunk에서 직접 작업하며, `svn update`로 최신 상태만 동기화한다. 완료 후 프로젝트 타입, 작업 경로를 사용자에게 보고.

**git인 경우:**

격리된 작업환경을 생성한다.
- ARGS[0]에서 브랜치명을 생성한다:
  1. 이슈 키 추출 시도: 대문자 영문 + `-` + 숫자 패턴 (e.g., `JIRA-123`, `PAY-456`)
  2. **이슈 키가 있으면**: 이슈 키를 브랜치명으로 사용 (e.g., `[JIRA-123] 로그인 기능 추가` → 브랜치 `JIRA-123`)
  3. **이슈 키가 없으면**: 핵심 키워드 추출, 한국어→영어 번역, 최대 40자 (e.g., `로그인 기능 추가` → `login-feature`)
- `git checkout -b <branch-name>`으로 브랜치를 생성한다. 브랜치가 이미 존재하면 (`already exists` 에러) `git checkout <branch-name>`으로 전환한다.
- 완료 후 프로젝트 타입, 브랜치명, 작업 경로를 사용자에게 보고.

## Step 6: VCS ignore 자동 보강

**svn인 경우** → 건너뛴다. SVN은 `svn:ignore` 속성을 사용하며, 자동 보강하지 않는다.

**git인 경우:**

프로젝트 타입에 따라 `.gitignore`에 빌드 아티팩트 패턴을 추가한다. 이미 존재하는 패턴은 건너뛴다.

| 프로젝트 타입 | 추가 패턴 |
|---------------|-----------|
| java-spring | `.gradle/`, `build/` |
| node | `node_modules/`, `dist/` |

`.dev/` 패턴도 이 단계에서 함께 추가한다 (dev 스킬의 문서 보관 규칙과 통합).

## Step 7: 진행 상태 초기화
`.dev/state.md`에 초기 상태를 Write한다:
- phase: setup, status: in_progress
- vcs-type, branch, base, project-type, project-root, args, flags 기록
- mode, intent-source 기록 (의도 파싱 결과)
- phases: { setup: completed }

