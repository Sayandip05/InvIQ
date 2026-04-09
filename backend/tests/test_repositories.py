"""
Repository tests — database layer.

Tests the infrastructure/database repositories.
"""

import pytest
from datetime import date, datetime, timezone

from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.requisition_repo import RequisitionRepository
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.models import Location, Item, InventoryTransaction, User, Requisition
from app.core.exceptions import DuplicateError, DatabaseError


class TestInventoryRepository:
    """Test inventory repository database operations."""

    def test_create_location(self, db):
        """Create location should save to database."""
        repo = InventoryRepository(db)
        location = repo.create_location(
            name="Test Warehouse",
            type="warehouse",
            region="North",
        )
        assert location.id is not None
        assert location.name == "Test Warehouse"

    def test_create_duplicate_location(self, db):
        """Create duplicate location should raise DuplicateError."""
        repo = InventoryRepository(db)
        repo.create_location(name="Duplicate", type="clinic", region="South")
        
        with pytest.raises(DuplicateError):
            repo.create_location(name="Duplicate", type="clinic", region="South")

    def test_get_location_by_id(self, db):
        """Get location by ID should return location."""
        repo = InventoryRepository(db)
        location = repo.create_location(name="Find Me", type="clinic", region="East")
        
        found = repo.get_location_by_id(location.id)
        assert found is not None
        assert found.name == "Find Me"

    def test_get_location_by_name(self, db):
        """Get location by name should return location."""
        repo = InventoryRepository(db)
        repo.create_location(name="Named Location", type="warehouse", region="West")
        
        found = repo.get_location_by_name("Named Location")
        assert found is not None
        assert found.type == "warehouse"

    def test_create_item(self, db):
        """Create item should save to database."""
        repo = InventoryRepository(db)
        item = repo.create_item(
            name="Test Medicine",
            category="medicine",
            unit="box",
            lead_time_days=7,
            min_stock=50,
        )
        assert item.id is not None
        assert item.name == "Test Medicine"

    def test_create_duplicate_item(self, db):
        """Create duplicate item should raise DuplicateError."""
        repo = InventoryRepository(db)
        repo.create_item(name="Duplicate Item", category="supplies", unit="pack", lead_time_days=5, min_stock=20)
        
        with pytest.raises(DuplicateError):
            repo.create_item(name="Duplicate Item", category="supplies", unit="pack", lead_time_days=5, min_stock=20)

    def test_get_item_by_id(self, db):
        """Get item by ID should return item."""
        repo = InventoryRepository(db)
        item = repo.create_item(name="Find Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        
        found = repo.get_item_by_id(item.id)
        assert found is not None
        assert found.name == "Find Item"

    def test_create_transaction(self, db):
        """Create transaction should save to database."""
        repo = InventoryRepository(db)
        location = repo.create_location(name="TX Location", type="clinic", region="Test")
        item = repo.create_item(name="TX Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        
        tx = repo.create_transaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 9),
            opening_stock=0,
            received=100,
            issued=0,
            closing_stock=100,
            entered_by="testuser",
        )
        assert tx.id is not None
        assert tx.closing_stock == 100

    def test_get_latest_transaction(self, db):
        """Get latest transaction should return most recent."""
        repo = InventoryRepository(db)
        location = repo.create_location(name="Latest Location", type="clinic", region="Test")
        item = repo.create_item(name="Latest Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        
        repo.create_transaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 1),
            opening_stock=0,
            received=100,
            issued=0,
            closing_stock=100,
            entered_by="testuser",
        )
        repo.create_transaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 5),
            opening_stock=100,
            received=50,
            issued=0,
            closing_stock=150,
            entered_by="testuser",
        )
        
        latest = repo.get_latest_transaction(location.id, item.id)
        assert latest is not None
        assert latest.closing_stock == 150
        assert latest.date == date(2026, 4, 5)

    def test_get_previous_transaction(self, db):
        """Get previous transaction should return transaction before date."""
        repo = InventoryRepository(db)
        location = repo.create_location(name="Prev Location", type="clinic", region="Test")
        item = repo.create_item(name="Prev Item", category="medicine", unit="box", lead_time_days=7, min_stock=50)
        
        repo.create_transaction(
            location_id=location.id,
            item_id=item.id,
            date=date(2026, 4, 1),
            opening_stock=0,
            received=100,
            issued=0,
            closing_stock=100,
            entered_by="testuser",
        )
        
        prev = repo.get_previous_transaction(location.id, item.id, date(2026, 4, 5))
        assert prev is not None
        assert prev.closing_stock == 100


