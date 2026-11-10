# fix/gx-work-audit 실행 계획

사용자 요청(2026-11-09): gx-work 전수조사에서 보고한 결함 전부를 새 브랜치에서 수정한다. 결함 목록·근거·수정 방향은 [audit-report.md](audit-report.md)가 정본이다.

- 기준: `origin/main` `6ef7517`, 브랜치 `fix/gx-work-audit`, 워크트리 `D:\SQ\oh-my-gx\.claude\worktrees\gx-work-audit`
- 종료점: 검증까지. 커밋·PR은 사용자 확인 후 `oh-my-gx:gx-commit`·`oh-my-gx:gx-pull-request`로 진행한다.
- 방식: 담당별로 파일 소유를 나눠 병렬 수정하고, 결함마다 실패하는 회귀 사례를 먼저 확인한 뒤 수정한다(RED → GREEN). 이미 통과하던 테스트는 의도한 계약 변경일 때만 고치고 그 이유를 보고한다. 부모가 통합·전체 검사·독립 리뷰를 맡는다.
- 설계 유지: 최초 요청을 TDD 진입 답변으로 치지 않는 원칙(F47), verify·보호 브랜치·커밋/PR 게이트, RED 격리.

## 담당과 파일 소유

다른 담당의 파일은 수정하지 않는다. 필요한 변경은 보고서의 "다른 담당에게 필요한 변경"에 정확히 적는다.

| 담당 | 소유 파일 | 항목 |
|---|---|---|
| G1 helper | `scripts/gx-work.py`, `scripts/codex-question.py`, `tests/test_gx_work.py`, `tests/test_gx_work_migration.py`, `tests/test_gx_work_orchestration.py`, `tests/test_codex_question_gate.py`, 신규 `tests/test_gx_work_audit.py` | F01(helper), F04(reissue·v2·run-id), F06–F16, F17(route·discard), F25(필드 검증), F30(오류 메시지), F36(route reason) |
| G2 gx-tdd | `.claude/skills/gx-tdd/**`, `tests/golden-scenarios.md`, `tests/test_codex_skill_pipeline.py`, `tests/test_codex_core_*.py`, `tests/test_codex_skill_questions.py`, 신규 `tests/test_codex_tdd_audit.py` | F01(gx-tdd 문서), F02(gx-tdd 설명), F03, F04(재개 분기), F17(재개 시 pending), F18(state 포인터), F19(읽기 전용 문구), F20–F23, F25(소비), F26, F28, F32·F33·F36·F41·F42·F43(gx-tdd 부분) |
| G3 gx-work 문서·gx-context·gx-research | `.claude/skills/gx-work/SKILL.md`, `.claude/skills/gx-work/references/*.md`, `.claude/skills/gx-work/references/dev-sharing.gitignore`, 신규 `.claude/skills/gx-work/evals/`, `.claude/skills/gx-context/**`, `.claude/skills/gx-research/SKILL.md`, `tests/test_gx_context_workflow.py`, `tests/test_gx_development_context.py`, `tests/test_codex_skill_context.py`, `tests/test_codex_dev_ignore_check.py`, 신규 `tests/test_codex_work_audit.py` | F01(gx-context·gx-work 문서), F02(gx-work·gx-context 설명, eval), F04·F14·F16·F17·F18·F19(문서), F24, F25(intake), F27, F28(gx-work 문서), F29, F30(문서), F33(a·b), F35–F39, F41·F42(gx-work·gx-context 부분), F47 |
| G4 기타 스킬·에이전트·훅·문서 | `.claude/skills/{gx-commit,gx-pull-request,gx-setup,gx-cross-review,gx-visualize}/**`, `agents/*.md`와 동기화 생성물 `.claude/skills/gx-work/references/codex-roles/**`, `.claude/hooks/capture-decision.sh`, `.claude/hooks/capture_decision.py`, `scripts/hook-tests.sh`, `README.md`, `docs/*.md`(현행 문서만), `index.html`, `.claude/rules/skill-routing.md`, `tests/test_codex_skill_layout.py`, `tests/test_codex_resources.py`, `tests/test_codex_hooks.py`, `tests/test_gx_visualize_skill_contract.py`, `tests/test_gx_arch_pipeline.py`, 신규 `tests/test_codex_release_audit.py` | F01(README·문서·라우팅), F18(gx-commit 제외 규칙), F23(gx-pull-request), F31, F32(그 밖의 스킬·에이전트·문서), F33(c gx-commit), F34, F40 |
| 부모 | `scripts/lint-consistency.sh`, `.claude-plugin/*.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`, `.claude/rules/release.md`, `tests/codex-smoke.md`, 이 계획·보고서 | F05, F44, 통합·전체 검사·독립 리뷰·CHANGELOG |

