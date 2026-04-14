"""Acceptance tests — Agent Atlas board report generation.

Tests run without a SQL Warehouse connection (offline mode).
The endpoint falls back to hardcoded defaults when no MAS, Genie,
Bedrock, or Gemini connections are available.
"""


class TestBoardReportGeneration:
    """TC-A1: Agent Atlas board report endpoint."""

    def test_board_report_returns_200(self, client):
        """MUST: Board report endpoint responds in offline mode."""
        r = client.post("/api/agent/atlas/board-report")
        assert r.status_code == 200

    def test_board_report_has_required_fields(self, client):
        """MUST: Response contains all top-level report fields."""
        data = client.post("/api/agent/atlas/board-report").json()
        required = [
            "report_title",
            "period",
            "generated_at",
            "executive_summary",
            "recommendations",
            "kpi_highlights",
            "agent_trace",
            "genie_questions_asked",
            "bedrock_tokens_used",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_board_report_has_title(self, client):
        """MUST: Report title includes 'Revenue Protection'."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert "Revenue Protection" in data["report_title"]

    def test_board_report_executive_summary_populated(self, client):
        """MUST: Executive summary is non-empty even in offline mode."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert len(data["executive_summary"]) > 0

    def test_board_report_has_recommendations(self, client):
        """MUST: Recommendations list is populated in offline mode."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0

    def test_board_report_market_intelligence_populated(self, client):
        """MUST: Market intelligence has fallback content in offline mode."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert "market_intelligence" in data
        assert len(data.get("market_intelligence", "")) > 0

    def test_board_report_trace_is_list(self, client):
        """MUST: Agent trace is a list (may be empty in offline mode)."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert isinstance(data["agent_trace"], list)

    def test_board_report_zero_tokens_offline(self, client):
        """SHOULD: No LLM tokens used in offline mode."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert data["bedrock_tokens_used"] == 0
