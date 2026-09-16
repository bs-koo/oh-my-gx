# 핵심 스킬 신뢰성 보강 통합 릴리스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A~D 분기의 결과를 하나의 검증 가능한 `1.33.0` 릴리스로 정리하고 Claude Code·Codex 배포 경로를 함께 확인한다.

**Architecture:** A와 B를 각각 리뷰·병합한 뒤 C와 D를 순서대로 병합한다. 통합 브랜치는 기능을 다시 구현하지 않고 골든 시나리오, 버전, 변경이력, 전체 회귀와 실제 smoke 증거만 다룬다. 배포 manifest 세 곳과 marketplace를 한 커밋에서 같은 버전으로 올린다.

**Tech Stack:** Markdown, JSON manifests, Bash/Python test runners, Claude Code/Codex smoke contracts

**Spec:** `docs/superpowers/specs/2026-09-15-core-skills-hardening-design.md`

## Global Constraints

- 선행 PR 병합 순서: A 요구사항 원장과 B 부트스트랩 병렬 → C 질문 계약 → D 지시문 모듈화.
- 작업 브랜치: `release/core-skills-hardening`, 최신 `main`에서 생성한다.
- 통합 브랜치에서 A~D의 동작 문구를 다시 편집하지 않는다. 실패하면 소유 분기로 돌려 수정한다.
- 릴리스 버전은 `1.33.0`이다.
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`의 버전을 일치시킨다.
- 실제 Codex smoke를 실행하지 못하면 상태를 `미실행`으로 유지하고 로컬 unittest 결과로 대체하지 않는다.

---

### Task 1: 병합 후 계약 충돌을 검사한다

**Files:**
- Modify: `tests/golden-scenarios.md`

**Interfaces:**
- Consumes: A~D가 추가한 context/pipeline/question/layout 테스트
- Produces: 골든 S45~S46

- [ ] **Step 1: 네 분기의 테스트 파일과 참조 파일이 모두 존재하는지 확인한다**

Run: `for f in tests/test_codex_skill_context.py tests/test_codex_skill_pipeline.py tests/test_codex_skill_questions.py tests/test_codex_skill_layout.py .claude/skills/gx-context/modes/from-document.md .claude/skills/gx-dev/references/intent-routing.md .claude/skills/gx-tdd/references/intent-routing.md docs/reports/2026-09-15-context-requirement-ledger-validation.md docs/reports/2026-09-15-pipeline-bootstrap-validation.md docs/reports/2026-09-15-codex-question-contract-validation.md docs/reports/2026-09-15-skill-instruction-layout-validation.md; do test -f "$f" || echo "MISSING: $f"; done`

Expected: 출력 없음.

세 스킬의 SVN 식별 문구가 합쳐진 상태도 확인한다.

Run: `for f in .claude/skills/gx-context/SKILL.md .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do for s in 'svn info --show-item url' 'branches/<name>' 'tags/<name>' 'REPOSITORY_ID' 'basename(PROJECT_ROOT)'; do grep -qF "$s" "$f" || echo "MISSING($f): $s"; done; done`

Expected: 출력 없음.

- [ ] **Step 2: 기존 자동 검사를 먼저 실행한다**

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v && python scripts/sync-codex-resources.py --check && bash scripts/lint-consistency.sh`

Expected: 모든 unittest OK, sync check 성공, lint 36/36 통과.

- [ ] **Step 3: 골든 시나리오 S45와 S46을 추가한다**

S44 다음에 다음 두 행을 넣고 기록 절의 총 시나리오 수를 46으로 갱신한다.

```markdown
| S45 ★ | Git 저장소의 `src/service/`에서 명령을 시작하고 루트에 `.claude/config.json`, `context/주문/`이 있음 | `/gx-tdd 주문 검증 --phase design` | PROJECT_ROOT는 `git rev-parse --show-toplevel` 절대경로다. `[setup, design]`을 실행하고 루트 `.dev`의 PRD가 없을 때 requirements를 먼저 실행한다. 하위 `src/service/.dev`나 config를 만들지 않는다 | gx-tdd Step -1 + 부분 phase 결정표 |
| S46 ★ | Codex 기본 모드, gx-context 문서 분석에서 문제·규모 질문이 필요함 | `/gx-context 주문 --from requirements/order.md` | request_user_input 호출마다 질문 3개 이하, 질문별 선택지 3개 이하, stable snake_case id가 있고 명시적 Other option은 없다. 실제 Other 답변은 같은 id로 decisions.md에 기록된다 | codex-runtime 질문 변환 + smoke Q2 |
```

- [ ] **Step 4: 골든 시나리오 문서 정합을 확인한다**

Run: `rg -n 'S44|S45|S46|N/46' tests/golden-scenarios.md`

Expected: S44~S46 각 1건과 `N/46` 기록 규칙 1건.

- [ ] **Step 5: 커밋한다**

