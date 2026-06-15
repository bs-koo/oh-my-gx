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

### Step 1: 검증 명령 식별

프로젝트 타입별 검증 명령:

| 프로젝트 타입 | 테스트 명령 | 빌드 명령 |
|--------------|------------|----------|
| java/kotlin | `./gradlew test` | `./gradlew build` |
| node | `npm test` | `npm run build` |
| python | `pytest` | (없음) |
| go | `go test ./...` | `go build ./...` |

`.claude/config.json`의 `projectTypes` 설정에서 감지.

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

### Step 3: 빌드 실행 (직접)

```bash
./gradlew build  # timeout: 300000
```

수집 정보:
- exit code
- 빌드 시간
- 경고 수 (있으면 보고)

### Step 4: 증거 분석

```
검증 결과:
- 테스트: {N pass, M fail} (exit code: {0|1})
- 빌드: {success|failure} (exit code: {0|1})
- 실행 시각: {timestamp}
```

판정:
- ✅ 테스트 0 failures + 빌드 exit 0 → **게이트 통과**
- ❌ 어느 하나라도 실패 → **게이트 차단**

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
1. 실패한 테스트의 원인을 분석합니다 (oh-my-gx:gx-red로 복귀)
2. 수정 후 다시 verify 게이트를 호출합니다

commit/PR 진입은 차단됩니다.
```

오케스트레이터에게 차단 알림 → red-green-refactor 사이클 재진입.

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

자세한 격파 표는 `.claude/rules/tdd-iron-law.md` 참조.

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

✅ 올바름:
- `Skill("oh-my-gx:gx-red")` — 차단 시 RED 단계 복귀
- `Skill("oh-my-gx:gx-commit")` — 통과 시 커밋 진입

❌ 금지:
- `Skill("red")`, `Skill("commit")` — 접두사 누락
- verify 미통과 상태에서 커밋/PR 진입 — Iron Law 3 위반

**위반 시**: 즉시 중단하고 fully-qualified 이름으로 재호출.
