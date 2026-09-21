import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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

    def test_class_level_annotation_adjacent_to_first_method(self):
        result = self.scan(FIXTURE)
        tight_nodes = [n for n in result["nodes"] if n["kind"] == "api" and "TightController" in n["label"]]
        self.assertEqual(1, len(tight_nodes), "Only one API node should exist for TightController.first")
        self.assertEqual("GET /api/tight/first", tight_nodes[0]["technical_label"])
        all_labels = {node["technical_label"] for node in result["nodes"] if node["kind"] == "api"}
        self.assertFalse(any("/api/tight/api/tight" in label for label in all_labels), "No duplicate class-level annotation in method path")

    def test_node_ids_are_unique(self):
        result = self.scan(FIXTURE)
        all_ids = [n["id"] for n in result["nodes"]]
        unique_ids = set(all_ids)
        self.assertEqual(len(unique_ids), len(all_ids), f"Duplicate node IDs found: {len(all_ids) - len(unique_ids)} duplicates")


JSP_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-jsp"


class JspLegacyScanTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_jsp_file_becomes_screen_node(self):
        result = self.scan(JSP_FIXTURE)
        screens = [n for n in result["nodes"] if n["kind"] == "screen"]
        self.assertEqual(1, len(screens))
        self.assertEqual("board/list.jsp", screens[0]["evidence"][0]["file"])

    def test_servlet_dopost_becomes_api_node(self):
        result = self.scan(JSP_FIXTURE)
        apis = [n for n in result["nodes"] if n["kind"] == "api"]
        self.assertEqual(["doPost"], [n["id"].split("--")[-1] for n in apis])

    def test_screen_form_action_links_to_api(self):
        result = self.scan(JSP_FIXTURE)
        self.assertTrue(any(e["relation"] == "requests" for e in result["edges"]))

    def test_mapper_xml_yields_table_nodes_with_statement_evidence(self):
        result = self.scan(JSP_FIXTURE)
        tables = [n for n in result["nodes"] if n["kind"] == "table"]
        self.assertEqual(["TB_BOARD"], sorted(n["technical_label"] for n in tables))
        self.assertEqual("code", tables[0]["evidence"][0]["kind"])

    def test_select_is_reads_and_insert_is_writes(self):
        result = self.scan(JSP_FIXTURE)
        relations = {e["relation"] for e in result["edges"] if e["target"].startswith("gx-table-")}
        self.assertEqual({"reads", "writes"}, relations)

    def test_sql_body_is_not_copied_into_ir(self):
        result = self.scan(JSP_FIXTURE)
        blob = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("SELECT BOARD_ID", blob)

    def test_unannotated_serviceimpl_class_classifies_as_service(self):
        result = self.scan(JSP_FIXTURE)
        services = [n for n in result["nodes"] if n["kind"] == "service"]
        self.assertTrue(
            any(n["label"] == "BoardServiceImpl" for n in services),
            "Annotation-free *ServiceImpl class should classify as a service node",
        )


COLLISION_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-collision"


class PackageCollisionEdgeTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_same_simple_name_in_different_packages_wires_correctly(self):
        result = self.scan(COLLISION_FIXTURE)

        def find_id(kind, file_suffix):
            matches = [
                n["id"]
                for n in result["nodes"]
                if n["kind"] == kind and n["evidence"][0]["file"].endswith(file_suffix)
            ]
            self.assertEqual(1, len(matches), f"expected exactly one {kind} node ending in {file_suffix}")
            return matches[0]

        auth_login = find_id("api", "auth/AuthController.java")
        admin_login = find_id("api", "admin/AdminController.java")
        auth_service = find_id("service", "auth/LoginService.java")
        admin_service = find_id("service", "admin/LoginService.java")

        edge_pairs = {(e["source"], e["target"]) for e in result["edges"]}
        self.assertIn((auth_login, auth_service), edge_pairs)
        self.assertIn((admin_login, admin_service), edge_pairs)
        self.assertNotIn((auth_login, admin_service), edge_pairs)
        self.assertNotIn((admin_login, auth_service), edge_pairs)


