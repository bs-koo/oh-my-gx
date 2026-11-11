"""gx-tdd 구현·설계 단계 일괄 개선(H2·F2·M1·F3·M4·M10·M14·F7·F12·F4·M2·M12)의 문서 계약 검사.

지시문은 모델이 읽고 따르는 계약이라 문구가 곧 동작이다. 실제 모델 세션의 질문 UI·도구 호출은
이 검사가 증명하지 않는다.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TDD = ROOT / ".claude/skills/gx-tdd"


def read(relative: str) -> str:
    return (TDD / relative).read_text(encoding="utf-8")


def section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin:text.index(end, begin + len(start))]


def option_labels(block: str) -> list[str]:
    return re.findall(r'\{\s*label:\s*"([^"]+)"', block)


class BaselineTests(unittest.TestCase):
    def test_h2_known_failures_are_recorded_for_verify(self):
        gate = section(read("phases/phase-implement.md"), "## Step 0.5:", "### 레이어별 하네스 게이트")
        rule = next(line for line in gate.splitlines() if "**기준 GREEN 확인**" in line)
        for phrase in ("기존 실패를 알고 진행", "`known-failures`", "새 실패만", "test-execution.md", "status: cancelled"):
            self.assertIn(phrase, rule)

    def test_f2_helper_failure_asks_once_with_config_fix_and_records_override(self):
        gate = section(read("phases/phase-implement.md"), "## Step 0.5:", "### 레이어별 하네스 게이트")
        rule = next(line for line in gate.splitlines() if line.startswith("**계획 helper 실패**"))
        for phrase in ("즉흥", "config.json", "수정안", "**한 번만**", "`test-plan-override`",
                       "command, scope, reason", "verify"):
            self.assertIn(phrase, rule)

    def test_f7_baseline_finishes_before_red_and_only_env_prep_starts_early(self):
        impl = read("phases/phase-implement.md")
        pre = section(impl, "### 기준선 사전 실행", "## Step 1:")
        self.assertIn("기준선 측정이 끝난 뒤에 RED", pre)
        self.assertIn("phase-design Step 0", pre)
        self.assertNotIn("run_in_background: true", pre)
        design = read("phases/phase-design.md")
        prep = next(line for line in design.splitlines() if line.startswith("**환경 준비 병행**"))
        for phrase in ("백그라운드", "테스트·빌드는 시작하지 않는다", "execution-log", "지원하지 않는 하네스"):
            self.assertIn(phrase, prep)


class ApprovalTests(unittest.TestCase):
    def test_m1_small_design_bundles_plan_and_method_into_design_approval(self):
        design = read("phases/phase-design.md")
        bundle = next(line for line in design.splitlines() if "**소형 설계의 계획·실행 방법 묶음**" in line)
        for phrase in ("implementation-plan.md", "core-planning.md", "1.2의 세 선택지", "계획 해시가 표시 때와 같을 때만",
                       "plan-approved-*", "execution-method-*", "중형·대형이면 묶지 않고", "design_approval"):
            self.assertIn(phrase, bundle)
        review = section(read("phases/phase-implement.md"), "### 1.2 계획 검토", "### 1.3")
        self.assertIn("phase-design Step 4", review)
        self.assertIn("중형·대형은 아래 질문을 따로 묻는다", review)
        self.assertIn("전체 모드의 소형 설계도 같은 결합 방식을 재사용", read("references/core-planning.md"))

    def test_f3_design_confirmation_is_bundled_with_remaining_decisions_but_kept(self):
        step4 = section(read("phases/phase-design.md"), "**Step 4**:", "**2회 반복 후**:")
        self.assertIn("한 호출로 묶는다", step4)
        self.assertIn("승인 게이트는 없애지 않는다", step4)
        self.assertIn("승인은 갱신된 설계에서 다시 받는다", step4)

    def test_f12_task_guard_always_recommends_regrouping_first(self):
        guard = section(read("phases/phase-implement.md"), "### 1.15 태스크 수 가드", "### 1.2 계획 검토")
        self.assertIn("추천은 항상 `AC 묶어서 재분해`다", guard)
        labels = option_labels(guard)
        self.assertEqual(labels[0], "AC 묶어서 재분해 (Recommended)")
        self.assertEqual(sum("(Recommended)" in label for label in labels), 1)


class HarnessGateTests(unittest.TestCase):
    def test_m4_server_side_rewrite_is_offered_and_needs_confirmation(self):
        gate = section(read("phases/phase-implement.md"), "### 레이어별 하네스 게이트", "### 기준선 사전 실행")
        labels = option_labels(gate)
        self.assertIn("서버 동작으로 AC 재작성", labels)
        self.assertTrue(2 <= len(labels) <= 3, labels)
        rule = next(line for line in gate.splitlines() if line.startswith('- **"서버 동작으로 AC 재작성"**'))
        for phrase in ("확인 전에는 RED를 시작하지 않는다", "재승인", "prd.md"):
            self.assertIn(phrase, rule)
        self.assertIn('**"중단"**(직접 입력)', gate)


class DraftTests(unittest.TestCase):
    def test_m10_design_draft_is_saved_on_display_and_reused_on_resume(self):
        design = read("phases/phase-design.md")
        step1 = next(line for line in design.splitlines() if line.startswith("**Step 1**"))
        self.assertIn("design.draft.md", step1)
        resume = next(line for line in design.splitlines() if line.startswith("**승인 대기 초안 재개**"))
        for phrase in ("설계 승인 대기", "다시 부르지 않는다", "확인 질문만 다시"):
            self.assertIn(phrase, resume)
        self.assertIn('`current-step`을 `"설계 승인 대기"`로 갱신', design)
        save = section(design, "**Phase 완료 후 저장**", "**Phase 완료 보고")
        self.assertIn("초안 파일은 지운다", save)


class ExecutionTests(unittest.TestCase):
    def test_m14_session_method_repairs_boundary_regression_in_session(self):
        step = section(read("phases/phase-implement.md"), "## Step 3.5:", "## Step 4:")
        for phrase in ("execution-method: session", "세션이", "implementer **수리 모드**",
                       "테스트 파일 무변경 확인", "수리 1회 상한"):
            self.assertIn(phrase, step)

    def test_f7_independent_lanes_are_marked_recommended_and_scoped(self):
        impl = read("phases/phase-implement.md")
        table = section(impl, "### 1.1 태스크 표 생성", "### 1.15")
        self.assertIn("**독립 갈래 표시**", table)
        self.assertIn("TYPE:RELROOT", table)
        rule = section(section(impl, "### 1.2 계획 검토", "### 1.3"), "**추천 기준**", "\n\n")
        self.assertIn("독립 갈래", rule)
        self.assertIn("실제 응답으로만", rule)
        lanes = next(line for line in impl.splitlines() if line.startswith("**독립 갈래 병렬 진행**"))
        self.assertIn("execution-method: subagents", lanes)
        scope = section(impl, "**독립 갈래 병렬 진행**", "### Step 2-R")
        self.assertIn("git status --porcelain -- {RELROOT}", scope)
        self.assertIn("같은 프로젝트의 테스트·빌드를 동시에 시작하지 않는다", scope)
        forbidden = section(impl, "## 금지 사항", "위반 감지 시")
        self.assertIn("독립 갈래 병렬만 예외", forbidden)

    def test_f4_orchestrator_reads_tails_not_full_logs(self):
        prep = next(line for line in read("phases/phase-implement.md").splitlines()
                    if line.startswith("**진입 준비**"))
        self.assertIn("전문을 읽지 않는다", prep)
        self.assertIn("실패 목록", prep)


class WordingTests(unittest.TestCase):
    def test_m2_user_facing_questions_spell_out_internal_terms(self):
        impl = read("phases/phase-implement.md")
        method = section(impl, "### 1.2 계획 검토", "### 1.3")
        block = method[method.index("AskUserQuestion("):]
        self.assertNotIn("GREEN·REFACTOR", block[:block.index("multiSelect")])
        guard = section(impl, "### 1.15 태스크 수 가드", "### 1.2 계획 검토")
        self.assertIn("수용 기준(AC)", guard)
        gate = section(impl, "### 레이어별 하네스 게이트", "### 기준선 사전 실행")
        self.assertIn("수용 기준(AC)", gate)
        self.assertIn("표시한 수용 기준(AC)", read("references/core-planning.md"))
        self.assertIn("내부 식별자는 decisions.md 기록에만", read("references/core-planning.md"))


class RulingTests(unittest.TestCase):
    def test_review_4a_behavior_defect_defaults_to_rgr_fix(self):
        rulings = section(read("phases/phase-implement.md"), "## 판정 기록 (Rulings)", "## 금지 사항")
        intro = rulings.split("\n\n", 2)[1]
        self.assertIn("4a(동작 결함)", intro)
        self.assertIn("범위·AC를 바꿀 때만 묻는다", intro)
        self.assertNotIn("동작 결함의 RGR 여부", intro)
        self.assertIn("| phase-review 4a 동작 결함 | RGR로 수정 | 수정이 범위·AC를 바꾸면 묻는다 |", rulings)


class SplitTests(unittest.TestCase):
    def test_m12_recovery_paths_live_in_conditional_reference(self):
        impl = read("phases/phase-implement.md")
        recovery = read("references/implement-recovery.md")
        for heading in ("## 1. 재계획 공통", "## 2. 하네스 게이트의 AC 제외", "## 3. 재개 (`--resume`)"):
            self.assertIn(heading, recovery)
        for moved in ("구 세대 전환 재개", "하네스 부재 AC 제외", "재계획의 새 값 채택"):
            self.assertIn(moved, recovery)
            self.assertNotIn(moved, impl)
        resume = section(impl, "## --resume 호환", "## 판정 기록")
        self.assertIn("../references/implement-recovery.md", resume)
        self.assertIn("§3", resume)
        self.assertTrue((TDD / "phases" / "../references/implement-recovery.md").resolve().is_file())
        self.assertLess(len(impl.replace("\r\n", "\n").encode("utf-8")), 92000)

    def test_m12_fix_loop_is_reread_only_after_compaction_or_resume(self):
        loop = section(read("phases/phase-implement.md"), "**fix loop (실패 시", "| 라운드 |")
        self.assertIn("처음 진입할 때 한 번", loop)
        self.assertIn("컨텍스트 압축 뒤나 재개 때는 디스크에서 다시 읽어", loop)
        self.assertNotIn("매 라운드 이 fix loop 절을 디스크에서 다시 읽어", loop)


if __name__ == "__main__":
    unittest.main()
