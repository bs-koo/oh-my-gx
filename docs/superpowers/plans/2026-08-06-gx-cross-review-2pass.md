# gx-cross-review 2패스 재설계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `gx-cross-review`를 2패스 구조로 개편하여, `ocr delegate`가 리뷰 대상과 규칙을 결정론적으로 확정하고 파일별 병렬 결함 리뷰(Pass 1)와 산출물 대조(Pass 2)를 분리한다.

**Architecture:** 외부 CLI `ocr`(alibaba/open-code-review)을 delegate 모드로만 호출한다 — OCR은 파일 선택과 규칙 해석만 하고 LLM을 호출하지 않으므로 API 키 설정이 불필요하다. Pass 1은 신규 `defect-reviewer` 에이전트를 파일당 하나씩 병렬 디스패치하고, Pass 2는 기존 advisor(codex/claude) 구조를 유지하되 입력을 파일 목록 기반으로 바꾼다. 산출물이 없으면 Pass 2만 생략되고 Pass 1은 그대로 동작한다.

**Tech Stack:** Markdown 스킬/에이전트 문서, Bash(`scripts/lint-consistency.sh`), JSON 설정. 컴파일 대상 코드는 없다.

## Global Constraints

- 이 저장소는 **빌드 툴체인이 없다.** `build.gradle`·`package.json`이 없으므로 gx-commit의 빌드 단계는 자동으로 건너뛴다.
- **검증 수단은 두 가지뿐이다**: `bash scripts/lint-consistency.sh`(정적 불변식, 현재 22개 검사 전부 통과) + `tests/golden-scenarios.md`(수동 행동 회귀).
- 모든 문서·주석·커밋 메시지는 **한국어**로 쓴다. 이모지를 쓰지 않는다. 사과 표현을 쓰지 않는다.
- 커밋 메시지 형식은 `{type}: 메시지`이며 **`Co-Authored-By` 트레일러를 절대 붙이지 않는다.**
- 작업 브랜치는 `feat/gx-cross-review-2pass`이며 이미 생성되어 있다. main에서 직접 작업하지 않는다.
- 심각도 어휘는 전 구간 **`Critical / High / Medium / Low` 4단계**다. 기존 `Critical / Warning / Info`는 폐기한다.
- `CHANGELOG.md` 버전 헤더는 반드시 **`## v{버전} ({YYYY-MM-DD})`** 형식이다. 린트 [1/23]이 `^## v\([0-9.]*\)` 정규식으로 버전을 뽑으므로 다른 형식은 검사를 실패시킨다.
- 에이전트 frontmatter의 `color`는 저장소에서 이미 쓰이는 값(`blue`·`cyan`·`green`·`magenta`·`orange`·`purple`·`red`·`white`·`yellow`)만 쓴다.
- 코멘트 `category`는 OCR 스키마와 동일한 8종이다: `bug`, `security`, `performance`, `maintainability`, `test`, `style`, `documentation`, `other`.
- 신규 파일 변수명: `DIFFS_DIR`(`${DEV_DIR}/diffs/`), `TARGETS_FILE`(`${DEV_DIR}/targets.md`), `RULES_FILE`(`${DEV_DIR}/rules.md`), `FILTERED_FILE`(`${DEV_DIR}/filtered-out.md`). 폐기 변수: `DIFF_FILE`, `SCOPE`.
- 스펙 원본: `docs/superpowers/specs/2026-08-06-gx-cross-review-2pass-design.md`. 판단이 갈리면 스펙을 따른다.

---

## File Structure

| 파일 | 책임 | 작업 |
|---|---|---|
| `agents/defect-reviewer.md` | 파일 1개의 결함을 OCR 규칙 + 프로젝트 컨벤션으로 검증. 읽기 전용 | 신규 (Task 1) |
| `.claude/config.json` | `contextLimits`에 `defect-reviewer` 입력 상한 등록 | 수정 (Task 1) |
| `scripts/lint-consistency.sh` | 정적 불변식. 검사 [23/23] 신설 + 전체 번호 갱신 | 수정 (Task 1·2·4) |
| `.claude/skills/gx-cross-review/SKILL.md` | 스킬 본문. Step 0·2·3A·3B·4·5 개편 | 수정 (Task 2·3·4·5) |
| `tests/golden-scenarios.md` | 행동 회귀 시나리오 S18~S23 | 수정 (Task 6) |
| `docs/guide.md` | 사용자 가이드의 gx-cross-review 절 | 수정 (Task 7) |
| `CHANGELOG.md`·`.claude-plugin/plugin.json`·`.claude-plugin/marketplace.json` | v1.22.0 릴리스 3중 일치 | 수정 (Task 7) |

`gx-dev`·`gx-tdd`의 phase 파일은 건드리지 않는다.

---

### Task 1: defect-reviewer 에이전트 신설

**Files:**
- Create: `agents/defect-reviewer.md`
- Modify: `.claude/config.json` (`contextLimits` 블록 끝)
- Modify: `scripts/lint-consistency.sh` (검사 번호 전체 + 새 검사 블록 추가)
- Test: `scripts/lint-consistency.sh` 실행

**Interfaces:**
- Produces: 에이전트 이름 `oh-my-gx:defect-reviewer`. 출력 말미에 `defect_verdict` YAML 블록(필드: `file`, `status`, `comments`, `by_severity`)을 낸다. Task 3이 이 이름으로 디스패치하고 이 블록을 파싱한다.
- Consumes: 없음 (첫 태스크)

- [ ] **Step 1: 린트에 새 불변식을 먼저 추가한다 (실패 확인용)**

`scripts/lint-consistency.sh` 맨 끝의 `echo` + 종료 처리 **직전**에 아래 블록을 삽입한다. 파일 마지막 3줄은 다음과 같이 생겼다 — 그 위에 넣는다.

```bash
echo
if [ "$FAIL" -ne 0 ]; then
```

삽입할 내용:

```bash
echo "[23/23] gx-cross-review 2패스 계약"
# defect_verdict 블록 producer 정의
grep -q "defect_verdict" agents/defect-reviewer.md \
  || fail "defect_verdict 블록 정의(producer) 누락: agents/defect-reviewer.md"
# contextLimits 등록
grep -q '"defect-reviewer"' .claude/config.json \
  || fail "contextLimits에 defect-reviewer 누락: .claude/config.json"
[ "$FAIL" -eq 0 ] && ok "defect-reviewer 계약 확인"
```

- [ ] **Step 2: 검사 번호를 22 → 23으로 일괄 갱신한다**

기존 22개 검사의 `[N/22]` 표기를 `[N/23]`으로 바꾼다.

```bash
sed -i 's|^echo "\[\([0-9]\+\)/22\]|echo "[\1/23]|' scripts/lint-consistency.sh
grep -c '/23\]' scripts/lint-consistency.sh
```

Expected: `23` (기존 22개 + 신규 1개)

- [ ] **Step 3: 린트를 실행해 실패를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: FAIL. 출력 말미에 아래 두 줄이 나온다.

