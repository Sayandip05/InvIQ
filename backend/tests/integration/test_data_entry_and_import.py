"""
Integration tests for Journey C: Data Entry and Import.

Verifies:
1. The system clearly shows required import columns and provides a preview,
   mapping, validation errors, and quarantine for invalid rows.
2. Imports are reviewed before commit. A default location must belong to the
   importing organization (foreign location ID is rejected).
3. Vendor delivery uploads create stock only for an authorized location in the
   vendor's organization and retain an auditable invoice/upload record.
4. Every inventory movement records who performed it, when, why, batch and
   expiry data where required, and the affected location/item.
"""

import io
import pytest
from datetime import date
from app.infrastructure.database.models import (
    User,
    Organization,
    Location,
    Item,
    InventoryTransaction,
    DataImportJob,
    ImportQuarantineRow,
    VendorUpload,
    VendorInvoice,
)
from app.core.security import create_access_token, hash_password
from app.application.cache_service import cache_invalidate_pattern


@pytest.fixture(autouse=True)
def clear_caches_before_test():
    cache_invalidate_pattern("*")
    yield
    cache_invalidate_pattern("*")


import openpyxl


def _create_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_data_import_preview_mapping_and_quarantine(client, db):
    """Journey C.1: Preview required columns, AI mapping, validation errors, and row quarantine."""
    org = Organization(name="Pharmacy Import Org", slug="pharmacy-import-org")
    db.add(org)
    db.commit()

    admin = User(
        email="admin_import@test.com",
        username="admin_import",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org.id,
        is_active=True,
        is_verified=True,
    )
    loc = Location(name="Main Counter Import", type="retail_counter", region="North", org_id=org.id)
    db.add_all([admin, loc])
    db.commit()

    headers = _auth_headers(admin)

    # 1. Upload Excel with mixed valid and corrupted rows
    excel_content = _create_excel([
        ["Item Name", "Received Qty", "Transaction Date", "Batch Number", "Expiry Date"],
        ["Amoxicillin 500mg", 100, "2026-05-01", "BTX-101", "2027-05-01"],
        ["Paracetamol 650mg", "INVALID_QTY", "2026-05-01", "BTX-102", "2027-06-01"],
        [None, 50, "2026-05-01", "BTX-103", "2027-07-01"],
    ])
    files = {"file": ("stock_manifest.xlsx", io.BytesIO(excel_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    res_upload = client.post(
        "/api/data-import/upload?target_entity=inventory_transaction",
        headers=headers,
        files=files,
    )
    assert res_upload.status_code == 200
    preview_data = res_upload.json()
    assert preview_data["success"] is True
    assert preview_data["total_rows"] == 3
    assert "target_schema" in preview_data
    assert "item_name" in preview_data["target_schema"]
    assert "mapping_result" in preview_data

    job_id = preview_data["job_id"]

    # 2. Confirm import with default location
    confirm_payload = {
        "job_id": job_id,
        "default_location_id": loc.id,
        "mapping": preview_data["mapping_result"],
    }
    res_confirm = client.post("/api/data-import/confirm", json=confirm_payload, headers=headers)
    assert res_confirm.status_code == 200
    confirm_data = res_confirm.json()
    assert confirm_data["status"] in ("PARTIAL", "COMPLETED")

    assert confirm_data["success_rows"] == 1
    assert confirm_data["quarantined_rows"] == 2

    # 3. Fetch quarantined rows
    res_quarantine = client.get(f"/api/data-import/jobs/{job_id}/quarantine", headers=headers)
    assert res_quarantine.status_code == 200
    quarantine_items = res_quarantine.json()["rows"]
    assert len(quarantine_items) == 2
    reasons = [q["reason"] for q in quarantine_items]
    assert "VALIDATION_ERROR" in reasons or "MISSING_REQUIRED" in reasons




def test_import_default_location_tenant_validation_and_ownership(client, db):
    """Journey C.2: Default location must belong to caller's org; foreign jobs and locations rejected."""
    org_1 = Organization(name="Org 1 Import", slug="org-1-import")
    org_2 = Organization(name="Org 2 Import", slug="org-2-import")
    db.add_all([org_1, org_2])
    db.commit()

    admin_1 = User(
        email="admin_org1@test.com",
        username="admin_org1",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_1.id,
        is_active=True,
        is_verified=True,
    )
    admin_2 = User(
        email="admin_org2@test.com",
        username="admin_org2",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        org_id=org_2.id,
        is_active=True,
        is_verified=True,
    )
    loc_1 = Location(name="Counter Org 1", type="retail_counter", region="East", org_id=org_1.id)
    loc_2 = Location(name="Counter Org 2", type="retail_counter", region="West", org_id=org_2.id)
    db.add_all([admin_1, admin_2, loc_1, loc_2])
    db.commit()

    headers_1 = _auth_headers(admin_1)
    headers_2 = _auth_headers(admin_2)

    # 1. Admin 1 uploads import file
    excel_content = _create_excel([
        ["Item Name", "Received", "Date"],
        ["Metformin 500mg", 60, "2026-05-02"],
    ])
    files = {"file": ("items.xlsx", io.BytesIO(excel_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    res_upload = client.post(
        "/api/data-import/upload?target_entity=inventory_transaction",
        headers=headers_1,
        files=files,
    )
    assert res_upload.status_code == 200
    job_id = res_upload.json()["job_id"]

    # 2. Admin 1 attempts to confirm using Org 2's location -> 422 ValidationError
    res_bad_loc = client.post("/api/data-import/confirm", json={
        "job_id": job_id,
        "default_location_id": loc_2.id,  # Foreign location!
        "mapping": res_upload.json()["mapping_result"],
    }, headers=headers_1)
    assert res_bad_loc.status_code in (400, 422)
    assert "does not belong to your organization" in str(res_bad_loc.json())

    # 3. Admin 2 attempts to confirm Admin 1's job -> 403 AuthorizationError
    res_cross_org = client.post("/api/data-import/confirm", json={
        "job_id": job_id,
        "default_location_id": loc_2.id,
        "mapping": res_upload.json()["mapping_result"],
    }, headers=headers_2)
    assert res_cross_org.status_code == 403


def test_vendor_delivery_upload_and_invoice_generation(client, db):
    """Journey C.3: Vendor uploads delivery manifest creating stock & auditable invoice records."""
    import openpyxl

    org_v = Organization(name="Pharmacy Vendor Org", slug="pharmacy-vendor-org")
    db.add(org_v)
    db.commit()

    loc_v = Location(name="Central Warehouse V", type="warehouse", region="South", org_id=org_v.id)
    item_v = Item(
        name="Omeprazole 20mg",
        category="Gastro",
        unit="capsule",
        org_id=org_v.id,
    )
    db.add_all([loc_v, item_v])
    db.commit()

    vendor_user = User(
        email="vendor_delivery@test.com",
        username="vendor_delivery",
        hashed_password=hash_password("VendorPass123!"),
        role="vendor",
        org_id=org_v.id,
        location_ids=[loc_v.id],
        is_active=True,
        is_verified=True,
    )
    db.add(vendor_user)
    db.commit()

    headers_v = _auth_headers(vendor_user)

    # Build Excel delivery manifest
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Item Name", "Quantity Received", "Unit Price", "Delivery Date", "Notes"])
    ws.append(["Omeprazole 20mg", 250, 45.0, "2026-05-03", "Standard Weekly Supply"])

    excel_io = io.BytesIO()
    wb.save(excel_io)
    excel_io.seek(0)

    files = {"file": ("delivery_manifest.xlsx", excel_io, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    # Upload delivery
    res_up = client.post(
        f"/api/vendor/upload-delivery?location_id={loc_v.id}",
        headers=headers_v,
        files=files,
    )
    assert res_up.status_code == 200
    upload_resp = res_up.json()
    assert upload_resp["success"] is True
    upload_data = upload_resp["data"]
    assert upload_data["success"] == 1
    assert "invoice" in upload_data
    invoice_number = upload_data["invoice"]["invoice_number"]

    # Verify inventory stock was increased
    tx = db.query(InventoryTransaction).filter(
        InventoryTransaction.location_id == loc_v.id,
        InventoryTransaction.item_id == item_v.id,
    ).first()
    assert tx is not None
    assert tx.received == 250
    assert tx.closing_stock == 250

    # Verify invoice record exists in DB
    inv_record = db.query(VendorInvoice).filter(VendorInvoice.invoice_number == invoice_number).first()
    assert inv_record is not None
    assert inv_record.org_id == org_v.id
    assert inv_record.subtotal == 250 * 45.0
    assert inv_record.total_amount == 13275.0  # subtotal + 18% GST


def test_inventory_movement_audit_and_batch_expiry_tracking(client, db):
    """Journey C.4: Every movement records who, when, why, batch, expiry, and affected location/item."""
    org_m = Organization(name="Pharmacy Movement Org", slug="pharmacy-movement-org")
    db.add(org_m)
    db.commit()

    staff = User(
        email="pharmacist_dan@test.com",
        username="pharmacist_dan",
        hashed_password=hash_password("StaffPass123!"),
        role="staff",
        org_id=org_m.id,
        is_active=True,
        is_verified=True,
    )
    loc_m = Location(name="Dispensing Branch", type="retail_counter", region="East", org_id=org_m.id)
    item_m = Item(
        name="Ceftriaxone 1g Inj",
        category="Antibiotic",
        unit="vial",
        org_id=org_m.id,
    )
    db.add_all([staff, loc_m, item_m])
    db.commit()

    headers = _auth_headers(staff)

    # 1. Record stock receipt with batch and expiry
    tx_payload = {
        "location_id": loc_m.id,
        "item_id": item_m.id,
        "date": "2026-05-04",
        "received": 80,
        "issued": 0,
        "batch_number": "BATCH-CEF-2026",
        "expiry_date": "2028-05-01",
        "notes": "Direct supplier consignment received",
    }
    res_tx = client.post("/api/inventory/transaction", json=tx_payload, headers=headers)
    assert res_tx.status_code == 200

    # 2. Query ledger to verify full audit trail
    tx = db.query(InventoryTransaction).filter(
        InventoryTransaction.location_id == loc_m.id,
        InventoryTransaction.item_id == item_m.id,
    ).first()
    assert tx is not None
    assert tx.entered_by == "pharmacist_dan"
    assert tx.batch_number == "BATCH-CEF-2026"
    assert str(tx.expiry_date) == "2028-05-01"
    assert tx.notes == "Direct supplier consignment received"
    assert tx.received == 80
    assert tx.closing_stock == 80  # 0 (initial opening stock) + 80 received

