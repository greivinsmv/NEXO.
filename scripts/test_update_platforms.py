"""Exact ID platform linking must reject ambiguous source games."""
import unittest

from update_platforms import parse_responses


def row(appid, game, platform):
    return {'steamId': {'value': str(appid)},
            'item': {'value': 'http://www.wikidata.org/entity/' + game},
            'platform': {'value': 'http://www.wikidata.org/entity/' + platform}}


class PlatformLinkTest(unittest.TestCase):
    def test_exact_ids_and_console_families(self):
        response = {'results': {'bindings': [
            row(10, 'Q1', 'Q5014725'), row(10, 'Q1', 'Q13361286'),
            row(11, 'Q2', 'Q19610114'), row(11, 'Q3', 'Q1406'),
            row(12, 'Q4', 'Q1406'), row(99, 'Q5', 'Q5014725'),
        ]}}
        records, stats = parse_responses([(response, 123.0)], {10, 11, 12})
        self.assertEqual({(appid, family) for appid, family, *_ in records},
                         {(10, 'PlayStation'), (10, 'Xbox')})
        self.assertEqual(stats, {'matched': 3, 'ambiguous': 1, 'linked': 2})


if __name__ == '__main__':
    unittest.main()
