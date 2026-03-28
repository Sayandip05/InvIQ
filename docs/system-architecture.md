# System Architecture

**Project:** InvIQ — Smart Inventory Assistant
**Updated:** March 28, 2026

---

## Changelog

| Date | Change |
|------|--------|
| March 20, 2026 | Initial architecture — 3 portals, SQLite, ChromaDB, LangChain tools |
| March 28, 2026 | Added: Modular Monolith decision, 6 portals, Redis layer, WebSocket, LangGraph ReAct agent, multi-tenancy (org_id), Vendor Upload Service, Super Admin, PDF generation, Alembic migrations, updated tech stack and ADR |

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              InvIQ — SMART INVENTORY ASSISTANT                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────┐ ┌───────┐ │
│  │Super Admin │ │   Admin    │ │  Manager   │ │   Staff    │ │ Vendor │ │Viewer │ │
│  │  Portal   │ │   Portal   │ │   Portal   │ │   Portal   │ │ Portal │ │Portal │ │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └───┬────┘ └──┬────┘ │
│        └──────────────┴──────────────┴──────────────┴─────────────┴─────────┘      │
│                                        │                                              │
│                                        ▼                                              │
│             ┌─────────────────────────────────────────────────────┐                  │
│             │              FastAPI Backend (Port 8000)            │                  │
│             │                                                      │                  │
│             │  JWT Auth → RBAC Role Check → Rate Limit → Logger  │                  │
│             │                     (4 middleware layers)           │                  │
│             └──────────────────────┬──────────────────────────────┘                  │
│                                    │                                                   │
│         ┌──────────────────────────┼───────────────────────────────┐                 │
│         ▼                          ▼                               ▼                 │
│  ┌─────────────┐         ┌─────────────────┐             ┌────────────────┐         │
│  │ Application │         │   AI Agent      │             │ Infrastructure │         │
│  │   Layer     │         │   Layer         │             │    Layer       │         │
│  │             │         │ LangGraph ReAct │             │                │         │
│  │ 5 Services  │         │ 7 Tools         │             │ PostgreSQL     │         │
│  │             │         │ ChromaDB RAG    │             │ Redis          │         │
│  └──────┬──────┘         └────────┬────────┘             │ WebSocket      │         │
│         │                         │                       │ ChromaDB       │         │
│         └─────────────────────────┘                       │ ReportLab PDF  │         │
│                       │                                   └────────────────┘         │
│                       ▼                                                               │
│              ┌─────────────────┐                                                      │
│              │  Domain Layer   │                                                      │
│              │ calculations.py │                                                      │
│              │ prompts.py      │                                                      │
│              └─────────────────┘                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Decision — Modular Monolith

### Why Modular Monolith (not Microservices)

| Factor | Decision | Reason |
|--------|---------|--------|
| Team size | 1 developer | Microservices require separate deployment pipelines per service |
| Infrastructure | Free tier (Render) | One dyno, one deploy — no orchestration overhead |
| Complexity | Single domain | Inventory + Requisitions + Analytics are tightly coupled by design |
| Debugging | Simpler | Single process, single log stream, no network between services |
| Future | Can extract | If scale demands, services can be extracted — boundaries are already clean |

### What Modular Monolith Means Here

One deployable unit — one Render service, one Docker container, one process.

Internally organized into completely independent modules with strict dependency rules. Inner layers never import outer layers. No circular dependencies.

```
One process → FastAPI app
    ├── Module: Inventory (routes + service + repo)
    ├── Module: Requisition (routes + service + repo)
    ├── Module: Analytics (routes + service + cache)
    ├── Module: Vendor (routes + service + parser)
    ├── Module: Auth (routes + service + repo)
    ├── Module: Chat/Agent (routes + graph + tools)
    └── Module: SuperAdmin (routes + service)
```

Each module owns its routes, service, and repository. No module reaches into another module's repository directly — it calls the other module's service instead.

---

## 3. Clean Architecture Layers

The backend follows **Clean Architecture** with strict unidirectional dependency rule.

### Layer Rules

| Layer | Rule | Examples |
|-------|------|----------|
| `domain/` | Zero imports from infrastructure, api, or any framework | `prompts.py`, `calculations.py` |
| `infrastructure/` | Only imports from `domain/` or Python stdlib | `connection.py`, `models.py`, `vector_store.py`, `redis_client.py` |
| `application/` | Only layer calling both `domain/` and `infrastructure/` | `inventory_service.py`, `agent_tools.py`, `agent_graph.py` |
| `api/` | Never imports from `infrastructure/` directly | Routes only import `application/` and `core/` |

