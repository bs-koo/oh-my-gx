# 공식 프롬프팅 가이드 정렬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude 공식 프롬프팅 가이드(Opus 5 · Sonnet 5)가 이름을 대고 경고한 안티패턴 3건을 플러그인에서 제거하고, 그 계약을 정합성 린트로 고정한다.

**Architecture:** 세 건 모두 마크다운 프롬프트 수정이므로 코드 테스트가 성립하지 않는다. 대신 이 저장소의 검증 수단인 `scripts/lint-consistency.sh`를 테스트로 쓴다. 각 태스크는 **린트 검사를 먼저 추가해 FAIL을 확인(RED)하고, 문서를 고쳐 통과시킨다(GREEN)**. 각 태스크는 린트 통과 상태로 끝나므로 CI(`.github/workflows/lint.yml`)가 중간 커밋에서도 초록이다.

**Tech Stack:** Bash (린트 스크립트), Markdown (스킬·에이전트 정의)

**Spec:** `https://claude.ai/code/artifact/0d15c9c7-8d25-4de5-9117-4f6428238f53` (Fable 도입 설계안 2판 — 설계 B·D 및 "Fable 무관 항목" 절)

## Global Constraints

- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (PreToolUse 훅 G1이 차단). 작업 시작 전 `feat/prompt-guide-alignment` 브랜치를 생성한다.
- **커밋**: `git commit`을 직접 실행하지 않는다. `.claude/rules/skill-routing.md`에 따라 `Skill(skill: "oh-my-gx:gx-commit")`으로 커밋한다.
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 **둘 다 통과**한 상태로 끝난다.
- **린트 번호 체계**: 현재 `[N/26]`. 태스크마다 검사 1개를 추가하며 분모를 1씩 올린다. 스크립트 헤더의 "검사 항목" 주석 목록에도 같은 번호로 항목을 추가한다. 스크립트 본문 주석에 `[15/26]`처럼 **자기 참조 문자열이 있으므로** 분모 치환은 전역으로 수행한다.
- **`sed -i` 이식성**: 아래 단계는 GNU sed(Linux·Git Bash)를 전제한다. macOS의 BSD sed에서는 `sed -i '' 's|...|...|g'`처럼 빈 확장자 인자가 필요하다. 치환 후 반드시 `grep -c`로 결과를 확인한다.
- **외과적 변경**: 지시된 줄만 고친다. 주변 문장·포매팅을 함께 다듬지 않는다.

---

## File Structure

| 파일 | 책임 | 태스크 |
|------|------|--------|
| `scripts/lint-consistency.sh` | 계약 검사 3건 추가 (`[27]`·`[28]`·`[29]`) | 1·2·3 |
| `.claude/skills/gx-tdd/phases/phase-review.md` | security 집계 부재를 0건과 구분하는 fail-closed 규약 | 1 |
| `agents/reviewer.md` | 발견 단계 커버리지 지시 + 보안 항목 보고 표현 정정 | 2 |
| `agents/qa-manager.md` | `[Info]` 보고 개수 상한 제거 | 2 |
| `.claude/skills/gx-ralph-iterate/SKILL.md` | 헤드리스 조기 턴 종료 방지 철칙 | 3 |

---

### Task 1: security_verdict fail-closed

**근거:** `phase-review.md:200`의 현행 규약은 "블록 부재 → 산문 집계 폴백"에서 끝난다. security-auditor 출력 자체가 비면 산문도 없으므로 **집계가 0건인 채로 Step 4.3 요약과 4c의 MEDIUM 처리가 진행된다.** spec/quality 경로에는 재호출·중단 계층이 있는데 security에만 없다.

