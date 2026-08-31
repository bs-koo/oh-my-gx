#!/usr/bin/env bash
# oh-my-gx 정합성 린트 — 스킬 전수 감사(v1.13.3)에서 도출된 불변식을 기계 검증한다.
# 사용: bash scripts/lint-consistency.sh (어디서 실행하든 저장소 루트 기준으로 동작)
#
# 검사 항목:
#  1. 버전 4중 일치 (.claude-plugin/plugin.json / marketplace.json / .codex-plugin/plugin.json / CHANGELOG)
#  2. 서브에이전트 도구명 Task 통일 (Agent( 호출 문법·allowed-tools Agent 선언 금지)
#  3. RGR 드리프트 키워드 (refactor 금지 목록 3파일 일치, green 재호출 상한, 프로젝트 루트 전달)
#  4. verify 게이트 판별식 키 존재 (rules 2 + 스킬 3 + 훅 1)
#  5. 디스패치 이름 ↔ agents/ 정의 대조
#  6. 셸 스크립트 CRLF 금지
#  7. 훅 스크립트 bash 문법
#  8. RGR 보조 스킬 allowed-tools Skill 선언 (본문이 Skill 체이닝 지시)
#  9. gx-humanizer 에이전트 접두사 (bare humanizer-* 금지)
# 10. force-push deny 패턴 bare 형태 커버 (settings.json)
# 11. gx-ralph 상태 계약 정합 (판별 키·종료 계약 3파일·스키마 키·게이트 층간 대칭·템플릿·러너 allowedTools 동기)
# 12. gx-dev CORE 모드 계약 (Gate 필수·산출물 계약·구 버전 방어·폐지 모드 잔존 금지)
# 13. gx-tdd CORE 모드 계약 (RGR·G-W-T 게이트 유지·긴급 감사·구 버전 방어·폐지 모드 잔존 금지)
# 14. 모델 프로파일(standard/eco) 계약 (config 키·기록 규칙·eco 오버라이드·결정 로직·setup 단계)
# 15. 번들 경로 규약(하네스 중립 상대경로) + config.json 부트스트랩 (v1.19.0, 상대경로 전환)
# 16. phase-complete context 커밋 예외 대칭 (헤더·skill-routing) + gx-dev 레거시 Read 제거 (v1.19.0)
# 17. force-push 훅 가드 G4 (v1.19.0)
# 18. SVN .dev/.active 포인터 계약 (producer·consumer·폴백) (v1.19.0)
# 19. cross-review fallback 3원 조건 단일화 + humanizer 영어 P1 치트시트(E2/E5/E6) (v1.19.0)
# 20. 언어 중립화 projectTypes SSOT 계약 (v1.21.0)
# 21. .dev 협업 공유 계약 (v1.21.0)
# 22. 리뷰 후속 v1.21.1 계약 (사용자 문서·경계 밖 소비 지점)
# 23. 프론트엔드 테스트 규약 계약 (셀렉터 3중 동기·레이어 하네스 게이트·표현 속성 배제·UI 안티패턴)
# 24. 하네스·복수 타입 검증 계약 (등록 검증·복합 타입·프론트 힌트·복수 명령 실행·헤드리스 처리·구축 가이드)
# 25. 작업 계획(.dev/plan.md) 계약 — --work 인자·읽기·갱신·커밋 규칙의 3지점 문구 대조

set -uo pipefail
cd "$(dirname "$0")/.."

FAIL=0
fail() { echo "  FAIL: $1"; FAIL=1; }
ok()   { echo "  ok: $1"; }

echo "[1/25] 버전 4중 일치"
# Codex 매니페스트(.codex-plugin/plugin.json)도 같은 버전을 싣는다 — 어긋나면 Codex UI에 옛 버전이 뜬다
V_PLUGIN=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/plugin.json | head -1)
V_MARKET=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/marketplace.json | head -1)
V_CODEX=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .codex-plugin/plugin.json | head -1)
V_CHANGE=$(sed -n 's/^## v\([0-9.]*\).*/\1/p' CHANGELOG.md | head -1)
if [ -n "$V_PLUGIN" ] && [ "$V_PLUGIN" = "$V_MARKET" ] && [ "$V_PLUGIN" = "$V_CODEX" ] && [ "$V_PLUGIN" = "$V_CHANGE" ]; then
  ok "plugin.json = marketplace.json = codex-plugin = CHANGELOG = $V_PLUGIN"
