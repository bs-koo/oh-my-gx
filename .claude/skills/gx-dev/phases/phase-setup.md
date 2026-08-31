# phase-setup: 작업환경 준비

## Step 0: 진행 중 작업 감지

### `--resume` 플래그가 있는 경우
1. `.dev/*/state.md`를 Glob으로 탐색한다.
2. 각 state.md를 Read하여 `status: in_progress`인 것을 필터링한다. `pipeline` 필드가 있는 state.md(다른 파이프라인 산출물 — 예: `pipeline: gx-tdd`)는 후보에서 제외한다.
3. `in_progress`가 **1개**이면 → 질문 없이 바로 재개 (아래 "이어서 진행" 절차).
4. `in_progress`가 **2개 이상**이면 → AskUserQuestion으로 사용자에게 선택을 요청한다:
   ```
   AskUserQuestion(
     questions: [{
       question: "재개할 수 있는 작업이 여러 개 있습니다. 어떤 작업을 재개할까요?",
       header: "재개 작업 선택",
       multiSelect: false,
       options: [
         { label: "<branch-1>", description: "<args-1>" },
         { label: "<branch-2>", description: "<args-2>" },
         ...각 state.md의 branch + args로 옵션 생성
       ]
     }]
   )
   ```
5. state.md가 없거나 모두 `status: completed`이면 → "재개할 작업이 없습니다." 출력 후 종료. `pipeline` 필드 제외로 후보가 0개가 된 경우에는 해당 파이프라인의 재개 명령을 안내한다 (예: `pipeline: gx-tdd`이면 "`/gx-tdd --resume`으로 재개하세요.") 후 종료.

### `--resume` 플래그가 없는 경우 (자동 감지)
ARGS[0]이 있으면 → 새 작업이므로 자동 감지를 건너뛰고 Step 1로 진행.
ARGS[0]이 없으면 → 아래 자동 감지 로직 실행.

1. `.dev/*/state.md`를 Glob으로 탐색한다.
2. state.md가 존재하고 `status: in_progress`이면:
   - `pipeline` 필드가 있으면(다른 파이프라인 산출물 — 예: `pipeline: gx-tdd`) 재개를 제안하지 않는다. "진행 중 작업은 {pipeline} 파이프라인 산출물입니다. 해당 파이프라인으로 재개하세요 (예: `/gx-tdd --resume`)." 안내 후 종료한다 (상태 덮어쓰기 방지).
   - 사용자에게 AskUserQuestion으로 질문:
     ```
     AskUserQuestion(
       questions: [{
         question: "이전에 진행하던 작업이 있습니다. 어떻게 할까요?",
         header: "이전 작업 감지",
         multiSelect: false,
         options: [
           { label: "이어서 진행", description: "이전 작업을 재개합니다" },
           { label: "새로 시작", description: "새 작업을 시작합니다" }
         ]
       }]
     )
     ```
     - "이어서 진행" → 재개
     - "새로 시작" → Step 1로 진행 (Step 7에서 덮어씀)
3. state.md가 없거나 `status: completed`이면 → Step 1로 진행.

**이어서 진행 시:**
- state.md에서 VCS_TYPE, GIT_PREFIX, PROJECT_ROOT, DEV_DIR, 베이스 브랜치, 프로젝트 타입, ARGS[0], flags, mode, model-profile을 복원. VCS_TYPE이 없으면 `"git"`으로 fallback. model-profile이 없으면(구 세션) config.json `modelProfile` 값(비어있으면 `standard`)으로 결정한다. DEV_DIR이 없으면 재구성한다 — git은 브랜치명의 `/`를 `-`로 치환, svn은 `.dev/.active`가 가리키는 `.dev/{slug}`(없으면 `.dev/trunk` 폴백). Step 5의 DEV_DIR 설정 규칙과 동일.
- **구 버전 세션 방어**: state.md에 `mode` 필드가 **존재하고** 그 값이 `all`/`core`가 아니면(v1.18.0 이전 구 버전에서 생성된 세션) 재개하지 않는다. "이 작업은 구 버전(v1.18.0 미만)에서 생성되어 재개할 수 없습니다. `/gx-dev {작업 설명}`으로 새로 시작해주세요." 안내 후 종료한다. **`mode` 필드가 없는 세션은 거부하지 않는다** — `--phase` 부트스트랩 골격 등 mode를 기록하지 않는 정상 v1.18.0 산출물이므로 그대로 재개한다.
- `test -d`로 경로 검증. 실패 시 "작업 경로가 유효하지 않습니다." → 새로 시작.
- `${DEV_DIR}/prd.md`, `${DEV_DIR}/design.md`, `${DEV_DIR}/trust-ledger.md`, `${DEV_DIR}/codemap.md`, `${DEV_DIR}/self-check.md`, `${DEV_DIR}/ac.md`, `${DEV_DIR}/summary.md`가 있으면 Read하여 맥락 복원.
- `references/` 디렉토리가 있으면 외부 규격 참조 탐색(Step 3의 5번 항목)을 재실행하여 `REFERENCES`를 복원한다.
- `context/` 디렉토리가 있고 베이스 브랜치가 있으면 Step 3-0 (context 최신화)을 재실행한다.
- Step 3의 도메인 컨텍스트 탐색(4번 항목)을 재실행하여 `DOMAIN_CONTEXT`를 복원한다. 이 단계는 Step 3-0과 독립적이다 — 베이스 브랜치가 없어 Step 3-0을 건너뛰더라도 `DOMAIN_CONTEXT` 복원은 실행한다.
- phases 맵에서 마지막 in_progress Phase를 찾아 재개.
- phase-setup의 나머지 단계(Step 1~Step 7)를 건너뛴다.

