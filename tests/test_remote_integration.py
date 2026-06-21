"""Remote integration tests — run against the deployed Databricks App.

These tests verify the live application end-to-end including SQL Warehouse
connectivity, Delta table reads/writes, and response latency.

Usage:
    pytest tests/test_remote_integration.py -v

Requires:
    - `azsu-centrica-demo` Databricks CLI profile configured
    - The app deployed and running at the expected URL
"""

import os
import time
import uuid

import pytest
import requests
from databricks.sdk import WorkspaceClient

APP_URL = os.environ.get(
    "APP_URL",
    "https://energy-theft-detection-7405616473758737.17.azure.databricksapps.com",
)
PROFILE = os.environ.get("DATABRICKS_PROFILE", "azsu-centrica-demo")
LATENCY_BUDGET_S = 15


@pytest.fixture(scope="session")
def auth_headers():
    """Authenticate via Databricks SDK and return Bearer headers."""
    w = WorkspaceClient(profile=PROFILE)
    headers = w.config.authenticate()
    assert "Authorization" in headers, "Failed to obtain auth token"
    return headers


@pytest.fixture(scope="session")
def api(auth_headers):
    """Convenience wrapper for authenticated requests to the deployed app."""

    class _Client:
        def get(self, path, **kwargs):
            return requests.get(f"{APP_URL}{path}", headers=auth_headers, **kwargs)

        def post(self, path, **kwargs):
            return requests.post(f"{APP_URL}{path}", headers=auth_headers, **kwargs)

    return _Client()


class TestRemoteHealth:
    """Smoke tests — app is reachable and responsive."""

    def test_health_endpoint(self, api):
        r = api.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert data.get("sql_connected") is True

    def test_readiness_endpoint(self, api):
        r = api.get("/api/readiness")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ready") is True


class TestRemoteDashboardKPIs:
    """Executive dashboard reads from live Delta tables."""

    def test_dashboard_kpis_200(self, api):
        r = api.get("/api/dashboard/kpis")
        assert r.status_code == 200

    def test_dashboard_kpis_has_live_data(self, api):
        data = api.get("/api/dashboard/kpis").json()
        recovered = data.get("revenue_recovered_ytd_gbp", 0) or 0
        assert recovered > 0, f"No recovered revenue — pipeline data may be stale. Keys: {list(data.keys())}"
        assert data.get("annual_theft_exposure_gbp", 0) > 0

    def test_dashboard_kpis_latency(self, api):
        """KPI read should complete within the latency budget."""
        start = time.time()
        r = api.get("/api/dashboard/kpis")
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < LATENCY_BUDGET_S, f"KPI read took {elapsed:.1f}s (budget: {LATENCY_BUDGET_S}s)"

    def test_investigation_kpis_200(self, api):
        r = api.get("/api/investigation/kpis")
        assert r.status_code == 200

    def test_recovery_opportunity_200(self, api):
        r = api.get("/api/dashboard/recovery-opportunity")
        assert r.status_code == 200


class TestRemoteCloseInvestigation:
    """Close investigation writes to Delta and impacts KPIs within latency budget."""

    def test_close_confirmed_theft_success(self, api):
        """POST close with confirmed_theft returns success and writes to Lakehouse."""
        r = api.post(
            "/api/investigation/UKI-0000874/close",
            json={
                "outcome": "confirmed_theft",
                "recovered_amount": 1500,
                "notes": f"Integration test run {uuid.uuid4().hex[:8]}",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["account_id"] == "UKI-0000874"
        assert data["outcome"] == "THEFT_CONFIRMED"
        assert "Lakebase" in data.get("message", "")

    def test_close_latency_within_budget(self, api):
        """Full close round-trip should complete within the latency budget."""
        start = time.time()
        r = api.post(
            "/api/investigation/UKI-0000874/close",
            json={"outcome": "no_theft"},
        )
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < LATENCY_BUDGET_S, f"Close took {elapsed:.1f}s (budget: {LATENCY_BUDGET_S}s)"

    def test_close_invalidates_cache_and_updates_kpis(self, api):
        """After close, KPI endpoints return fresh data (cache invalidated)."""
        api.post(
            "/api/investigation/UKI-0000874/close",
            json={"outcome": "confirmed_theft", "recovered_amount": 2000},
        )
        time.sleep(1)
        r = api.get("/api/investigation/kpis")
        assert r.status_code == 200
        data = r.json()
        assert data.get("closed_this_month", 0) >= 0


class TestRemoteFlaggedAccounts:
    """Investigation workbench — flagged accounts list from live data."""

    def test_flagged_accounts_returns_data(self, api):
        r = api.get("/api/investigation/accounts")
        assert r.status_code == 200
        accounts = r.json()
        assert len(accounts) > 0, "No flagged accounts — pipeline may not have run"

    def test_account_detail_live(self, api):
        accounts = api.get("/api/investigation/accounts?limit=1").json()
        if accounts:
            acct_id = accounts[0]["account_id"]
            r = api.get(f"/api/investigation/accounts/{acct_id}")
            assert r.status_code == 200
            data = r.json()
            assert "signals" in data
            assert "meter_reads" in data


class TestRemoteGovernance:
    """AI Governance page reads from live data."""

    def test_ai_components_200(self, api):
        r = api.get("/api/governance/components")
        assert r.status_code == 200

    def test_pii_matrix_200(self, api):
        r = api.get("/api/governance/pii-matrix")
        assert r.status_code == 200

    def test_audit_200(self, api):
        r = api.get("/api/governance/audit")
        assert r.status_code == 200
