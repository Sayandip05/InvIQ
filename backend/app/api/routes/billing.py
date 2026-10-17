"""
Billing API — Cart-based pharmacy counter billing with auto discount.

Layer: API / Routes

Workflow:
  1. POST /billing/sessions          → open a new bill (OPEN)
  2. POST /billing/sessions/{id}/scan→ scan medicine, add to cart, deduct stock immediately
  3. POST /billing/sessions/{id}/checkout → apply discount, close bill, fire async Celery task
  4. GET  /billing/sessions/{id}     → fetch session state (for receipt)
  5. DELETE /billing/sessions/{id}   → cancel, restore stock via reverse transactions

All endpoints are staff-or-above scoped to the caller's org.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.rate_limiter import limiter
from app.core.dependencies import (
    get_db,
    require_staff,
    get_caller_org_id,
    get_inventory_service,
    get_inventory_repo,
)
from app.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    ValidationError,
    InvalidStateError,
)
from app.infrastructure.database.models import User, Organization
from app.infrastructure.database.billing_repo import BillingRepository
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.application.inventory_service import InventoryService
from app.application.discount_service import apply_discount
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("smart_inventory.billing")

router = APIRouter(prefix="/billing", tags=["Billing Counter"])


# Pydantic request schemas

class OpenSessionRequest(BaseModel):
    location_id: int = Field(gt=0, description="Counter / branch location ID")


class ScanItemRequest(BaseModel):
    barcode:     str = Field(min_length=1, max_length=100, description="Medicine barcode, package barcode, or item ID")
    quantity:    int = Field(default=1, gt=0, description="Number of units/packages to dispense")
    location_id: int = Field(gt=0, description="Must match the session's location")
    unit:        Optional[str] = Field(default=None, description="Packaging unit (e.g. strip, box, tablet)")


# Helpers

def _get_session_or_404(billing_repo: BillingRepository, session_id: int, org_id: Optional[int]):
    session = billing_repo.get_by_id(session_id, org_id=org_id)
    if not session:
        raise NotFoundError("BillingSession", session_id)
    return session


def _require_open(session):
    if session.status != "OPEN":
        raise InvalidStateError(
            f"BillingSession #{session.id} is already {session.status}. "
            "Cannot modify a closed or cancelled bill."
        )


# Endpoints


@router.post("/sessions", response_model=dict)
@limiter.limit("30/minute")
def open_billing_session(
    request: Request,
    body: OpenSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Open a new customer billing session at a pharmacy counter."""
    org_id = get_caller_org_id(current_user)
    billing_repo = BillingRepository(db)

    # Validate location belongs to this org
    from app.infrastructure.database.models import Location
    location = (
        db.query(Location)
        .filter(Location.id == body.location_id, Location.org_id == org_id)
        .first()
    )
    if not location:
        raise NotFoundError("Location", body.location_id)

    session = billing_repo.create_session(
        org_id=org_id,
        location_id=body.location_id,
        cashier_id=current_user.id,
    )

    return {
        "success": True,
        "message": "Billing session opened",
        "data": {
            "session_id":  session.id,
            "status":      session.status,
            "location_id": session.location_id,
            "cashier":     current_user.username,
            "opened_at":   session.opened_at.isoformat() if session.opened_at else None,
            "items":       [],
        },
    }


@router.post("/sessions/{session_id}/scan", response_model=dict)
@limiter.limit("120/minute")
def scan_item_to_session(
    request: Request,
    session_id: int,
    body: ScanItemRequest,
    db: Session = Depends(get_db),
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_staff),
):
    """
    Scan a barcode and add to the open billing session.
    Stock is deducted immediately in base units via the FEFO dispense logic.
    """
    org_id = get_caller_org_id(current_user)
    billing_repo = BillingRepository(db)

    session = _get_session_or_404(billing_repo, session_id, org_id)
    _require_open(session)

    if session.location_id != body.location_id:
        raise ValidationError(
            f"Location mismatch: session #{session_id} is for location "
            f"#{session.location_id}, not #{body.location_id}."
        )

    # Delegate to dispense_by_barcode with UOM resolution — FEFO, advisory lock, base stock deduction
    dispense_result = service.dispense_by_barcode(
        barcode_or_id=body.barcode,
        location_id=body.location_id,
        quantity=body.quantity,
        unit=body.unit,
        entered_by=str(current_user.username),
        org_id=org_id,
    )

    d = dispense_result["data"]
    unit_mrp = float(d.get("mrp", 0.0))
    line_total = round(unit_mrp * body.quantity, 2)
    multiplier = int(d.get("multiplier", 1))
    base_qty_deducted = int(d.get("base_quantity_dispensed", body.quantity * multiplier))
    packaging_unit = d.get("packaging_unit", "units")
    purchase_rate = float(d.get("purchase_rate", 0.0))

    # Build item snapshot with UOM packaging metadata
    item_snapshot = {
        "item_id":            d["item_id"],
        "item_name":          d["item_name"],
        "barcode":            d.get("barcode"),
        "packaging_unit":     packaging_unit,
        "base_unit":          d.get("base_unit", "units"),
        "multiplier":         multiplier,
        "qty":                body.quantity,
        "base_qty_deducted":  base_qty_deducted,
        "mrp":                unit_mrp,
        "purchase_rate":      purchase_rate,
        "line_total":         line_total,
        "batch_number":       d.get("batch_number"),
        "allocated_batches":  d.get("allocated_batches", []),
        "transaction_id":     d.get("transaction_id"),
    }

    session = billing_repo.append_item(session, item_snapshot)

    # Compute running cart total
    gross_running = round(sum(i["line_total"] for i in session.items), 2)

    # Preview discount (without closing the session)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    discount_config = (org.settings or {}) if org else {}
    billing_preview = apply_discount(gross_running, discount_config)

    return {
        "success": True,
        "message": f"Added {body.quantity} {packaging_unit} of {d['item_name']} to bill",
        "data": {
            "session_id":     session.id,
            "items":          session.items,
            "item_count":     len(session.items),
            "billing_preview": billing_preview,
        },
    }


