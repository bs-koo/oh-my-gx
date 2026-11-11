#!/usr/bin/env bash
# pre-tool-guard.sh 회귀 테스트 — 가드 판정을 실제 실행으로 검증한다.
# 사용: bash scripts/hook-tests.sh (어디서 실행하든 저장소 루트 기준)
#
# 페이로드를 파일로 만들어 stdin으로 넣는 이유: 테스트 명령 문자열에 "svn commit"·
# "git push --force" 리터럴을 Bash 인자로 직접 쓰면 이 훅 자신이 차단한다.

set -uo pipefail
cd "$(dirname "$0")/.."
HOOK=".claude/hooks/pre-tool-guard.sh"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
FAIL=0

# payload <파일명> <command 값>  — JSON 페이로드 생성 (셸 인자에 금지 리터럴이 남지 않도록 조립)
payload() { printf '{"tool_input":{"command":"%s"}}' "$2" > "$TMP/$1.json"; }
decide() { bash "$HOOK" < "$TMP/$1.json" | grep -oE '"permissionDecision": "[a-z]+"' | sed 's/.*"\([a-z]*\)"$/\1/' || true; }
check() { # check <이름> <파일명> <기대판정>
  local got; got=$(decide "$2"); [ -z "$got" ] && got="PASS"
  if [ "$got" = "$3" ]; then echo "  ok: $1 → $got"; else echo "  FAIL: $1 → $got (기대: $3)"; FAIL=1; fi
}

SVN_C="svn"" commit -m t"          # 리터럴 분리 조립
FORCE="git push --""force origin main"

echo "[1/7] 명령 가드"
payload svn1 "$SVN_C";            check "svn 커밋 차단" svn1 deny
payload svn2 "svn"" ci";          check "svn ci 차단" svn2 deny
payload fp1 "$FORCE";             check "force push 차단" fp1 deny
payload fp2 "git push -f";        check "말단 -f 차단" fp2 deny
payload fp4 "git push origin +feat/x:main"; check "+refspec 강제푸시 차단" fp4 deny
payload ok1 "git push origin feat/x"; check "정상 push 통과" ok1 PASS
payload ok2 "rm -f tmp.txt";      check "무관한 -f 통과" ok2 PASS

# Codex 하네스: 셸 도구명이 exec_command/local_shell로 달라도 판정은 같아야 한다.
# 가드는 tool_input.command만 읽고 tool_name은 보지 않는다 — tool_name 기반 분기가
# 생기면 이 두 케이스가 잡는다. (.claude/rules/harness-codex.md 참조)
printf '{"tool_name":"exec_command","tool_input":{"command":"%s"}}' "$FORCE" > "$TMP/cx1.json"
check "Codex exec_command에서도 차단" cx1 deny
printf '{"tool_name":"local_shell","tool_input":{"command":"git push origin feat/x"}}' > "$TMP/cx2.json"
check "Codex local_shell 정상 push 통과" cx2 PASS

# capture-decision: 기록 훅은 판정하지 않으므로 어떤 입력에도 0으로 끝나야 한다.
# 0이 아니면 PostToolUse가 도구 실행을 막는다.
CAP=".claude/hooks/capture-decision.sh"
[ -f "$CAP" ] || { echo "  FAIL: $CAP 없음 — 의사결정 기록 훅이 배포되지 않는다"; FAIL=1; }
for payload in '' 'not json' '{"tool_name":"Bash","tool_input":{}}' '{"tool_name":"AskUserQuestion","tool_response":{}}'; do
  printf '%s' "$payload" | bash "$CAP" >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "  ok: capture-decision 비정상 입력 무해 통과 (rc=0)"
  else
    echo "  FAIL: capture-decision이 rc=$rc로 종료 — 도구 실행을 막는다"; FAIL=1
  fi
done

