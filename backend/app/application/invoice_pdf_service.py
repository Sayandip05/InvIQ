"""
Invoice PDF Service — Application Layer
========================================
Generates professional, compact, high-resolution PDF invoices for vendor deliveries
using ReportLab. The output is rendered into an in-memory byte buffer for direct
upload to Azure Blob Storage and HTTP streaming.
"""

from io import BytesIO
from typing import Dict, Any, List
from datetime import datetime, date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


class InvoicePdfService:
    """Renders formal vendor delivery invoice PDFs using ReportLab."""

    @classmethod
    def generate_invoice_pdf(
        cls,
        invoice_data: Dict[str, Any],
        vendor_data: Dict[str, Any],
        location_data: Dict[str, Any],
        organization_name: str = "InvIQ Healthcare Network",
    ) -> bytes:
        """
        Generate a styled PDF invoice and return raw bytes.

        Args:
            invoice_data: Dict containing invoice_number, invoice_date, line_items, subtotal, tax_amount, total_amount, status
            vendor_data: Dict containing username, full_name, email
            location_data: Dict containing name, type, region, address
            organization_name: Optional organization name

        Returns:
            bytes: Generated PDF binary data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        styles = getSampleStyleSheet()

        # Custom paragraph styles
        brand_title_style = ParagraphStyle(
            "BrandTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#4f46e5"),
        )
        invoice_heading_style = ParagraphStyle(
            "InvoiceHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#0f172a"),
        )
        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )
        meta_value_style = ParagraphStyle(
            "MetaValue",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0f172a"),
        )
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.white,
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        table_cell_right = ParagraphStyle(
            "TableCellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#1e293b"),
        )
        total_label_style = ParagraphStyle(
            "TotalLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#0f172a"),
        )
        total_amount_style = ParagraphStyle(
            "TotalAmount",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#4f46e5"),
        )

        elements = []

        # 1. Top Header (Brand Left / Invoice Title Right)
        inv_num = invoice_data.get("invoice_number", "INV-2026-000")
        inv_date = invoice_data.get("invoice_date", date.today().isoformat())
        if isinstance(inv_date, (datetime, date)):
            inv_date_str = inv_date.strftime("%Y-%m-%d")
        else:
            inv_date_str = str(inv_date)

        top_header_data = [
            [
                Paragraph(f"<b>InvIQ</b> | {organization_name}", brand_title_style),
                Paragraph("DELIVERY INVOICE", invoice_heading_style),
            ],
            [
                Paragraph(
                    "<font color='#64748b' size='8'>Smart Healthcare Inventory Management Platform</font>",
                    styles["Normal"],
                ),
                Paragraph(
                    f"<font color='#4f46e5' size='10'><b>{inv_num}</b></font>",
                    ParagraphStyle("InvNumRight", alignment=TA_RIGHT),
                ),
            ],
        ]
        top_table = Table(top_header_data, colWidths=[3.6 * inch, 3.6 * inch])
        top_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ])
        )
        elements.append(top_table)
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4f46e5"), spaceAfter=12))

        # 2. Two-Column Metadata Box (Vendor info & Delivery Details)
        vendor_name = vendor_data.get("full_name") or vendor_data.get("username", "Authorized Vendor")
        vendor_email = vendor_data.get("email", "-")
        location_name = location_data.get("name", "Central Receiving Depot")
        location_region = location_data.get("region", "-")

        meta_box_data = [
            [
                Paragraph("<b>DELIVERED BY (VENDOR):</b>", meta_label_style),
                Paragraph("<b>DELIVERY LOCATION:</b>", meta_label_style),
            ],
            [
                Paragraph(f"<b>{vendor_name}</b><br/>Email: {vendor_email}<br/>Username: {vendor_data.get('username', '-')}", meta_value_style),
                Paragraph(f"<b>{location_name}</b><br/>Region: {location_region}<br/>Delivery Date: {inv_date_str}", meta_value_style),
            ],
        ]
        meta_table = Table(meta_box_data, colWidths=[3.6 * inch, 3.6 * inch])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # 3. Line Items Table
        line_items = invoice_data.get("line_items", [])
        
        table_rows = [
            [
                Paragraph("<b>#</b>", table_header_style),
                Paragraph("<b>Item Description / Medicine</b>", table_header_style),
                Paragraph("<b>Qty</b>", table_header_style),
                Paragraph("<b>Unit</b>", table_header_style),
                Paragraph("<b>Unit Price (₹)</b>", table_header_style),
                Paragraph("<b>Amount (₹)</b>", table_header_style),
            ]
        ]

        for idx, item in enumerate(line_items, 1):
            name = item.get("item_name", "Medicine Item")
            qty = item.get("quantity", item.get("qty", 1))
            unit = item.get("unit", "Units")
            price = float(item.get("unit_price", 150.0))
            line_total = float(item.get("total", qty * price))

            table_rows.append([
                Paragraph(str(idx), table_cell_style),
                Paragraph(f"<b>{name}</b>", table_cell_style),
                Paragraph(str(qty), table_cell_right),
                Paragraph(unit, table_cell_style),
                Paragraph(f"{price:,.2f}", table_cell_right),
                Paragraph(f"{line_total:,.2f}", table_cell_right),
            ])

        col_widths = [0.4 * inch, 3.2 * inch, 0.7 * inch, 0.7 * inch, 1.0 * inch, 1.2 * inch]
        items_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        items_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ])
        )
        elements.append(items_table)
        elements.append(Spacer(1, 10))

        # 4. Totals Summary
        subtotal = float(invoice_data.get("subtotal", 0.0))
        tax_amount = float(invoice_data.get("tax_amount", 0.0))
        total_amount = float(invoice_data.get("total_amount", 0.0))

        totals_data = [
            [
                Paragraph("<b>Notes / Terms:</b>", meta_label_style),
                Paragraph("Subtotal:", total_label_style),
                Paragraph(f"₹ {subtotal:,.2f}", total_label_style),
            ],
            [
                Paragraph("Goods received and verified in good physical order.<br/>Batch tracking enabled.", meta_value_style),
                Paragraph("GST / Tax (18%):", total_label_style),
                Paragraph(f"₹ {tax_amount:,.2f}", total_label_style),
            ],
            [
                Paragraph(f"Status: <b>{invoice_data.get('status', 'ISSUED')}</b>", meta_label_style),
                Paragraph("<b>Grand Total:</b>", total_amount_style),
                Paragraph(f"<b>₹ {total_amount:,.2f}</b>", total_amount_style),
            ],
        ]

        totals_table = Table(totals_data, colWidths=[3.8 * inch, 1.8 * inch, 1.6 * inch])
        totals_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (1, 1), (2, 1), 0.75, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (1, 2), (2, 2), colors.HexColor("#eef2ff")),
            ])
        )
        elements.append(totals_table)
        elements.append(Spacer(1, 20))

        # 5. Footer & Verification Stamp
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        footer_text = Paragraph(
            f"<font color='#94a3b8' size='7.5'>This is an automated delivery invoice generated by InvIQ Smart Healthcare Inventory Platform on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. System verified.</font>",
            ParagraphStyle("Footer", alignment=TA_CENTER),
        )
        elements.append(footer_text)

        # Build document
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
