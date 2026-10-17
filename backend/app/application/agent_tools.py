import contextvars
import logging
from datetime import timedelta, date
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func
from langchain_core.tools import tool
from app.infrastructure.database.analytics_repo import (
    get_latest_stock_health,
    get_critical_alerts,
)
from app.infrastructure.database.models import Location, Item, InventoryTransaction
from app.domain.calculations import calculate_reorder_quantity

_logger = logging.getLogger("smart_inventory.agent")


# ReadOnlySession — structural write guard for the AI agent

_WRITE_METHODS = frozenset({
    "add", "add_all", "delete", "merge", "flush",
    "commit", "rollback", "bulk_insert_mappings",
    "bulk_update_mappings", "bulk_save_objects",
    "execute",  # overridden below to allow SELECT-only
})


class ReadOnlySession:
    """
    Strict read-only proxy around a SQLAlchemy Session.

    The AI chatbot (ReAct agent) is allowed to READ inventory data but must
    NEVER modify it.  This proxy enforces that rule structurally — any tool
    function that calls a mutating method will raise RuntimeError immediately,
    before a single byte reaches the database.

    Allowed:  .query(), .execute(SELECT …)
    Blocked:  .add(), .delete(), .commit(), .flush(), .execute(INSERT/UPDATE/DELETE …)
    """

    def __init__(self, session: Session) -> None:
        object.__setattr__(self, "_session", session)

    # Passthrough for read operations

    def query(self, *args, **kwargs):
        return object.__getattribute__(self, "_session").query(*args, **kwargs)

    def execute(self, statement, *args, **kwargs):
        """Allow SELECT-like statements; block INSERT / UPDATE / DELETE."""
        stmt_text = str(statement).strip().upper()
        if any(stmt_text.startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER")):
            raise RuntimeError(
                "[ReadOnlySession] The AI agent attempted a write operation via execute(). "
                "Agent tools must never modify inventory data."
            )
        return object.__getattribute__(self, "_session").execute(statement, *args, **kwargs)

    # Block all mutating methods

    def __getattr__(self, name: str):
        if name in _WRITE_METHODS:
            def _blocked(*args, **kwargs):
                raise RuntimeError(
                    f"[ReadOnlySession] The AI agent attempted to call Session.{name}(). "
                    f"Agent tools must never modify inventory data. "
                    f"Use a dedicated service endpoint for write operations."
                )
            return _blocked
        # Delegate safe attributes (e.g. .bind, .info) to the real session
        return getattr(object.__getattribute__(self, "_session"), name)

    def __setattr__(self, name: str, value) -> None:
        raise RuntimeError(
            f"[ReadOnlySession] Attempted to set attribute '{name}' on a read-only session."
        )



# ContextVar is the correct mechanism here: copy_context() in agent_service.py
# propagates ContextVars into the ThreadPoolExecutor worker thread.
# threading.local does NOT cross thread boundaries, so tools would get db=None.
_db_session_var: contextvars.ContextVar = contextvars.ContextVar(
    "db_session", default=None
)
_org_id_var: contextvars.ContextVar = contextvars.ContextVar(
    "agent_org_id", default=None
)


def set_db_session(db: Session, org_id: Optional[int] = None) -> None:
    """
    Bind a read-only view of the DB session and tenant org_id into the current context.

    The session is wrapped in ReadOnlySession so agent @tool functions
    can query inventory data but can NEVER commit, add, delete, or flush.
    This is a structural guardrail — violations raise RuntimeError before
    any SQL reaches the database.
    """
    _db_session_var.set(ReadOnlySession(db))
    _org_id_var.set(org_id)


def _get_db() -> Optional["ReadOnlySession"]:
    """Return the read-only DB proxy for the current context."""
    return _db_session_var.get()


def _get_org_id() -> Optional[int]:
    """Return the tenant org_id for the current agent context."""
    return _org_id_var.get()


def _no_data_message(message: str) -> List[Dict[str, Any]]:
    return [{"info": message}]


@tool
def get_inventory_overview() -> Dict[str, Any]:
    """Get a high-level overview of inventory: location, item, and transaction counts."""
    db = _get_db()
    if not db:
        return {"error": "Database not connected"}

    try:
        org_id = _get_org_id()
        loc_q = db.query(Location)
        item_q = db.query(Item)
        tx_q = db.query(InventoryTransaction).join(Location, InventoryTransaction.location_id == Location.id)

        if org_id is not None:
            loc_q = loc_q.filter(Location.org_id == org_id)
            item_q = item_q.filter(Item.org_id == org_id)
            tx_q = tx_q.filter(Location.org_id == org_id)

        locations_count = loc_q.count()
        items_count = item_q.count()
        transactions_count = tx_q.count()
        min_date, max_date = tx_q.with_entities(
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

        org_id = _get_org_id()
        alerts = get_critical_alerts(db, severity, org_id=org_id)

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


# Medicine Brand & Generic Salt Synonym Mapping
_GENERIC_TO_BRANDS = {
    "paracetamol": ["dolo", "combiflam", "calpol", "crocin", "paracetamol"],
    "acetaminophen": ["dolo", "combiflam", "calpol", "crocin"],
    "ibuprofen": ["combiflam", "brufen"],
    "pantoprazole": ["pan-d", "pantocid"],
    "domperidone": ["pan-d"],
    "amoxicillin": ["augmentin"],
    "clavulanate": ["augmentin"],
    "azithromycin": ["azithral"],
    "ciprofloxacin": ["ciplox"],
    "telmisartan": ["telma"],
    "metformin": ["glycomet"],
    "glimepiride": ["glycomet"],
    "aspirin": ["ecosprin"],
    "thyroxine": ["thyronorm"],
    "montelukast": ["montair"],
    "levocetirizine": ["montair"],
    "fexofenadine": ["allegra"],
    "salbutamol": ["ascoril"],
    "ambroxol": ["ascoril"],
    "xylometazoline": ["otrivin"],
    "calcium": ["shelcal"],
    "vitamin d": ["shelcal"],
    "vitamin b": ["becosules"],
    "b-complex": ["becosules"],
    "ors": ["electral"],
    "povidone": ["betadine"],
    "iodine": ["betadine"],
    "insulin": ["insulin lantus"],
    "vaccine": ["covaxin"],
}

_CATEGORY_SYNONYMS = {
    "fever": "analgesics",
    "pain": "analgesics",
    "painkiller": "analgesics",
    "painkillers": "analgesics",
    "antibiotic": "antibiotics",
    "antibiotics": "antibiotics",
    "stomach": "gastro",
    "acidity": "gastro",
    "heart": "cardiac",
    "blood pressure": "cardiac",
    "bp": "cardiac",
    "sugar": "diabetes",
    "cold": "respiratory",
    "cough": "respiratory",
    "allergy": "anti-allergic",
    "refrigerated": "cold chain",
}


def _match_medicine(item_name: str, category: str, query: str) -> bool:
    """Intelligently match medicine by exact name, partial token, generic salt alias, or category."""
    if not query or not query.strip():
        return True
    q = query.lower().strip()
    name = (item_name or "").lower()
    cat = (category or "").lower()

    # 1. Direct substring
    if q in name or q in cat:
        return True

    # 2. Token-wise check
    tokens = [t for t in q.replace("-", " ").split() if len(t) > 1]
    if tokens and all(t in name or t in cat for t in tokens):
        return True

    # 3. Generic salt alias check
    for generic, brands in _GENERIC_TO_BRANDS.items():
        if generic in q or q in generic:
            if any(b in name for b in brands):
                return True

    # 4. Category synonym check
    for syn, mapped_cat in _CATEGORY_SYNONYMS.items():
        if syn in q and mapped_cat in cat:
            return True

    return False


@tool
def get_stock_health(item: str = "", location: str = "") -> List[Dict[str, Any]]:
    """Get current stock health across all locations and items, with intelligent medicine/location filters."""
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        org_id = _get_org_id()
        stock_health = get_latest_stock_health(db, org_id=org_id)

        if item and item.strip():
            stock_health = [
                s for s in stock_health if _match_medicine(s.item_name, s.category, item)
            ]

        if location and location.strip():
            stock_health = [
                s for s in stock_health if location.lower().strip() in s.location_name.lower()
            ]

        if not stock_health:
            return _no_data_message("No stock health data found for the given filters.")

        results = []
        for item_data in stock_health[:30]:
            try:
                days_rem = float(item_data.days_remaining) if item_data.days_remaining != 999 else "Plenty"
                if isinstance(days_rem, float):
                    days_rem = round(days_rem, 1)
            except (ValueError, TypeError):
                days_rem = "Plenty"

            try:
                daily_use = float(item_data.avg_daily_usage or 0.0)
            except (ValueError, TypeError):
                daily_use = 0.0

            results.append(
                {
                    "location": item_data.location_name,
                    "item": item_data.item_name,
                    "category": item_data.category,
                    "current_stock": int(item_data.current_stock or 0),
                    "days_remaining": days_rem,
                    "status": str(item_data.health_status),
                    "daily_usage": round(daily_use, 1),
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
        org_id = _get_org_id()
        critical = get_critical_alerts(db, "CRITICAL", org_id=org_id)

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
            avg_usage = float(item.avg_daily_usage or 0.0)
            lead_days = int(item.lead_time_days or 2)
            cur_stock = int(item.current_stock or 0)
            reorder_qty = calculate_reorder_quantity(
                avg_daily_usage=avg_usage,
                lead_time_days=lead_days,
                current_stock=cur_stock,
            )

            try:
                days_rem = float(item.days_remaining) if item.days_remaining is not None and item.days_remaining != "N/A" else 999.0
            except (ValueError, TypeError):
                days_rem = 999.0

            suggestions.append(
                {
                    "location": item.location_name,
                    "item": item.item_name,
                    "current_stock": cur_stock,
                    "recommended_quantity": reorder_qty,
                    "urgency": "HIGH" if days_rem < 1.0 else ("MEDIUM" if days_rem < 3.0 else "LOW"),
                    "reasoning": f"Daily usage: {round(avg_usage, 1)} units, Lead time: {lead_days} days",
                }
            )

        return suggestions
    except Exception as e:
        return [{"error": f"Failed to calculate reorder suggestions: {str(e)}"}]



@tool
def get_location_summary(location_name: str) -> Dict[str, Any]:
    """Get a health summary for a specific location by name."""
    db = _get_db()
    if not db:
        return {"error": "Database not connected"}

    try:
        org_id = _get_org_id()
        stock_health = get_latest_stock_health(db, org_id=org_id)

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
    """Analyze stock health for items in a specific category (e.g. Antibiotics, Gastro, Analgesics, Cardiac)."""
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        org_id = _get_org_id()
        stock_health = get_latest_stock_health(db, org_id=org_id)

        category_data = [
            s for s in stock_health if _match_medicine(s.item_name, s.category, category)
        ]

        if not category_data:
            return [{"error": f"No data found for category: {category}"}]

        results = []
        for item in category_data[:20]:
            try:
                days_rem = float(item.days_remaining) if item.days_remaining != 999 else "Plenty"
                if isinstance(days_rem, float):
                    days_rem = round(days_rem, 1)
            except (ValueError, TypeError):
                days_rem = "Plenty"

            results.append(
                {
                    "item": item.item_name,
                    "location": item.location_name,
                    "status": str(item.health_status),
                    "current_stock": int(item.current_stock or 0),
                    "days_remaining": days_rem,
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

        # Resolve matching items using synonym expansion (scoped by org_id)
        org_id = _get_org_id()
        matching_item_ids = None
        if item and item.strip():
            items_q = db.query(Item)
            if org_id is not None:
                items_q = items_q.filter(Item.org_id == org_id)
            all_items = items_q.all()
            matching_item_ids = [
                it.id for it in all_items if _match_medicine(it.name, it.category, item)
            ]
            if not matching_item_ids:
                return {"info": f"No medicines found matching '{item}'."}

        query = (
            db.query(
                InventoryTransaction.date.label("date"),
                func.sum(InventoryTransaction.issued).label("issued"),
            )
            .join(Location, InventoryTransaction.location_id == Location.id)
            .join(Item, InventoryTransaction.item_id == Item.id)
            .filter(InventoryTransaction.date >= start_date)
        )

        if org_id is not None:
            query = query.filter(Location.org_id == org_id)

        if matching_item_ids is not None:
            query = query.filter(InventoryTransaction.item_id.in_(matching_item_ids))

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


# Pharmacy-Specific Tools

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
        org_id = _get_org_id()
        cutoff = date.today() + timedelta(days=days)
        q = (
            db.query(InventoryTransaction)
            .join(Item, InventoryTransaction.item_id == Item.id)
            .join(Location, InventoryTransaction.location_id == Location.id)
            .filter(
                InventoryTransaction.expiry_date != None,
                InventoryTransaction.expiry_date <= cutoff,
                InventoryTransaction.received > 0,  # Only inbound batches
            )
        )
        if org_id is not None:
            q = q.filter(Location.org_id == org_id)

        rows = (
            q.order_by(InventoryTransaction.expiry_date.asc())
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
        org_id = _get_org_id()
        items_q = db.query(Item).filter(Item.storage_temp == "cold_chain")
        if org_id is not None:
            items_q = items_q.filter(Item.org_id == org_id)

        items = (
            items_q
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
                .join(Location, InventoryTransaction.location_id == Location.id)
                .filter(InventoryTransaction.item_id == item.id)
            )
            if org_id is not None:
                tx_query = tx_query.filter(Location.org_id == org_id)
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


@tool
def search_medicines(query: str = "", category: str = "", storage_temp: str = "") -> List[Dict[str, Any]]:
    """
    Search medicines in the pharmacy catalog by brand name, generic salt, barcode, or category.
    Returns item name, category, strength, unit, MRP, purchase rate, barcode, and storage temperature.
    """
    db = _get_db()
    if not db:
        return [{"error": "Database not connected"}]

    try:
        org_id = _get_org_id()
        q = db.query(Item)
        if org_id is not None:
            q = q.filter(Item.org_id == org_id)
        if storage_temp and storage_temp.strip():
            q = q.filter(Item.storage_temp == storage_temp.strip().lower())

        all_items = q.order_by(Item.name.asc()).all()
        matching_items = []

        for it in all_items:
            # Check category filter if provided
            if category and category.strip():
                if not _match_medicine(it.name, it.category, category):
                    continue

            # Check query filter if provided
            if query and query.strip():
                if not _match_medicine(it.name, it.category, query):
                    continue

            matching_items.append(it)

        if not matching_items:
            return [{"info": f"No medicines found matching '{query}'"}]

        return [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "strength": item.strength or "N/A",
                "unit": item.unit,
                "barcode": item.barcode or "N/A",
                "mrp": getattr(item, "mrp", 0.0),
                "purchase_rate": getattr(item, "purchase_rate", 0.0),
                "storage_temp": item.storage_temp,
                "min_stock": item.min_stock,
            }
            for item in matching_items[:30]
        ]
    except Exception as e:
        return [{"error": str(e)}]


