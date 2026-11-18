#!/usr/bin/env python3
"""Prepare 60 real title pairs for human review without inventing labels."""
import argparse
import csv
import json
import random
from pathlib import Path

from title_matching import similarity

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('canonical', 'candidate', 'alternatives', 'expected', 'difficult',
          'suggested', 'reason', 'canonicalSteamId', 'candidateSteamId', 'source')


def make_queue(games, candidates, *, positive_count=30, negative_count=20, easy_count=10):
    by_id = {str(game['steamAppId']): game for game in games}
    by_candidate = {str(row['steamAppID']): row for row in candidates
                    if row.get('steamAppID') is not None and isinstance(row.get('title'), str)}
    positives = []
    for appid, game in by_id.items():
        row = by_candidate.get(appid)
        if row and row['title'].casefold() != game['name'].casefold():
            positives.append((similarity(game['name'], row['title']), game, row))
    positives.sort(key=lambda item: (item[0], item[1]['name']))
    if len(positives) < positive_count:
        raise ValueError(f'Only {len(positives)} real title variants available')
    hard_negatives = []
    for appid, game in by_id.items():
        best = max(((similarity(game['name'], row['title']), row)
                    for other, row in by_candidate.items() if other != appid),
                   default=None, key=lambda item: item[0])
        if best:
            hard_negatives.append((best[0], game, best[1]))
    hard_negatives.sort(key=lambda item: (-item[0], item[1]['name']))
    selected_negatives, used_ids = [], set()
    for score, game, row in hard_negatives:
        if game['steamAppId'] in used_ids or score < .4:
            continue
        selected_negatives.append((game, row))
        used_ids.add(game['steamAppId'])
        if len(selected_negatives) == negative_count:
            break
    if len(selected_negatives) < negative_count:
        raise ValueError('Not enough similar real titles for hard negatives')

    def entry(game, row, difficult, suggested, reason):
        return {'canonical': game['name'], 'candidate': row['title'], 'alternatives': '',
                'expected': '', 'difficult': str(int(difficult)), 'suggested': str(suggested),
                'reason': reason, 'canonicalSteamId': game['steamAppId'],
                'candidateSteamId': row['steamAppID'], 'source': 'CheapShark capture'}

    rows = [entry(game, row, True, 1, 'Variante observada con el mismo ID de Steam; revisar edición')
            for _, game, row in positives[:positive_count]]
    rows.extend(entry(game, row, True, 0, 'Título parecido con otro ID; revisar secuela o edición')
                for game, row in selected_negatives)
    available = [game for game in games if str(game['steamAppId']) in by_candidate]
    random.Random(7).shuffle(available)
    easy = [(game, by_candidate[str(game['steamAppId'])]) for game in available
            if game['name'].casefold() == by_candidate[str(game['steamAppId'])]['title'].casefold()]
    if len(easy) < easy_count:
        raise ValueError('Not enough exact-title control pairs')
    rows.extend(entry(game, row, False, 1, 'Control con título exacto; verificar producto')
                for game, row in easy[:easy_count])
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'data/catalog.json')
    parser.add_argument('--pool', type=Path, default=ROOT / 'data/replay/candidate-pool.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/data/title-review-queue.csv')
    args = parser.parse_args(argv)
    games = json.loads(args.catalog.read_text(encoding='utf-8'))['games']
    candidates = json.loads(args.pool.read_text(encoding='utf-8'))
    rows = make_queue(games, candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Prepared {len(rows)} real pairs, {sum(row["difficult"] == "1" for row in rows)} difficult; expected labels left blank')


if __name__ == '__main__':
    main()
