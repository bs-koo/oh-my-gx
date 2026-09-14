#!/usr/bin/env bash
# Render or install Codex hooks through the JSON-safe Python CLI.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for candidate in python3 python; do
  if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    exec "$candidate" "$SCRIPT_DIR/codex-install-hooks.py" "$@"
  fi
done
echo 'Python 3.10 이상이 필요합니다.' >&2
exit 2
