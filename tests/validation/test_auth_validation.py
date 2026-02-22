"""Validation tests for authentication endpoints."""

import pytest
import uuid


class TestRegistrationValidation:
    """Test input validation for user registration."""

    @pytest.mark.parametrize("username", [
        "",
        " ",
        "ab",  # Too short
        "a" * 300,  # Too long
        "user name",  # Space
        "user@test",  # Invalid char
        "test<script>",  # XSS
        "admin'--",  # SQL injection
    ])
    def test_invalid_username_formats(self, client, username):
        """Test that invalid username formats are rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": "valid@example.com",
            "password": "SecurePass123!",
        })
        
        assert response.status_code in [400, 422]
        error = response.json()
        assert "detail" in error or "errors" in error

    @pytest.mark.parametrize("email", [
        "",
        "notanemail",
        "@example.com",
        "user@",
        "user @example.com",
        "<script>@test.com",
    ])
    def test_invalid_email_formats(self, client, email):
        """Test that invalid email formats are rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": "validuser",
            "email": email,
            "password": "SecurePass123!",
        })
        
        assert response.status_code in [400, 422]
        error = response.json()
        assert "email" in str(error).lower()

    @pytest.mark.parametrize("password,expected_error_keyword", [
        ("", "required"),
        ("123", "short"),
        ("a" * 1000, "long"),
    ])
    def test_invalid_password_formats(self, client, password, expected_error_keyword):
        """Test that invalid passwords are rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": "validuser",
            "email": "valid@example.com",
            "password": password,
            "display_name": "Valid User"
        })
        
        assert response.status_code in [400, 422]
        error_text = str(response.json()).lower()
        assert expected_error_keyword in error_text or "password" in error_text

    def test_missing_required_fields(self, client):
        """Test that missing required fields are rejected."""
        # Missing username
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        assert response.status_code == 422  # FastAPI validation error

        # Missing email
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "SecurePass123!",
        })
        assert response.status_code == 422

        # Missing password
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
        })
        assert response.status_code == 422

    def test_duplicate_username(self, client):
        """Test that duplicate usernames are rejected."""
        unique_id = str(uuid.uuid4())[:8]
        username = f"dupuser_{unique_id}"
        
        # Create first user
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"user1_{unique_id}@example.com",
            "password": "SecurePass123!",
            "display_name": "User 1"
        })
        assert response.status_code == 201

        # Try to create with same username
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"user2_{unique_id}@example.com",
            "password": "SecurePass123!",
            "display_name": "User 2"
        })
        assert response.status_code == 409  # Conflict

    def test_duplicate_email(self, client):
        """Test that duplicate emails are rejected."""
        unique_id = str(uuid.uuid4())[:8]
        email = f"dupemail_{unique_id}@example.com"
        
        # Create first user
        response = client.post("/api/v1/auth/register", json={
            "username": f"user1_{unique_id}",
            "email": email,
            "password": "SecurePass123!",
            "display_name": "User 1"
        })
        assert response.status_code == 201

        # Try to create with same email
        response = client.post("/api/v1/auth/register", json={
            "username": f"user2_{unique_id}",
            "email": email,
            "password": "SecurePass123!",
            "display_name": "User 2"
        })
        assert response.status_code == 409  # Conflict

    def test_xss_in_display_name(self, client, xss_payloads):
        """Test that XSS payloads in display name are sanitized or rejected."""
        for payload in xss_payloads[:3]:  # Test a few
            response = client.post("/api/v1/auth/register", json={
                "username": f"xssuser_{hash(payload)}",
                "email": f"xss_{hash(payload)}@example.com",
                "password": "SecurePass123!",
                "display_name": payload,
            })
            
            # Either rejected or accepted with sanitized value
            if response.status_code == 201:
                # Verify display_name doesn't contain script tags
                user = response.json()["user"]
                assert "<script>" not in user.get("display_name", "")

    def test_sql_injection_in_username(self, client, sql_injection_payloads):
        """Test that SQL injection attempts are prevented."""
        for payload in sql_injection_payloads[:3]:  # Test a few
            response = client.post("/api/v1/auth/register", json={
                "username": payload,
                "email": f"sql_{hash(payload)}@example.com",
                "password": "SecurePass123!",
            })
            
            # Should be rejected due to invalid format
            assert response.status_code in [400, 422]

    def test_unicode_in_display_name(self, client):
        """Test that unicode characters are properly handled."""
        response = client.post("/api/v1/auth/register", json={
            "username": "unicodeuser",
            "email": "unicode@example.com",
            "password": "SecurePass123!",
            "display_name": "User 日本語 😀",
        })
        
        assert response.status_code == 201
        user = response.json()["user"]
        assert "日本語" in user["display_name"]

    def test_very_long_display_name(self, client):
        """Test display name length limits."""
        long_name = "A" * 500
        response = client.post("/api/v1/auth/register", json={
            "username": "longname",
            "email": "longname@example.com",
            "password": "SecurePass123!",
            "display_name": long_name,
        })
        
        # Should either reject or truncate
        if response.status_code == 201:
            user = response.json()["user"]
            assert len(user["display_name"]) < 500


class TestLoginValidation:
    """Test input validation for user login."""

    def test_empty_credentials(self, client):
        """Test that empty credentials are rejected."""
        response = client.post("/api/v1/auth/login", json={
            "username": "",
            "password": "",
        })
        assert response.status_code in [400, 401, 422]

    def test_missing_password(self, client):
        """Test that missing password is rejected."""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
        })
        assert response.status_code == 422

    def test_wrong_password(self, client):
        """Test that wrong password is rejected."""
        # First register
        client.post("/api/v1/auth/register", json={
            "username": "wrongpasstest",
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
        })

        # Try wrong password
        response = client.post("/api/v1/auth/login", json={
            "username": "wrongpasstest",
            "password": "WrongPass123!",
        })
        assert response.status_code == 401

    def test_nonexistent_user(self, client):
        """Test that nonexistent user login is rejected."""
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent999",
            "password": "SomePass123!",
        })
        assert response.status_code == 401

    def test_sql_injection_in_login(self, client):
        """Test SQL injection prevention in login."""
        response = client.post("/api/v1/auth/login", json={
            "username": "admin' OR '1'='1",
            "password": "anything",
        })
        assert response.status_code == 401  # Should not bypass auth

    def test_timing_attack_resistance(self, client):
        """Test that login timing doesn't leak user existence."""
        import time
        
        # Login with non-existent user
        start = time.time()
        client.post("/api/v1/auth/login", json={
            "username": "nonexistent123",
            "password": "somepassword",
        })
        time_nonexistent = time.time() - start
        
        # Register real user
        client.post("/api/v1/auth/register", json={
            "username": "timingtest",
            "email": "timing@example.com",
            "password": "CorrectPass123!",
        })
        
        # Login with existing user, wrong password
        start = time.time()
        client.post("/api/v1/auth/login", json={
            "username": "timingtest",
            "password": "wrongpassword",
        })
        time_existing = time.time() - start
        
        # Times should be similar (within reason)
        # This is a basic check; timing attacks are complex
        assert abs(time_existing - time_nonexistent) < 0.5
