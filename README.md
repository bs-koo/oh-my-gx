<div align="center">

# oh-my-gx

**GX 사업본부 개발자를 위한 개발 자동화 플러그인 — PRD·설계·구현·리뷰·PR까지 에이전트 팀이 처리합니다**

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
# PR #89 수정본을 지금 처음 설치할 때
codex.cmd plugin marketplace add bs-koo/oh-my-gx --ref feat/codex-native-validation
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

PR이 main에 반영된 뒤 기본 브랜치를 처음 설치할 때는 `--ref feat/codex-native-validation`을 생략합니다. 설치 후 작업할 프로젝트 폴더에서 새 Codex 세션을 열고 `/skills`로 GX 스킬 17개를, `/hooks`로 GX 훅 정의와 신뢰 상태를 확인합니다.

아래는 터미널 명령이 아니라 **Codex 채팅창에 단계별로 입력할 요청**입니다.

```text
oh-my-gx:gx-setup 스킬로 이 프로젝트를 준비해줘.
oh-my-gx:gx-tdd --core로 이 기능을 테스트 먼저 구현해줘.
oh-my-gx:gx-cross-review --advisor native로 변경사항을 검토해줘.
oh-my-gx:gx-verify로 테스트와 빌드를 실행해 검증해줘.
```

설치 갱신·커밋·PR·Superpowers 병행 사용은 [Codex 사용 가이드](docs/codex-guide.md)를 참고하세요. Linux Bash에서는 `codex.cmd` 대신 `codex`를 사용합니다.

## 하네스 지원

Claude Code의 기존 스킬 원본을 유지하고 Codex용 역할·설정 리소스를 함께 배포합니다. 2026-09-14에 Windows의 Codex CLI 0.154.0과 개발용 local export로 실제 소비 프로젝트를 검증했습니다. 상세 결과와 실패·수정 이력은 [구현·실측 보고](docs/reports/2026-09-14-codex-validation.md)에 있습니다.

| 기능 | Claude Code | Codex |
|------|-------------|-------|
| 스킬 인식·로드 | 지원 | 실제 설치에서 GX 스킬 17개 발견 확인 |
| 역할 정의 | `agents/*.md` 자동 로드 | 스킬 번들의 `codex-roles/` 17개 본문·index tools/tier를 자식 message에 주입 |
| 설정 템플릿 | 플러그인 `.claude/config.json` | 번들 템플릿과 config 병합 helper 사용; 기존 사용자 설정 보존 실측 |
| 훅 게이트 | 플러그인 적용 | `hooks.json`의 Bash matcher와 Python 어댑터; `/hooks`의 사용자 신뢰 확인 필요 |
| 역할·도구 대응 | Claude Task/Skill | 배포된 `gx-dev/references/codex-runtime.md`가 실제 스키마·allowlist 확인 후 매핑 |
| TDD·검증·리뷰 | 기존 파이프라인 | 실제 RED/GREEN, 코드 지문, native 교차 리뷰 실행 확인 |

### 알려진 제약

Codex의 일반 승인 흐름을 거친 로컬 커밋과 보호 훅의 차단을 확인했습니다. 무인 세션에서는 `.git` 쓰기 승인이 필요하면 진행할 수 없습니다. 부모 샌드박스 안의 별도 `codex exec`도 `CODEX_HOME` 쓰기 제한으로 막힐 수 있으므로, 이 환경에서는 `gx-cross-review --advisor native`를 선택하세요. 권한을 자동 우회하지 않습니다.

역할 도구 목록은 프롬프트 지침이며 강제 권한 경계가 아닙니다. RED 자식의 상세 열람 trace, Linux의 실제 모델 세션, macOS 및 릴리스 Git source 설치는 이번 실측 범위에 포함되지 않았습니다. 환경별 재검증 절차는 [Codex smoke 계약](tests/codex-smoke.md), 도구·경로 매핑은 [하네스 어댑터](.claude/rules/harness-codex.md)를 참고하세요.

설치 후 Codex 입력창에서 `oh-my-gx:gx-setup 스킬로 설정해줘`, `oh-my-gx:gx-tdd --core로 이 기능을 구현해줘`처럼 사용할 스킬을 명시하면 됩니다. `/skills`에서 설치된 스킬을 선택할 수도 있습니다.

## 언어/프레임워크 지원

