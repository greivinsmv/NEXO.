"""Ensure coverage is counted per distinct store and platform."""
import unittest

from audit_requirements import audit


class AuditTest(unittest.TestCase):
    def test_distinct_stores_count_as_two_prices(self):
        result = audit([
            {'platforms': ['PC', 'Xbox'], 'offers': [
                {'store': 'Steam', 'price': 10}, {'store': 'Steam', 'price': 9},
                {'store': 'GOG', 'price': 8}], 'steamUserScore': 0},
            {'platform': 'PC', 'offers': [{'store': 'Steam', 'price': 4}]},
        ])
        self.assertEqual(result['gamesWithTwoPrices'], 1)
        self.assertEqual(result['platforms'], {'PC': 2, 'Xbox': 1})
        self.assertEqual(result['gamesWithSteamUserScore'], 1)


if __name__ == '__main__':
    unittest.main()
