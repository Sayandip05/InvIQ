"""
InvIQ Pharmacy Warehouse Seed Script
======================================
Generates wholesale pharmacy / central warehouse data.

Architecture notes:
  - storage_temp belongs on Item   (product-level: Insulin is ALWAYS cold_chain)
  - batch_number + expiry_date belong on InventoryTransaction
    (each inbound delivery records its own batch and expiry)

Dataset (30-40% smaller than original generic seed):
  - 1  organization   (NovaMed Pharma Distributors)
  - 10 locations      (2 central warehouses + 5 retail pharmacies + 3 hospital clients)
  - 2000 items        (curated pharma catalog + generated extras)
  - 8000 transactions (inbound from suppliers + outbound to client locations)
"""

import os
import sys
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.connection import SessionLocal, engine, Base
from app.infrastructure.database.models import (
    Organization, Location, Item, InventoryTransaction,
)

random.seed(42)

# ── Pharmacy product catalog ──────────────────────────────────────────────────

PHARMA_PRODUCTS = [
    # (name, category, unit, lead_time_days, min_stock, storage_temp)
    # Antibiotics
    ("Amoxicillin 500mg Capsules",         "Antibiotics",            "box",     7,  200, "ambient"),
    ("Azithromycin 250mg Tablets",          "Antibiotics",            "box",     5,  150, "ambient"),
    ("Ciprofloxacin 500mg Tablets",         "Antibiotics",            "box",     7,  180, "ambient"),
    ("Metronidazole 400mg Tablets",         "Antibiotics",            "box",     5,  120, "ambient"),
    ("Doxycycline 100mg Capsules",          "Antibiotics",            "box",     7,  100, "ambient"),
    ("Cefixime 400mg Tablets",              "Antibiotics",            "box",     5,   90, "ambient"),
    ("Cloxacillin 500mg Capsules",          "Antibiotics",            "box",     7,   80, "ambient"),
    ("Erythromycin 500mg Tablets",          "Antibiotics",            "box",     7,   70, "ambient"),
    ("Co-trimoxazole 960mg Tablets",        "Antibiotics",            "box",     5,  100, "ambient"),
    ("Nitrofurantoin 100mg Capsules",       "Antibiotics",            "box",     7,   60, "ambient"),

    # Analgesics
    ("Paracetamol 500mg Tablets",           "Analgesics",             "box",     3,  500, "ambient"),
    ("Ibuprofen 400mg Tablets",             "Analgesics",             "box",     3,  400, "ambient"),
    ("Aspirin 75mg Tablets",                "Analgesics",             "box",     5,  300, "ambient"),
    ("Diclofenac 50mg Tablets",             "Analgesics",             "box",     5,  200, "ambient"),
    ("Tramadol 50mg Capsules",              "Analgesics",             "box",     7,  100, "ambient"),
    ("Naproxen 250mg Tablets",              "Analgesics",             "box",     5,  150, "ambient"),
    ("Mefenamic Acid 500mg Capsules",       "Analgesics",             "box",     5,  120, "ambient"),
    ("Celecoxib 200mg Capsules",            "Analgesics",             "box",     7,   80, "ambient"),

    # Cardiovascular
    ("Atenolol 50mg Tablets",               "Cardiovascular",         "box",    10,  150, "ambient"),
    ("Amlodipine 5mg Tablets",              "Cardiovascular",         "box",    10,  200, "ambient"),
    ("Lisinopril 10mg Tablets",             "Cardiovascular",         "box",    10,  180, "ambient"),
    ("Simvastatin 20mg Tablets",            "Cardiovascular",         "box",    10,  160, "ambient"),
    ("Atorvastatin 10mg Tablets",           "Cardiovascular",         "box",    10,  140, "ambient"),
    ("Warfarin 5mg Tablets",                "Cardiovascular",         "box",    14,   80, "ambient"),
    ("Clopidogrel 75mg Tablets",            "Cardiovascular",         "box",    10,  100, "ambient"),
    ("Furosemide 40mg Tablets",             "Cardiovascular",         "box",     7,  120, "ambient"),
    ("Carvedilol 25mg Tablets",             "Cardiovascular",         "box",    10,   70, "ambient"),
    ("Bisoprolol 5mg Tablets",              "Cardiovascular",         "box",    10,   90, "ambient"),

    # Diabetic Care
    ("Metformin 500mg Tablets",             "Diabetic Care",          "box",    10,  300, "ambient"),
    ("Glibenclamide 5mg Tablets",           "Diabetic Care",          "box",    10,  200, "ambient"),
    ("Glimepiride 2mg Tablets",             "Diabetic Care",          "box",    10,  150, "ambient"),
    ("Sitagliptin 100mg Tablets",           "Diabetic Care",          "box",    14,   80, "ambient"),
    ("Insulin Regular 100IU/mL Vial",       "Diabetic Care",          "vial",    5,  500, "cold_chain"),
    ("Insulin NPH 100IU/mL Vial",           "Diabetic Care",          "vial",    5,  400, "cold_chain"),
    ("Insulin Glargine 300IU/mL",           "Diabetic Care",          "vial",    5,  300, "cold_chain"),
    ("Insulin Lispro 100IU/mL",             "Diabetic Care",          "vial",    5,  250, "cold_chain"),

    # Cold Chain / Vaccines
    ("BCG Vaccine 20-dose Vial",            "Vaccines",               "vial",   14,  200, "cold_chain"),
    ("OPV Oral Polio 20-dose Vial",         "Vaccines",               "vial",   14,  250, "cold_chain"),
    ("Measles-Rubella Vaccine Vial",        "Vaccines",               "vial",   14,  300, "cold_chain"),
    ("Hepatitis B Vaccine 10-dose",         "Vaccines",               "vial",   14,  200, "cold_chain"),
    ("DPT Vaccine 10-dose Vial",            "Vaccines",               "vial",   14,  180, "cold_chain"),
    ("COVID-19 mRNA Vaccine Vial",          "Vaccines",               "vial",    7,  500, "cold_chain"),
    ("Influenza Vaccine 0.5mL Vial",        "Vaccines",               "vial",   14,  200, "cold_chain"),
    ("Tetanus Toxoid 10-dose Vial",         "Vaccines",               "vial",   14,  150, "cold_chain"),

    # Medical Consumables
    ("Surgical Gloves M 100pcs",            "Medical Consumables",    "box",     3,  500, "ambient"),
    ("Surgical Gloves L 100pcs",            "Medical Consumables",    "box",     3,  400, "ambient"),
    ("Disposable Syringes 5mL 100pcs",      "Medical Consumables",    "box",     5,  600, "ambient"),
    ("Disposable Syringes 1mL 100pcs",      "Medical Consumables",    "box",     5,  500, "ambient"),
    ("IV Cannula 18G 50pcs",                "Medical Consumables",    "box",     5,  300, "ambient"),
    ("IV Cannula 22G 50pcs",                "Medical Consumables",    "box",     5,  400, "ambient"),
    ("Surgical Mask N95 20pcs",             "Medical Consumables",    "box",     5,  300, "ambient"),
    ("IV Normal Saline 1L Bag",             "Medical Consumables",    "bag",     5,  600, "ambient"),
    ("IV Ringer's Lactate 1L Bag",          "Medical Consumables",    "bag",     5,  400, "ambient"),
    ("Sterile Gauze 10x10cm",               "Medical Consumables",    "pack",    3,  400, "ambient"),

    # Vitamins & Supplements
    ("Vitamin C 500mg Tablets",             "Vitamins",               "bottle", 10,  300, "ambient"),
    ("Vitamin D3 1000IU Capsules",          "Vitamins",               "bottle", 10,  250, "ambient"),
    ("Zinc Sulfate 20mg Tablets",           "Vitamins",               "box",     7,  200, "ambient"),
    ("Folic Acid 5mg Tablets",              "Vitamins",               "box",     7,  300, "ambient"),
    ("Ferrous Sulfate 200mg Tablets",       "Vitamins",               "box",     7,  350, "ambient"),
    ("Calcium Carbonate 500mg Tablets",     "Vitamins",               "bottle", 10,  200, "ambient"),
    ("Vitamin B12 1mg Tablets",             "Vitamins",               "box",    10,  180, "ambient"),

    # Antihypertensives
    ("Losartan 50mg Tablets",               "Antihypertensives",      "box",    10,  200, "ambient"),
    ("Valsartan 80mg Tablets",              "Antihypertensives",      "box",    10,  150, "ambient"),
    ("Ramipril 5mg Capsules",               "Antihypertensives",      "box",    10,  140, "ambient"),
    ("Hydrochlorothiazide 25mg Tablets",    "Antihypertensives",      "box",    10,  120, "ambient"),
    ("Spironolactone 25mg Tablets",         "Antihypertensives",      "box",    14,   80, "ambient"),

    # Gastrointestinal
    ("Omeprazole 20mg Capsules",            "Gastrointestinal",       "box",     7,  300, "ambient"),
    ("Pantoprazole 40mg Tablets",           "Gastrointestinal",       "box",     7,  250, "ambient"),
    ("Metoclopramide 10mg Tablets",         "Gastrointestinal",       "box",     5,  150, "ambient"),
    ("Oral Rehydration Salts Sachet",       "Gastrointestinal",       "pack",    3,  500, "ambient"),
    ("Lactulose Solution Sachet",           "Gastrointestinal",       "pack",    5,  200, "ambient"),
    ("Ondansetron 4mg Tablets",             "Gastrointestinal",       "box",     5,  180, "ambient"),

    # Respiratory
    ("Salbutamol 100mcg Inhaler",           "Respiratory",            "inhaler",10,  200, "ambient"),
    ("Beclomethasone 50mcg Inhaler",        "Respiratory",            "inhaler",14,  150, "ambient"),
    ("Cetirizine 10mg Tablets",             "Respiratory",            "box",     5,  300, "ambient"),
    ("Loratadine 10mg Tablets",             "Respiratory",            "box",     5,  250, "ambient"),
    ("Prednisolone 5mg Tablets",            "Respiratory",            "box",     7,  150, "ambient"),
    ("Montelukast 10mg Tablets",            "Respiratory",            "box",     7,  100, "ambient"),
    ("Ipratropium Bromide Inhaler",         "Respiratory",            "inhaler",10,   80, "ambient"),
]

