# gx-tdd 구현 내부 게이트 판정 규약 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 구현 단계 안의 확인 질문 3곳(과잉 구현 정리 여부, 동작 불변 정리 수행 여부, Minor·MEDIUM 수정 여부)을 기본값 판정으로 바꾸고, 판정을 `decisions.md`에 `Ruling` 블록으로 남겨 사이클 보고와 PR 본문에 노출한다. 산출물 승인·SPEC FAIL·Critical·동작 결함·위험 수용의 질문은 그대로 둔다.

**Architecture:** phase-implement에 `## 판정 기록 (Rulings)` 절(SSOT — 형식·기본값 표·노출 규칙)을 두고, verify_implement 5번과 phase-review 4b·4c가 그 규약을 참조해 질문 대신 판정한다. phase-complete Step 2-1이 decisions.md의 Ruling 블록과 유예 목록으로 `pr-rulings.md`를 만들어 gx-pull-request에 `--extra-section`으로 넘기고, gx-pull-request는 `## Rulings`·`## Deferred` 절을 요약 없이 그대로 옮긴다. 린트 `[35]`가 규약 절 존재·폐지된 질문 3곳 부재·기록 지시·PR 노출을 고정한다.

**Tech Stack:** Markdown (스킬·phase·문서), Bash (린트)

**Spec:** `docs/specs/2026-09-09-superpowers-gap-design.md` — D2, 2절 불변 목록, D5 순서

## Global Constraints

- **선행 조건**: `2026-09-09-tdd-task-review.md`가 main에 머지되어 있어야 한다 — `.claude-plugin/plugin.json` version `1.28.0`, `grep -c '/34\]' scripts/lint-consistency.sh`가 0보다 크고, phase-implement에 `### Step 2-V: 태스크 리뷰` 절이 있다.
- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (훅 G1). 작업 시작 전 `feat/tdd-rulings` 브랜치를 생성한다.
- **커밋**: 메시지는 `feat: …`/`docs: …` 한 줄 제목. 트레일러를 **붙이지 않는다**. 서브에이전트는 직접 `git commit`을 허용한다 (이전 계획과 같은 ruling). grep 패턴 인자에 `git commit` 문자열을 넣지 않는다.
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 둘 다 통과한 상태로 끝난다.
- **SKILL.md는 건드리지 않는다**: 규약의 SSOT를 phase-implement에 두는 이유가 `[32]` 예산이다. Trust Ledger 구조도 바꾸지 않는다 — 유예 항목은 decisions.md와 PR 본문에만 남긴다.
- **린트 번호 체계**: 현재 `[N/34]`. Task 5가 검사 1개를 추가하며 분모를 35로 올린다. `.claude/`·`README.md`의 인용도 함께 치환한다 (`[31]`이 검사). `docs/`·`CHANGELOG.md`는 치환하지 않는다.
- **린트가 고정하는 문구**: `[3]`·`[26]`·`[33]`·`[34]`의 phase-implement 문구, `[27]`·`[28]`·`[33]`·`[34]`의 phase-review 문구(`security 감사 미확보`, 커버리지 문단, `세션 IMPLEMENT`, `[태스크 리뷰 유예 Minor`)를 지우거나 바꾸지 않는다. 4b의 "기본 경로/격리 경로" 본문은 글자를 바꾸지 않고 앞머리만 바꾼다.
- **질문을 없애지 않는 곳**: 1.2 태스크 분해 승인, 1.15 태스크 수 가드, verify_red 3번, fix loop 소진, H3 긴급 감사, phase-review SPEC FAIL·4a·2회 반복 후 Critical, phase-complete 전부. 이 계획의 대상은 verify_implement 5·phase-review 4b·4c 셋뿐이다.
- **gx-green 단독 스킬의 "지금 정리할까요?"는 손대지 않는다** (단독 스킬은 대화형 도구다).
- **외과적 변경**: 지시된 블록만 고친다.

