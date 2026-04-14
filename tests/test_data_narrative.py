"""Data Narrative Consistency Tests.

Validates that the executive dashboard tells a consistent, data-driven story
end-to-end: the model_performance_log, investigation_cases, anomaly_scores,
KPI tiles, recovery opportunity, and case pipeline all reconcile.

These tests run against the FastAPI test client (fallback values) by default.
When SQL_WAREHOUSE_ID is set, they additionally validate live data.

Business narrative targets (March 2026):
  - Revenue recovered YTD: ~£34.9M (36% of £97M annual target)
  - 11 percentage points ahead of Q1 linear pace (25%)
  - Recovery rate: ~43% (vs 30% industry benchmark)
  - Pre-ML: tiny flagged/confirmed (8-25 HIGH flagged/month)
  - Post-ML: dramatic step-change (200-650 HIGH flagged/month, 55-74% hit rate)
  - March 2026 must have data (not empty)
  - Case Pipeline: 100+ open HIGH, meaningful in-progress and closed counts
"""

import pytest

ANNUAL_EXPOSURE = 323_000_000.0
BG_TARGET = 97_000_000.0
GROUP_ADJ_OP_PROFIT = 814_000_000.0
DIVISIONAL_AOP = 163_000_000.0


# ---------------------------------------------------------------------------
# TC-N1: KPI values match the £34.9M / 36% narrative
# ---------------------------------------------------------------------------

class TestNarrativeKPIs:
    """The KPI tiles must reflect the updated recovery narrative."""

    def test_recovered_ytd_above_30m(self, client):
        """Recovered YTD should be ≥£30M to tell the 36% story."""
        data = client.get("/api/dashboard/kpis").json()
        recovered = data["revenue_recovered_ytd_gbp"]
        assert recovered >= 30_000_000, (
            f"Recovered £{recovered:,.0f} is below the £30M floor — "
            "narrative needs ~£34.9M (36% of £97M target)"
        )

    def test_recovered_ytd_below_50m(self, client):
        """Recovered YTD should be realistic, not exceed £50M after Q1."""
        data = client.get("/api/dashboard/kpis").json()
        recovered = data["revenue_recovered_ytd_gbp"]
        assert recovered <= 50_000_000, (
            f"Recovered £{recovered:,.0f} exceeds £50M — unrealistic for Q1"
        )

    def test_recovery_rate_above_30_pct(self, client):
        """Recovery rate should exceed the 30% industry benchmark."""
        data = client.get("/api/dashboard/kpis").json()
        rate = data["recovery_rate_pct"]
        assert rate >= 30.0, (
            f"Recovery rate {rate}% is below 30% benchmark — "
            "narrative needs ~43% to show ML outperformance"
        )

    def test_recovery_rate_below_60_pct(self, client):
        """Recovery rate should be realistic (not inflated)."""
        data = client.get("/api/dashboard/kpis").json()
        rate = data["recovery_rate_pct"]
        assert rate <= 60.0, f"Recovery rate {rate}% is unrealistically high"

    def test_precision_above_65_pct(self, client):
        """Detection precision should reflect the ~72% narrative."""
        data = client.get("/api/dashboard/kpis").json()
        precision = data["detection_precision_pct"]
        assert precision >= 65.0, (
            f"Precision {precision}% too low — narrative expects ~72% "
            "to match Investigation Outcomes hit rate"
        )

    def test_precision_below_85_pct(self, client):
        """Precision should not be unrealistically high."""
        data = client.get("/api/dashboard/kpis").json()
        precision = data["detection_precision_pct"]
        assert precision <= 85.0, f"Precision {precision}% unrealistically high"

    def test_exposure_is_323m(self, client):
        """Annual exposure anchored at £323M (RECCo × BG market share)."""
        data = client.get("/api/dashboard/kpis").json()
        assert data["annual_theft_exposure_gbp"] == ANNUAL_EXPOSURE

    def test_recovery_target_is_97m(self, client):
        """Recovery target is 30% of £323M = £97M."""
        data = client.get("/api/dashboard/kpis").json()
        assert data["recovery_target_gbp"] == BG_TARGET

    def test_aop_ratio_is_198(self, client):
        """Exposure vs AOP should be ~198% (£323M / £163M)."""
        data = client.get("/api/dashboard/kpis").json()
        expected = round(ANNUAL_EXPOSURE / DIVISIONAL_AOP * 100, 0)
        assert data["exposure_vs_aop_pct"] == expected

    def test_recovered_pct_of_target_above_30(self, client):
        """Recovered as % of £97M target should be ≥30% (ahead of Q1 pace)."""
        data = client.get("/api/dashboard/kpis").json()
        pct = (data["revenue_recovered_ytd_gbp"] / BG_TARGET) * 100
        assert pct >= 30, (
            f"Only {pct:.1f}% of £97M target — should be ≥30% "
            "to show ahead-of-pace narrative"
        )