SERVICE_IMPL_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-service-impl"


class ServiceInterfaceMergeTests(unittest.TestCase):
    """컨트롤러는 인터페이스를 주입받고 실제 로직은 `{X}Impl`에 있다(eGov·Spring 관례).
    합치지 않으면 인터페이스는 막다른 길, 구현체는 컨트롤러에서 닿지 않는 별개의
    덩어리로 남아 화면 -> API -> 서비스 -> 저장소 -> 테이블 체인이 끊긴다."""

    def setUp(self):
        self.scan = _module().scan

    def test_service_impl_merges_into_its_interface(self):
        result = self.scan(SERVICE_IMPL_FIXTURE)
        labels = {n["label"] for n in result["nodes"] if n["kind"] == "service"}
        self.assertIn("UserService", labels)
        self.assertNotIn("UserServiceImpl", labels)

    def test_merged_service_keeps_the_impl_outgoing_edges(self):
        result = self.scan(SERVICE_IMPL_FIXTURE)
        by_id = {n["id"]: n for n in result["nodes"]}
        edges = {
            (by_id[e["source"]]["label"], e["relation"], by_id[e["target"]]["label"])
            for e in result["edges"]
        }
        # 체인이 끊기지 않는다: Controller -> UserService(합쳐진 인터페이스) -> UserMapper
        self.assertIn(("UserController.login", "calls", "UserService"), edges)
        self.assertIn(("UserService", "calls", "UserMapper"), edges)

    def test_merged_service_keeps_both_files_as_evidence(self):
        result = self.scan(SERVICE_IMPL_FIXTURE)
        node = next(n for n in result["nodes"] if n["kind"] == "service" and n["label"] == "UserService")
        files = {e["file"] for e in node["evidence"]}
        self.assertTrue(any(f.endswith("UserService.java") for f in files), files)
        self.assertTrue(any(f.endswith("UserServiceImpl.java") for f in files), files)

    def test_impl_without_interface_stays_as_is(self):
        # 짝이 되는 인터페이스가 스캔되지 않은 *Impl은 지어내지 않고 그대로 둔다
        result = self.scan(SERVICE_IMPL_FIXTURE)
        labels = {n["label"] for n in result["nodes"] if n["kind"] == "service"}
        self.assertIn("OrphanServiceImpl", labels)

    def test_merge_is_deterministic(self):
        self.assertEqual(self.scan(SERVICE_IMPL_FIXTURE), self.scan(SERVICE_IMPL_FIXTURE))

    def test_files_index_points_impl_file_at_the_merged_interface_id(self):
        # UserServiceImpl.java는 병합 전 자신의 노드 id를 files에 기록했다 - 병합 후에도
        # 그 항목이 옛 id를 그대로 가리키면 "이 파일이 어느 노드에 속하는가"가 끊긴다.
        result = self.scan(SERVICE_IMPL_FIXTURE)
        interface_node = next(
            n for n in result["nodes"] if n["kind"] == "service" and n["label"] == "UserService"
        )
        impl_file = next(f for f in result["files"] if f.endswith("UserServiceImpl.java"))
        self.assertEqual([interface_node["id"]], result["files"][impl_file])


class EdgeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_all_edge_endpoints_are_known_nodes(self):
        for fixture in (FIXTURE, JSP_FIXTURE):
            result = self.scan(fixture)
            ids = {node["id"] for node in result["nodes"]}
            for edge in result["edges"]:
                self.assertIn(edge["source"], ids, f"{fixture}: {edge}")
                self.assertIn(edge["target"], ids, f"{fixture}: {edge}")


SHARED_TABLE_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-shared-table"


class SharedTableNodeTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_same_table_across_mappers_is_one_node_with_two_edges(self):
        result = self.scan(SHARED_TABLE_FIXTURE)
        tables = [n for n in result["nodes"] if n["kind"] == "table"]
        self.assertEqual(1, len(tables))
        self.assertEqual("TB_BOARD", tables[0]["technical_label"])

        table_id = tables[0]["id"]
        incoming = [e for e in result["edges"] if e["target"] == table_id]
        self.assertEqual(2, len(incoming))
        sources = {e["source"] for e in incoming}
        self.assertEqual(2, len(sources))


PATH_COLLISION_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-path-collision"


class PathCollisionEdgeTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_ambiguous_path_produces_no_requests_edge(self):
        result = self.scan(PATH_COLLISION_FIXTURE)
        apis = [n for n in result["nodes"] if n["kind"] == "api"]
        self.assertEqual(2, len(apis), "expected both the Spring and Servlet api nodes for /board/list.do")

        requests_edges = [e for e in result["edges"] if e["relation"] == "requests"]
        self.assertEqual(
            0,
            len(requests_edges),
            "a path shared by two unrelated api nodes must not be guessed - the edge should be dropped",
        )


EGOV_MAPPER_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-egov-mapper"
IBATIS_MAPPER_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-ibatis-mapper"
UNRESOLVED_MAPPER_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-unresolved-mapper"


class EgovMapperNamespaceTests(unittest.TestCase):
    """eGovFrame 관례: Board_SQL.xml + BoardDao.java. 파일명 치환(stem.replace("Mapper", "DAO"))으로는
    맞지 않는다 - 매퍼의 namespace 속성이 실제 DAO를 가리킨다."""

    def setUp(self):
        self.scan = _module().scan

    def test_egov_mapper_xml_resolves_via_namespace(self):
        result = self.scan(EGOV_MAPPER_FIXTURE)
        edges = [(e["source"], e["target"], e["relation"]) for e in result["edges"]]
        # BoardDao -> TB_BOARD 의 reads 엣지가 실제로 해소돼야 한다
        self.assertTrue(any(r == "reads" for _, _, r in edges), edges)

    def test_ibatis_sqlmap_xml_resolves_via_namespace(self):
        # 실측(GSEED Gseed_Web_Renew): 매퍼 11개 전부 MyBatis3 <mapper>가 아니라
        # iBATIS 2.0 <sqlMap namespace="BoardDao">(점 없는 짧은 이름) 관례를 쓴다.
        result = self.scan(IBATIS_MAPPER_FIXTURE)
        edges = [(e["source"], e["target"], e["relation"]) for e in result["edges"]]
        self.assertTrue(any(r == "reads" for _, _, r in edges), edges)


class UnresolvedEdgeReportingTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_unresolved_edges_are_reported_not_silently_dropped(self):
        # 대상 DAO(MissingDao)가 존재하지 않아 해소되지 않는 엣지 - 버리되 그 사실을 보고한다.
        result = self.scan(UNRESOLVED_MAPPER_FIXTURE)
        self.assertIn("unresolved_edges", result)
        self.assertGreater(len(result["unresolved_edges"]), 0)

    def test_resolved_scan_reports_no_unresolved_edges(self):
        result = self.scan(FIXTURE)
        self.assertEqual(result["unresolved_edges"], [])


