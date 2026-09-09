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

echo "[T8] 인자 검증 — 모르는 시나리오는 usage 에러"
bash "$RUNNER" B9 >/dev/null 2>&1; assert "B9 → exit 2" 2 "$?"

echo
echo "결과: $PASS pass, $FAIL fail"
[ "$FAIL" -eq 0 ] || exit 1
