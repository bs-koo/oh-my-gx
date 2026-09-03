---
name: gx-setup
argument-hint: "없음"
description: VCS 감지, 도구 확인, 인증을 단계별로 수행한다.
disable-model-invocation: true
allowed-tools:
  - "Bash(echo *)"
  - "Bash(gh *)"
  - "Bash(git *)"
  - "Bash(svn *)"
  - "Bash(which *)"
  - "Bash(command *)"
  - "Bash(uname *)"
  - "Bash(java *)"
  - "Bash(winget install *)"
  - "Bash(choco install *)"
  - "Bash(scoop install *)"
  - "Bash(brew install *)"
  - "Bash(test *)"
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# setup

플러그인 초기 설정을 단계별로 수행한다.

## 실행 절차

아래 단계를 **순서대로** 실행한다. 각 단계 완료 시 `{항목} : 완료 ✅` 형식으로 출력한다.

### 0단계: VCS 감지

프로젝트의 버전 관리 시스템을 감지하고 `.claude/config.json`에 저장한다.

0. **config.json 부재 시 번들 템플릿에서 생성** (다른 단계보다 먼저): `test -f .claude/config.json`로 존재를 확인한다.
   - **없으면**: 플러그인 번들 템플릿을 `Read("../../config.json")`(이 SKILL.md 위치 기준 상대경로)로 읽어 프로젝트 `.claude/config.json`에 그대로 `Write`한다 (Write가 `.claude/` 디렉토리를 없으면 생성한다). 이 템플릿만은 스킬 디렉토리 밖(플러그인 루트의 `.claude/`)에 있어, 스킬 디렉토리만 배포하는 하네스에서는 읽지 못할 수 있다 — Read가 실패하면 저장소의 `.claude/config.json`을 프로젝트에 직접 복사하도록 사용자에게 안내하고 다음 단계로 넘어간다. `config.json 생성 : 완료 ✅ (번들 템플릿 복사)` 출력 후 아래 1로 진행한다.
   - **있으면**: 건너뛰고 아래 1로 진행한다.
1. `.claude/config.json`의 `"vcs"` 필드를 확인한다. 값이 이미 설정되어 있으면 (`"git"` 또는 `"svn"`) → 갱신 없이 `VCS 감지 : 완료 ✅ ({값}, 기존 설정 유지)` 출력 후 1단계로 진행.
2. 값이 비어있으면 → `git rev-parse --is-inside-work-tree 2>/dev/null`로 Git 저장소인지 확인한다.
3. 결과에 따라 분기:
   - **성공** → `VCS_TYPE = "git"`
   - **실패** →
     ```
     AskUserQuestion(
       questions: [{
         header: "VCS 선택",
         question: "Git 저장소가 감지되지 않았습니다. 프로젝트 환경을 선택해주세요.",
         multiSelect: false,
         options: [
           { label: "Git", description: "새 Git 저장소를 생성합니다" },
           { label: "SVN", description: "SVN 프로젝트입니다" },
           { label: "없음", description: "VCS를 사용하지 않습니다" }
         ]
       }]
     )
     ```
     - "Git" 선택 → `git init` 실행 후 `VCS_TYPE = "git"`
     - "SVN" 선택 → `VCS_TYPE = "svn"`
     - "없음" 선택 → "VCS 없이는 커밋/PR 기능을 사용할 수 없습니다." 안내 후 `VCS_TYPE = ""`
4. `.claude/config.json`의 `"vcs"` 필드를 `VCS_TYPE` 값으로 갱신한다 (Edit).
5. `VCS 감지 : 완료 ✅ ({VCS_TYPE})` 출력.

이후 단계는 `VCS_TYPE`에 따라 분기한다.

### 0.5단계: 프로젝트 타입 등록

`.claude/config.json`의 `projectTypes`를 프로젝트에 맞게 등록한다. **SSOT는 config에 등록된 값**이며, 힌트 카탈로그는 제안용이다.

