'use strict';

const SINGLE_CHARGE_LIMIT = 100000;

function checkLimit(amount) {
  if (!Number.isInteger(amount) || amount <= 0) {
    return { ok: false, reason: 'invalid' };
  }
  if (amount > SINGLE_CHARGE_LIMIT) {
    return { ok: false, reason: 'limit' };
  }
  return { ok: true };
}

module.exports = { checkLimit, SINGLE_CHARGE_LIMIT };
