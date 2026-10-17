"""
Login Attempt Cache — distributed brute-force protection.

Layer: Infrastructure (Cache)

Tracks failed login attempts per username in Redis with a sliding TTL.
When Redis is unavailable falls back to an in-memory dict (per-process only,
sufficient for single-worker dev). In production with Redis every worker
shares the same counter, so lockout is truly distributed.

Key schema:
  lockout:{username}  →  integer (attempt count), TTL = LOCKOUT_DURATION_MINUTES
"""

import logging
from datetime import timedelta
from app.infrastructure.cache.redis_client import (
    redis_increment,
    redis_get_int,
    redis_delete,
    get_redis,
)
from app.core.config import settings

logger = logging.getLogger("smart_inventory.login_attempts")

_LOCKOUT_TTL_SECONDS = settings.LOCKOUT_DURATION_MINUTES * 60
_PREFIX = "lockout:"

# In-memory fallback (dev without Redis)
_mem_attempts: dict[str, int] = {}


def record_failed_attempt(username: str) -> int:
    """
    Increment the failed login counter for a username.

    Uses Redis pipeline for atomic INCR + EXPIRE.
    Returns the new total attempt count.
    """
    key = f"{_PREFIX}{username}"

    if get_redis():
        count = redis_increment(key, _LOCKOUT_TTL_SECONDS)
        logger.debug("Failed login attempt #%d for '%s' (Redis)", count, username)
        return count

    # In-memory fallback
    logger.warning(
        "⚠️ SECURITY WARNING: Redis is unavailable. Tracking failed login attempts for '%s' in process-local memory only. "
        "Brute-force lockout counters are not synchronized across workers.",
        username,
    )
    _mem_attempts[username] = _mem_attempts.get(username, 0) + 1
    count = _mem_attempts[username]
    return count


def get_attempt_count(username: str) -> int:
    """Return the current failed attempt count for a username (0 if none)."""
    key = f"{_PREFIX}{username}"

    if get_redis():
        return redis_get_int(key)

    return _mem_attempts.get(username, 0)


def reset_attempts(username: str) -> None:
    """Clear the failed attempt counter after a successful login."""
    key = f"{_PREFIX}{username}"

    if get_redis():
        redis_delete(key)
    else:
        _mem_attempts.pop(username, None)

    logger.debug("Login attempt counter reset for '%s'", username)


def is_locked_out(username: str) -> bool:
    """
    Check if a username is currently locked out.

    Returns True if attempt count >= MAX_LOGIN_ATTEMPTS.
    NOTE: The TTL-based expiry in Redis handles the lockout window automatically.
    """
    return get_attempt_count(username) >= settings.MAX_LOGIN_ATTEMPTS
