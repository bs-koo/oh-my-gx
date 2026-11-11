---
name: gx-work
description: 기능 구현·버그 수정·PR까지 개발·진행 중 작업 이어서·'W01 시작'·계획만·구조 파악 요청의 기본 진입점이다. 의도와 진행 상태를 확인해 조사·문서 정리(gx-context)·TDD 개발(gx-tdd)·커밋/PR을 필요한 만큼만 연결하고, 실제 응답을 받은 뒤 다음 단계로 넘어간다. TDD를 명시한 요청은 gx-tdd가 직접 받는다.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill]
---

# GX Work — 작업 진입과 연결

사용자의 목표·범위·종료점과 현재 진행 상태를 파악해 **필요한 스킬 수행 → 결과와 다음 단계 제안 → 실제 결정 → 후속 작업**을 연결한다. 개발 실행은 gx-tdd가 맡으며 이 스킬은 고정 준비 파이프라인이나 두 번째 구현 루프를 만들지 않는다. 한국어로 응답한다.

**하네스 적응**: Claude Code는 `Skill("oh-my-gx:...")`와 `AskUserQuestion`을 쓴다. Codex는 이 파일 위치 기준 [references/codex-runtime.md](references/codex-runtime.md)를 먼저 읽고 대상 스킬의 설치된 `SKILL.md` 절차와 게이트를 그대로 수행한다. 도구 이름·모델은 현재 스키마를 따르고, 소비 프로젝트에 `.claude/rules/`가 있다고 가정하지 않는다.

- **플러그인 루트**: 이 SKILL.md가 있는 디렉토리 기준 `../../..`이다. 그 루트에 `scripts/gx-work.py`가 있는지 확인한 뒤 helper를 실행한다. Codex는 codex-runtime의 설치 루트 확인을 따른다. 소비 프로젝트의 `scripts/`나 개발 저장소 경로로 대신하지 않는다.
- **실행 파일·인코딩**: Windows PowerShell은 `python`, POSIX는 `python3`를 쓴다. 파일은 BOM 없는 UTF-8로 읽고 쓰며 PowerShell 읽기는 `Get-Content -Encoding UTF8`이다.

## 진행 순서

1. **요청 보존** — 원문 목표·제공 문서·제외 범위·요청한 종료점과 대화의 결정·부정·제한을 그대로 둔다. 단어 하나로 라우팅하지 않으며, 같은 run·범위에서 이미 답한 선택은 다시 묻지 않는다. 결과에 영향을 주는 미정·충돌만 묻는다.
2. **의도 분류** — 아래 **의도별 처리** 표로 의도와 종료점을 정한다. 이해·계획·상태만이면 읽기 전용으로 끝낸다.
3. **상태 확인(읽기 전용)** — 프로젝트 지침을 읽고 분류한 의도로 `route`를 실행해 진행 상태·잠금·미응답 질문을 확인한다. 결과는 아래 **route 결과별 처리**를 따른다. 잠금·프로세스·기록은 바꾸지 않는다.
4. **필요한 근거만 준비** — [작업 총괄 계약](references/tdd-entry.md)의 스킬 표에서 지금 부족한 근거에 맞는 스킬만 쓴다. 모든 스킬을 돌거나 결과를 개발로 자동 확장하지 않는다.
5. **결과와 다음 단계 제시** — [판단과 검증 전달](references/reviewability.md)에 따라 근거·불확실성·추천 다음 단계를 짧게 보여준다. 새 질문 단계나 일괄 퀴즈를 만들지 않는다.
6. **진입 질문** — 다음 단계가 개발이면 tdd-entry.md의 진입 질문(진입·종료점·모드·프로파일, 요청·설정에서 정한 항목은 뺀다)을 한 번에 묻고 실제 답을 기다린다. 답 전에는 gx-tdd 호출·브랜치/worktree·빌드·테스트·코드·커밋을 시작하지 않는다.
7. **인계** — 실제 진입 답변 뒤 [references/handoff.md](references/handoff.md)로 인계 파일을 만들고 `validate-handoff`가 `ready-for-tdd: true`일 때만 넘긴다. 원문·계획 본문을 프롬프트로 복사하지 않고 파일 포인터와 관련 ID만 전달한다.

