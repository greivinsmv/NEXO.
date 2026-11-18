#!/usr/bin/env python3
"""Add Steam user review percentages from public SteamSpy review counts."""
import json
import random
import sqlite3
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from build_catalog import cached_get, CACHE
from catalog_db import DATABASE, export_catalog

HEADERS = {'User-Agent': 'NEXO academic catalog/0.3 (+https://github.com/greivinsmv/NEXO)'}
REQUEST_INTERVAL = 2.5


def review_counts(item):
    try:
        positive = int(str(item.get('positive', 0)).replace(',', ''))
        negative = int(str(item.get('negative', 0)).replace(',', ''))
    except (TypeError, ValueError):
        return None
    if positive < 0 or negative < 0 or positive + negative == 0:
        return None
    return positive, negative


def captured_at(path):
    """Use the response file time, including when it came from the cache."""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def fetch_app(appid, last_started):
    url = 'https://steamspy.com/api.php?' + urlencode({'request': 'appdetails', 'appid': appid})
    path = CACHE / f'steamspy-review-{appid}.json'
    if path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return json.loads(path.read_text(encoding='utf-8')), last_started
    for attempt in range(4):
        pause = REQUEST_INTERVAL - (time.monotonic() - last_started)
        if pause > 0:
            time.sleep(pause)
        last_started = time.monotonic()
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=25) as response:
                data = json.load(response)
            if str(data.get('appid')) != str(appid):
                raise ValueError('SteamSpy returned another game')
            temporary = path.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
            temporary.replace(path)
            return data, last_started
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            if attempt == 3:
                print(f'No review data for {appid}: {error}', flush=True)
                return {}, last_started
            delay = min(30, 2**attempt + random.uniform(0, .5))
            if isinstance(error, HTTPError) and error.code == 429:
                try:
                    delay = min(60, max(delay, int(error.headers.get('Retry-After') or 30)))
                except ValueError:
                    delay = 30
            time.sleep(delay)
    return {}, last_started


def main():
    with sqlite3.connect(DATABASE) as connection:
        ids = [row[0] for row in connection.execute('SELECT steam_app_id FROM games WHERE active = 1')]
    if len(ids) < 500:
        raise ValueError('Incomplete SQLite catalog')
    listing = {}
    for page in (0, 1):
        url = f'https://steamspy.com/api.php?request=all&page={page}'
        path = CACHE / f'steamspy-review-page-{page}.json'
        data = json.loads(cached_get(url, path.name, 7))
        if not isinstance(data, dict) or not data:
            raise ValueError(f'Invalid SteamSpy page {page}')
        date = captured_at(path)
        listing.update({appid: (item, date) for appid, item in data.items()})
    counts = {}
    missing = []
    for appid in ids:
        item, date = listing.get(str(appid), ({}, None))
        pair = review_counts(item)
        if pair:
            counts[appid] = (*pair, date)
        else:
            missing.append(appid)
    last_started = 0.0
    for index, appid in enumerate(missing, 1):
        data, last_started = fetch_app(appid, last_started)
        pair = review_counts(data)
        if pair:
            counts[appid] = (*pair, captured_at(CACHE / f'steamspy-review-{appid}.json'))
        if index % 10 == 0:
            print(f'Checked {index}/{len(missing)} missing ranking entries', flush=True)
    if len(counts) < 400:
        raise ValueError(f'Only {len(counts)} Steam user scores; keeping previous snapshot')
    with sqlite3.connect(DATABASE) as connection:
        with connection:
            for appid, (positive, negative, response_date) in counts.items():
                payload = json.loads(connection.execute(
                    'SELECT payload_json FROM games WHERE steam_app_id = ?', (appid,)
                ).fetchone()[0])
                payload['steamUserScore'] = round(100 * positive / (positive + negative))
                payload['steamReviewCount'] = positive + negative
                payload['steamReviewCapturedAt'] = response_date
                connection.execute('UPDATE games SET payload_json = ? WHERE steam_app_id = ?',
                                   (json.dumps(payload, ensure_ascii=True, separators=(',', ':')), appid))
    export_catalog()
    print(f'Saved {len(counts)} Steam user review scores; {len(ids) - len(counts)} games have no source data')


if __name__ == '__main__':
    main()
