# oh-my-gx 언어 중립화 (v1.21.0) Implementation Plan

> **재조준 (2026-08-04)**: PR #68(verify 지문 경화)이 v1.20.0을 선점하여 릴리스 목표를 v1.21.0으로 변경했다. #68의 변경(gx-verify Step 5-A 지문, 훅 경화, lint [4] 확장)과 본 계획의 편집 앵커는 충돌하지 않음을 검증했다 (lint는 여전히 [19/19]까지 — [20/20] 번호 유효).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 임의의 언어/프레임워크 프로젝트가 최초 1회 등록 후 gx-tdd/gx-dev/gx-verify 전체 파이프라인을 질문·권한 프롬프트 없이 사용할 수 있게 한다.

**Architecture:** config.json `projectTypes`를 유일한 SSOT로 승격하고(신규 선택 필드 `warningPattern`·`artifacts`), gx-setup에 감지→등록 플로우를 신설한다. 스킬 문서의 하드코딩 명령 표는 전부 "예시(파생 사본)"로 격하한다. 스펙: `docs/superpowers/specs/2026-08-04-language-agnostic-skills-design.md`.

**Tech Stack:** 마크다운 스킬 문서 + JSON config + bash lint (`scripts/lint-consistency.sh`). 코드 빌드 없음 — 검증은 lint 스크립트와 grep이다.

## Global Constraints

- 신규 config 필드(`warningPattern`, `artifacts`)는 **전부 선택** — 기존 java-spring/node 사용자는 무변경 동작해야 한다.
- 게이트의 fail-closed 성격 유지 — 미등록 시 조용한 통과 금지.
- 모든 문서는 한국어, 이모지 금지.
- 커밋 메시지: `{type}: 한국어 메시지` 형식, 본문은 `-` bullet. **Co-Authored-By 라인 금지.**
- **`git add -A` 금지** — 워킹 트리에 무관한 untracked 파일(PDF, pptx, stackdump 등)이 있다. 반드시 명시 파일만 스테이징한다.
- 각 태스크 완료 조건: `bash scripts/lint-consistency.sh` 통과 (exit 0, "정합성 린트 통과" 출력).
- 버전 범프(v1.21.0)와 CHANGELOG는 **PR 3에서만** 수행 (릴리스 1회 발동).
- PR 순서: 이 계획의 전제는 `docs/language-agnostic-design` 브랜치(스펙+계획)가 먼저 머지되는 것이다. PR 1~3은 각각 **직전 PR 머지 후 main에서 분기**한다 (스택 PR 금지).
- PR 생성은 `Skill("oh-my-gx:gx-pull-request")`로 수행한다 (오케스트레이터가 실행 — 서브에이전트가 하지 않는다).
- 드리프트 주의: SSOT-파생 사본을 수정하면 gx-tdd SKILL.md의 "드리프트 주의" 목록도 함께 갱신한다.

## 인터페이스 계약 (전 태스크 공유)

- config 신규 필드 키: `warningPattern` (문자열, grep -ci 패턴), `artifacts` (문자열 배열, VCS ignore 패턴)
- 힌트 카탈로그 경로: `.claude/skills/gx-setup/references/project-type-hints.md`
- gx-setup 신설 단계 명칭: `0.5단계: 프로젝트 타입 등록` (lint가 `프로젝트 타입 등록` 문구를 검사)
- lint 신규 체크 번호: `[20/20] 언어 중립화(projectTypes SSOT) 계약 정합` (PR별로 검사 라인이 늘어난다)
- SSOT 명시 문구: 명령 표 주변에 `SSOT는 config` 문구 포함 (lint가 검사)

---

# PR 1 — 코어 메커니즘 (branch: `feat/language-agnostic-core`)

### Task 1: 브랜치 생성 + lint 불변식 [20] 추가 (RED)

**Files:**
- Modify: `scripts/lint-consistency.sh` (315행 부근, `[19/19]` 블록과 최종 요약 사이)

**Interfaces:**
- Produces: lint 체크 `[20/20]` — Task 2~5가 이 체크를 통과시킨다.

- [ ] **Step 1: 브랜치 생성**

```bash
git checkout main && git pull && git checkout -b feat/language-agnostic-core
```

- [ ] **Step 2: 기존 lint 통과 확인 (기준선)**

Run: `bash scripts/lint-consistency.sh`
Expected: exit 0, `정합성 린트 통과`

- [ ] **Step 3: [20] 체크 추가 (PR1 범위만)**

`scripts/lint-consistency.sh`에서 `echo "[19/19] cross-review fallback...` 블록의 끝(`[ "$FAIL" -eq 0 ] && ok "cross-review fallback...` 라인 다음, 최종 `echo` 요약 앞)에 삽입:

```bash
echo "[20/20] 언어 중립화(projectTypes SSOT) 계약 정합"
# --- PR1: config 신규 필드 + gx-verify 일반화 + 카탈로그 + gx-setup 등록 단계 ---
grep -q '"warningPattern"' .claude/config.json || fail "config 템플릿에 warningPattern 필드 누락"
grep -q '"artifacts"' .claude/config.json || fail "config 템플릿에 artifacts 필드 누락"
grep -q 'warningPattern' .claude/skills/gx-verify/SKILL.md || fail "gx-verify 경고 규약이 warningPattern 미참조"
grep -q 'SSOT는 config' .claude/skills/gx-verify/SKILL.md || fail "gx-verify 명령 표 SSOT 문구 누락"
CATALOG=.claude/skills/gx-setup/references/project-type-hints.md
[ -f "$CATALOG" ] || fail "힌트 카탈로그 없음: $CATALOG"
grep -q 'java-spring' "$CATALOG" || fail "카탈로그-템플릿 정합: 기본 타입(java-spring) 행 부재"
grep -q 'SSOT가 아니다' "$CATALOG" || fail "카탈로그 SSOT 아님 명시 문구 부재"
grep -q '프로젝트 타입 등록' .claude/skills/gx-setup/SKILL.md || fail "gx-setup 프로젝트 타입 등록 단계 누락"
grep -q 'java 계열' .claude/skills/gx-setup/SKILL.md || fail "gx-setup JDK 조건화 누락"
[ "$FAIL" -eq 0 ] && ok "projectTypes SSOT(코어)·카탈로그·등록 단계·JDK 조건화 확인"
```

- [ ] **Step 4: 라벨 분모 갱신**

```bash
sed -i 's|/19\]|/20]|g' scripts/lint-consistency.sh
```

파일 상단 주석(검사 항목 목록)에도 한 줄 추가: ` # 20. 언어 중립화 projectTypes SSOT 계약 (v1.21.0)`

- [ ] **Step 5: lint 실행 — 실패 확인 (RED)**

Run: `bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `[20/20]`에서 FAIL 다수 (warningPattern 필드 누락 등), exit=1

- [ ] **Step 6: 커밋**

```bash
git add scripts/lint-consistency.sh
git commit -m "$(cat <<'EOF'
test: 언어 중립화 계약 lint 불변식 추가 (RED)

