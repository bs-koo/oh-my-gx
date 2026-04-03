# oh-my-gx 사용 가이드

GX 사업본부 개발자를 위한 개발 자동화 플러그인. PRD, 설계, 구현, 리뷰, PR까지 에이전트 팀이 처리합니다.

---

## 1. 개요

### 스킬 전체 맵

```
/gx-setup ─────── 초기 설정 (gh, JDK, 인증, Chat 알림)
                     │
/gx-context ──────── 도메인 지식 등록/갱신
     │                     ↑ (context 동기화 제안)
     │               /gx-commit ── 커밋
     │                     ↑
     │               /gx-dev ──── PRD → 설계 → 구현 → 리뷰 → 커밋 → PR
     │                     ↓
     │               /gx-pull-request ── PR 생성
     │
/gx-lens ─────────── 현행 정책 분석 + 영향도 (읽기 전용)
/gx-research ─────── 외부 리서치 → context 반영 가능
/gx-humanizer ────── AI 글쓰기 교정
```

### 지원 환경

| 항목 | 지원 |
|------|------|
| VCS | Git, SVN |
| 언어/프레임워크 | Java (Spring Boot, Gradle), Node.js |
| OS | Windows, macOS, Linux |

---

## 2. 시작하기

### 2.1 설치

```
/install-plugin bs-koo/oh-my-gx
```

### 2.2 `/gx-setup` 초기 설정

```
/gx-setup
```

아래 항목을 단계별로 확인합니다:

| 단계 | 내용 | 출력 예시 |
|------|------|-----------|
| 0 | VCS 감지 (Git/SVN) | `VCS 감지 : 완료 ✅ (git)` |
| 1 | 필수 도구 (gh CLI, JDK) | `gh : 완료 ✅` |
| 2 | GitHub 인증 | `GH 인증 : 완료 ✅` |
| 3 | context/ 안내 | 도메인 지식 등록 안내 |
| 4 | Google Chat 연동 (선택) | 웹훅 URL 입력 |

설정 완료 후 퀵스타트가 표시됩니다:

```
=== 퀵스타트 ===
/gx-context {도메인}     → 도메인 지식 등록
/gx-lens {질문}          → 현행 분석 + 영향도
/gx-dev {요청}           → 전체 개발 사이클 (PRD~PR)
```

### 2.3 config.json 주요 설정

`.claude/config.json`에서 프로젝트별 설정을 조정합니다.

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `vcs` | `""` (git 취급) | `"git"` 또는 `"svn"` |
| `conventions.branchTypes` | feat, fix, refactor 등 9종 | 브랜치 타입 허용 목록 |
| `conventions.commitFormat` | `{type}: {message}` | 커밋 메시지 형식 |
| `conventions.prTitleMapping` | feat→FEATURE 등 | PR 제목 타입 매핑 |
| `projectTypes` | java-spring, node | 프로젝트 감지 및 빌드 명령 |
| `sensitiveFilePatterns` | `.env*`, `*.key` 등 | 커밋 시 경고할 파일 패턴 |
| `notifications.googleChat` | 비활성 | PR 생성 시 Chat 알림 |

---

## 3. 핵심 개념: 플러그인이 동작하는 방식

### 3.1 오케스트레이터와 에이전트 팀

`/gx-dev`를 실행하면 **오케스트레이터**가 기동합니다. 오케스트레이터는 `SKILL.md`(`.claude/skills/dev/SKILL.md`)에 정의된 프로토콜에 따라 Phase를 순차적으로 실행하는 지휘자입니다.

#### 오케스트레이터의 역할

1. **Phase 파일 로드**: 각 Phase에 진입할 때 해당 Phase 파일(`.claude/skills/dev/phases/phase-{name}.md`)을 Read하여 지시사항을 메모리에 로드합니다.
2. **Agent 호출**: Phase 파일의 지시에 따라 적절한 Agent를 `Task()`로 호출합니다. 이때 코드 맵, PRD, 설계서, REFERENCES, DOMAIN_CONTEXT 등 필요한 컨텍스트를 프롬프트에 포함합니다.
3. **결과 수집 및 판단**: Agent의 출력을 받아 다음 행동(사용자에게 질문, 다음 Agent 호출, 다음 Phase 전환)을 결정합니다.
4. **상태 관리**: `.dev/state.md`에 현재 Phase와 Step을 지속적으로 기록하여 세션 재개를 지원합니다.

