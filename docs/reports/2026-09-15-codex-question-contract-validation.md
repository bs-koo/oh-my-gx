# Codex 질문 계약 브랜치 검증

- 검증일: 2026-09-15
- 브랜치: `fix/codex-question-contract`
- 통합 기준 커밋: `47aac0e0d946a0ff2fad18fe40b894c34fe2e539`
- 최종 검토 수정 기준 커밋: `d678aff67b7242a6de604a6ad8475955eb606c97`
- 검증 대상 구현 HEAD: `c865af22b43b531a38c730ada0688dec1378e379`
- 자동 검사 결과: **PASS**
- 실제 Codex 세션 smoke Q2: **미실행**

이 보고서는 위 구현 HEAD의 정적 질문 계약과 회귀 검사를 기록한다. 보고서 커밋은 검증 대상 SHA에 포함하지 않는다. 통합 기준 이후의 gx-context 질문 계약과 SVN 저장소 ID 정렬도 전체 Codex 검사에 포함된다.

## 최종 검토 수정

`d678aff6..c865af22`에서 gx-dev·gx-tdd의 phase 파일 8개와 질문 계약 테스트 1개를 수정했다.

- gx-tdd의 8개 초과 태스크 가드를 두 단계 질문으로 구성했다. 첫 단계는 AC 재분해·작업 계획 분할·다른 실행 경로를, 후속 단계는 그대로 진행·무인 루프를 제시한다. `.dev/plan.md` 부재와 SVN에서는 유효한 선택지만 2~3개로 다시 구성한다. 네 실행 경로 모두 유지된다.
- gx-dev의 다중 재개 후보는 정렬된 목록과 페이지별 2~3개 선택지로 제시한다. "다음 후보"를 통해 남은 후보를 모두 선택할 수 있다.
- gx-dev requirements·design·core·implement와 gx-tdd requirements·design·implement의 수정 선택지는 별도 후속 질문을 호출하고 **실제 수정 답변을 기다린 뒤** 파싱·반영한다. 원 질문의 UI Other에 사용자가 직접 입력한 내용은 별도 경로로 처리한다. 기존 PRD·설계·AC·태스크 분해 승인 게이트와 G-W-T 재검증을 유지한다.
- 정적 AskUserQuestion 예시 검사 범위를 SKILL 본문에서 phase 소비 파일까지 넓혔다. 실제 선택지의 같은 질문 Other 입력 주장, 수정 답변 대기 순서, 동적 재개 후보와 네 태스크 실행 경로를 회귀 검사한다. 변경 전 focused 검사에서 네 옵션 예시와 phase 수정 경로가 실패했고, 변경 후 11건 모두 통과했다.

## 검증 결과

| 검사 | 실제 결과 |
|---|---|
| `python -m unittest tests.test_codex_skill_questions -q` | PASS — 11 tests, `OK` |
| `python -m unittest discover -s tests -p "test_codex_*.py" -q` | PASS — 136 tests, 209.648초, `OK` |
| `python scripts/sync-codex-resources.py --check` | PASS — exit 0, 출력 없음 |
| `bash scripts/lint-consistency.sh` | PASS — 36/36, `정합성 린트 통과` |
| `bash scripts/hook-tests.sh` | PASS — 6/6 절, `훅 회귀 테스트 통과` |
| `bash scripts/test-behavior-tests.sh` | PASS — 30 pass, 0 fail |
| `git diff --cached --check` (구현 커밋 전) | PASS — exit 0, 공백 오류 없음 |
| `rg`로 phase의 `Other로 이동`·선택 후 같은 질문 Other 입력 문구 검색 | PASS — 0건, `rg` exit 1(매치 없음) |

## Q2 smoke 판정

`tests/codex-smoke.md`의 Q2 행과 정적 계약 검사는 **PASS**다. Q2는 실제 소비 프로젝트의 Codex 세션에서 gx-context 개방형 질문에 UI Other로 답하고 gx-dev 모드·프로파일 질문에는 선택지로 답한 뒤, 표시된 질문·도구 trace와 같은 id의 `codex_hook.py capture` 기록을 요구한다. 실제 세션은 실행하지 않았으므로 Q2 실측 상태는 **미실행**이다. 정적·mock 검사를 실제 도구 smoke 성공으로 해석하지 않는다.

최종 구현 HEAD에서 자동 검사 실패는 없다. Q2 실제 세션 실행과 trace·decision capture 확보는 후속 실측 검증 항목이다.
