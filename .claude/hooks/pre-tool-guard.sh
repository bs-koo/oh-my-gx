#!/usr/bin/env bash
# 워크스페이스 PreToolUse Guard — Bash 명령 차단 규칙
# JSON permissionDecision 출력으로 차단(deny)·확인(ask), exit 0으로 통과

set -uo pipefail
DEFERRED_REASON=""
ALLOW_NOTE=""

# plain cat 사용: Windows(Git Bash) 훅 spawn에서 /dev/stdin은 빈 값을 반환한다 (실측 2026-07-10)
INPUT=$(cat 2>/dev/null || echo '{}')

# Claude Code 권한 모드. bypassPermissions에서는 G3(verify 미통과 커밋 확인)를 묻지 않고 경고 문맥으로 바꾼다
# — 훅의 ask는 bypass 모드에서도 확인 창을 띄워, 사용자가 고른 "묻지 않기"를 깨뜨린다. G1·G2·G4·레거시 차단은 그대로다.
# auto·dontAsk 등 다른 모드는 ask를 유지한다(dontAsk는 확인이 필요한 호출을 거부하므로 사실상 차단).
# Codex 어댑터는 이 필드를 지우고 GX_HOOK_HARNESS=codex를 넘긴다 — 아래 G3 완화(bypass·위험 수용 토큰·병합 커밋)를 모두 끄고 차단 정책을 유지한다.
# jq는 최상위 키만 읽는다. grep 폴백은 JSON 키 모양("permission_mode": "값")만 맞춘다 — 명령 문자열 안의 같은 글자는
# JSON에서 \"로 이스케이프되어 이 패턴에 맞지 않는다(위조 사례는 scripts/hook-tests.sh가 그 환경의 경로로 검사한다).
PERMISSION_MODE=""
if command -v jq >/dev/null 2>&1; then
  PERMISSION_MODE=$(printf '%s' "$INPUT" | jq -r '.permission_mode // empty' 2>/dev/null || echo "")
else
  PERMISSION_MODE=$(printf '%s' "$INPUT" | grep -o '"permission_mode"[[:space:]]*:[[:space:]]*"[A-Za-z]*"' | head -1 | sed 's/.*"\([A-Za-z]*\)"$/\1/')
fi