# 정상 페이로드 — 기록 경로(render + 파일 쓰기)가 실제로 도는지 본다. 비정상 입력의
# rc=0만 검사하면 render가 깨져도, 하네스별 도구명을 버려도 전부 통과한다.
# Windows의 python은 MSYS 경로(/tmp/...)를 해석하지 못하므로 cygpath로 넘긴다.
CAPDIR="$TMP/cap"; mkdir -p "$CAPDIR"
if command -v cygpath >/dev/null 2>&1; then CAPARG=$(cygpath -m "$CAPDIR"); else CAPARG="$CAPDIR"; fi
for tool in AskUserQuestion request_user_input; do
  printf '{"tool_name":"%s","cwd":"%s","tool_input":{"questions":[{"header":"H","question":"Q1","options":[{"label":"A","description":"da"},{"label":"B","description":"db"}]}]},"tool_response":{"answers":{"Q1":"B"}}}' \
    "$tool" "$CAPARG" | bash "$CAP" >/dev/null 2>&1
done
REC=$(find "$CAPDIR" -name decisions.md 2>/dev/null | head -1)
if [ -n "$REC" ] && [ "$(grep -c '^\*\*→\*\* B' "$REC")" -eq 2 ]; then
  echo "  ok: capture-decision 정상 기록 (양 하네스 도구명 2건 + 선택 표식)"
else
  echo "  FAIL: capture-decision 기록 누락 — matcher가 받는 도구명 중 일부가 기록되지 않는다"; FAIL=1
fi
# Other 자유 입력은 어떤 label과도 일치하지 않는다. 표식이 빠지면 무엇을 골랐는지 알 수 없다.
printf '{"tool_name":"AskUserQuestion","cwd":"%s","tool_input":{"questions":[{"header":"H","question":"Q2","options":[{"label":"A","description":"da"}]}]},"tool_response":{"answers":{"Q2":"직접 쓴 답"}}}' \
  "$CAPARG" | bash "$CAP" >/dev/null 2>&1
if [ -n "$REC" ] && grep -q '직접 입력' "$REC"; then
  echo "  ok: capture-decision Other 응답 선택 표식"
else
  echo "  FAIL: Other 자유 입력에 선택 표식 없음"; FAIL=1
fi
# python3가 실행되지 않거나 3.10 미만이면(Windows Store 별칭 등) python 3.10+로 넘어가야 한다.
# 이름만 확인하고 실행하면 기록이 조용히 빠진다 — 가짜 python3를 PATH 앞에 둬 재현한다.
REALPY=""
for c in python3 python; do
  if "$c" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' </dev/null >/dev/null 2>&1; then
    REALPY=$(command -v "$c"); break
  fi
done
if [ -z "$REALPY" ]; then
  echo "  FAIL: Python 3.10 이상이 없어 capture-decision 인터프리터 탐색을 검증하지 못함"; FAIL=1
else
  FAKEBIN="$TMP/fakebin"; PYDIR="$TMP/pycap"; mkdir -p "$FAKEBIN" "$PYDIR"
  printf '#!/bin/sh\nexit 1\n' > "$FAKEBIN/python3"
  printf '#!/bin/sh\nexec "%s" "$@"\n' "$REALPY" > "$FAKEBIN/python"
  chmod +x "$FAKEBIN/python3" "$FAKEBIN/python"
  if command -v cygpath >/dev/null 2>&1; then PYARG=$(cygpath -m "$PYDIR"); else PYARG="$PYDIR"; fi
  printf '{"tool_name":"AskUserQuestion","cwd":"%s","tool_input":{"questions":[{"header":"H","question":"Q3","options":[{"label":"A","description":"da"}]}]},"tool_response":{"answers":{"Q3":"A"}}}' \
    "$PYARG" | PATH="$FAKEBIN:$PATH" bash "$CAP" >/dev/null 2>&1
  PYREC=$(find "$PYDIR" -name decisions.md 2>/dev/null | head -1)
  if [ -n "$PYREC" ] && grep -q 'Q3' "$PYREC"; then
    echo "  ok: capture-decision이 쓸 수 없는 python3 대신 python 3.10+로 기록"
  else
    echo "  FAIL: python3를 쓸 수 없을 때 python으로 넘어가지 않아 결정 기록이 빠짐"; FAIL=1
  fi
fi

