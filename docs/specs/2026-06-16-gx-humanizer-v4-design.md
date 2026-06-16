# gx-humanizer v4.0 설계 — humanize-korean 우수 요소 흡수

- 작성일: 2026-06-16
- 상태: 승인됨 (brainstorming 완료)
- 대상 스킬: `.claude/skills/gx-humanizer`

## 1. 배경

외부 플러그인 `im-not-ai`의 `humanize-korean`(v1.5, 로컬 설치본 기준)을 분석한 결과,
우리 `gx-humanizer`(v3.2)에 없는 신뢰성 장치와 산출물 관리 체계가 확인되었다.
본 설계는 humanize-korean의 우수 요소를 흡수하되, gx-humanizer의 정체성(단일 스킬 경량성,
한/영 양국어 지원, "숨결 불어넣기")을 유지하는 것을 목표로 한다.

### 비교 요약 (현행)

| 축 | gx-humanizer v3.2 | humanize-korean v1.5 |
|----|-------------------|----------------------|
| 형태 | 단일 스킬 | 멀티에이전트 오케스트레이터 |
| 언어 | 한국어 + 영어 | 한국어 전용 |
| 모드 | audit / rewrite | Fast / Strict |
| 의미 보존 검증 | 원칙 1줄 | 전담 에이전트 |
| 과윤문 방지 | 없음 | 전담 에이전트 + 변경률 상한 |
| 산출물 | 인라인 | 단계별 파일(_workspace) |

## 2. 흡수 목표 (우선순위 — 4가지 전부)

1. 출력 품질 신뢰성: 의미 보존 검증, 과윤문 방지, 변경률 상한
2. 산출물·이력 관리: 단계별 파일 저장, run-id 기반 이력
3. 한국어 윤문 심도: 장르별 치환 처방 + 핵심 학술 근거를 patterns-ko에 보강 (taxonomy 전수 이식은 비범위)
4. 처리 구조 파이프라인화: 정밀 모드의 검증 단계 분리

## 3. 핵심 결정

- **구조: 하이브리드.** 기본은 단일 스킬(경량·양국어 유지), 정밀 모드(`strict`)에서만 검증 에이전트를 호출한다.
- **검증 에이전트 모델: opus.** 의미 동등성·과윤문 판단은 추론 깊이가 중요.
- **산출물: 모드 연동.** 기본 모드는 최종본+요약 2개, strict는 단계별 전체.

근거: humanize-korean 자신도 v1.4까지 풀 멀티에이전트로 갔다가 "5,000자에 25분"
성능 문제로 v1.5에서 단일 monolith로 롤백했다. 경량 기본 + 정밀 옵션의 하이브리드가
검증된 절충안이다.

## 4. 모드 체계 (2종 → 3종)

| 모드 | 동작 | 비고 |
|------|------|------|
| `audit` | 감지 리포트만 (수정 안 함) | 현행 유지 |
| `rewrite` | 감지 + 수정 + 변경률 상한 | 현행 + 안전장치 |
| `strict` (신규) | rewrite + 의미보존 검증 + 과윤문 검증 + 단계별 산출물 | 신규 |

### 트리거
- 사용자가 "정밀", "꼼꼼히", "--strict" 등을 명시 → `strict`
- 입력 8,000자 초과 → `strict` 자동 승급 (1줄 고지)
- 그 외 → 기존 audit/rewrite 결정 흐름 유지

## 5. 아키텍처 (하이브리드)

### 기본 모드 (audit / rewrite)
스킬 단독 실행. 추가 에이전트 호출 없음. 현행 경량 동작 유지.

### 정밀 모드 (strict)
스킬이 오케스트레이터가 되어 검증 에이전트를 순차 호출한다.

```
입력
  ↓ [스킬: 탐지 + 윤문]  (양국어 패턴 K/E/C)
03_rewrite.md
  ↓ [humanizer-fidelity]  의미 동등성 감사 → 04_fidelity.json
  ↓ (위반 edit 롤백 지시 시 재윤문)
  ↓ [humanizer-naturalness]  과윤문·AI티 잔존 검토 → 05_naturalness.json
  ↓ (재윤문 트리거 시 Phase 재실행, 최대 2회)
final.md + summary.md
```

