"""Business-logic tests for adoption report assembly."""
from __future__ import annotations

from types import SimpleNamespace

from src.pipelines.aws_access_cli import adoption
from src.pipelines.aws_access_cli.tenants import DEFAULT_TENANT


class FakeCatalog:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def render(self, key: str, params: dict[str, str]) -> str:
        self.calls.append((key, params))
        return key


class FakeAthena:
    def __init__(self, responses: dict[str, list[dict[str, str]]]) -> None:
        self.responses = responses

    def start_query(self, sql: str, _params: dict[str, str]) -> str:
        return sql

    def fetch_results(self, execution_id: str) -> SimpleNamespace:
        return SimpleNamespace(rows=self.responses[execution_id])


def test_adoption_metric_happy_path() -> None:
    catalog = FakeCatalog()
    athena = FakeAthena(
        {
            "q-home": [{"session_date": "2026-10-03", "metric_value": "7"}],
            "q-attempts": [{"session_date": "2026-10-03", "metric_value": "5"}],
        }
    )
    metrics = (
        adoption.MetricSpec("home", "Home", "q-home", {}),
        adoption.MetricSpec("attempts", "Attempts", "q-attempts", {}),
    )

    rows = adoption.build_adoption_report(
        athena,
        catalog,
        DEFAULT_TENANT,
        "2026-10-03",
        "2026-10-03",
        metrics=metrics,
    )

    assert rows == [{"session_date": "2026-10-03", "Home": "7", "Attempts": "5"}]


def test_adoption_metric_missing_data_edge_case() -> None:
    catalog = FakeCatalog()
    athena = FakeAthena({"q-empty": []})
    metrics = (adoption.MetricSpec("empty", "Empty", "q-empty", {}),)

    rows = adoption.build_adoption_report(
        athena,
        catalog,
        DEFAULT_TENANT,
        "2026-10-03",
        "2026-10-03",
        metrics=metrics,
    )

    assert rows == []