### 착수 기록 보정 (`--work` 세션 재개 시)

재개("이어서 진행")로 진입했고 state.md에 `work-id`가 있으면, `.dev/plan.md`의 해당 행이 이미 `진행`이고 `작업 위치`가 채워져 있는지 확인한다. 아직 `대기`이거나 `작업 위치`가 `-`이면 **Step 5.5가 실행되지 못한 채 중단된 세션**이다 (stash pop 충돌 등으로 Step 5 종료 시점에 멈춘 경우). 지금 기입하고 `docs: [plan] {ID} 착수` 메시지로 커밋한 뒤 `git push -u origin {현재 브랜치}`로 push한다.

재개 경로는 Step 5를 다시 거치지 않으므로 여기서 보정하지 않으면 착수 기록이 영영 남지 않는다 — 브랜치는 있는데 계획에는 흔적이 없어, 다른 팀원이 같은 작업에 착수해도 감지되지 않는다. 이미 기입되어 있으면 아무것도 하지 않는다. `work-id`가 없거나 계획 파일이 없으면 건너뛴다. svn이면 커밋하지 않고 사용자에게 안내한다.

## Step 1: VCS 확인

`.claude/config.json`의 `"vcs"` 필드를 읽어 `VCS_TYPE`을 결정한다.

**git인 경우** (vcs가 `"git"` 또는 `""` 미설정):
- `git rev-parse --is-inside-work-tree` 확인.
- 성공 → `VCS_TYPE` = `"git"`, `GIT_PREFIX` = `git`.
- 실패:
  ```
  AskUserQuestion(
    questions: [{
      question: "Git 저장소가 아닙니다. git init으로 생성할까요?",
      header: "git init",
      multiSelect: false,
      options: [
        { label: "예", description: "git init을 실행합니다" },
        { label: "아니오", description: "작업을 중단합니다" }
      ]
    }]
  )
  ```
  - 예 → `git init` 실행 후 계속.
  - 아니오 → 중단.

**svn인 경우:**
- `svn info` 확인.
- 성공 → `VCS_TYPE` = `"svn"`, `GIT_PREFIX` = `svn`.
- 실패 → "SVN 작업 복사본이 아닙니다." 출력 후 중단.

## Step 1.5: 모델 프로파일 결정

`MODEL_PROFILE`을 결정한다 (우선순위 순 — 먼저 매칭된 것 사용):
1. 플래그: `--eco` → `eco`, `--standard` → `standard`
2. ARGS[0] 자연어: `에코 모드`/`에코로`/`절약 모드` 포함 → `eco` (단독 명사 `에코`는 오탐 방지를 위해 제외)
3. 의도 파싱 Step 3에서 프로파일 질문에 답한 경우 → 그 답변 (표준 → `standard`, 에코 → `eco`)
4. `.claude/config.json`의 `"modelProfile"` 값 (`"eco"` / `"standard"`) — config.json이 없거나 파싱 불가하면 건너뛴다
5. 그 외 (미설정·빈 값·config 부재) → `standard`

