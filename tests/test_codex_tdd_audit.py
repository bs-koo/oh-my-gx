"""gx-work 전수조사(2026-11-09)의 gx-tdd 쪽 계약 회귀 검사.

gx-tdd의 지시문은 모델이 읽고 따르는 계약이라 문구가 곧 동작이다. 각 검사 이름에 결함 ID(fNN)를
붙였다. 문서에서 정규식·명령 블록을 꺼낼 수 있으면 그대로 실행해 확인한다. 실제 모델 세션의
행동(질문 UI·도구 호출)은 이 검사가 증명하지 않는다.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TDD = ROOT / ".claude/skills/gx-tdd"
GOLDEN = ROOT / "tests/golden-scenarios.md"


def read(relative: str) -> str:
    return (TDD / relative).read_text(encoding="utf-8")


def section(text: str, start: str, end: str | None = None) -> str:
    begin = text.index(start)
    if end is None:
        return text[begin:]
    return text[begin:text.index(end, begin + len(start))]


def line_with(text: str, *needles: str) -> str:
    return next(line for line in text.splitlines() if all(needle in line for needle in needles))


def description() -> str:
    meta = (TDD / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    return line_with(meta, "description:")


class WorkIdFormatTests(unittest.TestCase):
    """F01: W ID는 `W`+ASCII 숫자 2자리 이상(I1)."""

    def test_f01_value_format_accepts_three_digits(self):
        routing = read("references/intent-routing.md")
        flag = line_with(routing, "- `--work {ID}`가 포함되면")
        values = [token for token in re.findall(r"`([^`]+)`", flag) if token.startswith("^W")]
        self.assertEqual(values, ["^W[0-9]{2,}$"])
        pattern = re.compile(values[0])
        for sample, valid in (("W01", True), ("W99", True), ("W100", True), ("W118", True),
                              ("W1000", True), ("W1", False), ("W０１", False), ("W-01", False),
                              ("w01", False)):
            with self.subTest(sample=sample):
                self.assertEqual(bool(pattern.fullmatch(sample)), valid)
        self.assertIn("하이픈", flag, "이슈 키 오염을 막는 하이픈 금지 이유는 유지한다")
        self.assertNotIn("두 자리", routing)
        self.assertNotIn("`W00`~`W99`", routing)

    def test_f01_sentence_token_rule_runs_as_documented(self):
        rule = section(read("references/intent-routing.md"), "**WORK 추출 규칙**", "**Step 3")
        patterns = [token for token in re.findall(r"`([^`]+)`", rule) if token.startswith("(?<!")]
        self.assertEqual(len(patterns), 1, "문장 속 W 토큰 정규식은 한 곳에 둔다")
        token = re.compile(patterns[0])
        for sample, expected in (("W118 시작해줘", ["W118"]), ("phase W1000 개발해줘", ["W1000"]),
                                 ("W01 이어서 해줘", ["W01"]), ("W1 시작", []), ("W０１ 시작", []),
                                 ("W-01 시작", []), ("PW01 화면", []), ("W01a 버전", []),
                                 ("JIRA-W01 처리", [])):
            with self.subTest(sample=sample):
                self.assertEqual(token.findall(sample), expected)

    def test_f01_work_reference_steps_use_the_same_value_rule(self):
        reference = section(read("phases/setup-work.md"), "### 3.0.5", "#### 진행할 작업 확인")
        self.assertIn("^W[0-9]{2,}$", reference)
        lifecycle = read("references/document-lifecycle.md")
        self.assertNotIn("--work Wnn", lifecycle)


class EntryDescriptionTests(unittest.TestCase):
    def test_f02_description_targets_explicit_tdd_handoff_and_resume(self):
        text = description()
        for needle in ("TDD", "gx-work", "재개"):
            self.assertIn(needle, text)
        self.assertNotIn("기능 개발·버그 수정의 TDD 실행", text)
        self.assertRegex(text, r"일반[^.]*gx-work", "일반 개발 요청은 gx-work가 먼저 받는다")


class BranchPreparationTests(unittest.TestCase):
    """F03: 자동 stash는 필요할 때만, 다른 진행 중 실행의 변경은 옮기지 않는다."""

    def test_f03_setup_points_to_conditional_branch_preparation(self):
        setup = read("phases/phase-setup.md")
        step2 = section(setup, "## Step 2:", "## Step 3:")
        self.assertIn('Read("setup-branch.md")', step2)
        self.assertNotIn("gx-tdd-auto-$(date +%s)", setup)
        self.assertNotIn("`git stash pop`", setup)
        step5 = section(setup, "## Step 5:", "## Step 5.5:")
        self.assertIn("setup-branch.md", step5)
        self.assertIn("2.3", step5)

    def test_f03_classification_stops_before_moving_other_run_changes(self):
        branch = read("phases/setup-branch.md")
        table = section(branch, "| 순서 | 상황 | 처리 |", "\n\n")
        rows = [line for line in table.splitlines()[2:] if line.startswith("| ")]
        self.assertEqual(len(rows), 3)
        stop, carry, stash = rows
        # detached 워크트리에서는 gx-work route가 detached-head(읽기 전용)를 내므로 새 브랜치로 만든다(리뷰 High-3).
        for needle in ("다른 run-id", "status: in_progress", "중단", "git worktree add <경로> -b <새 브랜치> <베이스>"):
            self.assertIn(needle, stop)
        self.assertNotIn("--detach", stop)
        self.assertNotIn("git stash push", stop)
        self.assertIn("이번 실행 입력", carry)
        self.assertIn("stash하지 않는다", carry)
        self.assertIn("자동 stash", stash)
        definition = section(branch, "**이번 실행 입력**", "\n\n")
        self.assertIn(".dev/<run-id>/", definition)
        self.assertIn(".dev/plan.md", definition)

    def test_f03_stash_ref_is_recorded_before_state_exists(self):
        branch = read("phases/setup-branch.md")
        save = section(branch, "### 2.1.1 자동 stash", "## 2.2")
        self.assertIn("state가 생기기 전", save)
        self.assertIn("auto-stash.txt", save)
        self.assertIn("bare `git stash pop`", save)
        resume = read("phases/setup-resume.md")
        self.assertIn("stash 복원 충돌", resume)
        self.assertIn('Read("setup-branch.md")', resume)
        state = read("references/pipeline-state.md")
        self.assertRegex(state, r"(?m)^auto-stash: ")

    def test_f03_conflict_keeps_existing_two_choices_without_data_loss(self):
        branch = read("phases/setup-branch.md")
        restore = section(branch, "## 2.3 stash 복원", "## 재개")
        for needle in ("직접 해결 후 재개", "stash 보관하고 계속", "current-step: stash 복원 충돌",
                       "git reset --merge", "^3", "위험 수용"):
            self.assertIn(needle, restore)
        self.assertNotIn("stash를 drop하고 계속", restore, "충돌 표시가 남은 채 stash를 버리지 않는다")


class AutoStashProtocolTests(unittest.TestCase):
    """F03: setup-branch.md의 bash 블록을 임시 저장소에서 그대로 실행한다."""

    def setUp(self):
        self.bash = shutil.which("bash") or "bash"
        blocks = re.findall(r"```bash\n(.*?)\n```", read("phases/setup-branch.md"), re.S)
        self.save = next(block for block in blocks if "git stash push" in block)
        self.apply = next(block for block in blocks if "git stash apply" in block)
        self.cleanup = next(block for block in blocks if "git stash drop" in block)

    def git(self, root: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout

    def run_block(self, root: Path, block: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([self.bash, "-c", block], cwd=root, env=dict(os.environ, **env),
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def repository(self, directory: str) -> Path:
        root = Path(directory)
        self.git(root, "init", "-q", "-b", "main")
        for key, value in (("user.email", "t@example.invalid"), ("user.name", "T"), ("core.autocrlf", "false")):
            self.git(root, "config", key, value)
        (root / "a.txt").write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "base")
        return root

    def stash_entries(self, root: Path) -> list[str]:
        return self.git(root, "stash", "list", "--format=%H").split()

    def test_f03_stash_restore_keeps_run_inputs_and_other_sessions(self):
        with tempfile.TemporaryDirectory(prefix="gx tdd stash ") as directory:
            root = self.repository(directory)
            self.git(root, "checkout", "-q", "-b", "feat/old")
            (root / "a.txt").write_text("1-old\n2\n3\n4\n5\n", encoding="utf-8")
            self.git(root, "commit", "-qam", "old")
            (root / "other.txt").write_text("other\n", encoding="utf-8")
            self.git(root, "stash", "push", "-u", "-m", "other-session")
            other = self.stash_entries(root)[0]
            (root / "a.txt").write_text("1-old\n2\n3\n4\n5-dirty\n", encoding="utf-8")
            (root / "new.txt").write_text("new\n", encoding="utf-8")
            run_dir = root / ".dev/run-77"
            run_dir.mkdir(parents=True)
            (run_dir / "handoff.json").write_text("{}", encoding="utf-8")

            saved = self.run_block(root, self.save, RUN_ID="run-77")
            self.assertEqual(saved.returncode, 0, saved.stderr)
            record = (run_dir / "auto-stash.txt").read_text(encoding="utf-8").split()
            sha, source = record[0], record[1]
            self.assertEqual(source, "feat/old")
            self.assertIn(sha, self.stash_entries(root))
            self.assertTrue((run_dir / "handoff.json").is_file(), "실행 입력은 stash로 사라지지 않는다")
            porcelain = self.git(root, "status", "--porcelain").splitlines()
            self.assertTrue(porcelain and all(line.startswith("?? .dev/") for line in porcelain), porcelain)

            self.git(root, "checkout", "-q", "main")
            self.git(root, "checkout", "-q", "-b", "feat/new")
            applied = self.run_block(root, self.apply, RUN_ID="run-77", AUTO_STASH_SHA=sha)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            cleaned = self.run_block(root, self.cleanup, RUN_ID="run-77", AUTO_STASH_SHA=sha)
            self.assertEqual(cleaned.returncode, 0, cleaned.stderr)

            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "1\n2\n3\n4\n5-dirty\n")
            self.assertTrue((root / "new.txt").is_file())
            self.assertEqual(self.stash_entries(root), [other], "다른 세션의 stash는 그대로 둔다")
            self.assertFalse((run_dir / "auto-stash.txt").exists())
            self.assertTrue((run_dir / "handoff.json").is_file())

    def test_f03_run_inputs_only_leave_no_stash_or_record(self):
        with tempfile.TemporaryDirectory(prefix="gx tdd inputs ") as directory:
            root = self.repository(directory)
            run_dir = root / ".dev/run-88"
            run_dir.mkdir(parents=True)
            (run_dir / "handoff.json").write_text("{}", encoding="utf-8")
            saved = self.run_block(root, self.save, RUN_ID="run-88")
            self.assertEqual(saved.returncode, 0, saved.stderr)
            self.assertEqual(self.stash_entries(root), [])
            self.assertFalse((run_dir / "auto-stash.txt").exists())


class HandoffReissueTests(unittest.TestCase):
    """F04·F18·F25: 인계 재검증 실패의 출구, 상대 포인터, 선택 필드 소비."""

    def test_f04_resume_recheck_failure_reissues_then_validates_again(self):
        restore = section(read("phases/setup-resume.md"), "### 0.05", "### 0.1")
        for needle in ("reissue", "--change-source", "relocated", "validate-handoff", "실제 사용자 결정"):
            self.assertIn(needle, restore)
        self.assertLess(restore.index("reissue"), restore.rindex("validate-handoff"),
                        "재발급한 인계는 다시 검증한다")
        complete = section(read("phases/phase-complete.md"), "## Step -3", "## Step -2")
        self.assertIn("setup-resume.md", complete)
        self.assertIn("재발급", complete)

    def test_f04_consumer_accepts_v1_and_v2_and_names_reissue(self):
        handoff = read("references/plan-handoff.md")
        for needle in ("reissue", "schema-version", "v1", "v2", "../../../../scripts/gx-work.py"):
            self.assertIn(needle, handoff)
        self.assertTrue((TDD / "references" / "../../../../scripts/gx-work.py").resolve().is_file())

    def test_f18_state_pointers_are_project_relative_and_read_legacy_absolute(self):
        state = read("references/pipeline-state.md")
        row = line_with(state, "| `handoff-file`")
        self.assertIn("상대경로", row)
        self.assertIn("절대경로", row)
        example = section(state, "```yaml\nphase: implement", "\n```")
        for key in ("handoff-file", "request-file", "implementation-plan-file"):
            with self.subTest(key=key):
                value = re.search(rf'(?m)^{key}: "([^"]+)"', example).group(1)
                self.assertTrue(value.startswith(".dev/"), value)
        for relative in ("references/document-lifecycle.md", "phases/setup-explore.md"):
            with self.subTest(path=relative):
                self.assertNotIn(".dev/planning/", read(relative))
        self.assertNotIn("절대 포인터", read("phases/phase-implement.md"))

    def test_f25_optional_handoff_fields_are_consumed_without_skipping_review(self):
        handoff = read("references/plan-handoff.md")
        fields = section(handoff, "## 선택 필드", "\n## ")
        for field in ("`work-id`", "`execution-method`", "`model-profile`"):
            self.assertIn(field, fields)
        method = line_with(fields, "`execution-method`")
        self.assertIn("Step 1.2", method)
        self.assertIn("(Recommended)", method)
        self.assertIn("계획 검토", method)
        review = section(read("phases/phase-implement.md"), "### 1.2 계획 검토", "### 1.3")
        bullet = line_with(review, "인계의 `execution-method`")
        self.assertIn("(Recommended)", bullet)
        self.assertIn("명시 선택이 아니", bullet)
        profile = section(read("phases/phase-setup.md"), "## Step 1.5:", "## Step 2:")
        order = [line for line in profile.splitlines() if re.match(r"\d\. ", line)]
        self.assertIn("`model-profile`", order[1], "명시 플래그 다음 순위")
        reference = section(read("phases/setup-work.md"), "### 3.0.5", "1. ")
        self.assertIn("인계 `work-id`", reference)


class ReadOnlyAndModeTests(unittest.TestCase):
    def test_f19_read_only_handoff_saves_requested_prd_and_design_only(self):
        skill = (TDD / "SKILL.md").read_text(encoding="utf-8")
        entry = section(skill, "**계획 전용 인계**", "\n\n")
        self.assertIn("gx-work가 대화로", entry)
        self.assertIn("PRD·설계", entry)
        loop = section(skill, "### Phase 실행 루프", "### Phase 파일 경로")
        branch = section(loop, "if HANDOFF_READ_ONLY", "return  # READ_ONLY_COMPLETE")
        self.assertIn("저장", branch)
        handoff = read("references/plan-handoff.md")
        readonly = line_with(handoff, "`read-only: true`·`execution-authorized: false`")
        self.assertIn("run 디렉토리", readonly)
        self.assertIn("T태스크", readonly)

    def test_f22_gx_work_handoff_mode_comes_from_handoff_fields(self):
        routing = read("references/intent-routing.md")
        step1 = section(routing, "**Step 1: 플래그 호환**", "**Step 2: 자연어")
        rule = line_with(step1, "gx-work 인계의 모드 판정")
        for needle in ("`intent`", "`stop-at`", "`read-only`", "STATUS/RESUME/CORE", "명시 플래그"):
            self.assertIn(needle, rule)
        step2 = section(routing, "**Step 2: 자연어", "| 감지 패턴 |")
        self.assertIn("gx-work 인계", step2)

    def test_f42_run_id_owner_matches_handoff_contract(self):
        skill = (TDD / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("gx-work helper가 생성한", skill)
        owner = line_with(skill, "`run-id`", "직접 호출")
        self.assertIn("gx-work", owner)
        self.assertIn("setup", owner)


class SetupGuardTests(unittest.TestCase):
    def test_f21_config_guard_stops_with_user_command_before_branch_changes(self):
        setup = read("phases/phase-setup.md")
        self.assertNotIn('Skill("oh-my-gx:gx-setup")', setup)
        self.assertNotIn("CONFIG_SETUP_ATTEMPTS", setup)
        guard = section(setup, "### 3.0 config.json 가드", "### 3.0.4")
        self.assertIn("/oh-my-gx:gx-setup", guard)
        self.assertIn("중단", guard)
        templates = re.findall(r"(\.claude/skills/gx-setup/references/[\w.-]+\.json)", guard)
        self.assertTrue(templates)
        for template in templates:
            self.assertTrue((ROOT / template).is_file(), template)
        self.assertNotIn("../../config.json", guard)
        vcs = section(setup, "## Step 1:", "## Step 1.5:")
        self.assertIn("Step 3.0", vcs)
        self.assertIn("멈춘다", vcs)
        gx_setup = (ROOT / ".claude/skills/gx-setup/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", gx_setup)
        self.assertNotIn("config-setup-attempts", read("references/pipeline-state.md"))

    def test_f26_other_in_progress_run_is_not_overwritten(self):
        setup = read("phases/phase-setup.md")
        step5 = section(setup, "## Step 5:", "## Step 5.5:")
        git = step5[step5.index("**git인 경우:**"):]
        self.assertLess(git.index("이름 충돌"), git.index("git checkout -b"))
        self.assertIn("이름 충돌", step5[:step5.index("**git인 경우:**")], "svn slug도 같은 확인")
        step7 = section(setup, "## Step 7:", "**작업 계획 되돌림**")
        self.assertIn("run-id", step7)
        self.assertIn("덮어쓰지 않는다", step7)
        collision = section(read("phases/setup-branch.md"), "## 이름 충돌 확인", "## 2.3")
        for needle in ("다른 run-id", "status: in_progress", "git show", "git worktree list",
                       "다른 브랜치명", "--resume"):
            self.assertIn(needle, collision)

    def test_f17_unrelated_pending_question_is_answered_or_discarded(self):
        contract = read("references/interaction-contract.md")
        cleanup = section(contract, "### 이전 질문 정리", "\n---")
        for needle in ("codex-question.py", "discard", "--reason", "이전 질문에 답하기",
                       "폐기하고 새 작업", "exit 2", "discarded-question-", "응답 없이 폐기하지 않는다"):
            self.assertIn(needle, cleanup)
        resume = read("phases/setup-resume.md")
        self.assertIn("이전 질문 정리", resume[:resume.index("### `--resume` 플래그가 있는 경우")])
        self.assertIn("이전 질문 정리", section(read("phases/phase-setup.md"), "## Step 0:", "## Step 1:"))


class CompletionTests(unittest.TestCase):
    def test_f23_pr_step_passes_state_base_first(self):
        step = section(read("phases/phase-complete.md"), "### Step 2-2", "### Step 2-3")
        call = re.search(r'Skill\(skill: "oh-my-gx:gx-pull-request", args: "([^"]+)"\)', step)
        self.assertIsNotNone(call)
        self.assertEqual(call.group(1).split()[0], "${BASE_BRANCH}")
        self.assertIn("--background ${DEV_DIR}/pr-context.md", call.group(1))
        self.assertIn("--extra-section ${DEV_DIR}/pr-rulings.md", call.group(1))
        self.assertIn("`base`", step)

    def test_f28_commit_or_pr_only_request_changes_stop_at_first(self):
        routing = read("references/intent-routing.md")
        self.assertIn("종료점 변경", line_with(routing, "PHASE 매핑"))
        change = section(routing, "### 종료점 변경", "\n### ")
        order = [change.index(needle) for needle in ("decisions.md", "`stop-at`을", "reissue", "--change-source")]
        self.assertEqual(order, sorted(order))
        complete = read("phases/phase-complete.md")
        for start, end in (("## Step 1: Commit", "## Step 2: PR 생성"), ("## Step 2: PR 생성", "### Step 2-1")):
            with self.subTest(step=start):
                self.assertIn("종료점 변경", section(complete, start, end))

    def test_f33_same_run_decisions_are_not_asked_again(self):
        reference = section(read("phases/setup-work.md"), "### 3.0.5", "#### 진행할 작업 확인")
        self.assertNotIn("type은 AskUserQuestion으로 확인한다", reference)
        self.assertIn("진입 질문", reference)
        self.assertIn("다시 묻지 않", reference)
        step6 = section(read("phases/phase-setup.md"), "## Step 6:", "## Step 6.5:")
        self.assertIn("같은 실행", step6)
        self.assertIn("다시 묻지 않", step6)
        commit = section(read("phases/phase-complete.md"), "## Step 1: Commit", "## Step 2: PR 생성")
        self.assertIn('Skill(skill: "oh-my-gx:gx-commit", args: "--skip-context-sync")', commit)
        adaptation = read("references/harness-adaptation.md")
        self.assertIn("args", line_with(adaptation, "Skill(skill:"))

    def test_f43_entry_approval_is_not_ac_approval_and_plan_stop_resumes_at_review(self):
        reuse = line_with(read("phases/phase-requirements.md"), "**기존 계획 재사용 분기")
        self.assertIn("진입 승인", reuse)
        self.assertIn("AC 확정", reuse)
        restore = section(read("phases/setup-resume.md"), "### 0.05", "### 0.1")
        stop = line_with(restore, "계획 문서로 종료")
        self.assertIn("Step 1.2", stop)


class LegacyAndReferenceTests(unittest.TestCase):
    def test_f20_harness_gate_resumes_after_outside_setup(self):
        gate = section(read("phases/phase-implement.md"), "### 레이어별 하네스 게이트", "### 기준선 사전 실행")
        self.assertNotIn("gx-work로 별도 수행", gate)
        self.assertIn("--resume", gate)
        self.assertIn("test-harness-guide.md", gate)
        build = line_with(gate, '**"하네스 구축 후 재실행"**')
        self.assertNotIn("cancelled", build, "재개할 수 있게 진행 상태를 남긴다")
        frontend = section(read("references/frontend-testing.md"), "## §8.", "\n---")
        self.assertNotIn("gx-dev", frontend)
        self.assertNotIn("gx-work`로 별도 수행", frontend)
        self.assertIn("--resume", frontend)

    def test_f32_only_legacy_context_mentions_gx_dev(self):
        for path in sorted(TDD.rglob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "gx-dev" not in line:
                    continue
                with self.subTest(path=str(path.relative_to(TDD)), line=line[:50]):
                    self.assertRegex(line, r"제거|이력|다른 파이프라인|구버전")
                    self.assertNotRegex(line, r"gx-dev로|gx-dev를 사용|/gx-dev")
        self.assertNotIn("`/gx-dev", GOLDEN.read_text(encoding="utf-8"))

    def test_f36_legacy_state_points_to_new_branch_without_cycle(self):
        resume = read("phases/setup-resume.md")
        self.assertNotIn("기존 계획을 TDD 작업으로 전환해줘", resume)
        for heading in ("### `--resume` 플래그가 있는 경우", "### `--resume` 플래그가 없는 경우"):
            with self.subTest(heading=heading):
                block = section(resume, heading, "\n### ")
                legacy = line_with(block, "gx-tdd 파이프라인이 아닙니다")
                self.assertIn("새 브랜치", legacy)
                self.assertIn("워크트리", legacy)
        removed = section(read("references/intent-routing.md"), "### 제거된 무인 반복 경로", "### 의도 파싱")
        escape = line_with(removed, "구버전 기록에서 빠져나오기")
        self.assertIn("워크트리", escape)
        self.assertIn("새 브랜치", escape)

    def test_f41_stale_references_are_current(self):
        state = read("references/pipeline-state.md")
        self.assertNotIn("Step 0.4", state)
        self.assertIn("phase-setup의 Step 4에서", state)
        golden = GOLDEN.read_text(encoding="utf-8")
        s29 = line_with(golden, "| S29 |")
        self.assertIn("stop-at", s29)
        self.assertNotIn("커밋 + push", s29)
        self.assertNotIn("Step 2.3 stash pop", s29)


if __name__ == "__main__":
    unittest.main()