#### Agent 팀 (9명)

| Agent | 분류 | 역할 | 관점 | 모델 |
|-------|------|------|------|------|
| product-owner | PRODUCT | PRD 작성 + 인수 검증 | "뭘 만들지" / "비즈니스 의도대로 됐나" | sonnet |
| architect | PLANNING | 설계 | "어떻게 만들지" / "구조적 일관성" | opus |
| design-critic | REVIEW | 설계 비판 검토 | "이 가정이 맞나" / "더 단순하게 안 되나" | opus |
| coder | EXECUTION | 구현 + 수정 | "만든다" | opus |
| qa-manager | REVIEW | 코드 리뷰 + 스펙 충족 검증 | "스펙대로 됐나" | sonnet |
| security-auditor | REVIEW | 정책/보안/허점 감사 | "뭘 놓쳤나" | sonnet |
| researcher | ANALYSIS | 코드베이스 조사 + 기술 비교 | "이해한다" (독립 호출 전용) | sonnet |
| hacker | RECOVERY | 제약 우회 + 정체 탈출 | "다른 길이 있다" (정체 감지 시 호출) | sonnet |
| simplifier | RECOVERY | 복잡도 제거 + 범위 축소 | "더 작게 만들자" (정체 감지 시 호출) | sonnet |

#### 모델 라우팅 원칙

Agent마다 적합한 모델이 배정됩니다:

| 작업 유형 | 모델 | 이유 |
|-----------|------|------|
| 비판적 분석 (설계 비판, 가정 도전) | opus | 추론 깊이 우선 |
| 구조적 설계 (아키텍처 결정) | opus | 설계 품질 우선 |
| 코드 구현/수정 | opus | 복잡한 코드 생성 품질 우선 |
| 산출물 생성 (PRD, 리뷰, 감사) | sonnet | 비용 효율 우선 |
| 정체 탈출 (제약 우회, 범위 축소) | sonnet | 빠른 판단 우선 |
| 단순 검증 (빌드/테스트 결과 판단) | 오케스트레이터 직접 | Agent 불필요 |

---

### 3.2 Phase 실행 루프 상세

#### 모드별 Phase 목록

| 모드 | Phase 경로 | 용도 |
|------|-----------|------|
| NORMAL | setup → requirements → design → implement → review → complete | 전체 파이프라인 |
| HOTFIX | setup → requirements(경량) → implement → complete | 긴급 버그 수정 |
| IMPLEMENT | setup → implement → complete | 설계 없이 바로 구현 |

#### Phase 실행 루프 의사코드

오케스트레이터는 아래 루프를 기계적으로 실행합니다. "범위가 작으니 건너뛰자"와 같은 자의적 판단은 허용되지 않습니다.

```
for phase in PHASES:

    # 1. 산출물 게이트 — 이전 Phase 산출물이 없으면 이전 Phase부터
    if phase == "design" and not exists(".dev/prd.md"):
        → phase-requirements부터 실행
    if phase == "implement" and not exists(".dev/design.md"):
        → phase-design부터 실행  (hotfix 모드 제외)

    # 2. Phase 파일 Read
    Read(".claude/skills/dev/phases/phase-{phase}.md")

    # 3. Phase 파일의 지시에 따라 Agent 호출 + 결과 수집

    # 4. state.md 갱신
    Update state.md → phases.{phase}: completed

    # 5. 다음 Phase로 진행
```

#### Phase별 실행 흐름 다이어그램

