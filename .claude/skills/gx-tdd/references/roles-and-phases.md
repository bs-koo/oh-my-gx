# 역할과 Phase 계약

gx-tdd/SKILL.md에서 실행 목록을 정하기 전에 읽는다. 이 파일의 Phase 파일 경로는 ../phases/ 기준이다. 모델·도구는 현재 하네스 정책과 스키마로 해석한다.

## Agent 팀 (총 15종)

### PRODUCT
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| product-owner | PRD 작성 + 인수 검증 | "뭘 만들지" / "비즈니스 의도대로 됐나" | sonnet |

### PLANNING
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| architect | 설계 | "어떻게 만들지" / "구조적 일관성" | opus |
| **test-architect** | **testability 평가 (신규)** | **"어떻게 테스트할 수 있나"** | **opus** |

### REVIEW
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| design-critic | 설계 비판 검토 | "이 가정이 맞나" / "더 단순하게 안 되나" | opus |
| **reviewer** | **spec Part 1 + quality Part 2 통합. phase-implement 2-V 태스크 범위 모드는 sonnet** | **"스펙대로인가 → 잘 짜였나" — Part 1 verdict 선행** | **opus** |
| security-auditor | 정책/보안/허점 감사 | "뭘 놓쳤나" | sonnet |
| ~~qa-manager~~ | (deprecated — spec-reviewer·quality-reviewer로 분해 후 reviewer로 통합) | — | — |

### EXECUTION (RED 디스패치 → IMPLEMENT 세션 직접; `--isolated`·fix 4~5는 implementer)
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| **red-writer** | **실패 테스트 작성 전담 (신규)** | **"테스트만 작성" — 프로덕션 코드 안 봄** | **sonnet** |
| **implementer** | **GREEN+REFACTOR 통합 — `--isolated`·fix 라운드 4~5 격상에서 디스패치. 기본 경로는 세션이 같은 계약으로 직접 수행** | **"최소 통과 후 안전한 정리" — 테스트 수정 금지, focused만 실행** | **sonnet** |
| green-coder / refactor-coder / ~~coder~~ | (파이프라인 미호출 — 단독 스킬 전용; coder deprecated → red-writer/implementer로 재편) | — | sonnet |

### VERIFICATION
완료 검증은 **에이전트가 아니라 `oh-my-gx:gx-verify` 스킬**이 담당한다. phase-complete의 Step -1에서 `Skill("oh-my-gx:gx-verify")`로 호출되어 테스트/빌드를 직접 실행하고 0 failures를 확인한다.

### ANALYSIS
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| researcher | 코드베이스 조사 + 기술 비교 | "이해한다" (독립 호출 전용) | sonnet |

### RECOVERY (정체 시)
| Agent | 역할 | 관점 | 모델 |
|-------|------|------|------|
| hacker | 제약 우회 + 정체 탈출 | "다른 길이 있다" (정체 감지 시 호출) | sonnet |
| simplifier | 복잡도 제거 + 범위 축소 | "더 작게 만들자" (정체 감지 시 호출) | sonnet |

### 모델 라우팅 원칙

- 비판적 분석 / 구조적 설계 / 코드 품질 리뷰 / testability 평가: **opus** — 추론 깊이 우선
- PRD 작성 / spec 리뷰 / RED-GREEN-REFACTOR 구현 / 보안 감사 / 정체 탈출: **sonnet** — 비용 효율 우선
- verify 게이트: **`oh-my-gx:gx-verify` 스킬**이 담당 (별도 에이전트 아님). 테스트/빌드 직접 실행 + 0 failures 확인
- Mechanical Gate 결과 판단: 오케스트레이터가 직접 수행 — 에이전트 불필요
- 위 원칙과 Agent 팀 표의 모델은 **표준 프로파일(standard)** 기준이다. 에코 모드(eco)에서는 architect를 제외한 opus 에이전트가 sonnet으로 하향된다 — 공유 규칙 "모델 프로파일" 참조.
- **최소 강도 + 실패 시 격상**: 각 역할을 감당하는 가장 약한 모델을 쓰되(sonnet이 바닥 — haiku 강등 금지), 격상은 fix loop 라운드 4~5에서만 수행한다.

## Phase 개요 (TDD 강제)