### 신규 에이전트 (2종, opus, 양국어)

- **`humanizer-fidelity`** — 의미 보존 감사
  - 입력: 원문 + 윤문본 + 변경 항목(diff)
  - 검사: 사실·주장·수치·고유명사·직접인용·인과관계·순서가 훼손됐는지
  - 출력: edit 단위 판정(pass/rollback) + 사유
- **`humanizer-naturalness`** — 과윤문/잔존 검토
  - 입력: 윤문본 + 탐지 리포트
  - 검사: 과도한 문학체(과윤문), AI티 잔존, 리듬/장르 이탈
  - 출력: accept / rewrite_round / rollback 판정 + 대상 항목

## 6. 산출물 (모드 연동)

- 위치: 소비 프로젝트 cwd의 `.humanize/{run-id}/`
- run-id: `YYYY-MM-DD-NNN` (Glob로 표지 파일 매칭하여 시퀀스 조회, Bash ls 금지)
- `.gitignore`에 `.humanize/` 추가

| 파일 | audit | rewrite | strict |
|------|-------|---------|--------|
| `final.md` (최종본) | - | O | O |
| `summary.md` (변경 요약·메트릭) | O | O | O |
| `01_input.txt` | - | - | O |
| `02_detection.json` | - | - | O |
| `03_rewrite.md` | - | - | O |
| `04_fidelity.json` | - | - | O |
| `05_naturalness.json` | - | - | O |

(audit는 리포트만 인라인 출력하되 summary.md는 남긴다.)

## 7. 안전장치 (humanize-korean 핵심 흡수)

- **변경률 상한: 30% 경고 / 50% 강제 중단** (rewrite·strict 공통)
- 의미 불변 최상위 원칙 + Do-NOT list (수치·고유명사·직접인용 불가침)
- register(격식체) 보존, 장르 이탈 금지
- strict에서 재윤문 루프 최대 2회, 미해결 시 사람 개입 보고

## 8. 유지할 우리 강점 (불변)

- 한/영 양국어 패턴 (K1~K19 / E1~E19 / C1~C6)
- "숨결 불어넣기" 섹션 (블로그/에세이/SNS 한정)
- 콘텐츠 6유형별 적용 기준
- audit/rewrite 기본 경량 동작

## 9. 구현 범위

### 신규
- `agents/humanizer-fidelity.md`
- `agents/humanizer-naturalness.md`

### 수정
- `.claude/skills/gx-humanizer/SKILL.md`: 3모드 체계, strict 오케스트레이션, 변경률 상한, 산출물 규칙
- `.claude/config.json`: 신규 2개 에이전트 contextLimits 등록
- `.gitignore`: `.humanize/` 추가
- `references/patterns-ko.md`: 장르별 치환 처방 표 + 주요 K 패턴 핵심 학술 근거 보강 (목표 3)

### 유지 (수정 없음)
- `references/patterns-en.md`, `patterns-common.md`

## 10. 비범위 (Out of Scope)

- 웹 서비스화 (humanize-korean의 web-service-spec 미흡수)
- taxonomy SSOT 전수 이식(40+ 패턴 전수·논문 29편 인용) — 핵심 근거·장르 처방만 흡수하고 전수 이식은 후속 과제
- 모델별(GPT/Claude/Gemini) 패턴 분포 차등

## 11. 검증 전략

- audit/rewrite 기본 동작이 현행과 동일하게 유지되는지 (회귀 없음)
- strict 모드에서 의미 훼손 케이스를 fidelity가 잡아 롤백하는지
- 변경률 50% 초과 입력에서 강제 중단되는지
- 영어 텍스트가 strict에서도 정상 처리되는지 (양국어 회귀 없음)
- 장르별 치환 처방이 rewrite 결과에 실제 반영되는지 (목표 3)
