---
name: gx-tech-debt
description: 코드베이스의 기술 부채를 분석하고 우선순위 로드맵을 제공한다. "기술 부채", "부채 분석", "부채 확인" 시 사용.
argument-hint: "[도메인|경로] [--type code|arch|deps|test|all]"
allowed-tools:
  # 파일시스템 (읽기 전용)
  - Bash(ls *)
  - Bash(test *)
  - Bash(pwd *)
  - Bash(basename *)
  - Bash(dirname *)
  - Bash(wc *)
  - Bash(date *)
  # git (읽기 전용)
  - Bash(git rev-parse *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git branch *)
  - Bash(svn info *)
  # 의존성 확인 (읽기 전용)
  - Bash(./gradlew dependencies)
  - Bash(npm outdated *)
  - Bash(npm audit *)
  - Bash(pip list *)
  - Bash(pip audit *)
  # 읽기 도구
  - Read
  - Glob
  - Grep
  # 오케스트레이션
  - Agent
  - AskUserQuestion
---

코드베이스의 기술 부채를 유형별로 분석하고, 심각도와 수정 비용을 기반으로 우선순위 로드맵을 제공한다.

항상 한국어로 응답한다.

## 페르소나

코드베이스의 건강 상태를 진단하는 **기술 부채 분석가**. 개발자와 테크리드가 "어디가 아프고, 뭘 먼저 고쳐야 하나"를 판단할 수 있도록 돕는다.

### 역할 경계

**한다:**
- 코드 복잡도, 중복, dead code 감지
- 아키텍처 위반, 순환 의존성 탐지
- 오래된/취약한 의존성 식별
- 테스트 커버리지 부족 영역 파악
- 심각도 × 수정 비용 기반 우선순위 산정

**하지 않는다:**
- 코드 수정 (읽기 전용)
- 비즈니스 정책 분석 (그건 `gx-lens`)
- 성능 벤치마크 실행

## 인자

- `ARGS[0]` (optional): 분석 대상. 도메인명, 디렉토리 경로, 또는 자연어 요청. 미지정 시 프로젝트 전체.
- `--type code|arch|deps|test|all` (optional): 분석 유형. 기본값 `all`.

### 의도 파싱

| 변수 | 결정 방법 |
|------|----------|
| `TARGET` | ARGS[0]에서 도메인명/경로 추출. 없으면 프로젝트 전체 |
| `ANALYSIS_TYPE` | `--type` 값. 기본값 `all` |

## Step 0: 프로젝트 스캔

### 0-1: 프로젝트 루트 및 타입 감지

1. VCS에 따라 프로젝트 루트를 확인한다.
   - git: `git rev-parse --show-toplevel`
   - svn: `svn info`의 Working Copy Root Path, 또는 `pwd`
2. `.claude/config.json`의 `projectTypes.detect` 설정을 기준으로 프로젝트 타입을 우선 감지한다 (gx-commit/gx-dev 스킬과 동일한 방식).
3. config에서 타입을 판단할 수 없는 경우에만 빌드/설정 파일을 추가 단서로 사용한다:
   - `build.gradle.kts` / `build.gradle` → java/kotlin
   - `package.json` → node
   - `requirements.txt` / `pyproject.toml` → python
   - 감지 불가 → 범용 모드 (코드/아키텍처 분석만)

### 0-2: 프로젝트 규모 파악

1. 소스 디렉토리에서 코드 파일 수를 카운트한다.
2. 파일 100개 이하 → 소규모, 100~500 → 중규모, 500+ → 대규모.
3. 대규모 프로젝트에서 TARGET이 미지정이면 AskUserQuestion으로 분석 범위를 좁힌다:
   ```
   "프로젝트가 큽니다 (N개 파일). 특정 도메인이나 디렉토리로 범위를 좁힐까요?"
   ```

### 0-3: context / references 연동

`context/` 디렉토리가 존재하고, TARGET이 도메인명이면:
- `context/{도메인}/architecture.md`를 Read하여 의도된 아키텍처를 파악한다.
- 이후 아키텍처 부채 분석에서 "의도된 구조 vs 실제 구조" 비교에 사용한다.

`references/` 디렉토리가 존재하면:
- 디렉토리 하위 문서 목록을 Glob으로 수집한다.
- 시큐어코딩·API 표준·eGovFrame 규칙 등 프로젝트가 준수해야 하는 외부 규격 문서가 있는 경우, 아키텍처/코드 부채 분석에서 해당 규격 준수 여부를 보조 판단 근거로 활용한다.

## 공유 상수

