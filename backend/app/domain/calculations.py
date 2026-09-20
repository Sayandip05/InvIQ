"""
Domain calculations — pure business logic for inventory management.

All functions are stateless and free of infrastructure concerns.
They may be used by any application service, GraphQL resolver, or test.

─────────────────────────────────────────────────────────────
Exports (stable public API)
─────────────────────────────────────────────────────────────
calculate_reorder_quantity()   — legacy positional-arg API (kept for compat)
classify_stock_health()        — preferred: uses StockStatus / value objects
get_health_color()             — maps StockStatus → hex color string
format_stock_item()            — formats ORM result row → API response dict
                                 (note: knows ORM row shape; prefer service
                                  layer formatters for new callers)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.value_objects import (
    DAYS_REMAINING_INFINITE,
    ReorderPolicy,
    StockStatus,
    StockThresholds,
)


# ---------------------------------------------------------------------------
# Reorder quantity
# ---------------------------------------------------------------------------

def calculate_reorder_quantity(
    avg_daily_usage: float,
    lead_time_days: int,
    current_stock: int,
    safety_factor: float = StockThresholds.DEFAULT_SAFETY_FACTOR,
) -> int:
    """
    Calculate the recommended reorder quantity.

    Formula: max(0, (daily_usage × lead_time × safety_factor) − current_stock)
    """
    policy = ReorderPolicy(
        avg_daily_usage=float(avg_daily_usage or 0.0),
        lead_time_days=int(lead_time_days or 2),
        safety_factor=float(safety_factor or 2.0),
    )
    return policy.recommended_quantity(int(current_stock or 0))



# ---------------------------------------------------------------------------
# Stock health classification
# ---------------------------------------------------------------------------

def classify_stock_health(days_remaining: Optional[float]) -> StockStatus:
    """
    Classify a stock item as CRITICAL / WARNING / HEALTHY.

    Single pure-domain entry point for health classification.
    The SQL query in analytics_repo.py derives its CASE expression thresholds
    from StockThresholds — both implementations stay in sync.

    Args:
        days_remaining: current_stock / avg_daily_usage, or None if no data.

    Returns:
        StockStatus enum variant.

    Examples:
        >>> classify_stock_health(1.5)
        <StockStatus.CRITICAL: 'CRITICAL'>
        >>> classify_stock_health(5.0)
        <StockStatus.WARNING: 'WARNING'>
        >>> classify_stock_health(None)
        <StockStatus.HEALTHY: 'HEALTHY'>
    """
    return StockStatus.from_days(days_remaining)


# ---------------------------------------------------------------------------
# Color mapping
# ---------------------------------------------------------------------------

def get_health_color(status: str) -> str:
    """
    Return the UI hex color for a given health status string.

    Accepts both plain strings ('CRITICAL') and StockStatus enum values.
    Falls back to gray (#6b7280) for any unrecognised value so the UI
    always receives a valid color.

    Args:
        status: One of 'CRITICAL', 'WARNING', 'HEALTHY', or any string.

    Returns:
        Hex color string (e.g. '#ef4444').
    """
    try:
        return StockStatus(status).color
    except ValueError:
        return "#6b7280"  # unknown / UNKNOWN → gray


# ---------------------------------------------------------------------------
# Stock item formatter
# ---------------------------------------------------------------------------

def format_stock_item(item: Any) -> Dict:
    """
    Format a stock health ORM result row into an API response dict.

    Note: This function understands the shape of the SQLAlchemy named-tuple
    returned by analytics_repo.get_latest_stock_health(). New callers that need
    a plain-dict output should prefer building a dict directly in the
    service layer to avoid this domain→infrastructure coupling.

    Args:
        item: Named-tuple row from get_latest_stock_health().

    Returns:
        Dict ready for JSON serialisation.
    """
    days = (
        round(item.days_remaining, 1)
        if item.days_remaining != DAYS_REMAINING_INFINITE
        else None
    )
    return {
        "location_id":    item.location_id,
        "location_name":  item.location_name,
        "location_type":  item.location_type,
        "item_id":        item.item_id,
        "item_name":      item.item_name,
        "category":       item.category,
        "current_stock":  item.current_stock,
        "avg_daily_usage": round(item.avg_daily_usage, 2) if item.avg_daily_usage else 0,
        "days_remaining": days,
        "health_status":  item.health_status,
        "lead_time_days": item.lead_time_days,
        "last_updated":   str(item.last_updated),
        "color":          get_health_color(item.health_status),
    }
