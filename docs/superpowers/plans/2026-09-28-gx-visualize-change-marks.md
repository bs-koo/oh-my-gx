# gx-visualize 변경 표시 재설계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "이번 세션분만" 시각화를 없애고, 전체 아키텍처 맵 위에 이번 사이클에서 새로 생기거나 바뀐 구조를 `[신규]`·`[변경]`으로 표시하며, 이 과정을 명령 하나(`build_map.py`)로 끝낸다.

**Architecture:** 기준 커밋(`git merge-base <ref> HEAD`)의 소스를 임시 폴더에 꺼내 같은 스캐너로 스캔하고, 현재 스캔과 노드·엣지 ID로 비교해 IR에 `change`를 단다(`changes.py`). 렌더러 세 개(Archify·Mermaid·static)와 인덱스가 그 표시를 그린다. `build_map.py`가 스캔 → 변경 표시 → 라벨 → 도메인 분할 → 검증·렌더 → Mermaid 자산 → 인덱스를 한 번에 수행하고 JSON 보고를 낸다. 함께 Archify 열 간격(8px → 40px), `*Facade` 인식, gx-commit의 산출물 제외를 고친다.

**Tech Stack:** Python 3.10 표준 라이브러리만, git CLI, Archify CLI(`node ~/.agents/skills/archify/bin/archify.mjs`), Mermaid 11, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-18-gx-visualize-architecture-map-design.md` — 특히 §5.8(세션 스코프 폐기와 변경 표시), §6, §8 수용 기준 12~19.

## Global Constraints

- 한국어로 문서·주석·커밋 메시지를 쓴다. 커밋 형식은 `{type}: 한국어 메시지`이고 `Co-Authored-By` 줄을 절대 넣지 않는다.
- SQL 본문은 IR에 싣지 않는다 — 테이블명만. label·HTML·영수증·보고에 비밀·토큰·개인정보를 넣지 않는다.
- 실제 GX 저장소(`D:\SQ\kereb-grep-2025-admin\...`, `D:\SQ\GSEED\...`)는 **읽기 전용**이다. 파일을 만들거나 고치지 않고, git 쓰기 명령(checkout·clean·add·stash·commit)을 실행하지 않는다. 출력은 `--map-dir`로 scratchpad에만 쓴다.
- 이 저장소는 여러 에이전트가 같은 작업 트리를 쓴다. `git checkout <rev> -- .`, `git add -A`, `git stash`, `git clean`을 쓰지 않는다. 커밋은 바꾼 파일을 하나씩 지정해 `git add <path>`로 스테이징하고, 커밋 전에 `git diff --cached --stat`으로 내 파일만 올라갔는지 확인한다. `bash.exe.stackdump`와 `.dev/feat-gx-visualize-architecture-map/decisions.md`는 건드리지 않는다.
- `git push --force` 금지. Archify를 다시 설치하지 않는다(`npx ... skills add`를 손으로 실행하지 않는다).
- Python은 3.10에서 돌아야 한다(`tarfile` filter 인자, `match` 문, 3.11+ 전용 API 금지). 파일 입출력은 `encoding="utf-8"`을 명시한다.
- 서브에이전트는 하위 에이전트를 띄우지 않는다.
- 테스트 기준선: `python -m unittest discover -s tests -p "test_gx_*.py"`는 이 계획 시작 시점에 249건 중 **7건 실패**다. 7건 모두 `test_gx_visualize_routing`(`--visualize` 배선, 이 계획 범위 밖)이다. 이 7건 외의 실패가 생기면 안 된다.
- 스킬 파일을 바꾸는 태스크는 끝에 `python scripts/sync-codex-resources.py --check`와 `bash scripts/lint-consistency.sh`(약 4분 — Bash `timeout: 600000`)를 통과시킨다.
- 산출물(`.dev/architecture/`, `.dev/*/visual/`)은 커밋하지 않는다.

## Review Focus

이 다섯 가지는 사용자가 실제로 부딪힐 가능성이 가장 높은데, 명세 문장만으로는 테스트되지 않는다. 각각 담당 태스크에 테스트를 넣었다.

1. **프로젝트 루트가 git 최상위보다 아래일 때**(모노레포, `webapp/` 하위 등) — 기준 스캔이 같은 하위 폴더를 봐야 한다. 안 그러면 노드 ID 경로가 달라져 **모든 노드가 신규**로 칠해진다. → Task 2 `test_project_root_below_the_repository_top_uses_the_same_subtree`
2. **한국어 폴더·파일명**(JSP `게시판/list.jsp`) — `git ls-tree`의 경로 인용 때문에 기준 트리에서 빠지면 그 화면이 신규로 오판된다. → Task 2 `test_korean_directory_names_survive_base_extraction`
3. **한국어 라벨을 붙인 실행** — 라벨을 변경 판정보다 먼저 적용하면 라벨을 붙인 노드가 모두 "변경"이 된다. → Task 7 `test_labels_do_not_turn_into_changes`
4. **기준을 정할 수 없는 환경**(git 아님, 없는 ref, 공통 조상 없음, `--`로 시작하는 ref) — 맵은 만들어지고 이유가 보고돼야 한다. 조용히 표시가 사라지면 "변경 없음"으로 읽힌다. → Task 2의 네 테스트, Task 7 `test_changed_since_outside_git_still_builds_the_map`, Task 6 `test_skipped_marking_reports_the_reason`
5. **같은 명령을 두 번, 또는 도메인 하나만 다시 실행** — 두 번째 실행이 첫 결과와 같아야 하고, `--domain` 실행이 다른 도메인 산출물을 지우면 안 되며, 전체 실행은 사라진 도메인의 옛 그림을 지워야 한다. → Task 7 `test_rerun_is_stable`, `test_single_domain_run_keeps_other_domains`, `test_stale_domain_outputs_are_removed_on_full_run`

---

## 파일 구조

| 파일 | 책임 | 태스크 |
|---|---|---|
| `.claude/skills/gx-visualize/scripts/validate_ir.py` | `change` 필드 검증 | 1 |
| `.claude/skills/gx-visualize/schemas/gx-visual-ir.schema.json` | `change` 필드 문서화 | 1 |
| `.claude/skills/gx-visualize/scripts/changes.py` (신규) | 기준 트리 추출·비교·표시 | 2 |
| `.claude/skills/gx-visualize/scripts/scan_entrypoints.py` | `*Facade` → service | 3 |
| `.claude/skills/gx-visualize/scripts/split_domains.py` | `facade` 계층 폴더 | 3 |
| `.claude/skills/gx-visualize/references/entrypoint-rules.md` | Facade 규칙 문서 | 3 |
| `.claude/skills/gx-visualize/scripts/to_archify.py` | 라벨 접두사·강조 선·열 간격 40 | 4 |
| `.claude/skills/gx-visualize/scripts/render_fallback.py` | 배지·Mermaid 강조·배너, 스냅샷 배너 제거 | 5 |
| `.claude/skills/gx-visualize/scripts/render_archify.py` | Archify HTML에 배너, 스냅샷 인자 제거 | 5 |
| `.claude/skills/gx-visualize/templates/fallback.css` | 배지·강조 카드 스타일 | 5 |
| `.claude/skills/gx-visualize/scripts/build_index.py` | "이번 변경" 절·카드 강조 | 6 |
| `.claude/skills/gx-visualize/scripts/build_map.py` (신규) | 단일 명령 | 7 |
| `.claude/skills/gx-visualize/SKILL.md`, `references/gx-mapping.md`, `references/archify-adapter.md` | 계약 개정 | 8 |
| `.claude/skills/gx-dev/phases/phase-complete.md`, `.claude/skills/gx-tdd/phases/phase-complete.md`, `.claude/skills/gx-tdd/references/maintenance-notes.md` | Step 5.5 개정 | 8 |
| `.claude/skills/gx-commit/SKILL.md` | 산출물 스테이징 제외 | 9 |
| `README.md`, `docs/gx-visualize-guide.md`, `index.html`, `CHANGELOG.md`, `tests/codex-smoke.md` | 사용자 문서 | 11 |

---

### Task 1: IR에 변경 표시 필드를 더한다

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/validate_ir.py`
- Modify: `.claude/skills/gx-visualize/schemas/gx-visual-ir.schema.json`
- Create: `tests/test_gx_arch_changes.py`

**Interfaces:**
- Produces: IR 노드의 선택 필드 `change: "added" | "changed"`, IR 엣지의 선택 필드 `change: "added"`. `validate_ir.NODE_CHANGES = {"added", "changed"}`, `validate_ir.EDGE_CHANGES = {"added"}`. 이후 모든 태스크가 이 두 값만 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_gx_arch_changes.py`를 새로 만든다.

```python
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".claude" / "skills" / "gx-visualize" / "scripts"
SCHEMA = REPO / ".claude" / "skills" / "gx-visualize" / "schemas" / "gx-visual-ir.schema.json"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"gx_changes_test_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ir(nodes, edges):
    return {"schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t", "nodes": nodes, "edges": edges}


class ChangeFieldValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = _load("validate_ir")

    def _validate(self, payload):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ir.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return self.validator.validate(path)

    def _node(self, node_id, **extra):
        return {"id": node_id, "kind": "api", "label": node_id, "status": "unknown", **extra}

    def test_added_and_changed_nodes_and_added_edges_are_valid(self):
        payload = _ir(
            [self._node("a", change="added"), self._node("b", change="changed"), self._node("c")],
            [{"id": "a->b:calls", "source": "a", "target": "b", "relation": "calls", "change": "added"}],
        )
        self.assertEqual(self._validate(payload)["status"], "valid")

    def test_unknown_node_change_is_rejected(self):
        receipt = self._validate(_ir([self._node("a", change="removed")], []))
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(any("$.nodes[0].change" in error for error in receipt["errors"]))

    def test_edges_cannot_be_marked_changed(self):
        # 엣지 ID는 양 끝과 관계로 정해지므로 "바뀐 엣지"는 "사라진 엣지 + 새 엣지"로 나타난다.
        payload = _ir(
            [self._node("a"), self._node("b")],
            [{"id": "a->b:calls", "source": "a", "target": "b", "relation": "calls", "change": "changed"}],
        )
        receipt = self._validate(payload)
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(any("$.edges[0].change" in error for error in receipt["errors"]))

    def test_non_string_change_is_rejected_without_crashing(self):
        receipt = self._validate(_ir([self._node("a", change=["added"])], []))
        self.assertEqual(receipt["status"], "failed")

    def test_schema_documents_the_same_change_values(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$defs"]["node"]["properties"]["change"], {"enum": ["added", "changed"]})
        self.assertEqual(schema["$defs"]["edge"]["properties"]["change"], {"enum": ["added"]})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_arch_changes -v`
Expected: `test_unknown_node_change_is_rejected`, `test_edges_cannot_be_marked_changed`, `test_non_string_change_is_rejected_without_crashing`는 `'valid' != 'failed'`로 FAIL, `test_schema_documents_the_same_change_values`는 `KeyError: 'change'`로 ERROR. `test_added_and_changed_nodes_and_added_edges_are_valid`는 이미 PASS(검증기가 모르는 필드를 무시하므로).

- [ ] **Step 3: 검증기 구현**

`validate_ir.py`에서 `STATUSES = {...}` 줄 바로 아래에 추가한다.

```python
# 변경 표시(설계서 §5.8.1). 노드는 신규·변경, 엣지는 신규만 있다 - 엣지 ID가 양 끝과
# 관계로 정해지므로 "바뀐 엣지"는 "사라진 엣지 + 새 엣지"로 나타난다.
NODE_CHANGES = {"added", "changed"}
EDGE_CHANGES = {"added"}
```

노드 루프에서 `if "technical_label" in node and not isinstance(node["technical_label"], str):` 두 줄 바로 아래에 추가한다.

```python
        if "change" in node and (not isinstance(node["change"], str) or node["change"] not in NODE_CHANGES):
            errors.append((f"{base}.change", f"must be one of {', '.join(sorted(NODE_CHANGES))}"))
```

엣지 루프에서 `edge_id = edge.get("id")`로 시작하는 중복 검사 블록이 끝난 직후, `for field in ("source", "target"):` 바로 앞에 추가한다.

```python
        if "change" in edge and (not isinstance(edge["change"], str) or edge["change"] not in EDGE_CHANGES):
            errors.append((f"{base}.change", f"must be one of {', '.join(sorted(EDGE_CHANGES))}"))
```

`gx-visual-ir.schema.json`에서 `"status": {"enum": [...]}` 줄 아래(노드 `properties` 안)에 `"change": {"enum": ["added", "changed"]},`을 넣고, 엣지 `properties`의 `"relation"` 줄 끝에 쉼표를 붙인 뒤 `"change": {"enum": ["added"]}`를 넣는다.

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_gx_arch_changes tests.test_gx_visualize_ir -v`
Expected: 모두 PASS.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/validate_ir.py .claude/skills/gx-visualize/schemas/gx-visual-ir.schema.json tests/test_gx_arch_changes.py
git diff --cached --stat
git commit -m "feat: IR에 이번 변경 표시 필드를 더한다"
```

---

### Task 2: 기준 시점 스캔과 비교해 변경을 판정한다

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/changes.py`
- Modify: `tests/test_gx_arch_changes.py` (클래스 추가)

**Interfaces:**
- Consumes: `scan_entrypoints.scan(project_root) -> {"nodes", "edges", "unresolved_edges", "files", "skipped"}` (기존), Task 1의 `change` 값.
- Produces:
  - `changes.compute_changes(project_root: Path | str, since_ref: str, head: dict) -> dict` — `head`(scan 결과)의 노드·엣지에 `change`를 **제자리에서** 단다. 반환: 성공 시 `{"available": True, "base_ref": str, "base_commit": str(7자), "added": int, "changed": int, "added_edges": int, "removed": [{"id", "kind", "label"}]}`, 실패 시 `{"available": False, "base_ref": str, "reason": str}`(이때 `head`는 건드리지 않는다).
  - `changes.mark_changes(head: dict, base: dict) -> dict` — 위 성공 반환값에서 `available`·`base_ref`·`base_commit`을 뺀 부분.
  - `changes.ChangeBaseError(RuntimeError)`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_gx_arch_changes.py`의 `if __name__ == "__main__":` 바로 위에 추가한다.

```python
GIT = shutil.which("git")

CONTROLLER_PATH = "src/main/java/com/sqi/user/controller/UserController.java"
SERVICE_PATH = "src/main/java/com/sqi/user/service/UserService.java"
MAPPER_PATH = "src/main/java/com/sqi/user/mapper/UserMapper.java"
MAPPER_SOURCE = "package com.sqi.user.mapper;\n\n@Mapper\npublic interface UserMapper {\n    String list();\n}\n"


def _controller(endpoints):
    methods = "".join(
        f'\n    @GetMapping("/{name}")\n    public String {name}() {{\n        return userService.list();\n    }}\n'
        for name in endpoints
    )
    return (
        'package com.sqi.user.controller;\n\n@RestController\n@RequestMapping("/api/users")\n'
        f"public class UserController {{\n    private final UserService userService;\n{methods}}}\n"
    )


def _service(with_mapper):
    field = "    private final UserMapper userMapper;\n" if with_mapper else ""
    return (
        "package com.sqi.user.service;\n\n@Service\n"
        f'public class UserService {{\n{field}    public String list() {{\n        return "";\n    }}\n}}\n'
    )


def _write(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root, *args):
    subprocess.run(
        [
            "git", "-c", "user.name=gx", "-c", "user.email=gx@example.com",
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args,
        ],
        cwd=root, check=True, capture_output=True,
    )


def _repo_on_feature_branch(root):
    """main에 컨트롤러(list)·서비스를 커밋하고 feature 브랜치로 옮겨 둔 저장소."""
    _git(root, "init", "-q")
    _git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    _write(root, CONTROLLER_PATH, _controller(["list"]))
    _write(root, SERVICE_PATH, _service(with_mapper=False))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "feature")


@unittest.skipUnless(GIT, "git not available on PATH")
class ChangeMarkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.changes = _load("changes")
        cls.scanner = _load("scan_entrypoints")

    def _compute(self, root, ref="main"):
        head = self.scanner.scan(root)
        return head, self.changes.compute_changes(root, ref, head)

    @staticmethod
    def _by_label(head):
        return {node["label"]: node for node in head["nodes"]}

    def test_new_endpoint_is_added_and_existing_one_is_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _write(root, CONTROLLER_PATH, _controller(["list", "detail"]))
            _git(root, "commit", "-q", "-am", "detail 추가")
            head, summary = self._compute(root)
        nodes = self._by_label(head)
        self.assertTrue(summary["available"])
        self.assertEqual(nodes["UserController.detail"].get("change"), "added")
        self.assertNotIn("change", nodes["UserController.list"])
        self.assertNotIn("change", nodes["UserService"])
        new_edges = [edge for edge in head["edges"] if edge.get("change") == "added"]
        self.assertEqual([edge["source"] for edge in new_edges], [nodes["UserController.detail"]["id"]])
        self.assertEqual((summary["added"], summary["changed"], summary["added_edges"]), (1, 0, 1))

    def test_service_with_a_new_collaborator_is_changed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _write(root, SERVICE_PATH, _service(with_mapper=True))
            _write(root, MAPPER_PATH, MAPPER_SOURCE)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "mapper 추가")
            head, summary = self._compute(root)
        nodes = self._by_label(head)
        self.assertEqual(nodes["UserService"].get("change"), "changed")
        self.assertEqual(nodes["UserMapper"].get("change"), "added")
        self.assertEqual(summary["changed"], 1)

    def test_uncommitted_work_counts_as_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _write(root, CONTROLLER_PATH, _controller(["list", "draft"]))  # 커밋하지 않는다
            head, _ = self._compute(root)
        self.assertEqual(self._by_label(head)["UserController.draft"].get("change"), "added")

    def test_removed_endpoint_is_reported_not_drawn(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _write(root, CONTROLLER_PATH, _controller([]))
            _git(root, "commit", "-q", "-am", "list 삭제")
            head, summary = self._compute(root)
        self.assertEqual([item["label"] for item in summary["removed"]], ["UserController.list"])
        self.assertNotIn("UserController.list", self._by_label(head))

    def test_line_shifts_alone_mark_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _write(root, CONTROLLER_PATH, "// 주석 한 줄\n\n" + _controller(["list"]))
            _git(root, "commit", "-q", "-am", "주석")
            head, summary = self._compute(root)
        self.assertEqual((summary["added"], summary["changed"], summary["added_edges"]), (0, 0, 0))
        self.assertFalse(any("change" in node for node in head["nodes"]))

    def test_project_root_below_the_repository_top_uses_the_same_subtree(self):
        # Review Focus 1: 접두 경로를 무시하면 기준 쪽 노드 ID가 "webapp-..."로 달라져 전부 신규가 된다.
        with tempfile.TemporaryDirectory() as temporary:
            top = Path(temporary)
            project = top / "webapp"
            _git(top, "init", "-q")
            _git(top, "symbolic-ref", "HEAD", "refs/heads/main")
            _write(project, CONTROLLER_PATH, _controller(["list"]))
            _write(project, SERVICE_PATH, _service(with_mapper=False))
            _git(top, "add", "-A")
            _git(top, "commit", "-q", "-m", "base")
            head, summary = self._compute(project)
        self.assertTrue(summary["available"])
        self.assertEqual((summary["added"], summary["changed"]), (0, 0))

    def test_korean_directory_names_survive_base_extraction(self):
        # Review Focus 2: 경로 인용(core.quotepath) 때문에 기준 트리에서 빠지면 그 화면이 신규로 오판된다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write(root, "webapp/게시판/list.jsp", '<form action="/api/users/list"></form>\n')
            _repo_on_feature_branch(root)
            head, summary = self._compute(root)
        screens = [node for node in head["nodes"] if node["kind"] == "screen"]
        self.assertEqual(len(screens), 1)
        self.assertNotIn("change", screens[0])
        self.assertEqual(summary["added"], 0)

    def test_unknown_ref_keeps_the_map_and_reports_why(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            head, summary = self._compute(root, ref="no-such-branch")
        self.assertFalse(summary["available"])
        self.assertIn("no-such-branch", summary["reason"])
        self.assertFalse(any("change" in node for node in head["nodes"]))

    def test_option_like_ref_is_rejected_before_reaching_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _, summary = self._compute(root, ref="--output=x")
        self.assertFalse(summary["available"])
        self.assertIn("기준 ref가 올바르지 않습니다", summary["reason"])

    def test_unrelated_history_has_no_common_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _git(root, "checkout", "-q", "--orphan", "other")
            _git(root, "commit", "-q", "-m", "orphan")
            _git(root, "checkout", "-q", "feature")
            _, summary = self._compute(root, ref="other")
        self.assertFalse(summary["available"])
        self.assertIn("merge-base", summary["reason"])

    def test_not_a_git_repository_reports_why(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write(root, CONTROLLER_PATH, _controller(["list"]))
            _, summary = self._compute(root)
        self.assertFalse(summary["available"])
        self.assertIn("rev-parse", summary["reason"])

    def test_base_extraction_does_not_touch_the_working_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repo_on_feature_branch(root)
            _write(root, CONTROLLER_PATH, _controller(["list", "draft"]))
            status = ["git", "status", "--porcelain"]
            before = subprocess.run(status, cwd=root, capture_output=True, text=True, check=True).stdout
            self._compute(root)
            after = subprocess.run(status, cwd=root, capture_output=True, text=True, check=True).stdout
        self.assertEqual(before, after)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_arch_changes -v`
Expected: `ChangeMarkingTests` 전부 ERROR — `FileNotFoundError`(changes.py 없음). Task 1 테스트는 PASS.

- [ ] **Step 3: 구현**

`.claude/skills/gx-visualize/scripts/changes.py`를 만든다. (2026-09-28 scratchpad 시제품으로 kereb 실제 이력에서 확인한 코드다 — 기준 `c8c2280~1`에서 `getVersionPeriod` API 등 신규 5개를 판정했고, kereb 작업 트리는 바뀌지 않았다.)

```python
#!/usr/bin/env python3
"""Mark what changed since a base ref by comparing two entrypoint scans.

이번 사이클에서 무엇이 새로 생기고 바뀌었는지를 줄 단위 diff가 아니라 **두 스캔의
비교**로 판정한다(설계서 §5.8.1). 노드 ID는 (종류, 경로, 심볼)로 정해지고 줄 번호를
포함하지 않으므로, 기준 시점 트리를 같은 스캐너로 한 번 더 스캔하면 새로 생긴
노드·관계가 ID 차집합으로 나온다. 줄 단위 diff는 컨트롤러 한 파일에 엔드포인트가
여럿일 때 파일 전체를 칠하거나, 선언 줄만 보면 새 호출 관계를 놓친다.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path
from typing import Any

SCANNED_SUFFIXES = (".java", ".jsp", ".xml")


class ChangeBaseError(RuntimeError):
    """기준 시점을 정할 수 없다 - 호출자는 변경 표시를 생략하고 이 메시지를 보고한다."""


def _scanner():
    path = Path(__file__).with_name("scan_entrypoints.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_scan_for_changes", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"스캐너를 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(cwd: Path | str, *args: str, stdin: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(["git", *args], cwd=str(cwd), input=stdin, capture_output=True, check=False)
    except OSError as exc:
        raise ChangeBaseError(f"git을 실행할 수 없습니다: {exc}") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip() or f"종료 코드 {result.returncode}"
        raise ChangeBaseError(f"git {args[0]} 실패: {message}")
    return result.stdout


def resolve_base(project_root: Path | str, since_ref: str) -> dict[str, str]:
    """`since_ref`와 HEAD의 공통 조상 커밋, 저장소 최상위, 프로젝트 루트의 접두 경로를 구한다."""
    # `-`로 시작하는 값은 git이 옵션으로 해석한다 - ref로 넘기지 않는다.
    if not since_ref or since_ref.startswith("-"):
        raise ChangeBaseError(f"기준 ref가 올바르지 않습니다: {since_ref!r}")
    root = Path(project_root).resolve()
    top = _git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    prefix = _git(root, "rev-parse", "--show-prefix").decode("utf-8").strip()
    commit = _git(root, "merge-base", since_ref, "HEAD").decode("utf-8").strip()
    return {"ref": since_ref, "commit": commit, "top": top, "prefix": prefix}


def extract_base_tree(base: dict[str, str], destination: Path) -> Path:
    """기준 커밋의 스캔 대상 소스만 `destination`에 꺼내고, 프로젝트 루트에 해당하는 경로를 반환한다.

    `git archive`는 pathspec 하나라도 매치가 없으면(예: JSP가 없는 프로젝트) 전체가
    실패한다. 그래서 목록은 `ls-tree -z`로 받아 파이썬에서 거르고(-z라 한국어 경로가
    인용되지 않는다), 내용은 `cat-file --batch` 프로세스 하나로 받는다 - 파일마다 git을
    띄우지 않는다. 작업 트리·인덱스는 건드리지 않는다.
    """
    top = base["top"]
    pathspec = [base["prefix"]] if base["prefix"] else []
    listing = _git(top, "ls-tree", "-r", "-z", "--name-only", base["commit"], "--", *pathspec)
    paths = [
        raw for raw in listing.split(b"\0")
        if raw and raw.decode("utf-8", errors="replace").endswith(SCANNED_SUFFIXES)
    ]
    destination = destination.resolve()
    if paths:
        request = b"".join(base["commit"].encode("ascii") + b":" + raw + b"\n" for raw in paths)
        data = _git(top, "cat-file", "--batch", stdin=request)
        offset = 0
        for raw in paths:
            header_end = data.index(b"\n", offset)
            header = data[offset:header_end].split(b" ")
            offset = header_end + 1
            if len(header) != 3 or header[1] != b"blob":
                continue  # missing·submodule 등 - 내용이 따라오지 않는다
            size = int(header[2])
            content = data[offset : offset + size]
            offset += size + 1  # 내용 뒤의 LF
            target = (destination / raw.decode("utf-8", errors="replace")).resolve()
            try:
                target.relative_to(destination)
            except ValueError:
                continue  # 트리 밖을 가리키는 경로는 쓰지 않는다
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            except (OSError, UnicodeError):
                continue
    project = destination / base["prefix"] if base["prefix"] else destination
    project.mkdir(parents=True, exist_ok=True)
    return project


def mark_changes(head: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """`head`의 노드·엣지에 `change`를 표시하고(제자리 수정) 요약을 반환한다.

    - 신규 노드: `head`에만 있는 ID
    - 변경 노드: 양쪽에 있고 `technical_label`(API의 HTTP 경로) 또는 나가는 엣지 ID 집합이 다름
    - 신규 엣지: `head`에만 있는 엣지 ID
    - 삭제: `base`에만 있는 테이블 외 노드 - 그릴 수 없으므로 목록으로만 돌려준다
    구조가 바뀐 것만 표시한다. 메서드 본문만 바뀐 경우는 그림이 달라지지 않는다.
    """
    base_nodes = {node["id"]: node for node in base.get("nodes", [])}
    base_edge_ids = {edge["id"] for edge in base.get("edges", [])}
    base_out: dict[str, set[str]] = {}
    for edge in base.get("edges", []):
        base_out.setdefault(edge["source"], set()).add(edge["id"])
    head_out: dict[str, set[str]] = {}
    for edge in head.get("edges", []):
        head_out.setdefault(edge["source"], set()).add(edge["id"])

    added = changed = 0
    for node in head.get("nodes", []):
        previous = base_nodes.get(node["id"])
        if previous is None:
            node["change"] = "added"
            added += 1
        elif previous.get("technical_label") != node.get("technical_label") or base_out.get(
            node["id"], set()
        ) != head_out.get(node["id"], set()):
            node["change"] = "changed"
            changed += 1

    added_edges = 0
    for edge in head.get("edges", []):
        if edge["id"] not in base_edge_ids:
            edge["change"] = "added"
            added_edges += 1

    head_ids = {node["id"] for node in head.get("nodes", [])}
    removed = [
        {"id": node["id"], "kind": node["kind"], "label": node["label"]}
        for node in base.get("nodes", [])
        if node["id"] not in head_ids and node.get("kind") != "table"
    ]
    return {"added": added, "changed": changed, "added_edges": added_edges, "removed": removed}


def compute_changes(project_root: Path | str, since_ref: str, head: dict[str, Any]) -> dict[str, Any]:
    """기준 시점 트리를 스캔해 `head`에 변경을 표시한다. 기준을 정할 수 없으면 표시 없이 이유를 반환한다."""
    try:
        base = resolve_base(project_root, since_ref)
        with tempfile.TemporaryDirectory(prefix="gx-visualize-base-") as temporary:
            base_scan = _scanner().scan(extract_base_tree(base, Path(temporary)))
    except ChangeBaseError as exc:
        return {"available": False, "base_ref": since_ref, "reason": str(exc)}
    summary = mark_changes(head, base_scan)
    return {"available": True, "base_ref": since_ref, "base_commit": base["commit"][:7], **summary}
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_gx_arch_changes -v`
Expected: 모두 PASS. `test_not_a_git_repository_reports_why`가 실패하면 임시 폴더가 다른 git 저장소 안에 있는지 확인한다(`git -C <tempdir> rev-parse --show-toplevel`). 그렇다면 실패를 BLOCKED로 보고한다 — 테스트를 약하게 고치지 않는다.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/changes.py tests/test_gx_arch_changes.py
git diff --cached --stat
git commit -m "feat: 기준 시점 스캔과 비교해 이번 변경을 판정한다"
```

---

### Task 3: `*Facade` 클래스를 서비스 계층으로 인식한다

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/scan_entrypoints.py:119` (`_class_kind`)
- Modify: `.claude/skills/gx-visualize/scripts/split_domains.py:16` (`LAYER_DIRS`)
- Modify: `.claude/skills/gx-visualize/references/entrypoint-rules.md`
- Create: `tests/fixtures/gx-arch-facade/src/main/java/com/sqi/reb/controller/RebController.java`
- Create: `tests/fixtures/gx-arch-facade/src/main/java/com/sqi/reb/facade/RebFacade.java`
- Create: `tests/fixtures/gx-arch-facade/src/main/java/com/sqi/reb/service/RebService.java`
- Create: `tests/fixtures/gx-arch-facade/src/main/java/com/sqi/reb/support/ExcelSupport.java`
- Modify: `tests/test_gx_arch_scan.py`, `tests/test_gx_arch_split.py`

**Interfaces:**
- Produces: 이름이 `Facade`로 끝나는 클래스는 `kind: "service"` 노드가 된다. `split_domains.LAYER_DIRS`에 `"facade"`가 들어간다.

배경: kereb reb 도메인의 컨트롤러 API 11개가 `@Component RebFacade`를 거쳐 서비스로 가는데, 이 클래스가 노드가 아니어서 11개 모두 고립됐다(설계서 §5.8.3).

- [ ] **Step 1: 픽스처 작성**

`RebController.java`:

```java
package com.sqi.reb.controller;

@RestController
@RequestMapping("/api/reb")
public class RebController {
    private final RebFacade rebFacade;
    private final ExcelSupport excelSupport;

    @GetMapping("/list")
    public String list() {
        return rebFacade.list();
    }
}
```

`RebFacade.java`:

```java
package com.sqi.reb.facade;

@Component
public class RebFacade {
    private final RebService rebService;

    public String list() {
        return rebService.list();
    }
}
```

`RebService.java`:

```java
package com.sqi.reb.service;

@Service
public class RebService {
    public String list() {
        return "";
    }
}
```

`ExcelSupport.java` (체인 밖 유틸 — 노드가 되면 안 된다):

```java
package com.sqi.reb.support;

@Component
public class ExcelSupport {
    public byte[] write() {
        return new byte[0];
    }
}
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_gx_arch_scan.py`의 `FIXTURE = ...` 줄 아래에 `FACADE_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-facade"`를 추가하고, 파일 끝 `if __name__` 위에 클래스를 추가한다.

```python
class FacadeScanTests(unittest.TestCase):
    def setUp(self):
        self.result = _module().scan(FACADE_FIXTURE)
        self.by_label = {node["label"]: node for node in self.result["nodes"]}

    def test_component_facade_becomes_a_service_node(self):
        self.assertEqual(self.by_label["RebFacade"]["kind"], "service")

    def test_chain_runs_through_the_facade(self):
        pairs = {(edge["source"], edge["target"]) for edge in self.result["edges"]}
        api = self.by_label["RebController.list"]["id"]
        facade = self.by_label["RebFacade"]["id"]
        service = self.by_label["RebService"]["id"]
        self.assertIn((api, facade), pairs)
        self.assertIn((facade, service), pairs)
        self.assertNotIn("RebFacade", {edge["target"] for edge in self.result["unresolved_edges"]})

    def test_other_component_utilities_stay_out_of_the_map(self):
        # D3: 진입점 체인만 - @Component 유틸까지 넣지 않는다.
        self.assertNotIn("ExcelSupport", self.by_label)
        self.assertIn("ExcelSupport", {edge["target"] for edge in self.result["unresolved_edges"]})
```

`tests/test_gx_arch_split.py`의 `split_by_domain = _module.split_by_domain` 아래에 추가한다.

```python
_scan_spec = importlib.util.spec_from_file_location(
    "gx_split_test_scan", REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "scan_entrypoints.py"
)
_scan_module = importlib.util.module_from_spec(_scan_spec)
_scan_spec.loader.exec_module(_scan_module)
FACADE_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-facade"
```

그리고 도메인 테스트 클래스(`test_domain_is_segment_before_layer_dir`가 있는 클래스) 안에 추가한다.

```python
    def test_facade_folder_is_a_layer_not_a_domain(self):
        self.assertEqual(domain_of("src/main/java/com/sqi/reb/facade/RebFacade.java"), "reb")

    def test_facade_chain_stays_in_its_domain(self):
        # facade를 계층으로 보지 않으면 "facade" 가짜 도메인이 생겨 api→facade 엣지가 잘린다.
        result = _scan_module.scan(FACADE_FIXTURE)
        ir = {"schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
              "nodes": result["nodes"], "edges": result["edges"]}
        parts = split_by_domain(ir)
        self.assertEqual(sorted(parts), ["reb"])
        self.assertNotIn("cross-domain-edge", parts["reb"]["missing_inputs"])
```

- [ ] **Step 3: 실패 확인**

Run: `python -m unittest tests.test_gx_arch_scan tests.test_gx_arch_split -v`
Expected: `test_component_facade_becomes_a_service_node`는 `KeyError: 'RebFacade'`, `test_chain_runs_through_the_facade`도 `KeyError`, `test_facade_folder_is_a_layer_not_a_domain`는 `'facade' != 'reb'`, `test_facade_chain_stays_in_its_domain`는 `['reb'] != [...]` 또는 KeyError로 실패. `test_other_component_utilities_stay_out_of_the_map`는 PASS.

- [ ] **Step 4: 구현**

`scan_entrypoints.py`의 `_class_kind`에서

```python
        if name.endswith(("Service", "ServiceImpl")):
            return "service"
```

를 다음으로 바꾼다.

```python
        # Facade는 컨트롤러와 여러 서비스 사이의 계층이다(kereb reb: Controller → RebFacade
        # → 서비스들). 노드가 아니면 그 뒤 체인 전체가 컨트롤러에서 끊긴다. @Component에는
        # 유틸도 많으므로 어노테이션이 아니라 이름으로 한정한다(설계서 §5.8.3, D3).
        if name.endswith(("Service", "ServiceImpl", "Facade")):
            return "service"
```

`split_domains.py`의 `LAYER_DIRS`를 다음으로 바꾼다.

```python
LAYER_DIRS = ("controller", "service", "facade", "repository", "dao", "mapper", "web", "api")
```

`references/entrypoint-rules.md`의 표에서 service 행을

```markdown
| `service` | `@Service` 클래스, 이름이 `*Facade`인 클래스 | `*Service`·`*ServiceImpl`·`*Facade` 클래스 |
```

로 바꾸고, `## edge relation 값` 절 바로 앞에 다음 단락을 넣는다.

```markdown
**Facade.** 컨트롤러와 여러 서비스 사이에 `@Component` Facade를 두는 구조가 있다(kereb reb: `RebController → RebFacade → 서비스들`). Facade가 노드가 아니면 컨트롤러 API가 모두 고립된다. `@Component`에는 유틸(엑셀 헬퍼 등)도 많아 어노테이션으로는 가를 수 없으므로 **이름이 `Facade`로 끝나는 클래스만** 서비스 계층으로 본다. `facade` 폴더는 `controller`·`service`처럼 계층 폴더로 취급한다 — 도메인은 그 앞 세그먼트다.
```

- [ ] **Step 5: 통과 확인**

Run: `python -m unittest tests.test_gx_arch_scan tests.test_gx_arch_split -v`
Expected: 모두 PASS.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/scan_entrypoints.py .claude/skills/gx-visualize/scripts/split_domains.py .claude/skills/gx-visualize/references/entrypoint-rules.md tests/fixtures/gx-arch-facade tests/test_gx_arch_scan.py tests/test_gx_arch_split.py
git diff --cached --stat
git commit -m "fix: Facade 클래스를 서비스 계층으로 인식해 끊긴 체인을 잇는다"
```

---

### Task 4: Archify 변환에 변경 표시를 넣고 열 간격을 넓힌다

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/to_archify.py`
- Modify: `tests/test_gx_arch_archify.py`

**Interfaces:**
- Consumes: Task 1의 `change` 값.
- Produces: `to_archify.CHANGE_PREFIX = {"added": "[신규] ", "changed": "[변경] "}`. 변경된 노드의 컴포넌트 `label`은 접두사가 붙은 문자열이고, 신규 엣지의 connection은 `"variant": "emphasis"`를 갖는다. 레이아웃은 `cellW = max(150, maxWidth - gapX + 40)`.

배경(2026-09-28 실측, 설계서 §5.8.2·§5.8.3):
- Archify `tag` 필드는 검증은 통과하지만, `sources`가 있는 컴포넌트에서는 화면에 보이지 않았다. 그래서 라벨 접두사를 쓴다.
- 기존 `+ 8`은 겹치지 않을 만큼만 보장해서, 넓은 컴포넌트 옆 연결선이 8~23px로 짧아졌다(`Connection too short`, 최소 24px). `+ 40`으로 바꾸자 user 도메인이 Archify 통과로 바뀌었고, 기존 통과 6개 도메인도 그대로 통과했다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_gx_arch_archify.py` 상단 상수 아래에 추가한다.

```python
ARCHIFY_MJS = Path.home() / ".agents" / "skills" / "archify" / "bin" / "archify.mjs"


def _fan_in_ir():
    """kereb user 도메인 모양: API 8개가 서비스 하나로 모이고, 매퍼가 테이블 둘을 읽고 쓴다."""
    nodes = []
    for index in range(8):
        node = {
            "id": f"gx-api-{index}", "kind": "api", "status": "unknown",
            "label": f"UserAdminController.updateUserStatus{index}",
            "technical_label": f"POST /adm/v1/users/{{userId}}/update-status-{index}",
        }
        if index == 0:
            node["change"] = "added"
        nodes.append(node)
    nodes += [
        {"id": "gx-service-user", "kind": "service", "label": "UserService", "status": "unknown", "change": "changed"},
        {"id": "gx-repository-user", "kind": "repository", "label": "UserMapper", "status": "unknown"},
        {"id": "gx-table--TB_USER", "kind": "table", "label": "TB_USER", "technical_label": "TB_USER", "status": "unknown"},
        {"id": "gx-table--TB_ROLE", "kind": "table", "label": "TB_ROLE", "technical_label": "TB_ROLE", "status": "unknown"},
    ]
    edges = [
        {"id": f"gx-api-{index}->gx-service-user:calls", "source": f"gx-api-{index}",
         "target": "gx-service-user", "relation": "calls"}
        for index in range(8)
    ]
    edges[0]["change"] = "added"
    edges += [
        {"id": "gx-service-user->gx-repository-user:calls", "source": "gx-service-user",
         "target": "gx-repository-user", "relation": "calls"},
        {"id": "gx-repository-user->gx-table--TB_USER:reads", "source": "gx-repository-user",
         "target": "gx-table--TB_USER", "relation": "reads"},
        {"id": "gx-repository-user->gx-table--TB_USER:writes", "source": "gx-repository-user",
         "target": "gx-table--TB_USER", "relation": "writes"},
        {"id": "gx-repository-user->gx-table--TB_ROLE:reads", "source": "gx-repository-user",
         "target": "gx-table--TB_ROLE", "relation": "reads"},
    ]
    return {"schema_version": 1, "view": "service", "locale": "ko-KR", "title": "user 도메인 구조",
            "nodes": nodes, "edges": edges}
```

`ToArchifyTests` 클래스 안에 추가한다.

```python
    def test_added_and_changed_nodes_carry_a_visible_label_prefix(self):
        ir = _ir_with_label("UserController.list")
        ir["nodes"][0]["change"] = "added"
        component = self.to_archify(ir, "architecture")[NODE_KEY][0]
        self.assertEqual(component["label"], "[신규] UserController.list")
        self.assertNotIn("tag", component)  # tag는 sources가 있으면 화면에 보이지 않는다
        ir["nodes"][0]["change"] = "changed"
        self.assertEqual(self.to_archify(ir, "architecture")[NODE_KEY][0]["label"], "[변경] UserController.list")

    def test_prefix_is_counted_in_the_component_width(self):
        ir = _ir_with_label("가" * 14)
        plain = self.to_archify(ir, "architecture")[NODE_KEY][0]["size"][0]
        ir["nodes"][0]["change"] = "added"
        marked = self.to_archify(ir, "architecture")[NODE_KEY][0]["size"][0]
        self.assertGreater(marked, plain)

    def test_added_edges_are_emphasized_and_others_are_not(self):
        ir = {
            "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
            "nodes": [
                {"id": "a", "kind": "api", "label": "A.x", "status": "unknown"},
                {"id": "b", "kind": "service", "label": "B", "status": "unknown"},
                {"id": "c", "kind": "service", "label": "C", "status": "unknown"},
            ],
            "edges": [
                {"id": "a->b:calls", "source": "a", "target": "b", "relation": "calls", "change": "added"},
                {"id": "a->c:calls", "source": "a", "target": "c", "relation": "calls"},
            ],
        }
        connections = self.to_archify(ir, "architecture")[EDGE_KEY]
        self.assertEqual([connection.get("variant") for connection in connections], ["emphasis", None])
```

기존 `test_very_long_label_widens_grid_step_to_keep_separation`의 주석과 단언을 다음으로 바꾼다.

```python
    def test_very_long_label_widens_grid_step_to_keep_separation(self):
        # 열 사이 간격이 8px뿐이면 연결선이 Archify 최소 길이(24px)보다 짧아지고 관계
        # 라벨이 박스와 겹친다(2026-09-28 실측: user 도메인·세션 그래프). 40px을 보장한다.
        ir = _ir_with_label("가" * 25)
        out = self.to_archify(ir, "architecture")
        layout = out["layout"]
        for component in out[NODE_KEY]:
            width = component["size"][0] if "size" in component else 120
            self.assertGreaterEqual(layout["cellW"] + layout["gapX"] - width, 40)
```

파일 끝 `if __name__` 위에 실제 Archify 테스트 클래스를 추가한다.

```python
@unittest.skipUnless(ARCHIFY_MJS.is_file() and shutil.which("node"), "real Archify not installed")
class RealArchifyLayoutTests(unittest.TestCase):
    """가짜 실행 파일로는 레이아웃 규칙을 잡을 수 없다 - 실제 Archify 검증기로 확인한다.

    2026-09-28 실측: 이 모양(API 8개 → 서비스 1개, [신규]·[변경] 라벨)은 열 간격 8px에서
    clean-flow/edge-through-node·endpoint-side-direction으로 실패하고 40px에서 통과한다.
    """

    def test_fan_in_domain_with_change_marks_passes_real_validation(self):
        spec = importlib.util.spec_from_file_location("gx_to_archify_real", TO_ARCHIFY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = module.to_archify(_fan_in_ir(), "architecture")
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "user.archify.json"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [shutil.which("node"), str(ARCHIFY_MJS), "validate", "architecture", str(path), "--json"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout[-3000:])
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: `test_added_and_changed_nodes_carry_a_visible_label_prefix`(`'UserController.list' != '[신규] ...'`), `test_prefix_is_counted_in_the_component_width`(`not greater`), `test_added_edges_are_emphasized_and_others_are_not`(`[None, None]`), `test_very_long_label_widens_grid_step_to_keep_separation`(`8 not >= 40`)가 FAIL. Archify가 설치된 이 기계에서는 `test_fan_in_domain_with_change_marks_passes_real_validation`도 `1 != 0`으로 FAIL해야 한다 — **PASS하거나 SKIP되면 멈추고 보고한다**(실측과 다르다는 뜻이다).

- [ ] **Step 3: 구현**

`to_archify.py`에서 `_DEFAULT_LAYOUT` 위의 주석 블록과 상수를 다음으로 바꾼다.

```python
# 그리드 칸 간격 기본값. 같은 행에서 옆 열까지의 폭(stepX = cellW + gapX)이 컴포넌트
# 폭보다 _MIN_COLUMN_GAP 이상 넉넉해야 한다. renderers/architecture/render-architecture.mjs의
# rectsOverlap(a, b, 8)만 피하면(8px) 연결선이 Archify 최소 길이(24px)보다 짧아지고 관계
# 라벨이 박스와 겹친다 - 2026-09-28 실측으로 kereb user 도메인과 세션 그래프가 이 때문에
# 실패했고, 40px에서 통과했다(설계서 §5.8.3).
_DEFAULT_LAYOUT = {"mode": "grid", "cols": 5, "gapX": 90, "gapY": 50, "cellW": 150, "cellH": 64}
_MIN_COLUMN_GAP = 40
```

`_RELATION_LABEL_KO` 정의 바로 위에 추가한다.

```python
# 이번 변경 표시(설계서 §5.8.2). Archify의 `tag`는 검증은 통과하지만 sources가 있는
# 컴포넌트에서는 화면에 보이지 않았다(2026-09-28 헤드리스 캡처) - 라벨 접두사로 표시한다.
CHANGE_PREFIX = {"added": "[신규] ", "changed": "[변경] "}
```

`_component` 함수의 앞부분을 다음으로 바꾼다(나머지는 그대로).

```python
def _component(node: dict[str, Any], row: int, col: int, include_sources: bool) -> dict[str, Any]:
    label = CHANGE_PREFIX.get(node.get("change"), "") + node["label"]
    component: dict[str, Any] = {
        "id": node["id"],
        "type": KIND_TO_TYPE.get(node.get("kind"), "external"),
        "label": label,
        "row": row,
        "col": col,
    }
    # technical_label이 label과 같으면(예: 테이블 노드는 둘 다 테이블명) 같은 이름을
    # sublabel로 또 찍지 않는다 - 폭 계산도 실제로 찍히는 값 기준으로 맞춘다.
    technical_label = node.get("technical_label")
    sublabel = technical_label if technical_label is not None and technical_label != node["label"] else ""
    size = _component_size(label, sublabel)
```

`_connection`에서 `connection["label"] = ...` 두 줄 바로 아래에 추가한다.

```python
    if edge.get("change") == "added":
        connection["variant"] = "emphasis"
```

`to_archify`에서

```python
    required_cell_w = max_width - layout["gapX"] + _LABEL_FIT_MARGIN
```

를 다음으로 바꾼다.

```python
    required_cell_w = max_width - layout["gapX"] + _MIN_COLUMN_GAP
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: 모두 PASS(실제 Archify 테스트 포함).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/to_archify.py tests/test_gx_arch_archify.py
git diff --cached --stat
git commit -m "fix: Archify 열 간격을 넓히고 변경 표시를 라벨 접두사로 넣는다"
```

---

### Task 5: 렌더러가 변경을 그리고, 세션 스냅샷 배너를 없앤다

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/render_fallback.py`
- Modify: `.claude/skills/gx-visualize/scripts/render_archify.py`
- Modify: `.claude/skills/gx-visualize/templates/fallback.css`
- Modify: `tests/test_gx_visualize_fallback.py`, `tests/test_gx_visualize_backend.py`

**Interfaces:**
- Consumes: Task 1의 `change` 값, IR의 `meta.changes = {"available": bool, "base_ref": str, "base_commit": str, "reason": str}`(Task 7이 채운다).
- Produces:
  - `render_fallback.CHANGE_LABELS = {"added": "신규", "changed": "변경"}` — Task 6이 재사용한다.
  - `render_fallback.change_banner_html(ir: dict) -> str` — `meta.changes.available`이 참이 아니면 `""`.
  - `render_fallback.inject_banner(document: str, banner_html: str) -> str` — 기존 `inject_snapshot_banner`의 새 이름.
  - `render_fallback.render(ir_path, output_dir, backend, project_root=None, output_name=None, html_dir=None, mermaid_asset_href=None)` — `snapshot_banner` 인자 없음.
  - `render_archify.render_archify(ir_path, output_dir, archify_command=None, project_root=None, output_name=None, html_dir=None, mermaid_asset_href=None)` — `snapshot_banner` 인자 없음.
- 삭제: `snapshot_banner_html`, `inject_snapshot_banner`, 모든 `snapshot_banner` 인자, 두 CLI의 `--snapshot-banner`. `--scope session`이 사라지므로 쓰는 곳이 없다.

- [ ] **Step 1: 실패하는 테스트 작성 — 폴백 렌더러**

`tests/test_gx_visualize_fallback.py`에서 `test_snapshot_banner_is_absent_by_default`, `test_snapshot_banner_carries_the_three_required_facts`, `test_snapshot_banner_includes_short_head_in_a_git_project`, `test_snapshot_banner_is_inserted_right_after_the_body_tag` 네 테스트를 지우고, 그 자리에 추가한다.

```python
    CHANGES_META = {"changes": {"available": True, "base_ref": "main", "base_commit": "abc1234"}}

    def marked_ir(self, root, meta=None):
        nodes = [
            {"id": "A-new", "kind": "api", "label": "새 API", "status": "unknown", "evidence": [], "change": "added"},
            {"id": "B-old", "kind": "service", "label": "기존 서비스", "status": "unknown", "evidence": []},
            {"id": "C-changed", "kind": "repository", "label": "바뀐 저장소", "status": "unknown", "evidence": [], "change": "changed"},
        ]
        edges = [
            {"id": "A-new->B-old:calls", "source": "A-new", "target": "B-old", "relation": "calls", "change": "added"},
            {"id": "B-old->C-changed:calls", "source": "B-old", "target": "C-changed", "relation": "calls"},
        ]
        overrides = {"view": "service", "nodes": nodes, "edges": edges}
        if meta is not None:
            overrides["meta"] = meta
        return self.write_ir(root, **overrides)[0]

    def test_change_marks_render_as_badges_and_a_table_column(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render(self.marked_ir(root), root / "out", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
        self.assertIn('<span class="change change-added">신규</span>', html_text)
        self.assertIn('<span class="change change-changed">변경</span>', html_text)
        self.assertIn("<th>이번 변경</th>", html_text)

    def test_mermaid_source_colors_new_nodes_and_thickens_new_edges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render(self.marked_ir(root), root / "out", "mermaid")
            source = self.mermaid_source(Path(result["html_path"]).read_text(encoding="utf-8"))
        # 노드는 ID 순(A-new=n0, B-old=n1, C-changed=n2), 엣지도 ID 순이다.
        self.assertIn('n0["[신규]#10;새 API"]', source)
        self.assertIn("class n0 gxAdded", source)
        self.assertIn("class n2 gxChanged", source)
        self.assertIn("linkStyle 0 stroke:#15803d,stroke-width:3px", source)
        self.assertNotIn("linkStyle 1", source)
        self.assertNotRegex(source, r"classDef[^\n]*;")  # Mermaid 엔티티(#..;)로 오인되지 않게

    def test_change_banner_appears_only_when_marking_was_requested(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marked = self.renderer.render(self.marked_ir(root, meta=self.CHANGES_META), root / "a", "static")
            marked_html = Path(marked["html_path"]).read_text(encoding="utf-8")
            plain = self.renderer.render(self.marked_ir(root), root / "b", "static")
            plain_html = Path(plain["html_path"]).read_text(encoding="utf-8")
        self.assertIn("기준 main (abc1234) 이후 신규 1개 · 변경 1개", marked_html)
        self.assertNotIn("change-banner", plain_html)

    def test_change_banner_says_so_when_a_domain_did_not_change(self):
        ir = {"nodes": [{"id": "a", "label": "x"}], "meta": self.CHANGES_META}
        self.assertIn("구조 변경이 없습니다", self.renderer.change_banner_html(ir))
        skipped = {"nodes": [], "meta": {"changes": {"available": False, "reason": "git 아님"}}}
        self.assertEqual(self.renderer.change_banner_html(skipped), "")

    def test_banner_is_inserted_right_after_the_body_tag(self):
        injected = self.renderer.inject_banner("<html><body><p>본문</p></body></html>", "<p>배너</p>")
        self.assertEqual("<html><body><p>배너</p><p>본문</p></body></html>", injected)

    def test_snapshot_banner_is_gone(self):
        self.assertFalse(hasattr(self.renderer, "snapshot_banner_html"))
        self.assertNotIn("snapshot_banner", self.renderer.render.__code__.co_varnames)
```

- [ ] **Step 2: 실패하는 테스트 작성 — Archify 렌더러**

`tests/test_gx_visualize_backend.py`에서 `test_archify_success_html_carries_snapshot_banner_when_requested`를 다음으로 바꾼다.

```python
    def test_archify_success_html_carries_change_banner_when_ir_has_changes(self):
        # Archify가 만든 HTML은 이 스킬의 배너를 모른다 - render_archify()가 전달 후 넣는다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir = json.loads(SERVICE_FIXTURE.read_text(encoding="utf-8"))
            ir["nodes"][0]["change"] = "added"
            ir["meta"] = {"changes": {"available": True, "base_ref": "main", "base_commit": "abc1234"}}
            ir_path = root / SERVICE_FIXTURE.name  # 근거가 자기 파일명을 가리키므로 이름을 유지한다
            ir_path.write_text(json.dumps(ir, ensure_ascii=False), encoding="utf-8")
            result = self.renderer.render_archify(ir_path, root / "output", self.fake_archify(root))
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["backend"], "archify")
        self.assertIn("신규 1개", html_text)
        self.assertIn("Archify 결과", html_text)
```

같은 파일의 `test_mermaid_failure_continues_to_static_and_keeps_archify_failure` 안의 가짜 함수를 다음으로 바꾼다.

```python
            def render_or_fail(
                ir_path, output_dir, backend, output_name=None, html_dir=None, mermaid_asset_href=None,
            ):
                if backend == "mermaid":
                    raise RuntimeError("mermaid unavailable")
                return real_fallback(
                    ir_path, output_dir, backend, output_name=output_name,
                    html_dir=html_dir, mermaid_asset_href=mermaid_asset_href,
                )
```

- [ ] **Step 3: 실패 확인**

Run: `python -m unittest tests.test_gx_visualize_fallback tests.test_gx_visualize_backend -v`
Expected: 새 테스트들이 FAIL 또는 ERROR(`AttributeError: ... 'change_banner_html'`, `'inject_banner'`, 배지 없음), `test_snapshot_banner_is_gone`은 FAIL. `test_mermaid_failure_continues_to_static_and_keeps_archify_failure`는 `TypeError: ... unexpected keyword argument 'snapshot_banner'`로 ERROR.

- [ ] **Step 4: 폴백 렌더러 구현**

`render_fallback.py`:

1. `from datetime import datetime` 줄을 지운다(스냅샷 배너만 썼다).
2. `EVIDENCE_LABELS` 정의 바로 아래에 추가한다.

```python
# 이번 변경 표시(설계서 §5.8.2). 노드 배지·Mermaid 라벨·관계 표·인덱스가 같은 단어를 쓴다.
CHANGE_LABELS = {"added": "신규", "changed": "변경"}
```

3. `_status_badge` 함수 바로 아래에 추가한다.

```python
def _change_badge(change: Any) -> str:
    label = CHANGE_LABELS.get(change) if isinstance(change, str) else None
    if label is None:
        return ""
    return f'<span class="change change-{_escape(change)}">{_escape(label)}</span>'
```

4. `_node_list`의 `cards.append(...)`에서 `f'{status_html}'` 줄을 `f'{_change_badge(node.get("change"))}{status_html}'`로 바꾼다.

5. `_relationship_table` 전체를 다음으로 바꾼다.

```python
def _relationship_table(edges: list[dict[str, Any]]) -> str:
    rows = "".join(
        "<tr>"
        f'<td><code>{_escape(edge["id"])}</code></td>'
        f'<td><code>{_escape(edge["source"])}</code></td>'
        f'<td>{_escape(edge["relation"])}</td>'
        f'<td><code>{_escape(edge["target"])}</code></td>'
        f'<td>{_escape(CHANGE_LABELS.get(edge.get("change"), ""))}</td>'
        "</tr>"
        for edge in edges
    )
    if not rows:
        rows = '<tr><td colspan="5">표시할 관계가 없습니다.</td></tr>'
    return (
        '<section aria-labelledby="relations-title"><h2 id="relations-title">관계</h2>'
        '<div class="table-wrap"><table><thead><tr><th>관계 ID</th><th>출발</th><th>관계</th><th>도착</th><th>이번 변경</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div></section>'
    )
```

6. `_mermaid_source` 전체를 다음으로 바꾼다.

```python
def _mermaid_source(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]], suppress_unknown_status: bool
) -> str:
    aliases = {node["id"]: f"n{index}" for index, node in enumerate(nodes)}
    lines = ["flowchart LR"]
    for node in nodes:
        # 노드 ID는 넣지 않는다 - 노드 목록 카드에 이미 있고, 여기 넣으면 라벨이 긴
        # 기술 ID로 시작해 실제 이름을 가린다(버그 B, 2026-09-21 컨트롤러가 reb.html에서
        # 발견: "gx-api-webframework-public-src-main-java-..."가 라벨 맨 앞에 왔다).
        change_label = CHANGE_LABELS.get(node.get("change"))
        label_parts = [f"[{change_label}]"] if change_label else []
        label_parts.append(node["label"])
        technical = node.get("technical_label")
        if technical is not None and technical != node["label"]:
            label_parts.append(technical)
        # service 뷰에서만 unknown 상태를 라벨에서 뺀다 - _node_list()와 같은 기준.
        if not (suppress_unknown_status and node["status"] == "unknown"):
            label_parts.append(STATUS_LABELS[node["status"]])
        label = "#10;".join(_mermaid_text(part) for part in label_parts)
        lines.append(f'  {aliases[node["id"]]}["{label}"]')
    for edge in edges:
        relation = _mermaid_text(edge["relation"])
        lines.append(f'  {aliases[edge["source"]]} -->|{relation}| {aliases[edge["target"]]}')
    # 이번 변경 표시 - 채움색은 classDef, 새 관계는 linkStyle 순번으로 굵게 한다. 줄 끝에
    # `;`를 붙이지 않는다: `#15803d;` 같은 꼴은 Mermaid가 엔티티로 해석한다.
    added = [aliases[node["id"]] for node in nodes if node.get("change") == "added"]
    changed = [aliases[node["id"]] for node in nodes if node.get("change") == "changed"]
    if added:
        lines.append("  classDef gxAdded fill:#dcfce7,stroke:#15803d,stroke-width:3px,color:#14532d")
        lines.append(f"  class {','.join(added)} gxAdded")
    if changed:
        lines.append("  classDef gxChanged fill:#fef3c7,stroke:#b45309,stroke-width:3px,color:#78350f")
        lines.append(f"  class {','.join(changed)} gxChanged")
    for index, edge in enumerate(edges):
        if edge.get("change") == "added":
            lines.append(f"  linkStyle {index} stroke:#15803d,stroke-width:3px")
    return "\n".join(lines)
```

7. `snapshot_banner_html`과 `inject_snapshot_banner` 두 함수를 지우고, 그 자리에 추가한다(`_short_head`는 build_index가 쓰므로 남긴다).

```python
def change_banner_html(ir: dict[str, Any]) -> str:
    """`meta.changes`가 켜진 IR에 '이번 변경' 배너를 만든다. 표시가 꺼져 있으면 빈 문자열.

    Archify가 만든 HTML에도 같은 배너를 넣으므로(render_archify) fallback.css에 기대지 않고
    인라인 스타일만 쓴다. 변경이 없는 도메인에도 배너를 넣는다 - 표시 기능이 켜져 있었다는
    사실이 보여야 '표시 없음'을 '변경 없음'으로 읽을 수 있다(설계서 §5.8.2).
    """
    meta = ir.get("meta")
    changes = meta.get("changes") if isinstance(meta, dict) else None
    if not isinstance(changes, dict) or not changes.get("available"):
        return ""
    nodes = ir.get("nodes", [])
    added = sum(1 for node in nodes if node.get("change") == "added")
    changed = sum(1 for node in nodes if node.get("change") == "changed")
    base = f'{changes.get("base_ref", "")} ({changes.get("base_commit", "")})'
    if added or changed:
        text = f"이번 변경 — 기준 {base} 이후 신규 {added}개 · 변경 {changed}개. 그림의 [신규]·[변경] 표시와 굵은 선을 확인하세요."
        colors = "background:#dcfce7;color:#14532d;"
    else:
        text = f"이번 변경 — 기준 {base} 이후 이 도메인에는 구조 변경이 없습니다."
        colors = "background:#f1f5f9;color:#334155;"
    return (
        f'<p class="change-banner" role="note" style="margin:0;padding:10px 16px;{colors}'
        f'font:600 14px/1.5 system-ui,sans-serif;">{_escape(text)}</p>'
    )


def inject_banner(document: str, banner_html: str) -> str:
    """Insert `banner_html` right after the opening `<body>` tag of `document`.

    render()와 render_archify.render_archify()가 이 함수를 공유해 폴백 산출물과 Archify
    산출물 양쪽에 같은 방식으로 배너를 붙인다 - 렌더러마다 다른 HTML 구조에 각자 배너
    절차를 만들지 않는다.
    """
    match = _BODY_TAG_RE.search(document)
    if match is None:
        return document
    return document[: match.end()] + banner_html + document[match.end() :]
```

8. `render` 함수의 시그니처와 docstring의 `snapshot_banner` 단락, 끝부분을 다음으로 바꾼다.

```python
def render(
    ir_path: Path | str,
    output_dir: Path | str,
    backend: str,
    project_root: Path | str | None = None,
    output_name: str | None = None,
    html_dir: Path | str | None = None,
    mermaid_asset_href: str | None = None,
) -> dict[str, str]:
```

docstring에서 "`snapshot_banner`, when true, ..."로 시작하는 단락 전체를 다음 단락으로 바꾼다.

```text
    IR에 `meta.changes`가 켜져 있으면 '이번 변경' 배너(change_banner_html)를 `<body>` 바로
    뒤에 넣는다. 인자가 아니라 IR 데이터가 배너를 정한다 - build_map.py가 변경 표시를
    요청한 실행에서만 meta.changes를 채운다.
```

본문 끝의

```python
    document = _render_document(ir, backend, mermaid_asset_href=mermaid_asset_href)
    if snapshot_banner:
        document = inject_snapshot_banner(document, snapshot_banner_html(project_root))
```

를 다음으로 바꾼다.

```python
    document = _render_document(ir, backend, mermaid_asset_href=mermaid_asset_href)
    banner = change_banner_html(ir)
    if banner:
        document = inject_banner(document, banner)
```

9. `main`에서 `parser.add_argument("--snapshot-banner", action="store_true")` 줄과, `render(...)` 호출의 `snapshot_banner=args.snapshot_banner,`를 지운다. 호출은 다음이 된다.

```python
        result = render(
            args.ir_path, args.output_dir, args.backend,
            project_root=args.project_root, output_name=args.output_name,
            html_dir=args.html_dir, mermaid_asset_href=args.mermaid_asset_href,
        )
```

- [ ] **Step 5: Archify 렌더러 구현**

`render_archify.py`에서 `snapshot_banner`를 모두 없앤다. 끝나면 `grep -n snapshot .claude/skills/gx-visualize/scripts/render_archify.py`의 결과가 0줄이어야 한다.

`_render_fallback` 전체:

```python
def _render_fallback(
    ir_path: Path,
    output_dir: Path,
    backend: str,
    project_root: Path | str | None = None,
    output_name: str | None = None,
    html_dir: Path | str | None = None,
    mermaid_asset_href: str | None = None,
) -> dict[str, str]:
    return _fallback_module().render(
        ir_path, output_dir, backend,
        project_root=project_root, output_name=output_name,
        html_dir=html_dir, mermaid_asset_href=mermaid_asset_href,
    )
```

`_fallback`의 시그니처에서 `snapshot_banner: bool = False,` 줄을 지우고, 안의 두 `_render_fallback(...)` 호출을 다음으로 바꾼다.

```python
            if project_root is None:
                result = _render_fallback(
                    ir_path, output_dir, backend, output_name=output_name,
                    html_dir=html_dir, mermaid_asset_href=backend_asset_href,
                )
            else:
                result = _render_fallback(
                    ir_path, output_dir, backend,
                    project_root=project_root, output_name=output_name,
                    html_dir=html_dir, mermaid_asset_href=backend_asset_href,
                )
```

`_skip_archify`의 시그니처에서 `snapshot_banner: bool = False,`를 지우고, 끝의 호출을 다음으로 바꾼다.

```python
    return _fallback(
        ir_path, output_dir, receipt_path, attempts,
        project_root=project_root, status="not_applicable", output_name=output_name,
        html_dir=html_dir, mermaid_asset_href=mermaid_asset_href,
    )
```

`render_archify`의 시그니처에서 `snapshot_banner: bool = False,`를 지우고, docstring의 "`snapshot_banner`, when true, ..." 단락(4줄)을 다음으로 바꾼다.

```text
    IR에 `meta.changes`가 켜져 있으면 Archify가 만든 HTML에도 '이번 변경' 배너를 넣는다 -
    Archify는 이 배너를 모르므로 전달 후 render_fallback.inject_banner()로 삽입한다.
```

본문의 `_skip_archify(...)`, 두 `_fallback(...)` 호출(발견 실패·validate 실패), deliver 실패 뒤 `_fallback(...)` 호출에서 `snapshot_banner=snapshot_banner, `를 지운다. 예를 들어 validate 실패 호출은 다음이 된다.

```python
        return _fallback(
            ir_path, output_dir, receipt_path, attempts,
            project_root=project_root, output_name=output_name,
            html_dir=html_dir, mermaid_asset_href=mermaid_asset_href,
        )
```

Archify 성공 경로의 `if snapshot_banner:` 블록 전체를 다음으로 바꾼다.

```python
    # Archify HTML은 이 스킬의 변경 표시 배너를 모른다 - 전달 후 직접 삽입한다.
    # render_fallback.render()와 같은 함수라 두 경로의 배너가 같다(설계서 §5.8.2).
    fallback_module = _fallback_module()
    banner = fallback_module.change_banner_html(ir_document)
    if banner:
        html_path.write_text(
            fallback_module.inject_banner(html_path.read_text(encoding="utf-8"), banner),
            encoding="utf-8",
        )
```

`main`에서 `parser.add_argument("--snapshot-banner", action="store_true")`와 `snapshot_banner=args.snapshot_banner,`를 지운다.

- [ ] **Step 6: CSS**

`templates/fallback.css`의 `.status-planned, .status-unknown { ... }` 줄 바로 아래에 추가한다.

```css
.change { display: inline-block; border-radius: 999px; padding: 2px 9px; margin-right: 6px; font-size: .85rem; font-weight: 800; }
.change-added { background: #dcfce7; color: #14532d; }
.change-changed { background: #fef3c7; color: #78350f; }
.domain-card.domain-changed { box-shadow: 0 0 0 3px #86efac; }
```

- [ ] **Step 7: 통과 확인**

Run: `python -m unittest tests.test_gx_visualize_fallback tests.test_gx_visualize_backend tests.test_gx_arch_archify tests.test_gx_arch_index -v`
Expected: 모두 PASS. 그다음 `grep -rn "snapshot" .claude/skills/gx-visualize/scripts/`의 결과가 0줄인지 확인한다.

- [ ] **Step 8: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/render_fallback.py .claude/skills/gx-visualize/scripts/render_archify.py .claude/skills/gx-visualize/templates/fallback.css tests/test_gx_visualize_fallback.py tests/test_gx_visualize_backend.py
git diff --cached --stat
git commit -m "feat: 렌더러가 이번 변경을 그리고 세션 스냅샷 배너를 없앤다"
```

---

### Task 6: 인덱스에 "이번 변경" 절을 만든다

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/build_index.py`
- Modify: `tests/test_gx_arch_index.py`

**Interfaces:**
- Consumes: `render_fallback.CHANGE_LABELS`(Task 5), 도메인 IR의 노드 `change`와 `meta.changes`.
- Produces: `build_index.build_index(map_dir, project_root=None, changes=None) -> Path`. `changes`는 Task 7이 넘기는 전체 요약(`compute_changes` 반환값, 삭제 목록 포함)이다. 생략하면 도메인 IR의 `meta.changes`에서 기준 정보만 읽는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_gx_arch_index.py`의 `_write_domain` 시그니처와 끝부분을 다음으로 바꾼다(기존 호출은 그대로 동작한다).

```python
    def _write_domain(self, map_dir, domain, *, nodes=2, edges=1, missing=0, unresolved=0, backend="archify", status="valid", marks=(), changes=None):
```

그리고 `ir = {...}` 정의 바로 아래(파일에 쓰기 전)에 추가한다.

```python
        for index, change in enumerate(marks):
            ir["nodes"][index]["change"] = change
        if changes is not None:
            ir["meta"] = {"changes": changes}
```

클래스 안에 테스트를 추가한다.

```python
    CHANGES = {"available": True, "base_ref": "main", "base_commit": "abc1234"}

    def _write_changed_map(self, map_dir):
        self._write_domain(map_dir, "auth", nodes=2, marks=("added",), changes=self.CHANGES)
        self._write_domain(map_dir, "reb", nodes=3, marks=("changed", "added"), changes=self.CHANGES)
        self._write_domain(map_dir, "config", nodes=1, edges=0, changes=self.CHANGES)

    @staticmethod
    def _section(html_text, anchor):
        start = html_text.index(anchor)
        return html_text[start : html_text.index("</section>", start)]

    @staticmethod
    def _card(html_text, domain):
        start = html_text.index(f"<h3>{domain}</h3>")
        return html_text[html_text.rindex("<article", 0, start) : html_text.index("</article>", start)]

    def test_change_section_lists_changed_domains_with_labels_and_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_changed_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")
        section = self._section(html_text, 'id="changes-title"')
        self.assertIn('href="domains/auth.html"', section)
        self.assertIn("[신규] auth 노드 0", section)
        self.assertIn("신규 1개 · 변경 1개", section)
        self.assertIn("[신규] reb 노드 1, [변경] reb 노드 0", section)
        self.assertNotIn("domains/config.html", section)
        self.assertIn("main (abc1234)", html_text)

    def test_changed_domain_cards_are_highlighted(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_changed_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")
        self.assertIn("domain-changed", self._card(html_text, "auth"))
        self.assertIn("이번 변경: 신규 1개 · 변경 0개", self._card(html_text, "auth"))
        self.assertNotIn("domain-changed", self._card(html_text, "config"))

    def test_removed_items_come_from_the_full_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_changed_map(map_dir)
            summary = {**self.CHANGES, "removed": [{"id": "x", "kind": "api", "label": "UserController.list"}]}
            html_text = self.builder.build_index(map_dir, changes=summary).read_text(encoding="utf-8")
        self.assertIn("삭제된 항목 1개", html_text)
        self.assertIn("UserController.list", html_text)

    def test_skipped_marking_reports_the_reason(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_domain(map_dir, "auth", changes={"available": False, "base_ref": "main", "reason": "git merge-base 실패"})
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")
        self.assertIn("변경 표시를 생략했습니다: git merge-base 실패", html_text)

    def test_no_change_section_without_changed_since(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_fixture_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")
        self.assertNotIn('id="changes-title"', html_text)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_arch_index -v`
Expected: 새 테스트 5개 중 `test_no_change_section_without_changed_since`는 PASS, 나머지는 `ValueError: substring not found` 또는 `TypeError: ... unexpected keyword argument 'changes'`로 실패.

- [ ] **Step 3: 구현**

`build_index.py`:

1. `STATUS_LABELS` 아래에 추가한다.

```python
# "이번 변경" 절에 도메인마다 보여 줄 항목 수. 나머지는 "외 N개"로 센다.
MAX_LISTED = 8
```

2. `_collect_domains`를 다음으로 바꾼다.

```python
def _collect_domains(map_dir: Path, change_labels: dict[str, str]) -> list[dict[str, Any]]:
    ir_dir = map_dir / "ir"
    receipts_dir = map_dir / "receipts"
    domains: list[dict[str, Any]] = []
    for ir_path in sorted(ir_dir.glob(f"*{IR_SUFFIX}")):
        domain = _domain_name(ir_path)
        ir = _load_json(ir_path) or {}
        receipt = _load_json(receipts_dir / f"{domain}{RECEIPT_SUFFIX}") or {}
        nodes = ir.get("nodes", [])
        edges = ir.get("edges", [])
        missing_inputs = ir.get("missing_inputs", [])
        unresolved_edges = ir.get("unresolved_edges", [])
        change_nodes = sorted(
            (node["change"], str(node.get("label", "")))
            for node in (nodes if isinstance(nodes, list) else [])
            if isinstance(node, dict) and node.get("change") in change_labels
        )
        meta = ir.get("meta") if isinstance(ir.get("meta"), dict) else {}
        domains.append(
            {
                "domain": domain,
                "node_count": len(nodes) if isinstance(nodes, list) else 0,
                "edge_count": len(edges) if isinstance(edges, list) else 0,
                "missing_count": len(missing_inputs) if isinstance(missing_inputs, list) else 0,
                "unresolved_count": len(unresolved_edges) if isinstance(unresolved_edges, list) else 0,
                "backend": receipt.get("backend"),
                "status": receipt.get("status"),
                "evidence_files": _evidence_files(ir),
                "added": sum(1 for change, _ in change_nodes if change == "added"),
                "changed": sum(1 for change, _ in change_nodes if change == "changed"),
                "change_nodes": change_nodes,
                "changes_meta": meta.get("changes") if isinstance(meta.get("changes"), dict) else None,
            }
        )
    return domains
```

3. `_domain_card`에서 `return (` 앞에 추가하고, 반환 문자열을 바꾼다.

```python
    has_changes = bool(entry["added"] or entry["changed"])
    changed_class = " domain-changed" if has_changes else ""
    change_html = (
        f'<p class="change-line">이번 변경: 신규 {entry["added"]}개 · 변경 {entry["changed"]}개</p>'
        if has_changes else ""
    )
    return (
        f'<li><article class="domain-card domain-{css_class}{changed_class}">'
        f'<h3>{_escape(domain)}</h3>'
        f'<p class="domain-kind">{_escape(diagram_label)} · 백엔드 <code>{_escape(backend_text)}</code> · {_escape(status_label)}</p>'
        f'<p>노드 {entry["node_count"]}개 · 관계 {entry["edge_count"]}개</p>'
        f'<p>{_escape(missing_text)} · {_escape(unresolved_text)}</p>'
        f"{change_html}"
        f'<p><a href="domains/{_escape(domain)}.html">{_escape(domain)}.html 열기</a></p>'
        "</article></li>"
    )
```

4. `_domain_card` 아래에 추가한다.

```python
def _listed(items: list[str]) -> str:
    rest = len(items) - MAX_LISTED
    return ", ".join(items[:MAX_LISTED]) + (f" 외 {rest}개" if rest > 0 else "")


def _change_section(domains: list[dict[str, Any]], changes: Any, change_labels: dict[str, str]) -> str:
    """인덱스 맨 위의 '이번 변경' 절. 변경 표시를 요청하지 않은 실행(changes 없음)에는 만들지 않는다."""
    if not isinstance(changes, dict):
        return ""
    heading = '<section aria-labelledby="changes-title"><h2 id="changes-title">이번 변경</h2>'
    if not changes.get("available"):
        reason = changes.get("reason") or "기준 시점을 정할 수 없습니다"
        return f'{heading}<p class="fallback-note">변경 표시를 생략했습니다: {_escape(reason)}</p></section>'
    base = f'{changes.get("base_ref", "")} ({changes.get("base_commit", "")})'
    items = [
        f'<li><a href="domains/{_escape(entry["domain"])}.html">{_escape(entry["domain"])}</a> — '
        f'신규 {entry["added"]}개 · 변경 {entry["changed"]}개: '
        f'{_escape(_listed([f"[{change_labels[change]}] {label}" for change, label in entry["change_nodes"]]))}</li>'
        for entry in domains
        if entry["change_nodes"]
    ]
    parts = [heading]
    if items:
        parts.append(f"<p>기준 {_escape(base)} 이후 구조가 바뀐 곳입니다.</p>")
        parts.append(f'<ul class="change-summary">{"".join(items)}</ul>')
    else:
        parts.append(f"<p>기준 {_escape(base)} 이후 구조 변경이 없습니다.</p>")
    removed = changes.get("removed") if isinstance(changes.get("removed"), list) else []
    if removed:
        names = _listed([str(item.get("label", "")) for item in removed if isinstance(item, dict)])
        parts.append(f"<p>삭제된 항목 {len(removed)}개 (그림에는 없습니다): {_escape(names)}</p>")
    parts.append("</section>")
    return "".join(parts)
```

5. `build_index`를 다음으로 바꾼다.

```python
def build_index(
    map_dir: Path | str, project_root: Path | str | None = None, changes: dict[str, Any] | None = None
) -> Path:
    """`map_dir`의 `ir/`·`receipts/`를 읽어 `아키텍처-맵.html` 인덱스를 만들고 그 경로를 반환한다.

    `changes`는 build_map.py가 넘기는 전체 변경 요약(삭제 목록 포함)이다. 생략하면 도메인
    IR의 `meta.changes`에서 기준 정보만 읽는다 - 삭제 목록은 도메인 IR에 없으므로 인덱스만
    따로 다시 만들면 삭제 목록이 빠진다.
    """
    map_dir = Path(map_dir)
    fallback = _fallback_module()
    domains = _collect_domains(map_dir, fallback.CHANGE_LABELS)
    if changes is None:
        changes = next((entry["changes_meta"] for entry in domains if entry["changes_meta"]), None)

    node_total = sum(entry["node_count"] for entry in domains)
    edge_total = sum(entry["edge_count"] for entry in domains)
    diagram_count = sum(1 for entry in domains if entry["backend"] in DIAGRAM_BACKENDS)
    table_only_count = sum(1 for entry in domains if entry["backend"] == "static")
    evidence_files: set[str] = set()
    for entry in domains:
        evidence_files |= entry.pop("evidence_files")
        entry.pop("changes_meta")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha = fallback._short_head(project_root)
    revision_text = f" · 커밋 {_escape(sha)}" if sha else ""
    change_text = ""
    if isinstance(changes, dict) and changes.get("available"):
        change_text = f' · 이번 변경 기준 {changes.get("base_ref", "")} ({changes.get("base_commit", "")})'
    summary = (
        f"도메인 {len(domains)}개 · 근거로 인용된 소스 파일 {len(evidence_files)}개 · "
        f"노드 {node_total}개 · 관계 {edge_total}개 · 그림 {diagram_count}개 · 표 {table_only_count}개 · "
        f"생성 시각 {generated_at}{revision_text}{change_text}"
    )

    if domains:
        cards = "".join(_domain_card(entry) for entry in domains)
        body = _change_section(domains, changes, fallback.CHANGE_LABELS) + (
            f'<section aria-labelledby="domains-title"><h2 id="domains-title">도메인</h2><ul class="domain-list">{cards}</ul></section>'
        )
    else:
        body = '<p class="fallback-note">생성된 도메인 산출물이 없습니다.</p>'

    template = (TEMPLATE_DIR / "fallback.html").read_text(encoding="utf-8")
    css = (TEMPLATE_DIR / "fallback.css").read_text(encoding="utf-8")
    replacements = {
        "TITLE": "아키텍처 맵",
        "SUMMARY": _escape(summary),
        "CSS": css.rstrip(),
        "MERMAID_SECTION": "",
        "STATIC_CONTENT": body,
    }
    document = fallback.TEMPLATE_TOKEN.sub(lambda match: replacements[match.group(1)], template)

    index_path = map_dir / "아키텍처-맵.html"
    index_path.write_text(document, encoding="utf-8")
    return index_path
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_gx_arch_index -v`
Expected: 모두 PASS(기존 테스트 포함).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/build_index.py tests/test_gx_arch_index.py
git diff --cached --stat
git commit -m "feat: 인덱스에 이번 변경 절과 도메인 강조를 더한다"
```

---

### Task 7: `build_map.py` — 명령 하나로 맵을 만든다

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/build_map.py`
- Create: `tests/test_gx_arch_build_map.py`

**Interfaces:**
- Consumes: `scan_entrypoints.scan`, `changes.compute_changes`(Task 2), `split_domains.split_by_domain`, `validate_ir.validate`, `render_archify.render_archify`(Task 5 시그니처), `render_fallback.render`·`ensure_mermaid_asset`(Task 5), `build_index.build_index(map_dir, project_root, changes)`(Task 6).
- Produces:
  - CLI: `python scripts/build_map.py <PROJECT_ROOT> [--map-dir <MAP_DIR>] [--changed-since <REF>] [--domain <DOMAIN>] [--labels <LABELS_JSON>]` — stdout에 설계서 §5.8.4의 JSON 보고, 종료 코드 `validation_status == "failed"`면 1 아니면 0.
  - `build_map.build_map(project_root, map_dir=None, changed_since=None, domain=None, labels=None, archify_command=None) -> dict`
  - `build_map.apply_labels(ir: dict, labels: dict[str, str]) -> int`
  - Task 8의 SKILL.md가 이 CLI를 문서화한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_gx_arch_build_map.py`:

```python
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "build_map.py"
GIT = shutil.which("git")


def _load():
    spec = importlib.util.spec_from_file_location("gx_build_map_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _user_controller(endpoints):
    methods = "".join(
        f'\n    @GetMapping("/{name}")\n    public String {name}() {{\n        return userService.list();\n    }}\n'
        for name in endpoints
    )
    return (
        'package com.sqi.user.controller;\n\n@RestController\n@RequestMapping("/api/users")\n'
        f"public class UserController {{\n    private final UserService userService;\n{methods}}}\n"
    )


def _project(root, user_endpoints=("list", "detail")):
    """user(컨트롤러·서비스·매퍼·XML → TB_USER)와 code(컨트롤러·서비스) 두 도메인."""
    _write(root, "src/main/java/com/sqi/user/controller/UserController.java", _user_controller(user_endpoints))
    _write(root, "src/main/java/com/sqi/user/service/UserService.java", textwrap.dedent("""\
        package com.sqi.user.service;

        @Service
        public class UserService {
            private final UserMapper userMapper;

            public String list() {
                return userMapper.list();
            }
        }
        """))
    _write(root, "src/main/java/com/sqi/user/mapper/UserMapper.java", textwrap.dedent("""\
        package com.sqi.user.mapper;

        @Mapper
        public interface UserMapper {
            String list();
        }
        """))
    _write(root, "src/main/resources/mapper/user/UserMapper.xml", textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <mapper namespace="com.sqi.user.mapper.UserMapper">
            <select id="list">SELECT USER_ID FROM TB_USER</select>
        </mapper>
        """))
    _write(root, "src/main/java/com/sqi/code/controller/CodeController.java", textwrap.dedent("""\
        package com.sqi.code.controller;

        @RestController
        public class CodeController {
            private final CodeService codeService;

            @GetMapping("/api/codes")
            public String codes() {
                return codeService.codes();
            }
        }
        """))
    _write(root, "src/main/java/com/sqi/code/service/CodeService.java", textwrap.dedent("""\
        package com.sqi.code.service;

        @Service
        public class CodeService {
            public String codes() {
                return "";
            }
        }
        """))


def _git(root, *args):
    subprocess.run(
        [
            "git", "-c", "user.name=gx", "-c", "user.email=gx@example.com",
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args,
        ],
        cwd=root, check=True, capture_output=True,
    )


def _fake_archify(root, validation_exit=0):
    script = Path(root) / "fake_archify.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import sys

            phase = sys.argv[1]
            if phase == "doctor":
                raise SystemExit(0)
            if phase == "validate":
                print("validated")
                raise SystemExit({validation_exit})
            if phase == "deliver":
                output = pathlib.Path(sys.argv[-2])
                output.write_text('<html lang="ko"><body>Archify 결과</body></html>', encoding="utf-8")
                raise SystemExit(0)
            raise SystemExit(64)
            """
        ).strip() + "\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


class BuildMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.root = self.work / "project"
        self.map_dir = self.work / "map"
        self.command = _fake_archify(self.work)

    def build(self, **kwargs):
        return self.module.build_map(self.root, self.map_dir, archify_command=self.command, **kwargs)

    def read(self, relative):
        return (self.map_dir / relative).read_text(encoding="utf-8")

    def test_builds_index_and_one_page_per_domain(self):
        _project(self.root)
        report = self.build()
        self.assertEqual(report["validation_status"], "verified")
        self.assertEqual([entry["domain"] for entry in report["domains"]], ["code", "user"])
        self.assertTrue(report["index_path"].endswith("아키텍처-맵.html"))
        for relative in ("아키텍처-맵.html", "domains/user.html", "domains/code.html",
                         "ir/user.ir.json", "receipts/user.receipt.json"):
            self.assertTrue((self.map_dir / relative).is_file(), relative)
        self.assertIsNone(report["changes"])
        self.assertEqual(report["cross_domain_edge_count"], 0)

    def test_archify_failure_falls_back_to_a_drawn_mermaid_and_keeps_the_fallback_receipt(self):
        _project(self.root)
        self.command = _fake_archify(self.work, validation_exit=1)
        assets = self.map_dir / "assets"
        assets.mkdir(parents=True)
        (assets / "mermaid.min.js").write_bytes(b"/*mermaid*/" + b" " * 600_000)  # 다운로드 없이 확보된 상태
        report = self.build()
        self.assertEqual(report["validation_status"], "fallback")
        self.assertEqual({entry["backend"] for entry in report["domains"]}, {"mermaid"})
        self.assertTrue(report["mermaid_asset"]["available"])
        html_text = self.read("domains/user.html")
        self.assertIn('<pre class="mermaid">', html_text)
        self.assertIn("../assets/mermaid.min.js", html_text)
        receipt = json.loads(self.read("receipts/user.receipt.json"))
        self.assertEqual(receipt["status"], "fallback")
        self.assertIn("failed", [attempt["status"] for attempt in receipt["attempts"] if attempt["backend"] == "archify"])
        self.assertIn("폴백", self.read("아키텍처-맵.html"))

    def test_empty_project_fails_without_writing_ir(self):
        self.root.mkdir()
        report = self.build()
        self.assertEqual(report["validation_status"], "failed")
        self.assertEqual(report["missing_inputs"], ["entrypoint-scan"])
        self.assertIsNone(report["index_path"])
        self.assertFalse((self.map_dir / "ir").exists())

    def test_unknown_domain_fails_and_lists_found_domains(self):
        _project(self.root)
        report = self.build(domain="nope")
        self.assertEqual(report["validation_status"], "failed")
        self.assertIn("code, user", report["reason"])

    def test_single_domain_run_keeps_other_domains(self):
        _project(self.root)
        self.build()
        report = self.build(domain="user")
        self.assertEqual([entry["domain"] for entry in report["domains"]], ["user"])
        self.assertTrue((self.map_dir / "domains" / "code.html").is_file())

    def test_stale_domain_outputs_are_removed_on_full_run(self):
        _project(self.root)
        for relative in ("ir/old.ir.json", "domains/old.html", "receipts/old.receipt.json"):
            _write(self.map_dir, relative, "{}")
        self.build()
        for relative in ("ir/old.ir.json", "domains/old.html", "receipts/old.receipt.json"):
            self.assertFalse((self.map_dir / relative).exists(), relative)
        self.assertNotIn("<h3>old</h3>", self.read("아키텍처-맵.html"))

    def test_rerun_is_stable(self):
        _project(self.root)
        first = self.build()
        first_ir = self.read("ir/user.ir.json")
        second = self.build()
        self.assertEqual(self.read("ir/user.ir.json"), first_ir)
        self.assertEqual(
            [(entry["domain"], entry["backend"]) for entry in first["domains"]],
            [(entry["domain"], entry["backend"]) for entry in second["domains"]],
        )

    def test_labels_apply_only_on_exact_match(self):
        _project(self.root)
        report = self.build(labels={"UserService": "사용자 서비스", "User": "지어낸 라벨"})
        self.assertEqual(report["labels_applied"], 1)
        nodes = json.loads(self.read("ir/user.ir.json"))["nodes"]
        service = next(node for node in nodes if node["label"] == "사용자 서비스")
        self.assertEqual(service["technical_label"], "UserService")
        self.assertNotIn("지어낸 라벨", [node["label"] for node in nodes])

    def test_changed_since_outside_git_still_builds_the_map(self):
        _project(self.root)
        report = self.build(changed_since="main")
        self.assertEqual(report["validation_status"], "verified")
        self.assertFalse(report["changes"]["available"])
        self.assertIn("변경 표시를 생략했습니다", self.read("아키텍처-맵.html"))

    @unittest.skipUnless(GIT, "git not available on PATH")
    def test_changed_since_marks_a_new_endpoint_end_to_end(self):
        _project(self.root, user_endpoints=("list",))
        _git(self.root, "init", "-q")
        _git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "base")
        _git(self.root, "checkout", "-q", "-b", "feature")
        _write(self.root, "src/main/java/com/sqi/user/controller/UserController.java", _user_controller(("list", "detail")))
        _git(self.root, "commit", "-q", "-am", "detail 추가")

        report = self.build(changed_since="main")

        self.assertTrue(report["changes"]["available"])
        self.assertEqual(report["changes"]["added"], 1)
        user = next(entry for entry in report["domains"] if entry["domain"] == "user")
        self.assertEqual((user["added"], user["changed"]), (1, 0))
        nodes = json.loads(self.read("ir/user.ir.json"))["nodes"]
        self.assertEqual(next(node for node in nodes if node["label"] == "UserController.detail")["change"], "added")
        self.assertIn("기준 main (", self.read("domains/user.html"))
        self.assertIn("신규 1개", self.read("domains/user.html"))
        self.assertIn("구조 변경이 없습니다", self.read("domains/code.html"))
        self.assertIn('id="changes-title"', self.read("아키텍처-맵.html"))

    @unittest.skipUnless(GIT, "git not available on PATH")
    def test_labels_do_not_turn_into_changes(self):
        # Review Focus 3: 라벨을 먼저 붙이면 technical_label이 기준 스캔과 달라져 전부 "변경"이 된다.
        _project(self.root)
        _git(self.root, "init", "-q")
        _git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "base")
        report = self.build(changed_since="main", labels={"UserService": "사용자 서비스"})
        self.assertEqual(report["labels_applied"], 1)
        self.assertEqual((report["changes"]["added"], report["changes"]["changed"]), (0, 0))

    def test_cli_prints_json_report_and_exit_code(self):
        report = {"view": "service", "validation_status": "failed", "domains": [], "reason": "없음 — 테스트"}
        with mock.patch.object(self.module, "build_map", return_value=report) as build, \
                mock.patch.object(sys, "argv", ["build_map.py", "some/root", "--changed-since", "main"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.module.main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["reason"], "없음 — 테스트")
        self.assertEqual(build.call_args.args[2], "main")

    def test_cli_rejects_labels_that_are_not_an_object(self):
        labels = self.work / "labels.json"
        labels.write_text("[1, 2]", encoding="utf-8")
        with mock.patch.object(sys, "argv", ["build_map.py", str(self.work), "--labels", str(labels)]), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self.module.main()
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_arch_build_map -v`
Expected: 전부 ERROR — `FileNotFoundError`(build_map.py 없음).

- [ ] **Step 3: 구현**

`.claude/skills/gx-visualize/scripts/build_map.py`:

```python
#!/usr/bin/env python3
"""Build the architecture map in one command.

스캔 → 변경 표시 → (선택) 한국어 라벨 → 도메인 분할 → 도메인별 검증·렌더 → Mermaid
자산 → 인덱스를 한 번에 수행하고 JSON 보고를 낸다(설계서 §5.8.3·§5.8.4). 2026-09-28
콜드런에서 문서만 보고 실행한 모델이 이 단계들을 손으로 잇느라 13~24분이 걸렸고, 도메인
분할에는 실행 명령이 없어 매번 연결 코드를 새로 짰다. 결정적인 단계는 여기 모으고,
모델은 이 명령 하나를 실행해 보고를 전달한다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
DEFAULT_MAP_DIR = Path(".dev") / "architecture"
MERMAID_ASSET_HREF = "../assets/mermaid.min.js"
ENTRYPOINT_SCAN_GROUP = "entrypoint-scan"
IR_SUFFIX = ".ir.json"


def _load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"gx_visualize_{name}_for_build_map", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scanner = _load("scan_entrypoints")
changes_module = _load("changes")
splitter = _load("split_domains")
validator = _load("validate_ir")
archify_renderer = _load("render_archify")
fallback_renderer = _load("render_fallback")
index_builder = _load("build_index")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_labels(ir: dict[str, Any], labels: dict[str, str]) -> int:
    """스캔 라벨과 **정확히 일치하는** 항목만 한국어 라벨로 바꾸고 바꾼 노드 수를 반환한다.

    부분 일치·추측은 하지 않는다(SKILL.md "도메인 용어를 지어내지 않는다"). 원래 기술
    식별자는 technical_label이 비어 있을 때만 그리로 옮긴다 - API 노드의 technical_label
    (HTTP 경로)은 덮어쓰지 않는다.
    """
    applied = 0
    for node in ir["nodes"]:
        korean = labels.get(node["label"])
        if not isinstance(korean, str) or not korean.strip():
            continue
        node.setdefault("technical_label", node["label"])
        node["label"] = korean.strip()
        applied += 1
    return applied


def _clear_stale(map_dir: Path, keep: set[str]) -> None:
    """이번 스캔에 없는 도메인의 이전 산출물을 지운다.

    매 실행 전체를 다시 스캔하므로 사라진 도메인의 그림이 인덱스에 남으면 없는 구조를
    있는 것처럼 보여 준다. `--domain`으로 한 도메인만 그릴 때는 부르지 않는다.
    """
    for ir_path in sorted((map_dir / "ir").glob(f"*{IR_SUFFIX}")):
        name = ir_path.name[: -len(IR_SUFFIX)]
        if name in keep:
            continue
        ir_path.unlink(missing_ok=True)
        (map_dir / "domains" / f"{name}.html").unlink(missing_ok=True)
        for suffix in (".receipt.json", ".archify.json"):
            (map_dir / "receipts" / f"{name}{suffix}").unlink(missing_ok=True)


def _domain_status(receipt: dict[str, Any]) -> str:
    """렌더 영수증을 보고 계약의 verified·fallback·failed로 정규화한다(references/gx-mapping.md)."""
    if receipt.get("status") == "failed" or not receipt.get("artifact_path"):
        return "failed"
    if receipt.get("backend") == "archify" and receipt.get("status") == "valid":
        return "verified"
    return "fallback"


def _overall_status(domains: list[dict[str, Any]]) -> str:
    statuses = {entry["validation_status"] for entry in domains}
    if not domains or "failed" in statuses:
        return "failed"
    return "fallback" if "fallback" in statuses else "verified"


def _render_domain(
    name: str, part: dict[str, Any], map_dir: Path, project_root: Path, archify_command: Any
) -> dict[str, Any]:
    ir_path = map_dir / "ir" / f"{name}{IR_SUFFIX}"
    receipts_dir = map_dir / "receipts"
    entry: dict[str, Any] = {
        "domain": name,
        "backend": None,
        "validation_status": "failed",
        "html_path": None,
        "ir_path": str(ir_path) if ir_path.is_file() else None,
        "receipt_path": None,
        "missing_inputs": sorted(set(part.get("missing_inputs", []))),
        "added": sum(1 for node in part["nodes"] if node.get("change") == "added"),
        "changed": sum(1 for node in part["nodes"] if node.get("change") == "changed"),
    }
    # 검증을 통과하기 전에는 이전 {domain}.ir.json을 덮어쓰지 않는다(설계서 §6).
    pending = map_dir / "ir" / f".{name}{IR_SUFFIX}.pending"
    _write_json(pending, part)
    receipt = validator.validate(pending, project_root=project_root)
    if receipt["status"] != "valid":
        pending.unlink(missing_ok=True)
        entry["errors"] = receipt["errors"]
        return entry
    pending.replace(ir_path)
    entry["ir_path"] = str(ir_path)
    try:
        result = archify_renderer.render_archify(
            ir_path, receipts_dir, archify_command,
            project_root=project_root, output_name=name, html_dir=map_dir / "domains",
        )
    except (OSError, ValueError, RuntimeError) as exc:
        entry["errors"] = [str(exc)]
        entry["receipt_path"] = str(receipts_dir / f"{name}.receipt.json")
        return entry
    rendered = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    entry.update(
        backend=result["backend"],
        validation_status=_domain_status(rendered),
        html_path=result["html_path"],
        receipt_path=result["receipt_path"],
        missing_inputs=rendered.get("missing_inputs", entry["missing_inputs"]),
    )
    return entry


def _rerender_with_mermaid_asset(entry: dict[str, Any], map_dir: Path, project_root: Path) -> None:
    """Mermaid로 폴백한 도메인을 공유 자산으로 다시 그려 브라우저에서 실제 그림이 보이게 한다.

    render_fallback.render()는 영수증을 검증기 결과로 새로 쓴다. 그대로 두면 Archify 실패
    기록(attempts)과 폴백 판정이 사라지고 인덱스가 이 도메인을 "통과"로 표시한다(2026-09-28
    콜드런에서 관찰). 다시 그리기 전의 영수증을 되돌려 놓는다.
    """
    receipt_path = Path(entry["receipt_path"])
    preserved = receipt_path.read_text(encoding="utf-8")
    try:
        fallback_renderer.render(
            entry["ir_path"], map_dir / "receipts", "mermaid",
            project_root=project_root, output_name=entry["domain"],
            html_dir=map_dir / "domains", mermaid_asset_href=MERMAID_ASSET_HREF,
        )
    except (OSError, ValueError) as exc:
        entry.setdefault("errors", []).append(f"Mermaid 자산으로 다시 그리지 못했습니다: {exc}")
    finally:
        receipt_path.write_text(preserved, encoding="utf-8")


def build_map(
    project_root: Path | str,
    map_dir: Path | str | None = None,
    changed_since: str | None = None,
    domain: str | None = None,
    labels: dict[str, str] | None = None,
    archify_command: Any = None,
) -> dict[str, Any]:
    """`project_root`의 아키텍처 맵을 `map_dir`(기본 `<project_root>/.dev/architecture`)에 만든다.

    `archify_command`는 테스트용이다 - 생략하면 render_archify가 스스로 Archify를 찾는다.
    CLI에는 노출하지 않는다: 셸을 거친 명령 문자열이 깨지는 경로를 다시 열지 않는다(T15).
    """
    root = Path(project_root).resolve()
    map_dir = Path(map_dir) if map_dir is not None else root / DEFAULT_MAP_DIR
    report: dict[str, Any] = {
        "view": "service",
        "map_dir": str(map_dir),
        "index_path": None,
        "validation_status": "failed",
        "domains": [],
        "changes": None,
        "cross_domain_edge_count": 0,
        "unresolved_edge_count": 0,
        "skipped": [],
        "mermaid_asset": None,
        "missing_inputs": [],
        "labels_applied": 0,
    }

    head = scanner.scan(root)
    report["skipped"] = head["skipped"]
    report["unresolved_edge_count"] = len(head["unresolved_edges"])
    if not head["nodes"]:
        report["missing_inputs"] = [ENTRYPOINT_SCAN_GROUP]
        report["reason"] = (
            "스캔이 노드를 하나도 찾지 못했습니다. 지원 언어(Java Spring·JSP/Servlet) 소스가 없거나 "
            "project_root가 소스 트리를 포함하지 않습니다."
        )
        return report

    # 변경 판정은 라벨 적용보다 먼저 한다 - 라벨이 technical_label을 채우면 기준 스캔과
    # 달라져 라벨을 붙인 노드가 모두 "변경"으로 표시된다(설계서 §5.8.3).
    changes = changes_module.compute_changes(root, changed_since, head) if changed_since else None
    report["changes"] = changes
    if labels:
        report["labels_applied"] = apply_labels(head, labels)

    ir = {
        "schema_version": 1,
        "view": "service",
        "locale": "ko-KR",
        "title": "아키텍처 맵",
        "nodes": head["nodes"],
        "edges": head["edges"],
        "missing_inputs": [],
        "skipped": head["skipped"],
        "unresolved_edges": head["unresolved_edges"],
    }
    parts = splitter.split_by_domain(ir)
    kept_edges = {edge["id"] for part in parts.values() for edge in part["edges"]}
    report["cross_domain_edge_count"] = sum(1 for edge in head["edges"] if edge["id"] not in kept_edges)

    if domain is not None:
        if domain not in parts:
            found = ", ".join(sorted(parts)) or "없음"
            report["reason"] = f"도메인 '{domain}'을 찾지 못했습니다. 찾은 도메인: {found}"
            return report
        parts = {domain: parts[domain]}
    else:
        _clear_stale(map_dir, set(parts))

    domain_meta = None
    if changes is not None:
        domain_meta = {key: changes[key] for key in ("available", "base_ref", "base_commit", "reason") if key in changes}
    for name in sorted(parts):
        part = parts[name]
        part["title"] = f"{name} 도메인 구조"
        if domain_meta is not None:
            part["meta"] = {"changes": domain_meta}
        report["domains"].append(_render_domain(name, part, map_dir, root, archify_command))

    mermaid_domains = [entry for entry in report["domains"] if entry["backend"] == "mermaid"]
    if mermaid_domains:
        asset = fallback_renderer.ensure_mermaid_asset(map_dir / "assets")
        report["mermaid_asset"] = {"available": asset["available"], "attempts": asset["attempts"]}
        if asset["available"]:
            for entry in mermaid_domains:
                _rerender_with_mermaid_asset(entry, map_dir, root)

    report["index_path"] = str(index_builder.build_index(map_dir, project_root=root, changes=changes))
    report["validation_status"] = _overall_status(report["domains"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="프로젝트 전체를 스캔해 아키텍처 맵(아키텍처-맵.html)을 만듭니다.")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--map-dir", type=Path)
    parser.add_argument("--changed-since", metavar="REF")
    parser.add_argument("--domain")
    parser.add_argument("--labels", type=Path)
    args = parser.parse_args()

    labels = None
    if args.labels is not None:
        try:
            labels = json.loads(args.labels.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parser.error(f"--labels 파일을 읽을 수 없습니다: {exc}")
        if not isinstance(labels, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in labels.items()
        ):
            parser.error('--labels는 {"스캔 라벨": "한국어 라벨"} 형태의 JSON 객체여야 합니다.')

    report = build_map(args.project_root, args.map_dir, args.changed_since, args.domain, labels)
    # Windows 콘솔 기본 인코딩(cp949)은 보고의 일부 문자(—)를 쓰지 못해 UnicodeEncodeError로
    # 죽는다(2026-09-28 콜드런). 보고는 항상 UTF-8로 낸다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["validation_status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_gx_arch_build_map -v`
Expected: 모두 PASS.

- [ ] **Step 5: 전체 회귀 확인**

Run: `python -m unittest discover -s tests -p "test_gx_*.py" 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^FAILED|^OK"`
Expected: 실패는 `test_gx_visualize_routing`의 7건뿐.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/build_map.py tests/test_gx_arch_build_map.py
git diff --cached --stat
git commit -m "feat: 아키텍처 맵을 명령 하나로 만드는 build_map.py를 추가한다"
```

---

### Task 8: SKILL.md·참조 문서·phase-complete를 새 흐름으로 개정한다

**Files:**
- Modify: `.claude/skills/gx-visualize/SKILL.md`
- Modify: `.claude/skills/gx-visualize/references/gx-mapping.md`
- Modify: `.claude/skills/gx-visualize/references/archify-adapter.md:41`
- Modify: `.claude/skills/gx-dev/phases/phase-complete.md` (Step 5.5)
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md` (Step 5.5)
- Modify: `.claude/skills/gx-tdd/references/maintenance-notes.md:34`
- Modify: `tests/test_gx_visualize_skill_contract.py`, `tests/test_gx_arch_pipeline.py`

**Interfaces:**
- Consumes: Task 7의 CLI와 보고 필드.
- Produces: 모델이 따를 계약 — `service` 뷰는 `build_map.py` 한 명령, Step 5.5는 두 선택지.

- [ ] **Step 1: 실패하는 테스트 작성 — 스킬 계약**

`tests/test_gx_visualize_skill_contract.py`의 `AccumulatedMapContractTests`에서 `test_scope_flag_is_documented`, `test_session_scope_writes_to_dev_dir`, `test_all_scope_writes_to_map_dir`, `test_session_html_carries_snapshot_banner`, `test_session_and_accumulated_outputs_are_not_mixed` 다섯 테스트를 지우고 추가한다.

```python
    def test_session_scope_is_gone(self):
        self.assertNotIn("--scope", self.skill)
        self.assertNotIn("세션분", self.skill)
        self.assertNotIn("스냅샷 배너", self.skill)

    def test_service_view_runs_one_documented_command(self):
        self.assertIn("python scripts/build_map.py <PROJECT_ROOT>", self.skill)
        self.assertTrue((SKILL_DIR / "scripts" / "build_map.py").is_file())

    def test_change_marking_is_documented(self):
        for text in ("--changed-since", "[신규]", "[변경]", "커밋하지 않은 변경도 현재 쪽에 포함"):
            self.assertIn(text, self.skill)

    def test_labels_require_exact_glossary_match(self):
        self.assertIn("--labels", self.skill)
        self.assertIn("정확히 같은 이름", self.skill)

    def test_service_report_is_per_domain(self):
        for field in ("`index_path`", "`domains[]`", "`changes`", "`cross_domain_edge_count`"):
            self.assertIn(field, self.skill)

    def test_mapping_no_longer_requires_codemap_for_service(self):
        mapping = MAPPING.read_text(encoding="utf-8")
        self.assertRegex(mapping, r"(?m)^\| `service` \| 진입점 체인 스캔")
        self.assertNotIn("`codemap|design`", mapping)
```

`tests/test_gx_arch_pipeline.py`에서 `test_gate_offers_session_and_full_scope`를 지우고 추가한다.

```python
    def test_gate_offers_only_the_full_map_with_change_marks(self):
        for path in PHASES:
            text = self._text(path)
            self.assertNotIn("--scope", text, path.name)
            self.assertNotIn("세션분", text, path.name)
            self.assertIn("--changed-since ${BASE_BRANCH}", text, path.name)
            self.assertIn("--project-root ${PROJECT_ROOT}", text, path.name)

    def test_svn_projects_skip_change_marks_honestly(self):
        for path in PHASES:
            text = self._text(path)
            self.assertIn("svn이면", text, path.name)
            self.assertIn("변경 표시 없이", text, path.name)

    def test_both_pipelines_keep_the_same_gate_text(self):
        # 의도적 중복(maintenance-notes)이 어긋나지 않게 두 절을 통째로 비교한다.
        sections = []
        for path in PHASES:
            text = self._text(path)
            sections.append(text[text.index("## Step 5.5") : text.index("## Step 6")])
        self.assertEqual(sections[0], sections[1])
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_visualize_skill_contract tests.test_gx_arch_pipeline -v`
Expected: 새 테스트 대부분 FAIL(`--scope`가 아직 있음 등). `test_both_pipelines_keep_the_same_gate_text`는 이미 PASS일 수 있다.

- [ ] **Step 3: SKILL.md 개정**

1. frontmatter `argument-hint`와 `## 호출 계약`의 코드 블록 한 줄에서 `[--scope session|all] [--map-dir <path>] [--domain <name>]`을 `[--map-dir <path>] [--domain <name>] [--changed-since <ref>] [--labels <path>]`로 바꾼다(두 곳).

2. 호출 계약 목록에서 `--scope`, `--map-dir`, `--domain` 세 줄을 다음으로 바꾼다.

```markdown
- `--map-dir`: `service` 뷰의 출력 폴더. 기본값은 `.dev/architecture/`.
- `--domain`: `service` 뷰에서 그 도메인만 다시 그린다. 생략하면 전 도메인을 그린다.
- `--changed-since`: `service` 뷰에서 `<ref>`와 HEAD의 공통 조상 이후 새로 생기거나 바뀐 구조를 `[신규]`·`[변경]`으로 표시한다. 자세한 내용은 아래 "아키텍처 맵" 절을 읽는다.
- `--labels`: `service` 뷰의 한국어 라벨 파일. 스캔 라벨과 정확히 일치하는 항목만 바꾼다.
```

3. `## 뷰 라우터`의 `- `구조` → `service`; `서비스 관계` → `service`` 줄을 `- `구조`·`전체 구조`·`아키텍처` → `service`; `서비스 관계` → `service``로 바꾼다.

4. 뷰 표의 service 행을 `| `service` | 서비스·화면·API·테이블 관계는 무엇인가? | 코드 스캔(진입점 체인), 프로젝트 context | 1차 필수 |`로 바꾼다.

5. `## 입력 수집 계약` 제목 바로 아래에 한 줄을 넣는다.

```markdown
`service` 뷰는 이 수집을 쓰지 않는다 — 코드를 직접 스캔한다(아래 "아키텍처 맵" 절).
```

6. `## 실행 절차` 제목 바로 아래에 한 줄을 넣는다.

```markdown
`trace`·`progress`·`impact`·`sequence` 뷰의 절차다. `service` 뷰는 아래 "아키텍처 맵" 절의 명령 하나로 끝난다.
```

같은 절의 5번 항목 전체를 다음으로 바꾼다.

```markdown
5. Archify는 [선택 어댑터 계약](references/archify-adapter.md)에 따라 validate 후 deliver한다. 렌더 명령은 `python scripts/render_archify.py ${DEV_DIR}/visual/{view}.json ${DEV_DIR}/visual --project-root <PROJECT_ROOT>`다 — `--archify-command`는 생략한다(스크립트가 4번과 같은 `ensure_archify()`로 스스로 찾는다). 명시적 override는 테스트용이며, 그 값이 셸을 거치며 깨질 수 있다([선택 어댑터 계약](references/archify-adapter.md#archify-명령-계약)). Archify가 실패하면 Mermaid, 이어서 static을 시도한다. 명시한 `mermaid` 또는 `static`은 `scripts/render_fallback.py`로 렌더링한다.
```

7. `## 누적 아키텍처 맵` 절 전체(그 제목부터 `스캔이 **0개 노드**를 반환하면 ... 중단한다.` 단락까지)를 다음으로 바꾼다.

````markdown
## 아키텍처 맵 (`service` 뷰)

`service` 뷰는 언제나 **프로젝트 전체를 다시 스캔해** `${MAP_DIR}/`(기본 `.dev/architecture/`)를 새로 만든다. 이번 작업분만 따로 그리는 모드는 없다 — 변경 파일만 스캔하면 컨트롤러 → 서비스에서 체인이 끊긴다(2026-09-28 콜드런). 이번 사이클에서 무엇이 바뀌었는지는 `--changed-since`로 전체 맵 위에 표시한다. 산출물은 단발성이며 커밋하지 않는다.

### 실행 — 명령 하나

전체 스캔은 저장소 규모에 따라 시간이 걸릴 수 있음을 먼저 알리고 실행한다.

```text
python scripts/build_map.py <PROJECT_ROOT> [--map-dir <MAP_DIR>] [--changed-since <REF>] [--domain <DOMAIN>] [--labels <LABELS_JSON>]
```

이 명령이 스캔 → 변경 표시 → 라벨 적용 → 도메인 분할 → 도메인별 검증·렌더(Archify, 실패하면 Mermaid → static) → Mermaid 자산 확보 → 인덱스 생성을 모두 수행하고 JSON 보고를 stdout에 낸다. 단계를 손으로 나눠 실행하거나 중간 파일을 직접 만들지 않는다. 종료 코드는 `validation_status`가 `failed`면 1, 아니면 0이다.

- `--changed-since <REF>`: `<REF>`와 HEAD의 공통 조상 이후 새로 생기거나 바뀐 구조를 표시한다. gx-dev·gx-tdd Step 5.5는 `BASE_BRANCH`를 넘긴다. 단독 호출에서는 사용자가 "이번 브랜치에서 바뀐 것"처럼 비교 기준을 말했을 때만 넘기고, 아니면 생략한다. git 저장소가 아니거나 기준을 정할 수 없으면 맵은 그대로 만들고 표시만 생략하며, 보고의 `changes.reason`에 이유가 남는다.
- `--labels <LABELS_JSON>`: 한국어 라벨을 붙일 때만 쓴다. `context/{도메인}/glossary.md`를 읽고, 스캔 라벨과 **정확히 같은 이름**이 용어집에 있는 항목만 `{"스캔 라벨": "한국어 라벨"}` JSON 파일로 만든다. 스캔 라벨은 클래스명(`UserService`) 또는 `클래스.메서드`(`UserController.login`)이고, `python scripts/scan_entrypoints.py <PROJECT_ROOT>` 출력의 `label`에서 확인한다. 부분 일치·추측으로 항목을 만들지 않는다 — 근거가 없으면 이 인자를 생략하고 기술 식별자를 그대로 둔다. 원래 이름은 `technical_label`에 보존된다.
- `--domain <DOMAIN>`: 그 도메인만 다시 그린다. 다른 도메인의 산출물은 그대로 둔다.
- `--map-dir <MAP_DIR>`: 출력 폴더. 프로젝트 밖 경로는 사용자가 명시했을 때만 쓴다.

### 출력 구조 — `아키텍처-맵.html` 하나만 열면 된다

```text
${MAP_DIR}/
  아키텍처-맵.html              ← 인덱스. 이것만 열면 된다
  domains/{domain}.html          도메인별 그림·표
  ir/{domain}.ir.json            GX IR (사람이 읽는 정본)
  receipts/{domain}.receipt.json 영수증
  receipts/{domain}.archify.json 중간 산출물(Archify를 시도한 도메인만)
  assets/mermaid.min.js          Mermaid로 폴백한 도메인이 있을 때만
```

### 무엇이 표시되는가

`--changed-since`를 주면 기준 커밋의 소스를 임시 폴더에 꺼내 같은 스캐너로 스캔하고, 두 결과를 노드 ID로 비교한다. 작업 트리·인덱스는 건드리지 않고, 커밋하지 않은 변경도 현재 쪽에 포함된다.

| 표시 | 판정 | 그림에서 |
|---|---|---|
| 신규 | 현재 스캔에만 있는 노드·관계 | 라벨 앞 `[신규]`, 초록 채움(Mermaid), 굵은 선 |
| 변경 | 양쪽에 있고 HTTP 경로(`technical_label`)나 나가는 관계가 달라진 노드 | 라벨 앞 `[변경]`, 노랑 채움(Mermaid) |
| 삭제 | 기준에만 있는 테이블 외 노드 | 그릴 수 없으므로 인덱스와 보고에 목록으로만 |

구조가 바뀐 것만 표시한다. 메서드 본문만 바뀐 경우는 그림이 달라지지 않으므로 표시하지 않고, 테이블은 "변경"이 되지 않는다. 각 도메인 HTML 맨 위 배너가 기준 ref·커밋과 신규·변경 수를 알리고, 변경이 없는 도메인에는 "구조 변경이 없습니다"를 띄운다. 인덱스의 "이번 변경" 절이 바뀐 도메인과 항목을 모아 보여 준다.

### 도메인 분할

실제 저장소 규모(86노드)를 한 장으로 그리면 Archify 검증이 대량으로 실패하고 사람이 읽을 수도 없다(설계서 §5.7). 그래서 노드를 도메인별로 나눠 각각 별도 문서로 그린다.

- 도메인은 파일 경로에서 계층 폴더(`controller`·`service`·`facade`·`repository`·`dao`·`mapper`·`web`·`api`) 바로 앞 세그먼트다. 서비스 인터페이스와 `{X}Impl`은 한 노드로 합쳐지고, 이름이 `*Facade`인 클래스는 서비스 계층으로 본다. 추출 규칙은 [진입점 체인 추출 규칙](references/entrypoint-rules.md)을 읽는다.
- 테이블 노드는 자신을 참조하는 모든 도메인에 복제된다. 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않으므로 조용히 지우지 않고 관련 도메인 IR의 `missing_inputs`에 `cross-domain-edge`로 남기며, 보고의 `cross_domain_edge_count`가 실제 엣지 수를 센다.
- **도메인마다 개별로 Archify에 넣어 판정한다.** 한 저장소 안에서 어떤 도메인은 Archify 그림이, 어떤 도메인은 Mermaid 그림이 나오는 것이 정상이며 보고에 드러난다. Mermaid로 떨어진 도메인이 있으면 `assets/mermaid.min.js`를 1회 확보해 브라우저에서 실제 그림으로 그린다. 확보하지 못하면 소스만 보이는 HTML이 최종 상태다.
- 검증에 실패한 도메인의 이전 `ir/{domain}.ir.json`은 덮어쓰지 않는다. 전체 실행에서는 이번 스캔에 없는 도메인의 이전 산출물을 지운다.
- 스캔은 UTF-8로 읽지 못한 소스를 CP949로 재시도하고, 둘 다 실패한 파일은 `skipped`에 담는다. 관계를 해소하지 못한 엣지는 `unresolved_edges`로 남는다 — "노드가 없다"와 "관계를 해소하지 못했다"는 다른 사실이다. SQL 본문은 IR에 담지 않는다.
- 스캔이 **0개 노드**를 반환하면 빈 IR을 쓰지 않고 `missing_inputs: ["entrypoint-scan"]`으로 실패한다.

### 보고

`build_map.py`의 JSON 보고가 `service` 뷰의 최종 report다. 도메인이 여럿이라 단일 경로 필드를 쓰지 않는다.

| 필드 | 내용 |
|---|---|
| `view` | `service` |
| `map_dir`, `index_path` | 출력 폴더와 `아키텍처-맵.html` 경로. 실패 시 `index_path`는 `null` |
| `validation_status` | 도메인 하나라도 `failed`거나 도메인이 없으면 `failed`, 아니면 `fallback`이 하나라도 있으면 `fallback`, 전부 Archify면 `verified` |
| `domains[]` | 도메인마다 `domain`, `backend`, `validation_status`, `html_path`, `ir_path`, `receipt_path`, `missing_inputs`, `added`, `changed` |
| `changes` | `--changed-since`가 없으면 `null`. 있으면 `available`, `base_ref`, 그리고 `base_commit`·`added`·`changed`·`added_edges`·`removed[]` 또는 `reason` |
| `cross_domain_edge_count` | 어느 도메인 그림에도 담기지 못한 엣지 수 |
| `unresolved_edge_count`, `skipped` | 스캔 진단 |
| `mermaid_asset` | Mermaid 폴백 도메인이 있을 때만: `available`, `attempts` |
| `missing_inputs` | 스캔이 0개 노드면 `["entrypoint-scan"]` |
| `labels_applied` | `--labels`로 바꾼 노드 수 |

사용자에게는 먼저 `index_path`(`아키텍처-맵.html`)를 안내하고, 도메인별 `backend`·`validation_status`, `changes` 요약(신규·변경·삭제 수 또는 생략 이유), `cross_domain_edge_count`·`unresolved_edge_count`·`skipped`를 그대로 전한다. Archify가 아닌 도메인을 Archify 성공으로 표현하지 않는다.
````

8. `## 출력과 영수증 계약`의 첫 문장 앞에 한 줄을 넣는다.

```markdown
`service` 뷰는 위 "아키텍처 맵" 절의 보고를 쓴다. 아래는 나머지 뷰의 계약이다.
```

같은 절의 `확보하지 못했거나 애초에 시도하지 않았으면(예: `--scope session`) 소스 코드만 보여준다`를 `확보하지 못했거나 애초에 시도하지 않았으면(예: `sequence` 뷰) 소스 코드만 보여준다`로 바꾼다.

9. 개정 뒤 `grep -n "scope\|세션\|누적 아키텍처 맵" .claude/skills/gx-visualize/SKILL.md`로 남은 흔적이 없는지 확인한다. 남으면 새 흐름에 맞게 고친다.

- [ ] **Step 4: 참조 문서 개정**

`references/gx-mapping.md`:
- "산출물에서 IR로" 표의 `진입점 체인 스캔` 행 첫 칸을 `` `entrypoint-scan` (진입점 체인 스캔) ``으로 바꾼다.
- "view별 필수·보조 입력" 표의 service 행을 `| `service` | 진입점 체인 스캔(`entrypoint-scan`) | `context` | 스캔이 0개 노드면 failed; 런타임 토폴로지는 추정하지 않음 |`로 바꾼다.
- `모두 없을 때만 표의 합성 그룹명(`codemap|design`, `design|call-evidence`)을 넣는다`를 `모두 없을 때만 표의 합성 그룹명(`design|call-evidence`)을 넣는다`로 바꾼다.

`references/archify-adapter.md:41`의 `(이 프로젝트 정책상 커밋되는 `.dev/{branch}/visual/*` 산출물처럼)`을 `(`.dev/` 아래의 시각화 산출물처럼)`으로 바꾼다.

- [ ] **Step 5: phase-complete Step 5.5 개정 (두 파일 동일)**

`.claude/skills/gx-dev/phases/phase-complete.md`와 `.claude/skills/gx-tdd/phases/phase-complete.md`에서 `## Step 5.5: 구현 구조 시각화 제안`부터 `## Step 6` 바로 앞까지를 **똑같이** 다음으로 바꾼다.

````markdown
## Step 5.5: 구현 구조 시각화 제안

**헤드리스 판정 먼저**: ARGS에 `--non-interactive`가 있거나 `${DEV_DIR}/ralph.lock`이 존재하면 이 절 전체를 **strict no-op**으로 건너뛴다. 질문하지 않고 기존 완료 출력을 바꾸지 않는다 — 응답할 사용자가 없다. (gx-ralph 루프는 완료 처리를 gx-ralph-iterate Step 5.5에서 직접 수행하고 phase-complete를 거치지 않으므로, 이 판정은 현재 도달하지 않는 향후 진입 경로를 위한 예약이다.)

대화형 세션이면 아래를 질문한다. 구조화된 질문 도구가 없는 세션에서는 같은 선택지를 **자연어로 묻고 실제 답을 기다린다** — 도구가 없다는 이유로 건너뛰지 않는다. "질문 도구가 없음"과 "응답할 사용자가 없음"은 다른 조건이다: 앞의 것은 묻는 방식만 바뀌고, 뒤의 것만 strict no-op이다.

```
AskUserQuestion(
  questions: [{
    header: "구조 시각화",
    question: "이번 사이클에서 구현된 구조를 아키텍처 맵에 표시할까요?",
    multiSelect: false,
    options: [
      { label: "아키텍처 맵 갱신", description: "프로젝트 전체를 다시 스캔해 .dev/architecture/를 갱신하고, 이번 사이클에서 새로 생기거나 바뀐 구조를 [신규]·[변경]으로 표시합니다" },
      { label: "아니요", description: "시각화하지 않고 완료합니다" }
    ]
  }]
)
```

- **아키텍처 맵 갱신** → 프로젝트 전체를 다시 스캔하므로 저장소 규모에 따라 시간이 걸릴 수 있음을 먼저 알린 뒤, `oh-my-gx:gx-visualize`를 `service --project-root ${PROJECT_ROOT} --changed-since ${BASE_BRANCH}`로 호출한다. 선택이 곧 동의이므로 다시 묻지 않는다. **svn이면** `--changed-since`를 넘기지 않는다 — 변경 표시는 git 기준 시점이 필요하다. 이때는 맵을 변경 표시 없이 갱신했다고 함께 보고한다.
- **아니요** → 건너뛴다.

호출 결과의 `index_path`·`validation_status`, 도메인별 `backend`·`validation_status`, `changes`(신규·변경·삭제 수 또는 생략 이유)를 그대로 보고한다. `index_path`가 없으면 `visualization_status: failed`로 보고하고 경로를 성공처럼 제시하지 않는다.

이 절의 실패·누락·fallback은 **커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다.** Step 1~2가 이미 실패했다면 시각화 성공으로 그 실패를 덮지 않는다.

````

`.claude/skills/gx-tdd/references/maintenance-notes.md:34`의 `헤드리스 판정·AskUserQuestion 질문·scope 옵션·실패 무관 원칙`을 `헤드리스 판정·AskUserQuestion 질문·변경 표시 옵션·실패 무관 원칙`으로 바꾸고, 같은 줄의 `(린트 미검사, 수동 동기화. `tests/test_gx_arch_pipeline.py`가 각 파일에 개별적으로 존재를 검사할 뿐 두 파일의 동일성 자체는 검사하지 않는다)`를 `(린트 미검사. `tests/test_gx_arch_pipeline.py`의 `test_both_pipelines_keep_the_same_gate_text`가 두 절의 동일성을 검사한다)`로 바꾼다.

- [ ] **Step 6: 통과 확인**

Run: `python -m unittest tests.test_gx_visualize_skill_contract tests.test_gx_arch_pipeline tests.test_gx_visualize_guide tests.test_gx_visualize_docs -v`
Expected: 모두 PASS.

Run: `python scripts/sync-codex-resources.py --check`
Expected: exit 0.

Run (Bash `timeout: 600000`): `bash scripts/lint-consistency.sh`
Expected: 36/36 통과.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-visualize/SKILL.md .claude/skills/gx-visualize/references/gx-mapping.md .claude/skills/gx-visualize/references/archify-adapter.md .claude/skills/gx-dev/phases/phase-complete.md .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-tdd/references/maintenance-notes.md tests/test_gx_visualize_skill_contract.py tests/test_gx_arch_pipeline.py
git diff --cached --stat
git commit -m "docs: 세션분 시각화를 없애고 전체 맵의 변경 표시로 계약을 바꾼다"
```

---

### Task 9: gx-commit이 시각화 산출물을 스테이징하지 않게 한다

**Files:**
- Modify: `.claude/skills/gx-commit/SKILL.md` (커밋 실행 1번·5번)
- Create: `tests/test_gx_commit_visualize_outputs.py`

**Interfaces:**
- Produces: gx-commit 5번의 `git reset` 명령이 `'.dev/architecture'`와 `'.dev/*/visual/*'`을 포함한다.

배경: oh-my-gx 자체는 `.gitignore`로 산출물을 제외하지만, 소비 프로젝트는 setup 정책상 `.dev/`를 커밋한다(`gx-dev/phases/phase-setup.md`). 그래서 다음 gx-commit의 `git add -A`에 3.4MB짜리 Mermaid 자산과 절대경로가 든 영수증이 들어간다. `'.dev/*/visual'`(끝의 `/*` 없이)은 git pathspec에서 하위 파일과 매치되지 않는다 — 2026-09-28 실측.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_gx_commit_visualize_outputs.py`:

```python
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMMIT_SKILL = REPO / ".claude" / "skills" / "gx-commit" / "SKILL.md"


def _reset_command(text):
    match = re.search(r"`(git reset -q -- [^`]+)`", text)
    return match.group(1) if match else None


class CommitExcludesVisualizeOutputsTests(unittest.TestCase):
    def setUp(self):
        self.text = COMMIT_SKILL.read_text(encoding="utf-8")

    def test_reset_command_names_both_output_locations(self):
        command = _reset_command(self.text)
        self.assertIsNotNone(command)
        self.assertIn("'.dev/architecture'", command)
        self.assertIn("'.dev/*/visual/*'", command)

    def test_other_slug_question_does_not_ask_about_visualize_outputs(self):
        self.assertIn("gx-visualize의 단발성 산출물", self.text)

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_documented_pathspecs_actually_unstage_the_outputs(self):
        """문서의 pathspec을 실제 저장소에서 실행한다 - 문자열 검사로는 매치 여부를 알 수 없다."""
        specs = re.findall(r"'([^']+)'", _reset_command(self.text))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                return subprocess.run(
                    ["git", "-c", "user.name=gx", "-c", "user.email=gx@example.com", "-c", "commit.gpgsign=false", *args],
                    cwd=root, check=True, capture_output=True, text=True,
                )

            git("init", "-q")
            git("commit", "-q", "--allow-empty", "-m", "init")
            for relative in (
                ".dev/architecture/domains/user.html",
                ".dev/architecture/assets/mermaid.min.js",
                ".dev/feat-x/visual/trace.html",
                ".dev/feat-x/visual/sub/trace.json",
                ".dev/feat-x/state.md",
                "src/App.java",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n", encoding="utf-8")
            git("add", "-A")
            subprocess.run(["git", "reset", "-q", "--", *specs], cwd=root, check=False, capture_output=True)
            staged = git("diff", "--cached", "--name-only").stdout.split()
        self.assertEqual(sorted(staged), [".dev/feat-x/state.md", "src/App.java"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_gx_commit_visualize_outputs -v`
Expected: `test_reset_command_names_both_output_locations`, `test_other_slug_question_does_not_ask_about_visualize_outputs` FAIL, `test_documented_pathspecs_actually_unstage_the_outputs`는 staged 목록에 `.dev/architecture/...`가 남아 FAIL.

- [ ] **Step 3: 구현**

`.claude/skills/gx-commit/SKILL.md`의 `## 커밋 실행` 1번 항목 끝에 문장을 덧붙인다.

```markdown
 단 `.dev/architecture/`와 `.dev/*/visual/`은 gx-visualize의 단발성 산출물이므로 묻지 않는다 — 5단계에서 스테이징하지 않는다.
```

5번 항목의 두 줄을 다음으로 바꾼다.

```markdown
   - 제외 파일 없음: `git add -A` 후 런타임 파일과 시각화 산출물을 unstage한다: `git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' '.dev/architecture' '.dev/*/visual/*' 2>/dev/null` (루프 락·반복 로그는 커밋 대상이 아니다 — 커밋되면 다른 사용자의 라우팅·게이트 판별이 오작동한다. 시각화 산출물은 매 실행 다시 만드는 단발성이고 Mermaid 자산만 3.4MB다. `'.dev/*/visual'`처럼 끝의 `/*`를 빼면 하위 파일과 매치되지 않는다)
   - 제외 파일 있음: `git add <나머지 파일 각각 지정>` (위 런타임 파일과 시각화 산출물은 지정하지 않는다)
```

- [ ] **Step 4: 통과 확인**

Run: `python -m unittest tests.test_gx_commit_visualize_outputs -v`
Expected: 모두 PASS.

Run: `python scripts/sync-codex-resources.py --check` → exit 0
Run: `python -m unittest discover -s tests -p "test_codex_*.py"` → 전부 PASS
Run (Bash `timeout: 600000`): `bash scripts/lint-consistency.sh` → 36/36

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-commit/SKILL.md tests/test_gx_commit_visualize_outputs.py
git diff --cached --stat
git commit -m "fix: gx-commit이 시각화 산출물을 스테이징하지 않게 한다"
```

---

### Task 10: 실제 환경 수용 검증 (컨트롤러가 직접 수행)

이 태스크는 **구현자 서브에이전트에게 맡기지 않는다.** 콜드런은 새 에이전트를 띄워야 하는데 구현자는 하위 에이전트를 띄우지 않는다. 컨트롤러가 직접 실행하고 결과를 원장에 기록한다. 결함이 나오면 수정 태스크를 추가한다.

**Files:** 없음(scratchpad에만 쓴다). 결과는 SDD 원장에 기록한다.

- [ ] **Step 1: 전체 회귀**

Run: `python -m unittest discover -s tests -p "test_gx_*.py" 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^FAILED|^OK"`
Expected: 실패는 `test_gx_visualize_routing` 7건뿐.

- [ ] **Step 2: kereb 실제 실행 (읽기 전용)**

```bash
SP=<scratchpad>/accept && rm -rf "$SP" && mkdir -p "$SP"
python .claude/skills/gx-visualize/scripts/build_map.py D:/SQ/kereb-grep-2025-admin/sqisoft-sef-2024 --map-dir "$SP/map" --changed-since c8c2280~1 > "$SP/report.json"; echo "exit=$?"
git -C D:/SQ/kereb-grep-2025-admin/sqisoft-sef-2024 status --short
```

Expected:
- exit 0, `report.json`의 `changes.available == true`, `changes.added >= 5`(기존 시제품: `getVersionPeriod`·`RebService`·테이블 3개 — Facade 인식으로 `RebFacade`가 더해질 수 있다).
- `domains[]`에서 user의 `backend == "archify"`(열 간격 수정 효과, 수용 기준 17).
- reb IR에서 API 노드가 모두 나가는 엣지를 가진다(수용 기준 16):

```bash
PYTHONIOENCODING=utf-8 python -c "
import json,collections
d=json.load(open(r'$SP/map/ir/reb.ir.json',encoding='utf-8'))
out=collections.Counter(e['source'] for e in d['edges'])
print('고립 API:', [n['label'] for n in d['nodes'] if n['kind']=='api' and out[n['id']]==0])"
```

  Expected: `고립 API: []`.
- kereb `git status --short`가 실행 전과 같다(untracked 3건만).

- [ ] **Step 3: 헤드리스 브라우저로 화면 확인 (수용 기준 14)**

도메인 HTML마다 DOM을 덤프해 실제 그림과 표시를 센다.

```bash
CH="/c/Program Files/Google/Chrome/Application/chrome.exe"
for f in "$SP"/map/domains/*.html "$SP/map/아키텍처-맵.html"; do
  URI=$(python -c "import pathlib,sys;print(pathlib.Path(sys.argv[1]).resolve().as_uri())" "$f")
  "$CH" --headless=new --disable-gpu --allow-file-access-from-files --virtual-time-budget=8000 --dump-dom "$URI" > "$f.dom" 2>/dev/null
  echo "$(basename "$f"): svg=$(grep -o '<svg' "$f.dom" | wc -l) 신규=$(grep -o '\[신규\]' "$f.dom" | wc -l) 변경=$(grep -o '\[변경\]' "$f.dom" | wc -l) 배너=$(grep -c 'change-banner' "$f.dom") gxAdded=$(grep -o 'gxAdded' "$f.dom" | wc -l)"
done
```

Expected: 변경이 있는 도메인 HTML마다 `svg>=1`, `신규>=1` 또는 `변경>=1`, `배너=1`. Mermaid 도메인은 `gxAdded>=1`. 인덱스는 `이번 변경` 절이 있다.

그다음 스크린샷 3장(인덱스, Archify 도메인 하나, Mermaid 도메인 하나)을 `--screenshot`으로 찍어 **직접 본다**. 특히 Archify 페이지에서 배너가 Archify 화면에 가려지지 않고 보이는지 확인한다. 가려지면 Task 5의 배너 삽입 위치를 고치는 수정 태스크를 추가한다.

- [ ] **Step 4: 콜드런 두 개 (수용 기준 19)**

이 대화를 모르는 새 에이전트(중간 등급 모델) 두 개를 띄운다. 둘 다 대상 저장소와 oh-my-gx를 읽기 전용으로 두고, 출력은 scratchpad에만 쓰게 한다.
1. 단독: 사용자가 kereb에서 "/gx-visualize 우리 프로젝트에 지금까지 구현된 전체 구조를 그림으로 보여줘"라고 했다. SKILL.md만 보고 실행한다.
2. 파이프라인: gx-dev phase-complete Step 5.5에서 사용자가 "아키텍처 맵 갱신"을 골랐다. `BASE_BRANCH=c8c2280~1`, `PROJECT_ROOT=kereb`로 두고 phase-complete와 SKILL.md만 보고 실행한다.

각자 "문서만으로 결정할 수 없어 추측한 지점"과 "문서와 스크립트가 어긋난 지점"을 보고서로 남기게 한다. 추측 지점이 있으면 SKILL.md 수정 태스크를 추가한다.

- [ ] **Step 5: 기록**

원장에 실행 결과(도메인별 backend, 변경 수, 고립 API 수, DOM 수치, 스크린샷 판정, 콜드런 추측 지점)를 기록한다. Task 11의 문서 수치는 여기서 잰 값을 쓴다.

---

### Task 11: 사용자 문서와 CHANGELOG를 새 흐름으로 맞춘다

**Files:**
- Modify: `README.md` (visualize 절)
- Modify: `docs/gx-visualize-guide.md` (`## 누적 아키텍처 맵` 절)
- Modify: `index.html:1086`
- Modify: `CHANGELOG.md` (v1.34.0 절)
- Modify: `tests/codex-smoke.md` (시각화 절 V1·V4)

**Interfaces:**
- Consumes: Task 10에서 잰 수치(도메인별 backend 등). 수치가 없으면 이 태스크를 시작하지 않는다.

- [ ] **Step 1: README**

`README.md`의 visualize 예시 블록에 한 줄을 추가한다.

```
"우리 프로젝트 전체 구조를 그림으로 보여줘"  ← service  (도메인별 아키텍처 맵)
```

같은 절의 `` `--scope all`은 `.dev/architecture/`에 ... 참고하세요. `` 단락을 다음으로 바꾼다.

```markdown
`service` 뷰(구조)는 매 실행 프로젝트 전체를 다시 스캔해 `.dev/architecture/`에 도메인별 아키텍처 맵을 만듭니다. `아키텍처-맵.html` 하나만 열면 됩니다. gx-dev·gx-tdd 완료 단계에서 "아키텍처 맵 갱신"을 고르면 그 사이클에서 새로 생기거나 바뀐 구조를 `[신규]`·`[변경]`으로 표시합니다. 산출물은 커밋하지 않습니다. 뷰별 입력·출력 계약, 도메인 분할 규칙, 실패 시 문제 해결은 [docs/gx-visualize-guide.md](docs/gx-visualize-guide.md)를 참고하세요.
```

- [ ] **Step 2: 사용 가이드**

`docs/gx-visualize-guide.md`의 `## 누적 아키텍처 맵` 절(그 제목부터 `## 실패와 문제 해결` 바로 앞까지)을 아래로 바꾼다. `{N}`·`{M}`은 Task 10 Step 2에서 잰 도메인 수와 Archify 도메인 수로 채운다. `.dev/{branch-slug}/visual/`은 다른 뷰의 출력으로 가이드의 다른 절에 남아 있어야 한다(`tests/test_gx_visualize_guide.py`가 검사한다).

````markdown
## 아키텍처 맵

구조(`service`) 뷰는 매 실행 프로젝트 전체를 다시 스캔해 도메인별 아키텍처 맵을 만듭니다. 이번 작업분만 따로 그리는 모드는 없습니다 — 변경된 파일만 스캔하면 컨트롤러에서 서비스까지만 이어지고 체인이 끊기기 때문입니다. 이번 사이클에서 무엇이 바뀌었는지는 전체 맵 위에 표시합니다.

### 명령 하나로 만듭니다

```text
python scripts/build_map.py <프로젝트 루트> [--map-dir <출력 폴더>] [--changed-since <기준 ref>] [--domain <도메인>] [--labels <라벨 JSON>]
```

스캔부터 인덱스까지 이 명령이 모두 수행하고 JSON 보고를 출력합니다. gx-dev·gx-tdd 완료 단계에서 "아키텍처 맵 갱신"을 고르면 파이프라인이 기준 브랜치를 `--changed-since`로 넘겨 이 명령을 실행합니다. 전체 스캔은 저장소 규모에 따라 시간이 걸릴 수 있어 실행 전에 먼저 알립니다.

### 산출물은 폴더로 정리되고 인덱스 하나로 모입니다

```text
.dev/architecture/
  아키텍처-맵.html              ← 인덱스. 이것만 열면 전체가 보입니다
  domains/{domain}.html          도메인별 그림·표
  ir/{domain}.ir.json            GX IR (사람이 읽는 정본)
  receipts/{domain}.receipt.json 영수증
  receipts/{domain}.archify.json 중간 산출물(Archify를 시도한 도메인만)
  assets/mermaid.min.js          Mermaid로 그린 도메인이 있을 때만
```

`아키텍처-맵.html`은 도메인마다 이름·노드 수·백엔드(그림인지 표인지)·통과 여부·누락 건수를 카드로 요약하고 각 `domains/{domain}.html`로 링크합니다. 산출물은 커밋하지 않는 단발성이지만 디스크에는 실제로 쌓입니다 — 실측(SEF, 8도메인): 도메인당 약 800KB, 실행당 합계 약 4.70MB. 매 실행 전체를 다시 만들므로 오래된 산출물은 갱신·대체되고, 이번 스캔에 없는 도메인의 옛 산출물은 지워집니다.

### 이번 변경 표시

`--changed-since <기준 ref>`를 주면 기준 커밋과 현재를 같은 스캐너로 스캔해 비교합니다. 커밋하지 않은 변경도 현재 쪽에 포함됩니다.

| 표시 | 뜻 | 그림에서 |
|---|---|---|
| 신규 | 기준 이후 새로 생긴 노드·관계 | 라벨 앞 `[신규]`, 굵은 선 |
| 변경 | HTTP 경로나 나가는 관계가 달라진 노드 | 라벨 앞 `[변경]` |
| 삭제 | 기준에만 있던 노드 | 인덱스의 "이번 변경" 절에 목록으로만 |

메서드 본문만 바뀐 경우는 그림이 달라지지 않으므로 표시하지 않습니다. 각 도메인 페이지 맨 위 배너가 기준과 신규·변경 수를 알려 주고, 변경이 없는 도메인에는 "구조 변경이 없습니다"라고 표시합니다. git 저장소가 아니거나 기준을 찾지 못하면 맵은 그대로 만들고 표시만 생략하며, 인덱스에 그 이유를 적습니다.

### 도메인 분할

실제 저장소 규모를 한 장으로 그리면 Archify 검증이 대량으로 실패하고 사람이 읽기도 어렵습니다. 그래서 노드를 도메인별로 나눠 각각 별도 문서로 그립니다. `--domain`을 주면 그 도메인만 다시 그리고, 생략하면 찾은 전 도메인을 각각 그립니다.

**도메인마다 개별로 Archify에 넣어 판정합니다 — 전부 성공 아니면 전부 실패로 묶지 않습니다.** 한 저장소 안에서 어떤 도메인은 Archify 그림이, 어떤 도메인은 Mermaid 그림이 나오는 것이 정상입니다. 예를 들어 실제 GX 프로젝트(kreb-grep-2025-admin)를 도메인 {N}개로 나눴을 때(2026-09-28) {M}개는 Archify 그림, 나머지는 Mermaid 그림으로 그려졌습니다 — 이 비율은 해당 저장소 한 곳의 실측값이며 다른 프로젝트에 그대로 적용되는 일반적 보장이 아닙니다. Mermaid 도메인도 `assets/mermaid.min.js`를 확보하면 브라우저에서 실제 다이어그램을 그립니다(소스는 접어서 함께 보존) — 확보하지 못하면 소스만 보여줍니다.

테이블 노드는 파일 경로로 도메인을 정하지 않고, 자신을 참조하는 모든 도메인에 복제됩니다. 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않으므로 조용히 지우지 않고, 관련된 각 도메인 IR의 `missing_inputs`에 `cross-domain-edge`로 남기며 건수를 보고에 포함합니다. 검증에 실패한 도메인의 이전 `ir/{domain}.ir.json`은 덮어쓰지 않으므로 다른 도메인의 갱신에는 영향을 주지 않습니다.

### 스캔 범위

진입점 체인(화면 → API → 서비스 → 저장소 → 테이블)만 추출합니다. 서비스 인터페이스와 `{X}Impl` 구현체는 한 노드로 합치고, 이름이 `*Facade`인 클래스도 서비스 계층으로 봅니다. 유틸·DTO·설정 클래스는 넣지 않습니다.

스캔이 UTF-8로 읽지 못한 소스는 CP949로 재시도합니다(오래된 한국어 JSP·Java 코드베이스에 흔합니다). 둘 다 실패한 파일은 크래시시키지 않고 결과의 `skipped`에 담아 보고합니다. 스캔이 0개 노드를 반환하면 빈 IR을 쓰지 않고 `missing_inputs`에 `entrypoint-scan`을 기록한 뒤 중단합니다.
````

- [ ] **Step 3: index.html**

`index.html:1086`의 `<li>`를 다음으로 바꾼다.

```html
          <li>기본 출력은 <code>.dev/{branch-slug}/visual/</code>, 구조(<code>service</code>) 뷰는 도메인별 아키텍처 맵을 <code>.dev/architecture/</code>에 만들고 이번 사이클의 변경을 <code>[신규]</code>·<code>[변경]</code>으로 표시합니다 — 모두 단발성 산출물이며 커밋하지 않습니다</li>
```

- [ ] **Step 4: CHANGELOG**

`CHANGELOG.md`의 `## v1.34.0 (2026-09-18)` 절 전체를 다음으로 바꾼다. 마지막 Fixed 항목의 도메인 수치는 Task 10 Step 2의 값으로 채운다.

```markdown
## v1.34.0 (2026-09-28)

### Added

- `gx-visualize`(18번째 스킬)를 추가한다. GX 작업 산출물을 근거가 추적되는 JSON IR과 한국어 HTML로 변환하며 `trace`·`progress`·`impact`·`service`(1차 필수)와 `sequence`(후속 범위) 다섯 뷰를 다룬다.
- `service` 뷰는 코드를 직접 스캔해 진입점 체인(화면 → API → 서비스 → 저장소 → 테이블)을 도메인별 아키텍처 맵으로 그린다. `python scripts/build_map.py <프로젝트>` 명령 하나가 스캔부터 인덱스까지 수행하고, `.dev/architecture/아키텍처-맵.html` 하나만 열면 전체가 보인다. 도메인마다 Archify 성공·Mermaid 폴백을 개별로 판정하고, Mermaid 도메인도 브라우저에서 실제 그림으로 그린다.
- `--changed-since <ref>`로 기준 이후 새로 생기거나 바뀐 구조를 `[신규]`·`[변경]`으로 표시한다. 기준 커밋을 같은 스캐너로 스캔해 노드 ID로 비교하므로 줄이 밀려도 오판하지 않는다.
- gx-dev·gx-tdd의 phase-complete에 구조 시각화 제안(Step 5.5)을 추가한다. "아키텍처 맵 갱신"을 고르면 그 사이클의 변경을 표시한 전체 맵을 만든다. 헤드리스 세션은 strict no-op이고, 이 단계의 실패는 커밋·PR을 막지 않는다.

### Fixed

- Archify CLI 시그니처를 실제 명령 형식(validate/deliver)으로 고치고, 탐지를 `doctor`로 바꾼다. Archify가 없으면 묻지 않고 1회 자동 설치를 시도하며, 실패해도 Mermaid → 정적 HTML로 폴백한다. 렌더러가 Archify 명령을 스스로 찾으므로 셸을 거친 인자가 깨지지 않는다.
- 서비스 인터페이스와 `{X}Impl` 구현체, 이름이 `*Facade`인 클래스를 체인에 넣어 컨트롤러에서 저장소까지 끊기지 않게 한다.
- Archify 레이아웃의 열 간격을 넓혀 여러 API가 한 서비스로 모이는 도메인도 Archify로 그린다(kreb admin 실측: 도메인 {N}개 중 {M}개).
- 오래된 한국어 코드베이스의 CP949 소스에서 스캔·검증이 죽지 않게 한다.
- gx-commit이 시각화 산출물(`.dev/architecture`, `.dev/*/visual/*`)을 스테이징하지 않는다.
```

(`{N}`·`{M}`은 Task 10에서 잰 실제 값으로 바꾼다. 값을 모르면 이 문장을 쓰지 않는다.)

- [ ] **Step 5: Codex smoke 계약**

`tests/codex-smoke.md` 시각화 절의 V1 행 입력·증거 칸을 다음으로 바꾼다.

```markdown
| V1 | Codex `/skills`에서 gx-visualize 발견 후, 임의 Git 프로젝트에서 `gx-visualize service` 실행 | `python scripts/build_map.py`가 실행되어 `.dev/architecture/아키텍처-맵.html`·`domains/{domain}.html`·`ir/{domain}.ir.json`이 생성됨(매 실행 전체 재스캔, 커밋하지 않음); 도메인마다 개별 판정(일부 Archify·일부 Mermaid 공존이 정상) | 미실행 |
```

V4 행 증거 칸의 끝에 `; 선택지가 "아키텍처 맵 갱신/아니요" 두 개이고, git이면 `--changed-since ${BASE_BRANCH}`가 전달됨`을 덧붙인다.

- [ ] **Step 6: 확인**

Run: `python -m unittest tests.test_gx_visualize_guide tests.test_gx_visualize_docs -v` → 모두 PASS
Run: `grep -n "scope session\|세션분\|--scope" README.md docs/gx-visualize-guide.md index.html CHANGELOG.md tests/codex-smoke.md` → 결과 0줄
Run (Bash `timeout: 600000`): `bash scripts/lint-consistency.sh` → 36/36

- [ ] **Step 7: 커밋**

```bash
git add README.md docs/gx-visualize-guide.md index.html CHANGELOG.md tests/codex-smoke.md
git diff --cached --stat
git commit -m "docs: 사용자 문서를 전체 맵의 변경 표시 흐름으로 맞춘다"
```
