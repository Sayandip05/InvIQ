"""
Inventory service — business logic layer.

Receives an InventoryRepository via the constructor (injected by FastAPI DI).
Contains only business rules; all DB queries are delegated to the repository.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional

from app.infrastructure.database.inventory_repo import InventoryRepository
from app.core.exceptions import InsufficientStockError, ValidationError, DatabaseError

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
        flush_only: bool = False,
    ) -> Dict[str, Any]:
        try:
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
                raise ValidationError(
                    f"Invalid transaction: closing stock cannot be negative (would be {closing_stock})"
                )

            tx = self.repo.create_transaction(
                flush_only=flush_only,
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

            # ── Stock alert detection ───────────────────────────────────
            item = self.repo.get_item_by_id(item_id)
            if item and closing_stock <= item.min_stock:
                alert_status = "CRITICAL" if closing_stock <= 0 else "WARNING"
                logger.warning(
                    "Stock alert [%s]: %s at location %d — stock=%d, min=%d",
                    alert_status, item.name, location_id, closing_stock, item.min_stock,
                )
                # Queue alert for WebSocket broadcast
                from app.api.routes.websocket import pending_alerts
                pending_alerts.append({
                    "type": "low_stock_alert",
                    "status": alert_status,
                    "item_name": item.name,
                    "item_id": item_id,
                    "location_id": location_id,
                    "current_stock": closing_stock,
                    "min_stock": item.min_stock,
                })

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

        except (ValidationError, DatabaseError):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in add_transaction: %s", str(e))
            raise DatabaseError(f"Failed to add transaction: {str(e)}")

    def bulk_add_transactions(
        self,
        location_id: int,
        transaction_date: date,
        items_data: list,
        entered_by: str = "staff",
    ) -> Dict[str, Any]:
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
                        {"item_id": item_data["item_id"], "error": result.get("error")}
                    )

            return {
                "success": len(errors) == 0,
                "message": f"Processed {len(results)} transactions, {len(errors)} errors",
                "data": {"successful": results, "failed": errors},
            }

        except (ValidationError, DatabaseError):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in bulk_add_transactions: %s", str(e))
            raise DatabaseError(f"Failed to process bulk transactions: {str(e)}")

    def get_latest_stock(self, location_id: int, item_id: int) -> Optional[int]:
        latest = self.repo.get_latest_transaction(location_id, item_id)
        return latest.closing_stock if latest else None

    def get_location_items(self, location_id: int) -> list:
        """
        Return stock status for every item at the given location.

        Uses a single batch query (get_latest_stocks_for_location) instead of
        N+1 individual queries — critical for performance over remote DB connections.
        """
        items = self.repo.get_all_items()

        # Single query: {item_id: closing_stock} for all items at this location
        stock_map = self.repo.get_latest_stocks_for_location(location_id)

        result = []
        for item in items:
            latest_stock = stock_map.get(item.id, 0)

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

    @staticmethod
    def add_transaction_static(db, **kwargs) -> Dict[str, Any]:
        from app.infrastructure.database.inventory_repo import InventoryRepository

        repo = InventoryRepository(db)
        svc = InventoryService(repo)
        return svc.add_transaction(**kwargs)

    @staticmethod
    def get_latest_stock_static(db, location_id: int, item_id: int) -> Optional[int]:
        from app.infrastructure.database.inventory_repo import InventoryRepository

        repo = InventoryRepository(db)
        svc = InventoryService(repo)
        return svc.get_latest_stock(location_id, item_id)
