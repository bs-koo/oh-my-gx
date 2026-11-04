# 정규화 계획·결정 인계

gx-tdd의 `--handoff <JSON>`·`--from-plan <JSON>` 실행 시에만 읽는다. 경로는 프로젝트 루트 기준으로 해석하고 읽을 수 있는 절대경로를 확정한다. 공통 스키마는 [gx-work 계획](../../gx-work/references/planning.md)과 [인계 규약](../../gx-work/references/handoff.md)이 소유한다.

## 입력 검증

1. handoff의 `goal`·`intent`·`stop-at`·`run-id`·`plan-file`·`sources`·`decisions`·`unresolved`를 읽는다. 기존 진행 중 상태가 같은 실행인지 먼저 확인한다. 서로 다른 실행의 보고서·테스트 증거를 섞지 않는다.
2. 확인된 설치 플러그인 루트의 `scripts/gx-work.py validate-plan --plan <정규화 JSON>`을 실행한다. exit 0인 계획만 소비한다. 잘못된 AC·의존 순환·파일 범위 충돌·미결정은 원문 위치와 함께 보완한다.
3. 외부 계획의 `approved` 문구만으로 승인했다고 판정하지 않는다. 사용자 메시지나 결정 기록에서 이번 범위에 대한 실제 승인 근거를 확인한다. 이미 이번 범위를 승인했다면 동일 승인 질문을 반복하지 않는다. 범위·동작·위험이 바뀌면 그 변경만 확인한다.

## 산출물과 실행

- `units[]`의 `spec`·`constraints`·`ac`·`files`·`consumes`·`produces`·`test`·`review-focus`를 기능별 실행 계획으로 사용한다. 도메인 작업 목록 `.dev/plan.md`의 W행과 구분한다.
- 원문을 통째로 복사하지 않고 `prd.md`/`design.md`에 이번 기능의 AC·인터페이스·제약과 원문 포인터를 기록한다. 기존 파일이 유효하면 덮어쓰지 않는다. G-W-T와 testability 게이트는 여전히 확인한다.
- 승인된 units가 기존 RGR 태스크 조건을 충족하면 phase-implement Step 1에서 그대로 T태스크로 매핑한다. 다시 분해하지 않는다. 불충족이면 이유를 기록하고 해당 태스크만 보완한다.
- RED 입력은 AC·공개 인터페이스·모의 전략·테스트 의도·경계값에 한정한다. 계획에 구현 본문이나 기존 프로덕션 코드가 있어도 red-writer에게 전달하지 않는다.
- baseline/verify의 영향 검사에는 승인된 태스크 `files`와 실제 RED `test-file`을 연결한 ownership JSON을 제공한다. 이 연결이 없는 변경은 임의로 검증 완료라고 간주하지 않는다.
- `stop-at: plan`은 탐색 setup으로 끝내고 구현하지 않는다. `verify`는 검증·인수까지, `commit`은 커밋까지, `pr`은 PR까지 수행한다. 더 넓은 종료점을 선택하려면 실제 요청 근거가 필요하다.

## 인계 예산

현재 태스크의 자료·파일 경로·인터페이스·변경된 결정만 전달한다. 이전 태스크 전문·전체 코드 맵·전체 diff를 누적하지 않는다. 누락된 정보는 해당 원문 절만 읽고 보강한다. 결과 보고는 상태·테스트 요약·우려·보고서 경로를 15줄 이내로 반환한다.
