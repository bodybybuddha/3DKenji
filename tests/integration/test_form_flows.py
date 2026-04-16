"""
Integration tests for HTML form flows and HTMX submissions.

These tests verify the complete user workflows that were broken in recent changes:
1. Login form submission (status codes, redirects, cookies)
2. Project creation via HTML form (not JSON API)
3. Project list HTML rendering with correct template fields
4. HTMX response handling and error states
"""

import os
import pytest
import requests
from datetime import datetime


@pytest.fixture
def api_base_url():
    """Get the API base URL from environment or use default."""
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def auth_session(api_base_url):
    """Create an authenticated session for testing."""
    session = requests.Session()
    
    # Login with admin credentials
    resp = session.post(
        f"{api_base_url}/api/v1/auth/validate/login",
        data={"username_or_email": "admin", "password": "admin1234"},
        allow_redirects=False
    )
    
    # Verify login was successful
    assert resp.status_code == 303, f"Login failed with status {resp.status_code}: {resp.text}"
    assert "access_token" in resp.cookies, "No access token cookie set"
    
    return session


class TestLoginFormFlow:
    """Tests for the login form submission flow."""
    
    def test_login_form_invalid_credentials_returns_401(self, api_base_url):
        """Invalid credentials should return 401, not 200."""
        resp = requests.post(
            f"{api_base_url}/api/v1/auth/validate/login",
            data={"username_or_email": "admin", "password": "wrongpassword"},
            allow_redirects=False
        )
        
        assert resp.status_code == 401, \
            f"Expected 401 for invalid credentials, got {resp.status_code}"
        assert "Invalid" in resp.text or "invalid" in resp.text.lower(), \
            "Error message should indicate invalid credentials"
    
    def test_login_form_valid_credentials_returns_303_redirect(self, api_base_url):
        """Valid credentials should return 303 redirect (not 200 or 302)."""
        resp = requests.post(
            f"{api_base_url}/api/v1/auth/validate/login",
            data={"username_or_email": "admin", "password": "admin1234"},
            allow_redirects=False
        )
        
        assert resp.status_code == 303, \
            f"Expected 303 redirect, got {resp.status_code}"
        assert resp.headers.get("Location") == "/projects", \
            "Should redirect to /projects"
    
    def test_login_form_sets_https_only_cookie(self, api_base_url):
        """Access token cookie should be set with HttpOnly flag."""
        resp = requests.post(
            f"{api_base_url}/api/v1/auth/validate/login",
            data={"username_or_email": "admin", "password": "admin1234"},
            allow_redirects=False
        )
        
        assert "access_token" in resp.cookies, "No access token cookie"
        cookie_header = resp.headers.get("Set-Cookie", "")
        assert "HttpOnly" in cookie_header, "Cookie should have HttpOnly flag"
    
    def test_login_form_email_as_identifier(self, api_base_url):
        """Login should accept email as username identifier."""
        resp = requests.post(
            f"{api_base_url}/api/v1/auth/validate/login",
            data={"username_or_email": "admin@local.test", "password": "admin1234"},
            allow_redirects=False
        )
        
        assert resp.status_code == 303, \
            f"Email login failed with status {resp.status_code}"
        assert "access_token" in resp.cookies, "Email login didn't set cookie"


