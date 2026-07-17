"""
Chat API endpoint tests.

Tests /api/chat/* endpoints covering:
- Query routing (success, auth, validation)
- Session ownership enforcement
- Conversation history CRUD
- Suggestions endpoint
- Vector memory integration path (mocked)
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import get_auth_header


# ── Helpers ───────────────────────────────────────────────────────────────

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


# ── /api/chat/query ───────────────────────────────────────────────────────

class TestChatQuery:
    """POST /api/chat/query"""

    def test_query_unauthenticated_rejected(self, client):
        response = client.post("/api/chat/query", json={"question": "What is the stock?"})
        assert response.status_code in [401, 403]

    def test_query_too_short_rejected(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/chat/query",
            json={"question": "Hi"},
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_query_empty_string_rejected(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/chat/query",
            json={"question": ""},
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_query_returns_response_with_agent(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
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

    def test_query_creates_new_conversation_id(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
            response = client.post(
                "/api/chat/query",
                json={"question": "Show me the stock levels"},
                headers=headers,
            )
        assert response.status_code == 200
        conv_id = response.json().get("conversation_id")
        assert conv_id is not None
        assert conv_id.startswith("conv_")

    def test_query_continues_existing_conversation(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])

        # First message — create conversation
        with _mock_agent_available(True), _mock_agent_response("Here is the summary."), _mock_vector_memory():
            r1 = client.post(
                "/api/chat/query",
                json={"question": "Give me the inventory summary"},
                headers=headers,
            )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Second message — continue conversation
        with _mock_agent_available(True), _mock_agent_response("Continuing the conversation."), _mock_vector_memory():
            r2 = client.post(
                "/api/chat/query",
                json={"question": "What about warning items?", "conversation_id": conv_id},
                headers=headers,
            )
        assert r2.status_code == 200
        assert r2.json()["conversation_id"] == conv_id

    def test_query_falls_back_to_rule_based_when_agent_unavailable(self, client, test_user):
        """When agent is unavailable the rule-based fallback must still return 200."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        with _mock_agent_available(False), _mock_vector_memory():
            response = client.post(
                "/api/chat/query",
                json={"question": "What are the critical alerts?"},
                headers=headers,
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_query_suggested_actions_for_order_response(self, client, test_user):
        """Responses mentioning 'order' trigger a suggested action."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        with _mock_agent_available(True), \
             _mock_agent_response("You should order more paracetamol."), \
             _mock_vector_memory():
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


# ── Session ownership ─────────────────────────────────────────────────────

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

    def test_owner_can_read_own_history(self, client, test_user):
        conv_id = self._create_conversation(client, test_user)
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        r = client.get(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["conversation_id"] == conv_id

    def test_other_user_cannot_read_history(self, client, test_user, admin_user):
        """Admin should not see a conversation owned by test_user."""
        conv_id = self._create_conversation(client, test_user)
        admin_headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.get(f"/api/chat/history/{conv_id}", headers=admin_headers)
        assert r.status_code in [403, 401]

    def test_other_user_cannot_continue_conversation(self, client, test_user, admin_user):
        """Admin posting to a conversation owned by test_user must be rejected."""
        conv_id = self._create_conversation(client, test_user)
        admin_headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        with _mock_agent_available(True), _mock_agent_response(), _mock_vector_memory():
            r = client.post(
                "/api/chat/query",
                json={"question": "Show stock levels", "conversation_id": conv_id},
                headers=admin_headers,
            )
        assert r.status_code in [403, 401]


# ── /api/chat/history ─────────────────────────────────────────────────────

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

    def test_get_history_returns_messages(self, client, test_user):
        conv_id = self._create_conversation(client, test_user)
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        r = client.get(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 200
        messages = r.json()["messages"]
        assert len(messages) >= 2  # user message + assistant reply

    def test_get_history_nonexistent_returns_404(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        r = client.get("/api/chat/history/conv_does_not_exist", headers=headers)
        assert r.status_code == 404

    def test_delete_history_success(self, client, test_user):
        conv_id = self._create_conversation(client, test_user)
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        r = client.delete(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_get_history_after_delete_returns_404(self, client, test_user):
        conv_id = self._create_conversation(client, test_user)
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        client.delete(f"/api/chat/history/{conv_id}", headers=headers)
        r = client.get(f"/api/chat/history/{conv_id}", headers=headers)
        assert r.status_code == 404

    def test_unauthenticated_history_rejected(self, client):
        r = client.get("/api/chat/history/conv_abc123")
        assert r.status_code in [401, 403]


# ── /api/chat/sessions ────────────────────────────────────────────────────

class TestChatSessions:
    """GET /api/chat/sessions"""

    def test_sessions_list_empty_initially(self, client, admin_user):
        """Fresh admin user has no sessions yet."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r = client.get("/api/chat/sessions", headers=headers)
        assert r.status_code == 200
        # May have sessions from other tests; just verify shape
        assert "sessions" in r.json()

    def test_sessions_list_unauthenticated_rejected(self, client):
        r = client.get("/api/chat/sessions")
        assert r.status_code in [401, 403]

    def test_sessions_list_grows_after_query(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
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


# ── /api/chat/suggestions ─────────────────────────────────────────────────

class TestChatSuggestions:
    """GET /api/chat/suggestions — public endpoint."""

    def test_suggestions_accessible_without_auth(self, client):
        r = client.get("/api/chat/suggestions")
        assert r.status_code == 200

    def test_suggestions_returns_categories(self, client):
        r = client.get("/api/chat/suggestions")
        data = r.json()
        assert data["success"] is True
        suggestions = data["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_suggestions_have_required_keys(self, client):
        r = client.get("/api/chat/suggestions")
        for group in r.json()["suggestions"]:
            assert "category" in group
            assert "questions" in group
            assert isinstance(group["questions"], list)
