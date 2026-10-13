"""질문 등록/답변/재개의 실패 및 기록 복구 계약."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from codex_test_support import load


gate = load("gx_question_gate", "scripts/codex-question.py")


def question(identifier="implementation_path"):
    return {"id": identifier, "header": "구현 방식", "question": "어떤 방식을 사용할까요?",
            "options": [{"label": "기본 구현", "description": "현재 세션에서 진행"},
                        {"label": "독립 구현", "description": "구현 에이전트에 위임"}]}


class QuestionGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / ".dev" / "test"
        self.registration = {"phase": "design", "questions": [question()]}
        self.response = {"answers": {"implementation_path": {"answers": ["독립 구현"]}}}

    def run_gate(self, command, value=None):
        return gate.run(command, self.root, ".dev/test", value)

    def register(self):
        pending = self.run_gate("register", self.registration)[0]
        self.response["question_set_id"] = pending["question_set_id"]
        return pending

    def test_register_preserves_phase_visible_questions_and_both_payloads(self):
        value = self.register()
        self.assertEqual(value["phase"], "design")
        self.assertIn("어떤 방식을", value["visible_question"])
        self.assertIn("구현 에이전트에 위임", value["visible_question"])
        self.assertEqual(value["sync_payload"], {"questions": [question()]})
        self.assertEqual(value["async_payload"], {"questions": [
            {"title": question()["question"], "options": ["기본 구현", "독립 구현"]}]})
        pending, code = self.run_gate("status")
        self.assertEqual(code, 2)
        self.assertEqual(pending["question_set_id"], value["question_set_id"])
        self.assertEqual(self.register()["question_set_id"], value["question_set_id"])

    def test_unresolved_question_cannot_be_overwritten(self):
        self.register()
        before = (self.directory / gate.PENDING).read_bytes()
        with self.assertRaises(ValueError):
            self.run_gate("register", {"phase": "implement", "questions": [question()]})
        self.assertEqual((self.directory / gate.PENDING).read_bytes(), before)

    def test_ack_default_blank_partial_and_other_ids_do_not_release_pending(self):
        self.registration["questions"].append(question("model_policy"))
        self.register()
        before = (self.directory / gate.PENDING).read_bytes()
        invalid = [{"request_id": "registered"}, {"answers": {}},
                   {"selected": "기본 구현"}, {"default": "기본 구현"}, self.response,
                   {"answers": {"another_id": {"answers": ["기본 구현"]}}}]
        for answer in ([], [" "], [None], [True], ["기본 구현", ""]):
            invalid.append({"answers": {"implementation_path": {"answers": answer},
                                         "model_policy": {"answers": ["기본 구현"]}}})
        invalid = [{**value, "question_set_id": self.response["question_set_id"]} for value in invalid]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_gate("answer", value)
            self.assertEqual((self.directory / gate.PENDING).read_bytes(), before)
            self.assertFalse((self.directory / "decisions.md").exists())

    def test_actual_response_records_choices_once_and_resumes_same_phase(self):
        self.register()
        value, code = self.run_gate("answer", self.response)
        self.assertEqual(code, 0)
        self.assertEqual(value["phase"], "design")
        self.assertFalse((self.directory / gate.PENDING).exists())
        self.assertEqual(self.run_gate("status"), ({"status": "clear"}, 0))
        record = (self.directory / "decisions.md").read_text(encoding="utf-8")
        self.assertIn("**→** 독립 구현 — 구현 에이전트에 위임", record)
        self.assertIn("- 기본 구현 — 현재 세션에서 진행", record)
        self.assertTrue(self.run_gate("answer", self.response)[0]["repeated"])
        self.assertEqual((self.directory / "decisions.md").read_text(encoding="utf-8"), record)
        with self.assertRaises(ValueError):
            self.run_gate("answer", {"question_set_id": self.response["question_set_id"],
                                     "answers": {"implementation_path": {"answers": ["기본 구현"]}}})

    def test_partial_decision_write_failure_retains_pending_and_no_receipt(self):
        self.register()
        with mock.patch.object(gate, "atomic_text", side_effect=OSError("storage failure")):
            with self.assertRaises(OSError):
                self.run_gate("answer", self.response)
        self.assertEqual(self.run_gate("status")[1], 2)
        self.assertFalse((self.directory / gate.RECEIPT).exists())

    def test_decision_written_before_receipt_failure_recovers_without_duplicate(self):
        self.register()
        with mock.patch.object(gate, "atomic_json", side_effect=OSError("receipt failure")):
            with self.assertRaises(OSError):
                self.run_gate("answer", self.response)
        record = (self.directory / "decisions.md").read_bytes()
        with self.assertRaises(ValueError):
            self.run_gate("answer", {"question_set_id": self.response["question_set_id"],
                                     "answers": {"implementation_path": {"answers": ["다른 답변"]}}})
        self.assertTrue(self.run_gate("answer", self.response)[0]["repeated"])
        self.assertEqual((self.directory / "decisions.md").read_bytes(), record)

    def test_new_registration_after_answer_is_new_question_even_for_same_id(self):
        first = self.register()
        old_response = dict(self.response)
        self.run_gate("answer", self.response)
        second = self.register()
        self.assertNotEqual(first["question_set_id"], second["question_set_id"])
        with self.assertRaises(ValueError):
            self.run_gate("answer", {"answers": self.response["answers"]})
        with self.assertRaises(ValueError):
            self.run_gate("answer", old_response)
        self.assertEqual(self.run_gate("status")[1], 2)
        actual = {**self.response, "question_set_id": second["question_set_id"]}
        self.run_gate("answer", actual)
        self.assertTrue(self.run_gate("answer", actual)[0]["repeated"])
        self.assertEqual((self.directory / "decisions.md").read_text(encoding="utf-8").count("**Q.**"), 2)

    def test_invalid_pending_is_not_silently_cleared_or_overwritten(self):
        self.register()
        path = self.directory / gate.PENDING
        path.write_text('{"version": 1}', encoding="utf-8")
        for command, value in (("status", None), ("register", self.registration),
                               ("answer", self.response)):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.run_gate(command, value)
        self.assertEqual(path.read_text(encoding="utf-8"), '{"version": 1}')

    def test_path_traversal_absolute_and_nested_paths_are_rejected(self):
        for path in (".dev/../escape", "../escape", ".dev/a/b", str(self.root), ".dev/.",
                     ".dev/..", ".dev/CON", ".dev/com1.json", ".dev/NUL", ".dev/name.",
                     ".dev/name ", ".dev/name:", ".dev/name?", ".dev/a\x00b", ".dev/a\nb"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                gate.run("register", self.root, path, self.registration)

    def test_dot_and_unicode_branch_slugs_are_accepted(self):
        for slug in ("codex-fix-api.v2", "기능-질문.v2", "release-2026.10"):
            with self.subTest(slug=slug):
                value, code = gate.run("register", self.root, ".dev/" + slug, self.registration)
                self.assertEqual(code, 0)
                self.assertEqual(value["phase"], "design")
                self.assertEqual(gate.run("status", self.root, ".dev/" + slug)[1], 2)

    def test_supplied_question_set_token_must_match_even_on_first_question(self):
        first = self.register()
        with self.assertRaises(ValueError):
            self.run_gate("answer", {**self.response, "question_set_id": "stale-token"})
        self.run_gate("answer", {**self.response, "question_set_id": first["question_set_id"]})

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root / ".dev").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink 권한 없음: {exc}")
            with self.assertRaises(ValueError):
                self.register()

    def test_concurrent_or_abandoned_lock_blocks_status_and_mutations(self):
        self.register()
        (self.directory / ".question-lock").write_text("123", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_gate("status")
        with self.assertRaises(FileExistsError):
            self.run_gate("answer", self.response)
        self.assertTrue((self.directory / gate.PENDING).exists())

    def test_cli_utf8_register_gate_answer_and_retry(self):
        script = str(Path(gate.__file__))
        def invoke(command, value=None):
            args = [sys.executable, script, command, "--cwd", str(self.root), "--dev-dir", ".dev/test"]
            if value is not None:
                source = self.root / "input.json"
                source.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                args.extend(["--input", str(source)])
            process = subprocess.run(args, capture_output=True)
            return process.returncode, json.loads(process.stdout.decode("utf-8"))
        self.assertEqual(invoke("register", self.registration)[0], 0)
        self.response["question_set_id"] = invoke("status")[1]["question_set_id"]
        self.assertEqual(invoke("status")[0], 2)
        self.assertEqual(invoke("answer", {"request_id": "ack"})[0], 2)
        self.assertEqual(invoke("answer", self.response)[1]["phase"], "design")
        self.assertEqual(invoke("status")[0], 0)
        (self.directory / ".question-lock").write_text("123", encoding="utf-8")
        code, result = invoke("status")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "blocked")

    def test_invalid_registration_does_not_create_pending(self):
        for payload in ({"questions": [question()]}, {"phase": "design", "questions": []},
                        {"phase": "design", "questions": [question("BadId")]},
                        {"phase": "design", "questions": [question()] * 2}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.run_gate("register", payload)
            self.assertFalse((self.directory / gate.PENDING).exists())

    def test_sync_hook_does_not_duplicate_helper_owned_question_record(self):
        self.directory = self.root / ".dev" / "no-branch"
        self.run_gate = lambda command, value=None: gate.run(command, self.root, ".dev/no-branch", value)
        self.register()
        script = Path(gate.__file__).resolve().parents[1] / ".claude/hooks/codex_hook.py"
        payload = {"tool_name": "request_user_input", "cwd": str(self.root),
                   "tool_input": {"questions": [question()]}, "tool_response": self.response}
        def capture():
            process = subprocess.run([sys.executable, str(script), "capture"],
                                     input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                     capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
        capture()
        self.assertFalse((self.directory / "decisions.md").exists())
        self.run_gate("answer", self.response)
        payload["question_set_id"] = self.response["question_set_id"]
        capture()
        self.assertEqual((self.directory / "decisions.md").read_text(encoding="utf-8").count("**Q.**"), 1)

    def test_same_question_and_choice_after_completion_is_an_independent_hook_event(self):
        self.directory = self.root / ".dev" / "no-branch"
        self.run_gate = lambda command, value=None: gate.run(command, self.root, ".dev/no-branch", value)
        self.register()
        self.run_gate("answer", self.response)
        script = Path(gate.__file__).resolve().parents[1] / ".claude/hooks/codex_hook.py"
        payload = {"tool_name": "AskUserQuestion", "cwd": str(self.root),
                   "tool_input": {"questions": [question()]},
                   "tool_response": {"answers": {question()["question"]: "독립 구현"}}}
        process = subprocess.run([sys.executable, str(script), "capture"],
                                 input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((self.directory / "decisions.md").read_text(encoding="utf-8").count("**Q.**"), 2)


if __name__ == "__main__":
    unittest.main()
