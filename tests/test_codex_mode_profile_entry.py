"""개발 시작 전 모드(전체/핵심)·프로파일(표준/에코) 질문과 추천 기준 회귀 (v3.2.0).

v2.0.0에서 "매 요청마다 모드·프로파일을 묻지 않는다"로 바뀌어, 요청에 미리 적지 않으면 선택할 기회가 없었다.
gx-work 진입 질문과 직접 gx-tdd 시작 시 정해지지 않은 항목만 한 번 묻고, 작업 경중 기준으로 추천한다.
에코를 고를 수 있을 때 세션이 상위 등급 모델이면 절감 범위를 안내한다. 종료점 추천은 pr이다.
후속(엣지케이스 리뷰): 모드 답은 인계 `mode`로 싣고, 설정·SVN·핵심 모드로 정해진 항목은 묻지 않으며,
Codex 둘째 세트·route setup-required/resume-elsewhere·진행 중 변경(프로파일·모드·취소·지금 상태 커밋)을 문서로 고정한다.
"""
from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
WORK_SKILL = SKILLS / "gx-work/SKILL.md"
ENTRY = SKILLS / "gx-work/references/tdd-entry.md"
HANDOFF = SKILLS / "gx-work/references/handoff.md"
QUESTIONS = SKILLS / "gx-work/references/codex-questions.md"
ROUTING = SKILLS / "gx-tdd/references/intent-routing.md"
PLAN_HANDOFF = SKILLS / "gx-tdd/references/plan-handoff.md"
SETUP_BRANCH = SKILLS / "gx-tdd/phases/setup-branch.md"
SETUP = SKILLS / "gx-tdd/phases/phase-setup.md"
IMPLEMENT = SKILLS / "gx-tdd/phases/phase-implement.md"
STATE = SKILLS / "gx-tdd/references/pipeline-state.md"
WORKTREE_ANCHOR = "tdd-entry.md#새-범위용-워크트리-만들기"


def read(path):
    return path.read_text(encoding="utf-8")


def section(text, start, end=None):
    tail = text.split(start, 1)[1]
    return tail.split(end, 1)[0] if end else tail


