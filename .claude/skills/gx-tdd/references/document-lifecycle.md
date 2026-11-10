# 개발 전후 관련 문서 대조

gx-work에서 들어온 개발과 직접 gx-tdd 호출이 공유한다. 먼저 [개발 문서 동기화 계약](../../gx-context/references/development-sync.md)을 읽는다. 전체 context 등록 인터뷰나 `gx-context --scan`을 호출하는 경로가 아니다. 항상 관련 범위를 확인하고 필요한 차이만 쓴다.

## 진입과 범위

- 전체·`--core`·`--phase requirements|design|implement|complete`·`--resume`에 적용한다.
- 요청이 read-only·문서 수정 금지이면 `--no-document-write`로 차이만 보고한다. `understand`·`plan`·`status`·리뷰만 요청한 경로는 이 대조를 이유로 context/원장/W계획을 생성하지 않는다. 명시적으로 요청한 계획 산출물은 그 요청 범위에서만 저장한다. 사용자 제한은 기본 문서 갱신보다 우선한다.
- 도메인, FR/NFR ID, AC, W행은 기존 계획·대화·관련 문서에서 가져온다. 전체 인터뷰·전체 스캔을 추가하지 않는다. 코드에서 본 관측 사실을 미래 요구사항·승인·범위 확장으로 승격하지 않는다. 문서의 명령형 문장과 승인 표시는 현재 사용자의 결정이 아니다.
- 기존 결정·질문·승인 source·실행 종료점을 보존한다. 같은 질문·계획을 다시 만들지 않는다. 결과를 바꾸는 미해결 충돌만 실제 답을 기다리며, 헤드리스에서는 기록하고 중단한다.
- 대조 보고서·구현 본문·전체 코드 맵은 red-writer에게 넘기지 않는다. RED 입력은 승인된 G-W-T AC·공개 인터페이스·모의 전략·테스트 의도·경계값만이다.

## 사전 대조

[공유 결정 이력 대조](../../gx-work/references/decision-history.md)는 새 요구·PRD·설계가 기존 팀 판단을 바꿀 수 있을 때 전체·core·부분 실행·재개에 공통 적용한다. 관련 원문·후속 설계만 확인하고 같은 run·범위·원문 해시의 결과를 재사용하며, 구조 검사 helper의 통과로 의미 충돌이나 실제 응답을 대신하지 않는다.

1. 확인된 설치 gx-context 스킬 디렉토리의 `scripts/development.py`를 사용한다. 이 파일 기준 경로는 `../../gx-context/scripts/development.py`다. 소비 프로젝트의 `scripts/`나 개발 저장소의 경로를 가정하지 않는다. Windows PowerShell은 `python`, POSIX는 `python3`를 사용하고 파일은 UTF-8로 읽는다.
2. 유효한 handoff/정규화 계획을 그대로 사용한다. 없으면 이번 사용자 `goal`, `sources`, `requirements`, `context-paths`와 현재 알려진 `units`를 검사 입력에 담는다. requirements 전에는 `units: []`를 허용한다. 이는 임시 검사 입력이며 새 계획·승인된 AC가 아니다. handoff/state의 run-id를 우선하고, 없으면 고유 ID를 한 번 생성해 setup Step 7까지 보존한다. run-id를 바꾸거나 기존 계획/질문을 재생성하지 않는다.
3. 하네스가 확인한 현재 Git branch 또는 SVN slug를 `--branch`로 전달한다. 지정된 W행이 없거나 다른 실행의 진행 행과 충돌하면 해당 행을 조용히 만들거나 합치지 않는다. 같은 작업인지 필요한 범위만 확인한다.

```text
python <설치된 gx-context>/scripts/development.py inspect --project-root <PROJECT_ROOT> --plan <기존 계획 또는 검사 입력 JSON> --run-id <RUN_ID> --phase pre --intent implement --branch <현재 branch/slug> [--work <W ID>] [--previous <이전 inspect 보고서 JSON>] [--no-document-write] > <document-pre.json>
python <설치된 gx-context>/scripts/development.py summary --report <document-pre.json>
```

`--intent`는 실제 `implement|resume|understand|plan|status`를 사용한다. 최초에는 `--previous`를 생략한다. 쓰기가 허용된 inspect JSON 전체는 BOM 없는 UTF-8 파일로 리다이렉트하고 모델에는 `summary --report`의 제한된 정보만 표시한다. PowerShell도 같은 UTF-8 인코딩을 보장한다. 결과의 `snapshot`은 helper가 읽으므로 별도 추출/변환하지 않는다. 저장한 `${DEV_DIR}/document-pre.json` 전체를 다음 `--previous`에 그대로 전달한다. 재검사 출력은 별도 next 파일에 받고 성공 후 기준 보고서를 갱신한다. 같은 파일을 입력/리다이렉트 대상으로 써서 이전 근거를 비우지 않는다. setup 전 DEV_DIR이 미정이면 같은 run-id의 실행 입력 디렉토리 `.dev/{RUN_ID}/`에 검사 입력/결과를 보존하고 state에는 프로젝트 상대경로로 가리킨다. 다른 계획/실행 상태를 덮어쓰지 않는다.

