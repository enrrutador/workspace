const { PUBLIC_URL, MP_ACCESS_TOKEN, CURRENCY } = require("./env");
const { save } = require("./db");

const API_BASE = "https://api.mercadopago.com";

async function mpFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${MP_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(`MercadoPago ${res.status}: ${JSON.stringify(body)}`);
    err.status = 502;
    throw err;
  }
  return body;
}

async function createPreference(order) {
  const item = {
    id: order.id,
    title: order.title,
    quantity: 1,
    unit_price: order.amountUSD,
    currency_id: CURRENCY
  };
  const preference = await mpFetch(`${API_BASE}/checkout/preferences`, {
    method: "POST",
    body: JSON.stringify({
      items: [item],
      external_reference: order.id,
      notification_url: `${PUBLIC_URL}/webhooks/mercadopago`,
      back_urls: {
        success: `${PUBLIC_URL}/?order=${order.id}`,
        failure: `${PUBLIC_URL}/?order=${order.id}&failed=1`,
        pending: `${PUBLIC_URL}/?order=${order.id}&pending=1`
      },
      auto_return: "approved"
    })
  });
  order.initPoint = preference.init_point;
  order.mpPreferenceId = preference.id;
  save();
  return order;
}

async function fetchPayment(paymentId) {
  return mpFetch(`${API_BASE}/v1/payments/${paymentId}`);
}

module.exports = { createPreference, fetchPayment };
