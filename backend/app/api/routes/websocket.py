"""
WebSocket route for real-time critical stock alerts.

Layer: API
Clients connect to /ws/alerts?token=<jwt> to receive push notifications.
Authentication is enforced via JWT token in query parameter before connection
is accepted, preventing unauthenticated access to sensitive stock alerts.

Pub/Sub design:
  - inventory_service.py (sync) calls queue_websocket_alert(alert)
  - If Redis is available: publishes to channel "inviq:ws:alerts"
  - WebSocket handler (async) subscribes to the channel and broadcasts
  - If Redis is unavailable: falls back to in-process list (single-worker only)
"""

import asyncio
import json
import logging
import threading
import secrets
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_access_token
from app.core.exceptions import AuthenticationError
from app.core.dependencies import get_current_user, get_db
from app.infrastructure.database.models import User
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.cache.token_blacklist import is_token_blacklisted

logger = logging.getLogger("smart_inventory.websocket")

router = APIRouter(tags=["WebSocket"])

# ── Redis pub/sub channel name ────────────────────────────────────────────────
_ALERT_CHANNEL = "inviq:ws:alerts"

# ── Single-use WebSocket Tickets (30-second TTL) ──────────────────────────────
_tickets_lock = threading.Lock()
_ws_tickets: Dict[str, Dict[str, Any]] = {}


def create_ws_ticket(user: User) -> str:
    """Generate a cryptographically secure, single-use, 30s WebSocket ticket."""
    ticket = secrets.token_urlsafe(32)
    exp = time.time() + 30.0
    ticket_payload = {
        "user_id": user.id,
        "username": user.username,
        "org_id": user.org_id,
        "role": user.role,
        "exp": exp,
    }

    # Store in Redis if available
    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = get_redis()
        if r:
            r.setex(f"ws_ticket:{ticket}", 30, json.dumps(ticket_payload))
    except Exception:
        pass

    with _tickets_lock:
        _ws_tickets[ticket] = ticket_payload
    return ticket


def validate_and_consume_ws_ticket(ticket: str) -> Optional[Dict[str, Any]]:
    """Validate and immediately consume (delete) a single-use WebSocket ticket from all stores."""
    result = None

    # 1. Check & delete from Redis
    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = get_redis()
        if r:
            data = r.get(f"ws_ticket:{ticket}")
            if data:
                r.delete(f"ws_ticket:{ticket}")
                result = json.loads(data)
    except Exception:
        pass

    # 2. Always delete from in-memory store as well
    now = time.time()
    with _tickets_lock:
        expired = [k for k, v in _ws_tickets.items() if v["exp"] < now]
        for k in expired:
            _ws_tickets.pop(k, None)

        mem_data = _ws_tickets.pop(ticket, None)
        if result is None and mem_data and mem_data["exp"] >= now:
            result = mem_data

    return result



@router.post("/api/websocket/ticket", response_model=dict)
@router.post("/ws/ticket", response_model=dict)
def issue_websocket_ticket(current_user: User = Depends(get_current_user)):
    """
    Issue a short-lived (30s), single-use ticket for WebSocket authentication.
    Prevents token leakage in browser query strings, access logs, and proxy logs.
    """
    ticket = create_ws_ticket(current_user)
    return {
        "success": True,
        "ticket": ticket,
        "expires_in": 30,
    }


class ConnectionManager:
    """Manages active WebSocket connections, isolated strictly per organization."""

    def __init__(self):
        # {WebSocket: {"org_id": Optional[int], "username": str, "role": str}}
        self.active_connections: dict = {}

    async def connect(
        self,
        websocket: WebSocket,
        org_id: Optional[int] = None,
        username: str = "unknown",
        role: str = "staff",
    ):
        await websocket.accept()
        self.active_connections[websocket] = {
            "org_id": org_id,
            "username": username,
            "role": role,
        }
        logger.info(
            "WebSocket client '%s' (org=%s, role=%s) connected (%d total)",
            username, org_id, role, len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket):
        meta = self.active_connections.pop(websocket, None)
        username = meta.get("username", "unknown") if meta else "unknown"
        logger.info(
            "WebSocket client '%s' disconnected (%d remaining)",
            username, len(self.active_connections),
        )

    async def broadcast_to_org(self, org_id: Optional[int], message: dict):
        """
        Send a message only to clients belonging to the given org.
        - If org_id is provided: sends ONLY to clients in that organization.
        - If org_id is None: unassigned tenant events are DROPPED entirely to prevent data leaks.
        """
        if org_id is None:
            logger.debug("Dropping unassigned WebSocket event (org_id=None)")
            return

        disconnected = []
        for connection, meta in self.active_connections.items():
            client_org = meta.get("org_id")
            client_role = meta.get("role")

            if client_org != org_id:
                continue

            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.pop(conn, None)

    async def broadcast(self, message: dict):
        """Broadcast message to ALL active connections unconditionally."""
        disconnected = []
        for connection in list(self.active_connections.keys()):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.pop(conn, None)



# Singleton manager
manager = ConnectionManager()


# ── In-process fallback queue (single-worker / no-Redis only) ─────────────────
_alerts_lock = threading.Lock()
_pending_alerts: list = []
pending_alerts = _pending_alerts  # Backwards compatibility alias