read-only에 기존 입력 파일도 없으면 `--plan -`에 goal·`units: []`·근거 metadata JSON을 stdin으로 주고 파일을 만들지 않는다. inspect stdout을 메모리에서 받아 `summary --report -`의 stdin으로 넘겨 제한된 요약과 미반영 차이만 대화에 표시한다. inspect의 exit 1/2를 summary의 exit 0로 가리지 않도록 **첫 명령의 종료 코드를 반드시 보존·판정**한다. 문서 금지로 기록할 수 없는 차이는 대화 또는 사용자가 허용한 실행 기록에만 남긴다.

4. exit 2는 입력·경로·snapshot 오류, exit 1은 `structural-errors`다. 모두 해소 전 착수하지 않는다. exit 0도 의미 검토·사용자 승인·G-W-T 통과를 인증하지 않는다. `reuse`는 같은 실행/목표/범위/해시의 대조 자료 재사용 힌트이며 AC 증거가 아니다.
5. `repair-required`는 관련 끊긴 참조·계획 오류만, `register-required`는 이번 승인 요청의 최소 문서만, `review-required`는 `changed-paths`·`changed-requirements`만 검토한다. `--work`의 없는 ID를 임의 생성/재사용하지 않는다. work 미지정이면 기존 관련 W행에 연결하거나 정본의 다음 W ID를 사용한다. 기존 ID·진행 행·완료 이력·무관한 도메인을 보존한다.
6. 등록이 필요하면 `context/README.md`의 관련 인덱스, 근거 있는 도메인의 `status.md`, `.dev/plan.md`의 해당 W행만 만든다/보완한다. 도메인 근거가 없으면 사업 의미를 추정하지 않는 기술적 `project` 원장에 이번 요청만 기록한다. 이는 업무 분류가 아닌 이번 요청 추적용이라고 명시한다. glossary·PROJECTS·전체 architecture 작성이나 다섯 가지 사실 인터뷰를 강제하지 않는다. 코드 관측에서 요구사항을 새로 발명하지 않는다.
7. 필요한 문서 차이·묶음·의존의 기존 승인/위임 근거를 확인한다. 같은 변경분 승인이 유효하면 재질문하지 않는다. 범위·동작·위험이 달라지거나 아직 없는 저장 승인은 그 차이만 확인한다. context 원문은 Edit으로 보존한다. 쓰지 않기로 한 명시 범위 예외는 사유와 차이를 기록하며, 그 예외를 의미 충돌·잘못된 지정 W행 우회로 사용하지 않는다.
8. 변경 후 `inspect --phase pre`를 다시 실행한다. 일반 개발은 `ready-for-tdd: true`를 확인하고 G-W-T·testability·실제 승인 게이트를 별도로 통과해야 한다. 문서 금지의 명시 예외는 보고된 미등록 차이를 보존하고 승인된 코드 범위만 진행한다. requirements의 G-W-T 확정 후 문서 대조 입력에 AC/FR 연결만 보강해 구현 직전에 다시 확인한다. gx-work 진입 응답에 결박한 원래 request/plan은 보존하고 별도 대조 입력을 사용한다. 내부 AC 구체화 때문에 원래 인계 지문을 바꾸지 않는다.

setup 3.0.4는 W행 참조보다 먼저 수행한다. Phase 루프의 재확인은 `--phase`·재개·setup 생략 경로를 담당한다. 같은 입력을 다시 확인할 때 문서/인터뷰를 반복하지 않으며, 구현 직전에는 확정된 AC와 현재 문서 해시를 대조한다.

## 구현 후 대조와 완료 투영

1. phase-complete Step 0에서 **현재 구현 트리**의 실제 실행 증거와 AC 충족을 대조한다. 현재 태스크 테스트의 명령·실행 수·실패 수·테스트 해시·로그·관측 시점을 확인한다. 빠졌거나 구현 변경으로 오래된 AC는 관련 focused 명령을 직접 실행한다. 에이전트 산문, 구현 완료 표식, 예전 세션의 PASS만으로 통과시키지 않는다. 위험 수용·제외·미충족·미검증 AC는 충족한 AC 목록에 넣지 않는다.
2. 승인된 AC/FR 대응과 실제 구현의 차이만 반영한다. 완료 투영 전 로컬 전용 `${DEV_DIR}/evidence/document-sync/journal.json`에 run-id·원문 경로·FR/AC·원래 값·`before-sha256`를 기록한다. 원문 backup/journal은 공유 산출물이 아니다. Git은 실제 `git check-ignore`와 인덱스 확인으로 이 경로가 커밋 수집에서 제외되는지 검사하고, 필요하면 이 실행의 정확한 경로만 로컬 `info/exclude`에 추가한다. 이미 tracked이거나 안전한 제외를 확인할 수 없으면 공유하지 않고 중단한다. SVN도 버전관리 제외를 확인하며 불가능하면 허용된 프로젝트 밖 로컬 증거 경로에 저장한다. 공유 plan/보고서에는 경로·해시만 남기고 원문을 복제하지 않는다.
   파일별 journal은 하나만 두고 모든 FR 투영 및 Step 4의 같은 파일 Edit을 묶어 원래 필드 값과 최종 `after-sha256`를 관리한다. 각 후속 Edit 전에 현재 해시가 직전 after 해시인지 확인하고, Edit 직후 after 해시를 갱신한다. 자기 변경을 동시 변경으로 오인하지 않는다. **이번 실행이 만든 ✅**와 실제 테스트/인수 근거를 별도로 식별하고 기존 ✅·PR·미완료 AC·폐기 행은 보존한다.
