<div align="center">

# oh-my-gx

**요구사항 분석, 구현, 코드 리뷰와 검증을 지원하는 개발 워크플로.**

Claude Code와 Codex에서 도메인 문서와 작업 계획을 정리하고,
테스트 주도 개발(TDD), 코드 리뷰, 최종 검증을 연결합니다. 커밋과 PR은 요청한 범위에 따라 진행합니다.

설치 패키지는 `oh-my-gx`이며, 개발 요청은 `gx-work`로 시작합니다.

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-2ea44f?style=for-the-badge)](https://bs-koo.github.io/oh-my-gx/)
[![PDF 가이드](https://img.shields.io/badge/PDF_%EA%B0%80%EC%9D%B4%EB%93%9C-v1.21.1-ED2224?style=for-the-badge)](docs/oh-my-gx-guide.pdf)
[![Claude Code + Codex](https://img.shields.io/badge/Claude_Code_+_Codex-2563EB?style=for-the-badge)](#하네스-지원)

</div>

---

- [설치와 시작](#설치와-시작)
- [Codex 사용 가이드](docs/codex-guide.md)
- [하네스 지원](#하네스-지원)
- [언어/프레임워크 지원](#언어프레임워크-지원)
- [사용법](#사용법)
- [개발 흐름](#개발-흐름)
- [스킬 상세](#스킬-상세)
- [에이전트 팀](#에이전트-팀)
- [안전장치](#안전장치)
- [Google Chat 알림](#google-chat-알림)
- [FAQ](#faq)

---

## 설치와 시작

### Claude Code

```bash
# Claude Code CLI에서 실행
/plugin marketplace add bs-koo/oh-my-gx
/plugin install oh-my-gx@oh-my-gx

# 최초 1회 환경 설정 (VCS 감지, gh CLI, 인증, 알림 연동)
/oh-my-gx:gx-setup
```

### Codex

```powershell
# Windows PowerShell, Codex CLI 0.154.0 검증 기준
codex.cmd plugin marketplace add bs-koo/oh-my-gx
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

설치 후 작업할 프로젝트 폴더에서 새 Codex 세션을 엽니다. `/skills`에서 GX 스킬 18개를, `/hooks`에서 GX 훅 정의와 신뢰 상태를 확인하세요.

아래는 터미널 명령이 아니라 **Codex 채팅창에 입력하는 요청 예시**입니다.

```text
oh-my-gx:gx-setup 스킬로 이 프로젝트를 준비해줘.
oh-my-gx:gx-work로 이 기능의 요구사항을 정리하고 구현해줘.
oh-my-gx:gx-work로 알림 기능의 계획만 작성해줘.
oh-my-gx:gx-work로 이 기획서의 기능을 구현하고 PR까지 올려줘.
oh-my-gx:gx-cross-review --advisor native로 변경사항을 검토해줘.
oh-my-gx:gx-verify로 테스트와 빌드를 실행해 검증해줘.
```

설치 갱신·커밋·PR·Superpowers 병행 사용은 [Codex 사용 가이드](docs/codex-guide.md)를 참고하세요. Linux Bash에서는 `codex.cmd` 대신 `codex`를 사용합니다.

## 하네스 지원

Claude Code와 Codex에 공통 스킬 원본을 사용하고 Codex용 역할·설정 리소스를 함께 배포합니다. 이전 버전은 2026-09-14에 Windows Codex CLI 0.154.0과 개발용 local export로 소비 프로젝트에서 검증했습니다. 상세 결과와 실패·수정 이력은 [구현·실측 보고](docs/reports/2026-09-14-codex-validation.md)에 있습니다.

| 기능 | Claude Code | Codex |
|------|-------------|-------|
| 스킬 인식·로드 | 지원 | 이전 버전 실측은 17개; 현재 18개 배포 경로는 정적 검사, 새 설치 발견은 미실측 |
| 역할 정의 | `agents/*.md` 자동 로드 | 스킬 번들의 `codex-roles/` 역할 본문 17개와 도구·모델 티어 인덱스를 자식 에이전트에 전달 |
| 설정 템플릿 | 플러그인 `.claude/config.json` | 번들 템플릿과 config 병합 helper 사용; 기존 사용자 설정 보존 실측 |
| 훅 게이트 | 플러그인 적용 | `hooks.json`의 Bash matcher와 Python 어댑터; `/hooks`의 사용자 신뢰 확인 필요 |
| 역할·도구 대응 | Claude Task/Skill | 배포된 `gx-work/references/codex-runtime.md`가 실제 스키마·allowlist 확인 후 매핑 |
| 표준·에코 모델 선택 | opus/sonnet과 Task override | 모델 helper가 역할·프로파일·예외·allowlist를 계산; 기본 최신 허용 Astra/low·Sol/medium 자동 선택 |
| 필수 질문 대기 | 동기 AskUserQuestion | pending helper로 실제 답변·결정 기록 전 phase 진행 보류; async ack는 답변으로 취급하지 않음 |
| TDD·검증·리뷰 | TDD 파이프라인 | 이전 버전에서 RED/GREEN, 코드 지문, native 교차 리뷰 실행 확인 |

### 알려진 제약

Codex의 질문 UI 펼침은 앱이 결정합니다. 필수 질문은 본문과 선택지를 대화에도 표시하고 실제 답변을 기다립니다. 표준·에코는 자식 에이전트 배정에 적용되며, 기본 TDD GREEN·REFACTOR 같은 메인 세션 단계는 현재 모델을 유지합니다. 프로젝트별 모델 설정·대체·실측 기록은 [모델 정책](.claude/skills/gx-work/references/codex-models.md), 질문 표시·대기·재개는 [질문 계약](.claude/skills/gx-work/references/codex-questions.md)을 참고하세요.

이전 버전 실측에서 Codex의 일반 승인 흐름을 거친 로컬 커밋과 보호 훅의 차단을 확인했습니다. 무인 세션에서는 `.git` 쓰기 승인이 필요하면 진행할 수 없습니다. 부모 샌드박스 안의 별도 `codex exec`도 `CODEX_HOME` 쓰기 제한으로 막힐 수 있으므로, 이 환경에서는 `gx-cross-review --advisor native`를 선택하세요. 권한을 자동 우회하지 않습니다.

역할 도구 목록은 프롬프트 지침이며 강제 권한 경계가 아닙니다. RED 자식의 상세 열람 trace, Linux의 실제 모델 세션, macOS 및 릴리스 Git source 설치는 이번 실측 범위에 포함되지 않았습니다. 환경별 재검증 절차는 [Codex smoke 계약](tests/codex-smoke.md), 도구·경로 매핑은 [하네스 어댑터](.claude/rules/harness-codex.md)를 참고하세요.

설치 후 Codex 입력창에서 `oh-my-gx:gx-setup 스킬로 설정해줘`, `oh-my-gx:gx-work로 이 기능을 구현해줘`처럼 사용할 스킬을 명시하면 됩니다. `/skills`에서 설치된 스킬을 선택할 수도 있습니다.

## 언어/프레임워크 지원

워크플로는 특정 언어에 종속되지 않습니다. 빌드·테스트 명령은 `.claude/config.json`의 `projectTypes`를 기준으로 선택합니다. `/gx-setup`이 빌드 파일을 감지해 C/Make·CMake·Ceedling, Python, Go, Rust, .NET, Maven 등의 등록을 제안하며, 다른 환경도 확인 후 등록할 수 있습니다. 테스트 환경이 없는 프로젝트는 [테스트 하네스 가이드](docs/test-harness-guide.md)에 따라 먼저 구성하세요.

## 사용법

개발 작업은 `/gx-work <요청>`으로 시작합니다. 자연어 자동 발견은 하네스와 설치 상태에 따라 달라지므로, 사용할 스킬을 명시할 수도 있습니다.

**의사결정 기록**

실제로 확인한 질문과 선택은 `.dev/{브랜치}/decisions.md`에 기록합니다. 선택한 방안과 검토한 대안을 함께 남겨 결정 근거를 확인할 수 있습니다.

```markdown
## 2026-08-31 11:48 · 결제 취소 승인 기준

**Q.** 결제 취소 요청은 언제 처리하나요?

선택지:
**→** 관리자 승인 후 처리
- 사용자 요청 즉시 처리

**A.** 관리자 승인 후 처리
```

기록을 저장소에 포함하면 팀이 같은 결정 근거를 공유할 수 있습니다. 이미 승인한 결정과 위임한 내부 판단은 반복해서 확인하지 않습니다.

**작업 계획으로 진행하기**

요구사항이 여러 건이면 `.dev/plan.md`의 작업 ID로 범위와 의존 관계를 관리합니다.

`/gx-context`는 요구사항 문서(`--from <파일>`)와 대화에서 도메인별 요구사항 원장(`context/{도메인}/status.md`)을 정리하고 작업 계획을 함께 갱신합니다. 기존 코드만 있는 프로젝트는 코드베이스에서 도메인 구조를 먼저 정리합니다. 요구사항이 추가되면 원장과 계획을 대조해 반영하며, 진행·완료 작업의 상태와 위치는 보존합니다.

```
/gx-context --from docs/요구사항.md
/gx-context 계량기 사용량을 엑셀로 내려받는 기능 추가
```

```
"W01 시작해줘"
"phase W01 개발해줘"
```

작업 ID가 계획에 있으면 도메인·요구사항·브랜치 정보를 확인하고 실행 범위를 먼저 안내합니다.

```
작업 계획에서 W01을 찾았습니다.

  작업       이관 이력 조회
  도메인     재고관리     (context/재고관리/ 를 참조합니다)
  요구사항   FR-4~6
  선행       W00 완료됨
  브랜치     feat/transfer-history (새로 만듭니다)
```

ID 없이 요청하면 기존 계획에서 관련 작업을 찾아 안내합니다. 계획이 없으면 요청한 범위에 필요한 계획부터 정리합니다.

착수 가능한 작업은 다음과 같이 확인합니다.

```
"지금 뭐 할 수 있어?"
```

선행 작업 완료와 요구사항 참조의 유효성을 확인해 착수 가능한 작업을 안내합니다. 원장과 계획에 오류가 있으면 수정할 항목을 먼저 알립니다. 작업을 지정하려면 `--work W01`도 사용할 수 있습니다.

`.dev/plan.md`를 저장소에 포함하면 작업 브랜치의 착수·완료 기록을 PR과 함께 공유할 수 있습니다. 원격 브랜치에서 중복 착수 가능성을 확인하고, 미완료 선행 작업이 있으면 안내합니다.

**개발**

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "대시보드 기능 개발해줘" | gx-work → gx-tdd (검증까지) |
| "TDD로 결제 검증 만들어줘" | gx-work → gx-tdd (테스트 우선 사이클) |
| "긴급 수정해줘" | gx-work → gx-tdd (명시적 핵심 모드 요청이면 core) |
| "구현만 해줘", "가볍게" | gx-work → gx-tdd (기본 검증까지, TDD·검증 게이트 유지) |
| "PRD만 작성해줘" | gx-work (요구사항 정리 후 종료) |
| "이어서 해줘" | gx-work → gx-tdd (기존 종료점·중단 지점 복원) |
| "실패 테스트 먼저 작성해줘" | gx-red · 실패 테스트 작성 |
| "테스트 통과시켜줘" | gx-green · 최소 구현 |
| "중복 제거 정리해줘" | gx-refactor · 코드 정리 |
| "완료 검증해줘" | gx-verify · 변경 검증 |
| "랄프 루프 준비해줘" | gx-ralph · 반복 개발 준비 |

**분석·지식**

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "프로젝트 초기 설정해줘" | gx-setup · 프로젝트 설정 |
| "기획서 보고 context 만들어줘" | gx-context · 도메인·요구사항 관리 |
| "현재 로깅 정책 정리해줘" | gx-lens · 비즈니스 정책 분석 |
| "기술 부채 확인해줘" | gx-tech-debt · 기술 부채 진단 |
| "클라우드 네이티브 트렌드 조사해줘" | gx-research · 도메인·기술 조사 |

**품질·마무리**

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "교차 리뷰 해줘" | gx-cross-review · 구현 교차 검토 |
| ".dev/prd.md AI 흔적 교정해줘" | gx-humanizer · 문장 교정 |
| "변경 영향도를 시각화해줘" | gx-visualize · 구조·흐름 시각화 |
| "커밋해줘" | gx-commit · 커밋 작성 |
| "PR 만들어줘" | gx-pull-request · PR 작성 |

## 개발 흐름

`gx-work`가 요구사항과 기존 산출물을 확인해 도메인 컨텍스트·실행 계획을 연결하고, `gx-tdd`가 테스트 주도 개발을 수행합니다.

1. 기획서가 있으면 `requirements/`에, 준수할 외부 규격은 `references/`에 둡니다.
2. `/gx-work <요청>`으로 관련 context·요구사항·작업계획을 대조합니다. 필요한 FR·AC·작업 연결만 보강하고 기존 문서와 결정을 재사용합니다.
3. 구현 요청은 실패 테스트 확인 → 최소 구현 → 동작을 유지하는 코드 정리(RED-GREEN-REFACTOR)로 진행합니다.
4. 코드 리뷰와 실제 AC 충족을 확인하고 관련 문서의 변경분을 반영한 뒤 최종 검증합니다. 커밋·PR은 요청한 종료점에 포함된 경우 진행합니다.

문서 정합성 확인은 일반 개발의 기본 절차입니다. 전체 context 생성이나 재스캔을 매번 수행하지 않습니다. 문서가 없으면 이번 요청을 추적할 최소 요구사항 원장과 작업계획만 준비하며, 이미 맞는 문서는 다시 쓰지 않습니다. 계획만 요청하거나 문서 수정을 금지한 경우에는 그 범위를 지킵니다.

테스트·빌드는 변경 영향, 태스크 소유권, 프로젝트 설정에 따라 선택합니다. 범위가 불명확하거나 공통 설정·의존성이 바뀌면 전체 검증으로 확장합니다. 같은 실행에서 코드·설정·명령·범위가 일치하는 증거는 리뷰·검증·커밋에서 재사용합니다. Gradle은 테스트와 테스트를 제외한 빌드(`buildOnly`)를 구분하며, 전체 회귀 검증도 명시적으로 요청할 수 있습니다. 자세한 기준은 [사용 가이드](docs/guide.md)에 있습니다.

범위·수용 기준·계획의 승인 지점은 유지합니다. 이미 승인한 결정과 위임한 내부 판단은 반복해서 묻지 않습니다.

### gx-work로 시작하기

`/gx-work <요청>`은 프로젝트 이해, 계획 수립, 구현, 작업 재개를 요청 범위에 맞게 연결합니다.

```text
/gx-work 이 기획서로 결제 취소 기능 만들고 PR까지 올려줘
/gx-work 알림 기능 아이디어와 계획만 정리해줘
/gx-work 이 계획대로 테스트 먼저 구현해줘
/gx-work 아까 하던 작업 이어서 해줘
```

기본 종료점은 검증입니다. 커밋·PR은 명시적으로 요청하면 진행합니다. 계획만 요청하면 분석과 계획에서 종료하며, 브랜치 전환이나 제품 코드 변경 없이 결과를 제시합니다. `gx-context`·`gx-tdd`와 단독 검증·커밋·PR 스킬도 직접 사용할 수 있습니다.

### 외부 규격 참조

프로젝트가 지켜야 할 외부 규격이 있다면 `references/` 디렉토리에 문서를 넣어둡니다:

```
references/
├── 시큐어코딩-가이드.md
├── API-설계-표준.md
└── eGovFrame/
    └── 규칙.md
```

`gx-work`·`gx-tdd`의 설계·구현·리뷰 단계에서 이 문서를 참조해 요구사항과 규격의 준수 여부를 확인합니다.

기존 문서를 그대로 사용할 수 있으며, 다음 형식을 권장합니다:

- 문서 맨 위에 요약이나 목차를 두면 필요한 부분만 골라 봅니다
- 항목마다 번호나 ID(§3.2 등)를 붙이면 설계서에서 정확히 짚어 인용합니다
- 체크리스트 형태로 적어두면 리뷰가 항목별로 준수 여부를 확인합니다

---

## 스킬 상세

<a id="gx-work"></a>

### gx-work · 개발 작업 진행

프로젝트 파악, 작업 계획, 기능 개발과 작업 재개를 연결합니다. 기존 문서와 결정을 활용하고, 구현이 필요하면 `gx-tdd`로 이어서 진행합니다.

진행 중인 작업의 목표와 상태를 기록해 중단한 지점부터 이어갑니다. 기본 완료점은 검증이며 커밋·PR은 요청한 경우에 진행합니다.

<a id="tdd"></a>

### gx-tdd · 테스트 주도 개발

요구사항의 수용 기준(AC)을 테스트로 확인하고, 설계·구현·코드 리뷰·최종 검증을 진행합니다.

```
"TDD로 결제 한도 검증 만들어줘"      ← 전체 TDD 사이클
"테스트 주도로 로그인 개발해줘"
```

- **요구사항 분석**: 수용 기준을 Given-When-Then 형식으로 정리합니다.
- **설계**: 기술 설계와 테스트 가능성을 평가합니다. 테스트 가능성 점수가 7점 미만이면 설계를 보완합니다.
- **구현**: AC 1건 단위로 실패 테스트를 확인하고 최소 구현과 코드 정리를 수행합니다. `red-writer`가 실패 테스트를 작성하고, 현재 세션이 GREEN·REFACTOR를 수행합니다. `--isolated`는 구현도 별도 `implementer`에 위임합니다. 변경 범위와 수정 이력에 따라 태스크별 리뷰를 추가합니다.
- **코드 리뷰**: 선택한 테스트·빌드의 실행 증거를 확인하고, 수용 기준 충족·코드 품질·보안 위험을 검토합니다.
- **완료 검증**: 관련 문서를 실제 결과와 대조한 뒤 `gx-verify`가 실행 증거와 현재 변경의 일치를 확인합니다. 미검증 AC가 남으면 작업을 완료로 표시하지 않습니다. 커밋·PR은 요청한 종료점일 때 수행합니다.

구현 전에는 선택한 기존 테스트의 통과를 확인하고, 구현 중에는 태스크에 필요한 테스트를 실행합니다. RED-GREEN-REFACTOR와 검증 게이트는 개발 경로 전반에 유지합니다.

**핵심 모드(`--core`)**는 정식 설계 평가와 코드 리뷰를 생략하는 경로입니다. 수용 기준 확인, 실패 테스트 작성, RED-GREEN-REFACTOR, 완료 검증, 긴급 보안 감사는 유지합니다. `--core` 또는 명시적 핵심 모드 요청으로 선택합니다.

`gx-red`·`gx-green`·`gx-refactor`는 각 단계를 별도로 실행할 때 사용합니다. TDD 파이프라인은 red-writer와 현재 세션이 같은 단계 계약을 수행하며, 완료 단계에서 `gx-verify`를 수행합니다. `--ralph` 또는 "랄프로 …"를 명시하면 승인된 계획을 무인 반복 실행으로 인계합니다.

역할별 계약을 실제 모델 실행으로 점검하는 명령은 `bash scripts/behavior-tests.sh`입니다. 파일 해시, 테스트 출력, 도구 호출 기록을 확인하며, 절차는 [자동 행동 테스트](tests/golden-scenarios.md)에 있습니다.

<a id="ralph"></a>

### gx-ralph · 반복 개발 준비

승인된 PRD의 수용 기준을 반복 실행 원장으로 변환하고 외부 러너의 실행을 준비합니다. 러너는 `gx-ralph-iterate`로 AC를 1건씩 구현·검증·커밋합니다. 리뷰·인수·PR은 반복 실행 후 별도로 진행합니다.

```
"랄프 루프 준비해줘"          ← PRD의 AC를 루프 원장으로 변환 (ralph)
bash scripts/gx-ralph.sh      ← 플러그인 루트에서 러너 실행 (무인 반복)
"랄프 상태 확인해줘"          ← 진행 상태 조회 (--status)
```

동작 구조:

1. `gx-work`/`gx-tdd`로 PRD(·설계)를 승인까지 확정합니다 — 루프는 승인된 PRD를 명세로 읽는 소비자입니다. `/gx-work --ralph …`·`/gx-tdd --ralph …`(또는 "랄프로 …")로 시작하면 설계 확정 후 구현 진입 시 별도 호출 없이 이 스킬로 이어집니다. 기본 경로에서는 묻지 않습니다
2. `ralph`가 AC를 `ac-status.json` 원장으로 변환하고 최대 반복 수를 확정합니다
3. 러너가 반복마다 새 세션을 시작합니다. 기본 하네스는 Claude Code이며 Codex도 선택할 수 있습니다. AC 1건 구현 → 검증 → 커밋 → 원장 갱신 후 종료하며, 진행 상태는 원장·`progress.txt`·Git 이력에 기록합니다
4. 전 AC 완료 후 사용자가 복귀해 `--phase review` → `--phase complete`로 리뷰·인수·PR을 진행합니다

안전장치:

| 장치 | 동작 |
|------|------|
| 최대 반복 상한 | 기본 10회, 진입 시 확정 (러너 인자로 조정) |
| 반복당 타임아웃 | 기본 30분 |
| NO_DRIFT 감지 | 2회 연속 아무 변화가 없으면 루프 중단 (exit 4) |
| NO_PROGRESS 감지 | 커밋도 AC 완료도 없는 반복이 4회 연속이면 원장 요약(id·attempts)을 출력하고 중단 (exit 7) — 단일 AC 3회 실패의 BLOCKED는 그대로, 미완료 AC가 여럿이면 전부 소진되기 전에 먼저 중단 |
| AC별 시도 상한 | 같은 AC 3회 실패 시 건너뜀, 전부 소진 시 BLOCKED (exit 2) |
| verify backpressure | 매 반복 `verify --non-interactive` 통과 없이는 커밋 불가 (훅 G3가 최종 방어) |
| lock | 러너 동시 실행 방지 |
| 진입 차단 | 보호 브랜치(main/master/develop)·svn 프로젝트·PRD 부재 시 시작 불가 |

리뷰·인수·PR은 루프 밖에서 사람이 진행합니다 — 루프는 구현 구간만 무인화합니다. svn 프로젝트는 지원하지 않습니다(무인 커밋이 훅으로 차단되는 구조).

> **에코 모드는 ralph 무인 루프에 아직 적용되지 않습니다.** 루프의 에이전트는 각자의 기본 모델로 동작하고, 반복 세션의 오케스트레이터 모델만 `GX_RALPH_MODEL` 환경변수로 바꿀 수 있습니다(미지정 시 표준). 종료 후 `gx-work`로 재개하거나 `gx-tdd --phase review`·`--phase complete`로 복귀하면 그 구간부터 프로파일이 다시 적용됩니다.

<a id="context"></a>

### gx-context · 도메인·요구사항 관리

문서·대화·코드베이스에서 도메인 용어, 아키텍처, 요구사항을 정리합니다. `context/{도메인}/`의 요구사항 원장과 `.dev/plan.md`를 함께 갱신하고, 착수 가능한 작업을 확인합니다. 등록된 컨텍스트는 `gx-work`·`gx-tdd`의 공통 근거로 사용합니다.

일반 개발에서는 별도 호출 없이 관련 문서의 정합성을 확인합니다. `/gx-context`를 직접 호출하면 문서 기반 등록·도메인 정리·명시적 동기화를 수행합니다. 코드에서 관측한 현황과 승인된 요구사항을 구분하고 기존 완료·PR 이력을 보존합니다.

```
"requirements 폴더에 있는 기획서 보고 context 만들어줘"   ← 문서 기반 생성
"사용량 분석 도메인 등록해줘"                            ← Q&A 기반 생성
"코드베이스 분석해서 context 자동 생성해줘"               ← 코드 스캔
"사용량 분석 도메인 동기화해줘"                          ← git 히스토리 기반 진행도 갱신
```

<a id="lens"></a>

### gx-lens · 비즈니스 정책 분석

코드에서 비즈니스 정책과 적용 범위를 찾아 기획·제품 담당자가 검토할 수 있는 보고서로 정리합니다. 정책별 파일·라인 근거와 확인·추정·미확인 상태를 표시하고, 현재 구현과 요구사항의 차이를 설명합니다. 운영 설정 등 확인하지 못한 조건은 명시합니다.

조회 요청은 보고 후 종료합니다. `--idea`로 변경안을 주면 관측된 영향 경계에 따라 필요한 분석만 위임합니다. 파일 작성·테스트 실행·코드 변경 없이 분석하며, 근거가 부족하거나 분석이 실패하면 위험을 낮다고 단정하지 않습니다.

```
"현재 사용자 활동 로깅이 어떻게 되어 있는지 정리해줘"
"로그 보관 기간을 180일로 늘리면 어디에 영향이 가?"
```

<a id="tech-debt"></a>

### gx-tech-debt · 기술 부채 진단

코드·아키텍처·의존성·테스트의 기술 부채를 분석합니다. 심각도, 수정 용이성, 영향 범위를 기준으로 개선 우선순위와 로드맵을 제시하며, 코드는 수정하지 않습니다.

```
"기술 부채 확인해줘"                             ← 전체 프로젝트 분석
"/gx-tech-debt 결제 도메인"                      ← 특정 도메인만
"/gx-tech-debt --type deps"                      ← 의존성만 점검
```

- **품질 지표(Health Score)**: 100점 만점 점수와 A~F 등급으로 분석 결과를 요약합니다
- **의존성 스캔**: Java/Kotlin(Gradle), Node(npm audit/outdated), Python(pip-audit)을 자동 점검
- **아키텍처 비교**: `context/{도메인}/architecture.md`에 정의된 구조와 실제 구현을 비교합니다
- 비즈니스 정책은 `gx-lens`, 기술 품질은 `gx-tech-debt`로 분석합니다

<a id="research"></a>

### gx-research · 도메인·기술 조사

웹 검색과 문서 분석으로 도메인·기술·대안을 조사합니다. 꼼꼼 모드는 자료를 병렬로 수집하고, 주요 발견을 독립 출처 2개 이상으로 교차 검증합니다.

```
"클라우드 네이티브 트렌드 조사해줘"              ← 종합 리포트
"결제 시스템 비교 분석해줘 --format comparison"   ← 비교표
"인증 방식 핵심만 정리해줘 --format summary"      ← 핵심 요약
```

조사 결과는 `.research/`에 저장되고 모든 발견에 출처 URL이 붙습니다. `/gx-context --from`으로 context 문서에 반영할 수 있습니다.

<a id="cross-review"></a>

### gx-cross-review · 구현 교차 검토

개발 완료 후 PRD·설계서·Trust Ledger를 근거로 구현 결과를 교차 검증합니다. 수용 기준 충족, 설계 범위 이탈, 새로 발생한 위험을 확인하며, `gx-work`·`gx-tdd` 완료 후 단발성으로 호출합니다.

```
"교차 리뷰 해줘"                                   ← 호출 시 advisor 선택 (codex / native / claude)
"/gx-cross-review --advisor codex"                ← Codex CLI read-only 리뷰
"/gx-cross-review --advisor native"               ← 현재 하네스의 역할 에이전트 리뷰
"/gx-cross-review --advisor claude"               ← Claude Code 호스트에서 기존 역할 리뷰
```

결과는 advisor 종류와 무관하게 `${DEV_DIR}/cross-review.md`에 저장됩니다. 발견된 항목은 자동으로 고치지 않고, 사용자 승인(전부/일부/직접 입력/건너뛰기)을 거쳐 수정에 들어갑니다.

Codex advisor는 설치된 GX의 `scripts/codex-run.py`와 Codex CLI를 사용합니다. 별도 Claude companion 설치는 필요하지 않습니다. Codex 호스트에서 `--advisor claude`를 선택하면 미지원으로 종료합니다.

<a id="humanizer"></a>

### gx-humanizer · 문장 교정

한국어·영어 문서의 AI 글쓰기 패턴을 진단하고 문체를 교정합니다. 한국어 K1~K19, 영어 E1~E19, 공통 C1~C6 패턴을 사용합니다.

| 모드 | 동작 |
|------|------|
| `audit` | 감지 리포트만 (수정 안 함) |
| `rewrite` | 감지 + 수정 + 변경률 상한(30% 경고 / 50% 중단) |
| `strict` | rewrite + **의미 보존 검증**(`humanizer-fidelity`) + **과윤문 검토**(`humanizer-naturalness`) + 단계별 산출물 |

"정밀/꼼꼼히/--strict"를 명시하거나 입력이 8,000자를 넘으면 `strict` 모드를 적용합니다. 블로그·에세이는 문맥에 맞춰 글의 개성과 문장 리듬을 조정합니다.

```
"/gx-humanizer 제안서.md AI 글쓰기 흔적 교정해줘"
"/gx-humanizer 보고서.md 정밀 모드로 교정해줘"        ← strict (의미 보존·과윤문 검증)
```

<a id="visualize"></a>

### gx-visualize · 구조·흐름 시각화

PRD·설계서·변경사항·코드 맵을 근거가 추적되는 JSON 중간 표현(IR)과 한국어 HTML로 변환합니다. 명시적인 요청이 있을 때 실행하며, 요구사항 추적·진행 상태·변경 영향·프로젝트 구조를 시각화합니다.

```
"요구사항 추적 맵을 시각화해줘"     ← trace    (요구사항 → 기능 → 테스트 연결)
"진행 상태를 그림으로 보여줘"       ← progress (Phase·Gate·검증 상태)
"변경 영향도를 시각화해줘"          ← impact   (추가·삭제·변경·이동)
"시각화 포함"                      ← 현재 phase 기본값 (design→service · review→impact · 그 외→progress)
"우리 프로젝트 전체 구조를 그림으로 보여줘"  ← service  (도메인별 아키텍처 맵)
```

기본 출력은 `.dev/{branch-slug}/visual/`이며, `--backend auto`는 `Archify → Mermaid → 정적 HTML` 순으로 실행 가능한 렌더러를 고릅니다. Archify가 없거나 실행에 실패하면 사용자에게 묻지 않고 1회 자동 설치를 시도한 뒤, 그래도 안 되면 Mermaid, 다시 안 되면 정적 HTML로 폴백합니다. 정적 파일명·코드 근거만 사용하며 실제 배포 토폴로지나 운영 인프라를 자동 탐색하지 않습니다.

`service` 뷰(구조)는 매 실행 프로젝트 전체를 다시 스캔해 `.dev/architecture/`에 도메인별 아키텍처 맵을 만듭니다. `아키텍처-맵.html` 하나만 열면 됩니다. gx-work·gx-tdd 완료 단계에서 "아키텍처 맵 갱신"을 고르면 그 사이클에서 새로 생기거나 바뀐 구조를 `[신규]`·`[변경]`으로 표시합니다. 산출물은 커밋하지 않습니다. 뷰별 입력·출력 계약, 도메인 분할 규칙, 실패 시 문제 해결은 [docs/gx-visualize-guide.md](docs/gx-visualize-guide.md)를 참고하세요.

<a id="commit--pull-request"></a>

### gx-commit / gx-pull-request · 커밋·PR 작성

검증된 변경사항의 커밋 메시지와 PR 제목·본문을 작성합니다. 사용자가 요청한 종료점에 따라 진행하며, 보호 브랜치와 검증 게이트를 확인합니다.

```
"커밋해줘"      ← 브랜치명에서 타입 파싱, 변경사항 분석, 한국어 커밋 메시지 생성
"PR 만들어줘"   ← 커밋 히스토리 분석, PR 제목/본문 자동 생성
```

> **SVN 프로젝트**: commit/pull-request는 Git 전용입니다. SVN에서는 TDD 리뷰·verify 게이트까지 마친 뒤 터미널에서 `svn commit`을 직접 실행하세요.

---

## 에이전트 팀

역할 정의 17개를 배포하며, 스킬은 작업에 필요한 역할을 호출합니다. 아래는 현재 워크플로의 주요 역할입니다.

| 분류 | 에이전트 | 역할 |
|------|---------|------|
| **제품** | product-owner | 요구사항 구체화, PRD 작성, 인수 검증 |
| **설계** | architect | 기술 설계 (변경 범위, API, 구현 순서) |
| | test-architect | 테스트 가능성 평가와 점수 산정 |
| **구현** | red-writer | 실패 테스트 작성 |
| | implementer | GREEN·REFACTOR 구현 |
| | green-coder | 테스트를 통과하는 최소 구현 (단독 스킬) |
| | refactor-coder | 테스트 통과를 유지하는 코드 정리 (단독 스킬) |
| **리뷰** | design-critic | 설계 가정 검토, 과잉 설계 식별 |
| | reviewer | 수용 기준 충족과 코드 품질 리뷰 |
| | security-auditor | 정책·보안 위험 검증 |
| **윤문 검증** | humanizer-fidelity | 의미 보존 감사 (strict) |
| | humanizer-naturalness | 과도한 윤문과 AI 문체 잔존 검토 (strict) |
| **분석** | researcher | 코드베이스 조사와 기술 비교 |
| **복구** | hacker | 기술적 장애 분석과 대안 제시 |
| | simplifier | 복잡도 제거, 범위 축소 |

---

## 안전장치

- 기본 종료점은 검증이며, 커밋·PR은 요청 범위에 따라 수행합니다. PR 병합은 사용자의 명시적 요청이 필요한 운영 원칙입니다. `git push --force`는 플러그인의 deny 설정으로 차단합니다.
- 커밋 스킬과 활성화된 보호 훅은 **main/master/develop** 브랜치의 직접 커밋을 차단합니다.
- `gx-verify`는 실제 테스트·빌드 결과와 코드 지문을 확인합니다. 현재 코드와 일치하는 실행 증거를 기준으로 커밋 전 검증 게이트를 확인합니다.
- SVN 프로젝트는 검증까지 지원하며, `svn commit`은 사용자가 직접 실행합니다.
- 커밋 전에 민감 파일(`.env*`, `*.key`, `*.pem`, `credentials*`, `*secret*`)이 잡히면 경고합니다.
- 빌드 아티팩트(`build/`, `node_modules/` 등)가 tracked 상태면 `.gitignore` 보강을 제안합니다.
- PR 생성·수정 및 main 브랜치 push마다 정합성 린트(CI)가 스킬 문서·에이전트·설정 간 불변식을 자동 검사합니다.

---

## Google Chat 알림

`/oh-my-gx:gx-setup`에서 Google Chat 웹훅을 연동해두면 PR이 생성될 때 Chat Space로 알림이 자동 전송됩니다. 한 명이 설정해 커밋하면 팀 전체가 알림을 받습니다.

```
[oh-my-gx] 새로운 PR을 확인해주세요: https://github.com/bs-koo/oh-my-gx/pull/1
```

---

## FAQ

<details>
<summary><b>어떤 명령어로 시작하나요?</b></summary>

`/gx-work <요청>`을 사용하세요. 무엇을 원하는지와 어디까지 진행할지만 말하면 됩니다. 개발 실행은 TDD로 통일했으며 `gx-dev`는 제거되었습니다. 기존 gx-dev 작업은 자동 변환하지 않고 산출물을 보존한 뒤 TDD 전환 범위를 확인합니다.
</details>

<details>
<summary><b>context 없이도 gx-work·gx-tdd를 실행할 수 있나요?</b></summary>

네. 사전 등록 없이 시작할 수 있습니다. 일반 개발은 이번 요청에 필요한 최소 요구사항 원장·작업계획을 연결한 뒤 TDD로 진행합니다. 전체 도메인 문서나 인터뷰는 강제하지 않으며 기존 문서는 관련 범위만 대조합니다. 문서 수정을 명시적으로 금지하면 미반영 차이를 알리고 그 제한을 지킵니다.
</details>

<details>
<summary><b>gx-work·gx-tdd를 실행하면 바로 코드를 짜나요?</b></summary>

아닙니다. 기존 문서·계획·승인된 결정을 먼저 읽고, 빠진 중요 결정만 확인합니다. 필요한 PRD·설계와 승인 게이트를 거쳐 TDD로 구현하며, 이미 승인한 내용을 단계마다 다시 묻지 않습니다. 이해·계획만 요청하면 구현하지 않고 종료합니다.
</details>

<details>
<summary><b>gx-work·gx-tdd 도중에 멈추면 처음부터 다시 해야 하나요?</b></summary>

아닙니다. "이어서 해줘"라고 말하면 `.dev/{branch-slug}/state.md`에 저장된 진행 상태를 읽어 멈춘 단계부터 다시 시작합니다. 기존 실행의 목표·종료점·중단 위치를 복원합니다. 제거된 비TDD 진행 상태는 자동 재개하지 않고 산출물을 보존한 뒤 TDD 전환 범위를 확인합니다. 단, **v1.18.0 이전 버전에서 생성된 세션**(state.md의 `mode`가 `all`/`core`가 아닌 경우)은 호환성이 제거되어 재개할 수 없으며, 새로 시작해야 합니다.
</details>

<details>
<summary><b>humanizer의 strict 모드는 일반 모드와 뭐가 다른가요?</b></summary>

`audit`/`rewrite`는 단일 스킬이 가볍게 처리합니다. `strict`는 윤문을 마친 뒤 `humanizer-fidelity`가 의미 훼손(수치·고유명사·인용 변형)을, `humanizer-naturalness`가 과윤문·AI티 잔존을 교차 검증하고, 필요하면 다시 윤문합니다. 8,000자를 넘으면 자동으로 strict로 전환됩니다.
</details>

<details>
<summary><b>PR이 자동으로 머지되나요?</b></summary>

아닙니다. 자동화는 PR 생성까지입니다. 머지는 사용자가 명시적으로 요청할 때만 수행합니다 (설정 차단이 아니라 운영 원칙입니다).
</details>

<details>
<summary><b>SVN 프로젝트에서도 사용할 수 있나요?</b></summary>

네. `/gx-setup`을 실행하면 VCS를 자동으로 감지합니다. SVN 프로젝트에서도 `gx-work`·`gx-tdd` 파이프라인의 PRD·설계·구현·리뷰가 똑같이 동작하고, 커밋만 `svn commit`으로 직접 하면 됩니다. `context`·`lens`·`research`·`humanizer` 같은 다른 스킬도 모두 그대로 쓸 수 있습니다.
</details>

<details>
<summary><b>Codex에서도 쓸 수 있나요?</b></summary>

이전 버전은 Windows Codex CLI 0.154.0에서 설치된 스킬 17개를 확인하고 `setup → TDD → native 교차 리뷰 → verify`를 실제 실행했습니다. 설치·업데이트 절차와 채팅 예시는 [Codex 사용 가이드](docs/codex-guide.md)에 있습니다.

현재 배포에는 스킬 18개와 Codex용 역할 정의 17개, 도구·모델 티어 인덱스, 설정 템플릿을 포함합니다. 각 스킬의 하네스 적응 안내에 따라 현재 세션의 역할 위임·질문·스킬 호출 도구를 사용합니다. 현재 버전의 새 설치 발견과 실제 UI 동작은 이전 버전 실측으로 입증하지 않습니다.

`/hooks`에서 훅 정의와 신뢰 상태를 확인하세요. 중첩 외부 CLI와 무인 커밋은 Codex 권한 정책에 따라 제한될 수 있습니다. 구체적인 결과와 제약은 [실측 보고서](docs/reports/2026-09-14-codex-validation.md)와 [하네스 지원](#하네스-지원)을 참고하세요.
</details>

<details>
<summary><b>플러그인 업데이트는?</b></summary>

`/plugin marketplace update oh-my-gx`
</details>

<details>
<summary><b>버전별 변경사항은 어디서 보나요?</b></summary>

[CHANGELOG.md](CHANGELOG.md)에 릴리스별로 정리되어 있습니다. v1.18.0부터 `--hotfix`는 제거되었으며, 핵심 모드는 `--core` 또는 명시적 요청으로 선택합니다. 긴급 수정 요청도 기본적으로 TDD·검증 경로를 사용합니다.
</details>
