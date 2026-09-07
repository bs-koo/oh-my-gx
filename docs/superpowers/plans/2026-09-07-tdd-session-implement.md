# gx-tdd 세션 IMPLEMENT·AC 단위 태스크 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-tdd 구현 단계의 콜드 스타트를 태스크당 2회에서 1회로 줄이고, 태스크 단위를 테스트 1건에서 AC 1건으로 올린다. red-writer 격리·테스트 해시·focused 직접 실행·verify 지문은 그대로 둔다. 기본 경로가 바뀌며 `--isolated`가 현행 2석을 되돌린다.

**Architecture:** phase-implement Step 2-I의 implementer 디스패치를 "세션 IMPLEMENT 절차"로 바꾼다 — 오케스트레이터가 `agents/implementer.md`와 같은 계약(테스트 수정 금지·YAGNI·REFACTOR 금지 5항목·focused만 실행·self-review·report Write)으로 직접 구현한다. verify_implement는 파일 상태 대조라 그대로 동작한다. Step 1 분해 규칙은 "태스크 = AC 1건 + 같은 컴포넌트·패턴 묶기"로 바꾸고 8개 초과 시 분할을 먼저 묻는 가드를 넣는다. red-writer는 AC의 시나리오 전부를 테스트 집합으로 한 번에 쓰고, verify_red는 집합 전체의 실패를 확인한다. 검증은 린트 `[33]`(세션 IMPLEMENT 계약)과 골든 시나리오 S38·S39다.

**Tech Stack:** Markdown (스킬·phase·에이전트 정의·문서), Bash (린트)

**Spec:** `docs/specs/2026-09-07-tdd-density-rhythm-design.md` — D1·D2 절, 2절 불변 목록, 4절 비용 모델

## Global Constraints

- **선행 조건**: `2026-09-07-tdd-instruction-density.md`가 main에 머지되어 있어야 한다 (린트 분모 32, SKILL.md의 Context Slicing이 표, 드리프트 목록이 `references/maintenance-notes.md`). 착수 전 `grep -c '/32\]' scripts/lint-consistency.sh`가 0보다 커야 한다.
- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (훅 G1). 작업 시작 전 `feat/tdd-session-implement` 브랜치를 생성한다.
- **커밋**: 메시지는 `feat: …`/`docs: …` 한 줄 제목 (`.claude/config.json` `conventions.commitFormat`). gx-commit 규칙에 따라 `Co-Authored-By` 등 트레일러를 **붙이지 않는다**. 서브에이전트는 gx-commit의 확인 게이트에 응답할 수 없으므로 직접 `git commit`을 허용한다 (이전 계획과 같은 ruling). grep 패턴 인자에 `git commit` 문자열을 넣지 않는다 (훅 G1 오탐).
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 둘 다 통과한 상태로 끝난다. 린트 `[32/32]` 예산(SKILL.md ≤ 61,500B)이 살아 있으므로 SKILL.md에 문장을 **더할 때는 같은 절에서 같은 양을 줄인다**.
- **린트 번호 체계**: 현재 `[N/32]`. Task 6이 검사 1개를 추가하며 분모를 33으로 올린다. `.claude/`·`README.md`의 인용도 함께 치환한다 (`[31]`이 검사). `docs/`·`CHANGELOG.md`는 치환하지 않는다.
- **린트가 고정하는 문구 (phase-implement.md)**: `[3]` — 금지 5항목 `동작 변경`·`새 기능 추가`·`에러 핸들링`·`성능 최적화`·`인터페이스 시그니처 변경`과 `라운드 5`. `[11]` — `## Step 0.7: gx-ralph 전환 (--ralph 전용)` 제목과 "`--resume` 재진입은 방어 조건이 **아니다**". `[26]` — `reports/t{N}-impl.md`·`reports/t{N}-red.md`·`DONE_WITH_CONCERNS`·`NEEDS_CONTEXT`·`BLOCKED`. 이 문구들은 새 텍스트와 보존되는 격리 경로 블록 양쪽에 남는다.
- **gx-ralph-iterate는 손대지 않는다**: 무인 루프는 항상 2석 격리 경로다 (`[26]`이 `oh-my-gx:implementer` 언급을 검사한다).
- **외과적 변경**: 지시된 블록만 고친다. 격리 경로로 보존하는 implementer 디스패치 블록은 글자를 바꾸지 않고 위치만 옮긴다.

---

### Task 1: 태스크 분해를 AC 단위로 올리고 태스크 수 가드를 넣는다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` — `## Step 1: 태스크 분해 (오케스트레이터 직접 수행)` 절의 조건 1~2, `### 1.1 태스크 표 생성`의 예시 표, `### 1.2 사용자 승인 게이트` 앞에 `### 1.15 태스크 수 가드` 신설

**Interfaces:**
- Consumes: 없음
- Produces: 절 제목 `### 1.15 태스크 수 가드` (Task 6의 린트가 `태스크 수 가드` 문자열을 검사)

- [ ] **Step 1: 분해 조건 1~2를 교체한다**

현재 텍스트:

```
1. **단일 AC 또는 단일 컴포넌트**에 매핑된다. 단, **같은 패턴의 소형 변경으로 환산되는 AC들**(동일 검증 로직의 필드별 반복, 동일 형태의 매핑 추가 등)은 하나의 태스크로 묶는다 ...
2. **2-15분 단위**로 RED→IMPLEMENT 완료 가능한 크기.
```

(1번 행은 "하나의 태스크로" 뒤가 이어진다 — 행 전체를 교체한다.) 새 텍스트:

```markdown
1. **태스크 = AC 1건**이 기본이다. AC 하나의 G-W-T 시나리오 전부가 그 태스크의 테스트 집합이 된다. **같은 컴포넌트를 건드리는 AC들**과 **같은 패턴의 소형 변경으로 환산되는 AC들**(동일 검증 로직의 필드별 반복, 동일 형태의 매핑 추가 등)은 하나의 태스크로 **묶는 것이 기본**이다. 한 AC가 컴포넌트 둘 이상에 걸칠 때만 컴포넌트 단위로 나눈다 — 이때만 AC보다 작은 태스크가 생긴다.
2. **2~15분**은 태스크의 크기가 아니라 태스크 안에서 **테스트 하나를 통과시키는 한 걸음**의 크기다 (Step 2-I 내부 루프). 태스크는 리뷰어가 이웃 태스크를 승인하면서 이 태스크만 거절할 수 있을 만큼 독립적이면 충분하다.
```

