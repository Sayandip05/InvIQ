#!/bin/bash
# Test runner script with coverage reporting

echo "🧪 Running InvIQ Test Suite..."
echo "================================"

# Check if dependencies are installed
if ! python -c "import pytest" 2>/dev/null; then
    echo "⚠️  Test dependencies not found. Installing..."
    pip install -r ../requirements.txt
fi

# Run tests with coverage
pytest \
    --cov=app \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=80 \
    -v \
    "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in htmlcov/index.html"
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi
