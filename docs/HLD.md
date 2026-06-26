# High-Level Design (HLD) - InvIQ Smart Inventory Assistant

**Version:** 4.0  
**Last Updated:** June 26, 2026  
**Author:** Sayandip Bar

---

## 1. Problem Statement

Healthcare facilities struggle with manual inventory management, leading to stockouts of critical medical supplies, expired medications, and inefficient procurement. Staff spend hours on spreadsheets, lack real-time visibility, and cannot predict shortages before they become critical. InvIQ solves this by providing an AI-powered inventory management system that automates tracking, predicts shortages, and enables intelligent decision-making through natural language queries.

---

## 2. Who Are the Users?

### Primary Users
- **Hospital Administrators** - Oversee multiple locations, need consolidated reports
- **Inventory Managers** - Approve requisitions, monitor stock levels
- **Medical Staff** - Record stock usage, create requisition requests
- **Vendors** - Upload delivery manifests via Excel

### Pain Points Solved
- ❌ Manual stock counting → ✅ Automated transaction tracking
- ❌ Delayed shortage alerts → ✅ Real-time critical stock notifications
- ❌ Complex data analysis → ✅ AI chatbot answers questions in plain English
- ❌ Paper-based requisitions → ✅ Digital approval workflow
- ❌ Vendor coordination chaos → ✅ Excel upload with fuzzy item matching

---

## 3. System Overview

**InvIQ** is an AI-powered inventory management platform that tracks medical supplies across multiple healthcare locations. It provides:

1. **Real-time inventory tracking** with automatic stock calculations
2. **AI chatbot** powered by LangGraph ReAct agent for natural language queries
3. **Requisition workflow** with approval/rejection system
4. **Vendor integration** via Excel upload with fuzzy item matching
5. **Analytics dashboard** with heatmaps and critical alerts
6. **GraphQL analytics layer** via Strawberry — role-aware resolvers at `/graphql/analytics`
7. **Multi-tenancy** supporting multiple organizations
8. **Guest Demo Mode** permitting unauthenticated dashboard and chat access
9. **Low-stock email alerts** dispatched to managers on critical stock shortages

---

## 4. Scope

### ✅ In Scope
- Multi-location inventory tracking
- AI-powered natural language queries
- Requisition approval workflow
- Vendor Excel upload integration
- Real-time stock alerts (WebSocket) & Low-stock email alerts (SMTP)
- Role-based access control (5 roles: super_admin, admin, manager, staff, vendor) + Guest Demo Mode
- Analytics dashboard with caching
- Multi-tenancy (organization isolation)
- Audit logging for compliance
- PDF report generation

### ❌ Out of Scope
- Barcode/RFID scanning (future)
- Mobile app (web-responsive only)
- Automated reordering (manual approval required)
- Integration with ERP systems (future)
- Predictive analytics (ML models - future)
- Multi-language support (English only)
- Offline mode (requires internet)

---

## 5. System Architecture

