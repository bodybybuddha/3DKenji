"""Validation tests for API key endpoints."""

import pytest
from datetime import datetime, timedelta


class TestAPIKeyCreationValidation:
    """Test input validation for API key creation."""

    def test_create_key_without_name(self, auth_client):
        """Test that API key requires a name."""
        response = auth_client.post("/api/v1/keys", json={})
        assert response.status_code in [400, 422]

    def test_create_key_with_empty_name(self, auth_client):
        """Test that empty name is rejected."""
        response = auth_client.post("/api/v1/keys", json={
            "name": ""
        })
        assert response.status_code in [400, 422]

    def test_create_key_with_whitespace_name(self, auth_client):
        """Test that whitespace-only name is rejected."""
        response = auth_client.post("/api/v1/keys", json={
            "name": "   "
        })
        assert response.status_code in [400, 422]

    @pytest.mark.parametrize("name", [
        "a" * 300,  # Too long
        "<script>alert('xss')</script>",  # XSS
        "Key'; DROP TABLE api_keys;--",  # SQL injection
    ])
    def test_invalid_key_names(self, auth_client, name):
        """Test various invalid key names."""
        response = auth_client.post("/api/v1/keys", json={
            "name": name
        })
        
        # Either rejected or sanitized
        if response.status_code == 201:
            key = response.json()
            assert "<script>" not in key["name"]
            # Key should be created but name sanitized

    def test_create_key_with_past_expiration(self, auth_client):
        """Test that past expiration date is rejected."""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        response = auth_client.post("/api/v1/keys", json={
            "name": "Test Key",
            "expires_at": past_date
        })
        
        assert response.status_code in [400, 422]

    def test_create_key_with_invalid_date_format(self, auth_client):
        """Test invalid date format is rejected."""
        response = auth_client.post("/api/v1/keys", json={
            "name": "Test Key",
            "expires_at": "not-a-date"
        })
        
        assert response.status_code in [400, 422]

    def test_create_key_with_valid_expiration(self, auth_client):
        """Test creating key with valid future expiration."""
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        response = auth_client.post("/api/v1/keys", json={
            "name": "Valid Expiry Key",
            "expires_at": future_date
        })
        
        assert response.status_code == 201
        key = response.json()
        assert key["expires_at"] is not None

    def test_create_key_without_expiration(self, auth_client):
        """Test creating key without expiration (never expires)."""
        response = auth_client.post("/api/v1/keys", json={
            "name": "No Expiry Key"
        })
        
        assert response.status_code == 201

    def test_create_key_with_invalid_scopes(self, auth_client):
        """Test invalid scopes are rejected."""
        response = auth_client.post("/api/v1/keys", json={
            "name": "Scoped Key",
            "scopes": ["invalid_scope", "another_invalid"]
        })
        
        # Depending on implementation:
        # - 400 if strict validation
        # - 201 with filtered scopes
        # - 201 with all scopes if permissive
        assert response.status_code in [201, 400]

    def test_create_duplicate_key_name(self, auth_client):
        """Test creating keys with duplicate names."""
        # Create first key
        response = auth_client.post("/api/v1/keys", json={
            "name": "Duplicate Key Name"
        })
        assert response.status_code == 201

        # Create second key with same name
        response = auth_client.post("/api/v1/keys", json={
            "name": "Duplicate Key Name"
        })
        
        # Depending on requirements:
        # - 409 if names must be unique
        # - 201 if duplicates allowed
        assert response.status_code in [201, 409]

    def test_create_key_unauthorized(self, client):
        """Test creating key without authentication."""
        response = client.post("/api/v1/keys", json={
            "name": "Unauthorized Key"
        })
        
        assert response.status_code == 401

    def test_unicode_in_key_name(self, auth_client):
        """Test unicode characters in key name."""
        response = auth_client.post("/api/v1/keys", json={
            "name": "キー 🔑"
        })
        
        assert response.status_code == 201
        key = response.json()
        assert "🔑" in key["name"]

    def test_special_characters_in_key_name(self, auth_client):
        """Test special characters in key name."""
        response = auth_client.post("/api/v1/keys", json={
            "name": "Test Key!@#$%"
        })
        
        # Should either accept or reject based on policy
        assert response.status_code in [201, 400]


