"""Tests for scripts/dev/harvest_athena_query_catalog.py."""
from __future__ import annotations

from pathlib import Path

from scripts.dev.harvest_athena_query_catalog import (
    build_catalog,
    detect_status,
    extract_sql_blocks,
    normalize_to_shape,
    templatize,
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_extract_sql_blocks_pairs_heading_and_why_found(tmp_path: Path) -> None:
    markdown = _write(
        tmp_path / "catalog.md",
        """# Query catalog

## Playback lookup

```sql
SELECT *
FROM analytics.session_events
WHERE device_id = 'abc123'
```

**Why:** Confirm whether playback exists for the device.
**Found:** One matching session row.
""",
    )

    blocks = extract_sql_blocks(markdown)

    assert len(blocks) == 1
    assert blocks[0].heading == "Playback lookup"
    assert blocks[0].why == "Confirm whether playback exists for the device."
    assert blocks[0].found == "One matching session row."


def test_extract_sql_blocks_skips_file_with_no_sql_blocks(tmp_path: Path) -> None:
    markdown = _write(
        tmp_path / "notes.md",
        """# Notes

## Playback lookup

No SQL captured here.
""",
    )

    assert extract_sql_blocks(markdown) == []


def test_normalize_to_shape_collapses_same_table_and_columns_different_literals() -> None:
    first = """
SELECT *
FROM analytics.session_events
WHERE device_id = 'abc123'
  AND event_date = DATE '2026-09-01'
GROUP BY device_id
"""
    second = """
SELECT *
FROM analytics.session_events
WHERE device_id = 'xyz987'
  AND event_date = DATE '2026-09-02'
GROUP BY device_id
"""

    assert normalize_to_shape(first) == normalize_to_shape(second)


def test_detect_status_flags_not_yet_run_prose() -> None:
    file_text = """# Investigation

## Status

Drafted but not yet run against Athena.
"""

    assert detect_status(file_text) == "drafted-not-yet-run"


def test_detect_status_defaults_to_confirmed_run() -> None:
    file_text = """# Investigation

## Query

```sql
SELECT 1
```
"""

    assert detect_status(file_text) == "confirmed-run"


def test_templatize_replaces_literals_not_structure() -> None:
    sql = """
SELECT *
FROM analytics.session_events
WHERE device_id = 'abc123'
  AND event_date >= DATE '2026-09-01'
ORDER BY created_at DESC
"""

    templated = templatize(sql)

    assert "SELECT *" in templated
    assert "FROM analytics.session_events" in templated
    assert "ORDER BY created_at DESC" in templated
    assert "device_id = {{device_id}}" in templated
    assert "{{event_date_start}}" in templated
    assert "'abc123'" not in templated
    assert "DATE '2026-09-01'" not in templated


def test_build_catalog_deduplicates_across_two_source_files(tmp_path: Path) -> None:
    first = _write(
        tmp_path / "source_one.md",
        """# Query catalog

## Playback lookup

```sql
SELECT *
FROM analytics.session_events
WHERE device_id = 'abc123'
  AND event_date = DATE '2026-09-01'
```

**Why:** Investigate a playback session for one device.
""",
    )
    second = _write(
        tmp_path / "source_two.md",
        """# Query catalog

## Playback lookup rerun

```sql
SELECT *
FROM analytics.session_events
WHERE device_id = 'xyz987'
  AND event_date = DATE '2026-09-02'
```

**Why:** Investigate a playback session for another device.
""",
    )

    catalog = build_catalog([first, second])

    assert len(catalog) == 1
    entry = catalog[0]
    assert entry.raw_query_count == 2
    assert entry.tables == ["analytics.session_events"]
    assert {origin.source_path for origin in entry.origins} == {first, second}
    assert {origin.heading for origin in entry.origins} == {"Playback lookup", "Playback lookup rerun"}


def test_build_catalog_handles_one_malformed_source_file(tmp_path: Path) -> None:
    valid = _write(
        tmp_path / "valid.md",
        """# Query catalog

## Playback lookup

```sql
SELECT *
FROM analytics.session_events
WHERE device_id = 'abc123'
```
""",
    )
    malformed = _write(
        tmp_path / "malformed.md",
        """# Query catalog

## Playback lookup

This file forgot the fenced SQL block.
""",
    )

    catalog = build_catalog([valid, malformed])

    assert len(catalog) == 1
    assert catalog[0].raw_query_count == 1
    assert [origin.source_path for origin in catalog[0].origins] == [valid]
