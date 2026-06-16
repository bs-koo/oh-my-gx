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
/oh-my-gx:setup
```

---

## 사용법

자연어로 말하면 의도에 맞는 스킬이 발동됩니다. 명령어를 외울 필요 없습니다.

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
| ".dev/prd.md AI 흔적 교정해줘" | humanizer |
| "클라우드 네이티브 트렌드 조사해줘" | research |
| "기술 부채 확인해줘" | tech-debt |
| "교차 리뷰 해줘" | cross-review |
| "커밋해줘" | commit |
| "PR 만들어줘" | pull-request |

### 개발 흐름

`context` → `dev`(또는 `tdd`) 두 단계로 개발합니다. `dev`/`tdd`만 단독으로 써도 됩니다.

1. `requirements/` 폴더에 기획서(PDF, 이미지, 텍스트)를 넣습니다
2. `references/` 폴더에 준수해야 할 외부 규격 문서를 넣어두면 설계·구현·리뷰 시 자동으로 참조합니다
3. "context 만들어줘"로 도메인 지식을 등록합니다
4. "개발해줘"(`dev`) 또는 "TDD로 개발해줘"(`tdd`)로 PRD → 설계 → 구현 → 리뷰 → PR까지 실행합니다

각 단계 사이에 사용자 승인이 필요합니다. 승인 없이 다음으로 넘어가지 않습니다.

### dev vs tdd — 어떤 걸 쓰나

| | dev | tdd |
|---|---|---|
| 구현 방식 | coder가 설계 기반 구현 | **RED → GREEN → REFACTOR 격리 사이클 강제** |
| 리뷰 | qa + security 병렬 | **spec → quality 순차 강제** |
| 완료 게이트 | qa 통과 → commit | **verify 게이트(실제 테스트 실행 증거) 통과 → commit** |
| 언제 | 일반 기능 개발 | 테스트 우선·회귀 안전이 중요한 작업 |

명시적 TDD 키워드("TDD로", "테스트 먼저")가 있으면 `tdd`, 없으면 `dev`로 분기합니다.

### 외부 규격 참조

프로젝트가 준수해야 할 외부 규격이 있다면 `references/` 디렉토리에 문서를 넣어둡니다:

```
references/
├── 시큐어코딩-가이드.md
├── API-설계-표준.md
└── eGovFrame/
    └── 규칙.md
