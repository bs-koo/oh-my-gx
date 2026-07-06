# Testing Anti-Patterns 카탈로그

**참조 시점**: 테스트를 작성/변경할 때, 모의(mock)를 추가할 때, 프로덕션 클래스에 테스트 전용 메서드를 추가하고 싶을 때.

테스트는 모의가 아니라 **실제 동작**을 검증해야 한다. 모의는 격리 수단이지 검증 대상이 아니다.

> 출처: superpowers 플러그인 `test-driven-development/testing-anti-patterns.md`의 한국어 이식판. gx-tdd 파이프라인 특화 주의(§0)를 추가했다.

---

## 3대 Iron Law

```
1. NEVER test mock behavior
   (모의의 동작을 테스트하지 마라)

2. NEVER add test-only methods to production classes
   (프로덕션 클래스에 테스트 전용 메서드를 넣지 마라)

3. NEVER mock without understanding dependencies
   (의존성을 이해하지 못한 채 모킹하지 마라)
```

---

## §0. gx-tdd 특화 주의 — red-writer 격리와 모의

red-writer는 기존 프로덕션 코드를 보지 않으므로, 모의 구조의 근거는 **설계서 testability 섹션의 인터페이스 정의가 유일**하다.

- 설계서에 없는 필드/메서드를 추측해서 모킹하지 마라.
- 인터페이스 정의가 모의를 구성하기에 부족하면, 테스트를 억지로 만들지 말고 결과 보고에 **"설계서 인터페이스 불충분"**으로 명시하라. 오케스트레이터가 설계 보강(phase-design 재실행) 여부를 판단한다.

---

## Anti-Pattern 1: 모의 동작 테스트

**위반:**
```java
// ❌ 모의가 존재하는지를 검증
@Test
void 알림을_전송한다() {
    NotificationSender mock = mock(NotificationSender.class);
    when(mock.send(any())).thenReturn(true);

    assertTrue(mock.send(new Notice()));  // 모의를 검증할 뿐, 코드는 검증 안 됨
}
```

**왜 잘못인가:**
- 모의가 동작하는지를 확인할 뿐, 실제 컴포넌트가 동작하는지는 알 수 없다.
- 모의가 있으면 통과, 없으면 실패 — 실제 동작에 대해 아무것도 말해주지 않는다.

**수정:**
```java
// ✅ 실제 대상의 동작을 검증 (모의는 격리에만 사용)
@Test
void 알림_전송_실패_시_재시도_큐에_적재된다() {
    NotificationSender failingSender = mock(NotificationSender.class);
    when(failingSender.send(any())).thenReturn(false);
    NoticeService service = new NoticeService(failingSender, retryQueue);

    service.notify(new Notice());

    assertEquals(1, retryQueue.size());  // 검증 대상은 service의 동작
}
```

**게이트 함수:**
```
모의 요소에 assertion을 걸기 전에:
  자문: "실제 컴포넌트의 동작을 검증하는가, 모의의 존재를 검증하는가?"
  모의의 존재를 검증한다면 → STOP. assertion을 삭제하거나 모의를 해제하라.
```

---

## Anti-Pattern 2: 프로덕션의 테스트 전용 메서드

**위반:**
```java
// ❌ destroy()는 테스트에서만 호출됨
public class Session {
    public void destroy() {  // 프로덕션 API처럼 보이지만 테스트 전용!
        workspaceManager.destroyWorkspace(this.id);
    }
}
// 테스트에서: @AfterEach void tearDown() { session.destroy(); }
```

**왜 잘못인가:**
- 프로덕션 클래스가 테스트 전용 코드로 오염된다.
- 프로덕션에서 실수로 호출되면 위험하다.
- YAGNI와 책임 분리 위반이다.

**수정:**
```java
// ✅ 테스트 정리는 테스트 유틸리티가 담당 (Session에는 destroy 없음)
// src/test/java/testutil/SessionCleanup.java
public class SessionCleanup {
    public static void cleanup(Session session, WorkspaceManager wm) {
        wm.destroyWorkspace(session.getWorkspaceId());
    }
}
```

**게이트 함수:**
```
프로덕션 클래스에 메서드를 추가하기 전에:
  자문 1: "이 메서드는 테스트에서만 쓰이는가?" → 예라면 STOP. 테스트 유틸리티로 옮겨라.
  자문 2: "이 클래스가 이 자원의 생명주기를 소유하는가?" → 아니라면 STOP. 잘못된 클래스다.
```

---

## Anti-Pattern 3: 이해 없는 모킹

**위반:**
```typescript
// ❌ 모의가 테스트가 의존하는 부수효과를 차단
test('중복 서버 등록을 감지한다', async () => {
  // discoverAndCacheTools가 config 기록을 담당하는데 통째로 모킹해버림!
  vi.mock('ToolCatalog', () => ({
    discoverAndCacheTools: vi.fn().mockResolvedValue(undefined)
  }));

  await addServer(config);
  await addServer(config);  // 중복 예외가 나야 하지만 config가 안 쓰여서 안 남
});
```