else
  fail "버전 불일치: plugin.json=$V_PLUGIN marketplace.json=$V_MARKET codex-plugin=$V_CODEX CHANGELOG=$V_CHANGE"
fi

echo "[2/25] 서브에이전트 도구명 통일 (Task)"
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

echo "[3/25] RGR 드리프트 키워드"
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

echo "[4/25] verify 게이트 판별식 키 존재"
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
# verify 지문 계약: 게이트 4층(훅·라우팅·commit·PR) + 생산자(gx-verify)·기록자(phase-complete)가 모두 인지해야 한다
for f in .claude/rules/skill-routing.md .claude/skills/gx-commit/SKILL.md \
         .claude/skills/gx-pull-request/SKILL.md .claude/skills/gx-tdd/SKILL.md \
         .claude/skills/gx-verify/SKILL.md .claude/skills/gx-tdd/phases/phase-complete.md; do
  grep -q "verify-fingerprint" "$f" || fail "verify 지문 계약 누락: $f"
done
grep -q "compute_fingerprint" .claude/hooks/pre-tool-guard.sh \
  || fail "훅 지문 계산 함수(compute_fingerprint) 누락: pre-tool-guard.sh"
# 지문 계산 규약이 훅·gx-verify·회귀 테스트에서 동일해야 한다
# (임시 인덱스 트리 해시 + .dev 인덱스 제거 — git diff HEAD 방식은 신규 파일 스테이징 시 값이 바뀐다)
for f in .claude/hooks/pre-tool-guard.sh .claude/skills/gx-verify/SKILL.md scripts/hook-tests.sh; do
  grep -qF 'GIT_INDEX_FILE' "$f" || fail "지문 계산의 임시 인덱스 규약 누락: $f"
  grep -qF 'rm -r --cached -q --ignore-unmatch .dev' "$f" || fail "지문 계산의 .dev 제외 규약 누락: $f"
  grep -qF 'write-tree' "$f" || fail "지문 계산의 트리 해시 규약 누락: $f"
done
[ "$FAIL" -eq 0 ] && ok "판별식 키 5개 문서 + 훅 통합 정규식 + 지문 계약 6곳·계산 규약 3곳 확인"

echo "[5/25] 디스패치 이름 ↔ agents/ 대조"
BUILTIN="Explore general-purpose"
NAMES=$(grep -rhoE 'subagent_type="[^"]+"' .claude/skills 2>/dev/null | sed 's/subagent_type="//; s/"$//' | sort -u)
for n in $NAMES; do
  case "$n" in *'<'*|*'{'*) continue ;; esac  # 플레이스홀더 예시는 건너뜀
  base=${n#oh-my-gx:}
  case " $BUILTIN " in *" $base "*) continue ;; esac
  [ -f "agents/$base.md" ] || fail "agents/$base.md 없음 (디스패치 이름: $n)"
done
ok "디스패치 이름 전수 확인"

echo "[6/25] 셸 스크립트 CRLF 금지"
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

echo "[7/25] 훅 스크립트 문법"
if bash -n .claude/hooks/pre-tool-guard.sh 2>/dev/null; then
  ok "bash -n 통과"
else
  fail "pre-tool-guard.sh 문법 오류"
fi

echo "[8/25] Skill 체이닝 스킬의 Skill 선언"
for f in .claude/skills/gx-red/SKILL.md .claude/skills/gx-green/SKILL.md \
         .claude/skills/gx-refactor/SKILL.md .claude/skills/gx-verify/SKILL.md \
         .claude/skills/gx-ralph-iterate/SKILL.md; do
  awk '/^allowed-tools:/,/^---$/' "$f" | grep -qE '^[[:space:]]*-[[:space:]]*Skill[[:space:]]*$' \
    || fail "allowed-tools에 Skill 미선언 (본문이 Skill 체이닝 지시): $f"
done
[ "$FAIL" -eq 0 ] && ok "Skill 체이닝 5스킬 선언 확인"

echo "[9/25] gx-humanizer 에이전트 접두사"
if grep -qF '`humanizer-' .claude/skills/gx-humanizer/SKILL.md 2>/dev/null; then
  fail "gx-humanizer에 접두사 없는 에이전트 이름 잔존 (→ oh-my-gx:humanizer-*)"
else
  ok "humanizer 디스패치 접두사 정상"
fi