- [20/20] projectTypes SSOT·카탈로그·등록 단계·JDK 조건화 검사
- 후속 커밋이 이 불변식을 통과시킨다
EOF
)"
```

### Task 2: config.json 템플릿 확장

**Files:**
- Modify: `.claude/config.json` (42~53행 `projectTypes`)

**Interfaces:**
- Produces: `warningPattern`·`artifacts` 필드가 채워진 java-spring/node 항목 — gx-verify(Task 5)·phase-setup(Task 7)이 소비.

- [ ] **Step 1: projectTypes 블록 교체**

기존:

```json
  "projectTypes": {
    "java-spring": {
      "detect": ["build.gradle.kts", "build.gradle"],
      "build": "./gradlew build",
      "test": "./gradlew test"
    },
    "node": {
      "detect": ["package.json"],
      "build": "npm run build",
      "test": "npm test"
    }
  },
```

교체:

```json
  "projectTypes": {
    "java-spring": {
      "detect": ["build.gradle.kts", "build.gradle"],
      "build": "./gradlew build",
      "test": "./gradlew test",
      "warningPattern": "warning",
      "artifacts": [".gradle/", "build/"]
    },
    "node": {
      "detect": ["package.json"],
      "build": "npm run build",
      "test": "npm test",
      "warningPattern": "warn",
      "artifacts": ["node_modules/", "dist/"]
    }
  },
```

- [ ] **Step 2: JSON 유효성 확인**

Run: `python -c "import json;json.load(open('.claude/config.json',encoding='utf-8'));print('OK')"` (python 부재 시 `node -e "JSON.parse(require('fs').readFileSync('.claude/config.json'));console.log('OK')"`)
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add .claude/config.json
git commit -m "$(cat <<'EOF'
feat: projectTypes에 warningPattern·artifacts 선택 필드 추가

- java-spring/node 기본 템플릿에 신규 필드 채움
- 기존 소비자는 필드 부재 시 현행 동작 유지 (하위 호환)
EOF
)"
```

### Task 3: 힌트 카탈로그 신설

**Files:**
- Create: `.claude/skills/gx-setup/references/project-type-hints.md`

**Interfaces:**
- Produces: 감지 파일→제안 값 표 — gx-setup 등록 단계(Task 4)·phase-setup 인라인 등록(Task 7)이 Read.

- [ ] **Step 1: 카탈로그 파일 작성**

전체 내용:

````markdown
# 프로젝트 타입 힌트 카탈로그

gx-setup "프로젝트 타입 등록" 단계와 gx-dev/gx-tdd phase-setup의 인라인 등록이 참조하는 **제안용** 표다.

**이 카탈로그는 SSOT가 아니다.** SSOT는 소비 프로젝트 `.claude/config.json`의 `projectTypes`에 등록된 값이며, 등록 값이 항상 이 표보다 우선한다. 이 표는 감지 시 제안 품질을 높이는 힌트일 뿐이다.

## 사용 규칙

1. 감지 파일이 여러 행과 매칭되면 (예: Makefile + CMakeLists.txt 공존) 사용자에게 선택지를 제시한다.
2. 표에 없는 스택은 프로젝트 구조(빌드 스크립트, README, CI 설정)를 근거로 명령을 추론해 제안하되, 추론 근거를 함께 표시한다. 근거 없는 명령을 지어내지 않는다.
3. 제안 값은 반드시 사용자 확인을 거쳐 config에 기록한다.
4. `warningPattern`은 `grep -ci "<패턴>"` 인자로 쓰인다. `artifacts`는 VCS ignore 보강 패턴이다.
5. 권한 prefix는 build/test 명령의 첫 토큰에서 도출한다 — 등록 시 `.claude/settings.local.json` 허용 추가 제안에 사용한다.

## 힌트 표

| 감지 파일 | 타입 키 | build 제안 | test 제안 | warningPattern | artifacts | 권한 prefix |
|-----------|--------|-----------|----------|----------------|-----------|------------|
| `Makefile` | `c-make` | `make` | `make test` | `warning:` | `build/`, `*.o` | `Bash(make *)` |
| `CMakeLists.txt` | `c-cmake` | `cmake --build build` | `ctest --test-dir build --output-on-failure` | `warning:` | `build/` | `Bash(cmake *)`, `Bash(ctest *)` |
| `project.yml` (Ceedling) | `c-ceedling` | (없음 — test가 빌드 포함) | `ceedling test:all` | `warning:` | `build/` | `Bash(ceedling *)` |
| `pyproject.toml` / `setup.py` / `requirements.txt` | `python` | (없음) | `pytest` | `warning` | `.venv/`, `__pycache__/` | `Bash(pytest *)` |
| `go.mod` | `go` | `go build ./...` | `go test ./...` | `warning` | (없음) | `Bash(go *)` |
| `Cargo.toml` | `rust` | `cargo build` | `cargo test` | `warning:` | `target/` | `Bash(cargo *)` |
| `*.csproj` / `*.sln` | `dotnet` | `dotnet build` | `dotnet test` | `warning` | `bin/`, `obj/` | `Bash(dotnet *)` |
| `pom.xml` | `java-maven` | `mvn -B compile` | `mvn -B test` | `WARNING` | `target/` | `Bash(mvn *)` |
| `composer.json` | `php` | (없음) | `./vendor/bin/phpunit` | `warning` | `vendor/` | `Bash(./vendor/bin/phpunit *)` |
| `build.gradle(.kts)` | `java-spring` | (기본 템플릿 참조) | (기본 템플릿 참조) | `warning` | `.gradle/`, `build/` | `Bash(./gradlew *)` |
| `package.json` | `node` | (기본 템플릿 참조) | (기본 템플릿 참조) | `warn` | `node_modules/`, `dist/` | `Bash(npm *)` |

## 주의

- Node 변형은 lock 파일로 구분해 명령을 제안한다: `pnpm-lock.yaml` → `pnpm test`, `yarn.lock` → `yarn test`, `bun.lockb` → `bun test` (타입 키는 동일하게 `node`, 명령만 변형).
- C 계열은 test 명령이 프로젝트마다 크게 다르다 (make의 test 타깃 유무, CTest 구성 여부). 제안 후 반드시 실제 실행 가능한지 사용자에게 확인받는다.
- 임베디드 C에서 test는 **호스트에서 실행 가능**해야 gx-tdd RGR·verify가 성립한다. 타깃 전용 빌드만 있으면 하네스 구축 가이드(oh-my-gx 저장소 `docs/test-harness-guide.md`)를 안내한다.
````

- [ ] **Step 2: 커밋**

```bash
git add .claude/skills/gx-setup/references/project-type-hints.md
git commit -m "$(cat <<'EOF'
feat: 프로젝트 타입 힌트 카탈로그 신설

- 주요 스택(C/CMake/Ceedling·Python·Go·Rust·.NET·Maven·PHP) 감지 파일-제안 명령 표
- 제안용 문서 — SSOT는 config projectTypes 등록 값
EOF
)"
```

### Task 4: gx-setup 등록 단계 신설 + JDK 조건화

**Files:**
- Modify: `.claude/skills/gx-setup/SKILL.md` (0단계 끝 66행 부근에 0.5단계 삽입, JDK 절 147~155행 수정, allowed-tools 6~24행에 Glob 확인)

