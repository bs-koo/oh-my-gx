#!/usr/bin/env bash
# oh-my-gx 정합성 린트 — 스킬 전수 감사(v1.13.3)에서 도출된 불변식을 기계 검증한다.
# 사용: bash scripts/lint-consistency.sh (어디서 실행하든 저장소 루트 기준으로 동작)
#
# 검사 항목:
#  1. 버전 3중 일치 (plugin.json / marketplace.json / CHANGELOG 최신 섹션)
#  2. 서브에이전트 도구명 Task 통일 (Agent( 호출 문법·allowed-tools Agent 선언 금지)
#  3. RGR 드리프트 키워드 (refactor 금지 목록 3파일 일치, green 재호출 상한, 프로젝트 루트 전달)
#  4. verify 게이트 판별식 키 존재 (rules 2 + 스킬 3 + 훅 1)
#  5. 디스패치 이름 ↔ agents/ 정의 대조
#  6. 셸 스크립트 CRLF 금지
#  7. 훅 스크립트 bash 문법

set -uo pipefail
cd "$(dirname "$0")/.."

FAIL=0
fail() { echo "  FAIL: $1"; FAIL=1; }
ok()   { echo "  ok: $1"; }

echo "[1/7] 버전 3중 일치"
V_PLUGIN=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/plugin.json | head -1)
V_MARKET=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/marketplace.json | head -1)
V_CHANGE=$(sed -n 's/^## v\([0-9.]*\).*/\1/p' CHANGELOG.md | head -1)
if [ -n "$V_PLUGIN" ] && [ "$V_PLUGIN" = "$V_MARKET" ] && [ "$V_PLUGIN" = "$V_CHANGE" ]; then
  ok "plugin.json = marketplace.json = CHANGELOG = $V_PLUGIN"
else
  fail "버전 불일치: plugin.json=$V_PLUGIN marketplace.json=$V_MARKET CHANGELOG=$V_CHANGE"
fi

echo "[2/7] 서브에이전트 도구명 통일 (Task)"
if grep -rn 'Agent(subagent_type' .claude/skills >/dev/null 2>&1; then
  fail "Agent(subagent_type 호출 문법 잔존: $(grep -rl 'Agent(subagent_type' .claude/skills | tr '\n' ' ')"
else
  ok "Agent( 호출 문법 없음"
fi
if grep -rnE '^[[:space:]]*- Agent[[:space:]]*$' .claude/skills >/dev/null 2>&1; then
  fail "allowed-tools에 Agent 선언 잔존: $(grep -rlE '^[[:space:]]*- Agent[[:space:]]*$' .claude/skills | tr '\n' ' ')"
else
  ok "allowed-tools Agent 선언 없음"
fi

echo "[3/7] RGR 드리프트 키워드"
REFACTOR_FILES="agents/refactor-coder.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-refactor/SKILL.md"
for item in "동작 변경" "새 기능 추가" "에러 핸들링" "성능 최적화" "인터페이스 시그니처 변경"; do
  for f in $REFACTOR_FILES; do
    grep -q "$item" "$f" || fail "refactor 금지 항목 '$item' 누락: $f"
  done
done
grep -q "수행 불가능한 정리" .claude/skills/gx-refactor/SKILL.md \
  || fail "gx-refactor Task 프롬프트에 [수행 불가능한 정리] 누락"
grep -q "최대 2회" .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "green 재호출 상한(최대 2회) 누락: phase-implement.md"
grep -q "최대 2회" .claude/skills/gx-green/SKILL.md \
  || fail "green 재호출 상한(최대 2회) 누락: gx-green/SKILL.md"
for f in .claude/skills/gx-red/SKILL.md .claude/skills/gx-green/SKILL.md .claude/skills/gx-refactor/SKILL.md; do
  grep -q "프로젝트 루트" "$f" || fail "프로젝트 루트 전달 누락: $f"
done
grep -q "spec_verdict" agents/spec-reviewer.md \
  || fail "spec_verdict 블록 정의(producer) 누락: agents/spec-reviewer.md"
grep -q "spec_verdict" .claude/skills/gx-tdd/phases/phase-review.md \
  || fail "spec_verdict 파싱 규칙(consumer) 누락: phase-review.md"
[ "$FAIL" -eq 0 ] && ok "금지 목록 5항목×3파일, 재호출 상한, 프로젝트 루트 전달, spec_verdict 쌍"

echo "[4/7] verify 게이트 판별식 키 존재"
for f in .claude/rules/skill-routing.md .claude/rules/git-workflow.md \
         .claude/skills/gx-commit/SKILL.md .claude/skills/gx-pull-request/SKILL.md \
         .claude/skills/gx-tdd/SKILL.md .claude/hooks/pre-tool-guard.sh; do
  grep -q "pipeline: gx-tdd" "$f" || fail "판별식 키(pipeline: gx-tdd) 누락: $f"
  grep -q "verify-status" "$f"   || fail "판별식 키(verify-status) 누락: $f"
done
[ "$FAIL" -eq 0 ] && ok "판별식 키 6개 파일 존재"

echo "[5/7] 디스패치 이름 ↔ agents/ 대조"
BUILTIN="Explore general-purpose"
NAMES=$(grep -rhoE 'subagent_type="[^"]+"' .claude/skills 2>/dev/null | sed 's/subagent_type="//; s/"$//' | sort -u)
for n in $NAMES; do
  case "$n" in *'<'*|*'{'*) continue ;; esac  # 플레이스홀더 예시는 건너뜀
  base=${n#oh-my-gx:}
  case " $BUILTIN " in *" $base "*) continue ;; esac
  [ -f "agents/$base.md" ] || fail "agents/$base.md 없음 (디스패치 이름: $n)"
done
ok "디스패치 이름 전수 확인"

echo "[6/7] 셸 스크립트 CRLF 금지"
# 이식성 주의: grep -P는 macOS(BSD grep)에서 미지원이고, $'\r' 인자는 Git Bash(MSYS2)에서
# 변환되어 빈 패턴이 되므로 모든 줄에 매칭(오탐)된다. tr|cmp 비교는 세 환경 모두에서 동작한다.
CRLF=""
while IFS= read -r f; do
  if ! tr -d '\r' < "$f" | cmp -s - "$f"; then
    CRLF="$CRLF $f"
  fi
done < <(find .claude scripts -name '*.sh' -type f 2>/dev/null)
if [ -z "$CRLF" ]; then
  ok "CRLF 없음"
else
  fail "CRLF 포함 스크립트:$CRLF"
fi

echo "[7/7] 훅 스크립트 문법"
if bash -n .claude/hooks/pre-tool-guard.sh 2>/dev/null; then
  ok "bash -n 통과"
else
  fail "pre-tool-guard.sh 문법 오류"
fi

echo
if [ "$FAIL" -ne 0 ]; then
  echo "정합성 린트 실패 — 위 FAIL 항목을 수정하세요."
  exit 1
fi
echo "정합성 린트 통과"
