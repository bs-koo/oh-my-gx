import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".claude" / "skills" / "gx-visualize" / "scripts" / "build_index.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("gx_visualize_build_index", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(module)
    return module


class BuildIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()

    def _write_domain(self, map_dir, domain, *, nodes=2, edges=1, missing=0, unresolved=0, backend="archify", status="valid", marks=(), changes=None):
        ir_dir = map_dir / "ir"
        receipts_dir = map_dir / "receipts"
        ir_dir.mkdir(parents=True, exist_ok=True)
        receipts_dir.mkdir(parents=True, exist_ok=True)
        ir = {
            "schema_version": 1,
            "view": "service",
            "locale": "ko-KR",
            "title": f"{domain} 도메인",
            "nodes": [
                {
                    "id": f"{domain}-n{i}",
                    "kind": "service",
                    "label": f"{domain} 노드 {i}",
                    "status": "verified",
                    "evidence": [{"file": f"{domain}/File{i}.java", "line": 1, "kind": "code"}],
                }
                for i in range(nodes)
            ],
            "edges": [
                {"id": f"{domain}-e{i}", "source": f"{domain}-n0", "target": f"{domain}-n{(i + 1) % max(nodes, 1)}", "relation": "calls"}
                for i in range(edges)
            ],
            "missing_inputs": ["cross-domain-edge"] * missing,
            "unresolved_edges": [{"source": f"{domain}-n0", "target": "?", "relation": "calls"}] * unresolved,
        }
        for index, change in enumerate(marks):
            ir["nodes"][index]["change"] = change
        if changes is not None:
            ir["meta"] = {"changes": changes}
        (ir_dir / f"{domain}.ir.json").write_text(json.dumps(ir, ensure_ascii=False), encoding="utf-8")
        receipt = {"status": status, "backend": backend, "errors": [], "warnings": [], "node_count": nodes, "edge_count": edges, "missing_inputs": []}
        (receipts_dir / f"{domain}.receipt.json").write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")

    def _write_fixture_map(self, map_dir):
        self._write_domain(map_dir, "auth", nodes=3, edges=2, missing=0, unresolved=0, backend="archify", status="valid")
        self._write_domain(map_dir, "reb", nodes=4, edges=2, missing=2, unresolved=1, backend="mermaid", status="fallback")
        self._write_domain(map_dir, "config", nodes=1, edges=0, missing=0, unresolved=0, backend="static", status="fallback")

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

    def test_index_lists_every_domain_with_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_fixture_map(map_dir)
            index_path = self.builder.build_index(map_dir)
            html_text = index_path.read_text(encoding="utf-8")

        for domain in ("auth", "reb", "config"):
            self.assertIn(domain, html_text)
        self.assertIn("노드 3개", html_text)
        self.assertIn("archify", html_text)
        self.assertIn("mermaid", html_text)
        self.assertIn("static", html_text)
        self.assertIn("통과", html_text)
        self.assertIn("폴백", html_text)

    def test_index_links_point_to_domains_subfolder(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_fixture_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")

        self.assertIn("domains/auth.html", html_text)
        self.assertIn("domains/reb.html", html_text)
        self.assertIn("domains/config.html", html_text)

    def test_index_marks_fallback_domains_distinctly(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_fixture_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")

        self.assertIn("domain-diagram", html_text)  # archify와 mermaid 둘 다 그림
        self.assertIn("domain-table", html_text)  # static은 표만
        auth_card = html_text[html_text.index('<h3>auth</h3>') - 40 : html_text.index("</article>", html_text.index("<h3>auth</h3>"))]
        config_card = html_text[html_text.index('<h3>config</h3>') - 40 : html_text.index("</article>", html_text.index("<h3>config</h3>"))]
        self.assertIn("domain-diagram", auth_card)
        self.assertIn("domain-table", config_card)

    def test_index_reports_missing_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_fixture_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")

        reb_card = html_text[html_text.index("<h3>reb</h3>") : html_text.index("</article>", html_text.index("<h3>reb</h3>"))]
        self.assertIn("누락 입력 2건", reb_card)
        self.assertIn("미해소 관계 1건", reb_card)

        auth_card = html_text[html_text.index("<h3>auth</h3>") : html_text.index("</article>", html_text.index("<h3>auth</h3>"))]
        self.assertIn("누락 없음", auth_card)

    def test_index_is_deterministic(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_map, second_map = Path(first_dir), Path(second_dir)
            self._write_fixture_map(first_map)
            self._write_fixture_map(second_map)
            first_html = self.builder.build_index(first_map).read_text(encoding="utf-8")
            second_html = self.builder.build_index(second_map).read_text(encoding="utf-8")

        strip_timestamp = lambda text: re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "TS", text)
        self.assertEqual(strip_timestamp(first_html), strip_timestamp(second_html))

    def test_index_reuses_fallback_css_not_a_new_design_system(self):
        css_path = MODULE_PATH.parent.parent / "templates" / "fallback.css"
        css_text = css_path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            self._write_fixture_map(map_dir)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")

        self.assertIn(css_text.strip().splitlines()[0], html_text)

    def test_no_domains_reports_honestly_instead_of_blank_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            map_dir = Path(temporary)
            (map_dir / "ir").mkdir(parents=True)
            (map_dir / "receipts").mkdir(parents=True)
            html_text = self.builder.build_index(map_dir).read_text(encoding="utf-8")

        self.assertIn("생성된 도메인 산출물이 없습니다", html_text)


if __name__ == "__main__":
    unittest.main()
