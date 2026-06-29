"""
Strawberry GraphQL resolvers for the InvIQ analytics layer.

Design decisions
─────────────────
* All resolvers delegate to the **existing** AnalyticsService / cache_service /
  queries.py — no new database logic lives here.
* Redis caching reuses the same cache keys as the REST endpoints so a warm
  cache is shared between REST and GraphQL callers.
* Role-aware field masking:
    - Guest (None) and Vendor  → avg_daily_usage / days_remaining / lead_time_days = None
    - Manager / Admin / Super Admin → full values
  This prevents unauthenticated visitors from extracting operational forecasting
  data while still allowing them to browse stock status.
"""

from __future__ import annotations
import logging
from typing import Optional

import strawberry
from strawberry.types import Info

from app.application.analytics_service import AnalyticsService
from app.application.cache_service import (
    cache_get,
    cache_set,
    ANALYTICS_TTL,
    DASHBOARD_TTL,
)
from app.core.security import ROLE_HIERARCHY
from app.infrastructure.database.queries import get_latest_stock_health

from app.api.graphql.types import (
    AlertItem,
    AlertsResponse,
    CategoryBreakdown,
    CategoryDistribution,
    DashboardStats,
    HeatmapData,
    HealthSummary,
    LocationStock,
    LowStockItem,
    OverviewStats,
    StatusDistribution,
    StockHealthItem,
    SummaryData,
)

logger = logging.getLogger("smart_inventory.graphql")

# Roles that may receive the privileged forecasting fields.
_PRIVILEGED_ROLES = {"manager", "admin", "super_admin"}


def _is_privileged(user) -> bool:
    """Return True when the caller is manager-level or above."""
    if user is None:
        return False
    return user.role in _PRIVILEGED_ROLES


def _to_stock_health_item(raw, privileged: bool) -> StockHealthItem:
    """
    Map a raw SQLAlchemy result row (from get_latest_stock_health) to the
    StockHealthItem Strawberry type, applying role-based field masking.
    """
    from app.domain.calculations import get_health_color

    avg_usage = round(float(raw.avg_daily_usage), 2) if raw.avg_daily_usage else 0.0
    days_rem = (
        round(float(raw.days_remaining), 1)
        if raw.days_remaining and raw.days_remaining != 999
        else None
    )

    return StockHealthItem(
        location_id=raw.location_id,
        location_name=raw.location_name,
        location_type=raw.location_type,
        item_id=raw.item_id,
        item_name=raw.item_name,
        category=raw.category,
        current_stock=raw.current_stock,
        health_status=raw.health_status,
        color=get_health_color(raw.health_status),
        last_updated=str(raw.last_updated),
        avg_daily_usage=avg_usage if privileged else None,
        days_remaining=days_rem if privileged else None,
        lead_time_days=raw.lead_time_days if privileged else None,
    )


def _to_alert_item(raw_dict: dict, privileged: bool) -> AlertItem:
    """Map a dict from AnalyticsService.get_alerts to AlertItem."""
    return AlertItem(
        location_id=raw_dict["location_id"],
        location_name=raw_dict["location_name"],
        location_type=raw_dict["location_type"],
        item_id=raw_dict["item_id"],
        item_name=raw_dict["item_name"],
        category=raw_dict["category"],
        current_stock=raw_dict["current_stock"],
        health_status=raw_dict["health_status"],
        color=raw_dict["color"],
        last_updated=raw_dict["last_updated"],
        recommended_reorder=raw_dict.get("recommended_reorder", 0),
        avg_daily_usage=raw_dict.get("avg_daily_usage") if privileged else None,
        days_remaining=raw_dict.get("days_remaining") if privileged else None,
        lead_time_days=raw_dict.get("lead_time_days") if privileged else None,
    )


# ── Query class ──────────────────────────────────────────────────────────


