# High Level Design (HLD)

**Project:** InvIQ — Smart Inventory Assistant
**Updated:** March 28, 2026

---

## Changelog

| Date | Change |
|------|--------|
| March 20, 2026 | Initial HLD — 4 roles, 3 modules, core APIs |
| March 28, 2026 | Added: 6-role RBAC, multi-tenancy, Vendor Excel upload, Super Admin, Organization model, PDF report, WebSocket alerts, Redis caching, LangGraph ReAct agent wiring, updated user journeys |

---

## 1. Module Breakdown

### 1.1 Core Modules

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                MODULE OVERVIEW                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                           FRONTEND PORTALS (6 separate)                       │  │
│  │  Super Admin  │  Admin Portal  │  Manager Portal  │  Staff Portal             │  │
│  │  Vendor Portal  │  Viewer Portal  │  (React + Vite + Tailwind)                │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                           BACKEND MODULES                                      │  │
│  │                                                                                │  │
│  │  ┌──────────────────────┐  ┌───────────────────────────────────────────────┐ │  │
│  │  │    API Layer        │  │          APPLICATION LAYER                     │ │  │
│  │  │  routes/analytics.py │  │  inventory_service.py  │ business logic      │ │  │
│  │  │  routes/chat.py     │  │  requisition_service.py │ workflow            │ │  │
│  │  │  routes/inventory.py│  │  analytics_service.py  │ computation         │ │  │
│  │  │  routes/requisition.py  │  agent_tools.py  │ LangGraph tools          │ │  │
│  │  │  routes/vendor.py   │  │  vendor_service.py │ Excel ingestion         │ │  │
│  │  │  routes/superadmin.py│  │  user_service.py  │ org + user mgmt        │ │  │
│  │  │  routes/websocket.py│  │  agent_graph.py   │ ReAct loop             │ │  │
│  │  │  schemas/           │  │                                               │ │  │
│  │  └──────────────────────┘  └───────────────────────────────────────────────┘ │  │
│  │                                    │                                           │  │
│  │                                    ▼                                           │  │
│  │  ┌──────────────────────┐  ┌───────────────────────────────────────────────┐ │  │
│  │  │      DOMAIN          │  │          INFRASTRUCTURE LAYER                 │ │  │
│  │  │  calculations.py      │  │  database/connection.py  │  DB session        │ │  │
│  │  │  agent/prompts.py   │  │  database/models.py      │  ORM models        │ │  │
│  │  │                     │  │  database/queries.py    │  complex SQL       │ │  │
│  │  │                     │  │  database/inventory_repo.py │ CRUD              │ │  │
│  │  │                     │  │  database/requisition_repo.py │ CRUD           │ │  │
│  │  │                     │  │  vector_store/vector_store.py │ ChromaDB       │ │  │
│  │  │                     │  │  cache/redis_client.py  │  Redis             │ │  │
│  │  └──────────────────────┘  └───────────────────────────────────────────────┘ │  │
│  │                                                                                │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                          CORE LAYER                                       │ │  │
│  │  │  config.py  │  exceptions.py  │  dependencies.py  │  error_handlers.py  │ │  │
│  │  │  logging_config.py  │  middleware/request_logger.py  │  security.py      │ │  │
│  │  └──────────────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Descriptions

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| **Super Admin Portal** | Platform-level org and user management | UserService, OrgService |
| **Admin Portal** | Full org management, analytics, audit log, reports | All services |
| **Manager Portal** | Requisition approvals, stock monitoring | RequisitionService, AnalyticsService |
| **Staff Portal** | Daily stock entry, raise requisitions, AI chat | InventoryService, RequisitionService |
| **Vendor Portal** | Upload delivery Excel, view upload history | VendorService |
| **Viewer Portal** | Read-only analytics and inventory view | AnalyticsService |
| **InventoryService** | Transaction CRUD, stock calculations | InventoryRepository |
| **RequisitionService** | Requisition workflow | RequisitionRepository, InventoryService |
| **AnalyticsService** | Data aggregation, statistics, Redis caching | SQL queries, RedisClient |
| **VendorService** | Excel parsing, row validation, bulk ingestion | InventoryService, openpyxl |
| **AgentTools** | LangGraph @tool wrappers | SQL queries |
| **AgentGraph** | LangGraph ReAct loop wiring | AgentTools, Groq LLM, ChromaDB |
| **UserService** | User creation, role assignment, org isolation | UserRepository |
| **InventoryRepository** | Location/Item/Transaction CRUD | SQLAlchemy |
| **RequisitionRepository** | Requisition CRUD | SQLAlchemy |
| **RedisClient** | Cache get/set/invalidate, token blacklist | Upstash Redis |

---

## 2. Role Hierarchy & Access Control

