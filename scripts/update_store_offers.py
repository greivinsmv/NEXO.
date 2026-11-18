"""Capture offers with equivalent sequential, thread and process execution modes."""
import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from catalog_db import DATABASE, replace_aggregated_offers
from collection_engine import MODES, rate_gate, run_jobs

ENDPOINT = "https://www.cheapshark.com/api/1.0/"
HEADERS = {"User-Agent": "NEXO/1.0 (academic game price comparison; github.com/greivinsmv/NEXO)"}
BATCH_SIZE = 20
PAGE_SIZE = 60
REQUEST_INTERVAL = 2.5
_gate = None


def set_gate(gate):
    global _gate
    _gate = gate


def get_json(path):
    for attempt in range(5):
        try:
            if _gate is None:
                raise RuntimeError("The shared request gate is not initialized")
            _gate.wait()
            with urlopen(Request(ENDPOINT + path, headers=HEADERS), timeout=25) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt == 4:
                raise
            try:
                retry_after = min(60, max(1, int(error.headers.get("Retry-After") or 30)))
            except ValueError:
                retry_after = 30
            _gate.defer(retry_after)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def fetch_batch(ids):
    rows = []
    for page in range(12):
        query = urlencode({"steamAppID": ",".join(map(str, ids)), "pageSize": PAGE_SIZE, "pageNumber": page})
        result = get_json("deals?" + query)
        if not isinstance(result, list):
            raise ValueError("Invalid CheapShark deal response")
        rows.extend(result)
        if len(result) < PAGE_SIZE:
            return rows
    raise ValueError("CheapShark batch exceeded 12 pages; refusing a truncated snapshot")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="sequential")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers (1–8)")
    parser.add_argument("--dry-run", action="store_true", help="Validate a capture without replacing SQLite")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    started = time.monotonic()
    with sqlite3.connect(DATABASE) as connection:
        ids = [row[0] for row in connection.execute(
            "SELECT steam_app_id FROM games WHERE active = 1 ORDER BY position"
        )]
    if len(ids) < 500:
        raise ValueError("The SQLite catalog is incomplete")
    with rate_gate(args.mode, REQUEST_INTERVAL) as gate:
        set_gate(gate)
        stores = get_json("stores")
        if not isinstance(stores, list):
            raise ValueError("Invalid CheapShark store list")
        names = {str(store["storeID"]): store["storeName"] for store in stores if store.get("isActive") == 1}
        # Steam and GOG already have direct official storefront snapshots.
        names = {key: value for key, value in names.items() if value not in {"Steam", "GOG"}}
        allowed = set(ids)
        batches = [ids[index:index + BATCH_SIZE] for index in range(0, len(ids), BATCH_SIZE)]
        pages = run_jobs(batches, fetch_batch, mode=args.mode, workers=args.workers,
                         initializer=set_gate, initargs=(gate,))
        all_rows = [row for page in pages for row in page]
    by_game_store = {}
    for row in all_rows:
        try:
            appid = int(row["steamAppID"])
            store = names.get(str(row["storeID"]))
            price = Decimal(row["salePrice"])
            regular = Decimal(row["normalPrice"])
            deal_id = row["dealID"]
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
        if appid not in allowed or not store or not deal_id or price <= 0 or regular < price:
            continue
        offer = (appid, store, float(price), float(regular),
                 "https://www.cheapshark.com/redirect?dealID=" + deal_id)
        key = appid, store
        if key not in by_game_store or offer[2] < by_game_store[key][2]:
            by_game_store[key] = offer
    rows = sorted(by_game_store.values(), key=lambda row: (row[0], row[1]))
    distinct_stores = {row[1] for row in rows}
    if len(rows) < 100 or len(distinct_stores) < 5:
        raise ValueError(f"Only {len(rows)} offers at {len(distinct_stores)} stores; keeping the prior snapshot")
    captured_at = datetime.now(timezone.utc).isoformat()
    if not args.dry_run:
        replace_aggregated_offers(rows, captured_at)
    action = "validated" if args.dry_run else "saved"
    print(f"Mode {args.mode} ({1 if args.mode == 'sequential' else args.workers} workers): "
          f"read {len(batches)} game batches; {action} {len(rows)} offers across "
          f"{len(distinct_stores)} stores for {len({row[0] for row in rows})} games "
          f"in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()
