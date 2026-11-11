"""커밋·PR·verify 게이트 문서 계약 회귀 (2차 수정 X1: H1·M1·M3·L1·L2·L3·L11).

helper·훅 동작은 test_gx_aux_delivery.py와 scripts/hook-tests.sh가 실제 Git으로 검사한다.
여기서는 지시문이 그 동작과 같은 순서·조건을 계속 담고 있는지만 확인한다. 모델 행동 smoke는 아니다.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def section(text, start, end=None):
    tail = text.split(start, 1)[1]
    return tail.split(end, 1)[0] if end else tail


COMMIT = ".claude/skills/gx-commit/SKILL.md"
BRANCH = ".claude/skills/gx-commit/references/verify-and-branch.md"
HELPER = ".claude/skills/gx-commit/references/index-helper.md"
PULL = ".claude/skills/gx-pull-request/SKILL.md"
PR_RULES = ".claude/skills/gx-pull-request/references/pr-rules.md"
VERIFY = ".claude/skills/gx-verify/SKILL.md"
OUTPUT = ".claude/skills/gx-verify/references/output.md"
ROUTING = ".claude/rules/skill-routing.md"
CANCELLED_MARK = "verify 미통과(취소된 TDD 작업)"


class CancelledWorkTests(unittest.TestCase):
    """H1: 취소된 작업은 막지 않되 양 하네스 모두 경고하고 PR Checklist에 표기한다."""

    def test_commit_warns_without_blocking_in_both_harnesses(self):
        gate = section(read(COMMIT), "- **verify 게이트", "  - **지문 계산 규약**")
        self.assertIn("`status: cancelled`", gate)
        self.assertIn("양 하네스", gate)
        cancelled = section(read(BRANCH), "## 취소된 TDD 작업의 커밋 — 양 하네스", "\n## ")
        for marker in ("`status: cancelled`", "막지 않는다", "Codex", CANCELLED_MARK, "Checklist"):
            self.assertIn(marker, cancelled)

    def test_pull_request_marks_checklist_in_both_harnesses(self):
        gate = section(read(PULL), "- **verify 경고 게이트", "- **Codex 지문 계산·중단**")
        self.assertIn("`status: cancelled`", gate)
        self.assertIn(CANCELLED_MARK, gate)
        rules = section(read(PR_RULES), "## 취소된 TDD 작업의 PR — 양 하네스", "\n## ")
        for marker in ("묻지 않고", "Codex", f"- [ ] {CANCELLED_MARK}"):
            self.assertIn(marker, rules)

    def test_routing_does_not_offer_cancel_as_a_bypass(self):
        line = next(l for l in read(ROUTING).splitlines() if "**작업 취소 상태**" in l)
        for marker in ("`status: cancelled`", CANCELLED_MARK, "대안으로 안내하지 않는다"):
            self.assertIn(marker, line)


class StandaloneVerifyRecordTests(unittest.TestCase):
    """M1: 단독 verify도 진행 중인 gx-tdd state에 통과를 기록해야 커밋 안내가 풀린다."""

    def test_standalone_pass_is_written_to_the_running_state(self):
        standalone = section(read(OUTPUT), "## 기록용 블록")
        self.assertNotIn("기록할 오케스트레이터가 없으면 사용자 줄만 남긴다", standalone)
        for marker in ("`pipeline: gx-tdd`", "`status: in_progress`", "메인 세션",
                       "`verify-status: passed`", "`verify-fingerprint:`", "모두 같은 값"):
            self.assertIn(marker, standalone)
        passed = section(read(VERIFY), "### Step 5-A", "### Step 5-B")
        self.assertIn("단독 호출이면 메인 세션", passed)


class MergeConflictTests(unittest.TestCase):
    """M3: 미해결 충돌 경로가 남은 병합은 완화하지 않고 스테이징 전에 멈춘다."""

    def test_merge_relief_requires_no_unmerged_paths(self):
        merge = next(l for l in read(BRANCH).splitlines() if "**베이스 병합 커밋**" in l)
        for marker in ("`git ls-files -u`", "스테이징 전에 중단", "`git add <경로>`"):
            self.assertIn(marker, merge)
        self.assertIn("git ls-files -u", section(read(HELPER), "## 스테이징", "## 위험 수용 토큰"))
        self.assertIn("git ls-files -u", read(ROUTING))
        self.assertIn("ls-files -u", read(".claude/hooks/pre-tool-guard.sh"))


class BaselineLoadTests(unittest.TestCase):
    """L1: 기존 실패·명령 지정은 warnings-baseline 유무와 무관하게 읽는다."""

    def test_known_failures_load_is_its_own_item(self):
        step = section(read(VERIFY), "### Step 0.5", "### Step 1:")
        baseline = next(l for l in step.splitlines() if "`warnings-baseline: N`" in l)
        self.assertNotIn("known-failures", baseline)
        separate = next(l for l in step.splitlines() if "`known-failures`" in l)
        self.assertIn("test-plan-override", separate)
        self.assertIn("무관하게", separate)


class RiskAcceptanceTests(unittest.TestCase):
    """L2·L3·L11: 토큰은 커밋 직전에 쓰고, 이미 받은 명시 응답은 다시 묻지 않는다(Claude Code만)."""

    def test_token_is_written_after_assert_excluded(self):
        commit_step = section(read(COMMIT), "커밋 **직전** `assert-excluded`", "\n6. ")
        self.assertIn("accept-risk", commit_step)
        accept = next(l for l in read(BRANCH).splitlines() if '"위험을 알고 커밋"을 **실제 응답으로' in l)
        self.assertLess(accept.index("assert-excluded"), accept.index('"action":"accept-risk"'))
        self.assertIn("토큰이 남지 않는다", accept)
        helper = section(read(HELPER), "## 위험 수용 토큰", "## 실패 복원")
        self.assertIn("응답 직후가 아니라", helper)
        self.assertIn("링크", helper)

    def test_explicit_earlier_answer_counts_only_in_claude_code(self):
        claude = section(read(BRANCH), "## verify 미통과 커밋 — Claude Code", "## 취소된")
        already = next(l for l in claude.splitlines() if "**이미 받은 위험 수용**" in l)
        for marker in ("지금 상태 그대로 커밋", "실제 응답", "다시 묻지 않는다", "추측"):
            self.assertIn(marker, already)
        routing = read(ROUTING)
        self.assertIn("지금 상태 그대로 커밋", routing)
        self.assertIn("Codex에는 이 경로가 없다", routing)


class LegacyGuidanceMoveTests(unittest.TestCase):
    """SKILL.md 예산 때문에 옮긴 레거시 Ralph 안내가 참조 파일에 그대로 있다."""

    def test_legacy_guidance_lives_in_the_reference(self):
        self.assertIn("`references/verify-and-branch.md` 레거시 절", read(COMMIT))
        legacy = section(read(BRANCH), "## 제거된 Ralph 실행 기록 — 양 하네스")
        for marker in ("검증 표식과 무관하게", "자동 재개·상태 변환을 하지 않는다"):
            self.assertIn(marker, legacy)


if __name__ == "__main__":
    unittest.main()