- [ ] **Step 2: 1.1 예시 표의 RED 열을 테스트 집합으로 바꾼다**

예시 표 세 행을 아래로 교체한다 (열 구성은 같다).

```markdown
| 1 | AC-1 | PaymentLimit | PaymentLimitTest (케이스 3건: 초과 거부·경계값·기본 한도) | PaymentLimit.kt: data class + validate() → 매직 넘버 상수화 |
| 2 | AC-2, AC-3 (묶음) | PaymentService | PaymentServiceTest (케이스 4건) | PaymentService.processPayment() 한도 검증 추가 → 중복 검증 로직 추출 |
| 3 | AC-4 | PaymentController | PaymentControllerE2ETest (케이스 2건) | PaymentController.updateLimit() 엔드포인트 |
```

- [ ] **Step 3: `### 1.2 사용자 승인 게이트` 바로 앞에 가드 절을 넣는다**

```markdown
### 1.15 태스크 수 가드

태스크가 **8개를 넘으면** 승인 게이트 전에 아래를 먼저 묻는다. 태스크마다 red-writer 콜드 스타트와 verify 6단계가 붙으므로 30개짜리 분해는 한 세션에서 끝나지 않는다 — 분해가 잘못됐거나 실행 단위가 잘못된 것이다.

```
AskUserQuestion(
  questions: [{
    question: "태스크가 {N}개로 분해됐습니다. 8개를 넘으면 한 세션에서 완주하기 어렵습니다. 어떻게 할까요?",
    header: "태스크 수",
    options: [
      { label: "AC 묶어서 재분해 (추천)", description: "같은 컴포넌트·같은 패턴의 AC를 한 태스크로 묶어 8개 이하로 줄입니다. 태스크당 테스트 케이스가 늘어날 뿐 RGR 강도는 같습니다" },
      { label: "작업 계획으로 분할", description: "이번 실행은 앞 8개까지만 진행하고 나머지 AC는 `.dev/plan.md`의 후속 작업(W행)으로 등록합니다. 다음 실행에서 `W0N 시작해줘`로 이어집니다" },
      { label: "무인 루프로 전환", description: "이 파이프라인을 중단하고 `--ralph`로 재실행해 외부 러너가 AC를 1건씩 반복합니다 (svn 미지원)" },
      { label: "그대로 진행", description: "{N}개 전부 이 세션에서 진행합니다. 컨텍스트 압축이 일어날 수 있으며 `--resume`으로 이어갈 수 있습니다" }
    ],
    multiSelect: false
  }]
)
```

- **AC 묶어서 재분해** → 조건 1의 묶기 규칙을 적용해 재분해하고 1.1 표를 다시 제시한다. 여전히 8개를 넘으면 이 가드를 한 번 더 거친다 (최대 2회).
- **작업 계획으로 분할** → `.dev/plan.md`가 없으면 이 선택지를 **제외**하고 제시한다. 있으면 앞 8개 태스크에 대응하는 AC로 범위를 줄이고, 나머지 AC를 `.dev/plan.md`에 `대기` 상태의 새 W행으로 추가한다 (도메인·브랜치명은 현재 실행과 같은 규칙, 선행은 현재 `work-id`). `.dev/plan.md`만 스테이징해 `docs: [plan] 후속 작업 등록` 메시지로 커밋한다. trust-ledger `### 위험 수용`에 `- [범위 분할] AC-N…: 후속 W행으로 이관 (implement/Step 1.15)`를 기록한다.
- **무인 루프로 전환** → `status: cancelled`로 종료하고 `/gx-tdd --ralph {원 요청}` 재실행을 안내한다. svn이면 이 선택지를 제외한다.
- **그대로 진행** → 1.2로 진행한다. execution-log에 `"태스크 수 가드 통과(사용자 선택): {N}개"`를 남긴다.

핵심 모드는 Step 1을 건너뛰므로 이 가드도 타지 않는다 (AC 3~5개 = 태스크 3~5개).
```

- [ ] **Step 4: 검증**

Run: `grep -n '태스크 = AC 1건\|### 1.15 태스크 수 가드\|8개를 넘으면\|한 걸음' .claude/skills/gx-tdd/phases/phase-implement.md | cut -c1-80; bash scripts/lint-consistency.sh`
Expected: 4개 앵커가 Step 1 절 안에 순서대로, 린트 32/32 통과.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md
git commit -F - <<'MSG'
feat: gx-tdd 태스크 분해를 AC 단위로 올리고 태스크 수 가드를 추가한다
MSG
```

---

### Task 2: Step 2를 세션 IMPLEMENT 기본 경로로 재작성한다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` — `## Iron Law` 절, `## Step 2` 도입 의사코드, `### Step 2-R` 프롬프트의 `[report 파일]` 앞과 verify_red 2번, `### Step 2-I` 전체(제목·디스패치 블록·verify_implement 1·3·6번·fix loop 표), `## Step 3` 정체 감지 표의 "implementer가", `## state.md 추적`의 execution-log 예시, `## --resume 호환`의 IMPLEMENT·구 세션 행

**Interfaces:**
- Consumes: Task 1의 "테스트 집합" 개념
- Produces: 절 제목 `**세션 IMPLEMENT 절차**`와 `**격리 경로 (`--isolated`)**` (Task 3·4·6이 이 문구를 인용·검사)

- [ ] **Step 1: Iron Law 절의 2에이전트 서술을 교체한다**

현재:

