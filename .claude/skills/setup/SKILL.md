---
name: setup
argument-hint: "없음"
description: >
  플러그인 초기 설정. VCS 감지, 필수 도구 확인, 인증을 단계별로 수행한다.
  사용자가 "설정", "셋업", "setup", "초기화"라고 말하면 이 스킬을 사용한다.
disable-model-invocation: true
allowed-tools:
  - "Bash(curl *)"
  - "Bash(gh *)"
  - "Bash(git *)"
  - "Bash(svn *)"
  - "Bash(which *)"
  - "Bash(command *)"
  - "Bash(uname *)"
  - "Bash(java *)"
  - "Bash(winget *)"
  - "Bash(choco *)"
  - "Bash(scoop *)"
  - "Bash(brew *)"
  - "Bash(sudo *)"
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

1. 프로젝트 루트에서 `.git/` 디렉토리 존재 여부를 확인한다 (`test -d .git`).
2. 프로젝트 루트에서 `.svn/` 디렉토리 존재 여부를 확인한다 (`test -d .svn`).
3. 결과에 따라 분기:
   - `.git/`만 존재 → `VCS_TYPE = "git"`
   - `.svn/`만 존재 → `VCS_TYPE = "svn"`
   - 둘 다 존재 → AskUserQuestion: "Git과 SVN이 모두 감지되었습니다. 어떤 VCS를 사용하시겠습니까?" 선택지: `git`, `svn`
   - 둘 다 없음 → AskUserQuestion: "VCS를 감지하지 못했습니다. 사용 중인 VCS를 선택해주세요." 선택지: `git`, `svn`, `없음 (VCS 미사용)`
     - `없음` 선택 시 → "VCS 없이는 커밋/PR 기능을 사용할 수 없습니다." 안내 후 `VCS_TYPE = ""`
4. `.claude/config.json`의 `"vcs"` 필드를 확인한다:
   - 이미 값이 설정되어 있고 감지 결과와 **동일**하면 → 갱신 없이 `VCS 감지 : 완료 ✅ ({VCS_TYPE}, 기존 설정 유지)` 출력.
   - 이미 값이 설정되어 있지만 감지 결과와 **다르면** → AskUserQuestion: "기존 설정({기존값})과 감지 결과({감지값})가 다릅니다. 어떤 값을 사용하시겠습니까?" 선택지: 기존값, 감지값.
   - 값이 비어있으면 → `VCS_TYPE` 값으로 갱신한다 (Edit).
5. `VCS 감지 : 완료 ✅ ({VCS_TYPE})` 출력.

이후 단계는 `VCS_TYPE`에 따라 분기한다.

### 1단계: 필수 도구 확인

#### VCS CLI

| VCS_TYPE | 도구 | 확인 |
|----------|------|------|
| git | gh | `which gh` |
| svn | svn | `which svn` → `svn --version` |

