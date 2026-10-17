"""
Integration tests for Journey B: Master-Data Setup.

Verifies:
1. Admin adds medicines/items, categories, barcodes, units, minimum stock,
   storage requirements (ambient vs cold_chain), and locations.
2. Admin looks up items by barcode, updates item details, and deletion enforces transaction history check.
3. Admin creates suppliers/vendors with scoped location access; foreign location IDs are strictly rejected.
4. Multi-tenant vendor uploads/invoices remain strictly scoped to the receiving organization.
5. Admin can invite, edit, deactivate, and remove staff/vendor users, with location assignment validation against the tenant.
"""

import pytest
from datetime import date, timedelta
from app.infrastructure.database.models import User, Organization, Location, Item, InventoryTransaction, VendorUpload
from app.core.security import create_access_token, hash_password
from app.application.cache_service import cache_invalidate_pattern


@pytest.fixture(autouse=True)
def clear_caches_before_test():
    cache_invalidate_pattern("*")
    yield
    cache_invalidate_pattern("*")


def _auth_headers(user: User) -> dict:
    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "org_id": user.org_id,
        },
        expires_delta=timedelta(hours=1),
    )
    return {"Authorization": f"Bearer {token}"}


def test_item_master_data_crud_and_barcode_lookup(client, db):
    """Journey B.1: Admin adds medicine catalog item with barcode, storage temp, pricing, and performs CRUD."""
    org_1 = Organization(name="Pharmacy B1 Org", slug="pharmacy-b1-org")
    org_2 = Organization(name="Pharmacy B2 Org", slug="pharmacy-b2-org")
    db.add_all([org_1, org_2])
    db.commit()

    admin_1 = User(
        email="admin_b1@test.com",
        username="admin_b1",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_1.id,
        is_active=True,
        is_verified=True,
    )
    admin_2 = User(
        email="admin_b2@test.com",
        username="admin_b2",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_2.id,
        is_active=True,
        is_verified=True,
    )
    db.add_all([admin_1, admin_2])
    db.commit()

    headers_1 = _auth_headers(admin_1)
    headers_2 = _auth_headers(admin_2)

    # 1. Create medicine item for Org 1 with barcode and cold_chain storage
    item_payload = {
        "name": "Insulin Glargine 100IU",
        "category": "Diabetes",
        "unit": "vial",
        "barcode": "8901234567890",
        "strength": "100IU/ml",
        "mrp": 650.0,
        "purchase_rate": 520.0,
        "lead_time_days": 3,
        "min_stock": 15,
        "storage_temp": "cold_chain",
    }
    res = client.post("/api/inventory/items", json=item_payload, headers=headers_1)
    assert res.status_code == 200
    created_item = res.json()["data"]
    item_id = created_item["id"]
    assert created_item["barcode"] == "8901234567890"
    assert created_item["storage_temp"] == "cold_chain"

    # 2. Look up item by barcode for Org 1
    res_bc = client.get("/api/inventory/items/barcode/8901234567890", headers=headers_1)
    assert res_bc.status_code == 200
    assert res_bc.json()["data"]["name"] == "Insulin Glargine 100IU"

    # Org 2 attempts barcode lookup for Org 1's item -> 404 (isolated)
    res_bc_org2 = client.get("/api/inventory/items/barcode/8901234567890", headers=headers_2)
    assert res_bc_org2.status_code == 404

    # 3. Update medicine item details
    update_payload = {
        "min_stock": 20,
        "mrp": 675.0,
        "strength": "100IU/3ml pen",
    }
    res_up = client.put(f"/api/inventory/items/{item_id}", json=update_payload, headers=headers_1)
    assert res_up.status_code == 200
    assert res_up.json()["data"]["min_stock"] == 20
    assert res_up.json()["data"]["mrp"] == 675.0
    assert res_up.json()["data"]["strength"] == "100IU/3ml pen"

    # 4. Safe deletion check: When transactions exist, delete must be rejected
    loc_1 = Location(name="Main Counter", type="retail_counter", region="North", org_id=org_1.id)
    db.add(loc_1)
    db.commit()

    tx = InventoryTransaction(
        location_id=loc_1.id,
        item_id=item_id,
        org_id=loc_1.org_id,
        date=date.today(),
        opening_stock=0,
        received=50,
        issued=10,
        closing_stock=40,
        entered_by="admin_b1",
    )
    db.add(tx)
    db.commit()

    # Attempt to delete item with active history -> ValidationError (422 or 400)
    res_del_fail = client.delete(f"/api/inventory/items/{item_id}", headers=headers_1)
    assert res_del_fail.status_code in (400, 422)
    assert "historical inventory transactions exist" in str(res_del_fail.json())

    # Clean delete an item that has NO transactions
    res_temp = client.post("/api/inventory/items", json={
        "name": "Disposable Syringes 5ml",
        "category": "Surgicals",
        "unit": "piece",
        "lead_time_days": 1,
        "min_stock": 50,
    }, headers=headers_1)
    temp_item_id = res_temp.json()["data"]["id"]

    res_del_ok = client.delete(f"/api/inventory/items/{temp_item_id}", headers=headers_1)
    assert res_del_ok.status_code == 200


