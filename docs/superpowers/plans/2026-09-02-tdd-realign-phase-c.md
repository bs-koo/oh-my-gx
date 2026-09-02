# gx-tdd superpowers 재정렬 Phase C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-ralph 무인 루프를 2석(red-writer→implementer)으로 전환해 부록 A를 제거하고, 소비자가 없어진 spec/quality-reviewer 정의를 삭제하며(19→17종), parked 문구·잔여 Minor를 정리한다.

**Architecture:** 마크다운 스킬 문서 + grep 린트 저장소. 사용자 확정 결정 D3(ralph 2석 전환)·D4(spec/quality-reviewer 삭제)를 이행한다. 버전은 1.25.0 유지(미태그 — CHANGELOG 같은 섹션에 편입).

**Spec:** `docs/specs/2026-09-01-tdd-superpowers-realign.md` (v2 — Phase C 절) + 사용자 결정 D3·D4

## Global Constraints

- **작업 브랜치: `feat/tdd-agent-realign`** (PR #80 누적)
- 커밋 트레일러 필수: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01V9ZCGyv72BYDtwx8FPYFup`
- 검증: `bash scripts/lint-consistency.sh` exit 0 (26항목) + `bash scripts/hook-tests.sh`
- D1: AskUserQuestion 게이트 문구 무훼손. verify 게이트·지문·훅 무변경
- 줄번호는 참고치 — old 문자열 완전 일치 기준. 불일치 시 BLOCKED
- 단독 스킬(gx-green·gx-refactor·gx-red)의 자체 계약("최대 2회" 등)은 무변경
- 발표 자료 2종(tdd-presentation·script)은 아카이브 — 무변경
- 이모지 금지(index.html 기존 마크업 제외), 계획 외 절 수정 금지

---

### Task 0: 브랜치·기준선 확인

- [ ] `git branch --show-current` → `feat/tdd-agent-realign` / `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0 (아니면 중단·보고)

---

### Task 1: gx-ralph 2석 전환 + 부록 A 삭제 (원자적 — 한 커밋)

**Files:**
- Modify: `agents/implementer.md` (루프 모드), `.claude/skills/gx-ralph-iterate/SKILL.md:89`, `.claude/skills/gx-ralph/SKILL.md:76`·`:87`, `.claude/skills/gx-tdd/phases/phase-implement.md`(부록 A 삭제·Step 2-I 5종·:15), `.claude/skills/gx-tdd/phases/phase-complete.md`(Step -2 트리오 문구), `agents/green-coder.md`·`refactor-coder.md`(헤더 노트), `.claude/skills/gx-tdd/SKILL.md:57`, `tests/golden-scenarios.md`(S9), `scripts/lint-consistency.sh`([26/26] ralph 검사)

**원자성 근거**: 부록 A 삭제는 린트 [3/26](금지 5종이 부록에만 존재)과 [26/26](`부록 A` grep)을 동시에 깨뜨리므로, Step 2-I 5종 보강·린트 검사 교체·ralph 참조 재작성이 한 커밋에 있어야 어느 시점에도 린트가 깨지지 않는다.

- [ ] **Step 1: implementer 루프 모드 절 추가** — `agents/implementer.md`의 정리 모드 절 바로 뒤에:

```
   - **루프 모드**: gx-ralph 무인 반복(gx-ralph-iterate)의 디스패치에서는 report 파일·태스크 번호가 없다 — RED 산출물(테스트 파일 경로·코드·실패 메시지)을 **인라인으로** 전달받아 시작하고, 전달받은 대상 테스트 명령으로 GREEN·REFACTOR를 확인하며, 보고도 인라인 출력 형식으로 반환한다. 전체 검증은 루프의 verify 게이트가 담당한다.
```

- [ ] **Step 2: Step 2-I 프롬프트에 금지 5종 블록 추가** — phase-implement.md Step 2-I 프롬프트의 `[절대 규칙]` 3항(REFACTOR) 뒤 또는 프롬프트 내 적절한 위치(실측)에 부록 A 구 2-F와 동일한 블록 삽입 (린트 [3/26]의 phase-implement 대상 5종 보존):

```
    [수행 불가능한 정리]
    - 동작 변경
    - 새 기능 추가
    - 에러 핸들링 추가
    - 성능 최적화
    - 인터페이스 시그니처 변경
```

- [ ] **Step 3: 부록 A 삭제** — phase-implement.md `:464`(`## 부록 A: …`)부터 파일 끝(`:577`)까지 삭제. `:15`의 헤더 인용문 교체:

```
old: > green-coder·refactor-coder는 이 파이프라인에서 호출하지 않는다 — 단독 스킬(gx-green·gx-refactor)·gx-ralph 루프 전용 (부록 A 참조).
new: > green-coder·refactor-coder는 이 파이프라인에서 호출하지 않는다 — 단독 스킬(gx-green·gx-refactor) 전용. gx-ralph 루프도 red-writer→implementer 2석을 쓴다.
```

`--resume` 절의 구 세션 `test-count` 재측정 문구는 유지한다 (3석 세대 state 호환은 계속 필요).

- [ ] **Step 4: gx-ralph-iterate :89 재작성** — origin: gx-tdd 항목 전체를 교체:

```
new: - **origin: gx-tdd** → 2석 순차 디스패치: `oh-my-gx:red-writer`(해당 AC의 실패 테스트 작성·실패 확인) → `oh-my-gx:implementer`(GREEN 최소 구현 + REFACTOR 정리 — 루프 모드). 각 단계 프롬프트는 `gx-tdd/phases/phase-implement.md`의 Step 2-R/2-I 디스패치 프롬프트를 따르되, 대상을 이 AC 1건으로 한정하고 **report 파일·15줄 반환 계약은 제외**한다 — 루프에는 reports/ 디렉토리와 태스크 번호가 없으므로 RED 산출물은 인라인으로 인계하고 implementer는 루프 모드(agents/implementer.md)로 동작한다. focused 검증 명령은 이 AC의 테스트 파일로 조립한다(config `focusedTest` 템플릿 — 미지원 시 대상 테스트 직접 실행 명령). phase-implement.md를 Read할 수 없으면(플러그인 설치 환경의 경로 차이 등) BLOCKED로 중단하지 않는다 — 위 괄호의 각 에이전트 기본 역할 계약대로 이 AC 1건 한정 프롬프트를 직접 구성해 디스패치한다. 대상이 UI(화면 컴포넌트·컴포저블·스토어·라우팅 가드)이면 red-writer 프롬프트에 `gx-tdd/references/frontend-testing.md`의 UI 가드(셀렉터 우선순위·스타일 assert 금지)를 함께 전달한다. (v1.25.0 이전에 시작된 루프의 잔여 반복도 다음 반복부터 이 2석으로 디스패치한다 — 반복은 서로 독립이다)
```

- [ ] **Step 5: gx-ralph/SKILL.md 2곳** — `:76` `(gx-tdd면 RGR 트리오)` → `(gx-tdd면 red-writer→implementer 2석)`, `:87` `(coder·red/green/refactor-coder)` → `(coder·red-writer·implementer)`

- [ ] **Step 6: phase-complete Step -2 트리오 문구** — `:26` 부근 `반복 세션이 red-writer→green-coder→refactor-coder 트리오로 AC를 구현한 산출물이다` → `반복 세션이 red-writer→implementer 2석(v1.25.0 이전 루프는 트리오)으로 AC를 구현한 산출물이다`

- [ ] **Step 7: 헤더 노트·드리프트·S9** — agents/green-coder.md·refactor-coder.md 헤더 노트의 `단독 스킬(gx-green)·gx-ralph 루프 전용` → `단독 스킬(gx-green) 전용` (refactor는 gx-refactor). description의 gx-ralph 언급도 실측 갱신. SKILL.md `:57` 드리프트 항목에서 부록 A 관련 문구를 `(green/refactor 트리오는 단독 스킬 전용)`·`phase-implement.md(Step 2-R/2-I)`로 정리. golden S9의 `부록 A는 gx-ralph 전용` → `단독 스킬 전용`.

- [ ] **Step 8: 린트 [26/26] ralph 검사 교체**:

```
old: grep -q "부록 A" .claude/skills/gx-ralph-iterate/SKILL.md \
  || fail "ralph 트리오 프롬프트 참조(부록 A) 누락: gx-ralph-iterate/SKILL.md"
new: grep -q "oh-my-gx:implementer" .claude/skills/gx-ralph-iterate/SKILL.md \
  || fail "ralph 2석 디스패치(implementer) 누락: gx-ralph-iterate/SKILL.md"
```

- [ ] **Step 9: 죽은 참조 검증** — `grep -rn "부록 A\|구 Step 2-[GF]" .claude tests --include="*.md" | grep -v "\.dev/\|worktrees"` → 출력이 있으면 각 줄 갱신(CHANGELOG의 사실 기록은 Task 3에서 처리 — 여기선 스킵 허용, report에 기록). 린트·훅 exit 0.

- [ ] **Step 10: Commit** — `feat: gx-ralph 루프를 2석으로 전환하고 부록 A를 제거한다` + 트레일러

---

### Task 2: spec/quality-reviewer 삭제 + 17종 정합

**Files:**
- Delete: `agents/spec-reviewer.md`, `agents/quality-reviewer.md`
- Modify: `.claude/config.json`(contextLimits 2키 삭제), `.claude/skills/gx-tdd/SKILL.md`(팀 표·eco 3종 환원·드리프트), `tests/golden-scenarios.md`(S17), `README.md`, `docs/guide.md`, `docs/onboarding-guide.md`, `index.html`, `.claude/rules/harness-codex.md`

- [ ] **Step 1: 파일 삭제 + contextLimits** — `git rm agents/spec-reviewer.md agents/quality-reviewer.md`. config.json contextLimits에서 `spec-reviewer`·`quality-reviewer` 키 제거 (python3 파싱 확인).
- [ ] **Step 2: eco 3종 환원** — SKILL.md eco 목록 `design-critic, test-architect, reviewer, quality-reviewer` → `design-critic, test-architect, reviewer`. 하향 근거 괄호의 `quality-reviewer는 gx-tdd 미호출이나 opus 정의 존치로 린트 opus 전수 대조 계약상 목록에 남긴다` 문구 삭제. 드리프트 주의 모델 프로파일 항목의 `(+quality-reviewer 잔존 등재)` 삭제. 파생 사본(docs/guide.md·docs/tdd-guide.md의 동일 문구 — 실측) 동기 갱신. S17의 `eco 목록은 quality-reviewer 잔존 등재로 4종` → 3종 정합 문구.
- [ ] **Step 3: SKILL.md 팀 표·잔존** — Agent 팀 표에서 spec-reviewer·quality-reviewer의 "(파이프라인 미호출…)" 행 삭제. `grep -n "spec-reviewer\|quality-reviewer" .claude/skills/gx-tdd/SKILL.md`로 잔존 전수 확인 — 구 세대 호환·역사 서술(--resume 호환 줄, "구 2석" 설명)만 남기고 현행 서술은 갱신 (판단 기준: 존재하지 않는 파일을 현재형으로 가리키면 갱신).
- [ ] **Step 4: 문서 17종 파급** — 에이전트 수 19→17: README `:59`·표(2행 삭제), onboarding `:32`(19→17)·표(8종→6종 — 행 수 실측)·`:236` 카운트, guide `:106`·`:120`, index.html `:7`·`:714`·`:1079`·`:1189`·카드 2장 삭제·리뷰 그룹 count(5→3 — 실측), harness-codex `:33`·`:78`. qa-manager description 등 잔존 언급 grep 정리 (`grep -rn "spec-reviewer\|quality-reviewer" agents/ README.md docs/ index.html .claude/rules/ --include="*"` — 역사 서술 외 전부).
- [ ] **Step 5: 검증 + Commit** — 린트 exit 0 ([14/26] opus 전수 대조가 삭제로 자동 정합, [5/26] 디스패치 이름 — phase-review에 구 2석 디스패치 코드 없음 확인). `chore: 소비자가 없어진 spec/quality-reviewer 정의를 삭제한다 (에이전트 17종)` + 트레일러

---

### Task 3: parked·잔여 정리 + CHANGELOG 편입 + 최종 검증

**Files:** `.claude/skills/gx-tdd/phases/phase-review.md`, `.claude/skills/gx-tdd/phases/phase-implement.md`, `CHANGELOG.md`

- [ ] **Step 1: parked 문구 정리 (phase-review)** — SPEC FAIL 처리 절: `:210` 부근 `**SPEC PASS** → Step 4.1로 진행` → `**SPEC PASS** → Step 4.1 이후 절차 계속` (4.1이 분기 전 선행됨과 정합), `:216` 부근 `"이대로 진행" → 미충족 AC를 trust-ledger에 기록 후 Step 4.1 진행 (예외)` → `"이대로 진행" → 미충족 AC를 trust-ledger에 추가 기록 후 계속 진행 (위험 수용)` (실측 문맥 기준 — 취지: 이미 수행된 4.1을 재지시하지 않기)
- [ ] **Step 2: 잔여 Minor** — phase-implement focused 조립 절의 `{pattern}` 예시에 셸 인용 (`--tests *.PaymentLimitTest` → `--tests '*.PaymentLimitTest'` — 실측 2곳), porcelain 필터 서술에 svn 분기 문구 보강: `(svn은 \`svn status\` 출력의 경로 컬럼 기준으로 같은 필터를 적용)` — 이미 있으면 확인만
- [ ] **Step 3: CHANGELOG v1.25.0 편입** — implementer 불릿의 `프롬프트 소스는 phase-implement 부록 A에 보존` → `gx-ralph 루프도 v1.25.0에서 red-writer→implementer 2석으로 전환했다(부록 A 제거)`. 새 불릿 추가: `- **정리 — 유물 제거**: 어느 파이프라인도 디스패치하지 않게 된 spec-reviewer·quality-reviewer 정의를 삭제했다(에이전트 17종). eco 하향 목록은 design-critic·test-architect·reviewer 3종으로 환원`
- [ ] **Step 4: 최종 검증** — `bash scripts/lint-consistency.sh` exit 0 / `bash scripts/hook-tests.sh` 통과 / `grep -rn "부록 A\|spec-reviewer\|quality-reviewer" .claude tests README.md docs/guide.md docs/onboarding-guide.md index.html CHANGELOG.md --include="*" | grep -v "\.dev/\|worktrees\|구 2석\|2석 세대\|삭제했다\|이전 루프"` → 잔존 각 줄 정당성 판단 (역사 서술만 허용)
- [ ] **Step 5: Commit** — `docs: parked 문구를 정리하고 CHANGELOG에 Phase C를 편입한다` + 트레일러

---

## Self-Review

- D3 이행: Task 1이 루프 모드(implementer)·iterate 재작성·부록 A 삭제·금지 5종 보존·린트 2건을 한 커밋에 — 원자성 근거 명시. 구 루프 세션은 반복 독립성으로 자연 전환
- D4 이행: Task 2가 삭제·contextLimits·eco 3종·문서 17종을 커버. [14/26]는 삭제로 자동 정합
- parked 1건·잔여 Minor 2건·CHANGELOG 편입: Task 3
- 리터럴 관통: `oh-my-gx:implementer`(iterate·린트 [26]), 루프 모드(agents ↔ iterate), `red-writer→implementer 2석`(ralph SKILL·phase-complete·헤더 인용문)
