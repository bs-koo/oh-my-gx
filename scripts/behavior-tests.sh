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
cd "$(dirname "$0")/.."
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
  printf '%s' "$out"
}

# run_claude <샌드박스> <system 파일> <프롬프트 파일> <모델> <로그 jsonl> <허용 도구...> — 샌드박스 안에서 헤드리스 실행
run_claude() {
  local sb="$1" sys="$2" pr="$3" model="$4" log="$5"; shift 5
  ( cd "$sb" && MSYS_NO_PATHCONV=1 $TIMEOUT_CMD $CLAUDE_CMD -p \
      --append-system-prompt-file "$sys" --model "$model" \
      --output-format stream-json --verbose --allowedTools "$@" \
      < "$pr" > "$log" 2> "$log.err" )
}

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

scenario_B1() { bad "B1 미구현"; }
scenario_B2() { bad "B2 미구현"; }
scenario_B3() { bad "B3 미구현"; }

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