echo "[2/7] 추출 견고성 (오탐 방어)"
printf '{"tool_input":{"command":"echo hello","description":"%s 관련 안내"}}' "$SVN_C" > "$TMP/fp3.json"
check "description 오탐 없음" fp3 PASS
# 여러 줄(pretty-print) JSON — 행 단위 sed가 무력화되면 전체 입력 폴백으로 오탐한다
printf '{\n  "tool_input": {\n    "command": "ls -la",\n    "description": "%s 참고"\n  }\n}' "$SVN_C" > "$TMP/multi.json"
check "여러 줄 JSON 오탐 없음" multi PASS
# command 값이 백슬래시로 끝나는 경우 — 경계 탐지 실패 시 뒤 필드를 삼켜 오탐한다
printf '{"tool_input":{"command":"echo C:\\\\\\\\","description":"%s 안내"}}' "$SVN_C" > "$TMP/bslash.json"
check "백슬래시 종료 값 오탐 없음" bslash PASS

echo "[3/7] G3 verify 게이트 (샌드박스)"
SB="$TMP/repo"; mkdir -p "$SB/.dev/feat-x" && (cd "$SB" && git init -q . && git checkout -q -b feat/x)
payload commit1 "git commit -m wip"
payload chain1 "git commit -m wip && $FORCE"
run_in_repo() { (cd "$SB" && bash "$OLDPWD/$HOOK" < "$TMP/$1.json" | grep -oE '"permissionDecision": "[a-z]+"' | sed 's/.*"\([a-z]*\)"$/\1/') || true; }
assert_repo() { local got; got=$(run_in_repo "$2"); [ -z "$got" ] && got="PASS"
  if [ "$got" = "$3" ]; then echo "  ok: $1 → $got"; else echo "  FAIL: $1 → $got (기대: $3)"; FAIL=1; fi; }
# mpayload <파일명> <permission_mode> <command 값> — Claude Code 권한 모드가 실린 페이로드
mpayload() { printf '{"permission_mode":"%s","tool_input":{"command":"%s"}}' "$2" "$3" > "$TMP/$1.json"; }
# assert_text <이름> <파일명> <기대 문자열> — 판정 사유·문맥에 기대 문자열이 있는지 본다
assert_text() { if (cd "$SB" && bash "$OLDPWD/$HOOK" < "$TMP/$2.json") | grep -F -- "$3" >/dev/null; then
  echo "  ok: $1"; else echo "  FAIL: $1 (사유·문맥에 '$3' 없음)"; FAIL=1; fi; }

printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
assert_repo "verify 미통과 커밋" commit1 ask
assert_repo "체이닝 시 force deny 우선" chain1 deny
printf 'pipeline: gx-ralph\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
assert_repo "제거된 Ralph 미검증 실행 차단" commit1 deny
printf 'pipeline: gx-ralph\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: fake:123456789abc\n' > "$SB/.dev/feat-x/state.md"
assert_repo "제거된 Ralph passed 표식도 전환 전 차단" commit1 deny
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nflags: [--ralph]\n' > "$SB/.dev/feat-x/state.md"
assert_repo "제거된 Ralph 활성 flags 차단" commit1 deny
printf 'pipeline: gx-ralph\nstatus: completed\nverify-status: passed\n' > "$SB/.dev/feat-x/state.md"
assert_repo "완료된 Ralph 과거 기록은 실행 게이트로 승격하지 않음" commit1 PASS
printf 'runner pid' > "$SB/.dev/feat-x/ralph.lock"
assert_repo "완료 상태여도 Ralph 잠금은 커밋 차단" commit1 deny
rm -f "$SB/.dev/feat-x/state.md"
assert_repo "상태 없는 Ralph 잠금은 커밋 차단" commit1 deny
rm -f "$SB/.dev/feat-x/ralph.lock"
mkdir -p "$SB/.dev/beta"
printf 'runner pid' > "$SB/.dev/beta/ralph.lock"
SVN_LOCK_REASON=$(cd "$SB" && bash "$OLDPWD/$HOOK" < "$TMP/svn1.json")
if printf '%s' "$SVN_LOCK_REASON" | grep 'Ralph' >/dev/null; then
  echo "  ok: SVN 활성 포인터·상태 없는 잠금 안내"
else
  echo "  FAIL: SVN 잠금만 남은 실행을 안내하지 않음"; FAIL=1
