# InvIQ API Documentation

This document provides a comprehensive, production-grade reference for the InvIQ backend REST API, GraphQL analytics interface, and WebSocket layer. It details authentication rules, rate limits, caching behavior, and Guest Demo Mode interactions.

---

## ── Architecture Overview ───────────────────────────────────────────────────

InvIQ uses a **REST + GraphQL hybrid** — the industry-standard pattern:

- **REST** handles all **mutations** (create, update, delete) and complex transactional endpoints.
- **GraphQL** (Strawberry) handles all **analytics reads** — zero over-fetching, flexible field selection, role-aware data masking.

| Layer | Protocol | Base URL | Purpose |
|-------|----------|----------|---------|
| REST API | HTTPS | `/api` | All mutations + auth + chat + vendor |
| GraphQL | HTTPS | `/graphql/analytics` | Analytics reads (dashboard, heatmap, alerts, summary, stock health) |
| WebSocket | WSS | `/ws` | Real-time stock alert push |

- **Data Format:** UTF-8 JSON requests and responses
- **Standard REST Success Response Envelope:**
  ```json
  {
    "success": true,
    "message": "Action completed successfully",
    "data": { ... }
  }
  ```
- **Standard REST Error Response Envelope:**
  ```json
  {
    "success": false,
    "error": "Error type identifier (e.g. ValidationError)",
    "message": "Human readable error description",
    "details": { ... }
  }
  ```

---

## ── Global API Configurations ────────────────────────────────────────────────

### 1. Authentication & Security
- **Type:** JSON Web Tokens (JWT) signed with symmetric `HS256`.
- **Headers:** All authenticated requests must include `Authorization: Bearer <access_token>`.
- **Token Lifespans:**
  - **Access Token:** 30 minutes
  - **Refresh Token:** 7 days (supports token rotation)
- **Logout / Invalidation:** Blacklisted in Redis until expiration.
- **Login Lockout:** 5 failed attempts on an account → 15 minutes lockout (tracked in Redis).

### 2. Authorization Scopes (5-Tier RBAC)
The system supports a 5-tier role hierarchy. Permissions are cumulative (higher roles inherit lower permissions):
1. **`super_admin` (6):** Cross-tenant platform management, organization provisioning.
2. **`admin` (5):** Tenant-level administration, audit logs, user provisioning, reports.
3. **`manager` (4):** Requisition approval/rejection, stock overrides. Full GraphQL privileged fields.
4. **`staff` (3):** Basic inventory transactions (issue/receipt), requisition creation.
5. **`vendor` (2):** Excel manifest uploads, inventory ingestion.

> **GraphQL field masking:** `manager`, `admin`, and `super_admin` callers receive full values for `avgDailyUsage`, `daysRemaining`, and `leadTimeDays`. Guest and Vendor callers receive `null` for these operational forecasting fields.

### 3. Guest Demo Mode (Unauthenticated Access)
To allow visitors to preview the application without sign-up, the API utilizes a custom dependency: `get_optional_user()`.
- **GET REST Endpoints:** Relaxed authentication. If an invalid or missing token is detected, the API silently treats the caller as a **Guest (anonymous)** and serves the requested data (read-only).
- **GraphQL Endpoint:** Same model — unauthenticated callers are served all non-privileged fields; operational forecasting fields are masked to `null`.
- **POST/PUT/DELETE Endpoints:** Strict authentication. If a guest attempts a write, approval, or chat interaction, the frontend intercepts the request and redirects the user to `/signin`.
- **401 Interceptor:** The client interceptor only triggers a redirect to `/signin` if the request originally carried a token (session expired). Guests are never forced to redirect while browsing.

### 4. Rate Limiting
Handled by `slowapi` with Redis state storage:
- **Authentication Endpoints (`/api/auth/*`):** 5 requests/minute (brute-force defense).
- **Chat Endpoints (`/api/chat/*`):** 20 requests/minute (capping LLM API token costs).
- **Default Endpoints:** 60 requests/minute.
- **GraphQL (`/graphql/analytics`):** No Slowapi rate limiter — GraphQL is query-complexity-bounded by field selection depth.

