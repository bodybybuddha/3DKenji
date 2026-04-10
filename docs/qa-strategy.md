---
layout: default
title: QA Strategy
---

# QA Strategy & Testing Guide

## Overview

This document outlines a comprehensive QA strategy for the 3D Kenji application to catch frontend/backend integration issues proactively rather than reactively.

## Current State

### What We Have
- ✅ Contract tests for API endpoints (`tests/contract/`)
- ✅ Integration tests (`tests/integration/`)
- ✅ FastAPI backend with validation
- ✅ HTMX-powered frontend forms

### What's Missing
- ❌ End-to-end (E2E) tests simulating real user interactions
- ❌ Comprehensive input validation testing (boundary cases, edge cases)
- ❌ Form validation consistency checks
- ❌ HTMX response validation
- ❌ Cross-browser testing
- ❌ Automated accessibility checks

## Testing Pyramid

```
    /\
   /E2E\        <- Playwright tests (user flows)
  /------\
 /Integration\  <- API + DB + Services
/--------------\
/   Contract    \ <- API endpoint contracts
/----------------\
```

## QA Layers

### Layer 1: API Contract Tests (Existing)
**Location:** `tests/contract/`  
**Purpose:** Validate API responses match expected contracts  
**Coverage:** Authentication, Projects, Models, Keys, Users

### Layer 2: Integration Tests (Existing)
**Location:** `tests/integration/`  
**Purpose:** Test multi-component workflows  
**Coverage:** Auth flows, API key scopes, model uploads

### Layer 3: Input Validation Tests (NEW)
**Location:** `tests/validation/`  
**Purpose:** Exhaustive testing of all input fields  
**Coverage:**
- Boundary testing (min/max lengths)
- Type validation (strings, numbers, emails)
- Special characters and SQL injection attempts
- XSS prevention
- Required vs optional fields
- Format validation (emails, URLs, dates)

### Layer 4: E2E Browser Tests (NEW)
**Location:** `tests/e2e/`  
**Purpose:** Simulate real user interactions in browser  
**Coverage:**
- Complete user workflows (signup → login → create project)
- Form submissions with validation errors
- HTMX dynamic form updates
- Modal interactions
- File uploads
- Navigation flows

### Layer 5: Visual/Manual QA (NEW)
**Location:** `tests/manual/`  
**Purpose:** Checklist-driven manual testing  
**Coverage:**
- UI/UX consistency
- Responsive design
- Browser compatibility
- Accessibility (WCAG)

## Testing Tools & Setup

### 1. Playwright for E2E Testing
```bash
pip install playwright pytest-playwright
playwright install
```

**Why Playwright?**
- Multi-browser support (Chromium, Firefox, WebKit)
- Great for HTMX testing (waits for network responses)
- Screenshot/video recording on failures
- Debugging tools

### 2. Hypothesis for Property-Based Testing
```bash
pip install hypothesis
```

**Why Hypothesis?**
- Generates edge cases automatically
- Finds inputs you wouldn't think of
- Great for validation testing

### 3. Faker for Test Data
```bash
pip install faker
```

**Why Faker?**
- Realistic test data
- Consistent test data generation
- Supports various locales

## Implementation Plan

### Phase 1: Input Validation Test Suite (Week 1)
1. Create `tests/validation/` directory structure
2. Build test data factory with valid/invalid cases
3. Create parameterized tests for all endpoints
4. Document validation rules in one place

### Phase 2: E2E Framework Setup (Week 1-2)
1. Install and configure Playwright
2. Create page object models for main pages
3. Write smoke tests for critical paths
4. Set up CI/CD integration

### Phase 3: Comprehensive Coverage (Week 2-3)
1. Test all forms and user inputs
2. HTMX interaction tests
3. Error handling and edge cases
4. Performance and load testing basics

### Phase 4: Automation & CI/CD (Week 3-4)
1. Pre-commit hooks for fast tests
2. CI pipeline for all test suites
3. Test coverage reporting
4. Nightly E2E test runs

## Test Execution Strategy

