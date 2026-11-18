"""Bounded download → parse → title-match pipeline with three course modes."""
import hashlib
import json
import multiprocessing
import queue
import random
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from collection_engine import RateGate
from title_matching import match_game_candidates

MODES = ('sequential', 'concurrent', 'parallel')


class ReplayTransport:
    def __init__(self, root, latency=0.0, jitter=0.0, seed=0):
        self.root = Path(root).resolve()
        self.latency, self.jitter, self.seed = latency, jitter, seed
        if latency < 0 or jitter < 0:
            raise ValueError('Replay latency must be nonnegative')

    def fetch(self, job):
        filename = (self.root / job['fixture']).resolve()
        if not filename.is_relative_to(self.root):
            raise ValueError('Fixture path escapes replay directory')
        digest = hashlib.sha256(f"{self.seed}:{job['fixture']}".encode()).digest()
        delay = self.latency + self.jitter * (int.from_bytes(digest[:8], 'big') / (2**64 - 1))
        if delay:
            time.sleep(delay)
        return filename.read_bytes()


class LiveTransport:
    def __init__(self, capture_dir=None, *, per_domain=2, interval=2.5, timeout=25, attempts=3):
        if not 1 <= per_domain <= 8 or interval < 0 or timeout <= 0 or not 1 <= attempts <= 5:
            raise ValueError('Invalid live transport limits')
        self.capture_dir = Path(capture_dir).resolve() if capture_dir else None
        self.per_domain, self.interval, self.timeout, self.attempts = per_domain, interval, timeout, attempts
        self._domains = {}
        self._lock = threading.Lock()

    def fetch(self, job):
        url = job['url']
        domain = urlparse(url)
        if domain.scheme != 'https' or not domain.hostname:
            raise ValueError('Live sources must use HTTPS')
        with self._lock:
            if domain.hostname not in self._domains:
                self._domains[domain.hostname] = (
                    threading.Semaphore(self.per_domain),
                    RateGate(threading.Lock(), SimpleNamespace(value=0.0), self.interval),
                )
            semaphore, gate = self._domains[domain.hostname]
        for attempt in range(self.attempts):
            try:
                with semaphore:
                    gate.wait()
                    request = Request(url, headers={'User-Agent': 'NEXO academic catalog/0.3 (github.com/greivinsmv/NEXO)'})
                    with urlopen(request, timeout=self.timeout) as response:
                        raw = response.read()
                if self.capture_dir:
                    target = (self.capture_dir / job['fixture']).resolve()
                    if not target.is_relative_to(self.capture_dir):
                        raise ValueError('Fixture path escapes capture directory')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_name(target.name + f'.{threading.get_ident()}.tmp')
                    temporary.write_bytes(raw)
                    temporary.replace(target)
                return raw
            except HTTPError as error:
                if attempt + 1 == self.attempts or error.code not in (429, 500, 502, 503, 504):
                    raise
                if error.code == 429:
                    try:
                        gate.defer(min(60, max(1, int(error.headers.get('Retry-After') or 30))))
                    except ValueError:
                        gate.defer(30)
            except (OSError, TimeoutError):
                if attempt + 1 == self.attempts:
                    raise
            time.sleep(min(30, 2**attempt) + random.uniform(0, .25))


def parse_json_candidates(job, raw):
    """Read recorded source bytes or the small normalized test format."""
    payload = json.loads(raw)
    if job['source'] == 'Steam Store':
        appid = str(job['game']['steamAppId'])
        entry = payload.get(appid) if isinstance(payload, dict) else None
        data = entry.get('data') if isinstance(entry, dict) and entry.get('success') else None
        if not isinstance(data, dict) or not isinstance(data.get('name'), str):
            raise ValueError(f'Steam Store response has no game {appid}')
        price = data.get('price_overview') or {}
        return [{'title': data['name'], 'steamAppID': appid,
                 'price': price.get('final'), 'source': 'Steam Store'}]
    if job['source'] == 'CheapShark' and not isinstance(payload, list):
        raise ValueError('CheapShark response is not a deal list')
    candidates = payload.get('candidates') if isinstance(payload, dict) else payload
    if not isinstance(candidates, list):
        raise ValueError(f"{job['source']} response has no candidate list")
    return [item for item in candidates if isinstance(item, dict) and isinstance(item.get('title'), str)]