파이프라인은 언어 중립적이다. 빌드/테스트 명령은 `.claude/config.json`의 `projectTypes`(SSOT)에서 읽으며, `/gx-setup`의 "프로젝트 타입 등록"이 빌드 파일을 감지해 등록을 제안한다 (C/Make·CMake·Ceedling, Python, Go, Rust, .NET, Maven 등 힌트 내장 — 목록 밖 스택도 확인 후 등록 가능). 테스트 프레임워크가 없는 프로젝트는 `docs/test-harness-guide.md`를 참고해 하네스를 먼저 구축한다.

## 사용법

명령어를 외울 필요는 없습니다. 자연어로 말하면 의도에 맞는 스킬이 알아서 발동됩니다.

**의사결정 기록**

파이프라인이 확인 게이트에서 물어본 질문과 선택은 `.dev/{브랜치}/decisions.md`에 자동으로 쌓입니다. 고른 선택지뿐 아니라 **버린 선택지와 그 설명까지** 남으므로, 나중에 "왜 이렇게 정했나"를 되짚을 수 있습니다.

```markdown
## 2026-08-31 11:48 · 구현 방식

**Q.** 구현 구간을 3명이 어떻게 나눌까요?

선택지:
- 순수 릴레이 — 드라이버 1명이 돌리고 교대. 충돌 0...
**→** 구현만 3분할 — 설계까지 릴레이 후 AC를 나눠...

**A.** 구현만 3분할
```

별도 설정이 필요 없습니다. 플러그인을 설치하면 훅이 함께 배포됩니다. `.dev/`는 저장소에 공유되므로 팀원도 같은 기록을 봅니다.

**작업 계획으로 진행하기**

요구사항이 여러 건이면 `.dev/plan.md`에 작업 목록을 만들어두고 ID로 부릅니다. 도메인과 요구사항 범위를 매번 설명할 필요가 없습니다.

```
"W01 시작해줘"
"phase W01 개발해줘"
```

계획에 그 ID의 행이 있으면 도메인·요구사항·브랜치명을 알아서 확정하고, 무엇으로 진행하는지 먼저 보여줍니다.

```
작업 계획에서 W01을 찾았습니다.

  작업       이관 이력 조회
  도메인     재고관리     (context/재고관리/ 를 참조합니다)
  요구사항   FR-4~6
  선행       W00 완료됨
  브랜치     feat/transfer-history (새로 만듭니다)
```

ID를 잊었어도 괜찮습니다. 그냥 요청하면 계획에 비슷한 작업이 있는지 대조해 알려줍니다. 계획이 없는 프로젝트에서는 아무 일도 일어나지 않습니다.

무엇을 할 수 있는지 모를 때는 이렇게 물으면 됩니다.

```
"지금 뭐 할 수 있어?"
```

의존이 풀린 작업을 계산해서 알려줍니다. 명시적으로 지정하려면 `--work W01` 플래그도 쓸 수 있습니다.

`.dev/plan.md`는 저장소에 공유됩니다. 착수와 완료는 작업 브랜치에 기록되어 PR과 함께 머지되므로, 팀원이 `git pull` 후 누가 무엇을 끝냈는지 봅니다. 아직 머지되지 않은 착수는 원격 브랜치의 존재로 감지해 중복을 경고하고, 선행 작업이 끝나지 않았으면 알려줍니다.

**개발**

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "대시보드 기능 개발해줘" | dev (전체 사이클) |
| "TDD로 결제 검증 만들어줘" | tdd (테스트 우선 사이클) |
| "긴급 수정해줘" | dev / tdd (core — 경량 경로, AC를 재현 조건으로) |
| "구현만 해줘", "가볍게" | dev (core: AC 확인 → 구현 → Gate) / tdd (core: AC 확인 → RGR → verify) |
| "PRD만 작성해줘" | dev / tdd (단일 단계) |
| "이어서 해줘" | dev / tdd (중단 지점부터 재개) |
| "실패 테스트 먼저 작성해줘" | red (단독) |
| "테스트 통과시켜줘" | green (단독) |
| "중복 제거 정리해줘" | refactor (단독) |
| "완료 검증해줘" | verify |
| "랄프 루프 준비해줘" | ralph (무인 루프 준비) |

**분석·지식**

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "기획서 보고 context 만들어줘" | context |
| "현재 로깅 정책 정리해줘" | lens |
| "기술 부채 확인해줘" | tech-debt |
| "클라우드 네이티브 트렌드 조사해줘" | research |

