# gx-tdd superpowers 재정렬 Phase A Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-tdd의 implement 단계를 2석(red-writer + implementer)·focused 테스트·report 파일 계약·5라운드 fix loop로 재정렬한다 (설계 v2의 T1·T2·T4·T5·T6·T7·T8).

**Architecture:** 프롬프트/스킬 문서 저장소다 — "구현"은 마크다운 계약 문서와 grep 기반 CI 린트의 수정이며, "테스트"는 `bash scripts/lint-consistency.sh`다. 각 태스크는 린트를 먼저 강화해 FAIL을 목격한 뒤(RED) 본문을 고쳐 통과시킨다(GREEN). 구 트리오(green/refactor) 프롬프트는 gx-ralph가 참조하므로 부록 A로 보존한다.

**Tech Stack:** Markdown 스킬 문서, bash(grep 린트), JSON(config)

**Spec:** `docs/specs/2026-09-01-tdd-superpowers-realign.md` (v2 — 태스크가 이 계획과 충돌하면 spec이 우선)

**개정 이력:** v2 — Momus 계획 리뷰 REVISE 반영 (C-1 헤더·core 분기 교체 누락 / C-2·C-3 검증 grep 실패 확정 / C-4 `{pattern}` 규약 부재 / C-5 test-file producer·hash/count 소실 / C-6 sed 기대값 오류 / I-1~12 / M-1~8)

## Global Constraints

- 모든 문서·커밋 메시지는 한국어. 이모지·사과 표현 금지 (`.claude/rules/behavior.md`)
- **작업 브랜치: `feat/tdd-agent-realign`** — Task 0에서 확인/전환. 다른 브랜치에 커밋 금지
- 커밋 메시지 형식 `{type}: 한국어 요약`, 트레일러 금지 (저장소 관례 — skill-routing.md의 커밋 컨벤션)
- **커밋 방식 예외 선언**: 이 계획의 태스크별 `git commit` 직접 실행은 skill-routing.md의 gx-commit 라우팅 대상이 아니다 — 그 규칙은 "사용자 자연어 커밋 의도"와 "gx-dev/gx-tdd 파이프라인 내부"에 적용되며, superpowers 계획 실행은 어느 쪽도 아니다 (gx-ralph-iterate 헤드리스 커밋과 같은 층위의 예외). 메시지 컨벤션은 동일하게 준수한다
- 검증 명령: `bash scripts/lint-consistency.sh` — 통과 기준: exit 0, `FAIL:` 출력 0건 (fail()의 실제 출력 형식은 `  FAIL: {메시지}`)
- 확인 게이트(AskUserQuestion) 관련 문구는 절대 제거하지 않는다 (spec D1)
- 구 Step 2-G/2-F 트리오 프롬프트는 삭제 금지 — 부록 A로 이동 보존, **본문 무변경·헤더만 개칭 허용** (Task 2 Step 4)
- verify 게이트·지문(fingerprint)·훅 G3 관련 문구는 수정 금지 (spec: verify 계약 불변)
- 린트 항목 번호는 Task 8 전까지 기존 `[N/25]` 유지 — 분모 일괄 갱신은 Task 8에서만
- 기존 문서의 문체(개조식·한국어 서술)와 포맷을 따른다. 계획에 없는 절은 수정하지 않는다
- state.md 계약 리터럴 (여러 파일 완전 일치 필수): `"RGR T{N}: IMPLEMENT"`, `"RGR T{N}: FIX R{r}"`, steps 하위 키 `red`/`impl`, 필드 `test-file`/`test-file-hash`/`test-count`/`report`/`fix-round: {r}/5`, 상한 문자열 `라운드 5`
- **중간 커밋의 자기모순 허용**: Task 2 완료 시점에 SKILL.md 등 다른 파일의 트리오 서술은 아직 구식이다 — 이를 잡는 린트 검사는 없으며, Phase A 8커밋이 한 배포 단위(PR)로 묶이므로 의도된 상태다

---

### Task 0: 작업 브랜치 확인

**Files:** 없음 (git 상태만)

- [ ] **Step 1: 브랜치 전환/확인**

```bash
git checkout feat/tdd-agent-realign 2>/dev/null || git checkout -b feat/tdd-agent-realign
git branch --show-current
```

Expected: `feat/tdd-agent-realign`

- [ ] **Step 2: 린트 기준선 확인**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3`
Expected: exit 0, `FAIL:` 0건 (시작 전 기준선이 GREEN임을 확인 — 아니면 중단하고 보고)

---

### Task 1: agents/implementer.md 신설

**Files:**
- Create: `agents/implementer.md`
- Modify: `scripts/lint-consistency.sh:64` (REFACTOR_FILES)
- Modify: `agents/green-coder.md:28`, `agents/refactor-coder.md:28` (헤더 노트)

**Interfaces:**
- Produces: 에이전트 이름 `implementer` (디스패치명 `oh-my-gx:implementer`) — Task 2의 Step 2-I 디스패치, Task 6의 phase-review Step 0, Task 7의 SKILL.md 표가 사용
- Produces: implementer.md 본문의 금지 키워드 5종("동작 변경"·"새 기능 추가"·"에러 핸들링"·"성능 최적화"·"인터페이스 시그니처 변경") — 린트 [3/25] REFACTOR_FILES 검사가 소비. 4-status 리터럴(DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED) — Task 8의 [26/26]이 소비

- [ ] **Step 1: 린트 REFACTOR_FILES에 implementer 추가 (RED)**

`scripts/lint-consistency.sh:64`를 Edit:

```
old: REFACTOR_FILES="agents/refactor-coder.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-refactor/SKILL.md"
new: REFACTOR_FILES="agents/refactor-coder.md agents/implementer.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-refactor/SKILL.md"
```

- [ ] **Step 2: 린트 실행 — FAIL 확인**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep "FAIL:" | head -5`
Expected: `  FAIL: refactor 금지 항목 '동작 변경' 누락: agents/implementer.md` 등 (파일 부재로 [3/25]의 5종 검사 실패)

- [ ] **Step 3: agents/implementer.md 작성**

전문 (frontmatter 포함, 이대로 생성):

````markdown
---
name: implementer
description: |
  GREEN+REFACTOR 통합 구현 에이전트. 실패 테스트를 통과시키는 최소 코드를 작성한 뒤(GREEN), GREEN 상태를 유지하며 중복 제거·네이밍 개선·구조 정리를 수행한다(REFACTOR). 테스트 파일은 절대 수정하지 않는다. oh-my-gx:gx-tdd 파이프라인 전용 — 단독 스킬(gx-green·gx-refactor)과 gx-ralph 루프는 green-coder/refactor-coder를 계속 사용한다.

  <example>
  Context: red-writer가 실패 테스트를 작성하여 report 파일로 인계
  user: (오케스트레이터) reports/t1-red.md를 읽고 PasswordValidatorTest.shouldReject401을 통과시킨 뒤 정리까지 수행해줘
  assistant: implementer가 최소 구현으로 통과시키고, 매직 넘버 상수화 정리 후 focused 테스트 재확인, self-review를 거쳐 reports/t1-impl.md에 보고를 작성하고 DONE 상태를 반환
  </example>

  <example>
  Context: 리뷰 findings 수정 라운드 (fix loop)
  user: (오케스트레이터) 미해결 findings 2건을 수정해줘 (라운드 2)
  assistant: implementer가 수정 후 focused 테스트를 재실행하고 fix report를 reports/t1-impl.md에 append, 상태 반환
  </example>
model: sonnet
color: green
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# implementer

당신은 GREEN+REFACTOR 통합 구현 에이전트입니다. 실패 테스트를 통과시키는 **최소 코드**를 작성한 뒤, GREEN 상태를 유지하며 **정리만** 수행합니다.

## 절대 규칙

1. **테스트 파일을 수정하지 않습니다.** 테스트가 실패하면 코드를 고치고, 테스트를 고치지 않습니다. 테스트 자체 결함이 의심되면 수정하지 말고 "테스트 결함 의심"으로 보고합니다.
2. **GREEN**: 실패 테스트를 통과시키는 최소 코드만 작성합니다. 추가 기능·에러 핸들링·검증·로깅을 미리 넣지 않습니다 (YAGNI).
3. **REFACTOR**: 동작 변경 금지. 새 기능 추가 금지. 매 정리 후 focused 테스트로 GREEN 유지를 확인하고, 깨지면 즉시 되돌립니다.
4. **테스트 실행은 focused 집합만.** 오케스트레이터가 전달한 focused 테스트 명령만 실행합니다. 전체 스위트를 실행하지 않습니다 (전체 회귀는 파이프라인 경계에서 1회 실행됩니다).
5. 서브에이전트를 디스패치하지 않습니다. 리뷰는 오케스트레이터가 별도로 수행합니다.

## 입력

- **RED report 경로**: red-writer의 보고 파일 (테스트 파일 경로·코드·실패 메시지). Read하여 시작한다
- **설계서 인터페이스**: 대상 컴포넌트의 시그니처
- **focused 테스트 명령**: 이 태스크에서 실행할 테스트 명령 (오케스트레이터가 조립)
- **report 파일 경로**: 보고를 작성할 파일
- **프로젝트 루트**: 파일 도구 기준점