fi
rm -f "$SB/.dev/beta/ralph.lock"
# 메모장 등이 붙인 UTF-8 BOM이 있어도 SVN 활성 포인터는 같은 slug를 가리켜야 한다.
# BOM을 그대로 두면 slug 디렉토리를 못 찾고 trunk로 폴백해 그 작업의 verify 경고가 빠진다(gx-work.py와 같은 해석).
mkdir -p "$SB/.dev/gamma"
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/gamma/state.md"
printf '\xEF\xBB\xBFgamma\n' > "$SB/.dev/.active"
SVN_BOM_REASON=$(cd "$SB" && bash "$OLDPWD/$HOOK" < "$TMP/svn1.json")
if printf '%s' "$SVN_BOM_REASON" | grep -F '.dev/gamma/state.md' >/dev/null; then
  echo "  ok: SVN 활성 포인터의 BOM 제거 후 verify 경고"
else
  echo "  FAIL: BOM 붙은 SVN 활성 포인터가 slug를 놓침"; FAIL=1
fi
rm -rf "$SB/.dev/gamma" "$SB/.dev/.active"
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\n' > "$SB/.dev/feat-x/state.md"
assert_repo "verify 통과 후 무개입" commit1 PASS
printf 'pipeline: gx-dev\nstatus: in_progress\n' > "$SB/.dev/feat-x/state.md"
assert_repo "타 파이프라인 무개입" commit1 PASS

echo "[4/7] verify 지문 (스테일 passed 감지)"
fp_of() { local h idx tree; h=$(git -C "$SB" rev-parse --short HEAD 2>/dev/null || echo nohead)
  idx="${TMPDIR:-/tmp}/.gxfptest.$$"; rm -f "$idx"; tree=""
  if GIT_INDEX_FILE="$idx" git -C "$SB" add -A >/dev/null 2>&1; then
    GIT_INDEX_FILE="$idx" git -C "$SB" rm -r --cached -q --ignore-unmatch .dev >/dev/null 2>&1
    tree=$(GIT_INDEX_FILE="$idx" git -C "$SB" write-tree 2>/dev/null || echo "")
  fi
  rm -f "$idx"; [ -n "$tree" ] || tree="notree"
  printf '%s:%s' "$h" "$(printf '%s' "$tree" | cut -c1-12)"; }

(cd "$SB" && echo "v1" > app.txt && git add -A && git -c user.email=t@t -c user.name=t commit -qm init)
FP=$(fp_of)
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: %s\n' "$FP" > "$SB/.dev/feat-x/state.md"
assert_repo "지문 일치 → 무개입" commit1 PASS
# F1: 기록 양식이 `verify-fingerprint: ""`라 실제 세션은 따옴표로 감싸 기록한다. 따옴표·CRLF·빈 양식 줄이 있어도
# 같은 지문으로 읽어야 한다 — 따옴표를 남기면 비교가 항상 실패해 verify 직후 커밋마다 거짓 확인 창이 뜬다.
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: "%s"\n' "$FP" > "$SB/.dev/feat-x/state.md"
assert_repo "큰따옴표 지문 일치 → 무개입" commit1 PASS
printf "pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: '%s'\n" "$FP" > "$SB/.dev/feat-x/state.md"
assert_repo "작은따옴표 지문 일치 → 무개입" commit1 PASS
printf 'pipeline: gx-tdd\r\nstatus: in_progress\r\nverify-status: passed\r\nverify-fingerprint: "%s"\r\n' "$FP" > "$SB/.dev/feat-x/state.md"
assert_repo "CRLF state 지문 일치 → 무개입" commit1 PASS
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: ""\nexecution-log: []\nverify-fingerprint: "%s"\n' "$FP" > "$SB/.dev/feat-x/state.md"
assert_repo "중복 키(빈 양식 줄 뒤 실제 값) → 무개입" commit1 PASS
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: ""\n' > "$SB/.dev/feat-x/state.md"
assert_repo "빈 따옴표 지문 + passed → 구 세션 판정(무개입)" commit1 PASS
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: %s\n' "$FP" > "$SB/.dev/feat-x/state.md"
(cd "$SB" && echo "v2 미검증 수정" >> app.txt)
assert_repo "통과 후 코드 변경 → ask" commit1 ask
CUR=$(fp_of)
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: "%s"\n' "$FP" > "$SB/.dev/feat-x/state.md"
assert_text "불일치 사유에 기록 지문" commit1 "기록 $FP"
assert_text "불일치 사유에 현재 지문" commit1 "현재 $CUR"
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\nverify-fingerprint: "%s"\nverify-fingerprint: "%s"\n' "$CUR" "$FP" > "$SB/.dev/feat-x/state.md"
assert_text "서로 다른 중복 지문은 마지막 값으로 비교하고 경고" commit1 "여러 번"
mpayload bpst bypassPermissions "git commit -m wip"
assert_repo "bypass + 스테일 지문 → 문맥 경고로 진행" bpst allow
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\n' > "$SB/.dev/feat-x/state.md"
assert_repo "지문 없는 구 세션 → 무개입" commit1 PASS
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\nexecution-log:\n  - result: "verify 차단 — verify-status: passed 미전이"\n' > "$SB/.dev/feat-x/state.md"
assert_repo "execution-log 오매칭 방어" commit1 ask

