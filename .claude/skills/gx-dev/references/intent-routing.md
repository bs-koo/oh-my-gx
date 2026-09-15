> gx-dev/SKILL.md의 필수 참조 파일이다. 이 파일을 읽지 않고 관련 상태·질문·phase 결정을 추정하지 않는다. 상대경로는 gx-dev/SKILL.md 위치를 기준으로 해석한다.

## 인자

`ARGS[0]`에 자연어 요청을 받는다. 레거시 플래그도 호환한다.

### 의도 파싱

ARGS[0]을 받으면 아래 순서로 의도를 파싱한다:

**Step 1: 플래그 호환** (기존 사용자 보호)
- **`--work {ID}`는 다른 플래그보다 먼저 추출한다.** 아래 모드 플래그 분기에서 파싱이 종료되기 전에 소비해야 `--work --core`처럼 조합된 경우에도 작업 계획 참조가 유실되지 않는다. 추출 후 남은 인자로 아래 분기를 계속 판정한다.
- `--core`, `--phase`, `--base`, `--status`, `--resume`이 포함되면 해당 로직으로 실행.
- `--eco` 또는 `--standard`가 포함되면 **모델 프로파일 오버라이드**로 기록한다 (공유 규칙 "모델 프로파일" 참조). 프로파일 플래그는 모드 판정과 독립이므로, 나머지 플래그·자연어 파싱을 계속 진행한다.
- `--ralph`가 포함되면 **gx-ralph 전환 플래그**로 기록한다 (Step 2 "RALPH 우선순위 규칙"·Step 3 "모드 질문 생략 규칙" 참조). 전환 플래그는 모드 판정과 독립이므로 나머지 플래그·자연어 파싱을 계속 진행한다.
- `--work {ID}`가 포함되면 **작업 계획 참조 플래그**로 기록한다 — `.dev/plan.md`의 해당 행에서 도메인·요구사항·브랜치명을 확정한다 (phase-setup "작업 계획 참조" 절). ID는 `W` + 두 자리 숫자 형식이다(예: `W01`). 하이픈을 쓰지 않는 이유는 `config.json`의 `issueKey.pattern`(`^[A-Z]+-[0-9]+$`)에 매칭되면 브랜치명이 이슈 키로 오염되어 gx-commit의 타입 파싱이 깨지기 때문이다. 작업 계획 플래그는 모드 판정과 독립이므로 나머지 플래그·자연어 파싱을 계속 진행한다.
- 모드 관련 플래그가 없으면 Step 2로 진행한다 (`--eco`/`--standard`/`--ralph`만 있는 경우에도 Step 2의 자연어 판정을 계속한다).

**Step 2: 자연어 → 모드 판정**

먼저 아래 패턴으로 자동 판정을 시도한다:

| 감지 패턴 | 모드 | 예시 |
|-----------|------|------|
| `상태`, `진행`, `어디까지`, `현황` | STATUS | "지금 어디까지 됐어?" |
| `이어서`, `계속`, `재개`, `아까 하던` | RESUME | "아까 하던 작업 이어서 해줘" |
| `긴급`, `핫픽스`, `급한`, `빨리 고쳐`, `버그 수정만` | CORE | "로그인 버그 긴급 수정해줘" (AC를 재현 조건 관점으로 작성) |
| `구현만`, `핵심만`, `라이트`, `가볍게` | CORE | "알림 임계값 변경, 구현만 해줘" |
| `설계만`, `PRD만`, `리뷰만`, `커밋만` | PHASE(해당) | "설계만 해줘" |
| `{branch}에서`, `{branch} 기반`, `{branch} 브랜치` | BASE 추출 | "develop 브랜치 기반으로 작업해줘" |
| `에코 모드`, `에코로`, `절약 모드` | ECO 추출 (프로파일 — 모드와 독립) | "에코로 알림 기능 개발해줘" |
| `랄프로`, `ralph로`, `무인 루프로` | RALPH 추출 (gx-ralph 전환 플래그 — 프로파일과 독립) | "랄프로 알림 기능 개발해줘" |
| `W00`~`W99` 형태의 토큰 | WORK 추출 (작업 계획 참조 — 모드와 독립) | "W01 시작해줘", "phase W01 개발해줘" |

PHASE 매핑: `PRD만`/`요구사항만` → `--phase requirements`, `설계만` → `--phase design`, `리뷰만` → `--phase review`, `커밋만`/`PR만` → `--phase complete`. implement phase 단독 실행은 자연어 매핑 없이 `--phase implement` 플래그 전용이다 (자연어 "구현만"은 CORE로 라우팅 — 설계서 기반 구현 단독 실행과 의도가 다르다).

