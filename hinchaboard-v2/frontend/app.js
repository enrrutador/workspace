/**
 * app.js — Hinchaboard index page: live ticker, podium, TWO independent
 * ranked tables (country ranking + world ranking), push form with scope and
 * message, activity feed, fan chat ("La Tribuna"), club showcase carousels
 * and Hall of Fame. Pure frontend; no build step.
 * Preview mode: if window.__HINCHABOARD__ is set, it is used instead of the
 * API and live activity is simulated.
 */
"use strict";

const $ = (id) => document.getElementById(id);
const PREVIEW = window.__HINCHABOARD__ || null;

const STRINGS = {
  en: {
    tickerLabel: "LIVE", brandSub: "THE FANS' RANKING",
    season: "SEASON", endsIn: "ends in",
    headline: "The ranking the fans decide.",
    sub: "Every dollar is a push. Push from $1, lift your club, and the club on top when the year ends stays in the Hall of Fame forever.",
    statPool: "TOTAL PUSHED", statPushes: "FAN PUSHES", statClubs: "CLUBS RANKED", statListed: "CLUBS LISTED",
    rules: "Minimum push <strong>$1</strong> · Pushes pool into your club's total · Pass the club above by <strong>$1 or more</strong> · <strong>Two separate competitions</strong>: country and world",
    podiumGlobal: "Top of the world", podiumCountry: "Top of {country}", boardTitle: "The table",
    scopeGlobal: "World ranking", scopeCountry: "By country",
    scopeNote: "Two separate competitions — pushes in one never move the other.",
    boardEmpty: "No pushes yet here — the first fan puts their club on top for $1.",
    pushTitle: "Push your club", fLeague: "League", fClub: "Club",
    fFan: "Your fan name (optional)", fMessage: "Message next to your club (optional)",
    fMessagePh: "Say it loud — rivals will read it", fAmount: "Your push (USD)", pushBtn: "Push now",
    formScope: "Where does your push count?", formScopeCountry: "Club's country", formScopeGlobal: "The world",
    formCountsGlobal: "Counts only for the world ranking.",
    formCountsCountry: "Counts only for the {country} ranking.",
    firstPushHint: "The first push puts your club on top of this ranking for $1.",
    feedTitle: "Live from the stands",
    chatTitle: "La Tribuna — fan chat", cFanPh: "Your fan name", cTextPh: "Talk to the stands…", chatSend: "Send",
    chatBalance: "Messages: {n}", chatNoCredit: "You're out of messages. Add credit to keep chatting.",
    creditBtn: "Add messages", creditNote: "USD 1 = 3 messages. Chat credit is separate from the rankings.",
    creditPreview: "Preview: {n} messages added locally.", creditErr: "Could not start the credit purchase.",
    creditStart: "Opening checkout…",
    showTitle: "Every club. Every league.",
    showSub: "405 clubs across Latin America, the MLS and Europe — listed free, forever. The ranked tables above are where the fans fight.",
    hofTitle: "Hall of Fame",
    hofText: "When the season ends, the world champion and the champion of every country enter here and stay forever. The first class is crowned on December 31.",
    hofWorld: "World Champion", hofCountries: "Country champions", hofTbd: "Crowned Dec 31",
    footer: "Transparent fan ranking — every push is public. Seasons run January 1 to December 31; champions are forever.",
    scopeTagGlobal: "🌍 World",
    pushesWord: "pushes", needWord: "needs", toPass: "to pass",
    moreBtn: "Show more", lessBtn: "Show less",
    projected: "With this push:",
    projectLead: "your club takes the lead here",
    projectPos: "your club reaches #{pos}",
    projectNeed: "{amount} more to pass {club}",
    errAmount: "Minimum push is $1.00.", errClub: "Pick your club first.",
    errScope: "That club belongs to another country ranking. Use the world ranking to push it.",
    previewOk: "Preview mode: your push would be sent to checkout. Payments are not live yet.",
    chatErr: "Could not send. Try again in a bit.", anonymous: "A fan",
    regions: { latam: "Latin America", usa: "United States · MLS", europe: "Europe" },
    yourClubTop: "Your club is on top here — defend it!",
  },
  es: {
    tickerLabel: "EN VIVO", brandSub: "EL RANKING DE LOS HINCHAS",
    season: "TEMPORADA", endsIn: "cierra en",
    headline: "El ranking que deciden los hinchas.",
    sub: "Cada dólar es un empuje. Empujá desde USD 1, hacé subir a tu club, y el club que cierra el año arriba queda en el Salón de la Fama para siempre.",
    statPool: "TOTAL EMPUJADO", statPushes: "EMPUJES", statClubs: "CLUBES EN TABLAS", statListed: "CLUBES LISTADOS",
    rules: "Empuje mínimo <strong>$1</strong> · Los empujes se suman al total de tu club · Superá al de arriba por <strong>$1 o más</strong> · <strong>Dos competencias separadas</strong>: país y mundo",
    podiumGlobal: "La cima del mundo", podiumCountry: "La cima de {country}", boardTitle: "La tabla",
    scopeGlobal: "Ranking mundial", scopeCountry: "Por país",
    scopeNote: "Dos competencias separadas: los empujes de una no mueven la otra.",
    boardEmpty: "Todavía no hay empujes acá: el primer hincha pone a su club arriba por USD 1.",
    pushTitle: "Empujá a tu club", fLeague: "Liga", fClub: "Club",
    fFan: "Tu nombre de hincha (opcional)", fMessage: "Mensaje junto a tu club (opcional)",
    fMessagePh: "Decilo fuerte: lo leen los rivales", fAmount: "Tu empuje (USD)", pushBtn: "Empujar ahora",
    formScope: "¿Dónde cuenta tu empuje?", formScopeCountry: "País del club", formScopeGlobal: "El mundo",
    formCountsGlobal: "Cuenta solo para el ranking mundial.",
    formCountsCountry: "Cuenta solo para el ranking de {country}.",
    firstPushHint: "El primer empuje pone a tu club arriba de este ranking por USD 1.",
    feedTitle: "En vivo desde la tribuna",
    chatTitle: "La Tribuna — chat de hinchas", cFanPh: "Tu nombre de hincha", cTextPh: "Hablale a la tribuna…", chatSend: "Enviar",
    chatBalance: "Mensajes: {n}", chatNoCredit: "Te quedaste sin mensajes. Cargá crédito para seguir hablando.",
    creditBtn: "Cargar mensajes", creditNote: "USD 1 = 3 mensajes. El crédito del chat va aparte de los rankings.",
    creditPreview: "Vista previa: {n} mensajes cargados localmente.", creditErr: "No se pudo iniciar la compra de mensajes.",
    creditStart: "Abriendo el pago…",
    showTitle: "Todos los clubes. Todas las ligas.",
    showSub: "405 clubes de América Latina, la MLS y Europa: listados gratis, para siempre. Las tablas de arriba son donde pelean los hinchas.",
    hofTitle: "Salón de la Fama",
    hofText: "Cuando cierra la temporada, el campeón mundial y el campeón de cada país entran acá y se quedan para siempre. La primera camada se corona el 31 de diciembre.",
    hofWorld: "Campeón mundial", hofCountries: "Campeones de cada país", hofTbd: "Se corona el 31/12",
    footer: "Ranking de hinchas transparente: cada empuje es público. Las temporadas van del 1 de enero al 31 de diciembre; los campeones son para siempre.",
    scopeTagGlobal: "🌍 Mundial",
    pushesWord: "empujes", needWord: "necesita", toPass: "para pasar a",
    moreBtn: "Ver más", lessBtn: "Ver menos",
    projected: "Con este empuje:",
    projectLead: "tu club queda puntero acá",
    projectPos: "tu club llega al puesto #{pos}",
    projectNeed: "faltan {amount} para pasar a {club}",
    errAmount: "El empuje mínimo es $1.00.", errClub: "Elegí tu club primero.",
    errScope: "Ese club pertenece al ranking de otro país. Para empujarlo usá el ranking mundial.",
    previewOk: "Vista previa: tu empuje iría al pago. Los pagos todavía no están activos.",
    chatErr: "No se pudo enviar. Probá en un rato.", anonymous: "Un hincha",
    regions: { latam: "América Latina", usa: "Estados Unidos · MLS", europe: "Europa" },
    yourClubTop: "Tu club está arriba acá: ¡a defenderlo!",
  },
};

