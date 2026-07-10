#!/usr/bin/env python3
"""Benchmark Investigation Workbench cold-path latency.

Times account detail + case summary for the top flagged accounts.
Run against a deployed app or local dev server:

    APP_URL=https://<app>.databricksapps.com DATABRICKS_PROFILE=<profile> \\
        uv run python scripts/benchmark_investigation.py

    # Local (no auth):
    APP_URL=http://localhost:8000 uv run python scripts/benchmark_investigation.py
"""

from __future__ import annotations

import os
import statistics
import sys
import time

import requests

APP_URL = os.environ.get("APP_URL", "http://localhost:8000").rstrip("/")
PROFILE = os.environ.get("DATABRICKS_PROFILE", "")
TOP_N = int(os.environ.get("BENCHMARK_TOP_N", "5"))


def _headers() -> dict[str, str]:
    if not PROFILE:
        return {}
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient(profile=PROFILE)
    return w.config.authenticate()


def _timed_get(path: str, headers: dict[str, str]) -> tuple[float, int]:
    t0 = time.monotonic()
    r = requests.get(f"{APP_URL}{path}", headers=headers, timeout=120)
    elapsed = time.monotonic() - t0
    return elapsed, r.status_code


def _p50(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = min(len(sorted_v) - 1, int(len(sorted_v) * 0.95))
    return sorted_v[idx]


def main() -> int:
    headers = _headers()
    print(f"Benchmarking {APP_URL} (top {TOP_N} flagged accounts)\n")

    r = requests.get(f"{APP_URL}/api/investigation/accounts?limit={TOP_N}", headers=headers, timeout=60)
    if r.status_code != 200:
        print(f"Failed to list accounts: HTTP {r.status_code}", file=sys.stderr)
        return 1

    accounts = r.json()
    if not accounts:
        print("No flagged accounts returned.", file=sys.stderr)
        return 1

    summary_times: list[float] = []
    chart_times: list[float] = []
    case_summary_times: list[float] = []

    for acct in accounts:
        acct_id = acct["account_id"]
        drop = acct.get("consumption_drop_pct", 0)
        score = acct.get("composite_risk_score", 0)
        gaps = acct.get("comms_gap_count_30d", 0)
        risk = acct.get("risk_tier", "HIGH")

        summary_elapsed, summary_status = _timed_get(
            f"/api/investigation/accounts/{acct_id}/summary",
            headers,
        )
        summary_times.append(summary_elapsed)

        chart_elapsed, chart_status = _timed_get(
            f"/api/investigation/accounts/{acct_id}/consumption-chart",
            headers,
        )
        chart_times.append(chart_elapsed)

        case_path = (
            f"/api/llm/case-summary/{acct_id}"
            f"?skip_sql=true&risk_level={risk}"
            f"&consumption_drop_pct={drop}"
            f"&composite_risk_score={score}"
            f"&comms_gap_count_30d={gaps}"
        )
        case_elapsed, case_status = _timed_get(case_path, headers)
        case_summary_times.append(case_elapsed)

        print(
            f"  {acct_id}: summary={summary_elapsed:.2f}s ({summary_status}), "
            f"chart={chart_elapsed:.2f}s ({chart_status}), "
            f"case_summary={case_elapsed:.2f}s ({case_status})"
        )

    print()
    print(f"Account summary P50={_p50(summary_times):.2f}s  P95={_p95(summary_times):.2f}s")
    print(f"Consumption chart P50={_p50(chart_times):.2f}s  P95={_p95(chart_times):.2f}s")
    print(f"Case summary    P50={_p50(case_summary_times):.2f}s  P95={_p95(case_summary_times):.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
