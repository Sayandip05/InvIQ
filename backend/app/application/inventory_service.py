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
    # Thread-safe class-level cache for admin/manager email lists per organization to avoid DB queries in loops
    _recipients_cache: Dict[Optional[int], list[str]] = {}
    _recipients_cache_expiry: Dict[Optional[int], float] = {}
    _recipients_cache_lock = threading.Lock()

    def __init__(self, repo: InventoryRepository):
        self.repo = repo

    def _get_recipient_emails(self, org_id: Optional[int] = None) -> list[str]:
        """Fetch emails of active admins/managers for the organization, cached for 60 seconds."""
        now = time.time()
        # Fast path without lock
        if org_id in InventoryService._recipients_cache and now < InventoryService._recipients_cache_expiry.get(org_id, 0.0):
            return list(InventoryService._recipients_cache[org_id])

        with InventoryService._recipients_cache_lock:
            # Double check under lock
            if org_id in InventoryService._recipients_cache and now < InventoryService._recipients_cache_expiry.get(org_id, 0.0):
                return list(InventoryService._recipients_cache[org_id])

            try:
                from app.infrastructure.database.models import User
                query = self.repo.db.query(User).filter(
                    User.role == "admin",
                    User.is_active.is_(True),
                    User.email.isnot(None),
                )
                if org_id is not None:
                    query = query.filter(User.org_id == org_id)

                recipients = [u.email for u in query.all()]
                InventoryService._recipients_cache[org_id] = recipients
                InventoryService._recipients_cache_expiry[org_id] = now + 60.0  # cache for 60 seconds
                return list(recipients)
            except Exception as e:
                logger.error("Failed to query user recipient emails: %s", e)
                # Return cached value even if stale as fallback
                return list(InventoryService._recipients_cache.get(org_id, []))


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
        transacted_unit: Optional[str] = None,
        transacted_qty: Optional[int] = None,
        multiplier: Optional[int] = 1,
    ) -> Dict[str, Any]:
        try:
            # 1. Acquire transaction-level advisory lock on (location_id, item_id) to eliminate first-write races
            self.repo.acquire_advisory_lock(location_id, item_id)

            # 2. Reject backdated entries if later activity already exists for this item/location
            if self.repo.has_later_transactions(location_id, item_id, transaction_date) is True:
                raise ValidationError(
                    f"Backdated inventory transactions are not permitted when subsequent history exists after {transaction_date}. "
                    "Please record the stock movement under the current date with appropriate adjustment notes."
                )

            previous = self.repo.get_previous_transaction(
                location_id, item_id, transaction_date, lock=True
            )

            if previous:
                opening_stock = previous.closing_stock
            else:
                opening_stock = 0

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
                transacted_unit=transacted_unit,
                transacted_qty=transacted_qty,
                multiplier=multiplier,
            )

            # ── Stock alert detection ───────────────────────────────────
            item = self.repo.get_item_by_id(item_id)
            if item and closing_stock <= item.min_stock:
                alert_status = "CRITICAL" if closing_stock <= 0 else "WARNING"
                logger.warning(
                    "Stock alert [%s]: %s at location %d — stock=%d, min=%d",
                    alert_status, item.name, location_id, closing_stock, item.min_stock,
                )

                # Queue alert for real-time WebSocket broadcast safely (org-scoped)
                from app.api.routes.websocket import queue_websocket_alert
                queue_websocket_alert(
                    {
                        "type": "low_stock_alert",
                        "status": alert_status,
                        "item_name": item.name,
                        "item_id": item_id,
                        "location_id": location_id,
                        "current_stock": closing_stock,
                        "min_stock": item.min_stock,
                    },
                    org_id=item.org_id,
                )


                # ── Email alert to admins & managers ───────────────────
                # Resolve location name and recipient emails, then
                # dispatch in a background thread so SMTP latency never
                # blocks the HTTP transaction response.
                try:
                    from threading import Thread
                    from app.application.notification_service import NotificationService

                    # Fetch email addresses using cached helper scoped to the item's organization
                    recipient_emails = self._get_recipient_emails(org_id=item.org_id)


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

            if not items_data:
                raise ValidationError("items_data cannot be empty")

            for item_data in items_data:
                result = self.add_transaction(
                    location_id=location_id,
                    item_id=item_data["item_id"],
                    transaction_date=transaction_date,
                    received=item_data.get("received", 0),
                    issued=item_data.get("issued", 0),
                    notes=item_data.get("notes"),
                    entered_by=entered_by,
                    flush_only=True,
                    batch_number=item_data.get("batch_number"),
                    expiry_date=item_data.get("expiry_date"),
                )

                if not result.get("success"):
                    raise ValidationError(result.get("error", "Transaction failed"))
                results.append(result["data"])

            # Atomically commit once all rows succeed
            self.repo.commit()

            return {
                "success": True,
                "message": f"Successfully processed {len(results)} transactions atomically",
                "data": {"successful": results, "failed": []},
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

    def get_location_items(self, location_id: int, org_id: Optional[int] = None) -> list:
        """
        Return stock status for every item at the given location scoped to org_id.

        Uses a single batch query (get_latest_stocks_for_location) instead of
        N+1 individual queries — critical for performance over remote DB connections.
        Includes UOM packaging tiers and human-readable decomposed stock breakdown.
        """
        from app.application.uom_service import decompose_stock

        items = self.repo.get_all_items(org_id=org_id)

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

            raw_packagings = getattr(item, "packagings", None)
            packagings = raw_packagings if isinstance(raw_packagings, (list, tuple, set)) else []
            decomp = decompose_stock(latest_stock, getattr(item, "unit", "units"), packagings)

            serialized_packagings = []
            for p in packagings:
                try:
                    p_mult = _safe_int(getattr(p, "multiplier", 1), 1)
                    p_mrp = getattr(p, "mrp", None)
                    if p_mrp is None:
                        item_mrp = _safe_float(getattr(item, "mrp", 0.0), 0.0)
                        p_mrp = round(item_mrp * p_mult, 2)
                    else:
                        p_mrp = _safe_float(p_mrp, 0.0)
                    serialized_packagings.append({
                        "id": getattr(p, "id", None),
                        "unit_name": str(getattr(p, "unit_name", "")),
                        "multiplier": p_mult,
                        "barcode": getattr(p, "barcode", None),
                        "mrp": p_mrp,
                        "purchase_rate": getattr(p, "purchase_rate", None),
                        "is_default_dispense": getattr(p, "is_default_dispense", False) is True,
                        "is_default_purchase": getattr(p, "is_default_purchase", False) is True,
                    })
                except Exception:
                    pass

            result.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "unit": item.unit,
                    "base_unit": item.unit,
                    "min_stock": item.min_stock,
                    "current_stock": latest_stock,
                    "stock_breakdown": decomp["display_string"],
                    "decomposed": decomp["breakdown"],
                    "status": status,
                    "packagings": serialized_packagings,
                }
            )

        return result

    def dispense_by_barcode(
        self,
        barcode_or_id: str,
        location_id: int,
        quantity: int = 1,
        unit: Optional[str] = None,
        entered_by: str = "staff",
        org_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        High-speed barcode dispense for retail pharmacy counters.
        Resolves item & packaging tier (e.g. tablet, strip, box), converts to base units,
        picks earliest-expiring active batches (FEFO order), atomically reduces stock in
        integer base units, records transaction with UOM context, and flushes cache.
        """
        if quantity <= 0:
            raise ValidationError("Dispense quantity must be greater than 0")

        from app.application.uom_service import resolve_item_packaging, decompose_stock

        # 1. Resolve Item and Packaging
        item = None
        matched_pkg = None
        barcode_clean = str(barcode_or_id).strip()

        # Try looking up via ItemPackaging barcode first
        if barcode_clean:
            pkg_obj = self.repo.get_packaging_by_barcode(barcode_clean, org_id=org_id)
            if pkg_obj:
                matched_pkg = pkg_obj
                item = pkg_obj.item

        # If not found by packaging barcode, lookup Item by barcode
        if not item and barcode_clean:
            item = self.repo.get_item_by_barcode(barcode_clean, org_id=org_id)

        # Fallback to numeric item ID
        if not item and barcode_clean.isdigit():
            item = self.repo.get_item_by_id(int(barcode_clean), org_id=org_id)

        if not item:
            raise ValidationError(f"Medicine not found for barcode/ID: '{barcode_or_id}'")

        # Resolve packaging tier, multiplier, and package MRP
        pkg_resolution = resolve_item_packaging(item, unit_name_or_barcode=unit or (matched_pkg.unit_name if matched_pkg else barcode_clean))
        multiplier = max(1, int(pkg_resolution.get("multiplier", 1)))
        packaging_unit = pkg_resolution.get("unit_name", item.unit)
        package_mrp = float(pkg_resolution.get("mrp", item.mrp or 0.0))
        package_purchase_rate = float(pkg_resolution.get("purchase_rate", item.purchase_rate or 0.0))

        # Total atomic base units to deduct
        base_qty_to_dispense = quantity * multiplier

        from app.infrastructure.cache.redis_lock import redis_distributed_lock

        with redis_distributed_lock(f"stock:{location_id}:{item.id}", org_id=org_id):
            # 2. Check current stock level at this pharmacy location in base units
            current_stock = self.get_latest_stock(location_id, item.id) or 0
            if current_stock < base_qty_to_dispense:
                raise InsufficientStockError(
                    f"Insufficient stock for {item.name}: only {current_stock} {item.unit} available at this counter "
                    f"(requested {quantity} {packaging_unit} = {base_qty_to_dispense} {item.unit})"
                )

            # 3. Find active batches with positive available stock (FEFO Order)
            available_batches = self.repo.get_available_batches_fefo(location_id, item.id)

            remaining_to_dispense = base_qty_to_dispense
            allocated_batches = []
            last_tx_result = None

            if available_batches:
                for b in available_batches:
                    if remaining_to_dispense <= 0:
                        break
                    deduct = min(remaining_to_dispense, b["available_qty"])
                    tx_res = self.add_transaction(
                        location_id=location_id,
                        item_id=item.id,
                        transaction_date=date.today(),
                        received=0,
                        issued=deduct,
                        notes=f"FEFO Barcode Dispense: {quantity} {packaging_unit} [Batch: {b['batch_number']}, Code: {item.barcode or barcode_or_id}]",
                        entered_by=entered_by,
                        batch_number=b["batch_number"],
                        expiry_date=b["expiry_date"],
                        transacted_unit=packaging_unit,
                        transacted_qty=quantity,
                        multiplier=multiplier,
                    )
                    allocated_batches.append({
                        "batch_number": b["batch_number"],
                        "expiry_date": str(b["expiry_date"]) if b["expiry_date"] else None,
                        "quantity": deduct,
                        "quantity_base": deduct,
                        "transaction_id": tx_res["data"]["id"],
                    })
                    remaining_to_dispense -= deduct
                    last_tx_result = tx_res

            # If any remaining quantity (e.g. unbatched opening stock), issue the remainder
            if remaining_to_dispense > 0:
                fb_batch = "UNBATCHED"
                fb_expiry = None
                tx_res = self.add_transaction(
                    location_id=location_id,
                    item_id=item.id,
                    transaction_date=date.today(),
                    received=0,
                    issued=remaining_to_dispense,
                    notes=f"FEFO Barcode Dispense: {quantity} {packaging_unit} [Unbatched Stock, Code: {item.barcode or barcode_or_id}]",
                    entered_by=entered_by,
                    batch_number=fb_batch,
                    expiry_date=fb_expiry,
                    transacted_unit=packaging_unit,
                    transacted_qty=quantity,
                    multiplier=multiplier,
                )
                allocated_batches.append({
                    "batch_number": fb_batch,
                    "expiry_date": None,
                    "quantity": remaining_to_dispense,
                    "quantity_base": remaining_to_dispense,
                    "transaction_id": tx_res["data"]["id"],
                })
                last_tx_result = tx_res

            # 5. Targeted cache invalidation for real-time reactivity
            try:
                from app.application.cache_service import cache_invalidate_pattern
                cache_invalidate_pattern(f"ref:location_items:{location_id}")
                cache_invalidate_pattern(f"analytics:alerts:*")
            except Exception as e:
                logger.debug("Cache invalidation skipped: %s", e)

            remaining_stock = last_tx_result["data"]["closing_stock"] if last_tx_result else current_stock - base_qty_to_dispense
            status = "CRITICAL" if remaining_stock <= 0 else ("WARNING" if remaining_stock <= item.min_stock else "HEALTHY")

            primary_batch = allocated_batches[0]["batch_number"] if allocated_batches else f"BT-SCAN-{int(time.time()) % 10000}"
            primary_expiry = allocated_batches[0]["expiry_date"] if allocated_batches else str(date.today())

            packagings = getattr(item, "packagings", []) or []
            decomp = decompose_stock(remaining_stock, item.unit, packagings)

            return {
                "success": True,
                "message": f"Dispensed {quantity} {packaging_unit} ({base_qty_to_dispense} {item.unit}) of {item.name}",
                "data": {
                    "item_id": item.id,
                    "item_name": item.name,
                    "category": item.category,
                    "barcode": item.barcode,
                    "base_unit": item.unit,
                    "packaging_unit": packaging_unit,
                    "multiplier": multiplier,
                    "dispensed_quantity": quantity,
                    "base_quantity_dispensed": base_qty_to_dispense,
                    "mrp": package_mrp,
                    "purchase_rate": package_purchase_rate,
                    "batch_number": primary_batch,
                    "expiry_date": primary_expiry,
                    "allocated_batches": allocated_batches,
                    "remaining_stock": remaining_stock,
                    "stock_breakdown": decomp["display_string"],
                    "status": status,
                    "transaction_id": last_tx_result["data"]["id"] if last_tx_result else None,
                },
            }



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

