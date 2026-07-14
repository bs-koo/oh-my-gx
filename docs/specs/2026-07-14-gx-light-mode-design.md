# gx-dev·gx-tdd 모드 개편 설계: 2모드 체계 (v1 full/light → v3 all/core)

- 작성일: 2026-07-14 (v3 — 같은 날 개정: all/core 개명·한국어 정식 명칭·모델 프로파일 축 예약)
- 상태: 확정 (구현 완료)
- 범위: gx-dev + gx-tdd. §1~§9는 v1(gx-dev light 도입) 설계, §10이 v2 확장, §11이 v3 개정이다. v1의 "normal"·"긴급 프리셋"·"gx-tdd 제외" 결정은 §10에서, v2의 "full/light" 명칭은 §11에서 개정되었다.

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

## 10. v2 확장 (같은 날 개정)

### 10.1 normal → full 개명

- `mode: full | light`로 명명 대칭화. normal은 "light가 비정상"으로 읽히는 어감 문제.
- 내부 값 변경이므로 재개 마이그레이션 추가: `mode: normal` 발견 시 `full`로 조용히 갱신 (동작 동일).

### 10.2 긴급 프리셋 폐지

- v1의 프리셋은 실제 차이가 "AC 확인 질문 1회 생략"뿐 — 별도 개념(preset 필드·문서 행·시나리오)을 유지할 가치가 없다.
- 긴급일수록 원인 오판 위험이 커서 AC 확인 1회는 긴급에서 오히려 가치가 있다 (구 HOTFIX의 진짜 문제는 질문이 아니라 PO 왕복 2회였고, 그것은 이미 제거됨).
- "긴급/핫픽스" 키워드는 LIGHT로 라우팅하되 AC를 재현 조건 관점으로 작성하는 **작성 가이드**로만 남긴다. `--hotfix` 레거시 플래그는 LIGHT 매핑 유지.

### 10.3 gx-tdd full/light 재편 (v1 §6 개정)

v1은 gx-tdd를 범위에서 제외했으나, "light = 각 파이프라인의 필수 게이트는 유지하는 경량 경로"로 의미를 정의하면 tdd에도 일관 적용 가능하다:

| | gx-dev light | gx-tdd light |
|---|---|---|
| AC 작성 | 오케스트레이터 직접 (ac.md) | 동일 — 단 **G-W-T 형식 강제 + G-W-T 검증 게이트 통과 필수** |
| 구현 | 직접 or coder 1회 | **RGR 사이클 유지** (Iron Law 1 불변) |
| 게이트 | Mechanical Gate (빌드+테스트) | 기준선 게이트 + verify 게이트 + H1~H4 긴급 보안 감사 |
| 인수 | AC 자가 검증 | AC 자가 검증 (verify가 테스트 증거를 이미 강제) |
| Phase 구성 | setup → light → complete | setup → requirements(light 분기) → implement(RGR) → complete |

- 구 HOTFIX 대비 변화: product-owner 왕복 2회(경량 PRD + 인수) 제거. G-W-T 품질은 **G-W-T 검증 게이트를 오케스트레이터 작성물에 동일 적용**하는 것으로 방어 — v1 §6의 "PO 왕복은 정당한 비용" 평가를 개정한 근거.
- Trust Ledger 섹션명 `### Hotfix 긴급 감사` → `### Light 긴급 감사` (phase-complete가 레거시 산출물의 구 섹션명도 인식).
- 자연어 "구현만"은 tdd에서도 LIGHT로 라우팅 (gx-dev와 정렬. phase 단독 실행은 --phase implement 플래그 전용).
- gx-ralph 무영향: light에는 prd.md가 없어 ralph 진입 게이트(PRD 필수)가 자연 차단. origin·러너·훅은 mode 필드를 읽지 않음.

### 10.4 기계 검증 (v2 추가분)

- 린트 [12/13] 갱신: mode 값 `full | light`, --hotfix 매핑 문구 갱신.
- 린트 [13/13] 신설: tdd light 계약 — RGR 유지 문구·G-W-T 게이트 유지·긴급 감사 섹션·AC 자가 검증 분기·레거시 매핑·폐지 모드 잔존 금지.
- 골든 시나리오 S12 재정의(긴급도 질문 1회), S13 확장(normal→full, dev·tdd 공통), S14 신설(tdd light: RGR 유지 + PO 미디스패치).

## 11. v3 개정 (같은 날 — 모드 명칭 확정 + 모델 프로파일 축 예약)

### 11.1 full/light → all/core 개명

