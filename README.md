<div align="center">

# oh-my-gx

**GX 사업본부 개발자들을 위한 PRD, 설계, 구현, 리뷰, PR까지 처리하는 개발 자동화 플러그인**

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
| "긴급 수정해줘" | dev (hotfix) |
| "PRD만 작성해줘" | dev (단일 단계) |
| "이어서 해줘" | dev (재개) |
| ".dev/prd.md AI 흔적 교정해줘" | humanizer |
| "클라우드 네이티브 트렌드 조사해줘" | research |
| "커밋해줘" | commit |
| "PR 만들어줘" | pull-request |

### 개발 흐름

`context` → `dev` 두 단계로 개발합니다. `dev`만 단독으로 써도 됩니다.

1. `requirements/` 폴더에 기획서(PDF, 이미지, 텍스트)를 넣습니다
2. `references/` 폴더에 준수해야 할 외부 규격 문서를 넣어두면 설계·구현·리뷰 시 자동으로 참조합니다
3. "context 만들어줘"로 도메인 지식을 등록합니다
4. "개발해줘"로 PRD → 설계 → 구현 → 리뷰 → PR까지 실행합니다

각 단계 사이에 사용자 승인이 필요합니다. 승인 없이 다음으로 넘어가지 않습니다.

### 외부 규격 참조

프로젝트가 준수해야 할 외부 규격이 있다면 `references/` 디렉토리에 문서를 넣어둡니다:

```
references/
├── 시큐어코딩-가이드.md
├── API-설계-표준.md
└── eGovFrame/
    └── 규칙.md
```

`/gx-dev` 실행 시 설계·구현·리뷰 에이전트가 자동으로 참조합니다. 없어도 동작하지만, 등록하면 규격 준수를 자동 검증합니다.

기존 문서를 그대로 넣어도 동작합니다. 아래는 에이전트가 더 효과적으로 참조하기 위한 권장 팁입니다:
- 문서 상단에 요약이나 목차를 넣으면 에이전트가 필요한 부분만 탐색합니다
- 항목에 번호/ID(§3.2 등)를 부여하면 설계서에서 정확히 참조합니다
- 체크리스트 형태로 작성하면 QA가 항목별로 준수 여부를 검증합니다

---

## 스킬 상세

### context

기획서, 요구사항 문서, 코드베이스를 분석하여 도메인 지식을 `context/{도메인}/`에 등록합니다. 등록된 context는 `dev` 실행 시 자동 참조됩니다.

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

내부적으로 에이전트 팀이 단계를 나눠 처리합니다:

| 에이전트 | 역할 | 단계 |
|---------|------|------|
| 제품책임자(PO) | 요구사항 구체화, PRD 작성, 인수 검증 | requirements, complete |
| 설계자 | 기술 설계 (변경 범위, API, 구현 순서) | design |
| 설계 비판자 | 암묵적 가정 도전, 과잉 설계 식별 | design (중형 이상) |
| 개발자 | 설계 기반 코드 구현 | implement |
| QA 매니저 | 코드 리뷰 + 스펙 충족 검증 | implement, review |
| 보안 감사자 | 정책/보안/허점 교차 검증 | review |

### humanizer

PRD나 설계 문서에서 AI 글쓰기 패턴(40+가지)을 감지하고 교정합니다. 감지만 하는 audit 모드와 직접 수정하는 rewrite 모드를 지원합니다.

```
"/gx-humanizer 제안서.md AI 글쓰기 흔적 교정해줘"
"/gx-humanizer 소스코드 기반으로 기획서.md를 작성해줘"
"/gx-humanizer 발표대본.md 소스코드 기반으로 발표 대본 작성해줘"
```

### research

웹 검색과 문서 분석을 병행하여 도메인 리서치를 수행합니다. 결과물은 `/gx-context --from`으로 context 문서에 반영할 수 있습니다.

```
"클라우드 네이티브 트렌드 조사해줘"              ← 종합 리포트
"결제 시스템 비교 분석해줘 --format comparison"   ← 비교표
"인증 방식 핵심만 정리해줘 --format summary"      ← 핵심 요약
```

조사 결과는 `.research/` 디렉토리에 저장되며, 모든 발견에 출처 URL이 명시됩니다.

### commit / pull-request

```
"커밋해줘"      ← 브랜치명에서 타입 파싱, 변경사항 분석, 한국어 커밋 메시지 생성
"PR 만들어줘"   ← 커밋 히스토리 분석, PR 제목/본문 자동 생성
```

> **SVN 프로젝트**: commit/pull-request는 Git 전용입니다. SVN에서는 `/gx-dev` 리뷰까지 완료 후 `svn commit`을 직접 실행하세요.

---

## 안전장치

- PR 생성까지만 자동화합니다. **PR 머지는 사용자가 직접** 수행합니다.
- `git push --force`, `gh pr merge`는 설정 수준에서 차단됩니다.
- 보호 브랜치(main)에서 직접 커밋을 차단합니다.
- SVN 프로젝트에서는 `svn commit`을 Claude가 대신 실행하지 않습니다.
- 커밋 전 민감 파일(`.env`, `*.key`, `*.pem`, `credentials*`, `*secret*`) 감지 시 경고합니다.
- 빌드 아티팩트(`build/`, `node_modules/` 등)가 tracked 상태이면 자동으로 `.gitignore` 보강을 제안합니다.

---

## Google Chat 알림

`/oh-my-gx:setup`에서 Google Chat 웹훅을 연동하면 PR 생성 시 Chat Space에 자동 알림이 전송됩니다. 한 명이 설정하고 커밋하면 팀 전체가 받습니다.
```
[{프로젝트 이름}] 새로운 PR을 확인해주세요: {PR 주소}
[oh-my-gx] 새로운 PR을 확인해주세요: https://github.com/bs-koo/oh-my-gx/pull/1
```

---

## FAQ

<details>
<summary><b>context 없이도 dev를 실행할 수 있나요?</b></summary>

네. 없어도 동작합니다. 다만 context를 등록하면 AI가 도메인 용어를 정확히 이해하여 더 정확한 코드를 생성합니다.
</details>

<details>
<summary><b>dev를 실행하면 바로 코드를 짜나요?</b></summary>

아닙니다. PO 에이전트가 먼저 Q&A로 요구사항을 구체화하고(PRD), 설계자가 기술 설계를 거친 뒤 사용자가 승인해야 구현에 들어갑니다. 각 단계마다 선택형/자유입력형 질문으로 확인을 받습니다.
</details>

<details>
<summary><b>dev 도중에 멈추면 처음부터 다시 해야 하나요?</b></summary>

아닙니다. "이어서 해줘"라고 말하면 `.dev/state.md`에 저장된 진행 상태를 기반으로 중단된 단계부터 재개합니다.
</details>

<details>
<summary><b>PR이 자동으로 머지되나요?</b></summary>

아닙니다. PR 생성까지만 자동화합니다. `gh pr merge`는 설정 수준에서 차단되어 있습니다.
</details>

<details>
<summary><b>SVN 프로젝트에서도 사용할 수 있나요?</b></summary>

네. `/gx-setup` 실행 시 VCS를 자동 감지합니다. SVN 프로젝트에서는 `/gx-dev`의 PRD, 설계, 구현, 리뷰까지 동일하게 동작하며, 커밋만 `svn commit`으로 직접 수행하면 됩니다. `/gx-context`, `/gx-lens`, `/gx-research`, `/gx-humanizer`도 모두 사용 가능합니다.
</details>

<details>
<summary><b>플러그인 업데이트는?</b></summary>

`/plugin marketplace update oh-my-gx`
</details>
