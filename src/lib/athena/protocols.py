"""Protocol skeletons for shared Athena execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable


@dataclass
class QueryResult:
    """Normalized Athena query outcome."""

    query_execution_id: str
    rows: list[dict[str, str]]
    state: str


@runtime_checkable
class AthenaClient(Protocol):
    """DIP seam replacing FCT-1's four Athena executors.

    The shared client boundary replaces:
    - github_copilot/oasis-athena-mcp/src/athena_mcp/query_tools.py
    - github_copilot/ctap-smvod-session-report/scripts/lib/athena_runner.py
    - github_copilot/aws-access-cli/scripts/athena_runner/query_executor.py
    - github_copilot/mtn-zm-session-device-investigation/scripts/run_athena_query.py
    """

    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        ...

    def poll_status(self, execution_id: str) -> str:
        ...

    def fetch_results(self, execution_id: str) -> QueryResult:
        ...
