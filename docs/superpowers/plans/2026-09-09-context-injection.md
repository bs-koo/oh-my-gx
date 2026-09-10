# 도메인 컨텍스트 4요소 주입 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-context가 받아낸 README 핵심(배경·안 하면·사용자/규모·성공 기준)과 status.md 미반영 항목을 DOMAIN_CONTEXT에 실어 product-owner에 주입하고, PRD가 미반영 항목과 겹치는 요구사항은 새 FR을 만들지 않고 FR ID를 인용하게 한다. gx-dev·gx-tdd 양쪽 파이프라인에 같이 적용한다.

**Architecture:** phase-setup 3.1 "도메인 컨텍스트 탐색"이 glossary·architecture에 README 핵심·status.md ⬜ 행을 더해 4요소로 DOMAIN_CONTEXT를 구성한다(우선순위 용어 > README 핵심 > 미반영 > 아키텍처, `contextLimits` 초과 시 뒤에서부터 생략). phase-requirements의 product-owner 프롬프트에 4요소 전달과 FR 인용 규칙을, phase-design의 architect 프롬프트에 빠져 있던 도메인 컨텍스트 항목(용어·아키텍처만)을 명시한다. phase-complete Step 3은 인용된 FR ID로 status.md 행을 찾는다. 린트 `[36]`이 tdd/dev 양쪽의 setup 4요소·requirements FR 인용·design 전달을 검사한다.

**Tech Stack:** Markdown (스킬·phase 문서), Bash (린트)

**Spec:** `docs/specs/2026-09-09-superpowers-gap-design.md` — D3, D5 순서

## Global Constraints

- **선행 조건**: `2026-09-09-tdd-rulings.md`가 main에 머지되어 있어야 한다 — `.claude-plugin/plugin.json` version `1.29.0`, `grep -c '/35\]' scripts/lint-consistency.sh`가 0보다 크다.
- **언어**: 문서·커밋 메시지 모두 한국어. 이모지 사용 금지.
- **브랜치**: `main`/`master`/`develop`에서 커밋 불가 (훅 G1). 작업 시작 전 `feat/context-injection` 브랜치를 생성한다.
- **커밋**: 메시지는 `feat: …`/`docs: …` 한 줄 제목. 트레일러를 **붙이지 않는다**. 서브에이전트는 직접 `git commit`을 허용한다 (이전 계획과 같은 ruling). grep 패턴 인자에 `git commit` 문자열을 넣지 않는다.
- **검증**: 모든 태스크는 `bash scripts/lint-consistency.sh`와 `bash scripts/hook-tests.sh`가 둘 다 통과한 상태로 끝난다.
- **바이트 예산**: `[32]` — gx-tdd SKILL.md ≤ 63,000B, phase-setup.md ≤ 22,000B (LF 기준). phase-setup은 현재 약 20,950B라 여유 1,000B, SKILL.md는 Task 3에서 약 130B만 더한다. 초과하면 같은 절의 문장을 줄여 상쇄한다 — 예산을 다시 올리지 않는다.
- **린트 번호 체계**: 현재 `[N/35]`. Task 5가 검사 1개를 추가하며 분모를 36으로 올린다. `.claude/`·`README.md`의 인용도 함께 치환한다 (`[31]`이 검사). `docs/`·`CHANGELOG.md`는 치환하지 않는다.
- **린트가 고정하는 문구**: `[32]`의 phase-setup 포인터 4건(`Read("setup-resume.md")`·`ARGS[0]이 있고 `--resume`이 없으면`·`Read("setup-work.md")`·`계획이 있으나 작업 ID가 지정되지 않은 경우`), `[12]`·`[13]` CORE 계약, `[16]` phase-complete context 커밋 예외 문구. 지우거나 바꾸지 않는다.
- **쌍둥이 동기**: gx-tdd와 gx-dev의 phase-setup 3.1·phase-requirements·phase-design은 같은 변경을 받는다. 한쪽만 고치고 끝내지 않는다 (`references/maintenance-notes.md`의 쌍둥이 원칙).
- **외과적 변경**: 지시된 블록만 고친다.

---