BASE 추출: `{branch}에서`, `{branch} 기반`, `{branch} 브랜치`에서 branch명을 추출하여 `--base`로 처리한다. BASE 추출은 모드 판정과 독립적이다 — BASE가 추출되어도 모드가 결정되지 않으면 Step 3으로 진행한다.

ECO 추출: ARGS[0]에 `에코 모드`/`에코로`/`절약 모드`가 포함되면 모델 프로파일을 `eco`로 기록한다 (`--eco`와 동일. 단독 명사 `에코`는 도메인 용어 오탐 방지를 위해 매칭하지 않는다 — 예: "에코머니 적립 기능"). 프로파일 추출도 모드 판정과 독립적이다 — 모드가 결정되지 않으면 Step 3으로 진행한다.

RALPH 추출: ARGS[0]에 `랄프로`/`ralph로`/`무인 루프로`가 포함되면 gx-ralph 전환 플래그를 기록한다 (`--ralph`와 동일. 단독 명사 `랄프`/`ralph`/`루프 돌려`는 gx-ralph 스킬 직접 호출 트리거와 충돌하므로, 일반 부사 `무인으로`는 도메인 문장 오탐 방지를 위해 — 예: "무인으로 운영되는 매장 재고 기능" — 매칭하지 않는다).

**WORK 추출 규칙** (오탐 방지가 핵심이다):

- 요청에서 `W` + 두 자리 숫자 토큰(`W01`·`W12`)을 찾는다. 앞뒤가 단어 경계여야 한다.
- **토큰을 찾았다고 바로 작업 참조로 단정하지 않는다.** `.dev/plan.md`가 존재하고 그 표에 **같은 ID의 행이 실제로 있을 때만** 작업 참조로 확정한다. 화면 코드·버전 표기 등 우연히 형태가 겹치는 경우를 걸러내기 위함이다.
- 계획 파일이 없거나 행이 없으면 **추출하지 않고** 그 토큰을 일반 요청 문구의 일부로 남긴다. 사용자에게 되묻지 않는다 — 계획이 없는 프로젝트에서 `W01`은 그냥 단어다.
- 확정되면 `--work {ID}`를 명시한 것과 동일하게 처리한다 (phase-setup "작업 계획 참조" 절).
- `phase W01`처럼 앞에 `phase`가 붙어도 같다. 뒤따르는 토큰이 두 자리 숫자를 가진 `W` 토큰이면 작업 ID이고, `design`·`implement` 같은 단계명이면 기존 PHASE 판정이다.
- **자연어 WORK + RESUME 판정**: Step 1·Step 2에서 RESUME이 판정되었으면 WORK를 **무시하고** 1줄 안내한다 — "재개는 state.md의 `work-id`로 작업 문맥을 복원합니다 — {ID} 지정 없이 이어서 진행합니다." ("W01 이어서 해줘"처럼 둘 다 성립하는 발화가 플래그 충돌로 중단되지 않게 한다.) 명시 플래그 `--work`는 이 양보 대상이 아니며 기존대로 충돌 에러를 낸다 — 사용자가 명시한 것을 조용히 버리지 않는다. RALPH 우선순위 규칙과 같은 구조다.

**RALPH 우선순위 규칙** (출처에 따라 다르다 — 명시 플래그는 조용히 버리지 않는다):
- **svn 우선 배제**: `.claude/config.json`의 `vcs`가 `svn`이면 출처와 무관하게 RALPH를 무시하고 1줄 안내한다 — "gx-ralph는 SVN 미지원입니다 — 진행 방식을 확인합니다." 이후 Step 3의 모드 질문을 정상 제시한다 (phase-setup Step 7의 svn 처리는 이 규칙의 2차 방어. config.json은 정적 파일이라 이 시점에 읽을 수 있다).
- **자연어 RALPH + 선판정 모드**: Step 1·Step 2에서 STATUS/RESUME/CORE/PHASE 중 하나가 **이미 판정되었으면 RALPH를 무시**하고 1줄 안내한다 — "`랄프로`는 전체 모드 신규 실행에서만 유효합니다 — {판정된 모드}로 진행합니다." (예: "랄프로 이어서 해줘" → RESUME, "랄프로 긴급 수정해줘" → CORE).
- **플래그 `--ralph` + 자연어 모드 트리거**: Step 2 자연어가 STATUS/RESUME/CORE/PHASE를 판정하면 **플래그 충돌과 동일하게 에러 후 중단**한다 — "`--ralph`는 전체 모드 전용입니다 — 요청의 '{매칭 키워드}'가 {판정된 모드}를 요구합니다. 플래그를 빼거나 문구를 바꿔주세요." (`--ralph --core`가 에러인데 `--ralph 빨리 고쳐`만 조용히 core로 가면 심각도가 어긋난다.)
- 위에 걸리지 않고 모드가 미결정이면 Step 3으로 진행한다 — 거기서 RALPH가 모드를 확정한다.

