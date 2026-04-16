"""Smoke tests for authenticated user pages and dialogs."""

import uuid

import pytest
from playwright.sync_api import Page


def _create_minimal_project(page: Page, e2e_base_url: str, name: str) -> None:
    page.goto(f"{e2e_base_url}/projects")
    page.wait_for_selector("#projects-table", timeout=10000)
    page.click("button:has-text('New Project')")
    page.wait_for_selector("#project-form-modal", state="visible")
    page.fill("input[name='name']", name)
    page.click("#project-form button[type='submit']")
    page.wait_for_selector("#project-form-alert .alert-success", timeout=10000)
    page.wait_for_timeout(1800)
    if page.locator("#project-form-modal").count() and page.locator("#project-form-modal").first.is_visible():
        page.goto(f"{e2e_base_url}/projects")
    page.wait_for_selector(f"#projects-table .tabulator-row:has-text('{name}')", timeout=10000)


@pytest.mark.e2e
@pytest.mark.smoke
def test_projects_page_loads_for_authenticated_user(authenticated_page: Page, e2e_base_url: str):
    authenticated_page.goto(f"{e2e_base_url}/projects")
    assert authenticated_page.locator("h1:has-text('Projects')").count() == 1
    assert authenticated_page.locator("text=Manage your 3D printing projects").count() == 1
    assert authenticated_page.locator("button:has-text('New Project')").count() == 1
    assert authenticated_page.locator("#projects-table").count() == 1
    assert authenticated_page.locator("a[href='/keys']").count() > 0
    assert authenticated_page.locator("#user-menu-btn").count() == 1


@pytest.mark.e2e
@pytest.mark.smoke
def test_project_create_modal_opens_and_closes(authenticated_page: Page, e2e_base_url: str):
    authenticated_page.goto(f"{e2e_base_url}/projects")
    authenticated_page.click("button:has-text('New Project')")
    authenticated_page.wait_for_selector("#project-form-modal", state="visible")
    assert authenticated_page.locator("#modal-title:has-text('Create Project')").count() == 1
    assert authenticated_page.locator("#project_name").count() == 1
    assert authenticated_page.locator("#project_description").count() == 1
    assert authenticated_page.locator("#project_visibility").count() == 1
    assert authenticated_page.locator("#submit-btn:has-text('Create Project')").count() == 1
    authenticated_page.click("#project-form-modal button:has-text('Cancel')")
    authenticated_page.wait_for_selector("#project-form-modal", state="hidden")


@pytest.mark.e2e
@pytest.mark.smoke
def test_api_keys_page_loads_for_authenticated_user(authenticated_page: Page, e2e_base_url: str):
    authenticated_page.goto(f"{e2e_base_url}/keys")
    assert authenticated_page.locator("h1:has-text('API Keys')").count() == 1
    assert authenticated_page.locator("text=Create and manage API keys for programmatic access").count() == 1
    assert authenticated_page.locator("button:has-text('Generate Key')").count() == 1
    assert authenticated_page.locator("h3:has-text('Using API Keys')").count() == 1
    assert authenticated_page.locator("text=Authorization: Bearer YOUR_API_KEY").count() >= 1


@pytest.mark.e2e
@pytest.mark.smoke
def test_api_key_modal_opens_and_closes(authenticated_page: Page, e2e_base_url: str):
    authenticated_page.goto(f"{e2e_base_url}/keys")
    authenticated_page.click("button:has-text('Generate Key')")
    authenticated_page.wait_for_selector("#api-key-modal", state="visible")
    assert authenticated_page.locator("#api-key-modal h2:has-text('Generate API Key')").count() == 1
    assert authenticated_page.locator("#key_name").count() == 1
    assert authenticated_page.locator("input[name='scopes']").count() >= 6
    assert authenticated_page.locator("#key_expiry").count() == 1
    authenticated_page.click("#api-key-modal button:has-text('Cancel')")
    authenticated_page.wait_for_selector("#api-key-modal", state="hidden")


@pytest.mark.e2e
@pytest.mark.smoke
def test_profile_settings_page_loads(authenticated_page: Page, e2e_base_url: str):
    authenticated_page.goto(f"{e2e_base_url}/settings/profile")
    assert authenticated_page.locator("h1:has-text('Profile Settings')").count() == 1
    assert authenticated_page.locator("#profile-form").count() == 1
    assert authenticated_page.locator("#password-form").count() == 1
    assert authenticated_page.locator("text=Basic Information").count() == 1
    assert authenticated_page.locator("text=Danger Zone").count() == 1
    assert authenticated_page.locator("button:has-text('Delete Account')").count() == 1
    assert authenticated_page.locator("button:has-text('Dark Mode')").count() == 1
    assert authenticated_page.locator("button:has-text('Light Mode')").count() == 1


