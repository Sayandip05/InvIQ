"""
Analytics service tests — dashboard and reporting logic.

Tests the application/analytics_service.py module.
"""

import pytest
from unittest.mock import Mock, patch

from app.application.analytics_service import AnalyticsService
from app.core.exceptions import AppException


class TestAnalyticsService:
    """Test analytics service business logic."""

    def test_get_heatmap_empty_data(self, db):
        """Get heatmap with no data should return empty structure."""
        result = AnalyticsService.get_heatmap(db)
        assert result["success"] is True
        assert "data" in result
        assert "locations" in result["data"]
        assert "items" in result["data"]
        assert "matrix" in result["data"]

    def test_get_alerts_critical(self, db):
        """Get critical alerts should return formatted alerts."""
        result = AnalyticsService.get_alerts(db, severity="CRITICAL")
        assert result["success"] is True
        assert result["data"]["severity"] == "CRITICAL"
        assert "alerts" in result["data"]

    def test_get_alerts_warning(self, db):
        """Get warning alerts should return formatted alerts."""
        result = AnalyticsService.get_alerts(db, severity="WARNING")
        assert result["success"] is True
        assert result["data"]["severity"] == "WARNING"

    def test_get_summary(self, db):
        """Get summary should return overview stats."""
        result = AnalyticsService.get_summary(db)
        assert result["success"] is True
        assert "overview" in result["data"]
        assert "health_summary" in result["data"]
        assert "categories" in result["data"]

    def test_get_dashboard_stats(self, db):
        """Get dashboard stats should return chart data."""
        result = AnalyticsService.get_dashboard_stats(db)
        assert result["success"] is True
        assert "category_distribution" in result["data"]
        assert "low_stock_items" in result["data"]
        assert "location_stock" in result["data"]
        assert "status_distribution" in result["data"]

    def test_get_heatmap_with_data(self, db):
        """Get heatmap with data should format correctly."""
        from app.infrastructure.database.models import Location, Item, InventoryTransaction
        from datetime import date
        
        location = Location(name="Test Location", type="clinic", region="Test")
        item = Item(name="Test Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)
        
        tx = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 9),
            opening_stock=0,
            received=100,
            issued=0,
            closing_stock=100,
            entered_by="testuser",
        )
        db.add(tx)
        db.commit()
        
        result = AnalyticsService.get_heatmap(db)
        assert result["success"] is True
        assert len(result["data"]["details"]) > 0
