"""두 하네스가 gx-lens의 같은 읽기 전용·근거·분기 계약에 도달하는지 검사한다."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LENS = ROOT / ".claude/skills/gx-lens"


class LensSkillContractTests(unittest.TestCase):
    def text(self, relative):
        path = LENS / relative
        self.assertTrue(path.is_file(), f"필수 실행 계약이 없다: {relative}")
        return path.read_text(encoding="utf-8")

    def test_every_phase_and_local_reference_resolves_from_its_own_location(self):
        main = self.text("SKILL.md")
        self.assertLess(len(main.encode("utf-8")), 20 * 1024)
        for phase in ("prepare", "explore", "report", "impact", "impact-report"):
            self.assertIn(f"phases/phase-{phase}.md", main)
        for source in LENS.rglob("*.md"):
            content = source.read_text(encoding="utf-8")
            targets = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)", content)
            targets += re.findall(r'Read\("([^"\n]+)"\)', content)
            for target in targets:
                with self.subTest(source=source.name, target=target):
                    self.assertFalse(Path(target).is_absolute())
                    self.assertNotRegex(target, r"^[a-zA-Z]+:")
                    self.assertTrue((source.parent / target).is_file())

    def test_query_only_terminates_without_a_mandatory_idea_question(self):
        report = self.text("phases/phase-report.md")
        self.assertIn("`IDEA_RAW`가 없으면 보고서를 출력하고 종료한다", report)
        self.assertNotIn('header: "영향도 분석"', report)
        self.assertNotIn('header: "유사 기능 포함"', report)

    def test_rule_evidence_preserves_intent_and_implementation_separately(self):
        evidence = self.text("references/evidence-contract.md")
        for field in ("`rule_id`", "`status`", "`observed`", "`intended`", "`evidence`", "`limits`"):
            self.assertIn(field, evidence)
        for status in ("확인", "추정", "미확인"):
            self.assertRegex(evidence, rf"(?m)^\| {status} \|")
        self.assertIn("프로젝트 루트 상대경로:시작라인-끝라인", evidence)
        self.assertIn("현재 구현을 의도된 정책으로 승격하지 않는다", evidence)
        self.assertNotIn("라인 번호 생략", self.text("SKILL.md"))

    def test_impact_depth_has_observable_conditions_and_no_failure_to_zero(self):
        impact = self.text("phases/phase-impact.md")
        self.assertRegex(impact, r"(?m)^\| 직접 분석 \|")
        self.assertRegex(impact, r"(?m)^\| architect \|")
        self.assertRegex(impact, r"(?m)^\| security-auditor \|")
        self.assertIn("미확인", impact)
        self.assertNotIn("내용 전체", impact)
        report = self.text("phases/phase-impact-report.md")
        self.assertNotIn("0으로 가정", report)
        self.assertNotIn("한 단계 상향", report)
        self.assertIn("사용자/소비자", report)
        self.assertIn("테스트 경계", report)

    def test_codex_runtime_mapping_keeps_lens_queries_read_only(self):
        main = self.text("SKILL.md")
        self.assertIn("../gx-work/references/codex-runtime.md", main)
        self.assertIn("질문 기록 helper", main)
        self.assertIn("빌드·테스트", main)
        self.assertIn("Git 변경", main)
        self.assertIn("scripts/check_evidence.py", main)


if __name__ == "__main__":
    unittest.main()
