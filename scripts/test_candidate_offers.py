"""Second-store eligibility uses valid, distinct current offers."""
import unittest

from candidate_offers import normalize_deals


class CandidateOffersTest(unittest.TestCase):
    def test_keeps_cheapest_valid_offer_per_store(self):
        rows = [
            {'steamAppID': '10', 'storeID': '2', 'salePrice': '8.00', 'normalPrice': '10.00', 'dealID': 'a+b'},
            {'steamAppID': '10', 'storeID': '2', 'salePrice': '7.00', 'normalPrice': '10.00', 'dealID': 'second'},
            {'steamAppID': '10', 'storeID': '3', 'salePrice': '9.00', 'normalPrice': '9.00', 'dealID': 'third'},
            {'steamAppID': '11', 'storeID': '2', 'salePrice': '2.00', 'normalPrice': '3.00', 'dealID': 'other'},
            {'steamAppID': '10', 'storeID': '2', 'salePrice': 'NaN', 'normalPrice': '10.00', 'dealID': 'bad'},
        ]
        result = normalize_deals(rows, {'2': 'GameBillet', '3': 'Fanatical'}, {10}, '2026-11-16T00:00:00Z')
        self.assertEqual({offer['store']: offer['price'] for offer in result[10]},
                         {'GameBillet': 7.0, 'Fanatical': 9.0})
        self.assertNotIn(11, result)


if __name__ == '__main__':
    unittest.main()
