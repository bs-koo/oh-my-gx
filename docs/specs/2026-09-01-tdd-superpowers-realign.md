# gx-tdd superpowers 재정렬 설계 (v2)

작성일: 2026-09-01
개정: v2 (Momus 검토 REVISE 반영)
브랜치: `feat/tdd-agent-realign`
상태: 설계 확정 대기 (사용자 검토)
원본 기준: superpowers 6.3.0 (`test-driven-development`, `subagent-driven-development`, `writing-good-tests`, `verification-before-completion`)

## v1에서 달라진 것

| # | v1 결함 | v2 해결 |
|---|---------|---------|
| C-1 | eco 목록에서 quality-reviewer를 빼면 린트의 opus 전수 대조(`lint-consistency.sh:309-315`)가 FAIL | 목록에 reviewer를 **추가**하고 quality-reviewer는 **잔류** (T9) |
| C-2 | T4가 린트 [3/25]의 `"최대 2회"` 검사(`:72-73`)를 깨뜨림 | 검사 문자열을 `"라운드 5"`로 교체하는 린트 수정을 스펙에 포함 (T4) |
| C-3 | ralph가 참조하는 Step 2-G/2-F가 소리 없이 사라짐 | 트리오 프롬프트를 **부록 A로 보존** + ralph 참조 문구 갱신 (T1) |
| C-4 | phase-review Step 0이 여전히 green-coder 디스패치 — 미호출 선언과 모순 | Step 0 수정 주체를 implementer로 교체 (T3) |
| C-5 | focused 실행 명령의 SSOT 부재 — 구현 불가 | `projectTypes.focusedTest` 필드 신설 + 폴백 정의 (T2) |
| C-6 | test-count 증거 주체가 감시 대상(implementer)으로 역전 | verify_implement에서 오케스트레이터가 **focused 집합 1회 직접 실행** (T2) |
| C-7 | 영향 범위 표가 실제 대상의 절반 누락 | 실측 grep 기반으로 재작성 |
| I-1 | `--phase implement` 단독 경로의 전체 회귀 0회 | 핵심 모드와 같은 지점(Step 4 직전)에 1회 명시 (T2) |
| I-2 | opus 격상과 eco 프로파일 충돌 | "격상은 실패의 대응 — 프로파일과 독립" 규칙 명시 (T4) |
| I-3 | 구 세션 resume 시 red report 파일 부재 | 인라인 인계 예외 정의 (하위 호환) |
| I-4 | 새 current-step/steps 리터럴 미정의 | 계약 문자열 확정 (T5) |
| I-5 | T7 배칭이 Step 1 규칙 1과 충돌 | 규칙 1 개정문 확정 (T7) |
| I-6 | phase-complete 행이 오독 (ralph 예외 조항을 변경 지시) | 무변경 확인으로 교체 |
| I-7 | SKILL.md 드리프트 주의 목록 갱신 누락 | 항목별 갱신안 명시 |
| I-8 | 린트 번호 인용 오류 ([14/26]·[27/27]) | 실번호 [N/25] 기준, 신규 [26/26] + 분모 일괄 갱신 |
| I-9 | 통합 리뷰 Iron Law 문구 미확정 | 리터럴 + 재명시 지점 6곳 확정 (T3) |
| I-10 | T8의 미정의 변수·svn 누락·병렬 곁가지 | 재작성 (T8) |
| M-1~8 | 인용 라인 오차·mutation check 축약·표 불일치 등 | 각 절에서 정정 |

## 배경

gx-tdd는 superpowers의 TDD 스킬을 파이프라인화한 것이지만, 이식 과정에서 원본의 실행 모델과 어긋난 지점들이 실행 시간을 지배하게 되었다. W 하나(AC 4개 기준):

| 항목 | 현행 | 원본(SDD) 방식이면 |
|------|------|--------------------|
| 에이전트 디스패치 | 약 20회 (RGR 12 + 설계 3 + 리뷰 3 + 기타 2) | 약 13회 |
| 전체 테스트 실행 | 10~14회 (태스크마다 2~3회) | 3~4회 |
| 태스크당 좌석 | 3석 (red/green/refactor) + 오케스트레이터 검증 4종 | 2석 (implementer + reviewer) |
| 수정 루프 | fresh 재호출 2회 → 3회 실패 시 중단 | resume 1~3라운드 → fresh+모델 격상 4~5라운드 |
| 에이전트 보고 | 전문 인라인 반환 (오케스트레이터 컨텍스트에 누적) | report 파일 + 15줄 상태 반환 |

