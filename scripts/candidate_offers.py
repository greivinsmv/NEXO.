"""Find current second-store offers before choosing games for the catalog."""
import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

from collection_engine import rate_gate
from update_store_offers import BATCH_SIZE, REQUEST_INTERVAL, fetch_batch, get_json, set_gate

CACHE = Path(__file__).resolve().parents[1] / '.catalog-cache'
CACHE.mkdir(exist_ok=True)


def normalize_deals(rows, stores, allowed, captured_at):
    chosen = {}
    for row in rows:
        try:
            appid = int(row['steamAppID'])
            store = stores.get(str(row['storeID']))
            price = Decimal(str(row['salePrice']))
            regular = Decimal(str(row['normalPrice']))
            deal_id = str(row['dealID'])
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
        if (appid not in allowed or not store or not deal_id or not price.is_finite()
                or not regular.is_finite() or price <= 0 or regular < price):
            continue
        offer = {'store': store, 'price': float(price), 'regular': float(regular),
                 'currency': 'USD', 'url': 'https://www.cheapshark.com/redirect?dealID=' + quote(deal_id, safe=''),
                 'capturedAt': captured_at}
        key = appid, store
        if key not in chosen or offer['price'] < chosen[key]['price']:
            chosen[key] = offer
    by_game = {}
    for (appid, _), offer in chosen.items():
        by_game.setdefault(appid, []).append(offer)
    return by_game


def capture_candidate_offers(ids):
    ids = list(ids)
    allowed = set(ids)
    captured = {}
    with rate_gate('sequential', REQUEST_INTERVAL) as gate:
        set_gate(gate)
        directory = get_json('stores')
        if not isinstance(directory, list):
            raise ValueError('Invalid CheapShark store directory')
        stores = {str(store['storeID']): store['storeName'] for store in directory
                  if store.get('isActive') == 1 and store.get('storeName') not in {'Steam', 'GOG'}}
        for offset in range(0, len(ids), BATCH_SIZE):
            batch = ids[offset:offset + BATCH_SIZE]
            digest = hashlib.sha256(','.join(map(str, batch)).encode()).hexdigest()[:16]
            path = CACHE / f'candidate-offers-{digest}.json'
            if path.exists() and time.time() - path.stat().st_mtime < 2 * 86400:
                rows = json.loads(path.read_text(encoding='utf-8'))
            else:
                rows = fetch_batch(batch)
                temporary = path.with_suffix('.json.tmp')
                temporary.write_text(json.dumps(rows, separators=(',', ':')), encoding='utf-8')
                temporary.replace(path)
            date = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            for appid, offers in normalize_deals(rows, stores, allowed, date).items():
                captured.setdefault(appid, []).extend(offers)
            if offset % 200 == 0:
                print(f'Checked second-store offers for {min(offset + BATCH_SIZE, len(ids))}/{len(ids)} candidates', flush=True)
    return captured
