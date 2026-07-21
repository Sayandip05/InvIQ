# ── Multi-stage Dockerfile for InvIQ Smart Inventory Assistant ───────────
# Optimized for cloud deployment with Neon PostgreSQL + Upstash Redis
# Stage 1: Builder — install dependencies into a virtual environment
# Stage 2: Runner — slim image that copies only the venv and app code

# ── Stage 1: Builder ────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps needed to compile psycopg2 and argon2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment — this is the correct multi-stage pattern.
# The entire venv folder is copied to the runner stage, so every package
# (including typing_extensions and all transitive deps) is captured.
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Upgrade pip inside the venv
RUN pip install --no-cache-dir --upgrade pip

# Pre-install CPU-only PyTorch BEFORE sentence-transformers.
# Without this, sentence-transformers pulls torch + full CUDA stack (~2 GB).
# CPU-only torch is ~200 MB and sufficient for embedding inference.
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install all remaining Python dependencies into the venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runner ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime system libs only (no compiler) + curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create log directory for the rotating file handler
RUN mkdir -p /app/logs

# Copy the entire venv from the builder stage
COPY --from=builder /venv /venv

# Copy application code (backend only — frontend served separately)
COPY backend/app ./backend/app
COPY requirements.txt .

# Activate the venv for all subsequent commands
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

# Ensure venv site-packages are FIRST in Python's module search path.
# This prevents the system Python from shadowing venv packages (e.g. typing_extensions).
ENV PYTHONPATH="/app/backend"
ENV PYTHONHOME=""
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port 8000 for FastAPI
EXPOSE 8000

# Health check endpoint (used by Docker and orchestrators)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use explicit venv path to guarantee the correct Python interpreter and
# all venv-installed packages are used — avoids system Python shadowing.
CMD ["/venv/bin/gunicorn", "backend.app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "3", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
