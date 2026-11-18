"""The expanded replay deduplicates stores but keeps every product title."""
import json
import tempfile
import unittest
from pathlib import Path

from build_replay_pool import build_pool


class ReplayPoolTests(unittest.TestCase):
    def test_uses_real_candidate_rows_without_duplicate_store_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [{'steamAppID': str(appid), 'title': f'Game {appid}', 'storeID': '1'}
                    for appid in range(1, 501)]
            rows.append({'steamAppID': '1', 'title': 'Game 1', 'storeID': '2'})
            (root / 'deals.json').write_text(json.dumps(rows))
            jobs = [{'game': {'steamAppId': appid, 'name': f'Game {appid}'},
                     'source': 'CheapShark page 0', 'fixture': 'deals.json'} for appid in range(1, 501)]
            (root / 'manifest.json').write_text(json.dumps(jobs))
            self.assertEqual(build_pool(root), (500, 500))
            self.assertEqual(len(json.loads((root / 'candidate-pool.json').read_text())), 500)


if __name__ == '__main__':
    unittest.main()
