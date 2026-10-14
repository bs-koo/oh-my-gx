# gx-tdd 테스트 실행 횟수 축소 설계

작성일: 2026-10-14
상태: 설계 승인 · Codex 리뷰 반영 (spec 검토 대기)
기준 커밋: `d03645e`
브랜치: `perf/gx-tdd-test-runs`

## 목표

gx-tdd 파이프라인에서 W(작업) 하나가 전체 테스트 스위트를 돌리는 횟수를 줄이고, 남은 기준선 1회를 사용자가 PRD·설계를 검토하는 구간과 겹쳐 대기 경로에서 뺀다. verify의 신선한 실행, 기준선 판정, 테스트 무결성 해시, Iron Law는 그대로 둔다.

## 배경 (실측)

소비 프로젝트 kreb-grep-2026-web의 W77(`feat/gray-meter-building-toggle`) 실행 기록이다.

| 항목 | 시간 |
|---|---|
| java test | 19.6분 |
| java build | 3.2분 |
| vitest + lint | 21분 |
| node build | 3.2분 |
| 전체 게이트 1회 | 약 47분 (순차) |

현행 gx-tdd가 W 하나에서 전체 게이트를 돌리는 지점:

| 지점 | 위치 |
|---|---|
| 기준선 게이트 | `phase-implement.md` Step 0.5 |
| 리뷰 전 Mechanical Gate | `phase-review.md` Step 0 (리뷰 반복마다 재실행) |
| 리뷰 정리 후 GREEN 재확인 | `phase-review.md` Step 4.4의 4b·4c |
| 핵심 모드 경계 회귀 | `phase-implement.md` Step 3.5 (직후 verify가 또 전체를 돈다) |
| 완료 verify | `phase-complete.md` Step -1 → gx-verify |

2026-09-01 설계(`docs/specs/2026-09-01-tdd-superpowers-realign.md`)가 정한 "전체 스위트 3회"(기준선 + 경계 회귀 + verify)에 리뷰 반복·정리 재확인이 더해져 W77 규모에서 테스트 대기만 2시간 20분 이상이 됐다. 같은 세션에서 오케스트레이터가 태스크 focused를 `*DbTest` 와일드카드·모듈 묶음으로 넓혀 돌렸고 사용자가 직접 중단시켰다. 최종 게이트는 백엔드 전체 테스트와 red-writer의 Gradle 실행이 겹친 상태에서 테스트 JVM이 `OutOfMemoryError: Java heap space`로 죽어 4,232건 중 2,391건만 실행됐다.

이 설계는 2026-09-01 설계의 "경계 회귀" 항목을 대체한다. 그 문서는 이력으로 두고 고치지 않는다.

## 결과

| 실행 경로 | 현행 전체 스위트 | 변경 후 |
|---|---|---|
| 전체 모드 | 기준선 1 + 리뷰 게이트 1~2 + 정리 재확인 0~2 + verify 1 | 기준선 1(사전 실행) + verify 1 |
| 핵심 모드 | 기준선 1 + Step 3.5 1 + verify 1 | 기준선 1(사전 실행) + verify 1 |
| `--phase implement` 단독 | 기준선 1 + Step 3.5 1 | 변경 없음 |
| `--phase review` 단독, ralph 이후 리뷰 | 리뷰 게이트 전체 | 변경 없음 (누적 focused를 만들 근거가 없어 전체 폴백) |

verify가 차단되어 수정하면 verify를 다시 돈다. 이것은 현행과 같다.

## 범위

포함:
- `gx-tdd`의 SKILL.md(요약 문구), phase-requirements·phase-implement·phase-review·phase-complete, references(pipeline-state, maintenance-notes, harness-adaptation)
- `gx-verify` (동시 실행 금지)
- `agents/implementer.md`와 생성 사본 `.claude/skills/gx-dev/references/codex-roles/implementer.md`
- 사용자 문서(README, `docs/tdd-guide.md`, `docs/guide.md`)의 해당 서술
- `tests/test_codex_skill_pipeline.py`, `tests/golden-scenarios.md`
- CHANGELOG·버전

