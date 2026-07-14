# gx-dev 모드 개편 설계: normal / light 2모드 체계

- 작성일: 2026-07-14
- 상태: 확정 (구현 진행)
- 범위: gx-dev 전용. gx-tdd의 자체 hotfix 모드(RGR 유지)는 변경하지 않는다.

## 1. 배경

sef-plugin(사업부 공통, Pro~Max 전 계정)과 oh-my-gx(Max 전제)의 토큰 소모 구조를 비교 분석한 결과:

- gx-dev의 기존 3모드(전체/긴급 수정/구현만) 중 **구현만 모드는 기록 공백**(요구사항이 ARGS[0] 한 줄뿐, 사후 추적 불가)과 **게이트 공백**(review 생략으로 Mechanical Gate 미실행 — 테스트 증거 없이 커밋/PR 진입)이 있다.
- **긴급 수정(HOTFIX) 모드는 "긴급"인데 product-owner를 2회 왕복**(경량 PRD + 인수 검증)하는 모순이 있다. 속도가 최우선인 모드에서 가장 느린 에이전트 왕복 구조를 쓴다.
- "그냥 프롬프팅"과 차별화되는 파이프라인의 가치는 **기록(AC·변경 요약)과 게이트(테스트 실행 증거)**다. 이 둘을 유지하면서 에이전트 디스패치를 0~1회로 줄이는 경량 경로가 필요하다.
- Max 사용자에게는 "기록+게이트+속도", Pro 사용자에게는 토큰 절약까지 겸하는 하나의 모드로 두 요구를 커버한다.

## 2. 모드 체계 변경

### Before (3모드)

| 모드 | Phase | 디스패치 | 기록 | Gate |
|------|-------|---------|------|------|
| NORMAL | 6개 전부 | 6~7회 | PRD+설계서 | 있음 |
| HOTFIX | setup→requirements(경량)→implement→complete | 3회 (PO×2+coder) | 경량 PRD | **없음** |
| implement (구현만) | setup→implement→complete | 1~2회 | **없음** | **없음** |

### After (2모드 + 프리셋)

| 모드 | Phase | 디스패치 | 기록 | Gate |
|------|-------|---------|------|------|
| NORMAL | 6개 전부 (기존 그대로) | 6~7회 | PRD+설계서 | 있음 |
| LIGHT | setup→light→complete | **0~1회** | **ac.md + summary.md** | **필수** |
| LIGHT (긴급 프리셋) | 동일. AC 확인 질문 생략, AC를 재현 조건 형식으로 | 0~1회 | 동일 | 필수 |

- HOTFIX·구현만 모드는 **폐지**하고 LIGHT로 흡수한다.
- 긴급 프리셋은 별도 모드가 아니라 LIGHT의 변형이다 (`mode: light` + `preset: hotfix`).

## 3. LIGHT 경로 상세

```
setup(기존 재사용) → light(신설 phase) → complete(light 분기)
```

### phase-light 흐름

1. **Step 0 — AC 작성**: 오케스트레이터가 ARGS[0] + 코드 맵 + DOMAIN_CONTEXT를 기반으로 `${DEV_DIR}/ac.md`(초경량 PRD)를 직접 작성한다. 에이전트 디스패치 없음.
   - 형식: `## 배경`(2~3줄) + `## 요구사항 (AC)`(AC-1~AC-5, 검증 가능한 문장). gx-pull-request `--background` 계약("배경"+"요구사항" 섹션 파싱)과 호환되는 구조.
   - 긴급 프리셋: AC를 "재현 조건 → 원인 → 수정 방향" 관점으로 구성한다.
2. **Step 0.5 — AC 확인**: AskUserQuestion 1회 (승인/수정 요청). **긴급 프리셋이면 질문을 생략**하고 ac.md 기록 후 즉시 진행한다.
3. **Step 1 — 구현**: 규모 판정.
   - 예상 변경 파일 2개 이하이고 변경 방향이 명확 → **오케스트레이터 직접 구현** (디스패치 0회).
   - 그 외 → coder 1회 디스패치 (ac.md + 코드 맵 + REFERENCES).
4. **Step 2 — Mechanical Gate**: phase-review Step 0과 동일한 빌드/테스트 명령 결정 로직으로 build + test를 실행한다. **0 failures 없이는 complete 진입 불가.** 실패 시 수정 1회 시도 후 재실행, 재실패 시 AskUserQuestion(계속/중단). 긴급 프리셋도 Gate는 동일하게 필수.
5. **Step 3 — 기록**: `${DEV_DIR}/summary.md` 작성 (변경 파일 표 + 무엇을 왜 + Gate 실행 증거 1줄). Diff 수집 규칙에 따라 `DIFF_FILE` 갱신.

### phase-complete의 light 분기

- **인수 검증**: product-owner 디스패치 대신 **AC 자가 검증** — ac.md의 AC별로 구현·Gate 결과를 대조한 체크리스트를 표시하고, 미충족이 있으면 AskUserQuestion(수정/진행).
- **PR args**: `--background ${DEV_DIR}/ac.md --extra-section ${DEV_DIR}/summary.md`.
- **status.md 갱신**: 경로 B(커밋 기반) — light AC는 경량이므로 커밋 단위 추적이 적합 (기존 HOTFIX와 동일 근거).
- **context 환류**: 입력 소스 = diff + ac.md.

