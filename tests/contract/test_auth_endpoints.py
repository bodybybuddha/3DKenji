"""Tests for authentication endpoints."""

import os
import httpx
import pytest


@pytest.fixture
def api_base_url():
    """Get API base URL from environment."""
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture
def http_client(api_base_url):
    """Create HTTP client for API testing."""
    return httpx.Client(base_url=api_base_url)


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_register_success(self, http_client):
        """Test successful user registration."""
        response = http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "secure_password_123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["display_name"] == "Test User"

    def test_register_duplicate_username(self, http_client):
        """Test registration with duplicate username."""
        http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "secure_password_123",
            },
        )

        response = http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test2@example.com",
                "display_name": "Another User",
                "password": "another_password_123",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_duplicate_email(self, http_client):
        """Test registration with duplicate email."""
        http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "secure_password_123",
            },
        )

        response = http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser2",
                "email": "test@example.com",
                "display_name": "Another User",
                "password": "another_password_123",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_weak_password(self, http_client):
        """Test registration with weak password."""
        response = http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "weak",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_login_success(self, http_client):
        """Test successful login."""
        # Register first
        http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "secure_password_123",
            },
        )

        # Login
        response = http_client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "secure_password_123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["username"] == "testuser"

    def test_login_invalid_credentials(self, http_client):
        """Test login with invalid credentials."""
        response = http_client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrong_password",
            },
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_password(self, http_client):
        """Test login with wrong password."""
        # Register first
        http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "correct_password_123",
            },
        )

        # Try login with wrong password
        response = http_client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrong_password",
            },
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_password_change_success(self, http_client):
        """Test successful password change."""
        # Register first
        reg_response = http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "pwchange_user",
                "email": "pwchange@example.com",
                "display_name": "PW Change User",
                "password": "old_password_123",
            },
        )

        token = reg_response.json()["access_token"]

        # Change password
        response = http_client.post(
            "/api/v1/auth/password-change",
            json={
                "current_password": "old_password_123",
                "new_password": "new_password_123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["username"] == "pwchange_user"

        # Verify old password doesn't work
        login_response = http_client.post(
            "/api/v1/auth/login",
            json={
                "username": "pwchange_user",
                "password": "old_password_123",
            },
        )
        assert login_response.status_code == 401

        # Verify new password works
        login_response = http_client.post(
            "/api/v1/auth/login",
            json={
                "username": "pwchange_user",
                "password": "new_password_123",
            },
        )
        assert login_response.status_code == 200

    def test_password_change_wrong_current_password(self, http_client):
        """Test password change with wrong current password."""
        # Register first
        reg_response = http_client.post(
            "/api/v1/auth/register",
            json={
                "username": "wrongpw_user",
                "email": "wrongpw@example.com",
                "display_name": "Wrong PW User",
                "password": "correct_password_123",
            },
        )

        token = reg_response.json()["access_token"]

        # Try change password with wrong current password
        response = http_client.post(
            "/api/v1/auth/password-change",
            json={
                "current_password": "wrong_password",
                "new_password": "new_password_123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert "Current password is incorrect" in response.json()["detail"]

    def test_password_change_without_auth(self, http_client):
        """Test password change without authentication."""
        response = http_client.post(
            "/api/v1/auth/password-change",
            json={
                "current_password": "password",
                "new_password": "new_password_123",
            },
        )

        assert response.status_code == 401

    def test_password_change_invalid_token(self, http_client):
        """Test password change with invalid token."""
        response = http_client.post(
            "/api/v1/auth/password-change",
            json={
                "current_password": "password",
                "new_password": "new_password_123",
            },
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401