## 확정된 결정 (사용자 확인 완료)

| # | 결정 | 내용 |
|---|------|------|
| D1 | **확인 게이트는 현행 유지** | PRD·설계·태스크 분해 승인 등 AskUserQuestion 게이트는 의도된 협업 접점이다. superpowers의 "Rulings, not stalls"는 도입하지 않는다 |
| D2 | **RGR 2석** | red-writer(격리 유지) + implementer(GREEN+REFACTOR 통합, 신설) |

D1에 따라 이 설계의 범위는 **게이트 구조를 건드리지 않고, 에이전트 좌석·테스트 실행·증거 계약을 superpowers 방식으로 정렬**하는 것이다.

## 스펙

### T1. implementer 신설 — RGR 2석 (D2)

`agents/implementer.md`를 신설한다. green-coder + refactor-coder의 역할 통합:

- **절대 규칙 승계**: 테스트 파일 수정 금지(결함 의심 시 보고), YAGNI(테스트를 통과시키는 최소 코드), REFACTOR는 GREEN 유지·동작 변경 금지, 정리 실패 시 즉시 롤백.
- **작업 순서**: 최소 구현 → focused 테스트 통과 확인 → 정리(중복 제거·네이밍·구조) → focused 재확인 → self-review(T6) → report 작성(T5).
- **모델**: `model: sonnet`. 도구: Read, Write, Edit, Glob, Grep, Bash (`agents/green-coder.md:19-25`와 동일).

phase-implement Step 2가 `2-R (red-writer, 현행 유지) → 2-I (implementer)`로 바뀐다. 오케스트레이터 검증은 verify_red(현행 유지) + **verify_implement**(T2 정의)로 줄어든다.

**구 Step 2-G/2-F는 삭제하지 않고 phase-implement 말미의 "부록 A: gx-ralph 전용 트리오 프롬프트"로 이동한다.** `gx-ralph-iterate/SKILL.md:89`가 "Step 2-R/G/F 디스패치 프롬프트를 따르되"로 이 절들을 참조하며, 폴백 조건이 "Read 실패"뿐이라 절만 사라지면 반복 세션이 프롬프트 소스를 잃는다 (C-3). 같은 커밋에서 `gx-ralph-iterate/SKILL.md:89`의 참조 문구를 "Step 2-R 및 부록 A의 G/F 디스패치 프롬프트"로 갱신한다. ralph의 2석 전환은 C단계 검토 사항이다.

**green-coder·refactor-coder는 삭제하지 않는다.** 단독 스킬(gx-green·gx-refactor)과 gx-ralph-iterate가 사용한다. SKILL.md Agent 팀 표에 "gx-tdd 파이프라인에서는 호출하지 않는다 — 단독 스킬·ralph 루프 전용"으로 표기한다 (deprecated 아님).

### T2. 테스트 실행 전략 — "iterating은 focused, full은 경계에서 1회"

원본 `implementer-prompt.md:47-48`: "run the focused test for what you're changing; run the full suite once before committing, not after every edit."

**focused 집합의 정의 (M-5)**: 현재 태스크의 대상 테스트 + **이번 파이프라인 실행에서 이전 태스크들이 만든 신규 테스트 전부** (누적). 태스크 간 회귀는 이 집합이 즉시 잡고, 기존 스위트 회귀만 경계 실행으로 밀린다.

**focused 실행 명령의 SSOT (C-5)**: `.claude/config.json`의 `projectTypes.{타입}`에 선택 필드 `focusedTest`를 신설한다 — 템플릿 문자열이며 `{files}` 플레이스홀더에 테스트 파일 경로(공백 구분)가 치환된다. 예: java-spring `"./gradlew test --tests {pattern}"`(gradle은 클래스 패턴 — `{pattern}`은 파일명에서 유도한 FQCN 글롭), node `"npx vitest run {files}"`. **미정의 폴백**: 해당 타입의 전체 `test` 명령을 사용하고 execution-log에 `"focused 미지원 — 전체 실행 폴백"`을 기록한다 (현행 동작으로 안전 후퇴). 파급: config 기본 템플릿, `gx-setup`의 projectTypes 등록 절차와 `references/project-type-hints.md`에 focusedTest 힌트 추가, 린트의 config 키 검사에는 **선택 필드**로만 언급 (필수 검사 추가 없음).

