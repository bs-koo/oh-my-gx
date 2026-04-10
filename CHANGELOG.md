# Changelog

## v1.6.4 (2026-04-10) — AskUserQuestion 전수 구조화 및 스킬 강제 강화

### Fixes
- **커밋/PR 스킬 강제 3중 방어**: gx-dev 파이프라인이 길어져 컨텍스트 압축 후 오케스트레이터가 `git commit`/`gh pr create`를 직접 실행하는 문제를 방지. `phase-complete.md` 상단 CRITICAL 경고, `gx-dev/SKILL.md` "커밋/PR 스킬 강제" 섹션, `skill-routing.md` "내부 파이프라인에서도 동일 적용" 섹션 3곳에 명시
- **AskUserQuestion 비구조화 호출 일소**: 플러그인 전체에서 서술형/인라인/YAML 형태로 남아있던 AskUserQuestion 호출을 모두 JSON 스키마(`questions: [{header, question, multiSelect, options}]`)로 변환 (gx-commit, gx-context, gx-setup, gx-research, gx-humanizer, gx-pull-request, gx-lens, gx-dev phases 전반)
- **자유 입력 Other 유도 패턴 통일**: 사용자가 자유 입력해야 하는 질문에서 `"직접 입력"`/`"답변 입력"`/`"주제 입력"` 같은 모호한 메타 라벨을 `"Other로 입력"` + `"Other로 이동해서 ~을 자연어로 입력해주세요"` description으로 통일. 사용자가 라벨을 실제 입력 버튼으로 오인하던 UX 문제 해결
- **모드/VCS 선택 매핑 정합성**: gx-dev 모드 선택(`normal`→`"전체 파이프라인"`)과 gx-setup VCS 선택(`git`→`"Git"`)의 후속 처리 텍스트를 새 label과 일치시킴
- **SVN 비밀번호 수집 제거**: gx-setup에서 SVN 사용자명/비밀번호를 AskUserQuestion으로 수집하던 보안 이슈 제거. 대신 사용자에게 터미널에서 `svn info <URL>`로 사전 캐시하도록 안내
- **중복 규칙 통합**: agents/*.md 9개 파일에 중복 정의된 한국어/이모지/사과 규칙을 `.claude/rules/behavior.md`의 "8. 소통 원칙" 섹션으로 통합. `git-workflow.md`의 커밋 규칙은 `skill-routing.md` 참조로 축약

### Added
- **AskUserQuestion 스키마 규칙 확장**: `questions` 배열 한계를 `1~4개`에서 `1~5개`로 확장 (gx-context B-2 검증 질문 5개 일괄 호출 지원). 자유 입력 가이드 라벨 패턴 명문화

## v1.6.3 (2026-04-08) — AskUserQuestion 스키마 수정

### Fixes
- **AskUserQuestion "invalid tool parameter" 에러 수정**: gx-dev 스킬의 모든 AskUserQuestion 호출 패턴을 실제 도구 스키마(`questions` 배열, `header`, `multiSelect`, `{ label, description }`)에 맞게 수정. 설계/PRD 단계에서 마크다운이 렌더링되지 않고 에러가 발생하던 문제 해결
- **승인 패턴 options 최소 2개 준수**: 기존 "승인" 단일 옵션 → "승인" + "수정 요청" 2개로 변경 (스키마 `minItems: 2` 준수)
- **"직접 입력" 중복 옵션 제거**: UI가 자동 제공하는 "Other"와 중복되던 "직접 입력" 선택지를 모든 phase에서 제거

### Added
- **AskUserQuestion 스키마 규칙 섹션**: SKILL.md에 `questions` 배열 필수, `header` 최대 12자, `options` 2~4개, `preview` 선택 등 스키마 규칙을 명문화

## v1.6.2 (2026-04-03) — Skill 도구 누락 수정 및 코드 미리보기 제거

### Fixes
- **phase-complete Skill 호출 불가 수정**: gx-dev SKILL.md의 `allowed-tools`에 `Skill` 도구가 누락되어 phase-complete에서 `/gx-commit`, `/gx-pull-request` 스킬 호출이 차단되던 버그 수정

### Removed
- **코드 미리보기 기능 제거**: phase-design의 미리보기 선택지, phase-implement의 Step 1-preview 전체, preview-written 분기를 제거. coder agent가 Write/Edit 도구에 접근 가능하여 미리보기 모드에서도 실제 파일 수정을 방지할 수 없는 구조적 한계로 삭제

## v1.6.1 (2026-03-31) — 모든 모드에서 context 동기화 지원

### Features
- **context 최신화 (Step 3-0)**: phase-setup에서 베이스 브랜치 기준으로 context/를 자동 최신화. 작업 브랜치 변경 감지 시 사용자 확인 후 덮어쓰기
- **커밋 기반 status.md 갱신 (경로 B)**: HOTFIX/IMPLEMENT 모드에서 커밋 메시지 ↔ status.md 항목을 대조하여 사용자 확인 후 갱신
- **diff 기반 context 환류**: HOTFIX(diff+경량PRD), IMPLEMENT(diff only)에서도 glossary/architecture 갱신 후보를 추출하여 제안
- **context 자동 커밋 + 조건부 push**: status.md 갱신/환류 반영 시 별도 커밋 생성, context 커밋이 1건 이상일 때만 추가 push

### Fixes
- **HOTFIX+REJECT 보호**: HOTFIX 모드에서 인수검증 REJECT 시 status.md 갱신을 건너뛰도록 분기 규칙 추가
- **--resume context 복원**: 재개 시 context 최신화(Step 3-0) + DOMAIN_CONTEXT 탐색을 독립적으로 재실행
- **SVN 가드**: phase-complete Step 3에 SVN 건너뛰기 명시 (브랜치 기반 커밋 로그 비교 불가)
- **BASE_BRANCH 변수 등록**: SKILL.md 공유 변수 목록에 BASE_BRANCH 추가
- **git diff 명령 수정**: Step 3-0에서 `diff HEAD` → `diff BASE_BRANCH HEAD`로 변경하여 커밋된 context 변경도 감지
- **매칭 알고리즘 명시**: 경로 B에서 FR/BR ID 직접 매칭(우선) + 키워드 매칭(보조) 규칙 추가
- **Step 참조 통일**: --resume의 "Step 3.5" → "Step 3의 5번 항목"으로 정정

## v1.6.0 (2026-03-30) — 병렬 배치 설계 도입 및 승인 UX 개선

### Features
- **architect 의존성 힌트 기반 병렬 배치**: 구현 순서에 `(의존: N, M)` 표기를 도입하여 독립 단계를 병렬 실행 가능하게 함. 기존 레이어 순서 맹목 추종 문제 해결
- **3계층 의존성 분석**: 설계서 힌트(1차) → 파일 잠금(오버라이드) → import 검증(오버라이드) 구조로 안전한 병렬 배치 구성
- **예비 배치 미리보기**: 구현 계획 승인 시 간이 위상 정렬로 배치 구성을 사용자에게 미리 표시

### Improvements
- **승인 UX 간소화**: PRD/설계/구현계획 승인의 AskUserQuestion에서 중복 '직접 입력' 옵션 제거, Other(자동 제공)로 통합하여 2단계 → 1단계로 단축 (4곳)
- **구현 계획 재시도 무제한**: 2회 제한 제거, 사용자가 승인할 때까지 반복하도록 다른 Phase와 통일
- **구현 순서 테이블 정합성**: 헤더를 3컬럼(배치/단계·설명/대상 파일)으로 예시와 일치시킴
- **기존 설계서 폴백**: `(의존:)` 표기가 없는 기존 설계서는 이전 단계에 순차 의존으로 간주하여 --resume 호환 보장

## v1.5.1 (2026-03-25) — gx-dev 구동 안정성 및 브랜치별 산출물 분리

### Features
- **.dev/ 브랜치별 폴더 분리**: `DEV_DIR` 변수 도입으로 `.dev/{branch-slug}/` 형식으로 브랜치별 산출물 격리. 여러 기능을 번갈아 개발해도 PRD/설계서/state가 유실되지 않음
- **복수 작업 resume 선택**: `--resume` 시 `in_progress` 상태 작업이 여러 개면 AskUserQuestion으로 선택 가능

### Fixes
- **implement(경량 구현) 모드 보강**: 산출물 게이트에 implement 모드 예외 추가, phase-implement에 경량 구현 분기 신규 추가, Context Slicing에 coder/qa-manager implement 분기 반영
- **hotfix 인수검증 모순 수정**: phase-complete에서 hotfix가 인수검증을 건너뛴다는 잘못된 노트 제거 (hotfix는 경량 PRD를 생성하므로 인수검증 실행이 맞음)
- **SVN VCS_TYPE 설정 누락**: phase-setup SVN 분기에서 `VCS_TYPE = "svn"` 명시 추가
- **Step 번호 참조 정합성**: SKILL.md의 phase-setup Step 참조를 실제 번호 체계(Step 0~7)와 일치시킴
- **Phase 진행 표현 통일**: Phase 파일의 "phase-X로 진행"을 "다음 Phase로 진행"으로 통일하여 루프 기반 실행과 일관성 확보
- **diff 갱신 독립 Step 분리**: phase-complete의 diff 갱신을 인수검증 블록에서 분리하여 PRD 부재 시에도 실행
- **SELF_CHECK 변수 복원**: phase-review 문서 로드에 self-check.md Read 절차 추가
- **코드 미리보기 연계**: phase-design 승인 후 `preview-written` 플래그로 phase-implement Step 건너뛰기 분기 추가
- **--resume implement 모드 복원**: phase-implement에서 mode 필드 확인 후 Step 1/1.5 건너뛰기 로직 추가

### Improvements
- **AskUserQuestion 구조화**: 전 파일의 평문 AskUserQuestion 11건을 JSON 구조화 형식(question/options/description)으로 변환
- **승인/수정 패턴 통일**: value 네이밍을 `modify` → `input`으로 일관되게 통일
- **PR 머지 규칙 완화**: 머지 금지 규칙 제거, force push 금지만 유지하여 사용자 자율성 확보

## v1.5.0 (2026-03-24) — 스킬 네임스페이스 gx- prefix 추가

### Breaking Changes
- **모든 스킬명에 `gx-` prefix 추가**: `/commit`→`/gx-commit`, `/context`→`/gx-context`, `/dev`→`/gx-dev`, `/humanizer`→`/gx-humanizer`, `/lens`→`/gx-lens`, `/pull-request`→`/gx-pull-request`, `/research`→`/gx-research`, `/setup`→`/gx-setup`
- `/gx` 입력 시 전체 스킬 목록이 자동완성되어 사용성 향상

### Improvements
- **스킬 description 간결화**: 각 스킬의 설명을 한 줄로 정리하여 터미널 표시 가독성 개선
- **네임스페이스 충돌 해결**: oh-my-claudecode, Claude 기본 명령어 등 다른 플러그인과의 스킬명 충돌 방지

## v1.4.1 (2026-03-24) — setup VCS 감지 및 CLI 자동 설치 개선

### Fixes
- **VCS 감지 단순화**: `svn info` 감지를 제거하고 `git rev-parse` 성공/실패로 분기. 실패 시 사용자에게 Git/SVN/없음 선택지 제시. Git 선택 시 `git init` 자동 실행
- **gh CLI 자동 설치**: svn과 동일한 패키지 매니저 자동 설치 패턴 적용. 기존 안내 링크만 표시하던 방식에서 개선
- **winget 최우선 감지**: Windows 10/11 기본 내장 winget을 최우선 패키지 매니저로 추가. 별도 패키지 매니저 없이 gh/svn CLI 자동 설치 가능
- **SVN 인증 단계 추가**: 2단계(인증)에서 `svn info`로 캐시된 자격 증명 확인 후, 실패 시 사용자에게 아이디/비밀번호 입력 요청
- **allowed-tools 보강**: setup 스킬에 winget, choco, scoop, brew, sudo, test 명령 허용 추가

## v1.4.0 (2026-03-23) — SVN 프로젝트 지원

### Features
- **SVN 프로젝트에서도 사용 가능**: `/gx-setup`에서 VCS(Git/SVN)를 자동 감지하고 `config.json`에 저장. 이후 모든 스킬이 VCS 타입에 맞게 동작
  - `/gx-dev`: PRD → 설계 → 구현 → 리뷰까지 동일하게 동작. diff 수집은 `svn diff` 사용
  - `/gx-context`: 레포명 추출과 동기화 모드가 SVN 명령어로 분기
  - `/gx-lens`: 프로젝트 루트 감지가 `svn info`로 폴백
  - `/gx-commit`, `/gx-pull-request`: SVN에서는 미지원 안내 후 조기 종료
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
- **Google Chat 알림 중복 방지**: `/gx-pull-request` 스킬에서 기존 PR 업데이트(`gh pr edit`) 시에도 알림이 발송되던 문제 수정
  - 신규 PR 생성(`gh pr create`) 시에만 알림을 발송하도록 선행 조건 가드 추가

## v1.3.1 (2026-03-17) — /gx-dev Phase 스킵 방지

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
  - `/gx-context --from` 연동으로 리서치 결과를 context 문서에 반영 가능
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
