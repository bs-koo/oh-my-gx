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


if __name__ == "__main__":
    unittest.main()
