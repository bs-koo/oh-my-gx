# v1.21.0 코드리뷰 후속 결함 수정 (v1.21.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v1.21.0 전체 코드리뷰(동작 시뮬레이션 + 계약 정합)에서 발견된 Critical 4건·Important 9건·Minor 일부를 수정해 정상 완주 경로의 게이트 오경고, SVN 경로 결함, 사용자 문서 오류를 제거한다.

**Architecture:** 단일 수정 브랜치(`fix/review-followup`) 1개 PR로 v1.21.1 패치를 릴리스한다. lint [22/22] 불변식을 RED로 선행 추가한 뒤 각 결함을 GREEN으로 해소한다. 지문 게이트는 대조를 **트리 성분** 기준으로 바꾸는 것이 핵심 설계다 (기록 형식 `{HEAD}:{tree12}`는 유지 — HEAD 성분은 추적용).

**Tech Stack:** 마크다운 스킬 문서 + bash 훅/린트/훅테스트. 검증: `bash scripts/lint-consistency.sh` + `bash scripts/hook-tests.sh`.

## Global Constraints

- 커밋 메시지 `{type}: 한국어` + `-` bullet 본문. **Co-Authored-By 금지.**
- **`git add -A` 금지** — 워킹 트리에 무관 untracked 파일(PDF·pptx 등) 존재. 명시 경로만 스테이징 (Task 7의 `.dev`는 `git add .dev`로 디렉토리 지정).
- `.sh` 파일은 LF 유지 (lint [6]이 CRLF 차단).
- 각 태스크 완료 조건: `bash scripts/lint-consistency.sh` + `bash scripts/hook-tests.sh` 실행 결과를 보고 (lint는 Task 9 전까지 [22/22]만 부분 RED가 정상, hook-tests는 항상 통과 필수).
- 버전 범프(v1.21.1)·CHANGELOG는 Task 9에서만.
- 수정 금지: `compute_fingerprint()` 함수 본체(지문 **계산**은 불변 — 바꾸는 것은 **대조**뿐), gx-verify Step 5-A 지문 계산 bash 블록, `docs/onboarding-guide.md`(untracked 사용자 초안).
- 이번 범위 제외(파킹 유지): phase-complete context 갱신 순서(M3), plugin.json keywords, testing-anti-patterns 한글 함수명, 하네스 가이드 wildcard 러너 확장 안내.
- PR 생성은 오케스트레이터가 `Skill("oh-my-gx:gx-pull-request")`로 수행 (서브에이전트 금지).

## 인터페이스 계약 (전 태스크 공유)

- 지문 대조 규칙(신규): **트리 성분(콜론 뒤 12자)만 비교**. 문서 4곳(훅 주석·skill-routing·gx-commit·gx-pull-request)이 `트리 성분` 문구를 포함해야 lint [22] 통과.
- 런타임 파일 제외 pathspec: `'.dev/*/ralph.lock' '.dev/*/iter-*.log'` (gx-commit·gx-ralph-iterate 공통).
- 리뷰 diff 제외 pathspec: `-- . ':(exclude).dev'` (양 SKILL.md Diff 수집 규칙 — lint [22]가 `:(exclude).dev` 문자열 검사).
- svn 신규 파일 등록 명령: `svn add --force . 2>/dev/null` / `.active` 제외: `svn propset svn:ignore '.active' .dev`.
- lint 신규 체크: `[22/22] 리뷰 후속(v1.21.1) 계약 정합`, 분모 `/21]` → `/22]`.

---

### Task 1: 브랜치 + 계획 커밋 + lint [22] 추가 (RED)

**Files:**
- Modify: `scripts/lint-consistency.sh` ([21/22] 블록 끝과 최종 요약 사이)
- Commit: `docs/superpowers/plans/2026-08-05-review-followup-fixes.md` (이 계획 파일)

**Interfaces:**
- Produces: lint [22/22] — Task 2~8이 통과시킨다.

- [ ] **Step 1: 브랜치 생성 + 계획 커밋**

