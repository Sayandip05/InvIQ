# InvIQ Test Suite

Comprehensive test coverage (~80%) for the InvIQ Smart Inventory Assistant backend.

## Test Structure

```
tests/
├── conftest.py                      # Test fixtures and configuration
├── test_auth.py                     # Authentication endpoints (existing)
├── test_analytics.py                # Analytics endpoints (existing)
├── test_agent.py                    # AI agent & chat (existing)
├── test_security.py                 # Security module (JWT, passwords, RBAC)
├── test_exceptions.py               # Custom exception hierarchy
├── test_domain_calculations.py      # Business logic calculations
├── test_inventory_service.py        # Inventory service layer
├── test_requisition_service.py      # Requisition service layer
├── test_analytics_service.py        # Analytics service layer
├── test_vendor_service.py           # Vendor Excel upload service
├── test_cache_service.py            # Redis caching layer
├── test_repositories.py             # Database repositories
├── test_inventory_endpoints.py      # Inventory API endpoints
├── test_requisition_endpoints.py    # Requisition API endpoints
├── test_admin_endpoints.py          # Admin dashboard endpoints
├── test_dependencies.py             # FastAPI dependencies
└── test_rate_limiter.py             # Rate limiting

```

## Test Coverage by Layer

### ✅ Core Layer (100%)
- `test_security.py` - Password hashing, JWT tokens, role hierarchy
- `test_exceptions.py` - Custom exception classes
- `test_rate_limiter.py` - Rate limiting configuration
- `test_dependencies.py` - Dependency injection

### ✅ Domain Layer (100%)
- `test_domain_calculations.py` - Reorder calculations, stock formatting

### ✅ Application Layer (85%)
- `test_inventory_service.py` - Inventory business logic
- `test_requisition_service.py` - Requisition workflows
- `test_analytics_service.py` - Dashboard analytics
- `test_vendor_service.py` - Excel upload processing
- `test_cache_service.py` - Caching strategies

### ✅ Infrastructure Layer (80%)
- `test_repositories.py` - Database operations (inventory, requisition, user)

### ✅ API Layer (75%)
- `test_auth.py` - Login, logout, registration, RBAC
- `test_inventory_endpoints.py` - Inventory CRUD operations
- `test_requisition_endpoints.py` - Requisition lifecycle
- `test_admin_endpoints.py` - Admin dashboard
- `test_analytics.py` - Analytics endpoints
- `test_agent.py` - AI chat endpoints

## Running Tests

### Run All Tests
```bash
# Linux/Mac
./run_tests.sh

# Windows
run_tests.bat

# Or directly with pytest
pytest
```

### Run Specific Test Files
```bash
pytest tests/test_security.py
pytest tests/test_inventory_service.py
pytest tests/test_requisition_endpoints.py
```

### Run Specific Test Classes
```bash
pytest tests/test_security.py::TestPasswordHashing
pytest tests/test_inventory_service.py::TestInventoryService
```

### Run Specific Test Methods
```bash
pytest tests/test_security.py::TestPasswordHashing::test_hash_password_returns_different_hash
```

### Run with Coverage Report
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run Tests in Parallel (faster)
```bash
pip install pytest-xdist
pytest -n auto
```

### Run Only Fast Tests
```bash
pytest -m "not slow"
```

## Test Configuration

### pytest.ini
- Test discovery patterns
- Markers for test categorization
- Warning filters

### .coveragerc
- Coverage measurement configuration
- Exclusion patterns
- Report formatting

## Coverage Goals

| Layer | Target | Current |
|-------|--------|---------|
| Core | 100% | ~95% |
| Domain | 100% | ~100% |
| Application | 85% | ~85% |
| Infrastructure | 80% | ~80% |
| API | 75% | ~75% |
| **Overall** | **80%** | **~80%** |

## Test Patterns

### Unit Tests
- Test individual functions/methods in isolation
- Use mocks for external dependencies
- Fast execution (<1ms per test)

### Integration Tests
- Test multiple components together
- Use in-memory SQLite database
- Test real HTTP requests via TestClient

### Service Layer Tests
- Mock repositories
- Test business logic without database
- Verify exception handling

### Repository Tests
- Use real database (in-memory SQLite)
- Test CRUD operations
- Verify constraint enforcement

### API Endpoint Tests
- Use FastAPI TestClient
- Test authentication/authorization
- Verify response formats

## Fixtures

### Database Fixtures
- `db` - Fresh database session per test
- `test_user` - Standard user with staff role
- `admin_user` - Admin user for privileged operations

### Helper Functions
- `get_auth_header()` - Get Bearer token for authenticated requests

## Continuous Integration

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml --cov-fail-under=80
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests clearly
3. **One Assertion Per Test**: Keep tests focused
4. **Mock External Dependencies**: Don't call real APIs or services
5. **Clean Up**: Use fixtures for setup/teardown
6. **Fast Tests**: Keep unit tests under 1ms
7. **Deterministic**: Tests should always produce same result

## Troubleshooting

### Tests Fail Locally
```bash
# Clear pytest cache
pytest --cache-clear

# Recreate test database
rm -f test.db
pytest
```

### Coverage Not Updating
```bash
# Clear coverage data
rm -rf .coverage htmlcov/
pytest --cov=app
```

### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

## Next Steps

To reach 90%+ coverage, add:
- [ ] WebSocket tests
- [ ] Email verification tests
- [ ] Password reset flow tests
- [ ] Multi-tenancy tests
- [ ] Audit logging tests
- [ ] Error handler tests
- [ ] Middleware tests
