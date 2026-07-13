---
name: gx-verify
version: 1.0.0
description: "완료 검증 게이트 - 테스트 명령 직접 실행 + 0 failures 확인 필수. commit/PR 진입 차단. 'should work' 표현 금지."
argument-hint: ""
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Skill
  - AskUserQuestion
---

# gx-verify

> **이 스킬**: verify — 완료 검증 게이트
> **호출 시 주의**: 이 스킬 내에서 다른 스킬을 호출할 때 반드시 `oh-my-gx:` 접두사를 사용한다.

완료를 주장하기 전에 신선한 실행 증거를 수집한다. **Iron Law**: 검증 증거 없이 완료 주장 절대 금지.

---

## Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

위반 시:
- 완료 주장 즉시 철회
- verify 게이트 재실행
- "이전 실행 결과가 있음" 금지. 신선한 실행만 인정

---

## 사용 시점

- `oh-my-gx:gx-tdd` 파이프라인의 complete Phase 진입 전 자동 호출
- 단독 호출: 사용자가 "완료 검증", "verify 게이트" 명시
- 위반 감지 시: 다른 스킬이 "should work", "probably passes" 등 추측 표현 사용 시

---

## 실행 절차

### Step 0: 정체성 확인

```
oh-my-gx:gx-verify — 완료 검증 게이트 진입.
신선한 실행 증거를 수집합니다.
증거 없이 다음 단계 진입 불가.
```

### Step 0.5: 경고 baseline 로드

`oh-my-gx:gx-tdd` 파이프라인의 phase-implement(Step 0.5 기준선 게이트)가 기록한 경고 baseline을 로드한다. gx-verify는 무인자 독립 스킬이므로 `DEV_DIR`을 자체 계산한다:

1. `.claude/config.json`의 `vcs` 값을 확인한다 (없으면 `git`).
2. **git**: `git branch --show-current` → `/`를 `-`로 치환 → `DEV_DIR = .dev/{branch-slug}/`. 결과가 빈 문자열(detached HEAD 등)이면 baseline 탐색을 건너뛰고 그 사실을 보고한다. **svn**: `DEV_DIR = .dev/trunk/`.
3. `${DEV_DIR}/state.md`가 존재하고 **`status: in_progress`**(진행 중 파이프라인)이며 최상위 필드 `warnings-baseline: N`이 있으면 로드한다. **`status: completed`인 옛 파이프라인의 baseline은 로드하지 않는다** (stale 기준에 의한 오차단 방지).
4. 조건 미충족(파일 없음·완료 상태·필드 없음 — 단독 호출 등)이면 → **baseline 없음**으로 진행한다 (Step 4에서 경고 수 보고만, 비교 차단 없음).

### Step 1: 검증 명령 식별

프로젝트 타입별 검증 명령:

| 프로젝트 타입 | 테스트 명령 | 빌드 명령 |
|--------------|------------|----------|
| java-spring (gradle) | `./gradlew test` | `./gradlew build` |
| node | `npm test` | `npm run build` |
| python | `pytest` | (없음) |
| go | `go test ./...` | `go build ./...` |

`.claude/config.json`의 `projectTypes` 설정에서 감지. 기본 config는 `java-spring`·`node`만 정의하므로, `python`·`go` 행은 소비 프로젝트가 `projectTypes`에 해당 타입을 추가했을 때만 도달한다.

**감지 실패 시 (config.json 부재·projectTypes 미매칭·명령 결정 불가)**:
- 기본값은 **게이트 차단**이다. 검증 명령 없이 조용히 통과하는 것은 Iron Law 3 위반.
- AskUserQuestion으로 처리한다: "검증 명령을 감지하지 못했습니다. 게이트를 진행하려면 명령이 필요합니다."
  - "직접 입력" → 입력받은 명령으로 Step 2 진행
  - "건너뛰기 (위험 수용)" → 테스트 검증 없이 진행하되, 보고에 "위험 수용: 검증 명령 미감지"를 명시한다. trust-ledger 기록은 호출한 오케스트레이터가 수행한다 (이 스킬은 Write 권한이 없다)
  - "중단" → 게이트 차단 유지. commit/PR 진입 불가를 보고

### Step 2: 테스트 실행 (직접)

캐시된 결과 사용 금지. **반드시 새로 실행**.

```bash
# 예: java-spring
./gradlew test  # timeout: 300000 (5분)
```

수집 정보:
- exit code
- 테스트 통과 수 / 실패 수
- 실행 시간
- 출력 마지막 30줄 (실패 시 분석용)
- 경고 수 (baseline 비교용 — 아래 측정 규약 참조)

