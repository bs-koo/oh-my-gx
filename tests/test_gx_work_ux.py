"""gx-work helper 사용자 여정 개선 회귀: 모드 기록(A1)·계획 인계 답(A2)·다른 위치 재개(H4)·설정 누락(M5)·
새 판 안내(F9)·Codex 분할 진입 질문(A5)·설정 기본값(F5)·작업 취소(M9)."""

import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from codex_test_support import load
from test_gx_work import configure, plan
from test_gx_work_audit import SCRIPT, Project, digest, followup, followup_questions


work = load("gx_work_ux", "scripts/gx-work.py")
gate = load("gx_work_ux_question", "scripts/codex-question.py")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]


class A1ModeRecordTests(Project):
    def test_request_mode_is_validated_bound_and_carried_into_the_handoff(self):
        path = self.request({"goal": "결제 한도", "mode": "core"})
        result = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: gx-tdd로 진행")
        self.assertEqual(result["mode"], "core")
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])
        changed = copy.deepcopy(result)
        changed["mode"] = "all"
        self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])
        # 요청 파일의 모드가 바뀌면 입력 지문이 달라져 재검증이 실패한다.
        saved = self.save(result)
        self.request({"goal": "결제 한도", "mode": "all"})
        self.assertFalse(work.validate_handoff(saved, self.root)["ready-for-tdd"])

    def test_invalid_mode_is_reported_like_other_optional_fields(self):
        path = self.request({"goal": "결제 한도", "mode": "light"})
        with self.assertRaises(ValueError) as caught:
            work.handoff(request_path=path, project_root=self.root, run_id="run-1")
        self.assertEqual([issue["path"] for issue in caught.exception.issues], ["mode"])

    def test_request_without_mode_keeps_the_previous_fingerprint(self):
        path = self.request({"goal": "결제 한도"})
        result = work.handoff(request_path=path, project_root=self.root, run_id="run-1", stop_at="pr")
        expected = digest({"schema-version": 2, "input": {"goal": "결제 한도"}, "file": ".dev/run-1/intake.json",
                           "kind": "request", "run-id": "run-1", "stop-at": "pr"})
        self.assertEqual(result["input-sha256"], expected)
        self.assertIsNone(result["mode"])


class A2PlanChoiceTests(Project):
    def setUp(self):
        super().setUp()
        self.plan = self.root / ".dev/run-1/plan.json"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text(json.dumps(plan(), ensure_ascii=False), encoding="utf-8")

    def make(self, **extra):
        return work.handoff(self.plan, project_root=self.root, run_id="run-1",
                            entry_approval_source="u3: gx-tdd로 진행", **extra)

    def test_cli_choices_are_recorded_without_touching_the_external_plan(self):
        before = self.plan.read_bytes()
        result = self.make(mode="core", model_profile="eco")
        self.assertEqual((result["mode"], result["model-profile"]), ("core", "eco"))
        self.assertEqual(self.plan.read_bytes(), before)
        self.assertNotEqual(result["input-sha256"], self.make()["input-sha256"])
        saved = self.save(result)
        self.assertTrue(work.validate_handoff(saved, self.root)["ready-for-tdd"])
        for key, value in (("mode", "all"), ("model-profile", "standard"), ("mode", None), ("model-profile", None)):
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(result)
                changed[key] = value
                self.assertFalse(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])

    def test_choice_conflicting_with_the_source_file_is_rejected(self):
        value = plan()
        value["model-profile"] = "standard"
        self.plan.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "model-profile"):
            self.make(model_profile="eco")
        self.assertEqual(self.make(model_profile="standard")["model-profile"], "standard")
        with self.assertRaisesRegex(ValueError, "mode"):
            self.make(mode="fast")

    def test_reissue_keeps_the_recorded_choices(self):
        handoff = self.save(self.make(mode="core", model_profile="eco"))
        result = work.reissue(handoff, self.root, stop_at="pr", change_source="u9: PR까지")
        self.assertEqual((result["mode"], result["model-profile"], result["stop-at"]), ("core", "eco", "pr"))
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_cli_accepts_mode_and_model_profile(self):
        code, out, err = self.cli(SCRIPT, "handoff", "--plan", self.plan, "--project-root", self.root, "--run-id",
                                  "run-1", "--entry-approval-source", "u3: 진행", "--mode", "core",
                                  "--model-profile", "eco")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual((json.loads(out)["mode"], json.loads(out)["model-profile"]), ("core", "eco"))
        code, out, _ = self.cli(SCRIPT, "handoff", "--plan", self.plan, "--mode", "lite")
        self.assertEqual(code, 2)
        self.assertIn("--mode", json.loads(out)["error"])


