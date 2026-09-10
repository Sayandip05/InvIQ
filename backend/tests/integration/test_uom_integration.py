import pytest

pytestmark = pytest.mark.skip(reason="Packaging removed from inventory per user requirement")

from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.models import User, Location, Item, ItemPackaging, InventoryTransaction, Organization
from tests.conftest import get_auth_header


@pytest.fixture
def setup_uom_env(db, admin_user):
    client = TestClient(app)

    # 1. Ensure Org 1
    org = db.query(Organization).filter(Organization.id == 1).first()
    if not org:
        org = Organization(
            id=1,
            name="Main UOM Pharmacy",
            slug="main-uom-pharmacy",
            plan="single_pharmacy",
            settings={"discount_model": "none"}
        )
        db.add(org)
    db.commit()

    # 2. Ensure admin user has org_id 1
    admin_user["user"].org_id = 1
    db.commit()

    # 3. Create Location 77
    loc = db.query(Location).filter(Location.id == 77).first()
    if not loc:
        loc = Location(
            id=77,
            org_id=1,
            name="UOM Dispense Counter 77",
            type="retail_counter",
            region="North",
        )
        db.add(loc)
        db.commit()

    headers = get_auth_header(client, admin_user["username"], admin_user["password"])
    return client, headers, loc


def test_uom_packaging_endpoints_and_dispense(setup_uom_env, db):
    client, headers, loc = setup_uom_env

    # 1. Create Item 770
    item = db.query(Item).filter(Item.id == 770).first()
    if not item:
        item = Item(
            id=770,
            name="Paracetamol UOM Test 770",
            category="analgesics",
            unit="tablet",
            barcode="8901000000770",
            mrp=5.0,
            purchase_rate=3.0,
            min_stock=50,
            org_id=1,
        )
        db.add(item)
        db.commit()

    # 2. Add Packaging Tiers via API
    # 2a. Strip (10 tabs, MRP 48, barcode 8901000007710)
    strip_res = client.post(
        f"/api/inventory/items/{item.id}/packagings",
        headers=headers,
        json={
            "unit_name": "strip",
            "multiplier": 10,
            "barcode": "8901000007710",
            "mrp": 48.0,
            "purchase_rate": 28.0,
            "is_default_dispense": True,
        }
    )
    assert strip_res.status_code == 200
    strip_data = strip_res.json()["data"]
    assert strip_data["unit_name"] == "strip"
    assert strip_data["multiplier"] == 10
    assert strip_data["mrp"] == 48.0

    # 2b. Box (100 tabs, MRP 450, barcode 89010000077100)
    box_res = client.post(
        f"/api/inventory/items/{item.id}/packagings",
        headers=headers,
        json={
            "unit_name": "box",
            "multiplier": 100,
            "barcode": "89010000077100",
            "mrp": 450.0,
            "purchase_rate": 250.0,
        }
    )
    assert box_res.status_code == 200

    # 3. List Packagings
    list_res = client.get(f"/api/inventory/items/{item.id}/packagings", headers=headers)
    assert list_res.status_code == 200
    pkgs = list_res.json()["data"]
    assert len(pkgs) >= 2

    # 4. Add initial stock: 500 base tablets
    from app.application.inventory_service import InventoryService
    from app.infrastructure.database.inventory_repo import InventoryRepository
    inv_service = InventoryService(InventoryRepository(db))

    inv_service.add_transaction(
        location_id=loc.id,
        item_id=item.id,
        transaction_date=date.today(),
        received=500,
        issued=0,
        notes="Opening stock in base tablets",
        batch_number="BT-UOM-770",
        expiry_date=date(2028, 1, 1),
    )

    # 5. Dispense 2 STRIPS by scanning strip barcode (8901000007710)
    disp_res = client.post(
        "/api/inventory/scan-dispense",
        headers=headers,
        json={
            "barcode": "8901000007710",
            "location_id": loc.id,
            "quantity": 2,
        }
    )
    assert disp_res.status_code == 200
    d_data = disp_res.json()["data"]
    assert d_data["packaging_unit"] == "strip"
    assert d_data["multiplier"] == 10
    assert d_data["dispensed_quantity"] == 2
    assert d_data["base_quantity_dispensed"] == 20  # 2 * 10 = 20 tablets
    assert d_data["remaining_stock"] == 480         # 500 - 20 = 480 tablets

    # 6. Dispense 1 BOX by specifying unit="box"
    disp_box = client.post(
        "/api/inventory/scan-dispense",
        headers=headers,
        json={
            "barcode": item.barcode,
            "location_id": loc.id,
            "quantity": 1,
            "unit": "box",
        }
    )
    assert disp_box.status_code == 200
    b_data = disp_box.json()["data"]
    assert b_data["packaging_unit"] == "box"
    assert b_data["multiplier"] == 100
    assert b_data["base_quantity_dispensed"] == 100
    assert b_data["remaining_stock"] == 380         # 480 - 100 = 380 tablets


def test_uom_billing_cart_flow(setup_uom_env, db):
    client, headers, loc = setup_uom_env

    # 1. Create Item 880
    item = db.query(Item).filter(Item.id == 880).first()
    if not item:
        item = Item(
            id=880,
            name="Paracetamol Cart 880",
            category="analgesics",
            unit="tablet",
            barcode="8901000000880",
            mrp=5.0,
            purchase_rate=3.0,
            min_stock=50,
            org_id=1,
        )
        db.add(item)
        db.commit()

        pkg_strip = ItemPackaging(
            item_id=item.id,
            org_id=1,
            unit_name="strip",
            multiplier=10,
            barcode="8901000008810",
            mrp=48.0,
            purchase_rate=28.0,
            is_default_dispense=True,
        )
        db.add(pkg_strip)
        db.commit()

    # 2. Add stock: 200 base tablets
    from app.application.inventory_service import InventoryService
    from app.infrastructure.database.inventory_repo import InventoryRepository
    inv_service = InventoryService(InventoryRepository(db))

    inv_service.add_transaction(
        location_id=loc.id,
        item_id=item.id,
        transaction_date=date.today(),
        received=200,
        issued=0,
        notes="Opening stock for cart test",
        batch_number="BT-CART-880",
        expiry_date=date(2028, 1, 1),
    )

    # 3. Open billing session
    open_res = client.post("/api/billing/sessions", headers=headers, json={"location_id": loc.id})
    assert open_res.status_code == 200
    session_id = open_res.json()["data"]["session_id"]

    # 4. Scan 1 strip (barcode 8901000008810)
    scan_res = client.post(
        f"/api/billing/sessions/{session_id}/scan",
        headers=headers,
        json={"barcode": "8901000008810", "quantity": 1, "location_id": loc.id}
    )
    assert scan_res.status_code == 200
    items = scan_res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["packaging_unit"] == "strip"
    assert items[0]["multiplier"] == 10
    assert items[0]["base_qty_deducted"] == 10
    assert items[0]["mrp"] == 48.0
    assert items[0]["line_total"] == 48.0

    # 5. Cancel session -> verifies 10 base tablets are restored
    stock_before = db.query(InventoryTransaction).filter(
        InventoryTransaction.location_id == loc.id,
        InventoryTransaction.item_id == item.id
    ).order_by(InventoryTransaction.id.desc()).first().closing_stock

    del_res = client.delete(f"/api/billing/sessions/{session_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["data"]["status"] == "CANCELLED"

    stock_after = db.query(InventoryTransaction).filter(
        InventoryTransaction.location_id == loc.id,
        InventoryTransaction.item_id == item.id
    ).order_by(InventoryTransaction.id.desc()).first().closing_stock

    assert stock_after == stock_before + 10  # 10 tablets returned
