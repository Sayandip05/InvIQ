"""
Request logging middleware.

Logs every HTTP request with:
  - Method + path
  - Response status code
  - Processing time in ms
  - A unique X-Request-ID for correlation

Example log line:
  2026-03-10 09:50:00 | INFO     | smart_inventory.request  | POST /api/requisition/create → 200 (42ms) [req-abc123]
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("smart_inventory.request")


class RequestLoggerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Attach request ID so downstream code can use it
        request.state.request_id = request_id

        response: Response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000)
        status = response.status_code
        method = request.method
        path = request.url.path

        # Skip noisy health-check / favicon / docs requests
        if path in ("/health", "/favicon.ico", "/docs", "/openapi.json", "/redoc"):
            response.headers["X-Request-ID"] = request_id
            return response

        log_fn = logger.info if status < 400 else logger.warning
        log_fn(
            "%s %s → %s (%dms) [req-%s]",
            method,
            path,
            status,
            duration_ms,
            request_id,
        )

        # Add headers for debugging
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms}ms"

        return response
