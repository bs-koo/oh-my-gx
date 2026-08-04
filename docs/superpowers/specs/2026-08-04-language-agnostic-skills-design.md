# 설계: oh-my-gx 언어 중립화 (Language-Agnostic Skills)

- 날짜: 2026-08-04
- 상태: 승인됨 (브레인스토밍 완료)
- 대상 릴리스: v1.21.0 (minor — 원래 v1.20.0 목표였으나 PR #68이 선점하여 재조준)
- 배경 요청: GX 사업본부 하드웨어 파트(C 언어)가 gx-lens/gx-dev/gx-tdd/gx-context 사용을 원함. 전수조사 결과 파이프라인 구조는 언어 중립적이나 기본 설정·편의 장치가 Java/Node 중심.

## 1. 문제 정의

전수조사에서 확인된 언어 종속 지점은 6곳이다:

1. `.claude/config.json` `projectTypes` 기본값이 `java-spring`·`node`뿐 — 그 외 언어는 기준선 게이트(phase-implement Step 0.5), Mechanical Gate(phase-review Step 0), verify 게이트(gx-verify Step 1)에서 매번 "검증 명령 미감지" 질문 발생.
2. 스킬 문서 내 하드코딩 명령 표(gx-verify Step 1, gx-tdd/gx-dev phase-review Step 0-1, phase-setup Step 6 ignore 표, agents/architect.md·coder.md 타입 표).
3. 스킬 frontmatter `allowed-tools` Bash 화이트리스트에 gradle/npm 계열만 존재 — 타 언어 명령은 매번 권한 프롬프트.
4. gx-verify 경고 측정 규약이 java-spring(`grep -ci "warning"`)·node(`grep -ci "warn"`)만 지원 — 그 외 타입은 warnings-baseline 비교 게이트 비활성.
5. 에이전트 문서 어휘·예시가 Java/OO 중심(test-architect의 DI/mock, testing-anti-patterns.md의 Java 예시), gx-context 자동 스캔이 Java/Node 패턴 중심, gx-setup의 무조건 JDK 확인.
6. gx-tech-debt 의존성 분석이 `gradlew dependencies`/`npm audit` 하드코딩.

## 2. 목표 / 비목표

**목표:**
- 임의의 언어/프레임워크 프로젝트가 최초 1회 등록 후 gx-tdd/gx-dev/gx-verify 전체 파이프라인을 질문·권한 프롬프트 없이 사용할 수 있다.
- 기존 java-spring/node 사용자는 무변경으로 현행과 동일하게 동작한다 (하위 호환).
- 게이트의 fail-closed 성격은 유지한다 (미등록 시 조용한 통과 금지).

**비목표:**
- 테스트 하네스 자동 구축 (부재 감지 시 안내 후 중단만 — 구축은 별도 요청으로 수행).
- 모든 언어의 프리셋 완비 (카탈로그는 제안용 힌트이며, SSOT는 config 등록 값).
- ralph 루프의 언어별 특화 (기존 메커니즘 그대로 config를 따름).

## 3. 확정된 결정 사항

| 결정 | 선택 | 근거 |
|------|------|------|
| 핵심 메커니즘 | 감지→등록 혼합 | 자동 감지로 제안, 사용자 확인 후 config `projectTypes`에 기록. 이후 config만 참조(SSOT). 결정적·재현 가능 |
| 권한 처리 | setup이 권한 등록 (+화이트리스트 소량 보강) | 등록된 명령의 prefix 권한을 사용자 확인 후 소비 프로젝트 `settings.local.json`에 추가 |
| 범위 | 경고 규약·에이전트 문서·gx-context 스캔·gx-tech-debt 전부 포함 | 4개 영역 모두 선택됨 |
| 감지 카탈로그 | 주요 스택 힌트 내장 | 제안 품질 확보. 목록 밖 스택은 LLM 추론 제안 + 사용자 확인 |
| 하네스 부재 | 감지+안내 후 중단 | 하네스 구축은 파이프라인 밖 별도 작업. 온보딩 가이드로 안내 |

## 4. 아키텍처 원칙

**config.json `projectTypes`가 유일한 SSOT다.** 모든 스킬·에이전트는 빌드/테스트/경고/아티팩트 정보를 config에서만 읽는다. 스킬 문서 내 명령 표는 전부 "예시(파생 사본 — SSOT는 config)"로 명시한다.

### projectTypes 스키마 확장 (신규 필드는 전부 선택)

```json
"c-make": {
  "detect": ["Makefile"],
  "build": "make",
  "test": "make test",
  "warningPattern": "warning:",
  "artifacts": ["build/", "*.o"]
}
```

- `warningPattern` (선택): gx-verify 경고 측정 규약이 `grep -ci "<패턴>"`으로 카운트할 패턴. 미설정 시 현행 "그 외 타입"과 동일하게 카운트 생략·보고만. **하위 호환**: java-spring/node는 필드 부재 시 기존 하드코딩 grep(`warning`/`warn`)을 폴백으로 유지한다.
- `artifacts` (선택): phase-setup Step 6의 VCS ignore 보강 표(현재 java/node 하드코딩)를 대체. 미설정 시 ignore 보강 생략. (`.dev/` 패턴은 당초 타입 무관 유지였으나, 사용자 결정(2026-08-04)으로 v1.21.0에서 협업 공유 대상으로 전환되어 ignore하지 않는다.)

기본 번들 템플릿(`.claude/config.json`)에는 java-spring/node에 신규 필드를 채워 배포한다.

## 5. 감지→등록 플로우

### 5.1 gx-setup 신설 단계: 프로젝트 타입 등록

VCS 감지 단계 이후에 실행한다:

1. **빌드 파일 스캔**: 프로젝트 루트에서 Makefile, CMakeLists.txt, Cargo.toml, pom.xml, pyproject.toml/setup.py, go.mod, *.csproj/*.sln, package.json, build.gradle(.kts) 등을 Glob.
2. **힌트 카탈로그 매칭**: 신설 번들 문서 `references/project-type-hints.md`(gx-setup 스킬 하위)에서 감지 파일 → 타입 키·제안 build/test 명령·warningPattern·artifacts·권한 prefix를 조회한다. 카탈로그에 없는 스택은 LLM이 프로젝트 구조를 근거로 제안하되 반드시 사용자 확인을 거친다 (환각 방지 — 제안 근거 명시).
3. **사용자 확인**: AskUserQuestion으로 제안 값 확인/수정 (테스트 명령은 자유입력 수정 가능).
4. **config 기록**: 확정 값을 `.claude/config.json` `projectTypes`에 기록. 이미 등록된 타입은 갱신하지 않고 유지(기존 설정 우선).
5. **권한 등록**: 확정된 build/test 명령의 실행 파일 prefix 권한(예: `Bash(make *)`, `Bash(ceedling *)`)을 AskUserQuestion 확인 후 소비 프로젝트 `.claude/settings.local.json`의 `permissions.allow`에 추가한다 (파일 부재 시 생성, 기존 항목 보존, 중복 추가 금지). 거부 시 추가하지 않고 "매 실행 시 권한 프롬프트가 발생할 수 있음"을 안내한다.

### 5.2 파이프라인 연동 (phase-setup Step 3.1)

gx-dev/gx-tdd의 프로젝트 타입 감지에서 `projectTypes` 미매칭 시, 위 5.1의 2~5를 인라인 실행한다 — "미감지 → 질문 1회 → 등록 → 이후 영구 자동". 사용자가 등록을 거부하면 현행 fail-closed 동작(각 게이트에서 직접 입력/중단)으로 진행한다.

### 5.3 힌트 카탈로그 내용 (초기 수록 범위)

C(Make/CMake+CTest/Ceedling), C++(CMake+CTest/Make), Python(pytest), Go, Rust(cargo), .NET(dotnet), Java(Gradle — 기존/Maven — 신규), Kotlin, JS/TS 변형(npm/pnpm/yarn/bun), PHP(composer+phpunit). 각 행: 감지 파일, 타입 키, 제안 build/test, warningPattern, artifacts, 권한 prefix. 카탈로그는 제안용이며 config 기록 값이 항상 우선한다.

### 5.4 gx-setup JDK 단계 조건화

현행 무조건 JDK 확인을 제거하고, 감지/등록된 타입에 java 계열(gradle/maven)이 있을 때만 실행한다.

## 6. 소비 지점별 변경

| 대상 | 변경 |
|------|------|
| gx-verify SKILL.md | Step 1 표에 "SSOT는 config `projectTypes` — 아래는 예시" 명시. Step 2 경고 측정 규약을 `warningPattern` 기반으로 일반화 (부재 시 java-spring/node 하드코딩 폴백 → 그 외 보고만). 감지 실패 안내에 "`/gx-setup`으로 타입 등록" 선택지 추가 |
| gx-tdd/gx-dev phase-review | Step 0-1 빌드 명령 표 → config 참조로 교체 (CLAUDE.md 탐색 폴백은 1순위 유지) |
| gx-tdd/gx-dev phase-setup | Step 3.1 미매칭 시 등록 플로우 인라인 실행 (5.2). Step 6 ignore 표 → `artifacts` 필드 참조 |
| gx-tdd phase-implement | Step 0.5 기준선 게이트에 하네스 부재 감지 추가: test 명령이 미등록이거나 실행 결과 0건이며, 테스트 파일 글롭(`*test*`/`*Test*`/`*spec*` 파일·디렉토리)이 0건이면 하네스 부재로 판정 → 온보딩 가이드(하네스 구축)를 안내하고 중단한다 (하네스 구축은 별도 요청으로 수행 — 결정 사항 5행) |
| gx-tdd/gx-dev/gx-ralph-iterate frontmatter | `allowed-tools`에 대표 도구 추가: `Bash(make *)`, `Bash(cmake *)`, `Bash(ctest *)`, `Bash(ceedling *)`, `Bash(cargo *)`, `Bash(mvn *)`, `Bash(dotnet *)`. gx-tech-debt frontmatter에는 대표 의존성 분석 명령(`Bash(cargo audit *)`, `Bash(pip-audit *)` 등 카탈로그 수록분)을 추가 |
| agents/architect.md, coder.md | 프로젝트 타입 감지 표 → "config `projectTypes` 참조 + 예시" 교체. 컨벤션 학습 지침에 비-OO 언어 항목 추가 (C: 모듈/헤더 경계, 네이밍, 에러 코드 반환 관습, 전처리기 사용 패턴) |
| agents/test-architect.md | testability 개념에 C 관점 병기: DI → 함수 포인터 테이블/링크 타임 치환, mock → CMock/FFF/링커 스텁, 격리 → HAL 추상화·듀얼 타깃(호스트 빌드) |
| gx-tdd references/testing-anti-patterns.md | 모의 3원칙 각 항목에 C 대응 예시 추가 (Java 예시 유지 — 병기) |
| gx-context SKILL.md | A-1 자동 스캔을 언어 중립 휴리스틱으로 재작성: 디렉토리 2레벨 구조 + 파일 확장자 클러스터 + 네이밍 패턴(접미사/접두사 군집) 기반. 언어별 구체 패턴(src/main/java, *Controller.java 등)은 예시 부록으로 이동 |
| gx-tech-debt SKILL.md | 의존성/취약점 분석을 projectTypes 기반 분기로 변경: 분석 명령이 알려진 타입(gradle/npm/cargo/pip 등)만 실행, 그 외는 "의존성 분석 미지원 — 수동 확인 안내"를 명시 보고 (조용한 생략 금지) |
| 신설 문서 | ① `references/project-type-hints.md` (gx-setup 하위, 감지 카탈로그) ② 테스트 하네스 구축 온보딩 가이드 (docs/ — C: Unity/Ceedling/CppUTest 선택 기준, 임베디드 듀얼 타깃 구조·HAL 목킹 포함) |

## 7. 하위 호환 / 에러 처리

- 신규 config 필드는 전부 선택 — 기존 config 무변경 동작. 신규 스킬 문서가 구 config를 읽는 경우와 구 스킬 문서(플러그인 구버전)가 신 config를 읽는 경우 모두 안전 (모르는 필드 무시).
- 감지 실패(알 수 없는 스택): LLM 추론 제안 + 사용자 확인 → 등록. 거부 시 현행 fail-closed 게이트 유지.
- VCS 축(git/svn)·모델 프로파일 축(standard/eco)과 직교 — 상호 영향 없음.
- 등록 플로우의 config 쓰기 실패(권한/파싱)는 현행 config 가드(phase-setup 3.0)의 에러 경로를 따른다.
- settings.local.json 갱신은 기존 내용을 보존하는 병합만 수행하며, 실패 시 수동 설정 안내로 폴백.

## 8. 검증 전략

- `scripts/lint-consistency.sh` 불변식 추가:
  1. 스킬 문서의 명령 표 주변에 "SSOT는 config" 문구 존재 확인 (gx-verify Step 1, phase-review Step 0-1).
  2. `warningPattern`/`artifacts` 필드 키 문자열이 gx-verify·phase-setup 문서와 번들 템플릿에서 일치.
  3. 힌트 카탈로그의 타입 키가 번들 config 템플릿과 충돌하지 않음.
- SKILL.md "드리프트 주의" 목록에 신규 중복 지점 등재 (힌트 카탈로그 ↔ 템플릿, 경고 규약 폴백).
- 수동 시나리오 테스트: C(Make) 샘플 프로젝트로 gx-setup(등록·권한) → gx-tdd 핵심 모드 1사이클(RGR+verify). 기존 java-spring/node 프로젝트로 회귀 확인 (등록 질문이 나오지 않아야 함).

## 9. 릴리스 계획

- 버전: v1.21.0. `.claude-plugin/plugin.json`·`marketplace.json`·`CHANGELOG.md` 3곳 동기.
- README·GitHub Pages·온보딩 가이드에 언어 중립화 반영.
- 구현 PR 3분할:
  1. **코어 메커니즘**: config 스키마 확장 + gx-setup 등록 단계·권한 등록·JDK 조건화 + 힌트 카탈로그 + gx-verify 일반화
  2. **파이프라인 소비 지점**: gx-tdd/gx-dev phase-setup·phase-review·phase-implement(하네스 감지) + allowed-tools + lint 불변식
  3. **에이전트/주변 스킬**: architect·coder·test-architect·testing-anti-patterns + gx-context 스캔 + gx-tech-debt + 온보딩 문서
