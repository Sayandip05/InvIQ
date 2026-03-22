# System Architecture

**Project:** Smart Inventory Assistant  
**Updated:** March 20, 2026

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SMART INVENTORY ASSISTANT                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐            │
│   │   Vendor UI     │      │   Staff UI      │      │   Admin UI      │            │
│   │  (Data Entry)   │      │ (Requisitions)  │      │(Analytics/Chat) │            │
│   └────────┬────────┘      └────────┬────────┘      └────────┬────────┘            │
│            │                         │                         │                      │
│            └─────────────────────────┼─────────────────────────┘                      │
│                                      │                                              │
│                                      ▼                                              │
│                    ┌─────────────────────────────────────────┐                      │
│                    │         FastAPI Backend (8000)          │                      │
│                    │  ┌───────────────────────────────────┐  │                      │
│                    │  │  Routes: /api/inventory/*        │  │                      │
│                    │  │           /api/requisition/*     │  │                      │
│                    │  │           /api/chat/*            │  │                      │
│                    │  │           /api/analytics/*        │  │                      │
│                    │  └───────────────────────────────────┘  │                      │
│                    └────────────────┬───────────────────────┘                      │
│                                     │                                               │
│          ┌──────────────────────────┼──────────────────────────┐                   │
│          │                          │                          │                    │
│          ▼                          ▼                          ▼                    │
│  ┌───────────────┐         ┌───────────────┐         ┌───────────────┐           │
│  │    Routes     │         │  Application  │         │Infrastructure │           │
│  │  (Endpoints)  │────────▶│ (Business     │────────▶│  (DB Access   │           │
│  │               │         │   Logic)      │         │  & External)  │           │
│  └───────────────┘         └───────┬───────┘         └───────┬───────┘           │
│                                    │                          │                    │
│                                    ▼                          ▼                    │
│                    ┌───────────────────────────────────────────────────────┐         │
│                    │                  DOMAIN LAYER                         │         │
│                    │        (Pure Logic — No Framework Imports)            │         │
│                    │  ┌──────────────────┐  ┌──────────────────────────┐  │         │
│                    │  │ domain/calculations.py  │ domain/agent/prompts.py│  │         │
│                    │  │ (Stock formulas, health colors)   │ (System prompts)      │  │         │
│                    │  └──────────────────┘  └──────────────────────────┘  │         │
│                    └───────────────────────────────────────────────────────┘         │
│                                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                         DATA LAYER                                           │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │  │
│  │  │      SQLite         │  │     ChromaDB        │  │   External APIs    │  │  │
│  │  │  (Transactions,     │  │  (Vector Store      │  │   Groq (LLM)       │  │  │
│  │  │   Items, Reqs,      │  │   for AI Memory)   │  │   LangSmith        │  │  │
│  │  │   Chat Sessions)    │  │                     │  │                    │  │  │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture — Clean Architecture Layers

The backend follows **Clean Architecture** with strict layer separation.

### Layer Rules

| Layer | Rule | Examples |
|-------|------|----------|
| `domain/` | Zero imports from infrastructure, api, or any framework | `prompts.py`, `calculations.py` |
| `infrastructure/` | Only imports from `domain/` or Python stdlib | `connection.py`, `models.py`, `vector_store.py`, `tools.py` |
| `application/` | Only layer calling both `domain/` and `infrastructure/` | `inventory_service.py`, `requisition_service.py`, `agent_tools.py` |
| `api/` | Never imports from `infrastructure/` directly | Routes only import `application/` and `core/` |

### Layer Diagram

```
┌────────────────────────────────────────────────────┐
│                     API LAYER                       │
│  routes/  →  schemas/  →  core/dependencies    │
│  (HTTP contract)   (Pydantic)    (DI factories)   │
└──────────────────────┬────────────────────────────┘
                       │ calls only
                       ▼
┌────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                   │
│  inventory_service.py, requisition_service.py,      │
│  analytics_service.py, agent_tools.py              │
│  → orchestrates domain logic + infra calls         │
└──────────────────────┬────────────────────────────┘
                       │ calls only
                       ▼
┌────────────────────────────────────────────────────┐
│                   DOMAIN LAYER                      │
│  domain/calculations.py  (stock formulas)          │
│  domain/agent/prompts.py (pure text prompts)       │
│  → pure business logic, no framework deps          │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│                INFRASTRUCTURE LAYER                │
│  database/  (SQLAlchemy: models, repos, queries) │
│  vector_store/ (ChromaDB: semantic memory)        │
│  tools.py    (LangGraph @tool wrappers)           │
└────────────────────────────────────────────────────┘
```

---

## 3. Component Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              COMPONENT RELATIONSHIPS                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         FRONTEND (React + Vite)                            │    │
│  │  Vendor Pages  │  Staff Pages  │  Admin Pages  │  API Client (axios)   │    │
│  └────────────────────────────────┬────────────────────────────────────────────┘    │
│                                   │                                                    │
│                                   ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                          BACKEND (FastAPI)                                  │    │
│  │                                                                              │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │    │
│  │  │   API Routes       │  │  API Schemas       │  │   Core             │ │    │
│  │  │  inventory.py      │  │  inventory_schemas │  │  config.py         │ │    │
│  │  │  requisition.py    │  │  requisition_schemas  │  exceptions.py      │ │    │
│  │  │  analytics.py      │  │  chat_schemas      │  │  dependencies.py   │ │    │
│  │  │  chat.py          │  │                    │  │  error_handlers.py  │ │    │
│  │  └──────────┬─────────┘  └─────────────────────┘  │  logging_config.py  │ │    │
│  │             │                                       │  middleware/         │ │    │
│  │             └───────────────────────────────────────┴─────────────────────┘ │    │
│  │                                    │                                            │    │
│  │                                    ▼                                            │    │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │    │
│  │  │                      APPLICATION LAYER                                 │ │    │
│  │  │  inventory_service.py  │  requisition_service.py  │  analytics_service.py  │ │    │
│  │  │  agent_tools.py        │                                            │ │    │
│  │  └─────────────────────────┬──────────────────────────────────────────────┘ │    │
│  │                            │                                                 │    │
│  │          ┌─────────────────┴──────────────────┐                            │    │
│  │          ▼                                  ▼                             │    │
│  │  ┌──────────────────┐           ┌──────────────────────────────┐      │    │
│  │  │     DOMAIN       │           │       INFRASTRUCTURE          │      │    │
│  │  │ domain/calculations.py  │  │  database/connection.py  │      │    │
│  │  │ domain/agent/prompts.py │  │  database/models.py   │      │    │
│  │  └──────────────────┘           │  database/queries.py  │      │    │
│  │                                 │  database/inventory_repo.py  │  │    │
│  │                                 │  database/requisition_repo.py│  │    │
│  │                                 │  vector_store/vector_store.py│  │    │
│  │                                 └──────────────────────────────┘      │    │
│  └───────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────┬─────────────────────────────────────────────────┐ │
│  │        SQLite               │        ChromaDB          │     External APIs     │ │
│  │  locations, items,         │  chat_memory collection  │  Groq (LLM)          │ │
│  │  transactions,              │  semantic search         │  Groq (LLM)          │ │
│  │  requisitions,              │  cross-session recall    │  LangSmith (tracing) │ │
│  │  chat_sessions/messages    │                         │                       │ │
│  └─────────────────────────────┴───────────────────────────┴───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React + Vite + Tailwind | UI Framework |
| **Backend** | FastAPI | REST API Server |
| **ORM** | SQLAlchemy | Database Abstraction |
| **Primary DB** | SQLite (dev) / PostgreSQL (prod) | Transactional Data |
| **Vector DB** | ChromaDB | AI Semantic Memory |
| **AI Framework** | LangGraph + LangChain | Agent Orchestration |
| **LLM** | Groq (OpenAI-compatible) | Language Model |
| **Observability** | LangSmith (optional) | Tracing |

---

## 5. Environment Variables

```env
# Database
DATABASE_PATH=../database/smart_inventory.db
DATABASE_URL=  # Set for PostgreSQL (Supabase) in production

# API Keys
GROQ_API_KEY=<key>
LANGCHAIN_API_KEY=<optional>

# App
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173
```

---

## 6. ADR Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Architecture | Clean Architecture (responsibility-based layers) | Testability, separation of concerns |
| DB ORM | SQLAlchemy + Repository pattern | Flexibility, swap SQLite → PostgreSQL |
| AI Memory | SQLite (history) + ChromaDB (semantic) | Best of both: ACID + vector search |
| API Style | REST with success envelope `{success, data, error}` | Consistent client contract |
| Frontend | React + Vite + Tailwind | Fast dev, component-based, responsive |
| DI | FastAPI Depends() | Native, testable, no external IoC container |

---

## 7. Module Responsibilities

| Module | Responsibility | Public API |
|--------|---------------|------------|
| `api/routes` | HTTP endpoint definitions | REST endpoints |
| `api/schemas` | Pydantic request/response models | Type validation |
| `application/*_service` | Business logic orchestration | Domain operations |
| `application/agent_tools` | LangGraph @tool wrappers | AI tool functions |
| `domain/calculations` | Pure stock formulas | `calculate_reorder_quantity`, `format_stock_item` |
| `domain/agent/prompts` | System prompt text | `get_system_prompt()` |
| `infrastructure/database/models` | SQLAlchemy ORM classes | DB models |
| `infrastructure/database/repos` | Data access layer | CRUD operations |
| `infrastructure/database/queries` | Complex SQL views | `get_latest_stock_health`, `get_critical_alerts` |
| `infrastructure/vector_store` | ChromaDB semantic memory | `add_message()`, `search_relevant()` |
| `core/config` | Settings from .env | `settings` singleton |
| `core/dependencies` | FastAPI DI factories | `get_inventory_service()`, etc. |
| `core/exceptions` | Custom exception hierarchy | `NotFoundError`, `ValidationError`, etc. |
| `core/error_handlers` | Global exception → HTTP mapping | FastAPI exception handlers |
| `core/middleware` | Request/response logging | `RequestLoggerMiddleware` |
