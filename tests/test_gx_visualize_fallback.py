import importlib.util
import html
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".claude" / "skills" / "gx-visualize" / "scripts" / "render_fallback.py"
FIXTURE = ROOT / "tests" / "fixtures" / "gx-trace.valid.json"
PROJECT_FIXTURE = ROOT / "tests" / "fixtures" / "gx-visualize-project"


def load_renderer():
    spec = importlib.util.spec_from_file_location("gx_visualize_render_fallback", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(module)
    return module


class VisualFallbackRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def render(self, backend):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output_dir = Path(temporary.name)
        result = self.renderer.render(FIXTURE, output_dir, backend)
        html_text = Path(result["html_path"]).read_text(encoding="utf-8")
        receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
        return result, html_text, receipt

    def write_ir(self, root, **overrides):
        payload = {
            "schema_version": 1,
            "view": "trace",
            "locale": "ko-KR",
            "title": "테스트 시각화",
            "nodes": [
                {
                    "id": "N1",
                    "kind": "requirement",
                    "label": "첫 노드",
                    "technical_label": "service.first",
                    "status": "verified",
                    "evidence": [],
                },
                {
                    "id": "N2",
                    "kind": "function",
                    "label": "둘째 노드",
                    "status": "review",
                    "evidence": [],
                },
            ],
            "edges": [
                {
                    "id": "N1->N2",
                    "source": "N1",
                    "target": "N2",
                    "relation": "realized_by",
                }
            ],
        }
        payload.update(overrides)
        ir_path = root / "input.json"
        ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return ir_path, payload

    @staticmethod
    def mermaid_source(html_text):
        prefix = '<pre class="mermaid-source"><code>'
        start = html_text.index(prefix) + len(prefix)
        end = html_text.index("</code></pre>", start)
        return html.unescape(html_text[start:end])

    def test_static_html_is_self_contained_korean_and_accessible(self):
        result, html_text, receipt = self.render("static")

        self.assertEqual(result["backend"], "static")
        self.assertIn('<html lang="ko">', html_text)
        self.assertIn("요구사항 추적 맵", html_text)
        self.assertIn("범례", html_text)
        self.assertIn("노드 목록", html_text)
        self.assertIn("관계", html_text)
        self.assertIn("근거", html_text)
        self.assertIn("검증됨", html_text)
        self.assertIn("AN-02-001", html_text)
        self.assertIn("EnergyUsageService.findByPeriod", html_text)
        self.assertNotIn("<script>alert(1)</script>", html_text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html_text)
        self.assertNotIn('src="http', html_text)
        self.assertNotIn('href="http', html_text)
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["backend"], "static")

    def test_mermaid_html_preserves_labels_and_has_static_fallback(self):
        result, html_text, receipt = self.render("mermaid")

        self.assertEqual(result["backend"], "mermaid")
        self.assertIn("flowchart LR", html_text)
        self.assertIn("AN-02-001", html_text)
        self.assertIn("/api/v1/energy?&lt;script&gt;alert(1)&lt;/script&gt;", html_text)
        self.assertIn("Mermaid를 실행할 수 없어도", html_text)
        self.assertIn("노드 목록", html_text)
        self.assertNotIn("<script>alert(1)</script>", html_text)
        self.assertEqual(receipt["backend"], "mermaid")

    def test_mermaid_source_encodes_all_user_text_without_grammar_injection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root)
            payload["nodes"][0]["label"] = 'A\n  injected["가짜"] --> n9'
            payload["nodes"][0]["technical_label"] = 'C:\\work\\file" |[]{}()'
            payload["edges"][0]["relation"] = '연결\n  injected --> n1| "\\[]{}()'
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

            self.assertEqual(len(source.splitlines()), 4)
            self.assertNotIn("injected", source)
            self.assertNotIn("C:\\work", source)
            self.assertNotIn(' |[]{}()', source)
            self.assertIn("#65;#10;#32;#32;", source)
            self.assertIn("#67;#58;#92;#119;", source)
            self.assertIn("#34;#32;#124;#91;#93;#123;#125;#40;#41;", source)
            self.assertIn("#50672;#44208;#10;#32;#32;", source)

    def test_template_tokens_in_title_and_labels_remain_literal_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, title="{{STATIC_CONTENT}}")
            payload["nodes"][0]["label"] = "{{MERMAID_SECTION}}"
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

            self.assertIn("<title>{{STATIC_CONTENT}}</title>", html_text)
            self.assertIn("<h1>{{STATIC_CONTENT}}</h1>", html_text)
            self.assertIn("<h3>{{MERMAID_SECTION}}</h3>", html_text)
            self.assertEqual(html_text.count('id="nodes-title"'), 1)
            self.assertEqual(html_text.count('id="mermaid-title"'), 1)

    def test_output_is_deterministic_and_sorted_by_stable_ids(self):
        _, first_html, first_receipt = self.render("mermaid")
        _, second_html, second_receipt = self.render("mermaid")

        self.assertEqual(first_html, second_html)
        self.assertEqual(first_receipt, second_receipt)
        self.assertLess(first_html.index("AN-02-001"), first_html.index("AN-03-001"))
        self.assertLess(first_html.index("AN-03-001"), first_html.index("DE-13-001"))

    def test_failed_validation_writes_receipt_and_does_not_render_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid_ir = root / "invalid.json"
            invalid_ir.write_text("{}", encoding="utf-8")
            output_dir = root / "output"

            with self.assertRaisesRegex(ValueError, "IR 검증 실패"):
                self.renderer.render(invalid_ir, output_dir, "static")

            receipt_path = output_dir / "trace.receipt.json"
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["status"], "failed")
            self.assertFalse((output_dir / "trace.html").exists())

    def test_failed_rerender_uses_input_view_and_invalidates_stale_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="impact")
            output_dir = root / "output"
            first = self.renderer.render(ir_path, output_dir, "static")
            self.assertTrue(Path(first["html_path"]).is_file())
            self.assertEqual(
                json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))["status"],
                "valid",
            )

            payload["nodes"][0]["status"] = "not-a-status"
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "IR 검증 실패"):
                self.renderer.render(ir_path, output_dir, "static")

            receipt_path = output_dir / "impact.receipt.json"
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["status"], "failed")
            self.assertFalse((output_dir / "impact.html").exists())
            self.assertFalse((output_dir / "trace.receipt.json").exists())

    def test_unknown_backend_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "backend"):
                self.renderer.render(FIXTURE, Path(temporary), "canvas")

    def test_project_root_is_forwarded_when_rendering_real_dev_visual_ir(self):
        ir_path = PROJECT_FIXTURE / ".dev" / "feat-energy" / "visual" / "trace.json"
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(
                ir_path,
                Path(temporary),
                "static",
                project_root=PROJECT_FIXTURE,
            )

        self.assertEqual(result["backend"], "static")

    def test_binary_locator_is_rendered_without_requiring_a_line_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / "DE-13.xlsx").write_bytes(b"PK\x03\x04\xff\xfe")
            ir_path, payload = self.write_ir(project)
            payload["nodes"][0]["evidence"] = [
                {
                    "file": "DE-13.xlsx",
                    "kind": "test",
                    "locator": {"type": "xlsx", "sheet": "단위테스트", "cell": "B12"},
                }
            ]
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(
                ir_path,
                project / "output",
                "static",
                project_root=project,
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("단위테스트", html_text)
        self.assertIn("B12", html_text)


if __name__ == "__main__":
    unittest.main()
