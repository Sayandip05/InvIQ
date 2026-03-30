"""
Vendor Service — Excel delivery parsing and bulk transaction creation.

Handles:
  - Excel file parsing via openpyxl
  - Item name matching (exact match, case-insensitive)
  - Bulk transaction creation via InventoryService
  - VendorUpload record tracking
"""

import logging
from datetime import date
from typing import Dict, Any, List, Optional
from io import BytesIO

from sqlalchemy.orm import Session

from app.infrastructure.database.models import Item, VendorUpload
from app.application.inventory_service import InventoryService
from app.infrastructure.database.inventory_repo import InventoryRepository

logger = logging.getLogger("smart_inventory.vendor")


class VendorService:
    """Parse vendor Excel uploads and create inventory transactions."""

    def __init__(self, db: Session):
        self.db = db
        self.inv_repo = InventoryRepository(db)
        self.inv_service = InventoryService(self.inv_repo)

    def parse_and_process_excel(
        self,
        file_content: bytes,
        filename: str,
        location_id: int,
        vendor_user_id: int,
        org_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Parse an Excel file and create inventory transactions for each row.

        Expected columns: item_name, quantity_received, delivery_date (optional), notes (optional)

        Returns summary with success/error counts.
        """
        try:
            import openpyxl
        except ImportError:
            return {
                "success": False,
                "error": "openpyxl is not installed. Run: pip install openpyxl",
            }

        try:
            wb = openpyxl.load_workbook(BytesIO(file_content), read_only=True)
            ws = wb.active

            if not ws:
                return {"success": False, "error": "Excel file has no active sheet"}

            # Read header row
            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 2:
                return {"success": False, "error": "Excel file must have a header row and at least one data row"}

            header = [str(h).strip().lower() if h else "" for h in rows[0]]

            # Find column indices
            col_map = {}
            for i, h in enumerate(header):
                if "item" in h and "name" in h:
                    col_map["item_name"] = i
                elif "quantity" in h or "received" in h or "qty" in h:
                    col_map["quantity"] = i
                elif "date" in h:
                    col_map["date"] = i
                elif "note" in h:
                    col_map["notes"] = i

            if "item_name" not in col_map or "quantity" not in col_map:
                return {
                    "success": False,
                    "error": "Excel must have 'item_name' and 'quantity_received' columns",
                }

            # Build item lookup (case-insensitive)
            items_query = self.db.query(Item)
            if org_id:
                items_query = items_query.filter(Item.org_id == org_id)
            all_items = items_query.all()
            item_lookup = {item.name.lower(): item for item in all_items}

            # Process rows
            success_count = 0
            error_list = []
            today = date.today()

            for row_idx, row in enumerate(rows[1:], start=2):
                try:
                    item_name = str(row[col_map["item_name"]]).strip() if row[col_map["item_name"]] else ""
                    quantity = row[col_map["quantity"]]
                    delivery_date = row[col_map.get("date", -1)] if col_map.get("date") is not None and col_map.get("date") < len(row) else None
                    notes = str(row[col_map.get("notes", -1)]).strip() if col_map.get("notes") is not None and col_map.get("notes") < len(row) and row[col_map.get("notes")] else ""

                    if not item_name:
                        error_list.append({"row": row_idx, "reason": "Empty item name"})
                        continue

                    # Try exact match (case-insensitive)
                    matched_item = item_lookup.get(item_name.lower())

                    if not matched_item:
                        error_list.append({"row": row_idx, "reason": f"Item not found: '{item_name}'"})
                        continue

                    try:
                        qty = int(quantity)
                    except (TypeError, ValueError):
                        error_list.append({"row": row_idx, "reason": f"Invalid quantity: '{quantity}'"})
                        continue

                    if qty <= 0:
                        error_list.append({"row": row_idx, "reason": f"Quantity must be positive: {qty}"})
                        continue

                    # Parse date
                    tx_date = today
                    if delivery_date:
                        if isinstance(delivery_date, date):
                            tx_date = delivery_date
                        else:
                            try:
                                from datetime import datetime
                                tx_date = datetime.strptime(str(delivery_date), "%Y-%m-%d").date()
                            except ValueError:
                                pass  # Use today

                    # Create transaction (flush only — commit at end)
                    result = self.inv_service.add_transaction(
                        location_id=location_id,
                        item_id=matched_item.id,
                        transaction_date=tx_date,
                        received=qty,
                        issued=0,
                        notes=f"Vendor delivery: {notes}" if notes else f"Vendor delivery from {filename}",
                        entered_by=f"vendor/upload/{vendor_user_id}",
                        flush_only=True,
                    )

                    if result.get("success"):
                        success_count += 1
                    else:
                        error_list.append({"row": row_idx, "reason": result.get("error", "Transaction failed")})

                except Exception as e:
                    error_list.append({"row": row_idx, "reason": str(e)})

            # Commit all successful transactions atomically
            self.db.commit()

            # Save VendorUpload record
            upload = VendorUpload(
                vendor_user_id=vendor_user_id,
                org_id=org_id,
                filename=filename,
                location_id=location_id,
                total_rows=len(rows) - 1,
                success_rows=success_count,
                error_rows=len(error_list),
                errors_detail=error_list if error_list else None,
                status="COMPLETED" if error_list == [] else "COMPLETED_WITH_ERRORS" if success_count > 0 else "FAILED",
            )
            self.db.add(upload)
            self.db.commit()
            self.db.refresh(upload)

            wb.close()

            return {
                "success": True,
                "data": {
                    "upload_id": upload.id,
                    "filename": filename,
                    "total_rows": len(rows) - 1,
                    "success": success_count,
                    "errors": len(error_list),
                    "error_details": error_list[:20],  # Cap at 20 errors in response
                    "status": upload.status,
                },
            }

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to process vendor upload: %s", str(e))
            return {"success": False, "error": f"Failed to process file: {str(e)}"}

    def get_uploads_for_vendor(self, vendor_user_id: int) -> List[dict]:
        """Get upload history for a specific vendor."""
        uploads = (
            self.db.query(VendorUpload)
            .filter(VendorUpload.vendor_user_id == vendor_user_id)
            .order_by(VendorUpload.uploaded_at.desc())
            .all()
        )
        return [
            {
                "id": u.id,
                "filename": u.filename,
                "location_id": u.location_id,
                "total_rows": u.total_rows,
                "success_rows": u.success_rows,
                "error_rows": u.error_rows,
                "errors_detail": u.errors_detail,
                "status": u.status,
                "uploaded_at": str(u.uploaded_at) if u.uploaded_at else None,
            }
            for u in uploads
        ]