### Task 1: phase-setup 3.1의 도메인 컨텍스트를 4요소로 넓힌다 (tdd·dev)

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` — `### 3.1 병렬 수집` 4번 항목의 두 불릿
- Modify: `.claude/skills/gx-dev/phases/phase-setup.md` — 같은 위치의 같은 두 불릿

**Interfaces:**
- Consumes: 없음
- Produces: DOMAIN_CONTEXT 4요소 명칭 `용어`·`README 핵심`·`미반영 항목`·`아키텍처` (Task 2·3·5가 인용·검사)

- [ ] **Step 1: gx-tdd phase-setup의 두 불릿을 교체한다**

현재 (4번 항목 안):

```
   - 매칭되면 해당 도메인의 `glossary.md`, `architecture.md`를 Read하여 `DOMAIN_CONTEXT`에 저장한다.
```

새 텍스트:

```
   - 매칭되면 해당 도메인의 네 파일을 Read하여 `DOMAIN_CONTEXT`를 **4요소**로 구성한다 (우선순위 순 — `contextLimits` 초과 시 뒤에서부터 요약·생략):
     1. **용어**: `glossary.md` 전체
     2. **README 핵심**: `README.md`의 `## 배경`·`## 안 하면 어떻게 되는가`·`## 사용자와 규모`·`## 성공 기준` 네 절 (없는 절은 건너뛴다)
     3. **미반영 항목**: `status.md`에서 상태 열이 `⬜`인 행 전체 (FR ID·설명·AC 열 포함. 0건이면 "미반영 없음")
     4. **아키텍처**: `architecture.md` 전체
```

현재:

```
   - `DOMAIN_CONTEXT`는 이후 agent 프롬프트에 "도메인 컨텍스트"로 포함한다.
```

새 텍스트:

```
   - `DOMAIN_CONTEXT`는 이후 agent 프롬프트에 "도메인 컨텍스트"로 포함한다 — product-owner는 4요소 전부, architect·design-critic·test-architect는 용어·아키텍처만 (SKILL.md Context Slicing 표).
```

- [ ] **Step 2: gx-dev phase-setup에 같은 교체를 한다**

`.claude/skills/gx-dev/phases/phase-setup.md`의 같은 두 불릿(228~232행 부근, 안내 문구는 `/gx-context`로 되어 있다)을 Step 1과 **같은 새 텍스트**로 바꾼다. 안내 문구 불릿은 건드리지 않는다.

- [ ] **Step 3: 검증**

Run: `for f in .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md; do SEC=$(awk '/도메인 컨텍스트 탐색/{f=1} /외부 규격 참조 탐색/{f=0} f' "$f"); for s in 'README.md' 'status.md' '미반영' '우선순위' 'glossary.md' 'architecture.md' '4요소'; do printf '%s' "$SEC" | grep -qF "$s" || echo "MISSING($f): $s"; done; done; tr -d '\r' < .claude/skills/gx-tdd/phases/phase-setup.md | wc -c; bash scripts/lint-consistency.sh`
Expected: `MISSING` 없음, 22,000 이하, 35/35 통과.

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md
git commit -F - <<'MSG'
feat: 도메인 컨텍스트를 용어·README 핵심·미반영 항목·아키텍처 4요소로 구성한다
MSG
```

---

