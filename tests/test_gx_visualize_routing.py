"""현재 지원하는 완료 단계 opt-in 계약을 양쪽 파이프라인에서 검증한다."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"


class GxVisualizeRoutingTests(unittest.TestCase):
    def complete_sections(self):
        for name in ("gx-dev", "gx-tdd"):
            text = (SKILLS / name / "phases" / "phase-complete.md").read_text(encoding="utf-8")
            section = text.split("## Step 5.5:", 1)[1].split("## Step 6:", 1)[0]
            yield name, section

    def test_completion_choice_invokes_service_with_project_and_comparison(self):
        for name, section in self.complete_sections():
            with self.subTest(pipeline=name):
                self.assertIn('label: "아키텍처 맵 갱신"', section)
                self.assertIn('label: "아니요"', section)
                self.assertIn("oh-my-gx:gx-visualize", section)
                invocation = re.search(r"`(service --project-root [^`]+)`", section)
                self.assertIsNotNone(invocation)
                args = invocation.group(1).split()
                self.assertEqual(args, ["service", "--project-root", "${PROJECT_ROOT}",
                                        "--changed-since", "${BASE_BRANCH}"])
                self.assertRegex(section, r"아니요[^\n]*건너뛴다")

    def test_headless_and_ralph_skip_before_the_question(self):
        for name, section in self.complete_sections():
            with self.subTest(pipeline=name):
                guard, _ = section.split("AskUserQuestion(", 1)
                self.assertIn("--non-interactive", guard)
                self.assertIn("ralph.lock", guard)
                self.assertIn("strict no-op", guard)
                self.assertIn("질문하지 않고", guard)

    def test_interactive_tool_absence_still_waits_for_a_real_choice(self):
        for name, section in self.complete_sections():
            with self.subTest(pipeline=name):
                self.assertRegex(section, r"자연어로 묻고 실제 답을 기다린다")
                self.assertIn("선택이 곧 동의이므로 다시 묻지 않는다", section)

    def test_svn_omits_git_comparison_and_reports_the_limitation(self):
        for name, section in self.complete_sections():
            with self.subTest(pipeline=name):
                self.assertRegex(section, r"svn이면[^\n]*`--changed-since`를 넘기지 않는다")
                self.assertIn("변경 표시 없이", section)

    def test_reports_domain_results_and_keeps_delivery_gates_separate(self):
        for name, section in self.complete_sections():
            with self.subTest(pipeline=name):
                for field in ("index_path", "validation_status", "backend", "changes"):
                    self.assertIn(f"`{field}`", section)
                self.assertIn("visualization_status: failed", section)
                self.assertIn("커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다", section)
                self.assertIn("시각화 성공으로 그 실패를 덮지 않는다", section)

    def test_removed_design_review_hooks_are_not_required(self):
        for name in ("gx-dev", "gx-tdd"):
            for phase in ("design", "review"):
                with self.subTest(pipeline=name, phase=phase):
                    text = (SKILLS / name / "phases" / f"phase-{phase}.md").read_text(encoding="utf-8")
                    self.assertNotRegex(text, r'Skill\(skill:\s*"oh-my-gx:gx-visualize"')
                    self.assertNotIn("VISUALIZE_REQUESTED", text)

    def test_standalone_input_paths_and_natural_routes_remain_available(self):
        text = (SKILLS / "gx-visualize" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("[--input-path <path>]...", text)
        self.assertIn("기본 수집을 제한하지 않는다", text)
        self.assertIn("명시 경로와 기본 탐색 결과를 합친다", text)
        for phrase in ("시각화 포함", "구조를 그림으로 보여줘", "변경 영향도를 시각화해줘"):
            self.assertIn(phrase, text)
        self.assertIn("명시 요청이 없으면 자동 실행하지 않는다", text)


if __name__ == "__main__":
    unittest.main()
