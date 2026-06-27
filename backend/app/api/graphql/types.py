"""
Strawberry GraphQL type definitions for the InvIQ analytics layer.

All types mirror the shape produced by AnalyticsService so that the
resolvers are a thin mapping layer — no new business logic lives here.

Role-aware fields are annotated Optional[...] with a note explaining
that resolvers set them to None for Guest / Vendor callers.
"""

from __future__ import annotations
import strawberry
from strawberry.scalars import JSON
from typing import Optional


# ── Stock health / alert types ────────────────────────────────────────────


@strawberry.type
class StockHealthItem:
    """
    Stock health record for a single item at a single location.

    Fields marked *privileged* are set to None for Guest / Vendor callers;
    Manager, Admin, Super Admin receive the full values.
    """

    location_id: int
    location_name: str
    location_type: str
    item_id: int
    item_name: str
    category: str
    current_stock: int
    health_status: str   # "CRITICAL" | "WARNING" | "HEALTHY"
    color: str           # hex colour for the UI
    last_updated: str

    # Privileged — null for Guest / Vendor
    avg_daily_usage: Optional[float]
    days_remaining: Optional[float]
    lead_time_days: Optional[int]


@strawberry.type
class AlertItem:
    """A single critical / warning stock alert with a reorder suggestion."""

    location_id: int
    location_name: str
    location_type: str
    item_id: int
    item_name: str
    category: str
    current_stock: int
    health_status: str
    color: str
    last_updated: str
    recommended_reorder: int

    # Privileged — null for Guest / Vendor
    avg_daily_usage: Optional[float]
    days_remaining: Optional[float]
    lead_time_days: Optional[int]


# ── Alerts response ───────────────────────────────────────────────────────


@strawberry.type
class AlertsResponse:
    severity: str
    count: int
    alerts: list[AlertItem]


# ── Heatmap types ─────────────────────────────────────────────────────────


@strawberry.type
class HeatmapCell:
    """One cell in the inventory heatmap matrix (location × item)."""

    stock: int
    status: str                     # "CRITICAL" | "WARNING" | "HEALTHY" | "UNKNOWN"
    days_remaining: Optional[float]  # null when no usage data or item not tracked


@strawberry.type
class HeatmapData:
    """Full heatmap grid: locations (rows) × items (columns)."""

    locations: list[str]
    items: list[str]
    matrix: JSON                             # list[list[{stock, status, daysRemaining}]]
    details: list[StockHealthItem]


# ── Summary types ─────────────────────────────────────────────────────────


@strawberry.type
class OverviewStats:
    total_locations: int
    total_items: int
    total_records: int


@strawberry.type
class HealthSummary:
    critical: int
    warning: int
    healthy: int


@strawberry.type
class CategoryBreakdown:
    """Per-category stock counts."""

    name: str
    total: int
    critical: int
    warning: int
    healthy: int


@strawberry.type
class SummaryData:
    overview: OverviewStats
    health_summary: HealthSummary
    categories: list[CategoryBreakdown]


# ── Dashboard stats types ─────────────────────────────────────────────────


@strawberry.type
class CategoryDistribution:
    """Item count per category (for the pie / donut chart)."""

    name: str
    value: int


@strawberry.type
class LowStockItem:
    """An item below its min_stock threshold (top-5 worst)."""

    name: str
    stock: int
    min_stock: int
    shortage: int


@strawberry.type
class LocationStock:
    """Total stock quantity per location (for the bar chart)."""

    name: str
    value: int


@strawberry.type
class StatusDistribution:
    """Count of items per health status with a UI colour."""

    name: str    # "CRITICAL" | "WARNING" | "HEALTHY"
    value: int
    color: str   # "#ef4444" | "#f59e0b" | "#22c55e"


@strawberry.type
class DashboardStats:
    category_distribution: list[CategoryDistribution]
    low_stock_items: list[LowStockItem]
    location_stock: list[LocationStock]
    status_distribution: list[StatusDistribution]