const defaultLang = () => {
  const stored = localStorage.getItem("hinchaboard-lang");
  if (stored === "en" || stored === "es") return stored;
  return String(navigator.language || "en").toLowerCase().startsWith("es") ? "es" : "en";
};

const state = {
  lang: defaultLang(),
  viewScope: "global",   // board view: "global" | "country"
  country: "arg",        // selected country tab (league id = country key)
  formScope: "country",  // where the form's push counts
  clubs: [], leagues: [], clubById: new Map(), leagueById: new Map(),
  boards: new Map(), statsByScope: new Map(),
  activity: [], chat: [], flashClub: null,
  boardExpanded: false,
  wallet: "", balance: 0,
};
const S = () => STRINGS[state.lang];
const money = (v) => "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (tpl, vars) => Object.entries(vars).reduce((out, [k, v]) => out.replaceAll(`{${k}}`, v), tpl);

const WALLET_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function ensureWallet() {
  let id = localStorage.getItem("hinchaboard-wallet");
  if (id && WALLET_RE.test(id)) return id;
  id = globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID()
    : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      });
  localStorage.setItem("hinchaboard-wallet", id);
  return id;
}

/* ---------- shields ---------- */
function textOn(hex) {
  const h = String(hex || "#444").replace("#", "");
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.62 ? "#10160f" : "#ffffff";
}
function shield(club, size = 46) {
  if (!club) return "";
  const h = Math.round(size * 1.12);
  return `<svg class="shield" width="${size}" height="${h}" viewBox="0 0 48 54" aria-hidden="true">
    <path d="M24 2 L44 8 V27 C44 41 36 48.5 24 52 C12 48.5 4 41 4 27 V8 Z" fill="${esc(club.color)}" stroke="rgba(255,255,255,.4)" stroke-width="1.6"/>
    <text x="24" y="33" text-anchor="middle" font-family="Oswald, sans-serif" font-weight="700" font-size="12.5" fill="${textOn(club.color)}">${esc(club.short)}</text>
  </svg>`;
}
const clubOf = (id) => state.clubById.get(id);
const leagueOf = (id) => state.leagueById.get(id);
const countryName = (leagueId) => {
  const l = leagueOf(leagueId);
  if (!l) return leagueId;
  return state.lang === "es" ? l.country_es : l.country_en;
};
const leagueName = (l) => (state.lang === "es" ? l.name_es : l.name_en);
const leagueLabel = (id) => {
  const l = leagueOf(id);
  return l ? `${leagueName(l)} · ${countryName(id)}` : id;
};
const scopeTag = (scope) => scope === "global" ? S().scopeTagGlobal : countryName(scope);
const countriesSorted = () => [...state.leagues].sort((a, b) => countryName(a.id).localeCompare(countryName(b.id), state.lang));
const currentScope = () => state.viewScope === "global" ? "global" : state.country;
const formCountry = () => $("fLeague").value || state.country;
const formScope = () => state.formScope === "global" ? "global" : formCountry();
const statsFor = (scope) => state.statsByScope.get(scope) || { totalPushed: 0, totalPushes: 0, clubsRanked: 0 };
const boardFor = (scope) => state.boards.get(scope) || [];

