"""합성 Git fixture로 .dev 조회의 출처·범위·읽기 전용 경계를 검증한다."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_test_support import load


history = load("gx_history", "scripts/gx-history.py")
SCRIPT = Path(history.__file__)


@unittest.skipUnless(shutil.which("git"), "Git 필요")
class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gx history ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "-b", "feature/history")
        self.git("config", "user.name", "기록 기여자")
        self.git("config", "user.email", "not-returned@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.write("README.md", "합성 저장소\n")
        self.commit()

    def git(self, *args, input_bytes=None):
        return subprocess.run(["git", "-C", str(self.root), *args], input=input_bytes,
                              check=True, capture_output=True).stdout

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8", newline="\n")
        return target

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-m", "합성 근거")
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_committed_korean_original_and_dirty_copy_have_separate_provenance(self):
        path = ".dev/feat-공백 작업/decisions.md"
        original = "# 결정\n\n2026-10-01: 경계 정책\n답변: 요청 한도는 10입니다.\n"
        self.write(path, original)
        revision = self.commit()
        self.write(path, original.replace("10", "20"))
        value = history.search(self.root, ["요청 한도"])
        match = value["matches"][0]
        self.assertEqual(value["source"]["revision"], revision)
        self.assertEqual(match["path"], path)
        self.assertIn("한도는 10", match["excerpt"])
        self.assertNotIn("한도는 20", match["excerpt"])
        self.assertTrue(match["working_tree_differs_from_source"])
        self.assertEqual(match["record_contributor"]["name"], "기록 기여자")
        self.assertEqual(match["record_contributor"]["commit"], revision)
        self.assertEqual(match["decision_maker"], "unknown")
        self.assertEqual(match["decision_time"], "unknown")
        self.assertEqual(match["source_sha256"], hashlib.sha256(original.encode()).hexdigest())
        self.assertNotIn("not-returned@", json.dumps(value))

    def test_multiple_decisions_remain_candidates_without_choosing_winner(self):
        self.write(".dev/feat-a/decisions.md", "# 결정\n\n## 18:40\n질문: 재시도 정책\n답변: 자동 허용\n\n\n## 19:15\n질문: 재시도 정책\n답변: 수동 허용\n")
        self.commit()
        matches = history.search(self.root, ["재시도 정책"])["matches"]
        self.assertEqual(len(matches), 2)
        self.assertIn("자동 허용", matches[0]["excerpt"])
        self.assertIn("수동 허용", matches[1]["excerpt"])
        for match in matches:
            self.assertEqual(match["current_validity"], "unknown")
            self.assertEqual(match["conflict"], "unknown")
            self.assertEqual(match["approval"], "unknown")

    def test_prefixed_draft_old_plans_and_arbitrary_task_ids_are_searchable(self):
        paths = [".dev/plan-v1.md", ".dev/plan-v2.md", ".dev/task/design-draft.md",
                 ".dev/task/BRIEF-W112.md", ".dev/task/prefix__decisions.md", ".dev/task/ac.md"]
        for path in paths:
            self.write(path, "W112 AC-10005 연결 근거\n")
        self.commit()
        value = history.search(self.root, ["W112", "AC-10005"], limit=20)
        self.assertEqual({match["path"] for match in value["matches"]}, set(paths))
        self.assertTrue(all(match["current_validity"] == "unknown" for match in value["matches"]))
        path_value = history.search(self.root, ["BRIEF-W112"])
        self.assertEqual(path_value["matches"][0]["match_type"], "path")

    def test_logs_backups_reports_and_untracked_docs_are_excluded(self):
        excluded = [".dev/task/reports/design.md", ".dev/logs/decisions.md", ".dev/evidence/prd.md",
                    ".dev/visuals/design.md", ".dev/architecture/design.md", ".dev/backup/plan.md",
                    ".dev/salvage-old/prefix__decisions.md", ".dev/task/design-backup.md"]
        for path in excluded:
            self.write(path, "excluded-token\n")
        self.write(".dev/task/decisions.md", "searched-token\n")
        self.commit()
        self.write(".dev/task/prd.md", "excluded-token\n")
        value = history.search(self.root, ["excluded-token"])
        self.assertEqual(value["matches"], [])
        self.assertEqual(value["scope"]["eligible_files"], 1)
        self.assertIn("no matches does not establish", value["limitations"][0])

    def test_file_result_and_excerpt_limits_are_explicit(self):
        for index in range(4):
            self.write(f".dev/task{index}/decisions.md", "x" * 3000 + "needle" + "z" * 3000 + "\nneedle\n")
        self.commit()
        value = history.search(self.root, ["needle"], limit=1, max_files=2)
        self.assertEqual(len(value["matches"]), 1)
        self.assertEqual(value["scope"]["skipped"]["file_limit"], 2)
        self.assertEqual(value["scope"]["matched_lines"], 4)
        self.assertTrue(value["scope"]["truncated"])
        self.assertTrue(value["matches"][0]["excerpt_clipped"])
        self.assertIn("needle", value["matches"][0]["excerpt"])
        self.assertLessEqual(len(value["matches"][0]["excerpt"]), history.EXCERPT_CHARS)

    def test_one_repetitive_document_does_not_hide_another_work_item(self):
        self.write(".dev/task-a/decisions.md", "정책\n" * 40)
        self.write(".dev/task-b/decisions.md", "정책: 별도 작업의 결정\n")
        self.commit()
        value = history.search(self.root, ["정책"], limit=2)
        self.assertEqual({match["path"] for match in value["matches"]},
                         {".dev/task-a/decisions.md", ".dev/task-b/decisions.md"})

    def test_large_binary_non_utf8_and_symlink_blobs_are_skipped(self):
        self.write(".dev/a/design.md", "needle" * 100)
        self.write(".dev/b/design.md", b"needle\0binary")
        self.write(".dev/c/design.md", b"needle\xff")
        self.commit()
        outside_blob = self.git("hash-object", "-w", "--stdin", input_bytes=b"../outside-secret").decode().strip()
        self.git("update-index", "--add", "--cacheinfo", f"120000,{outside_blob},.dev/link/decisions.md")
        self.git("commit", "-m", "합성 symlink 기록")
        # 작업본에 symlink가 없어도 커밋된 mode를 기준으로 제외한다.
        value = history.search(self.root, ["needle"], max_bytes=50)
        self.assertEqual(value["matches"], [])
        self.assertEqual(value["scope"]["skipped"]["oversize"], 1)
        self.assertEqual(value["scope"]["skipped"]["binary_or_non_utf8"], 2)
        self.assertEqual(value["scope"]["skipped"]["non_regular"], 1)

    def test_total_byte_budget_is_explicit(self):
        for index in range(3):
            self.write(f".dev/task{index}/design.md", "needle" * 10)
        self.commit()
        with patch.object(history, "TOTAL_BYTES", 120):
            value = history.search(self.root, ["needle"])
        self.assertEqual(value["scope"]["read_bytes"], 120)
        self.assertEqual(value["scope"]["skipped"]["byte_budget"], 1)

    def test_many_files_are_read_in_one_batch_and_only_returned_lines_are_blamed(self):
        for index in range(40):
            self.write(f".dev/task{index}/design.md", "검색할 정책 근거\n")
        self.commit()
        with patch.object(history, "git", wraps=history.git) as invoke:
            value = history.search(self.root, ["정책"], limit=2)
        self.assertEqual(value["scope"]["scanned_files"], 40)
        commands = [call.args[1] for call in invoke.call_args_list]
        self.assertEqual(commands.count("cat-file"), 1)
        self.assertEqual(commands.count("blame"), 2)
        self.assertEqual(len(commands), 6)

    def test_git_line_numbers_use_lf_only_and_normalize_crlf(self):
        for index, separator in enumerate(("\u2028", "\u0085", "\r", "\r\n")):
            self.write(f".dev/task{index}/decisions.md", f"첫 줄{separator}중간 내용\n둘째 줄 근거\n")
        revision = self.commit()
        value = history.search(self.root, ["둘째 줄 근거"], limit=20)
        self.assertEqual(len(value["matches"]), 4)
        for match in value["matches"]:
            expected = 3 if "task3" in match["path"] else 2
            self.assertEqual(match["line"], expected)
            self.assertEqual(match["record_contributor"]["commit"], revision)

    def test_assume_unchanged_and_skip_worktree_cannot_hide_dirty_bytes(self):
        path = ".dev/task/decisions.md"
        self.write(path, "정책: A\n")
        self.commit()
        for flag, inverse in (("--assume-unchanged", "--no-assume-unchanged"),
                              ("--skip-worktree", "--no-skip-worktree")):
            with self.subTest(flag=flag):
                self.git("update-index", flag, path)
                self.write(path, "정책: B\n")
                value = history.search(self.root, ["정책"])
                self.assertTrue(value["matches"][0]["working_tree_differs_from_source"])
                self.assertIn("정책: A", value["matches"][0]["excerpt"])
                self.assertEqual(value["matches"][0]["working_tree_comparison"]["status"], "compared_bytes")
                self.git("update-index", inverse, path)
                self.write(path, "정책: A\n")

    def test_query_never_executes_working_tree_clean_filters(self):
        self.write(".dev/task/decisions.md", "정책: A\n")
        self.commit()
        marker = self.root / "filter-was-run"
        script = self.write("probe-filter.py", "import pathlib, sys\n"
                            f"pathlib.Path({str(marker)!r}).write_text('ran')\n"
                            "sys.stdout.buffer.write(sys.stdin.buffer.read())\n")
        self.git("config", "filter.gx-history-probe.clean",
                 f'"{Path(sys.executable).as_posix()}" "{script.as_posix()}"')
        self.write(".gitattributes", "*.md filter=gx-history-probe\n")
        self.write(".dev/task/decisions.md", "정책: B\n")
        value = history.search(self.root, ["정책"])
        self.assertEqual(value["status"], "ok")
        self.assertTrue(value["matches"][0]["working_tree_differs_from_source"])
        self.assertFalse(marker.exists())

    def test_missing_and_oversized_working_files_are_not_read(self):
        path = ".dev/task/decisions.md"
        target = self.write(path, "정책\n")
        self.commit()
        target.unlink()
        value = history.search(self.root, ["정책"])
        self.assertTrue(value["matches"][0]["working_tree_differs_from_source"])
        self.assertEqual(value["matches"][0]["working_tree_comparison"]["status"], "missing")
        target.write_bytes(b"x" * 100)
        with patch.object(history.os, "open", side_effect=AssertionError("크기가 다르면 읽지 않아야 합니다")):
            differs, observation = history.working_comparison(self.root, path, "unused", 7, 10)
        self.assertTrue(differs)
        self.assertEqual(observation["status"], "size_differs")

    def test_reparse_and_unreadable_working_paths_are_unknown_without_following(self):
        reparse = SimpleNamespace(st_mode=0o040755, st_file_attributes=0x400)
        with patch.object(Path, "lstat", return_value=reparse), patch.object(history.os, "open") as opened:
            differs, observation = history.working_comparison(self.root, ".dev/task/design.md", "unused", 1, 10)
        self.assertIsNone(differs)
        self.assertEqual(observation["reason"], "symlink_or_reparse_point")
        opened.assert_not_called()
        with patch.object(Path, "lstat", side_effect=PermissionError()):
            differs, observation = history.working_comparison(self.root, ".dev/task/design.md", "unused", 1, 10)
        self.assertIsNone(differs)
        self.assertEqual(observation["reason"], "unreadable_working_path")
        differs, observation = history.working_comparison(self.root, "../outside.md", "unused", 1, 10)
        self.assertIsNone(differs)
        self.assertEqual(observation["reason"], "outside_project_path")

    def test_concurrent_working_file_change_is_unknown(self):
        path = ".dev/task/decisions.md"
        target = self.write(path, "정책\n")
        observed = target.stat()
        changed = SimpleNamespace(st_mode=observed.st_mode, st_dev=observed.st_dev,
                                  st_ino=observed.st_ino, st_size=observed.st_size,
                                  st_mtime_ns=observed.st_mtime_ns + 1)
        with patch.object(history.os, "fstat", return_value=changed):
            differs, observation = history.working_comparison(self.root, path, "unused", observed.st_size, 100)
        self.assertIsNone(differs)
        self.assertEqual(observation["reason"], "changed_during_comparison")

    def test_untrusted_path_and_contributor_metadata_cannot_expand_output_unboundedly(self):
        blob = self.git("hash-object", "-w", "--stdin", input_bytes="근거\n".encode()).strip()
        long_name = ("x" * (history.PATH_CHARS + 1) + "__decisions.md").encode()
        dev_tree = self.git("mktree", "-z", input_bytes=b"100644 blob " + blob + b"\t" + long_name + b"\0").strip()
        tree = self.git("mktree", "-z", input_bytes=b"040000 tree " + dev_tree + b"\t.dev\0").strip()
        revision = self.git("commit-tree", tree.decode(), "-m", "합성 긴 경로").decode().strip()
        value = history.search(self.root, ["근거"], ref=revision)
        self.assertEqual(value["scope"]["skipped"]["unsupported_path"], 1)
        self.assertLess(len(json.dumps(value)), 5000)
        self.git("config", "user.name", "기여자" * 200)
        self.write(".dev/task/decisions.md", "근거\n")
        self.commit()
        value = history.search(self.root, ["근거"])
        self.assertEqual(len(value["matches"][0]["record_contributor"]["name"]), 256)
        self.assertTrue(value["matches"][0]["record_contributor"]["name_clipped"])

    def test_no_lazy_fetch_applies_to_every_git_read_and_missing_objects_are_errors(self):
        self.write(".dev/task/decisions.md", "근거\n")
        self.commit()
        with patch.object(history.subprocess, "run", wraps=subprocess.run) as invoke:
            value = history.search(self.root, ["근거"])
        self.assertEqual(value["status"], "ok")
        for call in invoke.call_args_list:
            self.assertEqual(call.args[0][0], "git")
            self.assertIn("--no-lazy-fetch", call.args[0])
            self.assertFalse(call.kwargs["shell"])
        # 존재하지 않는 원문 blob을 가리키는 합성 commit: 빈 검색 결과로 숨기지 않는다.
        dev_tree = self.git("mktree", "--missing", "-z",
                            input_bytes=b"100644 blob " + b"f" * 40 + b"\tdecisions.md\0").strip()
        tree = self.git("mktree", "-z", input_bytes=b"040000 tree " + dev_tree + b"\t.dev\0").strip()
        revision = self.git("commit-tree", tree.decode(), "-m", "합성 누락 원문").decode().strip()
        with self.assertRaises(history.HistoryError):
            history.search(self.root, ["근거"], ref=revision)

    def test_historical_ref_is_pinned_without_dirty_content_attribution(self):
        path = ".dev/task/decisions.md"
        self.write(path, "정책: 수동\n")
        old = self.commit()
        self.write(path, "정책: 자동\n")
        current = self.commit()
        value = history.search(self.root, ["정책"], ref=old)
        self.assertEqual(value["source"]["revision"], old)
        self.assertEqual(value["matches"][0]["record_contributor"]["commit"], old)
        self.assertTrue(value["matches"][0]["working_tree_differs_from_source"])
        self.assertIn("수동", value["matches"][0]["excerpt"])
        self.assertEqual(self.git("rev-parse", "HEAD").decode().strip(), current)

    def test_search_preserves_head_index_staged_and_unstaged_files(self):
        path = ".dev/task/decisions.md"
        self.write(path, "정책: 수동\n")
        self.commit()
        self.write(path, "정책: 자동\n")
        self.git("add", path)
        self.write(path, "정책: 확인 중\n")
        self.write(".dev/task/untracked.md", "추적하지 않는 파일")
        def snapshot():
            return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        before = snapshot()
        history.search(self.root, ["정책"])
        self.assertEqual(snapshot(), before)

    def test_invalid_repository_missing_git_and_invalid_ref_are_errors(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(history.HistoryError):
                history.search(other, ["정책"])
            (Path(other) / ".svn").mkdir()
            with self.assertRaisesRegex(history.HistoryError, "SVN"):
                history.search(other, ["정책"])
        for ref in ("does-not-exist", "--help", "HEAD\n--help", "HEAD; touch forbidden"):
            with self.subTest(ref=ref), self.assertRaises(history.HistoryError):
                history.search(self.root, ["정책"], ref=ref)
        with patch.object(history.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaises(history.HistoryError):
                history.search(self.root, ["정책"])
        with self.assertRaises(history.HistoryError):
            history.search(self.root / ".git", ["정책"])

    def test_input_and_output_limits_cannot_be_disabled(self):
        for args in (([], {}), ([" "], {}), (["x" * 257], {}), (["x"] * 13, {}),
                     (["x"], {"limit": 21}), (["x"], {"max_files": 0}), (["x"], {"max_bytes": 1048577})):
            with self.subTest(args=args), self.assertRaises(history.HistoryError):
                history.search(self.root, args[0], **args[1])

    def test_cli_utf8_success_and_machine_readable_lookup_failure(self):
        self.write(".dev/task/decisions.md", "한국어 근거\n")
        self.commit()
        args = [sys.executable, str(SCRIPT), "search", "--project-root", str(self.root), "--term", "한국어"]
        result = subprocess.run(args, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout.decode("utf-8"))["matches"][0]["excerpt"], "한국어 근거")
        error = subprocess.run(args + ["--ref", "missing"], capture_output=True)
        self.assertEqual(error.returncode, 2)
        self.assertEqual(json.loads(error.stdout.decode("utf-8"))["status"], "error")
        self.assertIsNone(json.loads(error.stdout.decode("utf-8"))["matches"])


if __name__ == "__main__":
    unittest.main()
