"""Acceptance tests — Robbie's Investigation Workbench."""

import pytest


class TestCloseInvestigation:
    """TC-I4: Close investigation endpoint."""

    @pytest.mark.parametrize(
        "outcome,expected_db,send_amount,expected_amount",
        [
            ("confirmed_theft", "THEFT_CONFIRMED", 4500.00, 4500.00),
            ("no_theft", "FALSE_POSITIVE", None, None),
            ("inconclusive", "INCONCLUSIVE", None, None),
        ],
    )
    def test_close_outcome_mapping_and_response(
        self, client, outcome, expected_db, send_amount, expected_amount
    ):
        """MUST: Each outcome returns 200 with correct DB enum and recovered amount."""
        payload = {"outcome": outcome}
        if send_amount is not None:
            payload["recovered_amount"] = send_amount
        r = client.post("/api/investigation/UKI-0000001/close", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["account_id"] == "UKI-0000001"
        assert data["outcome"] == expected_db
        assert data["recovered_amount"] == expected_amount
        assert "message" in data

    def test_close_ignores_recovered_for_non_theft(self, client):
        """MUST: recovered_amount is null when outcome is not confirmed_theft."""
        r = client.post(
            "/api/investigation/UKI-0000001/close",
            json={"outcome": "no_theft", "recovered_amount": 9999},
        )
        assert r.status_code == 200
        assert r.json()["recovered_amount"] is None

    def test_close_invalid_outcome_returns_422(self, client):
        """MUST: Invalid or missing outcome is rejected by Pydantic validation."""
        for payload in [
            {"outcome": "invalid_value"},
            {},
        ]:
            r = client.post("/api/investigation/UKI-0000001/close", json=payload)
            assert r.status_code == 422

    def test_close_notes_with_special_chars(self, client):
        """MUST: Notes with SQL-special characters don't crash."""
        r = client.post(
            "/api/investigation/UKI-0000001/close",
            json={
                "outcome": "confirmed_theft",
                "recovered_amount": 100,
                "notes": "O'Brien's meter — it's got 'quotes' and \"doubles\"",
            },
        )
        assert r.status_code == 200

    def test_close_cache_cleared(self, client):
        """MUST: Cache is empty after a close so next KPI read is fresh."""
        from energy_theft_detection.backend.router import _cache, _cache_set
        _cache_set("dashboard_kpis", {"stale": True})
        assert _cache.get("dashboard_kpis") is not None

        client.post(
            "/api/investigation/UKI-0000001/close",
            json={"outcome": "confirmed_theft", "recovered_amount": 500},
        )
        assert _cache.get("dashboard_kpis") is None


class TestFlaggedAccounts:
    """TC-I1: Flagged accounts list."""

    def test_accounts_returns_200(self, client):
        """MUST: Accounts endpoint responds."""
        r = client.get("/api/investigation/accounts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_accounts_filter_by_risk_tier(self, client):
        """SHOULD: Risk tier filter is accepted."""
        r = client.get("/api/investigation/accounts?risk_tier=HIGH")
        assert r.status_code == 200

    def test_accounts_pagination(self, client):
        """SHOULD: Limit and offset params are accepted."""
        r = client.get("/api/investigation/accounts?limit=10&offset=0")
        assert r.status_code == 200


class TestAccountDetail:
    """TC-I2: Account detail drawer."""

    def test_account_detail_returns_200(self, client):
        """MUST: Account detail responds for valid ID."""
        r = client.get("/api/investigation/accounts/BG-0000001")
        assert r.status_code == 200

    def test_account_detail_has_signals(self, client):
        """MUST: Response contains anomaly signals."""
        data = client.get("/api/investigation/accounts/BG-0000001").json()
        assert "signals" in data
        for key in ("isolation_forest_score", "lstm_deviation_score", "cohort_deviation_score"):
            assert key in data["signals"]

    def test_account_summary_returns_200(self, client):
        """MUST: Fast summary endpoint responds without chart series."""
        r = client.get("/api/investigation/accounts/BG-0000001/summary")
        assert r.status_code == 200
        data = r.json()
        assert "signals" in data
        assert "meter_reads" not in data

    def test_consumption_chart_returns_200(self, client):
        """MUST: Chart endpoint returns meter series."""
        r = client.get("/api/investigation/accounts/BG-0000001/consumption-chart")
        assert r.status_code == 200
        data = r.json()
        assert "meter_reads" in data
        assert "cohort_avg_reads" in data

    def test_meter_series_sorted_chronologically(self):
        """MUST: COLLECT_LIST order is normalized before charting."""
        from datetime import datetime

        from energy_theft_detection.backend.models import MeterReadPoint
        from energy_theft_detection.backend.router import _sort_meter_points

        unsorted = [
            MeterReadPoint(read_timestamp=datetime(2026, 3, 1), consumption_kwh=3.0, read_quality="actual"),
            MeterReadPoint(read_timestamp=datetime(2026, 1, 1), consumption_kwh=1.0, read_quality="actual"),
            MeterReadPoint(read_timestamp=datetime(2026, 2, 1), consumption_kwh=2.0, read_quality="actual"),
        ]
        sorted_pts = _sort_meter_points(unsorted)
        assert [p.consumption_kwh for p in sorted_pts] == [1.0, 2.0, 3.0]


class TestLLMCaseSummary:
    """TC-I3: Bedrock LLM case summary."""

    def test_case_summary_returns_200(self, client):
        """MUST: Case summary endpoint responds."""
        r = client.get("/api/llm/case-summary/BG-0000001")
        assert r.status_code == 200

    def test_case_summary_has_required_fields(self, client):
        """MUST: Summary contains all required fields."""
        data = client.get("/api/llm/case-summary/BG-0000001").json()
        for field in ("account_id", "risk_level", "key_signals", "recommended_action", "priority"):
            assert field in data, f"Missing field: {field}"
        assert isinstance(data["key_signals"], list)
        assert len(data["key_signals"]) > 0

    def test_case_summary_skip_sql_accepts_context(self, client):
        """MUST: skip_sql=true uses query params instead of anomaly_scores SQL."""
        r = client.get(
            "/api/llm/case-summary/BG-0000001"
            "?skip_sql=true&risk_level=HIGH&consumption_drop_pct=42.5"
            "&composite_risk_score=0.91&comms_gap_count_30d=7"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["risk_level"] == "HIGH"
        assert any("42.5%" in s for s in data["key_signals"])
        assert any("7 communication" in s for s in data["key_signals"])


class TestAccountDetailSQL:
    """Unit tests for account detail SQL helpers."""

    def test_account_detail_sql_gold_contains_gold_table(self):
        from energy_theft_detection.backend.router import _account_detail_sql

        sql = _account_detail_sql("UKI-0000001", use_gold=True)
        assert "gold_daily_consumption" in sql
        assert "smart_meter_reads" not in sql
        assert "ORDER BY day" in sql

    def test_consumption_chart_sql_uses_cohort_mv_when_enabled(self):
        from energy_theft_detection.backend.router import _consumption_chart_sql

        sql = _consumption_chart_sql("UKI-0000001", use_gold=True, use_cohort_mv=True)
        assert "gold_postcode_cohort_daily" in sql

    def test_account_detail_sql_bronze_fallback(self):
        from energy_theft_detection.backend.router import _account_detail_sql

        sql = _account_detail_sql("UKI-0000001", use_gold=False)
        assert "smart_meter_reads" in sql
        assert "gold_daily_consumption" not in sql
