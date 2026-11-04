"""gx-lens 근거는 실제 프로젝트 파일·라인·버전으로 재확인할 수 있어야 한다."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".claude/skills/gx-lens/scripts/check_evidence.py"


class LensEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "현재 프로젝트"
        self.root.mkdir()
        self.source = self.root / "src/한도.py"
        self.source.parent.mkdir()
        self.source.write_bytes("LIMIT = 100\r\ndef 허용(amount):\r\n    return amount <= LIMIT\r\n".encode("utf-8"))

    def run_check(self, path="src/한도.py", start=2, end=3, expected=None, helper=HELPER, cwd=None):
        self.assertTrue(helper.is_file(), "프로젝트 근거를 검증할 읽기 전용 helper가 없다")
        command = [sys.executable, str(helper), "--project-root", str(self.root),
                   "--path", path, "--start", str(start), "--end", str(end)]
        if expected is not None:
            command += ["--expected-sha256", expected]
        result = subprocess.run(command, cwd=cwd, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_valid_utf8_crlf_evidence_is_relative_without_source_dump_or_writes(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        code, record = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(record["status"], "valid")
        self.assertEqual(record["path"], "src/한도.py")
        self.assertEqual(record["locator"], "src/한도.py:2-3")
        self.assertEqual(record["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertNotIn("return amount", json.dumps(record))
        self.assertNotIn(str(self.root), json.dumps(record))
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_reused_evidence_reports_changed_even_when_file_size_is_unchanged(self):
        code, old = self.run_check()
        self.assertEqual(code, 0)
        self.source.write_bytes(self.source.read_bytes().replace(b"100", b"200"))
        code, record = self.run_check(expected=old["sha256"])
        self.assertEqual(code, 1)
        self.assertEqual(record["status"], "changed")
        self.assertNotEqual(record["sha256"], old["sha256"])

    def test_unchanged_evidence_keeps_the_digest(self):
        _, old = self.run_check()
        code, record = self.run_check(expected=old["sha256"])
        self.assertEqual(code, 0)
        self.assertEqual(record["sha256"], old["sha256"])

    def test_missing_path_and_invalid_line_ranges_are_rejected(self):
        for path, start, end, reason in (
            ("src/missing.py", 1, 1, "unreadable"),
            ("src/한도.py", 0, 1, "invalid_lines"),
            ("src/한도.py", 3, 2, "invalid_lines"),
            ("src/한도.py", 3, 4, "invalid_lines"),
        ):
            with self.subTest(path=path, start=start, end=end):
                code, record = self.run_check(path, start, end)
                self.assertEqual(code, 2)
                self.assertEqual(record["reason"], reason)

    def test_paths_outside_the_project_are_rejected_on_both_harness_platforms(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("secret = 1\n", encoding="utf-8")
        for path in ("../outside.py", str(outside), "C:\\outside.py", "C:outside.py", "\\\\server\\share\\outside.py"):
            with self.subTest(path=path):
                code, record = self.run_check(path, 1, 1)
                self.assertEqual(code, 2)
                self.assertEqual(record["reason"], "outside_scope")
                self.assertNotIn("secret", json.dumps(record))

    def test_generated_vendor_and_worktree_evidence_is_excluded(self):
        for directory in ("node_modules", "build", "dist", "target", ".git", ".svn", "worktrees", ".venv", "coverage"):
            with self.subTest(directory=directory):
                candidate = self.root / directory / "policy.py"
                candidate.parent.mkdir()
                candidate.write_text("LIMIT = 999\n", encoding="utf-8")
                code, record = self.run_check(candidate.relative_to(self.root).as_posix(), 1, 1)
                self.assertEqual(code, 2)
                self.assertEqual(record["reason"], "excluded_path")

    def test_symlink_evidence_is_excluded_even_when_destination_is_in_project(self):
        alias = self.root / "alias.py"
        try:
            alias.symlink_to(self.source)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"이 실행 환경은 symlink 생성 불가: {error}")
        code, record = self.run_check("alias.py", 1, 1)
        self.assertEqual(code, 2)
        self.assertEqual(record["reason"], "linked_path")

    def test_directory_symlink_cannot_escape_project_or_hide_excluded_path(self):
        outside = self.root.parent / "다른 프로젝트"
        outside.mkdir()
        (outside / "policy.py").write_text("LIMIT = 1\n", encoding="utf-8")
        alias = self.root / "shared"
        try:
            alias.symlink_to(outside, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"이 실행 환경은 symlink 생성 불가: {error}")
        code, record = self.run_check("shared/policy.py", 1, 1)
        self.assertEqual(code, 2)
        self.assertEqual(record["reason"], "linked_path")

    def test_binary_large_file_and_unbounded_excerpt_are_rejected(self):
        for name, data, end, reason in (
            ("binary.py", b"\x00\xff\x00", 1, "not_utf8_text"),
            ("huge.py", b"x" * (2 * 1024 * 1024 + 1), 1, "file_too_large"),
            ("long.py", b"x\n" * 100, 81, "invalid_lines"),
        ):
            with self.subTest(name=name):
                (self.root / name).write_bytes(data)
                code, record = self.run_check(name, 1, end)
                self.assertEqual(code, 2)
                self.assertEqual(record["reason"], reason)

    def test_installed_helper_works_from_unrelated_cwd_with_no_repository_import(self):
        self.assertTrue(HELPER.is_file(), "배포 helper가 없다")
        installed = self.root.parent / "설치 캐시/skills/gx-lens/scripts/check_evidence.py"
        installed.parent.mkdir(parents=True)
        shutil.copyfile(HELPER, installed)
        code, record = self.run_check(helper=installed, cwd=self.root.parent)
        self.assertEqual(code, 0)
        self.assertEqual(record["locator"], "src/한도.py:2-3")


if __name__ == "__main__":
    unittest.main()
