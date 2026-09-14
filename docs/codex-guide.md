---
layout: default
title: Codex 사용 가이드
permalink: /codex/
---

# Codex에서 oh-my-gx 사용하기

**설치 → 프로젝트에서 Codex 실행 → setup → 원하는 스킬 요청** 순서로 시작합니다. 확인한 환경은 Windows Codex CLI 0.154.0입니다.

## 1. 설치

Codex 로그인, Git, Python 3.10 이상이 필요합니다. Windows에서는 Git for Windows의 Git Bash도 사용합니다. 테스트·빌드 도구는 프로젝트 언어에 맞게 준비합니다.

### 수정본을 지금 처음 설치할 때

[PR #89](https://github.com/bs-koo/oh-my-gx/pull/89)의 수정 브랜치를 설치하는 PowerShell 명령입니다. 이 경로로 실제 설치와 GX 스킬 17개를 확인했습니다.

```powershell
codex.cmd plugin marketplace add bs-koo/oh-my-gx --ref feat/codex-native-validation
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

`--ref`는 해당 브랜치를 선택합니다. **PR이 main에 반영된 뒤 기본 브랜치를 처음 설치할 때는** 첫 명령에서 `--ref feat/codex-native-validation`을 생략합니다. 이미 설치한 경우에는 아래 갱신 절차를 참고하세요. Bash에서는 `codex.cmd` 대신 `codex`를 사용합니다. Linux의 실제 모델 세션과 macOS는 아직 실측하지 않았습니다.

작업할 프로젝트 폴더로 이동해 새 Codex 세션을 엽니다.

```powershell
cd C:\path\to\your-project
codex.cmd
```

Codex 입력창에서 `/skills`로 GX 스킬을 확인하고, `/hooks`로 GX 훅 정의와 신뢰 상태를 확인합니다. 훅이 표시되지 않거나 신뢰되지 않으면 보호 훅이 실행된다고 볼 수 없습니다.

## 2. 채팅으로 사용

아래 요청을 **한 단계씩 Codex 채팅창에** 입력합니다. 터미널 명령이 아닙니다.

```text
oh-my-gx:gx-setup 스킬로 이 프로젝트를 준비해줘.
```

setup이 프로젝트의 테스트·빌드 명령과 설정을 확인합니다. 기존 `.claude/config.json`의 사용자 정의 설정을 보존하며, Codex에서도 이 파일을 공통 프로젝트 설정으로 사용합니다.

```text
oh-my-gx:gx-tdd --core로 로그인 입력 검증을 테스트 먼저 구현해줘.
```

요구사항·설계와 필요한 선택에 답하면 RED 테스트 → 구현 → 검증을 진행합니다. 일반 개발을 원하면 `oh-my-gx:gx-dev로 로그인 화면을 만들어줘`처럼 요청할 수 있습니다.

```text
oh-my-gx:gx-cross-review --advisor native로 변경사항을 검토해줘.
oh-my-gx:gx-verify로 테스트와 빌드를 실행해 검증해줘.
```

Codex 안에서는 먼저 `--advisor native`를 사용하세요. 현재 Codex의 역할 에이전트로 리뷰하며, 외부 Codex를 다시 실행할 때 발생할 수 있는 홈 디렉터리 권한 문제를 피할 수 있습니다.

검증 후 Git 작업까지 맡기려면 별도로 요청합니다.

```text
oh-my-gx:gx-commit으로 이번 변경을 커밋해줘.
oh-my-gx:gx-pull-request로 main 대상 PR을 만들어줘.
```

커밋·PR은 작업 브랜치에서 진행합니다. 보호 브랜치나 검증 미통과·검증 후 코드 변경 상태에서는 중단합니다. Codex의 일반 권한 승인도 필요할 수 있으며 PR 머지는 별도 요청 사항입니다.

## 3. Superpowers와 함께 사용

Superpowers와 GX는 별도 플러그인입니다. GX 사용에 Superpowers 설치가 필수는 아닙니다. 둘 다 설치했다면 사용할 스킬 이름을 명시하세요.

| 원하는 작업 | 채팅 예시 |
|---|---|
| Superpowers로 계획 작성 | `Superpowers writing-plans로 구현 계획을 작성해줘` |
| GX로 프로젝트 준비 | `oh-my-gx:gx-setup 스킬로 준비해줘` |
| GX로 테스트부터 구현 | `oh-my-gx:gx-tdd --core로 이 기능을 구현해줘` |
| GX로 검토·검증 | `oh-my-gx:gx-cross-review --advisor native로 검토하고 gx-verify로 검증해줘` |

## 4. 갱신과 문제 확인

현재 등록된 Git marketplace를 새로 가져온 뒤 플러그인을 다시 설치하고 새 세션을 엽니다.

```powershell
codex.cmd plugin marketplace list --json
codex.cmd plugin marketplace upgrade oh-my-gx
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

갱신은 **등록된 ref**를 따릅니다. 수정 브랜치를 등록했다면 갱신만으로 main으로 전환되지 않습니다. 버전 숫자만 보지 말고 marketplace와 설치 상태도 확인하세요.

| 증상 | 확인할 것 |
|---|---|
| GX 스킬이 안 보임 | 설치 목록·활성 상태를 확인하고 새 Codex 세션에서 `/skills` 확인 |
| 보호 훅이 안 보임 | `/hooks`에서 GX 정의·신뢰 확인 |
| 외부 Codex 리뷰가 권한 오류로 중단됨 | `--advisor native`로 요청 |
| Ralph가 BLOCKED로 종료됨 | 차단 사유 확인; 무인 커밋에 필요한 권한을 자동 우회하지 않음 |

설치와 핵심 작업 흐름을 실측했지만 모든 Claude 동작과의 동등성을 보장하지는 않습니다. RED 역할의 구현 소스 미열람은 독립 trace가 없어 미확인이며, 역할 도구 목록은 권한을 강제하는 경계가 아닙니다. 전체 결과는 [실측 보고서](https://github.com/bs-koo/oh-my-gx/blob/feat/codex-native-validation/docs/reports/2026-09-14-codex-validation.md)를 참고하세요.
