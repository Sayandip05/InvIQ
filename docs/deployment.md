# Deployment Guide - InvIQ

**Version:** 1.0  
**Last Updated:** April 30, 2026  
**Author:** Sayandip Bar

---

## 🌐 Deployment Overview

InvIQ uses a modern serverless/managed infrastructure for zero-ops deployment:

| Service | Platform | URL | Purpose |
|---------|----------|-----|---------|
| **Frontend** | Vercel | `https://inviq.vercel.app` | React SPA hosting |
| **Backend** | Render.com | `https://inviq-api.onrender.com` | FastAPI REST API |
| **Database** | Neon | Project: `inviq-production` | PostgreSQL database |
| **Cache** | Upstash Redis | Instance: `inviq-cache` | Distributed cache & rate limiting |
| **Vector DB** | ChromaDB | Render persistent disk | AI semantic memory |

---

## 📋 Environment Variables

### Backend (Render.com)

**Required:**
```
ENVIRONMENT=production
PROJECT_NAME=Smart Inventory Assistant
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=<generate-with-openssl-rand-hex-32>
FRONTEND_URL=https://inviq.vercel.app
CORS_ORIGINS=https://inviq.vercel.app
```

**AI/LLM:**
```
GROQ_API_KEY=<your-groq-api-key>
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1024
```

**Redis (Upstash):**
```
UPSTASH_REDIS_REST_URL=https://your-endpoint.upstash.io
UPSTASH_REDIS_REST_TOKEN=<your-token>
REDIS_ENABLED=true
```

**Security:**
```
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
```

**Admin Accounts:**
```
SUPER_ADMIN_EMAIL=admin@yourdomain.com
ADMIN_EMAIL=admin@inventory.local
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password>
ADMIN_FULL_NAME=System Administrator
```

**Optional (AI Observability):**
```
LANGSMITH_API_KEY=<your-langsmith-key>
LANGSMITH_PROJECT=InvIQ
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

**Optional (Email):**
```
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<app-password>
SMTP_FROM_EMAIL=noreply@inviq.io
SMTP_FROM_NAME=InvIQ Smart Inventory
```

**ChromaDB:**
```
CHROMADB_ENABLED=true
CHROMADB_PATH=/opt/render/project/data/chromadb
CHROMADB_COLLECTION=chat_memory
```

**Rate Limiting:**
```
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=5/minute
```

**Google OAuth:**
```
GOOGLE_OAUTH_VERIFY_URL=https://www.googleapis.com/oauth2/v3/userinfo
```

---

### Frontend (Vercel)

```
VITE_API_URL=https://inviq-api.onrender.com
VITE_WS_URL=wss://inviq-api.onrender.com
```

---

## 🚀 Deployment Steps

### 1. Setup Infrastructure

#### A. Neon (Database)
1. Go to [neon.tech](https://neon.tech)
2. Create new project: `inviq-production`
3. Copy connection string from Connection Details
4. Format: `postgresql://user:[password]@[host]/[database]?sslmode=require`

