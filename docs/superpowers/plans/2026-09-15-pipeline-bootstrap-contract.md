# gx-dev·gx-tdd 파이프라인 부트스트랩 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 저장소 하위 디렉터리와 `--phase requirements/design` 진입에서도 gx-dev·gx-tdd가 필요한 setup을 실행하고 같은 프로젝트 루트·SVN 저장소 ID를 사용하게 한다.

**Architecture:** phase-setup 맨 앞에서 VCS 명령으로 절대 PROJECT_ROOT를 결정하고 이후 모든 상대경로의 기준으로 사용한다. `--phase requirements`는 `[setup, requirements]`, design은 `[setup, design]`으로 확장하며 기존 산출물 게이트가 PRD가 없을 때 requirements를 삽입한다. SVN 도메인 매칭은 gx-dev·gx-tdd가 같은 URL 정규화 규칙을 사용하고, 통합 단계에서 gx-context와 대조한다.

**Tech Stack:** Markdown skill instructions, Python 3.10 `unittest`, Git/SVN command contracts

**Spec:** `docs/superpowers/specs/2026-09-15-core-skills-hardening-design.md` — D2

## Global Constraints

- 기준 브랜치: `docs/codex-skill-maintenance`의 `5893c6c`; 작업 브랜치: `fix/pipeline-bootstrap-contract`.
- 이 브랜치는 A와 병렬 진행하며 `gx-context/SKILL.md`를 수정하지 않는다. gx-context의 SVN 식별 문구는 A가 소유하고 통합 단계에서 세 스킬을 대조한다.
- requirements/design 외 phase의 실행 목록과 TDD RGR 게이트는 변경하지 않는다.
- Git 루트는 `git rev-parse --show-toplevel`, SVN 루트는 `svn info --show-item wc-root`, 마지막 fallback은 현재 디렉터리 절대경로다.
- 기능 브랜치에서는 manifest·marketplace·CHANGELOG 버전을 바꾸지 않는다.
- `gx-dev`와 `gx-tdd`의 쌍둥이 문구는 동일 테스트에서 대조한다.

---

### Task 1: 부분 phase 선행 조건을 실행 목록에 반영한다

**Files:**
- Create: `tests/test_codex_skill_pipeline.py`
- Modify: `.claude/skills/gx-dev/SKILL.md` — Phase 실행 루프
- Modify: `.claude/skills/gx-tdd/SKILL.md` — Phase 실행 루프

**Interfaces:**
- Consumes: 기존 산출물 게이트 `design + prd.md 부재 → requirements`
- Produces: `requirements=[setup, requirements]`, `design=[setup, design]`

- [ ] **Step 1: phase 결정표 회귀 테스트를 작성한다**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / ".claude/skills/gx-dev/SKILL.md"
TDD = ROOT / ".claude/skills/gx-tdd/SKILL.md"


class PipelineBootstrapContractTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_partial_phase_lists_include_setup(self):
        for path in (DEV, TDD):
            text = self.read(path)
            loop = text[text.index("### Phase 실행 루프"):text.index("### Phase 파일 경로")]
            self.assertIn('elif --phase == "requirements":', loop, path)
            self.assertIn("PHASES = [setup, requirements]", loop, path)
            self.assertIn('elif --phase == "design":', loop, path)
            self.assertIn("PHASES = [setup, design]", loop, path)
            self.assertNotIn("PHASES = [해당 phase만]", loop, path)

    def test_phase_selection_matches_loop(self):
        for path in (DEV, TDD):
            text = self.read(path)
            selection = text[text.index("## Phase 선택"):]
            self.assertIn("requirements`: `[setup, requirements]`", selection, path)
            self.assertIn("design`: `[setup, design]`", selection, path)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 기존 단일 phase 분기 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_pipeline.PipelineBootstrapContractTests.test_partial_phase_lists_include_setup tests.test_codex_skill_pipeline.PipelineBootstrapContractTests.test_phase_selection_matches_loop -v`

Expected: 두 테스트 모두 FAIL하고 `PHASES = [해당 phase만]`가 원인으로 표시된다.

- [ ] **Step 3: gx-dev Phase 실행 루프의 `--phase` 분기를 교체한다**

```text
elif --phase == "requirements":
    PHASES = [setup, requirements]
