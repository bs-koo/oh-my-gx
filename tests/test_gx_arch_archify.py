import importlib.util
import json
import os
import shutil
import stat
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "render_archify.py"
TO_ARCHIFY = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "to_archify.py"

REQUIRED_TOP_LEVEL = {"schema_version", "diagram_type", "meta", "components"}
NODE_KEY = "components"
EDGE_KEY = "connections"

TEST_REPOSITORY = {
    "url": "https://github.com/example/repo.git",
    "revision": "a" * 40,
    "link_mode": "local-only",
}

KIND_TO_TYPE_AND_COL = {
    "screen": ("frontend", 0),
    "api": ("backend", 1),
    "service": ("backend", 2),
    "repository": ("backend", 3),
    "table": ("database", 4),
}


def _single_node_ir(kind: str) -> dict:
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [{"id": "n", "kind": kind, "label": "라벨", "evidence": []}],
        "edges": [],
    }


LINEAR_CHAIN_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "체인",
    "nodes": [
        {"id": "c-screen", "kind": "screen", "label": "화면", "evidence": []},
        {"id": "c-api", "kind": "api", "label": "API", "evidence": []},
        {"id": "c-service", "kind": "service", "label": "서비스", "evidence": []},
        {"id": "c-repo", "kind": "repository", "label": "저장소", "evidence": []},
        {"id": "c-table", "kind": "table", "label": "테이블", "evidence": []},
    ],
    "edges": [
        {"id": "e1", "source": "c-screen", "target": "c-api", "relation": "requests"},
        {"id": "e2", "source": "c-api", "target": "c-service", "relation": "calls"},
        {"id": "e3", "source": "c-service", "target": "c-repo", "relation": "calls"},
        {"id": "e4", "source": "c-repo", "target": "c-table", "relation": "reads"},
    ],
}

# id 알파벳 순서와 실제 연결이 어긋나도록 일부러 엇갈리게 짠 두 갈래 체인이다:
# s-alpha -> a-zulu, s-zulu -> a-alpha. id로만 행을 매기면(과거 버그) 잘못 짝지어진다 —
# 연결의 source 행을 따라가야만 s-alpha/a-zulu가, s-zulu/a-alpha가 각각 같은 행에 놓인다.
CROSSED_CHAINS_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "교차 체인",
    "nodes": [
        {"id": "s-alpha", "kind": "screen", "label": "화면A", "evidence": []},
        {"id": "s-zulu", "kind": "screen", "label": "화면Z", "evidence": []},
        {"id": "a-alpha", "kind": "api", "label": "APIA", "evidence": []},
        {"id": "a-zulu", "kind": "api", "label": "APIZ", "evidence": []},
    ],
    "edges": [
        {"id": "e-a", "source": "s-alpha", "target": "a-zulu", "relation": "requests"},
        {"id": "e-b", "source": "s-zulu", "target": "a-alpha", "relation": "requests"},
    ],
}

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


def _converter():
    spec = importlib.util.spec_from_file_location("gx_to_archify", TO_ARCHIFY)
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


def _init_git_repo(root: Path, origin: str | None = None) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    if origin is not None:
        subprocess.run(["git", "remote", "add", "origin", origin], cwd=root, check=True)


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

            # root is a plain tmp dir (not a git checkout), so no repository evidence is
            # available and the payload carries no --repo-root flag (see to_archify.py).
            archify_payload = out / "service.archify.json"
            calls = [json.loads(line) for line in (root / "argv.log").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["validate", "architecture", str(archify_payload), "--json"], calls[0])
            self.assertEqual(
                ["deliver", "architecture", str(archify_payload), str(out / "service.html"), "--json"], calls[1]
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

    def test_git_absent_yields_no_repository_evidence(self):
        # subprocess.run 자체가 없는 환경(git 미설치)을 흉내낸다 — merge_map.py의
        # fingerprint() 테스트와 같은 방식.
        with TemporaryDirectory() as tmp:
            with mock.patch.object(self.m.subprocess, "run", side_effect=FileNotFoundError):
                self.assertIsNone(self.m._git_repository_evidence(Path(tmp)))

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_git_repo_without_origin_yields_no_repository_evidence(self):
        # origin이 없는 리포지토리(갓 init했거나 SVN에서 옮겨온 경우)도 sources 생략으로
        # 안전하게 떨어져야 한다 — 실측: origin 조회가 실패하면 repository=None.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            self.assertIsNone(self.m._git_repository_evidence(root))

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_git_repo_with_origin_yields_repository_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root, origin="https://github.com/example/repo.git")
            evidence = self.m._git_repository_evidence(root)
            self.assertEqual("https://github.com/example/repo.git", evidence["url"])
            self.assertRegex(evidence["revision"], r"^[0-9a-f]{40}$")
            self.assertEqual("local-only", evidence["link_mode"])


