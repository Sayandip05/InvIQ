# Scaling & Cost Analysis - InvIQ

**Version:** 1.0  
**Last Updated:** April 30, 2026  
**Author:** Sayandip Bar

---

## 💰 Current Free Tier Usage

### Render.com (Backend)
- **Plan:** Free Tier
- **Resources:** 512MB RAM, 0.1 CPU
- **Hours:** 750 hours/month (spins down after 15 min inactivity)
- **Cold start:** 30-60 seconds
- **Bandwidth:** Unlimited
- **Current usage:** ~200 hours/month (demo/testing)

### Neon (Database)
- **Plan:** Free Tier
- **Storage:** 500MB database (currently ~50MB used)
- **Bandwidth:** 2GB/month (currently ~200MB used)
- **Connections:** Up to 60 concurrent
- **Backups:** Automatic daily backups (7 days retention)
- **Current usage:** 10% of limits

### Upstash Redis (Cache)
- **Plan:** Free Tier
- **Commands:** 10,000 commands/day (currently ~1,000/day)
- **Storage:** 256MB (currently ~10MB used)
- **Bandwidth:** 200MB/day
- **Current usage:** 10% of limits

### Vercel (Frontend)
- **Plan:** Free Tier (Hobby)
- **Bandwidth:** 100GB/month (currently ~5GB used)
- **Builds:** 100 hours/month (currently ~2 hours used)
- **Deployments:** Unlimited
- **Current usage:** 5% of limits

### Groq (LLM API)
- **Plan:** Free Tier
- **Requests:** 30 requests/minute
- **Tokens:** 14,400 tokens/minute
- **Current usage:** ~500 requests/day (well within limits)

---

## 🚨 Bottlenecks at Scale

### At 100 Users (Current Capacity)
✅ **All services handle this comfortably**
- Render: ~50 concurrent requests
- Database: ~20 connections
- Redis: ~5,000 commands/day
- No issues expected

---

### At 1,000 Users (First Bottleneck)

**What Breaks First:**

1. **Render Free Tier** 🔴 (CRITICAL)
   - **Issue:** 512MB RAM insufficient for 100+ concurrent users
   - **Symptom:** Out of memory errors, slow responses
   - **Solution:** Upgrade to Starter ($7/month) - 512MB → 2GB RAM

2. **Groq API Rate Limits** 🟡 (HIGH)
   - **Issue:** 30 requests/minute = ~43,200 requests/day
   - **Symptom:** 429 errors during peak hours
   - **Solution:** Implement request queuing or upgrade to paid tier

3. **Database Connections** 🟡 (MEDIUM)
   - **Issue:** 60 concurrent connections limit
   - **Symptom:** "Too many connections" errors
   - **Solution:** Connection pooling (already implemented) + upgrade Neon

4. **Upstash Redis** 🟢 (LOW)
   - **Issue:** 10,000 commands/day limit
   - **Symptom:** Cache misses, slower responses
   - **Solution:** Upgrade to paid tier ($10/month) - 100K commands/day

---

### At 10,000 Users (Major Scaling Needed)

**What Breaks:**

1. **Single Backend Instance** 🔴
   - Need horizontal scaling (multiple instances)
   - Load balancer required
   - Sticky sessions for WebSocket

2. **Database Write Throughput** 🔴
   - Need read replicas
   - Consider database sharding

3. **WebSocket Connections** 🔴
   - Single instance can't handle 10K+ WebSocket connections
   - Need Redis pub/sub for cross-instance broadcasting

4. **LLM API Costs** 🔴
   - Free tier insufficient
   - Need paid plan or self-hosted LLM

---

## 📈 Scaling Strategy

### Phase 1: 100-500 Users (Month 1-3)
**Action:** Upgrade Render to Starter  
**Cost:** ₹600/month ($7/month)  
**Why:** More RAM, no cold starts, better performance

---

### Phase 2: 500-1,000 Users (Month 3-6)
**Actions:**
1. Upgrade Neon to Pro (₹2,100/month)
   - 8GB database
   - 50GB bandwidth
   - 200 concurrent connections
   
2. Upgrade Upstash to paid (₹850/month)
   - 100K commands/day
   - 1GB storage

