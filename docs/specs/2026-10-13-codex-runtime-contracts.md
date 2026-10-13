# Codex 질문·모델 실행 계약 보완

수정일: 2026-10-13

## 문제와 범위

Codex 기본 모드의 비동기 질문은 등록 후 즉시 반환한다. GX는 실제 답변을 기다리라는 지침만 있어 사용자가 질문을 찾기 어렵고 다음 단계 차단·결정 기록이 실행자의 해석에 의존한다. 모델 배정도 Claude의 opus/sonnet 티어를 보존하지만 Codex 후보는 Astra/5.6 Sol에 머물러 있으며 eco·태스크 리뷰·fix 격상·메인 세션 실행을 함께 검증하는 실행 가능한 정책이 없다.

기존 시각화 작업과 분리해 origin/main 기반 codex/fix-codex-runtime에서 작업한다. Claude Task·질문·게이트는 유지한다. 앱 UI를 강제로 펼치거나 메인 세션 모델·사용자 전역 config·설치 캐시를 변경하지 않는다.

## 설계

### 모델 선택

scripts/codex-model-policy.py가 설치된 역할 index와 프로젝트 .claude/config.json의 선택적 codex.modelTiers를 읽는다. 기본 high는 최신 허용 Astra/low, mid는 최신 허용 Sol/medium이다. 특정 버전명을 기본값으로 고정하지 않고 실제 세션 models의 `gpt-<숫자 버전>-astra|sol` 정식 이름을 숫자 버전으로 비교한다. 요청 effort를 지원하는 같은 계열의 가장 높은 버전을 선택한다. 날짜 snapshot·preview·latest 별칭의 출시 순서를 이름만으로 추측하지 않는다. 계열 부재 시 다른 계열의 최신 허용 모델로 대체하고 사유를 표시하며, 지정한 model override는 기존 고정을 유지한다. family override는 astra/sol과 reasoning_effort로 설정한다.

입력 capabilities JSON에는 실제 세션의 models(모델명→허용 effort 목록)와 parent_model/parent_reasoning_effort만 적는다. 모델 목록은 실행 시점에 갱신하고 과거 세션 파일을 재사용하지 않는다. 계정 권한을 추측하거나 API 모델 목록을 spawn allowlist로 대신하지 않는다. 자동 최신 선택은 자식 배정 정책이며 메인 세션은 현재 사용자가 선택한 모델을 유지한다.

기본 역할 tier → 파이프라인 eco 대상 하향 → 태스크 리뷰 mid 및 TDD implementer fix 4~5 high 예외 순으로 적용한다. architect는 eco에서도 high를 유지한다. 후보와 요구 effort가 모두 허용된 모델만 선택한다. 후보가 없으면 허용 모델 중 해당 effort를 지원하는 모델로 대체하고 사유를 반환한다. 선택 불가 시 exit 2다. session 실행은 부모 모델·effort를 반환하며 eco로 바뀌지 않는 사실을 명시한다.

모델 override에는 fork_turns none과 agent_type 생략 또는 default를 사용한다. 고정 모델을 가진 하네스 역할을 GX 역할 이름의 대용으로 사용하지 않는다. 모델 선택 결과는 계획이며 실제 사용량·관측 모델로 오인하지 않는다. 오케스트레이터는 요청 배정과 실제 spawn 인자, 확인 가능한 하네스 결과를 model-dispatches.jsonl에 구분해서 기록한다.

### 질문과 재개

scripts/codex-question.py는 register/answer/status 명령으로 .dev/<현재 작업>/pending-question.json을 관리한다. 모든 질문은 stable snake_case id, 본문, 선택지와 현재 phase를 갖는다. 응답이 필요한 질문은 등록 → 질문 도구 호출 또는 자연어 표시 → 실제 답변 확인 → 결정 기록 → 해제 순으로 진행한다. 등록·도구 반환·추천 항목 preselection·시간 경과는 답변이 아니다.

async의 questions는 title/options 문자열 형식으로 변환하고 id·header는 로컬 pending 기록에 보존한다. 질문 본문과 선택지가 사용자가 볼 수 있는 응답에도 남게 한다. 필요한 정보·승인 질문은 도구의 용도 제한을 먼저 확인하며, 해당 도구가 승인 또는 필수 질문을 지원하지 않으면 자연어로 질문하고 턴을 종료해 실제 응답을 기다린다. 현재 Default에서 Plan 전용 동기 도구는 호출하지 않는다. 앱 UI 팝업을 제어한다고 주장하지 않는다.

status는 미응답일 때 exit 2를 반환한다. 의존 작업·다음 phase 직전에 상태를 확인한다. 독립 작업이 끝났는데 답변이 없으면 질문과 대기 사유를 포함해 턴을 종료한다. 무인 실행은 필수 질문에서 BLOCKED를 보고한다. 재개 시 pending 질문을 먼저 복원한다. answer는 실제 사용자 답변에 같은 질문 id와 register의 question_set_id를 붙인 입력만 받아 decisions.md에 기록한 뒤 pending을 해제한다. 실패·불완전 답변·다른 id·stale token은 해제하지 않는다. 선택적 질문과 이미 제공된 승인에는 불필요한 재질문을 만들지 않는다. 완료 영수증과 답변 digest로 재시도 중복을 방지한다.

기존 capture_decision.py와 Codex PostToolUse matcher는 async 도구명도 인식하되 질문 등록 ack에 답변이 없으면 기록하지 않는다. async 원시 입력에 stable id가 없는 경우에는 pending의 정규화된 질문과 실제 응답을 명시적으로 answer에 전달한다. Claude의 기존 동기 기록 경로는 유지한다.

### 배포·문서

공통 codex-runtime에서 모델/질문 상세 참조와 설치 루트 helper를 연결한다. dev·tdd·context 및 단독 스킬의 질문 적응 안내는 공통 계약을 따르게 한다. dev·tdd setup·프로파일 선택의 사용자 안내는 Claude와 Codex로 구분한다. gx-setup은 선택적 모델 설정을 기존 config 보존 방식으로 안내한다. Ralph eco는 미지원 상태를 유지하고 Codex식 안내를 추가한다.

## 수용 기준과 검증

1. dev/tdd standard/eco 역할 전체, architect 유지, task reviewer mid, fix 4~5 high를 실행 가능한 테스트로 검사한다.
2. allowlist·effort 미지원, 후보 부재, 사용자 override, 메인 세션 경로를 검사한다.
3. unanswered/ack/빈 답변/다른 id/부분 답변은 질문 상태를 해제하거나 결정으로 기록하지 않는다. 실제 답변은 한 번 기록되고 같은 phase에서 재개된다.
4. 질문의 숨은 UI·Plan 전용 도구·승인 용도 제한·헤드리스 처리와 재개 계약이 배포 참조에서 도달 가능하다.
5. sync-codex-resources --check, test_codex_*.py, hook-tests, lint-consistency를 통과한다. Windows 검사는 Git Bash를 명시한다.
6. skill-creator의 기존/개선 계약 비교 평가를 보존하고, 실제 앱 UI·인증 모델 세션과 구분해서 보고한다. 실제 소비 프로젝트 smoke 미실행은 PASS로 치환하지 않는다.

## 상태

- [x] 설계와 범위 확정
- [x] 모델 정책 구현·검증
- [x] 질문 대기·기록 구현·검증
- [x] 배포 문서·사용자 안내 동기화
- [x] 비교 평가·리뷰·회귀 검사
- [x] 커밋·PR 제출 준비 (검증·리뷰 통과)
