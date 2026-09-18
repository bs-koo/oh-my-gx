import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GX_DEV = ROOT / ".claude" / "skills" / "gx-dev"
SKILL = GX_DEV / "SKILL.md"
DESIGN = GX_DEV / "phases" / "phase-design.md"
REVIEW = GX_DEV / "phases" / "phase-review.md"
COMPLETE = GX_DEV / "phases" / "phase-complete.md"
SETUP = GX_DEV / "phases" / "phase-setup.md"
VISUALIZE = ROOT / ".claude" / "skills" / "gx-visualize" / "SKILL.md"


class GxVisualizeRoutingTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"missing gx-dev resource: {path}")
        return path.read_text(encoding="utf-8")

    def test_explicit_flag_is_independent_of_phase_mode_and_model_profile(self):
        skill = self.read(SKILL)
        self.assertIn("`--visualize`가 포함되면 `VISUALIZE_REQUESTED = true`", skill)
        self.assertIn("모드·Phase·`MODEL_PROFILE`을 변경하지 않는다", skill)
        self.assertIn("`--visualize`는 플래그 충돌 검증 대상이 아니다", skill)

    def test_korean_natural_language_triggers_normalize_to_same_flag(self):
        skill = self.read(SKILL)
        for trigger in ("시각화 포함", "구조를 그림으로 보여줘", "변경 영향도를 시각화해줘"):
            self.assertIn(trigger, skill)
        self.assertIn("`--visualize`로 정규화", skill)

    def test_absent_trigger_is_a_strict_noop(self):
        skill = self.read(SKILL)
        self.assertIn(
            "명시 플래그와 자연어 트리거가 모두 없으면 시각화 스킬을 호출하지 않고",
            skill,
        )
        self.assertIn("기존 Phase 실행과 출력만 그대로 수행", skill)

    def test_design_and_review_handoffs_pass_each_existing_path(self):
        for phase in (DESIGN, REVIEW):
            text = self.read(phase)
            for field in ("DEV_DIR", "PROJECT_ROOT", "view", "input_paths", "project_root"):
                self.assertIn(field, text)
            self.assertIn("실제로 존재하는 파일만", text)
            call = next(
                line for line in text.splitlines()
                if 'Skill(skill: "oh-my-gx:gx-visualize"' in line
            )
            self.assertIn('--input-path \\"${input_path}\\"', call)
            self.assertNotIn('args: "${view} --input ${DEV_DIR}', call)
            self.assertIn("프로젝트 context 기본 탐색", text)

        self.assertIn("설계 문서를 `${DEV_DIR}/design.md`에 Write", self.read(DESIGN))
        self.assertIn("Step 1.5: 요청된 시각화", self.read(REVIEW))

    def test_repeatable_input_path_preserves_default_project_discovery(self):
        visualize = self.read(VISUALIZE)
        self.assertIn("[--input-path <path>]...", visualize)
        self.assertIn("`--input-path`는 반복 가능", visualize)
        self.assertIn("기본 수집을 제한하지 않는다", visualize)
        self.assertIn("명시 경로와 기본 탐색 결과를 합친다", visualize)

    def test_resume_persists_and_restores_visualization_flag_and_view(self):
        setup = self.read(SETUP)
        self.assertIn("visualize-view", setup)
        self.assertIn("flags에 `--visualize`", setup)
        self.assertIn("VISUALIZE_REQUESTED = true", setup)
        self.assertIn("VISUALIZE_VIEW", setup)

    def test_phase_only_reports_cover_success_fallback_and_failure(self):
        for phase, marker in ((DESIGN, "**Phase 완료 보고"), (REVIEW, "리뷰 완료:")):
            text = self.read(phase)
            report = text[text.index(marker) :]
            for field in (
                "visualization_status",
                "view",
                "backend",
                "html_path",
                "ir_path",
                "receipt_path",
                "validation_status",
                "missing_inputs",
            ):
                self.assertIn(field, report)
            self.assertIn("generated|fallback|failed", report)
            self.assertIn("receipt가 없거나 읽을 수 없으면", report)
            self.assertIn("html_path: null", report)
            self.assertIn("strict no-op", report)
            self.assertIn("Phase 결과를 실패로 바꾸지 않는다", report)

    def test_completion_reports_truthful_artifacts_without_blocking_delivery(self):
        complete = self.read(COMPLETE)
        for field in (
            "visualization_status",
            "view",
            "backend",
            "html_path",
            "ir_path",
            "receipt_path",
            "validation_status",
        ):
            self.assertIn(field, complete)
        self.assertIn("커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다", complete)
        self.assertIn("HTML 경로를 성공처럼 보고하지 않는다", complete)


if __name__ == "__main__":
    unittest.main()
