#!/usr/bin/env python3
"""Expand real CheapShark captures into a CPU-heavy replay candidate pool."""
import argparse
import json
from pathlib import Path

from title_matching import normalized


def build_pool(root):
    root = Path(root)
    jobs = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    cheap_jobs = [job for job in jobs if job['source'].startswith('CheapShark page ')]
    games = {job['game']['steamAppId']: job['game'] for job in cheap_jobs}
    if len(games) < 500:
        raise ValueError('The source capture must contain CheapShark jobs for 500 games')
    candidates = {}
    for fixture in {job['fixture'] for job in cheap_jobs}:
        rows = json.loads((root / fixture).read_text(encoding='utf-8'))
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('title'), str):
                continue
            key = str(row.get('steamAppID') or ''), normalized(row['title'])
            if key[0] and key[1]:
                candidates.setdefault(key, row)
    if len(candidates) < 400:
        raise ValueError(f'Only {len(candidates)} distinct real candidates were captured')
    pool = [candidates[key] for key in sorted(candidates)]
    expanded = [{'game': games[appid], 'source': 'CheapShark pooled',
                 'fixture': 'candidate-pool.json'} for appid in sorted(games)]
    (root / 'candidate-pool.json').write_text(json.dumps(pool, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    (root / 'expanded-manifest.json').write_text(json.dumps(expanded, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(games), len(pool)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / 'data/replay')
    args = parser.parse_args(argv)
    games, candidates = build_pool(args.root)
    print(f'Built expanded replay for {games} games against {candidates} real candidates')


if __name__ == '__main__':
    main()
