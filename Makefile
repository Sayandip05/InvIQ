.PHONY: help dev backend frontend worker beat test clean lint build

ROOT_DIR := $(shell pwd)
PYTHON   ?= $(ROOT_DIR)/venv/bin/python
UVICORN  ?= $(ROOT_DIR)/venv/bin/uvicorn
CELERY   ?= $(ROOT_DIR)/venv/bin/celery
PYTEST   ?= $(ROOT_DIR)/venv/bin/pytest

help:
	@echo "╔═══════════════════════════════════════════════════════════════╗"
	@echo "║               InvIQ Management & Execution Makefile          ║"
	@echo "╚═══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev        - Run Backend, Frontend, and Celery Worker concurrently"
	@echo "  make backend    - Start FastAPI backend server with Uvicorn (Port 8000)"
	@echo "  make frontend   - Start Vite frontend dev server (Port 5173)"
	@echo "  make worker     - Start Celery background worker (--pool=solo)"
	@echo "  make beat       - Start Celery Beat periodic scheduler"
	@echo "  make test       - Run all backend unit & integration tests"
	@echo "  make clean      - Remove __pycache__, .pytest_cache and temp files"
	@echo ""

# Run all 3 services concurrently (Backend + Frontend + Worker)
dev:
	@echo "🚀 Starting InvIQ full stack: Backend (8000), Frontend (5173), and Worker..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
	(cd backend && $(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --reload) & \
	(cd frontend && npm run dev) & \
	(cd backend && $(CELERY) -A app.workers.celery_app worker --loglevel=info --pool=solo) & \
	wait

# Individual services
backend:
	@echo "⚡ Starting FastAPI Backend on http://127.0.0.1:8000..."
	@cd backend && $(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	@echo "⚡ Starting Vite Frontend on http://localhost:5173..."
	@cd frontend && npm run dev

worker:
	@echo "⚡ Starting Celery Worker..."
	@cd backend && $(CELERY) -A app.workers.celery_app worker --loglevel=info --pool=solo

beat:
	@echo "⚡ Starting Celery Beat Scheduler..."
	@cd backend && $(CELERY) -A app.workers.celery_app beat --loglevel=info

test:
	@echo "🧪 Running Pytest Test Suite..."
	@cd backend && $(PYTEST)

lint:
	@echo "🔍 Running Frontend ESLint..."
	@cd frontend && npm run lint

build:
	@echo "📦 Building Frontend Production Bundle..."
	@cd frontend && npm run build

clean:
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cache cleaned."
