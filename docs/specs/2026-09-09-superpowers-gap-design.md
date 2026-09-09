# gx-tdd·gx-context superpowers 이격 보완 설계

작성일: 2026-09-09
배경: oh-my-gx v1.27.0의 gx-tdd·gx-context와 superpowers 6.3.0 스킬 14종을 전면 대조한 분석(2026-09-09 세션)에서 나온 소견 6건 중 4건을 보완한다. 소견 4(지시문 규모)는 `2026-09-07-tdd-density-rhythm-design.md` D3·D4가 이미 다루므로 여기서 제외한다.

## 1. 문제

| 소견 | 현행 gx-tdd | superpowers | 비용 |
|---|---|---|---|
| 1·2. 세션 IMPLEMENT + 태스크별 리뷰 부재 | v1.27.0부터 오케스트레이터가 GREEN+REFACTOR를 직접 수행한다. 태스크 단위 검증은 verify_implement의 기계 검증(해시·porcelain·focused)과 self-review뿐이고, 사람 눈에 해당하는 리뷰는 phase-review에서 전체 diff에 대해 1회다 | 태스크마다 fresh implementer + 태스크 리뷰(spec+quality), 마지막에 전체 브랜치 리뷰. 컨트롤러는 직접 구현하지 않는다 | 세션이 자기 코드를 자기가 검증한다. 태스크 8개가 누적된 뒤 SPEC FAIL이 나오면 재구현 라운드가 커진다 |
| 3. 구현 내부 게이트의 사용자 확인 | 과잉 구현 정리 여부(verify_implement 5), 동작 불변 정리 수행 여부(phase-review 4b), Minor·MEDIUM 수정 여부(4c)를 AskUserQuestion으로 묻는다 | "Rulings, not stalls" — 컨트롤러가 판정하고 원장에 `Ruling: 무엇 — 왜 — 틀리면 비용`으로 남긴다. 멈춤은 비가역·보안·외부 부작용·계획 붕괴 넷뿐 | 구현 단계에서 사람이 기다리는 시점이 태스크당 최대 3회 늘어난다. 답은 거의 항상 기본값이다 |
| 5. gx-context 결합이 얕음 | phase-setup 3.1이 glossary·architecture만 DOMAIN_CONTEXT로 싣는다. gx-context가 정량화 수칙으로 받아낸 README의 문제·성공 기준·사용자/규모와 status.md 미반영 항목은 PRD 작성에 닿지 않는다 | 대응물 없음 (superpowers는 일회성 spec) | 도메인 지식이 있어도 PRD가 그것을 모르고 작성되고, 이미 status.md에 있는 FR과 중복된 요구사항이 새 번호로 생긴다 |
| 6. 스킬 행동 검증 공백 | 린트 33항목(문구·구조)과 골든 시나리오 39개(수동) | writing-skills — 서브에이전트로 규칙 위반을 먼저 관찰(RED)한 뒤 스킬을 쓰고 준수를 확인(GREEN) | "문구가 있다고 모델이 따르는 것은 아니다"(CHANGELOG v1.24.0). 프롬프트로만 금지되는 계약(red-writer 격리, implementer 테스트 수정 금지, reviewer 판정 순서)의 회귀를 잡을 수단이 없다 |

## 2. 무엇을 유지하는가 (불변)

- v1.27.0의 세션 IMPLEMENT 기본 경로와 `--isolated` 격리 경로. 되돌리지 않는다 — 콜드 스타트 절감이 해커톤 적용의 전제다.
- red-writer 격리, 테스트 해시·porcelain 대조, focused 직접 실행, verify 지문, 훅 G1~G4.
- 산출물 승인 게이트(PRD·설계·태스크 분해)와 SPEC FAIL·Critical·동작 결함 RGR 여부·위험 수용의 AskUserQuestion. 이것은 협업 접점이다(decisions.md 2026-09-01 "게이트 범위" 판정: "이 부분은 의도된거라 어쩔 수 없어").
- gx-ralph-iterate의 2석 헤드리스 경로. 이 설계의 어느 결정도 루프를 건드리지 않는다.
- `.dev/`의 협업 공유, `decisions.md` 훅 기록, reports 파일 인계 계약.

## 3. 결정

### D1. 태스크 리뷰를 조건부로 넣는다 (phase-implement Step 2-V)

