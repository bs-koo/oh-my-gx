# 구현 단계의 재계획·복구·재개 절차

[phase-implement.md](../phases/phase-implement.md)에서 아래 조건일 때만 Read한다. 첫 실행 경로(문서 로드 → 기준선 → 분해·승인 → RGR → 완료 보고)에는 필요 없다. 케이스 분류·기준선 세대·활성 태스크 선택의 정본은 [core-replanning.md](core-replanning.md)이고, 이 파일은 그 계약을 implement의 각 Step에 적용하는 방법만 담는다. Step 번호는 phase-implement.md 기준이다.

| 조건 | 절 |
|---|---|
| 문서·AC·계획·케이스가 바뀌는 재계획(보안 수리 H3, 하네스 게이트의 AC 제외, task merge/split, core→all, 리뷰·verify에서 구현 복귀) | §1 |
| 레이어별 하네스 게이트에서 "해당 AC 제외 후 진행" | §2 |
| `--resume`으로 implement에 재진입 | §3 |

## 1. 재계획 공통

[core-replanning.md](core-replanning.md)를 Read한다. 문서가 바뀌어도 기존 RED·테스트·report·`test-file-hash`·`test-count`·porcelain·기대값 스냅샷을 먼저 불변 이력에 보관한다. 변경 전 active 세대 hash를 확인한 뒤 케이스를 keep/add/replace/retire로 분류하고 영향 태스크만 새 `baseline-generation`으로 재개한다. add/replace의 새 케이스만 RED, keep은 본문·기대값 불변 GREEN이며 retire는 승인된 범위만 정리한다. task merge/split은 새 active 세대 소유권으로 매핑하고 과거 태스크 hash는 이력으로만 남긴다. 이 계약은 전체 모드·core→all·보안 수리·AC 제외·재개에도 적용한다. 재승인만으로 진행 중 RED가 GREEN인 것처럼 처리하지 않는다. 기준선 사전 실행의 `baseline-fingerprint`와 plan/proof·로그도 보존하며 Step 0.5의 현재 run·코드·설정·명령·범위 일치 조건으로 재사용을 판단한다.

**리뷰 4a 복귀의 변경표 승인**: phase-review 4a 기본 RGR 수정의 Ruling(승인된 범위 안에서 결함 케이스만 `add`하는 변경표)은 변경표 승인으로 본다 — 다시 묻지 않는다. 기존 AC 문구·범위를 바꾸거나 `replace`·`retire`가 필요하면 4a 예외(묻는다)로 처리하고 그 실제 응답을 승인으로 쓴다.

**RED 입력 치환 (Step 2)**: 재계획 입력은 케이스 변경표로 실제 치환한다. 기존 `{태스크가 매핑된 AC 시나리오}`에는 keep/add/replace/retire별 case-id·AC-ID·정확한 selector·이전/새 기대값·허용 파일·본문 스냅샷과 세대 링크를 함께 넣는다. 초기 구현은 previous 집합이 빈 경우로 명시한다. report↔state의 `baseline-generation`·`active-case-ids`·`previous-task-ids`/`supersedes`와 실제 selector가 서로 복원 가능해야 한다. 파일/selector 충돌은 디스패치 전에 차단한다. 완료 태스크에 새 AC가 붙어도 기존 keep을 다시 실패시키지 않는다.

**verify_red 추가 대조 (1·6번)**: 공통 계약대로 변경 전 active hash 확인·불변 이력 보관·변경표 승인을 확인하고 case-id/AC-ID/정확한 selector·이전/새 기대값과 실제 파일을 대조한다. 중복 selector·0건/복수 건 선택·파일 소유권 충돌·승인되지 않은 본문 변경은 실패다. 해시 기록 때는 이전 report·hash·porcelain·test-count·본문/기대값을 불변 이력에 먼저 보관한 후 새 `baseline-generation`·`active-case-ids`·`previous-task-ids`/`supersedes`·`case-change-report`로 연결한다. active 발행 시 `retired-case-ids`에 retire와 replace의 이전 ID를 누적한다. 감소/교체를 새 hash로 숨기지 않는다.

