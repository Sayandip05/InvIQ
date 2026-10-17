"""
Repository tests — database layer.
Tests the infrastructure/database repositories with high-value consolidated tests.
"""

import pytest
import uuid
from datetime import date

from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.requisition_repo import RequisitionRepository
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.models import Location
from app.core.exceptions import DuplicateError


def _uid(prefix: str = "") -> str:
    """Generate a unique name to avoid cross-test DB contamination."""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class TestInventoryRepository:
    """Test inventory repository database operations."""

    def test_location_and_item_crud(self, db):
        """Verify location and item creation with storage temp flags and querying."""
        repo = InventoryRepository(db)
        loc_name = _uid("warehouse-")
        loc = repo.create_location(org_id=1, name=loc_name, type="warehouse", region="North")
        assert loc.id is not None
        assert repo.get_location_by_name(loc_name).type == "warehouse"

        item = repo.create_item(
            org_id=1,
            name=_uid("Insulin-"),
            category="Diabetic Care",
            unit="vial",
            lead_time_days=5,
            min_stock=500,
            storage_temp="cold_chain",
        )
        assert item.id is not None
        assert item.storage_temp == "cold_chain"
        assert repo.get_item_by_id(item.id).name == item.name

    def test_inventory_transactions_and_timeline(self, db):
        """Verify transaction creation with batch/expiry and latest/previous queries."""
        repo = InventoryRepository(db)
        location = repo.create_location(org_id=1, name=_uid("timeline-loc-"), type="clinic", region="Test")
        item = repo.create_item(org_id=1, name=_uid("timeline-item-"), category="medicine", unit="box", lead_time_days=7, min_stock=50)

        # 1. Inbound with batch info
        tx1 = repo.create_transaction(
            location_id=location.id, item_id=item.id, org_id=1, date=date(2026, 4, 1),
            opening_stock=0, received=100, issued=0, closing_stock=100, entered_by="testuser",
            batch_number="BT-25-001", expiry_date=date(2027, 6, 30),
        )
        assert tx1.batch_number == "BT-25-001"

        # 3. Same-day transactions (e.g. morning receive + afternoon dispense on same date)
        today = date(2026, 4, 10)
        tx3_morning = repo.create_transaction(
            location_id=location.id, item_id=item.id, org_id=1, date=today,
            opening_stock=70, received=50, issued=0, closing_stock=120, entered_by="morning_shift",
        )
        tx4_afternoon = repo.create_transaction(
            location_id=location.id, item_id=item.id, org_id=1, date=today,
            opening_stock=120, received=0, issued=45, closing_stock=75, entered_by="afternoon_shift",
        )

        latest = repo.get_latest_transaction(location.id, item.id)
        assert latest.id == tx4_afternoon.id
        assert latest.closing_stock == 75

        # Verify bulk location stocks mapping selects the true latest record
        stocks_map = repo.get_latest_stocks_for_location(location.id)
        assert stocks_map[item.id] == 75


class TestRequisitionRepository:
    """Test requisition repository database operations."""

    def test_requisition_lifecycle_and_counts(self, db):
        """Create, fetch, and count requisitions by status and prefix."""
        location = Location(org_id=1, name=_uid("req-loc-"), type="clinic", region="Test")
        db.add(location)
        db.commit()

        repo = RequisitionRepository(db)
        unique_prefix = f"REQ-{_uid()}-"
        req = repo.create(
            requisition_number=f"{unique_prefix}001",
            location_id=location.id,
            org_id=location.org_id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        repo.commit()

        assert repo.get_by_id(req.id).requisition_number == f"{unique_prefix}001"
        assert repo.count_by_prefix(unique_prefix) == 1
        assert repo.count_by_status("PENDING") >= 1


class TestUserRepository:
    """Test user repository database operations."""

    def test_user_creation_lookup_and_duplicates(self, db):
        """Test user creation, password hashing, and duplicate detection."""
        repo = UserRepository(db)
        uid = _uid()
        user = repo.create(
            email=f"{uid}@example.com",
            username=f"user-{uid}",
            password="password123",
            full_name="New User",
            role="staff",
        )
        assert user.id is not None
        assert user.hashed_password != "password123"

        found_by_name = repo.get_by_username(f"user-{uid}")
        assert found_by_name is not None
        assert repo.get_by_email(f"{uid}@example.com") is not None

        with pytest.raises(DuplicateError):
            repo.create(email=f"{uid}@example.com", username=f"user2-{uid}", password="pass123")

    def test_login_attempts_and_session_recording(self, db):
        """Test incrementing attempts, resetting on success, and recording login time."""
        repo = UserRepository(db)
        uid = _uid()
        user = repo.create(email=f"attempts-{uid}@example.com", username=f"attempts-{uid}", password="pass123")
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 1

        user = repo.record_login(user)
        assert user.login_attempts == 0
        assert user.last_login_at is not None


class TestMultiTenantExplicitOrgRequired:
    """Ensure repositories reject missing org_id without ever silently falling back to Org 1."""

    def test_create_location_without_org_id_raises_validation_error(self, db):
        from app.core.exceptions import ValidationError
        repo = InventoryRepository(db)
        with pytest.raises(ValidationError, match="Organization ID .* is required"):
            repo.create_location(name="Orphan Location", type="clinic", region="North")

    def test_create_item_without_org_id_raises_validation_error(self, db):
        from app.core.exceptions import ValidationError
        repo = InventoryRepository(db)
        with pytest.raises(ValidationError, match="Organization ID .* is required"):
            repo.create_item(name="Orphan Item", category="Medicine", unit="box")

    def test_create_import_job_without_org_id_raises_validation_error(self, db):
        from app.core.exceptions import ValidationError
        from app.infrastructure.database.data_import_repo import DataImportRepository
        repo = DataImportRepository(db)
        with pytest.raises(ValidationError, match="Organization ID .* is required"):
            repo.create_job(uploaded_by_user_id=1, filename="test.csv", target_entity="item", org_id=None)

    def test_create_invoice_without_org_id_raises_validation_error(self, db):
        from app.core.exceptions import ValidationError
        from app.infrastructure.database.invoice_repo import InvoiceRepository
        repo = InvoiceRepository(db)
        with pytest.raises(ValidationError, match="Organization ID .* is required"):
            repo.create(
                vendor_user_id=1,
                vendor_upload_id=1,
                invoice_number="INV-20260409-999",
                invoice_date=date.today(),
                line_items=[],
                subtotal=0.0,
                tax_amount=0.0,
                total_amount=0.0,
                org_id=None,
            )