- verify_implement 통과 직후, 태스크 완료 처리 전에 reviewer를 **태스크 범위 모드**로 디스패치한다. 입력은 그 태스크의 AC·태스크 diff·RED/IMPL report·설계서 인터페이스뿐이다. phase-review는 전체 브랜치 리뷰로 남는다.
- **발동 조건**은 둘 중 하나다. (a) 태스크가 바꾼 프로덕션 파일이 2개 이상. (b) 그 태스크에 fix 라운드가 1회 이상 있었다. 둘 다 아니면 기계 검증으로 충분하다고 보고 `review: skipped`만 남긴다. 변경 파일은 verify_red의 porcelain 스냅샷과 현재 porcelain의 차이로 기계적으로 구한다.
- 태스크 diff는 실제 인덱스를 건드리지 않는 **임시 인덱스**(훅의 지문 계산과 같은 관용구)로 `reports/t{N}-diff.txt`에 쓴다. 실제 인덱스를 스테이징하면 porcelain 스냅샷 대조가 오탐한다. 수집은 한 Bash 호출로 하고 add 실패를 감지해 중단한다 — add가 실패해도 diff는 0으로 끝나며 HEAD 파일 전부를 삭제로 낸다. 경로 인용은 `core.quotePath=false`로 끈다. 스냅샷이 없는 구 세대 재개는 (a)를 판정하지 않는다.
- reviewer는 Write 도구가 없으므로 출력을 오케스트레이터가 `reports/t{N}-review.md`에 저장한다. 두 YAML 판정 블록의 파싱·상충 처리는 phase-review Step 4.0과 같다.
- 라우팅: spec FAIL·Critical·Important[동작결함] → **red-writer가 결함을 재현하는 실패 테스트를 먼저 추가**(RED 재호출 — verify_red 재적용, 해시·스냅샷·test-count 기준선 갱신)한 뒤 기존 fix loop(라운드 카운터·상한 5 공유, 라운드 4~5는 fresh implementer + opus). 기존 fix loop는 테스트 해시를 고정해 그 안에서 테스트를 추가할 수 없으므로, RED 없이 보내면 동작 결함을 테스트 없이 고치는 자동 경로가 된다(Iron Law 1 위반 — 최종 리뷰 C1). Important[동작불변] → 세션 정리(그것만 있어도 라운드 1 소모). Minor → 유예하고 phase-review Task A가 머지 전 수정 필요 여부를 판정한다. 재리뷰는 findings 목록 + 수정 diff만 보는 scoped 재리뷰다(superpowers re-review-prompt).
- 모델은 프로파일과 무관하게 sonnet이다. 태스크 diff는 작고, superpowers도 scoped 재리뷰는 저·중급 모델을 쓴다.
- 검증: 린트 `[34]`(Step 2-V 절·발동 조건·경로·sonnet·재리뷰·유예 전달), 골든 S40(발동)·S41(스킵).

### D2. 구현 내부 게이트 3곳을 기본값 판정으로 바꾼다

- 대상은 verify_implement 5(과잉 구현), phase-review 4b(동작 불변 정리), 4c(Minor·MEDIUM)뿐이다. 그 외 AskUserQuestion은 그대로다(2절 불변).
- 기본값: 과잉 구현은 **제거**(테스트가 참조하지 않는 신규 public 멤버. 설계서 인터페이스가 명시한 멤버는 "설계 예약"으로 유지). 동작 불변 정리는 **수행**. quality Minor는 **유예**. security MEDIUM은 동작 불변이면 정리 모드로 수정, 동작 변경 동반이면 유예. 모호하면 보수적으로 유예. 유예 목록은 `reports/review-deferred.md`에 두며 trust-ledger 구조는 바꾸지 않는다.
- 판정은 `${DEV_DIR}/decisions.md`에 훅과 같은 파일·같은 헤더 규약으로 append한다. 블록 형식은 `## {시각} · Ruling: {제목}` + `**판정.**`/`**근거.**`/`**틀리면.**` 세 줄이다. 워크스페이스 안에만 두지 않는다 — Step 4 사이클 보고와 PR 본문(`--extra-section`으로 넘기는 `pr-rulings.md`의 `## Rulings`·`## Deferred`)에 제목을 나열한다.
- 검증: 린트 `[35]`(규약 절·폐지된 질문 3곳 부재·기록 지시·PR 노출), 골든 S42.

### D3. 도메인 컨텍스트를 4요소로 넓히고 PRD·설계에 주입한다

