.PHONY: help dev backend frontend worker beat test clean

ifeq ($(OS),Windows_NT)
ROOT_DIR := $(CURDIR)
VENV     := $(ROOT_DIR)/venv/Scripts
PYTHON   := $(subst /,\,$(VENV)/python.exe)
UVICORN  := $(subst /,\,$(VENV)/uvicorn.exe)
CELERY   := $(subst /,\,$(VENV)/celery.exe)
PYTEST   := $(subst /,\,$(VENV)/pytest.exe)
else
ROOT_DIR := $(CURDIR)
VENV     := $(ROOT_DIR)/venv/bin
PYTHON   := $(VENV)/python
UVICORN  := $(VENV)/uvicorn
CELERY   := $(VENV)/celery
PYTEST   := $(VENV)/pytest
endif

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
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -ExecutionPolicy Bypass -File .\run-dev.ps1
else
	@echo "🚀 Starting InvIQ full stack: Backend (8000), Frontend (5173), and Worker..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
	(cd backend && "$(UVICORN)" app.main:app --host 127.0.0.1 --port 8000 --reload) & \
	(cd frontend && npm run dev) & \
	(cd backend && "$(CELERY)" -A app.workers.celery_app worker --loglevel=info --pool=solo) & \
	wait
endif

# Individual services
backend:
	@echo "⚡ Starting FastAPI Backend on http://127.0.0.1:8000..."
	@cd backend && "$(UVICORN)" app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	@echo "⚡ Starting Vite Frontend on http://localhost:5173..."
	@cd frontend && npm run dev

worker:
	@echo "⚡ Starting Celery Worker..."
	@cd backend && "$(CELERY)" -A app.workers.celery_app worker --loglevel=info --pool=solo

beat:
	@echo "⚡ Starting Celery Beat Scheduler..."
	@cd backend && "$(CELERY)" -A app.workers.celery_app beat --loglevel=info

test:
	@echo "🧪 Running Pytest Test Suite..."
	@cd backend && "$(PYTEST)"

clean:
ifeq ($(OS),Windows_NT)
	@echo "🧹 Cleaning cache files..."
	@powershell -NoProfile -Command "Get-ChildItem -Recurse -Include __pycache__,.pytest_cache | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Get-ChildItem -Recurse -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue"
	@echo "✅ Cache cleaned."
else
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cache cleaned."
endif