elif --phase == "design":
    PHASES = [setup, design]  # setup 뒤 prd.md가 없으면 2a 게이트가 requirements를 먼저 실행
elif --phase 지정:
    PHASES = [해당 phase만]  # implement/review/complete
```

산출물 게이트의 design 조건은 유지한다. `[setup, design]`에서 setup 완료 후 PRD가 없을 때만 requirements가 실행된다.

- [ ] **Step 4: gx-tdd Phase 실행 루프에 정확히 같은 분기를 넣는다**

```text
elif --phase == "requirements":
    PHASES = [setup, requirements]
elif --phase == "design":
    PHASES = [setup, design]  # setup 뒤 prd.md가 없으면 2a 게이트가 requirements를 먼저 실행
elif --phase 지정:
    PHASES = [해당 phase만]  # implement/review/complete
```

- [ ] **Step 5: 두 Phase 선택 설명을 결정표 표기로 바꾼다**

각 파일에서 requirements/design 두 불릿을 다음으로 교체한다. 명령 접두사 `/gx-dev` 또는 `/gx-tdd`는 해당 파일 값을 유지한다.

```markdown
- `--phase requirements`: `[setup, requirements]`를 실행하여 작업환경과 도메인 컨텍스트를 확정한 뒤 PRD를 작성한다.
- `--phase design`: `[setup, design]`를 실행한다. setup 뒤 `${DEV_DIR}/prd.md`가 없으면 산출물 게이트가 requirements를 먼저 실행한다.
```

- [ ] **Step 6: 테스트와 린트를 통과시킨다**

Run: `python -m unittest tests.test_codex_skill_pipeline -v && bash scripts/lint-consistency.sh`

Expected: 2 tests OK, lint 36/36 통과.

- [ ] **Step 7: 커밋한다**

```bash
git add tests/test_codex_skill_pipeline.py .claude/skills/gx-dev/SKILL.md .claude/skills/gx-tdd/SKILL.md
git commit -m "fix: 부분 phase에 필요한 setup을 선행한다"
```

---

### Task 2: PROJECT_ROOT를 VCS 루트 절대경로로 계산한다

**Files:**
- Modify: `tests/test_codex_skill_pipeline.py`
- Modify: `.claude/skills/gx-dev/phases/phase-setup.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md`
- Modify: `.claude/skills/gx-dev/SKILL.md` — 공유 규칙, phase-only 환경 감지
- Modify: `.claude/skills/gx-tdd/SKILL.md` — 공유 규칙, phase-only 환경 감지

**Interfaces:**
- Consumes: shell current directory, Git/SVN metadata
- Produces: absolute `PROJECT_ROOT`; every config/context/.dev/VCS/build path consumes it

- [ ] **Step 1: 루트 우선순위와 금지 문구 테스트를 추가한다**

```python
    def test_setup_resolves_absolute_project_root_before_state_scan(self):
        for path in (
            ROOT / ".claude/skills/gx-dev/phases/phase-setup.md",
            ROOT / ".claude/skills/gx-tdd/phases/phase-setup.md",
        ):
            text = self.read(path)
            root_step = text.index("## Step -1: 프로젝트 루트 결정")
            state_step = text.index("## Step 0: 진행 중 작업 감지")
            self.assertLess(root_step, state_step, path)
            section = text[root_step:state_step]
            self.assertIn("git rev-parse --show-toplevel", section, path)
            self.assertIn("svn info --show-item wc-root", section, path)
            self.assertIn("절대경로", section, path)

    def test_skill_contract_does_not_pin_root_to_dot(self):
        for path in (DEV, TDD):
            text = self.read(path)
            self.assertNotIn("`PROJECT_ROOT`: 항상 `./`", text, path)
            self.assertNotIn("`PROJECT_ROOT` = 현재 디렉토리", text, path)
            self.assertIn("PROJECT_ROOT` = phase-setup과 같은 우선순위의 절대경로", text, path)
