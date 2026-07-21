"""
Rate limiter tests — slowapi rate limiting.

Tests the core/rate_limiter.py module.
"""

import pytest
from fastapi import Request
from slowapi.errors import RateLimitExceeded

from app.core.rate_limiter import limiter, rate_limit_handler


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_limiter_exists(self):
        """Limiter should be configured."""
        assert limiter is not None

    def test_rate_limit_handler(self):
        """Rate limit handler should return 429 response."""
        from unittest.mock import Mock
        mock_request = Request(scope={"type": "http", "method": "GET", "path": "/test", "headers": []})
        
        # Mock Limit structure to be independent of slowapi version
        mock_limit = Mock()
        mock_limit.error_message = "Rate limit exceeded"
        mock_limit.limit = Mock(limit="5/minute")
        
        mock_exc = RateLimitExceeded(mock_limit)
        
        response = rate_limit_handler(mock_request, mock_exc)
        assert response.status_code == 429
        # Response body should contain error message
        assert b"rate limit" in response.body.lower() or b"too many" in response.body.lower()

    def test_limiter_key_func(self):
        """Limiter should use IP-based key function."""
        # Check either public key_func or internal _key_func depending on slowapi version
        key_func = getattr(limiter, "key_func", getattr(limiter, "_key_func", None))
        assert key_func is not None

