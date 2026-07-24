# InvIQ API Documentation

Comprehensive reference for the InvIQ backend REST API, GraphQL analytics interface, and WebSocket layer.

---

## Architecture Overview

InvIQ uses a **REST + GraphQL hybrid** pattern:

- **REST** handles all **mutations** (create, update, delete), authentication, chat, vendor uploads, admin, and super admin operations.
- **GraphQL** (Strawberry) handles all **analytics reads** — zero over-fetching, flexible field selection, role-aware data masking.
- **WebSocket** provides **real-time stock alert push** notifications.

| Layer | Protocol | Base URL | Purpose |
|-------|----------|----------|---------|
| REST API | HTTPS | `/api` | All mutations + auth + chat + vendor + admin |
| GraphQL | HTTPS | `/graphql/analytics` | Analytics reads (dashboard, heatmap, alerts, summary, stock health) |
| WebSocket | WSS | `/ws/alerts` | Real-time stock alert push |

### Response Envelope

**Success:**
```json
{
  "success": true,
  "message": "Action completed successfully",
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

---

## Global API Configurations

### 1. Authentication & Security

- **Type:** JSON Web Tokens (JWT) signed with `HS256`
- **Headers:** `Authorization: Bearer <access_token>`
- **Token Lifespans:** Access = 30 min, Refresh = 7 days (supports rotation)
- **Logout:** Access token blacklisted in Redis until expiry
- **Refresh Rotation:** Old refresh token is blacklisted after successful exchange
- **Login Lockout:** 5 failed attempts → 15 minutes lockout (Redis-tracked)

### 2. Authorization — 5-Tier RBAC

Permissions are cumulative (higher roles inherit lower permissions):

| Role | Level | Access |
|------|-------|--------|
| `super_admin` | 6 | Cross-tenant platform management, organization provisioning |
| `admin` | 5 | Tenant-level administration, audit logs, user provisioning, reports |
| `manager` | 4 | Requisition approval/rejection, full GraphQL privileged fields |
| `staff` | 3 | Basic inventory transactions, requisition creation |
| `vendor` | 2 | Excel manifest uploads, inventory ingestion |

> **GraphQL field masking:** `manager`, `admin`, and `super_admin` callers receive full values for `avgDailyUsage`, `daysRemaining`, and `leadTimeDays`. `guest`, `vendor`, and `staff` callers receive `null` for these fields.

### 3. Guest Demo Mode (Unauthenticated Access)

- **GET REST endpoints:** Silently serve data as Guest (anonymous) — no 401 raised.
- **GraphQL:** Same model — unauthenticated callers see all non-privileged fields; forecasting fields masked to `null`.
- **POST/PUT/DELETE endpoints:** Strict authentication — frontend redirects to `/signin`.
- **401 Interceptor:** Only triggers redirect if request originally carried a token (session expired).

### 4. Rate Limiting

Handled by `slowapi` with Redis-backed moving-window strategy:

| Tier | Limit | Applied To |
|------|-------|------------|
| Auth | 5/min | `/api/auth/login` |
| Register | 3/min | `/api/auth/register` |
| Password Reset | 3/min | `/api/auth/request-password-reset` |
| Refresh Token | 10/min | `/api/auth/refresh` |
| Chat | 20/min | `/api/chat/query`, `/api/chat/transcribe` |
| Transaction | 30/min | `/api/inventory/transaction` |
| Bulk Transaction | 10/min | `/api/inventory/bulk-transaction` |
| Requisition | 20/min | `/api/requisition/create` |
| Analytics | 30/min | `/api/analytics/*` |
| Vendor Upload | 10/min | `/api/vendor/upload-delivery` |
| Default | 60/min | All other endpoints |

**429 Response:**
```json
{
  "success": false,
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 60 seconds.",
  "retry_after": 60
}
```
With `Retry-After` header.

### 5. Caching System

Analytics and dashboard statistics are cached in Redis. **REST and GraphQL share the same cache keys.**

| Cache Key | TTL | Shared By |
|-----------|-----|-----------|
| `cache:analytics:dashboard_stats` | 2 min | REST + GraphQL |
| `cache:analytics:heatmap` | 5 min | REST + GraphQL |
| `cache:analytics:alerts:CRITICAL` | 5 min | REST + GraphQL |
| `cache:analytics:alerts:WARNING` | 5 min | REST + GraphQL |
| `cache:analytics:summary` | 5 min | REST + GraphQL |

- **Invalidation:** Automatically flushed on write transactions (`/api/inventory/transaction`, `/api/requisition/{id}/approve`).
- **`stockHealth` GraphQL query:** Not cached — designed for ad-hoc reporting.
- **Key prefix:** All cache keys prefixed with `cache:` to avoid collision with rate-limiter keys.

---

## REST API Endpoints

### 1. Authentication (`/api/auth`)

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/auth/login` | **POST** | Public | 5/min | Authenticate credentials. Returns access+refresh JWT. Lockout after 5 failures. |
| `/auth/register` | **POST** | `admin`+ | 3/min | Register a new user. Sends welcome email if SMTP enabled. |
| `/auth/logout` | **POST** | Authenticated | Default | Blacklist active JWT in Redis. |
| `/auth/refresh` | **POST** | Public | 10/min | Exchange valid refresh token for new access token. Old refresh revoked. |
| `/auth/me` | **GET** | Authenticated | Default | Retrieve current user profile. |
| `/auth/me` | **PATCH** | Authenticated | Default | Update own email/full_name. |
| `/auth/change-password` | **POST** | Authenticated | Default | Verify current password, set new one. |
| `/auth/users` | **GET** | `admin`+ | Default | Paginated user list with role/status filters. |
| `/auth/users/{user_id}` | **GET** | `admin`+ | Default | User detail. |
| `/auth/users/{user_id}/role` | **PUT** | `admin`+ | Default | Update user role. |
| `/auth/users/{user_id}/activate` | **PUT** | `admin`+ | Default | Activate user account. |
| `/auth/users/{user_id}/deactivate` | **PUT** | `admin`+ | Default | Deactivate user (not self). |
| `/auth/users/{user_id}/reset-password` | **POST** | `admin`+ | Default | Admin password reset. |
| `/auth/users/{user_id}` | **DELETE** | `admin`+ | Default | Hard delete user (not self). |
| `/auth/request-password-reset` | **POST** | Public | 3/min | Send reset email (no user enumeration). |
| `/auth/reset-password` | **POST** | Public | 5/min | Reset password via email token. |
| `/auth/verify-email` | **POST** | Public | Default | Verify email via token. |
| `/auth/google-auth` | **POST** | Public | 10/min | Google OAuth login/register. |

#### Request/Response Samples

**POST `/api/auth/login`**
```json
// Request
{ "username": "admin", "password": "SecurePassword123" }

// Response 200
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@inviq.io",
      "full_name": "Admin User",
      "role": "admin"
    }
  }
}
```

**POST `/api/auth/register`**
```json
// Request (admin+)
{
  "email": "newuser@hospital.com",
  "username": "nurse01",
  "password": "SecurePass99",
  "full_name": "Nurse Alpha",
  "role": "staff"
}
```

---

### 2. Inventory Management (`/api/inventory`)

All `GET` inventory routes support unauthenticated Guest Mode.

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/inventory/locations` | **GET** | Guest Permitted | Default | List all locations. |
| `/inventory/items` | **GET** | Guest Permitted | Default | List all items. |
| `/inventory/location/{location_id}/items` | **GET** | Guest Permitted | Default | Stock status for all items at a location. |
| `/inventory/stock/{location_id}/{item_id}` | **GET** | Guest Permitted | Default | Current stock for specific item+location. |
| `/inventory/locations` | **POST** | `staff`+ | 20/min | Create new location. |
| `/inventory/items` | **POST** | `staff`+ | 20/min | Register new item. |
| `/inventory/reset-data` | **POST** | `admin`+ | 3/min | Delete all inventory data (requires `confirm=true`). |
| `/inventory/transaction` | **POST** | `staff`+ | 30/min | Add single stock transaction. Triggers WebSocket alerts + email on low stock. |
| `/inventory/bulk-transaction` | **POST** | `staff`+ | 10/min | Add batch of transactions atomically. |

#### Request/Response Samples

**POST `/api/inventory/transaction`**
```json
// Request
{
  "location_id": 1,
  "item_id": 101,
  "date": "2026-06-10",
  "received": 50,
  "issued": 0,
  "notes": "Weekly restock",
  "batch_number": "BAT-2026-001",
  "expiry_date": "2027-06-10"
}

// Response 200
{
  "success": true,
  "message": "Transaction added successfully",
  "data": {
    "id": 884,
    "opening_stock": 45,
    "received": 50,
    "issued": 0,
    "closing_stock": 95,
    "date": "2026-06-10"
  }
}
```

**POST `/api/inventory/locations`**
```json
// Request
{
  "name": "Main Pharmacy",
  "type": "pharmacy",
  "region": "Delhi NCR",
  "address": "123 Hospital Road"
}
```

---

### 3. Requisition Workflow (`/api/requisition`)

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/requisition/create` | **POST** | `staff`+ | 20/min | Create stock requisition request. Auto-generates REQ number. |
| `/requisition/list` | **GET** | Guest Permitted | Default | Paginated list, filterable by status/location/requester. |
| `/requisition/stats` | **GET** | Guest Permitted | Default | Summary: total, pending, approved today, rejected, emergency pending. |
| `/requisition/{requisition_id}` | **GET** | Guest Permitted | Default | Full details with location + line items. |
| `/requisition/{requisition_id}/approve` | **PUT** | `manager`+ | 10/min | Approve — deducts stock atomically, broadcasts WebSocket alert. |
| `/requisition/{requisition_id}/reject` | **PUT** | `manager`+ | 10/min | Reject with mandatory reason (5-500 chars). |
| `/requisition/{requisition_id}/cancel` | **PUT** | `staff`+ | 10/min | Cancel a pending requisition. |

#### Request/Response Samples

**PUT `/api/requisition/5/approve`**
```json
// Request
{
  "approved_by": "manager_name",
  "item_adjustments": [
    { "item_id": 101, "approved_quantity": 40 }
  ]
}

// Response 200
{
  "success": true,
  "message": "Requisition approved, stock updated",
  "data": {
    "id": 5,
    "status": "APPROVED",
    "approved_at": "2026-06-10T08:24:00Z"
  }
}
```

---

### 4. AI Chatbot (`/api/chat`)

Queries feed into a LangGraph ReAct agent with 9 inventory tools.

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/chat/query` | **POST** | Authenticated | 20/min | Submit natural language question. Returns LLM-generated answer. |
| `/chat/transcribe` | **POST** | Authenticated | 20/min | Upload voice audio for Sarvam AI STT (`saaras:v3`) transcription. Supports 22 Indian languages. |
| `/chat/sessions` | **GET** | Authenticated | Default | List user's chat sessions. |
| `/chat/history/{conversation_id}` | **GET** | Authenticated | Default | Chat history for a session (ownership enforced). |
| `/chat/history/{conversation_id}` | **DELETE** | Authenticated | 10/min | Clear/delete a conversation. |
| `/chat/suggestions` | **GET** | Guest Permitted | Default | Predefined question suggestions. |

#### Request/Response Samples

**POST `/api/chat/query`**
```json
// Request
{
  "conversation_id": "conv_8f8b3b249b1c",
  "question": "What items are critical right now at Pharmacy A?"
}

// Response 200
{
  "success": true,
  "response": "At Pharmacy A, the following items are critical:\n1. **Paracetamol 500mg** - Current stock: 0 (Min: 100)\n2. **Amoxicillin 250mg** - Current stock: 5 (Min: 50)",
  "question": "What items are critical right now at Pharmacy A?",
  "conversation_id": "conv_8f8b3b249b1c",
  "suggested_actions": [
    { "type": "view", "label": "View All Alerts", "action": "view_alerts" }
  ]
}
```

**POST `/api/chat/transcribe`**
```json
// Request: multipart/form-data, field: file (binary audio)
// Response 200
{
  "success": true,
  "transcript": "What are the critical stock alerts in Delhi warehouse?",
  "language": "hi-IN"
}
```

---

### 5. Analytics — REST (`/api/analytics`)

Cached in Redis for fast, scalable sub-100ms responses.

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/analytics/dashboard/stats` | **GET** | Guest Permitted | 30/min | Category distribution, low-stock items, location stock, status distribution (cached 2 min). |
| `/analytics/heatmap` | **GET** | Guest Permitted | 30/min | Location × item grid (cached 5 min). |
| `/analytics/alerts` | **GET** | Guest Permitted | 30/min | Critical/warning alerts with reorder suggestions (cached 5 min). |
| `/analytics/summary` | **GET** | Guest Permitted | 30/min | Aggregate inventory health overview (cached 5 min). |

---

### 6. Vendor Ingestion (`/api/vendor`)

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/vendor/upload-delivery` | **POST** | `vendor`+ | 10/min | Upload Excel delivery manifest. Case-insensitive item matching. |
| `/vendor/my-uploads` | **GET** | `vendor`+ | Default | Upload history. |
| `/vendor/template` | **GET** | `vendor`+ | Default | Download blank Excel template. |

**Expected Excel columns:** `item_name`, `quantity_received`, `delivery_date` (optional), `notes` (optional)

---

### 7. Admin Dashboard (`/api/admin`)

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/admin/overview` | **GET** | `admin`+ | Default | Platform stats: total/active/inactive users, role breakdown, recent activity. |
| `/admin/audit-logs` | **GET** | `admin`+ | Default | Audit trail filterable by user, action, resource type. |
| `/admin/users/summary` | **GET** | `admin`+ | Default | All users with alerts (locked accounts, never logged in). |
| `/admin/reports/generate` | **GET** | `admin`+ | Default | Generate PDF report (inventory/transactions/requisitions/low_stock). |

---

### 8. Super Admin (`/api/superadmin`)

Requires `super_admin` role (exact match).

| Endpoint | Method | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `/superadmin/organizations` | **GET** | `super_admin` | Default | List all organizations. |
| `/superadmin/organizations` | **POST** | `super_admin` | 10/min | Create organization. |
| `/superadmin/organizations/{org_id}` | **PUT** | `super_admin` | 10/min | Update organization. |
| `/superadmin/organizations/{org_id}` | **DELETE** | `super_admin` | 5/min | Soft-delete organization (must have 0 users). |
| `/superadmin/organizations/{org_id}/admin` | **POST** | `super_admin` | 10/min | Create admin for organization. |
| `/superadmin/users` | **GET** | `super_admin` | Default | List all users across all organizations. |

---

### 9. Health & Root

| Endpoint | Method | Description |
|---|---|---|
| `/` | **GET** | Root — returns name, version, status, docs URL. |
| `/health` | **GET** | Health check — verifies Redis connectivity. Returns 200 or 503. |

---

## GraphQL Analytics API

**Endpoint:** `POST /graphql/analytics`
**Playground (dev only):** `GET /graphql/analytics`

Read-only analytics interface built with **Strawberry**. Zero over-fetching, server-side filtering, role-aware field masking, shared Redis cache with REST.

### Authentication

Same JWT Bearer token as REST. Pass in `Authorization` header. Unauthenticated requests accepted — privileged fields return `null`.

---

### Query: `dashboardStats`

Returns high-level chart data. Cached 2 minutes.

```graphql
query DashboardStats {
  dashboardStats {
    categoryDistribution { name value }
    lowStockItems { name stock minStock shortage }
    locationStock { name value }
    statusDistribution { name value color }
  }
}
```

---

### Query: `heatmap`

Returns the full inventory heatmap grid (locations × items). Cached 5 minutes.

```graphql
query Heatmap {
  heatmap {
    locations
    items
    matrix
    details {
      locationName
      itemName
      currentStock
      healthStatus
      color
      avgDailyUsage    # null for guest/vendor/staff
      daysRemaining    # null for guest/vendor/staff
      leadTimeDays     # null for guest/vendor/staff
    }
  }
}
```

---

### Query: `alerts`

Returns critical or warning stock alerts with recommended reorder quantities. Cached 5 minutes.

| Argument | Type | Default | Values |
|----------|------|---------|--------|
| `severity` | `String` | `"CRITICAL"` | `"CRITICAL"` \| `"WARNING"` |

```graphql
query Alerts($severity: String = "CRITICAL") {
  alerts(severity: $severity) {
    severity
    count
    alerts {
      itemName
      locationName
      currentStock
      healthStatus
      recommendedReorder
      avgDailyUsage    # null for guest/vendor/staff
      leadTimeDays     # null for guest/vendor/staff
    }
  }
}
```

---

### Query: `summary`

Aggregate inventory health overview. Cached 5 minutes.

```graphql
query Summary {
  summary {
    overview { totalLocations totalItems totalRecords }
    healthSummary { critical warning healthy }
    categories { name total critical warning healthy }
  }
}
```

---

### Query: `stockHealth`

Flexible ad-hoc stock health query with server-side filtering. **Not cached.**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `location` | `String` | `""` | Case-insensitive substring match |
| `item` | `String` | `""` | Case-insensitive substring match |
| `statusFilter` | `String` | `""` | Exact match: `""` \| `"CRITICAL"` \| `"WARNING"` \| `"HEALTHY"` |

```graphql
query StockHealth($location: String = "", $item: String = "", $statusFilter: String = "CRITICAL") {
  stockHealth(location: $location, item: $item, statusFilter: $statusFilter) {
    locationName
    itemName
    category
    currentStock
    healthStatus
    color
    lastUpdated
    avgDailyUsage    # null for guest/vendor/staff
    daysRemaining    # null for guest/vendor/staff
    leadTimeDays     # null for guest/vendor/staff
  }
}
```

---

### GraphQL Error Handling

```json
{
  "data": null,
  "errors": [
    {
      "message": "severity must be 'CRITICAL' or 'WARNING'",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["alerts"]
    }
  ]
}
```

---

## Real-Time WebSocket (`/ws/alerts`)

Clients connect to `/ws/alerts?token=<access_token>`. JWT validated before accept; rejects with code 4001 on invalid token.

### Connection

```
ws://localhost:8000/ws/alerts?token=eyJhbGciOi...
```

### Event Format

**Critical Stock Alert:**
```json
{
  "type": "low_stock_alert",
  "status": "CRITICAL",
  "item_name": "Paracetamol 500mg",
  "item_id": 101,
  "location_id": 1,
  "current_stock": 0,
  "min_stock": 100
}
```

**Heartbeat:**
- Client sends: `"ping"`
- Server responds: `{"type": "pong"}`

---

## Background Operations: Email Alerts

When stock drops below minimum threshold:

1. Active admins/managers queried from PostgreSQL (cached 60s).
2. Background `threading.Thread(daemon=True)` spawned — zero latency impact on HTTP response.
3. Thread establishes SMTP TLS connection and dispatches HTML alert template.
4. Thread terminates automatically; errors logged silently without rolling back transactions.

---

## Error Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `INSUFFICIENT_STOCK` | 400 | Not enough stock for operation |
| `DUPLICATE` | 409 | Resource already exists |
| `INVALID_STATE` | 400 | Operation not allowed in current state |
| `AUTHENTICATION_ERROR` | 401 | Invalid credentials |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `DATABASE_ERROR` | 500 | Database error (details sanitized) |
| `SERVICE_UNAVAILABLE` | 503 | Database connection error |
| `INTERNAL_ERROR` | 500 | Unhandled exception |
| `rate_limit_exceeded` | 429 | Rate limit exceeded |
