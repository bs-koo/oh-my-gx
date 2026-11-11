"""gx-setup이 새 설정 필드(베이스 브랜치·거절 기억·기본값)와 등록 직후 감지 확인을 실제 계약대로 안내하는지 검사한다."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / ".claude/skills/gx-setup"
TEMPLATE = SETUP / "references/config.template.json"
DEV_IGNORE = ROOT / ".claude/skills/gx-work/references/dev-ignore-check.md"


def read(path):
    return Path(path).read_text(encoding="utf-8")


class ConfigDefaultsTests(unittest.TestCase):
    def test_template_carries_shared_fields_with_current_behavior_defaults(self):
        config = json.loads(read(TEMPLATE))
        self.assertEqual(config["conventions"]["baseBranch"], "")
        self.assertIs(config["notifications"]["googleChat"]["declined"], False)
        self.assertEqual(config["devSharing"], "")
        self.assertEqual(config["devArtifacts"], "commit")
        self.assertEqual(config["workflowDefaults"],
                         {"stopAt": "", "mode": "", "modelProfile": "", "executionMethod": ""})
        self.assertEqual(config["timeouts"]["build"], 600000)
        self.assertEqual(config["documentChecks"], {"customFormatPaths": []})
        self.assertEqual(config, json.loads(read(ROOT / ".claude/config.json")))


class SetupContractTests(unittest.TestCase):
    def setUp(self):
        self.skill = read(SETUP / "SKILL.md")

    def test_base_branch_is_asked_once_only_when_main_and_develop_coexist(self):
        step = self.skill.split("### 3.6단계", 1)[1].split("\n### ", 1)[0]
        self.assertIn('Read("references/base-branch.md")', step)
        reference = read(SETUP / "references/base-branch.md")
        for contract in ("`main`과 `develop`이 **함께** 있을 때만", "conventions.baseBranch",
                         '{"conventions":{"baseBranch":"{선택}"}}', "매번 묻기", "기존 설정 유지"):
            self.assertIn(contract, reference)

    def test_declined_choices_are_saved_and_setup_remains_the_way_to_change_them(self):
        chat = read(SETUP / "references/google-chat.md")
        skip = chat.split('- "건너뛰기" →', 1)[1].split("\n", 1)[0]
        self.assertIn('{"notifications":{"googleChat":{"declined":true}}}', skip)
        self.assertIn("gx-setup에서는 다시 묻는다", chat)
        ignore = read(DEV_IGNORE)
        self.assertIn('`devSharing`을 `"ignore"`로 기록', ignore)
        self.assertIn("바꾸려면 /gx-setup을 다시 실행하세요", ignore)
        first = ignore.split("## 1.", 1)[1].split("## 2.", 1)[0]
        self.assertIn('`"ignore"`', first)
        self.assertIn("gx-setup이 실행하는 것이 아니면 묻지 않고", first)

    def test_profile_step_matches_user_invoked_setup_and_workflow_defaults(self):
        self.assertIn("disable-model-invocation: true", self.skill)
        self.assertNotIn('Skill("oh-my-gx:gx-setup")', self.skill)
        self.assertNotIn("세션 확정값", self.skill)
        step = self.skill.split("### 5단계", 1)[1].split("\n### ", 1)[0]
        self.assertIn("workflowDefaults.modelProfile", step)
        self.assertIn("설정값으로 진행", step)
        self.assertIn("이 값만으로는 프로파일 질문이 생략되지 않는다", step)

    def test_execution_method_default_is_only_a_recommendation(self):
        # L7: executionMethod는 진입 질문에서 빼는 항목이 아니라 phase-implement 1.2의 추천값이다.
        line = next(item for item in self.skill.splitlines() if item.startswith("- **기본값 안내**"))
        asked = line.split("설정값으로 진행", 1)[0]
        self.assertNotIn("executionMethod", asked)
        for marker in ("`executionMethod`는 구현계획 확인 질문", "phase-implement 1.2", "추천값으로만", "그대로 묻는다"):
            self.assertIn(marker, line)


class DetectionCheckTests(unittest.TestCase):
    """F2: 등록 직후 감지 확인 문서의 helper 호출이 실제 CLI와 맞는지 실제 저장소로 확인한다."""

    def command(self):
        registration = read(SETUP / "references/project-type-registration.md")
        found = re.search(r'`python "<GX_PLUGIN_ROOT>/scripts/gx-test-plan\.py" (plan [^`]+)`', registration)
        self.assertIsNotNone(found, "등록 직후 감지 확인 명령 누락")
        return found[1].replace('"<PROJECT_ROOT>"', "{root}").split()

    def run_check(self, root):
        args = [part.format(root=root) for part in self.command()]
        return subprocess.run([sys.executable, str(ROOT / "scripts/gx-test-plan.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", timeout=60)

    def test_documented_command_reports_path_detect_and_failure(self):
        with tempfile.TemporaryDirectory(prefix="gx-setup-detect-") as directory:
            root = Path(directory).resolve()
            (root / "backend").mkdir()
            (root / "backend/build.gradle.kts").write_text("plugins {}\n", encoding="utf-8")
            (root / ".claude").mkdir()
            config = root / ".claude/config.json"

            def register(detect):
                config.write_text(json.dumps({"projectTypes": {"java": {
                    "detect": [detect], "test": "./gradlew test", "buildOnly": "./gradlew build -x test"}}}),
                    encoding="utf-8")

            register("backend/build.gradle.kts")
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.test",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.test")
            for git in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "init"]):
                subprocess.run(["git", *git], cwd=root, check=True, capture_output=True, env=env)
            result = self.run_check(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("java:backend", {entry["project"] for entry in json.loads(result.stdout)["entries"]})
            register("back/build.gradle.kts")
            missed = self.run_check(root)
            self.assertEqual(missed.returncode, 1)
            self.assertIn("no project types detected", missed.stderr)


if __name__ == "__main__":
    unittest.main()