@strawberry.type
class Query:

    @strawberry.field(
        description=(
            "High-level dashboard metrics: category distribution, top low-stock "
            "items, location stock totals, and health-status distribution. "
            "Results are cached for 2 minutes (shared with REST /api/analytics/dashboard/stats)."
        )
    )
    def dashboard_stats(self, info: Info) -> DashboardStats:
        ctx = info.context
        db = ctx["db"]

        cache_key = "analytics:dashboard_stats"
        cached = cache_get(cache_key)

        if cached is None:
            raw = AnalyticsService.get_dashboard_stats(db)
            cache_set(cache_key, raw, ttl=DASHBOARD_TTL)
            data = raw["data"]
        else:
            data = cached["data"]

        return DashboardStats(
            category_distribution=[
                CategoryDistribution(name=d["name"], value=d["value"])
                for d in data["category_distribution"]
            ],
            low_stock_items=[
                LowStockItem(
                    name=d["name"],
                    stock=d["stock"],
                    min_stock=d["min_stock"],
                    shortage=d["shortage"],
                )
                for d in data["low_stock_items"]
            ],
            location_stock=[
                LocationStock(name=d["name"], value=d["value"])
                for d in data["location_stock"]
            ],
            status_distribution=[
                StatusDistribution(name=d["name"], value=d["value"], color=d["color"])
                for d in data["status_distribution"]
            ],
        )

    @strawberry.field(
        description=(
            "Inventory heatmap: a location × item matrix of stock health. "
            "The `matrix` field is a raw JSON array (list[list[{stock, status, daysRemaining}]]). "
            "`details` is the flat list of StockHealthItem records that populate the matrix. "
            "Cached 5 minutes."
        )
    )
    def heatmap(self, info: Info) -> HeatmapData:
        ctx = info.context
        db = ctx["db"]
        user = ctx["user"]
        privileged = _is_privileged(user)

        cache_key = "analytics:heatmap"
        cached = cache_get(cache_key)

        if cached is None:
            raw = AnalyticsService.get_heatmap(db)
            cache_set(cache_key, raw, ttl=ANALYTICS_TTL)
            data = raw["data"]
        else:
            data = cached["data"]

        # Re-fetch the raw DB rows to build typed detail objects with masking.
        # The cache holds the REST dict format; we read the live rows for type safety.
        # This is a lightweight re-query since the DB result is already cached in Redis
        # for other callers — only the Strawberry mapping runs here.
        raw_rows = get_latest_stock_health(db)
        details = [_to_stock_health_item(r, privileged) for r in raw_rows]

        return HeatmapData(
            locations=data["locations"],
            items=data["items"],
            matrix=data["matrix"],   # JSON scalar — unchanged
            details=details,
        )

    @strawberry.field(
        description=(
            "List of items with critical or warning stock levels. "
            "severity: 'CRITICAL' (default) or 'WARNING'. "
            "WARNING includes both WARNING and CRITICAL items. "
            "Cached 5 minutes per severity level."
        )
    )
    def alerts(
        self,
        info: Info,
        severity: str = "CRITICAL",
    ) -> AlertsResponse:
        if severity not in ("CRITICAL", "WARNING"):
            raise ValueError("severity must be 'CRITICAL' or 'WARNING'")

        ctx = info.context
        db = ctx["db"]
        user = ctx["user"]
        privileged = _is_privileged(user)

        cache_key = f"analytics:alerts:{severity}"
        cached = cache_get(cache_key)

        if cached is None:
            raw = AnalyticsService.get_alerts(db, severity)
            cache_set(cache_key, raw, ttl=ANALYTICS_TTL)
            data = raw["data"]
        else:
            data = cached["data"]

        return AlertsResponse(
            severity=data["severity"],
            count=data["count"],
            alerts=[_to_alert_item(a, privileged) for a in data["alerts"]],
        )

    @strawberry.field(
        description=(
            "Aggregate inventory summary: overview counts, health breakdown "
            "(critical / warning / healthy), and per-category stats. Cached 5 minutes."
        )
    )
    def summary(self, info: Info) -> SummaryData:
        ctx = info.context
        db = ctx["db"]

        cache_key = "analytics:summary"
        cached = cache_get(cache_key)

        if cached is None:
            raw = AnalyticsService.get_summary(db)
            cache_set(cache_key, raw, ttl=ANALYTICS_TTL)
            data = raw["data"]
        else:
            data = cached["data"]

        overview_d = data["overview"]
        health_d = data["health_summary"]
        categories_d = data["categories"]

        categories = [
            CategoryBreakdown(
                name=cat,
                total=stats["total"],
                critical=stats["critical"],
                warning=stats["warning"],
                healthy=stats["healthy"],
            )
            for cat, stats in categories_d.items()
        ]

        return SummaryData(
            overview=OverviewStats(
                total_locations=overview_d["total_locations"],
                total_items=overview_d["total_items"],
                total_records=overview_d["total_records"],
            ),
            health_summary=HealthSummary(
                critical=health_d["critical"],
                warning=health_d["warning"],
                healthy=health_d["healthy"],
            ),
            categories=categories,
        )

    @strawberry.field(
        description=(
            "Flexible stock-health query with optional filters. "
            "Unlike the REST endpoint, you can request exactly the fields you need "
            "and filter server-side by location name, item name, or health status. "
            "Privileged fields (avgDailyUsage, daysRemaining, leadTimeDays) are null "
            "for Guest / Vendor callers. Not cached — designed for ad-hoc reporting."
        )
    )
    def stock_health(
        self,
        info: Info,
        location: str = "",
        item: str = "",
        status_filter: str = "",
    ) -> list[StockHealthItem]:
        """
        Flexible per-item stock health query.

        Args:
            location: Filter by location name (case-insensitive substring match)
            item: Filter by item name (case-insensitive substring match)
            status_filter: Filter by health status — "" | "CRITICAL" | "WARNING" | "HEALTHY"
        """
        ctx = info.context
        db = ctx["db"]
        user = ctx["user"]
        privileged = _is_privileged(user)

        if status_filter and status_filter not in ("CRITICAL", "WARNING", "HEALTHY"):
            raise ValueError("statusFilter must be '', 'CRITICAL', 'WARNING', or 'HEALTHY'")

        rows = get_latest_stock_health(db)

        if location:
            rows = [r for r in rows if location.lower() in r.location_name.lower()]
        if item:
            rows = [r for r in rows if item.lower() in r.item_name.lower()]
        if status_filter:
            rows = [r for r in rows if r.health_status == status_filter]

        return [_to_stock_health_item(r, privileged) for r in rows]