# tool_input.command 값만 추출해 검사한다 — JSON 전체 글롭 매칭은 description 등
# 다른 필드의 문자열에 오탐한다 (PR 본문의 "svn"+"gx-commit"으로 G2 오발화, 실측 2026-07-13).
#
# 1순위 jq: 이스케이프(\\, \", \n)를 규약대로 해석한다.
# 2순위 awk 스캐너: jq가 없는 환경 폴백. 값의 시작 따옴표부터 문자 단위로 걸으며
#   백슬래시를 만나면 다음 문자를 통째로 소비해, "이스케이프되지 않은 종료 따옴표"를
#   정확히 찾는다. 정규식 근사(sed)는 값이 백슬래시로 끝날 때(예: `echo C:\\`)
#   경계를 놓쳐 뒤 필드(description 등)를 삼키고 오탐하므로 쓰지 않는다.
#   여러 줄(pretty-print) JSON도 전 행을 이어붙여 처리한다.
# 추출 실패 시 전체 INPUT으로 폴백(fail-closed 방향).
CMD=""
if command -v jq >/dev/null 2>&1; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")
fi
if [ -z "$CMD" ]; then
  CMD=$(printf '%s' "$INPUT" | awk '
    { buf = buf $0 }
    END {
      k = index(buf, "\"command\"")
      if (k == 0) { exit }
      rest = substr(buf, k + 9)
      n = length(rest); j = 1
      while (j <= n) { c = substr(rest, j, 1); if (c == ":" || c == " " || c == "\t") { j++; continue } break }
      if (substr(rest, j, 1) != "\"") { exit }
      j++
      out = ""
      while (j <= n) {
        c = substr(rest, j, 1)
        if (c == "\\") { out = out c substr(rest, j + 1, 1); j += 2; continue }
        if (c == "\"") break
        out = out c; j++
      }
      print out
    }' 2>/dev/null)
fi
[ -n "$CMD" ] || CMD="$INPUT"

# 코드 지문 계산 — verify 통과 시점의 코드와 지금 커밋하려는 코드가 같은지 대조하는 값.
# HEAD 커밋 + 워킹트리 전체의 트리 해시를 이어붙여 미커밋 수정·신규 파일까지 포착한다.
#
# 임시 인덱스(GIT_INDEX_FILE)에 전체를 add한 뒤 write-tree 하는 이유:
#   `git diff HEAD` 방식은 **신규 파일이 스테이징되면 값이 바뀐다**(untracked는 diff에
#   안 잡히지만 add 후에는 잡힌다). RGR은 테스트·구현 파일을 새로 만드는 것이 기본이라,
#   verify(스테이징 전) → git add -A → commit 순서에서 지문이 어긋나 게이트가 오발동한다
#   (헤드리스 루프에서는 자기 차단). 트리 해시는 스테이징 여부와 무관해 이 문제가 없다.
#   실제 인덱스는 건드리지 않는다.
# `.dev/`는 인덱스에서 제거해 제외한다: state.md·diff.txt 등 파이프라인 산출물은 코드가
#   아니며, 포함하면 상태를 기록할 때마다 지문이 스스로 무효화된다. gitignore에 의존하지
#   않고 명시 제거하므로 ignore 누락 저장소에서도 동일하게 동작한다.
compute_fingerprint() {
  FP_REPO="${1:-.}"
  FP_HEAD=$(git -C "$FP_REPO" rev-parse --short HEAD 2>/dev/null || echo "nohead")
  # mktemp가 만든 빈 파일은 git이 "index file smaller than expected"로 거부한다 — 경로만 쓴다
  FP_IDX="${TMPDIR:-/tmp}/.gxfp.$$"
  rm -f "$FP_IDX"
  FP_TREE=""
  if GIT_INDEX_FILE="$FP_IDX" git -C "$FP_REPO" add -A >/dev/null 2>&1; then
    GIT_INDEX_FILE="$FP_IDX" git -C "$FP_REPO" rm -r --cached -q --ignore-unmatch .dev >/dev/null 2>&1
    FP_TREE=$(GIT_INDEX_FILE="$FP_IDX" git -C "$FP_REPO" write-tree 2>/dev/null || echo "")
  fi
  rm -f "$FP_IDX"
  [ -n "$FP_TREE" ] || FP_TREE="notree"
  printf '%s:%s' "$FP_HEAD" "$(printf '%s' "$FP_TREE" | cut -c1-12)"
}

# 공통 판별: TDD 검증 대기 또는 제거된 Ralph 실행 상태인가 (0 = 커밋 중단)
# 판별식은 skill-routing.md·gx-commit·gx-pull-request와 동일: pipeline 키 + status: in_progress
# + (verify-status ≠ passed 또는 verify-fingerprint 불일치)
STALE_FP=0
RETIRED_PIPELINE=0
FP_DUPLICATE=0
verify_gate_open() {
  STATE_FILE="$1"
  GATE_REPO="${2:-.}"
  STALE_FP=0
  RETIRED_PIPELINE=0
  FP_DUPLICATE=0
  # 잠금만 남은 실행도 새 커밋으로 진행시키지 않는다. 상태 파일 부재·완료 여부와 독립이다.
  if [ -e "${STATE_FILE%/*}/ralph.lock" ]; then
    RETIRED_PIPELINE=1
    return 0
  fi
  [ -f "$STATE_FILE" ] || return 1
  grep -qE "pipeline: (gx-tdd|gx-ralph)" "$STATE_FILE" 2>/dev/null || return 1
  # 부분 문자열 매칭 유지(^앵커 금지): state.md 표기(들여쓰기·리스트)가 기계 보증되지 않아
  # 앵커가 빗나가면 게이트가 조용히 꺼진다.
  grep -q "status: in_progress" "$STATE_FILE" 2>/dev/null || return 1
  # 제거된 실행기의 passed 표시는 새 커밋 권한이 아니다. 기록을 보존한 뒤 명시적으로 전환한다.
  if grep -qE 'pipeline: gx-ralph' "$STATE_FILE" 2>/dev/null || grep -qiE '^[[:space:]]*flags:.*ralph' "$STATE_FILE" 2>/dev/null; then
    RETIRED_PIPELINE=1
    return 0
  fi
  # verify-status만은 줄 시작 앵커(들여쓰기 허용)를 쓴다 — execution-log의 자유 텍스트
  # `result: "... verify-status: passed ..."`가 부분 문자열로 매칭되면 게이트가 조용히 꺼진다.
  if grep -qE '^[[:space:]]*verify-status:[[:space:]]*passed' "$STATE_FILE" 2>/dev/null; then
    # 기록 양식이 `verify-fingerprint: ""`라 실제 세션은 값을 따옴표로 감싼다 — 따옴표·공백·CR을 벗긴 값으로 대조한다.
    # 키가 여러 번 나오면(빈 양식 줄 + 실제 기록) 비어 있지 않은 마지막 값을 쓰고, 서로 다른 값이 있으면 사유에 알린다.
    FP_VALUES=$(sed -n 's/^[[:space:]]*verify-fingerprint:[[:space:]]*//p' "$STATE_FILE" 2>/dev/null | tr -d " \t\r\"'" | grep -v '^$')
    RECORDED=$(printf '%s\n' "$FP_VALUES" | tail -1)
    [ "$(printf '%s\n' "$FP_VALUES" | sort -u | grep -c .)" -gt 1 ] && FP_DUPLICATE=1
    # 지문이 없는(빈 값 포함) 구 세션은 기존 판정을 유지한다 (하위 호환 — passed면 게이트 닫힘)
    [ -n "$RECORDED" ] || return 1
    # 대조는 트리 성분(콜론 뒤)만 — HEAD 성분은 기록·추적용이다. verify 통과 후
    # phase-complete가 커밋하면 HEAD는 전진하지만 트리가 같으면 검증된 코드가 그대로
    # 커밋된 것이므로 일치로 판정한다 (커밋 → PR 정상 경로의 상시 오경고 방지).
    CURRENT_FP=$(compute_fingerprint "$GATE_REPO")
    # write-tree 실패값(notree)끼리는 "같다"고 볼 수 없다 — 양쪽 계산이 모두 실패한 경우
    # 코드 동일성이 입증되지 않으므로 보수적으로 게이트를 연다.
    [ "${CURRENT_FP##*:}" != "notree" ] && [ "${RECORDED##*:}" = "${CURRENT_FP##*:}" ] && return 1
    STALE_FP=1   # passed 표식은 있으나 코드가 그 이후 변경됨 (스테일 passed)
    return 0
  fi
  return 0
}

# 위험 수용 토큰(Claude Code 전용): gx-commit이 실제 사용자 응답으로 verify 미통과 커밋의 위험 수용을 받으면
# .dev/{branch-slug}/verify-risk-accepted에 `tree: <트리 지문 12자>`를 쓴다. 트리가 지금과 같을 때만 유효하다
# — 수용 뒤 코드가 바뀌면 다시 묻는다. 확인을 스킬 질문 한 번으로 끝내기 위한 표식이다 (0 = 유효).
risk_token_valid() {
  [ -f "$1" ] || return 1
  TOKEN_TREE=$(sed -n 's/^[[:space:]]*tree:[[:space:]]*//p' "$1" 2>/dev/null | tr -d " \t\r\"'" | grep -v '^$' | tail -1)
  [ -n "$TOKEN_TREE" ] || return 1
  TOKEN_FP=$(compute_fingerprint "$2")
  [ "${TOKEN_FP##*:}" != "notree" ] && [ "$TOKEN_TREE" = "${TOKEN_FP##*:}" ]
}

# G4: force-push 차단 — 보호 정책(git push --force / -f 금지)을 훅으로도 배포해
# 소비 프로젝트가 플러그인 설치만으로 보호받게 한다(settings.json deny와 동일 취지).
# 중첩 case: 바깥이 push 명령(git -C/-c/rtk 래핑 포함)을 잡고, 안쪽이 force 플래그를 판정한다.
# G1/G3(커밋 가드)보다 먼저 평가한다 — "git commit && git push --force" 체이닝에서
# force-push deny가 verify ask로 강등되지 않도록 강한 판정을 우선한다.
# cd <dir> && git push 형태는 cwd 기준 해석이 빗나갈 수 있는 알려진 한계.
case "$CMD" in
  *"git "*"push"*)
    # push 서브커맨드 이후 인자만 검사한다 (명령 분리자 전까지) — 무관한 -f/--force 오탐 방지.
    # 마지막 push 이후 인자만 검사 (앞선 "push" 토큰 오탐 방지 — 예: echo push && git push --force)
    PUSH_ARGS="${CMD##*push}"; PUSH_ARGS="${PUSH_ARGS%%&&*}"; PUSH_ARGS="${PUSH_ARGS%%;*}"; PUSH_ARGS="${PUSH_ARGS%%|*}"
    # `+refspec`(예: git push origin +feat:main)도 강제 푸시다 — --force와 동일하게 차단한다.
    FORCE_HIT=0
    case "$PUSH_ARGS" in
      *"--force"*|*" -f"|*" -f "*) FORCE_HIT=1 ;;
    esac
    case "$PUSH_ARGS" in
      *" +"*:*) FORCE_HIT=1 ;;
    esac
    if [ "$FORCE_HIT" -eq 1 ]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "강제 푸시(git push --force / -f / +refspec)는 금지됩니다. 저장소 히스토리를 손상시킬 수 있습니다. 꼭 필요하면 사용자가 터미널에서 직접 실행해주세요."
  }
}
EOF
      exit 0
    fi
    ;;
