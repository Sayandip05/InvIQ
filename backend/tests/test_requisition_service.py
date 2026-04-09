"""
Requisition service tests — business logic layer.

Tests RequisitionService with mocked repositories.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

from app.application.requisition_service import RequisitionService
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    InvalidStateError,
    InsufficientStockError,
)


class TestRequisitionService:
    """Test requisition service business logic."""

    @pytest.fixture
    def mock_req_repo(self):
        return Mock()

    @pytest.fixture
    def mock_inv_repo(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_req_repo, mock_inv_repo):
        return RequisitionService(mock_req_repo, mock_inv_repo)

    def test_generate_requisition_number(self, service, mock_req_repo):
        """Requisition number should follow REQ-YYYYMMDD-XXX format."""
        mock_req_repo.count_by_prefix.return_value = 5
        req_number = service._generate_requisition_number()
        assert req_number.startswith("REQ-")
        assert "-006" in req_number  # 5 + 1 = 006

    def test_create_requisition_success(self, service, mock_req_repo, mock_inv_repo):
        """Create requisition should validate and save."""
        mock_location = Mock()
        mock_location.id = 1
        mock_location.name = "Test Location"
        mock_req_repo.get_location.return_value = mock_location

        mock_item = Mock()
        mock_item.id = 1
        mock_item.name = "Test Item"
        mock_req_repo.get_item.return_value = mock_item

        mock_requisition = Mock()
        mock_requisition.id = 1
        mock_requisition.requisition_number = "REQ-20260409-001"
        mock_requisition.location = mock_location
        mock_requisition.items = []
        mock_requisition.status = "PENDING"
        mock_requisition.created_at = datetime.now(timezone.utc)
        mock_requisition.updated_at = datetime.now(timezone.utc)
        mock_req_repo.create.return_value = mock_requisition
        mock_req_repo.count_by_prefix.return_value = 0

        result = service.create_requisition(
            location_id=1,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            items=[{"item_id": 1, "quantity": 10}],
        )

        assert result["success"] is True
        assert "REQ-" in result["data"]["requisition_number"]
        mock_req_repo.commit.assert_called_once()

    def test_create_requisition_invalid_location(self, service, mock_req_repo):
        """Create requisition with invalid location should fail."""
        mock_req_repo.get_location.return_value = None

        with pytest.raises(NotFoundError, match="Location"):
            service.create_requisition(
                location_id=999,
                requested_by="testuser",
                department="Pharmacy",
                urgency="NORMAL",
                items=[{"item_id": 1, "quantity": 10}],
            )

    def test_create_requisition_invalid_urgency(self, service, mock_req_repo):
        """Create requisition with invalid urgency should fail."""
        mock_location = Mock()
        mock_req_repo.get_location.return_value = mock_location

        with pytest.raises(ValidationError, match="Invalid urgency level"):
            service.create_requisition(
                location_id=1,
                requested_by="testuser",
                department="Pharmacy",
                urgency="INVALID",
                items=[{"item_id": 1, "quantity": 10}],
            )

    def test_create_requisition_invalid_item(self, service, mock_req_repo):
        """Create requisition with invalid item should fail."""
        mock_location = Mock()
        mock_req_repo.get_location.return_value = mock_location
        mock_req_repo.get_item.return_value = None

        with pytest.raises(NotFoundError, match="Item"):
            service.create_requisition(
                location_id=1,
                requested_by="testuser",
                department="Pharmacy",
                urgency="NORMAL",
                items=[{"item_id": 999, "quantity": 10}],
            )

    def test_create_requisition_zero_quantity(self, service, mock_req_repo):
        """Create requisition with zero quantity should fail."""
        mock_location = Mock()
        mock_req_repo.get_location.return_value = mock_location
        mock_item = Mock()
        mock_item.name = "Test Item"
        mock_req_repo.get_item.return_value = mock_item

        with pytest.raises(ValidationError, match="Quantity must be positive"):
            service.create_requisition(
                location_id=1,
                requested_by="testuser",
                department="Pharmacy",
                urgency="NORMAL",
                items=[{"item_id": 1, "quantity": 0}],
            )

    def test_approve_requisition_success(self, service, mock_req_repo, mock_inv_repo):
        """Approve requisition should deduct stock."""
        mock_req = Mock()
        mock_req.id = 1
        mock_req.status = "PENDING"
        mock_req.location_id = 1
        mock_req.requisition_number = "REQ-20260409-001"
        mock_req.department = "Pharmacy"

        mock_item = Mock()
        mock_item.item_id = 1
        mock_item.quantity_requested = 10
        mock_item.quantity_approved = None
        mock_req.items = [mock_item]

        mock_req_repo.get_by_id.return_value = mock_req

        mock_req_item = Mock()
        mock_req_item.id = 1
        mock_req_item.name = "Test Item"
        mock_req_repo.get_item.return_value = mock_req_item

        mock_latest_tx = Mock()
        mock_latest_tx.closing_stock = 50
        mock_inv_repo.get_latest_transaction.return_value = mock_latest_tx

        mock_new_tx = Mock()
        mock_new_tx.id = 100
        mock_inv_repo.create_transaction.return_value = mock_new_tx

        result = service.approve_requisition(
            requisition_id=1,
            approved_by="manager",
        )

        assert result["success"] is True
        assert mock_req.status == "APPROVED"
        mock_req_repo.commit.assert_called()

    def test_approve_requisition_not_pending(self, service, mock_req_repo):
        """Approve non-pending requisition should fail."""
        mock_req = Mock()
        mock_req.status = "APPROVED"
        mock_req_repo.get_by_id.return_value = mock_req

        with pytest.raises(InvalidStateError, match="already APPROVED"):
            service.approve_requisition(requisition_id=1, approved_by="manager")

    def test_approve_requisition_insufficient_stock(self, service, mock_req_repo, mock_inv_repo):
        """Approve requisition with insufficient stock should fail."""
        mock_req = Mock()
        mock_req.id = 1
        mock_req.status = "PENDING"
        mock_req.location_id = 1

        mock_item = Mock()
        mock_item.item_id = 1
        mock_item.quantity_requested = 100
        mock_item.quantity_approved = None
        mock_req.items = [mock_item]

        mock_req_repo.get_by_id.return_value = mock_req

        mock_req_item = Mock()
        mock_req_item.name = "Test Item"
        mock_req_repo.get_item.return_value = mock_req_item

        mock_latest_tx = Mock()
        mock_latest_tx.closing_stock = 10  # Not enough
        mock_inv_repo.get_latest_transaction.return_value = mock_latest_tx

        with pytest.raises(InsufficientStockError, match="Insufficient stock"):
            service.approve_requisition(requisition_id=1, approved_by="manager")

    def test_reject_requisition_success(self, service, mock_req_repo):
        """Reject requisition should update status."""
        mock_req = Mock()
        mock_req.status = "PENDING"
        mock_req.requisition_number = "REQ-20260409-002"
        mock_req_repo.get_by_id.return_value = mock_req

        result = service.reject_requisition(
            requisition_id=1,
            rejected_by="manager",
            reason="Out of budget",
        )

        assert result["success"] is True
        assert mock_req.status == "REJECTED"
        assert mock_req.rejection_reason == "Out of budget"
        mock_req_repo.commit.assert_called_once()

    def test_reject_requisition_not_pending(self, service, mock_req_repo):
        """Reject non-pending requisition should fail."""
        mock_req = Mock()
        mock_req.status = "APPROVED"
        mock_req_repo.get_by_id.return_value = mock_req

        with pytest.raises(InvalidStateError, match="already APPROVED"):
            service.reject_requisition(
                requisition_id=1,
                rejected_by="manager",
                reason="Too late",
            )

    def test_cancel_requisition_success(self, service, mock_req_repo):
        """Cancel pending requisition should succeed."""
        mock_req = Mock()
        mock_req.status = "PENDING"
        mock_req.requisition_number = "REQ-20260409-003"
        mock_req_repo.get_by_id.return_value = mock_req

        result = service.cancel_requisition(requisition_id=1, cancelled_by="testuser")

        assert result["success"] is True
        assert mock_req.status == "CANCELLED"
        mock_req_repo.commit.assert_called_once()

    def test_cancel_requisition_not_pending(self, service, mock_req_repo):
        """Cancel non-pending requisition should fail."""
        mock_req = Mock()
        mock_req.status = "APPROVED"
        mock_req_repo.get_by_id.return_value = mock_req

        with pytest.raises(InvalidStateError, match="Only PENDING requisitions"):
            service.cancel_requisition(requisition_id=1, cancelled_by="testuser")

    def test_get_stats(self, service, mock_req_repo):
        """Get stats should return requisition counts."""
        mock_req_repo.count_total.return_value = 100
        mock_req_repo.count_by_status.side_effect = [20, 10]  # PENDING, REJECTED
        mock_req_repo.count_approved_today.return_value = 5
        mock_req_repo.count_emergency_pending.return_value = 3

        stats = service.get_stats()

        assert stats["total"] == 100
        assert stats["pending"] == 20
        assert stats["approved_today"] == 5
        assert stats["rejected"] == 10
        assert stats["emergency_pending"] == 3
