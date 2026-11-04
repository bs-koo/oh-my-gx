---
name: gx-setup
argument-hint: "없음"
description: GX 플러그인의 초기 설정을 요청할 때 사용한다. 버전 관리와 빌드·테스트 설정을 등록하고 필수 도구와 인증 상태를 확인한다.
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

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("../gx-work/references/codex-runtime.md")`로 공통 실행 규약을 읽고, 이 스킬의 절차·게이트를 유지한다. 상대경로는 이 SKILL.md 위치 기준이다.
Codex config helper의 설치 경로는 **이 SKILL.md 디렉토리 기준** [../../../scripts/codex-project-config.py](../../../scripts/codex-project-config.py)다. 실제 설치된 SKILL.md 절대경로 `SKILL_PATH`에 대해 `Path(SKILL_PATH).resolve().parents[3]`가 `GX_PLUGIN_ROOT`이며, `.codex-plugin/plugin.json`과 helper의 존재를 확인한다. Windows PowerShell: `$skillPath = (Resolve-Path -LiteralPath '<installed SKILL.md>').Path; $pluginRoot = (Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $skillPath) '..\..\..')).Path; $helper = (Resolve-Path -LiteralPath (Join-Path $pluginRoot 'scripts/codex-project-config.py')).Path`. 아래 config 명령의 `<GX_PLUGIN_ROOT>`는 이 경로로만 치환하고, Windows에서는 확인한 `$helper` 절대경로를 사용한다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → 공통 codex-runtime의 질문 대기 계약으로 옮긴다. 실제 모드·용도가 허용하는 `request_user_input`·`request_user_input_async` 또는 자연어를 사용한다. 필수 질문은 pending 상태를 저장하고 실제 답변·결정 기록 전 다음 단계로 넘어가지 않는다. async 반환은 답변이 아니며 본문·선택지를 표시한다.
- `Skill(skill: "oh-my-gx:{name}")` → 해당 스킬의 `SKILL.md`를 읽어 그 절차를 수행한다.

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.

**Codex config 기록 규칙 (이 스킬 전체에 우선)**: 소비 프로젝트 `.claude/config.json`의 최초 생성과 이후 모든 값 변경은 설치된 GX 플러그인 루트의 `scripts/codex-project-config.py`만 사용한다. 이 SKILL.md 기준 `references/config.template.json`의 **실제 설치 절대경로**, 소비 프로젝트 루트 절대경로, 이번 단계에서 사용자가 확정한 필드만 담은 임시 UTF-8 JSON 파일을 준비해 `python "<GX_PLUGIN_ROOT>/scripts/codex-project-config.py" --cwd "<PROJECT_ROOT>" --template "<INSTALLED_TEMPLATE>" --updates "<UPDATES_JSON>"`을 실행한다 (Linux는 `python3`). 기존 config를 전체 객체로 재구성하거나 `Write`/`Edit`로 덮어쓰지 않는다. updates는 중첩 JSON 객체로 쓰고 미확정 필드를 넣지 않는다. 예: VCS만 확정되면 `{"vcs":"git"}`, 프로젝트 타입의 build/test만 확정되면 `{"projectTypes":{"node":{"build":"npm run build","test":"npm test"}}}`. helper는 기존 객체의 **알 수 없는 필드까지 보존**하도록 재귀 병합한다. 각 호출 후 `.claude/config.json`을 다시 읽어 JSON 파싱과 확정 필드·기존 사용자 값 보존을 확인한다. helper 부재·비정상 종료·파싱 실패·기존 값 소실이면 setup을 중단하고 완료를 표시하지 않는다. 임시 updates 파일은 소비 프로젝트 밖에 만들고 사용 후 제거한다. Claude Code는 아래 기존 Read/Write/Edit 절차를 유지한다.

## 실행 절차

아래 단계를 **순서대로** 실행한다. 각 단계 완료 시 `{항목} : 완료 ✅` 형식으로 출력한다.

### 0단계: VCS 감지

프로젝트의 버전 관리 시스템을 감지하고 `.claude/config.json`에 저장한다.

0. **config.json 생성·검증** (다른 단계보다 먼저): 기존 소비 프로젝트 `.claude/config.json`이 있으면 읽고 JSON으로 파싱한다. 오류가 있으면 파일 경로와 오류를 보고하고 setup을 중단한다. 기존 설정은 자동 덮어쓰지 않는다.
   - **없으면**: 이 SKILL.md 위치 기준 `Read("references/config.template.json")`로 번들 템플릿을 UTF-8로 읽고 JSON으로 파싱한다. 로드나 파싱이 실패하면 실패 파일 경로를 보고하고 setup을 중단한다. Codex에서는 위 helper에 빈 updates 객체 `{}`를 전달해 템플릿에서 생성한다. Claude Code에서는 정상 템플릿을 소비 프로젝트 `.claude/config.json`에 기록한다. 이후 **다시 읽어 JSON으로 파싱한다**. 재검증에 성공했을 때만 `config.json 생성 : 완료 ✅`를 출력하고 아래 1로 진행한다. 쓰기/재읽기 실패면 완료를 표시하지 않고 중단한다.
   - **있으면**: 기존 JSON 파싱 성공 후 아래 1로 진행한다.
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
4. `.claude/config.json`의 `"vcs"` 필드를 `VCS_TYPE` 값으로 갱신한다. Codex에서는 위 helper의 updates `{"vcs":"{VCS_TYPE}"}`만 사용한다. Claude Code는 기존 Edit를 사용한다.
5. `VCS 감지 : 완료 ✅ ({VCS_TYPE})` 출력.

이후 단계는 `VCS_TYPE`에 따라 분기한다.

### 0.5단계: 프로젝트 타입 등록

이번 실행의 프로젝트 타입·detect·build/test·focusedTest 등록 및 하네스 확인은 `Read("references/project-type-registration.md")`를 읽고 수행한다. SSOT는 config이며 기존 등록 유지·복수 타입·사용자 확인·권한 보존 게이트를 유지한다.

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
   /gx-work의 자기점검·리뷰 단계에서 svn diff가 필요합니다.

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

VCS_TYPE이 git이면 `Read("references/authentication-git.md")`, svn이면 `Read("references/authentication-svn.md")`를 읽어 해당 경로만 수행한다. SVN 사용자명·비밀번호를 대화로 수집하지 않는다. git은 gh auth status로 기존 인증을 확인하며 필요할 때만 device flow를 진행한다.

### 3단계: context/ 초기 구조 안내

프로젝트 루트에 `context/` 디렉토리가 없으면:
- "도메인 지식을 관리하려면 `/gx-context`로 context/ 디렉토리를 생성하세요." 안내

이미 있으면 건너뛴다.

### 3.5단계: .dev 공유 확인 (git)

git 저장소면 `Read("../gx-work/references/dev-ignore-check.md")`의 `.dev` 공유 확인을 수행한다. 작업 계획(`.dev/plan.md`)과 파이프라인 산출물이 팀에 공유되려면 `.dev/`가 git에서 무시되지 않아야 한다. 처음 설정할 때 한 번 잡아 두면 이후 gx-context·gx-dev가 같은 질문을 반복하지 않는다. svn이면 건너뛴다.

### 4단계: Google Chat 알림 연동 (선택)

svn이면 `Google Chat 연동 : 건너뜀 (SVN — PR 기반 알림 미지원)`을 출력한다. git에서 기존 webhookUrl이 있으면 기존 설정을 유지하고 완료를 표시한다. git에서 webhookUrl이 비어있을 때만 `Read("references/google-chat.md")`의 연동 여부 질문부터 수행한다. 사용자 선택 전 URL을 수집하거나 설정을 바꾸지 않는다.

### 5단계: 모델 프로파일 (선택)

gx-work·gx-tdd가 에이전트를 디스패치할 때 사용할 모델 프로파일을 설정한다. 파이프라인 절차는 동일하고 에이전트 모델 수준만 달라진다.

0. **세션 확정값 우선**: 이 스킬이 파이프라인의 config 부트스트랩(phase-setup config 가드의 `Skill("oh-my-gx:gx-setup")` 호출)으로 실행되었고, 이번 세션에서 모델 프로파일이 이미 확정된 경우(플래그·자연어·모드 확인 질문 답변) → **질문 없이 그 확정 값을 config.json에 기록**하고 `모델 프로파일 : 완료 ✅ ({값}, 세션 확정값 기록)` 출력 후 완료 단계로 진행한다 (프로파일 이중 질문 방지). Codex 기록은 위 helper의 `{"modelProfile":"{확정값}"}` updates만 사용한다.
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
         { label: "표준", description: "역할별 기본 high/mid 모델 수준을 유지합니다. 실제 모델은 현재 하네스에서 지원하는 모델로 결정합니다" },
         { label: "에코", description: "architect를 유지하고 지정된 high 역할을 mid로 낮춥니다. 빌드·테스트·verify와 메인 세션 모델은 유지합니다" }
       ]
     }]
   )
   ```
