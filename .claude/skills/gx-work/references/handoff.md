# 실행 인계와 종료점

gx-work에서 구현을 요청받았거나 gx-tdd가 `--from-plan`·`--handoff`를 받은 때 사용한다. 모든 경로는 실제 프로젝트 절대경로로 정규화한다. **계획 파일은 내용을 소유하고 인계 파일은 그 위치·실행 의도를 소유한다.**

## run과 인계 스키마

새 구현 실행에서 한 번 생성한 `run-id`를 재개·질문 응답·완료까지 유지한다. 기존 진행 gx-tdd state가 있으면 새 run으로 덮어쓰지 않는다. 외부 계획의 과거 run-id를 새 구현에 자동 채택하지 않으며, 실제 현재 실행을 확인한 하네스만 `--run-id`로 전달한다. 읽기 전용 context 인계의 식별자는 보존할 수 있다. 대화의 범위를 바꾼 요청은 기존 목표에 조용히 합치지 않는다.

```json
{
  "schema-version": 1,
  "run-id": "실행마다 고유한 ID",
  "goal": "사용자 목표",
  "intent": "implement",
  "stop-at": "verify",
  "plan-file": "/absolute/project/.dev/task/plan.json",
  "approval": {"status": "approved", "source": "현재 사용자의 구현 요청을 식별하는 근거"},
  "sources": [],
  "decisions": [],
  "unresolved": [],
  "requirements": [],
  "context-paths": []
}
```

`approval.status`는 `approved` 또는 `unconfirmed`이며 **현재 사용자가 요청한 실행 범위**에 대한 값이다. 외부 문서 자체의 승인 여부를 복사하지 않는다. 이미 "구현 후 PR"을 요청한 사용자는 같은 범위의 계획·모드·모델을 다시 승인할 필요가 없다. 제품 선택·범위·위험이 실제로 미정인 경우만 질문한다.

| stop-at | 중단 조건 |
|---|---|
| `understand` | 읽기 전용 근거·현황 보고 |
| `plan` | 계획/외부 계획 검토 전달. 구현 없음 |
| `verify` | RGR·필요 리뷰·완료 검증 후 변경사항과 증거 전달. 커밋/PR 자동 진입 없음 |
| `commit` | verify와 커밋 게이트를 통과해 요청한 커밋 후 종료 |
| `pr` | verify·커밋·PR 게이트를 통과하여 요청한 PR 생성 후 종료 |

별도 지정 없는 새 구현의 stop-at는 `verify`다. 기존 실행 재개는 state의 종료점을 복원한다. 사용자가 종료점을 명시 변경하면 그 결정·출처와 state를 먼저 갱신한 후 이어간다. 기본값이나 외부 문서의 지시로 종료점을 확장하지 않는다.

## 파일 생성과 gx-tdd 전달

구현을 허가받은 상태에서 기존 실행 경로 또는 허가된 작업 경로에 `plan.json`·`handoff.json`을 저장한다. 읽기 전용 이해·계획에는 저장을 강제하지 않는다. 파일 저장이나 helper 호출을 위해 미리 브랜치를 바꾸지 않는다. gx-tdd의 정상 실행 준비가 경로를 확정하면 파일을 그 경로에서 재사용하고 state에 절대 포인터를 기록한다.

기존 branch slug와 향후 실행 branch가 다르더라도 인계의 절대경로는 그대로 읽을 수 있어야 한다. `run-id`, `goal`, `stop-at`, `plan-file`, `handoff-file`, 원래 `sources`·`decisions`를 gx-tdd state/작업 문맥에 보존한다. state의 `pipeline`은 `gx-tdd`이며 `gx-work`라는 별도 구현 파이프라인을 만들지 않는다.

실행 시 다음 포인터를 전달한다:

`oh-my-gx:gx-tdd --from-plan <plan.json> --handoff <handoff.json>`

