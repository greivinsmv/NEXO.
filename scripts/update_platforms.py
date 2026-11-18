#!/usr/bin/env python3
"""Link console releases by exact Steam ID using Wikidata platform statements."""
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from build_catalog import CACHE, cache_fresh
from catalog_db import connect, export_catalog

USER_AGENT = 'NEXO academic catalog/0.3 (https://github.com/greivinsmv/NEXO)'
BATCH_SIZE = 50
PLATFORM_FAMILIES = {
    'Q10677': 'PlayStation', 'Q10680': 'PlayStation', 'Q10683': 'PlayStation',
    'Q170325': 'PlayStation', 'Q188808': 'PlayStation', 'Q5014725': 'PlayStation',
    'Q63184502': 'PlayStation',
    'Q132020': 'Xbox', 'Q48263': 'Xbox', 'Q13361286': 'Xbox', 'Q98973368': 'Xbox',
    'Q19610114': 'Nintendo Switch', 'Q65458682': 'Nintendo Switch',
    'Q122761124': 'Nintendo Switch 2',
}


def query_url(ids):
    values = ' '.join('"' + str(appid) + '"' for appid in ids)
    query = ('SELECT ?steamId ?item ?platform WHERE { VALUES ?steamId { ' + values +
             ' } ?item wdt:P1733 ?steamId . ?item wdt:P400 ?platform . }')
    return 'https://query.wikidata.org/sparql?' + urlencode({'query': query, 'format': 'json'})


def fetch_batch(ids):
    key = hashlib.sha256(','.join(map(str, ids)).encode()).hexdigest()[:16]
    path = CACHE / f'wikidata-platforms-{key}.json'
    if not cache_fresh(path, 7):
        for attempt in range(4):
            try:
                request = Request(query_url(ids), headers={'User-Agent': USER_AGENT,
                                                           'Accept': 'application/sparql-results+json'})
                with urlopen(request, timeout=45) as response:
                    raw = response.read()
                data = json.loads(raw)
                if not isinstance(data.get('results', {}).get('bindings'), list):
                    raise ValueError('Invalid Wikidata response')
                temporary = path.with_suffix('.json.tmp')
                temporary.write_bytes(raw)
                temporary.replace(path)
                break
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                if attempt == 3:
                    raise RuntimeError(f'Wikidata batch failed: {error}') from error
                delay = min(30, 2 ** attempt + 2)
                if isinstance(error, HTTPError) and error.code == 429:
                    try:
                        delay = min(60, max(delay, int(error.headers.get('Retry-After') or 30)))
                    except ValueError:
                        delay = 30
                time.sleep(delay)
        time.sleep(2)
    return json.loads(path.read_text(encoding='utf-8')), path.stat().st_mtime


def parse_responses(responses, requested):
    """Return evidence rows; ignore duplicate Wikidata games for one Steam ID."""
    requested = set(requested)
    by_id = defaultdict(lambda: defaultdict(set))
    captured = {}
    for response, timestamp in responses:
        for row in response.get('results', {}).get('bindings', []):
            try:
                appid = int(row['steamId']['value'])
                game_id = row['item']['value'].rsplit('/', 1)[1]
                platform_id = row['platform']['value'].rsplit('/', 1)[1]
            except (KeyError, ValueError, TypeError):
                continue
            if (appid not in requested or not re.fullmatch(r'Q\d+', game_id)
                    or not re.fullmatch(r'Q\d+', platform_id)):
                continue
            by_id[appid][game_id].add(platform_id)
            captured[appid] = timestamp
    records = []
    ambiguous = 0
    for appid, games in by_id.items():
        if len(games) != 1:
            ambiguous += 1
            continue
        game_id, platform_ids = next(iter(games.items()))
        for platform_id in sorted(platform_ids):
            family = PLATFORM_FAMILIES.get(platform_id)
            if family:
                records.append((appid, family, game_id, platform_id, captured[appid]))
    return records, {'matched': len(by_id), 'ambiguous': ambiguous,
                     'linked': len(by_id) - ambiguous}


def main():
    connection = connect()
    try:
        ids = [row[0] for row in connection.execute(
            'SELECT steam_app_id FROM games WHERE active = 1 ORDER BY position')]
    finally:
        connection.close()
    if len(ids) < 500:
        raise ValueError('Incomplete catalog; keeping previous platform evidence')
    responses = []
    for offset in range(0, len(ids), BATCH_SIZE):
        batch = ids[offset:offset + BATCH_SIZE]
        data, timestamp = fetch_batch(batch)
        responses.append((data, timestamp))
        print(f'Wikidata batch {offset // BATCH_SIZE + 1}/{(len(ids) + BATCH_SIZE - 1) // BATCH_SIZE}', flush=True)
    records, stats = parse_responses(responses, ids)
    families = {record[1] for record in records}
    if stats['linked'] < 400 or not {'PlayStation', 'Xbox', 'Nintendo Switch'} <= families:
        raise ValueError(f'Insufficient platform evidence: {stats}, {sorted(families)}')
    connection = connect()
    try:
        with connection:
            current = {row[0] for row in connection.execute('SELECT steam_app_id FROM games WHERE active = 1')}
            if current != set(ids):
                raise ValueError('Catalog changed during platform capture')
            connection.execute('DELETE FROM game_platforms WHERE steam_app_id IN '
                               '(SELECT steam_app_id FROM games WHERE active = 1)')
            connection.executemany(
                'INSERT INTO game_platforms(steam_app_id, platform, wikidata_game_id, '
                'wikidata_platform_id, captured_at) VALUES (?, ?, ?, ?, ?)',
                ((appid, family, game_id, platform_id,
                  datetime.fromtimestamp(timestamp, timezone.utc).isoformat())
                 for appid, family, game_id, platform_id, timestamp in records),
            )
    finally:
        connection.close()
    export_catalog()
    print(f"Linked {stats['linked']} games; {stats['ambiguous']} ambiguous IDs skipped; "
          f"{len(records)} console platform statements saved")


if __name__ == '__main__':
    main()