### 2.1 Role Hierarchy

```
Super Admin (platform owner — Sayandip only)
    └── Admin (one per organization)
            ├── Manager
            ├── Staff
            ├── Vendor
            └── Viewer
```

### 2.2 Who Gives Access to Whom

| Role | Can Create | Cannot Create |
|------|-----------|---------------|
| Super Admin | Admin accounts, Organizations | Cannot touch inventory data |
| Admin | Manager, Staff, Vendor, Viewer | Cannot create another Admin |
| Manager | Nobody | — |
| Staff | Nobody | — |
| Vendor | Nobody | — |
| Viewer | Nobody | — |

### 2.3 Portal Pages Per Role

| Role | Portal URL | Pages Accessible |
|------|-----------|-----------------|
| Super Admin | `/superadmin` | Organizations, All Users, Pending Signups, Assign Roles, Deactivate Org |
| Admin | `/admin` | Dashboard, User Management, Inventory, Analytics, Requisitions, Audit Log, Vendor Deliveries, PDF Reports |
| Manager | `/manager` | Dashboard, Requisitions (approve/reject), Inventory View, Analytics, Vendor Deliveries |
| Staff | `/staff` | My Location Stock, Log Transaction, Raise Requisition, My Requisitions, AI Assistant |
| Vendor | `/vendor` | Upload Delivery, My Uploads, Download Template |
| Viewer | `/viewer` | Dashboard (read-only), Analytics (read-only), Inventory View (read-only) |

### 2.4 JWT Claims Structure

```json
{
  "sub": "user_id",
  "role": "staff",
  "org_id": "org_123",
  "location_ids": [1, 3],
  "exp": 1234567890
}
```

Every DB query filters by `org_id` — one organization never sees another's data.

---

## 3. API Surface

### 3.1 Inventory APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/inventory/locations` | GET | List all locations |
| `/api/inventory/items` | GET | List all items |
| `/api/inventory/location/{id}/items` | GET | Items at location |
| `/api/inventory/stock/{location_id}/{item_id}` | GET | Current stock level |
| `/api/inventory/transaction` | POST | Add transaction |
| `/api/inventory/bulk-transaction` | POST | Bulk add transactions |
| `/api/inventory/upload-transactions` | POST | **[NEW]** Vendor Excel upload |
| `/api/inventory/reset-data` | POST | Reset test data |

### 3.2 Requisition APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/requisition/create` | POST | Create requisition |
| `/api/requisition/list` | GET | List requisitions |
| `/api/requisition/{id}` | GET | Get requisition |
| `/api/requisition/stats` | GET | Requisition statistics |
| `/api/requisition/{id}/approve` | PUT | Approve requisition |
| `/api/requisition/{id}/reject` | PUT | Reject requisition |
| `/api/requisition/{id}/cancel` | PUT | Cancel requisition |

### 3.3 Analytics APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analytics/heatmap` | GET | Stock level matrix (Redis cached, 5min TTL) |
| `/api/analytics/alerts` | GET | Critical/warning items |
| `/api/analytics/summary` | GET | Overall statistics (Redis cached) |
| `/api/analytics/dashboard/stats` | GET | Dashboard chart data (Redis cached) |

### 3.4 Chat APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/query` | POST | Send AI question → LangGraph ReAct agent |
| `/api/chat/history/{id}` | GET | Get conversation |
| `/api/chat/sessions` | GET | List conversations |
| `/api/chat/suggestions` | GET | Question suggestions |

### 3.5 Auth APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | JWT login (lockout after 5 failures) |
| `/api/auth/register` | POST | Admin creates new user |
| `/api/auth/logout` | POST | **[NEW]** Blacklist token in Redis |
| `/api/auth/me` | GET | Current user profile |
| `/api/auth/me` | PATCH | Update own profile |
| `/api/auth/change-password` | POST | Change own password |
| `/api/auth/refresh` | POST | Refresh JWT token |
| `/api/auth/users` | GET | List users (filterable) |
| `/api/auth/users/{id}` | GET | Single user detail |
| `/api/auth/users/{id}/role` | PUT | Update user role |
| `/api/auth/users/{id}/activate` | PUT | Activate user |
| `/api/auth/users/{id}/deactivate` | PUT | Deactivate user |
| `/api/auth/users/{id}/reset-password` | POST | Admin reset password |

### 3.6 Admin Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/overview` | GET | Platform stats |
| `/api/admin/audit-logs` | GET | Filterable audit trail |
| `/api/admin/users/summary` | GET | User management overview |
| `/api/admin/reports/generate` | GET | **[NEW]** Generate PDF report |

