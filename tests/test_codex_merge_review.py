"""PR #104(보조 스킬 경계 보강·요구사항 문답) 병합 후 독립 리뷰 지적의 문서 계약 회귀 검사.

리뷰 원문은 세션 scratchpad의 review-docs·review-analysis·review-delivery 보고서이고,
반영 결과는 .dev/fix-gx-work-audit/merge-review.md에 정리한다.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
TDD = SKILLS / "gx-tdd"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> str:
    return read(path).split("---", 2)[1]


class HumanizerShellBoundaryTests(unittest.TestCase):
    """윤문 대상은 외부 문서다. 문서 속 지시로 임의 명령이 사전 승인되지 않아야 한다."""

    def test_bash_is_limited_to_helper_and_hash_commands(self):
        front = frontmatter(SKILLS / "gx-humanizer/SKILL.md")
        self.assertNotRegex(front, r"(?m)^  - Bash\s*$")
        self.assertIn("Bash(python *)", front)

    def test_powershell_pipe_sets_utf8_before_freezing_source(self):
        # PowerShell 5.1 파이프는 UTF-8 설정 없이 비ASCII를 ?로 바꾼 채 원문이 불변 동결된다.
        line = next(l for l in read(SKILLS / "gx-humanizer/references/run-preservation.md").splitlines()
                    if "PowerShell" in l and "PYTHONUTF8" in l)
        self.assertIn("[Console]::OutputEncoding", line)
        self.assertIn("--input-file", line)


class ResearchExplicitOutputTests(unittest.TestCase):
    """F37 유지: --output으로 정한 경로는 사용자 산출물이라 .research/·.gitignore를 건드리지 않는다."""

    def setUp(self):
        self.text = read(SKILLS / "gx-research/SKILL.md")

    def test_runtime_directory_rule_excludes_explicit_output(self):
        rule = next(l for l in self.text.splitlines() if l.startswith("`.research/`는"))
        self.assertIn("`--output`", rule)
        self.assertIn("`.gitignore`도 바꾸지 않는다", rule)

    def test_null_findings_path_means_working_memory(self):
        reserve = self.text.split("사용자 지정 경로가 있으면 `--output", 1)[1].split("\n", 1)[0]
        self.assertIn("`null`", reserve)
        self.assertIn("작업 메모리", reserve)


class ReadOnlyHandoffDialogueTests(unittest.TestCase):
    """리뷰 H1·M1·M2: 읽기 전용 인계는 요청한 문서만 run 디렉토리에 저장하고, 미정이면 저장 전에 멈춘다."""

    def setUp(self):
        self.dialogue = read(TDD / "references/requirements-dialogue.md")

    def bullet(self, start):
        return next(l for l in self.dialogue.splitlines() if l.startswith(start))

    def test_read_only_saves_requested_documents_in_run_directory(self):
        line = self.bullet("- **HANDOFF_READ_ONLY**")
        for marker in ("`.dev/<run-id>/`", "state", "`register`/`answer`"):
            self.assertIn(marker, line)
        self.assertIn("아무것도", self.bullet("- **문서 저장 금지·대화 전용 계획**"))

    def test_claude_decision_hook_record_is_a_named_exception(self):
        self.assertIn("결정 기록 훅", self.dialogue.split("## 3.", 1)[1].split("## 4.", 1)[0])

    def test_requirements_save_step_matches_plan_handoff(self):
        save = read(TDD / "phases/phase-requirements.md").split("**Phase 완료 후 저장**", 1)[1].split("\n1. ", 1)[0]
        self.assertIn("`.dev/<run-id>/`", save)
        self.assertNotIn("HANDOFF_READ_ONLY·문서 금지이면 기존 파일과 state를 보존하고 대화로만", save)

    def test_read_only_branch_checks_waiting_before_saving(self):
        skill = read(TDD / "SKILL.md")
        branch = skill.split("if HANDOFF_READ_ONLY", 1)[1].split("return  # READ_ONLY_COMPLETE", 1)[0]
        self.assertLess(branch.index('return "waiting"'), branch.index(".dev/<run-id>/"))


class DialogueExitTests(unittest.TestCase):
    """리뷰 M3·M4: 상한 뒤에도 사용자 응답으로 이어 갈 길과 문답을 끝낼 수단이 있어야 한다."""

    def test_user_answer_after_design_cap_authorizes_one_more_iteration(self):
        after = read(TDD / "phases/phase-design.md").split("**2회 반복 후**", 1)[1].split("\n\n", 1)[0]
        self.assertIn("추가 반복 1회", after)

    def test_listed_questions_can_be_delegated_and_long_dialogue_offers_exit(self):
        section = read(TDD / "references/requirements-dialogue.md").split("## 1.", 1)[1].split("## 3.", 1)[0]
        self.assertIn("항목별 위임", section)
        self.assertIn("3회", section)
        self.assertIn("중단", section)


if __name__ == "__main__":
    unittest.main()
