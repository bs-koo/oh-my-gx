"""evals.json의 세 사례를 실행한 결과 폴더를 검증한다.

사용: python check_outputs.py <사례별 출력 프로젝트가 있는 폴더>
스킬 실행은 별도로 수행한다. 이 검사는 생성된 원장과 계획만 읽는다.
"""

from collections import Counter
import json
from pathlib import Path
import re
import sys


def table(path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines()
             if line.lstrip().startswith("|")]
    cells = lambda line: [cell.strip() for cell in line.strip().strip("|").split("|")]
    header = cells(lines[0])
    return [dict(zip(header, cells(line))) for line in lines[2:]]


def valid_dependencies(rows):
    graph = {row["ID"]: re.findall(r"W\d+", row["의존"]) for row in rows}
    visiting, visited = set(), set()

    def visit(node):
        if node not in graph or node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        if not all(visit(target) for target in graph[node]):
            return False
        visiting.remove(node)
        visited.add(node)
        return True

    return all(visit(node) for node in graph)


def grade(case, project):
    fixture = case["fixture"]
    rows = table(project / ".dev/plan.md")
    by_id = {row["ID"]: row for row in rows}
    plan_header = ("ID", "작업", "도메인", "요구사항", "의존", "작업 위치", "상태")
    initial = {row[0]: dict(zip(plan_header, row)) for row in fixture["plan_rows"]}
    ledger_header = ("ID", "요구사항", "AC", "상태", "PR")
    ledgers = {domain: table(project / "context" / domain / "status.md")
               for domain in fixture["ledgers"]}
    original = {domain: [dict(zip(ledger_header, row)) for row in source]
                for domain, source in fixture["ledgers"].items()}
    checks = []

    def check(text, passed):
        checks.append({"text": text, "passed": bool(passed),
                       "evidence": str(project)})

    check("작업 ID가 중복·삭제·추가 없이 보존된다", len(rows) == len(initial) and set(by_id) == set(initial))
    if case["id"] == 1:
        check("부분 폐기된 FR-2만 W01의 범위에서 제거된다",
              by_id["W01"]["요구사항"] == "FR-1" and by_id["W01"]["상태"] == "대기")
        check("진행·완료 작업의 모든 값이 보존된다",
              all(by_id[key] == initial[key] for key in ("W02", "W03")))
        check("원장 전체가 보존된다", ledgers == original)
    elif case["id"] == 2:
        assigned = Counter(token for row in rows if row["상태"] != "폐기"
                           for token in re.findall(r"(?:NFR|FR)-\d+", row["요구사항"]))
        check("FR-1·FR-2가 각각 한 작업에만 배정된다", assigned == {"FR-1": 1, "FR-2": 1})
        check("사용자 승인대로 FR-1은 W01에 남는다",
              re.findall(r"(?:NFR|FR)-\d+", by_id["W01"]["요구사항"]) == ["FR-1"])
        check("의존 대상이 실존하고 의존 순환이 없다", valid_dependencies(rows))
        check("원장 전체가 보존된다", ledgers == original)
    elif case["id"] == 3:
        meter = {row["ID"]: row for row in ledgers["계량기"]}
        check("입력 0건인 대체 대상의 미반영 요구사항이 폐기된다", meter["FR-1"]["상태"] == "🚫")
        check("해당 대기 작업이 폐기된다", by_id["W02"]["상태"] == "폐기")
        check("기존 완료 행의 ID·AC·상태·PR이 보존된다", meter["FR-2"] == original["계량기"][1])
        check("범위 밖 정산 원장과 작업이 보존된다",
              ledgers["정산"] == original["정산"] and by_id["W03"] == initial["W03"])
        check("입력이 동일한 건물 원장과 작업이 보존된다",
              ledgers["건물"] == original["건물"] and by_id["W01"] == initial["W01"])
    return {"eval_id": case["id"], "eval_name": case["name"], "expectations": checks}


def main():
    root = Path(sys.argv[1])
    cases = json.loads(Path(__file__).with_name("evals.json").read_text(encoding="utf-8"))["evals"]
    results = [grade(case, root / case["name"]) for case in cases]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["passed"] for result in results for item in result["expectations"]) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
