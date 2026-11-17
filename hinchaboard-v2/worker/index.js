/**
 * index.js — Cloudflare Worker for Hinchaboard.
 *
 * Two independent rankings per club:
 *   - country: only clubs from that country, pushed only into their own table
 *   - global: every club in the world, pushed independently of its country
 * A push in one ranking never moves the other.
 *
 * Routes:
 *   GET  /api/board                 ranked clubs for one ranking (public)
 *                                   ?scope=global (default) | ?scope=<countryId>
 *   GET  /api/chat                  fan chat ("La Tribuna"), newest first
 *   POST /api/chat                  post a chat message (rate-limited)
 *   POST /api/pushes                create a push intent (rate-limited, validated)
 *   GET  /api/intents/:id           push intent status (for the pay page)
 *   POST /api/admin/confirm         mark an intent as paid (dev/testing only,
 *                                   guarded by ADMIN_SECRET env var)
 *   POST /api/webhooks/polar        payment webhook (stub — 501 until wired)
 *   POST /api/webhooks/lemonsqueezy payment webhook (stub — 501 until wired)
 *
 * Storage (KV binding RANKING_KV):
 *   "board:global"    JSON {clubId: {league,total,pushes,firstAt,lastAt,shout?}}
 *   "board:country:<countryId>"  same shape, only clubs from that country
 *   "activity"        JSON array of recent confirmed pushes (newest first)
 *   "chat"            JSON array of fan chat messages (newest first)
 *   "intents:<uuid>"  JSON of one pending intent (auto-expires via KV TTL)
 *   "rl:<ip>"         JSON array of recent POST /api/pushes timestamps
 *
 * Payments are behind a clean interface: PAYMENT_PROVIDER env var selects
 * "stub" (default), "polar" or "lemonsqueezy". Only "stub" is implemented;
 * the other two return 501 with notes on what to implement (signature
 * verification + mapping the provider event to confirmPush()).
 */
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
  boardStats,
  checkRateLimit,
  MIN_PUSH_USD,
  STEP_USD,
  ACTIVITY_MAX,
  CHAT_MAX,
  CHAT_RATE_MAX,
  CHAT_RATE_WINDOW_MS,
  CHAT_MESSAGES_PER_USD,
  INTENT_TTL_SECONDS,
} from "./lib.js";
import { CLUB_LEAGUE } from "./clubs-data.js";

const COUNTRY_IDS = new Set(Object.values(CLUB_LEAGUE));

const json = (data, status = 200, extraHeaders = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...extraHeaders },
  });

const clientIp = (req) =>
  req.headers.get("cf-connecting-ip") ||
  req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
  "unknown";

const isScope = (scope) => scope === "global" || COUNTRY_IDS.has(scope);
const boardKey = (scope) =>
  scope === "global" ? "board:global" : `board:country:${scope}`;

async function readBoard(env, scope) {
  return (await env.RANKING_KV.get(boardKey(scope), "json")) || {};
}
async function readActivity(env) {
  return (await env.RANKING_KV.get("activity", "json")) || [];
}
async function readWallet(env, wallet) {
  return (await env.RANKING_KV.get(`wallet:${wallet}`, "json")) || { messages: 0 };
}
async function creditWallet(env, wallet, messages) {
  const current = await readWallet(env, wallet);
  const balance = current.messages + messages;
  await env.RANKING_KV.put(`wallet:${wallet}`, JSON.stringify({ messages: balance, updatedAt: Date.now() }));
  return balance;
}