### Local Development
```bash
# Run fast tests (unit + contract)
make test-fast

# Run all tests except E2E
make test

# Run E2E tests
make test-e2e

# Run validation tests only
make test-validation

# Run with coverage
make test-coverage
```

### CI/CD Pipeline
1. **On PR:** Contract + Integration tests (< 2 min)
2. **On Merge:** Full test suite except E2E (< 5 min)
3. **Nightly:** Full test suite including E2E (< 15 min)

## Input Validation Matrix

| Field Type | Validations Required |
|------------|---------------------|
| Username | Min/max length, alphanumeric+underscore, uniqueness, SQL injection |
| Email | Format, uniqueness, max length, internationalization |
| Password | Min length, complexity, max length, common passwords |
| Display Name | Min/max length, unicode support, XSS prevention |
| Project Name | Min/max length, special chars, uniqueness per user |
| File Upload | Type validation, size limits, virus scanning, path traversal |
| Dates | Format, past/future constraints, timezone handling |
| Numbers | Min/max values, type casting, overflow |
| API Keys | Format, expiration, permissions, rate limiting |

## Critical User Flows to Test

### Authentication Flows
- [ ] Register new user with valid data
- [ ] Register with invalid email
- [ ] Register with weak password
- [ ] Register with duplicate username
- [ ] Login with correct credentials
- [ ] Login with incorrect password
- [ ] Login with non-existent user
- [ ] Session management
- [ ] Logout
- [ ] Password reset flow

### Project Management
- [ ] Create project with required fields
- [ ] Create project with optional fields
- [ ] Create project with invalid data
- [ ] Create project with duplicate name
- [ ] Edit project details
- [ ] Delete project
- [ ] List projects
- [ ] Search/filter projects

### Model Upload
- [ ] Upload valid file
- [ ] Upload invalid file type
- [ ] Upload oversized file
- [ ] Upload with metadata
- [ ] Cancel upload
- [ ] Delete uploaded file

### API Key Management
- [ ] Create API key with name
- [ ] Create API key with expiration
- [ ] Create API key with scopes
- [ ] List API keys
- [ ] Revoke API key
- [ ] Use valid API key
- [ ] Use expired API key
- [ ] Use revoked API key

### Admin Functions
- [ ] View user list
- [ ] Create new user
- [ ] Edit user details
- [ ] Delete user
- [ ] View system logs
- [ ] Change system settings

## Error Handling Testing

### Frontend Error Display
- [ ] Inline field validation errors
- [ ] Form-level errors
- [ ] Toast notifications
- [ ] Modal error states
- [ ] Network error handling
- [ ] Timeout handling

### Backend Error Responses
- [ ] 400 Bad Request with validation details
- [ ] 401 Unauthorized
- [ ] 403 Forbidden
- [ ] 404 Not Found
- [ ] 409 Conflict
- [ ] 500 Internal Server Error
- [ ] Consistent error format

## HTMX-Specific Testing

### Dynamic Form Updates
- [ ] Form validation on blur
- [ ] Real-time feedback
- [ ] Progressive enhancement
- [ ] Partial page updates
- [ ] Loading states
- [ ] Error recovery

### Modal Interactions
- [ ] Open modal
- [ ] Close modal (button, escape, backdrop)
- [ ] Form submission in modal
- [ ] Validation errors in modal
- [ ] Success feedback
- [ ] Form reset on close

## Security Testing Checklist

- [ ] SQL injection attempts on all text inputs
- [ ] XSS attempts in all user-generated content
- [ ] CSRF protection on state-changing operations
- [ ] Authorization checks on all endpoints
- [ ] Rate limiting on sensitive operations
- [ ] File upload path traversal attempts
- [ ] Session hijacking prevention
- [ ] Password strength enforcement

## Performance Testing

- [ ] API response times < 200ms (p95)
- [ ] Page load times < 2s
- [ ] Form submission feedback < 500ms
- [ ] File upload progress indication
- [ ] Concurrent user handling
- [ ] Database query optimization