**Total Cost:** ₹3,550/month (~$42/month)

---

### Phase 3: 1,000-5,000 Users (Month 6-12)
**Actions:**
1. Upgrade Render to Standard (₹2,100/month)
   - 4GB RAM, 2 CPU
   - Better performance

2. Add database read replica (₹2,100/month)
   - Separate read/write traffic
   - Reduce primary DB load

3. Upgrade Groq to paid or self-host LLM (₹4,250/month)
   - Higher rate limits
   - Better reliability

**Total Cost:** ₹12,750/month (~$150/month)

---

### Phase 4: 5,000-10,000 Users (Month 12-18)
**Actions:**
1. Move to AWS EC2 or DigitalOcean (₹8,500/month)
   - 3x backend instances (load balanced)
   - Full control over infrastructure

2. Upgrade Neon to Team (₹8,500/month)
   - 100GB database
   - 250GB bandwidth
   - Point-in-time recovery

3. Redis Cluster (₹4,250/month)
   - Distributed caching
   - Pub/sub for WebSocket

4. CDN for static assets (₹850/month)
   - Faster global delivery

**Total Cost:** ₹29,750/month (~$350/month)

---

### Phase 5: 10,000+ Users (Month 18+)
**Actions:**
1. Kubernetes cluster (₹17,000/month)
   - Auto-scaling
   - High availability

2. Managed PostgreSQL (₹12,750/month)
   - Multi-region replication
   - Automatic failover

3. Self-hosted LLM (₹21,250/month)
   - GPU instance for inference
   - No API rate limits

4. Monitoring & Observability (₹4,250/month)
   - Datadog/New Relic
   - 24/7 alerting

**Total Cost:** ₹68,000/month (~$800/month)

---

## 💵 Cost at Different Scales

| Users | Monthly Cost (₹) | Monthly Cost ($) | Per User Cost |
|-------|------------------|------------------|---------------|
| **100** | ₹0 (Free tier) | $0 | ₹0 |
| **500** | ₹600 | $7 | ₹1.20 |
| **1,000** | ₹3,550 | $42 | ₹3.55 |
| **5,000** | ₹12,750 | $150 | ₹2.55 |
| **10,000** | ₹29,750 | $350 | ₹2.98 |
| **50,000** | ₹68,000 | $800 | ₹1.36 |

**Key Insight:** Per-user cost **decreases** as you scale (economies of scale)

---

## 🎯 Cost Optimization Decisions Made

### 1. **Serverless/Managed Services**
**Decision:** Use Render, Neon, Upstash instead of self-managed  
**Why:** Zero ops overhead, automatic scaling, pay-as-you-grow  
**Savings:** ~₹25,500/month ($300/month) in DevOps time

---

### 2. **Modular Monolith**
**Decision:** Single backend instead of microservices  
**Why:** 1 instance vs 5+ instances  
**Savings:** ₹8,500/month ($100/month) in infrastructure

---

### 3. **Redis Caching**
**Decision:** Cache analytics (2-5 min TTL)  
**Why:** Reduces database queries by 80%  
**Savings:** Can stay on smaller database tier longer

---

### 4. **Groq (Not OpenAI)**
**Decision:** Groq LLaMA 3.3 70B instead of GPT-4  
**Why:** 10x faster, 5x cheaper  
**Savings:** ₹12,750/month ($150/month) at 1K users

---

### 5. **Connection Pooling**
**Decision:** SQLAlchemy connection pool (max 20)  
**Why:** Reuse connections, reduce overhead  
**Savings:** Can handle 5x more users on same database tier

---

### 6. **No Background Jobs**
**Decision:** Synchronous processing (no Celery workers)  
**Why:** No additional worker instances needed  
**Savings:** ₹2,100/month ($25/month) per worker

---

### 7. **WebSocket (Not Polling)**
**Decision:** WebSocket for real-time updates  
**Why:** 1 connection vs 1 request/second polling  
**Savings:** 99% reduction in bandwidth costs

---

### 8. **Vercel (Not Custom Server)**
**Decision:** Vercel for frontend hosting  
**Why:** Free tier, global CDN, auto-scaling  
**Savings:** ₹2,100/month ($25/month) for frontend server