```bash
git checkout main && git pull && git checkout -b fix/review-followup
git add docs/superpowers/plans/2026-08-05-review-followup-fixes.md
git commit -m "$(cat <<'EOF'
docs: v1.21.0 코드리뷰 후속 수정 계획 추가

- Critical 4건(지문 스테일·guide 예시·svn add·.active 공유)과 Important 9건 수정 설계
EOF
)"
```

- [ ] **Step 2: 기준선 확인**

Run: `bash scripts/lint-consistency.sh && bash scripts/hook-tests.sh`
Expected: 둘 다 통과 (lint 21/21, 훅 회귀 통과)

- [ ] **Step 3: [22/22] 체크 추가**

`[ "$FAIL" -eq 0 ] && ok ".dev 공유 문구·ignore 로직 제거 확인"` 라인([21] 블록 끝) 다음, 최종 `echo` 요약 앞에 삽입:

```bash
echo "[22/22] 리뷰 후속(v1.21.1) 계약 정합"
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
```

- [ ] **Step 4: 분모 갱신 + 주석**

```bash
sed -i 's|/21\]|/22]|g' scripts/lint-consistency.sh
```

상단 주석 목록에 한 줄 추가: ` # 22. 리뷰 후속 v1.21.1 계약 (사용자 문서·경계 밖 소비 지점)`

- [ ] **Step 5: RED 확인 + 커밋**

Run: `bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: [22/22]에서 FAIL 다수, 기존 [1/22]~[21/22] 전부 ok, exit=1

```bash
git add scripts/lint-consistency.sh
git commit -m "$(cat <<'EOF'
test: 리뷰 후속 계약 lint 불변식 추가 (RED)

- [22/22] 지문 트리 대조·svn add·.active 제외·문서 교정·diff 제외 검사
EOF
)"
```

### Task 2: C1 — 지문 대조를 트리 성분 기준으로 교정 (훅 + 테스트 + 문서 4곳)

**Files:**
- Modify: `.claude/hooks/pre-tool-guard.sh` (`verify_gate_open` 내 대조 1줄 + 주석)
- Modify: `scripts/hook-tests.sh` ([4/5] 지문 절에 회귀 시나리오 추가)
- Modify: `.claude/rules/skill-routing.md`, `.claude/skills/gx-commit/SKILL.md:49-50`, `.claude/skills/gx-pull-request/SKILL.md:91`, `.claude/skills/gx-verify/SKILL.md:158`

**Interfaces:**
- Produces: "대조는 트리 성분만" 규칙 — 인터페이스 계약 참조. `compute_fingerprint()`와 지문 **기록** 형식은 절대 변경하지 않는다.

- [ ] **Step 1: 훅 대조 로직 교체**

`verify_gate_open()` 안의 기존:

```bash
    [ "$RECORDED" = "$(compute_fingerprint "$GATE_REPO")" ] && return 1
```

교체:

```bash
    # 대조는 트리 성분(콜론 뒤)만 — HEAD 성분은 기록·추적용이다. verify 통과 후
    # phase-complete가 커밋하면 HEAD는 전진하지만 트리가 같으면 검증된 코드가 그대로
    # 커밋된 것이므로 일치로 판정한다 (커밋 → PR 정상 경로의 상시 오경고 방지).
    CURRENT_FP=$(compute_fingerprint "$GATE_REPO")
    [ "${RECORDED##*:}" = "${CURRENT_FP##*:}" ] && return 1
```

(콜론 없는 비정상 기록값은 `##*:`가 전체 문자열을 남겨 불일치 → 보수적으로 게이트 유지.)

- [ ] **Step 2: hook-tests 회귀 시나리오 추가**

`scripts/hook-tests.sh`의 `[4/5]` 지문 절을 Read하여 마지막 시나리오("신규 파일 스테이징 후에도 지문 유지") 다음에 추가한다. 샌드박스 변수·assert 헬퍼 이름은 해당 절의 것을 그대로 사용한다 (아래는 절의 관례 기준 코드 — 변수명이 다르면 절에 맞춰 치환):

