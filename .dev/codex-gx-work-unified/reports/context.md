# gx-context 공통 입력·인계 개선

## 변경

- 신규/문서 입력이 `references/intake.md`의 같은 정규화와 질문 선별을 사용한다.
- 문제·현재 프로세스·사용자/규모·담당·레포를 정보 점검표로 사용한다. 근거 있는 다섯 사실을 다시 확인하거나 전체 align 질문을 반복하지 않는다. 범위·동작·설계 제약·인수 기준이 바뀌는 미정만 묻는다.
- 비차단 미정은 ❓, 사용자가 맡긴 내부 선택은 위임 메시지 포인터로 남긴다. 전체본 대체 범위, 개별 제거, 기존 context 변경과 계획 저장의 명시적 승인 경계는 유지한다. 동일 변경에 이미 받은 실제 승인은 재사용한다.
- 코드 스캔의 관측은 observed-facts로 분리한다. 사용자·문서에서 요청하지 않은 미래 요구를 만들지 않는다.
- 공통 계획 P-0~P-9, 원장 C-4-1의 기존 ID·AC·상태·PR 보존과 전체본 범위 보호는 유지한다. context-only는 원장/계획 정합성 확인 뒤 종료하며 빈 원장에서 요구사항을 추가로 유도하지 않는다.
- 인계는 목표/종료 지점/출처/결정/미정/도메인별 원장 포인터/계획 경로를 포함한다. gx-context가 다른 오케스트레이터를 호출하지 않는다.
- Python 표준 라이브러리 helper는 설치 스킬 내부에 포함된다. 자연어 추출이나 승인 진위 판정을 구현했다고 주장하지 않는다. 모델이 출처를 확인해 추출한 구조를 선별하고 정규화하는 역할이다.

## 검증 증거

1. 구현 전 `python -m unittest discover -s tests -p test_gx_context_workflow.py -v`: 8개 모두 기대한 FAIL. 이유는 공통 intake helper 부재.
2. 최소 helper 구현 후 같은 명령: 8개 PASS.
3. 소비 프로젝트의 별도 임시 디렉토리에서 실제 CLI 실행(한글 UTF-8 입출력, 원본 입력 불변)과 두 모드의 공유 계약/설치 helper 경로 확인을 추가한 최종 실행: 10개 PASS.
4. `python -m unittest discover -s tests -p test_codex_skill_context.py -v`: 34개 중 33 PASS, 1 ERROR. 동시 진행 중인 gx-dev 제거로 기존 `DEV_SETUP` 경로가 없어 `test_context_uses_shared_svn_repository_identity`에서 FileNotFoundError. 부모에게 기존 테스트의 전역 경로 마이그레이션 필요를 전달했다. 실패를 context 검증 성공으로 계산하지 않았다.

행동 검사는 근거 있는 5개 사실의 질문 0건, 중요/비차단 미정 분리, 위임 선택 재질문 방지, 제거 승인 위임 금지, 코드 관측의 미래 요구 승격 방지, 도메인별 같은 FR-1 보존, 실제 승인 source 요구, context-only 종료 경계 보존을 확인한다.

전체 통합 검사와 Claude/Codex 실제 설치·모델·질문 UI smoke는 부모 통합 단계에서 별도 확인한다. 이 보고서의 자동 검사만으로 실제 모델·설치 동작을 입증하지 않는다.

## 후속 reviewer·계획표 개선

reviewer 재현 3개(기존 unresolved 유실, 상충 explicit 결정 무시, 위임으로 차단 미정 삭제)를 먼저 RED로 확인한 뒤 수정했다. 근거 있는 단일 explicit 결정만 기존 미정을 해소하며, 승인 여부만으로 차단 질문을 지우지 않는다. helper는 13검사 GREEN이었다.

업무 계획표 helper `gx-context/scripts/plan.py`를 추가했다. 사용자 요청에 따라 기존 scripts/plan-lint.py의 표·그래프 파서 정본을 설치 helper로 옮기고, 기존 CLI는 같은 함수를 호출하는 호환 wrapper로 유지해 파서 중복을 피했다. 업무표·도메인 원장만 읽으며 gx-work normalized units를 다루지 않는다. 미배정·중복 배정·없는 참조·잘못된 의존·도메인 생략의 모호함을 검사하고, 완료된 의존만 있는 대기 작업을 ready로 계산한다. 일부/전체 폐기와 진행 중 완료 후보는 별도 제안으로 보고하며 ID·상태·작업 위치·원장을 수정하지 않는다. errors가 있으면 ready를 비운다.

새 행동 7개를 helper 부재로 RED 확인한 뒤 최소 구현하여 GREEN. 실제 소비 프로젝트 임시 폴더에서 한글 표를 CLI로 읽고 입력 파일 바이트 불변까지 확인한 최종 context 전체 검사는 21개 PASS다. 기존 plan-lint의 valid/twotables fixture는 exit 0, cycle/badref는 기대한 exit 1로 유지됨을 확인했다. P-2/P-8/P-9에 설치 helper 실행·저장 전/후 검증·다음 할 일 출력을 연결했다.

## 토큰 비용

가장 큰 절감은 반복 질문과 원문 인계 제거다. 새 도메인에서 다섯 사실이 문서에 모두 있으면 기존 5개 확인 질문+전체 align이 공통 선별에서 0개가 된다. 계획 저장 등 아직 필요한 승인은 별도로 유지한다. 후속 에이전트에는 원문·상태표 전문 대신 path/section/domain/ids와 관련 변경분만 준다. P-9의 반복 사용법 안내를 줄였다. 공통 intake 참조와 helper 입력/출력 비용이 추가되므로 정확한 세션 토큰 절감률은 실제 실행 측정 전에는 제시하지 않는다.
