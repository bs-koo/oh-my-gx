'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { checkLimit } = require('../src/limit');

test('0 이하 금액은 invalid로 거부한다', () => {
  assert.deepEqual(checkLimit(0), { ok: false, reason: 'invalid' });
});

test('정수가 아닌 금액은 invalid로 거부한다', () => {
  assert.deepEqual(checkLimit(10.5), { ok: false, reason: 'invalid' });
});

test('한도 이내 금액은 허용한다', () => {
  assert.deepEqual(checkLimit(50000), { ok: true });
});
