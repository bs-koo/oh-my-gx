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
| `pom.xml` | `java-maven` | `mvn -B compile` | `mvn -B test` | `warning` | `target/` | `Bash(mvn *)` |
| `composer.json` | `php` | (없음) | `./vendor/bin/phpunit` | `warning` | `vendor/` | `Bash(./vendor/bin/phpunit *)` |
| `build.gradle(.kts)` | `java-spring` | (기본 템플릿 참조) | (기본 템플릿 참조) | `warning` | `.gradle/`, `build/` | `Bash(./gradlew *)` |
| `package.json` | `node` | (기본 템플릿 참조) | (기본 템플릿 참조) | `warn` | `node_modules/`, `dist/` | `Bash(npm *)` |
| `vitest.config.*` / devDeps에 `vitest` | `node` | (프로젝트 build 스크립트) | `vitest run` | `warn` | `node_modules/`, `dist/`, `.nuxt/`, `.next/` | `Bash(npx *)` 또는 패키지 매니저 |
| `jest.config.*` / devDeps에 `jest` | `node` | (프로젝트 build 스크립트) | `jest --ci` | `warn` | `node_modules/`, `dist/` | `Bash(npx *)` 또는 패키지 매니저 |

## 프론트엔드 주의 — `npm test`를 그대로 제안하지 않는다

`package.json`이 감지됐다고 `npm test`를 등록하면 **대부분의 프론트 프로젝트에서 실패한다.** Nuxt·Next·Vite 스캐폴드는 `dev`/`build`/`lint`만 만들고 `test` 스크립트를 넣지 않는 경우가 많다. 등록 자체는 되지만 실행하면 `Missing script: test`가 나온다.

제안 전에 이 순서로 확인한다:

1. `package.json`의 `scripts.test`가 있는가 → 있으면 `{pm} test`를 제안
2. 없으면 devDependencies에 러너(`vitest`/`jest`)가 있는가 → 있으면 러너를 직접 호출 (`vitest run`, `jest --ci`)
3. 둘 다 없으면 → **테스트 하네스 부재**다. test 필드를 비워 등록하고 `docs/test-harness-guide.md`의 JS/TS 절을 안내한다. 없는 명령을 지어내면 온보딩은 통과하고 파이프라인 후반에 터진다

프론트는 러너가 아직 없는 상태가 정상적인 출발점이다. 그 사실을 정확히 기록하는 편이, 그럴듯한 명령을 넣어 나중에 실패하는 것보다 낫다.

## 복합 타입 — 한 저장소에 여러 스택

풀스택 모노레포(예: Spring + Nuxt)처럼 **양쪽 모두 실제 소스와 테스트를 가진 경우**, 타입을 하나만 고르면 나머지 레이어는 verify 게이트가 실행조차 하지 않아 미검증으로 통과한다. 한 타입 키에 양쪽을 이어 등록한다.

```json
"fullstack": {
  "detect": ["build.gradle.kts", "frontend/package.json"],
  "build": "./gradlew clean build -x test && pnpm --dir frontend build",
  "test":  "./gradlew test && pnpm --dir frontend test",
  "warningPattern": "warn",
  "artifacts": [".gradle/", "build/", "frontend/node_modules/", "frontend/dist/"]
}
```

조합 규칙:

1. **`&&`로 잇는다.** 한쪽이 실패하면 exit code가 살아서 게이트가 정상 차단된다. `;`로 이으면 뒤 명령의 결과만 남아 앞의 실패를 삼킨다.
2. **`cd A && ...` 대신 도구의 디렉토리 옵션을 쓴다** (`pnpm --dir`, `npm --prefix`, `make -C`, `mvn -f`). `cd`로 시작하는 명령은 권한 prefix 패턴과 매칭되지 않아 실행마다 권한 프롬프트가 뜬다.
3. **권한 prefix는 조각마다 도출한다** — 위 예시면 `Bash(./gradlew *)`와 `Bash(pnpm *)` 둘 다 등록한다.
4. **`warningPattern`은 하나뿐이다.** `warn`으로 두면 `warning`도 함께 잡혀 대부분의 조합에 무난하다.
5. **`detect`에 양쪽 파일을 모두 넣는다.** 한쪽만 넣으면 다른 쪽만 있는 저장소에서 오탐한다.

한쪽이 도구용일 뿐이면(문서 사이트용 `package.json` 등) 복합이 아니라 주 타입 하나를 고른다.

## 주의

- Node 변형은 lock 파일로 구분해 명령을 제안한다: `pnpm-lock.yaml` → `pnpm test`, `yarn.lock` → `yarn test`, `bun.lockb`/`bun.lock` → `bun test` (타입 키는 동일하게 `node`, 명령만 변형).
- C 계열은 test 명령이 프로젝트마다 크게 다르다 (make의 test 타깃 유무, CTest 구성 여부). 제안 후 반드시 실제 실행 가능한지 사용자에게 확인받는다.
- 임베디드 C에서 test는 **호스트에서 실행 가능**해야 gx-tdd RGR·verify가 성립한다. 타깃 전용 빌드만 있으면 하네스 구축 가이드(oh-my-gx 저장소 `docs/test-harness-guide.md`)를 안내한다.
