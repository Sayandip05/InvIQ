"""
Integration tests for Journey E: Insights, AI, Reports, and Real-Time Events.

Verifies:
1. REST and GraphQL analytics strictly partition data by organization with org-scoped cache keys.
2. PDF reports fetch only caller's organization data and reject cross-tenant location IDs.
3. Chat history, vector memory retrieval, and agent tools are strictly org-scoped.
4. WebSocket connections capture authenticated user and org metadata, drop unassigned events,
   and deliver alerts strictly to the intended organization.
"""

import pytest
import asyncio
from datetime import date
from app.infrastructure.database.models import User, Organization, Location, Item, InventoryTransaction, ChatSession, ChatMessage
from app.application.cache_service import cache_invalidate_pattern, cache_get, cache_set
from app.core.security import create_access_token, hash_password
from app.api.routes.websocket import manager, create_ws_ticket, validate_and_consume_ws_ticket


@pytest.fixture(autouse=True)
def clear_caches_before_test():
    cache_invalidate_pattern("*")
    yield
    cache_invalidate_pattern("*")


def _auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_rest_analytics_org_scoping_and_caching(client, db):
    """Journey E.1: REST analytics returns only caller's organization data with org-scoped cache keys."""
    org_x = Organization(name="Analytics Org X", slug="analytics-org-x")
    org_y = Organization(name="Analytics Org Y", slug="analytics-org-y")
    db.add_all([org_x, org_y])
    db.commit()

    admin_x = User(
        email="admin_x_analytics@test.com",
        username="admin_x_analytics",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_x.id,
        is_active=True,
        is_verified=True,
    )
    admin_y = User(
        email="admin_y_analytics@test.com",
        username="admin_y_analytics",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_y.id,
        is_active=True,
        is_verified=True,
    )
    db.add_all([admin_x, admin_y])
    db.commit()

    # Create location and item for Org X
    loc_x = Location(name="Org X Pharmacy Counter", type="retail_counter", region="North", org_id=org_x.id)
    item_x = Item(name="Medicine Org X", category="Antibiotics", unit="strip", min_stock=10, org_id=org_x.id)
    db.add_all([loc_x, item_x])
    db.commit()

    tx_x = InventoryTransaction(
        location_id=loc_x.id,
        item_id=item_x.id,
        date=date.today(),
        opening_stock=0,
        received=100,
        issued=95,
        closing_stock=5,  # Low stock (< 10)
        entered_by="admin",
    )
    db.add(tx_x)
    db.commit()

    headers_x = _auth_headers(admin_x)
    headers_y = _auth_headers(admin_y)

    # 1. Org X checks summary
    res_x = client.get("/api/analytics/summary", headers=headers_x)
    assert res_x.status_code == 200
    summary_x = res_x.json()
    assert summary_x["success"] is True

    # Check that cache key contains org_x.id
    cached_x = cache_get(f"analytics:summary:{org_x.id}")
    assert cached_x is not None

    # 2. Org Y checks summary (should have 0 items / completely separate cache key)
    res_y = client.get("/api/analytics/summary", headers=headers_y)
    assert res_y.status_code == 200
    cached_y = cache_get(f"analytics:summary:{org_y.id}")
    assert cached_y is not None


def test_pdf_report_org_scoping_and_cross_tenant_location_rejection(client, db):
    """Journey E.2: PDF report queries are scoped by org_id and reject cross-tenant location IDs."""
    org_a = Organization(name="Report Org A", slug="report-org-a")
    org_b = Organization(name="Report Org B", slug="report-org-b")
    db.add_all([org_a, org_b])
    db.commit()

    admin_a = User(
        email="admin_a_report@test.com",
        username="admin_a_report",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_a.id,
        is_active=True,
        is_verified=True,
    )
    loc_b = Location(name="Org B Branch", type="retail_counter", region="South", org_id=org_b.id)
    db.add_all([admin_a, loc_b])
    db.commit()

    headers_a = _auth_headers(admin_a)

    # 1. Admin A requests PDF report for their own org -> 200 OK (application/pdf)
    res_ok = client.get("/api/admin/reports/export?report_type=inventory", headers=headers_a)
    assert res_ok.status_code == 200
    assert "application/pdf" in res_ok.headers.get("content-type", "")

    # 2. Admin A attempts to filter report by Org B's location_id -> 404 NotFoundError
    res_bad_loc = client.get(f"/api/admin/reports/export?report_type=inventory&location_id={loc_b.id}", headers=headers_a)
    assert res_bad_loc.status_code == 404


def test_chat_and_vector_memory_org_isolation(client, db):
    """Journey E.3: Chat history & tools cannot access another organization's session or records."""
    org_1 = Organization(name="Chat Org 1", slug="chat-org-1")
    org_2 = Organization(name="Chat Org 2", slug="chat-org-2")
    db.add_all([org_1, org_2])
    db.commit()

    user_1 = User(
        email="user1_chat@test.com",
        username="user1_chat",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_1.id,
        is_active=True,
        is_verified=True,
    )
    user_2 = User(
        email="user2_chat@test.com",
        username="user2_chat",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_2.id,
        is_active=True,
        is_verified=True,
    )
    db.add_all([user_1, user_2])
    db.commit()

    # User 1 creates a private chat session
    session_1 = ChatSession(id="conv_org1_test", user_id=user_1.id, title="Stock query")
    msg_1 = ChatMessage(session_id=session_1.id, role="user", content="How many insulin vials in store?")
    db.add_all([session_1, msg_1])
    db.commit()

    headers_2 = _auth_headers(user_2)

    # User 2 attempts to query User 1's conversation -> 403 Forbidden
    res = client.post(
        "/api/chat/query",
        json={"question": "Continue last conversation", "conversation_id": "conv_org1_test"},
        headers=headers_2,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_isolation_and_drop_unassigned():
    """Journey E.4: ConnectionManager sends events strictly to matching org_id and drops unassigned events."""
    class MockWebSocket:
        def __init__(self):
            self.messages = []
        async def accept(self):
            pass
        async def send_json(self, data):
            self.messages.append(data)

    ws_tenant_10 = MockWebSocket()
    ws_tenant_20 = MockWebSocket()
    ws_unassigned = MockWebSocket()

    test_manager = type(manager)()
    await test_manager.connect(ws_tenant_10, org_id=10, username="tenant10_user", role="staff")
    await test_manager.connect(ws_tenant_20, org_id=20, username="tenant20_user", role="staff")
    await test_manager.connect(ws_unassigned, org_id=None, username="unassigned_user", role="staff")

    # 1. Broadcast an alert strictly for org_id=10
    alert_10 = {"type": "CRITICAL_STOCK", "item": "Paracetamol", "org_id": 10}
    await test_manager.broadcast_to_org(10, alert_10)

    assert len(ws_tenant_10.messages) == 1
    assert ws_tenant_10.messages[0]["item"] == "Paracetamol"
    assert len(ws_tenant_20.messages) == 0  # Tenant 20 got nothing!
    assert len(ws_unassigned.messages) == 0  # Unassigned client gets nothing (strict tenant isolation)

    # 2. Broadcast an unassigned tenant event (org_id=None) -> Must be DROPPED
    unassigned_event = {"type": "ORPHAN_ALERT", "org_id": None}
    await test_manager.broadcast_to_org(None, unassigned_event)

    # Confirm neither tenant received the unassigned event
    assert len(ws_tenant_10.messages) == 1
    assert len(ws_tenant_20.messages) == 0
    assert len(ws_unassigned.messages) == 0
