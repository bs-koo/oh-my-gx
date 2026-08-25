# TDD 가이드 — 개념부터 gx-tdd 적용까지

> 대상: GX 사업본부 개발자
> 범위: TDD의 목표·목적·필요성(왜) → 수행 방법(어떻게) → `oh-my-gx:gx-tdd`로 적용하는 법(우리 환경에서 실제로)
> 관련 문서: [사용 가이드](guide.md) · [설계 결정](design-decisions.md) · 스킬 원문 `.claude/skills/gx-tdd/`

---

## 목차

1. [한 장 요약](#1-한-장-요약)
2. [목표와 목적](#2-목표와-목적)
3. [필요성 — 왜 사후 테스트로는 부족한가](#3-필요성--왜-사후-테스트로는-부족한가)
4. [기초 개념](#4-기초-개념)
   - 4.1 [테스트 피라미드](#41-테스트-피라미드)
   - 4.2 [테스트 더블](#42-테스트-더블)
   - 4.3 [테스트 가능한 구조](#43-테스트-가능한-구조)
   - 4.4 [RED-GREEN-REFACTOR 루프](#44-red-green-refactor-루프)
5. [수행 방법 — 손으로 하는 TDD](#5-수행-방법--손으로-하는-tdd)
6. [적용 방법 — gx-tdd로 강제되는 TDD](#6-적용-방법--gx-tdd로-강제되는-tdd)
7. [실전 시나리오 — 유저 등록·조회, 포인트 충전](#7-실전-시나리오--유저-등록조회-포인트-충전)
8. [합리화 격파 표](#8-합리화-격파-표)
9. [체크리스트](#9-체크리스트)
10. [참고 자료](#10-참고-자료)

---

## 1. 한 장 요약

```
TDD의 본질
  테스트를 "먼저 쓰는 것"이 아니라,
  설계 단위를 잘게 쪼개고 그것이 검증 가능하게 구현되었는지 확인하는 것.

3단계 루프
  RED     실패하는 테스트를 먼저 쓴다     → "무엇을 해야 하는가"를 정의
  GREEN   통과하는 최소 코드를 쓴다        → 요구사항 외의 것을 만들지 않는다
  REFACTOR 통과를 유지하며 구조를 정리한다  → 테스트가 안전망이 된다

gx-tdd가 하는 일
  이 루프를 사람의 의지가 아니라 파이프라인 게이트로 강제한다.
  RED 없이 코드를 쓸 수 없고, 테스트 실행 증거 없이 커밋할 수 없다.
```

| 구분 | 수동 TDD | gx-tdd |
|------|---------|--------|
| RED 선행 | 개발자의 규율에 의존 | red-writer 전담 + 격리 검증으로 강제 |
| 최소 구현 | "이왕 하는 김에" 과잉 구현 | green-coder YAGNI + 과잉 구현 감지 |
| 리팩터 안전성 | 수동 확인 | 매 정리 후 테스트 재실행, 깨지면 롤백 |
| 완료 판정 | "돌려봤는데 되던데요" | verify 게이트 — 신선한 실행 증거 없으면 커밋 차단 |

---

## 2. 목표와 목적

### 2.1 목표

**검증 가능한 단위로 설계를 쪼개고, 각 단위가 의도대로 동작함을 실행 증거로 남기는 것.**

TDD의 목표는 커버리지 숫자가 아니다. 커버리지는 결과일 뿐이다. 목표는 두 가지다.

1. **설계 단위의 크기를 강제로 줄인다** — 테스트를 먼저 쓰려면 대상이 작고 격리 가능해야 한다. 테스트가 어렵다는 것은 설계가 잘못됐다는 신호다.
2. **"됐다"의 기준을 주관에서 증거로 바꾼다** — "동작할 것 같다"가 아니라 "N개 통과, 0개 실패"가 완료의 정의가 된다.

### 2.2 목적 — TDD가 실제로 해결하는 문제

| 목적 | 설명 |
|------|------|
| 요구사항을 먼저 정리한다 | 테스트를 쓰려면 입력·조건·기대 결과를 확정해야 한다. 모호한 요구사항은 테스트로 표현되지 않는다 |
| 점진적 설계를 유도한다 | 한 번에 큰 덩어리를 만들 수 없다. 작은 단위로 쪼개고 붙이는 흐름이 강제된다 |
| 인터페이스가 자연스럽게 나온다 | 테스트가 첫 번째 호출자다. 쓰기 불편한 API는 테스트를 쓰는 순간 드러난다 |
| 리팩토링이 가능해진다 | 회귀를 즉시 감지하는 테스트가 있어야 구조를 바꿀 용기가 생긴다 |
| 사후 디버깅 시간을 줄인다 | 실패 지점이 최근 변경 한 단위로 좁혀진다 |

### 2.3 흔한 오해

> "TDD는 테스트를 먼저 쓰는 규칙이다"

절반만 맞다. 순서는 수단이고, 핵심은 **검증 가능한 단위로 쪼개는 것**이다. 순서를 지켰지만 테스트가 모의(mock)의 동작만 확인하고 있다면 TDD를 한 것이 아니다.

> "TDD는 항상 테스트가 먼저여야 한다"

현장에는 두 전략이 공존한다.

| 전략 | 설명 | 적합한 상황 |
|------|------|-----------|
| TFD (Test First Development) | 테스트 먼저 → 코드를 맞춰 구현 | 도메인 규칙·비즈니스 로직 중심 |
| TLD (Test Last Development) | 코드 먼저 → 테스트 나중 | API·계층 설계 탐색이 선행돼야 하는 상황 |

`gx-tdd`는 TFD를 강제하는 파이프라인이다. 탐색적 작업이나 계층 스캐폴딩처럼 TLD가 맞는 국면에는 `oh-my-gx:gx-dev`를 쓴다. 도구를 나눠 둔 이유가 이것이다 — TDD를 안 할 거면 TDD 파이프라인을 우회하는 게 아니라, 애초에 다른 파이프라인을 고른다.

---

## 3. 필요성 — 왜 사후 테스트로는 부족한가

### 3.1 사전 테스트와 사후 테스트의 결정적 차이

같은 커버리지라도 얻는 것이 다르다.

```
사후 테스트가 던지는 질문:  "이 코드가 뭘 하고 있지?"   → 구현을 서술한다
사전 테스트가 던지는 질문:  "이 코드가 뭘 해야 하지?"   → 요구사항을 발견한다
```

사후 테스트는 이미 존재하는 구현에 편향된다. 구현이 놓친 케이스는 테스트도 놓친다. 구현이 잘못된 가정을 했으면 테스트가 그 가정을 굳혀버린다. 실패를 한 번도 목격하지 못한 테스트는, 사실 그 테스트가 무언가를 검증하고 있다는 증거조차 없다.

**RED를 목격하는 것 자체가 검증이다.** 실패를 본 적 없는 테스트는 assertion을 지워도 통과할 수 있다.

### 3.2 AI 에이전트 시대에 더 커진 필요성

에이전트가 코드를 쓰는 환경에서 TDD의 가치는 오히려 커진다.

- 에이전트는 **그럴듯한 완료 보고**를 잘한다. "구현했습니다", "정상 동작합니다"는 검증이 아니다.
- 에이전트는 **요청하지 않은 기능을 덧붙이는** 경향이 있다. 통과시켜야 할 테스트가 명시돼 있으면 범위가 고정된다.
- 에이전트는 **테스트를 고쳐서 통과시키려는** 유혹에 취약하다. 이건 GREEN 단계의 대표적 실패 모드다.

`gx-tdd`가 에이전트 보고를 믿지 않고 오케스트레이터가 직접 명령을 재실행하도록 설계된 이유다.

### 3.3 필요성을 부정하는 논리들

현장에서 TDD를 건너뛰는 이유는 대부분 아래 여섯 갈래다. 자세한 반박은 [8장 합리화 격파 표](#8-합리화-격파-표)에 있다.

| 유형 | 대표 문장 |
|------|----------|
| 단순함 합리화 | "이건 너무 간단해서 테스트가 필요 없다" |
| 사후 테스트 합리화 | "이미 수동으로 확인했다" |
| 매몰비용 합리화 | "몇 시간 짠 코드를 버리는 건 낭비다" |
| 실용주의 합리화 | "TDD는 교조적이다, 이번 한 번만" |
| 확신 합리화 | "이 케이스는 명백히 동작한다" |
| 환경 합리화 | "기존 코드에 테스트가 없다" |

이 문장들의 공통점은 **검증 없이 완료를 주장하기 위한 사전 정당화**라는 점이다. 하나라도 떠올랐다면 그 자체가 STOP 신호다.

---

## 4. 기초 개념

### 4.1 테스트 피라미드

테스트는 범위에 따라 역할이 나뉜다. **아래로 갈수록 빠르고 많이, 위로 갈수록 느리지만 신중하게.**

```
        /\        E2E        느림 / 적게 / 시나리오 전체
       /  \       ─────────────────────────────────
      /    \      통합        중간 / 적당히 / 컴포넌트 연결
     /      \     ─────────────────────────────────
    /________\    단위        빠름 / 많이 / 순수 로직
```

| 계층 | 대상 | 목적 | 환경 | 기술 |
|------|------|------|------|------|
| 단위 (Unit) | 도메인 모델 (Entity, VO, Domain Service) | 순수 로직의 정합성·규칙 검증 | Spring 없이 순수 JVM, 모든 의존성은 테스트 대역 | JUnit5, AssertJ, Kotest |
| 통합 (Integration) | Service, Facade 등 계층 로직 | 여러 컴포넌트가 연결된 상태에서 비즈니스 흐름 검증 | `@SpringBootTest`, 실제 Bean, Test DB | SpringBootTest + H2 / TestContainers |
| E2E | 전체 앱 (Controller → Service → DB) | 실제 HTTP 요청 단위 시나리오 | MockMvc, TestRestTemplate | `@AutoConfigureMockMvc`, WebTestClient |

예시로 구분해 보면 이렇다.

- 단위: 포인트 충전 시 최대 한도 초과 여부를 검증한다
- 통합: 포인트가 실제로 충전되고 DB에 반영되며 이벤트가 발행되는 전 과정을 검증한다
- E2E: 회원가입 → 포인트 충전 → 주문 흐름을 HTTP 요청으로 수행한 결과를 검증한다

**RGR 사이클에서 주로 도는 계층은 단위 테스트다.** 빠르기 때문이다. RED-GREEN을 몇 초 안에 반복하려면 Spring 컨텍스트를 띄우면 안 된다. 통합·E2E는 AC 단위로 별도 태스크에 배치한다.

### 4.2 테스트 더블

테스트 대상이 의존하는 외부 객체를 빠르고 안전하게 흉내 내는 대역 객체다.

#### 역할과 도구를 구분하라

`Stub`, `Mock`, `Spy`, `Fake`는 **테스트에서의 역할**이고, `mock()`, `spy()`는 **객체 생성 도구**다. 하나의 mock 객체가 Stub 역할과 Mock 역할을 동시에 맡을 수 있다.

```kotlin
val repo = mock<UserRepository>()                    // 도구: mock()
whenever(repo.findById(1L)).thenReturn(User(...))    // 역할: Stub  (고정 응답 제공)
verify(repo).findById(1L)                            // 역할: Mock  (호출 검증)
```

#### 역할별 정리

| 역할 | 목적 | 사용 방식 | 예시 |
|------|------|----------|------|
| Dummy | 자리만 채움 (사용되지 않음) | 생성자 등에 전달 | `User(null, null)` |
| Stub | 고정된 응답 제공 (상태 기반) | `when().thenReturn()` | `repo.find()`가 항상 특정 유저 반환 |
| Mock | 호출 여부·횟수 검증 (행위 기반) | `verify(...)` | 함수가 실행됐는지 검증 |
| Spy | 진짜 객체를 감싸고 일부만 조작 | `spy()` + `doReturn()` | 실제 서비스 중 특정 동작만 덮어씀 |
| Fake | 실제처럼 동작하는 가짜 구현체 | 직접 클래스 구현 | `InMemoryUserRepository` |

```kotlin
// Stub — 흐름만 통제하고 싶을 때. "이렇게 호출하면 이렇게 응답해줘"
val userRepo = mock<UserRepository>()
whenever(userRepo.findById(1L)).thenReturn(User("alen"))

// Mock — 호출 여부가 검증 대상일 때. "너 이렇게 동작했니?"
val speaker = mock<Speaker>()
speaker.say("hello")
verify(speaker, times(1)).say("hello")

// Spy — 로직은 그대로 쓰되 일부만 덮어쓰고 싶을 때
val spyFriend = spy(Friend())
spyFriend.hangout()
verify(spyFriend).hangout()

// Fake — 완전히 독립적인 테스트 환경이 필요할 때
class InMemoryUserRepository : UserRepository {
    private val data = mutableMapOf<Long, User>()
    override fun save(user: User) { data[user.id] = user }
    override fun findById(id: Long): User? = data[id]
}
```

#### 모의 3원칙 (gx-tdd가 강제하는 규칙)

```
1. 모의의 동작을 테스트하지 마라
2. 프로덕션 클래스에 테스트 전용 메서드를 넣지 마라
3. 의존성을 이해하지 못한 채 모킹하지 마라
```

**모의는 격리 도구이지 검증 대상이 아니다.** 아래는 대표적인 위반이다.

```kotlin
// 잘못됨 — 모의가 존재하는지를 검증할 뿐, 우리 코드는 검증되지 않는다
val sender = mock<NotificationSender>()
whenever(sender.send(any())).thenReturn(true)
assertTrue(sender.send(Notice()))

// 올바름 — 모의는 격리에만 쓰고, 검증 대상은 실제 서비스의 동작이다
val failingSender = mock<NotificationSender>()
whenever(failingSender.send(any())).thenReturn(false)
val service = NoticeService(failingSender, retryQueue)

service.notify(Notice())

assertEquals(1, retryQueue.size)   // 검증 대상: service의 동작
```

모의가 과해지는 경고 신호는 이렇다. 하나라도 해당하면 "여기서 정말 모의가 필요한가"를 다시 묻는다.

- 모의 셋업이 테스트 로직보다 길다
- 통과시키려고 전부 모킹하고 있다
- 모의를 제거하면 테스트가 깨진다
- 왜 모의가 필요한지 설명할 수 없다

이럴 때는 복잡한 모의보다 실제 컴포넌트를 쓰는 통합 테스트가 더 단순한 경우가 많다.

전체 안티패턴 카탈로그: `.claude/skills/gx-tdd/references/testing-anti-patterns.md`

### 4.3 테스트 가능한 구조

**검증하고 싶은 로직을, 외부 의존성과 격리된 상태에서 단독으로 확인할 수 있는 구조.**

#### 테스트하기 어려운 구조

| 문제 | 왜 문제인가 |
|------|-----------|
| 내부에서 의존 객체 직접 생성 (`new`) | 테스트 대역으로 대체 불가 → 격리 불가능 |
| 하나의 함수가 너무 많은 책임 | 실패 원인 추적 불가 |
| 외부 API·DB 접근이 하드코딩 | 실제 환경 없이 테스트 불가 → 느리고 불안정 |
| private 로직·static 메서드 남용 | 로직 분리 불가 → 단위 테스트 불가 |

```kotlin
// 테스트 불가능한 구조
class OrderService {
    fun completeOrder(userId: Long, productId: Long) {
        val user = UserJpaRepository().findById(userId)         // 직접 생성 → 대체 불가
        val product = ProductJpaRepository().findById(productId)

        if (product.stock <= 0) throw IllegalStateException()   // 도메인 로직이 서비스에 노출
        product.stock--

        if (user.point < product.price) throw IllegalStateException()
        user.point -= product.price

        OrderRepository().save(Order(user, product))
    }
}
```

문제는 세 가지다. 외부 의존성을 직접 생성해 Mock/Fake로 바꿀 수 없고, 도메인 규칙·상태 변경·저장이 한 곳에 몰려 있으며, `OrderServiceTest` 하나가 모든 케이스를 떠안아 실패 시 원인을 좁힐 수 없다.

#### 테스트 가능한 구조로

| 포인트 | 방법 |
|--------|------|
| 외부 의존성 분리 | 인터페이스화 + 생성자 주입(DI) |
| 비즈니스 로직 분리 | 도메인 엔티티 또는 전용 Service로 책임 이동 |
| 책임 단일화 | 한 함수는 한 역할만 |
| 상태 중심 설계 | "입력 → 상태 변화 → 결과" 구조 |

```kotlin
// 테스트 가능한 구조
class OrderService(
    private val userReader: UserReader,           // 인터페이스 주입 → Fake/Mock 가능
    private val productReader: ProductReader,
    private val orderRepository: OrderRepository,
) {
    fun completeOrder(command: OrderCommand) {
        val user = userReader.get(command.userId)
        val product = productReader.get(command.productId)

        product.decreaseStock()      // 규칙은 도메인이 소유
        user.pay(product.price)

        orderRepository.save(Order(user, product))
    }
}
```

이제 테스트가 `UserTest`(결제 규칙), `ProductTest`(재고 규칙), `OrderServiceTest`(흐름 조립)로 나뉜다. 실패하면 어느 층의 문제인지 즉시 드러난다.

> `gx-tdd`는 이 판단을 **test-architect 에이전트의 testability score(1~10)** 로 계량화한다. 7점 미만이면 구현 단계로 진입할 수 없다. 강결합·전역 상태·static 의존이 남아 있으면 red-writer가 의존성을 격리하지 못해 사이클 자체가 멈추기 때문이다.

### 4.4 RED-GREEN-REFACTOR 루프

```
반복
  1. 실패하는 테스트 작성      (RED)
  2. 통과할 최소한의 코드 작성  (GREEN)
  3. 구조 개선 및 리팩토링      (REFACTOR)
```

각 단계의 계약은 다음과 같다.

| 단계 | 해야 하는 것 | 절대 하면 안 되는 것 |
|------|------------|-------------------|
| RED | AC 하나를 검증하는 테스트 1개 작성, **실패를 눈으로 확인** | 프로덕션 코드 작성, 여러 동작을 한 테스트에 묶기 |
| GREEN | 그 테스트만 통과시키는 가장 단순한 구현 | 미래를 대비한 기능·에러 핸들링·로깅 추가, **테스트 수정** |
| REFACTOR | 중복 제거, 네이밍, 매직 넘버 상수화, 구조 정리 | 동작 변경, 기능 추가, 시그니처 변경, 성능 최적화 |

**GREEN에서 테스트를 고치면 안 되는 이유**: 테스트는 요구사항의 표현이다. 테스트를 고쳐 통과시키는 것은 요구사항을 구현에 맞추는 것이다. 테스트 자체에 결함이 의심되면 고치지 말고 RED로 돌아가 다시 쓴다.

---

## 5. 수행 방법 — 손으로 하는 TDD

도구 없이 TDD를 수행할 때의 실무 절차다. 6장의 자동화는 이 절차를 그대로 기계화한 것이다.

### 5.1 요구사항을 Given-When-Then으로 쓴다

테스트로 바꿀 수 없는 요구사항은 요구사항이 아니라 희망사항이다.

```
AC-1: 잘못된 비밀번호로 로그인 시도 시 401 응답
  Given: 사용자가 등록되어 있고 비밀번호가 "correct"이다
  When:  "wrong" 비밀번호로 POST /login을 호출한다
  Then:  401 응답이 반환되고 응답 body의 message가 "비밀번호 불일치"이다
```

금지 형태:

```
AC-1: 잘못된 비밀번호로 로그인하면 에러가 나와야 한다     (무엇을 assert할지 알 수 없다)
AC-2: 포인트가 적절히 충전된다                          ("적절히"는 검증 불가)
```

Then 절 점검 기준 세 가지:

- Given / When / Then 세 절이 모두 있는가
- Then이 자동 테스트로 확인 가능한 구체값(응답 코드, 필드 값, 호출 횟수, 잔액)을 포함하는가
- "올바르게", "적절히", "정상적으로" 같은 표현이 Then에 없는가

### 5.2 AC를 2~15분짜리 태스크로 쪼갠다

한 태스크는 하나의 AC 또는 하나의 컴포넌트에 대응하고, RED→GREEN→REFACTOR를 한 호흡에 마칠 수 있는 크기여야 한다. 태스크 간 파일 충돌이 없도록 나눈다.

### 5.3 사이클을 돈다

```
for 태스크:
    RED       실패 테스트 작성 → 테스트 실행 → 실패 메시지 확인 (필수)
    GREEN     최소 구현 → 대상 테스트 통과 확인 → 전체 테스트로 회귀 확인
    REFACTOR  정리 1건 → 테스트 실행 → 통과하면 다음 정리, 깨지면 즉시 롤백
```

각 단계에서 스스로 확인할 것:

- RED 후: 정말 실패했는가? 통과했다면 테스트가 잘못됐거나 이미 구현이 있는 것이다
- GREEN 후: 다른 테스트가 깨지지 않았는가? 테스트에서 쓰이지 않는 메서드·필드를 추가하지 않았는가
- REFACTOR 후: 테스트 수가 줄지 않았는가? public 시그니처가 바뀌지 않았는가

### 5.4 좋은 테스트의 3기준

1. **하나의 동작만 검증한다** — 테스트 이름에 "그리고"가 필요하면 나눈다
2. **이름이 검증 대상을 설명한다** — `test1()`이 아니라 `shouldRejectWhenChargeExceedsLimit()`
3. **실제 코드를 우선하고, 모의는 불가피할 때만 쓴다** — 느리거나 외부에 의존하는 부분만 대체한다

### 5.5 완료를 주장하기 전에

```
테스트 명령을 지금 다시 실행했는가?         (캐시·이전 결과 금지)
실패 0건인가?                              ("대부분 통과"는 통과가 아니다)
실행된 테스트가 1건 이상인가?                (0건 실행은 검증이 아니다)
빌드가 성공하는가?
새로 생긴 경고가 없는가?
```

이 다섯 줄을 통과하기 전에는 "완료"라고 말하지 않는다.

---

## 6. 적용 방법 — gx-tdd로 강제되는 TDD

5장의 규율을 사람의 의지에 맡기지 않고 **파이프라인 게이트**로 강제하는 것이 `oh-my-gx:gx-tdd`다.

### 6.1 언제 gx-tdd를 쓰고 언제 gx-dev를 쓰나

| 상황 | 스킬 |
|------|------|
| 도메인 규칙·비즈니스 로직 구현, 버그 수정(회귀 방지 필요) | `/gx-tdd` |
| 계층 스캐폴딩, 탐색적 프로토타입, 설정 변경 | `/gx-dev` |

호출 방법:

```
/gx-tdd 포인트 충전 기능 TDD로 구현해줘
/gx-dev  관리자 화면 목록 API 추가해줘
```

"TDD로", "테스트 먼저", "테스트 주도", "RED-GREEN-REFACTOR" 같은 키워드가 있으면 자동으로 `gx-tdd`로 라우팅된다.

### 6.2 두 스킬의 실제 차이

| 단계 | gx-dev | gx-tdd |
|------|--------|--------|
| requirements | 자연어 AC | **Given-When-Then 강제** |
| design | 비판 검토 | **testability 평가 추가 (score ≥ 7)** |
| implement | coder 단일 호출 | **red-writer → green-coder → refactor-coder 순차** |
| review | qa + security 병렬 | **spec → quality 순차 강제** |
| complete | qa 통과 후 커밋 | **verify 게이트 통과 후 커밋** |

### 6.3 3대 Iron Law

```
1. NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
   실패 테스트 없이 프로덕션 코드 작성 금지

2. NO PHASE SKIPPING WITHOUT AN EXPLICIT ESCAPE
   명시적 탈출구(핵심 모드, --phase) 외에 Phase 건너뛰기 금지

3. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
   신선한 검증 증거 없이 완료 주장 금지
```

위반 시 처리:

| 위반 | 조치 |
|------|------|
| Iron Law 1 | 작성된 코드 삭제 후 RED부터 재시작 |
| Iron Law 2 | 건너뛴 Phase부터 재실행 |
| Iron Law 3 | verify 게이트로 복귀 |

우선순위는 1 → 3 → 2 순이다. 코드 우선 작성이 가장 심각하다.

### 6.4 전체 흐름

```
setup ─────── 브랜치·프로젝트 타입·코드 맵·도메인 컨텍스트 준비
   ↓
requirements ─ PRD 작성 (product-owner)
   ↓          [게이트 1] G-W-T 검증 — AC가 전부 Given-When-Then 형식인가
design ─────── 설계 (architect) + 비판 검토 (design-critic)
   ↓          [게이트 2] testability score ≥ 7 (test-architect)
implement ──── [게이트 3] 기준선 게이트 — 기존 테스트 GREEN + 경고 수 기록
   ↓          RGR 사이클: red-writer → green-coder → refactor-coder (태스크별 순차)
review ─────── [게이트 4] Mechanical Gate (build + test)
   ↓          spec-reviewer (AC 충족) → quality-reviewer (코드 품질) + security-auditor
complete ───── [게이트 5] TDD 이행 게이트 → verify 게이트 (gx-verify)
              → 인수 검증 (product-owner) → commit → PR
```

각 게이트는 통과하지 못하면 다음 단계로 넘어가지 않는다. "간단하니까", "이미 확인했으니까"로 넘길 수 없다.

### 6.5 에이전트 역할 분담

TDD의 각 단계를 **다른 에이전트가 맡는다.** 한 에이전트가 테스트와 구현을 모두 쓰면 구현에 편향된 테스트가 나오기 때문이다.

| 단계 | 에이전트 | 무엇을 보는가 | 무엇이 금지되는가 |
|------|---------|-------------|-----------------|
| RED | `red-writer` | AC(G-W-T) + 설계서 testability 섹션 + 기존 테스트 스타일 | **기존 프로덕션 코드 참조**, 프로덕션 코드 작성 |
| GREEN | `green-coder` | 실패 테스트 + 대상 시그니처 | **테스트 파일 수정**, 과잉 구현(YAGNI 위반) |
| REFACTOR | `refactor-coder` | 정리 대상 파일 + 정리 항목 | 동작 변경, 기능 추가, 시그니처 변경 |
| 스펙 리뷰 | `spec-reviewer` | PRD의 AC + diff | 코드 품질 평가 |
| 품질 리뷰 | `quality-reviewer` | diff + 컨벤션 | AC 충족 여부 평가 (PRD를 받지 않음) |
| testability | `test-architect` | 설계서 + AC | — |

**red-writer의 격리**가 이 구조의 핵심이다. 기존 구현을 보지 않고 AC와 인터페이스 정의만으로 테스트를 쓴다. 구현에 적응한 테스트("코드가 이러니까 이렇게 검증하자")를 원천 차단하기 위해서다. red-writer는 참조한 파일 목록을 자기신고하고, 오케스트레이터가 그 목록에 프로덕션 소스가 있으면 해당 테스트를 폐기하고 재작성시킨다.

### 6.6 RGR 사이클에서 실제로 검증되는 것

에이전트의 보고를 그대로 믿지 않는다. 오케스트레이터가 매 단계 직접 확인한다.

**verify_red (RED 직후)**

1. 보고된 테스트 명령을 직접 실행 → **실패해야 정상**. 통과하면 잘못된 테스트로 보고 재작성
2. 참조 파일 목록에 프로덕션 소스가 있으면 격리 오염 → 폐기 후 재작성
3. 테스트 파일 해시(`git hash-object`)와 `git status --porcelain` 스냅샷 기록 → GREEN 단계 무결성 기준선

**verify_green (GREEN 직후)**

1. "테스트 결함 의심" 보고가 있으면 red-writer로 되돌림 (green-coder가 테스트를 고치지 않는다)
2. 테스트 파일 해시 재계산 → **RED 시점과 다르면 무단 수정**. 원복 후 재호출, 재차 위반 시 사이클 중단
3. 대상 테스트 통과 + 전체 테스트 회귀 없음 확인, 전체 테스트 수 기록
4. 테스트에서 쓰이지 않는 메서드·필드가 추가됐으면 과잉 구현으로 보고

**verify_refactor (REFACTOR 직후)**

1. 전체 테스트 통과 확인
2. 테스트 수가 GREEN 시점보다 줄었으면 사유 확인 (무단 삭제면 롤백)
3. public 시그니처 변경 없음 확인

같은 태스크에서 green-coder가 3회 실패하면 사이클을 멈추고 architect에 재설계를 위임한다. 세 번 막히면 구현이 아니라 설계 문제라는 판단이다.

### 6.7 verify 게이트 — 완료의 정의

`gx-verify`는 커밋 직전 마지막 관문이다.

| 검사 | 차단 조건 |
|------|----------|
| 테스트 실행 | 실패 1건 이상 |
| 빌드 | exit code ≠ 0 |
| 테스트 실행 수 | **0건 실행** (캐시·UP-TO-DATE 포함, 신선 재실행 후에도 0건이면 차단) |
| 신규 경고 | RGR 시작 전 기록한 `warnings-baseline`보다 증가 |

원칙 세 가지:

- **캐시된 결과 사용 금지.** 반드시 새로 실행한다
- **에이전트 보고는 증거가 아니다.** 오케스트레이터가 직접 명령을 실행한다
- **검증 명령을 감지하지 못하면 통과가 아니라 차단이다.** 조용한 통과는 Iron Law 3 위반이다

기존 경고는 허용하고 이번 구현이 유입한 경고만 잡는 이유는, 레거시 경고 때문에 게이트가 상시 차단되면 게이트 자체가 무력화되기 때문이다.

### 6.8 모드 선택

| 모드 | 경로 | 언제 |
|------|------|------|
| 전체 | setup → requirements → design → implement → review → complete | 신규 기능, 설계 판단이 필요한 변경 |
| 핵심(core) | setup → requirements(AC만) → implement(RGR + 긴급 보안 감사) → complete | 소형 변경, 긴급 버그 수정 |

핵심 모드에서도 **RGR 사이클, G-W-T 게이트, verify 게이트는 유지된다.** 생략되는 것은 설계 단계(testability 평가)와 정식 리뷰뿐이다. "급하니까 TDD를 건너뛴다"는 선택지는 이 스킬에 없다. 테스트 없이 바로 구현하려면 `gx-dev`의 핵심 모드를 쓴다.

모델 프로파일은 절차와 직교한다. `--eco`를 주면 design-critic·test-architect·quality-reviewer가 sonnet으로 내려가지만(architect는 유지), 게이트와 Iron Law는 그대로다.

### 6.9 단계별 단독 호출

전체 파이프라인 없이 한 단계만 쓸 수도 있다.

| 명령 | 용도 |
|------|------|
| `/gx-red 포인트 한도 초과 시 예외` | 실패 테스트만 작성 |
| `/gx-green` | 실패 테스트를 통과시키는 최소 구현 |
| `/gx-refactor` | GREEN 유지하며 정리 |
| `/gx-verify` | 완료 검증만 실행 |

기존 코드베이스에 TDD를 점진 도입할 때 유용하다. 새로 만지는 부분만 `/gx-red`로 시작하는 식이다.

### 6.10 산출물

브랜치별로 `.dev/{branch-slug}/`에 남는다 (예: `feat/point-charge` → `.dev/feat-point-charge/`).

| 파일 | 내용 |
|------|------|
| `prd.md` / `ac.md` | 확정된 요구사항 (핵심 모드는 ac.md) |
| `design.md` | 설계서 + Testability 평가 섹션 |
| `codemap.md` | 관련 파일 경로와 역할 (누적, 최대 25개) |
| `trust-ledger.md` | 감사 결과 + **위험 수용 이력** |
| `state.md` | 파이프라인 진행 상태 (재개용) |
| `diff.txt` | 변경사항 (에이전트 전달용) |

`trust-ledger.md`의 위험 수용 기록이 중요하다. 게이트를 위험 수용으로 통과시킨 항목은 전부 남는다 — 테스트 없이 넘어간 AC, 수용한 신규 경고, TDD 미이행 완료 실행 등. PR 본문에도 요약이 들어간다. **우회는 가능하되 흔적 없이는 불가능**하다는 것이 설계 의도다.

---

## 7. 실전 시나리오 — 유저 등록·조회, 포인트 충전

강의 과제를 `gx-tdd`로 수행하는 흐름이다.

### 7.1 호출

```
/gx-tdd 유저 등록·조회와 포인트 충전 기능을 TDD로 구현해줘
```

진행 방식(전체/핵심)과 모델 프로파일(표준/에코)을 묻는다. 신규 기능이므로 전체 과정을 선택한다.

### 7.2 requirements — AC를 G-W-T로

product-owner가 PRD를 쓰고, G-W-T 게이트가 형식을 검증한다.

```
AC-1: 신규 유저 등록 시 초기 포인트는 0이다
  Given: 등록되지 않은 이메일 "alen@example.com"이 있다
  When:  해당 이메일로 유저를 등록한다
  Then:  유저가 저장되고 point 값이 0이다

AC-2: 포인트 충전 시 잔액이 증가한다
  Given: 포인트 1,000을 보유한 유저가 있다
  When:  5,000 포인트를 충전한다
  Then:  잔액이 6,000이 된다

AC-3: 1회 충전 한도를 초과하면 충전이 거부된다
  Given: 1회 충전 한도가 100,000이고 잔액이 0인 유저가 있다
  When:  100,001 포인트 충전을 시도한다
  Then:  ChargeLimitExceededException이 발생하고 잔액은 0으로 유지된다

AC-4: 존재하지 않는 유저 조회 시 404를 반환한다
  Given: id 999인 유저가 없다
  When:  GET /users/999를 호출한다
  Then:  404 응답이 반환되고 body의 code가 "USER_NOT_FOUND"이다
```

"포인트가 적절히 충전된다" 같은 AC가 하나라도 있으면 게이트에서 막히고 재작성된다.

### 7.3 design — testability 평가

architect가 설계하고 test-architect가 점수를 매긴다.

```
## Testability 평가

### 컴포넌트별 테스트 전략
#### User (도메인)
- 단위 테스트: 순수 JVM. charge() 규칙을 직접 검증
- 모의 대상: 없음
- 격리 전략: 불필요 (의존성 없음)
- AC 매핑: AC-1, AC-2, AC-3

#### UserService (애플리케이션)
- 단위 테스트: UserRepository를 Fake(InMemory)로 주입
- 통합 테스트: @SpringBootTest + H2로 저장 반영 확인
- 격리 전략: 생성자 주입
- AC 매핑: AC-1, AC-2, AC-4

#### UserController
- E2E: MockMvc로 HTTP 상태·body 검증
- AC 매핑: AC-4

### Testability Score: 8/10
### 판정: TESTABILITY PASS
```

만약 `UserService`가 `UserJpaRepository()`를 직접 생성하는 설계였다면 점수가 7 미만으로 떨어지고, "DI로 UserRepository 추출 권고"와 함께 architect에게 재설계가 돌아간다. 4.3절의 나쁜 구조가 여기서 걸러진다.

### 7.4 implement — RGR 사이클

태스크 분해:

| # | AC | 컴포넌트 | RED | GREEN | REFACTOR |
|---|-----|---------|-----|-------|----------|
| T1 | AC-1 | User | `UserTest.shouldStartWithZeroPoint` | User 생성자 + point 필드 | — |
| T2 | AC-2 | User | `UserTest.shouldIncreaseBalanceOnCharge` | `User.charge()` | — |
| T3 | AC-3 | User | `UserTest.shouldRejectChargeOverLimit` | 한도 검증 분기 | 매직 넘버 상수화 |
| T4 | AC-1,2 | UserService | `UserServiceTest` (InMemory Fake) | register / charge 위임 | 중복 조회 로직 추출 |
| T5 | AC-4 | UserController | `UserControllerE2ETest` | 예외 → 404 매핑 | — |

T3 사이클을 예로 보면:

```
RED    red-writer가 UserTest.shouldRejectChargeOverLimit 작성
       (User 구현을 보지 않고 AC-3과 설계서 인터페이스만 참조)
       → 실행 → ChargeLimitExceededException 미존재로 컴파일 실패 확인
       → 테스트 파일 해시 기록

GREEN  green-coder가 예외 클래스 + 한도 분기 추가 (그 이상 없음)
       → 대상 테스트 통과, 전체 회귀 0건
       → 테스트 파일 해시 재확인 (변조 없음)

REFACTOR refactor-coder가 100_000 리터럴을 MAX_CHARGE_PER_REQUEST 상수로 추출
       → 테스트 재실행 → 통과 유지
       → 테스트 수 감소 없음 확인
```

여기서 green-coder가 "이왕 하는 김에" 일일 누적 한도까지 구현하려 하면 과잉 구현으로 감지되어 다음 RED로 미뤄진다. AC-3에는 1회 한도만 있기 때문이다.

### 7.5 review → complete

- spec-reviewer가 AC-1~4 충족 여부만 판정 (코드 품질은 보지 않음)
- 통과 후 quality-reviewer(품질) + security-auditor(보안)가 병렬 실행
- verify 게이트가 `./gradlew test`와 `./gradlew build`를 새로 실행해 0 failures 확인
- product-owner 인수 검증 → 커밋 → PR

verify에서 실패가 나오면 자동 수정하지 않는다. 실패 항목을 새 AC로 정의해 **RGR 사이클로 되돌아간다.** 버그 수정도 RED가 먼저다.

---

## 8. 합리화 격파 표

TDD를 건너뛰고 싶을 때 떠오르는 문장들과 반박이다. 원문: `.claude/skills/gx-tdd/references/tdd-iron-law.md`

### 단순함 합리화

| 변명 | 반박 |
|------|------|
| "이건 너무 간단해서 테스트가 필요 없다" | 단순한 코드도 깨진다. 테스트 30초면 끝난다 |
| "한 줄짜리 함수에 테스트는 과하다" | 한 줄짜리에서 가장 많은 버그가 나온다 |
| "getter/setter는 테스트 불필요" | 보통은 맞다. 단, AC에 포함되면 테스트한다 |

### 사후 테스트 합리화

| 변명 | 반박 |
|------|------|
| "이미 수동으로 테스트했다" | 수동은 재실행 불가. 자동 테스트만 신뢰 가능 |
| "테스트를 나중에 써도 같은 효과다" | 사후는 "이게 뭐 하는 코드?", 사전은 "이게 뭘 해야 함?" |
| "테스트를 고치면 금방 통과한다" | 테스트 수정은 GREEN의 실패 모드다. 코드를 고쳐라 |

### 매몰비용 합리화

| 변명 | 반박 |
|------|------|
| "몇 시간 짠 코드를 버리는 건 낭비다" | 매몰비용 오류. 검증 안 된 코드 유지가 더 큰 부채 |
| "참조용으로만 남겨두겠다" | 보면 적응한다. 그건 사후 테스트다 |
| "비슷한 코드를 다시 쓰는 건 비효율" | 두 번째 작성은 항상 더 빠르고 좋다 |

### 실용주의 합리화

| 변명 | 반박 |
|------|------|
| "TDD는 교조적, 실용주의자는 유연하게" | TDD가 실용적이다. 디버깅 시간이 더 짧다 |
| "정신만 따르면 되지 문자는 무시해도 된다" | 문자를 무시하면 정신도 무시된다 |
| "이번 한 번만 예외" | 첫 예외가 규칙이 된다 |
| "일정이 급하다" | 사후 디버깅이 더 오래 걸린다 |

### 확신 합리화

| 변명 | 반박 |
|------|------|
| "이 케이스는 명백히 동작한다" | "should work"는 검증이 아니다. 실행 증거가 필요하다 |
| "리뷰어가 어차피 잡아낼 것" | 리뷰어에게 부담 전가. 본인이 먼저 검증 |
| "다른 곳에 비슷한 테스트가 있다" | "비슷"은 검증이 아니다 |

### 환경·시간 합리화

| 변명 | 반박 |
|------|------|
| "기존 코드에 테스트가 없다" | 새 코드에는 추가한다 |
| "테스트 환경이 복잡하다" | 환경 셋업도 TDD의 일부. 한 번 만들면 재사용된다 |
| "테스트 작성이 코드보다 어렵다" | 테스트가 어려우면 설계가 어려운 것이다. 인터페이스를 단순화하라 |
| "TDD는 시간이 두 배 든다" | 디버깅 시간이 절반 이하로 줄어 총 시간은 단축된다 |
| "지금은 빠르게, 나중에 리팩토링" | 사후 리팩토링은 거의 일어나지 않는다 |

### 즉시 STOP해야 하는 표현

아래 표현을 쓰고 있다면 검증 없이 완료를 주장하는 중이다.

```
"테스트가 통과할 것 같다"   "should work"   "looks good"   "probably passes"
"완료!"   "Done!"   "Perfect!"   (실행 증거가 없는 경우)
```

---

## 9. 체크리스트

### 요구사항 단계

- [ ] 모든 AC가 Given-When-Then 세 절을 갖추었는가
- [ ] Then에 자동 검증 가능한 구체값이 있는가
- [ ] "적절히", "올바르게" 같은 표현이 없는가

### 설계 단계

- [ ] 외부 의존성이 인터페이스로 분리되고 생성자 주입되는가
- [ ] 도메인 규칙이 서비스가 아닌 도메인 객체에 있는가
- [ ] 각 컴포넌트의 테스트 전략(단위/통합/모의 대상)이 명시됐는가
- [ ] testability score가 7 이상인가

### 구현 단계

- [ ] RED에서 실패를 눈으로 확인했는가
- [ ] GREEN에서 테스트 파일을 수정하지 않았는가
- [ ] GREEN 구현에 테스트가 요구하지 않은 것이 없는가
- [ ] REFACTOR 후 전체 테스트가 통과하는가
- [ ] 테스트가 모의가 아닌 실제 동작을 검증하는가
- [ ] 프로덕션 클래스에 테스트 전용 메서드가 없는가

### 완료 단계

- [ ] 테스트를 방금 새로 실행했는가
- [ ] 실패 0건인가
- [ ] 실행된 테스트가 1건 이상인가
- [ ] 빌드가 성공하는가
- [ ] 신규 경고가 없는가
- [ ] 위험 수용 항목이 있다면 trust-ledger에 기록됐는가

