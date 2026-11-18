#!/usr/bin/env python3
"""Reproducible replay sweeps for the three pipeline modes."""
import argparse
import csv
import hashlib
import json
import os
import statistics
from pathlib import Path

from pipeline import ReplayTransport, run_pipeline


def metrics(samples, baseline, one_worker, workers):
    median = statistics.median(samples)
    absolute = baseline / median
    relative = one_worker / median if one_worker else None
    efficiency = relative / workers if relative else None
    karp_flatt = ((1 / relative - 1 / workers) / (1 - 1 / workers)
                  if relative and workers > 1 else None)
    return {'medianSeconds': median, 'minSeconds': min(samples), 'maxSeconds': max(samples),
            'absoluteSpeedup': absolute, 'relativeSpeedup': relative,
            'efficiency': efficiency, 'karpFlatt': karp_flatt}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='CSV results')
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--latency-ms', type=float, default=80)
    parser.add_argument('--jitter-ms', type=float, default=20)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--io-workers', type=int, default=8, help='Fixed I/O workers for CPU sweep')
    parser.add_argument('--queue-size', type=int, default=32)
    args = parser.parse_args(argv)
    if args.repetitions < 5:
        parser.error('Formal measurements require at least five repetitions')
    jobs = json.loads(args.manifest.read_text(encoding='utf-8'))
    if not isinstance(jobs, list) or not jobs:
        parser.error('Manifest must contain jobs')
    transport = ReplayTransport(args.fixture_root, args.latency_ms / 1000,
                                args.jitter_ms / 1000, args.seed)
    cpu_count = os.cpu_count() or 1
    cpu_sweep = sorted({min(64, value) for value in (1, 2, 4, cpu_count, 2 * cpu_count)})
    configurations = [('sequential', 1, 1)]
    configurations += [('concurrent', workers, 1) for workers in (1, 2, 4, 8, 16, 32, 64)]
    configurations += [('parallel', args.io_workers, workers) for workers in cpu_sweep]
    observations, signature = {}, None
    for mode, io_workers, cpu_workers in configurations:
        samples = []
        for repetition in range(args.repetitions):
            output = run_pipeline(jobs, transport.fetch, mode=mode, io_workers=io_workers,
                                  cpu_workers=cpu_workers, queue_size=args.queue_size)
            digest = hashlib.sha256(json.dumps(output['results'], sort_keys=True).encode()).hexdigest()
            if signature is None:
                signature = digest
            elif signature != digest:
                raise RuntimeError(f'Output differs in {mode}, I/O {io_workers}, CPU {cpu_workers}')
            samples.append(output['metrics'])
            print(mode, io_workers, cpu_workers, repetition + 1, samples[-1]['totalSeconds'], flush=True)
        observations[(mode, io_workers, cpu_workers)] = samples
    sample_median = lambda key, field: statistics.median(row[field] for row in observations[key])
    baseline = sample_median(('sequential', 1, 1), 'totalSeconds')
    baseline_download = sample_median(('sequential', 1, 1), 'downloadStageSeconds')
    baseline_match = sample_median(('sequential', 1, 1), 'matchStageSeconds')
    concurrent_one = sample_median(('concurrent', 1, 1), 'totalSeconds')
    parallel_one = sample_median(('parallel', args.io_workers, 1), 'totalSeconds')
    rows = []
    for (mode, io_workers, cpu_workers), samples in observations.items():
        workers = io_workers if mode == 'concurrent' else cpu_workers if mode == 'parallel' else 1
        reference = concurrent_one if mode == 'concurrent' else parallel_one if mode == 'parallel' else None
        total = [row['totalSeconds'] for row in samples]
        download = [row['downloadStageSeconds'] for row in samples]
        match = [row['matchStageSeconds'] for row in samples]
        download_median = statistics.median(download)
        match_median = statistics.median(match)
        rows.append({'mode': mode, 'ioWorkers': io_workers, 'cpuWorkers': cpu_workers,
                     'repetitions': len(samples), 'outputSha256': signature,
                     'downloadMedianSeconds': download_median, 'downloadMinSeconds': min(download),
                     'downloadMaxSeconds': max(download),
                     'downloadAbsoluteSpeedup': baseline_download / download_median if download_median else None,
                     'matchMedianSeconds': match_median, 'matchMinSeconds': min(match),
                     'matchMaxSeconds': max(match),
                     'matchAbsoluteSpeedup': baseline_match / match_median if match_median else None,
                     **metrics(total, baseline, reference, workers)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {len(rows)} configurations to {args.output}')


if __name__ == '__main__':
    main()