**경고 측정 규약 (SSOT — phase-implement Step 0.5의 baseline 기록도 이 규약을 따른다)**:
1. `mkdir -p ${DEV_DIR}`로 디렉토리 존재를 보장한 뒤, 명령 출력을 파일로 캡처한다: `<명령> > ${DEV_DIR}/verify-{test|build}.log 2>&1` (파이프가 아닌 **리다이렉트** — exit code가 원 명령의 것으로 유지된다). exit code를 먼저 확인한 뒤 로그를 분석한다.
2. 카운트: java-spring은 `grep -ci "warning" <로그>`, node는 `grep -ci "warn" <로그>`, 그 외 타입은 미지원 (카운트 생략·보고만).
3. 이 카운트는 요약 라인("N warnings")·로그 노이즈를 포함하는 **근사치**다. baseline보다 증가했을 때는 차단 전에 **로그 원문에서 실제 경고 라인을 대조**하여 신규 경고인지 확인한다. 노이즈·빌드 캐시 재출력으로 판정되면 차단하지 않고 "측정 노이즈"로 보고한다.
4. baseline과 현재 측정은 **동일한 명령(config.json projectTypes의 test·build)·동일한 규약**을 사용해야 유효하다.

### Step 3: 빌드 실행 (직접)

```bash
./gradlew build  # timeout: 300000
```

수집 정보:
- exit code
- 빌드 시간
- 경고 수 (baseline 비교용 — 추출 방법은 Step 2와 동일)

### Step 4: 증거 분석

```
검증 결과:
- 테스트: {N pass, M fail} (exit code: {0|1})
- 빌드: {success|failure} (exit code: {0|1})
- 경고: {N건} (baseline: {M건 | 없음})
- 실행 시각: {timestamp}
```

판정 (아래 순서로 하나씩 평가한다 — **이 목록이 판정의 단일 기준**이다):
1. 테스트 실패(1건 이상 failures) 또는 빌드 exit ≠ 0 → **게이트 차단**
2. **테스트 실행 수 확인**: 실행 수가 0건이거나 확인 불가("No tests found", gradle `:test UP-TO-DATE`처럼 콘솔에 개수 미표기)이면 먼저 실행 수를 확정한다 — gradle은 `build/test-results/test/*.xml`의 tests 합계로 확인하고, UP-TO-DATE(캐시)였다면 `./gradlew test --rerun-tasks`로 1회 신선 재실행한다. 확정 후에도 0건이면 → **게이트 차단**. AskUserQuestion — "테스트 명령/경로 확인 후 재실행" / "위험 수용 (테스트 부재 진행 — 보고에 명시, trust-ledger 기록은 오케스트레이터)" / "중단". **단, Step 1에서 이미 '건너뛰기(위험 수용)'를 선택했다면 이 검사를 건너뛴다** (동일 위험의 이중 차단 방지).
3. **신규 경고 비교** (Step 0.5에서 baseline을 로드한 경우만): 현재 경고 수(테스트+빌드)가 `warnings-baseline`보다 크면 측정 규약 3항대로 로그 원문을 대조하고, **실제 신규 경고로 확인되면** → **게이트 차단**. AskUserQuestion — "수정 후 재실행" / "위험 수용 (통과 처리하되 보고에 "위험 수용: 신규 경고 {N}건" 명시, trust-ledger 기록은 오케스트레이터)". baseline이 없으면(단독 호출 등) 경고 수를 보고만 한다.
4. 위 어디에도 걸리지 않음 → **게이트 통과**

### Step 5-A: 게이트 통과

```
✅ verify 게이트 통과

증거:
- 테스트: 47 pass, 0 fail
- 빌드: success
- 실행 시각: 2026-05-16T15:00:00

다음 단계 진행 가능 (commit, PR 등).
```

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
| "관련 부분 외에는 영향 없음" | 영향 검증 = 전체 테스트 실행 |
| "에이전트가 통과했다고 보고" | 에이전트 보고는 검증이 아님. 직접 실행 |
| "급하니 일부 테스트만 실행" | 일부 실행은 검증 아님. 전체 또는 명확한 격리 |
| "테스트가 flaky해서 무시" | flaky test는 fix 대상. 무시는 부채 누적 |
| "실행할 테스트가 없으니 통과" | 명령 미감지는 통과가 아니라 차단 사유. 직접 입력 또는 중단 |
| "명령이 성공했고 실패도 없으니 통과" | 0개 실행은 검증이 아니다. 최소 1건 실행을 확인하라 |

자세한 격파 표는 `.claude/skills/gx-tdd/references/tdd-iron-law.md` 참조.

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