**Files:**
- Modify: `scripts/lint-consistency.sh` (헤더 주석 + `[26/26]` 블록 뒤에 새 검사 추가)
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md:200`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 린트 분모 `27`. 다음 태스크는 `[N/27]`을 `[N/28]`로 올린다.

- [ ] **Step 1: 작업 브랜치 생성**

```bash
git checkout -b feat/prompt-guide-alignment
git branch --show-current
```

기대: `feat/prompt-guide-alignment` 출력.

- [ ] **Step 2: 린트 분모를 26에서 27로 올린다**

```bash
sed -i 's|/26\]|/27]|g' scripts/lint-consistency.sh
grep -c '/27\]' scripts/lint-consistency.sh
```

기대: 27 이상의 숫자 출력 (검사 26개 + 주석 자기 참조).

- [ ] **Step 3: 헤더 주석에 항목 27을 추가한다**

`scripts/lint-consistency.sh`에서 이 줄을 찾는다:

```bash
# 26. implement report 계약 (report 경로·4-status·ralph 2석 디스패치)
```

바로 뒤에 다음 줄을 추가한다:

```bash
# 27. security_verdict fail-closed 계약 (집계 부재 판별·재호출·헤드리스 BLOCKED·원장 기록)
```

- [ ] **Step 4: 실패하는 린트 검사를 추가한다**

`scripts/lint-consistency.sh`에서 `[26/27] implement report 계약` 블록의 마지막 줄을 찾는다:

```bash
[ "$FAIL" -eq 0 ] && ok "report 경로·4-status·ralph 2석 디스패치 확인"
```

바로 뒤, `if [ "$FAIL" -ne 0 ]; then` 앞에 다음을 추가한다:

```bash

echo "[27/27] security_verdict fail-closed 계약"
# security_verdict에는 verdict 필드가 없어 "판정 실패"가 겉으로 드러나지 않는다.
# 집계를 확보하지 못한 상태를 0건과 구분하지 않으면 감사 없이 통과하는 경로가 열린다.
REVIEW_MD=.claude/skills/gx-tdd/phases/phase-review.md
grep -qF '블록과 산문 집계가 모두 부재하면' "$REVIEW_MD" \
  || fail "security 집계 부재 판별 문구 누락: $REVIEW_MD"
grep -qF 'security 감사 집계 확보 실패' "$REVIEW_MD" \
  || fail "헤드리스 BLOCKED 사유 문구 누락: $REVIEW_MD"
grep -qF 'security 감사 미확보' "$REVIEW_MD" \
  || fail "trust-ledger 기록 문구 누락: $REVIEW_MD"
[ "$FAIL" -eq 0 ] && ok "security fail-closed 3계층 확인"
```

- [ ] **Step 5: 린트를 실행해 실패를 확인한다**

```bash
bash scripts/lint-consistency.sh
```

기대: `[27/27] security_verdict fail-closed 계약` 아래에 FAIL 3줄이 출력되고, 마지막에 `정합성 린트 실패`와 함께 종료 코드 1.

- [ ] **Step 6: phase-review.md의 security 규약을 고친다**

`.claude/skills/gx-tdd/phases/phase-review.md:200`의 이 줄을 찾는다:

```markdown
- `security_verdict`: CRITICAL/HIGH/MEDIUM 집계. 블록 부재 시 산문 집계로 폴백한다 (verdict 필드 없음 — 집계는 Step 4.3 요약과 4c의 MEDIUM 처리에 사용).
```

다음으로 교체한다:

```markdown
- `security_verdict`: CRITICAL/HIGH/MEDIUM 집계. 블록 부재 시 산문 집계로 폴백한다 (verdict 필드 없음 — 집계는 Step 4.3 요약과 4c의 MEDIUM 처리에 사용). **블록과 산문 집계가 모두 부재하면 "집계 0건"이 아니라 "집계 미확보"다** — security-auditor를 1회 재호출한다 (spec/quality의 재호출 합산 1회와 별도 카운트). 재호출 출력에도 집계가 없으면: 대화형은 AskUserQuestion으로 "위험 수용(원장 기록 후 진행)" / "중단"을 확인하고, 헤드리스(gx-ralph-iterate)는 `<ralph>BLOCKED: security 감사 집계 확보 실패</ralph>`로 종료한다. 위험 수용을 선택하면 Step 4.1에서 trust-ledger에 `security 감사 미확보 — 위험 수용` 항목을 기록한다 (SPEC FAIL의 "이대로 진행"과 같은 취급 — 감사 흔적 없이 통과하는 경로를 남기지 않는다).
```

- [ ] **Step 7: 린트와 훅 테스트를 실행해 통과를 확인한다**

```bash
bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh
```

기대: `ok: security fail-closed 3계층 확인`과 `정합성 린트 통과`가 출력되고, 훅 테스트도 통과.

- [ ] **Step 8: 커밋**

`Skill(skill: "oh-my-gx:gx-commit")`를 호출한다. 커밋 메시지 방향:

```
fix: security_verdict 집계 미확보를 0건과 구분한다
```

---

### Task 2: 리뷰 발견 단계를 커버리지로 전환

**근거:** Sonnet 5 가이드가 이름을 대고 경고한 패턴이다 — *"리뷰 프롬프트에 '사소한 지적은 하지 마라' 같은 내용이 있으면, Claude Sonnet 5는 이전 모델보다 그 지시를 더 충실히 따를 수 있다. 같은 깊이로 조사하고도 보고를 누락한다."* `qa-manager.md:171`의 "3개 이내로 제한"이 정확히 이것이고, qa-manager는 `model: sonnet`이다. Opus 5 가이드도 같은 권고를 한다 — *"모든 것을 보고하도록 요청하고 별도 패스에서 필터링하라."* 우리는 하류 필터(`[동작결함]/[동작불변]` 라우팅, `quality_verdict` 블록, fix loop 라운드)가 이미 완비돼 있어 이 구조가 성립한다.

**Files:**
- Modify: `scripts/lint-consistency.sh` (분모 27→28, 검사 `[28]` 추가)
- Modify: `agents/reviewer.md` (Part 2 섹션 + 금지 사항 표현)
- Modify: `agents/qa-manager.md:171`

**Interfaces:**
- Consumes: 린트 분모 `27` (Task 1이 남긴 값)
- Produces: 린트 분모 `28`. reviewer의 출력 형식·verdict 블록 스키마는 **변경하지 않는다** — Step 4.0 파서가 그대로 동작해야 한다.

- [ ] **Step 1: 린트 분모를 27에서 28로 올리고 헤더에 항목을 추가한다**

```bash
sed -i 's|/27\]|/28]|g' scripts/lint-consistency.sh
```

헤더 주석에서 `# 27. security_verdict fail-closed 계약 ...` 줄 뒤에 추가한다:

```bash
# 28. 리뷰 발견 단계 커버리지 계약 (커버리지 지시 존재·보고 개수 상한 금지·보안 보고 표현)
```

- [ ] **Step 2: 실패하는 린트 검사를 추가한다**

`[27/28] security_verdict fail-closed 계약` 블록의 마지막 줄 뒤에 추가한다:

```bash

echo "[28/28] 리뷰 발견 단계 커버리지 계약"
# Sonnet 5는 "사소한 것은 생략" 류 지시를 이전 모델보다 충실히 따라 재현율이 떨어진다.
# 필터링은 오케스트레이터의 라우팅·게이트가 담당하므로 발견 단계는 커버리지가 목표다.
grep -qF '발견 단계의 목표는 커버리지다' agents/reviewer.md \
  || fail "커버리지 지시 누락: agents/reviewer.md"
grep -qF '3개 이내로 제한' agents/qa-manager.md \
  && fail "보고 개수 상한이 남아 있음: agents/qa-manager.md"
grep -qF '중복 지적 불필요' agents/reviewer.md \
  && fail "보안 항목을 보고하지 말라는 오독 여지가 남아 있음: agents/reviewer.md"
[ "$FAIL" -eq 0 ] && ok "커버리지 지시 + 개수 상한 제거 + 보안 보고 표현 확인"
```

- [ ] **Step 3: 린트를 실행해 실패를 확인한다**

```bash
bash scripts/lint-consistency.sh
```

기대: `[28/28] 리뷰 발견 단계 커버리지 계약` 아래에 FAIL 3줄.

- [ ] **Step 4: reviewer.md에 커버리지 지시를 추가한다**

`agents/reviewer.md`의 `## Part 2: 코드 품질 검증` 섹션에서 이 줄을 찾는다:

```markdown
AC 충족 여부는 재평가하지 않습니다 (Part 1에서 끝). 분류:
```

바로 앞에 다음 문단을 삽입한다 (빈 줄로 분리):

```markdown
**발견 단계의 목표는 커버리지다.** 확신이 서지 않거나 심각도가 낮다고 판단한 항목도 빠짐없이 보고합니다. 중요도나 확신도로 미리 거르지 않습니다 — 필터링은 오케스트레이터의 라우팅(`[동작결함]`/`[동작불변]`)과 게이트 판정이 담당합니다. 걸러질 지적을 올리는 편이 실제 결함을 조용히 놓치는 것보다 낫습니다. 확신이 낮은 항목은 심각도를 낮춰 분류하되 보고에서 빼지는 않습니다.

```

- [ ] **Step 5: reviewer.md의 보안 항목 표현을 고친다**

`agents/reviewer.md`의 `## 금지 사항` 섹션에서 이 줄을 찾는다:

```markdown
- 새 기능 제안 / 보안 감사(security-auditor와 병렬 실행되므로 중복 지적 불필요 — 발견하면 Critical로만 표기)
```

