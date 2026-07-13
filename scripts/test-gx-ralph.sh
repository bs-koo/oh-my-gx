#!/usr/bin/env bash
# gx-ralph 러너 분기 테스트 — mock claude로 scripts/gx-ralph.sh의 종료 분기를 검증한다.
# 실행: bash scripts/test-gx-ralph.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/gx-ralph.sh"
PASS=0; FAIL=0

# ── mock claude: 시나리오 파일에서 한 줄씩 꺼내 동작을 재현한다 ──
make_mock() {
  local sandbox="$1"
  cat > "$sandbox/mock-claude.sh" <<'MOCK'
#!/usr/bin/env bash
step=$(head -1 "$GX_RALPH_MOCK_SCENARIO" 2>/dev/null || echo "")
# sed -i는 BSD sed(macOS)에서 에러가 삼켜져 시나리오가 소비되지 않음 — 임시 파일 사용
{ sed '1d' "$GX_RALPH_MOCK_SCENARIO" > "$GX_RALPH_MOCK_SCENARIO.tmp" && mv "$GX_RALPH_MOCK_SCENARIO.tmp" "$GX_RALPH_MOCK_SCENARIO"; } 2>/dev/null || true
case "$step" in
  CONTINUE_COMMIT)
    echo "x" >> work.txt && git add work.txt >/dev/null 2>&1 && git commit -q -m "feat: mock 구현 (AC-x)" >/dev/null 2>&1
    echo "<ralph>CONTINUE</ralph>" ;;
  CONTINUE_NOOP) echo "<ralph>CONTINUE</ralph>" ;;
  COMPLETE)      echo "<ralph>COMPLETE</ralph>" ;;
  BLOCKED)       echo "<ralph>BLOCKED: mock 사유</ralph>" ;;
  NOTHING)       echo "종료 계약 없이 끝나는 출력" ;;
  *)             echo "<ralph>BLOCKED: 시나리오 소진</ralph>" ;;
esac
MOCK
}

# ── 샌드박스: 작업 브랜치의 git repo + gx-ralph 상태 파일 일습 ──
make_sandbox() {
  local sandbox
  sandbox=$(mktemp -d)
  ( cd "$sandbox" \
    && git init -q -b feat/t \
    && git config user.email t@t.local && git config user.name t \
    && echo base > base.txt && git add base.txt && git commit -q -m "chore: base" \
    && mkdir -p .dev/feat-t \
    && printf 'pipeline: gx-ralph\nstatus: in_progress\nverify-status: pending\nbranch: feat/t\nmax-iterations: 10\nlast-known-head: none\n' > .dev/feat-t/state.md \
    && printf '{"version":1,"branch":"feat/t","created":"t","updated":"t","acs":[{"id":"AC-1","title":"t","passes":false,"attempts":0,"last_error":""}]}\n' > .dev/feat-t/ac-status.json \
    && printf '# gx-ralph progress\n' > .dev/feat-t/progress.txt )
  make_mock "$sandbox"
  echo "$sandbox"
}

# ── 실행 헬퍼: 러너를 mock과 함께 돌리고 exit code를 반환 ──
run_runner() {
  local sandbox="$1"; shift
  local scenario="$1"; shift
  local max_iter="${1:-}"
  printf '%s\n' $scenario > "$sandbox/scenario.txt"
  ( cd "$sandbox" \
    && GX_RALPH_CLAUDE_CMD="bash $sandbox/mock-claude.sh" \
       GX_RALPH_MOCK_SCENARIO="$sandbox/scenario.txt" \
       bash "$RUNNER" $max_iter >/dev/null 2>&1 )
  echo $?
}

assert() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ✅ $name (=$actual)"; PASS=$((PASS+1))
  else
    echo "  ❌ $name — 기대: $expected, 실제: $actual"; FAIL=$((FAIL+1))
  fi
}

iter_logs() { ls "$1"/.dev/feat-t/iter-*.log 2>/dev/null | wc -l | tr -d ' '; }

echo "[T1] COMPLETE 탈출: CONTINUE_COMMIT → COMPLETE"
SB=$(make_sandbox)
assert "exit=0" 0 "$(run_runner "$SB" "CONTINUE_COMMIT COMPLETE")"
assert "반복 2회" 2 "$(iter_logs "$SB")"
rm -rf "$SB"