LOCATION_CONFIGS = [
    {"name": "Central Pharma Warehouse – North",     "type": "central_warehouse", "region": "Delhi NCR"},
    {"name": "Central Pharma Warehouse – South",     "type": "central_warehouse", "region": "Bangalore"},
    {"name": "MediPlus Retail Pharmacy – Mumbai",    "type": "retail_pharmacy",   "region": "Mumbai"},
    {"name": "HealthMart Pharmacy – Chennai",         "type": "retail_pharmacy",   "region": "Chennai"},
    {"name": "CureCare Pharmacy – Hyderabad",        "type": "retail_pharmacy",   "region": "Hyderabad"},
    {"name": "PharmaHub – Kolkata",                  "type": "retail_pharmacy",   "region": "Kolkata"},
    {"name": "MediZone Pharmacy – Pune",             "type": "retail_pharmacy",   "region": "Pune"},
    {"name": "City General Hospital – Delhi",        "type": "hospital_client",   "region": "Delhi NCR"},
    {"name": "St. Thomas Multi-Specialty Hospital",  "type": "hospital_client",   "region": "Kerala"},
    {"name": "Apollo Clinic – Ahmedabad",            "type": "hospital_client",   "region": "Gujarat"},
]

# Extra catalog entries to reach 2000 total items
EXTRA_DRUG_POOL = {
    "Antibiotics":       ["Penicillin V", "Cephalexin", "Clarithromycin", "Linezolid", "Vancomycin",
                          "Gentamicin", "Streptomycin", "Flucloxacillin", "Levofloxacin", "Meropenem"],
    "Analgesics":        ["Morphine Sulfate", "Codeine Phosphate", "Piroxicam", "Ketorolac",
                          "Buprenorphine", "Tapentadol", "Paracetamol+Codeine"],
    "Cardiovascular":    ["Metoprolol", "Propranolol", "Diltiazem", "Verapamil",
                          "Ivabradine", "Digoxin", "Amiodarone"],
    "Diabetic Care":     ["Pioglitazone", "Empagliflozin", "Dapagliflozin",
                          "Liraglutide Injection", "Exenatide Injection"],
    "Medical Consumables": ["Urinary Catheter 14Fr", "Nasogastric Tube 12Fr", "Oxygen Mask Adult",
                            "Nebulizer Mask", "Wound Dressing 10x10cm", "Micropore Tape 2.5cm",
                            "Blood Collection Tubes", "IV Extension Set"],
    "Vitamins":          ["Magnesium Hydroxide 400mg", "Iron Sucrose Injection", "Vitamin B-Complex",
                          "Biotin 5mg", "Omega-3 Fish Oil"],
    "Gastrointestinal":  ["Esomeprazole 40mg", "Lansoprazole 30mg", "Domperidone 10mg",
                          "Loperamide 2mg", "Bismuth Subsalicylate"],
    "Respiratory":       ["Formoterol 12mcg Inhaler", "Tiotropium 18mcg Inhaler",
                          "Budesonide Inhaler", "Fluticasone Inhaler", "Aminophylline 100mg"],
    "Antihypertensives": ["Telmisartan 40mg", "Olmesartan 20mg", "Perindopril 4mg",
                          "Indapamide 1.5mg", "Labetalol 100mg"],
    "Vaccines":          ["Rotavirus Vaccine", "Pneumococcal Vaccine", "Varicella Vaccine",
                          "Meningococcal Vaccine", "Rabies Vaccine"],
}

