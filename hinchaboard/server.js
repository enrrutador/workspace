const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { URL } = require("url");

const env = require("./lib/env");
const dblib = require("./lib/db");
const boards = require("./lib/boards");
const { CONFIG, hasBadWord, assertBidAmount } = require("./lib/pricing");
const mp = require("./lib/mercadopago");

const PUBLIC_DIR = path.join(__dirname, "public");
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
  ".ico": "image/x-icon"
};

function esc(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function send(res, status, body, headers = {}) {
  const isBuffer = Buffer.isBuffer(body);
  const data = isBuffer || typeof body === "string" ? body : JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": isBuffer
      ? headers["Content-Type"] || "application/octet-stream"
      : typeof body === "string"
        ? headers["Content-Type"] || "text/html; charset=utf-8"
        : "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ...headers
  });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 1_000_000) {
        reject(new Error("body demasiado grande"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error("JSON inv\u00e1lido"));
      }
    });
    req.on("error", reject);
  });
}

function crestSvg(color1, color2, size = 64) {
  const w = size;
  const h = size * 1.1;
  const shield = `M ${w * 0.5} 0 L ${w} ${w * 0.12} L ${w} ${w * 0.55} C ${w} ${w * 0.85} ${w * 0.5} ${h} ${w * 0.5} ${h} C ${w * 0.5} ${h} 0 ${w * 0.85} 0 ${w * 0.55} L 0 ${w * 0.12} Z`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><defs><clipPath id="c"><path d="${shield}"/></clipPath></defs><g clip-path="url(#c)"><rect x="0" y="0" width="${w / 2}" height="${h}" fill="${color1}"/><rect x="${w / 2}" y="0" width="${w / 2}" height="${h}" fill="${color2}"/></g><path d="${shield}" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="${Math.max(1, size / 32)}"/></svg>`;
}

function shareSvg(club, rank, totalUSD, message) {
  const rankLabel = rank === 1 ? "N\u00ba 1" : `#${rank}`;
  const scope = "Ranking mundial";
  const lines = message ? `<foreignObject x="70" y="196" width="500" height="56"><div xmlns="http://www.w3.org/1999/xhtml" style="font:italic 20px Georgia, serif; color:#dbe4ff;">\u201c${esc(message).slice(0, 90)}\u201d</div></foreignObject>` : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320" viewBox="0 0 640 320"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#101733"/><stop offset="1" stop-color="#1a1030"/></linearGradient></defs><rect width="640" height="320" fill="url(#bg)"/><circle cx="560" cy="60" r="140" fill="rgba(90,120,255,.12)"/><circle cx="80" cy="300" r="110" fill="rgba(255,110,150,.08)"/><text x="40" y="64" font-family="Arial, sans-serif" font-size="20" fill="#8892b8" letter-spacing="2">${esc(scope.toUpperCase())}</text><text x="40" y="170" font-family="Arial Black, Arial, sans-serif" font-weight="900" font-size="92" fill="#ffffff">${rankLabel}</text><text x="40" y="130" font-family="Arial, sans-serif" font-size="24" fill="#9fb0e6">la hinchada m\u00e1s generosa</text><text x="230" y="120" font-family="Arial, sans-serif" font-weight="bold" font-size="34" fill="#ffffff">${esc(club.name)}</text><text x="230" y="160" font-family="Arial, sans-serif" font-size="24" fill="#7ef0c2">$${totalUSD.toLocaleString("en-US")}</text><text x="40" y="300" font-family="Arial, sans-serif" font-size="18" fill="#5f6b94">\u2b50 hinchaboard \u00b7 rank es lo que pagas</text>${lines}</svg>`;
}

function clubRankIn(clubId, scopeKey) {
  const scope = boards.boardScope(scopeKey);
  if (!scope) return null;
  const rows = boards.rankClubs(scope.clubs);
  const row = rows.find((r) => r.clubId === clubId);
  return row ? { rank: row.rank, totalUSD: row.totalUSD, message: row.message } : null;
}

function validateMessage(text) {
  if (!text) return null;
  const t = String(text).trim();
  if (t.length > CONFIG.MESSAGE_MAX_CHARS) {
    const err = new Error(`M\u00e1ximo ${CONFIG.MESSAGE_MAX_CHARS} caracteres`);
    err.status = 400;
    throw err;
  }
  if (hasBadWord(t)) {
    const err = new Error("Mensaje rechazado por el filtro de contenido");
    err.status = 400;
    throw err;
  }
  return t || null;
}

function validateEmail(email) {
  if (!email) return null;
  const e = String(email).trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e) || e.length > 140) {
    const err = new Error("Email inv\u00e1lido");
    err.status = 400;
    throw err;
  }
  return e;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const p = url.pathname;
  let m;
  try {
    if (p === "/api/meta") {
      const d = dblib.getDb();
      return send(res, 200, {
        countries: d.countries,
        leagues: d.leagues,
        config: {
          minBidUSD: CONFIG.MIN_BID_USD,
          messagePriceUSD: CONFIG.MESSAGE_PRICE_USD,
          messageMaxChars: CONFIG.MESSAGE_MAX_CHARS,
          chatPackPriceUSD: CONFIG.CHAT_PACK_PRICE_USD,
          chatPackMessages: CONFIG.CHAT_PACK_MESSAGES
        }
      });
    }

    if (p === "/api/board") {
      const scope = url.searchParams.get("scope") || "global";
      const board = boards.boardScope(scope);
      if (!board) return send(res, 404, { error: "Board inexistente" });
      return send(res, 200, {
        scope: board.key,
        label: board.label,
        entries: boards.rankClubs(board.clubs),
        stats: boards.stats()
      });
    }

    if (p === "/api/stats") return send(res, 200, boards.stats());

    m = p.match(/^\/api\/orders\/([\w-]+)$/);
    if (m) {
      const order = dblib.getOrder(m[1]);
      if (!order) return send(res, 404, { error: "Orden inexistente" });
      return send(res, 200, {
        id: order.id,
        status: order.status,
        type: order.type,
        clubId: order.clubId,
        amountUSD: order.amountUSD,
        messages: order.messages || null,
        token: order.status === "paid" ? order.token : undefined
      });
    }

    m = p.match(/^\/api\/claims$/);
    if (m && req.method === "POST") {
      const body = await readBody(req);
      const d = dblib.getDb();
      const club = dblib.getClub(body.clubId);
      if (!club) return send(res, 404, { error: "Club inexistente" });
      const email = validateEmail(body.email);
      const text = validateMessage(body.message);
      const wantsMessage = Boolean(text);
      const type = wantsMessage && !body.amountUSD ? "message" : "bid";
      let amountUSD = 0;
      if (type === "bid") {
        amountUSD = assertBidAmount(body.amountUSD);
        if (wantsMessage) amountUSD += CONFIG.MESSAGE_PRICE_USD;
      } else {
        if (!text) {
          const err = new Error("Los mensajes requieren contenido");
          err.status = 400;
          throw err;
        }
        amountUSD = CONFIG.MESSAGE_PRICE_USD;
      }
      const order = dblib.createOrder({
        type,
        clubId: club.id,
        clubName: club.name,
        amountUSD,
        bidUSD: type === "bid" ? assertBidAmount(body.amountUSD) : 0,
        message: text,
        title: type === "bid" ? `Apoyo a ${club.name}` + (wantsMessage ? " + mensaje" : "") : `Mensaje en ${club.name}`,
        email
      });
      if (env.DEV_PAYMENTS) {
        dblib.completeOrder(order);
        if (wantsMessage) {
          boards.activeMessage(club.id);
        }
        return send(res, 200, { dev: true, order, share: `/api/share/${club.id}.svg` });
      }
      await mp.createPreference(order);
      return send(res, 200, { order, initPoint: order.initPoint, share: `/api/share/${club.id}.svg` });
    }

    m = p.match(/^\/webhooks\/mercadopago$/);
    if (m && req.method === "POST") {
      const body = await readBody(req).catch(() => ({}));
      const paymentId = body?.data?.id || url.searchParams.get("data.id");
      if (!paymentId) return send(res, 200, { ok: true });
      const payment = await mp.fetchPayment(paymentId);
      if (payment.status === "approved") {
        const order = dblib.getOrder(payment.external_reference);
        if (order) dblib.completeOrder(order);
      }
      return send(res, 200, { ok: true });
    }

    m = p.match(/^\/api\/share\/([\w-]+)\.svg$/);
    if (m) {
      const club = dblib.getClub(m[1]);
      if (!club) return send(res, 404, { error: "Club inexistente" });
      const info = clubRankIn(club.id, "global") || { rank: 0, totalUSD: 0, message: null };
      return send(res, 200, shareSvg(club, info.rank, info.totalUSD, info.message), { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=30" });
    }

    m = p.match(/^\/api\/crest\/([\w-]+)\.svg$/);
    if (m) {
      const club = dblib.getClub(m[1]);
      if (!club) return send(res, 404, { error: "Club inexistente" });
      return send(res, 200, crestSvg(club.colors[0], club.colors[1], 40), { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=86400" });
    }

    m = p.match(/^\/api\/chat\/([\w-]+)\/messages$/);
    if (m) {
      const d = dblib.getDb();
      if (!d.leagues.some((l) => l.id === m[1])) return send(res, 404, { error: "Sala inexistente" });
      const since = url.searchParams.get("since");
      let list = d.chatMessages.filter((msg) => msg.room === m[1]);
      if (since) list = list.filter((msg) => msg.createdAt > since);
      return send(res, 200, { messages: list.slice(-100) });
    }

    m = p.match(/^\/api\/chat\/([\w-]+)\/send$/);
    if (m && req.method === "POST") {
      const body = await readBody(req);
      const d = dblib.getDb();
      if (!d.leagues.some((l) => l.id === m[1])) return send(res, 404, { error: "Sala inexistente" });
      const token = String(body.token || "");
      const entry = dblib.getOrCreateChatToken(token);
      if (entry.remaining <= 0) {
        return send(res, 402, { error: "Sin mensajes disponibles. Compra un paquete para escribir." });
      }
      if (entry.lastWriteAt) {
        const elapsed = Date.now() - new Date(entry.lastWriteAt).getTime();
        if (elapsed < CONFIG.CHAT_RATE_LIMIT_MS) {
          return send(res, 429, { error: "Vas muy r\u00e1pido, espera unos segundos" });
        }
      }
      const text = String(body.text || "").trim();
      if (!text || text.length > CONFIG.CHAT_MAX_CHARS) {
        return send(res, 400, { error: `Mensaje vac\u00edo o mayor a ${CONFIG.CHAT_MAX_CHARS} caracteres` });
      }
      if (hasBadWord(text)) return send(res, 400, { error: "Mensaje rechazado por el filtro de contenido" });
      const club = body.clubId ? dblib.getClub(body.clubId) : null;
      entry.remaining -= 1;
      entry.lastWriteAt = new Date().toISOString();
      const msg = {
        id: dblib.newId("msg"),
        room: m[1],
        clubId: club ? club.id : null,
        clubName: club ? club.name : null,
        colors: club ? club.colors : ["#5A6CFF", "#8B5CF6"],
        text,
        createdAt: entry.lastWriteAt
      };
      d.chatMessages.push(msg);
      if (d.chatMessages.length > 5000) d.chatMessages = d.chatMessages.slice(-5000);
      dblib.save();
      return send(res, 200, { message: msg, remaining: entry.remaining });
    }

    m = p.match(/^\/api\/chat\/pack$/);
    if (m && req.method === "POST") {
      const body = await readBody(req).catch(() => ({}));
      const email = validateEmail(body.email);
      const token = `chat_${crypto.randomBytes(8).toString("hex")}`;
      const order = dblib.createOrder({
        type: "chat_pack",
        amountUSD: CONFIG.CHAT_PACK_PRICE_USD,
        messages: CONFIG.CHAT_PACK_MESSAGES,
        token,
        title: `Paquete de ${CONFIG.CHAT_PACK_MESSAGES} mensajes para el chat`,
        email
      });
      if (env.DEV_PAYMENTS) {
        dblib.completeOrder(order);
        return send(res, 200, { dev: true, token, remaining: CONFIG.CHAT_PACK_MESSAGES });
      }
      await mp.createPreference(order);
      return send(res, 200, { order, initPoint: order.initPoint, token });
    }

    m = p.match(/^\/api\/chat\/pack\/([\w]+)$/);
    if (m) {
      const d = dblib.getDb();
      const entry = d.chatTokens.find((t) => t.token === m[1]);
      if (!entry) return send(res, 404, { error: "Token inexistente" });
      return send(res, 200, { remaining: entry.remaining });
    }

    if (p === "/" || p === "/index.html") {
      return send(res, 200, fs.readFileSync(path.join(PUBLIC_DIR, "index.html")), { "Content-Type": MIME[".html"] });
    }
    const staticFile = path.join(PUBLIC_DIR, p.replace(/^\//, ""));
    if (staticFile.startsWith(PUBLIC_DIR) && fs.existsSync(staticFile) && fs.statSync(staticFile).isFile()) {
      return send(res, 200, fs.readFileSync(staticFile), { "Content-Type": MIME[path.extname(staticFile)] || "application/octet-stream" });
    }
    if (p === "/favicon.ico") return res.writeHead(204).end();
    return send(res, 404, { error: "No encontrado" });
  } catch (err) {
    const status = err.status || 500;
    if (status >= 500) console.error(err);
    return send(res, status, { error: status >= 500 ? "Error interno" : err.message });
  }
});

server.listen(env.PORT, () => {
  console.log(`Hinchaboard corriendo en http://localhost:${env.PORT} ${env.DEV_PAYMENTS ? "(modo dev: pagos se aplican al instante)" : "(MercadoPago activo)"}`);
});