# ---------------------------------------------------------------------------
# TC-N2: Recovery Opportunity donut is internally consistent
# ---------------------------------------------------------------------------

class TestNarrativeRecoveryOpportunity:
    """Donut chart segments must sum to £323M and recovered must match KPIs."""

    def test_segments_sum_to_total(self, client):
        data = client.get("/api/dashboard/recovery-opportunity").json()
        parts = (
            data["recovered_ytd_gbp"]
            + data["high_confidence_gbp"]
            + data["medium_confidence_gbp"]
            + data["remaining_exposure_gbp"]
        )
        assert abs(parts - data["total_exposure_gbp"]) < 1.0

    def test_recovered_matches_kpi(self, client):
        """Recovered YTD in donut must match KPI tile value."""
        kpi = client.get("/api/dashboard/kpis").json()
        opp = client.get("/api/dashboard/recovery-opportunity").json()
        assert abs(kpi["revenue_recovered_ytd_gbp"] - opp["recovered_ytd_gbp"]) < 1.0, (
            f"KPI recovered £{kpi['revenue_recovered_ytd_gbp']:,.0f} != "
            f"donut recovered £{opp['recovered_ytd_gbp']:,.0f}"
        )

    def test_high_exceeds_medium(self, client):
        """HIGH confidence recovery should exceed MEDIUM (Pareto)."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["high_confidence_gbp"] > data["medium_confidence_gbp"]

    def test_high_accounts_above_100(self, client):
        """HIGH confidence account count should be meaningful (>100)."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["high_confidence_accounts"] >= 100, (
            f"Only {data['high_confidence_accounts']} HIGH accounts — "
            "need 100+ for a credible case pipeline"
        )

    def test_remaining_is_positive(self, client):
        """Remaining exposure should never go negative."""
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["remaining_exposure_gbp"] >= 0


# ---------------------------------------------------------------------------
# TC-N3: Case Pipeline is consistent with the investigation volume
# ---------------------------------------------------------------------------

