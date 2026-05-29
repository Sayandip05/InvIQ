"""
Request logging middleware.

Implemented as a pure ASGI middleware (NOT BaseHTTPMiddleware) to avoid
a documented Starlette incompatibility where BaseHTTPMiddleware intercepts
WebSocket upgrade connections and prevents the handshake from completing.

Logs every HTTP request with:
  - Method + path
  - Response status code
  - Processing time in ms
  - A unique X-Request-ID for correlation

WebSocket connections (scope["type"] == "websocket") are passed through
completely untouched.

Example log line:
  2026-03-10 09:50:00 | INFO | smart_inventory.request | POST /api/chat/query -> 200 (42ms) [req-abc123]
"""

import logging
import time
import uuid
from typing import Callable

logger = logging.getLogger("smart_inventory.request")

# Paths that generate too much noise — skip logging them
_SILENT_PATHS = frozenset({"/health", "/favicon.ico", "/docs", "/openapi.json", "/redoc"})


class RequestLoggerMiddleware:
    """
    Pure ASGI middleware for structured HTTP request logging.

    Bypasses WebSocket connections entirely so the WS handshake is never
    interrupted — fixing the silent connection-drop bug caused by the old
    BaseHTTPMiddleware approach.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        # Pass WebSocket and lifespan scopes straight through — do NOT touch them.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()
        path = scope.get("path", "")
        method = scope.get("method", "")

        # Wrap the send callable to capture the response status code.
        status_code: list[int] = [0]

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
                # Inject correlation headers
                headers = dict(message.get("headers", []))
                headers[b"x-request-id"] = request_id.encode()
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # Skip noisy internal paths
        if path in _SILENT_PATHS:
            return

        duration_ms = round((time.perf_counter() - start_time) * 1000)
        status = status_code[0]
        log_fn = logger.info if status < 400 else logger.warning
        log_fn(
            "%s %s -> %s (%dms) [req-%s]",
            method,
            path,
            status,
            duration_ms,
            request_id,
        )
