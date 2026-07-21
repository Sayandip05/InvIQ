"""
Repository tests — database layer.

Tests the infrastructure/database repositories.

All names use uuid4 suffixes to prevent cross-test contamination in the
shared SQLite test_temp.db (function-scoped db fixture rolls back uncommitted
changes, but the repo calls db.commit() so data persists in the file).
"""

import pytest
import uuid
from datetime import date, datetime, timezone

from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.requisition_repo import RequisitionRepository
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.models import Location, Item, InventoryTransaction, User, Requisition
from app.core.exceptions import DuplicateError, DatabaseError


def _uid(prefix: str = "") -> str:
    """Generate a unique name to avoid cross-test DB contamination."""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class TestInventoryRepository:
    """Test inventory repository database operations."""

    def test_create_location(self, db):
        """Create location should save to database."""
        repo = InventoryRepository(db)
        name = _uid("warehouse-")
        location = repo.create_location(name=name, type="warehouse", region="North")
        assert location.id is not None
        assert location.name == name

    def test_create_two_locations_same_name_allowed_at_repo_level(self, db):
        """Repo-level create_location does NOT enforce name uniqueness (done at route).
        The route checks get_location_by_name before calling create_location."""
        repo = InventoryRepository(db)
        name = _uid("same-name-loc-")
        loc1 = repo.create_location(name=name, type="clinic", region="South")
        loc2 = repo.create_location(name=name, type="clinic", region="South")
        # Both succeed at the repo layer — uniqueness is enforced at the route
        assert loc1.id is not None
        assert loc2.id is not None

    def test_get_location_by_id(self, db):
        """Get location by ID should return location."""
        repo = InventoryRepository(db)
        name = _uid("findme-loc-")
        location = repo.create_location(name=name, type="clinic", region="East")
        found = repo.get_location_by_id(location.id)
        assert found is not None
        assert found.name == name

    def test_get_location_by_name(self, db):
        """Get location by name should return location."""
        repo = InventoryRepository(db)
        name = _uid("named-loc-")
        repo.create_location(name=name, type="warehouse", region="West")
        found = repo.get_location_by_name(name)
        assert found is not None
        assert found.type == "warehouse"

    def test_create_item_with_storage_temp(self, db):
        """Create item with storage_temp should persist correctly."""
        repo = InventoryRepository(db)
        item = repo.create_item(
            name=_uid("Insulin Cold Chain "),
            category="Diabetic Care",
            unit="vial",
            lead_time_days=5,
            min_stock=500,
            storage_temp="cold_chain",
        )
        assert item.id is not None
        assert item.storage_temp == "cold_chain"

    def test_create_item_default_storage_temp(self, db):
        """Create item without storage_temp should default to 'ambient'."""
        repo = InventoryRepository(db)
        item = repo.create_item(
            name=_uid("Paracetamol "),
            category="Analgesics",
            unit="box",
            lead_time_days=3,
            min_stock=50,
        )
        assert item.id is not None
        # Default is 'ambient' (set at ORM level)
        assert item.storage_temp == "ambient"

    def test_create_two_items_same_name_allowed_at_repo_level(self, db):
        """Repo-level create_item does NOT enforce name uniqueness (done at route).
        The route checks get_item_by_name before calling create_item."""
        repo = InventoryRepository(db)
        name = _uid("dup-item-")
        item1 = repo.create_item(name=name, category="supplies", unit="pack", lead_time_days=5, min_stock=20)
        item2 = repo.create_item(name=name, category="supplies", unit="pack", lead_time_days=5, min_stock=20)
        # Both succeed at the repo layer — uniqueness is enforced at the route
        assert item1.id is not None
        assert item2.id is not None

    def test_get_item_by_id(self, db):
        """Get item by ID should return item."""
        repo = InventoryRepository(db)
        item = repo.create_item(name=_uid("find-item-"), category="medicine", unit="box", lead_time_days=7, min_stock=50)
        found = repo.get_item_by_id(item.id)
        assert found is not None

    def test_create_transaction_with_batch_info(self, db):
        """Create inbound transaction records batch_number and expiry_date."""
        repo = InventoryRepository(db)
        location = repo.create_location(name=_uid("batch-loc-"), type="warehouse", region="Test")
        item = repo.create_item(name=_uid("Vaccine "), category="Vaccines", unit="vial",
                                lead_time_days=14, min_stock=200, storage_temp="cold_chain")

        tx = repo.create_transaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 9),
            opening_stock=0,
            received=100,
            issued=0,
            closing_stock=100,
            entered_by="testuser",
            batch_number="BT-25-4821",
            expiry_date=date(2027, 6, 30),
        )
        assert tx.id is not None
        assert tx.closing_stock == 100
        assert tx.batch_number == "BT-25-4821"
        assert tx.expiry_date == date(2027, 6, 30)

    def test_create_transaction_without_batch_info(self, db):
        """Outbound transaction (issued only) leaves batch_number and expiry_date null."""
        repo = InventoryRepository(db)
        location = repo.create_location(name=_uid("no-batch-loc-"), type="clinic", region="Test")
        item = repo.create_item(name=_uid("Drug "), category="medicine", unit="box",
                                lead_time_days=7, min_stock=50)

        tx = repo.create_transaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 9),
            opening_stock=100,
            received=0,
            issued=20,
            closing_stock=80,
            entered_by="testuser",
        )
        assert tx.id is not None
        assert tx.batch_number is None
        assert tx.expiry_date is None

    def test_get_latest_transaction(self, db):
        """Get latest transaction should return most recent."""
        repo = InventoryRepository(db)
        location = repo.create_location(name=_uid("latest-loc-"), type="clinic", region="Test")
        item = repo.create_item(name=_uid("latest-item-"), category="medicine", unit="box",
                                lead_time_days=7, min_stock=50)

        repo.create_transaction(
            location_id=location.id, item_id=item.id, date=date(2026, 4, 1),
            opening_stock=0, received=100, issued=0, closing_stock=100, entered_by="testuser",
        )
        repo.create_transaction(
            location_id=location.id, item_id=item.id, date=date(2026, 4, 5),
            opening_stock=100, received=50, issued=0, closing_stock=150, entered_by="testuser",
        )
        latest = repo.get_latest_transaction(location.id, item.id)
        assert latest is not None
        assert latest.closing_stock == 150
        assert latest.date == date(2026, 4, 5)

    def test_get_previous_transaction(self, db):
        """Get previous transaction should return transaction before date."""
        repo = InventoryRepository(db)
        location = repo.create_location(name=_uid("prev-loc-"), type="clinic", region="Test")
        item = repo.create_item(name=_uid("prev-item-"), category="medicine", unit="box",
                                lead_time_days=7, min_stock=50)

        repo.create_transaction(
            location_id=location.id, item_id=item.id, date=date(2026, 4, 1),
            opening_stock=0, received=100, issued=0, closing_stock=100, entered_by="testuser",
        )
        prev = repo.get_previous_transaction(location.id, item.id, date(2026, 4, 5))
        assert prev is not None
        assert prev.closing_stock == 100


