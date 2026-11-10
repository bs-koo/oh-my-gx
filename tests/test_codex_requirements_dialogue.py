"""문답 진입 계약과 실제 pending 파일 회귀. 앱·모델 행동 smoke는 아니다."""

from pathlib import Path
import re
import tempfile
import unittest

from codex_test_support import load


ROOT = Path(__file__).resolve().parents[1]
TDD = ROOT / ".claude/skills/gx-tdd"
SHARED = TDD / "references/requirements-dialogue.md"
gate = load("gx_requirements_dialogue_gate", "scripts/codex-question.py")


def read(path):
    return path.read_text(encoding="utf-8-sig")


def question(identifier, body):
    return {"id": identifier, "header": "정책 확인", "question": body,
            "options": [{"label": "적용", "description": "확인한 정책을 적용합니다."},
                        {"label": "제외", "description": "이번 변경 범위에서 제외합니다."}]}


class RequirementsDialogueContractTests(unittest.TestCase):
    def shared(self):
        self.assertTrue(SHARED.is_file(), "두 모드의 문답 종료 조건 정본이 필요합니다")
        return read(SHARED)

    def test_shared_contract_distinguishes_readiness_waiting_and_approval(self):
        text = self.shared()
        for section in ("## 1. 중요한 미정 판정", "## 2. 문답 루프",
                        "## 3. 대기·재개와 쓰기 경계", "## 4. 재사용·진입·승인"):
            self.assertTrue(section in text, f"공통 문답 계약 절 누락: {section}")
        for result in ("ready", "waiting", "stopped", "mode-transition"):
            self.assertIn(result, text)
        self.assertTrue(re.search(r"문답[^\n]*승인[^\n]*(?:아님|아니다|대신하지|대체하지)", text),
                        "문답 해소와 실행 승인은 별개여야 합니다")

    def test_requirements_consults_dialogue_before_core_and_plan_reuse(self):
        text = read(TDD / "phases/phase-requirements.md")
        self.assertTrue("requirements-dialogue.md" in text, "requirements에서 공통 문답 계약을 읽어야 합니다")
        check = text.index("requirements-dialogue.md")
        self.assertLess(check, text.index("## 핵심 모드 분기 (core)"))
        self.assertLess(check, text.index("**기존 계획 재사용 분기 (전체 모드)**"))

    def test_full_mode_does_not_advance_with_unresolved_questions_after_one_recall(self):
        text = read(TDD / "phases/phase-requirements.md")
        unsafe = re.compile(r"product-owner를 1회 더 호출[.。]?\s*미해결 질문이 있으면 기록하고 phase-design으로 진행")
        self.assertIsNone(unsafe.search(text), "재호출 횟수가 중요한 미정 해소를 대신하면 안 됩니다")
        self.assertTrue("requirements-dialogue.md" in text, "전체 모드도 같은 문답 종료 조건을 사용해야 합니다")

    def test_completion_marker_cannot_suppress_real_pending_questions(self):
        text = read(TDD / "references/interaction-contract.md")
        process = text.split("#### 변환 프로세스", 1)[1]
        second_step = re.search(r"(?ms)^2\.(.*?)(?=^3\.)", process).group(1)
        self.assertNotIn('"추가 확인 사항 없음"이 포함되면 질문 변환을 건너뛴다.', second_step,
                         "종료 문구가 실제 질문 목록보다 우선하면 안 됩니다")
        self.assertTrue(re.search(r"(?:질문|미정)[^\n]*(?:없|비어)", second_step),
                        "변환 생략 전에 실제 질문·중요 미정 부재를 확인해야 합니다")
        self.assertTrue(re.search(r"충돌|불일치", second_step) and "대기" in second_step,
                        "종료 문구와 질문 목록이 충돌하면 실제 질문을 처리하고 대기해야 합니다")

    def test_design_and_implement_cannot_reuse_artifacts_before_dialogue_check(self):
        for name, reuse_marker in (("phase-design.md", "## 승인된 설계 재사용"),
                                   ("phase-implement.md", "## 핵심 모드 분기 (core)")):
            text = read(TDD / "phases" / name)
            with self.subTest(phase=name):
                self.assertTrue("requirements-dialogue.md" in text, f"단독 진입의 문답 검사 누락: {name}")
                self.assertLess(text.index("requirements-dialogue.md"), text.index(reuse_marker))
        design = read(TDD / "phases/phase-design.md")
        questions = design.split("**Step 4**:", 1)[1].split("**2회 반복 후**:", 1)[0]
        self.assertNotIn('("추가 확인 사항 없음"이 포함되지 않은 경우)', questions,
                         "설계 질문 분기도 종료 문구로 실제 질문을 숨기면 안 됩니다")
        criteria = questions.split("**질문이 있으면**", 1)[0]
        self.assertTrue("목록" in criteria and "미정" in criteria,
                        "설계 Step 4는 실제 질문 목록과 중요한 미정을 먼저 대조해야 합니다")
        capped = design.split("**2회 반복 후**:", 1)[1].split("**Phase 완료 후 저장**", 1)[0]
        self.assertTrue("미정" in capped and "waiting" in capped,
                        "설계 검토 상한 후에도 중요한 미정은 대기해야 합니다")

    def test_phase_completion_checks_dialogue_instead_of_only_file_presence(self):
        text = read(TDD / "SKILL.md")
        self.assertTrue("requirements-dialogue.md" in text, "phase 루프에서 문답 결과를 확인해야 합니다")
        completion = text[text.index("# 2c."):text.index("# 2e.")]
        self.assertIn("ready", completion)
        self.assertIn("waiting", completion)
        self.assertLess(completion.index("ready"), completion.index("Update state.md"))

    def test_core_dialogue_keeps_parent_ownership_and_read_only_has_no_registration(self):
        text = self.shared()
        self.assertIn("오케스트레이터", text)
        readonly = text.split("## 3. 대기·재개와 쓰기 경계", 1)[1].split("## 4.", 1)[0]
        self.assertIn("HANDOFF_READ_ONLY", readonly)
        self.assertIn("register", readonly)
        self.assertRegex(readonly, r"(?:하지 않는다|금지|호출하지)")
        entry = read(TDD / "SKILL.md")
        readonly_entry = entry.split("if HANDOFF_READ_ONLY:", 1)[1].split(
            'if requested_phase == "requirements":', 1)[0]
        complete = readonly_entry.index("READ_ONLY_COMPLETE")
        completion_line = readonly_entry.rfind("\n", 0, complete) + 1
        branches_by_outcome = {}
        for outcome in ("waiting", "stopped"):
            branches = [match for match in re.finditer(r"(?m)^\s+if [^\n]+", readonly_entry)
                        if outcome in match.group(0)]
            self.assertTrue(branches, f"읽기 전용 조기 반환 전에 {outcome}을 처리해야 합니다")
            branches_by_outcome[outcome] = branches[0]
            self.assertLess(branches[0].start(), complete)
            self.assertTrue(re.search(r"\breturn\b", readonly_entry[branches[0].start():completion_line]),
                            f"{outcome}을 완료로 처리하지 않고 대기/중단해야 합니다")
        self.assertLess(branches_by_outcome["stopped"].start(), branches_by_outcome["waiting"].start(),
                        "미정이 남아 있어도 사용자의 중단 요청을 먼저 처리해야 합니다")
        core = read(TDD / "phases/phase-requirements.md").split(
            "`use_inline_core`가 참이면", 1)[1].split("핵심 모드가 아닌 경우", 1)[0]
        self.assertNotRegex(core, r"Task\([^\n]*(?:product-owner|design-critic|test-architect)")


class RequirementsDialoguePendingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gx 요구사항 문답 ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / ".dev/dialogue"
        self.directory.mkdir(parents=True)
        self.state = self.directory / "state.md"
        self.state.write_text("pipeline: gx-tdd\nmode: core\nphase: requirements\n"
                              "status: in_progress\ncore-plan-status: approved\n",
                              encoding="utf-8")
        self.original_state = self.state.read_bytes()

    def run_gate(self, command, value=None):
        return gate.run(command, self.root, ".dev/dialogue", value)

    def register(self, identifier, body):
        return self.run_gate("register", {"phase": "requirements", "questions": [
            question(identifier, body)]})[0]

    def response(self, pending, value="적용"):
        return {"question_set_id": pending["question_set_id"], "answers": {
            item["id"]: {"answers": [value]} for item in pending["questions"]}}

    def test_three_followup_rounds_keep_fresh_pending_tokens_in_original_phase(self):
        tokens = []
        for mode in ("core", "all"):
            with self.subTest(mode=mode):
                # 같은 질문 helper를 사용하며 모드별 질문 상태기계를 만들지 않는다.
                self.state.write_text(f"pipeline: gx-tdd\nmode: {mode}\nphase: requirements\n"
                                      "status: in_progress\n", encoding="utf-8")
                baseline = self.state.read_bytes()
                for identifier, body in (("duplicate_policy", "중복 신청을 막을까요?"),
                                         ("cancelled_policy", "취소 완료 후 재신청을 허용할까요?"),
                                         ("cancel_pending_policy", "취소 처리 중에도 신청을 막을까요?")):
                    pending = self.register(identifier, body)
                    tokens.append(pending["question_set_id"])
                    status, code = self.run_gate("status")
                    self.assertEqual(code, 2)
                    self.assertEqual(status["phase"], "requirements")
                    answered, code = self.run_gate("answer", self.response(pending))
                    self.assertEqual((code, answered["phase"]), (0, "requirements"))
                    self.assertEqual(self.run_gate("status"), ({"status": "clear"}, 0))
                    self.assertEqual(self.state.read_bytes(), baseline)
        self.assertEqual(len(tokens), len(set(tokens)))
        self.assertEqual(read(self.directory / "decisions.md").count("**Q.**"), 6)

    def test_stale_answer_for_same_policy_id_does_not_resolve_new_followup(self):
        first = self.register("cancel_policy", "취소 후 재신청을 허용할까요?")
        old_answer = self.response(first)
        self.run_gate("answer", old_answer)
        second = self.register("cancel_policy", "취소 처리 중에도 재신청을 허용할까요?")
        self.assertNotEqual(first["question_set_id"], second["question_set_id"])
        before = (self.directory / gate.PENDING).read_bytes()
        with self.assertRaises(ValueError):
            self.run_gate("answer", old_answer)
        self.assertEqual((self.directory / gate.PENDING).read_bytes(), before)
        self.assertEqual(self.run_gate("status")[1], 2)
        self.assertEqual(self.state.read_bytes(), self.original_state)

    def test_standalone_design_and_implement_keep_resume_phase_and_cursor_for_followups(self):
        for mode in ("core", "all"):
            for entry_phase, step in (("design", "설계 질문"), ("implement", "1.2 구현 계획")):
                with self.subTest(mode=mode, phase=entry_phase):
                    self.state.write_text(
                        f"pipeline: gx-tdd\nmode: {mode}\nphase: {entry_phase}\n"
                        f"requested-phase: {entry_phase}\ncurrent-step: {step}\n"
                        f"execution-phases: [{entry_phase}]\nstop-at: verify\nstatus: in_progress\n",
                        encoding="utf-8")
                    baseline = self.state.read_bytes()
                    previous_token = None
                    for identifier, body in (("expiry_scope", "기존 링크에도 만료를 적용할까요?"),
                                             ("expiry_pending_scope", "진행 중인 다운로드에도 적용할까요?")):
                        pending, code = self.run_gate("register", {
                            "phase": entry_phase, "questions": [question(identifier, body)]})
                        self.assertEqual((code, pending["phase"]), (0, entry_phase))
                        self.assertNotEqual(pending["question_set_id"], previous_token)
                        status, code = self.run_gate("status")
                        self.assertEqual((code, status["phase"]), (2, entry_phase))
                        self.assertEqual(self.state.read_bytes(), baseline)
                        result, code = self.run_gate("answer", self.response(pending))
                        resume_phase = result["phase"]
                        self.assertEqual((code, resume_phase), (0, entry_phase))
                        self.assertEqual(self.run_gate("status"), ({"status": "clear"}, 0))
                        self.assertEqual(self.state.read_bytes(), baseline)
                        previous_token = pending["question_set_id"]

    def test_ack_and_partial_followup_answers_preserve_prior_decision_and_pending(self):
        first = self.register("duplicate_policy", "중복 신청을 막을까요?")
        self.run_gate("answer", self.response(first))
        pending = self.run_gate("register", {"phase": "requirements", "questions": [
            question("cancel_policy", "취소 완료 후 허용할까요?"),
            question("pending_policy", "취소 처리 중에도 허용할까요?")]})[0]
        before = (self.directory / gate.PENDING).read_bytes()
        decisions = (self.directory / "decisions.md").read_bytes()
        invalid = [{"request_id": "ack"},
                   {"question_set_id": pending["question_set_id"], "answers": {
                       "cancel_policy": {"answers": ["적용"]}}},
                   {"question_set_id": pending["question_set_id"], "answers": {
                       "cancel_policy": {"answers": ["적용"]},
                       "pending_policy": {"answers": []}}}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_gate("answer", value)
            self.assertEqual((self.directory / gate.PENDING).read_bytes(), before)
            self.assertEqual((self.directory / "decisions.md").read_bytes(), decisions)
            self.assertEqual(self.run_gate("status")[1], 2)
        self.assertEqual(self.state.read_bytes(), self.original_state)

    def test_approval_cannot_replace_an_unanswered_followup(self):
        self.register("cancel_pending_policy", "취소 처리 중에도 신청을 막을까요?")
        before = (self.directory / gate.PENDING).read_bytes()
        with self.assertRaises(ValueError):
            self.run_gate("register", {"phase": "implement", "questions": [
                question("core_plan_approval", "AC와 구현 계획을 승인할까요?")]})
        self.assertEqual((self.directory / gate.PENDING).read_bytes(), before)
        self.assertEqual(self.run_gate("status")[0]["phase"], "requirements")
        self.assertEqual(self.state.read_bytes(), self.original_state)

    def test_new_approval_pending_is_independent_of_completed_dialogue(self):
        pending = self.register("duplicate_policy", "중복 신청을 막을까요?")
        self.run_gate("answer", self.response(pending))
        approval, code = self.run_gate("register", {"phase": "requirements", "questions": [
            question("core_plan_approval", "확정된 AC와 구현 계획을 승인할까요?")]})
        self.assertEqual(code, 0)
        self.assertNotEqual(approval["question_set_id"], pending["question_set_id"])
        self.assertEqual(self.run_gate("status")[1], 2)
        self.assertEqual(read(self.directory / "decisions.md").count("**Q.**"), 1)
        self.assertEqual(self.state.read_bytes(), self.original_state)

    def test_read_only_status_does_not_create_dialogue_files_or_pipeline_state(self):
        with tempfile.TemporaryDirectory(prefix="gx 조회만 ") as empty:
            root = Path(empty)
            self.assertEqual(gate.run("status", root, ".dev/dialogue"), ({"status": "clear"}, 0))
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
