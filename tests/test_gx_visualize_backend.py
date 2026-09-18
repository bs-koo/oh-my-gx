import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "skills" / "gx-visualize" / "scripts"
DETECT_PATH = SCRIPTS / "detect_backend.py"
RENDER_PATH = SCRIPTS / "render_archify.py"
FIXTURE = ROOT / "tests" / "fixtures" / "gx-trace.valid.json"
PROJECT_FIXTURE = ROOT / "tests" / "fixtures" / "gx-visualize-project"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(module)
    return module


class VisualBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = load_module("gx_visualize_detect_backend", DETECT_PATH)
        cls.renderer = load_module("gx_visualize_render_archify", RENDER_PATH)

    def fake_archify(self, root, validation_exit=0, deliver_exit=0):
        script = root / "fake_archify.py"
        script.write_text(
            textwrap.dedent(
                f"""
                import pathlib
                import sys

                phase = sys.argv[1]
                if phase == "validate":
                    print("validated")
                    raise SystemExit({validation_exit})
                if phase == "deliver":
                    output = pathlib.Path(sys.argv[-2])
                    output.write_text('<html lang="ko"><body>Archify 결과</body></html>', encoding="utf-8")
                    print(str(output))
                    raise SystemExit({deliver_exit})
                raise SystemExit(64)
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        return [sys.executable, str(script)]

    def invalid_project_ir(self, root):
        project_root = root / "project"
        ir_path = project_root / ".dev" / "feat-energy" / "visual" / "trace.json"
        ir_path.parent.mkdir(parents=True)
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["nodes"][0]["evidence"] = [
            {
                "file": ".dev/feat-energy/missing.md",
                "line": 1,
                "kind": "artifact",
            }
        ]
        payload["nodes"][1]["evidence"] = [{"kind": "inferred"}]
        ir_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return project_root, ir_path

    def successful_archify_with_marker(self, root):
        marker = root / "archify-called.txt"
        script = root / "successful_archify.py"
        script.write_text(
            textwrap.dedent(
                f"""
                import pathlib
                import sys

                pathlib.Path({str(marker)!r}).write_text("called", encoding="utf-8")
                if sys.argv[1] == "deliver":
                    output = pathlib.Path(sys.argv[-2])
                    output.write_text("<html>fake success</html>", encoding="utf-8")
                raise SystemExit(0)
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        return [sys.executable, str(script)], marker

    def test_explicit_archify_command_is_detected_without_install_path_guessing(self):
        result = self.detector.detect_backend(
            archify_command=[sys.executable, "--version"],
            node_command=sys.executable,
        )

        self.assertEqual(result["backend"], "archify")
        self.assertIn("explicit", result["reason"])
        self.assertIsInstance(result["version"], str)

    def test_missing_node_skips_archify_and_selects_static_without_mermaid(self):
        with mock.patch.object(self.detector.shutil, "which", return_value=None):
            result = self.detector.detect_backend()

        self.assertEqual(result["backend"], "static")
        self.assertIn("node", result["reason"].lower())
        self.assertIsNone(result["version"])

    def test_non_executable_node_candidate_selects_static(self):
        with mock.patch.object(self.detector.shutil, "which", return_value="/tools/node"):
            with mock.patch.object(self.detector, "_command_version", return_value=None):
                result = self.detector.detect_backend()

        self.assertEqual(result["backend"], "static")
        self.assertIn("node", result["reason"].lower())

    def test_path_detection_selects_mermaid_when_archify_is_absent(self):
        locations = {"node": "/tools/node", "mmdc": "/tools/mmdc"}
        with mock.patch.object(
            self.detector.shutil,
            "which",
            side_effect=lambda name: locations.get(name),
        ):
            with mock.patch.object(
                self.detector,
                "_command_version",
                return_value="mermaid-cli 1.0",
            ):
                result = self.detector.detect_backend()

        self.assertEqual(result["backend"], "mermaid")
        self.assertEqual(result["version"], "mermaid-cli 1.0")
        self.assertIn("Archify", result["reason"])

    def test_malformed_archify_override_is_candidate_failure_not_api_error(self):
        cases = (
            ("explicit-normalization", {"archify_command": '"'}),
            ("explicit-execution", {"archify_command": ["bad\0command"]}),
            ("environment-normalization", {}),
        )
        for name, arguments in cases:
            with self.subTest(name=name):
                with mock.patch.dict(
                    self.detector.os.environ,
                    {"GX_ARCHIFY_COMMAND": '"'},
                    clear=False,
                ):
                    result = self.detector.detect_backend(
                        node_command=sys.executable,
                        mermaid_command=[sys.executable, "--version"],
                        **arguments,
                    )

                self.assertEqual(result["backend"], "mermaid")
                self.assertIsInstance(result["reason"], str)
                self.assertIsInstance(result["version"], str)

    def test_archify_success_runs_validate_then_deliver_and_records_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(
                FIXTURE,
                root / "output",
                self.fake_archify(root),
            )
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["backend"], "archify")
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual([item["phase"] for item in receipt["attempts"]], ["validate", "deliver"])
        self.assertTrue(all(item["exit_code"] == 0 for item in receipt["attempts"]))
        self.assertTrue(receipt["artifact_path"].endswith("trace.html"))
        self.assertIn("Archify 결과", html_text)

    def test_nonzero_archify_validation_falls_back_and_retains_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(
                FIXTURE,
                root / "output",
                self.fake_archify(root, validation_exit=23),
            )
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["backend"], "mermaid")
        self.assertEqual(receipt["status"], "fallback")
        self.assertEqual(receipt["backend"], "mermaid")
        self.assertEqual(receipt["attempts"][0]["backend"], "archify")
        self.assertEqual(receipt["attempts"][0]["phase"], "validate")
        self.assertEqual(receipt["attempts"][0]["exit_code"], 23)
        self.assertEqual(receipt["attempts"][0]["status"], "failed")
        self.assertIn("flowchart LR", html_text)

    def test_nonzero_deliver_is_the_top_level_failed_command_in_fallback_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(
                FIXTURE,
                root / "output",
                self.fake_archify(root, deliver_exit=17),
            )
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))

        self.assertEqual(receipt["status"], "fallback")
        self.assertEqual(receipt["exit_code"], 17)
        self.assertEqual(receipt["command"], receipt["attempts"][1]["command"])
        self.assertEqual(receipt["attempts"][1]["phase"], "deliver")
        self.assertEqual(receipt["attempts"][1]["status"], "failed")

    def test_stale_archify_html_is_not_accepted_when_deliver_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "no_artifact.py"
            script.write_text("raise SystemExit(0)\n", encoding="utf-8")
            output = root / "output"
            output.mkdir()
            (output / "trace.html").write_text("stale", encoding="utf-8")

            result = self.renderer.render_archify(
                FIXTURE,
                output,
                [sys.executable, str(script)],
            )
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))

        self.assertEqual(result["backend"], "mermaid")
        self.assertEqual(receipt["status"], "fallback")
        self.assertEqual(receipt["attempts"][1]["status"], "failed")
        self.assertIn("non-empty artifact", receipt["attempts"][1]["stderr"])

    def test_mermaid_failure_continues_to_static_and_keeps_archify_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_fallback = self.renderer._render_fallback

            def render_or_fail(ir_path, output_dir, backend):
                if backend == "mermaid":
                    raise RuntimeError("mermaid unavailable")
                return real_fallback(ir_path, output_dir, backend)

            with mock.patch.object(
                self.renderer,
                "_render_fallback",
                side_effect=render_or_fail,
            ) as fallback:
                result = self.renderer.render_archify(
                    FIXTURE,
                    root / "output",
                    self.fake_archify(root, validation_exit=9),
                )

            self.assertEqual(result["backend"], "static")
            self.assertEqual([call.args[2] for call in fallback.call_args_list], ["mermaid", "static"])
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["attempts"][0]["backend"], "archify")
            self.assertEqual(receipt["attempts"][1]["backend"], "mermaid")
            self.assertEqual(receipt["attempts"][2]["backend"], "static")

    def test_total_failure_removes_stale_target_html_and_leaves_failed_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            html_path = output / "trace.html"
            html_path.write_text("STALE", encoding="utf-8")

            with mock.patch.object(
                self.renderer,
                "_render_fallback",
                side_effect=RuntimeError("fallback unavailable"),
            ):
                with self.assertRaisesRegex(RuntimeError, "all failed"):
                    self.renderer.render_archify(
                        FIXTURE,
                        output,
                        self.fake_archify(root, validation_exit=9),
                    )

            receipt = json.loads((output / "trace.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")
            self.assertFalse(html_path.exists())

    def test_project_root_reaches_fallback_after_archify_failure(self):
        ir_path = PROJECT_FIXTURE / ".dev" / "feat-energy" / "visual" / "trace.json"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(
                ir_path,
                root / "output",
                self.fake_archify(root, validation_exit=9),
                project_root=PROJECT_FIXTURE,
            )

        self.assertIn(result["backend"], {"mermaid", "static"})

    def test_local_validation_failure_blocks_successful_archify_and_writes_failed_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project_root, ir_path = self.invalid_project_ir(root)
            command, marker = self.successful_archify_with_marker(root)
            output = root / "output"
            output.mkdir()
            html_path = output / "trace.html"
            html_path.write_text("STALE", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "IR validation failed"):
                self.renderer.render_archify(
                    ir_path,
                    output,
                    command,
                    project_root=project_root,
                )

            receipt = json.loads((output / "trace.receipt.json").read_text(encoding="utf-8"))

        self.assertFalse(marker.exists())
        self.assertFalse(html_path.exists())
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["backend"])
        self.assertIn(".dev/feat-energy/missing.md", receipt["missing_inputs"])
        self.assertTrue(receipt["errors"])

    def test_cli_project_root_blocks_successful_archify_on_local_validation_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project_root, ir_path = self.invalid_project_ir(root)
            command, marker = self.successful_archify_with_marker(root)
            output = root / "output"
            output.mkdir()
            html_path = output / "trace.html"
            html_path.write_text("STALE", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_PATH),
                    str(ir_path),
                    str(output),
                    "--archify-command",
                    subprocess.list2cmdline(command),
                    "--project-root",
                    str(project_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            receipt = json.loads((output / "trace.receipt.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 1)
        self.assertFalse(marker.exists())
        self.assertFalse(html_path.exists())
        self.assertEqual(receipt["status"], "failed")
        self.assertIn(".dev/feat-energy/missing.md", receipt["missing_inputs"])


if __name__ == "__main__":
    unittest.main()
