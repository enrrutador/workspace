/** Unit tests for worker/lib.js — run with: node worker/test.js */
import assert from "node:assert/strict";
import {
  isClubId,
  isWalletId,
  sanitizeFanName,
  sanitizeShout,
  sanitizeChatText,
  validatePushAmount,
  validateCreditAmount,
  applyPush,
  rankBoard,
  neededToPass,
  boardStats,
  checkRateLimit,
} from "./lib.js";

let n = 0;
const t = (name, fn) => { fn(); n++; console.log(`ok ${n} - ${name}`); };

// --- isClubId ---------------------------------------------------------------
t("accepts kebab-case club ids", () => {
  for (const id of ["river-plate", "psg", "inter-miami", "fc-porto"]) {
    assert.equal(isClubId(id), true, id);
  }
});
t("rejects bad club ids", () => {
  for (const id of ["River Plate", "", "a_b", "-x", "x-", 42, null]) {
    assert.equal(isClubId(id), false, String(id));
  }
});

// --- isWalletId ---------------------------------------------------------------
t("accepts uuid wallet tokens", () => {
  assert.equal(isWalletId("123e4567-e89b-12d3-a456-426614174000"), true);
  assert.equal(isWalletId("123E4567-E89B-12D3-A456-426614174000"), true);
});
t("rejects bad wallet tokens", () => {
  for (const id of ["", "abc", "123e4567e89b12d3a456426614174000", 42, null]) {
    assert.equal(isWalletId(id), false, String(id));
  }
});

// --- validateCreditAmount -------------------------------------------------------
t("credit: USD 1 buys 3 messages, USD 10 buys 30", () => {
  assert.deepEqual(validateCreditAmount(1), { ok: true, amount: 1, messages: 3 });
  assert.deepEqual(validateCreditAmount(10), { ok: true, amount: 10, messages: 30 });
});
t("credit: rejects below minimum, absurd amounts and non-numbers", () => {
  assert.equal(validateCreditAmount(0.5).error, "AMOUNT_TOO_LOW");
  assert.equal(validateCreditAmount(2000).error, "AMOUNT_TOO_HIGH");
  assert.equal(validateCreditAmount("lots").error, "AMOUNT_INVALID");
});

// --- sanitizeFanName ----------------------------------------------------------
t("fan name: trims, strips html chars, collapses spaces", () => {
  assert.equal(sanitizeFanName("  El <b>Diez</b>  "), "El bDiez/b");
  assert.equal(sanitizeFanName("Juan   Perez"), "Juan Perez");
});
t("fan name: caps at 40 chars, non-string is empty", () => {
  assert.equal(sanitizeFanName("x".repeat(60)).length, 40);
  assert.equal(sanitizeFanName(42), "");
  assert.equal(sanitizeFanName(undefined), "");
});

// --- validatePushAmount --------------------------------------------------------
t("rejects below minimum", () => {
  const r = validatePushAmount(0.99);
  assert.equal(r.ok, false); assert.equal(r.error, "AMOUNT_TOO_LOW"); assert.equal(r.minAllowed, 1);
});
t("accepts exactly minimum", () => {
  assert.deepEqual(validatePushAmount(1), { ok: true, amount: 1 });
});
t("rounds to cents", () => {
  assert.deepEqual(validatePushAmount(5.678), { ok: true, amount: 5.68 });
});
t("rejects absurd amounts and non-numbers", () => {
  assert.equal(validatePushAmount(200000).error, "AMOUNT_TOO_HIGH");
  assert.equal(validatePushAmount("lots").error, "AMOUNT_INVALID");
});

// --- applyPush (pooling) -------------------------------------------------------
t("first push creates the club entry", () => {
  const totals = applyPush({}, { club: "river-plate", league: "arg", amount: 5, at: 100 });
  assert.deepEqual(totals["river-plate"], { league: "arg", total: 5, pushes: 1, firstAt: 100, lastAt: 100 });
});
t("second push pools into the total, keeps firstAt", () => {
  let totals = applyPush({}, { club: "river-plate", league: "arg", amount: 5, at: 100 });
  totals = applyPush(totals, { club: "river-plate", league: "arg", amount: 3, at: 200 });
  assert.equal(totals["river-plate"].total, 8);
  assert.equal(totals["river-plate"].pushes, 2);
  assert.equal(totals["river-plate"].firstAt, 100);
  assert.equal(totals["river-plate"].lastAt, 200);
});
t("applyPush does not mutate the input", () => {
  const before = {};
  applyPush(before, { club: "boca-juniors", league: "arg", amount: 2, at: 50 });
  assert.deepEqual(before, {});
});

