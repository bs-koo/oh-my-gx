# phase-setup 보조 — 재개 감지

phase-setup Step 0이 `--resume` 지정 또는 ARGS[0] 부재일 때만 이 파일을 Read한다. 새 작업(ARGS[0] 있음, `--resume` 없음)에서는 읽히지 않는다. "이어서 진행"이 확정되면 phase-setup의 나머지 Step(1~7)을 건너뛴다는 계약은 원문 그대로다.

## Step 0: 진행 중 작업 감지

DEV_DIR을 읽기 전용으로 확정하고 [제거된 실행 경로의 중단 규약](../references/intent-routing.md#제거된-무인-반복-경로--실행-전-중단)을 먼저 적용한다. 구버전 실행에 속한 pending은 표시·응답으로 재개하지 않고 기록을 보존한 채 이관을 안내한다. 정상 TDD이면 Codex 공통 질문 helper의 status를 먼저 확인한다. pending이 있으면 원래 phase·질문을 복원하고 실제 응답을 기록·해제한 뒤 재개한다. pending의 목표·run·phase가 이번 재개 대상과 다르면 [이전 질문 정리](../references/interaction-contract.md#이전-질문-정리)를 따른다. 재개 제안·새 작업 질문으로 기존 미응답 질문을 덮어쓰지 않는다.

정상 TDD의 pending 확인은 일반 state.md 존재·pipeline 재개 판정보다 먼저 실행한다. state.md가 아직 없는 초기 setup 질문도 미응답이면 표시·대기하고, 답변 기록·해제 후 원래 setup을 계속한다. 해당 상태를 "재개할 작업이 없습니다"로 처리하지 않는다.

### `--resume` 플래그가 있는 경우
1. state.md 탐색을 위해 경로를 계산한다 (VCS 판별: `.claude/config.json`의 `vcs` 값이 있으면 이를 따르고, 없으면 `git rev-parse --is-inside-work-tree` 성공 시 git·실패하고 `svn info` 성공 시 svn으로 폴백):
   - **git**: 현재 브랜치명에서 **임시** 경로를 계산한다: `git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/state.md`.
   - **svn**: `.dev/.active`가 가리키는 `.dev/{slug}/state.md` (`.active` 부재·공백 시 `.dev/trunk/state.md` 폴백. 포인터가 없고 진행 중 `.dev/*/state.md`가 여럿이면 목록을 제시해 선택받는다).
2. 해당 경로의 state.md를 탐색한다.
3. 존재하고 `status: in_progress`이면 → `pipeline: gx-tdd` 필드를 확인한다. 필드가 없거나 값이 다르면(gx-dev 등 다른 파이프라인 산출물) 재개하지 않고 "진행 중 작업은 gx-tdd 파이프라인이 아닙니다. 제거된 비TDD 파이프라인은 자동 재개하지 않습니다. 기존 산출물은 그대로 둡니다. 새 범위는 이 브랜치가 아닌 새 브랜치나 별도 워크트리에서 `/oh-my-gx:gx-work <목표>`로 시작하세요(SVN은 `--slug <새 slug>`)." 출력 후 종료. 일치하면 DEV_DIR을 해당 파일의 부모 디렉토리(`.dev/{branch-slug}/`)로 확정하고 바로 재개 (아래 "이어서 진행" 절차).
4. state.md가 없으면 → "재개할 작업이 없습니다." 출력 후 종료. `status: cancelled`이면 "취소한 작업입니다. 기록은 남아 있습니다." 뒤 AskUserQuestion으로 `다시 열기` / `그대로 두기`를 묻는다. 다시 열기를 실제로 고를 때만 [상태 계약](../references/pipeline-state.md)의 cancelled 수명주기대로 되돌리고 "이어서 진행"으로 간다. `status: completed`이면 이번 요청이 다른 종료점("이어서 PR까지"·"커밋만"·"PR만")을 명시했을 때만 [종료점 변경](../references/intent-routing.md#종료점-변경)으로 `--phase complete` 경로를 따르고, 그 밖에는 "재개할 작업이 없습니다." 출력 후 종료.

### `--resume` 플래그가 없는 경우 (자동 감지)
ARGS[0]이 있으면 → 새 작업이므로 자동 감지를 건너뛰고 Step 1로 진행.
ARGS[0]이 없으면 → 아래 자동 감지 로직 실행.

1. state.md 탐색을 위해 경로를 계산한다 (VCS 판별: `.claude/config.json`의 `vcs` 값이 있으면 이를 따르고, 없으면 `git rev-parse --is-inside-work-tree` 성공 시 git·실패하고 `svn info` 성공 시 svn으로 폴백):
   - **git**: 현재 브랜치명에서 **임시** 경로를 계산한다: `git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/state.md`.
   - **svn**: `.dev/.active`가 가리키는 `.dev/{slug}/state.md` (`.active` 부재·공백 시 `.dev/trunk/state.md` 폴백. 포인터가 없고 진행 중 `.dev/*/state.md`가 여럿이면 목록을 제시해 선택받는다).
2. 해당 경로의 state.md를 탐색한다.
3. state.md가 존재하고 `status: in_progress`이면:
   - `pipeline: gx-tdd` 필드가 없거나 값이 다르면(gx-dev 등 다른 파이프라인 산출물) 재개를 제안하지 않는다. "진행 중 작업은 gx-tdd 파이프라인이 아닙니다. 제거된 비TDD 파이프라인은 자동 재개하지 않습니다. 기존 산출물은 그대로 둡니다. 새 범위는 이 브랜치가 아닌 새 브랜치나 별도 워크트리에서 `/oh-my-gx:gx-work <목표>`로 시작하세요(SVN은 `--slug <새 slug>`)." 안내 후 종료한다 (상태 덮어쓰기 방지).
   - 사용자에게 AskUserQuestion으로 질문: "이전에 진행하던 작업이 있습니다."
     - "이어서 진행" → 재개
     - "새로 시작" → Step 1로 진행 (진행 중인 기존 실행은 Step 5의 이름 충돌 확인으로 보존한다)
4. state.md가 없거나 `status: completed`·`cancelled`이면 → Step 1로 진행.

### 0.05 진입 승인·실행방법 복원 (재개 정합성 체크 전)

pending 질문 확인은 위 계약대로 state 존재·pipeline 판정보다 먼저 수행한다. 답변 해제 후 [제거된 실행 경로의 중단 규약](../references/intent-routing.md#제거된-무인-반복-경로--실행-전-중단)을 읽고 legacy pipeline/flags/잠금이면 원본을 보존하고 중단한다. 통과한 state를 읽기 전용으로 확인하고, 브랜치 이관·stash 복원·착수 기록·빌드/코드 변경 전에 다음을 수행한다.

1. `run-id`·`goal`·`stop-at`, `handoff-file`·`request-file`·`plan-file`, `entry-approved-run`·`entry-approved-source`·`entry-approved-scope-sha256`를 복원한다. 포인터는 현재 PROJECT_ROOT 기준 상대경로로 연다. 이전 세션의 절대경로 값도 읽되, 그 파일이 없으면(브랜치 이름 변경·다른 PC·다른 워크트리) 값의 `.dev/` 이후 부분을 현재 루트에 붙여 찾고 찾으면 state를 상대경로로 고친다. 이번 호출에 명시 `--stop-at`이 있고 저장값과 다르면 검증 전에 [종료점 변경](../references/intent-routing.md#종료점-변경) 1~3을 먼저 적용한다. gx-work origin/승인 기록이 있으면 원래 handoff로 `Read("../references/plan-handoff.md")`의 `validate-handoff --handoff <파일> --project-root <현재 실제 루트>`를 재실행한다. exit 0과 `ready-for-tdd: true`, state와 같은 run·원문·범위·종료점이 모두 필요하다. 실패 원인이 종료점 변경(decisions.md에 실제 사용자 결정이 기록되고 state `stop-at`이 갱신됨)이면 plan-handoff의 `reissue --stop-at <state 값> --change-source "<그 근거>"`, v1 인계의 경로 이동이면 `reissue`(진입 승인 유지, `relocated: true`)로 같은 run-id 인계를 다시 받고(v2 인계는 위치가 바뀌어도 검증되므로 재발급하지 않는다. 단 Codex 진입 답변의 응답 기록(표식) 복사를 빠뜨려 이동 뒤 검증이 실패하면 같은 종료점으로 `reissue`하고, 결과에 `dropped-question-set-id`가 있으면 "진입 질문의 응답 기록이 새 인계로 옮겨지지 않았습니다 — 진입 결정은 그대로 유지됩니다"처럼 식별자 값 없이 알린다). 재발급한 인계로 `validate-handoff`를 다시 통과하면 state의 `handoff-file`·`entry-approved-source`·`entry-approved-scope-sha256`를 새 인계 값으로 갱신한다. 그 밖의 누락/불일치는 일반 구현 요청 승인으로 대체하지 않고 원래 진입 확인/보완에서 대기한다. 원 handoff를 잃은 gx-work 실행을 standalone으로 바꾸지 않는다. gx-work 인계 이력이 없는 기존 직접 호출에는 진입 승인을 추가하지 않는다.
2. `current_requested_phase`는 state를 읽기 전에 캡처한 이번 명시 phase다. [core-planning.md](../references/core-planning.md)를 읽고 미적용 실제 core→all 결정 또는 mode-transition-status pending을 **mode 해석·과거 커서 적용 전에** 복구/멱등 적용한다. applied 일반 재개는 저장된 새 전체 목록·현재 커서를 유지하며 requirements부터 다시 초기화하지 않는다. 새 명시 phase는 과거 목록·커서보다 우선한다. 전이 자체로 원 run·gx-work 진입 승인·stop-at를 바꾸지 않는다.
3. mode 필드가 존재하는데 all/core가 아니면 null·빈 값도 포함해 구 버전 세션 방어로 중단한다. **필드 부재일 때만** `restore_mode(None, saved_flags)`로 독립 --core 토큰을 해석한다. 명시 all/core는 `restore_mode(saved_mode, saved_flags)`로 유지한다. 정규화 mode와 core-plan-status/core-plan-approved-digest를 복원하며 저장 flags는 saved_flags로만 두고 현재 명시 플래그와 합쳐 충돌시키지 않는다. 읽기 전용 계획 인계는 이 쓰기 복원을 수행하지 않는다.
4. scope-status closed 또는 current-step 범위 종료 확인이면 core-replanning.md의 scope-closed로 실행 재개를 끝낸다. 새 명시 requirements/design은 현재 문서 범위만 수행할 수 있고 닫힌 구현 범위를 자동으로 다시 열지 않는다. 그 밖에는 내부 T계획의 implementation-plan-file/sha256, plan-approved-run/source/sha256와 execution-method 및 run/plan-sha256/source를 복원해 현재 단독 SHA-256과 대조한다. core는 현재 ac.md+plan.md의 결합지문·실제 승인 근거도 검증한다. 유효한 결합 승인에 연결된 plan-approved를 재사용하며 같은 계획을 다시 승인받지 않는다. 방법만 빠졌으면 implement Step 1.3에서 방법만 보완한다. 누락/변경된 core 계획은 필요한 G-W-T·코드 Read·계획·결합 승인 Step만 보완하며 setup·완료 RGR을 반복하지 않는다. T계획 구체화는 원 요청 진입 승인을 무효화하지 않지만 요구범위/종료점 변경은 별도 확인한다.
5. session인데 복원/현재 명시 flags에 --isolated가 있거나 승인 subagents인데 복원 flags에 없으면 실제 결정으로 충돌을 해소한다. 조용히 flags를 추가/삭제하거나 방법을 기본값으로 바꾸지 않는다. 실제 선택 근거가 없거나 계획이 달라졌으면 Step 1.2~1.3에서 필요한 검토/방법만 확정한 뒤 원 중단 지점으로 돌아온다. RED/보고서·라운드·기준선과 baseline-fingerprint를 유지하며 충돌하는 증거는 재사용하지 않는다.
6. `current-step: 계획 문서로 종료`이면 미구현 상태와 계획 경로를 보고하고 phase-implement Step 1.2의 계획 검토·실행방법 질문을 다시 제시한다. 현재 세션/서브에이전트 응답이 있어야 같은 계획의 Step 1.3부터 이어 가며, 응답 없이 RED·complete/commit/PR로 체이닝하지 않는다.

### 0.1 재개 정합성 체크 (이어서 진행 선택 시)

**svn인 경우** → 브랜치/HEAD 정합성 개념이 없으므로 건너뛴다 (trunk 단일 작업).

**git인 경우** — state.md를 재개하기 전에 외부 개입으로 인한 불일치를 감지한다.

1. **브랜치 정합성**: state.md의 `branch` 필드와 `git branch --show-current` 결과를 비교한다. 표기 규약은 다음과 같다:
   - `{state.md의 branch}` / `{현재 브랜치}`: 원본 브랜치명 (예: `feat/login`).
   - `{old-slug}` / `{new-slug}`: 각 브랜치명에서 `/`를 `-`로 치환한 **DEV_DIR 슬러그** (예: `feat-login`).

   불일치 시 AskUserQuestion을 띄운다:
   - "기존 DEV_DIR `.dev/{old-slug}/` (state.md의 branch=`{state.md의 branch}`)를 현재 브랜치 DEV_DIR `.dev/{new-slug}/` (`{현재 브랜치}`)로 이관" → 이관 실행.
     - 이관 전에 목적지 `.dev/{new-slug}/`가 이미 존재하는지 확인한다. **존재 시 `mv`를 사용하지 않는다** (목적지 내부로 중첩 이동되어 구조가 깨진다).
     - 존재하지 않으면: `mv ".dev/{old-slug}" ".dev/{new-slug}"`.
     - 이관 뒤 state의 `.dev/{old-slug}/`로 시작하는 포인터를 `.dev/{new-slug}/`로 고친다.
     - 존재하면: 추가 AskUserQuestion — ①"기존 `.dev/{new-slug}/`를 `.dev/{new-slug}.backup-$(date +%s)/`로 백업 후 이관" / ②"중단". 백업 선택 시 `mv ".dev/{new-slug}" ".dev/{new-slug}.backup-$(date +%s)"` → `mv ".dev/{old-slug}" ".dev/{new-slug}"` 순서로 실행.
     - 경로에 공백/특수문자가 포함될 수 있으므로 `mv` 인자는 반드시 따옴표로 감싼다.
   - "새로 시작" → 기존 `.dev/{old-slug}/`는 유지하고 Step 1로 진행.
   - "중단" → 사용자에게 수동 정리를 요청하고 종료.
2. **HEAD 정합성**: state.md에 `last-known-head` 필드가 있고 현재 `git rev-parse HEAD`와 다르면, `git log {last-known-head}..HEAD --oneline`으로 외부 커밋 개수를 센다. 1개 이상이면 사용자에게 보고: "외부 커밋 {N}건이 감지되었습니다: {sha1}..{sha2}. 계속하시려면 확인해주세요." 후 AskUserQuestion으로 진행/중단 선택.

**이어서 진행 시:**
- 미적용 core→all 전이는 0.05대로 먼저 완료한다. applied 재개에서 커서를 다시 초기화하지 않는다. state 복원 전에 캡처한 current_requested_phase는 과거 ARGS·flags·mode·execution-phases·커서로 덮지 않는다. 자동 감지의 이어서 진행은 새 명시 requirements/design 요청을 취소하는 선택이 아니다.
- state.md에서 VCS_TYPE, GIT_PREFIX, 베이스 브랜치(git), 프로젝트 타입, ARGS[0], flags, mode, model-profile과 0.05의 run·승인·원문 포인터·계획·실행방법을 복원하되 PROJECT_ROOT는 Step -1의 절대경로를 유지한다. VCS_TYPE이 없으면 `"git"`으로 fallback. model-profile이 없으면(구 세션) config.json `modelProfile` 값(비어있으면 `standard`)으로 결정한다. 이번 요청이 프로파일을 바꾸면(`--eco`/`--standard`·자연어) [상태 계약](../references/pipeline-state.md) 모델 프로파일의 재개 중 변경 규칙을 따른다.
- **구 버전 세션 방어**: state.md에 `mode` 필드가 **존재하고** 그 값이 `all`/`core`가 아니면(v1.18.0 이전 구 버전에서 생성된 세션) 재개하지 않는다. "이 작업은 구 버전(v1.18.0 미만)에서 생성되어 재개할 수 없습니다. `/gx-tdd {작업 설명}`으로 새로 시작해주세요." 안내 후 종료한다. **`mode` 필드가 없는 세션은 거부하지 않는다** — `--phase` 부트스트랩 골격(SKILL.md 환경감지가 mode 없이 생성) 등 정상 v1.18.0 산출물이므로 그대로 재개한다.
- `test -d`로 경로 검증. 실패 시 "작업 경로가 유효하지 않습니다." → 새로 시작.
- **자동 stash 복원**: `current-step: stash 복원 충돌`이거나 `auto-stashed: true`이면 0.05·0.1 뒤 `Read("setup-branch.md")`의 "재개" 절을 먼저 수행한다(충돌 해결 뒤 남은 setup 5.5~7은 그 절이 마친다). state `auto-stash`의 SHA로만 다루며 bare `git stash pop`을 쓰지 않는다.
- mode 필드 부재만 0.05의 restore_mode(None, saved_flags)로 정규화한다. flags의 부분 문자열을 core로 오인하거나 명시 all을 --core로 덮지 않는다. 이번 명시 phase와 복원 mode는 독립이다.
- `${DEV_DIR}/` 하위의 prd.md, design.md, trust-ledger.md, codemap.md, ac.md, plan.md가 있으면 Read하여 맥락 복원.
- `current-step`이 `PRD 승인 대기`·`설계 승인 대기`이고 `prd.draft.md`·`design.draft.md`가 있으면 해당 phase에서 product-owner·architect를 다시 디스패치하지 않는다. 같은 초안을 다시 표시하고 승인·남은 질문만 다시 묻는다. 정식 문서가 이미 있고 초안이 남았으면 정식 문서를 기준으로 하고 초안을 지운다.
- `references/` 디렉토리가 있으면 외부 규격 참조 탐색(Step 3.1 병렬 수집의 5번 항목)을 재실행하여 `REFERENCES`를 복원한다.
- Step 3.1의 도메인 컨텍스트 탐색(4번 항목)을 재실행하여 `DOMAIN_CONTEXT`를 복원한다.
- `Read("../references/document-lifecycle.md")`의 문서 사전 대조를 같은 run-id·snapshot·journal로 복원한다. 현재 관련 문서 해시와 미해결 차이만 확인한다. 중단된 완료 투영은 검증 완료가 아니며, 승인·질문·계획을 새로 만들지 않는다.
- core-plan-status·core-plan-approved-digest를 현재 ac.md+plan.md 결합지문과 대조한다. plan.md·승인 필드 없는 구세션과 불일치는 pending으로 두고 필요한 requirements(core) 계획·승인 Step만 보완한다. 새 명시 requirements/design이면 유효성·근거만 복원하고 문서 경로를 따르며 과거 구현 Step으로 점프하지 않는다. 미응답 core_plan_approval은 실제 응답·기록 전 해제하지 않는다.
- **state 복원 → 요청 범위 복원 → PHASES 생성 → resume 커서 적용** 순서다. 현재 명시 phase가 없을 때만 저장 requested-phase(없으면 saved_flags의 --phase 값)·execution-phases·phase/current-step을 복원해 완료 setup/phase를 건너뛴다. 목록·커서 모순은 전체 초기화하지 않고 보고한다. RGR의 승인 plan.md·AC/파일/테스트 매핑·reports·test-file-hash/test-count·porcelain 스냅샷을 함께 복원하고 [core-replanning.md](../references/core-replanning.md)의 delta RED·기존 GREEN·승인된 은퇴·기준선 세대를 유지한다.
- phase-setup의 나머지 단계(Step 1~Step 7)를 건너뛴다.

명시 요청은 아래처럼 과거 커서보다 우선한다. `saved_requested_phase`는 위 계약으로 읽은 저장 범위다. 실행 직전 기존 커서·phase 상태를 execution-log에 보존하고 scope_updates를 적용한다. 새 요청은 과거 완료 표식을 적용하지 않고 **새 PHASES의 첫 단계부터** 시작한다. requirements/design은 explore를 먼저 실행한다. 기존 문서·승인 근거·테스트·기준선은 삭제하지 않는다. explore는 읽기만 하며 계획 저장이 허용된 경우 새 계획 메타데이터에 이 범위를 기록한다. 기존 실행 state를 덮지 않는다. HANDOFF_READ_ONLY에는 이 state 갱신을 적용하지 않는다.

```python
# 명시 요청과 재개 범위 적용
if current_requested_phase is not None:
    requested_phase = current_requested_phase
    PHASES = select_phases(mode, requested_phase)
    cursor_phase, cursor_step = PHASES[0], None
else:
    requested_phase = saved_requested_phase
    PHASES = list(saved_state.get("execution-phases", select_phases(mode, requested_phase)))
    cursor_phase = saved_state["phase"]
    cursor_step = saved_state.get("current-step")
scope_updates = {
    "requested-phase": requested_phase, "execution-phases": PHASES,
    "phase": cursor_phase, "current-step": cursor_step,
}
```

### 착수 기록 보정 (`--work` 세션 재개 시)

read-only·`--no-document-write`·명시 문서 수정 금지이면 W행 Edit·계획 commit/push를 하지 않는다. 아래 보정은 생략하고 착수 추적 미반영과 대상 W ID를 대화/허용된 실행 기록에만 남긴다.

재개("이어서 진행")로 진입했고 state.md에 `work-id`가 있으면, `.dev/plan.md`의 해당 행이 이미 `진행`이고 `작업 위치`가 채워져 있는지 확인한다. 아직 `대기`이거나 `작업 위치`가 `-`이면 **Step 5.5가 실행되지 못한 채 중단된 세션**이다 (stash 복원 충돌 등으로 Step 5 직후에 멈춘 경우). 지금 로컬 행을 기입한 뒤 [실행 종료점 계약](../references/execution-boundaries.md)을 적용한다. verify에서는 커밋·push하지 않는다. commit에서는 `docs: [plan] {ID} 착수`로 로컬 커밋만 하고, pr 또는 별도 명시적 원격 반영 요청에만 `git push -u origin {현재 브랜치}`를 수행한다.

재개 경로는 Step 5를 다시 거치지 않으므로 여기서 보정하지 않으면 착수 기록이 영영 남지 않는다 — 브랜치는 있는데 계획에는 흔적이 없어, 다른 팀원이 같은 작업에 착수해도 감지되지 않는다. 이미 기입되어 있으면 아무것도 하지 않는다. `work-id`가 없거나 계획 파일이 없으면 건너뛴다. svn이면 커밋하지 않고 사용자에게 안내한다.

