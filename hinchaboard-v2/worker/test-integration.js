/**
 * Integration test for worker/index.js with an in-memory KV mock.
 * Run with: node worker/test-integration.js
 */
import assert from "node:assert/strict";
import handler from "./index.js";

function makeEnv() {
  const store = new Map();
  return {
    PAYMENT_PROVIDER: "stub",
    ADMIN_SECRET: "test-secret",
    RANKING_KV: {
      async get(k, type) {
        if (!store.has(k)) return null;
        const v = store.get(k);
        return type === "json" ? JSON.parse(v) : v;
      },
      async put(k, v, opts = {}) {
        store.set(k, typeof v === "string" ? v : JSON.stringify(v));
        if (opts.expirationTtl) { /* mock ignores TTL */ }
      },
      async delete(k) { store.delete(k); },
    },
  };
}

const req = (method, path, body, headers = {}) =>
  new Request(`https://x.test${path}`, {
    method,
    headers: { "content-type": "application/json", ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });

const confirm = (env, intentId) =>
  handler.fetch(req("POST", "/api/admin/confirm", { intentId }, { "x-admin-secret": "test-secret" }), env);
const push = async (env, payload) => {
  const r = await handler.fetch(req("POST", "/api/pushes", payload), env);
  return { status: r.status, data: await r.json() };
};
const board = async (env, scope = "global") => {
  const d = await (await handler.fetch(req("GET", `/api/board?scope=${scope}`), env)).json();
  return d;
};
const credit = async (env, wallet, amount) => {
  const r = await handler.fetch(req("POST", "/api/chat/credits", { wallet, amount }), env);
  return { status: r.status, data: await r.json() };
};
const chat = async (env, payload) => {
  const r = await handler.fetch(req("POST", "/api/chat", payload), env);
  return { status: r.status, data: await r.json() };
};

let n = 0;
const t = async (name, fn) => { await fn(); n++; console.log(`ok ${n} - ${name}`); };

const env = makeEnv();

// 1. Empty board
await t("empty global board", async () => {
  const d = await board(env);
  assert.equal(d.ok, true);
  assert.equal(d.scope, "global");
  assert.deepEqual(d.board, []);
  assert.equal(d.stats.totalPushed, 0);
  assert.equal(d.rules.minPushUsd, 1);
});

// 2. Unknown club rejected
await t("rejects unknown club", async () => {
  const { status, data } = await push(env, { scope: "global", club: "not-a-club", amount: 10 });
  assert.equal(status, 400);
  assert.equal(data.error, "CLUB_UNKNOWN");
});

// 3. Below-minimum push rejected
await t("rejects below-minimum push", async () => {
  const { status, data } = await push(env, { scope: "global", club: "river-plate", amount: 0.5 });
  assert.equal(status, 400);
  assert.equal(data.error, "AMOUNT_TOO_LOW");
});

// 4. Unknown scope rejected
await t("rejects unknown scope", async () => {
  const r = await handler.fetch(req("GET", "/api/board?scope=atlantis"), env);
  assert.equal(r.status, 400);
  assert.equal((await r.json()).error, "UNKNOWN_SCOPE");
});

// 5. Country push creates intent with its scope
let argIntent;
await t("creates country push intent", async () => {
  const { status, data } = await push(env, { scope: "arg", club: "river-plate", amount: 25, fan: "El Diez" });
  assert.equal(status, 201);
  assert.equal(data.ok, true);
  argIntent = data.intentId;
  assert.match(data.payUrl, /\/pay\.html\?intent=/);
});

// 6. Intent status readable
await t("intent status pending with scope", async () => {
  const d = await (await handler.fetch(req("GET", `/api/intents/${argIntent}`), env)).json();
  assert.equal(d.intent.status, "pending_payment");
  assert.equal(d.intent.club, "river-plate");
  assert.equal(d.intent.league, "arg");
  assert.equal(d.intent.scope, "arg");
  assert.equal(d.intent.amount, 25);
});

// 7. Admin confirm requires secret
await t("admin confirm needs secret", async () => {
  const r = await handler.fetch(req("POST", "/api/admin/confirm", { intentId: argIntent }), env);
  assert.equal(r.status, 401);
});

// 8. Country push only moves the country board
await t("country push does not touch the global board", async () => {
  const d = await (await confirm(env, argIntent)).json();
  assert.equal(d.ok, true);
  assert.equal(d.scope, "arg");
  assert.equal(d.board[0].club, "river-plate");
  assert.equal(d.board[0].total, 25);
  const global = await board(env);
  assert.deepEqual(global.board, []);
});

// 9. Global push only moves the global board
let globalIntent;
await t("global push does not touch the country board", async () => {
  const b = await push(env, { scope: "global", club: "real-madrid", amount: 40, fan: "VikingoRM" });
  assert.equal(b.status, 201);
  globalIntent = b.data.intentId;
  const d = await (await confirm(env, globalIntent)).json();
  assert.equal(d.scope, "global");
  assert.equal(d.board[0].club, "real-madrid");
  assert.equal(d.board[0].total, 40);
  const esp = await board(env, "esp");
  assert.deepEqual(esp.board, []);
  const arg = await board(env, "arg");
  assert.equal(arg.board.length, 1);
  assert.equal(arg.board[0].total, 25);
});

// 10. Same club, two independent counters
await t("the same club keeps independent country and global totals", async () => {
  const b = await push(env, { scope: "global", club: "river-plate", amount: 20 });
  await confirm(env, b.data.intentId);
  const global = await board(env);
  assert.equal(global.board.length, 2);
  assert.equal(global.board[1].club, "river-plate");
  assert.equal(global.board[1].total, 20);
  const arg = await board(env, "arg");
  assert.equal(arg.board[0].club, "river-plate");
  assert.equal(arg.board[0].total, 25);
});

// 11. A club cannot be pushed into another country's ranking
await t("rejects country scope mismatch", async () => {
  const { status, data } = await push(env, { scope: "arg", club: "real-madrid", amount: 10 });
  assert.equal(status, 400);
  assert.equal(data.error, "SCOPE_MISMATCH");
});

// 12. Country board only contains clubs from that country
await t("country board filters by country", async () => {
  const b = await push(env, { scope: "arg", club: "boca-juniors", amount: 40 });
  await confirm(env, b.data.intentId);
  const arg = await board(env, "arg");
  assert.equal(arg.board.length, 2);
  assert.deepEqual(arg.board.map((r) => r.club), ["boca-juniors", "river-plate"]);
  assert.deepEqual(arg.board.map((r) => r.position), [1, 2]);
  assert.equal(arg.stats.totalPushed, 65);
  assert.equal(arg.activity[0].scope, "arg");
});

// 13. Alternative query shape: ?scope=country&country=arg
await t("supports scope=country&country=<id>", async () => {
  const r = await handler.fetch(req("GET", "/api/board?scope=country&country=arg"), env);
  const d = await r.json();
  assert.equal(r.status, 200);
  assert.equal(d.scope, "arg");
  assert.equal(d.board.length, 2);
  const missing = await handler.fetch(req("GET", "/api/board?scope=country"), env);
  assert.equal(missing.status, 400);
});

// 14. Activity feed keeps scope and message
await t("activity feed keeps scope and message", async () => {
  const d = await board(env);
  assert.ok(d.activity.length >= 4);
  assert.ok(d.activity.every((a) => a.scope === "global" || a.scope === "arg"));
});

// 15. Webhook stubs return 501
await t("webhooks are stubs", async () => {
  for (const p of ["polar", "lemonsqueezy"]) {
    const r = await handler.fetch(req("POST", `/api/webhooks/${p}`, {}), env);
    assert.equal(r.status, 501);
  }
});

// 16. Rate limit kicks in after 10 attempts (fresh env, same IP)
await t("rate limit", async () => {
  const env2 = makeEnv();
  let last;
  for (let i = 0; i < 11; i++) {
    last = await handler.fetch(
      req("POST", "/api/pushes", { scope: "global", club: "river-plate", amount: 5 }, { "x-forwarded-for": "9.9.9.9" }), env2);
  }
  assert.equal(last.status, 429);
});

// 17. Push message (shout) lands next to the club's position
await t("push message shows on the board row", async () => {
  const env3 = makeEnv();
  const b = await push(env3, { scope: "arg", club: "river-plate", amount: 10, fan: "El Diez", message: "¡Vamos River, hoy hay que ganar!" });
  await confirm(env3, b.data.intentId);
  const d = await board(env3, "arg");
  assert.equal(d.board[0].shout.text, "¡Vamos River, hoy hay que ganar!");
  assert.equal(d.board[0].shout.fan, "El Diez");
  assert.equal(d.activity[0].message, "¡Vamos River, hoy hay que ganar!");
});

// 18. Chat prepaid credit: USD 1 = 3 messages, admin confirms it
const wallet = "123e4567-e89b-12d3-a456-426614174000";
await t("chat credit adds messages and stays out of the rankings", async () => {
  const env4 = makeEnv();
  const before = await (await handler.fetch(req("GET", `/api/chat/wallet?wallet=${wallet}`), env4)).json();
  assert.equal(before.balance, 0);

  const c = await credit(env4, wallet, 1);
  assert.equal(c.status, 201);
  assert.equal(c.data.messages, 3);
  assert.match(c.data.payUrl, /\/pay\.html\?credit=/);

  const paid = await (await confirm(env4, c.data.intentId)).json();
  assert.equal(paid.ok, true);
  assert.equal(paid.type, "chat_credit");
  assert.equal(paid.balance, 3);

  const after = await (await handler.fetch(req("GET", `/api/chat/wallet?wallet=${wallet}`), env4)).json();
  assert.equal(after.balance, 3);
  assert.deepEqual((await board(env4, "global")).board, []);
});

// 19. Posting a chat message spends exactly one credit
await t("fan chat spends one message from the wallet", async () => {
  const env4 = makeEnv();
  const c = await credit(env4, wallet, 1);
  await confirm(env4, c.data.intentId);

  const r = await chat(env4, { wallet, fan: "Ana", club: "boca-juniors", text: "¡Dale campeón!" });
  assert.equal(r.status, 201);
  assert.equal(r.data.balance, 2);
  const d = await (await handler.fetch(req("GET", "/api/chat"), env4)).json();
  assert.equal(d.messages.length, 1);
  assert.equal(d.messages[0].text, "¡Dale campeón!");
  assert.equal(d.messages[0].club, "boca-juniors");

  await chat(env4, { wallet, fan: "Ana", text: "dos" });
  await chat(env4, { wallet, fan: "Ana", text: "tres" });
  const empty = await chat(env4, { wallet, fan: "Ana", text: "cuatro" });
  assert.equal(empty.status, 402);
  assert.equal(empty.data.error, "NO_CHAT_CREDIT");
});

// 20. A bigger deposit keeps the USD 1 = 3 messages rate
await t("USD 10 buys 30 chat messages", async () => {
  const env4 = makeEnv();
  const c = await credit(env4, wallet, 10);
  assert.equal(c.status, 201);
  assert.equal(c.data.messages, 30);
  await confirm(env4, c.data.intentId);
  const r = await chat(env4, { wallet, fan: "Ana", text: "hola" });
  assert.equal(r.data.balance, 29);
});

// 21. Chat credit validation: wallet, amount and missing intent
await t("chat credit validation", async () => {
  const env6 = makeEnv();
  const noWallet = await credit(env6, "nope", 1);
  assert.equal(noWallet.status, 400);
  const low = await credit(env6, wallet, 0.5);
  assert.equal(low.status, 400);
  assert.equal(low.data.error, "AMOUNT_TOO_LOW");
  const badWallet = await handler.fetch(req("GET", "/api/chat/wallet?wallet=nope"), env6);
  assert.equal(badWallet.status, 400);
  const nowhere = await confirm(env6, "123e4567-e89b-12d3-a456-426614174999");
  assert.equal(nowhere.status, 404);
});

// 22. Fan chat: validation (empty text, missing wallet, bogus club)
await t("fan chat validation", async () => {
  const env5 = makeEnv();
  const bad = await handler.fetch(req("POST", "/api/chat", { wallet, fan: "Ana", text: "   " }), env5);
  assert.equal(bad.status, 400);
  const noWallet = await handler.fetch(req("POST", "/api/chat", { fan: "Ana", text: "hola" }), env5);
  assert.equal(noWallet.status, 400);
  assert.equal((await noWallet.json()).error, "WALLET_REQUIRED");
  const noCredit = await handler.fetch(req("POST", "/api/chat", { wallet, fan: "Ana", text: "hola" }), env5);
  assert.equal(noCredit.status, 402);
  const c = await credit(env5, wallet, 1);
  await confirm(env5, c.data.intentId);
  const ok = await handler.fetch(req("POST", "/api/chat", { wallet, fan: "Ana", club: "not-a-club", text: "hola" }), env5);
  const d = await ok.json();
  assert.equal(d.message.club, null);
});

console.log(`\n${n} integration tests passed.`);
