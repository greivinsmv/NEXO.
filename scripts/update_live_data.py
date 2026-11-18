#!/usr/bin/env python3
"""Small public-data pilot. CheapShark is queried once per selected game, never at catalog scale."""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "NEXO-academic-pilot/0.1 (+https://github.com/greivinsmv/NEXO)"
GAMES = [
    ("elden-ring", "Elden Ring", "1245620", 0),
    ("hades-ii", "Hades II", "1145350", 1),
    ("sea-of-stars", "Sea of Stars", "1244090", 7),
    ("forza-horizon-5", "Forza Horizon 5", "1551360", 2),
    ("hollow-knight", "Hollow Knight", "367520", 3),
    ("god-of-war-ragnarok", "God of War Ragnarök", "2322010", 4),
    ("baldurs-gate-3", "Baldur's Gate 3", "1086940", 5),
    ("stardew-valley", "Stardew Valley", "413150", 6),
]


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    stores = {row["storeID"]: row["storeName"] for row in fetch_json("https://www.cheapshark.com/api/1.0/stores") if row.get("isActive") == 1}
    fx = fetch_json("https://api.hacienda.go.cr/indicadores/tc")
    usd_crc = float(fx["dolar"]["venta"]["valor"])
    eur_usd = float(fx["euro"]["dolares"])
    if not (300 < usd_crc < 1000 and .7 < eur_usd < 1.6):
        raise ValueError("Unexpected exchange rates; keeping previous snapshot")
    games = []
    for slug, title, app_id, art in GAMES:
        params = urllib.parse.urlencode({"steamAppID": app_id, "pageSize": 60})
        rows = fetch_json("https://www.cheapshark.com/api/1.0/deals?" + params)
        offers = []
        for row in rows:
            if str(row.get("steamAppID")) != app_id or row.get("storeID") not in stores:
                continue
            try:
                price = float(row["salePrice"])
                regular = float(row["normalPrice"])
            except (KeyError, TypeError, ValueError):
                continue
            if price < 0 or regular <= 0 or price > regular or not row.get("dealID"):
                continue
            offers.append({"store": stores[row["storeID"]], "price": price, "regular": regular,
                           "currency": "USD", "url": "https://www.cheapshark.com/redirect?dealID=" + row["dealID"],
                           "sourceChangedAt": datetime.fromtimestamp(int(row.get("lastChange") or 0), timezone.utc).isoformat()})
        offers.sort(key=lambda offer: offer["price"])
        if not offers:
            print("No offers:", title)
            continue
        best = offers[0]
        cover_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/library_600x900.jpg"
        games.append({"slug": slug, "name": title, "steamAppId": int(app_id), "platform": "PC", "type": "Juego", "format": "Digital",
                      "art": art, "store": best["store"], "price": best["price"], "regular": best["regular"],
                      "currency": "USD", "offers": offers[:12], "coverUrl": cover_url, "coverSource": "Steam",
                      "hours": None, "extras": None,
                      "completion": None, "achievements": None})
        time.sleep(0.5)
    if len(games) < 4:
        raise ValueError("Too few valid games; keeping previous snapshot")
    snapshot = {"capturedAt": datetime.now(timezone.utc).isoformat(), "source": "CheapShark API",
                "sourceUrl": "https://apidocs.cheapshark.com/", "games": games,
                "fx": {"source": "Ministerio de Hacienda de Costa Rica", "sourceUrl": "https://api.hacienda.go.cr/indicadores/tc",
                       "date": fx["dolar"]["venta"]["fecha"], "usd_crc": usd_crc, "eur_usd": eur_usd}}
    content = "window.NEXO_LIVE_DATA = " + json.dumps(snapshot, ensure_ascii=True, separators=(",", ":")) + ";\n"
    (ROOT / "live-data.js").write_text(content, encoding="utf-8")
    print("Wrote", len(games), "games and", sum(len(game["offers"]) for game in games), "offers")


if __name__ == "__main__":
    main()
