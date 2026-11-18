"""Offline, reproducible checks for the three required pipeline semantics."""
import json
import tempfile
import unittest
from pathlib import Path

from benchmark_pipeline import metrics
from pipeline import ReplayTransport, parse_json_candidates, run_pipeline
from title_matching import normalized, match_game_candidates


class PipelineTests(unittest.TestCase):
    def test_same_matches_in_all_three_modes(self):
        games = [
            {'steamAppId': 1, 'name': 'The Witcher 3: Wild Hunt', 'altTitles': ['Witcher III Wild Hunt']},
            {'steamAppId': 2, 'name': 'Dark Souls III', 'altTitles': []},
            {'steamAppId': 3, 'name': 'Hades II', 'altTitles': []},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jobs = []
            for game in games:
                for source in ('shop-a', 'shop-b'):
                    fixture = f"{source}/{game['steamAppId']}.json"
                    path = root / fixture
                    path.parent.mkdir(exist_ok=True)
                    title = game['name'].replace('III', '3').replace('II', '2')
                    path.write_text(json.dumps({'candidates': [
                        {'title': title, 'price': 9.99},
                        {'title': 'Borderlands 3', 'price': 1.00},
                    ]}))
                    jobs.append({'game': game, 'source': source, 'fixture': fixture})
            transport = ReplayTransport(root, latency=.01, jitter=.01, seed=7)
            outputs = [run_pipeline(jobs, transport.fetch, mode=mode, io_workers=3, cpu_workers=2,
                                    queue_size=2) for mode in ('sequential', 'concurrent', 'parallel')]
            self.assertEqual(outputs[0]['results'], outputs[1]['results'])
            self.assertEqual(outputs[0]['results'], outputs[2]['results'])
            self.assertTrue(all(item['accepted'] for item in outputs[0]['results']))
            self.assertTrue(all(output['metrics']['failed'] == 0 for output in outputs))

    def test_special_edition_needs_review(self):
        game = {'steamAppId': 4, 'name': 'Control', 'altTitles': []}
        result = match_game_candidates(game, [{'title': 'Control Ultimate Edition'}])
        self.assertTrue(result['doubtful'])
        self.assertIsNone(result['accepted'])
        self.assertEqual(normalized('DARK SOULS III — PC'), 'dark souls 3')
        self.assertEqual(normalized('BioShock™ Remastered'), normalized('BioShock Remastered'))
        self.assertEqual(normalized("Assassin’s Creed"), normalized('Assassins Creed'))
        self.assertEqual(normalized('Command & Conquer'), normalized('Command and Conquer'))

    def test_real_source_shapes_and_duplicate_store_deals(self):
        game = {'steamAppId': 10, 'name': 'Dark Souls III'}
        steam = json.dumps({'10': {'success': True, 'data': {
            'name': 'Dark Souls III', 'price_overview': {'final': 999}}}}).encode()
        rows = json.dumps([
            {'title': 'Dark Souls 3', 'steamAppID': '10', 'storeID': '1'},
            {'title': 'Dark Souls 3', 'steamAppID': '10', 'storeID': '2'},
            {'title': 'Dark Souls 2', 'steamAppID': '20', 'storeID': '1'},
        ]).encode()
        self.assertEqual(parse_json_candidates({'game': game, 'source': 'Steam Store'}, steam)[0]['price'], 999)
        candidates = parse_json_candidates({'game': game, 'source': 'CheapShark'}, rows)
        matched = match_game_candidates(game, candidates)
        self.assertTrue(matched['accepted'])
        self.assertFalse(matched['doubtful'])

    def test_failed_source_remains_visible_in_metrics(self):
        game = {'steamAppId': 5, 'name': 'Celeste'}
        with tempfile.TemporaryDirectory() as directory:
            output = run_pipeline([{'game': game, 'source': 'missing', 'fixture': 'missing.json'}],
                                  ReplayTransport(directory).fetch, mode='concurrent')
            self.assertEqual(output['metrics']['retried'], 1)
            self.assertEqual(output['metrics']['failed'], 1)
            self.assertEqual(output['results'], [])

    def test_speedup_uses_separate_absolute_and_relative_baselines(self):
        result = metrics([4.0, 5.0, 6.0, 5.0, 5.0], baseline=10.0,
                         one_worker=8.0, workers=2)
        self.assertEqual(result['medianSeconds'], 5.0)
        self.assertEqual(result['absoluteSpeedup'], 2.0)
        self.assertEqual(result['relativeSpeedup'], 1.6)
        self.assertEqual(result['efficiency'], .8)


if __name__ == '__main__':
    unittest.main()
