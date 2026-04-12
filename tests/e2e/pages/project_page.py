"""Page object for project management pages."""

from playwright.sync_api import expect

from .base_page import BasePage


class ProjectPage(BasePage):
    """Page object for project management."""

    # Selectors
    CREATE_PROJECT_BUTTON = "button:has-text('New Project')"
    PROJECT_MODAL = "#project-form-modal"
    PROJECT_FORM = "#project-form"
    PROJECT_ALERT = "#project-form-alert"
    PROJECT_NAME_INPUT = "#project_name"
    PROJECT_DESCRIPTION_INPUT = "#project_description"
    PROJECT_VISIBILITY_INPUT = "#project_visibility"
    SAVE_BUTTON = "#submit-btn"
    PROJECT_TABLE = "#projects-table"
    PROJECT_ROW = "#projects-table .tabulator-row"
    DELETE_BUTTON = "button[title='Delete']"
    EDIT_BUTTON = "button[title='Edit']"

    def navigate_to_projects(self):
        """Navigate to projects list."""
        self.navigate("/projects")
        self.page.wait_for_selector("h1:has-text('Projects')")
        self.page.wait_for_selector(self.PROJECT_TABLE)

    def open_create_modal(self):
        """Open create project modal."""
        self.page.click(self.CREATE_PROJECT_BUTTON)
        self.page.wait_for_selector(self.PROJECT_MODAL, state="visible")

    def create_project(self, name: str, description: str = "", visibility: str = "private"):
        """Create a new project."""
        self.open_create_modal()
        self.fill_input(self.PROJECT_NAME_INPUT, name)
        
        if description and self.page.locator(self.PROJECT_DESCRIPTION_INPUT).count():
            self.fill_input(self.PROJECT_DESCRIPTION_INPUT, description)

        if self.page.locator(self.PROJECT_VISIBILITY_INPUT).count():
            self.page.select_option(self.PROJECT_VISIBILITY_INPUT, visibility)
        
        self.page.click(self.SAVE_BUTTON)
        self.page.wait_for_selector(f"{self.PROJECT_ALERT} .alert-success", timeout=10000)
        self.page.wait_for_timeout(1800)
        if self.page.locator(self.PROJECT_MODAL).count() and self.page.locator(self.PROJECT_MODAL).first.is_visible():
            self.navigate_to_projects()
        self.page.wait_for_selector(f"{self.PROJECT_ROW}:has-text('{name}')", timeout=10000)

    def get_project_rows(self):
        """Get all project rows."""
        return self.page.locator(self.PROJECT_ROW)

    def _project_row(self, name: str):
        """Locate a project row by project name."""
        return self.page.locator(self.PROJECT_ROW).filter(has_text=name).first

    def project_exists(self, name: str) -> bool:
        """Check if project with name exists."""
        return self.page.locator(self.PROJECT_ROW).filter(has_text=name).count() > 0

    def open_project(self, name: str):
        """Open project by name."""
        project = self._project_row(name)
        project.locator("a:has-text('View')").click()
        self.page.wait_for_url("**/project/*", timeout=10000)

    def delete_project(self, name: str):
        """Delete project by name."""
        project = self._project_row(name)
        self.page.once("dialog", lambda dialog: dialog.accept())
        project.locator("button:has-text('Delete')").click()
        expect(self.page.locator(self.PROJECT_ROW).filter(has_text=name)).to_have_count(0, timeout=10000)

    def edit_project(self, old_name: str, new_name: str, visibility: str = "public"):
        """Edit an existing project."""
        project = self._project_row(old_name)
        project.locator("button:has-text('Edit')").click()
        self.page.wait_for_selector(self.PROJECT_MODAL, state="visible")
        self.fill_input(self.PROJECT_NAME_INPUT, new_name)
        if self.page.locator(self.PROJECT_VISIBILITY_INPUT).count():
            self.page.select_option(self.PROJECT_VISIBILITY_INPUT, visibility)
        self.page.click(self.SAVE_BUTTON)
        self.page.wait_for_selector(f"{self.PROJECT_ALERT} .alert-success", timeout=10000)
        self.page.wait_for_timeout(1800)
        if self.page.locator(self.PROJECT_MODAL).count() and self.page.locator(self.PROJECT_MODAL).first.is_visible():
            self.navigate_to_projects()
        self.page.wait_for_selector(f"{self.PROJECT_ROW}:has-text('{new_name}')", timeout=10000)

    def get_validation_error(self, field: str) -> str:
        """Get validation error for a field."""
        error = self.page.locator(f"{self.PROJECT_ALERT} .alert li:has-text('{field}:')").first
        if error.is_visible():
            return error.inner_text()
        return ""