1. **기존 등록 확인**: config `projectTypes` 중 `detect` 파일이 프로젝트 루트에 존재하는 타입이 있으면 → `프로젝트 타입 등록 : 완료 ✅ ({타입}, 기존 등록 유지)` 출력 후 **7(하네스 확인)으로 진행**한다 (config는 갱신하지 않는다). 등록 내용을 그대로 두더라도 하네스 확인은 수행한다 — 명령이 config에 적혀 있다는 것과 그 명령이 실제로 도는 것은 다른 문제이고, 이 간극이 파이프라인 후반(구현 직전)에야 드러나면 PRD·설계를 다 만든 뒤 되돌아가야 한다.
   **여러 타입의 detect 파일이 동시에 존재하면** 첫 매칭으로 단락하지 않고 아래 3의 다중 감지 분기로 처리한다.
2. **빌드 파일 스캔**: Glob으로 `Makefile`, `CMakeLists.txt`, `project.yml`, `Cargo.toml`, `pom.xml`, `pyproject.toml`, `setup.py`, `requirements.txt`, `go.mod`, `*.csproj`, `*.sln`, `composer.json`, `build.gradle`, `build.gradle.kts`, `package.json`을 탐색한다.
3. **제안 생성**: `Read("references/project-type-hints.md")`로 힌트 카탈로그를 읽어 감지 파일과 매칭한다.
   - 매칭되면 해당 행의 타입 키·build/test·warningPattern·artifacts를 제안 값으로 사용한다.
   - **여러 행이 매칭되면** 두 가지 상황을 구분한다. 잘못 고르면 한쪽 레이어가 영구히 검증되지 않으므로 사용자에게 물어본다.
     - **부수 감지**: 한쪽이 도구용일 뿐 별도 테스트 대상이 아닌 경우 (예: C 프로젝트의 도구용 `package.json`, 문서 사이트용 `package.json`). → 주 타입 하나를 고른다.
     - **복합 타입**: 양쪽 모두 실제 소스와 테스트를 가진 경우 (예: `build.gradle.kts` + `frontend/package.json`인 풀스택 모노레포). → **한 타입 키에 양쪽을 `&&`로 이은 복합 명령**을 등록한다. 하나만 고르면 나머지 레이어는 verify 게이트가 아예 실행하지 않아 미검증 상태로 통과한다.
     ```
     AskUserQuestion(
       questions: [{
         header: "타입 구성",
         question: "빌드 파일이 여러 개 감지되었습니다: {목록}. 어떤 구성인가요?",
         multiSelect: false,
         options: [
           { label: "복합 (양쪽 모두 테스트 대상)", description: "한 타입에 양쪽 build/test를 && 로 이어 등록합니다. 풀스택 모노레포의 기본 선택입니다" },
           { label: "{주 타입}만 대상", description: "나머지는 도구용이라 테스트 대상이 아닙니다" }
         ]
       }]
     )
     ```
     복합을 선택하면 각 행의 명령을 `&&`로 잇고 타입 키는 프로젝트를 나타내는 이름으로 제안한다 (예: `fullstack`). 명령 조합 규칙과 주의점은 힌트 카탈로그의 "복합 타입" 절을 따른다.
   - 매칭되지 않으면 프로젝트 구조(빌드 스크립트, README, CI 설정)를 근거로 추론해 제안하되 근거를 함께 표시한다. 근거 없는 명령을 지어내지 않는다.
   - 아무 빌드 파일도 감지되지 않으면 → `프로젝트 타입 등록 : 건너뜀 (감지 실패)` 출력 후 1단계로 진행한다 (파이프라인 게이트가 fail-closed로 처리).