**Interfaces:**
- Consumes: Task 3의 카탈로그 (`${CLAUDE_PLUGIN_ROOT:-.}/.claude/skills/gx-setup/references/project-type-hints.md`)
- Produces: "프로젝트 타입 등록" 절차 (스캔→제안→확인→config 기록→권한 등록) — Task 7의 phase-setup 인라인 등록이 이 절차를 포인터 참조.

- [ ] **Step 1: 0.5단계 삽입**

`이후 단계는 \`VCS_TYPE\`에 따라 분기한다.` 라인(67행) 바로 다음에 삽입:

````markdown
### 0.5단계: 프로젝트 타입 등록

`.claude/config.json`의 `projectTypes`를 프로젝트에 맞게 등록한다. **SSOT는 config에 등록된 값**이며, 힌트 카탈로그는 제안용이다.

1. **기존 등록 확인**: config `projectTypes` 중 `detect` 파일이 프로젝트 루트에 존재하는 타입이 있으면 → `프로젝트 타입 : 완료 ✅ ({타입}, 기존 설정 유지)` 출력 후 1단계로 진행한다 (갱신하지 않음).
2. **빌드 파일 스캔**: Glob으로 `Makefile`, `CMakeLists.txt`, `project.yml`, `Cargo.toml`, `pom.xml`, `pyproject.toml`, `setup.py`, `requirements.txt`, `go.mod`, `*.csproj`, `*.sln`, `composer.json`, `build.gradle`, `build.gradle.kts`, `package.json`을 탐색한다.
3. **제안 생성**: `Read("${CLAUDE_PLUGIN_ROOT:-.}/.claude/skills/gx-setup/references/project-type-hints.md")`로 힌트 카탈로그를 읽어 감지 파일과 매칭한다.
   - 매칭되면 해당 행의 타입 키·build/test·warningPattern·artifacts를 제안 값으로 사용한다. 여러 행이 매칭되면 사용자에게 선택지를 제시한다.
   - 매칭되지 않으면 프로젝트 구조(빌드 스크립트, README, CI 설정)를 근거로 추론해 제안하되 근거를 함께 표시한다. 근거 없는 명령을 지어내지 않는다.
   - 아무 빌드 파일도 감지되지 않으면 → `프로젝트 타입 : 건너뜀 (감지 실패)` 출력 후 1단계로 진행한다 (파이프라인 게이트가 fail-closed로 처리).
4. **사용자 확인**:
   ```
   AskUserQuestion(
     questions: [{
       header: "타입 등록",
       question: "감지된 프로젝트 타입: {타입키}. 명령을 확인해주세요. build: `{build}`, test: `{test}`",
       multiSelect: false,
       options: [
         { label: "등록 (Recommended)", description: "이 값으로 config.json projectTypes에 기록합니다" },
         { label: "명령 수정", description: "Other로 이동해서 build/test 명령을 직접 입력해주세요" },
         { label: "건너뛰기", description: "등록하지 않습니다. 파이프라인 게이트에서 매번 직접 입력해야 합니다" }
       ]
     }]
   )
   ```
   - "등록" → 5로 진행. "명령 수정" → 입력값 반영 후 5로 진행. "건너뛰기" → `프로젝트 타입 : 건너뜀 (사용자 선택)` 출력 후 1단계로 진행.
5. **config 기록**: 확정 값을 `projectTypes.{타입키}`에 Edit로 기록한다 (`detect`/`build`/`test`/`warningPattern`/`artifacts`. 빈 제안 값은 필드를 생략한다).
6. **권한 등록**: build/test 명령의 첫 토큰에서 prefix 권한을 도출하고 (예: `make test` → `Bash(make *)`) 확인받는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "권한 등록",
       question: "등록한 명령을 권한 프롬프트 없이 실행하도록 `.claude/settings.local.json`에 허용을 추가할까요? ({권한 prefix 목록})",
       multiSelect: false,
       options: [
         { label: "추가 (Recommended)", description: "permissions.allow에 병합합니다 (기존 항목 보존)" },
         { label: "건너뛰기", description: "추가하지 않습니다. 파이프라인 실행 중 권한 프롬프트가 발생할 수 있습니다" }
       ]
     }]
   )
   ```
   - "추가" → `.claude/settings.local.json`의 `permissions.allow` 배열에 병합한다. 파일 부재 시 `{"permissions":{"allow":[...]}}`로 생성하고, 기존 항목은 보존하며, 중복은 추가하지 않는다. JSON 파싱 실패 시 갱신하지 않고 수동 설정을 안내한다.
7. `프로젝트 타입 등록 : 완료 ✅ ({타입키})` 출력.
````

- [ ] **Step 2: JDK 절 조건화**

`#### JDK` 절(147행 부근)의 서두를 교체. 기존:

```markdown
#### JDK

1. `uname -s`로 OS를 감지한다.
```

교체:

```markdown
#### JDK (java 계열 타입만)

0.5단계에서 등록/확인된 `projectTypes`에 **java 계열** 타입(gradle/maven 기반 — `java-spring`, `java-maven` 등 build/test 명령에 `gradlew` 또는 `mvn`이 포함된 타입)이 있을 때만 실행한다. 없으면 `JDK : 건너뜀 (java 계열 타입 없음)` 출력 후 2단계로 진행한다.

1. `uname -s`로 OS를 감지한다.
```

- [ ] **Step 3: lint 확인 (부분 GREEN)**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A8 '\[20/20\]'`
Expected: `프로젝트 타입 등록`·`java 계열`·카탈로그 FAIL 해소. gx-verify 관련 FAIL만 잔존.

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/gx-setup/SKILL.md
git commit -m "$(cat <<'EOF'
feat: gx-setup에 프로젝트 타입 등록 단계 신설

- 0.5단계: 스캔→카탈로그 제안→확인→config 기록→권한 등록
- settings.local.json permissions.allow 병합 (기존 보존·중복 금지)
- JDK 확인을 java 계열 타입 감지 시에만 조건부 실행
EOF
)"
```

### Task 5: gx-verify 일반화

**Files:**
- Modify: `.claude/skills/gx-verify/SKILL.md` (Step 1 85~93행, Step 2 규약 111~115행)

**Interfaces:**
- Consumes: Task 2의 `warningPattern` 필드.

- [ ] **Step 1: Step 1 SSOT 문구 + 등록 안내**

85행 기존:

```markdown
`.claude/config.json`의 `projectTypes` 설정에서 감지. 기본 config는 `java-spring`·`node`만 정의하므로, `python`·`go` 행은 소비 프로젝트가 `projectTypes`에 해당 타입을 추가했을 때만 도달한다.
```

교체:

```markdown
**SSOT는 config `projectTypes`다** — 위 표는 예시(파생 사본)이며, config에 등록된 타입·명령이 항상 우선한다. 기본 템플릿은 `java-spring`·`node`만 정의하므로 그 외 행은 소비 프로젝트가 등록했을 때만 도달한다. 어떤 언어든 `/gx-setup`의 "프로젝트 타입 등록" 단계로 등록하면 이후 자동 감지된다.
```