`Skill("oh-my-gx:gx-tdd", args="<원래 목표> --handoff <인계.json>")`

기존 정규화 구현계획이 있을 때만 `--from-plan <계획.json>`을 더한다([references/planning.md](references/planning.md)). gx-tdd는 인계받은 목표 문장으로 모드를 다시 판정하지 않으므로, 요청에서 밝혔거나 진입 질문에서 답한(설정값으로 정한 것 포함) 모델 프로파일은 요청 파일의 `model-profile`, 모드는 `mode`로 넘기고(기존 계획 인계는 `handoff --mode`·`--model-profile`, 인계 지문에 묶인다. gx-tdd는 `mode: core`를 `--core`와 같게 본다), 베이스 브랜치는 `--base <브랜치>` 플래그로 붙인다(SVN 새 slug는 `--slug <새 slug>`). `--from-plan`은 문서 경로를 가져올 뿐 승인 표시가 아니다. Codex는 같은 인자·파일 포인터로 설치된 gx-tdd 절차를 실행한다. PRD·설계·T태스크 구현계획과 실행 방식(`session`/`subagents`) 선택은 gx-tdd가 소유하며 여기서 미리 작성하지 않는다. 직접 gx-tdd 독립 호출과 기존 state·pending·verify·보호 브랜치·커밋/PR 게이트는 그대로 유지된다.

## 의도별 처리

| 사용자 목표 | 처리 | 종료점 |
|---|---|---|
| 프로젝트·도메인 구조 파악, 원인 조사, 상태 조회 | 관련 코드·context·문서를 읽고 근거와 불확실성을 보고한다 | `understand` |
| 계획/설계만, 외부 계획 검토 | [planning.md](references/planning.md)의 필드로 계획을 대화에 제시한다. 파일·인계·질문 기록을 만들지 않는다. PRD·설계 문서 저장을 원할 때만 tdd-entry.md의 계획 전용 질문 후 gx-tdd 읽기 전용 인계 | `plan` |
| 기능 구현·버그 수정 | 근거 정리 → 진입 질문 → gx-tdd 인계 | 요청·설정·진입 질문으로 정한 값(추천 `pr`, SVN은 `verify`) |
| 작업 ID 지정(`W03 시작`) | `.dev/plan.md`에 같은 행이 있을 때만 작업 참조. tdd-entry.md의 W 착수 확인 후 진입 질문 | 위와 같음 |
| 지금 할 수 있는 작업 | tdd-entry.md의 준비된 W 조회(읽기 전용) | `understand` |
| 진행 중 작업 이어서 | route `resume`의 run-id·목표·종료점·step으로 gx-tdd `--resume` | 저장된 종료점 |
| 컨텍스트·용어·요구사항 정리, 진행 상태 동기화 | `oh-my-gx:gx-context`로 연결하고 그 결과에서 끝낸다 | `plan` |
| 요구사항 정리 후 개발까지 | gx-context로 원장·계획을 반영한 뒤 같은 run으로 진입 질문 → 인계 | 요청한 종료점 |
| 리뷰만 | 진행 중 gx-tdd 실행이면 `Skill("oh-my-gx:gx-tdd", args="--phase review")`, 완료된 구현의 교차 검토는 `oh-my-gx:gx-cross-review` | 리뷰 결과 |
| 커밋만·PR만 | route `--intent status`의 `state-file`로 현재 브랜치의 gx-tdd 실행 기록을 확인한다. 진행 중이면 아래 **지금 상태 커밋**인지 먼저 확인한다. 진행 중이거나 verify로 끝난 실행이면 아래 **종료점 변경**으로 재검증 뒤 진행한다. gx-tdd 실행 기록이 없으면 gx-commit·gx-pull-request 게이트만 수행(PR은 커밋 성공 뒤) | 요청한 결과 |

이해·계획·상태만 요청하면 **stash, checkout, pull, 브랜치/worktree 생성, gx-setup, 빌드·테스트를 실행하지 않는다**. 저장 요청이 없으면 계획·질문·state 파일도 만들지 않는다. gx-setup은 자동 호출하지 않고 실제 누락이 실행을 막을 때만(route `setup-required`) `/oh-my-gx:gx-setup` 실행을 안내한다.

