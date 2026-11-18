"""A catalog rebuild must publish two distinct sourced store prices per game."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import catalog_db


class TwoStoreCatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name, path in [('DATABASE', root / 'catalog.sqlite'),
                           ('PUBLIC_JSON', root / 'catalog.json'),
                           ('HISTORY_JSON', root / 'history.json')]:
            override = patch.object(catalog_db, name, path)
            override.start()
            self.addCleanup(override.stop)
        self.games = [{
            'steamAppId': appid, 'slug': f'game-{appid}', 'name': f'Game {appid}',
            'description': '', 'platform': 'PC', 'price': 10.0, 'regular': 10.0,
            'currentPlayers': 10, 'relevanceScore': 1.0, 'coverUrl': 'https://example.com/cover.jpg',
            'genres': [], 'screenshots': [], 'featuredAchievements': [],
            'offers': [{'store': 'Steam', 'price': 10.0, 'regular': 10.0,
                        'url': f'https://store.steampowered.com/app/{appid}/',
                        'capturedAt': '2026-11-15T00:00:00Z'}],
        } for appid in range(1, 501)]
        self.candidates = [{'steam_app_id': appid, 'source_page': appid % 2,
                            'page_rank': appid, 'name': f'Game {appid}'}
                           for appid in range(1, 501)]
        self.snapshot = {'capturedAt': '2026-11-16T00:00:00Z',
                         'source': 'Steam Store; two-store verified', 'games': self.games}

    def test_saves_second_store_atomically_with_games(self):
        secondary = {appid: [{'store': 'GameBillet', 'price': 8.0, 'regular': 10.0,
                              'url': 'https://www.cheapshark.com/redirect?dealID=test',
                              'capturedAt': '2026-11-16T00:00:00Z'}]
                     for appid in range(1, 501)}
        secondary[1][0]['store'] = 'GOG'
        catalog_db.save_catalog(self.snapshot, self.candidates, secondary)
        exported = json.loads(catalog_db.PUBLIC_JSON.read_text())['games']
        self.assertEqual(len(exported), 500)
        self.assertEqual({offer['store'] for offer in exported[0]['offers']}, {'Steam', 'GOG'})
        self.assertTrue(all({offer['store'] for offer in game['offers']} == {'Steam', 'GameBillet'}
                            for game in exported[1:]))
        with sqlite3.connect(catalog_db.DATABASE) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM retailer_offers').fetchone()[0], 500)
            self.assertEqual(connection.execute(
                "SELECT observed_at FROM offer_history WHERE steam_app_id = 1 AND store = 'Steam'"
            ).fetchone()[0], '2026-11-15T00:00:00Z')
            self.assertEqual(connection.execute(
                "SELECT source FROM offer_history WHERE steam_app_id = 1 AND store = 'GOG'"
            ).fetchone()[0], 'GOG Catalog')

    def test_rejects_incomplete_second_store_capture_before_writing(self):
        with self.assertRaisesRegex(ValueError, 'second store'):
            catalog_db.save_catalog(self.snapshot, self.candidates, {})
        self.assertFalse(catalog_db.DATABASE.exists())


if __name__ == '__main__':
    unittest.main()
