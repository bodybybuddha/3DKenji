import os

import httpx


def test_projects_create_requires_auth():
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    resp = httpx.post(f"{base_url}/api/v1/projects", json={"title": "Test"})
    # Expect unauthorized until auth is implemented
    assert resp.status_code in (401, 403)
