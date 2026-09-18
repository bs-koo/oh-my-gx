import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-java"
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "scan_entrypoints.py"


def _module():
    spec = importlib.util.spec_from_file_location("gx_scan_entrypoints", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JavaSpringScanTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_extracts_api_service_repository_nodes(self):
        result = self.scan(FIXTURE)
        kinds = {node["kind"] for node in result["nodes"]}
        self.assertEqual({"api", "service", "repository"}, kinds)

    def test_every_node_carries_real_code_evidence(self):
        result = self.scan(FIXTURE)
        self.assertTrue(result["nodes"])
        for node in result["nodes"]:
            evidence = node["evidence"][0]
            self.assertEqual("code", evidence["kind"])
            self.assertTrue((FIXTURE / evidence["file"]).is_file())
            self.assertGreaterEqual(evidence["line"], 1)

    def test_api_node_preserves_http_path_as_technical_label(self):
        result = self.scan(FIXTURE)
        api = [n for n in result["nodes"] if n["kind"] == "api" and n["label"] == "LoginController.login"]
        self.assertTrue(api, "LoginController.login node not found")
        self.assertEqual("POST /api/auth/login", api[0]["technical_label"])

    def test_edges_connect_api_to_service_to_repository(self):
        result = self.scan(FIXTURE)
        relations = {(e["source"].split("--")[-1], e["target"].split("--")[-1]) for e in result["edges"]}
        self.assertIn(("login", "LoginService"), relations)
        self.assertIn(("LoginService", "LoginMapper"), relations)

    def test_scan_is_deterministic(self):
        self.assertEqual(self.scan(FIXTURE), self.scan(FIXTURE))

    def test_files_index_maps_path_to_node_ids(self):
        result = self.scan(FIXTURE)
        key = "src/main/java/com/sqi/auth/LoginService.java"
        self.assertIn(key, result["files"])
        self.assertTrue(all(nid in {n["id"] for n in result["nodes"]} for nid in result["files"][key]))

    def test_changed_files_limits_scan_scope(self):
        result = self.scan(FIXTURE, changed_files=["src/main/java/com/sqi/auth/LoginService.java"])
        self.assertEqual({"src/main/java/com/sqi/auth/LoginService.java"}, set(result["files"]))

    def test_excluded_directories_are_not_scanned(self):
        result = self.scan(FIXTURE)
        for node in result["nodes"]:
            evidence_file = node["evidence"][0]["file"]
            self.assertFalse(evidence_file.startswith("build/"), f"build/ directory should be excluded but found {evidence_file}")

    def test_field_injection_creates_edges(self):
        result = self.scan(FIXTURE)
        relations = {(e["source"].split("--")[-1], e["target"].split("--")[-1]) for e in result["edges"]}
        self.assertIn(("me", "LoginService"), relations, "Field-injected @Autowired should produce edge")

    def test_class_level_request_mapping_prefixes_path(self):
        result = self.scan(FIXTURE)
        api_paths = {node["technical_label"] for node in result["nodes"] if node["kind"] == "api"}
        self.assertIn("GET /api/profile/me", api_paths, "Class-level @RequestMapping should prefix method path")

    def test_method_level_request_mapping_no_double(self):
        result = self.scan(FIXTURE)
        api_paths = {node["technical_label"] for node in result["nodes"] if node["kind"] == "api"}
        self.assertIn("ANY /legacy/ping", api_paths, "Method-level @RequestMapping should not double the path")
        self.assertNotIn("ANY /legacy/ping/legacy/ping", api_paths, "Path must not double")

    def test_sibling_methods_not_contaminated(self):
        result = self.scan(FIXTURE)
        legacy_nodes = [n for n in result["nodes"] if n["kind"] == "api" and "legacy" in n["evidence"][0]["file"].lower()]
        api_paths = {node["technical_label"] for node in legacy_nodes}
        self.assertIn("GET /a", api_paths, "@GetMapping(/a) should produce GET /a")
        self.assertIn("ANY /b", api_paths, "@RequestMapping(/b) should produce ANY /b")
        self.assertNotIn("GET /b/a", api_paths, "Sibling paths must not be contaminated")
        self.assertNotIn("ANY /b/b", api_paths, "Sibling paths must not be contaminated")

    def test_empty_method_path_uses_class_prefix_only(self):
        result = self.scan(FIXTURE)
        api_paths = {node["technical_label"] for node in result["nodes"] if node["kind"] == "api"}
        self.assertIn("GET /api/profile", api_paths, "Empty method path should use class prefix alone")
        self.assertNotIn("GET /api/profile/", api_paths, "Must not have trailing slash")

    def test_comment_containing_class_does_not_break_scoping(self):
        result = self.scan(FIXTURE)
        doc_nodes = [n for n in result["nodes"] if n["kind"] == "api" and "DocController" in n["label"]]
        api_paths = {node["technical_label"] for node in doc_nodes}
        self.assertIn("GET /api/profile/me", api_paths, "Javadoc 'class' should not break class-level annotation scoping")

    def test_commented_out_annotation_produces_no_node(self):
        result = self.scan(FIXTURE)
        all_labels = {node["technical_label"] for node in result["nodes"] if node["kind"] == "api"}
        self.assertNotIn("ANY /ghost", all_labels, "Commented-out @GetMapping should not produce a node")
        self.assertFalse(any("/ghost" in label for label in all_labels), "No node should reference /ghost")

    def test_string_literal_with_double_slash_not_mangled(self):
        result = self.scan(FIXTURE)
        doc_nodes = [n for n in result["nodes"] if n["kind"] == "api" and "DocController" in n["label"]]
        api_paths = {node["technical_label"] for node in doc_nodes}
        self.assertIn("GET /api/profile/proxy", api_paths, "@GetMapping(/proxy) should work despite string containing //")


if __name__ == "__main__":
    unittest.main()
