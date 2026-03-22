# High Level Design (HLD)

**Project:** Smart Inventory Assistant  
**Updated:** March 20, 2026

---

## 1. Module Breakdown

### 1.1 Core Modules

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                MODULE OVERVIEW                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                           FRONTEND MODULES                                    │  │
│  │  Vendor DataEntry  │  Staff Requisition  │  Admin Dashboard  │  Shared Layout   │  │
│  │  (pages/vendor)  │  (pages/staff)      │  (pages/admin)   │  (components)    │  │
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
│  │  │  routes/requisition.py  │  │  agent_tools.py  │ LangGraph tools       │ │  │
│  │  │  schemas/          │  │                                               │ │  │
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
│  │  └──────────────────────┘  └───────────────────────────────────────────────┘ │  │
│  │                                                                                │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                          CORE LAYER                                       │ │  │
│  │  │  config.py  │  exceptions.py  │  dependencies.py  │  error_handlers.py  │ │  │
│  │  │  logging_config.py  │  middleware/request_logger.py                       │ │  │
│  │  └──────────────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Descriptions

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| **Vendor DataEntry** | Form for entering inventory transactions | InventoryService, api.js |
| **Staff Requisition** | Create requisition requests | RequisitionService, api.js |
| **Admin Dashboard** | Display analytics charts | AnalyticsService, api.js |
| **Admin Inventory** | View/manage inventory | InventoryService, api.js |
| **Admin Requisitions** | Approve/reject requisitions | RequisitionService, api.js |
| **Admin Chatbot** | AI conversation interface | ChatService, api.js |
| **InventoryService** | Transaction CRUD, stock calculations | InventoryRepository |
| **RequisitionService** | Requisition workflow | RequisitionRepository, InventoryService |
| **AnalyticsService** | Data aggregation, statistics | SQL queries |
| **AgentTools** | LangGraph @tool wrappers | SQL queries |
| **InventoryRepository** | Location/Item/Transaction CRUD | SQLAlchemy |
| **RequisitionRepository** | Requisition CRUD | SQLAlchemy |

---

## 2. API Surface

### 2.1 Inventory APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/inventory/locations` | GET | List all locations |
| `/api/inventory/items` | GET | List all items |
| `/api/inventory/location/{id}/items` | GET | Items at location |
| `/api/inventory/stock/{location_id}/{item_id}` | GET | Current stock level |
| `/api/inventory/transaction` | POST | Add transaction |
| `/api/inventory/bulk-transaction` | POST | Bulk add transactions |
| `/api/inventory/reset-data` | POST | Reset test data |

### 2.2 Requisition APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/requisition/create` | POST | Create requisition |
| `/api/requisition/list` | GET | List requisitions |
| `/api/requisition/{id}` | GET | Get requisition |
| `/api/requisition/stats` | GET | Requisition statistics |
| `/api/requisition/{id}/approve` | PUT | Approve requisition |
| `/api/requisition/{id}/reject` | PUT | Reject requisition |
| `/api/requisition/{id}/cancel` | PUT | Cancel requisition |

### 2.3 Analytics APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analytics/heatmap` | GET | Stock level matrix |
| `/api/analytics/alerts` | GET | Critical/warning items |
| `/api/analytics/summary` | GET | Overall statistics |
| `/api/analytics/dashboard/stats` | GET | Dashboard chart data |

### 2.4 Chat APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/query` | POST | Send AI question |
| `/api/chat/history/{id}` | GET | Get conversation |
| `/api/chat/sessions` | GET | List conversations |
| `/api/chat/suggestions` | GET | Question suggestions |

### 2.5 Auth APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | JWT login (lockout after 5 failures) |
| `/api/auth/register` | POST | Admin creates new user |
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

### 2.6 Admin Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/overview` | GET | Platform stats |
| `/api/admin/audit-logs` | GET | Filterable audit trail |
| `/api/admin/users/summary` | GET | User management overview |

---

## 3. Major Data Entities

### 3.1 Entity Relationship