```
[setup]
  │  환경 준비, 브랜치 생성, 코드 맵 생성
  │  context/ 매칭, references/ 스캔
  ▼
[requirements]
  │  product-owner Agent 호출
  │  ┌─→ PRD 초안 작성
  │  │   사용자에게 전문 표시 + 질문
  │  │   사용자 답변 수렴
  │  └─← 승인될 때까지 반복
  │  산출물: .dev/prd.md
  ▼
[design]
  │  architect Agent 호출
  │  ┌─→ 설계 초안 작성
  │  │   (중형/대형일 때) design-critic Agent로 비판 검토
  │  │   사용자에게 전문 표시 + 질문
  │  │   사용자 답변 수렴
  │  └─← 승인될 때까지 반복
  │  산출물: .dev/design.md
  ▼
[implement]
  │  구현 계획 제시 → 사용자 승인
  │  의존성 분석 → 배치 구성 (위상 정렬)
  │  배치별 coder Agent 호출 (병렬 가능)
  │  배치 간 빌드 검증
  │  qa-manager Agent로 자기점검 (1회)
  │  Critical 발견 시 coder로 자동 수정
  │  산출물: 구현된 코드, .dev/self-check.md
  ▼
[review]
  │  Mechanical Gate: 빌드 + 테스트 통과 확인
  │  qa-manager + security-auditor 병렬 호출
  │  결과 합산 → Critical/QUESTION 처리
  │  최대 2회 반복
  │  산출물: .dev/trust-ledger.md
  ▼
[complete]
  │  product-owner Agent로 인수 검증
  │  /gx-commit 스킬 호출 → 커밋
  │  /gx-pull-request 스킬 호출 → PR 생성
  │  도메인 status.md 갱신, context 환류 제안
  ▼
  완료
```

#### 산출물 게이트

Phase 진입 시 이전 Phase의 산출물 존재 여부를 확인합니다. 예를 들어, `--phase implement`로 구현만 실행하려 해도 `.dev/prd.md`가 없으면 requirements Phase부터 자동으로 시작합니다. 이를 통해 산출물 누락 없이 파이프라인의 일관성을 보장합니다.

---

### 3.3 Q&A 루프와 사용자 상호작용

requirements(PRD 작성)와 design(설계) Phase에서는 **사용자 승인까지 반복하는 Q&A 루프**가 동작합니다.

#### Q&A 루프의 흐름

```
┌──────────────────────────────────────────────────┐
│  1. 오케스트레이터가 Agent를 호출                     │
│     (PRD/설계 작성 + 질문 생성 지시)                  │
│                                                    │
│  2. Agent가 산출물 초안 + "확인이 필요한 사항"을 출력    │
│                                                    │
│  3. 오케스트레이터가 산출물 전문을 사용자에게 표시       │
│                                                    │
│  4. Agent의 질문을 AskUserQuestion으로 변환하여 제시   │
│     ┌───────────────────────────────────────┐      │
│     │ 유형: 선택 → 선택형 AskUserQuestion    │      │
│     │ 유형: 자유입력 → 자유입력형            │      │
│     │ 기술 용어 → 비기술적 표현으로 의역     │      │
│     └───────────────────────────────────────┘      │
│                                                    │
│  5. 사용자 답변을 수렴                              │
│                                                    │
│  6-A. 질문이 남아있으면 → 답변 반영하여 Agent 재호출   │
│       (1번으로 돌아감)                              │
│                                                    │
│  6-B. 질문이 없으면 → 승인/수정 확인                  │
│       ├─ 승인 → 다음 Phase로 진행                   │
│       └─ 수정 요청 → 수정 내용을 받아 Agent 재호출    │
│          (1번으로 돌아감)                            │
└──────────────────────────────────────────────────┘
```

#### Q&A 히스토리 관리

Agent 프롬프트 크기를 관리하기 위해, 이전 라운드의 질문+답변은 **핵심 결정 사항만 요약**하여 전달합니다:

```
Q: 세션 기반 vs JWT? → A: JWT 선택
Q: 토큰 만료 시간? → A: 30분
```

산출물(PRD, 설계서)은 최신 버전만 전달하고, 이전 버전은 전달하지 않습니다.

---

### 3.4 context/ -- 도메인 지식이 참조되는 과정

`context/` 디렉토리는 프로젝트의 도메인 지식(용어, 아키텍처, 관련 레포 매핑)을 관리합니다. `/gx-dev` 실행 시 에이전트가 이 지식을 자동으로 참조합니다.

#### 디렉토리 구조

```
context/
├── README.md              ← 도메인 목록 인덱스
├── glossary.md            ← 공통 용어 사전
├── 결제/
│   ├── README.md          ← 도메인 개요
│   ├── PROJECTS.md        ← 관련 레포 매핑
│   ├── glossary.md        ← 도메인 용어 사전
│   ├── architecture.md    ← 아키텍처 + 주제 문서 링크
│   └── status.md          ← 구현 추적 (✅/⬜)
└── 주문/
    └── ...
```

