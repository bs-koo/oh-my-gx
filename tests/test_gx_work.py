"""공통 진입의 읽기 전용 라우팅·계획 정규화 경계 검증."""

import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import load


work = load("gx_work", "scripts/gx-work.py")


def plan():
    return {
        "schema-version": 1,
        "goal": "임계값을 넘는 요청을 거부한다",
        "units": [{
            "id": "U1", "spec": "임계값 초과 요청은 거부한다",
            "constraints": ["기존 정상 요청 응답 유지"],
            "ac": [{"id": "AC-1", "given": "임계값 10", "when": "11 요청", "then": "거부"}],
            "files": ["src/limit.py"], "consumes": [], "produces": ["거부 응답"],
            "test": {"intent": "임계값 초과 거부", "boundary": "9,10,11", "command": "python -m unittest tests.test_limit"},
            "review-focus": ["정상 요청 호환성"],
        }],
        "decisions": [],
    }


class WorkEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-b", "feature/limit", str(self.root)], check=True, capture_output=True)
        (self.root / "source.txt").write_text("사용자 미커밋 변경\n", encoding="utf-8")
        self.state = self.root / ".dev" / "feature-limit" / "state.md"

    def active(self, extra=""):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text("pipeline: gx-tdd\nstatus: in_progress\nphase: implement\n"
                              "run-id: old-run\ngoal: 기존 목표\nstop-at: commit\n" + extra, encoding="utf-8")

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_new_implementation_uses_only_tdd_and_defaults_to_verified_changes(self):
        value = work.route(self.root, "implement", goal="새 기능")
        self.assertEqual((value["action"], value["skill"], value["stop-at"]),
                         ("implement", "oh-my-gx:gx-tdd", "verify"))

    def test_implementation_cannot_request_a_read_only_endpoint(self):
        before = self.snapshot()
        for endpoint in ("understand", "plan"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                work.route(self.root, "implement", stop_at=endpoint)
        self.assertEqual(self.snapshot(), before)

    def test_existing_pipeline_resumes_with_original_run_and_goal(self):
        self.active()
        value = work.route(self.root, "implement", goal="추가 설명")
        self.assertEqual(value["action"], "resume")
        self.assertEqual((value["run-id"], value["goal"], value["stop-at"]),
                         ("old-run", "기존 목표", "commit"))

    def test_explicit_readonly_goals_do_not_resume_or_change_even_dirty_git(self):
        self.active()
        before = self.snapshot()
        for intent in ("understand", "plan", "status"):
            value = work.route(self.root, intent, goal="분석만")
            self.assertEqual(value["action"], intent)
            self.assertTrue(value["read-only"])
            self.assertIsNone(value["skill"])
        self.assertEqual(self.snapshot(), before)

    def test_resume_does_not_silently_expand_authorized_endpoint(self):
        self.active()
        with self.assertRaisesRegex(ValueError, "stop-at"):
            work.route(self.root, "resume", stop_at="pr")

    def test_readonly_intent_cannot_be_combined_with_mutating_endpoint(self):
        for intent in ("understand", "plan"):
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                work.route(self.root, intent, stop_at="commit")

    def test_missing_resume_returns_status_without_creating_pipeline(self):
        before = self.snapshot()
        self.assertEqual(work.route(self.root, "resume")["action"], "no-active-run")
        self.assertEqual(self.snapshot(), before)

    def test_other_branch_pipeline_is_not_resumed(self):
        self.active()
        self.state.rename(self.state.with_name("saved-state.md"))
        self.assertEqual(work.route(self.root, "implement")["action"], "implement")

    def test_completed_state_does_not_resume(self):
        self.active()
        self.state.write_text(self.state.read_text(encoding="utf-8").replace("in_progress", "completed"), encoding="utf-8")
        self.assertEqual(work.route(self.root, "implement")["action"], "implement")

    def test_malformed_optional_config_keeps_git_resume_available(self):
        self.active()
        config = self.root / ".claude" / "config.json"
        config.parent.mkdir()
        for content in ("{", "[]"):
            config.write_text(content, encoding="utf-8")
            with self.subTest(content=content):
                self.assertEqual(work.route(self.root, "resume")["run-id"], "old-run")

    def test_legacy_dev_cannot_be_automatically_resumed_as_tdd(self):
        self.active()
        self.state.write_text(self.state.read_text(encoding="utf-8").replace("gx-tdd", "gx-dev"), encoding="utf-8")
        before = self.snapshot()
        result = work.route(self.root, "implement")
        self.assertEqual(result["action"], "migration-required")
        self.assertTrue(result["read-only"])
        self.assertIsNone(result["skill"])
        self.assertEqual(result["run-id"], "old-run")
        self.assertEqual(self.snapshot(), before)

    def test_ralph_lock_never_starts_a_second_executor(self):
        self.active()
        self.state.write_text(self.state.read_text(encoding="utf-8").replace("gx-tdd", "gx-ralph"), encoding="utf-8")
        lock = self.state.with_name("ralph.lock")
        for locked in (False, True):
            if locked:
                lock.write_text("runner pid", encoding="utf-8")
            with self.subTest(locked=locked):
                before = self.snapshot()
                result = work.route(self.root, "resume")
                self.assertEqual(result["action"], "loop-active" if locked else "loop-resume-required")
                self.assertTrue(result["read-only"])
                self.assertIsNone(result["skill"])
                self.assertEqual(self.snapshot(), before)


class SvnWorkEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        config = self.root / ".claude" / "config.json"
        config.parent.mkdir()
        config.write_text('{"vcs": "svn"}', encoding="utf-8")
        self.pointer = self.root / ".dev" / ".active"

    def active(self, slug, pipeline="gx-tdd"):
        state = self.root / ".dev" / slug / "state.md"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(f"pipeline: {pipeline}\nstatus: in_progress\nphase: implement\n"
                         f"run-id: {slug}-run\ngoal: {slug}\nstop-at: commit\n", encoding="utf-8")
        return state

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_missing_or_blank_pointer_requires_selection_before_resuming(self):
        first = self.active("alpha")
        second = self.active("beta")
        for pointer in (None, "", " \n"):
            if pointer is not None:
                self.pointer.write_text(pointer, encoding="utf-8")
            for intent in ("resume", "implement"):
                with self.subTest(pointer=pointer, intent=intent):
                    before = self.snapshot()
                    result = work.route(self.root, intent, stop_at="pr", goal="이번 요청")
                    self.assertEqual(result["action"], "resume-selection-required")
                    self.assertEqual((result["skill"], result["skill-args"]), ("oh-my-gx:gx-tdd", "--resume"))
                    self.assertTrue(result["read-only"])
                    self.assertEqual(result["candidate-state-files"], [str(first.resolve()), str(second.resolve())])
                    self.assertIsNone(result["run-id"])
                    self.assertIsNone(result["stop-at"])
                    self.assertEqual(result["requested-stop-at"], "pr")
                    self.assertEqual(self.snapshot(), before)

    def test_multiple_active_states_do_not_expand_readonly_requests(self):
        self.active("alpha")
        self.active("beta")
        before = self.snapshot()
        for intent in ("understand", "plan", "status"):
            with self.subTest(intent=intent):
                result = work.route(self.root, intent)
                self.assertEqual(result["action"], intent)
                self.assertTrue(result["read-only"])
                self.assertIsNone(result["skill"])
        self.assertEqual(self.snapshot(), before)

    def test_only_active_svn_state_restores_identity_without_a_pointer(self):
        for pipeline, locked, action in (("gx-tdd", False, "resume"), ("gx-dev", False, "migration-required"),
                                         ("unknown", False, "migration-required"), ("gx-ralph", False, "loop-resume-required"),
                                         ("gx-ralph", True, "loop-active")):
            state = self.active("beta", pipeline)
            if locked:
                state.with_name("ralph.lock").write_text("runner pid", encoding="utf-8")
            for intent in ("resume", "implement"):
                with self.subTest(pipeline=pipeline, locked=locked, intent=intent):
                    before = self.snapshot()
                    result = work.route(self.root, intent)
                    self.assertEqual(result["action"], action)
                    self.assertEqual((result["run-id"], result["stop-at"]), ("beta-run", "commit"))
                    self.assertEqual(result["read-only"], pipeline != "gx-tdd")
                    self.assertEqual(self.snapshot(), before)

    def test_mixed_pipeline_candidates_remain_readonly_until_selected(self):
        self.active("alpha")
        for pipeline in ("gx-dev", "unknown", "gx-ralph"):
            second = self.active("beta", pipeline)
            if pipeline == "gx-ralph":
                second.with_name("ralph.lock").write_text("runner pid", encoding="utf-8")
            with self.subTest(pipeline=pipeline):
                before = self.snapshot()
                result = work.route(self.root, "resume")
                self.assertEqual(result["action"], "resume-selection-required")
                self.assertTrue(result["read-only"])
                self.assertIsNone(result["run-id"])
                self.assertIsNone(result["stop-at"])
                self.assertEqual(self.snapshot(), before)

    def test_explicit_pointer_restores_existing_identity_and_pipeline_guards(self):
        self.active("alpha")
        self.pointer.write_text("beta", encoding="utf-8")
        for pipeline, locked, action in (("gx-tdd", False, "resume"), ("gx-dev", False, "migration-required"),
                                         ("unknown", False, "migration-required"), ("gx-ralph", False, "loop-resume-required"),
                                         ("gx-ralph", True, "loop-active")):
            second = self.active("beta", pipeline)
            if locked:
                second.with_name("ralph.lock").write_text("runner pid", encoding="utf-8")
            with self.subTest(pipeline=pipeline, locked=locked):
                result = work.route(self.root, "resume")
                self.assertEqual(result["action"], action)
                self.assertEqual((result["run-id"], result["stop-at"]), ("beta-run", "commit"))
                self.assertEqual(result["read-only"], pipeline != "gx-tdd")


class NormalizedPlanTests(unittest.TestCase):
    def test_complete_plan_is_valid_without_fabricated_approval(self):
        self.assertEqual(work.validate_plan(plan()), [])

    def test_missing_boundary_and_conflicting_decisions_are_reported_together(self):
        value = plan()
        del value["units"][0]["test"]["boundary"]
        value["decisions"] = [
            {"topic": "인증", "value": "세션", "status": "explicit", "source": "사용자 답변 1"},
            {"topic": "인증", "value": "JWT", "status": "explicit", "source": "외부 계획"},
        ]
        problems = work.validate_plan(value)
        self.assertTrue(any(p["path"] == "units[0].test.boundary" for p in problems))
        self.assertTrue(any(p["kind"] == "conflict" for p in problems))

    def test_ac_ids_and_unit_ids_cannot_collide(self):
        value = plan()
        value["units"].append(copy.deepcopy(value["units"][0]))
        self.assertGreaterEqual(len([p for p in work.validate_plan(value) if p["kind"] == "conflict"]), 2)

    def test_incomplete_external_plan_is_not_silently_rewritten(self):
        value = {"goal": "기능 추가", "units": [{"id": "U1"}]}
        original = copy.deepcopy(value)
        self.assertTrue(work.validate_plan(value))
        self.assertEqual(value, original)

    def test_missing_inputs_and_dependency_cycle_block_execution(self):
        value = plan()
        value["units"][0]["depends-on"] = ["missing"]
        self.assertTrue(any(p["kind"] == "conflict" for p in work.validate_plan(value)))
        value["units"][0]["depends-on"] = ["U1"]
        self.assertTrue(any(p["kind"] == "conflict" for p in work.validate_plan(value)))

    def test_large_external_dependency_chain_returns_json_and_detects_cycles(self):
        value = plan()
        template = value["units"].pop()
        for index in range(1100):
            unit = copy.deepcopy(template)
            unit["id"] = f"U{index}"
            unit["ac"][0]["id"] = f"AC-{index}"
            unit["depends-on"] = [f"U{index + 1}"] if index < 1099 else []
            value["units"].append(unit)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large-plan.json"
            script = Path(__file__).resolve().parents[1] / "scripts" / "gx-work.py"
            for cyclic, exit_code in ((False, 0), (True, 2)):
                if cyclic:
                    value["units"][-1]["depends-on"] = ["U0"]
                path.write_text(json.dumps(value), encoding="utf-8")
                process = subprocess.run([sys.executable, str(script), "validate-plan", "--plan", str(path)],
                                         capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(process.returncode, exit_code, process.stderr)
                self.assertEqual(process.stderr, "")
                result = json.loads(process.stdout)
                self.assertEqual(result["valid"], not cyclic)
                if cyclic:
                    self.assertTrue(any(issue["kind"] == "conflict" for issue in result["issues"]))

    def test_planned_file_paths_cannot_escape_project_scope_on_any_host(self):
        for path in ("../../outside.py", "C:/outside.py", "/outside.py", "C:outside.py", r"..\outside.py", r"\outside.py", r"\\host\share\outside.py", "src/../outside.py"):
            with self.subTest(path=path):
                value = plan()
                value["units"][0]["files"] = [path]
                self.assertTrue(any(p["path"] == "units[0].files[0]" and p["kind"] == "scope"
                                    for p in work.validate_plan(value)))

    def test_handoff_preserves_file_pointer_and_never_imports_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "외부 계획.json"
            value = plan()
            value["approval"] = {"status": "approved", "source": "문서의 자체 승인 표식"}
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            before = path.read_bytes()
            result = work.handoff(path, stop_at="verify", run_id="run-123")
            self.assertEqual(result["approval"]["status"], "unconfirmed")
            self.assertEqual(result["plan-file"], str(path.resolve()))
            self.assertEqual(result["run-id"], "run-123")
            self.assertNotIn("units", result)
            self.assertEqual(path.read_bytes(), before)

    def test_handoff_rejects_invalid_plan_and_keeps_explicit_authorization_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(plan()), encoding="utf-8")
            result = work.handoff(path, stop_at="pr", approval_source="사용자 메시지 42: 구현 후 PR")
            self.assertEqual(result["approval"], {"status": "approved", "source": "사용자 메시지 42: 구현 후 PR"})
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                work.handoff(path, stop_at="verify")

    def test_context_run_identity_and_observed_facts_survive_readonly_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            value = plan()
            value["run-id"] = "context-run"
            value["observed-facts"] = [{"path": "src/limit.py", "fact": "현재 상한 검사 없음"}]
            path.write_text(json.dumps(value), encoding="utf-8")
            result = work.handoff(path, stop_at="understand")
            self.assertEqual(result["intent"], "understand")
            self.assertEqual(result["run-id"], "context-run")
            self.assertEqual(result["observed-facts"], value["observed-facts"])

    def test_fresh_implementation_never_adopts_past_external_plan_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            value = plan()
            value["run-id"] = "completed-run-42"
            path.write_text(json.dumps(value), encoding="utf-8")
            first = work.handoff(path, stop_at="verify")
            second = work.handoff(path, stop_at="verify")
            self.assertNotEqual(first["run-id"], value["run-id"])
            self.assertNotEqual(first["run-id"], second["run-id"])
            self.assertEqual(work.handoff(path, run_id="current-run")["run-id"], "current-run")

    def test_cli_invalid_plan_reports_all_gaps_and_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text('{"units": []}', encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "scripts" / "gx-work.py"
            process = subprocess.run([sys.executable, str(script), "validate-plan", "--plan", str(path)],
                                     capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 2)
            self.assertGreaterEqual(len(json.loads(process.stdout)["issues"]), 2)


class InstalledSkillResourceTests(unittest.TestCase):
    def test_split_skills_resolve_read_pointers_after_install_relocation(self):
        source = Path(__file__).resolve().parents[1] / ".claude" / "skills"
        skills = ("gx-work", "gx-tdd", "gx-cross-review", "gx-setup", "gx-humanizer", "gx-visualize", "gx-verify")
        with tempfile.TemporaryDirectory(prefix="gx-installed-") as directory:
            installed = Path(directory) / "plugin" / ".claude" / "skills"
            for name in skills:
                shutil.copytree(source / name, installed / name)
            for name in skills:
                entry = installed / name / "SKILL.md"
                self.assertLess(len(entry.read_bytes()), 20000, name)
                candidates = [entry]
                candidates.extend((installed / name / "references").glob("*.md"))
                for path in candidates:
                    for relative in re.findall(r'Read\("([^"\n]+)"\)', path.read_text(encoding="utf-8")):
                        if relative == "..." or any(marker in relative for marker in ("$", "{", "<")):
                            continue
                        with self.subTest(skill=name, path=path.name, relative=relative):
                            self.assertTrue((path.parent / relative).is_file(), str(path.parent / relative))
                    for relative in re.findall(r'python(?:3)? (\.\./scripts/[a-z_]+\.py)', path.read_text(encoding="utf-8")):
                        with self.subTest(skill=name, command_source=path.name, relative=relative):
                            self.assertTrue((path.parent / relative).is_file(), str(path.parent / relative))


if __name__ == "__main__":
    unittest.main()
