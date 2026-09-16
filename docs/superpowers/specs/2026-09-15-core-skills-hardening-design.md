# gx-context·gx-dev·gx-tdd 신뢰성 보강 설계

작성일: 2026-09-15
상태: 구현 계획 확정
기준 커밋: `5893c6c`

## 목표

`gx-context`가 문서에서 추출한 요구사항을 영속 원장으로 남기고, `gx-dev`·`gx-tdd`가 어느 하위 디렉터리와 부분 phase에서 시작하더라도 같은 프로젝트와 도메인 컨텍스트를 사용하게 한다. Claude Code와 Codex 질문 흐름은 각 하네스의 실제 스키마 범위 안에서 같은 결정을 기록한다. 동작 수정이 끝난 뒤 세 스킬의 긴 본문을 조건부 참조 파일로 나누어 이후 변경 시 드리프트를 줄인다.

## 범위와 분기

변경은 다음 다섯 배포 단위로 나눈다.

| 순서 | 브랜치 | 범위 | 선행 조건 |
|---|---|---|---|
| A | `feat/context-requirement-ledger` | 요구사항 원장 생산·병합, sync cursor, gx-context SVN 식별 | 기준 브랜치 |
| B | `fix/pipeline-bootstrap-contract` | phase 선행 조건, 프로젝트 루트, gx-dev·gx-tdd SVN 식별 | 기준 브랜치 |
| C | `fix/codex-question-contract` | 질문 개수·선택지·Other·Codex 변환 | A와 B 병합 |
| D | `refactor/skill-instruction-layout` | 조건부 참조 파일 분리 | C 병합 |
| E | `release/core-skills-hardening` | 충돌 확인, 버전·변경이력·전체 검증 | D 병합 |

A와 B는 수정 파일이 겹치지 않으므로 병렬 진행할 수 있다. SVN 식별은 A가 gx-context를, B가 gx-dev·gx-tdd를 소유하고 통합 검사에서 세 값을 대조한다. C는 세 스킬의 질문 절을 함께 바꾸므로 A와 B 뒤에서 진행한다. D는 앞 단계에서 확정한 문장을 파일 사이로 옮기므로 마지막 기능 변경 뒤에서만 진행한다.

## 공통 제약

- Claude Code와 Codex의 배포 경로는 모두 `.claude/skills/`이며, 새 참조 파일은 해당 디렉터리 아래에 둔다.
- `gx-dev`와 `gx-tdd`의 같은 계약은 한 PR에서 함께 수정한다.
- 문서 기반 스킬의 회귀 검사는 `test_codex_*.py` 이름으로 추가하여 기존 Windows·Linux `codex-contract` CI가 자동 수집하게 한다.
- 자동 검사는 문구 존재뿐 아니라 절 순서, 금지된 예시, 쌍둥이 파일의 값 일치까지 판정한다.
- 기능 브랜치 A~D에서는 버전 파일과 `CHANGELOG.md`를 수정하지 않는다. E에서 한 번만 `1.33.0`으로 올린다.
- 사용자 결정, verify, 보호 브랜치, 커밋·PR 게이트는 유지한다.
- `gx-tdd`의 RED → IMPLEMENT → VERIFY 순서와 Given-When-Then 형식은 변경하지 않는다.

## D1. 요구사항 원장 계약

### 정본 형식

`context/{도메인}/status.md`는 다음 표를 요구사항 원장으로 사용한다.

```markdown
| ID | 요구사항 | AC | 상태 | PR |
|---|---|---|---|---|
| FR-1 | 사용자는 이메일로 로그인할 수 있다 | - | ⬜ | - |
```

- `ID`: 입력 문서에 유효하고 중복되지 않은 `FR-N`·`NFR-N`이 있으면 유지한다. ID가 없거나 중복이면 유형별 현재 최댓값 다음 번호를 부여한다. 삭제된 번호는 재사용하지 않는다.
- `요구사항`: 후속 작업이 원문 없이도 범위를 판단할 수 있는 한 문장이다.
- `AC`: PRD가 연결되기 전 `-`, 연결 후 쉼표로 구분한 AC ID 목록이다.
- `상태`: `⬜`, `✅`, `🚫` 중 하나다. `🚫`는 승인된 문서 갱신에서 제거된 요구사항이다.
- `PR`: 구현 근거 URL 또는 커밋 해시다. 없으면 `-`다.

