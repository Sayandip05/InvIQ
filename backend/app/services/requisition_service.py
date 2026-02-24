from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from app.database.models import (
    Requisition, RequisitionItem, Item, Location, InventoryTransaction
)
from app.services.inventory_service import InventoryService


class RequisitionService:

    @staticmethod
    def _generate_requisition_number(db: Session) -> str:
        """Generate auto-incrementing requisition number: REQ-YYYYMMDD-NNN"""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"REQ-{today}-"

        # Count today's requisitions
        count = (
            db.query(Requisition)
            .filter(Requisition.requisition_number.like(f"{prefix}%"))
            .count()
        )
        return f"{prefix}{count + 1:03d}"

    @staticmethod
    def create_requisition(
        db: Session,
        location_id: int,
        requested_by: str,
        department: str,
        urgency: str,
        items: List[dict],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new stock-out requisition with line items.

        items format: [{"item_id": 1, "quantity": 50, "notes": "..."}, ...]
        """
        try:
            # Validate location
            location = db.query(Location).filter(Location.id == location_id).first()
            if not location:
                return {"success": False, "error": "Location not found"}

            # Validate urgency
            if urgency not in ("LOW", "NORMAL", "HIGH", "EMERGENCY"):
                return {"success": False, "error": "Invalid urgency level"}

            # Validate items exist
            for item_data in items:
                item = db.query(Item).filter(Item.id == item_data["item_id"]).first()
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

            # Create requisition
            req_number = RequisitionService._generate_requisition_number(db)
            requisition = Requisition(
                requisition_number=req_number,
                location_id=location_id,
                requested_by=requested_by,
                department=department,
                urgency=urgency,
                status="PENDING",
                notes=notes,
            )
            db.add(requisition)
            db.flush()  # Get the ID before adding items

            # Add line items
            for item_data in items:
                req_item = RequisitionItem(
                    requisition_id=requisition.id,
                    item_id=item_data["item_id"],
                    quantity_requested=item_data["quantity"],
                    notes=item_data.get("notes"),
                )
                db.add(req_item)

            db.commit()
            db.refresh(requisition)

            return {
                "success": True,
                "message": f"Requisition {req_number} created successfully",
                "data": RequisitionService._format_requisition(requisition),
            }

        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_requisitions(
        db: Session,
        status: Optional[str] = None,
        location_id: Optional[int] = None,
        requested_by: Optional[str] = None,
    ) -> List[dict]:
        """List requisitions with optional filters."""
        query = db.query(Requisition).options(
            joinedload(Requisition.location),
            joinedload(Requisition.items).joinedload(RequisitionItem.item),
        )

        if status:
            query = query.filter(Requisition.status == status.upper())
        if location_id:
            query = query.filter(Requisition.location_id == location_id)
        if requested_by:
            query = query.filter(Requisition.requested_by == requested_by)

        requisitions = query.order_by(desc(Requisition.created_at)).all()
        return [RequisitionService._format_requisition(r) for r in requisitions]

    @staticmethod
    def get_requisition(db: Session, requisition_id: int) -> Optional[dict]:
        """Get a single requisition with full details."""
        requisition = (
            db.query(Requisition)
            .options(
                joinedload(Requisition.location),
                joinedload(Requisition.items).joinedload(RequisitionItem.item),
            )
            .filter(Requisition.id == requisition_id)
            .first()
        )
        if not requisition:
            return None
        return RequisitionService._format_requisition(requisition)

    @staticmethod
    def approve_requisition(
        db: Session,
        requisition_id: int,
        approved_by: str,
        item_adjustments: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """
        Approve a requisition and auto-deduct stock.

        item_adjustments: [{"item_id": 1, "quantity_approved": 40}, ...]
        If not provided, approved qty = requested qty for all items.
        """
        try:
            requisition = (
                db.query(Requisition)
                .options(joinedload(Requisition.items))
                .filter(Requisition.id == requisition_id)
                .first()
            )

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

                # Check current stock
                current_stock = InventoryService.get_latest_stock(
                    db, requisition.location_id, req_item.item_id
                )
                if current_stock is None:
                    current_stock = 0

                if approved_qty > current_stock:
                    item = db.query(Item).filter(Item.id == req_item.item_id).first()
                    stock_errors.append(
                        f"{item.name}: requested {approved_qty}, available {current_stock}"
                    )

            if stock_errors:
                return {
                    "success": False,
                    "error": "Insufficient stock: " + "; ".join(stock_errors),
                }

            # Deduct stock by creating inventory transactions (issued = approved qty)
            today = date.today()
            for req_item in requisition.items:
                if req_item.quantity_approved and req_item.quantity_approved > 0:
                    result = InventoryService.add_transaction(
                        db=db,
                        location_id=requisition.location_id,
                        item_id=req_item.item_id,
                        transaction_date=today,
                        received=0,
                        issued=req_item.quantity_approved,
                        notes=f"Stock OUT: {requisition.requisition_number} ({requisition.department})",
                        entered_by=f"system/approved-by-{approved_by}",
                    )
                    if not result["success"]:
                        db.rollback()
                        return {
                            "success": False,
                            "error": f"Stock deduction failed: {result['error']}",
                        }

            # Update requisition status
            requisition.status = "APPROVED"
            requisition.approved_by = approved_by
            db.commit()

            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} approved. Stock deducted.",
                "data": RequisitionService._format_requisition(requisition),
            }

        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def reject_requisition(
        db: Session,
        requisition_id: int,
        rejected_by: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Reject a requisition with a reason."""
        try:
            requisition = db.query(Requisition).filter(
                Requisition.id == requisition_id
            ).first()

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
            db.commit()

            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} rejected.",
            }

        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def cancel_requisition(
        db: Session, requisition_id: int, cancelled_by: str
    ) -> Dict[str, Any]:
        """Cancel a pending requisition (only by the requester)."""
        try:
            requisition = db.query(Requisition).filter(
                Requisition.id == requisition_id
            ).first()

            if not requisition:
                return {"success": False, "error": "Requisition not found"}

            if requisition.status != "PENDING":
                return {
                    "success": False,
                    "error": "Only PENDING requisitions can be cancelled",
                }

            requisition.status = "CANCELLED"
            db.commit()

            return {
                "success": True,
                "message": f"Requisition {requisition.requisition_number} cancelled.",
            }

        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_stats(db: Session) -> dict:
        """Get summary statistics for the requisition dashboard."""
        today = date.today()

        total = db.query(Requisition).count()
        pending = db.query(Requisition).filter(Requisition.status == "PENDING").count()
        approved_today = (
            db.query(Requisition)
            .filter(
                Requisition.status == "APPROVED",
                func.date(Requisition.updated_at) == today,
            )
            .count()
        )
        rejected = db.query(Requisition).filter(Requisition.status == "REJECTED").count()
        emergency_pending = (
            db.query(Requisition)
            .filter(Requisition.status == "PENDING", Requisition.urgency == "EMERGENCY")
            .count()
        )

        return {
            "total": total,
            "pending": pending,
            "approved_today": approved_today,
            "rejected": rejected,
            "emergency_pending": emergency_pending,
        }

    @staticmethod
    def _format_requisition(req: Requisition) -> dict:
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
