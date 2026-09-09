"""
InvIQ Test Excel Generator — Generates realistic pharmaceutical Excel files
for end-to-end manual testing of:
1. Initial Store Catalog & Bulk Stock Load (Large File: 100 items)
2. Requisition Cycle 1: Acute & Emergency Restock (Medium File: 25 items)
3. Requisition Cycle 2: Chronic & Daily Dispensing Restock (Medium File: 25 items)

Uses Faker with Indian medical/distributor context, openpyxl styling, and realistic
batch numbers, expiry dates, rates, and packaging hierarchies.
"""

import os
import random
from datetime import date, timedelta
from faker import Faker
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Initialize Faker with seeds for deterministic, reproducible generation
fake = Faker(['en_IN', 'en_US'])
Faker.seed(42)
random.seed(42)

# Output directory for test files
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "test_data"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. MASTER PHARMACEUTICAL CATALOG (100 Real-World Medicines)
# ═══════════════════════════════════════════════════════════════════════════════
# Includes all 25 seeded medicines from reset_and_seed_db.py + 75 standard Indian pharmacy products

MASTER_MEDICINES = [
    # ── Gastrointestinal (12 items) ──
    {"name": "Pan-D Capsule", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 140.0, "mrp": 199.0},
    {"name": "Pantocid 40mg Tablet", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 15, "lead_time": 2, "price": 115.0, "mrp": 162.0},
    {"name": "Digene Antacid Gel 200ml", "category": "Gastro", "unit": "Bottle", "storage": "ambient", "min_stock": 10, "lead_time": 3, "price": 110.0, "mrp": 155.0},
    {"name": "Omez 20mg Capsule", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 42.0, "mrp": 60.0},
    {"name": "Rantac 150mg Tablet", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 28.0, "mrp": 40.0},
    {"name": "Rabeprazole 20mg Tablet", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 65.0, "mrp": 95.0},
    {"name": "Cremaffin Plus Syrup 200ml", "category": "Gastro", "unit": "Bottle", "storage": "ambient", "min_stock": 12, "lead_time": 3, "price": 195.0, "mrp": 260.0},
    {"name": "Gelusil Liquid 200ml", "category": "Gastro", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 2, "price": 95.0, "mrp": 130.0},
    {"name": "Cyclopam Tablet", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 45.0, "mrp": 65.0},
    {"name": "Ondem 4mg MD Tablet", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 38.0, "mrp": 55.0},
    {"name": "Dulcolax 5mg Tablet", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 12.0, "mrp": 18.0},
    {"name": "Eldoper 2mg Capsule", "category": "Gastro", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 22.0, "mrp": 32.0},

    # ── Analgesics & Anti-Inflammatory (12 items) ──
    {"name": "Dolo 650mg Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 50, "lead_time": 1, "price": 22.0, "mrp": 34.0},
    {"name": "Combiflam Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 28.0, "mrp": 42.0},
    {"name": "Volini Pain Relief Gel", "category": "Analgesics", "unit": "Tube", "storage": "ambient", "min_stock": 12, "lead_time": 2, "price": 98.0, "mrp": 140.0},
    {"name": "Paracetamol 500mg Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 50, "lead_time": 1, "price": 15.0, "mrp": 22.0},
    {"name": "Ibuprofen 400mg Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 24.0, "mrp": 36.0},
    {"name": "Diclofenac 50mg Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 18.0, "mrp": 28.0},
    {"name": "Tramadol 50mg Capsule", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 68.0, "mrp": 98.0},
    {"name": "Naproxen 250mg Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 48.0, "mrp": 70.0},
    {"name": "Ketoprofen 100mg Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 72.0, "mrp": 105.0},
    {"name": "Ultracet Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 165.0, "mrp": 230.0},
    {"name": "Zerodol-SP Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 35, "lead_time": 2, "price": 85.0, "mrp": 120.0},
    {"name": "Meftal-Spas Tablet", "category": "Analgesics", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 35.0, "mrp": 50.0},

    # ── Antibiotics & Anti-Infectives (12 items) ──
    {"name": "Augmentin 625 Duo", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 160.0, "mrp": 223.0},
    {"name": "Azithral 500mg Tablet", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 92.0, "mrp": 132.0},
    {"name": "Ciplox 500mg Tablet", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 30.0, "mrp": 45.0},
    {"name": "Amoxicillin 500mg Capsule", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 55.0, "mrp": 80.0},
    {"name": "Ciprofloxacin 500mg Tablet", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 32.0, "mrp": 48.0},
    {"name": "Doxycycline 100mg Capsule", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 42.0, "mrp": 62.0},
    {"name": "Metronidazole 400mg Tablet", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 35, "lead_time": 2, "price": 18.0, "mrp": 26.0},
    {"name": "Cephalexin 500mg Capsule", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 3, "price": 135.0, "mrp": 190.0},
    {"name": "Levofloxacin 500mg Tablet", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 75.0, "mrp": 110.0},
    {"name": "Clindamycin 300mg Capsule", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 185.0, "mrp": 260.0},
    {"name": "Taxim-O 200mg Tablet", "category": "Antibiotics", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 120.0, "mrp": 175.0},
    {"name": "Monocef 1g Injection", "category": "Antibiotics", "unit": "Vial", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 58.0, "mrp": 82.0},

    # ── Cardiac & Hypertension (10 items) ──
    {"name": "Telma 40mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 3, "price": 175.0, "mrp": 245.0},
    {"name": "Ecosprin 75 Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 50, "lead_time": 2, "price": 4.0, "mrp": 6.0},
    {"name": "Amlodipine 5mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 40, "lead_time": 2, "price": 18.0, "mrp": 28.0},
    {"name": "Atorvastatin 20mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 110.0, "mrp": 160.0},
    {"name": "Losartan 50mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 45.0, "mrp": 68.0},
    {"name": "Metoprolol 25mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 52.0, "mrp": 78.0},
    {"name": "Rosuvastatin 10mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 140.0, "mrp": 205.0},
    {"name": "Concor 5mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 3, "price": 95.0, "mrp": 140.0},
    {"name": "Clopidogrel 75mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 88.0, "mrp": 130.0},
    {"name": "Envas 5mg Tablet", "category": "Cardiac", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 42.0, "mrp": 60.0},

    # ── Diabetes Care (10 items) ──
    {"name": "Glycomet GP2 Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 3, "price": 135.0, "mrp": 189.0},
    {"name": "Metformin 500mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 50, "lead_time": 2, "price": 22.0, "mrp": 35.0},
    {"name": "Glimepiride 2mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 48.0, "mrp": 72.0},
    {"name": "Januvia 100mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 310.0, "mrp": 420.0},
    {"name": "Forxiga 10mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 450.0, "mrp": 610.0},
    {"name": "Galvus Met 50/500 Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 3, "price": 280.0, "mrp": 380.0},
    {"name": "Teneligliptin 20mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 95.0, "mrp": 140.0},
    {"name": "Pioglitazone 15mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 55.0, "mrp": 80.0},
    {"name": "Rybelsus 3mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 10, "lead_time": 4, "price": 520.0, "mrp": 690.0},
    {"name": "Glucobay 50mg Tablet", "category": "Diabetes", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 115.0, "mrp": 165.0},

    # ── Respiratory & Anti-Allergic (10 items) ──
    {"name": "Montair LC Tablet", "category": "Respiratory", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 150.0, "mrp": 210.0},
    {"name": "Allegra 120mg Tablet", "category": "Anti-Allergic", "unit": "Strip", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 155.0, "mrp": 218.0},
    {"name": "Ascoril LS Syrup 100ml", "category": "Respiratory", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 82.0, "mrp": 118.0},
    {"name": "Otrivin Nasal Spray", "category": "ENT", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 2, "price": 68.0, "mrp": 98.0},
    {"name": "Levocetirizine 5mg Tablet", "category": "Anti-Allergic", "unit": "Strip", "storage": "ambient", "min_stock": 40, "lead_time": 1, "price": 28.0, "mrp": 42.0},
    {"name": "Asthalin 100mcg Inhaler", "category": "Respiratory", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 2, "price": 125.0, "mrp": 170.0},
    {"name": "Budecort 200 Inhaler", "category": "Respiratory", "unit": "Bottle", "storage": "ambient", "min_stock": 12, "lead_time": 2, "price": 290.0, "mrp": 395.0},
    {"name": "Alex Cough Syrup 100ml", "category": "Respiratory", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 90.0, "mrp": 128.0},
    {"name": "Cheston Cold Tablet", "category": "Respiratory", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 38.0, "mrp": 55.0},
    {"name": "Sinarest Tablet", "category": "Respiratory", "unit": "Strip", "storage": "ambient", "min_stock": 35, "lead_time": 2, "price": 42.0, "mrp": 60.0},

    # ── Thyroid & Hormonal (4 items) ──
    {"name": "Thyronorm 50mcg Tablet", "category": "Thyroid", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 3, "price": 115.0, "mrp": 160.0},
    {"name": "Thyronorm 25mcg Tablet", "category": "Thyroid", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 110.0, "mrp": 155.0},
    {"name": "Eltroxin 100mcg Tablet", "category": "Thyroid", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 3, "price": 130.0, "mrp": 180.0},
    {"name": "Susten 200mg Capsule", "category": "Hormonal", "unit": "Strip", "storage": "ambient", "min_stock": 10, "lead_time": 3, "price": 260.0, "mrp": 360.0},

    # ── Vitamins & Dietary Supplements (10 items) ──
    {"name": "Shelcal 500mg Tablet", "category": "Vitamins", "unit": "Bottle", "storage": "ambient", "min_stock": 25, "lead_time": 3, "price": 100.0, "mrp": 145.0},
    {"name": "Becosules Z Capsule", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 40, "lead_time": 2, "price": 35.0, "mrp": 52.0},
    {"name": "Liv 52 Syrup 200ml", "category": "Supplements", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 3, "price": 120.0, "mrp": 170.0},
    {"name": "Electral ORS Sachet 21.8g", "category": "Electrolytes", "unit": "Sachet", "storage": "ambient", "min_stock": 60, "lead_time": 1, "price": 15.0, "mrp": 22.0},
    {"name": "Neurobion Forte Tablet", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 40, "lead_time": 2, "price": 30.0, "mrp": 42.0},
    {"name": "Supradyn Daily Tablet", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 45.0, "mrp": 62.0},
    {"name": "Limcee 500mg Chewable", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 35, "lead_time": 2, "price": 20.0, "mrp": 28.0},
    {"name": "Zincovit Tablet", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 75.0, "mrp": 105.0},
    {"name": "Evion 400mg Capsule", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 35, "lead_time": 2, "price": 28.0, "mrp": 40.0},
    {"name": "Calcimax 500 Tablet", "category": "Vitamins", "unit": "Strip", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 140.0, "mrp": 195.0},

    # ── First Aid, Antiseptics & Surgical (10 items) ──
    {"name": "Betadine 10% Solution", "category": "First Aid", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 2, "price": 88.0, "mrp": 125.0},
    {"name": "Band-Aid Washproof 20s", "category": "First Aid", "unit": "Box", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 42.0, "mrp": 60.0},
    {"name": "Dettol Antiseptic Liquid 250ml", "category": "First Aid", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 115.0, "mrp": 155.0},
    {"name": "Savlon Antiseptic Liquid 200ml", "category": "First Aid", "unit": "Bottle", "storage": "ambient", "min_stock": 15, "lead_time": 2, "price": 75.0, "mrp": 105.0},
    {"name": "Micropore Surgical Tape 1in", "category": "First Aid", "unit": "Box", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 48.0, "mrp": 70.0},
    {"name": "Cotton Absorbent 100g", "category": "First Aid", "unit": "Roll", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 35.0, "mrp": 50.0},
    {"name": "Gauze Roll 7.5cm", "category": "First Aid", "unit": "Roll", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 20.0, "mrp": 30.0},
    {"name": "Surgical Gloves Pair", "category": "First Aid", "unit": "Pair", "storage": "ambient", "min_stock": 50, "lead_time": 2, "price": 18.0, "mrp": 25.0},
    {"name": "Hand Sanitizer 500ml", "category": "First Aid", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 120.0, "mrp": 175.0},
    {"name": "Burnol Ointment 20g", "category": "First Aid", "unit": "Tube", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 55.0, "mrp": 80.0},

    # ── Cold Chain Biologicals & Vaccines (6 items) ──
    {"name": "Insulin Lantus Solostar", "category": "Cold Chain", "unit": "Pen", "storage": "cold_chain", "min_stock": 10, "lead_time": 1, "price": 520.0, "mrp": 680.0},
    {"name": "Covaxin Vaccine Vial", "category": "Cold Chain", "unit": "Vial", "storage": "cold_chain", "min_stock": 5, "lead_time": 1, "price": 220.0, "mrp": 300.0},
    {"name": "Human Mixtard 30/70 100IU", "category": "Cold Chain", "unit": "Vial", "storage": "cold_chain", "min_stock": 12, "lead_time": 1, "price": 140.0, "mrp": 185.0},
    {"name": "Humalog KwikPen 100IU/ml", "category": "Cold Chain", "unit": "Pen", "storage": "cold_chain", "min_stock": 8, "lead_time": 1, "price": 580.0, "mrp": 750.0},
    {"name": "Rabipur Rabies Vaccine", "category": "Cold Chain", "unit": "Vial", "storage": "cold_chain", "min_stock": 6, "lead_time": 1, "price": 310.0, "mrp": 420.0},
    {"name": "Tetanus Toxoid 0.5ml Injection", "category": "Cold Chain", "unit": "Vial", "storage": "cold_chain", "min_stock": 25, "lead_time": 1, "price": 12.0, "mrp": 18.0},

    # ── Dermatology & Topical Ointments (4 items) ──
    {"name": "Betnovate-N Cream 20g", "category": "Dermatology", "unit": "Tube", "storage": "ambient", "min_stock": 25, "lead_time": 2, "price": 42.0, "mrp": 60.0},
    {"name": "Soframycin Skin Cream 30g", "category": "Dermatology", "unit": "Tube", "storage": "ambient", "min_stock": 30, "lead_time": 2, "price": 48.0, "mrp": 68.0},
    {"name": "Candid-B Cream 20g", "category": "Dermatology", "unit": "Tube", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 105.0, "mrp": 150.0},
    {"name": "Clocip Dusting Powder 100g", "category": "Dermatology", "unit": "Bottle", "storage": "ambient", "min_stock": 20, "lead_time": 2, "price": 75.0, "mrp": 110.0},
]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: OPENPYXL STYLING SUITE
# ═══════════════════════════════════════════════════════════════════════════════

BORDER_THIN = Side(border_style="thin", color="E0E0E0")
CELL_BORDER = Border(left=BORDER_THIN, right=BORDER_THIN, top=BORDER_THIN, bottom=BORDER_THIN)

def apply_excel_styling(ws, header_bg="1E1E1E", header_fg="FFFFFF"):
    """Format sheet with premium dark-mode headers, zebra stripes, and auto column widths."""
    ws.views.sheetView[0].showGridLines = True
    ws.row_dimensions[1].height = 28

    header_font = Font(name="Calibri", size=11, bold=True, color=header_fg)
    header_fill = PatternFill(start_color=header_bg, end_color=header_bg, fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    row_even_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    row_odd_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    for col_idx, cell in enumerate(ws[1], 1):
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = CELL_BORDER

    # Style data rows
    for row_idx, row in enumerate(ws.iter_rows(min_row=2), 2):
        ws.row_dimensions[row_idx].height = 20
        fill = row_even_fill if row_idx % 2 == 0 else row_odd_fill
        for cell in row:
            cell.fill = fill
            cell.border = CELL_BORDER
            cell.font = Font(name="Calibri", size=10)
            
            # Numeric formatting
            if isinstance(cell.value, float):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif isinstance(cell.value, int):
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto-adjust column widths with safety margin
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GENERATOR: FILE 1 (LARGE INITIAL CATALOG & STOCK - 100 ITEMS)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_large_catalog_file():
    """
    Generates 01_Initial_Stock_Large_Catalog_100.xlsx.
    Used for 1st-time testing to populate the store with a comprehensive catalog,
    batch tracking, price book, and healthy initial closing stocks.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Delivery_Manifest"

    headers = [
        "item_name",
        "category",
        "quantity_received",
        "unit_price",
        "packaging_unit",
        "batch_number",
        "expiry_date",
        "delivery_date",
        "storage_temp",
        "lead_time_days",
        "min_stock",
        "notes"
    ]
    ws.append(headers)

    today = date(2026, 9, 1)

    for idx, med in enumerate(MASTER_MEDICINES, 1):
        # Realistic initial quantity: between 40 and 450 units
        qty = random.choice([50, 75, 100, 150, 200, 250, 300, 400, 500])
        
        # Batch number: LOT-2026-XXXXX
        batch_no = f"LOT-2026-{1000 + idx:04d}"
        
        # Expiry date: 14 to 30 months in future
        days_to_expiry = random.randint(420, 900)
        exp_date = (today + timedelta(days=days_to_expiry)).strftime("%Y-%m-%d")
        
        # Note
        note = f"Initial stock setup - Invoice #{fake.bothify(text='INV-2026-####')}"

        row = [
            med["name"],
            med["category"],
            qty,
            float(med["price"]),
            med["unit"],
            batch_no,
            exp_date,
            today.strftime("%Y-%m-%d"),
            med["storage"],
            med["lead_time"],
            med["min_stock"],
            note
        ]
        ws.append(row)

    apply_excel_styling(ws, header_bg="1E1E1E", header_fg="FFFFFF")

    # Add Instruction Sheet
    info_ws = wb.create_sheet(title="Testing_Instructions")
    info_ws.views.sheetView[0].showGridLines = True
    info_ws.append(["InvIQ Test File 01: Initial Large Stock Manifest"])
    info_ws.append([])
    info_ws.append(["File Purpose:", "1st Time Initial Load — Populates store inventory, catalog, batch records & initial stock."])
    info_ws.append(["Total Items:", len(MASTER_MEDICINES)])
    info_ws.append(["How to test manually:", ""])
    info_ws.append(["Option A (Vendor Delivery):", "Log in as Vendor/Admin -> Navigate to '/vendor/data-entry' -> Choose your Branch/Counter -> Upload this file."])
    info_ws.append(["", "Verifies: Real-time stock update, automated batch tracking, and official GST Invoice PDF generation."])
    info_ws.append(["Option B (AI Data Import):", "Navigate to '/data-import' -> Target Entity: 'inventory_transaction' -> Upload this file."])
    info_ws.append(["", "Verifies: AI Column Auto-Mapping, confidence gating, quarantine review, and batch ingestion."])
    
    info_ws.column_dimensions["A"].width = 28
    info_ws.column_dimensions["B"].width = 80
    info_ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="F26A4B")

    filepath = os.path.join(OUTPUT_DIR, "01_Initial_Stock_Large_Catalog_100.xlsx")
    wb.save(filepath)
    wb.close()
    print(f"✅ Generated File 1: {filepath} ({len(MASTER_MEDICINES)} rows)")
    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GENERATOR: FILE 2 (MEDIUM REQUISITION 1: ACUTE & EMERGENCY - 25 ITEMS)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_acute_requisition_file():
    """
    Generates 02_Requisition_Cycle1_Acute_Emergency_25.xlsx.
    25 items strictly for Emergency, ICU, Trauma, Acute infection & pain relief.
    All 25 items exist inside File 1.
    """
    acute_items = [
        # Analgesics & Trauma
        "Dolo 650mg Tablet",
        "Combiflam Tablet",
        "Paracetamol 500mg Tablet",
        "Tramadol 50mg Capsule",
        "Diclofenac 50mg Tablet",
        "Ultracet Tablet",
        "Zerodol-SP Tablet",
        "Volini Pain Relief Gel",
        # Antibiotics & Acute Infections
        "Augmentin 625 Duo",
        "Azithral 500mg Tablet",
        "Ciplox 500mg Tablet",
        "Amoxicillin 500mg Capsule",
        "Ciprofloxacin 500mg Tablet",
        "Monocef 1g Injection",
        "Taxim-O 200mg Tablet",
        # Emergency & First Aid
        "Betadine 10% Solution",
        "Band-Aid Washproof 20s",
        "Dettol Antiseptic Liquid 250ml",
        "Micropore Surgical Tape 1in",
        "Cotton Absorbent 100g",
        "Gauze Roll 7.5cm",
        "Surgical Gloves Pair",
        "Burnol Ointment 20g",
        # GI & Cold Chain Acute
        "Ondem 4mg MD Tablet",
        "Tetanus Toxoid 0.5ml Injection",
    ]

    med_lookup = {m["name"]: m for m in MASTER_MEDICINES}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Requisition_Manifest"

    headers = [
        "item_name",
        "requested_qty",
        "quantity_received",
        "packaging_unit",
        "department",
        "urgency",
        "unit_price",
        "batch_number",
        "expiry_date",
        "delivery_date",
        "notes"
    ]
    ws.append(headers)

    today = date(2026, 9, 6)

    for idx, item_name in enumerate(acute_items, 1):
        med = med_lookup[item_name]
        # Acute requested qty: between 15 and 60 units
        qty = random.choice([15, 20, 25, 30, 40, 50, 60])
        batch_no = f"REQ1-2026-{2000 + idx:04d}"
        days_to_expiry = random.randint(400, 750)
        exp_date = (today + timedelta(days=days_to_expiry)).strftime("%Y-%m-%d")
        
        dept = random.choice(["Emergency", "ICU", "OT", "Pharmacy Counter"])
        urgency = "EMERGENCY" if dept in ["Emergency", "ICU"] else "HIGH"

        row = [
            med["name"],
            qty,
            qty,  # quantity_received matches requested_qty for vendor fulfillment upload
            med["unit"],
            dept,
            urgency,
            float(med["price"]),
            batch_no,
            exp_date,
            today.strftime("%Y-%m-%d"),
            f"Emergency Replenishment Cycle #1 ({dept}) - Urgency: {urgency}"
        ]
        ws.append(row)

    apply_excel_styling(ws, header_bg="2E2E2E", header_fg="FFFFFF")

    # Add Instruction Sheet
    info_ws = wb.create_sheet(title="Testing_Instructions")
    info_ws.views.sheetView[0].showGridLines = True
    info_ws.append(["InvIQ Test File 02: Acute & Emergency Requisition Cycle"])
    info_ws.append([])
    info_ws.append(["File Purpose:", "Requisition Testing 1 — Emergency & Acute Care Ward Restocking."])
    info_ws.append(["Total Items:", len(acute_items)])
    info_ws.append(["How to test manually:", ""])
    info_ws.append(["Step 1 (Staff Requisition):", "Log in as Staff ('staff_single' or 'staff_apollo_1') -> Go to '/staff/requisition'."])
    info_ws.append(["", "Select items from this file (e.g., Augmentin, Dolo 650, Monocef, Surgical Gloves) with Urgency: EMERGENCY."])
    info_ws.append(["Step 2 (Admin Review):", "Log in as Admin -> Go to '/admin/requisitions' -> Review & Click 'Approve'."])
    info_ws.append(["Step 3 (Vendor Fulfillment):", "Go to '/vendor/data-entry' -> Upload this file to simulate vendor restocking the approved branch."])

    info_ws.column_dimensions["A"].width = 28
    info_ws.column_dimensions["B"].width = 80
    info_ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="F26A4B")

    filepath = os.path.join(OUTPUT_DIR, "02_Requisition_Cycle1_Acute_Emergency_25.xlsx")
    wb.save(filepath)
    wb.close()
    print(f"✅ Generated File 2: {filepath} ({len(acute_items)} rows)")
    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GENERATOR: FILE 3 (MEDIUM REQUISITION 2: CHRONIC & DAILY CARE - 25 ITEMS)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_chronic_requisition_file():
    """
    Generates 03_Requisition_Cycle2_Chronic_DailyCare_25.xlsx.
    25 items strictly for Chronic Care (Diabetes, Cardiac, Gastro, Thyroid, Nutrition).
    All 25 items exist inside File 1.
    """
    chronic_items = [
        # Diabetes & Endocrine
        "Glycomet GP2 Tablet",
        "Metformin 500mg Tablet",
        "Glimepiride 2mg Tablet",
        "Januvia 100mg Tablet",
        "Galvus Met 50/500 Tablet",
        "Insulin Lantus Solostar",
        "Thyronorm 50mcg Tablet",
        "Thyronorm 25mcg Tablet",
        # Cardiac & Hypertension
        "Telma 40mg Tablet",
        "Ecosprin 75 Tablet",
        "Amlodipine 5mg Tablet",
        "Atorvastatin 20mg Tablet",
        "Losartan 50mg Tablet",
        "Metoprolol 25mg Tablet",
        "Rosuvastatin 10mg Tablet",
        # Gastro Maintenance
        "Pan-D Capsule",
        "Pantocid 40mg Tablet",
        "Digene Antacid Gel 200ml",
        "Omez 20mg Capsule",
        "Cremaffin Plus Syrup 200ml",
        # Respiratory & Daily Allergy
        "Montair LC Tablet",
        "Allegra 120mg Tablet",
        "Ascoril LS Syrup 100ml",
        # Daily Vitamins & Supplements
        "Shelcal 500mg Tablet",
        "Becosules Z Capsule",
    ]

    med_lookup = {m["name"]: m for m in MASTER_MEDICINES}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Requisition_Manifest"

    headers = [
        "item_name",
        "requested_qty",
        "quantity_received",
        "packaging_unit",
        "department",
        "urgency",
        "unit_price",
        "batch_number",
        "expiry_date",
        "delivery_date",
        "notes"
    ]
    ws.append(headers)

    today = date(2026, 9, 6)

    for idx, item_name in enumerate(chronic_items, 1):
        med = med_lookup[item_name]
        # Chronic requested qty: between 40 and 150 units
        qty = random.choice([40, 50, 60, 75, 80, 100, 120, 150])
        batch_no = f"REQ2-2026-{3000 + idx:04d}"
        days_to_expiry = random.randint(450, 850)
        exp_date = (today + timedelta(days=days_to_expiry)).strftime("%Y-%m-%d")
        
        dept = random.choice(["Pharmacy Counter", "General Ward", "Cardiology"])
        urgency = "NORMAL"

        row = [
            med["name"],
            qty,
            qty,  # quantity_received matches requested_qty for vendor fulfillment upload
            med["unit"],
            dept,
            urgency,
            float(med["price"]),
            batch_no,
            exp_date,
            today.strftime("%Y-%m-%d"),
            f"Monthly OPD Chronic Refill ({dept}) - Urgency: {urgency}"
        ]
        ws.append(row)

    apply_excel_styling(ws, header_bg="1E1E1E", header_fg="FFFFFF")

    # Add Instruction Sheet
    info_ws = wb.create_sheet(title="Testing_Instructions")
    info_ws.views.sheetView[0].showGridLines = True
    info_ws.append(["InvIQ Test File 03: Chronic Care & OPD Refill Requisition Cycle"])
    info_ws.append([])
    info_ws.append(["File Purpose:", "Requisition Testing 2 — Chronic Disease & High-Volume Dispensing Restock."])
    info_ws.append(["Total Items:", len(chronic_items)])
    info_ws.append(["How to test manually:", ""])
    info_ws.append(["Step 1 (Staff Requisition):", "Log in as Staff -> Go to '/staff/requisition'."])
    info_ws.append(["", "Select chronic medications from this file (Glycomet, Telma, Ecosprin, Shelcal) with Urgency: NORMAL."])
    info_ws.append(["Step 2 (Admin Review):", "Log in as Admin -> Go to '/admin/requisitions' -> Filter by Department/Status -> Approve."])
    info_ws.append(["Step 3 (Vendor Restocking):", "Upload this file via '/vendor/data-entry' to deliver replenished stock to counter."])

    info_ws.column_dimensions["A"].width = 28
    info_ws.column_dimensions["B"].width = 80
    info_ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="F26A4B")

    filepath = os.path.join(OUTPUT_DIR, "03_Requisition_Cycle2_Chronic_DailyCare_25.xlsx")
    wb.save(filepath)
    wb.close()
    print(f"✅ Generated File 3: {filepath} ({len(chronic_items)} rows)")
    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("🏥 InvIQ — Generating Developer Test Excel Files with Faker")
    print("=" * 70)
    f1 = generate_large_catalog_file()
    f2 = generate_acute_requisition_file()
    f3 = generate_chronic_requisition_file()
    print("=" * 70)
    print(f"🎉 Successfully created 3 test files in: {OUTPUT_DIR}")
    print("   1. 01_Initial_Stock_Large_Catalog_100.xlsx (100 rows, Initial Ingest)")
    print("   2. 02_Requisition_Cycle1_Acute_Emergency_25.xlsx (25 rows, Acute Care Requisition)")
    print("   3. 03_Requisition_Cycle2_Chronic_DailyCare_25.xlsx (25 rows, Chronic Care Requisition)")
    print("=" * 70)
