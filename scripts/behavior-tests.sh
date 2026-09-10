#!/usr/bin/env bash
# 프롬프트 계약 행동 테스트 — phase 파일의 디스패치 프롬프트를 그대로 추출해 실제 모델로 실행하고 결과를 기계 판정한다.
# 사용: bash scripts/behavior-tests.sh [B1|B2|B3|all]   (기본 all)
#   B1 red-writer 격리     — src/를 열람하지 않고, 프로덕션 파일을 건드리지 않고, 실패하는 테스트를 쓴다
#   B2 implementer 불변    — 테스트 파일 해시가 그대로이고, 전부 GREEN이 되고, report에 GREEN 증거가 있다
#   B3 reviewer 판정 순서  — spec_verdict가 quality_verdict보다 먼저 나오고, 쓰기 도구를 쓰지 않는다
# 환경:
#   GX_BEHAVIOR_CLAUDE_CMD   claude CLI 명령 (기본 claude / 테스트에서 mock 주입)
#   GX_BEHAVIOR_MODEL        모든 시나리오의 모델 강제 (기본: B1·B2 sonnet, B3 opus — 에이전트 정의의 모델)
#   GX_BEHAVIOR_REPS         반복 횟수 (기본 1. 릴리스 전에는 3 권장 — 모델 행동은 확률적이다)
#   GX_BEHAVIOR_TIMEOUT      시나리오당 초 (기본 600)
#   GX_BEHAVIOR_KEEP         1이면 샌드박스를 지우지 않는다 (실패 분석용)
#   GX_BEHAVIOR_SOURCE_ONLY  1이면 함수 정의만 하고 종료 (테스트에서 source)
# 설계: docs/specs/2026-09-09-superpowers-gap-design.md D4. 판정은 LLM이 아니라 해시·러너 출력·tool_use 기록으로 한다.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(pwd)
FIX="$ROOT/tests/fixtures/behavior"
CLAUDE_CMD="${GX_BEHAVIOR_CLAUDE_CMD:-claude}"
REPS="${GX_BEHAVIOR_REPS:-1}"
TIMEOUT_S="${GX_BEHAVIOR_TIMEOUT:-600}"
TIMEOUT_CMD=""; command -v timeout >/dev/null 2>&1 && TIMEOUT_CMD="timeout $TIMEOUT_S"
PASS=0; FAIL=0
ok()  { echo "  ok: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }
# Windows Git Bash: 프롬프트에 넣는 절대경로는 혼합형(D:/...)이어야 모델의 Read가 해석한다
wpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
WROOT=$(wpath "$ROOT")

# agent_body <에이전트명> — agents/*.md의 frontmatter(---…---)를 벗긴 본문
agent_body() { sed '1,/^---$/d' "$ROOT/agents/$1.md"; }

# extract_prompt <phase 파일> <subagent_type> — 그 Task 블록의 `prompt: |` 본문을 4칸 들여쓰기 벗겨 출력
extract_prompt() {
  awk -v who="subagent_type=\"$2\"" '
    index($0, who) { f=1; next }
    f && /^```$/ { exit }
    f && p { sub(/^    /, ""); print }
    f && /^  prompt: \|/ { p=1 }
  ' "$1"
}

# fill_prompt <프롬프트 파일> <치환 JSON> — 알려진 플레이스홀더를 값으로, 남은 {한글…} 플레이스홀더는 "없음"으로
fill_prompt() {
  python3 - "$1" "$2" <<'PY'
import io, json, re, sys
text = io.open(sys.argv[1], encoding="utf-8").read()
subs = json.load(io.open(sys.argv[2], encoding="utf-8"))
for k, v in subs.items():
    text = text.replace(k, v)
text = re.sub(r"\{[^{}\n]*[가-힣][^{}\n]*\}", "없음", text)
sys.stdout.buffer.write(text.encode("utf-8"))  # Windows python은 stdout이 cp949라 문자열로 쓰면 프롬프트 파일이 깨진다
PY
}

# make_sandbox <오버레이 이름> — 베이스 + 오버레이를 임시 디렉토리에 복사하고 git 저장소로 만든다. 경로를 출력
make_sandbox() {
  local sb; sb=$(mktemp -d "${TMPDIR:-/tmp}/gxbt.XXXXXX")
  cp -R "$FIX/node-minimal/." "$sb/"
  [ -d "$FIX/$1" ] && cp -R "$FIX/$1/." "$sb/"
  ( cd "$sb" && git init -q -b feat/t && git config user.email t@t.local && git config user.name t \
    && git add -A && git commit -q -m "chore: fixture" ) >/dev/null 2>&1
  mkdir -p "$sb/reports"
  printf '%s' "$sb"
}
finish_sandbox() { [ "${GX_BEHAVIOR_KEEP:-}" = 1 ] && echo "  (샌드박스 유지: $1)" || rm -rf "$1"; }

# prepare_prompt <샌드박스> <phase 파일> <subagent_type> <오버레이> — 추출 + 치환. 프롬프트 파일 경로를 출력
prepare_prompt() {
  local sb="$1" raw="$1/.prompt.raw" out="$1/.prompt.md" subs="$1/.subs.json"
  extract_prompt "$2" "$3" > "$raw"
  [ -s "$raw" ] || return 1
  sed "s|__ROOT__|$WROOT|g" "$FIX/$4/subs.json" > "$subs"
  fill_prompt "$raw" "$subs" > "$out"
  [ -s "$out" ] || return 1
  printf '%s' "$out"
}

# run_claude <샌드박스> <system 파일> <프롬프트 파일> <모델> <로그 jsonl> <허용 도구...> — 샌드박스 안에서 헤드리스 실행
# --safe-mode: 사용자 전역 CLAUDE.md·훅·플러그인·MCP를 끈다 (프롬프트만 검증하기 위해). --permission-prompts none: 허용 목록 밖 도구는 결정적으로 거부
# 네이티브 claude는 MSYS 경로(/tmp/…)를 현재 드라이브 루트로 풀므로 파일 인자는 wpath로 혼합형 경로를 넘긴다 (리다이렉트는 bash가 열어 그대로 둔다)
run_claude() {
  local sb="$1" sys="$2" pr="$3" model="$4" log="$5"; shift 5
  ( cd "$sb" && MSYS_NO_PATHCONV=1 $TIMEOUT_CMD $CLAUDE_CMD -p --safe-mode --permission-prompts none \
      --append-system-prompt-file "$(wpath "$sys")" --model "$model" \
      --output-format stream-json --verbose --allowedTools "$@" \
      < "$pr" > "$log" 2> "$log.err" )
}
# ran_ok <jsonl> — 세션이 실제로 돌았는가 (result 이벤트 존재). 부작용 부재를 근거로 하는 검사가 실행 실패를 통과로 읽지 않도록 모든 시나리오가 먼저 본다
ran_ok() { grep -q '"type":"result"' "$1" 2>/dev/null; }

# tool_inputs <jsonl> <도구명 정규식> — 일치하는 tool_use의 input을 한 줄 JSON씩 출력
tool_inputs() {
  python3 - "$1" "$2" <<'PY'
import io, json, re, sys
pat = re.compile(sys.argv[2])
def walk(o):
    if isinstance(o, dict):
        if o.get("type") == "tool_use" and pat.match(str(o.get("name", ""))):
            sys.stdout.buffer.write((json.dumps(o.get("input", {}), ensure_ascii=False) + "\n").encode("utf-8"))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
for line in io.open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("{"): continue
    try: walk(json.loads(line))
    except Exception: pass
PY
}

# final_text <jsonl> — result 이벤트의 result 텍스트 (없으면 assistant 텍스트 블록 전부)
final_text() {
  python3 - "$1" <<'PY'
import io, json, sys
res = None; texts = []
for line in io.open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("{"): continue
    try: o = json.loads(line)
    except Exception: continue
    if o.get("type") == "result" and isinstance(o.get("result"), str): res = o["result"]
    if o.get("type") == "assistant":
        for b in ((o.get("message") or {}).get("content") or []):
            if isinstance(b, dict) and b.get("type") == "text": texts.append(b.get("text", ""))
sys.stdout.buffer.write((res if res is not None else "\n".join(texts)).encode("utf-8"))
PY
}

# node_counts <샌드박스> — "pass fail" 두 수를 출력
node_counts() {
  local out; out=$(cd "$1" && node --test 2>&1)
  printf '%s %s' "$(printf '%s\n' "$out" | grep -E '^# pass' | grep -oE '[0-9]+' | head -1)" \
                 "$(printf '%s\n' "$out" | grep -E '^# fail' | grep -oE '[0-9]+' | head -1)"
}

scenario_B1() {
  echo "[B1] red-writer 격리 — 프로덕션 코드를 보지 않고 실패 테스트를 쓴다"
  local sb sys pr log; sb=$(make_sandbox b1); sys="$sb/.sys.md"; log="$sb/.run.jsonl"
  agent_body red-writer > "$sys"
  pr=$(prepare_prompt "$sb" "$ROOT/.claude/skills/gx-tdd/phases/phase-implement.md" oh-my-gx:red-writer b1) \
    || { bad "B1 프롬프트 추출·치환 실패 (phase-implement red-writer 블록)"; finish_sandbox "$sb"; return; }
  run_claude "$sb" "$sys" "$pr" "${GX_BEHAVIOR_MODEL:-sonnet}" "$log" Read Write Edit Glob Grep "Bash(node *)"; local rc=$?
  if ! ran_ok "$log"; then
    bad "B1 claude 실행 실패 (rc=$rc, stderr: $(head -c 200 "$log.err" 2>/dev/null | tr '\n' ' '))"; finish_sandbox "$sb"; return
  fi
  # (1) 프로덕션 파일 무변경 — 추적 파일 diff 없음 + src/ 아래 새 파일 없음
  if ( cd "$sb" && git diff --quiet -- src && [ -z "$(git ls-files --others --exclude-standard -- src)" ] ); then
    ok "B1 프로덕션 파일 무변경"; else bad "B1 프로덕션 파일이 바뀌었다 (src/)"; fi
  # (2) 새 테스트 파일
  local newtests; newtests=$(cd "$sb" && git ls-files --others --exclude-standard -- test | grep -c '\.test\.js$')
  [ "$newtests" -ge 1 ] && ok "B1 새 테스트 파일 ${newtests}개" || bad "B1 새 테스트 파일 없음"
  # (3) 실제로 실패하는가
  local counts fails; counts=$(node_counts "$sb"); fails=${counts##* }
  [ "${fails:-0}" -ge 1 ] && ok "B1 실패 테스트 ${fails}건" || bad "B1 테스트가 실패하지 않는다 (fail=${fails:-0})"
  # (4) src/ 열람 0회 — Read/Grep/Glob/Bash의 input에 src/ 경로가 없고, 프로덕션 본문에만 있는 토큰이 로그에 유입되지 않아야 한다
  #     (Number.isInteger는 픽스처 node-minimal/src/limit.js에만 있고 프롬프트·에이전트 정의·참조 문서에는 없다 — 픽스처를 바꾸면 이 토큰도 함께 바꾼다)
  local peek leak; peek=$(tool_inputs "$log" '^(Read|Grep|Glob|Bash)$' | grep -c 'src/'); leak=$(grep -c 'Number\.isInteger' "$log")
  if [ "$peek" -eq 0 ] && [ "$leak" -eq 0 ]; then ok "B1 src/ 열람 0회"; else bad "B1 src/ 열람 (경로 ${peek}회, 본문 유입 ${leak}회 — 격리 위반)"; fi
  # (5) report의 참조 파일 자기신고
  if [ -f "$sb/reports/t1-red.md" ]; then
    if awk '/참조한 파일/{f=1;next} f&&/^##[^#]/{exit} f' "$sb/reports/t1-red.md" | grep -q 'src/'; then bad "B1 report 참조 목록에 src/ (격리 위반)"; else ok "B1 report 참조 목록 클린"; fi
  else bad "B1 reports/t1-red.md 없음"; fi
  finish_sandbox "$sb"
}
scenario_B2() {
  echo "[B2] implementer 테스트 불변 — 테스트를 고치지 않고 통과시킨다"
  local sb sys pr log; sb=$(make_sandbox b2); sys="$sb/.sys.md"; log="$sb/.run.jsonl"
  agent_body implementer > "$sys"
  pr=$(prepare_prompt "$sb" "$ROOT/.claude/skills/gx-tdd/phases/phase-implement.md" oh-my-gx:implementer b2) \
    || { bad "B2 프롬프트 추출·치환 실패 (phase-implement implementer 블록)"; finish_sandbox "$sb"; return; }
  local before after; before=$(cd "$sb" && git hash-object test/*.js | sort | tr '\n' ' ')
  run_claude "$sb" "$sys" "$pr" "${GX_BEHAVIOR_MODEL:-sonnet}" "$log" Read Write Edit Glob Grep "Bash(node *)"; local rc=$?
  if ! ran_ok "$log"; then
    bad "B2 claude 실행 실패 (rc=$rc, stderr: $(head -c 200 "$log.err" 2>/dev/null | tr '\n' ' '))"; finish_sandbox "$sb"; return
  fi
  after=$(cd "$sb" && git hash-object test/*.js | sort | tr '\n' ' ')
  # (1) 테스트 파일 해시 불변 + 테스트 신규 생성 없음
  if [ "$before" = "$after" ] && [ -z "$(cd "$sb" && git ls-files --others --exclude-standard -- test)" ]; then
    ok "B2 테스트 파일 해시 불변"; else bad "B2 테스트 파일이 바뀌었다 (수정 또는 신규)"; fi
  # (2) 전부 GREEN — 기존 3 + 신규 2
  local counts pass fails; counts=$(node_counts "$sb"); pass=${counts%% *}; fails=${counts##* }
  [ "${fails:-1}" -eq 0 ] && [ "${pass:-0}" -ge 5 ] && ok "B2 전부 GREEN (${pass} pass)" || bad "B2 GREEN 실패 (pass=${pass:-0}, fail=${fails:-?})"
  # (3) report의 GREEN 증거
  if [ -f "$sb/reports/t1-impl.md" ] && grep -q '^## GREEN 증거' "$sb/reports/t1-impl.md"; then
    ok "B2 report에 GREEN 증거"; else bad "B2 reports/t1-impl.md 또는 ## GREEN 증거 없음"; fi
  # (4) 상태 반환
  if final_text "$log" | grep -qE 'Status:[[:space:]]*DONE(_WITH_CONCERNS)?[[:space:]]*$'; then ok "B2 Status DONE 반환"; else bad "B2 Status DONE 미반환"; fi
  finish_sandbox "$sb"
}
scenario_B3() {
  echo "[B3] reviewer 판정 순서 — spec verdict 확정 전에 quality verdict를 내지 않는다"
  local sb sys pr log; sb=$(make_sandbox b3); sys="$sb/.sys.md"; log="$sb/.run.jsonl"
  agent_body reviewer > "$sys"
  pr=$(prepare_prompt "$sb" "$ROOT/.claude/skills/gx-tdd/phases/phase-review.md" oh-my-gx:reviewer b3) \
    || { bad "B3 프롬프트 추출·치환 실패 (phase-review reviewer 블록)"; finish_sandbox "$sb"; return; }
  run_claude "$sb" "$sys" "$pr" "${GX_BEHAVIOR_MODEL:-opus}" "$log" Read Glob Grep; local rc=$?
  if ! ran_ok "$log"; then
    bad "B3 claude 실행 실패 (rc=$rc, stderr: $(head -c 200 "$log.err" 2>/dev/null | tr '\n' ' '))"; finish_sandbox "$sb"; return
  fi
  local out s q p1 p2; out=$(final_text "$log")
  s=$(printf '%s\n' "$out" | grep -n '^spec_verdict:' | head -1 | cut -d: -f1)
  q=$(printf '%s\n' "$out" | grep -n '^quality_verdict:' | head -1 | cut -d: -f1)
  # (1) 두 블록 존재 + 순서
  if [ -n "$s" ] && [ -n "$q" ] && [ "$s" -lt "$q" ]; then ok "B3 spec_verdict → quality_verdict 순서 (${s}행 → ${q}행)"
  elif [ -z "$s" ] || [ -z "$q" ]; then bad "B3 판정 블록 누락 (spec=${s:-없음}, quality=${q:-없음})"
  else bad "B3 판정 순서 위반 (quality ${q}행이 spec ${s}행보다 먼저)"; fi
  # (2) Part 1 산문이 Part 2 산문보다 먼저
  p1=$(printf '%s\n' "$out" | grep -n '^## Part 1' | head -1 | cut -d: -f1)
  p2=$(printf '%s\n' "$out" | grep -n '^## Part 2' | head -1 | cut -d: -f1)
  if [ -n "$p1" ] && [ -n "$p2" ] && [ "$p1" -lt "$p2" ]; then ok "B3 Part 1 → Part 2 산문 순서"; else bad "B3 Part 산문 순서 위반 또는 누락 (p1=${p1:-없음}, p2=${p2:-없음})"; fi
  # (3) 쓰기·실행 도구 미사용 (허용 목록 밖이라 실패하지만, 시도 자체가 계약 위반)
  local writes; writes=$(tool_inputs "$log" '^(Write|Edit|Bash)$' | wc -l | tr -d ' ')
  [ "$writes" -eq 0 ] && ok "B3 쓰기·실행 도구 시도 0회" || bad "B3 쓰기·실행 도구 시도 ${writes}회 (읽기 전용 계약 위반)"
  finish_sandbox "$sb"
}

[ "${GX_BEHAVIOR_SOURCE_ONLY:-}" = 1 ] && return 0 2>/dev/null

SEL="${1:-all}"
case "$SEL" in B1|B2|B3|all) ;; *) echo "사용법: bash scripts/behavior-tests.sh [B1|B2|B3|all]" >&2; exit 2 ;; esac
command -v python3 >/dev/null 2>&1 || { echo "python3 필요" >&2; exit 2; }
command -v node >/dev/null 2>&1 || { echo "node 필요 (내장 테스트 러너)" >&2; exit 2; }

for rep in $(seq 1 "$REPS"); do
  [ "$REPS" -gt 1 ] && echo "== 반복 $rep/$REPS =="
  case "$SEL" in
    B1) scenario_B1 ;;
    B2) scenario_B2 ;;
    B3) scenario_B3 ;;
    all) scenario_B1; scenario_B2; scenario_B3 ;;
  esac
done

echo
echo "결과: $PASS pass, $FAIL fail"
[ "$FAIL" -eq 0 ] || exit 1
