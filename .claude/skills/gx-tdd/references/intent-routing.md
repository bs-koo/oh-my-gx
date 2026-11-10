> gx-tdd/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태/질문/페이즈 결정을 추정하지 않는다. 상대경로는 이 파일의 위치를 기준으로 해석한다.

## 인자

`ARGS[0]`에 자연어 요청을 받는다. 레거시 플래그도 호환한다.

### 제거된 무인 반복 경로 — 실행 전 중단

Ralph 무인 반복 기능은 제거되었다. 인계·부분 phase·재개를 포함해 **실행 setup과 state/브랜치/코드/빌드 변경 전에** 아래를 읽기 전용으로 확인한다.

- 실제 실행 인자에 `--ralph`, 명시 `/gx-ralph`·`/gx-ralph-iterate` 호출, 또는 무인 실행을 요구하는 `랄프로`·`ralph로`·`무인 루프로`·`루프 돌려`가 있으면 `unsupported-request`로 중단한다. 파일명·원문 인용·명시적 부정이나 설명/제거 요청을 실행 명령으로 오인하지 않는다. 일반 개발이나 커밋으로 조용히 대체하지 않는다.
- DEV_DIR은 상태 계약의 Git 현재 branch-slug 또는 SVN `.dev/.active` 규약으로 읽기 전용 계산한다. SVN 활성 포인터가 없거나 여러 진행 기록이 있으면 읽기 전용 후보 확인 후 같은 검사를 적용한다. 이 확인을 위해 state 초기화·브랜치 생성·포인터 쓰기를 하지 않는다.
- 현재 프로젝트/작업 경로를 읽기 전용으로 확정한 뒤 `status: in_progress`인 기존 `pipeline: gx-ralph` 또는 그 진행 상태에 저장된 `flags`의 `--ralph`가 있으면 `migration-required`로 중단한다. `${DEV_DIR}/ralph.lock`이 있으면 상태와 무관하게 별도 구버전 러너가 실행 중일 수 있음을 알리고 `loop-active`로 새 실행을 막는다. 잠금을 지우거나 프로세스를 종료하지 않는다.
- **구버전 기록에서 빠져나오기**: 그 state·잠금은 고치거나 지우지 않는다. git은 베이스에서 새 브랜치로 시작한다. 미커밋 변경이 있으면 그 변경을 옮기지 않도록 별도 워크트리(`git worktree add <경로> -b <새 브랜치> <베이스>`)를 만들고 그 경로에서 `/oh-my-gx:gx-work <목표>`로 새 진입 결정을 받는다. SVN은 새 목표를 `--slug <새 slug>`로 시작하며 이 검사는 그 slug의 기록에만 적용하고 setup Step 5가 `.dev/.active`를 새 slug로 바꾼다. 같은 브랜치에서 gx-work 전환을 다시 요청하게 안내하지 않는다(같은 판정으로 되돌아온다).
- 기존 PRD·설계·AC 원장·커밋·state는 보존한다. 지원 중단과 확인한 기록 경로를 알리고, 사용자가 새 TDD 작업으로 전환하도록 실제 요청한 경우에만 범위·미완료 항목·검증 근거를 검토한다. 원래 pipeline/실행 ID/승인을 새 실행으로 덮거나 자동 승인으로 승격하지 않는다.

상태 조회·기존 문서 검토는 읽기 전용으로 보고할 수 있다. 지원 중단 안내는 확인된 범위에 한정하며, 이 규약 자체가 구버전 외부 러너를 강제로 정지시키는 보안 경계라고 주장하지 않는다.

`status: completed`인 구버전 기록은 재개하지 않는다. 그 실행의 pending·완료·승인을 새 실행에 재사용하지 않으며, 기존 기록을 보존하고 사용자가 명시한 새 목표에 새 진입/계획 결정을 적용해 fresh TDD를 시작할 수 있다. 완료된 구버전 기록 때문에 새 작업을 영구 차단하지 않는다.

### 의도 파싱

ARGS[0]을 받으면 아래 순서로 의도를 파싱한다:

