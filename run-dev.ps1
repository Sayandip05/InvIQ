# run-dev.ps1 - Start InvIQ full stack on Windows
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvScripts = Join-Path $RootDir "venv\Scripts"

$Uvicorn = Join-Path $VenvScripts "uvicorn.exe"
$Celery = Join-Path $VenvScripts "celery.exe"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Starting InvIQ Full Stack (Backend + Frontend + Worker)" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Check venv
if (-not (Test-Path $Uvicorn)) {
    Write-Error "Virtual environment not found at $VenvScripts. Please create venv and install dependencies."
    exit 1
}

# Check frontend node_modules
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

Write-Host "⚡ Launching FastAPI Backend on http://127.0.0.1:8000 in a new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'InvIQ - Backend (FastAPI)'; cd '$BackendDir'; & '$Uvicorn' app.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "⚡ Launching Vite Frontend on http://localhost:5173 in a new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'InvIQ - Frontend (Vite)'; cd '$FrontendDir'; npm run dev"

Write-Host "⚡ Launching Celery Worker in a new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'InvIQ - Celery Worker'; cd '$BackendDir'; & '$Celery' -A app.workers.celery_app worker --loglevel=info --pool=solo"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "✅ All 3 services started in dedicated terminal windows!" -ForegroundColor Green
Write-Host "   - Backend API:    http://127.0.0.1:8000" -ForegroundColor White
Write-Host "   - API Docs:       http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "   - Frontend UI:    http://localhost:5173" -ForegroundColor White
Write-Host "   - Celery Worker:  Running (pool=solo)" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Cyan