### Task 2: product-owner·architect 프롬프트에 도메인 컨텍스트 전달 규칙을 넣는다 (tdd·dev)

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-requirements.md` — 핵심 모드 분기 첫 불릿, `**Step 1**` product-owner 프롬프트 목록
- Modify: `.claude/skills/gx-dev/phases/phase-requirements.md` — `Task(subagent_type="oh-my-gx:product-owner")` 프롬프트 목록
- Modify: `.claude/skills/gx-tdd/phases/phase-design.md`, `.claude/skills/gx-dev/phases/phase-design.md` — `Task(subagent_type="oh-my-gx:architect")` 프롬프트 목록

**Interfaces:**
- Consumes: Task 1의 4요소
- Produces: 문구 `FR ID를 인용` (Task 4·5가 인용·검사), 인용 형식 `FR-N (status.md 미반영)`

- [ ] **Step 1: gx-tdd phase-requirements**

핵심 모드 분기의 `- ARGS[0] + 코드 맵 + DOMAIN_CONTEXT(있으면)를 기반으로 `${PROJECT_ROOT}/${DEV_DIR}/ac.md`를 작성한다.`를 `- ARGS[0] + 코드 맵 + DOMAIN_CONTEXT(있으면 — 미반영 항목과 겹치는 AC는 그 FR ID를 인용한다)를 기반으로 `${PROJECT_ROOT}/${DEV_DIR}/ac.md`를 작성한다.`로 바꾼다.

`**Step 1**` 목록의 `- 프로젝트 루트 경로` 불릿 바로 뒤에 추가한다:

```markdown
- 도메인 컨텍스트 (DOMAIN_CONTEXT가 있으면 4요소 전부 — 용어·README 핵심·미반영 항목·아키텍처). **미반영 항목과 겹치는 요구사항은 새 FR을 만들지 않고 그 FR ID를 인용**한다 (`FR-7 (status.md 미반영)` 형식으로 요구사항 제목 끝에 표기). README 성공 기준의 수치는 해당 AC의 Then에 검증값으로 반영한다
```

- [ ] **Step 2: gx-dev phase-requirements**

`Task(subagent_type="oh-my-gx:product-owner")` 목록의 `- 프로젝트 루트 경로` 불릿 바로 뒤에 Step 1과 **같은 불릿**을 추가한다 (gx-dev의 AC는 G-W-T 강제가 아니므로 마지막 문장은 `README 성공 기준의 수치는 해당 AC의 검증 조건에 반영한다`로 바꾼다).

- [ ] **Step 3: phase-design (tdd·dev)**

두 파일의 `Task(subagent_type="oh-my-gx:architect")` 목록에서 `- 프로젝트 루트 경로 (agent가 코드 탐색 시 사용)` 불릿 바로 뒤에 추가한다:

```markdown
- 도메인 컨텍스트 (DOMAIN_CONTEXT가 있으면 용어·아키텍처만): 기존 용어를 그대로 쓰고, `architecture.md`의 레이어·의존 규칙과 다른 설계는 "기존 구조와의 차이" 절에 명시할 것
```

- [ ] **Step 4: 검증**

Run: `for f in .claude/skills/gx-tdd/phases/phase-requirements.md .claude/skills/gx-dev/phases/phase-requirements.md; do grep -qF 'FR ID를 인용' "$f" || echo "MISSING($f): FR ID를 인용"; grep -qF 'status.md 미반영' "$f" || echo "MISSING($f): 인용 형식"; done; for f in .claude/skills/gx-tdd/phases/phase-design.md .claude/skills/gx-dev/phases/phase-design.md; do grep -qF '도메인 컨텍스트 (DOMAIN_CONTEXT가 있으면 용어·아키텍처만)' "$f" || echo "MISSING($f): architect 전달"; done; bash scripts/lint-consistency.sh`
Expected: `MISSING` 없음, 35/35 통과 (`[13]` core 분기 문구는 앞부분이 그대로다).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-requirements.md .claude/skills/gx-dev/phases/phase-requirements.md .claude/skills/gx-tdd/phases/phase-design.md .claude/skills/gx-dev/phases/phase-design.md
git commit -F - <<'MSG'
feat: PRD 작성에 도메인 컨텍스트 4요소를 주입하고 미반영 FR은 ID를 인용한다
MSG
```

---