- DOMAIN_CONTEXT = 용어(glossary) + 아키텍처(architecture) + **README 핵심**(`## 배경`·`## 안 하면 어떻게 되는가`·`## 사용자와 규모`·`## 성공 기준`) + **status.md 미반영 항목**(상태 열이 ⬜인 행). 우선순위는 용어 > README 핵심 > 미반영 > 아키텍처이며 `contextLimits` 초과 시 뒤에서부터 요약·생략한다.
- product-owner는 4요소 전부를 받고, **미반영 항목과 겹치는 요구사항은 새 FR을 만들지 않고 그 FR ID를 인용**하며, 성공 기준의 수치를 AC의 Then에 반영한다. architect는 용어·아키텍처만 받는다(현행 SKILL.md 표대로 — 다만 phase-design 프롬프트 목록에 빠져 있던 항목을 명시한다).
- phase-complete Step 3의 status.md 갱신은 PRD가 인용한 FR ID로 행을 찾는다.
- gx-dev의 쌍둥이 블록(phase-setup 3.1·phase-requirements·phase-design)도 같이 고친다. 결합 지점이 같으므로 한쪽만 고치면 유지보수 노트의 쌍둥이 목록이 어긋난다.
- 검증: 린트 `[36]`(setup 4요소·requirements FR 인용·design 전달 — tdd/dev 양쪽), 골든 S43.

### D4. 프롬프트 계약을 실제 실행으로 검증하는 하네스를 둔다

- `scripts/behavior-tests.sh`: 픽스처 프로젝트(node 내장 러너, 의존성 0)를 임시 샌드박스에 복사하고, **phase 파일의 디스패치 프롬프트를 그대로 추출**해 에이전트 정의 본문을 system prompt로 붙여 `claude -p`로 실행한 뒤, 결과를 기계적으로 판정한다. 시나리오는 프롬프트로만 금지되는 계약 셋이다.
  - B1 red-writer 격리: `src/`를 한 번도 Read/Grep/Glob하지 않고, 프로덕션 파일을 건드리지 않고, 실패하는 테스트를 쓴다.
  - B2 implementer 테스트 불변: 테스트 파일 해시가 변하지 않고, 전부 GREEN이 되고, report에 `## GREEN 증거`가 있다.
  - B3 reviewer 판정 순서: `spec_verdict`가 `quality_verdict`보다 먼저 나온다.
- 판정은 LLM이 아니라 파일 해시·러너 출력·stream-json의 tool_use 기록으로 한다.
- 스크립트 자체는 mock claude로 CI에서 검증한다(`scripts/test-behavior-tests.sh` — gx-ralph 러너 테스트와 같은 방식). 실제 모델 실행은 릴리스 전 수동이며 결과를 PR 본문에 골든 시나리오와 같은 형식으로 남긴다.
- 프롬프트를 복사하지 않고 phase 파일에서 추출하는 이유: 복사본은 드리프트한다. 추출이 깨지면 mock 테스트가 CI에서 먼저 잡는다.

### D5. 실행 순서와 버전

| 순서 | 계획 | 버전 | 린트 |
|---|---|---|---|
| 1 | `2026-09-09-tdd-task-review.md` (D1) | 1.28.0 | [34] |
| 2 | `2026-09-09-tdd-rulings.md` (D2) | 1.29.0 | [35] |
| 3 | `2026-09-09-context-injection.md` (D3) | 1.30.0 | [36] |
| 4 | `2026-09-09-behavior-tests.md` (D4) | 1.31.0 | 없음 (CI에 mock 테스트 추가) |

각 계획은 앞 계획이 main에 머지된 뒤 시작한다. D2는 D1의 Step 2-V가 만든 findings 라우팅 위에서 판정 규약을 정의하고, D4는 D1이 바꾼 reviewer 프롬프트를 추출하므로 순서를 바꾸지 않는다.

## 4. 범위 밖

- 지시문 규모(SKILL.md 45KB 목표) — 밀도 설계 D3·D4.
- 산출물 승인 게이트 축소 — 협업 접점으로 유지한다는 결정이 이미 있다.
- gx-ralph-iterate에 태스크 리뷰 넣기 — 루프는 리뷰 없이 verify로 닫고 종료 후 대화형 재진입이 리뷰한다.
- gx-dev에 태스크 리뷰·판정 규약 넣기 — gx-dev는 coder 단일 호출이라 태스크 단위가 없다.