### Layer Diagram

```
┌────────────────────────────────────────────────────┐
│                     API LAYER                       │
│  routes/  →  schemas/  →  core/dependencies        │
│  (HTTP contract)  (Pydantic validation) (DI)        │
└──────────────────────┬─────────────────────────────┘
                       │ calls only ↓
┌────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                   │
│  inventory_service.py   requisition_service.py      │
│  analytics_service.py   vendor_service.py           │
│  user_service.py        agent_tools.py              │
│  agent_graph.py  ← NEW: LangGraph ReAct loop        │
│  → orchestrates domain logic + infra calls          │
└──────────────────────┬─────────────────────────────┘
                       │ calls only ↓
┌────────────────────────────────────────────────────┐
│                   DOMAIN LAYER                      │
│  domain/calculations.py  (stock formulas)           │
│  domain/agent/prompts.py (pure text prompts)        │
│  → pure business logic, zero framework deps         │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│                INFRASTRUCTURE LAYER                 │
│  database/     (SQLAlchemy: models, repos, queries) │
│  vector_store/ (ChromaDB: semantic memory)          │
│  cache/        (Redis: caching + token blacklist)   │  ← NEW
│  pdf/          (ReportLab: report generation)       │  ← NEW
└────────────────────────────────────────────────────┘
```

---

## 4. AI Agent Architecture (Updated)

### LangGraph ReAct Agent — How It Works

```
User question
      │
      ▼
[call_model node]
  Input: SystemPrompt + ConversationHistory + ChromaDB context + Question
  LLM (Groq LLaMA-3.3-70b) decides: which tool(s) to call
      │
      ▼ (if tool calls requested)
[run_tools node]
  Executes each tool the LLM requested:
    - get_inventory_overview
    - get_stock_health(item, location)
    - get_critical_items(severity)
    - calculate_reorder_suggestions(location)
    - get_location_summary(location_name)
    - get_category_analysis(category)
    - get_consumption_trends(item, location, days)
  Returns ToolMessage results back to LLM
      │
      ▼
[back to call_model]
  LLM reads tool results → decides: answer ready OR call more tools
      │
      ▼ (when no more tool calls needed)
[END]
  Final natural language answer → saved to DB + ChromaDB
```

### Agent vs Old Rule-Based Approach

| Old Approach (rule-based) | New Approach (ReAct agent) |
|--------------------------|---------------------------|
| `if "reorder" in question: call reorder_tool` | LLM decides which tools to call |
| Single tool call always | Multi-tool chaining per question |
| No reasoning between steps | LLM reads each result, decides next step |
| Fixed keyword matching | Natural language understanding |
| Cannot combine data from multiple tools | Synthesizes across all tool outputs |

### Graceful Fallback

```python
agent_response = run_agent(question, history, past_context)

if agent_response:
    result = {"response": agent_response}
else:
    # Fallback: rule-based when GROQ_API_KEY missing or agent fails
    result = _build_agent_response(question, db, conversation_id)
```

Product works even without Groq API key — rule-based fallback always available.

---

## 5. Redis Architecture (NEW)

### What Redis Does in InvIQ

| Use Case | Key Pattern | TTL | Invalidation |
|----------|------------|-----|-------------|
| Analytics heatmap cache | `analytics:heatmap:{org_id}` | 5 min | On any new transaction |
| Analytics summary cache | `analytics:summary:{org_id}` | 5 min | On any new transaction |
| Dashboard stats cache | `analytics:dashboard:{org_id}` | 5 min | On any new transaction |
| JWT token blacklist | `blacklisted:token:{jti}` | Token expiry time | Never (expires naturally) |
| Rate limiting counters | `ratelimit:{ip}:{endpoint}` | 1 min rolling | Never (rolling window) |

### Cache Invalidation Strategy

Write-through invalidation — whenever any write operation completes (new transaction, approved requisition), the service calls:

```python
await invalidate_pattern(f"analytics:*:{org_id}")
```

This ensures analytics are always consistent, never stale beyond the next write.

---

## 6. WebSocket Architecture (NEW)

```
Client connects: ws://api/ws/alerts/{location_id}?token=<jwt>
      │
      ▼
Server: verify JWT token on connect
  → invalid token → close(1008) immediately
  → valid token → accept connection, add to ConnectionManager
      │
      ▼
ConnectionManager: dict[location_id → list[WebSocket]]
      │
On any stock change (transaction POST):
  → InventoryService.add_transaction() completes
  → broadcast to all connections for that location_id:
     {type: "stock_alert", item: "Paracetamol", status: "CRITICAL", current_stock: 5}
      │
      ▼
Frontend receives push → shows alert badge instantly
  → No polling. No page refresh. O(locations) server work, not O(users × poll_rate)
```