- 배경: 에이전트 디스패치 모델을 낮춰 토큰 소비를 줄이는 **모델 프로파일 축**을 v1.17.0에 도입하기로 결정. 그 축의 유력 후보명 lite가 light와 발음·철자 충돌(1자 차이, 의미 상이)하므로, 미릴리스 상태인 지금 절차 축을 all/core로 개명해 충돌을 원천 해소한다.
- core 선정 근거: "핵심(기록+게이트)만 유지하는 경량 경로"라는 §1의 설계 철학("파이프라인의 가치는 기록과 게이트다")과 정확히 일치.
- 내부 키: `mode: all | core`. 플래그 `--core` (미릴리스였던 `--light`는 별칭 없이 제거, `--hotfix`→core 레거시 매핑은 유지).
- 마이그레이션 확장: `normal`/`full`→`all`, `light`→`core` 조용히 갱신(v1.16 개발 중 세션 보호 — dev는 `phases`/`steps`의 `light` 키도 `core`로 갱신), `hotfix`/`implement`→`core` 안내 후 재개.
- 파일: gx-dev `phase-light.md` → `phase-core.md`. Trust Ledger 섹션명 `### 핵심 모드 긴급 감사` (레거시 `### Light 긴급 감사`·`### Hotfix 긴급 감사` 인식 유지).

### 11.2 한국어 정식 명칭 (2층 네이밍)

- 이 플러그인은 응답·커밋·문서가 한국어 우선이므로, **사용자 노출층은 한국어가 정식 명칭**이다: **전체 모드(all) / 핵심 모드(core)**. AskUserQuestion 라벨은 "전체 과정 진행" / "핵심 과정만 진행".
- **기계층(state.md 값·플래그·린트 문자열)은 영어 키를 유지**한다 — 근거: (1) `--직행` 류 한국어 플래그는 IME 전환이 필요해 CLI 타이핑이 불편, (2) 한국어는 동의 표기가 많아(직행/다이렉트 등) 내부 키로 쓰면 파싱·마이그레이션·린트가 표기 변형에 취약, (3) `--hotfix` 등 기존 레거시 매핑 체계가 영어라 연속성 유지.
- 자연어 라우팅 키워드에 `핵심만` 추가. 기존 `라이트`/`가볍게`는 하위호환 키워드로 유지한다 (키워드 ≠ 모드명).
- 문서 표기 규약: 첫 등장은 "핵심 모드(core)" 형식으로 병기, 이후 "핵심 모드". 의사코드·표의 키 값은 all/core.

### 11.3 모델 프로파일 축 예약 (v1.17.0)

절차 축(mode)과 **직교**하는 모델 축을 신설 예정: **표준(standard) / 에코 모드(eco)**.

- 목적: Pro 요금제 사용자가 **전체 모드를 저비용으로** 사용 — 절차는 그대로, 에이전트 디스패치 모델만 opus 중심→sonnet 중심으로 하향. 2축 직교이므로 4조합(전체×표준, 전체×에코, 핵심×표준, 핵심×에코) 모두 유효하다.
- 설계 방향 (상세는 v1.17.0 별도 spec):
  - `config.json`에 `modelProfile: standard | eco` 1회 설정(gx-setup에서 질문) + `--eco` 플래그로 세션 오버라이드 + state.md `model-profile` 기록. ~~파이프라인 진입 질문은 절차 2택 유지~~ → 구현 시 개정: 모드 확인 질문이 뜰 때 프로파일 질문을 같은 호출에 함께 제시한다 (상세는 `2026-07-14-gx-eco-profile-design.md` §2·§3).
  - 구현은 Task 디스패치의 model 파라미터 오버라이드(frontmatter보다 우선)로 — `agents/*.md` 무수정. 하향 대상은 dev·tdd의 opus 5종(architect, design-critic, coder, quality-reviewer, test-architect).
  - 품질 방어: 게이트(빌드·테스트·verify·G-W-T·Mechanical Gate)는 모델 무관 기계 검증이므로 에코에서도 품질 바닥이 유지된다 (§1 철학의 연장).
  - 한계: 오케스트레이터 본체 모델은 사용자 세션 설정이라 플러그인이 제어 불가 — 문서로 안내.

### 11.4 기계 검증 (v3 갱신)

- 린트 [12]/[13] 갱신: mode 값 `all | core`, `phase-core.md` 존재/등록, `--hotfix` 매핑 안내("핵심 모드로 실행됩니다"), "핵심 모드 분기"·"핵심 모드 전용 긴급 보안 감사" 문구 쌍, 구 명칭("LIGHT 모드") 잔존 금지 신설.
- 골든 시나리오 갱신: S7·S11~S14 명칭 반영, S13 마이그레이션 확장(`normal`/`full`→all, `light`→core).
