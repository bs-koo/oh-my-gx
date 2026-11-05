---
layout: default
title: Codex 사용 가이드
permalink: /codex/
---

# Codex에서 oh-my-gx 사용하기

oh-my-gx는 프로젝트 지식 관리, 요구사항 정의, 설계·구현·리뷰·검증과 PR 생성을 지원하는 개발 워크플로입니다. Claude Code와 Codex에서 도메인 문서와 작업 계획을 정리하고, 테스트 주도 개발(TDD), 코드 리뷰, 최종 검증을 연결합니다. 설치 패키지는 `oh-my-gx`이며 커밋·PR은 요청한 범위에 따라 진행합니다.

**설치 → 프로젝트에서 Codex 실행 → 환경 설정 → gx-work로 작업 요청** 순서로 시작합니다. 이전 버전의 실측 환경은 Windows Codex CLI 0.154.0입니다.

## 1. 설치

Codex 로그인, Git, Python 3.10 이상이 필요합니다. Windows에서는 Git for Windows의 Git Bash도 사용합니다. 테스트·빌드 도구는 프로젝트 언어에 맞게 준비합니다.

<a id="수정본을-지금-처음-설치할-때"></a>

### 처음 설치할 때

Windows PowerShell에서 기본 배포를 설치합니다.

```powershell
codex.cmd plugin marketplace add bs-koo/oh-my-gx
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

이미 설치한 경우에는 아래 갱신 절차를 참고하세요. Bash에서는 `codex.cmd` 대신 `codex`를 사용합니다. Linux의 실제 모델 세션과 macOS는 아직 실측하지 않았습니다.

작업할 프로젝트 폴더로 이동해 새 Codex 세션을 엽니다.

```powershell
cd C:\path\to\your-project
codex.cmd
```

Codex 입력창의 `/skills`에서 GX 스킬 18개를 확인하고, `/hooks`에서 GX 훅 정의와 신뢰 상태를 확인합니다. 훅이 표시되지 않거나 신뢰되지 않으면 보호 훅이 실행된다고 볼 수 없습니다.

## 2. 채팅으로 사용

다음은 **Codex 채팅창에 입력하는 요청 예시**입니다. 터미널 명령이 아닙니다.

```text
oh-my-gx:gx-setup 스킬로 이 프로젝트를 준비해줘.
```

setup이 프로젝트의 테스트·빌드 명령과 설정을 확인합니다. 기존 `.claude/config.json`의 사용자 정의 설정을 보존하며, Codex에서도 이 파일을 공통 프로젝트 설정으로 사용합니다.

```text
oh-my-gx:gx-work로 로그인 입력 검증 기능을 구현해줘.
```

기존 문서·컨텍스트·상태를 확인하고 필요한 조사·문서 작업만 수행합니다. 결과와 추천 다음 단계를 제시하며 다음 단계가 문서 보완이면 그 작업까지만 진행합니다. 개발로 넘어가기 직전에 범위·관련 문서/W·종료점을 보여주고 “이 작업을 gx-tdd로 구체화·개발할까요?”라고 묻습니다. 진행·문서 보완·종료의 실제 답변을 기다리며 최초 구현·PR 요청을 그 답변으로 간주하지 않습니다.

진입 답변 뒤 gx-tdd가 PRD·설계·T태스크 구현계획을 확정하고, 계획을 보여준 뒤 현재 세션 중심 또는 구현 서브에이전트 방식을 선택받습니다. 이후 RED-GREEN-REFACTOR로 구현하며 기본 종료점은 검증입니다. 같은 실행·범위의 유효한 진입 승인과 이미 위임한 내부 판단은 반복해서 묻지 않습니다.

일반 개발은 관련 요구사항과 W작업을 연결하고, 구현 후 실제 AC 충족·관련 문서 차이를 확인한 뒤 최종 검증합니다. 필요한 문서가 없으면 이번 요청의 최소 원장·W목록만 보강하며 context에서 구체 구현계획을 만들지는 않습니다. 전체 context 인터뷰나 재스캔을 매번 실행하지 않습니다. 관련 파일의 변경 지문과 요약을 재사용해 같은 원문을 반복 전달하지 않습니다. 읽기 전용·명시 문서 수정 금지는 유지합니다.

정책 조사만 필요하면 `oh-my-gx:gx-lens로 결제 한도 정책을 확인해줘`처럼 요청합니다. 파일·라인 근거와 확인 수준을 보여주고 조회 후 종료합니다. 변경 아이디어가 있으면 영향 분석을 추가하며, 운영 설정값을 확인하지 못한 경우에는 미확인으로 남깁니다.

계획만 필요하거나 PR까지 맡기려면 요청 범위를 명시합니다.

```text
oh-my-gx:gx-work로 알림 기능의 계획만 작성해줘.
oh-my-gx:gx-work로 이 기획서의 기능을 구현하고 PR까지 올려줘.
```

계획만 요청하면 분석과 계획에서 종료하며 별도 저장 요청 없이 파일을 만들거나 브랜치를 전환하지 않습니다. `gx-tdd`도 직접 사용할 수 있으며 이 독립 호출에는 gx-work 진입 질문을 새로 붙이지 않습니다. 핵심 모드는 `--core` 또는 명시적 요청으로 선택합니다.

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

### 질문 대기와 모델 배정

필수 선택·승인 질문은 본문과 선택지를 대화에 표시하고 실제 답변을 기다립니다. 비동기 질문 등록 성공이나 추천 항목 선택 상태는 답변으로 취급하지 않습니다. TDD 진입 답변 전에는 개발용 setup·브랜치/worktree 변경·W착수·빌드·테스트·코드 수정·커밋을 시작하지 않습니다. UI가 접혀 있어도 자연어로 답할 수 있으며, state가 없는 미응답 질문도 재개 시 route보다 먼저 복원합니다. 무인 실행에서 필수 답변을 받을 수 없으면 `BLOCKED`로 종료합니다. 자세한 도구 용도 제한·기록·재개 절차는 [질문 계약](../.claude/skills/gx-work/references/codex-questions.md)을 참고하세요.

표준·에코의 자식 모델은 설치된 정책 helper가 현재 spawn allowlist와 effort를 검사해 결정합니다. 기본 high는 최신 허용 Astra/low, mid는 최신 허용 Sol/medium을 자동 선택합니다. 예를 들어 6.1 Sol과 더 높은 버전의 Sol이 함께 허용되면 요청 effort를 지원하는 가장 높은 숫자 버전을 선택합니다. eco에서도 architect는 high를 유지하고, TDD의 기본 GREEN·REFACTOR는 현재 메인 세션 모델을 유지합니다. `--isolated` 구현은 mid 에이전트, 태스크 리뷰는 mid, fix 4~5는 fresh high 에이전트를 사용합니다. 미지원 계열의 대체 사유와 같은 모델로 티어가 합쳐진 경고를 표시합니다.

프로젝트 `.claude/config.json`에 선택적으로 티어 설정을 추가할 수 있습니다. 설정은 실제 세션에서 지원되는 모델·effort여야 하며 사용자 전역 Codex 설정과 메인 모델을 자동으로 변경하지 않습니다.

```json
{"codex":{"modelTiers":{"high":{"family":"astra","reasoning_effort":"low"},"mid":{"family":"sol","reasoning_effort":"medium"}}}}
```

설정을 비워도 위 자동 최신 정책을 사용합니다. 특정 버전을 유지하려면 `family` 대신 `model`을 지정합니다. 날짜 snapshot·preview·별칭의 최신 순서는 모델 이름만으로 추측하지 않습니다. 호출별 요청 모델·effort와 확인 가능한 실제 관측값은 구분해 기록합니다. 정책 계산이 실제 앱 UI·하네스 모델 호출까지 검증한 것은 아닙니다. [모델 정책과 단계별 배정표](../.claude/skills/gx-work/references/codex-models.md)를 참고하세요.

## 3. Superpowers와 함께 사용

Superpowers와 GX는 별도 플러그인입니다. GX 사용에 Superpowers 설치가 필수는 아닙니다. gx-work는 의도·상태를 파악해 필요한 스킬을 선택하고 결과와 다음 단계를 제안합니다. 고정된 brainstorming → writing-plans 단계를 GX에 추가하지 않으며 도메인/요구사항/W 관리는 context, PRD·설계·T태스크 구현계획은 gx-tdd가 맡습니다. 둘 다 설치했다면 사용할 스킬 이름을 명시하세요.

| 원하는 작업 | 채팅 예시 |
|---|---|
| Superpowers로 계획 작성 | `Superpowers writing-plans로 구현 계획을 작성해줘` |
| GX로 프로젝트 준비 | `oh-my-gx:gx-setup 스킬로 준비해줘` |
| GX로 개발 시작 | `oh-my-gx:gx-work로 이 기능을 구현해줘` |
| GX로 계획만 작성 | `oh-my-gx:gx-work로 이 기능의 계획만 작성해줘` |
| GX로 구현부터 PR까지 | `oh-my-gx:gx-work로 이 기능을 구현하고 PR까지 올려줘` |
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

이전 버전은 [PR #89](https://github.com/bs-koo/oh-my-gx/pull/89)의 수정 브랜치에서 설치된 GX 스킬 17개와 핵심 작업 흐름을 실측했습니다. 이 기록은 현재 버전의 새 설치 발견과 실제 UI 동작을 입증하지 않습니다. RED 역할의 구현 소스 미열람은 독립 trace가 없어 미확인이며, 역할 도구 목록은 권한을 강제하는 경계가 아닙니다. 전체 결과는 [실측 보고서](https://github.com/bs-koo/oh-my-gx/blob/main/docs/reports/2026-09-14-codex-validation.md)를 참고하세요.
