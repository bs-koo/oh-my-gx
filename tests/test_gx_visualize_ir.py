import json
import importlib.util
import tempfile
import unittest
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".claude" / "skills" / "gx-visualize" / "scripts" / "validate_ir.py"
PROJECT_FIXTURE = ROOT / "tests" / "fixtures" / "gx-visualize-project"
spec = importlib.util.spec_from_file_location("gx_visualize_validate_ir", MODULE_PATH)
validator = importlib.util.module_from_spec(spec)
if spec.loader is not None:
    spec.loader.exec_module(validator)


class VisualIrValidationTests(unittest.TestCase):
    def write_ir(self, payload, root):
        path = root / "input.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def base_ir(self):
        return {
            "schema_version": 1,
            "view": "trace",
            "locale": "ko-KR",
            "title": "요구사항 추적 맵",
            "nodes": [
                {
                    "id": "AN-02-001",
                    "kind": "requirement",
                    "label": "조회한다",
                    "status": "verified",
                    "evidence": [],
                },
                {
                    "id": "AN-03-001",
                    "kind": "function",
                    "label": "조회 기능",
                    "status": "planned",
                    "evidence": [],
                },
            ],
            "edges": [
                {
                    "id": "AN-02-001->AN-03-001",
                    "source": "AN-02-001",
                    "target": "AN-03-001",
                    "relation": "realized_by",
                }
            ],
            "meta": {"project": "test"},
        }

    def test_duplicate_node_ids_are_errors_sorted_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["nodes"][1]["id"] = "AN-02-001"
            receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(any("nodes[1].id" in error for error in receipt["errors"]))
        self.assertEqual(receipt["node_count"], 2)

    def test_missing_edge_targets_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["edges"][0]["target"] = "AN-03-999"
            receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(any("edges[0].target" in error for error in receipt["errors"]))

    def test_invalid_status_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["nodes"][0]["status"] = "done"
            receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(any("nodes[0].status" in error for error in receipt["errors"]))

    def test_absent_evidence_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [
                {"file": "missing.md", "line": 4, "kind": "artifact"}
            ]
            receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("missing.md", " ".join(receipt["errors"]))

    def test_valid_trace_fixture_returns_clean_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "prd.md"
            evidence.write_text("요구사항\n", encoding="utf-8")
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [
                {"file": "prd.md", "line": 1, "kind": "artifact"}
            ]
            receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["errors"], [])
        self.assertEqual(receipt["warnings"], [])
        self.assertEqual(receipt["node_count"], 2)
        self.assertEqual(receipt["edge_count"], 1)
        self.assertEqual(receipt["missing_inputs"], [])

    def test_cp949_evidence_source_line_count_is_still_checked(self):
        # 오래된 한국어 JSP·Java 코드베이스에는 CP949로 저장된 파일이 섞여 있는 경우가
        # 흔하다 - utf-8로만 읽으면 근거 파일을 읽지 못했다는 거짓 에러가 나서 실제로는
        # 유효한 IR을 실패로 판정한다.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "legacy.jsp"
            evidence.write_bytes("첫줄\n둘째줄\n한글 화면\n".encode("cp949"))
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [{"file": "legacy.jsp", "line": 2, "kind": "code"}]
            receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["errors"], [])

    def test_project_root_relative_evidence_supports_real_dev_visual_layout(self):
        ir_path = PROJECT_FIXTURE / ".dev" / "feat-energy" / "visual" / "trace.json"

        receipt = validator.validate(ir_path, project_root=PROJECT_FIXTURE)

        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["errors"], [])
        self.assertEqual(receipt["missing_inputs"], [])

    def test_project_root_confinement_allows_internal_parent_segments_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            project = sandbox / "project"
            visual = project / ".dev" / "work" / "visual"
            visual.mkdir(parents=True)
            (project / ".dev" / "work" / "prd.md").write_text("요구사항\n", encoding="utf-8")
            (sandbox / "outside.md").write_text("외부\n", encoding="utf-8")
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [
                {"file": ".dev/work/visual/../prd.md", "line": 1, "kind": "artifact"}
            ]
            ir_path = self.write_ir(payload, visual)

            receipt = validator.validate(ir_path, project_root=project)
            self.assertEqual(receipt["status"], "valid")

            payload["nodes"][0]["evidence"][0]["file"] = "../outside.md"
            receipt = validator.validate(self.write_ir(payload, visual), project_root=project)
            self.assertEqual(receipt["status"], "failed")
            self.assertTrue(any("project root" in error for error in receipt["errors"]))

    def test_binary_xlsx_and_pdf_evidence_use_locators_without_text_decoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            evidence_dir = project / "artifacts"
            evidence_dir.mkdir()
            (evidence_dir / "DE-13.xlsx").write_bytes(b"PK\x03\x04\xff\xfe")
            (evidence_dir / "DE-08.pdf").write_bytes(b"%PDF-1.7\n\xff\xfe")
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [
                {
                    "file": "artifacts/DE-13.xlsx",
                    "kind": "test",
                    "locator": {"type": "xlsx", "sheet": "단위테스트", "cell": "B12"},
                },
                {
                    "file": "artifacts/DE-08.pdf",
                    "kind": "artifact",
                    "locator": {"type": "pdf", "page": 2},
                },
            ]

            receipt = validator.validate(self.write_ir(payload, project), project_root=project)

        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["errors"], [])

    def test_locator_requires_supported_type_specific_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "artifact.bin").write_bytes(b"\xff")
            cases = (
                ({"type": "xlsx", "sheet": "요구사항"}, ".locator.cell"),
                ({"type": "pdf", "page": 0}, ".locator.page"),
                ({"type": "image", "page": 1}, ".locator.type"),
            )
            for locator, error_path in cases:
                with self.subTest(locator=locator):
                    payload = self.base_ir()
                    payload["nodes"][0]["evidence"] = [
                        {"file": "artifact.bin", "kind": "artifact", "locator": locator}
                    ]
                    receipt = validator.validate(self.write_ir(payload, project), project_root=project)
                    self.assertEqual(receipt["status"], "failed")
                    self.assertTrue(any(error_path in error for error in receipt["errors"]))

    def assert_failed(self, payload, root):
        receipt = validator.validate(self.write_ir(payload, root))
        self.assertEqual(receipt["status"], "failed")
        return receipt

    def test_evidence_project_root_escape_and_absolute_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ir"
            root.mkdir()
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [{"file": "../outside.md", "line": 1, "kind": "artifact"}]
            receipt = self.assert_failed(payload, root)
            self.assertTrue(any("project root" in error for error in receipt["errors"]))
            payload["nodes"][0]["evidence"][0]["file"] = str(Path(tmp) / "outside.md")
            receipt = self.assert_failed(payload, root)
            self.assertTrue(any("project root" in error for error in receipt["errors"]))

    def test_evidence_line_must_exist_and_missing_inputs_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one.md").write_text("one\n", encoding="utf-8")
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [{"file": "one.md", "line": 2, "kind": "artifact"}]
            receipt = self.assert_failed(payload, root)
            self.assertTrue(any("line" in error for error in receipt["errors"]))
            payload["nodes"][0]["evidence"][0]["file"] = "missing.md"
            receipt = self.assert_failed(payload, root)
            self.assertEqual(receipt["missing_inputs"], ["missing.md"])

    def test_receipt_carries_ir_declared_missing_inputs(self):
        # split_domains.py는 cross-domain-edge 등을 IR 최상위 missing_inputs에 남긴다 -
        # 검증기가 근거 파일 부재로 계산한 자신의 집합으로 그 값을 덮어써서는 안 된다
        # (2026-09-18 최종 리뷰 I1).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["missing_inputs"] = ["cross-domain-edge", "cross-domain-edge"]
            receipt = validator.validate(self.write_ir(payload, root))
            self.assertEqual(receipt["status"], "valid")
            self.assertEqual(receipt["missing_inputs"], ["cross-domain-edge"])

    def test_receipt_does_not_report_empty_when_ir_has_declared_entries(self):
        # 실측된 결함: user 도메인 IR은 missing_inputs 9건을 선언했는데 영수증은 []를
        # 보고했다(같은 리뷰) - 빈 배열로 덮어쓰지 않는지 못박는다.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["missing_inputs"] = ["cross-domain-edge"]
            receipt = validator.validate(self.write_ir(payload, root))
            self.assertNotEqual(receipt["missing_inputs"], [])

    def test_unhashable_values_and_boolean_schema_version_return_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["schema_version"] = True
            payload["nodes"][0]["status"] = []
            payload["view"] = {}
            receipt = self.assert_failed(payload, root)
        paths = [error.split(":", 1)[0] for error in receipt["errors"]]
        self.assertEqual(paths, sorted(paths))

    def test_boolean_schema_version_is_rejected_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["schema_version"] = True
            receipt = self.assert_failed(payload, root)
        self.assertTrue(any("$.schema_version" in error for error in receipt["errors"]))

    def test_embedded_nul_in_evidence_path_returns_file_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [{"file": "bad\u0000name", "line": 1, "kind": "artifact"}]
            receipt = self.assert_failed(payload, root)
        self.assertTrue(any("$.nodes[0].evidence[0].file" in error for error in receipt["errors"]))

    def test_non_standard_json_constants_return_failed_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for constant in ("NaN", "Infinity", "-Infinity"):
                source = root / (constant.replace("-", "negative") + ".json")
                source.write_text(
                    '{"schema_version":1,"view":"trace","locale":"ko-KR","title":"T","nodes":[],"edges":[],"meta":{"score":' + constant + '}}',
                    encoding="utf-8",
                )
                receipt = validator.validate(source)
                self.assertEqual(receipt["status"], "failed", constant)

    def test_schema_runtime_parity_for_technical_label_and_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["nodes"][0]["technical_label"] = 7
            payload["meta"] = []
            receipt = self.assert_failed(payload, root)
        self.assertTrue(any("technical_label" in error for error in receipt["errors"]))
        self.assertTrue(any("$.meta" in error for error in receipt["errors"]))

    def test_inferred_evidence_is_explicit_and_has_no_fake_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["nodes"][0]["evidence"] = [{"kind": "inferred"}]
            receipt = validator.validate(self.write_ir(payload, root))
            self.assertEqual(receipt["status"], "valid")
            payload["nodes"][0]["evidence"] = [{"kind": "inferred", "file": "fake.md"}]
            self.assert_failed(payload, root)
            payload["nodes"][0]["evidence"] = [
                {"kind": "inferred", "locator": {"type": "pdf", "page": 1}}
            ]
            self.assert_failed(payload, root)

    def test_duplicate_edge_ids_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.base_ir()
            payload["edges"].append(dict(payload["edges"][0]))
            receipt = self.assert_failed(payload, root)
        self.assertTrue(any("edges[1].id" in error for error in receipt["errors"]))

    def test_malformed_and_non_utf8_inputs_return_failed_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed = root / "bad.json"
            malformed.write_text("{", encoding="utf-8")
            self.assertEqual(validator.validate(malformed)["status"], "failed")
            binary = root / "binary.json"
            binary.write_bytes(b"\xff\xfe")
            self.assertEqual(validator.validate(binary)["status"], "failed")

    def test_cli_failed_validation_writes_receipt_and_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_ir(self.base_ir(), root)
            source.write_text("{}", encoding="utf-8")
            output = root / "receipt.json"
            result = subprocess.run(
                ["python", str(MODULE_PATH), str(source), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "failed")

    def test_cli_project_root_validates_real_dev_visual_fixture(self):
        source = PROJECT_FIXTURE / ".dev" / "feat-energy" / "visual" / "trace.json"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "receipt.json"
            result = subprocess.run(
                [
                    "python",
                    str(MODULE_PATH),
                    str(source),
                    "--project-root",
                    str(PROJECT_FIXTURE),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            receipt = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["status"], "valid")


if __name__ == "__main__":
    unittest.main()
