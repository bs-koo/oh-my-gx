"""핵심 모드의 계획·승인·재개 계약을 배포 지시문에서 검증한다.

정적 계약 검사이며 실제 모델의 도구 호출이나 앱 사용자 이벤트를 실행하지 않는다.
"""

from pathlib import Path
import hashlib
import re
import subprocess
import sys
import tempfile
import unittest

from test_codex_skill_questions import (
    INPUT_LABEL,
    static_question_shapes,
    validate_question_shape,
)


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
CONTRACT = SKILLS / "gx-tdd/references/core-planning.md"


class CorePlanningContractTests(unittest.TestCase):
    def read(self, relative):
        path = SKILLS / relative
        self.assertTrue(path.is_file(), f"필수 배포 계약 누락: {relative}")
        return path.read_text(encoding="utf-8")

    def contract(self):
        return self.read("gx-tdd/references/core-planning.md")

    def test_plan_has_concrete_files_order_ac_checks_and_assumptions(self):
        text = self.contract()
        for phrase in (
            "${DEV_DIR}/plan.md", "변경 파일", "작업 순서", "의존관계",
            "AC별 검증 방법", "영향 범위", "가정", "Read",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn(".dev/plan.md", text)

    def test_approval_is_bound_to_both_documents(self):
        text = self.contract()
        for phrase in (
            "core-plan-status", "core-plan-approved-digest", "SHA-256",
            "ac.md", "plan.md", "pending", "approved", "재승인",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_documented_digest_reads_exact_bytes_of_both_documents(self):
        snippets = re.findall(r"```python\n(.*?)\n```", self.contract(), re.DOTALL)
        digest_code = next((code for code in snippets if "hashlib" in code and "sys.argv" in code), None)
        self.assertIsNotNone(digest_code, "문서 지문 예제는 ac.md·plan.md 경로를 인수로 받아야 함")
        with tempfile.TemporaryDirectory(prefix="gx core plan ") as directory:
            ac = Path(directory) / "ac.md"
            plan = Path(directory) / "plan.md"
            cases = (
                (b"AC-1\r\n", b"files: one.py\r\n"),
                (b"AC-1\n", b"files: one.py\r\n"),
                (b"AC-1\n", "변경 파일: two.py\n".encode("utf-8")),
            )
            digests = set()
            for ac_bytes, plan_bytes in cases:
                ac.write_bytes(ac_bytes)
                plan.write_bytes(plan_bytes)
                result = subprocess.run(
                    [sys.executable, "-c", digest_code, str(ac), str(plan)],
                    capture_output=True, text=True, encoding="utf-8", check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = result.stdout.strip()
                self.assertEqual(actual, hashlib.sha256(ac_bytes + b"\0" + plan_bytes).hexdigest())
                digests.add(actual)
            self.assertEqual(len(digests), len(cases), "어느 문서가 바뀌어도 기존 승인 지문과 달라야 함")

    def test_agent_use_is_conditional_and_plan_has_a_self_check(self):
        text = self.contract()
        for phrase in ("오케스트레이터", "architect", "1회", "design-critic", "자체 점검", "전체 모드"):
            self.assertIn(phrase, text)

    def test_codex_waits_for_real_combined_approval(self):
        text = self.contract()
        for phrase in (
            "codex-runtime.md", "codex-questions.md", "core_plan_approval",
            "실제", "응답", "ack", "후속 질문", "Other",
        ):
            self.assertIn(phrase, text)

    def test_each_approval_branch_uses_one_question_with_valid_choices(self):
        text = self.contract()
        examples = [block for block in re.findall(r"```[^\n]*\n(.*?)\n```", text, re.S)
                    if "AskUserQuestion(" in block]
        self.assertTrue(examples, "실행 방법별 결합 승인 예제가 필요함")
        option_counts = []
        for example in examples:
            shapes = list(static_question_shapes("```text\n" + example + "\n```"))
            self.assertEqual(len(shapes), 1, "한 실행 분기는 결합 승인 질문 하나만 수행")
            questions, options = shapes[0]
            self.assertEqual(questions, 1)
            validate_question_shape(questions, options)
            option_counts.extend(options)
        self.assertIn(3, option_counts, "미정 방법은 세션/서브에이전트/문서 종료로 확인")
        self.assertRegex(text, r"유효한 방법[^\n]*승인/수정 요청 2선택",
                         "명시 실행 방법은 기존 선택을 유지하며 문서만 승인/수정한다")
        self.assertIsNone(INPUT_LABEL.search(text), "명시적 Other 선택지는 추가하지 않음")

    def test_document_only_exit_keeps_approval_pending_and_stops_execution(self):
        text = self.contract()
        rule = next((line for line in text.splitlines()
                     if "계획 문서로 종료" in line and "pending" in line), None)
        self.assertIsNotNone(rule, "문서 종료는 실행 승인 없이 pending으로 남겨야 함")
        for phrase in ("approved", "미구현", "RED", "complete", "체이닝하지"):
            self.assertIn(phrase, rule, "문서 종료를 구현·완료 승인으로 재사용하지 않음")

    def test_both_phases_load_the_same_deployed_contract(self):
        consumers = {
            "gx-tdd/phases/phase-requirements.md": "../references/core-planning.md",
            "gx-tdd/phases/phase-implement.md": "../references/core-planning.md",
        }
        for name, relative in consumers.items():
            with self.subTest(phase=name):
                self.assertIn(relative, self.read(name))
                self.assertEqual((SKILLS / name).parent.joinpath(relative).resolve(), CONTRACT.resolve())

    def test_tdd_requirements_approve_ac_and_plan_together(self):
        text = self.read("gx-tdd/phases/phase-requirements.md")
        core = text.split("## 핵심 모드 분기 (core)", 1)[1].split("핵심 모드가 아닌 경우", 1)[0]
        for phrase in ("plan.md", "G-W-T", "함께", "승인"):
            self.assertIn(phrase, core)

    def test_tdd_core_uses_approved_plan_as_rgr_input(self):
        text = self.read("gx-tdd/phases/phase-implement.md")
        core = text.split("## 핵심 모드 분기 (core)", 1)[1].split("## Step 0:", 1)[0]
        for phrase in ("plan.md", "승인", "RGR", "태스크"):
            self.assertIn(phrase, core)
        self.assertIn("plan.md", text.split("## Step 2:", 1)[1])
        self.assertNotIn("AC 1개를 단일 태스크로 간주하여 바로 Step 2 진입", text)

    def test_resume_restores_plan_and_never_infers_old_approval(self):
        for name in (
            "gx-tdd/phases/setup-resume.md",
        ):
            with self.subTest(phase=name):
                text = self.read(name)
                for phrase in ("plan.md", "core-planning.md", "승인"):
                    self.assertIn(phrase, text)

    def test_state_contracts_persist_the_approval_identity(self):
        for pipeline in ("gx-tdd",):
            with self.subTest(pipeline=pipeline):
                text = self.read(f"{pipeline}/references/pipeline-state.md")
                for phrase in ("plan.md", "core-plan-status", "core-plan-approved-digest"):
                    self.assertIn(phrase, text)

    def test_phase_only_completion_restores_core_mode_before_the_gate(self):
        for name in ("gx-tdd/SKILL.md",):
            with self.subTest(phase_entry=name):
                text = self.read(name)
                environment = text.split("> **환경 감지**:", 1)[1]
                for phrase in ("restore_mode", "flags", "core-planning.md", "승인"):
                    self.assertIn(phrase, environment, f"{name}: --phase complete에서 {phrase} 복원 누락")


if __name__ == "__main__":
    unittest.main()