## 작업 절차

1. RED report를 Read하여 실패 테스트와 실패 사유를 파악한다
2. **GREEN**: 테스트를 통과시키는 가장 단순한 구현 작성 → focused 테스트 실행으로 통과 확인
3. **REFACTOR**: 중복 제거(Extract Method)·변수/함수 이름 개선·구조 정리·매직 넘버 상수화 → 매 정리 후 focused 테스트로 GREEN 재확인, 깨지면 롤백
4. **self-review** (보고 전 자기 diff 검토):
   - 완전성: 테스트가 요구하는 동작을 전부 구현했는가, 놓친 요구가 없는가
   - 품질: 이름이 하는 일과 일치하는가, 코드가 유지보수 가능한가
   - 규율: 과잉 구현(YAGNI 위반)이 없는가, 요청된 것만 만들었는가, 기존 코드베이스 패턴을 따랐는가
   - 테스트: 테스트가 모의가 아닌 실제 동작을 검증하는가, 출력이 깨끗한가(경고·노이즈 없음)
   - 발견한 문제는 지금 수정한 후 보고한다
5. report 파일에 전문 보고를 Write한다 (아래 형식)
6. 상태를 반환한다 (15줄 이내)

## 수행 불가능한 정리 (REFACTOR 범위 제한)

- 동작 변경
- 새 기능 추가
- 에러 핸들링 추가
- 성능 최적화
- 인터페이스 시그니처 변경

## report 파일 형식 (전문 — report 경로에 Write)

```
# T{N} 구현 보고

## 구현 내용
{무엇을 구현했는가 — 파일별}

## GREEN 증거
- 실행 명령: {focused 명령}
- 결과: {N pass, 0 fail — 출력 마지막 줄}

## REFACTOR 내역
1. {정리 항목} → ✅ 테스트 통과 (또는 ❌ 롤백)

## self-review 결과
{발견·수정 항목, 없으면 "발견 없음"}

## 우려사항
{있으면 구체적으로, 없으면 "없음"}
```

fix 라운드에서는 같은 파일에 `## fix 라운드 {r}` 섹션을 **append**한다: 수정 내용 + 재실행한 focused 명령과 출력.

## 상태 반환 (최종 메시지 — 15줄 이내)

- **Status**: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- 변경 파일: {목록}
- 테스트: {예: "3/3 pass (focused)"}
- 우려사항: {1~2줄, 없으면 "없음"}
- report: {report 파일 경로}

DONE_WITH_CONCERNS는 완료했으나 정합성에 의심이 있을 때, NEEDS_CONTEXT는 제공되지 않은 정보가 필요할 때, BLOCKED는 수행 불가일 때 사용한다. 확신 없는 결과를 조용히 제출하지 않는다.

## Red Flags

다음 생각이 들면 STOP:
- "이 정도는 미리 처리해도 될 듯" / "이왕 만드는 김에 X도" → YAGNI 위반
- "테스트를 조금만 고치면 통과할 텐데" → 테스트 무결성 위반. 보고만 한다
- "전체 테스트를 한 번 돌려보자" → focused 집합만. 전체는 경계에서
````

- [ ] **Step 4: green-coder·refactor-coder 헤더 노트 추가**

`agents/green-coder.md:28`의 `# green-coder` 제목 바로 아래에 추가:

```
> **호출 범위**: oh-my-gx:gx-tdd 파이프라인에서는 호출하지 않는다 (implementer로 통합됨) — 단독 스킬(gx-green)·gx-ralph 루프 전용. deprecated 아님.
```

`agents/refactor-coder.md:28`의 `# refactor-coder` 제목 바로 아래에 추가:

```
> **호출 범위**: oh-my-gx:gx-tdd 파이프라인에서는 호출하지 않는다 (implementer로 통합됨) — 단독 스킬(gx-refactor)·gx-ralph 루프 전용. deprecated 아님.
```

- [ ] **Step 5: 린트 통과 확인 (GREEN)**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3`
Expected: exit 0, `FAIL:` 0건

- [ ] **Step 6: Commit**

```bash
git add agents/implementer.md agents/green-coder.md agents/refactor-coder.md scripts/lint-consistency.sh
git commit -m "feat: implementer 에이전트를 신설한다 (GREEN+REFACTOR 통합)"
```

---

### Task 2: phase-implement Step 2 재작성 — 헤더·2-I·verify_implement·fix loop·부록 A

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (:9-14 헤더, :26-27 core 분기, :151-172 Step 2 골격, Step 2-G/2-F 이동, Step 3 격상 규칙, Step H3)
- Modify: `scripts/lint-consistency.sh:72-73` (린트 [3]의 phase-implement 상한 검사)

**Interfaces:**
- Consumes: Task 1의 `oh-my-gx:implementer`
- Produces: 리터럴 `"라운드 5"`(린트 [3]), `"RGR T{N}: IMPLEMENT"`·`"RGR T{N}: FIX R{r}"`(Task 3·7 사용), 부록 A 헤더 `## 부록 A: gx-ralph 전용 트리오 프롬프트 (구 Step 2-G/2-F)`(Task 6이 참조), verify_implement의 focused 조립 규약(`{files}`·`{pattern}` — Task 5의 focusedTest 필드를 소비), `reports/` 생성 규칙

- [ ] **Step 1: 린트 [3] 상한 검사 교체 (RED)**

`scripts/lint-consistency.sh:72-73`을 Edit:

```
old: grep -q "최대 2회" .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "green 재호출 상한(최대 2회) 누락: phase-implement.md"
new: grep -q "라운드 5" .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "fix 라운드 상한(라운드 5) 누락: phase-implement.md"
```

(바로 아래의 gx-green/SKILL.md "최대 2회" 검사는 그대로 둔다 — 단독 스킬은 현행 계약)

- [ ] **Step 2: 린트 실행 — FAIL 확인**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep "FAIL:"`
Expected: `  FAIL: fix 라운드 상한(라운드 5) 누락: phase-implement.md`

- [ ] **Step 3: 파일 헤더(:9-14) 교체**

```
old: 이 Phase는 **3 에이전트가 순차 사이클로 동작**한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님)
- **green-coder** → 통과 최소 코드 (입력은 실패 테스트+시그니처로 한정하되, 구현을 위한 기존 코드 Read는 허용 — red-writer 수준의 차단 아님)
- **refactor-coder** → 안전한 정리 (동작 변경 금지)

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.
new: 이 Phase는 **2 에이전트가 순차 사이클로 동작**한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님)
- **implementer** → 통과 최소 코드(GREEN) + 안전한 정리(REFACTOR — 동작 변경 금지). 입력은 RED report+시그니처로 한정하되, 구현을 위한 기존 코드 Read는 허용 — red-writer 수준의 차단 아님. 테스트 실행은 focused 집합만

위반 시 즉시 중단하고 사이클 처음(RED)부터 재시작한다.

> green-coder·refactor-coder는 이 파이프라인에서 호출하지 않는다 — 단독 스킬(gx-green·gx-refactor)·gx-ralph 루프 전용 (부록 A 참조).
```

- [ ] **Step 4: core 분기(:26-27) 교체**

```
old:   - green-coder 입력: 실패 테스트 + 기존 코드 인터페이스 (설계서 없음).
  - refactor-coder 입력: 정리 대상.
new:   - implementer 입력: RED report 경로 + 기존 코드 인터페이스 (설계서 없음) + focused 테스트 명령.
```

- [ ] **Step 5: Step 2 골격(:151-172) 교체**

old (전문 — 코드 펜스 포함 22줄):

````
## Step 2: RGR 사이클 (태스크별 순차)

각 태스크에 대해 **반드시 RED → GREEN → REFACTOR 순서로 실행**한다. 병렬 금지 (Iron Law).

```
for task in tasks:
    current_task = task

    # 2-R: RED
    red_result = dispatch_red(task)
    verify_red(red_result)  # 실패 확인 필수

    # 2-G: GREEN
    green_result = dispatch_green(task, red_result)
    verify_green(green_result)  # 통과 확인 + 전체 테스트 회귀 확인

    # 2-F: REFACTOR
    refactor_result = dispatch_refactor(task, green_result)
    verify_refactor(refactor_result)  # GREEN 유지 확인

    record_to_state(task, results)
```
````

new:

````
## Step 2: RGR 사이클 (태스크별 순차)

각 태스크에 대해 **반드시 RED → IMPLEMENT(GREEN+REFACTOR) 순서로 실행**한다. 병렬 금지 (Iron Law).

**진입 준비**: `mkdir -p ${DEV_DIR}/reports`를 실행한다 (핵심 모드처럼 Step 1을 건너뛴 경로 포함 — 모든 진입 경로 공통). 이후 에이전트 보고는 `reports/t{N}-red.md`·`reports/t{N}-impl.md`에 파일로 저장되고, 인계는 **파일 경로로만** 이루어진다 (전문 인라인 전달 금지 — 컨텍스트 경량화). `.dev/` 공유 정책에 따라 커밋에 포함된다.

```
for task in tasks:
    current_task = task

    # 2-R: RED
    red_result = dispatch_red(task)          # report: reports/t{N}-red.md
    verify_red(red_result)                   # 실패 확인 필수 (오케스트레이터 직접 실행)

    # 2-I: IMPLEMENT (GREEN + REFACTOR 통합)
    impl_result = dispatch_implementer(task, red_report_path)   # report: reports/t{N}-impl.md
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증

    record_to_state(task, results)
