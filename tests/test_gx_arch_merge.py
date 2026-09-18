import importlib.util
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "merge_map.py"


def _module():
    spec = importlib.util.spec_from_file_location("gx_merge_map", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _node(node_id, kind="service"):
    return {
        "id": node_id,
        "kind": kind,
        "label": node_id,
        "status": "unknown",
        "evidence": [{"kind": "code", "file": "a.java", "line": 1}],
    }


def _edge(source, target):
    return {"id": f"{source}->{target}", "source": source, "target": target, "relation": "calls"}


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_unchanged_nodes_are_preserved(self):
        previous = {"nodes": [_node("n1"), _node("n2")], "edges": [_edge("n1", "n2")]}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}, "b.java": {"fingerprint": "y", "nodes": ["n2"]}}}
        candidate = {"nodes": [_node("n1")], "edges": [], "files": {"a.java": ["n1"]}}
        merged, _ = self.m.merge(previous, candidate, manifest, [])
        self.assertEqual(["n1", "n2"], [n["id"] for n in merged["nodes"]])

    def test_changed_file_nodes_are_replaced_not_duplicated(self):
        previous = {"nodes": [_node("n1")], "edges": []}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}}}
        candidate = {"nodes": [_node("n1b")], "edges": [], "files": {"a.java": ["n1b"]}}
        merged, new_manifest = self.m.merge(previous, candidate, manifest, [])
        self.assertEqual(["n1b"], [n["id"] for n in merged["nodes"]])
        self.assertEqual(["n1b"], new_manifest["files"]["a.java"]["nodes"])

    def test_removed_file_drops_its_nodes(self):
        previous = {"nodes": [_node("n1"), _node("n2")], "edges": []}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}, "b.java": {"fingerprint": "y", "nodes": ["n2"]}}}
        merged, new_manifest = self.m.merge(previous, {"nodes": [], "edges": [], "files": {}}, manifest, ["b.java"])
        self.assertEqual(["n1"], [n["id"] for n in merged["nodes"]])
        self.assertNotIn("b.java", new_manifest["files"])

    def test_dangling_edges_are_removed_with_their_node(self):
        previous = {"nodes": [_node("n1"), _node("n2")], "edges": [_edge("n1", "n2")]}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}, "b.java": {"fingerprint": "y", "nodes": ["n2"]}}}
        merged, _ = self.m.merge(previous, {"nodes": [], "edges": [], "files": {}}, manifest, ["b.java"])
        self.assertEqual([], merged["edges"])

    def test_merge_output_is_sorted_and_deterministic(self):
        previous = {"nodes": [_node("n2"), _node("n1")], "edges": []}
        manifest = {"files": {}}
        merged, _ = self.m.merge(previous, {"nodes": [], "edges": [], "files": {}}, manifest, [])
        self.assertEqual(["n1", "n2"], [n["id"] for n in merged["nodes"]])

    def test_merge_records_new_fingerprint_and_stops_reporting_changed(self):
        # Ruling 1: merge() must record the NEW fingerprint (not the stale one),
        # otherwise changed_paths() would report the same file as changed forever.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "a.java"
            path.write_text("class A {}", encoding="utf-8")
            new_fp = self.m.fingerprint(path, "none")

            previous = {"nodes": [], "edges": []}
            manifest = {"files": {"a.java": {"fingerprint": "stale", "nodes": []}}}
            candidate = {"nodes": [_node("n1")], "edges": [], "files": {"a.java": ["n1"]}}

            merged, new_manifest = self.m.merge(
                previous, candidate, manifest, [], fingerprints={"a.java": new_fp}
            )

            self.assertEqual(new_fp, new_manifest["files"]["a.java"]["fingerprint"])

            changed, _removed = self.m.changed_paths(root, new_manifest, "none")
            self.assertNotIn("a.java", changed)

    def test_shared_node_survives_when_only_one_claiming_file_is_touched(self):
        # Ruling 2: gx-table--TB_BOARD is claimed by both BoardMapper.xml and
        # UserMapper.xml. Deleting UserMapper.xml alone must not drop the table
        # node (or the edge into it) while BoardMapper.xml still claims it.
        previous = {
            "nodes": [_node("gx-table--TB_BOARD", kind="table"), _node("board-dao")],
            "edges": [_edge("board-dao", "gx-table--TB_BOARD")],
        }
        manifest = {
            "files": {
                "BoardMapper.xml": {"fingerprint": "x", "nodes": ["gx-table--TB_BOARD"]},
                "UserMapper.xml": {"fingerprint": "y", "nodes": ["gx-table--TB_BOARD"]},
                "BoardDAO.java": {"fingerprint": "z", "nodes": ["board-dao"]},
            }
        }
        merged, new_manifest = self.m.merge(
            previous, {"nodes": [], "edges": [], "files": {}}, manifest, ["UserMapper.xml"]
        )
        node_ids = [n["id"] for n in merged["nodes"]]
        edge_ids = [e["id"] for e in merged["edges"]]
        self.assertIn("gx-table--TB_BOARD", node_ids)
        self.assertIn("board-dao->gx-table--TB_BOARD", edge_ids)
        self.assertNotIn("UserMapper.xml", new_manifest["files"])
        self.assertIn("BoardMapper.xml", new_manifest["files"])


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_non_git_fingerprint_changes_with_content(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_text("one", encoding="utf-8")
            first = self.m.fingerprint(path, "none")
            path.write_text("one-two-three", encoding="utf-8")
            self.assertNotEqual(first, self.m.fingerprint(path, "none"))

    def test_changed_paths_reports_new_and_removed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kept.java").write_text("class A {}", encoding="utf-8")
            manifest = {"files": {"gone.java": {"fingerprint": "stale", "nodes": []}}}
            changed, removed = self.m.changed_paths(root, manifest, "none")
            self.assertIn("kept.java", changed)
            self.assertEqual(["gone.java"], removed)

    def test_changed_paths_ignores_excluded_dirs(self):
        # Ruling 3: files under EXCLUDED_DIRS (e.g. build output) must not be
        # reported as changed, even though they match SCAN_SUFFIXES.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            excluded = root / "target" / "classes"
            excluded.mkdir(parents=True)
            (excluded / "Generated.java").write_text("class Generated {}", encoding="utf-8")
            manifest = {"files": {}}
            changed, removed = self.m.changed_paths(root, manifest, "none")
            self.assertEqual([], changed)
            self.assertEqual([], removed)

    def test_git_absent_falls_back_to_mtime_fingerprint(self):
        # fingerprint() must not crash when the git executable itself is
        # missing (FileNotFoundError from subprocess.run) — it should fall
        # through to the stat-based fingerprint, same as when git fails.
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.java"
            path.write_text("one", encoding="utf-8")
            with mock.patch.object(self.m.subprocess, "run", side_effect=FileNotFoundError):
                first = self.m.fingerprint(path, "git")
            self.assertTrue(first)

            path.write_text("one-two-three", encoding="utf-8")
            with mock.patch.object(self.m.subprocess, "run", side_effect=FileNotFoundError):
                second = self.m.fingerprint(path, "git")
            self.assertNotEqual(first, second)

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_git_available_returns_blob_sha(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.java"
            path.write_text("class A {}", encoding="utf-8")
            result = self.m.fingerprint(path, "git")
            self.assertRegex(result, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
