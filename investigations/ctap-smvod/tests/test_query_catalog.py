"""Tests for CTAP/SM-VOD query-catalog integration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_SPEC = importlib.util.spec_from_file_location("ctap_smvod_query_catalog", _SCRIPTS_DIR / "lib" / "query_catalog.py")
assert _SPEC and _SPEC.loader
query_catalog = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = query_catalog
_SPEC.loader.exec_module(query_catalog)


def test_query_lookup_returns_catalog_entry() -> None:
    rendered = query_catalog.render_query(
        "ctap-smvod-playback-outcome",
        {"database": "unified_e6auj7k7", "date": "2026-09-30"},
    )

    assert 'FROM "unified_e6auj7k7"."unified_sessions"' in rendered
    assert "WHERE timestamp_formatted = '2026-09-30'" in rendered


def test_debug_completeness_query_uses_catalog_template() -> None:
    rendered = query_catalog.render_query(
        "ctap-smvod-debug-completeness",
        {
            "database": "unified_e6auj7k7",
            "datetime_start": "2026-09-30T00:00:00.000Z",
            "datetime_end": "2026-10-01T00:00:00.000Z",
            "eventclass": "PLAYER",
            "session_ids_block": "          'session-1'",
        },
    )

    assert 'FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"' in rendered
    assert "AND datetime >= '2026-09-30T00:00:00.000Z'" in rendered
    assert "'session-1'" in rendered


def test_no_inline_sql_remains() -> None:
    script_dir = Path(__file__).resolve().parents[1] / "scripts"
    inline_sql_markers = ("QUERY_TEMPLATE = \"\"\"", "SELECT DISTINCT\n", "WITH session_states AS (")
    offenders: list[str] = []

    for path in sorted(script_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in inline_sql_markers):
            offenders.append(path.name)

    assert offenders == []
