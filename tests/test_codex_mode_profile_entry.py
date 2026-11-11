"""개발 시작 전 모드(전체/핵심)·프로파일(표준/에코) 질문과 추천 기준 회귀 (v3.2.0).

v2.0.0에서 "매 요청마다 모드·프로파일을 묻지 않는다"로 바뀌어, 요청에 미리 적지 않으면 선택할 기회가 없었다.
gx-work 진입 질문과 직접 gx-tdd 시작 시 정해지지 않은 항목만 한 번 묻고, 작업 경중 기준으로 추천한다.
에코를 고를 수 있을 때 세션이 상위 등급 모델이면 절감 범위를 안내한다. 종료점 추천은 pr이다.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
ENTRY = SKILLS / "gx-work/references/tdd-entry.md"
ROUTING = SKILLS / "gx-tdd/references/intent-routing.md"
IMPLEMENT = SKILLS / "gx-tdd/phases/phase-implement.md"
STATE = SKILLS / "gx-tdd/references/pipeline-state.md"


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


class ExecutionMethodRecommendationTests(unittest.TestCase):
    def test_method_recommendation_has_criteria(self):
        step = section(read(IMPLEMENT), "### 1.2 계획 검토·실행방법 확인", "### 1.3")
        rule = section(step, "**추천 기준**", "\n\n")
        for marker in ("서브에이전트", "태스크", "컨텍스트", "에코"):
            self.assertIn(marker, rule)


if __name__ == "__main__":
    unittest.main()
