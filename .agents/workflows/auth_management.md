---
description: Authentication and User Role Management Flow
---

# Authentication & Authorization Workflow

## 1. Initial Admin Access (System Seed)
On first startup, the app creates a default admin:
- **Username:** `admin` | **Password:** `admin123` | **Role:** `admin`

## 2. JWT Token Login
1. `POST /api/auth/login` → `{ "username": "admin", "password": "admin123" }`
2. Get `access_token` (30 min) + `refresh_token` (7 days)
3. Use `Authorization: Bearer <token>` on all subsequent requests
4. **Login lockout:** 5 failed attempts → account locked for 15 minutes

## 3. Admin: Managing Users
| Action | Endpoint | Method |
|--------|----------|--------|
| Create user | `/api/auth/register` | POST |
| List all users | `/api/auth/users?role=&is_active=` | GET |
| Get one user | `/api/auth/users/{id}` | GET |
| Change role | `/api/auth/users/{id}/role` | PUT |
| Reset password | `/api/auth/users/{id}/reset-password` | POST |
| Activate | `/api/auth/users/{id}/activate` | PUT |
| Deactivate | `/api/auth/users/{id}/deactivate` | PUT |
| Delete | `/api/auth/users/{id}` | DELETE |

## 4. Self-Service (Any User)
| Action | Endpoint | Method |
|--------|----------|--------|
| View profile | `/api/auth/me` | GET |
| Update profile | `/api/auth/me` | PATCH |
| Change password | `/api/auth/change-password` | POST |
| Refresh token | `/api/auth/refresh` | POST |

## 5. Role Hierarchy
- **Admin (4):** Full access + user management
- **Manager (3):** Approve/reject requisitions + all below
- **Staff (2):** Create items, transactions, requisitions
- **Viewer (1):** Read-only access

## 6. Audit Trail
All auth actions are logged to `audit_logs` table:
LOGIN, REGISTER, ROLE_CHANGE, ACTIVATE, DEACTIVATE, DELETE, PASSWORD_CHANGE, PASSWORD_RESET
