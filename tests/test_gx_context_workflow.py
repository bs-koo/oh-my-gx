"""공유 intake가 사실을 재질문하거나 관측을 요구사항으로 승격하지 않는지 검증한다."""

import importlib.util
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".claude/skills/gx-context/scripts/intake.py"


class ContextIntakeTests(unittest.TestCase):
    def normalize(self, **overrides):
        self.assertTrue(HELPER.is_file(), "설치 가능한 공통 intake helper가 필요합니다")
        spec = importlib.util.spec_from_file_location("gx_context_intake", HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = {
            "run-id": "W01",
            "goal": "요구사항 정리",
            "intent": "plan",
            "stop-at": "plan",
            "sources": [{"path": "docs/req.md", "scope": "§2"}],
            "decisions": [],
            "requirements": [],
            "plan-file": ".dev/plan.md",
        }
        payload.update(overrides)
        return module.normalize_intake(payload)

    def test_grounded_five_facts_do_not_generate_confirmation_questions(self):
        facts = [
            {"topic": topic, "value": "문서의 명확한 내용", "status": "explicit",
             "source": "docs/req.md#배경", "impact": "scope"}
            for topic in ("문제", "현재 프로세스", "사용자/규모", "담당", "관련 레포")
        ]
        result = self.normalize(decisions=facts)
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["decisions"], facts)

    def test_only_consequential_missing_decisions_block_progress(self):
        result = self.normalize(decisions=[
            {"topic": "다운로드 권한", "value": None, "status": "unresolved",
             "source": "docs/req.md#다운로드", "impact": "behavior"},
            {"topic": "PM 이름", "value": None, "status": "unresolved",
             "source": "docs/req.md", "impact": "metadata"},
        ])
        self.assertEqual([item["topic"] for item in result["questions"]], ["다운로드 권한"])
        self.assertEqual([item["blocking"] for item in result["unresolved"]], [True, False])

    def test_authorized_delegation_does_not_repeat_internal_choices(self):
        decision = {"topic": "파일 경계", "value": "컨트롤러와 서비스 분리",
                    "status": "inferred", "source": "src/payment", "impact": "architecture",
                    "delegation-source": "사용자 메시지: 세부 설계는 맡김"}
        result = self.normalize(decisions=[decision])
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["approval"]["status"], "unconfirmed")
        self.assertEqual(result["decisions"][0]["status"], "inferred")

    def test_inferred_behavior_without_delegation_requires_an_answer(self):
        result = self.normalize(decisions=[{
            "topic": "권한", "value": "관리자만", "status": "inferred",
            "source": "src/auth.py", "impact": "behavior",
        }])
        self.assertEqual(len(result["questions"]), 1)
        self.assertTrue(result["unresolved"][0]["blocking"])

    def test_removal_approval_cannot_be_inferred_from_delegation(self):
        result = self.normalize(decisions=[{
            "topic": "기존 FR-4 폐기", "value": "폐기", "status": "inferred",
            "source": "docs/req.md", "impact": "removal",
            "delegation-source": "사용자 메시지: 구현은 맡김",
        }])
        self.assertEqual(len(result["questions"]), 1)

    def test_code_observations_never_become_future_requirements(self):
        observed = {"domain": "결제", "path": "src/payment.py", "section": "pay",
                    "ids": [], "origin": "code", "text": "현재 무조건 승인한다"}
        requested = {"domain": "결제", "path": "context/결제/status.md",
                     "section": "요구사항 원장", "ids": ["FR-1"],
                     "origin": "conversation", "text": "사용자가 승인을 요청했다"}
        result = self.normalize(requirements=[observed, requested])
        self.assertEqual(result["requirements"], [{
            "domain": "결제", "path": "context/결제/status.md",
            "section": "요구사항 원장", "ids": ["FR-1"],
        }])
        self.assertEqual(result["observed-facts"], [observed])

    def test_context_handoff_preserves_endpoint_and_domain_scoped_ids(self):
        pointers = [{"domain": domain, "path": f"context/{domain}/status.md",
                     "section": "요구사항 원장", "ids": ["FR-1"], "origin": "document"}
                    for domain in ("건물", "계량기")]
        result = self.normalize(**{"intent": "understand", "stop-at": "understand",
                                   "requirements": pointers, "plan-file": None})
        self.assertEqual(result["stop-at"], "understand")
        self.assertEqual(result["intent"], "understand")
        self.assertIsNone(result["plan-file"])
        self.assertEqual([item["domain"] for item in result["requirements"]], ["건물", "계량기"])
        self.assertNotIn("next-skill", result)

    def test_approval_requires_an_actual_source(self):
        with self.assertRaisesRegex(ValueError, "approval.*source"):
            self.normalize(approval={"status": "approved", "source": None})

    def test_existing_blocking_unresolved_survives_approved_handoff(self):
        unresolved = {"topic": "인증 방식", "impact": "behavior", "blocking": True,
                      "source": "사용자 메시지"}
        result = self.normalize(unresolved=[unresolved], approval={
            "status": "approved", "source": "사용자: 구현 승인"})
        self.assertEqual(result["unresolved"], [unresolved])
        self.assertEqual(result["questions"], [unresolved])

    def test_conflicting_explicit_sources_require_a_decision(self):
        decisions = [{"topic": "인증", "value": value, "status": "explicit",
                      "source": source, "impact": "architecture"}
                     for value, source in (("세션", "문서 A"), ("JWT", "문서 B"))]
        result = self.normalize(decisions=decisions)
        self.assertEqual([item["topic"] for item in result["questions"]], ["인증"])
        self.assertTrue(result["unresolved"][0]["blocking"])
        self.assertEqual(result["decisions"], decisions)

    def test_existing_unresolved_is_cleared_only_by_grounded_unambiguous_answer(self):
        unresolved = {"topic": "인증", "impact": "behavior", "blocking": True,
                      "source": "문서 A"}
        decision = {"topic": "인증", "value": "JWT", "status": "inferred",
                    "source": "src/auth.py", "impact": "behavior",
                    "delegation-source": "사용자: 내부 설계 위임"}
        pending = self.normalize(unresolved=[unresolved], decisions=[decision])
        self.assertEqual(pending["questions"], [unresolved])
        decision.update(status="explicit", source="사용자: JWT로 확정")
        resolved = self.normalize(unresolved=[unresolved], decisions=[decision])
        self.assertEqual(resolved["questions"], [])
        self.assertEqual(resolved["unresolved"], [])

    def test_installed_helper_runs_from_consumer_without_repository_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            consumer = Path(directory)
            source = consumer / "컨텍스트 입력.json"
            output = consumer / "인계.json"
            payload = {"run-id": "W02", "goal": "계량기 요구사항 정리",
                       "intent": "plan", "stop-at": "plan", "sources": [],
                       "decisions": [], "plan-file": ".dev/plan.md"}
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(HELPER), str(source), "--output", str(output)],
                                    cwd=consumer, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["goal"], payload["goal"])
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), payload)

    def test_both_input_modes_reference_the_same_installed_contract(self):
        bundle = ROOT / ".claude/skills/gx-context"
        for mode in ("create", "from-document"):
            text = (bundle / f"modes/{mode}.md").read_text(encoding="utf-8")
            self.assertIn('Read("references/intake.md")', text)
        contract = (bundle / "references/intake.md").read_text(encoding="utf-8")
        helper_links = [bundle / "scripts" / part.split("`", 1)[0]
                        for part in contract.split("`scripts/")[1:]]
        self.assertTrue(helper_links)
        self.assertTrue(all(path.is_file() for path in helper_links))


