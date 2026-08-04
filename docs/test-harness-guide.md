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
test: $(TEST_SRCS) $(SRCS_UNDER_TEST)
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
