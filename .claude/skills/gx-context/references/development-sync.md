# 개발 요청의 관련 문서 연결

gx-work·gx-tdd의 구현 전후에 사용하는 좁은 대조 경로다. **정합성 확인은 기본, 문서 쓰기는 필요한 차이만** 수행한다. 전체 context 스캔·등록 인터뷰·계획 재생성을 호출하지 않는다. TDD의 실행 순서·실패 복구는 [document-lifecycle.md](../../gx-tdd/references/document-lifecycle.md)가 소유한다. 단독 gx-context의 전체 등록/동기화 절차와 구별한다.

## 입력과 검사 결과

이 파일 기준 `../scripts/development.py`와 같은 디렉토리의 `plan.py`가 설치된 실제 위치를 확인한다. 소비 프로젝트 cwd에서 helper 경로를 추측하지 않는다. Python stdlib만 사용하며 검사 자체는 파일·Git·네트워크·테스트를 변경/실행하지 않는다.

입력은 요청 intake 또는 이미 있는 normalized plan의 `goal`, `sources`, `context-paths`, `requirements: [{domain, ids, path?}]`다. `units[].files`는 기존 구현계획에 있을 때만 사용하며 units 생략/빈 목록도 허용한다. `path`가 있으면 해당 `context/<domain>/status.md`여야 한다. 문서 대조를 위해 구현계획·AC를 새로 만들지 않으며 구체화는 gx-tdd가 맡는다. 파일 포인터는 프로젝트 경계 안의 파일만 허용하며, symlink/junction의 실제 대상도 검사한다. goal·사용자 결정·실제 run-id를 유지한다.

TDD 진입 승인에 결박한 원래 request/plan 파일은 덮어쓰지 않는다. TDD 안에서 구체화한 AC·변경 파일은 별도 문서 대조 입력에 보강한다. 진입 요청과 내부 계획/대조 기록을 혼동해 정상 재개에서 승인 지문을 바꾸지 않는다. 실제 목표·범위 변경은 결과를 제시한 뒤 다시 확인한다.

```text
python <설치된 gx-context>/scripts/development.py inspect --project-root <project> --plan <normalized-plan.json> --run-id <run> --branch <실제 branch/slug> --phase pre [--work Wnn] [--previous <이전 inspect 보고서.json>] [--no-document-write]
python <설치된 gx-context>/scripts/development.py summary --report <저장한 inspect 보고서.json>
```

쓰기 허용 실행은 완전한 inspect 결과를 `.dev/<run>/document-pre.json`에 한 번 저장하고 모델에는 summary만 전달한다. 다음 `--previous`에는 같은 보고서 또는 내부 snapshot 객체를 저장한 파일을 사용한다. post는 같은 plan/run/work에 `--phase post`를 준다. PowerShell은 BOM 없는 UTF-8 입출력을 보장한다. 읽기 전용에는 `--plan -`로 stdin JSON을 주고 stdout을 메모리에 받아 `summary --report -`에 전달하여 임시 파일도 만들지 않는다. **inspect exit 1/2는 summary exit 0로 가리지 않는다.**

| 결과 | 처리 |
|---|---|
| exit 2 | 경로·입력·snapshot 오류를 해소한다. cache miss로 무시하지 않는다 |
| exit 1 / repair-required | 원장 구조·끊긴 연결·충돌을 해소한다. 지정 W 없는 경우 임의 ID를 만들지 않는다 |
| register-required | 이번 요청의 최소 FR/W 연결만 보강한다 |
| review-required | 관련 문서와 changed 항목의 의미를 대조한다 |
| reuse | 같은 실행·범위의 자료를 재사용한다. 승인·의미 일치·AC 통과 증명은 아니다 |
| report-only | 차이만 전달한다. 쓰기·개발로 확장하지 않는다 |

전역 원장/계획의 ID·참조·의존은 기계적으로 검사하고 모델은 현재 W·관련 FR/AC·관련 문서 절만 읽는다. 기본 요약은 목록 20개·문구 500자로 제한한다. 생략된 **현재 작업** 자료는 필요한 항목만 추가로 확인한다. 전체 snapshot·원문·무관한 도메인을 반복 주입하지 않는다. `ready-for-tdd`는 구조/연결 준비만 뜻하며 G-W-T·의미·승인 게이트를 대체하지 않는다.

## 최소 등록과 보존

- 기존 요청과 의미가 같은 대기/진행 W를 우선 연결한다. 없으면 `.dev/plan.md`의 실제 다음 ID에 이번 범위만 추가한다. 완료/폐기 W, 다른 run·브랜치·충돌 slug를 덮어쓰지 않는다. 기존 ID를 재사용하지 않는다.
- 필요한 최소 파일은 `context/README.md` 인덱스, `context/<domain>/status.md`의 `ID | 요구사항 | AC | 상태 | PR` 원장, `.dev/plan.md`의 `ID | 작업 | 도메인 | 요구사항 | 의존 | 작업 위치 | 상태` 표다. 기존 파일은 관련 행만 Edit한다. 새 FR은 해당 도메인의 실제 다음 번호를 쓴다. 사용자 요청에서 확인한 AC만 기록한다.
- 업무 도메인 근거가 없으면 `project`를 이번 기술 요청의 추적용 원장으로 명시한다. 업무 의미·담당자·미래 요구를 추정하지 않는다. glossary·architecture·PROJECTS 전체 작성은 필요하거나 요청받은 경우만 수행한다.
- 완료 FR의 버그 수정은 기존 ✅/PR을 보존하고 새 W/현재 AC로 추적한다. 폐기 FR은 명시적인 요구사항 결정 없이 구현하지 않는다. 코드 관측을 요구사항이나 승인으로 승격하지 않는다.
- 이미 허가된 같은 범위의 연결·최소 문서 저장·구현 판단은 재질문하지 않는다. 결과를 바꾸는 요구사항 충돌만 실제 결정으로 해소한다. read-only·명시 문서 금지는 우선하며 미반영 차이를 보고한다. 그 예외로 잘못된 지정 W·의미 충돌을 우회하지 않는다.

정책의 실제 동작을 추가 조사해야 할 때만 gx-lens의 근거를 사용한다. 모든 개발 요청에서 lens나 별도 에이전트를 자동 호출하지 않는다.
