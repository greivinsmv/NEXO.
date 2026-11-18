"""Match the public, paginated GOG US catalog to the SQLite game catalog."""
import json
import re
import sqlite3
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from catalog_db import DATABASE, replace_retailer_offers

ENDPOINT = "https://catalog.gog.com/v1/catalog"
PARAMS = {
    "limit": 100,
    "order": "asc:title",
    "productType": "in:game",
    "countryCode": "US",
    "locale": "en-US",
    "currencyCode": "USD",
}


def title_key(title):
    title = unicodedata.normalize("NFKD", title).casefold()
    return re.sub(r"[^a-z0-9]", "", title)


def fetch_page(page):
    url = ENDPOINT + "?" + urlencode({**PARAMS, "page": page})
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "NEXO academic game catalog (GitHub Pages)"}), timeout=25) as response:
                payload = json.load(response)
            if not isinstance(payload.get("products"), list):
                raise ValueError("GOG catalog response has no products")
            return payload
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def offer_for(product):
    if product.get("productType") != "game" or product.get("productState") != "default":
        return None
    price = product.get("price") or {}
    try:
        final = Decimal(price["finalMoney"]["amount"])
        regular = Decimal(price["baseMoney"]["amount"])
    except (KeyError, InvalidOperation, TypeError):
        return None
    if price["finalMoney"].get("currency") != "USD" or price["baseMoney"].get("currency") != "USD":
        return None
    url = product.get("storeLink", "")
    if final <= 0 or regular < final or urlparse(url).hostname != "www.gog.com":
        return None
    return float(final), float(regular), url


def main():
    with sqlite3.connect(DATABASE) as connection:
        catalog_rows = connection.execute(
            "SELECT steam_app_id, name FROM games WHERE active = 1"
        ).fetchall()
    if len(catalog_rows) < 500:
        raise ValueError("The SQLite catalog is incomplete")
    catalog = {}
    duplicate_keys = set()
    for appid, name in catalog_rows:
        key = title_key(name)
        if key in catalog:
            duplicate_keys.add(key)
        catalog[key] = appid
    for key in duplicate_keys:
        del catalog[key]
    first = fetch_page(1)
    pages = first.get("pages")
    if not isinstance(pages, int) or not 1 <= pages <= 200:
        raise ValueError("Unexpected GOG page count")
    products = list(first["products"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_page, page): page for page in range(2, pages + 1)}
        for future in as_completed(futures):
            products.extend(future.result()["products"])
    matches = {}
    ambiguous = set()
    for product in products:
        appid = catalog.get(title_key(product.get("title", "")))
        if appid is None:
            continue
        offer = offer_for(product)
        if offer is None:
            continue
        if appid in matches and matches[appid] != offer:
            ambiguous.add(appid)
        else:
            matches[appid] = offer
    rows = [(appid, *offer) for appid, offer in matches.items() if appid not in ambiguous]
    if len(rows) < 20:
        raise ValueError(f"Only {len(rows)} GOG matches; refusing to replace the previous snapshot")
    captured_at = datetime.now(timezone.utc).isoformat()
    replace_retailer_offers("GOG", rows, captured_at)
    print(f"Read {pages} GOG pages and matched {len(rows)} of {len(catalog_rows)} catalog games; skipped {len(ambiguous)} ambiguous titles")


if __name__ == "__main__":
    main()