class H4ResumeElsewhereTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gx-work-h4-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "main"
        subprocess.run(["git", "init", "-b", "main", str(self.root)], check=True, capture_output=True)
        subprocess.run(GIT + ["commit", "--allow-empty", "-m", "init"], cwd=self.root, check=True, capture_output=True)
        configure(self.root)
        self.worktree = self.base / "wt-login"
        subprocess.run(["git", "worktree", "add", "-b", "feat/login", str(self.worktree)], cwd=self.root,
                       check=True, capture_output=True)

    def state(self, place, slug, **fields):
        values = {"pipeline": "gx-tdd", "status": "in_progress", "phase": "implement", "run-id": f"{slug}-run",
                  "goal": "로그인 잠금", "stop-at": "pr", "work-id": "W118", "current-step": "RGR T2: RED"}
        values.update(fields)
        path = place / ".dev" / slug / "state.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"{key}: {value}\n" for key, value in values.items() if value is not None),
                        encoding="utf-8")
        return path

    def test_resume_finds_an_in_progress_run_in_another_worktree(self):
        path = self.state(self.worktree, "feat-login")
        result = work.route(self.root, "resume", goal="이어서 해줘")
        self.assertEqual(result["action"], "resume-elsewhere")
        self.assertTrue(result["read-only"])
        self.assertTrue(result["requires-user-decision"])
        self.assertIsNone(result["skill"])
        self.assertIsNone(result["setup-reason"])
        [candidate] = result["elsewhere-candidates"]
        self.assertEqual((candidate["branch"], candidate["slug"], candidate["work-id"], candidate["current-step"]),
                         ("feat/login", "feat-login", "W118", "RGR T2: RED"))
        self.assertTrue(work.same_path(candidate["worktree"], self.worktree))
        self.assertTrue(work.same_path(candidate["state-file"], path))

    def test_new_implementation_only_stops_for_the_same_goal_or_work_id(self):
        self.state(self.worktree, "feat-login")
        self.assertEqual(work.route(self.root, "implement", goal="W118 시작해줘")["action"], "resume-elsewhere")
        self.assertEqual(work.route(self.root, "implement", goal="로그인 잠금")["action"], "resume-elsewhere")
        self.assertEqual(work.route(self.root, "implement", goal="W11 정산 보고서")["action"], "implement")

    def test_current_checkout_states_and_finished_runs(self):
        # 이 체크아웃의 다른 slug 기록(브랜치가 어디에도 체크아웃되지 않음)도 후보다.
        subprocess.run(["git", "branch", "feat/pay"], cwd=self.root, check=True, capture_output=True)
        self.state(self.root, "feat-pay", branch="feat/pay", **{"work-id": "W120"})
        self.state(self.worktree, "feat-login", status="completed")
        self.state(self.worktree, "feat-old", status="cancelled")
        self.state(self.root, "feat-legacy", pipeline="gx-dev")
        [candidate] = work.route(self.root, "resume")["elsewhere-candidates"]
        self.assertEqual((candidate["branch"], candidate["worktree"], candidate["work-id"]), ("feat/pay", None, "W120"))

    def test_no_candidates_keeps_the_previous_results(self):
        self.assertEqual(work.route(self.root, "resume")["action"], "no-active-run")
        self.assertEqual(work.route(self.root, "implement", goal="새 기능")["action"], "implement")

    def test_same_run_in_two_places_prefers_the_checked_out_branch(self):
        self.state(self.root, "feat-login", branch="feat/login", **{"current-step": "오래된 사본"})
        self.state(self.worktree, "feat-login")
        [candidate] = work.route(self.root, "resume")["elsewhere-candidates"]
        self.assertEqual(candidate["current-step"], "RGR T2: RED")

    def test_states_of_deleted_branches_are_not_candidates(self):
        # M7: 머지 뒤 지워진 브랜치의 기록은 내지 않는다. 원격 추적 ref만 남은 브랜치는 낸다.
        self.state(self.root, "feat-merged", branch="feat/merged", **{"work-id": "W121"})
        self.state(self.root, "feat-nameless", **{"work-id": "W122"})
        self.assertEqual(work.route(self.root, "resume")["action"], "no-active-run")
        subprocess.run(["git", "update-ref", "refs/remotes/origin/feat/merged", "HEAD"], cwd=self.root,
                       check=True, capture_output=True)
        [candidate] = work.route(self.root, "resume")["elsewhere-candidates"]
        self.assertEqual((candidate["branch"], candidate["work-id"]), ("feat/merged", "W121"))
        self.assertEqual(work.route(self.root, "implement", goal="W121 시작해줘")["action"], "resume-elsewhere")


