import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "split_domains.py"

_spec = importlib.util.spec_from_file_location("gx_split_domains", SCRIPT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

domain_of = _module.domain_of
split_by_domain = _module.split_by_domain

LAYER_DIRS = ("controller", "service", "repository", "dao", "mapper", "web", "api")


def _node(node_id: str, file: str, kind: str = "service") -> dict:
    return {
        "id": node_id, "kind": kind, "label": node_id, "status": "unknown",
        "evidence": [{"kind": "code", "file": file, "line": 1}],
    }


def _table_node(node_id: str, label: str) -> dict:
    return {
        "id": node_id, "kind": "table", "label": label, "status": "unknown",
        "evidence": [{"kind": "code", "file": "src/main/resources/mapper/UserMapper.xml", "line": 12}],
    }


def _edge(source: str, target: str, relation: str = "calls") -> dict:
    return {"id": f"{source}->{target}", "source": source, "target": target, "relation": relation}


def ir_two_domains() -> dict:
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [
            _node("n-auth", "src/main/java/com/sqisoft/gx/auth/service/AuthService.java"),
            _node("n-code", "src/main/java/com/sqisoft/gx/code/service/CodeService.java"),
        ],
        "edges": [],
    }


def ir_shared_table() -> dict:
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [
            _node("n-auth", "src/main/java/com/sqisoft/gx/auth/repository/AuthRepository.java", kind="repository"),
            _node("n-code", "src/main/java/com/sqisoft/gx/code/repository/CodeRepository.java", kind="repository"),
            _table_node("gx-table--TB_USER", "TB_USER"),
        ],
        "edges": [
            _edge("n-auth", "gx-table--TB_USER", relation="reads"),
            _edge("n-code", "gx-table--TB_USER", relation="reads"),
        ],
    }


def ir_cross_domain() -> dict:
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [
            _node("n-user", "src/main/java/com/sqisoft/gx/user/service/UserService.java"),
            _node("n-auth", "src/main/java/com/sqisoft/gx/auth/service/AuthService.java"),
        ],
        "edges": [_edge("n-user", "n-auth")],
    }


class DomainOfTests(unittest.TestCase):
    def test_domain_is_segment_before_layer_dir(self):
        # SEF: .../modules/auth/controller/AuthController.java
        self.assertEqual(domain_of("webframework-public/src/main/java/com/sqisoft/sef/modules/auth/controller/AuthController.java"), "auth")
        # GSEED: .../gseed/board/controller/BoardController.java
        self.assertEqual(domain_of("src/main/java/com/sqisoft/gseed/board/controller/BoardController.java"), "board")

    def test_layer_dir_named_api_still_yields_owning_domain(self):
        # `api`는 계층 이름이자 도메인 이름일 수 있다. 계층으로 먼저 소비하지 않는다.
        self.assertEqual(domain_of("src/main/java/com/sqisoft/gseed/api/controller/ApiController.java"), "api")

    def test_unknown_layout_falls_back_to_parent_dir(self):
        self.assertEqual(domain_of("src/main/java/com/example/Foo.java"), "example")

    def test_domain_is_none_for_empty_path(self):
        self.assertIsNone(domain_of(""))


