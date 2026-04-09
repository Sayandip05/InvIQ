# Smart Inventory Assistant

AI-assisted inventory management for healthcare supply chains.

## Quick Start

### Backend

```bash
# Clone and setup
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Seed sample data
python ..\database\seed_data.py

# Run server
uvicorn app.main:app --reload --port 8000
```

### URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Environment Variables

Create `backend/.env` from `.env.example`:

```env
DATABASE_PATH=../database/smart_inventory.db
DATABASE_URL=  # Set for PostgreSQL (Supabase) in production
ENVIRONMENT=development
GROQ_API_KEY=<your-key>
LANGCHAIN_API_KEY=<optional>
CORS_ORIGINS=http://localhost:5173
SECRET_KEY=<change-in-production>
```

---

## Repository Structure

```
inviq/
├── backend/
│   └── app/
│       ├── main.py                              # FastAPI entry point
│       ├── api/
│       │   ├── routes/
│       │   │   ├── admin.py                 # Admin dashboard, PDF reports
│       │   │   ├── analytics.py             # Heatmap, alerts, summary
│       │   │   ├── auth.py                  # Login, register, user management
│       │   │   ├── chat.py                  # AI chatbot query, history
│       │   │   ├── inventory.py             # Locations, items, transactions
│       │   │   ├── requisition.py            # Create, approve, reject
│       │   │   ├── vendor.py                # Excel upload
│       │   │   ├── superadmin.py            # Platform management
│       │   │   └── websocket.py             # Real-time alerts
│       │   └── schemas/
│       │       ├── chat_schemas.py
│       │       ├── inventory_schemas.py
│       │       ├── requisition_schemas.py
│       │       └── auth_schemas.py
│       ├── application/                        # Business logic
│       │   ├── agent_tools.py                 # LangGraph @tool wrappers
│       │   ├── agent_service.py               # ReAct agent orchestration
│       │   ├── analytics_service.py           # Dashboard + Redis caching
│       │   ├── inventory_service.py          # Transaction CRUD
│       │   ├── vendor_service.py             # Excel parsing + fuzzy match
│       │   ├── requisition_service.py        # Workflow
│       │   ├── cache_service.py              # Redis helpers
│       │   └── audit_service.py              # Audit logging
│       ├── domain/                            # Pure logic (no framework deps)
│       │   ├── calculations.py                 # Reorder formula, health colors
│       │   └── agent/prompts.py              # System prompt text
│       ├── infrastructure/                    # External integrations
│       │   ├── database/
│       │   │   ├── connection.py             # SQLAlchemy engine/session
│       │   │   ├── models.py                # ORM classes
│       │   │   ├── queries.py               # Complex SQL (stock health, alerts)
│       │   │   ├── inventory_repo.py
│       │   │   ├── requisition_repo.py
│       │   │   ├── user_repo.py
│       │   │   └── audit_repo.py
│       │   ├── cache/
│       │   │   ├── redis_client.py
│       │   │   ├── token_blacklist.py
│       │   │   └── login_attempts.py
│       │   └── vector_store/
│       │       └── vector_store.py           # ChromaDB semantic memory
│       └── core/                             # Framework plumbing
│           ├── config.py                     # Settings from .env
│           ├── dependencies.py               # FastAPI Depends() factories
│           ├── security.py                   # JWT encode/decode
│           ├── rate_limiter.py               # slowapi setup
│           ├── exceptions.py
│           ├── error_handlers.py
│           ├── logging_config.py
│           └── middleware/request_logger.py
├── database/
│   ├── schema.sql                           # DB schema reference
│   ├── seed_data.py                        # Sample data
│   └── smart_inventory.db                   # SQLite file (dev)
├── docs/
│   ├── system-architecture.md               # Architecture, layers, ADR
│   ├── HLD.md                              # Modules, APIs, entities
│   ├── LLD.md                              # Schema, sequence diagrams
│   ├── deployment.md                        # Docker, CI/CD, Render
│   ├── auth_management.md                   # Auth workflow
│   └── INTERVIEW_PREP_PROMPT.md
├── Dockerfile
├── docker-compose.yml
├── cicd.yaml
├── requirements.txt
├── SETUP.md
└── README.md
```
smart-inventory-assistant/
├── backend/
│   └── app/
│       ├── main.py                              # FastAPI entry point
│       ├── api/
│       │   ├── routes/
│       │   │   ├── admin.py                 # Super admin dashboard
│       │   │   ├── analytics.py             # Heatmap, alerts, summary
│       │   │   ├── auth.py                  # Login, register, user management
│       │   │   ├── chat.py                  # Chatbot query, history
│       │   │   ├── inventory.py             # Locations, items, transactions
│       │   │   └── requisition.py            # Create, approve, reject
│       │   └── schemas/
│       │       ├── chat_schemas.py
│       │       ├── inventory_schemas.py
│       │       └── requisition_schemas.py
│       ├── application/                        # Business logic
│       │   ├── agent_tools.py                 # LangGraph @tool wrappers
│       │   ├── analytics_service.py
│       │   ├── inventory_service.py
│       │   └── requisition_service.py
│       ├── domain/                            # Pure logic (no framework deps)
│       │   ├── calculations.py                 # Reorder formula, health colors
│       │   └── agent/prompts.py              # System prompt text
│       ├── infrastructure/                    # External integrations
│       │   ├── database/
│       │   │   ├── connection.py             # SQLAlchemy engine/session
│       │   │   ├── models.py                # ORM classes
│       │   │   ├── queries.py               # Complex SQL (stock health, alerts)
│       │   │   ├── inventory_repo.py
│       │   │   └── requisition_repo.py
│       │   └── vector_store/
│       │       └── vector_store.py           # ChromaDB semantic memory
│       └── core/                             # Framework plumbing
│           ├── config.py                     # Settings from .env
│           ├── dependencies.py               # FastAPI Depends() factories
│           ├── error_handlers.py
│           ├── exceptions.py
│           ├── logging_config.py
│           └── middleware/request_logger.py
├── database/
│   ├── schema.sql                           # DB schema reference
│   ├── seed_data.py                        # Sample data
│   └── smart_inventory.db                   # SQLite file
├── frontend/main-dashboard/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── admin/                      # Dashboard, Inventory, Requisitions, Chatbot
│   │   │   ├── staff/                      # StaffRequisition
│   │   │   └── vendor/                     # DataEntry
│   │   ├── components/layout/              # AdminLayout, Sidebar
│   │   └── services/api.js                  # Axios HTTP client
│   └── package.json
├── docs/
│   ├── memory.md                            # Implementation status & roadmap
│   ├── system-architecture.md               # Architecture, layers, ADR summary
│   ├── HLD.md                              # Modules, APIs, entities, user journeys
│   ├── LLD.md                              # Schema, sequence diagrams, edge cases
│   └── deployment.md                        # Docker, CI/CD, environment configs
├── Dockerfile
├── docker-compose.yml
├── cicd.yaml
├── requirements.txt
└── README.md
```

---

## Architecture

Clean Architecture with strict layer separation:

| Layer | Rule | Examples |
|-------|------|----------|
| `domain/` | Zero framework imports | `calculations.py`, `prompts.py` |
| `infrastructure/` | Only domain + stdlib | `connection.py`, `models.py`, `vector_store.py` |
| `application/` | Calls both domain + infra | `*_service.py`, `agent_tools.py` |
| `api/` | Only calls application + core | `routes/`, `schemas/` |

---

## Module Audit (27/27 Implemented)

All modules implemented:
- FastAPI REST API with 7 route groups (50+ endpoints)
- JWT auth + RBAC (6 roles) + login lockout + audit trail + logout + token blacklist
- Redis caching (analytics TTL) + token blacklist + rate limiting
- LangGraph AI agent (Groq LLM) with ChromaDB semantic memory
- WebSocket real-time stock alerts (`/ws/alerts`)
- Automated testing (pytest, 29 tests)
- Docker (multi-stage build + docker-compose)
- CI/CD (GitHub Actions with PostgreSQL service)
- Graceful shutdown via lifespan context manager
- SQLAlchemy ORM + Repository pattern + PostgreSQL (Supabase)
- Vendor Excel upload with fuzzy matching
- PDF report generation (ReportLab)
- Multi-tenancy (org_id on every entity)
- 6 portal support (Super Admin, Admin, Manager, Staff, Vendor, Viewer)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Auth | JWT (python-jose), pwdlib (argon2), RBAC (6 roles) |
| AI | LangGraph, Groq (LLaMA-3.3-70b), ChromaDB (memory) |
| Caching | Redis (Upstash) + in-memory fallback |
| Security | Rate limiting (slowapi), token blacklist |
| Database | PostgreSQL (Supabase) |
| Excel | openpyxl + RapidFuzz |
| PDF | ReportLab |
| Real-time | WebSocket (FastAPI native) |

---

## Key Notes

- JWT authentication with RBAC (6 roles) is fully implemented.
- Token blacklist on logout for security.
- Redis caching for analytics with automatic invalidation.
- Rate limiting via slowapi (5/min login, 30/min analytics).
- All 27 modules implemented and documented.
- See `docs/deployment.md` for deployment guide.