---

### Task 1: phase-implement에 판정 규약을 두고 과잉 구현 질문을 판정으로 바꾼다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` — verify_implement 5번, `## Step 4: 사이클 완료 보고` 템플릿, `## 금지 사항 (Iron Law 강제)` 앞에 `## 판정 기록 (Rulings)` 신설

**Interfaces:**
- Consumes: 없음
- Produces: 절 제목 `## 판정 기록 (Rulings)`, 블록 제목 형식 `## {YYYY-MM-DD HH:MM} · Ruling: {제목}`, report 절 `## 과잉 구현 정리` (Task 2·3·5가 인용·검사)

- [ ] **Step 1: `## 금지 사항 (Iron Law 강제)` 제목 바로 위(`---` 앞)에 규약 절을 삽입한다**

```markdown
## 판정 기록 (Rulings)

구현 내부 게이트 3곳 — verify_implement 5번(과잉 구현), phase-review 4b(동작 불변 정리), 4c(Minor·MEDIUM) — 는 사용자에게 묻지 않고 **기본값으로 판정**하고 근거를 남긴다. 답이 거의 항상 기본값인 질문에 사람을 세우지 않기 위해서다. 산출물 승인(PRD·설계·태스크 분해), SPEC FAIL, Critical, 동작 결함의 RGR 여부, 위험 수용은 이 규약의 대상이 **아니며** 계속 AskUserQuestion으로 확인한다.

**기록 위치**: `${DEV_DIR}/decisions.md` — AskUserQuestion 훅(capture-decision)이 쓰는 파일에 오케스트레이터가 append한다. 파일이 없으면 훅과 같은 헤더로 만든다:

```
# 의사결정 기록

AskUserQuestion으로 오간 질문과 선택을 자동 기록한다. 고른 것뿐 아니라 버린 선택지도 남으므로 왜 그렇게 정했는지가 추적된다.
```

**블록 형식** (한 판정 = 한 블록. 시각은 `date "+%Y-%m-%d %H:%M"`):

```
## {YYYY-MM-DD HH:MM} · Ruling: {제목}

**판정.** {무엇을 어떻게 했는가 — 파일·항목을 명시}
**근거.** {왜 그 기본값인가}
**틀리면.** {되돌리는 방법과 비용 — 예: reports/t2-impl.md "## 과잉 구현 정리" 목록으로 복원}
```

**기본값 표**:

| 게이트 | 기본 판정 | 예외 |
|---|---|---|
| verify_implement 5 과잉 구현 | focused 테스트 집합이 참조하지 않는 신규 public 멤버를 **제거**하고 focused를 재실행한다. 제거로 focused가 깨지면(간접 사용) 복원하고 `## 우려사항`에 기록한다 | 설계서 인터페이스가 명시한 멤버는 제거하지 않고 "설계 예약"으로 판정만 기록한다 |
| phase-review 4b 동작 불변 정리 | **수행**한다 (정리 모드 — 기본은 세션 직접, `--isolated`면 implementer) | 없음 |
| phase-review 4c quality Minor | **유예** — 수정하지 않고 Deferred 목록에 올린다 | 없음 |
| phase-review 4c security MEDIUM | 동작 불변이 명백하면 **정리 모드로 수정**, 동작 변경을 동반하거나 모호하면 **유예** | 없음 |