**품질·마무리**

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "교차 리뷰 해줘" | cross-review |
| ".dev/prd.md AI 흔적 교정해줘" | humanizer |
| "커밋해줘" | commit |
| "PR 만들어줘" | pull-request |

## 개발 흐름

개발은 `context` → `dev`(또는 `tdd`)의 두 단계로 진행합니다. `dev`/`tdd`만 단독으로 써도 됩니다.

1. `requirements/` 폴더에 기획서(PDF, 이미지, 텍스트)를 넣습니다
2. 준수해야 할 외부 규격 문서가 있다면 `references/` 폴더에 넣어둡니다. 설계·구현·리뷰 단계에서 자동으로 참조합니다
3. "context 만들어줘"로 도메인 지식을 등록합니다
4. "개발해줘"(`dev`) 또는 "TDD로 개발해줘"(`tdd`)라고 하면 PRD → 설계 → 구현 → 리뷰 → PR까지 한 번에 이어집니다

단계와 단계 사이에는 사용자 승인이 필요합니다. 승인 없이 다음으로 넘어가는 일은 없습니다.

### dev vs tdd — 어떤 걸 쓰나

둘은 PRD → 설계 → 구현 → 리뷰 → PR 골격을 공유하지만, **구현을 끌고 가는 방식이 정반대**입니다. `dev`는 설계를 확정한 뒤 구현하고 사후에 검증하고, `tdd`는 실패 테스트를 먼저 쓰고 그걸 통과시키며 구현합니다.

| | dev (설계 우선) | tdd (테스트 우선) |
|---|---|---|
| 접근 | 설계 확정 → 구현 → 사후 검증 | 실패 테스트 먼저 → 통과시키며 구현 |
| 요구사항 | 자연어 수용 기준 | **Given-When-Then 강제** (자동 테스트로 변환 가능) |
| 설계 | 비판 검토 | **+ testability 점수**(7 미만이면 재설계) |
| 구현 | coder가 설계대로 한 번에 | **RED → GREEN → REFACTOR 격리 사이클** |
| 리뷰 | qa + security 병렬 | **spec(AC) → quality(품질) 순차** |
| 완료 | qa 통과 → commit | **verify 게이트**(실제 테스트 실행 증거) → commit |
| 테스트 | 선택 — 있으면 좋음 | **필수 — 없으면 진행 불가** |

> **한 줄 기준**: "이 작업의 정답을 자동 테스트로 표현할 수 있고, 그래야 하는가?" → 예면 `tdd`, 아니오·애매하면 `dev`.

- **`dev`가 맞는 작업** — UI·화면 조정, 설정·문서·인프라 변경, 외부 시스템 연동, 빠른 프로토타입, 테스트 인프라가 없는 레거시처럼 *자동 테스트로 명세를 떨어뜨리기 어려운* 작업
- **`tdd`가 맞는 작업** — 결제·인증·정산 같은 핵심 비즈니스 로직, 계산·검증처럼 입출력이 명확한 로직, 회귀가 치명적인 모듈, 리팩토링(안전망 필요), 버그 수정(재현 테스트 먼저)처럼 *정답을 자동 테스트로 표현할 수 있고 그래야 하는* 작업

"TDD로", "테스트 먼저" 같은 명시적 키워드가 있으면 `tdd`로, 없으면 `dev`로 갈립니다. 애매하면 어느 방식으로 갈지 물어봅니다.

### 외부 규격 참조

프로젝트가 지켜야 할 외부 규격이 있다면 `references/` 디렉토리에 문서를 넣어둡니다:

```
references/
├── 시큐어코딩-가이드.md
├── API-설계-표준.md
└── eGovFrame/
    └── 규칙.md
```

`dev`·`tdd`를 실행하면 설계·구현·리뷰 에이전트가 이 문서들을 자동으로 참조합니다. 없어도 동작하지만, 등록해두면 규격 준수 여부를 알아서 검증해줍니다.

기존 문서를 그대로 넣어도 됩니다. 다만 에이전트가 더 잘 찾아 쓰게 하려면:
- 문서 맨 위에 요약이나 목차를 두면 필요한 부분만 골라 봅니다
- 항목마다 번호나 ID(§3.2 등)를 붙이면 설계서에서 정확히 짚어 인용합니다
- 체크리스트 형태로 적어두면 리뷰가 항목별로 준수 여부를 확인합니다

---

## 스킬 상세

### dev

자연어 요청 한 줄이면 PRD 작성부터 PR 생성까지 전체 사이클이 돌아갑니다.

