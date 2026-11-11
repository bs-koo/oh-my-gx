"""gx-work 전수조사(2026-11-09) 결함 중 gx-work 문서·gx-context·gx-research 계약의 회귀 검사.

결함 ID는 `.dev/fix-gx-work-audit/audit-report.md`를 따른다. 문서 지시문이 소비 프로젝트에
설치되어 모델이 읽는 계약이므로, 수정한 결정이 문서에서 다시 사라지거나 옛 문구가 되살아나지
않는지 확인한다. 실제 세션의 스킬 선택·질문 UI는 여기서 검증하지 않는다.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
WORK = SKILLS / "gx-work"
REFS = WORK / "references"
CONTEXT = SKILLS / "gx-context"
RESEARCH = SKILLS / "gx-research"
ROUTE_ACTIONS = (
    "understand", "plan", "status", "implement", "resume", "no-active-run", "scope-review-required",
    "awaiting-decision", "resume-selection-required", "migration-required", "loop-active",
    "unsupported-request", "detached-head", "setup-required", "resume-elsewhere",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def description(path: Path) -> str:
    front = read(path).split("---", 2)[1]
    return re.search(r"(?m)^description:\s*(.+)$", front).group(1)


def section(text: str, start: str, end: str = "\n## ") -> str:
    tail = text.split(start, 1)[1]
    return tail.split(end, 1)[0]


def work_docs():
    return [WORK / "SKILL.md", *sorted(REFS.glob("*.md"))]


class TriggerDescriptionTests(unittest.TestCase):
    """F02: 자연어 개발 요청이 gx-work로 들어올 수 있게 설명 앞부분과 eval 세트를 둔다."""

    def test_work_description_leads_with_entry_triggers(self):
        text = description(WORK / "SKILL.md")
        first = text.split("다.", 1)[0]
        for marker in ("기능 구현", "버그 수정", "PR까지", "이어서", "W01", "계획만"):
            self.assertIn(marker, first)
        self.assertLessEqual(len(text), 1024)

    def test_context_description_sends_development_to_work(self):
        text = description(CONTEXT / "SKILL.md")
        for marker in (".dev/plan.md", "요구사항 추가", "작업 나눠줘"):
            self.assertIn(marker, text)
        self.assertRegex(text, r"개발[^.]*gx-work")

    def test_trigger_eval_set_covers_audit_scenarios_without_claiming_a_run(self):
        data = json.loads(read(WORK / "evals/evals.json"))
        self.assertEqual(data["skill_name"], "gx-work")
        self.assertEqual(data["run-status"], "NOT_RUN")
        evals = data["evals"]
        self.assertEqual([item["id"] for item in evals], list(range(1, len(evals) + 1)))
        expected = {
            "기능 구현": "gx-work", "버그 수정": "gx-work", "기획서로 PR까지": "gx-work",
            "계획만": "gx-work", "구조 파악": "gx-work", "이어서": "gx-work", "W03 시작": "gx-work",
            "요구사항 추가": "gx-context", "요구사항 추가 후 개발까지": "gx-work", "용어 정리": "gx-context",
            "기술 비교": "gx-research", "정책 영향": "gx-lens", "TDD로": "gx-tdd", "커밋": "gx-commit",
            "커밋하고 PR": "gx-commit", "랄프로": "gx-work", "context 동기화": "gx-context",
            "문서 정리": "gx-context",
        }
        self.assertEqual({item["scenario"]: item["expected_skill"] for item in evals},
                         {name: f"oh-my-gx:{skill}" for name, skill in expected.items()})
        for item in evals:
            with self.subTest(scenario=item["scenario"]):
                self.assertTrue(item["prompt"].strip())
                self.assertTrue(item["expectations"])
                self.assertIs(item["should_trigger"], item["expected_skill"] == "oh-my-gx:gx-work")
        chained = next(item for item in evals if item["scenario"] == "커밋하고 PR")
        self.assertEqual(chained["follow-up-skill"], "oh-my-gx:gx-pull-request")


class WorkIdFormatDocTests(unittest.TestCase):
    """F01: 작업 ID는 `W` + 두 자리 이상 ASCII 숫자(I1)로 문서도 통일한다."""

    def test_documents_describe_two_or_more_digit_ids(self):
        plan_mode = read(CONTEXT / "modes/plan.md")
        self.assertIn("두 자리 이상", plan_mode)
        self.assertIn("W100", plan_mode)
        self.assertNotIn("ID는 `W` + 두 자리 숫자.", plan_mode)
        entry = read(REFS / "tdd-entry.md")
        self.assertIn("두 자리 이상", entry)
        self.assertIn("(?<![A-Za-z0-9_-])W[0-9]{2,}(?![A-Za-z0-9_-])", entry)
        history = read(REFS / "decision-history.md")
        self.assertIn("두 자리 이상", history)
        self.assertNotIn("자릿수를 제한하지 않는다", history)
        self.assertNotIn("--work Wnn", read(CONTEXT / "references/development-sync.md"))

    def test_plan_helper_message_matches_the_shared_format(self):
        helper = read(CONTEXT / "scripts/plan.py")
        self.assertIn("두 자리 이상", helper)
        self.assertNotIn(r"\d{2}", helper)


class EntryCanonTests(unittest.TestCase):
    """F29·F47·F24·F19·F33a: 진입 질문 계약은 tdd-entry.md 한 곳이 소유한다."""

    CANON = "최초 요청은 TDD 진입 답변이 아니다"

    def setUp(self):
        self.entry = read(REFS / "tdd-entry.md")

    def test_first_request_rule_has_one_owner_and_pointers(self):
        owners = [path.name for path in work_docs() if self.CANON in read(path)]
        self.assertEqual(owners, ["tdd-entry.md"])
        stale = ("이후 제시하는 TDD 진입 질문의 답변은 아니다", "TDD 진입 질문의 실제 답변을 대신하지 않는다",
                 "최초 구현 요청은 그 답변을 대체하지 않는다")
        for path in work_docs():
            for phrase in stale:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertNotIn(phrase, read(path))
        for name in ("handoff.md", "planning.md"):
            self.assertIn("tdd-entry.md", read(REFS / name))

    def test_entry_and_endpoint_are_asked_in_one_question_call(self):
        self.assertIn("한 번의 질문 호출", self.entry)
        block = next(part for part in self.entry.split("```")[1::2] if "AskUserQuestion(" in part)
        # v3.2.0: 진입·종료점에 모드·프로파일까지 한 호출로 묻는다(이미 밝힌 항목은 뺀다).
        self.assertEqual(len(re.findall(r"(?m)^\s*question:", block)), 4)
        for group in re.findall(r"options:\s*\[(.*?)\]", block, re.S):
            self.assertIn(len(re.findall(r"\{\s*label:", group)), (2, 3))
        self.assertIn('header: "종료점"', block)
        self.assertIn("이미 밝힌 항목은 질문에서 빼고", self.entry)

    def test_claude_code_records_without_helper_and_codex_passes_real_set_id(self):
        self.assertIn("helper 등록 없이", self.entry)
        self.assertIn(".dev/<run-id>/decisions.md", self.entry)
        self.assertRegex(self.entry, r"`--question-set-id`[^\n]*Codex[^\n]*반환")
        skill = read(WORK / "SKILL.md")
        self.assertIn("`../../..`", skill)
        self.assertTrue((WORK / "../../../scripts/gx-work.py").resolve().is_file())

    def test_plan_only_and_development_questions_are_separate(self):
        for marker in ("개발 진입 질문", "계획 전용 질문", "대화로만 받기"):
            self.assertIn(marker, self.entry)
        row = next(line for line in read(WORK / "SKILL.md").splitlines() if line.startswith("| 계획/설계만"))
        for marker in ("planning.md", "대화", "인계"):
            self.assertIn(marker, row)

    def test_work_start_check_is_recorded_for_tdd_reuse(self):
        for marker in ("work-start:", "setup-work", "git ls-remote --heads origin", "`observed`"):
            self.assertIn(marker, self.entry)

    def test_execution_method_and_profile_flow_through_request(self):
        for marker in ("execution-method", "model-profile", "Step 1.2의 기본 선택"):
            self.assertIn(marker, self.entry)


class SpecialistRoutingTests(unittest.TestCase):
    """F39: 연결할 수 있는 전문 스킬과 준비된 W 조회 절차."""

    def test_entry_lists_specialist_skills_and_ready_work_lookup(self):
        entry = read(REFS / "tdd-entry.md")
        for skill in ("gx-context", "gx-lens", "gx-research", "gx-visualize", "gx-tech-debt", "gx-tdd",
                      "gx-verify", "gx-cross-review", "gx-commit", "gx-pull-request", "gx-humanizer"):
            self.assertIn(f"`oh-my-gx:{skill}`", entry)
        self.assertIn("../../gx-context/scripts/plan.py", entry)
        self.assertTrue((REFS / "../../gx-context/scripts/plan.py").resolve().is_file())
        for marker in ("`ready`", "`blocked`", "`errors`"):
            self.assertIn(marker, entry)


class SkillEntryStructureTests(unittest.TestCase):
    """F29·F30·F17·F28·F36·F35: SKILL.md를 번호 단계와 표로 재구성하고 결과값별 처리를 둔다."""

    def setUp(self):
        self.text = read(WORK / "SKILL.md")

    def test_entry_is_small_numbered_and_keeps_lint_markers(self):
        self.assertLess(len(self.text.encode("utf-8")), 20000)
        steps = section(self.text, "## 진행 순서")
        self.assertGreaterEqual(len(re.findall(r"(?m)^[1-9]\. \*\*", steps)), 6)
        for marker in ('Skill("oh-my-gx:gx-tdd"', "--handoff", "--from-plan", "understand",
                       "references/codex-runtime.md", "references/planning.md", "references/handoff.md"):
            self.assertIn(marker, self.text)
        self.assertEqual(len(re.findall(r"\]\([^)]*reviewability\.md\)", self.text)), 1)
        self.assertNotIn("Phase 실행 루프", self.text)

    def test_every_route_action_has_a_handling_row(self):
        table = section(self.text, "## route 결과별 처리")
        for action in ROUTE_ACTIONS:
            with self.subTest(action=action):
                self.assertRegex(table, rf"(?m)^\|[^\n]*`{re.escape(action)}`[^\n]*\|")
        for field in ("requested-stop-at", "stale-pending-file", "{\"error\""):
            self.assertIn(field, table)

    def test_pending_question_is_compared_before_reuse_or_discard(self):
        changes = section(self.text, "## 진행 중 실행의 변경")
        for marker in ("pending-goal", "pending-run-id", "pending-phase", "이전 질문에 답하기",
                       "폐기하고 새 작업", "codex-question.py discard", "--reason"):
            self.assertIn(marker, changes)
        self.assertIn("discard", read(REFS / "codex-questions.md"))
        self.assertIn("/.dev/*/discarded-question-*.json", read(REFS / "dev-sharing.gitignore"))

    def test_commit_or_pr_only_is_an_endpoint_change_decision(self):
        changes = section(self.text, "## 진행 중 실행의 변경")
        endpoint = changes.split("**종료점 변경**", 1)[1].split("\n- ", 1)[0]
        for marker in ("커밋만", "PR만", "decisions.md", "stop-at", "reissue", "--change-source", "--resume"):
            self.assertIn(marker, endpoint)

    def test_legacy_runs_have_a_documented_exit_without_cycle(self):
        changes = section(self.text, "## 진행 중 실행의 변경")
        legacy = changes.split("**새 범위로 시작**", 1)[1].split("\n- ", 1)[0]
        for marker in ("새 브랜치", "워크트리", "새 run-id", "/oh-my-gx:gx-work"):
            self.assertIn(marker, legacy)
        self.assertNotRegex(self.text, r"gx-dev(?:로|를) (?:전환|사용)")

    def test_harness_note_names_plugin_root_and_python(self):
        note = self.text.split("**하네스 적응**", 1)[1].split("\n## ", 1)[0]
        for marker in ("`../../..`", "scripts/gx-work.py", "`python3`", "Windows"):
            self.assertIn(marker, note)


class HandoffContractDocTests(unittest.TestCase):
    """F04·F14·F16·F18·F25·F35·F42와 I2·I3·I4."""

    def setUp(self):
        self.text = read(REFS / "handoff.md")
        block = next(part for part in self.text.split("```json")[1:])
        self.example = json.loads(block.split("```", 1)[0])

    def test_schema_v2_example_uses_relative_pointers(self):
        self.assertEqual(self.example["schema-version"], 2)
        pointer = self.example["request-file"]
        self.assertFalse(pointer.startswith("/") or re.match(r"^[A-Za-z]:", pointer), pointer)
        self.assertTrue(pointer.startswith(".dev/" + self.example["run-id"] + "/"))
        for field in ("work-id", "execution-method", "model-profile", "mode"):
            self.assertIn(field, self.example)
        self.assertNotEqual(self.example["input-sha256"], self.example["entry-approval"]["scope-sha256"])
        for marker in ("프로젝트 루트 기준 POSIX 상대경로", "표시용", "v1"):
            self.assertIn(marker, self.text)
        self.assertNotIn(".dev/task/", self.text)

    def test_run_directory_and_run_id_owner(self):
        for marker in (".dev/<run-id>/", "^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$", "gx-work가 한 번 만들"):
            self.assertIn(marker, self.text)

    def test_reissue_is_the_exit_for_endpoint_change_and_relocation(self):
        for marker in ("reissue --handoff", "--change-source", "reissued-from-sha256", "relocated: true"):
            self.assertIn(marker, self.text)

    def test_request_handoff_blocks_on_blocking_unresolved_and_conflicts(self):
        rule = self.text.split("**요청 인계의 차단 규칙**", 1)[1].split("\n\n", 1)[0]
        for marker in ("`blocking: true`", "같은 topic", "`ready-for-tdd: false`"):
            self.assertIn(marker, rule)

    def test_project_root_rule_matches_tdd(self):
        for marker in ("git rev-parse --show-toplevel", "svn info --show-item wc-root"):
            self.assertIn(marker, self.text)

    def test_helper_section_names_platform_python_and_error_capture(self):
        helper = section(self.text, "## helper와 입력 검증")
        for marker in ("python3", "Windows", "exit 2", "오류 JSON을 인계 파일로 저장하지 않"):
            self.assertIn(marker, helper)

    def test_encoding_rule(self):
        self.assertIn("BOM 없는 UTF-8", self.text)


class ContextBoundaryTests(unittest.TestCase):
    """F18·F25·F27·F38·F41: gx-context의 run 위치·직접 호출 안내·재질문·임시 파일."""

    def test_intake_uses_run_directory_and_returns_work_id(self):
        intake = read(CONTEXT / "references/intake.md")
        self.assertIn(".dev/<run-id>/context-intake.json", intake)
        self.assertNotIn(".dev/{run-id}/", intake)
        returned = intake.split("## 반환과 종료", 1)[1]
        self.assertIn("work-id", returned)

    def test_direct_call_points_to_work_instead_of_claiming_handoff(self):
        intake = read(CONTEXT / "references/intake.md")
        self.assertIn("/oh-my-gx:gx-work", intake)
        self.assertIn("scripts/intake.py -", intake)
        p9 = read(CONTEXT / "modes/plan.md").split("### P-9. 안내", 1)[1]
        self.assertNotIn("다음: gx-work에 목표·종료 지점·원장/계획 포인터를 인계합니다.", p9)
        self.assertIn("/oh-my-gx:gx-work", p9)
        self.assertIn("/oh-my-gx:gx-work", read(CONTEXT / "SKILL.md"))

    def test_scan_confirmation_offers_cancel(self):
        a0 = read(CONTEXT / "SKILL.md").split("### A-0. 사용자 확인", 1)[1].split("### A-1.", 1)[0]
        self.assertIn('label: "취소"', a0)
        self.assertIn('"취소" →', a0)

    def test_named_targets_are_not_asked_again(self):
        main = read(CONTEXT / "SKILL.md")
        self.assertIn("요청에 이미 드러난 선택은 묻지 않는다", main)
        self.assertIn("요청에 갱신 항목이 드러나", read(CONTEXT / "modes/update.md"))
        self.assertIn("요청 문장에서", read(CONTEXT / "modes/sync.md").split("### E-1.", 1)[0])

    def test_stale_owner_references_are_removed(self):
        ignore = read(REFS / "dev-ignore-check.md")
        self.assertNotIn("gx-work·gx-tdd(phase-setup Step 6)", ignore)
        self.assertIn("gx-tdd(phase-setup Step 6)", ignore)
        self.assertNotIn("/gx-work·/gx-tdd가 PRD", read(CONTEXT / "modes/create.md"))
        self.assertNotIn("gx-work·gx-tdd의 AC 상한", read(CONTEXT / "modes/plan.md"))

    def test_dev_ignore_answer_is_reused_within_the_run(self):
        reuse = section(read(REFS / "dev-ignore-check.md"), "## 4. 같은 run의 결과 재사용")
        for marker in (".dev/<run-id>/decisions.md", "그대로 두기", "다시 묻"):
            self.assertIn(marker, reuse)


class ResearchOutputTests(unittest.TestCase):
    """F37: 조사 결과는 저장 요청이 있을 때만 파일과 .gitignore를 바꾼다."""

    def setUp(self):
        self.text = read(RESEARCH / "SKILL.md")

    def test_default_delivery_is_conversation(self):
        self.assertNotIn("스킬 실행 시 프로젝트 `.gitignore`에 `.research/` 항목이 없으면 자동 추가한다", self.text)
        delivery = section(self.text, "## 결과 전달 방식")
        for marker in ("gx-work", "저장하지 마", "대화", "--output"):
            self.assertIn(marker, delivery)

    def test_files_and_gitignore_only_in_save_mode(self):
        step0 = self.text.split("### Step 0", 1)[1].split("### Step 1", 1)[0]
        self.assertIn("저장 모드", step0)
        self.assertIn("대화 모드", step0)
        findings = self.text.split("**2-2b. WebSearch", 1)[1].split("**findings.md 형식:**", 1)[0]
        self.assertIn("저장 모드", findings)


class HelperSpecAlignmentTests(unittest.TestCase):
    """통합: G1 helper의 실제 인자·출력과 gx-work 문서가 어긋나지 않는지 확인한다."""

    def setUp(self):
        self.skill = read(WORK / "SKILL.md")
        self.handoff = read(REFS / "handoff.md")
        self.questions = read(REFS / "codex-questions.md")

    def test_git_safe_directory_is_documented_for_ownership_mismatch(self):
        route_line = re.search(r"`python <플러그인 루트>/scripts/gx-work\.py route[^`]+`", self.skill).group(0)
        self.assertIn("--git-safe-directory", route_line)
        helper_block = section(self.handoff, "## helper와 입력 검증", "\nstdout JSON")
        for command in ("route", "handoff --request", "validate-handoff", "reissue"):
            with self.subTest(command=command):
                line = next(l for l in helper_block.splitlines() if f"gx-work.py {command}" in l)
                self.assertIn("--git-safe-directory", line)
        self.assertIn("소유권", self.handoff)

    def test_route_answer_and_endpoint_flags_have_handling(self):
        for flag in ("entry-answer-recorded", "stop-at-change-required", "answered-question-set-id"):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.skill)

    def test_register_example_carries_goal_and_run_id(self):
        example = section(self.questions, "등록 입력 예:", "Windows PowerShell 예시:")
        payload = json.loads(re.search(r"\{.+\}", example).group(0))
        self.assertIn("goal", payload)
        self.assertIn("run_id", payload)
        self.assertIn(".dev/<branch-slug>", self.questions)

    def test_discard_refusal_reasons_match_helper(self):
        # 표의 같은 문구가 먼저 나오므로 절 시작 표식으로 자른다.
        discard = self.skill.split("- **미응답 질문 대조**", 1)[1].split("\n- **", 1)[0]
        for reason in ("lock", "pending 없음", "--reason"):
            with self.subTest(reason=reason):
                self.assertIn(reason, discard)
        # 형식이 깨진 pending도 원문을 보관하고 해제한다(코드 리뷰 Low, helper `malformed: true`).
        self.assertIn("malformed", discard)
        self.assertNotIn("형식 오류)면", discard)
        self.assertIn("malformed", self.questions)

    def test_reissue_and_blocking_details_match_helper(self):
        for phrase in ("`dropped-question-set-id`", "v2 인계는 위치가 바뀌어도", "종료점이 같으면 `--change-source`",
                       "읽기 전용 인계를 실행 인계로", "`blocking` 값이 없는", "프로젝트 루트 기준으로 해석", "`issues`"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.handoff)

    def test_svn_new_scope_uses_explicit_slug_end_to_end(self):
        route_line = re.search(r"`python <플러그인 루트>/scripts/gx-work\.py route[^`]+`", self.skill).group(0)
        self.assertIn("--slug", route_line)
        new_scope = self.skill.split("- **새 범위로 시작**", 1)[1].split("\n\n", 1)[0]
        for phrase in ("SVN", "--slug <새 slug>", "requested-slug"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, new_scope)

    def test_finished_run_commit_or_pr_is_reverified_not_sent_straight(self):
        # verify로 끝난 실행도 gx-tdd 종료점 변경으로 재검증한다(리뷰 High-1, test_codex_review_fixes).
        row = next(l for l in self.skill.splitlines() if l.startswith("| 커밋만·PR만"))
        self.assertIn("verify로 끝난", row)
        self.assertNotIn("재발급 없이", row)


if __name__ == "__main__":
    unittest.main()
