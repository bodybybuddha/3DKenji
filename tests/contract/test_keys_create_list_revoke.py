import os

import httpx


def test_keys_endpoints_require_auth():
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    resp = httpx.post(f"{base_url}/api/v1/keys", json={})
    assert resp.status_code in (401, 403)
