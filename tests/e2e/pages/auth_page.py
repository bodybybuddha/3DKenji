"""Page object for authentication pages."""

from .base_page import BasePage


class AuthPage(BasePage):
    """Page object for authentication flows."""

    # Selectors
    REGISTER_FORM = "#register-form"
    LOGIN_FORM = "#login-form"
    USERNAME_INPUT = "#username"
    USERNAME_OR_EMAIL_INPUT = "#username_or_email"
    EMAIL_INPUT = "#email"
    PASSWORD_INPUT = "#password"
    PASSWORD_CONFIRM_INPUT = "#password_confirm"
    DISPLAY_NAME_INPUT = "#display_name"
    TERMS_CHECKBOX = "#terms"
    SUBMIT_BUTTON = "button[type='submit']"
    LOGOUT_BUTTON = "#user-menu-btn"

    def navigate_to_register(self):
        """Navigate to registration page."""
        self.navigate("/register")
        self.page.wait_for_selector(self.REGISTER_FORM)

    def navigate_to_login(self):
        """Navigate to login page."""
        self.navigate("/login")
        self.page.wait_for_selector(self.LOGIN_FORM)

    def register(self, username: str, email: str, password: str, display_name: str = ""):
        """Register a new user."""
        self.fill_input(self.USERNAME_INPUT, username)
        self.fill_input(self.EMAIL_INPUT, email)
        if self.page.locator(self.DISPLAY_NAME_INPUT).count():
            self.fill_input(self.DISPLAY_NAME_INPUT, display_name or username)
        self.fill_input(self.PASSWORD_INPUT, password)
        self.fill_input(self.PASSWORD_CONFIRM_INPUT, password)
        self.page.check(self.TERMS_CHECKBOX)
        
        self.page.click(f"{self.REGISTER_FORM} {self.SUBMIT_BUTTON}")
        self.page.wait_for_load_state("networkidle")

    def login(self, username_or_email: str, password: str):
        """Login with credentials."""
        self.fill_input(self.USERNAME_OR_EMAIL_INPUT, username_or_email)
        self.fill_input(self.PASSWORD_INPUT, password)
        self.page.click(f"{self.LOGIN_FORM} {self.SUBMIT_BUTTON}")
        self.page.wait_for_load_state("networkidle")

    def logout(self):
        """Logout current user."""
        if self.is_element_visible(self.LOGOUT_BUTTON):
            self.page.click(self.LOGOUT_BUTTON)
            self.page.click("a:has-text('Logout')")
            self.page.wait_for_url("**/login", timeout=10000)

    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        return self.page.locator("#logout-form").count() == 1 or self.page.locator("#user-menu-btn").count() == 1

    def get_validation_error(self, field: str) -> str:
        """Get validation error for a specific field."""
        error = self.page.locator(f".alert li:has-text('{field}:')").first
        if error.is_visible():
            return error.inner_text()
        return ""

    def is_on_dashboard(self) -> bool:
        """Check if on dashboard after login."""
        return "/projects" in self.page.url