class M5SetupRequiredTests(Project):
    def test_missing_or_broken_config_stops_before_the_entry_question(self):
        self.git()
        config = self.root / ".claude/config.json"
        for content, reason in ((None, "config-missing"), ("{", "config-invalid"), ("[]", "config-invalid"),
                                ('{"projectTypes": {"node": {"detect": ["package.json"]}}}',
                                 "project-type-unregistered"), ('{"vcs": "git"}', "project-type-unregistered")):
            with self.subTest(content=content):
                if content is None:
                    config.unlink()
                else:
                    config.write_text(content, encoding="utf-8")
                before = self.snapshot()
                result = work.route(self.root, "implement", goal="새 기능")
                self.assertEqual((result["action"], result["setup-reason"]), ("setup-required", reason))
                self.assertTrue(result["read-only"])
                self.assertFalse(result["requires-user-decision"])
                self.assertIn("/oh-my-gx:gx-setup", result["reason"])
                self.assertEqual(self.snapshot(), before)
                for intent in ("understand", "plan", "status"):
                    self.assertEqual(work.route(self.root, intent)["action"], intent)
                self.assertEqual(work.route(self.root, "resume")["action"], "no-active-run")

    def test_registered_type_is_detected_like_the_test_planner(self):
        self.git()
        (self.root / "pyproject.toml").unlink()
        (self.root / "backend").mkdir()
        (self.root / "backend/build.gradle.kts").write_text("", encoding="utf-8")
        types = {"projectTypes": {"java-spring": {"detect": ["build.gradle", "build.gradle.kts"]}}}
        (self.root / ".claude/config.json").write_text(json.dumps(types), encoding="utf-8")
        self.assertEqual(work.route(self.root, "implement", goal="새 기능")["action"], "implement")
        types["projectTypes"]["java-spring"]["roots"] = ["api"]
        (self.root / ".claude/config.json").write_text(json.dumps(types), encoding="utf-8")
        self.assertEqual(work.route(self.root, "implement", goal="새 기능")["setup-reason"], "project-type-unregistered")
        types["projectTypes"]["java-spring"]["roots"] = ["backend"]
        (self.root / ".claude/config.json").write_text(json.dumps(types), encoding="utf-8")
        self.assertEqual(work.route(self.root, "implement", goal="새 기능")["action"], "implement")

    def test_path_detect_markers_match_repository_relative_paths(self):
        # kreb처럼 경로형 detect만 쓰는 두 타입: 루트에 감지 파일이 없어도 등록된 것으로 본다.
        self.git()
        (self.root / "pyproject.toml").unlink()
        for marker in ("backend/build.gradle.kts", "frontend/package.json"):
            (self.root / marker).parent.mkdir()
            (self.root / marker).write_text("", encoding="utf-8")
        types = {"projectTypes": {"java-spring": {"detect": ["backend/build.gradle.kts"]},
                                  "node": {"detect": ["frontend/package.json"]}}}
        (self.root / ".claude/config.json").write_text(json.dumps(types), encoding="utf-8")
        self.assertEqual(work.route(self.root, "implement", goal="새 기능")["action"], "implement")
        # 경로형 패턴은 이름만 같은 다른 위치의 파일로 감지하지 않는다.
        types = {"projectTypes": {"java-spring": {"detect": ["api/build.gradle.kts"]}}}
        (self.root / ".claude/config.json").write_text(json.dumps(types), encoding="utf-8")
        result = work.route(self.root, "implement", goal="새 기능")
        self.assertEqual((result["action"], result["setup-reason"]), ("setup-required", "project-type-unregistered"))

    def test_active_run_is_not_blocked_by_setup(self):
        self.git()
        self.state()
        (self.root / ".claude/config.json").unlink()
        self.assertEqual(work.route(self.root, "resume")["action"], "resume")