4. **사용자 확인**:
   ```
   AskUserQuestion(
     questions: [{
       header: "타입 등록",
       question: "감지된 프로젝트 타입: {타입키}. 명령을 확인해주세요. build: `{build}`, test: `{test}`",
       multiSelect: false,
       options: [
         { label: "등록 (Recommended)", description: "이 값으로 config.json projectTypes에 기록합니다" },
         { label: "명령 수정", description: "Other로 이동해서 build/test 명령을 직접 입력해주세요" },
         { label: "건너뛰기", description: "등록하지 않습니다. 파이프라인 게이트에서 매번 직접 입력해야 합니다" }
       ]
     }]
   )
   ```
   - "등록" → 5로 진행. "명령 수정" → 입력값 반영 후 5로 진행. "건너뛰기" → `프로젝트 타입 등록 : 건너뜀 (사용자 선택)` 출력 후 1단계로 진행.
5. **config 기록**: 확정 값을 `projectTypes.{타입키}`에 Edit로 기록한다 (`detect`/`build`/`test`/`focusedTest`/`warningPattern`/`artifacts`. 빈 제안 값은 필드를 생략한다). `focusedTest`는 선택 필드로, 특정 테스트만 실행하는 명령 템플릿이다 — `{files}`(테스트 파일 경로 공백 구분) 또는 `{pattern}`(클래스 글롭 — 파일명에서 유도) 플레이스홀더를 쓴다. 미등록 시 gx-tdd가 전체 `test` 명령으로 폴백한다.
6. **권한 등록**: build/test 명령의 첫 토큰에서 prefix 권한을 도출하고 (예: `make test` → `Bash(make *)`) 확인받는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "권한 등록",
       question: "등록한 명령을 권한 프롬프트 없이 실행하도록 `.claude/settings.local.json`에 허용을 추가할까요? ({권한 prefix 목록})",
       multiSelect: false,
       options: [
         { label: "추가 (Recommended)", description: "permissions.allow에 병합합니다 (기존 항목 보존)" },
         { label: "건너뛰기", description: "추가하지 않습니다. 파이프라인 실행 중 권한 프롬프트가 발생할 수 있습니다" }
       ]
     }]
   )
   ```
   - "추가" → `.claude/settings.local.json`의 `permissions.allow` 배열에 병합한다. 파일 부재 시 `{"permissions":{"allow":[...]}}`로 생성하고, 기존 항목은 보존하며, 중복은 추가하지 않는다. JSON 파싱 실패 시 갱신하지 않고 수동 설정을 안내한다.
7. **하네스 확인** (등록·유지 경로 공통, 1회 실행):

   등록된 `test` 명령을 실제로 **한 번 실행**한다. config에 명령이 적혀 있다는 것과 그 명령이 도는 것은 별개이고, 이 차이는 온보딩에서 알면 몇 분이지만 파이프라인 후반에 알면 PRD·설계를 되돌려야 한다. 복합 명령이면 `&&`로 이어진 **각 조각을 나눠 실행**해 어느 레이어가 비어 있는지까지 보고한다.

   타임아웃은 config `timeouts.build`를 쓴다. 실행 결과에 따라:

   | 결과 | 출력 | 안내 |
   |---|---|---|
   | 정상 실행, 테스트 1건 이상 | `테스트 하네스 : 확인 ✅ ({N}건)` | 그대로 진행 |
   | 실행되지만 0건 | `테스트 하네스 : 명령은 동작하나 테스트 0건` | 첫 테스트 작성 필요를 안내 (gx-tdd는 이 상태로 진입하지 않는다) |
   | 명령 실행 불가 (러너 미설치·스크립트 부재) | `테스트 하네스 : 실행 실패 — {명령}` | 러너 설치를 안내하고 `docs/test-harness-guide.md`를 가리킨다 |
   | 기존 테스트가 실패 중 | `테스트 하네스 : 확인 ✅ ({N}건, {M}건 실패)` | 실패는 보고만 한다 — 기존 테스트를 고치는 것은 setup의 일이 아니다 |

   복합 명령의 부분 실패는 이렇게 보고한다:
   ```
   테스트 하네스 : 부분 확인
     ./gradlew test           → 7건 ✅
     pnpm --dir frontend test → 실행 실패 (러너 미설치)
   ```

   **이 확인은 정보 제공이며 setup을 중단시키지 않는다.** gx-setup은 gx-dev와 공유하는 스킬이고 gx-dev는 테스트를 필수로 요구하지 않으므로, 여기서 차단하면 정상적인 사용을 막게 된다. 하네스가 필수인 쪽은 gx-tdd이며, 그 강제는 phase-implement의 하네스 게이트와 gx-verify가 담당한다. 다만 이 단계에서 미리 알려주면 사용자가 파이프라인을 시작하기 전에 결정할 수 있다.

   test 명령이 등록되지 않은 타입(2에서 건너뛰었거나 test 필드가 없는 경우)은 `테스트 하네스 : 건너뜀 (test 명령 미등록)`을 출력한다.
8. `프로젝트 타입 등록 : 완료 ✅ ({타입키})` 출력.

### 1단계: 필수 도구 확인

#### VCS CLI

| VCS_TYPE | 도구 | 확인 |
|----------|------|------|
| git | gh | `which gh` |
| svn | svn | `which svn` → `svn --version` |

**git인 경우:**
1. `which gh` 실행
2. 있으면 → `gh : 완료 ✅` 출력
3. 없으면 → 패키지 매니저를 감지하여 자동 설치를 시도한다:

   a. OS와 패키지 매니저를 감지한다 (위에서부터 순서대로, 먼저 감지된 것을 사용):
      - `which winget` → Windows (winget)
      - `which choco` → Windows (Chocolatey)
      - `which scoop` → Windows (Scoop)
      - `which brew` → macOS/Linux (Homebrew)
      - `which apt` → Linux (apt)
      - `which yum` → Linux (yum)

   b. **apt/yum만 감지된 경우** → gh는 기본 저장소에 미포함되므로 자동 설치를 건너뛰고 수동 안내로 직행한다 (https://cli.github.com).

   c. **그 외 패키지 매니저가 감지되면**:
      ```
      AskUserQuestion(
        questions: [{
          header: "gh CLI 설치",
          question: "gh CLI가 설치되어 있지 않습니다. 자동 설치하시겠습니까?",
          multiSelect: false,
          options: [
            { label: "설치", description: "{감지된 패키지 매니저}로 gh CLI 설치" },
            { label: "건너뛰기", description: "나중에 직접 설치" }
          ]
        }]
      )
      ```

   d. "설치" 선택 시 감지된 패키지 매니저로 설치 (`timeout: 300000` — config.json `timeouts.install` 값):
      | 패키지 매니저 | 설치 명령 |
      |-------------|----------|
      | winget | `winget install --id GitHub.cli --accept-source-agreements --accept-package-agreements` |
      | choco | `choco install gh -y` |
      | scoop | `scoop install gh` |
      | brew | `brew install gh` |

   e. 설치 완료 후 `which gh`로 재확인 → 성공하면 `gh : 완료 ✅` 출력
   f. 설치 실패 시 → 수동 설치 안내 (https://cli.github.com) 출력 후 계속 진행
   g. 패키지 매니저가 감지되지 않으면 → 수동 설치 안내 (https://cli.github.com) 출력. `/gx-setup` 재실행 안내.

**svn인 경우:**
1. `which svn` 실행
2. 있으면 → `svn --version --quiet`로 버전 확인 → `svn : 완료 ✅ (버전)` 출력
3. 없으면 → `uname -s`로 OS를 감지하고 설치 안내를 표시한다:

   ```
   ⚠️ SVN CLI가 설치되어 있지 않습니다.
   /gx-dev의 자기점검·리뷰 단계에서 svn diff가 필요합니다.

   {OS별 안내}

   설치 후 터미널을 재시작하고 /gx-setup을 다시 실행하세요.
   ```

   **OS별 안내:**
   - **Windows**:
     ```
     1. https://sliksvn.com/download/ 에서 SlikSvn (64 bit)을 다운로드하세요.
     2. 다운로드된 .msi 파일을 더블클릭하여 설치를 실행하세요.
     3. 설치가 완료되면 터미널을 완전히 종료하고 다시 여세요.
     4. /gx-setup을 다시 실행하세요.
     ```
   - **macOS**: `brew install subversion`을 실행하고 터미널을 재시작하세요.
   - **Linux**: `sudo apt install subversion` 또는 `sudo yum install subversion`을 실행하세요.

   안내 출력 후 `svn : ⚠️ 미설치`로 표시하고 계속 진행한다.

#### JDK (java 계열 타입만)

0.5단계에서 **이번 실행의 detect 파일 매칭으로 감지된 타입(0.5단계에서 신규 등록됐든 기존 유지든)** 중 java 계열(gradle/maven 기반 — `java-spring`, `java-maven` 등 build/test 명령에 `gradlew` 또는 `mvn`이 포함된 타입)이 있을 때만 실행한다. config에 java 계열 항목이 존재해도 이번 프로젝트에서 detect 파일이 매칭되지 않으면 건너뛴다. 없으면 `JDK : 건너뜀 (java 계열 타입 없음)` 출력 후 2단계로 진행한다.

1. `uname -s`로 OS를 감지한다.
2. `java -version`으로 JDK 설치 여부와 버전을 확인한다.
3. JDK 8 이상이 설치되어 있으면 → `JDK : 완료 ✅ (버전)` 출력
4. 없거나 버전이 낮으면 → OS별 설치 안내를 제공한다:
   - **Linux**: `sudo apt install openjdk-17-jdk` 또는 `sudo yum install java-17-openjdk-devel`
   - **macOS**: `brew install openjdk@17`
   - **Windows (MSYS/Git Bash)**: https://adoptium.net 에서 다운로드 안내

### 2단계: 인증

**git인 경우** → GH 인증을 수행한다:

1. `gh auth status` 로 인증 상태 확인
2. 인증됨 → `GH 인증 : 완료 ✅` 출력
3. 미인증 → 아래 절차로 device flow 인증을 진행한다:

#### 2-1. Device code 발급

```bash
gh auth login --hostname github.com --git-protocol https --web 2>&1
```
- `timeout: 120000` (2분, config.json `timeouts.network` 값) 설정
- 이 명령은 **one-time code**와 인증 URL을 출력한다

#### 2-2. 사용자에게 안내

출력에서 코드와 URL을 파싱하여 아래 형식으로 안내한다:

```
🔐 GitHub 인증이 필요합니다.