class GxWorkEntryQuestionTests(unittest.TestCase):
    def setUp(self):
        self.entry = section(read(ENTRY), "## gx-tdd 진입 직전의 실제 결정", "## 질문 대기·기록·재개")

    def test_entry_call_asks_mode_and_profile_with_endpoint(self):
        block = section(self.entry, "AskUserQuestion(", "\n```")
        for header in ('header: "TDD 진입"', 'header: "종료점"', 'header: "모드"', 'header: "프로파일"'):
            self.assertIn(header, block)

    def test_pr_is_the_recommended_endpoint(self):
        endpoint = section(self.entry, 'header: "종료점"', "]")
        self.assertIn('label: "pr (Recommended)"', endpoint)
        self.assertNotIn('label: "verify (Recommended)"', endpoint)

    def test_already_stated_items_are_not_asked_again(self):
        rule = section(self.entry, "다음 단계가 개발이면", "```")
        for marker in ("핵심만", "에코로", "PR까지", "빼고"):
            self.assertIn(marker, rule)

    def test_codex_splits_four_questions(self):
        self.assertIn("한 호출에 질문 3개까지", self.entry)

    def test_answers_are_handed_to_gx_tdd(self):
        self.assertIn("`--core`", self.entry)
        self.assertIn("`model-profile`", self.entry)

    def test_mode_answer_travels_in_the_handoff_not_only_a_flag(self):
        # 재진입·계획 인계에서도 "핵심" 답이 "전체"로 바뀌지 않도록 인계 지문에 묶는다.
        answer = section(self.entry, "- `gx-tdd로 진행`", "\n- ")
        for marker in ("`mode`", "handoff --mode", "--model-profile", "지문", "`mode: core`를 `--core`와 같게"):
            self.assertIn(marker, answer)
        handoff = read(HANDOFF)
        example = json.loads(handoff.split("```json", 1)[1].split("```", 1)[0])
        self.assertIn("mode", example)
        fields = next(line for line in handoff.splitlines() if line.startswith("- 선택 필드"))
        for marker in ("`mode`(`all`|`core`)", "진입 질문에서 답한", "handoff --mode"):
            self.assertIn(marker, fields)
        self.assertIn("mode?", handoff)
        self.assertIn("`mode`(`all`|`core`)", read(PLAN_HANDOFF))
        self.assertIn("진입 질문에서 답한", read(PLAN_HANDOFF))

    def test_items_decided_by_settings_svn_or_core_are_not_asked(self):
        omitted = section(self.entry, "**질문에서 빼는 항목**", "\n\n- `gx-tdd로 진행`")
        for marker in ("route `defaults`", "workflowDefaults", "설정값으로 진행",
                       "`configured-model-profile`", "(현재 설정)", "추천값"):
            self.assertIn(marker, omitted)
        svn = section(omitted, "- **SVN**", "\n- ")
        for marker in ('`vcs: "svn"`', "`.svn`", "종료점 질문을 빼고", "SVN은 검증까지 진행하고 커밋은 직접 합니다"):
            self.assertIn(marker, svn)
        core = section(omitted, "- **핵심 모드의 프로파일**", "\n\n")
        for marker in ("핵심 모드는 설계·전체 리뷰가 없어 프로파일 차이가 없습니다", "design-critic",
                       "질문 호출을 늘리지 않", "`standard`로 기록"):
            self.assertIn(marker, core)

    def test_stated_expressions_match_gx_tdd_step2(self):
        rule = section(self.entry, "다음 단계가 개발이면", "\n\n")
        table = section(read(ROUTING), "| 감지 패턴 |", "PHASE 매핑")
        for phrase in ("긴급", "핫픽스", "버그 수정만", "전체로", "전체 모드", "표준으로", "에코로"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rule)
                self.assertIn(f"`{phrase}`", table)

    def test_codex_second_set_ids_and_condition(self):
        rule = section(self.entry, "다음 단계가 개발이면", "\n\n")
        for marker in ("`gx_work_mode`", "`gx_work_model_profile`", "`gx-tdd로 진행`일 때만", "셋 이하면 한 세트"):
            self.assertIn(marker, rule)
        ids = next(line for line in read(ENTRY).splitlines() if line.startswith("`run-id`는 새 실행"))
        for marker in ("`gx_work_tdd_entry`", "`gx_work_stop_at`", "`gx_work_mode`", "`gx_work_model_profile`",
                       "첫 세트의 id"):
            self.assertIn(marker, ids)
        second = section(read(QUESTIONS), "**gx-work 진입 질문의 둘째 세트**", "\n\n")
        for marker in ("`gx-tdd로 진행`으로 기록된 뒤에만", "exit 2", "`여기서 종료`", "`run_answers`",
                       "`earlier_question_set_ids`", "첫 세트 id", "`entry-followup-missing`"):
            self.assertIn(marker, second)

    def test_pr_option_tells_w_start_record_is_pushed(self):
        endpoint = section(self.entry, 'header: "종료점"', "]")
        self.assertIn("착수 기록을 시작할 때 바로 원격 브랜치에 올립니다", endpoint)

    def test_missing_layer_runner_is_announced_before_the_question(self):
        notice = section(self.entry, "진입 질문 전에 대상 레이어", "\n\n")
        for marker in ("테스트 러너", "서버 동작 기준으로 검증합니다", "확인할 수 없으면"):
            self.assertIn(marker, notice)


