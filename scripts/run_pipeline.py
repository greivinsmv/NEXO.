#!/usr/bin/env python3
"""Run the same title-matching pipeline with live or recorded source responses."""
import argparse
import json
from pathlib import Path

from pipeline import LiveTransport, ReplayTransport, MODES, run_pipeline


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True, help='JSON list of game/source/fixture jobs')
    parser.add_argument('--transport', choices=('replay', 'live'), required=True)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--fixture-root', type=Path, required=True, help='Recorded input or live capture directory')
    parser.add_argument('--io-workers', type=int, default=4)
    parser.add_argument('--cpu-workers', type=int, default=2)
    parser.add_argument('--queue-size', type=int, default=32)
    parser.add_argument('--latency-ms', type=float, default=0)
    parser.add_argument('--jitter-ms', type=float, default=0)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output', type=Path, help='Write results and metrics as JSON')
    args = parser.parse_args(argv)
    jobs = json.loads(args.manifest.read_text(encoding='utf-8'))
    if not isinstance(jobs, list):
        parser.error('Manifest must be a JSON list')
    transport = (ReplayTransport(args.fixture_root, args.latency_ms / 1000, args.jitter_ms / 1000, args.seed)
                 if args.transport == 'replay' else LiveTransport(args.fixture_root))
    output = run_pipeline(jobs, transport.fetch, mode=args.mode,
                          io_workers=args.io_workers, cpu_workers=args.cpu_workers, queue_size=args.queue_size)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output['metrics'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