**Step 1: 플래그 호환** (기존 사용자 보호)
- --handoff <JSON>·--from-plan <JSON>·--stop-at verify|commit|pr·--full-tests를 먼저 분리하고 [계획 인계 계약](plan-handoff.md)을 적용한다. 원문 파일명은 자연어 의도 키워드로 해석하지 않는다. gx-work origin은 실제 진입 응답을 `validate-handoff`로 검증하기 전 실행 setup을 시작하지 않는다. 일반 요청 문구가 false/pending 승인을 대체하지 않는다.
- **`--work {ID}`는 다른 플래그보다 먼저 추출한다.** 아래 모드 플래그 분기에서 파싱이 종료되기 전에 소비해야 `--work --core`처럼 조합된 경우에도 작업 계획 참조가 유실되지 않는다. 추출 후 남은 인자로 아래 분기를 계속 판정한다.
- **gx-work 인계의 모드 판정**: `origin: gx-work` 인계는 handoff의 `intent`·`stop-at`·`read-only`가 실행 범위를 정한다(계획 전용이 아니면 일반 실행 `all`). 목표 문장에는 Step 2의 STATUS/RESUME/CORE·PHASE 키워드 판정을 하지 않는다. 목표의 "이어서"·"긴급"을 재개·핵심 모드로 오인하지 않기 위해서다. 함께 받은 명시 플래그(`--core`·`--eco`·`--standard`·`--isolated`·`--base`)는 반영하고, 작업 ID·모델은 인계 `work-id`·`model-profile`을 쓴다.
- `--core`, `--phase`, `--base`, `--status`, `--resume`이 포함되면 해당 로직으로 실행.
- `--slug <name>`(SVN 전용)은 작업 slug 지정으로 분리해 phase-setup Step 5의 slug 규칙에 넘긴다. 모드 판정과 독립이며, 구버전 실행이 활성 포인터에 남은 SVN에서 새 범위를 시작하는 경로다.
- `--isolated`가 포함되면 **격리 구현 플래그**와 명시 `subagents` 방법 선택으로 보존한다 — phase-implement Step 2-I가 세션 직접 수행 대신 implementer 디스패치(현행 2석) 경로를 택한다. 모드 판정과 독립이므로 나머지 파싱을 계속한다. 이 선택도 Step 1.2의 실제 계획 검토 전 RED 실행을 허용하지 않는다. 명시 현재 세션 선택/기존 방법과 충돌하면 해소 전 중단한다.
- `--eco` 또는 `--standard`가 포함되면 **모델 프로파일 오버라이드**로 기록한다 (공유 규칙 "모델 프로파일" 참조). 프로파일 플래그는 모드 판정과 독립이므로, 나머지 플래그·자연어 파싱을 계속 진행한다.
- `--work {ID}`가 포함되면 **작업 계획 참조 플래그**로 기록한다 — `.dev/plan.md`의 해당 행에서 도메인·요구사항·브랜치명을 확정한다 (phase-setup "작업 계획 참조" 절). ID 값 형식은 `^W[0-9]{2,}$`(`W` + ASCII 숫자 2자리 이상. `W01`·`W118`, W99 다음은 W100)이다. 하이픈을 쓰지 않는 이유는 `config.json`의 `issueKey.pattern`(`^[A-Z]+-[0-9]+$`)에 매칭되면 브랜치명이 이슈 키로 오염되어 gx-commit의 타입 파싱이 깨지기 때문이다. 작업 계획 플래그는 모드 판정과 독립이므로 나머지 플래그·자연어 파싱을 계속 진행한다.
- 모드 관련 플래그가 없으면 Step 2로 진행한다 (`--eco`/`--standard`만 있는 경우에도 Step 2의 자연어 판정을 계속한다).

**Step 2: 자연어 → 모드 판정**

gx-work 인계는 Step 1의 인계 모드 판정을 따르고 아래 표의 모드·PHASE 판정을 적용하지 않는다. 그 밖의 요청은 먼저 아래 패턴으로 자동 판정을 시도한다:

| 감지 패턴 | 모드 | 예시 |
|-----------|------|------|
| `상태`, `진행`, `어디까지`, `현황` | STATUS | "지금 어디까지 됐어?" |
| `이어서`, `계속`, `재개`, `아까 하던` | RESUME | "아까 하던 작업 이어서 해줘" |
| `긴급`, `핫픽스`, `급한`, `빨리 고쳐`, `버그 수정만` | CORE | "로그인 버그 긴급 수정해줘" (AC를 재현 조건 관점의 G-W-T로 작성) |
| `구현만`, `핵심만`, `라이트`, `가볍게` | CORE | "알림 임계값 검증, TDD로 구현만 해줘" |
| `설계만`, `PRD만`, `리뷰만`, `커밋만` | PHASE(해당) | "설계만 해줘" |
| `{branch}에서`, `{branch} 기반`, `{branch} 브랜치` | BASE 추출 | "develop 브랜치 기반으로 작업해줘" |
| `에코 모드`, `에코로`, `절약 모드` | ECO 추출 (프로파일 — 모드와 독립) | "에코로 TDD 개발해줘" |
| W ID 토큰(`W01`·`W118`, 아래 WORK 추출 규칙) | WORK 추출 (작업 계획 참조 — 모드와 독립) | "W01 시작해줘", "phase W01 개발해줘" |

