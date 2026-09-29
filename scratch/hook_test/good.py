"""Scratch file to test the py-code-review hook passes clean code."""

from __future__ import annotations


def add_item(item: int, bucket: list[int] | None = None) -> list[int]:
    """Append item to a fresh list per call and return it."""
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
