from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_SKILL = ROOT / ".claude/skills/gx-context/SKILL.md"
CONTEXT_RULE = ROOT / ".claude/rules/context-docs.md"
DEV_SETUP = ROOT / ".claude/skills/gx-dev/phases/phase-setup.md"
TDD_SETUP = ROOT / ".claude/skills/gx-tdd/phases/phase-setup.md"
STATUS_HEADER = "| ID | 요구사항 | AC | 상태 | PR |"


class ContextRequirementLedgerTests(unittest.TestCase):
    def context_bundle(self) -> str:
        directory = CONTEXT_SKILL.parent
        ordered = [
            directory / "SKILL.md",
            directory / "modes/create.md",
            directory / "modes/from-document.md",
            directory / "modes/update.md",
            directory / "modes/sync.md",
            directory / "modes/plan.md",
        ]
        return "\n".join(path.read_text(encoding="utf-8") for path in ordered)

    def read(self, path: Path) -> str:
        if path == CONTEXT_SKILL:
            return self.context_bundle()
        return path.read_text(encoding="utf-8")

    def test_status_template_has_canonical_ledger(self):
        text = self.read(CONTEXT_SKILL)
        self.assertIn(STATUS_HEADER, text)
        self.assertIn("|---|---|---|---|---|", text)
        self.assertIn("🚫 폐기", text)

    def test_context_rule_declares_same_schema(self):
        text = self.read(CONTEXT_RULE)
        self.assertIn(STATUS_HEADER, text)
        self.assertIn("FR-N", text)
        self.assertIn("NFR-N", text)

    def test_from_mode_persists_requirements_before_plan(self):
        text = self.read(CONTEXT_SKILL)
        producer = text.index("### C-4-1. 요구사항 원장 반영")
        planner = text.index("### C-5. 작업 계획")
        self.assertLess(producer, planner)
        section = text[producer:planner]
        for phrase in (
            "LEDGER_REQUIREMENTS",
            "기존 ID·AC·상태·PR을 유지",
            "삭제된 번호를 재사용하지 않는다",
            "승인한 경우에만 `🚫`",
            "C-5는 `LEDGER_REQUIREMENTS`의 ID",
        ):
            self.assertIn(phrase, section)

    def test_new_context_does_not_drop_extracted_requirements(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4. context 생성"):text.index("### C-5. 작업 계획")]
        self.assertIn("B-5~B-11", section)
        self.assertIn("C-4-1을 반드시 실행", section)

    def test_from_mode_preserves_valid_unused_input_id(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4-1. 요구사항 원장 반영"):text.index("### C-5. 작업 계획")]
        self.assertIn("기존 원장에 없는 유효하고 고유한 입력 ID는 그대로 사용", section)
        self.assertIn("`FR-N`·`NFR-N` 형식", section)
        self.assertIn("`NFR-2`는 그대로 유지", section)
        self.assertIn("유효하지 않거나 입력 안에서 중복된 ID는 먼저 제거하여 ID 없는 후보로 정규화", section)

    def test_both_matching_modes_preserve_metadata_before_edit(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4-1. 요구사항 원장 반영"):text.index("### C-5. 작업 계획")]
        match = section.index("ID 일치와 핵심 문장 일치 모두")
        compare = section.index("모든 기존 행과 비교")
        edit = section.index("Edit으로")
        reread = section.index("저장한 표를 다시 읽어")
        self.assertLess(match, compare)
        self.assertLess(compare, edit)
        self.assertLess(edit, reread)
        self.assertIn("기존 ID·AC·상태·PR을 유지", section[match:edit])
        self.assertIn("변경되면 Edit하지 않는다", section[compare:edit])

    def test_final_ledger_array_matches_saved_rows_before_plan(self):
        text = self.read(CONTEXT_SKILL)
        producer = text.index("### C-4-1. 요구사항 원장 반영")
        planner = text.index("### C-5. 작업 계획")
        section = text[producer:planner]
        update = section.index("각 객체를 최종 `{ id, type, text, ac, status, pr }`로 갱신")
        equality = section.index("저장한 표의 행과 `LEDGER_REQUIREMENTS`가 일치")
        self.assertLess(update, equality)
        self.assertIn("각 객체의 id·type·text·ac·status·pr", section[equality:])
        self.assertIn("일치하지 않으면 C-5로 진행하지 않는다", section[equality:])

        plan_section = text[planner:]
        self.assertIn("`LEDGER_REQUIREMENTS`의 요구사항 항목", plan_section)

    def test_preserved_and_idless_inputs_share_reserved_id_set(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4-1. 요구사항 원장 반영"):text.index("### C-5. 작업 계획")]
        reserve = section.index("`RESERVED_LEDGER_IDS`")
        allocate = section.index("자동 ID를 할당")
        edit = section.index("Edit으로")
        self.assertLess(reserve, allocate)
        self.assertLess(allocate, edit)
        for phrase in (
            "기존 원장의 모든 ID와 입력에서 유효하고 고유한 ID를 먼저 예약",
            "예약 집합의 유형별 최댓값 다음 번호",
            "할당 즉시 `RESERVED_LEDGER_IDS`에 추가",
            "기존 `FR-1` + 입력 `FR-2` + ID 없는 FR → `FR-2`, `FR-3`",
            "Edit 전에 제안 표의 ID 중복",
        ):
            self.assertIn(phrase, section)

    def test_invalid_and_duplicate_input_ids_match_idless_before_allocation(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### C-4-1. 요구사항 원장 반영"):text.index("### C-5. 작업 계획")]
        normalize = section.index("유효하지 않거나 입력 안에서 중복된 ID는 먼저 제거하여 ID 없는 후보로 정규화")
        match = section.index("기존 행 하나와 후보 하나만 일대일로 연결")
        allocate = section.index("미매칭 후보에만 자동 ID를 할당")
        self.assertLess(normalize, match)
        self.assertLess(match, allocate)
        for phrase in (
            "`REQ-42`로 같은 문서를 다시 분석해도 핵심 문장이 같으면 기존 FR/NFR ID를 유지",
            "중복된 `FR-1` 후보 둘을 하나의 기존 행에 모두 매칭하지 않는다",
        ):
            self.assertIn(phrase, section)

    def test_sync_uses_persisted_cursor(self):
        text = self.read(CONTEXT_SKILL)
        for phrase in (
            "<!-- gx-sync",
            "git-head:",
            "svn-revision:",
            "pr-merged-at:",
            "${SYNC_GIT_HEAD}..${CANDIDATE_GIT_HEAD}",
            "분석·명령 실패 시 cursor를 갱신하지 않는다",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("git log --oneline -20", text)

    def test_initial_sync_searches_ids_across_history(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        self.assertIn("각 pending FR/NFR/AC ID를 전체 이력", section)
        self.assertIn("설명 키워드는 최근 100건", section)

    def test_sync_preflight_validates_cursors_and_freezes_upper_bounds(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-1. 사전 확인"):text.index("### E-2. git 히스토리 분석")]
        for phrase in (
            "40자리 hexadecimal",
            "git cat-file -e \"${SYNC_GIT_HEAD}^{commit}\"",
            "10진수 숫자",
            "엄격한 UTC ISO 8601",
            "실제 UTC 날짜·시각으로 파싱",
            "검증 실패한 cursor를 명령 인자로 사용하지 않는다",
            "CANDIDATE_GIT_HEAD",
            "CANDIDATE_SVN_REVISION",
            "CANDIDATE_PR_SYNC_AT",
        ):
            self.assertIn(phrase, section)

    def test_git_sync_distinguishes_merge_base_exit_codes_and_matches_full_message(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        for phrase in (
            "종료 코드 `0`",
            "종료 코드 `1`",
            "종료 코드 `2` 이상",
            "branch/rewrite",
            "`%B`",
            "${SYNC_GIT_HEAD}..${CANDIDATE_GIT_HEAD}",
            "`(^|[^A-Za-z0-9-])<ID>($|[^A-Za-z0-9-])`",
        ):
            self.assertIn(phrase, section)

    def test_svn_sync_uses_exclusive_lower_bound_and_rechecks_xml_message(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        for phrase in (
            "SYNC_SVN_REVISION + 1",
            "${SVN_FROM_REVISION}:${CANDIDATE_SVN_REVISION}",
            "--xml",
            "메시지에서 exact token을 재검증",
        ):
            self.assertIn(phrase, section)

    def test_pr_sync_paginates_complete_bounded_window_with_body(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        for phrase in (
            "`gh api --paginate`",
            "모든 page",
            "number·title·body·html_url·merged_at",
            "start <= merged_at < candidate",
            "제목·본문",
        ):
            self.assertIn(phrase, section)
        self.assertNotIn("gh pr list --state merged", section)

    def test_pr_source_requires_git_even_when_gh_is_available(self):
        text = self.read(CONTEXT_SKILL)
        preflight = text[text.index("### E-1. 사전 확인"):text.index("### E-2. git 히스토리 분석")]
        analysis = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        update = text[text.index("### E-4. status.md 갱신"):text.index("### E-5. 완료 안내")]
        self.assertIn("`ACTIVE_VCS = git`이고 gh를 사용할 수 있을 때만 `PR_SOURCE_ACTIVE = true`", preflight)
        self.assertIn("`PR_SOURCE_ACTIVE = true`일 때만 `CANDIDATE_PR_SYNC_AT`", preflight)
        self.assertIn("`PR_SOURCE_ACTIVE = true`일 때만 PR을 조회", analysis)
        self.assertIn("svn: 건너뜀 (PR 개념 없음)", analysis)
        self.assertIn("SVN 분석과 cursor 처리는 정상적으로 계속", analysis)
        self.assertIn("`PR_SOURCE_ACTIVE = true`인 경우 PR의 모든 page 처리가 성공했을 때만", update)

    def test_context_tree_describes_canonical_three_state_ledger(self):
        text = self.read(CONTEXT_RULE)
        self.assertIn("status.md          ← 정본 FR/NFR별 3상태 원장", text)
        self.assertNotIn("구현 추적 (AC별 ✅/⬜)", text)

    def test_sync_advances_frozen_candidates_only_after_complete_success(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-4. status.md 갱신"):text.index("### E-5. 완료 안내")]
        for phrase in (
            "CANDIDATE_GIT_HEAD",
            "CANDIDATE_SVN_REVISION",
            "CANDIDATE_PR_SYNC_AT",
            "모든 page 처리",
            "검증 실패",
            "기존 cursor를 유지",
        ):
            self.assertIn(phrase, section)

    def test_sync_rejects_svn_cursor_ahead_of_candidate(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-1. 사전 확인"):text.index("### E-2. git 히스토리 분석")]
        for phrase in (
            "SYNC_SVN_REVISION <= CANDIDATE_SVN_REVISION",
            "SVN cursor 역전",
            "정상 빈 범위로 처리하지 않는다",
            "기존 cursor를 보존",
        ):
            self.assertIn(phrase, section)

    def test_sync_rejects_pr_cursor_after_candidate(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-1. 사전 확인"):text.index("### E-2. git 히스토리 분석")]
        for phrase in (
            "SYNC_PR_MERGED_AT <= CANDIDATE_PR_SYNC_AT",
            "PR cursor 역전",
            "정상 빈 범위로 처리하지 않는다",
            "기존 cursor를 보존",
        ):
            self.assertIn(phrase, section)

    def test_exact_id_matching_is_case_insensitive_without_prefix_collisions(self):
        text = self.read(CONTEXT_SKILL)
        section = text[text.index("### E-2. git 히스토리 분석"):text.index("### E-3. 매칭 결과")]
        for phrase in (
            "Git/SVN/PR 모두",
            "pending ID와 입력 텍스트를 ASCII 대문자로 동일하게 정규화",
            "`fr-1`은 `FR-1`과 일치",
            "`NFR-1`이나 `FR-10`과 일치하지 않는다",
        ):
            self.assertIn(phrase, section)

    def test_context_uses_shared_svn_repository_identity(self):
        text = self.read(CONTEXT_SKILL)
        producer = text[text.index("### A-3. 초안 생성"):text.index("### A-4. 사용자 검토")]
        consumers = (self.read(DEV_SETUP), self.read(TDD_SETUP))
        for phrase in (
            "`svn info --show-item url` 종료 코드 != 0이면 진단 후 중단",
            "성공했지만 URL·ID가 비거나 모호하면 경고 후 `basename(PROJECT_ROOT)`",
        ):
            self.assertIn(phrase, producer)
            for consumer in consumers:
                self.assertIn(phrase, consumer)
        for phrase in (
            "svn info --show-item url",
            "trunk",
            "branches/<name>",
            "tags/<name>",
            "REPOSITORY_ID",
            "basename(PROJECT_ROOT)",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("svn info --show-item repos-root-url", text)


class ContextPlanSyncTests(unittest.TestCase):
    """plan.md가 어느 모드로 들어와도 원장과 맞춰지는지 확인하는 계약 검사."""

    directory = CONTEXT_SKILL.parent

    def text(self, relative: str) -> str:
        return (self.directory / relative).read_text(encoding="utf-8")

    def test_every_mode_ends_with_plan_sync(self):
        main = self.text("SKILL.md")
        section = main.split("## 작업 계획 마무리", 1)[1].split("\n## ", 1)[0]
        self.assertIn('`Read("modes/plan.md")`', section)
        self.assertIn("**항상**", section)
        self.assertIn("plan.md나 작업 계획을 말하지 않았어도 실행", section)
        self.assertIn("중간에 취소한 경우가 아니면", section)

    def test_requirement_input_routes_to_document_mode_before_update(self):
        main = self.text("SKILL.md")
        table = main.split("## 모드 자동 판단", 1)[1].split("**선택 모드 질문**", 1)[0]
        self.assertIn("처음 맞는 행 하나만", table)
        rows = [line for line in table.splitlines() if line.startswith("| ") and line[2].isdigit()]
        modes = [row.split("|")[3].strip() for row in rows]
        self.assertEqual(
            modes,
            ["**동기화**", "**스캔 → 문서 기반**", "**문서 기반**", "**스캔**", "**갱신**", "**신규**", "**선택**"],
        )
        self.assertIn("요구사항 입력 있음 + `context/` 폴더 없음", rows[1])
        self.assertIn("대상 도메인이 이미 있어도 이 모드다", rows[2])

    def test_inline_requirement_text_is_not_parsed_as_domain(self):
        main = self.text("SKILL.md")
        parse = main.split("## 인자 파싱", 1)[1].split("## 수칙", 1)[0]
        self.assertIn("여러 단어로 된 문장·목록이면 **요구사항 본문**", parse)
        self.assertIn("이번 사용자 메시지에 요구사항 문장이나 요구사항 문서 경로가 있으면", parse)
        self.assertIn("`REQUIREMENT_INPUT`", parse)

    def test_selection_and_update_offer_requirement_entry(self):
        main = self.text("SKILL.md")
        self.assertIn('label: "요구사항 추가 (Recommended)"', main)
        update = self.text("modes/update.md")
        self.assertIn('label: "요구사항 추가·변경"', update)
        self.assertIn('`Read("modes/from-document.md")`의 C-1부터', update)
        self.assertIn("`INPUT_SCOPE`를 `추가분`", update)

    def test_description_triggers_on_requirements_and_plan(self):
        front = self.text("SKILL.md").split("---", 2)[1]
        for phrase in (".dev/plan.md", "요구사항 추가", "작업 나눠줘", "plan.md를 말하지 않아도"):
            self.assertIn(phrase, front)

    def test_plan_sync_reconciles_ledger_not_only_this_input(self):
        plan = self.text("modes/plan.md")
        collect = plan.split("### P-1. 수집", 1)[1].split("### P-2. 대조", 1)[0]
        self.assertIn("모든 `context/{도메인}/status.md`", collect)
        self.assertIn("`{도메인}:FR-N`", collect)
        compare = plan.split("### P-2. 대조", 1)[1].split("### P-3.", 1)[0]
        for name in ("`UNASSIGNED`", "`DISCARD_CANDIDATES`", "`DONE_CANDIDATES`", "`BROKEN_REFS`"):
            self.assertIn(name, compare)
        self.assertIn("**미배정이 1건이어도 계획에 넣는다.**", compare)
        self.assertNotIn("2건 이상", plan)

    def test_discard_requires_ledger_tombstone_and_full_scope(self):
        plan = self.text("modes/plan.md")
        replan = plan.split("### P-6.", 1)[1].split("### P-7.", 1)[0]
        self.assertIn("폐기는 원장의 `🚫`만 근거로 삼는다", replan)
        self.assertIn("최댓값 다음 번호를 쓰고 폐기된 번호를 다시 쓰지 않는다", replan)
        document = self.text("modes/from-document.md")
        ledger = document.split("### C-4-1. 요구사항 원장 반영", 1)[1].split("### C-5.", 1)[0]
        self.assertIn("`INPUT_SCOPE`가 `전체본`일 때만", ledger)
        self.assertIn("`추가분`이면 입력에 없는 기존 행은 판정하지 않고 그대로 둔다", ledger)

    def test_saved_plan_covers_every_open_requirement_once(self):
        plan = self.text("modes/plan.md")
        save = plan.split("### P-8. 저장", 1)[1].split("### P-9.", 1)[0]
        self.assertIn("원장의 모든 `⬜` 요구사항이 `폐기`가 아닌 행 하나에만 들어 있다", save)
        self.assertIn("**기존 파일이 있으면 Write를 쓰지 않는다.**", save)

    def test_document_mode_splits_requirements_by_domain(self):
        document = self.text("modes/from-document.md")
        analysis = document.split("### C-2. 내용 분석", 1)[1].split("### C-3.", 1)[0]
        self.assertIn("요구사항마다 속할 도메인을 정한다", analysis)
        frames = document.split("#### C-3-2.", 1)[1].split("### C-4.", 1)[0]
        self.assertIn("**새 도메인**으로 정한 도메인마다", frames)
        handoff = document.split("### C-5. 작업 계획", 1)[1]
        self.assertIn('`Read("modes/plan.md")`', handoff)

    def test_scan_without_requirements_asks_before_skipping_plan(self):
        plan = self.text("modes/plan.md")
        entry = plan.split("### P-0. 진입 판단", 1)[1].split("### P-1.", 1)[0]
        self.assertIn("스캔 또는 신규 모드였다면 요구사항이 있는지 묻는다", entry)
        self.assertIn('`Read("modes/from-document.md")`의 C-1~C-4-1', entry)

    def test_sync_never_exits_before_plan_sync(self):
        sync = self.text("modes/sync.md")
        preflight = sync.split("### E-1. 사전 확인", 1)[1].split("### E-2.", 1)[0]
        self.assertNotIn("출력 후 종료\n", preflight)
        self.assertIn("E-5로 간다", preflight)
        self.assertIn("작업 계획 마무리는 실행한다", preflight)
        final = sync.split("### E-5. 완료 안내", 1)[1]
        self.assertIn("종료하지 않고 SKILL.md의 작업 계획 마무리로 넘어간다", final)

    def test_in_progress_row_completes_only_with_branch_evidence(self):
        plan = self.text("modes/plan.md")
        compare = plan.split("### P-2. 대조", 1)[1].split("### P-3.", 1)[0]
        rule = compare.split("**진행 행의 완료 판정**", 1)[1]
        for phrase in (
            "git ls-remote --heads origin {브랜치}",
            "git merge-base --is-ancestor {해시} HEAD",
            "`status: completed`",
            "판정하지 못한 행은 P-7에서",
        ):
            self.assertIn(phrase, rule)
        replan = plan.split("### P-6.", 1)[1].split("### P-7.", 1)[0]
        self.assertIn("진행 행 완료 판정을 통과하고 사용자가 승인하면 `완료`", replan)

if __name__ == "__main__":
    unittest.main()
