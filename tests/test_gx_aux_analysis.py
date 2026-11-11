"""분석 보조 스킬의 파일 경계·오류 분류를 실제 CLI와 임시 프로젝트로 확인한다."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AuxAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gx 분석 한글 ")
        self.addCleanup(self.temp.cleanup)
        # Windows CI의 임시 폴더는 8.3 짧은 이름(RUNNER~1)이라 helper가 정규화한 경로와 비교하려면 먼저 정규화한다.
        self.project = Path(self.temp.name).resolve() / "project with spaces"
        self.project.mkdir()

    def cli(self, script, *arguments, stdin=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *map(str, arguments)],
            input=stdin, cwd=self.project, capture_output=True, text=True, encoding="utf-8",
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"),
        )

    def invoke(self, script, *arguments, stdin=None):
        result = self.cli(script, *arguments, stdin=stdin)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def write(self, path, text=""):
        target = self.project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): p.read_bytes()
                for p in self.project.rglob("*") if p.is_file()}

    def scan(self, source="existing"):
        return self.invoke("gx-setup-scan.py", "--cwd", self.project, "--config-source", source)

    def test_new_template_does_not_confirm_gradle_and_nested_frontend(self):
        self.write("build.gradle", "plugins {}")
        self.write("frontend/package.json", '{"scripts":{"test":"vitest run"}}')
        template = (ROOT / ".claude/skills/gx-setup/references/config.template.json").read_text(encoding="utf-8")
        self.write(".claude/config.json", template)
        before = self.snapshot()
        report = self.scan("template")
        self.assertTrue(report["requires_confirmation"])
        self.assertEqual([item["path"] for item in report["markers"]],
                         ["build.gradle", "frontend/package.json"])
        self.assertTrue(all(item["needs_confirmation"] for item in report["markers"]))
        self.assertEqual(self.snapshot(), before)

    def test_existing_explicit_roots_are_preserved_while_new_stack_is_reported(self):
        self.write("frontend/package.json", "{}")
        self.write("backend/pom.xml", "<project/>")
        self.write(".claude/config.json", json.dumps({"projectTypes": {
            "custom-web": {"detect": ["package.json"], "roots": ["frontend"],
                           "test": "pnpm test", "userField": {"keep": True}}}}))
        before = self.snapshot()
        report = self.scan()
        records = {item["path"]: item for item in report["markers"]}
        self.assertEqual(records["frontend/package.json"]["registered_types"], ["custom-web"])
        self.assertFalse(records["frontend/package.json"]["needs_confirmation"])
        self.assertTrue(records["backend/pom.xml"]["needs_confirmation"])
        self.assertEqual(self.snapshot(), before)

    def make_link(self, link, target):
        link = self.project / link
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                  capture_output=True, text=True)
            if done.returncode == 0:
                return
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("junction/symlink를 만들 수 없는 환경")

    def test_linked_subproject_is_reported_and_requires_confirmation(self):
        outside = Path(self.temp.name).resolve() / "outside-module"
        outside.mkdir()
        (outside / "package.json").write_text("{}", encoding="utf-8")
        self.write("pom.xml", "<project/>")
        self.write(".claude/config.json", json.dumps({"projectTypes": {
            "java": {"detect": ["pom.xml"]}}}))
        self.make_link("modules/linked", outside)
        report = self.scan()
        self.assertEqual([item["path"] for item in report["markers"]], ["pom.xml"])
        self.assertEqual(report["skipped_links"], ["modules/linked"])
        self.assertTrue(report["requires_confirmation"])

    def test_custom_detect_markers_are_scanned_outside_the_builtin_catalog(self):
        self.write("engine/build.zig", "pub fn build() void {}")
        self.write("other/build.zig", "pub fn build() void {}")
        self.write("node_modules/vendor/build.zig", "generated")
        self.write(".claude/config.json", json.dumps({"projectTypes": {
            "zig": {"detect": ["build.zig"], "roots": ["engine"], "test": "zig build test"}}}))
        before = self.snapshot()
        report = self.scan()
        records = {item["path"]: item for item in report["markers"]}
        self.assertEqual(set(records), {"engine/build.zig", "other/build.zig"})
        self.assertEqual(records["engine/build.zig"]["registered_types"], ["zig"])
        self.assertFalse(records["engine/build.zig"]["needs_confirmation"])
        self.assertTrue(records["other/build.zig"]["needs_confirmation"])
        self.assertEqual(self.snapshot(), before)

    def test_registered_root_does_not_cover_another_root_and_generated_markers_are_excluded(self):
        self.write("package.json", "{}")
        self.write("other/package.json", "{}")
        self.write("node_modules/tool/package.json", "{}")
        self.write(".claude/worktrees/old/package.json", "{}")
        self.write(".research/old/package.json", "{}")
        self.write(".next/cache/package.json", "{}")
        self.write(".claude/config.json", json.dumps({"projectTypes": {
            "node": {"detect": ["package.json"], "roots": ["."], "test": "npm test"}}}))
        report = self.scan()
        records = {item["path"]: item for item in report["markers"]}
        self.assertEqual(set(records), {"package.json", "other/package.json"})
        self.assertFalse(records["package.json"]["needs_confirmation"])
        self.assertTrue(records["other/package.json"]["needs_confirmation"])

    def test_path_detect_markers_follow_the_test_plan_rules(self):
        self.write("backend/build.gradle.kts", "")
        self.write("frontend/package.json", "{}")
        self.write("tools/frontend/package.json", "{}")
        self.write("package.json", "{}")
        self.write(".claude/config.json", json.dumps({"projectTypes": {
            "java-spring": {"detect": ["backend/build.gradle.kts"], "test": "cd backend && ./gradlew test"},
            "node": {"detect": ["frontend/package.json"], "test": "pnpm test"},
            "root": {"detect": ["**/package.json"], "roots": ["."], "test": "npm test"},
            "fullstack": {"detect": ["frontend/package.json"], "roots": ["."], "test": "make test"}}}))
        records = {item["path"]: item for item in self.scan()["markers"]}
        self.assertEqual(records["backend/build.gradle.kts"]["registered_types"], ["java-spring"])
        # A path marker counts anywhere under an explicit root; a name marker only directly in it.
        self.assertEqual(records["frontend/package.json"]["registered_types"], ["node", "fullstack"])
        self.assertEqual(records["package.json"]["registered_types"], ["root"])
        self.assertTrue(records["tools/frontend/package.json"]["needs_confirmation"])

    def test_setup_scan_rejects_bad_config_instead_of_claiming_no_stacks(self):
        self.write(".claude/config.json", '{"projectTypes":[]}')
        result = self.cli("gx-setup-scan.py", "--cwd", self.project, "--config-source", "existing")
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stdout, result.stderr)
        self.assertIn("error", json.loads(result.stdout))

    def test_inspect_without_config_reports_projects_without_creating_setup_artifacts(self):
        self.write("web/package.json", '{"scripts":{"test":"vitest run"}}')
        self.write("backend/pom.xml", "<project/>")
        before = self.snapshot()
        report = self.invoke("gx-setup-scan.py", "--cwd", self.project)
        self.assertEqual(report["config_source"], "missing")
        self.assertEqual([item["root"] for item in report["markers"]], ["backend", "web"])
        self.assertTrue(all(item["needs_confirmation"] for item in report["markers"]))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / ".dev").exists())
        self.assertFalse((self.project / ".gitignore").exists())

    def test_inspect_shows_registered_type_even_when_its_marker_is_missing(self):
        self.write(".claude/config.json", json.dumps({"projectTypes": {
            "web": {"detect": ["package.json"], "roots": ["web"], "build": "pnpm build"}}}))
        before = self.snapshot()
        report = self.invoke("gx-setup-scan.py", "--cwd", self.project)
        self.assertIn("registrations", report)
        self.assertEqual(report["registrations"], [{"name": "web", "detect": ["package.json"],
                                                  "roots": ["web"], "has_build": True, "has_test": False}])
        self.assertEqual(report["markers"], [])
        self.assertEqual(self.snapshot(), before)

    def classify(self, tool, value, code=0, *extra):
        stdout = value if isinstance(value, str) else json.dumps(value)
        return self.invoke("gx-dependency-result.py", "classify", "--tool", tool,
                           "--exit-code", code, *extra, stdin=stdout)

    def test_normal_empty_results_are_complete_without_findings(self):
        samples = (
            ("npm-outdated", {}),
            ("npm-audit", {"auditReportVersion": 2, "vulnerabilities": {},
                           "metadata": {"vulnerabilities": {"total": 0}}}),
            ("pip-outdated", []),
            ("pip-audit", {"dependencies": [], "fixes": []}),
            ("cargo-audit", {"vulnerabilities": {"found": False, "count": 0, "list": []}}),
        )
        for tool, payload in samples:
            with self.subTest(tool=tool):
                result = self.classify(tool, payload)
                self.assertEqual(result["status"], "complete")
                self.assertEqual(result["findings"], 0)

    def test_nonzero_with_a_valid_finding_is_distinct_from_a_json_error(self):
        result = self.classify("npm-outdated", {"example": {
            "current": "1.0.0", "wanted": "1.1.0", "latest": "2.0.0"}}, 1)
        self.assertEqual((result["status"], result["findings"]), ("complete", 1))
        result = self.classify("npm-audit", {"error": {"code": "ENOLOCK", "summary": "No lockfile"}}, 1)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["findings"])
        self.assertIn("ENOLOCK", result["reason"])

    def test_outdated_package_names_do_not_become_status_envelope_keys(self):
        for name in ("partial", "error", "errors"):
            with self.subTest(package=name):
                record = self.classify("npm-outdated", {name: {
                    "current": "1.0.0", "wanted": "1.1.0", "latest": "2.0.0"}}, 1)
                self.assertEqual((record["status"], record["findings"]), ("complete", 1))

    def test_outdated_real_status_envelopes_and_unknown_shapes_remain_unassessed(self):
        samples = (
            ({"error": {"code": "ENOLOCK", "summary": "No lockfile"}}, "error"),
            ({"partial": True, "errors": ["registry request failed"]}, "partial"),
            ({"partial": {"unexpected": "object"}}, "error"),
            ({"errors": {"unexpected": "object"}}, "error"),
        )
        for payload, expected in samples:
            with self.subTest(payload=payload):
                record = self.classify("npm-outdated", payload, 1)
                self.assertEqual(record["status"], expected)
                self.assertIsNone(record["findings"])

    def test_unknown_status_object_cannot_hide_behind_a_valid_audit_body(self):
        payload = {"auditReportVersion": 2, "vulnerabilities": {},
                   "metadata": {"vulnerabilities": {"total": 0}},
                   "errors": {"unexpected": "object"}}
        self.assertEqual(self.classify("npm-audit", payload)["status"], "error")

    def test_invalid_partial_empty_and_timed_out_results_are_not_zero_findings(self):
        cases = (
            ("npm-audit", "", 1, (), "error"),
            ("npm-audit", '{"vulnerabilities":', 1, (), "error"),
            ("npm-audit", {"auditReportVersion": 2}, 0, (), "error"),
            ("pip-audit", {"dependencies": [{"name": "native", "skip_reason": "unsupported"}],
                           "fixes": []}, 0, (), "partial"),
            ("npm-outdated", {}, 0, ("--timed-out",), "timeout"),
            ("npm-audit", {"auditReportVersion": 1, "advisories": {}}, 0, (), "unsupported"),
        )
        for tool, payload, code, extra, expected in cases:
            with self.subTest(expected=expected, payload=payload):
                result = self.classify(tool, payload, code, *extra)
                self.assertEqual(result["status"], expected)
                self.assertIsNone(result["findings"])

    def test_inconsistent_counts_and_unexpected_exit_do_not_validate_audit(self):
        payload = {"vulnerabilities": {"found": True, "count": 1, "list": []}}
        self.assertEqual(self.classify("cargo-audit", payload, 1)["status"], "error")
        self.assertEqual(self.classify("pip-outdated", [], 2)["status"], "error")

    def test_placeholder_cargo_advisory_is_not_a_complete_vulnerability(self):
        payload = {"vulnerabilities": {"found": True, "count": 1, "list": [{}]}}
        self.assertEqual(self.classify("cargo-audit", payload, 1)["status"], "error")

    def test_supported_audit_findings_with_exit_one_are_retained(self):
        samples = (
            ("npm-audit", {"auditReportVersion": 2, "vulnerabilities": {
                "example": {"name": "example", "severity": "high", "via": ["other"], "nodes": []}},
                "metadata": {"vulnerabilities": {"total": 1}}}),
            ("pip-audit", {"dependencies": [{"name": "example", "version": "1.0",
                                             "vulns": [{"id": "PYSEC-example"}]}], "fixes": []}),
            ("cargo-audit", {"vulnerabilities": {"found": True, "count": 1, "list": [{
                "advisory": {"id": "RUSTSEC-example"}, "package": {"name": "example", "version": "1.0"}}]}}),
        )
        for tool, payload in samples:
            with self.subTest(tool=tool):
                record = self.classify(tool, payload, 1)
                self.assertEqual((record["status"], record["findings"]), ("complete", 1))

    def test_partial_analysis_has_no_health_grade_even_without_findings(self):
        report = self.invoke("gx-dependency-result.py", "health", stdin=json.dumps({
            "severities": [], "statuses": {"code": "complete", "deps": "error"}}))
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["score"])
        self.assertIsNone(report["grade"])
        self.assertEqual(report["unassessed"], ["deps"])

    def test_complete_scoped_analysis_retains_the_documented_heuristic(self):
        report = self.invoke("gx-dependency-result.py", "health", stdin=json.dumps({
            "severities": ["CRITICAL", "HIGH"], "statuses": {"code": "complete"}}))
        self.assertEqual((report["score"], report["grade"]), (80, "B"))

    def reserve(self, output=None):
        arguments = ["reserve", "--cwd", self.project, "--topic", "C# vs. Java", "--date", "20261110"]
        if output is not None:
            arguments += ["--output", str(output)]
        return self.invoke("gx-research-output.py", *arguments)

    def test_research_explicit_output_is_used_for_save_completion_and_context_command(self):
        report = self.reserve("docs/인증 비교.md")
        expected = (self.project / "docs/인증 비교.md").as_posix()
        self.assertEqual(report["output_path"], expected)
        saved = self.invoke("gx-research-output.py", "save", "--output", report["output_path"],
                            stdin="# 비교\n확인한 결과\n")
        self.assertEqual(saved["output_path"], expected)
        self.assertEqual(saved["context_command"], '/gx-context <도메인명> --from "' + expected + '"')
        self.assertEqual(Path(expected).read_text(encoding="utf-8"), "# 비교\n확인한 결과\n")
        self.assertFalse((self.project / ".research/인증 비교.md").exists())

    def test_research_explicit_output_leaves_research_dir_and_gitignore_untouched(self):
        # F37: 사용자가 정한 경로에 저장할 때는 .research/를 만들지 않고 .gitignore도 바꾸지 않는다.
        gitignore = self.write(".gitignore", "build/\n")
        report = self.reserve("docs/외부 보고서.md")
        self.assertIsNone(report["run_dir"])
        self.assertIsNone(report["findings_path"])
        self.assertFalse((self.project / ".research").exists())
        self.assertEqual(gitignore.read_text(encoding="utf-8"), "build/\n")

    def test_research_date_must_be_eight_digits(self):
        result = self.cli("gx-research-output.py", "reserve", "--cwd", self.project,
                          "--topic", "t", "--date", "2026111")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".research").exists())

    def test_parallel_same_day_research_reserves_different_outputs_and_preserves_findings(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            runs = list(pool.map(lambda _: self.reserve(), range(2)))
        self.assertNotEqual(runs[0]["run_dir"], runs[1]["run_dir"])
        self.assertNotEqual(runs[0]["findings_path"], runs[1]["findings_path"])
        self.assertNotEqual(runs[0]["output_path"], runs[1]["output_path"])
        old = Path(runs[0]["findings_path"])
        old.write_text("중단한 조사 결과", encoding="utf-8")
        self.reserve()
        self.assertEqual(old.read_text(encoding="utf-8"), "중단한 조사 결과")

    def test_explicit_existing_file_is_never_overwritten_even_after_reservation(self):
        existing = self.write("docs/existing.md", "기존 보고서")
        result = self.cli("gx-research-output.py", "reserve", "--cwd", self.project,
                          "--topic", "test", "--date", "20261110", "--output", existing)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(existing.read_text(encoding="utf-8"), "기존 보고서")
        reserved = self.reserve("docs/race.md")
        target = Path(reserved["output_path"])
        target.write_text("다른 실행의 보고서", encoding="utf-8")
        result = self.cli("gx-research-output.py", "save", "--output", target, stdin="새 보고서")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(target.read_text(encoding="utf-8"), "다른 실행의 보고서")

    def test_two_writers_cannot_replace_each_others_explicit_report(self):
        target = self.project / "docs/shared.md"
        def finish(text):
            return self.cli("gx-research-output.py", "save", "--output", target, stdin=text)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(finish, ("첫 보고서", "다른 보고서")))
        self.assertEqual(sorted(item.returncode for item in results), [0, 2])
        self.assertIn(target.read_text(encoding="utf-8"), ("첫 보고서", "다른 보고서"))


if __name__ == "__main__":
    unittest.main()
