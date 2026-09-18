"""
Vendor Service — Excel delivery parsing, bulk transaction creation, and automated invoice generation.

Handles:
  - Excel file parsing via openpyxl
  - Item name matching (exact match, case-insensitive)
  - Bulk transaction creation via InventoryService
  - VendorUpload record tracking
  - Automated Vendor Delivery Invoice generation with ReportLab PDF rendering
  - Cloud PDF upload via AzureBlobStorageService with database binary fallback
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from io import BytesIO

from sqlalchemy.orm import Session

from app.infrastructure.database.models import Item, VendorUpload, User, Location, VendorInvoice
from app.application.inventory_service import InventoryService
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.invoice_repo import InvoiceRepository
from app.application.invoice_pdf_service import InvoicePdfService
from app.infrastructure.storage.azure_blob_storage import get_storage_service
from app.core.exceptions import ValidationError

logger = logging.getLogger("smart_inventory.vendor")


def _parse_date_safe(val: Any) -> Tuple[Optional[date], Optional[str]]:
    """
    Parse a date value safely from Excel/CSV cells.
    Returns (parsed_date, error_message).
    """
    if val is None or str(val).strip() == "":
        return None, None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val, None
    if isinstance(val, datetime):
        return val.date(), None
    if isinstance(val, (int, float)):
        # Excel serial date (Windows Excel epoch 1899-12-30)
        try:
            from openpyxl.utils.datetime import from_excel
            dt = from_excel(val)
            if isinstance(dt, datetime):
                return dt.date(), None
            elif isinstance(dt, date):
                return dt, None
        except Exception:
            pass
        try:
            dt = date(1899, 12, 30) + timedelta(days=int(val))
            return dt, None
        except Exception:
            return None, f"Invalid date number '{val}'"

    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(val_str, fmt).date(), None
        except ValueError:
            pass
    return None, f"Could not read date '{val_str}'. Please use YYYY-MM-DD"


class VendorService:
    """Parse vendor Excel uploads, create inventory transactions, and generate delivery invoices."""

    def __init__(self, db: Session):
        self.db = db
        self.inv_repo = InventoryRepository(db)
        self.inv_service = InventoryService(self.inv_repo)
        self.invoice_repo = InvoiceRepository(db)

    def parse_and_process_excel(
        self,
        file_content: bytes,
        filename: str,
        location_id: int,
        vendor_user_id: int,
        org_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Parse an Excel file, validate all rows in memory (All-or-Nothing dry run),
        auto-create missing catalog items, and atomically record inventory transactions.

        Standard columns:
          item_name, quantity, unit, batch_number, expiry_date,
          purchase_rate, mrp, category, storage_temp, delivery_date, invoice_no

        Guarantees:
          - Zero AI calls during ingestion (100% deterministic).
          - All-or-Nothing validation: 0 DB records written if ANY row is invalid.
          - Clear, user-friendly line number error reporting.
          - Atomic rollback on unexpected database exceptions.
        """
        try:
            import openpyxl
        except ImportError:
            return {
                "success": False,
                "error": "openpyxl is not installed on the server",
            }

        try:
            wb = openpyxl.load_workbook(BytesIO(file_content), read_only=True)
            ws = wb.active

            if not ws:
                return {"success": False, "error": "Excel file has no active sheet"}

            # Read all rows into memory
            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 2:
                return {"success": False, "error": "Excel file must have a header row and at least one medicine data row"}

            header = [str(h).strip().lower() if h else "" for h in rows[0]]

            # Map columns (exact standard match + backwards-compatible aliases)
            col_map = {}
            for i, h in enumerate(header):
                if not h:
                    continue
                # Item Name
                if "item" in h and "name" in h:
                    col_map["item_name"] = i
                elif h in ("item", "medicine", "medicine_name", "drug_name", "product_name"):
                    col_map.setdefault("item_name", i)
                # Quantity
                elif "quantity" in h or "received" in h or "qty" in h:
                    col_map["quantity"] = i
                # Purchase Rate / Cost Price
                elif "purchase" in h or "cost" in h or ("unit" in h and "price" in h) or "buy_price" in h:
                    col_map["purchase_rate"] = i
                elif h in ("rate", "price") and "mrp" not in h:
                    col_map.setdefault("purchase_rate", i)
                # MRP / Retail Price
                elif "mrp" in h or "retail" in h or "sale_price" in h or "sales_price" in h:
                    col_map["mrp"] = i
                # Unit
                elif "unit" in h or "packaging" in h or "uom" in h:
                    col_map["unit"] = i
                # Batch Number
                elif "batch" in h or "lot" in h:
                    col_map["batch_number"] = i
                # Expiry Date
                elif "expir" in h or "exp" in h:
                    col_map["expiry_date"] = i
                # Category
                elif "category" in h or "group" in h:
                    col_map["category"] = i
                # Storage Temp
                elif "temp" in h or "storage" in h or "cold" in h:
                    col_map["storage_temp"] = i
                # Delivery Date
                elif "delivery" in h and "date" in h:
                    col_map["delivery_date"] = i
                elif "date" in h and "exp" not in h:
                    col_map.setdefault("delivery_date", i)
                # Invoice No / Notes
                elif "invoice" in h or "bill" in h or "note" in h or "order" in h:
                    col_map["invoice_no"] = i

            if "item_name" not in col_map or "quantity" not in col_map:
                return {
                    "success": False,
                    "error": "The delivery file is missing required columns. It must include 'item_name' and 'quantity'.",
                }

            # ── Phase 1: In-Memory Validation (All-or-Nothing Dry Run) ────────
            today = date.today()
            validation_errors: List[Dict[str, Any]] = []
            validated_rows: List[Dict[str, Any]] = []

            for row_idx, row in enumerate(rows[1:], start=2):
                # Skip completely empty rows
                if not any(cell is not None and str(cell).strip() != "" for cell in row):
                    continue

                row_errors: List[str] = []
                row_data: Dict[str, Any] = {}

                # 1. item_name
                raw_name = row[col_map["item_name"]] if col_map["item_name"] < len(row) else None
                item_name = str(raw_name).strip() if raw_name is not None else ""
                if not item_name or item_name.lower() in ("none", "nan", "null"):
                    row_errors.append(f"Line {row_idx}: Medicine name cannot be empty.")
                else:
                    row_data["item_name"] = item_name

                # 2. quantity
                raw_qty = row[col_map["quantity"]] if col_map["quantity"] < len(row) else None
                if raw_qty is None or str(raw_qty).strip() in ("", "None", "nan"):
                    row_errors.append(f"Line {row_idx}: Quantity is required.")
                else:
                    try:
                        qty_val = int(float(str(raw_qty).strip()))
                        if qty_val <= 0:
                            row_errors.append(f"Line {row_idx}: Quantity must be greater than zero (got '{raw_qty}').")
                        else:
                            row_data["quantity"] = qty_val
                    except (ValueError, TypeError):
                        row_errors.append(f"Line {row_idx}: Quantity must be a valid whole number (got '{raw_qty}').")

                # 3. unit
                raw_unit = row[col_map["unit"]] if col_map.get("unit") is not None and col_map["unit"] < len(row) else None
                unit_str = str(raw_unit).strip() if raw_unit is not None and str(raw_unit).strip() not in ("", "None", "nan") else "Units"
                row_data["unit"] = unit_str

                # 4. batch_number
                raw_batch = row[col_map["batch_number"]] if col_map.get("batch_number") is not None and col_map["batch_number"] < len(row) else None
                batch_str = str(raw_batch).strip() if raw_batch is not None and str(raw_batch).strip() not in ("", "None", "nan") else ""
                if "batch_number" in col_map and not batch_str:
                    row_errors.append(f"Line {row_idx}: Batch number cannot be empty.")
                else:
                    row_data["batch_number"] = batch_str or "BATCH-DEFAULT"

                # 5. expiry_date
                raw_exp = row[col_map["expiry_date"]] if col_map.get("expiry_date") is not None and col_map["expiry_date"] < len(row) else None
                if "expiry_date" in col_map:
                    if raw_exp is None or str(raw_exp).strip() in ("", "None", "nan"):
                        row_errors.append(f"Line {row_idx}: Expiry date is required.")
                    else:
                        exp_date, exp_err = _parse_date_safe(raw_exp)
                        if exp_err or not exp_date:
                            row_errors.append(f"Line {row_idx}: Invalid expiry date '{raw_exp}'. Please use YYYY-MM-DD format.")
                        elif exp_date < today:
                            row_errors.append(f"Line {row_idx}: Expiry date '{exp_date.isoformat()}' has already passed. Please enter a valid future date.")
                        else:
                            row_data["expiry_date"] = exp_date
                else:
                    row_data["expiry_date"] = today + timedelta(days=730)

                # 6. purchase_rate
                raw_pr = row[col_map["purchase_rate"]] if col_map.get("purchase_rate") is not None and col_map["purchase_rate"] < len(row) else None
                purchase_rate = 150.0
                if raw_pr is not None and str(raw_pr).strip() not in ("", "None", "nan"):
                    try:
                        pr_val = float(str(raw_pr).strip())
                        if pr_val < 0:
                            row_errors.append(f"Line {row_idx}: Purchase rate cannot be negative (got '{raw_pr}').")
                        else:
                            purchase_rate = round(pr_val, 2)
                    except (ValueError, TypeError):
                        row_errors.append(f"Line {row_idx}: Purchase rate must be a valid number (got '{raw_pr}').")
                row_data["purchase_rate"] = purchase_rate

                # 7. mrp
                raw_mrp = row[col_map["mrp"]] if col_map.get("mrp") is not None and col_map["mrp"] < len(row) else None
                mrp = round(purchase_rate * 1.25, 2)
                if raw_mrp is not None and str(raw_mrp).strip() not in ("", "None", "nan"):
                    try:
                        mrp_val = float(str(raw_mrp).strip())
                        if mrp_val < 0:
                            row_errors.append(f"Line {row_idx}: MRP cannot be negative (got '{raw_mrp}').")
                        elif mrp_val < purchase_rate:
                            row_errors.append(f"Line {row_idx}: Retail price (MRP ₹{mrp_val:.2f}) cannot be less than purchase rate (₹{purchase_rate:.2f}).")
                        else:
                            mrp = round(mrp_val, 2)
                    except (ValueError, TypeError):
                        row_errors.append(f"Line {row_idx}: MRP must be a valid number (got '{raw_mrp}').")
                row_data["mrp"] = mrp

                # 8. category
                raw_cat = row[col_map["category"]] if col_map.get("category") is not None and col_map["category"] < len(row) else None
                cat_str = str(raw_cat).strip() if raw_cat is not None and str(raw_cat).strip() not in ("", "None", "nan") else "General Medicine"
                row_data["category"] = cat_str

                # 9. storage_temp
                raw_temp = row[col_map["storage_temp"]] if col_map.get("storage_temp") is not None and col_map["storage_temp"] < len(row) else None
                if raw_temp is not None and str(raw_temp).strip() not in ("", "None", "nan"):
                    temp_val = str(raw_temp).strip().lower()
                    if temp_val not in ("ambient", "cold_chain"):
                        row_errors.append(f"Line {row_idx}: Storage temperature must be 'ambient' or 'cold_chain' (got '{raw_temp}').")
                    else:
                        row_data["storage_temp"] = temp_val
                else:
                    row_data["storage_temp"] = "ambient"

                # 10. delivery_date
                raw_deliv = row[col_map["delivery_date"]] if col_map.get("delivery_date") is not None and col_map["delivery_date"] < len(row) else None
                if raw_deliv is not None and str(raw_deliv).strip() not in ("", "None", "nan"):
                    deliv_date, deliv_err = _parse_date_safe(raw_deliv)
                    row_data["delivery_date"] = deliv_date if deliv_date else today
                else:
                    row_data["delivery_date"] = today

                # 11. invoice_no
                raw_inv = row[col_map["invoice_no"]] if col_map.get("invoice_no") is not None and col_map["invoice_no"] < len(row) else None
                inv_str = str(raw_inv).strip() if raw_inv is not None and str(raw_inv).strip() not in ("", "None", "nan") else ""
                row_data["invoice_no"] = inv_str

                if row_errors:
                    validation_errors.extend({"row": row_idx, "reason": err} for err in row_errors)
                else:
                    validated_rows.append(row_data)

            # If any validation error occurred, reject entire file immediately (ZERO DB WRITES)
            if validation_errors:
                bullet_list = "\n".join(f"• {err['reason']}" for err in validation_errors[:8])
                if len(validation_errors) > 8:
                    bullet_list += f"\n• ...and {len(validation_errors) - 8} more issues."
                error_summary = (
                    f"Delivery bill could not be processed due to errors ({len(validation_errors)} issues found). "
                    f"No stock was changed:\n{bullet_list}"
                )
                return {
                    "success": False,
                    "error": error_summary,
                    "error_details": validation_errors,
                }

            if not validated_rows:
                return {
                    "success": False,
                    "error": "The delivery file contains no valid medicine rows to process.",
                }

            # ── Phase 2: Atomic Database Execution ────────────────────────────
            # Resolve org_id strictly from location or vendor user if not provided
            if org_id is None:
                loc = self.db.query(Location).filter(Location.id == location_id).first()
                if loc and loc.org_id:
                    org_id = loc.org_id
                else:
                    v_user = self.db.query(User).filter(User.id == vendor_user_id).first()
                    if v_user and v_user.org_id:
                        org_id = v_user.org_id
                    else:
                        return {
                            "success": False,
                            "error": "Organization could not be determined for this upload.",
                        }

            # Pre-fetch existing items in tenant catalog (case-insensitive)
            items_query = self.db.query(Item).filter(Item.org_id == org_id)
            all_items = items_query.all()
            item_lookup = {item.name.strip().lower(): item for item in all_items}

            # Pre-fetch all latest closing stocks for location in ONE single query (O(1))
            location_stocks: Dict[int, int] = self.inv_repo.get_latest_stocks_for_location(location_id)
            successful_line_items = []

            for item_data in validated_rows:
                item_key = item_data["item_name"].strip().lower()
                item = item_lookup.get(item_key)

                if not item:
                    # Auto-create item in catalog
                    item = Item(
                        name=item_data["item_name"],
                        category=item_data["category"],
                        unit=item_data["unit"],
                        mrp=item_data["mrp"],
                        purchase_rate=item_data["purchase_rate"],
                        storage_temp=item_data["storage_temp"],
                        lead_time_days=2,
                        min_stock=10,
                        org_id=org_id,
                    )
                    self.db.add(item)
                    self.db.flush()
                    item_lookup[item_key] = item
                else:
                    # Update item pricing in catalog if valid values supplied
                    if item_data["mrp"] > 0:
                        item.mrp = item_data["mrp"]
                    if item_data["purchase_rate"] > 0:
                        item.purchase_rate = item_data["purchase_rate"]
                    self.db.flush()

                # Running stock tracking in base units
                opening_stock = location_stocks.get(item.id, 0)
                closing_stock = opening_stock + item_data["quantity"]
                location_stocks[item.id] = closing_stock

                note_text = f"Vendor delivery: {item_data['quantity']} {item_data['unit']}"
                if item_data["invoice_no"]:
                    note_text += f" ({item_data['invoice_no']})"
                elif filename:
                    note_text += f" ({filename})"

                # Create inventory transaction
                self.inv_repo.create_transaction(
                    location_id=location_id,
                    item_id=item.id,
                    date=item_data["delivery_date"],
                    opening_stock=opening_stock,
                    received=item_data["quantity"],
                    issued=0,
                    closing_stock=closing_stock,
                    notes=note_text,
                    entered_by=f"vendor/upload/{vendor_user_id}",
                    batch_number=item_data["batch_number"],
                    expiry_date=item_data["expiry_date"],
                    transacted_unit=item_data["unit"],
                    transacted_qty=item_data["quantity"],
                    multiplier=1,
                    flush_only=True,
                )

                line_total = round(item_data["quantity"] * item_data["purchase_rate"], 2)
                successful_line_items.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "quantity": item_data["quantity"],
                    "unit": item_data["unit"],
                    "multiplier": 1,
                    "base_quantity": item_data["quantity"],
                    "unit_price": item_data["purchase_rate"],
                    "total": line_total,
                    "batch_number": item_data["batch_number"],
                    "expiry_date": str(item_data["expiry_date"]) if item_data["expiry_date"] else None,
                })

            # Save VendorUpload record
            upload = VendorUpload(
                vendor_user_id=vendor_user_id,
                org_id=org_id,
                filename=filename,
                location_id=location_id,
                total_rows=len(validated_rows),
                success_rows=len(validated_rows),
                error_rows=0,
                errors_detail=None,
                status="COMPLETED",
            )
            self.db.add(upload)
            self.db.flush()

            wb.close()

            # Generate delivery invoice PDF
            invoice_summary = None
            if successful_line_items:
                try:
                    invoice_summary = self._generate_invoice_for_upload(
                        upload=upload,
                        line_items=successful_line_items,
                        tx_date=today,
                        org_id=org_id,
                    )
                except Exception as inv_err:
                    logger.error("Failed to generate invoice for upload %d: %s", upload.id, str(inv_err))

            self.db.commit()

            response_data = {
                "upload_id": upload.id,
                "filename": filename,
                "total_rows": len(validated_rows),
                "rows_processed": len(validated_rows),
                "success": len(validated_rows),
                "errors": 0,
                "error_details": [],
                "status": upload.status,
            }
            if invoice_summary:
                response_data["invoice"] = invoice_summary

            return {
                "success": True,
                "data": response_data,
            }

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to process vendor upload: %s", str(e), exc_info=True)
            return {"success": False, "error": f"Failed to save delivery records: {str(e)}"}

    def _generate_invoice_for_upload(
        self,
        upload: VendorUpload,
        line_items: List[Dict[str, Any]],
        tx_date: date,
        org_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Internal helper to calculate financial totals, generate PDF, upload to Azure, and save VendorInvoice."""
        subtotal = round(sum(item["total"] for item in line_items), 2)
        tax_amount = round(subtotal * 0.18, 2)  # Standard 18% GST
        total_amount = round(subtotal + tax_amount, 2)

        # Generate sequential invoice number
        invoice_number = self.invoice_repo.generate_next_invoice_number(tx_date)

        # Lookup vendor user and location
        vendor = self.db.query(User).filter(User.id == upload.vendor_user_id).first()
        location = self.db.query(Location).filter(Location.id == upload.location_id).first()

        vendor_data = {
            "username": vendor.username if vendor else f"vendor_{upload.vendor_user_id}",
            "full_name": vendor.full_name if vendor else "Authorized Vendor",
            "email": vendor.email if vendor else "vendor@inviq.io",
        }
        location_data = {
            "name": location.name if location else f"Location #{upload.location_id}",
            "region": location.region if location else "General",
        }

        invoice_payload = {
            "invoice_number": invoice_number,
            "invoice_date": tx_date,
            "line_items": line_items,
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "status": "ISSUED",
        }

        # Render PDF via ReportLab
        pdf_bytes = InvoicePdfService.generate_invoice_pdf(
            invoice_data=invoice_payload,
            vendor_data=vendor_data,
            location_data=location_data,
            organization_name="InvIQ Healthcare Network",
        )

        # Upload to Azure Blob Storage
        blob_path = f"invoices/{tx_date.year}/{tx_date.month:02d}/{invoice_number}.pdf"
        storage_service = get_storage_service()
        pdf_url = storage_service.upload_file(
            file_bytes=pdf_bytes,
            blob_name=blob_path,
            content_type="application/pdf",
        )

        # If SAS URL is supported, generate browser presigned link
        sas_url = storage_service.generate_sas_url(blob_path) if pdf_url else None

        # Persist invoice in database
        invoice = self.invoice_repo.create(
            org_id=org_id,
            vendor_user_id=upload.vendor_user_id,
            vendor_upload_id=upload.id,
            invoice_number=invoice_number,
            invoice_date=tx_date,
            line_items=line_items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status="ISSUED",
            pdf_path=blob_path,
            pdf_url=sas_url or pdf_url,
            pdf_content=pdf_bytes,  # In-database binary fallback
        )

        logger.info(
            "Auto-generated vendor delivery invoice %s (Total: ₹%0.2f, items: %d)",
            invoice_number,
            total_amount,
            len(line_items),
        )

        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "invoice_date": str(invoice.invoice_date),
            "items_count": len(line_items),
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "total_amount": invoice.total_amount,
            "status": invoice.status,
            "pdf_url": invoice.pdf_url,
        }

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
