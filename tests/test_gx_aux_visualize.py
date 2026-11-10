"""명시 backend와 출력 충돌의 실제 파일 회귀. 외부 설치는 호출하지 않는다."""

from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

from test_gx_arch_build_map import _load, _project


class VisualizeBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gx 시각화 경계 ")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.root = self.directory / "project"
        self.output = self.directory / "map"
        _project(self.root)
        self.builder = _load()
        self.addCleanup(mock.patch.stopall)
        self.discovery = mock.patch.object(self.builder.backend_detector, "ensure_archify",
                                           side_effect=AssertionError("명시 backend에서 Archify 호출")).start()
        self.archify = mock.patch.object(self.builder.archify_renderer, "render_archify",
                                         side_effect=AssertionError("명시 backend에서 Archify 렌더")).start()
        self.assets = mock.patch.object(self.builder.fallback_renderer, "ensure_mermaid_asset",
                                        return_value={"available": False, "attempts": []}).start()

    def build(self, **kwargs):
        return self.builder.build_map(self.root, self.output, **kwargs)

    def test_static_skips_archify_and_mermaid_downloads(self):
        report = self.build(backend="static")
        self.assertEqual(report["validation_status"], "fallback")
        self.assertEqual({item["backend"] for item in report["domains"]}, {"static"})
        self.discovery.assert_not_called()
        self.archify.assert_not_called()
        self.assets.assert_not_called()
        self.assertTrue(Path(report["index_path"]).is_file())

    def test_mermaid_skips_archify_and_fetches_shared_asset_once(self):
        report = self.build(backend="mermaid")
        self.assertEqual({item["backend"] for item in report["domains"]}, {"mermaid"})
        self.discovery.assert_not_called()
        self.archify.assert_not_called()
        self.assets.assert_called_once()
        self.assertEqual(report["validation_status"], "fallback")

    def test_cli_forwards_explicit_backend(self):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["build_map.py", str(self.root), "--map-dir", str(self.output),
                                             "--backend", "static"]), contextlib.redirect_stdout(output):
            result = self.builder.main()
        self.assertEqual(result, 0)
        report = json.loads(output.getvalue())
        self.assertEqual({item["backend"] for item in report["domains"]}, {"static"})

    def test_invalid_backend_fails_before_output_writes(self):
        with self.assertRaises(ValueError):
            self.build(backend="invalid")
        self.assertFalse(self.output.exists())

    def test_atomic_json_writers_do_not_share_pending_file(self):
        target = self.output / "run-manifest.json"
        barrier = threading.Barrier(2)
        pending_paths = []
        original = Path.write_text

        def synchronize(path, *args, **kwargs):
            pending_paths.append(str(path))
            result = original(path, *args, **kwargs)
            barrier.wait(timeout=5)
            return result

        with mock.patch.object(Path, "write_text", synchronize), ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.builder._write_json, target, {"run": value}) for value in ("A", "B")]
            for future in futures:
                future.result(timeout=10)
        self.assertEqual(len(set(pending_paths)), 2, "동시 쓰기는 서로 다른 임시 경로를 사용해야 함")
        self.assertIn(json.loads(target.read_text(encoding="utf-8"))["run"], {"A", "B"})
        self.assertEqual(list(self.output.glob("*.tmp")), [])

    def test_overlapping_build_does_not_replace_active_manifest(self):
        entered, release = threading.Event(), threading.Event()
        original = self.builder.scanner.scan

        def hold(root):
            entered.set()
            if not release.wait(timeout=60):
                raise RuntimeError("fixture release timeout")
            return original(root)

        with mock.patch.object(self.builder.scanner, "scan", hold), ThreadPoolExecutor(1) as pool:
            first = pool.submit(self.build, backend="static")
            try:
                self.assertTrue(entered.wait(timeout=30), "첫 실행이 스캔에 진입해야 함")
                before = (self.output / "run-manifest.json").read_bytes()
                second = self.build(backend="static")
                self.assertEqual(second["validation_status"], "failed")
                self.assertTrue(second["busy"])
                self.assertIsNone(second["index_path"])
                self.assertEqual((self.output / "run-manifest.json").read_bytes(), before)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=60)["validation_status"], "fallback")
        self.assertFalse((self.output / ".gx-map.lock").exists())

    def test_failed_run_releases_its_lock(self):
        with mock.patch.object(self.builder.scanner, "scan", side_effect=RuntimeError("fixture scan failure")):
            self.assertEqual(self.build(backend="static")["validation_status"], "failed")
        self.assertFalse((self.output / ".gx-map.lock").exists())
        self.assertEqual(self.build(backend="static")["validation_status"], "fallback")

    def test_foreign_lock_is_preserved_without_touching_outputs(self):
        self.output.mkdir()
        lock = self.output / ".gx-map.lock"
        lock.write_text("foreign lock", encoding="utf-8")
        manifest = self.output / "run-manifest.json"
        manifest.write_text('{"old":true}', encoding="utf-8")
        report = self.build(backend="static")
        self.assertTrue(report["busy"])
        self.assertEqual(report.get("requested_backend"), "static")
        self.assertTrue({"changes", "skipped", "mermaid_asset", "map_domains",
                         "cross_domain_edge_count", "unresolved_edge_count"}.issubset(report))
        self.assertEqual(lock.read_text(encoding="utf-8"), "foreign lock")
        self.assertEqual(manifest.read_text(encoding="utf-8"), '{"old":true}')

    def test_serialization_failure_leaves_no_temporary_file(self):
        with self.assertRaises(TypeError):
            self.builder._write_json(self.output / "bad.json", {"bad": object()})
        self.assertEqual(list(self.output.glob("*.tmp")), [])
        self.assertFalse((self.output / "bad.json").exists())

    def test_transient_windows_replacement_is_retried(self):
        target = self.output / "result.json"
        original = Path.replace
        calls = []

        def retry_once(path, destination):
            calls.append(path)
            if len(calls) == 1:
                error = PermissionError("fixture sharing violation")
                error.winerror = 32
                raise error
            return original(path, destination)

        with mock.patch.object(Path, "replace", retry_once):
            self.builder._write_json(target, {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"ok": True})


if __name__ == "__main__":
    unittest.main()
