"""Offline checks for consistent collection modes and the shared request budget."""

import os
import time
import unittest

from collection_engine import rate_gate, run_jobs

_gate = None


def init_gate(gate):
    global _gate
    _gate = gate


def timed_job(number):
    _gate.wait()
    return number, time.monotonic(), os.getpid()


def failing_job(number):
    if number == 2:
        raise ValueError("Incomplete source batch")
    return number


class CollectionEngineTests(unittest.TestCase):
    def test_modes_keep_order_and_one_shared_rate_limit(self):
        for mode in ("sequential", "threads", "processes"):
            with self.subTest(mode=mode), rate_gate(mode, .04) as gate:
                result = run_jobs(range(5), timed_job, mode=mode, workers=3,
                                  initializer=init_gate, initargs=(gate,))
                self.assertEqual([item[0] for item in result], list(range(5)))
                timestamps = sorted(item[1] for item in result)
                self.assertTrue(all(b - a >= .025 for a, b in zip(timestamps, timestamps[1:])))
                if mode == "processes":
                    self.assertTrue(any(item[2] != os.getpid() for item in result))

    def test_failed_batch_is_reported_in_every_mode(self):
        for mode in ("sequential", "threads", "processes"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "Incomplete source batch"):
                    run_jobs(range(4), failing_job, mode=mode, workers=2)


if __name__ == "__main__":
    unittest.main()
