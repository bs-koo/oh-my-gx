# Codex 질문 대기 계약

이 파일은 [공통 실행 규약](codex-runtime.md)의 질문 분기에서 읽는다. Claude `AskUserQuestion` 계약은 유지한다. 이미 사용자가 제공한 선택·승인은 다시 묻지 않는다. optional 질문의 무응답과 필수 결정의 무응답을 구분한다.

## 도구 선택과 표시

실제 노출된 도구의 사용 가능한 모드와 용도를 먼저 읽는다. Plan 전용 동기 도구는 Default에서 쓰지 않는다. 질문 도구가 optional 전용이거나 승인 용도로 금지되면 필수 선택·승인을 그 도구로 우회하지 않고 자연어로 질문한다. async가 허용된 정보·선호 질문에는 `questions: [{title, options: [문자열]}]` 형식을 사용한다. 동기 스키마의 id/header/options 객체/multiSelect를 그대로 보내지 않는다.

질문 등록 뒤 반환된 `visible_question`의 본문·선택지·설명을 사용자가 볼 수 있는 답변에도 표시한다. 사용자가 앱의 접힌 도구 상세를 열어야만 질문 내용을 알 수 있는 상태로 끝내지 않는다. 앱이 질문 UI를 펼치거나 팝업을 여는 동작은 플러그인이 제어하지 못한다. 선택은 UI 또는 자연어로 답할 수 있음을 안내한다.

## 필수 질문의 등록·대기·재개

설치된 [질문 helper](../../../../scripts/codex-question.py)를 사용한다. 단, gx-tdd 읽기 전용 인계·문서 저장 금지·대화 전용 계획의 질문은 helper에 등록하지 않고 자연어로 묻고 실제 답을 기다린다(gx-tdd `references/requirements-dialogue.md` 3절). 경로는 codex-runtime에서 확인한 설치 루트와 소비 프로젝트 루트로 조립한다. `--dev-dir`은 해당 프로젝트 안의 현재 `.dev/<branch-slug>`다. 초기 setup처럼 state.md가 아직 없으면 현재 Git 브랜치·SVN 활성 작업을 기준으로 같은 작업 경로를 먼저 확정한다. 순수 gx-context 등 파이프라인 밖 질문은 `.dev/<현재 브랜치 또는 작업 slug>`에 질문만 저장하며 가짜 pipeline state를 생성하지 않는다.

등록 입력 예:

```json
{"phase":"design","goal":"사용자 원문 목표","run_id":"20261109-153000-pay-limit","questions":[{"id":"design_approval","header":"설계 확인","question":"설계서를 확인해주세요.","options":[{"label":"승인 (Recommended)","description":"구현 단계로 진행합니다."},{"label":"수정 요청","description":"수정 내용을 후속 질문으로 확인합니다."}]}]}
```

`goal`·`run_id`는 선택이지만 state가 아직 없는 질문(gx-work 진입 질문 등)에는 넣는다. 그래야 다음 요청에서 route가 `pending-goal`·`pending-run-id`로 같은 작업의 질문인지 대조한다. 이때 `--dev-dir`은 현재 작업 디렉토리 `.dev/<branch-slug>`(SVN은 활성 slug, `--slug`로 새 slug를 시작하면 그 새 slug)여야 route가 찾는다.

**gx-work 진입 질문의 둘째 세트**: 남은 진입 질문이 넷이라 나눠 물을 때 첫 세트는 `gx_work_tdd_entry`·`gx_work_stop_at`, 둘째 세트는 `gx_work_mode`·`gx_work_model_profile`(선택지 `전체`/`핵심`, `표준`/`에코`)이다. 둘째 세트는 같은 `--dev-dir`에 같은 `run_id`의 진입 답이 `gx-tdd로 진행`으로 기록된 뒤에만 등록되며, 그 전에 등록하면 helper가 exit 2(`blocked`)로 거절한다. 진입 답이 `문서·범위 보완`·`여기서 종료`면 둘째 세트를 묻지 않는다. 두 세트 모두 `goal`·`run_id`를 넣고, 요청·설정에서 정한 항목과 핵심 모드의 프로파일은 뺀다. `answer` 영수증(`answered-question.json`)에는 이 run에서 답한 모든 세트의 답 누적 `run_answers`와 앞 세트 id 목록 `earlier_question_set_ids`가 남는다. 인계의 `--question-set-id`에는 첫 세트 id를 넘긴다. 둘째 세트가 미응답이면 `handoff`가 exit 2다. 첫 세트 답 뒤 끊겼다가 재진입하면 route의 `entry-followup-missing`에 남은 질문만 다시 등록한다(gx-work SKILL.md).

Windows PowerShell 예시:

```powershell
python "$pluginRoot/scripts/codex-question.py" register --cwd '<PROJECT_ROOT>' --dev-dir '.dev/<slug>' --input '<question.json>'
python "$pluginRoot/scripts/codex-question.py" status --cwd '<PROJECT_ROOT>' --dev-dir '.dev/<slug>'
```