다음으로 교체한다:

```markdown
- 새 기능 제안 / 보안 감사를 목적으로 한 별도 탐색 (security-auditor가 병렬 수행 — 코드를 읽다 보안 결함을 발견하면 Critical로 보고하되, 감사 범위를 넓히지는 않습니다)
```

- [ ] **Step 6: qa-manager.md의 보고 개수 상한을 제거한다**

`agents/qa-manager.md:171`의 이 줄을 찾는다:

```markdown
항목이 없으면 이 섹션 생략. 가장 임팩트 있는 3개 이내로 제한한다.
```

다음으로 교체한다:

```markdown
항목이 없으면 이 섹션 생략.
```

- [ ] **Step 7: 린트와 훅 테스트를 실행해 통과를 확인한다**

```bash
bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh
```

기대: `ok: 커버리지 지시 + 개수 상한 제거 + 보안 보고 표현 확인`과 `정합성 린트 통과`.

- [ ] **Step 8: 커밋**

`Skill(skill: "oh-my-gx:gx-commit")`를 호출한다. 커밋 메시지 방향:

```
fix: 리뷰 발견 단계를 커버리지 우선으로 되돌린다
```

---

### Task 3: 헤드리스 조기 턴 종료 방지

**근거:** `gx-ralph-iterate/SKILL.md`의 철칙 2번은 "질문 금지"만 다룬다. 공식 가이드가 권하는 나머지 절반 — *"턴을 끝내기 전에 마지막 문단을 확인하라. 그것이 계획·분석·질문·아직 하지 않은 일에 대한 약속이면 지금 도구를 써서 그 일을 하라. 컨텍스트가 길어졌다는 이유로 멈추지 마라"* — 이 빠져 있다. 헤드리스 루프에서 조기 종료는 종료 계약 미출력(종료 코드 3)이거나 attempts만 소모하는 실패다.

**Files:**
- Modify: `scripts/lint-consistency.sh` (분모 28→29, 검사 `[29]` 추가)
- Modify: `.claude/skills/gx-ralph-iterate/SKILL.md` (`## 철칙 (Iron Law)` 섹션)

**Interfaces:**
- Consumes: 린트 분모 `28` (Task 2가 남긴 값)
- Produces: 린트 분모 `29`. 철칙 1~5번의 번호와 내용은 **변경하지 않는다** — 린트 `[11/29]`(gx-ralph 상태 계약)와 `[26/29]`(implement report 계약)가 이 파일의 기존 문구를 검사한다.

- [ ] **Step 1: 린트 분모를 28에서 29로 올리고 헤더에 항목을 추가한다**

```bash
sed -i 's|/28\]|/29]|g' scripts/lint-consistency.sh
```

헤더 주석에서 `# 28. 리뷰 발견 단계 커버리지 계약 ...` 줄 뒤에 추가한다:

```bash
# 29. 헤드리스 조기 종료 방지 철칙 (마지막 문단 점검·컨텍스트 사유 중단 금지)
```

- [ ] **Step 2: 실패하는 린트 검사를 추가한다**

`[28/29] 리뷰 발견 단계 커버리지 계약` 블록의 마지막 줄 뒤에 추가한다:

```bash

echo "[29/29] 헤드리스 조기 종료 방지 철칙"
# 헤드리스 반복에서 도구 호출 없이 의도만 말하고 턴을 끝내면 종료 계약 미출력(종료 코드 3)이거나
# attempts만 소모된다. 사람이 "계속하세요"라고 답할 수 없는 세션이므로 철칙으로 고정한다.
ITERATE_MD=.claude/skills/gx-ralph-iterate/SKILL.md
grep -qF '턴을 끝내기 전에 마지막 문단을 확인한다' "$ITERATE_MD" \
  || fail "마지막 문단 점검 철칙 누락: $ITERATE_MD"
grep -qF '컨텍스트가 길어졌다는 이유로 멈추지 않는다' "$ITERATE_MD" \
  || fail "컨텍스트 사유 중단 금지 문구 누락: $ITERATE_MD"
[ "$FAIL" -eq 0 ] && ok "헤드리스 조기 종료 방지 철칙 확인"
```

- [ ] **Step 3: 린트를 실행해 실패를 확인한다**

```bash
bash scripts/lint-consistency.sh
```

기대: `[29/29] 헤드리스 조기 종료 방지 철칙` 아래에 FAIL 2줄.

