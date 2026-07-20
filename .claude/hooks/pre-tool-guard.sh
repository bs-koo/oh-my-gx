#!/usr/bin/env bash
# 워크스페이스 PreToolUse Guard — Bash 명령 차단 규칙
# JSON permissionDecision 출력으로 차단(deny)·확인(ask), exit 0으로 통과

set -uo pipefail

# plain cat 사용: Windows(Git Bash) 훅 spawn에서 /dev/stdin은 빈 값을 반환한다 (실측 2026-07-10)
INPUT=$(cat 2>/dev/null || echo '{}')

# tool_input.command 값만 추출해 검사한다 — JSON 전체 글롭 매칭은 description 등
# 다른 필드의 문자열에 오탐한다 (PR 본문의 "svn"+"gx-commit"으로 G2 오발화, 실측 2026-07-13).
# 값 내부의 이스케이프 따옴표(\")는 유지되고, 비이스케이프 경계("," 또는 "})는 값 내부에
# 나타날 수 없으므로 그 지점에서 자른다. 추출 실패 시 전체 INPUT으로 폴백(fail-closed 방향).
CMD=$(printf '%s' "$INPUT" | sed -E 's/.*"command"[[:space:]]*:[[:space:]]*"//; s/([^\\])"[[:space:]]*,[[:space:]]*"[a-zA-Z_]+"[[:space:]]*:.*/\1/; s/([^\\])"[[:space:]]*\}.*/\1/' 2>/dev/null)
[ -n "$CMD" ] || CMD="$INPUT"

# 공통 판별: state.md가 "verify 게이트 파이프라인(gx-tdd/gx-ralph) 진행 중 + verify 미통과" 상태인가 (0 = 미통과 상태)
# 판별식은 skill-routing.md·gx-commit·gx-pull-request와 동일: pipeline 키 + status: in_progress + verify-status ≠ passed
verify_gate_open() {
  STATE_FILE="$1"
  [ -f "$STATE_FILE" ] || return 1
  grep -qE "pipeline: (gx-tdd|gx-ralph)" "$STATE_FILE" 2>/dev/null || return 1
  # 부분 문자열 매칭 유지(^앵커 금지): state.md 표기(들여쓰기·리스트)가 기계 보증되지 않아
  # 앵커가 빗나가면 게이트가 조용히 꺼진다. verify-status 값은 pending|passed뿐이라 오탐 없음.
  grep -q "status: in_progress" "$STATE_FILE" 2>/dev/null || return 1
  grep -q "verify-status: passed" "$STATE_FILE" 2>/dev/null && return 1
  return 0
}

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
    if [ -n "$CURRENT_BRANCH" ]; then
      if [ -n "$GIT_DIR" ]; then
        GIT_ROOT=$(git -C "$GIT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")
      else
        GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
      fi
      BRANCH_SLUG=${CURRENT_BRANCH//\//-}
      if [ -n "$GIT_ROOT" ] && verify_gate_open "$GIT_ROOT/.dev/$BRANCH_SLUG/state.md"; then
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "verify 게이트 미통과 상태입니다 (.dev/${BRANCH_SLUG}/state.md: verify-status가 passed가 아님). oh-my-gx:gx-verify 통과 후 커밋을 권장합니다. 진행하면 'verify 미통과 커밋'으로 기록해야 합니다."
  }
}
EOF
        exit 0
      fi
    fi
    ;;
esac

# G4: force-push 차단 — 보호 정책(git push --force / -f 금지)을 훅으로도 배포해
# 소비 프로젝트가 플러그인 설치만으로 보호받게 한다(settings.json deny와 동일 집합).
# 중첩 case: 바깥이 push 명령(git -C/-c/rtk 래핑 포함)을 잡고, 안쪽이 force 플래그를 판정한다.
# cd <dir> && git push 형태는 커밋 가드(G1/G3)와 동일한 알려진 한계.
case "$CMD" in
  *"git "*"push"*)
    case "$CMD" in
      *"--force"*|*" -f"|*" -f "*)
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "강제 푸시(git push --force / -f)는 금지됩니다. 저장소 히스토리를 손상시킬 수 있습니다. 꼭 필요하면 사용자가 터미널에서 직접 실행해주세요."
  }
}
EOF
        exit 0
        ;;
    esac
    ;;
esac

# G2: SVN 직접 커밋 차단 — Claude 대신 사용자가 터미널에서 실행 (+ verify 미통과 경고)
# 인접 패턴("svn commit"/"svn ci"): svn과 commit이 명령 인자에 따로 등장하는 경우(문서 본문 등)의 오탐 방지
case "$CMD" in
  *"svn commit"*|*"svn ci"*)
    SVN_REASON="SVN 프로젝트에서는 Claude가 커밋을 실행하지 않습니다. 터미널에서 svn commit을 직접 실행해주세요."
    WC_ROOT=$(svn info --show-item wc-root 2>/dev/null || pwd)
    # svn 활성 작업 slug: .dev/.active 포인터로 기능별 state.md를 찾는다.
    # 부재·공백·안전하지 않은 값(/ 또는 ..)이면 .dev/trunk로 폴백(레거시 세션·verify 방어 유지).
    ACTIVE_SLUG=""
    [ -f "$WC_ROOT/.dev/.active" ] && ACTIVE_SLUG=$(tr -d '\r\n' < "$WC_ROOT/.dev/.active" 2>/dev/null)
    case "$ACTIVE_SLUG" in ""|*/*|*..*) ACTIVE_SLUG="trunk" ;; esac
    if verify_gate_open "$WC_ROOT/.dev/$ACTIVE_SLUG/state.md"; then
      SVN_REASON="$SVN_REASON 주의: gx-tdd verify 게이트 미통과 상태입니다 (.dev/$ACTIVE_SLUG/state.md). oh-my-gx:gx-verify 통과 후 커밋하세요."
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
