const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const state = {
  meta: null,
  config: null,
  scope: "global",
  tab: "board",
  chatRoom: null,
  chatToken: localStorage.getItem("hb_token") || null,
  chatRemaining: 0,
  lastChatTs: null,
  pollers: {}
};

function fmt(usd) {
  return "$" + Number(usd).toLocaleString("en-US");
}

function toast(text, isError = false) {
  const el = $("#toast");
  el.textContent = text;
  el.className = "toast" + (isError ? " error" : "");
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), 3500);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(body.error || "Error");
    err.status = res.status;
    throw err;
  }
  return body;
}

async function loadMeta() {
  const meta = await api("/api/meta");
  state.meta = meta;
  state.config = meta.config;
  const countrySel = $("#country-select");
  const leagueSel = $("#league-select");
  countrySel.innerHTML = '<option value="">🌍 País…</option>';
  leagueSel.innerHTML = '<option value="">🏆 Liga…</option>';
  for (const c of meta.countries) {
    countrySel.insertAdjacentHTML("beforeend", `<option value="${c.code}">${c.name}</option>`);
  }
  const grouped = {};
  for (const l of meta.leagues) {
    (grouped[l.countryName] = grouped[l.countryName] || []).push(l);
  }
  for (const [countryName, leagues] of Object.entries(grouped)) {
    const og = document.createElement("optgroup");
    og.label = countryName;
    for (const l of leagues) {
      og.insertAdjacentHTML("beforeend", `<option value="${l.id}">${l.name}</option>`);
    }
    leagueSel.appendChild(og);
  }
}

function crestImg(clubId) {
  return `<img src="/api/crest/${clubId}.svg" width="40" alt="escudo" />`;
}

function renderBoard(data) {
  $("#board-label").textContent = data.label;
  const list = $("#board-list");
  const now = new Date();
  list.innerHTML = data.entries.map((e, i) => {
    const top3 = e.rank <= 3 && e.totalUSD > 0;
    const zero = e.totalUSD === 0;
    const msg = e.message
      ? `<div class="club-message">💬 “${e.message.replace(/[<>&"]/g, "")}”</div>`
      : zero
        ? `<div class="club-message club-meta">Pon a ${e.name} primera con tu primer apoyo</div>`
        : "";
    return `<li class="board-item ${top3 ? "top3" : ""} ${zero ? "zero" : ""}">
      <div class="rank-badge">${e.rank}</div>
      <div class="crest">${crestImg(e.clubId)}</div>
      <div class="club-cell">
        <div class="club-name">${e.name}</div>
        <div class="club-meta">${e.country} · ${leagueName(e.league)} · ${Number(e.totalUSD).toLocaleString("en-US")} apoyos</div>
        ${msg}
      </div>
      <div class="amount">${fmt(e.totalUSD)}</div>
      <button class="bid-btn" data-club="${e.clubId}" data-total="${e.totalUSD}">${zero ? "Apoyar" : "Pujar"}</button>
    </li>`;
  }).join("");
  $$(".bid-btn").forEach((b) => b.addEventListener("click", () => openClaim(b.dataset.club, Number(b.dataset.total))));
}

function leagueName(id) {
  const l = state.meta?.leagues.find((x) => x.id === id);
  return l ? l.name : id;
}

async function refreshBoard() {
  const data = await api(`/api/board?scope=${encodeURIComponent(state.scope)}`);
  if (state.tab === "board") renderBoard(data);
  return data;
}

function setView(tab, scope) {
  if (scope) {
    state.scope = scope;
    $("#country-select").value = scope.startsWith("country:") ? scope.split(":")[1] : "";
    $("#league-select").value = scope.startsWith("league:") ? scope.split(":")[1] : "";
  }
  state.tab = tab;
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
  $("#view-board").classList.toggle("hidden", tab !== "board");
  $("#view-chat").classList.toggle("hidden", tab !== "chat");
  runPollers();
}

function runPollers() {
  clearInterval(state.pollers.board);
  clearInterval(state.pollers.chat);
  state.pollers.board = setInterval(refreshBoard, 6000);
  if (state.tab === "chat") {
    pollChat();
    state.pollers.chat = setInterval(pollChat, 3000);
  }
}

let claimCl = null;
function openClaim(clubId, currentTotal) {
  const club = state.meta.clubs.find((c) => c.id === clubId) || {};
  claimCl = { clubId, clubName: club.name, currentTotal, country: club.countryName };
  $("#claim-title").textContent = `Apoyar a ${club.name}`;
  $("#claim-summary").innerHTML = `Acumulado actual: <strong>${fmt(currentTotal)}</strong> · baja del ranking mundial: ${["", "subes posiciones", "#"]}`;
  $("#claim-amount").value = Math.max(1, Math.ceil((currentTotal + 1) * 1) - currentTotal);
  $("#claim-message").value = "";
  $("#claim-email").value = "";
  updateClaimTotal();
  $("#modal-claim").classList.remove("hidden");
  $("#claim-amount").focus();
}