---

## 📊 When to Upgrade What

| Metric | Threshold | Action | Cost Impact |
|--------|-----------|--------|-------------|
| **Concurrent users** | > 50 | Upgrade Render to Starter | +₹600/month |
| **Database size** | > 400MB | Upgrade Neon to Pro | +₹2,100/month |
| **Redis commands** | > 8K/day | Upgrade Upstash to paid | +₹850/month |
| **API requests** | > 100K/day | Add caching layer | ₹0 (optimization) |
| **Response time** | > 500ms (p95) | Add read replica | +₹2,100/month |
| **LLM requests** | > 40K/day | Upgrade Groq or self-host | +₹4,250/month |
| **WebSocket connections** | > 1,000 | Horizontal scaling + Redis pub/sub | +₹4,250/month |
| **Database connections** | > 50 | Upgrade Neon tier | +₹2,100/month |

---

## 🚀 When to Move from Render to EC2

**Move when:**
1. **Users > 5,000** - Need horizontal scaling
2. **Custom infrastructure** - Specific OS/network requirements
3. **Cost optimization** - Reserved instances cheaper at scale
4. **Compliance** - Need dedicated hardware/VPC

**Don't move if:**
- Users < 5,000 (Render is cheaper + easier)
- Team < 3 developers (no DevOps capacity)
- Rapid iteration needed (Render auto-deploys)

---

## 🔄 When to Add Read Replicas

**Add when:**
1. **Read/write ratio > 80/20** (most queries are reads)
2. **Database CPU > 70%** consistently
3. **Query response time > 200ms** (p95)
4. **Users > 1,000** with heavy analytics usage

**How:**
- Neon Pro tier includes read replicas
- Route analytics queries to replica
- Keep writes on primary
- Use connection pooling for both

---

## 💡 Cost Optimization Tips

### Short-term (0-1K users):
1. ✅ Use free tiers (already doing)
2. ✅ Cache aggressively (2-5 min TTL)
3. ✅ Use Groq instead of OpenAI
4. ✅ Modular monolith (not microservices)

### Medium-term (1K-10K users):
1. Add database indexes (faster queries)
2. Implement query result caching
3. Use CDN for static assets
4. Optimize LLM prompts (fewer tokens)

### Long-term (10K+ users):
1. Self-host LLM (GPU instance)
2. Database sharding by org_id
3. Multi-region deployment
4. Reserved instances (AWS/GCP)

---

## 📈 Revenue vs Cost Analysis

**Assumptions:**
- Pricing: ₹500/user/month ($6/user/month)
- Conversion: 10% of users are paying

| Users | Paying Users | Revenue (₹) | Cost (₹) | Profit (₹) | Margin |
|-------|--------------|-------------|----------|------------|--------|
| 100 | 10 | ₹5,000 | ₹0 | ₹5,000 | 100% |
| 500 | 50 | ₹25,000 | ₹600 | ₹24,400 | 98% |
| 1,000 | 100 | ₹50,000 | ₹3,550 | ₹46,450 | 93% |
| 5,000 | 500 | ₹2,50,000 | ₹12,750 | ₹2,37,250 | 95% |
| 10,000 | 1,000 | ₹5,00,000 | ₹29,750 | ₹4,70,250 | 94% |

**Key Insight:** High profit margins (90%+) due to cost-optimized architecture

---

## 🎯 Summary

### Current State (Free Tier):
- ✅ Supports 100 users comfortably
- ✅ Zero infrastructure cost
- ✅ 10% resource utilization

### First Upgrade (₹600/month):
- ✅ Supports 500 users
- ✅ No cold starts
- ✅ Better performance

### Production Ready (₹3,550/month):
- ✅ Supports 1,000 users
- ✅ No rate limits
- ✅ High availability

### Enterprise Scale (₹68,000/month):
- ✅ Supports 50,000+ users
- ✅ Multi-region
- ✅ 99.99% uptime

---

**Document Status:** ✅ Complete  
**Last Reviewed:** April 30, 2026  
**Next Review:** Quarterly (or when hitting 80% of any limit)