class TestRequisitionRepository:
    """Test requisition repository database operations."""

    def test_create_requisition(self, db):
        """Create requisition should save to database."""
        from app.infrastructure.database.models import Location
        
        location = Location(name="Req Location", type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)
        
        repo = RequisitionRepository(db)
        req = repo.create(
            requisition_number="REQ-TEST-001",
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        assert req.id is not None
        assert req.requisition_number == "REQ-TEST-001"

    def test_get_by_id(self, db):
        """Get requisition by ID should return requisition."""
        from app.infrastructure.database.models import Location
        
        location = Location(name="Get Location", type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)
        
        repo = RequisitionRepository(db)
        req = repo.create(
            requisition_number="REQ-GET-001",
            location_id=location.id,
            requested_by="testuser",
            department="Pharmacy",
            urgency="NORMAL",
            status="PENDING",
        )
        repo.commit()
        
        found = repo.get_by_id(req.id)
        assert found is not None
        assert found.requisition_number == "REQ-GET-001"

    def test_count_by_prefix(self, db):
        """Count by prefix should return matching count."""
        from app.infrastructure.database.models import Location
        
        location = Location(name="Count Location", type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)
        
        repo = RequisitionRepository(db)
        repo.create(requisition_number="REQ-20260409-001", location_id=location.id, requested_by="user1", department="Pharmacy", urgency="NORMAL", status="PENDING")
        repo.create(requisition_number="REQ-20260409-002", location_id=location.id, requested_by="user2", department="Pharmacy", urgency="NORMAL", status="PENDING")
        repo.commit()
        
        count = repo.count_by_prefix("REQ-20260409-")
        assert count == 2

    def test_count_by_status(self, db):
        """Count by status should return matching count."""
        from app.infrastructure.database.models import Location
        
        location = Location(name="Status Location", type="clinic", region="Test")
        db.add(location)
        db.commit()
        db.refresh(location)
        
        repo = RequisitionRepository(db)
        repo.create(requisition_number="REQ-STATUS-001", location_id=location.id, requested_by="user1", department="Pharmacy", urgency="NORMAL", status="PENDING")
        repo.create(requisition_number="REQ-STATUS-002", location_id=location.id, requested_by="user2", department="Pharmacy", urgency="NORMAL", status="APPROVED")
        repo.commit()
        
        pending_count = repo.count_by_status("PENDING")
        approved_count = repo.count_by_status("APPROVED")
        assert pending_count == 1
        assert approved_count == 1


class TestUserRepository:
    """Test user repository database operations."""

    def test_create_user(self, db):
        """Create user should save to database."""
        repo = UserRepository(db)
        user = repo.create(
            email="newuser@example.com",
            username="newuser",
            password="password123",
            full_name="New User",
            role="staff",
        )
        assert user.id is not None
        assert user.username == "newuser"
        assert user.hashed_password != "password123"  # Should be hashed

    def test_create_duplicate_user(self, db):
        """Create duplicate user should raise DuplicateError."""
        repo = UserRepository(db)
        repo.create(email="dup@example.com", username="dupuser", password="pass123")
        
        with pytest.raises(DuplicateError):
            repo.create(email="dup@example.com", username="dupuser", password="pass123")

    def test_get_by_username(self, db):
        """Get user by username should return user."""
        repo = UserRepository(db)
        repo.create(email="find@example.com", username="findme", password="pass123")
        
        found = repo.get_by_username("findme")
        assert found is not None
        assert found.email == "find@example.com"

    def test_get_by_email(self, db):
        """Get user by email should return user."""
        repo = UserRepository(db)
        repo.create(email="email@example.com", username="emailuser", password="pass123")
        
        found = repo.get_by_email("email@example.com")
        assert found is not None
        assert found.username == "emailuser"

    def test_increment_login_attempts(self, db):
        """Increment login attempts should increase counter."""
        repo = UserRepository(db)
        user = repo.create(email="attempts@example.com", username="attemptsuser", password="pass123")
        
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 1
        
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 2

    def test_reset_login_attempts(self, db):
        """Reset login attempts should clear counter."""
        repo = UserRepository(db)
        user = repo.create(email="reset@example.com", username="resetuser", password="pass123")
        
        user = repo.increment_login_attempts(user)
        user = repo.increment_login_attempts(user)
        assert user.login_attempts == 2
        
        user = repo.reset_login_attempts(user)
        assert user.login_attempts == 0

    def test_record_login(self, db):
        """Record login should update last_login_at."""
        repo = UserRepository(db)
        user = repo.create(email="login@example.com", username="loginuser", password="pass123")
        
        assert user.last_login_at is None
        
        user = repo.record_login(user)
        assert user.last_login_at is not None
        assert user.login_attempts == 0

    def test_count_filtered(self, db):
        """Count filtered should return matching count."""
        repo = UserRepository(db)
        repo.create(email="admin1@example.com", username="admin1", password="pass123", role="admin")
        repo.create(email="staff1@example.com", username="staff1", password="pass123", role="staff")
        repo.create(email="staff2@example.com", username="staff2", password="pass123", role="staff")
        
        admin_count = repo.count_filtered(role="admin")
        staff_count = repo.count_filtered(role="staff")
        assert admin_count >= 1
        assert staff_count >= 2
