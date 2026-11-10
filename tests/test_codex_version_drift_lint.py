"""정합성 린트 [1/36]의 버전 태그 드리프트 검사 회귀 (gx-work 전수조사 F05).

v3.0.0 태그 뒤 #102가 버전 표기 없이 main에 들어가 설치본과 main이 갈렸다.
최근 버전 태그 이후 배포 경로가 바뀌었는데 버전이 태그와 같으면 린트가 실패해야 한다.
린트 전체(약 4분)를 돌리지 않고 [1/36] 구간만 떼어 임시 저장소에서 실행한다.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "scripts" / "lint-consistency.sh"
# 릴리스 태그 접두사는 린트가 정본이다. 모노레포 이관본은 '<플러그인>--v'를 쓴다.
TAG_PREFIX = re.search(r"(?m)^RELEASE_TAG_PREFIX='([^']+)'$", LINT.read_text(encoding="utf-8")).group(1)
TAG = TAG_PREFIX + "1.0.0"
PRELUDE = 'set -uo pipefail\nFAIL=0\nfail() { echo "  FAIL: $1"; FAIL=1; }\nok() { echo "  ok: $1"; }\n'


def find_bash():
    # Windows의 PATH bash는 WSL 셰임일 수 있어 Git Bash를 우선한다(codex_hook.py와 같은 이유).
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432")):
            if base:
                candidate = Path(base) / "Git" / "bin" / "bash.exe"
                if candidate.exists():
                    return str(candidate)
    return shutil.which("bash")


def lint_section(number, lint_path=LINT):
    text = Path(lint_path).read_text(encoding="utf-8")
    start = text.index(f'echo "[{number}/')
    end = text.index(f'echo "[{number + 1}/', start)
    return text[start:end]


class VersionDriftLintTest(unittest.TestCase):
    lint_path = LINT

    def setUp(self):
        self.bash = find_bash()
        if not self.bash:
            self.skipTest("bash를 찾지 못했다")
        self.repo = Path(tempfile.mkdtemp(prefix="gx-drift-"))
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "test")
        self.git("config", "core.autocrlf", "false")
        self.set_version("1.0.0")
        self.write(".claude/skills/gx-sample/SKILL.md", "v1\n")
        self.write("docs/guide.md", "v1\n")
        self.write("scripts/lint-consistency.sh", "# v1\n")
        self.commit("init")
        self.git("tag", TAG)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def set_version(self, version):
        manifest = json.dumps({"name": "sample", "version": version}, indent=2) + "\n"
        market = json.dumps({"plugins": [{"name": "sample", "version": version}]}, indent=2) + "\n"
        self.write(".claude-plugin/plugin.json", manifest)
        self.write(".claude-plugin/marketplace.json", market)
        self.write(".codex-plugin/plugin.json", manifest)
        self.write("CHANGELOG.md", f"# Changelog\n\n## v{version} (2026-11-09) — sample\n")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run_section(self):
        script = PRELUDE + lint_section(1, self.lint_path) + "exit $FAIL\n"
        proc = subprocess.run([self.bash, "-c", script], cwd=self.repo, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout

    def test_skill_change_without_version_bump_fails(self):
        self.write(".claude/skills/gx-sample/SKILL.md", "v2\n")
        self.commit("skill change")
        code, out = self.run_section()
        self.assertEqual(code, 1, out)
        self.assertIn(f"{TAG} 이후 배포 경로가 바뀌었는데", out)
        self.assertIn(".claude/skills/gx-sample/SKILL.md", out)

    def test_uncommitted_skill_change_is_also_detected(self):
        self.write(".claude/skills/gx-sample/SKILL.md", "v2\n")
        code, out = self.run_section()
        self.assertEqual(code, 1, out)

    def test_bumped_version_passes(self):
        self.write(".claude/skills/gx-sample/SKILL.md", "v2\n")
        self.set_version("1.1.0")
        self.commit("skill change with bump")
        code, out = self.run_section()
        self.assertEqual(code, 0, out)
        self.assertIn(f"최근 태그 {TAG} 이후의 새 버전", out)

    def test_docs_only_change_passes(self):
        self.write("docs/guide.md", "v2\n")
        self.commit("docs only")
        code, out = self.run_section()
        self.assertEqual(code, 0, out)
        self.assertIn("배포 경로 변경 없음", out)

    def test_lint_only_change_passes(self):
        self.write("scripts/lint-consistency.sh", "# v2\n")
        self.commit("lint only")
        code, out = self.run_section()
        self.assertEqual(code, 0, out)

    def test_version_lower_than_tag_fails(self):
        self.write(".claude/skills/gx-sample/SKILL.md", "v2\n")
        self.set_version("0.9.0")
        self.commit("version rolled back")
        code, out = self.run_section()
        self.assertEqual(code, 1, out)
        self.assertIn("낮", out)

    def test_manifest_change_without_bump_fails(self):
        # 훅 배선 같은 매니페스트 변경도 설치본 동작을 바꾼다.
        manifest = json.dumps({"name": "sample", "version": "1.0.0", "hooks": {"PreToolUse": []}}, indent=2) + "\n"
        self.write(".claude-plugin/plugin.json", manifest)
        self.commit("manifest hooks")
        code, out = self.run_section()
        self.assertEqual(code, 1, out)
        self.assertIn(".claude-plugin/plugin.json", out)

    def test_eval_and_dev_only_script_changes_pass(self):
        self.write(".claude/skills/gx-sample/evals/evals.json", "{}\n")
        self.write("scripts/codex-probe-hook.sh", "# probe\n")
        self.commit("evals and probe only")
        code, out = self.run_section()
        self.assertEqual(code, 0, out)

    def test_line_ending_warnings_are_not_reported_as_changes(self):
        # 릴리스 직후 줄끝만 다시 쓰인 파일이 있으면 git이 stderr에 autocrlf 경고를 낸다. 변경 목록으로 세지 않는다.
        self.git("config", "core.autocrlf", "true")
        self.git("config", "core.safecrlf", "warn")
        self.write(".claude/skills/gx-sample/SKILL.md", "v1\n")
        code, out = self.run_section()
        self.assertEqual(code, 0, out)
        self.assertNotIn("warning:", out)

    def test_missing_tag_skips_with_notice(self):
        self.git("tag", "-d", TAG)
        self.write(".claude/skills/gx-sample/SKILL.md", "v2\n")
        self.commit("skill change without tags")
        code, out = self.run_section()
        self.assertEqual(code, 0, out)
        self.assertIn("건너뜀", out)


if __name__ == "__main__":
    unittest.main()
