import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.lib import lightstep_api as ls

PROJECT = ls.Project("https://api.example/public/v0.2", "Org", "proj")
T0 = datetime(2026, 10, 29, tzinfo=timezone.utc)


def _ok(series):
    attrs = {"series": series} if series else {}
    return 200, json.dumps({"data": {"attributes": attrs}}).encode()


def _series(name, *stamps):
    return {"group-labels": [f"k={name}"], "points": [[s, 1] for s in stamps]}


class FakeTransport:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def post(self, url, headers, body, timeout):
        attrs = json.loads(body)["data"]["attributes"]
        self.calls.append((url, headers, attrs))
        result = self.handler(len(self.calls), attrs)
        if isinstance(result, Exception):
            raise result
        return result


def test_load_token_from_env_and_dotenv(tmp_path):
    assert ls.load_token("eu", env={"LIGHTSTEP_API_KEY_EU": " abc "}) == "abc"
    dotenv = tmp_path / ".env"
    dotenv.write_text("# c\nexport LIGHTSTEP_API_KEY_US='xyz'\n")
    assert ls.load_token("US", env={}, dotenv_path=dotenv) == "xyz"


def test_missing_token_raises(tmp_path):
    with pytest.raises(ls.MissingTokenError, match="LIGHTSTEP_API_KEY_EU"):
        ls.load_token("EU", env={}, dotenv_path=tmp_path / "none.env")
    with pytest.raises(ValueError):
        ls.load_token("APAC", env={})


def test_split_window_and_day():
    start, end = ls.utc_day_window("2026-10-29")
    assert len(ls.split_window(start, end)) == 24
    assert ls.split_window(T0, T0 + timedelta(minutes=90))[-1][1] == T0 + timedelta(minutes=90)
    with pytest.raises(ValueError):
        ls.split_window(T0, T0)


def test_query_timeseries_request_and_empty():
    t = FakeTransport(lambda n, a: _ok([]))
    out = ls.query_timeseries(t, project=PROJECT, token="secret", uql="q", oldest=T0, youngest=T0 + timedelta(hours=1))
    url, headers, attrs = t.calls[0]
    assert out == []
    assert url.endswith("/Org/projects/proj/telemetry/query_timeseries")
    assert headers["Authorization"] == "bearer secret"
    assert attrs["oldest-time"] == "2026-10-29T00:00:00Z" and attrs["output-period"] == 3600


def test_query_timeseries_retries_then_succeeds_and_fails_fast():
    seq = [ls.TransportError("IncompleteRead"), (503, b""), _ok([_series("a", 1)])]
    sleeps = []
    t = FakeTransport(lambda n, a: seq[n - 1])
    out = ls.query_timeseries(t, project=PROJECT, token="t", uql="q", oldest=T0, youngest=T0 + timedelta(hours=1), sleep=sleeps.append)
    assert len(out) == 1 and sleeps == [1.0, 2.0]

    t = FakeTransport(lambda n, a: (401, b"nope"))
    with pytest.raises(ls.ApiError) as info:
        ls.query_timeseries(t, project=PROJECT, token="t", uql="q", oldest=T0, youngest=T0 + timedelta(hours=1), sleep=sleeps.append)
    assert info.value.status == 401 and len(t.calls) == 1

    t = FakeTransport(lambda n, a: (429, b""))
    with pytest.raises(ls.ApiError):
        ls.query_timeseries(t, project=PROJECT, token="t", uql="q", oldest=T0, youngest=T0 + timedelta(hours=1), max_retries=2, sleep=lambda s: None)
    assert len(t.calls) == 3


def test_split_halves_on_truncation():
    def handler(n, attrs):
        if attrs["output-period"] > 1800:
            return _ok([_series(str(i), 1) for i in range(50)])
        return _ok([_series(f"{attrs['oldest-time']}-{i}", 1) for i in range(3)])

    t = FakeTransport(handler)
    out = ls.fetch_all_series(t, project=PROJECT, token="t", uql="q", oldest=T0, youngest=T0 + timedelta(hours=1))
    assert len(t.calls) == 3 and len(out) == 6


def test_dedupe_across_slices():
    def handler(n, attrs):
        return _ok([_series("same", *([100] if n == 1 else [100, 200]))])

    t = FakeTransport(handler)
    out = ls.fetch_all_series(t, project=PROJECT, token="t", uql="q", oldest=T0, youngest=T0 + timedelta(hours=2))
    assert len(out) == 1 and [p[0] for p in out[0]["points"]] == [100, 200]


def test_min_width_truncation_fails():
    t = FakeTransport(lambda n, a: _ok([_series(str(i), 1) for i in range(50)]))
    with pytest.raises(ls.TruncationError):
        ls.fetch_all_series(t, project=PROJECT, token="t", uql="q", oldest=T0, youngest=T0 + timedelta(seconds=4))
