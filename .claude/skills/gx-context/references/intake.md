# 대화·문서 공통 요구사항 정리

helper·모드 경로는 gx-context/SKILL.md 위치 기준이며 Markdown 링크는 이 파일 위치 기준이다. 대화와 문서는 입력 매체만 다르며 같은 정규화·질문 선별·원장·계획 절차를 쓴다.

## 출처와 결정

문서 추출·인계·결과 보고에는 [판단과 검증 전달](../../gx-work/references/reviewability.md)을 적용한다. 기존 sources·decisions·observed-facts를 재사용하며 새 질문이나 파일을 의무화하지 않는다. 확인 사실·추정·미결정과 근거 절을 함께 전달하고 중요한 정책·숫자는 원문과 대조한다.

새 도메인 요구·정책이 이전 팀 판단을 바꿀 수 있으면 [공유 결정 이력 대조](../../gx-work/references/decision-history.md)로 관련 `.dev` 원문·후속 설계와 적용 범위를 확인한다. 현재 요구와 이전 선택의 관계·원문 포인터를 기존 sources/decisions에 보존하며 미해결 의미 충돌만 실제 응답을 기다린다.

1. 사용자 메시지, 입력 문서의 관련 절, 기존 context의 관련 절을 한 번 수집한다. 긴 문서는 목차·해당 절부터 읽고 추가 근거가 필요할 때만 범위를 넓힌다. 후속 단계에는 원문 전문 대신 `path + section`, 관련 요구사항 ID, 이번 변경분을 넘긴다.
2. `goal`, 사용자 요청의 종료 지점 `stop-at`, `sources`, `decisions`, `unresolved`를 정리한다. gx-work가 준 `run-id`, `intent`, `stop-at`, `work-id`와 기존 승인 근거는 그대로 이어받는다. 직접 호출이면 `run-id: context-YYYYMMDD-HHMMSS`로 이번 정리를 식별만 하고 run 디렉토리·인계 파일·새 파이프라인 상태를 만들지 않는다. 종료 지점이 따로 없으면 context와 계획을 정리하는 `intent: plan`, `stop-at: plan`이다. "컨텍스트만/이해만/정리만"이면 `intent: understand`, `stop-at: understand`다. 실행·커밋·PR 의도는 상위 gx-work에 돌려주며 여기서 실행하지 않는다. 상위 gx-work 없이 직접 호출됐는데 "개발까지"·"PR까지"를 원하면 문서 정리 결과와 함께 `/oh-my-gx:gx-work <목표>`로 이어서 진행하도록 안내한다.
3. 문제·현재 프로세스·사용자/규모·담당·관련 레포는 **질문 목록이 아니라 정보 점검표**다. 사용자·문서가 명확히 말한 값은 출처를 기록하고 다시 확인하지 않는다. 담당자 이름, 업무량 등 누락이 실제 동작이나 인수 기준을 바꾸지 않으면 ❓로 남긴다. 수치가 성능·용량의 인수 기준을 바꿀 때만 수치를 묻는다. 근거 없는 숫자·담당자·미래 정책을 추천 답변처럼 만들어 넣지 않는다.
4. `decisions`는 `{topic, value, source, status, impact}`로 기록한다. status는 `explicit|inferred|unresolved`, impact는 `scope|behavior|architecture|acceptance|removal|metadata`다. 출처가 명확한 문서 내용도 explicit이다. 추론한 내부 구현·묶음 선택을 사용자가 맡겼으면 실제 위임 메시지를 `delegation-source`에 기록하여 같은 선택을 다시 묻지 않는다. 위임은 요구사항 제거 승인이나 계획 승인으로 승격하지 않는다.
5. 코드 스캔은 현재의 관측 사실(`observed-facts`)이다. 현재 구현에서 발견한 동작·빈 원장·아키텍처를 "앞으로 구현할 요구사항"으로 만들지 않는다. 미래 요구는 사용자 메시지·요구사항 문서에서만 추출하며 승인된 C-4-1 절차로 FR/NFR에 넣는다. 코드와 요구가 충돌하면 현황과 요청을 함께 기록하고, 결과가 바뀌는 미정 사항만 질문한다.

## 필요한 질문만

- 이미 답이 있는 다섯 사실, 담당자·용어 같은 비차단 정보, 승인된 동일 결정은 질문하지 않는다.
- 범위, 동작, 설계 제약, 인수 기준이 달라지는 미정·충돌만 질문한다. 사용자가 이미 준 전체본/추가분·도메인 범위도 다시 묻지 않는다. 전체본의 대체 범위가 미정이거나 실제 제거가 있으면 기존 C-3-1-1/C-4-1 승인을 유지한다.
- 질문은 독립적인 항목을 최대 3개씩 묶는다. 답에 따라 후속 질문이 달라질 때만 순차적으로 묻는다. 답변 후 관련 결정만 갱신한다. 다섯 사실 전체를 다시 보여주고 align 승인을 받지 않는다.
- D-4의 기존 context 변경, C-4-1의 개별 제거, P-7의 새 작업 계획 승인 경계를 유지한다. 같은 변경분에 대한 실제 승인 기록이 있으면 그 근거를 재사용한다. 위임된 내부 선택을 재질문하지 않아도 별도로 남아 있는 명시적 승인 게이트는 실행한다. 미응답·시간 경과·async 반환을 승인으로 쓰지 않는다.

