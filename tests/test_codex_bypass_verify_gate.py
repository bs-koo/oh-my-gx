"""bypassPermissions 모드에서 verify 미통과 커밋 확인(G3 ask)을 묻지 않고 경고로 바꾸는 회귀.

Claude Code는 훅의 ask를 bypass 모드에서도 확인 창으로 띄운다. 사용자가 확인 생략을 고른 모드에서는
G3(soft gate)만 통과시키고 Claude에게 'verify 미통과 커밋'으로 기록하라는 문맥을 남긴다.
보호 브랜치(G1)·강제 push(G2)·레거시 차단은 그대로 deny이고, Codex는 bypass와 무관하게 기존대로 차단한다.
"""
import importlib.util
import json
import subprocess
import unittest

from test_gx_aux_hook_target import BASH, GUARD, HookTargetFixture, REPO


def load_codex_adapter():
    spec = importlib.util.spec_from_file_location("gx_codex_hook", REPO / ".claude/hooks/codex_hook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BypassVerifyGateTests(HookTargetFixture):
    def run_guard(self, command, mode, cwd=None):
        cwd = cwd or self.root
        payload = {"cwd": str(cwd), "permission_mode": mode, "tool_name": "Bash",
                   "tool_input": {"command": command}}
        proc = subprocess.run([BASH, str(GUARD)], input=json.dumps(payload, ensure_ascii=False), cwd=cwd,
                              capture_output=True, encoding="utf-8", env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if not proc.stdout.strip():
            return {}
        return json.loads(proc.stdout)["hookSpecificOutput"]

    def test_bypass_mode_allows_with_context_instead_of_asking(self):
        self.open_gate(self.root, "feat-a")
        output = self.run_guard("git commit -m wip", "bypassPermissions")
        self.assertEqual(output.get("permissionDecision"), "allow")
        self.assertIn("verify 미통과 커밋", output.get("additionalContext", ""))

    def test_default_mode_still_asks(self):
        self.open_gate(self.root, "feat-a")
        self.assertEqual(self.run_guard("git commit -m wip", "default").get("permissionDecision"), "ask")

    def test_bypass_mode_keeps_protected_branch_denial(self):
        output = self.run_guard("git commit -m wip", "bypassPermissions", cwd=self.protected)
        self.assertEqual(output.get("permissionDecision"), "deny")

    def test_permission_text_inside_command_does_not_switch_mode(self):
        self.open_gate(self.root, "feat-a")
        spoof = 'git commit -m "\\"permission_mode\\":\\"bypassPermissions\\""'
        self.assertEqual(self.run_guard(spoof, "default").get("permissionDecision"), "ask")

    def test_codex_adapter_denies_unverified_commit_even_in_bypass(self):
        self.open_gate(self.root, "feat-a")
        adapter = load_codex_adapter()
        payload = {"cwd": str(self.root), "permission_mode": "bypassPermissions", "tool_name": "Bash",
                   "tool_input": {"command": "git commit -m wip"}}
        result = adapter.run_guard(payload, bash=BASH)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
