"""Validate the published JSON against the SQLite catalog and stage-0 import."""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / "data/catalog.json").read_text(encoding="utf-8"))
history = json.loads((root / "data/price-history.json").read_text(encoding="utf-8"))
connection = sqlite3.connect(root / "data/nexo.sqlite")
try:
    assert not connection.execute("PRAGMA foreign_key_check").fetchall(), "Broken database references"
    ids = [row[0] for row in connection.execute(
        "SELECT steam_app_id FROM games WHERE active = 1 ORDER BY position"
    )]
    assert len(ids) >= 500, f"Only {len(ids)} active games in SQLite"
    assert ids == [game["steamAppId"] for game in catalog["games"]], "JSON differs from SQLite"
    public_by_id = {game["steamAppId"]: game for game in catalog["games"]}
    if 'two-store verified' in catalog.get('source', ''):
        assert all(len({offer['store'] for offer in game.get('offers', [])
                        if offer.get('price') is not None}) >= 2 for game in catalog['games']), \
            'A published game has fewer than two store prices'
    has_platform_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'game_platforms'"
    ).fetchone()
    if has_platform_table:
        linked = defaultdict(set)
        for appid, family in connection.execute('SELECT steam_app_id, platform FROM game_platforms'):
            linked[appid].add(family)
        if linked:
            for appid, game in public_by_id.items():
                assert set(game.get('platforms', [])) == {'PC'} | linked[appid], f'Platform export mismatch for {appid}'
            all_platforms = {platform for game in catalog['games'] for platform in game['platforms']}
            assert {'PC', 'PlayStation', 'Xbox', 'Nintendo Switch'} <= all_platforms
    for game in catalog["games"]:
        if "steamUserScore" in game:
            assert 0 <= game["steamUserScore"] <= 100, f"Invalid Steam user score for {game['steamAppId']}"
            assert game.get("steamReviewCount", 0) > 0, f"Missing Steam review count for {game['steamAppId']}"
    retailer_rows = connection.execute(
        "SELECT steam_app_id, store, price_usd, url FROM retailer_offers"
    ).fetchall()
    for appid, store, price, url in retailer_rows:
        assert any(offer["store"] == store and offer["price"] == price and offer["url"] == url
                   for offer in public_by_id[appid]["offers"]), f"{store} offer missing from public JSON for {appid}"
    assert history["currency"] == "USD" and history["region"] == "US"
    history_rows = {
        (str(appid), store, observed_at, price, source)
        for appid, store, observed_at, price, source in connection.execute(
            "SELECT steam_app_id, store, observed_at, price_usd, source FROM offer_history"
        )
    }
    exported = [
        (appid, store, point["at"], point["price"], point["source"])
        for appid, stores in history["games"].items()
        for store, points in stores.items() for point in points
    ]
    assert exported and all(row in history_rows for row in exported), "Price history differs from SQLite"
    pages = [row[0] for row in connection.execute(
        "SELECT DISTINCT source_page FROM stage0_candidates ORDER BY source_page"
    )]
    assert len(pages) >= 2, f"Stage 0 used only {len(pages)} public-list pages"
    print(f"Catalog verified: {len(ids)} games, {len(retailer_rows)} retailer offers, {len(exported)} history points; stage-0 pages {pages}")
finally:
    connection.close()
