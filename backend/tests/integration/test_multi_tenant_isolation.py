"""
Comprehensive Multi-Tenant Isolation Test Matrix.

Tests strict multi-tenant boundary enforcement across Org X and Org Y:
- Admin X sees ONLY Org X records
- Admin Y sees ONLY Org Y records
- Cross-tenant access attempts with guessed IDs return 403 Forbidden or 404 Not Found
- Normal users with org_id=None are strictly rejected with 403 Forbidden
- Super admin retains platform-wide access
"""

import pytest
from datetime import date, datetime
from app.infrastructure.database.models import (
    Organization,
    User,
    Location,
    Item,
    InventoryTransaction,
    Requisition,
    RequisitionItem,
    VendorInvoice,
    DataImportJob,
)
from tests.conftest import get_auth_header, hash_password


@pytest.fixture
def multi_tenant_fixture(db):
    """
    Setup complete test environment with Org X and Org Y.
    """
    from app.application.cache_service import cache_invalidate_pattern
    cache_invalidate_pattern("*")

    import uuid
    uid = uuid.uuid4().hex[:6]


    # 1. Organizations
    org_x = Organization(name=f"Org X Pharmacy {uid}", slug=f"org-x-{uid}")
    org_y = Organization(name=f"Org Y Pharmacy {uid}", slug=f"org-y-{uid}")
    db.add_all([org_x, org_y])
    db.commit()
    db.refresh(org_x)
    db.refresh(org_y)

    # 2. Users
    pw_hash = hash_password("SecurePass123!")

    admin_x = User(
        username=f"admin_x_{uid}",
        email=f"admin_x_{uid}@orgx.com",
        hashed_password=pw_hash,
        role="admin",
        org_id=org_x.id,
        is_active=True,
    )
    staff_x = User(
        username=f"staff_x_{uid}",
        email=f"staff_x_{uid}@orgx.com",
        hashed_password=pw_hash,
        role="staff",
        org_id=org_x.id,
        is_active=True,
    )
    admin_y = User(
        username=f"admin_y_{uid}",
        email=f"admin_y_{uid}@orgy.com",
        hashed_password=pw_hash,
        role="admin",
        org_id=org_y.id,
        is_active=True,
    )
    unassigned_user = User(
        username=f"unassigned_{uid}",
        email=f"unassigned_{uid}@example.com",
        hashed_password=pw_hash,
        role="admin",
        org_id=None,
        is_active=True,
    )
    db.add_all([admin_x, staff_x, admin_y, unassigned_user])
    db.commit()
    db.refresh(admin_x)
    db.refresh(staff_x)
    db.refresh(admin_y)
    db.refresh(unassigned_user)

    # 3. Locations & Items
    loc_x = Location(org_id=org_x.id, name=f"Clinic X {uid}", type="clinic", region="North")
    loc_y = Location(org_id=org_y.id, name=f"Clinic Y {uid}", type="clinic", region="South")

    item_x = Item(
        org_id=org_x.id,
        name=f"Drug X {uid}",
        category="medicine",
        unit="box",
        barcode=f"111{uid}",
        min_stock=10,
    )
    item_y = Item(
        org_id=org_y.id,
        name=f"Drug Y {uid}",
        category="medicine",
        unit="box",
        barcode=f"222{uid}",
        min_stock=10,
    )

    db.add_all([loc_x, loc_y, item_x, item_y])
    db.commit()
    db.refresh(loc_x)
    db.refresh(loc_y)
    db.refresh(item_x)
    db.refresh(item_y)

    # 4. Inventory Transactions
    today = date.today()
    tx_x = InventoryTransaction(
        location_id=loc_x.id,
        item_id=item_x.id,
        date=today,
        opening_stock=0,
        received=100,
        issued=10,
        closing_stock=90,
    )
    tx_y = InventoryTransaction(
        location_id=loc_y.id,
        item_id=item_y.id,
        date=today,
        opening_stock=0,
        received=50,
        issued=5,
        closing_stock=45,
    )
    db.add_all([tx_x, tx_y])
    db.commit()

    # 5. Requisitions
    req_x = Requisition(
        requisition_number=f"REQ-X-{uid}",
        location_id=loc_x.id,
        requested_by=staff_x.username,
        department="Pharmacy",
        urgency="NORMAL",
        status="PENDING",
    )
    req_y = Requisition(
        requisition_number=f"REQ-Y-{uid}",
        location_id=loc_y.id,
        requested_by=admin_y.username,
        department="Pharmacy",
        urgency="NORMAL",
        status="PENDING",
    )
    db.add_all([req_x, req_y])
    db.commit()
    db.refresh(req_x)
    db.refresh(req_y)

    req_item_x = RequisitionItem(
        requisition_id=req_x.id,
        item_id=item_x.id,
        quantity_requested=10,
    )
    req_item_y = RequisitionItem(
        requisition_id=req_y.id,
        item_id=item_y.id,
        quantity_requested=5,
    )
    db.add_all([req_item_x, req_item_y])
    db.commit()

    # 6. Vendor Uploads & Invoices
    from app.infrastructure.database.models import VendorUpload
    upload_x = VendorUpload(
        org_id=org_x.id,
        vendor_user_id=admin_x.id,
        filename=f"upload_x_{uid}.xlsx",
        location_id=loc_x.id,
        total_rows=1,
        success_rows=1,
        status="COMPLETED",
    )
    upload_y = VendorUpload(
        org_id=org_y.id,
        vendor_user_id=admin_y.id,
        filename=f"upload_y_{uid}.xlsx",
        location_id=loc_y.id,
        total_rows=1,
        success_rows=1,
        status="COMPLETED",
    )
    db.add_all([upload_x, upload_y])
    db.commit()
    db.refresh(upload_x)
    db.refresh(upload_y)

    inv_x = VendorInvoice(
        org_id=org_x.id,
        vendor_user_id=admin_x.id,
        vendor_upload_id=upload_x.id,
        invoice_number=f"INV-X-{uid}",
        invoice_date=today,
        line_items=[],
        subtotal=100.0,
        tax_amount=10.0,
        total_amount=110.0,
        status="ISSUED",
    )
    inv_y = VendorInvoice(
        org_id=org_y.id,
        vendor_user_id=admin_y.id,
        vendor_upload_id=upload_y.id,
        invoice_number=f"INV-Y-{uid}",
        invoice_date=today,
        line_items=[],
        subtotal=200.0,
        tax_amount=20.0,
        total_amount=220.0,
        status="ISSUED",
    )
    db.add_all([inv_x, inv_y])
    db.commit()
    db.refresh(inv_x)
    db.refresh(inv_y)


    # 7. Import Jobs
    job_x = DataImportJob(
        org_id=org_x.id,
        uploaded_by_user_id=admin_x.id,
        filename=f"import_x_{uid}.csv",
        target_entity="item",
        total_rows=10,
        status="PENDING",
    )
    job_y = DataImportJob(
        org_id=org_y.id,
        uploaded_by_user_id=admin_y.id,
        filename=f"import_y_{uid}.csv",
        target_entity="item",
        total_rows=20,
        status="PENDING",
    )
    db.add_all([job_x, job_y])
    db.commit()
    db.refresh(job_x)
    db.refresh(job_y)

    return {
        "org_x": org_x,
        "org_y": org_y,
        "admin_x": admin_x,
        "staff_x": staff_x,
        "admin_y": admin_y,
        "unassigned_user": unassigned_user,
        "loc_x": loc_x,
        "loc_y": loc_y,
        "item_x": item_x,
        "item_y": item_y,
        "req_x": req_x,
        "req_y": req_y,
        "inv_x": inv_x,
        "inv_y": inv_y,
        "job_x": job_x,
        "job_y": job_y,
    }


    return {
        "admin_x": admin_x,
        "staff_x": staff_x,
        "admin_y": admin_y,
        "unassigned_user": unassigned_user,
    }


