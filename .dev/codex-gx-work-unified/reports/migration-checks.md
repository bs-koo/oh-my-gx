# gx-dev 제거 후 검사 마이그레이션

## 수정 범위

- `scripts/lint-consistency.sh`: 36개 번호 유지. #12의 폐지된 dev/core 실행기 검사를 gx-work 배포 디렉토리·공통 런타임·계획/인계 포인터·종료점·두 번째 실행루프 부재로 교체. 실행기 공통 게이트는 유일한 gx-tdd에 유지. TDD roles-and-phases, setup/cross-review/humanizer의 정확한 조건부 참조를 bundle로 검사한다.
- `scripts/codex-model-policy.py`: 폐지된 gx-dev pipeline 분기 제거. 지원하지 않는 pipeline을 계속 허용하지 않도록 행동 테스트 추가.
- 기존 `test_codex_skill_pipeline/layout/questions/context`, `test_codex_dev_ignore_check`, `test_codex_model_policy`: 실행 계약은 TDD bundle로 한정, gx-work entry/공통 리소스 이동은 별도 검사. 문서·코드 근거가 바뀐 기대값만 교체.
- `test_gx_arch_pipeline`, `test_gx_visualize_routing`: TDD completion 계약을 유지하고 단일 gx-work→gx-tdd 인계를 별도로 검사. visualize 번들 참조 검사는 조건부 본문 추출에 맞춰 통합 중.
- 새 worker 전용 tests/test_gx_work.py, tests/test_gx_test_plan.py, tests/test_gx_work_migration.py는 수정하지 않았다. context helper 회귀는 부모의 후속 지시로 전용 tests/test_gx_context_workflow.py에 추가했다.

## 의미를 유지한 교체

옛 baseline.done 정규식 근사 검사는 현재 실행 계약에 없는 알고리즘이어서 실제 gx-test-plan helper의 proof 동작 검사로 교체했다. 성공 결과의 같은 run 재사용, 다른 run 거부, 로그 변조 거부, 0건 기록 시 이전 성공 무효화를 실제 임시 Git 저장소에서 확인한다. 전체 테스트 선실행/반복 기대는 영향 범위 확정 후 plan/reuse/record와 명시적 전체 폴백 조건으로 교체했다.

## 검증

- model-policy 새 거부 검사 RED: 기존 helper에서 gx-dev가 허용되어 실패함을 확인. 분기 제거 후 아래 focused 실행에 포함되어 GREEN.
- 1차 focused 대상 9파일/182검사: 26 FAIL/5 ERROR. 대부분 Windows WSL bash 선택 실패, 두 곳은 단일 TDD 배열 전환 후 인덱스/비교 테스트 자체 보정 필요였다. 실제 기대 변경은 explore 부트스트랩·baseline/테스트 영향계획·runtime 이동이었다. 원본 로그 `focused-migration.log`에 보존했다.
- Git Bash를 PATH 앞에 둔 2차 실패 대상 focused 3파일/73검사: 71 PASS, 2 FAIL. 부모 수정 대기인 gx-tdd 하단 Phase선택의 옛 [setup,...] 설명과 codex-smoke Q2 gx-dev 표기다. `focused-migration2.log`에 증거가 있다. 전체 Codex 스위트는 반복 실행하지 않았다.
- `bash -n scripts/lint-consistency.sh`: PASS. 실제 Bash는 `C:/Program Files/Git/bin/bash.exe`로 지정했다. Windows 기본 bash.exe는 WSL을 가리켜 실행할 수 없다.
- 린트 1차 전부 실행 후, 실패 관련 #12/14/16/19/20/24/25/32/34만 focused 실행했다. 자체 검사 경로·bundle·기대값은 보정했다. 남은 공통 경로 전환과 phase-setup 22KB 예산은 부모 통합 수정 후 전체 린트에서 확인해야 한다. 예산이나 보호 조건은 완화하지 않았다.

## reviewer 회귀

부모가 전달한 intake P1(기존 unresolved 유실), P2(상충 explicit 결정 통과)는 전용 행동 3개 RED 후 수정했다. 기존 차단 미정을 보존하고 승인·내부 위임으로 지우지 않는다. 근거 있는 단일 explicit 결정만 해소하며 충돌한 출처는 질문으로 남긴다. 현재 context 행동+CLI 검사 13 PASS.

소비 프로젝트 실제 설치·질문 UI·실제 모델 smoke는 이 정적/단위 검사로 입증하지 않는다. 부모가 최종 전체 Codex 검사·배포 동기화·전체 린트를 한 번 수행한다.