`eco`로 결정되면 안내한다: "에코 모드로 실행합니다 — 에이전트 디스패치가 sonnet 중심으로 하향됩니다 (절차·게이트는 동일). 더 큰 절감을 원하면 실행 전 세션 모델도 sonnet으로 바꾸세요 — 그래야 오케스트레이터와 인라인 단계(setup·complete 등)까지 sonnet으로 실행됩니다. (에코는 에이전트 디스패치만 낮추며, 오케스트레이터/메인 세션 모델은 플러그인이 제어하지 못합니다.)"
`standard`로 결정되면 안내한다: "표준 프로파일 — 에이전트를 frontmatter 모델대로 디스패치합니다 (architect·coder·design-critic 등 opus 에이전트는 세션 모델과 무관하게 opus로 실행). 세션 모델을 sonnet으로 낮춰 절감하려면 표준이 아니라 eco를 쓰세요 — 표준은 이 opus 에이전트들을 그대로 유지하므로 절감 효과가 제한적입니다."
결정 값은 Step 7에서 state.md `model-profile`에 기록한다. 디스패치 적용 규칙은 SKILL.md 공유 규칙 "모델 프로파일" 참조.

## Step 2: 베이스 브랜치 결정

**svn인 경우** → 건너뛴다. SVN은 브랜치 없이 trunk에서 직접 작업한다.

**git인 경우:**

공유 규칙의 "베이스 브랜치 감지"에 따라 결정한다.

결정 후 베이스 브랜치를 최신 상태로 동기화한다:
1. `git remote get-url origin`으로 remote 존재를 확인한다. 없으면 건너뛴다.
2. `git checkout <base-branch>`를 실행한다. 실패 시 경고를 표시하고 현재 로컬 상태로 계속 진행한다.
3. checkout 성공 시, `git pull origin <base-branch>`를 실행한다. pull 실패 시 (네트워크 오류 등) 경고를 표시하고 현재 로컬 상태로 계속 진행한다.

## Step 3-0: context 최신화

**git인 경우에만 실행한다.** svn인 경우 건너뛴다.

`context/` 디렉토리가 존재하고, 베이스 브랜치(Step 2에서 결정)가 있으면 실행한다. 둘 중 하나라도 없으면 건너뛴다.

작업 브랜치의 `context/`가 베이스 브랜치보다 오래되었을 수 있다 (다른 개발자가 context를 갱신한 경우). 파이프라인 시작 전에 최신 상태로 맞춘다.

> **참고**: 새 작업 흐름에서는 이 시점에 아직 작업 브랜치가 생성되지 않았다 (Step 5에서 생성). 따라서 현재 HEAD는 베이스 브랜치이고, diff는 항상 "차이 없음"이 되어 이 Step은 no-op이다. 이 Step이 실질적으로 동작하는 경우는 **`--resume`으로 재개할 때**와 **기존 작업 브랜치에서 파이프라인을 다시 시작할 때**이다.

1. `${GIT_PREFIX} diff ${BASE_BRANCH}... -- context/`로 차이를 확인한다. triple-dot(`...`)은 merge-base 기준으로 비교하므로, 베이스 브랜치에 새 커밋이 추가되어도 작업 브랜치의 순수 변경만 감지한다.
2. **차이가 없으면** → 건너뛴다.
3. **차이가 있으면**:
   a. 작업 브랜치에서 context를 변경했는지 2단계로 확인한다:
      - `${GIT_PREFIX} diff ${BASE_BRANCH}... -- context/` — 커밋된 변경 (이미 항목 1에서 확인했으므로 결과 재사용)
      - `${GIT_PREFIX} diff HEAD -- context/` — 미커밋(워킹 디렉토리 + 스테이징) 변경
      - 둘 중 하나라도 차이가 있으면 "작업 브랜치에 context 변경이 있음"으로 판단한다.
   b. **작업 브랜치에 context 변경이 없으면** → 안전하게 덮어쓴다:
      - `${GIT_PREFIX} checkout ${BASE_BRANCH} -- context/`로 베이스 브랜치의 context를 가져온다.
      - 사용자에게 보고한다: "context/를 ${BASE_BRANCH} 기준으로 최신화했습니다."
   c. **작업 브랜치에도 context 변경이 있으면** → 충돌 가능성이 있으므로 사용자에게 확인한다:
      ```
      AskUserQuestion(
        questions: [{
          question: "작업 브랜치와 베이스 브랜치 모두 context/가 변경되었습니다. 베이스 기준으로 덮어쓸까요?",
          header: "context 충돌",
          multiSelect: false,
          options: [
            { label: "덮어쓰기", description: "베이스 브랜치 기준으로 최신화합니다 (작업 브랜치 변경 유실)" },
            { label: "유지", description: "현재 상태를 유지하고 진행합니다" }
          ]
        }]
      )
      ```
      - 덮어쓰기 선택 → `${GIT_PREFIX} checkout ${BASE_BRANCH} -- context/` 실행.
      - 유지 선택 → 현재 상태로 계속 진행한다.
   d. 실패 시 경고를 표시하고 현재 상태로 계속 진행한다.

