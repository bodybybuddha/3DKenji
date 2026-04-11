"""Pytest configuration for E2E tests."""

import os
import uuid
import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="function")
def context(browser: Browser):
    """Create a new browser context for each test."""
    context = browser.new_context()
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext):
    """Create a new page for each test."""
    page = context.new_page()
    
    # Set base URL from environment or default
    base_url = os.getenv("E2E_BASE_URL", "http://localhost:8000")
    
    # Configure timeouts
    page.set_default_timeout(10000)  # 10 seconds
    page.set_default_navigation_timeout(30000)  # 30 seconds
    
    yield page
    
    # Screenshot on failure
    if hasattr(page, "_test_failed"):
        screenshot_dir = "tests/e2e/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        page.screenshot(path=f"{screenshot_dir}/failure.png")
    
    page.close()


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    """Return base URL for E2E tests."""
    return os.getenv("E2E_BASE_URL") or os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="function")
def e2e_credentials() -> dict[str, str]:
    """Generate unique credentials for an isolated test user."""
    suffix = uuid.uuid4().hex[:8]
    username = f"e2e_user_{suffix}"
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": "SecurePass123!",
        "display_name": f"E2E {suffix}",
    }


@pytest.fixture(scope="function")
def authenticated_page(page: Page, e2e_base_url: str, e2e_credentials: dict[str, str]) -> Page:
    """Create and authenticate a user using backend auth form endpoints."""
    page.goto(f"{e2e_base_url}/register")

    # In a fresh instance setup guard may redirect to /setup first.
    if "/setup" in page.url:
        admin_suffix = uuid.uuid4().hex[:6]
        setup_response = page.request.post(
            f"{e2e_base_url}/setup",
            form={
                "username": f"admin_{admin_suffix}",
                "email": f"admin_{admin_suffix}@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "theme": "dark",
            },
        )
        if setup_response.status >= 400:
            raise RuntimeError(f"Setup bootstrap failed in fixture: HTTP {setup_response.status}")

    register_response = page.request.post(
        f"{e2e_base_url}/api/v1/auth/register",
        data={
            "username": e2e_credentials["username"],
            "email": e2e_credentials["email"],
            "display_name": e2e_credentials["display_name"],
            "password": e2e_credentials["password"],
        },
    )

    if register_response.status >= 400:
        raise RuntimeError(f"Registration failed in fixture: HTTP {register_response.status}")

    token = register_response.json().get("access_token")
    if not token:
        raise RuntimeError("Registration response did not include access_token")

    page.context.add_cookies([
        {
            "name": "access_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/",
            "httpOnly": True,
        }
    ])

    page.goto(f"{e2e_base_url}/projects")
    if "/login" in page.url:
        raise RuntimeError("Authenticated fixture did not obtain session cookie")

    return page


@pytest.fixture(scope="function")
def admin_authenticated_page(page: Page, e2e_base_url: str) -> Page:
    """Login using configured admin credentials for admin-route coverage.

    Defaults to the deterministic sqlite test admin used by the pytest harness.
    """
    admin_username = os.getenv("E2E_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("E2E_ADMIN_PASSWORD", "admin1234")

    login_response = page.request.post(
        f"{e2e_base_url}/api/v1/auth/login",
        data={"username": admin_username, "password": admin_password},
    )
    if login_response.status >= 400:
        raise RuntimeError(f"Admin API login failed in fixture: HTTP {login_response.status}")

    token = login_response.json().get("access_token")
    if not token:
        raise RuntimeError("Admin login response did not include access_token")

    page.context.add_cookies([
        {
            "name": "access_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/",
            "httpOnly": True,
        }
    ])

    page.goto(f"{e2e_base_url}/projects")
    if "/login" in page.url:
        raise RuntimeError("Admin fixture did not obtain session cookie")
    return page


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to track test failures for screenshot capture."""
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        # Mark page as failed for screenshot
        if "page" in item.funcargs:
            item.funcargs["page"]._test_failed = True