제외:
- `gx-dev` — 별도 파일이고 기준선·verify가 없다. 리뷰 Step 0은 gx-dev 자체 계약으로 둔다.
- `gx-ralph-iterate`가 반복마다 부르는 verify — 별도 과제.
- 이전 W의 verify 결과를 기준선으로 재사용 — 병렬 W가 develop에 머지되면 트리가 달라 적중률이 낮고 다른 브랜치 state 탐색이 필요하다.
- 소비 프로젝트 설정(테스트 힙, vitest 워커 수) — 해당 저장소에서 별도로 다룬다.
- 발표 자료(`docs/tdd-presentation*.md`) — 시점 스냅샷이므로 고치지 않는다.

## D1. 전체 회귀를 verify 한 번으로

### 리뷰 Step 0 (phase-review)

**서두**: Step 0은 "이번 파이프라인이 만든 테스트와 빌드의 GREEN"을 보장한다. 기존 스위트 회귀는 phase-complete의 verify가 맡는다.

**0-1 Build**: 빌드는 테스트 실행을 제외한 변형으로 실행한다. CLAUDE.md에서 찾은 명령이 테스트를 포함하면(gradle `build`, `clean build` 등) 테스트 제외 변형(gradle `-x test testClasses` — 테스트 소스 컴파일은 유지)으로 바꾼다. `clean`은 붙이지 않는다. `'SSOT는 config'` 문구가 있는 빌드 표는 유지한다.

**0-2 Test — Step 0 테스트 집합** (리뷰 Step 0의 첫 실행, 재시도, 4b·4c 재확인이 모두 이 정의를 쓴다):

1. **무결성 선확인**: state.md `steps.implement`의 모든 태스크 `test-file-hash`를 현재 파일과 대조한다. 불일치나 파일 부재가 있으면 테스트를 실행하지 않고 파일 목록을 보여 묻는다 — "RED 산출물로 원복"(verify_implement 3의 무단 수정 처리) / "사용자 변경으로 인정"(해시 재기록). 수동 수정 뒤 재호출한 경로에서는 사용자의 정당한 수정일 수 있어 묻지 않고 원복하지 않는다. red-writer 재호출로 생긴 변경은 verify_red가 해시를 다시 기록하므로 걸리지 않는다.
2. **누적 focused**: 모든 태스크의 `test-file`(경로 하나 또는 경로 목록)을 모아 중복을 제거하고, 파일 경로가 어떤 타입의 `detect` 파일이 있는 디렉토리 아래에 있으면 그 타입(감지된 타입이 하나면 그 타입)으로 정해 타입별로 config `focusedTest` 템플릿에 대입한다. 조립 규칙(`{files}`·`{pattern}`)은 phase-implement "focused 테스트 명령 조립"을 따른다. 이번 파이프라인 테스트 파일이 없는 타입은 빌드만 하고 테스트는 돌리지 않는다 — 그 타입의 기존 스위트 회귀는 verify가 맡는다.
3. **전체 폴백**: 모든 태스크를 통틀어 `test-file` 기록이 0건이면(`--phase review` 단독, gx-ralph 루프 이후 리뷰, 구 세션) 감지된 모든 타입이 전체 `test`를 실행한다. 경로로 해석할 수 없거나 타입을 정할 수 없는 파일이 있음 / 해당 타입에 `focusedTest`가 없음 / focused 명령이 명령 자체 오류로 끝남(phase-implement의 명령 오류 가드와 같은 판정)이면 그 타입만 전체를 실행한다.
4. `'복수 타입'` 규약은 유지한다 — 감지된 타입마다 빌드와 위 테스트 집합을 실행한다.

