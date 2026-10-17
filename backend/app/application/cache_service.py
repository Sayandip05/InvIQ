"""
Cache Service — generic Redis caching with in-memory fallback for expensive queries.

Layer: Application

Features:
  - cache_get / cache_set / cache_delete / cache_invalidate_pattern
  - In-memory thread-safe fallback with TTL when Redis is disabled/unreachable
  - Pattern invalidation works across both Redis and in-memory cache
  - @cached(key, ttl) decorator for clean endpoint caching
  - SCAN-based key iteration (production-safe, non-blocking) with KEYS fallback

TTL reference:
  DASHBOARD_TTL   = 120s  (2 min)   — stats shown on dashboard
  ANALYTICS_TTL   = 300s  (5 min)   — deeper analytics queries
  REALTIME_TTL    = 30s   (30 sec)  — near-realtime feeds
"""

import fnmatch
import functools
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple
from app.infrastructure.cache.redis_client import get_redis

logger = logging.getLogger("smart_inventory.cache")

# TTL constants
DASHBOARD_TTL  = 120   # 2 minutes
ANALYTICS_TTL  = 300   # 5 minutes
REALTIME_TTL   = 30    # 30 seconds
DEFAULT_TTL    = 300

# Key prefix — separates our app keys from slowapi rate-limit keys in Redis
_PREFIX = "cache:"

# In-Memory Cache Fallback (thread-safe, TTL-aware)
_local_cache_lock = threading.Lock()
_local_cache: Dict[str, Tuple[float, Any]] = {}  # key -> (expiry_timestamp, value)


def _cleanup_local_cache_if_needed():
    """Remove expired items from in-memory cache."""
    now = time.time()
    expired_keys = [k for k, (exp, _) in _local_cache.items() if now > exp]
    for k in expired_keys:
        _local_cache.pop(k, None)


# Core primitives

def cache_get(key: str) -> Optional[Any]:
    """
    Retrieve a cached value by key.

    Uses high-performance L1 in-memory check first (sub-millisecond),
    falling back to L2 Redis on L1 miss and repopulating L1.
    """
    full_key = f"{_PREFIX}{key}"

    # 1. Fast L1 in-memory check (<0.1ms)
    with _local_cache_lock:
        item = _local_cache.get(full_key)
        if item is not None:
            expiry, val = item
            if time.time() < expiry:
                return val
            _local_cache.pop(full_key, None)

    # 2. L2 Redis check
    r = get_redis()
    if r:
        try:
            raw = r.get(full_key)
            if raw is not None:
                val = json.loads(raw)
                # Populate L1 cache for subsequent requests (default 30s local TTL)
                with _local_cache_lock:
                    _local_cache[full_key] = (time.time() + min(30, DEFAULT_TTL), val)
                return val
        except Exception as e:
            logger.debug("cache_get Redis failed key=%s: %s", key, e)

    return None



def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """
    Store a JSON-serializable value with TTL.

    Returns True if stored in Redis, False if Redis unavailable.
    Also updates in-memory fallback cache.
    """
    full_key = f"{_PREFIX}{key}"
    r = get_redis()
    stored_in_redis = False
    if r:
        try:
            r.setex(full_key, ttl, json.dumps(value, default=str))
            stored_in_redis = True
        except Exception as e:
            logger.debug("cache_set Redis failed key=%s: %s", key, e)

    # Always keep in-memory cache in sync
    with _local_cache_lock:
        _cleanup_local_cache_if_needed()
        _local_cache[full_key] = (time.time() + ttl, value)

    return stored_in_redis



def cache_delete(key: str) -> None:
    """Delete a specific cache entry from both Redis and in-memory cache."""
    full_key = f"{_PREFIX}{key}"
    r = get_redis()
    if r:
        try:
            r.delete(full_key)
        except Exception as e:
            logger.debug("cache_delete Redis failed key=%s: %s", key, e)

    with _local_cache_lock:
        _local_cache.pop(full_key, None)


def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching a glob pattern.

    Invalidates both Redis and in-memory cache.
    Uses SCAN (not KEYS) where supported, with graceful fallback.
    Returns total number of keys invalidated.

    Example:
        cache_invalidate_pattern("analytics:*")
        cache_invalidate_pattern("ref:*")
    """
    full_pattern = f"{_PREFIX}{pattern}"
    deleted = 0

    # 1. Invalidate Redis
    r = get_redis()
    if r:
        try:
            # Try SCAN first (non-blocking)
            cursor = 0
            while True:
                scan_res = r.scan(cursor=cursor, match=full_pattern, count=100)
                if isinstance(scan_res, tuple) and len(scan_res) == 2:
                    cursor, keys = scan_res
                elif isinstance(scan_res, list):
                    keys = scan_res
                    cursor = 0
                else:
                    break

                if keys:
                    r.delete(*keys)
                    deleted += len(keys)
                if cursor == 0 or not cursor:
                    break
        except Exception as e:
            logger.debug("Redis scan invalidation failed, trying fallback: %s", e)
            try:
                # Fallback to keys matching
                keys = r.keys(full_pattern)
                if keys:
                    r.delete(*keys)
                    deleted += len(keys)
            except Exception as e2:
                logger.debug("Redis keys invalidation fallback failed: %s", e2)

    # 2. Invalidate In-memory local cache
    local_deleted = 0
    with _local_cache_lock:
        matched_keys = [k for k in _local_cache if fnmatch.fnmatch(k, full_pattern)]
        for k in matched_keys:
            _local_cache.pop(k, None)
            local_deleted += 1

    total_deleted = deleted if r else local_deleted
    if total_deleted:
        logger.debug("Cache invalidated %d keys matching '%s'", total_deleted, pattern)
    return total_deleted



# @cached decorator

def cached(key: str, ttl: int = DEFAULT_TTL):
    """
    Decorator to cache a function's return value in Redis / local memory.

    Usage:
        @cached("analytics:dashboard_stats", ttl=DASHBOARD_TTL)
        def get_dashboard_stats(db):
            ...

    The decorated function is called only on cache miss.
    Result must be JSON-serializable.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cached_value = cache_get(key)
            if cached_value is not None:
                logger.debug("Cache HIT key=%s", key)
                return cached_value

            logger.debug("Cache MISS key=%s — calling function", key)
            result = func(*args, **kwargs)
            cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator
