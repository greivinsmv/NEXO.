#!/usr/bin/env python3
"""Build a sourced SQLite game catalog and export JSON for GitHub Pages.

SteamSpy's paginated public list supplies stage-0 candidates. Steam Store appdetails
validates each game and supplies US prices, media, and achievement counts.
An archived community dataset of HowLongToBeat estimates supplies playtime only
for unique exact names.
The response cache makes interrupted runs resumable and expires source snapshots.
"""
import argparse
import csv
import html
import io
import json
import math
import re
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from candidate_offers import capture_candidate_offers
from catalog_db import DATABASE, save_catalog

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".catalog-cache"
CACHE.mkdir(exist_ok=True)
TARGET = 500
PAUSE_SECONDS = 1.75  # Below the reported 200 Steam Store calls per five minutes.
HEADERS = {"User-Agent": "NEXO academic catalog/0.2 (+https://github.com/greivinsmv/NEXO)", "Accept": "application/json"}
HLTB_URL = "https://raw.githubusercontent.com/johagan94/hltb-dataset-plugin/ee4476326c891976941f17e191096fac7c5dad42/dataset/hltb_dataset_filtered.csv"


def get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def cache_fresh(path, max_age_days):
    return path.exists() and (max_age_days is None or time.time() - path.stat().st_mtime <= max_age_days * 86400)


def cached_get(url, filename, max_age_days=None):
    path = CACHE / filename
    if not cache_fresh(path, max_age_days):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(get(url))
        temporary.replace(path)
    return path.read_bytes()


def key(name):
    name = unicodedata.normalize("NFKD", name).casefold()
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def slug_for(name, appid):
    return re.sub(r"[^a-z0-9]+", "-", key(name)).strip("-")[:64] + "-" + str(appid)


def playtimes():
    source = cached_get(HLTB_URL, "hltb-2026.csv").decode("utf-8-sig")
    rows = {}
    duplicate = set()
    for row in csv.DictReader(io.StringIO(source)):
        if row.get("type") != "game" or "PC" not in (row.get("platform") or "").split(", "):
            continue
        title = key(row.get("name") or "")
        if not title or title in rows:
            duplicate.add(title)
        else:
            rows[title] = row
    for title in duplicate:
        rows.pop(title, None)
    return rows


def positive_hours(value):
    try:
        number = round(float(value), 1)
    except (TypeError, ValueError):
        return None
    return number if 0 < number < 2000 else None