```
````

- [ ] **Step 6: Step 2-G/2-F를 부록 A로 이동**

`### Step 2-G: GREEN (green-coder 디스패치)`(:245) 헤더부터 `` `current-step`을 `"RGR T{N}: REFACTOR"`로 갱신. ``(:350)과 그 뒤 `---`(:352)까지 **잘라내어**, 파일 맨 끝(금지 사항 절 뒤)에 아래 헤더와 함께 붙인다. **본문은 한 글자도 바꾸지 않되, 두 절의 헤더만 개칭한다** (죽은 참조 검증 grep이 "구 Step"으로 식별할 수 있게):

- `### Step 2-G: GREEN (green-coder 디스패치)` → `### 구 Step 2-G: GREEN (green-coder 디스패치 — gx-ralph 전용)`
- `### Step 2-F: REFACTOR (refactor-coder 디스패치)` → `### 구 Step 2-F: REFACTOR (refactor-coder 디스패치 — gx-ralph 전용)`

부록 도입부:

```markdown
## 부록 A: gx-ralph 전용 트리오 프롬프트 (구 Step 2-G/2-F)

> 이 부록은 gx-tdd 파이프라인이 사용하지 않는다. `gx-ralph-iterate`(헤드리스 반복)가 origin: gx-tdd 루프에서 red-writer → green-coder → refactor-coder 트리오를 디스패치할 때의 프롬프트 소스로만 보존된다. 파이프라인 본문은 Step 2-I(implementer)를 사용한다.
```

- [ ] **Step 7: Step 2-I 절 신설**

부록 A로 옮겨 비워진 자리(Step 2-R 절의 `---` 다음)에 삽입:

````markdown
### Step 2-I: IMPLEMENT (implementer 디스패치 — GREEN+REFACTOR 통합)

```
Task(subagent_type="oh-my-gx:implementer"):
  description: "IMPLEMENT: Pass & clean {component}"
  prompt: |
    당신은 GREEN+REFACTOR 통합 구현 전담자입니다.

    [절대 규칙]
    1. 테스트 파일을 수정하지 않습니다. 테스트가 실패하면 코드를 고치고, 테스트를 고치지 않습니다. 테스트 자체 결함이 의심되면 수정하지 말고 "테스트 결함 의심"으로 보고합니다.
    2. GREEN: 실패 테스트를 통과시키는 최소 코드만 작성합니다 (YAGNI — 추가 기능/에러 핸들링/검증/로깅 금지).
    3. REFACTOR: 동작 변경 금지. 매 정리 후 focused 테스트로 GREEN 유지 확인, 깨지면 즉시 롤백.
    4. 테스트 실행은 아래 focused 명령만 사용합니다. 전체 스위트를 실행하지 않습니다.
    5. 보고 전 self-review(완전성/품질/규율/테스트 4관점)를 수행하고 발견 즉시 수정합니다.

    [RED report]
    - 경로: {reports/t{N}-red.md} — Read하여 실패 테스트(파일·코드·실패 메시지)를 파악하십시오

    [설계서 인터페이스]
    {대상 컴포넌트의 시그니처만}

    [focused 테스트 명령]
    {오케스트레이터가 조립한 명령 — 대상 테스트 + 이번 파이프라인 실행의 신규 테스트 전부}

    [report 파일]
    {reports/t{N}-impl.md} — 전문 보고를 이 파일에 Write하십시오 (agents/implementer.md의 report 형식)

    [프로젝트 루트]
    {PROJECT_ROOT}

    [반환 형식 — 15줄 이내]
    - Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
    - 변경 파일 / 테스트 1줄 요약 / 우려사항 / report 경로
```

**focused 테스트 명령 조립**: config.json `projectTypes.{타입}.focusedTest` 템플릿을 사용한다. 대상은 이 태스크의 테스트 파일 + 이번 파이프라인 실행에서 이전 태스크들이 만든 신규 테스트 파일 전부(state.md 각 태스크의 `test-file` 기록)다.
- `{files}` 플레이스홀더: 테스트 파일 경로들을 공백 구분으로 치환한다 (예: `npx vitest run src/a.spec.ts src/b.spec.ts`).
- `{pattern}` 플레이스홀더: 각 테스트 파일명(확장자 제외)에서 유도한 클래스 글롭 `*.{파일명}`으로 치환하고, 복수 파일이면 플레이스홀더를 포함한 인자를 반복한다 (예: `./gradlew test --tests *.PaymentLimitTest --tests *.PaymentServiceTest`).
- `focusedTest` 필드가 없으면 해당 타입의 전체 `test` 명령을 사용하고 execution-log에 `"focused 미지원 — 전체 실행 폴백"`을 기록한다.

**verify_implement**: 오케스트레이터가 직접 검증. **저비용 검사(1~3번)를 테스트 실행보다 먼저 수행한다.**
1. **Status 분기**: `NEEDS_CONTEXT` → 요청된 정보를 보강해 재디스패치 (라운드 미소모). `BLOCKED` → 컨텍스트 보강 / 모델 격상 / 태스크 분할 / 설계 재확인 중 판정 후 처리. `DONE_WITH_CONCERNS` → report의 우려를 Read하고 정합성 문제면 fix 라운드로, 관찰이면 기록 후 진행.
2. **테스트 결함 의심 확인**: 보고됐으면 사유 확인 후 **red-writer 재호출**로 테스트를 재작성한다 (implementer가 테스트를 고치지 않는다).
3. **테스트 무결성 확인**: `git hash-object "{테스트 파일}"`을 재실행하여 verify_red의 `test-file-hash`와 비교하고, `git status --porcelain`(svn은 `svn status`)을 verify_red 스냅샷 파일(`${DEV_DIR}/rgr-t{N}-porcelain.txt`)과 대조한다 — **대조는 테스트 파일 라인만 필터**하여 수행한다(판별 글롭은 Step 0.5 4항의 테스트 파일 글롭 `**/*test*`·`**/*Test*`·`**/*spec*` 재사용. `.dev/` 경로 라인은 제외). **이전 태스크들의 `test-file-hash`도 재검증**한다. 무단 수정 감지 → 해당 테스트를 RED 산출물로 원복하고 implementer 재호출 1회 ("테스트 수정 금지" 재강조 — fix 라운드와 별도 카운트). 재차 위반 시 사이클 중단·사용자 보고.
4. **focused 집합 직접 실행**: 위 focused 명령을 오케스트레이터가 1회 직접 실행한다 — 통과 목격(증거 주체는 오케스트레이터, verify_red와 대칭) + 결과의 테스트 수를 state.md 해당 태스크의 `test-count`로 기록한다(직전 태스크의 같은 방식 값과 비교해 감소 시 사유 확인 — 무단 삭제면 롤백 요청). **전체 스위트는 실행하지 않는다** — 전체 회귀는 사이클 경계(전체 모드: phase-review Step 0 Mechanical Gate / 핵심 모드·`--phase implement` 단독: Step 3.5)가 담당한다.
5. **과잉 구현 감지**: 추가된 메서드/필드 중 테스트에서 안 쓰는 것 → 사용자에게 보고: "과잉 구현 감지. YAGNI 권고로 다음 RED 단계로 미루는 것이 좋습니다. 정리할까요?"
6. ✅ 통과 + 무결성 유지 → 태스크 완료, 다음 태스크로 진행.
7. ❌ 실패 → **fix loop 진입** (아래).

**fix loop (실패 시 — 태스크당 최대 5라운드)**:

| 라운드 | 방식 | 모델 |
|--------|------|------|
| 1~3 | **같은 implementer를 재개** — 하네스가 서브에이전트 재개(후속 메시지)를 지원하면 그 방식으로 미해결 항목을 전달, 지원하지 않으면 report 파일 경로를 실은 fresh 디스패치 (report가 영속 기억) | sonnet |
| 4~5 | **fresh 디스패치 + 모델 격상** (`model: "opus"` 오버라이드) — 프롬프트에 "이전 구현자가 {r-1}회 시도했다. report 파일에서 시도 내역을 읽어라"를 포함 | opus |

- 매 라운드: implementer가 수정 → focused 재실행 → fix report를 같은 report 파일에 append → 상태 반환 → 오케스트레이터가 verify_implement 재수행. `current-step`을 `"RGR T{N}: FIX R{r}"`로, state.md 해당 태스크에 `fix-round: {r}/5`를 기록한다.
- 모델 격상은 "실패의 대응"으로 **모델 프로파일과 독립**이다 — eco 세션에서도 라운드 4~5는 opus로 격상한다.
- **라운드 5 소진 시**: 사이클 중단 + AskUserQuestion — "수동 수정 후 계속" / "태스크 스킵 (위험 수용 — trust-ledger 기록)" / "중단".

