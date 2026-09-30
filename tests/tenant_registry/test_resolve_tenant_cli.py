"""Tests for scripts/resolve_tenant.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cli_success_prints_json_and_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/resolve_tenant.py", "--system", "lightstep_go", "--tenant", "GH"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "filter": {"sessionInfo.busUnitId": "apbyfj9d"},
        "project": "mcs-go-prod-mtn-1-eu",
        "region": "EU",
    }


def test_cli_unknown_tenant_exits_nonzero_with_message() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/resolve_tenant.py", "--system", "athena", "--tenant", "missing"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Unknown tenant 'missing'. Available tenant ids: iye9omdf, q95itlcu, dtunf6yo, apbyfj9d" in result.stderr