**verify_implement 4번의 count 비교**: 재계획의 새 값 채택은 승인된 케이스 변경표·이력 보관·새 active 세대 발행이 검증됐을 때만 허용한다. 이전 count와 새 count의 차이는 add/replace/retire 및 태스크 소유권 재매핑으로 정확히 설명되어야 한다. 파일에 기존 비태스크 테스트가 있으면 그 목록도 보존하여 focused 전체 수와 별도로 `active-case-ids`의 정확한 selector별 누락·중복·결과를 대조한다. 해시가 갱신됐다는 이유만으로 케이스 감소를 수용하지 않는다.

**보안 수리 H3의 "자동 수정 시도"**: 변경 전 active hash 확인·불변 이력 보관을 먼저 한다. 기존 승인 무효화 후 보안 항목을 ac.md의 새 G-W-T AC로 정의하고 plan.md의 영향 태스크·파일·테스트 및 keep/add/replace/retire 매핑을 갱신한다. 두 문서를 함께 재승인받아 RGR 사이클에 재진입한다: red-writer(add/replace 새 케이스만 delta RED, keep 본문·기대값 불변 GREEN) → IMPLEMENT(세션 또는 implementer) 순서로 수정한다(Step 2-R/2-I 재실행). 기존 report·기대값·해시 이력과 영향 없는 태스크는 보존하고 새 baseline-generation으로 영향 태스크만 재개한다.

## 2. 하네스 게이트의 AC 제외

기존 케이스가 있으면 문서·테스트 변경 전 §1대로 active hash 확인·불변 이력 보관을 먼저 한다. 핵심 모드는 기존 승인을 무효화한 뒤 ac.md에 제외 표시하고 plan.md의 retire 변경표까지 갱신하여 두 문서를 함께 재승인받는다. 전체 모드도 승인된 제외 범위를 변경표에 명시한다. 이후 red-writer만 승인된 active 집합을 정리하고 태스크를 복원한다. 제외 항목은 `${DEV_DIR}/trust-ledger.md`의 `### 위험 수용`에 `- [하네스 부재 AC 제외] {AC-N}: {레이어} 러너 없음 (implement/Step 0.5)` 형식으로 기록한다. 삭제-only는 가짜 RED·프로덕션 변경을 허가하지 않으며 남은 active GREEN과 source 불변을 검증한다. 진행 중 `baseline-fingerprint`와 기존 plan/proof도 지우지 않고 현재 실행 증거의 재사용 조건으로 판단한다.

AC 제외로 범위가 비면 다음 Phase로 넘기지 않는다(기존 변경 자동 원복·커밋 금지). 승인된 retire 정리·production 보존 검증을 마친 뒤 **이번 실행 전체 active 케이스가 0건일 때만** `scope-status: closed`, `current-step: 범위 종료 확인`, `status: in_progress`를 기록하고 `return "scope-closed"`로 전체 루프를 중단한다. 해당 레이어/태스크만 0건이고 다른 active 태스크가 있으면 그 태스크들은 계속한다.

## 3. 재개 (`--resume`)

`scope-status: closed` 또는 `current-step: 범위 종료 확인`은 아래 일반 재개 분기보다 우선한다. `status: in_progress`를 유지한 채 `return "scope-closed"`로 전체 Phase 루프를 끝내며 자동 구현·complete·commit/PR를 금지한다. 새 요구 범위 재확정·승인과 세대 재개를 명시적으로 거친 뒤에만 다시 연다. 개별 은퇴 태스크의 active 0건을 전체 범위 종료로 오인하지 않는다.

핵심 모드는 [core-planning.md](core-planning.md)로 ac.md·plan.md의 현재 승인 일치를 확인한다. 문서나 승인 필드가 없거나 불일치하면 phase-requirements의 계획·함께 승인으로 복귀하고, 유효하면 승인된 태스크 매핑과 기존 RED·무결성 기준선을 복원해 영향 태스크만 재개한다. 결합승인·실제 방법 선택과 기존 Step 1.2~1.3의 동일 run·계획 해시·출처 연결을 검증하고 부족한 방법만 보완한다. `current-step`만으로 승인 검사를 생략하지 않는다.

