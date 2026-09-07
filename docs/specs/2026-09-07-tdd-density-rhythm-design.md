# gx-tdd 지시문 밀도·사이클 리듬 설계

작성일: 2026-09-07
배경: superpowers(6.3.0) TDD 경로와의 실측 비교. GX 사업본부 AI 해커톤(2026-09-22, 6시간) 적용을 앞두고 gx-tdd의 체감 속도를 올리되 검증 층은 유지한다.

## 1. 문제

실측치는 이 저장소의 파일 크기와 phase 파일의 디스패치 구조에서 세었다.

| 항목 | gx-tdd (현행) | superpowers |
|---|---|---|
| 오케스트레이터가 사이클당 읽는 지시문 | 약 246KB (SKILL.md 75KB + phase 6종 135KB + verify·commit·PR 36KB) | 약 60KB (SDD 52KB + 마무리 8KB) |
| 태스크당 콜드 스타트 | 2회 (red-writer, implementer) + 오케스트레이터 기계 검증 6단계 | SDD 2회, 세션 내 실행 0회 |
| 태스크 단위 | "2~15분에 RED→IMPLEMENT 완료" — 사실상 테스트 1건 | 리뷰어가 이웃을 승인하면서 이것만 거절할 수 있는 단위. 2~5분은 태스크 안의 한 걸음 |
| 사용자 게이트 | 11~16회, 6개 phase에 분산 | 설계 대화에 집중, 실행은 무인 |

세 번째 항목이 가장 큰 비용을 만든다. 사이클 단위·디스패치 단위·검증 단위가 하나로 묶여 있어 테스트 30개짜리 분해는 콜드 스타트 60회가 된다. 실제로 한 세션에 태스크 30개가 배정된 사례가 있다.

네 번째 항목(게이트 분산)은 이번 범위에서 다루지 않는다.

## 2. 무엇을 유지하는가 (불변)

gx-tdd가 superpowers보다 나은 점은 "먼저 실패했다"와 "테스트를 건드리지 않고 통과시켰다"를 **재는** 검증 층이다. 아래는 어느 결정에서도 바꾸지 않는다.

- red-writer의 별도 컨텍스트 격리와 "참조한 파일" 자기신고 검증 (verify_red)
- 테스트 파일 해시(`test-file-hash`)의 RED 직후·IMPLEMENT 직후 대조, porcelain 스냅샷 대조
- 오케스트레이터가 focused 집합을 **직접** 실행해 통과를 목격하고 `test-count`를 기록
- verify 게이트의 신선 실행·지문(`verify-fingerprint`)·경고 기준선, 훅 G3
- trust-ledger의 위험 수용 기록, `reports/t{N}-red.md`·`reports/t{N}-impl.md` 보고 파일
- fix 라운드 4~5의 fresh 디스패치 + opus 격상 (fresh eyes와 역량 격상을 한 번에)

## 3. 결정

### D1. IMPLEMENT는 세션이 직접 수행한다 (기본값). RED 격리는 유지한다

- 태스크당 콜드 스타트를 2회에서 1회로 줄인다. red-writer 디스패치는 그대로이고, GREEN+REFACTOR는 오케스트레이터가 `agents/implementer.md`와 같은 계약(테스트 수정 금지, YAGNI, REFACTOR 금지 목록 5항목, focused만 실행, self-review, report 작성)으로 직접 수행한다.
- verify_implement의 검사(해시·porcelain·focused 직접 실행·test-count·과잉 구현·시그니처)는 파일 상태 대조라 수행 주체와 무관하게 같은 강도로 동작한다. implementer 격리는 원래 "입력 범위 제한"이었지 코드 차단이 아니었으므로(phase-implement Iron Law 절), 세션 수행으로 잃는 검증은 없다.
- 잃는 것은 implementer의 fresh eyes다. phase-review의 reviewer 1석과 fix 라운드 4~5의 fresh+opus 디스패치가 그 역할을 맡는다.
- `--isolated` 플래그로 현행 2석 디스패치를 되돌린다. gx-ralph 무인 루프는 항상 2석이다(반복 세션에는 사용자도 없고 재개도 없어 현행 구조가 맞다).
- 격리를 둘 다 없애는 안(superpowers executing-plans 방식)은 택하지 않는다. red-writer 격리는 해시로 대체할 수 없는 유일한 층이다.

