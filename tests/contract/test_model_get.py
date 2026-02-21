import os

import httpx


def test_model_get_not_found_or_auth():
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    resp = httpx.get(f"{base_url}/api/v1/models/000")
    assert resp.status_code in (401, 403, 404)
