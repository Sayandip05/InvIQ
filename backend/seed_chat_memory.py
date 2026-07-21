"""
InvIQ Pharmacy Chat & Qdrant Memory Seed Script
=================================================
Seeds:
  1. Login User Accounts (Admin, Pharmacist/Manager, Staff) in Neon PostgreSQL
  2. Realistic Wholesale Pharmacy Chat Sessions & Messages in PostgreSQL (chat_sessions, chat_messages)
  3. Embedded Conversations in Qdrant Vector Memory Store (semantic recall test data)
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.connection import SessionLocal, engine, Base
from app.infrastructure.database.models import User, ChatSession, ChatMessage
from app.core.security import hash_password
from app.infrastructure.vector_store.vector_store import VectorMemory

# ── Sample Realistic Wholesale Pharmacy Conversations ─────────────────────────

SAMPLE_CONVERSATIONS = [
    {
        "session_id": "session-pharma-coldchain-01",
        "title": "Cold Chain & Vaccine Storage Protocol",
        "messages": [
            ("user", "What are the exact storage temperature requirements for Insulin Regular and BCG Vaccine?"),
            ("assistant", "Insulin Regular 100IU/mL Vial and BCG Vaccine are cold-chain items requiring refrigerated storage between +2°C and +8°C. They must never be frozen. Currently, Central Pharma Warehouse – North holds 500 vials of Insulin Regular in Refrigerator Unit #2."),
            ("user", "Which batch of Insulin Regular expires first?"),
            ("assistant", "Batch BT-25-4821 expires first on June 30, 2026. Under FIFO (First-In, First-Out) stock principles, all outbound dispatches to retail pharmacies and hospitals must issue batch BT-25-4821 before batch BT-25-9904."),
            ("user", "What is the total cold-chain inventory count across all locations?"),
            ("assistant", "We currently track 67 cold-chain items across 10 locations, with total active stock valued at approximately ₹14,50,000."),
        ],
    },
    {
        "session_id": "session-pharma-amox-02",
        "title": "Amoxicillin Lead Time & Stock Alert Analysis",
        "messages": [
            ("user", "What is the standard lead time and safety stock threshold for Amoxicillin 500mg Capsules?"),
            ("assistant", "Amoxicillin 500mg Capsules has a standard supplier lead time of 7 days and a minimum stock threshold of 200 boxes."),
            ("user", "Why did the last shipment from MedSource Global take 10 days instead of 7?"),
            ("assistant", "The shipment of 400 boxes of Amoxicillin 500mg experienced a 3-day port customs verification delay at Mumbai Port. The inventory repository logged notes on April 14 under PO-9938."),
            ("user", "Should we increase the reorder threshold for Amoxicillin?"),
            ("assistant", "Given the lead time variability (+3 days delay), raising min_stock from 200 to 280 boxes is recommended to maintain a safety buffer against unexpected stockouts."),
        ],
    },
    {
        "session_id": "session-pharma-recall-03",
        "title": "Batch QA Verification & Drug Recall Check",
        "messages": [
            ("user", "Has any batch of Ciprofloxacin 500mg Tablets failed QA inspection or been recalled?"),
            ("assistant", "No drug recalls or QA failures have been flagged for Ciprofloxacin 500mg Tablets. Batch LOT-25-1001 passed QA assay testing on April 12, 2026 with 99.8% purity."),
            ("user", "Where is batch LOT-25-1001 stored right now?"),
            ("assistant", "Batch LOT-25-1001 (180 boxes, expiry April 2028) is stored in Central Pharma Warehouse – South, Rack B, Shelf 4."),
        ],
    },
    {
        "session_id": "session-pharma-req-04",
        "title": "Hospital Requisition Approval REQ-20260409-001",
        "messages": [
            ("user", "What is the status of requisition REQ-20260409-001 from City General Hospital – Delhi?"),
            ("assistant", "Requisition REQ-20260409-001 requested 500 boxes of Paracetamol 500mg Tablets. It was APPROVED by Chief Pharmacist Dr. Rajesh Sharma on April 9, 2026 and dispatched via Dispatch Order #DO-8831."),
            ("user", "Who received the delivery at City General Hospital?"),
            ("assistant", "Delivery was signed for by Head Nurse Sunita Verma at City General Hospital – Delhi receiving bay on April 10 at 14:30 IST."),
        ],
    },
]


def seed_users_and_memory():
    print("\n🔐  InvIQ User & Qdrant Vector Memory Seed")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Seed Users in PostgreSQL
        users_to_create = [
            {
                "email": "admin@inviq.local",
                "username": "admin",
                "password": "admin123",
                "full_name": "System Administrator",
                "role": "admin",
            },
            {
                "email": "pharmacist@inviq.local",
                "username": "pharmacist",
                "password": "pharmacist123",
                "full_name": "Dr. Rajesh Sharma (Chief Pharmacist)",
                "role": "manager",
            },
            {
                "email": "staff@inviq.local",
                "username": "staff",
                "password": "staff123",
                "full_name": "Warehouse Staff",
                "role": "staff",
            },
        ]

        created_users = {}
        for u_info in users_to_create:
            user = db.query(User).filter(User.username == u_info["username"]).first()
            if not user:
                user = User(
                    email=u_info["email"],
                    username=u_info["username"],
                    hashed_password=hash_password(u_info["password"]),
                    full_name=u_info["full_name"],
                    role=u_info["role"],
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"✅  User created: {u_info['username']} ({u_info['role']}) -> {u_info['email']}")
            else:
                user.is_active = True
                user.is_verified = True
                user.hashed_password = hash_password(u_info["password"])
                db.commit()
                print(f"ℹ️   User updated: {u_info['username']} ({u_info['role']})")
            created_users[u_info["username"]] = user

        admin_user = created_users["admin"]

        # 2. Seed Chat Sessions & Messages in PostgreSQL
        print("\n💬  Seeding Chat Sessions & Messages into PostgreSQL...")
        for conv in SAMPLE_CONVERSATIONS:
            sid = conv["session_id"]
            session = db.query(ChatSession).filter(ChatSession.id == sid).first()
            if not session:
                session = ChatSession(
                    id=sid,
                    user_id=admin_user.id,
                    title=conv["title"],
                )
                db.add(session)
                db.commit()
            
            # Delete old messages to avoid duplicates
            db.query(ChatMessage).filter(ChatMessage.session_id == sid).delete()
            db.commit()

            base_time = datetime.now(timezone.utc) - timedelta(days=2)
            for i, (role, content) in enumerate(conv["messages"]):
                msg_time = base_time + timedelta(minutes=i*5)
                msg = ChatMessage(
                    session_id=sid,
                    role=role,
                    content=content,
                    created_at=msg_time,
                )
                db.add(msg)
            db.commit()
            print(f"✅  Chat Session: '{conv['title']}' ({len(conv['messages'])} messages)")

        # 3. Seed Conversations into Qdrant Vector Memory
        print("\n🧠  Indexing Conversations into Qdrant Vector DB...")
        vm = VectorMemory()
        if vm.is_available:
            indexed_count = 0
            for conv in SAMPLE_CONVERSATIONS:
                sid = conv["session_id"]
                base_time = datetime.now(timezone.utc) - timedelta(days=2)
                for i, (role, content) in enumerate(conv["messages"]):
                    msg_time = base_time + timedelta(minutes=i*5)
                    vm.add_message(
                        session_id=sid,
                        role=role,
                        content=content,
                        timestamp=msg_time,
                    )
                    indexed_count += 1
            print(f"✅  {indexed_count} chat messages embedded and indexed into Qdrant Vector Memory!")
        else:
            print("⚠️   VectorMemory is not available.")

        print("\n" + "=" * 60)
        print("🎉  Seeding complete!")
        print("🔑  Login Credentials:")
        print("    Admin      : email='admin@inviq.local'      username='admin'      password='admin123'")
        print("    Pharmacist : email='pharmacist@inviq.local' username='pharmacist' password='pharmacist123'")
        print("    Staff      : email='staff@inviq.local'      username='staff'      password='staff123'")
        print("=" * 60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed_users_and_memory()
