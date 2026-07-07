#!/usr/bin/env bash
# 워크스페이스 PreToolUse Guard — Bash 명령 차단 규칙
# JSON permissionDecision 출력으로 차단(deny)·확인(ask), exit 0으로 통과

set -uo pipefail

INPUT=$(cat /dev/stdin 2>/dev/null || echo '{}')

# 공통 판별: state.md가 "gx-tdd 진행 중 + verify 미통과" 상태인가 (0 = 미통과 상태)
# 판별식은 skill-routing.md·gx-commit·gx-pull-request와 동일: pipeline: gx-tdd + status: in_progress + verify-status ≠ passed
verify_gate_open() {
  STATE_FILE="$1"
  [ -f "$STATE_FILE" ] || return 1
  grep -q "pipeline: gx-tdd" "$STATE_FILE" 2>/dev/null || return 1
  # 부분 문자열 매칭 유지(^앵커 금지): state.md 표기(들여쓰기·리스트)가 기계 보증되지 않아
  # 앵커가 빗나가면 게이트가 조용히 꺼진다. verify-status 값은 pending|passed뿐이라 오탐 없음.
  grep -q "status: in_progress" "$STATE_FILE" 2>/dev/null || return 1
  grep -q "verify-status: passed" "$STATE_FILE" 2>/dev/null && return 1
  return 0
}

# G1 + G3: git commit 가드
case "$INPUT" in
  *git*commit*)
    GIT_DIR=""
    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
    if [ -z "$CURRENT_BRANCH" ]; then
      GIT_DIR=$(echo "$INPUT" | sed -n 's/.*git[[:space:]]\{1,\}-C[[:space:]]\{1,\}\([^[:space:]"]\{1,\}\).*/\1/p' 2>/dev/null || echo "")
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
    "permissionDecisionReason": "gx-tdd verify 게이트 미통과 상태입니다 (.dev/${BRANCH_SLUG}/state.md: verify-status가 passed가 아님). oh-my-gx:gx-verify 통과 후 커밋을 권장합니다. 진행하면 'verify 미통과 커밋'으로 기록해야 합니다."
  }
}
EOF
        exit 0
      fi
    fi
    ;;
esac

# G2: SVN 직접 커밋 차단 — Claude 대신 사용자가 터미널에서 실행 (+ verify 미통과 경고)
case "$INPUT" in
  *svn*commit*)
    SVN_REASON="SVN 프로젝트에서는 Claude가 커밋을 실행하지 않습니다. 터미널에서 svn commit을 직접 실행해주세요."
    WC_ROOT=$(svn info --show-item wc-root 2>/dev/null || pwd)
    if verify_gate_open "$WC_ROOT/.dev/trunk/state.md"; then
      SVN_REASON="$SVN_REASON 주의: gx-tdd verify 게이트 미통과 상태입니다 (.dev/trunk/state.md). oh-my-gx:gx-verify 통과 후 커밋하세요."
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