PHASE 매핑: `PRD만`/`요구사항만` → `--phase requirements`, `설계만` → `--phase design`, `리뷰만` → `--phase review`, `커밋만`/`PR만` → `--phase complete`. 기존 실행에 저장된 `stop-at`이 그 요청과 다르면 아래 **종료점 변경**을 먼저 한다. implement phase 단독 실행은 `--phase implement` 플래그 전용이다. 자연어 "구현만"은 CORE다.

BASE 추출: `{branch}에서`, `{branch} 기반`, `{branch} 브랜치`에서 branch명을 추출하여 `--base`로 처리한다. BASE 추출은 모드 판정과 독립적이다 — BASE가 추출되어도 모드가 결정되지 않으면 Step 3으로 진행한다.

ECO 추출: ARGS[0]에 `에코 모드`/`에코로`/`절약 모드`가 포함되면 모델 프로파일을 `eco`로 기록한다 (`--eco`와 동일. 단독 명사 `에코`는 도메인 용어 오탐 방지를 위해 매칭하지 않는다 — 예: "에코머니 적립 기능"). 프로파일 추출도 모드 판정과 독립적이다 — 모드가 결정되지 않으면 Step 3으로 진행한다.


**WORK 추출 규칙** (오탐 방지가 핵심이다):

- 요청에서 문장 속 W ID를 정규식 `(?<![A-Za-z0-9_-])W[0-9]{2,}(?![A-Za-z0-9_-])`로 찾는다(ASCII 숫자 2자리 이상). 앞뒤에 영숫자·`_`·`-`가 붙은 `PW01`·`W01a`·`JIRA-W01`과 `W1`·전각 숫자는 토큰이 아니다.
- **토큰을 찾았다고 바로 작업 참조로 단정하지 않는다.** `.dev/plan.md`가 존재하고 그 표에 **같은 ID의 행이 실제로 있을 때만** 작업 참조로 확정한다. 화면 코드·버전 표기 등 우연히 형태가 겹치는 경우를 걸러내기 위함이다.
- 계획 파일이 없거나 행이 없으면 **추출하지 않고** 그 토큰을 일반 요청 문구의 일부로 남긴다. 사용자에게 되묻지 않는다 — 계획이 없는 프로젝트에서 `W01`은 그냥 단어다.
- 확정되면 `--work {ID}`를 명시한 것과 동일하게 처리한다 (phase-setup "작업 계획 참조" 절).
- `phase W01`처럼 앞에 `phase`가 붙어도 같다. 뒤따르는 토큰이 위 정규식의 W ID면 작업 ID이고, `design`·`implement` 같은 단계명이면 기존 PHASE 판정이다.
- **자연어 WORK + RESUME 판정**: Step 1·Step 2에서 RESUME이 판정되었으면 WORK를 **무시하고** 1줄 안내한다 — "재개는 state.md의 `work-id`로 작업 문맥을 복원합니다 — {ID} 지정 없이 이어서 진행합니다." ("W01 이어서 해줘"처럼 둘 다 성립하는 발화가 플래그 충돌로 중단되지 않게 한다.) 명시 플래그 `--work`는 이 양보 대상이 아니며 기존대로 충돌 에러를 낸다 — 사용자가 명시한 것을 조용히 버리지 않는다.

**Step 3: 프로젝트 기본값 적용**

일반 기능 요청은 모드를 `all`로 확정한다. 모델은 명시 플래그 > 자연어 > 이번 실행의 기존 결정 > config.json `modelProfile` > `standard` 순으로 정한다. 매 요청마다 모드·모델 프로파일 질문을 만들지 않는다. 적용 결과만 한 줄로 알리고 진행한다.

- **프로파일 질문 포함 규칙**: 사용자에게 선택을 요청했거나 설정·명시 지시가 충돌해서 실제 결정이 필요할 때만 묻는다. 설정된 `modelProfile`은 기본값으로 사용하며 재확인하지 않는다.
- **모드 질문 생략 규칙**: 일반 요청은 `all`. `--core` 또는 명시적 핵심 모드 요청이 있을 때만 `core`다. 자동으로 검증·설계 게이트를 줄이지 않는다.
- 이미 승인한 계획·handoff의 종료점과 명시 실행방법을 보존한다. 전체 모드는 implement Step 1.2에서 구체 계획 검토와 방법 선택을 한 질문으로 확인한다. core는 [core-planning.md](core-planning.md)에 따라 실제 코드 Read → 경량 plan.md → **AC+계획 실물 함께 승인 1회**에 방법도 연결한다. 유효한 동일 run/계획/선택은 재사용하고 방법만 빠졌으면 Step 1.3에서 방법만 묻는다. 미결정 방법을 기본값으로 채우지 않는다. plan/understand는 읽기 전용 경로로 보내고 실행 setup을 시작하지 않는다.
- 핵심 모드에서도 RGR·verify·G-W-T·긴급 보안 감사는 유지한다. 비TDD 개발 경로는 제공하지 않는다.
### 모드 판정 결과 기록

