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

    def test_edges_crossing_domains_are_dropped_and_reported(self):
        # 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않는다.
        # 조용히 버리지 않고 해당 도메인 IR의 missing_inputs에 남긴다.
        parts = split_by_domain(ir_cross_domain())
        self.assertTrue(any("cross-domain-edge" in p.get("missing_inputs", []) for p in parts.values()))

    def test_split_is_deterministic(self):
        self.assertEqual(split_by_domain(ir_two_domains()), split_by_domain(ir_two_domains()))


if __name__ == "__main__":
    unittest.main()
