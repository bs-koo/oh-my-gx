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
