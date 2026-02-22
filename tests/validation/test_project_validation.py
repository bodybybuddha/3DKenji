"""Validation tests for project endpoints."""

import pytest
import uuid


class TestProjectCreationValidation:
    """Test input validation for project creation."""

    @pytest.mark.parametrize("name", [
        "",
        " ",
        "a",  # Too short if min > 1
        "a" * 300,  # Too long
    ])
    def test_invalid_project_names(self, auth_client, name):
        """Test that invalid project names are rejected."""
        response = auth_client.post("/api/v1/projects", json={
            "name": name,
            "description": "Test description"
        })
        
        assert response.status_code in [400, 422]

    def test_missing_required_name(self, auth_client):
        """Test that missing project name is rejected."""
        response = auth_client.post("/api/v1/projects", json={
            "description": "Test description"
        })
        
        assert response.status_code in [400, 422]

    def test_xss_in_project_name(self, auth_client, xss_payloads):
        """Test XSS prevention in project name."""
        for payload in xss_payloads[:3]:
            response = auth_client.post("/api/v1/projects", json={
                "name": payload,
                "description": "Test"
            })
            
            # Either rejected or sanitized
            if response.status_code == 201:
                project = response.json()
                assert "<script>" not in project["name"]

    def test_xss_in_project_description(self, auth_client):
        """Test XSS prevention in project description."""
        xss_payload = "<script>alert('XSS')</script>"
        response = auth_client.post("/api/v1/projects", json={
            "name": "XSS Test Project",
            "description": xss_payload
        })
        
        if response.status_code == 201:
            project = response.json()
            # Script should be escaped or removed
            assert "<script>" not in project.get("description", "")

    def test_sql_injection_in_project_name(self, auth_client, sql_injection_payloads):
        """Test SQL injection prevention."""
        for payload in sql_injection_payloads[:3]:
            response = auth_client.post("/api/v1/projects", json={
                "name": payload,
                "description": "Test"
            })
            
            # Should not cause SQL errors
            # Either rejected or safely stored
            assert response.status_code in [201, 400, 422]

    def test_unicode_in_project_name(self, auth_client):
        """Test unicode support in project names."""
        response = auth_client.post("/api/v1/projects", json={
            "title": "プロジェクト 测试 🚀",
            "description": "Unicode test"
        })
        
        assert response.status_code == 201
        project = response.json()
        assert "🚀" in project["title"]

    def test_special_characters_in_name(self, auth_client):
        """Test special character handling."""
        special_chars = "!@#$%^&*()"
        response = auth_client.post("/api/v1/projects", json={
            "name": f"Test {special_chars} Project",
            "description": "Special chars test"
        })
        
        # Depending on requirements:
        # - May accept and store as-is
        # - May reject certain characters
        # - May sanitize
        assert response.status_code in [201, 400]

    def test_duplicate_project_name_same_user(self, auth_client):
        """Test duplicate project name handling."""
        # Create first project
        response = auth_client.post("/api/v1/projects", json={
            "name": "Duplicate Test",
            "description": "First"
        })
        assert response.status_code == 201

        # Try to create duplicate
        response = auth_client.post("/api/v1/projects", json={
            "name": "Duplicate Test",
            "description": "Second"
        })
        
        # Depending on requirements:
        # - 409 if names must be unique per user
        # - 201 if duplicate names allowed
        assert response.status_code in [201, 409]

    def test_very_long_description(self, auth_client):
        """Test description length limits."""
        long_description = "A" * 10000
        response = auth_client.post("/api/v1/projects", json={
            "name": "Long Desc Test",
            "description": long_description
        })
        
        # Should either accept, truncate, or reject
        if response.status_code == 201:
            project = response.json()
            # May be truncated
            assert len(project.get("description", "")) <= 10000

    def test_null_bytes_in_input(self, auth_client):
        """Test handling of null bytes."""
        response = auth_client.post("/api/v1/projects", json={
            "name": "Test\x00Project",
            "description": "Description\x00Test"
        })
        
        # Should reject or sanitize null bytes
        assert response.status_code in [201, 400]

    def test_whitespace_only_name(self, auth_client):
        """Test that whitespace-only names are rejected."""
        response = auth_client.post("/api/v1/projects", json={
            "name": "   ",
            "description": "Test"
        })
        
        assert response.status_code == 400

    def test_newlines_in_name(self, auth_client):
        """Test handling of newlines in project name."""
        response = auth_client.post("/api/v1/projects", json={
            "name": "Project\nWith\nNewlines",
            "description": "Test"
        })
        
        # Depending on requirements:
        # - May accept and preserve
        # - May accept and normalize
        # - May reject
        assert response.status_code in [201, 400]

    def test_html_entities_in_name(self, auth_client):
        """Test HTML entity handling."""
        response = auth_client.post("/api/v1/projects", json={
            "name": "Test &lt;Project&gt;",
            "description": "&amp; Description"
        })
        
        assert response.status_code == 201
        project = response.json()
        # Should preserve the text, not double-escape