class TestRequisitionRepository:
    """Test requisition repository database operations."""

    def test_create_requisition(self, db):
        """Create requisition should save to database."""
        location = Location(name=_uid("req-loc-"), type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)

        repo = RequisitionRepository(db)
        req_num = f"REQ-{_uid()}"
        req = repo.create(
            requisition_number=req_num,
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        assert req.id is not None
        assert req.requisition_number == req_num

    def test_get_by_id(self, db):
        """Get requisition by ID should return requisition."""
        location = Location(name=_uid("get-req-loc-"), type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)

        repo = RequisitionRepository(db)
        req_num = f"REQ-{_uid()}"
        req = repo.create(
            requisition_number=req_num,
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        repo.commit()

        found = repo.get_by_id(req.id)
        assert found is not None
        assert found.requisition_number == req_num

    def test_count_by_prefix(self, db):
        """Count by prefix should return matching count for a unique prefix."""
        location = Location(name=_uid("cnt-loc-"), type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)

        unique_prefix = f"REQ-{_uid()}-"
        repo = RequisitionRepository(db)
        repo.create(requisition_number=f"{unique_prefix}001", location_id=location.id,
                    requested_by="user1", department="Pharmacy", urgency="NORMAL", status="PENDING")
        repo.create(requisition_number=f"{unique_prefix}002", location_id=location.id,
                    requested_by="user2", department="Pharmacy", urgency="NORMAL", status="PENDING")
        repo.commit()

        count = repo.count_by_prefix(unique_prefix)
        assert count == 2

    def test_count_by_status(self, db):
        """Count by status should increase when requisitions are created."""
        location = Location(name=_uid("status-loc-"), type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)

        repo = RequisitionRepository(db)
        # Get baseline counts BEFORE adding test requisitions
        pending_before = repo.count_by_status("PENDING")
        approved_before = repo.count_by_status("APPROVED")

        unique_suffix = _uid()
        repo.create(requisition_number=f"REQ-P-{unique_suffix}", location_id=location.id,
                    requested_by="user1", department="Pharmacy", urgency="NORMAL", status="PENDING")
        repo.create(requisition_number=f"REQ-A-{unique_suffix}", location_id=location.id,
                    requested_by="user2", department="Pharmacy", urgency="NORMAL", status="APPROVED")
        repo.commit()

        assert repo.count_by_status("PENDING") == pending_before + 1
        assert repo.count_by_status("APPROVED") == approved_before + 1


class TestUserRepository:
    """Test user repository database operations."""

    def test_create_user(self, db):
        """Create user should save to database."""
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
        assert user.hashed_password != "password123"  # Should be hashed

    def test_create_duplicate_user(self, db):
        """Create duplicate user should raise DuplicateError."""
        repo = UserRepository(db)
        uid = _uid()
        repo.create(email=f"dup-{uid}@example.com", username=f"dup-{uid}", password="pass123")
        with pytest.raises(DuplicateError):
            repo.create(email=f"dup-{uid}@example.com", username=f"dup-{uid}", password="pass123")

    def test_get_by_username(self, db):
        """Get user by username should return user."""
        repo = UserRepository(db)
        uid = _uid()
        repo.create(email=f"find-{uid}@example.com", username=f"findme-{uid}", password="pass123")
        found = repo.get_by_username(f"findme-{uid}")
        assert found is not None
        assert found.email == f"find-{uid}@example.com"

    def test_get_by_email(self, db):
        """Get user by email should return user."""
        repo = UserRepository(db)
        uid = _uid()
        repo.create(email=f"email-{uid}@example.com", username=f"emailuser-{uid}", password="pass123")
        found = repo.get_by_email(f"email-{uid}@example.com")
        assert found is not None

    def test_increment_login_attempts(self, db):
        """Increment login attempts should increase counter."""
        repo = UserRepository(db)
        uid = _uid()
        user = repo.create(email=f"attempts-{uid}@example.com", username=f"attempts-{uid}", password="pass123")
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 1
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 2

    def test_reset_login_attempts(self, db):
        """Reset login attempts should clear counter."""
        repo = UserRepository(db)
        uid = _uid()
        user = repo.create(email=f"reset-{uid}@example.com", username=f"reset-{uid}", password="pass123")
        user = repo.increment_login_attempts(user)
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 2
        user = repo.reset_login_attempts(user)
        assert user.login_attempts == 0

    def test_record_login(self, db):
        """Record login should update last_login_at."""
        repo = UserRepository(db)
        uid = _uid()
        user = repo.create(email=f"login-{uid}@example.com", username=f"login-{uid}", password="pass123")
        assert user.last_login_at is None
        user = repo.record_login(user)
        assert user.last_login_at is not None
        assert user.login_attempts == 0

    def test_count_filtered(self, db):
        """Count filtered should return at-least counts including new records."""
        repo = UserRepository(db)
        uid = _uid()
        admin_before = repo.count_filtered(role="admin")
        staff_before = repo.count_filtered(role="staff")

        repo.create(email=f"admin-{uid}@example.com", username=f"admin-{uid}", password="pass123", role="admin")
        repo.create(email=f"staff1-{uid}@example.com", username=f"staff1-{uid}", password="pass123", role="staff")
        repo.create(email=f"staff2-{uid}@example.com", username=f"staff2-{uid}", password="pass123", role="staff")

        assert repo.count_filtered(role="admin") == admin_before + 1
        assert repo.count_filtered(role="staff") == staff_before + 2
