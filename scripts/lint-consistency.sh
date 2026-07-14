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
#  8. RGR 보조 스킬 allowed-tools Skill 선언 (본문이 Skill 체이닝 지시)
#  9. gx-humanizer 에이전트 접두사 (bare humanizer-* 금지)
# 10. force-push deny 패턴 bare 형태 커버 (settings.json)
# 11. gx-ralph 상태 계약 정합 (판별 키·종료 계약 3파일·스키마 키·게이트 층간 대칭·템플릿)
# 12. gx-dev CORE 모드 계약 (Gate 필수·산출물 계약·레거시 매핑·폐지 모드 잔존 금지)
# 13. gx-tdd CORE 모드 계약 (RGR·G-W-T 게이트 유지·긴급 감사·레거시 매핑·폐지 모드 잔존 금지)
# 14. 모델 프로파일(standard/eco) 계약 (config 키·기록 규칙·eco 오버라이드·결정 로직·setup 단계)

set -uo pipefail
cd "$(dirname "$0")/.."

FAIL=0
fail() { echo "  FAIL: $1"; FAIL=1; }
ok()   { echo "  ok: $1"; }

echo "[1/14] 버전 3중 일치"
V_PLUGIN=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/plugin.json | head -1)
V_MARKET=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/marketplace.json | head -1)
V_CHANGE=$(sed -n 's/^## v\([0-9.]*\).*/\1/p' CHANGELOG.md | head -1)
if [ -n "$V_PLUGIN" ] && [ "$V_PLUGIN" = "$V_MARKET" ] && [ "$V_PLUGIN" = "$V_CHANGE" ]; then
  ok "plugin.json = marketplace.json = CHANGELOG = $V_PLUGIN"
else
  fail "버전 불일치: plugin.json=$V_PLUGIN marketplace.json=$V_MARKET CHANGELOG=$V_CHANGE"
fi

echo "[2/14] 서브에이전트 도구명 통일 (Task)"
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

echo "[3/14] RGR 드리프트 키워드"
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
grep -q "quality_verdict" agents/quality-reviewer.md \
  || fail "quality_verdict 블록 정의(producer) 누락: agents/quality-reviewer.md"
grep -q "quality_verdict" .claude/skills/gx-tdd/phases/phase-review.md \
  || fail "quality_verdict 파싱 규칙(consumer) 누락: phase-review.md"
grep -q "security_verdict" .claude/skills/gx-tdd/phases/phase-review.md \
  || fail "security_verdict 계약(Task B 프롬프트 producer + 파싱 consumer) 누락: phase-review.md"
[ "$FAIL" -eq 0 ] && ok "금지 목록 5항목×3파일, 재호출 상한, 프로젝트 루트 전달, spec_verdict 쌍"

echo "[4/14] verify 게이트 판별식 키 존재"
for f in .claude/rules/skill-routing.md .claude/rules/git-workflow.md \
         .claude/skills/gx-commit/SKILL.md .claude/skills/gx-pull-request/SKILL.md \
         .claude/skills/gx-tdd/SKILL.md; do
  grep -q "pipeline: gx-tdd" "$f" || fail "판별식 키(pipeline: gx-tdd) 누락: $f"
  grep -q "verify-status" "$f"   || fail "판별식 키(verify-status) 누락: $f"
done
# 훅은 gx-tdd·gx-ralph 두 파이프라인을 통합 정규식으로 인식해야 한다.
# 주석에 남은 리터럴이 아닌 코드 패턴 자체를 검사한다 (주석 의존 금지).
grep -qE 'pipeline: \(gx-tdd\|gx-ralph\)' .claude/hooks/pre-tool-guard.sh \
  || fail "훅 판별식이 통합 정규식(pipeline: (gx-tdd|gx-ralph))이 아님: pre-tool-guard.sh"
grep -q "verify-status" .claude/hooks/pre-tool-guard.sh \
  || fail "판별식 키(verify-status) 누락: pre-tool-guard.sh"
[ "$FAIL" -eq 0 ] && ok "판별식 키 5개 문서 + 훅 통합 정규식 확인"

echo "[5/14] 디스패치 이름 ↔ agents/ 대조"
BUILTIN="Explore general-purpose"
NAMES=$(grep -rhoE 'subagent_type="[^"]+"' .claude/skills 2>/dev/null | sed 's/subagent_type="//; s/"$//' | sort -u)
for n in $NAMES; do
  case "$n" in *'<'*|*'{'*) continue ;; esac  # 플레이스홀더 예시는 건너뜀
  base=${n#oh-my-gx:}
  case " $BUILTIN " in *" $base "*) continue ;; esac
  [ -f "agents/$base.md" ] || fail "agents/$base.md 없음 (디스패치 이름: $n)"
