"""
Domain calculations tests — business logic for stock calculations.

Tests the domain/calculations.py module.
"""

import pytest
from unittest.mock import Mock

from app.domain.calculations import (
    calculate_reorder_quantity,
    classify_stock_health,
    get_health_color,
    format_stock_item,
)
from app.domain.value_objects import (
    StockStatus,
    StockThresholds,
    ReorderPolicy,
    DAYS_REMAINING_INFINITE,
)


class TestReorderCalculations:
    """Test reorder quantity calculation logic."""

    def test_calculate_reorder_quantity_basic(self):
        """Basic reorder calculation should work."""
        qty = calculate_reorder_quantity(
            avg_daily_usage=10.0,
            lead_time_days=7,
            current_stock=50,
            safety_factor=2.0,
        )
        # (10 * 7 * 2) - 50 = 140 - 50 = 90
        assert qty == 90

    def test_calculate_reorder_quantity_zero_usage(self):
        """Zero daily usage should return 0."""
        qty = calculate_reorder_quantity(
            avg_daily_usage=0.0,
            lead_time_days=7,
            current_stock=50,
        )
        assert qty == 0

    def test_calculate_reorder_quantity_negative_usage(self):
        """Negative daily usage should return 0."""
        qty = calculate_reorder_quantity(
            avg_daily_usage=-5.0,
            lead_time_days=7,
            current_stock=50,
        )
        assert qty == 0

    def test_calculate_reorder_quantity_high_stock(self):
        """High current stock should return 0 (no reorder needed)."""
        qty = calculate_reorder_quantity(
            avg_daily_usage=5.0,
            lead_time_days=7,
            current_stock=200,
            safety_factor=2.0,
        )
        # (5 * 7 * 2) - 200 = 70 - 200 = -130 → max(0, -130) = 0
        assert qty == 0

    def test_calculate_reorder_quantity_custom_safety_factor(self):
        """Custom safety factor should affect calculation."""
        qty = calculate_reorder_quantity(
            avg_daily_usage=10.0,
            lead_time_days=5,
            current_stock=0,
            safety_factor=3.0,
        )
        # (10 * 5 * 3) - 0 = 150
        assert qty == 150

    def test_calculate_reorder_quantity_fractional_result(self):
        """Fractional result should be rounded to int."""
        qty = calculate_reorder_quantity(
            avg_daily_usage=7.5,
            lead_time_days=6,
            current_stock=10,
            safety_factor=1.5,
        )
        # (7.5 * 6 * 1.5) - 10 = 67.5 - 10 = 57.5 → int(57.5) = 57
        assert qty == 57


class TestHealthColor:
    """Test health status color mapping."""

    def test_get_health_color_critical(self):
        """Critical status should return red."""
        color = get_health_color("CRITICAL")
        assert color == "#ef4444"

    def test_get_health_color_warning(self):
        """Warning status should return orange."""
        color = get_health_color("WARNING")
        assert color == "#f59e0b"

    def test_get_health_color_healthy(self):
        """Healthy status should return green."""
        color = get_health_color("HEALTHY")
        assert color == "#10b981"

    def test_get_health_color_unknown(self):
        """Unknown status should return gray."""
        color = get_health_color("UNKNOWN")
        assert color == "#6b7280"

    def test_get_health_color_case_sensitive(self):
        """Color mapping should be case-sensitive."""
        color = get_health_color("critical")  # lowercase
        assert color == "#6b7280"  # default gray


