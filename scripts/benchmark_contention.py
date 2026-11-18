#!/usr/bin/env python3
"""Measure three thread-safe ways to count real catalog offers by platform."""
import argparse
import json
import queue
import sqlite3
import statistics
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[1] / 'data/nexo.sqlite'
STRATEGIES = ('global_lock', 'thread_local', 'concurrent_queue')


def offer_platforms(database=DATABASE):
    with sqlite3.connect(database) as connection:
        platforms = {}
        for appid, payload_json in connection.execute('SELECT steam_app_id, payload_json FROM games WHERE active = 1'):
            payload = json.loads(payload_json)
            names = payload.get('platforms') or [payload.get('platform') or 'Sin plataforma']
            platforms[appid] = tuple([names] if isinstance(names, str) else names)
        return [platform for (appid,) in connection.execute('SELECT steam_app_id FROM retailer_offers')
                for platform in platforms.get(appid, ())]


def aggregate(items, workers, strategy):
    if workers < 1 or strategy not in STRATEGIES:
        raise ValueError('Invalid workers or strategy')
    chunks = [items[index::workers] for index in range(workers)]
    result = Counter()
    lock = threading.Lock()
    collected = queue.SimpleQueue()

    def run(chunk):
        if strategy == 'global_lock':
            for item in chunk:
                with lock:
                    result[item] += 1
        elif strategy == 'thread_local':
            return Counter(chunk)
        else:
            for item in chunk:
                collected.put(item)
        return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        partials = list(pool.map(run, chunks))
    if strategy == 'thread_local':
        for partial in partials:
            result.update(partial)
    elif strategy == 'concurrent_queue':
        while not collected.empty():
            result[collected.get_nowait()] += 1
    return result


def demonstrate_race(workers=4, steps=50):
    """Force each thread to read the same value before writing without a lock."""
    if workers < 2 or steps < 1:
        raise ValueError('Race demonstration needs at least two threads and one step')
    shared = {'offers': 0}
    read_barrier = threading.Barrier(workers)
    write_barrier = threading.Barrier(workers)

    def increment():
        for _ in range(steps):
            value = shared['offers']
            read_barrier.wait()
            shared['offers'] = value + 1
            write_barrier.wait()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda _: increment(), range(workers)))
    return {'expected': workers * steps, 'observed': shared['offers'],
            'lostUpdates': workers * steps - shared['offers']}


def benchmark(items, workers=4, repetitions=5):
    if repetitions < 1 or not items:
        raise ValueError('Need data and at least one repetition')
    expected = Counter(items)
    output = {}
    for strategy in STRATEGIES:
        seconds = []
        for _ in range(repetitions):
            began = time.perf_counter()
            actual = aggregate(items, workers, strategy)
            seconds.append(time.perf_counter() - began)
            if actual != expected:
                raise AssertionError(f'{strategy} lost offers')
        output[strategy] = {'medianSeconds': statistics.median(seconds),
                            'minSeconds': min(seconds), 'maxSeconds': max(seconds),
                            'repetitions': repetitions, 'count': sum(expected.values())}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--repeat-input', type=int, default=20)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 1 <= args.workers <= 64 or not 1 <= args.repeat_input <= 1000:
        parser.error('Workers and input repetition out of range')
    source = offer_platforms()
    if not source:
        parser.error('No real retailer offers in SQLite')
    result = {'workers': args.workers, 'sourceOffers': len(source),
              'inputRepetition': args.repeat_input,
              'strategies': benchmark(source * args.repeat_input, args.workers, args.repetitions),
              'race': demonstrate_race(max(2, args.workers))}
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
    print(payload, end='')


if __name__ == '__main__':
    main()