class RecommendationCriteriaTests(unittest.TestCase):
    def setUp(self):
        self.criteria = section(read(ENTRY), "### 진행 방식 추천 기준", "\n## ")

    def test_mode_and_profile_have_documented_signals(self):
        for marker in ("핵심", "전체", "에코", "표준", "스키마", "권한", "중요한 미정", "(Recommended)"):
            self.assertIn(marker, self.criteria)

    def test_recommendation_states_its_reason_and_is_not_a_decision(self):
        self.assertIn("근거", self.criteria)
        self.assertIn("실제 답", self.criteria)

    def test_eco_notice_for_higher_tier_session(self):
        notice = section(self.criteria, "**에코 안내**", "\n\n")
        for marker in ("Opus", "Fable", "/model sonnet", "서브에이전트로 구현", "오케스트레이터"):
            self.assertIn(marker, notice)

    def test_eco_is_only_recommended_for_full_mode(self):
        eco = next(line for line in self.criteria.splitlines() if line.startswith("| 프로파일 | 에코"))
        self.assertNotIn("대체로 겹침", eco)
        for marker in ("전체 모드에서만", "중간 규모"):
            self.assertIn(marker, eco)

    def test_core_is_recommended_without_open_decisions_or_schema_change(self):
        core = next(line for line in self.criteria.splitlines() if line.startswith("| 모드 | 핵심"))
        for marker in ("중요 미정이 없고", "스키마", "권한", "핵심을 추천한다"):
            self.assertIn(marker, core)

    def test_default_recommendation_and_direct_step3_evidence(self):
        rule = section(self.criteria, "선택지 설명에는", "\n\n")
        for marker in ("전체를", "현재 설정", "표준을 추천", "Step 3", "코드를 탐색하지 않"):
            self.assertIn(marker, rule)

    def test_eco_notice_comes_before_the_question_with_switch_paths(self):
        notice = section(self.criteria, "**에코 안내**", "\n\n")
        for marker in ("질문 **전에**", "같은 요청을 다시 보내세요", "Esc로 멈추고", "'이어서'"):
            self.assertIn(marker, notice)
        self.assertNotIn("에코 선택지 설명에", notice)

    def test_eco_wording_is_harness_neutral_and_codex_unknown_model_skips_notice(self):
        notice = section(self.criteria, "**에코 안내**", "\n\n")
        for marker in ("Claude Code: sonnet", "mid 티어", "확인할 수 없으면", "안내하지 않는다"):
            self.assertIn(marker, notice)
        for text in (read(ENTRY), read(ROUTING)):
            option = next(line for line in text.splitlines() if 'label: "에코"' in line)
            self.assertIn("Codex: mid", option)
            self.assertNotIn("{세션 모델 안내}", option)