## Step 3: 프로젝트 정보 수집
`PROJECT_ROOT = ./` (현재 디렉토리).

### 3.0.5 작업 계획 참조 (`--work` 사용 시)

`--work {ID}`가 지정된 경우에만 수행한다. 지정되지 않았으면 이 절을 통째로 건너뛰고 아래 병렬 수집으로 진행한다 — plan.md를 읽지 않으므로 기존 동작이 그대로 유지된다.

1. `.dev/plan.md`를 Read한다. 파일이 없으면 "작업 계획이 없습니다. `.dev/plan.md`를 만들거나 `--work` 없이 실행하세요." 출력 후 중단한다.
2. 표에서 ID가 일치하는 행을 찾는다. 표 파싱에 실패하거나 행이 없으면 "작업 계획에서 {ID} 행을 찾지 못했습니다." 출력 후 중단한다. 조용히 진행하지 않는다.
3. **이슈 키 추출을 건너뛴다.** 아래 브랜치 결정 단계의 이슈 키 파싱을 수행하지 않는다 — 작업 ID가 이슈 키로 오인되면 브랜치명이 오염되어 gx-commit의 타입 파싱이 깨진다.
4. **브랜치명을 `작업` 열에서 생성한다.** `{type}/{description}` 형식이며, description은 Step 5의 규칙과 동일하게 **한국어→영어로 번역하고 최대 40자**로 만든다 — `--work` 유무로 브랜치 명명 규칙이 갈리지 않게 한다. type은 AskUserQuestion으로 확인한다 (기본값 `feat`). svn이면 브랜치 대신 `.dev/{slug}/`의 slug로 쓴다.
5. **코드 맵 키워드**를 `작업` + `요구사항` 열 텍스트에서 추출한다 (이슈 키 제외 규칙 대신).
6. **도메인 컨텍스트**를 `도메인` 열의 도메인 하나만 로드한다 (`glossary.md`·`architecture.md`·`status.md`). 도메인이 예약어 `공통` 또는 `통합`이면 context를 읽지 않고 `DOMAIN_CONTEXT`를 빈 상태로 둔다. 이 경우 아래 병렬 수집의 "도메인 컨텍스트 탐색"(레포 매칭)은 수행하지 않는다 — 작업 계획이 도메인을 이미 확정했다.
7. **의존 확인**: `의존` 열의 각 ID가 표에서 `완료` 상태인지 확인한다. 아닌 것이 있으면 AskUserQuestion으로 진행 여부를 확인한다.
8. **대상 작업 상태·중복 착수 확인** (읽기만 한다 — 표를 여기서 고치지 않는다):
   - 행의 `상태`를 먼저 본다. `폐기`면 요구사항이 삭제되어 할 일이 없어진 작업이므로 "폐기된 작업입니다 — 계획을 확인하세요" 경고 후 AskUserQuestion으로 진행 여부를 확인한다. `완료`면 "이미 완료된 작업입니다"로 안내하고 확인받는다 — 재작업·수정은 정상이라 막지 않되, 아래 중복 착수 경고("다른 사람이 진행 중")와 메시지가 섞이지 않게 구분한다.
   - `작업 위치` 열 값이 `-`가 아니면 누군가 이미 착수한 것이다. 단, state.md의 `work-id`가 같은 ID이고 그 값이 현재 브랜치(svn은 `.dev/.active`의 slug)와 일치하면 **자기 재개**이므로 경고하지 않는다.
   - git이면 `git ls-remote --heads origin {브랜치명}`으로 원격에 그 브랜치가 있는지도 확인한다. 착수 커밋은 PR이 머지되기 전까지 베이스 브랜치의 plan.md에 반영되지 않으므로, 열 값이 `-`여도 원격 브랜치가 있으면 다른 사람이 진행 중이다. 명령이 실패하면(원격 없음·네트워크) 이 확인만 건너뛴다.
   - 둘 중 하나라도 착수 정황이면 경고하고 AskUserQuestion으로 진행 여부를 확인한다.
   - **기입과 커밋은 Step 5.5에서 한다.** 이 시점의 현재 브랜치는 아직 베이스 브랜치이므로(Step 2.2가 checkout했다) 여기서 커밋하면 보호 브랜치 가드(`pre-tool-guard.sh` G1)에 `deny`되어 기록이 남지 않는다.
