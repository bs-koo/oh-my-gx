# 실행 인계와 종료점

gx-work가 실제 TDD 진입 답변을 받았거나 gx-tdd가 `--from-plan`·`--handoff`를 받은 때 사용한다. 모든 경로는 실제 프로젝트 절대경로로 정규화한다. **요청/기존 계획 파일은 내용을 소유하고 인계 파일은 그 위치·실행 의도·진입 답변을 소유한다.** 진입 전의 결과 제안·질문 대기는 [작업 총괄 계약](tdd-entry.md)이 정본이다.

## run과 인계 스키마

새 구현 실행에서 한 번 생성한 `run-id`를 재개·질문 응답·완료까지 유지한다. 기존 진행 gx-tdd state가 있으면 새 run으로 덮어쓰지 않는다. 외부 계획의 과거 run-id를 새 구현에 자동 채택하지 않으며, 실제 현재 실행을 확인한 하네스만 `--run-id`로 전달한다. 읽기 전용 context 인계의 식별자는 보존할 수 있다. 대화의 범위를 바꾼 요청은 기존 목표에 조용히 합치지 않는다.

아래는 구조 설명용이다. 실제 인계 파일은 helper가 생성한 stdout 전체를 저장하며 지문·경로·승인 근거를 수동으로 추측해 채우지 않는다.

