"""Decision capture across Claude and Codex response shapes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from codex_test_support import load


capture = load("gx_capture", ".claude/hooks/capture_decision.py")


class DecisionTests(unittest.TestCase):
    def test_codex_question_is_not_replaced_by_id(self):
        payload = {
            "tool_input": {"questions": [{
                "id": "q1",
                "header": "방식",
                "question": "어떤 방식을 사용할까요?",
                "options": [
                    {"label": "A", "description": "첫 방법"},
                    {"label": "B", "description": "둘째 방법"},
                ],
            }]},
            "tool_response": {"answers": {"q1": {"answers": ["B"]}}},
        }

        text = capture.render(payload)

        self.assertIn("어떤 방식을 사용할까요?", text)
        self.assertIn("**ID.** q1", text)
        self.assertIn("둘째 방법", text)
        self.assertIn("**→** B", text)
        self.assertNotIn("{'answers':", text)

    def test_claude_question_key_keeps_choice_and_note(self):
        question = "배포할까요?"
        payload = {
            "tool_input": {"questions": [{
                "question": question,
                "header": "배포",
                "options": [
                    {"label": "예", "description": "지금 배포"},
                    {"label": "아니요", "description": "보류"},
                ],
            }]},
            "tool_response": {
                "answers": {question: "아니요"},
                "annotations": {question: {"notes": "검증 대기"}},
            },
        }

        text = capture.render(payload)

        self.assertIn("**Q.** 배포할까요?", text)
        self.assertNotIn("**ID.**", text)
        self.assertIn("**→** 아니요 — 보류", text)
        self.assertIn("- 예 — 지금 배포", text)
        self.assertIn("**A.** 아니요", text)
        self.assertIn("메모: 검증 대기", text)

    def test_multiple_choices_mark_only_unlisted_values_as_direct_input(self):
        payload = {
            "tool_input": {"questions": [{
                "id": "choices",
                "question": "어떤 항목을 고를까요?",
                "options": [
                    {"label": "A", "description": "기본"},
                    {"label": "B", "description": "추가"},
                ],
            }]},
            "tool_response": {
                "answers": {"choices": {"answers": ["A", "직접 제안"]}},
            },
        }

        text = capture.render(payload)

        self.assertIn("**→** A — 기본", text)
        self.assertIn("- B — 추가", text)
        self.assertIn("**→** (직접 입력) 직접 제안", text)
        self.assertNotIn("(직접 입력) A", text)
        self.assertIn("**A.** A, 직접 제안", text)

    def test_unanswered_codex_question_has_no_record(self):
        payload = {
            "tool_input": {"questions": [{"id": "q1", "question": "진행할까요?"}]},
            "tool_response": {"answers": {"q1": {"answers": []}}},
        }

        self.assertEqual(capture.answer_rows(payload), [])
        self.assertEqual(capture.render(payload), "")

    def test_blank_answers_do_not_create_a_decision_file(self):
        script = Path(capture.__file__).with_name("codex_hook.py")
        for tool_name, key, answer in (
            ("AskUserQuestion", "진행할까요?", ""),
            ("AskUserQuestion", "진행할까요?", " \t "),
            ("request_user_input", "q1", {"answers": [""]}),
            ("request_user_input", "q1", {"answers": [" \t "]}),
        ):
            with self.subTest(tool_name=tool_name, answer=answer):
                with tempfile.TemporaryDirectory() as workspace:
                    payload = {
                        "tool_name": tool_name,
                        "cwd": workspace,
                        "tool_input": {"questions": [{
                            "id": "q1",
                            "question": "진행할까요?",
                            "options": [{"label": "예", "description": "진행"}],
                        }]},
                        "tool_response": {"answers": {key: answer}},
                    }

                    self.assertEqual(capture.answer_rows(payload), [])
                    self.assertEqual(capture.render(payload), "")
                    result = subprocess.run(
                        [sys.executable, str(script), "capture"],
                        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                        capture_output=True,
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse((Path(workspace) / ".dev").exists())

    def test_mixed_codex_answers_drop_blank_values_without_trimming_valid_text(self):
        payload = {
            "tool_input": {"questions": [{"id": "q1", "question": "응답?"}]},
            "tool_response": {"answers": {
                "q1": {"answers": ["  검증 실행  ", " \t ", "추가 확인"]},
            }},
        }

        self.assertEqual(
            capture.answer_rows(payload),
            [("응답?", {"id": "q1", "question": "응답?"},
              ["  검증 실행  ", "추가 확인"], None)],
        )
        self.assertIn("**A.**   검증 실행  , 추가 확인", capture.render(payload))

    def test_capture_cli_appends_utf8_answers_in_payload_cwd(self):
        script = Path(capture.__file__).with_name("codex_hook.py")
        with tempfile.TemporaryDirectory() as workspace:
            path = Path(workspace) / ".dev" / "no-branch" / "decisions.md"
            for tool_name, key, value in (
                ("request_user_input", "verify_action", {"answers": ["검증 실행"]}),
                ("AskUserQuestion", "확인할까요?", "예"),
            ):
                payload = {
                    "tool_name": tool_name,
                    "cwd": workspace,
                    "tool_input": {"questions": [{
                        "id": "verify_action",
                        "question": "확인할까요?",
                        "header": "검증",
                    }]},
                    "tool_response": {"answers": {key: value}},
                }
                result = subprocess.run(
                    [sys.executable, str(script), "capture"],
                    input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            record = path.read_text(encoding="utf-8")
            self.assertEqual(record.count("# 의사결정 기록"), 1)
            self.assertEqual(record.count("**Q.** 확인할까요?"), 2)
            self.assertIn("**A.** 검증 실행", record)
            self.assertIn("**A.** 예", record)
            self.assertNotIn("**Q.** verify_action", record)

    def test_dubious_ownership_retries_with_exact_repository_scoped_trust(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace).resolve()
            (root / ".git").mkdir()
            nested = root / "nested"
            nested.mkdir()
            denied = subprocess.CompletedProcess(
                args=["git", "branch", "--show-current"],
                returncode=128,
                stdout="",
                stderr=f"fatal: detected dubious ownership in repository at '{root}'\n",
            )
            allowed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="feature/q1\n", stderr="",
            )

            with mock.patch.object(capture.subprocess, "run", side_effect=[denied, allowed]) as run:
                self.assertEqual(capture.branch_slug(str(nested)), "feature-q1")

            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0], ["git", "branch", "--show-current"])
            self.assertEqual(
                run.call_args_list[1].args[0],
                ["git", "-c", f"safe.directory={root.as_posix()}", "branch", "--show-current"],
            )
            for call in run.call_args_list:
                self.assertEqual(call.kwargs["cwd"], str(nested))
                self.assertEqual(call.kwargs["timeout"], 5)

    def test_unrelated_git_failure_keeps_no_branch_without_retry(self):
        failed = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: not a git repository",
        )
        with mock.patch.object(capture.subprocess, "run", return_value=failed) as run:
            self.assertEqual(capture.branch_slug("unused"), "no-branch")
        run.assert_called_once()

    def test_dubious_ownership_without_repository_metadata_does_not_trust_path(self):
        failed = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: detected dubious ownership in repository",
        )
        with tempfile.TemporaryDirectory() as workspace:
            with mock.patch.object(capture.subprocess, "run", return_value=failed) as run:
                self.assertEqual(capture.branch_slug(workspace), "no-branch")
        run.assert_called_once()

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_capture_cli_handles_dubious_ownership_without_global_config_write(self):
        script = Path(capture.__file__).with_name("codex_hook.py")
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "symbolic-ref", "HEAD", "refs/heads/feature/q1"],
                cwd=root, check=True,
            )
            global_config = root / "global.gitconfig"
            global_config.write_text("[user]\n\tname = Capture Test\n", encoding="utf-8")
            payload = {
                "tool_name": "request_user_input",
                "cwd": str(root),
                "tool_input": {"questions": [{
                    "id": "q1", "question": "어떤 방식을 사용할까요?",
                    "options": [{"label": "B", "description": "둘째 방법"}],
                }]},
                "tool_response": {"answers": {"q1": {"answers": ["B"]}}},
            }

            result = subprocess.run(
                [sys.executable, str(script), "capture"],
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                capture_output=True,
                env={**os.environ,
                     "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
                     "GIT_CONFIG_GLOBAL": str(global_config)},
                timeout=15,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = root / ".dev" / "feature-q1" / "decisions.md"
            self.assertTrue(record.is_file())
            self.assertIn("**ID.** q1", record.read_text(encoding="utf-8"))
            self.assertFalse((root / ".dev" / "no-branch").exists())
            self.assertEqual(
                global_config.read_text(encoding="utf-8"),
                "[user]\n\tname = Capture Test\n",
            )

    def test_storage_failure_warns_without_blocking_tool(self):
        script = Path(capture.__file__).with_name("codex_hook.py")
        with tempfile.TemporaryDirectory() as workspace:
            non_directory = Path(workspace) / "occupied"
            non_directory.write_text("file", encoding="utf-8")
            payload = {
                "tool_name": "request_user_input",
                "cwd": str(non_directory),
                "tool_input": {"questions": [{"id": "q", "question": "진행할까요?"}]},
                "tool_response": {"answers": {"q": {"answers": ["예"]}}},
            }
            result = subprocess.run(
                [sys.executable, str(script), "capture"],
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                capture_output=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("저장 실패".encode("utf-8"), result.stderr)


if __name__ == "__main__":
    unittest.main()