실패 시 수리 디스패치(RED report 없는 수리 모드, 테스트 파일 무변경 확인)와 1회 재시도, 재시도 실패 시 사용자 확인은 현행 그대로다. 재시도는 첫 실행과 같은 테스트 집합으로 한다.

### 리뷰 정리 후 재확인 (phase-review Step 4.4)

- 4b 정리 모드의 GREEN 기준선은 "Step 0에서 통과한 Step 0 테스트 집합"이다.
- 4b와 4c(`cleanup_medium`) 정리 뒤 재확인은 Step 0 테스트 집합 ∪ 정리 대상 파일 관련 테스트(중복 제거)를 오케스트레이터가 1회 직접 실행한다. 정리 대상 관련 테스트가 Step 0 집합에 이미 있으면 추가하지 않는다.
- 4c의 단발성 확인 리뷰는 위 재확인 뒤에 수행하며 Step 0을 다시 돌지 않는다(현행 구조 유지).
- 4c의 다음 반복(`did_fix`)은 Step 0부터 재실행한다(현행 유지). Step 0이 가벼워졌으므로 비용 문제가 없다.
- 금지 사항 절의 "정리 후 전체 테스트 GREEN을 반드시 재확인한다"는 "정리 후 Step 0 테스트 집합으로 GREEN을 재확인한다(전체 회귀는 verify)"로 바꾼다.

### 경계 회귀 Step 3.5 (phase-implement)

- 실행 조건을 "**같은 실행 안에서 implement 뒤에 complete(verify)가 실행되지 않는 경로**"로 정의한다. 현재 이 조건에 해당하는 경로는 `--phase implement` 단독 실행이다.
- 전체 모드(implement → review → complete)와 핵심 모드(implement → complete)는 같은 실행에서 verify가 뒤따르므로 Step 3.5를 건너뛴다. 사용자가 중간에 중단하면 verify도 커밋도 없으므로 회귀가 커밋으로 나가지 않는다.
- 완료 보고 템플릿의 "전체 회귀는 경계에서" 문구를 "전체 회귀는 완료 verify에서 (`--phase implement` 단독: Step 3.5)"로 바꾼다.

### verify 차단 처리 (phase-complete Step -1)

서두의 이유 목록에 "gx-tdd에서 기존 스위트 회귀를 전체 실행으로 확인하는 곳은 이 verify가 유일하다"를 추가한다.

차단 시 사용자 선택지는 3개(**수정** / 수동 수정 / 중단)로 두고, "RGR 사이클로 수정"을 "수정"으로 바꾼다. "수정"을 고르면:

1. state.md를 `verify-status: pending`, `verify-fingerprint: ""`로 둔다 (이전 통과 기록이 남아 커밋 게이트가 열리는 것을 막는다). `current-step`은 `"verify 회귀 수리"`로 갱신한다.
2. verify가 보고한 차단 사유를 아래 표로 분류해 처리한다.

verify 회귀 수리에서는 테스트 파일을 수정하지 않는다 (수리 diff를 다시 리뷰하지 않으므로, 테스트를 바꾸는 수리를 두면 실제 회귀가 테스트 수정으로 덮여 리뷰 없이 커밋될 수 있다).

| 차단 사유 | 처리 | 새 RED |
|---|---|---|
| 기존 테스트 실패 (프로덕션 코드가 기대를 깨뜨림) | implementer **수리 모드** — 깨진 테스트 + 에러 전문 + 깨진 대상으로 조립한 focused 검증 명령. 프로덕션 코드로만 해결하고 수리 뒤 테스트 파일 무변경을 확인한다 | 불필요 (깨진 테스트가 RED) |
| 빌드 실패 — 프로덕션 소스 | implementer 수리 모드 | 불필요 |
| 신규 경고 — 동작 불변으로 정리 가능 | 정리 모드 — 세션 직접(`--isolated`면 implementer 정리 모드) | 불필요 |
| 신규 경고 — 고치려면 동작이 바뀜 | 실패 항목을 새 AC로 정의해 phase-implement 복귀 (현행 RGR 경로) | 필요 |
| 테스트를 고쳐야만 해결됨 (테스트 기대 의심, 테스트 소스 컴파일 실패) | 수리하지 않는다. 근거를 보여 주고 수동 수정 / 중단으로 안내 | — |