class TestNarrativeCasePipeline:
    """Case Pipeline KPIs should reflect realistic investigation volumes."""

    def test_open_high_above_100(self, client):
        """Open HIGH risk cases should be 100+ (not single digits)."""
        data = client.get("/api/investigation/kpis").json()
        assert data["open_high_cases"] >= 100, (
            f"Only {data['open_high_cases']} open HIGH — "
            "should be 100+ to match the investigation volume narrative"
        )

    def test_in_progress_above_zero(self, client):
        """Some cases should be under active investigation."""
        data = client.get("/api/investigation/kpis").json()
        assert data["in_progress_cases"] > 0, (
            "Zero in-progress cases — investigators should be working on cases"
        )

    def test_closed_this_month_above_20(self, client):
        """Closed this month should be meaningful (>20)."""
        data = client.get("/api/investigation/kpis").json()
        assert data["closed_this_month"] >= 20, (
            f"Only {data['closed_this_month']} closed this month — "
            "should be ≥20 given the monthly investigation volume"
        )

    def test_confirmed_theft_this_month_positive(self, client):
        """Confirmed theft this month should be > 0."""
        data = client.get("/api/investigation/kpis").json()
        assert data["confirmed_theft_this_month"] > 0

    def test_confirmation_rate_above_60(self, client):
        """Confirmation rate (confirmed/closed) should be >60%."""
        data = client.get("/api/investigation/kpis").json()
        if data["closed_this_month"] > 0:
            rate = data["confirmed_theft_this_month"] / data["closed_this_month"] * 100
            assert rate >= 60, (
                f"Confirmation rate {rate:.1f}% — should be ≥60% "
                "to match the 72% hit rate narrative"
            )

    def test_confirmation_rate_below_95(self, client):
        """Confirmation rate should not be unrealistically high (like 100%)."""
        data = client.get("/api/investigation/kpis").json()
        if data["closed_this_month"] > 0:
            rate = data["confirmed_theft_this_month"] / data["closed_this_month"] * 100
            assert rate < 95, (
                f"Confirmation rate {rate:.1f}% is suspiciously high — "
                "100% implies every case is confirmed which is unrealistic"
            )

    def test_revenue_recovered_this_month_positive(self, client):
        """Monthly revenue recovered should be meaningful."""
        data = client.get("/api/investigation/kpis").json()
        assert data["revenue_recovered_this_month_gbp"] > 0


# ---------------------------------------------------------------------------
# TC-N4: Investigation Outcomes chart has correct shape
# ---------------------------------------------------------------------------

class TestNarrativeModelPerformance:
    """Model performance log should show tiny pre-ML, dramatic post-ML uplift."""

    def test_model_performance_returns_200(self, client):
        """Endpoint should respond successfully."""
        r = client.get("/api/governance/model-performance")
        assert r.status_code == 200

    def test_model_performance_has_data_when_sql_connected(self, client):
        """When SQL is available, should return data points."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data available (fallback returns empty list — run 01c notebook)")

    def test_has_pre_ml_and_post_ml_data(self, client):
        """Should have both manual_v1 and if_v1_lstm_v1 entries."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data available (fallback returns empty list)")
        versions = {p["model_version"] for p in data}
        assert "manual_v1" in versions, "No pre-ML (manual_v1) data"
        assert any("if_v1" in v for v in versions), "No post-ML data"

    def test_pre_ml_high_flagged_is_small(self, client):
        """Pre-ML HIGH flagged should be <50/month (manual process)."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data")
        pre_ml_high = [
            p for p in data
            if p["model_version"] == "manual_v1" and p["risk_tier"] == "HIGH"
        ]
        for p in pre_ml_high:
            assert p["cases_scored"] <= 50, (
                f"Pre-ML month {p['month']}: {p['cases_scored']} flagged HIGH — "
                "should be ≤50 for manual detection era"
            )

    def test_post_ml_high_flagged_is_large(self, client):
        """Post-ML HIGH flagged should be >150/month (ML step-change)."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data")
        post_ml_high = [
            p for p in data
            if p["model_version"] != "manual_v1" and p["risk_tier"] == "HIGH"
        ]
        assert len(post_ml_high) > 0, "No post-ML HIGH data points"
        for p in post_ml_high:
            assert p["cases_scored"] >= 150, (
                f"Post-ML month {p['month']}: {p['cases_scored']} flagged HIGH — "
                "should be ≥150 to show ML step-change"
            )

    def test_post_ml_precision_climbing(self, client):
        """Post-ML precision should generally increase over time."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data")
        post_ml_high = sorted(
            [p for p in data if p["model_version"] != "manual_v1" and p["risk_tier"] == "HIGH"],
            key=lambda p: p["month"],
        )
        if len(post_ml_high) < 3:
            pytest.skip("Not enough post-ML data points")
        first_precision = post_ml_high[0]["precision_pct"]
        last_precision = post_ml_high[-1]["precision_pct"]
        assert last_precision > first_precision, (
            f"Precision should climb: first={first_precision}%, last={last_precision}%"
        )

    def test_march_2026_has_data(self, client):
        """March 2026 must not be empty on the chart."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data")
        mar_2026 = [p for p in data if p["month"] == "2026-03"]
        assert len(mar_2026) > 0, (
            "March 2026 has no data — the chart will show an empty bar"
        )

    def test_march_2026_has_confirmed(self, client):
        """March 2026 HIGH should have confirmed > 0."""
        data = client.get("/api/governance/model-performance").json()
        if len(data) == 0:
            pytest.skip("No SQL data")
        mar_high = [
            p for p in data
            if p["month"] == "2026-03" and p["risk_tier"] == "HIGH"
        ]
        if not mar_high:
            pytest.skip("No March 2026 HIGH data")
        assert mar_high[0]["cases_confirmed"] > 0, (
            "March 2026 confirmed theft = 0 — chart bar will be empty"
        )