**git인 경우:**
1. `which gh` 실행
2. 있으면 → `gh : 완료 ✅` 출력
3. 없으면 → 설치 링크를 안내 (https://cli.github.com)

**svn인 경우:**
1. `which svn` 실행
2. 있으면 → `svn --version --quiet`로 버전 확인 → `svn : 완료 ✅ (버전)` 출력
3. 없으면 → 패키지 매니저를 감지하여 자동 설치를 시도한다:

   **설치 시도 순서:**
   a. OS와 패키지 매니저를 감지한다 (위에서부터 순서대로, 먼저 감지된 것을 사용):
      - `which winget` → Windows (winget, Windows 10/11 기본 내장)
      - `which choco` → Windows (Chocolatey)
      - `which scoop` → Windows (Scoop)
      - `which brew` → macOS/Linux (Homebrew)
      - `which apt` → Linux (apt)
      - `which yum` → Linux (yum)

   b. 패키지 매니저가 감지되면 AskUserQuestion:
      ```
      question: "SVN CLI가 설치되어 있지 않습니다. 자동 설치하시겠습니까?"
      options:
        - { value: "install", label: "설치 — {감지된 패키지 매니저}로 SVN CLI 설치" }
        - { value: "skip", label: "건너뛰기 — 나중에 직접 설치" }
      ```

   c. "설치" 선택 시 감지된 패키지 매니저로 설치 (`timeout: 300000`):
      | 패키지 매니저 | 설치 명령 |
      |-------------|----------|
      | winget | `winget install --id TortoiseSVN.TortoiseSVN --accept-source-agreements --accept-package-agreements` |
      | choco | `choco install svn -y` |
      | scoop | `scoop install svn` |
      | brew | `brew install subversion` |
      | apt | `sudo apt install -y subversion` |
      | yum | `sudo yum install -y subversion` |

   d. 설치 완료 후 `which svn`으로 재확인 → 성공하면 `svn : 완료 ✅` 출력
   e. 설치 실패 시 → 수동 설치 안내 출력 후 계속 진행

   f. 패키지 매니저가 감지되지 않으면 → 수동 설치 안내:
      - **Windows**: https://tortoisesvn.net (설치 시 "command line client tools" 옵션 체크) 또는 Chocolatey/Scoop 설치 후 `/setup` 재실행
      - **macOS**: `brew install subversion` (Homebrew 먼저 설치)
      - **Linux**: `sudo apt install subversion` 또는 `sudo yum install subversion`

#### JDK

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
- `timeout: 120000` (2분) 설정
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

`AskUserQuestion`으로 사용자가 인증 완료를 알릴 때까지 대기한다.

#### 2-3. 인증 확인

사용자가 완료를 알리면 `gh auth status`로 인증 성공 여부를 확인한다.
- 성공 → `GH 인증 : 완료 ✅` 출력
- 실패 → 에러 메시지를 보여주고, 2-1부터 재시도할지 사용자에게 묻는다

**svn인 경우** → 건너뛴다. `인증 : 건너뜀 (SVN)` 출력.

### 3단계: context/ 초기 구조 안내

프로젝트 루트에 `context/` 디렉토리가 없으면:
- "도메인 지식을 관리하려면 `/context`로 context/ 디렉토리를 생성하세요." 안내

이미 있으면 건너뛴다.

### 4단계: Google Chat 알림 연동 (선택)

**svn인 경우** → 건너뛴다. `Google Chat 연동 : 건너뜀 (SVN — PR 기반 알림 미지원)` 출력.

**git인 경우:**

1. `.claude/config.json`의 `notifications.googleChat` 확인:
   - `webhookUrl`이 이미 채워져 있으면 →
     `Google Chat 연동 : 완료 ✅ (기존 설정 사용)` 출력. 건너뜀.
   - `webhookUrl`이 비어있으면 → 2번으로.

2. AskUserQuestion: "Google Chat 웹훅 알림을 연동하시겠습니까? (PR 생성 시 Chat Space에 알림)"
   - 아니오 → 건너뜀
   - 예 → 3번으로

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

   AskUserQuestion:
   ```
   question: "위 방법으로 생성한 Google Chat 웹훅 URL을 입력해주세요."
   options:
     - { label: "건너뛰기", description: "나중에 설정합니다" }
   ```

   - 건너뛰기 → 건너뜀
   - URL 입력 → `https://chat.googleapis.com/` 시작 여부 검증
   - 유효하지 않으면 1회 재입력 요청. 재입력도 유효하지 않으면 건너뜀.
   - 유효하면 → config.json 갱신 (`enabled: true`, `webhookUrl: URL`)
     `Google Chat 연동 : 완료 ✅` 출력

### 완료: 퀵스타트

**git인 경우:**
```
=== 퀵스타트 ===
/context {도메인}     → 도메인 지식 등록
/lens {질문}          → 현행 분석 + 영향도
/dev {요청}           → 전체 개발 사이클 (PRD~PR)

💡 화면 설계서가 있다면:
requirements/ 폴더에 넣고 /context {도메인} --from requirements/ 로 등록
```

**svn인 경우:**
```
=== 퀵스타트 ===
/context {도메인}     → 도메인 지식 등록
/lens {질문}          → 현행 분석 + 영향도
/dev {요청}           → 개발 사이클 (PRD~리뷰)

⚠️ SVN 프로젝트:
- /commit, /pull-request는 SVN에서 미지원
- /dev 리뷰까지 완료 후 svn commit은 직접 수행하세요
```

## 주의사항

- 각 단계를 **하나씩** 실행하고, 실패하면 원인을 파악하여 사용자에게 안내한다.
- 설치 도중 에러가 나면 멈추고 사용자에게 상황을 설명한다.
- 이미 완료된 항목은 재실행하지 않고 `완료 ✅` 만 출력한다.
- `config.json`의 `vcs` 값이 이미 설정되어 있는 경우, 0단계에서는 감지된 VCS와 일치하는지 확인하며, 다를 경우 사용자에게 물어본다.
