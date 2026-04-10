---
layout: default
title: QA Quick Reference
---

# Quick Reference - QA Testing

## Running Tests

### Basic Commands
```bash
# Fast tests (contract tests only) - ~30 seconds
make test-fast

# Standard tests (contract + integration) - ~2 minutes  
make test

# Validation tests (input validation) - ~5 minutes
make test-validation

# E2E tests (browser tests) - ~10 minutes
# Requires server to be running first!
make test-e2e

# Full test suite - ~15 minutes
make test-full

# With coverage report
make test-coverage

# Security-focused tests only
make test-security
```

### Using the Script Directly
```bash
# All test levels
./scripts/run-qa-tests.sh fast
./scripts/run-qa-tests.sh standard
./scripts/run-qa-tests.sh validation
./scripts/run-qa-tests.sh e2e
./scripts/run-qa-tests.sh full
./scripts/run-qa-tests.sh coverage
./scripts/run-qa-tests.sh security
```

## Test Organization

```
tests/
├── contract/           # API contract tests
│   ├── test_auth_endpoints.py
│   ├── test_projects_*.py
│   └── test_keys_*.py
│
├── integration/        # Multi-component tests
│   ├── test_auth_flow.py
│   └── test_api_key_scopes.py
│
├── validation/         # Input validation tests
│   ├── test_auth_validation.py
│   ├── test_project_validation.py
│   └── test_api_key_validation.py
│
├── e2e/               # End-to-end browser tests
│   ├── pages/         # Page object models
│   ├── test_auth_flow.py
│   └── test_project_crud.py
│
├── fixtures/          # Test data factories
│   ├── factories.py
│   └── example_usage.py
│
└── manual/            # Manual QA checklists
    └── qa-checklist.md
```

## Writing New Tests

### Contract Test Example
```python
def test_create_project(client):
    """Test project creation."""
    response = client.post("/api/v1/projects", json={
        "name": "Test Project",
        "description": "Test"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Project"
```

### Validation Test Example
```python
@pytest.mark.parametrize("name,expected_status", [
    ("", 400),  # Empty
    ("a", 400),  # Too short
    ("a" * 300, 400),  # Too long
])
def test_invalid_names(client, name, expected_status):
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == expected_status
```

### E2E Test Example
```python
def test_create_project(logged_in_page):
    """Test project creation flow."""
    project_page = ProjectPage(logged_in_page)
    project_page.navigate_to_projects()
    project_page.create_project("Test Project", "Description")
    assert project_page.project_exists("Test Project")
```

## Using Test Factories

```python
from tests.fixtures.factories import UserFactory, ProjectFactory

# Create test user
user = UserFactory.build()  # With defaults
user = UserFactory.build(username="testuser")  # With custom values

# Create multiple users
users = UserFactory.build_batch(10)

# Get invalid variations
for variant, data in UserFactory.build_invalid("username"):
    # Test each invalid username variant
    pass

# Create test project
project = ProjectFactory.build()
project = ProjectFactory.build_with_unicode()
project = ProjectFactory.build_with_special_chars()
```

## Test Markers

```python
# Mark as smoke test (critical path)
@pytest.mark.smoke
def test_login():
    pass

# Mark as security test
@pytest.mark.security
def test_sql_injection():
    pass

# Mark as slow test
@pytest.mark.slow
def test_large_upload():
    pass

# Mark as E2E test
@pytest.mark.e2e
def test_full_workflow():
    pass
```

## Running Specific Tests

```bash
# Run by marker
pytest -m smoke
pytest -m security
pytest -m "not slow"

# Run by keyword
pytest -k "test_login"
pytest -k "sql_injection or xss"

# Run specific file
pytest tests/validation/test_auth_validation.py

# Run specific test
pytest tests/validation/test_auth_validation.py::test_empty_username
```

## Playwright E2E Tips

### Running in Headed Mode (See Browser)
```bash
pytest tests/e2e/ --headed
```

### Run Specific Browser
```bash
pytest tests/e2e/ --browser firefox
pytest tests/e2e/ --browser webkit
```

### Debug Mode (Slow Motion)
```bash
pytest tests/e2e/ --headed --slowmo 1000
```

### Generate Trace for Debugging
```bash
pytest tests/e2e/ --tracing on
playwright show-trace test-results/trace.zip
```

## Coverage Analysis

```bash
# Generate coverage report
make test-coverage

# View in browser
open htmlcov/index.html

# View in terminal
pytest --cov=src/backend --cov-report=term-missing
```

## Manual QA

1. Open [tests/manual/qa-checklist.md](tests/manual/qa-checklist.md)
2. Work through each section systematically
3. Check off items as you test
4. Note any issues found
5. Sign off when complete

## Test Data Reference

### XSS Payloads (from conftest.py)
- `<script>alert('XSS')</script>`
- `<img src=x onerror=alert('XSS')>`
- `<svg onload=alert('XSS')>`
- `javascript:alert('XSS')`

### SQL Injection Payloads
- `' OR '1'='1`
- `'; DROP TABLE users;--`
- `admin'--`
- `1' OR '1' = '1`

### Path Traversal
- `../../../etc/passwd`
- `..\\..\\..\\windows\\system32\\config\\sam`

### Unicode Test Strings
- `日本語`
- `Ñoño`
- `Москва`
- `😀🚀🎉`

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run QA Tests
  run: |
    make test-fast
    make test-validation
    
- name: Run E2E Tests
  run: |
    make dev &  # Start server
    sleep 5
    make test-e2e
```

## Troubleshooting

### Tests Can't Connect to Database
```bash
# Check environment variables
echo $DATABASE_URL

# Reset test database
rm -f tests/test.db
```

### E2E Tests Fail to Start
```bash
# Make sure server is running
curl http://localhost:8000/api/v1/health

# Check port isn't in use
lsof -i :8000
```

### Playwright Not Installed
```bash
pip install playwright pytest-playwright
playwright install chromium
```

### Permission Denied on Scripts
```bash
chmod +x scripts/run-qa-tests.sh
```

## Best Practices

1. **Write tests BEFORE fixing bugs** - Prevent regressions
2. **Use descriptive test names** - Explain what's being tested
3. **One assertion per test** - Makes failures clear
4. **Keep tests independent** - No test dependencies
5. **Use factories** - Consistent, maintainable test data
6. **Mock external services** - Fast, reliable tests
7. **Test edge cases** - Empty, null, max, min, special chars
8. **Test security** - SQL injection, XSS, auth bypass
9. **Test error paths** - Not just happy paths
10. **Keep tests fast** - Aim for <5 minutes total

## Resources

- 📖 [Full QA Strategy](docs/qa-strategy.md)
- 📋 [Manual Checklist](tests/manual/qa-checklist.md)
- 🏭 [Test Factories](tests/fixtures/factories.py)
- 🌐 [Playwright Docs](https://playwright.dev/python/)
- ✅ [Pytest Docs](https://docs.pytest.org/)