```

`/gx-dev`·`/gx-tdd` 실행 시 설계·구현·리뷰 에이전트가 자동으로 참조합니다. 없어도 동작하지만, 등록하면 규격 준수를 자동 검증합니다.

기존 문서를 그대로 넣어도 동작합니다. 아래는 에이전트가 더 효과적으로 참조하기 위한 권장 팁입니다:
- 문서 상단에 요약이나 목차를 넣으면 에이전트가 필요한 부분만 탐색합니다
- 항목에 번호/ID(§3.2 등)를 부여하면 설계서에서 정확히 참조합니다
- 체크리스트 형태로 작성하면 QA가 항목별로 준수 여부를 검증합니다

---

## 스킬 상세

### context

기획서, 요구사항 문서, 코드베이스를 분석하여 도메인 지식을 `context/{도메인}/`에 등록합니다. 등록된 context는 `dev`/`tdd` 실행 시 자동 참조됩니다.

```
"requirements 폴더에 있는 기획서 보고 context 만들어줘"   ← 문서 기반 생성
"사용량 분석 도메인 등록해줘"                            ← Q&A 기반 생성
"코드베이스 분석해서 context 자동 생성해줘"               ← 코드 스캔
"사용량 분석 도메인 동기화해줘"                          ← git 히스토리 기반 진행도 갱신
```

### lens

코드에서 비즈니스 정책을 찾아 PO/PD가 읽을 수 있는 보고서로 출력합니다. 코드를 수정하지 않습니다. 변경 아이디어를 이어서 입력하면 복잡도와 리스크 분석까지 수행합니다.

```
"현재 사용자 활동 로깅이 어떻게 되어 있는지 정리해줘"
"로그 보관 기간을 180일로 늘리면 어디에 영향이 가?"
```

### dev

자연어 요청 하나로 PRD 작성부터 PR 생성까지 전체 사이클을 수행합니다.

```
"사용량 분석 대시보드 기능 개발해줘"    ← 전체 사이클
"집계 스케줄러 오류 긴급 수정해줘"     ← hotfix 모드 (설계/리뷰 생략)
"PRD만 작성해줘"                     ← 특정 단계만
"이어서 해줘"                        ← 중단 지점부터 재개
```

내부적으로 에이전트 팀이 단계를 나눠 처리합니다(요구사항 → 설계 → 구현 → 리뷰 → 완료).

### tdd

`dev`와 동일한 6단계 골격에 **TDD 게이트를 강제**한 파이프라인입니다. 구현이 RED-GREEN-REFACTOR 사이클로 격리되고, 완료 전 verify 게이트를 반드시 통과해야 합니다.

```
"TDD로 결제 한도 검증 만들어줘"      ← 전체 TDD 사이클
"테스트 주도로 로그인 개발해줘"
```

- **requirements**: 수용 기준(AC)을 Given-When-Then 형식으로 강제 (자동 테스트로 변환 가능)
- **design**: `test-architect`가 testability 점수(1-10)를 산정, 7 미만이면 재설계
- **implement**: `red-writer`(실패 테스트) → `green-coder`(통과 최소 코드) → `refactor-coder`(정리) 격리 순차
- **review**: `spec-reviewer`(AC 충족) → `quality-reviewer`(코드 품질) 순차 게이트
- **complete**: `verify` 게이트(신선한 테스트 실행 증거) 통과 후에만 commit/PR

보조 스킬 `red` / `green` / `refactor` / `verify`는 파이프라인 내부에서 자동 호출되며, 단독으로도 사용할 수 있습니다.

### humanizer

AI 글쓰기 패턴(40+가지, 한국어 K1~K19 / 영어 E1~E19 / 공통 C1~C6)을 감지하고 교정합니다. 3가지 모드를 지원합니다.

| 모드 | 동작 |
|------|------|
| `audit` | 감지 리포트만 (수정 안 함) |
| `rewrite` | 감지 + 수정 + 변경률 상한(30% 경고 / 50% 중단) |
| `strict` | rewrite + **의미 보존 검증**(`humanizer-fidelity`) + **과윤문 검토**(`humanizer-naturalness`) + 단계별 산출물 |

"정밀/꼼꼼히/--strict" 명시 또는 입력 8,000자 초과 시 `strict`로 자동 승급합니다. 한/영 양국어를 모두 처리하며, 블로그/에세이에는 "숨결 불어넣기"(개성·리듬 주입)를 적용합니다.

```
"/gx-humanizer 제안서.md AI 글쓰기 흔적 교정해줘"
"/gx-humanizer 보고서.md 정밀 모드로 교정해줘"        ← strict (의미 보존·과윤문 검증)
```

### research

웹 검색과 문서 분석을 병행하여 도메인 리서치를 수행합니다. 결과물은 `/gx-context --from`으로 context 문서에 반영할 수 있습니다.

```
"클라우드 네이티브 트렌드 조사해줘"              ← 종합 리포트
"결제 시스템 비교 분석해줘 --format comparison"   ← 비교표
"인증 방식 핵심만 정리해줘 --format summary"      ← 핵심 요약
```

조사 결과는 `.research/` 디렉토리에 저장되며, 모든 발견에 출처 URL이 명시됩니다.

### tech-debt

코드베이스의 기술 부채를 4가지 유형(코드 / 아키텍처 / 의존성 / 테스트)별로 분석하고, 심각도 × 수정 용이성 × 영향 범위를 기반으로 우선순위 로드맵을 제공합니다. **읽기 전용** — 코드를 수정하지 않습니다.

```
"기술 부채 확인해줘"                             ← 전체 프로젝트 분석
"/gx-tech-debt 결제 도메인"                      ← 특정 도메인만
"/gx-tech-debt --type deps"                      ← 의존성만 점검
```

- **Health Score**: 100점 만점 A~F 등급으로 건강 상태 표시
- **의존성 스캔**: Java/Kotlin(Gradle), Node(npm audit/outdated), Python(pip-audit) 자동 점검
- **아키텍처 비교**: `context/{도메인}/architecture.md`가 있으면 의도된 구조 vs 실제 구조 비교
- `gx-lens`와 역할 분리: `gx-lens`는 비즈니스 정책, `gx-tech-debt`는 기술 품질

### cross-review

`/gx-dev`·`/gx-tdd` 완료 후 단발 호출 전용. PRD/설계서/Trust Ledger 등 산출물을 컨텍스트로 주입하여 "약속 대비 충실도"를 교차 검증합니다. 일반 코드 품질 리뷰가 아닌 **AC 충족 + 설계 범위 이탈 + 신규 위험만** 보고합니다.

```
"교차 리뷰 해줘"                                   ← 호출 시 advisor 선택 (codex / claude)
"/gx-cross-review --advisor codex"                ← codex 강제 (다른 모델 관점)
"/gx-cross-review --advisor claude"               ← qa-manager + security-auditor를 cross 미션으로 호출
```

> **별도 codex 플러그인 필요**: codex advisor 사용 시 `openai/codex-plugin-cc`가 별도로 설치되어 있어야 합니다.

### commit / pull-request

```
"커밋해줘"      ← 브랜치명에서 타입 파싱, 변경사항 분석, 한국어 커밋 메시지 생성
"PR 만들어줘"   ← 커밋 히스토리 분석, PR 제목/본문 자동 생성
```

> **SVN 프로젝트**: commit/pull-request는 Git 전용입니다. SVN에서는 `/gx-dev` 리뷰까지 완료 후 `svn commit`을 직접 실행하세요.

---

## 에이전트 팀

스킬은 내부적으로 직무별 에이전트 팀을 호출합니다. 각 에이전트는 하나의 관점만 책임집니다.

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

- PR 생성까지만 자동화합니다. **PR 머지는 사용자가 직접** 수행합니다.
- `git push --force`, `gh pr merge`는 설정 수준에서 차단됩니다.
- 보호 브랜치(main)에서 직접 커밋을 차단합니다.
- SVN 프로젝트에서는 `svn commit`을 Claude가 대신 실행하지 않습니다.
- 커밋 전 민감 파일(`.env`, `*.key`, `*.pem`, `credentials*`, `*secret*`) 감지 시 경고합니다.
- 빌드 아티팩트(`build/`, `node_modules/` 등)가 tracked 상태이면 자동으로 `.gitignore` 보강을 제안합니다.
- `tdd`의 verify 게이트는 "should work" 같은 추측 표현을 차단하고, 실제 테스트 실행 증거 없이는 commit에 진입하지 못합니다.

---

## Google Chat 알림

`/oh-my-gx:setup`에서 Google Chat 웹훅을 연동하면 PR 생성 시 Chat Space에 자동 알림이 전송됩니다. 한 명이 설정하고 커밋하면 팀 전체가 받습니다.

```
[oh-my-gx] 새로운 PR을 확인해주세요: https://github.com/bs-koo/oh-my-gx/pull/1
```

---

## FAQ

<details>
<summary><b>dev와 tdd 중 뭘 써야 하나요?</b></summary>

일반 기능 개발은 `dev`, 테스트를 먼저 작성하고 회귀를 막아야 하는 작업은 `tdd`입니다. "TDD로", "테스트 먼저" 같은 키워드를 쓰면 자동으로 `tdd`가 발동합니다. 애매하면 어느 방식으로 진행할지 물어봅니다.
</details>

<details>
<summary><b>context 없이도 dev/tdd를 실행할 수 있나요?</b></summary>

네. 없어도 동작합니다. 다만 context를 등록하면 AI가 도메인 용어를 정확히 이해하여 더 정확한 코드를 생성합니다.
</details>

<details>
<summary><b>dev/tdd를 실행하면 바로 코드를 짜나요?</b></summary>

아닙니다. PO 에이전트가 먼저 Q&A로 요구사항을 구체화하고(PRD), 설계자가 기술 설계를 거친 뒤 사용자가 승인해야 구현에 들어갑니다. 각 단계마다 선택형/자유입력형 질문으로 확인을 받습니다.
</details>

<details>
<summary><b>dev/tdd 도중에 멈추면 처음부터 다시 해야 하나요?</b></summary>

아닙니다. "이어서 해줘"라고 말하면 `.dev/state.md`에 저장된 진행 상태를 기반으로 중단된 단계부터 재개합니다.
</details>

<details>
<summary><b>humanizer의 strict 모드는 일반 모드와 뭐가 다른가요?</b></summary>

`audit`/`rewrite`는 단일 스킬이 가볍게 처리합니다. `strict`는 윤문 후 `humanizer-fidelity`가 의미 훼손(수치·고유명사·인용 변형)을, `humanizer-naturalness`가 과윤문·AI티 잔존을 교차 검증하고, 필요 시 재윤문합니다. 8,000자 초과 시 자동으로 strict로 전환됩니다.
</details>

<details>
<summary><b>PR이 자동으로 머지되나요?</b></summary>

아닙니다. PR 생성까지만 자동화합니다. `gh pr merge`는 설정 수준에서 차단되어 있습니다.
</details>

<details>
<summary><b>SVN 프로젝트에서도 사용할 수 있나요?</b></summary>

네. `/gx-setup` 실행 시 VCS를 자동 감지합니다. SVN 프로젝트에서는 PRD·설계·구현·리뷰까지 동일하게 동작하며, 커밋만 `svn commit`으로 직접 수행합니다.
</details>

<details>
<summary><b>플러그인 업데이트는?</b></summary>

`/plugin marketplace update oh-my-gx`
</details>