```
이 Phase는 **2 에이전트가 순차 사이클로 동작**한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — ...)
- **implementer** → 통과 최소 코드(GREEN) + 안전한 정리(REFACTOR — 동작 변경 금지). 입력은 RED report+시그니처로 한정하되, 구현을 위한 기존 코드 Read는 허용 — red-writer 수준의 차단 아님. 테스트 실행은 focused 집합만
```

새 텍스트 (red-writer 불릿은 원문 그대로 유지):

```markdown
이 Phase는 **RED 격리 디스패치 → IMPLEMENT 세션 직접 수행**으로 동작한다:
- **red-writer** → 실패 테스트 작성 (**지시 기반 격리** — 프롬프트로 기존 프로덕션 코드 참조를 금지하고, 참조 파일 자기신고를 verify_red가 검증. 도구 레벨 차단은 아님). 태스크의 AC 시나리오 전부를 테스트 집합으로 한 번에 쓴다
- **IMPLEMENT** → 통과 최소 코드(GREEN) + 안전한 정리(REFACTOR — 동작 변경 금지). 기본 경로에서는 **오케스트레이터가 직접 수행**한다 (Step 2-I "세션 IMPLEMENT 절차"). `--isolated`면 implementer를 디스패치한다 — 입력은 RED report+시그니처로 한정하되 기존 코드 Read는 허용, 테스트 실행은 focused 집합만. 어느 경로든 verify_implement의 해시·focused 직접 실행 검증은 같다
```

`> green-coder·refactor-coder는 …` 문장 끝의 `gx-ralph 루프도 red-writer→implementer 2석을 쓴다.`는 `gx-ralph 루프는 항상 red-writer→implementer 2석(격리 경로)을 쓴다.`로 바꾼다.

- [ ] **Step 2: Step 2 도입 의사코드를 교체한다**

현재:

```
    # 2-I: IMPLEMENT (GREEN + REFACTOR 통합)
    impl_result = dispatch_implementer(task, red_report_path)   # report: reports/t{N}-impl.md
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증
```

새 텍스트:

```
    # 2-I: IMPLEMENT (GREEN + REFACTOR 통합)
    if "--isolated" in state.flags:
        impl_result = dispatch_implementer(task, red_report_path)   # 격리 경로. report: reports/t{N}-impl.md
    else:
        impl_result = session_implement(task, red_report_path)      # 기본 경로. 세션이 직접 구현하고 같은 report를 Write
    verify_implement(impl_result)            # focused 집합 직접 실행 + 무결성 검증 (경로 무관 동일)
```

- [ ] **Step 3: Step 2-R 프롬프트에 작성 범위를 넣고 verify_red 2번을 다건으로 바꾼다**

Step 2-R 프롬프트 블록의 `[report 파일]` 행 **바로 앞**에 삽입한다 (들여쓰기는 이웃 블록과 같게):

```
    [작성 범위 — 테스트 집합]
    이 태스크에 매핑된 AC의 G-W-T 시나리오 **전부**를 각각 테스트 케이스로 작성합니다 (시나리오 1건 = 케이스 1건). 컴포넌트당 테스트 파일 하나에 모읍니다. 케이스마다 실패 확인 명령을 실행해 전부 실패하는지 확인하고, 통과하는 케이스가 있으면 기존 동작을 검증하는 잘못된 케이스이므로 다시 씁니다.
```

verify_red 2번 행을 교체한다. 현재 `2. **실패 확인** (통과 시 잘못된 테스트 → red-writer 재호출).` → 새:

```
2. **실패 확인 (집합 전체)**: report의 실패 확인 명령을 직접 실행해 신규 케이스가 **모두** 실패하는지 본다 (실패 건수 = report의 케이스 수). 통과하는 케이스가 있으면 그 케이스만 지목해 red-writer를 재호출한다 (전체 재작성 아님). 에러(컴파일 실패·러너 오류)로 끝난 것은 실패가 아니다 — 원인을 report와 대조해 red-writer 재호출.
```

- [ ] **Step 4: Step 2-I를 재작성한다**

`### Step 2-I: IMPLEMENT (implementer 디스패치 — GREEN+REFACTOR 통합)` 제목부터 `**focused 테스트 명령 조립**:` 문단 **직전**까지(제목 + Task 디스패치 코드 블록)를 아래로 교체한다. 기존 Task 블록은 "격리 경로" 아래로 **글자 그대로** 옮긴다.

```markdown
### Step 2-I: IMPLEMENT (세션 직접 수행 — GREEN+REFACTOR 통합. `--isolated`면 implementer 디스패치)

기본 경로에서는 **오케스트레이터가 이 단계를 직접 수행**한다 — 태스크당 콜드 스타트를 red-writer 1회로 줄이기 위해서다. verify_implement의 검증은 파일 상태 대조(해시·porcelain·focused 직접 실행)라 수행 주체와 무관하게 같은 강도로 동작한다. state.md `flags`에 `--isolated`가 있으면 아래 "격리 경로"의 implementer 디스패치를 대신 쓴다. gx-ralph 루프는 항상 격리 경로다.

**세션 IMPLEMENT 절차** (`agents/implementer.md`의 절대 규칙·REFACTOR 범위·report 형식과 같은 계약이다 — 한쪽을 고치면 함께 갱신. `references/maintenance-notes.md` 참조):

[절대 규칙]
1. 테스트 파일을 수정하지 않는다. 테스트가 실패하면 코드를 고친다. 테스트 자체 결함이 의심되면 고치지 말고 report `## 우려사항`에 "테스트 결함 의심"으로 적고 verify_implement 2번을 따른다.
2. GREEN: 실패 테스트를 통과시키는 최소 코드만 작성한다 (YAGNI — 추가 기능/에러 핸들링/검증/로깅 금지).
3. REFACTOR: 동작 변경 금지. 매 정리 후 focused 테스트로 GREEN 유지 확인, 깨지면 즉시 롤백.
4. 테스트 실행은 focused 명령만 사용한다. 전체 스위트는 사이클 경계(Step 3.5 / phase-review Step 0)에서만 실행한다.
5. report 작성 전 self-review(완전성/품질/규율/테스트 4관점)를 수행하고 발견 즉시 수정한다.

