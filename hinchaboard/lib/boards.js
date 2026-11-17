const { CONFIG } = require("./pricing");
const { getDb } = require("./db");

function clubTotals() {
  const d = getDb();
  const totals = new Map();
  for (const bid of d.bids) {
    if (bid.status === "refunded") continue;
    const entry = totals.get(bid.clubId) || { total: 0, firstPaidAt: bid.createdAt };
    entry.total += bid.usd;
    if (bid.createdAt < entry.firstPaidAt) entry.firstPaidAt = bid.createdAt;
    totals.set(bid.clubId, entry);
  }
  return totals;
}

function activeMessage(clubId, now = Date.now()) {
  const d = getDb();
  let latest = null;
  for (const m of d.messages) {
    if (m.clubId !== clubId) continue;
    const expires = new Date(m.paidAt).getTime() + CONFIG.MESSAGE_TTL_HOURS * 3600 * 1000;
    if (expires < now) continue;
    if (!latest || m.paidAt > latest.paidAt) latest = m;
  }
  return latest;
}

function rankClubs(clubs) {
  const totals = clubTotals();
  return clubs
    .map((club) => {
      const entry = totals.get(club.id);
      return {
        club,
        total: entry ? entry.total : 0,
        firstPaidAt: entry ? entry.firstPaidAt : null
      };
    })
    .sort((a, b) => b.total - a.total || String(a.firstPaidAt || a.club.createdAt).localeCompare(String(b.firstPaidAt || b.club.createdAt)) || a.club.name.localeCompare(b.club.name))
    .map((row, i) => ({
      rank: i + 1,
      clubId: row.club.id,
      name: row.club.name,
      country: row.club.country,
      league: row.club.league,
      totalUSD: row.total,
      message: activeMessage(row.club.id) ? activeMessage(row.club.id).text : null
    }));
}

function boardScope(scope) {
  const d = getDb();
  if (!scope || scope === "global") return { key: "global", label: "Ranking mundial", clubs: d.clubs };
  const [kind, value] = scope.split(":");
  if (kind === "country") {
    const country = d.countries.find((c) => c.code === value);
    if (!country) return null;
    return { key: scope, label: country.name, clubs: d.clubs.filter((c) => c.country === value) };
  }
  if (kind === "league") {
    const league = d.leagues.find((l) => l.id === value);
    if (!league) return null;
    return { key: scope, label: `${league.name} \u00b7 ${league.countryName}`, clubs: d.clubs.filter((c) => c.league === value) };
  }
  return null;
}

function stats() {
  const d = getDb();
  const totalUSD = d.bids.reduce((acc, b) => acc + b.usd, 0);
  return {
    revenueUSD: totalUSD,
    bids: d.bids.length,
    clubs: d.clubs.length,
    countries: d.countries.length,
    messages: d.messages.length,
    chatMessages: d.chatMessages.length
  };
}

module.exports = { rankClubs, boardScope, clubTotals, activeMessage, stats };