```bash
git add tests/golden-scenarios.md
git commit -m "test: 핵심 스킬 종단 골든 시나리오를 추가한다"
```

---

### Task 2: 1.33.0 버전과 변경이력을 반영한다

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: A~D 완료 상태
- Produces: 네 파일의 버전 `1.33.0`

- [ ] **Step 1: 세 JSON manifest의 version을 1.33.0으로 바꾼다**

```json
"version": "1.33.0"
```

marketplace에 plugin version이 둘 이상 있으면 oh-my-gx 항목의 version만 바꾼다.

- [ ] **Step 2: CHANGELOG 맨 위에 릴리스 절을 추가한다**

```markdown
## v1.33.0 (2026-09-15)

### Added
- gx-context `--from`이 추출 요구사항을 status.md 원장에 안정적인 FR/NFR ID로 저장한다.
- context sync가 Git·SVN·PR cursor를 기록해 고정 조회 범위 밖 변경을 놓치지 않는다.
- 핵심 스킬의 context, pipeline, question, layout 계약을 Windows·Linux Codex unittest로 검사한다.

### Changed
- gx-dev·gx-tdd의 requirements/design 부분 phase가 setup을 선행하고 VCS 작업 루트 절대경로를 사용한다.
- SVN 저장소 ID와 Claude Code·Codex 질문 개수·Other 처리 규칙을 세 스킬에서 통일한다.
- gx-context mode와 gx-dev·gx-tdd 실행 계약을 조건부 참조 파일로 분리한다.
```

- [ ] **Step 3: 버전 정합 검사를 실행한다**

Run: `bash scripts/lint-consistency.sh`

Expected: `[1/36]`에서 네 버전이 `1.33.0`으로 일치하고 전체 lint 통과.

- [ ] **Step 4: 커밋한다**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json CHANGELOG.md
git commit -m "chore: 1.33.0 릴리스 버전을 반영한다"
```

---

### Task 3: 전체 자동 검증을 실행한다

**Files:**
- Modify: 없음

**Interfaces:**
- Consumes: 1.33.0 후보 트리
- Produces: PR 본문에 기록할 검증 결과

- [ ] **Step 1: Codex 리소스와 전체 unittest를 검사한다**

Run: `python scripts/sync-codex-resources.py --check`

Expected: exit 0, 출력 없음.

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`

Expected: 모든 테스트 OK, skipped/error/failure 0건.

- [ ] **Step 2: 셸 계약 검사를 실행한다**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh && bash scripts/test-gx-ralph.sh && bash scripts/test-behavior-tests.sh`

Expected: lint 36/36, hook tests 성공, Ralph runner tests 성공, behavior mock 성공.

- [ ] **Step 3: 문서와 whitespace를 검사한다**

Run: `git diff --check main...HEAD && git status --short`

Expected: diff 오류 없음. status는 깨끗하거나 의도한 검증 보고서만 표시된다.

- [ ] **Step 4: 테스트 실패가 있으면 소유 분기로 되돌린다**

- context ledger/sync 실패: A 분기에서 수정 후 새 PR.
- phase/root/SVN 실패: B 분기에서 수정 후 새 PR.
- 질문 schema/smoke 실패: C 분기에서 수정 후 새 PR.
- Read 포인터/행 상한/기존 lint 실패: D 분기에서 수정 후 새 PR.

수정 PR이 병합된 뒤 최신 main을 release 브랜치에 병합하고 Step 1부터 다시 실행한다.

---

### Task 4: 실제 Codex 소비 프로젝트 smoke를 실행한다

**Files:**
- Modify: `tests/codex-smoke.md`
- Create: `docs/reports/2026-09-15-core-skills-codex-validation.md`

**Interfaces:**
- Consumes: 깨끗하게 설치한 1.33.0 후보 plugin cache
- Produces: Q2·S45·S46 실제 세션 증거

- [ ] **Step 1: 임시 소비 프로젝트를 준비한다**

Windows PowerShell:

```powershell
$caseRoot = Join-Path $env:TEMP 'gx-core-skills-1330'
New-Item -ItemType Directory -Force -Path (Join-Path $caseRoot 'src/service') | Out-Null
Set-Location $caseRoot
git init
git switch -c feat/smoke
git config user.email 'gx-smoke@example.invalid'
git config user.name 'GX Smoke'
```

루트에 최소 `.claude/config.json`, `context/주문/README.md`, `requirements/order.md`를 만들고 커밋한다. 저장소의 AGENTS.md는 복사하지 않는다.

- [ ] **Step 2: Git source plugin을 깨끗하게 설치한다**

```powershell
codex.cmd plugin marketplace add bs-koo/oh-my-gx
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

설치 목록에서 version `1.33.0`, cache 절대경로, GX 스킬 목록을 기록한다.

- [ ] **Step 3: 하위 디렉터리 phase와 질문을 실제 세션에서 확인한다**