### Task 3: SKILL.md Context Slicing과 gx-context 안내를 맞춘다

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` — Context Slicing 표 product-owner (PRD 작성) 행, architect 행
- Modify: `.claude/skills/gx-dev/SKILL.md:388`, `:529`, `:531`
- Modify: `.claude/skills/gx-context/SKILL.md` — B-6의 `- 사용자의 답변을 과도하게 다듬지 않는다. 핵심만 정리.` 뒤

**Interfaces:**
- Consumes: Task 1·2의 4요소·인용 규칙
- Produces: 없음

- [ ] **Step 1: gx-tdd SKILL.md**

product-owner (PRD 작성) 행의 `DOMAIN_CONTEXT(있으면)`를 `DOMAIN_CONTEXT(있으면 — 용어·README 핵심·미반영·아키텍처 4요소. 미반영과 겹치면 FR ID 인용)`로, architect 행의 `DOMAIN_CONTEXT(있으면)`를 `DOMAIN_CONTEXT(있으면 — 용어·아키텍처만)`로 바꾼다.

- [ ] **Step 2: gx-dev SKILL.md**

388행의 `로드된 도메인 용어(glossary)와 아키텍처 정보. 매칭되지 않으면 빈 상태.`를 `로드된 4요소 — 용어(glossary)·README 핵심(배경·안 하면·사용자/규모·성공 기준)·status.md 미반영 항목·아키텍처. 매칭되지 않으면 빈 상태.`로 바꾼다.

529행의 `+ DOMAIN_CONTEXT (있으면)`를 `+ DOMAIN_CONTEXT (있으면 — 4요소 전부. 미반영과 겹치면 FR ID 인용)`로, 531행의 `+ DOMAIN_CONTEXT (있으면)`를 `+ DOMAIN_CONTEXT (있으면 — 용어·아키텍처만)`로 바꾼다.

- [ ] **Step 3: gx-context SKILL.md**

B-6의 `- 사용자의 답변을 과도하게 다듬지 않는다. 핵심만 정리.` 불릿 뒤에 추가한다:

```markdown
- `배경`·`안 하면 어떻게 되는가`·`사용자와 규모`·`성공 기준` 네 절은 /gx-dev·/gx-tdd가 PRD 작성 시 product-owner에 주입한다. 수치를 남길수록 AC의 검증값이 구체적이 된다.
```

- [ ] **Step 4: 검증**

Run: `grep -c '4요소' .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md; grep -c 'product-owner에 주입' .claude/skills/gx-context/SKILL.md; tr -d '\r' < .claude/skills/gx-tdd/SKILL.md | wc -c; bash scripts/lint-consistency.sh`
Expected: tdd 1, dev 2, gx-context 1, 63,000 이하, 35/35 통과.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md .claude/skills/gx-context/SKILL.md
git commit -F - <<'MSG'
docs: Context Slicing 표와 gx-context 안내에 4요소 주입을 반영한다
MSG
```

---

### Task 4: phase-complete Step 3이 인용된 FR ID로 status.md 행을 찾는다 (tdd·dev)

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md:157`
- Modify: `.claude/skills/gx-dev/phases/phase-complete.md:122`

**Interfaces:**
- Consumes: Task 2의 인용 형식 `FR-N (status.md 미반영)`
- Produces: 없음

- [ ] **Step 1: 두 파일의 항목 3을 교체한다**

현재 (두 파일 동일):

```
3. 통과한 AC와 일치하는 행의 상태를 `⬜`→`✅`로, PR 열에 생성된 PR 링크를 기입한다.
```

새 텍스트 (두 파일 동일):

```
3. 통과한 AC와 일치하는 행의 상태를 `⬜`→`✅`로, PR 열에 생성된 PR 링크를 기입한다. PRD가 `FR-N (status.md 미반영)` 형식으로 FR ID를 인용한 AC는 그 FR 행을 대상으로 한다 (행의 AC 열이 비어 있어도 매칭되며, AC 열에 이번 AC ID를 기입한다).
```

- [ ] **Step 2: 검증**

Run: `grep -c 'status.md 미반영' .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-dev/phases/phase-complete.md; bash scripts/lint-consistency.sh`
Expected: 각 `1`, 35/35 통과 (`[16]`의 context 커밋 예외 문구 유지).

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-dev/phases/phase-complete.md
git commit -F - <<'MSG'
feat: status.md 갱신이 PRD가 인용한 FR ID로 행을 찾는다
MSG
```

---

### Task 5: 린트 [36]·골든 S43·v1.30.0 릴리스

