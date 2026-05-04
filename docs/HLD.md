# High-Level Design (HLD) - InvIQ Smart Inventory Assistant

**Version:** 2.0  
**Last Updated:** April 30, 2026  
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
6. **Multi-tenancy** supporting multiple organizations

---

## 4. Major Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  React SPA (6 Role-Based Portals + Landing Page)                │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST + WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                           │
│  FastAPI (56 endpoints) + Rate Limiting + JWT Auth              │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Business   │  │  AI Agent    │  │  Analytics   │
│   Logic      │  │  Service     │  │  Service     │
│              │  │              │  │              │
│ Inventory    │  │ LangGraph    │  │ Dashboard    │
│ Requisition  │  │ 7 Tools      │  │ Heatmap      │
│ Vendor       │  │ ChromaDB RAG │  │ Alerts       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │ Upstash Redis│  │  ChromaDB    │         │
│  │  (Neon)      │  │  (REST API)  │  │  (Vector DB) │         │
│  │              │  │              │  │              │         │
│  │ Transactions │  │ Cache        │  │ Semantic     │         │
│  │ Users        │  │ Token List   │  │ Memory       │         │
│  │ Requisitions │  │ Rate Limits  │  │ RAG Context  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **React Frontend** | User interface, 6 role-based portals (Super Admin, Admin, Manager, Staff, Vendor, Viewer) + Landing page, real-time WebSocket updates |
| **FastAPI Backend** | REST API (56 endpoints), authentication, business logic orchestration |
| **AI Agent Service** | LangGraph ReAct agent with 7 inventory tools, natural language processing |
| **Analytics Service** | Dashboard stats, heatmaps, critical alerts with Redis caching |
| **Inventory Service** | Stock tracking, transaction management, reorder calculations |
| **Requisition Service** | Approval workflow, status management, inventory updates |
| **Vendor Service** | Excel parsing, fuzzy item matching, bulk transaction creation |
| **PostgreSQL** | Primary data store (users, inventory, transactions, requisitions) |
| **Upstash Redis** | Distributed cache, token blacklist, login attempt tracking |
| **ChromaDB** | Vector database for AI semantic memory and RAG |

---

## 5. Data Flow Examples

### Flow 1: User Asks AI Chatbot
```
User: "What items are critical right now?"
  ↓
Frontend → POST /api/chat/query
  ↓
Chat Route → Agent Service
  ↓
LangGraph ReAct Agent
  ↓ (decides which tools to call)
Tool: get_critical_items(severity="CRITICAL")
  ↓
Database Query → Returns critical items
  ↓
Agent synthesizes natural language response
  ↓
Response saved to DB + ChromaDB (for future RAG)
  ↓
Frontend displays answer + suggested actions
```

### Flow 2: Staff Creates Requisition
```
Staff: Creates requisition for 100 Paracetamol
  ↓
Frontend → POST /api/requisition/create
  ↓
Requisition Service validates items
  ↓
Creates Requisition (status: PENDING)
  ↓
Creates RequisitionItems (line items)
  ↓
Saves to PostgreSQL
  ↓
Audit log created
  ↓
Manager receives notification
  ↓
Manager approves → Status: APPROVED
  ↓
Inventory Service creates transaction (received stock)
  ↓
Cache invalidated (analytics:*)
  ↓
WebSocket alert sent to location
```

### Flow 3: Vendor Uploads Delivery
```
Vendor: Uploads Excel file (50 items)
  ↓
Frontend → POST /api/vendor/upload-delivery
  ↓
Vendor Service parses Excel (openpyxl)
  ↓
For each row:
  - Fuzzy match item name (RapidFuzz, 85% threshold)
  - Validate quantity > 0
  - Create inventory transaction (received)
  ↓
VendorUpload record saved (success/error counts)
  ↓
Response: {total: 50, success: 48, errors: 2}
  ↓
Frontend shows success/error breakdown
```

---

## 6. Tech Stack Choices

### Backend
| Technology | Why Chosen |
|------------|-----------|
| **FastAPI** | Async support, automatic OpenAPI docs, fast performance, Python ecosystem |
| **PostgreSQL** | ACID compliance, complex queries, JSON support, production-ready |
| **Upstash Redis** | Serverless Redis, REST API (no TCP), pay-per-request, global replication |
| **ChromaDB** | Open-source vector DB, local-first, no external dependencies |
| **LangGraph** | State machine for AI agents, tool calling, ReAct pattern support |
| **Groq** | Fast LLM inference (LLaMA 3.3 70B), cost-effective, low latency |