```
  FAIL: defect_verdict 블록 정의(producer) 누락: agents/defect-reviewer.md
  FAIL: contextLimits에 defect-reviewer 누락: .claude/config.json
정합성 린트 실패 — 위 FAIL 항목을 수정하세요.
```

종료 코드는 1이다.

- [ ] **Step 4: 에이전트 파일을 작성한다**

`agents/defect-reviewer.md`를 아래 내용 그대로 만든다. `color`는 저장소에서 이미 쓰이는 값만 쓴다 — `cyan`이 4회, `blue`·`green`·`orange`·`purple`·`red`가 각 2회 쓰이므로 중복은 문제되지 않는다. 여기서는 1회만 쓰인 `yellow`를 쓴다. **검증되지 않은 색 이름(`teal` 등)을 쓰지 않는다.**

```markdown
---
name: defect-reviewer
description: |
  파일 1개의 결함만 검증하는 에이전트. OCR 규칙 체크리스트와 프로젝트 컨벤션을 기준으로 배정된 파일의 변경분만 리뷰한다. AC 충족·설계 범위는 평가하지 않는다 (gx-cross-review Pass 2 영역). gx-cross-review 전용이며 gx-dev·gx-tdd 파이프라인에서는 호출하지 않는다.

  <example>
  Context: gx-cross-review Pass 1에서 파일별 병렬 디스패치
  user: (오케스트레이터) PaymentService.java를 규칙 그룹 2 기준으로 리뷰해줘
  assistant: defect-reviewer가 diff 파일을 Read하여 Critical 1건(한도 검증 누락), Medium 2건을 보고하고 defect_verdict 블록을 출력
  </example>

  <example>
  Context: 다른 파일에서 문제를 발견
  user: (오케스트레이터) 이 파일 리뷰해줘
  assistant: defect-reviewer가 호출 대상 파일의 결함만 보고하고, 탐색 중 발견한 타 파일 문제는 보고하지 않음
  </example>
model: sonnet
color: yellow
tools:
  - Read
  - Glob
  - Grep
---

# defect-reviewer

당신은 **배정된 파일 1개**의 결함 검증 전담 에이전트입니다.

## 절대 규칙

1. **배정된 파일의 변경분만** 평가합니다.
2. **탐색 도구는 이해용입니다.** Read/Grep으로 다른 파일을 읽어 맥락을 파악해도 되지만, **코멘트는 배정된 파일에만** 답니다. 탐색 중 다른 파일에서 문제를 발견하면 무시합니다.
3. **precision > recall.** 오탐은 리뷰어 신뢰를 깎습니다. 확신이 서지 않으면 보고하지 않습니다.
4. **AC 충족·설계 범위를 평가하지 않습니다.** (gx-cross-review Pass 2 영역)

## 입력

- **대상 파일 경로**: 리뷰할 파일 1개
- **diff 파일 경로**: 해당 파일의 변경분 (직접 Read)
- **규칙 체크리스트**: OCR이 이 파일 유형에 매칭한 규칙 그룹
- **프로젝트 컨벤션**: 프로젝트 루트 CLAUDE.md의 아키텍처·패턴·컨벤션 (없으면 미전달)
- **요구사항 배경**: PRD 수용 기준 요약 (없으면 미전달)

## 보고하지 않는 것

- **삭제된 코드.** 참조 맥락일 뿐입니다.
- **변경되지 않은 코드.** 기존 결함은 이 리뷰의 범위가 아닙니다.
- **컴파일러·린터·포매터가 이미 잡는 것.** 문법 오류, 미사용 import, 들여쓰기.
- **근거 없는 스타일 취향.** 컨벤션 위반은 CLAUDE.md의 해당 규약을 인용해야 보고할 수 있습니다. 인용하지 못하면 취향이므로 보고하지 않습니다.
- **다른 파일의 문제.** 배정된 파일이 아니면 무시합니다.

## 작업 절차

1. diff 파일을 Read하여 변경분을 파악합니다.
2. 규칙 체크리스트의 각 항목을 변경분에 대조합니다.
3. 컨벤션이 전달됐으면 레이어 규약·네이밍 위반을 확인합니다.
4. 맥락이 불분명하면 Read/Grep으로 호출부·정의를 확인합니다. **추측으로 판단하지 않습니다.**
5. 확신이 서는 결함만 분류하여 보고합니다.

## 출력 형식

```
## 결함 리뷰: {파일 경로}

### Critical (N건)
- {파일}:{시작라인}-{끝라인} — [{category}] {문제}
  - 근거: {규칙 항목 또는 CLAUDE.md 규약 인용, 또는 코드 확인 결과}
  - 권고: {수정 방안}

### High (N건)
### Medium (N건)
### Low (N건)
```

`category`는 다음 8종 중 하나입니다: `bug`, `security`, `performance`, `maintainability`, `test`, `style`, `documentation`, `other`.

심각도 기준:

- **Critical**: 보안 취약점, 데이터 손실, 시스템 중단, 핵심 기능 실패
- **High**: 명백한 버그, 잘못된 분기, 누락된 검증
- **Medium**: 성능·유지보수성 문제, 엣지 케이스
- **Low**: 가독성, 비핵심 관행

### 기계 판정 블록 (필수)

위 출력의 **맨 마지막**에 아래 YAML 블록을 코드 펜스로 감싸 붙입니다. 오케스트레이터가 산문보다 이 블록을 우선 파싱합니다. 각 건수는 위 목록의 항목 수를 **다시 세어 일치**시킵니다.

```yaml
defect_verdict:
  file: src/main/java/com/example/PaymentService.java   # 배정받은 파일 경로
  status: reviewed                                       # reviewed | failed
  comments: 3                                            # 전체 코멘트 수
  by_severity: { critical: 1, high: 0, medium: 2, low: 0 }
```

diff 파일을 읽을 수 없거나 내용이 비어 리뷰가 불가능하면 `status: failed`로 보고하고 사유를 한 줄 덧붙입니다.

## 금지 사항

- 코드 직접 수정 (읽기 전용 에이전트입니다)
- AC 충족 여부 판정
- 설계 범위 이탈 판정
- 새 기능 제안

## Red Flags

다음 생각이 들면 STOP:
- "다른 파일에도 같은 문제가 있다" → 배정된 파일만 보고합니다
- "확실하진 않지만 일단 보고하자" → 규칙 3 위반. 보고하지 않습니다
- "이건 스타일이 좀 이상한데" → CLAUDE.md 규약을 인용할 수 없으면 보고하지 않습니다
```

- [ ] **Step 5: config.json에 contextLimits를 등록한다**

`.claude/config.json`의 `contextLimits` 객체에서 마지막 항목인 `"humanizer-naturalness"` 줄 뒤에 쉼표를 붙이고 아래를 추가한다.

```json
    "humanizer-naturalness": { "maxInputLines": 1200, "note": "윤문본 + 탐지 리포트" },
    "defect-reviewer": { "maxInputLines": 800, "note": "파일 1개 diff + 규칙 그룹 + 컨벤션 (파일당 호출이므로 작게 유지)" }
```

- [ ] **Step 6: JSON 문법을 검증한다**

Run: `node -e "JSON.parse(require('fs').readFileSync('.claude/config.json','utf8')); console.log('OK')"`

