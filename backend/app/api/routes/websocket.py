"""
WebSocket route for real-time critical stock alerts.

Layer: API
Clients connect to /ws/alerts to receive push notifications
when inventory transactions cause stock levels to drop below thresholds.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List

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
            self.active_connections.remove(conn)


# Singleton manager — importable by inventory routes for broadcasting
manager = ConnectionManager()


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time stock alerts.

    Clients connect here and receive JSON messages when:
    - Stock drops below critical threshold after a transaction
    - Reorder points are triggered
    - System-wide alerts are issued
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
