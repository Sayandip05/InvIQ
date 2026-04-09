"""
Inventory API endpoint tests — integration tests for inventory routes.

Tests the API layer with real HTTP requests.
"""

import pytest
from datetime import date
from tests.conftest import get_auth_header


class TestInventoryLocations:
    """Test location management endpoints."""

    def test_get_all_locations(self, client, test_user):
        """Get all locations should return list."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/inventory/locations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_locations_unauthenticated(self, client):
        """Get locations without auth should fail."""
        response = client.get("/api/inventory/locations")
        assert response.status_code in [401, 403]

    def test_create_location_success(self, client, test_user):
        """Create location should succeed with valid data."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/locations",
            json={
                "name": "Test Warehouse",
                "type": "warehouse",
                "region": "North",
                "address": "123 Test St",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Warehouse"

    def test_create_location_duplicate(self, client, test_user):
        """Create duplicate location should fail."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        # Create first
        client.post(
            "/api/inventory/locations",
            json={"name": "Duplicate Location", "type": "clinic", "region": "South"},
            headers=headers,
        )
        # Try duplicate
        response = client.post(
            "/api/inventory/locations",
            json={"name": "Duplicate Location", "type": "clinic", "region": "South"},
            headers=headers,
        )
        assert response.status_code in [400, 409]


class TestInventoryItems:
    """Test item management endpoints."""

    def test_get_all_items(self, client, test_user):
        """Get all items should return list."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/inventory/items", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_create_item_success(self, client, test_user):
        """Create item should succeed with valid data."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/items",
            json={
                "name": "Test Medicine",
                "category": "medicine",
                "unit": "box",
                "lead_time_days": 7,
                "min_stock": 50,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Medicine"

    def test_create_item_duplicate(self, client, test_user):
        """Create duplicate item should fail."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        # Create first
        client.post(
            "/api/inventory/items",
            json={"name": "Duplicate Item", "category": "supplies", "unit": "pack", "lead_time_days": 5, "min_stock": 20},
            headers=headers,
        )
        # Try duplicate
        response = client.post(
            "/api/inventory/items",
            json={"name": "Duplicate Item", "category": "supplies", "unit": "pack", "lead_time_days": 5, "min_stock": 20},
            headers=headers,
        )
        assert response.status_code in [400, 409]


class TestInventoryTransactions:
    """Test transaction endpoints."""

    def test_add_single_transaction(self, client, test_user, db):
        """Add single transaction should succeed."""
        from app.infrastructure.database.models import Location, Item
        
        # Create test data
        location = Location(name="TX Location", type="clinic", region="Test")
        item = Item(name="TX Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
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
                "notes": "Test transaction",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_add_transaction_invalid_location(self, client, test_user):
        """Add transaction with invalid location should fail."""
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
        """Get current stock should return latest stock level."""
        from app.infrastructure.database.models import Location, Item, InventoryTransaction
        
        location = Location(name="Stock Location", type="warehouse", region="Test")
        item = Item(name="Stock Item", category="supplies", unit="pack", lead_time_days=5, min_stock=20)
        db.add(location)
        db.add(item)
        db.commit()
        db.refresh(location)
        db.refresh(item)

        # Add transaction
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

    def test_bulk_transaction(self, client, test_user, db):
        """Bulk transaction should process multiple items."""
        from app.infrastructure.database.models import Location, Item
        
        location = Location(name="Bulk Location", type="clinic", region="Test")
        item1 = Item(name="Bulk Item 1", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        item2 = Item(name="Bulk Item 2", category="supplies", unit="pack", lead_time_days=5, min_stock=30)
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
                    {"item_id": item1.id, "received": 100, "issued": 0},
                    {"item_id": item2.id, "received": 50, "issued": 0},
                ],
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestInventoryReset:
    """Test data reset endpoint."""

    def test_reset_data_without_confirm(self, client, test_user):
        """Reset without confirm should fail."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/reset-data",
            json={"confirm": False},
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_reset_data_with_confirm(self, client, test_user):
        """Reset with confirm should succeed."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/inventory/reset-data",
            json={"confirm": True},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