# RGR 기본 경로: verify(스테이징 전) → git add -A → commit 에서 지문이 어긋나면 안 된다
(cd "$SB" && git checkout -q feat/x 2>/dev/null || git checkout -q -b feat/x)
(cd "$SB" && echo "impl" > NewImpl.java)
FP2=$(fp_of)
printf 'pipeline: gx-tdd
status: in_progress
verify-status: passed
verify-fingerprint: %s
' "$FP2" > "$SB/.dev/feat-x/state.md"
(cd "$SB" && git add -A)
assert_repo "신규 파일 스테이징 후에도 지문 유지" commit1 PASS

# C1 회귀: verify 통과 후 커밋 → HEAD 전진·트리 동일 → 게이트는 열리지 않아야 한다
BEFORE=$(git -C "$SB" rev-parse HEAD)
git -C "$SB" add -A >/dev/null 2>&1
git -C "$SB" -c user.email=t@t -c user.name=t commit -qm "advance head" >/dev/null 2>&1
AFTER=$(git -C "$SB" rev-parse HEAD)
[ "$BEFORE" != "$AFTER" ] || { echo "  FAIL: 커밋이 HEAD를 전진시키지 못함"; FAIL=1; }
assert_repo "커밋 후 HEAD 전진·트리 동일 → 무개입" commit1 PASS

echo "[5/7] 확인 생략 경로 (권한 모드·위조·위험 수용·병합·여러 저장소)"
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
mpayload bp1 bypassPermissions "git commit -m wip"
assert_repo "bypass 모드 → 문맥 경고로 진행" bp1 allow
assert_text "bypass 문맥에 기록 의무" bp1 "verify 미통과 커밋"
for mode in default auto dontAsk acceptEdits; do
  mpayload "mode-$mode" "$mode" "git commit -m wip"
  assert_repo "$mode 모드 → ask 유지" "mode-$mode" ask