| Phase | 파일 | 주 Agent | TDD 강제 사항 | Q&A Loop |
|-------|------|----------|--------------|----------|
| setup | phase-setup.md | (inline) | — | No |
| requirements | phase-requirements.md | product-owner (핵심 모드는 inline — AC·코드 확인·plan 결합 승인) | **AC = Given-When-Then 강제** (G-W-T 게이트 — 오케스트레이터 직접 검증) | Yes (max 1) |
| design | phase-design.md | architect + design-critic + **test-architect** | **testability score ≥ 7 필수** (미충족 시 재설계) | Yes (max 2) |
| implement | phase-implement.md | **red-writer(디스패치) → 세션 IMPLEMENT (`--isolated`: implementer) → 조건부 태스크 리뷰(reviewer)** | **Iron Law 1**: 실패 테스트 없이 코드 작성 금지 | RGR 사이클 |
| review | phase-review.md | **reviewer (spec+quality 통합 1석)** + security-auditor (병렬) | **Iron Law**: Part 1(spec) verdict 확정 전 Part 2 판정 금지 | Yes (max 2) |
| complete | phase-complete.md | **gx-verify(스킬)** → product-owner (인수) → commit/PR | **Iron Law 3**: verify 게이트 통과 필수 (테스트 실행 증거) | 인수 재시도 (max 1) |

**개발 실행의 필수 계약**:
- requirements/design에 **사전 게이트** (G-W-T, testability)
- implement는 **RED 격리 디스패치 + 세션 IMPLEMENT** (red-writer만 기존 코드 격리. `--isolated`로 implementer 디스패치 복원)
- review는 **reviewer 1석의 Part 1(spec) → Part 2(quality) 내부 순서 강제** (spec verdict 선행) + security 병렬
- complete는 **gx-verify 스킬 우선 호출** (verify 통과 없이 commit 진입 금지)

### 핵심 모드 경로 (core)

소형 변경용 경량 경로. 오케스트레이터가 AC와 실제 코드에 근거한 계획을 작성하고 **AC·계획 결합 승인 + RGR 사이클 + verify 게이트 + G-W-T 게이트 + 긴급 보안 감사 + AC 자가 검증을 실행**한다. 절차·승인·전환 정본은 [core-planning.md](core-planning.md)다:
```
core: setup → requirements (AC + G-W-T → 코드 Read·plan → 결합 승인·방법 선택) → implement (RGR + H1~H4 긴급감사) → complete (verify + AC 자가 검증)
all:  setup → requirements → design → implement (RGR) → review (spec+quality 통합 1석 + security 병렬) → complete (verify + 인수 + 요청한 종료점)
```
- **requirements (core 분기)**: 오케스트레이터가 `${DEV_DIR}/ac.md`(배경 + 요구사항: G-W-T 형식 AC)를 직접 작성한다 — product-owner 디스패치 없음. **G-W-T 검증 게이트는 동일하게 통과 필수** (RGR의 입력 계약이므로). 실제 코드를 확인해 `${DEV_DIR}/plan.md`를 작성하고 AC와 함께 승인받는다. 실행방법도 이 승인에 연결하며 유효한 같은 run·지문의 선택을 반복하지 않는다. 계획만 요청한 경우는 읽기 전용·explore 범위를 유지한다.
- **design**: 핵심 경로는 정식 설계·testability 평가를 생략하고 승인된 AC·plan·코드 맵을 사용한다. 중요한 구조·인터페이스 판단은 전체 모드 전환의 실제 결정 후 정식 설계로 해소한다.
- **implement**: design.md 대신 결합 승인된 ac.md·plan.md를 검사하고 전체 모드와 동일한 RGR을 수행한다. red-writer에는 계획의 파일·순서·인터페이스·검증과 AC를 전달하되 프로덕션 본문은 전달하지 않는다. 재계획은 [core-replanning.md](core-replanning.md)에 따라 기존 GREEN을 유지하며 새 케이스만 RED로 검증한다. 사이클 종료 후 H1~H4 (긴급 보안 감사: CRITICAL/HIGH만) 실행.
- **review**: 건너뛴다 (긴급 보안 감사가 H1~H4에서 대체).
- **complete**: verify 게이트 → **AC 자가 검증**(오케스트레이터가 ac.md의 AC별 충족을 체크리스트로 판정 — product-owner 디스패치 없음. verify가 테스트 증거를 이미 강제한다) → 사용자가 요청한 경우만 commit → PR. 기본 stop-at는 verify다.
- 긴급 버그 수정 요청("긴급/핫픽스" 키워드)도 이 경로다 — AC를 재현 조건 관점의 G-W-T로 작성한다.

**Iron Law 유지 (core여도)**:
- Iron Law 1 (실패 테스트 우선): RGR 사이클이 core에서도 강제됨
- Iron Law 3 (verify 게이트): complete의 Step -1에서 강제됨
- 우회 가능한 것은 design Phase (testability 평가)와 정식 review뿐