---

## 7. Multi-Tenancy Architecture (NEW)

### Org Isolation Strategy

Every entity in the database carries `org_id`. Every query filters by `org_id` extracted from JWT.

```python
# In every service method:
def get_locations(self, org_id: str):
    return self.repo.get_all_locations(org_id=org_id)

# In every repository:
def get_all_locations(self, org_id: str):
    return self.db.query(Location).filter(Location.org_id == org_id).all()
```

Admin of Org A can never see Org B's data — not through a bug, not through a URL parameter change. The filter is always applied at the DB layer, not the API layer.

### Data Isolation Scope

| Entity | Isolated By |
|--------|------------|
| Organization | Platform-level (Super Admin only) |
| User | org_id |
| Location | org_id |
| Item | org_id |
| InventoryTransaction | location_id → org_id |
| Requisition | location_id → org_id |
| VendorUpload | vendor_user_id → org_id |
| AuditLog | org_id |
| ChatSession | user_id → org_id |

---

## 8. Vendor Excel Upload Architecture (NEW)

```
POST /api/vendor/upload-delivery (multipart/form-data)
      │
      ▼
VendorService.parse_excel(file, vendor_user)
      │
      ├── openpyxl reads .xlsx rows
      ├── For each row:
      │     item_name → fuzzy match → item_id (RapidFuzz, 85% threshold)
      │     validate: location assigned to vendor? quantity > 0? date valid?
      │     if valid → InventoryService.add_transaction()
      │     if invalid → append to errors list
      │
      ├── VendorUpload record saved (total_rows, success_rows, error_rows)
      │
      ▼
Response: {
  total: 48,
  success: 46,
  errors: [
    {row: 3, item_name: "Paracetmol", reason: "No match above 85% threshold"},
    {row: 17, reason: "Quantity must be positive"}
  ]
}
```

### Excel Template Structure

| item_name | quantity_received | delivery_date | notes |
|-----------|-----------------|---------------|-------|
| Paracetamol 500mg | 200 | 2026-03-28 | Morning delivery |
| Surgical Gloves | 50 | 2026-03-28 | |

Vendor never needs to know internal IDs. Location is derived from their JWT `location_ids`.

---

## 9. PDF Report Architecture (NEW)

```
GET /api/admin/reports/generate?from=2026-01-01&to=2026-03-28
      │
      ▼
AnalyticsService.generate_report(org_id, from_date, to_date)
      │
      ├── Stock health summary query
      ├── Top 10 critical items with reorder quantities
      ├── Requisition stats (raised/approved/rejected)
      ├── Vendor delivery log
      ├── Consumption trend table
      │
      ▼
ReportLab builds PDF:
  - Header: Org name, date range, generated_by, generated_at
  - Section 1: Executive Summary (health counts)
  - Section 2: Critical Items Table
  - Section 3: Requisition Summary
  - Section 4: Vendor Activity Log
  - Section 5: Consumption Trends
      │
      ▼
Returns: PDF file (Content-Disposition: attachment)
```

---

## 10. Technology Stack (Updated)

| Layer | Technology | Purpose | Status |
|-------|------------|---------|--------|
| **Frontend** | React + Vite + Tailwind | 6 separate portals | Existing (friend) |
| **Backend** | FastAPI + Uvicorn | Async REST + WebSocket server | Existing |
| **ORM** | SQLAlchemy + Alembic | DB abstraction + migrations | Alembic NEW |
| **Primary DB** | PostgreSQL (Supabase) | Transactional data, org-isolated | Upgraded from SQLite |
| **Vector DB** | ChromaDB | AI cross-session semantic memory | Existing |
| **Cache** | Redis (Upstash) | Analytics cache + token blacklist + rate limiting | NEW |
| **AI Framework** | LangGraph + LangChain | ReAct agent orchestration | Upgraded from rule-based |
| **LLM** | Groq LLaMA-3.3-70b | Language model inference | Existing |
| **Excel Parsing** | openpyxl + RapidFuzz | Vendor delivery ingestion | NEW |
| **PDF Generation** | ReportLab | Org-wide audit reports | NEW |
| **Real-time** | WebSocket (FastAPI native) | Stock alert push | NEW |
| **Rate Limiting** | slowapi + Redis | API abuse protection | NEW |
| **Observability** | LangSmith + structured logs | Agent tracing + request logging | Existing |
| **Testing** | pytest + httpx | 15+ tests, CI-gated | NEW |
| **CI/CD** | GitHub Actions | Test → deploy gate | NEW |
| **Deployment** | Render (backend) + Vercel (frontend) | Free tier, auto-deploy | NEW |