3. 처리 뒤 verify를 다시 실행한다.
4. **수리 라운드 상한 2회**: 이번 phase-complete 진입 이후 execution-log의 `verify 회귀 수리 R{n}` 항목 수로 센다. 2회 수행된 뒤에도 차단되면 "수정" 선택지를 빼고 수동 수정 / 중단만 묻는다. RGR 복귀 후 재진입하면 새로 센다.
5. 수리 diff는 다시 리뷰하지 않는다(사용자 결정). execution-log에 `verify 회귀 수리 R{n}` 항목으로 분류·대상·결과를 남긴다.
6. `--resume`이 `"verify 회귀 수리"`에서 재개되면 Step -1부터 재실행한다 (state는 1번에서 이미 pending이다).

"자동 수정은 시도하지 않음" 원칙은 유지한다 — 수리는 사용자가 "수정"을 고른 경우에만 수행한다.

## D2. 태스크 테스트 범위와 동시 실행 금지

### focused 범위 (phase-implement — 모든 실행 경로 공통)

- "focused 테스트 명령 조립"의 대상을 **이 태스크의 `test-file` 기록 파일**로 한정한다. 이전 태스크 테스트의 누적 실행은 리뷰 Step 0이 한다.
- 범위 확장 금지를 명시한다: 와일드카드 패턴(`*DbTest` 등), 패키지·모듈 단위 묶음, 회귀 확인용 이웃 클래스를 덧붙이지 않는다. `{pattern}`은 각 테스트 파일명에서 유도한 클래스 글롭만 쓴다.
- 같은 규칙을 세션 IMPLEMENT 절대 규칙, 격리 경로 implementer 프롬프트, `agents/implementer.md`에 반영한다(maintenance-notes의 세션 IMPLEMENT 계약 쌍둥이).
- 이전 태스크 `test-file-hash` 재검증(verify_implement 3)은 태스크마다 계속 수행한다. 테스트를 실행하지 않는 검사라 비용이 없고, 다른 태스크 테스트의 삭제·수정은 여기서 잡힌다.

### 테스트 수 비교 (verify_implement 4)

- `test-count` 비교 대상을 "직전 태스크의 같은 방식 값"에서 **같은 태스크의 직전 `test-count`**로 바꾼다. 태스크마다 집합이 달라 태스크 간 비교는 의미가 없다.
- 기준값 갱신: 그 태스크의 `test-file-hash`가 직전 기록 이후 바뀌지 않았으면 비교하고, red-writer 재호출로 verify_red가 해시를 다시 기록했으면(정당한 테스트 변경) 비교 없이 새 값으로 기준을 다시 잡는다. 첫 기록은 비교하지 않는다.
- 테스트 삭제·수정 감지의 주력은 `test-file-hash`·porcelain 대조이며 변경 없다.

### 동시 실행 금지

- 전체 스위트(기준선 사전 실행, verify)나 다른 테스트·빌드 명령이 실행 중이면 새 테스트·빌드 명령을 시작하지 않는다. 테스트를 실행하는 서브에이전트 디스패치(red-writer 실패 확인, implementer 등)도 완료 뒤로 미룬다.
- 근거: 같은 빌드 데몬·DB·CPU를 나눠 쓰면 시간 제한 테스트가 오탐하고 테스트 JVM이 메모리 부족으로 죽는다(W77 실측).
- 이것은 오케스트레이터의 행동 규칙이다. 테스트를 띄우는 주체는 오케스트레이터 하나이고 자신의 백그라운드 작업을 알 수 있으므로 state.md 잠금은 두지 않는다.
- 반영 위치: phase-implement 세션 절대 규칙, phase-complete Step -1, gx-verify Step 2 앞.

