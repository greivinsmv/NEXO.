"""Validate rating parsing without relying on the external service."""
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from update_steam_reviews import captured_at, review_counts


class ReviewCountsTest(unittest.TestCase):
    def test_valid_counts(self):
        self.assertEqual(review_counts({'positive': '1,234', 'negative': 56}), (1234, 56))

    def test_no_votes_cannot_be_scored(self):
        self.assertIsNone(review_counts({'positive': 0, 'negative': 0}))

    def test_invalid_negative_count(self):
        self.assertIsNone(review_counts({'positive': 4, 'negative': -1}))

    def test_cached_response_keeps_its_original_date(self):
        with TemporaryDirectory() as directory:
            response = Path(directory) / 'response.json'
            response.write_text('{}', encoding='utf-8')
            self.assertAlmostEqual(response.stat().st_mtime,
                                   datetime.fromisoformat(captured_at(response)).timestamp(),
                                   places=2)


if __name__ == '__main__':
    unittest.main()
