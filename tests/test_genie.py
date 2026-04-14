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

    def test_start_conversation_returns_new_id(self, client):
        """MUST: New conversation has id 'new'."""
        data = client.post("/api/genie/conversation").json()
        assert data["conversation_id"] == "new"

    def test_start_conversation_has_empty_messages(self, client):
        """MUST: New conversation starts with empty message list."""
        data = client.post("/api/genie/conversation").json()
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) == 0


class TestGenieWarm:
    """TC-GN2: Genie pre-warm endpoint."""

    def test_warm_returns_200(self, client):
        """MUST: Warm endpoint responds even without Genie connection."""
        r = client.post("/api/genie/warm")
        assert r.status_code == 200

    def test_warm_returns_message_shape(self, client):
        """MUST: Warm response has role and content fields."""
        data = client.post("/api/genie/warm").json()
        assert "role" in data
        assert "content" in data


class TestGenieSendMessage:
    """TC-GN3: Genie message send endpoint."""

    def test_send_message_returns_200(self, client):
        """MUST: Send message endpoint responds without Genie connection."""
        r = client.post(
            "/api/genie/conversation/new/message",
            params={"message": "How many accounts are flagged?"},
        )
        assert r.status_code == 200

    def test_send_message_returns_message_shape(self, client):
        """MUST: Response has role, content, and conversation_id fields."""
        data = client.post(
            "/api/genie/conversation/new/message",
            params={"message": "Test question"},
        ).json()
        assert "role" in data
        assert "content" in data
        assert "conversation_id" in data


class TestGenieMessageValidation:
    """TC-GN4: GenieMessage model handles error content robustly.

    The field_validator on `content` coerces non-string values (e.g. error
    dicts returned by the Genie API) to strings, preventing Pydantic
    ValidationErrors from bubbling up as 500s.
    """

    def test_dict_content_coerced_to_string(self):
        """Dict content from PERMISSION_DENIED errors is auto-coerced."""
        msg = GenieMessage(
            role="assistant",
            content={"error": "PERMISSION_DENIED: TABLES_MISSING_EXCEPTION"},
        )
        assert isinstance(msg.content, str)
        assert "PERMISSION_DENIED" in msg.content

    def test_dict_content_extracts_error_key(self):
        """When dict has an 'error' key, the validator extracts it directly."""
        msg = GenieMessage(
            role="assistant",
            content={"error": "Something went wrong"},
        )
        assert msg.content == "Something went wrong"

    def test_dict_content_without_error_key_stringified(self):
        """Dict without 'error' key is str()-ified."""
        msg = GenieMessage(
            role="assistant",
            content={"status": "FAILED", "code": 403},
        )
        assert isinstance(msg.content, str)
        assert "FAILED" in msg.content

    def test_string_content_accepted(self):
        msg = GenieMessage(role="assistant", content="All good")
        assert msg.content == "All good"

    def test_empty_string_content_accepted(self):
        msg = GenieMessage(role="assistant", content="")
        assert msg.content == ""

    def test_none_like_value_coerced(self):
        """Non-string, non-dict values are str()-ified."""
        msg = GenieMessage(role="assistant", content=42)
        assert msg.content == "42"

    def test_coercion_pattern_handles_dict(self):
        """The str() coercion pattern used in router.py must produce a valid string."""
        raw_error = {"error": "PERMISSION_DENIED...TABLES_MISSING_EXCEPTION"}
        coerced = str(raw_error) if not isinstance(raw_error, str) else raw_error
        msg = GenieMessage(role="assistant", content=coerced)
        assert isinstance(msg.content, str)
        assert "PERMISSION_DENIED" in msg.content

    def test_coercion_pattern_preserves_string(self):
        raw_error = "Genie was unable to answer."
        coerced = str(raw_error) if not isinstance(raw_error, str) else raw_error
        msg = GenieMessage(role="assistant", content=coerced)
        assert msg.content == "Genie was unable to answer."

    def test_send_message_offline_returns_string_content(self, client):
        """Offline send_message must always return content as a string."""
        data = client.post(
            "/api/genie/conversation/new/message",
            params={"message": "How are we trending on target?"},
        ).json()
        assert isinstance(data["content"], str)


class TestGeniePermissionErrorHandling:
    """TC-GN5: Permission-denied errors surface as user-friendly messages.

    When the app SP lacks SELECT on the Genie Space's underlying tables,
    the API returns a dict like ``{"error": "PERMISSION_DENIED...
    TABLES_MISSING_EXCEPTION"}``.  These must never cause a 500.
    """

    PERM_ERROR_PAYLOADS = [
        {"error": "PERMISSION_DENIED: User does not have SELECT on schema.table [TABLES_MISSING_EXCEPTION]"},
        {"error": "PERMISSION_DENIED"},
        {"error": "TABLES_MISSING_EXCEPTION", "message": "access denied"},
        {"status": "FAILED", "error_code": "PERMISSION_DENIED"},
    ]

    @pytest.mark.parametrize("payload", PERM_ERROR_PAYLOADS)
    def test_permission_error_dict_produces_valid_genie_message(self, payload):
        """Every permission-error shape the API might return must coerce cleanly."""
        msg = GenieMessage(role="assistant", content=payload)
        assert isinstance(msg.content, str)
        assert len(msg.content) > 0

    def test_offline_send_never_returns_500(self, client):
        """Without Genie configured, the endpoint must return 200 with a string."""
        r = client.post(
            "/api/genie/conversation/new/message",
            params={"message": "Show theft cases by region"},
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["content"], str)
