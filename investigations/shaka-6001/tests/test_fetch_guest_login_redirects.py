"""Offline tests for fetch_guest_login_redirects (fake client, tmp_path only, no AWS)."""
from __future__ import annotations

from datetime import date

import pytest

from scripts import fetch_guest_login_redirects as fetch
from scripts.lib.athena_fetch import QUERY_DIR, render_query
from src.lib.athena.protocols import QueryResult

DAYS = [date(2026, 11, 4), date(2026, 11, 5)]
REDIRECT_ROW = {"user_id": "GUEST.u1", "device_id": "d1", "event_source": "guestLoginPrompt-redirect"}
DEBUG_ROW = {"datetime": "2026-11-04T11:15:00.000Z", "clientid": "d1:GUEST.u1", "eventclass": "c", "eventid": "e",
             "eventdata": "{}"}


class FakeClient:
    def __init__(self):
        self.sql: list[str] = []

    def start_query(self, sql, params):
        self.sql.append(sql)
        return f"id{len(self.sql)}"

    def poll_status(self, execution_id):
        return "SUCCEEDED"

    def fetch_results(self, execution_id):
        sql = self.sql[int(execution_id[2:]) - 1]
        return QueryResult(execution_id, [DEBUG_ROW if "ccl_debug_events" in sql else REDIRECT_ROW], "SUCCEEDED")


def _run(client, out_dir, dates=DAYS):
    return fetch.fetch_redirects(client, dates, out_dir, database="unified_t", debug_events_table="t_ccl_debug_events")


def test_only_missing_dates_trigger_query(tmp_path):
    client = FakeClient()
    _run(client, tmp_path, DAYS[:1])
    assert len(client.sql) == 2
    redirects, debug = _run(client, tmp_path)
    assert len(client.sql) == 4  # only 2026-11-05 queried, once per artifact
    assert all("2026-11-05" in sql for sql in client.sql[2:])
    assert redirects.skipped == debug.skipped == DAYS[:1]
    assert fetch.missing_dates(DAYS, tmp_path) == []


def test_partially_saved_date_refetches_only_the_missing_artifact(tmp_path):
    _run(FakeClient(), tmp_path, DAYS[:1])
    (tmp_path / "2026-11-04_guest_redirect_debug_events.csv").unlink()
    client = FakeClient()
    _run(client, tmp_path, DAYS[:1])
    assert len(client.sql) == 1 and "ccl_debug_events" in client.sql[0]


def test_debug_join_key_built_from_guest_ids():
    sql = render_query(fetch.DEBUG_QUERY, {"database": "unified_t", "debug_events_table": "t_ccl_debug_events",
                                           "date": "2026-11-04"}, QUERY_DIR)
    assert "device_id || ':' || user_id" in sql and "d.clientid = g.clientid" in sql
    assert "guestLoginPrompt-redirect" in sql
    assert "d.datetime >= '2026-11-04T00:00:00.000Z'" in sql and "d.datetime <" in sql  # datetime range always bound
    assert "{{" not in sql


def test_empty_day_saves_header_only_file_so_it_is_not_refetched(tmp_path):
    class Empty(FakeClient):
        def fetch_results(self, execution_id):
            return QueryResult(execution_id, [], "SUCCEEDED")

    _run(Empty(), tmp_path, DAYS[:1])
    header = (tmp_path / "2026-11-04_guest_login_redirect.csv").read_text().splitlines()
    assert header == [",".join(fetch.REDIRECT_FIELDS)]
    assert fetch.missing_dates(DAYS[:1], tmp_path) == []


class _Resolver:
    def __init__(self, out_dir):
        self.out_dir = out_dir

    def resolve_investigation_data_dir(self, slug, tool, *, tenant=None):
        return self.out_dir


def _patch_resolver(monkeypatch, out_dir):
    monkeypatch.setattr(fetch.YamlPathResolver, "from_file", lambda *a, **k: _Resolver(out_dir))


def test_dry_run_needs_no_credentials_or_client(tmp_path, monkeypatch, capsys):
    _patch_resolver(monkeypatch, tmp_path)

    def boom(*a, **k):
        raise AssertionError("must not be called")

    code = fetch.main(["--start-date", "2026-11-04", "--end-date", "2026-11-05", "--dry-run"],
                      client_factory=boom, credential_check=boom)
    assert code == 0 and "estimated_scan_mb=1300" in capsys.readouterr().out


def test_missing_credentials_fail_fast_with_message(tmp_path, monkeypatch, capsys):
    _patch_resolver(monkeypatch, tmp_path)

    def expired(profile):
        raise fetch.RedirectFetchError(f"expired {profile}")

    def no_client(*a, **k):
        raise AssertionError("no client without credentials")

    code = fetch.main(["--start-date", "2026-11-04", "--end-date", "2026-11-04"],
                      client_factory=no_client, credential_check=expired)
    assert code == 1 and "expired" in capsys.readouterr().err


def test_main_fetches_with_injected_client(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch, tmp_path)
    client = FakeClient()
    code = fetch.main(["--start-date", "2026-11-04", "--end-date", "2026-11-04"],
                      client_factory=lambda *a: client, credential_check=lambda p: None)
    assert code == 0 and len(client.sql) == 2
    assert (tmp_path / "2026-11-04_guest_redirect_debug_events.csv").is_file()


def test_end_before_start_exits_nonzero(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch, tmp_path)
    assert fetch.main(["--start-date", "2026-11-05", "--end-date", "2026-11-04"]) == 1
