"""Offline tests for the Athena fetch wrapper (fake client, no network)."""
from __future__ import annotations

from datetime import date

import pytest

from scripts.lib.athena_fetch import FetchError, fetch_missing
from scripts.lib.local_data import load_daily
from src.lib.athena.exceptions import AthenaQueryExecutionError
from src.lib.athena.protocols import QueryResult

DAYS = [date(2026, 11, 1), date(2026, 11, 2)]


class FakeClient:
    def __init__(self, fail=False):
        self.fail, self.sql = fail, []

    def start_query(self, sql, params):
        if self.fail:
            raise AthenaQueryExecutionError("boom")
        self.sql.append(sql)
        return f"id{len(self.sql)}"

    def poll_status(self, execution_id):
        return "SUCCEEDED"

    def fetch_results(self, execution_id):
        return QueryResult(execution_id, [{"sessionId": execution_id}], "SUCCEEDED")


@pytest.fixture()
def query_dir(tmp_path):
    directory = tmp_path / "queries"
    directory.mkdir()
    (directory / "demo.sql").write_text("SELECT 1 WHERE d = '{{date}}' AND db = '{{database}}'", encoding="utf-8")
    return directory


def _fetch(client, tmp_path, query_dir, dates=DAYS, name="demo"):
    return fetch_missing(client, name, dates, artifact="session", out_dir=tmp_path / "out",
                         params={"database": "db1"}, query_dir=query_dir)


def test_fetch_only_missing_dates(tmp_path, query_dir):
    client = FakeClient()
    first = _fetch(client, tmp_path, query_dir, DAYS[:1])
    second = _fetch(client, tmp_path, query_dir)
    assert len(client.sql) == 2 and "2026-11-02" in client.sql[1] and "db1" in client.sql[1]
    assert first.saved.keys() == {DAYS[0]} and second.skipped == [DAYS[0]]
    loaded = load_daily([tmp_path / "out"], "session", DAYS)
    assert loaded.missing == [] and len(loaded.rows) == 2


def test_fetch_error_wraps_client_exception(tmp_path, query_dir):
    with pytest.raises(FetchError) as info:
        _fetch(FakeClient(fail=True), tmp_path, query_dir)
    assert isinstance(info.value.__cause__, AthenaQueryExecutionError)
    assert not (tmp_path / "out" / "2026-11-01_session.csv").exists()


def test_bad_save_leaves_no_partial_file(tmp_path, query_dir):
    with pytest.raises(FetchError):
        fetch_missing(FakeClient(), "demo", DAYS[:1], artifact="session", out_dir=tmp_path / "out",
                      params={"database": "db1"}, fieldnames=["other"], query_dir=query_dir)
    assert list((tmp_path / "out").iterdir()) == []


def test_query_without_date_placeholder_raises(tmp_path, query_dir):
    (query_dir / "undated.sql").write_text("SELECT 1", encoding="utf-8")
    with pytest.raises(FetchError):
        _fetch(FakeClient(), tmp_path, query_dir, name="undated")


def test_unregistered_query_raises(tmp_path, query_dir):
    with pytest.raises(FetchError):
        _fetch(FakeClient(), tmp_path, query_dir, name="nope")
