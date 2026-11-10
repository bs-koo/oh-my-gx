"""gx-work 전수조사(2026-11-09) G4 범위의 배포 스킬·에이전트·사용자 문서 회귀 검사.

커밋·PR 스킬은 실제 git 동작으로, 나머지 지시문은 사용자에게 약속한 결과가
문서에 남아 있는지로 검사한다. 감사 항목 ID(F18 등)는 .dev/fix-gx-work-audit/audit-report.md다.
"""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
COMMIT = SKILLS / "gx-commit/SKILL.md"
PULL_REQUEST = SKILLS / "gx-pull-request/SKILL.md"
PROTECTED_CAPTURES = tuple(f".dev/{name}/decisions.md" for name in ("main", "master", "develop", "trunk"))


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def between(body: str, start: str, end: str | None = None) -> str:
    """start 이후부터 end 전까지를 돌려준다. 표식이 없으면 테스트가 실패하도록 예외를 낸다."""
    tail = body.split(start, 1)[1]
    return tail.split(end, 1)[0] if end else tail


def staged_after_reset(files: list[str], specs: list[str]) -> list[str]:
    """files를 모두 스테이징한 뒤 문서의 pathspec으로 reset하고 남은 스테이징 목록을 반환한다."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)

        def git(*args):
            return subprocess.run(
                ["git", "-c", "user.name=gx", "-c", "user.email=gx@example.com",
                 "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
                cwd=root, check=True, capture_output=True, text=True,
            )

        git("init", "-q")
        git("commit", "-q", "--allow-empty", "-m", "init")
        for relative in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        git("add", "-A")
        subprocess.run(["git", "reset", "-q", "--", *specs], cwd=root, check=False, capture_output=True)
        return sorted(git("diff", "--cached", "--name-only").stdout.split())


class CommitRunInputExclusionTests(unittest.TestCase):
    """F18·I10: 현재 실행 입력은 묻지 않고 커밋하고, 보호 브랜치 결정 기록은 묻지도 커밋하지도 않는다.

    실행 입력(handoff·intake·진입 결정)은 state의 포인터가 가리키므로 공유돼야 다른 PC·워크트리에서
    재개할 수 있다. 보호 브랜치 결정 기록은 작업 브랜치 생성 전 질문의 잔재라 이후 브랜치에 섞이면 안 된다.
    """

    def setUp(self):
        self.body = text(COMMIT)
        self.step_one = between(self.body, "1. `git status --short`", "\n2. ")

    def test_other_work_question_skips_current_run_and_protected_captures(self):
        for phrase in ("`.dev/<run-id>/`", "`.dev/{main,master,develop,trunk}/decisions.md`",
                       "묻지 않", "한 줄"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.step_one)

    def test_current_run_directory_is_committed_not_excluded(self):
        self.assertIn("커밋에 포함", self.step_one)
        self.assertIn("다른 PC", self.step_one)
        self.assertNotIn("둘 다 5단계에서 스테이징하지 않고", self.step_one)

    @unittest.skipUnless(shutil.which("git"), "git 필요")
    def test_documented_reset_unstages_only_protected_branch_captures(self):
        command = re.search(r"`(git reset -q -- [^`]+)`", self.body).group(1)
        specs = re.findall(r"'([^']+)'", command)
        staged = staged_after_reset(
            [*PROTECTED_CAPTURES, ".dev/f3a9-run/handoff.json", ".dev/f3a9-run/decisions.md",
             ".dev/feat-x/decisions.md", ".dev/feat-x/state.md", "src/App.java"], specs)
        self.assertEqual(staged, [".dev/f3a9-run/decisions.md", ".dev/f3a9-run/handoff.json",
                                  ".dev/feat-x/decisions.md", ".dev/feat-x/state.md", "src/App.java"])

    def test_run_directory_is_never_unstaged(self):
        self.assertIsNone(re.search(r"git reset -q -- '\.dev/<run-id>", self.body),
                          "현재 run 디렉토리를 unstage하면 재개에 필요한 인계 입력이 공유되지 않는다")

    def test_explicit_file_staging_includes_run_inputs_and_omits_protected_captures(self):
        step_five = between(self.body, "5. 스테이징:", "\n6. ")
        explicit = between(step_five, "제외 파일 있음", "\n")
        self.assertIn("현재 run 디렉토리는 지정", explicit)
        self.assertIn("보호 브랜치 결정 기록", explicit)


class CommitContextSyncSkipTests(unittest.TestCase):
    """F33(c)·I7: 파이프라인이 넘긴 --skip-context-sync이면 커밋 후 동기화 질문을 생략한다."""

    def setUp(self):
        self.body = text(COMMIT)

    def test_flag_is_an_argument_not_a_commit_message(self):
        hint = re.search(r"(?m)^argument-hint: (.+)$", self.body).group(1)
        self.assertIn("--skip-context-sync", hint)
        arguments = between(self.body, "Arguments:", "**하네스 적응**")
        self.assertIn("`--skip-context-sync`", arguments)
        self.assertIn("메시지로 쓰지 않는다", arguments)

    def test_sync_question_is_skipped_before_asking(self):
        sync = between(self.body, "## 커밋 후: context 동기화 체크", "**금지**")
        flag = sync.index("--skip-context-sync")
        self.assertLess(flag, sync.index("AskUserQuestion("))
        self.assertIn("건너뛴다", sync[flag:sync.index("AskUserQuestion(")])


class PullRequestBaseArgumentTests(unittest.TestCase):
    """F23·I8: 호출자가 베이스를 넘기면 다시 묻지 않는다."""

    def setUp(self):
        self.body = text(PULL_REQUEST)
        self.arguments = between(self.body, "Arguments:", "## 사전 확인")

    def test_explicit_base_is_parsed_after_flags_and_never_reasked(self):
        first_question = self.arguments.index("AskUserQuestion(")
        rule = self.arguments[:first_question]
        self.assertIn("`--background`·`--extra-section`", rule)
        self.assertIn("먼저 분리", rule)
        self.assertIn("자동 감지와 질문을 하지 않는다", rule)

    def test_unusable_explicit_base_stops_instead_of_asking(self):
        step_two = between(self.body, "**Step 2**", "## GH_HOST 감지")
        self.assertIn("질문으로 대체하지 않고", step_two)
        self.assertIn("git rev-parse --verify --quiet", step_two)


class PullRequestUncommittedOrderTests(unittest.TestCase):
    """F40: 미커밋 변경을 커밋 없음보다 먼저 보고 gx-commit 선행을 안내한다."""

    def setUp(self):
        self.step_two = between(text(PULL_REQUEST), "**Step 2**", "## GH_HOST 감지")

    def uncommitted_rule(self) -> str:
        return between(self.step_two, "- **미커밋 변경 선행 확인**", "\n- ")

    def test_uncommitted_changes_are_checked_before_the_no_commit_exit(self):
        self.assertLess(self.step_two.index("**미커밋 변경 선행 확인**"),
                        self.step_two.index("PR을 생성할 커밋이 없습니다"))
        rule = self.uncommitted_rule()
        self.assertIn("oh-my-gx:gx-commit", rule)
        self.assertIn("gx-commit이 성공한 뒤에만", rule)

    def test_files_gx_commit_never_stages_are_not_uncommitted_work(self):
        rule = self.uncommitted_rule()
        for item in ("ralph.lock", "iter-*.log", ".dev/architecture", "visual",
                     "{main,master,develop,trunk}/decisions.md"):
            with self.subTest(item=item):
                self.assertIn(item, rule)

    def test_run_inputs_count_as_uncommitted_work(self):
        # gx-commit은 현재 run 디렉토리를 커밋하므로, 그 변경은 PR 전에 커밋돼야 할 작업이다.
        ignored = between(self.uncommitted_rule(), "gx-commit이 커밋하지 않는 파일(", ")은")
        self.assertNotIn("<run-id>", ignored)


LEGACY_MARKERS = ("제거", "레거시", "기존 gx-dev", "pipeline: gx-dev", "구버전")
CURRENT_GUIDES = (
    COMMIT, PULL_REQUEST,
    *sorted((SKILLS / "gx-setup").rglob("*.md")),
    *sorted((SKILLS / "gx-cross-review").rglob("*.md")),
    *sorted((SKILLS / "gx-visualize").rglob("*.md")),
    *sorted((ROOT / "agents").glob("*.md")),
    ROOT / ".claude/rules/skill-routing.md",
    ROOT / "README.md", ROOT / "index.html",
    *(ROOT / "docs" / name for name in (
        "guide.md", "codex-guide.md", "onboarding-guide.md", "prompt-examples.md", "tdd-guide.md",
        "test-harness-guide.md", "gx-visualize-guide.md", "design-decisions.md")),
)


class RemovedDevPipelineGuidanceTests(unittest.TestCase):
    """F32: 현행 안내는 제거된 gx-dev를 쓰라고 하지 않는다. 레거시 처리 문맥만 남는다."""

    def test_every_gx_dev_mention_is_legacy_context(self):
        for path in CURRENT_GUIDES:
            for number, line in enumerate(text(path).splitlines(), 1):
                if "gx-dev" in line:
                    with self.subTest(path=path.relative_to(ROOT).as_posix(), line=number):
                        self.assertTrue(any(marker in line for marker in LEGACY_MARKERS), line.strip())

    def test_agent_descriptions_name_their_current_callers(self):
        def description(name):
            return between(text(ROOT / "agents" / f"{name}.md"), "description: |", "<example>")

        self.assertIn("oh-my-gx:gx-cross-review", description("qa-manager"))
        self.assertIn("oh-my-gx:gx-tdd", description("researcher"))
        coder = description("coder")
        self.assertIn("레거시", coder)
        self.assertIn("호출하지 않는다", coder)


class UserDocumentBehaviourTests(unittest.TestCase):
    """F01·F19·F28·F34: 사용자 문서가 실제 스킬 동작과 같은 결과를 약속한다."""

    def test_routing_documents_open_ended_work_ids(self):
        routing = text(ROOT / ".claude/rules/skill-routing.md")
        self.assertIn("W01 시작해줘", routing)
        self.assertIn("두 자리 이상", routing)
        self.assertIn("W100", routing)

    def test_readme_keeps_work_flag_on_direct_tdd_calls(self):
        """gx-work는 자연어 작업 ID를 받고 `--work`는 gx-tdd 직접 호출의 플래그다."""
        readme = text(ROOT / "README.md")
        flag_lines = [line for line in readme.splitlines() if "--work" in line]
        self.assertTrue(flag_lines)
        for line in flag_lines:
            with self.subTest(line=line):
                self.assertIn("gx-tdd", line)
                self.assertIn("두 자리 이상", line)

    def test_docs_do_not_fix_work_ids_to_two_digits(self):
        for path in (ROOT / "README.md", ROOT / "index.html", ROOT / ".claude/rules/skill-routing.md",
                     *(ROOT / "docs").glob("*.md")):
            for line in text(path).splitlines():
                if "두 자리" in line:
                    with self.subTest(path=path.name):
                        self.assertIn("두 자리 이상", line)

    def test_setup_quickstart_states_verify_as_default_endpoint(self):
        setup = text(SKILLS / "gx-setup/SKILL.md")
        quickstart = between(setup, "### 완료: 퀵스타트")
        work_lines = [line for line in quickstart.splitlines() if line.startswith("/gx-work")]
        self.assertTrue(work_lines)
        for line in work_lines:
            with self.subTest(line=line):
                self.assertNotIn("PRD~PR", line)
                self.assertIn("verify", line)

    def test_onboarding_explains_removed_ralph_exit(self):
        onboarding = text(ROOT / "docs/onboarding-guide.md")
        self.assertIn("--ralph", onboarding)
        self.assertIn("새 브랜치", onboarding)
        self.assertIn("워크트리", onboarding)

    def test_pages_do_not_promise_removed_unattended_runs(self):
        self.assertNotIn("무인 실행", text(ROOT / "index.html"))

    def test_plan_only_results_are_described_as_conversation_output(self):
        index = text(ROOT / "index.html")
        faq = between(index, "계획만 요청하거나 기존 계획을 가져올 수 있나요?", "</details>")
        guide = between(text(ROOT / "docs/guide.md"), "## 요청 예시", "## 결과에 맞춰 다음 단계 선택")
        codex = between(text(ROOT / "docs/codex-guide.md"), "계획만 필요하거나", "```text\noh-my-gx:gx-cross-review")
        for name, body in (("index-faq", faq), ("guide", guide), ("codex-guide", codex)):
            with self.subTest(document=name):
                self.assertIn("대화로", body)
                self.assertIn("PRD·설계", body)
                self.assertIn("읽기 전용", body)

    def test_direct_tdd_example_names_an_explicit_tdd_request(self):
        """F02: gx-tdd 직접 호출 예시는 TDD를 명시한 요청이어야 한다."""
        rows = re.findall(r'<span class="usage-say">"([^"]+)"</span><span class="usage-arrow">→</span>'
                          r'<span class="usage-skill">gx-tdd</span>', text(ROOT / "index.html"))
        self.assertEqual(len(rows), 1)
        self.assertIn("TDD", rows[0])
        self.assertIn("테스트 먼저", rows[0])

    def test_tdd_guide_entry_table_covers_plan_only_and_endpoint_change(self):
        table = between(text(ROOT / "docs/tdd-guide.md"), "### 6.1 공통 진입점과 직접 실행", "호출 방법:")
        plan_row = next(line for line in table.splitlines() if "계획만 요청" in line)
        self.assertIn("대화로", plan_row)
        self.assertIn("읽기 전용", plan_row)
        change_row = next(line for line in table.splitlines() if "종료점 변경" in line)
        self.assertIn("/gx-work", change_row)
        direct_row = next(line for line in table.splitlines() if line.rstrip().endswith("`/gx-tdd` |"))
        self.assertIn("TDD를 명시", direct_row)

    def test_guide_explains_commit_or_pr_after_a_verify_run(self):
        guide = between(text(ROOT / "docs/guide.md"), "## 요청 예시", "## 결과에 맞춰 다음 단계 선택")
        self.assertIn("종료점 변경", guide)


if __name__ == "__main__":
    unittest.main()
