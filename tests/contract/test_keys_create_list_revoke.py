import httpx


def test_keys_endpoints_require_auth():
    resp = httpx.post("http://localhost:8000/api/v1/keys", json={})
    assert resp.status_code in (401, 403)
