"""Cross-workspace reconciliation test for energy-theft-detection.

Hits key API endpoints on two deployed app instances and compares results to
verify feature parity — especially Power BI external lineage.

Usage:
    python3 scripts/reconcile_workspaces.py \\
        --before https://<your-app>.databricksapps.com \\
        --after  https://<your-new-app>.databricksapps.com \\
        [--token <DATABRICKS_PAT>]

    # Snapshot-only mode (capture current state before a redeploy):
    python3 scripts/reconcile_workspaces.py \\
        --snapshot https://<your-app>.databricksapps.com \\
        --out /tmp/before_snapshot.json

    # Compare a previously saved snapshot against the current live app:
    python3 scripts/reconcile_workspaces.py \\
        --compare /tmp/before_snapshot.json \\
        --after https://<your-new-app>.databricksapps.com
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


PROBE_TIMEOUT = 20  # seconds per request

ENDPOINTS = [
    ("health",            "/api/health",                             "GET"),
    ("dashboard_kpis",    "/api/dashboard/kpis",                    "GET"),
    ("investigation_kpis","/api/investigation/kpis",                "GET"),
    ("external_lineage",  "/api/governance/external-lineage",       "GET"),
    ("audit_summary",     "/api/governance/audit-summary",          "GET"),
    ("ai_components",     "/api/governance/ai-components",          "GET"),
]


@dataclass
class ProbeResult:
    endpoint_key: str
    url: str
    status_code: int
    latency_ms: int
    body: Any
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code in (200, 401)


def probe(base_url: str, path: str, token: str | None) -> ProbeResult:
    url = base_url.rstrip("/") + path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=PROBE_TIMEOUT, follow_redirects=True) as http:
            resp = http.get(url, headers=headers)
        ms = int((time.monotonic() - t0) * 1000)
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        return ProbeResult(
            endpoint_key=path,
            url=url,
            status_code=resp.status_code,
            latency_ms=ms,
            body=body,
        )
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        return ProbeResult(
            endpoint_key=path,
            url=url,
            status_code=0,
            latency_ms=ms,
            body=None,
            error=str(e)[:200],
        )


def snapshot_app(base_url: str, token: str | None) -> dict[str, Any]:
    results: dict[str, Any] = {"base_url": base_url, "captured_at": time.time(), "probes": {}}
    for key, path, _ in ENDPOINTS:
        r = probe(base_url, path, token)
        results["probes"][key] = {
            "url": r.url,
            "status_code": r.status_code,
            "latency_ms": r.latency_ms,
            "body": r.body,
            "error": r.error,
        }
        icon = "✅" if r.ok else "⚠️ "
        print(f"  {icon} {key}: HTTP {r.status_code} ({r.latency_ms}ms)")
    return results


def _extract_lineage_summary(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    nodes = body.get("nodes", [])
    edges = body.get("edges", [])
    return {
        "node_count": len(nodes),
        "pbi_node_count": sum(1 for n in nodes if n.get("system_type") == "POWER_BI"),
        "edge_count": len(edges),
        "source": body.get("source", "unknown"),
        "report_names": sorted(n.get("name", "") for n in nodes if n.get("system_type") == "POWER_BI"),
        "upstream_tables": sorted({e.get("source_table", "") for e in edges}),
    }


def _extract_health_summary(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    return {
        "sql_test": body.get("sql_test"),
        "catalog": body.get("catalog"),
        "schema_access_ok": body.get("schema_access_ok"),
    }


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Return a list of human-readable diff lines. Empty list = clean."""
    diffs: list[str] = []

    def _compare_key(key: str, extract_fn=None):
        bp = before["probes"].get(key, {})
        ap = after["probes"].get(key, {})

        before_code = bp.get("status_code", 0)
        after_code = ap.get("status_code", 0)
        if before_code != after_code:
            diffs.append(f"  {key}: HTTP {before_code} → {after_code}")

        if extract_fn:
            bv = extract_fn(bp.get("body"))
            av = extract_fn(ap.get("body"))
            for field_name in (set(bv) | set(av)):
                bval = bv.get(field_name)
                aval = av.get(field_name)
                if bval != aval:
                    diffs.append(f"  {key}.{field_name}: {bval!r} → {aval!r}")

    _compare_key("health", _extract_health_summary)
    _compare_key("external_lineage", _extract_lineage_summary)
    _compare_key("dashboard_kpis")
    _compare_key("investigation_kpis")
    _compare_key("audit_summary")
    _compare_key("ai_components")

    return diffs


