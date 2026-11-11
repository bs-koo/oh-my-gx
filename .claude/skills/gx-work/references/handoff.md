# 실행 인계와 종료점

gx-work가 실제 TDD 진입 답변을 받았거나 gx-tdd가 `--from-plan`·`--handoff`를 받은 때 사용한다. **요청/기존 계획 파일은 내용을 소유하고 인계 파일은 그 위치·실행 의도·진입 답변을 소유한다.** 진입 전의 결과 제안·질문 대기와 최초 요청·진입 답변의 구분은 [작업 총괄 계약](tdd-entry.md)이 정본이다.

## 프로젝트 루트·run·저장 위치

- **프로젝트 루트**: gx-tdd와 같은 규칙이다. git은 `git rev-parse --show-toplevel`, SVN은 `svn info --show-item wc-root`의 결과다(`.claude/config.json`에 `vcs`가 없어도 `.svn`이 있으면 SVN으로 본다). 하위 디렉토리에서 시작했어도 이 루트를 `--project-root`로 넘기고, 사용자가 말한 경로와 다르면 어느 루트로 진행하는지 보여준다.
- **run-id**: 새 실행을 시작할 때 gx-work가 한 번 만들고(예: `20261109-153000-pay-limit`) 재개·질문 응답·완료까지 유지한다. 형식은 `^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$`이며 helper는 형식만 검사한다. 기존 진행 gx-tdd state가 있으면 새 run으로 덮어쓰지 않는다. 외부 계획의 과거 run-id를 새 구현에 자동 채택하지 않으며, 읽기 전용(`understand`·`plan`) 인계만 context 인계의 식별자를 보존할 수 있다. 대화의 범위를 바꾼 요청은 기존 목표에 조용히 합치지 않는다.
- **저장 위치**: gx-work 실행 입력(요청 intake, 기존 계획 정규화본, handoff, 문서 사전 대조 보고서)은 `.dev/<run-id>/`에 둔다. 다른 run의 파일을 덮어쓰지 않는다. gx-context의 문서 준비 기록은 진입 전에도 이 디렉토리에 생길 수 있지만, 요청·인계 파일은 진입 답변 뒤에 쓴다. 읽기 전용 이해·계획에는 저장을 강제하지 않으며, 파일 저장이나 helper 호출을 위해 브랜치를 바꾸지 않는다.
- **인코딩**: JSON은 BOM 없는 UTF-8로 쓴다. helper stdout을 그대로 저장하고 지문·경로·승인 근거를 손으로 고치지 않는다. Windows PowerShell 5.1의 `-Encoding UTF8`은 BOM을 붙이므로 쓰지 않고, [Codex 실행 규약](codex-runtime.md)의 UTF-8 설정을 따른다.

## 인계 스키마

아래는 구조 설명용이다. 실제 인계 파일은 helper가 만든 stdout 전체다.

```json
{
  "schema-version": 2,
  "origin": "gx-work",
  "project-root": "표시용 절대경로 (지문에 넣지 않음)",
  "run-id": "20261109-153000-pay-limit",
  "goal": "사용자 목표",
  "intent": "implement",
  "stop-at": "verify",
  "handoff-kind": "request",
  "request-file": ".dev/20261109-153000-pay-limit/intake.json",
  "plan-file": null,
  "work-id": "W118",
  "execution-method": null,
  "model-profile": null,
  "input-sha256": "요청/계획 파일 내용과 종류·상대경로·run-id·종료점을 묶은 입력 지문",
  "approval": {"status": "approved", "source": "현재 사용자의 구현 요청을 식별하는 근거"},
  "entry-approval": {
    "status": "approved",
    "source": "제시한 범위로 gx-tdd에 진행하겠다는 실제 질문 응답 근거",
    "question-set-id": "Codex 질문 helper가 반환한 값, Claude Code는 null",
    "scope-sha256": "입력 지문에 요청 근거·진입 응답 근거·question-set-id를 묶은 승인 지문"
  },
  "ready-for-tdd": true,
  "read-only": false,
  "execution-authorized": true,
  "sources": [],
  "decisions": [],
  "unresolved": [],
  "requirements": [],
  "context-paths": []
}
```