**노출**: 판정은 사용자가 되돌릴 수 있어야 하므로 워크스페이스 안에만 두지 않는다. Step 4 사이클 완료 보고와 phase-complete Step 2-1의 `pr-rulings.md`(`## Rulings` 제목 나열 + `## Deferred` 유예 목록)에 옮긴다.
```

- [ ] **Step 2: verify_implement 5번을 교체한다**

현재:

```
5. **과잉 구현 감지**: 추가된 메서드/필드 중 테스트에서 안 쓰는 것 → 사용자에게 보고: "과잉 구현 감지. YAGNI 권고로 다음 RED 단계로 미루는 것이 좋습니다. 정리할까요?"
```

새 텍스트:

```
5. **과잉 구현 판정**: 추가된 public 메서드/필드 중 focused 테스트 집합이 참조하지 않는 것을 찾는다. 있으면 **묻지 않고 판정한다** — "판정 기록 (Rulings)" 절의 기본값대로 설계서 인터페이스가 명시한 멤버는 "설계 예약"으로 유지하고, 그 외는 제거한 뒤 focused를 재실행한다 (제거로 깨지면 복원하고 `## 우려사항`에 기록). 제거·유지 목록을 `reports/t{N}-impl.md`에 `## 과잉 구현 정리` 절로 append하고, decisions.md에 `Ruling: T{N} 과잉 구현 정리` 블록을 append한다. 판정할 것이 없으면 아무것도 기록하지 않는다.
```

- [ ] **Step 3: Step 4 보고 템플릿에 판정 줄을 넣는다**

`변경 파일: {N}개` 행 뒤에 추가한다:

```
판정: {N}건 (decisions.md — 제목 나열: T2 과잉 구현 정리, …)
```

- [ ] **Step 4: 검증**

Run: `for s in '## 판정 기록 (Rulings)' '· Ruling: ' '**판정.**' '**근거.**' '**틀리면.**' '## 과잉 구현 정리' '과잉 구현 판정' '설계 예약' 'pr-rulings.md'; do grep -qF "$s" .claude/skills/gx-tdd/phases/phase-implement.md || echo "MISSING: $s"; done; grep -c '정리할까요?' .claude/skills/gx-tdd/phases/phase-implement.md; bash scripts/lint-consistency.sh`
Expected: `MISSING` 없음, `0`, 34/34 통과 (`[34]`의 Step 2-V awk 구간은 `## Step 3` 앞에서 끝나므로 새 절과 무관).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md
git commit -F - <<'MSG'
feat: gx-tdd 판정 기록 규약을 두고 과잉 구현 정리를 질문 없이 판정한다
MSG
```

---

### Task 2: phase-review 4b·4c를 판정으로 바꾼다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` — Step 4.4 의사코드의 `# 4b` 블록과 `# 4c` else 분기, Step 4.3 요약

**Interfaces:**
- Consumes: Task 1의 규약 절·블록 형식
- Produces: phase-review의 `Ruling:` 기록 지시 (Task 5 린트가 검사), 4c의 Deferred 목록 (Task 3이 소비)

- [ ] **Step 1: 4b 블록에서 질문을 판정으로 바꾼다**

`    AskUserQuestion: "동작 불변 정리를 수행할까요?"` 행부터 `    did_fix = true (수행 시)` 행까지를 아래로 교체한다. "기본 경로"·"격리 경로" 두 문단은 현재 텍스트를 **글자 그대로** 유지하고 앞머리 `- "예" → `만 뗀다.

```
    Ruling(기본값: 수행) → decisions.md에 `Ruling: review 동작 불변 정리 {N}건` 블록 append (phase-implement "판정 기록 (Rulings)" 규약. 항목 목록은 사용자에게 통지만 한다 — 질문이 아니다)
    기본 경로: 오케스트레이터가 직접 정리한다 — phase-implement Step 2-I "세션 IMPLEMENT 절차"의 절대 규칙과 수행 불가능한 정리 목록을 그대로 지키고, 입력은 refactor_only 항목들의 {파일:라인 + 권고}("정리 대상")이며, 정리 한 단위마다 대상 파일 관련 테스트로 조립한 focused 검증을 실행한다. 결과를 `${DEV_DIR}/reports/review-cleanup.md`에 append한다 (리뷰 반복 시 누적).
               state.md flags에 `--isolated`가 있으면 Task(subagent_type="oh-my-gx:implementer") 정리 모드 — 입력 = refactor_only 항목들의 {파일:라인 + 권고}("정리 대상") + 대상 파일 관련 테스트로 조립한 focused 검증 명령 + report 경로 `${DEV_DIR}/reports/review-cleanup.md`. GREEN 유지·동작 변경 금지 계약은 agents/implementer.md의 REFACTOR 규칙을 따르며, GREEN 기준선은 Step 0에서 통과한 전체 테스트다
               → 어느 경로든 정리 후 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인
    did_fix = true
```

