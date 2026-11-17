/**
 * lib.js — pure business logic for Hinchaboard.
 * Fans push USD 1+ for their club; pushes pool into the club's total inside
 * one ranking (its country or the independent global ranking). A club passes
 * the one above it when its total beats it by at least STEP_USD ($1).
 * No Cloudflare-specific APIs here, so it can be unit-tested with plain node.
 */

export const MIN_PUSH_USD = 1;          // minimum single push
export const STEP_USD = 1;              // pass margin between club totals
export const MAX_PUSH_USD = 100_000;    // sanity cap per push
export const INTENT_TTL_SECONDS = 60 * 60; // pending-payment intents expire in 1h
export const RATE_LIMIT_MAX = 10;       // max push attempts...
export const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // ...per IP per hour
export const MAX_FAN_LEN = 40;          // max chars of the optional fan alias
export const ACTIVITY_MAX = 30;         // recent pushes kept for the live feed
export const MAX_SHOUT_LEN = 140;       // push message shown next to the club's position
export const MAX_CHAT_LEN = 200;        // fan chat message
export const CHAT_MESSAGES_PER_USD = 3; // USD 1 = 3 chat messages
export const MIN_CREDIT_USD = 1;        // minimum chat credit
export const MAX_CREDIT_USD = 1000;     // sanity cap per credit
export const CHAT_MAX = 50;             // chat messages kept
export const CHAT_RATE_MAX = 20;        // max chat messages...
export const CHAT_RATE_WINDOW_MS = 10 * 60 * 1000; // ...per IP per 10 minutes

const CLUB_ID_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const WALLET_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Club ids are lowercase kebab-case slugs from the clubs seed. */
export const isClubId = (id) => typeof id === "string" && CLUB_ID_RE.test(id);

/** Wallet tokens are UUIDs generated and stored by the browser. */
export const isWalletId = (id) => typeof id === "string" && WALLET_RE.test(id);

/** Shared text hygiene: strip HTML-ish chars, collapse spaces, trim, cap. */
export function sanitizeText(raw, maxLen) {
  if (typeof raw !== "string") return "";
  return raw.replace(/[<>&"']/g, "").replace(/\s+/g, " ").trim().slice(0, maxLen);
}

/** Optional fan alias shown in the activity feed; strip HTML-ish chars. */
export function sanitizeFanName(raw) {
  return sanitizeText(raw, MAX_FAN_LEN);
}

/** Optional message attached to a push, displayed next to the club's position. */
export const sanitizeShout = (raw) => sanitizeText(raw, MAX_SHOUT_LEN);

/** Fan chat message text. */
export const sanitizeChatText = (raw) => sanitizeText(raw, MAX_CHAT_LEN);

/**
 * Validate a chat credit purchase. USD 1 buys 3 messages; a larger deposit
 * keeps the same rate and the whole messages are credited.
 * @returns {{ok:true, amount:number, messages:number} | {ok:false, error:string}}
 */
export function validateCreditAmount(rawAmount) {
  const amount = Number(rawAmount);
  if (!Number.isFinite(amount)) return { ok: false, error: "AMOUNT_INVALID" };
  const rounded = Math.round(amount * 100) / 100;
  if (rounded < MIN_CREDIT_USD) return { ok: false, error: "AMOUNT_TOO_LOW" };
  if (rounded > MAX_CREDIT_USD) return { ok: false, error: "AMOUNT_TOO_HIGH" };
  const messages = Math.floor(rounded * CHAT_MESSAGES_PER_USD);
  if (messages < 1) return { ok: false, error: "AMOUNT_TOO_LOW" };
  return { ok: true, amount: rounded, messages };
}

/**
 * Validate a single fan push amount (pooling means no step rule per push —
 * the step governs club totals, see neededToPass).
 * @returns {{ok:true, amount:number} | {ok:false, error:string, minAllowed?:number}}
 */
export function validatePushAmount(rawAmount) {
  const amount = Number(rawAmount);
  if (!Number.isFinite(amount)) return { ok: false, error: "AMOUNT_INVALID" };
  const rounded = Math.round(amount * 100) / 100;
  if (rounded < MIN_PUSH_USD) {
    return { ok: false, error: "AMOUNT_TOO_LOW", minAllowed: MIN_PUSH_USD };
  }
  if (rounded > MAX_PUSH_USD) {
    return { ok: false, error: "AMOUNT_TOO_HIGH", minAllowed: MIN_PUSH_USD };
  }
  return { ok: true, amount: rounded };
}

/**
 * Pool a confirmed push into one ranking's totals map.
 * totals shape: { [clubId]: {league, total, pushes, firstAt, lastAt, shout?} }
 * shout: {text, fan, at} — the latest push message, shown next to the
 * club's position. A push without a message keeps the previous shout.
 * Returns a new object; the input is not mutated.
 */
export function applyPush(totals, { club, league, amount, at, shout }) {
  const next = { ...(totals || {}) };
  const cur = next[club] || { league, total: 0, pushes: 0, firstAt: at, lastAt: at };
  next[club] = {
    league,
    total: Math.round((cur.total + amount) * 100) / 100,
    pushes: cur.pushes + 1,
    firstAt: cur.firstAt,
    lastAt: at,
    ...(shout && shout.text ? { shout } : cur.shout ? { shout: cur.shout } : {}),
  };
  return next;
}

/**
 * Rank clubs by pooled total: highest first; ties keep the club that
 * reached the board earliest (firstAt) first.
 */
export function rankBoard(totals) {
  return Object.entries(totals || {})
    .map(([club, v]) => ({
      club,
      league: v.league,
      total: v.total,
      pushes: v.pushes,
      firstAt: v.firstAt,
      lastAt: v.lastAt,
      ...(v.shout ? { shout: v.shout } : {}),
    }))
    .sort((a, b) => b.total - a.total || a.firstAt - b.firstAt)
    .map((r, i) => ({ position: i + 1, ...r }));
}

/**
 * How much more a club needs to pass the club directly above it:
 * the rival's total + STEP_USD − its own total. null when leader/unranked.
 */
export function neededToPass(ranked, clubId) {
  const idx = ranked.findIndex((r) => r.club === clubId);
  if (idx <= 0) return null;
  const above = ranked[idx - 1];
  const me = ranked[idx];
  return Math.round((above.total + STEP_USD - me.total) * 100) / 100;
}

/** Aggregate stats for the header counters. */
export function boardStats(ranked) {
  return {
    totalPushed: Math.round(ranked.reduce((s, r) => s + r.total, 0) * 100) / 100,
    totalPushes: ranked.reduce((s, r) => s + r.pushes, 0),
    clubsRanked: ranked.length,
  };
}

/**
 * Sliding-window rate limiter over an array of past attempt timestamps.
 * @returns {{allowed:boolean, timestamps:number[]}} pruned list to persist
 */
export function checkRateLimit(timestamps, now = Date.now(), max = RATE_LIMIT_MAX, windowMs = RATE_LIMIT_WINDOW_MS) {
  const cutoff = now - windowMs;
  const fresh = (Array.isArray(timestamps) ? timestamps : []).filter((t) => t > cutoff);
  if (fresh.length >= max) return { allowed: false, timestamps: fresh };
  fresh.push(now);
  return { allowed: true, timestamps: fresh };
}