### Frontend
| Technology | Why Chosen |
|------------|-----------|
| **React 19** | Component reusability, large ecosystem, concurrent rendering |
| **Vite** | Fast dev server, optimized builds, HMR |
| **Tailwind CSS** | Utility-first, rapid prototyping, consistent design |
| **Recharts** | React-native charts, responsive, customizable |

### Infrastructure
| Technology | Why Chosen |
|------------|-----------|
| **Neon** | Managed PostgreSQL, free tier, automatic backups, serverless scaling |
| **Render.com** | Free tier, auto-deploy from GitHub, zero-config SSL |
| **Docker** | Consistent environments, easy local development |

---

## 7. Architecture Decisions

### Why Modular Monolith (Not Microservices)?
- **Team Size:** 1 developer - microservices add unnecessary complexity
- **Deployment:** Single Render dyno - no orchestration overhead
- **Domain:** Tightly coupled (inventory + requisitions + analytics)
- **Future:** Can extract services later if needed - boundaries are clean

### Why LangGraph ReAct Agent (Not Rule-Based)?
- **Flexibility:** LLM decides which tools to call based on question
- **Multi-step reasoning:** Can chain multiple tool calls
- **Natural language:** Understands intent, not just keywords
- **Graceful fallback:** Rule-based system still works if LLM unavailable

### Why Upstash Redis (Not Local Redis)?
- **Serverless:** No server management, pay-per-request
- **REST API:** Works in serverless/edge environments
- **Global:** Multi-region replication for low latency
- **Fallback:** In-memory cache works if Redis unavailable

---

## 8. Scope

### ✅ In Scope
- Multi-location inventory tracking
- AI-powered natural language queries
- Requisition approval workflow
- Vendor Excel upload integration
- Real-time stock alerts (WebSocket)
- Role-based access control (6 roles: super_admin, admin, manager, staff, vendor, viewer)
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

## 9. Non-Functional Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| **Availability** | 99.5% uptime | Health checks, database retry logic, graceful degradation |
| **Performance** | < 200ms API response | Redis caching (2-5 min TTL), connection pooling, indexed queries |
| **Scalability** | 100 concurrent users | Async FastAPI, horizontal scaling ready, stateless design |
| **Security** | OWASP Top 10 | JWT auth, Argon2 hashing, rate limiting, token blacklist, audit logs |
| **Data Integrity** | Zero data loss | PostgreSQL ACID, transaction rollback, foreign key constraints |
| **Observability** | Full traceability | Structured logging, LangSmith tracing, audit trail, request IDs |

---

## 10. Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Network                                               │
│  - HTTPS only (TLS 1.2+)                                        │
│  - CORS whitelist                                               │
│  - Rate limiting (slowapi: 5-60 req/min)                        │
│                                                                  │
│  Layer 2: Authentication                                        │
│  - JWT tokens (access: 30min, refresh: 7 days)                 │
│  - Argon2 password hashing (GPU-resistant)                      │
│  - Token rotation on refresh                                    │
│  - Token blacklist on logout (Redis)                            │
│  - Login lockout (5 attempts → 15 min)                          │
│                                                                  │
│  Layer 3: Authorization                                         │
│  - Role hierarchy (super_admin > admin > manager > staff)       │
│  - Endpoint-level RBAC                                          │
│  - Resource ownership checks                                    │
│  - Multi-tenancy isolation (org_id filter)                      │
│                                                                  │
│  Layer 4: Data                                                  │
│  - SQL injection prevention (parameterized queries)             │
│  - Input validation (Pydantic schemas)                          │
│  - Output sanitization                                          │
│  - Audit logging (all write operations)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Deployment Architecture

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

## 12. Key Design Patterns

| Pattern | Where Used | Why |
|---------|-----------|-----|
| **Repository Pattern** | Data access layer | Abstracts database, enables testing, swappable storage |
| **Dependency Injection** | FastAPI Depends() | Testable, loose coupling, request-scoped resources |
| **Service Layer** | Business logic | Separates orchestration from data access |
| **ReAct Agent** | AI chatbot | Reasoning + Acting loop for multi-step queries |
| **CQRS (light)** | Analytics | Separate read models with caching |
| **Event-driven** | WebSocket alerts | Real-time updates without polling |
| **Multi-tenancy** | org_id filter | Data isolation at database level |

---

## 13. Future Enhancements

### Phase 2 (Next 6 months)
- Barcode scanning integration
- Predictive analytics (ML models for demand forecasting)
- Mobile app (React Native)
- Automated reordering based on thresholds
- Integration with hospital ERP systems

### Phase 3 (Next 12 months)
- Multi-language support
- Advanced reporting (custom dashboards)
- Supplier management portal
- Batch/lot tracking for compliance
- Expiry date management

---

## 14. Success Metrics

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
**Review Date:** Every 3 months  
**Next Review:** July 30, 2026
