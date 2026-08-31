#!/usr/bin/env bash
# AskUserQuestion 질문·답변을 .dev/{branch-slug}/decisions.md에 기록하는 PostToolUse 훅.
#
# jq를 쓰지 않는 이유: Git Bash 기본 환경에 jq가 없어 조용히 아무것도 하지 않는다
# (실측 2026-08-31). python3는 이 저장소의 다른 검증 스크립트도 쓰는 전제다.
#
# 기록은 판정이 아니므로 어떤 실패도 도구 실행을 막지 않는다 — 항상 0으로 끝낸다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR/capture_decision.py" 2>/dev/null
fi

exit 0