#### B. Upstash Redis (Cache)
1. Go to [console.upstash.com](https://console.upstash.com)
2. Create new Redis database: `inviq-cache`
3. Select region closest to your Render deployment
4. Copy REST API credentials:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`

#### C. Groq (LLM API)
1. Go to [console.groq.com](https://console.groq.com)
2. Create API key
3. Copy `GROQ_API_KEY`

---

### 2. Deploy Backend (Render.com)

#### Initial Setup:
1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Production deployment"
   git push origin main
   ```

2. **Create Render Web Service:**
   - Go to [dashboard.render.com](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect GitHub repository: `Sayandip05/InvIQ`
   - Configure:
     - **Name:** `inviq-api`
     - **Region:** Choose closest to users
     - **Branch:** `main`
     - **Root Directory:** Leave empty
     - **Runtime:** `Python 3`
     - **Build Command:** `pip install -r requirements.txt && pip install -r backend/requirements-dev.txt`
     - **Start Command:** `cd backend && gunicorn app.main:app --workers 3 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
     - **Plan:** Free (or paid for production)

3. **Add Environment Variables:**
   - Go to Environment tab
   - Add all variables from "Backend Environment Variables" section above
   - **IMPORTANT:** Generate strong `SECRET_KEY`:
     ```bash
     openssl rand -hex 32
     ```

4. **Add Persistent Disk (for ChromaDB):**
   - Go to Disks tab
   - Add disk: `/opt/render/project/data`
   - Size: 1GB (free tier)

5. **Deploy:**
   - Click "Create Web Service"
   - Render will auto-deploy from GitHub

#### Get Deploy Hook URL:
1. Go to Settings → Deploy Hook
2. Copy webhook URL
3. Add to GitHub Secrets as `RENDER_DEPLOY_HOOK_URL`

---

### 3. Deploy Frontend (Vercel)

#### Initial Setup:
1. **Go to [vercel.com](https://vercel.com)**
2. **Import Project:**
   - Click "Add New..." → "Project"
   - Import `Sayandip05/InvIQ` from GitHub
   - Configure:
     - **Framework Preset:** Vite
     - **Root Directory:** `frontend`
     - **Build Command:** `npm run build`
     - **Output Directory:** `dist`

3. **Add Environment Variables:**
   ```
   VITE_API_URL=https://inviq-api.onrender.com
   VITE_WS_URL=wss://inviq-api.onrender.com
   ```

4. **Deploy:**
   - Click "Deploy"
   - Vercel will auto-deploy from GitHub

---

### 4. Setup CI/CD Pipeline

The CI/CD pipeline is already configured in `cicd.yaml` (GitHub Actions).

#### Add GitHub Secrets:
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Add secret:
   - **Name:** `RENDER_DEPLOY_HOOK_URL`
   - **Value:** Your Render deploy hook URL (from step 2)

#### Pipeline Triggers:
- **On Push to `main`:** Runs tests → Builds Docker → Deploys to Render
- **On Pull Request:** Runs tests only (no deployment)

#### Pipeline Jobs:
1. **Test Job:**
   - Runs all backend tests with pytest
   - Uses SQLite for testing (no external DB needed)
   - Fails fast on first error (`-x` flag)

2. **Build Job:**
   - Builds Docker image to verify compilation
   - Only runs if tests pass
   - Only on `main` branch pushes

3. **Deploy Job:**
   - Triggers Render deployment via webhook
   - Only runs if tests AND build succeed
   - Only on `main` branch pushes

---

## 🔄 Auto-Deployment Flow

```
Developer pushes to main
         ↓
GitHub Actions triggered
         ↓
┌────────────────────────┐
│   Job 1: Run Tests     │
│   - pytest backend/    │
│   - Coverage report    │
└───────────┬────────────┘
            ↓ (if pass)
┌────────────────────────┐
│   Job 2: Build Docker  │
│   - docker build       │
│   - Verify compilation │
└───────────┬────────────┘
            ↓ (if pass)
┌────────────────────────┐
│   Job 3: Deploy        │
│   - Trigger Render     │
│   - Trigger Vercel     │
└───────────┬────────────┘
            ↓
Production Updated ✅
```

**Deployment Time:**
- **Tests:** ~2-3 minutes
- **Build:** ~1-2 minutes
- **Render Deploy:** ~3-5 minutes
- **Vercel Deploy:** ~1-2 minutes
- **Total:** ~7-12 minutes

---

## 🏥 Health Checks

### Backend Health Check
```bash
curl https://inviq-api.onrender.com/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-30T12:00:00Z",
  "database": "connected",
  "redis": "connected",
  "chromadb": "available"
}
```

### Frontend Health Check
```bash
curl https://inviq.vercel.app
```

**Expected:** HTML page loads (status 200)

---

## 💻 Run Locally

### Quick Start (Docker):
```bash
# Clone repository
git clone https://github.com/Sayandip05/InvIQ.git
cd InvIQ

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up -d

# Access application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup:

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env
# Edit .env
npm run dev
```

---

## 🐛 Common Deployment Issues

### 1. **Backend fails to start: "Database connection error"**

**Cause:** Invalid `DATABASE_URL` or database not accessible

**Fix:**
```bash
# Verify connection string format
postgresql://user:password@host:port/database

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check Neon firewall rules (usually allows all by default)
```

---

### 2. **Backend fails: "SECRET_KEY not set"**

**Cause:** Missing or empty `SECRET_KEY` environment variable

**Fix:**
```bash
# Generate strong key
openssl rand -hex 32

# Add to Render environment variables
# Restart service
```

---

### 3. **Redis connection fails: "Upstash REST API error"**

**Cause:** Invalid Upstash credentials or network issue

**Fix:**
```bash
# Verify credentials in Upstash console
# Test REST API
curl -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
     $UPSTASH_REDIS_REST_URL/ping

# If fails, regenerate token in Upstash console
# Update Render environment variables
```

---

### 4. **AI Chatbot not working: "GROQ_API_KEY invalid"**

**Cause:** Missing or invalid Groq API key

**Fix:**
```bash
# Verify key at console.groq.com
# Check API key permissions
# Regenerate if needed
# Update Render environment variables
```

---

### 5. **CORS errors in frontend**

**Cause:** Frontend URL not in `CORS_ORIGINS`

**Fix:**
```bash
# Add frontend URL to backend environment
CORS_ORIGINS=https://inviq.vercel.app,https://inviq-preview.vercel.app

# Restart backend service
```

---

### 6. **ChromaDB data lost after restart**

**Cause:** No persistent disk mounted

**Fix:**
```bash
# In Render dashboard:
# 1. Go to Disks tab
# 2. Add persistent disk: /opt/render/project/data
# 3. Update CHROMADB_PATH=/opt/render/project/data/chromadb
# 4. Redeploy
```

---

### 7. **Slow cold starts on Render free tier**

**Cause:** Free tier spins down after 15 minutes of inactivity

**Fix:**
```bash
# Option 1: Upgrade to paid plan (no spin-down)
# Option 2: Use cron job to ping health endpoint every 10 minutes
# Option 3: Accept 30-60s cold start delay
```

---

### 8. **GitHub Actions failing: "pytest not found"**

**Cause:** Missing test dependencies in CI

**Fix:**
```yaml
# In cicd.yaml, ensure both requirements files installed:
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install -r backend/requirements-dev.txt
```

---

### 9. **Vercel build fails: "VITE_API_URL not defined"**

**Cause:** Missing environment variables in Vercel

**Fix:**
```bash
# In Vercel dashboard:
# Settings → Environment Variables
# Add: VITE_API_URL=https://inviq-api.onrender.com
# Redeploy
```

---

### 10. **Rate limiting not working**

**Cause:** Upstash Redis not connected (using in-memory fallback)

**Fix:**
```bash
# Verify Redis connection in logs
# Check UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN
# Note: In-memory rate limiting works per-worker (acceptable for most cases)
```

---

## 📊 Monitoring & Logs

### Backend Logs (Render):
```bash
# View live logs
render logs -s inviq-api --tail

# Or in Render dashboard:
# Service → Logs tab
```

### Frontend Logs (Vercel):
```bash
# View deployment logs
vercel logs inviq-production

# Or in Vercel dashboard:
# Project → Deployments → View Logs
```

### Database Logs (Neon):
```bash
# In Neon dashboard:
# Project → Monitoring → Query Stats
```

---

## 🔐 Security Checklist

Before going to production:

- [ ] Generate strong `SECRET_KEY` (32+ characters)
- [ ] Set strong `ADMIN_PASSWORD`
- [ ] Enable HTTPS only (Render/Vercel handle this)
- [ ] Configure `CORS_ORIGINS` to only allow your frontend
- [ ] Enable rate limiting with Redis
- [ ] Set up database backups (Neon auto-backups on paid plans)
- [ ] Enable audit logging (already implemented)
- [ ] Review and rotate API keys regularly
- [ ] Set up monitoring alerts (Render/Vercel dashboards)
- [ ] Test authentication flow end-to-end
- [ ] Verify token blacklist works (logout invalidation)

---

## 📈 Scaling Considerations

### Current Setup (Free Tier):
- **Render:** 512MB RAM, 0.1 CPU
- **Neon:** 500MB database, 2GB bandwidth
- **Upstash:** 10,000 commands/day
- **Vercel:** 100GB bandwidth

### When to Upgrade:
- **> 100 concurrent users:** Upgrade Render to paid plan (more RAM/CPU)
- **> 10,000 requests/day:** Upgrade Upstash to paid plan
- **> 500MB database:** Upgrade Neon to paid plan
- **> 100GB bandwidth:** Upgrade Vercel to paid plan

### Horizontal Scaling:
- **Backend:** Render auto-scales with paid plans
- **Database:** Neon connection pooling (already configured)
- **Redis:** Upstash global replication (already configured)
- **Frontend:** Vercel CDN (already configured)

---

## 🆘 Support

**Issues:** [GitHub Issues](https://github.com/Sayandip05/InvIQ/issues)  
**Email:** sayandip@inviq.io  
**LinkedIn:** [Sayandip Bar](http://www.linkedin.com/in/sayandipbar2005)

---

**Document Status:** ✅ Complete  
**Last Tested:** April 30, 2026  
**Next Review:** Every 3 months