esac

# G1 + G3: git commit 가드 — 인접 패턴: "git commit"(rtk/체이닝/래퍼 포함), "git -C/-c/-P/--… commit", "git.exe commit"
case "$CMD" in
  *"git commit"*|*"git -"*commit*|*"git.exe "*commit*)
    # JSON 원문을 helper에 넘겨 인용·heredoc·셸 래퍼·cd를 해석한 커밋 대상 목록을 받는다. 동적·모호한 경로는 차단한다.
    HOOK_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
    # python3 → python 순서로 실제 실행해 3.10 이상을 고른다. Windows의 python3는 Store 별칭이거나
    # 3.10 미만일 수 있어 첫 이름만 보면 모든 커밋이 막힌다(capture-decision.sh와 같은 방식).
    TARGET_PYTHON=""
    for candidate in python3 python; do
      if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' </dev/null >/dev/null 2>&1; then
        TARGET_PYTHON=$candidate
        break
      fi
    done
    if [ -n "$TARGET_PYTHON" ]; then
      if ! GIT_TARGETS=$(printf '%s' "$INPUT" | "$TARGET_PYTHON" "$HOOK_ROOT/../../scripts/gx-git-target.py"); then
        # helper는 판정하지 못한 원인 한 줄을 stdout에 남긴다. JSON 문자열이 깨지지 않게 제어문자·따옴표·백슬래시를 바꾼다.
        TARGET_REASON=$(printf '%s' "$GIT_TARGETS" | head -1 | tr -d '\000-\037' | tr '"\\' "'/")
        printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Git 커밋 대상을 확정하지 못했습니다: %s. 커밋할 저장소를 git -C <경로>로 명시하세요."}}\n' \
          "${TARGET_REASON:-대상 판정 helper가 실패했습니다}"
        exit 0
      fi
    else
      # Python 3.10+가 없으면 이전 bash 판정으로 보호를 유지한다: cwd와 따옴표 없는 `git -C <경로>`를 검사한다.
      GIT_TARGETS="?."
      while IFS= read -r FALLBACK_DIR; do
        [ -n "$FALLBACK_DIR" ] && [ -d "$FALLBACK_DIR" ] && GIT_TARGETS="$GIT_TARGETS"$'\n'"?$FALLBACK_DIR"
      done <<< "$(printf '%s\n' "$CMD" | sed -n 's/.*git[[:space:]]\{1,\}-C[[:space:]]\{1,\}\([^[:space:]"\\]\{1,\}\).*/\1/p')"
    fi
    # 한 명령에 여러 저장소의 commit이 있으면 각각 검사한다.
    # 루프 변수로 GIT_DIR를 쓰지 않는다 — export된 GIT_DIR를 덮어쓰면 아래 git 호출이 대상 저장소를 잃는다.
    DEFERRED_REASON=""
    ALLOW_NOTE=""
    while IFS= read -r TARGET_DIR; do
      [ -n "$TARGET_DIR" ] || continue
      # `?` 접두는 대상을 해석하지 못해 대신 검사하는 경로다. Git 저장소가 아니면 건너뛴다(이전 훅과 같은 판정).
      TARGET_OPTIONAL=0
      case "$TARGET_DIR" in "?"*) TARGET_OPTIONAL=1; TARGET_DIR=${TARGET_DIR#\?} ;; esac
      CURRENT_BRANCH=$(git -C "$TARGET_DIR" symbolic-ref --short HEAD 2>/dev/null || echo "")

    # G1: 보호 브랜치(main/master/develop)에서 직접 커밋 차단
    if [[ "$CURRENT_BRANCH" =~ ^(develop|main|master)$ ]]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "${CURRENT_BRANCH} 브랜치에서는 커밋할 수 없습니다. 작업 브랜치를 먼저 생성하세요."
  }
}
EOF
      exit 0
    fi

    # G3: gx-tdd verify 게이트 — 미통과 상태의 커밋은 사용자 확인(ask)을 요구
    # deny가 아닌 ask인 이유: 스킬/라우팅 층에 문서화된 "위험 수용" 경로를 보존하면서,
    # 컨텍스트 압축·라우팅 우회와 무관하게 항상 동작하는 결정론적 확인 지점을 만든다.
    # Claude Code에서는 미해결 충돌이 없는 진행 중인 베이스 병합 커밋·유효한 위험 수용 토큰·bypassPermissions면 묻지 않고
    # 문맥 경고(allow + additionalContext)로 바꾼다. Codex(GX_HOOK_HARNESS=codex)는 이 완화 없이 ask → deny다.
    GIT_ROOT=$(git -C "$TARGET_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")
    if [ -z "$GIT_ROOT" ]; then
      [ "$TARGET_OPTIONAL" -eq 1 ] && continue
      printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "커밋 대상 Git 저장소를 확인할 수 없습니다."}}'
      exit 0
    fi
    if [ -n "$GIT_ROOT" ]; then
      if [ -n "$CURRENT_BRANCH" ]; then
        BRANCH_SLUG=${CURRENT_BRANCH//\//-}
        GATE_FILE="$GIT_ROOT/.dev/$BRANCH_SLUG/state.md"
        GATE_LABEL=".dev/${BRANCH_SLUG}/state.md"
      else
        # detached HEAD(리베이스·bisect 중) — 브랜치 슬러그를 만들 수 없다.
        # 이때 게이트를 통째로 건너뛰면 무검증 커밋이 조용히 통과하므로,
        # .dev/*/state.md 중 게이트가 열린 것이 하나라도 있으면 확인을 요구한다.
        GATE_FILE=""
        GATE_LABEL=""
        for lock in "$GIT_ROOT"/.dev/*/ralph.lock; do
          if [ -e "$lock" ]; then
            GATE_FILE="${lock%/*}/state.md"
            GATE_LABEL="${lock#"$GIT_ROOT"/} (detached HEAD — 브랜치 미확정)"
            break
          fi
        done
        if [ -z "$GATE_FILE" ]; then
          for f in "$GIT_ROOT"/.dev/*/state.md; do
            [ -f "$f" ] || continue
            if verify_gate_open "$f" "$GIT_ROOT"; then
              GATE_FILE="$f"
              GATE_LABEL="${f#"$GIT_ROOT"/} (detached HEAD — 브랜치 미확정)"
              break
            fi
          done
        fi
      fi
      if [ -n "$GATE_FILE" ] && verify_gate_open "$GATE_FILE" "$GIT_ROOT"; then
        GATE_DECISION="ask"
        if [ "$RETIRED_PIPELINE" -eq 1 ]; then
          GATE_DECISION="deny"
          GATE_REASON="Ralph 지원이 중단된 실행 기록입니다 (${GATE_LABEL}). 기존 기록과 잠금을 보존하고 실행 종료를 확인한 뒤 명시적으로 TDD 전환 범위를 정하세요."
        elif [ "$STALE_FP" -eq 1 ]; then
          GATE_REASON="검증(verify) 뒤 코드가 바뀌었습니다(기록 ${RECORDED}, 현재 ${CURRENT_FP}). gx-verify를 다시 통과시킨 뒤 커밋하세요 (${GATE_LABEL})."
          [ "$FP_DUPLICATE" -eq 1 ] && GATE_REASON="$GATE_REASON 상태 파일에 서로 다른 verify-fingerprint가 여러 번 있어 마지막 값으로 비교했습니다."
        else
          GATE_REASON="검증(verify)을 아직 통과하지 않았습니다 (${GATE_LABEL}). gx-verify를 통과시킨 뒤 커밋하는 것을 권장합니다."
        fi
        # 앞 저장소의 ask로 뒤 저장소의 보호 브랜치/레거시 deny를 가리지 않는다.
        if [ "$GATE_DECISION" = "ask" ]; then
          if [ "${GX_HOOK_HARNESS:-}" != "codex" ]; then
            # 병합 완화는 미해결 충돌 경로(git ls-files -u)가 없을 때만이다. 남아 있으면 `git add -A && git commit`이
            # 충돌 표식을 그대로 커밋할 수 있어 기존 ask를 낸다. 목록을 읽지 못하면 완화하지 않는다.
            if git -C "$GIT_ROOT" rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1 \
              && UNMERGED=$(git -C "$GIT_ROOT" ls-files -u 2>/dev/null) && [ -z "$UNMERGED" ]; then
              ALLOW_NOTE="${ALLOW_NOTE:+$ALLOW_NOTE; }$TARGET_DIR: 베이스 병합 커밋 — 병합 후 verify를 다시 통과해야 커밋·PR 게이트가 닫힌다."
              continue
            fi
            if risk_token_valid "${GATE_FILE%/*}/verify-risk-accepted" "$GIT_ROOT"; then
              ALLOW_NOTE="${ALLOW_NOTE:+$ALLOW_NOTE; }$TARGET_DIR: 사용자가 위험을 수용한 verify 미통과 커밋 — $GATE_REASON"
              continue
            fi
            if [ "$PERMISSION_MODE" = "bypassPermissions" ]; then
              ALLOW_NOTE="${ALLOW_NOTE:+$ALLOW_NOTE; }$TARGET_DIR: bypassPermissions 모드 — $GATE_REASON"
              continue
            fi
          fi
          DEFERRED_REASON="${DEFERRED_REASON:+$DEFERRED_REASON; }$TARGET_DIR: $GATE_REASON"
          continue
        fi
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "$GATE_DECISION",
    "permissionDecisionReason": "$GATE_REASON"
  }
}
EOF
        exit 0
      fi
    fi
    done <<< "$GIT_TARGETS"
    ;;
