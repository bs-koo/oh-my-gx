#!/usr/bin/env bash
# gx-ralph 외부 러너 — Ralph 루프 드라이버
#
# 매 반복 새 claude 세션(-p)을 기동해 gx-ralph-iterate 스킬로 AC 1건씩 처리한다.
# 상태 계약의 정본: .claude/skills/gx-ralph/SKILL.md "상태 계약 (SSOT)" (드리프트 주의)
#
# 사용법: bash scripts/gx-ralph.sh [max_iterations]
# 환경변수:
#   GX_RALPH_CLAUDE_CMD    claude CLI 명령 (기본: claude / 테스트에서 mock 주입)
#   GX_RALPH_SKILL_NAME    반복 스킬 호출명 (기본: /oh-my-gx:gx-ralph-iterate / 개발 저장소: /gx-ralph-iterate)
#   GX_RALPH_ITER_TIMEOUT  반복당 타임아웃 초 (기본: 1800)
#
# 종료 코드: 0 COMPLETE | 2 BLOCKED | 3 종료 계약 미출력 | 4 NO_DRIFT | 5 MAX_ITER 소진 | 6 사전 조건 실패
set -uo pipefail

CLAUDE_CMD="${GX_RALPH_CLAUDE_CMD:-claude}"
SKILL_NAME="${GX_RALPH_SKILL_NAME:-/oh-my-gx:gx-ralph-iterate}"
ITER_TIMEOUT="${GX_RALPH_ITER_TIMEOUT:-1800}"

# allowedTools — gx-ralph-iterate/SKILL.md의 allowed-tools와 동기 (드리프트 주의)
ALLOWED_TOOLS="Read,Write,Edit,Glob,Grep,Task,Skill,Bash(git *),Bash(./gradlew *),Bash(npm *),Bash(npx *),Bash(pnpm *),Bash(yarn *),Bash(bun *),Bash(pytest *),Bash(go *),Bash(test *),Bash(ls *),Bash(mkdir *),Bash(pwd *),Bash(wc *),Bash(grep *)"

fail() { echo "[gx-ralph] 사전 조건 실패: $1" >&2; exit 6; }

# ── 사전 조건 assert ──
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "git 저장소가 아닙니다"
# 상대 경로(.dev/, .claude/config.json)가 저장소 루트 기준이 되도록 이동 (하위 디렉토리 실행 방어)
cd "$(git rev-parse --show-toplevel)" || fail "저장소 루트로 이동할 수 없습니다"

if [ -f ".claude/config.json" ] && grep -q '"vcs"[[:space:]]*:[[:space:]]*"svn"' .claude/config.json 2>/dev/null; then
  fail "SVN 프로젝트에서는 gx-ralph를 사용할 수 없습니다"
fi

BRANCH=$(git branch --show-current 2>/dev/null || echo "")
[ -n "$BRANCH" ] || fail "브랜치를 확인할 수 없습니다 (detached HEAD)"
case "$BRANCH" in
  main|master|develop) fail "보호 브랜치($BRANCH)에서는 루프를 돌릴 수 없습니다. 작업 브랜치를 사용하세요" ;;
esac

DEV_DIR=".dev/${BRANCH//\//-}"
STATE="$DEV_DIR/state.md"
AC_FILE="$DEV_DIR/ac-status.json"

[ -f "$STATE" ] || fail "$STATE 가 없습니다. /oh-my-gx:gx-ralph 로 먼저 준비하세요"
grep -q "pipeline: gx-ralph" "$STATE" || fail "state.md가 gx-ralph 파이프라인이 아닙니다"
grep -q "status: in_progress" "$STATE" || fail "state.md가 in_progress 상태가 아닙니다"
STATE_BRANCH=$(sed -n 's/^branch:[[:space:]]*//p' "$STATE" | head -1)
[ "$STATE_BRANCH" = "$BRANCH" ] || fail "브랜치 불일치 (state: $STATE_BRANCH, 현재: $BRANCH)"
[ -f "$AC_FILE" ] || fail "$AC_FILE 이 없습니다. /oh-my-gx:gx-ralph 로 먼저 준비하세요"

# ── 최대 반복 수: 인자 > state.md > 기본 10 ──
MAX_ITER="${1:-}"
if [ -z "$MAX_ITER" ]; then
  MAX_ITER=$(sed -n 's/^max-iterations:[[:space:]]*//p' "$STATE" | head -1)
fi
case "$MAX_ITER" in ''|*[!0-9]*) MAX_ITER=10 ;; esac

# ── lock 획득 (동시 실행 방지) ──
LOCK="$DEV_DIR/ralph.lock"
[ -e "$LOCK" ] && fail "lock이 존재합니다 ($LOCK). 다른 러너가 실행 중이거나 비정상 종료 잔재입니다"
echo "$$ $(date '+%Y-%m-%dT%H:%M:%S')" > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
# INT/TERM에서도 EXIT trap을 확실히 경유시킨다 (셸별 신호 시 EXIT trap 발화 차이 방어. SIGKILL은 잔존 → Step 1 게이트 안내로 복구)
trap 'exit 130' INT
trap 'exit 143' TERM