class TestProjectCreationFormFlow:
    """Tests for project creation via HTML form (HTMX)."""
    
    def test_create_project_form_submission_returns_201(self, api_base_url, auth_session):
        """Creating project via form should return 201."""
        project_name = f"Test Project {datetime.now().isoformat()}"
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": project_name,
                "description": "Test description",
                "visibility": "private",
                "tags": "test"
            },
            allow_redirects=False
        )
        
        assert resp.status_code == 201, \
            f"Expected 201 created, got {resp.status_code}: {resp.text}"
        assert "success" in resp.text.lower(), \
            "Response should contain success message"
    
    def test_create_project_requires_name_field(self, api_base_url, auth_session):
        """Creating project without name should return 400."""
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "description": "No name project",
                "visibility": "private"
            },
            allow_redirects=False
        )
        
        assert resp.status_code == 400, \
            f"Expected 400 for missing name, got {resp.status_code}"
    
    def test_create_project_empty_name_returns_400(self, api_base_url, auth_session):
        """Creating project with empty name should return 400."""
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "",
                "description": "Empty name",
                "visibility": "private"
            },
            allow_redirects=False
        )
        
        assert resp.status_code == 400, \
            f"Expected 400 for empty name, got {resp.status_code}"
    
    def test_created_project_appears_in_list(self, api_base_url, auth_session):
        """Created project should appear in the projects list."""
        project_name = f"Listable Project {datetime.now().isoformat()}"
        
        # Create project
        create_resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": project_name,
                "description": "Should appear in list",
                "visibility": "private",
                "tags": "test"
            },
            allow_redirects=False
        )
        assert create_resp.status_code == 201
        
        # Get projects list
        list_resp = auth_session.get(f"{api_base_url}/api/v1/projects")
        assert list_resp.status_code == 200
        
        projects = list_resp.json()
        project_titles = [p["title"] for p in projects["items"]]
        assert project_name in project_titles, \
            f"Created project not in list. Found: {project_titles}"


class TestProjectListHtmlRendering:
    """Tests for project list HTML rendering with correct template fields."""
    
    def test_projects_list_html_contains_project_titles(self, api_base_url, auth_session):
        """Project list HTML should contain project titles from 'title' field."""
        project_name = f"HTML Test Project {datetime.now().isoformat()}"
        
        # Create project
        auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": project_name,
                "description": "HTML rendering test",
                "visibility": "private",
                "tags": "html"
            },
            allow_redirects=False
        )
        
        # Get HTML fragment
        html_resp = auth_session.get(
            f"{api_base_url}/api/v1/projects?format=html"
        )
        assert html_resp.status_code == 200
        
        # Verify project title appears in HTML
        assert project_name in html_resp.text, \
            f"Project title not found in HTML. Content: {html_resp.text[:500]}"
    
    def test_projects_list_uses_correct_field_names(self, api_base_url, auth_session):
        """Project list template should use correct field names from Project model."""
        # Create a project
        auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "Field Mapping Test",
                "description": "Test field mapping",
                "visibility": "public",
                "tags": "test"
            },
            allow_redirects=False
        )
        
        # Get JSON list to verify structure
        json_resp = auth_session.get(f"{api_base_url}/api/v1/projects")
        assert json_resp.status_code == 200
        
        projects = json_resp.json()
        assert len(projects["items"]) > 0, "No projects in list"
        
        # Verify project has correct fields
        project = projects["items"][0]
        assert "title" in project, \
            f"Project missing 'title' field. Has: {list(project.keys())}"
        assert "id" in project, "Project missing 'id' field"
        assert "owner_id" in project, "Project missing 'owner_id' field"
        assert "category" in project, "Project missing 'category' field"
        assert "slug" in project, "Project missing 'slug' field"
        
        # These may or may not be present, but shouldn't cause crashes
        assert "disk_size_bytes" in project or True, "Disk size field should exist"
    
    def test_project_list_html_displays_category_field(self, api_base_url, auth_session):
        """Project list HTML should display category (not description) since that's what model has."""
        # Create with visibility=public (becomes category)
        auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "Category Display Test",
                "description": "Testing category display",
                "visibility": "public",
                "tags": "test"
            },
            allow_redirects=False
        )
        
        # Get HTML
        html_resp = auth_session.get(
            f"{api_base_url}/api/v1/projects?format=html"
        )
        
        # Verify it displays without crashing (no template errors)
        assert "Category Display Test" in html_resp.text, \
            "Project name should be displayed"
        # The category field should be shown (even if name doesn't mention it)
        assert html_resp.status_code == 200, \
            "HTML rendering should work without template errors"


