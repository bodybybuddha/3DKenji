"""Page object for authentication pages."""

from .base_page import BasePage


class AuthPage(BasePage):
    """Page object for authentication flows."""

    # Selectors
    REGISTER_FORM = "form[action='/api/v1/auth/register']"
    LOGIN_FORM = "form[action='/api/v1/auth/login']"
    USERNAME_INPUT = "input[name='username']"
    EMAIL_INPUT = "input[name='email']"
    PASSWORD_INPUT = "input[name='password']"
    DISPLAY_NAME_INPUT = "input[name='display_name']"
    SUBMIT_BUTTON = "button[type='submit']"
    LOGOUT_BUTTON = "a[href='/logout'], button:has-text('Logout')"

    def navigate_to_register(self):
        """Navigate to registration page."""
        self.navigate("/setup")

    def navigate_to_login(self):
        """Navigate to login page."""
        self.navigate("/login")

    def register(self, username: str, email: str, password: str, display_name: str = ""):
        """Register a new user."""
        self.fill_input(self.USERNAME_INPUT, username)
        self.fill_input(self.EMAIL_INPUT, email)
        self.fill_input(self.PASSWORD_INPUT, password)
        
        if display_name:
            self.fill_input(self.DISPLAY_NAME_INPUT, display_name)
        
        self.click_button(self.SUBMIT_BUTTON)

    def login(self, username: str, password: str):
        """Login with credentials."""
        self.fill_input(self.USERNAME_INPUT, username)
        self.fill_input(self.PASSWORD_INPUT, password)
        self.click_button(self.SUBMIT_BUTTON)

    def logout(self):
        """Logout current user."""
        if self.is_element_visible(self.LOGOUT_BUTTON):
            self.click_button(self.LOGOUT_BUTTON)

    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        return self.is_element_visible(self.LOGOUT_BUTTON)

    def get_validation_error(self, field: str) -> str:
        """Get validation error for a specific field."""
        error = self.page.locator(f"input[name='{field}'] + .error, .field-error-{field}").first
        if error.is_visible():
            return error.inner_text()
        return ""

    def is_on_dashboard(self) -> bool:
        """Check if on dashboard after login."""
        return "/dashboard" in self.page.url or self.page.url.endswith("/")
