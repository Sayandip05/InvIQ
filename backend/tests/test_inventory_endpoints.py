"""
Inventory API endpoint tests — integration tests for inventory routes.

Tests the API layer with real HTTP requests against SQLite test DB.
Pharmacy fields (storage_temp on Item, batch_number + expiry_date on Transaction)
are covered explicitly.
"""

import pytest
from datetime import date
from tests.conftest import get_auth_header


class TestInventoryLocations:
    """Test location management endpoints."""

    def test_get_all_locations(self, client, test_user):
        """GET /inventory/locations returns a success list."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/inventory/locations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_locations_public_access(self, client):
        """GET /locations is a public endpoint (uses optional auth) — returns 200."""
        response = client.get("/api/inventory/locations")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_create_location_success(self, client, test_user):
        """POST /inventory/locations with valid payload creates a location."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/locations",
            json={
                "name": "Central Pharma Warehouse – North",
                "type": "central_warehouse",
                "region": "Delhi NCR",
                "address": "123 Pharma Lane",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Central Pharma Warehouse – North"

    def test_create_location_duplicate(self, client, test_user):
        """Creating a duplicate location name should fail with 400/409."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        client.post(
            "/api/inventory/locations",
            json={"name": "Duplicate Pharmacy", "type": "retail_pharmacy", "region": "South"},
            headers=headers,
        )
        response = client.post(
            "/api/inventory/locations",
            json={"name": "Duplicate Pharmacy", "type": "retail_pharmacy", "region": "South"},
            headers=headers,
        )
        assert response.status_code in [400, 409]


class TestInventoryItems:
    """Test item management endpoints — includes pharmacy storage_temp field."""

    def test_get_all_items(self, client, test_user):
        """GET /inventory/items returns success list."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/inventory/items", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_create_ambient_item(self, client, test_user):
        """POST /inventory/items creates an ambient-storage medication."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/items",
            json={
                "name": "Amoxicillin 500mg Capsules",
                "category": "Antibiotics",
                "unit": "box",
                "lead_time_days": 7,
                "min_stock": 200,
                "storage_temp": "ambient",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Amoxicillin 500mg Capsules"
        assert data["data"]["storage_temp"] == "ambient"

    def test_create_cold_chain_item(self, client, test_user):
        """POST /inventory/items creates a cold-chain vaccine item."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/items",
            json={
                "name": "Insulin Regular 100IU/mL Vial",
                "category": "Diabetic Care",
                "unit": "vial",
                "lead_time_days": 5,
                "min_stock": 500,
                "storage_temp": "cold_chain",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["storage_temp"] == "cold_chain"

    def test_create_item_default_storage_temp(self, client, test_user):
        """POST without storage_temp should default to 'ambient'."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/items",
            json={
                "name": "Paracetamol 500mg Tablets",
                "category": "Analgesics",
                "unit": "box",
                "lead_time_days": 3,
                "min_stock": 500,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["storage_temp"] == "ambient"

    def test_create_item_invalid_storage_temp(self, client, test_user):
        """POST with invalid storage_temp value should fail validation."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/items",
            json={
                "name": "Bad Temp Item",
                "category": "Test",
                "unit": "box",
                "lead_time_days": 5,
                "min_stock": 10,
                "storage_temp": "frozen",   # invalid — only ambient | cold_chain
            },
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_item_duplicate(self, client, test_user):
        """Creating a duplicate item name should fail."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        client.post(
            "/api/inventory/items",
            json={"name": "Duplicate Drug", "category": "supplies", "unit": "pack",
                  "lead_time_days": 5, "min_stock": 20},
            headers=headers,
        )
        response = client.post(
            "/api/inventory/items",
            json={"name": "Duplicate Drug", "category": "supplies", "unit": "pack",
                  "lead_time_days": 5, "min_stock": 20},
            headers=headers,
        )
        assert response.status_code in [400, 409]


class TestInventoryTransactions:
    """Test transaction endpoints — includes batch_number + expiry_date fields."""

    def test_add_single_transaction_minimal(self, client, test_user, db):
        """Add transaction with minimal fields (no batch info)."""
        from app.infrastructure.database.models import Location, Item

        location = Location(name="TX Location Minimal", type="clinic", region="Test")
        item = Item(name="TX Item Minimal", category="medicine", unit="box",
                    lead_time_days=7, min_stock=50, storage_temp="ambient")
        db.add(location)
        db.add(item)
        db.commit()
        db.refresh(location)
        db.refresh(item)

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/transaction",
            json={
                "location_id": location.id,
                "item_id": item.id,
                "date": "2026-04-09",
                "received": 100,
                "issued": 0,
                "notes": "Monthly replenishment",
            },
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_add_single_transaction_with_batch_info(self, client, test_user, db):
        """Add inbound transaction with batch_number and expiry_date."""
        from app.infrastructure.database.models import Location, Item

        location = Location(name="Cold Chain Location", type="central_warehouse", region="Delhi")
        item = Item(name="BCG Vaccine Batch Test", category="Vaccines", unit="vial",
                    lead_time_days=14, min_stock=200, storage_temp="cold_chain")
        db.add(location)
        db.add(item)
        db.commit()
        db.refresh(location)
        db.refresh(item)

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/transaction",
            json={
                "location_id": location.id,
                "item_id": item.id,
                "date": "2026-04-09",
                "received": 200,
                "issued": 0,
                "batch_number": "BT-25-4821",
                "expiry_date": "2027-06-30",
                "notes": "New cold chain batch arrived",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_add_transaction_invalid_location(self, client, test_user):
        """Transaction with non-existent location_id should return 404."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/transaction",
            json={
                "location_id": 99999,
                "item_id": 1,
                "date": "2026-04-09",
                "received": 100,
                "issued": 0,
            },
            headers=headers,
        )
        assert response.status_code == 404

    def test_get_current_stock(self, client, test_user, db):
        """GET /inventory/stock/{location_id}/{item_id} returns latest stock."""
        from app.infrastructure.database.models import Location, Item, InventoryTransaction

        location = Location(name="Stock Location", type="warehouse", region="Test")
        item = Item(name="Stock Item", category="supplies", unit="pack",
                    lead_time_days=5, min_stock=20, storage_temp="ambient")
        db.add(location)
        db.add(item)
        db.commit()
        db.refresh(location)
        db.refresh(item)

        tx = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 9),
            opening_stock=0,
            received=150,
            issued=0,
            closing_stock=150,
            entered_by="testuser",
        )
        db.add(tx)
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get(
            f"/api/inventory/stock/{location.id}/{item.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_stock"] == 150

    def test_bulk_transaction_with_batch_data(self, client, test_user, db):
        """Bulk transaction with pharmacy batch info on inbound deliveries."""
        from app.infrastructure.database.models import Location, Item

        location = Location(name="Bulk Pharma Location", type="central_warehouse", region="Test")
        item1 = Item(name="Bulk Vaccine 1", category="Vaccines", unit="vial",
                     lead_time_days=14, min_stock=200, storage_temp="cold_chain")
        item2 = Item(name="Bulk Antibiotic 1", category="Antibiotics", unit="box",
                     lead_time_days=7, min_stock=100, storage_temp="ambient")
        db.add_all([location, item1, item2])
        db.commit()
        db.refresh(location)
        db.refresh(item1)
        db.refresh(item2)

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/bulk-transaction",
            json={
                "location_id": location.id,
                "date": "2026-04-09",
                "items": [
                    {
                        "item_id": item1.id,
                        "received": 200,
                        "issued": 0,
                        "batch_number": "LOT-25-1001",
                        "expiry_date": "2026-12-31",
                    },
                    {
                        "item_id": item2.id,
                        "received": 100,
                        "issued": 0,
                        "batch_number": "BT-25-2002",
                        "expiry_date": "2028-06-30",
                    },
                ],
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["successful"]) == 2

    def test_bulk_transaction_outbound_no_batch(self, client, test_user, db):
        """Outbound-only transaction (issued only, no batch info) is valid."""
        from app.infrastructure.database.models import Location, Item, InventoryTransaction

        location = Location(name="Outbound Location", type="retail_pharmacy", region="Mumbai")
        item = Item(name="Outbound Drug", category="Antibiotics", unit="box",
                    lead_time_days=7, min_stock=50, storage_temp="ambient")
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        # Seed opening stock
        db.add(InventoryTransaction(
            location_id=location.id, item_id=item.id,
            date=date(2026, 4, 1), opening_stock=0,
            received=200, issued=0, closing_stock=200, entered_by="seed",
        ))
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/bulk-transaction",
            json={
                "location_id": location.id,
                "date": "2026-04-09",
                "items": [
                    {"item_id": item.id, "received": 0, "issued": 50},
                ],
            },
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestInventoryReset:
    """Test data reset endpoint — requires admin role."""

    def test_reset_data_staff_forbidden(self, client, test_user):
        """Staff users must NOT be able to reset data (security boundary)."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/reset-data",
            json={"confirm": True},
            headers=headers,
        )
        assert response.status_code == 403

    def test_reset_data_without_confirm(self, client, admin_user):
        """Admin: reset without confirm=True should fail with 400/422."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.post(
            "/api/inventory/reset-data",
            json={"confirm": False},
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_reset_data_with_confirm(self, client, admin_user):
        """Admin: reset with confirm=True should wipe data and return 200."""
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.post(
            "/api/inventory/reset-data",
            json={"confirm": True},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