```

- [ ] **Step 2: 테스트가 `./` 고정 규칙 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_pipeline.PipelineBootstrapContractTests.test_setup_resolves_absolute_project_root_before_state_scan tests.test_codex_skill_pipeline.PipelineBootstrapContractTests.test_skill_contract_does_not_pin_root_to_dot -v`

Expected: Step -1 부재와 `항상 ./` 잔존으로 FAIL.

- [ ] **Step 3: 두 phase-setup의 맨 앞에 Step -1을 추가한다**

두 파일의 제목 다음, Step 0 앞에 다음 절을 넣는다.

```markdown
## Step -1: 프로젝트 루트 결정

현재 디렉토리에서 아래 순서로 절대경로 `PROJECT_ROOT`를 결정한다.

1. `git rev-parse --show-toplevel` 성공 시 그 출력을 사용한다.
2. Git이 아니고 `svn info --show-item wc-root` 성공 시 그 출력을 사용한다.
3. 둘 다 실패하면 현재 디렉토리의 절대경로를 사용한다. 이후 Git 생성을 승인받아 `git init`을 실행하면 `git rev-parse --show-toplevel`로 다시 계산한다.

이후 `.claude/config.json`, `.dev/`, `context/`, `references/`와 모든 Git·SVN·빌드·테스트 명령은 `PROJECT_ROOT` 기준으로 읽고 실행한다. 상대경로 파일 도구 호출도 이 경로 아래에서 해석한다.
```

- [ ] **Step 4: phase-setup 내부의 `PROJECT_ROOT = ./` 문장을 제거한다**

- gx-dev Step 3의 ``PROJECT_ROOT = ./ (현재 디렉토리).``를 ``PROJECT_ROOT는 Step -1에서 결정한 절대경로를 유지한다.``로 교체한다.
- gx-tdd Step 3의 같은 문장을 같은 새 문장으로 교체한다.
- Step 0의 `.dev/*/state.md`와 Step 1의 `.claude/config.json`이 `${PROJECT_ROOT}/...` 기준임을 각 절 첫 문장에 명시한다.

- [ ] **Step 5: 두 SKILL.md 공유 규칙과 phase-only 환경 감지를 갱신한다**

공유 규칙의 PROJECT_ROOT 불릿을 다음으로 교체한다.

```markdown
- `PROJECT_ROOT`: phase-setup Step -1이 Git `--show-toplevel` > SVN `wc-root` > 현재 디렉토리 절대경로 순으로 결정한 값.
```

Phase 선택 아래 환경 감지 3번을 다음으로 교체한다.

```markdown
> 3. `PROJECT_ROOT` = phase-setup과 같은 우선순위의 절대경로. 이후 config, `.dev`, context, VCS·빌드·테스트 명령은 이 경로를 기준으로 수행한다.
```

- [ ] **Step 6: 테스트와 전체 린트를 실행한다**

Run: `python -m unittest tests.test_codex_skill_pipeline -v && bash scripts/lint-consistency.sh`

Expected: 4 tests OK, lint 36/36 통과.

- [ ] **Step 7: 커밋한다**

```bash
git add tests/test_codex_skill_pipeline.py .claude/skills/gx-dev/SKILL.md .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md
git commit -m "fix: 파이프라인 루트를 VCS 작업 루트로 계산한다"
```

---

### Task 3: SVN 저장소 ID 규칙을 gx-dev·gx-tdd에서 통일한다

**Files:**
- Modify: `tests/test_codex_skill_pipeline.py`
- Modify: `.claude/skills/gx-dev/phases/phase-setup.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md`
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md`

**Interfaces:**
- Consumes: SVN working-copy URL, Task 2의 absolute PROJECT_ROOT
- Produces: `REPOSITORY_ID`

- [ ] **Step 1: 세 파일의 SVN 규칙 동등성 테스트를 추가한다**

```python
    def test_svn_repository_identity_is_shared(self):
        paths = (
            ROOT / ".claude/skills/gx-dev/phases/phase-setup.md",
            ROOT / ".claude/skills/gx-tdd/phases/phase-setup.md",
        )
        for path in paths:
            text = self.read(path)
            for phrase in (
                "svn info --show-item url",
                "trunk",
                "branches/<name>",
                "tags/<name>",
                "REPOSITORY_ID",
                "basename(PROJECT_ROOT)",
            ):
                self.assertIn(phrase, text, path)
            self.assertNotIn("svn info --show-item repos-root-url", text, path)