## 설치된 helper 실행

모델이 문맥을 읽어 위 필드를 추출한 뒤 `scripts/intake.py`로 질문 선별과 인계 형식을 정규화한다. helper는 자연어를 해석하거나 승인 진위를 판정하지 않으며 원장·계획을 수정하지 않는다. **실제 질문 도구는 `questions` 중 답이 없는 항목에만 호출**한다. 이 파일은 Python 표준 라이브러리만 사용하며 소비 프로젝트의 scripts/를 가정하지 않는다.

확인한 설치 스킬 경로의 `scripts/intake.py`를 사용한다 (Windows는 PowerShell에서 `python`, POSIX는 `python3`). gx-work가 호출했으면 gx-work 실행 입력과 같은 run 디렉토리에 BOM 없는 UTF-8 입력 `.dev/<run-id>/context-intake.json`을 만들고 첫 줄을, 직접 호출이면 파일 없이 stdin으로 넣어 stdout만 받는 둘째 줄을 실행한다. 직접 호출이 `.dev/context-*` 임시 디렉토리를 만들어 팀 공유 대상에 남기지 않기 위해서다.

```text
python <확인한 gx-context 설치 경로>/scripts/intake.py .dev/<run-id>/context-intake.json --output .dev/<run-id>/context-handoff.json
python <확인한 gx-context 설치 경로>/scripts/intake.py -
```

입력 공통 필드는 `run-id`, `goal`, `intent`, `stop-at`, `sources`, `decisions`다. 선택 필드는 `approval`(기본 unconfirmed), `unresolved`, `requirements`, `observed-facts`, `context-paths`, `plan-file`, `work-id`(`W` + 두 자리 이상 ASCII 숫자)다. 기존 unresolved의 차단 항목은 구현 승인이 있어도 유지한다. 같은 topic의 명확하고 근거 있는 단일 explicit 답변만 기존 미정을 해소하며, 내부 위임 추론은 기존 차단 질문을 지우지 않는다. 같은 topic의 explicit 값이 충돌하면 출처를 함께 남기고 질문한다. 명시적으로 해결된 과거 결정은 근거 문서를 보존하고 활성 decisions 목록에서 교체한 뒤 다시 정규화한다. `requirements`는 `{domain,path,section,ids,origin}`이며 origin은 `document|conversation|code`다. 코드 origin은 observed-facts로 분리된다. `requirements`의 path는 저장·검증된 status.md, section은 `요구사항 원장`, ids는 그 도메인의 최종 FR/NFR ID만 쓴다. 본문·AC·상태·PR은 파일에 보존하고 인계에 복사하지 않는다.

원장을 쓰기 전에는 requirements를 빈 배열로 두고 필요한 질문을 선별한다. 답변·원장·공통 계획 마무리 후 같은 intake의 결정·원장 포인터를 갱신해 한 번 더 실행한다. 질문할 항목이 처음부터 없으면 중간 실행 없이 최종 인계 때만 실행해도 된다. 승인 상태가 approved면 실제 승인 source가 필수다. 위임 근거와 승인 근거를 서로 복사하지 않는다.

## 반환과 종료

반환 스키마는 `schema-version: 1`, `run-id`, `goal`, `intent`, `stop-at`, `sources[{path,scope}]`, `decisions`, `approval{status,source}`, `unresolved[{topic,impact,blocking,source}]`, `questions`, `requirements[{domain,path,section,ids}]`, `observed-facts`, `context-paths[{path,section}]`, `plan-file`, `work-id`(없으면 null)다. 이번 정리로 연결하거나 새로 만든 W행이 있으면 `work-id`에 넣어 gx-work가 같은 작업으로 인계하게 한다. 파일 경로는 소비 프로젝트 기준이며 메시지가 출처면 `path: null`과 scope의 메시지 식별자로 표시한다.

공통 작업 계획 정합성 확인은 어느 모드든 한 번 수행한다. 차단 질문이 남으면 해당 항목과 pending 질문 위치를 반환하고 실제 응답을 기다린다. 처리 후에는 gx-work 호출자에게 `context-handoff.json` 경로와 관련 변경 요약만 반환한다. 다른 오케스트레이터를 호출하거나 구현을 시작하지 않는다. 상위 gx-work 없는 직접 호출이면 변경 요약만 보여주고, 개발까지 이어가려면 `/oh-my-gx:gx-work <목표>`(작업 계획의 행이면 `/oh-my-gx:gx-work W07 시작`)로 시작하도록 안내한 뒤 종료한다. "gx-work에 인계합니다"처럼 존재하지 않는 상위 호출자를 가정하지 않는다. 사용자가 정한 종료 지점은 다음 단계 실행 권한이 아니다.