## D3. 기준선 사전 실행

### 적용 조건

다음을 모두 만족할 때만 사전 실행한다. 하나라도 아니면 사전 실행하지 않고 Step 0.5에서 현행대로 동기 실행한다.

- 하네스가 Claude Code다 (Bash `run_in_background` 사용 가능)
- VCS가 git이다 (지문 규약이 git 전용)
- 이번 실행의 phase 목록에 implement가 있다 (전체 모드·핵심 모드. `--phase requirements`·`--phase design`·`--phase implement` 단독은 해당 없음 — 앞의 둘은 같은 실행에서 결과를 쓸 Step 0.5가 없다)
- 지문 계산이 성공한다

시작 시 이전 실행이 남긴 `baseline.done`·`baseline-*.log`를 지우고, `baseline.done` 첫 줄에 `start={baseline-fingerprint}`를 쓴다. 수용 조건에 "첫 줄의 start 값이 state.md `baseline-fingerprint`와 같음"을 더한다 (`.dev/`는 브랜치에 남으므로 낡은 결과 차단). 명령은 `;`로 잇는 골격을 phase-implement에 제시한다 (`&&`·`set -e` 금지). 같은 세션에서 실행 중이면 파일 내용과 무관하게 그 행이 우선이며, 지문이 이미 달라졌으면 작업을 중지하고 동기 실행한다. 기다릴 때는 포그라운드 sleep을 쓰지 않고 완료 알림을 기다린다.

### 트리거 (phase-requirements)

phase-requirements **진입 직후, 본문(핵심 모드의 ac.md 작성, 전체 모드의 PRD 사이클)보다 먼저** 사전 실행을 시작한다. 본문에는 적용 조건 요약과 phase-implement Step 0.5 "사전 실행" 절 포인터만 둔다. phase-setup은 린트 바이트 예산(22000B, 여유 220B) 때문에 쓰지 않는다. requirements 재진입 시 `baseline-fingerprint`가 이미 있고 사전 실행이 진행 중이거나 완료됐으면 다시 시작하지 않는다.

### 절차 (phase-implement Step 0.5 "사전 실행" 절 — 정본)

1. gx-verify Step 5-A의 Claude Code 지문 규약(임시 인덱스, `.dev/` 제외, `{HEAD 단축}:{트리해시 앞12자}`)으로 지문을 계산한다. 결과가 `^[0-9a-f]+:[0-9a-f]{12}$` 형식이 아니면 사전 실행하지 않는다. 형식이 맞으면 state.md 최상위 `baseline-fingerprint`에 기록한다.
2. Bash `run_in_background: true` 호출 한 번으로 config 등록 순서대로 감지된 타입별 test → build를 순차 실행한다. 명령은 Step 0.5와 같은 config `projectTypes`의 test·build다.
3. 각 명령의 출력은 `${DEV_DIR}/baseline-{type}-{test|build}.log`에 리다이렉트로 캡처하고, 명령이 끝날 때마다 `{type} {test|build} rc={N}` 줄을 `${DEV_DIR}/baseline.done`에 추가한다.
4. 모든 명령이 끝나면 같은 규약으로 지문을 다시 계산해 `fingerprint-end={값}` 줄을 쓰고, 마지막 줄에 `DONE`을 쓴다.
5. 시작부터 Step 0.5까지 오케스트레이터는 프로젝트 코드 파일을 바꾸지 않는다 (requirements·design은 `.dev/` 산출물만 쓴다). D2의 동시 실행 금지를 따른다.

`DONE`은 "실행 완료" 표식이지 "성공"이 아니다.

### 결과 수용 (Step 0.5)