감지 실패 시 블록(87~93행)의 대화형 안내 문구를 교체. 기존: `- (대화형) AskUserQuestion으로 처리한다: "검증 명령을 감지하지 못했습니다. 게이트를 진행하려면 명령이 필요합니다."` → 교체: `- (대화형) AskUserQuestion으로 처리한다: "검증 명령을 감지하지 못했습니다. 게이트를 진행하려면 명령이 필요합니다. (영구 등록은 /gx-setup의 프로젝트 타입 등록을 사용하세요)"`

- [ ] **Step 2: 경고 측정 규약 일반화**

113행 기존:

```markdown
2. 카운트: java-spring은 `grep -ci "warning" <로그>`, node는 `grep -ci "warn" <로그>`, 그 외 타입은 미지원 (카운트 생략·보고만).
```

교체:

```markdown
2. 카운트: config `projectTypes`의 **`warningPattern` 필드**를 사용해 `grep -ci "<warningPattern>" <로그>`로 센다. 필드가 없으면 폴백 — java-spring은 `grep -ci "warning"`, node는 `grep -ci "warn"`, 그 외 타입은 미지원 (카운트 생략·보고만).
```

- [ ] **Step 3: lint 전체 통과 확인 (GREEN)**

Run: `bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `[20/20] ... ok`, `정합성 린트 통과`, exit=0

- [ ] **Step 4: 커밋 + PR 생성**

```bash
git add .claude/skills/gx-verify/SKILL.md
git commit -m "$(cat <<'EOF'
feat: gx-verify 검증 명령·경고 규약을 projectTypes SSOT로 일반화

- Step 1 명령 표를 예시로 격하하고 gx-setup 등록 안내 추가
- 경고 카운트를 warningPattern 필드 기반으로 일반화 (java/node 폴백 유지)
EOF
)"
```

이후 오케스트레이터가 `Skill("oh-my-gx:gx-pull-request")`로 PR 1을 생성한다. **PR 1 머지 후 PR 2를 시작한다.**

---

# PR 2 — 파이프라인 소비 지점 (branch: `feat/language-agnostic-pipeline`)

### Task 6: lint [20] 확장 (PR2 범위, RED)

**Files:**
- Modify: `scripts/lint-consistency.sh` ([20/20] 블록)

- [ ] **Step 1: 브랜치 생성**

```bash
git checkout main && git pull && git checkout -b feat/language-agnostic-pipeline
```

- [ ] **Step 2: [20] 블록에 PR2 검사 추가**

`[ "$FAIL" -eq 0 ] && ok "projectTypes SSOT(코어)...` 라인 **앞**에 삽입:

```bash
# --- PR2: 파이프라인 소비 지점 (phase-setup·phase-review·하네스 감지·allowed-tools) ---
for f in .claude/skills/gx-dev/phases/phase-setup.md .claude/skills/gx-tdd/phases/phase-setup.md; do
  grep -q '프로젝트 타입 등록' "$f" || fail "phase-setup 인라인 등록 연동 누락: $f"
  grep -q 'artifacts' "$f" || fail "phase-setup ignore 보강이 artifacts 미참조: $f"
done
for f in .claude/skills/gx-dev/phases/phase-review.md .claude/skills/gx-tdd/phases/phase-review.md; do
  grep -q 'SSOT는 config' "$f" || fail "phase-review 빌드 표 SSOT 문구 누락: $f"
done
grep -q '테스트 하네스 부재' .claude/skills/gx-tdd/phases/phase-implement.md \
  || fail "phase-implement 하네스 부재 감지 누락"
for f in .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md .claude/skills/gx-ralph-iterate/SKILL.md; do
  grep -qF 'Bash(make *)' "$f" || fail "allowed-tools 대표 도구(make) 누락: $f"
  grep -qF 'Bash(ceedling *)' "$f" || fail "allowed-tools 대표 도구(ceedling) 누락: $f"
done
```

- [ ] **Step 3: lint 실행 — 실패 확인 (RED)**

Run: `bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: PR2 검사들 FAIL, exit=1

- [ ] **Step 4: 커밋**

```bash
git add scripts/lint-consistency.sh
git commit -m "$(cat <<'EOF'
test: 언어 중립화 lint에 파이프라인 소비 지점 검사 추가 (RED)

- phase-setup 등록 연동·artifacts, phase-review SSOT 문구
- 하네스 부재 감지, allowed-tools 대표 도구
EOF
)"
```

### Task 7: phase-setup 등록 연동 + artifacts 참조 (gx-tdd·gx-dev 동일 적용)

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-setup.md` (Step 3.1 항목 1 = 155행 부근, Step 6 표 = 210~218행)
- Modify: `.claude/skills/gx-dev/phases/phase-setup.md` (같은 구조의 대응 지점 — Step 번호가 다를 수 있으니 "프로젝트 타입 감지" 항목과 "VCS ignore 자동 보강" 절을 grep으로 찾아 동일하게 수정)

**Interfaces:**
- Consumes: Task 4의 "프로젝트 타입 등록" 절차, Task 2의 `artifacts` 필드.

- [ ] **Step 1: gx-tdd Step 3.1 항목 1 교체**

기존:

```markdown
1. **프로젝트 타입 감지**: `.claude/config.json`의 `projectTypes`에서 detect 필드와 매칭한다 (예: `build.gradle.kts` → `java-spring`, `package.json` → `node`). 여러 타입이 감지되면 모두 기록한다.
```

교체:

```markdown
1. **프로젝트 타입 감지**: `.claude/config.json`의 `projectTypes`에서 detect 필드와 매칭한다 (예: `build.gradle.kts` → `java-spring`, `package.json` → `node`, `Makefile` → `c-make`). 여러 타입이 감지되면 모두 기록한다. **매칭 실패 시**: gx-setup의 "프로젝트 타입 등록" 절차(빌드 파일 스캔 → 힌트 카탈로그 `Read("${CLAUDE_PLUGIN_ROOT:-.}/.claude/skills/gx-setup/references/project-type-hints.md")` 제안 → 사용자 확인 → config 기록 → 권한 등록)를 인라인으로 1회 실행한다. 사용자가 등록을 건너뛰면 타입 미상으로 진행한다 (이후 게이트는 fail-closed 동작 — 조용한 통과 없음).
```

- [ ] **Step 2: gx-tdd Step 6 git 절 교체**

기존:

```markdown
프로젝트 타입에 따라 `.gitignore`에 빌드 아티팩트 패턴을 추가한다. 이미 존재하는 패턴은 건너뛴다.

| 프로젝트 타입 | 추가 패턴 |
|---------------|-----------|
| java-spring | `.gradle/`, `build/` |
| node | `node_modules/`, `dist/` |
```

교체:

```markdown
프로젝트 타입에 따라 `.gitignore`에 빌드 아티팩트 패턴을 추가한다. **패턴은 config `projectTypes.{타입}.artifacts` 필드에서 읽는다** (SSOT는 config — 예: java-spring `.gradle/`·`build/`, node `node_modules/`·`dist/`). `artifacts` 필드가 없는 타입은 이 보강을 건너뛴다. 이미 존재하는 패턴은 건너뛴다.
```

- [ ] **Step 3: gx-dev phase-setup에 동일 수정 적용**

