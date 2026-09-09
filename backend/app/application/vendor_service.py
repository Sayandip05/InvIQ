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
from datetime import date
from typing import Dict, Any, List, Optional
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
        Parse an Excel file, create inventory transactions, and generate a formal delivery invoice.

        Expected columns: item_name, quantity_received, unit_price (optional), delivery_date (optional), notes (optional)

        Returns summary with upload & invoice details.
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
                elif "price" in h or "cost" in h or "rate" in h or ("unit" in h and "price" in h):
                    col_map["price"] = i
                elif "unit" in h or "packaging" in h or "uom" in h:
                    col_map["unit"] = i
                elif "batch" in h or "lot" in h:
                    col_map["batch"] = i
                elif "expir" in h or "exp" in h:
                    col_map["expiry"] = i
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

            # Pre-fetch all latest closing stocks for location in ONE single query (eliminates N+1)
            location_stocks: Dict[int, int] = self.inv_repo.get_latest_stocks_for_location(location_id)

            # Process rows
            success_count = 0
            error_list = []
            successful_line_items = []
            today = date.today()

            for row_idx, row in enumerate(rows[1:], start=2):
                try:
                    item_name = str(row[col_map["item_name"]]).strip() if row[col_map["item_name"]] else ""
                    quantity = row[col_map["quantity"]]
                    delivery_date = (
                        row[col_map.get("date", -1)]
                        if col_map.get("date") is not None and col_map.get("date") < len(row)
                        else None
                    )
                    notes = (
                        str(row[col_map.get("notes", -1)]).strip()
                        if col_map.get("notes") is not None and col_map.get("notes") < len(row) and row[col_map.get("notes")]
                        else ""
                    )
                    unit = (
                        str(row[col_map.get("unit", -1)]).strip()
                        if col_map.get("unit") is not None and col_map.get("unit") < len(row) and row[col_map.get("unit")]
                        else None
                    )
                    batch_number = (
                        str(row[col_map.get("batch", -1)]).strip()
                        if col_map.get("batch") is not None and col_map.get("batch") < len(row) and row[col_map.get("batch")]
                        else None
                    )
                    expiry_date = (
                        row[col_map.get("expiry", -1)]
                        if col_map.get("expiry") is not None and col_map.get("expiry") < len(row)
                        else None
                    )

                    # Optional price per item
                    unit_price = 150.0  # sensible healthcare item default
                    if col_map.get("price") is not None and col_map.get("price") < len(row) and row[col_map.get("price")] is not None:
                        try:
                            parsed_price = float(row[col_map["price"]])
                            if parsed_price > 0:
                                unit_price = parsed_price
                        except (TypeError, ValueError):
                            pass

                    if not item_name:
                        error_list.append({"row": row_idx, "reason": "Empty item name"})
                        continue

                    # Try exact match (case-insensitive)
                    matched_item = item_lookup.get(item_name.lower())

                    if not matched_item and org_id:
                        try:
                            new_item = Item(
                                name=item_name,
                                category="general",
                                unit=unit or "units",
                                lead_time_days=3,
                                min_stock=10,
                                storage_temp="ambient",
                                org_id=org_id,
                            )
                            self.db.add(new_item)
                            self.db.flush()
                            item_lookup[item_name.lower()] = new_item
                            matched_item = new_item
                        except Exception as create_err:
                            logger.warning("Could not auto-create item '%s': %s", item_name, create_err)

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

                    # Resolve packaging tier & multiplier
                    from app.application.uom_service import resolve_item_packaging
                    pkg_res = resolve_item_packaging(matched_item, unit_name_or_barcode=unit)
                    multiplier = max(1, int(pkg_res.get("multiplier", 1)))
                    resolved_unit = pkg_res.get("unit_name", getattr(matched_item, "unit", "Units") or "Units")

                    base_qty_received = qty * multiplier

                    # In-memory closing stock tracking in base units (O(1) — 0 DB roundtrips)
                    opening_stock = location_stocks.get(matched_item.id, 0)
                    closing_stock = opening_stock + base_qty_received
                    location_stocks[matched_item.id] = closing_stock

                    # Create transaction in base units with packaging context (flush only — commit at end)
                    self.inv_repo.create_transaction(
                        location_id=location_id,
                        item_id=matched_item.id,
                        date=tx_date,
                        opening_stock=opening_stock,
                        received=base_qty_received,
                        issued=0,
                        closing_stock=closing_stock,
                        notes=f"Vendor delivery: {qty} {resolved_unit} ({notes or filename})",
                        entered_by=f"vendor/upload/{vendor_user_id}",
                        batch_number=batch_number if batch_number else None,
                        expiry_date=expiry_date if expiry_date else None,
                        transacted_unit=resolved_unit,
                        transacted_qty=qty,
                        multiplier=multiplier,
                        flush_only=True,
                    )

                    success_count += 1
                    line_total = round(qty * unit_price, 2)
                    successful_line_items.append({
                        "item_id": matched_item.id,
                        "item_name": matched_item.name,
                        "quantity": qty,
                        "unit": resolved_unit,
                        "multiplier": multiplier,
                        "base_quantity": base_qty_received,
                        "unit_price": unit_price,
                        "total": line_total,
                        "batch_number": batch_number if batch_number else None,
                        "expiry_date": str(expiry_date) if expiry_date else None,
                    })

                except Exception as e:
                    error_list.append({"row": row_idx, "reason": str(e)})

            # Commit all successful transactions atomically
            self.db.commit()

            # Resolve org_id strictly from location or vendor user if not provided
            if org_id is None:
                from app.infrastructure.database.models import Location, User
                loc = self.db.query(Location).filter(Location.id == location_id).first()
                if loc and loc.org_id:
                    org_id = loc.org_id
                else:
                    v_user = self.db.query(User).filter(User.id == vendor_user_id).first()
                    if v_user and v_user.org_id:
                        org_id = v_user.org_id
                    else:
                        raise ValidationError("Organization ID (org_id) is required and could not be determined for this upload")

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
                status="COMPLETED" if error_list == [] else "PARTIAL" if success_count > 0 else "FAILED",
            )
            self.db.add(upload)
            self.db.commit()
            self.db.refresh(upload)

            wb.close()

            # ── Generate Vendor Delivery Invoice ─────────────────────────
            invoice_summary = None
            if success_count > 0:
                try:
                    invoice_summary = self._generate_invoice_for_upload(
                        upload=upload,
                        line_items=successful_line_items,
                        tx_date=today,
                        org_id=org_id,
                    )
                except Exception as inv_err:
                    logger.error("Failed to generate invoice for upload %d: %s", upload.id, str(inv_err))

            response_data = {
                "upload_id": upload.id,
                "filename": filename,
                "total_rows": len(rows) - 1,
                "success": success_count,
                "errors": len(error_list),
                "error_details": error_list[:20],  # Cap at 20 errors in response
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
            logger.error("Failed to process vendor upload: %s", str(e))
            return {"success": False, "error": f"Failed to process file: {str(e)}"}

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