class DaoStemCollisionTests(unittest.TestCase):
    """dao_by_stem은 같은 단순명(stem) DAO가 여러 개면 경로 사전순 마지막이 조용히
    이기는 무방비 dict 덮어쓰기였다(2026-09-18 최종 리뷰 M5) - namespace의 완전한
    클래스명으로 가르고, 그래도 못 가르면 엣지를 버리고 unresolved_edges에 남긴다."""

    def setUp(self):
        self.scan = _module().scan

    def _write_dao(self, root: Path, package: str) -> None:
        path = root.joinpath(*package.split("."), "BoardDAO.java")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"package {package};\n\npublic class BoardDAO {{\n    public Object selectBoard() {{\n        return null;\n    }}\n}}\n",
            encoding="utf-8",
        )

    def test_namespace_disambiguates_dao_stem_collision(self):
        # 리뷰어 재현: com/sqi/a/BoardDAO.java·com/sqi/b/BoardDAO.java가 있고 매퍼
        # namespace가 com.sqi.a.BoardDAO를 가리키면 반드시 a로 배선돼야 한다.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_dao(root, "com.sqi.a")
            self._write_dao(root, "com.sqi.b")
            mapper = root / "mappers" / "BoardMapper.xml"
            mapper.parent.mkdir(parents=True, exist_ok=True)
            mapper.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<mapper namespace="com.sqi.a.BoardDAO">\n'
                '  <select id="selectBoard" resultType="map">\n'
                "    SELECT BOARD_ID, TITLE FROM TB_BOARD WHERE USE_YN = 'Y'\n"
                "  </select>\n"
                "</mapper>\n",
                encoding="utf-8",
            )
            result = self.scan(root)

        reads_edges = [e for e in result["edges"] if e["relation"] == "reads"]
        self.assertEqual(1, len(reads_edges), result)
        self.assertIn("com-sqi-a-BoardDAO", reads_edges[0]["source"])
        self.assertNotIn("com-sqi-b-BoardDAO", reads_edges[0]["source"])
        self.assertEqual([], result["unresolved_edges"])

    def test_unresolvable_dao_stem_collision_is_reported_not_wrongly_wired(self):
        # namespace가 없고 stem만으로는 둘 중 하나를 고를 수 없으면 - 지어내지 않고
        # 버린 뒤 unresolved_edges에 남긴다. 잘못 배선하는 것보다 안전하다.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_dao(root, "com.sqi.a")
            self._write_dao(root, "com.sqi.b")
            mapper = root / "mappers" / "BoardMapper.xml"
            mapper.parent.mkdir(parents=True, exist_ok=True)
            mapper.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                "<mapper>\n"
                '  <select id="selectBoard" resultType="map">\n'
                "    SELECT BOARD_ID, TITLE FROM TB_BOARD WHERE USE_YN = 'Y'\n"
                "  </select>\n"
                "</mapper>\n",
                encoding="utf-8",
            )
            result = self.scan(root)

        self.assertEqual([], [e for e in result["edges"] if e["relation"] == "reads"])
        self.assertEqual(1, len(result["unresolved_edges"]), result)
        self.assertEqual("reads", result["unresolved_edges"][0]["relation"])


class LegacyEncodingTests(unittest.TestCase):
    """오래된 한국어 JSP·Java 코드베이스는 CP949로 저장된 파일이 섞여 있는 경우가 흔하다
    (실측: GSEED Gseed_Web_Renew, JSP 81개 중 2개가 CP949). utf-8로만 읽으면
    UnicodeDecodeError가 스캔 전체를 중단시킨다 - 파일 하나 때문에 나머지 수백 개의
    결과까지 잃는 것은 정직하지 않다."""

    def setUp(self):
        self.scan = _module().scan

    def test_cp949_encoded_jsp_still_yields_a_screen_node(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "legacy.jsp").write_bytes("<html>한글 화면</html>".encode("cp949"))
            result = self.scan(root)
        screens = [n for n in result["nodes"] if n["kind"] == "screen"]
        self.assertEqual(1, len(screens))
        self.assertEqual([], result["skipped"])

    def test_file_undecodable_in_either_encoding_is_skipped_not_raised(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.jsp").write_bytes(b"\xff\xfe\x00\x01")
            result = self.scan(root)  # must not raise
        self.assertEqual([], result["nodes"])
        self.assertEqual(["broken.jsp"], result["skipped"])


if __name__ == "__main__":
    unittest.main()