@pytest.mark.e2e
@pytest.mark.smoke
def test_project_file_upload_controls_exist(authenticated_page: Page, e2e_base_url: str):
    project_name = "E2E Upload Modal Project"
    _create_minimal_project(authenticated_page, e2e_base_url, project_name)

    authenticated_page.click(f"#projects-table .tabulator-row:has-text('{project_name}') a:has-text('View')")
    authenticated_page.wait_for_url("**/project/*", timeout=10000)

    assert authenticated_page.locator("#project-files-upload:has-text('Upload File')").count() == 1
    assert authenticated_page.locator("#project-files-upload-input[type='file']").count() == 1
    assert authenticated_page.locator("#project-files-uploader").count() == 1


@pytest.mark.e2e
@pytest.mark.smoke
def test_api_key_create_write_path(authenticated_page: Page, e2e_base_url: str):
    key_name = f"smoke-key-{uuid.uuid4().hex[:8]}"

    authenticated_page.goto(f"{e2e_base_url}/keys")
    authenticated_page.click("button:has-text('Generate Key')")
    authenticated_page.wait_for_selector("#api-key-modal", state="visible")

    authenticated_page.fill("#key_name", key_name)
    authenticated_page.check("input[name='scopes'][value='read:projects']")
    authenticated_page.click("#api-key-modal button:has-text('Generate Key')")

    authenticated_page.wait_for_selector("#api-key-display", state="visible", timeout=10000)
    assert authenticated_page.locator("#api-key-display").locator("text=API Key Generated").count() == 1
    assert authenticated_page.locator("#api-key-display button:has-text('Copy to Clipboard')").count() == 1
    assert authenticated_page.locator("#api-key-display button:has-text('Done')").count() == 1


@pytest.mark.e2e
@pytest.mark.smoke
def test_profile_update_write_path(authenticated_page: Page, e2e_base_url: str):
    suffix = uuid.uuid4().hex[:8]
    updated_email = f"smoke_profile_{suffix}@example.com"
    updated_display_name = f"Smoke Profile {suffix}"

    authenticated_page.goto(f"{e2e_base_url}/settings/profile")
    authenticated_page.wait_for_selector("#profile-form", state="visible")

    authenticated_page.fill("#email", updated_email)
    authenticated_page.fill("#display_name", updated_display_name)
    authenticated_page.click("#profile-form button[type='submit']")

    authenticated_page.wait_for_selector("#profile-form", state="visible", timeout=10000)
    assert authenticated_page.locator("#email").input_value() == updated_email
    assert authenticated_page.locator("#display_name").input_value() == updated_display_name


@pytest.mark.e2e
@pytest.mark.smoke
def test_password_change_write_path(
    authenticated_page: Page,
    e2e_base_url: str,
    e2e_credentials: dict[str, str],
):
    new_password = "NewSecurePass123!"

    authenticated_page.goto(f"{e2e_base_url}/settings/profile")
    authenticated_page.wait_for_selector("#password-form", state="visible")

    authenticated_page.fill("#current_password", e2e_credentials["password"])
    authenticated_page.fill("#new_password", new_password)
    authenticated_page.fill("#new_password_confirm", new_password)
    authenticated_page.click("#password-form button[type='submit']")
    authenticated_page.wait_for_selector("#password-form", state="visible", timeout=10000)
    # Success response injects this toast script marker; error responses inject alert-danger.
    assert "Password updated successfully" in authenticated_page.content()
    assert authenticated_page.locator(".alert-danger").count() == 0


@pytest.mark.e2e
@pytest.mark.smoke
def test_api_key_revoke_write_path(authenticated_page: Page, e2e_base_url: str):
    key_name = f"smoke-revoke-{uuid.uuid4().hex[:8]}"

    # Create key through the same UI modal flow users rely on.
    authenticated_page.goto(f"{e2e_base_url}/keys")
    authenticated_page.click("button:has-text('Generate Key')")
    authenticated_page.wait_for_selector("#api-key-modal", state="visible")
    authenticated_page.fill("#key_name", key_name)
    authenticated_page.check("input[name='scopes'][value='read:projects']")
    authenticated_page.click("#api-key-modal button:has-text('Generate Key')")
    authenticated_page.wait_for_selector("#api-key-display", state="visible", timeout=10000)

    authenticated_page.goto(f"{e2e_base_url}/keys")
    key_row = authenticated_page.locator("tr").filter(has_text=key_name).first
    key_row.wait_for(state="visible", timeout=10000)

    revoke_path = key_row.locator("button[title='Revoke']").get_attribute("hx-delete")
    assert revoke_path

    revoke_response = authenticated_page.request.delete(f"{e2e_base_url}{revoke_path}")
    assert revoke_response.status in (200, 204)

    # Reload keys page and verify the revoked key no longer appears.
    authenticated_page.goto(f"{e2e_base_url}/keys")
    authenticated_page.wait_for_selector("h1:has-text('API Keys')", timeout=10000)
    authenticated_page.wait_for_timeout(500)
    assert authenticated_page.locator("tr").filter(has_text=key_name).count() == 0
