import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "skills" / "gx-visualize" / "scripts"
DETECT_PATH = SCRIPTS / "detect_backend.py"
FALLBACK_PATH = SCRIPTS / "render_fallback.py"
FIXTURE = ROOT / "tests" / "fixtures" / "gx-trace.valid.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(module)
    return module


class EnsureArchifyInstallTests(unittest.TestCase):
    """ensure_archify(): archify가 없으면 묻지 않고 npx로 1회 자동 설치한다.

    실제 네트워크를 쓰지 않도록 `npx -y skills add tt-a1i/archify -g`는 가짜 실행 파일로
    대체한다 (_ARCHIFY_INSTALL_COMMAND monkeypatch) — 실제 npx를 호출하지 않는다.
    """

    @classmethod
    def setUpClass(cls):
        cls.detector = load_module("gx_arch_install_detect_backend", DETECT_PATH)

    def _candidate(self, root: Path) -> Path:
        """ensure_archify()가 찾을 Archify 후보 경로 (실제 설치 위치를 흉내낸 임시 경로)."""
        return root / "archify" / "bin" / "archify.mjs"

    def _write_installer(
        self,
        root: Path,
        *,
        exit_code: int,
        create_bin: bool,
        counter: Path | None = None,
    ) -> list[str]:
        """`npx -y skills add tt-a1i/archify -g`를 대신할 가짜 실행 파일.

        create_bin=True면 실제 설치처럼 후보 경로에 doctor 성공 응답 스텁을 만든다.
        counter가 있으면 호출될 때마다 한 줄씩 남겨 호출 횟수를 셀 수 있게 한다.
        """
        script = root / "fake_npx_install.py"
        bin_path = self._candidate(root)
        lines = ["import pathlib"]
        if counter is not None:
            lines.append(f"with open({str(counter)!r}, 'a', encoding='utf-8') as _fh:")
            lines.append("    _fh.write('x\\n')")
        if create_bin:
            lines.append(f"_bin = pathlib.Path({str(bin_path)!r})")
            lines.append("_bin.parent.mkdir(parents=True, exist_ok=True)")
            lines.append(
                "_bin.write_text("
                "'import sys\\n'"
                "'if len(sys.argv) > 1 and sys.argv[1] == \"doctor\":\\n'"
                "'    print(\"Archify is ready.\")\\n'"
                "'    raise SystemExit(0)\\n'"
                "'raise SystemExit(2)\\n', "
                "encoding='utf-8')"
            )
        lines.append(f"raise SystemExit({exit_code})")
        script.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return [sys.executable, str(script)]

    def _ensure_with_fake_install(self, root: Path, install_command: list[str]):
        with mock.patch.object(self.detector, "_ARCHIFY_CANDIDATES", (self._candidate(root),)):
            with mock.patch.object(self.detector, "_ARCHIFY_INSTALL_COMMAND", install_command):
                with mock.patch.object(self.detector.shutil, "which", return_value=sys.executable):
                    return self.detector.ensure_archify()

    def test_absent_archify_triggers_one_install_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install_command = self._write_installer(root, exit_code=0, create_bin=True)
            result = self._ensure_with_fake_install(root, install_command)

        self.assertTrue(result["available"])
        self.assertEqual(result["command"], [sys.executable, str(self._candidate(root))])
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["attempts"][0]["phase"], "install")

    def test_install_resolves_npx_to_absolute_path_before_invoking(self):
        # 판정 S: Windows에서 npx는 npx.CMD로만 PATH에 있어 shell=False + 맨 이름 "npx"는
        # CreateProcess가 못 찾아 FileNotFoundError로 끝난다(실측). node/mmdc처럼 shutil.which로
        # 해석한 절대경로를 argv[0]에 써야 한다 -- 맨 이름으로 되돌리면 called_argv[0]이
        # resolved_npx와 달라져 이 테스트가 실패한다.
        resolved_npx = r"C:\Program Files\nodejs\npx.CMD"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(self.detector, "_ARCHIFY_CANDIDATES", (self._candidate(root),)):
                with mock.patch.object(
                    self.detector.shutil,
                    "which",
                    side_effect=lambda name: resolved_npx if name == "npx" else None,
                ):
                    with mock.patch.object(self.detector.subprocess, "run") as run:
                        run.return_value = mock.Mock(returncode=1, stderr="")
                        result = self.detector.ensure_archify()

        called_argv = run.call_args.args[0]
        self.assertEqual(called_argv[0], resolved_npx)
        self.assertEqual(called_argv[1:], ["-y", "skills", "add", "tt-a1i/archify", "-g"])
        self.assertFalse(result["available"])

    def test_missing_npx_records_attempt_without_invoking_subprocess(self):
        # 판정 S: npx가 PATH에서 전혀 안 보이면(해석 실패) 없는 실행 파일을 호출해 예외를
        # 만들지 않고, subprocess를 아예 부르지 않은 채 정직하게 attempts에 남긴다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(self.detector, "_ARCHIFY_CANDIDATES", (self._candidate(root),)):
                with mock.patch.object(self.detector.shutil, "which", return_value=None):
                    with mock.patch.object(self.detector.subprocess, "run") as run:
                        result = self.detector.ensure_archify()

        run.assert_not_called()
        self.assertFalse(result["available"])
        self.assertEqual(len(result["attempts"]), 1)
        self.assertIsNone(result["attempts"][0]["exit_code"])
        self.assertIn("npx", result["attempts"][0]["stderr"])

    def test_cli_entry_point_installs_then_detects_via_ensure_archify(self):
        # 판정 P: SKILL.md:85는 `python detect_backend.py`를 그냥 실행하면 ensure_archify()를
        # 거친다고 서술한다. __main__이 detect_backend()만 부르도록 되돌리면 archify_install
        # 키가 아예 없거나 backend가 archify가 아니게 되어 이 테스트가 실패해야 한다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install_command = self._write_installer(root, exit_code=0, create_bin=True)
            with mock.patch.object(self.detector, "_ARCHIFY_CANDIDATES", (self._candidate(root),)):
                with mock.patch.object(self.detector, "_ARCHIFY_INSTALL_COMMAND", install_command):
                    with mock.patch.object(self.detector.shutil, "which", return_value=sys.executable):
                        buffer = io.StringIO()
                        with contextlib.redirect_stdout(buffer):
                            exit_code = self.detector.main()

        self.assertEqual(exit_code, 0)
        result = json.loads(buffer.getvalue())
        self.assertEqual(result["backend"], "archify")
        self.assertIn("archify_install", result)
        self.assertTrue(result["archify_install"]["available"])
        self.assertEqual(len(result["archify_install"]["attempts"]), 1)
        self.assertEqual(result["archify_install"]["attempts"][0]["phase"], "install")

    def test_install_is_attempted_only_once_per_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            counter = root / "install-calls.log"
            install_command = self._write_installer(
                root, exit_code=1, create_bin=False, counter=counter
            )
            result = self._ensure_with_fake_install(root, install_command)
            call_count = counter.read_text(encoding="utf-8").count("x\n")

        self.assertFalse(result["available"])
        self.assertEqual(call_count, 1)
        self.assertEqual(len(result["attempts"]), 1)

    def test_install_failure_falls_back_without_raising(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # 네트워크 차단을 흉내낸 0이 아닌 종료 코드
            install_command = self._write_installer(root, exit_code=1, create_bin=False)
            result = self._ensure_with_fake_install(root, install_command)  # 예외를 던지지 않아야 한다

        self.assertFalse(result["available"])
        self.assertIsNone(result["command"])
        self.assertEqual(result["attempts"][0]["exit_code"], 1)

    def test_exit_code_zero_with_promptscript_warning_is_not_success(self):
        # `npx skills add`는 PromptScript 실패를 출력하면서 exit 0으로 끝난다.
        # 성공 판정은 exit code가 아니라 bin/archify.mjs 존재로 한다 -- 여기서는 exit 0이지만
        # 실제 산출물을 만들지 않는 install을 흉내내 exit code만으로 성공 처리되지 않는지 확인한다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install_command = self._write_installer(root, exit_code=0, create_bin=False)
            result = self._ensure_with_fake_install(root, install_command)

        self.assertFalse(result["available"])
        self.assertEqual(result["attempts"][0]["exit_code"], 0)

    def test_fallback_html_states_no_diagram_was_produced(self):
        fallback = load_module("gx_arch_install_render_fallback", FALLBACK_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            result = fallback.render(FIXTURE, output_dir, "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("다이어그램은 생성되지 않았습니다", html_text)
        self.assertIn("npx -y skills add tt-a1i/archify -g", html_text)


if __name__ == "__main__":
    unittest.main()