`current-step`을 `"RGR T{N}: IMPLEMENT"`로 갱신.
````

- [ ] **Step 8: Step 3 격상 규칙·표 갱신**

`:365-368` 교체:

```
old: **3회 실패 시 아키텍처 격상** (superpowers 패턴):
- 같은 태스크에서 green-coder가 3회 실패하면(최초 1회 + 재호출 2회 소진) → 사이클 중단. **재호출 상한 소진 시점에는 이 격상 경로가 DIMINISHING_RETURNS 에스컬레이션보다 우선한다.**
- architect에 "이 태스크의 설계가 잘못된 것 같다. 재설계 필요" 위임.
- architect 결과로 설계서 갱신 후 RGR 사이클 재시작.
new: **fix loop 소진 시 아키텍처 격상** (superpowers 패턴):
- fix loop **라운드 4 진입(모델 격상)이 DIMINISHING_RETURNS 에스컬레이션보다 우선한다.** 라운드 5까지 소진하면 사이클을 중단하고 소진 처리(Step 2-I)를 따르되, 실패 양상이 설계 결함을 가리키면 architect에 "이 태스크의 설계가 잘못된 것 같다. 재설계 필요"를 위임한다.
- architect 결과로 설계서 갱신 후 RGR 사이클 재시작.
```

Step 3 표(:360-362)의 에이전트명 치환 3곳: `green-coder가 같은 컴파일 에러 반복` → `implementer가 같은 컴파일 에러 반복`, `green-coder가 구현 접근법 왕복` → `implementer가 구현 접근법 왕복`, `refactor-coder 결과 diff 없음` → `implementer의 REFACTOR 결과 diff 없음`.

- [ ] **Step 9: Step H3 트리오 문구 교체 (:426)**

```
old:   - "자동 수정 시도" → **RGR 사이클 재진입**: 보안 항목을 새 AC로 정의하여 red-writer(새 실패 테스트) → green-coder → refactor-coder 순서로 수정한다 (Step 2-R/G/F 재실행). green-coder를 RED 없이 직접 호출하지 않는다.
new:   - "자동 수정 시도" → **RGR 사이클 재진입**: 보안 항목을 새 AC로 정의하여 red-writer(새 실패 테스트) → implementer 순서로 수정한다 (Step 2-R/2-I 재실행). implementer를 RED 없이 직접 호출하지 않는다.
```

- [ ] **Step 10: 린트 통과 확인 (GREEN)**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3`
Expected: exit 0, `FAIL:` 0건 (부록 A가 트리오 금지 키워드를 보존하므로 [3/25] 통과 유지)

- [ ] **Step 11: Commit**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md scripts/lint-consistency.sh
git commit -m "feat: RGR 사이클을 2석(red-writer+implementer)으로 전환하고 fix loop 5라운드를 도입한다"
```

---

### Task 3: phase-implement 주변부 — 배칭·태스크 표·경계 회귀·state·resume

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (Step 1, Step 2-R, Step 3.5 신설, Step 4, state.md 추적, --resume, 금지 사항)

**Interfaces:**
- Consumes: Task 2의 리터럴 (`"RGR T{N}: IMPLEMENT"`, `"RGR T{N}: FIX R{r}"`, `reports/`)
- Produces: steps 하위 키 `red`/`impl`, 필드 `test-file`/`test-file-hash`/`test-count`/`report`/`fix-round` — Task 7의 SKILL.md state 스키마가 동일 형태를 사용

- [ ] **Step 1: Step 1 태스크 조건 1·2에 배칭·2석 반영**

`:101` 교체:

```
old: 1. **단일 AC 또는 단일 컴포넌트**에 매핑된다.
new: 1. **단일 AC 또는 단일 컴포넌트**에 매핑된다. 단, **같은 패턴의 소형 변경으로 환산되는 AC들**(동일 검증 로직의 필드별 반복, 동일 형태의 매핑 추가 등)은 하나의 태스크로 배칭할 수 있다 — RED는 테이블 드리븐 또는 케이스별 테스트를 한 파일에 작성하고, 한 번의 R→I 사이클로 처리하며, 태스크 표의 AC 매핑에 `AC-2~AC-4 (배칭)` 형태로 표기해 승인 게이트에서 확인받는다. 분리 기준: 독자적 판단·독자적 테스트 전략·독자적 리뷰 표면이 필요한 작업만 태스크를 분리한다.
```

`:102` 교체:

```
old: 2. **2-15분 단위**로 RED→GREEN→REFACTOR 완료 가능한 크기.
new: 2. **2-15분 단위**로 RED→IMPLEMENT 완료 가능한 크기.
```

- [ ] **Step 2: 태스크 표 템플릿(1.1) 갱신**

표 헤더·예시 행(:112-116)을 교체:

```
old: | # | AC 매핑 | 컴포넌트 | RED (테스트 작성) | GREEN (구현) | REFACTOR (정리) |
|---|---------|---------|-------------------|--------------|-----------------|
| 1 | AC-1 | PaymentLimit | PaymentLimitTest.shouldRejectExceededLimit | PaymentLimit.kt: data class + validate() | 매직 넘버 상수화 |
| 2 | AC-2 | PaymentService | PaymentServiceTest.shouldThrowOnExcess | PaymentService.processPayment() 한도 검증 추가 | 중복 검증 로직 추출 |
| 3 | AC-3 | PaymentController | PaymentControllerE2ETest | PaymentController.updateLimit() 엔드포인트 | — |
new: | # | AC 매핑 | 컴포넌트 | RED (테스트 작성) | IMPLEMENT (구현+정리) |
|---|---------|---------|-------------------|------------------------|
| 1 | AC-1 | PaymentLimit | PaymentLimitTest.shouldRejectExceededLimit | PaymentLimit.kt: data class + validate() → 매직 넘버 상수화 |
| 2 | AC-2, AC-3 (배칭) | PaymentService | PaymentServiceTest (케이스 2건) | PaymentService.processPayment() 한도 검증 추가 → 중복 검증 로직 추출 |
| 3 | AC-4 | PaymentController | PaymentControllerE2ETest | PaymentController.updateLimit() 엔드포인트 |
```

- [ ] **Step 3: Step 2-R에 report 지시·verify_red 갱신**

Step 2-R 디스패치 프롬프트의 `[출력 형식]` 앞에 삽입:

```
    [report 파일]
    {reports/t{N}-red.md} — 테스트 코드 전문·실패 확인 명령·실패 메시지를 이 파일에 Write하고, 최종 메시지에는 아래 출력 형식의 요약만 반환하십시오
```

verify_red 6항(:238)의 끝에 문장 추가: `테스트 파일 경로를 state.md 해당 태스크의 \`test-file\`로 기록한다 (focused 집합 조립에 사용).`

verify_red 6항 뒤에 7항을 삽입하고 기존 7항(:239)을 8항으로 밀며 문구를 갱신:

```
7. **report 저장 확인**: `reports/t{N}-red.md`가 존재하고 테스트 코드·실패 메시지를 담고 있는지 확인한다. 다음 단계(2-I) 인계는 이 파일 경로로만 한다.
8. ✅ 실패 정상 → IMPLEMENT(2-I)로 진행.
```

(기존 `7. ✅ 실패 정상 → GREEN으로 진행.`을 위 8항으로 교체)

- [ ] **Step 4: Step 3.5 신설 + Step 4 보고 양식 갱신**

`## Step 4: 사이클 완료 보고` 헤더(:372) 앞에 삽입:

```markdown
## Step 3.5: 경계 회귀 (핵심 모드·--phase implement 단독 전용)

**핵심 모드** 또는 **`--phase implement` 단독 실행**이면 전체 테스트를 1회 실행한다 — 사이클 중 focused만 돌렸으므로 기존 스위트 회귀를 여기서 확인한다 (전체 모드는 phase-review Step 0 Mechanical Gate가 이 역할을 겸하므로 건너뛴다). 실패 시 깨진 테스트를 implementer에 전달해 수정한다 (fix loop 규칙 적용).

---
```

Step 4 보고 예시(:379-381) 교체:

```
old: - T1 (AC-1): RED ✅ → GREEN ✅ → REFACTOR ✅
- T2 (AC-2): RED ✅ → GREEN ✅ → REFACTOR ✅ (회귀 0건)
- T3 (AC-3): RED ✅ → GREEN ✅ → REFACTOR — (정리 대상 없음)
new: - T1 (AC-1): RED ✅ → IMPLEMENT ✅
- T2 (AC-2, AC-3 배칭): RED ✅ → IMPLEMENT ✅ (fix 라운드 1회)
- T3 (AC-4): RED ✅ → IMPLEMENT ✅ (정리 대상 없음)
```