class TestFormatStockItem:
    """Test stock item formatting for API responses."""

    def test_format_stock_item_complete(self):
        """Format stock item with all fields."""
        mock_item = Mock()
        mock_item.location_id = 1
        mock_item.location_name = "Main Warehouse"
        mock_item.location_type = "warehouse"
        mock_item.item_id = 10
        mock_item.item_name = "Paracetamol"
        mock_item.category = "medicine"
        mock_item.current_stock = 150
        mock_item.avg_daily_usage = 12.5
        mock_item.days_remaining = 12.0
        mock_item.health_status = "HEALTHY"
        mock_item.lead_time_days = 7
        mock_item.last_updated = "2026-04-09"

        result = format_stock_item(mock_item)

        assert result["location_id"] == 1
        assert result["location_name"] == "Main Warehouse"
        assert result["item_name"] == "Paracetamol"
        assert result["current_stock"] == 150
        assert result["avg_daily_usage"] == 12.5
        assert result["days_remaining"] == 12.0
        assert result["health_status"] == "HEALTHY"
        assert result["color"] == "#10b981"

    def test_format_stock_item_critical(self):
        """Format critical stock item."""
        mock_item = Mock()
        mock_item.location_id = 2
        mock_item.location_name = "Clinic A"
        mock_item.location_type = "clinic"
        mock_item.item_id = 20
        mock_item.item_name = "Insulin"
        mock_item.category = "medicine"
        mock_item.current_stock = 5
        mock_item.avg_daily_usage = 10.0
        mock_item.days_remaining = 0.5
        mock_item.health_status = "CRITICAL"
        mock_item.lead_time_days = 14
        mock_item.last_updated = "2026-04-09"

        result = format_stock_item(mock_item)

        assert result["health_status"] == "CRITICAL"
        assert result["color"] == "#ef4444"
        assert result["days_remaining"] == 0.5

    def test_format_stock_item_no_usage(self):
        """Format stock item with no usage data."""
        mock_item = Mock()
        mock_item.location_id = 3
        mock_item.location_name = "Storage"
        mock_item.location_type = "warehouse"
        mock_item.item_id = 30
        mock_item.item_name = "Bandages"
        mock_item.category = "supplies"
        mock_item.current_stock = 200
        mock_item.avg_daily_usage = None
        mock_item.days_remaining = 999
        mock_item.health_status = "HEALTHY"
        mock_item.lead_time_days = 5
        mock_item.last_updated = "2026-04-09"

        result = format_stock_item(mock_item)

        assert result["avg_daily_usage"] == 0
        assert result["days_remaining"] is None  # 999 → None

    def test_format_stock_item_rounds_usage(self):
        """Format stock item should round avg_daily_usage to 2 decimals."""
        mock_item = Mock()
        mock_item.location_id = 4
        mock_item.location_name = "Pharmacy"
        mock_item.location_type = "clinic"
        mock_item.item_id = 40
        mock_item.item_name = "Aspirin"
        mock_item.category = "medicine"
        mock_item.current_stock = 100
        mock_item.avg_daily_usage = 7.123456
        mock_item.days_remaining = 14.2857
        mock_item.health_status = "WARNING"
        mock_item.lead_time_days = 7
        mock_item.last_updated = "2026-04-09"

        result = format_stock_item(mock_item)

        assert result["avg_daily_usage"] == 7.12
        assert result["days_remaining"] == 14.3


# ---------------------------------------------------------------------------
# StockStatus
# ---------------------------------------------------------------------------

class TestStockStatus:
    """Test StockStatus enum — classification and color mapping."""

    def test_from_days_critical(self):
        assert StockStatus.from_days(0.0) == StockStatus.CRITICAL
        assert StockStatus.from_days(2.9) == StockStatus.CRITICAL

    def test_from_days_boundary_critical(self):
        """Exactly at the CRITICAL boundary should still be WARNING."""
        assert StockStatus.from_days(StockThresholds.CRITICAL_DAYS) == StockStatus.WARNING

    def test_from_days_warning(self):
        assert StockStatus.from_days(3.0) == StockStatus.WARNING
        assert StockStatus.from_days(6.9) == StockStatus.WARNING

    def test_from_days_boundary_warning(self):
        """Exactly at the WARNING boundary should be HEALTHY."""
        assert StockStatus.from_days(StockThresholds.WARNING_DAYS) == StockStatus.HEALTHY

    def test_from_days_healthy(self):
        assert StockStatus.from_days(7.0) == StockStatus.HEALTHY
        assert StockStatus.from_days(100.0) == StockStatus.HEALTHY

    def test_from_days_none_is_healthy(self):
        """No usage data → cannot classify as critical, treat as HEALTHY."""
        assert StockStatus.from_days(None) == StockStatus.HEALTHY

    def test_color_critical(self):
        assert StockStatus.CRITICAL.color == "#ef4444"

    def test_color_warning(self):
        assert StockStatus.WARNING.color == "#f59e0b"

    def test_color_healthy(self):
        assert StockStatus.HEALTHY.color == "#10b981"

    def test_str_equality(self):
        """StockStatus inherits str so it equals its string value."""
        assert StockStatus.CRITICAL == "CRITICAL"
        assert StockStatus.WARNING == "WARNING"
        assert StockStatus.HEALTHY == "HEALTHY"


