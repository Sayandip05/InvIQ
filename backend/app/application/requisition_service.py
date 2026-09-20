"""
Requisition service — business logic layer.

Receives RequisitionRepository and InventoryRepository via the constructor
(injected by FastAPI DI). Contains only business rules; DB queries are
delegated to the repositories.
"""

import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional, List

from app.infrastructure.database.requisition_repo import RequisitionRepository
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    InvalidStateError,
    InsufficientStockError,
    DatabaseError,
)

logger = logging.getLogger("smart_inventory.service.requisition")


class RequisitionService:
    def __init__(self, repo: RequisitionRepository, inv_repo: InventoryRepository):
        self.repo = repo
        self.inv_repo = inv_repo

    def _generate_requisition_number(self) -> str:
        if hasattr(self.repo, "get_next_requisition_number"):
            return self.repo.get_next_requisition_number()
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"REQ-{today}-"
        count = self.repo.count_by_prefix(prefix) if hasattr(self.repo, "count_by_prefix") else 0
        return f"{prefix}{count + 1:03d}"

    @staticmethod
    def _format_requisition(req) -> dict:
        result = {
            "id": req.id,
            "requisition_number": req.requisition_number,
            "location_id": req.location_id,
            "location_name": req.location.name if req.location else None,
            "requested_by": req.requested_by,
            "department": req.department,
            "urgency": req.urgency,
            "status": req.status,
            "approved_by": req.approved_by,
            "rejection_reason": req.rejection_reason,
            "notes": req.notes,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            "items": [],
        }

        if req.items:
            for ri in req.items:
                base_unit = ri.item.unit if ri.item else "units"
                pkg_unit = ri.packaging_unit or base_unit
                mult = ri.multiplier or 1
                result["items"].append(
                    {
                        "id": ri.id,
                        "item_id": ri.item_id,
                        "item_name": ri.item.name if ri.item else None,
                        "item_unit": base_unit,
                        "base_unit": base_unit,
                        "packaging_unit": pkg_unit,
                        "multiplier": mult,
                        "quantity_requested": ri.quantity_requested,
                        "base_quantity_requested": ri.base_quantity_requested or (ri.quantity_requested * mult),
                        "quantity_approved": ri.quantity_approved,
                        "base_quantity_approved": ri.base_quantity_approved,
                        "notes": ri.notes,
                    }
                )

        return result

    def create_requisition(
        self,
        location_id: int,
        requested_by: str,
        department: str,
        urgency: str,
        items: List[dict],
        notes: Optional[str] = None,
        org_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        from app.core.exceptions import AuthorizationError, DuplicateError
        from app.application.uom_service import resolve_item_packaging

        try:
            location = self.repo.get_location(location_id)
            if not location:
                raise NotFoundError("Location", location_id)

            # ── Tenant ownership check on location ──────────────────────────
            if org_id is not None and location.org_id != org_id:
                raise AuthorizationError("Location does not belong to your organization")

            if urgency not in ("LOW", "NORMAL", "HIGH", "EMERGENCY"):
                raise ValidationError(
                    f"Invalid urgency level: {urgency}. Must be LOW, NORMAL, HIGH, or EMERGENCY"
                )

            validated_items = []
            for item_data in items:
                item = self.repo.get_item(item_data["item_id"])
                if not item:
                    raise NotFoundError("Item", item_data["item_id"])

                # ── Tenant ownership check on item ──────────────────────────
                if org_id is not None and item.org_id != org_id:
                    raise AuthorizationError(
                        f"Item '{item.name}' does not belong to your organization"
                    )

                qty = int(item_data.get("quantity", 0))
                if qty <= 0:
                    raise ValidationError(
                        f"Quantity must be positive for item {item.name}"
                    )

                # Resolve packaging unit & multiplier
                requested_unit = item_data.get("packaging_unit") or item_data.get("unit")
                pkg_res = resolve_item_packaging(item, unit_name_or_barcode=requested_unit)
                mult = max(1, int(pkg_res.get("multiplier", 1)))
                pkg_name = pkg_res.get("unit_name", item.unit)
                base_qty = qty * mult

                validated_items.append({
                    "item_id": item.id,
                    "quantity": qty,
                    "packaging_unit": pkg_name,
                    "multiplier": mult,
                    "base_quantity": base_qty,
                    "notes": item_data.get("notes"),
                })

            # Collision-resilient creation loop under simultaneous concurrent requests
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    req_number = self._generate_requisition_number()
                    requisition = self.repo.create(
                        requisition_number=req_number,
                        location_id=location_id,
                        requested_by=requested_by,
                        department=department,
                        urgency=urgency,
                        status="PENDING",
                        notes=notes,
                    )

                    for vi in validated_items:
                        self.repo.add_item(
                            requisition_id=requisition.id,
                            item_id=vi["item_id"],
                            quantity_requested=vi["quantity"],
                            packaging_unit=vi["packaging_unit"],
                            multiplier=vi["multiplier"],
                            base_quantity_requested=vi["base_quantity"],
                            notes=vi["notes"],
                        )

                    self.repo.commit()
                    self.repo.refresh(requisition)

                    logger.info("Requisition %s created by %s", req_number, requested_by)
                    return {
                        "success": True,
                        "message": f"Requisition {req_number} created successfully",
                        "data": self._format_requisition(requisition),
                    }
                except DuplicateError:
                    self.repo.rollback()
                    if attempt == max_attempts - 1:
                        raise DatabaseError("Failed to generate unique requisition number after multiple attempts")
                    logger.warning(
                        "Requisition number collision for %s (attempt %d/%d), retrying...",
                        req_number, attempt + 1, max_attempts,
                    )

        except (NotFoundError, ValidationError, AuthorizationError, DatabaseError):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in create_requisition: %s", str(e))
            raise DatabaseError(f"Failed to create requisition: {str(e)}")


    def list_requisitions(
        self,
        status: Optional[str] = None,
        location_id: Optional[int] = None,
        requested_by: Optional[str] = None,
        org_id: Optional[int] = None,
    ) -> List[dict]:
        requisitions = self.repo.list_all(status, location_id, requested_by, org_id=org_id)
        return [self._format_requisition(r) for r in requisitions]

    def get_requisition(self, requisition_id: int, org_id: Optional[int] = None) -> Optional[dict]:
        requisition = self.repo.get_with_full_details(requisition_id, org_id=org_id)
        if not requisition:
            return None
        return self._format_requisition(requisition)

    def approve_requisition(
        self,
        requisition_id: int,
        approved_by: str,
        item_adjustments: Optional[List[dict]] = None,
        org_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        from app.core.exceptions import AuthorizationError
        try:
            requisition = self.repo.get_by_id(requisition_id, load_items=True)

            if not requisition:
                raise NotFoundError("Requisition", requisition_id)

            # ── Tenant ownership check ──────────────────────────────────────
            if org_id is not None:
                location = self.repo.get_location(requisition.location_id)
                if not location or location.org_id != org_id:
                    raise AuthorizationError("Requisition does not belong to your organization")

            if requisition.status != "PENDING":
                raise InvalidStateError(
                    f"Cannot approve: requisition is already {requisition.status}"
                )

            adjustment_map = {}
            if item_adjustments:
                for adj in item_adjustments:
                    adjustment_map[adj["item_id"]] = adj["quantity_approved"]

            stock_errors = []
            for req_item in requisition.items:
                approved_qty = adjustment_map.get(
                    req_item.item_id, req_item.quantity_requested
                )
                req_item.quantity_approved = approved_qty
                
                raw_mult = getattr(req_item, "multiplier", 1)
                try:
                    mult_val = int(raw_mult) if raw_mult is not None else 1
                except (TypeError, ValueError):
                    mult_val = 1
                multiplier = max(1, mult_val)
                base_approved = approved_qty * multiplier
                req_item.base_quantity_approved = base_approved

                latest = self.inv_repo.get_latest_transaction(
                    requisition.location_id, req_item.item_id
                )
                current_stock = latest.closing_stock if latest else 0

                if base_approved > current_stock:
                    item = self.repo.get_item(req_item.item_id)
                    item_label = item.name if item else f"item_id={req_item.item_id}"
                    pkg_label = req_item.packaging_unit or "units"
                    stock_errors.append(
                        f"{item_label}: requested {approved_qty} {pkg_label} ({base_approved} base units), available {current_stock}"
                    )

            if stock_errors:
                raise InsufficientStockError(
                    "Insufficient stock: " + "; ".join(stock_errors)
                )

            from app.application.inventory_service import InventoryService

            inv_service = InventoryService(self.inv_repo)
            today = date.today()

            # ── Atomic batch: flush each deduction, commit once at the end ──
            for req_item in requisition.items:
                if req_item.quantity_approved and req_item.quantity_approved > 0:
                    raw_mult = getattr(req_item, "multiplier", 1)
                    try:
                        mult_val = int(raw_mult) if raw_mult is not None else 1
                    except (TypeError, ValueError):
                        mult_val = 1
                    multiplier = max(1, mult_val)
                    base_deduct = req_item.quantity_approved * multiplier
                    result = inv_service.add_transaction(
                        location_id=requisition.location_id,
                        item_id=req_item.item_id,
                        transaction_date=today,
                        received=0,
                        issued=base_deduct,
                        notes=f"Stock OUT: {requisition.requisition_number} ({requisition.department}) - {req_item.quantity_approved} {req_item.packaging_unit or 'units'}",
                        entered_by=f"system/approved-by-{approved_by}",
                        transacted_unit=getattr(req_item, "packaging_unit", None) or "units",
                        transacted_qty=req_item.quantity_approved,
                        multiplier=multiplier,
                        flush_only=True,  # Don't commit individual items
                    )
                    if not result["success"]:
                        raise DatabaseError(
                            f"Stock deduction failed: {result.get('error')}"
                        )

            requisition.status = "APPROVED"
            requisition.approved_by = approved_by
            requisition.approved_at = datetime.now(timezone.utc)
            self.repo.commit()  # Single atomic commit for all items

            logger.info(
                "Requisition %s approved by %s",
                requisition.requisition_number,
                approved_by,
            )
            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} approved. Stock deducted.",
                "data": self._format_requisition(requisition),
            }

        except (
            NotFoundError,
            InvalidStateError,
            InsufficientStockError,
            AuthorizationError,
            DatabaseError,
        ):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in approve_requisition: %s", str(e))
            raise DatabaseError(f"Failed to approve requisition: {str(e)}")

    def reject_requisition(
        self, requisition_id: int, rejected_by: str, reason: str, org_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from app.core.exceptions import AuthorizationError
        try:
            requisition = self.repo.get_by_id(requisition_id)

            if not requisition:
                raise NotFoundError("Requisition", requisition_id)

            # ── Tenant ownership check ──────────────────────────────────────
            if org_id is not None:
                location = self.repo.get_location(requisition.location_id)
                if not location or location.org_id != org_id:
                    raise AuthorizationError("Requisition does not belong to your organization")

            if requisition.status != "PENDING":
                raise InvalidStateError(
                    f"Cannot reject: requisition is already {requisition.status}"
                )

            requisition.status = "REJECTED"
            # approved_by intentionally left unchanged (None) — this was never approved.
            # rejection metadata is captured in rejection_reason and rejected_at.
            requisition.rejection_reason = reason
            requisition.rejected_at = datetime.now(timezone.utc)
            self.repo.commit()

            logger.info(
                "Requisition %s rejected by %s",
                requisition.requisition_number,
                rejected_by,
            )
            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} rejected.",
            }

        except (NotFoundError, InvalidStateError, AuthorizationError, DatabaseError):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in reject_requisition: %s", str(e))
            raise DatabaseError(f"Failed to reject requisition: {str(e)}")

    def cancel_requisition(
        self, requisition_id: int, cancelled_by: str, org_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from app.core.exceptions import AuthorizationError
        try:
            requisition = self.repo.get_by_id(requisition_id)

            if not requisition:
                raise NotFoundError("Requisition", requisition_id)

            # ── Tenant ownership check ──────────────────────────────────────
            if org_id is not None:
                location = self.repo.get_location(requisition.location_id)
                if not location or location.org_id != org_id:
                    raise AuthorizationError("Requisition does not belong to your organization")


            if requisition.status != "PENDING":
                raise InvalidStateError("Only PENDING requisitions can be cancelled")

            requisition.status = "CANCELLED"
            self.repo.commit()

            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} cancelled.",
            }

        except (NotFoundError, InvalidStateError, AuthorizationError, DatabaseError):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in cancel_requisition: %s", str(e))
            raise DatabaseError(f"Failed to cancel requisition: {str(e)}")

    def fulfill_requisition(
        self, requisition_id: int, fulfilled_by: str, org_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from app.core.exceptions import AuthorizationError
        try:
            requisition = self.repo.get_by_id(requisition_id, load_items=True)

            if not requisition:
                raise NotFoundError("Requisition", requisition_id)

            # ── Tenant ownership check ──────────────────────────────────────
            if org_id is not None:
                location = self.repo.get_location(requisition.location_id)
                if not location or location.org_id != org_id:
                    raise AuthorizationError("Requisition does not belong to your organization")

            if requisition.status not in ("APPROVED", "PENDING"):
                raise InvalidStateError(f"Cannot fulfill: requisition is already {requisition.status}")

            # If not yet approved, approve and deduct stock first
            if requisition.status == "PENDING":
              # Bug 3 fix: use a very large limit so stats aren't silently capped at 100 rows.
              rows = self.get_requisition_rows(date_from=date_from, date_to=date_to, org_id=org_id, limit=100_000)
              requisition = self.repo.get_by_id(requisition_id, load_items=True)

            requisition.status = "FULFILLED"
            self.repo.commit()

            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} marked as fulfilled.",
                "data": self._format_requisition(requisition),
            }

        except (NotFoundError, InvalidStateError, InsufficientStockError, AuthorizationError, DatabaseError):
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            logger.error("Unexpected error in fulfill_requisition: %s", str(e))
            raise DatabaseError(f"Failed to fulfill requisition: {str(e)}")

    def get_stats(self, org_id: Optional[int] = None) -> dict:

        return {
            "total": self.repo.count_total(org_id=org_id),
            "pending": self.repo.count_by_status("PENDING", org_id=org_id),
            "approved_today": self.repo.count_approved_today(org_id=org_id),
            "rejected": self.repo.count_by_status("REJECTED", org_id=org_id),
            "emergency_pending": self.repo.count_emergency_pending(org_id=org_id),
        }
