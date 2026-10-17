"""
Analytics Repository — specialized aggregation queries for stock health, heatmap pivots, and alerts.

Layer: Infrastructure / Database
Consolidates analytical queries with multi-tenant scoping and subquery aggregations
to prevent N+1 query overhead across remote database connections.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.domain.value_objects import StockThresholds
from app.infrastructure.database.models import InventoryTransaction, Item, Location


def get_latest_stock_health(
    db: Session,
    org_id: Optional[int] = None,
    location_id: Optional[int] = None,
    category: Optional[str] = None,
):
    """
    Get stock health for most recent transaction across all locations and items
    with optional multi-tenant and dimension filters.
    """
    # Tenant-scoped calendar: the "latest date" must be computed within the caller's
    # org, otherwise one busy org's activity distorts another org's usage windows.
    latest_date_q = db.query(func.max(InventoryTransaction.date))
    if org_id is not None:
        latest_date_q = latest_date_q.filter(InventoryTransaction.org_id == org_id)
    latest_date = latest_date_q.scalar()

    if not latest_date:
        return []

    # Subquery: exact latest transaction per location and item (deterministic tie-break by max ID)
    latest_tx_q = db.query(
        func.max(InventoryTransaction.id).label("max_id"),
    )
    if org_id is not None:
        latest_tx_q = latest_tx_q.filter(InventoryTransaction.org_id == org_id)
    latest_tx_sub = (
        latest_tx_q
        .group_by(InventoryTransaction.location_id, InventoryTransaction.item_id)
        .subquery()
    )

    daily_usage_q = db.query(
        InventoryTransaction.location_id,
        InventoryTransaction.item_id,
        func.avg(InventoryTransaction.issued).label("avg_daily_usage"),
    ).filter(
        InventoryTransaction.date >= (latest_date - timedelta(days=StockThresholds.USAGE_WINDOW_DAYS)),
        InventoryTransaction.date <= latest_date,
    )
    if org_id is not None:
        daily_usage_q = daily_usage_q.filter(InventoryTransaction.org_id == org_id)
    subq = (
        daily_usage_q
        .group_by(InventoryTransaction.location_id, InventoryTransaction.item_id)
        .subquery()
    )

    query = (
        db.query(
            Location.id.label("location_id"),
            Location.name.label("location_name"),
            Location.type.label("location_type"),
            Item.id.label("item_id"),
            Item.name.label("item_name"),
            Item.category.label("category"),
            Item.lead_time_days,
            Item.min_stock,
            InventoryTransaction.closing_stock.label("current_stock"),
            subq.c.avg_daily_usage,
            case(
                (
                    subq.c.avg_daily_usage > 0,
                    InventoryTransaction.closing_stock / subq.c.avg_daily_usage,
                ),
                else_=999,
            ).label("days_remaining"),
            case(
                (
                    case(
                        (
                            subq.c.avg_daily_usage > 0,
                            InventoryTransaction.closing_stock / subq.c.avg_daily_usage,
                        ),
                        else_=999,
                    )
                    < StockThresholds.CRITICAL_DAYS,
                    "CRITICAL",
                ),
                (
                    case(
                        (
                            subq.c.avg_daily_usage > 0,
                            InventoryTransaction.closing_stock / subq.c.avg_daily_usage,
                        ),
                        else_=999,
                    ).between(StockThresholds.CRITICAL_DAYS, StockThresholds.WARNING_DAYS),
                    "WARNING",
                ),
                else_="HEALTHY",
            ).label("health_status"),
            InventoryTransaction.date.label("last_updated"),
        )
        .join(latest_tx_sub, InventoryTransaction.id == latest_tx_sub.c.max_id)
        .join(Location, InventoryTransaction.location_id == Location.id)
        .join(Item, InventoryTransaction.item_id == Item.id)
        .outerjoin(
            subq,
            (InventoryTransaction.location_id == subq.c.location_id)
            & (InventoryTransaction.item_id == subq.c.item_id),
        )
    )

    if org_id is not None:
        query = query.filter(Item.org_id == org_id)

    if location_id is not None:
        query = query.filter(Location.id == location_id)
    if category is not None and category != "ALL":
        query = query.filter(Item.category == category)

    return query.all()


def get_critical_alerts(db: Session, severity: str = "CRITICAL", org_id: Optional[int] = None):
    """Get items with critical or warning stock levels, scoped to org if provided."""
    stock_health = get_latest_stock_health(db, org_id=org_id)

    if severity == "CRITICAL":
        return [item for item in stock_health if item.health_status == "CRITICAL"]
    elif severity == "WARNING":
        return [item for item in stock_health if item.health_status in ("CRITICAL", "WARNING")]
    else:
        return stock_health


def get_heatmap_data(db: Session, org_id: Optional[int] = None) -> Dict[str, Any]:
    """Get stock health data formatted for heatmap visualization, scoped to org if provided."""
    stock_health = get_latest_stock_health(db, org_id=org_id)

    # Extract unique locations and items
    locations = sorted(set(item.location_name for item in stock_health))
    items = sorted(set(item.item_name for item in stock_health))

    # Build matrix: locations (rows) x items (columns)
    matrix = []
    for location in locations:
        row = []
        for item_name in items:
            match = next(
                (
                    s
                    for s in stock_health
                    if s.location_name == location and s.item_name == item_name
                ),
                None,
            )
            if match:
                row.append(
                    {
                        "stock": match.current_stock,
                        "status": match.health_status,
                        "days_remaining": match.days_remaining if match.days_remaining != 999 else None,
                    }
                )
            else:
                row.append({"stock": 0, "status": "UNKNOWN", "days_remaining": None})
        matrix.append(row)

    return {
        "locations": locations,
        "items": items,
        "matrix": matrix,
        "details": stock_health,
    }


class AnalyticsRepository:
    """Class-based interface for analytics queries with injected database session."""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_stock_health(
        self,
        org_id: Optional[int] = None,
        location_id: Optional[int] = None,
        category: Optional[str] = None,
    ):
        return get_latest_stock_health(
            self.db, org_id=org_id, location_id=location_id, category=category
        )

    def get_critical_alerts(self, severity: str = "CRITICAL", org_id: Optional[int] = None):
        return get_critical_alerts(self.db, severity=severity, org_id=org_id)

    def get_heatmap_data(self, org_id: Optional[int] = None) -> Dict[str, Any]:
        return get_heatmap_data(self.db, org_id=org_id)
