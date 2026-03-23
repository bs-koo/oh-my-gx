# Changelog

## v1.3.5 (2026-03-23) — dev 파이프라인 스킬 호출 정규화

### Fixes
- **phase-complete 스킬 호출 방식 전환**: commit/PR 생성을 Read 방식에서 `Skill(skill: "oh-my-gx:commit")`, `Skill(skill: "oh-my-gx:pull-request")` 호출로 변경
  - 스킬의 절차, 포맷, allowed-tools를 우회하지 않고 반드시 스킬을 통해 실행
  - pull-request 스킬에 `--background`, `--extra-section` optional args 추가로 dev 컨텍스트 전달 지원

## v1.3.4 (2026-03-19) — Q&A 루프 사용자 승인 방식으로 전환

### Fixes
- **PRD/설계 Q&A 무한 반복 지원**: requirements(max 1), design(max 2) 고정 횟수 제한을 제거하고, 사용자가 "승인"할 때까지 반복하도록 변경
  - 사용자가 충분히 티키타카한 후 확정할 수 있어 PRD/설계 품질 향상
  - "수정 요청" 선택 시 에이전트가 다시 호출되어 처음부터 반복

## v1.3.3 (2026-03-19) — 에이전트 네임스페이스 분리

### Fixes
- **에이전트 프리픽스 충돌 해결**: `.claude/agents/` → `.claude-plugin/agents/`로 이동하여 `oh-my-gx:` 네임스페이스로 인식
  - `oh-my-claudecode:architect` 등 다른 플러그인 에이전트와의 이름 충돌 방지
  - plugin.json에 `agents` 경로 등록

## v1.3.2 (2026-03-18) — PR 알림 중복 발송 방지

### Fixes
- **Google Chat 알림 중복 방지**: `/pull-request` 스킬에서 기존 PR 업데이트(`gh pr edit`) 시에도 알림이 발송되던 문제 수정
  - 신규 PR 생성(`gh pr create`) 시에만 알림을 발송하도록 선행 조건 가드 추가

## v1.3.1 (2026-03-17) — /dev Phase 스킵 방지

### Fixes
- **Phase 스킵 방지**: LLM이 "요구사항이 명확하다", "범위가 작다" 등의 이유로 Phase를 임의 스킵하는 문제를 구조적으로 방지
  - Phase 라우팅을 서술형에서 기계적 for-loop 의사코드로 교체
  - CRITICAL 경고 + 산출물 게이트 (`.dev/prd.md`, `.dev/design.md` 존재 검증) 추가
  - 모드 미결정 시 AskUserQuestion으로 사용자에게 모드 선택 강제
  - Agent 팀 강제 — 외부 Agent(sisyphus-junior 등) 대체 금지

### Features
- **경량 구현 모드**: "구현만" 선택 시 `setup → implement → complete` 경로 (설계/리뷰 생략, 커밋/PR 포함)
- **모드 선택 UX**: 자연어 패턴 미매칭 시 3개 선택지 제시 (전체 파이프라인 / 긴급 수정 / 구현만)

## v1.3.0 (2026-03-16) — references/ 외부 규격 참조 기능

### Features
- **references/ 외부 규격 참조**: `references/` 디렉토리에 외부 규격/표준 문서를 넣으면 dev 파이프라인이 자동 참조
  - Setup: 5번째 병렬 작업으로 `references/` 탐색 + REFERENCES 변수 생성
  - Design: architect가 규격을 반영하여 설계서에 "준수 규격" 섹션 추가
  - Implement: coder가 규격을 준수하며 구현 (전체/배치/hotfix 모드)
  - Review: qa-manager가 규격 위반을 CERTAIN으로 보고, security-auditor가 보안 규격 감사
  - `references/` 없으면 기존과 동일하게 동작 (토큰 소모 없음)
  - `--resume` 시 REFERENCES 자동 복원

### Docs
- CLAUDE.md에 references/ 디렉토리 안내 섹션 추가
- README references/ 사용법 추가
- GitHub Pages references/ 설명 추가

## v1.2.0 (2026-03-16) — research 리서치 스킬

### Features
- **research 스킬 신설**: 웹 검색/문서 분석 기반 도메인 리서치 스킬
  - 인터뷰(주제/결과물/깊이) → 검색 → 검증 → 결과물 생성 워크플로우
  - 종합 리포트 / 비교표 / 핵심 요약 3가지 결과물 형태 지원
  - `/context --from` 연동으로 리서치 결과를 context 문서에 반영 가능
  - `.research/` 디렉토리에 중간 산출물 및 최종 결과물 저장

### Docs
- GitHub Pages research 스킬 섹션 추가
- README research 스킬 사용법 추가
- GitHub Pages UI/UX 개선 및 설명 통일

## v1.1.0 (2026-03-13) — coder 배치 병렬화

### Features
- **coder 배치 병렬화**: 독립적인 구현 단계를 배치로 묶어 병렬 coder Task로 호출
  - 의존성 분석 (파일 잠금 + import 참조) → 위상 정렬 → 배치 배정
  - 배치 모드 coder: 담당 파일만 수정, 개별 빌드 생략, 오케스트레이터가 통합 빌드
  - 배치 간 빌드 검증 + 에러 원인 특정 후 자동 수정
  - state.md 배치 추적 + --resume 호환
- dev 스킬 버전: 1.0.0 → 1.1.0

### Docs
- GitHub Pages 상세 문서 페이지 (index.html) 신규 생성
- README 간결화 + GitHub Pages 배지 링크 추가

### Migration
별도 마이그레이션 불필요. 기존 단일 coder 경로는 동일하게 동작한다.

## v1.0.0 (2026-03-12) — 첫 정식 릴리즈

첫 정식 릴리즈. 7개 스킬 + 9개 에이전트 팀 기반 개발 자동화 플러그인.