esac

# G2: SVN 직접 커밋 차단 — Claude 대신 사용자가 터미널에서 실행 (+ verify 미통과 경고)
# 인접 패턴("svn commit"/"svn ci"): svn과 commit이 명령 인자에 따로 등장하는 경우(문서 본문 등)의 오탐 방지
case "$CMD" in
  *"svn commit"*|*"svn ci"*)
    SVN_REASON="SVN 프로젝트에서는 Claude가 커밋을 실행하지 않습니다. 터미널에서 svn commit을 직접 실행해주세요."
    WC_ROOT=$(svn info --show-item wc-root 2>/dev/null || pwd)
    # svn 활성 작업 slug: .dev/.active 포인터로 기능별 state.md를 찾는다.
    # 첫 줄만 읽고 CR/LF만 제거한다 — 내부 공백까지 지우면 "a b"가 "ab"라는 존재하지 않는
    # slug로 둔갑해 폴백에도 걸리지 않는다. 공백 포함 값은 아래 case에서 불안전으로 걸러진다.
    ACTIVE_SLUG=""
    [ -f "$WC_ROOT/.dev/.active" ] && ACTIVE_SLUG=$(head -1 "$WC_ROOT/.dev/.active" 2>/dev/null | tr -d '\r\n')
    # 편집기가 붙인 UTF-8 BOM은 지운다 — 남기면 slug 디렉토리를 못 찾고 trunk로 폴백해 그 작업의 verify 게이트가 빠진다
    # (scripts/gx-work.py·capture_decision.py와 같은 해석).
    ACTIVE_SLUG=${ACTIVE_SLUG#$'\xEF\xBB\xBF'}
    # 부재·공백·공백 포함·안전하지 않은 값(/ 또는 ..)이면 .dev/trunk로 폴백(레거시 세션·verify 방어 유지).
    case "$ACTIVE_SLUG" in ""|"."|*" "*|*"	"*|*/*|*\\*|*..*) ACTIVE_SLUG="trunk" ;; esac
    # 스테일 포인터 방어: 값이 있어도 가리키는 state.md가 없으면 trunk로 폴백한다.
    [ -f "$WC_ROOT/.dev/$ACTIVE_SLUG/state.md" ] || [ -e "$WC_ROOT/.dev/$ACTIVE_SLUG/ralph.lock" ] || ACTIVE_SLUG="trunk"
    SVN_GATE_FILE="$WC_ROOT/.dev/$ACTIVE_SLUG/state.md"
    if [ ! -f "$SVN_GATE_FILE" ] && [ ! -e "${SVN_GATE_FILE%/*}/ralph.lock" ]; then
      for lock in "$WC_ROOT"/.dev/*/ralph.lock; do
        [ -e "$lock" ] || continue
        SVN_GATE_FILE="${lock%/*}/state.md"
        break
      done
    fi
    # svn은 git 지문을 계산할 수 없어 대조가 성립하지 않는다 — GATE_REPO를 넘기지 않으면
    # compute_fingerprint가 nohead:notree를 내 불일치(재검증 권고)로 판정되며 보수적이라 안전하다.
    if verify_gate_open "$SVN_GATE_FILE"; then
      if [ "$RETIRED_PIPELINE" -eq 1 ]; then
        SVN_REASON="$SVN_REASON 제거된 Ralph 실행 기록입니다. 기록을 보존하고 명시적으로 TDD 전환 범위를 정하세요."
      elif [ "$STALE_FP" -eq 1 ]; then
        SVN_REASON="$SVN_REASON 주의: verify 통과 후 코드가 변경되었을 수 있습니다 (.dev/$ACTIVE_SLUG/state.md 지문 불일치). oh-my-gx:gx-verify를 다시 통과시킨 뒤 커밋하세요."
      else
        SVN_REASON="$SVN_REASON 주의: gx-tdd verify 게이트 미통과 상태입니다 (.dev/$ACTIVE_SLUG/state.md). oh-my-gx:gx-verify 통과 후 커밋하세요."
      fi
    fi
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "$SVN_REASON"
  }
}
EOF
    exit 0
    ;;