| 시점 | 현행 | 변경 |
|------|------|------|
| verify_red | 오케스트레이터가 대상 테스트 직접 실행 (실패 목격) | **유지** |
| implementer 작업 중 | green-coder·refactor-coder가 전체 테스트 반복 | **focused 집합만** 실행. 전체 스위트 실행 금지 (프롬프트 지시) |
| verify_implement | verify_green(전체)+verify_refactor(전체) | 오케스트레이터가 **focused 집합 1회 직접 실행** — 통과 목격 + `test-count` 취득 (C-6). verify_red와 대칭으로 증거 주체가 오케스트레이터다. 전체 스위트는 돌리지 않는다 |
| 사이클 전체 종료 | (없음 — 태스크마다 전체) | **전체 모드**: phase-review Step 0 Mechanical Gate가 종료 회귀를 겸한다 (추가 실행 없음). **핵심 모드·`--phase implement` 단독(I-1)**: Step 4(사이클 완료 보고) 직전에 전체 테스트 1회 실행 |
| verify 게이트 | 전체 실행 | 유지 (verify 계약·지문 불변) |

결과: 전체 스위트 실행 = 기준선(Step 0.5) 1 + 경계 회귀(Mechanical Gate 또는 Step 4 직전) 1 + verify 1 = **3회** (현행 10~14회).

**무결성 기준선 재정의 (C-6)**:
- `test-file-hash`: 현행 유지 (verify_red 기록, verify_implement 대조 + 이전 태스크 해시 재검증).
- `test-count`: verify_implement의 **오케스트레이터 직접 focused 실행 결과**에서 취득·기록한다. 대조 대상은 같은 실행 방식의 직전 값이다. 전체 스위트 수 기반 정의는 폐기한다.
- porcelain 스냅샷: T8 참조.

**트레이드오프 명시**: 기존 스위트에 대한 회귀 발견이 경계 실행으로 늦어진다. 완화는 focused 누적 집합이며, 경계에서 잡힌 회귀는 Mechanical Gate의 기존 수정 경로(T3에서 주체만 implementer로 교체)가 처리한다.

### T3. 리뷰 통합 — reviewer 1석 (spec + quality 한 패스)

원본 task-reviewer(`task-reviewer-prompt.md:94`·`:115`)는 spec 검증(Part 1)과 품질 검증(Part 2)을 한 리뷰어가 한 번에 수행하고 verdict만 둘로 낸다. spec→quality 순차 분리는 gx-tdd의 발명이며 리뷰 왕복과 FAIL 루프 깊이를 2배로 만든다.

`agents/reviewer.md`를 신설한다:

- **Part 1 (spec)**: 현행 spec-reviewer 계약 그대로 — AC 충족 매트릭스(✅/⚠️/❌), 설계 범위 이탈, `spec_verdict` 블록.
- **Part 2 (quality)**: 현행 quality-reviewer 계약 그대로 — Critical/Important/Minor + `[동작결함|동작불변]` 마커, `quality_verdict` 블록. **Part 1이 FAIL이어도 Part 2를 수행한다** — 재구현 라운드에 품질 지적을 함께 전달한다 (미충족 AC 관련 지적은 "재구현 대상" 표기로 구분).
- **모델**: `model: opus` (quality-reviewer 승계). 도구: Read, Glob, Grep — 읽기 전용. **따라서 T5의 report 파일 Write 계약은 reviewer에 적용하지 않는다** (M-8). reviewer의 반환은 현행 계약 유지: 최종 메시지가 리뷰 전문이며 기계 판정 블록으로 끝난다. 오케스트레이터가 trust-ledger에 요약을 기록한다.
- **"Do Not Trust the Report"** (T6-3) 포함.

**Iron Law 개정 (I-9)**: 기존 `NO QUALITY REVIEW UNTIL SPEC COMPLIANCE CONFIRMED`를 다음 리터럴로 교체한다:

```
NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED
```

(한 리뷰어 내부에서 Part 1 → Part 2 순서 강제. spec FAIL이어도 Part 2는 수행하되 verdict 순서는 불변.) 재명시 지점: `phase-review.md:5-10`(헤더), `:96` 부근(통합 Step의 프롬프트 절대 규칙), `:428-429`(금지 사항), `gx-tdd/SKILL.md:280`(Phase 개요 표), `:286`(핵심 차별점), `:639`(병렬 실행 규칙). 여섯 곳 모두 이 리터럴 또는 그 요약("Part 1 verdict 선행")으로 통일한다.

