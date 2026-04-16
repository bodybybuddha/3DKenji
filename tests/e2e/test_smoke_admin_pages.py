"""Smoke tests for admin routes and access control."""

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.smoke
def test_non_admin_is_redirected_from_admin_routes(authenticated_page: Page, e2e_base_url: str):
    for route in ["/admin", "/admin/users", "/admin/plugins", "/admin/settings", "/admin/logs", "/admin/health"]:
        authenticated_page.goto(f"{e2e_base_url}{route}")
        assert "/projects" in authenticated_page.url
        assert authenticated_page.locator("h1:has-text('Projects')").count() == 1


@pytest.mark.e2e
@pytest.mark.smoke
def test_admin_dashboard_loads(admin_authenticated_page: Page, e2e_base_url: str):
    admin_authenticated_page.goto(f"{e2e_base_url}/admin")
    assert admin_authenticated_page.locator("h1:has-text('Admin Dashboard')").count() == 1
    assert admin_authenticated_page.locator("#user-count").count() == 1
    assert admin_authenticated_page.locator("#project-count").count() == 1
    assert admin_authenticated_page.locator("#model-count").count() == 1
    assert admin_authenticated_page.locator("#storage-used").count() == 1
    assert admin_authenticated_page.locator("a[href='/admin/users']").count() > 0
    assert admin_authenticated_page.locator("a[href='/admin/plugins']").count() > 0
    assert admin_authenticated_page.locator("a[href='/admin/logs']").count() > 0


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.parametrize(
    "route,heading_selector,primary_selector,secondary_selector",
    [
        ("/admin/users", "h2:has-text('Users')", "button:has-text('Add User')", "text=Manage system users and permissions"),
        ("/admin/plugins", "h2:has-text('Plugins')", "button:has-text('Upload Plugin')", "text=Manage plugins and extensions"),
        ("/admin/settings", "h2:has-text('Settings')", "form[hx-post='/api/v1/admin/settings/api']", "form[hx-post='/api/v1/admin/settings/storage']"),
        ("/admin/logs", "h2:has-text('Logs')", "#log-level-filter", "button:has-text('Clear Logs')"),
        ("/admin/health", "h2:has-text('System Health')", "#health-details", "#performance-metrics"),
    ],
)
def test_admin_subpages_load(
    admin_authenticated_page: Page,
    e2e_base_url: str,
    route: str,
    heading_selector: str,
    primary_selector: str,
    secondary_selector: str,
):
    admin_authenticated_page.goto(f"{e2e_base_url}{route}")
    assert admin_authenticated_page.locator(heading_selector).count() == 1
    assert admin_authenticated_page.locator(primary_selector).count() >= 1
    assert admin_authenticated_page.locator(secondary_selector).count() >= 1
    assert admin_authenticated_page.locator("a[href='/admin']").count() > 0
    assert admin_authenticated_page.locator("a[href='/admin/users']").count() > 0
    assert admin_authenticated_page.locator("a[href='/admin/plugins']").count() > 0