`.claude/skills/gx-dev/phases/phase-setup.md`에서 `프로젝트 타입 감지` 항목과 `VCS ignore 자동 보강` 절(java-spring/node 하드코딩 표)을 찾아 Step 1·2와 **동일한 문구**로 교체한다 (gx-dev의 Step 번호 체계를 유지하고 내용만 교체).

- [ ] **Step 4: lint 부분 확인**

Run: `bash scripts/lint-consistency.sh 2>&1 | grep -A12 '\[20/20\]'`
Expected: phase-setup 관련 FAIL 해소.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-setup.md .claude/skills/gx-dev/phases/phase-setup.md
git commit -m "$(cat <<'EOF'
feat: phase-setup 타입 미감지 시 인라인 등록 + artifacts 기반 ignore 보강

- 매칭 실패 시 gx-setup 등록 절차를 1회 인라인 실행 (질문 1회 → 영구 자동)
- .gitignore 보강 표를 projectTypes.artifacts 필드 참조로 교체
EOF
)"
```

### Task 8: phase-review 빌드 명령 표 → config 참조 (gx-tdd·gx-dev)

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-review.md` (Step 0-1, 28~37행)
- Modify: `.claude/skills/gx-dev/phases/phase-review.md` (같은 구조 — 22~23행 부근 표)

- [ ] **Step 1: gx-tdd Step 0-1 항목 2 교체**

기존:

```markdown
2. CLAUDE.md에 빌드 명령이 없으면 → 프로젝트 타입에서 기본값을 사용한다:
   | 프로젝트 타입 | 기본 빌드 명령 |
   |---------------|---------------|
   | java-spring (gradle) | `./gradlew build -x test` |
   | node | `bun run build` 또는 `npm run build` (package.json의 scripts.build가 있을 때만. `which bun` → bun, 없으면 npm) |
   | python | 건너뛰기 (인터프리터 언어 — 기본 config 미정의 타입, `projectTypes` 확장 시에만 도달) |
```

교체:

```markdown
2. CLAUDE.md에 빌드 명령이 없으면 → config `projectTypes`의 `build` 필드를 사용한다. **SSOT는 config다** — 아래는 기본 템플릿 기준 예시(파생 사본):
   | 프로젝트 타입 | 빌드 명령 (예시) |
   |---------------|---------------|
   | java-spring (gradle) | `./gradlew build -x test` (`build` 필드의 테스트 제외 변형) |
   | node | `bun run build` 또는 `npm run build` (package.json의 scripts.build가 있을 때만. `which bun` → bun, 없으면 npm) |

   `build` 필드가 없거나 빈 값인 타입(인터프리터 언어 등)은 빌드 검증을 건너뛰고, 건너뛰었음을 보고에 명시한다.
```

- [ ] **Step 2: gx-dev phase-review에 동일 수정 적용**

같은 표(22~23행 부근)를 위와 동일한 문구로 교체한다.

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-review.md .claude/skills/gx-dev/phases/phase-review.md
git commit -m "$(cat <<'EOF'
feat: phase-review 빌드 명령 표를 config SSOT 참조로 교체

- 하드코딩 표를 예시로 격하, build 필드 부재 시 건너뜀 명시 보고
EOF
)"
```

### Task 9: phase-implement 하네스 부재 감지

**Files:**
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md` (Step 0.5, 41~49행)

- [ ] **Step 1: Step 0.5에 4항 추가**

기존 3항(`테스트 명령 미감지·추출 불가 시...`) 다음에 추가:

