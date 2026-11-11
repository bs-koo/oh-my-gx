# RGR 재계획·케이스 변경·기준선 세대 공통 계약

gx-tdd의 requirements·implement·보안 수리·재개가 함께 적용한다. core의 결합 승인은 이 파일 기준 `core-planning.md`를 따른다. 전체 모드·core→all 전환에도 이미 구현된 케이스를 유지하는 같은 절차를 적용한다. 이 문서는 실행 절차와 순수 정책 예제이며 새 helper나 실행 엔진을 만들지 않는다. Claude Code와 Codex 모두 오케스트레이터가 분류·검증하고, 테스트 수정은 기존 red-writer 역할만 수행한다. Codex 디스패치는 `../../gx-work/references/codex-runtime.md`의 격리 인계 규칙을 따른다.

## 1. 변경 전 확인과 불변 이력

1. 문서·테스트를 바꾸기 **전에** 현재 active 기준선 세대의 `test-file-hash`와 테스트 파일·porcelain를 대조한다. 위반이나 소유권 불명이 있으면 멈추고 원인을 해결하며, 현재 파일의 hash로 덮어서 통과시키지 않는다. 처음 구현된 적 없는 태스크에는 이전 기준선이 없다.
2. 이전 테스트 원문·케이스 본문/기대값 스냅샷·AC·plan·RED/IMPL report·hash·test-count·porcelain를 `${DEV_DIR}/history/{baseline-generation}/{task-id}/`에 **불변 이력**으로 보관한다. 기존 report의 역사 절도 보존한다. 원본 확인 후 복사하며, 이력 파일을 다음 세대 입력으로 고쳐 쓰지 않는다. 진행 중 `baseline-fingerprint`와 공통 테스트 plan/proof·로그도 별도 기준선 증거로 그대로 둔다. 현재 run·코드·설정·명령·범위가 달라진 proof는 보존하되 재사용하지 않는다.
3. 변경할 AC와 태스크별 케이스 변경표를 작성한다. core는 문서 변경 전 승인 무효화 → G-W-T·계획 갱신 → AC+계획 실물 함께 재승인한다. 전체 모드는 기존 요구사항·설계 승인 절차로 변경 범위를 확정한다. phase-review 4a 기본 RGR 수정의 Ruling(승인된 범위 안에서 결함 케이스만 `add`하는 변경표)은 변경표 승인으로 본다. 기존 AC 문구·범위를 바꾸거나 `replace`·`retire`가 필요하면 4a 예외(묻는다)로 처리하고 그 실제 응답을 승인으로 쓴다. 승인 전 테스트를 교체·은퇴시키지 않는다.

변경표 report와 state의 연결에는 `baseline-generation`(예: `g2`), `active-case-ids`, `previous-task-ids`(예: `[T1, T2]`), `supersedes`(예: `[g1/T1, g1/T2]`), `case-change-report`(예: `reports/g2/t3-case-changes.md`)를 기록한다. 각 케이스 행은 다음 필드를 갖는다:

| 필드 | 내용 |
|---|---|
| `case-id`, `AC-ID` | 재사용하지 않는 케이스 ID와 연결된 AC |
| `test-file`, `selector` | 실제 테스트 파일과 러너에서 그 케이스 하나를 고르는 정확한 selector |
| `change` | `keep` / `add` / `replace` / `retire` |
| `previous-case-id` | replace/retire의 이전 ID, add는 없음 |
| `previous-expectation`, `expectation` | 이전/새 기대값 원문; 없는 쪽은 없음 |
| 본문 스냅샷·명령·결과 | 변경 전/후 본문, 케이스별 직접 실행 증거와 이력 경로 |

AC 기대값 변경은 같은 `case-id`를 고치는 방식으로 숨기지 않는다. 새 ID에 `replaces: 이전ID`를 연결하고, 이전 AC의 기대값과 새 AC의 기대값을 나란히 남긴다. 새 기대값과 모순되는 이전 케이스만 승인된 범위에서 교체할 수 있다. 관련 없는 이전 케이스는 `keep`으로 보존한다. 은퇴·교체된 ID는 이력에서 영구 예약하여 다시 활성화하지 않는다. active 세대 전환 시 `retired-case-ids` 원장에 분류 결과의 `retire`뿐 아니라 `replace.keys()`(교체된 이전 ID)도 누적한다. 다음 호출의 `retired_case_ids`로 이 누적 원장 전체를 전달하여 과거 교체 ID를 add로 재사용하는 것도 차단한다.

## 2. 실행 가능한 케이스 분류 정책