```
┌──────────────┐         ┌─────────────────┐         ┌──────────────┐
│  Location    │────────▶│  Inventory      │◀────────│     Item     │
│              │   1:N   │ Transaction    │    N:1  │              │
├──────────────┤         ├─────────────────┤         ├──────────────┤
│ id           │         │ id              │         │ id           │
│ name         │         │ location_id     │         │ name         │
│ type         │         │ item_id         │         │ category     │
│ region       │         │ date            │         │ unit         │
│ address     │         │ opening_stock   │         │ lead_time    │
│ created_at  │         │ received        │         │ min_stock    │
└──────────────┘         │ issued          │         └──────────────┘
                         │ closing_stock  │
                         │ entered_by     │
                         │ created_at    │
                         └───────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │  Requisition │
                          ├──────────────┤
             ┌────────────│ location_id   │
             │            │ requested_by  │
             │            │ department    │
             │            │ urgency       │
             │            │ status        │
             │            │ approved_by   │
             │            └──────┬────────┘
             │                   │ 1:N
             ▼                   ▼
      ┌─────────────────┐  ┌─────────────────┐
      │ RequisitionItem │  │ ChatSession     │
      ├─────────────────┤  ├─────────────────┤
      │ id              │  │ id (UUID)       │
      │ requisition_id  │  │ user_id         │
      │ item_id        │  │ title           │
      │ quantity_req    │  │ created_at      │
      │ quantity_appr   │  └────────┬────────┘
      │ notes           │           │ 1:N
      └─────────────────┘           ▼
                          ┌─────────────────┐
                          │ ChatMessage    │
                          ├─────────────────┤
                          │ id             │
                          │ session_id     │
                          │ role           │
                          │ content        │
                          │ created_at     │
                          └─────────────────┘
```

### 3.2 Entity Definitions

| Entity | Key Fields |
|--------|------------|
| **Location** | id, name, type, region, address |
| **Item** | id, name, category, unit, lead_time_days, min_stock |
| **InventoryTransaction** | id, location_id, item_id, date, opening_stock, received, issued, closing_stock |
| **Requisition** | id, requisition_number, location_id, requested_by, department, urgency, status |
| **RequisitionItem** | id, requisition_id, item_id, quantity_requested, quantity_approved |
| **ChatSession** | id, user_id, title |
| **ChatMessage** | id, session_id, role, content |

---

## 4. User Journeys

### 4.1 Vendor: Enter Inventory Data

```
Vendor → DataEntry page → POST /api/inventory/bulk-transaction
  → InventoryService.add_transaction() (calculates closing_stock)
  → InventoryRepository → SQLite
  → Response: {success: true, data: {...}}
```

### 4.2 Staff: Create Requisition

```
Staff → StaffRequisition page → POST /api/requisition/create
  → RequisitionService.create_requisition()
  → Generates REQ-YYYYMMDD-XXX number
  → Creates Requisition + RequisitionItems
  → Response: {success: true, data: {id, number, status: PENDING}}
```

### 4.3 Admin: Approve Requisition

```
Admin → Requisitions page → PUT /api/requisition/{id}/approve
  → RequisitionService.approve_requisition()
  → Deducts stock via InventoryService
  → Updates status to APPROVED
  → Response: {success: true}
```

### 4.4 Admin: AI Chat

```
Admin → Chatbot page → POST /api/chat/query
  → AgentTools (LangGraph @tool functions) query SQLite
  → Returns formatted response
  → Saves to SQLite + ChromaDB
  → Response: {success: true, response: "...", conversation_id}
```

---

## 5. Non-Functional Requirements

| Metric | Target | Notes |
|--------|--------|-------|
| API Response Time | < 500ms (p95) | Excluding AI chat |
| AI Chat Response | < 10s (p95) | Depends on LLM latency |
| Page Load Time | < 2s | Initial load |
| Database Queries | < 100ms (p95) | Simple queries |
| Uptime | 99.5% (prod) | Excluding maintenance |
| Concurrent Users | 50 (initial) | Can scale vertically |
| Authentication | JWT (done) | Implemented |
| Authorization | Role-based (done) | 4 roles: admin, manager, staff, viewer |

---

## 6. System Boundaries

### Does

- Inventory transaction management
- Requisition workflow (create → approve/reject)
- Stock health calculations
- AI-powered chat for inventory queries
- Analytics dashboard
- JWT authentication + RBAC (4 roles)
- Audit trail (who did what, when)
- Cross-session semantic memory

### Does NOT Do (Yet)

- Email notifications (Phase 6)
- Payment processing
- Multi-tenant isolation
- Advanced reporting
- Mobile app
