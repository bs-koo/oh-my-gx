from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_SKILL = ROOT / ".claude/skills/gx-context/SKILL.md"
CONTEXT_RULE = ROOT / ".claude/rules/context-docs.md"
STATUS_HEADER = "| ID | 요구사항 | AC | 상태 | PR |"


class ContextRequirementLedgerTests(unittest.TestCase):
    def read(self, path: Path) -> str:
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
        self.assertIn("ID가 없거나 유효하지 않거나 입력 안에서 중복", section)

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


if __name__ == "__main__":
    unittest.main()
