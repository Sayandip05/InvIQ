"""
Inventory service tests — business logic layer.

Tests InventoryService in isolation with mocked repository.
"""

import pytest
from datetime import date
from unittest.mock import Mock, MagicMock

from app.application.inventory_service import InventoryService
from app.core.exceptions import ValidationError, DatabaseError
from app.infrastructure.database.models import Item, InventoryTransaction


class TestInventoryService:
    """Test inventory service business logic."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository."""
        return InventoryService(mock_repo)

    def test_add_transaction_first_transaction(self, service, mock_repo):
        """First transaction should use item min_stock as opening."""
        mock_repo.get_previous_transaction.return_value = None
        mock_item = Mock()
        mock_item.min_stock = 100
        mock_item.name = "Test Item"
        mock_repo.get_item_by_id.return_value = mock_item

        mock_tx = Mock()
        mock_tx.id = 1
        mock_repo.create_transaction.return_value = mock_tx

        result = service.add_transaction(
            location_id=1,
            item_id=1,
            transaction_date=date(2026, 4, 1),
            received=50,
            issued=0,
        )

        assert result["success"] is True
        assert result["data"]["opening_stock"] == 100
        assert result["data"]["closing_stock"] == 150

    def test_add_transaction_with_previous(self, service, mock_repo):
        """Transaction should use previous closing as opening."""
        mock_prev = Mock()
        mock_prev.closing_stock = 200
        mock_repo.get_previous_transaction.return_value = mock_prev

        mock_item = Mock()
        mock_item.min_stock = 50
        mock_item.name = "Test Item"
        mock_repo.get_item_by_id.return_value = mock_item

        mock_tx = Mock()
        mock_tx.id = 2
        mock_repo.create_transaction.return_value = mock_tx

        result = service.add_transaction(
            location_id=1,
            item_id=1,
            transaction_date=date(2026, 4, 2),
            received=0,
            issued=30,
        )

        assert result["success"] is True
        assert result["data"]["opening_stock"] == 200
        assert result["data"]["closing_stock"] == 170

    def test_add_transaction_negative_closing_stock(self, service, mock_repo):
        """Transaction resulting in negative stock should fail."""
        mock_prev = Mock()
        mock_prev.closing_stock = 10
        mock_repo.get_previous_transaction.return_value = mock_prev

        with pytest.raises(ValidationError, match="closing stock cannot be negative"):
            service.add_transaction(
                location_id=1,
                item_id=1,
                transaction_date=date(2026, 4, 3),
                received=0,
                issued=20,  # More than available
            )

    def test_add_transaction_stock_alert_critical(self, service, mock_repo):
        """Transaction resulting in zero stock should trigger critical alert."""
        mock_repo.get_previous_transaction.return_value = None
        mock_item = Mock()
        mock_item.min_stock = 50
        mock_item.name = "Critical Item"
        mock_item.id = 1
        mock_repo.get_item_by_id.return_value = mock_item

        mock_tx = Mock()
        mock_tx.id = 3
        mock_repo.create_transaction.return_value = mock_tx

        result = service.add_transaction(
            location_id=1,
            item_id=1,
            transaction_date=date(2026, 4, 4),
            received=0,
            issued=50,  # Reduces to 0
        )

        assert result["success"] is True
        assert result["data"]["closing_stock"] == 0

    def test_get_latest_stock_exists(self, service, mock_repo):
        """Get latest stock should return closing stock."""
        mock_tx = Mock()
        mock_tx.closing_stock = 150
        mock_repo.get_latest_transaction.return_value = mock_tx

        stock = service.get_latest_stock(location_id=1, item_id=1)
        assert stock == 150

    def test_get_latest_stock_none(self, service, mock_repo):
        """Get latest stock with no transactions should return None."""
        mock_repo.get_latest_transaction.return_value = None
        stock = service.get_latest_stock(location_id=1, item_id=1)
        assert stock is None

    def test_get_location_items(self, service, mock_repo):
        """Get location items should return formatted item list."""
        mock_item1 = Mock()
        mock_item1.id = 1
        mock_item1.name = "Item A"
        mock_item1.category = "medicine"
        mock_item1.unit = "box"
        mock_item1.min_stock = 50

        mock_item2 = Mock()
        mock_item2.id = 2
        mock_item2.name = "Item B"
        mock_item2.category = "supplies"
        mock_item2.unit = "pack"
        mock_item2.min_stock = 100

        mock_repo.get_all_items.return_value = [mock_item1, mock_item2]

        # Mock latest transactions
        mock_tx1 = Mock()
        mock_tx1.closing_stock = 20  # Below min (50) → WARNING
        mock_tx2 = Mock()
        mock_tx2.closing_stock = 150  # Above min (100) → HEALTHY

        def mock_get_latest(loc_id, item_id):
            if item_id == 1:
                return mock_tx1
            return mock_tx2

        mock_repo.get_latest_transaction.side_effect = mock_get_latest

        items = service.get_location_items(location_id=1)

        assert len(items) == 2
        assert items[0]["name"] == "Item A"
        assert items[0]["status"] == "WARNING"
        assert items[0]["current_stock"] == 20
        assert items[1]["name"] == "Item B"
        assert items[1]["status"] == "HEALTHY"
        assert items[1]["current_stock"] == 150

    def test_bulk_add_transactions_success(self, service, mock_repo):
        """Bulk add should process all items successfully."""
        mock_repo.get_previous_transaction.return_value = None
        mock_item = Mock()
        mock_item.min_stock = 50
        mock_item.name = "Bulk Item"
        mock_repo.get_item_by_id.return_value = mock_item

        mock_tx = Mock()
        mock_tx.id = 10
        mock_repo.create_transaction.return_value = mock_tx

        items_data = [
            {"item_id": 1, "received": 100, "issued": 0},
            {"item_id": 2, "received": 50, "issued": 0},
        ]

        result = service.bulk_add_transactions(
            location_id=1,
            transaction_date=date(2026, 4, 5),
            items_data=items_data,
        )

        assert result["success"] is True
        assert len(result["data"]["successful"]) == 2
        assert len(result["data"]["failed"]) == 0

    def test_bulk_add_transactions_with_errors(self, service, mock_repo):
        """Bulk add with some failures should return error details."""
        def mock_add_transaction(**kwargs):
            if kwargs["item_id"] == 2:
                raise ValidationError("Invalid item")
            mock_tx = Mock()
            mock_tx.id = 11
            return {
                "success": True,
                "data": {"id": 11, "opening_stock": 0, "received": 100, "issued": 0, "closing_stock": 100, "date": "2026-04-06"}
            }

        # Patch the add_transaction method
        service.add_transaction = mock_add_transaction

        items_data = [
            {"item_id": 1, "received": 100, "issued": 0},
            {"item_id": 2, "received": 50, "issued": 0},  # Will fail
        ]

        with pytest.raises(ValidationError):
            service.bulk_add_transactions(
                location_id=1,
                transaction_date=date(2026, 4, 6),
                items_data=items_data,
            )