```markdown
4. **테스트 하네스 부재 감지**: test 명령이 미등록이거나 실행 결과 테스트 수가 0건이면, 테스트 파일 글롭(`**/*test*`, `**/*Test*`, `**/*spec*` — 파일·디렉토리)을 확인한다. 글롭도 0건이면 하네스 부재로 판정하고 안내 후 중단한다:
   "테스트 하네스가 감지되지 않습니다. gx-tdd는 실행 가능한 테스트 없이 진행할 수 없습니다 (Iron Law 1). 테스트 프레임워크를 먼저 구축한 뒤 다시 실행해주세요 (oh-my-gx 저장소 `docs/test-harness-guide.md` 참고 — C: Unity/Ceedling/CppUTest). 하네스 구축 자체를 원하시면 별도 작업으로 요청해주세요."
   state.md를 `status: cancelled`로 갱신하고 파이프라인을 종료한다. 테스트 파일이 존재하는데 실행이 0건이면 하네스 부재가 아니라 명령/경로 문제다 — 1항(기준 GREEN 확인)의 절차를 따른다.
```

참고: 안내 문구가 참조하는 `docs/test-harness-guide.md`는 PR 3(Task 15)에서 추가된다 — PR 2 머지 시점에는 일시적 선행 참조이며 PR 3 머지로 해소된다 (스펙의 PR 분할 결정에 따름).

- [ ] **Step 2: 커밋**

```bash
git add .claude/skills/gx-tdd/phases/phase-implement.md
git commit -m "$(cat <<'EOF'
feat: 기준선 게이트에 테스트 하네스 부재 감지 추가

- test 명령 미등록·실행 0건 + 테스트 파일 글롭 0건 → 안내 후 중단
- 하네스 구축은 별도 작업으로 분리 (스펙 결정 사항)
EOF
)"
```

### Task 10: allowed-tools 대표 도구 추가 + 드리프트 목록 갱신

**Files:**
- Modify: `.claude/skills/gx-tdd/SKILL.md` (6행 allowed-tools 배열, 55행 부근 드리프트 목록)
- Modify: `.claude/skills/gx-dev/SKILL.md` (allowed-tools yaml 리스트, 19행 `- Bash(go *)` 다음)
- Modify: `.claude/skills/gx-ralph-iterate/SKILL.md` (allowed-tools, 22행 `- Bash(go *)` 다음)

- [ ] **Step 1: gx-tdd allowed-tools 추가**

6행 배열에서 `"Bash(go *)"` 다음에 추가: `"Bash(make *)", "Bash(cmake *)", "Bash(ctest *)", "Bash(ceedling *)", "Bash(cargo *)", "Bash(mvn *)", "Bash(dotnet *)",`

- [ ] **Step 2: gx-dev·gx-ralph-iterate allowed-tools 추가**

각 파일 `- Bash(go *)` 라인 다음에 추가:

```yaml
  - Bash(make *)
  - Bash(cmake *)
  - Bash(ctest *)
  - Bash(ceedling *)
  - Bash(cargo *)
  - Bash(mvn *)
  - Bash(dotnet *)
```

- [ ] **Step 3: gx-tdd 드리프트 목록 갱신**

`- **프로젝트 타입 폴백 표**: SSOT는 ...` bullet을 교체:

```markdown
> - **프로젝트 타입 폴백 표**: SSOT는 `.claude/config.json`의 projectTypes. gx-verify Step 1·gx-tdd/gx-dev phase-review의 표는 파생 사본(예시)이다. 힌트 카탈로그(`gx-setup/references/project-type-hints.md`)는 제안용으로 config에 종속되며, 경고 카운트(`warningPattern` — gx-verify Step 2 폴백 포함)와 ignore 보강(`artifacts` — phase-setup Step 6)도 이 SSOT를 따른다.
```

- [ ] **Step 4: lint 전체 통과 확인 (GREEN)**

Run: `bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `정합성 린트 통과`, exit=0

- [ ] **Step 5: 커밋 + PR 생성**

```bash
git add .claude/skills/gx-tdd/SKILL.md .claude/skills/gx-dev/SKILL.md .claude/skills/gx-ralph-iterate/SKILL.md
git commit -m "$(cat <<'EOF'
feat: allowed-tools에 대표 빌드 도구 추가 및 드리프트 목록 갱신

- make/cmake/ctest/ceedling/cargo/mvn/dotnet prefix 허용 (3개 스킬)
- 프로젝트 타입 폴백 표 드리프트 항목에 카탈로그·신규 필드 종속 명시
EOF
)"
```

이후 오케스트레이터가 `Skill("oh-my-gx:gx-pull-request")`로 PR 2를 생성한다. **PR 2 머지 후 PR 3을 시작한다.**

---

# PR 3 — 에이전트·주변 스킬·문서·릴리스 (branch: `feat/language-agnostic-agents`)

### Task 11: architect·coder 타입 표 일반화 + 비-OO 컨벤션

**Files:**
- Modify: `agents/architect.md` (49~69행)
- Modify: `agents/coder.md` (53~67행)

- [ ] **Step 1: 브랜치 생성**

```bash
git checkout main && git pull && git checkout -b feat/language-agnostic-agents
```

- [ ] **Step 2: architect.md 타입 감지 절 교체**

`## 프로젝트 타입 감지` 절(49~57행)을 교체:

```markdown
## 프로젝트 타입 감지

`.claude/config.json`의 `projectTypes`에서 감지한다 (**SSOT는 config** — detect 파일 매칭, build/test 명령 포함). 아래는 기본 템플릿 기준 예시다:

| 파일 | 타입 | 빌드 |
|------|------|------|
| `build.gradle.kts` / `build.gradle` | Kotlin/Java (Gradle) | `./gradlew build` |
| `package.json` | Node.js (TypeScript/JavaScript) | `npm run build` |
| `Makefile` / `CMakeLists.txt` | C/C++ (Make/CMake) | `make` / `cmake --build build` |
```

- [ ] **Step 3: architect.md 컨벤션 학습에 비-OO 절 추가**

`**Kotlin/Java 프로젝트**` 블록(66~69행) 다음에 추가:

```markdown
**C/C++ 등 비객체지향 프로젝트** (`Makefile`, `CMakeLists.txt` 감지 시):
- 기존 코드에서 다음을 학습: 모듈/헤더 경계(공개 헤더 vs 내부 구현), 네이밍(파일/함수/매크로), 에러 처리 관습(반환 코드/errno), 전처리기 사용 패턴, 메모리 소유권 규약.
- 테스트 격리는 공개 인터페이스 헤더 기준으로 설계한다 (함수 포인터 테이블, 링크 타임 치환 — testability 평가는 test-architect 소관).
```

- [ ] **Step 4: coder.md 동일 교체**

`## 프로젝트 타입 감지` 절(53~61행)을 Step 2와 동일한 내용으로 교체하고, `## Bash 사용 제한`의 `허용 명령: 프로젝트 타입 감지 테이블의 빌드 명령, 린터 실행`을 `허용 명령: config projectTypes의 빌드 명령, 린터 실행`으로 교체한다.

- [ ] **Step 5: 커밋**

```bash
git add agents/architect.md agents/coder.md
git commit -m "$(cat <<'EOF'
feat: architect·coder 타입 감지를 config SSOT 참조로 일반화

- 하드코딩 표를 예시로 격하, C/C++ 행 추가
- 비-OO 프로젝트 컨벤션 학습 지침 추가
EOF
)"
```

### Task 12: test-architect·testing-anti-patterns C 관점 병기

**Files:**
- Modify: `agents/test-architect.md` (`## 평가 영역` 뒤, 58행 부근)
- Modify: `.claude/skills/gx-tdd/references/testing-anti-patterns.md` (모의 3원칙 아래, Anti-Pattern 1·2에 C 예시)

- [ ] **Step 1: test-architect에 비-OO 대응 절 추가**

`### testability score (1-10)` 절 앞에 추가:

```markdown
### 비-OO 언어(C 등) 평가 어휘

DI/모의 개념을 다음으로 번역하여 평가한다:
- 의존성 주입 → 함수 포인터 테이블 주입, 링크 타임 치환(테스트용 스텁 오브젝트 링크)
- Mock 프레임워크 → CMock/FFF/직접 작성 스텁
- 외부 의존성 격리 → HAL(하드웨어 추상 계층) 인터페이스 분리, 호스트 빌드 가능 여부(듀얼 타깃)
- 하드웨어 직접 접근(레지스터, ISR)이 추상화 없이 산재하면 감점 요인이다 — HAL 추출을 재설계로 권고한다.
```

- [ ] **Step 2: testing-anti-patterns 모의 3원칙에 C 각주 추가**

`## 모의 3원칙` 코드 블록 다음에 추가:

```markdown
> C 프로젝트에서 "모의"는 CMock/FFF 스텁·링커 치환 스텁을 포함한다. 원칙은 동일하다 — 스텁의 반환값을 검증하는 테스트, 프로덕션 모듈의 테스트 전용 reset 함수, 이해 없는 전면 스텁화 모두 위반이다.
```

- [ ] **Step 3: Anti-Pattern 1에 C 병기 예시 추가**

Anti-Pattern 1의 `**게이트 함수:**` 앞에 추가:

````markdown
**C 병기 예시 (Unity/CMock):**
```c
// ❌ 스텁이 존재하는지를 검증
void test_알림을_전송한다(void) {
    sender_send_ExpectAndReturn(&notice, true);
    TEST_ASSERT_TRUE(sender_send(&notice));  // 스텁만 검증됨
}

// ✅ 실제 대상의 동작을 검증 (스텁은 격리에만 사용)
void test_전송_실패_시_재시도_큐에_적재된다(void) {
    sender_send_ExpectAndReturn(&notice, false);
    notice_service_notify(&notice);
    TEST_ASSERT_EQUAL(1, retry_queue_size());  // 검증 대상은 service의 동작
}
```
````

- [ ] **Step 4: Anti-Pattern 2에 C 병기 예시 추가**

Anti-Pattern 2의 `**수정:**` 블록 다음에 추가:

```markdown
**C 병기**: 프로덕션 모듈(`session.c`)에 테스트에서만 호출하는 `session_destroy_all()`을 추가하지 않는다. 테스트 정리는 테스트 지원 파일(`test_support/session_cleanup.c`)이 공개 API 조합으로 수행한다.
```

- [ ] **Step 5: 커밋**

```bash
git add agents/test-architect.md .claude/skills/gx-tdd/references/testing-anti-patterns.md
git commit -m "$(cat <<'EOF'
feat: testability 평가·테스트 안티패턴에 C 관점 병기

- test-architect에 비-OO 평가 어휘 (함수 포인터·링크 치환·HAL·듀얼 타깃)
- 모의 3원칙·Anti-Pattern 1/2에 C(Unity/CMock) 예시 추가
EOF
)"
```

### Task 13: gx-context 자동 스캔 언어 중립화

**Files:**
- Modify: `.claude/skills/gx-context/SKILL.md` (A-1 절 87~97행, A-2 절 99~104행)

- [ ] **Step 1: A-1 스캔 항목 교체**

기존 1~5항을 교체:

```markdown
1. **디렉토리 구조**: 소스 루트 하위 최상위 2레벨을 스캔하여 도메인 후보를 추론한다. 언어 무관 휴리스틱:
   - 파일 확장자 클러스터로 소스 루트를 판별한다 (`.java`/`.kt`/`.ts`/`.py`/`.c`/`.h`/`.go`/`.rs` 등)
   - 업무 명사 디렉토리명 군집을 도메인 후보로 본다 (payment/, order/, sensor/, protocol/ 등)
   - 언어별 예시: Java `src/main/java/{base-package}/` 하위 패키지, Node `src/` 하위 modules/·features/·domains/, C `src/`·`include/` 하위 모듈 디렉토리
2. **도메인 모델**: 네이밍 패턴 군집으로 탐색한다 — 접미사형(`*Entity.java`, `*.entity.ts`, `*Model.*`) 또는 C 계열 모듈 쌍(`{이름}.h`/`{이름}.c`)의 구조체(typedef struct) 정의.
3. **진입점/인터페이스**: API 라우팅(`*Controller.java`, `*Router.*`, `routes/`) 또는 C 계열 공개 헤더(include/ 디렉토리, extern 함수 선언이 밀집한 헤더).
4. **설정 파일**: `application.yml`, `application.properties`, `.env`, `package.json`, `Makefile`/`CMakeLists.txt`, `Kconfig` 등을 읽는다.
5. **README/문서**: 프로젝트 루트의 `README.md`, `docs/` 디렉토리를 확인한다.
```

- [ ] **Step 2: A-2 도메인 분류에 C 예시 추가**

기존 3개 bullet 다음에 추가:

```markdown
- 모듈 접두사 기반 (C 계열): `uart_*.h`/`sensor_*.c` 군집 → 통신/센서 도메인
```

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/gx-context/SKILL.md
git commit -m "$(cat <<'EOF'
feat: gx-context 자동 스캔을 언어 중립 휴리스틱으로 일반화

- 확장자 클러스터·네이밍 군집 기반으로 재작성, 언어별 패턴은 예시로 격하
- C 계열 모듈 쌍·공개 헤더·접두사 군집 휴리스틱 추가
EOF
)"
```

### Task 14: gx-tech-debt 의존성 분석 일반화

**Files:**
- Modify: `.claude/skills/gx-tech-debt/SKILL.md` (frontmatter 20~25행, 1-3 절 171~192행)

- [ ] **Step 1: 1-3 절 서두 교체**

기존 `프로젝트 타입별로 의존성 상태를 확인한다:` 를 교체:

```markdown
config `projectTypes`에서 감지된 타입 기준으로 의존성 상태를 확인한다 (**SSOT는 config**). 아래에 분석 절차가 정의된 생태계만 실행한다.
```

- [ ] **Step 2: rust 절 추가**

`**python:**` 절 다음에 추가:

```markdown
**rust:**
1. `Cargo.toml`을 Read하여 의존성 목록을 파악한다.
2. `cargo tree --depth 1` (`timeout: 60000`)로 직접 의존성을 확인한다.
3. `cargo audit --json` (`timeout: 60000`)이 실행 가능하면 알려진 취약점을 확인한다. 미설치면 건너뛰고 보고에 명시한다.
```

- [ ] **Step 3: 범용 절 교체**

기존:

```markdown
**범용 (감지 불가):**
- 이 유형을 건너뛴다.
```

교체:

```markdown
**그 외 (분석 절차 미정의 타입·감지 불가):**
- 건너뛰지 않고 보고서에 명시 기재한다: "의존성 분석 미지원 — 수동 확인 필요 (vendored 라이브러리, git 서브모듈, 시스템 패키지 여부를 직접 점검하세요)". C/Make처럼 패키지 매니저가 없는 생태계가 여기 해당한다. 조용한 생략 금지.
```

- [ ] **Step 4: frontmatter allowed-tools 추가**

`- Bash(pip-audit *)` 다음에 추가:

```yaml
  - Bash(cargo tree *)
  - Bash(cargo audit *)
```

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-tech-debt/SKILL.md
git commit -m "$(cat <<'EOF'
feat: gx-tech-debt 의존성 분석을 projectTypes 기반으로 일반화

- rust(cargo tree/audit) 절 추가, 미정의 타입은 미지원 명시 보고
EOF
)"
```

### Task 15: 테스트 하네스 구축 가이드 신설

**Files:**
- Create: `docs/test-harness-guide.md`

**Interfaces:**
- Consumes: Task 9의 안내 문구가 이 경로를 참조한다 (경로 변경 금지).

- [ ] **Step 1: 가이드 작성**

전체 내용:

````markdown
# 테스트 하네스 구축 가이드

gx-tdd는 **호스트에서 실행 가능한 테스트**가 있어야 동작한다 (RGR 사이클·verify 게이트가 테스트를 직접 실행한다). 테스트 프레임워크가 없는 프로젝트는 이 가이드로 하네스를 먼저 구축한다.

## 공통 원칙

1. **호스트 실행 가능**: 테스트는 개발 PC에서 `1개 명령`으로 실행되고 exit code로 성패를 반환해야 한다.
2. **1개 명령**: 구축 후 `.claude/config.json`의 `projectTypes.{타입}.test`에 그 명령을 등록한다 (`/gx-setup`의 "프로젝트 타입 등록").
3. **실패 메시지**: 실패 시 어떤 assertion이 왜 실패했는지 출력되어야 RGR의 RED 확인이 성립한다.

## C 프로젝트

### 프레임워크 선택

| 프레임워크 | 특징 | 권장 상황 |
|-----------|------|----------|
| Unity | 단일 .c/.h, 의존성 없음, 매크로 assertion | 가장 단순. Make 기반 프로젝트에 직접 통합 |
| Ceedling | Unity+CMock+빌드 자동화 (Ruby 필요) | 모킹이 많은 임베디드. `ceedling test:all` 한 명령 |
| CppUTest | C/C++ 겸용, 메모리 누수 감지 | C++ 혼용 또는 누수 검증이 중요한 경우 |
| CTest(CMake) | CMake 내장 러너 | 이미 CMake 프로젝트인 경우 (assertion은 Unity 등과 조합) |

### Unity + Make 최소 구성

```
project/
├── src/          # 프로덕션 코드
├── test/
│   ├── unity/    # unity.c, unity.h, unity_internals.h (vendored)
│   └── test_xxx.c
└── Makefile
```

Makefile에 test 타깃 추가:

```makefile
TEST_SRCS := $(wildcard test/test_*.c) test/unity/unity.c
.PHONY: test
test: $(TEST_SRCS) $(SRCS_UNDER_TEST)
	@mkdir -p build
	$(HOST_CC) -Isrc -Itest/unity -o build/test_runner $^
	./build/test_runner
```

- `HOST_CC`는 크로스 컴파일러가 아닌 **호스트 컴파일러**(gcc/clang)다.
- 등록: `projectTypes."c-make".test` = `make test`.

### 임베디드: 듀얼 타깃 구조 (핵심)

레지스터 접근·ISR·HAL 호출이 로직에 섞여 있으면 호스트 테스트가 불가능하다. 다음 구조로 분리한다:

1. **HAL 인터페이스 분리**: 하드웨어 접근을 헤더(예: `hal_uart.h`)로 추상화하고, 타깃 구현(`hal_uart_stm32.c`)과 테스트 스텁(`test/stub_hal_uart.c`)을 링크 타임에 치환한다.
2. **로직은 순수 C로**: 비즈니스/프로토콜 로직 모듈은 HAL 헤더에만 의존하게 한다 — 이 모듈들이 gx-tdd RGR의 대상이다.
3. **두 빌드 타깃**: `make`(크로스, 타깃 펌웨어)와 `make test`(호스트, 로직+스텁)를 분리한다.

test-architect가 testability를 평가할 때 이 구조(HAL 추출·듀얼 타깃)를 기준으로 재설계를 권고할 수 있다.

## 기타 언어

- Python: `pip install pytest` → `pytest`. 테스트 파일 `test_*.py`.
- Go/Rust: 언어 내장 (`go test ./...` / `cargo test`) — 별도 구축 불필요.
- .NET: `dotnet new xunit` 테스트 프로젝트 추가 → `dotnet test`.

## 구축 후

1. `/gx-setup` 실행 → "프로젝트 타입 등록"에서 test 명령 등록 + 권한 추가.
2. 샘플 테스트 1개가 통과하는지 확인 (`0 failures`).
3. 이후 `/gx-tdd {요청}`으로 TDD 파이프라인 진입.
````

- [ ] **Step 2: 커밋**

```bash
git add docs/test-harness-guide.md
git commit -m "$(cat <<'EOF'
docs: 테스트 하네스 구축 가이드 신설

- C(Unity/Ceedling/CppUTest/CTest) 선택 기준과 Make 최소 구성
- 임베디드 듀얼 타깃(HAL 분리·링크 타임 치환) 구조 안내
EOF
)"
```

### Task 16: README 반영 + v1.21.0 릴리스

**Files:**
- Modify: `README.md` (언어 지원 안내 — 기존 구성에 맞는 위치에 삽입)
- Modify: `CHANGELOG.md` (최상단 새 섹션)
- Modify: `.claude-plugin/plugin.json` (`version`)
- Modify: `.claude-plugin/marketplace.json` (`plugins[0].version`)

- [ ] **Step 1: README에 언어 지원 절 추가**

README.md를 Read하여 기존 목차/구성에 맞는 위치(설치/시작하기 부근)에 삽입:

```markdown
## 언어/프레임워크 지원

파이프라인은 언어 중립적이다. 빌드/테스트 명령은 `.claude/config.json`의 `projectTypes`(SSOT)에서 읽으며, `/gx-setup`의 "프로젝트 타입 등록"이 빌드 파일을 감지해 등록을 제안한다 (C/Make·CMake·Ceedling, Python, Go, Rust, .NET, Maven 등 힌트 내장 — 목록 밖 스택도 확인 후 등록 가능). 테스트 프레임워크가 없는 프로젝트는 `docs/test-harness-guide.md`를 참고해 하네스를 먼저 구축한다.
```

- [ ] **Step 2: CHANGELOG 섹션 추가**

CHANGELOG.md 최상단(기존 최신 섹션 위)에 추가:

```markdown
## v1.21.0 (2026-08-04)

언어 중립화 — 모든 언어/프레임워크에서 파이프라인 사용 가능.

- projectTypes를 SSOT로 승격: 선택 필드 `warningPattern`(경고 카운트)·`artifacts`(ignore 보강) 추가
- gx-setup "프로젝트 타입 등록" 단계 신설: 빌드 파일 감지 → 힌트 카탈로그 제안 → config 기록 → settings.local.json 권한 등록. JDK 확인은 java 계열 조건부로 변경
- gx-dev/gx-tdd phase-setup: 타입 미감지 시 인라인 등록 (질문 1회 → 영구 자동)
- gx-verify·phase-review: 하드코딩 명령 표를 config 참조 예시로 격하, 경고 규약 warningPattern 일반화
- gx-tdd 기준선 게이트: 테스트 하네스 부재 감지 + 구축 가이드(docs/test-harness-guide.md) 안내
- allowed-tools에 make/cmake/ctest/ceedling/cargo/mvn/dotnet 추가 (gx-tdd·gx-dev·gx-ralph-iterate)
- architect·coder·test-architect·testing-anti-patterns에 C/비-OO 관점 병기
- gx-context 자동 스캔 언어 중립 휴리스틱화, gx-tech-debt 의존성 분석 projectTypes 분기 (rust 추가, 미지원 명시 보고)
- lint [20/20] 언어 중립화 계약 불변식 추가
```

- [ ] **Step 3: 버전 범프**

- `.claude-plugin/plugin.json`: `"version": "1.20.0"` → `"version": "1.21.0"`
- `.claude-plugin/marketplace.json`: `plugins[0].version` 동일 변경
(정확한 현재 버전 문자열은 파일에서 확인 후 교체 — main 최신 기준)

- [ ] **Step 4: lint 전체 통과 확인**

Run: `bash scripts/lint-consistency.sh; echo "exit=$?"`
Expected: `[1/20] 버전 3중 일치 ... ok ... = 1.21.0`, `정합성 린트 통과`, exit=0

- [ ] **Step 5: 커밋 + PR 생성**

```bash
git add README.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "$(cat <<'EOF'
chore: v1.21.0 릴리스 — 언어 중립화

- CHANGELOG v1.21.0 섹션, plugin.json·marketplace.json 버전 동기
- README 언어/프레임워크 지원 절 추가
EOF
)"
```

이후 오케스트레이터가 `Skill("oh-my-gx:gx-pull-request")`로 PR 3을 생성한다.

### Task 17: 수동 QA 시나리오 (PR 3 머지 전 확인)

**Files:** 없음 (검증 전용)

- [ ] **Step 1: C 샘플 스모크 테스트**

임시 디렉토리(스크래치패드)에 최소 C 프로젝트(Makefile + src/calc.c + test/ Unity 구성 또는 `make test`가 동작하는 최소 스텁)를 만들고:
1. `/gx-setup` → "프로젝트 타입 등록"이 Makefile을 감지해 `c-make` 제안·등록·권한 추가를 수행하는지
2. `/gx-tdd {간단 요청} 핵심만` → 기준선 게이트가 `make test`를 실행하고 RGR이 진행되는지
3. 하네스를 제거한 사본에서 → 기준선 게이트가 하네스 부재를 감지·안내 후 중단하는지

- [ ] **Step 2: 기존 스택 회귀 확인**

java-spring 또는 node 프로젝트(기존 config)에서 `/gx-tdd --status`·gx-verify 단독 호출이 **등록 질문 없이** 현행과 동일하게 동작하는지 확인한다.

- [ ] **Step 3: 결과 보고**

시나리오 결과(통과/실패, 실패 시 재현 절차)를 PR 3 본문에 기록한다.
