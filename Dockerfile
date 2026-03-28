# ── Multi-stage Dockerfile for Smart Inventory Assistant ─────────────────
# Stage 1: Builder — install dependencies in a virtual env
# Stage 2: Runner — slim image with only runtime deps

# ── Stage 1: Builder ────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps for psycopg2 and argon2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runner ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime libs (no compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code (backend only — no frontend in API container)
COPY backend/app ./backend/app
COPY requirements.txt .

# Set Python path so `from app.xxx` imports resolve
ENV PYTHONPATH=/app/backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check using curl (lighter than importing httpx)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn for production (proper worker management, graceful restarts)
# Workers = 2 * CPU cores + 1 (default 3 for 1-core container)
# Use --preload to share memory across workers
CMD ["gunicorn", "backend.app.main:app", \
     "--worker-class", "uvicorn.UvicornWorker", \
     "--workers", "3", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--preload", \
     "--access-logfile", "-"]