done
ok "디스패치 이름 전수 확인"

echo "[6/14] 셸 스크립트 CRLF 금지"
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

echo "[7/14] 훅 스크립트 문법"
if bash -n .claude/hooks/pre-tool-guard.sh 2>/dev/null; then
  ok "bash -n 통과"
else
  fail "pre-tool-guard.sh 문법 오류"
fi

echo "[8/14] Skill 체이닝 스킬의 Skill 선언"
for f in .claude/skills/gx-red/SKILL.md .claude/skills/gx-green/SKILL.md \
         .claude/skills/gx-refactor/SKILL.md .claude/skills/gx-verify/SKILL.md \
         .claude/skills/gx-ralph-iterate/SKILL.md; do
  awk '/^allowed-tools:/,/^---$/' "$f" | grep -qE '^[[:space:]]*-[[:space:]]*Skill[[:space:]]*$' \
    || fail "allowed-tools에 Skill 미선언 (본문이 Skill 체이닝 지시): $f"
done
[ "$FAIL" -eq 0 ] && ok "Skill 체이닝 5스킬 선언 확인"

echo "[9/14] gx-humanizer 에이전트 접두사"
if grep -qF '`humanizer-' .claude/skills/gx-humanizer/SKILL.md 2>/dev/null; then
  fail "gx-humanizer에 접두사 없는 에이전트 이름 잔존 (→ oh-my-gx:humanizer-*)"
else
  ok "humanizer 디스패치 접두사 정상"
fi

echo "[10/14] force-push deny 패턴 (bare 형태 커버)"
grep -qF 'Bash(*git push*--force*)' .claude/settings.json \
  || fail "settings.json deny에 'Bash(*git push*--force*)' 패턴 누락"
grep -qF 'Bash(*git push* -f)' .claude/settings.json \
  || fail "settings.json deny에 'Bash(*git push* -f)' (말단 -f) 패턴 누락"
grep -qF 'Bash(*git push* -f *)' .claude/settings.json \
  || fail "settings.json deny에 'Bash(*git push* -f *)' (중간 -f) 패턴 누락"
[ "$FAIL" -eq 0 ] && ok "deny 패턴 bare 형태 커버 확인"

echo "[11/14] gx-ralph 상태 계약 정합"
RALPH_ENTRY=.claude/skills/gx-ralph/SKILL.md
RALPH_ITER=.claude/skills/gx-ralph-iterate/SKILL.md
RALPH_RUNNER=scripts/gx-ralph.sh
for f in "$RALPH_ENTRY" "$RALPH_ITER"; do
  grep -q "pipeline: gx-ralph" "$f" || fail "판별식 키(pipeline: gx-ralph) 누락: $f"
  grep -q "verify-status" "$f"      || fail "판별식 키(verify-status) 누락: $f"
done
for token in '<ralph>COMPLETE</ralph>' '<ralph>CONTINUE</ralph>' '<ralph>BLOCKED:'; do
  for f in "$RALPH_ENTRY" "$RALPH_ITER" "$RALPH_RUNNER"; do
    grep -qF "$token" "$f" || fail "종료 계약 '$token' 누락: $f"
  done
done
for key in passes attempts last_error; do
  for f in "$RALPH_ENTRY" "$RALPH_ITER"; do
    grep -q "$key" "$f" || fail "ac-status 스키마 키($key) 누락: $f"
  done
done
# 스킬 층 verify 게이트·라우팅이 gx-ralph를 인식하는지 (훅 G3와 층간 대칭)
for f in .claude/skills/gx-commit/SKILL.md .claude/skills/gx-pull-request/SKILL.md .claude/rules/skill-routing.md; do
  grep -q "pipeline: gx-ralph" "$f" || fail "verify 게이트/라우팅이 gx-ralph 미인식: $f"
done
# 원장 id는 "AC-1" 형식 — 템플릿의 이중 접두사(AC-{id} → AC-AC-1) 금지
if grep -rn 'AC-{id}' "$RALPH_ENTRY" "$RALPH_ITER" >/dev/null 2>&1; then
  fail "이중 접두사 템플릿(AC-{id}) 잔존: $(grep -l 'AC-{id}' "$RALPH_ENTRY" "$RALPH_ITER" | tr '\n' ' ')"
fi
# dev/tdd 구현 진입 시 무인 루프 전환 질문이 두 파이프라인 모두에 존재 (드리프트 방지)
for f in .claude/skills/gx-dev/phases/phase-implement.md .claude/skills/gx-tdd/phases/phase-implement.md; do
  grep -q "ralph 무인 루프" "$f" || fail "구현 방식 확인(ralph 무인 루프 전환) 누락: $f"
