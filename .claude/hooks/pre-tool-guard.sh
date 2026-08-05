#!/usr/bin/env bash
# 워크스페이스 PreToolUse Guard — Bash 명령 차단 규칙
# JSON permissionDecision 출력으로 차단(deny)·확인(ask), exit 0으로 통과

set -uo pipefail

# plain cat 사용: Windows(Git Bash) 훅 spawn에서 /dev/stdin은 빈 값을 반환한다 (실측 2026-07-10)
INPUT=$(cat 2>/dev/null || echo '{}')

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

# 공통 판별: state.md가 "verify 게이트 파이프라인(gx-tdd/gx-ralph) 진행 중 + verify 미통과" 상태인가 (0 = 미통과 상태)
# 판별식은 skill-routing.md·gx-commit·gx-pull-request와 동일: pipeline 키 + status: in_progress
# + (verify-status ≠ passed 또는 verify-fingerprint 불일치)
STALE_FP=0
verify_gate_open() {
  STATE_FILE="$1"
  GATE_REPO="${2:-.}"
  STALE_FP=0
  [ -f "$STATE_FILE" ] || return 1
  grep -qE "pipeline: (gx-tdd|gx-ralph)" "$STATE_FILE" 2>/dev/null || return 1
  # 부분 문자열 매칭 유지(^앵커 금지): state.md 표기(들여쓰기·리스트)가 기계 보증되지 않아
  # 앵커가 빗나가면 게이트가 조용히 꺼진다.
  grep -q "status: in_progress" "$STATE_FILE" 2>/dev/null || return 1
  # verify-status만은 줄 시작 앵커(들여쓰기 허용)를 쓴다 — execution-log의 자유 텍스트
  # `result: "... verify-status: passed ..."`가 부분 문자열로 매칭되면 게이트가 조용히 꺼진다.
  if grep -qE '^[[:space:]]*verify-status:[[:space:]]*passed' "$STATE_FILE" 2>/dev/null; then
    RECORDED=$(sed -n 's/^[[:space:]]*verify-fingerprint:[[:space:]]*//p' "$STATE_FILE" 2>/dev/null | head -1 | tr -d ' \t\r')
    # 지문이 없는 구 세션은 기존 판정을 유지한다 (하위 호환 — passed면 게이트 닫힘)
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

# G1 + G3: git commit 가드 — 인접 패턴: "git commit"(rtk/체이닝 포함), "git -C <dir> commit", "git -c <opt> commit"
case "$CMD" in
  *"git commit"*|*"git -C "*commit*|*"git -c "*commit*)
    GIT_DIR=""
    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
    if [ -z "$CURRENT_BRANCH" ]; then
      GIT_DIR=$(echo "$CMD" | sed -n 's/.*git[[:space:]]\{1,\}-C[[:space:]]\{1,\}\([^[:space:]"\\]\{1,\}\).*/\1/p' 2>/dev/null || echo "")
      if [ -n "$GIT_DIR" ] && [ -d "$GIT_DIR" ]; then
        CURRENT_BRANCH=$(git -C "$GIT_DIR" symbolic-ref --short HEAD 2>/dev/null || echo "")
      fi
    fi

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
    if [ -n "$GIT_DIR" ]; then
      GIT_ROOT=$(git -C "$GIT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")
    else
      GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
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
        for f in "$GIT_ROOT"/.dev/*/state.md; do
          [ -f "$f" ] || continue
          if verify_gate_open "$f" "$GIT_ROOT"; then
            GATE_FILE="$f"
            GATE_LABEL="${f#"$GIT_ROOT"/} (detached HEAD — 브랜치 미확정)"
            break
          fi
        done
      fi
      if [ -n "$GATE_FILE" ] && verify_gate_open "$GATE_FILE" "$GIT_ROOT"; then
        if [ "$STALE_FP" -eq 1 ]; then
          GATE_REASON="verify 통과 후 코드가 변경되었습니다 (${GATE_LABEL}의 verify-fingerprint와 현재 코드 지문 불일치). 변경분은 아직 검증되지 않았으므로 oh-my-gx:gx-verify를 다시 통과시킨 뒤 커밋하세요."
        else
          GATE_REASON="verify 게이트 미통과 상태입니다 (${GATE_LABEL}: verify-status가 passed가 아님). oh-my-gx:gx-verify 통과 후 커밋을 권장합니다. 진행하면 'verify 미통과 커밋'으로 기록해야 합니다."
        fi
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "$GATE_REASON"
  }
}
EOF
        exit 0
      fi
    fi
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
    # 부재·공백·공백 포함·안전하지 않은 값(/ 또는 ..)이면 .dev/trunk로 폴백(레거시 세션·verify 방어 유지).
    case "$ACTIVE_SLUG" in ""|"."|*" "*|*"	"*|*/*|*\\*|*..*) ACTIVE_SLUG="trunk" ;; esac
    # 스테일 포인터 방어: 값이 있어도 가리키는 state.md가 없으면 trunk로 폴백한다.
    [ -f "$WC_ROOT/.dev/$ACTIVE_SLUG/state.md" ] || ACTIVE_SLUG="trunk"
    # svn은 git 지문을 계산할 수 없어 대조가 성립하지 않는다 — GATE_REPO를 넘기지 않으면
    # compute_fingerprint가 nohead:nodiff를 내 불일치(재검증 권고)로 판정되며 보수적이라 안전하다.
    if verify_gate_open "$WC_ROOT/.dev/$ACTIVE_SLUG/state.md"; then
      if [ "$STALE_FP" -eq 1 ]; then
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
exit 0
