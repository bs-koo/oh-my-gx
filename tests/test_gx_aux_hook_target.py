"""커밋 보호 훅(G1·G3)의 대상 판정 회귀 — 셸 래퍼·디렉터리 변경·거짓 차단·Python 부재·GIT_DIR 환경."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / '.claude/hooks/pre-tool-guard.sh'
TARGET = REPO / 'scripts/gx-git-target.py'
BASH = shutil.which('bash')
if os.name == 'nt' and Path('C:/Program Files/Git/bin/bash.exe').is_file():
    BASH = 'C:/Program Files/Git/bin/bash.exe'
PENDING = 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n'


@unittest.skipUnless(shutil.which('git') and BASH, 'Git·Bash 필요')
class HookTargetFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='gx 훅 대상 ')
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.env = os.environ.copy()
        for name in ('GIT_DIR', 'GIT_WORK_TREE'):
            self.env.pop(name, None)
        self.env['GIT_CONFIG_GLOBAL'] = str(self.parent / 'global.config')
        (self.parent / 'global.config').write_text('', encoding='utf-8')
        # 저장소가 아닌 워크스페이스 아래에 저장소를 둔다 — gx-commit의 `(cd <git-root> && …)` 실행 위치를 재현한다.
        self.workspace = self.parent / '워크스페이스'
        self.workspace.mkdir()
        self.root = self.repository(self.workspace / '작업', 'feat/a')
        self.protected = self.repository(self.workspace / '보호', 'main')

    def git(self, root, *args):
        return subprocess.run(['git', '-c', f'safe.directory={root.as_posix()}', '-c', 'commit.gpgsign=false', *args],
                              cwd=root, capture_output=True, check=True, encoding='utf-8', env=self.env)

    def repository(self, root, branch):
        root.mkdir(parents=True)
        self.git(root, 'init', '-q', '-b', branch)
        hooks = root / '.git/empty-hooks'
        hooks.mkdir()
        self.git(root, 'config', 'core.hooksPath', str(hooks))
        self.git(root, '-c', 'user.name=GX fixture', '-c', 'user.email=gx@example.invalid',
                 'commit', '-q', '--allow-empty', '-m', 'fixture')
        return root

    def open_gate(self, root, slug):
        state = root / '.dev' / slug / 'state.md'
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(PENDING, encoding='utf-8')

    def guard(self, command, cwd=None):
        cwd = cwd or self.root
        payload = {'cwd': str(cwd), 'tool_name': 'Bash', 'tool_input': {'command': command}}
        proc = subprocess.run([BASH, str(GUARD)], input=json.dumps(payload, ensure_ascii=False), cwd=cwd,
                              capture_output=True, encoding='utf-8', env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if not proc.stdout.strip():
            return 'PASS', ''
        output = json.loads(proc.stdout)['hookSpecificOutput']
        return output['permissionDecision'], output['permissionDecisionReason']

    def decision(self, command, cwd=None):
        return self.guard(command, cwd)[0]

    def targets(self, command, cwd=None):
        payload = {'cwd': str(cwd or self.root), 'tool_input': {'command': command}}
        proc = subprocess.run([sys.executable, str(TARGET)], input=json.dumps(payload, ensure_ascii=False),
                              capture_output=True, encoding='utf-8', env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.splitlines()

    def assertDecisions(self, commands, expected, cwd=None):
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command, cwd), expected)


class WrappedCommitTests(HookTargetFixture):
    def test_wrapped_commit_on_protected_cwd_is_denied(self):
        # 셸 래퍼·치환 안의 커밋을 대상 0개로 보고 통과시키면 보호 브랜치 커밋이 그대로 들어간다(H1).
        self.assertDecisions([
            "bash -c 'git commit -m x'",
            'sh -c "git commit -m x"',
            'eval "git commit -m x"',
            'echo $(git commit -m x)',
            'echo `git commit -m x`',
            'python -c "import os; os.system(\'git commit -m x\')"',
        ], 'deny', cwd=self.protected)

    def test_wrapped_commit_uses_inner_target(self):
        protected = self.protected.as_posix()
        self.assertDecisions([
            f"bash -c 'git -C \"{protected}\" commit -m x'",
            f"echo \"$(git -C '{protected}' commit -m x)\"",
            f"bash -lc 'cd \"{protected}\" && git commit -m x'",
        ], 'deny')

    def test_opaque_interpreter_commit_checks_current_repository(self):
        # 해석할 수 없는 인터프리터 안의 커밋은 현재 저장소로 대신 검사한다(검증 게이트 ask로 확인).
        self.open_gate(self.root, 'feat-a')
        self.assertEqual(self.decision('python -c "import os; os.system(\'git commit -m x\')"'), 'ask')
        command = 'python -c "import subprocess; subprocess.run([\'git\',\'commit\',\'-m\',\'x\'])"'
        self.assertEqual(self.targets(command), ['?' + self.root.as_posix()])


class DirectoryChangeTests(HookTargetFixture):
    def test_changed_directory_commit_targets_that_repository(self):
        protected = self.protected.as_posix()
        self.assertDecisions([
            f'(cd "{protected}" && git commit -m x)',
            f'{{ cd "{protected}"; git commit -m x; }}',
            f'command cd "{protected}" && git commit -m x',
            f'cd "{protected}" && git commit -m x',
        ], 'deny')

    def test_workspace_root_cd_commit_uses_repository_state(self):
        self.open_gate(self.root, 'feat-a')
        self.assertDecisions(['(cd 작업 && git commit -m x)', 'cd 작업 && git commit -m x'], 'ask', cwd=self.workspace)
        self.assertEqual(self.decision('(cd 보호 && git commit -m x)', cwd=self.workspace), 'deny')

    def test_subshell_directory_change_does_not_leak(self):
        root = self.root.as_posix()
        self.assertEqual(self.decision(f'(cd "{root}" && git commit -m x) && git log -1', cwd=self.protected), 'PASS')
        self.assertEqual(self.decision(f'(cd "{root}" && git log -1) && git commit -m x', cwd=self.protected), 'deny')
        self.assertEqual(self.targets(f'(cd "{root}" && git log -1) && git commit -m x', cwd=self.protected),
                         [self.protected.as_posix()])

    def test_dynamic_directory_change_is_denied_with_cd_reason(self):
        for command in ('cd "$TARGET_REPO" && git commit -m x', 'cd "$(pwd)" && git commit -m x'):
            with self.subTest(command=command):
                decision, reason = self.guard(command)
                self.assertEqual(decision, 'deny')
                self.assertIn('cd', reason)
                self.assertNotIn('Python', reason)


class FalseBlockTests(HookTargetFixture):
    COMMITS = [
        "git commit -F - <<'EOF'\nfix: don't break\nEOF",
        "git commit -F - <<'EOF'\n- commit 규칙 정리\nEOF",
        "git commit -m \"$(cat <<'EOF'\nfix: 5\" 모니터 지원\n\nCo-Authored-By: Claude <noreply@anthropic.com>\nEOF\n)\"",
        'rtk proxy git commit -m x',
        'git -P commit -m x',
    ]

    def test_read_commands_mentioning_commit_pass(self):
        # 검증 게이트를 열어 두어 cwd 대신 검사(ask)도 일어나지 않음을 함께 확인한다.
        self.open_gate(self.root, 'feat-a')
        self.assertDecisions([
            'git --no-pager log --oneline | grep commit',
            f'git -C "{self.root.as_posix()}" log -1 && grep -n commit README.md',
            'git -C "$SOME_REPO" log -1 | grep commit',
        ], 'PASS')

    def test_heredoc_and_wrapper_commits_are_judged_on_target(self):
        self.open_gate(self.root, 'feat-a')
        self.assertDecisions(self.COMMITS, 'ask')
        self.assertDecisions(self.COMMITS, 'deny', cwd=self.protected)

    def test_deny_reason_names_the_cause(self):
        cases = (('git -C "$UNKNOWN_TARGET" commit -m x', '동적'),
                 ('git commit -m "unterminated', '따옴표'),
                 ('git --git-dir=.git commit -m x', '--git-dir'))
        for command, cause in cases:
            with self.subTest(command=command):
                decision, reason = self.guard(command)
                self.assertEqual(decision, 'deny')
                self.assertIn(cause, reason)
                self.assertNotIn('Python', reason)


class NoPythonFallbackTests(HookTargetFixture):
    def setUp(self):
        super().setUp()
        # python3·python이 모두 실행에 실패하는 PATH — Python 3.10+가 없는 환경을 재현한다.
        shims = self.parent / 'shims'
        shims.mkdir()
        for name in ('python3', 'python'):
            (shims / name).write_text('#!/bin/sh\nexit 1\n', encoding='utf-8', newline='\n')
            (shims / name).chmod(0o755)
        self.env['PATH'] = str(shims) + os.pathsep + self.env['PATH']

    def test_feature_commit_passes_without_python(self):
        self.assertEqual(self.decision('git commit -m feature-work'), 'PASS')

    def test_verify_gate_still_asks_without_python(self):
        self.open_gate(self.root, 'feat-a')
        self.assertEqual(self.decision('git commit -m feature-work'), 'ask')

    def test_protected_cwd_and_plain_c_path_are_denied_without_python(self):
        decision, reason = self.guard('git commit -m x', cwd=self.protected)
        self.assertEqual(decision, 'deny')
        self.assertIn('main', reason)
        # sed 폴백은 따옴표·공백 없는 `git -C <경로>`만 읽는다(이전 훅과 같은 범위).
        plain = Path(tempfile.mkdtemp(prefix='gxplain')).resolve()
        self.addCleanup(shutil.rmtree, plain, True)
        target = self.repository(plain / 'main', 'main')
        decision, reason = self.guard(f'git -C {target.as_posix()} commit -m x')
        self.assertEqual(decision, 'deny')
        self.assertIn('main', reason)

    def test_non_repository_cwd_passes_without_python(self):
        self.assertEqual(self.decision('cd 작업 && git commit -m x', cwd=self.workspace), 'PASS')


class GitDirEnvironmentTests(HookTargetFixture):
    def test_exported_git_dir_is_not_overwritten_by_hook_loop(self):
        # 훅 루프 변수가 GIT_DIR이면 export된 값을 덮어써 git 호출이 대상 저장소를 잃는다(L9).
        self.env['GIT_DIR'] = (self.root / '.git').as_posix()
        self.assertEqual(self.decision('git commit -m x'), 'PASS')


if __name__ == '__main__':
    unittest.main()