```bash
# C1 회귀: verify 통과 후 커밋 → HEAD 전진·트리 동일 → 게이트는 열리지 않아야 한다
git -C "$SB" add -A >/dev/null 2>&1
git -C "$SB" -c user.email=t@t -c user.name=t commit -qm "advance head" >/dev/null 2>&1
assert_repo "커밋 후 HEAD 전진·트리 동일 → 무개입" commit1 PASS
```

Run: `bash scripts/hook-tests.sh; echo "exit=$?"`
Expected: 신규 시나리오 포함 전부 통과, exit=0 (Step 1 수정 전에 먼저 추가해 FAIL을 확인하면 더 좋다 — RED 증거)

- [ ] **Step 3: skill-routing 판별 문구 교정**

기존: `**(a) \`verify-status\`가 \`passed\`가 아니거나 (b) \`verify-fingerprint\`가 기록되어 있는데 현재 코드 지문과 다르면**(=verify 통과 후 코드가 바뀜)`
교체: `**(a) \`verify-status\`가 \`passed\`가 아니거나 (b) \`verify-fingerprint\`가 기록되어 있는데 현재 코드 지문과 트리 성분이 다르면**(=verify 통과 후 코드가 바뀜 — HEAD 성분은 참고용이며, 검증된 코드가 그대로 커밋되어 HEAD만 전진한 경우는 일치로 간주한다)`

- [ ] **Step 4: gx-commit·gx-pull-request 게이트 문구 교정**

gx-commit SKILL.md 49행의 같은 절(`(b) ... 현재 코드 지문과 다르면**(=verify 통과 후 코드가 바뀜)`)을 Step 3과 동일한 문구로 교체하고, 50행 지문 계산 규약 끝에 추가: ` **대조는 트리 성분(콜론 뒤 12자)만 수행한다** — HEAD 성분은 기록·추적용이며, 커밋으로 HEAD가 전진해도 트리가 같으면 일치다.`

gx-pull-request SKILL.md 91행의 같은 절도 Step 3과 동일하게 교체한다.

- [ ] **Step 5: gx-verify 문구 교정**

158행 기존: `훅·gx-commit·gx-pull-request·라우팅이 같은 규약으로 대조한다.`
교체: `훅·gx-commit·gx-pull-request·라우팅이 같은 규약으로 **트리 성분을** 대조한다 (HEAD 성분은 기록·추적용).`

- [ ] **Step 6: 검증 + 커밋**

Run: `bash scripts/hook-tests.sh && bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: hook-tests 전부 통과, lint [22]의 지문 관련 FAIL 4건 해소

```bash
git add .claude/hooks/pre-tool-guard.sh scripts/hook-tests.sh .claude/rules/skill-routing.md .claude/skills/gx-commit/SKILL.md .claude/skills/gx-pull-request/SKILL.md .claude/skills/gx-verify/SKILL.md
git commit -m "$(cat <<'EOF'
fix: verify 지문 대조를 트리 성분 기준으로 교정

- 커밋으로 HEAD가 전진해도 트리 동일이면 일치 판정 (커밋→PR 상시 오경고 제거)
- 훅·라우팅·gx-commit·gx-pull-request·gx-verify 문구 동기, 훅 회귀 테스트 추가
EOF
)"
```

### Task 3: C2·I6·I7 — 사용자 문서 교정 (guide.md + _config.yml)

**Files:**
- Modify: `docs/guide.md` (38행 지원 환경 표, 739~744행 등록 예시)
- Modify: `_config.yml` (2행 description)

- [ ] **Step 1: guide.md 등록 예시 교체**

기존:

```json
"projectTypes": {
  "python": {
    "detect": ["requirements.txt", "pyproject.toml"],
    "build": "python -m pytest --co -q"
  }
}
```

교체:

```json
"projectTypes": {
  "python": {
    "detect": ["pyproject.toml", "setup.py", "requirements.txt"],
    "test": "pytest",
    "warningPattern": "warning",
    "artifacts": [".venv/", "__pycache__/"]
  }
}
```

교체 블록 바로 아래에 문장 추가: `python은 별도 빌드가 없어 \`build\` 필드를 생략한다. 값 제안은 \`/gx-setup\`의 "프로젝트 타입 등록"(힌트 카탈로그)이 자동으로 해준다.`

