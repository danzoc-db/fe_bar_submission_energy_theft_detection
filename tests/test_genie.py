"""Acceptance tests — Genie conversation endpoints.

Tests run without a SQL Warehouse or Genie Space connection (offline mode).
Endpoints return graceful defaults when Genie is unavailable.
"""

import pytest

from energy_theft_detection.backend.models import GenieMessage


class TestGenieConversation:
    """TC-GN1: Genie conversation lifecycle."""

    def test_start_conversation_returns_200(self, client):
        """MUST: Start conversation endpoint responds."""
        r = client.post("/api/genie/conversation")
        assert r.status_code == 200

    def test_start_conversation_shape(self, client):
        """MUST: New conversation has id 'new' and empty message list."""
        data = client.post("/api/genie/conversation").json()
        assert data["conversation_id"] == "new"
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) == 0


class TestGenieWarm:
    """TC-GN2: Genie pre-warm endpoint."""

    def test_warm_returns_200_with_message_shape(self, client):
        """MUST: Warm endpoint responds with role + content fields."""
        r = client.post("/api/genie/warm")
        assert r.status_code == 200
        data = r.json()
        assert "role" in data
        assert "content" in data


class TestGenieSendMessage:
    """TC-GN3: Genie message send endpoint."""

    def test_send_message_returns_200_with_shape(self, client):
        """MUST: Send message returns 200 with role, content (string), and conversation_id."""
        r = client.post(
            "/api/genie/conversation/new/message",
            params={"message": "How many accounts are flagged?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "role" in data
        assert isinstance(data["content"], str)
        assert "conversation_id" in data


class TestGenieMessageValidation:
    """TC-GN4: GenieMessage model handles non-string content robustly.

    The field_validator on `content` coerces non-string values (e.g. error
    dicts returned by the Genie API) to strings, preventing Pydantic
    ValidationErrors from bubbling up as 500s.
    """

    def test_dict_with_error_key_extracts_value(self):
        """Dict with 'error' key extracts the value directly."""
        msg = GenieMessage(role="assistant", content={"error": "PERMISSION_DENIED"})
        assert isinstance(msg.content, str)
        assert msg.content == "PERMISSION_DENIED"

    def test_dict_without_error_key_stringified(self):
        """Dict without 'error' key is str()-ified."""
        msg = GenieMessage(role="assistant", content={"status": "FAILED", "code": 403})
        assert isinstance(msg.content, str)
        assert "FAILED" in msg.content

    def test_string_content_passthrough(self):
        """Normal strings pass through unchanged."""
        msg = GenieMessage(role="assistant", content="All good")
        assert msg.content == "All good"

    def test_non_string_non_dict_coerced(self):
        """Non-string, non-dict values are str()-ified."""
        msg = GenieMessage(role="assistant", content=42)
        assert msg.content == "42"

    @pytest.mark.parametrize("payload", [
        {"error": "PERMISSION_DENIED: TABLES_MISSING_EXCEPTION"},
        {"error": "PERMISSION_DENIED"},
        {"error": "TABLES_MISSING_EXCEPTION", "message": "access denied"},
        {"status": "FAILED", "error_code": "PERMISSION_DENIED"},
    ])
    def test_permission_error_shapes_coerce_cleanly(self, payload):
        """Every permission-error shape the API might return must coerce to string."""
        msg = GenieMessage(role="assistant", content=payload)
        assert isinstance(msg.content, str)
        assert len(msg.content) > 0
