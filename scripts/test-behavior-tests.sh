#!/usr/bin/env bash
# behavior-tests.sh 자체 테스트 — mock claude로 프롬프트 추출·샌드박스·판정 로직을 검증한다.
# 실행: bash scripts/test-behavior-tests.sh  (실제 모델은 호출하지 않는다)
set -uo pipefail
cd "$(dirname "$0")/.."
RUNNER="scripts/behavior-tests.sh"
PASS=0; FAIL=0
assert() { # assert <이름> <기대> <실제>
  if [ "$2" = "$3" ]; then echo "  ok: $1"; PASS=$((PASS+1)); else echo "  FAIL: $1 (기대: $2, 실제: $3)"; FAIL=$((FAIL+1)); fi
}
# ── mock claude: 시나리오 키(GX_BEHAVIOR_MOCK)에 따라 샌드박스에 부작용을 남기고 stream-json을 출력한다 ──
make_mock() {
  cat > "$1/mock-claude.sh" <<'MOCK'
#!/usr/bin/env bash
# 인자와 프롬프트 길이를 기록한다 (프롬프트가 stdin으로 들어오는지 확인용)
printf '%s\n' "$*" >> "${GX_BEHAVIOR_MOCK_ARGS:-/dev/null}"
printf 'prompt-bytes=%s\n' "$(wc -c < /dev/stdin | tr -d ' ')" >> "${GX_BEHAVIOR_MOCK_ARGS:-/dev/null}"
ev()  { printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"%s","input":{"file_path":"%s"}}]}}\n' "$1" "$2"; }
res() { printf '{"type":"result","result":%s}\n' "$1"; }
write_failing_test() {
  cat > test/limit-max.test.js <<'JS'
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { checkLimit } = require('../src/limit');

test('1회 한도를 넘는 금액은 limit 사유로 거부한다', () => {
  assert.deepEqual(checkLimit(150000), { ok: false, reason: 'limit' });
});
JS
}
case "${GX_BEHAVIOR_MOCK:-}" in
  B1:pass|B1:peek)
    write_failing_test; mkdir -p reports
    printf '# RED report\n\n## 테스트 파일\ntest/limit-max.test.js (케이스 1건)\n\n## 참조한 파일\n- ac.md\n- test/limit.test.js\n' > reports/t1-red.md
    ev Read ac.md; ev Read test/limit.test.js; ev Write test/limit-max.test.js
    [ "$GX_BEHAVIOR_MOCK" = B1:peek ] && ev Read src/limit.js
    res '"- Status: DONE\n- 테스트 파일: test/limit-max.test.js\n- 실패 확인: node --test test/limit-max.test.js — 1건 assertion\n- 우려사항: 없음\n- report: reports/t1-red.md"' ;;
  *) echo "unknown mock scenario: ${GX_BEHAVIOR_MOCK:-}" >&2; exit 9 ;;
esac
MOCK
  chmod +x "$1/mock-claude.sh"
}
# run_mock <시나리오> <mock 키> — 러너를 mock으로 실행한다. 출력은 OUT, exit 코드는 RC에 담는다 (서브셸 없이 호출할 것 — `OUT=$(run_mock …)`로 감싸면 RC가 사라진다)
run_mock() {
  make_mock "$TMP"
  OUT=$(GX_BEHAVIOR_CLAUDE_CMD="bash $TMP/mock-claude.sh" GX_BEHAVIOR_MOCK="$2" GX_BEHAVIOR_MOCK_ARGS="$TMP/args.txt" bash "$RUNNER" "$1" 2>&1); RC=$?
}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

echo "[T1] 프롬프트 추출 — phase 파일의 Task 블록에서 prompt 본문이 나온다"
[ -f "$RUNNER" ] || { echo "  FAIL: $RUNNER 없음"; exit 1; }
GX_BEHAVIOR_SOURCE_ONLY=1 . "$RUNNER"
P=$(extract_prompt .claude/skills/gx-tdd/phases/phase-implement.md oh-my-gx:red-writer)
assert "red-writer 프롬프트에 [절대 규칙]" 1 "$(printf '%s' "$P" | grep -c '^\[절대 규칙\]')"
assert "red-writer 프롬프트에 [report 파일]" 1 "$(printf '%s' "$P" | grep -c '^\[report 파일\]')"
P=$(extract_prompt .claude/skills/gx-tdd/phases/phase-implement.md oh-my-gx:implementer)
assert "implementer 프롬프트에 [RED report]" 1 "$(printf '%s' "$P" | grep -c '^\[RED report\]')"
P=$(extract_prompt .claude/skills/gx-tdd/phases/phase-review.md oh-my-gx:reviewer)
assert "reviewer 프롬프트에 [Iron Law]" 1 "$(printf '%s' "$P" | grep -c '^\[Iron Law\]')"
assert "reviewer 프롬프트가 phase-review Task B(security)로 넘어가지 않음" 0 "$(printf '%s' "$P" | grep -c 'security_verdict')"

echo "[T1b] 플레이스홀더 치환 — 알려진 키는 값으로, 남은 한글 플레이스홀더는 없음으로"
printf '[X]\n{PROJECT_ROOT}\n{코드 맵}\n{reports/t{N}-red.md}\n' > "$TMP/p.txt"
printf '{"{PROJECT_ROOT}": ".", "{reports/t{N}-red.md}": "reports/t1-red.md"}' > "$TMP/s.json"
F=$(fill_prompt "$TMP/p.txt" "$TMP/s.json")
assert "PROJECT_ROOT 치환" 1 "$(printf '%s' "$F" | grep -c '^\.$')"
assert "중첩 플레이스홀더 치환" 1 "$(printf '%s' "$F" | grep -c '^reports/t1-red.md$')"
assert "미지정 한글 플레이스홀더 → 없음" 1 "$(printf '%s' "$F" | grep -c '^없음$')"

echo "[T2] B1 정상 — src/ 미열람 + 프로덕션 무변경 + 실패 테스트 작성이면 통과"
: > "$TMP/args.txt"
run_mock B1 B1:pass
assert "B1 pass → exit 0" 0 "$RC"
assert "src/ 열람 0회 판정" 1 "$(printf '%s' "$OUT" | grep -c 'B1 src/ 열람 0회')"
assert "실패 테스트 감지" 1 "$(printf '%s' "$OUT" | grep -c 'B1 실패 테스트 1건')"
assert "system prompt 파일 전달" 1 "$(grep -c -- '--append-system-prompt-file' "$TMP/args.txt")"
assert "프롬프트가 stdin으로 전달됨" 1 "$(grep -cE 'prompt-bytes=[1-9][0-9]{2,}' "$TMP/args.txt")"
assert "Bash(node \*)만 허용" 1 "$(grep -c 'Bash(node \*)' "$TMP/args.txt")"

echo "[T3] B1 격리 위반 — src/limit.js를 Read하면 실패"
run_mock B1 B1:peek
assert "B1 peek → exit 1" 1 "$RC"
assert "격리 위반 판정" 1 "$(printf '%s' "$OUT" | grep -c '격리 위반')"

echo "[T8] 인자 검증 — 모르는 시나리오는 usage 에러"
bash "$RUNNER" B9 >/dev/null 2>&1; assert "B9 → exit 2" 2 "$?"

echo
echo "결과: $PASS pass, $FAIL fail"
[ "$FAIL" -eq 0 ] || exit 1