class DirectTddStartTests(unittest.TestCase):
    def setUp(self):
        self.step3 = section(read(ROUTING), "**Step 3:", "### 모드 판정 결과 기록")

    def test_undecided_mode_or_profile_is_asked_once(self):
        self.assertNotIn("매 요청마다 모드·모델 프로파일 질문을 만들지 않는다", self.step3)
        self.assertIn("AskUserQuestion(", self.step3)
        self.assertIn("진행 방식 추천 기준", self.step3)

    def test_gx_work_handoff_and_resume_are_not_asked_again(self):
        for marker in ("gx-work 인계", "--resume", "묻지 않는다"):
            self.assertIn(marker, self.step3)

    def test_profile_priority_includes_the_answer(self):
        priority = next(line for line in read(STATE).splitlines() if line.startswith("- 결정 우선순위"))
        self.assertIn("Step 3 질문 답변", priority)
        self.assertIn("정해지지 않은 항목만", priority)
        self.assertNotIn("함께 제시된 경우", priority)

    def test_step3_skip_list_and_setup_profile_order(self):
        # 부모 커밋에도 있던 문장 대신 이번 계약을 검사한다: 묻지 않는 경우 목록과 Step 1.5의 순서.
        skip = section(self.step3, "- **묻지 않는 경우**", "\n- ")
        for marker in ("gx-work 인계", "`--resume`", "STATUS", "PHASE 단독", "읽기 전용 인계",
                       "`mode`가 없는 이전 인계는 명시 `--core` > `all`"):
            self.assertIn(marker, skip)
        order = section(read(SETUP), "## Step 1.5: 모델 프로파일 결정", "\n## ")
        positions = [order.index(needle) for needle in ("1. 플래그", "gx-work 인계의 `model-profile`",
                                                        "ARGS[0] 자연어", "의도 파싱 Step 3", '"modelProfile"')]
        self.assertEqual(positions, sorted(positions))

    def test_step3_uses_workflow_defaults_and_skips_profile_for_core(self):
        head = self.step3.split("- **묻지 않는 경우**", 1)[0]
        for marker in ("`workflowDefaults.mode`", "`workflowDefaults.modelProfile`", "설정값으로 진행",
                       "(현재 설정)", "핵심 모드는 설계·전체 리뷰가 없어 프로파일 차이가 없습니다",
                       "CORE·ALL·ECO·STANDARD"):
            self.assertIn(marker, head)
        self.assertIn("정해지지 않은 항목만 실행 시작 전에 **한 번** 묻는다", head)
        answer = section(self.step3, "- 답은 state의", "\n\n")
        for marker in ("`standard`로 기록", "`gx_tdd_mode`", "`gx_tdd_model_profile`"):
            self.assertIn(marker, answer)

    def test_step3_recommendation_uses_only_the_request(self):
        rule = section(self.step3, "- **추천**", "\n- ")
        for marker in ("코드 탐색 전", "코드를 탐색하지 않", "전체·표준", "질문 **전에**"):
            self.assertIn(marker, rule)

    def test_gx_work_handoff_mode_core_counts_as_core_flag(self):
        step1 = section(read(ROUTING), "**Step 1: 플래그 호환**", "**Step 2: 자연어")
        rule = next(line for line in step1.splitlines() if "gx-work 인계의 모드 판정" in line)
        for marker in ("`mode`", "`core`면 `--core`와 같게", "호환용"):
            self.assertIn(marker, rule)

    def test_resume_with_profile_flag_is_a_change_not_a_conflict(self):
        routing = read(ROUTING)
        conflict = next(line for line in routing.splitlines() if line.startswith("- `--resume`과 `--phase`"))
        self.assertNotIn("`--status`, `--eco`", conflict)
        self.assertIn("재개와 프로파일 변경", conflict)
        change = section(routing, "### 진행 중 실행의 선택 변경", "\n### ")
        for marker in ("남은 디스패치부터", "전체 모드로 해줘", "core-planning.md#core--all-전환과-중단-후-재개",
                       "설계 전", "`mode: core`", "인계를 다시 발급하지 않는다", "`cancel`",
                       "지금 상태 그대로 커밋", "검증까지 마치고 커밋"):
            self.assertIn(marker, change)
        self.assertTrue((ROUTING.parent / "core-planning.md").read_text(encoding="utf-8")
                        .count("### core → all 전환과 중단 후 재개") == 1)

    def test_profile_change_on_resume_applies_to_remaining_dispatches(self):
        resume = next(line for line in read(STATE).splitlines() if line.startswith("- `--resume` 시"))
        self.assertNotIn("지원하지 않는다", resume)
        for marker in ("남은 디스패치부터", "decisions.md", "execution-log", "다시 실행하지 않는다"):
            self.assertIn(marker, resume)


