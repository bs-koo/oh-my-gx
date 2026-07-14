# gx-dev·gx-tdd 모델 프로파일 설계: 표준(standard) / 에코(eco) 2프로파일 체계

- 작성일: 2026-07-14
- 상태: 확정 (v1.17.0 구현)
- 범위: gx-dev + gx-tdd (대화형 파이프라인). 선행 설계: `2026-07-14-gx-light-mode-design.md` §11.3 (본 spec은 그 예약을 구체화한다)
- 관련 레포: oh-my-gx

## 1. 배경

- 절차 축 개편(전체/핵심 모드, v1.16.0)으로 에이전트 디스패치 **횟수**는 줄었지만, 전체 모드의 디스패치 **단가**는 여전히 opus 중심이다. Pro 요금제 사용자가 전체 모드를 타면 토큰 한도를 빠르게 소진한다.
- 요구: **절차는 그대로 두고 모델만 낮추는** 선택지 — Pro 사용자도 PRD→설계→구현→리뷰→PR 전 과정을 사용하되, 에이전트를 sonnet 중심으로 운용한다.
- 품질 방어 논리: 파이프라인의 가치는 기록과 게이트이며, 게이트(빌드·테스트·verify·G-W-T·Mechanical Gate)는 **모델 무관 기계 검증**이다. 모델을 낮춰도 품질 바닥은 게이트가 유지한다 (light-mode 설계 §1 철학의 연장).

## 2. 2축 직교 모델

| 축 | 질문 | 값 | 결정 시점 |
|----|------|----|----------|
| 절차 축 (`mode`) | 어떤 phase·게이트를 도는가 | `all`(전체 모드) / `core`(핵심 모드) | 매 실행 (의도 파싱/질문) |
| 모델 축 (`model-profile`) | 에이전트를 어떤 모델로 돌리는가 | `standard`(표준) / `eco`(에코 모드) | 프로젝트 1회 설정 + 실행별 오버라이드 |

- 두 축은 **직교**한다 — 4조합(전체×표준, 전체×에코, 핵심×표준, 핵심×에코) 모두 유효. Pro 사용자의 주 사용처는 전체×에코.
- 모드 확인 질문(의도 파싱 Step 3)이 제시될 때는 모델 프로파일 질문을 **같은 AskUserQuestion 호출의 두 번째 질문**으로 함께 묻는다 — 한 번의 submit으로 두 축이 동시 결정된다 (dev·tdd 동일). 플래그·자연어로 이미 확정됐으면 프로파일 질문은 생략하고, 모드가 자동 판정되어 질문 자체가 없으면(긴급·구현만 등) config > 기본값으로 조용히 결정한다 — 프로파일만을 위한 추가 인터럽트는 만들지 않는다.
- 한국어 정식 명칭: **표준 / 에코 모드(eco)**. 기계층은 영어 키 (2층 네이밍 규약 — light-mode 설계 §11.2와 동일).

## 3. MODEL_PROFILE 결정 규칙

phase-setup에서 결정하여 공유 변수 `MODEL_PROFILE`로 이후 모든 Phase에서 사용한다.

우선순위 (높은 것 우선):
1. **플래그**: `--eco` → `eco`, `--standard` → `standard` (config가 eco여도 이번 실행만 표준으로)
2. **자연어**: ARGS[0]에 `에코`, `절약 모드` 포함 → `eco` (모드 판정과 독립 — BASE 추출처럼 직교 처리)
3. **질문 답변**: 의도 파싱 Step 3의 모드 확인 질문에 프로파일 질문이 함께 제시된 경우 그 답변 — config 값이 있으면 해당 옵션을 `(현재 설정)`으로 첫 번째 배치
4. **config.json**: `"modelProfile"` 값 (`"eco"` / `"standard"`)
5. **기본값**: `standard` (config 미설정·빈 값 포함)

- state.md에 `model-profile: standard | eco`를 기록한다. `--resume` 시 state.md 값을 복원한다 (재개 중 프로파일 변경은 지원하지 않음 — `--eco`/`--standard`는 `--resume`과 동시 사용 불가).
- `--eco`와 `--standard`는 동시 사용 불가.
- `--status` 출력에 프로파일을 표시한다.

## 4. 디스패치 오버라이드 (구현 메커니즘)

