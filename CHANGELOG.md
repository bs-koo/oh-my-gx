# Changelog

## v1.2.0 (2026-03-16)

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

## v1.1.0 (2026-03-13)

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

## v1.0.0 (2026-03-12)

첫 정식 릴리즈. 7개 스킬 + 9개 에이전트 팀 기반 개발 자동화 플러그인.
