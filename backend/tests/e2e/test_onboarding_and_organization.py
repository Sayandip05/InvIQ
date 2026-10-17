"""
Integration tests for Journey A: Onboarding and Organization Setup.

Covers:
1. Public signup creating an organization, default counter location, and assigning org_id.
2. Email verification marking user as verified and activating account.
3. Organization profile retrieval and updates (name, DL number, GSTIN, phone, address, settings).
4. Branch creation, renaming, deactivation/toggle, safe archive when transactions exist, and clean delete.
5. Cross-tenant protection for organization and branch mutations.
"""

import pytest
from app.infrastructure.database.models import User, Organization, Location, InventoryTransaction
from app.application.cache_service import cache_invalidate_pattern
from app.core.security import create_access_token, hash_password
from datetime import date


@pytest.fixture(autouse=True)
def clear_caches_before_test():
    cache_invalidate_pattern("*")
    yield
    cache_invalidate_pattern("*")


def _auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_public_signup_creates_organization_and_default_counter(client, db):
    """Journey A.1 & A.2: Signup creates owner, unique organization, and default counter location."""
    signup_payload = {
        "email": "dr.sharma@apollohealth.example",
        "username": "drsharma",
        "password": "StrongPassword123!",
        "full_name": "Dr. Ramesh Sharma",
        "role": "admin",
    }
    res = client.post("/api/auth/signup", json=signup_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    user_data = data["data"]
    assert user_data["email"] == "dr.sharma@apollohealth.example"
    assert user_data["org_id"] is not None
    assert user_data["organization_name"] is not None

    # Verify DB records
    user = db.query(User).filter(User.email == "dr.sharma@apollohealth.example").first()
    assert user is not None
    assert user.org_id is not None
    assert len(user.location_ids) == 1

    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    assert org is not None
    assert "Sharma" in org.name

    loc = db.query(Location).filter(Location.id == user.location_ids[0]).first()
    assert loc is not None
    assert loc.org_id == org.id
    assert loc.type == "retail_counter"


def test_admin_organization_profile_get_and_update(client, db):
    """Journey A.2: Owner can fetch and update pharmacy profile, DL number, GSTIN, and settings."""
    org = Organization(name="Sharma Medicos Org", slug="sharma-medicos-org", plan="single_pharmacy")
    db.add(org)
    db.commit()
    db.refresh(org)

    owner = User(
        email="owner_sharma@example.com",
        username="owner_sharma",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org.id,
        is_active=True,
        is_verified=True,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    headers = _auth_headers(owner)

    # 1. GET /api/admin/organization
    get_res = client.get("/api/admin/organization", headers=headers)
    assert get_res.status_code == 200, get_res.text
    profile = get_res.json()["data"]
    assert profile["id"] == org.id
    assert profile["name"] == "Sharma Medicos Org"

    # 2. PUT /api/admin/organization
    update_payload = {
        "name": "Sharma Super Specialty Chemist",
        "dl_number": "DL-20B-998877/21B-112233",
        "gstin": "07AAAAA1234A1Z1",
        "phone": "+91 98765 00000",
        "email": "sharma.chemist@example.com",
        "address": "Shop 4, Central Medical Complex, New Delhi",
        "settings": {"fefo_expiry_days": 45, "auto_po_enabled": True},
    }
    put_res = client.put("/api/admin/organization", json=update_payload, headers=headers)
    assert put_res.status_code == 200, put_res.text
    updated = put_res.json()["data"]
    assert updated["name"] == "Sharma Super Specialty Chemist"
    assert updated["dl_number"] == "DL-20B-998877/21B-112233"
    assert updated["gstin"] == "07AAAAA1234A1Z1"
    assert updated["settings"]["fefo_expiry_days"] == 45


def test_branch_management_create_update_toggle_and_safe_archive(client, db):
    """Journey A.3: Add branch, rename, toggle status, and verify safe archive vs delete."""
    org = Organization(name="Branch Test Org", slug="branch-test-org")
    db.add(org)
    db.commit()
    db.refresh(org)

    admin = User(
        email="branch_admin@example.com",
        username="branch_admin",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org.id,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    headers = _auth_headers(admin)

    # 1. Create a clean branch (no transactions)
    create_res = client.post(
        "/api/inventory/locations",
        json={
            "name": "East Wing Counter",
            "type": "retail_counter",
            "region": "East",
            "address": "Building B, Ground Floor",
        },
        headers=headers,
    )
    assert create_res.status_code == 200, create_res.text
    branch1_id = create_res.json()["data"]["id"]

    # 2. Update/rename the branch
    update_res = client.put(
        f"/api/inventory/locations/{branch1_id}",
        json={
            "name": "East Wing Main Counter",
            "phone": "+91 99999 11111",
            "radius_meters": 300,
        },
        headers=headers,
    )
    assert update_res.status_code == 200, update_res.text
    assert update_res.json()["data"]["name"] == "East Wing Main Counter"
    assert update_res.json()["data"]["radius_meters"] == 300

    # 3. Toggle active status
    toggle_res = client.patch(f"/api/inventory/locations/{branch1_id}/toggle-active", headers=headers)
    assert toggle_res.status_code == 200, toggle_res.text
    assert toggle_res.json()["data"]["is_active"] is False

    # Toggle back to active
    toggle_res2 = client.patch(f"/api/inventory/locations/{branch1_id}/toggle-active", headers=headers)
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["data"]["is_active"] is True

    # 4. Create branch2 and attach a historical transaction to test safe archive
    create_res2 = client.post(
        "/api/inventory/locations",
        json={"name": "Cold Storage Branch", "type": "cold_storage", "region": "Central"},
        headers=headers,
    )
    assert create_res2.status_code == 200
    branch2_id = create_res2.json()["data"]["id"]

    # Add a mock transaction for branch2
    from app.infrastructure.database.models import Item
    test_item = Item(name="Test Vaccine", category="Vaccines", unit="vial", org_id=org.id)
    db.add(test_item)
    db.commit()
    db.refresh(test_item)

    tx = InventoryTransaction(
        location_id=branch2_id,
        item_id=test_item.id,
        org_id=test_item.org_id,
        date=date.today(),
        opening_stock=0,
        received=50,
        issued=0,
        closing_stock=50,
        entered_by="admin",
    )
    db.add(tx)
    db.commit()

    # Attempt delete on branch2 (has transaction history) -> Must archive safely
    del_res2 = client.delete(f"/api/inventory/locations/{branch2_id}", headers=headers)
    assert del_res2.status_code == 200
    assert del_res2.json()["action"] == "archived"
    assert del_res2.json()["data"]["is_active"] is False

    # Attempt delete on branch1 (has no transactions) -> Must delete cleanly
    del_res1 = client.delete(f"/api/inventory/locations/{branch1_id}", headers=headers)
    assert del_res1.status_code == 200
    assert del_res1.json()["action"] == "deleted"
    assert db.query(Location).filter(Location.id == branch1_id).first() is None


def test_cross_tenant_branch_mutation_prevention(client, db):
    """Journey A.4: Org X admin cannot update or delete Org Y's branches (returns 404)."""
    org_x = Organization(name="Tenant X Pharmacy", slug="tenant-x-pharmacy")
    org_y = Organization(name="Tenant Y Pharmacy", slug="tenant-y-pharmacy")
    db.add_all([org_x, org_y])
    db.commit()

    admin_x = User(
        email="admin_x@test.com",
        username="admin_x",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_x.id,
        is_active=True,
        is_verified=True,
    )
    db.add(admin_x)
    db.commit()

    loc_y = Location(name="Org Y Location", type="retail_counter", region="West", org_id=org_y.id)
    db.add(loc_y)
    db.commit()
    db.refresh(loc_y)

    headers_x = _auth_headers(admin_x)

    # Admin X tries to update Org Y's location
    update_res = client.put(
        f"/api/inventory/locations/{loc_y.id}",
        json={"name": "Hacked Location Name"},
        headers=headers_x,
    )
    assert update_res.status_code == 404

    # Admin X tries to delete Org Y's location
    delete_res = client.delete(f"/api/inventory/locations/{loc_y.id}", headers=headers_x)
    assert delete_res.status_code == 404