## 4. 의도 파싱 변경

| 감지 | Before | After |
|------|--------|-------|
| `긴급`, `핫픽스`, `급한`, `빨리 고쳐`, `버그 수정만` | HOTFIX | **LIGHT + 긴급 프리셋** |
| `구현만` | `--phase implement` 매핑 | **LIGHT** |
| `라이트`, `가볍게` | (없음) | LIGHT (신설) |
| AskUserQuestion 선택지 | 전체/긴급 수정/구현만 3택 | **전체 파이프라인/라이트 2택** |

- "구현만" 재매핑 근거: 기존에는 자연어 "구현만"이 `--phase implement`(설계서 필수, 없으면 중단)로, 모드 선택지 "구현만"이 경량 구현 모드로 — **같은 단어가 두 의미**로 쓰였다. 자연어 "구현만 해줘"의 실제 의도는 "절차 없이 빠르게"이므로 LIGHT로 통일한다. 설계서 기반 구현 phase 단독 실행은 `--phase implement` 플래그 전용으로 남는다.
- state.md 기록: `mode: normal | light`, 긴급 프리셋이면 `preset: hotfix` 추가. `intent-source`는 기존 유지.

## 5. 하위 호환

| 기존 | 신규 동작 |
|------|----------|
| `--hotfix` 플래그 | LIGHT + 긴급 프리셋으로 실행. 안내 1줄 출력 ("라이트 모드(긴급 프리셋)로 실행합니다") |
| `--light` 플래그 (신설) | LIGHT |
| `--phase implement` | 기존 그대로 (phase 단독 실행 — 설계서 필요) |
| 진행 중 레거시 세션 재개 (`mode: hotfix\|implement`) | 남은 Phase를 LIGHT 경로로 매핑해 진행. requirements가 이미 완료된 hotfix 세션은 prd.md를 ac.md 대용으로 사용 (재작성하지 않음) |
| 플래그 충돌 규칙 | `--light`·`--hotfix`는 `--phase`·`--resume`과 동시 사용 불가 (기존 --hotfix 규칙 승계) |

## 6. gx-tdd 범위 제외

- gx-tdd의 hotfix 모드는 **RGR·verify를 유지하는 별개 설계**이므로 변경하지 않는다 (Iron Law 충돌 없음).
- gx-tdd SKILL.md와 guide.md의 "gx-dev의 구현만 모드" 교차 참조 문구만 "라이트 모드"로 갱신한다.
- LIGHT에는 PRD가 없으므로 ralph 무인 루프 전환 대상이 아니다 (gx-ralph 진입 게이트의 PRD 필수 조건이 자연 차단). phase-light에는 ralph 전환 질문을 두지 않는다.

## 7. 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `.claude/skills/gx-dev/SKILL.md` | 의도 파싱·선택지·Phase 목록·스킵 금지 문구·Context Slicing·플래그 충돌 개편 |
| `.claude/skills/gx-dev/phases/phase-light.md` | 신설 |
| `.claude/skills/gx-dev/phases/phase-implement.md` | Hotfix/경량 구현 분기 삭제, ralph 질문 생략 조건 정리, --resume 모드 분기 정리 |
| `.claude/skills/gx-dev/phases/phase-requirements.md` | hotfix 경량 PRD 분기 삭제 |
| `.claude/skills/gx-dev/phases/phase-setup.md` | 레거시 mode 재개 마이그레이션 규칙 추가 |
| `.claude/skills/gx-dev/phases/phase-complete.md` | 인수 검증 light 분기(AC 자가 검증), status.md 분기 규칙, 환류 표, PR args |
| `.claude/skills/gx-tdd/SKILL.md` | gx-dev 교차 참조 문구 갱신 (108행 부근) |
| `docs/guide.md`, `README.md`, `index.html`, `docs/prompt-examples.md` | 모드 표·예시 갱신 |
| `tests/golden-scenarios.md` | light 라우팅·Gate 필수 시나리오 추가 |
| `scripts/lint-consistency.sh` | 모드 불변식 갱신 (아래 §8) |
| `context/glossary.md` | LIGHT 모드 용어 등록 |
| `.claude-plugin/plugin.json`, `marketplace.json`, `CHANGELOG.md` | v1.16.0 |

## 8. 기계 검증 (lint 불변식)

1. gx-dev SKILL.md에 HOTFIX 모드·"구현만" 선택지가 잔존하지 않는다 (레거시 호환 매핑 문구는 예외).
2. phase-light.md에 Mechanical Gate 실행 지시가 존재한다 (light의 게이트 공백 회귀 방지).
3. gx-dev SKILL.md의 `--hotfix` 레거시 매핑 문구와 phase-setup의 레거시 재개 규칙이 존재한다.
4. SKILL.md 모드 값(`normal | light`)과 phase-complete 분기가 일치한다.

## 9. 토큰 효과 (추정)

- 소형 작업 기준 에이전트 디스패치 3회(HOTFIX) 또는 1~2회(구현만) → **0~1회**.
- product-owner 프롬프트(정의 333줄) 왕복 2회 제거.
- 기록(ac.md/summary.md)과 게이트는 오케스트레이터 직접 수행이라 추가 디스패치 비용 없음.