done
# 복귀 안내 origin 분기 — gx-tdd 출발 루프가 gx-dev 리뷰(qa-manager)로 유도되지 않도록
grep -q '/gx-tdd --phase review' "$RALPH_ENTRY" \
  || fail "복귀 안내 origin 분기(/gx-tdd --phase review) 누락: $RALPH_ENTRY"
grep -q 'origin:' "$RALPH_RUNNER" \
  || fail "러너 COMPLETE 안내의 origin 분기 누락: $RALPH_RUNNER"
[ "$FAIL" -eq 0 ] && ok "판별 키·종료 계약 3파일·스키마 키·게이트 층간 대칭·템플릿 확인"

echo "[12/14] gx-dev CORE 모드 계약 정합"
GXDEV=.claude/skills/gx-dev/SKILL.md
CORE_PHASE=.claude/skills/gx-dev/phases/phase-core.md
# CORE 경로 등록 + Gate 필수 (core의 게이트 공백 회귀 방지)
[ -f "$CORE_PHASE" ] || fail "phase-core.md 없음"
grep -q "phase-core.md" "$GXDEV" || fail "SKILL.md에 phase-core 경로 미등록: $GXDEV"
grep -q "Mechanical Gate" "$CORE_PHASE" || fail "Mechanical Gate 지시 누락: $CORE_PHASE"
grep -q "건너뛰기 금지" "$CORE_PHASE" || fail "Gate 건너뛰기 금지 문구 누락: $CORE_PHASE"
# 산출물 계약 (ac.md·summary.md — producer와 consumer 양쪽)
for key in "ac.md" "summary.md"; do
  grep -q "$key" "$CORE_PHASE" || fail "산출물($key) 누락: $CORE_PHASE"
  grep -q "$key" .claude/skills/gx-dev/phases/phase-complete.md || fail "산출물($key) consumer 누락: phase-complete.md"
done
# 모드 값 정합 (SKILL.md 기록 규칙 ↔ complete 분기)
grep -q "mode: all | core" "$GXDEV" || fail "모드 값(all | core) 기록 규칙 누락: $GXDEV"
grep -q "핵심 모드" .claude/skills/gx-dev/phases/phase-complete.md || fail "phase-complete 핵심 모드 분기 누락"
# 레거시 호환 (--hotfix 매핑 + 구 세션 마이그레이션)
grep -q "핵심 모드로 실행됩니다" "$GXDEV" || fail "--hotfix 레거시 매핑 안내 누락: $GXDEV"
grep -q "레거시 모드 마이그레이션" .claude/skills/gx-dev/phases/phase-setup.md \
  || fail "레거시 모드 마이그레이션 규칙 누락: phase-setup.md"
# 폐지 모드·구 명칭 잔존 금지 (레거시 매핑·프리셋 명칭은 예외 — 모드 명칭 자체만 검사)
grep -q "HOTFIX 모드" "$GXDEV" && fail "폐지된 HOTFIX 모드 잔존: $GXDEV"
grep -q "경량 구현" "$GXDEV" && fail "폐지된 경량 구현 모드 잔존: $GXDEV"
grep -q "LIGHT 모드" "$GXDEV" && fail "구 명칭 LIGHT 모드 잔존: $GXDEV"
grep -q "Hotfix 모드 분기" .claude/skills/gx-dev/phases/phase-requirements.md \
  && fail "폐지된 Hotfix 분기 잔존: phase-requirements.md"
grep -q "경량 구현 모드 분기" .claude/skills/gx-dev/phases/phase-implement.md \
  && fail "폐지된 경량 구현 분기 잔존: phase-implement.md"
[ "$FAIL" -eq 0 ] && ok "CORE 경로·Gate 필수·산출물 계약·레거시 매핑·폐지 모드 부재 확인"

