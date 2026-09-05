# 🏥 InvIQ - AI-Powered Retail Chemist & Multi-Pharmacy Inventory Operating System

**Smart AI inventory, FEFO expiry loss prevention, barcode quick-dispensing, and distributor Excel synchronization for retail medical stores and pharmacy chains.**

---

## 🎯 Problem It Solves

Independent retail medical stores and local pharmacy chains in Tier-2/3 cities lose significant revenue every month due to **expired medications (FEFO loss)**, missed customer sales from sudden stockouts, and manual paper-heavy distributor bills. **InvIQ provides a simple, ultra-fast, mobile-friendly platform tailored specifically for chemist shop owners:**

1. **Zero Expiry Loss (FEFO)**: Real-time alerts at 30, 60, and 90 days before batch expiration so chemists can return stock to distributors on time.
2. **Instant Barcode Quick Dispense**: Connected USB/Bluetooth barcode scanner and camera dispense endpoint that removes sold items one-by-one with millisecond consistency.
3. **1-Click Distributor Bill Ingest**: Upload wholesaler Excel/CSV delivery manifests to auto-increment live stock in seconds.
4. **Single & Multi-Shop Chains**: Centralized dashboard to track stock across 1 to 10+ shop counters from a phone or tablet.

---

## 🛠️ Tech Stack

