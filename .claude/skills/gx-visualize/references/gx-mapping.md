# GX 산출물 매핑

입력 수집기와 IR 작성자가 공유하는 논리 그룹의 정본이다. 실제 파일명이 다르면 문서 제목·공식 산출물 ID로 동등성을 확인하고, 확인 근거 없이 비슷한 파일을 대신 고르지 않는다.

## 산출물에서 IR로

| 논리 그룹 | 기본 파일·동등 산출물 | IR 변환 | 주 사용 view |
|---|---|---|---|
| `prd` | `prd.md`, AN-02 요구사항정의서 | `requirement` 노드와 공식 요구사항 ID | `trace` |
| `design` | `design.md`, AN-03 기능명세서 | `function`, `service`, 명시된 `sequence` 관계 | `trace`, `impact`, `service`, `sequence` |
| `codemap` | `codemap.md` | 파일 근거가 있는 service/screen/api/table 후보 | `impact`, `service` |
| `state` | `state.md` | Phase·Gate·상태 노드 | `progress` |
| `diff` | `diff.txt` | `added`, `removed`, `changed`, `moved` 관계 | `impact` |
| `DE-08` | DE-08 테이블정의서 | `table`·`data` 노드와 function의 데이터 관계 | `trace`, `service` |
| `DE-13` | DE-13 단위테스트계획서 | `test` 노드와 `verifies` 관계 | `trace` |
| `summary` | `summary.md` | 완료·미완료 근거 카드 | `progress` |
| `self-check` | `self-check.md`, `trust-ledger.md` | 검증·Gate 근거 카드 | `progress` |
| `context` | 프로젝트 `context/`의 명시적 아키텍처 자료 | 확인된 경계·용어·관계 | `service` |
| `call-evidence` | 설계서의 sequence, 코드·테스트의 명시된 호출 근거 | 순서 edge와 파일·라인 근거 | `sequence` |
| 진입점 체인 스캔 | `scripts/scan_entrypoints.py`의 스캔 결과 | `service`/`sequence` 뷰의 screen·api·service·repository·table 노드와 code 근거 | `service`, `sequence` |

각 evidence는 [IR 계약](ir-contract.md)에 따라 실제 파일과 텍스트 line 또는 비텍스트 locator를 가리킨다. source가 관계를 선언하지 않으면 이름의 유사성만으로 edge를 만들지 않는다.

## view별 필수·보조 입력

| view | 필수 논리 그룹 | 보조 그룹 | 누락 처리 |
|---|---|---|---|
| `trace` | `prd`, `design`, `DE-08`, `DE-13` | `codemap` | 누락 그룹을 기록하고 확인 가능한 체인만 생성 |
| `progress` | `state` | `summary`, `self-check` | 상태 정본이 없으면 failed, 보조 누락은 부분 표시 |
| `impact` | `diff` | `codemap`, `design` | diff가 없으면 failed, 근거가 있는 변경만 표시 |
| `service` | `codemap` 또는 `design` | `DE-08`, `context` | 둘 다 없으면 failed; 런타임 토폴로지는 추정하지 않음 |
| `sequence` | `design` 또는 `call-evidence` | `codemap` | 둘 다 없으면 failed; 호출 순서를 추정하지 않음 |

`collect_inputs`는 찾은 파일을 프로젝트 루트 상대경로로 `files`에 넣는다. `missing_inputs`에는 충족되지 않은 필수 논리 그룹만 넣고, 보조 그룹은 `missing_inputs`에 넣지 않는다. `A 또는 B` 필수 조건은 후보 중 하나 이상을 찾으면 충족이며, 모두 없을 때만 표의 합성 그룹명(`codemap|design`, `design|call-evidence`)을 넣는다. 두 배열은 중복을 제거하고 사전순으로 정렬한다.

## 영수증 상태 정규화

최종 report의 `validation_status`는 다음 세 상태만 사용한다. 저수준 validator/renderer receipt는 구현 계약에 따라 `valid`, `fallback`, `not_applicable`, `failed`를 사용할 수 있다.

| 상태 | 판정 | 사용자에게 보고할 내용 |
|---|---|---|
| `verified` | IR이 valid이고 선택된 백엔드가 non-empty HTML을 만들었으며 경로가 receipt와 일치 | 실제 backend, 세 산출물 경로, 누락 입력 |
| `fallback` | 선호 백엔드가 없거나 실패했지만 Mermaid 또는 static이 같은 IR로 검증 가능한 HTML을 생성 | 실제 backend와 원래 실패 진단·시도 순서 |
| `failed` | IR 검증 실패, 모든 렌더 실패, HTML 부재·빈 파일, 또는 receipt 불일치 | 실패 이유, 누락 입력, receipt 경로, 재실행 명령 |

저수준 `not_applicable`(요청한 view에 Archify 변환기가 없어 애초에 시도하지 않음 — 예: `trace`/`progress`/`impact`/`sequence`)도 `fallback`으로 정규화한다. Archify가 실패한 게 아니라 대상이 아니었다는 구분은 report를 새 값으로 늘리지 않고 `backend`(`mermaid`|`static`)와 receipt의 `attempts` 배열(첫 항목이 `not_applicable`)로 남긴다.

`valid` receipt는 위 추가 검사를 모두 통과한 뒤에만 `verified`로 올린다. `fallback` receipt를 `verified`로 바꾸거나 실패한 Archify를 실제 backend로 보고하지 않는다.