명시적 무인 반복 실행 요청(`--ralph`·`랄프로` 등)은 [지원 중단 규약](../gx-tdd/references/intent-routing.md#제거된-무인-반복-경로--실행-전-중단)에 따라 먼저 멈추고 일반 개발이나 커밋으로 조용히 대체하지 않는다. 설명·제거 요청·파일명·인용은 실행 명령으로 보지 않는다.

## route 결과별 처리

`python <플러그인 루트>/scripts/gx-work.py route --project-root <프로젝트 루트> --intent <understand|plan|status|implement|resume> [--stop-at <종료점>] --goal "<원문 목표>" [--git-safe-directory <프로젝트 루트>] [--slug <SVN 작업 slug>]`로 판정한다(프로젝트 루트 규칙은 handoff.md). Codex 샌드박스처럼 git 소유권 불일치가 나는 환경에서만 확인된 프로젝트 루트를 `--git-safe-directory`로 넘긴다. 결과의 `requested-stop-at`은 이번 요청의 종료점이다. exit 2의 `{"error": ...}`(git 오류·입력 오류)는 상태 없음으로 넘기지 않고 내용을 그대로 보여준 뒤 멈춘다. 모든 결과의 `notices`(무시한 설정값, 새 판 설치 등)는 그대로 한 줄씩 보여준다. `defaults`(config `workflowDefaults`)의 항목은 진입 질문에서 빼고 "설정값으로 진행: …" 한 줄로 알린다. `configured-model-profile`(최상위 `modelProfile`)은 답이 아니며 프로파일 질문의 "(현재 설정)" 표시·추천값으로만 쓴다(tdd-entry.md).

| `action` | 뜻 | 처리 |
|---|---|---|
| `understand`·`plan`·`status` | 읽기 전용 요청 | 진행 중 실행이 있어도 읽기만 하고 보고 후 종료 |
| `implement` | 이어갈 실행 없음 | 근거 준비 → 진입 질문 → 인계 |
| `setup-required` | 설정 파일·프로젝트 타입이 없어 실행할 수 없음 | 진입 질문 전에 `reason`을 보여주고 멈춘다. 사용자가 `/oh-my-gx:gx-setup`을 실행한 뒤 같은 요청을 다시 하도록 안내한다(`Skill` 호출 금지) |
| `resume-elsewhere` | 다른 브랜치·워크트리에 진행 중 실행이 있음(브랜치가 로컬·원격 추적 ref에 남은 것만) | `elsewhere-candidates`(브랜치·W·중단 step)를 보여주고 `그 위치에서 이어서` / `새 작업으로 시작`을 묻는다. 이어서를 고르면 후보의 `worktree` 경로(없으면 `git switch <branch>`)와 그 위치의 `/oh-my-gx:gx-work 이어서`를 안내한다. 전환은 사용자가 고를 때만 안내하고 helper는 바꾸지 않는다. 새 작업이면 `setup-reason`이 있으면 `setup-required`처럼 멈추고, 없으면 route를 다시 부르지 않고 `implement`처럼 진행한다 |
| `resume` | 같은 목표의 gx-tdd 실행이 진행 중 | `run-id`·`goal`·`stop-at`·`state-file`을 복원해 `Skill("oh-my-gx:gx-tdd", args="--resume")`. 새 run을 만들지 않는다. `requested-stop-at`이 저장값과 다르면 **종료점 변경** |
| `no-active-run` | 이어서 할 실행이 없음 | 이어갈 대상이 없음을 알리고 새 작업으로 시작할지 묻는다 |
| `scope-review-required` | 진행 중 실행과 목표가 다름 | 두 목표를 합치지 않고 `기존 작업 이어서` / `별도 작업으로 시작`을 묻는다. 별도면 **새 범위로 시작** |
| `awaiting-decision` | 답하지 않은 질문이 있음 | **미응답 질문 대조** |
| `resume-selection-required` | SVN 활성 포인터 없이 후보가 여럿 | 후보만 보여주고 선택을 받는다. 선택 전에는 읽기·질문만, 선택 뒤 포인터를 복원해 다시 판정한다(handoff.md) |
| `migration-required` | 진행 중 gx-ralph·구버전 flags·gx-dev 실행 | 기록 경로만 안내하고 실행하지 않는다. **새 범위로 시작** |
| `loop-active` | `ralph.lock`이 있음 | 잠금·프로세스를 건드리지 않고 새 실행을 막는다 |
| `unsupported-request` | 제거된 무인 반복 실행 요청 | 지원 중단을 알리고 다른 실행으로 대체하지 않는다 |
| `detached-head` | 브랜치가 없는 HEAD | 읽기 전용 보고만 한다. 체크아웃·브랜치 생성은 사용자가 정한다 |

`stale-pending-file`·`stale-answered-file`은 완료된 실행에 남은 질문·답변 기록이다. 알리기만 하고 질문 대기나 재사용 근거로 다루지 않는다. 어느 결과든 `detached-head: true`가 붙으면 브랜치 없는 HEAD라는 뜻이므로 실행 setup으로 넘어가지 않는다. `stop-at-change-required: true`면 같은 실행의 저장 종료점과 이번 요청이 다르므로 **종료점 변경**으로 간다(저장값은 helper가 바꾸지 않는다). `entry-answer-recorded: true`면 같은 목표의 진입 질문 답이 이미 기록돼 있다. `answered-run-id`가 이번 대화의 run-id와 같고 `answered-selection`의 첫 답이 `gx-tdd로 진행`일 때만(이때 `requires-user-decision: false`) 다시 묻지 않는다. 다른 선택이면 그 선택을 따르고, 이전 세션의 기록이면 기록된 답을 보여주고 다시 확인한다. `answered-question-set-id`의 decisions.md 기록을 읽어 `gx-tdd로 진행`이면 같은 run-id·question-set-id로 인계하고, 다른 선택이면 그 선택을 따른다. Codex 분할 질문의 둘째 세트 답은 `answered-choices`(예: `{"mode": "core"}`)로 오며 다시 묻지 않고 요청 파일에 싣는다. `entry-followup-missing`이 있으면(`requires-user-decision: true`) 진입 답은 다시 묻지 않고, 그 목록에서 요청에서 이미 밝힌 항목과 핵심 모드의 프로파일을 뺀 나머지만 둘째 세트로 묻는다. 남는 것이 없으면 묻지 않고 인계한다.

## 진행 중 실행의 변경

- **미응답 질문 대조**: `pending-goal`·`pending-run-id`·`pending-phase`를 이번 요청과 대조한다. 같은 작업이면 원래 질문을 다시 보여주고 실제 답을 원래 phase에 기록해 잇는다. 다른 작업이면 `이전 질문에 답하기` / `폐기하고 새 작업`을 묻는다. 폐기는 실제 답을 근거로 `python <플러그인 루트>/scripts/codex-question.py discard --cwd <프로젝트 루트> --dev-dir <질문의 .dev/slug> --reason "<실제 사용자 결정 근거>"`가 exit 0일 때만 인정하고 route를 다시 판정한다. 형식이 깨진 pending도 원문을 보관하고 해제한다(결과 `malformed: true`). exit 2(lock, pending 없음, `--reason` 누락·빈 값)면 멈추고 보고한다. 질문 파일을 직접 지우지 않는다.
- **종료점 변경**: 진행 중이거나 verify로 끝난 gx-tdd 실행에 저장된 `stop-at`과 다른 종료점을 명시하면("이어서 PR까지", "커밋만", "PR만") 그 요청을 종료점 변경 결정으로 다룬다. 정본은 gx-tdd [intent-routing의 종료점 변경](../gx-tdd/references/intent-routing.md#종료점-변경)이다. 원문 근거를 state 디렉토리의 `decisions.md`에 기록한 뒤 gx-tdd에 `--resume --stop-at <새 종료점>`(verify로 끝난 실행은 `--phase complete --stop-at <새 종료점>`)으로 넘기면, gx-tdd가 state `stop-at` 갱신, 완료 실행의 진행 상태 복귀와 verify 재통과, gx-work 인계의 `reissue --stop-at <새 종료점> --change-source "<근거>"`, state 승인 지문 갱신을 순서대로 한다. 기본값·외부 문서로 종료점을 넓히지 않는다.
- **지금 상태 커밋**: 진행 중 실행에 "지금까지 한 거 커밋만"처럼 말하면 `지금 상태 그대로 커밋`(파이프라인 일시 중지, verify 미통과 커밋) / `검증까지 마치고 커밋`(위 종료점 변경)을 한 번 묻는다. 전자는 state를 `in_progress`로 둔 채 `oh-my-gx:gx-commit`을 호출하고, 이 실제 응답을 위험 수용으로 넘겨 gx-commit이 다시 묻지 않는다(verify 경고·기록은 그대로). 커밋 뒤 "이어서"로 재개한다. Codex는 위험 수용으로 verify를 우회하지 않으므로 전자를 내지 않고 검증 후 커밋만 안내한다. 작업 취소를 그 대안으로 권하지 않는다.
- **프로파일·모드 변경**: "에코로 바꿔서 이어가"·"표준으로"는 재개와 프로파일 변경이다. gx-tdd에 `--resume --eco`(또는 `--standard`)로 넘기면 남은 디스패치부터 적용한다. "전체 모드로 해줘"(핵심→전체)와 설계 전의 "핵심으로 해줘"(전체→핵심)는 원문을 state 디렉토리 `decisions.md`에 기록하고 `--resume`으로 넘긴다. 정본은 gx-tdd [진행 중 실행의 선택 변경](../gx-tdd/references/intent-routing.md#진행-중-실행의-선택-변경)이며 인계는 다시 발급하지 않는다.
- **작업 취소**: "이 작업 그만둘래"는 `작업 취소` / `계속 진행`을 묻고 실제 답이 취소일 때만 `python <플러그인 루트>/scripts/gx-work.py cancel --project-root <프로젝트 루트> --reason "<실제 사용자 응답 근거>" [--run-id <run-id>]`를 실행한다. exit 0이면 state가 `status: cancelled`가 되고 취소 근거가 같은 디렉토리 `decisions.md`에 남는다. 작업을 그만두는 선택으로만 설명하고 verify를 피하는 방법으로 권하지 않는다(취소 뒤 커밋·PR은 "verify 미통과(취소된 TDD 작업)"로 표기된다). exit 2(진행 중 실행 없음·gx-tdd 외·Ralph 기록·잠금·run-id 불일치 등)는 내용을 보여주고 멈춘다. 추천·무응답·헤드리스 판단으로 부르지 않는다. 다시 열기는 gx-tdd `--resume`이다.
- **새 범위로 시작**: 진행 중인 다른 실행과 구버전(gx-ralph·gx-dev)의 기록·질문·잠금은 그대로 둔다. 같은 브랜치에 새 실행을 겹치지 않는다. 미커밋 변경이 없으면 베이스 브랜치로 돌아가고, 미커밋 변경이 있으면 그 변경이 따라오지 않도록 사용자 동의를 받아 새 워크트리(`git worktree add <경로> -b <새 브랜치> <베이스>`)를 직접 만들고 경로와 다음 명령(그 위치에서 `/oh-my-gx:gx-work <새 목표>`)을 제시한다([새 범위용 워크트리 만들기](references/tdd-entry.md#새-범위용-워크트리-만들기)). 새 실행은 새 브랜치·새 run-id·새 진입 질문을 쓰며 구버전 PRD·AC·커밋은 근거 문서로만 연결한다. 구버전 실행으로 되돌리라고 안내하지 않는다. SVN은 브랜치가 없으므로 새 목표에 쓸 slug를 사용자에게 받아 `--slug <새 slug>`로 시작한다. route에 같은 `--slug`를 넘기면 `.dev/.active` 대신 그 slug의 기록만 검사하고 결과에 `requested-slug`가 남는다. gx-tdd 인계 인자에도 `--slug <새 slug>`를 붙이면 setup이 `.dev/.active`를 새 slug로 바꾼다.

자연어 자동 발견은 하네스·설치 상태에 달려 있다. 실제 세션에서 확인하기 전 작동한다고 보고하지 않으며, 발견되지 않는 환경에서는 `/oh-my-gx:gx-work <목표>`를 명시 진입점으로 안내한다. 로컬 테스트와 `evals/`의 트리거 기대값은 라우팅·데이터 계약만 다루며 설치 발견·실제 모델·질문 UI의 증거를 대신하지 않는다.