DOSAGE_FORMS  = ["Tablets", "Capsules", "Injection", "Syrup", "Cream", "Drops"]
STRENGTHS     = ["5mg", "10mg", "25mg", "50mg", "100mg", "200mg", "250mg", "500mg"]
PACK_SIZES    = ["10 pcs", "30 pcs", "60 pcs", "100 pcs"]
UNITS         = ["box", "bottle", "vial", "pack", "roll", "inhaler"]


def _random_batch() -> str:
    prefix = random.choice(["BT", "LOT", "MFG", "PH", "RX"])
    year   = random.choice(["24", "25", "26"])
    num    = random.randint(1000, 9999)
    return f"{prefix}-{year}-{num}"


def _random_expiry(storage_temp: str) -> date:
    today = date.today()
    # ~10% near-expiry for realistic alert data
    if random.random() < 0.10:
        return today + timedelta(days=random.randint(7, 60))
    if storage_temp == "cold_chain":
        return today + timedelta(days=random.randint(180, 540))
    return today + timedelta(days=random.randint(365, 1460))


def generate_seed_data(db: SessionLocal):
    print("\n🏥  InvIQ Pharmacy Warehouse Seed")
    print("=" * 50)

    # ── Organization ─────────────────────────────────────────────────────
    org = db.query(Organization).filter_by(slug="pharma-wholesale").first()
    if not org:
        org = Organization(name="NovaMed Pharma Distributors", slug="pharma-wholesale")
        db.add(org)
        db.commit()
        db.refresh(org)
        print("✅  Organization: NovaMed Pharma Distributors")
    else:
        print("ℹ️   Organization already exists")

    # ── Locations ─────────────────────────────────────────────────────────
    if db.query(Location).count() == 0:
        locs = [
            Location(
                org_id=org.id,
                name=c["name"],
                type=c["type"],
                region=c["region"],
                address=f"{random.randint(1,200)} Main Street, {c['region']}",
            )
            for c in LOCATION_CONFIGS
        ]
        db.bulk_save_objects(locs)
        db.commit()
        print(f"✅  {len(locs)} locations")
    else:
        print(f"ℹ️   Locations already exist")

    # ── Items (2000 target) ────────────────────────────────────────────────
    if db.query(Item).count() == 0:
        items_data = []

        # Curated catalog first
        for (name, category, unit, lead, min_stock, temp) in PHARMA_PRODUCTS:
            items_data.append(dict(
                org_id=org.id, name=name, category=category, unit=unit,
                lead_time_days=lead, min_stock=min_stock, storage_temp=temp,
            ))

        # Fill up to 2000 with generated entries
        used_names = {r[0] for r in PHARMA_PRODUCTS}
        target = 2000 - len(PHARMA_PRODUCTS)
        categories = list(EXTRA_DRUG_POOL.keys())

        for _ in range(target):
            cat  = random.choice(categories)
            base = random.choice(EXTRA_DRUG_POOL[cat])
            form = random.choice(DOSAGE_FORMS)
            strength = random.choice(STRENGTHS)
            pack = random.choice(PACK_SIZES)
            name = f"{base} {strength} {form} ({pack})"
            if name in used_names:
                name += f" [{random.randint(1, 99)}]"
            used_names.add(name)

            is_cold = cat in ("Vaccines", "Diabetic Care") and "Injection" in form
            temp    = "cold_chain" if is_cold else "ambient"

            items_data.append(dict(
                org_id=org.id, name=name, category=cat,
                unit=random.choice(UNITS),
                lead_time_days=random.randint(3, 21),
                min_stock=random.randint(20, 300),
                storage_temp=temp,
            ))

        # Fast bulk insert via mappings (no ORM overhead per row)
        db.bulk_insert_mappings(Item, items_data)
        db.commit()

        cold_count = sum(1 for d in items_data if d["storage_temp"] == "cold_chain")
        print(f"✅  {len(items_data)} items  (🧊 cold-chain: {cold_count})")
    else:
        print(f"ℹ️   Items already exist")

    # ── Transactions (8000 target) ─────────────────────────────────────────
    if db.query(InventoryTransaction).count() == 0:
        all_items = db.query(Item).all()
        all_locs  = db.query(Location).all()
        start     = datetime.now() - timedelta(days=365)

        print(f"⏳  Generating 8000 transactions…")
        tx_data = []
        near_expiry_count = 0

        for _ in range(8000):
            loc  = random.choice(all_locs)
            item = random.choice(all_items)
            tx_date = (start + timedelta(days=random.randint(0, 365))).date()

            opening  = random.randint(50, 800)
            received = random.randint(0, 400)
            issued   = random.randint(0, min(300, opening + received))
            closing  = opening + received - issued

            # Only inbound deliveries (received > 0) carry batch / expiry data
            batch_number = None
            expiry_date  = None
            if received > 0:
                batch_number = _random_batch()
                expiry_date  = _random_expiry(item.storage_temp)
                if (expiry_date - date.today()).days <= 60:
                    near_expiry_count += 1

            tx_data.append(dict(
                location_id=loc.id,
                item_id=item.id,
                date=tx_date,
                opening_stock=opening,
                received=received,
                issued=issued,
                closing_stock=closing,
                notes=random.choice([
                    "Monthly replenishment",
                    "Emergency order",
                    "Outbound to client",
                    "Quarterly review",
                    None,
                ]),
                entered_by="seed_script",
                batch_number=batch_number,
                expiry_date=expiry_date,
            ))

        db.bulk_insert_mappings(InventoryTransaction, tx_data)
        db.commit()
        print(f"✅  {len(tx_data)} transactions  (⚠️ near-expiry batches: {near_expiry_count})")
    else:
        print(f"ℹ️   Transactions already exist")

    print("\n" + "=" * 50)
    print("🎉  Seeding complete!")
    print(f"    Locations   : {db.query(Location).count()}")
    print(f"    Items       : {db.query(Item).count()}")
    print(f"    Transactions: {db.query(InventoryTransaction).count()}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        generate_seed_data(db)
    finally:
        db.close()