- 새 인계는 `schema-version: 2`다. 경로 포인터(`request-file`·`plan-file`, gx-tdd state의 `handoff-file`)와 지문 계산은 **프로젝트 루트 기준 POSIX 상대경로**를 쓰고 절대 루트를 지문에 넣지 않는다. `project-root`는 표시용이다. 그래서 브랜치 이름 변경·다른 PC·다른 워크트리에서도 같은 인계를 검증할 수 있다.
- `input-sha256`은 **입력 내용**의 지문이고, `entry-approval.scope-sha256`은 그 지문에 실제 승인 근거를 묶은 **승인** 지문이다. 입력이 바뀌면 둘 다, 승인 근거만 바뀌면 `scope-sha256`만 달라진다.
- 선택 필드: `work-id`(`W` + 두 자리 이상 ASCII 숫자), `execution-method`(`session`|`subagents`), `model-profile`(`standard`|`eco`). 사용자가 요청에서 밝혔거나 진입 질문에서 답한 값만 요청 파일 최상위에 넣는다. 쓰임새는 tdd-entry.md의 "인계 이후의 책임"을 따른다.
- v1 인계(`schema-version: 1`, 절대경로 포인터)도 `validate-handoff`가 그대로 검증한다. v1을 다른 경로에서 재개해 지문이 맞지 않으면 아래 `reissue`로 v2를 다시 발급한다.

`approval.status`는 `approved` 또는 `unconfirmed`이며 **현재 사용자가 요청한 작업 범위**에 대한 값이다. 외부 문서 자체의 승인 여부를 복사하지 않는다. `entry-approval`은 제시한 범위·관련 문서/FR/W·종료점으로 gx-tdd에 진입하겠다는 실제 답변만 기록한다. 같은 run·범위의 유효한 진입 승인·내부 선택·모드·모델은 다시 묻지 않는다. 제품 선택·범위·위험의 미정과 충돌은 계속 질문한다.

구체 구현계획이 없는 새 요청은 `handoff-kind: request`와 `request-file`을 쓴다. 요청 파일의 최소 내용은 `{goal, sources?, decisions?, unresolved?, requirements?, context-paths?, work-id?, execution-method?, model-profile?}`이며 `units`·Given-When-Then AC를 강제하지 않는다. gx-tdd가 PRD·설계·T태스크 구현계획을 만든다. 이미 구체 계획이 있을 때만 [계획 계약](planning.md)의 정규화 JSON을 `handoff-kind: plan`·`plan-file`로 재사용한다. 새 요청에 계획 파일을 만들기 위한 선행 구현계획 작성을 추가하지 않는다.

**요청 인계의 차단 규칙**: v2 요청 인계는 `unresolved`에 `blocking: true` 항목이나 `blocking` 값이 없는 항목이 있으면 helper가 exit 2와 `ready-for-tdd: false`, 이유 목록(`issues`)을 돌려준다. 결정 충돌은 gx-context intake와 같은 기준으로만 차단한다. `status: explicit`이고 source와 값이 있는 결정끼리 같은 topic의 값이 다르고, 그중 하나라도 impact가 scope·behavior·architecture·acceptance·removal일 때다. metadata 충돌, `status: unresolved`인 결정, 위임 추론과의 차이는 차단하지 않는다(필요하면 intake가 `unresolved`로 올린다). 그 항목을 실제 답변으로 해소해 요청 파일을 고친 뒤 다시 발급한다. 차단 미정을 남긴 채 진입 답변만으로 진행하지 않는다.

| stop-at | 중단 조건 |
|---|---|
| `understand` | 읽기 전용 근거·현황 보고 |
| `plan` | 계획/외부 계획 검토 전달. 구현 없음 |
| `verify` | RGR·필요 리뷰·완료 검증 후 변경사항과 증거 전달. 커밋/PR 자동 진입 없음 |
| `commit` | verify와 커밋 게이트를 통과해 요청한 커밋 후 종료 |
| `pr` | verify·커밋·PR 게이트를 통과하여 요청한 PR 생성 후 종료 |

