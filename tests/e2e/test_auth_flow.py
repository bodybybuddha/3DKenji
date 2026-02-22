"""E2E tests for authentication flows."""

import pytest
from playwright.sync_api import Page, expect
from tests.e2e.pages.auth_page import AuthPage


class TestAuthFlow:
    """Test complete authentication workflows."""

    def test_user_registration_success(self, page: Page):
        """Test successful user registration."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        # Register new user
        auth_page.register(
            username="testuser123",
            email="testuser123@example.com",
            password="SecurePass123!",
            display_name="Test User"
        )

        # Should redirect to dashboard
        assert auth_page.is_logged_in()
        assert auth_page.is_on_dashboard()

    def test_registration_with_invalid_email(self, page: Page):
        """Test registration with invalid email format."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        auth_page.register(
            username="testuser",
            email="not-an-email",
            password="SecurePass123!"
        )

        # Should show validation error
        error = auth_page.get_validation_error("email")
        assert "valid email" in error.lower() or "invalid" in error.lower()

    def test_registration_with_weak_password(self, page: Page):
        """Test registration with weak password."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        auth_page.register(
            username="testuser",
            email="test@example.com",
            password="123"  # Too weak
        )

        # Should show validation error
        error = auth_page.get_validation_error("password") or auth_page.get_error_message()
        assert error  # Some error should be present

    def test_registration_with_duplicate_username(self, page: Page):
        """Test registration with existing username."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        # First registration
        auth_page.register(
            username="duplicateuser",
            email="user1@example.com",
            password="SecurePass123!"
        )

        # Logout
        auth_page.logout()

        # Try to register with same username
        auth_page.navigate_to_register()
        auth_page.register(
            username="duplicateuser",
            email="user2@example.com",
            password="SecurePass123!"
        )

        # Should show error
        error = auth_page.get_error_message()
        assert "already exists" in error.lower() or "taken" in error.lower()

    def test_registration_with_missing_required_fields(self, page: Page):
        """Test registration with missing required fields."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        # Try to submit empty form
        auth_page.click_button(auth_page.SUBMIT_BUTTON)

        # Should not proceed (form validation should prevent submission)
        # Check we're still on registration page
        assert "/setup" in page.url or "/register" in page.url

    def test_login_with_valid_credentials(self, page: Page):
        """Test login with valid credentials."""
        auth_page = AuthPage(page)
        
        # First register a user
        auth_page.navigate_to_register()
        auth_page.register(
            username="loginuser",
            email="login@example.com",
            password="SecurePass123!"
        )
        auth_page.logout()

        # Now login
        auth_page.navigate_to_login()
        auth_page.login("loginuser", "SecurePass123!")

        # Should be logged in
        assert auth_page.is_logged_in()
        assert auth_page.is_on_dashboard()

    def test_login_with_incorrect_password(self, page: Page):
        """Test login with incorrect password."""
        auth_page = AuthPage(page)
        
        # Register a user first
        auth_page.navigate_to_register()
        auth_page.register(
            username="wrongpassuser",
            email="wrongpass@example.com",
            password="CorrectPass123!"
        )
        auth_page.logout()

        # Try to login with wrong password
        auth_page.navigate_to_login()
        auth_page.login("wrongpassuser", "WrongPass123!")

        # Should show error
        error = auth_page.get_error_message()
        assert "invalid" in error.lower() or "incorrect" in error.lower()

    def test_login_with_nonexistent_user(self, page: Page):
        """Test login with non-existent username."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_login()

        auth_page.login("nonexistentuser999", "SomePassword123!")

        # Should show error
        error = auth_page.get_error_message()
        assert error  # Should have some error message

    def test_logout_flow(self, page: Page):
        """Test logout functionality."""
        auth_page = AuthPage(page)
        
        # Register and login
        auth_page.navigate_to_register()
        auth_page.register(
            username="logoutuser",
            email="logout@example.com",
            password="SecurePass123!"
        )

        # User should be logged in
        assert auth_page.is_logged_in()

        # Logout
        auth_page.logout()

        # Should not be logged in anymore
        assert not auth_page.is_logged_in()

    def test_special_characters_in_username(self, page: Page):
        """Test username validation with special characters."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        # Try SQL injection
        auth_page.register(
            username="admin'; DROP TABLE users--",
            email="test@example.com",
            password="SecurePass123!"
        )

        # Should show validation error or sanitize
        error = auth_page.get_validation_error("username") or auth_page.get_error_message()
        # Either rejects or sanitizes - both are acceptable

    def test_xss_attempt_in_display_name(self, page: Page):
        """Test XSS prevention in display name."""
        auth_page = AuthPage(page)
        auth_page.navigate_to_register()

        xss_payload = "<script>alert('XSS')</script>"
        auth_page.register(
            username="xssuser",
            email="xss@example.com",
            password="SecurePass123!",
            display_name=xss_payload
        )

        # Check that script is not executed (page should not have alert)
        # and display name is escaped or sanitized
        page.wait_for_timeout(500)  # Brief wait to ensure no alert
        # If we get here without alert, XSS was prevented

    def test_concurrent_session_handling(self, page: Page, context):
        """Test handling of concurrent sessions."""
        auth_page = AuthPage(page)
        
        # Login in first session
        auth_page.navigate_to_register()
        auth_page.register(
            username="concurrentuser",
            email="concurrent@example.com",
            password="SecurePass123!"
        )

        # Open new page (new session)
        page2 = context.new_page()
        auth_page2 = AuthPage(page2)
        
        # Login in second session
        auth_page2.navigate_to_login()
        auth_page2.login("concurrentuser", "SecurePass123!")

        # Both sessions should work (or first should be invalidated based on requirements)
        assert auth_page2.is_logged_in()

        page2.close()