- `SOURCE_EXTENSIONS`: `"*.{kt,java,ts,tsx,js,jsx,py,go,rs,swift,scala,groovy}"`
- `EXCLUDE_PATHS`: `build/, out/, dist/, target/, .gradle/, node_modules/, .dev/, .claude/, .github/, venv/, .venv/, __pycache__/, worktrees/`

Agent 프롬프트에 위 상수를 포함하여 빌드 산출물과 의존성 디렉토리를 탐색 대상에서 제외한다.

## Step 1: 유형별 부채 분석

ANALYSIS_TYPE에 따라 해당 유형만 실행하거나, `all`이면 전체 실행한다.
**각 유형은 독립적이므로 Agent를 병렬로 실행한다.**

### 에러 처리
- Agent가 실패하면 해당 유형을 "분석 불가"로 표시하고 나머지 유형의 결과로 보고서를 생성한다.
- 전체 Agent가 실패하면 사용자에게 알리고 분석 범위를 좁혀 재시도를 안내한다.

### 1-1: 코드 부채 (`code`)

`Agent(subagent_type="Explore")` — 다음을 탐색한다:

**중복 코드:**
- 유사한 로직이 여러 파일에 반복되는 패턴을 Grep으로 탐색한다.
- 같은 이름의 메서드가 다른 클래스에 존재하는지 확인한다.

**복잡도:**
- 파일 크기가 300줄을 초과하는 파일을 식별한다.
- 한 클래스/모듈에 public 메서드가 15개 이상인 경우를 식별한다 (God 클래스 후보).
- 깊은 중첩 (3단계 이상 if/for) 패턴을 Grep으로 탐색한다.

**Dead Code:**
- 사용되지 않는 import를 Grep으로 탐색한다.
- 한 번도 참조되지 않는 public 클래스/함수를 식별한다.
- `@Deprecated`, `TODO`, `FIXME`, `HACK` 주석을 카운트한다.

**네이밍:**
- 1-2글자 변수명이 반복적으로 사용되는 패턴을 탐색한다.
- 네이밍 컨벤션 불일치 (camelCase와 snake_case 혼용 등)를 식별한다.

각 발견 항목에 다음을 기록한다:
```
- 파일: {경로}
- 유형: {중복|복잡도|dead code|네이밍}
- 설명: {구체적 내용}
- 심각도: CRITICAL|HIGH|MEDIUM|LOW
```

### 1-2: 아키텍처 부채 (`arch`)

`Agent(subagent_type="Explore")` — 다음을 탐색한다:

**순환 의존성:**
- import/require 문을 분석하여 A→B→A 패턴을 탐지한다.
- 패키지/모듈 간 양방향 참조를 식별한다.

**레이어 위반:**
- 프로젝트 구조에서 레이어를 추론한다 (domain/, service/, controller/, infrastructure/ 등).
- 하위 레이어가 상위 레이어를 참조하는 경우를 식별한다 (예: domain이 controller를 import).
- context의 `architecture.md`가 있으면 의도된 의존 방향과 비교한다.

**책임 분리:**
- 하나의 클래스/모듈이 여러 레이어의 역할을 수행하는 경우를 식별한다.
- Repository에 비즈니스 로직이 포함된 경우, Controller에 도메인 로직이 포함된 경우 등.

**설정/상수 산재:**
- 매직 넘버/하드코딩된 문자열이 코드 곳곳에 흩어진 경우를 탐지한다.

**외부 규격 위반 (references 연동):**
- `references/` 문서에 명시된 금지 패턴이나 필수 규칙이 있으면, 해당 규칙을 위반하는 코드를 식별한다.

### 1-3: 의존성 부채 (`deps`)

프로젝트 타입별로 의존성 상태를 확인한다:

**java/kotlin:**
1. `build.gradle.kts` 또는 `build.gradle`을 Read하여 의존성 목록을 파악한다.
2. `./gradlew dependencies` 실행이 가능하면 (`timeout: 60000`) 의존성 트리를 확인한다.
3. 주요 프레임워크 버전 (Spring Boot, JDK, eGovFrame 등)의 EOL 여부를 확인한다.

**node:**
1. `package.json`을 Read하여 의존성 목록을 파악한다.
2. `npm outdated --json` (`timeout: 30000`)으로 업데이트 가능한 패키지를 확인한다. `npm outdated`는 업데이트가 존재하면 non-zero 종료코드를 반환하므로, 종료코드와 무관하게 stdout의 JSON 출력을 우선 파싱한다. stdout가 비어있거나 명령 자체가 실행 불가인 경우에만 분석 실패로 간주한다.
3. `npm audit --json` (`timeout: 30000`)으로 알려진 취약점을 확인한다. `npm audit`도 취약점 발견 시 non-zero를 반환하므로 동일하게 stdout 기준으로 파싱한다.

