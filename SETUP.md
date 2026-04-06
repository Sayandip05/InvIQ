# InvIQ - Step-by-Step Setup Guide

## Prerequisites

Before starting, ensure you have:
- **Python 3.11+** (check: `python --version`)
- **Node.js 18+** (check: `node --version`)
- **Git** installed

---

## Phase 1: Environment Setup

### 1.1 Clone & Navigate
```bash
cd C:\Users\sayan\DEVELOPEMENT\InvIQ
```

### 1.2 Backend Environment
Create `backend/.env` file:
```env
# REQUIRED - Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-here

# Database (SQLite for dev, PostgreSQL for prod)
DATABASE_URL=sqlite:///./inviq.db

# Auth Settings
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15

# Rate Limiting
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=5/minute

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Environment
ENVIRONMENT=development

# Optional: SMTP for email (password reset/verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
FRONTEND_URL=http://localhost:5173

# Optional: Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional: Redis (for rate limiting/caching)
REDIS_URL=redis://localhost:6379
```

### 1.3 Frontend Environment
Create `frontend/.env` file:
```env
VITE_API_URL=http://localhost:8000/api
VITE_GOOGLE_CLIENT_ID=your-google-client-id
```

---

## Phase 2: Backend Setup

### 2.1 Create Virtual Environment
```bash
cd backend
python -m venv venv
```

### 2.2 Activate Virtual Environment
```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2.3 Install Dependencies
```bash
pip install -r requirements.txt
```

### 2.4 Verify Backend
```bash
python -c "from app.main import app; print('Backend OK')"
```

**Expected Output:** `Backend OK`

---

## Phase 3: Frontend Setup

### 3.1 Navigate to Frontend
```bash
cd frontend
```

### 3.2 Install Dependencies
```bash
npm install
```

### 3.3 Verify Frontend Build
```bash
npm run build
```

**Expected:** Build successful (815KB bundle)

---

## Phase 4: Running the Application

### 4.1 Start Backend (Terminal 1)
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Wait for output:**
```
INFO: Application startup complete
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 4.2 Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

**Wait for output:**
```
VITE v7.3.1 ready in 500ms
➜  Local:   http://localhost:5173/
```

---

## Phase 5: Access the Application

### 5.1 Open Browser
Go to: **http://localhost:5173**

### 5.2 Login Credentials
Default admin created on first run:
```
Username: admin
Password: admin123
```

---

## Phase 6: Testing Features

### 6.1 Auth Features
| Feature | URL | Notes |
|---------|-----|-------|
| Sign In | `/signin` | Default: admin/admin123 |
| Sign Up | `/signup` | Requires admin to enable |
| Forgot Password | `/forgot-password` | Needs SMTP config |
| Reset Password | `/reset-password?token=xxx` | Email link |
| Verify Email | `/verify-email?token=xxx` | Email link |

### 6.2 Portal Routes (by role)
| Role | URL | Description |
|------|-----|-------------|
| Admin | `/admin/dashboard` | Full access |
| Manager | `/manager/dashboard` | Approve requisitions |
| Viewer | `/viewer/dashboard` | Read-only |
| Staff | `/staff` | Create requisitions |
| Vendor | `/vendor` | Upload inventory |
| Super Admin | `/superadmin/dashboard` | System-wide |

### 6.3 New Features Added
- **User Management**: `/admin/users`
- **Audit Logs**: `/admin/audit-logs`
- **Reports**: `/admin/reports`
- **Real-time Alerts**: Bell icon in header

---

## Phase 7: Optional - Testing

### 7.1 Install Test Dependencies
```bash
pip install "httpx<0.28"
```

### 7.2 Run Tests
```bash
cd backend
python -m pytest tests/ -v
```

---

## Quick Reference Commands

### Backend
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

### Stop Servers
```bash
# Press Ctrl+C in each terminal
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change: `uvicorn app.main:app --port 8001` |
| Port 5173 in use | Check other vite processes |
| Import errors | Ensure venv is activated |
| SQLite locked | Delete `.db` file and restart |
| CORS errors | Add URL to `CORS_ORIGINS` in .env |

---

## Production Checklist

Before production deployment:
- [ ] Set `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Configure Redis for rate limiting/caching
- [ ] Configure SMTP for emails
- [ ] Set up Google OAuth credentials
- [ ] Set up reverse proxy (Nginx)
- [ ] Enable HTTPS/SSL

---

**🎉 You're ready to use InvIQ!**