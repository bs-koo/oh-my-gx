# Codex 질문 계약 브랜치 검증

- 검증일: 2026-09-15
- 브랜치: `fix/codex-question-contract`
- 실제 통합 기준 커밋: `47aac0e0d946a0ff2fad18fe40b894c34fe2e539`
- 검증 대상 구현 HEAD: `b9339b761c3a9b12f54d4a98bea7b930c80c995e`
- 자동 검사 결과: **PASS**
- 실제 Codex 세션 smoke Q2: **미실행**

이 보고서는 위 구현 HEAD의 정적 계약과 회귀 검사를 기록한다. 보고서 커밋은 검증 대상 SHA에 포함하지 않는다. 통합 기준 `47aac0e...` 뒤의 `d97d78231c9000386be89ca2839280c2fc9b244c`는 gx-context의 SVN 저장소 ID 진단을 gx-dev·gx-tdd 계약과 맞춘 Task 0 커밋이며, 아래 전체 Codex 검사 범위에 포함된다.

## 검증 결과

| 검사 | 실제 결과 |
|---|---|
| 금지된 명시적 Other label 및 종전 질문 `1~5`·선택지 `2~4` 상한 검색 | PASS — 세 스킬 디렉터리 검색 0건, `rg` exit 1(매치 없음) |
| `python -m unittest tests.test_codex_skill_questions -v`에 해당하는 질문 계약 테스트 | PASS — 전체 discover 실행 중 9건 모두 `ok` |
| `python -m unittest discover -s tests -p "test_codex_*.py" -v` | PASS — 134 tests, 134.086초, `OK` |
| `python scripts/sync-codex-resources.py --check` | PASS — exit 0, 출력 없음 |
| `bash scripts/lint-consistency.sh` | PASS — 36/36, `정합성 린트 통과` |
| `bash scripts/hook-tests.sh` | PASS — 6/6 절, `훅 회귀 테스트 통과` |
| `bash scripts/test-behavior-tests.sh` | PASS — 30 pass, 0 fail |
| `git diff --check 47aac0e..b9339b7` | PASS — exit 0, 공백 오류 없음 |

금지 패턴 검색에는 `rg -n -e 'label:\s*(?:\x22|\x27)(?:Other|Other로 입력|직접 입력|답변 입력|주제 입력)(?:\x22|\x27)' -e '(?:질문|questions)[^\r\n]*(?:1~5|최대 5)' -e '(?:선택지|options)[^\r\n]*(?:2~4|최대 4)' .claude/skills/gx-context .claude/skills/gx-dev .claude/skills/gx-tdd`를 사용했다. UI Other를 안내하는 설명 문장은 금지 대상이 아니며, 실제 `label` 값을 검사했다.

`tests/test_codex_skill_questions.py`의 9건은 세 스킬의 질문 1~3개·선택지 2~3개 규칙, 정적 예시의 개수, 명시적 Other option 부재, stable snake_case `id`·`multiSelect` 제거·현재 도구 스키마 우선의 Codex 변환 규칙, 수정 선택 후 별도 질문 답변 대기, Q2 smoke 계약 행을 확인한다. SVN 저장소 ID 정렬에 관한 `test_codex_skill_context.py` 회귀도 전체 discover에서 통과했다.

## Q2 smoke 판정

`tests/codex-smoke.md`의 Q2 행과 해당 정적 테스트는 **PASS**다. Q2는 실제 소비 프로젝트의 Codex 세션에서 gx-context 개방형 질문에 UI Other로 답하고, gx-dev 모드·프로파일 질문에는 선택지로 답한 뒤, 표시된 질문·도구 trace와 동일한 id의 `codex_hook.py capture` 기록을 요구한다. 이 실제 세션은 실행하지 않았으므로 Q2의 실측 상태는 **미실행**이다. mock과 정적 테스트 결과를 실제 도구 smoke 성공으로 해석하지 않는다.

## 변경 파일 범위

통합 기준에서 검증 대상 구현 HEAD까지 `git diff --name-status 47aac0e..b9339b7`의 출력은 다음 8개 파일이다. 보고서 파일은 이 목록에 포함되지 않는다.

```text
M  .claude/skills/gx-context/SKILL.md
M  .claude/skills/gx-dev/SKILL.md
M  .claude/skills/gx-dev/references/codex-runtime.md
M  .claude/skills/gx-tdd/SKILL.md
M  .claude/skills/gx-tdd/references/maintenance-notes.md
M  tests/codex-smoke.md
M  tests/test_codex_skill_context.py
A  tests/test_codex_skill_questions.py
```

자동 계약 검사에서 실패나 미해결 blocker는 없다. 실제 Codex 세션의 Q2 실행과 trace·decision capture 확보는 후속 실측 검증 항목이다.