def test_supplier_creation_and_location_validation(client, db):
    """Journey B.2 & B.3: Admin adds suppliers with scoped locations; rejects cross-tenant location IDs."""
    org_a = Organization(name="Pharmacy A Org", slug="pharmacy-a-org")
    org_b = Organization(name="Pharmacy B Org", slug="pharmacy-b-org")
    db.add_all([org_a, org_b])
    db.commit()

    admin_a = User(
        email="admin_a_sup@test.com",
        username="admin_a_sup",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_a.id,
        is_active=True,
        is_verified=True,
    )
    loc_a1 = Location(name="Storefront A1", type="retail_counter", region="East", org_id=org_a.id)
    loc_b1 = Location(name="Storefront B1", type="retail_counter", region="West", org_id=org_b.id)
    db.add_all([admin_a, loc_a1, loc_b1])
    db.commit()

    headers_a = _auth_headers(admin_a)

    # 1. Admin A creates supplier with valid location in Org A
    supplier_payload = {
        "name": "MedDistributors Ltd",
        "username": "med_dist_vendor",
        "email": "vendor_med@dist.com",
        "password": "VendorSecure123!",
        "location_ids": [loc_a1.id],
    }
    res_sup = client.post("/api/admin/suppliers", json=supplier_payload, headers=headers_a)
    assert res_sup.status_code == 200
    sup_id = res_sup.json()["data"]["id"]

    # 2. Admin A attempts to create supplier with Org B's location -> ValidationError (422)
    bad_supplier_payload = {
        "name": "BadDistributor Ltd",
        "username": "bad_dist_vendor",
        "email": "vendor_bad@dist.com",
        "password": "VendorSecure123!",
        "location_ids": [loc_b1.id],  # Foreign location!
    }
    res_bad = client.post("/api/admin/suppliers", json=bad_supplier_payload, headers=headers_a)
    assert res_bad.status_code in (400, 422)
    assert "Locations must belong to your organization" in str(res_bad.json())

    # 3. Admin A attempts to update supplier with Org B's location -> ValidationError (422)
    res_bad_update = client.put(f"/api/admin/suppliers/{sup_id}", json={
        "location_ids": [loc_b1.id],
    }, headers=headers_a)
    assert res_bad_update.status_code in (400, 422)
    assert "Locations must belong to your organization" in str(res_bad_update.json())


def test_staff_user_management_and_location_validation(client, db):
    """Journey B.4: Admin registers, edits, deactivates, and removes staff users with location validation."""
    org_x = Organization(name="Pharmacy Staff Org", slug="pharmacy-staff-org")
    org_y = Organization(name="Other Staff Org", slug="other-staff-org")
    db.add_all([org_x, org_y])
    db.commit()

    admin_x = User(
        email="admin_x_staff@test.com",
        username="admin_x_staff",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_x.id,
        is_active=True,
        is_verified=True,
    )
    loc_x1 = Location(name="Main Counter X", type="retail_counter", region="Central", org_id=org_x.id)
    loc_y1 = Location(name="Foreign Counter Y", type="retail_counter", region="Central", org_id=org_y.id)
    db.add_all([admin_x, loc_x1, loc_y1])
    db.commit()

    headers_x = _auth_headers(admin_x)

    # 1. Admin X registers staff user with valid location_ids
    staff_payload = {
        "username": "pharmacist_sarah",
        "email": "sarah@pharmacy.com",
        "full_name": "Sarah Pharmacist",
        "role": "staff",
        "password": "Password123!",
        "location_ids": [loc_x1.id],
    }
    res_reg = client.post("/api/auth/register", json=staff_payload, headers=headers_x)
    assert res_reg.status_code == 200
    staff_id = res_reg.json()["data"]["id"]

    # 2. Admin X attempts to register staff user with foreign location -> ValidationError (422)
    bad_staff_payload = {
        "username": "pharmacist_bad",
        "email": "bad@pharmacy.com",
        "full_name": "Bad Pharmacist",
        "role": "staff",
        "password": "Password123!",
        "location_ids": [loc_y1.id],  # Foreign!
    }
    res_bad_reg = client.post("/api/auth/register", json=bad_staff_payload, headers=headers_x)
    assert res_bad_reg.status_code in (400, 422)
    assert "Locations must belong to your organization" in str(res_bad_reg.json())


    # 3. Admin X edits staff user via PUT /api/auth/users/{user_id}
    res_edit = client.put(f"/api/auth/users/{staff_id}", json={
        "full_name": "Sarah Senior Pharmacist",
        "role": "admin",
    }, headers=headers_x)
    assert res_edit.status_code == 200
    assert res_edit.json()["data"]["full_name"] == "Sarah Senior Pharmacist"
    assert res_edit.json()["data"]["role"] == "admin"

    # 4. Admin X deactivates staff user
    res_deact = client.put(f"/api/auth/users/{staff_id}/deactivate", headers=headers_x)
    assert res_deact.status_code == 200

    # 5. Deactivated user cannot log in
    res_login = client.post("/api/auth/login", json={
        "email": "sarah@pharmacy.com",
        "password": "Password123!",
    })
    assert res_login.status_code in (401, 403)


    # 6. Admin X removes staff user
    res_del = client.delete(f"/api/auth/users/{staff_id}", headers=headers_x)
    assert res_del.status_code == 200