- [ ] **Step 2: 4c의 Minor·MEDIUM 분기를 판정으로 바꾼다**

현재 (`    if Minor(quality) 또는 MEDIUM(security) 항목 있음:`부터 그 `else:` 직전까지):

```
    if Minor(quality) 또는 MEDIUM(security) 항목 있음:
        항목 목록 표시 + "수정할까요?" 확인
        if 수정 선택:
            # 4a/4b와 동일 분류 적용: Minor(quality)는 전부 동작 불변 → 정리 모드(기본은 세션 직접, `--isolated`면 implementer),
            #   security MEDIUM은 위 분류 기준(동작 변경 동반이면 RGR, 아니면 정리 모드(기본은 세션 직접, `--isolated`면 implementer))
            → 단발성 확인 리뷰 (반복 카운트 미포함)
        else:
            → phase-complete
```

새 텍스트:

```
    if Minor(quality) 또는 MEDIUM(security) 항목 있음:
        항목 목록 표시 (판정 결과 통지 — 질문이 아니다)
        # 기본값 (phase-implement "판정 기록 (Rulings)" 규약):
        #   quality Minor → 유예. 수정하지 않고 Deferred 목록에 올린다
        #   security MEDIUM → 동작 불변이 명백하면 정리 모드(기본은 세션 직접, `--isolated`면 implementer)로 수정,
        #                     동작 변경을 동반하거나 모호하면 유예 (Deferred 목록 — 동작 변경은 RED 없이 손대지 않는다)
        Ruling → decisions.md에 `Ruling: review Minor {N}건 유예 · MEDIUM {M}건 {정리|유예}` 블록 append
        Deferred 목록(항목별 [Minor|MEDIUM] 파일:라인 — 요약)을 `${DEV_DIR}/reports/review-deferred.md`에 Write (리뷰 반복 시 덮어쓴다 — 최신 리뷰가 정본)
        if 정리한 MEDIUM 있음:
            → 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인 → 단발성 확인 리뷰 (반복 카운트 미포함)
        → phase-complete (Deferred는 Step 2-1 pr-rulings.md로 전달)
```

- [ ] **Step 3: Step 4.3 요약에 판정 줄을 넣는다**

`- Trust Ledger: ${DEV_DIR}/trust-ledger.md` 행 뒤에 추가한다:

```
- Rulings: {N}건 (decisions.md) · Deferred: {M}건 (reports/review-deferred.md)
```

- [ ] **Step 4: 검증**

Run: `grep -c '동작 불변 정리를 수행할까요\|"수정할까요?" 확인' .claude/skills/gx-tdd/phases/phase-review.md; for s in 'Ruling: review 동작 불변 정리' 'Ruling: review Minor' 'reports/review-deferred.md' 'reports/review-cleanup.md' '세션 IMPLEMENT' '[태스크 리뷰 유예 Minor' 'security 감사 미확보'; do grep -qF "$s" .claude/skills/gx-tdd/phases/phase-review.md || echo "MISSING: $s"; done; bash scripts/lint-consistency.sh`
Expected: `0`, `MISSING` 없음, 34/34 통과.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-review.md
git commit -F - <<'MSG'
feat: phase-review 동작 불변 정리와 Minor·MEDIUM 처리를 질문 없이 판정한다
MSG
```

---

### Task 3: phase-complete가 판정·유예를 PR 본문으로 옮기고 gx-pull-request가 그대로 싣는다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md` — `### Step 2-1` 목록 끝에 3번 추가, `### Step 2-2` 호출 인자
- Modify: `.claude/skills/gx-pull-request/SKILL.md:69` (`--extra-section` 설명), `:149` (본문 템플릿 주석)