1. 브라우저에서 이 URL을 열어주세요: https://github.com/login/device
2. 아래 코드를 입력하세요: XXXX-XXXX
3. GitHub 계정으로 로그인하면 인증이 완료됩니다.

인증을 완료하면 알려주세요.
```

사용자에게 인증 완료 여부를 묻는다:
```
AskUserQuestion(
  questions: [{
    header: "GH 인증",
    question: "GitHub 로그인을 완료하셨나요?",
    multiSelect: false,
    options: [
      { label: "완료", description: "인증을 완료했습니다. 다음 단계로 진행합니다" },
      { label: "재시도", description: "인증 URL을 다시 표시합니다" }
    ]
  }]
)
```

#### 2-3. 인증 확인

사용자가 완료를 알리면 `gh auth status`로 인증 성공 여부를 확인한다.
- 성공 → `GH 인증 : 완료 ✅` 출력
- 실패 → 에러 메시지를 보여주고, 2-1부터 재시도할지 사용자에게 묻는다

**svn인 경우** → SVN 자격 증명 캐시 여부만 확인한다:

1. `svn info`로 현재 워킹 카피의 인증 상태를 확인한다.
   - 성공 (자격 증명 캐시됨) → `SVN 인증 : 완료 ✅ (캐시된 자격 증명 사용)` 출력.
   - 실패 (인증 오류) → 아래 안내 후 **진행한다** (자격 증명을 직접 수집하지 않는다):
     ```
     SVN 인증 : 미설정

     보안상 SVN 사용자명/비밀번호를 대화로 수집하지 않습니다.
     터미널에서 직접 아래 명령으로 자격 증명을 캐시한 뒤 다시 실행해주세요:

       svn info <저장소 URL>

     최초 1회 인증 성공 시 SVN이 자격 증명을 자동 캐시합니다.
     ```
   - `SVN 인증 : 건너뜀` 출력 후 다음 단계로 진행.

2. **주의**: 어떤 경우에도 AskUserQuestion으로 사용자명/비밀번호를 수집하지 않는다. 비밀번호는 프롬프트 히스토리, 세션 로그, 옵션 description 등에 노출될 위험이 있다.

### 3단계: context/ 초기 구조 안내

프로젝트 루트에 `context/` 디렉토리가 없으면:
- "도메인 지식을 관리하려면 `/gx-context`로 context/ 디렉토리를 생성하세요." 안내

이미 있으면 건너뛴다.

### 4단계: Google Chat 알림 연동 (선택)

**svn인 경우** → 건너뛴다. `Google Chat 연동 : 건너뜀 (SVN — PR 기반 알림 미지원)` 출력.

**git인 경우:**

1. `.claude/config.json`의 `notifications.googleChat` 확인:
   - `webhookUrl`이 이미 채워져 있으면 →
     `Google Chat 연동 : 완료 ✅ (기존 설정 사용)` 출력. 건너뜀.
   - `webhookUrl`이 비어있으면 → 2번으로.

2. 사용자에게 연동 여부를 묻는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "Chat 연동",
       question: "Google Chat 웹훅 알림을 연동하시겠습니까? (PR 생성 시 Chat Space에 알림)",
       multiSelect: false,
       options: [
         { label: "연동", description: "웹훅 URL을 입력받아 연동합니다" },
         { label: "건너뛰기", description: "연동하지 않고 진행합니다" }
       ]
     }]
   )
   ```
   - "건너뛰기" → 건너뜀
   - "연동" → 3번으로