def previous_verified_games(max_age_days=7):
    """Carry forward active games with a recently observed second store."""
    if not DATABASE.exists():
        return {}, {}
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
    candidates, offers = {}, {}
    with sqlite3.connect(DATABASE) as connection:
        for appid, payload in connection.execute(
            'SELECT steam_app_id, payload_json FROM games WHERE active = 1'
        ):
            game = json.loads(payload)
            candidates[str(appid)] = {
                'name': game['name'], 'ccu': game.get('currentPlayers') or 0,
                'owners': str(game.get('estimatedOwners') or 0),
                'positive': round((game.get('steamReviewCount') or 0)
                                  * (game.get('steamUserScore') or 0) / 100),
                'price': round((game.get('price') or 0) * 100),
            }
        for appid, store, price, regular, url, captured_at in connection.execute(
            'SELECT r.steam_app_id, r.store, r.price_usd, r.regular_usd, r.url, r.captured_at '
            'FROM retailer_offers r JOIN games g ON g.steam_app_id = r.steam_app_id '
            'WHERE g.active = 1 AND r.store != ?'
            , ('Steam',)
        ):
            try:
                observed = datetime.fromisoformat(captured_at.replace('Z', '+00:00')).timestamp()
            except (ValueError, AttributeError):
                continue
            if observed < cutoff or not url or price is None or price <= 0:
                continue
            offers.setdefault(appid, []).append({
                'store': store, 'price': price, 'regular': regular or price,
                'currency': 'USD', 'url': url, 'capturedAt': captured_at,
            })
    return candidates, offers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-days", type=float, default=7, help="Maximum age for SteamSpy and Steam Store responses")
    parser.add_argument('--dry-run', action='store_true', help='Validate selection without replacing SQLite')
    args = parser.parse_args(argv)
    if not 0 <= args.cache_days <= 30:
        parser.error("--cache-days must be between 0 and 30")
    candidates = {}
    candidate_rows = []
    for page in range(2):
        url = f"https://steamspy.com/api.php?request=all&page={page}"
        listing = json.loads(cached_get(url, f"steamspy-page-{page}.json", args.cache_days))
        if not isinstance(listing, dict) or not listing:
            raise ValueError(f"SteamSpy page {page} did not contain candidates")
        for rank, (appid, item) in enumerate(listing.items()):
            if not str(appid).isdigit() or appid in candidates or not isinstance(item, dict):
                continue
            candidates[appid] = item
            candidate_rows.append({
                "steam_app_id": int(appid),
                "source_page": page,
                "page_rank": rank,
                "name": item.get("name") or appid,
            })
        print(f"Stage 0: page {page}, {len(listing)} entries", flush=True)
    prior_candidates, prior_offers = previous_verified_games()
    for appid, item in prior_candidates.items():
        candidates.setdefault(appid, item)
    def candidate_score(item):
        lower_owners = int(str(item.get("owners", "0")).split("..")[0].replace(",", "").strip() or 0)
        return 4 * math.log1p(max(0, int(item.get("ccu") or 0))) + math.log1p(lower_owners) + .3 * math.log1p(max(0, int(item.get("positive") or 0)))
    candidate_ids = sorted(candidates, key=lambda appid: candidate_score(candidates[appid]), reverse=True)
    eligible_ids = [int(appid) for appid in candidate_ids if str(appid).isdigit()
                    and int(candidates[appid].get('ccu') or 0) >= 5
                    and int(candidates[appid].get('price') or 0) > 0]
    secondary_offers = capture_candidate_offers(eligible_ids)
    for appid, offers in prior_offers.items():
        if appid in eligible_ids and appid not in secondary_offers:
            secondary_offers[appid] = offers
    if len(secondary_offers) < TARGET:
        raise ValueError(f'Only {len(secondary_offers)} candidate games have another current store offer')
    times = playtimes()
    catalog = []
    failures = []
    for appid in candidate_ids:
        candidate = candidates.get(appid, {"name": appid})
        if len(catalog) >= TARGET:
            break
        if not re.fullmatch(r"\d+", str(appid)) or not candidate.get("name"):
            continue
        # Active paid titles only. A classic can stay if people still play it.
        if int(candidate.get("ccu") or 0) < 5 or int(candidate.get("price") or 0) <= 0:
            continue
        if int(appid) not in secondary_offers:
            continue
        path = CACHE / f"steam-{appid}.json"
        if cache_fresh(path, args.cache_days):
            response = json.loads(path.read_text(encoding="utf-8"))
        else:
            url = "https://store.steampowered.com/api/appdetails?" + urllib.parse.urlencode({"appids": appid, "cc": "us", "l": "english"})
            try:
                response = json.loads(get(url))
                if response.get(str(appid), {}).get("success"):
                    path.write_text(json.dumps(response, separators=(",", ":")), encoding="utf-8")
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                failures.append((appid, str(error)))
                print("Retry later:", appid, error, flush=True)
                time.sleep(8)
                continue
            time.sleep(PAUSE_SECONDS)
        steam_captured_at = (datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                             if path.exists() else datetime.now(timezone.utc).isoformat())
        info = response.get(str(appid), {})
        data = info.get("data") if info.get("success") else None
        if not isinstance(data, dict) or data.get("type") != "game":
            continue
        if data.get("is_free") or (data.get("release_date") or {}).get("coming_soon"):
            continue
        genres = {item.get("description") for item in (data.get("genres") or [])}
        if genres.intersection({"Utilities", "Software Training", "Design & Illustration", "Photo Editing", "Video Production", "Audio Production"}):
            continue
        name = data.get("name") or candidate["name"]
        description = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(data.get("short_description") or ""))).strip()
        screenshots = [{"url": shot["path_thumbnail"]}
                       for shot in (data.get("screenshots") or [])[:6]
                       if shot.get("path_thumbnail", "").startswith("https://")
                       and (shot.get("path_full") or shot["path_thumbnail"]).startswith("https://")]
        cover_fallback = data.get("capsule_imagev5") or data.get("capsule_image") or data.get("header_image")
        if not cover_fallback or not cover_fallback.startswith("https://"):
            continue
        cover = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/library_600x900.jpg"
        price = data.get("price_overview") or {}
        final = price.get("final")
        initial = price.get("initial")
        amount = round(final / 100, 2) if isinstance(final, int) and final >= 0 else None
        regular = round(initial / 100, 2) if isinstance(initial, int) and initial >= 0 else None
        if data.get("is_free"):
            amount, regular = 0, 0
        if amount is None or amount <= 0:
            continue
        hltb = times.get(key(name))
        entry = {
            "slug": slug_for(name, appid), "name": name, "description": description, "steamAppId": int(appid),
            "currentPlayers": int(candidate.get("ccu") or 0),
            "estimatedOwners": int(str(candidate.get("owners", "0")).split("..")[0].replace(",", "").strip() or 0),
            "relevanceScore": round(candidate_score(candidate), 2),
            "platform": "PC", "type": "Juego", "format": "Digital", "genres": sorted(genre for genre in genres if genre), "art": len(catalog) % 8,
            "store": "Steam", "price": amount, "regular": regular, "currency": "USD",
            "offers": [{"store": "Steam", "price": amount, "regular": regular, "currency": "USD", "url": f"https://store.steampowered.com/app/{appid}/", "capturedAt": steam_captured_at}] if amount is not None else [],
            "coverUrl": cover, "coverFallbackUrl": cover_fallback, "cardImageUrl": data.get("header_image") or cover_fallback,
            "gameLogoUrl": f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/logo.png",
            "coverSource": "Steam", "screenshots": screenshots,
            "achievements": (data.get("achievements") or {}).get("total"),
            "featuredAchievements": [{"name": item.get("localized_name") or item.get("name"), "icon": item.get("path")}
                                     for item in ((data.get("achievements") or {}).get("highlighted") or [])[:6]
                                     if item.get("path", "").startswith("https://")],
            "releaseDate": (data.get("release_date") or {}).get("date"),
            "metacritic": (data.get("metacritic") or {}).get("score"),
            "hours": positive_hours(hltb.get("main_story")) if hltb else None,
            "extras": positive_hours(hltb.get("main_plus_sides")) if hltb else None,
            "completion": positive_hours(hltb.get("completionist")) if hltb else None,
            "hltbId": int(hltb["id"]) if hltb and str(hltb.get("id", "")).isdigit() else None,
        }
        catalog.append(entry)
        if len(catalog) % 50 == 0:
            print("Validated", len(catalog), "games", flush=True)
    if len(catalog) < TARGET:
        raise RuntimeError(f"Only {len(catalog)} games validated; {len(failures)} fetch failures. Rerun to resume.")
    if args.dry_run:
        with sqlite3.connect(DATABASE) as connection:
            previous = {row[0] for row in connection.execute('SELECT steam_app_id FROM games WHERE active = 1')}
        selected = {game['steamAppId'] for game in catalog}
        print(f'Dry run: {len(catalog)} games with two stores; {len(selected & previous)} retained, '
              f'{len(selected - previous)} new, {len(previous - selected)} retired; SQLite unchanged', flush=True)
        return
    snapshot = {"capturedAt": datetime.now(timezone.utc).isoformat(), "source": "Steam Store; SteamSpy pages 0 and 1 plus recent prior candidates; CheapShark and prior verified second-store offers; archived HLTB data (2026-03-27); two-store verified", "games": catalog}
    saved = save_catalog(snapshot, candidate_rows,
                         {game['steamAppId']: secondary_offers[game['steamAppId']] for game in catalog})
    print("Saved", saved, "games in SQLite and JSON,", sum(g["achievements"] is not None for g in catalog), "achievement counts,", sum(g["hours"] is not None for g in catalog), "playtimes", flush=True)


if __name__ == "__main__":
    main()