**Interfaces:**
- Consumes: Task 1의 `· Ruling: ` 블록, Task 2의 `reports/review-deferred.md`
- Produces: 파일 `${DEV_DIR}/pr-rulings.md`, PR 본문 절 `## Rulings`·`## Deferred` (Task 5 린트가 검사)

- [ ] **Step 1: Step 2-1에 항목 3을 추가한다**

`   Trust Ledger가 없으면 이 섹션을 생략한다.` 문단과 "핵심 모드 긴급 감사 병기" 문단 뒤, `### Step 2-2` 제목 앞에 추가한다:

```markdown
3. **Rulings·Deferred**: `${DEV_DIR}/decisions.md`에 `· Ruling: ` 블록이 하나라도 있거나 `${DEV_DIR}/reports/review-deferred.md`가 있으면 `${DEV_DIR}/pr-rulings.md`를 Write한다. 둘 다 없으면 만들지 않는다.
   ```markdown
   ## Rulings
   - {Ruling 블록 제목} — {**판정.** 줄 요약} (틀리면: {**틀리면.** 줄 요약})

   ## Deferred
   - [Minor] {파일:라인} — {요약}
   - [MEDIUM] {파일:라인} — {요약}
   ```
   Rulings는 decisions.md의 블록 순서대로 전부 나열한다 — 사용자가 되돌릴 판정을 고르는 목록이므로 요약으로 줄이지 않는다.
```

- [ ] **Step 2: Step 2-2 호출을 고친다**

`` `Skill(skill: "oh-my-gx:gx-pull-request", args: "--background ${DEV_DIR}/pr-context.md")` `` 행을 아래로 바꾼다:

```markdown
`Skill(skill: "oh-my-gx:gx-pull-request", args: "--background ${DEV_DIR}/pr-context.md --extra-section ${DEV_DIR}/pr-rulings.md")` — `pr-rulings.md`를 만들지 않았으면 `--extra-section` 인자를 뺀다.
```

그 아래 문장 `pull-request 스킬은 `--background`로 받은 파일만 PR 본문(Background + Audit Summary)에 반영한다 — 자동 감지는 없다 (gx-dev phase-complete와 동일한 명시 전달 방식).` 끝에 ` `--extra-section`의 `## Rulings`·`## Deferred`는 요약 없이 같은 제목으로 실린다.`를 붙인다.

- [ ] **Step 3: gx-pull-request SKILL.md 두 곳을 고친다**

69행 `- `--extra-section <파일경로>` (optional): Checklist 앞에 삽입할 추가 섹션 파일. 지정 시 해당 파일을 Read하여 요약본을 Checklist 직전에 삽입한다.` 문장 끝(같은 불릿 안, 괄호 예시 앞)에 붙인다: ` 파일에 `## Rulings`·`## Deferred` 절이 있으면 요약하지 않고 같은 제목의 절로 항목을 **그대로** 옮긴다 — 판정 목록은 사용자가 되돌릴 근거라 항목이 빠지면 안 된다.`

149행 `(--extra-section 파일이 있으면 여기에 해당 파일을 Read하여 요약 섹션을 삽입한다. 예: Trust Ledger → ## Audit Summary)`를 `(--extra-section 파일이 있으면 여기에 해당 파일을 Read하여 요약 섹션을 삽입한다. 예: Trust Ledger → ## Audit Summary. 단 ## Rulings·## Deferred 절은 요약 없이 항목 그대로)`로 바꾼다.

- [ ] **Step 4: 검증**

