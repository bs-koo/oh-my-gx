# 개발 문서 수명주기 통합

## 기존 결함 지도

기준: 작업트리 gx-work-unified의 시작 HEAD b6542ee.

- gx-tdd phase-setup의 3.0.5는 `--work`/기존 계획이 없으면 등록을 생략했고, 기존 PROJECTS의 레포 매칭만으로 DOMAIN_CONTEXT를 찾았다. 직접 requirements·부분 phase·재개에서도 관련 context/요구사항/W계획 대조를 보장하지 않았다.
- setup-work는 없는 W 계획에서 중단하거나, W행 연결을 거절/매칭하지 못하면 계획 없이 구현하도록 진행했다. `ARGS[0]`도 W 작업명으로 교체했다.
- phase-complete는 verify/proof/fingerprint → 인수 → commit/PR → status/plan/context 반영 순서였다. `.dev`만 지문에서 제외하므로 뒤늦은 context/status 쓰기가 방금 얻은 증거를 오래된 것으로 만들었다.
- 기존 W 완료는 행 존재만으로 처리했고, 원장의 과거 ✅를 재사용하는 버그 수정과 이번 요청 AC를 구분하지 못했다. state completed와 PR 생성/병합도 혼동될 수 있었다.
- Ralph iterate는 모든 passes 표식만으로 W행을 완료·커밋했다. 최종 관련 문서 대조와 누적 리뷰를 거치지 않는 별도 완료 경로였다.

## 반영한 계약

- gx-tdd 필수 참조 `references/document-lifecycle.md`와 setup 3.0.4, requirements, implement, 부분 phase 루프, resume, Ralph 준비에 관련 문서 사전 대조를 연결했다. 기존 계획/사용자 goal/AC/source/승인과 질문을 재사용하며 필요한 차이만 다룬다.
- 설치된 gx-context의 `development.py inspect`를 사용하고 전체 JSON은 파일, 모델에는 bounded `summary`만 제공한다. 이전 inspect 보고서를 그대로 `--previous`에 넘기며 입력/출력 파일을 겹치지 않는다. read-only는 `--plan -`/`summary --report -`의 stdin과 첫 명령 exit를 사용해 프로젝트 파일을 만들지 않는다.
- 최소 등록은 관련 context 인덱스·근거 있는 도메인 원장·이번 W행이다. 도메인 근거가 없으면 업무 분류가 아닌 요청 추적용 project 원장을 사용한다. 전체 인터뷰·스캔·glossary/PROJECTS 생성은 강제하지 않는다.
- 구현 완료 후 현재 AC의 실제 실행·인수 근거를 먼저 대조하고 관련 status/context를 반영한 다음, 최종 영향 계획·proof·fingerprint를 생성/확인한다. 최종 verify 뒤에는 `.dev` 진행/전달 기록만 변경한다. 새 PR URL은 .dev/delivery.md에 보존하며 후속 명시적 sync에서 원장에 반영한다.
- 새 ✅ 투영의 원래 필드 값·전후 해시는 로컬 제외 evidence/document-sync/journal.json에 둔다. 같은 파일 후속 Edit마다 after 해시를 갱신한다. 실패/대기/재개 때 이번 실행의 새 ✅만 조건부 원복하며 동시 변경이면 중단한다. 원문 backup은 커밋 수집에서 제외하고 공유 보고서에는 포인터/해시만 남긴다.
- 원장의 기존 ✅/PR은 버그 수정 중 보존한다. 모든 실제 AC·인수·최종 verify가 통과한 W행만 완료한다. 미충족/미검증/위험 수용 AC가 남으면 원래 W행은 진행을 유지한다. read-only/문서 금지는 착수·재개·되돌림을 포함한 문서 쓰기를 막는다.
- Ralph는 모든 AC passes를 루프 구현 종료로만 보고한다. W행을 완료/커밋하지 않고 document-sync-pending과 review/complete 인계를 기록한다. 이미 all-pass인 진입도 이 기록을 거친다. 누적 review-run-id/review-fingerprint의 현재 트리 증거가 있어야 complete로 들어가고, 문서/최종 verify 후 pending을 해제한다. per-AC 추가 agent/문서 갱신/verify는 넣지 않았다. 러너 COMPLETE 계약과 기존 로컬 커밋 opt-in은 유지한다.
- Claude/Codex의 상대 설치 경로·질문 대기·RED 격리·승인·보호/지문 게이트·기본 verify 종료점을 유지했다. gx-ralph 준비에는 새 helper에 필요한 Python/Edit 도구 선언을 보완했다.

## 확인

- 최초 문서 흐름 회귀 5개는 기존 누락/순서로 실패한 뒤 통과했다. 이후 읽기 전용·private journal 경계를 더해 문서 흐름 계약 7개가 통과했다.
- `test_codex_skill_pipeline.py`: 33개 통과. PowerShell PATH의 WSL bash 대신 실제 Git Bash를 선택했다. 첫 기본 PATH 실행의 WSL 미설치 오류는 소스 결함으로 처리하지 않았다.
- `RalphTddContractTests`: 기존 불충분한 완료 경로로 새 2개 검사가 실패한 뒤, 누적 리뷰 게이트를 포함한 5개 검사 통과.
- `sync-codex-resources.py --check`: 통과.
- `git diff --check` 소유 파일 범위: 통과.
- 최종 main SKILL 16,250B로 20KB 진입 예산 이내다. setup phase는 21,683B이며 main 예산과 별도다. 새 shared reference development-sync.md의 실존과 API 계약을 확인했다. 통합 린트에서 발견한 gx-lens의 literal request_user_input 누락은 부모가 보완했다. 최종 통합 린트는 부모가 수행한다.

정적/로컬 계약 검사이며 실제 설치 세션·질문 UI·모델 배정·훅 신뢰를 실행했다고 주장하지 않는다. 다른 작업자의 변경을 되돌리거나 stage/commit/push하지 않았다.