## Accessibility Testing

- [ ] Keyboard navigation
- [ ] Screen reader compatibility
- [ ] Color contrast (WCAG AA)
- [ ] Focus indicators
- [ ] ARIA labels
- [ ] Form error announcements
- [ ] Alt text for images

## Test Data Management

### Database Isolation Strategy

**File Location:** `tests/test.db` (SQLite)  
**Cleanup:** Automatically deleted and recreated each test session

**Isolation Approach:**
1. **Session-level database** - Created once per test run
2. **Transaction-based isolation** - Each test runs in a transaction that's rolled back
3. **No cross-test pollution** - Tests cannot affect each other's data
4. **Real database behavior** - Not mocked, catches actual SQL issues

**Using Database Fixtures:**
```python
def test_user_creation(db_session):
    """Test with automatic transaction rollback."""
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    
    # Verify user exists
    assert db_session.query(User).filter_by(username="testuser").first()
    
    # Transaction automatically rolled back after test
    # No cleanup needed - next test gets fresh database
```

**For E2E/Integration Tests:**
- Use HTTP client fixtures (tests start API server subprocess)
- Server uses the same test database file
- Each test run starts with fresh database
- No need to manually clean up data

### Test Data Factories

Located in `tests/fixtures/factories.py`:
```python
# - UserFactory: Create users with various states
# - ProjectFactory: Create projects with relationships
# - ModelFactory: Create models with files
# - APIKeyFactory: Create keys with various permissions
# - BoundaryValueFactory: Generate edge case values
# - RandomDataFactory: Realistic test data with Faker
```

**Benefits:**
- ✅ Consistent test data across tests
- ✅ Easy to generate valid and invalid data
- ✅ Supports boundary testing (min/max values, edge cases)
- ✅ Generates realistic data (names, emails, dates)

### Database State Management

**Clean State Guarantee:**
- Database deleted before each test session
- Fresh schema created from models
- Each test runs in isolated transaction
- Automatic rollback ensures no artifacts

**When to Use Each Fixture:**
- `db_session` - Unit tests, validation tests (fast, isolated)
- `auth_client` - API/integration tests (uses HTTP, slower)
- `client` - Basic HTTP tests without authentication

## Monitoring & Reporting

### Test Reports
- Coverage reports (aim for 80%+)
- Test execution time trends
- Flaky test detection
- Failed test history

### Quality Metrics
- Defect escape rate
- Mean time to detection
- Test maintenance burden
- Test execution time

## Best Practices

### Writing Tests
1. **Arrange-Act-Assert** pattern
2. **One assertion per test** when possible
3. **Descriptive test names** that explain what's being tested
4. **Independent tests** - no test dependencies
5. **Fast tests** - optimize for speed
6. **Maintainable tests** - DRY with fixtures/helpers

### Test Organization
```
tests/
├── conftest.py           # Shared fixtures
├── fixtures/
│   ├── factories.py      # Data factories
│   └── data/             # Static test data
├── contract/             # API contract tests
├── integration/          # Multi-component tests
├── validation/           # Input validation tests
│   ├── test_auth_validation.py
│   ├── test_project_validation.py
│   └── test_model_validation.py
├── e2e/                  # Browser E2E tests
│   ├── pages/           # Page object models
│   ├── test_auth_flow.py
│   ├── test_project_crud.py
│   └── test_model_upload.py
└── manual/              # Manual test checklists
    ├── browser-compatibility.md
    ├── accessibility.md
    └── ui-consistency.md
```

## Next Steps

1. **Immediate Actions:**
   - Set up Playwright
   - Create validation test suite
   - Document all validation rules
   - Create test data factory

2. **Short Term (This Sprint):**
   - Write E2E tests for critical paths
   - Add parameterized validation tests
   - Set up test coverage reporting

3. **Long Term (Next Month):**
   - Complete E2E coverage
   - Add performance tests
   - Implement visual regression testing
   - Set up nightly test runs

## Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [HTMX Testing Patterns](https://htmx.org/docs/#testing)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