/** Move a paid intent into the correct ranking + activity feed. */
async function confirmPush(env, intent) {
  const at = Date.now();
  const scope = intent.scope || "global";
  const totals = applyPush(await readBoard(env, scope), {
    club: intent.club,
    league: intent.league,
    amount: intent.amount,
    at,
    shout: intent.message ? { text: intent.message, fan: intent.fan || "", at } : null,
  });
  await env.RANKING_KV.put(boardKey(scope), JSON.stringify(totals));
  const activity = [
    {
      club: intent.club,
      league: intent.league,
      scope,
      amount: intent.amount,
      fan: intent.fan || "",
      message: intent.message || "",
      at,
    },
    ...(await readActivity(env)),
  ].slice(0, ACTIVITY_MAX);
  await env.RANKING_KV.put("activity", JSON.stringify(activity));
  await env.RANKING_KV.delete(`intents:${intent.id}`);
  return rankBoard(totals);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname;

    // ---- Public board -------------------------------------------------
    if (req.method === "GET" && path === "/api/board") {
      let scope = url.searchParams.get("scope") || "global";
      if (scope === "country") {
        scope = url.searchParams.get("country") || "";
        if (!COUNTRY_IDS.has(scope)) return json({ ok: false, error: "UNKNOWN_SCOPE" }, 400);
      }
      if (!isScope(scope)) return json({ ok: false, error: "UNKNOWN_SCOPE" }, 400);
      const ranked = rankBoard(await readBoard(env, scope));
      return json({
        ok: true,
        scope,
        board: ranked,
        activity: await readActivity(env),
        stats: boardStats(ranked),
        rules: { minPushUsd: MIN_PUSH_USD, stepUsd: STEP_USD },
      });
    }

    // ---- Create push intent -------------------------------------------
    if (req.method === "POST" && path === "/api/pushes") {
      const ip = clientIp(req);
      const rlKey = `rl:${ip}`;
      const rl = checkRateLimit(await env.RANKING_KV.get(rlKey, "json"), Date.now());
      if (!rl.allowed) {
        return json({ ok: false, error: "RATE_LIMITED" }, 429, {
          "retry-after": "3600",
        });
      }
      await env.RANKING_KV.put(rlKey, JSON.stringify(rl.timestamps), {
        expirationTtl: 3600,
      });

      let body;
      try {
        body = await req.json();
      } catch {
        return json({ ok: false, error: "BAD_JSON" }, 400);
      }
      const scope = body.scope || "global";
      if (!isScope(scope)) return json({ ok: false, error: "UNKNOWN_SCOPE" }, 400);
      if (!isClubId(body.club) || !(body.club in CLUB_LEAGUE)) {
        return json({ ok: false, error: "CLUB_UNKNOWN" }, 400);
      }
      const league = CLUB_LEAGUE[body.club];
      if (scope !== "global" && scope !== league) {
        return json({ ok: false, error: "SCOPE_MISMATCH" }, 400);
      }
      const check = validatePushAmount(body.amount);
      if (!check.ok) return json({ ok: false, ...check }, 400);

      const intent = {
        id: crypto.randomUUID(),
        type: "push",
        club: body.club,
        league,
        scope,
        amount: check.amount,
        fan: sanitizeFanName(body.fan),
        message: sanitizeShout(body.message),
        status: "pending_payment",
        provider: env.PAYMENT_PROVIDER || "stub",
        createdAt: Date.now(),
      };
      await env.RANKING_KV.put(`intents:${intent.id}`, JSON.stringify(intent), {
        expirationTtl: INTENT_TTL_SECONDS,
      });
      return json(
        { ok: true, intentId: intent.id, payUrl: `/pay.html?intent=${intent.id}` },
        201
      );
    }

    // ---- Fan chat ("La Tribuna") ---------------------------------------
    if (req.method === "GET" && path === "/api/chat") {
      const messages = (await env.RANKING_KV.get("chat", "json")) || [];
      return json({ ok: true, messages });
    }

    // ---- Chat prepaid wallet -------------------------------------------
    if (req.method === "GET" && path === "/api/chat/wallet") {
      const wallet = url.searchParams.get("wallet") || "";
      if (!isWalletId(wallet)) return json({ ok: false, error: "WALLET_REQUIRED" }, 400);
      return json({ ok: true, balance: (await readWallet(env, wallet)).messages });
    }

    // USD 1 = 3 messages. The browser stores the wallet token; credits are
    // separate from every ranking and never push a club.
    if (req.method === "POST" && path === "/api/chat/credits") {
      const ip = clientIp(req);
      const rlKey = `rlcr:${ip}`;
      const rl = checkRateLimit(await env.RANKING_KV.get(rlKey, "json"), Date.now());
      if (!rl.allowed) {
        return json({ ok: false, error: "RATE_LIMITED" }, 429, { "retry-after": "3600" });
      }
      await env.RANKING_KV.put(rlKey, JSON.stringify(rl.timestamps), {
        expirationTtl: 3600,
      });

      let body;
      try {
        body = await req.json();
      } catch {
        return json({ ok: false, error: "BAD_JSON" }, 400);
      }
      if (!isWalletId(body.wallet)) return json({ ok: false, error: "WALLET_REQUIRED" }, 400);
      const check = validateCreditAmount(body.amount);
      if (!check.ok) return json({ ok: false, ...check }, 400);

      const intent = {
        id: crypto.randomUUID(),
        type: "chat_credit",
        wallet: body.wallet,
        amount: check.amount,
        messages: check.messages,
        status: "pending_payment",
        provider: env.PAYMENT_PROVIDER || "stub",
        createdAt: Date.now(),
      };
      await env.RANKING_KV.put(`intents:${intent.id}`, JSON.stringify(intent), {
        expirationTtl: INTENT_TTL_SECONDS,
      });
      return json(
        {
          ok: true,
          intentId: intent.id,
          payUrl: `/pay.html?credit=${intent.id}`,
          messages: intent.messages,
          rate: CHAT_MESSAGES_PER_USD,
        },
        201
      );
    }

    if (req.method === "POST" && path === "/api/chat") {
      const ip = clientIp(req);
      const rlKey = `rlc:${ip}`;
      const rl = checkRateLimit(
        await env.RANKING_KV.get(rlKey, "json"), Date.now(), CHAT_RATE_MAX, CHAT_RATE_WINDOW_MS);
      if (!rl.allowed) {
        return json({ ok: false, error: "RATE_LIMITED" }, 429, { "retry-after": "600" });
      }
      await env.RANKING_KV.put(rlKey, JSON.stringify(rl.timestamps), {
        expirationTtl: Math.ceil(CHAT_RATE_WINDOW_MS / 1000),
      });

      let body;
      try {
        body = await req.json();
      } catch {
        return json({ ok: false, error: "BAD_JSON" }, 400);
      }
      const text = sanitizeChatText(body.text);
      if (!text) return json({ ok: false, error: "TEXT_REQUIRED" }, 400);
      if (!isWalletId(body.wallet)) return json({ ok: false, error: "WALLET_REQUIRED" }, 400);
      const wallet = await readWallet(env, body.wallet);
      if (wallet.messages < 1) return json({ ok: false, error: "NO_CHAT_CREDIT" }, 402);

      const balance = wallet.messages - 1;
      await env.RANKING_KV.put(
        `wallet:${body.wallet}`,
        JSON.stringify({ messages: balance, updatedAt: Date.now() })
      );
      const message = {
        fan: sanitizeFanName(body.fan),
        club: isClubId(body.club) && body.club in CLUB_LEAGUE ? body.club : null,
        text,
        at: Date.now(),
      };
      const messages = [message, ...((await env.RANKING_KV.get("chat", "json")) || [])].slice(0, CHAT_MAX);
      await env.RANKING_KV.put("chat", JSON.stringify(messages));
      return json({ ok: true, message, balance }, 201);
    }

    // ---- Intent status (pay page polls this) ---------------------------
    const intentMatch = path.match(/^\/api\/intents\/([0-9a-f-]{36})$/);
    if (req.method === "GET" && intentMatch) {
      const intent = await env.RANKING_KV.get(`intents:${intentMatch[1]}`, "json");
      if (!intent) return json({ ok: false, error: "INTENT_NOT_FOUND" }, 404);
      return json({ ok: true, intent });
    }

    // ---- Admin confirm (DEV/TESTING ONLY — remove or protect in prod) --
    if (req.method === "POST" && path === "/api/admin/confirm") {
      const secret = req.headers.get("x-admin-secret");
      if (!env.ADMIN_SECRET || secret !== env.ADMIN_SECRET) {
        return json({ ok: false, error: "UNAUTHORIZED" }, 401);
      }
      let body;
      try {
        body = await req.json();
      } catch {
        return json({ ok: false, error: "BAD_JSON" }, 400);
      }
      const intent = await env.RANKING_KV.get(`intents:${body.intentId}`, "json");
      if (!intent) return json({ ok: false, error: "INTENT_NOT_FOUND" }, 404);
      if (intent.type === "chat_credit") {
        const balance = await creditWallet(env, intent.wallet, intent.messages);
        await env.RANKING_KV.delete(`intents:${intent.id}`);
        return json({ ok: true, type: "chat_credit", messages: intent.messages, balance });
      }
      const board = await confirmPush(env, intent);
      return json({ ok: true, type: "push", scope: intent.scope || "global", board });
    }

    // ---- Payment webhooks (stubs — wire a real provider here) ---------
    const hookMatch = path.match(/^\/api\/webhooks\/(polar|lemonsqueezy)$/);
    if (req.method === "POST" && hookMatch) {
      // TODO(provider): verify webhook signature with the provider secret,
      // extract intentId + paid amount from the event payload, then call
      // confirmPush(env, intent). See IMPLEMENTACION.md "Conectar pagos reales".
      return json(
        {
          ok: false,
          error: "PROVIDER_NOT_CONNECTED",
          provider: hookMatch[1],
          hint: "Set PAYMENT_PROVIDER and implement signature verification (see IMPLEMENTACION.md).",
        },
        501
      );
    }

    return json({ ok: false, error: "NOT_FOUND" }, 404);
  },
};
