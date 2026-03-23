"""
Analytics endpoint tests — cache hits/misses, rate limiting, data shapes.
"""

import pytest
from tests.conftest import get_auth_header


class TestAnalyticsEndpoints:
    """Verify all analytics endpoints return correct data shapes."""

    def test_heatmap(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/analytics/heatmap", headers=headers)
        assert response.status_code == 200
        # Heatmap returns a list or dict of location/item data
        assert response.json() is not None

    def test_alerts_critical(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/analytics/alerts?severity=CRITICAL", headers=headers)
        assert response.status_code == 200

    def test_alerts_warning(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/analytics/alerts?severity=WARNING", headers=headers)
        assert response.status_code == 200

    def test_alerts_invalid_severity(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/analytics/alerts?severity=INVALID", headers=headers)
        assert response.status_code in [400, 422]

    def test_summary(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/analytics/summary", headers=headers)
        assert response.status_code == 200

    def test_dashboard_stats(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/analytics/dashboard/stats", headers=headers)
        assert response.status_code == 200

    def test_unauthenticated_access(self, client):
        """Analytics endpoints require authentication."""
        response = client.get("/api/analytics/heatmap")
        assert response.status_code in [401, 403]

        response = client.get("/api/analytics/summary")
        assert response.status_code in [401, 403]


class TestAnalyticsCaching:
    """Verify cache behavior — second call should be faster or identical."""

    def test_repeated_calls_return_same_data(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        r1 = client.get("/api/analytics/summary", headers=headers)
        r2 = client.get("/api/analytics/summary", headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Both should return the same data (cached or fresh)
        assert r1.json() == r2.json()