def print_lineage_detail(label: str, snapshot: dict[str, Any]):
    probe = snapshot["probes"].get("external_lineage", {})
    body = probe.get("body", {})
    if not isinstance(body, dict):
        print(f"  {label}: no lineage data (HTTP {probe.get('status_code', '?')})")
        return
    summary = _extract_lineage_summary(body)
    print(f"  {label}:")
    print(f"    Power BI reports : {summary['pbi_node_count']} nodes")
    print(f"    Column edges     : {summary['edge_count']}")
    print(f"    Source           : {summary['source']}")
    print(f"    Reports          : {', '.join(summary['report_names']) or '(none)'}")
    print(f"    Upstream tables  : {', '.join(summary['upstream_tables']) or '(none)'}")


def main():
    parser = argparse.ArgumentParser(description="Cross-workspace reconciliation test")
    parser.add_argument("--before", help="App URL to snapshot as baseline")
    parser.add_argument("--after", help="App URL to test against baseline")
    parser.add_argument("--snapshot", help="App URL to snapshot only (saves to --out)")
    parser.add_argument("--compare", help="Path to saved baseline JSON snapshot")
    parser.add_argument("--out", default="/tmp/before_snapshot.json", help="Output file for --snapshot mode")
    parser.add_argument("--token", default=None, help="Databricks PAT for authenticated requests")
    parser.add_argument("--json", action="store_true", help="Output diff as JSON")
    args = parser.parse_args()

    # Snapshot-only mode
    if args.snapshot:
        print(f"\nSnapshotting {args.snapshot} ...")
        snap = snapshot_app(args.snapshot, args.token)
        with open(args.out, "w") as f:
            json.dump(snap, f, indent=2)
        print(f"\nSaved to {args.out}")
        print_lineage_detail("External lineage", snap)
        return

    # Resolve before snapshot
    before_snap: dict[str, Any] | None = None
    if args.compare:
        with open(args.compare) as f:
            before_snap = json.load(f)
        print(f"\nLoaded baseline from {args.compare} (captured {time.ctime(before_snap.get('captured_at', 0))})")
    elif args.before:
        print(f"\nSnapshotting BEFORE: {args.before}")
        before_snap = snapshot_app(args.before, args.token)
    else:
        parser.error("Provide --before or --compare")

    # Resolve after snapshot
    if not args.after:
        parser.error("Provide --after")
    print(f"\nSnapshotting AFTER: {args.after}")
    after_snap = snapshot_app(args.after, args.token)

    # Compare
    diffs = compare_snapshots(before_snap, after_snap)

    print(f"\n{'=' * 70}")
    print("  Workspace Reconciliation Report")
    print(f"  Before: {before_snap['base_url']}")
    print(f"  After : {after_snap['base_url']}")
    print(f"{'=' * 70}")

    print("\n  External Lineage (Power BI):")
    print_lineage_detail("Before", before_snap)
    print_lineage_detail("After ", after_snap)

    print(f"\n{'─' * 70}")
    if diffs:
        print(f"  {len(diffs)} difference(s) found:")
        for d in diffs:
            print(d)
    else:
        print("  No differences — workspaces are in parity.")
    print(f"{'─' * 70}\n")

    if args.json:
        out = {
            "before_url": before_snap["base_url"],
            "after_url": after_snap["base_url"],
            "diffs": diffs,
            "lineage_before": _extract_lineage_summary(
                before_snap["probes"].get("external_lineage", {}).get("body", {})
            ),
            "lineage_after": _extract_lineage_summary(
                after_snap["probes"].get("external_lineage", {}).get("body", {})
            ),
        }
        print(json.dumps(out, indent=2))

    sys.exit(0 if not diffs else 1)


if __name__ == "__main__":
    main()
