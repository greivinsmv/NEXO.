"""The scheduled rebuild must not silently use old public listings."""
import os
import json
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from build_catalog import cache_fresh, previous_verified_games


class CatalogCacheTests(unittest.TestCase):
    def test_source_cache_expires_but_pinned_archive_can_be_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'response.json'
            path.write_text('{}')
            self.assertTrue(cache_fresh(path, 7))
            old = time.time() - 8 * 86400
            os.utime(path, (old, old))
            self.assertFalse(cache_fresh(path, 7))
            self.assertTrue(cache_fresh(path, None))

    def test_prior_candidate_keeps_only_recent_second_store(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.sqlite'
            with sqlite3.connect(path) as connection:
                connection.executescript('''
                    CREATE TABLE games(steam_app_id INTEGER, payload_json TEXT, active INTEGER);
                    CREATE TABLE retailer_offers(steam_app_id INTEGER, store TEXT, price_usd REAL,
                        regular_usd REAL, url TEXT, captured_at TEXT);
                ''')
                for appid in (1, 2):
                    connection.execute('INSERT INTO games VALUES(?, ?, 1)',
                                       (appid, json.dumps({'name': f'Game {appid}', 'currentPlayers': 50,
                                                           'estimatedOwners': 1000, 'price': 10})))
                now = datetime.now(timezone.utc)
                connection.executemany('INSERT INTO retailer_offers VALUES(?, ?, ?, ?, ?, ?)', [
                    (1, 'GOG', 9.0, 10.0, 'https://example.com/1', now.isoformat()),
                    (2, 'GOG', 9.0, 10.0, 'https://example.com/2',
                     (now - timedelta(days=8)).isoformat()),
                ])
            with patch('build_catalog.DATABASE', path):
                candidates, offers = previous_verified_games()
            self.assertEqual(set(candidates), {'1', '2'})
            self.assertEqual(set(offers), {1})


if __name__ == '__main__':
    unittest.main()
