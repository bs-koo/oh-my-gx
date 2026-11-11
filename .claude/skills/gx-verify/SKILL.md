---
name: gx-verify
version: 1.0.0
description: 완료 검증·verify 게이트·커밋·PR 전 검증 요청에 사용한다. 현재 코드의 테스트·빌드 실행 근거를 확인하고 검증 통과 여부를 판정한다.
argument-hint: "[--non-interactive]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Skill
  - AskUserQuestion
---

# 변경 검증

> **이 스킬**: verify — 완료 검증 게이트
> **호출 시 주의**: 이 스킬 내에서 다른 스킬을 호출할 때 반드시 `oh-my-gx:` 접두사를 사용한다.

완료를 주장하기 전에 현재 코드의 실행 증거를 확인한다. [테스트 실행 계약](../gx-tdd/references/test-execution.md)을 먼저 읽고 영향 범위 선택·같은 실행의 정확한 증거 재사용·전체 폴백을 적용한다. **Iron Law**: 검증 증거 없이 완료 주장 절대 금지.

---

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("../gx-work/references/codex-runtime.md")`로 공통 실행 규약을 읽고, 이 스킬의 절차·게이트를 유지한다. 상대경로는 이 SKILL.md 위치 기준이다.
Codex 지문 helper의 설치 경로는 **이 SKILL.md 디렉토리 기준** [../../../scripts/codex-fingerprint.py](../../../scripts/codex-fingerprint.py)다. 실제 설치된 SKILL.md 절대경로 `SKILL_PATH`에 대해 `Path(SKILL_PATH).resolve().parents[3]`가 `GX_PLUGIN_ROOT`이며, `.codex-plugin/plugin.json`과 helper의 존재를 확인한다. Windows PowerShell: `$skillPath = (Resolve-Path -LiteralPath '<installed SKILL.md>').Path; $pluginRoot = (Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $skillPath) '..\..\..')).Path; $helper = (Resolve-Path -LiteralPath (Join-Path $pluginRoot 'scripts/codex-fingerprint.py')).Path`. 아래 지문 명령의 `<GX_PLUGIN_ROOT>`는 이 경로로만 치환하고, Windows에서는 확인한 `$helper` 절대경로를 사용한다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → 공통 codex-runtime의 질문 대기 계약으로 옮긴다. 실제 모드·용도가 허용하는 `request_user_input`·`request_user_input_async` 또는 자연어를 사용한다. 필수 질문은 pending 상태를 저장하고 실제 답변·결정 기록 전 다음 단계로 넘어가지 않는다. async 반환은 답변이 아니며 본문·선택지를 표시한다.
- `Skill(skill: "oh-my-gx:{name}")` → 해당 스킬의 `SKILL.md`를 읽어 그 절차를 수행한다.

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.

## Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

위반 시:
- 완료 주장 즉시 철회
- verify 게이트 재실행
- 이전 세션 결과로 통과 금지. 같은 실행의 정확한 지문·명령·config·scope 증거만 재사용

---

## 사용 시점

- `oh-my-gx:gx-tdd` 파이프라인의 complete Phase 진입 전 자동 호출
- 단독 호출: 사용자가 "완료 검증", "verify 게이트" 명시
- 위반 감지 시: 다른 스킬이 "should work", "probably passes" 등 추측 표현 사용 시

---

## 모드 (--non-interactive)

ARGS에 `--non-interactive`가 포함되면 **비대화 모드**로 동작한다. 응답할 사용자가 없는 헤드리스 세션용이다 — 헤드리스에는 AskUserQuestion 도구가 존재하지 않아 대화 분기가 성립하지 않는다.

- **기본(무인자)**: 기존 대화형 동작 그대로다. 아래 절차의 AskUserQuestion 분기가 모두 유효하다.
- **비대화 모드**: AskUserQuestion 분기 3곳(Step 1 감지 실패, Step 4 판정 2·판정 3)을 질문 없이 **fail-closed 게이트 차단**으로 대체한다. 차단 보고는 Step 5-B 형식을 따르고 차단 사유를 명시한다. "위험 수용"·"건너뛰기" 선택지는 비대화 모드에 존재하지 않는다.

---

## 실행 절차

진입 배너는 출력하지 않는다. 바로 Step 0.5부터 수행한다.

### Step 0.5: 경고 baseline 로드

`oh-my-gx:gx-tdd` 파이프라인의 phase-implement(Step 0.5 기준선 게이트)가 기록한 경고 baseline을 로드한다. gx-verify는 무인자 독립 스킬이므로 `DEV_DIR`을 자체 계산한다:

1. `.claude/config.json`의 `vcs` 값을 확인한다 (없으면 `git`).
2. **git**: `git branch --show-current` → `/`를 `-`로 치환 → `DEV_DIR = .dev/{branch-slug}/`. 결과가 빈 문자열(detached HEAD 등)이면 baseline 탐색을 건너뛰고 그 사실을 보고한다. **svn**: `.dev/.active`가 가리키는 `DEV_DIR = .dev/{slug}/`를 사용한다 (`.active` 부재·공백 시 `.dev/trunk/` 폴백).
3. `${DEV_DIR}/state.md`가 존재하고 **`status: in_progress`**(진행 중 파이프라인)이며 최상위 필드 `warnings-baseline: N`이 있으면 로드한다. **`status: completed`인 옛 파이프라인의 baseline은 로드하지 않는다** (stale 기준에 의한 오차단 방지).
4. 조건 미충족(파일 없음·완료 상태·필드 없음 — 단독 호출 등)이면 → **baseline 없음**으로 진행한다 (Step 4에서 경고 수 보고만, 비교 차단 없음).
5. baseline 유무와 무관하게, `${DEV_DIR}/state.md`가 `status: in_progress`이고 `known-failures`(기존 실패 ID 목록)·`test-plan-override`가 있으면 로드한다.

### Step 1: 검증 명령 식별

Git은 먼저 test-execution.md의 helper로 변경·태스크 소유 관계를 포함한 계획을 생성한다. 필수 테스트의 RED 해시 확인은 생략하지 않는다. 이 계획을 review와 verify에서 공유하며 모든 감지 프로젝트의 entry 또는 명시적 제외 사유를 확인한다. helper 실패 시 기본값은 게이트 차단이다. `test-plan-override`가 로드되었으면 helper `override` 계획으로 그 `command`를 `reuse`/`record`하고 다시 묻지 않는다(테스트 실행 계약 "계획 실패 처리"). 사용자의 전체 회귀 요청은 helper `--full`로 반영한다. **SVN은 Git helper·지문·증거 재사용을 적용하지 않는다.** 모든 감지 프로젝트의 config `test`와 테스트가 없는 `buildOnly`를 순차 직접 실행하는 보수적 폴백을 사용한다. 테스트 수·exit·경고 게이트는 동일하게 지킨다.

프로젝트 타입별 검증 명령:

| 프로젝트 타입 | 테스트 명령 | 빌드 명령 |
|--------------|------------|----------|
| java-spring (gradle) | `./gradlew test` | `./gradlew build -x test testClasses` |
| node | `npm test` | `npm run build` |
| python | `pytest` | (없음) |
| go | `go test ./...` | `go build ./...` |

**SSOT는 config `projectTypes`다** — 위 표는 예시(파생 사본)이며, config에 등록된 타입·명령이 항상 우선한다. 기본 템플릿은 `java-spring`·`node`만 정의하므로 그 외 행은 소비 프로젝트가 등록했을 때만 도달한다. 어떤 언어든 `/gx-setup`의 "프로젝트 타입 등록" 단계로 등록하면 이후 자동 감지된다.

**복수 타입이 감지되면 전부 실행한다.** `detect` 매칭이 2개 이상이면 각 프로젝트의 계획된 test·build entry를 실행하거나 같은 실행의 정확한 증거를 재사용하고, **하나라도 실패하면 게이트를 차단**한다. 한쪽만 골라 실행하면 나머지 레이어(흔히 프론트엔드)가 검증 없이 통과하는데, 그건 verify 게이트가 존재하는 이유를 정면으로 무효화한다. 경고 카운트는 타입별 `warningPattern`으로 각각 세어 합산한다. 실행 순서는 config 등록 순서를 따른다.

복합 명령 하나로 등록된 경우(`"test": "A && B"`)는 그 자체가 단일 명령이므로 그대로 실행하면 된다 — 등록 방식은 `/gx-setup`이 안내한다.

**감지 실패 시 (config.json 부재·projectTypes 미매칭·명령 결정 불가)**:
- 기본값은 **게이트 차단**이다. 검증 명령 없이 조용히 통과하는 것은 Iron Law 3 위반.
- **비대화 모드**: 질문 없이 즉시 게이트 차단으로 종료한다 — 보고: "검증 명령 미감지 (비대화 모드 fail-closed)".
- (대화형) AskUserQuestion으로 처리한다: "검증 명령을 감지하지 못했습니다. 게이트를 진행하려면 명령이 필요합니다. (영구 등록은 /gx-setup의 프로젝트 타입 등록을 사용하세요)" — helper 오류 원문 한 줄과 config 수정안을 본문에 함께 보인다
  - "직접 입력" → 입력받은 명령으로 Step 2 진행
  - "건너뛰기 (위험 수용)" → 테스트 검증 없이 진행하되, 보고에 "위험 수용: 검증 명령 미감지"를 명시한다. trust-ledger 기록은 호출한 오케스트레이터가 수행한다 (이 스킬은 Write 권한이 없다)
  - "중단" → 게이트 차단 유지. commit/PR 진입 불가를 보고

### Step 2: 테스트 실행 (직접)

계획의 test entry마다 `reuse`를 확인한다. **같은 runId·정확한 코드 지문·configHash·명령·scope·로그 해시가 모두 일치한 성공 증거**는 재사용한다. 나머지는 선택된 명령을 직접 실행하고 `record`한다. 이전 세션·실패·0건·실행 수 미확정 결과는 재사용하지 않는다. 범위를 줄일 근거가 없으면 helper가 명시한 전체 폴백을 실행한다. 단독 verify는 새 runId이므로 기존 증거를 재사용하지 않는다.

검증 실행 중에는 다른 테스트·빌드 명령을 병행하지 않는다 (호출자 포함 — 같은 빌드 데몬·DB·CPU 경합은 시간 제한 테스트 오탐과 테스트 프로세스 메모리 부족을 부른다). 복수 타입도 config 등록 순서대로 하나씩 실행한다. 시작 알림·백그라운드 실행·시간 초과는 테스트 실행 계약 "긴 실행과 시간 초과"를 따른다.

```bash
# 예: java-spring
./gradlew test --tests LoginTest  # 선택 계획 예시, timeout: config timeouts.build
```

수집 정보:
- exit code
- 테스트 통과 수 / 실패 수 / 실패 테스트 ID (`known-failures` 대조용)
- 실행 시간
- 출력 마지막 30줄 (실패 시 분석용)
- 경고 수 (baseline 비교용 — 아래 측정 규약 참조)

**경고 측정 규약 (SSOT — phase-implement Step 0.5의 baseline 기록도 이 규약을 따른다)**:
1. `mkdir -p "${DEV_DIR}/evidence"`로 entry 로그 디렉토리 존재를 보장한 뒤, 명령 출력을 파일로 캡처한다: `<명령> > ${DEV_DIR}/evidence/{entry.id}.log 2>&1` (파이프가 아닌 **리다이렉트** — exit code가 원 명령의 것으로 유지된다). exit code를 먼저 확인한 뒤 로그를 분석한다.
2. 카운트: config `projectTypes`의 **`warningPattern` 필드**를 사용해 `grep -ci "<warningPattern>" <로그>`로 센다. 필드가 없으면 폴백 — java-spring은 `grep -ci "warning"`, node는 `grep -ci "warn"`, 그 외 타입은 미지원 (카운트 생략·보고만).
3. 이 카운트는 요약 라인("N warnings")·로그 노이즈를 포함하는 **근사치**다. baseline보다 증가했을 때는 차단 전에 **로그 원문에서 실제 경고 라인을 대조**하여 신규 경고인지 확인한다. 노이즈·빌드 캐시 재출력으로 판정되면 차단하지 않고 "측정 노이즈"로 보고한다.
4. baseline과 현재 측정은 **동일한 명령·scope·규약**을 사용해야 유효하다. 범위가 달라졌으면 합계 차이로 차단하지 않고 신규 경고 원문을 대조한다. 재사용한 증거도 원래 로그의 경고를 분석한다.

### Step 3: 빌드 실행 (직접)

계획의 build entry도 정확히 일치하는 같은 실행 증거는 재사용한다. 없으면 `buildOnly`를 직접 실행하고 기록한다. 빌드 명령에 테스트가 포함되지 않게 한다. custom 명령의 테스트 제외 여부를 확정할 수 없으면 `buildOnly`를 명시할 때까지 차단한다. 기본 Gradle 명령의 제한적 변환은 test-execution.md를 따른다.

```bash
./gradlew build -x test testClasses  # timeout: config timeouts.build
```

수집 정보:
- exit code
- 빌드 시간
- 경고 수 (baseline 비교용 — 추출 방법은 Step 2와 동일)

### Step 4: 증거 분석

[판단과 검증 전달](../gx-work/references/reviewability.md)에 따라 검증한 동작·남은 중요한 미검증 조건·실제 명령/cwd/로그 위치를 결과에 포함한다. 이 범위 밖 운영·배포·문서 의미까지 통과했다고 확대하지 않는다. 사용자 요청이 없으면 전체 로그를 대화에 반복 출력하지 않는다.

```
검증 결과:
- 테스트: {N pass, M fail} (exit code: {0|1})
- 빌드: {success|failure} (exit code: {0|1})
- 경고: {N건} (baseline: {M건 | 없음})
- 실행 시각: {timestamp}
```

판정 (아래 순서로 하나씩 평가한다 — **이 목록이 판정의 단일 기준**이다):
1. `known-failures` 밖의 **새** 테스트 실패 1건 이상 또는 빌드 exit ≠ 0 → **게이트 차단**. 목록 안 실패는 차단하지 않고 보고만 한다. 해소 알림·시간 초과는 테스트 실행 계약을 따르며 하네스·비대화 모드와 무관하다
2. **테스트 실행 수 확인**: 실행 수가 0건이거나 확인 불가("No tests found", gradle `:test UP-TO-DATE`처럼 콘솔에 개수 미표기)이면 먼저 실행 수를 확정한다 — gradle은 해당 프로젝트 `build/test-results/test/*.xml`의 tests 합계를 확인하고 신선한 증거가 없으면 helper plan --rerun-tests로 계획을 다시 만들어 **선택된 명령**에 `--rerun-tasks`를 붙여 1회 재실행한다. 실제 실행한 정확한 명령으로 계획·증거를 다시 기록한다. 0건/미확정은 재사용 가능한 증거를 만들지 않는다. 확정 후에도 0건이면 → **게이트 차단**. **비대화 모드**: 질문 없이 차단 보고("테스트 실행 0건")로 종료. (대화형) AskUserQuestion — "테스트 명령/경로 확인 후 재실행" / "위험 수용 (테스트 부재 진행 — 보고에 명시, trust-ledger 기록은 오케스트레이터)" / "중단". **단, Step 1에서 이미 '건너뛰기(위험 수용)'를 선택했다면 이 검사를 건너뛴다** (동일 위험의 이중 차단 방지). 명시적 ignore로 test entry가 없는 프로젝트는 제외 사유를 보고하고 저장소 필수 구조 검사·린트는 유지한다.
3. **신규 경고 비교** (Step 0.5에서 baseline을 로드한 경우만): 동일 명령·scope의 현재 경고 수(테스트+빌드)가 `warnings-baseline`보다 크면 측정 규약 3항대로 로그 원문을 대조하고, **실제 신규 경고로 확인되면** → **게이트 차단**. **비대화 모드**: 질문 없이 차단 보고(신규 경고 목록 포함)로 종료. (대화형) AskUserQuestion — "수정 후 재실행" / "위험 수용 (통과 처리하되 보고에 "위험 수용: 신규 경고 {N}건" 명시, trust-ledger 기록은 오케스트레이터)". baseline이 없으면(단독 호출 등) 경고 수를 보고만 한다.
4. 위 어디에도 걸리지 않음 → **게이트 통과**

### Step 5-A: 게이트 통과

통과 시 **코드 지문을 함께 계산해 기록용 블록에 싣는다**. state.md 기록은 호출한 오케스트레이터가, 단독 호출이면 메인 세션이 `references/output.md`대로 수행한다.

git 저장소는 통과 보고 전에 반드시 `Read("references/fingerprint.md")`를 읽고 현재 하네스의 계산·형식·실패 처리를 수행한다. Codex helper 부재·실패·빈/잘못된 지문은 테스트·빌드가 통과했어도 게이트 차단이며 pending·기존 지문 제거를 요청한다. 이전 passed를 유지하지 않는다. svn은 지문을 "해당 없음"으로 보고한다.

통과 출력은 `Read("references/output.md")`대로 나눈다. 사용자에게는 결과·테스트 수·범위 한 줄만 보인다. 코드 지문 등 내부 식별자와 state 기록 지시(`verify-status: passed`·`verify-fingerprint`)는 오케스트레이터 기록용 블록에만 둔다.

오케스트레이터(`oh-my-gx:gx-tdd`)가 호출했으면 다음 Phase 진입 신호.

### Step 5-B: 게이트 차단

```
❌ verify 게이트 차단

실패 증거:
- 테스트: 45 pass, 2 fail
  - LoginServiceTest.shouldRejectInvalidPassword
  - LoginServiceTest.shouldRateLimitFailedAttempts
- 빌드: success

조치:
1. 파이프라인(oh-my-gx:gx-tdd) 호출이면 → phase-complete Step -1의 처리 분기(RGR 수정/수동 수정/중단)를 따릅니다
2. 단독 호출이면 → 실패 원인 분석 후 oh-my-gx:gx-red 복귀를 권고합니다
3. 수정 후 다시 verify 게이트를 호출합니다

commit/PR 진입은 차단됩니다.
```

오케스트레이터에게 차단을 알린다 (복귀 방식은 위 조치의 분기를 따른다 — 파이프라인이면 phase-complete의 사용자 선택, 단독이면 gx-red 복귀 권고).

---

## 합리화 격파 표

| 변명 | 반박 |
|------|------|
| "방금 전에 통과한 것을 봤음" | 직전 변경 후 신선한 실행 필요 |
| "should pass now" | "should"는 검증이 아니다. 실행 결과만 신뢰 |
| "linter가 통과했음" | linter는 컴파일/실행 검증 아님 |
| "관련 부분 외에는 영향 없음" | 명시적 소유·매핑·runner 근거가 있어야 범위를 줄인다 |
| "에이전트가 통과했다고 보고" | 에이전트 보고는 검증이 아님. 직접 실행 |
| "급하니 일부 테스트만 실행" | 변경/영향 범위 계획이 필요하며 미매핑은 전체 폴백 |
| "테스트가 flaky해서 무시" | flaky test는 fix 대상. 무시는 부채 누적 |
| "실행할 테스트가 없으니 통과" | 명령 미감지는 통과가 아니라 차단 사유. 직접 입력 또는 중단 |
| "명령이 성공했고 실패도 없으니 통과" | 0개 실행은 검증이 아니다. 최소 1건 실행을 확인하라 |

자세한 격파 표는 이 SKILL.md 기준 `../gx-tdd/references/tdd-iron-law.md` 참조.

---

## Red Flags

### "should/probably" 어휘 감지

다음 표현이 발견되면 즉시 verify 호출:
- "테스트가 통과할 것 같음"
- "이 변경으로 버그가 고쳐졌을 것"
- "should work"
- "looks good"
- "probably passes"

### 만족 표현 감지

검증 증거 없는 만족 표현 차단:
- "완료!"
- "Great!"
- "Perfect!"
- "Done!"

→ 모두 verify 게이트 호출. 신선한 실행 증거 수집.

---

## 사용자 안내 톤

verify 차단 시 사용자에게 알릴 때:

✅ 권장: "verify 게이트가 차단되었습니다. {N건 실패}. 다음 단계 진입을 위해 실패 원인을 해결해야 합니다. 자세한 실패 메시지: {경로}"

❌ 금지: "당신이 잘못 했습니다", "왜 테스트를 안 했나요?"

차단은 사용자 책임 추궁이 아니라 안전망이다.

---

## 다른 스킬 호출 시 절대 규칙 (Iron Law)

✅ 올바름 (단독 호출 시):
- `Skill("oh-my-gx:gx-red")` — 차단 시 RED 단계 복귀
- `Skill("oh-my-gx:gx-commit")` — 통과 시 커밋 진입
(파이프라인 호출이면 복귀·커밋 주체는 오케스트레이터다 — phase-complete가 인수 검증 후 commit을 호출한다)

❌ 금지:
- `Skill("red")`, `Skill("commit")` — 접두사 누락
- verify 미통과 상태에서 커밋/PR 진입 — Iron Law 3 위반

**위반 시**: 즉시 중단하고 fully-qualified 이름으로 재호출.
