"""재계획 정책 예제와 Node fixture의 RED→GREEN을 실행한다.

문서 함수·fixture 검증이며 모델의 지시 준수, 실제 앱 또는 인증 설치 smoke가 아니다.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_codex_core_plan_edges import SKILLS, documented_policy


def case(ac="AC-1", expected="ok", replaces=None):
    value = {"ac_id": ac, "test_file": "cases.test.cjs", "selector": ac, "expectation": expected}
    if replaces is not None:
        value["replaces"] = replaces
    return value


class CoreReplanningPolicyTests(unittest.TestCase):
    def classifier(self):
        return documented_policy(self, "gx-tdd/references/core-replanning.md", "classify_cases")

    def test_keep_add_replace_retire_and_input_immutability(self):
        classify = self.classifier()
        previous = {"C-keep": case(), "C-edit": case("AC-2"), "C-drop": case("AC-3")}
        current = {"C-keep": case(), "C-new": case("AC-4"),
                   "C-edited": case("AC-2", "new", "C-edit")}
        before = deepcopy((previous, current))
        self.assertEqual(classify(previous, current), {
            "keep": ["C-keep"], "add": ["C-new"], "retire": ["C-drop"],
            "replace": {"C-edit": "C-edited"},
        })
        self.assertEqual((previous, current), before)

    def test_unchanged_replacement_metadata_remains_keep(self):
        classify = self.classifier()
        previous = {"C-2": case("AC-2", "new", "C-1")}
        self.assertEqual(classify(previous, deepcopy(previous)), {
            "keep": ["C-2"], "add": [], "retire": [], "replace": {},
        })

    def test_same_id_content_changes_require_new_id(self):
        classify = self.classifier()
        for key, value in (("ac_id", "AC-2"), ("expectation", "changed"),
                           ("selector", "new-selector"), ("test_file", "other.test.cjs")):
            current = {"C-1": case()}
            current["C-1"][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                classify({"C-1": case()}, current)

    def test_invalid_replacement_and_retired_id_reuse_rejected(self):
        classify = self.classifier()
        examples = (
            ({"C-1": case()}, {"C-2": case(replaces="missing")}, ()),
            ({"C-1": case()}, {"C-2": case(replaces="C-1"), "C-3": case(replaces="C-1")}, ()),
            ({"C-1": case()}, {"C-1": case(), "C-old": case("AC-2")}, ("C-old",)),
            ({"C-1": case()}, {"C-1": case(), "C-2": case(replaces="C-1")}, ()),
        )
        for index, (previous, current, retired) in enumerate(examples):
            with self.subTest(example=index), self.assertRaises(ValueError):
                classify(previous, current, retired)

    def test_delete_only_and_empty_change_have_no_new_red_cases(self):
        classify = self.classifier()
        self.assertEqual(classify({"C-1": case(), "C-2": case("AC-2")}, {"C-1": case()}),
                         {"keep": ["C-1"], "add": [], "retire": ["C-2"], "replace": {}})
        self.assertEqual(classify({}, {}), {"keep": [], "add": [], "retire": [], "replace": {}})

    def test_production_instructions_connect_retirement_history_and_active_baselines(self):
        path = SKILLS / "gx-tdd/references/core-replanning.md"
        self.assertTrue(path.is_file(), "재계획 실행 계약 누락")
        text = path.read_text(encoding="utf-8")
        for label, pattern in (
            ("삭제-only production 변경 제한", r"(?:삭제-only|삭제만|retire.only)[^\n]*(?:production|프로덕션)[^\n]*(?:금지|허가|승인|변경하지)"),
            ("불변 이력", r"(?:불변[^\n]*이력|이력[^\n]*불변)"),
            ("활성 기준선 세대", r"(?:active[^\n]*(?:기준선|baseline)|(?:기준선|baseline)[^\n]*active)"),
        ):
            with self.subTest(contract=label):
                self.assertIsNotNone(re.search(pattern, text, re.I), label)
        for relative in ("gx-tdd/phases/phase-implement.md", "gx-tdd/phases/phase-requirements.md"):
            with self.subTest(consumer=relative):
                self.assertTrue("core-replanning.md" in (SKILLS / relative).read_text(encoding="utf-8"),
                                f"재계획 계약 연결 누락: {relative}")

    def test_red_writer_role_preserves_green_cases_during_replanning(self):
        for path in (
            SKILLS.parents[1] / "agents/red-writer.md",
            SKILLS / "gx-work/references/codex-roles/red-writer.md",
        ):
            with self.subTest(role=path.name):
                text = path.read_text(encoding="utf-8")
                for phrase in ("재계획", "add", "replace", "keep", "retire"):
                    self.assertTrue(phrase in text, f"{path}: 케이스 구분 {phrase} 누락")
                self.assertNotIn("3. **테스트가 반드시 실패해야 합니다.**", text,
                                 "역할의 절대 규칙도 신규 케이스와 기존 GREEN을 구분해야 함")

    def test_all_retired_scope_stops_before_completion(self):
        for relative in (
            "gx-tdd/references/core-replanning.md", "gx-tdd/phases/phase-implement.md",
            "gx-tdd/SKILL.md", "gx-tdd/phases/phase-complete.md",
        ):
            with self.subTest(consumer=relative):
                path = SKILLS / relative
                self.assertTrue(path.is_file(), f"필수 실행 계약 누락: {relative}")
                text = path.read_text(encoding="utf-8")
                self.assertTrue("scope-closed" in text, f"{relative}: 전체 은퇴 뒤 완료 체이닝 중단 누락")


@unittest.skipUnless(shutil.which("node"), "Node 내장 테스트 러너가 필요함")
class ReplanningNodeFixtureTests(unittest.TestCase):
    """실제 내장 러너로 사례 증거를 만든다. 모델 오케스트레이션을 실행하지 않는다."""

    def test_add_replace_retire_and_unauthorized_keep_edit(self):
        classify = documented_policy(self, "gx-tdd/references/core-replanning.md", "classify_cases")
        with tempfile.TemporaryDirectory(prefix="gx-replan-") as directory:
            root = Path(directory)
            production = root / "value.cjs"
            test_file = root / "cases.test.cjs"

            def fixture_case(identifier, expected, replaces=None):
                value = case(identifier, str(expected), replaces)
                value["selector"] = identifier
                return value

            def write_production(extra):
                production.write_text(f"exports.value = x => x === 'keep' ? 1 : {extra};\n", encoding="utf-8")

            def write_cases(cases):
                lines = ["const {test}=require('node:test');", "const assert=require('node:assert/strict');",
                         "const {value}=require('./value.cjs');"]
                for identifier, expected in cases.items():
                    input_value = "keep" if identifier == "C-keep" else "extra"
                    lines.append(f"test({json.dumps(identifier)},()=>assert.equal(value('{input_value}'),{expected}));")
                test_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

            def case_sources():
                return {identifier: line for line in test_file.read_text(encoding="utf-8").splitlines()
                        for identifier in re.findall(r'^test\("(C-[\w-]+)"', line)}

            def run(expected):
                result = subprocess.run([shutil.which("node"), "--test", "--test-reporter=tap", str(test_file)],
                                        cwd=root, capture_output=True, text=True, encoding="utf-8", check=False)
                statuses = {name: status == "ok" for status, name in
                            re.findall(r"^(ok|not ok) \d+ - (C-[\w-]+)$", result.stdout, re.M)}
                self.assertEqual(statuses, expected, result.stdout[-1800:] + result.stderr[-500:])
                self.assertEqual(result.returncode == 0, all(expected.values()))
                self.assertTrue(statuses["C-keep"], "기존 유지 사례는 GREEN이어야 함")

            previous = {"C-keep": fixture_case("C-keep", 1)}
            added = {**previous, "C-add": fixture_case("C-add", 2)}
            self.assertEqual(classify(previous, added)["add"], ["C-add"])
            write_production(0)
            write_cases({"C-keep": 1})
            run({"C-keep": True})
            approved_keep = case_sources()["C-keep"]
            write_cases({"C-keep": 1, "C-add": 2})
            self.assertEqual(case_sources()["C-keep"], approved_keep)
            run({"C-keep": True, "C-add": False})
            write_production(2)
            run({"C-keep": True, "C-add": True})

            changed = {"C-keep": previous["C-keep"], "C-edit": fixture_case("C-edit", 3, "C-add")}
            self.assertEqual(classify(added, changed)["replace"], {"C-add": "C-edit"})
            history = root / "baseline-1.cjs.snapshot"
            history.write_bytes(test_file.read_bytes())
            prior_digest = hashlib.sha256(history.read_bytes()).hexdigest()
            write_cases({"C-keep": 1, "C-edit": 3})
            self.assertEqual(case_sources()["C-keep"], approved_keep)
            run({"C-keep": True, "C-edit": False})
            write_production(3)
            run({"C-keep": True, "C-edit": True})
            self.assertEqual(hashlib.sha256(history.read_bytes()).hexdigest(), prior_digest)

            self.assertEqual(classify(changed, previous)["retire"], ["C-edit"])
            production_before = production.read_bytes()
            write_cases({"C-keep": 1})
            run({"C-keep": True})
            self.assertEqual(production.read_bytes(), production_before, "삭제-only는 production을 수정하지 않음")
            self.assertEqual(hashlib.sha256(history.read_bytes()).hexdigest(), prior_digest)
            self.assertEqual(case_sources()["C-keep"], approved_keep)

            write_cases({"C-keep": "0+1"})
            run({"C-keep": True})
            self.assertNotEqual(case_sources()["C-keep"], approved_keep,
                                "모두 GREEN이어도 허용 delta 밖 keep 본문 변경은 비교로 검출")


if __name__ == "__main__":
    unittest.main()
