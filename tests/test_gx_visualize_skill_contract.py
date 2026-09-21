import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".claude" / "skills" / "gx-visualize"
SKILL = SKILL_DIR / "SKILL.md"
MAPPING = SKILL_DIR / "references" / "gx-mapping.md"
CODEX = SKILL_DIR / "references" / "codex-runtime.md"
EXAMPLE = SKILL_DIR / "examples" / "trace-request.md"


class GxVisualizeSkillContractTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"required skill resource is missing: {path}")
        return path.read_text(encoding="utf-8")

    def test_command_routes_every_view_and_defaults_backend_to_auto(self):
        skill = self.read(SKILL)
        self.assertIn(
            "gx-visualize <trace|progress|impact|service|sequence> "
            "[--input <path>] [--input-path <path>]... [--dev-dir <path>] "
            "[--output <path>] "
            "[--backend auto|archify|mermaid|static]",
            skill,
        )
        self.assertIn("기본 백엔드: `auto`", skill)
        for view in ("trace", "progress", "impact", "service", "sequence"):
            self.assertRegex(skill, rf"(?m)^\| `{view}` \|")

    def test_mapping_covers_gx_artifacts_and_receipt_states(self):
        mapping = self.read(MAPPING)
        for artifact in ("prd.md", "design.md", "codemap.md", "state.md", "diff.txt", "DE-08", "DE-13"):
            self.assertIn(artifact, mapping)
        for status in ("verified", "fallback", "failed"):
            self.assertRegex(mapping, rf"(?m)^\| `{status}` \|")

    def test_all_bundled_markdown_references_are_relative_and_resolve(self):
        resources = (SKILL, MAPPING, CODEX, EXAMPLE)
        for source in resources:
            text = self.read(source)
            for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
                with self.subTest(source=source.name, target=target):
                    self.assertFalse(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", target))
                    self.assertFalse(Path(target).is_absolute())
                    self.assertFalse(re.match(r"^[A-Za-z]:[\\/]", target))
                    self.assertTrue((source.parent / target).resolve().is_file())

        skill = self.read(SKILL)
        for target in (
            "references/gx-mapping.md",
            "references/codex-runtime.md",
            "references/ir-contract.md",
            "references/archify-adapter.md",
            "examples/trace-request.md",
            "../gx-dev/references/codex-runtime.md",
        ):
            self.assertIn(target, skill)

    def test_input_collector_reports_missing_inputs_without_fabrication(self):
        skill = self.read(SKILL)
        self.assertIn(
            'collect_inputs(project_root, dev_dir, view) -> {"files": [...], "missing_inputs": [...]}`',
            skill,
        )
        self.assertIn("누락 입력을 추정하거나 조용히 채우지 않는다", skill)
        self.assertIn("`files`와 `missing_inputs`를 정렬", skill)
        mapping = self.read(MAPPING)
        self.assertIn("충족되지 않은 필수 논리 그룹만", mapping)
        self.assertIn("보조 그룹은 `missing_inputs`에 넣지 않는다", mapping)
        self.assertIn("`A 또는 B`", mapping)

    def test_natural_language_routes_views_and_asks_when_ambiguous(self):
        skill = self.read(SKILL)
        for phrase, view in (
            ("변경 영향도", "impact"),
            ("구조", "service"),
            ("서비스 관계", "service"),
            ("호출 순서", "sequence"),
            ("진행", "progress"),
            ("상태", "progress"),
            ("추적", "trace"),
            ("요구사항", "trace"),
        ):
            self.assertIn(f"`{phrase}` → `{view}`", skill)
        for phase, view in (("design", "service"), ("review", "impact"), ("그 외", "progress")):
            self.assertIn(f"`{phase}` → `{view}`", skill)
        self.assertIn("모호하면 사용자에게 view를 질문", skill)

    def test_project_root_evidence_and_non_text_locator_contract_is_documented(self):
        skill = self.read(SKILL)
        ir_contract = self.read(SKILL_DIR / "references" / "ir-contract.md")
        self.assertIn("--project-root", skill)
        self.assertIn("프로젝트 루트 상대경로", ir_contract)
        self.assertIn("locator", ir_contract)
        self.assertIn('{"type":"xlsx"', ir_contract)
        self.assertIn('{"type":"pdf"', ir_contract)

    def test_output_contract_and_visualization_only_failure_are_explicit(self):
        skill = self.read(SKILL)
        for field in (
            "view",
            "backend",
            "html_path",
            "ir_path",
            "receipt_path",
            "validation_status",
            "missing_inputs",
        ):
            self.assertRegex(skill, rf"(?m)^\s*-\s+`{field}`")
        self.assertIn("시각화만", skill)
        self.assertIn("visualization_status: failed", skill)
        self.assertIn("재실행 명령", skill)
        self.assertIn("개발·리뷰·커밋 파이프라인은 실패시키지 않는다", skill)

    def test_korean_triggers_and_no_runtime_inference_codex_contract(self):
        skill = self.read(SKILL)
        codex = self.read(CODEX)
        for trigger in ("시각화 포함", "구조를 그림으로 보여줘", "변경 영향도를 시각화해줘"):
            self.assertIn(trigger, skill)
        self.assertIn("런타임 사실을 추론하지 않는다", skill)
        self.assertIn("../../gx-dev/references/codex-runtime.md", codex)

        owned_text = "\n".join(self.read(path) for path in (SKILL, MAPPING, CODEX, EXAMPLE))
        self.assertNotRegex(owned_text, r"(?i)\b(?:gpt-\d|opus|sonnet|haiku)\b")
        self.assertNotRegex(owned_text, r"(?m)(?:^[A-Za-z]:[\\/]|/(?:Users|home)/)")


class AccumulatedMapContractTests(unittest.TestCase):
    def setUp(self):
        self.skill = (
            ROOT / ".claude" / "skills" / "gx-visualize" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_scope_flag_is_documented(self):
        self.assertIn("--scope session|all", self.skill)

    def test_map_dir_default_is_not_committed_location(self):
        self.assertIn(".dev/architecture/", self.skill)
        self.assertNotIn("docs/architecture/", self.skill)

    def test_outputs_are_not_promised_as_commit_targets(self):
        self.assertNotIn("커밋 대상", self.skill)

    def test_service_view_is_promoted(self):
        self.assertNotIn("계약 지원 뷰", self.skill)
        self.assertRegex(self.skill, r"\| `service` \|.*\| 1차 필수 \|")

    def test_sequence_deferral_is_documented(self):
        self.assertRegex(self.skill, r"\| `sequence` \|.*\| 후속 범위 \|")
        self.assertIn("participants", self.skill)

    def test_skill_links_entrypoint_rules(self):
        self.assertIn("references/entrypoint-rules.md", self.skill)
        self.assertTrue((ROOT / ".claude" / "skills" / "gx-visualize" / "references" / "entrypoint-rules.md").is_file())

    def test_korean_label_enrichment_is_required(self):
        self.assertIn("context/", self.skill)
        self.assertIn("한국어 라벨", self.skill)

    def test_empty_scan_must_not_write_empty_ir(self):
        self.assertIn("0개 노드", self.skill)

    def test_session_scope_writes_to_dev_dir(self):
        self.assertIn("`session` | `${DEV_DIR}/visual/`", self.skill)

    def test_all_scope_writes_to_map_dir(self):
        self.assertIn("`all` | `${MAP_DIR}/`", self.skill)

    def test_session_html_carries_snapshot_banner(self):
        self.assertIn("스냅샷 배너", self.skill)

    def test_session_and_accumulated_outputs_are_not_mixed(self):
        self.assertIn("한 폴더에 섞지 않는다", self.skill)

    def test_scope_all_does_not_promise_incremental_merge(self):
        self.assertNotIn("증분 갱신", self.skill)
        self.assertNotIn("merge_map", self.skill)
        self.assertNotIn(".scan-manifest.json", self.skill)

    def test_scope_all_states_full_rescan(self):
        self.assertIn("전체를 다시 스캔", self.skill)

    def test_scan_failures_report_both_skipped_and_unresolved_edges(self):
        self.assertIn("`skipped`", self.skill)
        self.assertIn("`unresolved_edges`", self.skill)


if __name__ == "__main__":
    unittest.main()