- [ ] **Step 4: 철칙 6번을 추가한다**

`.claude/skills/gx-ralph-iterate/SKILL.md`의 `## 철칙 (Iron Law)` 섹션에서 5번 항목을 찾는다:

```markdown
5. **종료 계약을 응답의 마지막 줄에 정확히 한 번** 출력한다. 지시 인용 등으로 계약 문자열을 본문 중간에 쓰지 않는다.
```

바로 뒤에 6번을 추가한다:

```markdown
6. **턴을 끝내기 전에 마지막 문단을 확인한다.** 그것이 계획·분석·다음 단계 목록이거나 아직 하지 않은 일에 대한 약속("이제 …하겠습니다", "다음으로 …")이면, 설명하지 말고 지금 도구를 호출해 그 일을 수행한다. 오류가 났으면 재시도하고, 빠진 정보는 직접 찾는다. **컨텍스트가 길어졌다는 이유로 멈추지 않는다.** 이 세션이 턴을 끝내는 유일한 방법은 5번의 종료 계약 출력이다.
```

- [ ] **Step 5: 린트와 훅 테스트를 실행해 통과를 확인한다**

```bash
bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh
```

기대: `ok: 헤드리스 조기 종료 방지 철칙 확인`과 `정합성 린트 통과`, 훅 테스트 통과.

- [ ] **Step 6: 기존 ralph 린트가 깨지지 않았는지 확인한다**

```bash
bash scripts/lint-consistency.sh 2>&1 | grep -E '^\[(11|26)/29\]' -A2
```

기대: `[11/29] gx-ralph 상태 계약 정합`과 `[26/29] implement report 계약` 모두 FAIL 없음.

- [ ] **Step 7: 커밋**

`Skill(skill: "oh-my-gx:gx-commit")`를 호출한다. 커밋 메시지 방향:

```
fix: 헤드리스 반복의 조기 턴 종료를 철칙으로 차단한다
```

---

## 마무리

- [ ] **CHANGELOG 갱신**

`CHANGELOG.md`에 세 변경을 한 항목으로 기록한다. 버전을 올릴지는 사용자에게 확인한다 — 올린다면 `.claude/rules/release.md`에 따라 `.claude-plugin/plugin.json`·`.claude-plugin/marketplace.json`·`.codex-plugin/plugin.json` 세 곳의 `version`을 함께 갱신해야 하고, 린트 `[1/29]`가 이를 검사한다.

- [ ] **PR 생성**

`Skill(skill: "oh-my-gx:gx-pull-request")`를 호출한다.

## 이 계획이 다루지 않는 것

- **refusal 폴백의 모델 축 (Spec 설계 B의 나머지 절반)** — Task 1은 security 경로에 재호출·중단 계층을 세우지만, 재호출을 **한 티어 위 모델로** 올리는 부분은 뺐다. 티어 축(`agentTiers`)이 있어야 "한 티어 위"가 정의되고, 그건 Codex 실측에 걸려 있다. 그때까지 재호출은 현행대로 같은 모델로 수행한다 — 형식 실패에는 유효하고, 모델이 거부한 경우에는 L2(중단·보고)로 수렴하므로 안전 측면의 손실은 없다.
- **모델 적응 규칙의 나머지 두 문단 (Spec 설계 D)** — 컨텍스트 예산 안심 문구와 경계 명시는 **오케스트레이터가 Fable일 때 나타나는 증상**에 대한 처방이다. Spec의 "증상 기반 도입" 원칙에 따라, `/model fable`로 실제 증상을 관찰한 뒤 나온 항목만 넣는다. Task 3의 자율성 철칙만 모델과 무관하게 지금 값이 있어 포함했다.
- **`agents/implementer.md`의 self-review** — Opus 5 가이드는 자기 검증 지시 제거를 권하지만 implementer는 `model: sonnet`이고 Sonnet 5 가이드에는 해당 항목이 없다. 현행 유지가 맞다.
- **effort 축** — Claude Code의 `Task` 파라미터에 `effort`가 없어 frontmatter 정적 지정만 가능하고, 그건 플러그인 사용자 전원에게 강제된다. 보류한다.
- **규범성 감축** — 705KB는 Opus 5에서 중립이다. Fable 채택이 확정된 뒤에 별도 브랜치로 다룬다.
- **Codex 호환** — 별도 계획 `2026-09-04-codex-compat-hardening.md`에서 다룬다.
