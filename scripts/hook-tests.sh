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

echo "[1/5] 명령 가드"
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

echo "[2/5] 추출 견고성 (오탐 방어)"
printf '{"tool_input":{"command":"echo hello","description":"%s 관련 안내"}}' "$SVN_C" > "$TMP/fp3.json"
check "description 오탐 없음" fp3 PASS
# 여러 줄(pretty-print) JSON — 행 단위 sed가 무력화되면 전체 입력 폴백으로 오탐한다
printf '{\n  "tool_input": {\n    "command": "ls -la",\n    "description": "%s 참고"\n  }\n}' "$SVN_C" > "$TMP/multi.json"
check "여러 줄 JSON 오탐 없음" multi PASS
# command 값이 백슬래시로 끝나는 경우 — 경계 탐지 실패 시 뒤 필드를 삼켜 오탐한다
printf '{"tool_input":{"command":"echo C:\\\\\\\\","description":"%s 안내"}}' "$SVN_C" > "$TMP/bslash.json"
check "백슬래시 종료 값 오탐 없음" bslash PASS

echo "[3/5] G3 verify 게이트 (샌드박스)"
SB="$TMP/repo"; mkdir -p "$SB/.dev/feat-x" && (cd "$SB" && git init -q . && git checkout -q -b feat/x)
payload commit1 "git commit -m wip"
payload chain1 "git commit -m wip && $FORCE"
run_in_repo() { (cd "$SB" && bash "$OLDPWD/$HOOK" < "$TMP/$1.json" | grep -oE '"permissionDecision": "[a-z]+"' | sed 's/.*"\([a-z]*\)"$/\1/') || true; }
assert_repo() { local got; got=$(run_in_repo "$2"); [ -z "$got" ] && got="PASS"
  if [ "$got" = "$3" ]; then echo "  ok: $1 → $got"; else echo "  FAIL: $1 → $got (기대: $3)"; FAIL=1; fi; }

printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
assert_repo "verify 미통과 커밋" commit1 ask
assert_repo "체이닝 시 force deny 우선" chain1 deny
printf 'pipeline: gx-ralph\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
assert_repo "gx-ralph 파이프라인 인식" commit1 ask
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: passed\n' > "$SB/.dev/feat-x/state.md"
assert_repo "verify 통과 후 무개입" commit1 PASS
printf 'pipeline: gx-dev\nstatus: in_progress\n' > "$SB/.dev/feat-x/state.md"
assert_repo "타 파이프라인 무개입" commit1 PASS

echo "[4/5] verify 지문 (스테일 passed 감지)"
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
(cd "$SB" && echo "v2 미검증 수정" >> app.txt)
assert_repo "통과 후 코드 변경 → ask" commit1 ask
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

echo "[5/5] detached HEAD"
# 리베이스·bisect 중에는 브랜치 슬러그를 만들 수 없다 — 게이트를 통째로 건너뛰면 무검증 커밋이 통과한다
(cd "$SB" && git checkout -q --detach HEAD)
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > "$SB/.dev/feat-x/state.md"
assert_repo "detached HEAD에서도 게이트 평가" commit1 ask
printf 'pipeline: gx-tdd\nstatus: completed\nverify-status: passed\n' > "$SB/.dev/feat-x/state.md"
assert_repo "detached + 완료 상태는 무개입" commit1 PASS

echo
if [ "$FAIL" -ne 0 ]; then echo "훅 회귀 테스트 실패"; exit 1; fi
echo "훅 회귀 테스트 통과"