Run: `grep -c '## Rulings\|pr-rulings.md' .claude/skills/gx-tdd/phases/phase-complete.md; grep -c '## Rulings' .claude/skills/gx-pull-request/SKILL.md; grep -c -- '--extra-section \${DEV_DIR}/pr-rulings.md' .claude/skills/gx-tdd/phases/phase-complete.md; bash scripts/lint-consistency.sh`
Expected: `3` 이상, `2`, `1`, 34/34 통과 (`[16]` context 커밋 예외 문구·`[4]` verify 판별 키 유지).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-pull-request/SKILL.md
git commit -F - <<'MSG'
feat: 판정과 유예 목록을 PR 본문 Rulings·Deferred 절로 옮긴다
MSG
```

---

### Task 4: 유지보수 노트와 TDD 가이드를 갱신한다

**Files:**
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md` — `**"수동 수정 재주입" 기록 문구**` 항목 앞에 항목 추가
- Modify: `docs/tdd-guide.md` — 6.6 verify_implement 목록 4번

**Interfaces:**
- Consumes: Task 1~3의 용어
- Produces: 없음

- [ ] **Step 1: maintenance-notes**

`- **"수동 수정 재주입" 기록 문구**: …` 항목 **바로 앞**에 추가한다:

```markdown
- **판정 기록 규약**(Ruling 블록 형식·기본값 표·노출): SSOT는 phase-implement.md "판정 기록 (Rulings)" 절. phase-review 4b/4c(판정 지시)·phase-complete Step 2-1(pr-rulings.md 조립)·gx-pull-request SKILL.md(`--extra-section`의 Rulings/Deferred 무요약 규칙)이 소비한다. 린트 [35/34]가 규약 절·폐지된 질문 3곳 부재·기록 지시·PR 노출을 검사한다.
```

(인용을 `[35/34]`로 적는 이유: 린트 `[31]`은 현재 분모(34)와 같은지만 본다. Task 5 Step 2의 전역 치환이 `[35/35]`로 올린다.)

- [ ] **Step 2: tdd-guide**

6.6의 `4. 테스트에서 쓰이지 않는 메서드·필드가 추가됐으면 과잉 구현으로 보고`를 `4. 테스트에서 쓰이지 않는 public 메서드·필드가 추가됐으면 과잉 구현으로 판정해 제거한다 (설계서 인터페이스가 명시한 멤버는 유지). 묻지 않고 처리하고 판정·근거·되돌림 비용을 `decisions.md`에 남긴다`로 바꾼다.

- [ ] **Step 3: 검증**

Run: `grep -c '판정 기록 규약' .claude/skills/gx-tdd/references/maintenance-notes.md; grep -c 'decisions.md' docs/tdd-guide.md; bash scripts/lint-consistency.sh`
Expected: `1`, `1` 이상, 34/34 통과.

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/gx-tdd/references/maintenance-notes.md docs/tdd-guide.md
git commit -F - <<'MSG'
docs: 판정 기록 규약을 유지보수 노트와 TDD 가이드에 반영한다
MSG
```

---

### Task 5: 린트 [35]·골든 S42·v1.29.0 릴리스

**Files:**
- Modify: `scripts/lint-consistency.sh` — 헤더 목록, `[34/34]` 블록 뒤에 새 블록, 분모 34→35 전역 치환
- Modify: `[N/34]`를 인용하는 `.claude/`·`README.md` 파일 전부
- Modify: `tests/golden-scenarios.md` — S42 행, `N/41` → `N/42`
- Modify: `CHANGELOG.md` — v1.29.0 절
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` — `1.28.0` → `1.29.0`

**Interfaces:**
- Consumes: Task 1~3의 문자열
- Produces: 린트 `[35/35] gx-tdd 구현 내부 게이트 판정 계약`

- [ ] **Step 1: 새 검사를 `[34/34]` 블록 뒤(`if [ "$FAIL" -ne 0 ]` 앞)에 추가한다 (분모는 아직 34)**

