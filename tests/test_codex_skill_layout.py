"""실행 지시문이 필요한 시점에 읽히고 단일 파일에 보관되는지 검증한다."""

from pathlib import Path
import re
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
        """옮긴 본문에서 지시문 파일을 기준으로 쓴 Markdown 링크를 확인한다."""
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.text(path)):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            with self.subTest(source=path.relative_to(ROOT), target=target):
                self.assertTrue((path.parent / target).is_file())

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
