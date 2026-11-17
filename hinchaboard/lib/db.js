const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DATA_DIR = path.join(__dirname, "..", "data");
const DB_PATH = path.join(DATA_DIR, "db.json");

let db = null;

function newId(prefix) {
  return `${prefix}_${crypto.randomBytes(6).toString("hex")}`;
}

function seedIfMissing() {
  const seed = require("../data/seed");
  db = seed.buildDatabase();
  save();
  console.log(`[db] base creada con ${db.clubs.length} clubes en ${db.leagues.length} ligas`);
}

function load() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(DB_PATH)) {
    seedIfMissing();
    return;
  }
  db = JSON.parse(fs.readFileSync(DB_PATH, "utf8"));
}

function save() {
  const tmp = DB_PATH + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(db));
  fs.renameSync(tmp, DB_PATH);
}

function getDb() {
  if (!db) load();
  return db;
}

function getClub(clubId) {
  return getDb().clubs.find((c) => c.id === clubId);
}

function createOrder(fields) {
  const d = getDb();
  const order = {
    id: newId("ord"),
    status: "pending",
    createdAt: new Date().toISOString(),
    ...fields
  };
  d.orders.push(order);
  save();
  return order;
}

function getOrder(orderId) {
  return getDb().orders.find((o) => o.id === orderId);
}

function completeOrder(order) {
  if (!order || order.status === "paid") return null;
  const d = getDb();
  order.status = "paid";
  order.paidAt = new Date().toISOString();
  if (order.type === "bid") {
    d.bids.push({
      id: newId("bid"),
      clubId: order.clubId,
      usd: order.bidUSD,
      message: order.message || null,
      createdAt: order.paidAt,
      email: order.email || null
    });
    if (order.message) {
      d.messages.push({ clubId: order.clubId, text: order.message, paidAt: order.paidAt });
    }
  } else if (order.type === "message") {
    d.messages.push({ clubId: order.clubId, text: order.message, paidAt: order.paidAt });
  } else if (order.type === "chat_pack") {
    d.chatTokens.push({
      token: order.token,
      remaining: order.messages,
      createdAt: order.paidAt,
      lastWriteAt: null
    });
  }
  save();
  return order;
}

function getOrCreateChatToken(token) {
  const d = getDb();
  let entry = d.chatTokens.find((t) => t.token === token);
  if (!entry) {
    entry = { token, remaining: 0, createdAt: new Date().toISOString(), lastWriteAt: null };
    d.chatTokens.push(entry);
    save();
  }
  return entry;
}

module.exports = {
  getDb,
  save,
  getClub,
  createOrder,
  getOrder,
  completeOrder,
  getOrCreateChatToken,
  newId
};
