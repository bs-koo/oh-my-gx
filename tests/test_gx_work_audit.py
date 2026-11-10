"""gx-work 전수조사(2026-11-09) helper 회귀: F01·F04·F06~F17·F25·F30·F36과 독립 리뷰 지적."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid

from codex_test_support import ROOT, load
from test_gx_work import plan


work = load("gx_work_audit", "scripts/gx-work.py")
gate = load("gx_work_audit_question", "scripts/codex-question.py")
SCRIPT = ROOT / "scripts" / "gx-work.py"
QUESTION = ROOT / "scripts" / "codex-question.py"
LISTS = ("sources", "decisions", "unresolved", "requirements", "context-paths", "observed-facts", "questions")
RELEASED = "6ef7517"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def legacy_v1(root, source, run_id, *, stop_at="verify", approval=None, entry=None,
              question_set_id=None, kind="request"):
    """3.0.0 helper(main 6ef7517)가 저장한 v1 인계를 같은 계산으로 재현한다."""
    path = Path(source).resolve()
    root = Path(root).resolve()
    value = json.loads(path.read_text(encoding="utf-8"))
    fingerprint = digest({"input": value, "file": str(path), "kind": kind, "project-root": str(root),
                          "run-id": run_id, "stop-at": stop_at})
    ready = bool(entry)
    readonly = stop_at in ("understand", "plan")
    entry_fingerprint = digest({"scope": fingerprint, "request-source": approval or entry,
                                "source": entry, "question-set-id": question_set_id})
    result = {
        "schema-version": 1, "origin": "gx-work", "handoff-kind": kind, "run-id": run_id,
        "project-root": str(root), "input-sha256": fingerprint, "goal": value["goal"],
        "intent": stop_at if readonly else "implement", "stop-at": stop_at,
        "plan-file": str(path) if kind == "plan" else None,
        "request-file": str(path) if kind == "request" else None, "work-id": value.get("work-id"),
        "approval": {"status": "approved" if approval or entry else "unconfirmed", "source": approval or entry},
        "entry-approval": {"status": "approved" if ready else "unconfirmed", "source": entry,
                           "question-set-id": question_set_id,
                           "scope-sha256": entry_fingerprint if ready else None},
        "ready-for-tdd": ready, "read-only": readonly, "execution-authorized": ready and not readonly,
    }
    for key in LISTS:
        result[key] = value.get(key, [])
    return result


def entry_question():
    return {"id": "gx_work_tdd_entry", "header": "TDD 진입", "question": "위 범위를 gx-tdd로 구체화·개발할까요?",
            "options": [{"label": "gx-tdd로 진행", "description": "제시한 범위로 진행합니다"},
                        {"label": "여기서 종료", "description": "개발로 넘어가지 않습니다"}]}


class Project(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gx-work-audit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def git(self, branch="feature/limit"):
        subprocess.run(["git", "init", "-b", branch, str(self.root)], check=True, capture_output=True)

    def state(self, slug="feature-limit", text=None, **fields):
        values = {"pipeline": "gx-tdd", "status": "in_progress", "phase": "implement",
                  "run-id": "old-run", "goal": "기존 목표", "stop-at": "commit"}
        values.update({key.replace("_", "-"): value for key, value in fields.items()})
        path = self.root / ".dev" / slug / "state.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = text if text is not None else "".join(f"{key}: {value}\n" for key, value in values.items())
        path.write_text(content, encoding="utf-8")
        return path

    def request(self, value=None, name=".dev/run-1/intake.json", raw=None):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            path.write_bytes(raw)
        else:
            path.write_text(json.dumps(value or {"goal": "결제 한도"}, ensure_ascii=False), encoding="utf-8")
        return path

    def save(self, value, name=".dev/run-1/handoff.json"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def register(self, slug, **context):
        registration = {"phase": "work-entry", "questions": [entry_question()], **context}
        return gate.run("register", self.root, ".dev/" + slug, registration)[0]["question_set_id"]

    def answered(self, slug, selection="gx-tdd로 진행", **context):
        identifier = self.register(slug, **context)
        gate.run("answer", self.root, ".dev/" + slug,
                 {"question_set_id": identifier, "answers": {"gx_work_tdd_entry": {"answers": [selection]}}})
        return identifier

    def marker_line(self, slug, identifier):
        text = (self.root / ".dev" / slug / "decisions.md").read_text(encoding="utf-8")
        return next(line for line in text.splitlines() if line.startswith(f"<!-- gx-question:{identifier}:"))

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and ".git" not in p.relative_to(self.root).parts}

    def cli(self, script, *args):
        process = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, timeout=60)
        return process.returncode, process.stdout.decode("utf-8"), process.stderr.decode("utf-8")


class F01WorkIdTests(Project):
    def test_work_ids_with_two_or_more_ascii_digits_are_accepted(self):
        for work_id in ("W01", "W99", "W100", "W118", "W1000"):
            with self.subTest(work_id=work_id):
                path = self.request({"goal": "기능", "work-id": work_id})
                self.assertEqual(work.handoff(request_path=path, project_root=self.root, run_id="run-1")["work-id"],
                                 work_id)

    def test_short_fullwidth_hyphen_and_other_digit_work_ids_are_rejected_with_expected_format(self):
        for work_id in ("W1", "W０１", "W-01", "w01", "W01a", "W 01", "W١٢"):
            with self.subTest(work_id=work_id):
                path = self.request({"goal": "기능", "work-id": work_id})
                with self.assertRaises(ValueError) as caught:
                    work.handoff(request_path=path, project_root=self.root, run_id="run-1")
                message = str(caught.exception)
                for needle in ("work-id", work_id, "두 자리 이상"):
                    self.assertIn(needle, message)

    def test_validate_plan_applies_the_same_work_id_rule(self):
        value = plan()
        value["work-id"] = "W118"
        self.assertEqual(work.validate_plan(value), [])
        value["work-id"] = "W1"
        self.assertTrue(any(issue["path"] == "work-id" for issue in work.validate_plan(value)))


class F04HandoffV2Tests(Project):
    def ready(self, **extra):
        path = self.request({"goal": "결제 한도"})
        return work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                            approval_source="u1: 구현해줘", entry_approval_source="u3: gx-tdd로 진행", **extra)

    def test_new_handoff_is_v2_with_project_relative_pointer(self):
        result = self.ready()
        self.assertEqual(result["schema-version"], 2)
        self.assertEqual(result["request-file"], ".dev/run-1/intake.json")
        self.assertIsNone(result["plan-file"])
        self.assertEqual(result["project-root"], str(self.root))
        self.assertTrue(result["ready-for-tdd"])

    def test_relative_pointer_is_resolved_from_project_root(self):
        self.request()
        result = work.handoff(request_path=".dev/run-1/intake.json", project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: 진행")
        self.assertEqual(result["request-file"], ".dev/run-1/intake.json")
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_moved_project_validates_without_reissue(self):
        self.save(self.ready())
        moved = Path(tempfile.mkdtemp(prefix="gx-work-moved-")).resolve()
        self.addCleanup(shutil.rmtree, moved, True)
        shutil.copytree(self.root, moved / "renamed project")
        checked = work.validate_handoff(moved / "renamed project/.dev/run-1/handoff.json", moved / "renamed project")
        self.assertTrue(checked["ready-for-tdd"], checked)
        self.assertEqual(checked["run-id"], "run-1")
        # 옮긴 v2를 재발급해도(종료점 변경과 함께여도) 위치 변경을 relocated로 남긴다.
        result = work.reissue(moved / "renamed project/.dev/run-1/handoff.json", moved / "renamed project",
                              stop_at="pr", change_source="u9: PR까지")
        self.assertTrue(result["relocated"])
        self.assertEqual(result["project-root"], str(moved / "renamed project"))

    def test_v2_project_root_is_display_only_but_v1_binds_it(self):
        changed = self.ready()
        changed["project-root"] = str(self.root.parent)
        self.assertTrue(work.validate_handoff(self.save(changed), self.root)["ready-for-tdd"])
        legacy = legacy_v1(self.root, self.root / ".dev/run-1/intake.json", "run-1", entry="u3: 진행")
        legacy["project-root"] = str(self.root.parent)
        self.assertFalse(work.validate_handoff(self.save(legacy), self.root)["ready-for-tdd"])

    def test_released_v1_handoffs_still_validate(self):
        request = self.request({"goal": "결제 한도", "work-id": "W01"})
        plan_file = self.root / ".dev/run-2/plan.json"
        plan_file.parent.mkdir(parents=True)
        plan_file.write_text(json.dumps(plan()), encoding="utf-8")
        cases = (
            (request, "request", "verify", "gx_work_tdd_entry"),
            (request, "request", "pr", None),
            (plan_file, "plan", "commit", "q-entry"),
            (request, "request", "plan", None),
        )
        for source, kind, stop_at, question in cases:
            with self.subTest(kind=kind, stop_at=stop_at):
                value = legacy_v1(self.root, source, "legacy-run", stop_at=stop_at, approval="u1: 요청",
                                  entry="u3: 진행", question_set_id=question, kind=kind)
                checked = work.validate_handoff(self.save(value, ".dev/legacy/handoff.json"), self.root)
                self.assertTrue(checked["ready-for-tdd"], checked)
                self.assertEqual((checked["run-id"], checked["stop-at"]), ("legacy-run", stop_at))

    def test_v1_replica_matches_the_released_helper(self):
        source = subprocess.run(["git", "-C", str(ROOT), "show", f"{RELEASED}:scripts/gx-work.py"],
                                capture_output=True)
        if source.returncode != 0:
            self.skipTest("기준 커밋을 읽을 수 없는 체크아웃")
        released_path = self.root / "released_gx_work.py"
        released_path.write_bytes(source.stdout)
        spec = importlib.util.spec_from_file_location("released_gx_work", released_path)
        released = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(released)
        request = self.request({"goal": "결제 한도", "work-id": "W01", "sources": [{"path": "a.md"}]})
        expected = released.handoff(request_path=request, project_root=self.root, run_id="run-1", stop_at="pr",
                                    approval_source="u1", entry_approval_source="u3", question_set_id="q-entry")
        self.assertEqual(legacy_v1(self.root, request, "run-1", stop_at="pr", approval="u1", entry="u3",
                                   question_set_id="q-entry"), expected)

    def test_run_id_format_is_checked(self):
        self.request()
        for bad in ("ab", "-run", ".run", "run 1", "실행-1", "a" * 81, "run/1"):
            with self.subTest(run_id=bad), self.assertRaises(ValueError) as caught:
                work.handoff(request_path=".dev/run-1/intake.json", project_root=self.root, run_id=bad)
            self.assertIn("run-id", str(caught.exception))
        for good in ("run-1", "20261109-153000-pay-limit", str(uuid.uuid4()), "a.b_c-d"):
            with self.subTest(run_id=good):
                self.assertEqual(work.handoff(request_path=".dev/run-1/intake.json", project_root=self.root,
                                              run_id=good)["run-id"], good)


class F04ReissueTests(Project):
    def prepared(self, stop_at="verify", entry="u3: gx-tdd로 진행"):
        path = self.request({"goal": "결제 한도"})
        return self.save(work.handoff(request_path=path, project_root=self.root, run_id="run-1", stop_at=stop_at,
                                      approval_source="u1: 구현해줘", entry_approval_source=entry))

    def test_endpoint_change_requires_actual_decision_and_keeps_run(self):
        handoff = self.prepared()
        before = handoff.read_bytes()
        snapshot = self.snapshot()
        with self.assertRaisesRegex(ValueError, "change-source"):
            work.reissue(handoff, self.root, stop_at="pr")
        result = work.reissue(handoff, self.root, stop_at="pr", change_source="u9: 이어서 PR까지")
        self.assertEqual(self.snapshot(), snapshot)
        self.assertEqual((result["run-id"], result["stop-at"], result["schema-version"]), ("run-1", "pr", 2))
        self.assertEqual(result["entry-approval"]["source"], "u9: 이어서 PR까지")
        self.assertEqual(result["approval"]["source"], "u1: 구현해줘")
        self.assertEqual(result["reissued-from-sha256"], hashlib.sha256(before).hexdigest())
        self.assertFalse(result["relocated"])
        self.save(result)
        checked = work.validate_handoff(handoff, self.root)
        self.assertTrue(checked["ready-for-tdd"], checked)
        self.assertEqual(checked["stop-at"], "pr")

    def test_relocated_v1_is_reissued_as_v2_keeping_entry_approval(self):
        request = self.request({"goal": "결제 한도"})
        self.save(legacy_v1(self.root, request, "run-1", approval="u1: 요청", entry="u3: 진행",
                            question_set_id="gx_work_tdd_entry"))
        moved = Path(tempfile.mkdtemp(prefix="gx-work-moved-")).resolve() / "other worktree"
        self.addCleanup(shutil.rmtree, moved.parent, True)
        shutil.copytree(self.root, moved)
        handoff = moved / ".dev/run-1/handoff.json"
        self.assertFalse(work.validate_handoff(handoff, moved)["ready-for-tdd"])
        result = work.reissue(handoff, moved)
        self.assertEqual((result["schema-version"], result["run-id"], result["stop-at"]), (2, "run-1", "verify"))
        self.assertTrue(result["relocated"])
        self.assertEqual(result["entry-approval"]["source"], "u3: 진행")
        self.assertEqual(result["request-file"], ".dev/run-1/intake.json")
        handoff.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(work.validate_handoff(handoff, moved)["ready-for-tdd"])

    def test_changed_request_is_a_new_entry_not_a_reissue(self):
        handoff = self.prepared()
        self.request({"goal": "다른 기능"})
        with self.assertRaisesRegex(ValueError, "새 진입"):
            work.reissue(handoff, self.root)
        with self.assertRaisesRegex(ValueError, "새 진입"):
            work.reissue(handoff, self.root, stop_at="pr", change_source="u9: PR까지")

    def test_readonly_or_unapproved_handoff_is_not_widened(self):
        with self.assertRaises(ValueError):
            work.reissue(self.prepared(stop_at="plan"), self.root, stop_at="verify", change_source="u9: 구현까지")
        unapproved = self.save(work.handoff(request_path=".dev/run-1/intake.json", project_root=self.root,
                                            run_id="run-1"))
        with self.assertRaisesRegex(ValueError, "진입"):
            work.reissue(unapproved, self.root, stop_at="pr", change_source="u9: PR까지")

    def test_cli_reissue_success_and_errors(self):
        handoff = self.prepared()
        code, out, err = self.cli(SCRIPT, "reissue", "--handoff", handoff, "--project-root", self.root,
                                  "--stop-at", "commit")
        self.assertEqual((code, err), (2, ""))
        failure = json.loads(out)
        self.assertIn("change-source", failure["error"])
        self.assertFalse(failure["ready-for-tdd"])
        code, out, err = self.cli(SCRIPT, "reissue", "--handoff", handoff, "--project-root", self.root,
                                  "--stop-at", "commit", "--change-source", "u9: 커밋까지")
        self.assertEqual((code, err), (0, ""))
        result = json.loads(out)
        self.assertEqual((result["stop-at"], result["run-id"]), ("commit", "run-1"))
        self.assertEqual(result["reissued-from-sha256"], hashlib.sha256(handoff.read_bytes()).hexdigest())


class F06GitStateTests(Project):
    def test_detached_head_is_a_readonly_result(self):
        self.git()
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "--allow-empty", "-m", "init"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "checkout", "--detach"], check=True, capture_output=True)
        before = self.snapshot()
        for intent in ("implement", "resume"):
            with self.subTest(intent=intent):
                result = work.route(self.root, intent, goal="새 기능")
                self.assertEqual(result["action"], "detached-head")
                self.assertTrue(result["read-only"])
                self.assertIsNone(result["skill"])
        self.assertEqual(work.route(self.root, "status")["action"], "status")
        self.assertEqual(self.snapshot(), before)

    def test_git_failure_other_than_not_a_repository_is_an_error(self):
        failure = subprocess.CompletedProcess(["git"], 128, "", "fatal: detected dubious ownership in repository at 'X'\n")
        with mock.patch.object(work.subprocess, "run", return_value=failure):
            with self.assertRaises(ValueError) as caught:
                work.route(self.root, "implement")
        self.assertIn("dubious ownership", str(caught.exception))
        self.assertIn("--git-safe-directory", str(caught.exception))

    def test_safe_directory_is_per_command_and_only_for_the_confirmed_root(self):
        self.git()
        calls, real = [], subprocess.run

        def spy(command, *args, **kwargs):
            calls.append(list(command))
            return real(command, *args, **kwargs)

        with mock.patch.object(work.subprocess, "run", side_effect=spy):
            self.assertEqual(work.route(self.root, "implement", git_safe_directory=self.root)["action"], "implement")
        git_calls = [command for command in calls if command[0] == "git"]
        self.assertTrue(git_calls)
        for command in git_calls:
            self.assertEqual(command[1:3], ["-c", f"safe.directory={self.root.as_posix()}"])
        with self.assertRaises(ValueError):
            work.route(self.root, "implement", git_safe_directory=self.root.parent)

    def test_cli_route_errors_are_json(self):
        code, out, err = self.cli(SCRIPT, "route", "--project-root", self.root / "missing", "--intent", "implement")
        self.assertEqual((code, err), (2, ""))
        self.assertIn("project-root", json.loads(out)["error"])


class F07PendingOwnershipTests(Project):
    def pending(self, slug="feature-limit"):
        path = self.root / ".dev" / slug / "pending-question.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, "question_set_id": str(uuid.uuid4()), "phase": "design",
                                    "questions": [entry_question()]}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_completed_run_pending_is_only_reported_as_stale(self):
        self.git()
        self.state(status="completed")
        pending = self.pending()
        for intent, action in (("implement", "implement"), ("resume", "no-active-run")):
            with self.subTest(intent=intent):
                result = work.route(self.root, intent, goal="새 기능")
                self.assertEqual(result["action"], action)
                self.assertEqual(result["stale-pending-file"], str(pending))
                self.assertIsNone(result["run-id"])
                self.assertNotIn("pending-goal", result)

    def test_legacy_dev_pending_does_not_preempt_migration(self):
        self.git()
        self.state(pipeline="gx-dev")
        self.pending()
        for intent in ("implement", "resume"):
            with self.subTest(intent=intent):
                result = work.route(self.root, intent)
                self.assertEqual(result["action"], "migration-required")
                self.assertTrue(result["read-only"])

    def test_active_tdd_pending_waits_with_run_identity(self):
        self.git()
        self.state()
        self.pending()
        result = work.route(self.root, "resume")
        self.assertEqual(result["action"], "awaiting-decision")
        self.assertEqual((result["pending-run-id"], result["pending-goal"], result["pending-phase"]),
                         ("old-run", "기존 목표", "design"))


class F08ScopeBeforeEndpointTests(Project):
    def test_different_goal_and_endpoint_is_a_scope_review(self):
        self.git()
        self.state()
        result = work.route(self.root, "implement", stop_at="pr", goal="새 정산 보고서")
        self.assertEqual(result["action"], "scope-review-required")
        self.assertEqual((result["stop-at"], result["requested-stop-at"]), ("commit", "pr"))
        self.assertTrue(result["requires-user-decision"])

    def test_endpoint_change_on_resume_is_reported_without_expanding(self):
        self.git()
        self.state()
        result = work.route(self.root, "resume", stop_at="pr")
        self.assertEqual(result["action"], "resume")
        self.assertEqual((result["stop-at"], result["requested-stop-at"]), ("commit", "pr"))
        self.assertTrue(result["stop-at-change-required"])
        self.assertNotIn("stop-at-change-required", work.route(self.root, "resume", stop_at="commit"))

    def test_every_route_result_keeps_requested_endpoint(self):
        self.git()
        for intent, stop_at in (("implement", "pr"), ("understand", None), ("plan", "plan"), ("status", None),
                                ("resume", "commit")):
            with self.subTest(intent=intent):
                self.assertEqual(work.route(self.root, intent, stop_at=stop_at)["requested-stop-at"], stop_at)
        self.state(pipeline="gx-dev")
        self.assertEqual(work.route(self.root, "implement", stop_at="pr")["requested-stop-at"], "pr")
        self.assertEqual(work.route(self.root, "implement", stop_at="verify", goal="랄프로 개발해줘")["requested-stop-at"],
                         "verify")


class F09RetiredRequestTests(Project):
    def test_readonly_intents_are_not_blocked_by_mentions(self):
        for intent in ("understand", "plan", "status"):
            for goal in ("--ralph 지원이 왜 중단됐는지 설명해줘", "랄프로 개발해줘"):
                with self.subTest(intent=intent, goal=goal):
                    result = work.route(self.root, intent, goal=goal)
                    self.assertEqual(result["action"], intent)
                    self.assertTrue(result["read-only"])

    def test_paths_filenames_and_management_requests_are_not_execution(self):
        for goal in ("scripts/gx-ralph.sh 파일 삭제해줘", "gx-ralph.sh 지워줘",
                     ".claude/skills/gx-ralph-iterate/SKILL.md 정리해줘", "`/gx-ralph` 스킬 파일 지워줘",
                     "--ralph 옵션 지워줘", "--ralph가 뭐야?", "--ralph는 왜 없어졌어",
                     "--ralph에서 TDD로 전환해줘", "gx-ralph에서 일반 TDD로 전환할 방법 알려줘",
                     "랄프로 진행하던 작업을 TDD로 전환해줘", "for 루프 돌려서 합계를 구하는 함수 구현해줘"):
            with self.subTest(goal=goal):
                self.assertEqual(work.route(self.root, "implement", goal=goal)["action"], "implement")

    def test_explicit_execution_is_still_blocked(self):
        for goal in ("랄프로 개발해줘", "루프 돌려", "랄프 루프 돌려줘", "/gx-ralph", "--ralph 결제 기능 구현",
                     "문서를 정리해줘. 그리고 랄프로 개발해줘", "gx-ralph.sh 지우고 랄프로 개발해줘",
                     "랄프로 전환해서 개발해줘"):
            with self.subTest(goal=goal):
                self.assertEqual(work.route(self.root, "implement", goal=goal)["action"], "unsupported-request")


class F10EncodingTests(Project):
    def svn(self, config=b'{"vcs": "svn"}'):
        path = self.root / ".claude" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(config)

    def svn_state(self, slug):
        return self.state(slug, run_id=f"{slug}-run", goal=slug)

    def test_bom_and_multiline_pointer_still_finds_the_lock(self):
        self.svn()
        self.svn_state("alpha")
        lock = self.root / ".dev/beta/ralph.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("runner", encoding="utf-8")
        (self.root / ".dev/.active").write_bytes("\ufeffbeta\r\nalpha\n".encode("utf-8"))
        self.assertEqual(work.route(self.root, "implement")["action"], "loop-active")

    def test_unsafe_pointer_falls_back_to_trunk_like_the_capture_hook(self):
        self.svn()
        self.svn_state("trunk")
        for pointer in ("../alpha", "a b", "beta."):
            with self.subTest(pointer=pointer):
                (self.root / ".dev/.active").write_text(pointer, encoding="utf-8")
                self.assertEqual(work.route(self.root, "resume")["run-id"], "trunk-run")

    def test_bom_config_keeps_svn_mode(self):
        self.svn(b'\xef\xbb\xbf{"vcs": "svn"}')
        self.svn_state("beta")
        (self.root / ".dev/.active").write_text("beta", encoding="utf-8")
        self.assertEqual(work.route(self.root, "resume")["run-id"], "beta-run")

    def test_bom_state_is_parsed(self):
        self.git()
        path = self.state()
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        result = work.route(self.root, "resume")
        self.assertEqual((result["action"], result["existing-pipeline"], result["run-id"]),
                         ("resume", "gx-tdd", "old-run"))

    def test_bom_json_inputs_are_accepted(self):
        path = self.request(raw=b"\xef\xbb\xbf" + json.dumps({"goal": "기능"}, ensure_ascii=False).encode("utf-8"))
        result = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: 진행")
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_utf16_inputs_are_rejected_with_a_clear_message(self):
        path = self.request(raw=json.dumps({"goal": "기능"}, ensure_ascii=False).encode("utf-16"))
        with self.assertRaises(ValueError) as caught:
            work.handoff(request_path=path, project_root=self.root, run_id="run-1")
        self.assertIn("UTF-8", str(caught.exception))
        code, out, err = self.cli(SCRIPT, "validate-plan", "--plan", path)
        self.assertEqual((code, err), (2, ""))
        self.assertIn("UTF-8", json.loads(out)["error"])


class F11QuestionBindingTests(Project):
    def test_pending_question_set_cannot_approve_entry(self):
        path = self.request()
        identifier = self.register("run-1")
        with self.assertRaisesRegex(ValueError, "응답"):
            work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                         entry_approval_source="u3: 진행", question_set_id=identifier)

    def test_fabricated_or_unrecorded_question_set_is_rejected(self):
        path = self.request()
        for identifier in ("gx_work_tdd_entry", str(uuid.uuid4())):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError) as caught:
                work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                             entry_approval_source="u3: 진행", question_set_id=identifier)
            self.assertIn("question-set-id", str(caught.exception))

    def test_answered_question_set_is_accepted_and_revalidated(self):
        self.git()
        path = self.request()
        # 리뷰 1: 인계 run의 디렉토리(.dev/run-1) 기록이거나 영수증의 run_id가 인계 run-id와 같아야 한다.
        for slug, context in (("run-1", {}), ("feature-limit", {"run_id": "run-1"})):
            with self.subTest(slug=slug):
                identifier = self.answered(slug, **context)
                result = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                                      entry_approval_source="u3: gx-tdd로 진행", question_set_id=identifier)
                self.assertTrue(result["ready-for-tdd"])
                self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_route_does_not_ask_again_after_a_recorded_entry_answer(self):
        self.git()
        identifier = self.answered("feature-limit", goal="결제 한도 구현", run_id="run-1")
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertEqual(result["action"], "implement")
        self.assertTrue(result["entry-answer-recorded"])
        self.assertFalse(result["requires-user-decision"])
        self.assertEqual((result["answered-question-set-id"], result["answered-run-id"]), (identifier, "run-1"))
        self.assertTrue(work.route(self.root, "implement", goal="다른 기능")["requires-user-decision"])

    def test_completed_run_handoff_is_not_reused(self):
        self.git()
        path = self.request()
        handoff = self.save(work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                                         entry_approval_source="u3: 진행"))
        self.assertTrue(work.validate_handoff(handoff, self.root)["ready-for-tdd"])
        self.state(status="completed", run_id="run-1")
        checked = work.validate_handoff(handoff, self.root)
        self.assertFalse(checked["ready-for-tdd"])
        self.assertIn("완료", checked["error"])
        with self.assertRaisesRegex(ValueError, "완료"):
            work.reissue(handoff, self.root, stop_at="pr", change_source="u9: PR까지")


class F12PlanConsistencyTests(Project):
    def test_validate_plan_and_handoff_agree_on_shared_fields(self):
        for key, value in (("sources", "문자열"), ("requirements", {"domain": "계량기"}), ("work-id", "W1"),
                           ("execution-method", "auto"), ("model-profile", "fast")):
            with self.subTest(key=key):
                document = plan()
                document[key] = value
                self.assertTrue(any(issue["path"] == key for issue in work.validate_plan(document)))
                path = self.request(document, ".dev/run-1/plan.json")
                with self.assertRaises(ValueError):
                    work.handoff(path, project_root=self.root, run_id="run-1")

    def test_duplicate_json_keys_are_rejected(self):
        path = self.request(raw='{"goal": "기능", "goal": "다른 기능"}'.encode("utf-8"))
        with self.assertRaisesRegex(ValueError, "중복"):
            work.handoff(request_path=path, project_root=self.root, run_id="run-1")
        code, out, err = self.cli(SCRIPT, "validate-plan", "--plan", path)
        self.assertEqual((code, err), (2, ""))
        self.assertIn("중복", json.loads(out)["error"])


class F13StateParsingTests(Project):
    def test_comments_quotes_and_block_list_flags(self):
        self.git()
        base = ("pipeline: gx-tdd  # 파이프라인\nstatus: \"in_progress\"\nrun-id: 'old-run'\n"
                "goal: \"기존 # 목표\"\nstop-at: commit # 종료점\nflags:\n  - --isolated\n")
        self.state(text=base)
        result = work.route(self.root, "resume")
        self.assertEqual((result["action"], result["run-id"], result["goal"], result["stop-at"]),
                         ("resume", "old-run", "기존 # 목표", "commit"))
        self.state(text=base + "  - --ralph\n")
        self.assertEqual(work.route(self.root, "resume")["action"], "migration-required")

    def test_lines_after_the_first_yaml_block_are_ignored(self):
        self.git()
        fields = "pipeline: gx-tdd\nstatus: in_progress\nrun-id: old-run\ngoal: 기존 목표\nstop-at: commit\n"
        for text in (fields + "---\nstatus: completed\npipeline: gx-dev\n",
                     "---\n" + fields + "---\n# 메모\nstatus: completed\n",
                     fields + "steps:\n  implement:\n    - status: completed\n"):
            with self.subTest(text=text):
                self.state(text=text)
                self.assertEqual(work.route(self.root, "resume")["action"], "resume")

    def test_invalid_or_empty_saved_endpoint_is_an_error(self):
        self.git()
        for value in ("", "everything", "PR"):
            with self.subTest(value=value):
                self.state(stop_at=value)
                with self.assertRaises(ValueError) as caught:
                    work.route(self.root, "resume")
                for needle in ("stop-at", "verify"):
                    self.assertIn(needle, str(caught.exception))
                self.assertEqual(work.route(self.root, "status")["action"], "status")


class F14RequestBlockingTests(Project):
    def test_blocking_unresolved_and_conflicting_decisions_block_request_handoff(self):
        # 리뷰 4: 결정 충돌은 gx-context intake와 같이 근거 있는 explicit끼리이며 차단 impact일 때만 차단한다.
        cases = ({"unresolved": [{"topic": "한도", "blocking": True}]},
                 {"decisions": [{"topic": "인증", "value": "세션", "status": "explicit", "source": "u1",
                                 "impact": "architecture"},
                                {"topic": "인증", "value": "JWT", "status": "explicit", "source": "u2",
                                 "impact": "architecture"}]},
                 {"unresolved": [{"topic": "한도"}]})
        for extra in cases:
            with self.subTest(extra=extra):
                path = self.request({"goal": "기능", **extra})
                with self.assertRaises(ValueError) as caught:
                    work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                                 entry_approval_source="u3: 진행")
                self.assertTrue(caught.exception.issues)
                code, out, err = self.cli(SCRIPT, "handoff", "--request", path, "--project-root", self.root,
                                          "--run-id", "run-1", "--entry-approval-source", "u3: 진행")
                self.assertEqual((code, err), (2, ""))
                failure = json.loads(out)
                self.assertFalse(failure["ready-for-tdd"])
                self.assertTrue(failure["issues"])

    def test_non_blocking_unresolved_is_preserved(self):
        path = self.request({"goal": "기능", "unresolved": [{"topic": "문구", "blocking": False}]})
        result = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: 진행")
        self.assertTrue(result["ready-for-tdd"])
        self.assertEqual(result["unresolved"], [{"topic": "문구", "blocking": False}])


class F15CliJsonTests(Project):
    def test_argument_errors_are_json_on_stdout(self):
        for args in (("handoff", "--request", "a.json", "--plan", "b.json"), ("handoff",),
                     ("route", "--project-root", self.root), ("unknown",),
                     ("route", "--project-root", self.root, "--intent", "bogus")):
            with self.subTest(args=args):
                code, out, err = self.cli(SCRIPT, *args)
                self.assertEqual((code, err), (2, ""))
                self.assertIn("error", json.loads(out))

    def test_deeply_nested_json_is_reported_without_traceback(self):
        depth = 100000
        path = self.request(raw=('{"goal": "기능", "sources": ' + "[" * depth + "]" * depth + "}").encode("utf-8"))
        for args in (("validate-plan", "--plan", path),
                     ("handoff", "--request", path, "--project-root", self.root, "--run-id", "run-1")):
            with self.subTest(command=args[0]):
                code, out, err = self.cli(SCRIPT, *args)
                self.assertEqual((code, err), (2, ""))
                self.assertIn("중첩", json.loads(out)["error"])


class F16ProjectRootTests(Project):
    def test_git_subdirectory_is_normalized_to_the_toplevel(self):
        self.git()
        self.state()
        subdirectory = self.root / "src" / "pkg"
        subdirectory.mkdir(parents=True)
        result = work.route(subdirectory, "resume")
        self.assertEqual((result["action"], result["run-id"]), ("resume", "old-run"))
        self.assertEqual(result["project-root"], str(self.root))
        self.assertEqual(result["requested-project-root"], str(subdirectory))
        self.assertNotIn("requested-project-root", work.route(self.root, "resume"))
        self.request()
        handoff = work.handoff(request_path=self.root / ".dev/run-1/intake.json", project_root=subdirectory,
                               run_id="run-1", entry_approval_source="u3: 진행")
        self.assertEqual(handoff["request-file"], ".dev/run-1/intake.json")
        self.assertTrue(work.validate_handoff(self.save(handoff), subdirectory)["ready-for-tdd"])

    def test_svn_working_copy_without_config_is_recognized(self):
        (self.root / ".svn").mkdir()
        self.state("beta", run_id="beta-run")
        (self.root / ".dev/.active").write_text("beta\n", encoding="utf-8")
        subdirectory = self.root / "module"
        subdirectory.mkdir()
        for start in (self.root, subdirectory):
            with self.subTest(start=start):
                self.assertEqual(work.route(start, "resume")["run-id"], "beta-run")


class F17PendingLifecycleTests(Project):
    def test_stateless_pending_reports_goal_run_and_phase(self):
        self.git()
        identifier = self.register("feature-limit", goal="결제 한도 구현", run_id="run-1")
        result = work.route(self.root, "implement", goal="다른 기능")
        self.assertEqual(result["action"], "awaiting-decision")
        self.assertEqual((result["pending-goal"], result["pending-run-id"], result["pending-phase"]),
                         ("결제 한도 구현", "run-1", "work-entry"))
        self.assertEqual(result["pending-question-set-id"], identifier)
        status = work.route(self.root, "status")
        self.assertEqual(status["action"], "status")
        self.assertEqual(status["pending-goal"], "결제 한도 구현")

    def test_register_keeps_work_identity_and_rejects_other_work(self):
        first = self.register("run-1", goal="결제 한도 구현", run_id="run-1")
        self.assertEqual(self.register("run-1", goal="결제 한도 구현", run_id="run-1"), first)
        for context in ({"goal": "다른 기능", "run_id": "run-1"}, {}):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.register("run-1", **context)
        with self.assertRaises(ValueError):
            self.register("run-2", goal="기능", run_id="a b")

    def test_discard_archives_records_and_releases(self):
        self.git()
        identifier = self.register("feature-limit", goal="결제 한도 구현", run_id="run-1")
        result, code = gate.run("discard", self.root, ".dev/feature-limit", reason="u7: 폐기하고 새 작업")
        self.assertEqual((code, result["status"], result["question_set_id"]), (0, "discarded", identifier))
        directory = self.root / ".dev/feature-limit"
        self.assertFalse((directory / gate.PENDING).exists())
        archives = list(directory.glob("discarded-question-*.json"))
        self.assertEqual(len(archives), 1)
        archived = json.loads(archives[0].read_text(encoding="utf-8"))
        self.assertEqual((archived["question"]["question_set_id"], archived["reason"]),
                         (identifier, "u7: 폐기하고 새 작업"))
        record = (directory / "decisions.md").read_text(encoding="utf-8")
        self.assertIn("u7: 폐기하고 새 작업", record)
        self.assertIn(f"<!-- gx-question-discarded:{identifier} -->", record)
        self.assertNotIn(f"<!-- gx-question:{identifier}:", record)
        self.assertNotIn("**A.**", record)
        self.assertEqual(gate.run("status", self.root, ".dev/feature-limit"), ({"status": "clear"}, 0))
        self.assertEqual(work.route(self.root, "implement", goal="새 기능")["action"], "implement")

    def test_discard_requires_reason_pending_and_free_lock(self):
        with self.assertRaises(ValueError):
            gate.run("discard", self.root, ".dev/run-1", reason="u7: 폐기")
        self.register("run-1")
        for reason in (None, " "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                gate.run("discard", self.root, ".dev/run-1", reason=reason)
        (self.root / ".dev/run-1/.question-lock").write_text("123", encoding="utf-8")
        with self.assertRaises((ValueError, OSError)):
            gate.run("discard", self.root, ".dev/run-1", reason="u7: 폐기")
        self.assertTrue((self.root / ".dev/run-1" / gate.PENDING).exists())

    def test_discard_retry_after_partial_failure_keeps_one_archive_and_record(self):
        self.register("run-1")
        with mock.patch.object(gate, "atomic_text", side_effect=OSError("storage failure")):
            with self.assertRaises(OSError):
                gate.run("discard", self.root, ".dev/run-1", reason="u7: 폐기")
        self.assertTrue((self.root / ".dev/run-1" / gate.PENDING).exists())
        gate.run("discard", self.root, ".dev/run-1", reason="u7: 폐기")
        directory = self.root / ".dev/run-1"
        self.assertEqual(len(list(directory.glob("discarded-question-*.json"))), 1)
        self.assertEqual((directory / "decisions.md").read_text(encoding="utf-8").count("gx-question-discarded"), 1)

    def test_cli_discard_exit_codes(self):
        self.register("run-1")
        base = ("discard", "--cwd", self.root, "--dev-dir", ".dev/run-1")
        code, out, err = self.cli(QUESTION, *base)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["status"], "blocked")
        code, out, err = self.cli(QUESTION, *base, "--reason", "u7: 폐기하고 새 작업")
        self.assertEqual((code, json.loads(out)["status"]), (0, "discarded"))
        code, out, err = self.cli(QUESTION, *base, "--reason", "u7: 다시")
        self.assertEqual(code, 2)


class F25OptionalFieldTests(Project):
    def test_execution_method_and_model_profile_are_preserved_and_bound(self):
        path = self.request({"goal": "기능", "work-id": "W118", "execution-method": "subagents",
                             "model-profile": "eco"})
        result = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                              entry_approval_source="u3: 진행")
        self.assertEqual((result["work-id"], result["execution-method"], result["model-profile"]),
                         ("W118", "subagents", "eco"))
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])
        result["execution-method"] = "session"
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])
        plain = work.handoff(request_path=self.request({"goal": "기능"}), project_root=self.root, run_id="run-1")
        self.assertEqual((plain["execution-method"], plain["model-profile"]), (None, None))

    def test_invalid_optional_values_are_rejected_with_allowed_values(self):
        for key, value, allowed in (("execution-method", "auto", "subagents"), ("model-profile", "fast", "eco"),
                                    ("execution-method", 1, "session")):
            with self.subTest(key=key, value=value):
                path = self.request({"goal": "기능", key: value})
                with self.assertRaises(ValueError) as caught:
                    work.handoff(request_path=path, project_root=self.root, run_id="run-1")
                for needle in (key, str(value), allowed):
                    self.assertIn(needle, str(caught.exception))


class F30ErrorMessageTests(Project):
    def test_errors_name_field_value_and_expected_format(self):
        path = self.request()
        with self.assertRaises(ValueError) as caught:
            work.handoff(request_path=path, project_root=self.root, run_id="run 1")
        for needle in ("run-id", "run 1", "A-Za-z0-9"):
            self.assertIn(needle, str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            work.handoff(request_path=path, project_root=self.root, run_id="run-1", stop_at="ship")
        for needle in ("stop-at", "ship", "verify"):
            self.assertIn(needle, str(caught.exception))

    def test_plan_issues_are_structured_in_cli_output(self):
        path = self.request({"goal": "기능", "units": []}, ".dev/run-1/plan.json")
        code, out, err = self.cli(SCRIPT, "handoff", "--plan", path, "--project-root", self.root, "--run-id", "run-1")
        self.assertEqual((code, err), (2, ""))
        failure = json.loads(out)
        self.assertTrue(all(isinstance(issue, dict) and issue.get("path") for issue in failure["issues"]))
        self.assertFalse(failure["error"].lstrip().startswith("{"))
        self.assertIn("units", failure["error"])


class F13StateLayoutTests(Project):
    """리뷰 High: state.md가 펜스·제목·본문 뒤 YAML이어도 훅과 같은 실행을 본다."""

    BODY = "pipeline: gx-tdd\nstatus: in_progress\nphase: implement\nrun-id: old-run\ngoal: 기존 목표\nstop-at: commit\n"
    LAYOUTS = {
        "fenced": "```yaml\n" + BODY + "```\n\n본문 설명\n",
        "heading+frontmatter": "# 작업 상태\n\n---\n" + BODY + "---\n\n본문\n",
        "heading+fenced": "# 작업 상태\n\n```yaml\n" + BODY + "```\n",
        "yaml-after-body": "# 진행 기록\n\n작업 메모를 먼저 적었다.\n\n" + BODY,
    }

    def test_route_sees_in_progress_run_in_every_layout(self):
        self.git()
        for name, text in self.LAYOUTS.items():
            with self.subTest(layout=name):
                self.state(text=text)
                self.assertEqual(work.route(self.root, "resume")["action"], "resume")
                other = work.route(self.root, "implement", goal="전혀 다른 목표")
                self.assertEqual(other["action"], "scope-review-required")

    def test_structured_block_value_is_not_overridden_by_body(self):
        self.git()
        self.state(text="```yaml\n" + self.BODY + "```\n\nstatus: completed 처리 예정\n")
        self.assertEqual(work.route(self.root, "resume")["action"], "resume")

    def test_completed_run_in_fence_is_still_recognised(self):
        self.git()
        self.state(text="```yaml\n" + self.BODY.replace("in_progress", "completed") + "```\n")
        self.assertTrue(work.completed_state(self.root, "old-run"))


class F36LegacyExitTests(Project):
    def test_legacy_results_explain_how_to_start_a_new_scope(self):
        self.git()
        for pipeline, locked, action in (("gx-dev", False, "migration-required"),
                                         ("gx-ralph", False, "migration-required"),
                                         ("gx-ralph", True, "loop-active")):
            with self.subTest(pipeline=pipeline, locked=locked):
                path = self.state(pipeline=pipeline)
                if locked:
                    path.with_name("ralph.lock").write_text("runner", encoding="utf-8")
                result = work.route(self.root, "implement", goal="새 기능")
                self.assertEqual(result["action"], action)
                for needle in ("새 브랜치", "워크트리", "/oh-my-gx:gx-work", "새 범위", "--slug", ".dev/.active"):
                    self.assertIn(needle, result["reason"])


class F36SvnSlugEscapeTests(Project):
    """SVN은 .dev/.active가 구버전 slug를 가리켜도 새 slug를 명시하면 그 slug만 검사한다."""

    def setUp(self):
        super().setUp()
        config = self.root / ".claude" / "config.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"vcs": "svn"}', encoding="utf-8")
        self.state("legacy", pipeline="gx-dev", run_id="legacy-run")
        (self.root / ".dev/.active").write_text("legacy\n", encoding="utf-8")

    def test_pointer_to_legacy_run_blocks_only_without_an_explicit_slug(self):
        before = self.snapshot()
        self.assertEqual(work.route(self.root, "implement", goal="새 결제")["action"], "migration-required")
        result = work.route(self.root, "implement", goal="새 결제", slug="new-pay")
        self.assertEqual((result["action"], result["requested-slug"], result["state-file"]),
                         ("implement", "new-pay", None))
        self.assertEqual(self.snapshot(), before)

    def test_explicit_slug_applies_every_guard_to_that_slug(self):
        lock = self.root / ".dev/new-pay/ralph.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("runner", encoding="utf-8")
        self.assertEqual(work.route(self.root, "implement", slug="new-pay")["action"], "loop-active")
        lock.unlink()
        self.state("new-pay", run_id="new-run", goal="새 결제")
        result = work.route(self.root, "resume", slug="new-pay")
        self.assertEqual((result["action"], result["run-id"]), ("resume", "new-run"))
        self.assertEqual(work.route(self.root, "implement", goal="다른 기능", slug="new-pay")["action"],
                         "scope-review-required")

    def test_explicit_slug_skips_candidate_selection(self):
        (self.root / ".dev/.active").unlink()
        self.state("alpha", run_id="alpha-run")
        self.assertEqual(work.route(self.root, "implement")["action"], "resume-selection-required")
        self.assertEqual(work.route(self.root, "implement", slug="beta")["action"], "implement")

    def test_slug_must_be_safe_and_svn_only(self):
        for slug in ("../legacy", "a b", "beta.", ".", "a/b"):
            with self.subTest(slug=slug), self.assertRaises(ValueError) as caught:
                work.route(self.root, "implement", slug=slug)
            self.assertIn("slug", str(caught.exception))
        (self.root / ".claude/config.json").unlink()
        self.git()
        with self.assertRaisesRegex(ValueError, "SVN"):
            work.route(self.root, "implement", slug="new-pay")

    def test_cli_accepts_slug(self):
        code, out, err = self.cli(SCRIPT, "route", "--project-root", self.root, "--intent", "implement",
                                  "--goal", "새 결제", "--slug", "new-pay")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["action"], "implement")


class ReviewQuestionBindingTests(Project):
    """독립 리뷰 1·2·5·9: 질문 기록은 인계 run에 결박되고 답변 선택까지 확인한다."""

    def entry(self, identifier, run_id="run-1"):
        return work.handoff(request_path=".dev/run-1/intake.json", project_root=self.root, run_id=run_id,
                            entry_approval_source="u3: gx-tdd로 진행", question_set_id=identifier)

    def test_answer_from_another_run_or_directory_is_not_accepted(self):
        self.git()
        self.request()
        for context in ({"run_id": "run-9"}, {}):
            with self.subTest(context=context), self.assertRaisesRegex(ValueError, "question-set-id"):
                self.entry(self.answered("feature-limit", **context))
        identifier = self.answered("feature-limit")
        line = self.marker_line("feature-limit", identifier)
        other = self.root / ".dev/other-run/decisions.md"
        other.parent.mkdir(parents=True)
        other.write_text("# 의사결정 기록\n\n" + line + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "question-set-id"):
            self.entry(identifier)
        own = self.root / ".dev/run-1/decisions.md"
        own.write_text("# 의사결정 기록\n\n" + line + "\n", encoding="utf-8")
        result = self.entry(identifier)
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])
        self.assertTrue(self.entry(self.answered("feature-limit", run_id="run-1"))["ready-for-tdd"])

    def test_marker_must_be_a_complete_line(self):
        self.request()
        identifier = str(uuid.uuid4())
        own = self.root / ".dev/run-1/decisions.md"
        for text in ("```\n    " + f"<!-- gx-question:{identifier}:x -->" + "\n```\n",
                     f"메모 <!-- gx-question:{identifier}:{'0' * 64} -->\n"):
            with self.subTest(text=text):
                own.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "question-set-id"):
                    self.entry(identifier)

    def test_missing_record_error_explains_copying_the_marker(self):
        self.git()
        self.request()
        handoff = self.save(self.entry(self.answered("feature-limit", run_id="run-1")))
        shutil.rmtree(self.root / ".dev/feature-limit")
        checked = work.validate_handoff(handoff, self.root)
        self.assertFalse(checked["ready-for-tdd"])
        for needle in (".dev/run-1/decisions.md", "복사"):
            self.assertIn(needle, checked["error"])

    def test_declined_entry_answer_cannot_approve_and_route_asks_again(self):
        self.git()
        self.request({"goal": "결제 한도 구현"})
        identifier = self.answered("feature-limit", selection="여기서 종료", goal="결제 한도 구현", run_id="run-1")
        receipt = json.loads((self.root / ".dev/feature-limit/answered-question.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["answers"], {"gx_work_tdd_entry": {"answers": ["여기서 종료"]}})
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertTrue(result["entry-answer-recorded"])
        self.assertTrue(result["requires-user-decision"])
        self.assertEqual(result["answered-selection"], ["여기서 종료"])
        with self.assertRaisesRegex(ValueError, "여기서 종료"):
            self.entry(identifier)
        self.answered("feature-limit", goal="결제 한도 구현", run_id="run-1")
        result = work.route(self.root, "implement", goal="결제 한도 구현")
        self.assertFalse(result["requires-user-decision"])
        self.assertEqual(result["answered-selection"], ["gx-tdd로 진행"])

    def copy_answer_block(self, slug, identifier):
        """문서대로 표식 줄부터 답변 블록까지 `.dev/run-1/decisions.md`로 옮기고 원래 기록은 없앤다."""
        text = (self.root / ".dev" / slug / "decisions.md").read_text(encoding="utf-8")
        block = text[text.index(f"<!-- gx-question:{identifier}:"):]
        shutil.rmtree(self.root / ".dev" / slug)
        (self.root / ".dev/run-1/decisions.md").write_text("# 의사결정 기록\n\n" + block, encoding="utf-8")

    def test_copied_answer_block_carries_the_entry_selection(self):
        self.git()
        self.request()
        identifier = self.answered("feature-limit", selection="여기서 종료")
        self.copy_answer_block("feature-limit", identifier)
        with self.assertRaisesRegex(ValueError, "여기서 종료"):
            self.entry(identifier)
        legacy = self.save(legacy_v1(self.root, self.root / ".dev/run-1/intake.json", "run-1", approval="u1",
                                     entry="u3: 진행", question_set_id=identifier))
        for kwargs in ({}, {"stop_at": "pr", "change_source": "u9: PR까지"}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "여기서 종료"):
                work.reissue(legacy, self.root, **kwargs)

    def test_copied_proceed_block_is_accepted_with_recommended_label(self):
        self.git()
        self.request()
        question = entry_question()
        question["options"][0]["label"] = "gx-tdd로 진행 (Recommended)"
        identifier = gate.run("register", self.root, ".dev/feature-limit",
                              {"phase": "work-entry", "questions": [question]})[0]["question_set_id"]
        gate.run("answer", self.root, ".dev/feature-limit", {"question_set_id": identifier, "answers": {
            "gx_work_tdd_entry": {"answers": ["gx-tdd로 진행 (Recommended)"]}}})
        self.copy_answer_block("feature-limit", identifier)
        result = self.entry(identifier)
        self.assertTrue(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_answer_receipt_of_a_completed_run_is_stale(self):
        self.git()
        self.answered("feature-limit", goal="결제 한도", run_id="run-1")
        self.state("feat-old", status="completed", run_id="run-1", goal="결제 한도")
        result = work.route(self.root, "implement", goal="결제 한도")
        self.assertNotIn("entry-answer-recorded", result)
        self.assertTrue(result["requires-user-decision"])
        self.assertEqual(result["stale-answered-file"], str(self.root / ".dev/feature-limit/answered-question.json"))

    def test_reissue_refuses_a_question_that_is_still_pending(self):
        self.git("main")
        request = self.request()
        identifier = self.register("main")
        self.save(legacy_v1(self.root, request, "run-1", approval="u1", entry="u3: 진행",
                            question_set_id=identifier))
        handoff = self.root / ".dev/run-1/handoff.json"
        self.assertFalse(work.validate_handoff(handoff, self.root)["ready-for-tdd"])
        for kwargs in ({}, {"stop_at": "pr", "change_source": "u9: PR까지"}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "응답"):
                work.reissue(handoff, self.root, **kwargs)


class ReviewLegacyReissueTests(Project):
    """독립 리뷰 3: 진행 중 3.0.0 실행은 v1 규칙(run-id 형식·요청 차단)으로 재발급 출구를 쓴다."""

    def legacy(self, run_id, value):
        request = self.request(value)
        return self.save(legacy_v1(self.root, request, run_id, approval="u1", entry="u3: 진행",
                                   question_set_id="gx_work_tdd_entry"))

    def test_legacy_run_id_and_old_request_rules_survive_reissue(self):
        handoff = self.legacy("run 1 한글", {"goal": "결제", "unresolved": [{"topic": "x"}],
                                             "decisions": [{"topic": "a", "value": "1", "status": "explicit",
                                                            "source": "u1", "impact": "scope"},
                                                           {"topic": "a", "value": "2", "status": "explicit",
                                                            "source": "u2", "impact": "scope"}]})
        self.assertTrue(work.validate_handoff(handoff, self.root)["ready-for-tdd"])
        result = work.reissue(handoff, self.root, stop_at="pr", change_source="u9: PR까지")
        self.assertEqual((result["run-id"], result["schema-version"], result["legacy-run-id"]), ("run 1 한글", 2, True))
        self.save(result)
        checked = work.validate_handoff(handoff, self.root)
        self.assertTrue(checked["ready-for-tdd"], checked)
        again = work.reissue(handoff, self.root, stop_at="commit", change_source="u10: 커밋까지")
        self.assertTrue(again["legacy-run-id"])
        result.pop("legacy-run-id")
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_new_handoffs_cannot_claim_the_legacy_exception(self):
        path = self.request({"goal": "결제", "unresolved": [{"topic": "x"}]})
        with self.assertRaises(ValueError):
            work.handoff(request_path=path, project_root=self.root, run_id="run 1")
        self.request({"goal": "결제"})
        result = work.handoff(request_path=path, project_root=self.root, run_id="run-1", entry_approval_source="u3")
        self.assertNotIn("legacy-run-id", result)
        result["legacy-run-id"] = True
        self.assertFalse(work.validate_handoff(self.save(result), self.root)["ready-for-tdd"])

    def test_path_unsafe_legacy_run_id_is_still_rejected(self):
        for run_id in ("../x", "a/b", "a\\b"):
            with self.subTest(run_id=run_id), self.assertRaisesRegex(ValueError, "run-id"):
                work.reissue(self.legacy(run_id, {"goal": "결제"}), self.root, stop_at="pr", change_source="u9")


class ReviewDecisionConflictTests(Project):
    """독립 리뷰 4: gx-context intake가 차단하지 않는 결정 차이는 인계도 차단하지 않는다."""

    def test_only_grounded_consequential_explicit_conflicts_block(self):
        cases = (
            [{"topic": "문구", "value": "A", "status": "explicit", "source": "u1", "impact": "metadata"},
             {"topic": "문구", "value": "B", "status": "explicit", "source": "u2", "impact": "metadata"}],
            [{"topic": "범위", "value": "❓", "status": "unresolved", "impact": "scope"},
             {"topic": "범위", "value": "전체", "status": "inferred", "impact": "scope", "delegation-source": "u2: 알아서"}],
            [{"topic": "인증", "value": "세션", "status": "explicit", "impact": "architecture"},
             {"topic": "인증", "value": "JWT", "status": "explicit", "impact": "architecture"}],
        )
        for decisions in cases:
            with self.subTest(decisions=decisions):
                path = self.request({"goal": "기능", "decisions": decisions})
                result = work.handoff(request_path=path, project_root=self.root, run_id="run-1",
                                      entry_approval_source="u3: 진행")
                self.assertTrue(result["ready-for-tdd"])


class ReviewRouteOrderTests(Project):
    """독립 리뷰 7·8: 미응답 질문이 state 오류보다 먼저이고, detached HEAD는 읽기 전용 결과에도 표시한다."""

    def test_pending_question_is_reported_before_an_invalid_saved_endpoint(self):
        self.git()
        self.state(stop_at="everything")
        self.register("feature-limit")
        self.assertEqual(work.route(self.root, "resume")["action"], "awaiting-decision")

    def test_readonly_results_mark_detached_head(self):
        self.git()
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "--allow-empty", "-m", "init"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "checkout", "--detach"], check=True, capture_output=True)
        for intent in ("status", "understand", "plan", "implement"):
            with self.subTest(intent=intent):
                self.assertTrue(work.route(self.root, intent)["detached-head"])
        subprocess.run(["git", "-C", str(self.root), "checkout", "-q", "feature/limit"], check=True, capture_output=True)
        self.assertNotIn("detached-head", work.route(self.root, "status"))


class ReviewMalformedPendingDiscardTests(Project):
    """독립 리뷰 6: 형식이 깨진 pending도 실제 결정으로 원문을 보관한 뒤 해제한다."""

    def test_malformed_pending_is_archived_byte_for_byte_and_released(self):
        directory = self.root / ".dev/run-1"
        directory.mkdir(parents=True)
        raw = b'{"version": 1, "questions": [\xff broken'
        (directory / gate.PENDING).write_bytes(raw)
        result, code = gate.run("discard", self.root, ".dev/run-1", reason="u7: 깨진 질문 폐기")
        self.assertEqual((code, result["status"], result["malformed"]), (0, "discarded", True))
        self.assertFalse((directory / gate.PENDING).exists())
        archives = list(directory.glob("discarded-question-*.json"))
        self.assertEqual(len(archives), 1)
        archived = json.loads(archives[0].read_text(encoding="utf-8"))
        self.assertEqual(base64.b64decode(archived["raw-base64"]), raw)
        self.assertEqual(archived["reason"], "u7: 깨진 질문 폐기")
        record = (directory / "decisions.md").read_text(encoding="utf-8")
        self.assertIn(f"<!-- gx-question-discarded:raw-sha256:{hashlib.sha256(raw).hexdigest()} -->", record)
        self.assertIn("u7: 깨진 질문 폐기", record)
        self.assertEqual(gate.run("status", self.root, ".dev/run-1"), ({"status": "clear"}, 0))

    def test_malformed_pending_retry_after_failure_keeps_one_archive(self):
        directory = self.root / ".dev/run-1"
        directory.mkdir(parents=True)
        (directory / gate.PENDING).write_text('{"version": 1}', encoding="utf-8")
        with mock.patch.object(gate, "atomic_text", side_effect=OSError("storage failure")):
            with self.assertRaises(OSError):
                gate.run("discard", self.root, ".dev/run-1", reason="u7: 폐기")
        self.assertTrue((directory / gate.PENDING).exists())
        gate.run("discard", self.root, ".dev/run-1", reason="u7: 폐기")
        self.assertEqual(len(list(directory.glob("discarded-question-*.json"))), 1)
        self.assertEqual((directory / "decisions.md").read_text(encoding="utf-8").count("gx-question-discarded"), 1)


if __name__ == "__main__":
    unittest.main()
