"""Behavior checks for the manually rendered Codex hook installation."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from codex_test_support import ROOT, load


installer = load("gx_install", "scripts/codex-install-hooks.py")
CLI = ROOT / "scripts/codex-install-hooks.py"
WRAPPER = ROOT / ".claude/hooks/run-hook.cmd"
DENY = {"cwd": "", "tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}
PASS = {"cwd": "", "tool_name": "Bash", "tool_input": {"command": "git status"}}


def git_bash():
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/bash.exe",
            Path(os.environ.get("LOCALAPPDATA", ".")) / "Programs/Git/bin/bash.exe",
        ]
        return next((str(path) for path in candidates if path.is_file()), None)
    return shutil.which("bash")


class InstallTests(unittest.TestCase):
    def test_space_path_is_quoted(self):
        """Removing Windows quotes would split a plugin path containing spaces."""
        value = installer.render(Path("D:/plugin with spaces"), "C:/Python/python.exe")
        item = value["hooks"]["PreToolUse"][0]
        self.assertEqual(item["matcher"], "^Bash$")
        self.assertIn('"D:/plugin with spaces/.claude/hooks/codex_hook.py"', item["hooks"][0]["commandWindows"])
        json.loads(json.dumps(value))

    def test_other_hooks_survive_and_merge_is_idempotent(self):
        """Replacing the hooks object or appending duplicates must fail here."""
        external = {"hooks": [{"type": "command", "command": "echo external"}]}
        existing = {"description": "keep", "hooks": {"Stop": [external]}}
        generated = installer.render(Path("/tmp/plugin"), "/usr/bin/python3")
        result = installer.merge(existing, generated)
        self.assertEqual(result["description"], "keep")
        self.assertEqual(result["hooks"]["Stop"], [external])
        self.assertEqual(installer.merge(result, generated), result)
        self.assertEqual(existing, {"description": "keep", "hooks": {"Stop": [external]}})

    def test_generated_commands_execute_with_spaces(self):
        """Quoting that only looks right in JSON but fails in a shell is caught."""
        bash = git_bash()
        if not bash:
            self.skipTest("Git Bash unavailable")
        with tempfile.TemporaryDirectory(prefix="plugin with spaces ") as directory:
            root = Path(directory)
            hooks = root / ".claude/hooks"
            hooks.mkdir(parents=True)
            for filename in ("codex_hook.py", "pre-tool-guard.sh"):
                shutil.copy2(ROOT / ".claude/hooks" / filename, hooks / filename)
            command = installer.render(root, sys.executable)["hooks"]["PreToolUse"][0]["hooks"][0]
            payload = dict(DENY, cwd=str(root))
            for argv in ([bash, "-c", command["command"]],):
                with self.subTest(argv=argv):
                    proc = subprocess.run(argv, input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True, cwd=root, timeout=35)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
            if os.name == "nt":
                proc = subprocess.run(command["commandWindows"], shell=True, input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True, cwd=root, timeout=35)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    @unittest.skipUnless(os.name == "nt", "Windows cmd integration")
    def test_windows_metachar_paths_execute_and_install(self):
        """An unquoted ampersand must not split the hook command or bypass self-test."""
        for prefix in ("gx&", "gx!", "gx space "):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory(prefix=prefix) as directory:
                root = Path(directory)
                scripts = root / "scripts"
                hooks = root / ".claude/hooks"
                scripts.mkdir()
                hooks.mkdir(parents=True)
                shutil.copy2(CLI, scripts / CLI.name)
                for filename in ("codex_hook.py", "pre-tool-guard.sh"):
                    shutil.copy2(ROOT / ".claude/hooks" / filename, hooks / filename)
                command = installer.render(root, sys.executable)["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"]
                payload = dict(DENY, cwd=str(root))
                probe = subprocess.run(command, shell=True, input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True, cwd=root, timeout=35)
                self.assertEqual(probe.returncode, 0, probe.stderr)
                self.assertEqual(json.loads(probe.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
                target = root / "hooks.json"
                target.write_bytes(b'{"hooks":{}}')
                installed = subprocess.run([sys.executable, str(scripts / CLI.name), "--write", str(target)], capture_output=True, timeout=35, cwd=root, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                self.assertEqual(installed.returncode, 0, installed.stderr.decode("utf-8", errors="replace"))
                self.assertIn("PreToolUse", json.loads(target.read_text(encoding="utf-8"))["hooks"])

    def test_unsafe_windows_path_characters_are_rejected(self):
        """Percent expansion, quotes and line breaks cannot become cmd syntax."""
        for unsafe in ("%", '"', "\r", "\n", "^"):
            with self.subTest(unsafe=repr(unsafe)):
                with self.assertRaisesRegex(ValueError, "Windows cmd"):
                    installer.render(Path("D:/R" + unsafe + "D"), "C:/Python/python.exe")
                with self.assertRaisesRegex(ValueError, "Windows cmd"):
                    installer.render(Path("D:/plugin"), "C:/Py" + unsafe + "thon/python.exe")

    @unittest.skipUnless(os.name == "nt", "Windows path integration")
    def test_unsafe_plugin_root_is_rejected_before_write(self):
        """A percent-sign root must leave the requested config untouched."""
        with tempfile.TemporaryDirectory(prefix="gx%") as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(CLI, scripts / CLI.name)
            target = root / "hooks.json"
            target.write_bytes(b'{"hooks":{}}')
            proc = subprocess.run([sys.executable, str(scripts / CLI.name), "--write", str(target)], capture_output=True, cwd=root, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Windows cmd", proc.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(target.read_bytes(), b'{"hooks":{}}')
            self.assertEqual(list(root.glob("hooks.json.bak-*")), [])

    def test_cli_self_test_runs_quoted_command_before_write(self):
        """A broken generated command must not replace a config, even in a spaced root."""
        with tempfile.TemporaryDirectory(prefix="plugin with spaces ") as directory:
            root = Path(directory)
            scripts = root / "scripts"
            hooks = root / ".claude/hooks"
            scripts.mkdir()
            hooks.mkdir(parents=True)
            shutil.copy2(CLI, scripts / CLI.name)
            for filename in ("codex_hook.py", "pre-tool-guard.sh"):
                shutil.copy2(ROOT / ".claude/hooks" / filename, hooks / filename)
            target = root / "hooks.json"
            target.write_bytes(b'{"hooks":{}}')
            argv = [sys.executable, str(scripts / CLI.name), "--write", str(target)]
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            success = subprocess.run(argv, capture_output=True, timeout=35, env=env, cwd=root)
            self.assertEqual(success.returncode, 0, success.stderr.decode("utf-8", errors="replace"))
            installed = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("plugin with spaces", installed["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"])
            before = target.read_bytes()
            (hooks / "pre-tool-guard.sh").unlink()
            failed = subprocess.run(argv, capture_output=True, timeout=35, env=env, cwd=root)
            self.assertEqual(failed.returncode, 2, failed.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(target.read_bytes(), before)

    def test_write_preserves_existing_hooks_and_second_write_is_noop(self):
        """A second install must preserve other hooks and avoid new backups."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hooks.json"
            target.write_text(json.dumps({"hooks": {"Stop": [{"matcher": ".*", "hooks": [{"type": "command", "command": "echo external"}]}]}}), encoding="utf-8")
            first = subprocess.run([sys.executable, str(CLI), "--write", str(target)], text=True, encoding="utf-8", errors="replace", capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["hooks"]["Stop"][0]["hooks"][0]["command"], "echo external")
            self.assertEqual(len(list(target.parent.glob("hooks.json.bak-*"))), 1)
            before = target.read_bytes()
            second = subprocess.run([sys.executable, str(CLI), "--write", str(target), "--cmd"], text=True, encoding="utf-8", errors="replace", capture_output=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(len(list(target.parent.glob("hooks.json.bak-*"))), 1)

    def test_invalid_existing_config_is_not_modified(self):
        """A JSON parse failure must leave the original bytes untouched."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hooks.json"
            target.write_bytes(b"{broken")
            proc = subprocess.run([sys.executable, str(CLI), "--write", str(target)], text=True, encoding="utf-8", errors="replace", capture_output=True)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(target.read_bytes(), b"{broken")
            self.assertEqual(list(target.parent.glob("hooks.json.bak-*")), [])

    def test_invalid_existing_hook_shape_is_not_modified(self):
        """A malformed existing hook entry must fail cleanly before backup."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hooks.json"
            target.write_bytes(b'{"hooks":{"PreToolUse":[{"hooks":null}]}}')
            proc = subprocess.run([sys.executable, str(CLI), "--write", str(target)], capture_output=True, timeout=35, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(proc.returncode, 2, proc.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(target.read_bytes(), b'{"hooks":{"PreToolUse":[{"hooks":null}]}}')
            self.assertEqual(list(target.parent.glob("hooks.json.bak-*")), [])

    def test_old_gx_hook_is_preserved_with_warning(self):
        """A prior Bash hook path must remain visible for manual deduplication."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hooks.json"
            old_group = {"matcher": "exec_command|local_shell|shell", "hooks": [{"type": "command", "command": "bash /old/plugin/.claude/hooks/pre-tool-guard.sh"}]}
            target.write_text(json.dumps({"hooks": {"PreToolUse": [old_group]}}), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(CLI), "--write", str(target)], capture_output=True, timeout=35, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0], old_group)
            self.assertIn("중복", proc.stderr.decode("utf-8", errors="replace"))

    def test_backup_timestamp_collision_keeps_both_versions(self):
        """A reused clock tick must not overwrite an earlier backup."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hooks.json"
            stamp = "20260914T120000000000"
            first_backup = target.with_name(target.name + ".bak-" + stamp)
            first_backup.write_bytes(b"older")

            class FrozenClock:
                @staticmethod
                def now():
                    return __import__("datetime").datetime(2026, 9, 14, 12)

            with patch.object(installer, "datetime", FrozenClock):
                second_backup = installer.backup(target, b"current")
            self.assertEqual(first_backup.read_bytes(), b"older")
            self.assertEqual(second_backup.read_bytes(), b"current")
            self.assertNotEqual(first_backup, second_backup)

    def test_shell_launcher_renders_adapter(self):
        """The shell entry point must delegate to the JSON-safe installer."""
        bash = git_bash()
        if not bash:
            self.skipTest("Git Bash unavailable")
        proc = subprocess.run([bash, str(ROOT / "scripts/codex-install-hooks.sh")], capture_output=True, timeout=35)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
        rendered = json.loads(proc.stdout)
        self.assertIn("codex_hook.py", rendered["hooks"]["PreToolUse"][0]["hooks"][0]["command"])
        self.assertEqual(rendered["hooks"]["PreToolUse"][0]["matcher"], "^Bash$")

    @unittest.skipUnless(os.name == "nt", "Windows cmd integration")
    def test_wrapper_preserves_failure_and_bang_path(self):
        """A batch block swallowing ERRORLEVEL or expanding ! breaks this."""
        with tempfile.TemporaryDirectory(prefix="hook space! ") as directory:
            root = Path(directory)
            hook = root / "exit-seven.sh"
            hook.write_text("exit 7\n", encoding="utf-8")
            proc = subprocess.run(f'"{WRAPPER}" "{hook}"', shell=True, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 7, proc.stderr)
            missing = subprocess.run(f'"{WRAPPER}" "{root / "missing.sh"}"', shell=True, capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)


if __name__ == "__main__":
    unittest.main()