def queue_websocket_alert(alert: dict, org_id: Optional[int] = None) -> None:
    """
    Queue a real-time alert for delivery to WebSocket clients of the given org.

    org_id must be provided for tenant-scoped events.

    Routing priority:
      1. In-process queue → immediate local socket consumption (<1ms)
      2. Redis Pub/Sub   → cross-process, production-safe, multi-worker
    """
    import time
    if "_published_at_ms" not in alert:
        alert["_published_at_ms"] = round(time.time() * 1000, 2)
    if "org_id" not in alert:
        alert["org_id"] = org_id

    with _alerts_lock:
        _pending_alerts.append(alert)

    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = get_redis()
        if r:
            r.publish(_ALERT_CHANNEL, json.dumps(alert, default=str))
            if org_id is not None:
                org_channel = f"inviq:events:org:{org_id}"
                r.publish(org_channel, json.dumps(alert, default=str))
    except Exception as exc:
        logger.debug("Redis publish failed: %s", exc)


def publish_domain_event(topic: str, org_id: Optional[int], payload: dict) -> None:
    """
    Publish a standardized multi-tenant domain event to WebSocket clients and Redis channels.
    Topics: 'stock.low', 'expiry.critical', 'requisition.approved', 'import.completed'
    """
    event = {
        "event_topic": topic,
        "type": topic.replace(".", "_"),
        "org_id": org_id,
        "payload": payload,
        "timestamp": time.time(),
    }
    queue_websocket_alert(event, org_id=org_id)





async def start_redis_subscriber():
    """
    Long-running async task: subscribe to Redis pub/sub channel and
    broadcast messages to all connected WebSocket clients.

    Call this from the FastAPI lifespan so it runs for the server lifetime.
    Gracefully exits (with a warning) when Redis is not configured.
    """
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        url = settings.REDIS_URL
        if not url and settings.UPSTASH_REDIS_REST_URL:
            # Convert Upstash HTTPS REST URL → rediss:// for asyncio client
            url = (
                settings.UPSTASH_REDIS_REST_URL
                .replace("https://", "rediss://")
                .replace("http://", "redis://")
            )

        if not url:
            logger.info("Redis not configured — WebSocket alerts use in-process queue (single-worker only)")
            return

        client = aioredis.from_url(url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(_ALERT_CHANNEL)
        logger.info("WebSocket Redis subscriber ready → channel: %s", _ALERT_CHANNEL)

        async for message in pubsub.listen():
            if message and message.get("type") == "message":
                try:
                    alert = json.loads(message["data"])
                    org_id_for_alert = alert.get("org_id")  # may be None for global broadcasts
                    await manager.broadcast_to_org(org_id_for_alert, alert)
                except Exception as exc:
                    logger.warning("Failed to broadcast Redis alert: %s", exc)

    except ImportError:
        logger.warning("redis[asyncio] not installed — WebSocket using in-process queue fallback")
    except Exception as exc:
        logger.warning("Redis subscriber error — WebSocket using in-process queue fallback: %s", exc)


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time stock alerts.

    Supports:
    1. Single-use ticket (Recommended): /ws/alerts?ticket=<single_use_ticket>
    2. JWT token (Legacy fallback with revocation check): /ws/alerts?token=<access_token>
    
    Rejects unauthenticated, revoked, disabled, or invalid connections BEFORE accepting.
    """
    ticket = websocket.query_params.get("ticket")
    token = websocket.query_params.get("token")

    if not ticket and not token:
        logger.warning("WebSocket rejected: no ticket or token from %s", websocket.client)
        await websocket.close(code=4001, reason="Authentication ticket or token required")
        raise AuthenticationError("Authentication ticket or token required")

    username = "unknown"
    user_id = None

    # 1. Single-use ticket flow
    if ticket:
        ticket_data = validate_and_consume_ws_ticket(ticket)
        if not ticket_data:
            logger.warning("WebSocket rejected: invalid or expired ticket from %s", websocket.client)
            await websocket.close(code=4001, reason="Invalid or expired ticket")
            raise AuthenticationError("Invalid or expired ticket")
        user_id = ticket_data.get("user_id")
        username = ticket_data.get("username", "unknown")

    # 2. Token fallback flow
    elif token:
        if is_token_blacklisted(token):
            logger.warning("WebSocket rejected: blacklisted token from %s", websocket.client)
            await websocket.close(code=4001, reason="Token has been revoked")
            raise AuthenticationError("Token has been revoked")

        try:
            payload = verify_access_token(token)
            user_id = payload.get("sub")
            username = payload.get("username", "unknown")
        except AuthenticationError:
            logger.warning("WebSocket rejected: invalid token from %s", websocket.client)
            await websocket.close(code=4001, reason="Invalid or expired token")
            raise

    # Extract org_id and role from whichever auth path succeeded
    org_id_for_ws: Optional[int] = None
    role_for_ws: str = "staff"

    if ticket and ticket_data:
        org_id_for_ws = ticket_data.get("org_id")
        role_for_ws = ticket_data.get("role", "staff")
    elif token and payload:
        org_id_for_ws = payload.get("org_id")
        role_for_ws = payload.get("role", "staff")

    if user_id:
        try:
            from app.infrastructure.database.connection import SessionLocal
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user and not user.is_active:
                    logger.warning("WebSocket rejected: user %s disabled", username)
                    await websocket.close(code=4001, reason="User account disabled")
                    raise AuthenticationError("User account disabled")
                if user:
                    org_id_for_ws = user.org_id
                    role_for_ws = user.role
        except AuthenticationError:
            raise
        except Exception:
            pass


    await manager.connect(
        websocket,
        org_id=org_id_for_ws,
        username=username,
        role=role_for_ws,
    )
    logger.info("WebSocket user '%s' (org=%s, role=%s) connected", username, org_id_for_ws, role_for_ws)


    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})

            # Drain in-process fallback queue (no-op when Redis is active)
            with _alerts_lock:
                alerts_to_send = list(_pending_alerts)
                _pending_alerts.clear()

            for alert in alerts_to_send:
                org_id_for_alert = alert.get("org_id")
                await manager.broadcast_to_org(org_id_for_alert, alert)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket user '%s' disconnected", username)