@router.post("/sessions/{session_id}/checkout", response_model=dict)
@limiter.limit("30/minute")
def checkout_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Close the billing session, apply discount on cart total, and fire async
    Celery task to update the monthly sales Redis cache.
    """
    org_id = get_caller_org_id(current_user)
    billing_repo = BillingRepository(db)

    session = _get_session_or_404(billing_repo, session_id, org_id)
    _require_open(session)

    if not session.items:
        raise ValidationError("Cannot checkout an empty billing session. Scan at least one item first.")

    # Compute gross total from item snapshots
    gross_total = round(sum(float(i.get("line_total", 0)) for i in session.items), 2)
    purchase_cost = round(sum(
        float(i.get("purchase_rate", 0)) * int(i.get("qty", 1))
        for i in session.items
    ), 2)

    # Load org discount policy
    org = db.query(Organization).filter(Organization.id == org_id).first()
    discount_config = (org.settings or {}) if org else {}
    billing = apply_discount(gross_total, discount_config)

    # month_key for aggregation
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")

    closed_session = billing_repo.checkout(
        session=session,
        gross_total=billing["gross_total"],
        discount_model=billing["discount_model"],
        discount_pct=billing["discount_pct"],
        discount_amount=billing["discount_amount"],
        net_total=billing["net_total"],
        purchase_cost=purchase_cost,
        month_key=month_key,
    )

    # Fire async Celery task to update monthly sales Redis cache
    try:
        from app.workers.tasks import update_monthly_sales_cache_task
        update_monthly_sales_cache_task.delay(
            session_id=closed_session.id,
            org_id=org_id,
        )
    except Exception as e:
        logger.warning("Could not dispatch monthly sales cache task: %s", e)

    return {
        "success": True,
        "message": "Bill checked out successfully",
        "data": {
            "session_id":     closed_session.id,
            "status":         closed_session.status,
            "items":          closed_session.items,
            "billing":        billing,
            "purchase_cost":  purchase_cost,
            "cashier":        current_user.username,
            "closed_at":      closed_session.closed_at.isoformat() if closed_session.closed_at else None,
        },
    }


@router.get("/sessions/{session_id}", response_model=dict)
def get_billing_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Fetch current state of a billing session (for receipt display)."""
    org_id = get_caller_org_id(current_user)
    billing_repo = BillingRepository(db)

    session = _get_session_or_404(billing_repo, session_id, org_id)

    # Compute running billing preview if OPEN
    billing_preview = None
    if session.status == "OPEN" and session.items:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        discount_config = (org.settings or {}) if org else {}
        gross = round(sum(float(i.get("line_total", 0)) for i in session.items), 2)
        billing_preview = apply_discount(gross, discount_config)

    return {
        "success": True,
        "data": {
            "session_id":    session.id,
            "status":        session.status,
            "location_id":   session.location_id,
            "cashier_id":    session.cashier_id,
            "items":         session.items,
            "item_count":    len(session.items),
            "billing_preview": billing_preview,
            "gross_total":   session.gross_total,
            "discount_model":session.discount_model,
            "discount_pct":  session.discount_pct,
            "discount_amount":session.discount_amount,
            "net_total":     session.net_total,
            "opened_at":     session.opened_at.isoformat() if session.opened_at else None,
            "closed_at":     session.closed_at.isoformat() if session.closed_at else None,
            "month_key":     session.month_key,
        },
    }


@router.delete("/sessions/{session_id}", response_model=dict)
@limiter.limit("20/minute")
def cancel_billing_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_staff),
):
    """
    Cancel an OPEN billing session.
    Restores stock for every item already scanned by issuing reverse transactions.
    """
    org_id = get_caller_org_id(current_user)
    billing_repo = BillingRepository(db)

    session = _get_session_or_404(billing_repo, session_id, org_id)
    _require_open(session)

    # Reverse each dispensed item's stock in base units
    from datetime import date
    reversed_items = []
    for line in (session.items or []):
        try:
            base_qty_to_restore = int(line.get("base_qty_deducted") or (int(line["qty"]) * int(line.get("multiplier", 1))))
            pkg_name = line.get("packaging_unit") or "units"
            service.add_transaction(
                location_id=session.location_id,
                item_id=int(line["item_id"]),
                transaction_date=date.today(),
                received=base_qty_to_restore,  # Put base stock back
                issued=0,
                notes=f"VOID: Billing session #{session_id} cancelled ({line['qty']} {pkg_name})",
                entered_by=str(current_user.username),
                batch_number=line.get("batch_number"),
                transacted_unit=pkg_name,
                transacted_qty=int(line["qty"]),
                multiplier=int(line.get("multiplier", 1)),
            )
            reversed_items.append(line["item_name"])
        except Exception as e:
            logger.error(
                "Failed to reverse stock for item %s in cancelled session %s: %s",
                line.get("item_id"), session_id, e,
            )

    billing_repo.cancel(session)

    return {
        "success": True,
        "message": f"Billing session #{session_id} cancelled. Stock restored for {len(reversed_items)} item(s).",
        "data": {
            "session_id":    session_id,
            "status":        "CANCELLED",
            "reversed_items": reversed_items,
        },
    }
