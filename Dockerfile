# ── Multi-stage Dockerfile for InvIQ Smart Inventory Assistant ───────────
# Optimized for cloud deployment with Neon PostgreSQL + Upstash Redis
# Stage 1: Builder — install dependencies in a virtual env
# Stage 2: Runner — slim image with only runtime deps

# ── Stage 1: Builder ────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps for psycopg2 (PostgreSQL) and argon2 (password hashing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runner ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime libs (no compiler) + curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code (backend only — frontend served separately)
COPY backend/app ./backend/app
COPY requirements.txt .

# Create directory for ChromaDB vector store persistence
RUN mkdir -p /app/data/chromadb && chmod 755 /app/data/chromadb

# Set Python path so `from app.xxx` imports resolve correctly
ENV PYTHONPATH=/app/backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port 8000 for FastAPI
EXPOSE 8000

# Health check endpoint (used by Docker and orchestrators)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn for production
# - 3 workers (suitable for 1-core container, adjust based on CPU)
# - uvicorn worker class for async support
# - 120s timeout for LLM API calls
# - preload for memory efficiency across workers
# - access logs to stdout for container logging
CMD ["gunicorn", "backend.app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "3", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
