"""실행 지시문이 필요한 시점에 읽히고 단일 파일에 보관되는지 검증한다."""

from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude/skills"
CONTRACT_REFS = (
    "references/intent-routing.md",
    "references/pipeline-state.md",
    "references/interaction-contract.md",
)
CONTEXT_MODES = {
    "신규": "modes/create.md",
    "문서 기반": "modes/from-document.md",
    "갱신": "modes/update.md",
    "동기화": "modes/sync.md",
}


class SkillInstructionLayoutTests(unittest.TestCase):
    def text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def assert_relative_links_resolve(self, path: Path) -> None:
        """출력 템플릿을 제외한 지시문 링크를 파일 위치 기준으로 확인한다."""
        fence = None
        for line in self.text(path).splitlines():
            marker = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line)
            if marker:
                token, rest = marker.groups()
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence) and not rest.strip():
                    fence = None
                continue
            if fence is not None:
                continue
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", line):
                target = target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                self.assertTrue((path.parent / target).is_file(), f"{path}: {target}")

    def test_relative_links_ignore_output_template_but_check_instructions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "mode.md"
            (source.parent / "existing.md").write_text("참조 본문", encoding="utf-8")
            source.write_text(
                "참조: [실제 지시문](existing.md)\n"
                "```markdown\n"
                "# 생성될 context/README.md\n"
                "- [공통 용어 사전](glossary.md)\n"
                "```\n",
                encoding="utf-8",
            )
            self.assert_relative_links_resolve(source)
            source.write_text(
                source.read_text(encoding="utf-8") + "참조: [누락된 지시문](missing.md)\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssertionError):
                self.assert_relative_links_resolve(source)

    def test_context_modes_are_conditionally_loaded(self):
        directory = SKILLS / "gx-context"
        main = self.text(directory / "SKILL.md")
        for mode, relative in CONTEXT_MODES.items():
            with self.subTest(mode=mode):
                self.assertTrue((directory / relative).is_file())
                pointer = rf'^\s*-\s*`{re.escape(mode)}`\s*→\s*`Read\("{re.escape(relative)}"\)`'
                self.assertRegex(main, re.compile(pointer, re.MULTILINE))
                self.assert_relative_links_resolve(directory / relative)
        self.assertLessEqual(len(main.splitlines()), 320)

    def test_context_mode_sections_have_one_owner(self):
        directory = SKILLS / "gx-context"
        expected = {
            "## 모드 B: 신규 (Q&A 기반)": "modes/create.md",
            "## 모드 C: 문서 기반 (--from)": "modes/from-document.md",
            "## 모드 D: 갱신": "modes/update.md",
            "## 모드 E: 동기화 (--sync)": "modes/sync.md",
            "### C-4-1. 요구사항 원장 반영": "modes/from-document.md",
            "## 주제 문서 헤더 템플릿": "modes/update.md",
        }
        paths = [directory / "SKILL.md", *(directory / p for p in CONTEXT_MODES.values())]
        for heading, owner in expected.items():
            with self.subTest(heading=heading):
                self.assertTrue((directory / owner).is_file())
                self.assertIn(heading, self.text(directory / owner).splitlines())
                owners = [p for p in paths if p.is_file() and heading in self.text(p).splitlines()]
                self.assertEqual(owners, [directory / owner])

    def test_context_internal_reads_resolve_from_skill_directory(self):
        directory = SKILLS / "gx-context"
        document_mode = self.text(directory / "modes/from-document.md")
        for relative in ("modes/create.md", "modes/update.md"):
            with self.subTest(relative=relative):
                self.assertIn(f'Read("{relative}")', document_mode)
                self.assertTrue((directory / relative).is_file())
        for relative in CONTEXT_MODES.values():
            with self.subTest(mode=relative):
                self.assertIn("상대경로는 gx-context/SKILL.md 위치를 기준으로", self.text(directory / relative))

    def test_dev_references_are_loaded_before_phase_loop(self):
        self.assert_contract_load("gx-dev")

    def test_tdd_references_are_loaded_before_phase_loop(self):
        self.assert_contract_load("gx-tdd")

    def assert_contract_load(self, name: str) -> None:
        directory = SKILLS / name
        main = self.text(directory / "SKILL.md")
        loop = main.index("### Phase 실행 루프")
        positions = []
        for relative in CONTRACT_REFS:
            with self.subTest(skill=name, reference=relative):
                path = directory / relative
                self.assertTrue(path.is_file())
                position = main.index(f'Read("{relative}")')
                self.assertLess(position, loop)
                positions.append(position)
                self.assert_relative_links_resolve(path)
        self.assertEqual(positions, sorted(positions), name)
        self.assertLessEqual(len(main.splitlines()), 520)

    def test_moved_headings_have_one_owner_per_skill(self):
        expected = {
            "## 인자": CONTRACT_REFS[0],
            "## 코드 맵": CONTRACT_REFS[1],
            "## Trust Ledger (신뢰 원장)": CONTRACT_REFS[1],
            "### 에이전트 질문 → AskUserQuestion 변환 규칙": CONTRACT_REFS[2],
            "## 플래그 충돌 검증": CONTRACT_REFS[0],
            "## 에러 처리": CONTRACT_REFS[2],
        }
        for name in ("gx-dev", "gx-tdd"):
            directory = SKILLS / name
            paths = [directory / "SKILL.md", *(directory / p for p in CONTRACT_REFS)]
            for heading, owner in expected.items():
                with self.subTest(skill=name, heading=heading):
                    self.assertTrue((directory / owner).is_file())
                    self.assertIn(heading, self.text(directory / owner).splitlines())
                    owners = [p for p in paths if p.is_file() and heading in self.text(p).splitlines()]
                    self.assertEqual(owners, [directory / owner])

    def test_phase_safety_gates_remain_in_main_skills(self):
        for name in ("gx-dev", "gx-tdd"):
            with self.subTest(skill=name):
                main = self.text(SKILLS / name / "SKILL.md")
                self.assertIn("> **CRITICAL: Phase 스킵 절대 금지.**", main)
                self.assertIn("### Phase 실행 루프", main)
        self.assertIn("> **Phase 합치기 절대 금지.**", self.text(SKILLS / "gx-tdd/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
