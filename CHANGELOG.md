# Changelog

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
