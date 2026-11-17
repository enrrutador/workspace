#!/usr/bin/env python3
"""Build self-contained preview.html from the Hinchaboard frontend sources.
Inlines styles.css + app.js, injects window.__HINCHABOARD__ with clubs.json
and sample boards for the global ranking and every country, plus activity
and chat.
Run from the repo root: python3 build_preview.py"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FE = ROOT / "frontend"

clubs_data = json.loads((FE / "clubs.json").read_text())
club_league = {c["id"]: c["league"] for c in clubs_data["clubs"]}

NOW = int(time.time() * 1000)
MIN = 60_000

# club -> (total, pushes, shout_text, shout_fan)
SAMPLE = {
    "real-madrid":         (214, 132, "Hala Madrid — the world is ours", "VikingoRM"),
    "barcelona":           (201, 121, "Més que un club", "Culé1899"),
    "atletico-madrid":     (96, 61, None, None),
    "river-plate":         (168, 118, "¡Este año la tabla es nuestra!", "El Diez"),
    "boca-juniors":        (157, 109, "La 12 no abandona: ¡arriba Boca!", "Xeneize12"),
    "independiente":       (55, 34, None, None),
    "racing":              (41, 26, None, None),
    "manchester-city":     (131, 74, None, None),
    "liverpool":           (124, 71, "You'll never walk alone", "KopiteYNWA"),
    "arsenal":             (88, 57, "North London is ours", "Gunner4Life"),
    "flamengo":            (118, 88, "Maior do mundo", "TorcedorBR"),
    "palmeiras":           (89, 61, None, None),
    "sao-paulo":           (36, 22, None, None),
    "paris-saint-germain": (104, 63, None, None),
    "marseille":           (38, 24, None, None),
    "bayern-munchen":      (97, 58, None, None),
    "borussia-dortmund":   (44, 29, None, None),
    "inter":               (81, 49, None, None),
    "juventus":            (64, 41, None, None),
    "inter-miami":         (92, 66, "Miami to the top", "MikeMLS"),
    "la-galaxy":           (63, 40, None, None),
    "seattle-sounders":    (22, 14, None, None),
    "club-america":        (76, 52, "¡Ódiame más!", "ÁguilaMayor"),
    "chivas":              (48, 31, None, None),
    "atletico-nacional":   (34, 21, None, None),
    "millonarios":         (27, 18, None, None),
    "nacional":            (47, 29, None, None),
    "penarol":             (39, 24, None, None),
    "colo-colo":           (43, 27, "El Cacique manda en Chile", "AlboEterno"),
    "universidad-de-chile": (31, 20, None, None),
    "olimpia":             (28, 17, None, None),
    "universitario":       (24, 15, None, None),
    "alianza-lima":        (21, 13, None, None),
    "bolivar":             (19, 12, None, None),
    "barcelona-sc":        (23, 16, None, None),
    "caracas":             (17, 11, None, None),
    "galatasaray":         (52, 33, None, None),
    "fenerbahce":          (46, 30, None, None),
    "club-brugge":         (29, 19, None, None),
    "celtic":              (35, 23, None, None),
    "rangers":             (33, 22, None, None),
    "ajax":                (58, 37, None, None),
    "benfica":             (61, 39, None, None),
    "sporting-cp":         (54, 35, None, None),
}


def make_board(club_ids):
    board = []
    for i, club in enumerate(club_ids):
        total, pushes, shout, fan = SAMPLE[club]
        entry = {
            "club": club, "league": club_league[club], "total": total, "pushes": pushes,
            "firstAt": NOW - (len(club_ids) - i) * 37 * MIN, "lastAt": NOW - i * 3 * MIN,
        }
        if shout:
            entry["shout"] = {"text": shout, "fan": fan, "at": NOW - i * 3 * MIN}
        board.append(entry)
    board.sort(key=lambda r: (-r["total"], r["firstAt"]))
    for i, r in enumerate(board):
        r["position"] = i + 1
    return board


boards = {"global": make_board(list(SAMPLE))}
country_ids = sorted({c["league"] for c in clubs_data["clubs"]})
for country in country_ids:
    boards[country] = make_board([c for c in SAMPLE if club_league[c] == country])

stats_by_scope = {
    scope: {
        "totalPushed": sum(r["total"] for r in rows),
        "totalPushes": sum(r["pushes"] for r in rows),
        "clubsRanked": len(rows),
    }
    for scope, rows in boards.items()
}

activity = [
    {"club": "river-plate", "league": "arg", "scope": "arg", "amount": 12, "fan": "El Diez", "message": "¡Este año la tabla es nuestra!", "at": NOW - 2 * MIN},
    {"club": "real-madrid", "league": "esp", "scope": "global", "amount": 20, "fan": "VikingoRM", "message": "Hala Madrid — the world is ours", "at": NOW - 5 * MIN},
    {"club": "boca-juniors", "league": "arg", "scope": "arg", "amount": 10, "fan": "Xeneize12", "message": "", "at": NOW - 7 * MIN},
    {"club": "inter-miami", "league": "usa", "scope": "global", "amount": 8, "fan": "MikeMLS", "message": "", "at": NOW - 11 * MIN},
    {"club": "flamengo", "league": "bra", "scope": "bra", "amount": 15, "fan": "TorcedorBR", "message": "Maior do mundo", "at": NOW - 14 * MIN},
    {"club": "barcelona", "league": "esp", "scope": "esp", "amount": 11, "fan": "Culé1899", "message": "", "at": NOW - 18 * MIN},
    {"club": "colo-colo", "league": "chi", "scope": "global", "amount": 5, "fan": "AlboEterno", "message": "El Cacique manda en Chile", "at": NOW - 23 * MIN},
    {"club": "liverpool", "league": "eng", "scope": "eng", "amount": 9, "fan": "KopiteYNWA", "message": "", "at": NOW - 29 * MIN},
    {"club": "galatasaray", "league": "tur", "scope": "global", "amount": 7, "fan": "Cimbom1905", "message": "", "at": NOW - 34 * MIN},
]

chat = [  # newest first
    {"fan": "Xeneize12", "club": "boca-juniors", "text": "River, miren la tabla desde abajo 😄", "at": NOW - 1 * MIN},
    {"fan": "El Diez", "club": "river-plate", "text": "Tranquilo, la temporada es larga y la cima es nuestra", "at": NOW - 4 * MIN},
    {"fan": "Culé1899", "club": "barcelona", "text": "Madrid, enjoy it while it lasts", "at": NOW - 8 * MIN},
    {"fan": "VikingoRM", "club": "real-madrid", "text": "The world champion will be white. Watch us.", "at": NOW - 12 * MIN},
    {"fan": "MikeMLS", "club": "inter-miami", "text": "Miami is coming for that global top 5", "at": NOW - 19 * MIN},
    {"fan": "TorcedorBR", "club": "flamengo", "text": "Flamengo maior do mundo, simples assim", "at": NOW - 26 * MIN},
    {"fan": "AnaBanana", "club": "palmeiras", "text": "Verdão no topo do Brasil, anotem aí", "at": NOW - 33 * MIN},
]

preview_data = {
    "clubs": clubs_data,
    "boards": boards,
    "statsByScope": stats_by_scope,
    "activity": activity,
    "chat": chat,
}

html = (FE / "index.html").read_text()
css = (FE / "styles.css").read_text()
js = (FE / "app.js").read_text()

html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>\n{css}\n</style>")
inject = f"<script>window.__HINCHABOARD__ = {json.dumps(preview_data, ensure_ascii=False)};</script>\n<script>\n{js}\n</script>"
html = html.replace('<script src="app.js"></script>', inject)

banner = """
<div style="position:sticky;top:0;z-index:50;background:#7f1d1d;color:#fff;text-align:center;padding:7px 12px;font:600 .82rem Inter,system-ui,sans-serif">
  VISTA PREVIA · PREVIEW — Datos de ejemplo / Sample data · Los pagos no están activos / Payments are not live yet
</div>
"""
html = html.replace("<body>", "<body>" + banner, 1)

out = ROOT / "preview.html"
out.write_text(html)
print(f"preview.html OK: {len(html)} bytes · {len(boards)} boards · global pool ${stats_by_scope['global']['totalPushed']}")