# ── 이전 실행 로그 보존 (재실행 시 iter-N.log 덮어쓰기 방지) ──
if ls "$DEV_DIR"/iter-*.log >/dev/null 2>&1; then
  ARCHIVE="$DEV_DIR/logs-$(date '+%Y%m%d-%H%M%S')"
  mkdir -p "$ARCHIVE" && mv "$DEV_DIR"/iter-*.log "$ARCHIVE"/
  echo "[gx-ralph] 이전 반복 로그를 $ARCHIVE/ 로 보존"
fi

# ── 타임아웃 명령 가용성 (없으면 타임아웃 없이 실행) ──
TIMEOUT_CMD=""
command -v timeout >/dev/null 2>&1 && TIMEOUT_CMD="timeout $ITER_TIMEOUT"

echo "[gx-ralph] 루프 시작 — 브랜치: $BRANCH, 최대 반복: $MAX_ITER"

ac_hash() { cksum "$AC_FILE" 2>/dev/null | awk '{print $1}'; }

NO_DRIFT=0
i=1
while [ "$i" -le "$MAX_ITER" ]; do
  PRE_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "none")
  PRE_AC=$(ac_hash)
  LOG="$DEV_DIR/iter-$i.log"

  echo "[gx-ralph] 반복 $i/$MAX_ITER 시작 → $LOG"
  # MSYS_NO_PATHCONV=1: Git Bash(Windows)가 "/gx-..." 인자를 Windows 경로로 자동 변환해
  # 프롬프트가 깨지는 것을 방지한다 (통합 스모크 실측 2026-07-10). 타 환경에서는 무해.
  # shellcheck disable=SC2086 — CLAUDE_CMD/TIMEOUT_CMD의 의도적 단어 분리
  MSYS_NO_PATHCONV=1 $TIMEOUT_CMD $CLAUDE_CMD -p "$SKILL_NAME" --allowedTools "$ALLOWED_TOOLS" > "$LOG" 2>&1
  EXIT_CODE=$?

  # [^<]* 대신 .* — BLOCKED 사유에 '<'가 포함돼도 계약이 파싱되도록 (계약은 한 줄에 하나)
  CONTRACT=$(grep -o '<ralph>.*</ralph>' "$LOG" 2>/dev/null | tail -1)

  case "$CONTRACT" in
    "<ralph>COMPLETE</ralph>")
      DONE=$(grep -c '"passes"[[:space:]]*:[[:space:]]*true' "$AC_FILE" 2>/dev/null || echo "?")
      # 복귀 파이프라인은 origin 분기 — gx-tdd 출발 루프는 spec→quality 리뷰(/gx-tdd)가 정본
      ORIGIN=$(sed -n 's/^origin:[[:space:]]*//p' "$STATE" | head -1)
      REVIEW_CMD="/gx-dev"; [ "$ORIGIN" = "gx-tdd" ] && REVIEW_CMD="/gx-tdd"
      echo "[gx-ralph] ✅ COMPLETE — 전 AC 완료 (passes=true: $DONE건, 반복 $i회)"
      echo "[gx-ralph] 다음 단계: $REVIEW_CMD --phase review 로 리뷰 → --phase complete 로 인수·PR"
      exit 0
      ;;
    "<ralph>BLOCKED:"*)
      REASON=${CONTRACT#<ralph>BLOCKED: }; REASON=${REASON%</ralph>}
      echo "[gx-ralph] ⛔ BLOCKED — $REASON (반복 $i회에서 중단)" >&2
      echo "[gx-ralph] $LOG 와 $DEV_DIR/progress.txt 를 확인한 뒤 조치 후 러너를 재실행하세요" >&2
      exit 2
      ;;
    "<ralph>CONTINUE</ralph>")
      : # 아래 드리프트 검사 후 계속
      ;;
    *)
      echo "[gx-ralph] ⛔ 종료 계약 미출력 (exit: $EXIT_CODE) — 세션 크래시/타임아웃 의심. $LOG 확인" >&2
      exit 3
      ;;
  esac

  POST_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "none")
  POST_AC=$(ac_hash)
  if [ "$PRE_HEAD" = "$POST_HEAD" ] && [ "$PRE_AC" = "$POST_AC" ]; then
    NO_DRIFT=$((NO_DRIFT+1))
    echo "[gx-ralph] 경고: 반복 $i 무변화 (연속 $NO_DRIFT회)"
    # 한계: verify 실패 반복도 attempts++로 원장이 변하므로 이 감지는 완전 무변화(크래시성)만 잡는다.
    # 실질 무진전은 AC별 attempts 상한(3회)과 MAX_ITER가 최종 방어한다.
    if [ "$NO_DRIFT" -ge 2 ]; then
      echo "[gx-ralph] ⛔ NO_DRIFT — 2회 연속 아무 변화 없음. 루프를 중단합니다" >&2
      exit 4
    fi
  else
    NO_DRIFT=0
  fi

  # last-known-head 갱신 (state.md 계약 필드)
  if grep -q "^last-known-head:" "$STATE" 2>/dev/null; then
    sed -i "s|^last-known-head:.*|last-known-head: $POST_HEAD|" "$STATE"
  fi

  i=$((i+1))
done

echo "[gx-ralph] ⛔ 최대 반복($MAX_ITER회) 소진 — 미완료 AC가 남았습니다" >&2
echo "[gx-ralph] /oh-my-gx:gx-ralph --status 로 상태 확인 후, 러너 재실행 또는 사람 개입을 결정하세요" >&2
exit 5
