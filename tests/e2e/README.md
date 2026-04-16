# End-to-End (E2E) Tests

## Overview

E2E tests simulate real user interactions in a browser to validate complete workflows from frontend to backend.

## Setup

### Install Playwright

```bash
pip install playwright pytest-playwright
playwright install chromium  # or firefox, webkit
```

### Configuration

Playwright is configured in `pytest.ini` with appropriate timeouts and base URL settings.

## Running E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/

# Run in headed mode (see browser)
pytest tests/e2e/ --headed

# Run specific browser
pytest tests/e2e/ --browser firefox

# Debug mode (slow motion)
pytest tests/e2e/ --slowmo 500

# Generate trace for debugging
pytest tests/e2e/ --tracing retain-on-failure
```

## Writing E2E Tests

### Use Page Object Model

```python
from tests.e2e.pages.auth_page import AuthPage

def test_login(page):
    auth_page = AuthPage(page)
    auth_page.navigate()
    auth_page.login("user@example.com", "password")
    assert auth_page.is_logged_in()
```

### Wait for HTMX Responses

```python
# Wait for HTMX to complete
page.wait_for_load_state("networkidle")

# Or wait for specific element
page.wait_for_selector("#success-message")
```

## Best Practices

1. **Use data-testid attributes** in HTML for stable selectors
2. **Avoid using CSS classes** that might change with styling
3. **Clean up after tests** - logout, delete created resources
4. **Use fixtures** for common setup (logged-in user, etc.)
5. **Take screenshots on failure** - configured automatically

## Debugging Failed Tests

```bash
# Run with browser visible
pytest tests/e2e/test_auth_flow.py --headed --slowmo 1000

# Show trace viewer for last run
playwright show-trace test-results/trace.zip
```
