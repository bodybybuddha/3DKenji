"""Smoke tests for public frontend pages."""

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.smoke
def test_landing_page_loads_and_shows_primary_cta(page: Page, e2e_base_url: str):
    page.goto(f"{e2e_base_url}/")
    if "/setup" in page.url:
        assert page.locator("#setup-form").count() == 1
        assert page.locator("input[name='username']").count() == 1
        assert page.locator("input[name='email']").count() == 1
        assert page.locator("select[name='theme']").count() == 1
        return
    assert page.locator("h1:has-text('Welcome to 3DKenji')").count() > 0
    assert page.locator("text=3D Model Management and Printing Platform").count() == 1
    assert page.locator("text=Project Management").count() == 1
    assert page.locator("text=Model Upload").count() == 1
    assert page.locator("text=API Access").count() == 1
    assert page.locator("a[href='/login']").count() > 0 or page.locator("a[href='/projects']").count() > 0


@pytest.mark.e2e
@pytest.mark.smoke
def test_login_page_loads(page: Page, e2e_base_url: str):
    page.goto(f"{e2e_base_url}/login")
    if "/setup" in page.url:
        assert page.locator("#setup-form").count() == 1
        return
    assert page.locator("h1:has-text('Login')").count() == 1
    assert page.locator("#login-form").count() == 1
    assert page.locator("input[name='username_or_email']").count() == 1
    assert page.locator("input[name='password']").count() == 1
    assert page.locator("input[name='remember']").count() == 1
    assert page.locator("a[href='/register']").count() > 0


@pytest.mark.e2e
@pytest.mark.smoke
def test_register_page_loads(page: Page, e2e_base_url: str):
    page.goto(f"{e2e_base_url}/register")

    # Fresh instances can route through setup guard.
    if "/setup" in page.url:
        assert page.locator("#setup-form").count() == 1
        return

    assert page.locator("h1:has-text('Create Account')").count() == 1
    assert page.locator("#register-form").count() == 1
    assert page.locator("input[name='username']").count() == 1
    assert page.locator("input[name='email']").count() == 1
    assert page.locator("input[name='password_confirm']").count() == 1
    assert page.locator("input[name='terms']").count() == 1
    assert page.locator("a[href='/login']").count() > 0


@pytest.mark.e2e
@pytest.mark.smoke
def test_setup_page_behavior(page: Page, e2e_base_url: str):
    page.goto(f"{e2e_base_url}/setup")

    # Either setup form (fresh system) or redirect to login (already configured).
    if "/setup" in page.url:
        assert page.locator("#setup-form").count() == 1
        assert page.locator("input[name='password_confirm']").count() == 1
        assert page.locator("select[name='theme']").count() == 1
        assert page.locator("button[type='submit']").count() == 1
    else:
        assert "/login" in page.url
        assert page.locator("#login-form").count() == 1
