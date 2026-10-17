"""
Unit and integration tests for Barcode Quick Dispense & Background Tasks.
"""

import pytest
from datetime import date, timedelta
from tests.conftest import get_auth_header
from app.infrastructure.database.models import Item, Location, InventoryTransaction
from app.application.inventory_service import InventoryService
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.application.background_tasks import (
    run_fefo_expiry_audit,
    run_stock_threshold_audit,
    run_cold_chain_health_check,
)
from app.application.agent_tools import (
    search_medicines,
    get_near_expiry_items,
    get_cold_chain_items,
    set_db_session,
)


class TestBarcodeDispense:
    """Test the POST /api/inventory/scan-dispense endpoint and service."""

    def test_scan_dispense_success(self, client, test_user, db):
        org_id = test_user["user"].org_id
        location = Location(org_id=org_id, name="Dispense Counter 1", type="counter", region="North")
        item = Item(
            org_id=org_id,
            name="Pan-D Capsule Test",
            barcode="890108699999",
            category="Gastro & PPI",
            unit="strip",
            lead_time_days=3,
            min_stock=10,
            mrp=199.0,
        )
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        # Inbound delivery with batch
        tx_in = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            org_id=item.org_id,
            date=date.today(),
            opening_stock=0,
            received=50,
            issued=0,
            closing_stock=50,
            batch_number="BT-TEST-001",
            expiry_date=date.today() + timedelta(days=120),
        )
        db.add(tx_in)
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/scan-dispense",
            json={
                "barcode": "890108699999",
                "location_id": location.id,
                "quantity": 2,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["item_name"] == "Pan-D Capsule Test"
        assert data["data"]["dispensed_quantity"] == 2
        assert data["data"]["remaining_stock"] == 48
        assert data["data"]["batch_number"] == "BT-TEST-001"

    def test_scan_dispense_by_numeric_id(self, client, test_user, db):
        org_id = test_user["user"].org_id
        location = Location(org_id=org_id, name="Dispense Counter 2", type="counter", region="South")
        item = Item(
            org_id=org_id,
            name="Dolo 650 Test",
            barcode="890108688888",
            category="Analgesics & Pain",
            unit="strip",
            lead_time_days=2,
            min_stock=5,
            mrp=30.0,
        )
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        tx_in = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            org_id=item.org_id,
            date=date.today(),
            opening_stock=0,
            received=20,
            issued=0,
            closing_stock=20,
            batch_number="BT-DOLO-99",
            expiry_date=date.today() + timedelta(days=200),
        )
        db.add(tx_in)
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/scan-dispense",
            json={
                "barcode": str(item.id),
                "location_id": location.id,
                "quantity": 1,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["remaining_stock"] == 19

    def test_scan_dispense_insufficient_stock(self, client, test_user, db):
        org_id = test_user["user"].org_id
        location = Location(org_id=org_id, name="Dispense Counter 3", type="counter", region="East")
        item = Item(
            org_id=org_id,
            name="Augmentin Test",
            barcode="890108677777",
            category="Antibiotics",
            unit="strip",
            lead_time_days=5,
            min_stock=5,
        )
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)


        tx_in = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            org_id=item.org_id,
            date=date.today(),
            opening_stock=0,
            received=2,
            issued=0,
            closing_stock=2,
        )
        db.add(tx_in)
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/scan-dispense",
            json={
                "barcode": "890108677777",
                "location_id": location.id,
                "quantity": 10,
            },
            headers=headers,
        )
    def test_scan_dispense_unbatched_stock(self, client, test_user, db):
        """Dispensing stock without batch records should use UNBATCHED with no expiry date."""
        org_id = test_user["user"].org_id
        location = Location(org_id=org_id, name="Dispense Counter Unbatched", type="counter", region="North")
        item = Item(
            org_id=org_id,
            name="Unbatched Medicine",
            barcode="890108600000",
            category="General",
            unit="box",
            lead_time_days=3,
            min_stock=5,
            mrp=50.0,
        )
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        # Inbound delivery with NO batch or expiry
        tx_in = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            org_id=item.org_id,
            date=date.today(),
            opening_stock=0,
            received=10,
            issued=0,
            closing_stock=10,
            batch_number=None,
            expiry_date=None,
        )
        db.add(tx_in)
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/scan-dispense",
            json={
                "barcode": "890108600000",
                "location_id": location.id,
                "quantity": 2,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["remaining_stock"] == 8
        assert data["data"]["batch_number"] == "UNBATCHED"
        assert data["data"]["expiry_date"] is None

    def test_background_audits(self, db):
        res_fefo = run_fefo_expiry_audit(db, days_ahead=90)
        assert res_fefo["status"] == "success"

        res_stock = run_stock_threshold_audit(db)
        assert res_stock["status"] == "success"

        res_cold = run_cold_chain_health_check(db)
        assert res_cold["status"] == "success"

    def test_search_medicines_tool(self, db):
        set_db_session(db)
        results = search_medicines.invoke({"query": "Pan-D"})
        assert isinstance(results, list)