판정 1~5(기준 GREEN, warnings-baseline 기록, 측정 불가 처리, 하네스 부재, 레이어별 하네스)는 지금처럼 Step 0.5에서 한다. 바뀌는 것은 측정값의 출처뿐이다. 사전 실행 결과를 쓰려면 아래 수용 조건을 **모두** 만족해야 한다.

- `baseline.done`의 마지막 줄이 `DONE`이다.
- 감지된 모든 타입의 test·build 줄이 각각 1개씩 있다.
- `baseline-fingerprint`, `fingerprint-end`, Step 0.5 시점에 다시 계산한 지문의 트리 성분이 모두 같다.
- 각 로그 파일이 존재한다.

수용하면 rc·로그로 판정 1~5를 수행한다. `rc≠0`은 판정 1(기준 GREEN 실패 — 사용자 보고·진행 확인), 실행 0건은 판정 4(하네스 부재 감지), 경고 추출 불가는 판정 3(미측정 — 조용한 0 기록 금지)으로 현행과 똑같이 처리한다.

| 상태 | 처리 |
|---|---|
| 수용 조건 충족 | 사전 실행 로그로 판정 |
| 같은 세션에서 아직 실행 중 | 완료 알림 또는 `DONE` 줄을 기다린다. 기다리는 동안 다른 테스트·빌드를 시작하지 않는다 |
| `baseline.done`이 없거나 `DONE`이 없고 실행 중인 작업도 없음 (세션 재개 등) | 동기 실행 |
| 지문 불일치, 타입 줄 누락, 로그 부재 | 사전 실행 결과를 버리고 동기 실행 |
| `baseline-fingerprint`가 없음 (적용 조건 미충족, 구 세션) | 동기 실행 |

Step 0.7(gx-ralph 전환)은 Step 0.5 판정 뒤에 오므로 순서가 바뀌지 않는다.

### 하네스

- Claude Code: 위 절차를 따른다.
- Codex: 사용자 질문 사이에 백그라운드 세션이 유지된다는 보장을 확인하지 못했다. phase-requirements 트리거 문구에 "Codex에서는 시작하지 않는다"를 명시하고, `harness-adaptation.md` 표에 "`Bash(run_in_background: true)` 기준선 사전 실행 | 미지원 — 시작하지 않고 Step 0.5에서 동기 실행" 행을 추가한다.

### 트레이드오프

PRD·설계 대화 중에 PC 부하가 생긴다. 총 CPU 시간은 같고 시점만 앞당겨진다.

## state.md 필드

| 필드 | 위치 | 기록 시점 | 비고 |
|---|---|---|---|
| `baseline-fingerprint` | 최상위 | 사전 실행 시작 | 신규. phase-setup Step 7 초기화 필드에는 넣지 않는다 (없음 = 사전 실행 안 함) |
| `warnings-baseline` | 최상위 | Step 0.5 판정 | 변경 없음 |
| `test-file` | 태스크 | verify_red | 값 형식을 "경로 하나 또는 경로 목록"으로 명시 |
| `test-count` | 태스크 | verify_implement 4 | 비교 대상·기준 갱신 규칙만 변경 |

`pipeline-state.md` 스키마 예시와 게이트 목록("기준선·Mechanical Gate·verify")을 함께 갱신한다.

## 변경 파일 목록

