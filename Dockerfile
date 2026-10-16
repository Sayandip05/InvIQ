# ── Multi-stage Dockerfile for InvIQ Smart Inventory Assistant (Backend) ─────
# Optimized for cloud deployment (Azure App Service / Azure Container Apps / Docker)
# Stage 1: Builder — install dependencies into a virtual environment
# Stage 2: Runner — slim image with non-root security context

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies needed to compile C-extensions (psycopg2, argon2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runner ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# Install minimal runtime system libraries + curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root system user and group
RUN groupadd -r -g 1001 inviq && \
    useradd -r -u 1001 -g inviq -d /app -s /bin/bash inviq

# Copy the entire pre-built venv from builder
COPY --from=builder /venv /venv

# Copy application code and Alembic migrations
COPY backend/app ./backend/app
COPY backend/alembic ./backend/alembic
COPY backend/alembic.ini ./backend/alembic.ini
COPY requirements.txt .

# Create logs directory and ensure non-root user permissions
RUN mkdir -p /app/logs && chown -R inviq:inviq /app

# Environment variables
ENV PATH="/venv/bin:$PATH" \
    VIRTUAL_ENV="/venv" \
    PYTHONPATH="/app/backend:/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Switch to non-root user
USER inviq

# Expose default HTTP port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run alembic migrations and start production gunicorn server
CMD ["sh", "-c", \
     "cd /app/backend && /venv/bin/alembic upgrade head && \
      cd /app && exec /venv/bin/gunicorn app.main:app \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers 3 \
        --bind 0.0.0.0:${PORT:-8000} \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        --log-level info"]