### 5. Caching System
Analytics and dashboard statistics are cached in Redis to prevent heavy database aggregation overhead. **The REST and GraphQL layers share the same cache keys** — a REST warm cache is immediately available to GraphQL callers and vice versa.

| Cache Key | TTL | Shared By |
|-----------|-----|-----------|
| `cache:analytics:dashboard_stats` | 2 min | REST + GraphQL |
| `cache:analytics:heatmap` | 5 min | REST + GraphQL |
| `cache:analytics:alerts:CRITICAL` | 5 min | REST + GraphQL |
| `cache:analytics:alerts:WARNING` | 5 min | REST + GraphQL |
| `cache:analytics:summary` | 5 min | REST + GraphQL |

- **Invalidation:** Automatically flushed whenever write transactions (`/api/inventory/transaction`, `/api/requisition/{id}/approve`) are successfully committed.
- **`stockHealth` GraphQL query:** Not cached — designed for ad-hoc reporting with server-side filter arguments.

---

## ── REST API Endpoints Directory ─────────────────────────────────────────────

### 1. Authentication (`/api/auth`)

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/auth/login` | **POST** | Public | 5/min | Authenticate credentials. Returns access/refresh JWT tokens. |
| `/auth/register` | **POST** | `admin`+ | 3/min | Register a new user within the administrator's organization. |
| `/auth/logout` | **POST** | Authenticated | Default | Blacklists the active JWT token in Redis. |
| `/auth/refresh` | **POST** | Public | Default | Exchange valid refresh token for a new access token. |
| `/auth/me` | **GET** | Authenticated | Default | Retrieve active user profile data. |
| `/auth/me` | **PATCH**| Authenticated | Default | Update own profile details. |
| `/auth/users` | **GET** | `admin`+ | Default | Paginated list of users within the organization. |
| `/auth/users/{user_id}` | **GET** | `admin`+ | Default | Retrieve detailed profile of a specific user. |
| `/auth/users/{user_id}/role` | **PUT** | `admin`+ | Default | Update a user's access role. |
| `/auth/users/{user_id}/deactivate`| **PUT** | `admin`+ | Default | Temporarily deactivate a user account. |
| `/auth/users/{user_id}/activate` | **PUT** | `admin`+ | Default | Re-activate a deactivated user account. |
| `/auth/users/{user_id}` | **DELETE**| `admin`+ | Default | Hard delete a user account from the system. |
| `/auth/users/{user_id}/reset-password`|**POST**| `admin`+ | Default | Reset a user's password directly (admin override). |
| `/auth/change-password` | **POST** | Authenticated | Default | Change password for the logged-in user. |
| `/auth/request-password-reset`|**POST**| Public | 5/min | Triggers a password reset token sent via email. |
| `/auth/reset-password` | **POST** | Public | 5/min | Reset password using a valid email token. |
| `/auth/verify-email` | **POST** | Public | 5/min | Verify user email registration using email token. |
| `/auth/google-auth` | **POST** | Public | Default | Authenticate via Google OAuth using id token. |

#### Request/Response Samples:
**POST `/api/auth/login`**
- **Body:**
  ```json
  {
    "username": "admin",
    "password": "SecurePassword123"
  }
  ```
- **Response (200 OK):**
  ```json
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
        "role": "admin",
        "org_id": 1
      }
    }
  }
  ```

---

### 2. Inventory Management (`/api/inventory`)

All `GET` inventory routes support unauthenticated visitors in Guest Mode.

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/inventory/locations` | **GET** | Guest Permitted| Default | List all physical inventory locations (warehouses, pharmacies). |
| `/inventory/items` | **GET** | Guest Permitted| Default | Retrieve inventory item registry (medications, supplies). |
| `/inventory/location/{location_id}/items`|**GET**|Guest Permitted| Default | Get current stock status of all registered items at a location. |
| `/inventory/stock/{location_id}/{item_id}`|**GET**|Guest Permitted| Default | Get exact closing stock of a specific item at a location. |
| `/inventory/locations` | **POST** | `staff`+ | 20/min | Create a new physical location. |
| `/inventory/items` | **POST** | `staff`+ | 20/min | Register a new item in the database catalog. |
| `/inventory/reset-data` | **POST** | `staff`+ | 3/min | Reset and wipe all inventory, transactions, and locations. |
| `/inventory/transaction` | **POST** | `staff`+ | 30/min | Add a single stock transaction (received/issued). |
| `/inventory/bulk-transaction` | **POST** | `staff`+ | 10/min | Add a batch of transactions within a database transaction. |

