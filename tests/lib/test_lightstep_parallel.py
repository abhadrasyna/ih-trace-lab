"""Offline tests for scripts/lib/lightstep_parallel.py."""

from __future__ import annotations

import threading
import time

import pytest

from scripts.lib.lightstep_parallel import SerialJobRunner, ThreadJobRunner


def test_results_in_input_order_even_when_jobs_finish_out_of_order() -> None:
    jobs = [lambda i=i: (time.sleep(0.05 * (4 - i)), i)[1] for i in range(5)]
    seen: list[int] = []
    assert ThreadJobRunner(4).run(jobs, lambda index, value: seen.append(value)) == [0, 1, 2, 3, 4]
    assert sorted(seen) == [0, 1, 2, 3, 4]


def test_on_result_runs_on_calling_thread_and_concurrency_is_bounded() -> None:
    active = peak = 0
    lock = threading.Lock()

    def job() -> int:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return 1

    threads: set[int] = set()
    ThreadJobRunner(2).run([job] * 8, lambda i, v: threads.add(threading.get_ident()))
    assert peak <= 2 and threads == {threading.get_ident()}


def test_first_failure_stops_new_submissions_and_is_raised() -> None:
    started: list[int] = []

    def make(i: int):
        def job() -> int:
            started.append(i)
            if i == 1:
                raise RuntimeError("boom")
            time.sleep(0.05)
            return i
        return job

    with pytest.raises(RuntimeError, match="boom"):
        ThreadJobRunner(2).run([make(i) for i in range(20)])
    assert len(started) < 20


def test_serial_runner_and_one_worker_start_no_threads() -> None:
    idents: list[int] = []
    jobs = [lambda: idents.append(threading.get_ident()) or 1] * 3
    assert SerialJobRunner().run(jobs) == [1, 1, 1] and ThreadJobRunner(1).run(jobs) == [1, 1, 1]
    assert set(idents) == {threading.get_ident()}


def test_worker_bounds_rejected() -> None:
    for bad in (0, 9):
        with pytest.raises(ValueError):
            ThreadJobRunner(bad)