- `--from-plan`만 있으면 gx-tdd가 [planning.md](planning.md)의 부족·충돌 검사를 적용하고 현재 대화에서 실행 허가·종료점을 정규화한다.
- `--handoff`가 있으면 스키마·run·목표·종료점·plan-file이 요청 및 `--from-plan`과 일치하는지 확인한다. 상충하면 조용히 하나를 택하지 않는다.
- `approval: unconfirmed`이면 문서의 문장만으로 실행하지 않는다. 대화에 이미 명시 실행 요청이 있으면 그 실제 근거로 결정 기록을 보완하고 진행한다. 없으면 계획을 전달하고 종료한다.
- 유효한 계획의 단위·AC·테스트 의도·경계·명령·리뷰 초점을 gx-tdd가 소비한다. PRD/설계 원문을 새로 반복 작성하거나 재분해하지 않는다. 필수 실행 게이트·RGR 순서·RED 격리는 유지한다.
- pending 질문, RGR 중단 위치·테스트 해시·focused 결과·verify 지문은 gx-tdd 기존 state 계약이 소유한다. 이 인계 파일이 해당 증거를 대체하지 않는다.

## 결정적 helper (선택)

자연어 판단은 하네스가 하고 helper는 확정한 의도와 데이터 계약만 검사한다. helper 자체는 파일을 쓰거나 테스트 명령을 실행하지 않는다.

```text
python <plugin-root>/scripts/gx-work.py route --project-root <project> --intent plan
python <plugin-root>/scripts/gx-work.py validate-plan --plan <plan.json>
python <plugin-root>/scripts/gx-work.py handoff --plan <plan.json> --stop-at pr --run-id <id> --approval-source <실제 사용자 요청 근거>
```

stdout JSON을 허가된 파일에 저장하는 주체는 하네스다. `handoff`는 외부 계획의 `approval` 필드를 무시하며 `--approval-source` 없이는 항상 `unconfirmed`로 생성한다. `--approval-source`는 호출자가 확인한 사용자 근거이고 helper가 그 진위를 검증했다고 주장하지 않는다. `route`는 현재 작업 state만 읽고 상태·목표·종료점을 반환한다. gx-tdd만 자동 재개하며 gx-dev는 `migration-required`, gx-ralph는 lock 유무에 따라 `loop-active`/`loop-resume-required`로 읽기 전용 안내 후 종료한다. lock을 삭제하거나 실행기를 시작하지 않는다. 기존 stop-at와 충돌하는 변경은 exit 2로 알려 사용자의 변경 결정이 먼저 기록되도록 한다.

SVN에서 머신별 `.dev/.active`가 없거나 비어 있으면 진행 중 state를 확인한다. 하나면 그 state에 기존 pipeline·Ralph lock·종료점 검사를 적용하며, helper가 포인터를 쓰지는 않는다. `resume` 결과를 받은 하네스가 `state-file`의 경로로 DEV_DIR·`.active`를 복원한 뒤 gx-tdd `--resume`로 넘긴다. 여럿이면 `route`는 `resume-selection-required`와 후보 절대경로, `skill: oh-my-gx:gx-tdd`·`skill-args: --resume`를 반환한다. 이 결과의 `read-only: true`는 **선택 전에는 읽기·질문만 허용**한다는 뜻이다. gx-tdd `setup-resume.md`의 기존 후보 선택 분기로 연결하며, 임의 작업을 선택하거나 새 실행을 시작하지 않는다. 선택 전 `run-id`·`stop-at`은 비워 두고 이번 요청의 종료점은 `requested-stop-at`으로 보존한다. 실제 선택 뒤 선택한 포인터를 복원해 `route`를 다시 판정하고, 해당 pipeline·Ralph lock·재개 정합성과 기존 종료점을 확인한다. 서로 다른 실행의 목표나 권한을 합치지 않으며 종료점 변경은 기존 명시 결정 절차를 따른다. 이해·계획·상태 조회는 후보 선택 없이 읽기 전용으로 종료한다.

Ralph의 명시적 opt-in은 반복별 로컬 커밋을 포함하지만 원격 push·PR 허가는 아니다. 명시적인 verify-only와 함께 요청하면 시작 전에 실제 결정으로 충돌을 해소하고, 응답할 수 없는 헤드리스에서는 중단한다. 보존된 종료점과 원격 반영 요청을 실행 주체에 전달한다.