`previous`·`current`는 **case-id → 케이스 dict**다. 필수 키는 `ac_id`, `test_file`, `selector`, `expectation`, 선택 키는 `replaces`다. 동일 ID는 dict 내용 전체가 같아야 한다. 이전 교체로 생긴 `replaces` 메타데이터가 그대로 남아 있으면 `keep`이다. `retired_case_ids`는 과거 모든 세대의 은퇴·교체 ID다. 반환 목록은 입력 dict의 순서를 유지한다. `replace`에 든 이전/새 ID는 `retire`/`add`에 중복해서 넣지 않는다. 입력은 변경하지 않는다.

```python
def classify_cases(previous, current, retired_case_ids=()):
    """승인·파일 충돌 검증에 앞서 케이스 변경 종류만 분류한다."""
    required = {"ac_id", "test_file", "selector", "expectation"}
    for cases in (previous, current):
        if not isinstance(cases, dict):
            raise ValueError("케이스 집합은 dict여야 합니다")
        for case_id, value in cases.items():
            if not isinstance(case_id, str) or not case_id:
                raise ValueError("case-id는 비어 있지 않은 문자열이어야 합니다")
            if not isinstance(value, dict) or not required.issubset(value):
                raise ValueError("케이스 필수 필드가 누락되었습니다")
    retired = set(retired_case_ids)
    if retired.intersection(current):
        raise ValueError("은퇴한 case-id는 재사용할 수 없습니다")

    keep = []
    added = []
    replacements = {}
    for case_id, value in current.items():
        if case_id in previous:
            if value != previous[case_id]:
                raise ValueError("같은 case-id의 내용 변경은 새 ID와 replaces가 필요합니다")
            keep.append(case_id)
            continue
        if "replaces" not in value:
            added.append(case_id)
            continue
        old_id = value["replaces"]
        if not isinstance(old_id, str) or old_id not in previous:
            raise ValueError("교체할 이전 case-id가 없습니다")
        if old_id in current:
            raise ValueError("교체한 이전 케이스를 동시에 활성화할 수 없습니다")
        if old_id in replacements:
            raise ValueError("한 이전 케이스를 중복 교체할 수 없습니다")
        replacements[old_id] = case_id

    removed = [case_id for case_id in previous
               if case_id not in current and case_id not in replacements]
    return {"keep": keep, "add": added, "retire": removed,
            "replace": replacements}
```

이 함수의 분류는 승인이나 무결성 통과 판정이 아니다. report/verify에서 실제 파일·케이스 본문·기대값과 대조한다. `(test-file, 정확한 selector)` 중복, selector가 0건/복수 건을 고르는 문제, 경로 정규화 후 파일 소유권 충돌은 차단한다. 같은 파일의 AC는 한 태스크로 묶으며 task merge/split 시 새 active 세대의 단일 파일 소유권으로 재매핑한다. 과거 세대의 은퇴 태스크 hash는 이력으로만 보관하고 현재 파일과 재대조하지 않는다. 현재 파일과 비교할 hash는 현재 active 세대 소유 태스크의 값이다.

## 3. delta RED → IMPLEMENT와 새 세대 검증

