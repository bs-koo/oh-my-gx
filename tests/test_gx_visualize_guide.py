import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "gx-visualize-guide.md"
SMOKE = ROOT / "tests" / "codex-smoke.md"
IMPACT_FIXTURE = ROOT / "tests" / "fixtures" / "gx-impact.valid.json"
VALIDATOR_PATH = (
    ROOT / ".claude" / "skills" / "gx-visualize" / "scripts" / "validate_ir.py"
)


class GxVisualizeGuideTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"required Task 6 artifact is missing: {path}")
        return path.read_text(encoding="utf-8")

    def test_guide_covers_routes_output_and_three_backend_outcomes(self):
        guide = self.read(GUIDE)

        self.assertIn("gx-visualize", guide)
        for trigger in (
            "시각화 포함",
            "구조를 그림으로 보여줘",
            "변경 영향도를 시각화해줘",
        ):
            self.assertIn(trigger, guide)
        for view in ("trace", "progress", "impact", "service", "sequence"):
            self.assertRegex(guide, rf"(?m)^\| `{view}` \|")
        for view in ("trace", "progress", "impact"):
            self.assertRegex(guide, rf"(?m)^\| `{view}` \|.*\| 1차 필수 \|$")
        for view in ("service", "sequence"):
            self.assertRegex(guide, rf"(?m)^\| `{view}` \|.*\| 계약 지원 \|$")
        self.assertRegex(guide, r"근거가\s+부족하면 관계를 추정하지")
        self.assertIn("`missing_inputs`와 실패 상태", guide)
        self.assertIn(".dev/{branch-slug}/visual/", guide)
        self.assertIn("Archify 사용 가능", guide)
        self.assertIn("Archify 없음", guide)
        self.assertIn("정적 HTML 폴백", guide)
        self.assertIn("설치하거나 자동 업데이트하지 않습니다", guide)

    def test_guide_explains_evidence_receipts_and_truthful_failures(self):
        guide = self.read(GUIDE)

        for field in (
            "view",
            "backend",
            "html_path",
            "ir_path",
            "receipt_path",
            "validation_status",
            "missing_inputs",
        ):
            self.assertIn(f"`{field}`", guide)
        self.assertIn("파일·라인", guide)
        self.assertIn("locator", guide)
        self.assertIn("visualization_status: failed", guide)
        self.assertIn("실패한 Archify를 성공으로 표시하지", guide)
        self.assertIn("재실행 명령", guide)
        self.assertIn("성공 또는 폴백", guide)
        self.assertIn("검증 또는 입력 감지에 실패", guide)
        self.assertIn("HTML을 제거", guide)
        self.assertIn("failed receipt", guide)

    def test_impact_fixture_is_valid_real_ir(self):
        self.assertTrue(IMPACT_FIXTURE.is_file(), "impact fixture must be present")
        spec = importlib.util.spec_from_file_location(
            "gx_visualize_task6_validator", VALIDATOR_PATH
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)

        receipt = validator.validate(IMPACT_FIXTURE, project_root=ROOT)
        payload = json.loads(IMPACT_FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["errors"], [])
        self.assertEqual(payload["view"], "impact")
        self.assertGreaterEqual(receipt["node_count"], 2)
        self.assertGreaterEqual(receipt["edge_count"], 1)

        skill_node = next(
            node for node in payload["nodes"] if node["id"] == "gx-change-visualize-skill"
        )
        evidence = skill_node["evidence"][0]
        source_lines = (ROOT / evidence["file"]).read_text(encoding="utf-8").splitlines()
        cited_line = source_lines[evidence["line"] - 1]
        self.assertIn(skill_node["technical_label"], cited_line)

    def test_codex_smoke_keeps_live_visualization_checks_not_run(self):
        smoke = self.read(SMOKE)

        for scenario in ("V1", "V2", "V3"):
            self.assertRegex(smoke, rf"(?m)^\| {scenario} \|")
        self.assertIn("gx-visualize 발견", smoke)
        self.assertIn("실패한 Archify 시도", smoke)
        self.assertIn("visualization_status: failed", smoke)
        for scenario in ("V1", "V2", "V3"):
            with self.subTest(scenario=scenario):
                self.assertRegex(smoke, rf"(?m)^\| {scenario} \|.*\| 미실행 \|$")
        self.assertIn("로컬 단위 테스트나 mock 결과를 PASS 근거로 대체하지 않는다", smoke)


if __name__ == "__main__":
    unittest.main()
