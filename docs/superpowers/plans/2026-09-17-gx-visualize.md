# gx-visualize Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GX 산출물을 한국어 중심의 요구사항 추적·진행·변경 영향 시각화로 변환하는 독립 `gx-visualize` 스킬과 Archify/Mermaid/정적 HTML 백엔드 어댑터를 추가한다.

**Architecture:** 입력 수집과 GX JSON IR을 렌더러에서 분리한다. IR을 먼저 검증한 뒤 Archify가 실행 가능하면 Archify를 사용하고, 그렇지 않으면 Mermaid 또는 정적 HTML로 폴백한다. `gx-dev`는 명시적 요청이 있을 때만 이 스킬을 호출하며, 결과는 작업별 `.dev/{branch-slug}/visual/`에 저장한다.

**Tech Stack:** Markdown skill contracts, Python 3 standard library (`json`, `unittest`, `pathlib`), Node.js/Archify optional CLI, Mermaid source as fallback, self-contained HTML/SVG.

**Spec:** `docs/superpowers/specs/2026-09-17-gx-visualize-design.md`

## Global Constraints

- 기본 실행은 시각화를 자동 실행하지 않고 `--visualize` 또는 자연어 시각화 요청에서만 실행한다.
- `schema_version`은 `1`로 고정하고, 모든 edge의 양끝 노드와 근거 경로를 검증한다.
- 한국어 UI·콘텐츠를 기본으로 하되 ID·API path·table name·코드 식별자는 원문을 보존한다.
- Archify는 선택 의존성이며 설치·네트워크·자동 업데이트를 전제로 하지 않는다.
- 시각화 실패는 본 개발·리뷰 파이프라인을 실패시키지 않지만 `receipt`에 실패 원인과 폴백을 기록한다.
- Claude Code와 Codex가 동일한 상대경로 번들 계약을 사용한다.
- 구현 중 스킬·phase·Codex 리소스를 수정하면 `skill-maintenance.md`의 동기화·검증 절차를 따른다.

---

### Task 1: GX 시각화 IR 계약과 검증기

**Files:**
- Create: `.claude/skills/gx-visualize/references/ir-contract.md`
- Create: `.claude/skills/gx-visualize/schemas/gx-visual-ir.schema.json`
- Create: `.claude/skills/gx-visualize/scripts/validate_ir.py`
- Create: `tests/test_gx_visualize_ir.py`

**Interfaces:**
- Consumes: UTF-8 JSON file path and optional `--output receipt.json`.
- Produces: exit code `0|1` and receipt object with `status`, `errors`, `warnings`, `node_count`, `edge_count`, `missing_inputs`.
- Validator entry point: `validate(path: pathlib.Path) -> dict`.

- [ ] **Step 1: Write failing tests** for duplicate node IDs, missing edge targets, invalid status, absent evidence file, and a valid `trace` fixture.
- [ ] **Step 2: Run** `python -m unittest tests.test_gx_visualize_ir -v`; verify the validator module/schema is missing and tests fail.
- [ ] **Step 3: Define** the JSON Schema and the prose contract with exact enums and evidence rules from the spec.
- [ ] **Step 4: Implement** `validate()` using only the Python standard library; make errors deterministic and sort them by JSON path.
- [ ] **Step 5: Run** the focused test again and then `python -m unittest discover -s tests -p "test_gx_*.py" -v`; expect all pass.
- [ ] **Step 6: Commit** `test: add gx visualization IR contract and validator`.

### Task 2: 한국어 HTML/Mermaid 폴백 렌더러

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/render_fallback.py`
- Create: `.claude/skills/gx-visualize/templates/fallback.html`
- Create: `.claude/skills/gx-visualize/templates/fallback.css`
- Create: `tests/fixtures/gx-trace.valid.json`
- Create: `tests/test_gx_visualize_fallback.py`

**Interfaces:**
- Consumes: validated IR path, output directory, and `--backend mermaid|static`.
- Produces: `render(ir_path, output_dir, backend) -> dict` with `html_path`, `backend`, `receipt_path`.
- HTML must be self-contained and include Korean title, legend, node IDs, status text, and evidence cards.

- [ ] **Step 1: Write failing tests** for Korean content, preserved technical labels, deterministic output, and static rendering when Mermaid is unavailable.
- [ ] **Step 2: Run** `python -m unittest tests.test_gx_visualize_fallback -v`; verify failure because renderer/templates do not exist.
- [ ] **Step 3: Implement** stable Mermaid generation from sorted nodes/edges and HTML escaping for labels, paths, and evidence.
- [ ] **Step 4: Implement** static HTML fallback with an accessible node list, relationship table, status badges, and evidence sections; do not hide failed validation.
- [ ] **Step 5: Run** focused tests and inspect generated fixture HTML for `lang="ko"`, `AN-02-001`, and the absence of unescaped `<script>` input.
- [ ] **Step 6: Commit** `feat: add Korean Mermaid and static visualization fallback`.

### Task 3: Archify 선택 어댑터와 백엔드 선택 영수증

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/detect_backend.py`
- Create: `.claude/skills/gx-visualize/scripts/render_archify.py`
- Create: `.claude/skills/gx-visualize/references/archify-adapter.md`
- Create: `tests/test_gx_visualize_backend.py`

