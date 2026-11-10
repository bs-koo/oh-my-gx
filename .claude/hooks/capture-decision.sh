#!/usr/bin/env bash
# AskUserQuestion 질문·답변을 .dev/{branch-slug}/decisions.md에 기록하는 PostToolUse 훅.
#
# jq를 쓰지 않는 이유: Git Bash 기본 환경에 jq가 없어 조용히 아무것도 하지 않는다
# (실측 2026-08-31).
#
# 인터프리터는 python3 → python 순서로 실제 실행해 3.10 이상인지 확인한다
# (scripts/codex-install-hooks.sh와 같은 방식). Windows의 python3는 Store 별칭이거나
# 3.10 미만일 수 있어 이름만 확인하면 기록이 조용히 빠진다. 버전 확인은 stdin을
# 막아 실행한다 — 훅 페이로드는 실제 기록 실행이 읽어야 한다.
#
# 기록은 판정이 아니므로 어떤 실패도 도구 실행을 막지 않는다 — 항상 0으로 끝낸다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for candidate in python3 python; do
  if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' </dev/null >/dev/null 2>&1; then
    "$candidate" "$SCRIPT_DIR/capture_decision.py" 2>/dev/null
    break
  fi
done

exit 0