class F9UpdateNoticeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gx-work-cache-")
        self.addCleanup(temporary.cleanup)
        self.cache = Path(temporary.name)

    def install(self, name, version):
        path = self.cache / name / ".claude-plugin/plugin.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"name": "oh-my-gx", "version": version}), encoding="utf-8")
        return path.parents[1]

    def test_newer_sibling_version_is_announced(self):
        loaded = self.install("3.1.0", "3.1.0")
        self.install("3.0.0", "3.0.0")
        self.install("3.10.0", "3.10.0")
        self.install("9.9.9", "not-a-version")
        (self.cache / "4.0.0").mkdir()
        [notice] = work.update_notices(loaded)
        self.assertIn("새 판 3.10.0가 설치되어 있습니다. Claude Code는 /reload-plugins, Codex는 새 세션", notice)
        self.assertIn("3.1.0", notice)

    def test_latest_or_non_cache_layout_is_silent(self):
        self.assertEqual(work.update_notices(self.install("3.1.0", "3.1.0")), [])
        self.install("3.0.9", "3.0.9")
        self.assertEqual(work.update_notices(self.cache / "3.1.0"), [])
        checkout = self.install("oh-my-gx", "3.1.0")
        self.install("3.2.0", "3.2.0")
        self.assertEqual(work.update_notices(checkout), [])
        self.assertEqual(work.update_notices(self.cache / "missing"), [])


class A5SplitEntryQuestionTests(Project):
    def setUp(self):
        super().setUp()
        self.git()

    def register_followup(self, run_id="run-1"):
        return gate.run("register", self.root, ".dev/feature-limit", {"phase": "work-entry", "goal": "결제 한도 구현",
                        "run_id": run_id, "questions": followup_questions()})

    def test_second_set_is_only_registered_after_a_proceed_entry_answer(self):
        with self.assertRaisesRegex(ValueError, "진입 질문 답"):
            self.register_followup()
        self.answered("feature-limit", selection="여기서 종료", goal="결제 한도 구현", run_id="run-1")
        with self.assertRaisesRegex(ValueError, "진입 질문 답"):
            self.register_followup()
        self.answered("feature-limit", selection="gx-tdd로 진행 (Recommended)", goal="결제 한도 구현", run_id="run-2")
        with self.assertRaisesRegex(ValueError, "진입 질문 답"):
            self.register_followup("run-1")
        self.assertEqual(self.register_followup("run-2")[0]["status"], "pending")

    def test_receipt_keeps_the_entry_answer_after_the_second_set(self):
        first = self.answered("feature-limit", goal="결제 한도 구현", run_id="run-1")
        second = followup(self, "feature-limit", "run-1", "결제 한도 구현", mode="전체 (Recommended)", profile="에코")
        receipt = json.loads((self.root / ".dev/feature-limit/answered-question.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["question"]["question_set_id"], second)
        self.assertEqual(receipt["earlier_question_set_ids"], [first])
        self.assertEqual(set(receipt["run_answers"]), {"gx_work_tdd_entry", "gx_work_mode", "gx_work_model_profile"})
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertTrue(result["entry-answer-recorded"])
        self.assertFalse(result["requires-user-decision"])
        self.assertEqual(result["answered-choices"], {"mode": "all", "model-profile": "eco"})
        # 진입 답의 질문세트 id로 인계해도 응답이 이 run에 결박돼 있음을 찾는다.
        path = self.request({"goal": "결제 한도 구현", "mode": "all", "model-profile": "eco"})
        handoff = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                               entry_approval_source="u3: gx-tdd로 진행", question_set_id=first)
        self.assertTrue(work.validate_handoff(self.save(handoff), self.root)["ready-for-tdd"])

    def test_interrupted_split_reasks_only_the_second_set(self):
        first = self.answered("feature-limit", goal="결제 한도 구현", run_id="run-1")
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertEqual(result["entry-followup-missing"], ["gx_work_mode", "gx_work_model_profile"])
        self.assertTrue(result["requires-user-decision"])
        configure(self.root, workflowDefaults={"mode": "core"})
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertEqual(result["entry-followup-missing"], ["gx_work_model_profile"])
        configure(self.root)
        self.register_followup()
        path = self.request({"goal": "결제 한도 구현"})
        with self.assertRaisesRegex(ValueError, "둘째 세트"):
            work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                         entry_approval_source="u3: gx-tdd로 진행", question_set_id=first)
        self.assertEqual(work.route(self.root, "implement", goal="결제 한도 구현")["action"], "awaiting-decision")

    def test_other_run_answers_are_not_merged(self):
        self.answered("feature-limit", goal="결제 한도 구현", run_id="run-1")
        self.answered("feature-limit", goal="결제 한도 구현", run_id="run-2")
        receipt = json.loads((self.root / ".dev/feature-limit/answered-question.json").read_text(encoding="utf-8"))
        self.assertEqual(set(receipt["run_answers"]), {"gx_work_tdd_entry"})
        self.assertNotIn("earlier_question_set_ids", receipt)