[수행 불가능한 정리]
- 동작 변경
- 새 기능 추가
- 에러 핸들링 추가
- 성능 최적화
- 인터페이스 시그니처 변경

[절차 — 내부 RGR 루프]
1. `reports/t{N}-red.md`를 Read해 이 태스크의 실패 테스트 집합(파일·케이스·실패 메시지)을 파악한다. 설계서 인터페이스(대상 시그니처)를 확인한다. 구현에 필요한 기존 코드는 Read한다 (세션은 red-writer와 달리 코드 차단 대상이 아니다).
2. focused 명령을 실행해 현재 실패 케이스 목록을 얻는다.
3. 실패 케이스 **하나**를 고른다 → 그 케이스만 통과시키는 최소 코드를 작성한다 → focused를 재실행해 그 케이스가 통과하고 이미 통과한 케이스가 유지되는지 본다. 실패 케이스가 남아 있으면 3을 반복한다. 한 걸음이 15분을 넘기면 케이스를 더 잘게 볼 수 있는지 먼저 의심한다.
4. 전부 GREEN이면 REFACTOR: 중복 제거·네이밍·구조 정리. 정리 한 단위마다 focused 재실행. 깨지면 그 단위를 롤백한다. 정리할 것이 없으면 "정리 없음"으로 기록한다.
5. self-review 후 `reports/t{N}-impl.md`를 Write한다. 형식은 `agents/implementer.md`의 report 형식과 같다 — `## 구현 내용` / `## GREEN 증거`(focused 명령 + "N pass / 0 fail" 출력 요약) / `## REFACTOR 내역` / `## self-review 결과` / `## 우려사항`.
6. verify_implement로 진행한다. 세션 경로에는 NEEDS_CONTEXT·BLOCKED 상태 반환이 없다 — 필요한 파일은 직접 읽고, 막히면 fix loop와 Step 3 정체 감지가 처리한다. 우려가 있으면 report `## 우려사항`에 적고 verify_implement 1번의 DONE_WITH_CONCERNS 처리를 따른다.

**격리 경로 (`--isolated`)** — 아래 implementer 디스패치를 그대로 쓴다. 상태 반환(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)은 이 경로에서만 발생한다.

```
(기존 Task(subagent_type="oh-my-gx:implementer") 블록 전체를 여기로 옮긴다 — 글자 변경 없음)
```
```

- [ ] **Step 5: verify_implement 1·3·6번과 fix loop 표를 두 경로에 맞춘다**

verify_implement 1번 행의 앞머리 `1. **Status 분기**:`를 `1. **Status 분기** (격리 경로에서만 상태가 반환된다. 세션 경로는 report `## 우려사항`이 비어 있지 않으면 DONE_WITH_CONCERNS로 취급한다):`로 바꾸고 나머지는 그대로 둔다.

3번 행에서 `해당 테스트를 RED 산출물로 원복하고 implementer 재호출 1회 ("테스트 수정 금지" 재강조 — fix 라운드와 별도 카운트)`를 `해당 테스트를 RED 산출물로 원복하고 구현 주체가 1회 재수행한다 — 세션 경로는 세션이 원복 후 재구현, 격리 경로는 implementer 재호출 ("테스트 수정 금지" 재강조 — fix 라운드와 별도 카운트)`로 바꾼다.

6번 행 끝의 `(REFACTOR 금지 목록 위반 — 발견 시 implementer에 롤백 요청)`을 `(REFACTOR 금지 목록 위반 — 발견 시 롤백한다. 격리 경로는 implementer에 롤백 요청)`으로 바꾼다.

fix loop 표를 교체한다:

```markdown
| 라운드 | 방식 | 모델 |
|--------|------|------|
| 1~3 | **세션이 직접 수정** (기본 경로). 격리 경로는 **같은 implementer를 재개** — 하네스가 서브에이전트 재개(후속 메시지)를 지원하면 그 방식으로 미해결 항목을 전달, 지원하지 않으면 report 파일 경로를 실은 fresh 디스패치 (report가 영속 기억) | 세션 / sonnet |
| 4~5 | **두 경로 모두 fresh implementer 디스패치 + 모델 격상** (`model: "opus"` 오버라이드) — 세션이 3라운드 실패한 뒤에는 fresh eyes와 역량 격상이 함께 필요하다. 프롬프트에 "이전 구현자가 {r-1}회 시도했다. report 파일에서 시도 내역을 읽어라"를 포함 | opus |
```

표 아래 첫 불릿 `- 매 라운드: implementer가 수정 → …`의 앞머리를 `- 매 라운드: 구현 주체(세션 또는 implementer)가 수정 → …`로 바꾼다.

- [ ] **Step 6: Step 3 정체 감지 표·state.md 추적·--resume 호환을 맞춘다**

Step 3 표의 세 행에서 `implementer가`를 `구현 주체(세션 또는 implementer)가`로, `implementer의 REFACTOR 결과`를 `구현 주체의 REFACTOR 결과`로 바꾼다.

`## state.md 추적`의 execution-log 예시 두 번째 엔트리를 교체한다:

```yaml
- phase: implement
  agent: session-implement (T1)     # 기본 경로. 격리 경로는 implementer (T1)
  result: "최소 구현 + focused 3/3 pass + 매직 넘버 상수화"
```

`## --resume 호환`의 두 행을 교체한다:

```markdown
- `"RGR T{N}: IMPLEMENT"` → state.md `flags`에 `--isolated`가 있으면 implementer 재디스패치, 없으면 세션이 `reports/t{N}-red.md`를 읽고 "세션 IMPLEMENT 절차"를 처음부터 재개 (report 파일이 있으면 그 진행분을 반영)
- 구 세션 호환: `"RGR T{N}: GREEN"`/`"RGR T{N}: REFACTOR"`(3석 세대) → 해당 태스크를 위 IMPLEMENT 규칙으로 이어받는다. 재개 시 `test-file-hash`·`test-count`·porcelain 스냅샷 기준선을 그대로 사용한다
```

