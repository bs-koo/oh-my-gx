'use strict';

const SINGLE_CHARGE_LIMIT = 100000;

function checkLimit(amount) {
  if (!Number.isInteger(amount) || amount <= 0) {
    return { ok: false, reason: 'invalid' };
  }
  return { ok: true };
}

module.exports = { checkLimit, SINGLE_CHARGE_LIMIT };