9. **ARGS[0] 보강**: `작업` 열 텍스트를 요청 문구로 사용한다.
10. **state.md에 `work-id: {ID}`를 기록한다** — `--resume` 시 문맥 복원과 phase-complete의 행 매칭 근거가 된다.

#### 진행할 작업 확인

작업이 확정되면 **무엇으로 진행하는지 사용자에게 보여준 뒤** 다음 단계로 넘어간다. 계획에서 자동으로 읽어온 값이라 사용자가 의도한 것과 다를 수 있고, 도메인·요구사항 범위는 이후 모든 에이전트의 입력이 되므로 여기서 어긋나면 되돌리기 어렵다.

```
작업 계획에서 W01을 찾았습니다.

  작업       이관 이력 조회
  도메인     재고관리     (context/재고관리/ 를 참조합니다)
  요구사항   FR-4~6
  선행       W00 완료됨
  브랜치     feat/transfer-history (새로 만듭니다)

이대로 진행합니다.
```

선행 작업이 완료되지 않았거나 다른 사람이 이미 착수한 경우에만 AskUserQuestion으로 멈춰 확인받는다. 정상 경로에서는 표시만 하고 진행한다 — 확인이 잦으면 흐름이 끊긴다.

#### 계획이 있으나 작업 ID가 지정되지 않은 경우

`.dev/plan.md`가 존재하는데 요청에 작업 ID가 없으면, **요청 내용을 계획의 대기 작업과 대조**한다. 사용자가 계획의 존재를 잊었거나 아직 모를 수 있기 때문이다.

- 요청과 뚜렷하게 대응하는 대기 작업이 **있으면**: 그 작업으로 진행할지 AskUserQuestion으로 확인한다. "아니오"면 계획과 무관하게 기존 경로로 진행한다.
- 대응하는 작업이 **없으면**: 조용히 기존 경로로 진행한다. 계획에 없는 작업을 하는 것은 정상이며, 매번 "계획을 쓰시겠어요?"라고 묻는 것은 방해다.

```
요청하신 내용이 작업 계획의 W02와 비슷합니다.

  W02  분류 규칙 관리 · 재고관리 · FR-7~9 · 대기

  [ W02로 진행 / 계획과 무관하게 진행 ]
```

이 대조는 계획 파일이 있을 때만 수행한다. 파일이 없으면 아무 일도 하지 않으므로 기존 프로젝트의 동작은 그대로다.

### 3.1 병렬 수집

아래 5개 작업은 서로 독립적이므로 **병렬로 실행**한다:
1. **프로젝트 타입 감지**: `.claude/config.json`의 `projectTypes`에서 detect 필드와 매칭한다 (예: `build.gradle.kts` → `java-spring`, `package.json` → `node`, `Makefile` → `c-make`). 여러 타입이 감지되면 모두 기록한다. **매칭 실패 시**: gx-setup의 "프로젝트 타입 등록" 절차(빌드 파일 스캔 → 힌트 카탈로그 `Read("../../gx-setup/references/project-type-hints.md")` 제안 → 사용자 확인 → config 기록 → 권한 등록 → 하네스 확인)를 인라인으로 1회 실행한다. 사용자가 등록을 건너뛰면 타입 미상으로 진행한다 (이후 게이트는 fail-closed 동작 — 조용한 통과 없음). 타입 감지와 함께 config.json의 `modelProfile`(Step 1.5가 이미 결정했으면 그 값 유지)·`sensitiveFilePatterns`·`buildArtifactPatterns`·`timeouts`·`contextLimits`도 함께 로드하여 이후 단계(에이전트 입력 상한, 커밋 가드, 타임아웃)에서 참조한다.
2. **디렉토리 구조 수집**: `PROJECT_ROOT`의 최상위 2레벨 디렉토리 구조를 수집한다.
3. **CLAUDE.md 확인**: `PROJECT_ROOT`에 CLAUDE.md가 있으면 읽어서 코딩 컨벤션을 확보한다.
4. **도메인 컨텍스트 탐색**: 현재 레포와 매칭되는 도메인 컨텍스트를 찾는다.
   - **git**: `git remote get-url origin`으로 레포명을 추출한다 (예: `xx/asset-factory-api`).
   - **svn**: `svn info --show-item repos-root-url`로 저장소 URL을 추출하고, URL의 마지막 세그먼트를 레포명으로 사용한다.
   - `context/*/PROJECTS.md`를 Grep하여 해당 레포를 참조하는 도메인을 찾는다.
   - 매칭되면 해당 도메인의 `glossary.md`, `architecture.md`를 Read하여 `DOMAIN_CONTEXT`에 저장한다.
   - `context/` 디렉토리가 없거나 매칭되지 않으면 `DOMAIN_CONTEXT`는 빈 상태로 진행한다.
     사용자에게 안내: "도메인 컨텍스트가 없습니다. `context/` 디렉토리를 생성하고 `/gx-context`로 도메인을 등록하면 이후 작업에서 용어/아키텍처를 참조할 수 있습니다."
   - `DOMAIN_CONTEXT`는 이후 agent 프롬프트에 "도메인 컨텍스트"로 포함한다.