**Interfaces:**
- `detect_backend() -> {"backend": "archify|mermaid|static", "reason": str, "version": str|null}`.
- `render_archify(ir_path, output_dir, archify_command) -> receipt`.
- Archify command failures return a failed Archify attempt plus a successful fallback receipt; they never claim Archify success.

- [ ] **Step 1: Write failing tests** using a fake executable for Archify success, non-zero Archify validation, missing Node, and fallback selection.
- [ ] **Step 2: Run** `python -m unittest tests.test_gx_visualize_backend -v`; confirm missing detection/adapter behavior.
- [ ] **Step 3: Implement** executable detection without network calls or guessed installation paths; accept an explicit command override.
- [ ] **Step 4: Implement** the Archify flow as `validate` then `deliver`, capture stdout/stderr, and write a receipt containing command, exit code, and artifact path.
- [ ] **Step 5: Implement** fallback chaining `archify -> mermaid -> static` and preserve the original failed backend diagnostic.
- [ ] **Step 6: Run** focused tests and verify a failed Archify command produces a usable HTML file and truthful receipt.
- [ ] **Step 7: Commit** `feat: add optional Archify backend with truthful fallback`.

### Task 4: `gx-visualize` 스킬 계약과 GX 산출물 수집

**Files:**
- Create: `.claude/skills/gx-visualize/SKILL.md`
- Create: `.claude/skills/gx-visualize/references/gx-mapping.md`
- Create: `.claude/skills/gx-visualize/references/codex-runtime.md`
- Create: `.claude/skills/gx-visualize/examples/trace-request.md`
- Create: `tests/test_gx_visualize_skill_contract.py`

**Interfaces:**
- Skill command: `gx-visualize <trace|progress|impact|service|sequence> [--input <path>] [--output <path>] [--backend auto|archify|mermaid|static]`.
- Input collector: `collect_inputs(project_root, dev_dir, view) -> {"files": [...], "missing_inputs": [...]}`.
- Output report fields: `view`, `backend`, `html_path`, `ir_path`, `receipt_path`, `validation_status`, `missing_inputs`.

- [ ] **Step 1: Write failing contract tests** for view routing, default `auto` backend, relative references, missing-input reporting, and explicit “visualization only” failure behavior.
- [ ] **Step 2: Run** `python -m unittest tests.test_gx_visualize_skill_contract -v`; verify the skill contract and mapping references are absent.
- [ ] **Step 3: Write** SKILL.md with Korean trigger phrases, view router, input mapping, output contract, failure rules, and “do not infer runtime facts” constraints.
- [ ] **Step 4: Add** Codex adaptation notes that point to the installed runtime contract without assuming Claude-only tools, model names, or absolute plugin paths.
- [ ] **Step 5: Add** mapping tables for `prd/design/codemap/state/diff/DE-08/DE-13` and the three receipt states (`verified`, `fallback`, `failed`).
- [ ] **Step 6: Run** contract tests and `python scripts/sync-codex-resources.py --check`; fix every missing relative reference.
- [ ] **Step 7: Commit** `feat: add gx-visualize skill contract and GX mappings`.

### Task 5: `gx-dev` 명시적 호출 연동

**Files:**
- Modify: `.claude/skills/gx-dev/SKILL.md`
- Modify: `.claude/skills/gx-dev/phases/phase-design.md`
- Modify: `.claude/skills/gx-dev/phases/phase-review.md`
- Modify: `.claude/skills/gx-dev/phases/phase-complete.md`
- Modify: `tests/test_codex_project_config.py` or create `tests/test_gx_visualize_routing.py`