의도 파싱 결과를 state.md에 기록한다:
```yaml
mode: all | core
work-id: W01        # --work로 진입한 경우의 작업 ID (미사용 시 생략). phase-complete가 plan.md 행 매칭에 쓴다
model-profile: standard | eco
intent-source: flag | natural-language | user-selection
```

### 종료점 변경

기존 gx-tdd 실행(진행 중이거나 verify로 끝난 실행)의 저장 `stop-at`과 다른 종료점을 사용자가 명시하면("커밋만" → `commit`, "PR만"·"이어서 PR까지" → `pr`) 그 요청을 종료점 변경 결정으로 다룬다. 기본값·외부 문서로는 바꾸지 않는다. gx-work가 넘긴 `--resume --stop-at <값>`(verify로 끝난 실행은 `--phase complete --stop-at <값>`), PHASE 매핑의 커밋만·PR만, 이번 세션의 명시 발화가 이 절차를 시작한다.

1. 사용자 원문과 이전·새 종료점을 `${DEV_DIR}/decisions.md`에 기록한다. 같은 결정(같은 원문·같은 새 종료점)이 gx-work나 환경 감지 6의 기록으로 이미 있으면 다시 쓰지 않는다.
2. state의 `stop-at`을 새 값으로 갱신한다. `status: completed`였으면 SKILL.md 환경 감지 6대로 진행 상태로 되돌리고 verify부터 다시 통과한다.
3. gx-work 인계 실행(`handoff-file` 있음)이면 [계획 인계](plan-handoff.md)의 `reissue --stop-at <새 값> --change-source "<1의 근거>"`로 인계를 다시 발급하고 `validate-handoff`를 다시 통과한다. 재발급 뒤 state의 `handoff-file`·`entry-approved-source`·`entry-approved-scope-sha256`를 새 인계 값으로 갱신한다(다음 재개의 대조 기준). 직접 호출 실행은 이 단계가 없다.
4. `--phase complete`(커밋만·PR만) 또는 `--resume`으로 이어 간다. PR도 커밋 게이트를 거친다.

### 플래그 참조

- `--phase requirements|design|implement|review|complete`: 특정 Phase만 실행
- `--core`: 핵심 모드 (G-W-T AC → 코드 Read·경량 plan.md → AC+계획 함께 승인 → 승인된 순차 RGR → 인수·문서 대조·verify). commit/pr는 실제 요청한 경우만 추가한다.
- `--eco`: 에코 모드 — 에이전트 디스패치를 sonnet 중심으로 하향 (공유 규칙 "모델 프로파일" 참조)
- `--standard`: 표준 프로파일 강제 — config.json이 eco여도 이번 실행만 표준
- `--base <branch>`: 베이스 브랜치 지정
- `--status`: 현재 파이프라인 진행 상태 조회
- `--resume`: 이전 파이프라인 재개
- `--isolated`: 구현 단계를 red-writer→implementer 2석 디스패치로 실행 (기본은 red-writer 디스패치 + 세션 직접 구현). 모든 모드와 호환한다.

현재 세션/서브에이전트는 전체 모드 implement 1.2 또는 core 결합 승인에서 계획과 함께 실제 선택한다. 미선택이면 두 방법과 계획 문서 종료를 제시한다. 처음 명시한 방법은 보존하고 계획 검토만 확인한다. 1.3은 선택 검증·flags 반영과 빠진 방법만 보완한다. 문서 종료·미응답은 실행 승인이 아니며 RED/complete로 체이닝하지 않는다. 두 방법 모두 RED/리뷰 격리와 RGR을 유지한다.

ARGS[0]이 없고 모드도 판정되지 않으면 다음을 응답:
"구현할 기능이나 수정할 버그를 설명해주세요. 예: `/gx-tdd 로그인 기능 추가해줘`"

### --status 동작
`--status`가 지정되면 파이프라인을 실행하지 않고 현재 상태만 출력한다:

1. 현재 브랜치명에서 DEV_DIR을 계산하고 (`git branch --show-current` → `/`를 `-`로 치환 → `.dev/{branch-slug}/`), `${DEV_DIR}/state.md`를 탐색한다.
2. state.md가 없으면: "진행 중인 파이프라인이 없습니다." 출력 후 종료.
3. state.md가 있으면 다음을 출력:
   ```
   ## 파이프라인 상태
   - 작업: {args}
   - 브랜치: {branch} (base: {base})
   - 프로젝트: {project-type} ({project-root})
   - 현재 Phase: {phase} ({status})
   - 플래그: {flags}
   - 모델 프로파일: {model-profile} (필드가 없는 레거시 세션은 standard로 표시)
   - 시작: {started}

   ### Phase 진행
   - setup: {status}
   - requirements: {status}
   - ...
   ```
4. 출력 후 종료. 파이프라인을 시작하지 않는다.

## 플래그 충돌 검증

아래 충돌은 **이번 사용자가 명시한 플래그끼리만** 검사한다. 복원한 saved_flags를 현재 인자와 합치지 않는다. 저장 --core와 현재 단독 --phase는 충돌이 아니다.

- `--core`와 `--phase`는 **동시 사용 불가**. 둘 다 있으면: "`--core`와 `--phase`는 동시에 사용할 수 없습니다." 에러 후 중단.
- `--eco`와 `--standard`는 **동시 사용 불가**. 둘 다 있으면: "`--eco`와 `--standard`는 동시에 사용할 수 없습니다." 에러 후 중단.
- `--resume`과 `--phase`, `--core`, `--status`, `--eco`, `--standard`는 **동시 사용 불가**. 함께 있으면: "`--resume`은 다른 모드 플래그와 동시에 사용할 수 없습니다." 에러 후 중단 (재개는 state.md의 `model-profile`을 유지한다).
- `--resume`은 ARGS[0] 없이 단독 사용한다. ARGS[0]이 함께 있으면: "`--resume`은 작업 설명 없이 단독으로 사용합니다." 에러 후 중단.
- `--work`와 `--resume`은 **동시 사용 불가**. 함께 있으면: "`--work`와 `--resume`은 동시에 사용할 수 없습니다." 에러 후 중단 (재개는 state.md의 `work-id`에서 작업 문맥을 복원하므로 ID를 다시 받을 이유가 없다).
- `--isolated`는 모드 플래그와 호환하며 `--status`에서는 실행하지 않는다. 다만 명시 `session` 선택이나 기존/복원 method·flags와 모순이면 보고하고 실제 결정으로 해소한다. `--resume`에서 이번 플래그나 state를 조용히 우선해 충돌을 덮지 않는다. 유효한 같은 run·계획·선택이면 그대로 복원하며 재질문하지 않는다.

## 저장 모드와 단독 실행 범위

검증된 HANDOFF_READ_ONLY는 state 복원·초기화 없이 explore와 필요한 requirements/design의 계획 내용만 수행하고 종료한다. 그 밖의 기존 실행은 [core-planning.md](core-planning.md)의 **state 복원 → 요청 범위 결정 → PHASES 생성 → resume 커서 적용** 순서다. 명시 mode all/core가 우선하고 필드 부재만 restore_mode(None, saved_flags)로 독립 --core를 해석한다. 잘못된 명시 mode(null·빈 값 포함)는 거부한다.

현재 명시 requested_phase가 저장 requested-phase·execution-phases·과거 커서보다 우선한다. requirements/design은 [explore, 요청phase]이며 저장 core여도 PRD/설계 문서 경로다. mode를 all로 바꾸거나 구현까지 넓히지 않는다. 현재 명시 phase 없는 재개만 저장 범위(없으면 saved_flags의 --phase)·목록·커서를 복원해 완료한 setup/phase를 반복하지 않는다. 목록·커서 모순은 보고한다.

단독 implement는 [implement]다. core는 ac.md+plan.md의 실제 결합 승인·현재 지문, all은 PRD·설계·testability를 검사한다. core 단독 complete도 legacy mode를 정규화하고 승인 게이트를 먼저 수행한다. 보완은 필요한 계획·승인 Step만 수행하고 기존 RED/테스트/기준선을 보존한다. implement 이후 complete가 실제 후속 목록에 없을 때만 needs_boundary_regression(PHASES)의 전체 회귀를 적용한다. 미적용 core→all 실제 결정/pending은 mode·과거 커서보다 먼저 처리하고 applied 일반 재개는 새 전체 목록·현재 커서를 유지한다. 새 명시 phase는 과거 전이 목록보다 우선한다. 전환으로 원 gx-work 승인·run·stop-at를 넓히지 않는다.
