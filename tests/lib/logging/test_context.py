"""Tests for `src.lib.logging.context`'s FCID propagation primitives."""
from __future__ import annotations

import contextvars
import logging
from concurrent.futures import ThreadPoolExecutor

from src.lib.logging.context import FcidLogFilter, bind_fcid, current_fcid


def test_current_fcid_defaults_to_none() -> None:
    def _in_fresh_context() -> str | None:
        return current_fcid()

    assert contextvars.copy_context().run(_in_fresh_context) is None


def test_bind_fcid_then_current_fcid_round_trips() -> None:
    def _in_fresh_context() -> None:
        bind_fcid("abc-123")
        assert current_fcid() == "abc-123"

    contextvars.copy_context().run(_in_fresh_context)


def test_bind_fcid_does_not_leak_across_independent_contexts() -> None:
    def _bind_and_read(value: str) -> str | None:
        bind_fcid(value)
        return current_fcid()

    ctx_a = contextvars.copy_context()
    ctx_b = contextvars.copy_context()
    assert ctx_a.run(_bind_and_read, "fcid-a") == "fcid-a"
    assert ctx_b.run(_bind_and_read, "fcid-b") == "fcid-b"
    # neither context's bind leaked into a brand-new, never-bound context
    assert contextvars.copy_context().run(current_fcid) is None


def test_fcid_propagates_across_thread_pool_via_copy_context() -> None:
    def _worker() -> str | None:
        return current_fcid()

    def _bind_and_submit(pool: ThreadPoolExecutor) -> str | None:
        bind_fcid("pool-fcid")
        snapshot = contextvars.copy_context()
        future = pool.submit(snapshot.run, _worker)
        return future.result()

    with ThreadPoolExecutor(max_workers=1) as pool:
        result = contextvars.copy_context().run(_bind_and_submit, pool)

    assert result == "pool-fcid"


def test_fcid_log_filter_injects_bound_value() -> None:
    filter_ = FcidLogFilter()
    logger = logging.getLogger("test.fcid.filter.bound")
    logger.addFilter(filter_)
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[assignment]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:

        def _emit() -> None:
            bind_fcid("logged-fcid")
            logger.info("hello")

        contextvars.copy_context().run(_emit)
    finally:
        logger.removeHandler(handler)
        logger.removeFilter(filter_)

    assert len(records) == 1
    assert records[0].fcid == "logged-fcid"  # type: ignore[attr-defined]


def test_fcid_log_filter_defaults_to_no_fcid_sentinel() -> None:
    filter_ = FcidLogFilter()
    logger = logging.getLogger("test.fcid.filter.unbound")
    logger.addFilter(filter_)
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[assignment]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        contextvars.copy_context().run(logger.info, "hello")
    finally:
        logger.removeHandler(handler)
        logger.removeFilter(filter_)

    assert len(records) == 1
    assert records[0].fcid == "no-fcid"  # type: ignore[attr-defined]
