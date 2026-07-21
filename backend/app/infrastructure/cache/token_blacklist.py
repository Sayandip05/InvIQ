"""
JWT Token Blacklist — invalidate tokens on logout.

Layer: Infrastructure (Cache)
Uses Redis SET with TTL matching token expiry.
Falls back to in-memory set when Redis is unavailable.
"""

import logging
from datetime import timedelta
from app.infrastructure.cache.redis_client import get_redis, is_redis_available
from app.core.config import settings

logger = logging.getLogger("smart_inventory.token_blacklist")

import time

# ── In-memory fallback (only for dev without Redis) ────────────────────────
# Stores token -> expiration epoch timestamp to prevent unbounded leaks.
_memory_blacklist: dict[str, float] = {}

# Redis key prefix
_PREFIX = "blacklist:"


def _purge_expired_memory_tokens() -> None:
    """Remove expired tokens from in-memory fallback store to prevent memory leaks."""
    now = time.time()
    expired = [t for t, exp in _memory_blacklist.items() if exp < now]
    for t in expired:
        _memory_blacklist.pop(t, None)



def blacklist_token(token: str, expires_in_minutes: int = None) -> None:
    """
    Add a JWT to the blacklist.

    Args:
        token: The JWT string to blacklist
        expires_in_minutes: TTL for the blacklist entry (defaults to access token expiry)
    """
    if expires_in_minutes is None:
        expires_in_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    r = get_redis()
    if r and is_redis_available():
        try:
            ttl_seconds = int(timedelta(minutes=expires_in_minutes).total_seconds())
            r.setex(
                f"{_PREFIX}{token}",
                ttl_seconds,
                "1",
            )
            return
        except Exception as e:
            logger.warning("Redis blacklist write failed: %s", e)

    # Fallback to in-memory
    _purge_expired_memory_tokens()
    expiry_epoch = time.time() + (expires_in_minutes * 60)
    _memory_blacklist[token] = expiry_epoch
    logger.debug("Token blacklisted (in-memory fallback)")


def is_token_blacklisted(token: str) -> bool:
    """Check if a JWT has been blacklisted (logged out)."""
    r = get_redis()
    if r and is_redis_available():
        try:
            return r.exists(f"{_PREFIX}{token}") > 0
        except Exception as e:
            logger.warning("Redis blacklist read failed: %s", e)

    # Fallback to in-memory
    _purge_expired_memory_tokens()
    return token in _memory_blacklist


def blacklist_refresh_token(token: str) -> None:
    """Blacklist a refresh token (longer TTL)."""
    blacklist_token(token, expires_in_minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
