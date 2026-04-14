"""Acceptance tests — Susie's Executive Dashboard.

Tests run without a SQL Warehouse connection (default values).
Priority: MUST = blocks demo, SHOULD = enhances demo, NICE = polish.
"""

import pytest


class TestDashboardKPIs:
    """TC-D1: KPI tiles return valid data."""

    def test_kpis_returns_200(self, client):
        """MUST: KPI endpoint responds."""
        r = client.get("/api/dashboard/kpis")
        assert r.status_code == 200

    def test_kpis_has_required_fields(self, client):
        """MUST: Response contains all KPI fields."""
        data = client.get("/api/dashboard/kpis").json()
        required = [
            "annual_theft_exposure_gbp",
            "exposure_vs_aop_pct",
            "revenue_recovered_ytd_gbp",
            "recovery_rate_pct",
            "detection_precision_pct",
            "recovery_target_gbp",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_kpis_values_are_positive(self, client):
        """MUST: All KPI values are non-negative."""
        data = client.get("/api/dashboard/kpis").json()
        assert data["annual_theft_exposure_gbp"] > 0
        assert data["exposure_vs_aop_pct"] >= 0
        assert data["revenue_recovered_ytd_gbp"] >= 0
        assert data["recovery_rate_pct"] >= 0
        assert data["detection_precision_pct"] >= 0

    def test_exposure_is_reasonable(self, client):
        """MUST: Annual exposure is a realistic figure (< £1B)."""
        data = client.get("/api/dashboard/kpis").json()
        assert 0 < data["annual_theft_exposure_gbp"] < 1_000_000_000

    def test_recovery_rate_is_realistic(self, client):
        """MUST: Recovery rate % is realistic (not inflated by bad scaling)."""
        data = client.get("/api/dashboard/kpis").json()
        assert data["recovery_rate_pct"] < 300, (
            f"Recovery rate {data['recovery_rate_pct']}% is unrealistic — "
            "default values may not match expected recovery target"
        )

    def test_recovered_less_than_1b(self, client):
        """MUST: Recovered YTD is a realistic industry figure, not billions."""
        data = client.get("/api/dashboard/kpis").json()
        assert data["revenue_recovered_ytd_gbp"] < 1_000_000_000, (
            f"Recovered £{data['revenue_recovered_ytd_gbp']:,.0f} is unrealistic — "
            "check default recovered value is realistic"
        )

    def test_precision_is_realistic(self, client):
        """MUST: Default precision reflects real-world hit rate (~60-70%)."""
        data = client.get("/api/dashboard/kpis").json()
        assert 50 <= data["detection_precision_pct"] <= 90


class TestDashboardHeatmap:
    """TC-D2: Risk heatmap endpoint."""

    def test_heatmap_returns_200(self, client):
        """MUST: Heatmap endpoint responds with a list."""
        r = client.get("/api/dashboard/heatmap")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestDashboardTrend:
    """TC-D3: Theft signal trend endpoint."""

    def test_trend_returns_200(self, client):
        """MUST: Trend endpoint responds with a list."""
        r = client.get("/api/dashboard/trend")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestDashboardFuelSplit:
    """TC-D4: Fuel type split."""

    def test_fuel_split_returns_200(self, client):
        """MUST: Fuel split endpoint responds."""
        r = client.get("/api/dashboard/fuel-split")
        assert r.status_code == 200

    def test_fuel_split_has_two_types(self, client):
        """SHOULD: Returns both electricity and gas."""
        data = client.get("/api/dashboard/fuel-split").json()
        fuel_types = {item["fuel_type"] for item in data}
        assert "electricity" in fuel_types
        assert "gas" in fuel_types

    def test_fuel_split_percentages_sum_to_100(self, client):
        """SHOULD: Percentages sum to 100."""
        data = client.get("/api/dashboard/fuel-split").json()
        total = sum(item["percentage"] for item in data)
        assert abs(total - 100.0) < 0.1


class TestRecoveryOpportunity:
    """TC-D5: Revenue recovery opportunity endpoint (donut chart data)."""

    def test_returns_200(self, client):
        """MUST: Endpoint responds."""
        r = client.get("/api/dashboard/recovery-opportunity")
        assert r.status_code == 200

    def test_has_required_fields(self, client):
        """MUST: Response contains all segment fields."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        required = [
            "total_exposure_gbp",
            "recovered_ytd_gbp",
            "high_confidence_gbp",
            "high_confidence_accounts",
            "medium_confidence_gbp",
            "medium_confidence_accounts",
            "remaining_exposure_gbp",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_segments_sum_to_total(self, client):
        """MUST: Recovered + HIGH + MEDIUM + remaining = total exposure."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        parts = (
            data["recovered_ytd_gbp"]
            + data["high_confidence_gbp"]
            + data["medium_confidence_gbp"]
            + data["remaining_exposure_gbp"]
        )
        assert abs(parts - data["total_exposure_gbp"]) < 1.0, (
            f"Segments sum to {parts:,.0f} but total is {data['total_exposure_gbp']:,.0f}"
        )

    def test_total_is_323m(self, client):
        """MUST: Total exposure anchored at £323M."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["total_exposure_gbp"] == 323_000_000.0

    def test_remaining_is_positive(self, client):
        """MUST: Remaining exposure is non-negative (segments don't exceed total)."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["remaining_exposure_gbp"] >= 0

    def test_default_high_exceeds_medium(self, client):
        """SHOULD: HIGH confidence recovery exceeds MEDIUM in defaults."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["high_confidence_gbp"] > data["medium_confidence_gbp"]

    def test_default_accounts_are_positive(self, client):
        """SHOULD: Default account counts are realistic."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["high_confidence_accounts"] > 0
        assert data["medium_confidence_accounts"] > 0