`context-docs.md`와 `gx-context` 템플릿이 이 표의 정본이다. `plan.md`의 `요구사항` 열은 이 ID를 참조하며 요구사항 상태를 직접 변경하지 않는다.

### `--from` 생산과 병합

문서 분석 C-2 직후 요구사항마다 정규화된 후보를 만든다. C-4에서 context 문서를 생성·갱신한 다음, C-5 작업계획을 만들기 전에 status 원장을 병합한다.

1. 기존 ID가 같으면 같은 행을 갱신한다.
2. ID가 없으면 공백·문장부호를 제거한 요구사항 핵심 문장을 비교한다.
3. 같은 항목이면 기존 ID·AC·상태·PR을 유지하고 요구사항 문장만 승인된 새 내용으로 갱신한다.
4. 새 항목이면 다음 번호로 `⬜` 행을 추가한다.
5. 기존 문서에서 사라진 `⬜` 항목은 제안 목록에 넣고 사용자가 제거를 승인한 경우에만 `🚫`로 바꾼다. `✅` 항목은 자동 폐기하지 않는다.
6. 병합이 끝난 원장의 ID를 C-5 계획의 요구사항 열에서 사용한다.

### sync cursor

`status.md` 끝에 다음 주석을 둔다.

```markdown
<!-- gx-sync
git-head: 0123456789abcdef0123456789abcdef01234567
svn-revision: -
pr-merged-at: 2026-09-15T00:00:00Z
-->
```

Git과 SVN 중 사용하지 않는 값은 `-`다. 첫 동기화는 각 pending ID를 전체 이력에서 정확히 검색하고 설명 키워드는 최근 100건에서 보조 검색한다. cursor가 있으면 Git은 `<git-head>..HEAD`, SVN은 `<svn-revision>:HEAD`, PR은 `merged:>=<pr-merged-at>` 범위를 사용한다. 사용자가 반영 또는 건너뛰기를 확정한 뒤에만 cursor를 현재 값으로 전진시킨다. 분석·명령 실패 시 cursor를 유지한다.

## D2. 파이프라인 부트스트랩 계약

### 프로젝트 루트

phase 실행 전에 다음 우선순위로 절대경로 `PROJECT_ROOT`를 결정한다.

1. Git 저장소이면 `git rev-parse --show-toplevel` 출력.
2. SVN 작업 복사본이면 `svn info --show-item wc-root` 출력.
3. 아직 VCS를 만들기 전이면 현재 디렉터리의 절대경로.

이후 `.claude/config.json`, `context/`, `.dev/`, 빌드·테스트, Git·SVN 명령은 모두 `PROJECT_ROOT` 기준으로 수행한다. 새 Git 저장소 생성을 승인받은 경우 `git init` 뒤 루트를 다시 계산한다.

### 부분 phase 확장

`--phase`는 다음 결정표로 PHASES를 만든다.

| 요청 | 실행 목록 |
|---|---|
| requirements | `setup, requirements` |
| design + PRD 없음 | `setup, requirements, design` |
| design + PRD 있음 | `setup, design` |
| implement | 환경 감지 후 `implement`; PRD나 설계가 없으면 현재 안내문으로 중단 |
| review | 환경 감지 후 `review` |
| complete | 환경 감지 후 `complete` |

requirements와 design은 새 산출물 디렉터리·브랜치·컨텍스트가 필요하므로 setup을 항상 포함한다. implement/review/complete는 기존 작업을 대상으로 하므로 경량 환경 감지를 유지한다.

### SVN 저장소 식별

세 스킬은 같은 값을 사용한다.

1. `svn info --show-item url`에서 작업 복사본 URL을 읽는다.
2. URL 끝의 `trunk`, `branches/<name>`, `tags/<name>`를 제거한다.
3. 남은 마지막 세그먼트를 `REPOSITORY_ID`로 사용한다.
4. 결과가 비거나 모호하면 `basename(PROJECT_ROOT)`를 사용한다.

