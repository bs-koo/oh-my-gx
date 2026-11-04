# gx-work 통합 구현 계획

**명세:** [spec.md](spec.md). 기준 main: 43acaee. 브랜치: codex/gx-work-unified.

## 작업 분담

| 작업 | 담당 범위 | 산출/소비 계약 | 확인 |
|---|---|---|---|
| A | gx-work 스킬·계획/handoff helper·전용 테스트 | 정규화 계획·의도·종료점·run-id를 B/D에 전달 | helper temp 프로젝트 테스트 |
| B | gx-context 모드·인계·전용 테스트 | 요구사항 근거·결정·기존 작업계획을 A/D에 전달 | 원장 보존·공통 경로·불필요 질문 회귀 |
| C | 테스트 선택 helper·verify·review·전용 테스트 | plan/record/reuse와 코드·설정·명령·로그 지문 | 영향 매핑·전체 폴백·증거 무효화 테스트 |
| D | 공통 리소스 이동·gx-dev 제거·TDD 소비·commit·배포/문서 통합 | A/B/C 계약 연결, 원래 안전 조건 보존 | migration RED/GREEN·필수 최종 검사 |

## 사전 충돌 검사

| 작업 쌍/작업 | 확인한 경계 | 판정 |
|---|---|---|
| A·D | gx-work/references 공존 | A는 planning/handoff만, D는 codex-* 공통 파일만 소유 |
| B·D | context의 기존 gx-dev runtime 포인터 | B 완료 후 D가 마지막 경로 변환; B는 모드 내용 소유 |
| C·D | TDD phase 수정 | C는 review, D는 implement/complete/setup/intent 소유 |
| A·B | 인계 JSON | sources/decisions/requirements/plan-file/goal/stop-at/run-id 명시 |
| A | 계획만 요청 | helper·대화 모두 읽기 전용, 실행 시작 때 환경 준비 |
| B | 코드 스캔과 미래 요구사항 | 관측 사실을 신규 FR로 발명하지 않음 |
| C | 검증 절감과 fail-closed | 불명확한 범위는 전체 확장, 실패/0건 재사용 금지 |
| D | 제거와 하위 호환 | 예전 gx-dev 상태는 새 TDD로 묵시 변환하지 않고 전환 안내 |

## 검증 예산

각 작업은 담당 테스트만 반복한다. 리소스/경로를 바꾼 뒤 전체 Codex 계약 검사는 통합 시 1회 실행한다. 새로운 실패나 수정이 있을 때 관련 집합만 재실행하며, 최종 CI는 공통 리소스·훅·라우팅 변경으로 정당화되는 범위만 확인한다.
