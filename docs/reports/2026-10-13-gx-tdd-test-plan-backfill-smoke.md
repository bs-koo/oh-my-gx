# gx-tdd 단위테스트계획서 역보강 검증 보고

작성일: 2026-10-13
대상 브랜치: `feat/gx-tdd-test-plan-link`
설계: `docs/superpowers/specs/2026-10-13-gx-tdd-test-plan-backfill-design.md`
계획: `docs/superpowers/plans/2026-10-13-gx-tdd-test-plan-backfill.md`

## 1. 자동 검사 (Windows, Python 3.10)

| 검사 | 명령 | 결과 |
|---|---|---|
| 헬퍼 단위·지시문 계약 테스트 | `python -m unittest discover -s tests -p "test_de13_*.py"` | 81 tests OK (최종 리뷰 반영 후) |
| Codex 계약 테스트 | `python -m unittest discover -s tests -p "test_codex_*.py"` | 152 tests OK |
| Codex 역할 동기화 | `python scripts/sync-codex-resources.py --check` | 드리프트 없음 |
| 훅 회귀 | `bash scripts/hook-tests.sh` | 통과 |
| 정합성 린트 | `bash scripts/lint-consistency.sh` | 36/36 |

브랜치는 Claude Opus 리뷰(Critical 1·Important 5)와 Codex CLI 0.160.0 읽기 전용 리뷰(Important 7)를 받았고, 지적한 대용량 diff·재실행 중복·빈 서식 행·테스트 본문 범위·〃 연쇄·원장 쓰기 실패·버전 규칙을 회귀 테스트와 함께 고쳤다.

이 검사는 헬퍼 동작과 지시문 계약 문구를 확인한다. 실제 모델 세션에서 오케스트레이터가 짝짓기 초안을 지시대로 쓰는지는 입증하지 않는다.

## 2. 실데이터 확인 (헬퍼 단독, 사본)

입력: `pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-단위테스트계획서.xlsx`(gx-pm 4.x 출력, 169행)의 사본. 원장은 기존 REB-UT-001 Pass 1행 + REB-FN-001 신규 1행.

| 항목 | 결과 |
|---|---|
| apply | 버전 2.0, 결과 기입 1, 신규 `REB-UT-170`(171행, 연계요구사항ID `REB-RE-001`, 의존성 `없음`, 결과 `Pass`) |
| 개정이력 | 4행 `2.0 · 2026.10.13 · 추가 · 단위테스트 신규 1건 추가(REB-UT-170)·결과 기입 Pass 2건 (gx-tdd) · 구본승` (gx-pm 개정이력 규칙: +1.0, 사유 추가/보완), 개정 내용 셀 서식(s=4) 유지 |
| 범위 | 데이터 시트 dimension·자동 필터 `A1:K171`, 결과 드롭다운 `K2:K171`, 개정이력 필터 `A2:F4`, `_FilterDatabase` 정의 이름 2건 확장 |
| 바뀐 zip 항목 | `xl/workbook.xml`, `xl/worksheets/sheet1.xml`, `xl/worksheets/sheet2.xml`만 |
| 원장 표시 | `v2.0`, `v2.0 REB-UT-170` |
| 엑셀에서 갱신본 열기 | 미실행 — 사용자 확인 필요 (scratchpad `realcheck/REB-단위테스트계획서.xlsx`: 신규 행 서식·드롭다운·필터 범위, 개정이력 행) |

계획서 xlsx와 사본은 회사 산출물이라 레포에 넣지 않았다.

## 3. 실제 파이프라인 smoke

| ID | 절차 | 확인 항목 | 상태 |
|---|---|---|---|
| P1 | 계획서를 등록한 샘플 Spring Boot 프로젝트에서 도메인 요청(`건물별 메모 관리 TDD로 개발해줘`) | 계획서 관련 질문 없음 / complete Step 0.5에서 `.dev/ut-results/{slug}.md` 생성, 기존·신규 행과 근거 / 기능 커밋에 원장 포함 | 미실행 |
| P2 | P1 이후 `/gx-test-plan` | 실명 질문 1회, 계획서 신규 행·결과·개정이력 2.0, 원장 반영 표시 | 미실행 |
| T1 | Codex 세션 (`tests/codex-smoke.md` T1) | 질문 규칙, 실제 답변 대기 | 미실행 |

미실행 항목은 인증된 실제 세션이 필요하다. 실행 후 이 표의 상태와 근거(파일 경로·커밋 해시)를 갱신한다.