class ToArchifyTests(unittest.TestCase):
    def setUp(self):
        self.to_archify = _converter().to_archify

    def test_output_carries_required_top_level_keys(self):
        # REQUIRED_TOP_LEVEL은 docs/reports/2026-09-18-archify-ir-schema.md에 기록한 실제 키 집합이다.
        from_schema = set(REQUIRED_TOP_LEVEL)
        self.assertTrue(from_schema.issubset(set(self.to_archify(VALID_IR, "architecture"))))

    def test_node_ids_are_preserved_verbatim(self):
        out = self.to_archify(VALID_IR, "architecture")
        self.assertEqual(["n1"], [n["id"] for n in out[NODE_KEY]])

    def test_korean_labels_survive_conversion(self):
        out = self.to_archify(VALID_IR, "architecture")
        self.assertEqual("로그인", out[NODE_KEY][0]["label"])

    def test_gx_evidence_maps_to_archify_sources(self):
        out = self.to_archify(VALID_IR, "architecture", repository=TEST_REPOSITORY)
        component = out[NODE_KEY][0]
        self.assertEqual([{"path": "a.java", "line": 1}], component["sources"])
        self.assertEqual(TEST_REPOSITORY, out["meta"]["repository"])

    def test_missing_repository_omits_sources_and_meta_repository(self):
        # sources를 실으면 Archify가 meta.repository{url, revision}과 --repo-root를 요구하고
        # 실제 리포지토리로 경로 존재를 검증한다 (실측 보고 §3.3). repository가 없으면 둘 다 비운다.
        out = self.to_archify(VALID_IR, "architecture")
        self.assertNotIn("sources", out[NODE_KEY][0])
        self.assertNotIn("repository", out["meta"])

    def test_gx_only_fields_are_not_leaked(self):
        # 최상위가 additionalProperties: false이므로 GX 전용 필드는 반드시 빠져야 한다.
        blob = json.dumps(self.to_archify(VALID_IR, "architecture"), ensure_ascii=False)
        for gx_only in ("evidence", "technical_label", "status", '"view"', "ko-KR"):
            self.assertNotIn(gx_only, blob)

    def test_inferred_evidence_is_dropped(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [{"kind": "inferred"}]
        out = self.to_archify(ir, "architecture", repository=TEST_REPOSITORY)
        self.assertNotIn("sources", out[NODE_KEY][0])

    def test_sources_are_capped_at_three(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [
            {"kind": "code", "file": f"f{n}.java", "line": n} for n in range(1, 6)
        ]
        out = self.to_archify(ir, "architecture", repository=TEST_REPOSITORY)
        self.assertEqual(3, len(out[NODE_KEY][0]["sources"]))

    def test_conversion_is_deterministic(self):
        self.assertEqual(self.to_archify(VALID_IR, "architecture"), self.to_archify(VALID_IR, "architecture"))

    def test_kind_maps_to_reported_type_and_col(self):
        # 실측 보고 §3.2의 kind→type/col 표를 하드코딩해 대조한다.
        for kind, (expected_type, expected_col) in KIND_TO_TYPE_AND_COL.items():
            component = self.to_archify(_single_node_ir(kind), "architecture")[NODE_KEY][0]
            self.assertEqual(expected_type, component["type"], kind)
            self.assertEqual(expected_col, component["col"], kind)

    def test_linear_chain_bands_in_one_row(self):
        out = self.to_archify(LINEAR_CHAIN_IR, "architecture")
        by_id = {c["id"]: c for c in out[NODE_KEY]}
        chain = ["c-screen", "c-api", "c-service", "c-repo", "c-table"]
        self.assertEqual({0}, {by_id[node_id]["row"] for node_id in chain})
        self.assertEqual([0, 1, 2, 3, 4], [by_id[node_id]["col"] for node_id in chain])

    def test_row_follows_connection_source_not_id_order(self):
        # id 정렬만으로 행을 매기면 s-alpha/a-alpha, s-zulu/a-zulu가 잘못 짝지어진다.
        # 실제 연결은 s-alpha->a-zulu, s-zulu->a-alpha이므로 그 짝이 같은 행에 있어야 한다.
        out = self.to_archify(CROSSED_CHAINS_IR, "architecture")
        by_id = {c["id"]: c for c in out[NODE_KEY]}
        self.assertEqual(by_id["s-alpha"]["row"], by_id["a-zulu"]["row"])
        self.assertEqual(by_id["s-zulu"]["row"], by_id["a-alpha"]["row"])
        self.assertNotEqual(by_id["s-alpha"]["row"], by_id["s-zulu"]["row"])

    def test_row_and_col_assignment_is_deterministic(self):
        first = self.to_archify(CROSSED_CHAINS_IR, "architecture")
        second = self.to_archify(CROSSED_CHAINS_IR, "architecture")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