`:383` 교체: `전체 테스트: {N pass}, 0 fail` → `focused 누적: {N pass}, 0 fail (전체 회귀는 경계에서 — 전체 모드: review Step 0 / 핵심 모드·단독: Step 3.5)`
`:387` 교체: `- T2 GREEN 단계에서 과잉 구현 감지 → 사용자 승인으로 다음 RED로 미룸` → `- T2 IMPLEMENT 단계에서 과잉 구현 감지 → 사용자 승인으로 다음 RED로 미룸`

- [ ] **Step 5: state.md 추적·execution-log·--resume·금지 사항 갱신**

state.md 태스크 블록(:440-451) 교체:

```
old:     - "RGR T1 (AC-1)":
        red: completed
        green: completed
        refactor: completed
    - "RGR T2 (AC-2)":
        red: completed
        green: completed
        refactor: skipped (대상 없음)
    - "RGR T3 (AC-3)":
        red: completed
        green: in_progress
        refactor: pending
new:     - "RGR T1 (AC-1)":
        red: completed
        test-file: src/test/.../PaymentLimitTest.java   # verify_red 기록 — focused 집합 조립에 사용
        test-file-hash: 3ca970cc...   # verify_red 기록 — verify_implement 무결성 비교 기준선
        test-count: 47                # verify_implement 기록 — focused 직접 실행 결과 (테스트 삭제 감지 기준선)
        report: reports/t1-impl.md
        impl: completed
    - "RGR T2 (AC-2)":
        red: completed
        impl: in_progress
        fix-round: 2/5
    - "RGR T3 (AC-3)":
        red: pending
        impl: pending
```

execution-log의 green/refactor 2항목(:459-465) 교체:

```
old: - phase: implement
  agent: green-coder (T1)
  result: "최소 구현 + 통과 + 회귀 0건"
- phase: implement
  agent: refactor-coder (T1)
  result: "매직 넘버 상수화 + GREEN 유지"
new: - phase: implement
  agent: implementer (T1)
  result: "최소 구현 + focused 3/3 pass + 매직 넘버 상수화"
```

--resume 3줄(:474-476) 교체:

```
old: - `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: GREEN"` → 해당 태스크의 GREEN부터 재시작 (RED는 file에서 복원)
- `"RGR T{N}: REFACTOR"` → 해당 태스크의 REFACTOR부터 재시작
new: - `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: IMPLEMENT"` → 해당 태스크의 implementer 재디스패치 (RED report는 reports/t{N}-red.md에서 복원)
- `"RGR T{N}: FIX R{r}"` → 해당 태스크의 fix loop 라운드 {r}부터 재개 (report 파일이 영속 기억)
- 구 세션 호환: `"RGR T{N}: GREEN"`/`"RGR T{N}: REFACTOR"`(3석 세대) → 해당 태스크를 implementer 재디스패치로 이어받는다. red 산출물(테스트 파일)은 유효하므로 RED 재실행 불필요. reports/가 없으므로 이 재개에 한해 테스트 코드·실패 메시지의 인라인 인계를 허용하고 execution-log에 "2석 전환 재개 — 인라인 인계"를 기록한다
```

금지 사항 갱신 (:484, :491):

```
old: - ❌ `coder` (deprecated — red-writer/green-coder/refactor-coder로 분해됨)
new: - ❌ `coder` (deprecated) / `green-coder`·`refactor-coder` (파이프라인 미호출 — implementer로 통합. 단독 스킬·gx-ralph 전용)
```

```
old: - ❌ 검증 명령 생략 (verify_red/green/refactor) — Iron Law 3 위반
new: - ❌ 검증 명령 생략 (verify_red/verify_implement) — Iron Law 3 위반
```

- [ ] **Step 6: 검증**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0, `FAIL:` 0건
Run: `grep -c "RGR T{N}: IMPLEMENT" .claude/skills/gx-tdd/phases/phase-implement.md` → 2 이상
Run: `grep -n "green: \|refactor: " .claude/skills/gx-tdd/phases/phase-implement.md` → 출력 없음 (state 예시의 구 키 제거 확인 — 부록 A의 프롬프트 산문에는 이 패턴이 없음)

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md
git commit -m "feat: 배칭·경계 회귀·state 리터럴·구 세션 재개 호환을 정의한다"
```

---

### Task 4: red-writer 테스트 품질 가드 보강 — Name the Break + 변이 점검 (3중 동기)

**Files:**
- Modify: `.claude/skills/gx-tdd/references/testing-anti-patterns.md` (Principle 1 이식 + 출처 정정)
- Modify: `agents/red-writer.md`, `.claude/skills/gx-tdd/phases/phase-implement.md`(Step 2-R), `.claude/skills/gx-red/SKILL.md` (3중 동기)

**Interfaces:**
- Produces: 가드 불릿 4종(아래) — 3파일 동일 문구 유지 대상 (첫 불릿의 `깨짐 명명` 키워드가 검증 grep 대상)

- [ ] **Step 1: testing-anti-patterns.md에 이식**

`## 모의 3원칙` 헤더(:11) 앞에 삽입:

````markdown
## 깨짐 명명 원칙 (Name the Break)

테스트 본문을 쓰기 전에 답한다: **어떤 프로덕션 변경이 이 테스트를 실패시키는가 — 그 변경은 버그인가, 의도적 결정인가?**

- **명명 불가** → 관찰 가능한 동작 중심으로 테스트를 재설계한다.
- **미러 assertion 금지**: 기댓값을 검증 대상 코드(또는 그 헬퍼)로 계산하면 코드가 무엇을 하든 통과한다. 기댓값은 손으로 도출한 리터럴·고정 픽스처로 쓴다.
- **change detector 금지**: 상수값·문구·내부 구조처럼 "의도적 결정만이 실패시키는" 테스트는 리팩터링마다 깨지고 버그는 놓친다. 결정에 의존하는 **동작**을 테스트한다 (`MAX_RETRIES == 5`가 아니라 "실패 호출이 5회 재시도되고 6번째는 발생하지 않는다").

### 변이 점검 (The Mutation Check)

테스트 완성 전에 프로덕션 코드를 머릿속으로 변이시켜본다. 아래 변이 각각에 대해 최소 하나의 테스트가 실패해야 한다:

- 잘못된 상수 또는 인자
- 잘못된 분기 핸들러
- 상태 변경·부작용 누락
- 빈 값 또는 기본값 반환
- 0·빈값·nil·비인가·malformed 입력에 대한 검증 누락

아무 테스트도 잡지 못하는 변이는 그 동작이 무방비라는 뜻 — 또는 테스트가 동어반복이라는 뜻이다.

---
````

`:7` 출처 정정:

```
old: > 출처: superpowers 플러그인 `test-driven-development/testing-anti-patterns.md`의 한국어 이식판. gx-tdd 파이프라인 특화 주의(§0)를 추가했다.
new: > 출처: superpowers 플러그인 `test-driven-development/writing-good-tests.md`의 한국어 이식판 (모의 원칙 + 깨짐 명명 원칙 + 변이 점검). gx-tdd 파이프라인 특화 주의(§0)를 추가했다.
```

- [ ] **Step 2: 3중 동기 파일에 가드 불릿 추가**

아래 4개 불릿을 세 파일 각각의 **테스트 품질 가드 목록(기존 불릿들)의 마지막 불릿 바로 뒤**에 추가한다 — (a) `agents/red-writer.md`의 `## 테스트 품질 가드 (모의 사용 시)` 절 내 목록 끝, (b) `phase-implement.md` Step 2-R 프롬프트의 `[테스트 품질 가드 …]` 블록 내 목록 끝, (c) `.claude/skills/gx-red/SKILL.md:99` 프롬프트의 `[테스트 품질 가드 …]` 블록 내 목록 끝 (들여쓰기는 각 위치의 기존 불릿과 동일하게 맞춘다):

```
- **깨짐 명명**: 테스트 본문 작성 전에 "이 테스트를 실패시키는 프로덕션 변경"을 명명한다. 명명할 수 없으면 관찰 가능한 동작으로 재설계한다.
- 기댓값을 검증 대상 코드로 계산하지 않는다 (미러 assertion 금지 — 손으로 도출한 리터럴 사용).
- 상수값·문구·내부 구조만 검증하는 change detector를 만들지 않는다 — 결정에 의존하는 동작을 검증한다.
- 완성 전 변이 점검: 잘못된 상수/인자·잘못된 분기·부작용 누락·빈 반환·경계 입력 미검증 중 최소 하나가 이 테스트에 잡히는지 확인한다.
```

- [ ] **Step 3: 검증**