### 3.7 Vendor APIs (NEW)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/vendor/upload-delivery` | POST | Upload Excel delivery manifest |
| `/api/vendor/my-uploads` | GET | Upload history with row-level status |
| `/api/vendor/template` | GET | Download blank Excel template |

### 3.8 Super Admin APIs (NEW)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/superadmin/organizations` | GET | All orgs on platform |
| `/api/superadmin/users` | GET | All users across all orgs |
| `/api/superadmin/assign-role` | POST | Assign Admin to org |
| `/api/superadmin/org/{id}/deactivate` | PUT | Deactivate entire org |

### 3.9 WebSocket APIs (NEW)

| Endpoint | Protocol | Purpose |
|----------|---------|---------|
| `/ws/alerts/{location_id}?token=<jwt>` | WebSocket | Real-time stock alert push |

---

## 4. Major Data Entities

### 4.1 Entity Relationship (Updated)

```
┌──────────────────┐
│   Organization   │  ← NEW: multi-tenancy root
├──────────────────┤
│ id               │
│ name             │
│ is_active        │
│ created_at       │
└────────┬─────────┘
         │ 1:N
         ▼
┌──────────────┐         ┌─────────────────┐         ┌──────────────┐
│     User     │         │  Inventory      │         │     Item     │
├──────────────┤         │  Transaction    │         ├──────────────┤
│ id           │         ├─────────────────┤         │ id           │
│ org_id       │         │ id              │         │ name         │
│ email        │         │ location_id     │         │ category     │
│ role         │         │ item_id         │         │ unit         │
│ location_ids │         │ date            │         │ lead_time    │
│ is_active    │         │ opening_stock   │         │ min_stock    │
└──────────────┘         │ received        │         └──────────────┘
                         │ issued          │
                         │ closing_stock   │
                         │ entered_by      │
                         └───────┬─────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
     ┌─────────────────┐  ┌─────────────┐  ┌──────────────────┐
     │  Requisition    │  │ ChatSession │  │  VendorUpload    │ ← NEW
     ├─────────────────┤  ├─────────────┤  ├──────────────────┤
     │ location_id     │  │ user_id     │  │ id               │
     │ requested_by    │  │ title       │  │ vendor_user_id   │
     │ urgency         │  └──────┬──────┘  │ filename         │
     │ status          │         │ 1:N     │ location_id      │
     │ approved_by     │         ▼         │ total_rows       │
     └────────┬────────┘  ┌─────────────┐  │ success_rows     │
              │ 1:N       │ ChatMessage │  │ error_rows       │
              ▼           └─────────────┘  │ status           │
     ┌─────────────────┐                   │ uploaded_at      │
     │ RequisitionItem │                   └──────────────────┘
     ├─────────────────┤
     │ item_id         │        ┌──────────────────┐
     │ quantity_req    │        │    AuditLog      │  ← existing, expanded
     │ quantity_appr   │        ├──────────────────┤
     └─────────────────┘        │ user_id          │
                                │ org_id           │
                                │ action           │
                                │ resource_type    │
                                │ details (JSON)   │
                                │ ip_address       │
                                └──────────────────┘
```

### 4.2 Entity Definitions (Updated)

| Entity | Key Fields | Status |
|--------|------------|--------|
| **Organization** | id, name, is_active, created_at | NEW |
| **User** | id, org_id, email, role, location_ids, is_active | UPDATED (added org_id, location_ids) |
| **Location** | id, org_id, name, type, region, address | UPDATED (added org_id) |
| **Item** | id, org_id, name, category, unit, lead_time_days, min_stock | UPDATED (added org_id) |
| **InventoryTransaction** | id, location_id, item_id, date, opening_stock, received, issued, closing_stock | UNCHANGED |
| **Requisition** | id, requisition_number, location_id, requested_by, department, urgency, status | UNCHANGED |
| **RequisitionItem** | id, requisition_id, item_id, quantity_requested, quantity_approved | UNCHANGED |
| **VendorUpload** | id, vendor_user_id, filename, location_id, total_rows, success_rows, error_rows, status | NEW |
| **ChatSession** | id, user_id, title | UNCHANGED |
| **ChatMessage** | id, session_id, role, content | UNCHANGED |
| **AuditLog** | id, user_id, org_id, action, resource_type, resource_id, details, ip_address | UPDATED (added org_id) |

---

## 5. User Journeys (Updated)

### 5.1 Super Admin: Onboard a New Organization

```
Sayandip (Super Admin) → /superadmin/organizations
  → POST /api/superadmin/organizations (create org)
  → POST /api/superadmin/assign-role (assign a user as Admin)
  → Admin gets login credentials
  → Admin logs in → /admin portal
```

### 5.2 Admin: Create Vendor Account

