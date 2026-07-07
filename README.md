<div align="center">

# oh-my-gx

**GX 사업본부 개발자를 위한 개발 자동화 플러그인 — PRD·설계·구현·리뷰·PR까지 에이전트 팀이 처리합니다**

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-2ea44f?style=for-the-badge)](https://bs-koo.github.io/oh-my-gx/)

</div>

---

## 설치

```bash
# Claude Code CLI에서 실행
/plugin marketplace add bs-koo/oh-my-gx
/plugin install oh-my-gx@oh-my-gx
```

## 시작

```bash
/oh-my-gx:gx-setup
```

---

## 사용법

명령어를 외울 필요는 없습니다. 자연어로 말하면 의도에 맞는 스킬이 알아서 발동됩니다.

| 이렇게 말하면 | 발동 스킬 |
|--------------|----------|
| "기획서 보고 context 만들어줘" | context |
| "현재 로깅 정책 정리해줘" | lens |
| "대시보드 기능 개발해줘" | dev |
| "TDD로 결제 검증 만들어줘" | tdd |
| "실패 테스트 먼저 작성해줘" | red |
| "테스트 통과시켜줘" | green |
| "중복 제거 정리해줘" | refactor |
| "완료 검증해줘" | verify |
| "긴급 수정해줘" | dev (hotfix) |
| "PRD만 작성해줘" | dev / tdd (단일 단계) |
| "이어서 해줘" | dev / tdd (재개) |
| ".dev/prd.md AI 흔적 교정해줘" | humanizer |
| "클라우드 네이티브 트렌드 조사해줘" | research |
| "기술 부채 확인해줘" | tech-debt |
| "교차 리뷰 해줘" | cross-review |
| "커밋해줘" | commit |
| "PR 만들어줘" | pull-request |

### 개발 흐름

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

**`dev`가 맞는 작업** — UI·화면 조정, 설정·문서·인프라 변경, 외부 시스템 연동, 빠른 프로토타입, 테스트 인프라가 없는 레거시처럼 *자동 테스트로 명세를 떨어뜨리기 어렵거나 그럴 필요가 적은* 작업.

**`tdd`가 맞는 작업** — 결제·인증·정산 같은 핵심 비즈니스 로직, 계산·검증처럼 입출력이 명확한 로직, 회귀가 치명적인 모듈, 리팩토링(안전망 필요), 버그 수정(재현 테스트 먼저)처럼 *정답을 자동 테스트로 표현할 수 있고 그래야 하는* 작업.

> **한 줄 기준**: "이 작업의 정답을 자동 테스트로 표현할 수 있고, 그래야 하는가?" → 예면 `tdd`, 아니오·애매하면 `dev`.

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

`/gx-dev`·`/gx-tdd`를 실행하면 설계·구현·리뷰 에이전트가 이 문서들을 자동으로 참조합니다. 없어도 동작하지만, 등록해두면 규격 준수 여부를 알아서 검증해줍니다.

기존 문서를 그대로 넣어도 됩니다. 다만 에이전트가 더 잘 찾아 쓰게 하려면 아래 팁이 도움이 됩니다:
- 문서 맨 위에 요약이나 목차를 두면 에이전트가 필요한 부분만 골라 봅니다
- 항목마다 번호나 ID(§3.2 등)를 붙이면 설계서에서 정확히 짚어 인용합니다
- 체크리스트 형태로 적어두면 QA가 항목별로 준수 여부를 확인합니다

---

## 스킬 상세

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

### dev

자연어 요청 한 줄이면 PRD 작성부터 PR 생성까지 전체 사이클이 돌아갑니다.

```
"사용량 분석 대시보드 기능 개발해줘"    ← 전체 사이클
"집계 스케줄러 오류 긴급 수정해줘"     ← hotfix 모드 (설계/리뷰 생략)
"PRD만 작성해줘"                     ← 특정 단계만
"이어서 해줘"                        ← 중단 지점부터 재개
```

내부에서는 에이전트 팀이 요구사항 → 설계 → 구현 → 리뷰 → 완료로 단계를 나눠 처리합니다. UI·설정·문서 변경, 외부 연동, 프로토타입처럼 자동 테스트로 명세를 떨어뜨리기 어려운 작업에 적합합니다. 정답을 테스트로 먼저 표현할 수 있는 작업이라면 `tdd`를 쓰세요.

### tdd

`dev`와 같은 6단계 골격을 쓰지만 **구현을 테스트가 끌고 가는** 별도 파이프라인입니다. 실패 테스트를 먼저 쓰고(RED) 통과시키며 구현하고(GREEN) 정리하며(REFACTOR), 완료 전에는 verify 게이트를 반드시 통과해야 합니다. `dev`와 어떤 작업에 무엇을 쓸지는 위 **dev vs tdd — 어떤 걸 쓰나** 표를 참고하세요.

```
"TDD로 결제 한도 검증 만들어줘"      ← 전체 TDD 사이클
"테스트 주도로 로그인 개발해줘"
```

- **requirements**: 수용 기준(AC)을 Given-When-Then 형식으로 강제 (자동 테스트로 변환 가능)
- **design**: `test-architect`가 testability 점수(1-10)를 매기고, 7 미만이면 재설계
- **implement**: `red-writer`(실패 테스트) → `green-coder`(통과 최소 코드) → `refactor-coder`(정리)를 격리된 순서로
- **review**: `spec-reviewer`(AC 충족) → `quality-reviewer`(코드 품질) 순차 게이트
- **complete**: `verify` 게이트(신선한 테스트 실행 증거)를 통과해야만 commit/PR

보조 스킬 `red` / `green` / `refactor` / `verify`는 파이프라인 안에서 자동으로 불려 나오며, 단독으로도 쓸 수 있습니다.

### humanizer

AI 글쓰기 패턴(40+가지, 한국어 K1~K19 / 영어 E1~E19 / 공통 C1~C6)을 감지하고 교정합니다. 모드는 세 가지입니다.

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

### research

웹 검색과 문서 분석을 함께 돌려 도메인 리서치를 수행합니다. 결과물은 `/gx-context --from`으로 context 문서에 반영할 수 있습니다.

```
"클라우드 네이티브 트렌드 조사해줘"              ← 종합 리포트
"결제 시스템 비교 분석해줘 --format comparison"   ← 비교표
"인증 방식 핵심만 정리해줘 --format summary"      ← 핵심 요약
```

조사 결과는 `.research/` 디렉토리에 저장되고, 모든 발견에는 출처 URL이 함께 붙습니다.

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
- `gx-lens`와는 역할이 갈립니다. `gx-lens`는 비즈니스 정책을, `gx-tech-debt`는 기술 품질을 봅니다

### cross-review

`/gx-dev`·`/gx-tdd`를 끝낸 뒤 한 번만 부르는 전용 스킬입니다. PRD/설계서/Trust Ledger 같은 산출물을 컨텍스트로 넣어 "약속한 대로 만들었는가"를 교차 검증합니다. 일반 코드 품질 리뷰가 아니라 **AC 충족, 설계 범위 이탈, 신규 위험만** 짚어 보고합니다.

```
"교차 리뷰 해줘"                                   ← 호출 시 advisor 선택 (codex / claude)
"/gx-cross-review --advisor codex"                ← codex 강제 (다른 모델 관점)
"/gx-cross-review --advisor claude"               ← qa-manager + security-auditor를 cross 미션으로 호출
```

교차 리뷰 결과는 advisor 종류와 무관하게 `${DEV_DIR}/cross-review.md`에 저장됩니다. 발견된 항목은 자동으로 고치지 않고, 사용자 승인(전부/일부/직접 입력/건너뛰기)을 거쳐 `coder` 에이전트에 위임합니다.

> **별도 codex 플러그인 필요**: codex advisor를 쓰려면 `openai/codex-plugin-cc`가 따로 설치되어 있어야 합니다.

### commit / pull-request

```
"커밋해줘"      ← 브랜치명에서 타입 파싱, 변경사항 분석, 한국어 커밋 메시지 생성
"PR 만들어줘"   ← 커밋 히스토리 분석, PR 제목/본문 자동 생성
```

> **SVN 프로젝트**: commit/pull-request는 Git 전용입니다. SVN에서는 `/gx-dev` 리뷰까지 마친 뒤 `svn commit`을 직접 실행하세요.

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
| | green-coder | 통과 최소 코드 작성 (tdd, YAGNI) |
| | refactor-coder | GREEN 유지하며 정리 (tdd) |
| **리뷰** | design-critic | 암묵적 가정 도전, 과잉 설계 식별 |
| | qa-manager | 코드 리뷰 + 스펙 충족 검증 (dev) |
| | spec-reviewer | AC 충족만 검증 (tdd 1단계) |
| | quality-reviewer | 코드 품질만 검증 (tdd 2단계) |
| | security-auditor | 정책/보안/허점 교차 검증 |
| **윤문 검증** | humanizer-fidelity | 의미 보존 감사 (strict) |
| | humanizer-naturalness | 과윤문/AI티 잔존 검토 (strict) |
| **분석** | researcher | 코드베이스 조사 + 기술 비교 |
| **복구** | hacker | 제약 우회, 정체 탈출 |
| | simplifier | 복잡도 제거, 범위 축소 |

---

## 안전장치

- 자동화는 PR 생성까지만입니다. **PR 머지는 사용자가 직접** 합니다.
- `git push --force`, `gh pr merge`는 설정 수준에서 막혀 있습니다.
- 보호 브랜치(main)에는 직접 커밋하지 못하게 막습니다.
- SVN 프로젝트에서는 Claude가 `svn commit`을 대신 실행하지 않습니다.
- 커밋 전에 민감 파일(`.env`, `*.key`, `*.pem`, `credentials*`, `*secret*`)이 잡히면 경고합니다.
- 빌드 아티팩트(`build/`, `node_modules/` 등)가 tracked 상태면 `.gitignore`를 보강하라고 제안합니다.
- `tdd`의 verify 게이트는 "should work" 같은 추측성 표현을 막습니다. 실제 테스트 실행 증거가 없으면 commit으로 넘어가지 못합니다.

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

아닙니다. "이어서 해줘"라고 말하면 `.dev/state.md`에 저장된 진행 상태를 읽어 멈춘 단계부터 다시 시작합니다.
</details>

<details>
<summary><b>humanizer의 strict 모드는 일반 모드와 뭐가 다른가요?</b></summary>

`audit`/`rewrite`는 단일 스킬이 가볍게 처리합니다. `strict`는 윤문을 마친 뒤 `humanizer-fidelity`가 의미 훼손(수치·고유명사·인용 변형)을, `humanizer-naturalness`가 과윤문·AI티 잔존을 교차 검증하고, 필요하면 다시 윤문합니다. 8,000자를 넘으면 자동으로 strict로 전환됩니다.
</details>

<details>
<summary><b>PR이 자동으로 머지되나요?</b></summary>

아닙니다. 자동화는 PR 생성까지입니다. `gh pr merge`는 설정 수준에서 막혀 있습니다.
</details>

<details>
<summary><b>SVN 프로젝트에서도 사용할 수 있나요?</b></summary>

네. `/gx-setup`을 실행하면 VCS를 자동으로 감지합니다. SVN 프로젝트에서도 `dev`·`tdd` 파이프라인의 PRD·설계·구현·리뷰가 똑같이 동작하고, 커밋만 `svn commit`으로 직접 하면 됩니다. `context`·`lens`·`research`·`humanizer` 같은 다른 스킬도 모두 그대로 쓸 수 있습니다.
</details>

<details>
<summary><b>플러그인 업데이트는?</b></summary>

`/plugin marketplace update oh-my-gx`
</details>