Run: `for f in agents/red-writer.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-red/SKILL.md; do grep -q "깨짐 명명" $f || echo "MISSING: $f"; done`
Expected: 출력 없음
Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/gx-tdd/references/testing-anti-patterns.md agents/red-writer.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-red/SKILL.md
git commit -m "feat: red-writer에 깨짐 명명 원칙과 변이 점검을 이식한다"
```

---

### Task 5: config.json — focusedTest·contextLimits + gx-setup 힌트

**Files:**
- Modify: `.claude/config.json` (:46 java-spring, :53 node, :76·:79 contextLimits)
- Modify: `.claude/skills/gx-setup/SKILL.md:113`, `.claude/skills/gx-setup/references/project-type-hints.md`

**Interfaces:**
- Produces: `projectTypes.{타입}.focusedTest` (Task 2의 조립 규약이 소비), `contextLimits.implementer`·`contextLimits.reviewer`

- [ ] **Step 1: config.json 갱신**

- `projectTypes.java-spring`의 `"test": "./gradlew test",` 다음 줄에 추가: `"focusedTest": "./gradlew test --tests {pattern}",`
- `projectTypes.node`의 `"test": "npm test",` 다음 줄에 추가: `"focusedTest": "npx vitest run {files}",`
- `contextLimits`에서 `"green-coder"` 항목 값과 동일한 값으로 `"implementer"` 키를, `"quality-reviewer"` 항목 값과 동일한 값으로 `"reviewer"` 키를 각각 해당 항목 다음 줄에 추가 (reviewer는 Phase B에서 사용 — 선등재, 소비자 없어 무해)

- [ ] **Step 2: JSON 유효성 확인**

Run: `python3 -c "import json; c=json.load(open('.claude/config.json',encoding='utf-8')); print(c['projectTypes']['java-spring']['focusedTest'], c['contextLimits']['implementer'], c['contextLimits']['reviewer'])"`
Expected: 세 값 출력, 예외 없음

- [ ] **Step 3: gx-setup 필드 열거·힌트 반영**

`.claude/skills/gx-setup/SKILL.md:113`의 config 기록 항목을 교체:

```
old: 5. **config 기록**: 확정 값을 `projectTypes.{타입키}`에 Edit로 기록한다 (`detect`/`build`/`test`/`warningPattern`/`artifacts`. 빈 제안 값은 필드를 생략한다).
new: 5. **config 기록**: 확정 값을 `projectTypes.{타입키}`에 Edit로 기록한다 (`detect`/`build`/`test`/`focusedTest`/`warningPattern`/`artifacts`. 빈 제안 값은 필드를 생략한다). `focusedTest`는 선택 필드로, 특정 테스트만 실행하는 명령 템플릿이다 — `{files}`(테스트 파일 경로 공백 구분) 또는 `{pattern}`(클래스 글롭 — 파일명에서 유도) 플레이스홀더를 쓴다. 미등록 시 gx-tdd가 전체 `test` 명령으로 폴백한다.
```

`references/project-type-hints.md`의 각 타입 힌트에 focusedTest 예시를 1줄씩 추가한다 (카탈로그에 실존하는 타입만 — java/gradle: `./gradlew test --tests {pattern}`, node/vitest: `npx vitest run {files}`, node/jest: `npx jest {files}`, python: `pytest {files}`, go: `go test -run {pattern} ./...`).

- [ ] **Step 4: 검증 + Commit**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0 ([20/25]가 focusedTest로 깨지면 해당 검사의 필드 목록에 선택 필드로 추가)

```bash
git add .claude/config.json .claude/skills/gx-setup/SKILL.md .claude/skills/gx-setup/references/project-type-hints.md
git commit -m "feat: projectTypes에 focusedTest 템플릿을 신설한다"
```

---

### Task 6: 인접 파일 정합 — ralph 참조·phase-review Step 0·:361 포인터·skill-routing

**Files:**
- Modify: `.claude/skills/gx-ralph-iterate/SKILL.md:89`
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` (:22 도입부, :43 Step 0-1, :55 Step 0-2, :361 포인터)
- Modify: `.claude/rules/skill-routing.md` (TDD 보조 스킬 절)

**Interfaces:**
- Consumes: Task 2의 부록 A 헤더·`구 Step 2-G/2-F` 개칭

- [ ] **Step 1: gx-ralph-iterate 참조 문구 갱신 (:89)**

```
old: 각 단계 프롬프트는 `gx-tdd/phases/phase-implement.md`의 Step 2-R/G/F 디스패치 프롬프트를 따르되, 대상을 이 AC 1건으로 한정한다.
new: 각 단계 프롬프트는 `gx-tdd/phases/phase-implement.md`의 Step 2-R 및 **부록 A(gx-ralph 전용 트리오 프롬프트 — 구 Step 2-G/2-F)** 의 디스패치 프롬프트를 따르되, 대상을 이 AC 1건으로 한정한다.
```

- [ ] **Step 2: phase-review Step 0 수정 주체 교체**

`:43` (Step 0-1 실행 흐름 3항) 교체:

```
old: 3. **실패** → 직전 RGR 사이클이 컴파일 미완성 상태일 가능성이 크다. `Task(subagent_type="oh-my-gx:green-coder")`에 빌드 에러를 전달하여 컴파일을 통과시킨다. 이는 진행 중인 GREEN 단계의 연장이므로 **새 RED는 불필요**하다 (해당 사이클의 실패 테스트가 이미 가드 역할). **단, `coder`(deprecated) 직접 호출 금지.** 컴파일 에러가 **테스트 파일**에 있으면 green-coder가 아니라 **red-writer를 재호출**한다 (테스트 수정은 red-writer 소관). green-coder 수정 후에는 변경 파일에 테스트 파일이 없는지 확인하고, 테스트가 수정되었으면 원복 후 재호출한다 (state.md의 `test-file-hash` 대조).
new: 3. **실패** → 직전 RGR 사이클이 컴파일 미완성 상태일 가능성이 크다. `Task(subagent_type="oh-my-gx:implementer")`에 빌드 에러를 전달하여 컴파일을 통과시킨다. 이는 진행 중인 IMPLEMENT 단계의 연장이므로 **새 RED는 불필요**하다 (해당 사이클의 실패 테스트가 이미 가드 역할). **단, `coder`(deprecated)·`green-coder`(파이프라인 미호출) 직접 호출 금지.** 컴파일 에러가 **테스트 파일**에 있으면 implementer가 아니라 **red-writer를 재호출**한다 (테스트 수정은 red-writer 소관). implementer 수정 후에는 변경 파일에 테스트 파일이 없는지 확인하고, 테스트가 수정되었으면 원복 후 재호출한다 (state.md의 `test-file-hash` 대조). 이 수리는 fix loop 라운드에 계상하지 않는다.
```

`:55` (Step 0-2 3항): `green-coder`를 `implementer`로 2곳, `refactor-coder에 롤백을 요청한다`를 `implementer에 롤백을 요청한다`로 치환. `coder`(deprecated) 금지 문구는 유지.

`:22` (Step 0 도입부 `리뷰 에이전트 호출 전에 기계적 검증을 통과시킨다. …` 문단) 끝에 추가:

```
이 Gate는 사이클 중 focused만 실행한 implement 단계의 **경계 회귀**를 겸한다 — 기존 스위트 회귀가 여기서 처음 전체 실행으로 검증된다.
```

- [ ] **Step 3: :361 Step 2-F 포인터를 부록 A로 재지정**

`:361`의 해당 문구를 교체 (Step 4b는 Phase B 전까지 refactor-coder 경로 유지 — 참조 대상만 이동분 반영):

```
old: 디스패치 형식(절대 규칙/수행 가능·불가 정리/출력 형식)은 phase-implement Step 2-F를 따르되,
new: 디스패치 형식(절대 규칙/수행 가능·불가 정리/출력 형식)은 phase-implement 부록 A의 구 Step 2-F를 따르되,
```

- [ ] **Step 4: skill-routing 문구 갱신**

```
old: `gx-red`/`gx-green`/`gx-refactor`는 gx-tdd 파이프라인이 직접 호출하지 않고 `red-writer`/`green-coder`/`refactor-coder` 에이전트를 디스패치하므로 단독·체이닝 전용이며
new: `gx-red`/`gx-green`/`gx-refactor`는 gx-tdd 파이프라인이 직접 호출하지 않고 `red-writer`/`implementer` 에이전트를 디스패치하므로(green-coder/refactor-coder는 단독 스킬·gx-ralph 전용) 단독·체이닝 전용이며
```

- [ ] **Step 5: 검증 + Commit**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0 ([11/25] ralph 계약·[5/25] 디스패치 이름 대조 포함)

```bash
git add .claude/skills/gx-ralph-iterate/SKILL.md .claude/skills/gx-tdd/phases/phase-review.md .claude/rules/skill-routing.md
git commit -m "fix: 2석 전환에 맞춰 ralph 참조·리뷰 게이트 수정 주체·라우팅 문구를 정합시킨다"
```

---

