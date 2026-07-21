from datetime import timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from langchain_core.tools import tool
from app.infrastructure.database.queries import (
    get_latest_stock_health,
    get_critical_alerts,
)
from app.infrastructure.database.models import Location, Item, InventoryTransaction
from app.domain.calculations import calculate_reorder_quantity

import threading

_thread_local = threading.local()


def set_db_session(db: Session):
    """Set the database session for tools to use (thread-safe request-scoped storage)."""
    _thread_local.db = db


def _get_db() -> Optional[Session]:
    """Get the current thread-scoped database session."""
    return getattr(_thread_local, "db", None)



def _no_data_message(message: str) -> List[Dict[str, Any]]:
    return [{"info": message}]


@tool
def get_inventory_overview() -> Dict[str, Any]:
    """Get a high-level overview of inventory: location, item, and transaction counts."""
    db = _get_db()
    if not db:
        return {"error": "Database not connected"}

    try:
        locations_count = db.query(Location).count()
        items_count = db.query(Item).count()
        transactions_count = db.query(InventoryTransaction).count()
        min_date, max_date = db.query(
            func.min(InventoryTransaction.date),
            func.max(InventoryTransaction.date),
        ).one()

        return {
            "locations": locations_count,
            "items": items_count,
            "transactions": transactions_count,
            "transaction_start_date": str(min_date) if min_date else None,
            "transaction_end_date": str(max_date) if max_date else None,
            "has_data": transactions_count > 0,
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def get_critical_items(
    location: str = "", severity: str = "CRITICAL"
) -> List[Dict[str, Any]]:
    """Get items with critically low or warning-level stock. Filter by location and severity."""
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        if severity not in {"CRITICAL", "WARNING"}:
            return [{"error": "Severity must be CRITICAL or WARNING"}]

        alerts = get_critical_alerts(db, severity)

        if location and location.strip():
            alerts = [
                item
                for item in alerts
                if location.lower() in item.location_name.lower()
            ]

        if not alerts:
            return _no_data_message("No matching low-stock alerts found.")

        results = []
        for alert in alerts[:20]:
            results.append(
                {
                    "location": alert.location_name,
                    "item": alert.item_name,
                    "category": alert.category,
                    "current_stock": alert.current_stock,
                    "days_remaining": round(alert.days_remaining, 1)
                    if alert.days_remaining != 999
                    else "N/A",
                    "daily_usage": round(alert.avg_daily_usage, 1)
                    if alert.avg_daily_usage
                    else 0,
                    "status": alert.health_status,
                }
            )

        return results
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_stock_health(item: str = "", location: str = "") -> List[Dict[str, Any]]:
    """Get current stock health across all locations and items, with optional filters."""
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        stock_health = get_latest_stock_health(db)

        if item and item.strip():
            stock_health = [
                s for s in stock_health if item.lower() in s.item_name.lower()
            ]

        if location and location.strip():
            stock_health = [
                s for s in stock_health if location.lower() in s.location_name.lower()
            ]

        if not stock_health:
            return _no_data_message("No stock health data found for the given filters.")

        results = []
        for item_data in stock_health[:30]:
            results.append(
                {
                    "location": item_data.location_name,
                    "item": item_data.item_name,
                    "category": item_data.category,
                    "current_stock": item_data.current_stock,
                    "days_remaining": round(item_data.days_remaining, 1)
                    if item_data.days_remaining != 999
                    else "Plenty",
                    "status": item_data.health_status,
                    "daily_usage": round(item_data.avg_daily_usage, 1)
                    if item_data.avg_daily_usage
                    else 0,
                }
            )

        return results
    except Exception as e:
        return [{"error": str(e)}]


@tool
def calculate_reorder_suggestions(location: str = "") -> List[Dict[str, Any]]:
    """Calculate recommended reorder quantities for critical items."""
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        critical = get_critical_alerts(db, "CRITICAL")

        if location and location.strip():
            critical = [
                item
                for item in critical
                if location.lower() in item.location_name.lower()
            ]

        if not critical:
            return _no_data_message(
                "No critical items currently require reorder suggestions."
            )

        suggestions = []
        for item in critical[:15]:
            reorder_qty = calculate_reorder_quantity(
                avg_daily_usage=item.avg_daily_usage or 0,
                lead_time_days=item.lead_time_days,
                current_stock=item.current_stock,
            )

            suggestions.append(
                {
                    "location": item.location_name,
                    "item": item.item_name,
                    "current_stock": item.current_stock,
                    "recommended_quantity": reorder_qty,
                    "urgency": "HIGH" if item.days_remaining < 1 else "MEDIUM",
                    "reasoning": f"Daily usage: {round(item.avg_daily_usage, 1)} units, Lead time: {item.lead_time_days} days",
                }
            )

        return suggestions
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_location_summary(location_name: str) -> Dict[str, Any]:
    """Get a health summary for a specific location by name."""
    db = _get_db()
    if not db:
        return {"error": "Database not connected"}

    try:
        stock_health = get_latest_stock_health(db)

        location_data = [
            s for s in stock_health if location_name.lower() in s.location_name.lower()
        ]

        if not location_data:
            return {"error": f"No data found for location: {location_name}"}

        critical = sum(1 for s in location_data if s.health_status == "CRITICAL")
        warning = sum(1 for s in location_data if s.health_status == "WARNING")
        healthy = sum(1 for s in location_data if s.health_status == "HEALTHY")

        return {
            "location": location_data[0].location_name,
            "total_items": len(location_data),
            "critical_items": critical,
            "warning_items": warning,
            "healthy_items": healthy,
            "status": "NEEDS_ATTENTION" if critical > 0 else "STABLE",
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def get_category_analysis(category: str) -> List[Dict[str, Any]]:
    """Analyze stock health for items in a specific category."""
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        stock_health = get_latest_stock_health(db)

        category_data = [
            s for s in stock_health if category.lower() in s.category.lower()
        ]

        if not category_data:
            return [{"error": f"No data found for category: {category}"}]

        results = []
        for item in category_data[:20]:
            results.append(
                {
                    "item": item.item_name,
                    "location": item.location_name,
                    "status": item.health_status,
                    "current_stock": item.current_stock,
                    "days_remaining": round(item.days_remaining, 1)
                    if item.days_remaining != 999
                    else "Plenty",
                }
            )

        return results
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_consumption_trends(
    item: str = "", location: str = "", days: int = 14
) -> Dict[str, Any]:
    """Get consumption trends over the last N days, with optional item/location filters."""
    db = _get_db()
    if not db:
        return {"error": "Database not connected"}

    days = max(1, min(days, 90))

    try:
        latest_date = db.query(func.max(InventoryTransaction.date)).scalar()
        if not latest_date:
            return {"info": "No transaction data available yet."}

        start_date = latest_date - timedelta(days=days - 1)

        query = (
            db.query(
                InventoryTransaction.date.label("date"),
                func.sum(InventoryTransaction.issued).label("issued"),
            )
            .join(Location, InventoryTransaction.location_id == Location.id)
            .join(Item, InventoryTransaction.item_id == Item.id)
            .filter(InventoryTransaction.date >= start_date)
        )

        if item and item.strip():
            query = query.filter(Item.name.ilike(f"%{item.strip()}%"))

        if location and location.strip():
            query = query.filter(Location.name.ilike(f"%{location.strip()}%"))

        rows = (
            query.group_by(InventoryTransaction.date)
            .order_by(InventoryTransaction.date.asc())
            .all()
        )

        if not rows:
            return {"info": "No trend data found for the selected filters."}

        series = [{"date": str(r.date), "issued": int(r.issued or 0)} for r in rows]
        values = [point["issued"] for point in series]

        return {
            "start_date": str(start_date),
            "end_date": str(latest_date),
            "days_requested": days,
            "points": series,
            "total_issued": int(sum(values)),
            "avg_daily_issued": round(sum(values) / len(values), 2),
            "peak_daily_issued": int(max(values)),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Pharmacy-Specific Tools ────────────────────────────────────────────────────

@tool
def get_near_expiry_items(days: int = 60) -> List[Dict[str, Any]]:
    """
    List all medication batches expiring within the specified number of days.
    Batch numbers and expiry dates are tracked per-delivery on inventory transactions.
    Returns item name, category, batch number, expiry date, location, and days remaining.
    """
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        cutoff = date.today() + timedelta(days=days)
        rows = (
            db.query(InventoryTransaction)
            .join(Item, InventoryTransaction.item_id == Item.id)
            .join(Location, InventoryTransaction.location_id == Location.id)
            .filter(
                InventoryTransaction.expiry_date != None,
                InventoryTransaction.expiry_date <= cutoff,
                InventoryTransaction.received > 0,  # Only inbound batches
            )
            .order_by(InventoryTransaction.expiry_date.asc())
            .limit(50)
            .all()
        )

        if not rows:
            return [{"info": f"No batches expiring within {days} days."}]

        return [
            {
                "item_name": row.item.name,
                "category": row.item.category,
                "batch_number": row.batch_number,
                "expiry_date": str(row.expiry_date),
                "days_remaining": (row.expiry_date - date.today()).days,
                "location": row.location.name,
                "storage_temp": row.item.storage_temp,
                "received_qty": row.received,
            }
            for row in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_cold_chain_items(location: str = "") -> List[Dict[str, Any]]:
    """
    List all cold-chain medications and vaccines (require refrigerated storage).
    Optionally filter by location name. Returns item name, category, latest batch number,
    nearest expiry date from the latest transaction, and current stock level.
    """
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        items = (
            db.query(Item)
            .filter(Item.storage_temp == "cold_chain")
            .order_by(Item.category.asc(), Item.name.asc())
            .limit(50)
            .all()
        )

        if not items:
            return [{"info": "No cold-chain items found in the database."}]

        results = []
        for item in items:
            tx_query = (
                db.query(InventoryTransaction)
                .join(Location)
                .filter(InventoryTransaction.item_id == item.id)
            )
            if location and location.strip():
                tx_query = tx_query.filter(Location.name.ilike(f"%{location.strip()}%"))

            # Latest transaction = current stock level + most recent batch info
            latest_tx = tx_query.order_by(InventoryTransaction.date.desc()).first()

            results.append({
                "item_name": item.name,
                "category": item.category,
                "storage_temp": item.storage_temp,
                "latest_batch": latest_tx.batch_number if latest_tx else None,
                "batch_expiry": str(latest_tx.expiry_date) if latest_tx and latest_tx.expiry_date else None,
                "days_to_expiry": (latest_tx.expiry_date - date.today()).days if latest_tx and latest_tx.expiry_date else None,
                "current_stock": latest_tx.closing_stock if latest_tx else "No data",
                "location": latest_tx.location.name if latest_tx else "N/A",
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]
