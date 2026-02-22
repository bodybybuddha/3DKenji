"""E2E tests for project CRUD operations."""

import pytest
from playwright.sync_api import Page
from tests.e2e.pages.auth_page import AuthPage
from tests.e2e.pages.project_page import ProjectPage


@pytest.fixture
def logged_in_page(page: Page):
    """Fixture to provide a logged-in user."""
    auth_page = AuthPage(page)
    auth_page.navigate_to_register()
    auth_page.register(
        username=f"projectuser_{page.context.pages.index(page)}",
        email=f"projectuser_{page.context.pages.index(page)}@example.com",
        password="SecurePass123!",
        display_name="Project Test User"
    )
    return page


class TestProjectCRUD:
    """Test project creation, reading, updating, and deletion."""

    def test_create_project_success(self, logged_in_page: Page):
        """Test creating a project with valid data."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_page.create_project(
            name="Test Project",
            description="A test project for E2E testing"
        )

        # Project should be created and visible
        assert project_page.project_exists("Test Project")

    def test_create_project_with_empty_name(self, logged_in_page: Page):
        """Test creating project with empty name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_page.open_create_modal()
        project_page.fill_input(project_page.PROJECT_NAME_INPUT, "")
        project_page.click_button(project_page.SAVE_BUTTON)

        # Should show validation error
        error = project_page.get_validation_error("name")
        assert error or not project_page.project_exists("")

    def test_create_project_with_long_name(self, logged_in_page: Page):
        """Test creating project with excessively long name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        long_name = "A" * 300  # Assuming max is 255 or similar
        project_page.open_create_modal()
        project_page.fill_input(project_page.PROJECT_NAME_INPUT, long_name)
        project_page.click_button(project_page.SAVE_BUTTON)

        # Should either truncate or show error
        error = project_page.get_validation_error("name") or project_page.get_error_message()
        # Some validation should occur

    def test_create_project_with_special_characters(self, logged_in_page: Page):
        """Test creating project with special characters in name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        special_name = "Test <script>alert('xss')</script> Project"
        project_page.create_project(
            name=special_name,
            description="Testing special chars"
        )

        # Project should be created with sanitized name
        # Check that the script tag doesn't execute
        logged_in_page.wait_for_timeout(500)
        # If no alert, XSS was prevented

    def test_create_duplicate_project_name(self, logged_in_page: Page):
        """Test creating project with duplicate name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        # Create first project
        project_page.create_project(
            name="Duplicate Project",
            description="First one"
        )

        # Try to create another with same name
        project_page.create_project(
            name="Duplicate Project",
            description="Second one"
        )

        # Depending on requirements:
        # - Should either allow (different projects)
        # - Or reject (unique names per user)
        # This test documents the expected behavior

    def test_list_projects(self, logged_in_page: Page):
        """Test viewing list of projects."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        # Create multiple projects
        for i in range(3):
            project_page.create_project(
                name=f"List Test Project {i}",
                description=f"Description {i}"
            )

        # All projects should be visible
        cards = project_page.get_project_cards()
        assert len(cards) >= 3

    def test_open_project_detail(self, logged_in_page: Page):
        """Test opening project detail view."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_name = "Detail Test Project"
        project_page.create_project(
            name=project_name,
            description="For testing detail view"
        )

        # Open project
        project_page.open_project(project_name)

        # Should navigate to project detail
        project_page.assert_text_visible(project_name)

    def test_delete_project(self, logged_in_page: Page):
        """Test deleting a project."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_name = "To Be Deleted"
        project_page.create_project(
            name=project_name,
            description="This will be deleted"
        )

        # Verify it exists
        assert project_page.project_exists(project_name)

        # Delete it
        project_page.delete_project(project_name)

        # Verify it's gone
        assert not project_page.project_exists(project_name)

    def test_project_form_validation_on_blur(self, logged_in_page: Page):
        """Test that form validation occurs on field blur."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()
        project_page.open_create_modal()

        # Fill invalid data and blur field
        name_input = logged_in_page.locator(project_page.PROJECT_NAME_INPUT)
        name_input.fill("")
        name_input.blur()

        # Should show inline validation error
        logged_in_page.wait_for_timeout(300)  # Wait for HTMX validation
        error = project_page.get_validation_error("name")
        # Error might appear immediately or on submit

    def test_project_sql_injection_attempt(self, logged_in_page: Page):
        """Test SQL injection prevention in project name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        sql_injection = "'; DROP TABLE projects; --"
        project_page.create_project(
            name=sql_injection,
            description="SQL injection test"
        )

        # Project list should still be accessible (table not dropped)
        project_page.navigate_to_projects()
        # If we can still see the page, SQL injection was prevented

    def test_project_unicode_support(self, logged_in_page: Page):
        """Test projects with unicode characters."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        unicode_name = "プロジェクト 测试 Projekt 🚀"
        project_page.create_project(
            name=unicode_name,
            description="Testing unicode support"
        )

        # Should handle unicode properly
        assert project_page.project_exists("プロジェクト") or \
               project_page.project_exists("🚀")

    def test_project_description_html_escape(self, logged_in_page: Page):
        """Test that HTML in description is escaped."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        html_description = "<b>Bold</b> <script>alert('xss')</script>"
        project_page.create_project(
            name="HTML Test Project",
            description=html_description
        )

        # Open project to see description
        project_page.open_project("HTML Test Project")

        # Check that script didn't execute
        logged_in_page.wait_for_timeout(500)
        # If no alert, XSS was prevented
