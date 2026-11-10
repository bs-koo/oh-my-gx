"""총괄 스킬이 context 요청을 구현계획으로 바꾸거나 무응답으로 TDD를 시작하지 않는다."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import ROOT, load
from test_gx_work import plan


work = load("gx_work_orchestration", "scripts/gx-work.py")
gate = load("gx_work_orchestration_question", "scripts/codex-question.py")


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gx-work-flow-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.request = self.root / "request.json"
        self.request.write_text(json.dumps({"goal": "사용량 엑셀 다운로드", "work-id": "W01",
            "requirements": [{"domain": "계량기", "ids": ["FR-1"]}],
            "sources": [{"path": None, "message-id": "u1"}]}), encoding="utf-8")

    def prepare(self, **extra):
        return work.handoff(request_path=self.request, project_root=self.root, run_id="run-1",
                            approval_source="u1: 구현하고 PR까지", stop_at="pr", **extra)

    def save(self, value):
        path = self.root / "handoff.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def answered_entry(self):
        """F11: question-set-id는 질문 helper가 실제 답변을 기록한 값이어야 한다."""
        question = {"id": "gx_work_tdd_entry", "header": "TDD 진입", "question": "gx-tdd로 진행할까요?",
                    "options": [{"label": "gx-tdd로 진행", "description": "범위대로 진행"},
                                {"label": "여기서 종료", "description": "개발하지 않음"}]}
        identifier = gate.run("register", self.root, ".dev/run-1",
                              {"phase": "work-entry", "questions": [question]})[0]["question_set_id"]
        gate.run("answer", self.root, ".dev/run-1", {"question_set_id": identifier,
                 "answers": {"gx_work_tdd_entry": {"answers": ["gx-tdd로 진행"]}}})
        return identifier

    def test_fresh_work_route_recommends_preparation_without_dispatching_tdd(self):
        result = work.route(self.root, "implement", stop_at="pr", goal="엑셀 다운로드")
        self.assertIsNone(result["skill"])
        self.assertTrue(result["requires-user-decision"])
        self.assertEqual(result["stop-at"], "pr")

    def test_context_intake_does_not_require_or_create_an_implementation_plan(self):
        before = self.snapshot()
        result = self.prepare()
        self.assertEqual(result["handoff-kind"], "request")
        self.assertIsNone(result["plan-file"])
        self.assertEqual(result["work-id"], "W01")
        self.assertFalse(result["ready-for-tdd"])
        self.assertEqual(self.snapshot(), before)

    def test_retired_ralph_request_cannot_be_approved_by_handoff(self):
        for goal in ("랄프로 기능 개발해줘", "/gx-ralph", "/gx-ralph-iterate", "루프 돌려"):
            with self.subTest(goal=goal):
                self.request.write_text(json.dumps({"goal": goal}), encoding="utf-8")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "지원.*중단"):
                    self.prepare(entry_approval_source="실제 사용자 진행 답변")
                self.assertEqual(self.snapshot(), before)

    def test_generic_implementation_request_is_not_the_tdd_entry_answer(self):
        result = self.prepare()
        self.assertEqual(result["approval"]["status"], "approved")
        self.assertEqual(result["entry-approval"]["status"], "unconfirmed")
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_actual_next_step_answer_allows_tdd_to_build_its_own_plan(self):
        identifier = self.answered_entry()
        result = self.prepare(entry_approval_source="u3: 이 범위로 TDD 진행", question_set_id=identifier)
        self.assertTrue(result["ready-for-tdd"])
        self.assertEqual(result["origin"], "gx-work")
        self.assertEqual(result["entry-approval"]["question-set-id"], identifier)
        checked = work.validate_handoff(self.save(result), self.root)
        self.assertTrue(checked["ready-for-tdd"])
        self.assertEqual(checked["run-id"], "run-1")

    def test_entry_answer_can_authorize_a_next_step_after_a_context_only_request(self):
        result = work.handoff(request_path=self.request, project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: 이 내용으로 개발 진행")
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_changed_intake_requires_a_new_scope_review(self):
        result = self.prepare(entry_approval_source="u3: TDD 진행")
        handoff = self.save(result)
        self.request.write_text('{"goal":"다른 기능 개발"}', encoding="utf-8")
        self.assertFalse(work.validate_handoff(handoff, self.root)["ready-for-tdd"])

    def test_run_endpoint_goal_and_digest_tampering_are_rejected(self):
        # I2: v2의 project-root는 표시용이라 결박 대상이 아니다(v1 결박은 test_gx_work_audit F04).
        # 대신 지문이 묶는 프로젝트 상대 포인터를 같은 내용의 다른 파일로 바꾸는 변조를 거절한다.
        first = self.prepare(entry_approval_source="u3: TDD 진행")
        (self.root / "copied-request.json").write_bytes(self.request.read_bytes())
        for key, value in (("run-id", "other-run"), ("stop-at", "commit"), ("goal", "다른 목표"),
                           ("input-sha256", "0" * 64), ("request-file", "copied-request.json")):
            with self.subTest(key=key):
                changed = copy.deepcopy(first)
                changed[key] = value
                self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])

    def test_missing_or_fabricated_ready_flag_does_not_replace_entry_answer(self):
        result = self.prepare()
        result["ready-for-tdd"] = True
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])
        result = self.prepare(entry_approval_source="u3: TDD 진행")
        result.pop("entry-approval")
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_entry_response_metadata_changes_are_detected(self):
        first = self.prepare(entry_approval_source="u3: TDD 진행", question_set_id=self.answered_entry())
        for field, value in (("source", "u-other: 다른 답변"), ("question-set-id", "q-another")):
            with self.subTest(field=field):
                changed = copy.deepcopy(first)
                changed["entry-approval"][field] = value
                self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])

    def test_saved_request_authority_and_false_readiness_are_not_overwritten(self):
        first = self.prepare(entry_approval_source="u3: TDD 진행")
        changed = copy.deepcopy(first)
        changed["approval"]["source"] = "다른 최초 요청"
        self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])
        changed = copy.deepcopy(first)
        changed["ready-for-tdd"] = False
        self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])

    def test_new_goal_is_not_silently_merged_into_a_different_active_work(self):
        subprocess.run(["git", "init", "-b", "feature/export", str(self.root)], check=True, capture_output=True)
        state = self.root / ".dev/feature-export/state.md"
        state.parent.mkdir(parents=True)
        state.write_text("pipeline: gx-tdd\nstatus: in_progress\nrun-id: old-run\ngoal: 기존 사용량 조회\nstop-at: verify\n", encoding="utf-8")
        before = self.snapshot()
        result = work.route(self.root, "implement", goal="새 정산 보고서")
        self.assertEqual(result["action"], "scope-review-required")
        self.assertEqual(result["requested-goal"], "새 정산 보고서")
        self.assertEqual(result["goal"], "기존 사용량 조회")
        self.assertIsNone(result["skill"])
        self.assertTrue(result["requires-user-decision"])
        self.assertEqual(self.snapshot(), before)

    def test_svn_pending_without_active_pointer_or_state_is_not_lost(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude/config.json").write_text('{"vcs":"svn"}', encoding="utf-8")
        pending = self.root / ".dev/export/pending-question.json"
        pending.parent.mkdir(parents=True)
        pending.write_text('{"phase":"work-entry","question_set_id":"q-entry"}', encoding="utf-8")
        before = self.snapshot()
        self.assertEqual(work.route(self.root, "resume")["action"], "awaiting-decision")
        another = self.root / ".dev/another/pending-question.json"
        another.parent.mkdir(parents=True)
        another.write_bytes(pending.read_bytes())
        result = work.route(self.root, "resume")
        self.assertEqual(result["action"], "resume-selection-required")
        self.assertEqual(len(result["candidate-pending-files"]), 2)
        self.assertIsNone(result["skill"])
        self.assertEqual(len(self.snapshot()), len(before) + 1)

    def test_approved_tdd_planning_entry_never_turns_into_implementation_permission(self):
        result = work.handoff(request_path=self.request, project_root=self.root, run_id="run-1",
                              stop_at="plan", entry_approval_source="u3: TDD에서 계획만 작성")
        self.assertTrue(result["ready-for-tdd"])
        self.assertTrue(result["read-only"])
        self.assertFalse(result["execution-authorized"])
        verified = work.validate_handoff(self.save(result), self.root)
        self.assertTrue(verified["ready-for-tdd"])
        self.assertTrue(verified["read-only"])
        result["execution-authorized"] = True
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_negative_or_malformed_receipts_never_become_entry_permission(self):
        receipt = self.prepare(entry_approval_source="u3: TDD 진행")
        for field, value in (("entry-approval", {"status": "declined", "source": "u4: 문서에서 종료"}),
                             ("schema-version", True), ("origin", "external")):
            with self.subTest(field=field):
                changed = copy.deepcopy(receipt)
                changed[field] = value
                self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])
        path = self.root / "handoff.json"
        path.write_text("[]", encoding="utf-8")
        self.assertFalse(work.validate_handoff(path, self.root)["ready-for-tdd"])

    def test_empty_entry_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            self.prepare(entry_approval_source=" ")

    def test_existing_plan_is_reused_without_forcing_context_to_write_it(self):
        path = self.root / "existing-plan.json"
        path.write_text(json.dumps(plan()), encoding="utf-8")
        before = self.snapshot()
        result = work.handoff(path, project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: 이 계획으로 TDD 진행")
        self.assertEqual(result["handoff-kind"], "plan")
        self.assertIsNone(result["request-file"])
        self.assertTrue(result["ready-for-tdd"])
        self.assertEqual(self.snapshot(), before)
        saved = self.save(result)
        self.assertTrue(work.validate_handoff(saved, self.root)["ready-for-tdd"])
        value = plan()
        value["units"][0]["ac"][0]["then"] = "새로운 동작"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assertFalse(work.validate_handoff(saved, self.root)["ready-for-tdd"])

    def test_cli_request_preparation_has_no_hidden_implementation_plan_requirement(self):
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/gx-work.py"), "handoff", "--request",
                                 str(self.request), "--project-root", str(self.root), "--run-id", "run-1",
                                 "--entry-approval-source", "u3: TDD 진행"],
                                text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ready-for-tdd"])
        self.assertEqual(self.snapshot(), before)

    def test_external_symlink_request_is_not_an_in_project_scope(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / "request.json"
            target.write_bytes(self.request.read_bytes())
            link = self.root / "linked.json"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink unavailable")
            with self.assertRaises(ValueError):
                work.handoff(request_path=link, project_root=self.root, run_id="run-1",
                             entry_approval_source="u3: 진행")

    def test_pending_entry_question_without_pipeline_state_is_resumed_readonly(self):
        subprocess.run(["git", "init", "-b", "feature/export", str(self.root)], check=True, capture_output=True)
        pending = self.root / ".dev/feature-export/pending-question.json"
        pending.parent.mkdir(parents=True)
        pending.write_text(json.dumps({"question_set_id": "q-entry", "phase": "work-entry",
                                      "questions": [{"id": "work_next_step", "question": "TDD로 진행할까요?"}]}), encoding="utf-8")
        before = self.snapshot()
        for intent in ("implement", "resume"):
            result = work.route(self.root, intent)
            self.assertEqual(result["action"], "awaiting-decision")
            self.assertIsNone(result["skill"])
            self.assertTrue(result["read-only"])
        self.assertEqual(work.route(self.root, "implement", goal="새 요청")["requested-goal"], "새 요청")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(work.route(self.root, "status")["action"], "status")

    def test_cli_rechecks_saved_handoff_without_writing_or_executing(self):
        path = self.save(self.prepare(entry_approval_source="u3: TDD 진행"))
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/gx-work.py"), "validate-handoff",
                                 "--handoff", str(path), "--project-root", str(self.root)],
                                text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ready-for-tdd"])
        self.assertEqual(self.snapshot(), before)
        self.save(self.prepare())
        result = subprocess.run([sys.executable, str(ROOT / "scripts/gx-work.py"), "validate-handoff",
                                 "--handoff", str(path), "--project-root", str(self.root)],
                                text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ready-for-tdd"])


if __name__ == "__main__":
    unittest.main()