class TestMultiTenantIsolation:
    """Matrix tests ensuring Org X cannot see or modify Org Y data."""

    def test_admin_x_sees_only_org_x_locations_and_items(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        loc_x = multi_tenant_fixture["loc_x"]
        loc_y = multi_tenant_fixture["loc_y"]
        item_x = multi_tenant_fixture["item_x"]
        item_y = multi_tenant_fixture["item_y"]

        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # Locations
        resp_loc = client.get("/api/inventory/locations", headers=headers_x)
        assert resp_loc.status_code == 200
        loc_names = [l["name"] for l in resp_loc.json()["data"]]
        assert loc_x.name in loc_names
        assert loc_y.name not in loc_names

        # Items
        resp_item = client.get("/api/inventory/items", headers=headers_x)
        assert resp_item.status_code == 200
        item_names = [i["name"] for i in resp_item.json()["data"]]
        assert item_x.name in item_names
        assert item_y.name not in item_names

    def test_admin_y_sees_only_org_y_locations_and_items(self, client, multi_tenant_fixture):
        admin_y = multi_tenant_fixture["admin_y"]
        loc_x = multi_tenant_fixture["loc_x"]
        loc_y = multi_tenant_fixture["loc_y"]
        item_x = multi_tenant_fixture["item_x"]
        item_y = multi_tenant_fixture["item_y"]

        headers_y = get_auth_header(client, admin_y.email, "SecurePass123!")
        
        # Locations
        resp_loc = client.get("/api/inventory/locations", headers=headers_y)
        assert resp_loc.status_code == 200
        loc_names = [l["name"] for l in resp_loc.json()["data"]]
        assert loc_y.name in loc_names
        assert loc_x.name not in loc_names

        # Items
        resp_item = client.get("/api/inventory/items", headers=headers_y)
        assert resp_item.status_code == 200
        item_names = [i["name"] for i in resp_item.json()["data"]]
        assert item_y.name in item_names
        assert item_x.name not in item_names

    def test_admin_x_cannot_access_org_y_location_items(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        loc_y = multi_tenant_fixture["loc_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # Accessing Location Y should return 404 for Admin X
        resp = client.get(f"/api/inventory/location/{loc_y.id}/items", headers=headers_x)
        assert resp.status_code == 404

    def test_admin_x_cannot_access_org_y_stock(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        loc_y = multi_tenant_fixture["loc_y"]
        item_y = multi_tenant_fixture["item_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # Accessing Location Y + Item Y
        resp = client.get(f"/api/inventory/stock/{loc_y.id}/{item_y.id}", headers=headers_x)
        assert resp.status_code == 404

    def test_admin_x_cannot_bulk_transact_on_org_y_location_or_item(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        loc_x = multi_tenant_fixture["loc_x"]
        loc_y = multi_tenant_fixture["loc_y"]
        item_x = multi_tenant_fixture["item_x"]
        item_y = multi_tenant_fixture["item_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # Attempt with foreign location
        resp_loc = client.post(
            "/api/inventory/bulk-transaction",
            json={
                "location_id": loc_y.id,
                "date": str(date.today()),
                "items": [{"item_id": item_x.id, "received": 10, "issued": 0}],
            },
            headers=headers_x,
        )
        assert resp_loc.status_code == 404

        # Attempt with own location but foreign item
        resp_item = client.post(
            "/api/inventory/bulk-transaction",
            json={
                "location_id": loc_x.id,
                "date": str(date.today()),
                "items": [{"item_id": item_y.id, "received": 10, "issued": 0}],
            },
            headers=headers_x,
        )
        assert resp_item.status_code == 404

    def test_admin_x_cannot_create_requisition_with_org_y_location_or_item(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        loc_x = multi_tenant_fixture["loc_x"]
        loc_y = multi_tenant_fixture["loc_y"]
        item_x = multi_tenant_fixture["item_x"]
        item_y = multi_tenant_fixture["item_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # Foreign location
        resp_loc = client.post(
            "/api/requisition/create",
            json={
                "location_id": loc_y.id,
                "department": "Pharmacy",
                "urgency": "NORMAL",
                "items": [{"item_id": item_x.id, "quantity": 5}],
            },
            headers=headers_x,
        )
        assert resp_loc.status_code == 403

        # Foreign item
        resp_item = client.post(
            "/api/requisition/create",
            json={
                "location_id": loc_x.id,
                "department": "Pharmacy",
                "urgency": "NORMAL",
                "items": [{"item_id": item_y.id, "quantity": 5}],
            },
            headers=headers_x,
        )
        assert resp_item.status_code == 403

    def test_admin_x_cannot_view_or_approve_org_y_requisition(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        req_y = multi_tenant_fixture["req_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # View detail
        resp_get = client.get(f"/api/requisition/{req_y.id}", headers=headers_x)
        assert resp_get.status_code == 404

        # Approve
        resp_app = client.put(f"/api/requisition/{req_y.id}/approve", json={}, headers=headers_x)
        assert resp_app.status_code == 403

        # Reject
        resp_rej = client.put(f"/api/requisition/{req_y.id}/reject", json={"reason": "Invalid requisition"}, headers=headers_x)
        assert resp_rej.status_code == 403


        # Cancel
        resp_can = client.put(f"/api/requisition/{req_y.id}/cancel", json={}, headers=headers_x)
        assert resp_can.status_code == 403


    def test_admin_x_cannot_view_org_y_invoice_or_pdf(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        inv_y = multi_tenant_fixture["inv_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # View detail
        resp = client.get(f"/api/vendor/invoices/{inv_y.id}", headers=headers_x)
        assert resp.status_code == 403

        # Download PDF
        resp_pdf = client.get(f"/api/vendor/invoices/{inv_y.id}/pdf", headers=headers_x)
        assert resp_pdf.status_code == 403

    def test_admin_x_cannot_view_or_confirm_org_y_import_job(self, client, multi_tenant_fixture):
        admin_x = multi_tenant_fixture["admin_x"]
        job_y = multi_tenant_fixture["job_y"]
        headers_x = get_auth_header(client, admin_x.email, "SecurePass123!")
        
        # View status
        resp_status = client.get(f"/api/data-import/jobs/{job_y.id}", headers=headers_x)
        assert resp_status.status_code == 403

        # View quarantine
        resp_quar = client.get(f"/api/data-import/jobs/{job_y.id}/quarantine", headers=headers_x)
        assert resp_quar.status_code == 403

        # Confirm
        resp_conf = client.post(
            "/api/data-import/confirm",
            json={"job_id": job_y.id, "confirmed_mapping": {}},
            headers=headers_x,
        )
        assert resp_conf.status_code == 403

    def test_unassigned_user_is_denied_across_all_endpoints(self, client, multi_tenant_fixture):
        unassigned_user = multi_tenant_fixture["unassigned_user"]
        loc_x = multi_tenant_fixture["loc_x"]
        item_x = multi_tenant_fixture["item_x"]
        headers = get_auth_header(client, unassigned_user.email, "SecurePass123!")
        
        # Inventory
        assert client.get("/api/inventory/locations", headers=headers).status_code == 403
        assert client.get("/api/inventory/items", headers=headers).status_code == 403
        
        # Requisition
        assert client.get("/api/requisition/list", headers=headers).status_code == 403
        assert client.post("/api/requisition/create", json={"location_id": loc_x.id, "department": "Pharmacy", "urgency": "NORMAL", "items": [{"item_id": item_x.id, "quantity": 1}]}, headers=headers).status_code == 403

        # Analytics
        assert client.get("/api/analytics/heatmap", headers=headers).status_code == 403
        assert client.get("/api/analytics/summary", headers=headers).status_code == 403

        # Chat
        assert client.post("/api/chat/query", json={"question": "What is our stock?"}, headers=headers).status_code == 403

        # Invoices
        assert client.get("/api/vendor/invoices", headers=headers).status_code == 403