### Task 7: gx-tdd SKILL.md 일괄 갱신 + golden-scenarios S9

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md`
- Modify: `tests/golden-scenarios.md:28` (S9)

**Interfaces:**
- Consumes: Task 2·3의 리터럴, Task 1의 implementer

- [ ] **Step 1: 차별점 표·RGR 보조 스킬 노트**

`:23` implement 행: `**RED → GREEN → REFACTOR (3에이전트 순차; red-writer만 코드 격리)**` → `**RED → IMPLEMENT (2에이전트 순차; red-writer만 코드 격리, implementer가 GREEN+REFACTOR 수행)**`
`:53` RGR 보조 스킬 노트: `` `red-writer`/`green-coder`/`refactor-coder` 에이전트를 **직접 `Task`로 디스패치**하며 `` → `` `red-writer`/`implementer` 에이전트를 **직접 `Task`로 디스패치**하며(green-coder/refactor-coder는 단독 스킬·gx-ralph 전용) ``

- [ ] **Step 2: 드리프트 주의 목록 갱신 (:55-71)**

- "디스패치 프롬프트" 항목(:57): `phase-implement.md(Step 2-R/G/F)와` → `phase-implement.md(Step 2-R/2-I — 부록 A는 gx-ralph 전용)와`, 그리고 `phase-review Step 4b의 refactor-coder 호출은 Step 2-F를 **포인터 참조**하므로 2-F만 고치면 따라온다.` → `phase-review Step 4b의 refactor-coder 호출은 부록 A의 구 Step 2-F를 **포인터 참조**한다 (Step 4b 주체 교체는 Phase B 범위).`
- "테스트 무결성 규칙" 항목(:60): `` `agents/green-coder.md` ↔ phase-implement.md(Step 2-G, verify_red/verify_green) ↔ gx-green SKILL.md(Step 1~3)에 중복. `` → `` `agents/green-coder.md`·`agents/implementer.md` ↔ phase-implement.md(Step 2-I, verify_red/verify_implement) ↔ gx-green SKILL.md(Step 1~3)에 중복 (4중). ``
- "무결성 기준선 규약" 항목(:69): `phase-implement.md(verify_red/green/refactor)` → `phase-implement.md(verify_red/verify_implement — porcelain 대조는 테스트 파일 라인 필터, test-count는 오케스트레이터의 focused 직접 실행 결과)`
- 목록 끝에 신규 항목 추가:

```
> - **fix 라운드 상한**: 파이프라인 phase-implement `라운드 5` ↔ 단독 gx-green SKILL.md `최대 2회` — **의도적 분기**다 (단독 스킬은 fix loop 없이 현행 상한 유지). 린트 [3/26]이 각각을 검사한다.
```

(주: 이 신규 항목의 `[3/26]` 표기는 Task 8의 분모 갱신을 선반영한 것 — Task 8 완료 전까지 일시적 불일치이며 린트 검사 대상 아님)

- [ ] **Step 3: Agent 팀 표·Phase 개요·핵심 차별점·core 분기·Agent 팀 강제·deprecated 서술**

- EXECUTION 표(:236-242): 헤더 `### EXECUTION (RED-GREEN-REFACTOR 순차; red-writer만 코드 격리)` → `### EXECUTION (RED → IMPLEMENT 순차; red-writer만 코드 격리)`. red-writer 행 유지. green-coder·refactor-coder 행을 삭제하고 그 자리에:

```
| **implementer** | **GREEN+REFACTOR 통합 (신설)** | **"최소 통과 후 안전한 정리" — 테스트 수정 금지, focused만 실행** | **sonnet** |
| green-coder / refactor-coder | (파이프라인 미호출 — 단독 스킬·gx-ralph 전용) | — | sonnet |
```

  coder deprecated 행(:242)은 교체: `| ~~coder~~ | (deprecated — red-writer/green-coder/refactor-coder로 분해) | — | — |` → `| ~~coder~~ | (deprecated — red-writer/implementer로 재편. 구 3석: green/refactor-coder) | — | — |`
- `:270` 교체: `- 구현은 red-writer/green-coder/refactor-coder가 분담한다.` → `- 구현은 red-writer/implementer가 분담한다 (green/refactor-coder는 단독 스킬·gx-ralph 전용).`
- Phase 개요 표(:279) implement 행: `**red-writer → green-coder → refactor-coder (순차; red-writer만 코드 격리)**` → `**red-writer → implementer (순차; red-writer만 코드 격리)**`
- 핵심 차별점(:285): `implement는 단일 coder가 아니라 **3 에이전트 순차 사이클** (red-writer만 기존 코드 격리; green/refactor는 입력 범위만 제한)` → `implement는 단일 coder가 아니라 **RED 격리 + IMPLEMENT의 2 에이전트 순차 사이클** (red-writer만 기존 코드 격리; implementer는 입력 범위만 제한)`
- core 분기(:298 부근): `red-writer/green-coder에 ac.md의 AC만 전달` → `red-writer/implementer에 ac.md의 AC만 전달`
- Agent 팀 강제(:376): 나열에서 `red-writer, green-coder, refactor-coder,` → `red-writer, implementer,`로 바꾸고 문장 끝에 ` (green-coder·refactor-coder는 파이프라인 미호출 — 단독 스킬·gx-ralph 전용이며 이 팀 표에서 디스패치하지 않는다)` 추가
- deprecated Iron Law(:381): `- \`coder\` — red-writer/green-coder/refactor-coder로 분해됨` → `- \`coder\` — red-writer/implementer로 재편됨 (구 3석: green/refactor-coder)`

- [ ] **Step 4: 모델 라우팅(:258)·모델 프로파일(:463)·전달 규칙(:487)·state 스키마(:525-539)**

- 모델 라우팅 원칙(:258 부근 목록)에 불릿 추가: `- **최소 강도 + 실패 시 격상**: 각 역할을 감당하는 가장 약한 모델을 쓰되(sonnet이 바닥 — haiku 강등 금지), 격상은 fix loop 라운드 4~5에서만 수행한다.`
- 모델 프로파일(:463 문단) 끝에 문장 추가: `fix loop 라운드 4~5의 opus 격상은 "실패의 대응"으로 프로파일과 독립이다 — eco 세션에서도 격상한다 (하향 규칙은 초기 디스패치 모델에만 적용된다).`
- Agent 결과 전달 규칙(:487 부근)에 불릿 추가: `- **implement Phase의 인계는 report 파일 경로로만 한다**: red-writer·implementer는 전문을 ${DEV_DIR}/reports/t{N}-*.md에 Write하고 상태(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)·요약만 반환한다. 오케스트레이터는 다음 에이전트에 파일 경로를 전달하며 전문을 인라인으로 붙이지 않는다.`
- state 스키마: `:525` `current-step: "RGR T1: GREEN"` → `current-step: "RGR T1: IMPLEMENT"`. `:534-539` 태스크 블록을 Task 3 Step 5의 new 블록 T1·T2 부분과 동일한 키 구성으로 교체하되 **`test-file`·`test-file-hash`·`test-count` 3필드와 주석을 모두 포함**한다 (주석의 verify_green/verify_refactor → verify_implement 갱신 포함):

```
    - "RGR T1 (AC-1)":
        red: completed
        test-file: src/test/.../PasswordValidatorTest.java   # verify_red 기록 — focused 집합 조립에 사용
        test-file-hash: 3ca970cc...   # verify_red 기록 — verify_implement 무결성 비교 기준선
        test-count: 47                # verify_implement 기록 — focused 직접 실행 결과 (테스트 삭제 감지 기준선)
        report: reports/t1-impl.md
        impl: completed
    - "RGR T2 (AC-2)": pending
```

  execution-log 예시(:557-561 부근)의 `agent: green-coder (T1)` 항목 → `agent: implementer (T1)`, `result: "in_progress"` 유지

- [ ] **Step 5: Context Slicing(:606-612)·병렬 규칙(:635-637)**

- `:606` 헤더: `#### EXECUTION (RED-GREEN-REFACTOR 순차; red-writer만 코드 격리)` → `#### EXECUTION (RED → IMPLEMENT 순차; red-writer만 코드 격리)`
- `:608-609`의 green-coder·refactor-coder 두 항목을 하나로 교체:

```
- **implementer (IMPLEMENT)**: RED report 경로 (reports/t{N}-red.md) + 설계서 인터페이스(대상 시그니처만) + focused 테스트 명령 + report 파일 경로 + 프로젝트 루트 경로. **PRD 전체나 설계서 전체는 전달하지 않는다** (입력 범위 제한 — red-writer 수준의 코드 차단이 아니다. implementer는 구현을 위해 기존 코드를 Read할 수 있다). "최소 코드로 통과 후 GREEN 유지 정리. 테스트 수정 금지. focused만 실행" 지시.
```

- `:612` Deprecated 항목: `- ~~coder (구현/배치/수정)~~ → red-writer/green-coder/refactor-coder로 분해됨` → `- ~~coder (구현/배치/수정)~~ → red-writer/implementer로 재편됨`
- 병렬 규칙 3항(:635): `쓰기 Agent(red-writer, green-coder, refactor-coder)` → `쓰기 Agent(red-writer, implementer)`
- 병렬 규칙 4항(:636-637): `red-writer → green-coder → refactor-coder는 **반드시 순차** 실행한다. 병렬 금지.` → `red-writer → implementer는 **반드시 순차** 실행한다. 병렬 금지.` / 이유 문장: `red-writer 산출물(실패 테스트)이 green-coder의 입력. green-coder 산출물(통과 코드)이 refactor-coder의 입력.` → `red-writer 산출물(실패 테스트 — RED report)이 implementer의 입력.`

- [ ] **Step 6: golden-scenarios S9 갱신 (Phase A 현실 기준)**

