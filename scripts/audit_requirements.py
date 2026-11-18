#!/usr/bin/env python3
"""Report catalog coverage against the measurable parts of the course brief."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(games):
    platforms = Counter()
    stores = Counter()
    for game in games:
        names = game.get('platforms') or [game.get('platform') or 'Sin plataforma']
        if isinstance(names, str):
            names = [names]
        platforms.update(names)
        stores.update({offer['store'] for offer in game.get('offers', []) if offer.get('price') is not None})
    return {
        'games': len(games),
        'platforms': dict(platforms),
        'gamesWithTwoPrices': sum(len({offer['store'] for offer in game.get('offers', [])
                                       if offer.get('price') is not None}) >= 2 for game in games),
        'storesWithOffers': dict(stores),
        'gamesWithAlternateTitles': sum(bool(game.get('altTitles')) for game in games),
        'gamesWithReleaseDate': sum(bool(game.get('releaseDate')) for game in games),
        'gamesWithMetacritic': sum(game.get('metacritic') is not None for game in games),
        'gamesWithSteamUserScore': sum(game.get('steamUserScore') is not None for game in games),
        'gamesWithHLTB': sum(game.get('hltbId') is not None for game in games),
        'gamesWithMainStoryHours': sum(game.get('hours') is not None for game in games),
    }


if __name__ == '__main__':
    games = json.loads((ROOT / 'data/catalog.json').read_text(encoding='utf-8'))['games']
    print(json.dumps(audit(games), ensure_ascii=False, indent=2))