별도 지정 없는 새 구현의 stop-at는 `verify`다. 기존 실행 재개는 state의 종료점을 복원한다. 종료점 변경은 SKILL.md의 **종료점 변경** 절차(결정 기록 → state 갱신 → `reissue`)를 따른다. 기본값이나 외부 문서의 지시로 종료점을 확장하지 않는다.

## 파일 생성과 gx-tdd 전달

계획만 요청한 경우는 대화로 끝내고 인계를 만들지 않는다. 사용자가 PRD·설계 문서 저장을 원해 tdd-entry.md의 계획 전용 질문에 답한 경우에만 `stop-at: plan` 인계를 만들며, 이 인계는 검증 뒤 `ready-for-tdd: true`여도 `read-only: true`·`execution-authorized: false`다. 요청한 계획 결과에서 끝나고 실행 setup·코드·테스트·커밋으로 넓히지 않는다. 일반 구현 인계는 `execution-authorized: true`도 확인한다.

실제 진입 답변을 받은 뒤 `.dev/<run-id>/`에 요청/기존 정규화 계획과 `handoff.json`을 저장한다. 진입 답변 전에는 branch/worktree 변경·gx-setup·W착수·빌드·테스트·코드 수정·커밋·push를 하지 않는다. gx-tdd state에는 `handoff-file`·`request-file`·`plan-file`을 프로젝트 상대경로로 기록한다(이전 절대경로 값도 읽는다). `run-id`, `goal`, `stop-at`, 실제 `entry-approval`, 원래 `sources`·`decisions`를 gx-tdd state/작업 문맥에 보존한다. state의 `pipeline`은 `gx-tdd`이며 `gx-work`라는 별도 구현 파이프라인을 만들지 않는다.

실행 시 다음 포인터를 전달한다:

`oh-my-gx:gx-tdd <원래 목표> --handoff <handoff.json>`

기존 구체 계획을 인계하는 경우에만 `--from-plan <plan.json>`을 추가한다.