class SplitByDomainTests(unittest.TestCase):
    def test_split_groups_nodes_by_domain(self):
        parts = split_by_domain(ir_two_domains())
        self.assertEqual(sorted(parts), ["auth", "code"])

    def test_table_nodes_join_every_domain_that_references_them(self):
        # 테이블 노드는 파일 근거가 없다. 그 테이블을 읽고 쓰는 도메인 전부에 들어간다.
        parts = split_by_domain(ir_shared_table())
        for d in parts:
            self.assertIn("gx-table--TB_USER", [n["id"] for n in parts[d]["nodes"]])

    def test_shared_table_with_domain_owned_edges_has_no_spurious_cross_domain_marker(self):
        # 테이블 하나를 두 도메인이 함께 참조해도(ir_shared_table: TB_USER를 auth·code가
        # 모두 읽는다), 각 도메인이 그 테이블로 잇는 자기 소유 엣지(auth: n-auth->TB_USER,
        # code: n-code->TB_USER)는 서로에게 cross-domain-edge로 잘못 잡히면 안 된다 -
        # 양쪽 다 자기 도메인 안에서 양 끝을 온전히 담고 있어 실제로 잃은 적이 없다.
        parts = split_by_domain(ir_shared_table())
        for domain, part in parts.items():
            self.assertNotIn("cross-domain-edge", part.get("missing_inputs", []), domain)

    def test_edges_crossing_domains_are_dropped_and_reported(self):
        # 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않는다.
        # 조용히 버리지 않고 해당 도메인 IR의 missing_inputs에 남긴다.
        parts = split_by_domain(ir_cross_domain())
        self.assertTrue(any("cross-domain-edge" in p.get("missing_inputs", []) for p in parts.values()))

    def test_split_is_deterministic(self):
        self.assertEqual(split_by_domain(ir_two_domains()), split_by_domain(ir_two_domains()))

    def test_skipped_files_are_attributed_to_their_domain(self):
        # scan()의 skipped(읽기 실패 파일)를 도메인 분할 후에도 보존한다 - 그대로 두면
        # 나중에 그 도메인 IR만 읽는 사람은 어떤 파일이 인코딩 때문에 빠졌는지 알 수
        # 없다(2026-09-18 최종 리뷰 M6). 무관한 도메인에 전체 목록을 복제하지 않는다.
        ir = ir_two_domains()
        ir["skipped"] = [
            "src/main/java/com/sqisoft/gx/auth/service/BrokenAuth.java",
            "src/main/java/com/sqisoft/gx/code/service/BrokenCode.java",
        ]
        parts = split_by_domain(ir)
        self.assertEqual(parts["auth"]["skipped"], ["src/main/java/com/sqisoft/gx/auth/service/BrokenAuth.java"])
        self.assertEqual(parts["code"]["skipped"], ["src/main/java/com/sqisoft/gx/code/service/BrokenCode.java"])

    def test_unresolved_edges_are_attributed_to_the_source_domain(self):
        # scan()의 unresolved_edges(관계 미해소)도 같은 이유로 보존한다.
        ir = ir_two_domains()
        ir["unresolved_edges"] = [
            {"source": "n-auth", "target": "AuthMapper", "relation": "reads"},
            {"source": "n-code", "target": "CodeMapper", "relation": "writes"},
        ]
        parts = split_by_domain(ir)
        self.assertEqual(parts["auth"]["unresolved_edges"], [{"source": "n-auth", "target": "AuthMapper", "relation": "reads"}])
        self.assertEqual(parts["code"]["unresolved_edges"], [{"source": "n-code", "target": "CodeMapper", "relation": "writes"}])

    def test_unresolved_edge_with_raw_path_source_falls_back_to_domain_of(self):
        # 매퍼 XML -> DAO 해소에 실패한 미해소 엣지의 source는 노드 id가 아니라 원본 XML
        # 상대경로로 남는다(scan_entrypoints.py) - 이 경우도 domain_of()로 도메인을
        # 추정할 수 있다.
        ir = ir_two_domains()
        ir["unresolved_edges"] = [
            {"source": "src/main/resources/auth/mapper/AuthMapper.xml", "target": "gx-table--TB_AUTH", "relation": "reads"},
        ]
        parts = split_by_domain(ir)
        self.assertEqual(parts["auth"]["unresolved_edges"], ir["unresolved_edges"])
        self.assertNotIn("unresolved_edges", parts["code"])

    def test_no_skipped_or_unresolved_edges_omits_the_keys(self):
        # 아무것도 없으면 빈 리스트를 억지로 채우지 않는다 - 키 부재 자체가 "없음"이다.
        parts = split_by_domain(ir_two_domains())
        for part in parts.values():
            self.assertNotIn("skipped", part)
            self.assertNotIn("unresolved_edges", part)


if __name__ == "__main__":
    unittest.main()