과거 설계 기록(`docs/specs/`, `docs/superpowers/`, `docs/reports/`)과 `.dev/`의 다른 작업 기록은 고치지 않는다.

## 담당 간 인터페이스 (고정)

- **I1 W ID**: 값 형식 `^W[0-9]{2,}$`(ASCII 숫자만). 문장 속 토큰 `(?<![A-Za-z0-9_-])W[0-9]{2,}(?![A-Za-z0-9_-])`. 기존 `W01`은 그대로 유효하고 W99 다음은 W100이다. 하이픈 금지 이유(이슈 키 패턴)는 유지한다.
- **I2 handoff schema v2**: 새 인계는 `schema-version: 2`. `request-file`·`plan-file`·`handoff-file` 포인터와 지문 계산은 project-root 기준 POSIX 상대경로를 쓰고 절대 root는 지문에 넣지 않는다(`project-root` 필드는 표시용으로 유지). validate-handoff는 v1(기존 절대경로)도 검증한다. 선택 필드: `work-id`(I1), `execution-method`(`session`|`subagents`), `model-profile`(`standard`|`eco`).
- **I3 run 입력 위치**: gx-work 실행 입력(intake·handoff·문서 사전대조)은 `.dev/<run-id>/`에 둔다. run-id 형식 `^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$`. helper는 형식을 검증한다. gx-tdd state의 `handoff-file`·`request-file`은 프로젝트 상대경로로 기록하고, 기존 절대경로 값도 읽는다.
- **I4 reissue**: `python <plugin-root>/scripts/gx-work.py reissue --handoff <file> --project-root <root> [--stop-at verify|commit|pr] [--change-source "<실제 사용자 결정 근거>"] [--question-set-id <id>]`. stdout에 새 handoff JSON(같은 run-id, `reissued-from-sha256`). 종료점이 바뀌면 `--change-source` 필수이며 새 범위의 `entry-approval.source`가 된다. 경로만 바뀌면 진입 승인을 유지하고 `relocated: true`를 남긴다. 실패는 exit 2와 JSON 오류.
- **I5 pending 폐기**: `python <plugin-root>/scripts/codex-question.py discard --cwd <root> --dev-dir <dir> --reason "<실제 사용자 결정 근거>"`. pending을 `discarded-question-<UTC>.json`으로 보관하고 decisions.md에 기록한 뒤 exit 0. pending이 없거나 lock이 있으면 exit 2. 보관 파일은 공유 제외 대상이다(dev-sharing.gitignore).
- **I6 route 결과**: 모든 결과에 `requested-stop-at`. pending이 있으면 `pending-goal`·`pending-run-id`·`pending-phase`. 새 결과값 `detached-head`(읽기 전용). 완료 run의 pending은 `stale-pending-file`로만 보고하고 awaiting-decision을 만들지 않는다. git 오류는 `{"error": ...}` exit 2. 결과값 목록은 G3가 문서화한다.
- **I7 gx-commit 인자**: `--skip-context-sync`이면 커밋 후 context 동기화 질문을 생략한다. gx-tdd phase-complete가 커밋할 때 전달한다.
- **I8 PR 베이스**: phase-complete Step 2-2는 `Skill(skill: "oh-my-gx:gx-pull-request", args: "<state의 base> --background ... [--extra-section ...]")`. gx-pull-request는 ARGS[0] 베이스가 있으면 묻지 않는다.
- **I9 gx-work 인계의 모드 판정**: `origin: gx-work` 인계는 handoff의 `intent`·`stop-at`·`read-only`로 모드를 정하고, 목표 문장에 STATUS/RESUME/CORE 키워드 판정을 하지 않는다. 명시 플래그(`--core`·`--eco` 등)는 반영한다.
- **I10 gx-commit 다른 작업 잔재 판정** (G4 제기로 정정): 현재 state가 가리키는 run 디렉토리(I3)는 "다른 작업 잔재" 질문 없이 **스테이징(커밋 포함)**하고 한 줄로 알린다 — state의 포인터가 가리키는 인계 입력과 진입 승인 기록이 공유돼야 다른 PC·워크트리에서 재개할 수 있다(런타임 파일은 dev-sharing.gitignore가 계속 제외). 보호 브랜치 capture 파일(`.dev/{main,master,develop,trunk}/decisions.md`)만 질문 없이 **스테이징에서 제외**하고 한 줄로 알린다.
- **I11 Claude Code 진입 질문**: Claude Code는 AskUserQuestion으로 진입·종료점을 한 번에 묻고 helper 등록 없이 `.dev/<run-id>/decisions.md`에 기록한다. `--question-set-id`는 Codex 질문 helper가 반환한 값일 때만 전달한다. 플러그인 루트는 gx-work SKILL.md 디렉토리 기준 `../../..`이며 `scripts/gx-work.py` 존재로 확인한다.