#### Request/Response Samples:
**GET `/api/inventory/location/1/items`**
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": 101,
        "name": "Paracetamol 500mg",
        "category": "Medication",
        "unit": "Tablets",
        "min_stock": 100,
        "current_stock": 45,
        "status": "WARNING"
      }
    ]
  }
  ```

**POST `/api/inventory/transaction`**
- **Body:**
  ```json
  {
    "location_id": 1,
    "item_id": 101,
    "transaction_date": "2026-06-10",
    "received": 50,
    "issued": 0,
    "notes": "Weekly restock"
  }
  ```
- **Response (201 Created):**
  ```json
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

---

### 3. Requisition Workflow (`/api/requisition`)

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/requisition/create` | **POST** | `staff`+ | 20/min | Create a new stock requisition request. |
| `/requisition/list` | **GET** | Guest Permitted| Default | Paginated list of requisitions filtered by status. |
| `/requisition/stats` | **GET** | Guest Permitted| Default | Summary statistics of requisition statuses (Pending, Approved, Rejected). |
| `/requisition/{requisition_id}` | **GET** | Guest Permitted| Default | Detailed view of a requisition including items requested. |
| `/requisition/{requisition_id}/approve` | **PUT** | `manager`+ | 10/min | Approve requisition (commits stock transaction & websocket trigger). |
| `/requisition/{requisition_id}/reject` | **PUT** | `manager`+ | 10/min | Reject requisition (requires reason string). |
| `/requisition/{requisition_id}/cancel` | **PUT** | `staff`+ | 10/min | Cancel a pending requisition. |

#### Request/Response Samples:
**PUT `/api/requisition/5/approve`**
- **Body:**
  ```json
  {
    "item_adjustments": [
      {
        "item_id": 101,
        "approved_quantity": 40
      }
    ]
  }
  ```
- **Response (200 OK):**
  ```json
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

### 4. AI Chatbot Agent (`/api/chat`)

Queries to the AI Chatbot feed into a LangGraph ReAct agent.

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/chat/query` | **POST** | Authenticated | 20/min | Submit a natural language question. Generates tool actions or text. |
| `/chat/transcribe` | **POST** | Authenticated | 15/min | Upload voice audio (WAV/MP3/M4A/WEBM) for Sarvam AI STT (`saaras:v3`) transcription. |
| `/chat/sessions` | **GET** | Authenticated | Default | Get list of user's active/past chat sessions. |
| `/chat/history/{conversation_id}` | **GET** | Authenticated | Default | Get historical messages from a specific chat session. |
| `/chat/history/{conversation_id}` | **DELETE**| Authenticated | 10/min | Clear/delete a chat session history. |
| `/chat/suggestions` | **GET** | Guest Permitted| Default | Returns a list of default recommended prompts. |

#### Request/Response Samples:
**POST `/api/chat/transcribe`**
- **Content-Type:** `multipart/form-data`
- **Form Body:** `file` (binary audio blob)
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "transcript": "What are the critical stock alerts in Delhi warehouse?",
    "language": "hi-IN"
  }
  ```

**POST `/api/chat/query`**
- **Body:**
  ```json
  {
    "conversation_id": "conv_8f8b3b249b1c",
    "question": "What items are critical right now at Pharmacy A?"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "response": "At Pharmacy A, the following items are currently critical:\n1. **Paracetamol 500mg** - Current stock: 0 (Min: 100)\n2. **Amoxicillin 250mg** - Current stock: 5 (Min: 50)",
    "question": "What items are critical right now at Pharmacy A?",
    "conversation_id": "conv_8f8b3b249b1c",
    "suggested_actions": [
      {
        "type": "view",
        "label": "View All Alerts",
        "action": "view_alerts"
      }
    ]
  }
  ```