3. 선택 값을 `.claude/config.json`의 `"modelProfile"`에 기록한다 (표준 → `"standard"`, 에코 → `"eco"`). Codex는 위 helper의 `{"modelProfile":"{확정값}"}` updates만 사용한다. Claude Code는 기존 Edit를 사용한다.
4. 에코 선택 시 1줄 안내: "메인 세션 모델은 플러그인이 제어하지 않습니다. 토큰 절약이 목적이면 세션 모델도 Sonnet 사용을 권장합니다."
5. `모델 프로파일 : 완료 ✅ ({값})` 출력. 실행별 오버라이드는 `/gx-work`·`/gx-tdd`의 `--eco`/`--standard` 플래그로 가능하다.

### 완료: 퀵스타트

**git인 경우:**
```
=== 퀵스타트 ===
/gx-context {도메인}     → 도메인 지식 등록
/gx-lens {질문}          → 현행 분석 + 영향도
/gx-work {요청}           → 전체 개발 사이클 (PRD~PR)
/gx-tdd {요청}           → TDD 강제 개발 사이클 (RGR + verify 게이트)

💡 화면 설계서가 있다면:
requirements/ 폴더에 넣고 /gx-context {도메인} --from requirements/ 로 등록
```

**svn인 경우:**
```
=== 퀵스타트 ===
/gx-context {도메인}     → 도메인 지식 등록
/gx-lens {질문}          → 현행 분석 + 영향도
/gx-work {요청}           → 개발 사이클 (PRD~리뷰)
/gx-tdd {요청}           → TDD 강제 개발 사이클 (RGR + verify 게이트)

⚠️ SVN 프로젝트:
- /gx-commit, /gx-pull-request는 SVN에서 미지원
- /gx-work 리뷰까지 완료 후 svn commit은 직접 수행하세요
```

