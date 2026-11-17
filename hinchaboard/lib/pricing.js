const CONFIG = {
  MIN_BID_USD: 1,
  MAX_BID_USD: 999999,
  MIN_RAISE_USD: 1,
  TOP_UP_COST_USD: 0,
  MESSAGE_PRICE_USD: 2,
  MESSAGE_MAX_CHARS: 140,
  MESSAGE_TTL_HOURS: 72,
  CHAT_PACK_PRICE_USD: 2,
  CHAT_PACK_MESSAGES: 10,
  CHAT_MAX_CHARS: 280,
  CHAT_RATE_LIMIT_MS: 5000,
  CHAT_HISTORY_PER_ROOM: 200
};

const BAD_WORDS = [
  "puta", "puto", "mierda", "pendejo", "chinga", "co\u00f1o", "maricon", "negro de m",
  "verga", "carajo", "cabron", "gilipollas", "sudaca", "fuera pet", "cabr\u00e3o",
  "viado", "ot\u00e1rio", "arrombado", "nazi", "hitler"
];

function hasBadWord(text) {
  const normalized = text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return BAD_WORDS.some((w) => w && normalized.includes(w.normalize("NFD").replace(/[\u0300-\u036f]/g, "")));
}

function assertBidAmount(usd) {
  const n = Math.floor(Number(usd));
  if (!Number.isFinite(n) || n < CONFIG.MIN_BID_USD || n > CONFIG.MAX_BID_USD) {
    const err = new Error(`Monto inv\u00e1lido: entre $${CONFIG.MIN_BID_USD} y $${CONFIG.MAX_BID_USD} USD en enteros`);
    err.status = 400;
    throw err;
  }
  return n;
}

module.exports = { CONFIG, hasBadWord, assertBidAmount };