**Interfaces:**
- Intent parser adds `--visualize` as an independent flag; it must not alter the selected Phase or model profile.
- Phase handoff passes `DEV_DIR`, `PROJECT_ROOT`, selected view, and available input paths to `gx-visualize`.
- Default path remains byte-for-byte behaviorally equivalent when the flag is absent.

- [ ] **Step 1: Write failing routing tests** for explicit flag, Korean natural-language trigger, absent-trigger no-op, and conflict with `--status` only if the existing parser defines that conflict.
- [ ] **Step 2: Run** the focused routing test and confirm the new trigger is not recognized.
- [ ] **Step 3: Add** the independent flag and natural-language detection without changing phase precedence, resume semantics, or RALPH rules.
- [ ] **Step 4: Add** optional calls after design completion and review entry, passing only the files that exist.
- [ ] **Step 5: Add** completion reporting with HTML/IR/receipt paths and truthful fallback status; never block commit/PR on visualization failure.
- [ ] **Step 6: Run** `python -m unittest discover -s tests -p "test_codex_*.py" -v` and the focused visualization tests.
- [ ] **Step 7: Commit** `feat: wire explicit gx visualization into gx-dev phases`.

### Task 6: 배포·문서·검증 시나리오

**Files:**
- Create: `docs/gx-visualize-guide.md`
- Create: `tests/golden-scenarios.md` section for visualization or `tests/codex-smoke.md` visualization scenarios
- Create: `tests/fixtures/gx-impact.valid.json`

**Interfaces:**
- Both manifests expose `.claude/skills/gx-visualize` through the existing skill path mechanism.
- User documentation includes install-independent examples for Archify available, Archify missing, and static fallback cases.

- [ ] **Step 1: Write documentation checks** for the skill name, trigger examples, output directory, and fallback disclosure.
- [ ] **Step 2: Add** one Codex smoke scenario covering skill discovery, one fallback scenario, and one truthful failed-visualization report.
- [ ] **Step 3: Run** `python scripts/sync-codex-resources.py --check` and `bash scripts/lint-consistency.sh`.
- [ ] **Step 4: Run** `python -m unittest discover -s tests -p "test_codex_*.py" -v` and `python -m unittest discover -s tests -p "test_gx_*.py" -v`.
- [ ] **Step 5: Record** any unexecuted real Archify/Codex installation checks as unexecuted in the smoke report; do not substitute local mocks for those claims.
- [ ] **Step 6: Commit** `docs: document gx visualization skill and Codex smoke coverage`.

### Task 7: 버전 업·README·GitHub Pages 공개

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`
- Modify: `index.html`
- Test: `tests/test_gx_visualize_docs.py`

**Interfaces:**
- Version changes from `1.32.0` to `1.33.0` in every plugin manifest that currently declares `1.32.0`.
- README and Pages describe `gx-visualize` as the 18th skill, including Korean examples, views, output path, and Archify/Mermaid/static fallback disclosure.
- No page or README sentence claims live infrastructure inspection or guaranteed Archify availability.

- [ ] **Step 1: Write failing documentation tests** that load both manifests and assert version `1.33.0`, the `gx-visualize` skill directory exists, README contains the trigger/output/fallback terms, and `index.html` contains the skill name plus 18-skill count.
- [ ] **Step 2: Run** `python -m unittest tests.test_gx_visualize_docs -v`; verify the assertions fail before documentation/version edits.
- [ ] **Step 3: Update** `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and marketplace metadata consistently to `1.33.0` without changing unrelated versions.
- [ ] **Step 4: Add** a README section and usage table for `gx-visualize`, preserving Korean style and linking to `docs/gx-visualize-guide.md`.
- [ ] **Step 5: Add** an accessible GitHub Pages feature card/section, update the displayed skill count from 17 to 18 where it describes the current catalog, and add a Korean sample output flow.
- [ ] **Step 6: Run** the focused documentation tests and inspect `index.html` for balanced tags and no external runtime dependency.
- [ ] **Step 7: Commit** `feat: publish gx-visualize in plugin docs and pages`.

## Self-review checklist

- IR, Korean rendering, Archify integration, fallback, skill routing, `gx-dev` integration, deployment, and smoke coverage each have a dedicated task.
- No task requires live infrastructure inspection or a network download.
- All interfaces used by later tasks are defined in the producing task.
- The default `gx-dev` path remains unchanged without an explicit visualization request.
- The plan does not claim perceptual visual QA without browser/image evidence.