### Backend & Cloud Infrastructure
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)
![GraphQL](https://img.shields.io/badge/GraphQL-Strawberry-E10098?logo=graphql&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?logo=supabase&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Upstash-DC382D?logo=redis&logoColor=white)
![Azure](https://img.shields.io/badge/Azure-App_Service_%26_Blob_Storage-0078D4?logo=microsoftazure&logoColor=white)
![Alembic](https://img.shields.io/badge/Database-Alembic_Migrations-CC292B?logo=alembic&logoColor=white)

### Frontend
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)

### AI & Barcode Infrastructure
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-FF6B00?logo=ai&logoColor=white)
![Sarvam AI](https://img.shields.io/badge/Sarvam_AI-Saaras_v3_STT-7C3AED?logo=google&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-Cloud_Vector_DB-DC2626?logo=database&logoColor=white)

---

## ✨ Key Capabilities

- ⚡ **Ultra-Fast Barcode Scanner Dispensing** - Instant 1-by-1 stock deduction on counter scan with zero latency and PostgreSQL transaction advisory locking.
- 💊 **Unit of Measure (UOM) Granularity & Multi-Packaging** - Atomic smallest-unit ledger (`tablet`, `ml`, `vial`) with multi-tier packaging conversions (`strip`, `box`, `case`), single-dose 1-tablet strip handling, and hierarchical stock decomposition visualizers.
- 🛒 **Counter Billing Cart & Flexible Customer Discounts** - High-speed barcode retail billing session with live discount previews (`none`, `flat`, `tiered` slabs), receipt generation, instant stock locking, and zero-drift void cancellation.
- 📈 **Real-Time Monthly Sales & Gross Margin KPIs** - Sub-millisecond sales, discounts, revenue, and gross profit analytics backed by Redis pipeline caching and Celery background workers.
- 📦 **FEFO Expiry Loss Shield** - Proactive batch alerts at 30, 60, and 90 days ensuring no expired medicine remains on shelves.
- 🚚 **Supplier & Distributor Management** - Direct vendor portal with 1-click Excel delivery manifest ingestion and automated PDF invoices stored in Azure Blob Storage.
- 🤖 **AI Chemist Assistant** - Ask questions in plain English or Hindi: *"What medicines are running low in Counter 1?"*
- 📊 **Real-Time Clean Analytics** - Live stock count, critical shortages, cold-chain fridge monitor, and store-by-store breakdowns.
- 🔐 **Enterprise Multi-Tenant Security** - Strict non-nullable `org_id` schema, HttpOnly SameSite auth cookies, CSP headers, issued-at (`iat`) token invalidation, cryptographic Google OAuth ID-token verification, and tenant-scoped Redis pub/sub.
- ☁️ **Dual Environment Architecture** - Strictly separated `DEVELOPMENT` (local dev & rapid testing) and `PRODUCTION` (containerized Azure App Service / Cloud with Alembic migrations).
- ✅ **Production Test Suite** - Comprehensive 342+ test cases covering unit conversions, billing lifecycles, RBAC, multi-tenancy, and FEFO dispensing with 100% pass rate.

---

## 🚀 Quick Setup & Environments

InvIQ has exactly **TWO environments**:
1. **DEVELOPMENT** — Local machine development and manual testing.
2. **PRODUCTION** — Deployed cloud environment (Azure App Service + Azure Blob Storage + Supabase Postgres + Upstash Redis).

### 1. Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/Sayandip05/InvIQ.git
cd InvIQ

# 2. Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure local environment
cp .env.example .env
# Ensure ENVIRONMENT=development in your .env

# 4. Run database migrations (or let dev server auto-create)
./venv/bin/alembic -c backend/alembic.ini upgrade head

# 5. Start Backend development server
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Development Setup

```bash
# In a new terminal
cd frontend
npm install
npm run dev
# Frontend runs at http://localhost:5173
```

### 3. Production Deployment (Azure App Service / Docker)

The project uses a unified multi-stage `Dockerfile`. In production (`ENVIRONMENT=production`), the container automatically applies Alembic migrations on boot before starting Gunicorn workers:

```bash
# Run via Docker Compose (or deploy Docker image to Azure App Service)
docker compose up -d --build
```

---

## 🏗️ Future-Proof System Architecture

### 1. Full-Stack & Cloud Infrastructure Architecture

```mermaid
graph TB
    subgraph ClientLayer["🖥️ Chemist & Counter Client Layer (React 19 SPA)"]
        Landing["🌐 Landing Page (Single & Multi-Pharmacy Tiers)"]
        AuthApp["🔐 Auth & Tenant Portal (Argon2id + JWT + HttpOnly Cookies)"]
        AdminPort["🛡️ Chemist Admin Dashboard & Organization Settings"]
        StaffPort["💊 Counter Staff Portal (Permitted Branch Scoped)"]
        BarcodeGun["🔫 Counter Barcode Scanner (USB / Bluetooth / Camera)"]
        VendorPort["🚚 Wholesaler / Distributor Delivery Portal"]
    end

    subgraph APIGateway["🚪 API Gateway & Security Layer (FastAPI)"]
        CORS["CORS & Trusted Hosts Security"]
        SecHeaders["🛡️ Security Headers & Strict CSP Middleware"]
        Limiter["⚡ SlowAPI Rate Limiter (Upstash Redis TLS 6379)"]
        AuthMid["🔑 JWT Token & Role Authorization Guard"]
        TenantGuard["🏢 Multi-Tenant Context Resolver (org_id Scoping)"]
        REST["REST API Engine (60+ Scoped Endpoints)"]
        ScanAPI["⚡ Quick-Dispense Engine (/api/inventory/scan-dispense)"]
        GQL["GraphQL Subgraph (/graphql/analytics)"]
        WS["WebSocket Alerts Engine (/ws/alerts)"]
    end

    subgraph BusinessLayer["⚙️ Domain & Application Services"]
        InvSvc["InventoryService & Barcode Dispenser<br/>• Batch-Aware FEFO Deductions<br/>• Redis Distributed Lock (SETNX)"]
        AnalyticsSvc["AnalyticsService & FEFO Shield<br/>• 30/60/90 Day Expiry Calculations<br/>• Tenant-Scoped Cache Keys"]
        ReqSvc["RequisitionService<br/>• Chemist Purchase Orders<br/>• Draft → Approved → Fulfilled Lifecycle"]
        VendorSvc["VendorService<br/>• Excel Delivery Manifest Sync<br/>• PDF Invoices in Azure Blob"]
        ImportSvc["DataImportService<br/>• 2-Pass Synonym Heuristic/AI Mapping<br/>• Quarantine Error Inspection"]
        PdfSvc["InvoicePdfService & ReportService<br/>• ReportLab Vector PDF Engine"]
        NotifySvc["NotificationService<br/>• SMTP Background Mailer<br/>• Tenant-Scoped Low Stock Alerts"]
        CacheSvc["CacheService<br/>• L1 Memory + L2 Upstash REST<br/>• Tenant Pattern Invalidation"]
        AgentSvc["AgentService & ReAct Chatbot<br/>• LangGraph AI Architecture<br/>• Multilingual Voice STT (Sarvam)"]
    end

    subgraph AsyncWorkers["⚡ Asynchronous Processing & Background Workers"]
        CeleryApp["Celery Worker Engine (Redis Broker)"]
        TaskImport["📄 CSV/Excel Import Task"]
        TaskInvoice["🧾 PDF Invoice Generation Task"]
        TaskVector["🧠 Vector Embeddings Sync Task"]
        TaskEmail["📧 Transactional Email Task"]
        CeleryBeat["⏰ Celery Beat Periodic Jobs<br/>• FEFO Expiry Audits (6h)<br/>• Stock Threshold Audits (1h)<br/>• Cold-Chain Monitoring (30m)"]
    end

    subgraph DataStorage["💾 Persistence & Cloud Infrastructure"]
        PG[("⚡ PostgreSQL / Supabase<br/>Strict org_id Row Isolation<br/>B-Tree & Composite Indexes")]
        Redis[("⚡ Upstash Redis<br/>• Distributed Lock (Redlock)<br/>• Token Blacklist & WS Tickets<br/>• Org Pub/Sub: inviq:events:org:{id}")]
        Qdrant[("🧠 Qdrant Cloud Vector DB<br/>Gemini 768-dim Embeddings<br/>Tenant Payload Filtering")]
        Azure[("☁️ Azure Blob Storage<br/>Invoices, Reports & Manifests")]
        Groq["⚡ Groq Cloud (LLaMA 3.3 70B)"]
        Sarvam["🎙️ Sarvam AI (Saaras v3 STT)"]
    end

    %% Client Connections
    Landing --> CORS
    AuthApp --> CORS
    AdminPort --> CORS
    StaffPort --> CORS
    BarcodeGun --> ScanAPI
    VendorPort --> CORS
    CORS --> SecHeaders --> Limiter --> AuthMid --> TenantGuard
    TenantGuard --> REST
    TenantGuard --> ScanAPI
    TenantGuard --> GQL
    TenantGuard --> WS

    %% Gateway to Business Services
    ScanAPI --> InvSvc
    REST --> InvSvc
    REST --> AnalyticsSvc
    REST --> ReqSvc
    REST --> VendorSvc
    REST --> ImportSvc
    REST --> AgentSvc
    GQL --> AnalyticsSvc
    WS --> InvSvc

    %% Services to Async Workers
    ImportSvc -.-> TaskImport -.-> CeleryApp
    VendorSvc -.-> TaskInvoice -.-> CeleryApp
    AgentSvc -.-> TaskVector -.-> CeleryApp
    NotifySvc -.-> TaskEmail -.-> CeleryApp
    CeleryBeat --> CeleryApp

    %% Services to Data Storage
    InvSvc --> PG
    InvSvc --> Redis
    InvSvc --> CacheSvc
    ReqSvc --> PG
    VendorSvc --> PG
    VendorSvc --> PdfSvc
    VendorSvc --> Azure
    AnalyticsSvc --> PG
    AnalyticsSvc --> CacheSvc
    CacheSvc --> Redis
    ImportSvc --> Groq
    ImportSvc --> PG
    AgentSvc --> Groq
    AgentSvc --> Qdrant
    AgentSvc --> Sarvam
    NotifySvc --> PG
```

---

### 2. Retail Chemist & Distributor Supply Chain Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Customer as 👤 Customer
    actor Chemist as 💊 Chemist Counter
    participant App as 💻 InvIQ Counter App
    participant API as ⚡ FastAPI Backend
    participant Lock as 🔒 Redis Distributed Lock
    participant DB as 🐘 PostgreSQL DB
    participant WS as 📡 WebSocket (Redis Pub/Sub)
    actor Supplier as 🚚 Medicine Wholesaler

    Note over Chemist,DB: 1. Counter Dispensing & Atomic FEFO Deduction
    Customer->>Chemist: Requests Medicine (e.g. Pan-D)
    Chemist->>App: Scans Barcode (8901086001234)
    App->>API: POST /api/inventory/scan-dispense
    API->>Lock: Acquire Lock (lock:org_1:stock:loc_1:item_5)
    API->>DB: Query Batches Ordered by Expiry Date (FEFO)
    API->>DB: Atomic Update: issued += 1 on Earliest Batch
    API->>Lock: Release Distributed Lock
    DB-->>API: Stock Count Updated (e.g. 42 remaining)
    API-->>App: 200 OK (Beep Success Sound + Remaining Stock)
    
    opt Stock Below Minimum Threshold (< 15)
        API->>WS: Broadcast to Channel inviq:events:org:1
        WS-->>Chemist: Real-Time Audio & Visual Alert Triggered
    end

    Note over Chemist,Supplier: 2. Purchase Order & Wholesaler Delivery
    Chemist->>App: Creates Stock Requisition for Low Items
    App->>API: POST /api/requisition/create
    API->>Supplier: Email / In-App Notification Sent
    Supplier->>App: Logs into /vendor portal & uploads Excel Delivery Manifest
    App->>API: POST /api/vendor/upload-delivery
    API->>DB: Atomic Bulk Insert: received += Qty
    API->>DB: Auto-Generate Formal PDF Invoice
    API-->>Supplier: Delivery Manifest Successfully Processed
    API-->>Chemist: Live Counter Stock Instantly Replenished
```

---

### 3. High-Speed Barcode Quick-Dispense Engine

```mermaid
flowchart TD
    Scan["🔫 Barcode Gun Keystroke / Mobile Camera Scan"] --> Input["📱 InvIQ Counter Listener (Sub-50ms Capture)"]
    Input --> Request["🚀 POST /api/inventory/scan-dispense<br/>{ barcode_or_id: '8901086...', location_id: 1, qty: 1 }"]
    
    Request --> Auth["🛡️ Scoped Tenant & Branch Authorization"]
    Auth --> Lock["🔒 Redis Distributed Lock: lock:org_{id}:stock:{loc}:{item}"]
    Lock --> Lookup["🔍 O(1) Index Lookup on Item.barcode"]
    
    Lookup --> Check{"Is Item Valid & In Stock?"}
    Check -- No --> Error["❌ Error 400: Out of Stock / Unrecognized Barcode"]
    
    Check -- Yes --> FEFO["🛡️ Batch Aggregation: FEFO Ordering (expiry_date ASC)"]
    FEFO --> Atomic["⚡ Atomic Ledger Transaction: closing = opening + received - issued"]
    
    Atomic --> Cache["🧹 Invalidate Tenant Cache (cache:{org_id}:*)"]
    Cache --> Threshold{"Stock < min_stock?"}
    
    Threshold -- Yes --> Alert["🚨 Publish Domain Event: stock.low to inviq:events:org:{id}"]
    Threshold -- No --> Resp["✅ Return JSON { remaining_stock, status: 'HEALTHY' }"]
    Alert --> Resp
    
    Resp --> Unlock["🔓 Release Distributed Lock"]
    Unlock --> Audio["🔊 Trigger Instant Counter Audio Beep & Flash Badge (<15ms)"]
```

---

## 👥 Role-Based Access Control (RBAC) & User Journeys

```mermaid
graph LR
    subgraph Roles["👤 User Roles & Scopes"]
        Admin["🛡️ Chemist Store Owner<br/>(Org Admin)"]
        Manager["📋 Branch Manager<br/>(Store Operations)"]
        Staff["💊 Counter Pharmacist<br/>(POS & Dispense)"]
        Vendor["🚚 Wholesaler / Distributor<br/>(Delivery Vendor)"]
    end

    subgraph Capabilities["⚡ Scoped Capabilities"]
        StoreMgmt["💊 Pharmacy Profile & Branch Setup<br/>Supplier Management & Master Data<br/>FEFO Expiry Alerts & Reports<br/>Requisition Approvals"]
        StaffOps["⚡ 1-Click Barcode Dispense<br/>Counter Stock Intake & Transactions<br/>Create Purchase Requisitions"]
        VendorOps["📄 Excel Delivery Manifest Upload<br/>Auto Invoice PDF Generation<br/>Download Delivery Receipts"]
    end

    Admin --> StoreMgmt
    Manager --> StoreMgmt
    Staff --> StaffOps
    Vendor --> VendorOps
```




---


---

## 🔷 GraphQL Analytics API

InvIQ uses a **REST + GraphQL hybrid** — the industry-standard pattern. REST handles all mutations (create/update/delete). GraphQL handles analytics reads with zero over-fetching.

**Endpoint:** `POST /graphql/analytics`  
**Playground (dev):** `GET /graphql/analytics`

### Available Queries

```graphql
# Dashboard chart data
{ dashboardStats {
    categoryDistribution { name value }
    lowStockItems { name stock minStock shortage }
    statusDistribution { name value color }
} }

# Full heatmap grid
{ heatmap { locations items matrix
    details { itemName currentStock healthStatus }
} }

# Stock alerts with filter
{ alerts(severity: "CRITICAL") {
    count alerts { itemName currentStock recommendedReorder }
} }

# Aggregate summary
{ summary {
    healthSummary { critical warning healthy }
    categories { name total critical }
} }

# Flexible ad-hoc query with server-side filters
{ stockHealth(location: "Warehouse", statusFilter: "CRITICAL") {
    itemName currentStock avgDailyUsage daysRemaining
} }
```

### Role-Aware Field Masking

| Caller | `avgDailyUsage` | `daysRemaining` | `leadTimeDays` |
|--------|:---:|:---:|:---:|
| Guest / Vendor | `null` | `null` | `null` |
| Manager / Admin | ✅ | ✅ | ✅ |

---

## 📚 Documentation

For detailed documentation, see the `/docs` folder:

- **[High-Level Design (HLD)](docs/HLD.md)** - System overview, architecture, tech stack decisions
- **[API Reference](docs/api.md)** - REST + GraphQL endpoint reference

---

## 🧪 Testing & Quality Assurance

```bash
# Run all automated tests (344 test cases across Unit, Integration, API, E2E)
./venv/bin/pytest backend/tests/ -v

# Run by testing category
./venv/bin/pytest backend/tests/unit/ -v          # Unit Tests
./venv/bin/pytest backend/tests/integration/ -v   # Integration & Multi-tenant Tests
./venv/bin/pytest backend/tests/api/ -v           # REST & GraphQL API Tests
./venv/bin/pytest backend/tests/e2e/ -v           # End-to-End Workflow Tests

# Run with coverage report
./venv/bin/pytest backend/tests/ --cov=app --cov-report=term-missing
```

---

## ⚡ Performance Benchmarks

The benchmark suite is located in `backend/tests/benchmark/`:

```bash
# 1. Run concurrency and throughput latency benchmark
cd backend
../venv/bin/python tests/benchmark/run_latency_benchmark.py

# 2. Run Locust load testing suite
../venv/bin/locust -f tests/benchmark/locustfile.py --headless -u 100 -r 10 --run-time 1m --host http://localhost:8000
```

---

## 📦 Project Structure

```
InvIQ/
├── backend/
│   ├── alembic/                  # Version-controlled database migrations
│   ├── alembic.ini               # Portable migration configuration
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/           # REST routes (auth, inventory, vendor, requisition, admin…)
│   │   │   ├── schemas/          # Pydantic validation schemas with password complexity
│   │   │   └── graphql/          # Strawberry GraphQL (resolvers, schema, role masking)
│   │   ├── application/          # Domain services (inventory, vendor, data import, analytics…)
│   │   ├── core/                 # Config, security (Argon2id, JWT, Google OAuth), middleware
│   │   ├── infrastructure/       # Database models/repos, Upstash Redis, Azure Blob Storage, Qdrant
│   │   └── workers/              # Celery background task processing & Celery Beat
│   ├── scripts/                  # Database migration fixtures and demo seeding utilities
│   └── tests/                    # 344 automated test cases & benchmark suite
│       ├── unit/                 # Domain, service, exception, security unit tests
│       ├── integration/          # Multi-tenant isolation, UoM, import, event pipeline
│       ├── api/                  # REST, GraphQL, WebSocket, Billing endpoints
│       ├── e2e/                  # Daily operations, onboarding, master data workflows
│       └── benchmark/            # Concurrency benchmarks, Locust load tests, latency profiling
├── frontend/
│   ├── src/
│   │   ├── components/           # Reusable React components & Tailwind styles
│   │   ├── pages/                # Admin, counter staff, and vendor portal views
│   │   ├── context/              # Auth, multi-tenant organization & WebSocket alert context
│   │   └── services/             # Axios API client with automatic token refresh
│   └── package.json
├── docs/                         # HLD, DECISIONS, FLOW, and API reference
├── Dockerfile                    # Unified multi-stage production Dockerfile
├── docker-compose.yml            # Local dev orchestration
└── README.md
```

---

## 🔐 Security Features

- **Multi-Tenant Data Isolation** - Strict non-nullable `org_id` on all tenant entities; complete isolation between pharmacy organizations (one admin cannot view or access another pharmacy's data).
- **JWT Authentication** - Short-lived access tokens (30min) + refresh tokens (7 days) with `iat` revocation on password reset.
- **Argon2id Password Hashing** - GPU/ASIC cracking resistant algorithm with unified complexity validation.
- **Google OAuth ID Token Verification** - Cryptographic verification via `google-auth` with mandatory email verification and audience matching.
- **Postgres Advisory Locking** - Transaction-level concurrency lock on `(location_id, item_id)` for zero race conditions.
- **Rate Limiting** - SlowAPI sliding-window limiter backed by Upstash Redis TLS.
- **Token Blacklist** - Immediate logout token revocation in Redis.
- **Login Lockout** - 5 failed attempts → 15-minute brute-force lockout.
- **Role-Based Access Control** - Role hierarchy (`admin`, `manager`, `staff`, `vendor`) with tenant scoping and GraphQL field masking.
- **Audit Logging** - Tenant-scoped immutable audit trail tracking all state-altering events.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Sayandip Bar**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](http://www.linkedin.com/in/sayandipbar2005)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?logo=github&logoColor=white)](https://github.com/Sayandip05)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?logo=gmail&logoColor=white)](mailto:sayandip@inviq.io)

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Strawberry GraphQL** - Code-first GraphQL for Python
- **LangChain/LangGraph** - AI agent orchestration
- **Groq** - Fast LLM inference
- **Supabase** - Managed PostgreSQL & Realtime
- **Upstash** - Serverless Redis
- **ChromaDB** - Vector database for RAG

---

## 📊 Project Stats

![GitHub Stars](https://img.shields.io/github/stars/Sayandip05/InvIQ?style=social)
![GitHub Forks](https://img.shields.io/github/forks/Sayandip05/InvIQ?style=social)
![GitHub Issues](https://img.shields.io/github/issues/Sayandip05/InvIQ)
![GitHub License](https://img.shields.io/github/license/Sayandip05/InvIQ)

---

<div align="center">
  <p>Made with ❤️ for healthcare professionals</p>
  <p>⭐ Star this repo if you find it helpful!</p>
</div>
