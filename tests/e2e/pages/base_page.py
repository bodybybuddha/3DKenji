"""Base page object for common functionality."""

import os

from playwright.sync_api import Page, expect


class BasePage:
    """Base page object with common methods."""

    def __init__(self, page: Page, base_url: str | None = None):
        self.page = page
        self.base_url = base_url or os.getenv("E2E_BASE_URL") or os.getenv("API_BASE_URL", "http://localhost:8000")

    def navigate(self, path: str = "/"):
        """Navigate to a path."""
        self.page.goto(f"{self.base_url}{path}")

    def wait_for_htmx(self):
        """Wait for HTMX requests to complete."""
        # Wait for network to be idle
        self.page.wait_for_load_state("networkidle")

    def fill_input(self, selector: str, value: str):
        """Fill an input field."""
        self.page.fill(selector, value)

    def click_button(self, selector: str):
        """Click a button and wait for HTMX."""
        self.page.click(selector)
        self.wait_for_htmx()

    def submit_form(self, form_selector: str):
        """Submit a form and wait for response."""
        self.page.locator(form_selector).evaluate("form => form.submit()")
        self.wait_for_htmx()

    def get_error_message(self) -> str:
        """Get error message if present."""
        error = self.page.locator(".error-message, .alert-error, .alert-danger").first
        if error.is_visible():
            return error.inner_text()
        return ""

    def get_success_message(self) -> str:
        """Get success message if present."""
        success = self.page.locator(".success-message, .alert-success").first
        if success.is_visible():
            return success.inner_text()
        return ""

    def is_element_visible(self, selector: str, timeout: int = 5000) -> bool:
        """Check if element is visible."""
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except:
            return False

    def screenshot(self, name: str):
        """Take a screenshot."""
        self.page.screenshot(path=f"tests/e2e/screenshots/{name}.png")

    def wait_for_modal(self):
        """Wait for modal to appear."""
        self.page.wait_for_selector(".modal, [role='dialog']", state="visible")

    def close_modal(self):
        """Close modal by clicking close button or pressing escape."""
        close_btn = self.page.locator(".modal-close, [aria-label='Close']").first
        if close_btn.is_visible():
            close_btn.click()
        else:
            self.page.keyboard.press("Escape")
        self.wait_for_htmx()

    def assert_url_contains(self, path: str):
        """Assert current URL contains path."""
        expect(self.page).to_have_url(f".*{path}.*")

    def assert_text_visible(self, text: str):
        """Assert text is visible on page."""
        expect(self.page.locator(f"text={text}").first).to_be_visible()