3. 웹훅 URL 생성 가이드를 표시한 후 AskUserQuestion으로 URL을 받는다:

   ```
   📋 Google Chat 웹훅 URL 생성 방법

   1. Google Chat에서 알림을 받을 스페이스를 엽니다.
      (스페이스가 없으면 '+ 새 스페이스'로 먼저 생성하세요)
   2. 스페이스 상단의 스페이스 이름을 클릭합니다.
   3. '앱 및 통합' 탭을 선택합니다.
   4. '+ 웹훅 추가'를 클릭합니다.
   5. 웹훅 이름(예: 'Claude Code')을 입력하고 '저장'을 누릅니다.
   6. 생성된 웹훅 URL을 복사합니다.
   ```

   ```
   AskUserQuestion(
     questions: [{
       header: "웹훅 URL 입력",
       question: "위 방법으로 생성한 Google Chat 웹훅 URL을 입력해주세요.",
       multiSelect: false,
       options: [
         { label: "Other로 입력", description: "Other로 이동해서 웹훅 URL을 붙여넣어주세요" },
         { label: "건너뛰기", description: "나중에 설정합니다" }
       ]
     }]
   )
   ```

   - 건너뛰기 → 건너뜀
   - URL 입력 → `https://chat.googleapis.com/` 시작 여부 검증
   - 유효하지 않으면 1회 재입력 요청. 재입력도 유효하지 않으면 건너뜀.
   - 유효하면 → config.json 갱신 (`enabled: true`, `webhookUrl: URL`)
     `Google Chat 연동 : 완료 ✅` 출력