class F5DefaultsTests(Project):
    def test_valid_defaults_are_reported_and_invalid_ones_become_notices(self):
        configure(self.root, workflowDefaults={"stopAt": "pr", "mode": "core", "executionMethod": "session",
                                               "modelProfile": "eco"}, modelProfile="standard")
        result = work.route(self.root, "understand")
        self.assertEqual(result["defaults"], {"stop-at": "pr", "mode": "core", "execution-method": "session",
                                              "model-profile": "eco"})
        self.assertEqual(result["configured-model-profile"], "standard")
        self.assertEqual(result["notices"], [])
        configure(self.root, workflowDefaults={"stopAt": "plan", "mode": "", "executionMethod": "team",
                                               "modelProfile": "fast"}, modelProfile="cheap")
        result = work.route(self.root, "implement", goal="새 기능")
        self.assertEqual(result["defaults"], {})
        self.assertIsNone(result["configured-model-profile"])
        self.assertEqual(len(result["notices"]), 4)
        self.assertTrue(all("무시합니다" in notice for notice in result["notices"]))
        configure(self.root, workflowDefaults="pr")
        self.assertIn("workflowDefaults", work.route(self.root, "status")["notices"][0])

    def test_top_level_model_profile_is_a_recommendation_not_an_answer(self):
        # 템플릿 기본값 "standard"가 든 최상위 modelProfile은 프로파일 질문을 생략하는 근거가 아니다.
        self.git()
        configure(self.root, modelProfile="standard")
        self.answered("feature-limit", goal="결제 한도 구현", run_id="run-1")
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertEqual((result["defaults"], result["configured-model-profile"]), ({}, "standard"))
        self.assertEqual(result["entry-followup-missing"], ["gx_work_mode", "gx_work_model_profile"])
        configure(self.root, modelProfile="standard", workflowDefaults={"modelProfile": "eco"})
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertEqual(result["entry-followup-missing"], ["gx_work_mode"])