/* ---------- countdown ---------- */
function startCountdown() {
  const now = new Date();
  $("seasonYear").textContent = now.getFullYear();
  const end = new Date(now.getFullYear(), 11, 31, 23, 59, 59);
  const tick = () => {
    let diff = Math.max(0, end - new Date());
    const d = Math.floor(diff / 864e5); diff -= d * 864e5;
    const h = Math.floor(diff / 36e5); diff -= h * 36e5;
    const m = Math.floor(diff / 6e4); const s = Math.floor((diff - m * 6e4) / 1e3);
    $("countdown").textContent = `${d}d ${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };
  tick(); setInterval(tick, 1000);
}

/* ---------- count-up ---------- */
function countUp(el, to, prefix = "") {
  const from = 0, t0 = performance.now(), dur = 1100;
  const step = (t) => {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + Math.round(from + (to - from) * e).toLocaleString("en-US");
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ---------- renders ---------- */
function renderScopeButtons() {
  $("boardScopeGlobal").classList.toggle("active", state.viewScope === "global");
  $("boardScopeCountry").classList.toggle("active", state.viewScope === "country");
  $("fScopeCountry").classList.toggle("active", state.formScope === "country");
  $("fScopeGlobal").classList.toggle("active", state.formScope === "global");
}

function renderTicker() {
  const items = state.activity.length
    ? state.activity.map((a) => {
      const c = clubOf(a.club);
      return c ? `<span class="tick">⚽ <b>${esc(c.name)}</b> <span class="up">+${money(a.amount)}</span> · ${esc(scopeTag(a.scope))}${a.fan ? ` · ${esc(a.fan)}` : ""}</span>` : "";
    }).join("")
    : boardFor(currentScope()).map((r) => {
      const c = clubOf(r.club);
      return c ? `<span class="tick">🏆 <b>${esc(c.name)}</b> ${money(r.total)}</span>` : "";
    }).join("");
  $("tickerTrack").innerHTML = items + items; // duplicate for a seamless loop
}

function renderStats(animate = true) {
  const st = statsFor(currentScope());
  if (animate) {
    countUp($("statPool"), st.totalPushed, "$");
    countUp($("statPushes"), st.totalPushes);
    countUp($("statClubs"), st.clubsRanked);
    countUp($("statListed"), state.clubs.length);
  } else {
    $("statPool").textContent = money(st.totalPushed);
    $("statPushes").textContent = st.totalPushes.toLocaleString("en-US");
    $("statClubs").textContent = st.clubsRanked;
    $("statListed").textContent = state.clubs.length;
  }
}

function renderTitles() {
  const isGlobal = state.viewScope === "global";
  $("podiumTitle").textContent = isGlobal
    ? S().podiumGlobal
    : fmt(S().podiumCountry, { country: countryName(state.country) });
  $("boardTitle").textContent = S().boardTitle;
}

function renderPodium() {
  const board = boardFor(currentScope());
  const top = board.slice(0, 3);
  const order = [top[1], top[0], top[2]].filter(Boolean); // 2nd, 1st, 3rd
  $("podium").innerHTML = order.map((r) => {
    const c = clubOf(r.club); if (!c) return "";
    const cls = r.position === 1 ? "pod-1" : r.position === 2 ? "pod-2" : "pod-3";
    return `<div class="pod ${cls}">
      ${r.position === 1 ? '<span class="crown">👑</span>' : ""}
      ${shield(c, 56)}
      <div class="pod-name">${esc(c.name)}</div>
      <div class="pod-league">${esc(leagueLabel(r.league))}</div>
      <div class="pod-total">${money(r.total)}</div>
      <div class="pod-bar"><div class="pod-pos">#${r.position}</div></div>
    </div>`;
  }).join("");
}

function renderTabs() {
  $("leagueTabs").hidden = state.viewScope !== "country";
  $("leagueTabs").innerHTML = countriesSorted().map((l) =>
    `<button type="button" class="tab${state.country === l.id ? " active" : ""}" data-country="${l.id}">${esc(countryName(l.id))}</button>`).join("");
  $("leagueTabs").querySelectorAll(".tab").forEach((b) =>
    b.addEventListener("click", () => selectCountry(b.dataset.country)));
}

function renderBoard() {
  const rows = boardFor(currentScope());
  const leaderTotal = rows.length ? rows[0].total : 0;
  const limit = state.boardExpanded ? rows.length : 20;
  $("boardEmpty").hidden = rows.length > 0;
  $("board").innerHTML = rows.slice(0, limit).map((r, i) => {
    const c = clubOf(r.club); if (!c) return "";
    const above = rows[i - 1];
    const need = above ? Math.max(0, Math.round((above.total + 1 - r.total) * 100) / 100) : 0;
    const pct = leaderTotal > 0 ? Math.max(5, Math.round((r.total / leaderTotal) * 100)) : 0;
    const posCls = r.position <= 3 ? ` p${r.position}` : "";
    return `<div class="row${r.position === 1 ? " top1" : ""}${r.position === 2 ? " top2" : ""}${r.position === 3 ? " top3" : ""}${posCls}${state.flashClub === r.club ? " flash" : ""}" style="--club:${esc(c.color)}; --w:${pct}%; animation-delay:${Math.min(i * 45, 500)}ms">
      <div class="pos">${r.position}</div>
      <div class="row-shield">${shield(c, 46)}</div>
      <div class="row-main">
        <div class="club-name">${esc(c.name)}</div>
        <div class="club-meta">${esc(leagueLabel(r.league))} · ${r.pushes} ${S().pushesWord}</div>
      </div>
      <div class="board-nums">
        <div class="board-total">${money(r.total)}</div>
        ${above ? `<div class="board-need">${S().needWord} ${money(need)} ${S().toPass} ${esc(clubOf(above.club)?.name || "")}</div>` : ""}
      </div>
      ${r.shout ? `<div class="row-shout"><span class="shout">💬 “${esc(r.shout.text)}”${r.shout.fan ? ` — <span class="shout-fan">${esc(r.shout.fan)}</span>` : ""}</span></div>` : ""}
    </div>`;
  }).join("");
  const more = $("boardMore");
  more.hidden = rows.length <= 20;
  more.setAttribute("aria-expanded", String(state.boardExpanded));
  const remaining = Math.max(0, rows.length - 20);
  more.textContent = state.boardExpanded ? S().lessBtn : `${S().moreBtn} (${remaining})`;
}

function renderFeed() {
  $("feed").innerHTML = state.activity.slice(0, 12).map((a) => {
    const c = clubOf(a.club); if (!c) return "";
    return `<li>${shield(c, 30)}<div><b>${esc(c.name)}</b> <span class="feed-amt">+${money(a.amount)}</span>
      <span class="feed-fan"> · ${esc(scopeTag(a.scope))}${a.fan ? ` · ${esc(a.fan)}` : ""}</span>
      ${a.message ? `<div class="feed-msg">“${esc(a.message)}”</div>` : ""}</div></li>`;
  }).join("") || `<li class="muted">—</li>`;
}

function renderRows() {
  const regions = ["latam", "usa", "europe"];
  $("rows").innerHTML = regions.map((region, ri) => {
    const clubs = state.clubs.filter((c) => leagueOf(c.league)?.region === region);
    const chips = clubs.map((c) => `<span class="chip-club">${shield(c, 30)} ${esc(c.name)}</span>`).join("");
    const dur = Math.max(40, clubs.length * 1.1);
    return `<div class="row-label">${esc(S().regions[region])} · ${clubs.length}</div>
      <div class="carousel${ri % 2 ? " rev" : ""}"><div class="carousel-track" style="--dur:${dur}s">${chips}${chips}</div></div>`;
  }).join("");
}

function renderHof() {
  const slots = [
    { icon: "🌍🏆", label: S().hofWorld },
    { icon: "🏆", label: S().hofCountries },
  ];
  $("hofCards").innerHTML = slots.map((s) =>
    `<div class="hof-card"><div class="laurel">🌿🏆🌿</div><div class="hof-slot">${esc(s.label)}</div><div class="hof-tbd">${esc(S().hofTbd)}</div></div>`).join("");
}

function renderWallet() {
  const el = $("chatBalance");
  if (el) el.textContent = fmt(S().chatBalance, { n: String(state.balance) });
}

function renderChat() {
  $("chatMsgs").innerHTML = [...state.chat].reverse().map((m) => {
    const c = m.club ? clubOf(m.club) : null;
    return `<li>${c ? shield(c, 26) : '<span style="width:26px;text-align:center">💬</span>'}
      <div class="chat-body"><span class="chat-fan">${esc(m.fan || S().anonymous)}</span>
      ${c ? `<span class="chat-club"> · ${esc(c.name)}</span>` : ""}<br>${esc(m.text)}</div></li>`;
  }).join("");
  const box = $("chatMsgs"); box.scrollTop = box.scrollHeight;
}

/* ---------- board scope ---------- */
async function loadBoard(scope) {
  if (state.boards.has(scope)) return state.boards.get(scope);
  if (PREVIEW) {
    state.boards.set(scope, PREVIEW.boards?.[scope] || []);
    if (PREVIEW.statsByScope?.[scope]) state.statsByScope.set(scope, PREVIEW.statsByScope[scope]);
    return boardFor(scope);
  }
  const d = await fetch(`/api/board?scope=${encodeURIComponent(scope)}`).then((r) => r.json());
  if (!d.ok) throw new Error(d.error || "BOARD_ERROR");
  state.boards.set(scope, d.board || []);
  state.statsByScope.set(scope, d.stats || statsFor(scope));
  if (d.activity) state.activity = d.activity;
  return boardFor(scope);
}

async function refreshBoardView() {
  renderScopeButtons();
  renderTabs();
  renderTitles();
  try { await loadBoard(currentScope()); } catch { /* keep empty board */ }
  renderPodium();
  renderBoard();
  renderStats(false);
  renderTicker();
  renderFeed();
}

async function selectBoardScope(view) {
  state.viewScope = view;
  state.boardExpanded = false;
  await refreshBoardView();
}

async function selectCountry(country) {
  state.country = country;
  state.viewScope = "country";
  state.boardExpanded = false;
  if ([...$("fLeague").options].some((o) => o.value === country)) {
    $("fLeague").value = country;
    fillClubSelect();
  }
  await refreshBoardView();
}

/* ---------- form ---------- */
function fillFormSelects() {
  const previous = $("fLeague").value || state.country;
  $("fLeague").innerHTML = countriesSorted().map((l) =>
    `<option value="${l.id}">${esc(leagueName(l))} (${esc(countryName(l.id))})</option>`).join("");
  if ([...$("fLeague").options].some((o) => o.value === previous)) $("fLeague").value = previous;
  fillClubSelect();
  // chat club select: all clubs grouped by country
  $("cClub").innerHTML = `<option value="">—</option>` + countriesSorted().map((l) =>
    `<optgroup label="${esc(countryName(l.id))}">${state.clubs.filter((c) => c.league === l.id)
      .map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</optgroup>`).join("");
}

function fillClubSelect() {
  const league = $("fLeague").value;
  const previous = $("fClub").value;
  const pool = state.clubs.filter((c) => c.league === league);
  $("fClub").innerHTML = pool.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  if (pool.some((c) => c.id === previous)) $("fClub").value = previous;
  updateFormScopeNote();
  updateHint();
}

function updateFormScopeNote() {
  $("formScopeNote").textContent = state.formScope === "global"
    ? S().formCountsGlobal
    : fmt(S().formCountsCountry, { country: countryName(formCountry()) });
}

async function updateHint() {
  const clubId = $("fClub").value;
  const scope = formScope();
  const amount = Number($("fAmount").value) || 0;
  const hint = $("pushHint");
  if (!clubId) { hint.textContent = ""; return; }
  try { await loadBoard(scope); } catch { /* offline */ }
  const rows = boardFor(scope);
  const c = clubOf(clubId);
  if (!c) { hint.textContent = ""; return; }
  if (!rows.length) { hint.textContent = S().firstPushHint; return; }
  const mine = rows.find((r) => r.club === clubId);
  const myTotal = (mine?.total || 0) + amount;
  const leader = rows[0];
  if (amount <= 0) {
    hint.textContent = leader && leader.club !== clubId
      ? `${c.name}: ${S().needWord} ${money(Math.round((leader.total + 1 - (mine?.total || 0)) * 100) / 100)} ${S().toPass} ${clubOf(leader.club)?.name || ""}`
      : S().yourClubTop;
    return;
  }
  const aboveMe = rows.filter((r) => r.club !== clubId && r.total >= myTotal).sort((a, b) => a.total - b.total)[0];
  if (!aboveMe) {
    hint.textContent = `${S().projected} ${S().projectLead}`;
  } else {
    hint.textContent = `${S().projected} ${fmt(S().projectPos, { pos: String(rows.filter((r) => r.club !== clubId && r.total >= myTotal).length + 1) })} · ${fmt(S().projectNeed, { amount: money(Math.round((aboveMe.total + 1 - myTotal) * 100) / 100), club: clubOf(aboveMe.club)?.name || "" })}`;
  }
}

/* ---------- i18n ---------- */
function applyLang() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { const k = el.dataset.i18n; if (S()[k]) el.textContent = S()[k]; });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => { const k = el.dataset.i18nHtml; if (S()[k]) el.innerHTML = S()[k]; });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => { const k = el.dataset.i18nPh; if (S()[k]) el.placeholder = S()[k]; });
  document.querySelectorAll(".lang-switch button").forEach((b) => b.classList.toggle("active", b.dataset.lang === state.lang));
  renderWallet(); renderScopeButtons(); renderTitles(); renderTabs(); renderBoard(); renderFeed(); renderTicker(); renderRows(); renderHof(); renderChat(); fillFormSelects(); renderStats(false);
}

/* ---------- data ---------- */
async function loadAll() {
  if (PREVIEW) {
    state.clubs = PREVIEW.clubs.clubs; state.leagues = PREVIEW.clubs.leagues;
    state.activity = PREVIEW.activity || [];
    state.chat = PREVIEW.chat || [];
    state.boards = new Map(Object.entries(PREVIEW.boards || {}));
    state.statsByScope = new Map(Object.entries(PREVIEW.statsByScope || {}));
    state.balance = 3;
  } else {
    const [clubsRes, chatRes, walletRes] = await Promise.all([
      fetch("clubs.json").then((r) => r.json()),
      fetch("/api/chat").then((r) => r.json()).catch(() => ({ messages: [] })),
      fetch(`/api/chat/wallet?wallet=${encodeURIComponent(state.wallet)}`)
        .then((r) => r.json()).catch(() => null),
    ]);
    state.clubs = clubsRes.clubs; state.leagues = clubsRes.leagues;
    state.chat = chatRes.messages || [];
    if (walletRes?.ok) state.balance = walletRes.balance;
  }
  state.clubById = new Map(state.clubs.map((c) => [c.id, c]));
  state.leagueById = new Map(state.leagues.map((l) => [l.id, l]));
}

async function pollChat() {
  if (PREVIEW) return;
  try {
    const d = await fetch("/api/chat").then((r) => r.json());
    if (JSON.stringify(d.messages) !== JSON.stringify(state.chat)) { state.chat = d.messages || []; renderChat(); }
  } catch { /* offline: keep current */ }
}

/* ---------- preview simulation ---------- */
const SIM_FANS = ["El Diez", "La12Tw", "SebaMillonario", "AnaBanana", "TorcedorBR", "MikeMLS", "Gunner4Life", "Culé1899", "Xeneize12", "GarotoSP"];
const SIM_MSGS = {
  en: ["This year is ours.", "Rivals, read it and weep.", "From the stands, always.", "One dollar at a time, to the top."],
  es: ["Este año es nuestro.", "Rivales, léanlo y lloren.", "Desde la tribuna, siempre.", "De a un dólar, hasta la cima."],
};
function simulate() {
  const scope = currentScope();
  const board = boardFor(scope);
  if (!board.length) return;
  const pick = board[Math.floor(Math.random() * Math.min(board.length, 14))];
  const amount = 1 + Math.floor(Math.random() * 15);
  const fan = SIM_FANS[Math.floor(Math.random() * SIM_FANS.length)];
  const msg = Math.random() < 0.45 ? SIM_MSGS[state.lang][Math.floor(Math.random() * 4)] : "";
  const entry = board.find((r) => r.club === pick.club);
  entry.total = Math.round((entry.total + amount) * 100) / 100; entry.pushes += 1;
  if (msg) entry.shout = { text: msg, fan, at: Date.now() };
  board.sort((a, b) => b.total - a.total || a.firstAt - b.firstAt);
  board.forEach((r, i) => { r.position = i + 1; });
  state.activity.unshift({ club: pick.club, league: pick.league, scope, amount, fan, message: msg, at: Date.now() });
  state.activity = state.activity.slice(0, 30);
  const st = statsFor(scope);
  state.statsByScope.set(scope, {
    totalPushed: Math.round((st.totalPushed + amount) * 100) / 100,
    totalPushes: st.totalPushes + 1,
    clubsRanked: st.clubsRanked || board.length,
  });
  state.flashClub = pick.club;
  renderTicker(); renderStats(false); renderPodium(); renderBoard(); renderFeed();
  setTimeout(() => { state.flashClub = null; }, 1300);
}

/* ---------- events ---------- */
function wire() {
  document.querySelectorAll(".lang-switch button").forEach((b) =>
    b.addEventListener("click", () => { state.lang = b.dataset.lang; localStorage.setItem("hinchaboard-lang", state.lang); applyLang(); }));
  $("boardScopeGlobal").addEventListener("click", () => selectBoardScope("global"));
  $("boardScopeCountry").addEventListener("click", () => selectBoardScope("country"));
  $("boardMore").addEventListener("click", () => {
    state.boardExpanded = !state.boardExpanded;
    $("boardMore").setAttribute("aria-expanded", String(state.boardExpanded));
    renderBoard();
  });
  $("fScopeCountry").addEventListener("click", () => {
    state.formScope = "country"; renderScopeButtons(); updateFormScopeNote(); updateHint();
  });
  $("fScopeGlobal").addEventListener("click", () => {
    state.formScope = "global"; renderScopeButtons(); updateFormScopeNote(); updateHint();
  });
  $("fLeague").addEventListener("change", fillClubSelect);
  $("fClub").addEventListener("change", updateHint);
  $("fAmount").addEventListener("input", updateHint);

  $("pushForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("formMsg"); msg.textContent = ""; msg.className = "form-msg";
    const scope = formScope();
    const club = $("fClub").value, amount = Number($("fAmount").value);
    if (!club) { msg.textContent = S().errClub; return; }
    if (!Number.isFinite(amount) || amount < 1) { msg.textContent = S().errAmount; return; }
    const payload = { scope, club, amount, fan: $("fFan").value, message: $("fMessage").value };
    if (PREVIEW) { msg.textContent = S().previewOk; msg.classList.add("ok"); return; }
    try {
      const r = await fetch("/api/pushes", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
      const d = await r.json();
      if (!d.ok) {
        msg.textContent = d.error === "AMOUNT_TOO_LOW" ? S().errAmount
          : d.error === "SCOPE_MISMATCH" ? S().errScope
          : d.error;
        return;
      }
      window.location.href = d.payUrl;
    } catch { msg.textContent = "Network error."; }
  });

  $("creditBtn").addEventListener("click", () => {
    $("creditPanel").hidden = !$("creditPanel").hidden;
  });
  document.querySelectorAll("#creditPanel [data-amount]").forEach((b) =>
    b.addEventListener("click", () => startCredit(Number(b.dataset.amount))));

  $("chatForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("chatMsg"); msg.textContent = ""; msg.className = "form-msg";
    const payload = { wallet: state.wallet, fan: $("cFan").value, club: $("cClub").value || null, text: $("cText").value };
    if (!payload.text.trim()) return;
    if (state.balance < 1) {
      msg.textContent = S().chatNoCredit;
      $("creditPanel").hidden = false;
      return;
    }
    if (PREVIEW) {
      state.balance -= 1;
      state.chat.unshift({ fan: payload.fan, club: payload.club, text: payload.text, at: Date.now() });
      state.chat = state.chat.slice(0, 50);
      $("cText").value = ""; renderChat(); renderWallet(); return;
    }
    try {
      const r = await fetch("/api/chat", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
      const d = await r.json();
      if (!d.ok) {
        msg.textContent = d.error === "NO_CHAT_CREDIT" ? S().chatNoCredit : S().chatErr;
        if (d.error === "NO_CHAT_CREDIT") $("creditPanel").hidden = false;
        return;
      }
      state.balance = d.balance;
      $("cText").value = "";
      state.chat.unshift(d.message); renderChat(); renderWallet();
    } catch { msg.textContent = S().chatErr; }
  });
}

async function startCredit(amount) {
  const msg = $("chatMsg"); msg.textContent = ""; msg.className = "form-msg";
  if (PREVIEW) {
    const added = Math.floor(amount * 3);
    state.balance += added; renderWallet();
    msg.textContent = fmt(S().creditPreview, { n: String(added) }); msg.classList.add("ok");
    $("creditPanel").hidden = true;
    return;
  }
  msg.textContent = S().creditStart;
  try {
    const r = await fetch("/api/chat/credits", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ wallet: state.wallet, amount }),
    });
    const d = await r.json();
    if (!d.ok) { msg.textContent = S().creditErr; return; }
    window.location.href = d.payUrl;
  } catch { msg.textContent = S().creditErr; }
}

/* ---------- init ---------- */
(async function init() {
  state.wallet = ensureWallet();
  await loadAll();
  startCountdown();
  applyLang();
  await selectBoardScope("global");
  renderStats(true);
  wire();
  if (PREVIEW) setInterval(simulate, 8000);
  else setInterval(pollChat, 15000);
})();