```json
{
  "schema-version": 1,
  "origin": "gx-work",
  "project-root": "/absolute/project",
  "run-id": "실행마다 고유한 ID",
  "goal": "사용자 목표",
  "intent": "implement",
  "stop-at": "verify",
  "handoff-kind": "request",
  "request-file": "/absolute/project/.dev/task/intake.json",
  "input-sha256": "helper가 계산한 현재 인계 범위 지문",
  "approval": {"status": "approved", "source": "현재 사용자의 구현 요청을 식별하는 근거"},
  "entry-approval": {
    "status": "approved",
    "source": "제시한 범위로 gx-tdd에 진행하겠다는 실제 질문 응답 근거",
    "question-set-id": "질문 helper가 반환한 식별자",
    "scope-sha256": "helper가 계산한 현재 인계 범위 지문"
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

`approval.status`는 `approved` 또는 `unconfirmed`이며 **현재 사용자가 요청한 작업 범위**에 대한 값이다. 외부 문서 자체의 승인 여부를 복사하지 않는다. 최초 “구현 후 PR” 요청은 요청 범위와 종료점의 근거이며 **이후 제시하는 TDD 진입 질문의 답변은 아니다.** `entry-approval`은 제시한 범위·관련 문서/FR/W·종료점으로 gx-tdd에 진입하겠다는 실제 답변만 기록한다. 같은 run·범위의 유효한 진입 승인·내부 선택·모드·모델은 다시 묻지 않는다. 제품 선택·범위·위험의 미정과 충돌은 계속 질문한다.

구체 구현계획이 없는 새 요청은 `handoff-kind: request`와 `request-file`을 사용한다. 입력 요청의 최소 내용은 `{goal, sources?, decisions?, unresolved?, requirements?, context-paths?, work-id?}`이며 `units`·Given-When-Then AC를 강제하지 않는다. gx-tdd가 PRD·설계·T태스크 구현계획을 만든다. 이미 구체 계획이 있을 때만 [계획 계약](planning.md)의 정규화 JSON을 `handoff-kind: plan`·`plan-file`로 재사용한다. 새 요청에 계획 파일을 만들기 위한 선행 구현계획 작성을 추가하지 않는다.

| stop-at | 중단 조건 |
|---|---|
| `understand` | 읽기 전용 근거·현황 보고 |
| `plan` | 계획/외부 계획 검토 전달. 구현 없음 |
| `verify` | RGR·필요 리뷰·완료 검증 후 변경사항과 증거 전달. 커밋/PR 자동 진입 없음 |
| `commit` | verify와 커밋 게이트를 통과해 요청한 커밋 후 종료 |
| `pr` | verify·커밋·PR 게이트를 통과하여 요청한 PR 생성 후 종료 |

별도 지정 없는 새 구현의 stop-at는 `verify`다. 기존 실행 재개는 state의 종료점을 복원한다. 사용자가 종료점을 명시 변경하면 그 결정·출처와 state를 먼저 갱신한 후 이어간다. 기본값이나 외부 문서의 지시로 종료점을 확장하지 않는다.

## 파일 생성과 gx-tdd 전달

계획·이해만 요청해 gx-tdd의 문서 절차를 선택하는 경우에도 실제 진입 응답을 받는다. 이 인계는 검증 뒤 `ready-for-tdd: true`여도 `read-only: true`·`execution-authorized: false`다. 요청한 계획 결과에서 종료하며 실행 setup·코드·테스트·커밋으로 확장하지 않는다. 문서 저장 요청이 없으면 대화에만 제시한다. 일반 구현 인계는 `execution-authorized: true`도 확인한다.

실제 진입 답변을 받은 뒤 기존 실행 경로 또는 허가된 작업 경로에 요청/기존 정규화 계획과 `handoff.json`을 저장한다. 읽기 전용 이해·계획에는 저장을 강제하지 않는다. 파일 저장이나 helper 호출을 위해 미리 브랜치를 바꾸지 않는다. 진입 답변 전에는 branch/worktree 변경·gx-setup·W착수·빌드·테스트·코드 수정·커밋·push를 수행하지 않는다. gx-tdd의 정상 실행 준비가 경로를 확정하면 파일을 그 경로에서 재사용하고 state에 절대 포인터를 기록한다.

기존 branch slug와 향후 실행 branch가 다르더라도 인계의 절대경로는 그대로 읽을 수 있어야 한다. `run-id`, `goal`, `stop-at`, `request-file` 또는 `plan-file`, `handoff-file`, 실제 `entry-approval`, 원래 `sources`·`decisions`를 gx-tdd state/작업 문맥에 보존한다. state의 `pipeline`은 `gx-tdd`이며 `gx-work`라는 별도 구현 파이프라인을 만들지 않는다.

실행 시 다음 포인터를 전달한다:

`oh-my-gx:gx-tdd <원래 목표> --handoff <handoff.json>`

기존 구체 계획을 인계하는 경우에만 `--from-plan <plan.json>`을 추가한다.

- `--from-plan`만 있는 gx-tdd 독립 호출은 [planning.md](planning.md)의 부족·충돌 검사와 기존 실행 허가·종료점 계약을 적용한다. gx-work 경유 진입 질문을 새로 강제하지 않는다.
- gx-work `--handoff`는 `validate-handoff --handoff <handoff.json> --project-root <PROJECT_ROOT>`로 다시 검사한다. run·프로젝트·목표·종료점·근거 묶음·요청/계획 지문이 일치하고 `ready-for-tdd: true`일 때만 setup/계획 단계로 진행한다. `--from-plan`이 있으면 같은 plan-file인지도 확인한다.
- `entry-approval` 누락·미응답·오래된 지문·범위 불일치면 `pending`으로 원래 질문을 복원한다. 일반 `approval`의 요청 근거로 진입 승인을 채우지 않는다. async ack·헤드리스는 실제 답변이 아니며 헤드리스는 `BLOCKED`로 종료한다.
- 유효한 기존 계획은 단위·AC·테스트 의도·경계·명령·리뷰 초점을 재사용한다. 계획이 없는 요청은 원문·문서 포인터로 gx-tdd의 PRD·설계·T계획을 만든다. context의 W목록을 T태스크 구현계획으로 오인하지 않는다. 필수 실행 게이트·RGR 순서·RED 격리는 유지한다.
- pending 질문, RGR 중단 위치·테스트 해시·focused 결과·verify 지문은 gx-tdd 기존 state 계약이 소유한다. 이 인계 파일이 해당 증거를 대체하지 않는다.

구현 인계에는 [관련 문서 연결](../../gx-context/references/development-sync.md)의 관련 FR/W·context 포인터와 이미 확인한 결정만 보존한다. gx-tdd가 직접 호출·재개에도 같은 대조를 적용한다. 문서를 이미 확인했으면 같은 snapshot/보고서를 재사용하고 전체 context 모드나 인터뷰를 다시 실행하지 않는다. 완료 순서는 **현재 AC 증거 대조 → 관련 문서 차이 반영 → 최종 verify → 요청한 커밋/PR**이며 새 PR URL은 `.dev` 전달 기록에 둔다. 최종 verify 뒤 context에 쓰면 현재 지문을 다시 검증해야 한다.

## helper와 입력 검증

자연어 판단과 실제 응답 확인은 하네스가 하고 helper는 확정한 의도·데이터·진입 근거의 정합성만 검사한다. helper 자체는 파일을 쓰거나 테스트 명령을 실행하지 않는다.

```text
python <plugin-root>/scripts/gx-work.py route --project-root <project> --intent plan
python <plugin-root>/scripts/gx-work.py validate-plan --plan <plan.json>
python <plugin-root>/scripts/gx-work.py handoff --request <intake.json> --project-root <project> --stop-at pr --run-id <id> --approval-source <최초 요청 근거> --entry-approval-source <실제 TDD 진입 응답 근거> --question-set-id <질문 식별자>
python <plugin-root>/scripts/gx-work.py handoff --plan <existing-plan.json> --project-root <project> --stop-at verify --run-id <id> --approval-source <최초 요청 근거> --entry-approval-source <실제 TDD 진입 응답 근거>
python <plugin-root>/scripts/gx-work.py validate-handoff --handoff <handoff.json> --project-root <project>
```

stdout JSON을 허가된 파일에 저장하는 주체는 하네스다. `handoff`는 `--request`와 `--plan` 중 하나만 사용하며 외부 문서의 `approval` 필드를 무시한다. `--approval-source`는 최초 요청 범위만 기록하고 이것만 있으면 `ready-for-tdd: false`다. `--entry-approval-source`는 실제 진입 질문 응답이며 optional `--question-set-id`는 해당 질문 helper의 식별자다. 인계 결과의 `entry-approval.scope-sha256`은 현재 root·run·종료점·메타데이터·입력 내용의 연결을 검사하는 근거다. helper가 실제 사용자 사건의 진위를 증명했다고 주장하지 않는다.

`route`보다 먼저 state 없는 현재 브랜치 경로의 pending 질문도 복원한다. 별도 workflow 파일은 생성하지 않는다. `route`는 현재 작업 state를 읽고 상태·목표·종료점을 반환한다. gx-tdd만 자동 재개하며 gx-dev는 `migration-required`, gx-ralph는 lock 유무에 따라 `loop-active`/`loop-resume-required`로 읽기 전용 안내 후 종료한다. lock을 삭제하거나 실행기를 시작하지 않는다. 기존 stop-at와 충돌하는 변경은 exit 2로 알려 사용자의 변경 결정이 먼저 기록되도록 한다.

SVN에서 머신별 `.dev/.active`가 없거나 비어 있으면 진행 중 state를 확인한다. 하나면 그 state에 기존 pipeline·Ralph lock·종료점 검사를 적용하며, helper가 포인터를 쓰지는 않는다. `resume` 결과를 받은 하네스가 `state-file`의 경로로 DEV_DIR·`.active`를 복원한 뒤 gx-tdd `--resume`로 넘긴다. 여럿이면 `route`는 `resume-selection-required`와 후보 절대경로, `skill: oh-my-gx:gx-tdd`·`skill-args: --resume`를 반환한다. 이 결과의 `read-only: true`는 **선택 전에는 읽기·질문만 허용**한다는 뜻이다. gx-tdd `setup-resume.md`의 기존 후보 선택 분기로 연결하며, 임의 작업을 선택하거나 새 실행을 시작하지 않는다. 선택 전 `run-id`·`stop-at`은 비워 두고 이번 요청의 종료점은 `requested-stop-at`으로 보존한다. 실제 선택 뒤 선택한 포인터를 복원해 `route`를 다시 판정하고, 해당 pipeline·Ralph lock·재개 정합성과 기존 종료점을 확인한다. 서로 다른 실행의 목표나 권한을 합치지 않으며 종료점 변경은 기존 명시 결정 절차를 따른다. 이해·계획·상태 조회는 후보 선택 없이 읽기 전용으로 종료한다.

Ralph의 명시적 opt-in은 반복별 로컬 커밋을 포함하지만 원격 push·PR 허가는 아니다. 명시적인 verify-only와 함께 요청하면 시작 전에 실제 결정으로 충돌을 해소하고, 응답할 수 없는 헤드리스에서는 중단한다. 보존된 종료점과 원격 반영 요청을 실행 주체에 전달한다.