phase-review의 구조 변경:
- Step 2(spec) + Step 3 Task A(quality) → **Step 2: reviewer + security-auditor 병렬 1회**. security-auditor 병렬 유지.
- **Step 0 (Mechanical Gate)의 수정 주체 교체 (C-4)**: `:43`의 green-coder 디스패치 → **implementer** (빌드 에러 전달, "진행 중 GREEN의 연장 — 새 RED 불필요" 논리 유지). `:55`의 green-coder(깨진 테스트 통과)·refactor-coder(롤백) → **implementer** (수정/롤백 모드 명시). 테스트 파일 무단 수정 감지·원복 규칙 유지. **Step 0의 1회 재시도는 T4 fix 라운드 카운터에 포함하지 않는다** (라운드는 리뷰 findings 수정 전용).
- Step 4의 refactor_only 수정 주체: refactor-coder → **implementer** (정리 모드 — 정리 대상은 리뷰 findings, GREEN 기준선은 Step 0 통과 결과. `SKILL.md:57`의 "Step 2-F 포인터 참조" 드리프트 주의를 이에 맞게 갱신 — I-7).
- 결과 처리(분류·라우팅·기계 판정 파싱·상충 시 FAIL 규칙)는 현행 유지.

**spec-reviewer·quality-reviewer는 gx-tdd에서 미호출로 전환한다.** 실호출처가 `phase-review.md:99`·`:186`뿐임을 전수 grep으로 확인했다. 두 파일은 잔류시키고 (린트 opus 전수 대조 관계는 T9), Agent 팀 표에 T1과 같은 방식으로 표기한다.

### T4. fix loop 재설계 — resume 우선 + 모델 격상 + 5라운드

원본 `SDD SKILL.md:377-405`. 현행 "green-coder fresh 재호출 최대 2회 → 3회 실패 시 사이클 중단"(`phase-implement.md:293`)을 대체한다:

| 라운드 | 방식 | 모델 |
|--------|------|------|
| 1~3 | **같은 implementer를 재개** — 하네스가 서브에이전트 재개(후속 메시지)를 지원하면 그 방식, 지원하지 않으면 report 파일 경로를 실은 fresh 디스패치 (report가 영속 기억) | sonnet |
| 4~5 | **fresh + 모델 격상** — "이전 구현자가 N회 시도했다. report 파일에서 시도 내역을 읽어라" 프레이밍 | opus |
| 라운드 5 소진 | 사이클 중단 + 사용자 확인 (D1: AskUserQuestion — "수동 수정 후 계속 / 태스크 스킵(위험 수용, trust-ledger 기록) / 중단") | — |

- 매 라운드: implementer가 수정 → focused 재실행 → fix report를 같은 report 파일에 **append** → 짧은 상태 반환. 오케스트레이터는 verify_implement를 재수행한다.
- **eco 프로파일과의 관계 (I-2)**: 격상은 "실패의 대응"으로 **프로파일과 독립**이다. eco 세션에서도 라운드 4~5는 opus로 격상한다. eco의 하향 규칙(`SKILL.md:463`)은 초기 디스패치 모델에 적용되는 것으로, 이 격상과 충돌하지 않음을 해당 절에 한 문장으로 명시한다.
- 정체 감지와의 우선순위: 현행 "재호출 상한 소진 시 격상 경로 우선"(`phase-implement.md:366`)을 "라운드 4 진입(모델 격상)이 DIMINISHING_RETURNS 에스컬레이션보다 우선하며, 라운드 5 소진 시 에스컬레이션·중단 판정"으로 갱신한다.
- 무결성 위반(테스트 무단 수정) 재호출 1회 제한은 라운드 체계와 **별도 유지** (위반은 실패가 아니라 계약 위반).

**린트 수정 (C-2)**: `lint-consistency.sh:72-73`의 `grep -q "최대 2회" phase-implement.md` 검사를 `grep -q "라운드 5" phase-implement.md`(fix 라운드 상한 리터럴)로 교체한다. phase-implement 본문에 `"라운드 5"` 리터럴이 위 표와 소진 규칙에 존재해야 한다. **gx-green/SKILL.md의 "최대 2회" 검사(`:74-75`)는 유지한다** — 단독 스킬은 현행 계약이며, 파이프라인과 단독 스킬의 상한이 갈라진다는 드리프트 주의를 SKILL.md에 추가한다 (I-7).

### T5. report 파일 계약 + 4-status 보고

원본 `implementer-prompt.md:128-149`(Report Format). 에이전트 전문 출력이 오케스트레이터 컨텍스트에 누적되어 긴 파이프라인에서 압축→라우팅 실패를 유발하는 문제의 해법.

