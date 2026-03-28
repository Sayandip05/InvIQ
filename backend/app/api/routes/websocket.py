"""
WebSocket route for real-time critical stock alerts.

Layer: API
Clients connect to /ws/alerts?token=<jwt> to receive push notifications.
Authentication is enforced via JWT token in query parameter before connection
is accepted, preventing unauthenticated access to sensitive stock alerts.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

from app.core.security import verify_access_token
from app.core.exceptions import AuthenticationError

logger = logging.getLogger("smart_inventory.websocket")

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages active WebSocket connections for broadcasting alerts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected (%d total)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(self.active_connections))

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        # Clean up dead connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


# Singleton manager — importable by inventory routes for broadcasting
manager = ConnectionManager()


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time stock alerts.

    Requires JWT token in query parameter: /ws/alerts?token=<access_token>
    Rejects unauthenticated or invalid token connections before accepting.

    Clients receive JSON messages when:
    - Stock drops below critical threshold after a transaction
    - Reorder points are triggered
    - System-wide alerts are issued
    """
    # ── Authentication: validate token BEFORE accepting connection ──────
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("WebSocket rejected: no token provided from %s", websocket.client)
        await websocket.close(code=4001, reason="Authentication token required")
        return

    try:
        payload = verify_access_token(token)
        username = payload.get("username", "unknown")
    except AuthenticationError:
        logger.warning("WebSocket rejected: invalid token from %s", websocket.client)
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # ── Connection accepted for authenticated user ──────────────────────
    await manager.connect(websocket)
    logger.info("WebSocket authenticated user '%s' connected", username)

    try:
        while True:
            # Keep connection alive — listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket user '%s' disconnected", username)

