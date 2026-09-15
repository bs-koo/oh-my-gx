# gx-context·gx-dev·gx-tdd 지시문 모듈화 검증

- 검증일: 2026-09-15
- 분기: `refactor/skill-instruction-layout`
- 변경 비교 기준: `f917cdff98dd0f33f3f82a52ee26387eda42df7d`
- 검증 대상 구현 HEAD: `4ba31d7bda7990a77135ff3e11824db46331249a`
- 로컬 자동 검사 결과: **PASS**
- 실제 Codex 세션 smoke Q2: **미실행**

이 보고서는 구현 HEAD의 정적 지시문 계약, 셸 회귀, mock 행동 검사를 기록한다. 이 보고서의 갱신 커밋은 검증 대상 구현 SHA에 포함하지 않는다.

## 검증 결과

| 검사 | 관찰 결과 |
|---|---|
| `python -m unittest tests.test_codex_skill_layout tests.test_codex_skill_context tests.test_codex_skill_pipeline tests.test_codex_skill_questions -v` | PASS — 67 tests, `OK` |
| `python -m unittest discover -s tests -p "test_codex_*.py" -v` | 이전 구현 `9f6c1a49b0eabe2a00eeb3af8320140e86e4a7b4`에서 PASS — 151 tests, 188.288초, `OK`; 이번 문구·테스트 보강 후 재실행하지 않음 |
| `python scripts/sync-codex-resources.py --check` | PASS — exit 0, 출력 없음 |
| `bash scripts/lint-consistency.sh` | PASS — 36/36, `정합성 린트 통과` |
| `bash scripts/hook-tests.sh` | 이전 구현 `9f6c1a49b0eabe2a00eeb3af8320140e86e4a7b4`에서 PASS — 6개 그룹; 이번 라우팅 문구·정적 테스트 변경 후 재실행하지 않음 |
| `bash scripts/test-behavior-tests.sh` | 이전 구현 `9f6c1a49b0eabe2a00eeb3af8320140e86e4a7b4`에서 PASS — 30 pass, 0 fail; 이번 라우팅 문구·정적 테스트 변경 후 재실행하지 않음 |
| `git diff --check f917cdff98dd0f33f3f82a52ee26387eda42df7d 4ba31d7bda7990a77135ff3e11824db46331249a` | PASS — exit 0, 공백 오류 없음 |

## 지시문 배치와 연결

보고서 파일을 제외한 구현 diff는 20개 파일, 2,128 insertions/1,777 deletions이다. 최종 리뷰 수정은 `gx-context/SKILL.md`, `modes/create.md`, `gx-ralph/SKILL.md`, `test_codex_skill_layout.py`의 4개 파일이며, 마지막 보강은 그중 메인 `SKILL.md`와 layout 테스트 2개 파일이다. gx-context의 모드 B·C·D·E는 `modes/create.md`, `from-document.md`, `update.md`, `sync.md`에 각각 한 번만 있으며, `SKILL.md`는 선택된 모드를 `Read("modes/...")`로 연결한다. 문서 기반 모드의 내부 신규·갱신 경로, 기존 도메인에 신규 모드로 진입해 갱신을 선택할 때 메인 로딩 규칙과 B-1 분기의 D 전환·B 종료, 스캔 중 루트 파일이 모두 있어도 새 도메인의 status.md 생성 전에 B-9-1의 5열 원장과 gx-sync cursor를 읽는 순서가 집중 테스트에서 통과했다.

gx-dev·gx-tdd는 각자 `references/intent-routing.md`, `pipeline-state.md`, `interaction-contract.md`를 Phase 실행 루프 전에 지정 순서로 읽는다. 이동한 여섯 헤더는 스킬별로 하나의 reference 파일에만 정확히 존재하며, Phase 스킵 금지와 gx-tdd Phase 합치기 금지 게이트는 메인 `SKILL.md`에 남아 있다. `test_codex_skill_layout.py`는 대상 링크가 **참조 파일 자신의 위치**에서 존재하는지 검사하고, 출력 템플릿 안의 생성 예정 링크는 건너뛰되 실제 지시문 링크가 없을 때 실패하는 음성 사례도 검사한다. gx-context 내부 `Read`는 스킬 디렉터리 기준으로, gx-tdd의 phase·frontend 포인터는 해당 reference 기준으로 확인했다.

gx-ralph의 verify 지문 정본 포인터는 `../gx-tdd/references/pipeline-state.md`의 "verify 지문" 절로 갱신했다. 문서 링크의 실제 대상과 절 제목도 집중 테스트로 확인했다.

`test_codex_skill_context.py`, `test_codex_skill_pipeline.py`, `test_codex_skill_questions.py`는 이동 후 메인 파일과 필수 reference/mode를 묶어 읽어 기존 원장·파이프라인·질문 계약을 검사한다. 따라서 회귀 결과는 **이동한 계약 내용과 링크의 정적 충실도**를 뒷받침한다. 이전 문장과 새 문장을 바이트 단위로 동일하다고 주장하는 검사는 아니다. 구현 diff와 새 파일 소유 범위를 별도로 확인했다.

| 메인 지시문 | 현재 행 수 | 계획 한도 |
|---|---:|---:|
| `gx-context/SKILL.md` | 161 | 320 |
| `gx-dev/SKILL.md` | 211 | 520 |
| `gx-tdd/SKILL.md` | 249 | 520 |

## 실측 상태

정적 테스트, hook 회귀, behavior mock은 실제 설치된 Codex 모델 세션의 질문 UI와 도구 trace를 실행하지 않는다. `tests/codex-smoke.md`의 Q2에서 요구하는 실제 세션 질문·선택지·UI Other 응답 및 같은 id의 `codex_hook.py capture` 기록은 확보하지 않았으므로 **Q2 실측은 미실행**이다. 이번 구현 HEAD에서는 집중 테스트·sync·lint·diff 검사가 통과했고, 전체 Codex·hook·behavior 결과는 바로 이전 구현 SHA에서 얻었다. 실제 세션 검증은 통합 후 별도 증거로 기록해야 한다.
