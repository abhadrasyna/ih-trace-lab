"""Offline tests for build_enriched_events (synthetic rows, tmp_path only)."""
from __future__ import annotations

import csv
import json
from datetime import timezone

from scripts.build_enriched_events import FIELDNAMES, enrich_rows, parse_utc, write_enriched
from scripts.lib.analysis_config import parse_config

CONFIG = parse_config({
    "tenant": "ZA", "default_start_date": "2026-11-01",
    "app_version": {"before": "v-old", "after": "v-new"},
    "upgrade_window": {"timezone": "Asia/Kolkata", "start": "2026-11-04T16:30:00+05:30",
                       "end": "2026-11-04T17:00:00+05:30"},
})
GOOD_UA = ("Mozilla/5.0 (Linux; Android 13; P11 Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Version/4.0 Chrome/156.0.8078.47 Mobile Safari/537.36")


def _row(message_id, *, ts="2026-11-05T00:00:00.000Z", ua=GOOD_UA, version="v-new"):
    desc = {"errordescription": "E86001", "shakaerror": {"code": 6001}, "app_version": version}
    if ua is not None:
        desc["user_agent"] = ua
    data = {"sessionid": "s-" + message_id, "errordescription": desc}
    return {"datetime": ts, "messageid": message_id, "clibversion": "JS.1", "clientid": "dev:hh",
            "eventclass": "PLAYER", "eventid": "PLAYER_ERROR", "eventdata": json.dumps(data)}


def test_duplicates_removed_once():
    result = enrich_rows([_row("a"), _row("a"), _row("a"), _row("b")], CONFIG)
    assert [r["messageid"] for r in result.rows] == ["a", "b"]
    assert result.duplicates_removed == 2


def test_unparsed_ua_kept_and_counted():
    result = enrich_rows([_row("a"), _row("b", ua=None), _row("c", ua="curl/8")], CONFIG)
    assert len(result.rows) == 3
    assert result.unparsed_ua == 2
    assert result.rows[0]["device_model"] == "P11" and result.rows[0]["is_webview"] is True


def test_unknown_and_conflict_periods_kept_and_counted():
    rows = [_row("a", version="v-old"),  # after by timestamp, before by version -> conflict
            _row("b", version="v-other", ts="2026-11-04T11:15:00.000Z"),  # inside window, no known version
            _row("c", ts="garbage")]
    result = enrich_rows(rows, CONFIG)
    assert [r["period"] for r in result.rows] == ["before", "unknown", "unknown"]
    assert (result.conflicts, result.bad_timestamp) == (1, 1)
    assert result.period_counts == {"before": 1, "unknown": 2}


def test_write_enriched_is_idempotent(tmp_path):
    out = tmp_path / "nested" / "out.csv"
    rows = enrich_rows([_row("a")], CONFIG).rows
    write_enriched(out, rows)
    write_enriched(out, rows)
    with open(out, newline="", encoding="utf-8") as handle:
        read = list(csv.DictReader(handle))
    assert len(read) == 1 and list(read[0]) == FIELDNAMES
    assert not list(out.parent.glob("*.tmp"))


def test_parse_utc_handles_z_and_garbage():
    assert parse_utc("2026-11-05T00:19:19.950Z").tzinfo == timezone.utc
    assert parse_utc("nope") is None and parse_utc("") is None