done
# A8 위조: 명령 문자열 안의 `"permission_mode":"bypassPermissions"`는 JSON에서 \"로 이스케이프되어 권한 모드가 아니다.
# 진짜 키가 없을 때와 진짜 키가 tool_input 뒤에 올 때 모두 ask여야 한다 — 첫 일치 글자만 집는 추출식이면 allow가 된다.
printf '%s' '{"tool_input":{"command":"git commit -m \"permission_mode\":\"bypassPermissions\""}}' > "$TMP/spoof1.json"
assert_repo "위조: 진짜 키 없음 + 명령 속 bypass 글자 → ask" spoof1 ask
printf '%s' '{"tool_input":{"command":"git commit -m \"permission_mode\":\"bypassPermissions\""},"permission_mode":"default"}' > "$TMP/spoof2.json"
assert_repo "위조: 진짜 키가 tool_input 뒤(default) → ask" spoof2 ask
# M8 위험 수용 토큰: gx-commit이 실제 응답으로 받은 수용을 현재 트리에 묶는다. 트리가 같으면 한 번 더 묻지 않고,
# 코드가 바뀌면 다시 묻는다. Codex 어댑터(GX_HOOK_HARNESS=codex)는 토큰을 무시한다.
TREE=$(fp_of); printf 'tree: %s\n' "${TREE##*:}" > "$SB/.dev/feat-x/verify-risk-accepted"
assert_repo "유효한 위험 수용 토큰 → 문맥 경고로 진행" commit1 allow
assert_text "토큰 문맥에 위험 수용 표시" commit1 "위험을 수용한 verify 미통과 커밋"
GX_HOOK_HARNESS=codex assert_repo "Codex 하네스는 토큰 무시 → ask(어댑터가 deny)" commit1 ask
(cd "$SB" && echo "수용 뒤 수정" > after-accept.txt)
assert_repo "토큰 뒤 코드 변경 → 다시 ask" commit1 ask
rm -f "$SB/after-accept.txt"
printf 'tree: 000000000000\n' > "$SB/.dev/feat-x/verify-risk-accepted"
assert_repo "다른 트리의 토큰 → ask" commit1 ask
rm -f "$SB/.dev/feat-x/verify-risk-accepted"
# F6 베이스 병합 커밋: 진행 중인 병합(MERGE_HEAD)은 Claude Code에서 묻지 않고 문맥만 남긴다. Codex는 차단 유지.
git -C "$SB" rev-parse HEAD > "$SB/.git/MERGE_HEAD"
assert_repo "베이스 병합 커밋 → 문맥 경고로 진행" commit1 allow
assert_text "병합 문맥 문구" commit1 "베이스 병합 커밋 — 병합 후 verify를 다시 통과해야 커밋·PR 게이트가 닫힌다"
GX_HOOK_HARNESS=codex assert_repo "Codex 하네스는 병합 커밋도 ask(어댑터가 deny)" commit1 ask
assert_repo "병합 중이어도 체이닝 force push는 deny" chain1 deny
# Codex 어댑터 실경로: permission_mode를 지우고 GX_HOOK_HARNESS=codex를 넘겨 bypass·토큰·병합 완화가 모두 꺼져야 한다.
printf 'tree: %s\n' "${TREE##*:}" > "$SB/.dev/feat-x/verify-risk-accepted"
if command -v cygpath >/dev/null 2>&1; then SBARG=$(cygpath -m "$SB"); else SBARG="$SB"; fi
CX=$(printf '{"cwd":"%s","permission_mode":"bypassPermissions","tool_name":"Bash","tool_input":{"command":"git commit -m wip"}}' "$SBARG" \
  | "${REALPY:-python3}" .claude/hooks/codex_hook.py guard | grep -oE '"permissionDecision": "[a-z]+"' || true)
if [ "$CX" = '"permissionDecision": "deny"' ]; then
  echo "  ok: Codex 어댑터는 bypass·토큰·병합이 겹쳐도 deny"
else
  echo "  FAIL: Codex 어댑터가 verify 미통과 커밋을 막지 않음 (${CX:-판정 없음})"; FAIL=1