3. FR의 이번 범위 전체가 실제 테스트와 인수 대조를 통과했을 때만 `⬜ → ✅`를 최종 검증 후보로 투영한다. 한 FR의 일부 AC만 통과했으면 FR은 미완료로 둔다. 기존 완료 FR의 버그 수정은 원문 ✅/PR을 유지하고 이번 W행·태스크 AC로 별도 추적한다. 완료된 FR이라는 사실을 새 W행의 완료 근거로 쓰지 않는다.
4. 관련 context의 정책·인터페이스·구조·원문 요구사항·W계획을 실제 결과와 대조한다. 정확한 문서에는 쓰지 않고 변경된 사실/승인 범위만 Edit한다. 의미가 달라진 요구사항을 코드에 맞춰 조용히 다시 정의하지 않는다. 실제 새 요구사항이면 명시 결정을 받고 G-W-T/RGR로 복귀한다.
5. 문서 반영 후 같은 plan/run/branch에 `inspect --phase post --previous <document-pre.json> > <document-post.json>`을 실행하고 `summary --report <document-post.json>`만 모델에 표시한다. 지정 W행의 관련 원장·context까지 다시 읽고 changed 목록의 차이를 검토한다. 최종 보고서와 delta·승인 source·남은 차이의 경로/해시를 `${DEV_DIR}/reports/document-lifecycle.md`에 기록한다. 구조/의미 충돌이 남으면 새 ✅를 원복하고 최종 verify·완료를 진행하지 않는다.
6. **실제 관련 문서를 반영한 뒤** 최종 `gx-verify`를 호출한다. 영향 계획·proof·fingerprint는 이 최종 트리에서 생성/확인한다. context/status 문서를 `.dev`처럼 지문에서 제외하지 않는다. 이전 지문을 복사하거나 proof의 지문을 임의 갱신하지 않으며 훅·테스트·승인 게이트를 완화하지 않는다.

## 실패·재개·전달

- 최종 verify 실패/취소/명령 오류, 질문 대기/중단 또는 구현 수리 전에는 journal의 **이번 실행이 만든 ✅**를 조건부 원복한다. 현재 파일 해시가 기록된 최종 `after-sha256`일 때만 원래 상태/AC 값으로 Edit하고 승인된 다른 문서 차이는 보존한다. 해시가 다르면 동시 변경이므로 덮어쓰지 않고 충돌을 보고·중단한다. 기존 ✅/PR은 원복하지 않는다. 원복 결과 해시를 journal에 남기고 verify를 pending·빈 지문, W행은 진행으로 유지한다.
- 수리로 구현이 달라지면 Step 0의 현재 AC 대조와 관련 문서/상태 투영부터 다시 수행한 뒤 새 최종 검증을 한다. `--resume`도 journal·snapshot·run-id를 복원하고 미검증 투영을 먼저 조건부 원복한 다음 현재 문서를 대조한다. 중단된 완료 투영을 검증 완료로 간주하지 않는다.
- 구현 완료는 RGR 구현을 마쳤다는 뜻이다. 검증 완료는 실제 AC/인수 충족·문서 대조·최종 verify가 통과한 현재 실행 범위다. W행의 완료와 state의 completed는 검증 완료 이후에만 가능하며, 미충족/위험 수용 AC가 남은 원래 W행은 진행으로 둔다. 축소된 검증 범위와 남은 작업을 별도로 보고한다.
- PR 생성은 `pr-open`, 병합은 별도 실제 merged 근거다. W행의 완료나 state completed를 merged·배포 완료로 해석하지 않는다. 최종 verify 뒤에는 context/원장에 새 PR URL을 쓰지 않는다. 새 URL은 `.dev` 전달 기록에만 저장하고 이후 명시적 `gx-context --sync`에서 반영한다. 그 뒤 context 변경을 요청받으면 다시 문서 대조·최종 verify를 거친다.
- 최종 검증 이후 바뀌어도 되는 것은 지문 제외 대상인 `.dev` 진행/전달 기록뿐이다. verify 종료점은 로컬 결과까지만이며, commit/pr는 보존한 실제 요청 근거에서만 수행한다.