def run_pipeline(jobs, fetch_raw, parse_candidates=parse_json_candidates, *, mode='sequential',
                 io_workers=4, cpu_workers=2, queue_size=32, threshold=.82):
    """Use identical jobs and parsing in each mode; only stage concurrency changes."""
    if mode not in MODES or not 1 <= io_workers <= 64 or not 1 <= cpu_workers <= 64 or queue_size < 1:
        raise ValueError('Invalid pipeline configuration')
    jobs = list(jobs)
    keys = [(job['game']['steamAppId'], job['source']) for job in jobs]
    if len(set(keys)) != len(keys):
        raise ValueError('One job per game and source is required')
    started = time.perf_counter()
    results, failures = [], []
    download_seconds = 0.0
    match_seconds = 0.0
    download_bounds = []
    match_bounds = []

    def fetch_parse(job):
        began = time.perf_counter()
        try:
            candidates = parse_candidates(job, fetch_raw(job))
            finished = time.perf_counter()
            return job, candidates, finished - began, None, began, finished
        except Exception as error:
            finished = time.perf_counter()
            return job, [], finished - began, f'{type(error).__name__}: {error}', began, finished

    def finish(job, future_or_result):
        nonlocal match_seconds
        try:
            result = future_or_result.result() if hasattr(future_or_result, 'result') else future_or_result
            match_seconds += result.pop('matchSeconds')
            match_bounds.append((result.pop('matchStarted'), result.pop('matchFinished')))
            results.append({'source': job['source'], **result})
        except Exception as error:
            failures.append({'gameId': job['game']['steamAppId'], 'source': job['source'],
                             'error': f'{type(error).__name__}: {error}'})

    if mode == 'sequential':
        for job in jobs:
            item, candidates, elapsed, error, began, finished = fetch_parse(job)
            download_seconds += elapsed
            download_bounds.append((began, finished))
            if error:
                failures.append({'gameId': item['game']['steamAppId'], 'source': item['source'], 'error': error})
            else:
                finish(item, match_game_candidates(item['game'], candidates, threshold))
    else:
        incoming, ready = queue.Queue(maxsize=queue_size), queue.Queue(maxsize=queue_size)
        sentinel = object()

        def downloader():
            while True:
                job = incoming.get()
                if job is sentinel:
                    incoming.task_done()
                    return
                ready.put(fetch_parse(job))
                incoming.task_done()

        threads = [threading.Thread(target=downloader, daemon=True) for _ in range(io_workers)]
        for thread in threads:
            thread.start()

        def produce():
            for job in jobs:
                incoming.put(job)
            for _ in threads:
                incoming.put(sentinel)

        producer = threading.Thread(target=produce, daemon=True)
        producer.start()
        pending = []
        executor = ProcessPoolExecutor(max_workers=cpu_workers,
                                       mp_context=multiprocessing.get_context('spawn')) if mode == 'parallel' else None
        try:
            for _ in jobs:
                job, candidates, elapsed, error, began, finished = ready.get()
                download_seconds += elapsed
                download_bounds.append((began, finished))
                if error:
                    failures.append({'gameId': job['game']['steamAppId'], 'source': job['source'], 'error': error})
                    continue
                if executor:
                    pending.append((job, executor.submit(match_game_candidates, job['game'], candidates, threshold)))
                    if len(pending) >= cpu_workers * 2:
                        finish(*pending.pop(0))
                else:
                    finish(job, match_game_candidates(job['game'], candidates, threshold))
            for item in pending:
                finish(*item)
        finally:
            if executor:
                executor.shutdown(wait=True)
            producer.join()
            for thread in threads:
                thread.join()

    # Failed source jobs get one final attempt after the initial wave. A game can
    # still be published with its other sources if this final attempt fails.
    first_failures = failures
    failures = []
    job_by_key = {(job['game']['steamAppId'], job['source']): job for job in jobs}
    for failure in first_failures:
        job = job_by_key[(failure['gameId'], failure['source'])]
        _, candidates, elapsed, error, began, finished = fetch_parse(job)
        download_seconds += elapsed
        download_bounds.append((began, finished))
        if error:
            failures.append({'gameId': failure['gameId'], 'source': failure['source'], 'error': error})
        else:
            finish(job, match_game_candidates(job['game'], candidates, threshold))
    results.sort(key=lambda row: (row['gameId'], row['source']))
    metrics = {
        'mode': mode, 'jobs': len(jobs), 'successful': len(results), 'retried': len(first_failures),
        'failed': len(failures), 'doubtful': sum(item['doubtful'] for item in results),
        'downloadWorkerSeconds': round(download_seconds, 6), 'matchWorkerSeconds': round(match_seconds, 6),
        'downloadStageSeconds': round(max(end for _, end in download_bounds) - min(begin for begin, _ in download_bounds), 6) if download_bounds else 0,
        'matchStageSeconds': round(max(end for _, end in match_bounds) - min(begin for begin, _ in match_bounds), 6) if match_bounds else 0,
        'totalSeconds': round(time.perf_counter() - started, 6), 'failures': failures,
    }
    return {'results': results, 'metrics': metrics}
