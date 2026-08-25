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

## JS/TS 프론트엔드

가장 흔한 하네스 부재 케이스다. Nuxt·Next·Vite 스캐폴드는 `dev`/`build`/`lint`만 만들고 테스트 러너를 넣지 않는다. `package.json`에 `scripts.test`가 없고 devDependencies에 `vitest`/`jest`가 없으면 하네스가 없는 것이다.

### 최소 구성 (Vitest)

```bash
pnpm add -D vitest            # npm이면 npm i -D vitest
```

`package.json`에 스크립트를 추가한다. gx-setup이 등록할 test 명령이 이것이다.

```json
"scripts": { "test": "vitest run" }
```

`vitest run`은 watch 없이 1회 실행하고 종료한다 — CI와 verify 게이트가 요구하는 형태다. `vitest`(watch 모드)를 등록하면 게이트가 영원히 끝나지 않는다.

### 컴포넌트까지 테스트하려면

```bash
pnpm add -D @vue/test-utils happy-dom          # Vue/Nuxt
pnpm add -D @testing-library/react jsdom        # React
```

DOM 환경을 `vitest.config.ts`에 지정한다 (`environment: 'happy-dom'` 또는 `'jsdom'`). Nuxt는 앱 컨텍스트(auto-import·composable)가 필요한 컴포넌트가 많아 `@nuxt/test-utils`의 설정 헬퍼를 쓰는 편이 확실하다.

### 첫 테스트는 순수 로직부터

프레임워크 렌더링 없이 도는 곳에서 시작하면 러너·설정·CI 연결이 한 번에 검증된다. 유틸(`lib/`, `utils/`), 컴포저블·훅, 라우팅 가드가 그 자리다. 컴포넌트 마운트 테스트는 그다음에 붙인다.

```ts
// lib/formatCurrency.spec.ts
import { formatCurrency } from './formatCurrency'

it('천단위_구분기호를_넣는다', () => {
  expect(formatCurrency(1234567)).toBe('1,234,567')
})
```

### 모노레포라면

프론트가 하위 디렉토리에 있으면 저장소 루트에서 도는 명령으로 등록한다 (`pnpm --dir frontend test`). `cd frontend && ...` 형태는 권한 prefix와 매칭되지 않아 실행마다 프롬프트가 뜬다. 백엔드와 함께 등록하는 복합 타입 구성은 `gx-setup/references/project-type-hints.md`의 "복합 타입" 절을 따른다.

### UI 테스트를 쓸 때

셀렉터를 CSS 클래스나 DOM 구조에 묶으면 디자인을 바꿀 때마다 테스트가 깨지고, 결국 팀이 테스트를 지우게 된다. 규약은 `gx-tdd/references/frontend-testing.md`에 있다 — 하네스를 구축하기 전에 §3~4만 읽어두면 첫 테스트부터 방향이 잡힌다.

## 기타 언어

- Python: `pip install pytest` → `pytest`. 테스트 파일 `test_*.py`.
- Go/Rust: 언어 내장 (`go test ./...` / `cargo test`) — 별도 구축 불필요.
- .NET: `dotnet new xunit` 테스트 프로젝트 추가 → `dotnet test`.

## 구축 후

1. `/gx-setup` 실행 → "프로젝트 타입 등록"에서 test 명령 등록 + 권한 추가.
2. 샘플 테스트 1개가 통과하는지 확인 (`0 failures`).
3. 이후 `/gx-tdd {요청}`으로 TDD 파이프라인 진입.
