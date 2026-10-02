"""Tests for `src.lib.har.loader`."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.lib.har.exceptions import HarFormatError
from src.lib.har.loader import JsonHarEntryLoader

_FIXTURES = Path(__file__).parent / "fixtures"


def test_load_entries_returns_list() -> None:
    entries = JsonHarEntryLoader().load_entries(_FIXTURES / "valid.har")

    assert len(entries) == 2
    assert entries[0].url == "https://example.test/manifest.mpd"
    assert entries[0].method == "GET"
    assert entries[0].status == 200
    assert entries[0].started_datetime == "2026-09-30T00:00:00.000Z"
    assert entries[1].status == 206


def test_load_entries_accepts_str_path() -> None:
    entries = JsonHarEntryLoader().load_entries(str(_FIXTURES / "valid.har"))

    assert len(entries) == 2


def test_load_entries_accepts_open_file_handle() -> None:
    with open(_FIXTURES / "valid.har", encoding="utf-8") as handle:
        entries = JsonHarEntryLoader().load_entries(handle)

    assert len(entries) == 2


def test_load_entries_accepts_binary_file_handle() -> None:
    with open(_FIXTURES / "valid.har", "rb") as handle:
        entries = JsonHarEntryLoader().load_entries(handle)

    assert len(entries) == 2


def test_load_entries_accepts_utf8_bom(tmp_path: Path) -> None:
    har_file = tmp_path / "bom.har"
    har_file.write_bytes(b"\xef\xbb\xbf" + (_FIXTURES / "valid.har").read_bytes())

    entries = JsonHarEntryLoader().load_entries(har_file)

    assert len(entries) == 2


def test_load_entries_accepts_utf8_bom_via_text_handle(tmp_path: Path) -> None:
    har_file = tmp_path / "bom_text.har"
    har_file.write_bytes(b"\xef\xbb\xbf" + (_FIXTURES / "valid.har").read_bytes())

    with open(har_file, encoding="utf-8") as handle:
        entries = JsonHarEntryLoader().load_entries(handle)

    assert len(entries) == 2


def test_load_entries_raises_on_invalid_utf8(tmp_path: Path) -> None:
    har_file = tmp_path / "bad_utf8.har"
    har_file.write_bytes(b"\xff\xfe\x00invalid")

    with pytest.raises(HarFormatError, match="UTF-8"):
        JsonHarEntryLoader().load_entries(har_file)


def test_load_entries_raises_on_missing_entries_key() -> None:
    with pytest.raises(HarFormatError, match="entries"):
        JsonHarEntryLoader().load_entries(_FIXTURES / "missing_entries.har")


def test_load_entries_raises_on_invalid_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.har"
    bad_file.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(HarFormatError, match="JSON"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_non_dict_log(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_log.har"
    bad_file.write_text('{"log": "not-a-dict"}', encoding="utf-8")

    with pytest.raises(HarFormatError, match="log"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_non_list_entries(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_entries.har"
    bad_file.write_text('{"log": {"entries": "not-a-list"}}', encoding="utf-8")

    with pytest.raises(HarFormatError, match="entries"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_non_dict_entry(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_entry.har"
    bad_file.write_text('{"log": {"entries": ["not-a-dict"]}}', encoding="utf-8")

    with pytest.raises(HarFormatError, match="index 0"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_missing_request_or_response(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_entry2.har"
    bad_file.write_text('{"log": {"entries": [{"startedDateTime": "x"}]}}', encoding="utf-8")

    with pytest.raises(HarFormatError, match="request"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_missing_url(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_url.har"
    bad_file.write_text(
        '{"log": {"entries": [{"request": {"method": "GET"}, "response": {"status": 200}}]}}',
        encoding="utf-8",
    )

    with pytest.raises(HarFormatError, match="url"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_non_string_method(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_method.har"
    bad_file.write_text(
        '{"log": {"entries": [{"request": {"url": "https://x", "method": null}, "response": {"status": 200}}]}}',
        encoding="utf-8",
    )

    with pytest.raises(HarFormatError, match="method"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_non_integer_status(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_status.har"
    bad_file.write_text(
        '{"log": {"entries": [{"request": {"url": "https://x", "method": "GET"}, "response": {"status": "abc"}}]}}',
        encoding="utf-8",
    )

    with pytest.raises(HarFormatError, match="status"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_null_status(tmp_path: Path) -> None:
    bad_file = tmp_path / "null_status.har"
    bad_file.write_text(
        '{"log": {"entries": [{"request": {"url": "https://x", "method": "GET"}, "response": {"status": null}}]}}',
        encoding="utf-8",
    )

    with pytest.raises(HarFormatError, match="status"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_boolean_status(tmp_path: Path) -> None:
    bad_file = tmp_path / "bool_status.har"
    bad_file.write_text(
        '{"log": {"entries": [{"request": {"url": "https://x", "method": "GET"}, "response": {"status": true}}]}}',
        encoding="utf-8",
    )

    with pytest.raises(HarFormatError, match="status"):
        JsonHarEntryLoader().load_entries(bad_file)


def test_load_entries_raises_on_non_string_started_datetime(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_started_datetime.har"
    bad_file.write_text(
        '{"log": {"entries": [{"startedDateTime": 12345, "request": {"url": "https://x", "method": "GET"},'
        ' "response": {"status": 200}}]}}',
        encoding="utf-8",
    )

    with pytest.raises(HarFormatError, match="startedDateTime"):
        JsonHarEntryLoader().load_entries(bad_file)