- [ ] **Step 7: 검증**

Run: `for s in '세션 IMPLEMENT 절차' '격리 경로 (`--isolated`)' 'subagent_type="oh-my-gx:implementer"' '동작 변경' '새 기능 추가' '에러 핸들링' '성능 최적화' '인터페이스 시그니처 변경' '라운드 5' 'reports/t{N}-impl.md' 'reports/t{N}-red.md' DONE_WITH_CONCERNS NEEDS_CONTEXT BLOCKED 'model: "opus"' 'git hash-object' 'focused 집합 직접 실행' '작성 범위 — 테스트 집합' '실패 확인 (집합 전체)' 'session-implement'; do grep -qF "$s" .claude/skills/gx-tdd/phases/phase-implement.md || echo "MISSING: $s"; done; grep -c 'dispatch_implementer' .claude/skills/gx-tdd/phases/phase-implement.md`
Expected: `MISSING` 없음, 마지막 `1` (의사코드의 격리 분기 한 곳).

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 32/32 통과, 훅 테스트 통과.

- [ ] **Step 8: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md
git commit -F - <<'MSG'
feat: gx-tdd IMPLEMENT를 세션 직접 수행으로 바꾸고 --isolated 격리 경로를 남긴다
MSG
```

---

### Task 3: SKILL.md·phase-setup·maintenance-notes를 새 구조에 맞춘다

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` — 차별점 표의 implement 행, `## 인자` Step 1 플래그 목록, `### 플래그 참조`, `## 플래그 충돌 검증`, Agent 팀 EXECUTION 표, Phase 개요 implement 행, "핵심 차별점" 불릿, 핵심 모드 implement 불릿, Context Slicing 표의 implementer 행, 병렬 실행 규칙 3~4항
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` — Step 7의 `flags` 기록 불릿
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md` — 디스패치 프롬프트 항목

**Interfaces:**
- Consumes: Task 2의 "세션 IMPLEMENT 절차"
- Produces: SKILL.md·phase-setup.md의 `--isolated` 문자열 (Task 6 린트 검사 대상)

- [ ] **Step 1: 차별점 표·Phase 개요·핵심 차별점을 고친다**

차별점 표 implement 행의 gx-tdd 셀 `**RED → IMPLEMENT (2에이전트 순차; red-writer만 코드 격리, implementer가 GREEN+REFACTOR 수행)**`을 `**RED 격리 디스패치 → IMPLEMENT 세션 직접 (기본. `--isolated`면 implementer 디스패치). 태스크 = AC 1건**`으로 바꾼다.

Phase 개요 implement 행의 주 Agent 셀 `**red-writer → implementer (순차; red-writer만 코드 격리)**`를 `**red-writer(디스패치) → 세션 IMPLEMENT (`--isolated`: implementer)**`로 바꾼다.

"핵심 차별점" 불릿 `- implement는 단일 coder가 아니라 **RED 격리 + IMPLEMENT의 2 에이전트 순차 사이클** (red-writer만 기존 코드 격리; implementer는 입력 범위만 제한)`을 `- implement는 **RED 격리 디스패치 + 세션 IMPLEMENT** (red-writer만 기존 코드 격리. `--isolated`로 implementer 디스패치 복원)`로 바꾼다.

핵심 모드 경로의 implement 불릿에서 `red-writer/implementer에 ac.md의 AC만 전달`을 `red-writer에 ac.md의 AC만 전달하고 세션이 그 AC로 구현`으로 바꾼다.

- [ ] **Step 2: 플래그를 추가한다**

`## 인자` Step 1의 `- --core, --phase, --base, --status, --resume이 포함되면 해당 로직으로 실행.` 불릿 아래에 추가한다:

```markdown
- `--isolated`가 포함되면 **격리 구현 플래그**로 기록한다 — phase-implement Step 2-I가 세션 직접 수행 대신 implementer 디스패치(현행 2석) 경로를 택한다. 모드 판정과 독립이므로 나머지 파싱을 계속한다.
```

`### 플래그 참조`의 `--ralph` 항목 아래에 추가한다:

```markdown
- `--isolated`: 구현 단계를 red-writer→implementer 2석 디스패치로 실행 (기본은 red-writer 디스패치 + 세션 직접 구현). 모든 모드와 호환. `--ralph`와 함께 쓰면 무인 루프가 원래 2석이라 중복 지정일 뿐이다
```

`## 플래그 충돌 검증` 절 끝에 한 줄을 더한다: `- `--isolated`는 어떤 플래그와도 충돌하지 않는다. `--status`에서는 무시한다.`

- [ ] **Step 3: Agent 팀 표·Context Slicing·병렬 규칙을 고친다**

EXECUTION 표 제목 `### EXECUTION (RED → IMPLEMENT 순차; red-writer만 코드 격리)`를 `### EXECUTION (RED 디스패치 → IMPLEMENT 세션 직접; `--isolated`·fix 4~5·ralph는 implementer)`로 바꾼다. implementer 행의 역할 셀을 `**GREEN+REFACTOR 통합 — `--isolated`·fix 라운드 4~5 격상·gx-ralph 루프에서 디스패치. 기본 경로는 세션이 같은 계약으로 직접 수행**`으로 바꾼다.

Context Slicing 표의 `implementer (IMPLEMENT)` 행 바로 위에 행을 추가한다:

```markdown
| 세션 IMPLEMENT (기본 경로) | 디스패치 없음 — 오케스트레이터가 RED report·설계서 인터페이스·focused 명령을 직접 읽고 phase-implement "세션 IMPLEMENT 절차"를 수행 |
```

병렬 실행 규칙 4항 `**RGR 사이클 내 순차 강제 (Iron Law)**: red-writer → implementer는 **반드시 순차** 실행한다.`를 `**RGR 사이클 내 순차 강제 (Iron Law)**: red-writer → IMPLEMENT(세션 또는 implementer)는 **반드시 순차** 실행한다.`로 바꾼다. 그 아래 이유 문장의 `implementer의 입력`은 `IMPLEMENT의 입력`으로 바꾼다.

