# Changelog

## v1.4.2 (2026-03-27) — 에이전트 토큰 사용량 최적화

### Improvements
- **패턴 스냅샷 도입**: phase-setup Step 4에서 핵심 파일 3~5개의 구조적 정보(레이어 구조, 메서드 시그니처, 네이밍 컨벤션)를 발췌하여 코드 맵에 포함. 이후 에이전트가 동일 파일을 반복 Read하지 않음
- **product-owner Read 제거**: PO 프롬프트에서 프로젝트 루트 경로를 제거하고 소스 파일 직접 Read를 금지. 코드 맵과 패턴 스냅샷만으로 PRD 작성 (~47K 토큰 절감)
- **architect Read 제한**: 패턴 스냅샷을 우선 참조하고 추가 파일 Read를 핵심 파일 3개 이내로 제한 (~56K 토큰 절감)

## v1.4.1 (2026-03-24) — setup VCS 감지 및 CLI 자동 설치 개선

### Fixes
- **VCS 감지 단순화**: `svn info` 감지를 제거하고 `git rev-parse` 성공/실패로 분기. 실패 시 사용자에게 Git/SVN/없음 선택지 제시. Git 선택 시 `git init` 자동 실행
- **gh CLI 자동 설치**: svn과 동일한 패키지 매니저 자동 설치 패턴 적용. 기존 안내 링크만 표시하던 방식에서 개선
- **winget 최우선 감지**: Windows 10/11 기본 내장 winget을 최우선 패키지 매니저로 추가. 별도 패키지 매니저 없이 gh/svn CLI 자동 설치 가능
- **SVN 인증 단계 추가**: 2단계(인증)에서 `svn info`로 캐시된 자격 증명 확인 후, 실패 시 사용자에게 아이디/비밀번호 입력 요청
- **allowed-tools 보강**: setup 스킬에 winget, choco, scoop, brew, sudo, test 명령 허용 추가

## v1.4.0 (2026-03-23) — SVN 프로젝트 지원

### Features
- **SVN 프로젝트에서도 사용 가능**: `/setup`에서 VCS(Git/SVN)를 자동 감지하고 `config.json`에 저장. 이후 모든 스킬이 VCS 타입에 맞게 동작
  - `/dev`: PRD → 설계 → 구현 → 리뷰까지 동일하게 동작. diff 수집은 `svn diff` 사용
  - `/context`: 레포명 추출과 동기화 모드가 SVN 명령어로 분기
  - `/lens`: 프로젝트 루트 감지가 `svn info`로 폴백
  - `/commit`, `/pull-request`: SVN에서는 미지원 안내 후 조기 종료
- **setup 스킬 VCS 분기**: SVN 프로젝트에서는 gh CLI 대신 svn CLI를 확인하고, GH 인증과 Google Chat 연동을 건너뜀
- **pre-tool-guard SVN 가드**: Claude가 `svn commit`을 대신 실행하지 않도록 훅에서 차단
- **VCS 워크플로우 규칙 분리**: `git-workflow.md`를 Git/SVN 섹션으로 분리

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
