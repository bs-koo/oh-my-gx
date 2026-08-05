# Cross-Review 결과

- advisor: codex (fallback 모드)
- 브랜치: feat/gx-cross-review (base: main)
- DEV_DIR: .dev/feat-gx-cross-review
- 실행 시각: 2026-05-04T10:15Z
- 모드: 산출물 부재 fallback (PRD/설계서 없음 → AC 매트릭스/설계 범위 이탈 섹션 생략)

## 신규 위험

### Warning

**1. [GAP] `.claude/skills/gx-cross-review/SKILL.md:296` — `git diff <merge-base>`가 untracked 파일을 누락**

- 근거: Step 2-2의 diff 수집 명령 `git diff "$(git merge-base HEAD "${BASE_BRANCH}")"`는 working tree와 merge-base의 차이를 한 번에 보여주지만, **untracked 파일은 git index에 없으므로 diff 출력에 나타나지 않는다**. `/gx-dev` 워크플로우에서 사용자가 새 파일을 추가하고 `git add` 전에 cross-review를 호출하면, 신규 구현 전체가 검증 대상에서 누락된다. advisor는 "파일이 없는 것"으로 보고 PRD AC가 충족되었다고 잘못 판단할 수 있다.
- 권고: untracked 목록을 별도로 수집하여 diff 뒤에 합산.
  ```bash
  git diff "$(git merge-base HEAD "${BASE_BRANCH}")" > "${DIFF_FILE}"
  git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do
    echo "--- /dev/null"
    echo "+++ b/$f"
    git diff --no-index /dev/null -- "$f" 2>/dev/null | tail -n +3
  done >> "${DIFF_FILE}"
  ```
  또는 `git add -N` (intent-to-add)으로 untracked를 인덱스에 등록한 뒤 diff 수행. 사용자 워킹 디렉토리 변경을 피하려면 전자가 안전.

**2. [GAP] `.claude/skills/gx-cross-review/SKILL.md:734` — fallback `--scope` 기본값 불일치 (functional bug)**

- 근거: Step 0-0 인자 표는 `${SCOPE}`를 `diff|stat`으로 정의하지만 (기본값 `diff`), companion `review` 서브명령은 `--scope` 값으로 `auto|working-tree|branch`만 허용한다 (companion `--help`로 확인). fallback의 `node companion review --scope ${SCOPE:-auto}` 호출은 `${SCOPE}`가 미설정일 때만 `auto`로 폴백하고, ARGS 파싱 후 기본값이 `diff`로 들어가면 `--scope diff`가 전달되어 companion이 거부한다. **즉 fallback의 default 케이스(인자 없이 호출)에서 항상 실패**한다.
- 권고: fallback 호출 시 `${SCOPE}`를 companion 어휘로 매핑.
  ```
  ${SCOPE} == "stat"  → companion --scope auto (자체 stat 수집)
  ${SCOPE} == "diff"  → companion --scope auto
  미지정              → companion --scope auto
  ```
  또는 fallback에서 `--scope` 자체를 생략 (companion 기본값이 auto). 가장 간단한 수정: `--scope auto` 고정.

## 총평

- **강점**: SKILL.md 자체 구조는 명확하고 단계 분리가 잘 되어 있음. dev 산출물 우선순위 슬라이싱과 BATCH_MODE 상태 머신이 깔끔.
- **합산**: Critical 0, Warning 2, Info 0
- **권고**: 두 건 모두 functional 결함이므로 머지 전 수정 권장. 특히 #2는 fallback default 호출이 항상 실패하는 회귀 위험.

## 처리 결과

- **1번 항목 (Warning GAP SKILL.md:296 untracked 누락)**: 수정됨. Step 2-2의 diff 수집에 `git ls-files --others --exclude-standard` + `git diff --no-index`로 untracked 파일 합산 추가.
- **2번 항목 (Warning GAP SKILL.md:734 fallback --scope 어휘 불일치)**: 수정됨. `--scope ${SCOPE:-auto}` → `--scope auto` 고정. `${SCOPE}`(diff/stat)는 Step 2-2 자체 diff 수집에만 의미 있음을 명시.

## 비고

- codex는 PowerShell 권한 정책으로 `git diff` 직접 실행이 차단된 상태에서 SKILL.md 본문 정독만으로 두 결함을 도출함. 실제 코드 동작 검증은 못 했으나 정황 증거 강함.
- fallback 모드 특성상 산출물 부재 → AC 매트릭스/설계 범위 이탈/references 위반 섹션은 생성하지 않음.
- 원시 응답: `.dev/feat-gx-cross-review/cross-review.raw.md`