# ---------------------------------------------------------------------------
# StockThresholds
# ---------------------------------------------------------------------------

class TestStockThresholds:
    """Verify threshold constants are correct and consistent."""

    def test_critical_days_value(self):
        assert StockThresholds.CRITICAL_DAYS == 3.0

    def test_warning_days_value(self):
        assert StockThresholds.WARNING_DAYS == 7.0

    def test_critical_less_than_warning(self):
        assert StockThresholds.CRITICAL_DAYS < StockThresholds.WARNING_DAYS

    def test_usage_window_days(self):
        assert StockThresholds.USAGE_WINDOW_DAYS == 7

    def test_default_safety_factor(self):
        assert StockThresholds.DEFAULT_SAFETY_FACTOR == 2.0


# ---------------------------------------------------------------------------
# ReorderPolicy
# ---------------------------------------------------------------------------

class TestReorderPolicy:
    """Test the value-object API for reorder quantity calculation."""

    def test_recommended_quantity_basic(self):
        policy = ReorderPolicy(avg_daily_usage=10.0, lead_time_days=7)
        # (10 * 7 * 2.0) - 50 = 90
        assert policy.recommended_quantity(current_stock=50) == 90

    def test_recommended_quantity_zero_usage(self):
        policy = ReorderPolicy(avg_daily_usage=0.0, lead_time_days=7)
        assert policy.recommended_quantity(current_stock=0) == 0

    def test_recommended_quantity_negative_usage(self):
        policy = ReorderPolicy(avg_daily_usage=-1.0, lead_time_days=7)
        assert policy.recommended_quantity(current_stock=0) == 0

    def test_recommended_quantity_no_reorder_needed(self):
        policy = ReorderPolicy(avg_daily_usage=5.0, lead_time_days=7)
        # (5 * 7 * 2) = 70 < 200 → 0
        assert policy.recommended_quantity(current_stock=200) == 0

    def test_recommended_quantity_custom_safety_factor(self):
        policy = ReorderPolicy(avg_daily_usage=10.0, lead_time_days=5, safety_factor=3.0)
        # (10 * 5 * 3) = 150
        assert policy.recommended_quantity(current_stock=0) == 150

    def test_immutability(self):
        policy = ReorderPolicy(avg_daily_usage=10.0, lead_time_days=7)
        with pytest.raises((AttributeError, TypeError)):
            policy.avg_daily_usage = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# classify_stock_health
# ---------------------------------------------------------------------------

class TestClassifyStockHealth:
    """Test the pure classify_stock_health() domain function."""

    def test_critical(self):
        assert classify_stock_health(1.0) == StockStatus.CRITICAL
        assert classify_stock_health(0.0) == StockStatus.CRITICAL

    def test_warning(self):
        assert classify_stock_health(3.0) == StockStatus.WARNING
        assert classify_stock_health(6.99) == StockStatus.WARNING

    def test_healthy(self):
        assert classify_stock_health(7.0) == StockStatus.HEALTHY
        assert classify_stock_health(30.0) == StockStatus.HEALTHY

    def test_none_is_healthy(self):
        assert classify_stock_health(None) == StockStatus.HEALTHY

    def test_returns_stock_status_enum(self):
        result = classify_stock_health(5.0)
        assert isinstance(result, StockStatus)
