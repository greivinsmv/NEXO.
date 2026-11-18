"""SQLite source of truth and static JSON export for the public catalog."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "nexo.sqlite"
PUBLIC_JSON = ROOT / "data" / "catalog.json"
HISTORY_JSON = ROOT / "data" / "price-history.json"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS catalog_runs (
    id INTEGER PRIMARY KEY,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL,
    stage0_url TEXT NOT NULL,
    stage0_pages INTEGER NOT NULL CHECK(stage0_pages >= 2)
);
CREATE TABLE IF NOT EXISTS stage0_candidates (
    run_id INTEGER NOT NULL REFERENCES catalog_runs(id) ON DELETE CASCADE,
    steam_app_id INTEGER NOT NULL,
    source_page INTEGER NOT NULL,
    page_rank INTEGER NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (run_id, steam_app_id)
);
CREATE INDEX IF NOT EXISTS stage0_candidates_page ON stage0_candidates(run_id, source_page);
CREATE TABLE IF NOT EXISTS games (
    steam_app_id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    platform TEXT NOT NULL,
    price_usd REAL NOT NULL,
    regular_usd REAL,
    current_players INTEGER NOT NULL,
    relevance_score REAL NOT NULL,
    main_hours REAL,
    achievements INTEGER,
    cover_url TEXT NOT NULL,
    position INTEGER NOT NULL,
    active INTEGER NOT NULL CHECK(active IN (0, 1)),
    updated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS games_active_position ON games(active, position);
CREATE TABLE IF NOT EXISTS game_genres (
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    genre TEXT NOT NULL,
    PRIMARY KEY (steam_app_id, genre)
);
CREATE TABLE IF NOT EXISTS game_screenshots (
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    url TEXT NOT NULL,
    PRIMARY KEY (steam_app_id, position)
);
CREATE TABLE IF NOT EXISTS game_achievements (
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    icon_url TEXT NOT NULL,
    PRIMARY KEY (steam_app_id, position)
);
CREATE TABLE IF NOT EXISTS price_observations (
    run_id INTEGER NOT NULL REFERENCES catalog_runs(id) ON DELETE CASCADE,
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    store TEXT NOT NULL,
    price_usd REAL NOT NULL,
    regular_usd REAL,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (run_id, steam_app_id, store)
);
CREATE TABLE IF NOT EXISTS retailer_offers (
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    store TEXT NOT NULL,
    price_usd REAL NOT NULL,
    regular_usd REAL NOT NULL,
    url TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (steam_app_id, store)
);
CREATE INDEX IF NOT EXISTS retailer_offers_store ON retailer_offers(store);
CREATE TABLE IF NOT EXISTS offer_history (
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    store TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    price_usd REAL NOT NULL CHECK(price_usd >= 0),
    source TEXT NOT NULL,
    PRIMARY KEY (steam_app_id, store, observed_at)
);
CREATE INDEX IF NOT EXISTS offer_history_lookup ON offer_history(steam_app_id, store, observed_at);
CREATE TABLE IF NOT EXISTS game_platforms (
    steam_app_id INTEGER NOT NULL REFERENCES games(steam_app_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    wikidata_game_id TEXT NOT NULL,
    wikidata_platform_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (steam_app_id, wikidata_platform_id)
);
CREATE INDEX IF NOT EXISTS game_platforms_game ON game_platforms(steam_app_id);
"""

PLATFORM_ORDER = ('PC', 'PlayStation', 'Xbox', 'Nintendo Switch', 'Nintendo Switch 2')


def connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def save_catalog(snapshot, candidates, secondary_offers=None):
    games = snapshot["games"]
    pages = {row["source_page"] for row in candidates}
    if len(games) < 500 or len({game["steamAppId"] for game in games}) != len(games):
        raise ValueError("Catalog must contain at least 500 distinct games")
    if len(pages) < 2:
        raise ValueError("Stage 0 must read at least two pages of a public listing")
    if secondary_offers is not None and any(not secondary_offers.get(game['steamAppId']) for game in games):
        raise ValueError('Every published game needs a second store offer')
    connection = connect()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO catalog_runs(captured_at, source, stage0_url, stage0_pages) VALUES(?, ?, ?, ?)",
                (snapshot["capturedAt"], snapshot["source"], "https://steamspy.com/api.php?request=all&page={page}", len(pages)),
            )
            run_id = cursor.lastrowid
            connection.executemany(
                "INSERT INTO stage0_candidates(run_id, steam_app_id, source_page, page_rank, name) VALUES(?, ?, ?, ?, ?)",
                ((run_id, row["steam_app_id"], row["source_page"], row["page_rank"], row["name"]) for row in candidates),
            )
            connection.execute("UPDATE games SET active = 0")
            for position, game in enumerate(games):
                appid = game["steamAppId"]
                connection.execute(
                    """INSERT INTO games(
                         steam_app_id, slug, name, description, platform, price_usd, regular_usd,
                         current_players, relevance_score, main_hours, achievements, cover_url,
                         position, active, updated_at, payload_json
                       ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                       ON CONFLICT(steam_app_id) DO UPDATE SET
                         slug=excluded.slug, name=excluded.name, description=excluded.description,
                         platform=excluded.platform, price_usd=excluded.price_usd,
                         regular_usd=excluded.regular_usd, current_players=excluded.current_players,
                         relevance_score=excluded.relevance_score, main_hours=excluded.main_hours,
                         achievements=excluded.achievements, cover_url=excluded.cover_url,
                         position=excluded.position, active=1, updated_at=excluded.updated_at,
                         payload_json=excluded.payload_json""",
                    (appid, game["slug"], game["name"], game.get("description") or "", game["platform"],
                     game["price"], game.get("regular"), game.get("currentPlayers") or 0,
                     game.get("relevanceScore") or 0, game.get("hours"), game.get("achievements"),
                     game["coverUrl"], position, snapshot["capturedAt"],
                     json.dumps(game, ensure_ascii=True, separators=(",", ":"))),
                )
                for table in ("game_genres", "game_screenshots", "game_achievements"):
                    connection.execute(f"DELETE FROM {table} WHERE steam_app_id = ?", (appid,))
                connection.executemany(
                    "INSERT INTO game_genres(steam_app_id, genre) VALUES(?, ?)",
                    ((appid, genre) for genre in game.get("genres", [])),
                )
                connection.executemany(
                    "INSERT INTO game_screenshots(steam_app_id, position, url) VALUES(?, ?, ?)",
                    ((appid, index, shot["url"]) for index, shot in enumerate(game.get("screenshots", []))),
                )
                connection.executemany(
                    "INSERT INTO game_achievements(steam_app_id, position, name, icon_url) VALUES(?, ?, ?, ?)",
                    ((appid, index, item["name"], item["icon"]) for index, item in enumerate(game.get("featuredAchievements", []))),
                )
                connection.executemany(
                    "INSERT INTO price_observations(run_id, steam_app_id, store, price_usd, regular_usd, captured_at) VALUES(?, ?, ?, ?, ?, ?)",
                    ((run_id, appid, offer["store"], offer["price"], offer.get("regular"), offer.get('capturedAt') or snapshot["capturedAt"])
                     for offer in game.get("offers", [])),
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) VALUES(?, ?, ?, ?, ?)",
                    ((appid, offer["store"], offer.get('capturedAt') or snapshot["capturedAt"], offer["price"], "Steam Store")
                     for offer in game.get("offers", [])),
                )
            if secondary_offers is not None:
                connection.execute(
                    "DELETE FROM retailer_offers WHERE store != 'GOG' AND steam_app_id IN "
                    "(SELECT steam_app_id FROM games WHERE active = 1)"
                )
                for appid, offers in secondary_offers.items():
                    for offer in offers:
                        if offer['store'] == 'Steam':
                            raise ValueError('A secondary offer must come from another store')
                        connection.execute(
                            'INSERT OR REPLACE INTO retailer_offers(steam_app_id, store, price_usd, regular_usd, url, captured_at) '
                            'VALUES (?, ?, ?, ?, ?, ?)',
                            (appid, offer['store'], offer['price'], offer['regular'], offer['url'], offer['capturedAt']),
                        )
                        connection.execute(
                            'INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) '
                            'VALUES (?, ?, ?, ?, ?)',
                            (appid, offer['store'], offer['capturedAt'], offer['price'],
                             'GOG Catalog' if offer['store'] == 'GOG' else 'CheapShark'),
                        )
            # A new stage-0 ranking can replace older games. Retire their current
            # retailer offers while retaining dated history in SQLite.
            connection.execute(
                "DELETE FROM retailer_offers WHERE steam_app_id IN "
                "(SELECT steam_app_id FROM games WHERE active = 0)"
            )
    finally:
        connection.close()
    return export_catalog()