#### 참조 과정 (phase-setup Step 3.4)

```
1. git remote get-url origin 실행
   → 현재 레포명 추출 (예: "org/payment-service")

2. context/*/PROJECTS.md를 Grep
   → 현재 레포를 참조하는 도메인을 찾음
   예: context/결제/PROJECTS.md에 "payment-service"가 기재되어 있으면 매칭

3. 매칭된 도메인의 glossary.md, architecture.md를 Read
   → DOMAIN_CONTEXT 변수에 저장

4. 이후 모든 Agent 호출 시 "도메인 컨텍스트"로 프롬프트에 포함
```

- SVN 프로젝트에서는 `svn info --show-item repos-root-url`로 저장소 URL을 추출하고, URL의 마지막 세그먼트를 레포명으로 사용합니다.
- `context/` 디렉토리가 없거나 매칭되지 않으면 `DOMAIN_CONTEXT`는 빈 상태로 진행합니다. 이 경우 "도메인 컨텍스트가 없습니다. `/gx-context`로 도메인을 등록하면 이후 작업에서 용어/아키텍처를 참조할 수 있습니다." 안내가 표시됩니다.

#### 활용 예시

결제 도메인에서 `context/결제/glossary.md`에 "PG사 수수료"라는 용어가 정의되어 있으면, product-owner는 PRD에서 이 용어를 정확한 의미로 사용하고, architect는 설계 시 수수료 계산 로직의 위치를 아키텍처 문서에 맞게 배치합니다.

---

### 3.5 references/ -- 외부 규격이 참조되는 과정

`references/` 디렉토리는 프로젝트가 준수해야 할 외부 규격/표준(시큐어코딩 가이드, API 설계 표준, eGovFrame 규칙 등)을 관리합니다.

#### 참조 과정 (phase-setup Step 3.5)

```
1. references/ 디렉토리 존재 확인

2. 디렉토리 내 파일 목록 수집 (하위 디렉토리 포함)

3. 각 파일에서 한줄 설명 추출:
   ┌────────────────────────────────────────────────┐
   │ .md 파일  → 첫 번째 # 헤딩 텍스트              │
   │ .txt 파일 → 첫 번째 비공백 줄                  │
   │ 그 외     → 파일명 그대로 사용 (.pdf 등)       │
   └────────────────────────────────────────────────┘

4. 파일 목록 + 한줄 설명을 REFERENCES 변수에 저장
   예:
   | 파일 | 설명 |
   |------|------|
   | references/시큐어코딩-가이드.md | 시큐어코딩 가이드 v2.1 |
   | references/API-설계-표준.pdf | API-설계-표준.pdf |

5. 이후 4개 Agent의 프롬프트에 REFERENCES 테이블을 전달
```

#### Agent별 활용 방식

| Agent | REFERENCES 활용 |
|-------|----------------|
| architect (설계) | "아래 외부 규격/표준을 설계에 반영하라. 관련 규격이 있으면 Read하여 준수 여부를 확인하고, 설계서에 '준수 규격' 섹션을 추가하라." |
| coder (구현) | "아래 외부 규격/표준을 구현 시 준수하라. 필요 시 Read하여 상세 내용을 확인하라." |
| qa-manager (리뷰) | "아래 외부 규격/표준의 준수 여부를 검토하라. 위반 발견 시 CERTAIN으로 보고하라." |
| security-auditor (감사) | "아래 외부 규격/표준의 보안 관련 항목을 감사에 포함하라." |

각 Agent는 REFERENCES 테이블에서 관련 파일을 식별한 후, `Read` 도구로 해당 파일의 상세 내용을 직접 확인합니다.

#### 실제 시나리오 예시

시큐어코딩 가이드를 `references/`에 넣으면:
1. **설계 단계**: architect가 설계서에 "준수 규격" 섹션을 추가하고, 가이드의 관련 항목(예: SQL Injection 방지, 입력값 검증)을 설계에 반영합니다.
2. **구현 단계**: coder가 가이드를 Read하여 PreparedStatement 사용, 입력값 화이트리스트 검증 등을 준수하며 코딩합니다.
3. **리뷰 단계**: qa-manager가 가이드 위반 여부를 검토하고, 위반 시 CERTAIN(확실한 문제)으로 보고합니다.
4. **감사 단계**: security-auditor가 보안 관련 항목을 중점적으로 감사합니다.

