#!/usr/bin/env bash
# 훅 페이로드 캡처 프로브 — Codex 훅 입력의 필드 구조를 실측하기 위한 투명 래퍼.
#
# 실측 항목 1(.claude/rules/harness-codex.md): Codex의 `exec_command` 호출 시 훅 입력의
# `tool_input`이 Claude Code와 동일하게 `command` 필드를 갖는가. pre-tool-guard.sh는
# 그 추출에 실패하면 입력 전체를 검사 대상으로 폴백하므로, 구조가 다르면 무관한 명령이
# 차단되는 오탐이 난다.
#
# 이 스크립트는 페이로드를 로그에 적은 뒤 **가드에 그대로 넘기고 가드의 판정을 돌려준다.**
# 별도의 통과용 훅을 끼우면 캡처하는 동안 보호가 사라지므로 그렇게 하지 않는다.
#
# 사용법:
#   1. hooks.json의 PreToolUse command를 이 스크립트로 바꾼다:
#        scripts/codex-install-hooks.sh --write <경로>   로 만든 뒤 pre-tool-guard.sh →
#        codex-probe-hook.sh 로 손으로 바꾸는 것이 가장 짧다.
#   2. Codex 세션에서 아무 셸 명령이나 몇 번 실행한다.
#   3. scripts/codex-probe-hook.sh --show 로 캡처된 구조를 본다.
#   4. 확인이 끝나면 hooks.json을 원래 가드로 되돌린다.
#
# 로그 경로: $GX_PROBE_LOG (기본 .dev/codex-probe.jsonl)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GUARD="$PLUGIN_ROOT/.claude/hooks/pre-tool-guard.sh"
LOG="${GX_PROBE_LOG:-$PLUGIN_ROOT/.dev/codex-probe.jsonl}"

if [ "${1:-}" = "--show" ]; then
  if [ ! -s "$LOG" ]; then
    echo "캡처된 페이로드가 없다: $LOG" >&2
    exit 1
  fi
  echo "로그: $LOG ($(wc -l < "$LOG" | tr -d ' ')건)"
  # Windows 콘솔 기본 코드페이지(cp949)에서 한국어·em dash 출력이 깨진다.
  PYTHONIOENCODING=utf-8 python3 - "$LOG" <<'PY'
import json, sys
from collections import Counter
top, inner, tools = Counter(), Counter(), Counter()
missing = 0
rows = 0
for line in open(sys.argv[1], encoding='utf-8'):
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except ValueError:
        continue
    rows += 1
    payload = rec.get('payload')
    if not isinstance(payload, dict):
        continue
    top.update(payload.keys())
    tools[payload.get('tool_name', '(없음)')] += 1
    ti = payload.get('tool_input')
    if isinstance(ti, dict):
        inner.update(ti.keys())
        if 'command' not in ti:
            missing += 1
    else:
        missing += 1
print('레코드: %d건' % rows)
print('최상위 키: %s' % ', '.join('%s(%d)' % kv for kv in top.most_common()))
print('tool_input 키: %s' % (', '.join('%s(%d)' % kv for kv in inner.most_common()) or '(없음)'))
print('tool_name 값: %s' % ', '.join('%s(%d)' % kv for kv in tools.most_common()))
if missing:
    print('경고: tool_input.command가 없는 레코드 %d건 — 가드가 입력 전체로 폴백해 오탐한다.' % missing)
    print('      pre-tool-guard.sh의 추출부를 Codex 필드명에 맞게 넓힐 것.')
else:
    print('tool_input.command 전 레코드 존재 — Claude Code와 같은 구조. 가드 수정 불필요.')
PY
  exit 0
fi

INPUT=$(cat 2>/dev/null || echo '{}')

# 기록 실패가 도구 실행을 막지 않도록 모든 실패를 흘린다 — 판정은 가드가 낸다.
{
  mkdir -p "$(dirname "$LOG")" 2>/dev/null
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$INPUT" | python3 -c '
import json, sys, datetime
raw = sys.stdin.read()
try:
    payload = json.loads(raw)
except ValueError:
    payload = None
rec = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "payload": payload}
if payload is None:
    rec["raw"] = raw[:4000]
print(json.dumps(rec, ensure_ascii=False))
' >> "$LOG"
  else
    printf '{"at":"%s","raw":%s}\n' "$(date -Iseconds 2>/dev/null)" "$(printf '%s' "$INPUT" | sed 's/\/\\/g; s/"/\\"/g; s/^/"/; s/$/"/')" >> "$LOG"
  fi
} 2>/dev/null || true

printf '%s' "$INPUT" | bash "$GUARD"
exit $?
