@echo off
REM Test runner script for Windows with coverage reporting

echo 🧪 Running InvIQ Test Suite...
echo ================================

REM Check if dependencies are installed
python -c "import pytest" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Test dependencies not found. Installing...
    pip install -r ..\requirements.txt
)

REM Run tests with coverage
pytest ^
    --cov=app ^
    --cov-report=html ^
    --cov-report=term-missing ^
    --cov-report=xml ^
    --cov-fail-under=80 ^
    -v ^
    %*

REM Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ All tests passed!
    echo 📊 Coverage report generated in htmlcov/index.html
) else (
    echo.
    echo ❌ Some tests failed!
    exit /b 1
)