Expected: `OK`

node가 없으면 대신 `python -c "import json;json.load(open('.claude/config.json'));print('OK')"`를 쓴다.

- [ ] **Step 7: 린트를 실행해 통과를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: 마지막 두 줄이 아래와 같다.

```
  ok: defect-reviewer 계약 확인
정합성 린트 통과
```

종료 코드는 0이다.

- [ ] **Step 8: 커밋한다**

```bash
git add agents/defect-reviewer.md .claude/config.json scripts/lint-consistency.sh
git commit -m "$(cat <<'EOF'
feat: defect-reviewer 에이전트를 추가한다

- 파일 1개의 결함만 검증하는 읽기 전용 에이전트 신설
- 탐색 도구는 이해용이고 코멘트는 배정 파일에만 다는 규율 명시
- 컨벤션 위반은 CLAUDE.md 규약 인용을 필수로 하여 취향 지적 차단
- defect_verdict 기계 판정 블록 정의
- lint-consistency.sh에 [23/23] 검사 추가
EOF
)"
```

---

### Task 2: Step 0·2 개편 — ocr 확인과 대상·규칙 확보

**Files:**
- Modify: `.claude/skills/gx-cross-review/SKILL.md` (frontmatter `allowed-tools`, 공유 변수 섹션, Step 0, Step 2)
- Modify: `scripts/lint-consistency.sh` ([23/23] 블록에 검사 1종 추가)
- Test: `scripts/lint-consistency.sh` 실행

**Interfaces:**
- Consumes: 없음
- Produces: `${TARGETS_FILE}`(`${DEV_DIR}/targets.md`) — 리뷰 대상 파일 목록과 제외 사유. `${RULES_FILE}`(`${DEV_DIR}/rules.md`) — 규칙 그룹. Task 3이 둘 다 읽는다.

- [ ] **Step 1: 린트에 검사를 먼저 추가한다**

`scripts/lint-consistency.sh`의 `[23/23]` 블록에서 `[ "$FAIL" -eq 0 ] && ok` 줄 **앞**에 삽입한다.

```bash
# ocr 호출 권한
grep -q 'Bash(ocr \*)' .claude/skills/gx-cross-review/SKILL.md \
  || fail "allowed-tools에 Bash(ocr *) 누락: gx-cross-review/SKILL.md"
```

- [ ] **Step 2: 린트를 실행해 실패를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: FAIL — `allowed-tools에 Bash(ocr *) 누락: gx-cross-review/SKILL.md`

- [ ] **Step 3: frontmatter에 ocr 권한을 추가한다**

`SKILL.md` frontmatter의 `# codex 호출` 주석 블록 아래(`- Bash(codex *)` 다음 줄)에 추가한다.

```yaml
  # open-code-review 호출
  - Bash(ocr *)
```

- [ ] **Step 4: 공유 변수 섹션을 갱신한다**

`## 공유 변수` 목록에서 아래 두 줄을 **삭제**한다.

```
- `DIFF_FILE`: `${DEV_DIR}/diff.txt`. Step 2-2에서 갱신.
```

`SCOPE` 관련 기술도 함께 지운다. 그리고 `RAW_FILE` 줄 뒤에 아래를 추가한다.

```
- `DIFFS_DIR`: `${DEV_DIR}/diffs/`. 파일별 diff 저장 디렉토리. Step 3A-2에서 생성.
- `TARGETS_FILE`: `${DEV_DIR}/targets.md`. 병합된 리뷰 대상·제외 목록. Step 2-1 산출물.
- `RULES_FILE`: `${DEV_DIR}/rules.md`. 파일별 규칙 그룹. Step 2-2 산출물.
- `FILTERED_FILE`: `${DEV_DIR}/filtered-out.md`. 오탐 필터가 제거한 항목과 사유. Step 3A-4 산출물.
```

- [ ] **Step 5: Step 0에 ocr 존재 확인을 추가한다**

`### 0-3. 산출물 점검` 섹션 끝(references 점검 문단 뒤)에 아래를 추가한다.

````markdown
### 0-3.5. ocr 존재 확인

```bash
which ocr
```

실패하면 아래를 출력하고 **종료한다.** 자동 설치는 하지 않는다 (codex 선례 준수 — 사용자 환경 침해 방지).

```
open-code-review(ocr) CLI가 설치되어 있지 않습니다.

설치:
  npm install -g @alibaba-group/open-code-review

설치 후 /gx-cross-review를 다시 호출해주세요.
(delegate 모드로 사용하므로 별도 LLM 설정은 필요하지 않습니다.)
```

성공하면 `ocr --version` 결과를 `${OCR_VERSION}`에 담아 0-4 환경 보고에 한 줄로 표시한다.
````

`### 0-4. 환경 보고`의 예시 블록에 `- ocr: v{버전}` 줄을 `- DEV_DIR:` 다음에 추가한다.

- [ ] **Step 6: Step 2를 통째로 교체한다**

`## Step 2: 산출물 컨텍스트 빌더`부터 `### 2-3. 컨텍스트 통합` 끝까지를 아래로 교체한다.

````markdown
## Step 2: 리뷰 대상·규칙 확보

오케스트레이터가 직접 수행한다.

### 2-1. preview 2회 호출 후 병합

`ocr delegate preview --from/--to`(range 모드)는 **커밋된 변경만** 본다. 이 스킬은 `/gx-dev` 직후 `git add` 전 호출을 지원하므로 두 번 호출해 병합한다.

```bash
mkdir -p "${DEV_DIR}"
ocr delegate preview --from "${BASE_BRANCH}" --to HEAD > "${DEV_DIR}/preview-range.txt" 2>&1
ocr delegate preview > "${DEV_DIR}/preview-workspace.txt" 2>&1
```

두 출력을 병합하여 `${TARGETS_FILE}`에 기록한다.

- 리뷰 대상 목록은 **합집합**으로 병합하고 경로 중복을 제거한다. 같은 경로가 양쪽에 있으면 한 항목으로 합치고 상태는 **workspace 쪽 값**을 채택한다.
- 제외 목록도 합쳐 사유를 보존한다. 같은 경로가 한쪽에서 대상, 다른 쪽에서 제외로 나오면 **대상을 우선한다.**

> **preview의 역할은 파일 목록 확정에 한정한다.** diff 본문은 여기서 가져오지 않는다 (Step 3A-2에서 별도 생성). 두 모드의 diff를 각각 받아 합치면 같은 파일의 커밋분과 미커밋분이 분리되어 리뷰어가 변경 전체를 보지 못한다.

`${TARGETS_FILE}` 형식:

```markdown
# 리뷰 대상

| 경로 | 상태 | +/- |
|------|------|-----|
| src/main/java/PaymentService.java | modified | +42/-8 |

# 제외

| 경로 | 사유 |
|------|------|
| src/test/java/PaymentServiceTest.java | 테스트 파일 |
```

### 2-2. 규칙 확보

```bash
ocr delegate rule <대상 경로들...> > "${RULES_FILE}" 2>&1
```