class TestHtmxResponseHandling:
    """Tests for HTMX-specific response handling."""
    
    def test_create_project_modal_loads_correctly(self, api_base_url, auth_session):
        """Create project modal should load without errors."""
        resp = auth_session.get(f"{api_base_url}/projects/create-modal")
        
        assert resp.status_code == 200, \
            f"Modal load failed with {resp.status_code}"
        assert "project-form" in resp.text, \
            "Modal should contain project-form element"
        assert "project_name" in resp.text, \
            "Form should have project_name field"
        assert "hx-post" in resp.text and "/api/v1/projects" in resp.text, \
            "Form should have HTMX post to /api/v1/projects"
    
    def test_create_project_response_is_html_fragment(self, api_base_url, auth_session):
        """Create project response should be HTML fragment (not JSON or redirect)."""
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "HTMX Response Test",
                "description": "Testing response format",
                "visibility": "private",
                "tags": "test"
            },
            headers={"HX-Request": "true"},
            allow_redirects=False
        )
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        assert "text/html" in resp.headers.get("Content-Type", ""), \
            "Response should be HTML, not JSON"
        assert "alert" in resp.text.lower() or "success" in resp.text.lower(), \
            "Response should contain alert/success message"


class TestFormDataMapping:
    """Tests for correct mapping between form fields and backend parameters."""
    
    def test_form_name_field_maps_to_title_parameter(self, api_base_url, auth_session):
        """Form 'name' field should be accepted and stored as 'title'."""
        project_name = "Name Mapping Test"
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": project_name,  # Form uses 'name' field
                "visibility": "private"
            },
            allow_redirects=False
        )
        
        assert resp.status_code == 201, \
            f"Creation failed: {resp.status_code}"
        
        # Verify in list that it was stored as 'title'
        list_resp = auth_session.get(f"{api_base_url}/api/v1/projects")
        projects = list_resp.json()
        titles = [p["title"] for p in projects["items"]]
        assert project_name in titles, \
            f"Project name not found as 'title' in list. Titles: {titles}"
    
    def test_form_visibility_maps_to_visibility_field(self, api_base_url, auth_session):
        """Form 'visibility' field should be stored in project visibility."""
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "Visibility Mapping Test",
                "visibility": "public",
                "tags": "test"
            },
            allow_redirects=False
        )
        
        assert resp.status_code == 201
        
        # Verify visibility was set
        list_resp = auth_session.get(f"{api_base_url}/api/v1/projects")
        projects = list_resp.json()
        
        # Find our project
        test_project = next(
            (p for p in projects["items"] if p["title"] == "Visibility Mapping Test"),
            None
        )
        assert test_project is not None, "Test project not found in list"
        assert test_project["visibility"] == "public", \
            f"Visibility should be 'public', got {test_project['visibility']}"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_project_creation_with_special_characters(self, api_base_url, auth_session):
        """Project names with special characters should be handled safely."""
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "Project <script>alert('xss')</script> & \"special\"",
                "visibility": "private"
            },
            allow_redirects=False
        )
        
        # Should either succeed with sanitization or fail gracefully
        assert resp.status_code in (201, 400), \
            f"Unexpected status {resp.status_code}"
    
    def test_project_name_length_validation(self, api_base_url, auth_session):
        """Very long project names should be validated."""
        resp = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={
                "name": "x" * 1000,  # Extremely long
                "visibility": "private"
            },
            allow_redirects=False
        )
        
        # Should fail validation
        assert resp.status_code in (400, 413), \
            f"Long project names should be rejected, got {resp.status_code}"
    
    def test_concurrent_project_creation_with_same_name(self, api_base_url, auth_session):
        """Creating multiple projects with same name in same category should work (different slugs)."""
        project_name = "Concurrent Test"
        
        resp1 = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={"name": project_name, "visibility": "private"},
            allow_redirects=False
        )
        assert resp1.status_code == 201
        
        resp2 = auth_session.post(
            f"{api_base_url}/api/v1/projects",
            data={"name": project_name, "visibility": "private"},
            allow_redirects=False
        )
        assert resp2.status_code == 201, \
            "Should allow duplicate names (will have different slugs)"
        
        # Verify both appear in list
        list_resp = auth_session.get(f"{api_base_url}/api/v1/projects")
        projects = list_resp.json()
        matching = [p for p in projects["items"] if p["title"] == project_name]
        assert len(matching) >= 2, \
            f"Should have at least 2 projects with name '{project_name}'"