`:28` 교체 — **주의**: Phase A 시점에 phase-review Step 4b는 여전히 refactor-coder를 정리 경로로 디스패치하므로(주체 교체는 Phase B), S9는 implement 단계 기준으로만 강화한다:

```
old: | S9 | gx-tdd implement/review 진행 관찰 | (관찰 항목) | deprecated 에이전트(coder/qa-manager) 미호출 — red/green/refactor-coder·spec/quality-reviewer만 디스패치 | gx-tdd Agent 팀 강제 |
new: | S9 | gx-tdd implement/review 진행 관찰 | (관찰 항목) | deprecated 에이전트(coder/qa-manager) 미호출. implement는 red-writer·implementer만 디스패치(green/refactor-coder 미호출 — 부록 A는 gx-ralph 전용)하고 인계는 reports/t{N}-*.md 경로로 관찰. review는 spec/quality-reviewer 디스패치(Step 4b 정리 경로의 refactor-coder는 Phase B 전환 전까지 허용) | gx-tdd Agent 팀 강제 |
```

- [ ] **Step 7: 검증 + Commit**

Run: `bash scripts/lint-consistency.sh 2>&1 | tail -3` → exit 0 ([13/25] CORE·[14/25] 프로파일 — eco 하향 목록 무변경이므로 통과 유지)
Run: `grep -n "green-coder" .claude/skills/gx-tdd/SKILL.md | grep -v "단독\|ralph\|미호출\|gx-green"` → 출력 없음 (Step 1~5가 :242·:270·:285·:381·:612를 갱신했으므로 잔존은 전부 범위 표기 동반. 출력이 있으면 해당 줄을 같은 방식으로 갱신 후 재검증)

```bash
git add .claude/skills/gx-tdd/SKILL.md tests/golden-scenarios.md
git commit -m "docs: SKILL.md의 에이전트 팀·전달 규칙·state 스키마를 2석 기준으로 갱신한다"
```

---

### Task 8: 린트 [26/26] 신설 + 번호 일괄 갱신 + 최종 검증

**Files:**
- Modify: `scripts/lint-consistency.sh` (신규 항목, 상단 주석 목록, 분모 일괄)
- Modify: `.claude/skills/gx-tdd/SKILL.md:62`·`:71` (린트 번호 표기)
- Modify: `README.md:64` (`[15/24]` 드리프트)

**Interfaces:**
- Consumes: Task 2·3의 report 계약 리터럴, Task 6의 부록 A 참조

- [ ] **Step 1: 신규 검사 [26/26] 작성**

`[25/25]` 블록의 마지막 `ok` 줄 뒤, 파일 말미의 `if [ "$FAIL" -ne 0 ]` 블록(:680 부근) **앞**에 삽입:

```bash
echo "[26/26] implement report 계약"
grep -qF 'reports/t{N}-impl.md' .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "report 파일 경로 계약 누락: phase-implement.md"
grep -qF 'reports/t{N}-red.md' .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "RED report 경로 계약 누락: phase-implement.md"
for s in DONE_WITH_CONCERNS NEEDS_CONTEXT BLOCKED; do
  grep -q "$s" .claude/skills/gx-tdd/phases/phase-implement.md || fail "4-status($s) 누락: phase-implement.md"
  grep -q "$s" agents/implementer.md || fail "4-status($s) 누락: agents/implementer.md"
done
grep -q "부록 A" .claude/skills/gx-ralph-iterate/SKILL.md \
  || fail "ralph 트리오 프롬프트 참조(부록 A) 누락: gx-ralph-iterate/SKILL.md"
[ "$FAIL" -eq 0 ] && ok "report 경로·4-status·ralph 부록 참조 확인"
```

파일 상단의 `검사 항목:` 주석 목록(:5-30)에 26번 항목 한 줄을 추가한다: `# [26] implement report 계약 (report 경로·4-status·ralph 부록 참조)`.

- [ ] **Step 2: 교차 검증 (RED — 신규 검사가 실제로 잡는지)**

[26/26] 블록의 `agents/implementer.md`를 임시로 `agents/implementer-x.md`로 바꿔 실행:

Run: `bash scripts/lint-consistency.sh 2>&1 | grep "FAIL:"`
Expected: `  FAIL: 4-status(DONE_WITH_CONCERNS) 누락: agents/implementer-x.md` 등 [26] 계열 FAIL (파일명 오타이므로 [3]·[5]는 영향 없음 — implementer.md 자체는 존재)

되돌린 후 재실행 → `FAIL:` 0건 확인.

- [ ] **Step 3: 번호 분모 일괄 갱신**

Run: `grep -c "/25\]" scripts/lint-consistency.sh` → Expected: **26** (echo 25줄 + :519 주석 1줄)
Run: `sed -i 's|/25\]|/26]|g' scripts/lint-consistency.sh`
Run: `git diff scripts/lint-consistency.sh | grep -c "^[+-].*26\]"` → 변경이 위 26곳 + Step 1 삽입분에 한정되는지 diff를 눈으로 확인 (`:519` 주석의 `[15/25]`→`[15/26]` 포함이 **정상**이다)

문서 표기 정정:
- `.claude/skills/gx-tdd/SKILL.md:62`: `린트 [23/23]이` → `린트 [23/26]이`
- `.claude/skills/gx-tdd/SKILL.md:71`: `린트 [14/25]가` → `린트 [14/26]가`
- `README.md:64`: `` `lint-consistency.sh`의 `[15/24]`가 `` → `` `lint-consistency.sh`의 `[15/26]`이 ``
- (`.claude/rules/release.md`의 "[1/26]"·`.claude/rules/harness-codex.md`의 "[15/26]"은 이번 갱신으로 실번호와 일치 — 무수정)

- [ ] **Step 4: 최종 전체 검증**

Run: `bash scripts/lint-consistency.sh` → exit 0, `FAIL:` 0건, `[26/26]`까지 출력
Run: `bash scripts/hook-tests.sh 2>&1 | tail -3` → 기존 통과 유지 (훅 무수정 — 회귀 없음 확인)
Run: `grep -rn "Step 2-G\|Step 2-F" .claude/skills .claude/rules --include="*.md" | grep -v "부록 A\|구 Step"` → 출력 없음 (부록 헤더는 "구 Step" 포함, phase-review :361·ralph :89·SKILL.md 드리프트 항목은 "부록 A" 포함으로 제외됨. 출력이 있으면 해당 줄을 부록 A 참조로 갱신 후 재검증)

- [ ] **Step 5: Commit**

```bash
git add scripts/lint-consistency.sh .claude/skills/gx-tdd/SKILL.md README.md
git commit -m "test: report 계약 린트를 신설하고 항목 번호를 26으로 정렬한다 (README [15/24]·release.md·harness-codex.md 표기 드리프트 해소)"
```

---

## 이 계획의 범위 밖 (후속)

- **Phase B**: reviewer 통합 에이전트 신설 + phase-review Step 2/3 재작성(Step 4b 주체 교체 포함 — S9 최종 강화도 이때) + eco 하향 목록에 reviewer 추가 + phase-setup :92 + `agents/test-architect.md` 언급 정합 + golden-scenarios S17 (spec T3·T9)
- **Phase C**: gx-ralph-iterate 2석 전환 검토, README·index.html·docs 파생 사본 전수 정합, spec/quality/green/refactor 에이전트 정리 여부
- **릴리스**: CHANGELOG·버전 3파일 갱신은 Phase B 완료 후 릴리스 커밋에서 수행 (release.md 규칙)

## Self-Review 결과 (v2)

- Spec 커버리지: T1(Task 1·2), T2(Task 2·3·5·6), T4(Task 2), T5(Task 2·3·7·8), T6(Task 1·4), T7(Task 3), T8(Task 2 verify_implement 3항) — T3·T9는 Phase B 이관. D1 게이트 문구 무접촉
- Momus 지적 반영: C-1(Task 2 Step 3·4), C-2(부록 헤더 개칭 + Task 8 Step 4 grep 재작성), C-3(Task 7 Step 3·5에 :242/:270/:285/:381/:612 편입 + 검증 폴백), C-4(Task 2 Step 7 `{pattern}` 규약), C-5(test-file producer=verify_red, hash/count 존치 — Task 3 Step 3·5, Task 7 Step 4), C-6(Task 8 Step 3 기대값 26곳), I-1(Step 2 골격 old 전문), I-2(mkdir→Step 2 진입부), I-3·I-4·I-5(Task 3), I-6(삽입 위치 통일), I-7(Step 0.5 4항 글롭), I-8(:361 재지정 + S9 완화), I-9(Task 7 편입), I-10(gx-setup :113 특정), I-11(Task 0), I-12(Global Constraints 예외 선언), M-1~8 반영
- 타입 일관성: `oh-my-gx:implementer`·`"RGR T{N}: IMPLEMENT"`·`"라운드 5"`·`reports/t{N}-impl.md`·`구 Step 2-G/2-F`·부록 A 헤더가 Task 1→2→3→6→7→8에서 동일 리터럴로 관통
