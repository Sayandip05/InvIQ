# Deployment

**Project:** InvIQ — Smart Inventory Assistant  
**Updated:** April 9, 2026

---

## 1. Cloud Provider

**Provider:** Render (Backend) + Supabase (PostgreSQL) + Vercel (Frontend)  
**Reason:** Free tier friendly, Python support, managed PostgreSQL, auto-deploy from git

---

## 2. Environment Overview

| Environment | Compute | Database | Vector Store | Deployment |
|-------------|---------|----------|-------------|------------|
| **Development** | Local machine | SQLite (file) | ChromaDB (local) | Manual (`uvicorn`) |
| **Staging** | Render (Free) | Supabase PostgreSQL | ChromaDB (local) | GitHub Actions auto-deploy |
| **Production** | Render (Paid) | Supabase PostgreSQL | ChromaDB (persistent) | GitHub Actions auto-deploy |

---

## 3. Docker Setup

### 3.1 Dockerfile (Multi-stage for production)

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target=/app/deps

FROM python:3.11-slim
COPY --from=builder /app/deps /app/deps
ENV PYTHONPATH=/app
ENV PATH=/app/deps/bin:$PATH
COPY backend/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 docker-compose.yml (Development)

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_PATH=/data/smart_inventory.db
      - ENVIRONMENT=development
    volumes:
      - ./database:/data
      - ./data/chromadb:/chromadb

  frontend:
    build: ./frontend/main-dashboard
    ports:
      - "5173:5173"
    stdin_open: true
```

---

## 4. CI/CD Pipeline

```
Push Code → Lint (ruff) → Test (pytest) → Build Docker → Deploy Render
```

### 4.1 Pipeline Steps (cicd.yaml)

1. **Lint** — ruff (Python)
2. **Test** — pytest with PostgreSQL service container
3. **Build** — Docker image build
4. **Deploy** — Render auto-deploy from main branch

---

## 5. Environment Variables by Stage

### Development (.env)

```env
DATABASE_PATH=../database/smart_inventory.db
ENVIRONMENT=development
GROQ_API_KEY=<key>
LANGCHAIN_API_KEY=<optional>
```

### Staging/Production

```env
DATABASE_URL=postgresql://[user]:[pass]@host:5432/inventory
REDIS_URL=redis://[host]:6379
ENVIRONMENT=production
GROQ_API_KEY=<secrets-manager>
SECRET_KEY=<strong-random-key>
CORS_ORIGINS=https://your-domain.vercel.app
```

---

## 6. Security

| Layer | Implementation |
|-------|----------------|
| **Network** | Render's private networking, security groups |
| **SSL/TLS** | Render auto-provisioned TLS |
| **API** | Rate limiting (slowapi + Redis), token blacklist |
| **Database** | Supabase row-level security, encryption at rest |
| **Secrets** | Render Environment Variables |
| **Backup** | Supabase Point-in-time recovery |

---

## 7. Monitoring

| Metric | Tool |
|--------|------|
| **Logs** | Render built-in logs |
| **Metrics** | Render Metrics (paid) |
| **Alerts** | Health check endpoint + external monitor |
| **Tracing** | LangSmith (AI calls) |
| **Uptime** | Render always-on (paid) or external monitor |

---

## 8. Rollback Steps

### 8.1 Render Rollback

```bash
# Deploy previous commit
git push render <previous-commit-sha>:main --force
```

### 8.2 Database Rollback

```bash
# Supabase point-in-time recovery from dashboard
# Or restore from Supabase dashboard → Backups
```

---

## 9. Free-Tier Limitations

| Service | Free Tier | Usage |
|---------|-----------|-------|
| **Render** | 750h/month (spins down after 15min inactivity) | Dev/Staging |
| **Supabase** | 500MB DB, 1GB file storage, 100K API calls/day | Dev/Staging |
| **Vercel** | 100GB bandwidth, serverless functions | Frontend |
| **ChromaDB** | Local only (no cloud) | Dev |

**Estimated Production Cost:** $20–40/month (Render paid + Supabase pro)

---

## 10. Infrastructure Checklist (Pre-Production)

- [x] Multi-stage Dockerfile for production
- [x] Docker-compose for local dev
- [x] Render.com account and auto-deploy configured
- [x] Supabase PostgreSQL project created
- [x] Environment variables configured in Render
- [x] Health check endpoint (`/health`) implemented
- [x] CORS configured for frontend domain
- [x] Redis/Upstash configured for caching and rate limiting
- [x] Custom domain (optional)
- [x] CI/CD GitHub Actions pipeline tested
