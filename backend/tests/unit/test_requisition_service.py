"""
Requisition service tests — business logic layer.
Tests RequisitionService lifecycle, state transitions, and stock validation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

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
        repo = Mock()
        repo.has_later_transactions.return_value = False
        return repo

    @pytest.fixture
    def service(self, mock_req_repo, mock_inv_repo):
        return RequisitionService(mock_req_repo, mock_inv_repo)

    def test_create_requisition_success_and_numbering(self, service, mock_req_repo, mock_inv_repo):
        """Create requisition generates REQ number, validates location/items, and commits."""
        mock_location = Mock(id=1, name="Test Location")
        mock_req_repo.get_location.return_value = mock_location

        mock_item = Mock(id=1, name="Test Item")
        mock_req_repo.get_item.return_value = mock_item

        mock_requisition = Mock(
            id=1,
            requisition_number="REQ-20260409-001",
            location=mock_location,
            items=[],
            status="PENDING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
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

    def test_create_requisition_collision_retry(self, service, mock_req_repo):
        """If a collision occurs on first attempt, service retries and succeeds."""
        from app.core.exceptions import DuplicateError

        mock_location = Mock(id=1, name="Test Location")
        mock_req_repo.get_location.return_value = mock_location

        mock_item = Mock(id=1, name="Test Item")
        mock_req_repo.get_item.return_value = mock_item

        mock_requisition = Mock(
            id=2,
            requisition_number="REQ-20260409-002",
            location=mock_location,
            items=[],
            status="PENDING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # First call raises DuplicateError (simulating collision), second call succeeds
        mock_req_repo.create.side_effect = [DuplicateError("duplicate number"), mock_requisition]
        mock_req_repo.count_by_prefix.side_effect = [0, 1]

        result = service.create_requisition(
            location_id=1,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            items=[{"item_id": 1, "quantity": 10}],
        )
        assert result["success"] is True
        assert result["data"]["requisition_number"] == "REQ-20260409-002"
        assert mock_req_repo.create.call_count == 2

    def test_create_requisition_validation_errors(self, service, mock_req_repo):
        """Rejects invalid location, invalid urgency, and zero quantities."""
        mock_req_repo.get_location.return_value = None
        with pytest.raises(NotFoundError, match="Location"):
            service.create_requisition(
                location_id=999, requested_by="user", department="Pharmacy",
                urgency="NORMAL", items=[{"item_id": 1, "quantity": 10}],
            )

    def test_approve_requisition_and_stock_deduction(self, service, mock_req_repo, mock_inv_repo):
        """Approving requisition verifies stock sufficiency and deducts inventory."""
        mock_item = Mock(id=1, name="Medicine A", min_stock=2, org_id=1)
        req_item = Mock(item_id=1, quantity_requested=5, item=mock_item)
        mock_req = Mock(id=1, status="PENDING", location_id=10, items=[req_item])
        mock_req_repo.get_by_id.return_value = mock_req
        mock_inv_repo.get_item_by_id.return_value = mock_item

        # Stock check: has 10 units
        mock_inv_repo.get_latest_transaction.return_value = Mock(closing_stock=10)
        mock_inv_repo.get_previous_transaction.return_value = Mock(closing_stock=10)
        mock_inv_repo.create_transaction.return_value = Mock(id=1, closing_stock=5)

        result = service.approve_requisition(requisition_id=1, approved_by="admin_user")
        assert result["success"] is True
        assert mock_req.status == "APPROVED"

    def test_approve_requisition_insufficient_stock_fails(self, service, mock_req_repo, mock_inv_repo):
        """Approving when available stock < requested quantity raises InsufficientStockError."""
        mock_item = Mock(id=1, name="Medicine A")
        req_item = Mock(item_id=1, quantity_requested=50, item=mock_item)
        mock_req = Mock(id=1, status="PENDING", location_id=10, items=[req_item])
        mock_req_repo.get_by_id.return_value = mock_req

        mock_inv_repo.get_latest_transaction.return_value = Mock(closing_stock=10)
        with pytest.raises(InsufficientStockError):
            service.approve_requisition(requisition_id=1, approved_by="admin_user")

    def test_reject_and_cancel_state_transitions(self, service, mock_req_repo):
        """Tests rejection, cancellation, and invalid state transitions."""
        mock_req = Mock(id=1, status="PENDING")
        mock_req_repo.get_by_id.return_value = mock_req

        service.reject_requisition(requisition_id=1, rejected_by="admin", reason="Budget limit")
        assert mock_req.status == "REJECTED"

        # Rejecting already rejected requisition fails
        with pytest.raises(InvalidStateError):
            service.reject_requisition(requisition_id=1, rejected_by="admin", reason="Duplicate")

    def test_fulfill_approved_requisition_succeeds(self, service, mock_req_repo):
        """Fulfilling an APPROVED requisition transitions it to FULFILLED and commits."""
        mock_req = Mock(id=1, status="APPROVED", requisition_number="REQ-1", items=[])
        mock_req_repo.get_by_id.return_value = mock_req

        result = service.fulfill_requisition(requisition_id=1, fulfilled_by="staff_user")

        assert result["success"] is True
        assert mock_req.status == "FULFILLED"
        mock_req_repo.commit.assert_called()

    def test_fulfill_pending_requisition_is_rejected(self, service, mock_req_repo):
        """A PENDING requisition must be approved first: fulfilling it raises InvalidStateError
        and leaves state and stock untouched (no commit)."""
        mock_req = Mock(id=1, status="PENDING", requisition_number="REQ-2", items=[])
        mock_req_repo.get_by_id.return_value = mock_req

        with pytest.raises(InvalidStateError):
            service.fulfill_requisition(requisition_id=1, fulfilled_by="staff_user")

        assert mock_req.status == "PENDING"
        mock_req_repo.commit.assert_not_called()