- **Task 호출의 `model` 파라미터**가 에이전트 정의(frontmatter `model:`)보다 우선하는 것을 이용한다. `agents/*.md`는 무수정 — frontmatter가 표준 프로파일의 SSOT로 유지된다.
- 규칙: `MODEL_PROFILE == eco`이면, opus 에이전트 중 **architect를 제외한** 것들을 `model: "sonnet"`으로 오버라이드하여 디스패치한다. 이미 sonnet인 에이전트는 그대로 (haiku 강등은 하지 않는다 — 절약 폭 대비 산출물 손실이 큼).
- **architect 유지 원칙**: 게이트가 방어하지 못하는 산출물(설계서)의 생산자만 opus를 유지한다. 설계 오류는 빌드·테스트가 잡지 못하고 구현·리뷰·수정 전체로 전파되는 가장 비싼 실패인 반면, 호출은 1~2회로 가장 적어 유지 비용이 작다. 반대로 coder는 테스트·Mechanical Gate·리뷰·인수 4겹이 방어하므로 하향하고(토큰 지배 항 — 절약 효과 최대), 검증자 3종(design-critic·test-architect·quality-reviewer)의 실패 모드는 '놓침'으로 eco 사용자가 수용하는 트레이드오프다.

| 파이프라인 | 에이전트 | 표준 | 에코 |
|-----------|---------|------|------|
| 공통 | **architect** | opus | **opus (유지)** |
| gx-dev | design-critic, coder | opus | **sonnet** |
| gx-tdd | design-critic, test-architect, quality-reviewer | opus | **sonnet** |
| 공통 | product-owner, spec-reviewer, security-auditor, red/green/refactor-coder, researcher, hacker, simplifier | sonnet | sonnet (무변경) |

- 이 규칙은 SKILL.md **공유 규칙**에 1곳으로 정의한다 — phase 파일의 개별 `Task(...)` 표기는 수정하지 않는다 (규칙이 모든 디스패치에 적용됨을 명시).
- **폴백**: 구버전 Claude Code에서 Task의 model 파라미터가 무시되는 경우가 확인되면, opus 에이전트의 `-eco` 복제본(frontmatter `model: sonnet`)을 만들어 디스패치 이름을 스위칭하는 방식으로 전환한다 (v1.17.x 패치 범위).

## 5. 설정·온보딩

- `.claude/config.json`에 `"modelProfile": ""` 필드 신설 — 빈 값은 `standard` 취급 (기존 `vcs` 필드 관례와 동일).
- `gx-setup`에 **5단계(모델 프로파일)** 신설: config 값이 비어있으면 AskUserQuestion(표준/에코) 1회 → config.json 기록. 이미 설정되어 있으면 유지 출력 후 건너뜀.
- 안내 문구에 명시: 오케스트레이터 본체(메인 세션)의 모델은 플러그인이 제어할 수 없다 — Pro 사용자는 세션 모델도 Sonnet 사용을 권장.

## 6. 범위와 비범위

- **v1.17.0 범위**: gx-dev·gx-tdd 대화형 파이프라인의 에이전트 디스패치.
- **비범위 (후속)**:
  - `gx-ralph-iterate` (무인 루프): state.md의 `model-profile`을 읽어 coder 디스패치에 적용 — 후속 릴리스에서 러너 테스트와 함께 반영.
  - `gx-cross-review`, `gx-humanizer`, `gx-lens` 등 단발 스킬: 각자의 에이전트 구성이 달라 별도 검토.
  - 리뷰 반복 한도 조정(에코 시 +1) 등 프로파일별 절차 보정: 실사용 데이터 확인 전에는 도입하지 않는다 (YAGNI).

## 7. 토큰 효과 (추정)

- 전체 모드 기준 opus 디스패치 3~4회(설계·비판·구현·품질 리뷰)가 sonnet으로 하향 — opus 대비 sonnet 단가 차이를 고려하면 에이전트 비용의 지배 항이 크게 감소한다.
- 핵심 모드×에코: 디스패치 0~1회 × sonnet — 최대 절약 조합.

## 8. 기계 검증

- 린트 **[14/14] 모델 프로파일 계약** 신설:
  - config.json에 `modelProfile` 키 존재
  - gx-dev·gx-tdd SKILL.md에 `model-profile: standard | eco` 기록 규칙 존재
  - 양쪽 SKILL.md에 에코 오버라이드 규칙(`model: "sonnet"` 오버라이드 문구) 존재
  - 양쪽 phase-setup에 MODEL_PROFILE 결정 로직 존재
  - gx-setup에 모델 프로파일 단계 존재
- 골든 시나리오:
  - **S15**: `/gx-dev --eco {기능}` → 전체 모드 진행 시 architect·design-critic·coder 디스패치에 `model: "sonnet"` 오버라이드 관찰 (sonnet 에이전트는 무변경). state.md `model-profile: eco`.
  - **S16**: config `modelProfile: "eco"` + 플래그 없음 → eco 적용. 같은 조건에서 `--standard` 지정 → 이번 실행만 표준. `--eco --standard` 동시 지정 → 충돌 에러.