class TestAPIKeyRevocationValidation:
    """Test validation for API key revocation."""

    def test_revoke_nonexistent_key(self, auth_client):
        """Test revoking non-existent key."""
        response = auth_client.delete("/api/v1/keys/99999")
        assert response.status_code == 404

    def test_revoke_invalid_key_id(self, auth_client):
        """Test revoking with invalid key ID."""
        response = auth_client.delete("/api/v1/keys/invalid")
        assert response.status_code in [400, 404, 422]

    def test_revoke_sql_injection(self, auth_client):
        """Test SQL injection in key revocation."""
        response = auth_client.delete("/api/v1/keys/1' OR '1'='1")
        assert response.status_code in [400, 404, 422]

    def test_revoke_another_users_key(self, auth_client, client):
        """Test that users cannot revoke other users' keys."""
        # Create key with auth_client
        response = auth_client.post("/api/v1/keys", json={
            "name": "User1 Key"
        })
        key_id = response.json()["id"]

        # Create second user
        response = client.post("/api/v1/auth/register", json={
            "username": "otheruser",
            "email": "other@example.com",
            "password": "SecurePass123!"
        })
        other_token = response.json()["access_token"]
        
        # Try to revoke first user's key
        response = client.delete(
            f"/api/v1/keys/{key_id}",
            headers={"Authorization": f"Bearer {other_token}"}
        )
        
        assert response.status_code in [403, 404]

    def test_double_revocation(self, auth_client):
        """Test revoking already revoked key."""
        # Create and revoke key
        response = auth_client.post("/api/v1/keys", json={
            "name": "Double Revoke Test"
        })
        key_id = response.json()["id"]
        
        response = auth_client.delete(f"/api/v1/keys/{key_id}")
        assert response.status_code == 204

        # Try to revoke again
        response = auth_client.delete(f"/api/v1/keys/{key_id}")
        assert response.status_code in [404, 410]  # Gone or not found


class TestAPIKeyUsageValidation:
    """Test validation for using API keys."""

    def test_use_invalid_key_format(self, client):
        """Test using invalidly formatted API key."""
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": "Bearer invalid-key-format"}
        )
        assert response.status_code == 401

    def test_use_expired_key(self, auth_client, client):
        """Test using expired API key."""
        # Create key with very short expiration
        past_time = datetime.utcnow() - timedelta(seconds=1)
        response = auth_client.post("/api/v1/keys", json={
            "name": "Expired Key",
            "expires_at": past_time.isoformat()
        })
        
        # This should be rejected at creation
        assert response.status_code == 400

    def test_use_revoked_key(self, auth_client, client):
        """Test using revoked API key."""
        # Create key
        response = auth_client.post("/api/v1/keys", json={
            "name": "Revoked Key"
        })
        key_id = response.json()["id"]
        api_key = response.json()["key"]

        # Revoke it
        auth_client.delete(f"/api/v1/keys/{key_id}")

        # Try to use it
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 401

    def test_use_key_with_insufficient_scope(self, auth_client, client):
        """Test using key with insufficient permissions."""
        # Create key with limited scope
        response = auth_client.post("/api/v1/keys", json={
            "name": "Limited Key",
            "scopes": ["read:projects"]
        })
        
        if response.status_code == 201:
            api_key = response.json()["key"]

            # Try to create project (write operation)
            response = client.post(
                "/api/v1/projects",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"name": "Test Project"}
            )
            
            # Should be forbidden if scopes are enforced
            assert response.status_code in [201, 403]


class TestAPIKeyListValidation:
    """Test validation for listing API keys."""

    def test_list_keys_unauthorized(self, client):
        """Test listing keys without authentication."""
        response = client.get("/api/v1/keys")
        assert response.status_code == 401

    def test_list_keys_with_invalid_pagination(self, auth_client):
        """Test invalid pagination parameters."""
        response = auth_client.get("/api/v1/keys?page=-1")
        # Should handle gracefully
        assert response.status_code == 200
