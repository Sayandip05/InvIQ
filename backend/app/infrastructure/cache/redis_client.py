"""
Upstash Redis client — REST HTTP backend with graceful fallback.

Layer: Infrastructure
Uses the upstash-redis Python SDK which talks to Upstash over HTTPS (REST),
making it compatible with serverless / edge environments without a persistent
TCP connection.

When Redis is unavailable the app continues without caching — all callers
check is_redis_available() or receive None from get_redis().

Key namespaces used by this app:
  cache:*       → analytics / dashboard response cache (TTL 2-5 min)
  blacklist:*   → JWT token blacklist (TTL = token expiry)
  lockout:*     → login attempt counters (TTL = lockout window)
  ratelimit:*   → managed by slowapi automatically
"""

import logging
import json
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger("smart_inventory.redis")

# ── Module-level singleton ───────────────────────────────────────────────────
_redis_client = None          # upstash_redis.Redis instance or None
_redis_available: bool = False
_import_failed: bool = False  # True once upstash_redis import fails — prevents retry spam


def _build_client():
    """Instantiate an Upstash Redis client from env settings."""
    from upstash_redis import Redis  # lazy import — only fails if pkg missing
    return Redis(
        url=settings.UPSTASH_REDIS_REST_URL,
        token=settings.UPSTASH_REDIS_REST_TOKEN,
    )


def get_redis():
    """
    Get the singleton Upstash Redis client.
    Returns None if Redis is unavailable or not configured.
    """
    global _redis_client, _redis_available, _import_failed

    # Short-circuit: package was already confirmed missing — don't retry.
    if _import_failed:
        return None

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
        logger.info(
            "UPSTASH_REDIS_REST_URL / TOKEN not set — running without Redis (in-memory fallback active)"
        )
        _redis_available = False
        return None

    try:
        _redis_client = _build_client()
        # Ping to verify connectivity
        _redis_client.ping()
        _redis_available = True
        logger.info(
            "Upstash Redis connected → %s",
            settings.UPSTASH_REDIS_REST_URL,
        )
        return _redis_client
    except ImportError as e:
        # Package missing — log once and never retry
        logger.warning("Upstash Redis package not available — running without cache: %s", e)
        _import_failed = True
        _redis_available = False
        _redis_client = None
        return None
    except Exception as e:
        logger.warning("Upstash Redis connection failed — running without cache: %s", e)
        _redis_available = False
        _redis_client = None
        return None


def is_redis_available() -> bool:
    """Ping Upstash Redis to confirm it's still healthy."""
    global _redis_available
    if _redis_available and _redis_client:
        try:
            _redis_client.ping()
            return True
        except Exception:
            _redis_available = False
            logger.warning("Upstash Redis health check failed — marking unavailable")
    return False


def close_redis() -> None:
    """Reset singleton state (Upstash REST client has no persistent pool to close)."""
    global _redis_client, _redis_available
    _redis_client = None
    _redis_available = False
    logger.info("Upstash Redis client reference cleared")


# ── Typed helpers (used by cache_service, token_blacklist, login_attempts) ───

def redis_get_json(key: str) -> Optional[Any]:
    """Get a JSON-deserialized value from Redis. Returns None on any failure."""
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        if raw is None:
            return None
        # upstash-redis already decodes strings; parse if it's a JSON string
        if isinstance(raw, str):
            return json.loads(raw)
        return raw
    except Exception as e:
        logger.debug("redis_get_json failed key=%s: %s", key, e)
        return None


def redis_set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    """Set a JSON-serialized value with TTL. Returns True on success."""
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.debug("redis_set_json failed key=%s: %s", key, e)
        return False


def redis_delete(key: str) -> bool:
    """Delete a key. Returns True on success."""
    r = get_redis()
    if not r:
        return False
    try:
        r.delete(key)
        return True
    except Exception as e:
        logger.debug("redis_delete failed key=%s: %s", key, e)
        return False


def redis_increment(key: str, ttl_seconds: int) -> int:
    """
    Atomic increment with TTL (used for login attempt counters).
    Sets TTL only on first creation. Returns new count.
    """
    r = get_redis()
    if not r:
        return 0
    try:
        count = r.incr(key)
        # Only set TTL when the key is freshly created (count == 1)
        if count == 1:
            r.expire(key, ttl_seconds)
        return count
    except Exception as e:
        logger.debug("redis_increment failed key=%s: %s", key, e)
        return 0


def redis_get_int(key: str) -> int:
    """Get an integer counter value. Returns 0 if missing or unavailable."""
    r = get_redis()
    if not r:
        return 0
    try:
        val = r.get(key)
        return int(val) if val is not None else 0
    except Exception as e:
        logger.debug("redis_get_int failed key=%s: %s", key, e)
        return 0
