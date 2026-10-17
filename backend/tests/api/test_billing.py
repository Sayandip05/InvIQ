import pytest
from datetime import date
from app.infrastructure.database.models import Item, Location, Organization, User, InventoryTransaction, BillingSession
from tests.conftest import get_auth_header


@pytest.fixture
def setup_billing_env(db, admin_user):
    # Ensure Org 1 exists
    org = db.query(Organization).filter(Organization.id == 1).first()
    if not org:
        org = Organization(
            id=1,
            name="Main Test Pharmacy",
            slug="main-test-pharmacy",
            plan="single_pharmacy",
            settings={
                "discount_model": "flat",
                "flat_discount_pct": 10.0,
            }
        )
        db.add(org)
    else:
        org.settings = {
            "discount_model": "flat",
            "flat_discount_pct": 10.0,
        }
    db.commit()

    # Create location
    loc = db.query(Location).filter(Location.id == 10).first()
    if not loc:
        loc = Location(
            id=10,
            org_id=1,
            name="Billing Counter 1",
            type="retail_counter",
            region="East",
        )
        db.add(loc)
        db.commit()

    # Create item with barcode and stock
    item = db.query(Item).filter(Item.id == 100).first()
    if not item:
        item = Item(
            id=100,
            org_id=1,
            name="Paracetamol 500mg",
            category="Tablet",
            unit="strip",
            barcode="8901234567890",
            mrp=50.0,
            purchase_rate=30.0,
            min_stock=5,
        )
        db.add(item)
        db.commit()

    # Add initial stock
    tx = db.query(InventoryTransaction).filter(
        InventoryTransaction.location_id == 10,
        InventoryTransaction.item_id == 100
    ).first()
    if not tx:
        tx = InventoryTransaction(
            location_id=10,
            item_id=100,
            org_id=1,
            date=date.today(),
            opening_stock=0,
            received=100,
            issued=0,
            closing_stock=100,
            entered_by="system",
            batch_number="BATCH-A1",
            expiry_date=date(2027, 12, 31),
        )
        db.add(tx)
        db.commit()

    return {"org": org, "location": loc, "item": item}


def test_billing_session_lifecycle(client, db, admin_user, setup_billing_env):
    auth_header = get_auth_header(client, "testadmin", "adminpass123")

    # 1. Open billing session
    res = client.post("/api/billing/sessions", json={"location_id": 10}, headers=auth_header)
    assert res.status_code == 200, res.text
    session_data = res.json()["data"]
    session_id = session_data["session_id"]
    assert session_data["status"] == "OPEN"
    assert session_data["location_id"] == 10

    # 2. Scan item into bill
    scan_res = client.post(
        f"/api/billing/sessions/{session_id}/scan",
        json={"barcode": "8901234567890", "quantity": 2, "location_id": 10},
        headers=auth_header,
    )
    assert scan_res.status_code == 200, scan_res.text
    cart_data = scan_res.json()["data"]
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["item_name"] == "Paracetamol 500mg"
    assert cart_data["items"][0]["line_total"] == 100.0  # 2 * 50.0

    # Check preview discount (10% flat)
    preview = cart_data["billing_preview"]
    assert preview["gross_total"] == 100.0
    assert preview["discount_pct"] == 10.0
    assert preview["discount_amount"] == 10.0
    assert preview["net_total"] == 90.0

    # 3. Checkout bill
    checkout_res = client.post(
        f"/api/billing/sessions/{session_id}/checkout",
        headers=auth_header,
    )
    assert checkout_res.status_code == 200, checkout_res.text
    closed_data = checkout_res.json()["data"]
    assert closed_data["status"] == "CLOSED"
    assert closed_data["billing"]["net_total"] == 90.0
    assert closed_data["purchase_cost"] == 60.0  # 2 * 30.0

    # 4. Verify DB session status
    saved = db.query(BillingSession).filter(BillingSession.id == session_id).first()
    assert saved.status == "CLOSED"
    assert saved.gross_total == 100.0
    assert saved.net_total == 90.0


def test_billing_session_cancel_restores_stock(client, db, admin_user, setup_billing_env):
    auth_header = get_auth_header(client, "testadmin", "adminpass123")

    # 1. Open session
    res = client.post("/api/billing/sessions", json={"location_id": 10}, headers=auth_header)
    session_id = res.json()["data"]["session_id"]

    # 2. Scan item (quantity 5)
    client.post(
        f"/api/billing/sessions/{session_id}/scan",
        json={"barcode": "8901234567890", "quantity": 5, "location_id": 10},
        headers=auth_header,
    )

    # 3. Cancel session
    cancel_res = client.delete(f"/api/billing/sessions/{session_id}", headers=auth_header)
    assert cancel_res.status_code == 200, cancel_res.text
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Verify session is CANCELLED in DB
    saved = db.query(BillingSession).filter(BillingSession.id == session_id).first()
    assert saved.status == "CANCELLED"


def test_admin_discount_settings_endpoints(client, admin_user, setup_billing_env):
    auth_header = get_auth_header(client, "testadmin", "adminpass123")

    # 1. Get current settings
    res = client.get("/api/admin/discount-settings", headers=auth_header)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["discount_model"] == "flat"

    # 2. Update to tiered model
    update_payload = {
        "discount_model": "tiered",
        "flat_discount_pct": 0,
        "tiered_discount_config": [
            {"min_bill": 0, "max_bill": 499, "discount_pct": 0},
            {"min_bill": 500, "max_bill": None, "discount_pct": 10},
        ],
        "manual_discount_cap_pct": 20,
    }
    put_res = client.put("/api/admin/discount-settings", json=update_payload, headers=auth_header)
    assert put_res.status_code == 200, put_res.text
    assert put_res.json()["data"]["discount_model"] == "tiered"

    # 3. Verify get returns new settings
    res2 = client.get("/api/admin/discount-settings", headers=auth_header)
    assert res2.status_code == 200
    assert res2.json()["data"]["discount_model"] == "tiered"
    assert len(res2.json()["data"]["tiered_discount_config"]) == 2


def test_monthly_sales_report_endpoint(client, admin_user, setup_billing_env):
    auth_header = get_auth_header(client, "testadmin", "adminpass123")

    # Get monthly report for current month
    today = date.today()
    res = client.get(f"/api/admin/reports/monthly-sales?year={today.year}&month={today.month}", headers=auth_header)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert "gross_total" in data
    assert "discount_amount" in data
    assert "net_total" in data
    assert "gross_profit" in data
    assert "margin_pct" in data
