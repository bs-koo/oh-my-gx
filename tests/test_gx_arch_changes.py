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