**Step 3: 모드·프로파일 확인 (위 패턴에 해당하지 않는 경우)**

위 자동 판정 패턴에서 모드(STATUS/RESUME/CORE/PHASE)가 결정되지 않으면 — 즉, 일반적인 기능 요청이면 — **반드시** AskUserQuestion으로 모드를 확인한다 (예외: RALPH가 추출된 경우 — 아래 "모드 질문 생략 규칙"). 오케스트레이터가 임의로 모드를 판정하지 않는다. 모델 프로파일이 미확정이면(플래그·자연어 없음) **같은 호출의 두 번째 질문**으로 함께 묻는다 — 한 번의 submit으로 두 축이 함께 결정된다.

```
AskUserQuestion(
  questions: [
    {
      question: "어떤 방식으로 진행할까요? (요청: {ARGS[0]})",
      header: "진행 방식",
      options: [
        { label: "전체 과정 진행", description: "PRD → 설계 → 구현 → 리뷰 → PR" },
        { label: "핵심 과정만 진행", description: "AC 확인 → 구현 → 빌드·테스트 게이트 → 기록 → PR. 소형 변경용 — 산출물(ac.md·summary.md)은 남긴다" }
      ],
      multiSelect: false
    },
    {
      question: "모델 프로파일을 선택해주세요. 절차·게이트는 동일하고 에이전트 모델 수준만 달라집니다.",
      header: "모델 프로파일",
      options: [
        { label: "표준", description: "설계·비판 검토·구현에 opus — 품질 우선 (Max 요금제 권장)" },
        { label: "에코", description: "architect 외 opus 에이전트를 sonnet으로 하향 — 토큰 절약 (Pro 요금제 권장, 게이트 동일)" }
      ],
      multiSelect: false
    }
  ]
)
```

- **프로파일 질문 포함 규칙**: `--eco`/`--standard` 플래그나 자연어(`에코 모드`/`에코로`/`절약 모드`)로 이미 확정됐으면 두 번째 질문을 **생략**한다 (모드 질문만 제시). config.json `modelProfile`이 설정되어 있으면 해당 옵션을 **첫 번째에 배치**하고 label 끝에 `(현재 설정)`을 붙인다 — 이 질문의 답변이 이번 실행의 최종 결정이다.
- **모드 질문 생략 규칙**: 모드가 미결정이고 RALPH가 추출된 상태이면 **모드를 `all`로 확정하고 모드 질문을 생략**한다 — 무인 루프는 PRD가 필수(gx-ralph Step 1-4)라 core와 양립하지 않으므로 선택지가 하나뿐이다. 프로파일이 미확정이면 프로파일 질문만 단독으로 제시한다. `intent-source`는 `flag` 또는 `natural-language`로 기록한다.
- "전체 과정 진행" 선택 → 전체 모드(all) (전체 Phase 실행)
- "핵심 과정만 진행" 선택 → 핵심 모드(core): setup → core → complete (설계/정식 리뷰 생략, 기록·Mechanical Gate·커밋/PR은 유지)
- "표준"/"에코" 선택 → `MODEL_PROFILE`로 확정 (phase-setup Step 1.5가 결정을 확정하고, Step 7이 state.md `model-profile`에 기록)

### 모드 판정 결과 기록

의도 파싱 결과를 state.md에 기록한다:
```yaml
mode: all | core
work-id: W01        # --work로 진입한 경우의 작업 ID (미사용 시 생략). phase-complete가 plan.md 행 매칭에 쓴다
model-profile: standard | eco
intent-source: flag | natural-language | user-selection
```

### 플래그 참조

- `--phase requirements|design|implement|review|complete`: 특정 Phase만 실행
- `--core`: 핵심 모드 (AC 확인 → 구현 → Gate → 기록 → PR)
- `--eco`: 에코 모드 — 에이전트 디스패치를 sonnet 중심으로 하향 (공유 규칙 "모델 프로파일" 참조)
- `--standard`: 표준 프로파일 강제 — config.json이 eco여도 이번 실행만 표준
- `--base <branch>`: 베이스 브랜치 지정
- `--status`: 현재 파이프라인 진행 상태 조회
- `--resume`: 이전 파이프라인 재개
- `--ralph`: 전체 모드 implement 진입 시 gx-ralph(무인 루프)로 전환 — 자연어 `랄프로`와 동일. `--core`·`--phase`·`--resume`·`--status`와 동시 사용 불가(에러), 자연어 모드 트리거(`긴급`·`구현만` 등)와 충돌해도 에러. svn 프로젝트에서는 무시하고 안내 (RALPH 우선순위 규칙)