- **report 파일**: `${DEV_DIR}/reports/t{N}-red.md`, `${DEV_DIR}/reports/t{N}-impl.md`. `{N}`은 Step 1 태스크 표의 태스크 번호. **디렉토리는 오케스트레이터가 Step 1(태스크 분해) 완료 시 `mkdir -p ${DEV_DIR}/reports`로 생성한다** (M-7). fix 라운드는 `t{N}-impl.md`에 append.
- **적용 대상**: 쓰기 도구를 가진 구현 에이전트(red-writer, implementer)만. **reviewer는 읽기 전용이므로 제외** (M-8, T3 참조).
- **반환 계약 (15줄 이내)**: `Status` / 변경 파일 목록 / 테스트 1줄 요약 (예: `"3/3 pass (focused)"`) / 우려사항 / report 경로.
- **Status 4종**: `DONE` | `DONE_WITH_CONCERNS`(완료했으나 의심 — 오케스트레이터가 report의 우려를 읽고 정정 또는 진행 판정) | `NEEDS_CONTEXT`(정보 부족 — 보강 후 재디스패치. 현행 red-writer의 "설계서 인터페이스 불충분" 보고를 이 status로 흡수) | `BLOCKED`(수행 불가 — 컨텍스트 보강 / 모델 격상 / 태스크 분할 / 설계 재확인 중 오케스트레이터 판정).
- **인계는 경로로**: red → implementer 인계 시 테스트 코드·실패 메시지를 인라인으로 붙이지 않고 `t{N}-red.md` 경로를 전달한다. reviewer에게는 brief(태스크 표 행 + AC)·report·DIFF_FILE **경로**를 전달한다.
- **state.md 계약 문자열 확정 (I-4)**:
  - `current-step` 리터럴: `"RGR T{N}: RED"`(유지) / `"RGR T{N}: IMPLEMENT"`(신설, 구 GREEN·REFACTOR 대체) / `"RGR T{N}: FIX R{r}"`(fix 라운드).
  - `steps.implement`의 태스크 하위 키: `red`, `impl` (구 `green`·`refactor` 대체).
  - 태스크 필드 추가: `fix-round: {r}/5` (fix 진입 시), `report: reports/t{N}-impl.md`.
  - `--resume` 매칭 표를 이 리터럴로 갱신: `"RGR T{N}: IMPLEMENT"` → 해당 태스크 implementer 재디스패치(red report 유효), `"RGR T{N}: FIX R{r}"` → 라운드 r부터 재개.
- SKILL.md "Agent 결과 전달 규칙"을 이 계약으로 개정한다. execution-log에는 현행처럼 1줄 요약만.
- `.dev/` 산출물 공유 정책에 따라 reports/도 커밋된다. porcelain 대조의 `.dev/` 제외 규칙이 그대로 적용된다.

### T6. 프롬프트 보강 3종

1. **red-writer — "Name the Break" + The Mutation Check** (`writing-good-tests.md:20-79` Principle 1, `:157-169` The Mutation Check — 별도 절이다, M-3): 테스트 본문 작성 전 "이 테스트를 실패시키는 프로덕션 변경"을 명명 (명명 불가 = 관찰 가능한 동작으로 재설계), 미러 assertion(기대값을 대상 코드로 계산) 금지, change detector(상수값·문구·내부 구조만 검증) 금지. 완료 전 mutation check — 원본 변이 **5종 그대로**: 잘못된 상수/인자, 잘못된 분기 핸들러, 상태 변경·부작용 누락, 빈/기본 반환, 0·빈값·nil·비인가·malformed 입력 검증 누락. `references/testing-anti-patterns.md`에 해당 절을 이식하고, `:7`의 출처 표기(`test-driven-development/testing-anti-patterns.md` — 6.3.0에 없는 파일)를 `writing-good-tests.md`로 정정한다 (M-6).
2. **implementer — self-review** (`implementer-prompt.md:92-117`): 보고 전 자기 diff를 완전성/품질/규율(YAGNI)/테스트 4관점으로 검토, 발견 즉시 수정 후 보고.
3. **reviewer — "Do Not Trust the Report"** (`task-reviewer-prompt.md:64-71`): 구현자 report의 주장·자기 정당화("YAGNI라서 뺐다")를 미검증 주장으로 취급하고 diff로 검증. 테스트 재실행 금지(`:75-82`) — report와 verify_implement의 실행 증거가 있으며, 구체적 의심이 있을 때만 focused 1회.

### T7. 같은 모양 소형 AC 배칭

