#!/usr/bin/env bash
# 워크스페이스 PreToolUse Guard — Bash 명령 차단 규칙
# JSON permissionDecision 출력으로 차단, exit 0으로 통과

set -uo pipefail

INPUT=$(cat /dev/stdin 2>/dev/null || echo '{}')

# G1: 보호 브랜치(main)에서 직접 커밋 차단 (git)
case "$INPUT" in
  *git*commit*)
    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
    if [ -z "$CURRENT_BRANCH" ]; then
      GIT_DIR=$(echo "$INPUT" | sed -n 's/.*git[[:space:]]\{1,\}-C[[:space:]]\{1,\}\([^[:space:]"]\{1,\}\).*/\1/p' 2>/dev/null || echo "")
      if [ -n "$GIT_DIR" ] && [ -d "$GIT_DIR" ]; then
        CURRENT_BRANCH=$(git -C "$GIT_DIR" symbolic-ref --short HEAD 2>/dev/null || echo "")
      fi
    fi
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
    ;;
esac

# G2: SVN 직접 커밋 차단 — /commit 스킬을 사용하도록 유도 (SVN은 스킬 미지원이므로 안내)
case "$INPUT" in
  *svn*commit*)
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "SVN 커밋은 사용자가 직접 실행해야 합니다. Claude가 svn commit을 대신 실행하지 않습니다."
  }
}
EOF
    exit 0
    ;;
esac
exit 0