1. 오케스트레이터가 승인된 변경표와 기존 테스트만으로 RED 입력을 만든다. Step 2-R의 기존 AC·인터페이스 플레이스홀더를 **실제 해당 AC·case-id·변경 종류·정확한 selector·이전/새 기대값·보존할 본문 스냅샷·허용 파일**로 치환한다. 설명을 report에만 남기고 디스패치에서 누락하지 않는다. red-writer에는 프로덕션 본문·계획 전문을 전달하지 않는다.
2. red-writer는 `add`와 `replace`의 **새 케이스만** 실패하도록 작성한다 (delta RED). `keep`은 본문·기대값·ID·selector 내용 불변이며 GREEN이어야 한다. `replace`의 이전 케이스는 승인된 변경표에 있는 것만 active 집합에서 제거하고 원문·기대값은 이력에 보존한다. `retire`는 명시적으로 승인된 요구사항 삭제/제외에 해당하는 케이스만 은퇴시킨다. 다른 테스트는 수정하지 않는다.
3. verify_red는 변경 전 hash 확인·이력 저장 여부, 승인된 변경표, 실제 selector별 결과를 직접 대조한다. 실패 건수는 `len(add) + len(replace)`이며 `keep` 실패는 회귀다. 컴파일/러너 오류는 RED가 아니다. 모든 테스트가 GREEN이어도 허용 delta 밖 `keep` 본문/기대값 변경이 있으면 차단한다. 최초 구현은 이전 집합이 비어 있으므로 모든 케이스가 `add`이고 기존의 전부 RED 규칙을 적용한다.
4. 통과 후에만 새 `baseline-generation`을 active로 발행하고 해당 세대의 report 경로·active-case-ids·test-file/hash·porcelain를 기록한다. 보고서 작업 경로(`reports/t{N}-red.md`·`reports/t{N}-impl.md`)를 다시 써야 하면 이전 원문을 위 이력에 먼저 보관하며 새 report에 이전 경로·세대 링크를 둔다. `test-count`는 새 active 집합의 기대 케이스 수와 연결하고 이전 값은 이력으로 남긴다. 새 기준선이 검증되기 전 중단되면 `current-step`과 후보 세대 정보를 남기고 기존 active 세대를 유효한 새 세대로 오인하지 않는다.
5. IMPLEMENT는 기존처럼 **테스트 파일 수정 금지**다. 새 active 집합 전부를 focused 실행하여 GREEN을 확인한다. verify_implement는 현재 active 세대의 파일 hash·porcelain·active-case-ids·본문/기대값 스냅샷·실행 수·selector별 결과를 대조한다. 승인된 은퇴/교체 수로 설명되지 않는 케이스 감소·유실·추가·무단 변경은 실패다. 현재 active 세대에 남은 다른 태스크의 hash도 검증한다. 이전 세대 보고·기대값·테스트 원문은 그대로여야 한다.

## 4. 삭제-only·재개·모드 전환

삭제-only(`add`·`replace` 없음)는 production/프로덕션 변경을 자동 허가하지 않는다. 가짜 RED를 만들거나 과잉 구현 정리를 실행하지 않는다. 승인된 테스트 소유권·active 집합 정리는 red-writer만 수행하고, 남은 active 케이스 GREEN 및 **production 소스 변경 전후 동일**을 오케스트레이터가 직접 검증한 뒤 IMPLEMENT를 건너뛴다. 프로덕션 정리가 필요하면 별도 요구사항과 그 동작 변경을 재현하는 새 RED로 시작한다.

개별 태스크의 active 케이스만 0건이면 승인된 retire와 source 불변 검증 후 그 태스크를 은퇴/skip하고 **다른 active 태스크는 계속**한다. 은퇴할 케이스가 있는 태스크는 active 집합이 비었다는 이유로 변경표·red-writer 정리·검증 전에 계획에서 사라지게 하지 않는다. delta가 아예 없는 태스크도 기존 GREEN·무결성만 확인하며 이미 구현된 동작을 억지로 RED로 바꾸지 않는다.

**이번 실행 전체의 active-case-ids 합집합이 0건**이고 승인된 은퇴 정리·다른 테스트 무단 삭제 없음·production 보존 검증을 마쳤을 때만 범위를 종료한다. state.md에 `scope-status: closed`, `current-step: 범위 종료 확인`, `status: in_progress`를 보존하여 기록하고 `return "scope-closed"` 신호로 implement와 전체 Phase 루프를 즉시 중단한다. 이 신호를 일반 Phase 완료로 처리하거나 complete·자동 commit/PR로 체이닝하지 않는다. 기존 변경을 자동 원복하거나 커밋하지 않는다. 다른 active 태스크가 남으면 이 신호를 반환하지 않고 경계 회귀/complete verify 경로를 유지한다.

재개 시 `scope-status: closed` 또는 `current-step: 범위 종료 확인`이면 `return "scope-closed"`로 종료하여 자동 구현·complete를 금지한다. 새 요구 범위를 사용자와 재확정하고 해당 승인·변경표·세대 계약으로 명시적으로 다시 열었을 때만 재개한다. 단순 재개 요청·과거 승인·완료 커서는 새 요구 범위의 재확정이 아니다.

`--resume`은 승인 검증 후 현재 active 세대와 후보 세대의 상태·변경표·이력 링크를 복원하고, 중단된 검증부터 재개한다. 후보 RED 작성 중 중단되어 실제 테스트가 바뀌었으면, 변경 전 hash 검증 기록·불변 원본 hash를 먼저 확인하고 현재 diff가 승인 delta 안인지 keep 본문/기대값·다른 테스트 스냅샷으로 검증한다. 이 경우 정당한 후보 delta가 반영된 현재 파일을 과거 전체 파일 hash와 단순 비교하지 않는다. 기록이 없거나 허용 delta를 벗어나면 중단하며 새 hash를 기준선으로 수용하지 않는다. 과거 task의 완료 표지만으로 새 AC가 구현됐다고 간주하지 않는다. 보안 H3의 AC 추가, 하네스 부재 AC 제외, task merge/split과 core→all 전환에서도 같은 분류·보관·승인·delta RED 순서를 적용한다. core→all은 기존 완료 케이스를 `keep`으로 매핑한 뒤 새 전체 요구사항/설계에서 생긴 케이스만 `add`/`replace`한다. 기존 core 루프를 이어 실행하지 않고 전이된 실제 PHASES를 따른다.