원본 `SDD SKILL.md:223-229` (Batch small same-shape work). phase-implement Step 1에 반영:

**규칙 1 개정 (I-5)** — `phase-implement.md:101`의 태스크 조건 1을 다음 리터럴로 교체한다:

> 1. **단일 AC 또는 단일 컴포넌트**에 매핑된다. 단, **같은 패턴의 소형 변경으로 환산되는 AC들**(동일 검증 로직의 필드별 반복, 동일 형태의 매핑 추가 등)은 하나의 태스크로 배칭할 수 있다 — RED는 테이블 드리븐 또는 케이스별 테스트를 한 파일에 작성하고, 한 번의 R→I 사이클로 처리하며, 태스크 표의 AC 매핑에 `AC-2~AC-4 (배칭)` 형태로 표기해 승인 게이트에서 확인받는다.

분리 기준은 원본을 승계한다: 독자적 판단·독자적 테스트 전략·독자적 리뷰 표면이 필요한 작업만 태스크를 분리한다.

### T8. porcelain 스냅샷 범위 축소

verify_red가 저장하는 `rgr-t{N}-porcelain.txt`의 **대조 규칙**을 좁힌다 (스냅샷 취득 명령은 현행 유지 — `git status --porcelain`, svn은 `svn status`):

- 대조 시 `.dev/` 경로 라인 제외 (현행 유지).
- **추가**: 대조 대상을 **테스트 파일 라인만으로 필터**한다. 판별 글롭은 phase-implement Step 0.5의 레이어별 하네스 게이트가 쓰는 테스트 파일 글롭(`**/*test*`·`**/*Test*`·`**/*spec*` 계열)을 재사용한다 — 무결성 검증의 목적이 "다른 테스트 파일 변경 감지"이므로 프로덕션·아티팩트 라인은 비교하지 않는다.
- svn 분기: `svn status` 출력에 같은 필터를 적용한다 (경로 컬럼 기준. `phase-implement.md:238`의 svn 규칙과 대칭 유지).

효과: 빌드 아티팩트·무관 파일 출현으로 인한 무결성 오탐 제거.

### T9. 모델 라우팅 — 최소 강도 + 실패 시 격상

SKILL.md "모델 라우팅 원칙"에 추가한다:

- **최소 강도**: 각 역할을 감당하는 가장 약한 모델을 쓴다. 단 "턴 수가 토큰 단가를 이긴다" — 산문 요구사항 기반 구현·리뷰어는 sonnet이 바닥 (haiku 강등 금지 규칙 유지).
- **격상은 실패의 대응**: fix loop 라운드 4~5에서만 opus 격상 (T4). 프로파일과 독립.
- **eco 하향 대상 (C-1)**: `design-critic·test-architect·quality-reviewer·reviewer` — reviewer를 **추가**하고 quality-reviewer를 **잔류**시킨다. 린트(`lint-consistency.sh:309-315`)가 `agents/*.md`의 `model: opus` 전수를 eco 목록과 대조하므로, opus인 채 존치되는 quality-reviewer를 빼면 FAIL이다. quality-reviewer는 gx-tdd가 디스패치하지 않으므로 목록 등재는 실행에 영향이 없다 — 등재 사유를 SKILL.md 해당 절에 각주로 남긴다. architect 유지 원칙 불변.

## 파이프라인 before/after (전체 모드, AC 4개·태스크 4개 기준)

| Phase | 현행 | 변경 후 |
|-------|------|---------|
| requirements | product-owner 1 | 동일 |
| design | architect + (critic ∥ test-architect) | 동일 |
| implement | (red+green+refactor)×4 = 12 디스패치, 전체 테스트 9~12회 | (red+implementer)×4 = **8 디스패치**, 전체 테스트 **1회** (Step 0.5 기준선. 이후는 focused만 — M-4) |
| review | spec → (quality ∥ security) = 3 디스패치 | (reviewer ∥ security) = **2 디스패치** + Mechanical Gate 전체 1회 |
| complete | verify + product-owner 인수 | 동일 (verify 전체 1회) |
| **합계** | 디스패치 ~20, 전체 테스트 10~14회 | 디스패치 **~15**, 전체 테스트 **3회** |

확인 게이트 수는 변하지 않는다 (D1).

## 영향 범위 (실측 grep 기반 — C-7)

### 신설
| 파일 | 내용 |
|------|------|
| `agents/implementer.md` | T1, T5, T6-2 |
| `agents/reviewer.md` | T3, T6-3 |