echo "[13/14] gx-tdd CORE 모드 계약 정합"
GXTDD=.claude/skills/gx-tdd/SKILL.md
TDD_REQ=.claude/skills/gx-tdd/phases/phase-requirements.md
TDD_IMPL=.claude/skills/gx-tdd/phases/phase-implement.md
# 모드 값 정합 + core 경로에서 Iron Law 유지 (RGR·verify 회귀 방지)
grep -q "mode: all | core" "$GXTDD" || fail "모드 값(all | core) 기록 규칙 누락: $GXTDD"
grep -q "Iron Law 유지 (core여도)" "$GXTDD" || fail "core Iron Law 유지 문구 누락: $GXTDD"
# requirements core 분기: 오케스트레이터 직접 ac.md + G-W-T 게이트 유지
grep -q "핵심 모드 분기" "$TDD_REQ" || fail "requirements core 분기 누락: $TDD_REQ"
grep -q "ac.md" "$TDD_REQ" || fail "core 산출물(ac.md) 누락: $TDD_REQ"
grep -qE "G-W-T 검증 게이트.*(동일하게|유지)" "$TDD_REQ" || fail "core G-W-T 게이트 유지 문구 누락: $TDD_REQ"
# implement core 분기: RGR 유지 + 긴급 감사 존재
grep -q "핵심 모드 분기" "$TDD_IMPL" || fail "implement core 분기 누락: $TDD_IMPL"
grep -q "RGR 사이클은 유지" "$TDD_IMPL" || fail "core RGR 유지 문구 누락: $TDD_IMPL"
grep -q "핵심 모드 전용 긴급 보안 감사" "$TDD_IMPL" || fail "core 긴급 보안 감사 섹션 누락: $TDD_IMPL"
# complete: core AC 자가 검증 분기 존재
grep -q "AC 자가 검증" .claude/skills/gx-tdd/phases/phase-complete.md \
  || fail "phase-complete core AC 자가 검증 분기 누락"
# 레거시 호환 (--hotfix 매핑 + 구 세션 마이그레이션)
grep -q "핵심 모드로 실행됩니다" "$GXTDD" || fail "--hotfix 레거시 매핑 안내 누락: $GXTDD"
grep -q "레거시 모드 마이그레이션" .claude/skills/gx-tdd/phases/phase-setup.md \
  || fail "레거시 모드 마이그레이션 규칙 누락: gx-tdd phase-setup.md"
# 폐지 모드·구 명칭 잔존 금지 (레거시 매핑 언급은 예외 — 모드 명칭 자체만 검사)
grep -q "HOTFIX 모드" "$GXTDD" && fail "폐지된 HOTFIX 모드 잔존: $GXTDD"
grep -q "LIGHT 모드" "$GXTDD" && fail "구 명칭 LIGHT 모드 잔존: $GXTDD"
grep -q "Hotfix 모드 분기" "$TDD_REQ" && fail "폐지된 Hotfix 분기 잔존: $TDD_REQ"
grep -q "Hotfix 모드 분기" "$TDD_IMPL" && fail "폐지된 Hotfix 분기 잔존: $TDD_IMPL"
[ "$FAIL" -eq 0 ] && ok "tdd core 경로·RGR/G-W-T 유지·긴급 감사·레거시 매핑·폐지 모드 부재 확인"

echo "[14/14] 모델 프로파일(standard/eco) 계약 정합"
grep -q '"modelProfile"' .claude/config.json || fail "config.json modelProfile 키 누락"
for f in "$GXDEV" "$GXTDD"; do
  grep -q "model-profile: standard | eco" "$f" || fail "model-profile 기록 규칙 누락: $f"
  grep -q "모델 프로파일 (MODEL_PROFILE)" "$f" || fail "모델 프로파일 공유 규칙 누락: $f"
  grep -q 'model: "sonnet"' "$f" || fail "eco 디스패치 오버라이드 문구 누락: $f"
  grep -q "architect는 eco에서도 opus" "$f" || fail "architect opus 유지 문구 누락: $f"
  grep -q 'header: "모델 프로파일"' "$f" || fail "Step 3 모드·프로파일 동시 질문 누락: $f"
done
for f in .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do
  grep -q "모델 프로파일 결정" "$f" || fail "MODEL_PROFILE 결정 로직 누락: $f"
done
grep -q "모델 프로파일" .claude/skills/gx-setup/SKILL.md || fail "gx-setup 모델 프로파일 단계 누락"
# 의미 정합: agents/*.md의 opus 집합 ↔ SKILL eco 하향 목록 (architect는 유지 원칙, humanizer 계열은 파이프라인 외)
ECO_LINES=$(grep "eco (에코 모드)" "$GXDEV" "$GXTDD")
for a in agents/*.md; do
  grep -q "^model: opus" "$a" || continue
  name=$(basename "$a" .md)
  case "$name" in architect|humanizer-*) continue ;; esac
  echo "$ECO_LINES" | grep -q "$name" || fail "opus 에이전트($name)가 eco 하향 목록에 없음 — SKILL.md 모델 프로파일 규칙 갱신 필요"
done
[ "$FAIL" -eq 0 ] && ok "config 키·기록 규칙·오버라이드·opus 집합 대조·결정 로직·setup 단계 확인"

echo
if [ "$FAIL" -ne 0 ]; then
  echo "정합성 린트 실패 — 위 FAIL 항목을 수정하세요."
  exit 1
fi
echo "정합성 린트 통과"