// --- rankBoard ------------------------------------------------------------------
t("ranks by total desc, ties by earliest firstAt", () => {
  const ranked = rankBoard({
    "boca-juniors": { league: "arg", total: 10, pushes: 3, firstAt: 200, lastAt: 300 },
    "river-plate": { league: "arg", total: 50, pushes: 9, firstAt: 300, lastAt: 400 },
    "racing-club": { league: "arg", total: 10, pushes: 2, firstAt: 100, lastAt: 250 },
  });
  assert.deepEqual(ranked.map((r) => r.club), ["river-plate", "racing-club", "boca-juniors"]);
  assert.deepEqual(ranked.map((r) => r.position), [1, 2, 3]);
});

// --- neededToPass ------------------------------------------------------------------
t("needed to pass = rival total + $1 step − own total", () => {
  const ranked = rankBoard({
    "river-plate": { league: "arg", total: 50, pushes: 9, firstAt: 100, lastAt: 100 },
    "boca-juniors": { league: "arg", total: 30, pushes: 4, firstAt: 200, lastAt: 200 },
  });
  assert.equal(neededToPass(ranked, "boca-juniors"), 21);
  assert.equal(neededToPass(ranked, "river-plate"), null);
  assert.equal(neededToPass(ranked, "racing-club"), null);
});

// --- boardStats ------------------------------------------------------------------
t("stats sum pool, pushes and clubs", () => {
  const ranked = rankBoard({
    "river-plate": { league: "arg", total: 50, pushes: 9, firstAt: 100, lastAt: 100 },
    "boca-juniors": { league: "arg", total: 30, pushes: 4, firstAt: 200, lastAt: 200 },
  });
  assert.deepEqual(boardStats(ranked), { totalPushed: 80, totalPushes: 13, clubsRanked: 2 });
});

// --- checkRateLimit ---------------------------------------------------------------
t("allows up to max then blocks", () => {
  let ts = [];
  for (let i = 0; i < 10; i++) {
    const r = checkRateLimit(ts, 1000 + i);
    assert.equal(r.allowed, true); ts = r.timestamps;
  }
  assert.equal(checkRateLimit(ts, 2000).allowed, false);
});
t("window slides: old attempts expire", () => {
  const hour = 3600 * 1000;
  const old = Array.from({ length: 10 }, (_, i) => i * 1000);
  assert.equal(checkRateLimit(old, hour + 5000).allowed, true);
});

// --- sanitizeShout / sanitizeChatText -----------------------------------------
t("shout: sanitized and capped at 140", () => {
  assert.equal(sanitizeShout("  ¡Vamos <i>River</i>!  "), "¡Vamos iRiver/i!");
  assert.equal(sanitizeShout("x".repeat(200)).length, 140);
  assert.equal(sanitizeShout(7), "");
});
t("chat text: sanitized and capped at 200", () => {
  assert.equal(sanitizeChatText("hola   todos"), "hola todos");
  assert.equal(sanitizeChatText("x".repeat(300)).length, 200);
});

// --- applyPush shout -------------------------------------------------------------
t("push with message sets the club shout; push without keeps it", () => {
  let totals = applyPush({}, { club: "river-plate", league: "arg", amount: 5, at: 100, shout: { text: "¡Vamos River!", fan: "El Diez", at: 100 } });
  assert.deepEqual(totals["river-plate"].shout, { text: "¡Vamos River!", fan: "El Diez", at: 100 });
  totals = applyPush(totals, { club: "river-plate", league: "arg", amount: 3, at: 200 });
  assert.equal(totals["river-plate"].shout.text, "¡Vamos River!");
  totals = applyPush(totals, { club: "river-plate", league: "arg", amount: 3, at: 300, shout: { text: "Nuevo mensaje", fan: "Ana", at: 300 } });
  assert.equal(totals["river-plate"].shout.text, "Nuevo mensaje");
  const ranked = rankBoard(totals);
  assert.equal(ranked[0].shout.text, "Nuevo mensaje");
});

// --- checkRateLimit custom params -------------------------------------------------
t("rate limit honors custom max/window (chat)", () => {
  let ts = [];
  for (let i = 0; i < 20; i++) {
    const r = checkRateLimit(ts, 1000 + i, 20, 600000);
    assert.equal(r.allowed, true); ts = r.timestamps;
  }
  assert.equal(checkRateLimit(ts, 2000, 20, 600000).allowed, false);
});

console.log(`\n${n} tests passed.`);