- [ ] **Step 4: phase-setup Step 7과 maintenance-notes를 고친다**

phase-setup Step 7의 `flags` 기록 불릿 끝에 문장을 더한다: ` `--isolated`는 있는 그대로 기록한다 — phase-implement Step 2-I와 phase-review 4b의 경로 판정 키다.`

`references/maintenance-notes.md`의 `**디스패치 프롬프트**(red-writer/implementer — …)` 항목 뒤에 항목을 추가한다:

```markdown
- **세션 IMPLEMENT 계약**(절대 규칙 5항·수행 불가능한 정리 5항·report 형식 5절): phase-implement.md Step 2-I "세션 IMPLEMENT 절차" ↔ `agents/implementer.md`(절대 규칙·REFACTOR 범위·report 파일 형식)에 중복. 린트 [3/33]이 금지 5항목을 양쪽에서 검사하고, [33/33]이 절차 블록 존재를 검사한다.
```

- [ ] **Step 5: 검증**

Run: `grep -c -- '--isolated' .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-tdd/references/maintenance-notes.md; grep -c '2에이전트 순차\|2 에이전트 순차' .claude/skills/gx-tdd/SKILL.md; wc -c .claude/skills/gx-tdd/SKILL.md`
Expected: SKILL.md 4 이상, phase-setup 1 이상, maintenance-notes 1 이상; `0`; SKILL.md ≤ 61,500B (초과하면 Agent 팀 표의 deprecated 행 두 개를 한 줄로 합쳐 상쇄한다).

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 32/32 통과 (`[14]` 모델 프로파일 문구·`[25]` --work·`[32]` 예산 유지), 훅 테스트 통과.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-tdd/references/maintenance-notes.md
git commit -F - <<'MSG'
docs: gx-tdd SKILL.md에 --isolated 플래그와 세션 IMPLEMENT 구조를 반영한다
MSG
```

---

### Task 4: phase-review 정리 모드에 세션 경로를 넣는다

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` — `# 4b: 동작 불변 품질 결함 → implementer 정리 모드 (새 RED 없음)` 블록의 `"예"` 분기

**Interfaces:**
- Consumes: Task 2의 "세션 IMPLEMENT 절차"
- Produces: phase-review.md의 `세션 IMPLEMENT` 문자열 (Task 6 린트 검사 대상)

- [ ] **Step 1: 제목 주석과 "예" 분기를 교체한다**

`# 4b: 동작 불변 품질 결함 → implementer 정리 모드 (새 RED 없음)`을 `# 4b: 동작 불변 품질 결함 → 정리 모드 (새 RED 없음. 기본은 세션 직접, --isolated는 implementer)`로 바꾼다. 다음 주석 행의 `implementer 정리 모드의 GREEN 선행 조건 충족`은 `정리 모드의 GREEN 선행 조건 충족`으로 바꾼다.

`"예"` 분기(현재 `- "예" → Task(subagent_type="oh-my-gx:implementer"):` 부터 `→ 정리 후 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인` 행까지)를 아래로 교체한다:

```
      - "예" → 기본 경로: 오케스트레이터가 직접 정리한다 — phase-implement Step 2-I "세션 IMPLEMENT 절차"의 절대 규칙과 수행 불가능한 정리 목록을 그대로 지키고, 입력은 refactor_only 항목들의 {파일:라인 + 권고}("정리 대상")이며, 정리 한 단위마다 대상 파일 관련 테스트로 조립한 focused 검증을 실행한다. 결과를 `${DEV_DIR}/reports/review-cleanup.md`에 append한다 (리뷰 반복 시 누적).
               state.md flags에 `--isolated`가 있으면 Task(subagent_type="oh-my-gx:implementer") 정리 모드 — 입력 = refactor_only 항목들의 {파일:라인 + 권고}("정리 대상") + 대상 파일 관련 테스트로 조립한 focused 검증 명령 + report 경로 `${DEV_DIR}/reports/review-cleanup.md`. GREEN 유지·동작 변경 금지 계약은 agents/implementer.md의 REFACTOR 규칙을 따르며, GREEN 기준선은 Step 0에서 통과한 전체 테스트다
               → 어느 경로든 정리 후 오케스트레이터가 전체 테스트 1회 직접 실행으로 GREEN 재확인
```

- [ ] **Step 2: 검증**