`references/` 디렉토리가 없으면 `REFERENCES`는 빈 상태로 진행하며, Agent 프롬프트에 포함되지 않습니다. 별도의 안내 메시지도 출력하지 않습니다.

---

### 3.6 코드 맵

코드 맵은 현재 작업과 관련된 파일의 경로와 역할을 기록하는 누적 문서입니다. 모든 Agent에게 "이 기능과 관련된 코드가 어디에 있는지"를 알려주는 네비게이션 가이드 역할을 합니다.

#### 구조

```markdown
## 코드 맵: 결제 한도 변경

### 핵심 파일
- src/domain/PaymentLimit.kt:1 → 결제 한도 도메인 모델
- src/service/PaymentService.kt:45 → 결제 처리 서비스 (한도 검증 로직)

### 참조 파일
- src/repository/PaymentLimitRepository.kt:1 → 한도 조회 레포지토리
- src/controller/PaymentController.kt:30 → REST API 엔드포인트

### 설정
- src/main/resources/application.yml → 결제 관련 설정
```

#### 생성 (phase-setup Step 4)

1. ARGS[0](사용자 요청)에서 핵심 도메인 키워드를 추출합니다.
   - 예: "[JIRA-123] 결제 한도 변경" → `결제`, `한도` → `payment`, `limit`
2. 키워드로 프로젝트를 Grep하여 관련 파일을 수집합니다.
3. 발견된 파일의 상단(클래스 선언, 주요 메서드 시그니처)을 가볍게 Read하여 역할을 파악합니다.
4. 핵심/참조/설정으로 분류하여 초기 코드 맵을 작성합니다.

초기 코드 맵은 **최대 15개** 파일로 제한됩니다 (핵심 5, 참조 7, 설정 3 이내).

#### 누적

각 Agent(product-owner, architect, coder, qa-manager 등) 출력에 "탐색 추가 항목" 섹션이 있으면 해당 파일을 코드 맵에 추가합니다. Agent가 작업 중 발견한 새로운 관련 파일이 점진적으로 축적되는 구조입니다.

- 누적 코드 맵은 **최대 25개**로 제한됩니다. 초과 시 참조 파일부터 제거합니다.
- 갱신될 때마다 `.dev/codemap.md`에 저장합니다.

#### 전달

모든 Agent 호출 시 현재 코드 맵이 프롬프트에 포함됩니다. Agent는 코드 맵을 기반으로 관련 파일을 타겟팅하여 상세 분석을 수행합니다.

---

### 3.7 자기점검 vs 리뷰

`/gx-dev`에는 두 단계의 품질 검증이 있습니다. 목적과 깊이가 다릅니다.

| 구분 | 자기점검 (phase-implement) | 리뷰 (phase-review) |
|------|--------------------------|---------------------|
| **시점** | 구현 직후, 사용자 리뷰 전 | 자기점검 이후 |
| **목적** | 명백한 실수를 빠르게 잡기 | 스펙 충족 + 보안 감사 |
| **Agent** | qa-manager (단독) | qa-manager + security-auditor (병렬) |
| **입력** | diff + PRD의 "요구사항"/"수용 기준"만 | diff + PRD + 설계서 + REFERENCES |
| **반복** | 1회 패스, 루프 없음 | 최대 2회 반복 |
| **Critical 처리** | coder로 자동 수정 1회 시도 | coder로 자동 수정 + 재리뷰 |
| **QUESTION 처리** | 기록만, phase-review로 이월 | AskUserQuestion으로 사용자 확인 |
| **빌드/테스트 Gate** | 없음 | 있음 (Mechanical Gate) |
| **보안 감사** | 없음 | security-auditor 통합 감사 |

**흐름 요약**: 자기점검에서 명백한 실수(Critical)를 잡아 자동 수정한 후, 리뷰에서 스펙 충족과 보안까지 포괄적으로 검증합니다. 자기점검에서 발견된 Warning/Info는 리뷰에서 중복 보고되지 않도록 qa-manager에 전달됩니다.