# ---------------------------------------------------------------------------
# TC-N5: Cross-check recovery across endpoints
# ---------------------------------------------------------------------------

class TestNarrativeCrossConsistency:
    """Numbers must reconcile across KPI, donut, case pipeline, and Genie."""

    def test_kpi_recovered_equals_donut_recovered(self, client):
        """Both sources of recovered YTD must agree."""
        kpi = client.get("/api/dashboard/kpis").json()
        opp = client.get("/api/dashboard/recovery-opportunity").json()
        diff = abs(kpi["revenue_recovered_ytd_gbp"] - opp["recovered_ytd_gbp"])
        assert diff < 1.0, (
            f"KPI says £{kpi['revenue_recovered_ytd_gbp']:,.0f}, "
            f"donut says £{opp['recovered_ytd_gbp']:,.0f}"
        )

    def test_kpi_precision_matches_investigation_kpis(self, client):
        """Dashboard precision and investigation precision should be close."""
        dash = client.get("/api/dashboard/kpis").json()
        inv = client.get("/api/investigation/kpis").json()
        diff = abs(dash["detection_precision_pct"] - inv["precision_rate_pct"])
        assert diff < 5.0, (
            f"Dashboard precision {dash['detection_precision_pct']}% vs "
            f"investigation precision {inv['precision_rate_pct']}% — "
            "should be within 5pts"
        )

    def test_annualised_run_rate_exceeds_bg_target(self, client):
        """At the current YTD recovery pace, annualised run-rate should exceed £97M."""
        kpi = client.get("/api/dashboard/kpis").json()
        recovered = kpi["revenue_recovered_ytd_gbp"]
        months_elapsed = 3  # March = Q1
        annualised = recovered * (12 / months_elapsed)
        assert annualised >= BG_TARGET, (
            f"Annualised run-rate £{annualised:,.0f} below £97M BG target — "
            "the narrative claims the model exceeds the target"
        )

    def test_story_beats_q1_linear_pace(self, client):
        """Recovered should be >25% of target (Q1 linear pace)."""
        kpi = client.get("/api/dashboard/kpis").json()
        recovered = kpi["revenue_recovered_ytd_gbp"]
        q1_pace = BG_TARGET * 0.25
        assert recovered > q1_pace, (
            f"Recovered £{recovered:,.0f} below Q1 linear pace "
            f"£{q1_pace:,.0f} (25% of £97M)"
        )


# ---------------------------------------------------------------------------
# TC-N6: Constants and anchors haven't drifted
# ---------------------------------------------------------------------------

class TestNarrativeAnchors:
    """Business constants that underpin the entire story must not drift."""

    def test_exposure_323m(self, client):
        data = client.get("/api/dashboard/kpis").json()
        assert data["annual_theft_exposure_gbp"] == 323_000_000.0

    def test_target_97m(self, client):
        data = client.get("/api/dashboard/kpis").json()
        assert data["recovery_target_gbp"] == 97_000_000.0

    def test_donut_total_323m(self, client):
        data = client.get("/api/dashboard/recovery-opportunity").json()
        assert data["total_exposure_gbp"] == 323_000_000.0