esac
# 모든 강한 deny(Git 보호·레거시·SVN)를 평가한 다음에만 보류한 ask를 반환한다.
if [ -n "${DEFERRED_REASON:-}" ]; then
  # Python 없이도(폴백 판정) ask를 낼 수 있게 JSON 문자열 이스케이프를 셸에서 한다.
  ESCAPED_REASON=$(printf '%s 그대로 진행하면 이 커밋은 '\''verify 미통과 커밋'\''으로 기록해야 합니다.' "$DEFERRED_REASON" | tr -d '\000-\037' | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "%s"}}\n' "$ESCAPED_REASON"
  exit 0
fi
# 확인 생략(bypass·위험 수용 토큰·베이스 병합 커밋): 확인 창 없이 진행하되 Claude가 읽는 문맥(additionalContext)에
# 대상별 사유와 기록 의무를 한 번만 남긴다.
if [ -n "${ALLOW_NOTE:-}" ]; then
  NOTE="확인 없이 커밋을 진행합니다. ${ALLOW_NOTE} 사용자에게 알리고, 병합 커밋이 아닌 verify 미통과 커밋은 gx-tdd trust-ledger·PR 본문에 'verify 미통과 커밋'으로 기록하라."
  ESCAPED_NOTE=$(printf '%s' "$NOTE" | tr -d '\000-\037' | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": "%s"}}\n' "$ESCAPED_NOTE"
  exit 0
fi
exit 0
