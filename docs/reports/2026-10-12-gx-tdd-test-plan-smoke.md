# gx-tdd 단위테스트계획서(DE-13) 연동 검증 보고

작성일: 2026-10-12
대상 브랜치: `feat/gx-tdd-test-plan-link` (기준 `e807c65`)
설계: `docs/superpowers/specs/2026-10-12-gx-tdd-test-plan-link-design.md`
계획: `docs/superpowers/plans/2026-10-12-gx-tdd-test-plan-link.md`

## 1. 자동 검사 (Windows, Python 3.10)

| 검사 | 명령 | 결과 |
|---|---|---|
| 헬퍼 단위·지시문 계약 테스트 | `python -m unittest discover -s tests -p "test_de13_*.py"` | 64 tests OK (최종 리뷰 2회 반영 후) |
| Codex 계약 테스트 | `python -m unittest discover -s tests -p "test_codex_*.py"` | 152 tests OK |
| Codex 역할 동기화 | `python scripts/sync-codex-resources.py --check` | 드리프트 없음 |
| 훅 회귀 | `bash scripts/hook-tests.sh` | 훅 회귀 테스트 통과 |
| 정합성 린트 | `bash scripts/lint-consistency.sh` | 정합성 린트 통과 (36/36, 버전 1.34.0 4중 일치) |

이 검사는 헬퍼 동작과 지시문 계약 문구를 확인한다. 실제 모델 세션에서 오케스트레이터가 지시대로 움직이는지는 입증하지 않는다.

브랜치 전체 리뷰는 두 번 받았다 — Claude Opus(Critical 1·Important 5)와 Codex CLI 0.160.0 읽기 전용 리뷰(Important 7). 지적한 skip 판정 반례와 지시문 순서 결함은 회귀 테스트(`tests/test_de13_check.py`, `tests/test_de13_contract.py`)로 고정했다.

## 2. 실데이터 확인 (헬퍼 단독)

입력: `pm-test/건물에너지 데이터 통합관리 시스템/xlsx/REB-단위테스트계획서.xlsx` (gx-pm 4.x 출력, 169행), 같은 폴더 `REB-기능명세서.xlsx`.

| 항목 | 결과 |
|---|---|
| `scope --fn REB-FN-001,REB-FN-014` | 하한선 13행(대상 13). UT-002 사전조건 `신규 프로젝트, 회차 없음`(〃 해소), UT-048 표식 `가정` |
| `scope --spec` (기능 목록) | 기능 46개, `REB-FN-001` 기능명 `원천 데이터 등록` 매핑 |
| `apply` (REB-UT-001 Pass 원장 1행) | 원본 바이트 불변(수정 시각 2026-09-09 16:32 유지), 변경 zip 항목은 데이터 시트 `xl/worksheets/sheet2.xml` 1개, K2 `Pass`(서식 s=3 유지), `Pass,Fail` 데이터 검증 유지, 담당자 `구본승` 매핑 |
| 엑셀에서 사본 열기 | **미실행** — 사용자 확인 필요 (결과 열·드롭다운·서식 육안 확인) |

계획서 xlsx와 사본은 회사 산출물이라 레포에 넣지 않았다.

## 3. 실제 파이프라인 smoke

| ID | 절차 | 확인 항목 | 상태 |
|---|---|---|---|
| P1 | 샘플 Spring Boot 프로젝트에 `references/REB-단위테스트계획서.xlsx`·`REB-기능명세서.xlsx`를 두고 이 브랜치 플러그인을 로컬 설치한 뒤 `REB-FN-014 건물별 메모 관리 TDD로 개발해줘` 실행 (Claude Code) | 브랜치 `feat/…`(이슈 키 오인 없음) / `.dev/{브랜치}/ut-floor.md`에 REB-UT-045~050 6행 / AC `[UT: …]` 태그, REB-UT-048 `(가정 기반)` / 테스트 이름에 `REB-UT-0xx` / 게이트 2 통과 후 `.dev/ut-results/REB-FN-014.md` Pass(또는 사유 있는 제외) / 기능 커밋에 원장 포함 | 미실행 |
| P2 | P1 이후 `/gx-test-plan` | 실명 질문 1회, `.dev/ut-results/export/…_결과반영_*.xlsx` K열 Pass, 원본 불변 | 미실행 |
| T1 | Codex 세션에서 P1과 같은 요청 (`tests/codex-smoke.md` T1) | 질문 3개 이하·선택지 3개 이하, 게이트 질문이 실제 답변을 기다림 | 미실행 |

미실행 항목은 인증된 실제 세션이 필요하다. 실행 후 이 표의 상태와 근거(파일 경로·커밋 해시)를 갱신한다.
