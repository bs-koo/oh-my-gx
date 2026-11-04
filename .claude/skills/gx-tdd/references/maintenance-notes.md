# gx-tdd 유지보수 노트

v2의 공통 진입은 gx-work, 개발 실행은 gx-tdd다. gx-dev와 그 phase는 제거했다. 실행 중에는 이 문서를 읽지 않는다. 스킬·역할·검증 계약을 수정할 때 아래 소유 지점과 소비 지점을 함께 대조한다.

| 계약 | 정본과 함께 확인할 곳 |
|---|---|
| 공통 Codex 실행·질문·모델 | gx-work/references의 codex-runtime·codex-questions·codex-models, scripts/codex-* helper, gx-setup 설정 템플릿 |
| 역할 본문·도구·티어 | agents/*.md → scripts/sync-codex-resources.py → gx-work/references/codex-roles. 생성물은 직접 편집하지 않는다 |
| 의도·종료점·계획 인계 | gx-work/SKILL·planning/handoff, scripts/gx-work.py, gx-tdd intent-routing·plan-handoff·execution-boundaries |
| TDD 진입·계획 검토·실행방법 | gx-work의 실제 진입 응답 → validate-handoff → gx-tdd setup 전 게이트. 구체 PRD/설계/T계획은 gx-tdd 내부, phase-implement 1.2 계획 링크·범위와 session/subagents/문서 종료를 한 응답으로 확인 → 1.3 기록 검증·flags 반영 → RGR. 계획 승인만 받아 방법이 빠진 경우에만 추가 선택 질문. pipeline-state·setup Step7/충돌 골격·setup-resume 0.05·단독 --phase 골격에서 원문/승인/run/계획 해시/방법을 함께 보존한다. --isolated 실제 분기와 충돌 처리를 확인하며 Ralph 명시 전환은 별도로 유지한다 |
| 도메인 원장·업무 W계획 | gx-context modes/plan.md·scripts/plan.py. scripts/plan-lint.py도 같은 파서/check를 사용한다. 기능 units/T태스크와 혼동하지 않는다 |
| 개발 전후 문서 | gx-context references/development-sync.md·scripts/development.py가 대조 정본. gx-work 진입·gx-tdd document-lifecycle·setup 3.0.4·requirements/implement·complete 순서를 함께 확인한다. 관련 문서/상태 투영 → 최종 verify/proof/지문 → .dev 완료 기록 → 요청한 commit/PR. RED 격리·문서 금지·완료 투영의 조건부 원복을 유지한다 |
| TDD 상태·지문 | gx-tdd pipeline-state, pre-tool-guard G3, gx-commit, gx-pull-request. pipeline/status/verify-status/verify-fingerprint 판별과 트리 성분 비교를 유지한다 |
| RED·IMPLEMENT·수리 | phase-implement 2-R/2-I, agents/red-writer·implementer, 단독 gx-red·green·refactor. RED 미열람·테스트 불변·현재 태스크만 실행·report/15줄 반환을 함께 확인한다 |
| 테스트 선택·증거 | scripts/gx-test-plan.py, test-execution.md, baseline·review·verify·commit·Ralph. 실제 Git 변경을 누락하지 않고, 코드/설정/명령/범위/run/log가 달라지면 재사용하지 않는다 |
| 리뷰 판정 | agents/reviewer가 spec/quality 블록과 동작 마커 정본. phase-implement 2-V·phase-review가 소비. 근거 부족은 review-evidence로 보강한 뒤 결함 여부를 판정한다 |
| 실패·반복 상한 | phase-implement fix loop와 failure-investigation. 라운드 4~5 격상·총5회·수리2회 등 각 루프의 기존 상한을 매 라운드 복원한다 |
| UI 테스트 | frontend-testing.md·testing-anti-patterns.md, red-writer, gx-red, phase-implement·design. 스타일/스냅샷을 동작 테스트로 오인하지 않는다 |
| 조건부 로드 | 모든 SKILL.md는 UTF8 LF 기준20KB미만. 긴 advisor·인증·strict·시각화·지문 설명은 필요 분기에서만 읽고 이동된 파일 기준 상대경로를 확인한다 |

## 검사

- 관련 기능의 좁은 테스트를 먼저 실행한다. 공통 배포·하네스 계약 변경은 통합 시 Codex 계약 검사를 한 번 수행하고, 실패·추가 변경이 있는 대상만 재실행한다.
- `python scripts/sync-codex-resources.py --check`, `bash scripts/lint-consistency.sh`를 수행한다. 보호 조건은 hook-tests, Ralph 경로는 runner 검사를 더한다.
- 기존 린트 번호 [3/36]·[23/36]·[33/36]·[34/36]은 역할/TDD/UI/태스크리뷰 불변식, [32/36]는 진입 예산을 확인한다. 테스트를 문구 유지용으로 약화하지 말고 실제 입력·행동·설치 경로와 연결한다.
- scripts/behavior-tests.sh는 phase의 `Task(subagent_type=...)`·`prompt: |`·4칸 들여쓰기 형식에서 프롬프트를 추출한다. 블록 형식을 바꾸면 mock을 확인하고, placeholder를 바꾸면 fixtures/behavior의 substitutions도 갱신한다.
- 정적·mock·helper 통과는 실제 설치 발견·모델 배정·질문 UI·훅 신뢰의 증거가 아니다. tests/codex-smoke.md의 미실행은 그대로 구분한다.