```bash
echo "[35/34] gx-tdd 구현 내부 게이트 판정 계약"
# 설계: docs/specs/2026-09-09-superpowers-gap-design.md D2
IMPL=.claude/skills/gx-tdd/phases/phase-implement.md
REV=.claude/skills/gx-tdd/phases/phase-review.md
COMP=.claude/skills/gx-tdd/phases/phase-complete.md
grep -qF '## 판정 기록 (Rulings)' "$IMPL" || fail "판정 기록 규약 절 누락: phase-implement.md"
for s in '· Ruling: ' '**판정.**' '**근거.**' '**틀리면.**' '## 과잉 구현 정리' '설계 예약'; do
  grep -qF "$s" "$IMPL" || fail "판정 규약 문구 누락($s): phase-implement.md"
done
grep -qF '정리할까요?' "$IMPL" && fail "폐지된 과잉 구현 질문 잔존: phase-implement.md verify_implement 5"
grep -qF '동작 불변 정리를 수행할까요' "$REV" && fail "폐지된 4b 질문 잔존: phase-review.md"
grep -qF '"수정할까요?" 확인' "$REV" && fail "폐지된 4c 질문 잔존: phase-review.md"
grep -qF 'Ruling: review 동작 불변 정리' "$REV" || fail "4b 판정 기록 지시 누락: phase-review.md"
grep -qF 'Ruling: review Minor' "$REV" || fail "4c 판정 기록 지시 누락: phase-review.md"
grep -qF 'reports/review-deferred.md' "$REV" || fail "Deferred 목록 파일 누락: phase-review.md"
grep -qF '## Rulings' "$COMP" || fail "pr-rulings Rulings 절 누락: phase-complete.md"
grep -qF -- '--extra-section ${DEV_DIR}/pr-rulings.md' "$COMP" || fail "extra-section 전달 누락: phase-complete.md Step 2-2"
grep -qF '## Rulings' .claude/skills/gx-pull-request/SKILL.md || fail "PR 본문 Rulings 무요약 규칙 누락: gx-pull-request SKILL.md"
[ "$FAIL" -eq 0 ] && ok "판정 규약 절·폐지 질문 3곳 부재·4b/4c 기록 지시·Deferred·PR 노출 확인"
```

스크립트 헤더의 검사 항목 주석 목록 `# 34. …` 아래에 추가한다:

```
# 35. gx-tdd 구현 내부 게이트 판정 계약 (규약 절·폐지 질문 3곳 부재·4b/4c 기록 지시·Deferred·PR 노출)
```

- [ ] **Step 2: 분모를 35로 올린다**

```bash
sed -i 's|/34\]|/35]|g' scripts/lint-consistency.sh
grep -rlE '\[[0-9]+/34\]' .claude README.md --include=*.md --exclude-dir=worktrees | xargs -r sed -i 's|/34\]|/35]|g'
grep -rnE '\[[0-9]+/34\]' .claude README.md scripts --include=*.md --include=*.sh | grep -v worktrees
```
Expected: 마지막 grep 출력 없음.

- [ ] **Step 3: 변이 시험 (RED)**

Run: `sed -i 's|과잉 구현 판정\*\*: 추가된|과잉 구현 감지**: 추가된|; s|판정할 것이 없으면 아무것도 기록하지 않는다.|판정할 것이 없으면 아무것도 기록하지 않는다. 정리할까요?|' .claude/skills/gx-tdd/phases/phase-implement.md && bash scripts/lint-consistency.sh; echo "exit=$?"; git checkout -- .claude/skills/gx-tdd/phases/phase-implement.md`
Expected: `폐지된 과잉 구현 질문 잔존`으로 FAIL, exit 1. 복원 후 다음 단계.

Run: `sed -i 's|## 판정 기록 (Rulings)|## 판정 기록|' .claude/skills/gx-tdd/phases/phase-implement.md && bash scripts/lint-consistency.sh; echo "exit=$?"; git checkout -- .claude/skills/gx-tdd/phases/phase-implement.md`
Expected: `판정 기록 규약 절 누락`으로 FAIL, exit 1. 복원.