**Files:**
- Modify: `scripts/lint-consistency.sh` — 헤더 목록, `[35/35]` 블록 뒤에 새 블록, 분모 35→36 전역 치환
- Modify: `[N/35]`를 인용하는 `.claude/`·`README.md` 파일 전부
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md` — `**review 진입 '변경 없음' 판정**` 항목 앞에 항목 추가
- Modify: `tests/golden-scenarios.md` — S43 행, `N/42` → `N/43`
- Modify: `CHANGELOG.md` — v1.30.0 절
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` — `1.29.0` → `1.30.0`

**Interfaces:**
- Consumes: Task 1~4의 문자열
- Produces: 린트 `[36/36] 도메인 컨텍스트 주입 계약`

- [ ] **Step 1: 새 검사를 `[35/35]` 블록 뒤(`if [ "$FAIL" -ne 0 ]` 앞)에 추가한다 (분모는 아직 35)**

```bash
echo "[36/35] 도메인 컨텍스트 주입 계약"
# 설계: docs/specs/2026-09-09-superpowers-gap-design.md D3 — tdd/dev 쌍둥이를 함께 검사한다
for f in .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md; do
  SEC=$(awk '/도메인 컨텍스트 탐색/{f=1} /외부 규격 참조 탐색/{f=0} f' "$f")
  [ -n "$SEC" ] || fail "도메인 컨텍스트 탐색 절 누락: $f"
  for s in 'README.md' 'status.md' '미반영' '우선순위' '4요소'; do
    printf '%s' "$SEC" | grep -qF "$s" || fail "도메인 컨텍스트 구성 요소($s) 누락: $f"
  done
done
for f in .claude/skills/gx-tdd/phases/phase-requirements.md .claude/skills/gx-dev/phases/phase-requirements.md; do
  grep -qF 'FR ID를 인용' "$f" || fail "미반영 항목 FR 인용 지시 누락: $f"
done
for f in .claude/skills/gx-tdd/phases/phase-design.md .claude/skills/gx-dev/phases/phase-design.md; do
  grep -qF '도메인 컨텍스트 (DOMAIN_CONTEXT가 있으면 용어·아키텍처만)' "$f" || fail "architect 도메인 컨텍스트 전달 누락: $f"
done
for f in .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-dev/phases/phase-complete.md; do
  grep -qF 'status.md 미반영' "$f" || fail "인용 FR 행 매칭 규칙 누락: $f"
done
[ "$FAIL" -eq 0 ] && ok "setup 4요소·requirements FR 인용·design 전달·complete 행 매칭 (tdd/dev) 확인"
```

스크립트 헤더의 검사 항목 주석 목록 `# 35. …` 아래에 추가한다:

```
# 36. 도메인 컨텍스트 주입 계약 (setup 4요소·requirements FR 인용·design 전달·complete 행 매칭 — tdd/dev 쌍둥이)
```

- [ ] **Step 2: 분모를 36으로 올린다**

```bash
sed -i 's|/35\]|/36]|g' scripts/lint-consistency.sh
grep -rlE '\[[0-9]+/35\]' .claude README.md --include=*.md --exclude-dir=worktrees | xargs -r sed -i 's|/35\]|/36]|g'
grep -rnE '\[[0-9]+/35\]' .claude README.md scripts --include=*.md --include=*.sh | grep -v worktrees
```
Expected: 마지막 grep 출력 없음.

- [ ] **Step 3: 유지보수 노트 항목**

`- **review 진입 '변경 없음' 판정**: …` 항목 **바로 앞**에 추가한다 (분모는 Step 2에서 이미 36이다):

```markdown
- **도메인 컨텍스트 4요소**(용어·README 핵심·미반영 항목·아키텍처 + 우선순위): gx-tdd/gx-dev phase-setup 3.1이 쌍둥이 producer, phase-requirements(product-owner — 4요소 전부 + FR 인용)·phase-design(architect — 용어·아키텍처만)·phase-complete Step 3(인용 FR 행 매칭)이 쌍둥이 consumer. 각 SKILL.md Context Slicing 표는 파생 사본. 린트 [36/36]이 8파일을 검사한다.
```

- [ ] **Step 4: 변이 시험 (RED)**

