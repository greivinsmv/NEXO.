"""Review queues require real source pairs and leave human labels empty."""
import unittest

from prepare_title_review import make_queue


class ReviewQueueTests(unittest.TestCase):
    def test_suggests_but_never_fills_expected_label(self):
        games = [{'steamAppId': 1, 'name': 'Dark Souls II'},
                 {'steamAppId': 2, 'name': 'Dark Souls III'},
                 {'steamAppId': 3, 'name': 'Game Exact'}]
        candidates = [{'steamAppID': '1', 'title': 'Dark Souls 2'},
                      {'steamAppID': '2', 'title': 'Dark Souls 3'},
                      {'steamAppID': '3', 'title': 'Game Exact'}]
        rows = make_queue(games, candidates, positive_count=2, negative_count=1, easy_count=1)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row['expected'] == '' for row in rows))
        self.assertEqual(sum(row['difficult'] == '1' for row in rows), 3)
        self.assertEqual(rows[2]['suggested'], '0')
        self.assertNotEqual(rows[2]['canonicalSteamId'], rows[2]['candidateSteamId'])


if __name__ == '__main__':
    unittest.main()
