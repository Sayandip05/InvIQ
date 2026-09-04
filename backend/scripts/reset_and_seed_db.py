"""
Reset and Seed Database with Authentic Retail Chemist Inventory Data.
Configures 2 Admins:
- Admin 1: Single Pharmacy Owner (1 Retail Counter)
- Admin 2: Multi-Pharmacy Chain Owner (3 Branches including Cold Storage)
- Both can add more branches/locations dynamically later.
"""

import sys
import os
from datetime import date, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infrastructure.database.connection import SessionLocal, engine, Base
from app.infrastructure.database.models import (
    Organization,
    User,
    Location,
    Item,
    InventoryTransaction,
    Requisition,
    RequisitionItem,
    VendorUpload,
    VendorInvoice,
    AuditLog,
    ChatSession,
    ChatMessage,
    DataImportJob,
    ImportQuarantineRow,
)
from app.core.security import hash_password
from app.application.cache_service import cache_invalidate_pattern


from sqlalchemy import text


def reset_and_seed():
    print("🔄 Ensuring Database Schema and seeding fresh data...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    for model in [ImportQuarantineRow, DataImportJob, VendorInvoice, VendorUpload, RequisitionItem, Requisition, InventoryTransaction, Item, Location, ChatMessage, ChatSession, AuditLog, User, Organization]:
        try:
            db.query(model).delete()
        except Exception:
            pass
    db.commit()


    try:
        today = date.today()

        medicines_data = [
            # Gastro
            {"name": "Pan-D Capsule", "category": "Gastro", "unit": "strip", "barcode": "890108600101", "strength": "40mg+30mg", "mrp": 199.0, "purchase_rate": 140.0, "min_stock": 20, "lead_time": 2, "storage": "ambient"},
            {"name": "Pantocid 40mg Tablet", "category": "Gastro", "unit": "strip", "barcode": "890108600117", "strength": "40mg", "mrp": 162.0, "purchase_rate": 115.0, "min_stock": 15, "lead_time": 2, "storage": "ambient"},
            {"name": "Digene Antacid Gel 200ml", "category": "Gastro", "unit": "bottle", "barcode": "890108600122", "strength": "200ml Mint", "mrp": 155.0, "purchase_rate": 110.0, "min_stock": 10, "lead_time": 3, "storage": "ambient"},
            # Analgesic & Pain
            {"name": "Dolo 650mg Tablet", "category": "Analgesics", "unit": "strip", "barcode": "890108600102", "strength": "650mg", "mrp": 34.0, "purchase_rate": 22.0, "min_stock": 50, "lead_time": 1, "storage": "ambient"},
            {"name": "Combiflam Tablet", "category": "Analgesics", "unit": "strip", "barcode": "890108600120", "strength": "400mg+325mg", "mrp": 42.0, "purchase_rate": 28.0, "min_stock": 30, "lead_time": 2, "storage": "ambient"},
            {"name": "Volini Pain Relief Gel", "category": "Analgesics", "unit": "tube", "barcode": "890108600113", "strength": "50g", "mrp": 140.0, "purchase_rate": 98.0, "min_stock": 12, "lead_time": 2, "storage": "ambient"},
            # Antibiotics
            {"name": "Augmentin 625 Duo", "category": "Antibiotics", "unit": "strip", "barcode": "890108600103", "strength": "625mg", "mrp": 223.0, "purchase_rate": 160.0, "min_stock": 15, "lead_time": 2, "storage": "ambient"},
            {"name": "Azithral 500mg Tablet", "category": "Antibiotics", "unit": "strip", "barcode": "890108600104", "strength": "500mg", "mrp": 132.0, "purchase_rate": 92.0, "min_stock": 20, "lead_time": 2, "storage": "ambient"},
            {"name": "Ciplox 500mg Tablet", "category": "Antibiotics", "unit": "strip", "barcode": "890108600118", "strength": "500mg", "mrp": 45.0, "purchase_rate": 30.0, "min_stock": 15, "lead_time": 2, "storage": "ambient"},
            # Cardiac & Diabetes
            {"name": "Telma 40mg Tablet", "category": "Cardiac", "unit": "strip", "barcode": "890108600105", "strength": "40mg", "mrp": 245.0, "purchase_rate": 175.0, "min_stock": 25, "lead_time": 3, "storage": "ambient"},
            {"name": "Glycomet GP2 Tablet", "category": "Diabetes", "unit": "strip", "barcode": "890108600106", "strength": "500mg+2mg", "mrp": 189.0, "purchase_rate": 135.0, "min_stock": 20, "lead_time": 3, "storage": "ambient"},
            {"name": "Ecosprin 75 Tablet", "category": "Cardiac", "unit": "strip", "barcode": "890108600116", "strength": "75mg", "mrp": 6.0, "purchase_rate": 4.0, "min_stock": 40, "lead_time": 2, "storage": "ambient"},
            {"name": "Thyronorm 50mcg Tablet", "category": "Thyroid", "unit": "bottle", "barcode": "890108600112", "strength": "50mcg", "mrp": 160.0, "purchase_rate": 115.0, "min_stock": 15, "lead_time": 3, "storage": "ambient"},
            # Anti-Allergic & Respiratory
            {"name": "Montair LC Tablet", "category": "Respiratory", "unit": "strip", "barcode": "890108600107", "strength": "10mg+5mg", "mrp": 210.0, "purchase_rate": 150.0, "min_stock": 25, "lead_time": 2, "storage": "ambient"},
            {"name": "Allegra 120mg Tablet", "category": "Anti-Allergic", "unit": "strip", "barcode": "890108600119", "strength": "120mg", "mrp": 218.0, "purchase_rate": 155.0, "min_stock": 15, "lead_time": 2, "storage": "ambient"},
            {"name": "Ascoril LS Syrup 100ml", "category": "Respiratory", "unit": "bottle", "barcode": "890108600115", "strength": "100ml", "mrp": 118.0, "purchase_rate": 82.0, "min_stock": 15, "lead_time": 2, "storage": "ambient"},
            {"name": "Otrivin Nasal Spray", "category": "ENT", "unit": "bottle", "barcode": "890108600114", "strength": "10ml", "mrp": 98.0, "purchase_rate": 68.0, "min_stock": 10, "lead_time": 2, "storage": "ambient"},
            # Vitamins & Supplements
            {"name": "Shelcal 500mg Tablet", "category": "Vitamins", "unit": "bottle", "barcode": "890108600108", "strength": "500mg+D3", "mrp": 145.0, "purchase_rate": 100.0, "min_stock": 20, "lead_time": 3, "storage": "ambient"},
            {"name": "Becosules Z Capsule", "category": "Vitamins", "unit": "strip", "barcode": "890108600121", "strength": "Zinc+B-Complex", "mrp": 52.0, "purchase_rate": 35.0, "min_stock": 35, "lead_time": 2, "storage": "ambient"},
            {"name": "Liv 52 Syrup 200ml", "category": "Supplements", "unit": "bottle", "barcode": "890108600109", "strength": "200ml", "mrp": 170.0, "purchase_rate": 120.0, "min_stock": 15, "lead_time": 3, "storage": "ambient"},
            {"name": "Electral ORS Sachet 21.8g", "category": "Electrolytes", "unit": "sachet", "barcode": "890108600123", "strength": "21.8g", "mrp": 22.0, "purchase_rate": 15.0, "min_stock": 50, "lead_time": 1, "storage": "ambient"},
            # First Aid & Antiseptics
            {"name": "Betadine 10% Solution", "category": "First Aid", "unit": "bottle", "barcode": "890108600110", "strength": "100ml", "mrp": 125.0, "purchase_rate": 88.0, "min_stock": 12, "lead_time": 2, "storage": "ambient"},
            {"name": "Band-Aid Washproof 20s", "category": "First Aid", "unit": "box", "barcode": "890108600125", "strength": "20 Strips", "mrp": 60.0, "purchase_rate": 42.0, "min_stock": 15, "lead_time": 2, "storage": "ambient"},
            # Cold-Chain Biologicals
            {"name": "Insulin Lantus Solostar", "category": "Cold Chain", "unit": "pen", "barcode": "890108600111", "strength": "100IU/ml 3ml", "mrp": 680.0, "purchase_rate": 520.0, "min_stock": 8, "lead_time": 1, "storage": "cold_chain"},
            {"name": "Covaxin Vaccine Vial", "category": "Cold Chain", "unit": "vial", "barcode": "890108600124", "strength": "10 Doses", "mrp": 0.0, "purchase_rate": 0.0, "min_stock": 5, "lead_time": 1, "storage": "cold_chain"},
        ]

        # ─────────────────────────────────────────────────────────────────────
        # 1. SETUP ORGANIZATION 1: Single Pharmacy Store
        # ─────────────────────────────────────────────────────────────────────
        print("🏢 Setting up Org 1: Single Pharmacy Owner (Gupta Medicos)...")
        org_single = Organization(
            name="Gupta Medicos & Retail Chemist",
            slug="gupta-medicos",
            plan="single_pharmacy",
            is_active=True,
        )
        db.add(org_single)
        db.flush()

        loc_single = Location(
            org_id=org_single.id,
            name="Gupta Medicos - Main Counter",
            type="retail_counter",
            region="East",
            radius_meters=500,
            pincode="713216",
            phone="+91 98321 11001",
            address="Shop 4, City Center Market, Durgapur",
        )
        db.add(loc_single)
        db.flush()

        admin_single = User(
            org_id=org_single.id,
            email="single@inviq.local",
            username="admin_single",
            full_name="Rajesh Gupta (Single Chemist Owner)",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True,
            is_verified=True,
            location_ids=[loc_single.id],
        )
        staff_single = User(
            org_id=org_single.id,
            email="staff_single@inviq.local",
            username="staff_single",
            full_name="Amit Sen (Counter Staff)",
            hashed_password=hash_password("staff123"),
            role="staff",
            is_active=True,
            is_verified=True,
            location_ids=[loc_single.id],
        )
        db.add_all([admin_single, staff_single])
        db.flush()

        # Seed items for Single Pharmacy Org
        for med in medicines_data:
            item = Item(
                org_id=org_single.id,
                name=med["name"],
                category=med["category"],
                unit=med["unit"],
                barcode=med["barcode"],
                strength=med["strength"],
                mrp=med["mrp"],
                purchase_rate=med["purchase_rate"],
                min_stock=med["min_stock"],
                lead_time_days=med["lead_time"],
                storage_temp=med["storage"],
            )
            db.add(item)
            db.flush()

            # Seed transaction
            opening = 40
            received = 20
            issued = 18
            closing = opening + received - issued
            batch = f"BT-S1-{item.id:04d}"
            expiry = today + timedelta(days=365 + (int(item.id) * 20))

            tx = InventoryTransaction(
                location_id=loc_single.id,
                item_id=item.id,
                date=today,
                opening_stock=opening,
                received=received,
                issued=issued,
                closing_stock=closing,
                batch_number=batch,
                expiry_date=expiry,
                entered_by="system",
                notes="Initial single pharmacy counter stock",
            )
            db.add(tx)

        # ─────────────────────────────────────────────────────────────────────
        # 2. SETUP ORGANIZATION 2: Multi-Pharmacy Chain (3 Branches)
        # ─────────────────────────────────────────────────────────────────────
        print("🏢 Setting up Org 2: Multi-Pharmacy Chain Owner (Apollo Chemist Network)...")
        org_multi = Organization(
            name="Apollo Chemist & Pharmacy Network",
            slug="apollo-chemist",
            plan="multi_pharmacy",
            is_active=True,
        )
        db.add(org_multi)
        db.flush()

        loc1 = Location(
            org_id=org_multi.id,
            name="Apollo Pharmacy - Main Market (Branch 1)",
            type="retail_counter",
            region="East",
            radius_meters=500,
            pincode="713216",
            phone="+91 98321 00001",
            address="Shop 12, Main Market Plaza, Durgapur",
        )
        loc2 = Location(
            org_id=org_multi.id,
            name="Apollo Pharmacy - Station Road (Branch 2)",
            type="retail_counter",
            region="East",
            radius_meters=300,
            pincode="713212",
            phone="+91 98321 00002",
            address="24 Station Road, Junction Market, Durgapur",
        )
        loc3 = Location(
            org_id=org_multi.id,
            name="Apollo Pharmacy - Cold Storage & Depot (Branch 3)",
            type="cold_storage",
            region="East",
            radius_meters=50,
            pincode="713216",
            phone="+91 98321 00003",
            address="Dedicated Medical Fridge (2°C - 8°C), Central Depot",
        )
        db.add_all([loc1, loc2, loc3])
        db.flush()

        admin_multi = User(
            org_id=org_multi.id,
            email="admin@inviq.local",
            username="admin",
            full_name="Dr. S. K. Sharma (Chain Owner)",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True,
            is_verified=True,
            location_ids=[loc1.id, loc2.id, loc3.id],
        )
        vendor_user = User(
            org_id=org_multi.id,
            email="vendor@inviq.local",
            username="vendor",
            full_name="Shree Pharma Distributors",
            hashed_password=hash_password("vendor123"),
            role="vendor",
            is_active=True,
            is_verified=True,
            location_ids=[loc1.id, loc2.id, loc3.id],
        )
        staff1 = User(
            org_id=org_multi.id,
            email="staff@inviq.local",
            username="staff",
            full_name="Ramesh Kumar (Branch 1 Staff)",
            hashed_password=hash_password("staff123"),
            role="staff",
            is_active=True,
            is_verified=True,
            location_ids=[loc1.id],
        )
        staff2 = User(
            org_id=org_multi.id,
            email="staff2@inviq.local",
            username="staff2",
            full_name="Pooja Verma (Branch 2 Staff)",
            hashed_password=hash_password("staff2123"),
            role="staff",
            is_active=True,
            is_verified=True,
            location_ids=[loc2.id],
        )
        db.add_all([admin_multi, vendor_user, staff1, staff2])
        db.flush()

        # Seed items for Multi-Pharmacy Org
        for med in medicines_data:
            item = Item(
                org_id=org_multi.id,
                name=med["name"],
                category=med["category"],
                unit=med["unit"],
                barcode=med["barcode"],
                strength=med["strength"],
                mrp=med["mrp"],
                purchase_rate=med["purchase_rate"],
                min_stock=med["min_stock"],
                lead_time_days=med["lead_time"],
                storage_temp=med["storage"],
            )
            db.add(item)
            db.flush()

            for loc in [loc1, loc2, loc3]:
                if item.storage_temp == "cold_chain" and loc.id != loc3.id:
                    opening, received, issued = 3, 5, 4
                elif item.storage_temp == "cold_chain" and loc.id == loc3.id:
                    opening, received, issued = 20, 30, 12
                elif item.storage_temp != "cold_chain" and loc.id == loc3.id:
                    continue
                else:
                    if med["barcode"] in ["890108600101", "890108600102"]:
                        opening = 60 if loc.id == loc1.id else 35
                        received = 40 if loc.id == loc1.id else 25
                        issued = 52 if loc.id == loc1.id else 30
                    elif med["barcode"] == "890108600118":  # Low stock
                        opening, received, issued = 10, 0, 7
                    else:
                        opening, received, issued = 30, 20, 15

                closing = opening + received - issued

                # Batch & expiry
                if med["barcode"] == "890108600103":  # 45 days (FEFO Alert)
                    expiry = today + timedelta(days=45)
                    batch = "BT-AUG-248"
                elif med["barcode"] == "890108600119":  # 25 days (FEFO Critical)
                    expiry = today + timedelta(days=25)
                    batch = "BT-ALG-019"
                elif med["barcode"] == "890108600111":  # 60 days
                    expiry = today + timedelta(days=60)
                    batch = "BT-INS-981"
                else:
                    expiry = today + timedelta(days=365 + (int(item.id) * 30))
                    batch = f"BT-26-{item.id:04d}"

                tx = InventoryTransaction(
                    location_id=loc.id,
                    item_id=item.id,
                    date=today,
                    opening_stock=opening,
                    received=received,
                    issued=issued,
                    closing_stock=closing,
                    batch_number=batch,
                    expiry_date=expiry,
                    entered_by="system",
                    notes="Multi-branch inventory sync",
                )
                db.add(tx)

        db.commit()
        print("✅ Database cleanly reset with 2 Admins (Single Pharmacy & 3-Pharmacy Chain)!")

        # Invalidate Redis cache
        print("🧹 Flushing Redis analytics & lookup cache...")
        try:
            cache_invalidate_pattern("*")
            print("🚀 Redis cache flushed!")
        except Exception as err:
            print(f"⚠️ Redis cache clear warning (non-fatal): {err}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during reset & seed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    reset_and_seed()