Run: `sed -i 's|3. \*\*미반영 항목\*\*: `status.md`|3. **미반영 항목**: `progress.md`|' .claude/skills/gx-dev/phases/phase-setup.md && bash scripts/lint-consistency.sh; echo "exit=$?"; git checkout -- .claude/skills/gx-dev/phases/phase-setup.md`
Expected: `도메인 컨텍스트 구성 요소(status.md) 누락: .claude/skills/gx-dev/phases/phase-setup.md`로 FAIL, exit 1 (gx-tdd 쪽만 고치고 dev를 빠뜨리는 회귀를 잡는다). 복원.

- [ ] **Step 5: 골든 시나리오 행을 추가한다**

S42 행 아래에 추가하고, 기록 절의 `N/42`를 `N/43`으로 바꾼다.

```markdown
| S43 ★ | `context/충전/`이 있고 README `## 성공 기준`에 "1회 한도 100,000원", status.md에 `FR-3 \| 1회 충전 한도 검증 \| - \| ⬜ \|` 행이 있는 저장소 | `/gx-tdd 포인트 충전 한도 검증 TDD로 구현해줘` | product-owner 프롬프트에 README 핵심 네 절과 status.md ⬜ 행이 실린다. PRD 요구사항 제목에 `FR-3 (status.md 미반영)`이 붙고 새 FR 번호가 생기지 않는다. AC의 Then에 `100,000`이 검증값으로 들어간다. phase-complete Step 3이 FR-3 행을 ✅로 바꾸고 AC 열을 채운다 | phase-setup 3.1 4요소 + phase-requirements FR 인용 + 린트 [36/36] |
```

- [ ] **Step 6: CHANGELOG와 버전**

CHANGELOG 상단에 추가한다:

```markdown
## v1.30.0 (2026-09-09)

gx-context가 받아낸 도메인 지식이 PRD에 닿게 한다. 그동안 DOMAIN_CONTEXT는 용어와 아키텍처만 실었고, 정량화 수칙으로 애써 받아낸 README의 문제·성공 기준·사용자/규모와 status.md의 미반영 항목은 product-owner가 보지 못했다. 설계: `docs/specs/2026-09-09-superpowers-gap-design.md` D3.

- **변경 — DOMAIN_CONTEXT 4요소**: 용어 > README 핵심(배경·안 하면·사용자/규모·성공 기준) > status.md 미반영 항목 > 아키텍처. `contextLimits` 초과 시 뒤에서부터 생략한다. gx-tdd·gx-dev phase-setup 3.1 쌍둥이 동기
- **변경 — PRD의 FR 인용**: 미반영 항목과 겹치는 요구사항은 새 FR을 만들지 않고 `FR-N (status.md 미반영)`으로 인용한다. 성공 기준 수치는 AC 검증값에 반영한다. phase-complete Step 3은 인용된 FR 행을 갱신한다
- **수정 — architect 프롬프트**: SKILL.md 표에는 있었지만 phase-design 프롬프트 목록에 빠져 있던 도메인 컨텍스트 항목(용어·아키텍처만)을 명시했다 (tdd·dev)
- **검증 — 린트 [36] 주입 계약 (8파일)**, 골든 S43
```

```bash
sed -i 's|"version": "1.29.0"|"version": "1.30.0"|' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
```
Expected: 세 파일 모두 `1.30.0`.

- [ ] **Step 7: 검증 (GREEN)**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 36/36 통과, 훅 테스트 통과.

- [ ] **Step 8: 커밋**

```bash
git add scripts/lint-consistency.sh .claude README.md tests/golden-scenarios.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json
git commit -F - <<'MSG'
feat: 린트 [36] 도메인 컨텍스트 주입 계약과 v1.30.0 릴리스 준비
MSG
```

---

## 완료 기준

- 린트 36/36·훅 테스트 통과. `[32]` 예산(SKILL.md 63,000B·phase-setup 22,000B) 이내.
- 골든 S43을 실제로 한 번 돌려 PRD에 `FR-3 (status.md 미반영)` 인용과 Then의 성공 기준 수치를 눈으로 확인한다 (PR 체크박스).
- 후속: D4(`2026-09-09-behavior-tests.md`).