```
"사용량 분석 대시보드 기능 개발해줘"    ← 전체 사이클
"알림 임계값 변경, 구현만 해줘"        ← 핵심 모드 (AC 확인 → 구현 → Gate → 기록)
"집계 스케줄러 오류 긴급 수정해줘"     ← 핵심 모드 (AC를 재현 조건으로 작성해 확인)
"PRD만 작성해줘"                     ← 특정 단계만
"이어서 해줘"                        ← 중단 지점부터 재개
```

내부에서는 에이전트 팀이 요구사항 → 설계 → 구현 → 리뷰 → 완료로 단계를 나눠 처리합니다. 어떤 작업에 `dev`가 맞는지는 위 [dev vs tdd](#dev-vs-tdd--어떤-걸-쓰나)를 참고하세요.

설계가 확정되면 기본 경로는 바로 구현으로 넘어갑니다. 무인 루프로 돌리고 싶을 때만 `--ralph` 플래그나 "랄프로 …" 발화로 명시하세요 — 그러면 기준 테스트 GREEN을 확인한 뒤 [ralph](#ralph)로 이어집니다. AC가 많고 자리를 비울 때 유용합니다. 핵심 모드·svn에서는 지원하지 않습니다.

소형 변경은 **핵심 모드(core)**가 빠릅니다: 오케스트레이터가 AC(수용 기준) 3~5줄을 직접 작성해 확인받고, 구현 후 빌드·테스트 게이트를 통과해야 커밋/PR로 진행합니다. 산출물(`ac.md`·`summary.md`)이 남으므로 "그냥 프롬프팅"과 달리 나중에 왜 바꿨는지 추적할 수 있습니다.

토큰이 부담되면 **에코 모드(eco)**를 켜세요: 절차·게이트는 그대로 두고 에이전트 디스패치만 sonnet 중심으로 하향합니다 — 단 설계(architect)는 opus를 유지합니다. 설계 오류만은 게이트가 잡아주지 못하기 때문입니다 (Pro 요금제 권장). `/gx-setup`에서 1회 설정하거나 `--eco` 플래그·"에코로 개발해줘" 자연어로 켤 수 있고, `--standard`로 이번 실행만 표준으로 되돌립니다. 모드 확인 질문이 뜨는 경우에는 표준/에코 선택이 **같은 창에 함께** 나와 한 번의 submit으로 두 축을 결정합니다. dev·tdd 모두 적용됩니다.

### tdd

`dev`와 같은 6단계 골격을 쓰지만 **구현을 테스트가 끌고 가는** 별도 파이프라인입니다.

```
"TDD로 결제 한도 검증 만들어줘"      ← 전체 TDD 사이클
"테스트 주도로 로그인 개발해줘"
```

- **requirements**: 수용 기준(AC)을 Given-When-Then 형식으로 강제 (자동 테스트로 변환 가능)
- **design**: `test-architect`가 testability 점수(1-10)를 매기고, 7 미만이면 재설계
- **implement**: `red-writer`(실패 테스트, 격리 디스패치) → 세션이 직접 통과 최소 코드 + 정리(`--isolated`면 `implementer` 디스패치). 태스크는 AC 1건 단위이며 8개를 넘으면 분할을 먼저 묻는다. 프로덕션 파일을 2개 이상 바꿨거나 fix 라운드를 거친 태스크는 완료 전에 `reviewer`가 태스크 범위로 한 번 더 본다(sonnet). 나머지는 기계 검증(해시·focused 직접 실행)으로 닫는다. 기준선 게이트(기존 테스트 GREEN 확인) 통과 후 바로 사이클에 들어갑니다. `--ralph`나 "랄프로 …"로 명시한 실행만 그 시점에 무인 루프로 전환되며, 루프 안에서도 RGR 사이클이 AC 1건 단위로 유지됩니다
- **review**: `reviewer`(AC 충족 → 코드 품질 통합 1석, spec verdict 선행) + `security-auditor` 병렬
- **complete**: `verify` 게이트(신선한 테스트 실행 증거)를 통과해야만 commit/PR

tdd에도 **핵심 모드(core)**가 있습니다: 설계(testability 평가)와 정식 리뷰만 생략하는 경량 경로로, AC(Given-When-Then)를 오케스트레이터가 직접 작성해 확인받고 **RGR 사이클·verify 게이트·긴급 보안 감사는 그대로 유지**합니다. dev 핵심 모드와 달리 테스트 작성이 여전히 강제됩니다 — "TDD로 긴급 수정해줘", "TDD로 구현만 해줘"가 이 경로입니다.

보조 스킬 `red` / `green` / `refactor`는 단계를 **단독으로** 실행하고 싶을 때 쓰는 스킬입니다 — 파이프라인은 이 스킬들을 거치지 않고 해당 에이전트를 직접 지휘하며, `verify`만 완료 단계에서 스킬로 호출됩니다.

프롬프트로만 금지되는 계약(red-writer의 프로덕션 코드 미열람, implementer의 테스트 불변, reviewer의 판정 순서)은 `bash scripts/behavior-tests.sh`가 실제 모델 실행으로 검증합니다 — phase 파일의 디스패치 프롬프트를 그대로 추출해 픽스처 프로젝트에서 돌리고 파일 해시·러너 출력·도구 호출 기록으로 판정합니다 (`tests/golden-scenarios.md` "자동 행동 테스트").

### ralph

루프 엔지니어링(Ralph 루프) 스킬입니다. PRD 확정 후, **외부 러너**가 수용 기준(AC)을 1건씩 자율 반복으로 구현합니다 — 사람은 PRD 승인까지만 개입하고, 구현 구간은 무인으로 돌아갑니다.

```
"랄프 루프 준비해줘"          ← PRD의 AC를 루프 원장으로 변환 (ralph)
bash scripts/gx-ralph.sh      ← 터미널에서 러너 실행 (무인 반복)
"랄프 상태 확인해줘"          ← 진행 상태 조회 (--status)
```

동작 구조:

1. `dev`/`tdd`로 PRD(·설계)를 승인까지 확정합니다 — 루프는 승인된 PRD를 명세로 읽는 소비자입니다. `/gx-dev --ralph …`·`/gx-tdd --ralph …`(또는 "랄프로 …")로 시작하면 설계 확정 후 구현 진입 시 별도 호출 없이 이 스킬로 이어집니다. 기본 경로에서는 묻지 않습니다
2. `ralph`가 AC를 `ac-status.json` 원장으로 변환하고 최대 반복 수를 확정합니다
3. 러너가 반복마다 **새 claude 세션**을 기동합니다 — AC 1건 구현 → verify → 커밋 → 원장 갱신 → 세션 종료. 진행 상태는 대화가 아닌 파일(원장·progress.txt)과 git 히스토리에 영속됩니다
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

> **에코 모드는 ralph 무인 루프에 아직 적용되지 않습니다.** 루프의 에이전트는 각자의 기본 모델로 동작하고, 반복 세션의 오케스트레이터 모델만 `GX_RALPH_MODEL` 환경변수로 바꿀 수 있습니다(미지정 시 표준). 종료 후 `dev`/`tdd`로 복귀(`--phase review`/`complete`)하면 그 구간부터 프로파일이 다시 적용됩니다.

### context

기획서, 요구사항 문서, 코드베이스를 분석해 도메인 지식을 `context/{도메인}/`에 등록합니다. 한번 등록한 context는 `dev`/`tdd`를 실행할 때 자동으로 참조됩니다.

```
"requirements 폴더에 있는 기획서 보고 context 만들어줘"   ← 문서 기반 생성
"사용량 분석 도메인 등록해줘"                            ← Q&A 기반 생성
"코드베이스 분석해서 context 자동 생성해줘"               ← 코드 스캔
"사용량 분석 도메인 동기화해줘"                          ← git 히스토리 기반 진행도 갱신
```

### lens

코드에 묻혀 있는 비즈니스 정책을 찾아 PO/PD가 읽을 수 있는 보고서로 뽑아냅니다. 코드는 건드리지 않습니다. 변경 아이디어를 이어서 말하면 복잡도와 리스크 분석까지 해줍니다.

```
"현재 사용자 활동 로깅이 어떻게 되어 있는지 정리해줘"
"로그 보관 기간을 180일로 늘리면 어디에 영향이 가?"
```

### tech-debt

코드베이스의 기술 부채를 네 가지 유형(코드 / 아키텍처 / 의존성 / 테스트)으로 나눠 분석하고, 심각도 × 수정 용이성 × 영향 범위를 따져 우선순위 로드맵을 내놓습니다. **읽기 전용**이라 코드는 수정하지 않습니다.

```
"기술 부채 확인해줘"                             ← 전체 프로젝트 분석
"/gx-tech-debt 결제 도메인"                      ← 특정 도메인만
"/gx-tech-debt --type deps"                      ← 의존성만 점검
```

- **Health Score**: 100점 만점에 A~F 등급으로 건강 상태를 보여줍니다
- **의존성 스캔**: Java/Kotlin(Gradle), Node(npm audit/outdated), Python(pip-audit)을 자동 점검
- **아키텍처 비교**: `context/{도메인}/architecture.md`가 있으면 의도한 구조와 실제 구조를 맞대봅니다
- `lens`와는 역할이 갈립니다 — `lens`는 비즈니스 정책을, `tech-debt`는 기술 품질을 봅니다

### research

웹 검색과 문서 분석을 함께 돌려 도메인 리서치를 수행합니다. 꼼꼼 모드에서는 병렬 수집과 출처 교차 검증(주요 발견은 독립 출처 2개 이상)까지 수행합니다.

```
"클라우드 네이티브 트렌드 조사해줘"              ← 종합 리포트
"결제 시스템 비교 분석해줘 --format comparison"   ← 비교표
"인증 방식 핵심만 정리해줘 --format summary"      ← 핵심 요약
```

조사 결과는 `.research/`에 저장되고 모든 발견에 출처 URL이 붙습니다. `/gx-context --from`으로 context 문서에 반영할 수 있습니다.

### cross-review

`dev`·`tdd`를 끝낸 뒤 한 번만 부르는 전용 스킬입니다. PRD/설계서/Trust Ledger 같은 산출물을 컨텍스트로 넣어 "약속한 대로 만들었는가"를 교차 검증합니다. 일반 코드 품질 리뷰가 아니라 **AC 충족, 설계 범위 이탈, 신규 위험만** 짚어 보고합니다.

```
"교차 리뷰 해줘"                                   ← 호출 시 advisor 선택 (codex / native / claude)
"/gx-cross-review --advisor codex"                ← Codex CLI read-only 리뷰
"/gx-cross-review --advisor native"               ← 현재 하네스의 역할 에이전트 리뷰
"/gx-cross-review --advisor claude"               ← Claude Code 호스트에서 기존 역할 리뷰
```

결과는 advisor 종류와 무관하게 `${DEV_DIR}/cross-review.md`에 저장됩니다. 발견된 항목은 자동으로 고치지 않고, 사용자 승인(전부/일부/직접 입력/건너뛰기)을 거쳐 수정에 들어갑니다.

Codex advisor는 설치된 GX의 `scripts/codex-run.py`와 Codex CLI를 사용합니다. 별도 Claude companion 설치는 필요하지 않습니다. Codex 호스트에서 `--advisor claude`를 선택하면 미지원으로 종료합니다.

### humanizer

AI 글쓰기 패턴(40+가지, 한국어 K1~K19 / 영어 E1~E19 / 공통 C1~C6)을 감지하고 교정합니다.

| 모드 | 동작 |
|------|------|
| `audit` | 감지 리포트만 (수정 안 함) |
| `rewrite` | 감지 + 수정 + 변경률 상한(30% 경고 / 50% 중단) |
| `strict` | rewrite + **의미 보존 검증**(`humanizer-fidelity`) + **과윤문 검토**(`humanizer-naturalness`) + 단계별 산출물 |

"정밀/꼼꼼히/--strict"라고 명시하거나 입력이 8,000자를 넘으면 자동으로 `strict`로 올라갑니다. 한국어와 영어를 모두 처리하고, 블로그·에세이에는 "숨결 불어넣기"(개성·리듬 주입)를 적용합니다.

```
"/gx-humanizer 제안서.md AI 글쓰기 흔적 교정해줘"
"/gx-humanizer 보고서.md 정밀 모드로 교정해줘"        ← strict (의미 보존·과윤문 검증)
```

### visualize

`gx-visualize`는 **18번째 스킬**로 추가되어 `oh-my-gx`가 GX 스킬 18개가 됐습니다. GX 작업 산출물(PRD·설계서·diff·codemap)을 근거가 추적되는 JSON IR과 한국어 HTML로 바꿉니다. 설계·구현·리뷰·커밋 게이트를 대신하지 않으며, 시각화를 명시적으로 요청했을 때만 실행됩니다.

```
"요구사항 추적 맵을 시각화해줘"     ← trace    (요구사항 → 기능 → 테스트 연결)
"진행 상태를 그림으로 보여줘"       ← progress (Phase·Gate·검증 상태)
"변경 영향도를 시각화해줘"          ← impact   (추가·삭제·변경·이동)
"시각화 포함"                      ← 현재 phase 기본값 (design→service · review→impact · 그 외→progress)
```

기본 출력은 `.dev/{branch-slug}/visual/`이며, `--backend auto`는 `Archify → Mermaid → 정적 HTML` 순으로 실행 가능한 렌더러를 고릅니다. Archify가 없거나 실행에 실패하면 사용자에게 묻지 않고 1회 자동 설치를 시도한 뒤, 그래도 안 되면 Mermaid, 다시 안 되면 정적 HTML로 폴백합니다. 정적 파일명·코드 근거만 사용하며 실제 배포 토폴로지나 운영 인프라를 자동 탐색하지 않습니다.

`--scope all`은 `.dev/architecture/`에 도메인별로 누적 아키텍처 맵을 매 실행 전체 재스캔으로 갱신합니다. 뷰별 입력·출력 계약, 도메인 분할 규칙, 실패 시 문제 해결은 [docs/gx-visualize-guide.md](docs/gx-visualize-guide.md)를 참고하세요.

### commit / pull-request

```
"커밋해줘"      ← 브랜치명에서 타입 파싱, 변경사항 분석, 한국어 커밋 메시지 생성
"PR 만들어줘"   ← 커밋 히스토리 분석, PR 제목/본문 자동 생성
```

> **SVN 프로젝트**: commit/pull-request는 Git 전용입니다. SVN에서는 리뷰(및 `tdd`라면 verify 게이트)까지 마친 뒤 터미널에서 `svn commit`을 직접 실행하세요.

---

## 에이전트 팀

스킬은 내부적으로 직무별 에이전트 팀을 부릅니다. 에이전트 하나는 관점 하나만 맡습니다.

| 분류 | 에이전트 | 역할 |
|------|---------|------|
| **제품** | product-owner | 요구사항 구체화, PRD 작성, 인수 검증 |
| **설계** | architect | 기술 설계 (변경 범위, API, 구현 순서) |
| | test-architect | 설계의 testability 평가 + 점수 산정 (tdd) |
| **구현** | coder | 설계 기반 코드 구현 (dev) |
| | red-writer | 실패 테스트 작성 전담 (tdd) |
| | implementer | GREEN+REFACTOR 통합 구현 (tdd) |
| | green-coder | 통과 최소 코드 작성 (단독 스킬 전용) |
| | refactor-coder | GREEN 유지하며 정리 (단독 스킬 전용) |
| **리뷰** | design-critic | 암묵적 가정 도전, 과잉 설계 식별 |
| | qa-manager | 코드 리뷰 + 스펙 충족 검증 (dev) |
| | reviewer | spec+quality 통합 리뷰 (tdd) |
| | security-auditor | 정책/보안/허점 교차 검증 |
| **윤문 검증** | humanizer-fidelity | 의미 보존 감사 (strict) |
| | humanizer-naturalness | 과윤문/AI티 잔존 검토 (strict) |
| **분석** | researcher | 코드베이스 조사 + 기술 비교 |
| **복구** | hacker | 제약 우회, 정체 탈출 |
| | simplifier | 복잡도 제거, 범위 축소 |

---

## 안전장치

- 자동화는 PR 생성까지만입니다. **PR 머지는 사용자가 직접** 합니다. `git push --force`(강제 푸시)는 설정 수준(deny 목록)에서 차단되며, `gh pr merge`는 도구 차단이 아닌 운영 원칙으로 — 사용자가 명시적으로 요청할 때만 수행합니다.
- 보호 브랜치(**main/master/develop**)에는 훅이 직접 커밋을 차단합니다.
- `tdd`의 verify 게이트는 "should work" 같은 추측성 표현을 막습니다 — 실제 테스트 실행 증거가 없으면 commit으로 넘어가지 못하고, 게이트 미통과 상태의 커밋 시도는 **훅이 감지해 한 번 더 확인**을 받습니다.
- SVN 프로젝트에서는 Claude가 `svn commit`을 대신 실행하지 않습니다 (훅 차단).
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
<summary><b>dev와 tdd 중 뭘 써야 하나요?</b></summary>

**판단 기준은 "정답을 자동 테스트로 표현할 수 있고, 그래야 하는가"입니다.** 결제·인증·정산 같은 핵심 비즈니스 로직, 계산·검증, 버그 수정(재현 테스트 먼저), 리팩토링이라면 `tdd`가 맞습니다. UI·설정·문서 변경, 외부 연동, 프로토타입, 테스트 인프라가 없는 레거시처럼 테스트로 명세를 떨어뜨리기 어려운 작업이라면 `dev`가 낫습니다. "TDD로", "테스트 먼저" 키워드를 쓰면 `tdd`가 자동 발동하고, 애매하면 어느 방식으로 갈지 물어봅니다.
</details>

<details>
<summary><b>context 없이도 dev/tdd를 실행할 수 있나요?</b></summary>

네, 없어도 동작합니다. 다만 context를 등록해두면 AI가 도메인 용어를 정확히 이해해 더 정확한 코드를 만듭니다.
</details>

<details>
<summary><b>dev/tdd를 실행하면 바로 코드를 짜나요?</b></summary>

아닙니다. PO 에이전트가 먼저 Q&A로 요구사항을 다듬어 PRD를 만들고, 설계자가 기술 설계를 마친 다음, 사용자가 승인해야 구현에 들어갑니다. 단계마다 선택형이나 자유입력형 질문으로 확인을 받습니다.
</details>

<details>
<summary><b>dev/tdd 도중에 멈추면 처음부터 다시 해야 하나요?</b></summary>

아닙니다. "이어서 해줘"라고 말하면 `.dev/{branch-slug}/state.md`에 저장된 진행 상태를 읽어 멈춘 단계부터 다시 시작합니다. `dev`와 `tdd`는 서로의 진행 상태를 구분하므로 잘못된 파이프라인으로 재개되는 일은 없습니다. 단, **v1.18.0 이전 버전에서 생성된 세션**(state.md의 `mode`가 `all`/`core`가 아닌 경우)은 호환성이 제거되어 재개할 수 없으며, 새로 시작해야 합니다.
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

네. `/gx-setup`을 실행하면 VCS를 자동으로 감지합니다. SVN 프로젝트에서도 `dev`·`tdd` 파이프라인의 PRD·설계·구현·리뷰가 똑같이 동작하고, 커밋만 `svn commit`으로 직접 하면 됩니다. `context`·`lens`·`research`·`humanizer` 같은 다른 스킬도 모두 그대로 쓸 수 있습니다.
</details>

<details>
<summary><b>Codex에서도 쓸 수 있나요?</b></summary>

Windows Codex CLI 0.154.0에서 설치된 스킬 17개를 확인하고 `setup → TDD → native 교차 리뷰 → verify`를 실제 실행했습니다. 수정 브랜치 설치 명령과 채팅 예시는 [Codex 사용 가이드](docs/codex-guide.md)에 있습니다.

`dev`·`tdd`·`lens`·`setup`의 번들 파일 경로 문제는 해결됐습니다. 이 넷은 자기 `phases/`·`references/` 파일을 플러그인 루트 기준 절대경로로 읽었는데, 지금은 상대경로로 바꿔 설치 위치와 무관하게 동작합니다. 스킬 본문의 도구 이름이 Claude Code 기준이라는 문제는 **스킬 17개 전부에 "하네스 적응" 노트를 넣어** 해결했습니다 — `Task`는 `spawn_agent`로, `AskUserQuestion`은 `request_user_input`으로, `Skill()`은 해당 `SKILL.md`를 읽는 것으로 옮기라고 각 스킬이 직접 안내합니다.

역할 본문·tools/tier 인덱스와 setup 템플릿을 스킬에 동봉합니다. `/hooks`에서 훅 정의와 신뢰를 확인하세요. 중첩 외부 CLI와 무인 커밋은 Codex 권한 정책에 따라 막힐 수 있으며, 역할의 소스 미열람은 아직 독립 trace로 입증하지 못했습니다. 구체적인 결과와 제한은 [실측 보고서](docs/reports/2026-09-14-codex-validation.md)와 [하네스 지원](#하네스-지원)을 참고하세요.
</details>

<details>
<summary><b>플러그인 업데이트는?</b></summary>

`/plugin marketplace update oh-my-gx`
</details>

<details>
<summary><b>버전별 변경사항은 어디서 보나요?</b></summary>

[CHANGELOG.md](CHANGELOG.md)에 릴리스별로 정리되어 있습니다. 특히 **v1.18.0부터 레거시 `--hotfix` 플래그가 제거**되었습니다 — 자연어 "긴급/핫픽스"는 그대로 핵심 모드로 동작하므로 대부분 영향이 없지만, 과거 스크립트나 alias에 `--hotfix`를 직접 박아 쓰던 경우 `--core`로 교체해야 합니다.
</details>
