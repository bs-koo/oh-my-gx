"""배포 문서의 실행 정책을 검사한다. 실제 모델 행동·설치 앱 smoke는 아니다."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"


def documented_policy(test, relative, function):
    path = SKILLS / relative
    test.assertTrue(path.is_file(), f"정책 문서 누락: {relative}")
    blocks = re.findall(r"```python\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
    source = next((block for block in blocks if f"def {function}(" in block), None)
    test.assertIsNotNone(source, f"실행 가능한 정책 함수 누락: {function}")
    namespace = {}
    try:
        exec(compile(source, str(path), "exec"), namespace)
    except Exception as error:
        test.fail(f"{function} 예제 실행 실패: {type(error).__name__}: {error}")
    return namespace[function]


class CorePlanEdgeTests(unittest.TestCase):
    def policy(self, name):
        return documented_policy(self, "gx-tdd/references/core-planning.md", name)

    def phases(self, pipeline, mode, requested_phase):
        self.assertEqual(pipeline, "gx-tdd")
        return self.policy("select_phases")(mode, requested_phase)

    def test_read_only_handoff_selects_plan_phases_without_saved_state(self):
        select = self.policy("select_phases")
        for phase, expected in (
            (None, ["explore", "requirements"]),
            ("requirements", ["explore", "requirements"]),
            ("design", ["explore", "design"]),
        ):
            with self.subTest(phase=phase):
                self.assertEqual(select(None, phase, handoff_read_only=True), expected)

    def test_read_only_handoff_rejects_execution_phases(self):
        select = self.policy("select_phases")
        for phase in ("implement", "review", "complete", "unknown"):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                select(None, phase, handoff_read_only=True)

    def test_unknown_phase_is_not_silently_replaced_with_a_full_run(self):
        select = self.policy("select_phases")
        for mode in ("all", "core"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                select(mode, "unknown")

    def test_saved_explicit_mode_wins_over_legacy_core_flags(self):
        restore = self.policy("restore_mode")
        for mode, flags, expected in (
            ("all", "--core --phase complete", "all"),
            ("core", "", "core"), (None, "--core --eco", "core"),
            (None, ["--eco", "--core"], "core"), (None, [], "all"),
            (None, "--core-extra --label=--core", "all"),
            (None, ["--core-extra", "--label=--core"], "all"),
        ):
            with self.subTest(mode=mode, flags=flags):
                self.assertEqual(restore(mode, flags), expected)

    def test_invalid_explicit_mode_does_not_fall_back_to_flags(self):
        restore = self.policy("restore_mode")
        for mode in ("other", "CORE", "", 1):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                restore(mode, "--core")

    def test_requested_phase_overrides_both_modes(self):
        for pipeline in ("gx-tdd",):
            for mode in ("all", "core"):
                for phase in ("complete", "implement", "review"):
                    with self.subTest(pipeline=pipeline, mode=mode, phase=phase):
                        self.assertEqual(self.phases(pipeline, mode, phase), [phase])

    def test_document_phase_requests_use_explore_without_execution_setup(self):
        for pipeline in ("gx-tdd",):
            for mode in ("all", "core"):
                for phase in ("requirements", "design"):
                    with self.subTest(pipeline=pipeline, mode=mode, phase=phase):
                        self.assertEqual(self.phases(pipeline, mode, phase), ["explore", phase])

    def test_default_execution_preserves_pipeline_core_shape(self):
        for pipeline, core_phases in (
            ("gx-tdd", ["setup", "requirements", "implement", "complete"]),
        ):
            with self.subTest(pipeline=pipeline, mode="core"):
                self.assertEqual(self.phases(pipeline, "core", None), core_phases)
            with self.subTest(pipeline=pipeline, mode="all"):
                self.assertEqual(self.phases(pipeline, "all", None),
                                 ["setup", "requirements", "design", "implement", "review", "complete"])

    def test_full_transition_runs_review_without_recreating_setup(self):
        full = self.policy("full_mode_phases")
        for pipeline in ("gx-tdd",):
            with self.subTest(pipeline=pipeline):
                self.assertEqual(full(pipeline), ["requirements", "design", "implement", "review", "complete"])
        with self.assertRaises(ValueError):
            full("unknown")

    def test_implement_boundary_uses_actual_later_completion(self):
        needs = self.policy("needs_boundary_regression")
        for phases, expected in (
            (["implement"], True), (["implement", "review"], True),
            (["complete", "implement"], True),
            (["implement", "complete"], False),
            (["requirements", "design", "implement", "review", "complete"], False),
            (["complete"], False), ([], False),
        ):
            with self.subTest(phases=phases):
                self.assertEqual(needs(phases), expected)

    def test_completion_consumes_normalized_mode_before_any_work(self):
        for pipeline in ("gx-tdd",):
            with self.subTest(pipeline=pipeline):
                text = (SKILLS / pipeline / "phases/phase-complete.md").read_text(encoding="utf-8")
                entry = text.split("## Step -2:", 1)[0]
                for phrase in ("restore_mode", "core-plan", "승인"):
                    self.assertTrue(phrase in entry, f"{pipeline}: 완료 진입 전 {phrase} 검증 누락")
        tdd = (SKILLS / "gx-tdd/phases/phase-complete.md").read_text(encoding="utf-8")
        gate = tdd.split("## Step -2:", 1)[1].split("## Step -1:", 1)[0]
        self.assertNotIn("`mode: core` 또는 `flags`의 `--core` 포함", gate,
                         "TDD 이행 판정도 정규화된 mode를 사용해야 함")

    def test_explicit_document_phases_produce_prd_dependencies_in_saved_core(self):
        path = SKILLS / "gx-tdd/phases/phase-requirements.md"
        blocks = re.findall(r"```python\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
        policy = next((block for block in blocks if "use_inline_core" in block), None)
        self.assertIsNotNone(policy, "명시 requirements/design은 PRD를 만드는 분기로 연결해야 함")
        for mode, phase, expected in (
            ("core", None, True), ("core", "implement", True),
            ("core", "requirements", False), ("core", "design", False),
            ("all", None, False),
        ):
            with self.subTest(mode=mode, phase=phase):
                namespace = {"mode": mode, "requested_phase": phase}
                exec(compile(policy, str(path), "exec"), namespace)
                self.assertEqual(namespace["use_inline_core"], expected)


    def test_gwt_gate_uses_current_document_in_saved_core_mode(self):
        path = SKILLS / "gx-tdd/phases/phase-requirements.md"
        text = path.read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)\n```", text, re.S)
        route = next(block for block in blocks if "use_inline_core =" in block)
        gate = text.split("## G-W-T 검증 게이트", 1)[1]
        selection = next((block for block in re.findall(r"```python\n(.*?)\n```", gate, re.S)
                          if "gwt_document" in block), None)
        self.assertIsNotNone(selection, "게이트도 현재 PRD/inline 분기의 문서와 재작성 주체를 선택해야 함")
        for mode, phase, document, rewriter in (
            ("core", None, "ac.md", "orchestrator"),
            ("core", "implement", "ac.md", "orchestrator"),
            ("core", "requirements", "prd.md", "product-owner"),
            ("core", "design", "prd.md", "product-owner"),
            ("all", None, "prd.md", "product-owner"),
        ):
            with self.subTest(mode=mode, phase=phase):
                namespace = {"mode": mode, "requested_phase": phase}
                exec(compile(route, str(path), "exec"), namespace)
                exec(compile(selection, str(path), "exec"), namespace)
                self.assertEqual(namespace["gwt_document"], document)
                self.assertEqual(namespace["gwt_rewriter"], rewriter)
        self.assertIn("`gwt_document`", gate)
        self.assertIn("`gwt_rewriter`", gate)
        self.assertNotIn("**핵심 모드**는 ac.md", gate)


if __name__ == "__main__":
    unittest.main()