- [ ] **Step 2: 지원 환경 표 언어 중립화**

기존: `| 언어/프레임워크 | Java (Spring Boot, Gradle), Node.js |`
교체: `| 언어/프레임워크 | 언어 중립 — config \`projectTypes\` 등록 기반 (Java·Node 기본 내장, C/C++·Python·Go·Rust·.NET·Maven 등은 \`/gx-setup\` 자동 등록) |`

- [ ] **Step 3: _config.yml description 교체**

기존: `description: Java Spring Boot / 풀스택 개발을 위한 AI 기반 Claude Code 플러그인`
교체: `description: 모든 언어/프레임워크를 지원하는 GX 사업본부 AI 개발 자동화 Claude Code 플러그인`

- [ ] **Step 4: 검증 + 커밋**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: guide/_config 관련 FAIL 4건 해소

```bash
git add docs/guide.md _config.yml
git commit -m "$(cat <<'EOF'
fix: 사용자 문서의 잘못된 등록 예시와 낡은 지원 범위 교정

- guide.md python 예시에 test 필드 복원·collect-only 플래그 제거 (verify 차단 결함)
- 지원 환경 표·GitHub Pages description 언어 중립화
EOF
)"
```

### Task 4: C3·C4 — SVN 신규 파일 등록 + .active 공유 제외

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (Step 5 svn 절, 375~376행)
- Modify: `.claude/skills/gx-dev/phases/phase-implement.md` (변경사항 수집의 svn 절 — 같은 `svn diff > ${DIFF_FILE}` 앵커를 Grep으로 찾아 동일 적용)
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md`·`.claude/skills/gx-dev/phases/phase-review.md` (Step 1 svn 절)
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md:104`·gx-dev phase-complete의 동일 svn 안내
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md`·`.claude/skills/gx-dev/phases/phase-setup.md` (Step 6 svn 절)

- [ ] **Step 1: phase-implement svn 수집 절 교체 (gx-tdd)**

기존:

```markdown
1. 스테이징 불필요 (SVN은 staging 개념 없음).
2. `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다.
```

교체:

```markdown
1. **신규 파일 등록**: `svn add --force . 2>/dev/null`로 unversioned 신규 파일을 일괄 등록한다 (`--force`는 versioned 디렉토리 하위 추가를 허용하며 svn:ignore 패턴은 존중된다. RGR이 만든 신규 테스트·구현 파일은 add 없이는 `svn diff`에 실리지 않아 리뷰가 오판한다).
2. `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다.
```

- [ ] **Step 2: gx-dev phase-implement에 동일 적용**

`svn diff > ${DIFF_FILE}` 앵커 앞에 같은 "신규 파일 등록" 항목을 삽입한다 (절의 번호 체계는 해당 파일 기준으로 유지).

- [ ] **Step 3: phase-review Step 1 svn 절 (양쪽)**

기존(gx-tdd 기준): "`svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다. staging 없이 한 단계로 끝난다."
교체: "`svn add --force . 2>/dev/null`로 신규 파일을 등록한 뒤 `svn diff > ${DIFF_FILE}`로 로컬 변경사항 전체를 수집한다." (gx-dev도 동일 앵커 교체)

- [ ] **Step 4: phase-complete svn 안내 (양쪽)**

gx-tdd phase-complete:104 기존 안내 문구를 교체:
기존: `"SVN 프로젝트입니다. verify 게이트 통과를 확인한 뒤 \`svn commit\`을 직접 실행해주세요."`
교체: `"SVN 프로젝트입니다. verify 게이트 통과를 확인하고, \`svn add --force .\`로 신규 파일(.dev 산출물 포함)이 등록되었는지 확인한 뒤 \`svn commit\`을 직접 실행해주세요."`
(gx-dev phase-complete에 같은 안내가 있으면 동일 교체 — Grep으로 확인.)

