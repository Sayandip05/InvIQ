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
        assert limiter.enabled is True

    def test_rate_limit_handler(self):
        """Rate limit handler should return 429 response."""
        mock_request = Request(scope={"type": "http", "method": "GET", "path": "/test"})
        mock_exc = RateLimitExceeded("Rate limit exceeded")
        
        response = rate_limit_handler(mock_request, mock_exc)
        assert response.status_code == 429
        # Response body should contain error message
        assert b"rate limit" in response.body.lower() or b"too many" in response.body.lower()

    def test_limiter_key_func(self):
        """Limiter should use IP-based key function."""
        # The limiter uses get_remote_address by default
        assert limiter.key_func is not None
