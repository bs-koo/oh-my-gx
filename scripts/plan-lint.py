#!/usr/bin/env python3
"""작업 계획(.dev/plan.md) 검증.

표 구조·의존 그래프를 확인한다. lint-consistency.sh는 grep/sed/diff만 쓰므로
그래프 순회가 필요한 검사는 이 스크립트로 분리한다.

사용:
    python3 scripts/plan-lint.py <plan.md 경로>

종료 코드:
    0  통과
    1  검증 실패 (사유를 stderr로 출력)
    2  파일을 읽을 수 없음
"""
import io
import re
import sys

# Windows 콘솔 기본 인코딩(cp949)에서는 일부 기호를 출력하지 못해 예외가 난다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

HEADER = ["ID", "작업", "도메인", "요구사항", "의존", "작업 위치", "상태"]
STATES = {"대기", "진행", "완료"}
ID_RE = re.compile(r"^W\d{2}$")


def parse(path):
    """plan.md를 읽어 행 리스트를 돌려준다. 형식 오류는 예외로 올린다."""
    try:
        text = io.open(path, encoding="utf-8").read()
    except OSError as exc:
        # docstring이 약속한 대로 2로 종료한다. SystemExit(str)은 1이 되어 "검증 실패"와 구분되지 않는다.
        print(f"FAIL {path}: 파일을 읽을 수 없습니다: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        raise ValueError("표를 찾지 못했습니다")

    def cells(line):
        return [c.strip() for c in line.strip("|").split("|")]

    head = cells(lines[0])
    if head != HEADER:
        raise ValueError(f"표 헤더가 규약과 다릅니다\n  기대: {HEADER}\n  실제: {head}")

    rows = []
    for line in lines[2:]:  # 0=헤더, 1=구분선
        c = cells(line)
        if len(c) != len(HEADER):
            raise ValueError(f"열 개수가 {len(HEADER)}가 아닙니다: {line}")
        rows.append(dict(zip(HEADER, c)))
    if not rows:
        raise ValueError("작업 행이 없습니다")
    return rows


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


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        rows = parse(sys.argv[1])
    except ValueError as exc:
        print(f"FAIL {sys.argv[1]}: {exc}", file=sys.stderr)
        return 1
    errors = check(rows)
    if errors:
        for e in errors:
            print(f"FAIL {sys.argv[1]}: {e}", file=sys.stderr)
        return 1
    print(f"ok: {sys.argv[1]} - 작업 {len(rows)}건, 형식·의존 정상")
    return 0


if __name__ == "__main__":
    sys.exit(main())