5. **외부 규격 참조 탐색**: 프로젝트 루트에 `references/` 디렉토리가 있는지 확인한다.
   - `references/` 디렉토리가 존재하면:
     a. 디렉토리 내 파일 목록을 수집한다 (하위 디렉토리 포함).
     b. 각 파일에서 한줄 설명을 추출한다:
        - `.md` 파일: 첫 번째 `#` 헤딩 텍스트
        - `.txt` 파일: 첫 번째 비공백 줄
        - 그 외 (`.pdf` 등): 파일명 그대로 사용
     c. 파일 목록 + 한줄 설명을 `REFERENCES` 변수에 저장한다.
   - `references/` 디렉토리가 없으면 `REFERENCES`는 빈 상태로 진행한다. 안내 메시지를 출력하지 않는다.

## Step 4: 관련 코드 맵 생성
ARGS[0]에서 도메인 키워드를 추출하여 `PROJECT_ROOT` 내에서 관련 코드를 탐색하고 초기 코드 맵을 생성한다.

1. **키워드 추출**: ARGS[0]에서 핵심 도메인 키워드를 추출한다 (이슈 키 제외).
   - 예: "[JIRA-123] 결제 한도 변경" → `결제`, `한도` → `payment`, `limit`, `amount`
2. **관련 파일 탐색**: `PROJECT_ROOT`를 기준으로 키워드로 Grep하여 관련 파일을 수집한다.
   - 서비스, 도메인 모델, 컨트롤러/핸들러 등 핵심 파일을 식별한다.
3. **핵심 파일 스캔**: 발견된 파일의 상단(클래스 선언, 주요 상수/메서드 시그니처)을 Read하여 역할을 한 줄로 정리한다.
4. **코드 맵 작성**: 핵심 파일 / 참조 파일 / 설정으로 분류하여 맵을 작성한다.

탐색은 **가볍게** — 파일 전체를 읽지 않고, 역할 파악에 필요한 최소한만 읽는다. 코드 맵에 등록하는 파일은 **최대 15개**로 제한한다 (핵심 ≤ 5, 참조 ≤ 7, 설정 ≤ 3). 초과 시 관련도가 높은 파일을 우선한다. 상세한 코드 분석은 이후 agent들이 맵을 기반으로 타겟팅하여 수행한다.

## Step 5: 작업환경 생성

**svn인 경우** → 건너뛴다. SVN은 trunk에서 직접 작업하며, `svn update`로 최신 상태만 동기화한다. 완료 후 프로젝트 타입, 작업 경로를 사용자에게 보고.

**git인 경우:**

격리된 작업환경을 생성한다.
- **`--work` 사용 시**: 3.0.5에서 이미 결정한 브랜치명을 그대로 쓴다. 아래 유도 절차(이슈 키 추출 포함)를 수행하지 않는다 — 여기서 다시 유도하면 3.0.5가 `작업 위치` 열에 기록한 이름과 어긋나고, phase-complete의 작업 계획 갱신 단계에서 행 매칭(`작업 위치` = 현재 브랜치)이 실패한다.
- ARGS[0]에서 브랜치명을 생성한다 (`--work` 미사용 시):
  1. 이슈 키 추출 시도: 대문자 영문 + `-` + 숫자 패턴 (e.g., `JIRA-123`, `PAY-456`)
  2. **이슈 키가 있으면**: 이슈 키를 브랜치명으로 사용 (e.g., `[JIRA-123] 로그인 기능 추가` → 브랜치 `JIRA-123`)
  3. **이슈 키가 없으면**: 요청 성격에 맞는 타입(config.json `conventions.branchTypes` 중 선택)과 핵심 키워드로 `conventions.branchFormat`(`{type}/{description}`) 형식의 브랜치명을 생성한다. description은 한국어→영어 번역, 최대 40자 (e.g., `로그인 기능 추가` → `feat/login-feature`. 타입 접두사가 있어야 gx-commit의 타입 파싱이 동작한다)
