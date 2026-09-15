# gx-dev·gx-tdd 파이프라인 부트스트랩 B 분기 검증

검증일: 2026-09-15. 작업 분기 `fix/pipeline-bootstrap-contract`의 최종 리뷰 수정 구현 커밋은 `f30e341e33360f543fb49fa2b721d0be71d17395`, 이번 수정의 실제 비교 기준은 `baeba67358b46f30a91476f0058551b5cfd4d4e1`이다. 검증은 해당 구현 트리에서 실행했고, 보고서만 별도 커밋한다.

## 결과와 범위

| 검사 | 관찰 결과 |
|---|---|
| 파이프라인 집중 테스트 | `python -m unittest tests.test_codex_skill_pipeline -v` → 19/19 PASS |
| Codex 전체 테스트 | `python -m unittest discover -s tests -p "test_codex_*.py" -v` → 103/103 PASS, exit 0 |
| 정합성 린트 | `bash scripts/lint-consistency.sh` → 36/36 PASS, exit 0 |
| 훅 회귀 | `bash scripts/hook-tests.sh` → 6개 그룹 PASS, exit 0 |
| 행동 테스트 mock | `bash scripts/test-behavior-tests.sh` → 30 pass, 0 fail, exit 0 |
| Codex 생성 리소스 드리프트 | `python scripts/sync-codex-resources.py --check` → exit 0, 출력 없음 |
| 커밋 diff 공백 오류 | `git diff --check baeba67358b46f30a91476f0058551b5cfd4d4e1..f30e341e33360f543fb49fa2b721d0be71d17395` → exit 0, 출력 없음 |

`gx-tdd`의 단독 phase 환경 감지에서 `PROJECT_ROOT`는 절대경로를 유지하고 Git·SVN `DEV_DIR`는 `.dev/{branch-slug}/`·`.dev/{slug}/`·`.dev/trunk/`의 프로젝트 상대경로로 정했다. SVN 활성 작업 포인터는 `${PROJECT_ROOT}/.dev/.active`를 계속 읽는다. phase-implement·phase-review의 `${PROJECT_ROOT}/${DEV_DIR}` 소비 경로를 테스트에서 실제 파일로 확인했고, 공백 있는 임시 루트 및 `DEV_DIR`에서 Bash diff 리다이렉트도 실행했다. Git·SVN `.git`·`.svn` 마커가 있는데 사용 가능한 도구가 `no_wc`를 보고하는 두 케이스를 기존 루트 선택 fixture에 추가했다.

## 변경 파일과 크기

이번 비교 기준 대비 제품 diff는 2개 파일, 79 insertions/7 deletions다: `.claude/skills/gx-tdd/SKILL.md`, `tests/test_codex_skill_pipeline.py`. `gx-dev`, phase 파일, `gx-context`, manifest, marketplace, CHANGELOG는 이번 수정에서 변경하지 않았다. 보고서 커밋의 파일 범위는 이 문서 한 개다.

린트 32번의 예산은 CR 바이트를 제거한 크기로 계산한다. 현재 gx-tdd `SKILL.md`는 62,942/63,000 B로 58 B 남고, 변경하지 않은 `phase-setup.md`는 21,997/22,000 B로 3 B 남는다. 작업 트리의 원본 CRLF 크기는 각각 63,657 B, 22,181 B다. 별도 모듈화 설계의 최종 목표는 gx-context/gx-dev/gx-tdd `SKILL.md` 320/520/520행이며 이 수정은 해당 목표의 범위에 속하지 않는다.

## 검증의 한계와 통합 조건

훅·mock 행동 테스트는 훅·프롬프트 파일이 이번 diff에서 직접 변경되지 않았더라도 구현 커밋의 정확한 트리에서 다시 실행했다. 이 보고서만 커밋한 뒤에는 제품 동작이 바뀌지 않으므로 다시 실행하지 않는다. A 변경을 B에 통합하거나 훅·프롬프트·phase 파일이 바뀌면 병합한 정확한 HEAD에서 두 테스트와 Codex 전체 테스트·린트·sync를 다시 실행한다.

이 결과는 저장소의 정적 계약 테스트, 셸 훅 회귀, mock 행동 테스트에 대한 로컬 증거다. 실제 설치된 플러그인의 Claude/Codex 인증 모델 세션에서 하위 디렉토리 시작, SVN 작업 복사본, 질문 UI를 재실행한 결과로 해석하지 않는다. `gx-context` 원장 producer 변경은 별도 A 분기 소유이며 B에는 아직 포함되지 않았다. 통합할 때 A의 SVN `REPOSITORY_ID` 문구를 B의 두 consumer와 대조한다.

검증 중 생성된 `.claude/hooks/__pycache__/`, `scripts/__pycache__/`, `tests/__pycache__/`는 두 커밋 범위에서 제외한다.