class TestProjectUpdateValidation:
    """Test input validation for project updates."""

    def test_update_with_invalid_name(self, auth_client):
        """Test updating project with invalid name."""
        # Create project
        response = auth_client.post("/api/v1/projects", json={
            "title": "Original Name",
            "description": "Original"
        })
        project_id = response.json()["id"]

        # Try to update with empty name
        response = auth_client.patch(f"/api/v1/projects/{project_id}", json={
            "title": "",
            "description": "Updated"
        })
        
        assert response.status_code in [400, 422]

    def test_update_nonexistent_project(self, auth_client):
        """Test updating non-existent project."""
        response = auth_client.patch("/api/v1/projects/99999", json={
            "title": "Updated Name",
            "description": "Updated"
        })
        
        assert response.status_code == 404

    def test_update_with_xss(self, auth_client):
        """Test XSS prevention in updates."""
        # Create project
        response = auth_client.post("/api/v1/projects", json={
            "title": "XSS Update Test",
            "description": "Original"
        })
        project_id = response.json()["id"]

        # Update with XSS payload
        response = auth_client.patch(f"/api/v1/projects/{project_id}", json={
            "title": "Updated",
            "description": "<script>alert('XSS')</script>"
        })
        
        if response.status_code == 200:
            project = response.json()
            assert "<script>" not in project.get("description", "")


class TestProjectDeletionValidation:
    """Test validation for project deletion."""

    def test_delete_nonexistent_project(self, auth_client):
        """Test deleting non-existent project."""
        response = auth_client.delete("/api/v1/projects/99999")
        assert response.status_code == 404

    def test_delete_with_invalid_id(self, auth_client):
        """Test deletion with invalid project ID."""
        response = auth_client.delete("/api/v1/projects/invalid")
        assert response.status_code in [400, 404, 422]

    def test_delete_with_sql_injection(self, auth_client):
        """Test SQL injection prevention in deletion."""
        response = auth_client.delete("/api/v1/projects/1' OR '1'='1")
        # Should safely handle the malicious input
        assert response.status_code in [400, 404, 422]


class TestProjectListValidation:
    """Test validation for project listing."""

    def test_list_with_invalid_pagination(self, auth_client):
        """Test invalid pagination parameters."""
        response = auth_client.get("/api/v1/projects?page=-1")
        assert response.status_code in [200, 400]  # May default to valid value

        response = auth_client.get("/api/v1/projects?per_page=10000")
        assert response.status_code in [200, 400]  # May cap at max value

    def test_list_with_sql_injection_in_search(self, auth_client):
        """Test SQL injection in search parameter."""
        response = auth_client.get("/api/v1/projects?search=test' OR '1'='1")
        # Should safely handle search parameter
        assert response.status_code == 200