- `git checkout -b <branch-name>`으로 브랜치를 생성한다. 브랜치가 이미 존재하면 (`already exists` 에러) `git checkout <branch-name>`으로 전환한다.
- **DEV_DIR 설정**: 브랜치명(또는 svn 작업 slug)이 결정된 직후 `DEV_DIR`을 설정한다.
  - **git**: branch-slug는 브랜치명에서 `/`를 `-`로 치환한다 (예: `feat/login` → `feat-login`). `DEV_DIR = .dev/{branch-slug}`.
  - **svn**: 브랜치가 없으므로 git 브랜치명 생성과 **동일한 규칙**으로 작업 slug를 만든다 — `--work` 사용 시 3.0.5가 결정한 slug를 그대로 쓰고, 아니면 ARGS에 `--slug <name>`이 있으면 그 값, 없고 ARGS[0]에 이슈 키(config `issueKey.pattern`)가 있으면 이슈 키, 둘 다 없으면 요청 타입+키워드로 `{type}-{description}`(최대 40자)을 만든다. slug는 `/`→`-` 치환 후 `[a-zA-Z0-9._-]`로 정규화하고(대문자 이슈 키 보존) `/`·`..`를 제거한다. `DEV_DIR = .dev/{slug}` (고정 `.dev/trunk`가 아닌 **기능별 격리**). 결정한 slug를 `.dev/.active`에 기록한다(덮어쓰기) — 훅·라우팅·verify가 활성 작업의 state.md를 찾는 포인터.
  - `mkdir -p ${DEV_DIR}`를 실행하여 디렉토리를 생성한다.
- 완료 후 프로젝트 타입, 브랜치명, 작업 경로를 사용자에게 보고.

## Step 5.5: 작업 계획 착수 기록 (`--work` 사용 시)

`--work`로 진입한 경우에만 수행한다. 3.0.5가 판정만 하고 쓰기를 여기로 미룬 이유는, 그 시점의 현재 브랜치가 아직 베이스 브랜치(Step 2.2가 checkout했다)여서 `git commit`이 보호 브랜치 가드(`pre-tool-guard.sh` G1)에 `deny`되기 때문이다. 작업 브랜치로 전환된 지금은 통과한다.

1. `.dev/plan.md`에서 해당 행의 `작업 위치` 열에 브랜치명(svn은 slug)을 기입하고 `상태` 열을 `진행`으로 바꾼다.
2. **전용 커밋**: `.dev/plan.md`만 스테이징해 `docs: [plan] {ID} 착수` 메시지로 커밋하고 `git push -u origin {브랜치명}`으로 push한다. 베이스 브랜치로 보내지 않는다 — 브랜치 보호가 걸린 저장소에서 거부되고, phase-complete의 완료 갱신과 층위가 어긋난다. **`-u`를 빠뜨리지 않는다.** 방금 만든 브랜치라 upstream이 없어 `git push`만으로는 `no upstream branch`로 실패하고, 그러면 원격 브랜치가 생기지 않아 3.0.5의 중복 착수 감지가 근거를 잃는다. push가 실패하면 경고에 "다른 팀원이 이 착수를 감지하지 못합니다"를 포함해 남기고 진행한다 (착수 기록은 조율 수단이지 게이트가 아니다).
3. svn이면 커밋하지 않고 사용자에게 터미널에서 반영하도록 안내한다.

이 커밋은 PR과 함께 베이스 브랜치로 머지된다. 그전까지 다른 팀원에게는 **원격 브랜치의 존재**로 드러난다 — 3.0.5의 중복 착수 확인이 `git ls-remote`로 이를 본다.

## Step 6: VCS ignore 자동 보강

**svn인 경우** → 건너뛴다. 단, 이전 버전이 `svn:ignore`에 등록한 `.dev`가 남아 있으면 제거를 제안한다 (`.dev` 산출물은 협업 공유 대상 — `svn propget svn:ignore .` 확인 후 사용자 확인을 받아 재적용).

