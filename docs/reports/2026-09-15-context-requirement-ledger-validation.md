# gx-context 요구사항 원장 브랜치 검증

- 검증일: 2026-09-15
- 브랜치: `feat/context-requirement-ledger`
- 실제 기준 커밋: `14e8a1f97c93b7e5066d1c42737d56cdd65af754`
- final-review 수정 기준 HEAD: `ba24dea92a6921e51e658ae384798f9eb6c79784`
- 검증 대상 구현 HEAD: `e3467f1c2e6a5f6ba8ef9c030e81e4ec0e120ee0`
- 결과: PASS

이 보고서의 검증 대상은 위 구현 HEAD다. 보고서 자체를 갱신하는 후속 커밋은 검증 대상 SHA에 포함하지 않으며 자기 참조 SHA도 기록하지 않는다. 계획 예시의 오래된 기준 `5893c6c` 대신 실제 브랜치 merge-base인 `14e8a1f97c93b7e5066d1c42737d56cdd65af754`를 사용했다.

## final-review 회귀 수정

- 유효하지 않거나 입력 안에서 중복된 ID를 ID 없는 후보로 먼저 정규화하고, 기존 행과 후보를 일대일로 핵심 문장 매칭한 뒤 미매칭 후보에만 새 ID를 할당한다. `REQ-42` 재실행의 기존 FR/NFR ID 유지와 중복 `FR-1` 후보의 단일 행 중복 매칭 방지를 계약 테스트로 고정했다.
- `ACTIVE_VCS = git`이고 gh를 사용할 수 있을 때만 PR source를 활성화한다. 후보 시각 캡처, PR 조회, 성공 판정이 모두 `PR_SOURCE_ACTIVE` 조건을 사용하며 SVN에서는 `svn: 건너뜀 (PR 개념 없음)`을 기록하고 SVN 분석과 cursor 처리를 계속한다.
- `context-docs.md`의 status.md 트리 설명을 정본 FR/NFR별 3상태 원장으로 맞췄다.

## TDD RED 증거

구현 전 다음 focused 명령을 실행해 신규 회귀 테스트가 현재 계약의 누락 때문에 실패하는지 확인했다.

`python -m unittest tests.test_codex_skill_context.ContextRequirementLedgerTests.test_invalid_and_duplicate_input_ids_match_idless_before_allocation tests.test_codex_skill_context.ContextRequirementLedgerTests.test_pr_source_requires_git_even_when_gh_is_available tests.test_codex_skill_context.ContextRequirementLedgerTests.test_context_tree_describes_canonical_three_state_ledger -v`

결과는 3 tests 실행, 2 failures와 1 error였다. 누락된 ID 정규화·일대일 매칭 문구에서 `ValueError`, PR source 조건과 status.md 설명에서 각각 `AssertionError`가 발생했다.

## 자동 검증

| 검사 | 실제 결과 |
|---|---|
| 위 focused 회귀 테스트 3건 | PASS — 3 tests, 0 failures |
| `python -m unittest tests.test_codex_skill_context -v` | PASS — 22 tests, 0 failures |
| `python -m unittest discover -s tests -p "test_codex_*.py" -v` | PASS — 106 tests, 101.584초, 0 failures |
| `bash scripts/lint-consistency.sh` | PASS — 36/36, `정합성 린트 통과` |
| `python scripts/sync-codex-resources.py --check` | PASS — exit 0, 출력 없음 |
| `git diff --check` | PASS — exit 0, whitespace 오류 없음 |

`hook-tests.sh`와 `test-behavior-tests.sh`는 이번 final-review 수정에서 훅, 실행 스크립트, 역할, 설정을 변경하지 않았으므로 재실행하지 않았다. 수정된 Markdown 실행 계약은 focused context 테스트, 전체 Codex 테스트, sync-check, 36개 정합성 린트로 검증했다.

## 변경 파일 범위

final-review 수정 기준 HEAD에서 검증 대상 구현 HEAD까지 `git diff --name-only ba24dea92a6921e51e658ae384798f9eb6c79784..e3467f1c2e6a5f6ba8ef9c030e81e4ec0e120ee0`의 실제 출력은 다음 3개 파일이다.

```text
.claude/rules/context-docs.md
.claude/skills/gx-context/SKILL.md
tests/test_codex_skill_context.py
```

실제 기준 커밋에서 검증 대상 구현 HEAD까지 `git diff --name-only 14e8a1f97c93b7e5066d1c42737d56cdd65af754..e3467f1c2e6a5f6ba8ef9c030e81e4ec0e120ee0`의 전체 브랜치 변경 파일은 다음 5개다.

```text
.claude/rules/context-docs.md
.claude/skills/gx-context/SKILL.md
docs/reports/2026-09-15-context-requirement-ledger-validation.md
tests/golden-scenarios.md
tests/test_codex_skill_context.py
```

## 판정

final-review의 ID 정규화·일대일 병합, VCS별 PR source 활성 조건, 원장 설명 수정은 검증 대상 구현 HEAD에 반영됐고 관련 회귀 및 전체 Codex 계약 검사를 통과했다. 검증 실패와 미해결 blocker는 없다.
