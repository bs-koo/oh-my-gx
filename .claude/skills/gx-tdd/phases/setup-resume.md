# phase-setup 보조 — 재개 감지

phase-setup Step 0이 `--resume` 지정 또는 ARGS[0] 부재일 때만 이 파일을 Read한다. 새 작업(ARGS[0] 있음, `--resume` 없음)에서는 읽히지 않는다. "이어서 진행"이 확정되면 phase-setup의 나머지 Step(1~7)을 건너뛴다는 계약은 원문 그대로다.

## Step 0: 진행 중 작업 감지

DEV_DIR을 읽기 전용으로 확정하고 [제거된 실행 경로의 중단 규약](../references/intent-routing.md#제거된-무인-반복-경로--실행-전-중단)을 먼저 적용한다. 구버전 실행에 속한 pending은 표시·응답으로 재개하지 않고 기록을 보존한 채 이관을 안내한다. 정상 TDD이면 Codex 공통 질문 helper의 status를 먼저 확인한다. pending이 있으면 원래 phase·질문을 복원하고 실제 응답을 기록·해제한 뒤 재개한다. 재개 제안·새 작업 질문으로 기존 미응답 질문을 덮어쓰지 않는다.

정상 TDD의 pending 확인은 일반 state.md 존재·pipeline 재개 판정보다 먼저 실행한다. state.md가 아직 없는 초기 setup 질문도 미응답이면 표시·대기하고, 답변 기록·해제 후 원래 setup을 계속한다. 해당 상태를 "재개할 작업이 없습니다"로 처리하지 않는다.

### `--resume` 플래그가 있는 경우
1. state.md 탐색을 위해 경로를 계산한다 (VCS 판별: `.claude/config.json`의 `vcs` 값이 있으면 이를 따르고, 없으면 `git rev-parse --is-inside-work-tree` 성공 시 git·실패하고 `svn info` 성공 시 svn으로 폴백):
   - **git**: 현재 브랜치명에서 **임시** 경로를 계산한다: `git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/state.md`.
   - **svn**: `.dev/.active`가 가리키는 `.dev/{slug}/state.md` (`.active` 부재·공백 시 `.dev/trunk/state.md` 폴백. 포인터가 없고 진행 중 `.dev/*/state.md`가 여럿이면 목록을 제시해 선택받는다).
2. 해당 경로의 state.md를 탐색한다.
3. 존재하고 `status: in_progress`이면 → `pipeline: gx-tdd` 필드를 확인한다. 필드가 없거나 값이 다르면(gx-dev 등 다른 파이프라인 산출물) 재개하지 않고 "진행 중 작업은 gx-tdd 파이프라인이 아닙니다. 제거된 비TDD 파이프라인은 자동 재개하지 않습니다. 기존 산출물을 보존하고 `/gx-work 기존 계획을 TDD 작업으로 전환해줘`로 범위와 미완료 항목을 확인하세요." 출력 후 종료. 일치하면 DEV_DIR을 해당 파일의 부모 디렉토리(`.dev/{branch-slug}/`)로 확정하고 바로 재개 (아래 "이어서 진행" 절차).
4. state.md가 없거나 `status: completed`이면 → "재개할 작업이 없습니다." 출력 후 종료.

### `--resume` 플래그가 없는 경우 (자동 감지)
ARGS[0]이 있으면 → 새 작업이므로 자동 감지를 건너뛰고 Step 1로 진행.
ARGS[0]이 없으면 → 아래 자동 감지 로직 실행.

1. state.md 탐색을 위해 경로를 계산한다 (VCS 판별: `.claude/config.json`의 `vcs` 값이 있으면 이를 따르고, 없으면 `git rev-parse --is-inside-work-tree` 성공 시 git·실패하고 `svn info` 성공 시 svn으로 폴백):
   - **git**: 현재 브랜치명에서 **임시** 경로를 계산한다: `git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/state.md`.
   - **svn**: `.dev/.active`가 가리키는 `.dev/{slug}/state.md` (`.active` 부재·공백 시 `.dev/trunk/state.md` 폴백. 포인터가 없고 진행 중 `.dev/*/state.md`가 여럿이면 목록을 제시해 선택받는다).
2. 해당 경로의 state.md를 탐색한다.
3. state.md가 존재하고 `status: in_progress`이면:
   - `pipeline: gx-tdd` 필드가 없거나 값이 다르면(gx-dev 등 다른 파이프라인 산출물) 재개를 제안하지 않는다. "진행 중 작업은 gx-tdd 파이프라인이 아닙니다. 제거된 비TDD 파이프라인은 자동 재개하지 않습니다. 기존 산출물을 보존하고 `/gx-work 기존 계획을 TDD 작업으로 전환해줘`로 범위와 미완료 항목을 확인하세요." 안내 후 종료한다 (상태 덮어쓰기 방지).
   - 사용자에게 AskUserQuestion으로 질문: "이전에 진행하던 작업이 있습니다."
     - "이어서 진행" → 재개
     - "새로 시작" → Step 1로 진행 (Step 7에서 덮어씀)
4. state.md가 없거나 `status: completed`이면 → Step 1로 진행.

### 0.05 진입 승인·실행방법 복원 (재개 정합성 체크 전)

pending 질문 확인은 위 계약대로 state 존재·pipeline 판정보다 먼저 수행한다. 답변 해제 후 [제거된 실행 경로의 중단 규약](../references/intent-routing.md#제거된-무인-반복-경로--실행-전-중단)을 읽고 legacy pipeline/flags/잠금이면 원본을 보존하고 중단한다. 통과한 state를 읽기 전용으로 확인하고, 브랜치 이관·stash 복원·착수 기록·빌드/코드 변경 전에 다음을 수행한다.

1. `run-id`·`goal`·`stop-at`, `handoff-file`·`request-file`·`plan-file`, `entry-approved-run`·`entry-approved-source`·`entry-approved-scope-sha256`를 복원한다. gx-work origin/승인 기록이 있으면 원래 handoff를 찾아 `Read("../references/plan-handoff.md")`의 `validate-handoff --handoff <절대경로> --project-root <현재 실제 루트>`를 재실행한다. exit 0과 `ready-for-tdd: true`, state와 같은 run·원문·범위·종료점이 모두 필요하다. 누락/불일치는 일반 구현 요청 승인으로 대체하지 않고 원래 진입 확인/보완에서 대기한다. 원 handoff를 잃은 gx-work 실행을 standalone으로 바꾸지 않는다. gx-work 인계 이력이 없는 기존 직접 호출에는 진입 승인을 추가하지 않는다.
2. 내부 T계획의 `implementation-plan-file`·`implementation-plan-sha256`, `plan-approved-run`·`plan-approved-source`·`plan-approved-sha256`와 `execution-method`·`execution-method-run`·`execution-method-plan-sha256`·`execution-method-source`를 복원한다. 계획 파일의 현재 SHA-256을 비교한다. 같은 run·계획·실제 선택 근거면 재질문하지 않는다. TDD 내부 계획 작성은 원래 요청 범위의 진입 승인을 무효화하지 않지만 요구범위/종료점 변경은 별도 확인한다.
3. `session`인데 복원/이번 명시 flags에 `--isolated`가 있거나, 승인된 `subagents`인데 복원 flags에서 빠졌으면 충돌을 보고하고 실제 결정으로 해소한다. 조용히 플래그를 추가/삭제하거나 방법을 기본값으로 바꾸지 않는다. 기록이 없거나 계획이 바뀌었으면 `phase-implement` Step 1.2~1.3에서 해당 계획 검토·방법을 확정한 뒤 중단 지점으로 복귀한다. 이미 작성한 RED/보고서와 라운드 카운터를 유지하며 새 계획과 충돌하는 증거를 재사용하지 않는다.
4. `current-step: 계획 문서로 종료`이면 미구현 상태와 계획 경로를 보고한다. 새 실제 실행 응답 없이 RED·complete/commit/PR로 체이닝하지 않는다.

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
     - 존재하면: 추가 AskUserQuestion — ①"기존 `.dev/{new-slug}/`를 `.dev/{new-slug}.backup-$(date +%s)/`로 백업 후 이관" / ②"중단". 백업 선택 시 `mv ".dev/{new-slug}" ".dev/{new-slug}.backup-$(date +%s)"` → `mv ".dev/{old-slug}" ".dev/{new-slug}"` 순서로 실행.
     - 경로에 공백/특수문자가 포함될 수 있으므로 `mv` 인자는 반드시 따옴표로 감싼다.
   - "새로 시작" → 기존 `.dev/{old-slug}/`는 유지하고 Step 1로 진행.
   - "중단" → 사용자에게 수동 정리를 요청하고 종료.
2. **HEAD 정합성**: state.md에 `last-known-head` 필드가 있고 현재 `git rev-parse HEAD`와 다르면, `git log {last-known-head}..HEAD --oneline`으로 외부 커밋 개수를 센다. 1개 이상이면 사용자에게 보고: "외부 커밋 {N}건이 감지되었습니다: {sha1}..{sha2}. 계속하시려면 확인해주세요." 후 AskUserQuestion으로 진행/중단 선택.

**이어서 진행 시:**
- state.md에서 VCS_TYPE, GIT_PREFIX, 베이스 브랜치(git), 프로젝트 타입, ARGS[0], flags, mode, model-profile과 0.05의 run·승인·원문 포인터·계획·실행방법을 복원하되 PROJECT_ROOT는 Step -1의 절대경로를 유지한다. VCS_TYPE이 없으면 `"git"`으로 fallback. model-profile이 없으면(구 세션) config.json `modelProfile` 값(비어있으면 `standard`)으로 결정한다.
- **구 버전 세션 방어**: state.md에 `mode` 필드가 **존재하고** 그 값이 `all`/`core`가 아니면(v1.18.0 이전 구 버전에서 생성된 세션) 재개하지 않는다. "이 작업은 구 버전(v1.18.0 미만)에서 생성되어 재개할 수 없습니다. `/gx-tdd {작업 설명}`으로 새로 시작해주세요." 안내 후 종료한다. **`mode` 필드가 없는 세션은 거부하지 않는다** — `--phase` 부트스트랩 골격(SKILL.md 환경감지가 mode 없이 생성) 등 정상 v1.18.0 산출물이므로 그대로 재개한다.
- `test -d`로 경로 검증. 실패 시 "작업 경로가 유효하지 않습니다." → 새로 시작.
- `${DEV_DIR}/` 하위의 prd.md, design.md, trust-ledger.md, codemap.md, ac.md가 있으면 Read하여 맥락 복원.
- `references/` 디렉토리가 있으면 외부 규격 참조 탐색(Step 3.1 병렬 수집의 5번 항목)을 재실행하여 `REFERENCES`를 복원한다.
- Step 3.1의 도메인 컨텍스트 탐색(4번 항목)을 재실행하여 `DOMAIN_CONTEXT`를 복원한다.
- `Read("../references/document-lifecycle.md")`의 문서 사전 대조를 같은 run-id·snapshot·journal로 복원한다. 현재 관련 문서 해시와 미해결 차이만 확인한다. 중단된 완료 투영은 검증 완료가 아니며, 승인·질문·계획을 새로 만들지 않는다.
- phases 맵에서 마지막 in_progress Phase를 찾아 재개.
- phase-setup의 나머지 단계(Step 1~Step 7)를 건너뛴다.

### 착수 기록 보정 (`--work` 세션 재개 시)

read-only·`--no-document-write`·명시 문서 수정 금지이면 W행 Edit·계획 commit/push를 하지 않는다. 아래 보정은 생략하고 착수 추적 미반영과 대상 W ID를 대화/허용된 실행 기록에만 남긴다.

재개("이어서 진행")로 진입했고 state.md에 `work-id`가 있으면, `.dev/plan.md`의 해당 행이 이미 `진행`이고 `작업 위치`가 채워져 있는지 확인한다. 아직 `대기`이거나 `작업 위치`가 `-`이면 **Step 5.5가 실행되지 못한 채 중단된 세션**이다 (stash pop 충돌 등으로 Step 5 종료 시점에 멈춘 경우). 지금 로컬 행을 기입한 뒤 [실행 종료점 계약](../references/execution-boundaries.md)을 적용한다. verify에서는 커밋·push하지 않는다. commit에서는 `docs: [plan] {ID} 착수`로 로컬 커밋만 하고, pr 또는 별도 명시적 원격 반영 요청에만 `git push -u origin {현재 브랜치}`를 수행한다.

재개 경로는 Step 5를 다시 거치지 않으므로 여기서 보정하지 않으면 착수 기록이 영영 남지 않는다 — 브랜치는 있는데 계획에는 흔적이 없어, 다른 팀원이 같은 작업에 착수해도 감지되지 않는다. 이미 기입되어 있으면 아무것도 하지 않는다. `work-id`가 없거나 계획 파일이 없으면 건너뛴다. svn이면 커밋하지 않고 사용자에게 안내한다.