`gx-tdd`는 `src/service`에서, `gx-context`는 저장소 루트에서 각각 새 Codex 세션으로 실행한다. `gx-context`의 `context/` 모드 판별은 호출 위치를 기준으로 하므로 루트의 기존 컨텍스트를 확인하려면 루트에서 시작한다.

```text
$gx-tdd 주문 검증 --phase design
$gx-context 주문 --from requirements/order.md
```

`--from` 입력 파일은 `gx-context` 호출 위치인 저장소 루트에서 상대경로로 지정한다.

필수 증거:

- 루트 `.dev`만 생성되고 `src/service/.dev`는 생성되지 않는다.
- requirements/design 경로가 setup 뒤 실행된다.
- request_user_input trace의 질문은 3개 이하, option은 3개 이하, id는 snake_case다.
- 명시적 Other option은 없고 UI Other 답변의 id가 decision 기록에 남는다.

- [ ] **Step 4: 실제 명령값으로 검증 보고서 골격을 생성하고 결과를 채운다**

```powershell
$codexVersion = (codex.cmd --version | Out-String).Trim()
$pluginList = (codex.cmd plugin list --json | Out-String).Trim()
$repoRoot = (git rev-parse --show-toplevel | Out-String).Trim()
$report = @"
# 1.33.0 핵심 스킬 Codex 검증

- 일시: 2026-09-15
- OS: Windows
- Codex CLI: $codexVersion
- 테스트 저장소: $repoRoot

## 설치 목록 원문

````json
$pluginList
````

| 시나리오 | 결과 | 증거 |
|---|---|---|
| 하위 디렉터리 ``--phase design`` | 미실행 | PROJECT_ROOT, 생성된 .dev 경로, phase 순서를 기록한다 |
| gx-context 질문 Q2 | 미실행 | tool trace의 id·질문 수·option 수·Other 수를 기록한다 |
| decision capture | 미실행 | decisions.md의 question id와 답변을 기록한다 |
"@
[IO.File]::WriteAllText(
  (Join-Path $repoRoot 'docs/reports/2026-09-15-core-skills-codex-validation.md'),
  $report,
  [Text.UTF8Encoding]::new($false)
)
```

각 `미실행`을 실제 세션 결과에 따라 `PASS` 또는 `FAIL`로 바꾸고 증거 열에 관측값을 적는다. 실행하지 못한 항목만 `미실행`으로 유지하고 같은 행에 사유를 기록한다.

- [ ] **Step 5: codex-smoke Q2 상태와 보고서를 커밋한다**

Q2의 상태를 실제 결과에 맞춰 `PASS`, `FAIL`, `미실행` 중 하나로 갱신한다.

```bash
git add tests/codex-smoke.md docs/reports/2026-09-15-core-skills-codex-validation.md
git commit -m "test: 1.33.0 Codex 실제 세션 결과를 기록한다"
```

---

### Task 5: 릴리스 PR을 생성한다

**Files:**
- Modify: 없음

**Interfaces:**
- Consumes: Task 1~4 커밋과 검증 결과
- Produces: 리뷰 가능한 PR

- [ ] **Step 1: 최종 상태를 확인한다**

Run: `git status --short && git log --oneline main..HEAD`

Expected: 작업 트리 깨끗함. 골든 시나리오, 버전, 실제 smoke 결과 커밋이 보인다.

- [ ] **Step 2: gx-pull-request 스킬로 PR을 만든다**

```text
Skill(skill: "oh-my-gx:gx-pull-request")
```

PR 제목:

```text
FEATURE: gx-context·gx-dev·gx-tdd 실행 계약을 보강한다
```

PR 본문 핵심:

```markdown
문서에서 추출한 요구사항이 plan의 FR 참조만 남기고 사라지던 흐름을 status.md 원장으로 연결했습니다. 하위 디렉터리와 부분 phase에서도 VCS 루트를 사용하며, Codex 질문은 실제 스키마 범위와 Other 처리 규칙을 따릅니다.

## 변경
- gx-context 요구사항 원장과 sync cursor
- gx-dev·gx-tdd setup 선행 및 PROJECT_ROOT 절대경로
- SVN 저장소 ID와 Codex 질문 계약 통일
- 핵심 스킬 조건부 reference 분리

## 검증
- `python -m unittest discover -s tests -p "test_codex_*.py" -v`
- `python scripts/sync-codex-resources.py --check`
- `bash scripts/lint-consistency.sh`
- `bash scripts/hook-tests.sh`
- `bash scripts/test-gx-ralph.sh`
- `bash scripts/test-behavior-tests.sh`
- 실제 Codex 결과: `docs/reports/2026-09-15-core-skills-codex-validation.md`
```

- [ ] **Step 3: PR 체크를 확인한다**

Run: `gh pr checks --watch`

Expected: 모든 필수 check PASS. 실패하면 해당 소유 분기로 수정하고 release 브랜치에 반영한 뒤 다시 확인한다.
