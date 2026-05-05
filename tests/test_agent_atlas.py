"""Acceptance tests — Agent Atlas board report generation.

Tests run without a SQL Warehouse connection (offline mode).
The endpoint falls back to hardcoded defaults when no MAS, Genie,
Bedrock, or Gemini connections are available.
"""


class TestBoardReportGeneration:
    """TC-A1: Agent Atlas board report endpoint."""

    def test_board_report_returns_200_with_required_fields(self, client):
        """MUST: Board report responds and contains all top-level fields."""
        r = client.post("/api/agent/atlas/board-report")
        assert r.status_code == 200
        data = r.json()
        for field in (
            "report_title", "period", "generated_at", "executive_summary",
            "recommendations", "kpi_highlights", "agent_trace",
            "genie_questions_asked", "bedrock_tokens_used",
        ):
            assert field in data, f"Missing field: {field}"

    def test_board_report_content_populated(self, client):
        """MUST: Title, summary, recommendations, and market intel are populated."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert "Revenue Protection" in data["report_title"]
        assert len(data["executive_summary"]) > 0
        assert isinstance(data["recommendations"], list) and len(data["recommendations"]) > 0
        assert len(data.get("market_intelligence", "")) > 0

    def test_board_report_offline_metadata(self, client):
        """SHOULD: Offline mode uses zero LLM tokens and returns trace as list."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert isinstance(data["agent_trace"], list)
        assert data["bedrock_tokens_used"] == 0