class M9CancelTests(Project):
    def setUp(self):
        super().setUp()
        self.git()

    def test_cancel_marks_only_the_status_and_releases_the_run(self):
        path = self.state()
        path.write_bytes("# 실행 상태\r\n\r\npipeline: gx-tdd\r\nstatus: in_progress\r\nrun-id: old-run\r\n"
                         "goal: 기존 목표\r\nstop-at: commit\r\nsteps:\r\n  implement:\r\n    - T1\r\n".encode("utf-8"))
        (path.parent / "pending-question.json").write_text("{}", encoding="utf-8")
        result = work.cancel(self.root, "u7: 작업 취소", run_id="old-run")
        self.assertEqual((result["status"], result["previous-status"], result["run-id"]),
                         ("cancelled", "in_progress", "old-run"))
        content = path.read_bytes().decode("utf-8")
        self.assertIn("status: cancelled\r\ncancelled-at: ", content)
        self.assertIn('cancel-source: "u7: 작업 취소"\r\nrun-id: old-run\r\n', content)
        self.assertIn("steps:\r\n  implement:\r\n    - T1\r\n", content)
        self.assertTrue((path.parent / "pending-question.json").exists())
        # L5: 취소 근거를 같은 디렉터리 decisions.md에 남긴다(없으면 질문 helper와 같은 헤더로 만든다).
        decisions = (path.parent / "decisions.md").read_text(encoding="utf-8")
        self.assertTrue(decisions.startswith("# 의사결정 기록\n"))
        self.assertIn("· 작업 취소\n\n**결정.** 작업 취소 (run-id old-run, phase 없음)\n\n**근거.** u7: 작업 취소\n",
                      decisions)
        self.assertTrue(work.same_path(result["decisions-file"], path.parent / "decisions.md"))
        self.assertEqual(work.state_fields(path)["status"], "cancelled")
        self.assertEqual(work.route(self.root, "resume")["action"], "no-active-run")
        with self.assertRaisesRegex(ValueError, "진행 중"):
            work.cancel(self.root, "u8: 다시 취소")

    def test_cancel_refuses_without_a_matching_active_run(self):
        with self.assertRaisesRegex(ValueError, "진행 중"):
            work.cancel(self.root, "u7: 취소")
        path = self.state()
        before = path.read_bytes()
        for kwargs, pattern in (({"reason": " "}, "reason"), ({"reason": "u7", "run_id": "other"}, "run-id")):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, pattern):
                work.cancel(self.root, **kwargs)
        (path.parent / "ralph.lock").write_text("runner", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ralph.lock"):
            work.cancel(self.root, "u7: 취소")
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((path.parent / "decisions.md").exists())

    def test_cancel_refuses_legacy_runs(self):
        # L4: gx-tdd가 아니거나 Ralph 흔적이 있는 기록은 고치지 않는다.
        decisions = self.root / ".dev" / "feature-limit" / "decisions.md"
        for fields in ({"pipeline": "gx-dev"}, {"pipeline": "gx-ralph"}, {"flags": "--core --ralph"},
                       {"flags": "RALPH"}):
            with self.subTest(fields=fields):
                path = self.state(**fields)
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "gx-tdd 실행만"):
                    work.cancel(self.root, "u7: 취소")
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(decisions.exists())
        self.state(flags="--core --ralphish")
        self.assertEqual(work.cancel(self.root, "u7: 취소")["status"], "cancelled")

    def test_cancel_appends_to_existing_decisions(self):
        path = self.state()
        decisions = path.parent / "decisions.md"
        decisions.write_text("# 의사결정 기록\n\n## 이전 결정\n", encoding="utf-8")
        work.cancel(self.root, "u9: 그만")
        text = decisions.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# 의사결정 기록\n\n## 이전 결정\n\n## "))
        self.assertEqual(text.count("# 의사결정 기록"), 1)
        self.assertIn("**근거.** u9: 그만\n", text)

    def test_cli_cancel(self):
        self.state()
        code, out, err = self.cli(SCRIPT, "cancel", "--project-root", self.root)
        self.assertEqual(code, 2)
        self.assertIn("--reason", json.loads(out)["error"])
        code, out, err = self.cli(SCRIPT, "cancel", "--project-root", self.root, "--reason", "u7: 그만할래")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["status"], "cancelled")
        code, out, _ = self.cli(SCRIPT, "cancel", "--project-root", self.root, "--reason", "u7: 그만할래")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
