import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_test_support import load


hook = load("gx_codex_hook", ".claude/hooks/codex_hook.py")


class GuardTests(unittest.TestCase):
    def test_ask_becomes_deny(self):
        """Changing the Codex ask conversion to pass-through must fail here."""
        answer = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "verify pending",
            }
        }
        with tempfile.TemporaryDirectory() as cwd:
            payload = {
                "cwd": cwd,
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m test"},
            }
            result = subprocess.CompletedProcess([], 0, json.dumps(answer), "")
            with patch.object(hook.subprocess, "run", return_value=result) as run:
                out = hook.run_guard(payload, bash="bash")
            self.assertEqual(
                out["hookSpecificOutput"]["permissionDecision"], "deny"
            )
            self.assertEqual(run.call_args.kwargs["cwd"], cwd)

    def test_guard_crash_denies(self):
        """Changing a failed Bash process to pass must fail closed here."""
        result = subprocess.CompletedProcess([], 127, "", "missing script")
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook.subprocess, "run", return_value=result):
                out = hook.run_guard({"cwd": cwd}, bash="bash")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_empty_guard_output_allows_tool(self):
        """Treating the Bash guard's normal empty output as deny must fail here."""
        result = subprocess.CompletedProcess([], 0, " \n", "")
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook.subprocess, "run", return_value=result):
                out = hook.run_guard({"cwd": cwd}, bash="bash")
        self.assertIsNone(out)

    def test_deny_output_is_preserved(self):
        """Changing a valid Bash deny into an allow must fail here."""
        answer = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "protected branch",
            }
        }
        result = subprocess.CompletedProcess([], 0, json.dumps(answer), "")
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook.subprocess, "run", return_value=result):
                out = hook.run_guard({"cwd": cwd}, bash="bash")
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_invalid_guard_json_denies(self):
        """Passing malformed Bash output through must fail closed here."""
        result = subprocess.CompletedProcess([], 0, "not-json", "")
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook.subprocess, "run", return_value=result):
                out = hook.run_guard({"cwd": cwd}, bash="bash")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_timeout_denies(self):
        """Allowing a timed out protection guard must fail closed here."""
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(
                hook.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["bash"], 30),
            ):
                out = hook.run_guard({"cwd": cwd}, bash="bash")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_unknown_decision_denies(self):
        """Returning a decision unsupported by Codex must fail closed here."""
        answer = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "unexpected",
            }
        }
        result = subprocess.CompletedProcess([], 0, json.dumps(answer), "")
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook.subprocess, "run", return_value=result):
                out = hook.run_guard({"cwd": cwd}, bash="bash")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_missing_bash_denies(self):
        """Trying to execute a missing Bash interpreter must fail closed."""
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(hook, "find_bash", return_value=None):
                out = hook.run_guard({"cwd": cwd})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_invalid_cwd_denies_without_raising(self):
        """Letting an invalid payload path crash the hook must fail closed."""
        out = hook.run_guard({"cwd": "\0"}, bash="bash")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_guard_cli_returns_deny_json_for_invalid_input(self):
        """Replacing guard-mode invalid-input denial with a crash must fail here."""
        script = Path(hook.__file__)
        proc = subprocess.run(
            [sys.executable, str(script), "guard"],
            input=b"not-json",
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        output = json.loads(proc.stdout.decode("ascii"))
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )


class BashLookupTests(unittest.TestCase):
    def test_windows_prefers_known_git_bash_to_path_wsl_shim(self):
        """Letting System32 WSL win over Git Bash must fail this lookup contract."""
        wsl = r"C:\Windows\System32\bash.exe"
        expected = str(
            Path(hook.os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Git/bin/bash.exe"
        )
        windows_os = SimpleNamespace(name="nt", environ=os.environ)
        with patch.object(hook, "os", windows_os), patch.object(
            hook.shutil, "which", return_value=wsl
        ), patch.object(hook.Path, "is_file", autospec=True, return_value=True):
            self.assertEqual(hook.find_bash(), expected)

    def test_windows_rejects_path_wsl_shim_when_git_bash_is_missing(self):
        """Returning the WSL shim as a runnable Bash must fail closed."""
        wsl = r"C:\Windows\System32\bash.exe"

        def exists(path):
            return str(path).replace("\\", "/").lower().endswith(
                "/windows/system32/bash.exe"
            )

        windows_os = SimpleNamespace(name="nt", environ=os.environ)
        with patch.object(hook, "os", windows_os), patch.object(
            hook.shutil, "which", return_value=wsl
        ), patch.object(hook.Path, "is_file", autospec=True, side_effect=exists):
            self.assertIsNone(hook.find_bash())

    def test_windows_accepts_git_bash_found_only_on_path(self):
        """Rejecting a non-WSL Git Bash from a custom user PATH must fail here."""
        custom_git_bash = r"D:\Tools\Git\bin\bash.exe"

        def exists(path):
            return str(path) == custom_git_bash

        windows_os = SimpleNamespace(name="nt", environ=os.environ)
        with patch.object(hook, "os", windows_os), patch.object(
            hook.shutil, "which", return_value=custom_git_bash
        ), patch.object(hook.Path, "is_file", autospec=True, side_effect=exists):
            self.assertEqual(hook.find_bash(), custom_git_bash)

    @unittest.skipUnless(hook.os.name == "nt", "Windows Git Bash integration only")
    def test_windows_default_bash_executes_shared_guard(self):
        """A WSL launcher must not make an unprotected tool call deny here."""
        resolved = hook.find_bash()
        self.assertIsNotNone(resolved)
        normalized = resolved.replace("\\", "/").lower()
        self.assertFalse(normalized.endswith("/windows/system32/bash.exe"))
        cwd = str(Path(hook.__file__).parents[2])
        self.assertIsNone(
            hook.run_guard(
                {"cwd": cwd, "tool_name": "Bash", "tool_input": {"command": "git status"}}
            )
        )


class HookRegistrationTests(unittest.TestCase):
    def test_codex_registration_uses_adapter_for_bash(self):
        """Broad matcher or a direct Bash command must fail this Codex contract."""
        config = json.loads((Path(hook.__file__).parents[2] / "hooks.json").read_text())
        pre = config["hooks"]["PreToolUse"]
        post = config["hooks"]["PostToolUse"]

        self.assertEqual(pre[0]["matcher"], "^Bash$")
        self.assertEqual(post[0]["matcher"], "AskUserQuestion|request_user_input")
        for group, mode in ((pre[0], "guard"), (post[0], "capture")):
            command = group["hooks"][0]
            self.assertIn("codex_hook.py", command["command"])
            self.assertTrue(command["command"].endswith(" " + mode))
            self.assertIn("codex_hook.py", command["commandWindows"])
            self.assertTrue(command["commandWindows"].endswith(" " + mode))
            self.assertEqual(command["timeout"], 35)
            self.assertNotIn("shell", command)
