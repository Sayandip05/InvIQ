"""
Inventory service — business logic layer.

Receives an InventoryRepository via the constructor (injected by FastAPI DI).
Contains only business rules; all DB queries are delegated to the repository.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional

from app.repositories.inventory_repo import InventoryRepository
from app.core.exceptions import InsufficientStockError

logger = logging.getLogger("smart_inventory.service.inventory")


class InventoryService:

    def __init__(self, repo: InventoryRepository):
        self.repo = repo

    def add_transaction(
        self,
        location_id: int,
        item_id: int,
        transaction_date: date,
        received: int,
        issued: int,
        notes: Optional[str] = None,
        entered_by: str = "staff",
    ) -> Dict[str, Any]:
        """
        Add a new inventory transaction.

        Automatically calculates opening_stock and closing_stock.
        """
        try:
            # Get previous day's closing stock as opening stock
            previous = self.repo.get_previous_transaction(
                location_id, item_id, transaction_date
            )

            if previous:
                opening_stock = previous.closing_stock
            else:
                item = self.repo.get_item_by_id(item_id)
                opening_stock = item.min_stock if item else 0

            closing_stock = opening_stock + received - issued

            if closing_stock < 0:
                return {
                    "success": False,
                    "error": f"Invalid transaction: closing stock cannot be negative (would be {closing_stock})",
                }

            tx = self.repo.create_transaction(
                location_id=location_id,
                item_id=item_id,
                date=transaction_date,
                opening_stock=opening_stock,
                received=received,
                issued=issued,
                closing_stock=closing_stock,
                notes=notes,
                entered_by=entered_by,
            )

            return {
                "success": True,
                "message": "Transaction added successfully",
                "data": {
                    "id": tx.id,
                    "opening_stock": opening_stock,
                    "received": received,
                    "issued": issued,
                    "closing_stock": closing_stock,
                    "date": str(transaction_date),
                },
            }

        except Exception as e:
            self.repo.rollback()
            return {"success": False, "error": str(e)}

    def bulk_add_transactions(
        self,
        location_id: int,
        transaction_date: date,
        items_data: list,
        entered_by: str = "staff",
    ) -> Dict[str, Any]:
        """Add multiple transactions at once (for daily batch entry)."""
        try:
            results = []
            errors = []

            for item_data in items_data:
                result = self.add_transaction(
                    location_id=location_id,
                    item_id=item_data["item_id"],
                    transaction_date=transaction_date,
                    received=item_data.get("received", 0),
                    issued=item_data.get("issued", 0),
                    notes=item_data.get("notes"),
                    entered_by=entered_by,
                )

                if result["success"]:
                    results.append(result["data"])
                else:
                    errors.append(
                        {"item_id": item_data["item_id"], "error": result["error"]}
                    )

            return {
                "success": len(errors) == 0,
                "message": f"Processed {len(results)} transactions, {len(errors)} errors",
                "data": {"successful": results, "failed": errors},
            }

        except Exception as e:
            self.repo.rollback()
            return {"success": False, "error": str(e)}

    def get_latest_stock(self, location_id: int, item_id: int) -> Optional[int]:
        """Get most recent closing stock for an item at a location."""
        latest = self.repo.get_latest_transaction(location_id, item_id)
        return latest.closing_stock if latest else None

    def get_location_items(self, location_id: int) -> list:
        """Get all items for a location with their current stock and status."""
        items = self.repo.get_all_items()

        result = []
        for item in items:
            latest_stock = self.get_latest_stock(location_id, item.id) or 0

            if latest_stock <= (item.min_stock * 0.5):
                status = "CRITICAL"
            elif latest_stock <= item.min_stock:
                status = "WARNING"
            else:
                status = "HEALTHY"

            result.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "unit": item.unit,
                    "min_stock": item.min_stock,
                    "current_stock": latest_stock,
                    "status": status,
                }
            )

        return result

    # ── Keep backward-compatible static methods for code that hasn't migrated yet ──

    @staticmethod
    def add_transaction_static(db, **kwargs) -> Dict[str, Any]:
        """Legacy static method — used by RequisitionService until it's fully migrated."""
        from app.repositories.inventory_repo import InventoryRepository

        repo = InventoryRepository(db)
        svc = InventoryService(repo)
        return svc.add_transaction(**kwargs)

    @staticmethod
    def get_latest_stock_static(db, location_id: int, item_id: int) -> Optional[int]:
        """Legacy static method."""
        from app.repositories.inventory_repo import InventoryRepository

        repo = InventoryRepository(db)
        svc = InventoryService(repo)
        return svc.get_latest_stock(location_id, item_id)