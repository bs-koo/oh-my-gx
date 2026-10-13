# Codex 질문·모델 실행 계약 보완 검증

수정일: 2026-10-13

## 변경 결과

기본 모델 정책은 최신 허용 Astra/low·Sol/medium 자동 선택이며, 실제 세션의 spawn allowlist와 요청 effort만 사용한다. 프로젝트 `codex.modelTiers.family` 자동 선택 및 `model` 고정 override와 후보 부재의 대체 사유를 반환한다. dev/tdd의 eco 대상, architect 유지, task reviewer mid, TDD fix 4~5 fresh high, 부모 세션 구현을 함께 계산한다. 역할 없는 setup·complete는 부모 세션 정보로 따로 기록한다.

필수 질문은 stable id와 질문 세트 token으로 등록하고, 실제 답변 기록 전 원래 phase를 유지한다. async 등록 ack·추천 항목·빈/부분 답변은 결정을 만들지 않는다. 답변 저장 후 실패의 재시도는 결정 digest로 중복을 방지한다. 완료 영수증은 같은 token이 명시된 이벤트만 억제하며, 이후 독립 질문을 과거 답변의 중복으로 지우지 않는다. Claude 기존 capture와 Codex 질문 도구 용도 제한은 유지한다.

설계는 [실행 계약 설계서](../specs/2026-10-13-codex-runtime-contracts.md), 배포 정본은 [Codex 실행 규약](../../.claude/skills/gx-dev/references/codex-runtime.md)이다. 모델·effort 설정은 [공식 하위 에이전트 문서](https://learn.chatgpt.com/docs/agent-configuration/subagents)의 설정 우선순위와 실제 세션의 도구 스키마를 대조했다. 모델 선택 결과는 요청 계획이며 실제 관측 모델과 구분한다.

## 실행 증거

Windows PowerShell에서 Git for Windows의 Bash를 명시했다. Python 3.10 stdlib를 사용하며 별도 라이브러리 설치 없이 검사했다.

| 검사 | 결과 | 범위 |
|---|---|---|
| `python scripts/sync-codex-resources.py --check` | PASS | 역할 index·setup 템플릿 드리프트 없음 |
| `python -m unittest discover -s tests -p 'test_codex_*.py' -q` | 200 tests, OK | 역할 matrix·모델 정책·질문·capture·배포·기존 Codex 계약 |
| 최종 질문 회귀 `test_codex_question_gate.py` | 17 tests, OK | token·pending·부분/빈 응답·재시도·독립 질문 기록 |
| 최종 결정 기록 회귀 `test_codex_decisions.py` | 17 tests, OK | 현재 작업 소유권·async ack·기존 동기 capture |
| `bash scripts/hook-tests.sh` | PASS, 6개 그룹 | 기존 Claude/Codex 보호·capture 회귀 |
| `bash scripts/lint-consistency.sh` | PASS, 36개 항목 | 양 하네스 대응·모델 프로파일·상대경로·지시문 예산 |
| `git diff --check` | PASS | 공백·패치 오류 없음 |

최초 린트는 공통 질문 안내에서 실제 도구명을 제거한 점과 tdd setup의 바이트 예산을 차단했다. 모드·용도 제한을 명시한 도구명을 복원하고 공통 모델 문서로 설명을 모아 최종 검사에 통과했다. 상한을 늘리거나 검사 항목을 삭제하지 않았다. 전체 검사 이후 리뷰 보완으로 바뀐 질문·기록 코드는 해당 두 회귀를 다시 실행했다.

## 자동 최신 모델 선택 후속 검증

사용자 후속 요청에 따라 고정 기본 모델명을 계열별 최신 허용 모델 선택으로 바꿨다. 요청 effort를 지원하는 정식 숫자 버전을 비교하며 `family` 자동 선택과 `model` 고정을 구분한다. 날짜 snapshot·preview·별칭·미래 명명 규칙의 순서를 추측하지 않고 메인 세션을 교체하지 않는다. 새 버전 fixture는 정렬 테스트 입력이며 실제 출시·계정 접근을 주장하지 않는다.

모델 정책 35개, 리소스 동기화, 정합성 린트 36개, diff 검사는 통과했다. 로컬 전체 209개 실행은 기존 CLI 러너의 5초 제한과 Ralph의 30초 제한에서 2개가 시간 초과였다. CLI 러너는 개별 재실행에서 통과했다. Ralph는 원본 테스트/러너를 바꾸지 않고 진단 실행의 제한만 90초로 늘려 같은 assertion을 확인했으며 30.261초에 통과했다. 이를 기본 30초 제한을 사용한 전체 209개 PASS로 표시하지 않는다. 모델 선택 후속 리뷰에서 조치할 결함은 없었다.

## Astra low 후속 검증

사용자 요청에 따라 기본 high 모델 티어의 추론 강도를 high에서 low로 바꿨다. 최신 허용 Astra 선택, architect 유지, TDD fix 4~5 fresh agent 격상에 같은 low 기본값을 적용한다. Sol은 medium, 명시적 프로젝트 effort override와 부모 세션은 기존 설정을 유지한다. 역할 matrix와 fix 4~5의 실제 spawn 인자, low 미지원 시 대체·중단을 확인했다.

모델 정책 35개, 리소스 동기화, 정합성 린트 36개, diff 검사는 통과했다. 로컬 전체 209개는 597.862초에 기존 Ralph의 trailing 계약 검사 30초 시간 초과와 CLI 러너의 자식 프로세스 종료 검사 실패를 보고했다. 변경하지 않은 두 테스트를 개별로 함께 재실행해 27.613초에 모두 통과했다. 전체 209개 로컬 실행을 PASS로 표시하지 않는다.

## Skill Creator 비교 평가

아래 비교 점수는 이전 Astra/high 정책 당시의 평가 결과다. 현재 평가 fixture의 자식 Astra 기대값은 후속 요청에 맞춰 low로 갱신했으며 기존 점수를 새 정책 재평가 결과로 사용하지 않는다.

기존 main 스킬을 별도로 보존하고 동일한 두 시나리오를 기존·개선 계약에 적용했다. [평가 프롬프트·기대 결과](../../tests/fixtures/codex-runtime/evals.json)를 저장했다. 질문 시나리오는 Default의 필수 설계 승인·미응답·수정 요청 재개, 모델 시나리오는 tdd eco와 기본/isolated 구현·태스크 리뷰·fix4·dev coder·Astra 부재다.

평가 결과와 정량 판정은 비교 workspace에 보존하고 Skill Creator의 정적 review viewer로 확인할 수 있도록 만들었다. 이 평가는 계약 적용과 격리 fixture helper 실행을 검사한다. 실제 앱 UI 클릭·질문 자동 펼침·인증된 모델 호출을 검사한 것이 아니다. 토큰·청구 비용·모델별 지연 시간은 NOT_MEASURED이며 비교 지표로 제시하지 않는다. 한 시나리오당 각 계약 1회이므로 반복 실행 신뢰도나 광범위 성능 개선으로 해석하지 않는다.

| 시나리오 | 기존 계약 | 개선 계약 |
|---|---|---|
| 필수 질문·대기·재개 | 4/6 | 6/6 |
| 표준/에코 모델·예외 | 5/8 | 8/8 |

기존 계약에도 승인 전 진행 금지·architect 유지·세션 상속·fix 격상은 있었다. 실패 항목은 턴 종료와 질문 세트 token, 최신 Sol 우선 배정의 명확성이다. 개선 평가 출력의 optional async 예시가 승인 선택지를 재사용한 표현상 모순은 평가자 지적 후 삭제하고 correction_note를 남겼다. 이 정정은 실제 필수 승인의 자연어 대기 경로를 바꾸지 않는다.

## 리뷰와 한계

읽기 전용 리뷰의 P2 2건을 보완했다. 완료 영수증이 이후 독립 동기 질문을 숨기는 문제는 token 식별을 요구하도록 수정했고, 동일·다른 질문 세트의 이벤트를 임시 fixture로 재검증했다. 역할 없는 인라인 단계를 helper role로 전달하면 실패하는 문서/API 불일치는 기록 절차를 분리했다. 재검토에서 미해결 사항은 없었다.

helper는 오케스트레이터가 제공한 capabilities·실제 사용자 응답의 정규화 입력에 의존한다. 앱 팝업을 제어하거나 사용자 이벤트 진위를 증명하지 않으며 하네스 모든 도구를 강제로 차단하지 않는다. [실제 소비 프로젝트 smoke](../../tests/codex-smoke.md)의 Q3/Q4/M1~M3는 미실행으로 유지했다. 사용자 전역 Codex 설정·설치된 1.32.0 캐시·기존 시각화 작업은 이번 변경 대상에서 제외했다.
