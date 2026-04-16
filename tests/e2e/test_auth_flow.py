"""E2E tests for authentication flows."""

import uuid

from playwright.sync_api import Browser, Page, expect
from tests.e2e.pages.auth_page import AuthPage


class TestAuthFlow:
    """Test complete authentication workflows."""

    def test_user_registration_success(self, page: Page):
        """Test successful user registration."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()
        suffix = uuid.uuid4().hex[:8]

        auth_page.register(
            username=f"testuser_{suffix}",
            email=f"testuser_{suffix}@example.com",
            password="SecurePass123!",
            display_name="Test User"
        )

        page.wait_for_url("**/projects", timeout=10000)
        assert auth_page.is_logged_in()
        assert auth_page.is_on_dashboard()

    def test_registration_with_invalid_email(self, page: Page):
        """Test registration with invalid email format."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        auth_page.register(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email="not-an-email",
            password="SecurePass123!"
        )

        error = page.locator(auth_page.EMAIL_INPUT).evaluate("element => element.validationMessage")
        assert error

    def test_registration_with_weak_password(self, page: Page):
        """Test registration with weak password."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        auth_page.register(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"weak_{uuid.uuid4().hex[:8]}@example.com",
            password="123"  # Too weak
        )

        error = page.locator(auth_page.PASSWORD_INPUT).evaluate("element => element.validationMessage")
        assert error

    def test_registration_with_duplicate_username(self, page: Page):
        """Test registration with existing username."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()
        duplicate_username = f"duplicate_{uuid.uuid4().hex[:8]}"

        auth_page.register(
            username=duplicate_username,
            email=f"{duplicate_username}_1@example.com",
            password="SecurePass123!"
        )
        page.wait_for_url("**/projects", timeout=10000)

        auth_page.logout()

        auth_page.navigate_to_register()
        auth_page.register(
            username=duplicate_username,
            email=f"{duplicate_username}_2@example.com",
            password="SecurePass123!"
        )

        error = auth_page.get_error_message()
        assert "already exists" in error.lower() or "taken" in error.lower()

    def test_registration_with_missing_required_fields(self, page: Page):
        """Test registration with missing required fields."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        page.click(f"{auth_page.REGISTER_FORM} {auth_page.SUBMIT_BUTTON}")

        assert "/register" in page.url
        assert page.locator(auth_page.REGISTER_FORM).count() == 1

    def test_login_with_valid_credentials(self, page: Page):
        """Test login with valid credentials."""
        auth_page = AuthPage(page)
        suffix = uuid.uuid4().hex[:8]
        
        auth_page.navigate_to_register()
        auth_page.register(
            username=f"login_{suffix}",
            email=f"login_{suffix}@example.com",
            password="SecurePass123!"
        )
        page.wait_for_url("**/projects", timeout=10000)
        auth_page.logout()

        auth_page.navigate_to_login()
        auth_page.login(f"login_{suffix}", "SecurePass123!")

        page.wait_for_url("**/projects", timeout=10000)
        assert auth_page.is_logged_in()
        assert auth_page.is_on_dashboard()

    def test_login_with_incorrect_password(self, page: Page):
        """Test login with incorrect password."""
        auth_page = AuthPage(page)
        suffix = uuid.uuid4().hex[:8]
        
        auth_page.navigate_to_register()
        auth_page.register(
            username=f"wrongpass_{suffix}",
            email=f"wrongpass_{suffix}@example.com",
            password="CorrectPass123!"
        )
        page.wait_for_url("**/projects", timeout=10000)
        auth_page.logout()

        auth_page.navigate_to_login()
        auth_page.login(f"wrongpass_{suffix}", "WrongPass123!")

        error = auth_page.get_error_message()
        assert "invalid" in error.lower() or "incorrect" in error.lower()

    def test_login_with_nonexistent_user(self, page: Page):
        """Test login with non-existent username."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_login()

        auth_page.login("nonexistentuser999", "SomePassword123!")

        error = auth_page.get_error_message()
        assert "invalid" in error.lower() or "password" in error.lower()

    def test_logout_flow(self, page: Page):
        """Test logout functionality."""
        auth_page = AuthPage(page)
        suffix = uuid.uuid4().hex[:8]
        
        auth_page.navigate_to_register()
        auth_page.register(
            username=f"logout_{suffix}",
            email=f"logout_{suffix}@example.com",
            password="SecurePass123!"
        )
        page.wait_for_url("**/projects", timeout=10000)

        assert auth_page.is_logged_in()

        auth_page.logout()

        assert not auth_page.is_logged_in()
        assert "/login" in page.url

    def test_special_characters_in_username(self, page: Page):
        """Test username validation with special characters."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        auth_page.register(
            username="admin'; DROP TABLE users--",
            email="test@example.com",
            password="SecurePass123!"
        )

        error = auth_page.get_validation_error("username") or auth_page.get_error_message()
        assert "username" in error.lower() or "invalid" in error.lower()

    def test_registration_accepts_optional_display_name(self, page: Page):
        """Test registration succeeds when display name is omitted."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()
        suffix = uuid.uuid4().hex[:8]

        auth_page.register(
            username=f"nodisplay_{suffix}",
            email=f"nodisplay_{suffix}@example.com",
            password="SecurePass123!"
        )

        page.wait_for_url("**/projects", timeout=10000)
        assert auth_page.is_logged_in()

    def test_concurrent_session_handling(self, page: Page, browser: Browser):
        """Test handling of concurrent sessions."""
        auth_page = AuthPage(page)
        suffix = uuid.uuid4().hex[:8]
        
        auth_page.navigate_to_register()
        auth_page.register(
            username=f"concurrent_{suffix}",
            email=f"concurrent_{suffix}@example.com",
            password="SecurePass123!"
        )
        page.wait_for_url("**/projects", timeout=10000)

        second_context = browser.new_context()
        page2 = second_context.new_page()
        auth_page2 = AuthPage(page2)
        
        auth_page2.navigate_to_login()
        auth_page2.login(f"concurrent_{suffix}@example.com", "SecurePass123!")

        page2.wait_for_url("**/projects", timeout=10000)
        assert auth_page2.is_logged_in()
        assert auth_page.is_logged_in()

        second_context.close()
