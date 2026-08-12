#!/usr/bin/env python3
"""Benchmark Genie conversation latency via the app API.

Times warm + representative dashboard questions end-to-end.

    APP_URL=https://<app>.databricksapps.com DATABRICKS_PROFILE=zoccali-fevm-aws \\
        uv run python scripts/benchmark_genie.py
"""

from __future__ import annotations

import os
import statistics
import sys
import time

import requests

APP_URL = os.environ.get("APP_URL", "http://localhost:8000").rstrip("/")
PROFILE = os.environ.get("DATABRICKS_PROFILE", "")

GENIE_QUESTIONS = [
    "What is our annualised run rate based on 2026 monthly recovery so far?",
    "Which postcode sectors have the most HIGH risk accounts? Rank the top 5.",
    "What is the current detection precision rate?",
]


def _headers() -> dict[str, str]:
    if not PROFILE:
        return {}
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient(profile=PROFILE).config.authenticate()


def _timed_post(path: str, headers: dict[str, str], params: dict | None = None) -> tuple[float, int, dict]:
    t0 = time.monotonic()
    r = requests.post(f"{APP_URL}{path}", headers=headers, params=params or {}, timeout=180)
    elapsed = time.monotonic() - t0
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return elapsed, r.status_code, data


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
    print(f"Genie benchmark — {APP_URL}\n")

    warm_elapsed, warm_status, warm_data = _timed_post("/api/genie/warm", headers)
    conv_id = warm_data.get("conversation_id") or "new"
    print(f"  warm: {warm_elapsed:.2f}s ({warm_status}), conversation_id={conv_id!r}")

    question_times: list[float] = []
    for q in GENIE_QUESTIONS:
        elapsed, status, resp = _timed_post(
            f"/api/genie/conversation/{conv_id}/message",
            headers,
            {"message": q},
        )
        question_times.append(elapsed)
        conv_id = resp.get("conversation_id") or conv_id
        preview = (resp.get("content") or "")[:80].replace("\n", " ")
        print(f"  Q: {q[:55]}… → {elapsed:.2f}s ({status}) — {preview}")

    print()
    print(f"Genie warm          {warm_elapsed:.2f}s")
    print(f"Genie questions     P50={_p50(question_times):.2f}s  P95={_p95(question_times):.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
