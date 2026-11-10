# 보조 스킬 경계·복구 구현계획

> **For agentic workers:** 각 소유 범위에서 회귀 RED → 최소 수정 → GREEN을 수행한다. 서로의 편집을 되돌리지 않는다. 최종 검증·독립 리뷰는 부모가 통합한다.

**Goal:** 승인된 보조 스킬 결함 13건과 공통 보호·복구 경계를 수정한다.

**Architecture:** 기존 스킬과 helper의 책임을 유지하며 인덱스·테스트 보존, 실행 ID, 오류 분류, 대상 저장소, 시각화 출력 보호를 기계적으로 검증한다. 승인·모드·모델·문서 인계의 정본은 공유한다.

**Tech Stack:** Markdown, Python 3.10+ 표준 라이브러리/unittest, Git Bash, 기존 Node fixture.

**Spec:** [보조 스킬 경계 설계](../specs/2026-11-10-aux-skill-edges-design.md). 이전 감사 결과에 대한 사용자의 “모두 진행해줘” 응답이 실행 범위 승인이다.

## Global Constraints

- 기준 main: `6ef7517`. 작업 경로: `D:/SQ/oh-my-gx/.claude/worktrees/gx-aux-skill-edges`.
- 기존 사용자 변경과 다른 작업을 보존한다. 커밋·원격 반영은 별도 요청 범위다.
- 임시 fixture의 실제 동작 검사와 정적 지시문 검사를 구분한다. 실제 앱 사용자 승인을 가장하지 않는다.
- helper 입력은 경로·JSON을 명시적으로 검증하고 실패를 정상 빈 결과로 바꾸지 않는다.

## Review Focus

- 이미 staged인 제외 파일, 부분 staged 수정·삭제·새 인덱스, 실패 시 작업 파일 불변.
- cwd와 -C 저장소가 다름, 공백·한글 경로·연속 -C, 모호한 명령은 잘못된 저장소로 통과하지 않음.
- 임의 테스트 삭제·skip, 중단한 humanizer 실행과 동시 실행의 기존 결과 불변.
- 새 템플릿·기존 설정·하위 스택, 읽기 전용 모델 입력, 정상 빈 의존성 결과와 오류 JSON.
- explicit static/mermaid의 Archify 미호출, 동시 map 출력, 실패 후 잠금 해제·기존 결과 보존.

## Task 1: 커밋·보호·교차 리뷰

**소유:** delivery 담당. gx-commit/SKILL, pre-tool-guard, gx-cross-review/SKILL, 관련 helper와 `tests/test_gx_aux_delivery.py` 및 필요한 훅 회귀.

- [x] 실제 인덱스·두 저장소·untracked/stat fixture의 실패를 먼저 확인한다.
- [x] 명시 제외를 인덱스에서 제거·재확인하고 실패 복원을 파일명이 아닌 원 인덱스 내용으로 수행한다.
- [x] 실제 Git 대상 경로를 보호 브랜치·verify 양쪽에 사용하고 모호한 경우 차단한다.
- [x] 교차 리뷰의 diff/stat과 전체 파일 목록을 일관되게 전달한다.
- [x] 정상·실패·재개·공백 경로 회귀를 통과한다.

## Task 2: 단독 GREEN·humanizer

**소유:** RGR/humanizer 담당. gx-green/SKILL, gx-humanizer/SKILL·strict, humanizer-naturalness 원본 역할, 관련 helper와 `tests/test_gx_aux_integrity.py`.

- [x] 대상 외 테스트 변조와 중단 run 충돌, 검증 입력 누락의 RED를 확인한다.
- [x] 전체 테스트 목록·지문을 비교하고 허가 없는 삭제·skip을 차단한다.
- [x] run-id는 모든 예약/진행/완료 디렉터리를 반영해 배타적으로 확보한다.
- [x] 원문·확정 장르·톤·수정 범위를 검증 입력에 포함하고 안전본·중단 이력을 보존한다.
- [x] 행동 회귀를 통과하고 배포 역할 갱신 필요 사항을 보고한다.

## Task 3: 설정·읽기 전용·분석 출력