ARGS[0]이 없고 모드도 판정되지 않으면 다음을 응답:
"구현할 기능이나 수정할 버그를 설명해주세요. 예: `/gx-dev 로그인 기능 추가해줘`"

### --status 동작
`--status`가 지정되면 파이프라인을 실행하지 않고 현재 상태만 출력한다:

1. phase-setup의 Step 0과 동일한 방식으로 `.dev/*/state.md`를 Glob으로 탐색한다.
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

- `--core`와 `--phase`는 **동시 사용 불가**. 둘 다 있으면: "`--core`와 `--phase`는 동시에 사용할 수 없습니다." 에러 후 중단.
- `--eco`와 `--standard`는 **동시 사용 불가**. 둘 다 있으면: "`--eco`와 `--standard`는 동시에 사용할 수 없습니다." 에러 후 중단.
- `--resume`과 `--phase`, `--core`, `--status`, `--eco`, `--standard`는 **동시 사용 불가**. 함께 있으면: "`--resume`은 다른 모드 플래그와 동시에 사용할 수 없습니다." 에러 후 중단 (재개는 state.md의 `model-profile`을 유지한다).
- `--resume`은 ARGS[0] 없이 단독 사용한다. ARGS[0]이 함께 있으면: "`--resume`은 작업 설명 없이 단독으로 사용합니다." 에러 후 중단.
- `--ralph`와 `--core`, `--phase`, `--resume`, `--status`는 **동시 사용 불가**. 함께 있으면: "`--ralph`는 전체 모드 전용입니다 — `--core`/`--phase`/`--resume`/`--status`와 함께 쓸 수 없습니다." 에러 후 중단.
- `--work`와 `--resume`은 **동시 사용 불가**. 함께 있으면: "`--work`와 `--resume`은 동시에 사용할 수 없습니다." 에러 후 중단 (재개는 state.md의 `work-id`에서 작업 문맥을 복원하므로 ID를 다시 받을 이유가 없다).

## Phase 선택 (--phase 플래그)

`--phase` 실행 목록:
- `--phase requirements`: `[setup, requirements]`를 실행하여 작업환경과 도메인 컨텍스트를 확정한 뒤 PRD를 작성한다.
- `--phase design`: `[setup, design]`을 실행한다. setup 후 `${DEV_DIR}/prd.md`가 없으면 게이트가 requirements를 먼저 실행한다.
- `--phase implement`: 환경 감지 + implement 실행. 대화 맥락에 설계서가 없고 `${DEV_DIR}/design.md`도 없으면: "설계서가 필요합니다. `/gx-dev --phase design`을 먼저 실행하거나 설계 내용을 입력해주세요." 후 중단.
- `--phase review`: 환경·베이스 브랜치 감지 후 현재 변경사항을 리뷰한다. **결과 보고로 종료하고 phase-complete로 체이닝하지 않는다** (`--phase complete` 별도 실행). 종료 시 이번 실행에서 만든 골격 state.md는 `status: completed`로 갱신한다.
- `--phase complete`: 환경 감지 + 베이스 브랜치 감지 + complete 실행 (test, commit, PR).

> **환경 감지**: 위 3개 모드는 phase-setup을 건너뛰므로, Phase 진입 전에 다음을 수행한다:
> 1. `PROJECT_ROOT` = phase-setup과 같은 우선순위의 절대경로. 이후 config, `.dev`, context, VCS·빌드·테스트 명령은 이 경로를 기준으로 수행한다.
> 2. `${PROJECT_ROOT}/.claude/config.json`의 `vcs`를 읽고(부재·파싱 실패 시 git), **git**은 `git rev-parse --is-inside-work-tree`, **svn**은 `svn info`로 작업 복사본을 확인한다.
> 3. `MODEL_PROFILE` 결정: `${PROJECT_ROOT}/.dev/{branch-slug}/state.md`에 `model-profile` 필드가 있으면 그 값을 사용하고, 없으면 플래그(`--eco`/`--standard`) > config.json `modelProfile` > `standard` 순으로 결정한다 (phase-setup Step 1.5와 동일 규칙 — eco 디스패치 오버라이드가 이 값에 의존하므로 생략하지 않는다).
> 4. `--work {ID}`가 지정되었으면 `${PROJECT_ROOT}/.dev/{branch-slug}/state.md`에 `work-id: {ID}`를 기록한다 (파일이 없으면 이 항목만으로 만들지 않는다). 이 경로는 phase-setup을 건너뛰어 3.0.5가 실행되지 않으므로, 기록하지 않으면 **지정한 ID가 조용히 무시되고** phase-complete Step 3.5가 `작업 위치` 열로만 행을 찾는다 — 브랜치가 계획에 없으면 아무 일도 일어나지 않는다.

---