파일이 많아 명령줄 길이가 문제되면 50개 단위로 나눠 호출한다. 이때 **단순히 이어붙이면 안 된다** — 각 호출이 `### Rule Group 1`부터 독립적으로 번호를 매기므로 번호가 중복되고 같은 그룹이 여러 배치에 중복 출력된다. 병합 규칙:

1. 배치별 출력에서 그룹을 파싱한다 (헤더의 출처·패턴, 규칙 본문, 적용 파일 목록).
2. **출처·패턴·본문 3개가 모두 같은 그룹을 하나로 합치고 적용 파일 목록을 합집합한다.**
3. 합친 결과에 `1`부터 다시 번호를 매겨 `${RULES_FILE}`에 기록한다.

### 2-3. 조기 종료

병합된 리뷰 대상이 0건이면 `"변경사항이 없습니다."`를 표시하고 종료한다.

### 2-4. 산출물 슬라이싱 (Pass 2 입력용)

Pass 2 advisor에 전달할 산출물을 우선순위대로 추린다.

| 순위 | 항목 | 추출 방법 |
|------|------|----------|
| 1 | PRD "수용 기준" | `prd.md`의 `### 수용 기준` 섹션. 없고 `ac.md`가 있으면 `## 요구사항 (AC)` 섹션 |
| 1 | 설계 "변경 범위" + "구현 순서" | `design.md`의 해당 섹션. 핵심 모드는 `summary.md`의 "변경 파일" 표 |
| 1 | 리뷰 대상 파일 목록 | `${TARGETS_FILE}` |
| 2 | trust-ledger 항목 목록 | `trust-ledger.md` 전체 |
| 2 | self-check 발견 사항 | `self-check.md` 전체 |
| 3 | codemap 핵심 파일 | `codemap.md`의 "핵심 파일" 섹션 |
| 4 | references 목록 | `references/` 파일명 + 첫 200자 요약 |

**컨텍스트 폭발 방지**: 합산이 60,000 토큰을 넘으면 4순위를 파일명만 남기고, 그래도 넘으면 3순위를 핵심 파일 5개로, 그래도 넘으면 2순위를 Critical 항목만으로 줄인다.
````

- [ ] **Step 7: 린트를 실행해 통과를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: `정합성 린트 통과`, 종료 코드 0

- [ ] **Step 8: 커밋한다**

```bash
git add .claude/skills/gx-cross-review/SKILL.md scripts/lint-consistency.sh
git commit -m "$(cat <<'EOF'
feat: gx-cross-review Step 0·2를 ocr delegate 기반으로 교체한다

- Step 0에 ocr 존재 확인 추가 (미설치 시 안내 후 종료, 자동 설치 금지)
- Step 2를 preview 2회 병합 + rule 확보로 교체하여 커버리지를 결정론적으로 확정
- rule 배치 호출 시 그룹 중복 병합 규칙 명시
- DIFF_FILE 폐기, DIFFS_DIR·TARGETS_FILE·RULES_FILE·FILTERED_FILE 도입
- allowed-tools에 Bash(ocr *) 추가
EOF
)"
```

---

### Task 3: Step 3A 신설 — Pass 1 파일별 결함 리뷰

**Files:**
- Modify: `.claude/skills/gx-cross-review/SKILL.md` (`## Step 3: advisor별 호출` 앞에 새 섹션 삽입)
- Test: `scripts/lint-consistency.sh` 실행

**Interfaces:**
- Consumes: `${TARGETS_FILE}`, `${RULES_FILE}` (Task 2 산출물). `oh-my-gx:defect-reviewer` 에이전트와 `defect_verdict` 블록 (Task 1 산출물).
- Produces: Pass 1 신규 위험 목록 (오케스트레이터 컨텍스트 보유). `${FILTERED_FILE}`. Task 4가 Pass 2 프롬프트에 중복 금지 항목으로 전달하고, Task 5가 "신규 위험" 섹션에 채운다.

- [ ] **Step 1: Step 3A 섹션을 삽입한다**

`## Step 3: advisor별 호출` 바로 앞에 아래를 삽입한다.

````markdown
## Step 3A: Pass 1 — 파일별 결함 리뷰

산출물 유무와 무관하게 **항상 수행한다.**

### 3A-1. 배분

- 원칙: **파일 1개당 `defect-reviewer` 1개.** 파일당 독립 컨텍스트를 보장하는 것이 이 패스의 존재 이유다.
- 동시 디스패치 상한: **5개.** 한 메시지에 최대 5개 Task를 발행하고, 완료되면 다음 묶음을 발행한다.
- 대상이 **15개를 초과**하면 확인한다.

```
AskUserQuestion(
  questions: [{
    question: "리뷰 대상이 N개 파일입니다. 어떻게 진행할까요?",
    header: "대상 규모",
    options: [
      { label: "전체 리뷰", description: "N개 파일 전부 리뷰 (에이전트 N회 디스패치)" },
      { label: "변경량 상위 15개", description: "증감 라인수 기준 상위 15개만 리뷰. 나머지는 커버리지에 '사용자 선택 제외'로 기록" },
      { label: "중단", description: "범위를 좁혀 다시 호출" }
    ],
    multiSelect: false
  }]
)
```

### 3A-2. 파일별 diff 생성

디스패치 **전에** 오케스트레이터가 대상 파일마다 diff를 파일로 만든다. `defect-reviewer`의 도구는 `Read, Glob, Grep`이라 Bash가 없어 스스로 git을 실행할 수 없다.

**파일이 range·workspace 어느 쪽에서 왔든 동일한 명령을 쓴다** — 커밋분과 미커밋분이 쪼개지면 리뷰어가 변경 전체를 보지 못한다.

```bash
mkdir -p "${DEV_DIR}/diffs"
MB=$(git merge-base HEAD "${BASE_BRANCH}")
# tracked: 커밋 + staged + unstaged를 한 번에 포함
git diff "${MB}" -- "<path>" > "${DEV_DIR}/diffs/<슬러그>.diff"
# untracked: 전체를 신규 코드로 간주
git diff --no-index /dev/null "<path>" > "${DEV_DIR}/diffs/<슬러그>.diff" 2>/dev/null
```

**슬러그 규칙**: 경로의 `/`를 `-`로 치환한다 (`src/main/App.java` → `src-main-App.java.diff`). `BRANCH_SLUG`와 동일한 치환 규칙이다.

생성 결과가 0줄인 파일은 대상에서 빼고 커버리지 `excluded`에 **`diff 없음`** 사유로 기록한다 (커밋 후 워킹 트리에서 되돌린 파일 등).

### 3A-3. 디스패치

각 `Task(subagent_type="oh-my-gx:defect-reviewer")` 프롬프트에 다음을 담는다.

```
대상 파일: {경로}
diff 파일 경로: {DEV_DIR}/diffs/{슬러그}.diff

규칙 체크리스트:
{RULES_FILE에서 이 파일이 속한 그룹의 본문}

프로젝트 컨벤션:
{프로젝트 루트 CLAUDE.md의 아키텍처·패턴·컨벤션 섹션. 없으면 이 항목 자체를 생략}

요구사항 배경:
{PRD 수용 기준 요약. 산출물이 없으면 이 항목 자체를 생략}

한국어로 출력한다.
```