class GxWorkRouteAndChangeTests(unittest.TestCase):
    """route 신규 결과·공통 출력, 진행 중 변경, 워크트리 직접 생성을 gx-work 문서가 다룬다."""

    def setUp(self):
        self.skill = read(WORK_SKILL)

    def test_new_route_results_and_common_outputs_have_handling(self):
        table = section(self.skill, "## route 결과별 처리", "\n## ")
        setup = next(line for line in table.splitlines() if line.startswith("| `setup-required`"))
        for marker in ("진입 질문 전에", "`reason`", "/oh-my-gx:gx-setup", "`Skill` 호출 금지"):
            self.assertIn(marker, setup)
        elsewhere = next(line for line in table.splitlines() if line.startswith("| `resume-elsewhere`"))
        for marker in ("`elsewhere-candidates`", "그 위치에서 이어서", "새 작업으로 시작", "`worktree`",
                       "git switch", "사용자가 고를 때만", "`setup-reason`"):
            self.assertIn(marker, elsewhere)
        for marker in ("`notices`", "`defaults`", "설정값으로 진행", "`configured-model-profile`",
                       "`answered-choices`", "`entry-followup-missing`", "핵심 모드의 프로파일"):
            self.assertIn(marker, table)

    def test_endpoint_row_matches_entry_question(self):
        row = next(line for line in self.skill.splitlines() if line.startswith("| 기능 구현·버그 수정"))
        self.assertNotIn("(요청하면 `commit`·`pr`)", row)
        for marker in ("추천 `pr`", "SVN은 `verify`"):
            self.assertIn(marker, row)
        self.assertIn("요청에서 밝혔거나 진입 질문에서 답한", self.skill)

    def test_in_progress_changes_cover_profile_mode_cancel_and_commit_now(self):
        changes = section(self.skill, "## 진행 중 실행의 변경", "\n\n자연어")
        commit_now = section(changes, "- **지금 상태 커밋**", "\n- ")
        for marker in ("지금 상태 그대로 커밋", "검증까지 마치고 커밋", "oh-my-gx:gx-commit", "Codex"):
            self.assertIn(marker, commit_now)
        # H1: Codex는 검증 후 커밋만 안내하고 작업 취소를 verify 미통과 커밋의 대안으로 권하지 않는다.
        self.assertIn("검증 후 커밋만 안내한다", commit_now)
        self.assertNotIn("작업 취소 뒤 커밋", commit_now)
        routing_commit = next(line for line in read(ROUTING).splitlines() if line.startswith("- **지금 상태 커밋**"))
        self.assertIn("Codex는 전자를 내지 않고 검증 후 커밋만 안내한다", routing_commit)
        profile = section(changes, "- **프로파일·모드 변경**", "\n- ")
        for marker in ("에코로 바꿔서", "--resume --eco", "남은 디스패치부터", "전체 모드로 해줘",
                       "intent-routing.md#진행-중-실행의-선택-변경"):
            self.assertIn(marker, profile)
        cancel = section(changes, "- **작업 취소**", "\n- ")
        for marker in ("`작업 취소` / `계속 진행`", "실제 답이 취소일 때만", "gx-work.py cancel", "--reason",
                       "status: cancelled", "추천·무응답"):
            self.assertIn(marker, cancel)
        self.assertIn("**지금 상태 커밋**", next(line for line in self.skill.splitlines()
                                              if line.startswith("| 커밋만·PR만")))

    def test_cancel_and_mode_options_are_documented_for_the_helper(self):
        helper = section(read(HANDOFF), "## helper와 입력 검증", "\n## ")
        cancel = next(line for line in helper.splitlines() if "gx-work.py cancel" in line)
        for marker in ("--reason", "--run-id", "--git-safe-directory", "--slug"):
            self.assertIn(marker, cancel)
        plan = next(line for line in helper.splitlines() if "gx-work.py handoff --plan" in line)
        for marker in ("--mode all|core", "--model-profile standard|eco"):
            self.assertIn(marker, plan)
        self.assertIn("`cancel`(현재 위치 state의 `status` 줄을 바꾸고 같은 디렉토리 `decisions.md`에 취소 근거를 "
                      "덧붙인다) 외에는 파일을 쓰거나", helper)
        for marker in ("`decisions-file`", "`pipeline`이 `gx-tdd`가 아님", "Ralph 흔적"):
            self.assertIn(marker, helper)

    def test_new_scope_worktree_is_created_with_consent(self):
        procedure = section(read(ENTRY), "## 새 범위용 워크트리 만들기", "\n## ")
        for marker in ("`새 워크트리 만들기 (Recommended)` / `중단`", "실제 답이 만들기일 때만",
                       "git worktree add <경로> -b <새 브랜치> <베이스>", "safe.directory", "/oh-my-gx:gx-work <목표>",
                       "무응답·추천만으로 만들지 않는다"):
            self.assertIn(marker, procedure)
        new_scope = section(self.skill, "- **새 범위로 시작**", "\n\n")
        escape = next(line for line in read(ROUTING).splitlines() if "구버전 기록에서 빠져나오기" in line)
        stop = next(line for line in read(SETUP_BRANCH).splitlines() if line.startswith("| 1 |"))
        for text in (new_scope, escape, stop):
            self.assertIn("사용자 동의를 받아", text)
            self.assertIn(WORKTREE_ANCHOR, text)


class ExecutionMethodRecommendationTests(unittest.TestCase):
    def test_method_recommendation_has_criteria(self):
        step = section(read(IMPLEMENT), "### 1.2 계획 검토·실행방법 확인", "### 1.3")
        rule = section(step, "**추천 기준**", "\n\n")
        for marker in ("서브에이전트", "태스크", "컨텍스트", "에코"):
            self.assertIn(marker, rule)


if __name__ == "__main__":
    unittest.main()
