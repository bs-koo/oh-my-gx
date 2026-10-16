"""실패·빈 스캔이 이전 성공을 현재 결과로 제시하지 않는 회귀 검증."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_gx_arch_build_map import _load, _project, _fake_archify, _git
from test_gx_arch_index import load_builder


class CurrentRunTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.root = self.work / "project"
        self.output = self.work / "map"
        _project(self.root)
        self.builder = _load()
        self.command = _fake_archify(self.work)

    def build(self):
        return self.builder.build_map(self.root, self.output, archify_command=self.command)

    def test_failed_validation_does_not_reuse_previous_success(self):
        controller = self.root / "src/main/java/com/sqi/user/controller/UserController.java"
        controller.write_text(controller.read_text(encoding="utf-8").replace("UserService userService;", "CodeService userService;"), encoding="utf-8")
        first = self.build()
        self.assertEqual(first["validation_status"], "verified")
        with mock.patch.object(self.builder.validator, "validate", return_value={"status": "failed", "errors": ["broken evidence"]}):
            second = self.build()
        self.assertEqual(second["validation_status"], "failed")
        for entry in second["domains"]:
            self.assertIsNone(entry["html_path"])
            self.assertIsNone(entry["ir_path"])
            self.assertTrue(Path(entry["last_good"]["html_path"]).is_file())
        html = Path(second["index_path"]).read_text(encoding="utf-8")
        self.assertIn("broken evidence", html)
        self.assertNotIn('href="domains/user.html"', html)
        self.assertIn('href="domains/user.last-good.html"', html)
        self.assertIn("생성 실패", (self.output / "domains/user.html").read_text(encoding="utf-8"))

    def test_all_source_deletion_keeps_real_git_change_summary(self):
        _git(self.root, "init")
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-m", "baseline")
        self.build()
        for path in self.root.rglob("*"):
            if path.suffix in {".java", ".xml"}:
                path.unlink()
        report = self.builder.build_map(self.root, self.output, changed_since="HEAD", archify_command=self.command)
        self.assertEqual(report["validation_status"], "failed")
        self.assertTrue(report["changes"]["available"])
        self.assertGreater(len(report["changes"]["removed"]), 0)
        self.assertGreater(len(report["changes"]["removed_edges"]), 0)
        text = Path(report["index_path"]).read_text(encoding="utf-8")
        self.assertIn("삭제된 항목", text)
        self.assertNotIn("이후 구조 변경이 없습니다", text)

    def test_empty_scan_publishes_current_empty_state(self):
        self.build()
        with mock.patch.object(self.builder.scanner, "scan", return_value={"nodes": [], "edges": [], "skipped": [], "unresolved_edges": []}):
            report = self.build()
        self.assertEqual(report["validation_status"], "failed")
        html = Path(report["index_path"]).read_text(encoding="utf-8")
        self.assertNotIn('href="domains/user.html"', html)
        self.assertIn("스캔이 노드를 하나도", html)
        self.assertEqual(json.loads((self.output / "run-manifest.json").read_text(encoding="utf-8"))["domains"], [])

    def test_missing_html_and_missing_asset_are_not_diagrams(self):
        report = self.build()
        entry = report["domains"][0]
        Path(entry["html_path"]).unlink()
        entries = load_builder()._collect_domains(self.output, {})
        self.assertEqual(entries[0]["capability"], "failed")

    def test_delete_only_summary_never_says_unchanged(self):
        self.build()
        index = load_builder().build_index(self.output, changes={"available": True, "removed": [{"id": "gone", "label": "OldController"}], "removed_edges": [{"id": "old-edge"}]})
        html = index.read_text(encoding="utf-8")
        self.assertIn("삭제된 항목 1개", html)
        self.assertIn("삭제된 관계 1개", html)
        self.assertNotIn("이후 구조 변경이 없습니다", html)

    def partial(self, domain="user"):
        return self.builder.build_map(self.root, self.output, domain=domain, archify_command=self.command)

    def test_partial_refresh_keeps_other_domains_searchable_as_previous_results(self):
        first = self.build()
        original = (self.output / "domains/code.html").read_bytes()
        result = self.partial()
        self.assertEqual(["user"], [entry["domain"] for entry in result["domains"]])
        self.assertEqual({"code", "user"}, {entry["domain"] for entry in result["map_domains"]})
        retained = next(entry for entry in result["map_domains"] if entry["domain"] == "code")
        self.assertEqual("retained", retained["freshness"])
        self.assertEqual(first["domains"][0]["generated_at"], retained["generated_at"])
        self.assertEqual(original, (self.output / "domains/code.html").read_bytes())
        page = Path(result["index_path"]).read_text(encoding="utf-8")
        self.assertIn('href="domains/code.html"', page)
        self.assertIn("이번 실행에서 갱신하지 않은 이전 결과", page)
        self.assertIn("CodeService", page)

    def test_first_partial_refresh_disables_unrendered_domain_and_external_links(self):
        controller = self.root / "src/main/java/com/sqi/user/controller/UserController.java"
        controller.write_text(controller.read_text(encoding="utf-8").replace("UserService userService;", "CodeService userService;"), encoding="utf-8")
        result = self.partial()
        self.assertFalse((self.output / "domains/code.html").exists())
        part = json.loads((self.output / "ir/user.ir.json").read_text(encoding="utf-8"))
        code_nav = next(entry for entry in part["meta"]["navigation"]["domains"] if entry["name"] == "code")
        self.assertFalse(code_nav["available"])
        external = next(node for node in part["nodes"] if node.get("external_domain") == "code")
        self.assertFalse(external["external_available"])
        states = {entry["domain"]: entry for entry in result["map_domains"]}
        self.assertEqual("not_generated", states["code"]["validation_status"])

    def test_partial_failure_does_not_restore_selected_previous_success(self):
        self.build()
        with mock.patch.object(self.builder.validator, "validate", return_value={"status": "failed", "errors": ["broken"]}):
            result = self.partial()
        states = {entry["domain"]: entry for entry in result["map_domains"]}
        self.assertEqual("failed", states["user"]["validation_status"])
        self.assertEqual("retained", states["code"]["freshness"])
        page = Path(result["index_path"]).read_text(encoding="utf-8")
        self.assertNotIn('href="domains/user.html"', page)
        self.assertIn('href="domains/code.html"', page)

    def test_partial_refresh_does_not_resurrect_removed_or_missing_domain(self):
        self.build()
        (self.output / "domains/code.html").unlink()
        result = self.partial()
        self.assertNotIn('href="domains/code.html"', Path(result["index_path"]).read_text(encoding="utf-8"))
        for path in self.root.rglob("Code*.java"):
            path.unlink()
        result = self.partial()
        self.assertEqual(["user"], [entry["domain"] for entry in result["map_domains"]])

    def test_unknown_domain_keeps_previous_map_with_failure_notice(self):
        self.build()
        result = self.partial("typo")
        self.assertEqual("failed", result["validation_status"])
        page = Path(result["index_path"]).read_text(encoding="utf-8")
        self.assertIn("찾지 못했습니다", page)
        self.assertIn('href="domains/code.html"', page)

    def test_output_directory_reuse_does_not_keep_another_projects_pages(self):
        self.build()
        other = self.work / "other"
        other.mkdir()
        (other / "user/service").mkdir(parents=True)
        (other / "user/service/OtherService.java").write_text("@Service class OtherService {}", encoding="utf-8")
        result = self.builder.build_map(other, self.output, domain="user", archify_command=self.command)
        self.assertEqual(["user"], [entry["domain"] for entry in result["map_domains"]])
        self.assertNotIn("last_good", result["domains"][0])

    def test_successive_partial_runs_never_archive_another_projects_leftover_html(self):
        self.build()
        other = self.work / "other"
        _project(other)
        self.builder.build_map(other, self.output, domain="user", archify_command=self.command)
        result = self.builder.build_map(other, self.output, domain="code", archify_command=self.command)
        self.assertNotIn("last_good", result["domains"][0])

    def test_successive_partial_runs_retain_both_results(self):
        self.partial("user")
        result = self.partial("code")
        self.assertTrue(all(entry.get("html_path") for entry in result["map_domains"]))
        page = Path(result["index_path"]).read_text(encoding="utf-8")
        self.assertIn('href="domains/user.html"', page)
        self.assertIn('href="domains/code.html"', page)

    def test_retained_change_markers_are_not_counted_as_current_changes(self):
        self.build()
        ir_file = self.output / "ir/code.ir.json"
        ir = json.loads(ir_file.read_text(encoding="utf-8"))
        ir["nodes"][0]["change"] = "added"
        ir["meta"]["changes"] = {"available": True, "base_ref": "old-base"}
        ir_file.write_text(json.dumps(ir), encoding="utf-8")
        result = self.partial()
        entry = next(entry for entry in self.builder.index_builder._collect_domains(self.output, {"added": "신규"}) if entry["domain"] == "code")
        self.assertEqual(0, entry["added"])
        self.assertIsNone(entry["changes_meta"])
        self.assertNotIn("old-base", Path(result["index_path"]).read_text(encoding="utf-8"))

    def test_legacy_retained_pages_use_page_links_without_missing_new_anchors(self):
        self.build()
        manifest_file = self.output / "run-manifest.json"
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        for entries in (manifest["domains"], manifest["map_domains"]):
            for entry in entries:
                entry.pop("detail_anchor_prefix", None)
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        controller = self.root / "src/main/java/com/sqi/user/controller/UserController.java"
        controller.write_text(controller.read_text(encoding="utf-8").replace("UserService userService;", "CodeService userService;"), encoding="utf-8")
        result = self.partial()
        page = Path(result["index_path"]).read_text(encoding="utf-8")
        self.assertNotIn('href="domains/code.html#gx-detail-', page)
        part = json.loads((self.output / "ir/user.ir.json").read_text(encoding="utf-8"))
        external = next(node for node in part["nodes"] if node.get("external_domain") == "code")
        viewer = self.builder.fallback_renderer._viewer_module()
        self.assertEqual("code.html", viewer.node_href(external))


if __name__ == "__main__":
    unittest.main()