**자기점검 건너뛰기 조건**: 총 변경이 10줄 미만이면서 변경된 파일이 설정 파일만으로 구성된 경우(`.yml`, `.json`, `.md` 등), 자기점검을 건너뛰고 phase-review로 직행합니다.

---

### 3.8 정체 감지 + 에스컬레이션

phase-implement(구현→자기점검)와 phase-review(QA→수정→재리뷰) 루프에서, 같은 문제가 반복되거나 진전이 없으면 오케스트레이터가 이를 감지하고 전담 Agent로 에스컬레이션합니다.

#### 감지 패턴

| 패턴 | 감지 기준 | 유형 |
|------|----------|------|
| SPINNING | 동일 에러 메시지가 2회 연속 반복 | 기계적 (텍스트 비교) |
| OSCILLATION | 접근법 A→B→A 왕복이 감지됨 | 정성적 (LLM 판단) |
| NO_DRIFT | 이전 반복과 비교해 코드 변경이 실질적으로 없음 | 반기계적 (diff stat) |
| DIMINISHING_RETURNS | 수정 범위가 줄어드는데 결과가 개선되지 않음 | 정성적 (LLM 판단) |

#### 에스컬레이션 경로

```
정체 감지
  │
  ├─ SPINNING (같은 에러 반복)
  │    1차: hacker Agent — 제약 우회 분석
  │    2차: researcher Agent — 근본 원인 분석
  │
  ├─ OSCILLATION (A→B→A 왕복)
  │    1차: architect Agent — 설계 재검토
  │    2차: 사용자에게 두 접근법 제시, 선택 요청
  │
  ├─ NO_DRIFT (변경 없음)
  │    1차: hacker Agent — 제약 식별 + 우회 경로
  │    2차: researcher Agent — 코드베이스 탐색
  │
  └─ DIMINISHING_RETURNS (개선 없음)
       1차: simplifier Agent — 복잡도 분석 + 범위 축소
       2차: 사용자에게 현재 상태 보고, 방향 전환 여부 확인
```

정체 감지 시 기존 반복 카운트를 소진하지 않고 에스컬레이션으로 전환합니다. `state.md`의 `execution-log`에 `stagnation: {패턴}` 필드가 기록됩니다.

---

## 4. 스킬 레퍼런스

### 4.1 `/gx-setup` -- 초기 설정

프로젝트에 플러그인을 처음 연결할 때 실행합니다. VCS 감지, 도구 설치, 인증, 알림을 순서대로 처리합니다.

| 항목 | 설명 |
|------|------|
| 인자 | 없음 |
| SVN | VCS 감지 + svn CLI 확인 + SVN 인증. gh CLI/PR 관련은 건너뜀 |

---

### 4.2 `/gx-context` -- 도메인 컨텍스트 관리

도메인 지식을 등록/갱신/동기화합니다. 상황에 따라 5가지 모드를 자동 선택합니다.

| 모드 | 조건 | 설명 |
|------|------|------|
| 스캔 | context/ 없음 | 코드베이스 분석 → context 초안 자동 생성 |
| 신규 | 도메인명 지정 | Q&A 기반 새 도메인 생성 |
| 문서 기반 | `--from` 지정 | 파일에서 context 생성/갱신 |
| 갱신 | 기존 도메인 존재 | Q&A 또는 파일 기반 갱신 |
| 동기화 | `--sync` 지정 | git 히스토리 분석 → status.md 갱신 |

**인자:**
- `{도메인명}` -- 대상 도메인
- `--from {파일경로}` -- 파일에서 context 생성
- `--sync` -- git 히스토리 기반 진행도 동기화

---

### 4.3 `/gx-dev` -- 전체 개발 사이클 (핵심)