### 5단계: 모델 프로파일 (선택)

gx-dev·gx-tdd가 에이전트를 디스패치할 때 사용할 모델 프로파일을 설정한다. 파이프라인 절차는 동일하고 에이전트 모델 수준만 달라진다.

0. **세션 확정값 우선**: 이 스킬이 파이프라인의 config 부트스트랩(phase-setup config 가드의 `Skill("oh-my-gx:gx-setup")` 호출)으로 실행되었고, 이번 세션에서 모델 프로파일이 이미 확정된 경우(플래그·자연어·모드 확인 질문 답변) → **질문 없이 그 확정 값을 config.json에 기록**하고 `모델 프로파일 : 완료 ✅ ({값}, 세션 확정값 기록)` 출력 후 완료 단계로 진행한다 (프로파일 이중 질문 방지).
1. `.claude/config.json`의 `"modelProfile"` 필드를 확인한다:
   - 값이 이미 설정되어 있으면 (`"standard"` 또는 `"eco"`) → `모델 프로파일 : 완료 ✅ ({값}, 기존 설정 유지)` 출력 후 완료 단계로 진행.
   - 비어있으면 → 2번으로.
2. 사용자에게 프로파일을 묻는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "모델 프로파일",
       question: "에이전트 모델 프로파일을 선택해주세요. 절차·게이트는 동일하고 에이전트가 사용하는 모델 수준만 달라집니다.",
       multiSelect: false,
       options: [
         { label: "표준", description: "에이전트 기본 모델 그대로 (설계 등 핵심에 opus) — 품질 우선 (Max 요금제 권장)" },
         { label: "에코", description: "설계(architect)를 제외한 opus 에이전트를 sonnet으로 하향 — 토큰 절약 (Pro 요금제 권장). 빌드·테스트·verify 게이트는 동일하게 유지" }
       ]
     }]
   )
   ```
3. 선택 값을 `.claude/config.json`의 `"modelProfile"`에 기록한다 (표준 → `"standard"`, 에코 → `"eco"`).
4. 에코 선택 시 1줄 안내: "메인 세션 모델은 플러그인이 제어하지 않습니다. 토큰 절약이 목적이면 세션 모델도 Sonnet 사용을 권장합니다."
5. `모델 프로파일 : 완료 ✅ ({값})` 출력. 실행별 오버라이드는 `/gx-dev`·`/gx-tdd`의 `--eco`/`--standard` 플래그로 가능하다.

### 완료: 퀵스타트

**git인 경우:**
```
=== 퀵스타트 ===
/gx-context {도메인}     → 도메인 지식 등록
/gx-lens {질문}          → 현행 분석 + 영향도
/gx-dev {요청}           → 전체 개발 사이클 (PRD~PR)
/gx-tdd {요청}           → TDD 강제 개발 사이클 (RGR + verify 게이트)

💡 화면 설계서가 있다면:
requirements/ 폴더에 넣고 /gx-context {도메인} --from requirements/ 로 등록
```

**svn인 경우:**
```
=== 퀵스타트 ===
/gx-context {도메인}     → 도메인 지식 등록
/gx-lens {질문}          → 현행 분석 + 영향도
/gx-dev {요청}           → 개발 사이클 (PRD~리뷰)
/gx-tdd {요청}           → TDD 강제 개발 사이클 (RGR + verify 게이트)

⚠️ SVN 프로젝트:
- /gx-commit, /gx-pull-request는 SVN에서 미지원
- /gx-dev 리뷰까지 완료 후 svn commit은 직접 수행하세요
```

## 주의사항

- 각 단계를 **하나씩** 실행하고, 실패하면 원인을 파악하여 사용자에게 안내한다.
- 설치 도중 에러가 나면 멈추고 사용자에게 상황을 설명한다.
- 이미 완료된 항목은 재실행하지 않고 `완료 ✅` 만 출력한다.
- `config.json`의 `vcs` 값이 이미 설정되어 있는 경우, 0단계에서는 감지된 VCS와 일치하는지 확인하며, 다를 경우 사용자에게 물어본다.
