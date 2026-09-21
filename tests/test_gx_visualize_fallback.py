import importlib.util
import html
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".claude" / "skills" / "gx-visualize" / "scripts" / "render_fallback.py"
FIXTURE = ROOT / "tests" / "fixtures" / "gx-trace.valid.json"
PROJECT_FIXTURE = ROOT / "tests" / "fixtures" / "gx-visualize-project"


def load_renderer():
    spec = importlib.util.spec_from_file_location("gx_visualize_render_fallback", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(module)
    return module


class VisualFallbackRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def render(self, backend):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output_dir = Path(temporary.name)
        result = self.renderer.render(FIXTURE, output_dir, backend)
        html_text = Path(result["html_path"]).read_text(encoding="utf-8")
        receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
        return result, html_text, receipt

    def write_ir(self, root, **overrides):
        payload = {
            "schema_version": 1,
            "view": "trace",
            "locale": "ko-KR",
            "title": "테스트 시각화",
            "nodes": [
                {
                    "id": "N1",
                    "kind": "requirement",
                    "label": "첫 노드",
                    "technical_label": "service.first",
                    "status": "verified",
                    "evidence": [],
                },
                {
                    "id": "N2",
                    "kind": "function",
                    "label": "둘째 노드",
                    "status": "review",
                    "evidence": [],
                },
            ],
            "edges": [
                {
                    "id": "N1->N2",
                    "source": "N1",
                    "target": "N2",
                    "relation": "realized_by",
                }
            ],
        }
        payload.update(overrides)
        ir_path = root / "input.json"
        ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return ir_path, payload

    @staticmethod
    def mermaid_source(html_text):
        prefix = '<pre class="mermaid-source"><code>'
        start = html_text.index(prefix) + len(prefix)
        end = html_text.index("</code></pre>", start)
        return html.unescape(html_text[start:end])

    def test_static_html_is_self_contained_korean_and_accessible(self):
        result, html_text, receipt = self.render("static")

        self.assertEqual(result["backend"], "static")
        self.assertIn('<html lang="ko">', html_text)
        self.assertIn("요구사항 추적 맵", html_text)
        self.assertIn("범례", html_text)
        self.assertIn("노드 목록", html_text)
        self.assertIn("관계", html_text)
        self.assertIn("근거", html_text)
        self.assertIn("검증됨", html_text)
        self.assertIn("AN-02-001", html_text)
        self.assertIn("EnergyUsageService.findByPeriod", html_text)
        self.assertNotIn("<script>alert(1)</script>", html_text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html_text)
        self.assertNotIn('src="http', html_text)
        self.assertNotIn('href="http', html_text)
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["backend"], "static")

    def test_mermaid_html_preserves_labels_and_has_static_fallback(self):
        result, html_text, receipt = self.render("mermaid")

        self.assertEqual(result["backend"], "mermaid")
        self.assertIn("flowchart LR", html_text)
        self.assertIn("AN-02-001", html_text)
        self.assertIn("/api/v1/energy?&lt;script&gt;alert(1)&lt;/script&gt;", html_text)
        self.assertIn("다이어그램은 생성되지 않았습니다", html_text)
        self.assertIn("npx -y skills add tt-a1i/archify -g", html_text)
        self.assertIn("노드 목록", html_text)
        self.assertNotIn("<script>alert(1)</script>", html_text)
        self.assertEqual(receipt["backend"], "mermaid")

    def test_mermaid_source_preserves_ascii_and_korean_text_verbatim(self):
        # 버그 A(2026-09-21 컨트롤러가 reb.html에서 발견): 예전에는 모든 문자를
        # #{ord};로 인코딩해 "gx-api-webframework-..." 같은 라벨이 화면에
        # "#103;#120;..."로 떴다. Mermaid 문법에 꼭 필요한 문자만 인코딩하고 나머지
        # ASCII·한글은 원문 그대로 남아야 사람이 읽을 수 있다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root)
            payload["nodes"][0]["label"] = "에너지 사용량 조회 API"
            payload["nodes"][0]["technical_label"] = "EnergyUsageService.findByPeriod"
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

        self.assertIn("에너지 사용량 조회 API", source)
        self.assertIn("EnergyUsageService.findByPeriod", source)
        self.assertNotIn("#51060;", source)  # '에'가 인코딩되면 나타날 코드포인트

    def test_mermaid_source_escapes_only_grammar_breaking_characters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root)
            payload["nodes"][0]["label"] = 'A\n  injected["가짜"] --> n9'
            payload["edges"][0]["relation"] = '연결| "\\[]{}()'
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

        # 줄바꿈은 여전히 인코딩된다 - 각 statement는 한 줄이어야 한다(2 노드 + 1
        # 헤더 + 1 엣지 = 4줄을 유지해야 새 줄이 실제로 삽입되지 않았다는 뜻이다).
        self.assertEqual(len(source.splitlines()), 4)
        # 따옴표는 라벨을 조기 종료시키므로 여전히 인코딩된다
        self.assertNotIn('"가짜"', source)
        self.assertIn("#34;가짜#34;", source)
        # 엣지 라벨의 파이프는 `-->|...|` 구분자와 충돌하므로 여전히 인코딩된다
        self.assertIn("#124;", source)
        # 대괄호·중괄호·소괄호·백슬래시·한글은 인용된 라벨 안에서 안전하므로
        # 원문 그대로 남는다
        self.assertIn("injected[", source)
        self.assertIn("--> n9", source)
        self.assertIn("\\[]{}()", source)
        self.assertIn("연결", source)

    def test_mermaid_label_does_not_lead_with_the_node_id(self):
        # 버그 B(2026-09-21 컨트롤러가 reb.html에서 발견): 라벨이 긴 기술 ID로
        # 시작해 실제 이름을 가렸다. ID는 노드 목록 카드에 이미 있으므로 Mermaid
        # 라벨에서는 뺀다.
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(FIXTURE, Path(temporary), "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

        self.assertIn("에너지 사용량을 기간별로 조회한다", source)
        for node_id in ("AN-02-001", "AN-03-001", "DE-13-001"):
            for line in source.splitlines():
                if f'["' not in line:
                    continue
                label = line.split('["', 1)[1]
                self.assertFalse(label.startswith(node_id), f"{node_id}가 라벨 맨 앞에 남아 있다: {line}")

    def test_unknown_status_badge_is_not_shown_in_service_view(self):
        # service 뷰는 코드 스캐너가 상태를 알 수 없어 모든 노드가 구조적으로
        # unknown이다 - 그걸 다 찍으면 "확인 필요"가 노드 수만큼 반복돼 정보가
        # 아니라 잡음이 된다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="service")
            payload["nodes"] = [
                {"id": "N1", "kind": "service", "label": "UserService", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("UserService", html_text)
        self.assertNotIn("확인 필요", html_text)

    def test_unknown_status_badge_is_shown_outside_service_view(self):
        # trace·progress·impact는 사람이 상태를 채우는 뷰다 - unknown은 "아직 확인
        # 안 됨"이라는 실행 가능한 신호이므로 service 뷰만의 억제를 여기까지 넓히면
        # 안 된다(리뷰 판정 AH).
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="trace")
            payload["nodes"] = [
                {"id": "N1", "kind": "requirement", "label": "확인 안 된 요구사항", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("확인 필요", html_text)

    def test_legend_omitted_when_every_node_is_unknown_in_service_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="service")
            payload["nodes"] = [
                {"id": "N1", "kind": "service", "label": "UserService", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertNotIn("범례", html_text)

    def test_legend_shown_for_unknown_only_nodes_outside_service_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="trace")
            payload["nodes"] = [
                {"id": "N1", "kind": "requirement", "label": "확인 안 된 요구사항", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("범례", html_text)
        self.assertIn("확인 필요", html_text)

    def test_legend_lists_only_statuses_actually_used_in_service_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="service")
            payload["nodes"] = [
                {"id": "N1", "kind": "service", "label": "확실한 노드", "status": "verified", "evidence": []},
                {"id": "N2", "kind": "service", "label": "미상 노드", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("범례", html_text)
        self.assertIn("검증됨", html_text)
        self.assertNotIn("확인 필요", html_text)

    def test_mermaid_label_hides_unknown_in_service_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="service")
            payload["nodes"] = [
                {"id": "N1", "kind": "service", "label": "UserService", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

        self.assertNotIn("확인 필요", source)

    def test_mermaid_label_shows_unknown_outside_service_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="trace")
            payload["nodes"] = [
                {"id": "N1", "kind": "requirement", "label": "확인 안 된 요구사항", "status": "unknown", "evidence": []},
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

        self.assertIn("확인 필요", source)

    def test_duplicate_table_label_shown_once_in_node_card(self):
        # 테이블 노드는 label과 technical_label이 같은 테이블명이다 - "TB_ROLE TB_ROLE"
        # 처럼 같은 이름을 두 번 찍지 않는다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root)
            payload["nodes"] = [
                {
                    "id": "T1", "kind": "table", "label": "TB_ROLE",
                    "technical_label": "TB_ROLE", "status": "unknown", "evidence": [],
                },
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "static")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(1, html_text.count("TB_ROLE"))

    def test_duplicate_table_label_shown_once_in_mermaid_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root)
            payload["nodes"] = [
                {
                    "id": "T1", "kind": "table", "label": "TB_ROLE",
                    "technical_label": "TB_ROLE", "status": "unknown", "evidence": [],
                },
            ]
            payload["edges"] = []
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")
            source = self.mermaid_source(html_text)

        self.assertEqual(1, source.count("TB_ROLE"))

    def test_template_tokens_in_title_and_labels_remain_literal_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, title="{{STATIC_CONTENT}}")
            payload["nodes"][0]["label"] = "{{MERMAID_SECTION}}"
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(ir_path, root / "output", "mermaid")
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

            self.assertIn("<title>{{STATIC_CONTENT}}</title>", html_text)
            self.assertIn("<h1>{{STATIC_CONTENT}}</h1>", html_text)
            self.assertIn("<h3>{{MERMAID_SECTION}}</h3>", html_text)
            self.assertEqual(html_text.count('id="nodes-title"'), 1)
            self.assertEqual(html_text.count('id="mermaid-title"'), 1)

    def test_output_is_deterministic_and_sorted_by_stable_ids(self):
        _, first_html, first_receipt = self.render("mermaid")
        _, second_html, second_receipt = self.render("mermaid")

        self.assertEqual(first_html, second_html)
        self.assertEqual(first_receipt, second_receipt)
        self.assertLess(first_html.index("AN-02-001"), first_html.index("AN-03-001"))
        self.assertLess(first_html.index("AN-03-001"), first_html.index("DE-13-001"))

    def test_output_name_scopes_separate_renders_to_distinct_files(self):
        # 판정 Y: 같은 output_dir에 같은 view("trace")의 IR을 두 번 렌더하면 output_name
        # 없이는 둘 다 trace.html로 서로를 덮어쓴다. --output-name을 주면 각 렌더가 자기
        # 이름의 파일을 갖고 둘 다 살아남아야 한다.
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "output"
            first = self.renderer.render(FIXTURE, output_dir, "static", output_name="auth")
            second = self.renderer.render(FIXTURE, output_dir, "static", output_name="code")
            self.assertTrue(Path(first["html_path"]).is_file())
            self.assertTrue(Path(second["html_path"]).is_file())
            self.assertTrue(Path(first["receipt_path"]).is_file())
            self.assertTrue(Path(second["receipt_path"]).is_file())

        self.assertNotEqual(first["html_path"], second["html_path"])
        self.assertTrue(first["html_path"].endswith("auth.html"))
        self.assertTrue(second["html_path"].endswith("code.html"))

    def test_output_name_omitted_keeps_view_derived_filename(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(FIXTURE, Path(temporary), "static")

        self.assertTrue(result["html_path"].endswith("trace.html"))
        self.assertTrue(result["receipt_path"].endswith("trace.receipt.json"))

    def test_failed_validation_writes_receipt_and_does_not_render_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid_ir = root / "invalid.json"
            invalid_ir.write_text("{}", encoding="utf-8")
            output_dir = root / "output"

            with self.assertRaisesRegex(ValueError, "IR 검증 실패"):
                self.renderer.render(invalid_ir, output_dir, "static")

            receipt_path = output_dir / "trace.receipt.json"
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["status"], "failed")
            self.assertFalse((output_dir / "trace.html").exists())

    def test_failed_rerender_uses_input_view_and_invalidates_stale_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ir_path, payload = self.write_ir(root, view="impact")
            output_dir = root / "output"
            first = self.renderer.render(ir_path, output_dir, "static")
            self.assertTrue(Path(first["html_path"]).is_file())
            self.assertEqual(
                json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))["status"],
                "valid",
            )

            payload["nodes"][0]["status"] = "not-a-status"
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "IR 검증 실패"):
                self.renderer.render(ir_path, output_dir, "static")

            receipt_path = output_dir / "impact.receipt.json"
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["status"], "failed")
            self.assertFalse((output_dir / "impact.html").exists())
            self.assertFalse((output_dir / "trace.receipt.json").exists())

    def test_unknown_backend_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "backend"):
                self.renderer.render(FIXTURE, Path(temporary), "canvas")

    def test_snapshot_banner_is_absent_by_default(self):
        # I7 이전에는 만들 수단 자체가 없었다 - 기본값(False)에서는 여전히 없어야 한다
        # (수용 기준 10은 --scope session 전용, --scope all은 넣지 않는다).
        _, html_text, _ = self.render("static")
        self.assertNotIn("갱신되지 않습니다", html_text)

    def test_snapshot_banner_carries_the_three_required_facts(self):
        # SKILL.md:101/설계서 §5.1이 요구하는 세 가지: 생성 시각, 커밋 해시, 갱신되지
        # 않는다는 고지(2026-09-18 최종 리뷰 I7, 수용 기준 10).
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            result = self.renderer.render(FIXTURE, output_dir, "static", snapshot_banner=True)
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("생성 시각", html_text)
        self.assertIn("갱신되지 않습니다", html_text)

    def test_snapshot_banner_includes_short_head_in_a_git_project(self):
        # FIXTURE의 근거 파일은 자기 자신(같은 디렉터리)을 가리키므로, evidence
        # confinement가 깨지지 않도록 project_root도 같은 디렉터리(tests/fixtures/,
        # 실제 oh-my-gx git 저장소 내부)로 준다 - git이 상위로 올라가 HEAD를 찾는다.
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            result = self.renderer.render(
                FIXTURE, output_dir, "static", project_root=FIXTURE.parent, snapshot_banner=True,
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("커밋", html_text)

    def test_snapshot_banner_is_inserted_right_after_the_body_tag(self):
        banner = self.renderer.snapshot_banner_html(None)
        injected = self.renderer.inject_snapshot_banner("<html><body><p>본문</p></body></html>", banner)
        self.assertEqual(f"<html><body>{banner}<p>본문</p></body></html>", injected)

    def test_project_root_is_forwarded_when_rendering_real_dev_visual_ir(self):
        ir_path = PROJECT_FIXTURE / ".dev" / "feat-energy" / "visual" / "trace.json"
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(
                ir_path,
                Path(temporary),
                "static",
                project_root=PROJECT_FIXTURE,
            )

        self.assertEqual(result["backend"], "static")

    def test_binary_locator_is_rendered_without_requiring_a_line_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / "DE-13.xlsx").write_bytes(b"PK\x03\x04\xff\xfe")
            ir_path, payload = self.write_ir(project)
            payload["nodes"][0]["evidence"] = [
                {
                    "file": "DE-13.xlsx",
                    "kind": "test",
                    "locator": {"type": "xlsx", "sheet": "단위테스트", "cell": "B12"},
                }
            ]
            ir_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.renderer.render(
                ir_path,
                project / "output",
                "static",
                project_root=project,
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("단위테스트", html_text)
        self.assertIn("B12", html_text)

    def test_html_dir_writes_html_separately_from_receipt_dir(self):
        # `--scope all`은 이걸로 `${MAP_DIR}/domains/`(html)와 `${MAP_DIR}/receipts/`
        # (receipt)를 분리한다 - 32개 파일이 평평하게 쌓인다는 지적(2026-09-21)의 수정.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.renderer.render(
                FIXTURE, root / "receipts", "static", output_name="auth", html_dir=root / "domains",
            )

            self.assertEqual(result["html_path"], str(root / "domains" / "auth.html"))
            self.assertEqual(result["receipt_path"], str(root / "receipts" / "auth.receipt.json"))
            self.assertTrue((root / "domains" / "auth.html").is_file())
            self.assertTrue((root / "receipts" / "auth.receipt.json").is_file())
            self.assertFalse((root / "receipts" / "auth.html").exists())

    def test_html_dir_omitted_keeps_flat_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(FIXTURE, Path(temporary), "static")

        self.assertEqual(Path(result["html_path"]).parent, Path(result["receipt_path"]).parent)

    def test_fallback_html_renders_mermaid_not_just_source(self):
        # 사용자 요청 2(2026-09-21): 폴백 도메인도 그림이 보여야 한다.
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(
                FIXTURE, Path(temporary), "mermaid", mermaid_asset_href="../assets/mermaid.min.js",
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn('<pre class="mermaid">', html_text)
        self.assertIn("mermaid.initialize(", html_text)

    def test_fallback_references_shared_asset_not_inline(self):
        # 실측 mermaid.min.js는 3.4MB다 - href로만 참조하고 내용을 인라인하지 않는다.
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(
                FIXTURE, Path(temporary), "mermaid", mermaid_asset_href="../assets/mermaid.min.js",
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn('<script src="../assets/mermaid.min.js"></script>', html_text)
        self.assertLess(len(html_text), 50_000)

    def test_source_is_still_available_but_collapsed(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.renderer.render(
                FIXTURE, Path(temporary), "mermaid", mermaid_asset_href="../assets/mermaid.min.js",
            )
            html_text = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("<details>", html_text)
        self.assertIn("<summary>", html_text)
        self.assertIn('class="mermaid-source"', html_text)
        self.assertGreater(html_text.index('class="mermaid-source"'), html_text.index("<details>"))

    def test_mermaid_asset_href_omitted_keeps_source_only_fallback(self):
        # "지금처럼" - 자산 href를 안 주면(호출자가 확보를 시도하지 않았거나 실패한
        # 경우) 기존 동작(소스만, Archify 설치 안내) 그대로다.
        _, html_text, _ = self.render("mermaid")
        self.assertIn("다이어그램은 생성되지 않았습니다", html_text)
        self.assertNotIn('<pre class="mermaid">', html_text)

    def test_node_card_heading_css_wraps_long_tokens(self):
        # 버그 C(2026-09-21 컨트롤러가 reb.html에서 발견): RebController.download...
        # 같은 긴 토큰이 h3에 overflow-wrap이 없어 옆 카드를 침범했다.
        css_path = MODULE_PATH.parent.parent / "templates" / "fallback.css"
        css_text = css_path.read_text(encoding="utf-8")
        match = re.search(r"\.node-card h3\s*\{[^}]*\}", css_text)
        self.assertIsNotNone(match)
        self.assertIn("overflow-wrap: anywhere", match.group(0))


class EnsureMermaidAssetTests(unittest.TestCase):
    """ensure_mermaid_asset(): 폴백 도메인이 공유하는 mermaid.min.js를 1회 확보한다.

    실제 네트워크를 쓰지 않도록 curl은 가짜 실행 파일로 대체한다.
    """

    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    @staticmethod
    def _fake_run_writing(payload: bytes, *, returncode: int = 0):
        def fake_run(argv, **kwargs):
            out_path = Path(argv[argv.index("-o") + 1])
            out_path.write_bytes(payload)
            return mock.Mock(returncode=returncode, stderr="")

        return fake_run

    def test_download_success_writes_asset_and_records_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets_dir = Path(temporary) / "assets"
            with mock.patch.object(self.renderer.shutil, "which", return_value="curl"):
                with mock.patch.object(
                    self.renderer.subprocess, "run", side_effect=self._fake_run_writing(b"x" * 600_000)
                ) as run:
                    result = self.renderer.ensure_mermaid_asset(assets_dir)

            self.assertTrue(result["available"])
            self.assertTrue((assets_dir / "mermaid.min.js").is_file())
            self.assertEqual((assets_dir / "mermaid.min.js").stat().st_size, 600_000)
            self.assertEqual(len(result["attempts"]), 1)
            self.assertEqual(result["attempts"][0]["phase"], "download")
            self.assertEqual(run.call_args.kwargs.get("timeout"), 90)

    def test_already_cached_asset_is_reused_without_downloading(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets_dir = Path(temporary)
            assets_dir.mkdir(exist_ok=True)
            (assets_dir / "mermaid.min.js").write_bytes(b"x" * 600_000)
            with mock.patch.object(self.renderer.subprocess, "run") as run:
                result = self.renderer.ensure_mermaid_asset(assets_dir)

        run.assert_not_called()
        self.assertTrue(result["available"])
        self.assertEqual(result["attempts"], [])

    def test_missing_curl_records_attempt_without_raising(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets_dir = Path(temporary) / "assets"
            with mock.patch.object(self.renderer.shutil, "which", return_value=None):
                result = self.renderer.ensure_mermaid_asset(assets_dir)

        self.assertFalse(result["available"])
        self.assertIsNone(result["path"])
        self.assertEqual(len(result["attempts"]), 1)
        self.assertIn("curl", result["attempts"][0]["stderr"])

    def test_undersized_download_is_treated_as_failure(self):
        # 잘렸거나 오류 페이지를 받은 다운로드를 성공으로 착각하지 않는다.
        with tempfile.TemporaryDirectory() as temporary:
            assets_dir = Path(temporary) / "assets"
            with mock.patch.object(self.renderer.shutil, "which", return_value="curl"):
                with mock.patch.object(
                    self.renderer.subprocess, "run", side_effect=self._fake_run_writing(b"not the real file")
                ):
                    result = self.renderer.ensure_mermaid_asset(assets_dir)

            self.assertFalse(result["available"])
            self.assertFalse((assets_dir / "mermaid.min.js").exists())


if __name__ == "__main__":
    unittest.main()