```
Admin → /admin/users → Create User (role=vendor, location_ids=[1,2])
  → POST /api/auth/register {role: "vendor", location_ids: [...]}
  → UserService creates user with org_id from Admin's JWT
  → Vendor receives login credentials
```

### 5.3 Vendor: Upload Delivery Excel

```
Vendor → /vendor/upload-delivery
  → Downloads template from GET /api/vendor/template
  → Fills in: item_name, quantity_received, delivery_date, notes
  → Uploads file → POST /api/vendor/upload-delivery
  → VendorService.parse_excel()
      → openpyxl reads rows
      → fuzzy match item_name → item_id (RapidFuzz, 85% threshold)
      → validate each row
      → call InventoryService.add_transaction() per row
  → Returns: {total: 48, success: 46, errors: [{row: 3, reason: "item not found"}]}
  → VendorUpload record saved to DB
  → Admin/Manager can see upload in /admin/vendor-deliveries
```

### 5.4 Staff: Create Requisition

```
Staff → /staff/requisition → POST /api/requisition/create
  → RequisitionService.create_requisition()
  → Generates REQ-YYYYMMDD-XXX number
  → Creates Requisition + RequisitionItems
  → WebSocket push to Manager portal: "New requisition pending"
  → Response: {success: true, data: {id, number, status: PENDING}}
```

### 5.5 Manager: Approve Requisition

```
Manager → /manager/requisitions → PUT /api/requisition/{id}/approve
  → RequisitionService.approve_requisition()
  → Deducts stock via InventoryService
  → Invalidates Redis cache: analytics:*
  → Updates status to APPROVED
  → AuditLog entry created
  → Response: {success: true}
```

### 5.6 Admin: AI Chat with LangGraph Agent

```
Admin/Staff → /staff/chat → POST /api/chat/query {question: "..."}
  → JWT verified → org_id extracted
  → ChromaDB: retrieve past context (RAG)
  → LangGraph ReAct Agent:
      call_model node → LLM decides which tool(s) to call
      run_tools node  → executes tool(s) with live DB data
      call_model node → LLM synthesizes final answer
      (loops until no more tool calls needed)
  → Response saved to ChatSession + ChromaDB
  → Response: {success: true, response: "...", conversation_id}
```

### 5.7 Admin: Generate PDF Report

```
Admin → /admin/reports → GET /api/admin/reports/generate?from=2026-01-01&to=2026-03-28
  → AnalyticsService aggregates data for date range
  → ReportLab generates PDF:
      - Org name, date range, generated by
      - Stock health summary (critical/warning/healthy)
      - Top 10 critical items with reorder suggestions
      - Requisition summary
      - Vendor delivery log
      - Consumption trends
  → Returns PDF file download
```

### 5.8 Real-time Stock Alert via WebSocket

```
Stock drops below threshold (any transaction)
  → InventoryService.add_transaction() completes
  → ConnectionManager.broadcast(location_id, {type: "alert", item: "...", status: "CRITICAL"})
  → All connected clients for that location_id receive instant push
  → Frontend shows alert badge without page refresh
```

---

## 6. Non-Functional Requirements (Updated)

| Metric | Target | Notes |
|--------|--------|-------|
| API Response Time | < 500ms (p95) | Excluding AI chat |
| Analytics Response | < 50ms (p95) | Redis cached |
| AI Chat Response | < 10s (p95) | Groq LLM latency |
| Page Load Time | < 2s | Initial load |
| Database Queries | < 100ms (p95) | Simple queries |
| Uptime | 99.5% (prod) | Render free tier |
| Concurrent Users | 50 (initial) | Can scale vertically |
| Authentication | JWT + Redis blacklist | Secure logout |
| Authorization | Role-based (6 roles) | org_id isolation |
| Real-time | WebSocket per location | Stock alert push |

---

## 7. System Boundaries (Updated)

### Does

- Inventory transaction management
- Vendor Excel delivery ingestion with fuzzy item matching
- Requisition workflow (create → approve/reject)
- Stock health calculations
- AI-powered chat via LangGraph ReAct agent (Groq LLaMA-3.3-70b)
- Analytics dashboard with Redis caching
- JWT authentication + RBAC (6 roles)
- Multi-tenant org isolation (org_id on every entity)
- Audit trail (who did what, when, from which org)
- Cross-session semantic memory (ChromaDB RAG)
- Real-time stock alerts via WebSocket
- PDF report generation (ReportLab)
- Token blacklisting on logout (Redis)
- Rate limiting (slowapi + Redis)

### Does NOT Do (Planned / Out of Scope)

- Email/SMS notifications (future)
- Payment processing
- Mobile app
- Self-service org signup (manual onboarding via Super Admin only)
- Vendor email notifications on upload result (future)
- Multi-language UI (future)
