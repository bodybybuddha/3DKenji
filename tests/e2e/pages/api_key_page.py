"""Page object for API key management."""

from .base_page import BasePage


class APIKeyPage(BasePage):
    """Page object for API key management."""

    # Selectors
    CREATE_KEY_BUTTON = "button:has-text('Create API Key'), button:has-text('New Key')"
    KEY_NAME_INPUT = "input[name='name']"
    KEY_EXPIRATION_INPUT = "input[name='expires_at']"
    SAVE_BUTTON = "button[type='submit']"
    API_KEY_ROW = ".api-key-item, tr.key-row"
    REVOKE_BUTTON = "button:has-text('Revoke')"
    CONFIRM_REVOKE = "button:has-text('Confirm')"
    API_KEY_SECRET = ".api-key-secret, code"

    def navigate_to_keys(self):
        """Navigate to API keys page."""
        self.navigate("/settings/keys")

    def open_create_modal(self):
        """Open create API key modal."""
        self.click_button(self.CREATE_KEY_BUTTON)
        self.wait_for_modal()

    def create_key(self, name: str, expires_at: str | None = None):
        """Create a new API key."""
        self.open_create_modal()
        self.fill_input(self.KEY_NAME_INPUT, name)
        
        if expires_at:
            self.fill_input(self.KEY_EXPIRATION_INPUT, expires_at)
        
        self.click_button(self.SAVE_BUTTON)

    def get_key_secret(self) -> str:
        """Get the displayed API key secret after creation."""
        secret_element = self.page.locator(self.API_KEY_SECRET).first
        secret_element.wait_for(state="visible")
        return secret_element.inner_text()

    def key_exists(self, name: str) -> bool:
        """Check if API key with name exists."""
        return self.is_element_visible(f"text={name}")

    def revoke_key(self, name: str):
        """Revoke API key by name."""
        key_row = self.page.locator(f"{self.API_KEY_ROW}:has-text('{name}')").first
        key_row.hover()
        key_row.locator(self.REVOKE_BUTTON).click()
        
        # Confirm revocation
        self.click_button(self.CONFIRM_REVOKE)

    def get_key_count(self) -> int:
        """Get number of API keys listed."""
        return self.page.locator(self.API_KEY_ROW).count()