### D2. 태스크 단위를 AC로 올리고, RGR의 작은 걸음은 태스크 안으로 넣는다

- **태스크 = AC 1건**이 기본이다. red-writer는 그 AC의 G-W-T 시나리오 전부를 테스트 집합으로 한 번에 쓴다. verify_red는 집합의 **모든** 케이스가 실패해야 통과시키고, 통과하는 케이스가 있으면 그 케이스만 재작성시킨다.
- 세션 IMPLEMENT는 내부 루프를 돈다 — focused 실행 → 실패 케이스 하나 선택 → 최소 구현 → focused 재실행 → 다음 케이스 → 전부 GREEN 후 REFACTOR. TDD의 2~15분 걸음은 여기서 일어난다.
- 같은 컴포넌트를 건드리는 AC, 같은 패턴의 소형 변경으로 환산되는 AC는 하나의 태스크로 **묶는 것이 기본**이다. 한 AC가 컴포넌트 둘 이상에 걸칠 때만 AC보다 작은 태스크가 생긴다.
- **태스크 수 가드**: 분해가 8개를 넘으면 승인 게이트 전에 분할 선택지를 먼저 묻는다 — AC 묶어 재분해 / `.dev/plan.md` W행으로 분할 / `--ralph` 전환 / 그대로 진행.
- red-writer는 구현을 보지 못하므로, 테스트를 하나씩 쓸 때 얻는 "구현이 드러내는 다음 테스트" 피드백은 현행 구조에도 없었다. AC 단위 일괄 작성으로 잃는 것이 없다.

### D3. 지시문을 추출·압축·조건부 로드로 줄인다

- **추출**: SKILL.md의 하네스 적응 표는 `references/harness-adaptation.md`로, 드리프트 주의 19항목은 `references/maintenance-notes.md`로 옮긴다. 둘 다 실행 중에는 읽히지 않는다. 하네스 표는 Codex 실행 시 포인터를 따라 읽는다(스킬 디렉토리는 어느 하네스에도 함께 배포된다).
- **압축**: state.md 스키마의 60줄 YAML 예시를 필드 표로, Context Slicing 불릿을 표로, 작업 경로 기준 불릿을 표로 바꾼다. 갱신 규칙·판별 키·지시 문구는 원문 그대로 보존한다.
- **조건부 로드**: phase-setup의 재개 감지(Step 0 전체)는 `phases/setup-resume.md`로, 작업 계획 참조(3.0.5·5.5·되돌림)는 `phases/setup-work.md`로 옮기고, 플래그가 있을 때만 Read한다.
- **예산 린트**: SKILL.md ≤ 61,500B, phase-setup.md ≤ 22,000B를 정합성 린트로 고정한다. 45KB 목표는 인자 절(의도 파싱 6K자) 재작성이 필요해 후속으로 남긴다.

### D4. 범위 밖

- Codex용 디스패치 프롬프트 분리(phase-implement 14KB): 린트 [3]·[26] 갱신이 필요하고 Codex 경로를 실측할 수 없어 보류.
- SKILL.md 인자 절 재작성, 게이트 앞당기기(승인을 설계 시점에 집중), gx-dev 쌍둥이 블록 정리, gx-ralph-iterate 구조.

## 4. 비용 모델

AC 10개, 테스트 30개, 전체 모드 기준.

| 항목 | 현행 | 이후 |
|---|---|---|
| 구현 단계 콜드 스타트 | 60회 (태스크 30개 × 2) | 10회 이하 (AC당 red-writer 1회, 묶기 시 더 감소) |
| 오케스트레이터 지시문 (기본 경로) | 약 246KB | 약 213KB (SKILL 61.5KB + setup 22KB, 나머지 동일) |
| 태스크 승인 표의 행 수 | 30 | 8 이하 (가드) |

지시문 감량은 매 턴에 작용하지만 체감 속도의 큰 몫은 콜드 스타트 수에서 나온다. 두 계획은 독립이며 순서는 밀도 → 리듬이다(둘 다 SKILL.md를 고치므로 충돌을 피한다).

## 5. 계획

- `docs/superpowers/plans/2026-09-07-tdd-instruction-density.md` — D3. v1.26.2.
- `docs/superpowers/plans/2026-09-07-tdd-session-implement.md` — D1·D2. v1.27.0. 밀도 계획 머지 후 착수.