echo "[10/25] force-push deny 패턴 (bare 형태 커버)"
grep -qF 'Bash(*git push*--force*)' .claude/settings.json \
  || fail "settings.json deny에 'Bash(*git push*--force*)' 패턴 누락"
grep -qF 'Bash(*git push* -f)' .claude/settings.json \
  || fail "settings.json deny에 'Bash(*git push* -f)' (말단 -f) 패턴 누락"
grep -qF 'Bash(*git push* -f *)' .claude/settings.json \
  || fail "settings.json deny에 'Bash(*git push* -f *)' (중간 -f) 패턴 누락"
[ "$FAIL" -eq 0 ] && ok "deny 패턴 bare 형태 커버 확인"

echo "[11/25] gx-ralph 상태 계약 정합"
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
# dev/tdd phase-implement에 gx-ralph 전환 절(--ralph opt-in)이 두 파이프라인 모두에 존재 (드리프트 방지)
# + 폐지된 진입 질문이 되살아나지 않도록 "구현 방식 확인" 문구 잔존 금지 (v1.23.0 격하)
grep -q '^## Step 0.7: gx-ralph 전환 (--ralph 전용)' .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "gx-tdd phase-implement Step 0.7 전환 절 헤더 누락"
grep -q '^## gx-ralph 전환 (--ralph 전용)' .claude/skills/gx-dev/phases/phase-implement.md \
  || fail "gx-dev phase-implement 전환 절 헤더 누락"
for f in .claude/skills/gx-dev/phases/phase-implement.md .claude/skills/gx-tdd/phases/phase-implement.md; do
  grep -q '`--resume` 재진입은 방어 조건이 \*\*아니다\*\*' "$f" || fail "전환 절 --resume 비방어 규칙 누락: $f"
done
# dev/tdd 쌍둥이 opt-in 규칙 문구 대조 (의도 파싱) + phase-setup flags 기록 기준
for key in 'RALPH 추출:' 'RALPH 우선순위 규칙' 'svn 우선 배제' '모드 질문 생략 규칙' '`--ralph`와 `--core`'; do
  for f in .claude/skills/gx-dev/SKILL.md .claude/skills/gx-tdd/SKILL.md; do
    grep -qF "$key" "$f" || fail "RALPH 쌍둥이 규칙($key) 누락: $f"
  done
done
for f in .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do
  grep -q '무시된 RALPH는 기록하지 않는다' "$f" || fail "phase-setup Step 7 --ralph 기록 기준(무시된 RALPH 미기록) 누락: $f"
done
# 폐지된 진입 질문 문구 잔존 금지 — 스킬 디렉토리 전체 ([12]/[13]과 같은 관례)
if grep -rl "구현 방식 확인" .claude/skills >/dev/null 2>&1; then
  fail "폐지된 ralph 진입 질문(구현 방식 확인) 잔존: $(grep -rl '구현 방식 확인' .claude/skills | tr '\n' ' ')"
fi
# skill-routing이 '랄프로 …' 발화를 --ralph 전환으로 라우팅 (gx-ralph 직접 호출로 새지 않도록)
grep -q -- '--ralph' .claude/rules/skill-routing.md || fail "skill-routing에 --ralph 전환 라우팅 행 누락"
# 러너 --allowedTools ↔ gx-ralph-iterate allowed-tools 집합 동기 — 러너만 누락되면 헤드리스 세션이
# 해당 test 명령을 실행하지 못해 매 반복 verify 차단 → attempts 소진 → BLOCKED로 낭비된다 (v1.21.0 회귀)
TOOLS_DIFF=$(diff <(sed -n '/^allowed-tools:/,/^---/p' "$RALPH_ITER" | tr -d '\r' | grep '^  - ' | sed 's/^  - //' | sort) \
                  <(grep '^ALLOWED_TOOLS=' "$RALPH_RUNNER" | sed 's/^ALLOWED_TOOLS="//; s/"$//' | tr ',' '\n' | sort) \
             | grep '^[<>]' | tr '\n' ' ')
[ -z "$TOOLS_DIFF" ] || fail "러너 ALLOWED_TOOLS가 gx-ralph-iterate allowed-tools와 불일치 (<: iterate에만, >: 러너에만): $TOOLS_DIFF"
# 복귀 안내 origin 분기 — gx-tdd 출발 루프가 gx-dev 리뷰(qa-manager)로 유도되지 않도록
grep -q '/gx-tdd --phase review' "$RALPH_ENTRY" \
  || fail "복귀 안내 origin 분기(/gx-tdd --phase review) 누락: $RALPH_ENTRY"
