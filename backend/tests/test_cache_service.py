"""
Cache service tests — Redis caching layer.

Tests the application/cache_service.py module.
"""

import pytest
from unittest.mock import Mock, patch

from app.application.cache_service import (
    cache_get,
    cache_set,
    cache_delete,
    cache_invalidate_pattern,
)


class TestCacheService:
    """Test cache service operations."""

    def test_cache_get_no_redis(self):
        """Cache get without Redis should return None."""
        with patch('app.application.cache_service.redis_get_json', return_value=None):
            result = cache_get("test_key")
            assert result is None

    def test_cache_set_no_redis(self):
        """Cache set without Redis should return False."""
        with patch('app.application.cache_service.redis_set_json', return_value=False):
            result = cache_set("test_key", {"data": "value"}, ttl=60)
            assert result is False

    def test_cache_delete_no_redis(self):
        """Cache delete without Redis should return False."""
        with patch('app.application.cache_service.redis_delete', return_value=False):
            result = cache_delete("test_key")
            assert result is False

    def test_cache_get_with_data(self):
        """Cache get with data should return cached value."""
        with patch('app.application.cache_service.redis_get_json', return_value={"cached": "data"}):
            result = cache_get("test_key")
            assert result == {"cached": "data"}

    def test_cache_set_success(self):
        """Cache set should return True on success."""
        with patch('app.application.cache_service.redis_set_json', return_value=True):
            result = cache_set("test_key", {"data": "value"}, ttl=60)
            assert result is True

    def test_cache_invalidate_pattern(self):
        """Cache invalidate pattern should delete matching keys."""
        with patch('app.application.cache_service.get_redis') as mock_redis:
            mock_client = Mock()
            mock_client.keys.return_value = ["analytics:heatmap", "analytics:summary"]
            mock_redis.return_value = mock_client
            
            cache_invalidate_pattern("analytics:*")
            mock_client.delete.assert_called()
