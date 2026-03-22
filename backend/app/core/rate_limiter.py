"""
Rate Limiter configuration — slowapi integration.

Layer: Core
Provides configurable rate limiting with Redis backend (falls back to in-memory).
"""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

logger = logging.getLogger("smart_inventory.rate_limit")


def _get_key_func():
    """Use client IP as rate limit key."""
    return get_remote_address


def _get_storage_uri() -> str | None:
    """Use Redis for distributed rate limiting if available, else in-memory."""
    if settings.REDIS_URL:
        logger.info("Rate limiter: using Redis backend")
        return settings.REDIS_URL
    logger.info("Rate limiter: using in-memory backend (single-process only)")
    return "memory://"


limiter = Limiter(
    key_func=_get_key_func(),
    storage_uri=_get_storage_uri(),
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    strategy="fixed-window",
)
