# Input Validation Tests

## Overview

This directory contains comprehensive input validation tests for all user inputs in the application. These tests ensure that:

1. **Required fields** are properly validated
2. **Data types** are enforced (strings, numbers, emails, etc.)
3. **Length constraints** are respected (min/max)
4. **Format validations** work correctly (email, URL, date, etc.)
5. **Special characters** are handled properly
6. **Security** measures prevent SQL injection, XSS, etc.

## Test Structure

```
tests/validation/
├── README.md (this file)
├── conftest.py (shared fixtures and test data)
├── test_auth_validation.py (registration, login validation)
├── test_project_validation.py (project CRUD validation)
├── test_model_validation.py (model upload validation)
├── test_api_key_validation.py (API key creation validation)
└── test_user_validation.py (user profile validation)
```

## Running Validation Tests

```bash
# Run all validation tests
pytest tests/validation/

# Run specific validation test file
pytest tests/validation/test_auth_validation.py

# Run with verbose output
pytest tests/validation/ -v

# Run parametrized tests individually
pytest tests/validation/ -v --tb=short
```

## Writing New Validation Tests

### Use Parameterized Tests

```python
@pytest.mark.parametrize("username,expected_error", [
    ("", "required"),
    ("a", "too short"),
    ("a" * 300, "too long"),
    ("user@name", "invalid characters"),
])
def test_username_validation(client, username, expected_error):
    response = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 400
    assert expected_error in response.json()["detail"].lower()
```

### Test Both Frontend and Backend

Each validation should be tested at both levels:
- **Frontend:** Prevents invalid input before submission
- **Backend:** Ensures security even if frontend is bypassed

## Validation Categories

### 1. Required Field Validation
- Empty strings
- Null values
- Whitespace-only strings
- Missing keys in JSON

### 2. Length Validation
- Minimum length
- Maximum length
- Exact length (where applicable)
- UTF-8 byte length vs character length

### 3. Format Validation
- Email addresses (RFC 5322)
- URLs (protocol, domain, path)
- Dates (ISO 8601, timezone handling)
- Phone numbers (international formats)
- Usernames (alphanumeric + underscore)

### 4. Type Validation
- String vs Number
- Integer vs Float
- Boolean coercion
- Array vs Object
- File types (MIME type, extension)

### 5. Security Validation
- SQL injection attempts
- XSS attempts (`<script>`, event handlers)
- Path traversal (`../../../etc/passwd`)
- Command injection (`;`, `|`, `&&`)
- CSRF protection
- Rate limiting

### 6. Business Logic Validation
- Uniqueness constraints
- Referential integrity
- State transitions
- Permission checks
- Resource limits

## Common Test Patterns

### Invalid Input Matrix

For each field, test:
- ✅ Valid value
- ❌ Empty/null
- ❌ Wrong type
- ❌ Too short
- ❌ Too long
- ❌ Invalid format
- ❌ SQL injection
- ❌ XSS attempt
- ❌ Special characters
- ❌ Unicode edge cases

### Example Test Data

See `conftest.py` for comprehensive test data including:
- Valid usernames, emails, passwords
- Invalid usernames (too short, special chars, SQL injection)
- Invalid emails (no @, no domain, etc.)
- Invalid passwords (too short, no complexity)
- XSS payloads
- SQL injection strings
- Unicode test cases
- Boundary values