```

- [ ] **Step 2: gx-dev의 `repos-root-url` 때문에 실패하는지 확인한다**

Run: `python -m unittest tests.test_codex_skill_pipeline.PipelineBootstrapContractTests.test_svn_repository_identity_is_shared -v`

Expected: gx-dev에서 `svn info --show-item url` 누락으로 FAIL.

- [ ] **Step 3: 두 소비 지점에 동일한 판별 규칙을 기록한다**

gx-dev·gx-tdd phase-setup의 SVN 레포명 설명을 다음 문장으로 교체한다.

```markdown
**svn 저장소 ID**: `svn info --show-item url`의 끝에서 `trunk`, `branches/<name>`, `tags/<name>`을 제거하고 남은 마지막 세그먼트를 `REPOSITORY_ID`로 사용한다. 결과가 비거나 모호하면 `basename(PROJECT_ROOT)`를 사용한다.
```

- [ ] **Step 4: maintenance notes에 쌍둥이 소비 지점을 기록한다**

```markdown
- **SVN REPOSITORY_ID**: `svn info --show-item url` 정규화(`trunk`, `branches/<name>`, `tags/<name>` 제거) 후 마지막 세그먼트, 실패 시 `basename(PROJECT_ROOT)`. gx-dev·gx-tdd phase-setup을 함께 수정하고, gx-context producer는 요구사항 원장 분기에서 같은 문구를 유지한다. `tests/test_codex_skill_pipeline.py`가 두 pipeline 파일을 대조한다.
```

- [ ] **Step 5: 전체 브랜치 검증을 실행한다**

Run: `python -m unittest tests.test_codex_skill_pipeline -v && python scripts/sync-codex-resources.py --check && bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`

Expected: 5 tests OK, sync check 성공, lint 36/36, hook tests 성공.

- [ ] **Step 6: 커밋한다**

```bash
git add tests/test_codex_skill_pipeline.py .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-tdd/references/maintenance-notes.md
git commit -m "fix: SVN 저장소 식별 규칙을 통일한다"
```

---

### Task 4: 하위 디렉터리·부분 phase 수용 증거를 기록한다

**Files:**
- Create: `docs/reports/2026-09-15-pipeline-bootstrap-validation.md`

**Interfaces:**
- Consumes: Task 1~3 결과
- Produces: 통합 브랜치가 확인할 B 완료 증거

- [ ] **Step 1: 정적 회귀 검사를 모두 실행한다**

Run: `python -m unittest discover -s tests -p "test_codex_*.py" -v`

Expected: 모든 테스트 OK.

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh && bash scripts/test-behavior-tests.sh`

Expected: lint 36/36, hook tests 성공, behavior mock 성공.

- [ ] **Step 2: 수동 명령 판독을 수행한다**

Run: `rg -n "PHASES = \[setup, (requirements|design)\]|git rev-parse --show-toplevel|svn info --show-item wc-root|REPOSITORY_ID" .claude/skills/gx-dev .claude/skills/gx-tdd .claude/skills/gx-context`

Expected: phase 목록은 dev/tdd 양쪽, root 명령은 두 setup과 두 phase-only 환경 설명, REPOSITORY_ID는 dev/tdd에서 확인된다.

- [ ] **Step 3: 분기 검증 보고서를 작성한다**

```markdown
# gx-dev·gx-tdd 파이프라인 부트스트랩 검증

- 기준 커밋: `5893c6c`
- 분기: `fix/pipeline-bootstrap-contract`
- 결과: PASS

| 검사 | 결과 |
|---|---|
| `test_codex_skill_pipeline.py` | PASS |
| lint 36/36 | PASS |
| hook-tests | PASS |
| behavior mock | PASS |
```

- [ ] **Step 4: 증거를 커밋한다**

```bash
git add docs/reports/2026-09-15-pipeline-bootstrap-validation.md
git commit -m "docs: 파이프라인 부트스트랩 분기 검증 결과를 기록한다"
```