grep -q 'origin:' "$RALPH_RUNNER" \
  || fail "러너 COMPLETE 안내의 origin 분기 누락: $RALPH_RUNNER"
[ "$FAIL" -eq 0 ] && ok "판별 키·종료 계약 3파일·스키마 키·게이트 층간 대칭·템플릿·러너 allowedTools 동기 확인"

echo "[12/25] gx-dev CORE 모드 계약 정합"
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
# 구 버전 세션 방어 (v1.18.0: 레거시 모드 호환 제거)
grep -q "구 버전 세션 방어" .claude/skills/gx-dev/phases/phase-setup.md \
  || fail "구 버전 세션 방어 규칙 누락: phase-setup.md"
# 레거시·폐지 모드 잔존 금지 (v1.18.0: --hotfix 플래그·구 명칭 hotfix/light 완전 제거 — 자연어 '핫픽스'는 한글이라 무관)
grep -rqi "hotfix" .claude/skills/gx-dev && fail "레거시 hotfix 잔존: gx-dev"
grep -rqiE "\blight\b" .claude/skills/gx-dev && fail "구 명칭 light 잔존: gx-dev"
grep -q "HOTFIX 모드" "$GXDEV" && fail "폐지된 HOTFIX 모드 잔존: $GXDEV"
grep -q "경량 구현" "$GXDEV" && fail "폐지된 경량 구현 모드 잔존: $GXDEV"
[ "$FAIL" -eq 0 ] && ok "CORE 경로·Gate 필수·산출물 계약·구 버전 방어·폐지 모드 부재 확인"

echo "[13/25] gx-tdd CORE 모드 계약 정합"
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
# 구 버전 세션 방어 (v1.18.0: 레거시 모드 호환 제거)
grep -q "구 버전 세션 방어" .claude/skills/gx-tdd/phases/phase-setup.md \
  || fail "구 버전 세션 방어 규칙 누락: gx-tdd phase-setup.md"
# 레거시·폐지 모드 잔존 금지 (v1.18.0: --hotfix 플래그·구 명칭 hotfix/light 완전 제거 — 자연어 '핫픽스'는 한글이라 무관)
grep -rqi "hotfix" .claude/skills/gx-tdd && fail "레거시 hotfix 잔존: gx-tdd"
grep -rqiE "\blight\b" .claude/skills/gx-tdd && fail "구 명칭 light 잔존: gx-tdd"
grep -q "HOTFIX 모드" "$GXTDD" && fail "폐지된 HOTFIX 모드 잔존: $GXTDD"
[ "$FAIL" -eq 0 ] && ok "tdd core 경로·RGR/G-W-T 유지·긴급 감사·구 버전 방어·폐지 모드 부재 확인"

echo "[14/25] 모델 프로파일(standard/eco) 계약 정합"
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
  echo "$ECO_LINES" | grep -qE "[^-a-z]$name|^$name" || fail "opus 에이전트($name)가 eco 하향 목록에 없음 — SKILL.md 모델 프로파일 규칙 갱신 필요"
done
[ "$FAIL" -eq 0 ] && ok "config 키·기록 규칙·오버라이드·opus 집합 대조·결정 로직·setup 단계 확인"

echo "[15/25] 번들 경로 규약(상대경로) + config 부트스트랩"
# 하네스 중립 규약: 번들 파일은 그 지시가 적힌 파일 기준 상대경로로 읽는다.
# ${CLAUDE_PLUGIN_ROOT} 기반 절대경로 조립은 Codex 설치 구조에서 깨진다 —
# Codex 스킬 루트에는 .claude/skills/ 중간 경로가 없고 변수 설정도 보장되지 않는다.
# (.claude/rules/harness-codex.md "동작하지 않는 것" 참조)
if grep -rn 'CLAUDE_PLUGIN_ROOT' .claude/skills >/dev/null 2>&1; then
  fail "설치 위치 의존 경로 잔존 — 상대경로로 전환할 것: $(grep -rl 'CLAUDE_PLUGIN_ROOT' .claude/skills | tr '\n' ' ')"