| 파일 | 변경 |
|---|---|
| `.claude/skills/gx-tdd/phases/phase-requirements.md` | D3 트리거 |
| `.claude/skills/gx-tdd/phases/phase-implement.md` | Step 0.5 "사전 실행" 절·결과 수용, 세션 절대 규칙(범위·동시 실행), 격리 프롬프트, focused 조립, verify_implement 4, Step 3.5 조건, 완료 보고 템플릿 |
| `.claude/skills/gx-tdd/phases/phase-review.md` | Step 0 서두·0-1·0-2, Step 4.4 4b·4c, 금지 사항, state 예시 |
| `.claude/skills/gx-tdd/phases/phase-complete.md` | 서두 이유, Step -1 동시 실행 금지·차단 처리 |
| `.claude/skills/gx-tdd/SKILL.md` | 요약·`--phase` 설명 중 사실과 달라지는 문구 |
| `.claude/skills/gx-tdd/references/pipeline-state.md` | 신규 필드, `test-file` 형식, 게이트 목록 |
| `.claude/skills/gx-tdd/references/maintenance-notes.md` | 중복 항목: focused 범위 규칙 3곳, 수리 모드 3곳(review Step 0·Step 3.5·complete Step -1), 사전 실행 트리거↔절차 |
| `.claude/skills/gx-tdd/references/harness-adaptation.md` | Codex 미지원 행 |
| `.claude/skills/gx-verify/SKILL.md` | Step 2 앞 동시 실행 금지 |
| `agents/implementer.md` | 범위 확장 금지, 전체 회귀 위치 문구, 수리 모드 호출처에 "verify 회귀 수리" 추가 |
| `.claude/skills/gx-dev/references/codex-roles/implementer.md` | `sync-codex-resources.py`로 재생성 (직접 수정 금지) |
| `README.md`, `docs/tdd-guide.md`, `docs/guide.md` | 기준선 시점, 리뷰 게이트 범위, verify 역할 |
| `tests/test_codex_skill_pipeline.py` | 회귀 assert |
| `tests/golden-scenarios.md` | 수동 시나리오 |
| `CHANGELOG.md`, manifest 3곳 | 버전 |

`gx-ralph/SKILL.md:111`("최종 리뷰가 … 전체 테스트로 재검증")은 ralph 이후 리뷰가 전체 폴백이므로 사실로 남는다. 고치지 않는다.

## 호환·제약

- 린트 존재 검사 문자열을 유지한다: `'SSOT는 config'`, `'복수 타입'`(phase-review·phase-implement·gx-verify), `'테스트 하네스 부재'`, `'레이어별 하네스'`, `'프론트 AC 제외'`, `'focused 집합 직접 실행'`, `## Step 0.7: gx-ralph 전환 (--ralph 전용)` 헤더, `'라운드 5'`, phase-review의 verdict·Ruling·deferred 문구.
- `phase-setup.md`는 고치지 않는다 (바이트 예산, `'Step 3.5'` 금지 문자열).
- phase-implement에서 Step 2-I보다 앞에 행 시작 `Task(subagent_type="oh-my-gx:implementer")` 블록을 새로 넣지 않는다(behavior-tests 추출 규칙).
- `agents/implementer.md`를 고치면 `python scripts/sync-codex-resources.py`로 codex-roles를 재생성한다.
- phase 파일의 AskUserQuestion 예시는 질문 1~3개·선택지 2~3개 규칙을 지킨다.
- 린트 항목은 추가하지 않는다(`[N/36]` 분모 변경 파급 회피).

## 검증

자동:
- `python scripts/sync-codex-resources.py --check`
- `bash scripts/lint-consistency.sh` (약 4분, timeout 600000)
- `python -m unittest discover -s tests -p "test_codex_*.py" -v`
- `bash scripts/test-behavior-tests.sh` (프롬프트 추출 mock 검사 — 실제 모델을 부르는 `behavior-tests.sh`는 돌리지 않는다)

`tests/test_codex_skill_pipeline.py` 추가 assert (문서 계약 검사):
- phase-review Step 0-2가 무결성 선확인, 누적 focused, 전체 폴백 4조건을 담고, 4b·4c 재확인이 "Step 0 테스트 집합"을 가리킨다
- phase-implement Step 3.5 조건이 "complete가 실행되지 않는 경로"이고, focused 조립이 이 태스크 `test-file`로 한정되며 범위 확장 금지를 담는다
- phase-requirements 트리거가 Step 0.5 "사전 실행" 절을 가리키고 Codex·svn 제외를 담는다
- phase-implement Step 0.5 수용 조건이 `DONE`·타입 줄·지문 3자 일치·로그 존재를 모두 담는다
- phase-complete Step -1이 "수정" 선택지, `verify-status: pending` 리셋, 분류 표, 상한 2회를 담는다