### 5.1 Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  React 19 SPA (Vite)                                                 │  │
│  │  - 5 Role-Based Portals (Super Admin, Admin, Manager, Staff,        │  │
│  │    Vendor) + Guest Demo Mode                                         │  │
│  │  - Landing Page                                                      │  │
│  │  - WebSocket Client (real-time alerts)                              │  │
│  │  - Auth Context (JWT token management)                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │
                             │ HTTPS/REST (56 endpoints)
                             │ WebSocket (real-time)
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (Python 3.11+)                                  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Middleware Stack                                              │ │  │
│  │  │  1. CORS (allow origins)                                       │ │  │
│  │  │  2. Request Logger (UUID, timing)                              │ │  │
│  │  │  3. Rate Limiter (slowapi - 5-60 req/min)                      │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Authentication & Authorization                                │ │  │
│  │  │  - JWT token validation (access + refresh)                     │ │  │
│  │  │  - Token blacklist check (Redis)                               │ │  │
│  │  │  - Role-based access control (5-tier hierarchy)                │ │  │
│  │  │  - Guest Demo Access (optional JWT validation on GET routes)   │ │  │
│  │  │  - Multi-tenancy (org_id isolation)                            │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  REST API Routes (56 endpoints)                                │ │  │
│  │  │  /api/auth/*        - Authentication (21 endpoints)            │ │  │
│  │  │  /api/inventory/*   - Inventory management (9 endpoints)       │ │  │
│  │  │  /api/requisition/* - Requisition workflow (8 endpoints)       │ │  │
│  │  │  /api/chat/*        - AI chatbot (5 endpoints)                 │ │  │
│  │  │  /api/analytics/*   - Analytics REST reads (4 endpoints)       │ │  │
│  │  │  /api/vendor/*      - Vendor uploads (3 endpoints)             │ │  │
│  │  │  /api/superadmin/*  - Super admin (6 endpoints)                │ │  │
│  │  │  /ws                - WebSocket (2 endpoints)                  │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  GraphQL Analytics (Strawberry — read-only)                    │ │  │
│  │  │  /graphql/analytics — 5 queries                                │ │  │
│  │  │  · dashboardStats   - Chart data (cached 2 min)                │ │  │
│  │  │  · heatmap          - Location×item grid (cached 5 min)        │ │  │
│  │  │  · alerts(severity) - Critical/warning list (cached 5 min)     │ │  │
│  │  │  · summary          - Health overview (cached 5 min)           │ │  │
│  │  │  · stockHealth(...) - Ad-hoc filtered read (not cached)        │ │  │
│  │  │  Role-aware field masking: privileged fields null for          │ │  │
│  │  │  Guest/Vendor callers                                          │ │  │
│  │  │  Shared Redis cache keys with REST layer                       │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Inventory   │  │ Requisition  │  │   Vendor     │  │  Analytics   │   │
│  │  Service     │  │  Service     │  │  Service     │  │  Service     │   │
│  │              │  │              │  │              │  │              │   │
│  │ - Stock calc │  │ - Approval   │  │ - Excel      │  │ - Dashboard  │   │
│  │ - Reorder    │  │ - Workflow   │  │   parsing    │  │ - Heatmap    │   │
│  │ - Tracking   │  │ - Inventory  │  │ - Fuzzy      │  │ - Alerts     │   │
│  │              │  │   update     │  │   matching   │  │ - Caching    │   │
│  │ └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│  ┌──────┴─────────────────┴─────────────────┴─────────────────┴────────┐   │
│  │                      AI Agent Service                                │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  LangGraph ReAct Agent (Groq LLaMA 3.3 70B)                    │ │   │
│  │  │  - Natural language query processing                           │ │   │
│  │  │  - Multi-step reasoning                                        │ │   │
│  │  │  - Tool selection & execution                                  │ │   │
│  │  │  - Conversation history (last 6 messages)                      │ │   │
│  │  │  - Vector context injection (RAG)                              │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  7 Agent Tools (@tool decorator)                               │ │   │
│  │  │  1. get_inventory_overview()                                   │ │   │
│  │  │  2. get_critical_items(location, severity)                     │ │   │
│  │  │  3. get_stock_health(item, location)                           │ │   │
│  │  │  4. calculate_reorder_suggestions(location)                    │ │   │
│  │  │  5. get_location_summary(location_name)                        │ │   │
│  │  │  6. get_category_analysis(category)                            │ │   │
│  │  │  7. get_consumption_trends(item, location, days)               │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Audit Service                                                       │   │
│  │  - Logs all write operations (create, update, delete, approve)      │   │
│  │  - Tracks user, timestamp, action, entity, changes                  │   │
│  │  └──────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                                  │
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │  PostgreSQL          │  │  Upstash Redis       │  │  ChromaDB        │  │
│  │  (Neon)              │  │  (REST API)          │  │  (Local)         │  │
│  │                      │  │                      │  │                  │  │
│  │  Tables:             │  │  Keys:               │  │  Collections:    │  │
│  │  - users             │  │  - token_blacklist:* │  │  - chat_memory   │  │
│  │  - organizations     │  │  - login_attempts:*  │  │                  │  │
│  │  - locations         │  │  - analytics:*       │  │  Embeddings:     │  │
│  │  - items             │  │  - dashboard:*       │  │  - 384 dims      │  │
│  │  - inventory_trans   │  │                      │  │  - Semantic      │  │
│  │  - requisitions      │  │  TTL:                │  │    search        │  │
│  │  - requisition_items │  │  - 2-5 min (cache)   │  │  - Session-based │  │
│  │  - vendor_uploads    │  │  - 30 min (tokens)   │  │    context       │  │
│  │  - chat_sessions     │  │  - 15 min (lockout)  │  │                  │  │
│  │  - chat_messages     │  │                      │  │  Fallback:       │  │
│  │  - audit_logs        │  │  Fallback:           │  │  - Disabled      │  │
│  │                      │  │  - In-memory dict    │  │    gracefully    │  │
│  │  Features:           │  │    (dev only)        │  │                  │  │
│  │  - ACID compliance   │  │                      │  │                  │  │
│  │  - Foreign keys      │  │                      │  │                  │  │
│  │  - Indexes           │  │                      │  │                  │  │
│  │  - Connection pool   │  │                      │  │                  │  │
│  │  - Retry logic (3x)  │  │                      │  │                  │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **React Frontend** | User interface, 5 role-based portals (Super Admin, Admin, Manager, Staff, Vendor) + Guest Demo Mode, real-time WebSocket updates |
| **FastAPI Backend** | REST API (56 endpoints), authentication, business logic orchestration |
| **GraphQL Layer (Strawberry)** | Read-only analytics API at `/graphql/analytics` — 5 queries, role-aware field masking, shared Redis cache with REST |
| **AI Agent Service** | LangGraph ReAct agent with 7 inventory tools, natural language processing |
| **Analytics Service** | Dashboard stats, heatmaps, critical alerts with Redis caching — shared by REST and GraphQL |
| **Inventory Service** | Stock tracking, transaction management, reorder calculations |
| **Requisition Service** | Approval workflow, status management, inventory updates |
| **Vendor Service** | Excel parsing, fuzzy item matching, bulk transaction creation |
| **PostgreSQL** | Primary data store (users, inventory, transactions, requisitions) |
| **Upstash Redis** | Distributed cache, token blacklist, login attempt tracking |
| **ChromaDB** | Vector database for AI semantic memory and RAG |

---

## 6. Detailed Request/Response Flows

### 6.1 User Login Flow
```
User enters credentials
         ↓
Frontend → POST /api/auth/login
         ↓
┌────────────────────────────────────────┐
│  Auth Route                            │
│  1. Check login attempts (Redis)       │
│  2. If locked → 429 error              │
│  3. Query user from database           │
│  4. Verify password (Argon2)           │
│  5. If fail → increment attempts       │
│  6. If success:                        │
│     - Generate access token (30 min)   │
│     - Generate refresh token (7 days)  │
│     - Clear login attempts             │
│     - Create audit log                 │
└────────────────────────────────────────┘
         ↓
Response: {access_token, refresh_token, user}
         ↓
Frontend stores tokens in localStorage
         ↓
Frontend redirects to role-based portal
```
**Security Layers:**
- Rate limiting: 5 requests/minute
- Login lockout: 5 attempts → 15 min lockout
- Argon2 password hashing (GPU-resistant)
- Timing-attack prevention (DUMMY_HASH)
- Audit logging

### 6.2 AI Chatbot Query Flow
```
User asks: "What items are critical?"
         ↓
Frontend → POST /api/chat/query
         ↓
┌────────────────────────────────────────┐
│  Chat Route                            │
│  1. Validate JWT token                 │
│  2. Check rate limit (20/min)          │
│  3. Load conversation history (last 6) │
│  4. Query vector store for context     │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  Agent Service                         │
│  1. Build message context:             │
│     - System prompt                    │
│     - Vector context (RAG)             │
│     - Conversation history             │
│     - User question                    │
│  2. Invoke LangGraph ReAct agent       │
│  3. Agent decides which tools to call  │
│  4. Execute tools (e.g., get_critical) │
│  5. Agent synthesizes response         │
│  6. Timeout: 30 seconds                │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  Tool Execution                        │
│  get_critical_items(severity="CRITICAL")│
│  1. Query database with filters        │
│  2. Calculate stock levels             │
│  3. Return critical items list         │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  Save Response                         │
│  1. Save to chat_messages table        │
│  2. Save to ChromaDB (vector store)    │
│  3. Return response to user            │
└────────────────────────────────────────┘
         ↓
Frontend displays answer + suggested actions
```
**Performance:**
- Vector search: < 50ms
- LLM inference: 1-3 seconds (Groq)
- Total response time: 2-4 seconds

### 6.3 Requisition Approval Flow
```
Staff creates requisition
         ↓
Frontend → POST /api/requisition/create
         ↓
┌────────────────────────────────────────┐
│  Requisition Service                   │
│  1. Validate items exist               │
│  2. Create Requisition (PENDING)       │
│  3. Create RequisitionItems (line)     │
│  4. Save to database                   │
│  5. Create audit log                   │
└────────────────────────────────────────┘
         ↓
Manager receives notification (WebSocket)
         ↓
Manager reviews requisition
         ↓
Frontend → PUT /api/requisition/{id}/approve
         ↓
┌────────────────────────────────────────┐
│  Requisition Service                   │
│  1. Check user role (manager+)         │
│  2. Update status → APPROVED           │
│  3. For each item:                     │
│     - Create inventory transaction     │
│     - Update stock levels              │
│  4. Invalidate cache (analytics:*)     │
│  5. Create audit log                   │
└────────────────────────────────────────┘
         ↓
WebSocket broadcast to location
         ↓
Staff receives approval notification
```
**Transaction Safety:**
- Database transaction (rollback on error)
- Foreign key constraints
- Audit trail for compliance

### 6.4 Vendor Excel Upload Flow
```
Vendor uploads Excel file (50 items)
         ↓
Frontend → POST /api/vendor/upload-delivery
         ↓
┌────────────────────────────────────────┐
│  Vendor Service                        │
│  1. Parse Excel (openpyxl)             │
│  2. For each row:                      │
│     a. Extract: item_name, qty, batch  │
│     b. Fuzzy match item (RapidFuzz)    │
│        - Threshold: 85%                │
│        - Returns best match            │
│     c. Validate quantity > 0           │
│     d. Create transaction (received)   │
│     e. Track success/error             │
│  3. Create VendorUpload record         │
│  4. Invalidate cache                   │
│  5. Create audit log                   │
└────────────────────────────────────────┘
         ↓
Response: {total: 50, success: 48, errors: 2}
         ↓
Frontend shows success/error breakdown
         ↓
WebSocket alert to location (new stock)
```
**Error Handling:**
- Partial success (48/50 items)
- Error details per row
- Transaction per item (isolated failures)

### 6.5 Real-Time Alert Flow (WebSocket)
```
Stock level drops below threshold
         ↓
Inventory transaction created
         ↓
┌────────────────────────────────────────┐
│  Inventory Service                     │
│  1. Calculate new stock level          │
│  2. Check if critical (< reorder)      │
│  3. If critical:                       │
│     - Trigger WebSocket broadcast      │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  WebSocket Manager                     │
│  1. Get all connections for location   │
│  2. Broadcast alert message:           │
│     {                                  │
│       type: "critical_stock",          │
│       item: "Paracetamol",             │
│       location: "Main Pharmacy",       │
│       current: 5,                      │
│       reorder: 20                      │
│     }                                  │
└────────────────────────────────────────┘
         ↓
All connected clients receive alert
         ↓
Frontend shows toast notification
```
**WebSocket Features:**
- Connection per user session
- Location-based broadcasting
- Automatic reconnection
- Heartbeat ping/pong

### 6.6 Low-Stock Email Alert Flow
```
Stock level drops below threshold
         ↓
Inventory transaction created
         ↓
┌────────────────────────────────────────┐
│  Inventory Service                     │
│  1. Check if stock <= min_stock        │
│  2. Query active Admins & Managers     │
│  3. Spin up background daemon thread   │
│  4. Return HTTP response immediately   │
└────────────────────────────────────────┘
         ↓ (Asynchronous execution in background thread)
┌────────────────────────────────────────┐
│  Background Thread: NotificationSvc    │
│  1. Establish SMTP TLS connection      │
│  2. Build HTML alert template          │
│  3. Dispatch email to recipient list   │
│  4. Mask email PII and log completion  │
└────────────────────────────────────────┘
         ↓
Admins & Managers receive email warning
```
**Email Alerts Features:**
- **Zero Latency Impact:** Uses Python `threading.Thread(daemon=True)` to offload SMTP overhead, maintaining high response times.
- **PII Protection:** Leverages a `mask_email` security helper to ensure no plain-text emails are written to standard logs or diagnostic systems.
- **Isolated Transactions:** Exceptions raised by the email dispatch are caught at the thread level, meaning network or mail-server outages never rollback or halt inventory updates.

---

## 7. Authentication & Authorization Architecture

### 7.1 JWT Token Flow
```
┌─────────────────────────────────────────────────────────────────┐
│  Token Generation (Login)                                       │
│                                                                  │
│  1. User authenticates                                          │
│  2. Generate access token:                                      │
│     {                                                           │
│       sub: user_id,                                             │
│       username: "admin",                                        │
│       role: "admin",                                            │
│       type: "access",                                           │
│       exp: now + 30 minutes                                     │
│     }                                                           │
│  3. Generate refresh token:                                     │
│     {                                                           │
│       sub: user_id,                                             │
│       type: "refresh",                                          │
│       exp: now + 7 days                                         │
│     }                                                           │
│  4. Sign with SECRET_KEY (HS256)                                │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Token Validation (Every Request)                               │
│                                                                  │
│  1. Extract token from Authorization header                     │
│  2. Decode and verify signature                                 │
│  3. Check expiry                                                │
│  4. Verify type = "access"                                      │
│  5. Check token blacklist (Redis)                               │
│  6. Query user from database                                    │
│  7. Check user is_active                                        │
│  8. Inject user into request context                            │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Role-Based Access Control                                      │
│                                                                  │
│  Role Hierarchy:                                                │
│  super_admin (5) > admin (4) > manager (3) >                    │
│  staff (2) > vendor (1)                                         │
│                                                                  │
│  Endpoint Protection:                                           │
│  - /api/superadmin/* → super_admin only                         │
│  - /api/admin/* → admin+ (Management routes require admin auth)  │
│  - /api/requisition/approve/reject → manager+                   │
│  - /api/requisition/create → staff+                             │
│  - /api/vendor/* → vendor+                                      │
│  - GET /api/{inventory,requisition,chat,analytics}/* → Guest    │
│    Permitted (uses optional JWT validation; no 401 raises)      │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Multi-Tenancy Isolation
- Every table has an `org_id` column to isolate organization data.
- Every query filters by `org_id` automatically or within context dependency.
- Users can only access data belonging to their organization's `org_id`.
- The `super_admin` role can bypass this filter to perform cross-organization platform administration.

---

## 8. Tech Stack & Characteristics

### 8.1 Tech Stack Choices

#### Backend
| Technology | Why Chosen |
|------------|-----------|
| **FastAPI** | Async support, automatic OpenAPI docs, fast performance, Python ecosystem |
| **Strawberry GraphQL** | Code-first GraphQL for Python — integrates natively with FastAPI, supports role-aware resolvers and field-level nullable masking |
| **PostgreSQL** | ACID compliance, complex queries, JSON support, production-ready |
| **Upstash Redis** | Serverless Redis, REST API (no TCP), pay-per-request, global replication |
| **ChromaDB** | Vector database for semantic search and RAG context storage |
| **LangGraph** | Orchestrates ReAct agent workflows and structures tool execution state machines |
| **Groq** | Ultra-fast LLM inference (LLaMA 3.3 70B), cost-effective |

#### Frontend
| Technology | Why Chosen |
|------------|-----------|
| **React 19** | Modern UI capabilities, component reusability, large ecosystem |
| **Vite** | Fast hot-reloading (HMR) and optimized build times |
| **Tailwind CSS** | Rapid and consistent responsive styling |
| **Recharts** | Fully interactive charts tailored for analytics dashboards |

#### Infrastructure
| Technology | Why Chosen |
|------------|-----------|
| **Neon** | Serverless PostgreSQL with auto-scaling, instant branching, and automatic backups |
| **Render.com** | Zero-downtime deployment, health checks, automatic SSL |
| **Docker** | Standardized, isolated container environments for local dev and testing |

### 8.2 System Characteristics

| Characteristic | Value | Notes |
|----------------|-------|-------|
| **Architecture** | Modular Monolith | Clean boundaries, ready for extraction |
| **API Style** | REST + GraphQL + WebSocket | 56 REST endpoints, 5 GraphQL queries, 2 WebSocket endpoints |
| **Database** | PostgreSQL (ACID) | Single source of truth |
| **Caching** | Redis (Upstash) | 2-5 min TTL, pattern-based invalidation, shared between REST and GraphQL |
| **AI** | LangGraph ReAct | 7 tools, 30s timeout |
| **Auth** | JWT (HS256) | 30 min access, 7 days refresh |
| **Rate Limiting** | slowapi | 5-60 req/min, Redis-backed (REST only) |
| **Real-time** | WebSocket | Location-based broadcasting |
| **Deployment** | Single instance | Render.com free tier |
| **Scaling** | Vertical | Add RAM/CPU to single instance |
| **Background Jobs** | Daemon Threads | In-process email dispatch |
| **External APIs** | Groq, LangSmith | LLM inference, observability |

### 8.3 External Integrations
- **Groq API:** Handles LLM inference for chatbot queries using `llama-3.3-70b-versatile`.
- **LangSmith:** Monitors chain execution and traces tool performance.
- **SMTP Server:** Dispatches automated emails for password resets, invites, and critical stock notifications.
- **Google OAuth:** Validates external credentials to log in social users.
- *Placeholder Integrations:* Planned integrations include Twilio for SMS warnings and Stripe/Razorpay for automatic vendor replenishment invoices.

---

## 9. Architectural Decisions

### 9.1 Why Modular Monolith Over Microservices?
- **Team Size:** A single developer maintains the system. Building and managing microservices would introduce substantial operational overhead (network overhead, service discovery, pipeline management).
- **Domain Coupling:** Inventory tracking, requisitions, and analytics are tightly coupled. Extracting services prematurely would necessitate distributed transactions (Sagas) and complicate data consistency.
- **Deployment Simplicity:** A single Render instance runs the server, avoiding multi-container orchestrations.
- **Cost:** Keeps infrastructure footprints low (single PostgreSQL pool, single cache pool).
- **Performance:** In-process function execution runs in nanoseconds, eliminating HTTP serialization latency between sub-modules.
- **Modular Boundaries:** Designed with clean separation to ease extraction to microservices if scaling demands dictate:
  ```
  backend/app/
  ├── api/              # API routes and Pydantic schemas
  ├── application/      # Service orchestration (inventory, requisition, agent, analytics)
  ├── domain/           # Core calculations and business rules
  └── infrastructure/   # Persistence, caching, and database configuration
  ```

### 9.2 Background Jobs & Task Queues
- **Decision:** **Lightweight Async Dispatch (In-Process Daemon Threads)**
- **Rationale:** External brokers like Celery/RabbitMQ are bypassed to avoid high infrastructure costs and deployment complexity. For SMTP operations (which block for 1–3 seconds), Python's `threading.Thread(daemon=True)` executes tasks asynchronously.
- **Error Handling:** Outages on the mail server or integrations log warnings in the background but do not affect or roll back database transactions.
- **Scale Plan:** If alert volumes scale to thousands per minute, a Redis-backed lightweight queue like **ARQ** or **Celery** will replace the thread executor to ensure persistence across container restarts.

### 9.3 Security Architecture Decisions

#### 9.3.1 Password Hashing: Argon2
Winner of the Password Hashing Competition (PHC). GPU-resistant and memory-hard, protecting users from dictionary attacks better than legacy algorithms (bcrypt, PBKDF2).

#### 9.3.2 Token Blacklist & Rate Limiting
A Redis cache registers blacklisted JWT access tokens upon logout. Endpoints use `slowapi` to impose strict request throttling (5/min for auth, 20/min for AI queries) to counter brute-force attempts and control LLM compute costs.

#### 9.3.3 Database-level Multi-Tenancy
Queries dynamically filter by `org_id` in the database query layer rather than application-level logic. This limits security drift risks compared to memory-based filters.

---

## 10. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend (Vercel)                                              │
│  - React SPA                                                    │
│  - CDN distribution                                             │
│  - Auto-deploy from GitHub                                      │
│                                                                  │
│  Backend (Render.com)                                           │
│  - FastAPI + Gunicorn + Uvicorn                                 │
│  - 3 workers                                                    │
│  - Auto-deploy from GitHub                                      │
│  - Health checks                                                │
│                                                                  │
│  Database (Neon)                                                │
│  - Managed PostgreSQL                                           │
│  - Automatic backups                                            │
│  - Connection pooling                                           │
│                                                                  │
│  Cache (Upstash Redis)                                          │
│  - Serverless Redis                                             │
│  - Global replication                                           │
│  - REST API                                                     │
│                                                                  │
│  Vector DB (ChromaDB)                                           │
│  - Local persistent storage                                     │
│  - Mounted volume                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Key Design Patterns

| Pattern | Where Used | Why |
|---------|-----------|-----|
| **Repository Pattern** | Data access layer (`user_repo`, etc.) | Decouples ORM queries from business logic, simplifying testing and making data sources swap-ready |
| **Dependency Injection** | FastAPI `Depends()` | Promotes loose coupling, facilitates unit testing through mock dependencies, and controls connection scopes |
| **Service Layer** | Business logic files | Isolates transactional orchestrations from routing logic |
| **ReAct Agent** | Chat system (`agent_service`) | Powers an LLM reasoning-action loop to execute multi-step tools based on prompt contexts |
| **CQRS (Light)** | Dashboard analytics — REST + GraphQL reads separated from writes | Isolates write operations from read-heavy analytics calculations served via REST and the GraphQL layer |
| **Event-driven** | WebSocket modules | Pushes live notifications to active frontends without polling overhead |
| **Role-aware Resolvers** | GraphQL analytics layer | Field-level null masking enforces RBAC at the data layer — Guest/Vendor see stock status but not operational forecasting fields |

---

## 12. Non-Functional Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| **Availability** | 99.5% uptime | Endpoint health checks, database reconnection retry loops, and safe fallback systems |
| **Performance** | < 200ms API response | Caching reads in Redis with a 2-5 min TTL, database indexing, and query optimizations |
| **Scalability** | 100 concurrent users | Stateless backend layout, async FastAPI event loops, and lightweight connection pool sizes |
| **Security** | OWASP Top 10 compliance | JWT verification, Argon2 hashes, Redis blacklisting, and SQL injection safety via SQLAlchemy |
| **Data Integrity** | Zero data loss | Strict PostgreSQL foreign keys and atomic ACID transaction blocks |
| **Observability** | Full execution tracing | Python standard JSON logs, unique `X-Request-ID` headers, and optional LangSmith tracing |

---

## 13. Scalability & Data Flow Patterns

### 13.1 Data Flow Patterns

#### Read-Heavy (Analytics — REST)
```
Request → Check Redis cache → If miss, query DB → Cache result → Return
```

#### Read-Heavy (Analytics — GraphQL)
```
Request → JWT optional auth → Check Redis (shared keys) → If miss, call AnalyticsService
       → Apply role-aware field masking → Return typed Strawberry objects
```

#### Write-Heavy (Inventory Transactions)
```
Request → Validate → Write to DB → Invalidate cache (analytics:*) → Audit log → WebSocket broadcast
```

#### AI Query (RAG)
```
Request → Load history → Query vector DB → Build context → LLM inference → Save response
```

#### Real-time (WebSocket)
```
Event → WebSocket manager → Broadcast to location → All clients receive
```

### 13.2 Scalability Considerations
- **Neon PG Limits:** Free tier constraints (~500MB DB capacity, 20 max pool connections). Vertical scale triggers are defined when telemetry indicators show connection exhausts.
- **WebSocket Broadcasting:** Single-instance dependent. To expand horizontally, a Redis Pub/Sub adapter will distribute messages to WebSocket listeners across cluster nodes.
- **LLM Rate Throttling:** Groq limits LLM throughput. Production mitigations involve queuing, failover LLMs (e.g. Gemini, OpenAI), and aggressive semantic caching of common questions.

---

## 14. Future Enhancements

### Phase 2 (Next 6 months)
- Barcode scanning integration (mobile camera parsing)
- Predictive analytics (ML models for demand forecasting)
- Mobile app (React Native port)
- Automated reordering based on thresholds
- Integration with hospital ERP systems

### Phase 3 (Next 12 months)
- Multi-language support
- Advanced reporting (custom dashboards)
- Supplier management portal
- Batch/lot tracking for compliance
- Expiry date management

---

## 15. Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| **User Adoption** | 80% of staff using daily | TBD |
| **Stockout Reduction** | 50% fewer critical stockouts | TBD |
| **Time Saved** | 10 hours/week per manager | TBD |
| **AI Accuracy** | 90% correct answers | TBD |
| **System Uptime** | 99.5% | TBD |
| **Response Time** | < 200ms (p95) | TBD |

---

**Document Status:** ✅ Complete  
**Last Reviewed:** June 26, 2026  
**Next Review:** Every 3 months