단 **`.dev/.active`는 공유 예외**다 — 이 머신의 활성 작업을 가리키는 런타임 포인터라 공유되면 다른 사용자의 `--resume`·verify baseline이 타인 세션 기준으로 오염된다. `.dev`가 아직 unversioned면 `svn add --depth=empty .dev`로 디렉토리만 등록한 뒤 `svn propset svn:ignore '.active' .dev`를 적용해 `.active`를 공유에서 제외한다. 이미 `.active`가 versioned로 커밋되어 있으면 `svn rm --keep-local .dev/.active`로 버전 관리에서만 제거하도록 안내한다. 제거 후에는 위 `svn propset svn:ignore '.active' .dev`를 반드시 재적용한다 (ignore 속성이 없으면 다음 `svn add --force .`가 `.active`를 다시 등록한다).

**git인 경우:**

프로젝트 타입에 따라 `.gitignore`에 빌드 아티팩트 패턴을 추가한다. **패턴은 config `projectTypes.{타입}.artifacts` 필드에서 읽는다** (SSOT는 config — 예: java-spring `.gradle/`·`build/`, node `node_modules/`·`dist/`). `artifacts` 필드가 없는 타입은 이 보강을 건너뛴다. 이미 존재하는 패턴은 건너뛴다.

`.dev/`는 `.gitignore`에 추가하지 않는다 — 파이프라인 산출물(PRD·설계서·Trust Ledger·state.md 등)은 **협업 공유 대상**으로 커밋에 포함된다 (verify 지문은 `.dev`를 인덱스에서 제외하므로 게이트와 무관). 기존 `.gitignore`에 이전 버전이 추가한 `.dev/` 패턴이 남아 있으면 제거를 제안한다 (사용자 확인 후 해당 줄 삭제). 일시 파일(ralph.lock, verify-*.log 등)도 함께 커밋될 수 있음을 사용자에게 안내한다.

## Step 7: 진행 상태 초기화
Write 전에 기존 `${DEV_DIR}/state.md`가 존재하고 `status: in_progress`이며 `pipeline` 필드가 있으면(다른 파이프라인 산출물), 덮어쓰면 해당 파이프라인 상태(verify 게이트 포함)가 유실됨을 경고하고 AskUserQuestion으로 덮어쓰기/중단을 확인받는다.
`${DEV_DIR}/state.md`에 초기 상태를 Write한다:
- phase: setup, status: in_progress
- vcs-type, branch, base, dev-dir, project-type, project-root, args, flags 기록. `flags`에는 의도 파싱의 RALPH 우선순위 규칙을 **통과해 살아남은** RALPH만(플래그·자연어 `랄프로` 등 출처 무관) `--ralph`로 **정규화하여** 포함한다 — phase-implement "gx-ralph 전환" 절의 판정 키이며 별도 필드를 두지 않는다. 우선순위 규칙에서 **무시된 RALPH는 기록하지 않는다** (core 세션에 `--ralph`가 남아 `--status`·전환 절이 이중 안내를 내지 않도록). `VCS_TYPE`이 `svn`이면 포함하지 않고 "gx-ralph는 SVN 미지원 — 대화형으로 진행합니다" 1줄을 안내한다 (의도 파싱의 svn 우선 배제가 1차, 이것은 2차 방어)
- mode, intent-source 기록 (의도 파싱 결과)
- model-profile 기록 (Step 1.5 결정 값)
- phases: { setup: completed }

**작업 계획 되돌림**: 덮어쓰기 전의 state.md가 `status: completed`였고 그 파일의 `work-id`가 가리키는 행이 `.dev/plan.md`에서 `완료`이면, 그 행을 `진행`으로 되돌리고 `.dev/plan.md`만 스테이징해 `docs: [plan] {ID} 재개` 메시지로 커밋한다. 완료 표시를 남겨두면 다른 팀원이 미검증 산출물을 전제로 후속 작업에 착수한다. `work-id`가 없거나 계획에 행이 없으면 아무것도 하지 않으며, 이번 실행의 Step 5.5가 이미 그 행을 `진행`으로 바꿨다면 추가 작업이 없다. 되돌림이 여기 있는 이유는 완료 상태를 뒤집는 순간이 이 Write뿐이기 때문이다 — phase-complete는 완료를 기록할 뿐 재진입을 알지 못한다.

