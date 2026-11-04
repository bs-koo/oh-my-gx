#!/usr/bin/env python3
"""업무 계획표·요구사항 원장 정합성과 지금 착수 가능한 작업을 읽기 전용으로 계산한다."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

HEADER = ["ID", "작업", "도메인", "요구사항", "의존", "작업 위치", "상태"]
# 폐기: 요구사항이 삭제되어 할 일이 없어진 작업. 행을 지우지 않고 상태로 남긴다
STATES = {"대기", "진행", "완료", "폐기"}
ID_RE = re.compile(r"^W\d{2}$")


def parse_table(text, header, allow_empty=False):
    def cells(line):
        return [cell.strip() for cell in line.strip().strip("|").split("|")]
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.strip().startswith("|") and cells(line) == header), None)
    if start is None:
        raise ValueError(f"규약 헤더를 가진 표를 찾지 못했습니다: {header}")
    rows = []
    for line in lines[start + 2:]:
        if not line.strip().startswith("|"):
            break
        values = cells(line)
        if len(values) != len(header):
            raise ValueError(f"열 개수가 {len(header)}가 아닙니다: {line}")
        rows.append(dict(zip(header, values)))
    if not rows and not allow_empty:
        raise ValueError("작업 행이 없습니다")
    return rows


def parse(path):
    return parse_table(Path(path).read_text(encoding="utf-8"), HEADER)


def check(rows):
    """행 리스트를 검증하고 오류 메시지 목록을 돌려준다."""
    errors = []
    ids = [r["ID"] for r in rows]

    for r in rows:
        if not ID_RE.match(r["ID"]):
            errors.append(f"{r['ID']}: ID 형식은 W + 두 자리 숫자입니다 (하이픈 금지)")
        if r["상태"] not in STATES:
            errors.append(f"{r['ID']}: 상태는 {'/'.join(sorted(STATES))} 중 하나여야 합니다 (현재 '{r['상태']}')")

    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"ID 중복: {', '.join(sorted(dup))}")

    # 의존 실존
    known = set(ids)
    deps = {}
    for r in rows:
        raw = r["의존"]
        # 쉼표가 규약이지만 문서 예시에 가운뎃점이 쓰여 둘 다 받는다
        d = [] if raw == "-" else [x.strip() for x in re.split(r"[,·]", raw) if x.strip()]
        deps[r["ID"]] = d
        for target in d:
            if target not in known:
                errors.append(f"{r['ID']}: 의존 대상 {target}이(가) 표에 없습니다")

    # 폐기된 작업에 의존하면 그 작업은 영원히 시작할 수 없다
    discarded = {r["ID"] for r in rows if r["상태"] == "폐기"}
    for r in rows:
        if r["상태"] == "폐기":
            continue
        for target in deps.get(r["ID"], []):
            if target in discarded:
                errors.append(f"{r['ID']}: 폐기된 작업 {target}에 의존한다 (의존을 정리하거나 대체 작업을 지정할 것)")

    # 순환 — 실존하는 의존만 대상으로 DFS
    color = {}  # 0=미방문, 1=탐색중, 2=완료

    def visit(node, trail):
        color[node] = 1
        for nxt in deps.get(node, []):
            if nxt not in known:
                continue
            if color.get(nxt, 0) == 1:
                cycle = trail[trail.index(nxt):] + [nxt] if nxt in trail else [nxt, node, nxt]
                errors.append(f"의존 순환: {' → '.join(cycle)}")
                continue  # return하면 node가 탐색중(1)으로 남아 이후 노드가 가짜 순환으로 보고된다
            if color.get(nxt, 0) == 0:
                visit(nxt, trail + [nxt])
        color[node] = 2

    for i in ids:
        if color.get(i, 0) == 0:
            visit(i, [i])

    return errors


LEDGER_HEADER = ["ID", "요구사항", "AC", "상태", "PR"]


def requirement_refs(row, domains):
    refs = []
    for token in re.split(r"[,·]", row["요구사항"]):
        token = token.strip()
        if token in ("", "-"):
            continue
        domain, raw = token.split(":", 1) if ":" in token else (row["도메인"], token)
        domain, raw = domain.strip(), raw.strip()
        if domain in {"공통", "통합"}:
            if len(domains) != 1:
                raise ValueError(f"{row['ID']}: {token}의 출처 도메인이 필요합니다")
            domain = next(iter(domains))
        match = re.fullmatch(r"(N?FR)-(\d+)(?:[~～](?:(N?FR)-)?(\d+))?", raw)
        if not match:
            raise ValueError(f"{row['ID']}: 요구사항 참조 형식 오류: {token}")
        kind, first, end_kind, last = match.groups()
        first, last = int(first), int(last or first)
        if (end_kind and end_kind != kind) or last < first:
            raise ValueError(f"{row['ID']}: 요구사항 범위 오류: {token}")
        refs.extend((domain, f"{kind}-{number}") for number in range(first, last + 1))
    return refs


def analyze(rows, ledger):
    errors = check(rows)
    index = {}
    for item in ledger:
        key = (item["domain"], item["id"])
        if key in index:
            errors.append(f"원장 ID 중복: {key[0]}:{key[1]}")
        if not re.fullmatch(r"N?FR-\d+", item["id"]) or not item.get("text", "").strip():
            errors.append(f"원장 형식 오류: {key[0]}:{key[1]}")
        if item["status"] not in {"⬜", "✅", "🚫"}:
            errors.append(f"원장 상태 오류: {key[0]}:{key[1]}")
        index[key] = item
    domains = {domain for domain, _ in index}
    assignments = defaultdict(list)
    refs_by_task = {}
    for row in rows:
        try:
            refs = requirement_refs(row, domains)
        except ValueError as exc:
            errors.append(str(exc))
            refs = []
        refs_by_task[row["ID"]] = refs
        if row["상태"] != "폐기" and not refs:
            errors.append(f"{row['ID']}: 연결된 요구사항이 없습니다")
        for ref in refs:
            if ref not in index:
                errors.append(f"{row['ID']}: 원장에 없는 요구사항 {ref[0]}:{ref[1]}")
            if row["상태"] != "폐기":
                assignments[ref].append(row["ID"])
    unassigned = []
    for key, item in index.items():
        if item["status"] != "⬜":
            continue
        owners = assignments[key]
        if not owners:
            unassigned.append({"domain": key[0], "id": key[1]})
            errors.append(f"미배정 요구사항: {key[0]}:{key[1]}")
        elif len(owners) > 1:
            errors.append(f"중복 배정: {key[0]}:{key[1]} → {', '.join(owners)}")
    ready, blocked, partial, discard, done, progress = [], [], [], [], [], []
    states = {row["ID"]: row["상태"] for row in rows}
    for row in rows:
        refs = refs_by_task[row["ID"]]
        values = [index[ref]["status"] for ref in refs if ref in index]
        if row["상태"] == "진행" and values and all(value == "✅" for value in values):
            progress.append(row["ID"])
        if row["상태"] != "대기" or not values:
            continue
        retired = [f"{ref[0]}:{ref[1]}" for ref in refs if ref in index and index[ref]["status"] == "🚫"]
        if retired:
            if len(retired) == len(refs):
                discard.append(row["ID"])
            else:
                partial.append({"id": row["ID"], "requirements": retired})
            continue
        if all(value == "✅" for value in values):
            done.append(row["ID"])
            continue
        dependencies = [value.strip() for value in re.split(r"[,·]", row["의존"])
                        if value.strip() not in ("", "-")]
        waiting = [value for value in dependencies if states.get(value) != "완료"]
        if waiting:
            blocked.append({"id": row["ID"], "dependencies": waiting})
        else:
            ready.append(row["ID"])
    return {"errors": errors, "unassigned": unassigned,
            "partial-discards": partial, "discard-candidates": discard,
            "done-candidates": done, "progress-review": progress,
            "ready": [] if errors else ready, "blocked": blocked}


def inspect_project(project_root, plan_path=None):
    root = Path(project_root)
    plan_path = Path(plan_path) if plan_path else root / ".dev/plan.md"
    rows = parse(plan_path)
    ledger = []
    for path in sorted((root / "context").glob("*/status.md")):
        items = parse_table(path.read_text(encoding="utf-8"), LEDGER_HEADER, allow_empty=True)
        ledger.extend({"domain": path.parent.name, "id": row["ID"],
                       "text": row["요구사항"], "status": row["상태"]} for row in items)
    return analyze(rows, ledger)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    try:
        result = inspect_project(args.project_root, args.plan)
    except (OSError, ValueError) as exc:
        result = {"errors": [str(exc)], "ready": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