function updateClaimTotal() {
  const amount = Math.max(0, parseInt($("#claim-amount").value, 10) || 0);
  const hasMsg = $("#claim-message").value.trim().length > 0;
  $("#claim-total").textContent = fmt(amount + (hasMsg ? state.config.messagePriceUSD : 0));
  $("#claim-count").textContent = `${$("#claim-message").value.length}/${state.config.messageMaxChars}`;
}

async function submitClaim() {
  const amount = parseInt($("#claim-amount").value, 10);
  const message = $("#claim-message").value.trim();
  const email = $("#claim-email").value.trim();
  const hasMsg = message.length > 0;
  const payload = {
    clubId: claimCl.clubId,
    amountUSD: amount,
    message: hasMsg ? message : undefined,
    email: email || undefined
  };
  if (!hasMsg) delete payload.message;
  $("#claim-submit").disabled = true;
  $("#claim-submit").textContent = "Procesando…";
  try {
    const res = await api("/api/claims", { method: "POST", body: JSON.stringify(payload) });
    if (res.dev) {
      $("#modal-claim").classList.add("hidden");
      showSuccess(res.share, `Aplicado al instante (modo demo). Recaudado: ${fmt(res.order.amountUSD)}`);
      refreshBoard();
    } else {
      window.location.href = res.initPoint;
    }
  } catch (err) {
    toast(err.message, true);
  } finally {
    $("#claim-submit").disabled = false;
    $("#claim-submit").textContent = "Ir a pagar";
  }
}

function showSuccess(shareUrl, note) {
  $("#success-share").innerHTML = `<img src="${shareUrl}" alt="imagen compartible" />`;
  $("#share-download").href = shareUrl;
  $("#share-copy").onclick = () => {
    navigator.clipboard.writeText(location.origin + shareUrl);
    toast("Enlace copiado");
  };
  $("#success-note").textContent = note;
  $("#modal-success").classList.remove("hidden");
}

async function pollChat() {
  const room = state.chatRoom || (state.scope.startsWith("league:") ? state.scope.split(":")[1] : "liga-profesional");
  const url = `/api/chat/${room}/messages${state.lastChatTs ? `?since=${encodeURIComponent(state.lastChatTs)}` : ""}`;
  const data = await api(url).catch(() => null);
  if (!data) return;
  const box = $("#chat-messages");
  if (data.messages.length) {
    state.lastChatTs = data.messages[data.messages.length - 1].createdAt;
    for (const msg of data.messages) {
      box.insertAdjacentHTML("beforeend", chatMsgHtml(msg));
      box.scrollTop = box.scrollHeight;
    }
    if (box.children.length > 200) box.innerHTML = Array.from(box.children).slice(-200).map((c) => c.outerHTML).join("");
  }
}

function chatMsgHtml(msg) {
  const time = new Date(msg.createdAt).toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
  const who = msg.clubName ? `<img class="crest-mini" src="/api/crest/${msg.clubId}.svg" alt="" /> <span class="who">${msg.clubName}</span>` : `<span class="who">Hincha</span>`;
  return `<div class="chat-msg">
    ${msg.clubName ? `<img class="crest-mini" src="/api/crest/${msg.clubId}.svg" alt=""/>` : `<span class="crest-mini">⭑</span>`}
    <div><div>${who} <span class="ts">${time}</span></div><div class="txt">${msg.text.replace(/[<>&"]/g, "")}</div></div>
  </div>`;
}

async function refreshCredits() {
  if (!state.chatToken) {
    $("#credits-remaining").textContent = "";
    return;
  }
  const data = await api(`/api/chat/pack/${state.chatToken}`).catch(() => null);
  if (data) {
    state.chatRemaining = data.remaining;
    $("#credits-remaining").textContent = `· te quedan ${data.remaining} mensajes`;
  }
}