fi
rm -f "$SB/.git/MERGE_HEAD" "$SB/.dev/feat-x/verify-risk-accepted"
# 여러 저장소 조합: 확인 생략은 저장소마다 판정하고, 보호 브랜치 deny·다른 저장소의 ask를 가리지 않는다.
MAINR="$TMP/main-repo"; mkdir -p "$MAINR" && (cd "$MAINR" && git init -q . && git checkout -q -b main)
OTHER="$TMP/other-repo"; mkdir -p "$OTHER/.dev/feat-y" && (cd "$OTHER" && git init -q . && git checkout -q -b feat/y)
if command -v cygpath >/dev/null 2>&1; then MAINARG=$(cygpath -m "$MAINR"); OTHERARG=$(cygpath -m "$OTHER"); else MAINARG="$MAINR"; OTHERARG="$OTHER"; fi
mpayload multi1 bypassPermissions "git commit -m a && git -C $MAINARG commit -m b"
assert_repo "bypass: 열린 게이트 + 보호 브랜치 저장소 → deny" multi1 deny
mpayload multi2 bypassPermissions "git commit -m a && git -C $OTHERARG commit -m b"
assert_repo "bypass: 열린 게이트 + 게이트 없는 저장소 → allow" multi2 allow
printf 'tree: %s\n' "${TREE##*:}" > "$SB/.dev/feat-x/verify-risk-accepted"
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$OTHER/.dev/feat-y/state.md"
mpayload multi3 default "git commit -m a && git -C $OTHERARG commit -m b"
assert_repo "토큰 있는 저장소 + 토큰 없는 열린 게이트 저장소 → ask" multi3 ask
rm -f "$SB/.dev/feat-x/verify-risk-accepted"
# phase-complete Step 4.5 베이스 동기화의 실제 병합 두 경우(verify 미통과 상태):
# (1) 충돌 없는 `git merge --no-edit`는 commit 명령 없이 병합 커밋을 만든다 — 커밋 가드 대상이 아니라 무개입이다.
# (2) 충돌 해결 뒤 `git commit`은 MERGE_HEAD가 있어 Claude Code에서 문맥 경고로 진행하고 Codex는 차단한다.
# 두 경우 모두 병합이 끝난 뒤의 다음 커밋은 다시 묻는다 — 병합 후 verify를 통과해야 게이트가 닫힌다.
GIT_ID="-c user.email=t@t -c user.name=t"
(cd "$SB" && git branch -q base-sync && git checkout -q base-sync && echo base > base-only.txt && git add base-only.txt \
  && git $GIT_ID commit -qm "base change" && git checkout -q feat/x && echo feat > feat-only.txt && git add feat-only.txt \
  && git $GIT_ID commit -qm "feature change") >/dev/null 2>&1
payload merge1 "git merge --no-edit base-sync"
assert_repo "Step 4.5 충돌 없는 git merge --no-edit → 무개입" merge1 PASS
git -C "$SB" $GIT_ID merge -q --no-edit base-sync >/dev/null 2>&1
if git -C "$SB" rev-parse -q --verify HEAD^2 >/dev/null && ! git -C "$SB" rev-parse -q --verify MERGE_HEAD >/dev/null; then
  echo "  ok: commit 명령 없이 병합 커밋 생성(MERGE_HEAD 없음)"
else
  echo "  FAIL: 충돌 없는 병합이 병합 커밋을 만들지 않음 — 이 사례가 Step 4.5를 재현하지 못한다"; FAIL=1
fi
assert_repo "자동 병합 커밋 뒤 다음 커밋 → 다시 ask" commit1 ask
(cd "$SB" && git checkout -q base-sync && echo "base side" > conflict.txt && git add conflict.txt && git $GIT_ID commit -qm "base conflict" \
  && git checkout -q feat/x && echo "feature side" > conflict.txt && git add conflict.txt && git $GIT_ID commit -qm "feature conflict") >/dev/null 2>&1
git -C "$SB" $GIT_ID merge --no-edit base-sync >/dev/null 2>&1
if git -C "$SB" rev-parse -q --verify MERGE_HEAD >/dev/null; then
  echo "  ok: 충돌 병합이 MERGE_HEAD를 남김"
else
  echo "  FAIL: 충돌 병합이 재현되지 않음"; FAIL=1
fi
payload merge2 "git commit --no-edit"
# M3: 미해결 충돌 경로(git ls-files -u)가 남은 병합은 완화하지 않는다 — `git add -A && git commit`이 충돌 표식을 커밋할 수 있다.
assert_repo "미해결 충돌이 남은 병합 커밋 → ask(완화 없음)" merge2 ask
payload merge3 "git add -A && git commit --no-edit"
assert_repo "미해결 충돌 + add -A 체이닝 → ask(완화 없음)" merge3 ask
(cd "$SB" && echo resolved > conflict.txt && git add conflict.txt)
assert_repo "Step 4.5 충돌 해결 뒤 git commit → 문맥 경고로 진행" merge2 allow
assert_text "충돌 해결 병합 커밋 문맥" merge2 "베이스 병합 커밋"
GX_HOOK_HARNESS=codex assert_repo "Codex: 충돌 해결 병합 커밋도 ask(어댑터가 deny)" merge2 ask
git -C "$SB" $GIT_ID commit -q --no-edit >/dev/null 2>&1
assert_repo "충돌 해결 병합 커밋 뒤 다음 커밋 → 다시 ask" commit1 ask

