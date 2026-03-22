# Deployment

**Project:** Smart Inventory Assistant  
**Updated:** March 20, 2026

---

## 1. Cloud Provider

**Provider:** AWS  
**Reason:** Mature services, good Python ecosystem support, cost-effective for startup

---

## 2. Environment Overview

| Environment | Compute | Database | Vector Store | Deployment |
|-------------|---------|----------|-------------|------------|
| **Development** | Local machine | SQLite (file) | ChromaDB (local) | Manual (`uvicorn`) |
| **Staging** | AWS EC2 t3.small | RDS PostgreSQL db.t3.micro | ChromaDB (local) | GitHub Actions |
| **Production** | AWS ECS Fargate (2 tasks) | RDS PostgreSQL db.t3.medium | ChromaDB (EFS) | GitHub Actions |

---

## 3. Docker Setup

### 3.1 Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
ENV PYTHONPATH=/app
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
Push Code → Build → Test (pytest) → Lint (ruff) → Build Docker → Push ECR → Deploy Staging → Manual Approval → Deploy Production
```

### 4.1 Pipeline Steps (cicd.yaml)

1. **Lint** — ruff (Python), ESLint (JavaScript)
2. **Test** — pytest (Python), Vitest (JavaScript)
3. **Build** — Docker image build
4. **Push** — ECR registry
5. **Deploy Staging** — ECS task definition update
6. **Deploy Production** — ECS task definition update (manual approval gate)

---

## 5. Environment Variables by Stage

### Development (.env)

```env
DATABASE_PATH=../database/smart_inventory.db
ENVIRONMENT=development
GROQ_API_KEY=<key>
LANGCHAIN_API_KEY=<optional>
```

### Staging

```env
DATABASE_URL=postgresql://user:pass@staging-db:5432/inventory
ENVIRONMENT=staging
GROQ_API_KEY=<key>
```

### Production

```env
DATABASE_URL=postgresql://user:pass@prod-db.amazonaws.com:5432/inventory
ENVIRONMENT=production
GROQ_API_KEY=<secrets-manager>
```

---

## 6. Security

| Layer | Implementation |
|-------|----------------|
| **Network** | VPC with private subnets, security groups |
| **SSL/TLS** | ACM certificate, HTTPS only |
| **API** | Rate limiting (Phase 1), API Keys (Phase 1) |
| **Database** | IAM authentication, encryption at rest |
| **Secrets** | AWS Secrets Manager |
| **Backup** | RDS automated backups (7 days retention) |

---

## 7. Monitoring

| Metric | Tool |
|--------|------|
| **Logs** | CloudWatch Logs |
| **Metrics** | CloudWatch Metrics |
| **Alerts** | CloudWatch Alarms → SNS → Email |
| **Tracing** | LangSmith (AI calls) |
| **Uptime** | CloudWatch Synthetics |

---

## 8. Rollback Steps

### 8.1 ECS Rollback

```bash
# List previous task definition revisions
aws ecs list-task-definitions --family smart-inventory --sort DESC

# Deregister bad revision
aws ecs deregister-task-definition --task-definition smart-inventory:NEW_BAD_REVISION

# Register previous good revision
aws ecs update-service --cluster production --service smart-inventory --task-definition smart-inventory:GOOD_REVISION --region us-east-1
```

### 8.2 Database Rollback

```bash
# Restore from RDS snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier inventory-restore \
  --db-snapshot-identifier rds:inventory-YYYY-MM-DD \
  --region us-east-1
```

---

## 9. Free-Tier Limitations

| Service | Free Tier | Usage |
|---------|-----------|-------|
| **EC2** | 750h/month t2.micro (12 months) | Staging only |
| **RDS** | 750h/month db.t3.micro (12 months) | Dev/Staging |
| **S3** | 5GB | Logs, backups |
| **CloudWatch** | 10 custom metrics | Basic monitoring |
| **ECS Fargate** | None | Production needs paid |

**Estimated Production Cost:** $95–195/month

---

## 10. Infrastructure Checklist (Pre-Production)

- [ ] Replace placeholder Dockerfile with multi-stage production image
- [ ] Configure RDS PostgreSQL with backup retention
- [ ] Set up EFS for ChromaDB vector persistence
- [ ] Configure Secrets Manager for API keys
- [ ] Set up ALB with health checks
- [ ] Configure CloudWatch dashboards
- [ ] Set up SNS notification topics
- [ ] Define ECS autoscaling policy
- [ ] Create Route 53 DNS records
- [ ] Enable ACM TLS certificate
- [ ] Configure WAF rate limiting rules
- [ ] Test rollback procedure in staging
