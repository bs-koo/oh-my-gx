"""단독 GREEN 보존과 humanizer 예약·복구의 실제 파일 회귀."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gx 보존 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()  # Windows 8.3 짧은 임시 경로 정규화
        self.helper = load("gx-test-integrity")
        self.write("test/current.test.js", "test('new', () => assert.equal(value(), 2));\n")
        self.write("test/existing.test.js", "test('old', () => assert.equal(value(), 1));\n")
        self.write("checks/한글.custom", "assert old behavior\n")
        self.write("package.json", '{}')
        self.write(".claude/config.json", json.dumps({"projectTypes": {"node": {
            "detect": ["package.json"], "testSelection": {"tests": ["checks/*.custom"]}}}}))
        self.baseline = self.root / ".dev" / "green-baseline.json"

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def capture(self):
        return self.helper.capture(self.root, self.baseline)

    def test_source_changes_preserve_dirty_and_untracked_test_baseline(self):
        baseline = self.capture()
        self.write("src/value.js", "module.exports = 2;\n")
        self.assertTrue(self.helper.verify(self.root, self.baseline, baseline["baseline_sha256"])["unchanged"])
        self.assertIn("checks/한글.custom", baseline["files"])
        self.assertIn("test/existing.test.js", baseline["files"])

    def test_other_test_deletion_skip_and_config_change_are_detected(self):
        for change in ("delete", "skip", "custom", "config", "new"):
            with self.subTest(change=change):
                baseline_path = self.root / ".dev" / (change + ".json")
                before = self.helper.capture(self.root, baseline_path)
                if change == "delete":
                    (self.root / "test/existing.test.js").unlink()
                elif change == "skip":
                    self.write("test/existing.test.js", "test.skip('old', () => {});\n")
                elif change == "custom":
                    self.write("checks/한글.custom", "skip old behavior\n")
                elif change == "config":
                    self.write(".claude/config.json", '{"projectTypes": {}}')
                else:
                    self.write("test/extra.test.js", "test.skip('extra', () => {});\n")
                result = self.helper.verify(self.root, baseline_path, before["baseline_sha256"])
                self.assertFalse(result["unchanged"])
                # 각 변조는 다음 subtest 전에 원래 내용으로 복원한다.
                self.write("test/existing.test.js", "test('old', () => assert.equal(value(), 1));\n")
                self.write("checks/한글.custom", "assert old behavior\n")
                self.write(".claude/config.json", json.dumps({"projectTypes": {"node": {
                    "detect": ["package.json"], "testSelection": {"tests": ["checks/*.custom"]}}}}))
                (self.root / "test/extra.test.js").unlink(missing_ok=True)

    def test_baseline_cannot_be_overwritten_or_replaced_to_hide_mutation(self):
        before = self.capture()
        self.write("test/existing.test.js", "test.skip('old', () => {});\n")
        with self.assertRaises((ValueError, FileExistsError)):
            self.capture()
        self.baseline.write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "baseline|기준선"):
            self.helper.verify(self.root, self.baseline, before["baseline_sha256"])

    def test_invalid_config_and_missing_tests_block_capture(self):
        self.write(".claude/config.json", '{broken')
        with self.assertRaises(ValueError):
            self.capture()

    def test_capture_requires_real_tests_and_runner_config_is_protected(self):
        for path in ("test/current.test.js", "test/existing.test.js", "checks/한글.custom"):
            (self.root / path).unlink()
        with self.assertRaises(ValueError):
            self.capture()

    def test_nested_custom_test_and_runner_config_are_included(self):
        self.write("apps/api/package.json", '{}')
        self.write("apps/api/scenarios/login.case", "assert\n")
        self.write(".claude/config.json", json.dumps({"projectTypes": {"node": {
            "detect": ["package.json"], "roots": ["apps/api"],
            "testSelection": {"tests": ["scenarios/*.case"]}}}}))
        before = self.capture()
        self.assertIn("apps/api/scenarios/login.case", before["files"])
        self.write("apps/api/package.json", '{"scripts":{"test":"echo pass"}}')
        self.assertFalse(self.helper.verify(self.root, self.baseline, before["baseline_sha256"])["unchanged"])

    def test_path_detect_marker_resolves_the_project_root_for_custom_tests(self):
        self.write("backend/build.gradle.kts", "")
        self.write("backend/scenarios/login.case", "assert\n")
        self.write("api/backend/build.gradle.kts", "")
        self.write("api/backend/scenarios/other.case", "assert\n")
        self.write(".claude/config.json", json.dumps({"projectTypes": {"java-spring": {
            "detect": ["backend/build.gradle.kts"], "testSelection": {"tests": ["scenarios/*.case"]}}}}))
        files = self.capture()["files"]
        self.assertIn("backend/scenarios/login.case", files)
        self.assertNotIn("api/backend/scenarios/other.case", files)

    def test_runner_configuration_alone_is_not_a_test_inventory(self):
        for path in ("test/current.test.js", "test/existing.test.js", "checks/한글.custom"):
            (self.root / path).unlink()
        self.write("apps/api/package.json", '{}')
        with self.assertRaises(ValueError):
            self.capture()

    def test_malformed_selection_is_blocked_as_value_error(self):
        self.write(".claude/config.json", json.dumps({"projectTypes": {"node": {"testSelection": []}}}))
        with self.assertRaises(ValueError):
            self.capture()

    def test_custom_tests_with_unresolved_project_roots_are_not_silently_omitted(self):
        self.write(".claude/config.json", json.dumps({"projectTypes": {"unknown": {
            "detect": ["missing.project"], "testSelection": {"tests": ["checks/*.custom"]}}}}))
        with self.assertRaises(ValueError):
            self.capture()


    def test_shared_transpiler_browser_and_wrapper_config_mutations_are_detected(self):
        configurations = ['.babelrc', '.babelrc.json', 'babel.config.cjs', 'tsconfig.json',
                          'tsconfig.strict.json', '.swcrc', '.browserslistrc', 'browserslist',
                          'gradlew', 'gradlew.bat', '.npmrc', 'apps/web/webpack.config.js']
        for index, name in enumerate(configurations):
            with self.subTest(name=name):
                self.write(name, 'before\n')
                path = self.root / '.dev' / f'configuration-{index}.json'
                baseline = self.helper.capture(self.root, path)
                self.write(name, 'after\n')
                result = self.helper.verify(self.root, path, baseline['baseline_sha256'])
                self.assertFalse(result['unchanged'], name)
                self.assertIn(name, result['changed'])

    def test_scan_permission_failure_blocks_capture_and_verify(self):
        restricted = self.root / 'restricted'
        self.write('restricted/hidden.test.js', 'test hidden behavior\n')
        original_scandir = self.helper.os.scandir

        def denied(path):
            if Path(path) == restricted:
                raise PermissionError(13, 'scan denied', str(restricted))
            return original_scandir(path)

        with patch.object(self.helper.os, 'scandir', side_effect=denied):
            with self.assertRaisesRegex(OSError, 'scan denied'):
                self.capture()
        self.assertFalse(self.baseline.exists())
        baseline = self.capture()
        with patch.object(self.helper.os, 'scandir', side_effect=denied):
            with self.assertRaisesRegex(OSError, 'scan denied'):
                self.helper.verify(self.root, self.baseline, baseline['baseline_sha256'])

    def test_runner_cache_and_build_outputs_are_not_fingerprinted(self):
        # H2: RED 뒤 capture, GREEN에서 테스트 재실행만 해도 캐시·산출물이 바뀐다.
        caches = [".pytest_cache/v/cache/lastfailed", "target/surefire-reports/TEST-A.xml",
                  "target/test-classes/ATest.class", "test-results/out.xml", "out/test/a.test.js",
                  "build/reports/tests/index.html", "venv/lib/test_x.py", ".venv/lib/test_y.py",
                  "node_modules/pkg/index.test.js", "coverage/lcov.info"]
        for name in caches:
            self.write(name, "before\n")
        baseline = self.capture()
        for name in caches:
            self.assertNotIn(name, baseline["files"])
            self.write(name, "after\n")
        self.assertTrue(self.helper.verify(self.root, self.baseline, baseline["baseline_sha256"])["unchanged"])

    def test_git_ignored_paths_are_not_fingerprinted(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.write(".gitignore", "generated/\n")
        self.write("generated/gen.test.js", "before\n")
        baseline = self.capture()
        self.assertNotIn("generated/gen.test.js", baseline["files"])
        self.assertIn("test/existing.test.js", baseline["files"])

    def test_production_files_with_test_like_substrings_are_not_tests(self):
        production = ["src/main/java/aop/LoggingAspect.java", "src/main/java/latest/Feed.java",
                      "src/main/java/repo/UserSpecification.java", "src/contest/Entry.java"]
        for name in production:
            self.write(name, "class A {}\n")
        baseline = self.capture()
        for name in production:
            self.assertNotIn(name, baseline["files"])
            self.write(name, "class A { int x; }\n")
        self.assertTrue(self.helper.verify(self.root, self.baseline, baseline["baseline_sha256"])["unchanged"])

    def test_test_naming_conventions_are_fingerprinted(self):
        tests = ["src/test/java/a/CalcTest.java", "x/CalcTests.java", "x/CalcIT.java",
                 "pkg/test_calc.py", "pkg/calc_test.py", "web/a.test.ts", "web/a.spec.tsx",
                 "cypress/e2e/login.cy.js", "web/__tests__/a.js", "tests/helper.py"]
        for name in tests:
            self.write(name, "x\n")
        baseline = self.capture()
        for name in tests:
            self.assertIn(name, baseline["files"])

    def test_application_config_is_not_protected_but_runner_config_is(self):
        apps = ["app.config.ts", "next.config.js", "tailwind.config.js", "postcss.config.cjs"]
        runners = ["jest.config.js", "vitest.config.ts", "karma.conf.js", "karma.config.js",
                   "playwright.config.ts", "cypress.config.js", "pytest.ini", "tox.ini"]
        for name in apps + runners:
            self.write(name, "before\n")
        baseline = self.capture()
        for name in apps:
            self.assertNotIn(name, baseline["files"])
        for name in runners:
            self.assertIn(name, baseline["files"])
            self.write(name, "after\n")
        for name in apps:
            self.write(name, "after\n")
        result = self.helper.verify(self.root, self.baseline, baseline["baseline_sha256"])
        self.assertEqual(result["changed"], sorted(runners))

    def test_dependency_changes_are_reported_separately_from_test_tampering(self):
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}, "dependencies": {"a": "1"}}))
        self.write("package-lock.json", "{}")
        self.write("requirements.txt", "a==1\n")
        baseline = self.capture()
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}, "dependencies": {"a": "2", "b": "1"}}))
        self.write("package-lock.json", '{"x":1}')
        self.write("requirements.txt", "a==2\n")
        result = self.helper.verify(self.root, self.baseline, baseline["baseline_sha256"])
        self.assertTrue(result["unchanged"])
        self.assertEqual(result["dependency_changed"], ["package-lock.json", "package.json", "requirements.txt"])
        # 테스트 스크립트 변경은 여전히 변조다.
        self.write("package.json", json.dumps({"scripts": {"test": "echo pass"}, "dependencies": {"a": "1"}}))
        result = self.helper.verify(self.root, self.baseline, baseline["baseline_sha256"])
        self.assertFalse(result["unchanged"])
        self.assertIn("package.json", result["changed"])

    def test_cli_output_is_utf8_without_inherited_encoding_variables(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO")}
        self.write("checks/😀한글.test.js", "x\n")
        command = [sys.executable, str(ROOT / "scripts/gx-test-integrity.py"), "capture",
                   "--cwd", str(self.root), "--baseline", str(self.root / ".dev" / "cli.json")]
        result = subprocess.run(command, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("checks/😀한글.test.js", json.loads(result.stdout.decode("utf-8"))["files"])


class HumanizerRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gx 윤문 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()  # Windows 8.3 짧은 임시 경로 정규화
        self.helper = load("gx-humanizer-run")
        self.metadata = {"mode": "strict", "genre": "학술/리포트", "tone": "격식체",
                         "scope": "3장만", "sources": ["보고서.md"]}

    def reserve(self):
        return self.helper.reserve(self.root, self.metadata, "2026-11-10")

    def input(self, run):
        self.helper.freeze_input(self.root, run["run_id"], "수치는 50%다.\n".encode("utf-8"))

    def audit(self, run, round_number, rewrite, verdict):
        folder = self.root / ".humanize" / run["run_id"]
        (folder / "03_rewrite.md").write_text(rewrite, encoding="utf-8")
        import hashlib
        expected = hashlib.sha256((folder / "03_rewrite.md").read_bytes()).hexdigest()
        report = {"meta": {"run_id": run["run_id"], "round": round_number,
                           "rewrite_sha256": expected, "audit_verdict": verdict, "edits_rollback": 0},
                  "flagged_edits": []}
        (folder / "04_fidelity.json").write_text(json.dumps(report), encoding="utf-8")
        return self.helper.archive_round(self.root, run["run_id"], round_number, expected)

    def test_failed_or_incomplete_run_is_used_and_original_input_remains(self):
        run = self.reserve()
        self.input(run)
        original = self.root / ".humanize" / run["run_id"] / "01_input.txt"
        before = original.read_bytes()
        self.assertEqual(self.reserve()["run_id"], "2026-11-10-002")
        self.assertEqual(original.read_bytes(), before)
        with self.assertRaises((ValueError, FileExistsError)):
            self.helper.freeze_input(self.root, run["run_id"], b"different input")

    def test_reservation_uses_existing_directories_above_999(self):
        (self.root / ".humanize" / "2026-11-10-999").mkdir(parents=True)
        self.assertEqual(self.reserve()["run_id"], "2026-11-10-1000")

    def test_concurrent_cli_reservations_have_unique_ids_and_metadata(self):
        command = [sys.executable, str(ROOT / "scripts/gx-humanizer-run.py"), "reserve",
                   "--cwd", str(self.root), "--date", "2026-11-10", "--mode", "strict",
                   "--genre", "학술/리포트", "--tone", "격식체", "--scope", "3장만", "--source", "보고서.md"]
        def invoke(_):
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True)
            return json.loads(result.stdout)
        with ThreadPoolExecutor(max_workers=4) as pool:
            runs = list(pool.map(invoke, range(8)))
        self.assertEqual(len({run["run_id"] for run in runs}), 8)
        for run in runs:
            saved = json.loads((self.root / ".humanize" / run["run_id"] / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["metadata"], self.metadata)

    def test_cli_output_is_utf8_without_inherited_encoding_variables(self):
        # Windows 파이프의 기본 stdout은 cp949다. 실행 환경 변수에 기대지 않고 UTF-8 JSON을 내야 한다.
        env = {k: v for k, v in os.environ.items()
               if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO")}
        command = [sys.executable, str(ROOT / "scripts/gx-humanizer-run.py"), "reserve",
                   "--cwd", str(self.root), "--date", "2026-11-10", "--mode", "strict",
                   "--genre", "학술/리포트 😀", "--tone", "격식체", "--scope", "3장만", "--source", "보고서.md"]
        result = subprocess.run(command, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        run = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(run["metadata"]["genre"], "학술/리포트 😀")
        self.assertEqual(Path(run["directory"]), self.root / ".humanize" / run["run_id"])

    def test_empty_source_is_blocked_and_not_frozen(self):
        run = self.reserve()
        command = [sys.executable, str(ROOT / "scripts/gx-humanizer-run.py"), "freeze-input",
                   "--cwd", str(self.root), "--run-id", run["run_id"]]
        result = subprocess.run(command, input=b"  \n", capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertTrue(json.loads(result.stdout.decode("utf-8"))["blocked"])
        self.assertFalse((self.root / ".humanize" / run["run_id"] / "01_input.txt").exists())

    def test_missing_scope_metadata_and_path_escape_are_rejected(self):
        for field in ("genre", "tone", "scope", "sources"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                metadata = dict(self.metadata)
                metadata.pop(field)
                self.helper.reserve(self.root, metadata, "2026-11-10")
        with self.assertRaises(ValueError):
            self.helper.freeze_input(self.root, "../escape", b"data")

    def test_fidelity_safe_snapshot_survives_later_failed_overwrite_and_restart(self):
        run = self.reserve()
        self.input(run)
        first = "数値は50%です。\n---diff---\ne001: wording\n"
        self.audit(run, 0, first, "full_pass")
        self.audit(run, 1, "数値は500%です。", "fail")
        safe = load("gx-humanizer-run").select_safe(self.root, run["run_id"])
        self.assertEqual(Path(safe["source"]).read_text(encoding="utf-8"), first)
        self.assertEqual(safe["round"], 0)
        with self.assertRaises(ValueError):
            self.audit(run, 3, "unsafe third rewrite", "full_pass")

    def test_no_pass_falls_back_to_frozen_input_and_tampering_is_blocked(self):
        run = self.reserve()
        self.input(run)
        self.audit(run, 0, "수치는 500%다.", "fail")
        self.assertEqual(self.helper.select_safe(self.root, run["run_id"])["round"], None)
        folder = self.root / ".humanize" / run["run_id"]
        (folder / "01_input.txt").write_text("변조", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.helper.select_safe(self.root, run["run_id"])

    def test_audit_rewrite_hash_and_immutable_round_are_checked(self):
        run = self.reserve()
        self.input(run)
        self.audit(run, 0, "safe", "full_pass")
        with self.assertRaises((ValueError, FileExistsError)):
            self.audit(run, 0, "replacement", "full_pass")
        with self.assertRaises(ValueError):
            self.helper.archive_round(self.root, run["run_id"], 1, "0" * 64)

    def test_stale_fidelity_report_is_not_evidence_for_new_round(self):
        run = self.reserve()
        self.input(run)
        checkpoint = self.audit(run, 0, "safe", "full_pass")
        with self.assertRaises(ValueError):
            self.helper.archive_round(self.root, run["run_id"], 1, checkpoint["rewrite_sha256"])

    def test_changed_confirmed_metadata_is_not_silently_reused(self):
        run = self.reserve()
        self.input(run)
        path = self.root / ".humanize" / run["run_id"] / "run.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["metadata"]["genre"] = "blog"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.helper.select_safe(self.root, run["run_id"])

    def test_history_on_absent_directory_does_not_create_files(self):
        self.assertEqual(self.helper.history(self.root), {"runs": []})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_history_reports_legacy_and_incomplete_without_body_or_writes(self):
        legacy = self.root / ".humanize" / "2026-11-10-001"
        legacy.mkdir(parents=True)
        (legacy / "final.md").write_text("PRIVATE ORIGINAL BODY", encoding="utf-8")
        broken = self.root / ".humanize" / "2026-11-10-002"
        broken.mkdir()
        (broken / "run.json").write_text("{broken", encoding="utf-8")
        run = self.reserve()
        self.input(run)
        before = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        result = self.helper.history(self.root)
        self.assertEqual([row["run_id"] for row in result["runs"]],
                         [run["run_id"], "2026-11-10-002", "2026-11-10-001"])
        self.assertEqual(result["runs"][0]["genre"], "학술/리포트")
        self.assertEqual(result["runs"][0]["status"], "in_progress")
        self.assertEqual(result["runs"][-1]["status"], "legacy_unverified")
        self.assertEqual(result["runs"][1]["status"], "incomplete")
        self.assertNotIn("PRIVATE ORIGINAL BODY", json.dumps(result))
        self.assertEqual(before, {str(path.relative_to(self.root)): path.read_bytes()
                                  for path in self.root.rglob('*') if path.is_file()})
        self.assertEqual(self.helper.history(self.root, "2026-11-10-999"), {"runs": []})

    def test_history_cli_selects_run_without_reservation(self):
        run = self.reserve()
        folder = self.root / ".humanize" / run["run_id"]
        (folder / "final.md").write_text("PRIVATE", encoding="utf-8")
        (folder / "summary.md").write_text("PRIVATE", encoding="utf-8")
        command = [sys.executable, str(ROOT / "scripts/gx-humanizer-run.py"), "history",
                   "--cwd", str(self.root), "--run-id", run["run_id"]]
        before = sorted(str(path) for path in self.root.rglob('*'))
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True)
        row = json.loads(result.stdout)["runs"][0]
        self.assertEqual(row["status"], "outputs_present")
        self.assertEqual(row["verification"], "unverified")
        self.assertNotIn("PRIVATE", result.stdout)
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))

    def test_history_malformed_metadata_is_a_partial_row_and_numeric_order_is_used(self):
        for identifier, value in (("2026-11-10-999", {"schema": 1, "run_id": "2026-11-10-999", "metadata": []}),
                                  ("2026-11-10-1000", [])):
            folder = self.root / ".humanize" / identifier
            folder.mkdir(parents=True)
            (folder / "run.json").write_text(json.dumps(value), encoding="utf-8")
        rows = self.helper.history(self.root)["runs"]
        self.assertEqual([row["run_id"] for row in rows], ["2026-11-10-1000", "2026-11-10-999"])
        self.assertEqual([row["status"] for row in rows], ["incomplete", "incomplete"])


    def naturalness(self, run, checkpoint, rewrite_sha=None):
        path = self.root / '.humanize' / run['run_id'] / '05_naturalness.json'
        value = {'meta': {'run_id': run['run_id'], 'round': checkpoint['round'],
                          'rewrite_sha256': rewrite_sha or checkpoint['rewrite_sha256'],
                          'verdict': 'accept', 'human_intervention_required': False},
                 'next_action': {'verdict': 'accept', 'targets': []}}
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_naturalness_for_replaced_working_draft_cannot_approve_saved_fidelity_draft(self):
        import hashlib
        run = self.reserve()
        self.input(run)
        checkpoint = self.audit(run, 0, 'fidelity draft A', 'full_pass')
        folder = self.root / '.humanize' / run['run_id']
        (folder / '03_rewrite.md').write_text('naturalness draft B', encoding='utf-8')
        self.naturalness(run, checkpoint, hashlib.sha256(b'naturalness draft B').hexdigest())
        with self.assertRaises(ValueError):
            self.helper.archive_naturalness(self.root, run['run_id'], 0, checkpoint['rewrite_sha256'])
        with self.assertRaises((ValueError, OSError)):
            self.helper.select_safe(self.root, run['run_id'], require_naturalness=True,
                                    round_number=0, rewrite_sha256=checkpoint['rewrite_sha256'])

    def test_both_reviews_approve_exact_immutable_draft_and_tampering_blocks_completion(self):
        run = self.reserve()
        self.input(run)
        checkpoint = self.audit(run, 0, 'immutable draft A', 'full_pass')
        folder = self.root / '.humanize' / run['run_id']
        (folder / '03_rewrite.md').write_text('unreviewed working draft B', encoding='utf-8')
        self.naturalness(run, checkpoint)
        self.helper.archive_naturalness(self.root, run['run_id'], 0, checkpoint['rewrite_sha256'])
        selected = self.helper.select_safe(self.root, run['run_id'], require_naturalness=True,
                                           round_number=0, rewrite_sha256=checkpoint['rewrite_sha256'])
        self.assertEqual(selected['rewrite_sha256'], checkpoint['rewrite_sha256'])
        self.assertEqual(Path(selected['source']).read_text(encoding='utf-8'), 'immutable draft A')
        (folder / 'rounds/000/05_naturalness.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.helper.select_safe(self.root, run['run_id'], require_naturalness=True,
                                    round_number=0, rewrite_sha256=checkpoint['rewrite_sha256'])


class AuxiliaryConsumerContracts(unittest.TestCase):
    def test_green_invokes_whole_test_integrity_and_preserves_baseline(self):
        text = (ROOT / ".claude/skills/gx-green/SKILL.md").read_text(encoding="utf-8")
        for phrase in ("gx-test-integrity.py", "baseline_sha256", "미추적", "skip", "재생성"):
            self.assertIn(phrase, text)

    def test_strict_passes_original_and_confirmed_metadata_and_uses_saved_safe_round(self):
        strict = (ROOT / ".claude/skills/gx-humanizer/references/strict.md").read_text(encoding="utf-8")
        role = (ROOT / "agents/humanizer-naturalness.md").read_text(encoding="utf-8")
        skill = (ROOT / ".claude/skills/gx-humanizer/SKILL.md").read_text(encoding="utf-8")
        for phrase in ("01_input.txt", "run.json", "genre", "tone", "scope"):
            self.assertIn(phrase, strict)
            self.assertIn(phrase, role)
        for phrase in ("gx-humanizer-run.py", "reserve", "archive-round", "safe"):
            self.assertIn(phrase, skill + strict)
        self.assertIn("  - Bash", skill)
        self.assertNotIn(".humanize/{오늘}-*/summary.md", skill)

    def test_history_routes_before_mode_question_and_never_reserves(self):
        skill = (ROOT / ".claude/skills/gx-humanizer/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("history", skill.split("---", 2)[1])
        query = skill[skill.index("### 이력 조회"):skill.index("### Step 0:")]
        self.assertIn("history --cwd", query)
        self.assertIn("예약하지", query)
        self.assertIn("본문", query)


    def test_documented_history_flag_and_strict_final_digest_contract_are_consumed(self):
        skill = (ROOT / '.claude/skills/gx-humanizer/SKILL.md').read_text(encoding='utf-8')
        query = skill[skill.index('### 이력 조회'):skill.index('### Step 0:')]
        self.assertIn('--history [run-id]', query)
        strict = (ROOT / '.claude/skills/gx-humanizer/references/strict.md').read_text(encoding='utf-8')
        naturalness = strict.split('#### S3.', 1)[1].split('#### 재윤문', 1)[0]
        for phrase in ('rewrite_sha256', 'rounds/', 'archive-naturalness'):
            self.assertIn(phrase, naturalness)
        self.assertIn('--require-naturalness', strict.split('#### S4.', 1)[1])
        role = (ROOT / 'agents/humanizer-naturalness.md').read_text(encoding='utf-8')
        self.assertIn('rewrite_sha256', role)
        self.assertIn('rewrite_path', role)


if __name__ == "__main__":
    unittest.main()