- [ ] **Step 5: phase-setup Step 6 svn 절에 .active 예외 (양쪽)**

gx-tdd 쪽 svn 절의 "제거를 제안한다: ... 재적용한다." 문장 다음, "처리 후 Step 7로 진행한다." 앞에 삽입:

```markdown
단 **`.dev/.active`는 공유 예외**다 — 이 머신의 활성 작업을 가리키는 런타임 포인터라 공유되면 다른 사용자의 `--resume`·verify baseline이 타인 세션 기준으로 오염된다. `.dev`가 아직 unversioned면 `svn add --depth=empty .dev`로 디렉토리만 등록한 뒤 `svn propset svn:ignore '.active' .dev`를 적용해 `.active`를 공유에서 제외한다. 이미 `.active`가 versioned로 커밋되어 있으면 `svn rm --keep-local .dev/.active`로 버전 관리에서만 제거하도록 안내한다.
```

gx-dev 쪽 svn 절("건너뛴다. 단, 이전 버전이...") 끝에도 같은 문단을 추가한다.

- [ ] **Step 6: 검증 + 커밋**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: svn add·.active FAIL 3건 해소

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md .claude/skills/gx-dev/phases/phase-implement.md .claude/skills/gx-tdd/phases/phase-review.md .claude/skills/gx-dev/phases/phase-review.md .claude/skills/gx-tdd/phases/phase-complete.md .claude/skills/gx-dev/phases/phase-complete.md .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md
git commit -m "$(cat <<'EOF'
fix: SVN 신규 파일 svn add 지시 추가 및 .active 공유 제외

