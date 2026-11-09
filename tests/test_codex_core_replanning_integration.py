"""재계획 후 보안 수리·정식 리뷰 소비 계약의 문서 회귀.

모델 실행이나 인증 앱 smoke를 대신하지 않는 정적 통합 계약 검사다.
"""

from pathlib import Path
import unittest


PHASES = Path(__file__).resolve().parents[1] / ".claude/skills/gx-tdd/phases"
SKILLS = PHASES.parents[1]
REFERENCES = PHASES.parent / "references"


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


class ReplanningIntegrationContractTests(unittest.TestCase):
    def test_h3_rechecks_boundary_regression_after_security_code_changes(self):
        text = (PHASES / "phase-implement.md").read_text(encoding="utf-8")
        h3 = section(text, "**Step H3**", "**Step H4**")
        self.assertIn("needs_boundary_regression(PHASES)", h3)
        self.assertRegex(h3, r"보안 수리[^\n]*Step 3\.5[^\n]*재실행")
        self.assertRegex(h3, r"이전[^\n]*(?:GREEN|통과)[^\n]*(?:재사용|대체)[^\n]*금지")
        self.assertRegex(h3, r"새 코드[^\n]*통과 증거[^\n]*단독[^\n]*완료 보고")

    def test_review_hash_focused_and_fallback_share_active_task_selection(self):
        text = (PHASES / "phase-review.md").read_text(encoding="utf-8")
        test_gate = section(text, "### Step 0-2: Test", "타입에 `test` 필드도 없으면")
        self.assertIn("REVIEW_ACTIVE_TASKS", test_gate)
        for label, next_label in (("1. **무결성 선확인**", "2. **누적 focused**"),
                                  ("2. **누적 focused**", "3. **전체 폴백**")):
            with self.subTest(consumer=label):
                self.assertIn("REVIEW_ACTIVE_TASKS", section(test_gate, label, next_label))
        self.assertIn("REVIEW_ACTIVE_TASKS", test_gate.split("3. **전체 폴백**", 1)[1])
        self.assertNotIn("모든 태스크 `test-file-hash`를 현재 파일", test_gate)
        self.assertRegex(test_gate, r"active[^\n]*소유권[^\n]*selector[^\n]*count")

    def test_review_preserves_retired_history_and_blocks_ambiguous_mapping(self):
        text = (PHASES / "phase-review.md").read_text(encoding="utf-8")
        test_gate = section(text, "### Step 0-2: Test", "타입에 `test` 필드도 없으면")
        self.assertRegex(test_gate, r"retired/superseded[^\n]*불변 이력")
        self.assertRegex(test_gate, r"과거[^\n]*현재 파일[^\n]*비교[^\n]*원복[^\n]*덮[^\n]*금지")
        self.assertRegex(test_gate, r"legacy[^\n]*세대 필드[^\n]*기존 동작")
        self.assertRegex(test_gate, r"매핑[^\n]*모호[^\n]*새 hash[^\n]*통과[^\n]*복원")
        self.assertRegex(test_gate, r"다른 테스트[^\n]*무결성[^\n]*유지")

    def test_review_repairs_continue_using_step_zero_selected_set(self):
        text = (PHASES / "phase-review.md").read_text(encoding="utf-8")
        self.assertIn("Step 4.4의 4b·4c 재확인이 모두 이 정의", text)
        self.assertGreaterEqual(text.count("Step 0 테스트 집합 ∪ 정리 대상 파일 관련 테스트"), 2)

    def test_standalone_verify_resolves_active_tasks_before_shared_plan_inputs(self):
        verify = (SKILLS / "gx-verify/SKILL.md").read_text(encoding="utf-8")
        verify_step = section(verify, "### Step 1:", "### Step 2:")
        self.assertIn("test-execution.md", verify_step)
        text = (REFERENCES / "test-execution.md").read_text(encoding="utf-8")
        planning = section(text, "## 계획 생성", "## 선택 규칙")
        selection = planning.split("\n3. ", 1)[0]
        for field in ("core-replanning.md", "§5", "ACTIVE_TASKS",
                      "baseline-generation", "active-case-ids", "supersedes"):
            with self.subTest(selection=field):
                self.assertIn(field, selection)
        required = section(planning, "\n3. ", "\n4. ")
        ownership = section(planning, "\n4. ", "\n```bash")
        for field in ("ACTIVE_TASKS", "test-file-hash", "required-tests.json"):
            with self.subTest(required=field):
                self.assertIn(field, required)
        for field in ("ACTIVE_TASKS", "test-ownership.json"):
            with self.subTest(ownership=field):
                self.assertIn(field, ownership)
        self.assertNotIn("모든 태스크의 `test-file`", required)
        self.assertIn('--cwd "$PROJECT_ROOT"', planning)

    def test_review_and_shared_verify_reference_one_active_selection_contract(self):
        contract = (REFERENCES / "core-replanning.md").read_text(encoding="utf-8")
        heading = "## 5. 활성 태스크 선택 정본"
        self.assertIn(heading, contract)
        selection = contract.split(heading, 1)[1]
        for field in ("ACTIVE_TASKS", "승인된 AC·계획", "active-case-ids",
                      "baseline-generation", "supersedes", "불변 이력"):
            with self.subTest(contract=field):
                self.assertIn(field, selection)
        self.assertRegex(selection, r"영향 없는 이전 세대[^\n]*유지")
        self.assertRegex(selection, r"retired/superseded[^\n]*현재 파일[^\n]*금지")
        self.assertRegex(selection, r"legacy[^\n]*세대[^\n]*기존 동작")
        review = (PHASES / "phase-review.md").read_text(encoding="utf-8")
        test_gate = section(review, "### Step 0-2: Test", "타입에 `test` 필드도 없으면")
        self.assertIn("core-replanning.md", test_gate)
        self.assertIn("§5", test_gate)
        self.assertIn("REVIEW_ACTIVE_TASKS = ACTIVE_TASKS", test_gate)

    def test_shared_verify_blocks_partial_mapping_before_conservative_fallback(self):
        text = (REFERENCES / "test-execution.md").read_text(encoding="utf-8")
        planning = section(text, "## 계획 생성", "## 선택 규칙")
        selection = planning.split("\n3. ", 1)[0]
        self.assertRegex(selection, r"일부[^\n]*매핑[^\n]*(?:모호|불명확)[^\n]*차단")
        self.assertRegex(selection, r"새 hash[^\n]*통과[^\n]*금지")
        self.assertRegex(selection, r"전체 폴백[^\n]*우회[^\n]*금지")
        self.assertIn("scope-closed", selection)
        ownership = section(planning, "\n4. ", "\n```bash")
        self.assertRegex(ownership, r"활성[^\n]*소유권[^\n]*확정[^\n]*전체 폴백")


if __name__ == "__main__":
    unittest.main()