### 3A-4. 오탐 필터

수집된 코멘트가 **4건 이상**이면 반증 기반 필터를 1회 적용한다 (3건 이하는 비용 대비 이득이 없어 생략).

판정 원칙은 **비대칭**이다.

- **제거**: diff만으로 핵심 주장이 **틀렸다고 입증되는** 코멘트
- **통과**: 확인 불가한 코멘트. 리뷰어는 Read/Grep으로 필터가 못 보는 맥락을 확인했을 수 있다
- **통과**: 의심스럽지만 반증하지 못하는 코멘트

필터는 오케스트레이터가 직접 수행한다 (에이전트 추가 없음). 제거된 항목은 **`${FILTERED_FILE}`**에 사유와 함께 보존한다. `${RAW_FILE}`은 Step 3a-2의 codex 호출이 `>`로 덮어쓰므로 재사용하지 않는다.

### 3A-5. 실패 처리

- 일부 실패: 성공분만 사용하고 커버리지 `failed`에 파일명을 기록한다. 결과 보고에 부분 결과임을 명시한다.
- **전부 실패**: 실패로 보고하고 중단한다. 부분 성공과 전면 실패를 구분한다.
````

- [ ] **Step 2: 기존 Step 3 제목을 Pass 2로 바꾼다**

`## Step 3: advisor별 호출`을 아래로 바꾼다.

```markdown
## Step 3B: Pass 2 — 산출물 대조 (advisor별 호출)
```

같은 섹션 안의 `### 3-A. codex 경로`·`### 3-B. claude 경로`는 각각 `### 3B-1. codex 경로`·`### 3B-2. claude 경로`로 바꾼다. 하위 항목 번호(`3a-1`, `3b-1` 등)도 충돌하지 않도록 `3B-1-1` 형태로 맞춘다.

- [ ] **Step 3: 린트를 실행해 통과를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: `정합성 린트 통과`, 종료 코드 0

- [ ] **Step 4: 커밋한다**

```bash
git add .claude/skills/gx-cross-review/SKILL.md
git commit -m "$(cat <<'EOF'
feat: gx-cross-review에 Pass 1 파일별 결함 리뷰를 신설한다

- 파일당 defect-reviewer 1개, 동시 5개, 15개 초과 시 확인
- 오케스트레이터가 파일별 diff를 미리 생성하여 경로로 전달
- 커밋분과 미커밋분을 한 명령으로 합쳐 변경 전체를 보장
- 반증 기반 오탐 필터를 4건 이상일 때 적용, 제거 항목은 filtered-out.md에 보존
- 기존 Step 3을 Step 3B(Pass 2)로 재명명
EOF
)"
```

---

### Task 4: Step 3B 입력 변경과 폐기 정리

**Files:**
- Modify: `.claude/skills/gx-cross-review/SKILL.md` (Step 0-0 ARGS 표, Step 3B 프롬프트, fallback 섹션 삭제, 다른 스킬과의 관계)
- Modify: `scripts/lint-consistency.sh` ([23/23] 블록에 검사 1종 추가)
- Test: `scripts/lint-consistency.sh` 실행

**Interfaces:**
- Consumes: Pass 1 신규 위험 목록 (Task 3), `${TARGETS_FILE}` (Task 2)
- Produces: Pass 2 advisor 응답. Task 5가 정규화한다.

- [ ] **Step 1: 린트에 검사를 먼저 추가한다**

`[23/23]` 블록의 `[ "$FAIL" -eq 0 ] && ok` 줄 앞에 삽입한다.

```bash
# 폐기 변수·플래그 잔존 금지
grep -q 'DIFF_FILE' .claude/skills/gx-cross-review/SKILL.md \
  && fail "폐기된 DIFF_FILE 잔존: gx-cross-review/SKILL.md"
grep -q -- '--scope' .claude/skills/gx-cross-review/SKILL.md \
  && fail "폐기된 --scope 잔존: gx-cross-review/SKILL.md"
```

- [ ] **Step 2: 린트를 실행해 실패를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: FAIL — `폐기된 DIFF_FILE 잔존` 및 `폐기된 --scope 잔존` 두 줄

- [ ] **Step 3: ARGS 표에서 `--scope`를 제거한다**

`### 0-0. ARGS 파싱`의 옵션 표에서 `--scope` 행을 삭제한다. 바로 아래 "알 수 없는 옵션" 안내 문구의 지원 옵션 목록도 아래로 바꾼다.

```
"인식하지 못한 옵션을 무시했습니다: <token>. 지원 옵션: --advisor, --dev-dir, --base"
```

- [ ] **Step 4: Pass 2 프롬프트의 diff 참조를 교체한다**

codex prompt(`<task>` 블록)의 아래 두 줄을

```
diff 파일: ${DIFF_FILE}
이 파일을 Read하여 변경사항을 확인한다.
```

다음으로 바꾼다.

```
대상 파일 목록: ${TARGETS_FILE}
이 파일을 Read하여 변경 범위를 확인한다. 특정 파일의 세부 내용이 필요하면 해당 파일을 직접 Read한다.
```

claude prompt(qa-manager·security-auditor 양쪽)의 `- diff 파일 경로: ${DIFF_FILE}` 줄도 아래로 바꾼다.

```
- 대상 파일 목록: ${TARGETS_FILE} (세부 내용이 필요하면 해당 파일을 직접 Read)
```

- [ ] **Step 5: Pass 1 결과 중복 금지를 프롬프트에 추가한다**

codex prompt의 `<grounding_rules>` 블록에 아래 한 줄을 추가한다.

```
- Pass 1이 이미 보고한 신규 위험 항목은 다시 보고하지 않는다 (중복 금지).
```

`<artifacts>` 블록 끝에 아래 섹션을 추가한다.

```
### Pass 1 신규 위험 (이미 보고됨, 중복 금지)
{Pass 1 확정 목록}
```

claude prompt의 두 에이전트 미션에도 각각 아래 항목을 추가한다.

```
5. Pass 1 중복 금지: Pass 1이 이미 보고한 신규 위험은 다시 보고하지 않는다.
   Pass 1 신규 위험: {Pass 1 확정 목록}
```

- [ ] **Step 6: Pass 2 생략 조건을 명시한다**

`## Step 3B` 섹션 맨 앞에 아래를 추가한다.

```markdown
**산출물(prd/ac/design)이 셋 다 없으면 이 Step 전체를 생략한다.** Step 4에서 AC 매트릭스·설계 범위 이탈·references 위반 섹션을 빼고 Pass 1 결과만으로 보고한다. 이는 오류가 아니라 정상 분기다.
```

- [ ] **Step 7: fallback 섹션을 삭제한다**

`## 산출물 부재 fallback` 섹션 전체(F-1·F-2·F-3 포함)를 삭제한다. 산출물 부재가 정상 분기가 되었으므로 진행 여부를 묻는 AskUserQuestion도 함께 사라진다.

`### 0-3. 산출물 점검`의 판정 규칙에서 fallback 언급을 아래로 바꾼다.