## 공통 제약

- 모든 담당은 이 워크트리 안에서만 작업하고 절대경로를 쓴다. 커밋·push·브랜치 전환·`git stash`·`git reset`·`git checkout -- <file>`을 하지 않는다(stash 목록은 다른 세션과 공유된다).
- `.claude/rules/skill-maintenance.md`를 따른다. AskUserQuestion·Skill 지시를 바꾸면 같은 위치의 하네스 적응 안내도 맞춘다. Codex 경로는 `gx-work/references/codex-runtime.md` 계약을 유지한다.
- 모든 배포 `SKILL.md`는 UTF-8 LF 20KB 미만을 유지한다(gx-tdd SKILL.md는 이미 19.4KB이므로 추가 내용은 references로).
- 린트(`scripts/lint-consistency.sh`)는 부모만 고친다. 필요한 린트 변경은 보고서에 적는다. 전체 린트는 부모가 통합 때 실행한다.
- 테스트는 담당 범위의 focused 실행만 한다. `agents/*.md`나 `.claude/config.json`을 바꾸면 `python scripts/sync-codex-resources.py` 후 `--check`.
- 한국어로 쓰고 이모지를 쓰지 않는다. 코드 주석도 한국어.

## 보고 형식

1. 변경 파일 목록
2. 항목별 처리(ID, 무엇을 바꿨는지, 회귀 사례와 RED→GREEN 근거)
3. 처리하지 않은 항목과 이유
4. 다른 담당·부모에게 필요한 변경(파일·위치·정확한 내용)
5. 실행한 명령과 결과 요약

## 진행

- [x] 감사 보고서·계획 저장
- [x] G1·G2·G3·G4 병렬 수정 (2026-11-09 세션 재시작으로 중단 → G1 처음부터·G2 이어서 재수행, G3·G4는 남은 결과를 부모가 diff로 검토. 진행 기록 `progress-g1.md`·`progress-g2.md`)
- [x] 부모 통합: 린트(F05 드리프트 검사·F44), 버전 3.1.0·CHANGELOG·release.md, I10 정정 반영(gx-commit·gx-pull-request), helper 실제 스펙과 gx-work·gx-tdd 문서 대조(`--git-safe-directory`·`--slug`·`entry-answer-recorded`·`stop-at-change-required`·reissue 조건), Codex smoke W1~W7, 훅 `.active` BOM 해석 통일
- [x] 전체 검사: sync --check, unittest(`test_codex_*`, `test_gx_work*`, context·history·lens·test-plan), hook-tests, behavior mock, lint, diff-check (리뷰 반영 전 1회 통과, 반영 후 최종 재실행)
- [x] 독립 리뷰와 반영: 코드(High 1·Medium 6·Low 10)·문서(High 3·Medium 7·Low 6) 1차 → 반영 → 재확인에서 새로 나온 코드 3건·문서 10건 반영. 회귀 단언 `tests/test_codex_review_fixes.py`, helper `Review*`·`F13StateLayoutTests`
- [ ] 최종 보고(커밋·PR은 사용자 확인 후)
