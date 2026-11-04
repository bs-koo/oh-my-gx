#!/usr/bin/env python3
"""업무 계획표 lint 호환 진입점. 정본은 설치되는 gx-context/scripts/plan.py다."""
import importlib.util
from pathlib import Path
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

path = Path(__file__).resolve().parents[1] / ".claude/skills/gx-context/scripts/plan.py"
spec = importlib.util.spec_from_file_location("gx_context_plan", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HEADER, STATES, ID_RE = module.HEADER, module.STATES, module.ID_RE
parse, check = module.parse, module.check

def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        rows = parse(sys.argv[1])
    except OSError as exc:
        print(f"FAIL {sys.argv[1]}: 파일을 읽을 수 없습니다: {exc}", file=sys.stderr)
        return 2
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
