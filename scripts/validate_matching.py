#!/usr/bin/env python3
"""Report precision and recall from a team-reviewed title-pair CSV."""
import argparse
import csv
import json
from pathlib import Path

from title_matching import match_game_candidates


def evaluate(rows, *, minimum=60, hard_minimum=50, threshold=.82):
    rows = list(rows)
    if len(rows) < minimum:
        raise ValueError(f'Need at least {minimum} reviewed pairs, got {len(rows)}')
    hard = sum(row.get('difficult', '').strip().lower() in ('1', 'true', 'yes', 'sí', 'si') for row in rows)
    if hard < hard_minimum:
        raise ValueError(f'Need at least {hard_minimum} difficult cases, got {hard}')
    matrix = {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0}
    for index, row in enumerate(rows, 1):
        if row.get('expected') not in ('0', '1'):
            raise ValueError(f'Row {index} needs expected=0 or 1')
        game = {'steamAppId': index, 'name': row['canonical'],
                'altTitles': [name.strip() for name in row.get('alternatives', '').split('|') if name.strip()]}
        result = match_game_candidates(game, [{'title': row['candidate']}], threshold)
        actual = result['accepted'] is not None
        expected = row['expected'] == '1'
        matrix['tp' if actual and expected else 'fp' if actual else 'fn' if expected else 'tn'] += 1
    precision = matrix['tp'] / (matrix['tp'] + matrix['fp']) if matrix['tp'] + matrix['fp'] else None
    recall = matrix['tp'] / (matrix['tp'] + matrix['fn']) if matrix['tp'] + matrix['fn'] else None
    return {'pairs': len(rows), 'difficultPairs': hard, 'threshold': threshold,
            **matrix, 'precision': precision, 'recall': recall}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reviewed_csv', type=Path)
    parser.add_argument('--threshold', type=float, default=.82)
    args = parser.parse_args(argv)
    with args.reviewed_csv.open(newline='', encoding='utf-8-sig') as file:
        print(json.dumps(evaluate(csv.DictReader(file), threshold=args.threshold), indent=2))


if __name__ == '__main__':
    main()