### Codex 모델 설정 안내

Codex에서는 [모델 정책](../gx-work/references/codex-models.md)을 참조한다. config의 `codex.modelTiers`가 없거나 비어 있으면 helper 기본값을 사용한다. 사용자가 역할 티어별 모델·effort를 지정하면 `codex-project-config.py`에 `{"codex":{"modelTiers":{확정한 티어만}}}` updates를 전달해 기존 사용자 설정을 보존한다. setup은 현재 세션의 spawn allowlist·effort와 대조해 지원 여부를 표시하며, 임의로 전역 `~/.codex/config.toml`이나 메인 모델을 변경하지 않는다. 질문은 공통 pending 계약으로 실제 응답을 기다린다. 세션 정보가 없으면 모델 설정이 검증됐다고 표시하지 않는다.

## 주의사항

- 각 단계를 **하나씩** 실행하고, 실패하면 원인을 파악하여 사용자에게 안내한다.
- 설치 도중 에러가 나면 멈추고 사용자에게 상황을 설명한다.
- 이미 완료된 항목은 재실행하지 않고 `완료 ✅` 만 출력한다.
- `config.json`의 `vcs` 값이 이미 설정되어 있는 경우, 0단계에서는 감지된 VCS와 일치하는지 확인하며, 다를 경우 사용자에게 물어본다.
