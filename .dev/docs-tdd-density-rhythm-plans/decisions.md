# 의사결정 기록

AskUserQuestion으로 오간 질문과 선택을 자동 기록한다. 고른 것뿐 아니라 버린 선택지도 남으므로 왜 그렇게 정했는지가 추적된다.

## 2026-09-07 14:44 · 실행 방식

**Q.** 계획 두 개가 저장됐습니다 (`docs/superpowers/plans/2026-09-07-tdd-instruction-density.md`, `2026-09-07-tdd-session-implement.md`). 설계는 `docs/specs/2026-09-07-tdd-density-rhythm-design.md`입니다. 밀도 계획부터 어떻게 실행할까요?

선택지:

**→** 서브에이전트 구동 (추천) — superpowers:subagent-driven-development. 태스크마다 fresh 구현자 + 리뷰 + fix loop. 이전 두 계획(#81·#82)과 같은 방식. 밀도 계획 6태스크를 먼저 끝내고 PR → 머지 후 리듬 계획
- 세션 내 실행 — superpowers:executing-plans. 이 세션이 직접 태스크를 수행. 디스패치 없이 빠르지만 리뷰는 내 자기 검토뿐
- 계획만 커밋하고 멈춤 — docs/tdd-density-rhythm-plans 브랜치에 설계·계획 3파일만 커밋. 실행은 검토 후 별도 지시

**A.** 서브에이전트 구동 (추천)