async function sendChat(e) {
  e.preventDefault();
  const text = $("#chat-input").value.trim();
  if (!text) return;
  if (!state.chatToken) {
    $("#modal-pack").classList.remove("hidden");
    return;
  }
  try {
    const room = state.chatRoom || (state.scope.startsWith("league:") ? state.scope.split(":")[1] : "liga-profesional");
    const res = await api(`/api/chat/${room}/send`, {
      method: "POST",
      body: JSON.stringify({ token: state.chatToken, text })
    });
    $("#chat-input").value = "";
    state.lastChatTs = res.message.createdAt;
    const box = $("#chat-messages");
    box.insertAdjacentHTML("beforeend", chatMsgHtml(res.message));
    box.scrollTop = box.scrollHeight;
    state.chatRemaining = res.remaining;
    $("#credits-remaining").textContent = `· te quedan ${res.remaining} mensajes`;
  } catch (err) {
    toast(err.message, true);
    if (err.status === 402) $("#modal-pack").classList.remove("hidden");
  }
}

async function buyPack() {
  const email = $("#pack-email").value.trim();
  try {
    const res = await api("/api/chat/pack", { method: "POST", body: JSON.stringify({ email: email || undefined }) });
    $("#modal-pack").classList.add("hidden");
    if (res.dev) {
      state.chatToken = res.token;
      localStorage.setItem("hb_token", res.token);
      state.chatRemaining = res.remaining;
      $("#credits-remaining").textContent = `· te quedan ${res.remaining} mensajes (demo)`;
      toast("Paquete activado");
    } else {
      sessionStorage.setItem("hb_pending_pack", res.token);
      window.location.href = res.initPoint;
    }
  } catch (err) {
    toast(err.message, true);
  }
}

async function handleOrderReturn() {
  const params = new URLSearchParams(location.search);
  const orderId = params.get("order");
  if (!orderId) return;
  for (let i = 0; i < 40; i++) {
    const order = await api(`/api/orders/${orderId}`).catch(() => null);
    if (order?.status === "paid") {
      if (order.type === "chat_pack") {
        state.chatToken = sessionStorage.getItem("hb_pending_pack") || order.token;
        localStorage.setItem("hb_token", state.chatToken);
        toast("Paquete de chat activado");
        refreshCredits();
      } else {
        toast("¡Pago confirmado! Actualizando ranking…");
        showSuccess(`/api/share/${order.clubId}.svg`, "Tu apoyo ya está en el board.");
        refreshBoard();
      }
      history.replaceState(null, "", location.pathname);
      return;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
}

async function handleFailedReturn() {
  const params = new URLSearchParams(location.search);
  if (params.get("failed")) toast("Pago cancelado o fallido", true);
  if (params.get("pending")) toast("Pago pendiente de confirmación");
  if (params.get("failed") || params.get("pending") || params.get("order")) {
    history.replaceState(null, "", location.pathname);
  }
}

async function refreshStats() {
  const s = await api("/api/stats").catch(() => null);
  if (!s) return;
  $("#stat-revenue").textContent = fmt(s.revenueUSD);
  $("#stat-bids").textContent = s.bids.toLocaleString("en-US");
  $("#stat-clubs").textContent = s.clubs.toLocaleString("en-US");
}

function init() {
  $("#country-select").addEventListener("change", (e) => {
    if (e.target.value) setView("board", `country:${e.target.value}`);
  });
  $("#league-select").addEventListener("change", (e) => {
    if (e.target.value) setView("board", `league:${e.target.value}`);
  });
  $$(".tab").forEach((t) => {
    if (t.dataset.tab === "chat") {
      t.addEventListener("click", () => setView("chat") && refreshCredits());
    } else if (t.dataset.scope) {
      t.addEventListener("click", () => setView("board", "global"));
    }
  });
  $$(".modal-close").forEach((b) => b.addEventListener("click", () => $("#" + b.dataset.close).classList.add("hidden")));
  $$(".modal").forEach((m) => m.addEventListener("click", (e) => { if (e.target === m) m.classList.add("hidden"); }));
  $("#claim-amount").addEventListener("input", updateClaimTotal);
  $("#claim-message").addEventListener("input", updateClaimTotal);
  $("#claim-submit").addEventListener("click", submitClaim);
  $("#chat-form").addEventListener("submit", sendChat);
  $("#buy-pack-btn").addEventListener("click", () => $("#modal-pack").classList.remove("hidden"));
  $("#pack-submit").addEventListener("click", buyPack);
  $("#open-info").addEventListener("click", (e) => {
    e.preventDefault();
    toast("Compras apoyos: $1 mínimo, enteros. Más $ acumulado = mejor rank. El mensaje destacado cuesta $2 y se muestra 72h junto al club.");
  });
  loadMeta()
    .then(() => refreshBoard())
    .then(() => runPollers())
    .catch((err) => toast(err.message, true));
  refreshStats();
  setInterval(refreshStats, 10000);
  handleFailedReturn();
  if (new URLSearchParams(location.search).get("order")) handleOrderReturn();
}

init();
