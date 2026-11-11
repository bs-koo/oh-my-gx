"""gx-tdd 질문 묶기·초안 보존·진행 안내·완료 단계(베이스 동기화·기존 실패) 문서 계약 회귀.

사용자 여정 검토(H2·H3·H7·M2·M6·M9·M10·M11·M12·M14·L5)와 실사용 세션 분석(F3·F4·F6·F8)에서
나온 변경을 지시문이 계속 담고 있는지 확인한다. 모델 행동 smoke는 아니다.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TDD = ROOT / ".claude/skills/gx-tdd"


def read(relative):
    return (TDD / relative).read_text(encoding="utf-8")


def section(text, start, end=None):
    tail = text.split(start, 1)[1]
    return tail.split(end, 1)[0] if end else tail


class QuestionBundlingTests(unittest.TestCase):
    def test_independent_questions_share_one_call(self):
        rules = section(read("references/interaction-contract.md"), "#### 변환 규칙", "#### 승인/수정 공통 패턴")
        self.assertNotIn("하나씩 순차 호출", rules)
        bundle = next(line for line in rules.splitlines() if "2개 이상" in line)
        for marker in ("독립", "한 호출로 묶는다", "Claude Code", "4개", "Codex", "3개", "앞 답에 따라"):
            self.assertIn(marker, bundle)

    def test_choice_descriptions_state_scale_and_reasks_show_the_change(self):
        rules = section(read("references/interaction-contract.md"), "#### 변환 규칙", "#### 승인/수정 공통 패턴")
        for marker in ("PR 수", "태스크 수", "순차·병렬", "예상 시간", "이전 답: … → 새 사실: …"):
            self.assertIn(marker, rules)

    def test_dialogue_loop_bundles_instead_of_one_by_one(self):
        loop = section(read("references/requirements-dialogue.md"), "## 2. 문답 루프", "## 3.")
        self.assertNotIn("**하나씩**", loop)
        self.assertIn("한 호출로 묶어", loop)

    def test_same_product_owner_is_resumed_when_the_harness_allows(self):
        loop = section(read("references/requirements-dialogue.md"), "## 2. 문답 루프", "## 3.")
        for marker in ("서브에이전트 재개", "새 디스패치", "fix loop"):
            self.assertIn(marker, loop)

    def test_prd_approval_joins_remaining_questions_with_a_short_body(self):
        step4 = section(read("phases/phase-requirements.md"), "**Step 4**", "## G-W-T 검증 게이트")
        self.assertIn("같은 호출에 묶는다", step4)
        self.assertIn("답을 반영해 승인", step4)
        self.assertIn("Other 자유 입력", step4)
        self.assertIn("짧게", step4)
        self.assertIn("한 호출로 묶는다", section(read("references/requirements-dialogue.md"), "## 4.", "## 5."))


class DraftPersistenceTests(unittest.TestCase):
    def test_prd_draft_is_saved_when_shown_and_removed_on_approval(self):
        text = read("phases/phase-requirements.md")
        step2 = section(text, "**Step 2**", "**Step 3**")
        for marker in ("prd.draft.md", 'current-step: "PRD 승인 대기"', "다시 디스패치하지 않고", "HANDOFF_READ_ONLY"):
            self.assertIn(marker, step2)
        save = section(text, "**Phase 완료 후 저장**", "**Phase 완료 보고")
        self.assertLess(save.index("prd.md`에 Write"), save.index("prd.draft.md"))
        self.assertIn("rm -f", save)

    def test_drafts_keep_open_questions_and_answer_pointers(self):
        # 초안 재개에서 미정 항목·부분 답이 사라지지 않도록 질문 목록과 답의 기록 위치를 함께 남긴다.
        heading = "`## 확인이 필요한 사항 (승인 전)`"
        step2 = section(read("phases/phase-requirements.md"), "**Step 2**", "**Step 3**")
        design = read("phases/phase-design.md")
        step4 = section(design, "**Step 4**", "**실제 필수 질문이나")
        resume = next(line for line in design.splitlines() if line.startswith("**승인 대기 초안 재개**"))
        for text in (step2, step4):
            for marker in (heading, '"확인이 필요한 사항"', "decisions.md", "`→ 답변: decisions.md`"):
                self.assertIn(marker, text)
        for text in (step2, resume):
            self.assertIn("답변 표시가 없는 항목만 다시 묻고", text)
            self.assertIn("Step 4의 답으로 이어 쓴다", text)
        for save in (section(read("phases/phase-requirements.md"), "**Phase 완료 후 저장**", "**Phase 완료 보고"),
                     section(design, "**Phase 완료 후 저장**", "**Phase 완료 보고")):
            self.assertIn(heading + " 절", save)
            self.assertIn("뺀다" if "prd.md" in save else "빼고", save)

    def test_resume_reuses_the_same_draft(self):
        resume = section(read("phases/setup-resume.md"), "**이어서 진행 시:**", "### 착수 기록 보정")
        for marker in ("PRD 승인 대기", "설계 승인 대기", "prd.draft.md", "design.draft.md", "다시 디스패치하지 않는다"):
            self.assertIn(marker, resume)

    def test_state_contract_documents_drafts(self):
        state = read("references/pipeline-state.md")
        storage = section(state, "### 문서 보관", "### 진행 상태 추적")
        for marker in ("prd.draft.md", "design.draft.md", "PRD 승인 대기", "초안을 지운다", "승인 근거가 아니다"):
            self.assertIn(marker, storage)


class ProfileOrderTests(unittest.TestCase):
    def test_phase_bootstrap_and_setup_share_profile_order(self):
        # L6: --phase 부트스트랩도 phase-setup Step 1.5처럼 핵심 모드 standard·workflowDefaults를 같은 자리에 둔다.
        bootstrap = next(line for line in read("SKILL.md").splitlines() if line.startswith("> 5. `MODEL_PROFILE`"))
        order = ["명시 --eco/--standard", "기존 state 값", "핵심 모드면 standard",
                 "workflowDefaults.modelProfile", "> modelProfile", "> standard"]
        positions = [bootstrap.index(item) for item in order]
        self.assertEqual(positions, sorted(positions))
        setup = section(read("phases/phase-setup.md"), "## Step 1.5:", "## Step 2:")
        items = [line for line in setup.splitlines() if re.match(r"\d\. ", line)]
        self.assertTrue(items[3].startswith("4. 핵심 모드 → `standard`"), items[3])
        self.assertIn("5·6의 설정값도 쓰지 않는다", items[3])
        self.assertIn("`workflowDefaults.modelProfile`", items[4])
        entry = (ROOT / ".claude/skills/gx-work/references/tdd-entry.md").read_text(encoding="utf-8")
        core = next(line for line in entry.splitlines() if line.startswith("- **핵심 모드의 프로파일**"))
        for marker in ("`standard`로 기록", "요청에서 프로파일을 밝혔으면 그 값", "`workflowDefaults.modelProfile`"):
            self.assertIn(marker, core)


class ProgressAndWordingTests(unittest.TestCase):
    def setUp(self):
        self.contract = read("references/interaction-contract.md")

    def test_entry_block_and_boundary_lines(self):
        progress = section(self.contract, "## 진행 안내", "## 사용자 메시지 문구")
        for marker in ("확인받을 지점", "테스트 실행", "전체:", "핵심:", "[구현 2/5] T2 실패 테스트 작성 중"):
            self.assertIn(marker, progress)

    def test_compaction_hint_after_design_and_pr(self):
        progress = section(self.contract, "## 진행 안내", "## 사용자 메시지 문구")
        hint = next(line for line in progress.splitlines() if "맥락 정리 안내" in line)
        for marker in ("설계 확정", "PR 생성", "/compact", "--resume", "W 작업 하나에 세션 하나"):
            self.assertIn(marker, hint)
        step6 = section(read("phases/phase-complete.md"), "## Step 6:")
        self.assertIn("진행 안내", step6)

    def test_user_messages_hide_internal_identifiers(self):
        wording = section(self.contract, "## 사용자 메시지 문구", "## 에러 처리")
        for marker in ("question-set-id", "지문 값", "state 필드명", "무엇이 막혔는지 — 다음에 할 일", "원문"):
            self.assertIn(marker, wording)
        restore = section(read("phases/setup-resume.md"), "### 0.05", "### 0.1")
        self.assertNotIn("질문 식별자가 빠졌음을 사용자에게 알린다", restore)
        self.assertIn("식별자 값 없이", restore)

    def test_long_commands_follow_the_test_execution_timeout(self):
        errors = section(self.contract, "## 에러 처리")
        self.assertNotIn("timeout: 300000", errors)
        self.assertIn("test-execution.md", errors)
        self.assertIn("600000", errors)
        self.assertIn("백그라운드", errors)


class InstructionVolumeTests(unittest.TestCase):
    def test_dialogue_contract_is_read_once_in_the_loop(self):
        skill = read("SKILL.md")
        loop = section(skill, "# 2. Phase별 순차 실행", "### Phase 파일 경로")
        self.assertNotIn('Read("references/requirements-dialogue.md")', loop)
        self.assertIn("처음 한 번", loop)
        self.assertIn("압축 뒤", loop)

    def test_rare_state_rules_moved_to_a_conditional_reference(self):
        state = read("references/pipeline-state.md")
        operations = read("references/pipeline-operations.md")
        for heading in ("### Diff 수집 규칙", "### Context Slicing 규칙", "### 정체 감지 + 에스컬레이션",
                        "### 베이스 브랜치 감지", "### 병렬 실행 규칙", "### verify 지문 계산·대조"):
            with self.subTest(heading=heading):
                self.assertIn(heading, operations)
                self.assertNotIn(heading, state)
        pointer = section(state, "### 조건부 운영 규칙")
        self.assertIn("(pipeline-operations.md)", pointer)
        for name in ("Diff 수집 규칙", "Context Slicing 규칙", "베이스 브랜치 감지", "정체 감지"):
            self.assertIn(name, pointer)
        self.assertNotIn('Read("references/pipeline-operations.md")', section(read("SKILL.md"), "## 필수 실행 계약 로드", "## Phase 라우팅"))

    def test_state_contract_shrank(self):
        size = len((TDD / "references/pipeline-state.md").read_bytes().replace(b"\r\n", b"\n"))
        self.assertLess(size, 28000)


class StateSchemaTests(unittest.TestCase):
    def setUp(self):
        self.state = read("references/pipeline-state.md")

    def test_new_fields_are_in_the_example_and_table(self):
        example = section(self.state, "```yaml\nphase: implement", "\n```")
        self.assertRegex(example, r"(?m)^known-failures: \[\]$")
        self.assertRegex(example, r"(?m)^test-plan-override: null$")
        for row in ("| `status` |", "| `known-failures` |", "| `test-plan-override` |", "| `current-step` 초안 값 |"):
            self.assertIn(row, self.state)
        self.assertIn("{ command, scope, reason }", self.state)
        self.assertIn("`cancelled`", self.state)

    def test_cancelled_lifecycle(self):
        rule = next(line for line in self.state.splitlines() if "**cancelled 수명주기**" in line)
        for marker in ("사용자", "응답으로만", "지우지 않고", "in_progress", "게이트", "다시 열기"):
            self.assertIn(marker, rule)
        resume = read("phases/setup-resume.md")
        flag = section(resume, "### `--resume` 플래그가 있는 경우", "### `--resume` 플래그가 없는 경우")
        self.assertIn("status: cancelled", flag)
        self.assertIn("다시 열기", flag)

    def test_known_failures_ledger_entry(self):
        ledger = section(self.state, "## Trust Ledger (신뢰 원장)", "---")
        self.assertIn("known-failures", ledger)


class CompletionPhaseTests(unittest.TestCase):
    def setUp(self):
        self.complete = read("phases/phase-complete.md")

    def test_base_sync_is_optional_and_sits_before_final_verify(self):
        self.assertLess(self.complete.index("## Step 4: 관련 문서"), self.complete.index("## Step 4.5: 베이스 동기화"))
        self.assertLess(self.complete.index("## Step 4.5: 베이스 동기화"), self.complete.index("## Step -1: verify 게이트"))
        sync = section(self.complete, "## Step 4.5: 베이스 동기화", "## Step -1: verify 게이트")
        for marker in ("git fetch", "merge-base --is-ancestor", "rev-list --count", "git merge --no-edit",
                       "그대로 검증", "병합 후 검증", "git merge --abort", "사용자에게 보고"):
            self.assertIn(marker, sync)
        for banned in ("rebase", "force push", "commit-tree", "reset --soft", "read-tree", "checkout-index"):
            self.assertIn(banned, sync)
        self.assertRegex(sync, r"(?:쓰지 않는다|대신하지 않는다)")

    def test_known_failures_only_block_new_failures(self):
        verify = section(self.complete, "## Step -1: verify 게이트", '**verify 회귀 수리** ("수정" 선택 시)')
        for marker in ("known-failures", "새 실패", "기존 실패 N건", "trust-ledger", "베이스에서 온 실패",
                       "기존 실패로 기록하고 진행"):
            self.assertIn(marker, verify)
        audit = section(self.complete, "### Step 2-1", "### Step 2-2")
        self.assertIn("기존 실패 N건(이번 변경과 무관)", audit)

    def test_session_method_repairs_in_session(self):
        repair = section(self.complete, '**verify 회귀 수리** ("수정" 선택 시)', "**Iron Law 위반 감지**")
        row = next(line for line in repair.splitlines() if line.startswith("   | 기존 테스트 실패"))
        for marker in ("execution-method: session", "세션 직접", "implementer", "테스트 파일 무변경"):
            self.assertIn(marker, row)

    def test_architecture_map_question_is_conditional(self):
        gate = section(self.complete, "## Step 5.5:", "AskUserQuestion(")
        condition = next(line for line in gate.splitlines() if line.startswith("**질문 조건**"))
        for marker in ("중형", "새 모듈", "한 줄", "gx-visualize"):
            self.assertIn(marker, condition)

    def test_conflicted_base_sync_resumes_without_merging_again(self):
        """M4: 재개는 다시 merge하지 않고 미해결 경로·하네스별 병합 커밋 마무리를 나눈다."""
        resume = section(self.complete, "**충돌 재개**", "1. `git fetch")
        for marker in ("다시 merge하지 않는다", "MERGE_HEAD", "git ls-files -u", "대기",
                       "Step 0의 스테이징보다 먼저", 'Skill(skill: "oh-my-gx:gx-commit"',
                       "Codex", "git commit --no-edit", "Step -1"):
            self.assertIn(marker, resume)
        sync = section(self.complete, "## Step 4.5: 베이스 동기화", "## Step -1: verify 게이트")
        self.assertIn("베이스 SHA", line_with(sync, "**병합 후 검증**"))

    def test_verify_stop_reports_base_lead_without_merging(self):
        intro = section(self.complete, "## Step 4.5: 베이스 동기화", "**충돌 재개**")
        rule = line_with(intro, "`stop-at: verify`")
        for marker in ("묻거나 병합하지 않는다", "N커밋 앞서 있음", "Step 6"):
            self.assertIn(marker, rule)

    def test_base_failures_become_known_only_with_a_base_run(self):
        """M5: 베이스 실패 판단만으로는 known-failures에 넣지 않는다."""
        option = line_with(section(self.complete, "## Step -1: verify 게이트", '**verify 회귀 수리** ("수정" 선택 시)'),
                           "기존 실패로 기록하고 진행")
        for marker in ("실행 근거", "git worktree add <임시경로> <베이스 SHA>", "git worktree remove <임시경로>",
                       "같은 테스트 ID가 실패", "이 선택지를 두지 않는다", "Codex"):
            self.assertIn(marker, option)
        self.assertNotIn("--detach", option)


class ImplementRecoveryContractTests(unittest.TestCase):
    def test_review_4a_ruling_approves_only_add_only_case_changes(self):
        """M6: 4a 기본 RGR Ruling은 add-only 변경표 승인이고, AC·범위 변경은 묻는다."""
        for path in ("references/implement-recovery.md", "references/core-replanning.md"):
            with self.subTest(path=path):
                rule = line_with(read(path), "4a 기본 RGR 수정의 Ruling")
                for marker in ("`add`", "변경표 승인으로 본다", "AC 문구·범위", "4a 예외", "실제 응답"):
                    self.assertIn(marker, rule)

    def test_parallel_lanes_share_build_roots_and_serialize_shared_test_resources(self):
        """M8: 같은 빌드 루트는 한 갈래, 같은 테스트 DB·포트는 실행 직렬화."""
        impl = read("phases/phase-implement.md")
        marking = line_with(impl, "**독립 갈래 표시**")
        for marker in ("settings.gradle(.kts)", "pom.xml", "워크스페이스 루트", "한 갈래"):
            self.assertIn(marker, marking)
        lanes = section(impl, "**독립 갈래 병렬 진행**", "### Step 2-R")
        self.assertIn("같은 테스트 DB·포트", lanes)
        self.assertIn("동시에 디스패치하지 않고", lanes)

    def test_codex_stop_answer_is_natural_language(self):
        gate = section(read("phases/phase-implement.md"), "### 레이어별 하네스 게이트", "### 기준선 사전 실행")
        stop = line_with(gate, '**"중단"**(직접 입력)')
        for marker in ("Codex", "codex-questions.md", "세 선택지만", "실제 응답"):
            self.assertIn(marker, stop)

    def test_baseline_records_counts_for_known_failure_comparison(self):
        gate = section(read("phases/phase-implement.md"), "## Step 0.5:", "### 레이어별 하네스 게이트")
        self.assertIn("record --baseline", line_with(gate, "동일 실행·동일 코드"))
        self.assertIn("record --baseline", line_with(gate, "**계획 helper 실패**"))


def line_with(text, marker):
    return next(line for line in text.splitlines() if marker in line)


if __name__ == "__main__":
    unittest.main()