### 수정 — 스킬 본문
| 파일 | 변경 |
|------|------|
| `gx-tdd/phases/phase-implement.md` | Step 1(배칭 규칙 1 개정 + reports/ mkdir), Step 2 재작성(2-R/2-I), verify_implement(T2·C-6), fix loop(T4, `"라운드 5"` 리터럴), report 계약(T5), Step H 수정 경로의 implementer 교체, 부록 A(구 2-G/2-F 트리오 프롬프트), state.md 추적·--resume 절의 새 리터럴 |
| `gx-tdd/phases/phase-review.md` | Step 0 수정 주체 implementer 교체(C-4), Step 2+3 통합(T3), Iron Law 리터럴 교체(:5-10·:96·:428-429), Step 4b 주체 교체·포인터 문구(:361-362) 갱신 |
| `gx-tdd/phases/phase-setup.md` | `:92` standard 프로파일 안내의 에이전트 나열(quality-reviewer → reviewer 반영) |
| `gx-tdd/phases/phase-complete.md` | **무변경** (I-6) — Step -2 본 조건·Step 0은 에이전트 이름 비의존 확인 완료. `:26`의 트리오 언급은 ralph 예외 전용으로 트리오 유지이므로 불변 |
| `gx-tdd/SKILL.md` | frontmatter description(:4 "리뷰(spec→quality)" 문구), 차별점 표(:23), 드리프트 주의(:53·:57·:60·:69 — I-7 갱신안 아래), Agent 팀 표(:214-270), Phase 개요 표(:279-280), 핵심 차별점(:285-286), core 분기(:298), Agent 팀 강제(:376), deprecated Iron Law(:380-382), 모델 라우팅·모델 프로파일(:457-466, I-2 문장 포함), Agent 결과 전달 규칙(:487), state.md 스키마·예시(:513-561, I-4 리터럴), Context Slicing(:606-618 — implementer·reviewer 행 추가), 병렬 실행 규칙(:635-639), 린트 번호 표기 2곳(:62 "[23/23]"·:71 "[14/25]" — I-8) |
| `gx-ralph-iterate/SKILL.md` | `:89` 참조 문구를 "Step 2-R 및 부록 A의 G/F 디스패치 프롬프트"로 갱신 (C-3). 트리오 유지 |
| `gx-tdd/references/testing-anti-patterns.md` | Principle 1 + The Mutation Check 이식, 출처 표기 정정 (T6-1, M-6) |

**드리프트 주의 목록(I-7) 갱신안**: `:57` "Step 4b는 Step 2-F 포인터 참조" → "Step 4b는 implementer 정리 모드 디스패치 — 부록 A와 무관"으로 교체. `:60` 테스트 무결성 3중 중복 → implementer 포함 4중으로 재정의. `:69` 무결성 기준선 규약 → T2·T8의 새 정의(focused 직접 실행 test-count·테스트 파일 필터 porcelain)로 교체. 신규 항목: "fix 라운드 상한 — 파이프라인 `라운드 5` ↔ 단독 gx-green `최대 2회` (의도적 분기)".

### 수정 — 에이전트·설정·규칙
| 파일 | 변경 |
|------|------|
| `agents/green-coder.md` `refactor-coder.md` | 헤더에 "gx-tdd 파이프라인 미호출 — 단독 스킬·gx-ralph 전용" 명시 |
| `agents/spec-reviewer.md` `quality-reviewer.md` | 같은 방식 표기 (C단계 정리 후보. quality-reviewer의 `model: opus`는 유지 — T9) |
| `agents/test-architect.md` | spec-reviewer/quality-reviewer 언급 문구 정합 |
| `.claude/config.json` | `projectTypes.*.focusedTest` 신설(C-5), `contextLimits`에 `implementer`·`reviewer` 추가(:64-79 — `SKILL.md:629`가 소비) |
| `.claude/rules/skill-routing.md` | "TDD 보조 스킬" 절의 "red-writer/green-coder/refactor-coder 디스패치" 문구를 2석 기준으로 갱신 |
| `gx-setup/SKILL.md` + `references/project-type-hints.md` | focusedTest 등록 절차·힌트 (C-5) |

