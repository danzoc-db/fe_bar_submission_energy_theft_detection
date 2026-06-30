"""Acceptance tests — Agent Atlas board report generation.

Tests run without a SQL Warehouse connection (offline mode).
The endpoint falls back to hardcoded defaults when no MAS, Genie,
Bedrock, or Gemini connections are available.
"""


class TestBoardReportJsonParsing:
    """TC-A1b: LLM JSON fence stripping for board report fields."""

    def test_parse_fenced_json_on_one_line(self):
        from energy_theft_detection.backend.router import _parse_llm_json_object

        raw = (
            '```json { "executive_summary": "As of May, revenue recovered exceeded target.", '
            '"recommendations": ["Increase investment"], '
            '"kpi_highlights": [{"label": "Recovered", "value": "£10M", "trend": "up", "context": "May"}] } ```'
        )
        parsed = _parse_llm_json_object(raw)
        assert parsed is not None
        assert parsed["executive_summary"].startswith("As of May")
        assert parsed["recommendations"] == ["Increase investment"]
        assert parsed["kpi_highlights"][0]["value"] == "£10M"

    def test_parse_multiline_fenced_json(self):
        from energy_theft_detection.backend.router import _parse_llm_json_object

        raw = """```json
{"executive_summary": "CFO summary.", "recommendations": []}
```"""
        parsed = _parse_llm_json_object(raw)
        assert parsed is not None
        assert parsed["executive_summary"] == "CFO summary."

    def test_apply_board_report_json_populates_fields(self):
        from energy_theft_detection.backend.models import BoardReport
        from energy_theft_detection.backend.router import _apply_board_report_json

        report = BoardReport(
            report_title="t",
            period="p",
            generated_at="g",
            executive_summary="",
            revenue_protection_overview="",
            regional_analysis="",
            model_performance_summary="",
            recommendations=[],
        )
        _apply_board_report_json(
            report,
            {
                "executive_summary": "Lead with £ impact.",
                "revenue_protection_overview": "Pipeline healthy.",
                "regional_analysis": "London leads.",
                "model_performance_summary": "High precision.",
                "recommendations": ["Act now"],
                "kpi_highlights": [{"label": "HIGH", "value": "146", "trend": "up", "context": "flagged"}],
            },
        )
        assert report.executive_summary == "Lead with £ impact."
        assert report.recommendations == ["Act now"]
        assert report.kpi_highlights[0].value == "146"


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