`tests/golden-scenarios.md` 수동 시나리오 (모델 실행 필요 — 자동 검사가 못 잡는 행동):
- 전체 모드 W에서 전체 스위트가 사전 실행 1 + verify 1만 돈다
- 사전 실행 중 코드 파일을 바꾸면 Step 0.5가 동기 재실행한다
- verify가 기존 테스트 회귀로 차단 → "수정" → 수리 모드 → verify 재통과, state가 수리 중 pending이다

실측 효과는 다음 소비 프로젝트 W 실행에서 execution-log의 게이트 시간으로 확인한다. Codex smoke 대상 동작(설치·질문·역할 위임·훅·커밋)은 바꾸지 않는다.

## 릴리스

CHANGELOG에 `Changed` 항목을 추가하고 manifest 3곳의 버전을 올린다. 열려 있는 PR #92가 v1.34.0을 쓰므로 이 변경은 v1.35.0으로 한다. 머지 순서가 바뀌면 PR 시점에 조정한다.

## 위험

| 위험 | 완화 |
|---|---|
| 기존 테스트 회귀를 리뷰 뒤 verify에서 처음 발견 | verify 차단 "수정" 경로가 분류 후 수리 모드로 처리. 상한 2회, 내역은 execution-log |
| 태스크 간 회귀를 태스크 시점이 아닌 리뷰 Step 0에서 발견 | Step 0 수리 디스패치 유지. 이전 태스크 해시 재검증은 태스크마다 계속 |
| 사전 실행 뒤 또는 실행 중 코드 변경을 기준선으로 오인 | 시작·종료·Step 0.5 지문 3자 비교로 무효화 후 동기 재실행 |
| 사전 실행 중 PC 부하 | 테스트를 실행하지 않는 단계와만 겹친다. 총 비용은 같다 |

## Codex 리뷰 반영 기록 (2026-10-14)

반영: 사전 실행 적용 조건·지문 실패 처리·svn 제외, `DONE`의 의미와 수용 조건, verify 차단 분류·상한·state 리셋, 리뷰 Step 0 무결성 선확인, 시작·종료 지문, Step 3.5 조건 재정의, Step 0 테스트 집합 정의 통일, `test-file` 형식·타입별 조립, Codex 대응 명시, 변경 파일 목록, 골든 시나리오, 사용자 문서, `test-count` 기준 갱신 규칙.

반영하지 않음:
- 동시 실행 잠금(state.md 게이트 식별자·stale 판정) — 테스트를 띄우는 주체가 오케스트레이터 하나이고 자기 백그라운드 작업을 알 수 있다. 잠금과 stale 판정은 실패 경로를 더 만든다. 행동 규칙으로 둔다.
- 누적 focused가 실제 수집한 파일 목록 기록·대조 — 해시 선확인이 테스트 파일 삭제·수정을 잡고, 수집 누락은 러너 출력의 실행 수로 보인다. 별도 기록은 들이는 비용에 비해 얻는 것이 적다.

## 최종 리뷰 반영 기록 (2026-10-14)

구현 후 Codex 리뷰와 Claude 리뷰어(새 컨텍스트)의 지적으로 다음을 바꿨다: `--phase requirements` 단독 사전 실행 제외, 낡은 `baseline.done` 차단(`start=` 줄·시작 시 삭제), 실행 중 우선 규칙과 지문 변경 시 중지, 실행 골격(`;` 연결), Step 0 무결성 불일치 시 원복 대신 질문, 테스트 파일이 없는 타입은 빌드만, 타입 판별 규칙, gradle `-x test testClasses`, verify 회귀 수리에서 테스트 수정 제외, 수리 상한 카운터 기준, 정리 주체, `test-file-hash` 목록 형식.
