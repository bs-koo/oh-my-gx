# RED report — T1 (AC-1)

## 테스트 파일
test/limit-max.test.js (케이스 2건)

## 실패 확인 명령
node --test test/limit-max.test.js

## 케이스별 실패 메시지
- '1회 한도를 넘는 금액은 limit 사유로 거부한다': AssertionError — Expected { ok: false, reason: 'limit' }, actual { ok: true }
- '한도보다 1원 많은 금액도 limit 사유로 거부한다': AssertionError — Expected { ok: false, reason: 'limit' }, actual { ok: true }

## 참조한 파일
- ac.md
- test/limit.test.js