- RGR 신규 파일이 svn diff에 실리도록 add --force 선행 (리뷰 오판·변경없음 오중단 방지)
- .dev/.active를 svn:ignore로 공유 제외 (다중 사용자 세션 오염 방지)
EOF
)"
```

### Task 5: I1·I4 — gx-commit 아티팩트 통합 + 런타임 파일 스테이징 제외

**Files:**
- Modify: `.claude/skills/gx-commit/SKILL.md` (커밋 실행 절의 2항·5항, 1항 목록 표시)
- Modify: `.claude/skills/gx-ralph-iterate/SKILL.md` (Step 4의 2항 스테이징)

- [ ] **Step 1: 아티팩트 패턴 합집합 (gx-commit 2항)**

기존: `2. 빌드 아티팩트 패턴(\`.claude/config.json\` → \`buildArtifactPatterns\` 참조)이 tracked 파일 목록에 있으면:`
교체: `2. 빌드 아티팩트 패턴(\`.claude/config.json\`의 모든 \`projectTypes.*.artifacts\`와 레거시 \`buildArtifactPatterns\`의 **합집합** — 타입별 artifacts가 SSOT)이 tracked 파일 목록에 있으면:`

- [ ] **Step 2: 스테이징 런타임 파일 제외 + 타 슬러그 확인 (gx-commit 5항·1항)**

5항 기존:

```markdown
5. 스테이징:
   - 제외 파일 없음: `git add -A`
   - 제외 파일 있음: `git add <나머지 파일 각각 지정>`
```

교체:

```markdown
5. 스테이징:
   - 제외 파일 없음: `git add -A` 후 런타임 파일을 unstage한다: `git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' 2>/dev/null` (루프 락·반복 로그는 커밋 대상이 아니다 — 커밋되면 다른 사용자의 라우팅·게이트 판별이 오작동한다)
   - 제외 파일 있음: `git add <나머지 파일 각각 지정>` (위 런타임 파일은 지정하지 않는다)
```

1항("`git status --short`로 변경 파일 목록을 확인하고, 목록을 사용자에게 표시한다.") 끝에 추가: ` 목록에 **현재 브랜치 슬러그가 아닌 \`.dev/{다른-slug}/\`** 경로가 있으면 다른 작업의 잔재일 수 있으므로 포함 여부를 사용자에게 확인한다.`

- [ ] **Step 3: gx-ralph-iterate 스테이징 동일 제외**

Step 4의 2항 기존: `2. 스테이징: \`git add -A\` 후 \`git status --porcelain\`으로 스테이징 목록을 검사한다.`
교체: `2. 스테이징: \`git add -A\` 후 런타임 파일을 unstage하고(\`git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' 2>/dev/null\` — 락·반복 로그는 커밋 금지) \`git status --porcelain\`으로 스테이징 목록을 검사한다.`

- [ ] **Step 4: 검증 + 커밋**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: gx-commit artifacts FAIL 해소

```bash
git add .claude/skills/gx-commit/SKILL.md .claude/skills/gx-ralph-iterate/SKILL.md
git commit -m "$(cat <<'EOF'
fix: gx-commit 아티팩트 가드 통합 및 런타임 파일 스테이징 제외

- projectTypes.artifacts 합집합을 SSOT로 (buildArtifactPatterns는 레거시 폴백)
- ralph.lock·iter 로그 unstage, 타 슬러그 .dev 잔재는 사용자 확인
EOF
)"
```

### Task 6: I2·M4 — 리뷰 diff에서 .dev 제외 + porcelain 대조 명시

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` (Diff 수집 규칙), `.claude/skills/gx-dev/SKILL.md:547~` (쌍둥이)
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` (Step 1의 `--phase review` 브랜치 비교 명령)·gx-dev 쌍둥이
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md:258` (porcelain 대조)

- [ ] **Step 1: Diff 수집 규칙에 pathspec (양 SKILL.md)**

수집 절차 2항의 명령 기존: `git diff --cached > ${DEV_DIR}/diff.txt`
교체: `git diff --cached -- . ':(exclude).dev' > ${DEV_DIR}/diff.txt`

4항의 --stat 명령도 동일하게 `--stat -- . ':(exclude).dev'`로 교체하고, 규칙 끝("이 규칙은 모든 diff 패턴에 적용한다..." 문장)을 다음으로 교체:

```markdown
이 규칙은 모든 diff 패턴에 적용한다: `git diff --cached` (스테이징), `git diff <base>...HEAD` (브랜치 비교) 등 — **모든 git diff 명령에 `-- . ':(exclude).dev'` pathspec을 붙여 `.dev` 산출물을 리뷰 diff에서 제외한다** (산출물은 공유 대상이지만 코드 리뷰 대상이 아니며, PRD·AC 전문이 diff로 유입되면 quality-reviewer의 격리 계약이 우회 붕괴하고 500줄 초과 강등이 빈발한다). svn은 pathspec 제외가 없으므로 diff 수집 후 리뷰 에이전트 프롬프트에 "`.dev` 경로의 변경은 리뷰 대상에서 제외하라"를 명시한다.
```

(gx-dev SKILL.md 547행 이하 쌍둥이 규칙에 동일 적용.)

- [ ] **Step 2: phase-review 브랜치 비교 명령 (양쪽)**

gx-tdd phase-review Step 1의 기존: `git diff $(git merge-base HEAD <base-branch>)...HEAD`를 `DIFF_FILE`에 리다이렉트한다.
교체: `git diff $(git merge-base HEAD <base-branch>)...HEAD -- . ':(exclude).dev'`를 `DIFF_FILE`에 리다이렉트한다.
(gx-dev 쌍둥이 동일.)

- [ ] **Step 3: porcelain 대조 .dev 제외 명시**

phase-implement 258행(verify_green 2항)의 "대조하여 **다른 테스트 파일**의 변경 여부도 확인한다." 뒤에 추가: ` (`.dev/` 경로 라인은 대조에서 제외한다 — 산출물 공유 전환으로 델타에 나타날 수 있으나 테스트 무결성과 무관하다)`

- [ ] **Step 4: 검증 + 커밋**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: `:(exclude).dev` FAIL 2건 해소

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md .claude/skills/gx-tdd/phases/phase-review.md .claude/skills/gx-dev/phases/phase-review.md .claude/skills/gx-tdd/phases/phase-implement.md
git commit -m "$(cat <<'EOF'
fix: 리뷰 diff에서 .dev 산출물 제외

- 모든 diff 명령에 exclude pathspec (quality-reviewer 격리 유지, diff 폭증 방지)
- porcelain 무결성 대조의 .dev 제외 명시
EOF
)"
```

### Task 7: I3 — 저장소 자신의 .gitignore 정리 + 기존 산출물 공유 개시

**Files:**
- Modify: `.gitignore` (16행 `.dev/` 제거)
- Commit: `.dev/` 기존 산출물 (feat-gx-cross-review·feat-gx-humanizer-v4·feat-gx-tdd — 전부 md/txt, 런타임 파일 없음 확인됨)

- [ ] **Step 1: .gitignore에서 .dev/ 라인 제거**

`.gitignore`의 `.dev/` 한 줄을 삭제한다 (다른 라인 무변경).

- [ ] **Step 2: 기존 산출물 확인 후 스테이징**

```bash
find .dev -name 'ralph.lock' -o -name 'iter-*.log'
```
Expected: 출력 없음 (런타임 파일 없음 — 있으면 해당 파일만 제외하고 진행)

```bash
git add .gitignore .dev
```

- [ ] **Step 3: 검증 + 커밋**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: `.gitignore .dev 잔존` FAIL 해소

```bash
git commit -m "$(cat <<'EOF'
fix: 저장소 자신의 .gitignore에서 .dev 제거 — 자기 계약 준수

- v1.21.0 공유 계약에 맞춰 기존 파이프라인 산출물 공유 개시
EOF
)"
```

### Task 8: I5·I8·I9·M1·M2·드리프트 열거 — 소수정 묶음

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` (53행 포인터, 재개 절, 2.3 pop 충돌)
- Modify: `.claude/skills/gx-setup/SKILL.md` (0.5 Step 1 다중 감지, JDK 문구)
- Modify: `.claude/skills/gx-tdd/SKILL.md` (드리프트 목록 bullet)

- [ ] **Step 1: I5 낡은 포인터 정정**

phase-setup:53 기존: `외부 규격 참조 탐색(Step 3.5)을 재실행하여 \`REFERENCES\`를 복원한다.`
교체: `외부 규격 참조 탐색(Step 3.1 병렬 수집의 5번 항목)을 재실행하여 \`REFERENCES\`를 복원한다.`

- [ ] **Step 2: I8 재개 시 DOMAIN_CONTEXT 복원 (gx-dev와 대칭)**

위에서 교체한 REFERENCES 복원 줄 바로 다음에 추가:

```markdown
- Step 3.1의 도메인 컨텍스트 탐색(4번 항목)을 재실행하여 `DOMAIN_CONTEXT`를 복원한다.
```

- [ ] **Step 3: I9 auto-stash pop 충돌 복구 경로**

2.3의 기존: `- "stash를 유지하고 수동 해결" → conflict 상태를 유지한 채 파이프라인 일시 중단. 사용자가 해결 후 재개 지시.`
교체: `- "stash를 유지하고 수동 해결" → **중단 전에 \`${DEV_DIR}/state.md\` 골격을 먼저 Write한다** (\`pipeline: gx-tdd\`, \`status: in_progress\`, \`auto-stashed: true\`, execution-log에 \`auto-stash: <ref>\` — Step 7 이전 시점이라 골격 없이는 \`--resume\`이 재개할 작업을 찾지 못한다). 이후 conflict 상태를 유지한 채 파이프라인을 일시 중단하고, 사용자에게 stash ref와 수동 복원 명령(\`git stash pop\`)을 안내한다. 사용자가 해결 후 재개 지시.`

- [ ] **Step 4: M1 다중 감지 확인 + M2 JDK 문구 (gx-setup)**

0.5단계 Step 1 끝에 추가: ` **여러 타입의 detect 파일이 동시에 존재하면**(예: C 프로젝트에 도구용 package.json) 첫 매칭으로 단락하지 않고 AskUserQuestion으로 주 타입을 확인한다.`

JDK 절 기존: `이번 실행의 detect 파일 매칭으로 감지·등록된 타입` → 교체: `이번 실행의 detect 파일 매칭으로 감지된 타입(0.5단계에서 신규 등록됐든 기존 유지든)`

- [ ] **Step 5: 드리프트 목록 열거 보강**

gx-tdd SKILL.md의 "프로젝트 타입 폴백 표" bullet 끝에 추가: ` agents/architect.md·coder.md의 타입 감지 표와 gx-commit의 아티팩트 패턴 합집합 규칙도 이 SSOT의 파생 소비자다.`

- [ ] **Step 6: 검증 + 커밋**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A20 '\[22/22\]'`
Expected: Step 3.5 FAIL 해소 — [22/22] 전체 ok 도달

```bash
git add .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-setup/SKILL.md .claude/skills/gx-tdd/SKILL.md
git commit -m "$(cat <<'EOF'
fix: 재개 경로·낡은 포인터·다중 감지 소수정 묶음

- gx-tdd 재개 시 DOMAIN_CONTEXT 복원 (gx-dev와 대칭), Step 3.5 포인터 정정
- auto-stash pop 충돌 시 state.md 골격 선기록 (--resume 도달 가능하게)
- gx-setup 다중 detect 확인·JDK 문구 명확화, 드리프트 목록 열거 보강
EOF
)"
```

### Task 9: v1.21.1 릴리스

**Files:**
- Modify: `CHANGELOG.md` (최상단), `.claude-plugin/plugin.json`·`.claude-plugin/marketplace.json` (1.21.0 → 1.21.1)

- [ ] **Step 1: CHANGELOG 섹션 추가 (최상단)**

```markdown
## v1.21.1 (2026-08-05)

