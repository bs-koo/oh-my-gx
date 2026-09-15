from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / ".claude/skills/gx-dev/SKILL.md"
TDD = ROOT / ".claude/skills/gx-tdd/SKILL.md"
SETUPS = (
    ROOT / ".claude/skills/gx-dev/phases/phase-setup.md",
    ROOT / ".claude/skills/gx-tdd/phases/phase-setup.md",
)
TDD_RESUME = ROOT / ".claude/skills/gx-tdd/phases/setup-resume.md"


class PipelineBootstrapContractTests(unittest.TestCase):
    def read(self, path: Path) -> str:
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
            self.assertIn("명령이 없거나 메타데이터 오류", root_step, path)
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


if __name__ == "__main__":
    unittest.main()