echo "[T2] MAX_ITER 소진: 상한 3회"
SB=$(make_sandbox)
assert "exit=5" 5 "$(run_runner "$SB" "CONTINUE_COMMIT CONTINUE_COMMIT CONTINUE_COMMIT CONTINUE_COMMIT" 3)"
assert "반복 3회" 3 "$(iter_logs "$SB")"
rm -rf "$SB"

echo "[T3] NO_DRIFT: 무변화 2회 연속 → 중단"
SB=$(make_sandbox)
assert "exit=4" 4 "$(run_runner "$SB" "CONTINUE_NOOP CONTINUE_NOOP CONTINUE_NOOP")"
assert "반복 2회" 2 "$(iter_logs "$SB")"
rm -rf "$SB"

echo "[T4] BLOCKED: 반복 세션이 중단 선언"
SB=$(make_sandbox)
assert "exit=2" 2 "$(run_runner "$SB" "BLOCKED")"
assert "반복 1회" 1 "$(iter_logs "$SB")"
rm -rf "$SB"

echo "[T5] lock 존재 시 기동 거부"
SB=$(make_sandbox)
touch "$SB/.dev/feat-t/ralph.lock"
assert "exit=6" 6 "$(run_runner "$SB" "COMPLETE")"
assert "반복 0회" 0 "$(iter_logs "$SB")"
rm -rf "$SB"

echo "[T6] 종료 계약 미출력 → BLOCKED 취급"
SB=$(make_sandbox)
assert "exit=3" 3 "$(run_runner "$SB" "NOTHING")"
rm -rf "$SB"

echo "[T7] 보호 브랜치 기동 거부"
SB=$(make_sandbox)
( cd "$SB" && git checkout -q -b main )
assert "exit=6" 6 "$(run_runner "$SB" "COMPLETE")"
rm -rf "$SB"

echo "[T8] 재실행 시 이전 반복 로그 보존 (logs-*/ 아카이브)"
SB=$(make_sandbox)
assert "1차 exit=0" 0 "$(run_runner "$SB" "COMPLETE")"
assert "2차 exit=0" 0 "$(run_runner "$SB" "COMPLETE")"
assert "현재 실행 로그 1개" 1 "$(iter_logs "$SB")"
ARCHIVED=$(ls -d "$SB"/.dev/feat-t/logs-* 2>/dev/null | wc -l | tr -d ' ')
assert "아카이브 디렉토리 1개" 1 "$ARCHIVED"
rm -rf "$SB"

echo "[T9] COMPLETE 복귀 안내 origin 분기 (gx-tdd → /gx-tdd --phase review)"
SB=$(make_sandbox)
printf 'origin: gx-tdd\n' >> "$SB/.dev/feat-t/state.md"
printf '%s\n' COMPLETE > "$SB/scenario.txt"
OUT=$( cd "$SB" \
  && GX_RALPH_CLAUDE_CMD="bash $SB/mock-claude.sh" \
     GX_RALPH_MOCK_SCENARIO="$SB/scenario.txt" \
     bash "$RUNNER" 2>&1 )
case "$OUT" in
  *"/gx-tdd --phase review"*) assert "안내에 /gx-tdd 포함" 1 1 ;;
  *)                          assert "안내에 /gx-tdd 포함" 1 0 ;;
esac
rm -rf "$SB"

echo "[T10] CRLF state.md에서도 브랜치 검증·origin 분기 동작 (Windows 개행 방어)"
SB=$(make_sandbox)
printf 'pipeline: gx-ralph\r\nstatus: in_progress\r\nverify-status: pending\r\nbranch: feat/t\r\nmax-iterations: 10\r\nlast-known-head: none\r\norigin: gx-tdd\r\n' > "$SB/.dev/feat-t/state.md"
printf '%s\n' COMPLETE > "$SB/scenario.txt"
OUT=$( cd "$SB" \
  && GX_RALPH_CLAUDE_CMD="bash $SB/mock-claude.sh" \
     GX_RALPH_MOCK_SCENARIO="$SB/scenario.txt" \
     bash "$RUNNER" 2>&1 ); RC=$?
assert "exit=0 (CRLF 브랜치 비교)" 0 "$RC"
case "$OUT" in
  *"/gx-tdd --phase review"*) assert "origin 분기 (CRLF)" 1 1 ;;
  *)                          assert "origin 분기 (CRLF)" 1 0 ;;
esac
rm -rf "$SB"

echo
echo "결과: $PASS pass, $FAIL fail"
[ "$FAIL" -eq 0 ] || exit 1