**소유:** analysis/setup 담당. gx-setup 타입 등록, gx-lens, gx-work의 모델 규약, codex-model-policy.py, gx-tech-debt, gx-research, 관련 helper와 `tests/test_gx_aux_analysis.py`·기존 모델 검사.

- [x] 모노레포 누락·읽기 전용 helper 충돌·오류 JSON·지정 출력 경로 회귀 RED를 확인한다.
- [x] 기존 설정을 보존하면서 미등록 스택도 탐색하고 새 템플릿을 구별한다.
- [x] 모델 capabilities는 메모리/표준입력으로 검증할 수 있게 하며 읽기 전용 디스패치 기록은 대화에서 유지한다.
- [x] 정상 결과 스키마와 오류·부분·미지원 상태를 분리하고 부분 분석의 점수 한계를 표시한다.
- [x] 확정 OUTPUT_PATH와 실행별 research 결과를 저장·완료·인계에 재사용한다.
- [x] 신규 및 기존 관련 회귀를 통과한다.

## Task 4: 시각화 backend·동시 출력

**소유:** 부모. build_map.py, service-map 참조, 관련 시각화 회귀와 사용자 문서.

- [x] explicit backend가 전달되지 않고 임시 JSON 쓰기가 충돌하는 RED를 확인한다.
- [x] build_map API/CLI에 backend를 연결하고 static/mermaid는 Archify 설치·탐지를 건너뛴다.
- [x] 출력 폴더의 배타적 실행과 고유 임시 파일·원자적 교체·실패 시 정리를 구현한다.
- [x] 기본 auto·도메인 부분 갱신·기존 실패 보존 회귀를 통과한다.

## Task 5: 통합·독립 리뷰

- [x] 역할·설정 배포 생성물과 사용자 안내·smoke 경계 시나리오를 갱신한다.
- [x] sync --check, lint, hooks, mock behavior, 전체 Codex 및 변경 관련 회귀를 실행한다.
- [x] 기능/복구·보호·하네스 계약을 독립 재리뷰하고 중요한 발견을 해결한다.
- [x] 기존 작업 보존과 실제 앱 미검증 범위를 포함해 완료 결과를 기록한다.

## Task 6: 기능 개선 평가

사용자가 기능 개선 관점의 검토도 추가했다. 앞선 수정은 계속 진행하며, 보조 스킬로 새로 할 수 있는 작업을 함께 평가한다.

- [x] 현재 지원 기능과 구분해 실행 이력·재개·버전 비교, 분석 결과의 후속 작업 연결, 검증 범위·결과 조회를 조사한다.
- [x] 후보마다 사용자 시나리오·부족한 현재 기능·기대 효용·구현 비용·기존 구조와의 연결을 정리한다.
- [x] 결함 수정에 자연스럽게 포함되는 확장과 별도 범위가 필요한 큰 기능을 구분해 보고한다.

## 실행 기록

- 2026-11-10: main에서 격리 브랜치를 만들고 승인된 감사 항목을 네 소유 범위로 나눴다.
- 시각화 신규 경계 10건 및 기존 orchestration·index·문서·계약 회귀 85건이 통과했다. 명시 backend·동시 쓰기는 임시 프로젝트와 설치 호출 mock으로 확인했으며 실제 앱 실행을 뜻하지 않는다.
- 보조 전문 스킬 13개의 기능 검토와 조회 기능 3종을 `docs/reports/2026-11-10-aux-skill-functional-roadmap.md`에 정리했다.
- 독립 리뷰에서 실행 설정 누락·탐색 오류·윤문 양 검수의 동일본 결합, 사용자 detect·패키지명 상태 충돌, index 경합·명령 체인·Windows BOM 경계를 추가 발견해 보완했다. 통합 지시문 예산 검사 실패는 상세 참조 분리로 해결하며 예산 기준을 유지한다.
- 최종 전체 실행: 보조 회귀 84건·Codex 286건·lens 15건·lint 36단계·훅 6그룹·mock 30건 통과. 역할 sync 검사와 기존 작업 48파일 지문 보존도 확인했다. 실제 앱 smoke는 미실행으로 구분했다.
- 추가 요청인 core의 grill-me형 문답 적용 여부는 별도 분석 문서에 정리했다. core 실행 절차는 변경하지 않았다.
