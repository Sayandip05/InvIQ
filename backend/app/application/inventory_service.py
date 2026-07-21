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

import threading
import time

logger = logging.getLogger("smart_inventory.service.inventory")


class InventoryService:
    # Thread-safe class-level cache for admin/manager email lists to avoid DB queries in loops
    _recipients_cache: list[str] = []
    _recipients_cache_expiry: float = 0.0
    _recipients_cache_lock = threading.Lock()

    def __init__(self, repo: InventoryRepository):
        self.repo = repo

    def _get_recipient_emails(self) -> list[str]:
        """Fetch emails of active admins/managers, cached for 60 seconds to avoid querying in loops."""
        now = time.time()
        # Fast path without lock
        if now < InventoryService._recipients_cache_expiry:
            return list(InventoryService._recipients_cache)

        with InventoryService._recipients_cache_lock:
            # Double check under lock
            if now < InventoryService._recipients_cache_expiry:
                return list(InventoryService._recipients_cache)

            try:
                from app.infrastructure.database.models import User
                recipients = [
                    u.email
                    for u in self.repo.db.query(User)
                    .filter(
                        User.role.in_(["admin", "super_admin", "manager"]),
                        User.is_active.is_(True),
                        User.email.isnot(None),
                    )
                    .all()
                ]
                InventoryService._recipients_cache = recipients
                InventoryService._recipients_cache_expiry = now + 60.0  # cache for 60 seconds
                return list(recipients)
            except Exception as e:
                logger.error("Failed to query user recipient emails: %s", e)
                # Return cached value even if stale as fallback
                return list(InventoryService._recipients_cache)

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
        batch_number: Optional[str] = None,
        expiry_date: Optional[date] = None,
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
                batch_number=batch_number,
                expiry_date=expiry_date,
            )

            # ── Stock alert detection ───────────────────────────────────
            item = self.repo.get_item_by_id(item_id)
            if item and closing_stock <= item.min_stock:
                alert_status = "CRITICAL" if closing_stock <= 0 else "WARNING"
                logger.warning(
                    "Stock alert [%s]: %s at location %d — stock=%d, min=%d",
                    alert_status, item.name, location_id, closing_stock, item.min_stock,
                )

                # Queue alert for real-time WebSocket broadcast safely
                from app.api.routes.websocket import queue_websocket_alert
                queue_websocket_alert({
                    "type": "low_stock_alert",
                    "status": alert_status,
                    "item_name": item.name,
                    "item_id": item_id,
                    "location_id": location_id,
                    "current_stock": closing_stock,
                    "min_stock": item.min_stock,
                })

                # ── Email alert to admins & managers ───────────────────
                # Resolve location name and recipient emails, then
                # dispatch in a background thread so SMTP latency never
                # blocks the HTTP transaction response.
                try:
                    from threading import Thread
                    from app.application.notification_service import NotificationService

                    # Fetch email addresses using cached helper
                    recipient_emails = self._get_recipient_emails()

                    # Resolve location name for the email body
                    location = self.repo.get_location_by_id(location_id)
                    location_name = location.name if location else f"Location #{location_id}"

                    if recipient_emails:
                        # Capture all loop variables for the thread closure
                        thread = Thread(
                            target=NotificationService.send_low_stock_alert,
                            kwargs={
                                "recipients":    recipient_emails,
                                "item_name":     item.name,
                                "item_id":       item_id,
                                "location_id":   location_id,
                                "current_stock": closing_stock,
                                "min_stock":     item.min_stock,
                                "alert_status":  alert_status,
                                "location_name": location_name,
                            },
                            daemon=True,  # dies with the main process — no leak
                            name=f"low-stock-email-{item_id}-{location_id}",
                        )
                        thread.start()
                        logger.info(
                            "Low-stock email dispatched (background) for %s @ %s to %d recipient(s)",
                            item.name, location_name, len(recipient_emails),
                        )
                except Exception as email_err:
                    # Email failure must never affect the inventory transaction
                    logger.error("Failed to dispatch low-stock email alert: %s", str(email_err))

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
                    batch_number=item_data.get("batch_number"),
                    expiry_date=item_data.get("expiry_date"),
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
