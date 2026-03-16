"""
Requisition service — business logic layer.

Receives RequisitionRepository and InventoryRepository via the constructor
(injected by FastAPI DI). Contains only business rules; DB queries are
delegated to the repositories.
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List

from app.repositories.requisition_repo import RequisitionRepository
from app.repositories.inventory_repo import InventoryRepository

logger = logging.getLogger("smart_inventory.service.requisition")


class RequisitionService:

    def __init__(self, repo: RequisitionRepository, inv_repo: InventoryRepository):
        self.repo = repo
        self.inv_repo = inv_repo

    # ── Helpers ──

    def _generate_requisition_number(self) -> str:
        """Generate auto-incrementing requisition number: REQ-YYYYMMDD-NNN."""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"REQ-{today}-"
        count = self.repo.count_by_prefix(prefix)
        return f"{prefix}{count + 1:03d}"

    @staticmethod
    def _format_requisition(req) -> dict:
        """Format a requisition ORM object into a JSON-serializable dict."""
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
                result["items"].append(
                    {
                        "id": ri.id,
                        "item_id": ri.item_id,
                        "item_name": ri.item.name if ri.item else None,
                        "item_unit": ri.item.unit if ri.item else None,
                        "quantity_requested": ri.quantity_requested,
                        "quantity_approved": ri.quantity_approved,
                        "notes": ri.notes,
                    }
                )

        return result

    # ── Core operations ──

    def create_requisition(
        self,
        location_id: int,
        requested_by: str,
        department: str,
        urgency: str,
        items: List[dict],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new stock-out requisition with line items."""
        try:
            # Validate location
            location = self.repo.get_location(location_id)
            if not location:
                return {"success": False, "error": "Location not found"}

            if urgency not in ("LOW", "NORMAL", "HIGH", "EMERGENCY"):
                return {"success": False, "error": "Invalid urgency level"}

            # Validate items exist
            for item_data in items:
                item = self.repo.get_item(item_data["item_id"])
                if not item:
                    return {
                        "success": False,
                        "error": f"Item ID {item_data['item_id']} not found",
                    }
                if item_data.get("quantity", 0) <= 0:
                    return {
                        "success": False,
                        "error": f"Quantity must be positive for item {item.name}",
                    }

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

            for item_data in items:
                self.repo.add_item(
                    requisition_id=requisition.id,
                    item_id=item_data["item_id"],
                    quantity_requested=item_data["quantity"],
                    notes=item_data.get("notes"),
                )

            self.repo.commit()
            self.repo.refresh(requisition)

            logger.info("Requisition %s created by %s", req_number, requested_by)
            return {
                "success": True,
                "message": f"Requisition {req_number} created successfully",
                "data": self._format_requisition(requisition),
            }

        except Exception as e:
            self.repo.rollback()
            return {"success": False, "error": str(e)}

    def list_requisitions(
        self,
        status: Optional[str] = None,
        location_id: Optional[int] = None,
        requested_by: Optional[str] = None,
    ) -> List[dict]:
        """List requisitions with optional filters."""
        requisitions = self.repo.list_all(status, location_id, requested_by)
        return [self._format_requisition(r) for r in requisitions]

    def get_requisition(self, requisition_id: int) -> Optional[dict]:
        """Get a single requisition with full details."""
        requisition = self.repo.get_with_full_details(requisition_id)
        if not requisition:
            return None
        return self._format_requisition(requisition)

    def approve_requisition(
        self,
        requisition_id: int,
        approved_by: str,
        item_adjustments: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Approve a requisition and auto-deduct stock."""
        try:
            requisition = self.repo.get_by_id(requisition_id, load_items=True)

            if not requisition:
                return {"success": False, "error": "Requisition not found"}

            if requisition.status != "PENDING":
                return {
                    "success": False,
                    "error": f"Cannot approve: requisition is already {requisition.status}",
                }

            # Build adjustment map
            adjustment_map = {}
            if item_adjustments:
                for adj in item_adjustments:
                    adjustment_map[adj["item_id"]] = adj["quantity_approved"]

            # Check stock availability and set approved quantities
            stock_errors = []
            for req_item in requisition.items:
                approved_qty = adjustment_map.get(
                    req_item.item_id, req_item.quantity_requested
                )
                req_item.quantity_approved = approved_qty

                latest = self.inv_repo.get_latest_transaction(
                    requisition.location_id, req_item.item_id
                )
                current_stock = latest.closing_stock if latest else 0

                if approved_qty > current_stock:
                    item = self.repo.get_item(req_item.item_id)
                    stock_errors.append(
                        f"{item.name}: requested {approved_qty}, available {current_stock}"
                    )

            if stock_errors:
                return {
                    "success": False,
                    "error": "Insufficient stock: " + "; ".join(stock_errors),
                }

            # Deduct stock via inventory repo
            from app.services.inventory_service import InventoryService

            inv_service = InventoryService(self.inv_repo)
            today = date.today()

            for req_item in requisition.items:
                if req_item.quantity_approved and req_item.quantity_approved > 0:
                    result = inv_service.add_transaction(
                        location_id=requisition.location_id,
                        item_id=req_item.item_id,
                        transaction_date=today,
                        received=0,
                        issued=req_item.quantity_approved,
                        notes=f"Stock OUT: {requisition.requisition_number} ({requisition.department})",
                        entered_by=f"system/approved-by-{approved_by}",
                    )
                    if not result["success"]:
                        self.repo.rollback()
                        return {
                            "success": False,
                            "error": f"Stock deduction failed: {result['error']}",
                        }

            requisition.status = "APPROVED"
            requisition.approved_by = approved_by
            self.repo.commit()

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

        except Exception as e:
            self.repo.rollback()
            return {"success": False, "error": str(e)}

    def reject_requisition(
        self, requisition_id: int, rejected_by: str, reason: str
    ) -> Dict[str, Any]:
        """Reject a requisition with a reason."""
        try:
            requisition = self.repo.get_by_id(requisition_id)

            if not requisition:
                return {"success": False, "error": "Requisition not found"}

            if requisition.status != "PENDING":
                return {
                    "success": False,
                    "error": f"Cannot reject: requisition is already {requisition.status}",
                }

            requisition.status = "REJECTED"
            requisition.approved_by = rejected_by
            requisition.rejection_reason = reason
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

        except Exception as e:
            self.repo.rollback()
            return {"success": False, "error": str(e)}

    def cancel_requisition(
        self, requisition_id: int, cancelled_by: str
    ) -> Dict[str, Any]:
        """Cancel a pending requisition (only by the requester)."""
        try:
            requisition = self.repo.get_by_id(requisition_id)

            if not requisition:
                return {"success": False, "error": "Requisition not found"}

            if requisition.status != "PENDING":
                return {
                    "success": False,
                    "error": "Only PENDING requisitions can be cancelled",
                }

            requisition.status = "CANCELLED"
            self.repo.commit()

            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} cancelled.",
            }

        except Exception as e:
            self.repo.rollback()
            return {"success": False, "error": str(e)}

    def get_stats(self) -> dict:
        """Get summary statistics for the requisition dashboard."""
        return {
            "total": self.repo.count_total(),
            "pending": self.repo.count_by_status("PENDING"),
            "approved_today": self.repo.count_approved_today(),
            "rejected": self.repo.count_by_status("REJECTED"),
            "emergency_pending": self.repo.count_emergency_pending(),
        }
