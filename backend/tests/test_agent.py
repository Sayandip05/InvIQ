"""
Agent & Chat endpoint tests — mock the LLM, verify tool triggers.
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import get_auth_header


class TestChatEndpoints:
    """Verify the chat API works with mocked LLM responses."""

    def test_chat_requires_auth(self, client):
        """Chat endpoint requires authentication."""
        response = client.post("/api/chat/", json={"message": "hello"})
        assert response.status_code in [401, 403]

    @patch("app.application.agent_service.ChatGroq")
    def test_chat_sends_message(self, mock_groq, client, test_user):
        """Chat endpoint accepts messages and returns a response."""
        # Mock the LLM response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Here is your inventory overview."
        mock_llm.invoke.return_value = mock_response
        mock_groq.return_value = mock_llm

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/chat/",
            json={"message": "Show me inventory overview"},
            headers=headers,
        )
        # Should return 200 regardless of LLM mock status
        assert response.status_code == 200

    def test_chat_empty_message(self, client, test_user):
        """Chat endpoint handles empty messages gracefully."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/chat/",
            json={"message": ""},
            headers=headers,
        )
        # Should either reject or handle empty input
        assert response.status_code in [200, 400, 422]


class TestChatSessions:
    """Verify chat session management."""

    def test_get_chat_history(self, client, test_user):
        """User can retrieve their chat history."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/chat/history", headers=headers)
        assert response.status_code == 200

    def test_chat_history_requires_auth(self, client):
        """Chat history requires authentication."""
        response = client.get("/api/chat/history")
        assert response.status_code in [401, 403]


class TestAgentTools:
    """Verify the agent tool functions return valid data."""

    def test_inventory_overview_tool(self, db):
        """Test inventory_overview tool returns data."""
        from app.application.agent_tools import inventory_overview
        result = inventory_overview.invoke({"input": ""})
        assert isinstance(result, str)

    def test_critical_items_tool(self, db):
        """Test critical_items tool returns data."""
        from app.application.agent_tools import critical_items
        result = critical_items.invoke({"input": ""})
        assert isinstance(result, str)

    def test_stock_health_tool(self, db):
        """Test stock_health tool returns data."""
        from app.application.agent_tools import stock_health
        result = stock_health.invoke({"input": ""})
        assert isinstance(result, str)
