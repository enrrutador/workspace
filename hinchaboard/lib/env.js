const fs = require("fs");
const path = require("path");

function loadEnvFile() {
  const envPath = path.join(__dirname, "..", ".env");
  if (!fs.existsSync(envPath)) return;
  const raw = fs.readFileSync(envPath, "utf8");
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim();
    if (!(key in process.env)) process.env[key] = value;
  }
}

loadEnvFile();

module.exports = {
  PORT: parseInt(process.env.PORT || "3000", 10),
  PUBLIC_URL: process.env.PUBLIC_URL || "http://localhost:3000",
  MP_ACCESS_TOKEN: process.env.MERCADOPAGO_ACCESS_TOKEN || "",
  MP_WEBHOOK_SECRET: process.env.MERCADOPAGO_WEBHOOK_SECRET || "",
  COUNTRY_CODE: process.env.COUNTRY_CODE || "AR",
  CURRENCY: process.env.CURRENCY || "USD",
  DEV_PAYMENTS: !process.env.MERCADOPAGO_ACCESS_TOKEN
};