- [ ] **Step 4: 골든 시나리오 행을 추가한다**

S41 행 아래에 추가하고, 기록 절의 `N/41`을 `N/42`로 바꾼다.

```markdown
| S42 ★ | 세션 IMPLEMENT가 테스트에 없는 public 헬퍼를 하나 더 만든 태스크 | `/gx-tdd 포인트 충전 한도 검증 TDD로 구현해줘` | verify_implement 5가 사용자에게 **묻지 않고** 헬퍼를 제거하고 focused를 재실행한다. `.dev/{slug}/decisions.md`에 `· Ruling: T{N} 과잉 구현 정리` 블록(판정·근거·틀리면 3줄)이 append되고 `reports/t{N}-impl.md`에 `## 과잉 구현 정리` 절이 남는다. 사이클 완료 보고의 `판정:` 줄과 PR 본문 `## Rulings`에 제목이 나열된다. AskUserQuestion이 뜨면 회귀 | phase-implement 판정 기록 규약 + 린트 [35/35] |
```

- [ ] **Step 5: CHANGELOG와 버전**

CHANGELOG 상단에 추가한다:

```markdown
## v1.29.0 (2026-09-09)

구현 단계 안의 확인 질문 3곳을 기본값 판정으로 바꾼다. superpowers의 "Rulings, not stalls"를 가져오되 범위는 구현 내부 게이트로 한정한다 — PRD·설계·태스크 분해 승인, SPEC FAIL, Critical, 동작 결함 RGR 여부, 위험 수용은 협업 접점이라 그대로 묻는다. 설계: `docs/specs/2026-09-09-superpowers-gap-design.md` D2.

- **변경 — 판정 기록 규약**: phase-implement `## 판정 기록 (Rulings)` 절이 SSOT. 판정은 `decisions.md`(AskUserQuestion 훅과 같은 파일)에 `Ruling: 제목` 블록(판정·근거·틀리면)으로 append하고, 사이클 완료 보고와 PR 본문 `## Rulings`에 제목을 나열한다
- **변경 — 과잉 구현(verify_implement 5)**: 테스트가 참조하지 않는 신규 public 멤버를 묻지 않고 제거한다(설계서 인터페이스 멤버는 "설계 예약"으로 유지). 제거 목록은 report `## 과잉 구현 정리`에 남긴다
- **변경 — phase-review 4b·4c**: 동작 불변 정리는 수행, quality Minor는 유예, security MEDIUM은 동작 불변이면 정리·아니면 유예. 유예 목록은 `reports/review-deferred.md` → PR 본문 `## Deferred`
- **변경 — gx-pull-request**: `--extra-section` 파일의 `## Rulings`·`## Deferred`는 요약 없이 항목 그대로 싣는다
- **검증 — 린트 [35] 판정 계약**, 골든 S42
```

```bash
sed -i 's|"version": "1.28.0"|"version": "1.29.0"|' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
```
Expected: 세 파일 모두 `1.29.0`.

- [ ] **Step 6: 검증 (GREEN)**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 35/35 통과, 훅 테스트 통과.

- [ ] **Step 7: 커밋**

```bash
git add scripts/lint-consistency.sh .claude README.md tests/golden-scenarios.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json
git commit -F - <<'MSG'
feat: 린트 [35] 판정 계약과 v1.29.0 릴리스 준비
MSG
```

---

## 완료 기준

- 린트 35/35·훅 테스트 통과. phase-implement·phase-review에 폐지된 질문 문구 3개가 없다.
- 골든 S42를 실제로 한 번 돌려 AskUserQuestion 없이 헬퍼가 제거되고 decisions.md에 Ruling 블록이 append되는 것을 눈으로 확인한다 (PR 체크박스).
- 후속: D3(`2026-09-09-context-injection.md`).