v1.21.0 전체 코드리뷰(동작 시뮬레이션·계약 정합) 후속 결함 수정.

- verify 지문 대조를 트리 성분 기준으로 교정 — 정상 완주(커밋 → PR) 경로의 상시 오경고 제거 (훅·라우팅·gx-commit·gx-pull-request 동기, 훅 회귀 테스트 추가)
- guide.md 등록 예시 교정(test 필드 누락·collect-only 플래그 — 복사 시 verify 차단 결함) 및 지원 환경 표·GitHub Pages 설명 언어 중립화
- SVN: 신규 파일 `svn add --force` 지시 추가 (diff 누락·리뷰 오판 방지), `.dev/.active` 공유 제외 (다중 사용자 세션 오염 방지)
- gx-commit: 아티팩트 가드를 projectTypes.artifacts 합집합으로 통합, 런타임 파일(ralph.lock·iter 로그) 스테이징 제외, 타 슬러그 .dev 잔재 확인
- 리뷰 diff에서 .dev 제외 pathspec (quality-reviewer 격리 유지), porcelain 무결성 대조의 .dev 제외 명시
- 저장소 자체 .gitignore의 .dev/ 제거 — 자기 계약 준수, 기존 산출물 공유 개시
- gx-tdd 재개 시 DOMAIN_CONTEXT 복원(gx-dev와 대칭), auto-stash pop 충돌 시 state.md 골격 선기록, 낡은 Step 3.5 포인터 정정
- lint [22/22] 리뷰 후속 계약 불변식 추가 (사용자 문서·경계 밖 소비 지점)
```

- [ ] **Step 2: 버전 범프**

`.claude-plugin/plugin.json`·`.claude-plugin/marketplace.json`의 `1.21.0` → `1.21.1`.

- [ ] **Step 3: 최종 검증**

Run: `bash scripts/lint-consistency.sh; echo "lint=$?"; bash scripts/hook-tests.sh; echo "hook=$?"`
Expected: lint 22/22 전체 ok·버전 3중 일치 1.21.1·exit 0, hook-tests 통과·exit 0

- [ ] **Step 4: 커밋**

```bash
git add CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "$(cat <<'EOF'
chore: v1.21.1 릴리스 — 코드리뷰 후속 결함 수정

- CHANGELOG v1.21.1 섹션, plugin.json·marketplace.json 버전 동기
EOF
)"
```

이후 오케스트레이터가 브랜치 전체 최종 리뷰를 수행하고 `Skill("oh-my-gx:gx-pull-request")`로 PR을 생성한다.
