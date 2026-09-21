import importlib.util
import json
import shlex
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
# service 뷰만 diagram_type()이 "architecture"를 반환해 Archify를 실제로 시도한다
# (render_archify.py 판정 1) — validate-then-deliver 시퀀싱·폴백 체인·receipt 모양을
# pin하는 아래 4개 테스트는 그래서 trace가 아니라 이 fixture를 쓴다.
SERVICE_FIXTURE = ROOT / "tests" / "fixtures" / "gx-service.valid.json"
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
                if phase == "doctor":
                    print("Archify is ready.")
                    raise SystemExit(0)
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

    def realistic_archify_stub(self, root, *, version="2.17.0-dev.1"):
        """Reproduce real Archify's shape: `--version` fails (exit 2), `doctor` succeeds.

        A prior double used `[sys.executable, "--version"]` as the Archify stand-in --
        python's own `--version` succeeds, which hid judgment L (the detector still
        probed with `--version`, so a real Archify install was never actually
        detectable). This stub fails `--version` exactly like real Archify
        (docs/reports/2026-09-18-archify-ir-schema.md §1), so a regression back to the
        `--version` probe fails the tests that use it.
        """
        bin_dir = root / "archify" / "bin"
        bin_dir.mkdir(parents=True)
        script = bin_dir / "archify.mjs"
        script.write_text(
            textwrap.dedent(
                """
                import sys

                if len(sys.argv) > 1 and sys.argv[1] == "doctor":
                    print("Archify is ready.")
                    raise SystemExit(0)
                print("Unknown command", file=sys.stderr)
                raise SystemExit(2)
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        if version is not None:
            (root / "archify" / "package.json").write_text(
                json.dumps({"version": version}), encoding="utf-8"
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
        with tempfile.TemporaryDirectory() as temporary:
            command = self.realistic_archify_stub(Path(temporary))
            result = self.detector.detect_backend(
                archify_command=command,
                node_command=sys.executable,
            )

        self.assertEqual(result["backend"], "archify")
        self.assertIn("explicit", result["reason"])
        self.assertEqual(result["version"], "2.17.0-dev.1")

    def test_archify_probe_uses_doctor_not_version(self):
        # 판정 L: 실제 Archify는 --version에 exit 2로 실패하고 doctor에만 성공한다
        # (docs/reports/2026-09-18-archify-ir-schema.md §1). 탐지 프로브를 --version으로
        # 되돌리면 이 테스트가 반드시 실패해야 한다.
        with tempfile.TemporaryDirectory() as temporary:
            command = self.realistic_archify_stub(Path(temporary))
            version_probe = subprocess.run(
                [*command, "--version"], capture_output=True, text=True, check=False
            )
            self.assertNotEqual(0, version_probe.returncode)

            result = self.detector.detect_backend(archify_command=command, node_command=sys.executable)

        self.assertEqual(result["backend"], "archify")

    def test_detect_backend_and_render_archify_agree_on_the_same_command(self):
        # 판정 L 항목 5: render_archify.py는 detect_backend를 import하지 않지만, 같은
        # Archify 명령에 대해 두 모듈의 판정이 어긋나면 안 된다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = self.fake_archify(root)

            detection = self.detector.detect_backend(archify_command=command, node_command=sys.executable)
            self.assertEqual(detection["backend"], "archify")

            result = self.renderer.render_archify(SERVICE_FIXTURE, root / "output", command)

        self.assertEqual(result["backend"], "archify")

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
                SERVICE_FIXTURE,
                root / "output",
                self.fake_archify(root),
            )
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["backend"], "archify")
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual([item["phase"] for item in receipt["attempts"]], ["validate", "deliver"])
        self.assertTrue(all(item["exit_code"] == 0 for item in receipt["attempts"]))
        self.assertTrue(receipt["artifact_path"].endswith("service.html"))
        self.assertIn("Archify 결과", html_text)

    def test_archify_success_html_carries_snapshot_banner_when_requested(self):
        # I7: Archify가 만든 HTML은 배너 개념을 모른다 - render_archify()가 전달 후
        # 직접 삽입해야 한다. 폴백 경로와 달리 별도 코드 경로라 따로 확인한다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(
                SERVICE_FIXTURE,
                root / "output",
                self.fake_archify(root),
                snapshot_banner=True,
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["backend"], "archify")
        self.assertIn("생성 시각", html_text)
        self.assertIn("갱신되지 않습니다", html_text)
        self.assertIn("Archify 결과", html_text)

    def test_archify_command_json_array_round_trips_paths_with_spaces(self):
        # I2: 이 환경의 실제 Archify command[0]은 C:\Program Files\nodejs\node.EXE처럼
        # 공백을 포함한다. list2cmdline+shlex.split(posix=False) 왕복은 이 케이스에서
        # 항등이 아니라서(공백 때문에 인용부호가 붙고 벗겨지지 않는다) 조용히 폴백을
        # 유발한다(2026-09-18 최종 리뷰 I2, 실측: exit 0 + WinError 5). JSON 배열
        # 직렬화는 공백과 무관하게 그대로 왕복해야 한다.
        command = [r"C:\Program Files\nodejs\node.EXE", r"C:\Users\dev\archify.mjs"]

        broken = shlex.split(subprocess.list2cmdline(command), posix=False)
        self.assertNotEqual(broken, command, "list2cmdline/shlex 왕복이 이미 항등이면 이 테스트는 무의미하다")

        serialized = json.dumps(command)
        self.assertEqual(self.renderer._normalize_command(serialized), command)

    def test_archify_success_receipt_carries_ir_declared_missing_inputs(self):
        # I1: archify 성공 receipt는 별도로 조립되므로 missing_inputs를 깜빡하면 폴백
        # 경로(local_receipt를 그대로 펼치는 render_fallback.render)와 비대칭이 된다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path = root / "service.json"
            ir_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "view": "service",
                        "locale": "ko-KR",
                        "title": "t",
                        "nodes": [{"id": "n1", "kind": "api", "label": "a", "status": "unknown", "evidence": []}],
                        "edges": [],
                        "missing_inputs": ["cross-domain-edge"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = self.renderer.render_archify(ir_path, root / "output", self.fake_archify(root))
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))

        self.assertEqual(result["backend"], "archify")
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["missing_inputs"], ["cross-domain-edge"])

    def test_output_name_scopes_separate_domain_renders_to_distinct_files(self):
        # 판정 Y: 도메인마다 같은 output_dir에 같은 view("service")의 IR을 렌더할 때
        # output_name이 없으면 둘 다 service.html로 서로를 덮어쓴다. --output-name을
        # 주면 각 렌더가 자기 이름의 파일을 갖고 둘 다 살아남아야 한다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / "output"
            first = self.renderer.render_archify(
                SERVICE_FIXTURE, output_dir, self.fake_archify(root), output_name="auth",
            )
            second = self.renderer.render_archify(
                SERVICE_FIXTURE, output_dir, self.fake_archify(root), output_name="code",
            )
            self.assertTrue(Path(first["html_path"]).is_file())
            self.assertTrue(Path(second["html_path"]).is_file())
            self.assertTrue(Path(first["receipt_path"]).is_file())
            self.assertTrue(Path(second["receipt_path"]).is_file())

        self.assertNotEqual(first["html_path"], second["html_path"])
        self.assertTrue(first["html_path"].endswith("auth.html"))
        self.assertTrue(second["html_path"].endswith("code.html"))

    def test_output_name_omitted_keeps_view_derived_filename(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(SERVICE_FIXTURE, root / "output", self.fake_archify(root))

        self.assertTrue(result["html_path"].endswith("service.html"))
        self.assertTrue(result["receipt_path"].endswith("service.receipt.json"))

    def test_nonzero_archify_validation_falls_back_and_retains_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render_archify(
                SERVICE_FIXTURE,
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
                SERVICE_FIXTURE,
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
            (output / "service.html").write_text("stale", encoding="utf-8")

            result = self.renderer.render_archify(
                SERVICE_FIXTURE,
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

            def render_or_fail(
                ir_path, output_dir, backend, output_name=None, snapshot_banner=False, html_dir=None,
            ):
                if backend == "mermaid":
                    raise RuntimeError("mermaid unavailable")
                return real_fallback(
                    ir_path, output_dir, backend, output_name=output_name, snapshot_banner=snapshot_banner,
                    html_dir=html_dir,
                )

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

            # 임시 디렉터리가 살아 있는 동안 확인한다 - with 블록 밖에서 확인하면
            # TemporaryDirectory 정리로 경로 자체가 사라져 무엇을 확인하든 항상
            # 통과하는 무의미한 검사가 된다(이 테스트에 실제로 있던 결함).
            self.assertFalse(marker.exists())
            # I8: 이번 IR 검증 실패가 지난 실행의 정상 HTML을 지우면 안 된다 - 새로
            # 렌더를 시도하지도 못했으므로 이전 산출물이 그대로 남아야 한다
            # (2026-09-18 최종 리뷰 I8).
            self.assertTrue(html_path.exists())
            self.assertEqual(html_path.read_text(encoding="utf-8"), "STALE")
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
            self.assertTrue(html_path.exists())
            self.assertEqual(html_path.read_text(encoding="utf-8"), "STALE")
            self.assertEqual(receipt["status"], "failed")
            self.assertIn(".dev/feat-energy/missing.md", receipt["missing_inputs"])


if __name__ == "__main__":
    unittest.main()
