"""
Tests for Performance Optimizations: Database Indexing, N+1 Query Elimination, Admin Aggregations, and Lookup Caching.
"""

import pytest
from datetime import date
from io import BytesIO
import openpyxl

from app.infrastructure.database.models import (
    InventoryTransaction,
    Requisition,
    RequisitionItem,
    Item,
    Location,
    User,
    ChatMessage,
    AuditLog,
)
from app.application.vendor_service import VendorService
from app.infrastructure.database.audit_repo import AuditRepository
from app.application.cache_service import cache_get, cache_set, cache_invalidate_pattern
from tests.conftest import get_auth_header


def _create_multi_item_excel(items_data: list[tuple[str, int, float]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Deliveries"

    ws.append(["item_name", "quantity_received", "unit_price", "delivery_date", "notes"])
    for name, qty, price in items_data:
        ws.append([name, qty, price, "2026-08-14", "Batch delivery"])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── 1. Model Index Declarations ──────────────────────────────────────────

def test_models_have_indexes_declared():
    """Verify that all required single and composite indexes are defined on ORM tables."""
    inv_tx_index_names = {idx.name for idx in InventoryTransaction.__table__.indexes}
    assert "ix_inv_tx_loc_item_date" in inv_tx_index_names
    assert "ix_inv_tx_item_date" in inv_tx_index_names

    req_index_names = {idx.name for idx in Requisition.__table__.indexes}
    assert "ix_requisitions_status_urgency" in req_index_names
    assert "ix_requisitions_loc_created" in req_index_names

    req_item_index_names = {idx.name for idx in RequisitionItem.__table__.indexes}
    assert "ix_req_items_req_item" in req_item_index_names

    chat_index_names = {idx.name for idx in ChatMessage.__table__.indexes}
    assert "ix_chat_messages_session_created" in chat_index_names

    audit_index_names = {idx.name for idx in AuditLog.__table__.indexes}
    assert "ix_audit_logs_action_created" in audit_index_names

    user_index_names = {idx.name for idx in User.__table__.indexes}
    assert "ix_users_role_active" in user_index_names


# ── 2. N+1 Elimination in Vendor Delivery Ingestion ───────────────────────

def test_vendor_service_prefetched_stock_processing(db):
    """Verify multi-row Excel parsing properly chains opening and closing stocks in-memory."""
    loc = db.query(Location).first()
    if not loc:
        loc = Location(org_id=1, name="Warehouse Beta", type="warehouse", region="West")
        db.add(loc)
        db.commit()

    item = db.query(Item).filter(Item.org_id == loc.org_id).first()
    if not item:
        item = Item(org_id=loc.org_id, name="Ceftriaxone 1g", category="Antibiotics", unit="Vials", lead_time_days=2, min_stock=20)
        db.add(item)
        db.commit()

    vendor = db.query(User).filter(User.role == "vendor").first()
    if not vendor:
        from app.core.security import hash_password
        vendor = User(
            username="pharma_vendor",
            email="vendor@pharma.com",
            hashed_password=hash_password("Vendor123!"),
            role="vendor",
            is_active=True,
        )
        db.add(vendor)
        db.commit()

    # Upload multiple deliveries of the SAME item in one file
    excel_bytes = _create_multi_item_excel([
        (item.name, 10, 100.0),
        (item.name, 15, 100.0),
    ])

    service = VendorService(db)
    res = service.parse_and_process_excel(
        file_content=excel_bytes,
        filename="batch_delivery.xlsx",
        location_id=loc.id,
        vendor_user_id=vendor.id,
    )

    assert res["success"] is True
    assert res["data"]["success"] == 2

    # Query last 2 transactions for this item
    txs = (
        db.query(InventoryTransaction)
        .filter(
            InventoryTransaction.location_id == loc.id,
            InventoryTransaction.item_id == item.id,
        )
        .order_by(InventoryTransaction.id.desc())
        .limit(2)
        .all()
    )

    # Latest tx should have opening = previous closing
    latest_tx = txs[0]
    first_tx = txs[1]
    assert latest_tx.opening_stock == first_tx.closing_stock
    assert latest_tx.closing_stock == first_tx.closing_stock + 15


# ── 3. Admin Overview Consolidated SQL Aggregation ────────────────────────

def test_admin_overview_metrics(client, admin_user):
    headers = get_auth_header(client, admin_user["username"], admin_user["password"])
    res = client.get("/api/admin/overview", headers=headers)
    assert res.status_code == 200

    data = res.json()["data"]
    assert "users" in data
    users_data = data["users"]
    assert users_data["total"] >= 1
    assert users_data["active"] >= 1
    assert "by_role" in users_data
    assert "admin" in users_data["by_role"]


# ── 4. Audit Log SQL-Level Filtering ─────────────────────────────────────

def test_audit_repo_sql_level_filtering(db, admin_user):
    repo = AuditRepository(db)
    repo.create(
        username=admin_user["username"],
        action="UPDATE_STOCK",
        resource_type="inventory",
        resource_id="101",
    )
    repo.create(
        username=admin_user["username"],
        action="DELETE_ITEM",
        resource_type="item",
        resource_id="202",
    )

    filtered_stock = repo.get_filtered(action="UPDATE_STOCK")
    assert len(filtered_stock) >= 1
    assert all(log.action == "UPDATE_STOCK" for log in filtered_stock)

    filtered_item = repo.get_filtered(resource_type="item")
    assert len(filtered_item) >= 1
    assert all(log.resource_type == "item" for log in filtered_item)


# ── 5. Lookup Endpoints Redis Caching ─────────────────────────────────────

def test_inventory_lookup_redis_caching(client, admin_user):
    from unittest.mock import patch

    headers = get_auth_header(client, admin_user["username"], admin_user["password"])
    fake_redis_store = {}

    class MockRedisClient:
        def get(self, key):
            return fake_redis_store.get(key)

        def setex(self, key, ttl, value):
            fake_redis_store[key] = value
            return True

        def delete(self, *keys):
            for k in keys:
                fake_redis_store.pop(k, None)

        def scan(self, cursor=0, match=None, count=100):
            prefix = match.rstrip("*") if match else ""
            matching = [k for k in fake_redis_store if k.startswith(prefix)]
            return 0, matching

    mock_client = MockRedisClient()

    with patch("app.application.cache_service.get_redis", return_value=mock_client), \
         patch("app.infrastructure.cache.redis_client.get_redis", return_value=mock_client):

        # Clear cache before test
        cache_invalidate_pattern("ref:*")

        # 1. First fetch -> should populate cache
        res1 = client.get("/api/inventory/locations", headers=headers)
        assert res1.status_code == 200
        assert cache_get("ref:locations") is not None

        # 2. Second fetch -> serves from cache
        res2 = client.get("/api/inventory/locations", headers=headers)
        assert res2.status_code == 200
        assert res1.json() == res2.json()


        # 3. Create new location -> should invalidate cache
        new_loc_payload = {
            "name": "Super Fast Warehouse",
            "type": "warehouse",
            "region": "South",
            "address": "123 Speed Way",
        }
        create_res = client.post("/api/inventory/locations", json=new_loc_payload, headers=headers)
        assert create_res.status_code == 200

        # Cache should now be invalidated
        assert cache_get("ref:locations") is None

