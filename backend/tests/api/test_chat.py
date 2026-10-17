"""
Chat API endpoint tests.

Tests /api/chat/* endpoints covering:
- Query routing (success, auth, validation)
- Admin role restriction (staff rejected)
- Session ownership enforcement
- Conversation history CRUD
- Suggestions endpoint
- Vector memory integration path (mocked)
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import get_auth_header


# Helpers

def _mock_agent_response(text: str = "Stock is healthy across all locations."):
    """Return a mock that replaces invoke_agent with a canned answer."""
    return patch(
        "app.api.routes.chat.invoke_agent",
        return_value=text,
    )


def _mock_agent_available(available: bool = True):
    return patch("app.api.routes.chat.is_agent_available", return_value=available)


def _mock_vector_memory():
    """Mock VectorMemory so tests don't touch Qdrant."""
    mock_mem = MagicMock()
    mock_mem.is_available = False
    return patch(
        "app.api.routes.chat.get_vector_memory",
        return_value=mock_mem,
    )


def _mock_inventory_has_data(has_data: bool = True):
    """Mock get_inventory_overview tool in the chat router namespace to report that DB has data."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = {
        "has_data": has_data,
        "locations": 1,
        "items": 1,
        "transactions": 1,
    }
    return patch(
        "app.api.routes.chat.get_inventory_overview",
        new=mock_tool,
    )


# /api/chat/query

class TestChatQuery:
    """POST /api/chat/query"""

    def test_query_unauthenticated_rejected(self, client):
        response = client.post("/api/chat/query", json={"question": "What is the stock?"})
        assert response.status_code in [401, 403]

    def test_query_staff_role_rejected(self, client, test_user):
        """Staff users must be blocked from accessing AI Assistant."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/chat/query",
            json={"question": "What is the stock?"},
            headers=headers,
        )
        assert response.status_code == 403
        assert "reserved for Pharmacy Administrators" in response.json()["error"]["message"]

    def test_query_too_short_rejected(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.post(
            "/api/chat/query",
            json={"question": "Hi"},
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_query_empty_string_rejected(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.post(
            "/api/chat/query",
            json={"question": ""},
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_query_returns_response_with_agent(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory(), _mock_inventory_has_data():
            response = client.post(
                "/api/chat/query",
                json={"question": "What items are critical?"},
                headers=headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data
        assert "conversation_id" in data

    def test_query_creates_new_conversation_id(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory(), _mock_inventory_has_data():
            response = client.post(
                "/api/chat/query",
                json={"question": "Show me the stock levels"},
                headers=headers,
            )
        assert response.status_code == 200
        conv_id = response.json().get("conversation_id")
        assert conv_id is not None
        assert conv_id.startswith("conv_")

    def test_query_continues_existing_conversation(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])

        # First message — create conversation
        with _mock_agent_available(True), _mock_agent_response("Here is the summary."), _mock_vector_memory(), _mock_inventory_has_data():
            r1 = client.post(
                "/api/chat/query",
                json={"question": "Give me the inventory summary"},
                headers=headers,
            )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Second message — continue conversation
        with _mock_agent_available(True), _mock_agent_response("Continuing the conversation."), _mock_vector_memory(), _mock_inventory_has_data():
            r2 = client.post(
                "/api/chat/query",
                json={"question": "What about warning items?", "conversation_id": conv_id},
                headers=headers,
            )
        assert r2.status_code == 200
        assert r2.json()["conversation_id"] == conv_id

    def test_query_falls_back_to_rule_based_when_agent_unavailable(self, client, admin_user):
        """When agent is unavailable the rule-based fallback must still return 200."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        with _mock_agent_available(False), _mock_vector_memory():
            response = client.post(
                "/api/chat/query",
                json={"question": "What are the critical alerts?"},
                headers=headers,
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_query_suggested_actions_for_order_response(self, client, admin_user):
        """Responses mentioning 'order' trigger a suggested action."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        with _mock_agent_available(True), \
             _mock_agent_response("You should order more paracetamol."), \
             _mock_vector_memory(), \
             _mock_inventory_has_data():
            response = client.post(
                "/api/chat/query",
                json={"question": "What should I order today?"},
                headers=headers,
            )
        assert response.status_code == 200
        data = response.json()
        actions = data.get("suggested_actions") or []
        action_types = [a["action"] for a in actions]
        assert "export_reorder_list" in action_types


# Session ownership

class TestChatSessionOwnership:
    """Users may not access another user's conversation."""

    def _create_conversation(self, client, user: dict) -> str:
        headers = get_auth_header(client, user["username"], user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
            r = client.post(
                "/api/chat/query",
                json={"question": "Show me inventory overview"},
                headers=headers,
            )
        assert r.status_code == 200
        return r.json()["conversation_id"]

    def test_owner_can_read_own_history(self, client, admin_user):
        conv_id = self._create_conversation(client, admin_user)
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.get(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["conversation_id"] == conv_id

    def test_other_user_cannot_read_history(self, client, admin_user, test_user):
        """Another user should not see a conversation owned by admin_user."""
        conv_id = self._create_conversation(client, admin_user)
        other_headers = get_auth_header(client, test_user["username"], test_user["password"])
        r = client.get(f"/api/chat/history/{conv_id}", headers=other_headers)
        assert r.status_code in [403, 401]

    def test_other_user_cannot_continue_conversation(self, client, admin_user, test_user):
        """Another user posting to a conversation owned by admin_user must be rejected."""
        conv_id = self._create_conversation(client, admin_user)
        other_headers = get_auth_header(client, test_user["username"], test_user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
            r = client.post(
                "/api/chat/query",
                json={"question": "Show stock levels", "conversation_id": conv_id},
                headers=other_headers,
            )
        assert r.status_code in [403, 401]


# /api/chat/history

class TestChatHistory:
    """GET + DELETE /api/chat/history/{conversation_id}"""

    def _create_conversation(self, client, user: dict) -> str:
        headers = get_auth_header(client, user["username"], user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
            r = client.post(
                "/api/chat/query",
                json={"question": "List all warehouse locations"},
                headers=headers,
            )
        return r.json()["conversation_id"]

    def test_get_history_returns_messages(self, client, admin_user):
        conv_id = self._create_conversation(client, admin_user)
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.get(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 200
        messages = r.json()["messages"]
        assert len(messages) >= 2  # user message + assistant reply

    def test_get_history_nonexistent_returns_404(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.get("/api/chat/history/conv_does_not_exist", headers=headers)
        assert r.status_code == 404

    def test_delete_history_success(self, client, admin_user):
        conv_id = self._create_conversation(client, admin_user)
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.delete(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_get_history_after_delete_returns_404(self, client, admin_user):
        conv_id = self._create_conversation(client, admin_user)
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        client.delete(f"/api/chat/history/{conv_id}", headers=headers)
        r = client.get(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 404

    def test_unauthenticated_history_rejected(self, client):
        r = client.get("/api/chat/history/conv_abc123")
        assert r.status_code in [401, 403]


# /api/chat/sessions

class TestChatSessions:
    """GET /api/chat/sessions"""

    def test_sessions_list_empty_initially(self, client, admin_user):
        """Fresh admin user has no sessions yet."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.get("/api/chat/sessions", headers=headers)
        assert r.status_code == 200
        assert "sessions" in r.json()

    def test_sessions_list_unauthenticated_rejected(self, client):
        r = client.get("/api/chat/sessions")
        assert r.status_code in [401, 403]

    def test_sessions_list_grows_after_query(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r_before = client.get("/api/chat/sessions", headers=headers)
        count_before = len(r_before.json()["sessions"])

        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
            client.post(
                "/api/chat/query",
                json={"question": "How many items are in stock?"},
                headers=headers,
            )

        r_after = client.get("/api/chat/sessions", headers=headers)
        count_after = len(r_after.json()["sessions"])
        assert count_after >= count_before + 1


# /api/chat/suggestions

class TestChatSuggestions:
    """GET /api/chat/suggestions — authenticated endpoint."""

    def test_suggestions_unauthenticated_returns_401(self, client):
        r = client.get("/api/chat/suggestions")
        assert r.status_code == 401

    def test_suggestions_returns_categories(self, client, admin_user):
        headers = get_auth_header(client, admin_user["email"], admin_user["password"])
        r = client.get("/api/chat/suggestions", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        suggestions = data["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_suggestions_have_required_keys(self, client, admin_user):
        headers = get_auth_header(client, admin_user["email"], admin_user["password"])
        r = client.get("/api/chat/suggestions", headers=headers)
        assert r.status_code == 200
        for group in r.json()["suggestions"]:
            assert "category" in group
            assert "questions" in group
            assert isinstance(group["questions"], list)


# /api/chat/transcribe

class TestVoiceTranscribe:
    """POST /api/chat/transcribe — English-only voice transcription via Sarvam AI."""

    def test_transcribe_unauthenticated_returns_401(self, client):
        files = {"file": ("test.webm", b"fake audio bytes", "audio/webm")}
        r = client.post("/api/chat/transcribe", files=files)
        assert r.status_code == 401

    def test_transcribe_missing_key_returns_422(self, client, admin_user, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "SARVAM_API_KEY", "")
        headers = get_auth_header(client, admin_user["email"], admin_user["password"])
        files = {"file": ("test.webm", b"fake audio bytes", "audio/webm")}
        r = client.post("/api/chat/transcribe", files=files, headers=headers)
        assert r.status_code == 422
        error_msg = r.json().get("error", {}).get("message", "") or r.json().get("detail", "")
        assert "not configured" in error_msg.lower()

    def test_transcribe_success_en_in(self, client, admin_user, monkeypatch):
        from app.core.config import settings
        from unittest.mock import MagicMock
        monkeypatch.setattr(settings, "SARVAM_API_KEY", "test-sarvam-key")

        # Mock SarvamAI client
        mock_response = MagicMock()
        mock_response.transcript = "What medicines are running low in stock?"
        mock_client = MagicMock()
        mock_client.speech_to_text.transcribe.return_value = mock_response

        import sys
        mock_sarvam_mod = MagicMock()
        mock_sarvam_mod.SarvamAI.return_value = mock_client
        monkeypatch.setitem(sys.modules, "sarvamai", mock_sarvam_mod)

        headers = get_auth_header(client, admin_user["email"], admin_user["password"])
        files = {"file": ("query.webm", b"\x1a\x45\xdf\xa3" + b"sample-audio-data-padding-test-bytes-long", "audio/webm")}
        r = client.post("/api/chat/transcribe", files=files, headers=headers)

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["text"] == "What medicines are running low in stock?"

        # Verify language_code was explicitly 'en-IN'
        mock_client.speech_to_text.transcribe.assert_called_once()
        kwargs = mock_client.speech_to_text.transcribe.call_args.kwargs
        assert kwargs["language_code"] == "en-IN"
        assert kwargs["mode"] == "transcribe"
        assert kwargs["model"] == "saaras:v3"
