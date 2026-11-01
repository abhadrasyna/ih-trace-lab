"""Bounded worker pool for independent jobs, returning results in input order.

Jobs run inside a copy of the caller's ``contextvars`` context so the FCID survives the thread boundary.
``on_result`` is called from the collecting (calling) thread only, so callers need no locks.
"""

from __future__ import annotations

import contextvars
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Protocol, TypeVar

T = TypeVar("T")
DEFAULT_WORKERS = 4
MAX_WORKERS = 8
OnResult = Callable[[int, T], None]


class JobRunner(Protocol):
    def run(self, jobs: Sequence[Callable[[], T]], on_result: OnResult | None = None) -> list[T]: ...


def validate_workers(workers: int) -> int:
    if not 1 <= workers <= MAX_WORKERS:
        raise ValueError(f"workers must be between 1 and {MAX_WORKERS}, got {workers}")
    return workers


class SerialJobRunner:
    """Runs jobs one after another on the calling thread; stops at the first failure."""

    def run(self, jobs: Sequence[Callable[[], T]], on_result: OnResult | None = None) -> list[T]:
        results: list[T] = []
        for index, job in enumerate(jobs):
            result = job()
            results.append(result)
            if on_result:
                on_result(index, result)
        return results


class ThreadJobRunner:
    """Runs up to ``workers`` jobs at once. After the first failure nothing new is submitted, in-flight jobs finish, then it is re-raised."""

    def __init__(self, workers: int = DEFAULT_WORKERS) -> None:
        self.workers = validate_workers(workers)

    def run(self, jobs: Sequence[Callable[[], T]], on_result: OnResult | None = None) -> list[T]:
        if self.workers == 1:
            return SerialJobRunner().run(jobs, on_result)
        results: list[T | None] = [None] * len(jobs)
        pending: dict[Future[T], int] = {}
        first_error: BaseException | None = None
        next_index = 0
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            while pending or (first_error is None and next_index < len(jobs)):
                while first_error is None and next_index < len(jobs) and len(pending) < self.workers:
                    pending[pool.submit(contextvars.copy_context().run, jobs[next_index])] = next_index
                    next_index += 1
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    index = pending.pop(future)
                    try:
                        results[index] = future.result()
                    except BaseException as exc:  # noqa: BLE001 - re-raised after in-flight jobs finish
                        first_error = first_error or exc
                        continue
                    if on_result:
                        on_result(index, results[index])  # type: ignore[arg-type]
        if first_error is not None:
            raise first_error
        return results  # type: ignore[return-value]
