"""
Report Service — Application layer

Data-fetching layer for PDF and other report generation.
All SQLAlchemy queries that were previously embedded directly
in admin.py route handlers have been moved here.

The route layer calls these methods and only handles:
  - HTTP response construction (StreamingResponse, headers)
  - PDF rendering (reportlab)

This service has no knowledge of HTTP, FastAPI, or reportlab.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    InventoryTransaction,
    Item,
    Location,
    Requisition,
)

logger = logging.getLogger("smart_inventory.report_service")


# ---------------------------------------------------------------------------
# Public DTOs (plain dicts — no ORM objects leave this service)
# ---------------------------------------------------------------------------

StockRow = Dict[str, Any]
TransactionRow = Dict[str, Any]
RequisitionRow = Dict[str, Any]
RequisitionStats = Dict[str, Any]


class ReportService:
    """
    Encapsulates all data queries needed by the admin report generator.

    Instantiate with a live SQLAlchemy Session; the session lifecycle
    is managed by the caller (FastAPI Depends / test fixtures).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Inventory & Low-Stock ────────────────────────────────────────────

    def get_stock_rows(
        self,
        location_id: Optional[int] = None,
        org_id: Optional[int] = None,
    ) -> List[StockRow]:
        """
        Return the latest closing stock for every item scoped to the organization.

        Uses a subquery to select the most-recent transaction (max ID) per item,
        then joins back to get the closing_stock on that transaction.
        """
        subquery = self._db.query(
            InventoryTransaction.item_id,
            func.max(InventoryTransaction.id).label("max_id"),
        )
        if location_id is not None:
            subquery = subquery.filter(InventoryTransaction.location_id == location_id)

        latest_sub = subquery.group_by(InventoryTransaction.item_id).subquery()

        q = (
            self._db.query(
                Item.name,
                Item.category,
                Item.unit,
                Item.min_stock,
                InventoryTransaction.closing_stock,
            )
            .join(latest_sub, Item.id == latest_sub.c.item_id)
            .join(
                InventoryTransaction,
                InventoryTransaction.id == latest_sub.c.max_id,
            )
        )
        if location_id is not None:
            q = q.filter(InventoryTransaction.location_id == location_id)
        if org_id is not None:
            q = q.filter(Item.org_id == org_id)

        rows = q.all()
        return [
            {
                "name": r.name,
                "category": r.category,
                "unit": r.unit,
                "current_stock": r.closing_stock,
                "min_stock": r.min_stock,
            }
            for r in rows
        ]

    def get_low_stock_rows(
        self,
        location_id: Optional[int] = None,
        org_id: Optional[int] = None,
    ) -> List[StockRow]:
        """
        Same as get_stock_rows() but filtered to items at or below min_stock.
        """
        return [
            r
            for r in self.get_stock_rows(location_id=location_id, org_id=org_id)
            if r["current_stock"] <= r["min_stock"]
        ]

    # ── Transactions ─────────────────────────────────────────────────────

    def get_transaction_rows(
        self,
        location_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 200,
        org_id: Optional[int] = None,
    ) -> List[TransactionRow]:
        """
        Return recent inventory transactions with location and item names, scoped to org_id.
        """
        q = (
            self._db.query(
                InventoryTransaction.date,
                Location.name.label("location"),
                Item.name.label("item"),
                InventoryTransaction.opening_stock,
                InventoryTransaction.received,
                InventoryTransaction.issued,
                InventoryTransaction.closing_stock,
                InventoryTransaction.entered_by,
            )
            .join(Location, InventoryTransaction.location_id == Location.id)
            .join(Item, InventoryTransaction.item_id == Item.id)
        )
        if location_id is not None:
            q = q.filter(InventoryTransaction.location_id == location_id)
        if org_id is not None:
            q = q.filter(Location.org_id == org_id)
        if date_from:
            q = q.filter(InventoryTransaction.date >= date_from)
        if date_to:
            q = q.filter(InventoryTransaction.date <= date_to)

        rows = q.order_by(InventoryTransaction.date.desc()).limit(limit).all()
        return [
            {
                "date": str(r.date),
                "location": r.location,
                "item": r.item,
                "opening_stock": r.opening_stock,
                "received": r.received,
                "issued": r.issued,
                "closing_stock": r.closing_stock,
                "entered_by": r.entered_by,
            }
            for r in rows
        ]

    # ── Requisitions ─────────────────────────────────────────────────────

    def get_requisition_rows(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        org_id: Optional[int] = None,
    ) -> List[RequisitionRow]:
        """
        Return requisitions ordered by creation date descending, scoped to org_id.
        """
        q = self._db.query(
            Requisition.requisition_number,
            Requisition.department,
            Requisition.requested_by,
            Requisition.urgency,
            Requisition.status,
            Requisition.created_at,
            Requisition.approved_by,
        )
        if org_id is not None:
            q = q.filter(Requisition.org_id == org_id)
        if date_from:
            q = q.filter(Requisition.created_at >= date_from)
        if date_to:
            q = q.filter(Requisition.created_at <= date_to)

        rows = q.order_by(Requisition.created_at.desc()).limit(limit).all()
        return [
            {
                "requisition_number": r.requisition_number,
                "department": r.department,
                "requested_by": r.requested_by,
                "urgency": r.urgency,
                "status": r.status,
                "created_at": str(r.created_at)[:10] if r.created_at else "-",
                "approved_by": r.approved_by,
            }
            for r in rows
        ]

    def get_requisition_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        org_id: Optional[int] = None,
    ) -> RequisitionStats:
        """
        Return aggregated requisition counts for the summary table.
        """
        # Bug fix: use a very large limit so stats are never silently capped at 100 rows.
        rows = self.get_requisition_rows(date_from=date_from, date_to=date_to, org_id=org_id, limit=100_000)
        return {
            "total": len(rows),
            "pending": sum(1 for r in rows if r["status"] == "PENDING"),
            "approved": sum(1 for r in rows if r["status"] == "APPROVED"),
            "rejected": sum(1 for r in rows if r["status"] == "REJECTED"),
        }

    def get_monthly_sales_summary(
        self,
        org_id: int,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """
        Return Monthly Sales & Profit summary for a specific calendar month.
        Reads from Redis monthly cache with fallback to DB BillingSession aggregate.
        """
        month_key = f"{year:04d}-{month:02d}"
        summary = None
        try:
            from app.infrastructure.cache.redis_client import get_redis, is_redis_available
            r = get_redis()
            if r and is_redis_available():
                raw = r.hgetall(f"sales:{org_id}:{month_key}")
                if raw:
                    summary = {
                        "month":           month_key,
                        "session_count":   int(raw.get(b"session_count", 0) or raw.get("session_count", 0)),
                        "gross_total":     float(raw.get(b"gross_total",    0) or raw.get("gross_total",    0)),
                        "discount_amount": float(raw.get(b"discount_amount",0) or raw.get("discount_amount",0)),
                        "net_total":       float(raw.get(b"net_total",      0) or raw.get("net_total",      0)),
                        "purchase_cost":   float(raw.get(b"purchase_cost",  0) or raw.get("purchase_cost",  0)),
                    }
                    net    = summary["net_total"]
                    cost   = summary["purchase_cost"]
                    profit = round(net - cost, 2)
                    summary["gross_profit"] = profit
                    summary["margin_pct"]   = round((profit / net * 100) if net > 0 else 0.0, 2)
        except Exception as e:
            logger.warning("Redis monthly sales cache read failed in ReportService: %s", e)

        if summary is None:
            from app.infrastructure.database.billing_repo import BillingRepository
            repo = BillingRepository(self._db)
            summary = repo.get_monthly_aggregate(org_id=org_id, year=year, month=month)

        return summary



# ---------------------------------------------------------------------------
# Convenience factory — use in FastAPI Depends
# ---------------------------------------------------------------------------

def get_report_service(db: Session) -> ReportService:
    """FastAPI dependency factory for ReportService."""
    return ReportService(db)
