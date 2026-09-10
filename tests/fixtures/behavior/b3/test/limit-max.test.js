'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { checkLimit } = require('../src/limit');

test('1회 한도를 넘는 금액은 limit 사유로 거부한다', () => {
  assert.deepEqual(checkLimit(150000), { ok: false, reason: 'limit' });
});

test('한도보다 1원 많은 금액도 limit 사유로 거부한다', () => {
  assert.deepEqual(checkLimit(100001), { ok: false, reason: 'limit' });
});
