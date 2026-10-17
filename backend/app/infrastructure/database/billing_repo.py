"""
Billing Repository — data access layer for BillingSession.

Layer: Infrastructure / Database

All DB queries for billing sessions live here.
The billing route layer calls this via FastAPI Depends().
No business logic — only DB reads and writes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.infrastructure.database.models import BillingSession

logger = logging.getLogger("smart_inventory.billing_repo")


class BillingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # Create

    def create_session(
        self,
        org_id: int,
        location_id: int,
        cashier_id: int,
    ) -> BillingSession:
        """Open a new OPEN billing session for a customer bill."""
        session = BillingSession(
            org_id=org_id,
            location_id=location_id,
            cashier_id=cashier_id,
            status="OPEN",
            items=[],
        )
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        logger.info(
            "BillingSession #%s opened | org=%s location=%s cashier=%s",
            session.id, org_id, location_id, cashier_id,
        )
        return session

    # Read

    def get_by_id(self, session_id: int, org_id: Optional[int] = None) -> Optional[BillingSession]:
        """Fetch a BillingSession by primary key, optionally scoped to org."""
        q = self._db.query(BillingSession).filter(BillingSession.id == session_id)
        if org_id is not None:
            q = q.filter(BillingSession.org_id == org_id)
        return q.first()

    def get_open_sessions_for_cashier(
        self, cashier_id: int, org_id: int
    ) -> List[BillingSession]:
        """Return all OPEN sessions for a cashier (should normally be 0–1)."""
        return (
            self._db.query(BillingSession)
            .filter(
                BillingSession.cashier_id == cashier_id,
                BillingSession.org_id == org_id,
                BillingSession.status == "OPEN",
            )
            .order_by(BillingSession.opened_at.desc())
            .all()
        )

    # Append item to cart

    def append_item(
        self,
        session: BillingSession,
        item_snapshot: Dict[str, Any],
    ) -> BillingSession:
        """
        Append one line item to the session's items JSON array.
        Uses list copy to trigger SQLAlchemy dirty-detection on JSON column.
        """
        current = list(session.items or [])
        current.append(item_snapshot)
        session.items = current
        self._db.commit()
        self._db.refresh(session)
        return session

    # Checkout

    def checkout(
        self,
        session: BillingSession,
        gross_total: float,
        discount_model: str,
        discount_pct: float,
        discount_amount: float,
        net_total: float,
        purchase_cost: float,
        month_key: str,        # "YYYY-MM"
    ) -> BillingSession:
        """Close the session and persist financial breakdown."""
        session.status          = "CLOSED"
        session.gross_total     = round(gross_total, 2)
        session.discount_model  = discount_model
        session.discount_pct    = round(discount_pct, 4)
        session.discount_amount = round(discount_amount, 2)
        session.net_total       = round(net_total, 2)
        session.purchase_cost   = round(purchase_cost, 2)
        session.closed_at       = datetime.now(timezone.utc)
        session.month_key       = month_key
        self._db.commit()
        self._db.refresh(session)
        logger.info(
            "BillingSession #%s CLOSED | gross=%.2f disc=%.2f%% net=%.2f",
            session.id, gross_total, discount_pct, net_total,
        )
        return session

    # Cancel

    def cancel(self, session: BillingSession) -> BillingSession:
        """Mark a session CANCELLED (stock reversal is done by the route layer)."""
        session.status    = "CANCELLED"
        session.closed_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(session)
        logger.info("BillingSession #%s CANCELLED", session.id)
        return session

    # Monthly aggregation (fallback when Redis is cold)

    def get_monthly_aggregate(self, org_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Aggregate CLOSED billing sessions for a given calendar month.
        Used as the Redis-cold fallback in ReportService.
        """
        from sqlalchemy import func as sqlfunc
        month_key = f"{year:04d}-{month:02d}"

        result = (
            self._db.query(
                sqlfunc.count(BillingSession.id).label("session_count"),
                sqlfunc.coalesce(sqlfunc.sum(BillingSession.gross_total),    0.0).label("gross_total"),
                sqlfunc.coalesce(sqlfunc.sum(BillingSession.discount_amount), 0.0).label("discount_amount"),
                sqlfunc.coalesce(sqlfunc.sum(BillingSession.net_total),      0.0).label("net_total"),
                sqlfunc.coalesce(sqlfunc.sum(BillingSession.purchase_cost),  0.0).label("purchase_cost"),
            )
            .filter(
                BillingSession.org_id == org_id,
                BillingSession.status == "CLOSED",
                BillingSession.month_key == month_key,
            )
            .one()
        )

        gross    = float(result.gross_total)
        cost     = float(result.purchase_cost)
        net      = float(result.net_total)
        profit   = round(net - cost, 2)
        margin   = round((profit / net * 100) if net > 0 else 0.0, 2)

        return {
            "month":           month_key,
            "session_count":   result.session_count,
            "gross_total":     round(gross, 2),
            "discount_amount": round(float(result.discount_amount), 2),
            "net_total":       round(net, 2),
            "purchase_cost":   round(cost, 2),
            "gross_profit":    profit,
            "margin_pct":      margin,
        }
