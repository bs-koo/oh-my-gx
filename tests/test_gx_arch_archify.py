import importlib.util
import json
import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "render_archify.py"

VALID_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "서비스 구조",
    "nodes": [
        {"id": "n1", "kind": "api", "label": "로그인", "status": "unknown",
         "evidence": [{"kind": "code", "file": "a.java", "line": 1}]}
    ],
    "edges": [],
}


def _module():
    spec = importlib.util.spec_from_file_location("gx_render_archify", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_archify(directory: Path) -> Path:
    """Record argv to argv.log; succeed validate but fail deliver so the adapter falls back.

    render_archify() short-circuits to fallback as soon as validate fails, so a fake
    that always exits 1 would never invoke deliver and argv.log would only ever gain
    one line. Phase-aware exit codes let both commands run and be recorded.
    """
    script = directory / "fake_archify.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "log = Path(__file__).with_name('argv.log')\n"
        "with log.open('a', encoding='utf-8') as handle:\n"
        "    handle.write(json.dumps(sys.argv[1:], ensure_ascii=False) + '\\n')\n"
        "sys.exit(0 if sys.argv[1] == 'validate' else 1)\n",
        encoding="utf-8",
    )
    return script


class ArchifyCommandTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_service_view_maps_to_architecture_diagram_type(self):
        self.assertEqual("architecture", self.m.diagram_type("service"))

    def test_sequence_view_maps_to_sequence_diagram_type(self):
        self.assertEqual("sequence", self.m.diagram_type("sequence"))

    def test_validate_and_deliver_use_real_archify_signature(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.java").write_text("class A {}", encoding="utf-8")
            ir_path = root / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(root)
            out = root / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=root)

            calls = [json.loads(line) for line in (root / "argv.log").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["validate", "architecture", str(ir_path), "--json"], calls[0])
            self.assertEqual(
                ["deliver", "architecture", str(ir_path), str(out / "service.html"), "--json"], calls[1]
            )

    def test_failed_archify_still_produces_fallback_html(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.java").write_text("class A {}", encoding="utf-8")
            ir_path = root / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            out = root / "out"
            result = self.m.render_archify(ir_path, out, ["python", str(_fake_archify(root))], project_root=root)
            self.assertTrue(Path(result["html_path"]).is_file())
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual("fallback", receipt["status"])
            self.assertNotEqual("archify", receipt["backend"])


if __name__ == "__main__":
    unittest.main()
