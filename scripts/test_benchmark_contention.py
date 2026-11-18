"""Check contention strategies against a known count and a controlled race."""
import unittest
from collections import Counter

from benchmark_contention import STRATEGIES, aggregate, demonstrate_race


class ContentionTest(unittest.TestCase):
    def test_three_strategies_keep_all_updates(self):
        values = ['PC', 'Xbox', 'PC', 'PlayStation'] * 100
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                self.assertEqual(aggregate(values, 4, strategy), Counter(values))

    def test_unprotected_read_modify_write_loses_updates(self):
        self.assertEqual(demonstrate_race(4, 12),
                         {'expected': 48, 'observed': 12, 'lostUpdates': 36})


if __name__ == '__main__':
    unittest.main()