def export_catalog():
    connection = connect()
    try:
        run = connection.execute(
            "SELECT captured_at, source FROM catalog_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not run:
            raise ValueError("The database has no catalog snapshot")
        games = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM games WHERE active = 1 ORDER BY position"
        )]
        by_game = {}
        for appid, store, price, regular, url, captured_at in connection.execute(
            "SELECT steam_app_id, store, price_usd, regular_usd, url, captured_at FROM retailer_offers"
        ):
            by_game.setdefault(appid, []).append({
                "store": store, "price": price, "regular": regular, "currency": "USD",
                "url": url, "capturedAt": captured_at,
            })
        by_platform = {}
        for appid, platform, captured_at in connection.execute(
            "SELECT steam_app_id, platform, captured_at FROM game_platforms"
        ):
            by_platform.setdefault(appid, []).append((platform, captured_at))
        for game in games:
            linked = by_platform.get(game['steamAppId'], [])
            families = {'PC', *(platform for platform, _ in linked)}
            game['platforms'] = [platform for platform in PLATFORM_ORDER if platform in families]
            if linked:
                game['platformsUpdatedAt'] = max(date for _, date in linked)
            else:
                game.pop('platformsUpdatedAt', None)
            extra = by_game.get(game["steamAppId"], [])
            if not extra:
                continue
            offers = [offer for offer in game.get("offers", []) if offer["store"] not in {item["store"] for item in extra}]
            offers.extend(extra)
            offers.sort(key=lambda offer: (offer["price"], offer["store"]))
            game["offers"] = offers
            game["store"] = offers[0]["store"]
            game["price"] = offers[0]["price"]
            game["regular"] = offers[0]["regular"]
            game["currency"] = "USD"
        if len(games) < 500:
            raise ValueError(f"The database contains only {len(games)} active games")
        output = {"capturedAt": run[0], "source": run[1], "games": games}
        temporary = PUBLIC_JSON.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(output, ensure_ascii=True, separators=(",", ":")) + "\n", encoding="utf-8")
        temporary.replace(PUBLIC_JSON)
        export_price_history(connection)
        return len(games)
    finally:
        connection.close()


def export_price_history(connection=None):
    owned = connection is None
    if owned:
        connection = connect()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        series = {}
        latest = None
        for appid, store, observed_at, price, source in connection.execute(
            "SELECT steam_app_id, store, observed_at, price_usd, source FROM offer_history "
            "WHERE observed_at >= ? ORDER BY steam_app_id, store, observed_at", (cutoff,)
        ):
            series.setdefault(str(appid), {}).setdefault(store, []).append(
                {"at": observed_at, "price": price, "source": source}
            )
            if latest is None or observed_at > latest:
                latest = observed_at
        output = {"currency": "USD", "region": "US", "capturedThrough": latest, "games": series}
        temporary = HISTORY_JSON.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(output, ensure_ascii=True, separators=(",", ":")) + "\n", encoding="utf-8")
        temporary.replace(HISTORY_JSON)
        return sum(len(points) for stores in series.values() for points in stores.values())
    finally:
        if owned:
            connection.close()


def seed_existing_price_history():
    connection = connect()
    try:
        with connection:
            connection.execute(
                "INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) "
                "SELECT steam_app_id, store, captured_at, price_usd, 'Steam Store' FROM price_observations"
            )
            connection.execute(
                "INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) "
                "SELECT steam_app_id, store, captured_at, price_usd, "
                "CASE WHEN store = 'GOG' THEN 'GOG Catalog' ELSE 'CheapShark' END FROM retailer_offers"
            )
    finally:
        connection.close()
    return export_price_history()


def save_pilot_price_history(snapshot):
    connection = connect()
    try:
        with connection:
            for game in snapshot.get("games", []):
                appid = game.get("steamAppId")
                if appid is None or not connection.execute(
                    "SELECT 1 FROM games WHERE steam_app_id = ?", (appid,)
                ).fetchone():
                    continue
                connection.executemany(
                    "INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) VALUES(?, ?, ?, ?, ?)",
                    ((appid, offer["store"], snapshot["capturedAt"], offer["price"], "CheapShark")
                     for offer in game.get("offers", []) if offer.get("store") and offer.get("price") is not None),
                )
    finally:
        connection.close()
    return export_price_history()


def replace_retailer_offers(store, rows, captured_at):
    connection = connect()
    try:
        with connection:
            connection.execute("DELETE FROM retailer_offers WHERE store = ?", (store,))
            connection.executemany(
                "INSERT INTO retailer_offers(steam_app_id, store, price_usd, regular_usd, url, captured_at) VALUES(?, ?, ?, ?, ?, ?)",
                ((appid, store, price, regular, url, captured_at) for appid, price, regular, url in rows),
            )
            connection.execute(
                "INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) "
                "SELECT steam_app_id, store, captured_at, price_usd, 'GOG Catalog' "
                "FROM retailer_offers WHERE store = ? AND captured_at = ?", (store, captured_at)
            )
    finally:
        connection.close()
    return export_catalog()


def replace_aggregated_offers(rows, captured_at):
    """Replace the non-GOG retailer snapshot after every batch succeeds."""
    connection = connect()
    try:
        with connection:
            connection.execute("DELETE FROM retailer_offers WHERE store NOT IN ('GOG')")
            connection.executemany(
                "INSERT INTO retailer_offers(steam_app_id, store, price_usd, regular_usd, url, captured_at) VALUES(?, ?, ?, ?, ?, ?)",
                ((appid, store, price, regular, url, captured_at)
                 for appid, store, price, regular, url in rows),
            )
            connection.execute(
                "INSERT OR IGNORE INTO offer_history(steam_app_id, store, observed_at, price_usd, source) "
                "SELECT steam_app_id, store, captured_at, price_usd, 'CheapShark' "
                "FROM retailer_offers WHERE store != 'GOG' AND captured_at = ?", (captured_at,)
            )
    finally:
        connection.close()
    return export_catalog()