PRD에서 PR까지 전체 개발 파이프라인을 에이전트 팀으로 실행합니다. 동작 원리의 상세는 [3. 핵심 개념](#3-핵심-개념-플러그인이-동작하는-방식)을 참고하세요.

#### 모드

| 모드 | 경로 | 용도 |
|------|------|------|
| normal | setup → requirements → design → implement → review → complete | 전체 파이프라인 |
| hotfix | setup → requirements(경량) → implement → complete | 긴급 버그 수정 |
| implement | setup → implement → complete | 설계 없이 바로 구현 |

#### Phase별 역할

| Phase | 주 Agent | 설명 |
|-------|----------|------|
| setup | (오케스트레이터) | 환경 준비, 브랜치 생성, 코드 맵 |
| requirements | product-owner | PRD 작성 (Q&A 루프) |
| design | architect + design-critic | 설계 (Q&A 루프) |
| implement | coder + qa-manager | 구현 + 자기점검 |
| review | qa-manager + security-auditor | 코드 리뷰 + 보안 감사 (병렬) |
| complete | product-owner | 인수 검증 → 커밋 → PR |

#### 인자/옵션 (자연어로 사용 가능)

| 자연어 표현 | 내부 동작 |
|-------------|-----------|
| "긴급", "핫픽스", "빨리 고쳐" | hotfix 모드 |
| "구현만", "설계 없이" | implement 모드 |
| "이어서", "계속", "재개" | 이전 작업 재개 |
| "어디까지", "상태", "현황" | 진행 상태 조회 |
| "PRD만", "설계만", "리뷰만" | 특정 Phase만 실행 |
| "{branch}에서", "{branch} 기반" | 베이스 브랜치 지정 |

#### .dev/ 산출물

각 기능 브랜치별로 `.dev/`에 산출물이 저장됩니다.

| 파일 | 내용 |
|------|------|
| prd.md | 요구사항 문서 |
| design.md | 설계 문서 |
| trust-ledger.md | 보안 감사 원장 |
| codemap.md | 관련 코드 맵 |
| state.md | 파이프라인 상태 (세션 전용) |
| diff.txt | 변경사항 diff (리뷰 입력용) |
| self-check.md | 자기점검 결과 |

---

### 4.4 `/gx-lens` -- 정책 탐지 + 영향도

코드에서 비즈니스 정책을 탐지하고, 변경 시 영향도를 PO/PD 친화적 보고서로 제공합니다. 읽기 전용이며 코드를 변경하지 않습니다.

**인자:**
- `{자연어 쿼리}` -- 탐지할 정책 설명 (필수)
- `--detail` -- 상세 모드 (더 많은 파일 탐색)
- `--idea "{아이디어}"` -- 보고서 후 영향도 분석 자동 실행

**흐름:** Prepare → Explore → Report → (Impact → Impact-Report)

**영향도 판정:**
- **바로 진행** -- 복잡도 낮고 리스크 없음
- **추가 검토 후 진행** -- 복잡도 중간 또는 일부 리스크
- **신중히 판단 필요** -- 복잡도 높거나 CRITICAL 리스크 존재

---

### 4.5 `/gx-commit` -- 커밋

변경사항을 분석하여 브랜치 타입 기반 한국어 커밋 메시지를 자동 생성합니다.

**동작:**
1. 빌드 실행 (프로젝트 타입에 따라)
2. 브랜치명에서 타입 파싱 (예: `feat/login` → `feat`)
3. diff 분석 → 커밋 메시지 자동 생성
4. 민감 파일 감지 시 경고
5. `{type}: 한국어 요약` 형식으로 커밋

**커밋 메시지 예시:**
```
feat: 결제 한도 변경 기능 추가

- 일일/월간 한도 설정 API 구현
- 한도 초과 시 거래 거부 로직 추가
- 관리자 한도 조회 화면 추가
```

**SVN:** 미지원. `svn commit`을 직접 실행하세요.

---

### 4.6 `/gx-pull-request` -- PR 생성

커밋 히스토리를 분석하여 PR 제목과 본문을 자동 생성합니다.

**인자:**
- `{베이스 브랜치}` -- 미지정 시 자동 감지 (main/master/develop)
- `--background {파일경로}` -- Background 섹션에 비즈니스 맥락 반영
- `--extra-section {파일경로}` -- 추가 섹션 삽입 (예: Trust Ledger)

**PR 본문 구조:**
- `## Background` -- 왜 이 변경이 필요한가
- `## Summary` -- 무엇을 했는가
- `## Changes` -- 구체적으로 무엇이 바뀌었는가 (기능 단위)
- `## Checklist` -- 확인 항목

**PR 제목 형식:** `[{TYPE}] 설명을 ~한다.`
- 예: `[FEATURE] 결제 한도 변경 기능을 구현한다.`

**SVN:** 미지원. PR 개념이 없으므로 리뷰어에게 직접 알려주세요.

---

### 4.7 `/gx-research` -- 리서치

웹 검색과 문서 분석을 병행하여 출처가 명확한 조사 결과를 산출합니다.

**인자:**
- `{주제}` -- 리서치 주제
- `--format report|comparison|summary` -- 결과물 형태
- `--output {경로}` -- 저장 경로 (기본: `.research/{주제}-{날짜}.md`)

**결과물 형태:**

| 형태 | 설명 |
|------|------|
| 종합 리포트 | 요약 → 주요 발견 → 상세 분석 → 출처 |
| 비교표 | 비교 기준 표 → 각 항목 요약 → 판단 근거 |
| 핵심 요약 | 한 줄 결론 → 핵심 포인트 3~5개 → 출처 |

---

### 4.8 `/gx-humanizer` -- AI 글쓰기 교정

AI가 생성한 텍스트의 흔적을 찾아내어 자연스러운 글로 교정합니다.

**모드:**
- **audit** -- 패턴 감지 리포트만 출력 (수정 안 함)
- **rewrite** -- 감지 후 직접 수정까지 수행

**감지 패턴:** 한국어 19개, 영어 19개, 공통 6개 = 총 44개

**심각도:**
- P1 -- 확실한 AI 흔적 (즉시 수정)
- P2 -- 의심스러운 패턴 (맥락 판단)
- P3 -- 스타일 개선 (선택적)

---

## 5. 설정 커스터마이징

### 브랜치 타입 추가

`.claude/config.json` → `conventions.branchTypes` 배열에 추가:

```json
"branchTypes": ["feat", "fix", "refactor", "chore", "docs", "test", "style", "perf", "ci", "release"]
```

### PR 타입 매핑 추가

```json
"prTitleMapping": {
  "feat": "FEATURE",
  "fix": "BUGFIX",
  "release": "RELEASE"
}
```

### 프로젝트 타입 추가

```json
"projectTypes": {
  "python": {
    "detect": ["requirements.txt", "pyproject.toml"],
    "build": "python -m pytest --co -q"
  }
}
```

### Google Chat 알림 연동

`/gx-setup`에서 설정하거나, config.json을 직접 수정:

```json
"notifications": {
  "googleChat": {
    "enabled": true,
    "webhookUrl": "https://chat.googleapis.com/v1/spaces/..."
  }
}
```

---

## 6. SVN 프로젝트

SVN 환경에서는 일부 기능이 제한됩니다.

| 스킬 | SVN 지원 | 비고 |
|------|:---:|------|
| `/gx-setup` | O | svn CLI 확인 + 인증 |
| `/gx-context` | O | svn info로 레포 감지 |
| `/gx-dev` | O (일부) | 커밋/PR 단계는 수동 |
| `/gx-lens` | O | 전체 지원 |
| `/gx-commit` | X | `svn commit` 직접 실행 |
| `/gx-pull-request` | X | PR 개념 없음 |
| `/gx-research` | O | 전체 지원 |
| `/gx-humanizer` | O | 전체 지원 |

---

## 7. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `gh CLI가 설치되어 있지 않습니다` | gh 미설치 | `/gx-setup` 실행 |
| `main 브랜치에서는 커밋할 수 없습니다` | pre-tool-guard 차단 | 작업 브랜치를 먼저 생성 |
| `SVN 프로젝트에서는 /gx-commit을 지원하지 않습니다` | SVN 환경 | `svn commit` 직접 실행 |
| `커밋할 변경사항이 없습니다` | 변경 없음 | 코드 수정 후 재시도 |
| `PR을 생성할 커밋이 없습니다` | 베이스 대비 커밋 없음 | 커밋 먼저 실행 |
| `detached HEAD 상태` | 브랜치 미체크아웃 | `git checkout {branch}` |
| `origin remote가 설정되어 있지 않습니다` | remote 미설정 | `git remote add origin {URL}` |
| 빌드 타임아웃 (5분) | 빌드가 너무 오래 걸림 | 빌드 단계 건너뜀 (자동) |
| `--hotfix와 --phase는 동시에 사용할 수 없습니다` | 플래그 충돌 | 하나만 사용 |
