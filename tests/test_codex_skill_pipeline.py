import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / ".claude/skills/gx-dev/SKILL.md"
TDD = ROOT / ".claude/skills/gx-tdd/SKILL.md"
SETUPS = (
    ROOT / ".claude/skills/gx-dev/phases/phase-setup.md",
    ROOT / ".claude/skills/gx-tdd/phases/phase-setup.md",
)
TDD_RESUME = ROOT / ".claude/skills/gx-tdd/phases/setup-resume.md"


def skill_bundle(directory: Path) -> str:
    ordered = (
        directory / "SKILL.md",
        directory / "references/intent-routing.md",
        directory / "references/pipeline-state.md",
        directory / "references/interaction-contract.md",
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in ordered)


# Executable approximation of the prose in phase-setup Step -1. Mock VCS commands
# make unavailable tools, working copies, and metadata errors deterministic.
ROOT_SELECTION_PROBE = r'''
PATH=""
if test "$MOCK_GIT" != missing; then
  git() {
    if test "$1" = init; then MOCK_GIT=wc; MOCK_GIT_ROOT=$(pwd -P); return 0; fi
    case "$MOCK_GIT" in
      wc) printf '%s\n' "$MOCK_GIT_ROOT" ;;
      no_wc) printf '%s\n' 'fatal: not a git repository' >&2; return 1 ;;
      error) printf '%s\n' 'fatal: corrupt git metadata' >&2; return 1 ;;
    esac
  }
fi
if test "$MOCK_SVN" != missing; then
  svn() {
    case "$MOCK_SVN" in
      wc) printf '%s\n' "$MOCK_SVN_ROOT" ;;
      no_wc) printf '%s\n' 'E155007: not a working copy' >&2; return 1 ;;
      error) printf '%s\n' 'E200009: corrupt svn metadata' >&2; return 1 ;;
    esac
  }
fi
has_marker() {
  local p="$PWD"
  while :; do
    if test "$1" = .git && test -e "$p/.git"; then return 0; fi
    if test "$1" = .svn && test -d "$p/.svn"; then return 0; fi
    if test "$p" = /; then break; fi
    p="${p%/*}"
    if test -z "$p"; then p=/; fi
  done
  return 1
}
resolve_root() {
  local answer status
  if command -v git >/dev/null; then
    answer=$(git rev-parse --show-toplevel 2>&1); status=$?
    if test "$status" -eq 0; then printf '%s\n' "$answer"; return 0; fi
    if has_marker .git || test "$answer" != 'fatal: not a git repository'; then
      printf 'git root diagnostic: %s\n' "$answer" >&2; return 1
    fi
  elif has_marker .git; then
    printf '%s\n' 'git command missing for .git marker' >&2; return 1
  fi
  if command -v svn >/dev/null; then
    answer=$(svn info --show-item wc-root 2>&1); status=$?
    if test "$status" -eq 0; then printf '%s\n' "$answer"; return 0; fi
    if has_marker .svn || test "$answer" != 'E155007: not a working copy'; then
      printf 'svn root diagnostic: %s\n' "$answer" >&2; return 1
    fi
  elif has_marker .svn; then
    printf '%s\n' 'svn command missing for .svn marker' >&2; return 1
  fi
  pwd -P
}
project_root=$(resolve_root) || exit 1
if test "$MOCK_INIT" = yes; then
  git init || exit 1
  project_root=$(resolve_root) || exit 1
fi
printf '%s\n' "$project_root"
'''


# Executable approximation of the SVN URL outcome gate documented in both
# setup phases. This checks command failure separately from a successful URL
# that cannot identify a repository; it does not execute a skill or model.
SVN_URL_OUTCOME_PROBE = r'''
svn() {
  test "$1 $2 $3" = 'info --show-item url' || return 9
  if test "$MOCK_SVN_STATUS" = failure; then
    printf '%s\n' 'E200009: SVN metadata error' >&2
    return 1
  fi
  printf '%s\n' "$MOCK_SVN_URL"
}
url=$(svn info --show-item url 2>&1)
status=$?
if test "$status" -ne 0; then
  printf 'SVN URL diagnostic: %s\n' "$url" >&2
  exit "$status"
fi
case "$url" in
  ''|https://*/|http://*/|svn://*/)
    printf '%s\n' 'SVN URL warning: ambiguous output' >&2
    printf '%s\n' 'project'
    ;;
  *) printf '%s\n' 'repository' ;;
esac
'''


class PipelineBootstrapContractTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        if path in (DEV, TDD):
            return skill_bundle(path.parent)
        return path.read_text(encoding="utf-8")

    def test_partial_phase_lists_include_setup(self):
        for path in (DEV, TDD):
            text = self.read(path)
            loop = text[
                text.index("### Phase 실행 루프") : text.index("### Phase 파일 경로")
            ]
            self.assertIn('elif --phase == "requirements":', loop, path)
            self.assertIn("PHASES = [setup, requirements]", loop, path)
            self.assertIn('elif --phase == "design":', loop, path)
            self.assertIn("PHASES = [setup, design]", loop, path)
            remaining = "PHASES = [해당 phase만]"
            self.assertIn(remaining, loop, path)
            self.assertLess(loop.index("PHASES = [setup, design]"), loop.index(remaining))

    def test_phase_selection_matches_loop(self):
        for path in (DEV, TDD):
            text = self.read(path)
            selection = text[text.index("## Phase 선택") :]
            self.assertIn(
                "requirements`: `[setup, requirements]`를 실행하여 작업환경과 "
                "도메인 컨텍스트를 확정한 뒤 PRD를 작성한다.",
                selection,
                path,
            )
            self.assertIn("design`: `[setup, design]`", selection, path)

    def test_design_gate_precedes_phase_file_execution(self):
        for path in (DEV, TDD):
            text = self.read(path)
            loop_start = text.index("### Phase 실행 루프")
            loop_end = text.index("### Phase 파일 경로", loop_start)
            loop = text[loop_start:loop_end]
            design_list = "PHASES = [setup, design]"
            design_gate = (
                'if phase == "design" and not exists("${DEV_DIR}/prd.md"):\n'
                "        → phase-requirements부터 실행"
            )
            phase_execution = '# 2b. Phase 파일 Read (필수)\n    Read("phases/phase-{phase}.md")'

            self.assertIn(design_gate, loop, path)
            self.assertIn(phase_execution, loop, path)
            self.assertLess(loop.index(design_list), loop.index(design_gate), path)
            self.assertLess(loop.index(design_gate), loop.index(phase_execution), path)

    def test_setup_resolves_absolute_project_root_before_state_scan(self):
        for path in SETUPS:
            text = self.read(path)
            root_step = text.index("## Step -1: 프로젝트 루트 결정")
            state_step = text.index("## Step 0: 진행 중 작업 감지")
            self.assertLess(root_step, state_step, path)

            section = text[root_step:state_step]
            git_root = "git rev-parse --show-toplevel"
            svn_root = "svn info --show-item wc-root"
            fallback = "현재 디렉토리의 절대경로"
            for phrase in (git_root, svn_root, fallback):
                self.assertIn(phrase, section, path)
            self.assertLess(section.index(git_root), section.index(svn_root), path)
            self.assertLess(section.index(svn_root), section.index(fallback), path)
            self.assertIn(
                "`git init`을 실행하면 `git rev-parse --show-toplevel`로 다시 계산",
                section,
                path,
            )
            self.assertIn(
                "`.claude/config.json`, `.dev/`, `context/`, `references/`와 "
                "모든 Git·SVN·빌드·테스트 명령은 `PROJECT_ROOT` 기준",
                section,
                path,
            )

            state_section = text[state_step : text.index("## Step 1:", state_step)]
            vcs_section = text[
                text.index("## Step 1:", state_step) : text.index("## Step 1.5:")
            ]
            self.assertIn("`${PROJECT_ROOT}/.dev/*/state.md`", state_section, path)
            self.assertIn("`${PROJECT_ROOT}/.claude/config.json`", vcs_section, path)

    def test_svn_repository_identity_is_shared(self):
        svn_rules = []
        for path in SETUPS:
            text = self.read(path)
            rule = next(
                line for line in text.splitlines() if line.startswith("   - **svn**:")
            )
            self.assertNotIn("svn info --show-item repos-root-url", rule, path)
            for phrase in (
                "svn info --show-item url",
                "trunk",
                "branches/<name>",
                "tags/<name>",
                "REPOSITORY_ID",
                "basename(PROJECT_ROOT)",
            ):
                self.assertIn(phrase, rule, path)
            self.assertIn("끝에서", rule, path)
            self.assertIn("마지막", rule, path)
            self.assertIn("비거나 모호하면", rule, path)
            svn_rules.append(rule)
        self.assertEqual(*svn_rules)

    def test_svn_url_failure_stops_before_ambiguous_fallback(self):
        for path in SETUPS:
            rule = next(
                line for line in self.read(path).splitlines()
                if line.startswith("   - **svn**:")
            )
            for phrase in (
                "종료 코드 != 0",
                "진단",
                "중단",
                "성공했지만",
                "경고",
                "basename(PROJECT_ROOT)",
            ):
                self.assertIn(phrase, rule, path)
            self.assertLess(rule.index("종료 코드 != 0"), rule.index("성공했지만"))

        bash = shutil.which("bash") or "bash"
        cases = (
            ("failure", "", 1, "", "SVN URL diagnostic"),
            ("success", "https://svn.example.invalid/", 0, "project", "SVN URL warning"),
        )
        for status, url, exit_code, output, message in cases:
            with self.subTest(status=status):
                env = os.environ.copy()
                env.update(MOCK_SVN_STATUS=status, MOCK_SVN_URL=url)
                result = subprocess.run(
                    [bash, "-c", SVN_URL_OUTCOME_PROBE],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(result.stdout.strip(), output)
                self.assertIn(message, result.stderr)

    def test_skill_contract_uses_root_for_full_and_phase_only_runs(self):
        legacy_forms = (
            "`PROJECT_ROOT`: 항상 `./`",
            "| `PROJECT_ROOT` | `./` |",
            "`PROJECT_ROOT` = 현재 디렉토리",
            "PROJECT_ROOT`가 기본값 `./`",
            "기본값 `./`이면 **bare 명령**",
        )
        for path in (DEV, TDD):
            text = self.read(path)
            for phrase in legacy_forms:
                self.assertNotIn(phrase, text, path)
            self.assertIn(
                "`PROJECT_ROOT`: phase-setup Step -1이 Git `--show-toplevel` > SVN "
                "`wc-root` > 현재 디렉토리 절대경로 순으로 결정한 값.",
                text,
                path,
            )

            phase_only = text[text.index("> **환경 감지**") :]
            root_rule = (
                "`PROJECT_ROOT` = phase-setup과 같은 우선순위의 절대경로. 이후 config, "
                "`.dev`, context, VCS·빌드·테스트 명령은 이 경로를 기준으로 수행한다."
            )
            self.assertIn(root_rule, phase_only, path)
            self.assertLess(
                phase_only.index(root_rule),
                phase_only.index("git rev-parse --is-inside-work-tree"),
                path,
            )

    def test_tdd_phase_only_dev_dir_joins_once_to_project_root(self):
        text = self.read(TDD)
        phase_only = text[text.index("> **환경 감지**") :]
        rule = next(line for line in phase_only.splitlines() if line.startswith("> 4."))
        consumers = (
            ROOT / ".claude/skills/gx-tdd/phases/phase-implement.md",
            ROOT / ".claude/skills/gx-tdd/phases/phase-review.md",
        )
        for path in consumers:
            self.assertIn("${PROJECT_ROOT}/${DEV_DIR}", self.read(path), path)

        for vcs, value, expected in (
            ("git", "feat/login", ".dev/feat-login/"),
            ("svn", "feature", ".dev/feature/"),
            ("svn fallback", "", ".dev/trunk/"),
        ):
            with self.subTest(vcs=vcs):
                if vcs == "git":
                    template = rule.split("`DEV_DIR = ", 1)[1].split("`", 1)[0]
                    dev_dir = template.replace("{branch-slug}", value.replace("/", "-"))
                else:
                    svn_rule = rule.split("**svn**:", 1)[1]
                    if value:
                        template = svn_rule.split("`DEV_DIR = ", 1)[1].split("`", 1)[0]
                        dev_dir = template.replace("{slug}", value)
                    else:
                        dev_dir = svn_rule.split("폴백", 1)[0].split("`")[-2]
                self.assertEqual(dev_dir, expected)
                with tempfile.TemporaryDirectory(prefix="pipeline phase root ") as root:
                    state = Path(root) / expected / "state.md"
                    state.parent.mkdir(parents=True)
                    state.write_text("pipeline: gx-tdd\n", encoding="utf-8")
                    result = subprocess.run(
                        [shutil.which("bash") or "bash", "-c",
                         'test -f "$1/$2/state.md"', "probe", root, dev_dir],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_tdd_diff_redirection_handles_spaced_dev_dir(self):
        text = self.read(TDD.parent / "references/pipeline-state.md")
        section = text[text.index("#### 수집 절차") :]
        commands = [
            line.strip() for line in section.splitlines()
            if "${DEV_DIR}/diff.txt" in line and line.strip().startswith(("git ", "echo "))
        ]
        self.assertTrue(commands)
        with tempfile.TemporaryDirectory(prefix="pipeline diff root ") as root:
            diff_dir = Path(root) / ".dev" / "feature with space"
            diff_dir.mkdir(parents=True)
            env = os.environ.copy()
            env["DEV_DIR"] = ".dev/feature with space"
            for command in commands:
                result = subprocess.run(
                    [shutil.which("bash") or "bash", "-c",
                     "git() { printf 'changed\\n'; }; " + command],
                    cwd=root, env=env, capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, (command, result.stderr))
            self.assertTrue((diff_dir / "diff.txt").is_file())

    def test_setup_does_not_reassign_project_root_to_dot(self):
        for path in SETUPS:
            text = self.read(path)
            self.assertNotIn("`PROJECT_ROOT = ./`", text, path)
            self.assertNotIn("`PROJECT_ROOT` = `./`", text, path)
            self.assertIn(
                "`PROJECT_ROOT`는 Step -1에서 결정한 절대경로를 유지한다.",
                text,
                path,
            )

    def test_tdd_resume_keeps_root_resolved_before_state_restore(self):
        path = TDD_RESUME
        text = self.read(path)
        resume = text[text.index("**이어서 진행 시:**") :]
        self.assertNotIn(
            "state.md에서 VCS_TYPE, GIT_PREFIX, PROJECT_ROOT,", resume, path
        )
        self.assertIn("PROJECT_ROOT는 Step -1의 절대경로를 유지한다", resume, path)

    def test_setup_distinguishes_project_paths_from_bundled_references(self):
        for path in SETUPS:
            text = self.read(path)
            root_step = text[text.index("## Step -1:") : text.index("## Step 0:")]
            self.assertIn("프로젝트 파일의 상대경로", root_step, path)
            self.assertIn("번들 스킬·phase 파일", root_step, path)
            self.assertIn("지시 파일 위치 기준", root_step, path)
            self.assertIn("Read(\"", text, path)
            self.assertNotIn(
                "상대경로 파일 도구 호출도 이 경로 아래에서 해석한다",
                root_step,
                path,
            )

    def test_root_fallback_only_after_not_working_copy_diagnostics(self):
        for path in SETUPS:
            text = self.read(path)
            root_step = text[text.index("## Step -1:") : text.index("## Step 0:")]
            self.assertIn("not a git repository", root_step, path)
            self.assertIn("E155007", root_step, path)
            self.assertIn("메타데이터 오류 등 다른 실패", root_step, path)
            self.assertIn("진단을 표시하고 중단", root_step, path)
            self.assertNotIn("둘 다 실패하면", root_step, path)

    def test_tdd_config_guard_quotes_spaced_project_root(self):
        path = SETUPS[1]
        text = self.read(path)
        guard_start = text.index("### 3.0 config.json 가드")
        guard = text[guard_start : text.index("**Iron Law", guard_start)]
        command = 'test -f "${PROJECT_ROOT}/.claude/config.json"'
        self.assertIn(command, guard, path)

        with tempfile.TemporaryDirectory(prefix="pipeline root ") as temp_root:
            config = Path(temp_root) / ".claude" / "config.json"
            config.parent.mkdir()
            config.write_text("{}", encoding="utf-8")
            root = Path(temp_root).resolve().as_posix()
            result = subprocess.run(
                [
                    shutil.which("bash") or "bash",
                    "-c",
                    command.replace("${PROJECT_ROOT}", root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_vcs_tools_skip_only_when_no_working_copy_markers(self):
        for path in SETUPS:
            text = self.read(path)
            root_step = text[text.index("## Step -1:") : text.index("## Step 0:")]
            for phrase in (
                "command -v git",
                "command -v svn",
                "현재 디렉토리와 상위 디렉토리",
                "`.git` 파일·디렉토리",
                "`.svn` 디렉토리",
                "마커가 없으면 없는 명령을 건너뛴다",
                "마커가 있는데 명령이 없거나 도구가 작업 복사본 아님을 보고하면 진단을 표시하고 중단",
            ):
                self.assertIn(phrase, root_step, path)

        probe = (
            'PATH=""; if command -v git >/dev/null || '
            'command -v svn >/dev/null; then exit 9; fi; '
            'p="$PWD"; while :; do '
            'if test -e "$p/.git"; then echo needs-git; exit; fi; '
            'if test -d "$p/.svn"; then echo needs-svn; exit; fi; '
            'parent="${p%/*}"; if test "$parent" = "$p"; then break; fi; '
            'p="$parent"; done; echo fresh'
        )
        bash = shutil.which("bash") or "bash"
        with tempfile.TemporaryDirectory(prefix="pipeline probe ") as temp_root:
            base = Path(temp_root)
            nested = base / "nested"
            nested.mkdir()
            cases = (
                (None, None, "fresh"),
                (".git", "directory", "needs-git"),
                (".git", "file", "needs-git"),
                (".svn", "directory", "needs-svn"),
            )
            for marker, kind, expected in cases:
                if marker:
                    if kind == "file":
                        (base / marker).write_text("gitdir: elsewhere\n", encoding="utf-8")
                    else:
                        (base / marker).mkdir()
                result = subprocess.run(
                    [bash, "-c", probe],
                    cwd=nested,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
                if marker:
                    if kind == "file":
                        (base / marker).unlink()
                    else:
                        (base / marker).rmdir()

    def test_fresh_git_init_recomputes_absolute_root(self):
        for path in SETUPS:
            text = self.read(path)
            root_step = text[text.index("## Step -1:") : text.index("## Step 0:")]
            self.assertIn(
                "`git init`을 실행하면 `git rev-parse --show-toplevel`로 다시 계산",
                root_step,
                path,
            )

        git = shutil.which("git") or "git"
        with tempfile.TemporaryDirectory(prefix="pipeline git init ") as temp_root:
            root = Path(temp_root).resolve()
            nested = root / "nested"
            nested.mkdir()
            before = subprocess.run(
                [git, "-C", str(nested), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(before.returncode, 0)
            created = subprocess.run(
                [git, "-C", str(root), "init", "-q"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            after = subprocess.run(
                [git, "-C", str(nested), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertEqual(Path(after.stdout.strip()).resolve(), root)

    def test_missing_git_is_reported_before_git_init_prompt(self):
        for path in SETUPS:
            text = self.read(path)
            vcs_step = text[text.index("## Step 1:") : text.index("## Step 1.5:")]
            guard = "`command -v git` 실패면 Git 명령 부재를 안내하고 중단한다."
            self.assertIn(guard, vcs_step, path)
            self.assertLess(vcs_step.index(guard), vcs_step.index("git init"), path)

    def test_skipped_tool_counts_as_confirmed_no_working_copy(self):
        for path in SETUPS:
            text = self.read(path)
            root_step = text[text.index("## Step -1:") : text.index("## Step 0:")]
            self.assertIn(
                "명령 부재·마커 없음은 해당 VCS의 작업 복사본 부재로 확정한다",
                root_step,
                path,
            )
            fallback = root_step[root_step.index("3. ") :]
            self.assertIn("Git·SVN 각각", fallback, path)
            self.assertIn("명령 부재·마커 없음", fallback, path)
            self.assertIn("not a working copy", fallback, path)

    def test_root_selection_probe_covers_missing_tools_and_metadata_errors(self):
        bash = shutil.which("bash") or "bash"
        with tempfile.TemporaryDirectory(prefix="pipeline contract ") as temp_root:
            base = Path(temp_root)
            nested = base / "nested"
            nested.mkdir()
            base_root = subprocess.check_output(
                [bash, "-c", "pwd -P"], cwd=base, text=True
            ).strip()
            nested_root = subprocess.check_output(
                [bash, "-c", "pwd -P"], cwd=nested, text=True
            ).strip()

            cases = (
                # name, git, svn, marker, init, expected root or diagnostic
                ("fresh without tools", "missing", "missing", None, "no", nested_root),
                ("no svn before git init", "no_wc", "missing", None, "yes", nested_root),
                ("svn working copy without git", "missing", "wc", ".svn", "no", base_root),
                ("git wins over svn", "wc", "wc", None, "no", base_root),
                (
                    "missing git for marker", "missing", "missing", ".git", "no",
                    "git command missing",
                ),
                (
                    "git tool reports no wc for marker", "no_wc", "missing", ".git", "no",
                    "git root diagnostic",
                ),
                (
                    "missing svn for marker", "no_wc", "missing", ".svn", "no",
                    "svn command missing",
                ),
                (
                    "svn tool reports no wc for marker", "no_wc", "no_wc", ".svn", "no",
                    "svn root diagnostic",
                ),
                (
                    "git metadata error", "error", "missing", None, "no",
                    "git root diagnostic",
                ),
                (
                    "svn metadata error", "no_wc", "error", None, "no",
                    "svn root diagnostic",
                ),
            )
            for name, git_mode, svn_mode, marker, init, expected in cases:
                with self.subTest(name=name):
                    if marker:
                        (base / marker).mkdir()
                    env = os.environ.copy()
                    env.update(
                        MOCK_GIT=git_mode,
                        MOCK_SVN=svn_mode,
                        MOCK_GIT_ROOT=base_root,
                        MOCK_SVN_ROOT=(
                            nested_root if name == "git wins over svn" else base_root
                        ),
                        MOCK_INIT=init,
                    )
                    result = subprocess.run(
                        [bash, "-c", ROOT_SELECTION_PROBE],
                        cwd=nested,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if "diagnostic" in expected or "command missing" in expected:
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertEqual(result.stdout, "")
                        self.assertIn(expected, result.stderr)
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.strip(), expected)
                        self.assertTrue(result.stdout.strip().startswith("/"))
                    if marker:
                        (base / marker).rmdir()

    def test_git_init_recomputes_physical_root_when_pwd_is_an_alias(self):
        bash = shutil.which("bash") or "bash"
        with tempfile.TemporaryDirectory(prefix="pipeline alias ") as temp_root:
            nested = Path(temp_root) / "nested"
            nested.mkdir()
            physical_root = subprocess.check_output(
                [bash, "-c", "pwd -P"], cwd=nested, text=True
            ).strip()
            env = os.environ.copy()
            env.update(
                MOCK_GIT="no_wc",
                MOCK_SVN="missing",
                MOCK_GIT_ROOT="",
                MOCK_SVN_ROOT="",
                MOCK_INIT="yes",
            )
            result = subprocess.run(
                [bash, "-c", "PWD=/synthetic-alias\n" + ROOT_SELECTION_PROBE],
                cwd=nested,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), physical_root)


# Executable approximation of the acceptance rule in phase-implement Step 0.5
# "기준선 사전 실행". It checks the decision table, not a model run.
BASELINE_ACCEPT_PROBE = r'''
accept() {
  local done="$1" start="$2" current="$3" dir="$4"; shift 4
  test -f "$done" || { echo sync; return; }
  test "$(head -n 1 "$done")" = "start=$start" || { echo sync; return; }
  test "$(tail -n 1 "$done")" = DONE || { echo sync; return; }
  local end; end=$(sed -n 's/^fingerprint-end=//p' "$done")
  test -n "$end" || { echo sync; return; }
  test "${start#*:}" = "${end#*:}" && test "${start#*:}" = "${current#*:}" || { echo sync; return; }
  local t k
  for t in "$@"; do
    for k in test build; do
      test "$(grep -c "^$t $k rc=[0-9][0-9]*$" "$done")" = 1 || { echo sync; return; }
      test -f "$dir/baseline-$t-$k.log" || { echo sync; return; }
    done
  done
  echo accept
}
accept "$DONE_FILE" "$START" "$CURRENT" "$DIR" $TYPES
'''

TDD_PHASES = ROOT / ".claude/skills/gx-tdd/phases"
IMPLEMENTER = ROOT / "agents/implementer.md"


def section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    stop = text.index(end, begin + len(start))
    return text[begin:stop]


class TestRunBudgetContractTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (TDD_PHASES / name).read_text(encoding="utf-8")

    def test_review_gate_runs_pipeline_tests_not_full_suite(self):
        text = self.read("phase-review.md")
        gate = section(text, "## Step 0: Mechanical Gate", "## Step 1:")
        for needle in (
            "Step 0 테스트 집합",
            "무결성 선확인",
            "사용자 변경으로 인정",
            "누적 focused",
            "`detect` 파일이 있는 디렉토리",
            "테스트 파일이 없는 타입은 빌드만",
            "전체 폴백",
            "통틀어 `test-file` 기록이 0건",
            "`focusedTest` 없음",
            "명령 자체 오류",
            "-x test testClasses",
            "기존 스위트 전체 회귀는 phase-complete의 verify 게이트가 1회 맡는다",
            "SSOT는 config",
            "복수 타입",
        ):
            self.assertIn(needle, gate)
        handling = section(text, "### Step 4.4", "## state.md 추적")
        self.assertNotIn("전체 테스트 1회 직접 실행", handling)
        self.assertGreaterEqual(handling.count("Step 0 테스트 집합"), 3)
        self.assertNotIn("정리 후 전체 테스트 GREEN", text)

    def test_task_focused_scope_is_task_only(self):
        text = self.read("phase-implement.md")
        implementer = IMPLEMENTER.read_text(encoding="utf-8")
        assembly = section(text, "**focused 테스트 명령 조립**:", "**명령 오류 가드**")
        self.assertIn("이 태스크의 `test-file` 기록 파일만", assembly)
        self.assertNotIn("이전 태스크들이 만든 신규 테스트 파일 전부", text)
        self.assertGreaterEqual(text.count("와일드카드"), 3)
        for needle in ("와일드카드", "모듈 묶음", "verify 회귀 수리", "완료 verify"):
            self.assertIn(needle, implementer)
        self.assertNotIn("전체는 경계에서", implementer)
        self.assertIn("같은 태스크의 직전 `test-count`", text)
        self.assertNotIn("직전 태스크의 같은 방식 값", text)
        subs = ROOT / "tests/fixtures/behavior/b2/subs.json"
        for key in json.loads(subs.read_text(encoding="utf-8")):
            self.assertIn(key, text, key)

    def test_boundary_regression_only_without_following_verify(self):
        text = self.read("phase-implement.md")
        step = section(text, "## Step 3.5:", "## Step 4:")
        self.assertIn("## Step 3.5: 경계 회귀 (--phase implement 단독 전용)", step)
        self.assertIn("complete(verify)가 실행되지 않는 경로", step)
        core = section(text, "## 핵심 모드 분기 (core)", "## Step 0: 문서 로드")
        self.assertIn("Step 3.5(경계 회귀)는 건너뛴다", core)
        self.assertNotIn("핵심 모드·`--phase implement` 단독: Step 3.5", text)

    def test_baseline_prelaunch_contract(self):
        req = self.read("phase-requirements.md")
        trigger = section(req, "## 기준선 사전 실행 (진입 직후)", "## 핵심 모드 분기 (core)")
        self.assertIn("phase-implement.md", trigger)
        self.assertIn("Codex와 svn은 시작하지 않고", trigger)
        self.assertIn("phase 목록에 implement가 있을 때만", trigger)
        impl = self.read("phase-implement.md")
        pre = section(impl, "### 기준선 사전 실행 (Claude Code·git 전용)", "## Step 0.7")
        for needle in (
            "phase 목록에 implement가 있을 때만",
            "`--phase requirements`",
            "run_in_background: true",
            "`baseline-fingerprint`",
            "${DEV_DIR}/baseline.done",
            "${DEV_DIR}/baseline-{타입}-{test|build}.log",
            "`{타입} {test|build} rc={N}`",
            "`fingerprint-end={값}`",
            "`start={baseline-fingerprint}`",
            "실행 완료 표식이지 성공이 아니다",
            "동기 실행",
            "판정 1(기준 GREEN 실패)",
            "`&&`·`set -e`로 잇지 않는다",
            "작업을 중지하고 동기 실행",
            "포그라운드 sleep으로 기다리지 않는다",
        ):
            self.assertIn(needle, pre)
        self.assertIn("```bash", pre)
        accept = section(pre, "**결과 수용**", "| 상태 | 처리 |")
        for needle in (
            "첫 줄이 `start={값}`",
            "마지막 줄이 `DONE`",
            "각 1개",
            "트리 성분",
            "HEAD 성분은 비교하지 않는다",
            "로그 파일 존재",
        ):
            self.assertIn(needle, accept)
        self.assertIn("기준선 사전 실행", section(impl, "## Step 0.5", "### 레이어별 하네스 게이트"))
        refs = TDD_PHASES.parent / "references"
        self.assertIn("run_in_background", (refs / "harness-adaptation.md").read_text(encoding="utf-8"))
        self.assertIn("baseline-fingerprint:", (refs / "pipeline-state.md").read_text(encoding="utf-8"))

    def test_baseline_acceptance_probe(self):
        bash = shutil.which("bash") or "bash"
        start = "1111111:aaaaaaaaaaaa"
        good = [f"start={start}", "java-spring test rc=0", "java-spring build rc=0",
                "node test rc=0", "node build rc=0",
                f"fingerprint-end={start}", "DONE"]
        cases = (
            ("complete", good, start, True, "accept"),
            ("stale file from another run", [f"start=1111111:dddddddddddd"] + good[1:], start, True, "sync"),
            ("no start line", good[1:], start, True, "sync"),
            ("duplicate type line", good[:2] + good[1:], start, True, "sync"),
            ("empty end fingerprint",
             [l if not l.startswith("fingerprint-end=") else "fingerprint-end=" for l in good], start, True, "sync"),
            ("failed baseline still accepted",
             [l.replace("node test rc=0", "node test rc=1") for l in good], start, True, "accept"),
            ("head moved, tree same", good, "2222222:aaaaaaaaaaaa", True, "accept"),
            ("no DONE", good[:-1], start, True, "sync"),
            ("missing type line", [l for l in good if l != "node build rc=0"], start, True, "sync"),
            ("end fingerprint differs",
             [l.replace(f"fingerprint-end={start}", "fingerprint-end=1111111:bbbbbbbbbbbb") for l in good],
             start, True, "sync"),
            ("current tree differs", good, "1111111:cccccccccccc", True, "sync"),
            ("log missing", good, start, False, "sync"),
        )
        for name, lines, current, logs, expected in cases:
            with self.subTest(name), tempfile.TemporaryDirectory(prefix="baseline probe ") as root:
                done = Path(root) / "baseline.done"
                done.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))  # LF 고정 — Windows 텍스트 모드 CRLF 방지
                if logs:
                    for t in ("java-spring", "node"):
                        for k in ("test", "build"):
                            (Path(root) / f"baseline-{t}-{k}.log").write_text("", encoding="utf-8")
                env = dict(os.environ, DONE_FILE=str(done), START=start, CURRENT=current,
                           DIR=root, TYPES="java-spring node")
                result = subprocess.run([bash, "-c", BASELINE_ACCEPT_PROBE], env=env,
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.stdout.strip(), expected, result.stderr)

    def test_verify_block_repair_contract(self):
        text = self.read("phase-complete.md")
        step = section(text, "## Step -1: verify 게이트", "## Step 0: 인수 검증")
        self.assertIn('"수정"', step)
        self.assertIn("다른 테스트·빌드 명령을 시작하지 않고", step)
        self.assertNotIn('"RGR 사이클로 수정"', step)
        repair = section(step, '**verify 회귀 수리** ("수정" 선택 시)', "**Iron Law 위반 감지**")
        for needle in (
            "`verify-status: pending`",
            '`verify-fingerprint: ""`',
            "수리 모드",
            "테스트 파일은 수정하지 않는다",
            "테스트를 고쳐야만 해결됨",
            "수리 라운드 상한 2회",
            "`verify 회귀 수리 R{n}` 항목 수",
            "세션 직접",
            "다시 리뷰하지 않는다",
        ):
            self.assertIn(needle, repair)
        self.assertNotIn("red-writer 재호출", repair)
        self.assertIn("이 verify가 유일하다", text[: text.index("## Step -2")])
        verify = (ROOT / ".claude/skills/gx-verify/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("다른 테스트·빌드 명령을 병행하지 않는다", section(verify, "### Step 2", "### Step 3"))
        state = (TDD_PHASES.parent / "references/pipeline-state.md").read_text(encoding="utf-8")
        self.assertIn("verify 회귀 수리", state)


if __name__ == "__main__":
    unittest.main()
