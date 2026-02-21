import os

import pytest
import httpx


def test_projects_list_empty():
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    resp = httpx.get(f"{base_url}/api/v1/projects")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