## 5. 활성 태스크 선택 정본

review Mechanical Gate와 공통 `test-execution.md`를 사용하는 단독 verify·complete·commit은 아래 한 계약으로 **`ACTIVE_TASKS`**를 복원한다. 리뷰의 `REVIEW_ACTIVE_TASKS`는 이 집합의 별칭이다. 리뷰를 먼저 실행했다는 전제나 세대 번호 최댓값으로 별도 선택 규칙을 만들지 않는다.

1. state/report에 `baseline-generation`, `active-case-ids`, `previous-task-ids`, `supersedes`, `case-change-report`, `retired-case-ids` 중 하나라도 있으면 세대 계약을 적용한다. 현재 승인된 AC·계획과 각 태스크의 케이스 변경표·불변 이력·승계 연결을 함께 읽어 현재 active 케이스와 파일의 소유 태스크를 복원한다. 각 active case-id/정확한 selector는 한 소유 태스크에만 대응하고 실제 파일·본문/기대값·count와 연결돼야 한다.
2. **영향 없는 이전 세대 소유 태스크는 현재 소유권이 유효하면 ACTIVE_TASKS에 유지**한다. 새 세대가 있는 태스크만 고르거나 이전 세대를 일괄 제외하지 않는다. merge/split·replace/retire로 소유권을 넘긴 태스크는 승인된 변경표와 `supersedes`로 승계가 검증된 경우에만 제외한다. 일부 케이스만 남은 태스크도 그 케이스와 파일의 현재 단일 소유권이 확정돼야 한다.
3. retired/superseded 태스크는 승인된 은퇴/승계 근거와 불변 이력의 원문·hash·기대값만 확인한다. 이 과거 hash를 현재 파일과 비교·현재 RED로 원복·현재값으로 덮어쓰는 행위는 금지한다. 과거 `test-file`이나 source/test 관계를 현재 필수 테스트·소유권 배열에 다시 넣지 않는다. 실제 Git 변경과 영향 분석에서 발견한 경로는 별도로 검증하므로 이 제외를 실제 변경 누락에 사용하지 않는다.
4. 일부 세대 필드만 있거나 승인된 계획과 active 케이스·태스크·파일 매핑이 모호하면 **복구 전 검증을 차단**한다. 승인된 계획·변경표·불변 이력에서 누락된 연결을 복원하며 새 hash로 통과시키거나 케이스 감소를 수용하지 않는다. 다른 테스트의 무단 변경·중복 소유권도 실패다. 전체 폴백으로 이 소유권/무결성 오류를 우회하지 않는다. 후보 세대가 작성 중이면 §3~4의 중단된 검증을 먼저 마쳐야 현재 검증 집합으로 발행할 수 있다.
5. legacy 세션 전체에 세대 메타데이터가 전혀 없으면 모든 기존 태스크를 선택하는 기존 동작을 유지한다. state/태스크가 없는 단독 verify도 기존 실제 변경 기반 선택·보수적 폴백을 유지하며, 기록이 없다는 이유로 범위를 종료하지 않는다. 단독 verify의 새 run-id는 실행 증거의 재사용 키이며 저장된 승인·세대의 원래 run-id를 덮어쓰지 않는다.
6. 승인된 전체 은퇴 정리·다른 테스트 보존·production 불변 검증이 끝난 실제 전체 active 0건만 §4의 `scope-closed`로 중단한다. 단순 빈 목록이나 누락된 기록은 이 신호의 근거가 아니다. `scope-status: closed`를 새 구현·complete·자동 commit/PR로 연결하지 않는다.

복원한 **동일 ACTIVE_TASKS**만 현재 `test-file-hash` 대조, `required-tests.json`의 필수 테스트 경로, `test-ownership.json`의 승인된 현재 source/test 관계에 사용한다. 과거 report는 불변 이력으로 보존한다. 현재 소유권이 확정된 뒤에도 source→test 영향 관계의 근거가 부족하면 기존 공통 테스트 계약의 보수적 전체 폴백을 적용하며, 현재 active 파일 부재나 무단 변경을 이 폴백으로 숨기지 않는다.
