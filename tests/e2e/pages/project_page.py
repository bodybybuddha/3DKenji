"""Page object for project management pages."""

from .base_page import BasePage


class ProjectPage(BasePage):
    """Page object for project management."""

    # Selectors
    CREATE_PROJECT_BUTTON = "button:has-text('Create Project'), button:has-text('New Project')"
    PROJECT_NAME_INPUT = "input[name='name'], input[name='project_name']"
    PROJECT_DESCRIPTION_INPUT = "textarea[name='description']"
    SAVE_BUTTON = "button[type='submit'], button:has-text('Save'), button:has-text('Create')"
    PROJECT_CARD = ".project-card"
    PROJECT_TITLE = ".project-title, h2, h3"
    DELETE_BUTTON = "button:has-text('Delete')"
    EDIT_BUTTON = "button:has-text('Edit')"
    CONFIRM_DELETE = "button:has-text('Confirm'), button[data-action='confirm']"

    def navigate_to_projects(self):
        """Navigate to projects list."""
        self.navigate("/projects")

    def open_create_modal(self):
        """Open create project modal."""
        self.click_button(self.CREATE_PROJECT_BUTTON)
        self.wait_for_modal()

    def create_project(self, name: str, description: str = ""):
        """Create a new project."""
        self.open_create_modal()
        self.fill_input(self.PROJECT_NAME_INPUT, name)
        
        if description:
            self.fill_input(self.PROJECT_DESCRIPTION_INPUT, description)
        
        self.click_button(self.SAVE_BUTTON)

    def get_project_cards(self):
        """Get all project cards."""
        return self.page.locator(self.PROJECT_CARD).all()

    def project_exists(self, name: str) -> bool:
        """Check if project with name exists."""
        return self.is_element_visible(f"text={name}")

    def open_project(self, name: str):
        """Open project by name."""
        project = self.page.locator(f"{self.PROJECT_CARD}:has-text('{name}')").first
        project.click()
        self.wait_for_htmx()

    def delete_project(self, name: str):
        """Delete project by name."""
        project = self.page.locator(f"{self.PROJECT_CARD}:has-text('{name}')").first
        project.hover()
        project.locator(self.DELETE_BUTTON).click()
        
        # Confirm deletion
        self.click_button(self.CONFIRM_DELETE)

    def get_validation_error(self, field: str) -> str:
        """Get validation error for a field."""
        error = self.page.locator(f"input[name='{field}'] + .error, textarea[name='{field}'] + .error").first
        if error.is_visible():
            return error.inner_text()
        return ""