---

## 11. Environment Variables (Updated)

```env
# Database
DATABASE_URL=postgresql://...  # Supabase connection string

# Cache
REDIS_URL=redis://...          # Upstash Redis URL

# AI
GROQ_API_KEY=<key>
LANGCHAIN_API_KEY=<optional>
LANGCHAIN_PROJECT=inviq

# Auth
SECRET_KEY=<strong-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
ENVIRONMENT=production
CORS_ORIGINS=https://inviq.vercel.app
```

---

## 12. ADR Summary (Updated)

| Decision | Choice | Reason |
|----------|--------|--------|
| Deployment Architecture | Modular Monolith | Single developer, free tier, tightly coupled domain |
| Internal Architecture | Clean Architecture | Testability, strict layer separation, swappable infra |
| DB ORM | SQLAlchemy + Repository pattern | Swap SQLite → PostgreSQL without changing business logic |
| DB Migrations | Alembic | Schema versioning for production — `create_all()` is not production-safe |
| Multi-tenancy | org_id on every entity | DB-layer isolation, not API-layer — cannot be bypassed |
| AI Agent | LangGraph ReAct | True reasoning loop vs keyword matching; graceful fallback preserved |
| AI Memory | DB history + ChromaDB RAG | ACID history + semantic cross-session recall |
| Cache | Redis (Upstash) | Analytics caching + secure logout (token blacklist) + rate limiting |
| Real-time | WebSocket (FastAPI native) | No polling, O(locations) server work, native async |
| Excel Parsing | openpyxl + RapidFuzz | No external service, fuzzy name matching for real vendor workflows |
| PDF | ReportLab | Pure Python, no external service, free |
| Rate Limiting | slowapi + Redis | Native FastAPI integration, Redis-backed for distributed correctness |
| API Style | REST with `{success, data, error}` envelope | Consistent client contract across all 6 portals |
| DI | FastAPI Depends() | Native, testable, no external IoC container |

---

## 13. Module Responsibilities (Updated)

| Module | Responsibility | Public API |
|--------|---------------|------------|
| `api/routes` | HTTP endpoint definitions | REST endpoints |
| `api/routes/websocket` | WebSocket connection management | `ws://` endpoints |
| `api/schemas` | Pydantic request/response models | Type validation |
| `application/inventory_service` | Transaction CRUD, stock calculations | Domain operations |
| `application/requisition_service` | Requisition workflow | Approve/reject/create |
| `application/analytics_service` | Data aggregation + Redis cache | Dashboard data |
| `application/vendor_service` | Excel parsing, fuzzy matching, bulk ingestion | `parse_excel()` |
| `application/user_service` | User + org management | `create_user()`, `assign_role()` |
| `application/agent_tools` | LangGraph @tool wrappers | 7 tool functions |
| `application/agent_graph` | LangGraph ReAct loop | `run_agent()` |
| `domain/calculations` | Pure stock formulas | `calculate_reorder_quantity()` |
| `domain/agent/prompts` | System prompt text | `get_system_prompt()` |
| `infrastructure/database/models` | SQLAlchemy ORM classes | DB models |
| `infrastructure/database/repos` | Data access layer (org-scoped) | CRUD operations |
| `infrastructure/database/queries` | Complex SQL views | `get_latest_stock_health()` |
| `infrastructure/vector_store` | ChromaDB semantic memory | `add_message()`, `search_relevant()` |
| `infrastructure/cache` | Redis client (cache + blacklist) | `get_cached()`, `set_cached()`, `invalidate_pattern()` |
| `infrastructure/pdf` | ReportLab PDF builder | `generate_report()` |
| `core/config` | Settings from .env | `settings` singleton |
| `core/dependencies` | FastAPI DI factories | `get_inventory_service()`, `require_role()` |
| `core/exceptions` | Custom exception hierarchy | `NotFoundError`, `ValidationError` |
| `core/error_handlers` | Global exception → HTTP mapping | FastAPI exception handlers |
| `core/middleware` | Request/response logging | `RequestLoggerMiddleware` |
| `core/security` | JWT encode/decode/blacklist check | `verify_access_token()` |
