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

# In-memory fallback (only for dev without Redis)
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

    # Always record in local memory store as well for instant local consistency
    _purge_expired_memory_tokens()
    expiry_epoch = time.time() + (expires_in_minutes * 60)
    _memory_blacklist[token] = expiry_epoch

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

    # Log warning if Redis is unavailable
    logger.warning(
        "⚠️ SECURITY WARNING: Redis is unavailable. Blacklisting token in process-local memory only. "
        "Revocation will not synchronize across other worker processes."
    )


def is_token_blacklisted(token: str) -> bool:
    """Check if a JWT has been blacklisted (logged out)."""
    # Check local memory first for sub-microsecond lookup
    _purge_expired_memory_tokens()
    if token in _memory_blacklist:
        return True

    r = get_redis()
    if r and is_redis_available():
        try:
            return r.exists(f"{_PREFIX}{token}") > 0
        except Exception as e:
            logger.warning("Redis blacklist read failed: %s", e)

    return False


def blacklist_refresh_token(token: str) -> None:
    """Blacklist a refresh token (longer TTL)."""
    blacklist_token(token, expires_in_minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)


# Single-use password reset JTI store
_RESET_PREFIX = "pw_reset_jti:"
_memory_reset_jtis: dict[str, float] = {}  # jti -> expiry_epoch (in-memory fallback)


def register_reset_jti(jti: str, ttl_seconds: int = 3600) -> None:
    """Store a password-reset JTI so we can single-use it."""
    r = get_redis()
    if r and is_redis_available():
        try:
            r.setex(f"{_RESET_PREFIX}{jti}", ttl_seconds, "1")
            return
        except Exception as e:
            logger.warning("Redis reset JTI write failed: %s", e)
    # Fallback to in-memory
    logger.warning(
        "⚠️ SECURITY WARNING: Redis is unavailable. Storing password reset JTI in process-local memory only. "
        "Single-use guarantee is not synchronized across worker processes."
    )
    _memory_reset_jtis[jti] = time.time() + ttl_seconds


def consume_reset_jti(jti: str) -> bool:
    """Check if a JTI exists and delete it atomically (single-use).

    Returns True if the JTI was found and consumed; False if already used or not found.
    """
    r = get_redis()
    if r and is_redis_available():
        try:
            key = f"{_RESET_PREFIX}{jti}"
            # Redis DEL returns number of keys deleted — atomic check-and-delete
            deleted = r.delete(key)
            return deleted > 0
        except Exception as e:
            logger.warning("Redis reset JTI consume failed: %s", e)
    # Fallback to in-memory
    logger.warning(
        "⚠️ SECURITY WARNING: Redis is unavailable. Consuming password reset JTI from process-local memory only."
    )
    now = time.time()
    # Purge expired entries
    expired = [k for k, exp in _memory_reset_jtis.items() if exp < now]
    for k in expired:
        _memory_reset_jtis.pop(k, None)
    if jti in _memory_reset_jtis:
        _memory_reset_jtis.pop(jti)
        return True
    return False

