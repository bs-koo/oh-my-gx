# gx-dev·gx-tdd 파이프라인 부트스트랩 B 분기 검증

검증일: 2026-09-15. 작업 분기 `fix/pipeline-bootstrap-contract`의 구현 기준은 `cb5b91f2ded67b38b14abe602a710c5ed300f52a`, 실제 비교 기준은 `14e8a1f97c93b7e5066d1c42737d56cdd65af754`다. 계획의 예시 기준 `5893c6c`는 현재 분기의 실제 부모 기준이 아니므로 이 보고서의 diff와 검증 범위에 사용하지 않았다.

## 결과와 범위

| 검사 | 관찰 결과 |
|---|---|
| 파이프라인 집중 테스트 | `python -m unittest tests.test_codex_skill_pipeline -v` → 17/17 PASS |
| Codex 전체 테스트 | `python -m unittest discover -s tests -p "test_codex_*.py" -v` → 101/101 PASS, exit 0 |
| 정합성 린트 | `bash scripts/lint-consistency.sh` → 36/36 PASS, exit 0 |
| 훅 회귀 | `bash scripts/hook-tests.sh` → 6개 그룹 PASS, exit 0 |
| 행동 테스트 mock | `bash scripts/test-behavior-tests.sh` → 30 pass, 0 fail, exit 0 |
| Codex 생성 리소스 드리프트 | `python scripts/sync-codex-resources.py --check` → exit 0, 출력 없음 |
| 커밋 diff 공백 오류 | `git diff --check 14e8a1f97c93b7e5066d1c42737d56cdd65af754..cb5b91f2ded67b38b14abe602a710c5ed300f52a` → exit 0, 출력 없음 |

`rg -n "PHASES = \[setup, (requirements|design)\]|git rev-parse --show-toplevel|svn info --show-item wc-root|REPOSITORY_ID" .claude/skills/gx-dev .claude/skills/gx-tdd .claude/skills/gx-context`로 수동 대조했다. gx-dev와 gx-tdd의 부분 phase 목록은 각각 `requirements=[setup, requirements]`, `design=[setup, design]`으로 일치한다. 두 `phase-setup.md`의 Step -1은 Git `--show-toplevel` → SVN `wc-root` → 부재가 확정된 경우의 현재 디렉토리 절대경로 순서를 명시하며, 이후 config·`.dev`·context·VCS·빌드·테스트 경로도 그 루트를 사용한다. 두 파일의 SVN 식별 규칙은 `svn info --show-item url`의 종료 코드가 실패하면 중단하고, 성공한 URL 끝의 `trunk`/`branches/<name>`/`tags/<name>` 제거 후 마지막 세그먼트를 `REPOSITORY_ID`로 쓰며, 성공했지만 값이 비거나 모호한 경우에만 경고 후 `basename(PROJECT_ROOT)`를 쓰는 것으로 일치한다.

## 변경 파일과 크기

실제 기준 대비 제품 diff는 7개 파일, 629 insertions/49 deletions다: `.claude/skills/gx-dev/{SKILL.md,phases/phase-setup.md}`, `.claude/skills/gx-tdd/{SKILL.md,phases/phase-setup.md,phases/setup-resume.md,references/maintenance-notes.md}`, `tests/test_codex_skill_pipeline.py`. `gx-context`, manifest, marketplace, CHANGELOG는 이 B 분기에서 변경하지 않았다. 이 보고서 커밋의 제품 파일 범위는 이 문서 한 개다.

기존 린트 32번의 예산은 CR 바이트를 제거한 크기로 계산한다. 현재 gx-tdd `SKILL.md`는 62,978/63,000 B, `phase-setup.md`는 21,997/22,000 B로 통과했지만 여유가 각각 22 B, 3 B다. 원본 파일 크기는 CRLF 때문에 각각 63,699 B, 22,181 B다. 별도 모듈화 설계의 최종 목표는 gx-context/gx-dev/gx-tdd `SKILL.md` 320/520/520행이고 현재는 791/725/743행이다. 이는 후속 모듈화 작업의 목표이며 B 분기의 크기 수용 판정과 구분한다.

## 검증의 한계와 통합 조건

이 결과는 저장소의 정적 계약 테스트, 셸 훅 회귀, mock 행동 테스트에 대한 로컬 증거다. 실제 설치된 플러그인의 Claude/Codex 인증 모델 세션에서 하위 디렉토리 시작, SVN 작업 복사본, 질문 UI를 재실행한 결과로 해석하지 않는다. `gx-context` 원장 producer 변경은 별도 A 분기 소유이며 B에는 아직 포함되지 않았다. 통합할 때 A의 SVN `REPOSITORY_ID` 문구를 B의 두 consumer와 대조하고, 병합한 정확한 HEAD에서 같은 검사들을 다시 실행해야 한다.

검증 중 생성된 `.claude/hooks/__pycache__/`, `scripts/__pycache__/`, `tests/__pycache__/`와 `.superpowers/sdd/` 기록은 제품 커밋 범위에서 제외한다.