Run: `grep -c '세션 IMPLEMENT' .claude/skills/gx-tdd/phases/phase-review.md; grep -c 'review-cleanup.md' .claude/skills/gx-tdd/phases/phase-review.md; bash scripts/lint-consistency.sh`
Expected: `1` 이상, `1` 이상, 32/32 통과 (`[28]`·`[27]`은 이 블록을 건드리지 않는다).

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-review.md
git commit -F - <<'MSG'
feat: gx-tdd 리뷰 정리 모드를 세션 직접 수행 기본으로 바꾼다
MSG
```

---

### Task 5: 에이전트 정의·규칙·문서의 2석 서술을 갱신한다

**Files:**
- Modify: `agents/implementer.md:4` (description)
- Modify: `agents/coder.md:4` (description의 gx-tdd 언급)
- Modify: `.claude/rules/skill-routing.md:53`
- Modify: `README.md:255`
- Modify: `docs/tdd-guide.md:427`, `:464`, `:498`
- Modify: `docs/onboarding-guide.md`, `docs/guide.md` — `implementer`가 기본 디스패치처럼 서술된 문장이 있으면 (Step 1의 grep으로 확인)

**Interfaces:**
- Consumes: Task 2·3의 용어("세션 IMPLEMENT", `--isolated`)
- Produces: 없음

- [ ] **Step 1: 대상 문장을 나열한다**

Run: `grep -rnE 'implementer' agents/implementer.md agents/coder.md .claude/rules/skill-routing.md README.md docs/tdd-guide.md docs/onboarding-guide.md docs/guide.md | grep -vE 'green-coder|refactor-coder|humanizer' | cut -c1-140`
Expected: 아래 Step 2~4의 행이 포함된다. 목록에 있으나 아래에 없는 행은 "기본 경로가 implementer 디스패치"라고 읽히는지 판단해, 그렇게 읽히면 같은 방식으로 고치고 커밋 메시지 본문에 행을 적는다.

- [ ] **Step 2: 에이전트 정의 두 개**

`agents/implementer.md` 4행의 `oh-my-gx:gx-tdd 파이프라인과 gx-ralph 루프(루프 모드)가 사용한다`를 `oh-my-gx:gx-tdd에서는 `--isolated` 실행·fix 라운드 4~5 격상·리뷰 정리 모드(`--isolated`)에서 디스패치되고, 기본 경로는 오케스트레이터가 같은 계약으로 직접 구현한다. gx-ralph 루프(루프 모드)는 항상 이 에이전트를 쓴다`로 바꾼다.

`agents/coder.md` 4행의 `구현은 red-writer/implementer가 분담한다`를 `구현은 red-writer(실패 테스트)와 오케스트레이터의 세션 IMPLEMENT(`--isolated`면 implementer)가 분담한다`로 바꾼다.

- [ ] **Step 3: 규칙과 README**

`.claude/rules/skill-routing.md` 53행의 `` `red-writer`/`implementer` 에이전트를 디스패치하므로 ``를 `` `red-writer`를 디스패치하고 IMPLEMENT는 오케스트레이터가 직접 수행하므로(`--isolated`면 `implementer` 디스패치) ``로 바꾼다.

`README.md` 255행의 `` `red-writer`(실패 테스트) → `implementer`(통과 최소 코드 + 정리)의 격리 순차 사이클. ``를 `` `red-writer`(실패 테스트, 격리 디스패치) → 세션이 직접 통과 최소 코드 + 정리(`--isolated`면 `implementer` 디스패치). 태스크는 AC 1건 단위이며 8개를 넘으면 분할을 먼저 묻는다. ``로 바꾼다.

- [ ] **Step 4: TDD 가이드**

`docs/tdd-guide.md` 427행 표 셀 `**red-writer → implementer 순차**`를 `**red-writer 격리 디스패치 → 세션 IMPLEMENT (`--isolated`: implementer)**`로, 464행 `RGR 사이클: red-writer → implementer (태스크별 순차)`를 `RGR 사이클: red-writer → 세션 IMPLEMENT (AC 단위 태스크, 순차)`로, 498행 `(implementer가 테스트를 고치지 않는`을 `(구현 주체가 테스트를 고치지 않는`으로 바꾼다.

- [ ] **Step 5: 검증**

Run: `grep -rnE 'red-writer.{0,12}implementer.{0,12}(순차|사이클)' README.md docs/tdd-guide.md .claude/rules/skill-routing.md agents/coder.md | grep -v isolated; bash scripts/lint-consistency.sh`
Expected: 출력 없음, 32/32 통과 (`[26]`이 agents/implementer.md의 4-status 문자열을 계속 확인한다 — description만 바꿨으므로 유지).

- [ ] **Step 6: 커밋**

```bash
git add agents/implementer.md agents/coder.md .claude/rules/skill-routing.md README.md docs/tdd-guide.md docs/onboarding-guide.md docs/guide.md
git commit -F - <<'MSG'
docs: 세션 IMPLEMENT 구조를 에이전트 정의·규칙·가이드에 반영한다
MSG
```

(onboarding-guide·guide에 고칠 행이 없었으면 `git add`에서 뺀다.)

---

### Task 6: 린트 [33]·골든 시나리오 S38·S39·v1.27.0 릴리스

**Files:**
- Modify: `scripts/lint-consistency.sh` — 헤더 목록, `[32/32]` 블록 뒤에 새 블록, 분모 32→33 전역 치환
- Modify: `[N/32]`를 인용하는 `.claude/`·`README.md` 파일 전부
- Modify: `tests/golden-scenarios.md` — S38·S39 행, `N/37` → `N/39`
- Modify: `CHANGELOG.md` — v1.27.0 절
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` — `1.26.2` → `1.27.0`

**Interfaces:**
- Consumes: Task 1~5의 문자열 (`세션 IMPLEMENT 절차`, `--isolated`, `태스크 수 가드`, `model: "opus"`)
- Produces: 린트 `[33/33] gx-tdd 세션 IMPLEMENT 계약`

- [ ] **Step 1: 새 검사를 `[32/32]` 블록 뒤에 추가한다 (분모는 아직 32)**

```bash
echo "[33/32] gx-tdd 세션 IMPLEMENT 계약"
# 설계: docs/specs/2026-09-07-tdd-density-rhythm-design.md D1·D2
IMPL=.claude/skills/gx-tdd/phases/phase-implement.md
grep -q '세션 IMPLEMENT 절차' "$IMPL" || fail "세션 IMPLEMENT 절차 블록 누락: phase-implement.md"
grep -q -- '--isolated' "$IMPL" || fail "격리 경로 플래그(--isolated) 누락: phase-implement.md"
grep -q -- '--isolated' .claude/skills/gx-tdd/SKILL.md || fail "--isolated 플래그 참조 누락: gx-tdd SKILL.md"
grep -q -- '--isolated' .claude/skills/gx-tdd/phases/phase-setup.md || fail "--isolated flags 기록 규칙 누락: phase-setup.md"
grep -q 'git hash-object' "$IMPL" || fail "테스트 무결성(해시) 검증 누락: phase-implement.md"
grep -q 'focused 집합 직접 실행' "$IMPL" || fail "focused 직접 실행 검증 누락: phase-implement.md"
grep -q 'model: "opus"' "$IMPL" || fail "fix 라운드 4~5 격상 디스패치 누락: phase-implement.md"
grep -q '태스크 수 가드' "$IMPL" || fail "태스크 수 가드 누락: phase-implement.md"
grep -q '작성 범위 — 테스트 집합' "$IMPL" || fail "red-writer 테스트 집합 작성 범위 누락: phase-implement.md"
grep -q '세션 IMPLEMENT' .claude/skills/gx-tdd/phases/phase-review.md || fail "정리 모드 세션 경로 누락: phase-review.md"
[ "$FAIL" -eq 0 ] && ok "세션 IMPLEMENT 절차·--isolated 3곳·무결성 검증·격상 디스패치·태스크 수 가드·테스트 집합 확인"
```

스크립트 헤더의 검사 항목 주석 목록에 `[33/32] gx-tdd 세션 IMPLEMENT 계약`을 `[32/32]` 항목 아래 같은 형식으로 추가한다.

- [ ] **Step 2: 변이 시험 (RED)**

Run: `sed -i 's|^\*\*세션 IMPLEMENT 절차\*\*|**세션 임플리먼트 절차**|' .claude/skills/gx-tdd/phases/phase-implement.md && bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `세션 IMPLEMENT 절차 블록 누락`으로 FAIL, exit 1.

Run: `git checkout -- .claude/skills/gx-tdd/phases/phase-implement.md && grep -c '^\*\*세션 IMPLEMENT 절차\*\*' .claude/skills/gx-tdd/phases/phase-implement.md`
Expected: `1`.

- [ ] **Step 3: 분모를 33으로 올린다**

```bash
sed -i 's|/32\]|/33]|g' scripts/lint-consistency.sh
grep -rlE '\[[0-9]+/32\]' .claude README.md --include=*.md | xargs -r sed -i 's|/32\]|/33]|g'
grep -rnE '\[[0-9]+/32\]' .claude README.md scripts --include=*.md --include=*.sh | grep -v worktrees
```
Expected: 마지막 grep 출력 없음.

- [ ] **Step 4: 골든 시나리오 두 행을 추가한다**

S37 행 아래에 추가하고, 기록 절의 `N/37`을 `N/39`로 바꾼다.

```markdown
| S38 ★ | AC 2개(각 시나리오 2~3건)짜리 전체 모드 gx-tdd 실행, `--isolated` 없음 | `/gx-tdd 포인트 충전 한도 검증 TDD로 구현해줘` | 태스크 2개로 분해된다. 태스크마다 red-writer **1회**만 디스패치되고 implementer 디스패치는 없다. 세션이 실패 케이스를 하나씩 통과시키며 `reports/t{N}-impl.md`를 직접 Write한다. state.md 태스크 객체에 `test-file-hash`·`test-count`가 기록되고 execution-log에 `session-implement (T{N})`가 남는다 |
| S39 | 같은 요청에 `--isolated` | `/gx-tdd --isolated 포인트 충전 한도 검증 TDD로 구현해줘` | 태스크마다 red-writer → implementer **2회** 디스패치. state.md `flags`에 `--isolated`. 나머지 검증(해시·focused 직접 실행)은 S38과 동일 |
```

- [ ] **Step 5: CHANGELOG와 버전**

CHANGELOG 상단에 추가한다:

```markdown
## v1.27.0 (2026-09-07)

gx-tdd 구현 단계의 리듬을 바꾼다. 태스크당 콜드 스타트가 2회에서 1회로 줄고, 태스크 단위가 테스트 1건에서 AC 1건으로 올라간다. red-writer 격리·테스트 해시·focused 직접 실행·verify 지문은 그대로다. 설계: `docs/specs/2026-09-07-tdd-density-rhythm-design.md`.

- **변경 — IMPLEMENT를 세션이 직접 수행**: GREEN+REFACTOR를 오케스트레이터가 `agents/implementer.md`와 같은 계약(테스트 수정 금지·YAGNI·REFACTOR 금지 5항목·focused만 실행·self-review·report Write)으로 직접 수행한다. verify_implement의 해시·porcelain·focused 직접 실행 검증은 주체와 무관하게 같다. fix 라운드 1~3은 세션이 고치고 4~5는 종전대로 fresh implementer + opus 격상이다. 리뷰 정리 모드도 같은 경로다.
- **추가 — `--isolated`**: 현행 red-writer→implementer 2석 디스패치를 되돌린다. gx-ralph 무인 루프는 항상 2석이다.
- **변경 — 태스크 = AC 1건**: red-writer가 AC의 G-W-T 시나리오 전부를 테스트 집합으로 한 번에 쓰고, verify_red는 집합 전체의 실패를 확인한다. 세션은 실패 케이스를 하나씩 통과시키는 내부 루프를 돈다. 같은 컴포넌트·같은 패턴의 AC는 묶는 것이 기본이다.
- **추가 — 태스크 수 가드**: 분해가 8개를 넘으면 승인 전에 "AC 묶어 재분해 / 작업 계획으로 분할 / 무인 루프 전환 / 그대로 진행"을 먼저 묻는다.
- **추가 — 린트 [33] 세션 IMPLEMENT 계약**, 골든 시나리오 S38·S39.
```

```bash
sed -i 's|"version": "1.26.2"|"version": "1.27.0"|' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
```
Expected: 세 파일 모두 `1.27.0`.

- [ ] **Step 6: 검증 (GREEN)**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 33/33 통과, 훅 테스트 통과.

- [ ] **Step 7: 커밋**

```bash
git add scripts/lint-consistency.sh .claude README.md tests/golden-scenarios.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json
git commit -F - <<'MSG'
feat: 린트 [33] 세션 IMPLEMENT 계약과 v1.27.0 릴리스 준비
MSG
```

---

## 완료 기준

- 린트 33/33·훅 테스트 통과. `[32]` 예산이 유지된다 (SKILL.md ≤ 61,500B).
- phase-implement의 기본 경로에 `Task(subagent_type="oh-my-gx:implementer")`가 **격리 경로 블록과 fix 라운드 4~5에만** 남는다.
- 골든 시나리오 S38을 실제로 한 번 돌려 red-writer 디스패치 1회·implementer 0회·`reports/t{N}-impl.md` 세션 작성·`test-file-hash` 기록을 눈으로 확인한다 (PR 체크박스).
- 남는 후속: SKILL.md 인자 절 재작성(45KB 목표), 게이트를 설계 시점으로 모으기, gx-dev 쌍둥이 정리 — 설계 문서 D4.
