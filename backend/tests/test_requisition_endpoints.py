"""
Requisition API endpoint tests — integration tests for requisition routes.
"""

import pytest
from tests.conftest import get_auth_header


class TestRequisitionCreate:
    """Test requisition creation endpoint."""

    def test_create_requisition_success(self, client, test_user, db):
        """Create requisition should succeed with valid data."""
        from app.infrastructure.database.models import Location, Item
        
        location = Location(name="Req Location", type="clinic", region="Test")
        item = Item(name="Req Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/requisition/create",
            json={
                "location_id": location.id,
                "department": "Pharmacy",
                "urgency": "NORMAL",
                "items": [
                    {"item_id": item.id, "quantity": 50, "notes": "Urgent need"}
                ],
                "notes": "Monthly requisition",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "REQ-" in data["data"]["requisition_number"]

    def test_create_requisition_invalid_urgency(self, client, test_user, db):
        """Create requisition with invalid urgency should fail."""
        from app.infrastructure.database.models import Location, Item
        
        location = Location(name="Req Location 2", type="clinic", region="Test")
        item = Item(name="Req Item 2", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.post(
            "/api/requisition/create",
            json={
                "location_id": location.id,
                "department": "Pharmacy",
                "urgency": "INVALID",
                "items": [{"item_id": item.id, "quantity": 50}],
            },
            headers=headers,
        )
        assert response.status_code in [400, 422]

    def test_create_requisition_unauthenticated(self, client):
        """Create requisition without auth should fail."""
        response = client.post(
            "/api/requisition/create",
            json={
                "location_id": 1,
                "department": "Pharmacy",
                "urgency": "NORMAL",
                "items": [{"item_id": 1, "quantity": 50}],
            },
        )
        assert response.status_code in [401, 403]


class TestRequisitionList:
    """Test requisition listing endpoint."""

    def test_list_requisitions(self, client, test_user):
        """List requisitions should return paginated results."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/requisition/list", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "pagination" in data

    def test_list_requisitions_with_filters(self, client, test_user):
        """List requisitions with filters should work."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get(
            "/api/requisition/list?status=PENDING&limit=10",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_requisitions_pagination(self, client, test_user):
        """List requisitions should respect pagination."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get(
            "/api/requisition/list?skip=0&limit=5",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 5


class TestRequisitionDetails:
    """Test requisition details endpoint."""

    def test_get_requisition_details(self, client, test_user, db):
        """Get requisition details should return full data."""
        from app.infrastructure.database.models import Location, Item, Requisition, RequisitionItem
        
        location = Location(name="Detail Location", type="clinic", region="Test")
        item = Item(name="Detail Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        req = Requisition(
            requisition_number="REQ-TEST-001",
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        req_item = RequisitionItem(
            requisition_id=req.id,
            item_id=item.id,
            quantity_requested=50,
        )
        db.add(req_item)
        db.commit()

        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get(f"/api/requisition/{req.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["requisition_number"] == "REQ-TEST-001"

    def test_get_nonexistent_requisition(self, client, test_user):
        """Get nonexistent requisition should return 404."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/requisition/99999", headers=headers)
        assert response.status_code == 404


class TestRequisitionApproval:
    """Test requisition approval endpoint."""

    def test_approve_requisition_requires_manager(self, client, test_user):
        """Approve requisition should require manager role."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.put(
            "/api/requisition/1/approve",
            json={},
            headers=headers,
        )
        # Staff user should not have permission
        assert response.status_code in [401, 403]

    def test_approve_requisition_success(self, client, admin_user, db):
        """Approve requisition should succeed for admin."""
        from app.infrastructure.database.models import Location, Item, Requisition, RequisitionItem, InventoryTransaction
        from datetime import date
        
        location = Location(name="Approve Location", type="clinic", region="Test")
        item = Item(name="Approve Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        # Add stock first
        tx = InventoryTransaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 1),
            opening_stock=0,
            received=200,
            issued=0,
            closing_stock=200,
            entered_by="system",
        )
        db.add(tx)
        db.commit()

        req = Requisition(
            requisition_number="REQ-APPROVE-001",
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        req_item = RequisitionItem(
            requisition_id=req.id,
            item_id=item.id,
            quantity_requested=50,
        )
        db.add(req_item)
        db.commit()

        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.put(
            f"/api/requisition/{req.id}/approve",
            json={},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestRequisitionRejection:
    """Test requisition rejection endpoint."""

    def test_reject_requisition_success(self, client, admin_user, db):
        """Reject requisition should succeed for admin."""
        from app.infrastructure.database.models import Location, Item, Requisition, RequisitionItem
        
        location = Location(name="Reject Location", type="clinic", region="Test")
        item = Item(name="Reject Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        db.add_all([location, item])
        db.commit()
        db.refresh(location)
        db.refresh(item)

        req = Requisition(
            requisition_number="REQ-REJECT-001",
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        req_item = RequisitionItem(
            requisition_id=req.id,
            item_id=item.id,
            quantity_requested=50,
        )
        db.add(req_item)
        db.commit()

        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.put(
            f"/api/requisition/{req.id}/reject",
            json={"reason": "Out of budget"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestRequisitionStats:
    """Test requisition stats endpoint."""

    def test_get_requisition_stats(self, client, test_user):
        """Get requisition stats should return counts."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        response = client.get("/api/requisition/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "total" in data["data"]
        assert "pending" in data["data"]
