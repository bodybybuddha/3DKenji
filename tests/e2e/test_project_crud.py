"""E2E tests for project CRUD operations."""

import uuid

import pytest
from playwright.sync_api import Page
from tests.e2e.pages.project_page import ProjectPage


@pytest.fixture
def logged_in_page(authenticated_page: Page):
    """Fixture to provide a logged-in user."""
    return authenticated_page


class TestProjectCRUD:
    """Test project creation, reading, updating, and deletion."""

    def test_create_project_success(self, logged_in_page: Page):
        """Test creating a project with valid data."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()
        project_name = f"Test Project {uuid.uuid4().hex[:8]}"

        project_page.create_project(
            name=project_name,
            description="A test project for E2E testing"
        )

        assert project_page.project_exists(project_name)

    def test_create_project_with_empty_name(self, logged_in_page: Page):
        """Test creating project with empty name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_page.open_create_modal()
        project_page.fill_input(project_page.PROJECT_NAME_INPUT, "   ")
        logged_in_page.click(project_page.SAVE_BUTTON)

        logged_in_page.wait_for_timeout(500)
        error = project_page.get_validation_error("name") or project_page.get_error_message()
        assert error
        assert not project_page.project_exists("   ")

    def test_create_project_with_long_name(self, logged_in_page: Page):
        """Test creating project with excessively long name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        long_name = "A" * 300
        project_page.open_create_modal()
        project_page.fill_input(project_page.PROJECT_NAME_INPUT, long_name)
        logged_in_page.click(project_page.SAVE_BUTTON)

        logged_in_page.wait_for_timeout(500)
        error = project_page.get_validation_error("name") or project_page.get_error_message()
        assert error or logged_in_page.locator(project_page.PROJECT_MODAL).is_visible()
        assert not project_page.project_exists(long_name)

    def test_create_project_rejects_html_in_name(self, logged_in_page: Page):
        """Test creating project rejects HTML in the project name."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        special_name = "Test <script>alert('xss')</script> Project"
        project_page.open_create_modal()
        project_page.fill_input(project_page.PROJECT_NAME_INPUT, special_name)
        logged_in_page.click(project_page.SAVE_BUTTON)

        logged_in_page.wait_for_timeout(500)
        error = project_page.get_error_message()
        assert error or logged_in_page.locator(project_page.PROJECT_MODAL).is_visible()
        assert not project_page.project_exists(special_name)

    def test_list_projects(self, logged_in_page: Page):
        """Test viewing list of projects."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        for i in range(3):
            project_page.create_project(
                name=f"List Test Project {i} {uuid.uuid4().hex[:6]}",
                description=f"Description {i}"
            )

        cards = project_page.get_project_cards()
        assert cards.count() >= 3

    def test_open_project_detail(self, logged_in_page: Page):
        """Test opening project detail view."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_name = f"Detail Test Project {uuid.uuid4().hex[:8]}"
        project_page.create_project(
            name=project_name,
            description="For testing detail view"
        )

        project_page.open_project(project_name)

        project_page.assert_text_visible(project_name)
        assert logged_in_page.locator("button:has-text('Upload Model')").count() == 1

    def test_edit_project_name(self, logged_in_page: Page):
        """Test editing a project from the projects list."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        original_name = f"Editable Project {uuid.uuid4().hex[:8]}"
        updated_name = f"Updated Project {uuid.uuid4().hex[:8]}"
        project_page.create_project(name=original_name, description="Original")

        project_page.edit_project(original_name, updated_name)

        assert project_page.project_exists(updated_name)
        assert not project_page.project_exists(original_name)

    def test_delete_project(self, logged_in_page: Page):
        """Test deleting a project."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        project_name = f"To Be Deleted {uuid.uuid4().hex[:8]}"
        project_page.create_project(
            name=project_name,
            description="This will be deleted"
        )

        assert project_page.project_exists(project_name)

        project_page.delete_project(project_name)

        assert not project_page.project_exists(project_name)

    def test_project_sql_injection_attempt_does_not_break_page(self, logged_in_page: Page):
        """Test SQL injection-like input does not break the application."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        sql_injection = "'; DROP TABLE projects; --"
        project_page.open_create_modal()
        project_page.fill_input(project_page.PROJECT_NAME_INPUT, sql_injection)
        logged_in_page.click(project_page.SAVE_BUTTON)

        project_page.navigate_to_projects()
        assert logged_in_page.locator("h1:has-text('Projects')").count() == 1

    def test_project_unicode_support(self, logged_in_page: Page):
        """Test projects with unicode characters."""
        project_page = ProjectPage(logged_in_page)
        project_page.navigate_to_projects()

        unicode_name = "プロジェクト 测试 Projekt 🚀"
        project_page.create_project(
            name=unicode_name,
            description="Testing unicode support"
        )

        assert project_page.project_exists(unicode_name)
