"""
Vendor service tests — Excel upload parsing, history, and location access.
"""

import pytest
from unittest.mock import Mock

from app.application.vendor_service import VendorService
from app.api.routes.vendor import _has_location_access
from app.infrastructure.database.models import VendorUpload


class TestVendorService:
    """Test vendor service Excel parsing logic and upload tracking."""

    def test_parse_invalid_excel_and_upload_history(self, db):
        """Test error handling on invalid file and upload history retrieval."""
        service = VendorService(db)
        result = service.parse_and_process_excel(
            file_content=b"not an excel file",
            filename="test.xlsx",
            location_id=1,
            vendor_user_id=1,
        )
        assert result["success"] is False

        # Upload tracking
        upload = VendorUpload(
            org_id=1,
            vendor_user_id=1,
            filename="test.xlsx",
            location_id=1,
            total_rows=10,
            success_rows=8,
            error_rows=2,
            status="COMPLETED_WITH_ERRORS",
        )
        db.add(upload)
        db.commit()

        uploads = service.get_uploads_for_vendor(vendor_user_id=1)
        assert len(uploads) == 1
        assert uploads[0]["filename"] == "test.xlsx"

    def test_has_location_access_formats(self):
        """Test location access helper across int lists, string lists, and JSON strings."""
        # Unrestricted
        assert _has_location_access(Mock(location_ids=None), 1) is True
        assert _has_location_access(Mock(location_ids=[]), 1) is True

        # Int & String & JSON lists
        assert _has_location_access(Mock(location_ids=[1, 2]), 1) is True
        assert _has_location_access(Mock(location_ids=[1, 2]), 3) is False
        assert _has_location_access(Mock(location_ids='[1, 2]'), 2) is True
        assert _has_location_access(Mock(location_ids='[1, 2]'), 4) is False

    def test_standard_template_ingestion_and_auto_create_catalog(self, db):
        """Verify ingestion of official 11-column template auto-creates items and creates transactions."""
        import openpyxl
        from io import BytesIO
        from datetime import date, timedelta
        from app.infrastructure.database.models import Item, InventoryTransaction, Location, User

        loc = db.query(Location).filter(Location.org_id == 1).first()
        if not loc:
            loc = Location(org_id=1, name="Central Pharmacy", type="retail_counter", region="North")
            db.add(loc)
            db.commit()

        vendor = db.query(User).filter(User.org_id == 1).first()
        if not vendor:
            vendor = User(username="vendor_std", email="std@vendor.com", hashed_password="pw", role="vendor", org_id=1)
            db.add(vendor)
            db.commit()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "item_name", "quantity", "unit", "batch_number", "expiry_date",
            "purchase_rate", "mrp", "category", "storage_temp", "delivery_date", "invoice_no"
        ])
        future_exp = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        ws.append([
            "Azithromycin 500mg", 40, "strip", "BT-AZ-2026", future_exp,
            55.0, 90.0, "Antibiotics", "ambient", date.today().strftime("%Y-%m-%d"), "INV-TEST-01"
        ])
        buf = BytesIO()
        wb.save(buf)

        service = VendorService(db)
        res = service.parse_and_process_excel(
            file_content=buf.getvalue(),
            filename="manifest_std.xlsx",
            location_id=loc.id,
            vendor_user_id=vendor.id,
            org_id=1,
        )

        assert res["success"] is True
        assert res["data"]["success"] == 1
        assert res["data"]["errors"] == 0

        # Verify Item was automatically created in catalog
        item = db.query(Item).filter(Item.name == "Azithromycin 500mg", Item.org_id == 1).first()
        assert item is not None
        assert item.category == "Antibiotics"
        assert item.unit == "strip"
        assert item.purchase_rate == 55.0
        assert item.mrp == 90.0
        assert item.storage_temp == "ambient"

        # Verify transaction
        tx = db.query(InventoryTransaction).filter(
            InventoryTransaction.item_id == item.id,
            InventoryTransaction.location_id == loc.id,
        ).first()
        assert tx is not None
        assert tx.received == 40
        assert tx.batch_number == "BT-AZ-2026"
        assert tx.expiry_date == date.today() + timedelta(days=365)

    def test_all_or_nothing_validation_past_expiry_rejects_entire_file(self, db):
        """Verify All-or-Nothing policy: if row 2 has past expiry date, reject whole file with 0 DB writes."""
        import openpyxl
        from io import BytesIO
        from datetime import date, timedelta
        from app.infrastructure.database.models import Item, InventoryTransaction, Location, User

        loc = db.query(Location).filter(Location.org_id == 1).first()
        vendor = db.query(User).filter(User.org_id == 1).first()

        count_items_before = db.query(Item).count()
        count_tx_before = db.query(InventoryTransaction).count()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "item_name", "quantity", "unit", "batch_number", "expiry_date",
            "purchase_rate", "mrp", "category", "storage_temp", "delivery_date", "invoice_no"
        ])
        # Row 2 is valid
        future_exp = (date.today() + timedelta(days=200)).strftime("%Y-%m-%d")
        ws.append(["Valid Med A", 10, "strip", "BT-01", future_exp, 20.0, 30.0, "General", "ambient", str(date.today()), "INV-1"])
        # Row 3 has past expiry date
        past_exp = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        ws.append(["Expired Med B", 10, "strip", "BT-02", past_exp, 20.0, 30.0, "General", "ambient", str(date.today()), "INV-1"])

        buf = BytesIO()
        wb.save(buf)

        service = VendorService(db)
        res = service.parse_and_process_excel(
            file_content=buf.getvalue(),
            filename="manifest_with_error.xlsx",
            location_id=loc.id,
            vendor_user_id=vendor.id,
            org_id=1,
        )

        assert res["success"] is False
        assert "Line 3" in res["error"]
        assert "has already passed" in res["error"]

        # ZERO database changes
        assert db.query(Item).count() == count_items_before
        assert db.query(InventoryTransaction).count() == count_tx_before

    def test_all_or_nothing_validation_negative_quantity_rejects_file(self, db):
        """Verify negative quantity is rejected with line number and 0 DB changes."""
        import openpyxl
        from io import BytesIO
        from datetime import date, timedelta
        from app.infrastructure.database.models import Item, InventoryTransaction, Location, User

        loc = db.query(Location).filter(Location.org_id == 1).first()
        vendor = db.query(User).filter(User.org_id == 1).first()

        count_tx_before = db.query(InventoryTransaction).count()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "item_name", "quantity", "unit", "batch_number", "expiry_date",
            "purchase_rate", "mrp", "category", "storage_temp", "delivery_date", "invoice_no"
        ])
        future_exp = (date.today() + timedelta(days=200)).strftime("%Y-%m-%d")
        ws.append(["Invalid Qty Med", -5, "strip", "BT-NEG", future_exp, 20.0, 30.0, "General", "ambient", str(date.today()), "INV-1"])

        buf = BytesIO()
        wb.save(buf)

        service = VendorService(db)
        res = service.parse_and_process_excel(
            file_content=buf.getvalue(),
            filename="negative_qty.xlsx",
            location_id=loc.id,
            vendor_user_id=vendor.id,
            org_id=1,
        )

        assert res["success"] is False
        assert "Line 2" in res["error"]
        assert "greater than zero" in res["error"]
        assert db.query(InventoryTransaction).count() == count_tx_before

    def test_all_or_nothing_validation_mrp_less_than_purchase_rate(self, db):
        """Verify rejection when MRP is less than purchase rate."""
        import openpyxl
        from io import BytesIO
        from datetime import date, timedelta
        from app.infrastructure.database.models import Location, User

        loc = db.query(Location).filter(Location.org_id == 1).first()
        vendor = db.query(User).filter(User.org_id == 1).first()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "item_name", "quantity", "unit", "batch_number", "expiry_date",
            "purchase_rate", "mrp", "category", "storage_temp", "delivery_date", "invoice_no"
        ])
        future_exp = (date.today() + timedelta(days=200)).strftime("%Y-%m-%d")
        ws.append(["Loss Making Med", 10, "strip", "BT-LOSS", future_exp, 100.0, 60.0, "General", "ambient", str(date.today()), "INV-1"])

        buf = BytesIO()
        wb.save(buf)

        service = VendorService(db)
        res = service.parse_and_process_excel(
            file_content=buf.getvalue(),
            filename="mrp_loss.xlsx",
            location_id=loc.id,
            vendor_user_id=vendor.id,
            org_id=1,
        )

        assert res["success"] is False
        assert "Line 2" in res["error"]
        assert "cannot be less than purchase rate" in res["error"]