---

### 5. Analytics Dashboard — REST (`/api/analytics`)

Analytics endpoints are cached in Redis to maintain fast, scalable sub-100ms response times. For flexible, field-level analytics queries, use the [GraphQL analytics endpoint](#-graphql-analytics-api) instead.

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/analytics/dashboard/stats` | **GET** | Guest Permitted| 30/min | High-level metrics for dashboard (cached 2 min). |
| `/analytics/heatmap` | **GET** | Guest Permitted| 30/min | Grid data representing item stock health per location (cached 5 min). |
| `/analytics/alerts` | **GET** | Guest Permitted| 30/min | List of critical/warning stock alerts across all locations (cached 5 min). |
| `/analytics/summary` | **GET** | Guest Permitted| 30/min | Aggregate inventory health overview (cached 5 min). |

---

### 6. Vendor Ingestion (`/api/vendor`)

Fuzzy matching uses `RapidFuzz` to map manifest strings to registry database entities.

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/vendor/upload-delivery` | **POST** | `vendor`+ | 10/min | Upload Excel document containing stock delivery details. |
| `/vendor/my-uploads` | **GET** | `vendor`+ | Default | Retrieve manifest ingestion history for current vendor. |
| `/vendor/template` | **GET** | `vendor`+ | Default | Download a blank Excel template for vendor manifests. |

- **Fuzzy Matching Threshold:** `85%` matching score. Names scoring lower write warning rows to the ingestion log and skip import.
- **Upload parser:** `openpyxl` (Python engine).

---

### 7. Administrative Controls (`/api/admin`)

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/admin/overview` | **GET** | `admin`+ | Default | Tenant system overview numbers (users, locations, audits). |
| `/admin/audit-logs` | **GET** | `admin`+ | Default | Paginated system-wide write operation logs for compliance. |
| `/admin/users/summary` | **GET** | `admin`+ | Default | User count aggregated by role. |
| `/admin/reports/generate` | **GET** | `admin`+ | Default | Generate and export PDF reports (returns binary blob). |

---

### 8. Platform Superadmin Operations (`/api/superadmin`)

Requires `super_admin` role (global scope, skips tenant constraints).

| Endpoint | Method | Auth Scope | Rate Limit | Description |
|---|---|---|---|---|
| `/superadmin/organizations` | **GET** | `super_admin` | Default | List all provisioned organizations. |
| `/superadmin/organizations` | **POST** | `super_admin` | 10/min | Create and provision a new multi-tenant organization. |
| `/superadmin/organizations/{org_id}`|**PUT** | `super_admin` | 10/min | Update organization details. |
| `/superadmin/organizations/{org_id}`|**DELETE**| `super_admin` | 5/min | Delete organization (soft delete). |
| `/superadmin/organizations/{org_id}/admin`|**POST**| `super_admin` | 10/min | Provision tenant admin user for an organization. |
| `/superadmin/users` | **GET** | `super_admin` | Default | List all users across all organizations on the platform. |

---

## 🔷 GraphQL Analytics API

**Endpoint:** `POST /graphql/analytics`  
**Playground (dev only):** `GET /graphql/analytics`

The GraphQL layer is a read-only analytics interface built with **Strawberry** (code-first Python GraphQL). It exposes the same underlying `AnalyticsService` as the REST layer but with:
- **Zero over-fetching** — clients request exactly the fields they need
- **Server-side filtering** on `stockHealth` (location, item name, status)
- **Role-aware field masking** (see RBAC section above)
- **Shared Redis cache** — warm REST cache is immediately reused

### Authentication

GraphQL uses the same JWT Bearer token as REST. Pass it in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Unauthenticated (Guest) requests are accepted — privileged fields return `null`.

---

### Query: `dashboardStats`

Returns high-level chart data for the analytics dashboard. Cached for 2 minutes.

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

**Response:**
```json
{
  "data": {
    "dashboardStats": {
      "categoryDistribution": [
        { "name": "Medication", "value": 42 },
        { "name": "Equipment", "value": 18 }
      ],
      "lowStockItems": [
        { "name": "Paracetamol 500mg", "stock": 5, "minStock": 100, "shortage": 95 }
      ],
      "locationStock": [
        { "name": "Main Pharmacy", "value": 2840 }
      ],
      "statusDistribution": [
        { "name": "CRITICAL", "value": 8, "color": "#ef4444" },
        { "name": "WARNING",  "value": 14, "color": "#f59e0b" },
        { "name": "HEALTHY",  "value": 38, "color": "#22c55e" }
      ]
    }
  }
}
```

---

### Query: `heatmap`

Returns the full inventory heatmap grid (locations × items). Cached for 5 minutes.

```graphql
query Heatmap {
  heatmap {
    locations
    items
    matrix        # JSON scalar — list[list[{stock, status, daysRemaining}]]
    details {
      locationName
      itemName
      currentStock
      healthStatus
      color
      avgDailyUsage   # null for Guest/Vendor
      daysRemaining   # null for Guest/Vendor
      leadTimeDays    # null for Guest/Vendor
    }
  }
}
```

---

### Query: `alerts`

Returns critical or warning stock alerts with recommended reorder quantities. Cached for 5 minutes per severity level.

**Arguments:**

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
      avgDailyUsage   # null for Guest/Vendor
      leadTimeDays    # null for Guest/Vendor
    }
  }
}
```

---

### Query: `summary`

Returns aggregate inventory health overview — item counts, health breakdown, and per-category stats. Cached for 5 minutes.

```graphql
query Summary {
  summary {
    overview {
      totalLocations
      totalItems
      totalRecords
    }
    healthSummary {
      critical
      warning
      healthy
    }
    categories {
      name
      total
      critical
      warning
      healthy
    }
  }
}
```

---

### Query: `stockHealth`

Flexible ad-hoc stock health query with server-side filtering. **Not cached** — designed for on-demand reporting.

**Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `location` | `String` | `""` | Case-insensitive substring match on location name |
| `item` | `String` | `""` | Case-insensitive substring match on item name |
| `statusFilter` | `String` | `""` | Exact match: `""` \| `"CRITICAL"` \| `"WARNING"` \| `"HEALTHY"` |

```graphql
query StockHealth(
  $location: String = "",
  $item: String = "",
  $statusFilter: String = "CRITICAL"
) {
  stockHealth(location: $location, item: $item, statusFilter: $statusFilter) {
    locationName
    itemName
    category
    currentStock
    healthStatus
    color
    lastUpdated
    avgDailyUsage   # null for Guest/Vendor
    daysRemaining   # null for Guest/Vendor
    leadTimeDays    # null for Guest/Vendor
  }
}
```

**Example — all critical items at any Warehouse:**
```graphql
{ stockHealth(location: "Warehouse", statusFilter: "CRITICAL") {
    itemName locationName currentStock
} }
```

---

### GraphQL Error Handling

GraphQL errors are returned in the standard `errors` array. The HTTP status code is always `200` for GraphQL responses (per the spec).

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

## ── Real-Time WebSockets (`/ws`) ─────────────────────────────────────────────

Clients connect to `/ws/alerts?token=<access_token>` to receive server-sent events. Connections are tracked per-location.

### Event Format:
**Critical Stock Alert Event (`low_stock_alert`)**
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

---

## ── Background Operations: Email alerts ──────────────────────────────────────

When stock level transitions below minimum requirements:
1. Active administrators and managers are queried from PostgreSQL.
2. A background `threading.Thread(daemon=True)` is spawned.
3. The thread connects to the configured SMTP relay (TLS encrypted).
4. HTML alert template is populated and dispatched.
5. Thread terminates automatically; errors are logged silently without interrupting active requests.