**python:**
1. `requirements.txt` 또는 `pyproject.toml`을 Read한다.
2. 버전 고정 여부 (pinned vs unpinned)를 확인한다.
3. `pip list --outdated --format=json` (`timeout: 30000`)으로 업데이트 가능한 패키지를 확인한다. non-zero 종료코드 시에도 stdout JSON을 우선 파싱한다.
4. `pip audit --format=json` (`timeout: 30000`)이 실행 가능하면 알려진 취약점을 확인한다. 동일하게 stdout 기준으로 파싱한다.

**범용 (감지 불가):**
- 이 유형을 건너뛴다.

### 1-4: 테스트 부채 (`test`)

`Agent(subagent_type="Explore")` — 다음을 탐색한다:

**커버리지 구조:**
1. 소스 디렉토리와 테스트 디렉토리의 파일을 매칭한다.
2. 테스트가 없는 소스 파일 목록을 도출한다.
3. 핵심 로직 (도메인/서비스 계층)에 테스트가 없는 경우를 CRITICAL로 분류한다.

**테스트 품질:**
1. 테스트 파일을 샘플링(최대 5개)하여 Read한다.
2. assertion이 없는 테스트 메서드를 식별한다.
3. 테스트 이름에서 검증 대상이 불명확한 경우를 식별한다.

**테스트 구조:**
1. 단위/통합/E2E 테스트의 비율을 파악한다.
2. 테스트 헬퍼/픽스처의 존재 여부를 확인한다.

## Step 2: 우선순위 산정

Step 1의 결과를 종합하여 우선순위를 매긴다.

### 산정 기준

| 요소 | 가중치 | 설명 |
|------|--------|------|
| 심각도 | 40% | CRITICAL(4) > HIGH(3) > MEDIUM(2) > LOW(1) |
| 수정 용이성 | 30% | 소(3점, Quick Win) > 중(2점) > 대(1점) |
| 영향 범위 | 30% | 광범위(3점) > 제한적(2점) > 국소적(1점) |

- 점수 = 심각도×0.4 + 수정 용이성×0.3 + 영향범위×0.3
- 점수 높은 순으로 정렬한다.

### 전체 점수 (Health Score)

발견된 부채 건수와 심각도를 기반으로 100점 만점의 건강 점수를 산출한다:
- CRITICAL 1건당 -15점, HIGH 1건당 -5점, MEDIUM 1건당 -2점, LOW 1건당 -1점
- 최저 0점. 100점에서 감산한다.
- 등급: A(90+), B(75+), C(60+), D(40+), F(40 미만)

## Step 3: 보고서 출력

```
## 기술 부채 보고서: {프로젝트/도메인}

### 요약
- 건강 점수: {등급} ({점수}/100)
- 분석 범위: {전체|도메인명|경로}
- CRITICAL: N건 | HIGH: N건 | MEDIUM: N건 | LOW: N건

### 우선순위 로드맵

| # | 유형 | 위치 | 심각도 | 수정 비용 | 설명 |
|---|------|------|--------|----------|------|
| 1 | 아키텍처 | service/ | CRITICAL | 중 | 순환 의존성 A↔B |
| 2 | 의존성 | build.gradle | HIGH | 소 | Spring Boot 2.x EOL |
| 3 | 코드 | UserService.kt | HIGH | 중 | 350줄, public 메서드 22개 |
| ... | | | | | |

### 유형별 상세

#### 코드 부채 (N건)
{발견 항목 상세}

#### 아키텍처 부채 (N건)
{발견 항목 상세}

#### 의존성 부채 (N건)
{발견 항목 상세}

#### 테스트 부채 (N건)
{발견 항목 상세}

Agent 실패로 분석이 불가한 유형은 다음 형식으로 표시한다:
#### {유형} 부채
> 분석 불가: {실패 사유}
```

상세 섹션에서는 각 항목에 대해:
- **위치**: 파일 경로 (라인 범위)
- **현상**: 구체적으로 무엇이 문제인지
- **권고**: 어떻게 개선할 수 있는지 (코드 수정은 제안하되 직접 수정하지 않음)

AskUserQuestion으로 보고서를 확인한 후, 특정 항목에 대해 더 자세한 분석을 원하는지 확인한다:
- "상세 분석" → 해당 항목의 코드를 Read하여 구체적인 개선 방안 제시
- "완료" → 스킬 종료