class ContextPlanTests(unittest.TestCase):
    def helper(self):
        path = HELPER.with_name("plan.py")
        self.assertTrue(path.is_file(), "소비 프로젝트에 설치되는 계획 검증 helper가 필요합니다")
        spec = importlib.util.spec_from_file_location("gx_context_plan", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(self, task="W01", domain="건물", requirements="FR-1", dependencies="-", status="대기"):
        return {"ID": task, "작업": task + " 작업", "도메인": domain,
                "요구사항": requirements, "의존": dependencies, "작업 위치": "-", "상태": status}

    def ledger(self, domain="건물", requirement="FR-1", status="⬜"):
        return {"domain": domain, "id": requirement, "text": "실제 요구", "status": status}

    def test_ready_work_requires_completed_dependencies_and_waiting_state(self):
        rows = [self.row("W00", requirements="FR-1", status="완료"),
                self.row("W01", requirements="FR-2", dependencies="W00"),
                self.row("W02", requirements="FR-3", dependencies="W01"),
                self.row("W03", requirements="FR-4", status="진행")]
        ledger = [self.ledger(requirement=f"FR-{number}", status="✅" if number == 1 else "⬜")
                  for number in range(1, 5)]
        result = self.helper().analyze(rows, ledger)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["ready"], ["W01"])
        self.assertEqual(result["blocked"], [{"id": "W02", "dependencies": ["W01"]}])

    def test_missing_and_duplicate_requirement_assignments_fail_closed(self):
        rows = [self.row("W01"), self.row("W02")]
        result = self.helper().analyze(rows, [self.ledger(), self.ledger(requirement="NFR-1")])
        self.assertEqual(result["unassigned"], [{"domain": "건물", "id": "NFR-1"}])
        self.assertTrue(any("중복 배정" in error for error in result["errors"]))
        self.assertEqual(result["ready"], [])

    def test_same_ids_from_different_domains_stay_distinct(self):
        rows = [self.row("W01", domain="통합", requirements="건물:FR-1, 계량기:FR-1")]
        result = self.helper().analyze(rows, [self.ledger(), self.ledger(domain="계량기")])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["ready"], ["W01"])

    def test_repeated_or_overlapping_refs_within_one_task_are_one_assignment(self):
        for references in ("FR-1, FR-1", "FR-1~2, FR-2"):
            with self.subTest(references=references):
                ledger = [self.ledger()]
                if "FR-2" in references or "~2" in references:
                    ledger.append(self.ledger(requirement="FR-2"))
                result = self.helper().analyze([self.row(requirements=references)], ledger)
                self.assertEqual(result["errors"], [])
                self.assertEqual(result["ready"], ["W01"])

    def test_escaped_pipe_cells_preserve_backslash_parity(self):
        module = self.helper()
        for count in (1, 2, 3, 4):
            with self.subTest(backslashes=count):
                first = "A" + "\\" * count
                if count % 2:
                    first += "|B"
                text = "| 값 | 끝 |\n|---|---|\n| " + first + "| 끝 |\n"
                try:
                    rows = module.parse_table(text, ["값", "끝"])
                except ValueError as exc:
                    self.fail(str(exc))
                self.assertEqual(rows, [{"값": first, "끝": "끝"}])

    def test_alignment_and_short_separator_cells_remain_valid(self):
        module = self.helper()
        for separator in ("|:-:|---:|", ":-: | -----------:", "- | -"):
            with self.subTest(separator=separator):
                text = "| 값 | 끝 |\n" + separator + "\n| 실제 값 | 끝 |\n"
                self.assertEqual(module.parse_table(text, ["값", "끝"]),
                                 [{"값": "실제 값", "끝": "끝"}])

    def test_missing_or_invalid_table_separators_are_rejected(self):
        module = self.helper()
        for separator in (None, "", "not a separator", "|---|", "|---|text|"):
            with self.subTest(separator=separator):
                lines = ["| 값 | 끝 |"]
                if separator is not None:
                    lines.append(separator)
                lines.extend(["| 첫 행 | 끝 |", "| 둘째 행 | 끝 |"])
                with self.assertRaises(ValueError):
                    module.parse_table("\n".join(lines), ["값", "끝"])

    def test_ambiguous_cross_domain_reference_blocks_recommendations(self):
        rows = [self.row(domain="통합")]
        result = self.helper().analyze(rows, [self.ledger(), self.ledger(domain="계량기")])
        self.assertTrue(any("출처 도메인" in error for error in result["errors"]))
        self.assertEqual(result["ready"], [])

    def test_partial_and_full_discards_are_proposals_and_never_ready(self):
        rows = [self.row("W01", requirements="FR-1~2"), self.row("W02", requirements="FR-3")]
        ledger = [self.ledger(status="🚫"), self.ledger(requirement="FR-2"),
                  self.ledger(requirement="FR-3", status="🚫")]
        result = self.helper().analyze(rows, ledger)
        self.assertEqual(result["partial-discards"], [{"id": "W01", "requirements": ["건물:FR-1"]}])
        self.assertEqual(result["discard-candidates"], ["W02"])
        self.assertEqual(result["ready"], [])

    def test_cycles_and_discarded_dependencies_block_all_recommendations(self):
        rows = [self.row("W01", dependencies="W02"),
                self.row("W02", requirements="FR-2", dependencies="W01", status="폐기")]
        result = self.helper().analyze(rows, [self.ledger(), self.ledger(requirement="FR-2", status="🚫")])
        self.assertTrue(any("의존 순환" in error for error in result["errors"]))
        self.assertTrue(any("폐기된 작업" in error for error in result["errors"]))
        self.assertEqual(result["ready"], [])

    def test_reruns_preserve_ids_and_progress_or_completion_without_mutation(self):
        rows = [self.row("W01", status="진행"), self.row("W02", requirements="FR-2", status="완료")]
        ledger = [self.ledger(status="✅"), self.ledger(requirement="FR-2", status="✅")]
        snapshot = deepcopy((rows, ledger))
        module = self.helper()
        first = module.analyze(rows, ledger)
        self.assertEqual(first, module.analyze(rows, ledger))
        self.assertEqual((rows, ledger), snapshot)
        self.assertEqual(first["progress-review"], ["W01"])
        self.assertEqual(first["ready"], [])

    def test_installed_plan_cli_reads_real_tables_without_changing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            domain = root / "context/건물"
            domain.mkdir(parents=True)
            ledger = domain / "status.md"
            ledger.write_text("## 요구사항 원장\n\n| ID | 요구사항 | AC | 상태 | PR |\n"
                              "|---|---|---|---|---|\n| FR-1 | 실제 요구 | - | ⬜ | - |\n", encoding="utf-8")
            plan = root / "계획.md"
            plan.write_text("| ID | 작업 | 도메인 | 요구사항 | 의존 | 작업 위치 | 상태 |\n"
                            "|----|------|--------|----------|------|-----------|------|\n"
                            "| W01 | 조회 | 건물 | FR-1 | - | - | 대기 |\n", encoding="utf-8")
            before = {path: path.read_bytes() for path in (plan, ledger)}
            process = subprocess.run([sys.executable, str(HELPER.with_name("plan.py")),
                                      "--project-root", str(root), "--plan", str(plan)],
                                     cwd=root, capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)["ready"], ["W01"])
            self.assertEqual(before, {path: path.read_bytes() for path in (plan, ledger)})

    def test_installed_plan_cli_accepts_escaped_requirement_ac_and_task_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "context/건물/status.md"
            ledger.parent.mkdir(parents=True)
            ledger.write_text("| ID | 요구사항 | AC | 상태 | PR |\n|---|---|---|---|---|\n"
                              "| FR-1 | A \\| B 조회 | A \\| B 표시 | ⬜ | #7 |\n", encoding="utf-8")
            plan = root / "계획.md"
            plan.write_text("| ID | 작업 | 도메인 | 요구사항 | 의존 | 작업 위치 | 상태 |\n"
                            "|---|---|---|---|---|---|---|\n"
                            "| W01 | A \\| B 조회 | 건물 | FR-1 | - | - | 대기 |\n", encoding="utf-8")
            before = {path: path.read_bytes() for path in (plan, ledger)}
            process = subprocess.run([sys.executable, str(HELPER.with_name("plan.py")),
                                      "--project-root", str(root), "--plan", str(plan)],
                                     cwd=root, capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            self.assertEqual(json.loads(process.stdout)["ready"], ["W01"])
            self.assertEqual(before, {path: path.read_bytes() for path in (plan, ledger)})

    def test_plan_cli_blocks_missing_separator_in_plan_or_ledger(self):
        for missing in ("plan", "ledger"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                ledger = root / "context/건물/status.md"
                ledger.parent.mkdir(parents=True)
                ledger_separator = "" if missing == "ledger" else "|---|---|---|---|---|\n"
                first_status = "⬜" if missing == "ledger" else "✅"
                ledger.write_text("| ID | 요구사항 | AC | 상태 | PR |\n" + ledger_separator +
                                  f"| FR-1 | 첫 요구 | - | {first_status} | #7 |\n"
                                  "| FR-2 | 둘째 요구 | - | ⬜ | - |\n", encoding="utf-8")
                plan = root / "계획.md"
                plan_separator = "" if missing == "plan" else "|---|---|---|---|---|---|---|\n"
                first_task = "| W01 | 첫 작업 | 건물 | FR-1 | - | old/branch | 완료 |\n" if missing == "plan" else ""
                plan.write_text("| ID | 작업 | 도메인 | 요구사항 | 의존 | 작업 위치 | 상태 |\n" +
                                plan_separator + first_task +
                                "| W02 | 둘째 작업 | 건물 | FR-2 | - | - | 대기 |\n", encoding="utf-8")
                process = subprocess.run([sys.executable, str(HELPER.with_name("plan.py")),
                                          "--project-root", str(root), "--plan", str(plan)],
                                         cwd=root, capture_output=True, encoding="utf-8")
                self.assertEqual(process.returncode, 1, process.stdout)
                result = json.loads(process.stdout)
                self.assertTrue(result["errors"])
                self.assertEqual(result["ready"], [])


if __name__ == "__main__":
    unittest.main()