```
- prd, ac, design 셋 다 없으면 → **Pass 2를 생략하고 Pass 1만 수행한다** (정상 분기).
- 셋 중 하나라도 있으면 → 두 패스 모두 수행. **AC 명세는 prd.md 우선, 없으면 ac.md(core)를 사용한다.**
```

`### 0-4. 환경 보고`의 "fallback 모드" 예시 문구도 아래로 바꾼다.

```
- 산출물: prd.md/ac.md/design.md 모두 없음 → Pass 1만 수행
```

- [ ] **Step 8: 다른 스킬과의 관계 항목을 갱신한다**

문서 맨 끝 `## 다른 스킬과의 관계`에서 `/codex:review` 줄 뒤에 추가한다.

```markdown
- `ocr`(open-code-review): Pass 1의 리뷰 대상·규칙 확보에 delegate 모드로 사용한다. 필수 의존이며 미설치 시 Step 0에서 종료한다.
```

- [ ] **Step 9: 린트를 실행해 통과를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: `정합성 린트 통과`, 종료 코드 0

`폐기된 DIFF_FILE 잔존` 또는 `폐기된 --scope 잔존`이 남으면 해당 문자열이 아직 문서에 있는 것이다. 아래로 위치를 찾는다.

```bash
grep -n 'DIFF_FILE\|--scope' .claude/skills/gx-cross-review/SKILL.md
```

- [ ] **Step 10: 커밋한다**

```bash
git add .claude/skills/gx-cross-review/SKILL.md scripts/lint-consistency.sh
git commit -m "$(cat <<'EOF'
feat: Pass 2 입력을 파일 목록 기반으로 바꾸고 폐기 항목을 정리한다

- advisor 프롬프트의 diff 참조를 TARGETS_FILE로 교체
- Pass 1 신규 위험을 중복 금지 항목으로 전달
- 산출물 부재를 정상 분기로 전환하고 fallback 섹션 삭제
- DIFF_FILE·--scope 폐기 및 잔존 금지 린트 추가
EOF
)"
```

---

### Task 5: Step 4·5 — 통합 정규화와 심각도 4단계 통일

**Files:**
- Modify: `.claude/skills/gx-cross-review/SKILL.md` (Step 3B 출력 계약, Step 4, Step 5, 진행 상태 추적)
- Test: `scripts/lint-consistency.sh` 실행 + 수동 grep 검증

**Interfaces:**
- Consumes: Pass 1 결과 (Task 3), Pass 2 advisor 응답 (Task 4)
- Produces: `${RESULT_FILE}`(`${DEV_DIR}/cross-review.md`) 최종 산출물

- [ ] **Step 1: advisor 출력 계약의 심각도를 4단계로 바꾼다**

codex prompt의 `<structured_output_contract>` 안 `## 신규 위험` 블록을 아래로 바꾼다.

```
## 신규 위험
trust-ledger.md와 Pass 1 목록에 없는 신규 항목만.
- [Critical/High/Medium/Low] [category] 항목 설명
  - 위치: 파일:라인
  - 근거: ...
  - 권고: ...

category는 다음 8종 중 하나: bug, security, performance, maintainability, test, style, documentation, other
```

- [ ] **Step 2: Step 4 표준 포맷에 커버리지 섹션을 추가한다**

`### 4-1. 표준 포맷`의 마크다운 예시에서 `- 실행 시각:` 줄 다음에 아래를 삽입한다.

````markdown
## 커버리지

- 리뷰: 12개 파일
- 제외: 5개 (테스트 3, 생성 코드 1, binary 1)
- 실패: 0개
- 오탐 필터: 15건 중 3건 제거

제외 사유 범주는 다섯 가지다. 앞의 셋은 OCR preview가, 뒤의 둘은 이 스킬이 판정한다.

| 사유 | 판정 주체 |
|------|----------|
| 테스트 / 생성 코드 / binary / 대형 diff | `ocr delegate preview` |
| `사용자 선택 제외` | Step 3A-1의 "변경량 상위 15개" 선택 |
| `diff 없음` | Step 3A-2의 diff 생성 결과가 0줄 |
````

- [ ] **Step 3: 신규 위험 섹션의 심각도를 4단계로 바꾼다**

`### 4-1. 표준 포맷` 예시의 `## 신규 위험` 블록을 아래로 바꾼다.

```markdown
## 신규 위험

(trust-ledger와 Pass 1 중복을 제외한 항목만)

### Critical
- [bug] PaymentService.kt:55 — 한도 초과 검증 누락
  - 근거: ...
  - 권고: ...

### High
### Medium
### Low
```

- [ ] **Step 4: 사용자 요약에 커버리지를 추가한다**

`### 4-3. 사용자 요약`의 예시 블록을 아래로 바꾼다.

```
## Cross-Review 완료

- advisor: codex
- 커버리지: 12개 파일 리뷰 / 5개 제외 / 0개 실패
- AC 충족: [Must] 4/5, [Should] 2/3
- 설계 범위 이탈: 1건
- 신규 위험: Critical 1, High 2, Medium 3, Low 0
- references 위반: 없음

전문: ${RESULT_FILE}     (= ${DEV_DIR}/cross-review.md)
원시 응답: ${RAW_FILE}    (= ${DEV_DIR}/cross-review.raw.md)
제외된 지적: ${FILTERED_FILE} (= ${DEV_DIR}/filtered-out.md)
```

Pass 2를 생략한 실행에서는 `advisor` 줄을 `- advisor: (Pass 2 생략 — 산출물 없음)`으로 쓰고 AC·설계 범위·references 줄을 빼라는 단서를 예시 아래에 한 문장으로 덧붙인다.

- [ ] **Step 5: Step 5의 심각도 표현을 바꾼다**

`### 5-1. 처리 대상 식별`의 항목 목록에서 `- 신규 위험 (Critical/Warning/Info).`를 아래로 바꾼다.

```
- 신규 위험 (Critical/High/Medium/Low).
```

`### 5-3. 분기 처리`의 "일부 수정" AskUserQuestion 예시 문구에서 `[Critical]`은 그대로 두되, 설명에 4단계 어휘를 쓴다. 문서 전체에서 `Warning`·`Info`를 심각도 의미로 쓰는 잔존 표현을 찾아 바꾼다.

```bash
grep -n 'Warning\|Info' .claude/skills/gx-cross-review/SKILL.md
```

self-check의 "Warning/Info" 언급은 **다른 산출물의 등급이므로 그대로 둔다.** 바꾸는 대상은 cross-review 자신의 신규 위험 등급뿐이다.

- [ ] **Step 6: 진행 상태 추적에 커버리지를 추가한다**

`## 진행 상태 추적`의 YAML 예시에서 `findings` 블록을 아래로 바꾼다.

```yaml
findings:
  ac_total: 5
  ac_met: 4
  range_violation: 1
  critical: 1
  high: 2
  medium: 3
  low: 0
  references_violation: 0
coverage:
  reviewed: 12
  excluded: 5
  failed: 0
  filtered_out: 3
```

- [ ] **Step 7: 잔존 표현을 검증한다**

Run:

```bash
grep -n 'Warning\|Info' .claude/skills/gx-cross-review/SKILL.md
```

Expected: self-check 산출물을 가리키는 줄만 남는다 (예: `self-check.md의 Warning/Info는 중복 보고하지 않는다`). cross-review 자신의 신규 위험 등급으로 쓰인 `Warning`·`Info`는 0건이어야 한다.

- [ ] **Step 8: 린트를 실행해 통과를 확인한다**

Run: `bash scripts/lint-consistency.sh`

Expected: `정합성 린트 통과`, 종료 코드 0

- [ ] **Step 9: 커밋한다**

```bash
git add .claude/skills/gx-cross-review/SKILL.md
git commit -m "$(cat <<'EOF'
feat: 결과 정규화에 커버리지를 추가하고 심각도를 4단계로 통일한다

- Critical/Warning/Info 3단계를 Critical/High/Medium/Low 4단계로 전면 교체
- advisor 출력 계약과 Step 5 문구를 4단계로 갱신
- 커버리지 섹션 추가 (리뷰·제외·실패·필터 건수와 제외 사유 범주)
- 진행 상태 추적에 coverage 필드 추가
EOF
)"
```

---

### Task 6: 골든 시나리오 S18~S23 추가

**Files:**
- Modify: `tests/golden-scenarios.md` (시나리오 표 끝 + 기록 문구)
- Test: 문서 자체 점검 (자동 실행 없음)

**Interfaces:**
- Consumes: Task 1~5가 구현한 동작 전부
- Produces: 릴리스 전 수동 점검 체크리스트

- [ ] **Step 1: 시나리오 표에 6행을 추가한다**

`tests/golden-scenarios.md`의 시나리오 표 마지막 행(S17) 뒤에 아래를 추가한다.

```markdown
| S18 ★ | `ocr` 미설치 (PATH에서 제거) | `/gx-cross-review` | 설치 안내(`npm install -g @alibaba-group/open-code-review`) 후 종료. 자동 설치 시도 0회 | gx-cross-review Step 0-3.5 |
| S19 | 산출물(prd/ac/design) 없는 저장소 + 변경 3파일 | `/gx-cross-review` | Pass 1만 동작. AC 매트릭스·설계 범위 이탈·references 위반 섹션 미출력. **진행 여부 질문 없음**(구 fallback AskUserQuestion 제거 확인) | gx-cross-review Step 0-3 판정 → Step 3B 생략 |
| S20 | 커밋된 변경 1파일 + `git add` 전 미커밋 변경 1파일 + untracked 신규 1파일 | `/gx-cross-review` | 세 파일 모두 리뷰 대상. 커밋 파일은 range preview에서만, 나머지는 workspace preview에서만 나오므로 **2회 병합이 동작해야 통과** | gx-cross-review Step 2-1 |
| S21 | 변경 20개 파일 | `/gx-cross-review` | 15개 초과 확인 질문 1회. "전체 리뷰" 선택 시 defect-reviewer가 동시 5개씩 나뉘어 디스패치됨 | gx-cross-review Step 3A-1 |
| S22 | 산출물 있는 저장소 | `/gx-cross-review` | 커버리지 섹션 출력 + Pass 1 신규 위험이 Pass 2 advisor 프롬프트에 "중복 금지" 항목으로 전달됨 | gx-cross-review Step 3B |
| S23 | 프로젝트 `CLAUDE.md`에 레이어·네이밍 규약이 있고 이를 위반한 변경 | `/gx-cross-review` | 컨벤션 위반이 Pass 1에서 보고되고 **근거로 `CLAUDE.md` 규약이 인용됨**. 인용 없는 스타일 지적은 보고되지 않음 | defect-reviewer 보고 제외 규칙 |
```

- [ ] **Step 2: 기록 문구의 총 개수를 갱신한다**

문서 맨 끝 `## 기록` 절의 아래 문장에서

```
점검 결과는 릴리스 PR 본문에 `골든 시나리오: N/17 통과 (미통과: ID)` 형식으로 기록한다.
```

`N/17`을 `N/23`으로 바꾼다.

- [ ] **Step 3: 표 형식이 깨지지 않았는지 확인한다**

Run:

```bash
grep -c '^| S' tests/golden-scenarios.md
```

Expected: `23`

- [ ] **Step 4: 커밋한다**

```bash
git add tests/golden-scenarios.md
git commit -m "$(cat <<'EOF'
test: 2패스 재설계 골든 시나리오 S18~S23을 추가한다

- S18 ocr 미설치 시 안내 후 종료
- S19 산출물 부재 시 Pass 1만 동작하고 진행 여부 질문 없음
- S20 커밋분·미커밋분·untracked 3종을 preview 2회 병합으로 모두 포함
- S21 15개 초과 확인과 동시 5개 배분
- S22 커버리지 출력과 Pass 1 중복 금지 전달
- S23 컨벤션 위반의 CLAUDE.md 근거 인용 강제
EOF
)"
```

---

### Task 7: 문서 갱신과 v1.22.0 릴리스 준비

**Files:**
- Modify: `docs/guide.md` (gx-cross-review 절)
- Modify: `CHANGELOG.md` (최상단에 새 섹션)
- Modify: `.claude-plugin/plugin.json` (`version`)
- Modify: `.claude-plugin/marketplace.json` (`plugins[0].version`)
- Test: `scripts/lint-consistency.sh` 실행 (검사 [1/23] 버전 3중 일치)

**Interfaces:**
- Consumes: Task 1~6의 모든 변경
- Produces: 릴리스 가능한 상태. main 머지 시 `.github/workflows/release.yml`이 태그와 GitHub Release를 자동 생성한다.

- [ ] **Step 1: 현재 버전과 guide.md의 해당 절을 확인한다**

Run:

```bash
grep -n '"version"' .claude-plugin/plugin.json
grep -n 'version' .claude-plugin/marketplace.json | head -3
grep -n 'cross-review' docs/guide.md | head -10
```

Expected: plugin.json과 marketplace.json 모두 `1.21.1`. guide.md에서 gx-cross-review를 설명하는 줄 번호가 나온다.

`marketplace.json`의 버전은 `plugins` 배열 안 객체의 `"version": "1.21.1"` 필드다 (최상위가 아니다).

- [ ] **Step 2: guide.md의 gx-cross-review 절에 ocr 요구사항을 명시한다**

해당 절 도입부에 아래 문단을 추가한다. 주변 문체(존댓말/평서문)는 기존 절을 따른다.

```markdown
`/gx-cross-review`는 [open-code-review](https://github.com/alibaba/open-code-review)(`ocr`) CLI를 필요로 합니다.

    npm install -g @alibaba-group/open-code-review

delegate 모드로만 사용하므로 별도 LLM 엔드포인트나 API 키 설정은 필요하지 않습니다. `ocr`은 리뷰할 파일과 파일별 규칙을 결정하는 역할만 하고, 실제 리뷰는 Claude가 수행합니다.

리뷰는 두 단계로 진행됩니다. 먼저 파일별로 결함을 찾고(Pass 1), 그다음 PRD·설계서 대비 약속이 지켜졌는지 검증합니다(Pass 2). PRD나 설계서가 없는 저장소에서도 Pass 1은 그대로 동작합니다.
```

