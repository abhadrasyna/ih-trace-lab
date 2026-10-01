"""Tests for scripts/dev/harvest_lightstep_query_catalog.py."""
from __future__ import annotations

from pathlib import Path

from scripts.dev.harvest_lightstep_query_catalog import extract_templates, slugify


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_extract_templates_captures_purpose_tool_and_save_path(tmp_path: Path) -> None:
    markdown = _write(
        tmp_path / "lightstep-query-templates.md",
        """# Lightstep templates

## Session Inventory by Device

**Purpose:** Compare session counts for a single device.
Tool: `query_timeseries`
**Save exports as:** `exports/<DEVICE_ID>-inventory.csv`

```
metric requests
| filter service == "sm-vod" && device_id == "<DEVICE_ID>"
```
""",
    )

    templates = extract_templates(markdown)

    assert len(templates) == 1
    template = templates[0]
    assert template.title == "Session Inventory by Device"
    assert template.purpose == "Compare session counts for a single device."
    assert template.tool == "query_timeseries"
    assert template.save_exports_as == "exports/{{device_id}}-inventory.csv"
    assert '{{device_id}}' in template.tql


def test_extract_templates_skips_section_with_no_code_block(tmp_path: Path) -> None:
    markdown = _write(
        tmp_path / "lightstep-query-templates.md",
        """# Lightstep templates

## Notes only

**Purpose:** This section has no query block.

## Session Inventory by Device

**Purpose:** Compare session counts for a single device.
Tool: `query_timeseries`

```
metric requests
| filter service == "sm-vod"
```
""",
    )

    templates = extract_templates(markdown)

    assert [template.title for template in templates] == ["Session Inventory by Device"]


def test_slugify_produces_kebab_case() -> None:
    assert slugify("sm-vod Session Inventory by Device") == "smvod-session-inventory-by-device"


def test_slugify_handles_punctuation_and_repeated_dashes() -> None:
    assert slugify("HTTP 5xx × retries (daily) --  Device!!!") == "http-5xx-retries-daily-device"
