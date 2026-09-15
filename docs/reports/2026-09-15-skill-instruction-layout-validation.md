# gx-context·gx-dev·gx-tdd 지시문 모듈화 검증

- 검증일: 2026-09-15
- 분기: `refactor/skill-instruction-layout`
- 변경 비교 기준: `f917cdff98dd0f33f3f82a52ee26387eda42df7d`
- 검증 대상 구현 HEAD: `36514fbd590a025abd85a0cc9e26dd17be2bc09f`
- 로컬 자동 검사 결과: **PASS**
- 실제 Codex 세션 smoke Q2: **미실행**

이 보고서는 구현 HEAD의 정적 지시문 계약, 셸 회귀, mock 행동 검사를 기록한다. 보고서 커밋은 검증 대상 구현 SHA에 포함하지 않는다.

## 검증 결과

| 검사 | 관찰 결과 |
|---|---|
| `python -m unittest tests.test_codex_skill_layout tests.test_codex_skill_context tests.test_codex_skill_pipeline tests.test_codex_skill_questions -v` | PASS — 64 tests, `OK` |
| `python -m unittest discover -s tests -p "test_codex_*.py" -v` | PASS — 148 tests, 205.794초, `OK` |
| `python scripts/sync-codex-resources.py --check` | PASS — exit 0, 출력 없음 |
| `bash scripts/lint-consistency.sh` | PASS — 36/36, `정합성 린트 통과` |
| `bash scripts/hook-tests.sh` | PASS — 6개 그룹, `훅 회귀 테스트 통과` |
| `bash scripts/test-behavior-tests.sh` | PASS — 30 pass, 0 fail |
| `git diff --check f917cdff98dd0f33f3f82a52ee26387eda42df7d 36514fbd590a025abd85a0cc9e26dd17be2bc09f` | PASS — exit 0, 공백 오류 없음 |

## 지시문 배치와 연결

구현 diff는 19개 파일, 2,086 insertions/1,775 deletions이다. gx-context의 모드 B·C·D·E는 `modes/create.md`, `from-document.md`, `update.md`, `sync.md`에 각각 한 번만 있으며, `SKILL.md`는 선택된 모드를 `Read("modes/...")`로 연결한다. 문서 기반 모드의 내부 신규·갱신 경로와 스캔 중 README 또는 용어 사전이 빠진 경우의 B-0 읽기 순서도 집중 테스트에서 통과했다.

gx-dev·gx-tdd는 각자 `references/intent-routing.md`, `pipeline-state.md`, `interaction-contract.md`를 Phase 실행 루프 전에 지정 순서로 읽는다. 이동한 여섯 헤더는 스킬별로 하나의 reference 파일에만 정확히 존재하며, Phase 스킵 금지와 gx-tdd Phase 합치기 금지 게이트는 메인 `SKILL.md`에 남아 있다. `test_codex_skill_layout.py`는 대상 링크가 **참조 파일 자신의 위치**에서 존재하는지 검사하고, 출력 템플릿 안의 생성 예정 링크는 건너뛰되 실제 지시문 링크가 없을 때 실패하는 음성 사례도 검사한다. gx-context 내부 `Read`는 스킬 디렉터리 기준으로, gx-tdd의 phase·frontend 포인터는 해당 reference 기준으로 확인했다.

`test_codex_skill_context.py`, `test_codex_skill_pipeline.py`, `test_codex_skill_questions.py`는 이동 후 메인 파일과 필수 reference/mode를 묶어 읽어 기존 원장·파이프라인·질문 계약을 검사한다. 따라서 회귀 결과는 **이동한 계약 내용과 링크의 정적 충실도**를 뒷받침한다. 이전 문장과 새 문장을 바이트 단위로 동일하다고 주장하는 검사는 아니다. 구현 diff와 새 파일 소유 범위를 별도로 확인했다.

| 메인 지시문 | 현재 행 수 | 계획 한도 |
|---|---:|---:|
| `gx-context/SKILL.md` | 161 | 320 |
| `gx-dev/SKILL.md` | 211 | 520 |
| `gx-tdd/SKILL.md` | 249 | 520 |

## 실측 상태

정적 테스트, hook 회귀, behavior mock은 실제 설치된 Codex 모델 세션의 질문 UI와 도구 trace를 실행하지 않는다. `tests/codex-smoke.md`의 Q2에서 요구하는 실제 세션 질문·선택지·UI Other 응답 및 같은 id의 `codex_hook.py capture` 기록은 확보하지 않았으므로 **Q2 실측은 미실행**이다. 로컬 자동 검사는 위 구현 HEAD에서 모두 통과했으며, 실제 세션 검증은 통합 후 별도 증거로 기록해야 한다.