`gx-context`의 PROJECTS.md 자동 등록, `gx-dev`·`gx-tdd`의 도메인 매칭이 모두 이 규칙을 쓴다.

## D3. 하네스 질문 계약

공통 최소 범위를 사용한다.

- 한 호출의 질문은 1~3개다.
- 질문 하나의 선택지는 2~3개다.
- 추천 선택지는 첫 번째이며 label 끝에 `(Recommended)`를 붙인다.
- UI가 제공하는 Other를 별도 option으로 만들지 않는다.
- 자유입력은 실제 후보 2개 또는 후보 1개와 `모르겠음`을 제시한다. 사용자는 UI의 Other로 직접 입력한다.
- Claude Code 예시는 `AskUserQuestion` 스키마를 유지한다.
- Codex 변환은 `multiSelect`를 제거하고 stable snake_case `id`를 추가하며 현재 세션의 실제 `request_user_input` 스키마가 문서보다 우선한다.
- 질문 도구를 사용할 수 없으면 자연어로 한 질문씩 묻고 실제 답을 기다린다.

`gx-dev/references/codex-runtime.md`가 Codex 변환의 정본이다. 각 스킬의 하네스 적응 절은 이를 링크하고, 직접 `Other로 입력` option을 포함하지 않는다.

## D4. 지시문 파일 경계

기능 동작을 바꾸지 않고 다음처럼 분리한다.

```text
.claude/skills/gx-context/
├── SKILL.md
└── modes/
    ├── create.md
    ├── from-document.md
    ├── update.md
    └── sync.md

.claude/skills/gx-dev/references/
├── intent-routing.md
├── pipeline-state.md
└── interaction-contract.md

.claude/skills/gx-tdd/references/
├── intent-routing.md
├── pipeline-state.md
└── interaction-contract.md
```

`SKILL.md`에는 frontmatter, 하네스 적응, 인자 파싱 진입점, 모드/phase 선택, 조건부 Read 순서, 핵심 안전 게이트만 남긴다. 이동한 파일은 SKILL.md의 위치를 기준으로 상대경로로 읽는다. `gx-dev`와 `gx-tdd`는 같은 이름의 참조 파일을 각자 보유해 독립적으로 읽히게 하고, 쌍둥이 계약은 maintenance notes와 자동 검사로 묶는다.

목표 상한은 `gx-context/SKILL.md` 320행, `gx-dev/SKILL.md` 520행, `gx-tdd/SKILL.md` 520행이다. 분리 전후의 헤딩 집합과 고정 계약 문구가 같아야 하며 새 기능을 함께 넣지 않는다.

## 수용 기준

1. 새 도메인 `--from` 실행 후 status.md에 추출 요구사항의 ID와 문장이 남고 plan.md가 같은 ID만 참조한다.
2. 기존 status.md를 갱신해도 완료 행의 ID·AC·상태·PR이 보존된다.
3. sync cursor 이후 20개가 넘는 커밋이 있어도 cursor 범위의 FR ID 커밋을 찾는다.
4. 저장소 하위 디렉터리에서 requirements/design을 실행해도 저장소 루트의 config/context/.dev를 사용한다.
5. dev와 tdd의 phase 결정표 및 SVN `REPOSITORY_ID`가 일치한다.
6. 정적 질문 예시에 명시적 Other option, 질문 4개 이상, 선택지 4개 이상이 없다.
7. Codex 변환 예시에 stable `id`가 있고 `multiSelect`가 없다.
8. 모듈화 전후 기존 36개 린트, 훅 테스트, Codex 테스트, 행동 테스트 mock이 모두 통과한다.

## 제외 범위

- status.md와 외부 이슈 트래커의 양방향 동기화
- 요구사항 자연어 유사도용 임베딩 또는 외부 데이터베이스
- gx-tdd의 RGR 알고리즘 변경
- 실제 Claude/Codex 질문 UI 구현 변경
- 기존 소비 프로젝트의 status.md 자동 마이그레이션 명령
