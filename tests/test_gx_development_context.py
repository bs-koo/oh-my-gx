"""개발 전후 문서 점검이 실제 원장/계획을 읽고 범위를 보존하는지 검사한다."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".claude/skills/gx-context/scripts/development.py"
PLAN_HEADER = "| ID | 작업 | 도메인 | 요구사항 | 의존 | 작업 위치 | 상태 |\n|---|---|---|---|---|---|---|\n"
LEDGER_HEADER = "| ID | 요구사항 | AC | 상태 | PR |\n|---|---|---|---|---|\n"


class DevelopmentContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gx-doc-check-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.write("src/pay.py", "LIMIT = 10\n")
        self.request = {"schema-version": 1, "goal": "결제 한도 오류 수정",
                        "sources": [{"path": None, "scope": "사용자 메시지", "message-id": "u1"}],
                        "units": [{"id": "U1", "files": ["src/pay.py"],
                                   "ac": [{"id": "AC-1", "given": "한도 10", "when": "11 결제", "then": "거절"}]}],
                        "requirements": [{"domain": "결제", "ids": ["FR-1"]}],
                        "context-paths": []}
        self.write_request()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_request(self):
        self.request_path = self.write(".dev/request.json", json.dumps(self.request, ensure_ascii=False))

    def registered(self, status="⬜", work_state="대기", location="-", pr="-"):
        self.write("context/README.md", "# 도메인\n- 결제\n")
        self.write("context/결제/status.md", LEDGER_HEADER + f"| FR-1 | 한도 초과 거부 | AC-1 | {status} | {pr} |\n")
        self.write("context/결제/architecture.md", "# 결제 구조\n한도는 서비스에서 검사한다.\n")
        self.write(".dev/plan.md", PLAN_HEADER + f"| W01 | 한도 오류 수정 | 결제 | FR-1 | - | {location} | {work_state} |\n")

    def module(self):
        self.assertTrue(HELPER.is_file(), "개발 문서 정합성 helper가 필요하다")
        spec = importlib.util.spec_from_file_location("gx_development", HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def inspect(self, **options):
        return self.module().inspect(self.root, self.request_path, "run-1", **options)

    def bytes(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def test_ordinary_implementation_without_documents_requires_registration_without_writes(self):
        before = self.bytes()
        result = self.inspect()
        self.assertEqual(result["action"], "register-required")
        self.assertFalse(result["ready-for-tdd"])
        self.assertEqual(result["next-work-id"], "W01")
        self.assertEqual(before, self.bytes())

    def test_registered_work_exposes_only_related_content_and_preserves_status(self):
        self.registered()
        self.write("context/배송/status.md", LEDGER_HEADER + "| FR-1 | PRIVATE UNRELATED TEXT | AC-9 | ✅ | #99 |\n")
        before = self.bytes()
        result = self.inspect(work_id="W01")
        self.assertTrue(result["ready-for-tdd"])
        self.assertEqual([(r["domain"], r["id"]) for r in result["requirements"]], [("결제", "FR-1")])
        self.assertNotIn("PRIVATE UNRELATED TEXT", json.dumps(result, ensure_ascii=False))
        self.assertEqual(before, self.bytes())

    def test_missing_explicit_work_is_not_created_or_silently_replaced(self):
        self.registered()
        result = self.inspect(work_id="W02")
        self.assertEqual(result["action"], "repair-required")
        self.assertFalse(result["ready-for-tdd"])
        self.assertEqual(result["work-id"], "W02")

    def test_completed_requirement_bugfix_uses_current_work_not_old_completion(self):
        self.registered(status="✅", pr="https://example.test/pr/1")
        before = self.bytes()
        result = self.inspect(work_id="W01")
        self.assertTrue(result["ready-for-tdd"])
        self.assertEqual(result["work"]["상태"], "대기")
        self.assertEqual(result["requirements"][0]["pr"], "https://example.test/pr/1")
        self.assertEqual(before, self.bytes())

    def test_readonly_intents_and_document_write_denial_do_not_create_documents(self):
        before = self.bytes()
        for intent in ("understand", "plan", "status"):
            with self.subTest(intent=intent):
                self.assertEqual(self.inspect(intent=intent)["action"], "report-only")
        self.assertEqual(self.inspect(no_document_write=True)["action"], "report-only")
        self.assertEqual(before, self.bytes())

    def test_global_unrelated_integrity_errors_are_not_hidden_by_selected_scope(self):
        self.registered()
        self.write("context/배송/status.md", LEDGER_HEADER + "| FR-1 | X | - | ⬜ | - |\n| FR-1 | Y | - | ⬜ | - |\n")
        result = self.inspect(work_id="W01")
        self.assertFalse(result["ready-for-tdd"])
        self.assertGreater(result["structural-errors"]["count"], 0)

    def test_same_run_snapshot_reuses_but_source_or_requirement_change_requires_review(self):
        self.registered()
        first = self.inspect(work_id="W01")
        previous = self.write(".dev/snapshot.json", json.dumps(first["snapshot"], ensure_ascii=False))
        self.assertEqual(self.inspect(work_id="W01", previous=previous)["action"], "reuse")
        self.write("src/pay.py", "LIMIT = 11\n")
        changed = self.inspect(work_id="W01", previous=previous, phase="post")
        self.assertEqual(changed["action"], "review-required")
        self.assertIn("src/pay.py", changed["changed-paths"])
        self.write("context/결제/status.md", LEDGER_HEADER + "| FR-1 | 새 승인 정책 | AC-1 | ⬜ | - |\n")
        self.assertIn("결제:FR-1", self.inspect(work_id="W01", previous=previous)["changed-requirements"])

    def test_different_run_or_work_snapshot_is_rejected(self):
        self.registered()
        snapshot = self.inspect(work_id="W01")["snapshot"]
        for key, value in (("run-id", "another-run"), ("work-id", "W02"), ("project-root", str(self.root.parent))):
            with self.subTest(key=key):
                changed = dict(snapshot, **{key: value})
                previous = self.write(".dev/snapshot.json", json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.inspect(work_id="W01", previous=previous)

    def test_completed_or_foreign_work_is_not_reopened(self):
        self.registered(work_state="완료")
        self.assertFalse(self.inspect(work_id="W01")["ready-for-tdd"])
        self.registered(work_state="진행", location="feat/other")
        self.assertFalse(self.inspect(work_id="W01", branch="feat/current")["ready-for-tdd"])

    def test_same_branch_different_run_is_blocked(self):
        self.registered(work_state="진행", location="feat/pay")
        self.write(".dev/feat-pay/state.md", "pipeline: gx-tdd\nstatus: in_progress\nbranch: feat/pay\nrun-id: other-run\nwork-id: W01\n")
        self.assertFalse(self.inspect(work_id="W01", branch="feat/pay")["ready-for-tdd"])

    def test_colliding_branch_slug_is_blocked_even_for_another_work_or_new_registration(self):
        self.registered()
        self.write(".dev/feat-pay/state.md", "status: in_progress\nbranch: feat/pay\nrun-id: other-run\nwork-id: W02\n")
        for options in ({"work_id": "W01"}, {}):
            with self.subTest(options=options):
                result = self.inspect(branch="feat-pay", **options)
                self.assertFalse(result["ready-for-tdd"])
                self.assertTrue(result["blockers"])

    def test_retired_requirement_blocks_implementation_without_overwriting_ledger(self):
        self.registered(status="🚫")
        before = self.bytes()
        result = self.inspect(work_id="W01")
        self.assertFalse(result["ready-for-tdd"])
        self.assertTrue(result["blockers"])
        self.assertEqual(before, self.bytes())

    def test_same_run_cannot_silently_switch_an_existing_work_binding(self):
        self.registered()
        self.write(".dev/feat-pay/state.md", "status: in_progress\nbranch: feat/pay\nrun-id: run-1\nwork-id: W02\ngoal: 기존 작업\n")
        before = self.bytes()
        result = self.inspect(work_id="W01", branch="feat/pay")
        self.assertFalse(result["ready-for-tdd"])
        self.assertTrue(result["blockers"])
        self.assertEqual(before, self.bytes())

    def test_supplied_requirement_pointer_must_match_local_domain_ledger(self):
        self.registered()
        for path in ("../outside/status.md", "context/배송/status.md"):
            with self.subTest(path=path):
                self.request["requirements"][0]["path"] = path
                self.write_request()
                with self.assertRaises(ValueError):
                    self.inspect(work_id="W01")
        self.request["requirements"][0]["path"] = "context/결제/status.md"
        self.write_request()
        self.assertTrue(self.inspect(work_id="W01")["ready-for-tdd"])

    def test_stdin_discovery_and_summary_need_no_project_artifacts(self):
        project = self.root / "fresh"
        project.mkdir()
        before = self.bytes()
        command = [sys.executable, str(HELPER), "inspect", "--project-root", str(project),
                   "--plan", "-", "--run-id", "run-readonly", "--intent", "understand"]
        result = subprocess.run(command, input=json.dumps({"goal": "결제 파악", "units": []}),
                                capture_output=True, text=True, encoding="utf-8", timeout=15,
                                env=dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp949"))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["action"], "report-only")
        summary = subprocess.run([sys.executable, str(HELPER), "summary", "--report", "-"],
                                 input=result.stdout, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertEqual(json.loads(summary.stdout)["goal"], "결제 파악")
        self.assertEqual(before, self.bytes())

    def test_previous_full_report_is_supported_but_malformed_snapshot_is_rejected(self):
        self.registered()
        report = self.inspect(work_id="W01")
        previous = self.write(".dev/prior.json", json.dumps(report))
        self.assertEqual(self.inspect(work_id="W01", previous=previous)["action"], "reuse")
        for key, value in (("input-digest", "bad"), ("global-digest", None),
                           ("requirements", {"../escape:FR-1": "a" * 64})):
            with self.subTest(key=key):
                changed = dict(report["snapshot"], **{key: value})
                self.write(".dev/prior.json", json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.inspect(work_id="W01", previous=previous)

    def test_requirement_alias_and_huge_range_fail_closed(self):
        self.registered()
        for ref in ("FR-01", "FR-1~0002", "FR-1~999999999"):
            with self.subTest(ref=ref):
                self.write(".dev/plan.md", PLAN_HEADER + f"| W01 | 작업 | 결제 | {ref} | - | - | 대기 |\n")
                self.assertFalse(self.inspect(work_id="W01")["ready-for-tdd"])

    def test_work_ids_continue_past_two_digits_without_reuse(self):
        # 작업 ID는 `W` + 두 자리 이상 숫자다. W99 다음은 W100이며 범위 소진으로 막거나 ID를 재사용하지 않는다.
        self.registered(work_state="완료")
        self.write(".dev/plan.md", PLAN_HEADER + "| W99 | 완료 | 결제 | FR-1 | - | - | 완료 |\n")
        result = self.inspect()
        self.assertEqual(result["next-work-id"], "W100")
        self.assertEqual(result["structural-errors"]["count"], 0)
        self.assertFalse(any("소진" in blocker for blocker in result["blockers"]))
        self.write(".dev/plan.md", PLAN_HEADER + "| W118 | 완료 | 결제 | FR-1 | - | - | 완료 |\n")
        self.assertEqual(self.inspect()["next-work-id"], "W119")

    def test_three_or_more_digit_work_ids_are_selected_like_two_digit_ids(self):
        self.registered()
        for work in ("W118", "W1000"):
            with self.subTest(work=work):
                self.write(".dev/plan.md", PLAN_HEADER + f"| {work} | 한도 오류 수정 | 결제 | FR-1 | - | - | 대기 |\n")
                result = self.inspect(work_id=work)
                self.assertTrue(result["ready-for-tdd"], result["structural-errors"])
                self.assertEqual(result["work"]["ID"], work)

    def test_malformed_work_ids_are_rejected(self):
        self.registered()
        for work in ("W1", "W０１", "W-01", "w01", "W01\n", "W١٢"):
            with self.subTest(work=work):
                with self.assertRaisesRegex(ValueError, "work-id"):
                    self.inspect(work_id=work)

    def test_external_document_and_dev_directory_symlinks_are_rejected(self):
        self.registered()
        with tempfile.TemporaryDirectory(prefix="gx-outside-") as directory:
            outside = Path(directory)
            (outside / "status.md").write_text(LEDGER_HEADER, encoding="utf-8")
            link = self.root / "context/外部/status.md"
            link.parent.mkdir()
            try:
                link.symlink_to(outside / "status.md")
            except OSError:
                self.skipTest("symlink unavailable")
            with self.assertRaises(ValueError):
                self.inspect(work_id="W01")

    def test_invalid_previous_and_source_escape_are_not_treated_as_cache_miss(self):
        self.registered()
        previous = self.write(".dev/bad.json", "{broken")
        with self.assertRaises(ValueError):
            self.inspect(work_id="W01", previous=previous)
        self.request["sources"] = [{"path": "../outside.md", "scope": "all"}]
        self.write_request()
        with self.assertRaises(ValueError):
            self.inspect(work_id="W01")

    def test_compact_summary_keeps_actions_without_echoing_snapshot_or_source_content(self):
        self.registered()
        module = self.module()
        result = module.inspect(self.root, self.request_path, "run-1", work_id="W01")
        summary = module.summarize(result)
        self.assertEqual(summary["action"], result["action"])
        self.assertNotIn("snapshot", summary)
        self.assertNotIn("LIMIT = 10", json.dumps(summary))
        self.assertEqual(summary["requirements"][0]["id"], "FR-1")

    def test_dev_directory_link_cannot_change_the_project_boundary(self):
        with tempfile.TemporaryDirectory(prefix="gx-dev-outside-") as directory:
            project = self.root / "other-project"
            project.mkdir()
            outside = Path(directory)
            (outside / "request.json").write_text(json.dumps(self.request), encoding="utf-8")
            try:
                (project / ".dev").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlink unavailable")
            with self.assertRaises(ValueError):
                self.module().inspect(project, project / ".dev/request.json", "run-1")

    def test_cli_is_readonly_and_does_not_create_import_cache_in_installed_skill(self):
        self.registered()
        installed = self.root / "installed"
        installed.mkdir()
        self.assertTrue(HELPER.is_file(), "개발 helper가 필요하다")
        (installed / "development.py").write_bytes(HELPER.read_bytes())
        (installed / "plan.py").write_bytes(HELPER.with_name("plan.py").read_bytes())
        before = self.bytes()
        result = subprocess.run([sys.executable, str(installed / "development.py"), "inspect",
                                 "--project-root", str(self.root), "--plan", str(self.request_path),
                                 "--run-id", "run-1", "--work", "W01", "--phase", "pre"],
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ready-for-tdd"])
        self.assertEqual(before, self.bytes())


if __name__ == "__main__":
    unittest.main()