- [ ] **Step 3: CHANGELOG.md에 v1.22.0 섹션을 추가한다**

`# Changelog` 줄 바로 다음, 기존 `## v1.21.1` 섹션 **앞**에 삽입한다.

**헤더 형식이 중요하다.** 린트 [1/23]이 `sed -n 's/^## v\([0-9.]*\).*/\1/p'`로 첫 버전을 뽑으므로 반드시 `## v1.22.0 (날짜)` 형식이어야 한다. `## [1.22.0] - 날짜` 같은 형식은 버전 추출에 실패해 검사가 FAIL한다.

기존 섹션들은 "요약 한 문장 + 빈 줄 + 평문 불릿 목록" 구조다. 하위 제목(`### 추가` 등)을 쓰지 않는다.

```markdown
## v1.22.0 (2026-08-06)

gx-cross-review 2패스 재설계 — open-code-review(`ocr`) delegate 연동으로 리뷰 커버리지를 결정론적으로 확정.

- Pass 1(파일별 결함) / Pass 2(산출물 대조) 2패스 분리 — advisor 선택은 Pass 2에만 적용
- `ocr delegate preview`·`rule`로 리뷰 대상과 파일별 규칙 확보, 제외 파일은 사유와 함께 보고 (`ocr` 필수 의존 — 미설치 시 설치 안내 후 종료)
- `defect-reviewer` 에이전트 추가 — 파일당 1개씩 최대 5개 병렬, 프로젝트 CLAUDE.md 컨벤션 참조, 컨벤션 위반은 규약 인용 필수
- 반증 기반 오탐 필터 — diff로 반증되는 지적만 제거, 제거 내역은 `filtered-out.md`에 보존
- 결과에 커버리지 섹션 추가 (리뷰·제외·실패 건수와 제외 사유 범주)
- 신규 위험 심각도를 Critical/Warning/Info → Critical/High/Medium/Low 4단계로 통일 (advisor 계약·Step 5 문구 동기)
- 산출물(PRD·설계) 부재를 정상 분기로 전환 — Pass 2만 생략, 진행 여부 질문 제거
- diff 500줄 초과 시 요약 전환 경로와 `--scope` 플래그 제거 (파일 단위 분해로 대체), `DIFF_FILE` 폐기
- lint [23/23] 2패스 계약 불변식 추가 (defect_verdict producer·ocr 권한·폐기 항목 잔존 금지)
```

- [ ] **Step 4: 버전을 3곳 모두 갱신한다**

`.claude-plugin/plugin.json`의 `"version": "1.21.1"`을 `"version": "1.22.0"`으로 바꾼다.

`.claude-plugin/marketplace.json`의 `plugins[0].version`도 `1.22.0`으로 바꾼다.

- [ ] **Step 5: JSON 문법과 버전 일치를 검증한다**

Run:

```bash
node -e "JSON.parse(require('fs').readFileSync('.claude-plugin/plugin.json','utf8'));JSON.parse(require('fs').readFileSync('.claude-plugin/marketplace.json','utf8'));console.log('JSON OK')"
bash scripts/lint-consistency.sh
```

Expected: `JSON OK`, 그리고 린트 출력의 `[1/23] 버전 3중 일치`가 `ok`로 통과. 마지막 줄은 `정합성 린트 통과`.

버전 불일치가 있으면 `[1/23]`에서 FAIL이 난다. 세 곳(`plugin.json`, `marketplace.json`, `CHANGELOG.md`)을 다시 확인한다.

- [ ] **Step 6: 커밋한다**

```bash
git add docs/guide.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "$(cat <<'EOF'
docs: v1.22.0 릴리스 문서를 갱신한다

- guide.md에 ocr 설치 요구사항과 2패스 구조 설명 추가
- CHANGELOG에 v1.22.0 섹션 작성
- plugin.json·marketplace.json 버전을 1.22.0으로 갱신
EOF
)"
```

- [ ] **Step 7: PR을 갱신한다**

```bash
git push
```

기존 PR #75의 본문에 구현 완료 사실을 반영한다. 본문 갱신은 `oh-my-gx:gx-pull-request` 스킬을 호출하여 수행한다 (직접 `gh pr edit`을 실행하지 않는다 — 스킬 라우팅 규칙).

---

## Self-Review

**스펙 커버리지 대조**

| 스펙 섹션 | 구현 태스크 |
|---|---|
| 4.2 Step 0 ocr 확인 | Task 2 Step 5 |
| 4.3 Step 2 preview 2회 병합 | Task 2 Step 6 |
| 4.3 rule 배치 그룹 병합 | Task 2 Step 6 |
| 4.4 3A-1 배분·상한 | Task 3 Step 1 |
| 4.4 3A-2 diff 파일 사전 생성 | Task 3 Step 1 |
| 4.4 3A-3 출력·verdict | Task 1 Step 4 |
| 4.4 3A-4 오탐 필터·FILTERED_FILE | Task 3 Step 1 |
| 4.5 defect-reviewer 에이전트 | Task 1 Step 4 |
| 4.5 contextLimits | Task 1 Step 5 |
| 4.6 Pass 2 입력 변경·DIFF_FILE 폐기 | Task 4 Step 4 |
| 4.6 Pass 1 중복 금지 | Task 4 Step 5 |
| 4.6 산출물 부재 시 Pass 2 생략 | Task 4 Step 6 |
| 4.7 커버리지 섹션·제외 사유 범주 | Task 5 Step 2 |
| 4.7 심각도 4단계 통일 | Task 5 Step 1·3·5 |
| 4.8 진행 상태 coverage | Task 5 Step 6 |
| 5장 fallback 삭제 | Task 4 Step 7 |
| 6장 골든 시나리오 S18~S23 | Task 6 |
| 6장 정적 불변식 3종 | Task 1 Step 1, Task 2 Step 1, Task 4 Step 1 |
| 8장 영향 범위 전체 | Task 1~7 |

누락 없음.

**이름 일관성**

- 에이전트 이름은 전 구간 `defect-reviewer`(디스패치 시 `oh-my-gx:defect-reviewer`).
- verdict 블록은 전 구간 `defect_verdict`. Task 1이 정의하고 Task 1 Step 1의 린트가 검사한다.
- 파일 변수는 전 구간 `DIFFS_DIR`·`TARGETS_FILE`·`RULES_FILE`·`FILTERED_FILE`. Task 2 Step 4가 정의하고 Task 3~5가 사용한다.
- 심각도는 전 구간 `Critical/High/Medium/Low`.
- 린트 검사 번호는 전 구간 `[N/23]`. Task 1 Step 2가 일괄 갱신한다.

**린트 순서 주의**

Task 4 Step 1이 추가하는 `DIFF_FILE`·`--scope` 잔존 금지 검사는 **Task 4 Step 3~7이 완료되어야 통과한다.** Task 4 안에서 red → green이 닫히므로 다른 태스크를 막지 않는다. 태스크를 건너뛰거나 순서를 바꾸면 린트가 실패한 채로 남으니 순서대로 진행한다.