모든 모드에서 [core-replanning.md](core-replanning.md)로 active/후보 baseline-generation·케이스 변경표·이전/새 기대값·ID 원장·불변 이력 링크를 복원하고 현재 active 소유권의 hash부터 검증한다. 후보 RED 작성 중 중단되었다면 변경 전 hash 검증 기록·이력 원본 hash와 승인 delta/keep 본문 보존을 먼저 대조하며, 정당한 후보 delta를 과거 전체 파일 hash 불일치로 오인하지 않는다. 재계획 중단은 이전 완료 task를 새 AC 완료로 간주하지 않으며, merge/split 후 superseded 태스크 hash를 현재 파일과 재대조하지 않는다. RED 재개는 add/replace만, keep은 내용 불변 GREEN, retire는 승인 범위만 정리한다. 삭제-only/active 0건은 IMPLEMENT를 시작하지 않는다. core→all 뒤에는 전이된 실제 PHASES와 전체 모드 요구사항·설계에서 확정한 변경표로 이어간다.

일반 중단 지점 재개 전에는 setup-resume 0.05의 진입 승인·현재 계획 해시·방법/flags도 검증한다. 유효한 같은 run·계획의 선택은 재사용하고, 부족한 계획 검토/방법만 Step 1.2~1.3에서 확정한 후 아래 중단 지점으로 돌아온다. 완료된 RED·태스크/보고서·fix 카운터는 보존한다. 독립 갈래 병렬 중이었으면 `current-step` 하나로 정하지 않고 각 태스크의 `red`·`impl`·`fix-round` 기록으로 갈래마다 다음 단계를 정한다.

- `"기준선 게이트"` → Step 0.5부터 재실행
- `"하네스 준비 대기"` → Step 0.5의 레이어별 하네스 게이트부터 다시 확인한다. 러너가 아직 없으면 같은 질문으로 멈춘다.
- `"태스크 분해 승인"` → 저장된 내부 계획·해시를 읽어 Step 1.2부터 재개. 유효한 계획 전체를 다시 분해하지 않는다.
- `"실행방법 선택"` → Step 1.3에서 원래 미응답 질문을 복원한다.
- `"계획 문서로 종료"` → 미구현 상태와 계획 경로를 보고하고 Step 1.2 질문을 다시 제시한다. 현재 세션/서브에이전트 응답이면 같은 계획의 Step 1.3에서 이어 가고, 다시 문서 종료·무응답이면 종료한다.
- `"RGR T{N}: RED"` → 해당 태스크의 RED부터 재시작
- `"RGR T{N}: IMPLEMENT"` → state.md `flags`에 `--isolated`가 있으면 implementer 재디스패치, 없으면 세션이 `reports/t{N}-red.md`를 읽고 "세션 IMPLEMENT 절차"를 처음부터 재개 (report 파일이 있으면 그 진행분을 반영)
- `"RGR T{N}: FIX R{r}"` → 해당 태스크의 fix loop 라운드 {r}부터 재개 (report 파일이 영속 기억). fix loop 절을 디스크에서 다시 읽는다.
- `"RGR T{N}: REVIEW"` → Step 2-V 판정부터 재실행 (변경 파일·태스크 diff 재수집 후 디스패치)
- `"RGR T{N}: REVIEW R{r}"` → 라운드 {r}의 수정 diff 재수집 후 재리뷰부터 재개 (`reports/t{N}-review.md`가 이전 findings의 영속 기억)
- 구 세션 호환: `"RGR T{N}: GREEN"`/`"RGR T{N}: REFACTOR"`(3석 세대) → 해당 태스크를 위 IMPLEMENT 규칙(`flags`에 따라 세션 또는 implementer)으로 이어받는다. red 산출물(테스트 파일)은 유효하므로 RED 재실행 불필요. reports/가 없으므로 이 재개에 한해 테스트 코드·실패 메시지의 인라인 인계를 허용하고 execution-log에 "구 세대 전환 재개 — 인라인 인계"를 기록한다. 구 세션 state에 `test-file` 기록이 없으면 RED 산출물과 실제 파일을 대조해 현재 태스크 경로를 복원한 뒤 공통 `focused` CLI를 사용한다. 복원이 불가능하면 필요한 경로를 확인할 때까지 중단하며 전체 `test`로 자동 폴백하지 않는다. `test-file-hash`·porcelain 스냅샷은 구 state에 기록이 있으면 그대로 대조하고 없을 때만 생략한다. `test-count`는 정의가 달라(전체 vs focused) 비교하지 않고 재측정한다
- `"경계 회귀 수리"` → Step 3.5부터 재실행 (전체 테스트 재확인 후 수리)
- `"변경사항 수집"` → Step 5부터 재실행
