"""Lightstep public-API client: token loading, ``query_timeseries``, UTC slicing and truncation-driven auto-split.

The HTTP layer is injected as a ``Transport`` so tests need no network. The token is read only from the
environment (else the gitignored root ``.env``) and is never logged.
"""

from __future__ import annotations

import http.client
import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

SERIES_CAP = 50
DEFAULT_SLICE = timedelta(hours=1)
MIN_SLICE = timedelta(seconds=1)
MAX_RETRIES = 5
BASE_BACKOFF_S = 1.0
REQUEST_TIMEOUT_S = 120.0
_TOKEN_VARS = {"EU": "LIGHTSTEP_API_KEY_EU", "US": "LIGHTSTEP_API_KEY_US"}
_REPO_ROOT = Path(__file__).resolve().parents[2]

Series = dict[str, object]
Window = tuple[datetime, datetime]


class LightstepError(Exception):
    """Base class for Lightstep client failures."""


class MissingTokenError(LightstepError):
    """The region's API token is not in the environment or ``.env``."""


class TransportError(LightstepError):
    """Network-level failure (connection reset, ``IncompleteRead``, timeout); retryable."""


class ApiError(LightstepError):
    """Non-retryable HTTP error, or a retryable one that exhausted its retries."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Lightstep API HTTP {status}: {message}")
        self.status = status


class TruncationError(LightstepError):
    """A slice still hits the series cap at the minimum width, so data would be lost."""


class Transport(Protocol):
    def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        """Returns ``(status, body)``; raises ``TransportError`` on network failure."""


class UrllibTransport:
    """Default transport built on ``urllib``; returns HTTP error statuses instead of raising."""

    def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https base URLs
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            raise TransportError(f"{type(exc).__name__}: {exc}") from exc



@dataclass(frozen=True)
class Project:
    base_url: str
    org: str
    project: str


def _parse_dotenv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        values[key] = value.strip().strip("'\"")
    return values


def load_token(region: str, *, env: Mapping[str, str] | None = None, dotenv_path: Path | None = None) -> str:
    """Returns the API token for ``region`` ("EU" or "US") from ``env``, else the ``.env`` file."""
    var = _TOKEN_VARS.get(region.upper())
    if var is None:
        raise ValueError(f"unknown Lightstep region {region!r}; expected one of {sorted(_TOKEN_VARS)}")
    environment = os.environ if env is None else env
    token = environment.get(var, "").strip()
    if not token:
        path = _REPO_ROOT / ".env" if dotenv_path is None else dotenv_path
        if path.is_file():
            token = _parse_dotenv(path.read_text(encoding="utf-8")).get(var, "").strip()
    if not token:
        raise MissingTokenError(f"{var} is not set in the environment or the root .env file")
    return token


def _rfc3339(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_day_window(day: str) -> Window:
    """Returns the full UTC day for ``YYYY-MM-DD`` as ``(00:00:00Z, next-day 00:00:00Z)``."""
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def split_window(oldest: datetime, youngest: datetime, width: timedelta = DEFAULT_SLICE) -> list[Window]:
    """Cuts ``[oldest, youngest)`` into contiguous slices of ``width``; the last may be shorter."""
    if oldest.tzinfo is None or youngest.tzinfo is None:
        raise ValueError("window bounds must be timezone-aware")
    if youngest <= oldest:
        raise ValueError("youngest must be after oldest")
    if width <= timedelta(0):
        raise ValueError("width must be positive")
    slices: list[Window] = []
    cursor = oldest
    while cursor < youngest:
        end = min(cursor + width, youngest)
        slices.append((cursor, end))
        cursor = end
    return slices


def query_timeseries(
    transport: Transport,
    *,
    project: Project,
    token: str,
    uql: str,
    oldest: datetime,
    youngest: datetime,
    output_period: int | None = None,
    max_retries: int = MAX_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Series]:
    """POSTs one ``query_timeseries`` call and returns its ``series`` (empty list when the key is absent).

    ``output_period`` (seconds) sets the point spacing; the default is one point spanning the whole window.

    Retries 429/5xx and network errors with exponential backoff up to ``max_retries`` retries.
    """
    url = f"{project.base_url}/{project.org}/projects/{project.project}/telemetry/query_timeseries"
    headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
    period = output_period or max(1, int((youngest - oldest).total_seconds()))
    attributes = {
        "query": uql,
        "query-type": "default",
        "oldest-time": _rfc3339(oldest),
        "youngest-time": _rfc3339(youngest),
        "output-period": period,
        "include-exemplars": False,
    }
    body = json.dumps({"data": {"attributes": attributes}}).encode("utf-8")
    for attempt in range(max_retries + 1):
        error: LightstepError
        try:
            status, payload = transport.post(url, headers, body, REQUEST_TIMEOUT_S)
        except TransportError as exc:
            error = exc
        else:
            if status == 200:
                return _extract_series(payload)
            error = ApiError(status, payload[:200].decode("utf-8", "replace"))
            if status != 429 and status < 500:
                raise error
        if attempt == max_retries:
            raise error
        delay = BASE_BACKOFF_S * 2**attempt
        logger.warning("lightstep call failed (%s); retry %d/%d in %.1fs", type(error).__name__, attempt + 1, max_retries, delay)
        sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


def _extract_series(payload: bytes) -> list[Series]:
    try:
        decoded = json.loads(payload)
        series = decoded["data"]["attributes"].get("series", [])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ApiError(200, f"unexpected response shape: {exc}") from exc
    if not isinstance(series, list):
        raise ApiError(200, "series is not a list")
    return series


def _series_key(series: Series) -> tuple[str, ...]:
    return tuple(sorted(str(label) for label in series.get("group-labels", [])))  # type: ignore[attr-defined]


def _fetch_slice(
    transport: Transport, window: Window, min_width: timedelta, cap: int, call: Callable[[Window], list[Series]], counter: list[int]
) -> list[Series]:
    series = call(window)
    counter[0] += 1
    if len(series) < cap:
        return series
    width = window[1] - window[0]
    if width / 2 < min_width:
        raise TruncationError(f"slice {_rfc3339(window[0])}..{_rfc3339(window[1])} still has >= {cap} series at minimum width {min_width}")
    middle = window[0] + width / 2
    middle = middle.replace(microsecond=0)
    if not window[0] < middle < window[1]:
        raise TruncationError(f"slice {_rfc3339(window[0])}..{_rfc3339(window[1])} cannot be split further")
    return _fetch_slice(transport, (window[0], middle), min_width, cap, call, counter) + _fetch_slice(
        transport, (middle, window[1]), min_width, cap, call, counter
    )


def merge_series(batches: list[Series]) -> list[Series]:
    """Merges series sharing a label set; points are unioned by timestamp (first value wins)."""
    merged: dict[tuple[str, ...], Series] = {}
    seen: dict[tuple[str, ...], set[object]] = {}
    for item in batches:
        key = _series_key(item)
        points = list(item.get("points", []))  # type: ignore[call-overload]
        if key not in merged:
            merged[key] = {**item, "points": []}
            seen[key] = set()
        for point in points:
            stamp = point[0] if isinstance(point, (list, tuple)) else point
            if stamp not in seen[key]:
                seen[key].add(stamp)
                merged[key]["points"].append(point)  # type: ignore[attr-defined]
    return list(merged.values())


def fetch_all_series(
    transport: Transport,
    *,
    project: Project,
    token: str,
    uql: str,
    oldest: datetime,
    youngest: datetime,
    slice_width: timedelta = DEFAULT_SLICE,
    min_width: timedelta = MIN_SLICE,
    cap: int = SERIES_CAP,
    output_period: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Series]:
    """Returns every series for ``[oldest, youngest)``, halving any slice that reaches ``cap`` series.

    Raises ``TruncationError`` rather than returning partial data when a slice cannot be split further.
    """

    def call(window: Window) -> list[Series]:
        return query_timeseries(
            transport, project=project, token=token, uql=uql, oldest=window[0], youngest=window[1],
            output_period=output_period, sleep=sleep,
        )

    counter = [0]
    collected: list[Series] = []
    for window in split_window(oldest, youngest, slice_width):
        collected.extend(_fetch_slice(transport, window, min_width, cap, call, counter))
    result = merge_series(collected)
    logger.info("fetched %d series in %d calls", len(result), counter[0])
    return result