- `--from-plan`만 있는 gx-tdd 독립 호출은 [planning.md](planning.md)의 부족·충돌 검사와 기존 실행 허가·종료점 계약을 적용한다. gx-work 경유 진입 질문을 새로 강제하지 않는다.
- gx-work `--handoff`는 `validate-handoff --handoff <handoff.json> --project-root <PROJECT_ROOT>`로 다시 검사한다. run·프로젝트·목표·종료점·근거 묶음·요청/계획 지문이 일치하고 `ready-for-tdd: true`일 때만 setup/계획 단계로 진행한다. `--from-plan`이 있으면 같은 plan-file인지도 확인한다.
- `entry-approval` 누락·미응답·오래된 지문·범위 불일치면 `pending`으로 원래 질문을 복원한다. 일반 `approval`의 요청 근거로 진입 승인을 채우지 않는다. async ack·헤드리스는 실제 답변이 아니며 헤드리스는 `BLOCKED`로 종료한다.
- **재검증 실패의 출구**: 종료점을 바꿨거나 v1 인계의 경로가 옮겨져 지문이 맞지 않으면 원래 인계를 손으로 고치지 않고 `reissue`로 다시 발급한다. 종료점 변경은 실제 사용자 결정 근거(`--change-source`)가 있어야 하며 그 근거가 새 범위의 `entry-approval.source`가 된다. v1 인계는 다른 경로에서 재발급하면 진입 승인을 유지한다. v2 인계는 위치가 바뀌어도 재발급 없이 검증되므로 경로 이동만으로는 재발급하지 않는다. 단 Codex 진입 답변의 응답 기록(표식)을 `.dev/<run-id>/decisions.md`에 복사하지 않은 채 옮겨 검증이 실패하면 같은 종료점 `reissue`로 다시 발급하고 `dropped-question-set-id`를 사용자에게 알린다. 재발급 결과의 `relocated: true`는 기록된 루트나 v1 절대 포인터가 현재 위치와 달랐다는 표시다. 종료점이 같으면 `--change-source`·`--question-set-id`를 주지 않는다(거절). 목표·요청 내용이 바뀐 경우, 읽기 전용 인계를 실행 인계로 바꾸려는 경우, 완료된 실행은 재발급을 거절하며 새 진입 질문으로 간다. 원래 question-set-id가 아직 답하지 않은 질문(pending)이면 재발급을 거절한다. 이 실행에 결박된 응답이 없는 question-set-id(3.0.0 인계의 고정 문자열, 기록 유실 등)만 버리고 승인 근거 문장을 남기며 결과의 `dropped-question-set-id`로 알린다. v1 인계(또는 이미 legacy로 재발급한 인계)를 재발급하면 결과에 `legacy-run-id: true`가 붙고, run-id 형식(I3)과 요청 차단 규칙을 소급 적용하지 않는다. 이 값은 지문에 묶이므로 손으로 지우거나 붙이지 않는다. 단 `/`·`\`·`..`·제어문자처럼 경로를 깨는 run-id는 legacy여도 거절하며, 그 실행은 새 진입 질문으로 시작한다.
- 유효한 기존 계획은 단위·AC·테스트 의도·경계·명령·리뷰 초점을 재사용한다. 계획이 없는 요청은 원문·문서 포인터로 gx-tdd의 PRD·설계·T계획을 만든다. context의 W목록을 T태스크 구현계획으로 오인하지 않는다. 필수 실행 게이트·RGR 순서·RED 격리는 유지한다.
- pending 질문, RGR 중단 위치·테스트 해시·focused 결과·verify 지문은 gx-tdd 기존 state 계약이 소유한다. 이 인계 파일이 해당 증거를 대체하지 않는다.

구현 인계에는 [관련 문서 연결](../../gx-context/references/development-sync.md)의 관련 FR/W·context 포인터와 이미 확인한 결정만 보존한다. gx-tdd가 직접 호출·재개에도 같은 대조를 적용한다. 문서를 이미 확인했으면 같은 snapshot/보고서를 재사용하고 전체 context 모드나 인터뷰를 다시 실행하지 않는다. 완료 순서는 **현재 AC 증거 대조 → 관련 문서 차이 반영 → 최종 verify → 요청한 커밋/PR**이며 새 PR URL은 `.dev` 전달 기록에 둔다. 최종 verify 뒤 context에 쓰면 현재 지문을 다시 검증해야 한다.

## helper와 입력 검증

자연어 판단과 실제 응답 확인은 하네스가 하고 helper는 확정한 의도·데이터·진입 근거의 정합성만 검사한다. helper 자체는 파일을 쓰거나 테스트 명령을 실행하지 않는다. 아래 `python`은 Windows PowerShell 기준이며 POSIX에서는 `python3`를 쓴다. 플러그인 루트는 SKILL.md의 규칙으로 확인한다.

```text
python <plugin-root>/scripts/gx-work.py route --project-root <project> --intent plan [--git-safe-directory <project>] [--slug <SVN 작업 slug>]
python <plugin-root>/scripts/gx-work.py validate-plan --plan <plan.json>
python <plugin-root>/scripts/gx-work.py handoff --request .dev/<run-id>/intake.json --project-root <project> --stop-at pr --run-id <run-id> --approval-source <최초 요청 근거> --entry-approval-source <실제 TDD 진입 응답 근거> [--question-set-id <Codex helper 반환값>] [--git-safe-directory <project>]
python <plugin-root>/scripts/gx-work.py handoff --plan .dev/<run-id>/plan.json --project-root <project> --stop-at verify --run-id <run-id> --approval-source <최초 요청 근거> --entry-approval-source <실제 TDD 진입 응답 근거> [--git-safe-directory <project>]
python <plugin-root>/scripts/gx-work.py validate-handoff --handoff .dev/<run-id>/handoff.json --project-root <project> [--git-safe-directory <project>]
python <plugin-root>/scripts/gx-work.py reissue --handoff .dev/<run-id>/handoff.json --project-root <project> [--stop-at verify|commit|pr] [--change-source "<실제 사용자 결정 근거>"] [--question-set-id <id>] [--git-safe-directory <project>]
```

helper는 내부에서 git으로 루트·브랜치를 확인한다(v1 인계 검증은 git을 부르지 않는다). Codex 샌드박스처럼 git 소유권 불일치(dubious ownership)가 나는 환경에서는 확인된 프로젝트 루트를 `--git-safe-directory`로 넘긴다. helper는 project-root와 같은 그 경로 하나에만 명령별 `safe.directory`를 적용하고 전역 설정을 바꾸지 않는다. `handoff`의 `--request`·`--plan` 상대경로는 프로젝트 루트 기준으로 해석한다(`validate-plan`의 `--plan`은 현재 디렉토리 기준).

stdout JSON을 허가된 파일에 저장하는 주체는 하네스다. 출력을 먼저 변수로 받아 exit 코드를 확인하고 exit 0일 때만 저장한다. 오류는 exit 2와 `{"error": ...}`이며 검증 실패에는 `issues` 목록과 `ready-for-tdd: false`가 함께 올 수 있다(인자 파싱 오류에는 `ready-for-tdd`가 없다), **오류 JSON을 인계 파일로 저장하지 않고** 필드·값·기대 형식이 담긴 내용을 그대로 보여준다. `handoff`는 `--request`와 `--plan` 중 하나만 쓰며 외부 문서의 `approval` 필드를 무시한다. `--approval-source`는 최초 요청 범위만 기록하고 이것만 있으면 `ready-for-tdd: false`다. `--entry-approval-source`는 실제 진입 질문 응답이다. `reissue`의 stdout은 같은 run-id와 `reissued-from-sha256`(이전 인계 파일의 지문)을 가진 새 인계이며 하네스가 같은 경로에 저장한다. helper가 실제 사용자 사건의 진위를 증명했다고 주장하지 않는다.

`route`의 결과값별 처리는 SKILL.md의 표를 따른다. gx-tdd만 자동 재개하며, 진행 중인 구버전(gx-ralph·gx-dev) 실행은 `migration-required`, 잠금은 `loop-active`로 기록 경로만 안내한다. lock을 지우거나 실행기를 시작하지 않으며 completed인 구버전은 재개하지 않는다. 새 목표에는 새 진입 결정을 적용한다.

SVN에서 `route --slug <slug>`를 주면 `.dev/.active`와 후보 탐색 대신 그 slug의 기록만 검사한다(git에서는 오류, 안전하지 않은 slug도 오류). 구버전 실행이 활성 포인터에 남아 있을 때 새 범위를 시작하는 경로다. 머신별 `.dev/.active`가 없거나 비어 있으면 진행 중 state를 확인한다. 하나면 그 state에 기존 pipeline·구버전 잠금·종료점 검사를 적용하며 helper가 포인터를 쓰지는 않는다. `resume` 결과를 받은 하네스가 `state-file`의 경로로 DEV_DIR·`.active`를 복원한 뒤 gx-tdd `--resume`으로 넘긴다. 여럿이면 `route`는 `resume-selection-required`와 후보 절대경로, `skill: oh-my-gx:gx-tdd`·`skill-args: --resume`을 반환한다. 이 결과의 `read-only: true`는 **선택 전에는 읽기·질문만 허용**한다는 뜻이다. gx-tdd `setup-resume.md`의 기존 후보 선택 분기로 연결하며 임의 작업을 고르거나 새 실행을 시작하지 않는다. 선택 전 `run-id`·`stop-at`은 비워 두고 이번 요청의 종료점은 `requested-stop-at`으로 보존한다. 실제 선택 뒤 포인터를 복원해 `route`를 다시 판정하고 해당 pipeline·구버전 잠금·재개 정합성과 기존 종료점을 확인한다. 서로 다른 실행의 목표나 권한을 합치지 않는다. 이해·계획·상태 조회는 후보 선택 없이 읽기 전용으로 종료한다.
