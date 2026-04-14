"""Acceptance tests — Robbie's Investigation Workbench."""


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

    def test_accounts_filter_by_fuel_type(self, client):
        """SHOULD: Fuel type filter is accepted."""
        r = client.get("/api/investigation/accounts?fuel_type=electricity")
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
        signals = data["signals"]
        assert "isolation_forest_score" in signals
        assert "lstm_deviation_score" in signals
        assert "cohort_deviation_score" in signals

    def test_account_detail_has_meter_reads(self, client):
        """MUST: Response contains meter_reads list."""
        data = client.get("/api/investigation/accounts/BG-0000001").json()
        assert "meter_reads" in data
        assert isinstance(data["meter_reads"], list)

    def test_account_detail_has_risk_tier(self, client):
        """MUST: Response contains risk_tier."""
        data = client.get("/api/investigation/accounts/BG-0000001").json()
        assert data["risk_tier"] in ["HIGH", "MEDIUM", "LOW"]


class TestLLMCaseSummary:
    """TC-I3: Bedrock LLM case summary."""

    def test_case_summary_returns_200(self, client):
        """MUST: Case summary endpoint responds."""
        r = client.get("/api/llm/case-summary/BG-0000001")
        assert r.status_code == 200

    def test_case_summary_has_required_fields(self, client):
        """MUST: Summary contains all required fields."""
        data = client.get("/api/llm/case-summary/BG-0000001").json()
        required = ["account_id", "risk_level", "key_signals", "recommended_action", "priority"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_case_summary_signals_is_list(self, client):
        """MUST: key_signals is a non-empty list."""
        data = client.get("/api/llm/case-summary/BG-0000001").json()
        assert isinstance(data["key_signals"], list)
        assert len(data["key_signals"]) > 0
