"""Does a bounded per-tenant pool with an Athena concurrency cap cut wall-clock vs serial, with ordered results,
failure isolation and FCID propagation? Simulated units, no AWS.

Run: python3 scratch/2026-11-02_pipeline-runtime_parallel-tenants_poc.py
Model: 4 tenants x 6 reports x 8 dates = 192 units (the real daily run is 163 queries in 593s, ~3.6s each);
durations are scaled by SCALE so the whole experiment takes seconds. QUOTA models Athena's per-account
concurrent-query limit: a unit that starts while QUOTA queries are running gets a throttle error and retries
after a short backoff (the real adapter only retries throttling raised by StartQueryExecution).
"""
from __future__ import annotations

import contextvars
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.lib.logging.context import bind_fcid, current_fcid  # noqa: E402

SCALE = 0.01
TENANTS = ["NG", "GH", "ZA", "ZM"]
REPORTS = ["adoption", "adoption-session", "shaka-hhid", "shaka-session", "guest-session", "shaka-1xxx-position"]
DATES = [f"2026-10-{d:02d}" for d in range(26, 34)]
QUOTA = 8
BACKOFF_S = 0.05


class Athena:
    """Fake account-wide Athena: counts concurrency, throttles above QUOTA, records the peak."""

    def __init__(self, quota: int) -> None:
        self.quota, self.running, self.peak, self.throttled = quota, 0, 0, 0
        self.lock = threading.Lock()

    def query(self, seconds: float) -> None:
        while True:
            with self.lock:
                if self.running >= self.quota:
                    self.throttled += 1
                else:
                    self.running += 1
                    self.peak = max(self.peak, self.running)
                    break
            time.sleep(BACKOFF_S)
        try:
            time.sleep(seconds)
        finally:
            with self.lock:
                self.running -= 1


def make_unit(athena: Athena, cap: threading.Semaphore | None, fail: set, seen_fcids: list):
    def run(tenant: str, report: str, date: str) -> str:
        seen_fcids.append(current_fcid())
        if (tenant, report, date) in fail:
            raise RuntimeError(f"boom {tenant}/{report}/{date}")
        seconds = random.Random(f"{tenant}{report}{date}").uniform(2.0, 5.2) * SCALE
        if cap is None:
            athena.query(seconds)
        else:
            with cap:
                athena.query(seconds)
        return f"{tenant}/{report}/{date}"

    return run


def run_group(unit, tenant: str, parallel_reports: int) -> list:
    """One tenant's units, optionally parallel across reports. Never raises: failures become results."""
    jobs = [(tenant, r, d) for d in DATES for r in REPORTS]

    def safe(job):
        try:
            return unit(*job)
        except Exception as exc:  # isolation: one unit's failure must not cancel the others
            return exc

    if parallel_reports <= 1:
        return [safe(j) for j in jobs]
    with ThreadPoolExecutor(max_workers=parallel_reports) as pool:
        # copy_context() must run in the submitting thread, one copy per task (a Context cannot be entered concurrently)
        return list(pool.map(lambda pair: pair[1].run(safe, pair[0]), [(j, contextvars.copy_context()) for j in jobs]))


def scenario(name: str, *, tenant_workers: int, parallel_reports: int = 1, cap: int | None = None, quota: int = QUOTA,
             fail: set | None = None, propagate_ctx: bool = True) -> dict:
    athena, seen = Athena(quota), []
    semaphore = threading.Semaphore(cap) if cap else None
    unit = make_unit(athena, semaphore, fail or set(), seen)
    bind_fcid("poc-fcid")
    started = time.monotonic()
    if tenant_workers <= 1:
        results = [run_group(unit, t, parallel_reports) for t in TENANTS]
    else:
        with ThreadPoolExecutor(max_workers=tenant_workers) as pool:
            def submit(t):
                if propagate_ctx:
                    return pool.submit(contextvars.copy_context().run, run_group, unit, t, parallel_reports)
                return pool.submit(run_group, unit, t, parallel_reports)

            results = [f.result() for f in [submit(t) for t in TENANTS]]  # input order, not completion order
    wall = time.monotonic() - started
    flat = [x for group in results for x in group]
    return {
        "scenario": name, "wall_s": round(wall, 2), "failed": sum(isinstance(x, Exception) for x in flat), "units": len(flat),
        "peak": athena.peak, "throttled": athena.throttled, "fcid_ok": all(f == "poc-fcid" for f in seen),
        "first": flat[0] if isinstance(flat[0], str) else "ERR",
    }


def main() -> None:
    rows = [
        scenario("serial (today)", tenant_workers=1),
        scenario("tenants x2", tenant_workers=2),
        scenario("tenants x4", tenant_workers=4),
        scenario("tenants x4, no ctx copy", tenant_workers=4, propagate_ctx=False),
        scenario("tenants x4 + reports x6, no cap", tenant_workers=4, parallel_reports=6),
        scenario("tenants x4 + reports x6, cap=8", tenant_workers=4, parallel_reports=6, cap=8),
        scenario("tenants x4, GH has 3 failing units", tenant_workers=4,
                 fail={("GH", "shaka-hhid", DATES[1]), ("GH", "adoption", DATES[2]), ("GH", "guest-session", DATES[0])}),
    ]
    serial = rows[0]["wall_s"]
    print(f"{'scenario':<40}{'wall_s':>8}{'speedup':>9}{'peak_q':>8}{'throttle':>10}{'failed':>8}  fcid_ok")
    for r in rows:
        print(f"{r['scenario']:<40}{r['wall_s']:>8}{serial / r['wall_s']:>8.1f}x{r['peak']:>8}{r['throttled']:>10}{r['failed']:>8}  {r['fcid_ok']}")
    print(f"\nunits per scenario: {rows[0]['units']}; first result of ordered run: {rows[2]['first']}")


if __name__ == "__main__":
    main()
