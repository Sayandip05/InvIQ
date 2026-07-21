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
        with patch('app.application.cache_service.get_redis', return_value=None):
            result = cache_get("test_key")
            assert result is None

    def test_cache_set_no_redis(self):
        """Cache set without Redis should return False."""
        with patch('app.application.cache_service.get_redis', return_value=None):
            result = cache_set("test_key", {"data": "value"}, ttl=60)
            assert result is False

    def test_cache_delete_no_redis(self):
        """Cache delete without Redis should complete silently."""
        with patch('app.application.cache_service.get_redis', return_value=None):
            cache_delete("test_key")

    def test_cache_get_with_data(self):
        """Cache get with data should return cached value."""
        mock_client = Mock()
        mock_client.get.return_value = '{"cached": "data"}'
        with patch('app.application.cache_service.get_redis', return_value=mock_client):
            result = cache_get("test_key")
            assert result == {"cached": "data"}
            mock_client.get.assert_called_with("cache:test_key")

    def test_cache_set_success(self):
        """Cache set should return True on success."""
        mock_client = Mock()
        with patch('app.application.cache_service.get_redis', return_value=mock_client):
            result = cache_set("test_key", {"data": "value"}, ttl=60)
            assert result is True
            mock_client.setex.assert_called_with("cache:test_key", 60, '{"data": "value"}')

    def test_cache_invalidate_pattern(self):
        """Cache invalidate pattern should scan and delete matching keys."""
        mock_client = Mock()
        mock_client.scan.side_effect = [
            (1, ["cache:analytics:heatmap"]),
            (0, ["cache:analytics:summary"]),
        ]
        
        with patch('app.application.cache_service.get_redis', return_value=mock_client):
            deleted_count = cache_invalidate_pattern("analytics:*")
            assert deleted_count == 2
            assert mock_client.delete.call_count == 2
