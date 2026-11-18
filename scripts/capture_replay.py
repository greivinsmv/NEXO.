#!/usr/bin/env python3
"""Record real Steam and CheapShark JSON for every published game."""
import argparse
import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from pipeline import LiveTransport

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/catalog.json'
CACHE = ROOT / '.catalog-cache'


def fresh(path, max_age_days):
    return path.is_file() and time.time() - path.stat().st_mtime < max_age_days * 86400


def valid_response(source, raw, appid):
    data = json.loads(raw)
    if source == 'Steam Store':
        entry = data.get(str(appid)) if isinstance(data, dict) else None
        if not isinstance(entry, dict) or not entry.get('success') or not isinstance(entry.get('data'), dict):
            raise ValueError(f'Invalid Steam response for {appid}')
        if not isinstance(entry['data'].get('name'), str):
            raise ValueError(f'Steam response has no title for {appid}')
    elif source == 'CheapShark':
        if not isinstance(data, list) or len(data) >= 100:
            raise ValueError(f'CheapShark response may be truncated for {appid}')
        if any(str(row.get('steamAppID')) != str(appid) for row in data if isinstance(row, dict)):
            raise ValueError(f'CheapShark response includes another game for {appid}')
    else:
        raise ValueError(f'Unknown source: {source}')
    return data


def valid_batch_response(raw, appids):
    rows = json.loads(raw)
    allowed = {str(appid) for appid in appids}
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('CheapShark batch is not a deal list')
    if any(str(row.get('steamAppID')) not in allowed for row in rows):
        raise ValueError('CheapShark batch includes another game')
    if len(rows) > 60:
        raise ValueError('CheapShark exceeded the requested page size')
    return rows


def capture(catalog_path, cache_dir, output_dir, max_age_days=7, transport=None):
    games = json.loads(Path(catalog_path).read_text(encoding='utf-8'))['games']
    if len(games) < 500 or len({game['steamAppId'] for game in games}) != len(games):
        raise ValueError('Replay requires 500 distinct published games')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    transport = transport or LiveTransport(output_dir, per_domain=1, interval=2.5)
    sources = {'Steam Store': 0, 'CheapShark': 0}
    jobs, hashes, observed_at = [], {}, {}
    for page in range(2):
        source = Path(cache_dir) / f'steamspy-page-{page}.json'
        if not fresh(source, max_age_days):
            raise ValueError(f'Stage-0 response is missing or stale: {source}')
        target = output_dir / 'stage0' / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        name = str(target.relative_to(output_dir))
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        observed_at[name] = datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()
    for index, game in enumerate(games, 1):
        appid = game['steamAppId']
        descriptor = {'steamAppId': appid, 'name': game['name'], 'altTitles': game.get('altTitles') or []}
        steam_url = 'https://store.steampowered.com/api/appdetails?' + urlencode(
            {'appids': appid, 'cc': 'us', 'l': 'english'})
        steam_fixture = f'steam/{appid}.json'
        steam_target = output_dir / steam_fixture
        steam_cache = Path(cache_dir) / f'steam-{appid}.json'
        if not fresh(steam_target, max_age_days):
            steam_target.parent.mkdir(parents=True, exist_ok=True)
            if fresh(steam_cache, max_age_days):
                shutil.copy2(steam_cache, steam_target)
            else:
                transport.fetch({'url': steam_url, 'fixture': steam_fixture})
        valid_response('Steam Store', steam_target.read_bytes(), appid)
        if fresh(steam_cache, max_age_days) and steam_target.read_bytes() == steam_cache.read_bytes():
            shutil.copystat(steam_cache, steam_target)
        sources['Steam Store'] += 1
        jobs.append({'game': descriptor, 'source': 'Steam Store',
                     'fixture': steam_fixture, 'url': steam_url})
        hashes[steam_fixture] = hashlib.sha256(steam_target.read_bytes()).hexdigest()
        observed_at[steam_fixture] = datetime.fromtimestamp(steam_target.stat().st_mtime, timezone.utc).isoformat()
        if index % 50 == 0:
            print(f'Prepared {index}/{len(games)} Steam responses', flush=True)
    for offset in range(0, len(games), 20):
        batch = games[offset:offset + 20]
        appids = [game['steamAppId'] for game in batch]
        for page in range(12):
            cheap_url = 'https://www.cheapshark.com/api/1.0/deals?' + urlencode(
                {'steamAppID': ','.join(map(str, appids)), 'pageSize': 60, 'pageNumber': page})
            cheap_fixture = f'cheapshark/batch-{offset // 20:03d}-page-{page}.json'
            cheap_target = output_dir / cheap_fixture
            if not fresh(cheap_target, max_age_days):
                transport.fetch({'url': cheap_url, 'fixture': cheap_fixture})
            rows = valid_batch_response(cheap_target.read_bytes(), appids)
            hashes[cheap_fixture] = hashlib.sha256(cheap_target.read_bytes()).hexdigest()
            observed_at[cheap_fixture] = datetime.fromtimestamp(cheap_target.stat().st_mtime, timezone.utc).isoformat()
            for game in batch:
                descriptor = {'steamAppId': game['steamAppId'], 'name': game['name'],
                              'altTitles': game.get('altTitles') or []}
                jobs.append({'game': descriptor, 'source': f'CheapShark page {page}',
                             'fixture': cheap_fixture, 'url': cheap_url})
                sources['CheapShark'] += 1
            if len(rows) < 60:
                break
        else:
            raise ValueError(f'CheapShark batch {offset // 20} exceeded 12 pages')
        print(f'Captured CheapShark batch {offset // 20 + 1}/{(len(games) + 19) // 20}', flush=True)
    metadata = {'capturedAt': datetime.now(timezone.utc).isoformat(), 'games': len(games),
                'jobs': len(jobs), 'sources': sources, 'sha256': hashes, 'observedAt': observed_at,
                'note': 'Steam files may be cached JSON responses; CheapShark files are original response bytes.'}
    (output_dir / 'manifest.json').write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output_dir / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--cache-dir', type=Path, default=CACHE)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/replay')
    parser.add_argument('--cache-days', type=float, default=7)
    args = parser.parse_args(argv)
    if not 0 < args.cache_days <= 30:
        parser.error('--cache-days must be between 0 and 30')
    result = capture(args.catalog, args.cache_dir, args.output, args.cache_days)
    print(f"Saved {result['jobs']} real-source jobs for {result['games']} games to {args.output}")


if __name__ == '__main__':
    main()
