# System Architecture - InvIQ

**Version:** 1.0  
**Last Updated:** April 30, 2026  
**Author:** Sayandip Bar

---

## 🏗️ Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  React 19 SPA (Vite)                                                 │  │
│  │  - 6 Role-Based Portals (Super Admin, Admin, Manager, Staff,        │  │
│  │    Vendor, Viewer)                                                   │  │
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
│  │  FastAPI Application (Python 3.11)                                   │  │
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
│  │  │  - Role-based access control (6-tier hierarchy)                │ │  │
│  │  │  - Multi-tenancy (org_id isolation)                            │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  API Routes (56 endpoints)                                     │ │  │
│  │  │  /api/auth/*        - Authentication (21 endpoints)            │ │  │
│  │  │  /api/inventory/*   - Inventory management (9 endpoints)       │ │  │
│  │  │  /api/requisition/* - Requisition workflow (8 endpoints)       │ │  │
│  │  │  /api/chat/*        - AI chatbot (5 endpoints)                 │ │  │
│  │  │  /api/analytics/*   - Dashboard analytics (2 endpoints)        │ │  │
│  │  │  /api/vendor/*      - Vendor uploads (3 endpoints)             │ │  │
│  │  │  /api/superadmin/*  - Super admin (6 endpoints)                │ │  │
│  │  │  /ws                - WebSocket (2 endpoints)                  │ │  │
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
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
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
│  └──────────────────────────────────────────────────────────────────────┘   │
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
│  │  - chat_messages     │  │                      │  │                  │  │
│  │  - audit_logs        │  │  Fallback:           │  │  Fallback:       │  │
│  │                      │  │  - In-memory dict    │  │  - Disabled      │  │
│  │  Features:           │  │    (dev only)        │  │    gracefully    │  │
│  │  - ACID compliance   │  │                      │  │                  │  │
│  │  - Foreign keys      │  │                      │  │                  │  │
│  │  - Indexes           │  │                      │  │                  │  │
│  │  - Connection pool   │  │                      │  │                  │  │
│  │  - Retry logic (3x)  │  │                      │  │                  │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request/Response Flow for Key Features

### 1. User Login Flow

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

---

### 2. AI Chatbot Query Flow

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

---

### 3. Requisition Approval Flow

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

---

### 4. Vendor Excel Upload Flow

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

---

### 5. Real-Time Alert Flow (WebSocket)

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

---

## 🔐 Authentication & Authorization Flow

### JWT Token Flow

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
│  super_admin (6) > admin (5) > manager (4) >                    │
│  staff (3) > vendor (2) > viewer (1)                            │
│                                                                  │
│  Endpoint Protection:                                           │
│  - /api/superadmin/* → super_admin only                         │
│  - /api/admin/* → admin+                                        │
│  - /api/requisition/approve → manager+                          │
│  - /api/requisition/create → staff+                             │
│  - /api/vendor/* → vendor+                                      │
│  - /api/analytics/* → viewer+                                   │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Multi-Tenancy Isolation                                        │
│                                                                  │
│  1. Every query filters by org_id                               │
│  2. User can only access their organization's data              │
│  3. Super admin can access all organizations                    │
│  4. Database-level isolation (not app-level)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚫 Background Jobs & Task Queues

**Status:** ❌ **NOT IMPLEMENTED**

InvIQ uses a **synchronous request-response** architecture. There are:
- ❌ No Celery workers
- ❌ No background job queues
- ❌ No async task processing
- ❌ No scheduled cron jobs

**Why No Background Jobs?**
1. **Simplicity** - Easier to deploy and debug for a resume project
2. **Real-time requirements** - Users expect immediate responses
3. **Low volume** - Current scale doesn't require async processing
4. **WebSocket** - Real-time updates handled via WebSocket, not polling
5. **Portfolio scope** - Demonstrates core architecture without operational complexity

**When Background Jobs Would Be Needed:**
- Email sending at scale (currently synchronous, acceptable for demo)
- Large report generation (PDF exports currently in-request)
- Batch data imports (vendor uploads currently synchronous)
- Scheduled analytics (daily/weekly reports)
- Notification delivery (WhatsApp, SMS - currently placeholders)

**Recommended Implementation (Production):**
- FastAPI BackgroundTasks (simple, built-in)
- Celery + Redis (robust, scalable)
- ARQ (async, Redis-based, Python-native)

---

## 🔌 External Integrations

### Currently Implemented:
1. **Groq API** ✅ - LLM inference (LLaMA 3.3 70B) for AI chatbot
2. **LangSmith** ✅ (optional) - AI observability and tracing
3. **SMTP** ✅ (optional) - Email notifications (Gmail, etc.)
4. **Google OAuth** ✅ (optional) - Social login authentication

### Placeholder/Future Integrations:
> **Note:** These are architectural placeholders for a production system. Not implemented in this resume project.

- **WhatsApp Business API** 📱 - Real-time stock alerts to staff mobile
- **SMS Gateway (Twilio)** 📲 - Critical shortage notifications
- **Payment Gateway (Razorpay/Stripe)** 💳 - Vendor invoice payments
- **Hospital ERP Integration** 🏥 - Sync with existing hospital systems
- **Email Marketing (SendGrid)** 📧 - Bulk notifications to vendors

**Why Placeholders?**
This is a portfolio/resume project demonstrating architecture and implementation skills. In a production deployment, these integrations would be added based on client requirements and budget.

---

## 🛡️ Security Architecture Decisions

### 1. Password Hashing: Argon2
**Why:** Winner of Password Hashing Competition, GPU-resistant, memory-hard

**Alternatives Rejected:**
- ❌ bcrypt - Vulnerable to GPU attacks
- ❌ PBKDF2 - Faster to crack with specialized hardware
- ❌ SHA256 - Not designed for passwords

---

### 2. JWT Tokens: HS256 (Symmetric)
**Why:** Simple, fast, no key distribution needed

**Security Measures:**
- Token type enforcement (access vs refresh)
- Short expiry (30 min access, 7 days refresh)
- Token rotation on refresh
- Blacklist on logout (Redis)

**Alternatives Rejected:**
- ❌ RS256 (asymmetric) - Overkill for single backend
- ❌ Session cookies - Harder for mobile apps

---

### 3. Rate Limiting: slowapi + Redis
**Why:** Prevents brute force, DDoS, API abuse

**Tiered Limits:**
- Auth endpoints: 5/minute (brute force protection)
- Chat endpoints: 20/minute (LLM cost control)
- Default: 60/minute (general protection)

**Fallback:** In-memory (per-worker) when Redis unavailable

---

### 4. Login Lockout: Redis-backed
**Why:** Distributed lockout across workers

**Configuration:**
- 5 failed attempts → 15 min lockout
- Sliding window (TTL resets on each attempt)
- In-memory fallback for dev

---

### 5. Token Blacklist: Redis
**Why:** Immediate logout invalidation

**How:**
- On logout, add token to blacklist with TTL = token expiry
- Every request checks blacklist before accepting token
- Prevents "logout but token still works" vulnerability

---

### 6. Multi-Tenancy: Database-level
**Why:** Strongest isolation, prevents data leaks

**Implementation:**
- Every table has org_id column
- Every query filters by org_id
- Foreign keys enforce org_id consistency
- Super admin can bypass (for platform management)

**Alternatives Rejected:**
- ❌ App-level filtering - Easy to forget, security risk
- ❌ Separate databases - Too complex, expensive

---

### 7. Audit Logging: Database
**Why:** Compliance, forensics, debugging

**What's Logged:**
- All write operations (create, update, delete, approve)
- User, timestamp, action, entity, changes
- Immutable (no updates/deletes)

---

## 🏛️ Why Modular Monolith Over Microservices?

### Decision: Modular Monolith

**Reasons:**

#### 1. **Team Size: 1 Developer**
- Microservices require 3-5 developers minimum
- Operational overhead (deployment, monitoring, debugging)
- Communication overhead (API contracts, versioning)

#### 2. **Domain Coupling**
- Inventory, requisitions, and analytics are tightly coupled
- Splitting would require distributed transactions
- Network calls add latency and failure points

#### 3. **Deployment Simplicity**
- Single deployment unit (one Render dyno)
- No orchestration (Kubernetes, Docker Swarm)
- Easier rollback (single version)

#### 4. **Development Speed**
- Shared code (no duplication)
- Refactoring is easy (no API versioning)
- Single codebase to understand

#### 5. **Cost**
- Free tier: 1 backend instance
- Microservices: 5+ instances (auth, inventory, requisition, analytics, gateway)
- Database connections: 1 pool vs 5 pools

#### 6. **Performance**
- In-process calls (nanoseconds)
- Microservices: HTTP calls (milliseconds)
- No serialization overhead

---

### Modular Boundaries (Ready for Extraction)

```
backend/app/
├── api/              # API layer (routes, schemas)
├── application/      # Business logic (services)
├── domain/           # Domain logic (calculations, rules)
└── infrastructure/   # External dependencies (DB, cache, vector)
```

**If we need microservices later:**
1. Extract `application/inventory_service.py` → Inventory Service
2. Extract `application/requisition_service.py` → Requisition Service
3. Extract `application/agent_service.py` → AI Service
4. Keep clean boundaries (no circular dependencies)

---

### When to Switch to Microservices?

**Triggers:**
- Team grows to 10+ developers
- Different scaling needs (AI service needs GPU, inventory doesn't)
- Different tech stacks (Python for AI, Go for high-throughput)
- Regulatory isolation (PII data in separate service)
- Independent deployment cadence (AI updates daily, inventory weekly)

**Current Status:** None of these apply → Monolith is correct choice

---

## 📊 System Characteristics

| Characteristic | Value | Notes |
|----------------|-------|-------|
| **Architecture** | Modular Monolith | Clean boundaries, ready for extraction |
| **API Style** | REST + WebSocket | 56 REST endpoints, 2 WebSocket endpoints |
| **Database** | PostgreSQL (ACID) | Single source of truth |
| **Caching** | Redis (Upstash) | 2-5 min TTL, pattern-based invalidation |
| **AI** | LangGraph ReAct | 7 tools, 30s timeout |
| **Auth** | JWT (HS256) | 30 min access, 7 days refresh |
| **Rate Limiting** | slowapi | 5-60 req/min, Redis-backed |
| **Real-time** | WebSocket | Location-based broadcasting |
| **Deployment** | Single instance | Render.com free tier |
| **Scaling** | Vertical | Add RAM/CPU to single instance |
| **Background Jobs** | None | Synchronous request-response |
| **External APIs** | Groq, LangSmith | LLM inference, observability |

---

## 🔄 Data Flow Patterns

### 1. Read-Heavy (Analytics)
```
Request → Check Redis cache → If miss, query DB → Cache result → Return
```

### 2. Write-Heavy (Inventory Transactions)
```
Request → Validate → Write to DB → Invalidate cache → Audit log → WebSocket broadcast
```

### 3. AI Query (RAG)
```
Request → Load history → Query vector DB → Build context → LLM inference → Save response
```

### 4. Real-time (WebSocket)
```
Event → WebSocket manager → Broadcast to location → All clients receive
```

---

## 📈 Scalability Considerations

### Current Limits (Free Tier)
- **Concurrent users:** ~100
- **Requests/second:** ~50
- **Database size:** 500MB
- **Redis commands:** 10,000/day

### Scaling Strategy
1. **Vertical scaling** (add RAM/CPU) - Up to 1,000 users
2. **Database read replicas** - Separate read/write
3. **Redis clustering** - Distribute cache
4. **CDN for frontend** - Already done (Vercel)
5. **Horizontal scaling** - Multiple backend instances (requires sticky sessions for WebSocket)

### Bottlenecks
1. **LLM API** - Groq rate limits (30 req/min free tier)
2. **Database connections** - Connection pool (max 20)
3. **WebSocket** - Single instance (no broadcasting across instances)

---

**Document Status:** ✅ Complete  
**Last Reviewed:** April 30, 2026  
**Next Review:** Every 3 months