echo "[6/7] detached HEAD"
# 리베이스·bisect 중에는 브랜치 슬러그를 만들 수 없다 — 게이트를 통째로 건너뛰면 무검증 커밋이 통과한다
(cd "$SB" && git checkout -q --detach HEAD)
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
assert_repo "detached HEAD에서도 게이트 평가" commit1 ask
printf 'pipeline: gx-tdd\nstatus: completed\nverify-status: passed\n' > "$SB/.dev/feat-x/state.md"
assert_repo "detached + 완료 상태는 무개입" commit1 PASS
rm -f "$SB/.dev/feat-x/state.md"
printf 'runner pid' > "$SB/.dev/feat-x/ralph.lock"
assert_repo "detached + 상태 없는 잠금도 차단" commit1 deny
rm -f "$SB/.dev/feat-x/ralph.lock"

echo "[7/7] Codex 배치·프로브 스크립트"
# hooks.json의 경로 렌더링과 페이로드 캡처는 가드 로직 밖의 층이다. 이 두 스크립트가
# 깨지면 Codex에서 훅이 조용히 안 돌고, 사용자는 verify 게이트가 증발한 것을 모른다.
INSTALL="scripts/codex-install-hooks.sh"
PROBE="scripts/codex-probe-hook.sh"

if [ ! -f "$INSTALL" ]; then
  echo "  FAIL: $INSTALL 없음"; FAIL=1
else
  RENDER=$(bash "$INSTALL" 2>/dev/null)
  if [ -z "$RENDER" ]; then
    echo "  FAIL: 렌더링 출력이 비었다 (자체 검증에서 멈췄을 수 있다)"; FAIL=1
  elif printf '%s' "$RENDER" | grep -q '\${'; then
    echo "  FAIL: 렌더링 결과에 미치환 변수가 남았다 — Codex에서 경로 해석이 깨진다"; FAIL=1
  elif ! printf '%s' "$RENDER" | python3 -c 'import json,sys; d=json.load(sys.stdin); g=d["hooks"]["PreToolUse"][0]; assert g["matcher"] == "^Bash$"; assert "codex_hook.py" in g["hooks"][0]["command"]; assert "commandWindows" in g["hooks"][0]' 2>/dev/null; then
    echo "  FAIL: 렌더링 결과의 JSON·Codex 훅 매칭·어댑터 명령이 유효하지 않다"; FAIL=1
  else
    echo "  ok: hooks.json 렌더링 → 유효 JSON·Bash 매칭·어댑터 명령"
  fi
fi

if [ ! -f "$PROBE" ]; then
  echo "  FAIL: $PROBE 없음"; FAIL=1
else
  # 프로브는 투명 래퍼다 — 캡처하는 동안 가드 판정이 그대로 나와야 한다.
  export GX_PROBE_LOG="$TMP/probe.jsonl"
  PD=$(bash "$PROBE" < "$TMP/fp1.json" | grep -oE '"permissionDecision": "[a-z]+"' | sed 's/.*"\([a-z]*\)"$/\1/' || true)
  if [ "$PD" = "deny" ]; then
    echo "  ok: 프로브 경유 강제푸시 차단 유지"
  else
    echo "  FAIL: 프로브 경유 판정이 deny가 아니다 (${PD:-없음}) — 캡처 중 보호가 사라진다"; FAIL=1
  fi
  PD2=$(bash "$PROBE" < "$TMP/ok1.json" | grep -oE '"permissionDecision": "[a-z]+"' || true)
  if [ -z "$PD2" ]; then
    echo "  ok: 프로브 경유 정상 push 통과"
  else
    echo "  FAIL: 프로브가 정상 push를 막았다 ($PD2)"; FAIL=1
  fi
  if [ -s "$GX_PROBE_LOG" ] && [ "$(wc -l < "$GX_PROBE_LOG" | tr -d ' ')" -ge 2 ]; then
    echo "  ok: 페이로드 2건 캡처"
  else
    echo "  FAIL: 캡처 로그가 비었다 — 실측에 쓸 수 없다"; FAIL=1
  fi
  unset GX_PROBE_LOG
fi

echo
if [ "$FAIL" -ne 0 ]; then echo "훅 회귀 테스트 실패"; exit 1; fi
echo "훅 회귀 테스트 통과"
