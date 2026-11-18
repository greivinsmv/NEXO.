"""Extract only explicit product data from public HTML source pages."""
import json
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urlparse

from title_matching import similarity


class SourceUnavailable(ValueError):
    """A response is an age gate, block page, or has no explicit source data."""


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.canonical, self.scripts, self.app_name = {}, None, [], None
        self._script = None
        self._app_name = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = attrs.get('itemprop') or attrs.get('property') or attrs.get('name')
            if key and attrs.get('content') is not None:
                self.meta.setdefault(key, attrs['content'])
        elif tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href')
        elif tag == 'script' and attrs.get('type') == 'application/ld+json':
            self._script = []
        elif attrs.get('id') == 'appHubAppName':
            self._app_name = True

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)
        if self._app_name:
            self.app_name = (self.app_name or '') + data

    def handle_endtag(self, tag):
        if tag == 'script' and self._script is not None:
            try:
                value = json.loads(''.join(self._script))
                self.scripts.extend(value if isinstance(value, list) else [value])
            except (json.JSONDecodeError, TypeError):
                pass
            self._script = None
        if tag == 'div' and self._app_name:
            self._app_name = False


def document(raw):
    parser = DocumentParser()
    parser.feed(raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else raw)
    return parser


def price(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise SourceUnavailable('No valid explicit price') from None
    if not number.is_finite() or number <= 0:
        raise SourceUnavailable('No valid explicit price')
    return float(number)


def jsonld_product(page, product_types):
    for entry in page.scripts:
        if not isinstance(entry, dict):
            continue
        types = entry.get('@type')
        types = {types} if isinstance(types, str) else set(types or [])
        if types.intersection(product_types) and isinstance(entry.get('name'), str):
            return entry
    raise SourceUnavailable('No product JSON-LD')


def parse_steam(raw, appid):
    page = document(raw)
    path = urlparse(page.canonical or '').path
    if not path.startswith(f'/app/{appid}/'):
        raise SourceUnavailable(f'Steam app {appid} redirected or unavailable')
    if page.meta.get('priceCurrency') != 'USD':
        raise SourceUnavailable('Steam HTML is not priced in USD')
    name = (page.app_name or '').strip()
    if not name:
        raise SourceUnavailable('Steam HTML has no game title')
    return {'source': 'Steam Store HTML', 'title': name,
            'price': price(page.meta.get('price')), 'currency': 'USD',
            'url': page.canonical, 'format': 'Digital', 'platform': 'PC'}


def parse_gog(raw, expected_url):
    page = document(raw)
    product = jsonld_product(page, {'Product', 'VideoGame'})
    if urlparse(product.get('url') or '').path.rstrip('/') != urlparse(expected_url).path.rstrip('/'):
        raise SourceUnavailable('GOG product URL differs from the expected edition')
    for offer in product.get('offers') or []:
        if not isinstance(offer, dict) or offer.get('priceCurrency') != 'USD':
            continue
        seller = offer.get('seller') or {}
        if isinstance(seller, dict) and seller.get('name') not in (None, 'GOG.com'):
            continue
        if offer.get('availability') != 'https://schema.org/InStock':
            continue
        return {'source': 'GOG HTML', 'title': product['name'],
                'price': price(offer.get('price')), 'currency': 'USD',
                'url': offer.get('url') or product['url'], 'format': 'Digital', 'platform': 'PC'}
    raise SourceUnavailable('GOG HTML has no available USD offer')


def parse_walmart(raw, expected_url):
    page = document(raw)
    product = jsonld_product(page, {'Product'})
    if urlparse(product.get('url') or page.canonical or '').path.split('/')[-1] != urlparse(expected_url).path.split('/')[-1]:
        raise SourceUnavailable('Walmart product ID differs from the expected product')
    for offer in product.get('offers') or []:
        if not isinstance(offer, dict) or offer.get('priceCurrency') != 'USD':
            continue
        if offer.get('availability') != 'https://schema.org/InStock':
            continue
        if offer.get('itemCondition') != 'https://schema.org/NewCondition':
            continue
        return {'source': 'Walmart HTML', 'title': product['name'],
                'price': price(offer.get('price')), 'currency': 'USD',
                'url': offer.get('url') or expected_url,
                'format': 'Por verificar', 'platform': 'Por verificar'}
    raise SourceUnavailable('Walmart HTML has no new available USD offer')


def parse_metacritic(raw, expected_name=None):
    page = document(raw)
    product = jsonld_product(page, {'VideoGame'})
    if expected_name and similarity(expected_name, product['name']) < .82:
        raise SourceUnavailable('Metacritic title differs from the expected game')
    rating = product.get('aggregateRating') or {}
    if not isinstance(rating, dict) or rating.get('name') != 'Metascore':
        raise SourceUnavailable('Metacritic HTML has no critic rating')
    value = price(rating.get('ratingValue'))
    if value > 100:
        raise SourceUnavailable('Metacritic rating exceeds 100')
    return {'source': 'Metacritic HTML', 'title': product['name'],
            'score': value, 'reviewCount': rating.get('reviewCount'),
            'url': product.get('url')}
