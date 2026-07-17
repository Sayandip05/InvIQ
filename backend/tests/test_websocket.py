"""
WebSocket endpoint tests.

Tests /ws/alerts authentication gating and connection lifecycle.
Uses Starlette's WebSocketTestSession via FastAPI TestClient.
"""

import pytest
from tests.conftest import get_auth_header


class TestWebSocketAuth:
    """Authentication enforcement before connection is accepted."""

    def test_no_token_closes_connection(self, client):
        """Connecting without a token must be rejected (code 4001)."""
        with pytest.raises(Exception):
            # TestClient raises when WS is closed before sending
            with client.websocket_connect("/ws/alerts") as ws:
                ws.receive_json()

    def test_invalid_token_closes_connection(self, client):
        """An invalid / expired token must be rejected."""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/alerts?token=bad.token.here") as ws:
                ws.receive_json()

    def test_valid_token_accepted(self, client, test_user):
        """A valid JWT allows the connection to open."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        token = headers["Authorization"].split(" ")[1]

        with client.websocket_connect(f"/ws/alerts?token={token}") as ws:
            # Connection is open — server is listening
            ws.send_text("ping")
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_admin_token_accepted(self, client, admin_user):
        """Admin JWT also allows connection."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        token = headers["Authorization"].split(" ")[1]

        with client.websocket_connect(f"/ws/alerts?token={token}") as ws:
            ws.send_text("ping")
            data = ws.receive_json()
            assert data == {"type": "pong"}


class TestWebSocketPingPong:
    """Keepalive ping / pong protocol."""

    def _open(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        token = headers["Authorization"].split(" ")[1]
        return client.websocket_connect(f"/ws/alerts?token={token}")

    def test_ping_returns_pong(self, client, test_user):
        with self._open(client, test_user) as ws:
            ws.send_text("ping")
            msg = ws.receive_json()
            assert msg["type"] == "pong"

    def test_multiple_pings(self, client, test_user):
        """Multiple consecutive pings must each receive a pong."""
        with self._open(client, test_user) as ws:
            for _ in range(3):
                ws.send_text("ping")
                msg = ws.receive_json()
                assert msg["type"] == "pong"


class TestWebSocketBroadcast:
    """Pending alerts are drained and broadcast to connected clients."""

    def _open(self, client, test_user):
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        token = headers["Authorization"].split(" ")[1]
        return client.websocket_connect(f"/ws/alerts?token={token}")

    def test_pending_alert_is_broadcast_on_ping(self, client, test_user):
        """An alert appended to pending_alerts is sent to the client on next ping."""
        from app.api.routes.websocket import pending_alerts

        alert_payload = {
            "type": "stock_alert",
            "item": "Paracetamol",
            "status": "CRITICAL",
        }
        pending_alerts.append(alert_payload)

        with self._open(client, test_user) as ws:
            ws.send_text("ping")
            # First message could be the alert OR the pong depending on ordering.
            # Drain up to 2 messages and check the alert appears.
            messages = []
            try:
                messages.append(ws.receive_json())
                messages.append(ws.receive_json())
            except Exception:
                pass

            payloads = [m for m in messages if m.get("type") == "stock_alert"]
            assert payloads, f"Expected stock_alert in {messages}"

        # Clean up in case the broadcast didn't drain it
        pending_alerts.clear()

    def test_pending_alerts_cleared_after_broadcast(self, client, test_user):
        """Alerts list is empty after they are dispatched."""
        from app.api.routes.websocket import pending_alerts

        pending_alerts.append({"type": "test_event"})
        with self._open(client, test_user) as ws:
            ws.send_text("ping")
            try:
                ws.receive_json()
                ws.receive_json()
            except Exception:
                pass

        assert len(pending_alerts) == 0


class TestConnectionManager:
    """Unit tests for ConnectionManager.connect / disconnect / broadcast."""

    @pytest.mark.asyncio
    async def test_connect_increments_count(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.api.routes.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws)
        assert len(mgr.active_connections) == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        from unittest.mock import AsyncMock
        from app.api.routes.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws)
        mgr.disconnect(ws)
        assert len(mgr.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        from unittest.mock import AsyncMock
        from app.api.routes.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws1, ws2 = AsyncMock(), AsyncMock()
        await mgr.connect(ws1)
        await mgr.connect(ws2)

        msg = {"type": "alert", "data": "test"}
        await mgr.broadcast(msg)

        ws1.send_json.assert_called_once_with(msg)
        ws2.send_json.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        """A connection that raises during send is cleaned up."""
        from unittest.mock import AsyncMock
        from app.api.routes.websocket import ConnectionManager

        mgr = ConnectionManager()
        dead_ws = AsyncMock()
        dead_ws.send_json.side_effect = Exception("closed")
        good_ws = AsyncMock()

        await mgr.connect(dead_ws)
        await mgr.connect(good_ws)

        await mgr.broadcast({"type": "ping"})

        assert dead_ws not in mgr.active_connections
        assert good_ws in mgr.active_connections