### 수정 — 검증·문서
| 파일 | 변경 |
|------|------|
| `scripts/lint-consistency.sh` | [3/25] `"최대 2회"`→`"라운드 5"` 교체(phase-implement 대상만, C-2), REFACTOR_FILES(:64) 3중 동기에 implementer 추가, [14/25] eco 목록 대조는 T9 목록으로 자동 충족 확인, spec/quality→reviewer 참조 검사 추가, **신규 [26/26]**: report 계약 문구(`reports/t{N}-impl.md`·4-status) 존재 검사. 총 26항목 — 전체 echo의 분모를 26으로 일괄 갱신 (I-8) |
| `tests/golden-scenarios.md` | S9("red/green/refactor-coder·spec/quality-reviewer만 디스패치")·S17("quality-reviewer sonnet 오버라이드 관찰")을 2석·reviewer 기준으로 갱신 |
| `.claude/rules/release.md` `.claude/rules/harness-codex.md` | 린트 번호 표기 "[1/26]"·"[15/26]" — 분모 26 갱신 후 **결과적으로 일치**하므로 불변 확인만 (I-8. 현행 스크립트 25항목과의 기존 드리프트가 이번 갱신으로 해소됨) |
| `README.md` `index.html` `docs/` 파생 | spec/quality-reviewer·트리오 언급을 grep 전수 후 정합 (구현 시 `grep -rn "spec-reviewer\|quality-reviewer\|green-coder\|refactor-coder" README.md index.html docs/` 결과를 체크리스트로) |
| `CHANGELOG.md` + 버전 3파일 | 릴리스 규칙에 따라 갱신 |

## 하위 호환

| 조건 | 동작 |
|------|------|
| 구 세션 `--resume` (state.md에 `"RGR T{N}: GREEN"`/`"REFACTOR"` 기록) | 해당 태스크를 implementer 재디스패치로 이어받는다 — red 산출물(테스트 파일)은 유효하므로 RED 재실행 불필요. **reports/가 없으므로 이 재개에 한해 인라인 인계를 허용**하고 (I-3) execution-log에 `"2석 전환 재개 — 인라인 인계"` 기록. 이후 라운드부터 report 계약 적용 |
| gx-ralph 세션 | 트리오 유지 + 부록 A로 프롬프트 소스 보존 (C-3). phase-complete Step -2 ralph 예외 판정 불변 |
| 단독 `/gx-green` `/gx-refactor` `/gx-red` | 변경 없음 (에이전트·"최대 2회" 계약 존치) |
| verify 게이트·지문·커밋/PR 게이트·훅 G3 | 영향 없음 (T2는 implement 내부 실행 전략만 변경) |
| focusedTest 미등록 프로젝트 | 전체 test 명령 폴백 — 현행과 동일 동작 (C-5) |

## 도입하지 않는 것 (근거 기록)

| 항목 | 사유 |
|------|------|
| R1 Rulings, not stalls (확인 게이트 제거) | **D1** — 게이트는 의도된 협업 접점 |
| 태스크 간 병렬 실행 | 태스크가 대개 컴파일 의존 체인이라 이득이 작고, 전체 테스트 공유 자원 문제가 남는다 |
| implementer 1석 (원본 원형) | red-writer 격리(구현 편향 차단)가 gx-tdd의 핵심 차별점 — D2에서 2석 확정 |
| 태스크별 커밋 (원본 SDD) | gx-commit 라우팅·verify 게이트 체계와 충돌. 커밋은 현행대로 phase-complete 1회 |
| gx-ralph 2석 전환 | 이번 범위 외 — 부록 A로 트리오 소스 보존, C단계 검토 |

## 구현 순서

| 단계 | 범위 | 배포 단위 |
|------|------|-----------|
| **A** | T1 + T2 + T4 + T5 + T6(red/implementer) + T7 + T8 — `agents/implementer.md` 신설, phase-implement 재작성(부록 A 포함), ralph 참조 문구 갱신, config(focusedTest·contextLimits), SKILL.md 해당 절, 린트([3]·REFACTOR_FILES·[26/26]·분모 26), golden-scenarios S9 | **하나로 배포.** 2석 전환·테스트 전략·report 계약·ralph 참조 보존은 서로 맞물려 쪼갤 수 없다 |
| B | T3 + T6(reviewer) + T9 — `agents/reviewer.md` 신설, phase-review 재작성(Step 0 주체 교체 포함), eco 목록, phase-setup :92, golden-scenarios S17 | 별도. A만으로도 implement 단축이 성립한다. **주의**: A 배포 시점의 phase-review Step 0은 아직 green-coder를 참조하므로, A에서 Step 0 주체 교체만 선반영한다 (implementer가 A에서 생기므로 가능) |
| C | gx-ralph-iterate 2석 전환 검토, spec/quality/green/refactor 에이전트 정리 여부, README·index.html·docs 파생 사본 전수 정합 | 별도 (검토 후) |