1. `register`의 exit 0을 확인한 뒤 질문을 표시한다. `pending-question.json`에 stable snake_case id·원래 phase·질문·선택지가 보존된다. 기존 미응답 질문을 새 질문으로 덮어쓰지 않는다.
2. async 도구 호출 완료는 **등록 확인(ack)** 이다. 선택지 preselection, 추천 값, 시간 경과, 도구의 성공·빈 반환은 실제 답변이 아니다. 등록 직후에는 결정·승인을 기록하지 않는다.
3. `status`가 exit 2면 응답 대기다. 다음 phase, 선택에 의존하는 파일 변경, 승인에 의존하는 커밋/PR로 진입하지 않는다. 독립 읽기·조사만 계속할 수 있다. 독립 작업을 끝냈거나 자연어 필수 질문을 썼으면 질문·선택지·대기 사유를 포함한 final 응답으로 턴을 종료한다. 같은 질문을 다시 등록하거나 긴 sleep으로 앱을 붙잡아 두지 않는다.
4. 실제 사용자 메시지 또는 질문 도구의 실제 응답이 도착하면 pending id와 질문 세트를 대조한다. 오케스트레이터가 register의 `question_set_id`를 아래 정규화 답변에 붙인다. token을 사용자에게 입력시키지 않는다. 다른 token/id, 빈 답변, 부분 답변은 pending을 해제하지 않는다. 늦은 응답이 현재 질문에 대한 답인지 대화 문맥으로 확인하고 불명확한 응답은 필요한 부분만 다시 확인한다. 선택 라벨 이외의 자유 입력도 실제 사용자 답변이면 보존한다.
5. `answer`가 exit 0일 때만 결정 기록 성공과 pending 해제를 인정하고 원래 phase에서 재개한다. 기록 실패는 대기 상태를 유지한다. 같은 답변의 재전달은 중복 기록하지 않는다.

```json
{"question_set_id":"<register가 반환한 UUID>","answers":{"design_approval":{"answers":["승인 (Recommended)"]}}}
```

```powershell
python "$pluginRoot/scripts/codex-question.py" answer --cwd '<PROJECT_ROOT>' --dev-dir '.dev/<slug>' --input '<actual-answer.json>'
```

6. 미응답 질문을 버리고 새 작업으로 가겠다는 **실제 사용자 답변**이 있을 때만 `discard`로 폐기한다. 시간 경과·새 요청의 도착만으로 폐기하지 않고 pending 파일을 직접 지우지 않는다. exit 0이면 pending이 같은 디렉토리의 `discarded-question-<UTC 시각>.json`으로 보관되고 `decisions.md`에 폐기 사유가 기록된다. 형식이 깨진 pending도 원문 바이트를 보관 파일에 담고 해제한다(결과 `malformed: true`, 정상 pending은 `malformed: false`). pending 없음, `.question-lock` 있음, `--reason` 누락·빈 값이면 exit 2(`{"status":"blocked","error"}`)이므로 멈추고 보고한다. 질문 helper의 `answer` 영수증은 선택값(`answers`)도 남기며, gx-work route는 이를 `answered-selection`으로 돌려준다.

```powershell
python "$pluginRoot/scripts/codex-question.py" discard --cwd '<PROJECT_ROOT>' --dev-dir '.dev/<slug>' --reason '<실제 사용자 결정 근거>'
```

helper 입력은 오케스트레이터가 전달한 실제 사용자 답변에 의존한다. helper가 앱 사용자 이벤트의 진위를 증명하거나 하네스 모든 도구를 강제로 차단하는 것은 아니다. optional 질문에는 helper를 의무 등록하지 않으며 도구의 무응답 처리 규칙을 따른다. 헤드리스 실행에서 필수 질문이 필요하면 BLOCKED와 질문·phase를 기록해 종료한다. 무응답을 승인으로 간주하지 않는다.

비정상 종료로 `.question-lock`이 남으면 프로세스와 pending·결정 기록을 확인한 뒤 명시적으로 복구한다. 잠금이 있는 동안 helper는 exit 2를 반환하며 자동으로 잠금을 없애 승인·기록을 추측하지 않는다. pending·완료 영수증·폐기 보관 파일·잠금·모델 호출 JSONL은 현재 세션 런타임 파일이므로 Git에 공유하지 않는다.

## 기록과 훅

pending 질문은 `answer`가 `decisions.md`에 같은 id로 기록한다. Claude의 기존 PostToolUse와 pending 없는 동기 질문은 기존 capture 경로를 유지한다. async hook은 실제 answers 없는 ack를 무시한다. raw async 호출에는 id가 없으므로 최종 사용자 응답은 pending을 읽어 정규화하고 `answer`로 전달한다. 이 원칙은 UI 자유 입력과 자연어 답변에도 같다.

완료 후 hook 중복 제거는 같은 `question_set_id`가 payload에 명시되고 실제 marker까지 일치할 때만 적용한다. token 없는 raw 동기 이벤트는 새로운 독립 질문일 수 있어 정상 기록한다. helper의 동일 token 재시도는 중복 없이 처리되지만 token 없는 지연 hook의 이벤트 동일성을 자동 증명하지 않는다.

후속 `--resume`과 각 phase 진입은 먼저 pending 상태를 확인한다. 미응답이면 원래 질문을 표시하고 대기하며, 실제 응답이 기록·해제된 뒤에만 기존 state.md의 phase 순서를 진행한다. main status를 `completed`로 바꾸거나 미완료 phase를 완료로 표시해서 대기를 숨기지 않는다.
