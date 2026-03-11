---
name: setup
version: 5.0.0
argument-hint: "없음"
description: |
  플러그인 초기 설정.
  필수 도구 확인, GH 인증을 단계별로 수행합니다.
allowed-tools:
  - "Bash(curl *)"
  - "Bash(gh *)"
  - "Bash(git *)"
  - "Bash(which *)"
  - "Bash(command *)"
  - "Bash(uname *)"
  - "Bash(java *)"
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

### 1단계: 필수 도구 확인

#### gh

| 도구 | 확인 |
|------|------|
| gh | `which gh` |

1. `which gh` 실행
2. 있으면 → `gh : 완료 ✅` 출력
3. 없으면 → 설치 링크를 안내 (https://cli.github.com)

#### JDK

1. `uname -s`로 OS를 감지한다.
2. `java -version`으로 JDK 설치 여부와 버전을 확인한다.
3. JDK 8 이상이 설치되어 있으면 → `JDK : 완료 ✅ (버전)` 출력
4. 없거나 버전이 낮으면 → OS별 설치 안내를 제공한다:
   - **Linux**: `sudo apt install openjdk-17-jdk` 또는 `sudo yum install java-17-openjdk-devel`
   - **macOS**: `brew install openjdk@17`
   - **Windows (MSYS/Git Bash)**: https://adoptium.net 에서 다운로드 안내

### 2단계: GH 인증

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

### 3단계: context/ 초기 구조 안내

프로젝트 루트에 `context/` 디렉토리가 없으면:
- "도메인 지식을 관리하려면 `/context`로 context/ 디렉토리를 생성하세요." 안내

이미 있으면 건너뛴다.

### 4단계: Google Chat 알림 연동 (선택)

1. `.claude/config.json`의 `notifications.googleChat` 확인:
   - `webhookUrl`이 이미 채워져 있으면 →
     `Google Chat 연동 : 완료 ✅ (기존 설정 사용)` 출력. 건너뜀.
   - `webhookUrl`이 비어있으면 → 2번으로.

2. AskUserQuestion: "Google Chat 웹훅 알림을 연동하시겠습니까? (PR 생성 시 Chat Space에 알림)"
   - 아니오 → 건너뜀
   - 예 → 3번으로

3. AskUserQuestion: "Google Chat 스페이스의 웹훅 URL을 입력하세요."
   - `https://chat.googleapis.com/` 시작 여부 검증
   - 유효하지 않으면 1회 재입력 요청. 재입력도 유효하지 않으면 건너뜀.
   - 유효하면 → config.json 갱신 (`enabled: true`, `webhookUrl: URL`)
     `Google Chat 연동 : 완료 ✅` 출력

### 완료: 퀵스타트

```
=== 퀵스타트 ===
/context {도메인}     → 도메인 지식 등록
/lens {질문}          → 현행 분석 + 영향도
/dev {요청}           → 전체 개발 사이클 (PRD~PR)

💡 화면 설계서가 있다면:
requirements/ 폴더에 넣고 /context {도메인} --from requirements/ 로 등록
```

## 주의사항

- 각 단계를 **하나씩** 실행하고, 실패하면 원인을 파악하여 사용자에게 안내한다.
- 설치 도중 에러가 나면 멈추고 사용자에게 상황을 설명한다.
- 이미 완료된 항목은 재실행하지 않고 `완료 ✅` 만 출력한다.