fi
if grep -rn '프로젝트 루트>/\.claude/skills' .claude/skills >/dev/null 2>&1; then
  fail "레거시 경로 표기('<프로젝트 루트>/.claude/skills') 잔존: $(grep -rl '프로젝트 루트>/\.claude/skills' .claude/skills | tr '\n' ' ')"
fi
for f in .claude/skills/gx-dev/SKILL.md .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-lens/SKILL.md; do
  grep -q '상대경로' "$f" || fail "번들 경로 규약(상대경로) 설명 누락: $f"
done
grep -q 'Read("\.\./\.\./config\.json")' .claude/skills/gx-setup/SKILL.md \
  || fail "gx-setup config.json 번들 템플릿 생성 단계 누락"
# 상대경로가 실제 파일을 가리키는지 (오타·파일 이동 방어 — 절대경로 조립을 버린 대가로 필수)
while IFS=: read -r f ref; do
  [ -z "$ref" ] && continue
  case "$ref" in *[\{\<\$\*]*|.claude/*|/*) continue ;; esac
  d=$(dirname "$f")
  [ -f "$d/$ref" ] || fail "번들 참조 대상 없음: ${f#.claude/skills/} → Read($ref)"
done < <(grep -rHoE 'Read\(["`]?[A-Za-z0-9_./-]+\.(md|json)["`]?\)' .claude/skills --include='*.md' 2>/dev/null \
         | grep -v 'skill-creator' \
         | sed -E 's/:Read\(["`]?/:/; s/["`]?\)$//')
[ "$FAIL" -eq 0 ] && ok "상대경로 규약·참조 실존·config 부트스트랩 확인"

echo "[16/25] phase-complete context 커밋 예외 대칭 + 레거시 Read 제거"
grep -q "유일한 예외" .claude/skills/gx-dev/phases/phase-complete.md \
  || fail "phase-complete 헤더 context 커밋 예외 누락"
grep -q "context 변경사항 자동 커밋" .claude/rules/skill-routing.md \
  || fail "skill-routing context 커밋 예외 누락"
grep -q "다른 스킬의 프로세스를 실행할 때 아래 경로에서 Read한다" .claude/skills/gx-dev/SKILL.md \
  && fail "gx-dev 레거시 'Read한다' 형제 스킬 지시 잔존"
[ "$FAIL" -eq 0 ] && ok "context 커밋 예외 헤더·라우팅 + 레거시 Read 제거 확인"

echo "[17/25] force-push 훅 가드 G4"
grep -q "force-push 차단" .claude/hooks/pre-tool-guard.sh || fail "훅 force-push 가드(G4) 주석 누락"
grep -qF '*"--force"*' .claude/hooks/pre-tool-guard.sh || fail "훅 force-push 패턴(--force) 누락"
[ "$FAIL" -eq 0 ] && ok "force-push 훅 가드 확인"

echo "[18/25] SVN .dev/.active 포인터 계약"
for f in .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do
  grep -qF '.dev/.active' "$f" || fail "svn .dev/.active producer 누락: $f"
done
for f in .claude/hooks/pre-tool-guard.sh .claude/rules/skill-routing.md .claude/rules/git-workflow.md .claude/skills/gx-verify/SKILL.md; do
  grep -qF '.dev/.active' "$f" || fail "svn .dev/.active consumer 누락: $f"
done
grep -q 'ACTIVE_SLUG' .claude/hooks/pre-tool-guard.sh || fail "훅 ACTIVE_SLUG 해석 누락"
[ "$FAIL" -eq 0 ] && ok "SVN .dev/.active producer·consumer·폴백 확인"

echo "[19/25] cross-review fallback 3원 조건 + humanizer P1 커버리지"
if grep -qF 'prd.md/design.md 둘 다 없으면' .claude/skills/gx-cross-review/SKILL.md; then
  fail "cross-review fallback 구 조건(prd/design 둘 다) 잔존"
fi
grep -qF 'prd.md·ac.md·design.md 셋 다 없으면' .claude/skills/gx-cross-review/SKILL.md \
  || fail "cross-review fallback 3원 조건(prd·ac·design 셋 다) 누락"
for code in E2 E5 E6; do
  awk '/### 영어 즉시 수정/{p=1} /### 영어 맥락 판단/{p=0} p' .claude/skills/gx-humanizer/SKILL.md \
    | grep -q "^| $code " || fail "humanizer 영어 P1 치트시트에 $code 누락"
done
[ "$FAIL" -eq 0 ] && ok "cross-review fallback 3원 + humanizer P1(E2/E5/E6) 확인"

echo "[20/25] 언어 중립화(projectTypes SSOT) 계약 정합"
# --- PR1: config 신규 필드 + gx-verify 일반화 + 카탈로그 + gx-setup 등록 단계 ---
grep -q '"warningPattern"' .claude/config.json || fail "config 템플릿에 warningPattern 필드 누락"
grep -q '"artifacts"' .claude/config.json || fail "config 템플릿에 artifacts 필드 누락"
grep -q 'warningPattern' .claude/skills/gx-verify/SKILL.md || fail "gx-verify 경고 규약이 warningPattern 미참조"
grep -q 'SSOT는 config' .claude/skills/gx-verify/SKILL.md || fail "gx-verify 명령 표 SSOT 문구 누락"
CATALOG=.claude/skills/gx-setup/references/project-type-hints.md
[ -f "$CATALOG" ] || fail "힌트 카탈로그 없음: $CATALOG"
grep -q 'java-spring' "$CATALOG" || fail "카탈로그-템플릿 정합: 기본 타입(java-spring) 행 부재"
grep -q 'SSOT가 아니다' "$CATALOG" || fail "카탈로그 SSOT 아님 명시 문구 부재"
grep -q '프로젝트 타입 등록' .claude/skills/gx-setup/SKILL.md || fail "gx-setup 프로젝트 타입 등록 단계 누락"
grep -q 'java 계열' .claude/skills/gx-setup/SKILL.md || fail "gx-setup JDK 조건화 누락"
# --- PR2: 파이프라인 소비 지점 (phase-setup·phase-review·하네스 감지·allowed-tools) ---
for f in .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do
  grep -q '프로젝트 타입 등록' "$f" || fail "phase-setup 인라인 등록 연동 누락: $f"
  grep -q 'artifacts' "$f" || fail "phase-setup ignore 보강이 artifacts 미참조: $f"
done
for f in .claude/skills/gx-dev/phases/phase-review.md .claude/skills/gx-tdd/phases/phase-review.md; do
  grep -q 'SSOT는 config' "$f" || fail "phase-review 빌드 표 SSOT 문구 누락: $f"
done
grep -q '테스트 하네스 부재' .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "phase-implement 하네스 부재 감지 누락"
for f in .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md .claude/skills/gx-ralph-iterate/SKILL.md; do
  grep -qF 'Bash(make *)' "$f" || fail "allowed-tools 대표 도구(make) 누락: $f"
  grep -qF 'Bash(ceedling *)' "$f" || fail "allowed-tools 대표 도구(ceedling) 누락: $f"
done
[ "$FAIL" -eq 0 ] && ok "projectTypes SSOT(코어+파이프라인)·카탈로그·등록 단계·JDK 조건화·하네스 감지·allowed-tools 확인"

echo "[21/25] .dev 협업 공유 계약"
for f in .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md; do
  grep -q '패턴도 이 단계에서 함께 추가한다' "$f" && fail ".dev ignore 추가 로직 잔존: $f"
  grep -q '협업 공유 대상' "$f" || fail ".dev 공유 문구 누락: $f"
done
grep -q 'echo .dev' .claude/skills/gx-tdd/phases/phase-setup.md && fail "svn:ignore .dev 추가 명령 잔존: gx-tdd phase-setup"
for f in .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md; do
  grep -q '협업 공유 대상' "$f" || fail "문서 보관 규칙 .dev 공유 미반영: $f"
done
[ "$FAIL" -eq 0 ] && ok ".dev 공유 문구·ignore 로직 제거 확인"

echo "[22/25] 리뷰 후속(v1.21.1) 계약 정합"
# C2: guide.md 등록 예시 — test 필드 존재 + collect-only 플래그 금지 (복사 사용자가 verify에 차단되는 결함)
grep -qF '"test": "pytest"' docs/guide.md || fail "guide.md 등록 예시에 test 필드 누락"
grep -qF 'pytest --co' docs/guide.md && fail "guide.md 예시에 collect-only 플래그 잔존"
# I6/I7: 사용자 문서 언어 중립 서술
grep -q '언어 중립' docs/guide.md || fail "guide.md 언어 중립 서술 누락"
grep -qE '언어 중립|모든 언어' _config.yml || fail "_config.yml description 언어 중립 미반영"
# I3: 저장소 자신의 .dev 공유 계약 준수
grep -qE '^\.dev/?$' .gitignore && fail "저장소 .gitignore에 .dev 잔존 (자기 계약 위반)"
# I4: gx-commit 아티팩트 가드의 projectTypes.artifacts 소비
grep -q 'projectTypes.*artifacts' .claude/skills/gx-commit/SKILL.md || fail "gx-commit이 projectTypes.artifacts 미참조"
# C3: svn 신규 파일 add 지시 (RGR 신규 파일이 diff에 실리도록)
for f in .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-dev/phases/phase-implement.md; do
  grep -q 'svn add' "$f" || fail "svn add 지시 누락: $f"
done
# C4: .active 공유 제외
grep -qF "svn propset svn:ignore '.active'" .claude/skills/gx-tdd/phases/phase-setup.md || fail ".active 공유 제외 propset 누락: gx-tdd phase-setup"
# C1: 지문 대조 트리 성분 특례 (훅 + 문서 3곳 동기)
grep -q '트리 성분' .claude/hooks/pre-tool-guard.sh || fail "훅 지문 대조 트리 성분 특례 누락"
for f in .claude/rules/skill-routing.md .claude/skills/gx-commit/SKILL.md .claude/skills/gx-pull-request/SKILL.md; do
  grep -q '트리 성분' "$f" || fail "지문 트리 성분 대조 문구 누락: $f"
done
# I5: 낡은 단계 포인터 금지
grep -qF 'Step 3.5' .claude/skills/gx-tdd/phases/phase-setup.md && fail "낡은 포인터(Step 3.5) 잔존: gx-tdd phase-setup"
# I2: 리뷰 diff의 .dev 제외 pathspec
for f in .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md; do
  grep -qF ':(exclude).dev' "$f" || fail "Diff 수집 규칙 .dev 제외 누락: $f"
done
[ "$FAIL" -eq 0 ] && ok "guide/Pages 문서·.gitignore·gx-commit·svn add·.active·지문 트리 대조·diff 제외 확인"

echo "[23/25] 프론트엔드 테스트 규약 계약"
FE_REF=.claude/skills/gx-tdd/references/frontend-testing.md
[ -f "$FE_REF" ] || fail "프론트 테스트 규약 참조 파일 누락: $FE_REF"
# 셀렉터 규약 3중 동기 (red-writer 자기완결성 ↔ 파이프라인 프롬프트 ↔ 단독 스킬)
for f in agents/red-writer.md .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-red/SKILL.md; do
  grep -q 'data-testid' "$f" || fail "UI 셀렉터 규약 누락 (3중 동기 대상): $f"
  grep -q '스타일 값' "$f" || fail "스타일 assert 금지 문구 누락 (3중 동기 대상): $f"
done
# 레이어별 하네스 게이트 (프론트 러너 부재 시 사용자 분기)
grep -q '레이어별 하네스' .claude/skills/gx-tdd/phases/phase-implement.md   || fail "레이어별 하네스 게이트 누락: gx-tdd phase-implement.md"
grep -q '프론트 AC 제외' .claude/skills/gx-tdd/phases/phase-implement.md   || fail "하네스 게이트 분기(프론트 AC 제외) 누락: gx-tdd phase-implement.md"
# 표현 속성은 AC가 아니다 (G-W-T 게이트)
grep -q '표현 속성' .claude/skills/gx-tdd/phases/phase-requirements.md   || fail "표현 속성 배제 규칙 누락: gx-tdd phase-requirements.md"
# test-architect의 표현/동작 레이어 구분
grep -q '표현 레이어' .claude/skills/gx-tdd/phases/phase-design.md   || fail "표현/동작 레이어 구분 누락: gx-tdd phase-design.md"
# UI 안티패턴 (기존 5종은 모의 중심 — UI 결합 패턴이 별도로 있어야 red-writer가 판정 가능)
grep -q 'Anti-Pattern 6' .claude/skills/gx-tdd/references/testing-anti-patterns.md   || fail "UI 안티패턴 섹션 누락: testing-anti-patterns.md"
# 낡은 표기 금지 — 태스크는 순차 실행이므로 "배치 병렬 조건"은 사실과 다름
grep -qF '배치 병렬 조건' .claude/skills/gx-tdd/phases/phase-implement.md   && fail "사실과 다른 표기(배치 병렬 조건) 잔존: gx-tdd phase-implement.md — 태스크는 순차 실행"
[ "$FAIL" -eq 0 ] && ok "참조 파일·셀렉터 3중 동기·하네스 게이트·표현 속성 배제·UI 안티패턴·순차 표기 확인"
echo "[24/25] 하네스·복수 타입 검증 계약"
GXSETUP=.claude/skills/gx-setup/SKILL.md
CATALOG2=.claude/skills/gx-setup/references/project-type-hints.md
# G1: 등록한 명령을 실제 실행해 하네스 상태를 확인 (기존 등록 유지 경로 포함)
grep -q '하네스 확인' "$GXSETUP" || fail "gx-setup 하네스 확인 단계 누락 (등록 명령 미실행)"
grep -q '기존 등록 유지' "$GXSETUP" || fail "gx-setup 기존 등록 경로에도 하네스 확인 적용 누락"
# G2: 모노레포 복합 타입 선택지 (주 타입 하나만 고르면 나머지 레이어가 영구 미검증)
grep -q '복합 타입' "$GXSETUP" || fail "gx-setup 복합 타입(모노레포) 선택지 누락"
grep -q '복합 타입' "$CATALOG2" || fail "힌트 카탈로그 복합 타입 안내 누락"
# G3: 프론트 테스트 러너 힌트 (node의 npm test 기본값은 프론트에서 대개 부재)
grep -q 'vitest' "$CATALOG2" || fail "힌트 카탈로그 프론트 러너(vitest) 행 누락"
# G4/G5: 복수 타입 감지 시 전부 실행 (verify·mechanical gate·기준선 게이트)
grep -q '복수 타입' .claude/skills/gx-verify/SKILL.md || fail "gx-verify 복수 타입 실행 규칙 누락"
for f in .claude/skills/gx-tdd/phases/phase-review.md .claude/skills/gx-tdd/phases/phase-implement.md          .claude/skills/gx-dev/phases/phase-review.md; do
  grep -q '복수 타입' "$f" || fail "복수 타입 실행 규칙 누락: $f"
done
# 인라인 등록 절차 열거에 하네스 확인 반영 (gx-setup 단계 추가에 따른 드리프트 방지)
for f in .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do
  grep -q '권한 등록 → 하네스 확인' "$f" || fail "인라인 등록 절차에 하네스 확인 누락: $f"
done
# G6: core 모드 하네스 판별 기준 구체화 (설계서 러너 필드가 없는 경로)
grep -q '프론트엔드 경로' .claude/skills/gx-tdd/phases/phase-implement.md   || fail "core 모드 하네스 판별 기준(프론트엔드 경로) 누락: gx-tdd phase-implement.md"
# G7: 헤드리스(ralph)는 AskUserQuestion이 없으므로 fail-closed 처리가 필요
grep -q '하네스' .claude/skills/gx-ralph-iterate/SKILL.md   || fail "gx-ralph-iterate 하네스 부재 처리 누락 (헤드리스 fail-closed)"
# G8: 구축 가이드에 JS/TS 항목 (가장 흔한 하네스 부재 스택)
grep -q 'vitest' docs/test-harness-guide.md || fail "test-harness-guide.md JS/TS(vitest) 섹션 누락"
# G9: 사용자 문서에 프론트 지원 서술
grep -q '프론트' docs/guide.md || fail "guide.md 프론트엔드 지원 서술 누락"
[ "$FAIL" -eq 0 ] && ok "등록 검증·복합 타입·프론트 힌트·복수 타입 실행·core 판별·헤드리스·구축 가이드·사용자 문서 확인"
echo
echo "[25/25] 작업 계획(plan.md) 계약"
# --work 플래그·읽기 절차·갱신 Step·커밋 규칙이 dev/tdd 양쪽과 라우팅 규칙에 대칭으로 존재하는지 대조한다.
# plan.md 자체는 소비 프로젝트의 런타임 파일이라 이 저장소에 없다 — 문구 존재만 검사하고,
# 표 파싱·의존 그래프 검증은 Phase C의 scripts/plan-lint.py가 담당한다.
for f in .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md; do
  grep -q -- '--work' "$f" || fail "--work 플래그 파싱 규칙 누락: $f"
done
[ "$FAIL" -eq 0 ] && ok "작업 계획 계약 확인"

if [ "$FAIL" -ne 0 ]; then
  echo "정합성 린트 실패 — 위 FAIL 항목을 수정하세요."
  exit 1
fi
echo "정합성 린트 통과"
