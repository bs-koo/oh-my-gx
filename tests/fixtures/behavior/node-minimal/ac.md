## 배경

1회 충전 금액에 한도(100,000원)를 둔다.

## 요구사항 (AC)

AC-1: 1회 충전 한도 검증
  시나리오 1
    Given: 1회 충전 한도가 100,000원이다
    When: checkLimit(150000)을 호출한다
    Then: { ok: false, reason: 'limit' }가 반환된다
  시나리오 2
    Given: 1회 충전 한도가 100,000원이다
    When: checkLimit(100001)을 호출한다
    Then: { ok: false, reason: 'limit' }가 반환된다
