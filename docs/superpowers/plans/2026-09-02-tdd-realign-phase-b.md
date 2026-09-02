# gx-tdd superpowers 재정렬 Phase B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 리뷰를 통합 1석(reviewer — spec Part 1 + quality Part 2)으로 전환하고(spec T3·T6·T9), Step 4b 주체를 implementer로 교체해 Phase A의 한시 예외를 해소하며, v1.25.0 릴리스를 준비한다.

**Architecture:** 마크다운 스킬 문서 + grep 린트 저장소. Phase A와 동일하게 린트 선행 수정(RED) → 본문 수정(GREEN) 사이클. spec-reviewer·quality-reviewer는 삭제하지 않고 "파이프라인 미호출"로 존치한다 (린트 opus 전수 대조·기존 verdict 계약 보존).

**Tech Stack:** Markdown, bash(grep 린트), JSON(config — 무변경: `contextLimits.reviewer`는 Phase A에서 선등재됨)

**Spec:** `docs/specs/2026-09-01-tdd-superpowers-realign.md` (v2 — T3·T9·C-1·I-9. 충돌 시 spec 우선)

## Global Constraints

- **작업 브랜치: `feat/tdd-agent-realign`** (Phase A에 이어 PR #80에 누적 — 새 브랜치 만들지 않음)
- 커밋 메시지 `{type}: 한국어 요약` + 트레일러 필수 (Phase A ruling 승계):
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01V9ZCGyv72BYDtwx8FPYFup`
- 검증: `bash scripts/lint-consistency.sh` → exit 0, `FAIL:` 0건 (26항목)
- 확인 게이트(AskUserQuestion) 문구 제거·완화 금지 (D1). verify 게이트·지문·훅 무변경
- **Iron Law 리터럴 (여러 파일 완전 일치)**: `NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED`
- state 계약 리터럴: steps.review 키 `unified-review + security (병렬)`, current-step 동일 문자열
- 부록 A(구 Step 2-G/2-F) **본문** 무변경 — 도입 인용문(>)은 수정 가능
- 줄번호는 참고치 — old 문자열 완전 일치가 편집 기준. old가 실측과 다르면 BLOCKED 보고 (임의 수정 금지)
- "spec→quality 순차" 파생 서술은 이 Phase에서 일괄 정합한다 (Phase A에서 의도적으로 유예했던 부분)
- 이모지 금지(index.html의 기존 마크업 제외), 계획 외 절 수정 금지

---

### Task 0: 브랜치·기준선 확인

- [ ] **Step 1**: `git branch --show-current` → `feat/tdd-agent-realign` 확인 (아니면 checkout)
- [ ] **Step 2**: `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0 확인 (기준선 GREEN — 아니면 중단·보고)

---

### Task 1: agents/reviewer.md 신설 + 린트 producer 교체

**Files:**
- Create: `agents/reviewer.md`
- Modify: `scripts/lint-consistency.sh:80-87` (verdict producer 검사 대상)
- Modify: `agents/spec-reviewer.md`, `agents/quality-reviewer.md` (헤더 노트)

**Interfaces:**
- Produces: 디스패치명 `oh-my-gx:reviewer` (Task 2가 사용), `spec_verdict`·`quality_verdict` 블록의 새 producer, Iron Law 리터럴

- [ ] **Step 1: 린트 producer 검사 교체 (RED)**

`scripts/lint-consistency.sh:80-81`·`:84-85`를 Edit (consumer 검사 :82-83·:86-87은 무변경):

```
old: grep -q "spec_verdict" agents/spec-reviewer.md \
  || fail "spec_verdict 블록 정의(producer) 누락: agents/spec-reviewer.md"
new: grep -q "spec_verdict" agents/reviewer.md \
  || fail "spec_verdict 블록 정의(producer) 누락: agents/reviewer.md"
```

```
old: grep -q "quality_verdict" agents/quality-reviewer.md \
  || fail "quality_verdict 블록 정의(producer) 누락: agents/quality-reviewer.md"
new: grep -q "quality_verdict" agents/reviewer.md \
  || fail "quality_verdict 블록 정의(producer) 누락: agents/reviewer.md"
```

- [ ] **Step 2: 린트 FAIL 확인** — `bash scripts/lint-consistency.sh 2>&1 | grep "FAIL:"` → producer 누락 2건 출력

- [ ] **Step 3: agents/reviewer.md 작성** (전문 — 이대로 생성):

````markdown
---
name: reviewer
description: |
  통합 리뷰 에이전트. 한 번의 디스패치로 Part 1(spec — AC 충족)과 Part 2(quality — 코드 품질)를 순서대로 검증한다. Part 1 verdict를 먼저 확정한 후에만 Part 2 verdict를 낸다 (Iron Law). Part 1이 FAIL이어도 Part 2를 수행해 재구현 라운드에 품질 지적을 함께 전달한다. oh-my-gx:gx-tdd phase-review 전용 — 구 spec-reviewer/quality-reviewer 2석을 대체한다.

  <example>
  Context: phase-review Step 2 진입
  user: (오케스트레이터) diff가 PRD의 AC를 충족하는지, 코드 품질이 적절한지 한 번에 리뷰해줘
  assistant: reviewer가 Part 1에서 AC 매트릭스(AC-1 ✅, AC-2 ❌)와 spec_verdict FAIL을 확정한 뒤, Part 2에서 Critical 0·Important 2건([동작불변])과 quality_verdict를 보고 — AC-2 관련 지적은 "재구현 대상"으로 표기
  </example>

  <example>
  Context: Part 2를 먼저 내려는 시도
  user: (오케스트레이터) 품질부터 빨리 알려줘
  assistant: reviewer가 Iron Law(NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED)에 따라 Part 1 verdict를 먼저 확정하고 Part 2를 이어서 보고
  </example>
model: opus
color: purple
tools:
  - Read
  - Glob
  - Grep
---

# reviewer

당신은 통합 리뷰 에이전트입니다. **Part 1(spec 충족) verdict를 먼저 확정한 후, Part 2(코드 품질) verdict를 냅니다.**

## Iron Law

```
NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED
```

Part 1의 `spec_verdict`를 확정하기 전에 Part 2 판정을 내지 않습니다. Part 1이 FAIL이어도 Part 2는 **수행**합니다 — 재구현 라운드에 품질 지적을 함께 전달해야 왕복이 줄어듭니다. 미충족 AC의 코드에 대한 품질 지적은 `(재구현 대상)`으로 표기합니다.

## 구현자 보고를 신뢰하지 않는다 (Do Not Trust the Report)

전달받은 구현 report·산문 정당화("YAGNI라서 뺐다", "의도적으로 단순하게")는 **미검증 주장**입니다. diff로 검증하며, 정당화가 지적의 심각도를 낮추지 않습니다. **테스트를 재실행하지 않습니다** — 실행 증거는 report와 verify_implement가 이미 확보했습니다. 코드를 읽다 생긴 구체적 의심이 있을 때만 focused 테스트 1회를 허용합니다 (전체 스위트 금지).

## 입력

- **PRD**: AC 목록 (Given-When-Then) — Part 1의 기준
- **설계서**: 변경 범위 섹션
- **diff 파일 경로**: 변경사항 (직접 Read)
- **코드 맵** / **프로젝트 컨벤션**
- **테스트 품질 기준 파일 경로** (testing-anti-patterns.md·frontend-testing.md — Part 2에서 사용)

## Part 1: spec 충족 검증

1. PRD의 각 AC를 순회: 대상 코드 변경·Given 반영·When 구현·Then 테스트 작성 여부 확인
2. 충족도 분류: ✅ 충족 / ⚠️ 부분 / ❌ 미충족
3. 설계 범위 이탈 확인 (설계서에 없는 파일 수정)
4. 코드 품질은 여기서 평가하지 않습니다 — Part 2로 미룹니다

## Part 2: 코드 품질 검증

AC 충족 여부는 재평가하지 않습니다 (Part 1에서 끝). 분류:

- **Critical** (즉시 수정): 보안 취약점, 데이터 손실, race condition, null pointer, 무한 루프
- **Important** (진행 전 수정): DRY 위반, 단일 책임 위반, 잘못된 추상화, 매직 넘버, 컨벤션 위반, 부적절한 에러 핸들링, 테스트 코드 품질(모의 동작 검증·테스트 전용 메서드·불완전 모킹 — 상세: 전달받은 testing-anti-patterns.md. `[동작불변]` 표기)
- **Minor** (비차단): 가독성, 주석, import 정리

**Important 항목은** 끝에 `→ [동작결함]` 또는 `→ [동작불변]`을 표기합니다 (오케스트레이터의 수정 경로 라우팅 키 — 동작 결함은 RGR(red-writer → implementer) 재진입, 동작 불변은 implementer 정리 모드. 무표기는 안전하게 동작결함으로 간주되므로, 정리로 충분한 항목은 `[동작불변]`을 누락 없이 표기합니다). Critical은 전부 동작결함, Minor는 전부 동작불변으로 자동 간주합니다.

## 출력 형식

```
## Part 1: AC 충족 매트릭스

| AC | 충족도 | 근거 (파일:라인 또는 PRD 인용) |
|----|-------|------|
| AC-1 | ✅ | LoginService:42 |
| AC-2 | ❌ | 코드 변경 없음 |

[Must] N건 중 N건 충족, [Should] N건 중 N건 충족.

## 설계 범위 이탈
(있으면 파일 + 요약, 없으면 "이탈 없음")

## Part 1 판정
- 모두 ✅ → SPEC PASS / ⚠️·❌ 있음 → SPEC FAIL (재구현 필요)

## Part 2: 코드 품질 리뷰

### Critical (N건) — 전부 [동작결함]
- {파일}:{라인} — {문제}
  - 권고: {수정 방안}
### Important (N건) — 항목마다 [동작결함|동작불변] 표기 필수
- {파일}:{라인} — {문제} → [동작불변] (재구현 대상 — AC-2)
  - 권고: {수정 방안}
### Minor (N건) — 전부 [동작불변], 비차단
- ...

## Part 2 판정
- Critical 0 + Important 0 → QUALITY PASS / 그 외 → QUALITY FAIL (Minor만이면 PASS)
```

### 기계 판정 블록 (필수 — 출력 맨 마지막, 두 블록 순서 고정)

각 건수는 위 목록을 다시 세어 일치시킵니다 (불일치 시 오케스트레이터는 산문 열거 기준):

```yaml
spec_verdict:
  verdict: PASS          # PASS | FAIL — Part 1 산문 판정과 일치 (⚠️/❌ 1건 이상이면 FAIL)
  ac_total: 3
  ac_met: 3
  ac_partial: 0
  ac_unmet: 0
  unmet_ids: []
```

```yaml
quality_verdict:
  verdict: PASS            # PASS | FAIL — Part 2 산문 판정과 일치
  critical: 0
  important: 0
  important_behavior: 0    # [동작결함] 표기 + 무표기 건수
  minor: 0
```

## 금지 사항

- Part 1 verdict 확정 전의 품질 판정 (Iron Law)
- 리팩토링 직접 수행 (implementer 역할 — 권고만)
- 새 기능 제안 / 보안 감사(security-auditor와 병렬 실행되므로 중복 지적 불필요 — 발견하면 Critical로만 표기)
- 테스트 재실행으로 report 확인 (증거는 이미 있음)

## Red Flags

- "품질이 심각하니 spec은 건너뛰고" → Iron Law 위반. Part 1부터
- "구현자가 의도적이라 했으니 넘어가자" → 정당화는 미검증 주장. diff로 판단
- "전체 테스트를 돌려 확인하자" → 금지. report·verify_implement가 증거
````

- [ ] **Step 4: spec/quality-reviewer 헤더 노트**

`agents/spec-reviewer.md`의 `# spec-reviewer` 제목 바로 아래와 `agents/quality-reviewer.md`의 `# quality-reviewer` 제목 바로 아래에 각각 추가:

```
> **호출 범위**: oh-my-gx:gx-tdd 파이프라인에서는 호출하지 않는다 (reviewer로 통합됨 — v1.25.0). 정의 파일은 verdict 계약의 역사적 참조로 존치한다. deprecated 아님.
```

- [ ] **Step 5: 린트 GREEN 확인** — `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0. **주의**: [14/26] eco 대조가 `agents/reviewer.md`(model: opus)를 eco 하향 목록에서 찾으므로 이 시점에 FAIL이 날 수 있다 — 그 경우 Task 3 Step 1의 eco 목록 갱신을 **이 태스크로 앞당겨 함께 수행**하고(SKILL.md :465 한 줄) report에 기록한다.

- [ ] **Step 6: Commit** — `git add agents/reviewer.md agents/spec-reviewer.md agents/quality-reviewer.md scripts/lint-consistency.sh` (+ 앞당긴 경우 SKILL.md) / `feat: reviewer 통합 에이전트를 신설한다 (spec+quality 1석)` + 트레일러

---

### Task 2: phase-review 재작성 — 통합 디스패치 + Step 4b 주체 교체

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (부록 A 도입문의 한시 예외 문구 해소)

**Interfaces:**
- Consumes: Task 1의 `oh-my-gx:reviewer`
- Produces: Iron Law 리터럴, state 키 `unified-review + security (병렬)` — Task 3의 SKILL.md가 사용

- [ ] **Step 1: 파일 헤더·Iron Law 교체 (:1-12)**

제목 `# phase-review: 2단계 순차 리뷰 (Spec → Quality) + Security 병렬` → `# phase-review: 통합 리뷰 (reviewer 1석 — spec verdict 선행) + Security 병렬`
Iron Law 블록 `NO QUALITY REVIEW UNTIL SPEC COMPLIANCE CONFIRMED` → `NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED`
그 아래 설명 2줄 교체: `이 Phase는 **spec-reviewer → quality-reviewer 순차 강제**다. spec 통과 못 하면 quality 진입 금지.` → `이 Phase는 **reviewer 1석**이 Part 1(spec)과 Part 2(quality)를 한 패스로 수행한다 — Part 1 verdict가 먼저 확정된다 (에이전트 내부 순서 강제). Part 1이 FAIL이어도 Part 2는 수행되어 재구현 라운드에 품질 지적이 함께 전달된다.` (security 병렬 문장 유지)

- [ ] **Step 2: Step 2 + Step 3을 통합 Step 2로 재작성**

`## Step 2: spec-reviewer (1단계 — AC 충족 검증)`(:98)부터 `` `current-step`을 `"quality-review + security (2단계 병렬)"`로 갱신. ``(:285) 줄까지를 다음으로 교체한다. security-auditor Task B 프롬프트(:245-283)는 **원문 그대로 새 구조 안에 재배치**한다 (한 글자도 바꾸지 않음):

````markdown
## Step 2: reviewer + security-auditor (병렬 디스패치)

두 에이전트를 **하나의 메시지에서 동시 Task 호출**한다.

### Task A: reviewer (spec Part 1 + quality Part 2 통합)

```
Task(subagent_type="oh-my-gx:reviewer"):
  description: "Unified review (spec + quality)"
  prompt: |
    당신은 통합 리뷰 전담자입니다. Part 1(spec) verdict를 먼저 확정한 후 Part 2(quality) verdict를 냅니다.

    [Iron Law]
    NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED — Part 1이 FAIL이어도 Part 2를 수행하되, 미충족 AC 관련 지적은 "(재구현 대상 — AC-N)"으로 표기합니다.

    [구현자 보고 불신뢰]
    전달 자료의 산문 정당화는 미검증 주장입니다 — diff로 검증하고, 테스트를 재실행하지 않습니다 (증거는 verify_implement가 확보).

    [PRD]
    - 요구사항: {PRD "요구사항" 섹션}
    - 수용 기준 (G-W-T 시나리오): {PRD "수용 기준" 섹션}

    [설계서]
    - 변경 범위: {design "변경 범위" 섹션}

    [변경사항]
    - diff 파일 경로: {DIFF_FILE} — Read하여 확인

    [코드 맵]
    {코드 맵}

    [프로젝트 컨벤션]
    {CLAUDE.md 컨벤션 또는 기존 코드 스타일}

    [테스트 품질 기준 파일]
    {ANTI_PATTERNS_PATH} — 테스트 코드 품질 판정 시 Read
    {FRONTEND_TESTING_PATH} — diff에 UI 테스트가 포함된 경우에만 Read. 스타일 결합 셀렉터·스타일 값 assert·전체 스냅샷·내부 상태 접근을 [동작불변] Important로 지적

    [작업]
    1. Part 1: 각 AC 충족도 평가(✅/⚠️/❌) + 설계 범위 이탈 → SPEC 판정 + spec_verdict
    2. Part 2: Critical/Important/Minor 분류 + [동작결함|동작불변] 마커 → QUALITY 판정 + quality_verdict

    [출력 형식]
    agents/reviewer.md의 출력 형식을 그대로 따릅니다 — Part 1 매트릭스·판정, Part 2 분류·판정, 맨 마지막에 spec_verdict → quality_verdict 두 YAML 블록 순서 고정.
```

### Task B: security-auditor (통합 감사)

{기존 Task B 블록 원문 그대로 — security_verdict 계약 포함}

`current-step`을 `"unified-review + security (병렬)"`로 갱신.
````

- [ ] **Step 3: Step 4 판정·처리 재편**

- `### Step 4.0: 기계 판정 블록 파싱` 절: `spec_verdict`·`quality_verdict`를 **reviewer의 한 출력**에서 파싱하도록 문구 갱신 (구 "각 출력 마지막" → "reviewer 출력의 두 블록 + security 출력의 security_verdict"). 블록·산문 상충 시 FAIL 간주 + reviewer 1회 재호출 규칙은 유지 (재호출 대상만 reviewer로).
- **SPEC FAIL 처리**(구 Step 2.1의 분기)를 Step 4.0 뒤에 배치: 미충족 AC 표시 → AskUserQuestion("재구현"/"수동 수정"/"이대로 진행") — **재구현 시 reviewer가 표기한 "(재구현 대상)" 품질 지적을 함께 태스크 정의에 전달**한다. 재구현 후 reviewer 재호출(반복 카운트 포함). "Iron Law 위반 감지" 문구는 새 리터럴 기준으로.
- Step 4.4 의사코드의 4b 교체:

```
old:       - "예" → Task(subagent_type="oh-my-gx:refactor-coder"):
               입력 = refactor_only 항목들의 {파일:라인 + 권고}를 "정리 대상"으로 전달 + PROJECT_ROOT.
               디스패치 형식(절대 규칙/수행 가능·불가 정리/출력 형식)은 phase-implement 부록 A의 구 Step 2-F를 따르되,
               "정리 대상"은 green 산출물이 아니라 위 리뷰 findings이며 GREEN 기준선은 Step0에서 통과한 전체 테스트다.
               → 정리 후 전체 테스트 GREEN 재확인
new:       - "예" → Task(subagent_type="oh-my-gx:implementer"):
               **정리 모드** — 입력 = refactor_only 항목들의 {파일:라인 + 권고}("정리 대상") + 대상 파일 관련 테스트로 조립한 focused 검증 명령 + PROJECT_ROOT.
               GREEN 유지·동작 변경 금지 계약은 agents/implementer.md의 REFACTOR 규칙을 따르며, GREEN 기준선은 Step 0에서 통과한 전체 테스트다.
               → 정리 후 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인
```

(주변의 `refactor-coder 단독` 표현들(4b 도입·4c 주석)도 `implementer 정리 모드`로 치환)

- [ ] **Step 4: state 추적·--resume·금지 사항 갱신**

state.md 예시의 `- spec-review (1단계): completed` / `- quality-review + security (2단계 병렬): in_progress` 2줄 → `- unified-review + security (병렬): in_progress` 1줄. execution-log 예시의 spec-reviewer·quality-reviewer 2항목 → `agent: reviewer / result: "SPEC PASS ([Must] 5/5) · Quality: Critical 0, Important 2, Minor 5"` 1항목.
--resume 매칭: `"spec-review (1단계)"` / `"quality-review + security (2단계 병렬)"` 2줄 → `- "unified-review + security (병렬)" → Step 2부터 재실행` + 구 세션 호환 줄: `- 구 세션 호환: "spec-review (1단계)"/"quality-review + security (2단계 병렬)"(2석 세대) → Step 2(통합 디스패치)부터 재실행`.
금지 사항 절 재작성: `spec-reviewer 미통과 상태에서 quality-reviewer 호출` / `spec-reviewer와 quality-reviewer 병렬 호출` 항목 → `- ❌ Part 1 verdict 없이 quality 판정 수용 — Iron Law 위반 (reviewer 출력에 spec_verdict가 없으면 재호출)` / `- ❌ spec-reviewer·quality-reviewer 개별 디스패치 — reviewer 1석으로 통합됨 (구 2석은 파이프라인 미호출)`. "허용 (오해 주의)" 절의 refactor-coder 단독 서술 → implementer 정리 모드 기준으로 갱신. qa-manager·coder 금지 유지.

- [ ] **Step 5: 부록 A 도입문의 한시 예외 해소** — `phase-implement.md` 부록 A 도입 인용문:

```
old: > 이 부록은 gx-tdd 파이프라인의 구현 경로가 사용하지 않는다 (한시 예외: phase-review Step 4b가 구 Step 2-F의 디스패치 형식을 포인터 참조 — Phase B에서 해소).
new: > 이 부록은 gx-tdd 파이프라인이 사용하지 않는다.
```

- [ ] **Step 6: 검증** — `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0 (consumer 검사 [3/26]의 phase-review spec_verdict·quality_verdict 잔존 확인 — Step 2 프롬프트와 Step 4.0에 리터럴이 남으므로 통과). `grep -c "NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED" .claude/skills/gx-tdd/phases/phase-review.md` → 1 이상. `grep -n "spec-reviewer\|quality-reviewer" .claude/skills/gx-tdd/phases/phase-review.md | grep -v "미호출\|구 세대\|구 2석\|2석 세대"` → 출력 없음 (잔존 시 같은 방식으로 갱신).

- [ ] **Step 7: Commit** — `feat: phase-review를 reviewer 1석 통합으로 재작성하고 Step 4b 주체를 implementer로 교체한다` + 트레일러

---

### Task 3: SKILL.md·phase-setup·golden 일괄 갱신

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` (:92 부근)
- Modify: `tests/golden-scenarios.md` (S9·S10·S17)

**Interfaces:**
- Consumes: Task 1·2의 리터럴

- [ ] **Step 1: eco 하향 목록 (T9·C-1)** — Task 1 Step 5에서 앞당겨 처리했으면 확인만. `:465` 부근:

```
old: - **eco (에코 모드)**: **design-critic, test-architect, quality-reviewer**를 Task 호출 시
new: - **eco (에코 모드)**: **design-critic, test-architect, reviewer, quality-reviewer**를 Task 호출 시
```

같은 문단의 하향 근거 괄호 `(하향되는 3종은 실패 모드가 '놓침'인 검증자이며 spec-reviewer·security-auditor·verify가 별도 축에서 방어)` → `(하향 대상은 실패 모드가 '놓침'인 검증자이며 security-auditor·verify가 별도 축에서 방어. quality-reviewer는 gx-tdd 미호출이나 opus 정의 존치로 린트 opus 전수 대조 계약상 목록에 남긴다)`. 드리프트 주의의 모델 프로파일 항목(`tdd: design-critic·test-architect·quality-reviewer`) → `tdd: design-critic·test-architect·reviewer(+quality-reviewer 잔존 등재)`.

- [ ] **Step 2: 리뷰 구조 서술 일괄** — 각 old 실측 후 교체:
- frontmatter `:4` description: `리뷰(spec→quality)` → `리뷰(reviewer 통합)`
- 차별점 표 review 행: `**spec → quality 순차 강제**` → `**reviewer 통합 1석 (spec verdict 선행)**`
- Agent 팀 표 REVIEW 절: `**reviewer** | **spec Part 1 + quality Part 2 통합 (신설)** | **"스펙대로인가 → 잘 짜였나" — Part 1 verdict 선행** | **opus**` 행 신설, spec-reviewer·quality-reviewer 행을 `(파이프라인 미호출 — reviewer로 통합. 정의 존치)` 표기로 교체
- Phase 개요 표 review 행: `**spec-reviewer → quality-reviewer (순차 강제)** + security-auditor (quality와 병렬)` → `**reviewer (spec+quality 통합 1석)** + security-auditor (병렬)`
- 핵심 차별점: `review는 병렬이 아니라 **spec → quality 순차** (spec 우선)` → `review는 **reviewer 1석의 Part 1(spec) → Part 2(quality) 내부 순서 강제** (spec verdict 선행) + security 병렬`
- Agent 팀 강제 나열: `spec-reviewer, quality-reviewer` → `reviewer` (+ 괄호에 `spec-reviewer·quality-reviewer는 reviewer로 통합 — 파이프라인 미호출` 추가. Phase A의 "한시 예외: phase-review Step 4b …" 문구 **삭제** — Task 2에서 해소됨)
- 드리프트 주의: "마커 분류" 항목의 SSOT `agents/quality-reviewer.md` → `agents/reviewer.md`, "기계 판정 블록" 항목의 spec·quality SSOT → `agents/reviewer.md` (security는 기존 유지)
- Context Slicing REVIEW 절: spec-reviewer·quality-reviewer 두 항목 → 통합 1항목: `- **reviewer (통합 리뷰)**: PRD의 "요구사항"+"수용 기준" + 설계서의 "변경 범위" + diff 파일 경로(DIFF_FILE) + 코드 맵 + 프로젝트 컨벤션 + 테스트 품질 기준 파일 경로. **"Part 1 verdict 선행. 테스트 재실행 금지"** 지시.`
- 병렬 규칙: 읽기 전용 나열에 reviewer 추가, 5항 `spec-reviewer → quality-reviewer는 **반드시 순차**` → `reviewer 1석이 Part 1 → Part 2를 내부 순서로 수행한다 (개별 2석 디스패치 금지). security-auditor는 reviewer와 병렬 가능`
- state 예시 steps.review: `- spec-review (1단계): pending` / `- quality-review + security (2단계 병렬): pending` → `- unified-review + security (병렬): pending`

- [ ] **Step 3: phase-setup :92** — standard 안내의 `architect·coder·design-critic·test-architect·quality-reviewer 등 opus 에이전트` → `architect·coder·design-critic·test-architect·reviewer 등 opus 에이전트`

- [ ] **Step 4: golden S9·S10·S17**
- S9: `implement는 red-writer·implementer만 디스패치(…)하고 인계는 reports/t{N}-*.md 경로로 관찰. review는 spec/quality-reviewer 디스패치(Step 4b 정리 경로의 refactor-coder는 Phase B 전환 전까지 허용)` → `implement는 red-writer·implementer만 디스패치(…)하고 인계는 reports/t{N}-*.md 경로로 관찰. review는 reviewer(통합 1석)·security-auditor만 디스패치 — Step 4b 정리도 implementer` (실측 old 기준)
- S10: `spec/quality/security 리뷰 각 1회 완료` 행 → `reviewer·security 리뷰 완료 | (관찰 항목) | reviewer 출력 마지막에 spec_verdict → quality_verdict 두 블록 순서 고정 + security 출력에 security_verdict — verdict/집계가 산문과 일치`
- S17: `design-critic·test-architect·quality-reviewer 디스패치에 model: "sonnet" 오버라이드 관찰` → `design-critic·test-architect·reviewer 디스패치에 model: "sonnet" 오버라이드 관찰` (뒤의 괄호·나열도 실측에 맞게 — quality-reviewer는 디스패치되지 않으므로 관찰 대상에서 제외)

- [ ] **Step 5: 검증 + Commit** — 린트 exit 0 ([14/26] eco 대조 통과 — reviewer 등재 확인). `grep -n "spec-reviewer\|quality-reviewer" .claude/skills/gx-tdd/SKILL.md | grep -v "미호출\|통합\|잔존\|존치"` → 출력 없음 (잔존 시 같은 방식 갱신). / `docs: SKILL.md·setup·golden을 reviewer 통합 기준으로 갱신한다` + 트레일러

---

### Task 4: 파생 문서 정합 — 리뷰 서술 + 에이전트 19종

**Files:** `README.md`, `docs/guide.md`, `docs/onboarding-guide.md`, `docs/tdd-guide.md`, `index.html`, `.claude/rules/harness-codex.md`, `.claude/skills/gx-cross-review/SKILL.md`, `agents/test-architect.md`

- [ ] **Step 1: 에이전트 18 → 19** (reviewer 신설로): README `:59`, onboarding `:32`, guide `:106`·`:120`, index.html `:7`·`:1079`·`:1189`, harness-codex `:33`·`:78` — 각 위치의 "18"을 "19"로 (실측 문맥 확인)
- [ ] **Step 2: 리뷰 서술 정합**:
- README `:256`: `**review**: \`spec-reviewer\`(AC 충족) → \`quality-reviewer\`(코드 품질) 순차 게이트 + \`security-auditor\`` → `**review**: \`reviewer\`(AC 충족 → 코드 품질 통합 1석, spec verdict 선행) + \`security-auditor\` 병렬`
- README `:402` 부근 에이전트 표: `reviewer | spec+quality 통합 리뷰 (tdd)` 행 신설, spec-reviewer·quality-reviewer 행에 `(reviewer로 통합 — 미호출)` 표기
- onboarding `:245` 부근 표: 동일 방식 (reviewer 행 추가 + 기존 행 표기)
- guide.md의 gx-tdd 리뷰 서술 (`:672` 부근 `리뷰는 **spec-reviewer(AC 충족) → quality-reviewer(코드 품질)** 2단계로` 류): → `리뷰는 **reviewer(AC 충족 → 코드 품질 통합 1석)**로` (실측 문맥 기준)
- tdd-guide.md의 리뷰 절 (spec→quality 순차 서술): 통합 1석 기준으로 (실측 후 해당 행만)
- index.html `:1108` (spec-reviewer 카드): reviewer 카드로 교체 또는 `(reviewer로 통합)` 표기 + quality-reviewer 카드 동일 처리 + 리뷰 흐름 서술(`:931` 부근 review 행이 있으면) 갱신
- cross-review `:807`: `gx-tdd 내부 리뷰는 spec-reviewer→quality-reviewer가 담당하며` → `gx-tdd 내부 리뷰는 reviewer(spec→quality 통합 1석)가 담당하며`
- test-architect.md의 spec-reviewer/quality-reviewer 언급 (실측): 통합 기준 문구로
- [ ] **Step 3: 검증 + Commit** — 린트 exit 0. `grep -rn "spec-reviewer" README.md docs/guide.md docs/onboarding-guide.md index.html | grep -v "통합\|미호출"` → 출력 없음 (잔존 시 판단·갱신). / `docs: 파생 문서를 reviewer 통합·19종 기준으로 정합시킨다` + 트레일러

---

### Task 5: 릴리스 준비 (v1.25.0) + 최종 검증

**Files:** `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`

- [ ] **Step 1: CHANGELOG v1.25.0 섹션** — 최상단(`# Changelog` 다음)에 추가. 형식은 v1.24.0 섹션 관례(서사 도입 문단 + `- **추가|변경 — 항목**: 설명` 불릿)를 따른다. 내용: Phase A+B 통합 —

```markdown
## v1.25.0 (2026-09-02)

gx-tdd의 implement·review 단계를 superpowers 실행 모델로 재정렬했다. 기존에는 W 하나(AC 4개)에 에이전트 디스패치 약 20회·전체 테스트 스위트 실행 10~14회가 들었다 — 태스크마다 3에이전트(red/green/refactor)를 순차 디스패치하며 매 단계 전체 테스트를 재실행하고, 리뷰도 spec→quality 2석 왕복이었기 때문이다. superpowers 원본(subagent-driven-development)과의 전면 대조로 이격을 도출해 2에이전트 구현·통합 1석 리뷰·focused 테스트 전략으로 재편했다. 확인 게이트(AskUserQuestion)는 협업 접점이므로 그대로 유지한다. 효과: 전체 테스트 10~14회 → 3회, implement 디스패치 태스크당 3 → 2, 리뷰 왕복 절반.

- **추가 — implementer 에이전트**: green-coder+refactor-coder 통합(GREEN 최소 구현 + GREEN 유지 정리). 테스트 수정 금지·YAGNI 계약 승계, self-review 4관점, focused 전용 실행. 구 트리오는 단독 스킬(gx-green·gx-refactor)·gx-ralph 전용으로 존치하며 프롬프트 소스는 phase-implement 부록 A에 보존
- **추가 — reviewer 에이전트**: spec(AC 충족)과 quality(코드 품질)를 한 디스패치로 — Part 1 verdict 선행(Iron Law: NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED), Part 1 FAIL이어도 Part 2를 수행해 재구현 라운드에 품질 지적을 함께 전달. spec/quality-reviewer 2석은 미호출 존치
- **변경 — focused 테스트 전략**: 사이클 중에는 대상+신규 테스트만 실행하고 전체 스위트는 경계 3회(기준선·Mechanical Gate·verify)로 한정. `projectTypes.focusedTest` 템플릿(`{files}`/`{pattern}`) 신설, 미등록·명령 오류 시 전체 폴백 가드
- **변경 — report 파일 계약**: 에이전트 전문 보고를 `.dev/{slug}/reports/t{N}-*.md`로, 반환은 4-status(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED) 15줄 이내 — 긴 파이프라인의 컨텍스트 오염·라우팅 실패를 구조적으로 차단
- **변경 — fix loop 5라운드**: 실패 시 같은 implementer 재개(1~3라운드) → fresh+opus 격상(4~5라운드) → 소진 시에만 사용자 확인. 리뷰 Gate·경계 회귀의 기존 스위트 회귀는 수리 모드(RED report 없이 에러+focused 명령)로 처리
- **추가 — red-writer 테스트 품질 가드**: 깨짐 명명 원칙(Name the Break — 미러 assertion·change detector 금지)과 변이 점검 5종을 이식 (3중 동기: agents ↔ phase-implement ↔ gx-red)
- **변경 — 검증 계약**: 린트 [26/26](report 경로·4-status·ralph 부록 참조) 신설, 전 항목 분모 26 정렬. 하위 호환: 구 3석 세션 `--resume`·gx-ralph 트리오·단독 스킬 동작 불변
```

- [ ] **Step 2: 버전 3파일** — `.claude-plugin/plugin.json` `"version"`, `.claude-plugin/marketplace.json` `plugins[0].version`, `.codex-plugin/plugin.json` `"version"` 전부 `1.25.0` (현재 1.24.0). python3 JSON 파싱으로 3값 확인.
- [ ] **Step 3: 최종 검증** — `bash scripts/lint-consistency.sh` → exit 0 ([1/26] 버전 4중 일치 통과 확인), `bash scripts/hook-tests.sh` → 통과, `grep -rn "spec → quality\|spec→quality" .claude/skills .claude/rules README.md docs/guide.md docs/onboarding-guide.md --include="*.md"` → 잔존 각 줄 정당성 판단 (구 세대 호환·역사 서술만 허용)
- [ ] **Step 4: Commit** — `chore: v1.25.0 릴리스를 준비한다` + 트레일러

---

## 범위 밖 (Phase C — 머지 후)

- gx-ralph-iterate 2석 전환 검토 (트리오 유지 중 — 부록 A 소스 보존)
- 발표 자료 2종(tdd-presentation·script)은 아카이브 — 보존 확정
- spec/quality/green/refactor 에이전트 정의 파일의 최종 정리 여부

## Self-Review

- Spec 커버리지: T3(Task 1·2·3·4), T6-reviewer(Task 1 — Do Not Trust the Report), T9·C-1(Task 3 Step 1, eco 잔류 근거 포함), I-9(Iron Law 리터럴 + 재명시 지점: phase-review 헤더·프롬프트·금지 사항, SKILL.md 개요·차별점·병렬 규칙) — 전부 태스크에 매핑. 릴리스는 spec "Phase B 완료 후" 지시 이행
- 린트 정합: [3/26] producer 2건 교체(Task 1 RED) + consumer 무변경, [14/26] eco는 reviewer 등재로 통과(Task 1 Step 5 앞당김 규칙), [5/26] 디스패치 이름은 Task 1 선행으로 충족, [1/26] 버전 4중은 Task 5에서 일치
- 계약 리터럴 관통: `oh-my-gx:reviewer`·Iron Law 문자열·`unified-review + security (병렬)`이 Task 1→2→3에서 동일
- Phase A 교훈 반영: 실측 old 기준(줄번호 참고치), 검증 grep에 폴백 지시, 커밋 트레일러 명시, 에이전트 개수 파급(19종) 포함
