"""
Background tasks module for retail chemist operations.

Provides both standalone asynchronous functions (for direct execution or FastAPI background tasks)
and Celery-compatible task wrappers for scheduled Celery Beat execution.
"""

import logging
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from app.infrastructure.database.models import Item, Location, InventoryTransaction
from app.infrastructure.database.analytics_repo import get_critical_alerts
from app.api.routes.websocket import queue_websocket_alert

logger = logging.getLogger("smart_inventory.background")


def run_fefo_expiry_audit(
    db: Session,
    days_ahead: int = 60,
    org_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Audits all active inventory batches and identifies batches expiring soon.
    Dispatches real-time WebSocket alerts to pharmacy counters for FEFO rotation.
    Scoping: Multi-tenant aware (filters by org_id when provided, tags alerts with org_id).
    """
    cutoff = date.today() + timedelta(days=days_ahead)
    query = (
        db.query(InventoryTransaction)
        .join(Item, InventoryTransaction.item_id == Item.id)
        .join(Location, InventoryTransaction.location_id == Location.id)
        .filter(
            InventoryTransaction.expiry_date.isnot(None),
            InventoryTransaction.expiry_date >= date.today(),  # Bug 5 fix: exclude already-expired batches
            InventoryTransaction.expiry_date <= cutoff,
            InventoryTransaction.closing_stock > 0,
        )
    )

    if org_id is not None:
        query = query.filter(Item.org_id == org_id)

    expiring_batches = query.order_by(InventoryTransaction.expiry_date.asc()).all()

    total_risk_val = 0.0
    alerts_emitted = 0

    for tx in expiring_batches:
        days_left = (tx.expiry_date - date.today()).days if tx.expiry_date else 0
        mrp = getattr(tx.item, "mrp", 0.0) or 0.0
        risk_val = float(mrp) * float(tx.closing_stock)
        total_risk_val += risk_val

        # Multi-tenant org_id resolution: Item -> Location -> Passed org_id
        item_org_id = (
            getattr(tx.item, "org_id", None)
            or (getattr(tx.location, "org_id", None) if tx.location else None)
            or org_id
        )

        if not item_org_id:
            logger.warning(
                "Skipping FEFO expiry alert for item '%s' (id=%s) — no organization associated",
                getattr(tx.item, "name", "Unknown"),
                getattr(tx.item, "id", "N/A"),
            )
            continue

        alert_data = {
            "type": "fefo_expiry_alert",
            "event_topic": "expiry.critical",
            "message": f"FEFO Expiry Alert: {tx.item.name} (Batch #{tx.batch_number or 'N/A'}) expires in {days_left} days",
            "item_name": tx.item.name,
            "item_id": tx.item.id,
            "batch_number": tx.batch_number,
            "expiry_date": str(tx.expiry_date),
            "days_remaining": days_left,
            "location_name": tx.location.name if tx.location else "Main Counter",
            "location_id": tx.location.id if tx.location else None,
            "current_stock": tx.closing_stock,
            "estimated_loss_inr": round(risk_val, 2),
            "org_id": item_org_id,
        }

        queue_websocket_alert(alert_data, org_id=item_org_id)
        alerts_emitted += 1

    logger.info(
        "FEFO Expiry Audit completed (org_id=%s): %d batches identified at risk, ₹%.2f estimated value",
        org_id or "all",
        len(expiring_batches),
        total_risk_val,
    )

    return {
        "status": "success",
        "org_id": org_id,
        "batches_at_risk": len(expiring_batches),
        "total_risk_value_inr": round(total_risk_val, 2),
        "alerts_emitted": alerts_emitted,
    }


def run_stock_threshold_audit(
    db: Session,
    org_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Identifies critical and warning stock shortages across all pharmacy locations.
    Dispatches real-time WebSocket alerts tagged with tenant org_id.
    """
    critical_alerts = get_critical_alerts(db, "CRITICAL", org_id=org_id)
    warning_alerts = get_critical_alerts(db, "WARNING", org_id=org_id)

    alerts_emitted = 0
    # Emit WebSocket alerts for critical stock shortages
    for alert in critical_alerts:
        # Resolve item's org_id if available on alert or item
        item_org_id = getattr(alert, "org_id", None) or org_id
        if item_org_id is None:
            # Look up item's org_id from DB
            item_row = db.query(Item.org_id).filter(Item.id == alert.item_id).first()
            item_org_id = item_row[0] if item_row and item_row[0] else None

        if not item_org_id:
            logger.warning(
                "Skipping stock threshold alert for item '%s' (id=%s) — no organization associated",
                getattr(alert, "item_name", "Unknown"),
                getattr(alert, "item_id", "N/A"),
            )
            continue

        days_text = f" ({round(float(alert.days_remaining), 1)} days left)" if alert.days_remaining is not None else ""
        queue_websocket_alert({
            "type": "stock_critical_alert",
            "event_topic": "stock.low",
            "message": f"Critical Stock Shortage: {alert.item_name} at {alert.location_name} — {alert.current_stock} remaining{days_text}",
            "item_name": alert.item_name,
            "item_id": alert.item_id,
            "location_name": alert.location_name,
            "location_id": alert.location_id,
            "current_stock": float(alert.current_stock or 0),
            "days_remaining": round(float(alert.days_remaining), 1) if alert.days_remaining is not None else None,
            "health_status": "CRITICAL",
            "org_id": item_org_id,
        }, org_id=item_org_id)
        alerts_emitted += 1

    logger.info(
        "Stock Threshold Audit completed (org_id=%s): %d critical, %d warnings, %d alerts emitted",
        org_id or "all",
        len(critical_alerts),
        len(warning_alerts),
        alerts_emitted,
    )

    return {
        "status": "success",
        "org_id": org_id,
        "critical_count": len(critical_alerts),
        "warning_count": len(warning_alerts),
        "alerts_emitted": alerts_emitted,
    }


def run_cold_chain_health_check(
    db: Session,
    org_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Checks all cold-chain compliant items (Insulin, Vaccines, 2-8°C storage).
    Dispatches tenant-scoped alerts if cold-chain stocks require urgent attention.
    """
    query = db.query(Item).filter(Item.storage_temp == "cold_chain")
    if org_id is not None:
        query = query.filter(Item.org_id == org_id)

    cold_items = query.all()

    alerts_emitted = 0
    # Audit active stock and temperature tracking for cold-chain items
    for item in cold_items:
        item_org_id = getattr(item, "org_id", None) or org_id
        if not item_org_id:
            logger.warning(
                "Skipping cold-chain alert for item '%s' (id=%s) — no organization associated",
                item.name,
                item.id,
            )
            continue

        # Check if item has any batches nearing expiry (<30 days)
        cutoff = date.today() + timedelta(days=30)
        expiring_tx = (
            db.query(InventoryTransaction)
            .join(Location, InventoryTransaction.location_id == Location.id)
            .filter(
                InventoryTransaction.item_id == item.id,
                InventoryTransaction.expiry_date.isnot(None),
                InventoryTransaction.expiry_date <= cutoff,
                InventoryTransaction.closing_stock > 0,
            )
            .first()
        )

        if expiring_tx:
            days_left = (expiring_tx.expiry_date - date.today()).days if expiring_tx.expiry_date else 0
            location_name = expiring_tx.location.name if expiring_tx.location else "Cold Storage"
            queue_websocket_alert({
                "type": "cold_chain_warning",
                "event_topic": "coldchain.warning",
                "message": f"Cold-Chain Warning: {item.name} in {location_name} expires in {days_left} days (2-8°C)",
                "item_name": item.name,
                "item_id": item.id,
                "batch_number": expiring_tx.batch_number,
                "expiry_date": str(expiring_tx.expiry_date),
                "days_remaining": days_left,
                "location_name": location_name,
                "location_id": expiring_tx.location.id if expiring_tx.location else None,
                "current_stock": expiring_tx.closing_stock,
                "storage_temp": item.storage_temp or "2-8°C",
                "org_id": item_org_id,
            }, org_id=item_org_id)
            alerts_emitted += 1

    logger.info(
        "Cold-Chain Check completed (org_id=%s): %d items monitored, %d alerts emitted",
        org_id or "all",
        len(cold_items),
        alerts_emitted,
    )

    return {
        "status": "success",
        "org_id": org_id,
        "cold_chain_items_monitored": len(cold_items),
        "alerts_emitted": alerts_emitted,
    }

