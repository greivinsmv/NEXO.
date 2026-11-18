"""Execute collection jobs consistently in sequential, threaded or process mode.

The rate gate is shared by every worker, including workers in separate processes.
It controls the start of each HTTP attempt, including retries.
"""

import multiprocessing
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace

MODES = ("sequential", "threads", "processes")


@dataclass
class RateGate:
    lock: object
    next_allowed: object
    interval: float

    def wait(self):
        with self.lock:
            delay = self.next_allowed.value - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.next_allowed.value = time.monotonic() + self.interval

    def defer(self, seconds):
        with self.lock:
            self.next_allowed.value = max(self.next_allowed.value, time.monotonic() + seconds)


@contextmanager
def rate_gate(mode, interval):
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    if interval < 0:
        raise ValueError("Request interval cannot be negative")
    if mode == "processes":
        context = multiprocessing.get_context("spawn")
        yield RateGate(context.Lock(), context.Value("d", 0.0), interval)
    else:
        yield RateGate(threading.Lock(), SimpleNamespace(value=0.0), interval)


def run_jobs(jobs, worker, *, mode="sequential", workers=4, initializer=None, initargs=()):
    """Return results in input order; propagate any failure before the caller writes data."""
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    if not 1 <= workers <= 8:
        raise ValueError("Worker count must be between 1 and 8")
    if mode == "sequential":
        if initializer:
            initializer(*initargs)
        return [worker(job) for job in jobs]
    executor = ThreadPoolExecutor if mode == "threads" else ProcessPoolExecutor
    options = {"mp_context": multiprocessing.get_context("spawn")} if mode == "processes" else {}
    with executor(max_workers=workers, initializer=initializer, initargs=initargs, **options) as pool:
        return list(pool.map(worker, jobs))
