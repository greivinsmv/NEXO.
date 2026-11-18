"""HTML sources must expose an exact product and an explicit current value."""
import json
import unittest

from html_sources import SourceUnavailable, parse_gog, parse_metacritic, parse_steam, parse_walmart


def jsonld(payload):
    return ('<script type="application/ld+json">' + json.dumps(payload) + '</script>').encode()


class HtmlSourceTests(unittest.TestCase):
    def test_steam_requires_product_page_and_usd_price(self):
        raw = (b'<link rel="canonical" href="https://store.steampowered.com/app/10/Game/">'
               b'<meta itemprop="priceCurrency" content="USD"><meta itemprop="price" content="9.99">'
               b'<div id="appHubAppName">Game</div>')
        self.assertEqual(parse_steam(raw, 10)['price'], 9.99)
        with self.assertRaises(SourceUnavailable):
            parse_steam(b'<title>Age check</title>', 10)

    def test_gog_requires_exact_edition_and_available_offer(self):
        product = {'@type': ['Product', 'VideoGame'], 'name': 'Game Deluxe',
                   'url': 'https://www.gog.com/en/game/game_deluxe',
                   'offers': [{'price': '12.50', 'priceCurrency': 'USD',
                               'availability': 'https://schema.org/InStock'}]}
        self.assertEqual(parse_gog(jsonld(product), product['url'])['price'], 12.5)
        with self.assertRaises(SourceUnavailable):
            parse_gog(jsonld(product), 'https://www.gog.com/en/game/game_standard')

    def test_walmart_does_not_use_used_offer(self):
        product = {'@type': 'Product', 'name': 'Game - PlayStation 5',
                   'url': 'https://www.walmart.com/ip/Game/10', 'offers': [
                       {'price': 2, 'priceCurrency': 'USD', 'availability': 'https://schema.org/InStock',
                        'itemCondition': 'https://schema.org/UsedCondition'},
                       {'price': 9, 'priceCurrency': 'USD', 'availability': 'https://schema.org/InStock',
                        'itemCondition': 'https://schema.org/NewCondition'}]}
        self.assertEqual(parse_walmart(jsonld(product), 'https://www.walmart.com/ip/10')['price'], 9)

    def test_metacritic_requires_critic_score(self):
        item = {'@type': 'VideoGame', 'name': 'Game', 'aggregateRating':
                {'name': 'Metascore', 'ratingValue': 91, 'reviewCount': 80}}
        self.assertEqual(parse_metacritic(jsonld(item))['score'], 91)
        with self.assertRaises(SourceUnavailable):
            parse_metacritic(jsonld(item), expected_name='Another Game')
        item['aggregateRating']['name'] = 'User score'
        with self.assertRaises(SourceUnavailable):
            parse_metacritic(jsonld(item))


if __name__ == '__main__':
    unittest.main()
