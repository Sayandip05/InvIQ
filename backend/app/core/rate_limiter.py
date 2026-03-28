"""
Rate Limiter — slowapi integration with Redis backend.

Layer: Core

Strategy: moving-window (more accurate than fixed-window — no burst at window reset).
Backend: Redis (distributed across workers). Falls back to in-memory (dev only).

Key functions:
  get_remote_address  → identifies by client IP (for public endpoints like /login)
  get_user_id         → identifies by JWT user ID (for authenticated endpoints)

Rate limit tiers (matching Opencode security requirements):
  AUTH_LIMIT          → "5/minute"    login brute-force protection
  REGISTER_LIMIT      → "3/minute"    registration spam prevention
  CHAT_LIMIT          → "20/minute"   LLM call protection (expensive)
  TRANSACTION_LIMIT   → "30/minute"   write operation protection
  ANALYTICS_LIMIT     → "30/minute"   read-heavy analytics
  DEFAULT_LIMIT       → "60/minute"   catch-all
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

logger = logging.getLogger("smart_inventory.rate_limit")


# ── Key functions ─────────────────────────────────────────────────────────

def get_user_id_or_ip(request: Request) -> str:
    """
    Rate limit key for authenticated endpoints.

    Uses JWT user ID when available (extracted from the already-decoded
    user stored by get_current_user), falls back to client IP.

    This means:
    - Authenticated users: limited per account (fair across shared IPs/NAT)
    - Unauthenticated: limited per IP (for login, register, etc.)
    """
    # Try to get user id from request state (set by get_current_user dependency)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return get_remote_address(request)


def _get_storage_uri() -> str:
    """Use Redis for distributed rate limiting if available, else in-memory."""
    if settings.REDIS_URL:
        logger.info("Rate limiter: using Redis backend (distributed)")
        return settings.REDIS_URL
    logger.warning(
        "Rate limiter: REDIS_URL not set — using in-memory (not shared across workers)"
    )
    return "memory://"


# ── Limiter instance ──────────────────────────────────────────────────────

limiter = Limiter(
    key_func=get_remote_address,        # default: per-IP
    storage_uri=_get_storage_uri(),
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    strategy="moving-window",           # accurate, no burst at window reset
)


# ── Pre-defined limit strings ─────────────────────────────────────────────
# Import these in routes instead of hardcoding strings

AUTH_LIMIT         = settings.RATE_LIMIT_AUTH           # "5/minute"
REGISTER_LIMIT     = "3/minute"
CHAT_LIMIT         = "20/minute"
TRANSACTION_LIMIT  = "30/minute"
REQUISITION_LIMIT  = "20/minute"
ANALYTICS_LIMIT    = "30/minute"
REFRESH_LIMIT      = "10/minute"


# ── 429 error handler ────────────────────────────────────────────────────

def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom 429 response with Retry-After header.

    Add to FastAPI app:
        from slowapi.errors import RateLimitExceeded
        app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    """
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={
            "success": False,
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. Please retry after {retry_after} seconds.",
            "retry_after": retry_after,
        },
    )
