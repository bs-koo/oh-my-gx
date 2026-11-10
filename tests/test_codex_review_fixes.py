"""gx-work 전수조사 수정본(fix/gx-work-audit)의 독립 리뷰 지적 회귀 검사.

지시문은 소비 프로젝트에서 모델이 읽는 계약이다. 리뷰가 찾은 모순·막다른 길이 문서에 다시
생기지 않는지 확인한다. 지적 번호는 문서 리뷰의 High/Medium/Low 순번이다.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
WORK = SKILLS / "gx-work"
TDD = SKILLS / "gx-tdd"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def row(text: str, prefix: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(prefix))


class CompletedRunEndpointTests(unittest.TestCase):
    """High-1: verify로 끝난 실행의 커밋·PR도 gx-tdd 종료점 변경으로 재검증한다."""

    def test_gx_work_routes_finished_run_through_endpoint_change(self):
        line = row(read(WORK / "SKILL.md"), "| 커밋만·PR만")
        self.assertIn("verify로 끝난", line)
        self.assertIn("종료점 변경", line)
        self.assertNotIn("재발급 없이", line)

    def test_user_guides_match(self):
        guide = read(ROOT / "docs/guide.md")
        self.assertIn("검증으로 끝난 작업", guide)
        self.assertNotIn("진행 중인 실행이 없으면 커밋·PR 스킬의 확인 절차만", guide)
        self.assertIn("검증으로 끝난 작업", row(read(ROOT / "docs/tdd-guide.md"), "| 진행 중"))


class CompletedRunReentryTests(unittest.TestCase):
    """High-2: 완료 실행 재진입은 결정 기록·상태 되돌림 뒤 검증하고, 실패하면 원복한다."""

    def test_environment_detection_reverts_before_validation(self):
        body = read(TDD / "SKILL.md")
        step = body.split("> 6. ", 1)[1].split("\n", 1)[0]
        self.assertLess(step.index("status: completed"), step.index("0.05"))
        self.assertIn("원복", step)

    def test_endpoint_change_updates_state_approval_after_reissue(self):
        section = read(TDD / "references/intent-routing.md").split("### 종료점 변경", 1)[1].split("\n### ", 1)[0]
        self.assertIn("entry-approved-scope-sha256", section)
        self.assertIn("handoff-file", section)
        self.assertIn("entry-approved-scope-sha256", read(TDD / "references/plan-handoff.md"))


class NewScopeWorktreeTests(unittest.TestCase):
    """High-3: 새 범위 안내의 워크트리 명령은 하나로, 미커밋 변경이면 워크트리만."""

    COMMAND = "git worktree add <경로> -b <새 브랜치> <베이스>"
    FILES = (WORK / "SKILL.md", ROOT / "docs/onboarding-guide.md", TDD / "phases/setup-branch.md",
             TDD / "references/intent-routing.md", ROOT / "scripts/gx-work.py")

    def test_every_worktree_hint_uses_a_new_branch(self):
        for path in self.FILES:
            text = read(path)
            with self.subTest(path=path.name):
                self.assertIn(self.COMMAND, text)
                for bad in re.findall(r"git worktree add[^`\"\n]*", text):
                    self.assertIn("-b <새 브랜치>", bad)
                self.assertNotIn("--detach", text)

    def test_base_checkout_is_only_for_clean_work(self):
        for path in (WORK / "SKILL.md", ROOT / "docs/onboarding-guide.md", ROOT / "scripts/gx-work.py"):
            with self.subTest(path=path.name):
                self.assertIn("미커밋", read(path))


class HandoffFlagTests(unittest.TestCase):
    """Medium-2: 요청에 명시한 핵심 모드·베이스는 인계 플래그로 전달한다."""

    def test_explicit_core_and_base_are_forwarded(self):
        body = read(WORK / "SKILL.md")
        for flag in ("--core", "--base <브랜치>"):
            with self.subTest(flag=flag):
                self.assertIn(flag, body)


class CodexEntryRecordTests(unittest.TestCase):
    """Medium-3: Codex 진입 답변 기록은 커밋되는 run 디렉토리에도 남긴다."""

    def test_answer_marker_is_copied_into_run_directory(self):
        text = read(WORK / "references/tdd-entry.md")
        self.assertIn("<!-- gx-question:", text)
        self.assertIn(".dev/<run-id>/decisions.md", text)


class PullRequestInputsTests(unittest.TestCase):
    """Medium-4: 파이프라인이 넘긴 PR 입력 파일은 미커밋 작업으로 치지 않는다."""

    def test_background_and_extra_section_files_are_not_uncommitted_work(self):
        body = read(SKILLS / "gx-pull-request/SKILL.md")
        rule = body.split("- **미커밋 변경 선행 확인**", 1)[1].split("\n  - ", 1)[0]
        self.assertIn("`--background`", rule)
        self.assertIn("`--extra-section`", rule)


class CommitChainTests(unittest.TestCase):
    """Medium-5: 사용자가 커밋과 PR을 함께 요청했으면 커밋 성공 뒤 PR로 잇는다."""

    def test_commit_chains_to_pull_request_only_for_user_requests(self):
        body = read(SKILLS / "gx-commit/SKILL.md")
        chain = body.split("## 커밋과 PR을 함께 요청한 경우", 1)[1].split("\n## ", 1)[0]
        self.assertIn("oh-my-gx:gx-pull-request", chain)
        self.assertIn("성공한 뒤에만", chain)
        self.assertIn("파이프라인", chain)


class ReviewOnlyTests(unittest.TestCase):
    """Medium-6: 리뷰만은 gx-tdd 리뷰 phase나 교차 리뷰로 잇는다."""

    def test_review_only_has_its_own_route(self):
        line = row(read(WORK / "SKILL.md"), "| 리뷰만")
        self.assertIn("--phase review", line)
        self.assertIn("gx-cross-review", line)


class CompletionRequestScopeTests(unittest.TestCase):
    """Medium-7: 커밋·PR 종료점 변경 근거는 이번 세션의 사용자 발화뿐이다."""

    def test_saved_goal_does_not_widen_endpoint(self):
        body = read(TDD / "phases/phase-complete.md")
        for step in ("## Step 1: Commit", "## Step 2: PR 생성"):
            section = body.split(step, 1)[1].split("\n## ", 1)[0]
            with self.subTest(step=step):
                self.assertIn("이번 세션의 사용자 발화", section)
                self.assertIn("저장된 goal", section)


class GitOwnershipTests(unittest.TestCase):
    """코드 리뷰 Medium: v2 검증은 git을 부르므로 gx-tdd 호출부도 소유권 불일치 인자를 안내한다."""

    def test_gx_tdd_validate_calls_mention_git_safe_directory(self):
        for relative in ("SKILL.md", "phases/phase-setup.md", "references/plan-handoff.md"):
            text = read(TDD / relative)
            lines = [line for line in text.splitlines() if "validate-handoff --handoff" in line]
            with self.subTest(file=relative):
                self.assertTrue(lines)
                self.assertTrue(any("--git-safe-directory" in line for line in lines), lines)


class HelperRoundTwoDocTests(unittest.TestCase):
    """코드 리뷰 반영 뒤 helper 스펙(G1 2차)과 문서 정합."""

    def setUp(self):
        self.skill = read(WORK / "SKILL.md")
        self.handoff = read(WORK / "references/handoff.md")
        self.entry = read(WORK / "references/tdd-entry.md")

    def test_route_keys_are_documented(self):
        for key in ("stale-answered-file", "answered-selection", "detached-head: true"):
            with self.subTest(key=key):
                self.assertIn(key, self.skill)

    def test_reissue_refusals_and_legacy_run_id(self):
        for phrase in ("`legacy-run-id: true`", "아직 답하지 않은 질문", "경로를 깨는 run-id"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.handoff)

    def test_decision_conflict_rule_matches_intake(self):
        rule = self.handoff.split("**요청 인계의 차단 규칙**", 1)[1].split("\n\n", 1)[0]
        for phrase in ("`status: explicit`", "source", "scope", "metadata"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rule)

    def test_entry_marker_binding_is_whole_line_in_run_directory(self):
        self.assertIn("한 줄 그대로", self.entry)
        self.assertIn("`run_id`", self.entry)


class MissingAnswerRecordExitTests(unittest.TestCase):
    """코드 리뷰 재확인 Low: 표식 복사를 빠뜨린 v2 인계의 이동 뒤 실패에도 출구가 있다."""

    def test_same_endpoint_reissue_is_allowed_and_reported(self):
        for relative in ("phases/setup-resume.md", "references/plan-handoff.md"):
            text = read(TDD / relative)
            with self.subTest(file=relative):
                self.assertIn("응답 기록", text)
                self.assertIn("dropped-question-set-id", text)
        self.assertIn("응답 기록", read(WORK / "references/handoff.md").split("**재검증 실패의 출구**", 1)[1].split("\n- ", 1)[0])


class DocReviewRoundTwoTests(unittest.TestCase):
    """문서 리뷰 재확인에서 새로 나온 Medium 2·Low 8."""

    def test_a_resume_carries_and_applies_the_new_endpoint(self):
        skill = read(WORK / "SKILL.md")
        bullet = skill.split("- **종료점 변경**", 1)[1].split("\n- ", 1)[0]
        self.assertIn("--resume --stop-at <새 종료점>", bullet)
        resume = read(TDD / "phases/setup-resume.md")
        self.assertIn("명시 `--stop-at`", resume)
        section = read(TDD / "references/intent-routing.md").split("### 종료점 변경", 1)[1].split("\n### ", 1)[0]
        self.assertIn("--resume --stop-at", section)

    def test_b_commit_then_pr_does_not_loop(self):
        body = read(SKILLS / "gx-pull-request/SKILL.md")
        rule = body.split("- **미커밋 변경 선행 확인**", 1)[1].split("\n- **", 1)[0]
        self.assertIn("이번 요청에서 gx-commit을 이미 수행했으면", rule)
        self.assertIn("auto-stash.txt", rule)

    def test_la_completed_run_endpoint_change_is_not_a_dead_end(self):
        line = next(l for l in read(TDD / "phases/setup-resume.md").splitlines() if l.startswith("4. "))
        self.assertIn("종료점 변경", line)
        self.assertIn("--phase complete", line)

    def test_lb_reissue_validate_then_update_order(self):
        resume = read(TDD / "phases/setup-resume.md")
        self.assertNotIn("갱신한다 `validate-handoff`", resume)
        self.assertIn("다시 통과하면 state의 `handoff-file`", resume)

    def test_lc_rollback_restores_verify_fields(self):
        step = read(TDD / "SKILL.md").split("> 6. ", 1)[1].split("\n", 1)[0]
        self.assertIn("verify-status·verify-fingerprint", step)

    def test_ld_commit_declares_skill_and_codex_mapping(self):
        body = read(SKILLS / "gx-commit/SKILL.md")
        front = body.split("---", 2)[1]
        self.assertIn("  - Skill", front)
        adaptation = body.split("**하네스 적응**", 1)[1].split("도구 이름이 다르다는 이유로", 1)[0]
        self.assertIn("`Skill`", adaptation)

    def test_le_model_profile_travels_in_the_request_file(self):
        skill = read(WORK / "SKILL.md")
        self.assertNotIn("`--eco`/`--standard` 플래그로 붙인다", skill)
        self.assertIn("요청 파일의 `model-profile`", skill)

    def test_lf_routing_names_the_actual_start_record_step(self):
        self.assertIn("Step 5.5", read(ROOT / ".claude/rules/skill-routing.md"))

    def test_lg_endpoint_decision_is_recorded_once(self):
        section = read(TDD / "references/intent-routing.md").split("### 종료점 변경", 1)[1].split("\n### ", 1)[0]
        self.assertIn("이미 있으면 다시 쓰지 않는다", section)

    def test_lh_new_scope_worktree_branch_is_reused(self):
        branch = read(TDD / "phases/setup-branch.md")
        self.assertIn("현재 브랜치를 작업 브랜치로 쓴다", branch)


class LowFindingTests(unittest.TestCase):
    def test_auto_stash_pointer_stays_local(self):
        self.assertIn("/.dev/*/auto-stash.txt", read(WORK / "references/dev-sharing.gitignore"))
        self.assertIn("'.dev/*/auto-stash.txt'", read(SKILLS / "gx-commit/SKILL.md"))

    def test_slug_flag_is_parsed_by_gx_tdd(self):
        routing = read(TDD / "references/intent-routing.md")
        step_one = routing.split("**Step 1:", 1)[1].split("**Step 2:", 1)[0]
        self.assertIn("--slug", step_one)

    def test_plan_pointer_example_is_project_relative(self):
        self.assertNotIn("/absolute/project/.dev/task", read(TDD / "phases/phase-implement.md"))

    def test_research_findings_follow_output_mode(self):
        body = read(SKILLS / "gx-research/SKILL.md")
        policy = body.split("**Phase 0 응답 실패 정책**", 1)[1].split("\n", 1)[0]
        self.assertIn("저장 모드", policy)
        merge = next(line for line in body.splitlines() if line.startswith("4. 결과를 아래 findings 형식"))
        self.assertIn("기본 위치", merge)

    def test_recorded_entry_answer_is_reused_only_for_same_run(self):
        body = read(WORK / "SKILL.md")
        self.assertIn("answered-run-id", body)

    def test_dev_repo_routing_exception_matches_current_completion(self):
        rules = read(ROOT / ".claude/rules/skill-routing.md")
        self.assertNotIn("Step 3~4", rules)


if __name__ == "__main__":
    unittest.main()