**왜 잘못인가:**
- 모킹한 메서드에 테스트가 의존하는 부수효과(config 기록)가 있었다.
- "안전하게 다 모킹"이 실제 동작을 깨뜨린다.
- 테스트가 엉뚱한 이유로 통과하거나 원인 불명으로 실패한다.

**수정:**
```typescript
// ✅ 올바른 레벨에서 모킹 (느린 부분만 모킹, 필요한 동작은 보존)
test('중복 서버 등록을 감지한다', async () => {
  vi.mock('MCPServerManager');  // 느린 서버 기동만 모킹

  await addServer(config);   // config 기록됨
  await expect(addServer(config)).rejects.toThrow();  // 중복 감지 ✓
});
```

**게이트 함수:**
```
메서드를 모킹하기 전에:
  1. "실제 메서드의 부수효과는 무엇인가?"
  2. "이 테스트가 그 부수효과에 의존하는가?"
  3. 의존한다면 → 더 낮은 레벨(실제 느린/외부 연산)에서 모킹하거나, 필요한 동작을 보존하는 test double을 사용하라.
  4. 무엇에 의존하는지 불확실하면 → 실제 구현으로 먼저 실행해 관찰한 뒤 최소로 모킹하라.
     (gx-tdd의 red-writer는 실제 구현을 볼 수 없으므로 §0을 따른다 — 설계서 인터페이스가 근거, 부족하면 보고)

Red Flags: "안전하게 모킹해두자" / "느릴 것 같으니 모킹" / 의존 체인 이해 없이 모킹
```

---

## Anti-Pattern 4: 불완전한 모의

**위반:**
```java
// ❌ 당장 필요한 필드만 가진 부분 모의
Map<String, Object> mockResponse = Map.of(
    "status", "success",
    "data", Map.of("userId", "123", "name", "Alice")
    // 누락: 하위 코드가 사용하는 metadata.requestId
);
```

**왜 잘못인가:**
- 부분 모의는 구조적 가정을 숨긴다 — 아는 필드만 모킹하게 된다.
- 하위 코드가 누락 필드에 의존하면 조용히 실패한다.
- 테스트는 통과하는데 통합에서 깨진다. 거짓 확신이다.

**Iron Rule**: 모의는 **실재하는 완전한 데이터 구조**를 미러링하라. 당장 테스트가 쓰는 필드만이 아니라.

**게이트 함수:**
```
모의 응답을 만들기 전에:
  1. 실제 API 응답에 어떤 필드가 있는지 확인하라 (문서/설계서 testability 섹션의 정의).
  2. 하위에서 소비될 수 있는 필드를 전부 포함하라.
  3. 모의가 실제 응답 스키마와 완전히 일치하는지 검증하라.
  불확실하면: 문서화된 필드를 전부 포함하라.
```

---

## Anti-Pattern 5: 사후 테스트

**위반:**
```
✅ 구현 완료
❌ 테스트 없음
"테스트할 준비 완료"
```

**왜 잘못인가:**
- 테스트는 구현의 일부이지 선택적 후속 작업이 아니다.
- TDD(RED 선행)라면 이 상태가 존재할 수 없다.
- 테스트 없이 완료를 주장할 수 없다 (Iron Law 3).

**수정**: RGR 사이클로 복귀 — 실패 테스트 작성 → 통과 구현 → 정리 → 그 다음에 완료 주장.

---

## 모의가 과도해지는 경고 신호

- 모의 셋업이 테스트 로직보다 길다
- 테스트를 통과시키려고 전부 모킹하고 있다
- 모의에 실제 컴포넌트가 가진 메서드가 빠져 있다
- 모의를 바꾸면 테스트가 깨진다

→ 이럴 때는 복잡한 모의보다 **실제 컴포넌트를 쓰는 통합 테스트**가 더 단순한 경우가 많다. "여기서 정말 모의가 필요한가?"를 자문하라.

---

## Red Flags

- assertion이 `*-mock` 류 테스트 ID를 검사한다
- 테스트 파일에서만 호출되는 프로덕션 메서드가 있다
- 모의 셋업이 테스트의 50%를 넘는다
- 모의를 제거하면 테스트가 깨진다
- 왜 모의가 필요한지 설명할 수 없다
- "안전하게 모킹해두자"

---

## 결론

**모의는 격리 도구이지 검증 대상이 아니다.**

TDD를 지키면 이 anti-pattern들은 대부분 예방된다: 테스트를 먼저 쓰면 무엇을 검증하는지 생각하게 되고, 실패를 목격하면 테스트가 모의가 아닌 실제 동작을 검증함이 증명되고, 최소 구현이면 테스트 전용 메서드가 끼어들 틈이 없다.

**모의의 동작을 테스트하고 있다면 이미 TDD를 위반한 것이다** — 실제 코드로 실패를 목격하기 전에 모의를 넣었다는 뜻이다.
