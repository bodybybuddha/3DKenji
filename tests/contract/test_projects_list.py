import os

import pytest
import httpx


def test_projects_list_requires_auth():
    """Test that projects list requires authentication."""
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    resp = httpx.get(f"{base_url}/api/v1/projects")
    # Expect unauthorized without auth token
    assert resp.status_code == 401
